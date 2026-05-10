"""
@meta
type: test
scope: unit
domain: config
covers:
  - Repo config validation for publication config, adapter mappings, and runtime configs
excludes:
  - Full publication/export execution
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import json
import subprocess
import sys
import uuid
from pathlib import Path
from shutil import rmtree


REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR = REPO_ROOT / "scripts" / "validate_repo_config.py"


def run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def valid_starter_kit_manifest() -> dict[str, object]:
    return {
        "outputRoot": "project-OS-starter-kit",
        "copyPaths": ["AGENTS.md"],
        "requiredPaths": ["repo_config/planning_artifact_schema.yaml"],
        "forbiddenPaths": [".codex"],
    }


def make_test_root() -> Path:
    root = REPO_ROOT / ".tmp-tests" / f"validate-repo-config-{uuid.uuid4().hex}"
    root.mkdir(parents=True, exist_ok=False)
    return root


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_validator_passes_for_current_repo() -> None:
    result = run_validator()

    assert result.returncode == 0
    assert "repo config validation passed" in result.stdout.lower()


def test_validator_fails_when_publication_config_is_missing_required_keys() -> None:
    test_root = make_test_root()
    try:
        publication_config = test_root / "repo_config" / "publication-config.json"
        adapter_mappings = test_root / "repo_config" / "agent-adapter-mappings.json"
        starter_kit_manifest = test_root / "repo_config" / "starter-kit-manifest.json"
        runtime_config = test_root / "configs" / "train.yaml"

        write_json(publication_config, {"publicPaths": ["README.md"]})
        write_json(
            adapter_mappings,
            [
                {
                    "source": "docs/operating_system/templates/agents/root-AGENTS.template.md",
                    "destination": "AGENTS.md",
                    "prefix": "#",
                }
            ],
        )
        write_json(starter_kit_manifest, valid_starter_kit_manifest())
        write_text(runtime_config, "training:\n  experiment_name: train-prod\n")
        write_text(
            test_root / "docs" / "operating_system" / "templates" / "agents" / "root-AGENTS.template.md",
            "# template\n",
        )

        result = run_validator(
            "--publication-config",
            str(publication_config),
            "--adapter-mappings",
            str(adapter_mappings),
            "--starter-kit-manifest",
            str(starter_kit_manifest),
            "--runtime-config-root",
            str(test_root / "configs"),
        )

        assert result.returncode == 1
        assert "forbiddenpaths" in result.stdout.lower()
    finally:
        rmtree(test_root, ignore_errors=True)


def test_validator_fails_when_adapter_mapping_source_is_missing() -> None:
    test_root = make_test_root()
    try:
        publication_config = test_root / "repo_config" / "publication-config.json"
        adapter_mappings = test_root / "repo_config" / "agent-adapter-mappings.json"
        starter_kit_manifest = test_root / "repo_config" / "starter-kit-manifest.json"
        runtime_config = test_root / "configs" / "monitor.yaml"

        write_json(
            publication_config,
            {
                "publicPaths": ["README.md"],
                "forbiddenPaths": [".codex"],
                "requiredPaths": ["README.md"],
                "allowedGeneratedPaths": [],
                "scrubPrivateReferencePaths": ["README.md"],
            },
        )
        write_json(
            adapter_mappings,
            [
                {
                    "source": "docs/operating_system/templates/agents/missing.template.md",
                    "destination": "AGENTS.md",
                    "prefix": "#",
                }
            ],
        )
        write_json(starter_kit_manifest, valid_starter_kit_manifest())
        write_text(runtime_config, "monitor:\n  thresholds:\n    min_capture_records: 1\n")
        write_text(test_root / "README.md", "# readme\n")

        result = run_validator(
            "--publication-config",
            str(publication_config),
            "--adapter-mappings",
            str(adapter_mappings),
            "--starter-kit-manifest",
            str(starter_kit_manifest),
            "--runtime-config-root",
            str(test_root / "configs"),
        )

        assert result.returncode == 1
        assert "missing adapter source" in result.stdout.lower()
    finally:
        rmtree(test_root, ignore_errors=True)


def test_validator_fails_when_runtime_config_is_not_a_mapping() -> None:
    test_root = make_test_root()
    try:
        publication_config = test_root / "repo_config" / "publication-config.json"
        adapter_mappings = test_root / "repo_config" / "agent-adapter-mappings.json"
        starter_kit_manifest = test_root / "repo_config" / "starter-kit-manifest.json"
        runtime_config = test_root / "configs" / "assets.yaml"

        write_json(
            publication_config,
            {
                "publicPaths": ["README.md"],
                "forbiddenPaths": [".codex"],
                "requiredPaths": ["README.md"],
                "allowedGeneratedPaths": [],
                "scrubPrivateReferencePaths": ["README.md"],
            },
        )
        write_json(
            adapter_mappings,
            [
                {
                    "source": "docs/operating_system/templates/agents/root-AGENTS.template.md",
                    "destination": "AGENTS.md",
                    "prefix": "#",
                }
            ],
        )
        write_json(starter_kit_manifest, valid_starter_kit_manifest())
        write_text(runtime_config, "- just\n- a\n- list\n")
        write_text(test_root / "README.md", "# readme\n")
        write_text(
            test_root / "docs" / "operating_system" / "templates" / "agents" / "root-AGENTS.template.md",
            "# template\n",
        )

        result = run_validator(
            "--publication-config",
            str(publication_config),
            "--adapter-mappings",
            str(adapter_mappings),
            "--starter-kit-manifest",
            str(starter_kit_manifest),
            "--runtime-config-root",
            str(test_root / "configs"),
        )

        assert result.returncode == 1
        assert "top-level mapping" in result.stdout.lower()
    finally:
        rmtree(test_root, ignore_errors=True)


def test_validator_fails_when_starter_kit_manifest_is_missing_required_keys() -> None:
    test_root = make_test_root()
    try:
        publication_config = test_root / "repo_config" / "publication-config.json"
        adapter_mappings = test_root / "repo_config" / "agent-adapter-mappings.json"
        starter_kit_manifest = test_root / "repo_config" / "starter-kit-manifest.json"
        runtime_config = test_root / "configs" / "assets.yaml"

        write_json(
            publication_config,
            {
                "publicPaths": ["README.md"],
                "forbiddenPaths": [".codex"],
                "requiredPaths": ["README.md"],
                "allowedGeneratedPaths": [],
                "scrubPrivateReferencePaths": ["README.md"],
            },
        )
        write_json(
            adapter_mappings,
            [
                {
                    "source": "docs/operating_system/templates/agents/root-AGENTS.template.md",
                    "destination": "AGENTS.md",
                    "prefix": "#",
                }
            ],
        )
        write_json(starter_kit_manifest, {"outputRoot": "project-OS-starter-kit"})
        write_text(runtime_config, "assets:\n  enabled: true\n")
        write_text(test_root / "README.md", "# readme\n")
        write_text(
            test_root / "docs" / "operating_system" / "templates" / "agents" / "root-AGENTS.template.md",
            "# template\n",
        )

        result = run_validator(
            "--publication-config",
            str(publication_config),
            "--adapter-mappings",
            str(adapter_mappings),
            "--starter-kit-manifest",
            str(starter_kit_manifest),
            "--runtime-config-root",
            str(test_root / "configs"),
        )

        assert result.returncode == 1
        assert "starter-kit manifest is missing required keys" in result.stdout.lower()
    finally:
        rmtree(test_root, ignore_errors=True)
