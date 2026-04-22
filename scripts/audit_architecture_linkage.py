"""
@meta
name: audit_architecture_linkage
type: script
domain: docs
responsibility:
  - Audit feature sources for removed manual reference bridges.
  - Confirm architecture refs are owned by metadata instead of feature-local manual lists.
inputs:
  - docs/features/*/feature.source.yaml
  - Python @meta blocks
outputs:
  - Human-readable report for disallowed feature-source manual_refs
tags:
  - docs
  - lineage
  - metadata
  - audit
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def script_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_manual_ref_sources(root: Path) -> list[str]:
    findings: list[str] = []
    features_root = root / "docs" / "features"
    for source_path in sorted(features_root.glob("*/feature.source.yaml")):
        parsed = yaml.safe_load(source_path.read_text(encoding="utf-8"))
        if not isinstance(parsed, dict) or "manual_refs" not in parsed:
            continue
        findings.append(str(source_path.relative_to(root).as_posix()))
    return sorted(findings)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Audit architecture linkage policy that requires metadata-derived refs "
            "instead of feature-source manual_refs."
        )
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=script_root(),
        help="Repository root to audit. Defaults to the current repository root.",
    )
    parser.add_argument(
        "--strict-awareness",
        action="store_true",
        help="Exit non-zero when disallowed manual_refs are found.",
    )
    parser.add_argument(
        "--report-awareness",
        action="store_true",
        help="Print the awareness report even when no candidates are found.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.repo_root.resolve()
    manual_ref_sources = find_manual_ref_sources(root)
    if manual_ref_sources:
        print("Architecture linkage policy failed: manual_refs is not supported.")
        for source_path in manual_ref_sources:
            print(f"- {source_path}")
        return 1

    if args.report_awareness:
        print("Architecture linkage awareness audit passed: no feature-source manual_refs found.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
