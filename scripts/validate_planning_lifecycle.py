"""
@meta
name: validate_planning_lifecycle
type: script
domain: docs
distribution_tier: starter_kit
responsibility:
  - Validate metadata for planning artifacts that exist.
  - Validate optional plan-to-spec references.
  - Keep roadmap use optional.
inputs:
  - docs/intent/master-workstream-roadmap.md
  - docs/superpowers/specs/*.md
  - docs/superpowers/plans/*.md
outputs:
  - Exit status and human-readable planning validation report.
tags:
  - docs
  - validation
  - planning
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import sys
from typing import Any

import yaml

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from planning_artifact_schema import (
    get_allowed_values,
    get_artifact_schema,
    get_required_fields,
    get_required_values,
)


@dataclass(frozen=True)
class Finding:
    category: str
    path: str
    message: str


COORDINATION_STATES = {"pending", "active", "blocked", "completed"}


def _clean_coordination_cell(value: str) -> str:
    return value.strip().strip("`").strip()


def _coordination_rows(text: str) -> list[dict[str, str]]:
    header = re.search(
        r"(?im)^\|\s*Task\s*\|\s*State\s*\|\s*Workspace\s*\|\s*Executor\s*\|"
        r"\s*(?:Depends On|Dependencies)\s*\|\s*Required Proof\s*\|"
        r"\s*(?:Evidence|Last Evidence)\s*\|\s*\r?$",
        text,
    )
    if header is None:
        return []

    rows: list[dict[str, str]] = []
    for line in text[header.end() :].splitlines():
        if not line.strip():
            continue
        if not line.lstrip().startswith("|"):
            break
        cells = [_clean_coordination_cell(cell) for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7 or all(set(cell) <= {"-", ":", " "} for cell in cells):
            continue
        rows.append(
            {
                "task": cells[0],
                "state": cells[1].lower(),
                "workspace": cells[2],
                "executor": cells[3],
                "dependencies": cells[4],
                "proof": cells[5],
                "evidence": cells[6],
            }
        )
    return rows


def _coordination_value(text: str, label: str) -> str | None:
    match = re.search(rf"(?im)^-\s*{re.escape(label)}:\s*(.+?)\s*$", text)
    return match.group(1).strip() if match else None


def validate_git_coordination(path: Path, payload: dict[str, Any], text: str) -> list[Finding]:
    if re.search(r"(?im)^-\s*Coordination:\s*`?git-tracked`?\s*$", text) is None:
        return []

    rel = path.as_posix()
    findings: list[Finding] = []
    if re.search(r"(?im)^##\s+Coordination State\s*$", text) is None:
        return [Finding("coordination_error", rel, "git-tracked plan requires `## Coordination State`")]

    owner_matches = re.findall(r"(?im)^-\s*Coordination owner:\s*(.+?)\s*$", text)
    if len(owner_matches) != 1 or not owner_matches[0].strip('` <>"'):
        findings.append(Finding("coordination_error", rel, "requires exactly one coordination owner"))

    for label in ("Branch", "Base commit", "Active task(s)", "Expected workspace", "Next action", "Blockers"):
        value = _coordination_value(text, label)
        if value is None or not value.strip('` <>"'):
            findings.append(Finding("coordination_error", rel, f"missing coordination field `{label}`"))

    rows = _coordination_rows(text)
    if not rows:
        findings.append(Finding("coordination_error", rel, "requires a task ledger with proof columns"))
        return findings

    invalid_states = sorted({row["state"] for row in rows} - COORDINATION_STATES)
    if invalid_states:
        findings.append(
            Finding("coordination_error", rel, f"task state must be one of: {', '.join(sorted(COORDINATION_STATES))}")
        )

    mode_match = re.search(r"(?im)^-\s*Mode:\s*`?([^`\r\n]+)", text)
    mode = mode_match.group(1).strip().lower() if mode_match else ""
    active_rows = [row for row in rows if row["state"] == "active"]
    if mode in {"inline sequential", "subagent-ready"} and len(active_rows) > 1:
        findings.append(Finding("coordination_error", rel, f"{mode} permits at most one active task"))

    records = {row["task"]: row for row in rows}
    for row in active_rows:
        dependencies = row["dependencies"]
        if dependencies.lower() in {"", "none", "n/a"}:
            continue
        for dependency in re.findall(r"Task\s+\d+", dependencies, flags=re.IGNORECASE) or [dependencies]:
            dependency = dependency.strip()
            dependency_row = records.get(dependency)
            if dependency_row is None or dependency_row["state"] != "completed":
                findings.append(
                    Finding(
                        "coordination_error",
                        rel,
                        f"active task `{row['task']}` depends on non-completed task `{dependency}`",
                    )
                )

    for row in rows:
        if row["state"] == "completed" and row["evidence"].lower() in {"", "pending", "none", "n/a"}:
            findings.append(
                Finding(
                    "coordination_error",
                    rel,
                    f"completed task `{row['task']}` requires recorded evidence",
                )
            )

    if payload.get("status") == "completed":
        if any(row["state"] in {"active", "blocked"} for row in rows):
            findings.append(Finding("coordination_error", rel, "completed plan cannot have active or blocked tasks"))
        if (_coordination_value(text, "Blockers") or "").strip("` ").lower() not in {"", "none", "n/a"}:
            findings.append(Finding("coordination_error", rel, "completed plan cannot have unresolved blockers"))

    return findings


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate existing roadmap, specification, and plan artifacts."
    )
    parser.add_argument(
        "--repo-root",
        default=str(Path(__file__).resolve().parents[1]),
        help="Repository root. Defaults to this script's repository.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Retained for command compatibility; existing-artifact errors always fail.",
    )
    return parser


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def extract_frontmatter(path: Path) -> dict[str, Any] | None:
    text = path.read_text(encoding="utf-8", errors="ignore").removeprefix("\ufeff")
    if not text.startswith("---"):
        return None
    marker_end = text.find("\n---", 3)
    if marker_end == -1:
        return None
    payload = yaml.safe_load(text[3:marker_end])
    return payload if isinstance(payload, dict) else None


def discover_artifacts(root: Path, artifact_type: str) -> list[Path]:
    schema = get_artifact_schema(root, artifact_type)
    globs = schema.get("path_globs", [])
    paths: set[Path] = set()
    if isinstance(globs, list):
        for pattern in globs:
            if isinstance(pattern, str):
                paths.update(
                    path
                    for path in root.glob(pattern)
                    if path.is_file() and path.name != "README.md"
                )
    return sorted(paths)


def validate_artifact(root: Path, path: Path, artifact_type: str) -> list[Finding]:
    rel = relative_path(path, root)
    text = path.read_text(encoding="utf-8", errors="ignore")
    payload = extract_frontmatter(path)
    if payload is None:
        return [Finding("planning_metadata_error", rel, "missing valid YAML frontmatter")]

    findings: list[Finding] = []
    for field in get_required_fields(root, artifact_type):
        if field not in payload or payload[field] in (None, ""):
            findings.append(
                Finding("planning_metadata_error", rel, f"missing required field `{field}`")
            )

    for field, expected in get_required_values(root, artifact_type).items():
        if payload.get(field) != expected:
            findings.append(
                Finding(
                    "planning_metadata_error",
                    rel,
                    f"`{field}` must be `{expected}` for {artifact_type} artifacts",
                )
            )

    for field in ("status", "layer"):
        allowed = get_allowed_values(root, field, artifact_type)
        value = payload.get(field)
        if allowed and value is not None and value not in allowed:
            findings.append(
                Finding(
                    "planning_metadata_error",
                    rel,
                    f"`{field}` must be one of: {', '.join(allowed)}",
                )
            )

    parent_spec_value = payload.get("parent_spec")
    if (
        artifact_type == "plan"
        and payload.get("status") in {"proposed", "active"}
        and isinstance(parent_spec_value, str)
        and parent_spec_value != "none"
    ):
        parent_spec = root / parent_spec_value
        if not parent_spec.is_file():
            findings.append(
                Finding(
                    "planning_reference_error",
                    rel,
                    f"parent_spec does not resolve: `{parent_spec_value}`",
                )
            )
    if artifact_type == "plan":
        findings.extend(validate_git_coordination(Path(rel), payload, text))
    return findings


def validate_planning_artifacts(root: Path) -> list[Finding]:
    findings: list[Finding] = []
    for artifact_type in ("roadmap", "spec", "plan"):
        for path in discover_artifacts(root, artifact_type):
            findings.extend(validate_artifact(root, path, artifact_type))
    return findings


def main() -> int:
    args = build_parser().parse_args()
    root = Path(args.repo_root).resolve()
    findings = validate_planning_artifacts(root)
    if findings:
        print("Planning artifact validation failed:")
        for finding in findings:
            print(f"- [{finding.category}] {finding.path}: {finding.message}")
        return 1
    print("Planning artifact validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
