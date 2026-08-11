"""
@meta
name: validate_repo_contracts
type: script
domain: docs
distribution_tier: starter_kit
responsibility:
  - Validate active repository contracts through one canonical command.
  - Orchestrate focused schema, planning, prompt, runtime, and repository checks.
inputs:
  - docs/superpowers/specs/*.md
  - docs/superpowers/plans/*.md
  - repo_config/*.json
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
import re
import subprocess
import sys
from types import ModuleType

import json

STARTER_KIT_CLASSIFICATION_ENFORCEMENT = "fail"
STARTER_KIT_DISTRIBUTION_TIER = "starter_kit"
HARNESS_SHIM_IMPORTS = {
    "scripts/harness_task.py": "harness_core_launcher",
    "scripts/plan_coordination.py": "harness_core.coordination",
    "scripts/planning_artifact_schema.py": "harness_core.planning_schema",
    "scripts/validate_harness_config.py": "harness_core_launcher",
}
PACKAGE_RUNTIME_SCRIPT_NAMES = {
    "validate_harness_config.py",
    "validate_planning_lifecycle.py",
    "validate_template_required_sections.py",
}


@dataclass(frozen=True)
class ValidationIssue:
    category: str
    path: str
    message: str


def validate_harness_shims(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    forbidden = re.compile(r"\bdef\s+(?:run_managed|resolve_managed_packet|resolve_task|verify_task|validate)\b|importlib\.util")
    for relative, expected_import in HARNESS_SHIM_IMPORTS.items():
        path = root / relative
        if not path.is_file():
            issues.append(ValidationIssue("harness_shim", relative, "missing shim"))
            continue
        source = path.read_text(encoding="utf-8")
        if expected_import not in source or forbidden.search(source):
            issues.append(ValidationIssue("harness_shim", relative, "must delegate to package without core implementation"))
    return issues


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def relative_path(path: Path, root: Path) -> str:
    return path.resolve().relative_to(root.resolve()).as_posix()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Validate active repository schemas, planning contracts, generated "
            "agent surfaces, and starter-kit classification."
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
        help="Run the hook-facing subset without validator-specific pytest.",
    )
    parser.add_argument(
        "--sync-starter-kit-tier",
        action="store_true",
        help=(
            "Auto-apply distribution_tier marker on metadata-capable manifest files "
            "before classification validation"
        ),
    )
    return parser


def pytest_basetemp(default_relative: str) -> str:
    override = os.environ.get("REPO_VALIDATOR_PYTEST_BASETEMP")
    if override:
        return override
    return default_relative


IN_PROCESS_SCRIPT_NAMES = {
    "validate_planning_lifecycle.py",
    "validate_template_required_sections.py",
    "validate_learning_materials_format.py",
    "validate_prompt_metadata_schema.py",
    "validate_agent_metadata_schema.py",
    "validate_generated_header_format.py",
    "validate_agent_runtime_drift.py",
    "validate_repo_config.py",
    "validate_harness_config.py",
    "render_harness_routing.py",
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


def harness_core_python() -> list[str]:
    return ["uv", "run", "--package", "harness-core", "python"]


def build_subprocess_steps(
    *,
    root: Path,
    python_executable: str,
    fast: bool,
) -> list[list[str]]:
    planning_lifecycle_script = str(root / "scripts" / "validate_planning_lifecycle.py")
    template_sections_script = str(root / "scripts" / "validate_template_required_sections.py")
    learning_format_script = str(root / "scripts" / "validate_learning_materials_format.py")
    prompt_metadata_schema_script = str(root / "scripts" / "validate_prompt_metadata_schema.py")
    repo_config_script = str(root / "scripts" / "validate_repo_config.py")
    harness_config_script = str(root / "scripts" / "validate_harness_config.py")
    harness_routing_script = str(root / "scripts" / "render_harness_routing.py")
    agent_metadata_schema_script = str(root / "scripts" / "validate_agent_metadata_schema.py")
    generated_header_script = str(root / "scripts" / "validate_generated_header_format.py")
    env_gitignore_contract_script = str(root / "scripts" / "validate_env_gitignore_contract.py")
    agent_runtime_drift_script = str(root / "scripts" / "validate_agent_runtime_drift.py")

    def package_runtime(script: str) -> list[str]:
        return [*harness_core_python(), script]

    steps: list[list[str]] = [
        package_runtime(planning_lifecycle_script),
        package_runtime(template_sections_script),
        [python_executable, learning_format_script],
        [python_executable, prompt_metadata_schema_script],
        [python_executable, agent_metadata_schema_script],
        [python_executable, generated_header_script],
        [python_executable, env_gitignore_contract_script],
        [python_executable, agent_runtime_drift_script, "--skip-deploy-check"],
    ]
    steps.append([python_executable, repo_config_script])
    steps.append([*package_runtime(harness_config_script), "--repo-root", str(root)])
    steps.append([python_executable, harness_routing_script, "--repo-root", str(root), "--check"])
    if not fast:
        pytest_targets = [
            "tests/test_validate_repo_config.py",
            "tests/test_validate_planning_lifecycle.py",
            "tests/test_validate_repo_contracts.py",
        ]
        steps.append(
            [
                *harness_core_python(),
                "-m",
                "pytest",
                "--basetemp",
                pytest_basetemp(".tmp-tests/repo-contract-pytest"),
                *pytest_targets,
                "-q",
            ]
        )
    return steps


def _load_starter_kit_manifest(root: Path) -> dict | None:
    path = root / "repo_config" / "starter-kit-manifest.json"
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else None


def _is_metadata_capable(path: Path) -> bool:
    analysis = _analyze_metadata_file(path)
    return analysis[0]


def _analyze_metadata_file(path: Path) -> tuple[bool, bool]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    is_metadata_capable = False
    if path.suffix == ".py":
        is_metadata_capable = "@meta" in "\n".join(text.splitlines()[:30])
    elif path.suffix == ".md":
        is_metadata_capable = text.startswith("---\n")
    has_starter_kit_tier = False
    if is_metadata_capable:
        pattern = re.compile(
            rf"^\s*(?:#\s*)?distribution_tier:\s*{re.escape(STARTER_KIT_DISTRIBUTION_TIER)}\s*$",
            re.MULTILINE,
        )
        has_starter_kit_tier = bool(pattern.search(text))
    return is_metadata_capable, has_starter_kit_tier


def _iter_files_pruned(root: Path) -> list[Path]:
    excluded_dirs = {
        ".git",
        ".worktrees",
        ".tmp-tests",
        "generated_exports",
        "generated_agents",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    }
    files: list[Path] = []
    for current_root, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in excluded_dirs]
        current_path = Path(current_root)
        for filename in filenames:
            files.append(current_path / filename)
    return files


def _has_distribution_tier(path: Path, tier: str) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    pattern = re.compile(
        rf"^\s*(?:#\s*)?distribution_tier:\s*{re.escape(tier)}\s*$",
        re.MULTILINE,
    )
    return bool(pattern.search(text))


def _has_starter_kit_distribution_tier_from_analysis(analysis: tuple[bool, bool]) -> bool:
    return analysis[1]


def sync_starter_kit_distribution_tier(root: Path) -> int:
    manifest = _load_starter_kit_manifest(root)
    if manifest is None:
        return 0

    copy_paths = manifest.get("copyPaths", [])
    if not isinstance(copy_paths, list):
        return 0

    in_kit: set[str] = set()
    for item in copy_paths:
        if not isinstance(item, str):
            continue
        rel = item.replace("\\", "/")
        target = root / rel
        if target.is_file():
            in_kit.add(rel)
        elif target.is_dir():
            for file in target.rglob("*"):
                if file.is_file():
                    in_kit.add(relative_path(file, root))

    patched = 0
    for rel in sorted(in_kit):
        if rel.startswith("docs/operating_system/templates/"):
            continue
        file_path = root / rel
        if not file_path.exists() or not _is_metadata_capable(file_path):
            continue
        if _has_distribution_tier(file_path, STARTER_KIT_DISTRIBUTION_TIER):
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        if file_path.suffix == ".md":
            lines = text.splitlines()
            if lines and lines[0].strip() == "---":
                try:
                    end = lines.index("---", 1)
                except ValueError:
                    continue
                lines.insert(end, f"distribution_tier: {STARTER_KIT_DISTRIBUTION_TIER}")
                file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                patched += 1
        elif file_path.suffix == ".py":
            if "@meta" in text and "distribution_tier:" not in text:
                lines = text.splitlines()
                for idx, line in enumerate(lines[:30]):
                    if line.strip().startswith("#") and "@meta" in line:
                        insert_at = idx + 1
                        while insert_at < len(lines) and lines[insert_at].strip().startswith("#"):
                            if "distribution_tier:" in lines[insert_at]:
                                break
                            insert_at += 1
                        else:
                            lines.insert(insert_at, f"# distribution_tier: {STARTER_KIT_DISTRIBUTION_TIER}")
                            file_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                            patched += 1
                        break
    return patched


def validate_starter_kit_classification(root: Path) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    manifest = _load_starter_kit_manifest(root)
    if manifest is None:
        return issues

    copy_paths = manifest.get("copyPaths", [])
    if not isinstance(copy_paths, list):
        return issues

    in_kit: set[str] = set()
    for item in copy_paths:
        if not isinstance(item, str):
            continue
        rel = item.replace("\\", "/")
        target = root / rel
        if target.is_file():
            in_kit.add(rel)
        elif target.is_dir():
            for file in target.rglob("*"):
                if file.is_file():
                    in_kit.add(relative_path(file, root))

    for rel in sorted(in_kit):
        if rel.startswith("docs/operating_system/templates/"):
            continue
        file_path = root / rel
        if not file_path.exists():
            continue
        analysis = _analyze_metadata_file(file_path)
        if not analysis[0]:
            continue
        if _has_starter_kit_distribution_tier_from_analysis(analysis):
            continue
        issues.append(
            ValidationIssue(
                category="starter_kit_classification_drift",
                path=rel,
                message=(
                    "metadata-capable file is in starter-kit manifest but missing "
                    f"`distribution_tier: {STARTER_KIT_DISTRIBUTION_TIER}`"
                ),
            )
        )

    for path in _iter_files_pruned(root):
        if not path.is_file():
            continue
        analysis = _analyze_metadata_file(path)
        if not analysis[0]:
            continue
        rel = relative_path(path, root)
        if rel in in_kit:
            continue
        if _has_starter_kit_distribution_tier_from_analysis(analysis):
            issues.append(
                ValidationIssue(
                    category="starter_kit_classification_drift",
                    path=rel,
                    message=(
                        "file declares starter-kit distribution tier but is not included "
                        "in starter-kit manifest copyPaths"
                    ),
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

    if args.sync_starter_kit_tier:
        patched = sync_starter_kit_distribution_tier(root)
        if patched:
            print(f"Starter-kit distribution tier sync patched {patched} file(s).")

    classification_issues = [*validate_starter_kit_classification(root), *validate_harness_shims(root)]

    if classification_issues:
        if STARTER_KIT_CLASSIFICATION_ENFORCEMENT == "fail":
            return report_issues(classification_issues)
        print("Repo contract warning:")
        for issue in classification_issues:
            print(f"- {issue.category}: {issue.path} - {issue.message}")

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
