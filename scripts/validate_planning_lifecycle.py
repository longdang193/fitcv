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
