"""
@meta
name: validate_repo_contracts
type: script
domain: docs
responsibility:
  - Validate the repo contract graph across source-owned, generated, and partially generated surfaces.
  - Orchestrate architecture checks, adoption-shape validation, repo-config validation, and governed metadata coverage checks through one canonical command.
  - Enforce mixed-ownership boundary rules for feature history files before commit or CI completion.
inputs:
  - docs/features/*/feature.source.yaml
  - docs/features/*/history.md
  - docs/stages/*.source.yaml
  - docs/superpowers/specs/*.md
  - docs/superpowers/plans/*.md
  - repo_config/adoption-mode.yaml
  - repo_config/*.json
  - configs/*.yaml
  - aml/components/*.yaml
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
from functools import lru_cache
import importlib.util
import inspect
import os
from pathlib import Path
import subprocess
import sys
from types import ModuleType

import yaml
from validator_policy import (
    ALLOWED_MODES,
    ARCHITECTURE_METADATA_MARKER_LINE,
    GENERATED_HISTORY_END_MARKER,
    GENERATED_HISTORY_START_MARKER,
    HUMAN_NOTES_HEADING,
    SETUP_META_MARKER,
)


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
            "metadata-bearing sources, mixed-ownership docs, adoption shape, "
            "and repo config."
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


@lru_cache(maxsize=8)
def load_adoption_mode_payload(root: Path) -> dict | None:
    adoption_mode_path = root / "repo_config" / "adoption-mode.yaml"
    if not adoption_mode_path.exists():
        return None
    payload = yaml.safe_load(adoption_mode_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return None
    return payload

def managed_architecture_metadata_enabled(root: Path) -> bool:
    payload = load_adoption_mode_payload(root)
    if payload is None:
        return True
    return bool(payload.get("managed_architecture_metadata", False))

def read_adoption_mode(root: Path) -> str | None:
    payload = load_adoption_mode_payload(root)
    if payload is None:
        return None
    mode = payload.get("adoption_mode")
    if mode not in ALLOWED_MODES:
        return None
    return mode

IN_PROCESS_SCRIPT_NAMES = {
    "validate_adoption_shape.py",
    "validate_checkpoint_packs.py",
    "validate_planning_lifecycle.py",
    "validate_template_required_sections.py",
    "validate_prompt_ladder.py",
    "validate_prompt_metadata_schema.py",
    "validate_execution_context_pack_references.py",
    "validate_agent_metadata_schema.py",
    "validate_provider_settings_schema.py",
    "validate_generated_header_format.py",
    "validate_agent_runtime_drift.py",
    "sync_architecture_docs.py",
    "validate_repo_config.py",
}

@lru_cache(maxsize=64)
def _load_script_module(script_path: Path) -> ModuleType:
    module_name = f"_repo_contract_step_{script_path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load script module: {script_path.as_posix()}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def _run_script_main_in_process(script_path: Path, args: list[str], cwd: Path) -> int:
    module = _load_script_module(script_path)
    if not hasattr(module, "main"):
        raise RuntimeError(f"Script has no main(): {script_path.as_posix()}")
    main_callable = getattr(module, "main")
    original_cwd = Path.cwd()
    original_argv = sys.argv[:]
    try:
        os.chdir(cwd)
        sys.argv = [script_path.as_posix(), *args]
        parameter_count = len(inspect.signature(main_callable).parameters)
        if parameter_count == 0:
            result = main_callable()
        else:
            result = main_callable(args)
        return int(result) if isinstance(result, int) else 0
    finally:
        sys.argv = original_argv
        os.chdir(original_cwd)

def _can_run_in_process(command: list[str], repo_root_path: Path) -> bool:
    if len(command) < 2:
        return False
    python_exe = Path(command[0]).name.lower()
    if python_exe not in {"python", "python.exe", Path(sys.executable).name.lower()}:
        return False
    if command[1] == "-m":
        return False
    script_path = Path(command[1]).resolve()
    scripts_root = (repo_root_path / "scripts").resolve()
    try:
        script_path.relative_to(scripts_root)
    except ValueError:
        return False
    return script_path.name in IN_PROCESS_SCRIPT_NAMES

def run_step(command: list[str], *, cwd: Path) -> int:
    rendered = " ".join(command)
    print(f"> {rendered}")
    if _can_run_in_process(command, cwd):
        script_path = Path(command[1]).resolve()
        script_args = command[2:]
        return _run_script_main_in_process(script_path, script_args, cwd)
    completed = subprocess.run(command, cwd=cwd, check=False)
    return completed.returncode


def build_subprocess_steps(
    *,
    root: Path,
    python_executable: str,
    fast: bool,
    adoption_mode: str | None = None,
) -> list[list[str]]:
    adoption_shape_script = str(root / "scripts" / "validate_adoption_shape.py")
    checkpoint_pack_script = str(root / "scripts" / "validate_checkpoint_packs.py")
    planning_lifecycle_script = str(root / "scripts" / "validate_planning_lifecycle.py")
    template_sections_script = str(root / "scripts" / "validate_template_required_sections.py")
    prompt_ladder_script = str(root / "scripts" / "validate_prompt_ladder.py")
    prompt_metadata_schema_script = str(root / "scripts" / "validate_prompt_metadata_schema.py")
    context_pack_references_script = str(root / "scripts" / "validate_execution_context_pack_references.py")
    repo_config_script = str(root / "scripts" / "validate_repo_config.py")
    agent_metadata_schema_script = str(root / "scripts" / "validate_agent_metadata_schema.py")
    provider_settings_schema_script = str(root / "scripts" / "validate_provider_settings_schema.py")
    generated_header_script = str(root / "scripts" / "validate_generated_header_format.py")
    agent_runtime_drift_script = str(root / "scripts" / "validate_agent_runtime_drift.py")
    steps: list[list[str]] = [
        [python_executable, adoption_shape_script],
        [python_executable, checkpoint_pack_script],
        [python_executable, planning_lifecycle_script],
        [python_executable, template_sections_script],
        [python_executable, prompt_ladder_script],
        [python_executable, prompt_metadata_schema_script],
        [python_executable, context_pack_references_script],
        [python_executable, agent_metadata_schema_script],
        [python_executable, provider_settings_schema_script],
        [python_executable, generated_header_script],
    ]
    if adoption_mode is None:
        adoption_mode = read_adoption_mode(root)
    if adoption_mode != "starter_method_only":
        steps.append([python_executable, agent_runtime_drift_script, "--skip-deploy-check"])
    if adoption_mode != "starter_method_only":
        sync_script = str(root / "scripts" / "sync_architecture_docs.py")
        steps.append([python_executable, sync_script, "--check"])
    steps.append([python_executable, repo_config_script])
    if not fast:
        pytest_targets = [
            "tests/test_validate_repo_config.py",
            "tests/test_validate_planning_lifecycle.py",
            "tests/test_validate_repo_contracts.py",
        ]
        adoption_test = root / "tests" / "test_validate_adoption_shape.py"
        if adoption_test.exists():
            pytest_targets.insert(1, "tests/test_validate_adoption_shape.py")
        steps.append(
            [
                python_executable,
                "-m",
                "pytest",
                "--basetemp",
                pytest_basetemp(".tmp-tests/repo-contract-pytest"),
                *pytest_targets,
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
        start_count = text.count(GENERATED_HISTORY_START_MARKER)
        end_count = text.count(GENERATED_HISTORY_END_MARKER)
        human_count = text.count(HUMAN_NOTES_HEADING)

        if start_count != 1:
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message=(
                        "expected exactly one generated history start marker, "
                        f"found {start_count}"
                    ),
                )
            )
        if end_count != 1:
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message=(
                        "expected exactly one generated history end marker, "
                        f"found {end_count}"
                    ),
                )
            )
        if start_count != 1 or end_count != 1:
            continue

        start_index = text.index(GENERATED_HISTORY_START_MARKER)
        end_index = text.index(GENERATED_HISTORY_END_MARKER)
        if start_index > end_index:
            issues.append(
                ValidationIssue(
                    category="partial_generated_boundary_error",
                    path=rel_path,
                    message="generated history end marker appears before the start marker",
                )
            )
            continue

        after_end = text[end_index + len(GENERATED_HISTORY_END_MARKER) :].lstrip("\n")
        if not after_end.startswith(HUMAN_NOTES_HEADING):
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
                    message=(
                        "expected exactly one `## Human Notes` heading, "
                        f"found {human_count}"
                    ),
                )
            )
    return issues


def _starts_with_architecture_block(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped == ARCHITECTURE_METADATA_MARKER_LINE:
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
        return stripped[1:].lstrip() == SETUP_META_MARKER
    return False


def validate_required_metadata_coverage(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not managed_architecture_metadata_enabled(root):
        return issues

    components_root = root / "aml" / "components"
    if components_root.exists():
        for path in sorted(components_root.glob("*.yaml")):
            if not path.is_file():
                continue
            if not _starts_with_architecture_block(path.read_text(encoding="utf-8")):
                issues.append(
                    ValidationIssue(
                        category="missing_required_metadata",
                        path=relative_path(path, root),
                        message="AML component is missing required top-of-file `# @architecture` metadata",
                    )
                )

    configs_root = root / "configs"
    if configs_root.exists():
        for path in sorted(configs_root.glob("*.yaml")):
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
        python_executable=sys.executable,
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
