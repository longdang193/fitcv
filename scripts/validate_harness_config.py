"""
@meta
name: validate_harness_config
type: script
domain: harness
distribution_tier: starter_kit
responsibility:
  - Validate canonical harness policy references.
inputs:
  - agents/*.toml
  - agents/roles.yaml
  - repo_config/harness.yaml
outputs:
  - Exit status and configuration findings.
tags:
  - harness
  - validation
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from pathlib import Path
import tomllib
from typing import Any

import yaml


ROUTE_FIELDS = {
    "template",
    "role",
    "rules",
    "skills",
    "tools",
    "workspace",
    "checks",
    "retry_policy",
    "execution_modes",
    "runtime_providers",
    "default_runtime_provider",
}
ROLE_FIELDS = {"writes", "accepts", "result_kind", "required_fields"}
ORCHESTRATION_FIELDS = {
    "aliases",
    "work_scheduling",
    "max_parallel_writers",
    "workspace_mode",
    "validator_role",
    "review_required",
    "rules",
}
RETRY_POLICY_FIELDS = {"max_attempts", "retryable_reasons", "exhaustion", "approval_resume", "approval_ttl_seconds"}
TOOL_FIELDS = {"optional", "fallback", "host_kind", "writer_access", "validator_access", "root_probe"}
REQUIRED_STATES = {"classified", "planned", "running", "observed", "verifying", "awaiting_decision", "accepted", "unvalidated", "blocked"}
RUNTIME_PROVIDER_FIELDS = {"contract_version"}
FRICTION_POLICY_FIELDS = {"event_version", "minimum_distinct_runs", "window_days"}


def load_yaml(path: Path) -> Any:
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def list_templates(root: Path) -> set[str]:
    templates: set[str] = set()
    for path in (root / "agents").glob("*.toml"):
        with path.open("rb") as handle:
            payload = tomllib.load(handle)
        name = payload.get("name")
        if isinstance(name, str) and name == path.stem:
            templates.add(name)
    return templates


def valid_string_list(value: Any) -> bool:
    return bool(value) and isinstance(value, list) and all(
        isinstance(item, str) and item for item in value
    )


def validate(root: Path) -> list[str]:
    errors: list[str] = []
    roles_path = root / "agents" / "roles.yaml"
    policy_path = root / "repo_config" / "harness.yaml"
    if not roles_path.is_file():
        return ["missing roles file `agents/roles.yaml`"]
    if not policy_path.is_file():
        return ["missing harness policy `repo_config/harness.yaml`"]

    roles_payload = load_yaml(roles_path)
    policy = load_yaml(policy_path)
    templates = list_templates(root)
    rules = {path.stem for path in (root / "docs" / "operating_system" / "rules").glob("*.md")}
    skills = {path.parent.name for path in (root / ".agents" / "skills").glob("*/SKILL.md")}

    roles = roles_payload.get("roles") if isinstance(roles_payload, dict) else None
    if not isinstance(roles, dict):
        return ["roles must be a mapping"]
    for name, role in roles.items():
        if not isinstance(name, str) or not isinstance(role, dict):
            errors.append("roles must map names to mappings")
            continue
        missing = ROLE_FIELDS - role.keys()
        if missing:
            errors.append(f"role `{name}` missing fields: {', '.join(sorted(missing))}")
        if not isinstance(role.get("writes"), bool):
            errors.append(f"role `{name}` writes must be a boolean")
        if not valid_string_list(role.get("accepts")):
            errors.append(f"role `{name}` accepts must be a list of strings")
        if not isinstance(role.get("result_kind"), str) or not role["result_kind"]:
            errors.append(f"role `{name}` result_kind must be a non-empty string")
        if not valid_string_list(role.get("required_fields")):
            errors.append(f"role `{name}` required_fields must be a list of strings")
        constraints = role.get("field_constraints")
        if constraints is not None:
            if not isinstance(constraints, dict):
                errors.append(f"role `{name}` field_constraints must be a mapping")
            else:
                for field, values in constraints.items():
                    if field not in role.get("required_fields", []) or not valid_string_list(values):
                        errors.append(f"role `{name}` field constraint `{field}` must target a required string field")

    if not isinstance(policy, dict):
        return [*errors, "harness policy must be a mapping"]
    if not isinstance(policy.get("version"), int):
        errors.append("harness policy version must be an integer")

    states = policy.get("states")
    if not isinstance(states, dict):
        errors.append("states must be a mapping")
        states = {}
    for state, next_states in states.items():
        if not valid_string_list(next_states) and next_states != []:
            errors.append(f"state `{state}` transitions must be a list of strings")
            continue
        for next_state in next_states:
            if next_state not in states:
                errors.append(f"state `{state}` references unknown state `{next_state}`")
    for state in sorted(REQUIRED_STATES - states.keys()):
        errors.append(f"missing required state `{state}`")
    for state in ("accepted", "unvalidated", "blocked"):
        if states.get(state) not in ([], None):
            errors.append(f"state `{state}` must be terminal")

    checks = policy.get("checks")
    if not isinstance(checks, dict):
        errors.append("checks must be a mapping")
        checks = {}
    for name, check in checks.items():
        command = check.get("command") if isinstance(check, dict) else None
        if not valid_string_list(command):
            errors.append(f"check `{name}` command must be a non-empty list of strings")

    tools = policy.get("tools")
    if not isinstance(tools, dict):
        errors.append("tools must be a mapping")
        tools = {}
    for name, tool in tools.items():
        if not isinstance(tool, dict):
            errors.append(f"tool `{name}` must be a mapping")
            continue
        missing = {"host_kind", "writer_access", "validator_access", "root_probe"} - tool.keys()
        unknown = set(tool) - TOOL_FIELDS
        if missing:
            errors.append(f"tool `{name}` missing fields: {', '.join(sorted(missing))}")
        if unknown:
            errors.append(f"tool `{name}` has unknown fields: {', '.join(sorted(unknown))}")
        if not isinstance(tool.get("host_kind"), str) or not tool["host_kind"]:
            errors.append(f"tool `{name}` host_kind must be a non-empty string")
        if tool.get("writer_access") not in {"workspace_write", "read_only"}:
            errors.append(f"tool `{name}` writer_access must be `workspace_write` or `read_only`")
        if tool.get("validator_access") != "read_only":
            errors.append(f"tool `{name}` validator_access must be `read_only`")
        if not isinstance(tool.get("root_probe"), str) or not tool["root_probe"]:
            errors.append(f"tool `{name}` root_probe must be a non-empty string")

    runtime_providers = policy.get("runtime_providers")
    if not isinstance(runtime_providers, dict) or not runtime_providers:
        errors.append("runtime_providers must be a non-empty mapping")
        runtime_providers = {}
    for provider_id, provider in runtime_providers.items():
        if not isinstance(provider_id, str) or not provider_id or not isinstance(provider, dict):
            errors.append("runtime_providers must map non-empty IDs to mappings")
            continue
        missing = RUNTIME_PROVIDER_FIELDS - provider.keys()
        unknown = set(provider) - RUNTIME_PROVIDER_FIELDS
        if missing:
            errors.append(f"runtime provider `{provider_id}` missing fields: {', '.join(sorted(missing))}")
        if unknown:
            errors.append(f"runtime provider `{provider_id}` has unknown fields: {', '.join(sorted(unknown))}")
        version = provider.get("contract_version")
        if not isinstance(version, int) or isinstance(version, bool) or version < 1:
            errors.append(f"runtime provider `{provider_id}` contract_version must be a positive integer")

    friction_policy = policy.get("friction_policy")
    if not isinstance(friction_policy, dict):
        errors.append("friction_policy must be a mapping")
    else:
        missing = FRICTION_POLICY_FIELDS - friction_policy.keys()
        unknown = set(friction_policy) - FRICTION_POLICY_FIELDS
        if missing:
            errors.append(f"friction policy missing fields: {', '.join(sorted(missing))}")
        if unknown:
            errors.append(f"friction policy has unknown fields: {', '.join(sorted(unknown))}")
        if friction_policy.get("event_version") != 1:
            errors.append("friction policy `event_version` must be 1")
        for name in ("minimum_distinct_runs", "window_days"):
            value = friction_policy.get(name)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append(f"friction policy `{name}` must be a positive integer")

    gates = policy.get("approval_gates", {})
    if not isinstance(gates, dict):
        errors.append("approval_gates must be a mapping")
        gates = {}
    for name, gate in gates.items():
        paths = gate.get("paths") if isinstance(gate, dict) else None
        if not valid_string_list(paths):
            errors.append(f"approval gate `{name}` paths must be a non-empty list of strings")

    retry_policies = policy.get("retry_policies")
    if not isinstance(retry_policies, dict) or not retry_policies:
        errors.append("retry_policies must be a non-empty mapping")
        retry_policies = {}
    for name, retry_policy in retry_policies.items():
        if not isinstance(retry_policy, dict):
            errors.append(f"retry policy `{name}` must be a mapping")
            continue
        missing = RETRY_POLICY_FIELDS - retry_policy.keys()
        if missing:
            errors.append(f"retry policy `{name}` missing fields: {', '.join(sorted(missing))}")
            continue
        attempts = retry_policy["max_attempts"]
        if not isinstance(attempts, int) or isinstance(attempts, bool) or attempts < 1:
            errors.append(f"retry policy `{name}` max_attempts must be a positive integer")
        if not valid_string_list(retry_policy["retryable_reasons"]):
            errors.append(f"retry policy `{name}` retryable_reasons must be a non-empty list of strings")
        if retry_policy["exhaustion"] != "block":
            errors.append(f"retry policy `{name}` exhaustion must be `block`")
        if retry_policy["approval_resume"] != "successor_attempt":
            errors.append(f"retry policy `{name}` approval_resume must be `successor_attempt`")
        ttl_seconds = retry_policy["approval_ttl_seconds"]
        if not isinstance(ttl_seconds, int) or isinstance(ttl_seconds, bool) or ttl_seconds < 1:
            errors.append(f"retry policy `{name}` approval_ttl_seconds must be a positive integer")

    orchestration = policy.get("orchestration")
    if not isinstance(orchestration, dict) or not orchestration:
        errors.append("orchestration must be a non-empty mapping")
        orchestration = {}
    aliases: dict[str, str] = {}
    for name, mode in orchestration.items():
        if not isinstance(mode, dict):
            errors.append(f"orchestration `{name}` must be a mapping")
            continue
        missing = ORCHESTRATION_FIELDS - mode.keys()
        unknown = set(mode) - ORCHESTRATION_FIELDS
        if missing:
            errors.append(f"orchestration `{name}` missing fields: {', '.join(sorted(missing))}")
            continue
        if unknown:
            errors.append(f"orchestration `{name}` has unknown fields: {', '.join(sorted(unknown))}")
        if not valid_string_list(mode["aliases"]):
            errors.append(f"orchestration `{name}` aliases must be a non-empty list of strings")
        else:
            for alias in mode["aliases"]:
                if alias in orchestration or alias in aliases:
                    errors.append(f"orchestration alias `{alias}` is ambiguous")
                aliases[alias] = name
        scheduling = mode["work_scheduling"]
        if scheduling not in {"single", "sequential", "parallel"}:
            errors.append(f"orchestration `{name}` work_scheduling must be `single`, `sequential`, or `parallel`")
        writers = mode["max_parallel_writers"]
        if not isinstance(writers, int) or isinstance(writers, bool) or writers < 1:
            errors.append(f"orchestration `{name}` max_parallel_writers must be a positive integer")
        if scheduling != "parallel" and writers != 1:
            errors.append(f"orchestration `{name}` non-parallel scheduling requires one writer")
        if scheduling == "parallel" and writers < 2:
            errors.append(f"orchestration `{name}` parallel scheduling requires at least two writers")
        if mode["workspace_mode"] != "isolated":
            errors.append(f"orchestration `{name}` workspace_mode must be `isolated`")
        validator_role = mode["validator_role"]
        if validator_role not in roles:
            errors.append(f"orchestration `{name}` has unknown validator role `{validator_role}`")
        elif roles[validator_role].get("writes") is not False:
            errors.append(f"orchestration `{name}` validator role `{validator_role}` must not write")
        if not isinstance(mode["review_required"], bool):
            errors.append(f"orchestration `{name}` review_required must be a boolean")
        if not isinstance(mode["rules"], list) or not all(isinstance(rule, str) and rule for rule in mode["rules"]):
            errors.append(f"orchestration `{name}` rules must be a list of strings")
        else:
            for rule in mode["rules"]:
                if rule not in rules:
                    errors.append(f"unknown rule `{rule}`")

    routes = policy.get("routes")
    if not isinstance(routes, dict) or not routes:
        errors.append("routes must be a non-empty mapping")
        return errors
    for name, route in routes.items():
        if not isinstance(route, dict):
            errors.append(f"route `{name}` must be a mapping")
            continue
        missing = ROUTE_FIELDS - route.keys()
        if missing:
            errors.append(f"route `{name}` missing fields: {', '.join(sorted(missing))}")
            continue
        template = route["template"]
        role_name = route["role"]
        if template not in templates:
            errors.append(f"unknown template `{template}`")
        if role_name not in roles:
            errors.append(f"unknown role `{role_name}`")
        elif template not in roles[role_name].get("accepts", []):
            errors.append(f"role `{role_name}` does not accept template `{template}`")
        for rule in route["rules"]:
            if rule not in rules:
                errors.append(f"unknown rule `{rule}`")
        for skill in route["skills"]:
            if skill not in skills:
                errors.append(f"unknown skill `{skill}`")
        for check in route["checks"]:
            if check not in checks:
                errors.append(f"unknown check `{check}`")
        for tool in route["tools"]:
            if tool not in tools:
                errors.append(f"unknown tool `{tool}`")
        for gate in route.get("approval_gates", []):
            if gate not in gates:
                errors.append(f"unknown approval gate `{gate}`")
        if route["retry_policy"] not in retry_policies:
            errors.append(f"unknown retry policy `{route['retry_policy']}`")
        for mode in route["execution_modes"]:
            if mode not in orchestration:
                errors.append(f"unknown execution mode `{mode}`")
        for field in ("rules", "skills", "tools", "checks", "execution_modes", "runtime_providers"):
            if not valid_string_list(route[field]):
                errors.append(f"route `{name}` {field} must be a non-empty list of strings")
            elif len(set(route[field])) != len(route[field]):
                errors.append(f"route `{name}` {field} must not contain duplicates")
        for provider_id in route["runtime_providers"]:
            if provider_id not in runtime_providers:
                errors.append(f"route `{name}` has unknown runtime provider `{provider_id}`")
        default_provider = route["default_runtime_provider"]
        if not isinstance(default_provider, str) or not default_provider:
            errors.append(f"route `{name}` default_runtime_provider must be a non-empty string")
        elif default_provider not in route["runtime_providers"]:
            errors.append(f"route `{name}` default_runtime_provider must be allowed")
        if not isinstance(route["workspace"], str) or not route["workspace"]:
            errors.append(f"route `{name}` workspace must be a non-empty string")
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate canonical harness policy.")
    parser.add_argument("--repo-root", default=Path(__file__).resolve().parents[1])
    args = parser.parse_args(argv)
    errors = validate(Path(args.repo_root))
    if errors:
        print("Harness configuration validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print("Harness configuration validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
