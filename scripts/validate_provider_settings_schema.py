"""
Validate provider settings schema, hook contracts, and capability compatibility.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

VALID_PROVIDERS = ("codex", "claude", "antigravity")
VALID_EVENTS = ("task_start", "task_end", "error", "pre_tool", "post_tool")
VALIDATOR_COMMAND = "python scripts/hooks/run_validator.py --fast"
MAX_TIMEOUT_SECONDS = 120


@dataclass(frozen=True)
class Finding:
    category: str
    path: str
    message: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate provider settings schema.")
    parser.add_argument("--repo-root", default=str(repo_root()))
    return parser.parse_args()


def _read_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _relative(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def _contains_encoded_whitespace(command: str) -> bool:
    return "%20" in command.lower()


def validate(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    settings_root = root / "docs" / "operating_system" / "provider_settings"
    for provider in VALID_PROVIDERS:
        path = settings_root / f"{provider}.yaml"
        rel = _relative(path, root)
        if not path.exists():
            findings.append(Finding("provider_settings_schema_error", rel, "missing provider settings file."))
            continue
        payload = _read_yaml(path)
        if payload.get("provider") != provider:
            findings.append(Finding("provider_settings_schema_error", rel, "`provider` must match file name."))
        if payload.get("schema_version") != 1:
            findings.append(Finding("provider_settings_schema_error", rel, "`schema_version` must be 1."))

        hooks = payload.get("hooks")
        if not isinstance(hooks, dict):
            findings.append(Finding("provider_settings_schema_error", rel, "`hooks` must be an object."))
            continue

        hooks_enabled = hooks.get("enabled")
        if not isinstance(hooks_enabled, bool):
            findings.append(Finding("provider_settings_schema_error", rel, "`hooks.enabled` must be boolean."))

        events = hooks.get("events")
        if not isinstance(events, dict):
            findings.append(Finding("provider_settings_schema_error", rel, "`hooks.events` must be an object."))
            continue

        for event_name in VALID_EVENTS:
            event = events.get(event_name)
            if not isinstance(event, dict):
                findings.append(Finding("provider_settings_schema_error", rel, f"`hooks.events.{event_name}` must be an object."))
                continue

            event_enabled = event.get("enabled")
            if not isinstance(event_enabled, bool):
                findings.append(Finding("provider_settings_schema_error", rel, f"`hooks.events.{event_name}.enabled` must be boolean."))
                continue

            if provider in ("codex", "claude"):
                provider_event = event.get("provider_event")
                if event_enabled and (not isinstance(provider_event, str) or not provider_event.strip()):
                    findings.append(
                        Finding(
                            "provider_settings_schema_error",
                            rel,
                            f"`hooks.events.{event_name}.provider_event` must be set for enabled lifecycle hooks.",
                        )
                    )
                blocking = event.get("blocking")
                timeout = event.get("timeout_seconds")
                commands = event.get("commands")
                if not isinstance(blocking, bool):
                    findings.append(Finding("provider_settings_schema_error", rel, f"`hooks.events.{event_name}.blocking` must be boolean."))
                if not isinstance(timeout, int) or timeout <= 0 or timeout > MAX_TIMEOUT_SECONDS:
                    findings.append(
                        Finding(
                            "provider_settings_schema_error",
                            rel,
                            f"`hooks.events.{event_name}.timeout_seconds` must be an int between 1 and {MAX_TIMEOUT_SECONDS}.",
                        )
                    )
                if not isinstance(commands, list):
                    findings.append(Finding("provider_settings_schema_error", rel, f"`hooks.events.{event_name}.commands` must be a list."))
                    continue
                for command in commands:
                    if not isinstance(command, str) or not command.strip():
                        findings.append(
                            Finding(
                                "provider_settings_schema_error",
                                rel,
                                f"`hooks.events.{event_name}.commands` entries must be non-empty strings.",
                            )
                        )
                        continue
                    if _contains_encoded_whitespace(command):
                        findings.append(
                            Finding(
                                "provider_settings_schema_error",
                                rel,
                                f"`hooks.events.{event_name}.commands` must not include URL-encoded paths.",
                            )
                        )
                if event_enabled and event_name == "task_end":
                    if VALIDATOR_COMMAND not in commands:
                        findings.append(
                            Finding(
                                "provider_settings_schema_error",
                                rel,
                                "enabled `task_end` must include the shared validator wrapper command.",
                            )
                        )
            else:
                fallback_rule = event.get("fallback_rule")
                if event_enabled and (not isinstance(fallback_rule, str) or not fallback_rule.strip()):
                    findings.append(
                        Finding(
                            "provider_settings_schema_error",
                            rel,
                            f"`hooks.events.{event_name}.fallback_rule` must be set for enabled fallback events.",
                        )
                    )

    return findings


def main() -> int:
    args = parse_args()
    root = Path(args.repo_root).resolve()
    findings = validate(root)
    if findings:
        print("Provider settings schema validation failed:")
        for finding in findings:
            print(f"- {finding.category}: {finding.path} - {finding.message}")
        return 1
    print("Provider settings schema validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
