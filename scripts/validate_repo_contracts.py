"""
@meta
name: validate_repo_contracts
type: script
domain: docs
responsibility:
  - Validate the repo contract graph across generated outputs, metadata-bearing sources, and repo-wide validation entrypoints.
  - Orchestrate architecture sync checks, repo-config validation, and adoption-shape validation through one canonical command.
  - Enforce required metadata coverage for config and setup surfaces plus mixed-ownership feature-history boundaries.
inputs:
  - docs/features/*/feature.source.yaml
  - docs/features/*/history.md
  - docs/stages/*.source.yaml
  - repo_config/adoption-mode.yaml
  - config/**/*.yaml
  - setup/*.ps1
  - setup/*.sh
outputs:
  - Exit status and human-readable repo contract validation results.
tags:
  - docs
  - validation
  - metadata
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

import yaml


GENERATED_HISTORY_START = "<!-- GENERATED HISTORY START -->"
GENERATED_HISTORY_END = "<!-- GENERATED HISTORY END -->"
HUMAN_HISTORY_HEADING = "## Human Notes"


@dataclass(frozen=True)
class ValidationIssue:
    category: str
    path: str
    message: str


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate the repo contract graph across generated outputs, "
            "metadata-bearing sources, mixed-ownership docs, and adoption shape."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(repo_root()),
        help="Repository root. Defaults to this script's repository.",
    )
    parser.add_argument(
        "--fast",
        action="store_true",
        help=(
            "Run the hook-facing validation subset. This still runs the "
            "architecture sync check path and skips only the extra validator-"
            "specific pytest pass."
        ),
    )
    return parser


def pytest_basetemp(default_relative: str) -> str:
    override = os.environ.get("REPO_VALIDATOR_PYTEST_BASETEMP")
    if override:
        return override
    return default_relative


def venv_site_packages(root: Path) -> Path | None:
    site_packages = root / ".venv" / "Lib" / "site-packages"
    if site_packages.exists():
        return site_packages
    return None


def resolve_python_executable(root: Path) -> str:
    pyvenv_cfg = root / ".venv" / "pyvenv.cfg"
    if pyvenv_cfg.exists():
        for line in pyvenv_cfg.read_text(encoding="utf-8").splitlines():
            if not line.startswith("home = "):
                continue
            home = line.split("=", 1)[1].strip()
            candidate = Path(home) / "python.exe"
            try:
                if candidate.exists():
                    return str(candidate)
            except PermissionError:
                continue
    return sys.executable


def read_adoption_mode(root: Path) -> dict[str, Any]:
    adoption_mode_path = root / "repo_config" / "adoption-mode.yaml"
    if not adoption_mode_path.exists():
        return {}
    payload = yaml.safe_load(adoption_mode_path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def managed_architecture_metadata_enabled(root: Path) -> bool:
    payload = read_adoption_mode(root)
    return bool(payload.get("managed_architecture_metadata", False))


def run_step(command: list[str], *, cwd: Path) -> int:
    rendered = " ".join(command)
    print(f"> {rendered}")
    env = os.environ.copy()
    site_packages = venv_site_packages(cwd)
    if site_packages is not None and command and command[0].lower().endswith("python.exe"):
        existing = env.get("PYTHONPATH")
        env["PYTHONPATH"] = (
            str(site_packages)
            if not existing
            else os.pathsep.join([str(site_packages), existing])
        )
    completed = subprocess.run(command, cwd=cwd, check=False, env=env)
    return completed.returncode


def build_subprocess_steps(*, root: Path, python_executable: str, fast: bool) -> list[list[str]]:
    sync_script = str(root / "scripts" / "sync_architecture_docs.py")
    repo_config_script = str(root / "scripts" / "validate_repo_config.py")
    adoption_shape_script = str(root / "scripts" / "validate_adoption_shape.py")
    steps: list[list[str]] = [
        [python_executable, sync_script, "--check"],
        [python_executable, repo_config_script],
        [python_executable, adoption_shape_script],
    ]
    if not fast:
        basetemp = root / pytest_basetemp(".tmp-tests/repo-contract-pytest")
        basetemp.parent.mkdir(parents=True, exist_ok=True)
        steps.append(
            [
                python_executable,
                "-m",
                "pytest",
                "--basetemp",
                str(basetemp),
                "tests/test_validate_repo_config.py",
                "tests/test_validate_adoption_shape.py",
                "tests/test_validate_repo_contracts.py",
                "-q",
            ]
        )
    return steps


def validate_history_boundaries(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for source_path in sorted((root / "docs" / "features").glob("*/feature.source.yaml")):
        history_path = source_path.parent / "history.md"
        rel_path = relative_path(history_path, root)
        if not history_path.exists():
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message="missing required history.md for opted-in feature folder",
                )
            )
            continue

        text = history_path.read_text(encoding="utf-8")
        start_count = text.count(GENERATED_HISTORY_START)
        end_count = text.count(GENERATED_HISTORY_END)
        human_count = text.count(HUMAN_HISTORY_HEADING)

        if start_count == 0 and end_count == 0 and human_count == 0:
            continue
        if start_count != 1:
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message=f"expected exactly one generated history start marker, found {start_count}",
                )
            )
        if end_count != 1:
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message=f"expected exactly one generated history end marker, found {end_count}",
                )
            )
        if start_count != 1 or end_count != 1:
            continue

        start_index = text.index(GENERATED_HISTORY_START)
        end_index = text.index(GENERATED_HISTORY_END)
        if start_index > end_index:
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message="generated history end marker appears before the start marker",
                )
            )
            continue

        after_end = text[end_index + len(GENERATED_HISTORY_END) :].lstrip("\n")
        if not after_end.startswith(HUMAN_HISTORY_HEADING):
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message="missing required `## Human Notes` section after generated history block",
                )
            )
        elif human_count != 1:
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message=f"expected exactly one `## Human Notes` heading, found {human_count}",
                )
            )
    return issues


def _starts_with_architecture_block(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == "# @architecture":
            return True
        if stripped.startswith("#"):
            continue
        return False
    return False


def _has_setup_meta(text: str, suffix: str) -> bool:
    lines = text.splitlines()
    if suffix == ".sh" and lines and lines[0].startswith("#!"):
        lines = lines[1:]
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.startswith("#"):
            return False
        return stripped[1:].lstrip() == "@meta"
    return False


def validate_required_metadata_coverage(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not managed_architecture_metadata_enabled(root):
        return issues

    configs_root = root / "config"
    if configs_root.exists():
        for path in sorted(configs_root.rglob("*.yaml")):
            if not path.is_file():
                continue
            if not _starts_with_architecture_block(path.read_text(encoding="utf-8")):
                issues.append(
                    ValidationIssue(
                        category="missing_required_metadata",
                        path=relative_path(path, root),
                        message="runtime config is missing required top-of-file `# @architecture` metadata",
                    )
                )

    setup_root = root / "setup"
    if setup_root.exists():
        for pattern in ("*.ps1", "*.sh"):
            for path in sorted(setup_root.glob(pattern)):
                if not path.is_file():
                    continue
                if not _has_setup_meta(path.read_text(encoding="utf-8"), path.suffix):
                    issues.append(
                        ValidationIssue(
                            category="missing_required_metadata",
                            path=relative_path(path, root),
                            message="setup script is missing required top-of-file `@meta` comment block",
                        )
                    )
    return issues


def report_issues(issues: list[ValidationIssue]) -> int:
    if not issues:
        return 0
    print("Repo contract validation failed:")
    for issue in issues:
        print(f"- {issue.category}: {issue.path} - {issue.message}")
    return 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(args.repo_root).resolve()

    issues = [
        *validate_required_metadata_coverage(root),
        *validate_history_boundaries(root),
    ]
    status = report_issues(issues)
    if status != 0:
        return status

    for step in build_subprocess_steps(
        root=root,
        python_executable=resolve_python_executable(root),
        fast=args.fast,
    ):
        status = run_step(step, cwd=root)
        if status != 0:
            return status

    print(
        "Repo contract validation passed (hook subset)."
        if args.fast
        else "Repo contract validation passed."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
