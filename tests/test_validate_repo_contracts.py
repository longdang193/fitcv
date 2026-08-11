"""
@meta
name: test_validate_repo_contracts
type: test
scope: unit
domain: docs
covers:
  - Repo contract validator orchestration and fast-mode success on the current starter repo
tags:
  - fast
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_repo_contracts.py"
SCRIPTS_ROOT = str(REPO_ROOT / "scripts")

if SCRIPTS_ROOT not in sys.path:
    sys.path.insert(0, SCRIPTS_ROOT)


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load {path.name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


VALIDATOR = load_module("validate_repo_contracts", VALIDATOR_PATH)
ENV_GITIGNORE_VALIDATOR = load_module(
    "validate_env_gitignore_contract",
    REPO_ROOT / "scripts" / "validate_env_gitignore_contract.py",
)


def run_validator(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_validator_fast_mode_passes_for_current_repo() -> None:
    result = run_validator("--fast")

    assert result.returncode == 0
    assert "repo contract validation passed" in result.stdout.lower()


def test_main_propagates_subprocess_failure(monkeypatch) -> None:
    monkeypatch.setattr(
        VALIDATOR,
        "build_subprocess_steps",
        lambda *, root, python_executable, fast: [["python", "fake-step"]],
    )
    monkeypatch.setattr(VALIDATOR, "run_step", lambda command, cwd: 1)

    status = VALIDATOR.main(["--repo-root", str(REPO_ROOT), "--fast"])

    assert status == 1


def test_build_subprocess_steps_excludes_retired_metadata_validators() -> None:
    steps = VALIDATOR.build_subprocess_steps(
        root=REPO_ROOT,
        python_executable="python",
        fast=True,
    )

    rendered = [" ".join(step) for step in steps]

    assert any("validate_template_required_sections.py" in step for step in rendered)
    assert any("validate_prompt_metadata_schema.py" in step for step in rendered)
    assert any("validate_env_gitignore_contract.py" in step for step in rendered)
    assert any("validate_repo_config.py" in step for step in rendered)
    assert any("validate_harness_config.py" in step for step in rendered)
    assert any("render_harness_routing.py" in step for step in rendered)
    assert not any("validate_adoption_shape.py" in step for step in rendered)
    assert not any("validate_python_meta_headers.py" in step for step in rendered)


def test_package_dependent_validators_run_through_core_workspace() -> None:
    steps = VALIDATOR.build_subprocess_steps(
        root=REPO_ROOT,
        python_executable="python",
        fast=True,
    )

    package_steps = [
        step for step in steps
        if any(Path(part).name in VALIDATOR.PACKAGE_RUNTIME_SCRIPT_NAMES for part in step)
    ]

    assert package_steps
    assert all(step[:5] == ["uv", "run", "--package", "harness-core", "python"] for step in package_steps)


def test_full_contract_pytest_uses_core_runtime_resolver() -> None:
    steps = VALIDATOR.build_subprocess_steps(
        root=REPO_ROOT,
        python_executable="python",
        fast=False,
    )
    pytest_steps = [step for step in steps if "pytest" in step]

    assert pytest_steps
    assert pytest_steps == [[
        *VALIDATOR.harness_core_python(),
        "-m",
        "pytest",
        "--basetemp",
        VALIDATOR.pytest_basetemp(".tmp-tests/repo-contract-pytest"),
        "tests/test_validate_repo_config.py",
        "tests/test_validate_planning_lifecycle.py",
        "tests/test_validate_repo_contracts.py",
        "-q",
    ]]


def test_harness_shim_validation_rejects_core_implementation(tmp_path: Path) -> None:
    for relative_path, import_path in VALIDATOR.HARNESS_SHIM_IMPORTS.items():
        write_text(tmp_path / relative_path, f"from {import_path} import thing\n")

    assert VALIDATOR.validate_harness_shims(tmp_path) == []

    write_text(tmp_path / "scripts" / "harness_task.py", "def run_managed():\n    pass\n")

    issues = VALIDATOR.validate_harness_shims(tmp_path)

    assert any(issue.path == "scripts/harness_task.py" and "must delegate" in issue.message for issue in issues)


def test_starter_kit_classification_constants_match_contract() -> None:
    assert VALIDATOR.STARTER_KIT_DISTRIBUTION_TIER == "starter_kit"
    assert VALIDATOR.STARTER_KIT_CLASSIFICATION_ENFORCEMENT == "fail"


def test_validate_env_gitignore_contract_passes_with_required_entries(tmp_path: Path) -> None:
    write_text(
        tmp_path / ".gitignore",
        """.env
.env.*
!.env.example
*.private.*
*.local.*
""",
    )
    write_text(tmp_path / ".env.example", "API_KEY=placeholder\n")

    issues = ENV_GITIGNORE_VALIDATOR.validate_env_gitignore_contract(tmp_path)

    assert issues == []


def test_validate_env_gitignore_contract_reports_missing_entries(tmp_path: Path) -> None:
    write_text(tmp_path / ".gitignore", "node_modules/\n")
    write_text(tmp_path / ".env.example", "API_KEY=placeholder\n")

    issues = ENV_GITIGNORE_VALIDATOR.validate_env_gitignore_contract(tmp_path)

    assert "missing required .gitignore entry: .env" in issues
    assert "missing required .gitignore entry: .env.*" in issues
    assert "missing required .gitignore entry: *.private.*" in issues
    assert "missing required .gitignore entry: *.local.*" in issues
    assert "missing required .gitignore entry when .env.example exists: !.env.example" in issues


def test_starter_kit_classification_detects_missing_distribution_tier(tmp_path: Path) -> None:
    write_text(
        tmp_path / "repo_config" / "starter-kit-manifest.json",
        """{
  "copyPaths": ["scripts"]
}
""",
    )
    write_text(
        tmp_path / "scripts" / "demo.py",
        """\"\"\"
@meta
name: demo
type: script
\"\"\"
""",
    )

    issues = VALIDATOR.validate_starter_kit_classification(tmp_path)

    assert any("missing `distribution_tier: starter_kit`" in issue.message for issue in issues)


def test_starter_kit_classification_detects_out_of_manifest_tier(tmp_path: Path) -> None:
    write_text(
        tmp_path / "repo_config" / "starter-kit-manifest.json",
        """{
  "copyPaths": ["docs"]
}
""",
    )
    write_text(
        tmp_path / "scripts" / "demo.py",
        """\"\"\"
@meta
name: demo
type: script
distribution_tier: starter_kit
\"\"\"
""",
    )

    issues = VALIDATOR.validate_starter_kit_classification(tmp_path)

    assert any("not included in starter-kit manifest" in issue.message for issue in issues)


def test_starter_kit_classification_ignores_tmp_tests_tree(tmp_path: Path) -> None:
    write_text(
        tmp_path / "repo_config" / "starter-kit-manifest.json",
        """{
  "copyPaths": ["docs"]
}
""",
    )
    write_text(
        tmp_path / ".tmp-tests" / "scratch.py",
        """\"\"\"
@meta
name: scratch
type: script
distribution_tier: starter_kit
\"\"\"
""",
    )

    issues = VALIDATOR.validate_starter_kit_classification(tmp_path)

    assert issues == []
