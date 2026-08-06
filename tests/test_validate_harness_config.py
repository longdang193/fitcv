"""
@meta
name: test_validate_harness_config
type: test
domain: harness
distribution_tier: starter_kit
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "validate_harness_config.py"


def load_validator():
    spec = importlib.util.spec_from_file_location("validate_harness_config", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_text(root: Path, relative_path: str, content: str) -> None:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_harness_root(root: Path) -> None:
    for name in ("low", "normal", "high"):
        write_text(root, f"agents/{name}.toml", f'name = "{name}"\n')

    write_text(
        root,
        "agents/roles.yaml",
        yaml.safe_dump(
            {
                "version": 1,
                "roles": {
                    "implement": {
                        "writes": True,
                        "accepts": ["low", "normal", "high"],
                        "result_kind": "claimed_result",
                        "required_fields": ["changed_files"],
                    },
                    "validate": {
                        "writes": False,
                        "accepts": ["low", "normal", "high"],
                        "result_kind": "claimed_result",
                        "required_fields": ["summary", "findings", "verdict"],
                    },
                },
            },
            sort_keys=False,
        ),
    )
    write_text(
        root,
        "docs/operating_system/rules/command-execution-rule.md",
        "# Command Execution\n",
    )
    write_text(
        root,
        "docs/operating_system/rules/multi-agent-orchestration-rule.md",
        "# Multi-Agent Orchestration\n",
    )
    write_text(
        root,
        ".agents/skills/skill-code-standards/SKILL.md",
        "---\nname: skill-code-standards\ndescription: Use when standards apply.\n---\n",
    )
    write_text(
        root,
        "repo_config/harness.yaml",
        yaml.safe_dump(
            {
                "version": 3,
                "states": {
                    "classified": ["planned", "blocked"],
                    "planned": ["running", "awaiting_decision", "blocked"],
                    "running": ["observed", "awaiting_decision", "blocked"],
                    "observed": ["verifying", "running", "blocked"],
                    "verifying": ["awaiting_decision", "accepted", "blocked"],
                    "awaiting_decision": ["awaiting_decision", "planned", "accepted", "unvalidated", "blocked"],
                    "accepted": [],
                    "unvalidated": [],
                    "blocked": [],
                },
                "retry_policies": {
                    "bounded": {
                        "max_attempts": 2,
                        "retryable_reasons": ["check_failed", "review_required"],
                        "exhaustion": "block",
                        "approval_resume": "successor_attempt",
                        "approval_ttl_seconds": 3600,
                    }
                },
                "checks": {"diff": {"command": ["git", "diff", "--check"]}},
                "tools": {
                    "shell": {
                        "optional": False,
                        "host_kind": "app_server_shell",
                        "writer_access": "workspace_write",
                        "validator_access": "read_only",
                        "root_probe": "shell_root_probe",
                    }
                },
                "runtime_providers": {
                    "codex_app_server": {"contract_version": 1},
                },
                "friction_policy": {
                    "event_version": 1,
                    "minimum_distinct_runs": 3,
                    "window_days": 14,
                },
                "orchestration": {
                    "single_work_lane": {
                        "aliases": ["single_agent"],
                        "work_scheduling": "single",
                        "max_parallel_writers": 1,
                        "workspace_mode": "isolated",
                        "validator_role": "validate",
                        "review_required": False,
                        "rules": [],
                    },
                    "sequential_work_lanes": {
                        "aliases": ["sequential_agents"],
                        "work_scheduling": "sequential",
                        "max_parallel_writers": 1,
                        "workspace_mode": "isolated",
                        "validator_role": "validate",
                        "review_required": True,
                        "rules": ["multi-agent-orchestration-rule"],
                    },
                },
                "routes": {
                    "local_change": {
                        "template": "low",
                        "role": "implement",
                        "rules": ["command-execution-rule"],
                        "skills": ["skill-code-standards"],
                        "tools": ["shell"],
                        "workspace": "current",
                        "checks": ["diff"],
                        "retry_policy": "bounded",
                        "execution_modes": ["single_work_lane", "sequential_work_lanes"],
                        "runtime_providers": ["codex_app_server"],
                        "default_runtime_provider": "codex_app_server",
                    }
                },
            },
            sort_keys=False,
        ),
    )


def test_valid_harness_config_passes(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)

    assert validator.validate(tmp_path) == []


def test_unknown_route_runtime_provider_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["runtime_providers"] = ["missing"]
    config["routes"]["local_change"]["default_runtime_provider"] = "missing"
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "route `local_change` has unknown runtime provider `missing`" in validator.validate(tmp_path)


def test_route_runtime_provider_default_must_be_allowed(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["default_runtime_provider"] = "missing"
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "route `local_change` default_runtime_provider must be allowed" in validator.validate(tmp_path)


def test_missing_template_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["template"] = "missing"
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown template `missing`" in validator.validate(tmp_path)


def test_missing_skill_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["skills"] = ["skill-missing"]
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown skill `skill-missing`" in validator.validate(tmp_path)


def test_missing_role_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["role"] = "missing"
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown role `missing`" in validator.validate(tmp_path)


def test_missing_rule_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["rules"] = ["missing-rule"]
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown rule `missing-rule`" in validator.validate(tmp_path)


def test_missing_check_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["checks"] = ["missing"]
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown check `missing`" in validator.validate(tmp_path)


def test_empty_check_command_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["checks"]["diff"]["command"] = []
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "check `diff` command must be a non-empty list of strings" in validator.validate(tmp_path)


def test_unknown_tool_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["tools"] = ["missing"]
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown tool `missing`" in validator.validate(tmp_path)


def test_invalid_execution_mode_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["execution_modes"] = ["missing"]
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown execution mode `missing`" in validator.validate(tmp_path)


def test_parallel_writers_require_isolated_workspace(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["orchestration"]["sequential_work_lanes"]["max_parallel_writers"] = 2
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "orchestration `sequential_work_lanes` non-parallel scheduling requires one writer" in validator.validate(tmp_path)


def test_ambiguous_alias_and_unknown_topology_field_fail(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["orchestration"]["single_work_lane"]["aliases"].append("sequential_agents")
    config["orchestration"]["single_work_lane"]["unexpected"] = True
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    errors = validator.validate(tmp_path)

    assert "orchestration `single_work_lane` has unknown fields: unexpected" in errors
    assert "orchestration alias `sequential_agents` is ambiguous" in errors


def test_invalid_state_transition_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["states"]["observed"] = ["missing"]
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "state `observed` references unknown state `missing`" in validator.validate(tmp_path)


def test_invalid_role_template_pairing_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    roles = yaml.safe_load((tmp_path / "agents/roles.yaml").read_text())
    roles["roles"]["implement"]["accepts"] = ["normal"]
    (tmp_path / "agents/roles.yaml").write_text(yaml.safe_dump(roles), encoding="utf-8")

    assert "role `implement` does not accept template `low`" in validator.validate(tmp_path)


def test_missing_route_retry_policy_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    del config["routes"]["local_change"]["retry_policy"]
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "route `local_change` missing fields: retry_policy" in validator.validate(tmp_path)


def test_unknown_route_retry_policy_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["routes"]["local_change"]["retry_policy"] = "missing"
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "unknown retry policy `missing`" in validator.validate(tmp_path)


def test_invalid_retry_policy_approval_ttl_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["retry_policies"]["bounded"]["approval_ttl_seconds"] = 0
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "retry policy `bounded` approval_ttl_seconds must be a positive integer" in validator.validate(tmp_path)


def test_invalid_friction_policy_fails(tmp_path: Path) -> None:
    validator = load_validator()
    write_harness_root(tmp_path)
    config = yaml.safe_load((tmp_path / "repo_config/harness.yaml").read_text())
    config["friction_policy"]["window_days"] = 0
    (tmp_path / "repo_config/harness.yaml").write_text(yaml.safe_dump(config), encoding="utf-8")

    assert "friction policy `window_days` must be a positive integer" in validator.validate(tmp_path)
