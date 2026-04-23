"""
@meta
type: test
scope: unit
domain: docs
covers:
  - starter-aligned adoption-shape validation
  - lineage generated contract enforcement
excludes:
  - repo-wide content completeness beyond required surfaces
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
import subprocess
import sys

import yaml


class IndentedSafeDumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False) -> object:
        return super().increase_indent(flow, False)


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_architecture_docs.py"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_adoption_shape.py"
GENERATOR_PATH = REPO_ROOT / "tools" / "docs" / "generate_architecture_metadata.py"
FORMATTER_PATH = REPO_ROOT / "scripts" / "format_contract_yaml.py"
AUDIT_PATH = REPO_ROOT / "scripts" / "audit_architecture_linkage.py"
GENERATED_HEADER = "# GENERATED FILE - do not edit directly.\n"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.dump(
            payload,
            Dumper=IndentedSafeDumper,
            sort_keys=False,
            default_flow_style=False,
            allow_unicode=False,
            width=10_000,
        ),
        encoding="utf-8",
    )


def build_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"

    write_yaml(
        repo_root / "docs" / "features" / "cv_system" / "feature.source.yaml",
        {
            "feature_id": "cv_system",
            "name": "CV System",
            "status": "active",
            "type": "add",
            "summary": "Own the CV-writing lifecycle.",
            "invariants": [],
            "domains": ["pipeline"],
            "depends_on": [],
            "capabilities": [
                {
                    "capability_id": "cv_system.structured-cv-generation",
                    "statement": "Generate CV artifacts.",
                    "state": "active",
                }
            ],
            "stage_participation": [
                {
                    "stage_id": "cv_analysis",
                    "role": "primary",
                    "capability_ids": ["cv_system.structured-cv-generation"],
                }
            ],
        },
    )
    (repo_root / "docs" / "features" / "cv_system" / "history.md").write_text(
        "# History\n\n## Human Notes\nLegacy CV note.\n", encoding="utf-8"
    )

    write_yaml(
        repo_root / "docs" / "stages" / "cv_analysis.source.yaml",
        {
            "stage_id": "cv_analysis",
            "name": "CV Analysis",
            "summary": "Prepare ranked jobs for writing.",
            "depends_on": ["ranking"],
            "primary_features": ["cv_system"],
            "related_features": [],
            "inputs": ["ranked jobs"],
            "outputs": ["generation-ready jobs"],
        },
    )

    for relative_path, content in {
        "docs/setup.md": (
            "---\n"
            "doc_id: setup\n"
            "doc_type: setup-guide\n"
            "explains:\n"
            "  features:\n"
            "    - cv_system\n"
            "  stages:\n"
            "    - cv_analysis\n"
            "---\n\n"
            "# Setup\n\n"
            "Install the required dependencies, confirm tool versions, provision prerequisites, and bootstrap in order.\n"
        ),
        "docs/configuration.md": (
            "---\n"
            "doc_id: configuration\n"
            "doc_type: operator-guide\n"
            "explains:\n"
            "  features:\n"
            "    - cv_system\n"
            "  configs:\n"
            "    - config/runtime/prompts.yaml\n"
            "---\n\n"
            "# Configuration\n\n"
            "Each environment variable and config file has profile defaults, override rules, ownership, and repo_config guidance.\n"
        ),
        "docs/usage.md": (
            "---\n"
            "doc_id: usage\n"
            "doc_type: operator-guide\n"
            "explains:\n"
            "  features:\n"
            "    - cv_system\n"
            "  stages:\n"
            "    - cv_analysis\n"
            "---\n\n"
            "# Usage\n\n"
            "Use the command entrypoint for the operator workflow, developer flow, and run loop.\n"
        ),
        "docs/pipeline.md": (
            "---\n"
            "doc_id: pipeline\n"
            "doc_type: architecture-guide\n"
            "explains:\n"
            "  stages:\n"
            "    - cv_analysis\n"
            "---\n\n"
            "# Pipeline\n\n"
            "The stage workflow documents the processing flow, sequence, handoff, and step order.\n"
        ),
        "docs/architecture.md": (
            "---\n"
            "doc_id: architecture\n"
            "doc_type: architecture-guide\n"
            "explains:\n"
            "  features:\n"
            "    - cv_system\n"
            "  stages:\n"
            "    - cv_analysis\n"
            "  components:\n"
            "    - src/fitcv\n"
            "---\n\n"
            "# Architecture\n\n"
            "The architecture captures each component boundary, integration point, information flow, and control flow.\n"
        ),
        "docs/intent/README.md": "# Intent\n",
        "docs/intent/project-charter.md": "# Project Charter\n",
        "docs/intent/stakeholders.md": "# Stakeholders\n",
        "docs/intent/success-outcomes.md": "# Success Outcomes\n",
        "docs/intent/constraints-and-non-goals.md": "# Constraints And Non-Goals\n",
    }.items():
        target = repo_root / relative_path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    write_yaml(
        repo_root / "repo_config" / "adoption-mode.yaml",
        {
            "adoption_mode": "managed_architecture_metadata",
            "managed_architecture_metadata": True,
            "legacy_feature_contracts": False,
            "architecture_generator": "scripts/sync_architecture_docs.py",
            "starter_sync": {
                "starter_baseline_ref": "a5d2d85b3174cde84f90df26642385b429e3c194",
                "last_shared_surface_review_at": "2026-04-22",
                "reviewed_surface_classes": [
                    "repo_config",
                    "operating_system_docs",
                    "skills",
                    "adapters",
                    "generated_instruction_surfaces",
                    "validation_and_sync_scripts",
                ],
                "divergences": [],
            },
        },
    )

    (repo_root / "docs" / "operating_system").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "superpowers" / "specs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "superpowers" / "plans").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "superpowers" / "archive" / "specs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "superpowers" / "archive" / "plans").mkdir(parents=True, exist_ok=True)

    (repo_root / "docs" / "superpowers" / "archive" / "specs" / "2026-04-22-cv-system-spec.md").write_text(
        "---\n"
        "artifact_type: spec\n"
        "related_features:\n"
        "  - cv_system\n"
        "---\n\n"
        "# CV System Spec\n",
        encoding="utf-8",
    )
    (repo_root / "docs" / "superpowers" / "archive" / "plans" / "2026-04-22-cv-system-plan.md").write_text(
        "---\n"
        "artifact_type: plan\n"
        "status: completed\n"
        "completed_at: 2026-04-22T20:45:00+02:00\n"
        "change_id: 2026-04-22-cv-system-lineage\n"
        "related_features:\n"
        "  - cv_system\n"
        "affects:\n"
        "  capabilities:\n"
        "    - cv_system.structured-cv-generation\n"
        "verification:\n"
        "  - pytest tests/test_cv_writer.py\n"
        "outcome:\n"
        "  summary: CV generation lineage metadata is now explicit.\n"
        "---\n\n"
        "# CV System Plan\n",
        encoding="utf-8",
    )

    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "validate_adoption_shape.py").write_text(
        VALIDATOR_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts_dir / "format_contract_yaml.py").write_text(
        FORMATTER_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts_dir / "audit_architecture_linkage.py").write_text(
        AUDIT_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (repo_root / "tools" / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "tools" / "docs" / "generate_architecture_metadata.py").write_text(
        GENERATOR_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (scripts_dir / "cv_writer.py").write_text(
        '"""\n'
        "@meta\n"
        "name: cv_writer\n"
        "type: script\n"
        "domain: cv_generation\n"
        "capabilities: []\n"
        '"""\n\n'
        "def build_cv() -> None:\n"
        '    """\n'
        "    @capability cv_system.structured-cv-generation\n"
        '    """\n'
        "    return None\n\n"
        "def main() -> None:\n"
        "    build_cv()\n"
        "    return None\n",
        encoding="utf-8",
    )

    tests_dir = repo_root / "tests"
    tests_dir.mkdir(parents=True, exist_ok=True)
    (tests_dir / "test_cv_writer.py").write_text(
        '"""\n'
        "@meta\n"
        "type: test\n"
        "scope: unit\n"
        "domain: cv_generation\n"
        '"""\n\n'
        "# @proves cv_system.structured-cv-generation\n"
        "def test_placeholder() -> None:\n"
        "    assert True\n",
        encoding="utf-8",
    )
    for test_name in (
        "test_architecture_metadata_generation.py",
        "test_architecture_linkage_audit.py",
        "test_format_contract_yaml.py",
        "test_validate_adoption_shape.py",
        "test_setup_hooks.py",
    ):
        (tests_dir / test_name).write_text(
            '"""\n@meta\ntype: test\nscope: unit\ndomain: docs\n"""\n\n'
            "def test_placeholder() -> None:\n"
            "    assert True\n",
            encoding="utf-8",
        )

    (repo_root / "docs" / "generated").mkdir(parents=True, exist_ok=True)
    (repo_root / "config" / "runtime").mkdir(parents=True, exist_ok=True)
    (repo_root / "config" / "runtime" / "prompts.yaml").write_text(
        "# @architecture\n"
        "# owner: cv_system\n"
        "# features:\n"
        "#   - cv_system\n"
        "# stages:\n"
        "#   - cv_analysis\n"
        "# capabilities:\n"
        "#   - cv_system.structured-cv-generation\n"
        "# role: config\n"
        "# canonical: true\n\n"
        "prompts:\n"
        "  cv_generation:\n"
        "    structured_write:\n"
        "      prompt_id: cv_generation.structured_write.v1\n",
        encoding="utf-8",
    )

    return repo_root


def run_validator(repo_root: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )


def read_lineage(repo_root: Path) -> tuple[str, dict[str, object]]:
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    text = lineage_path.read_text(encoding="utf-8")
    assert text.startswith(GENERATED_HEADER)
    return text, yaml.safe_load(text[len(GENERATED_HEADER) :])


def write_lineage(repo_root: Path, payload: dict[str, object]) -> None:
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage_path.write_text(GENERATED_HEADER + yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def test_validator_script_exists() -> None:
    assert VALIDATOR_PATH.exists(), "Expected scripts/validate_adoption_shape.py to exist."


def test_validator_passes_for_complete_repo(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    process = run_validator(repo_root)

    assert process.returncode == 0


def test_validator_fails_when_required_docs_are_missing(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    (repo_root / "docs" / "architecture.md").unlink()
    process = run_validator(repo_root)

    assert process.returncode == 1
    assert "missing required root project doc" in process.stdout.lower()
    assert "docs/architecture.md" in process.stdout


def test_validator_fails_when_required_doc_is_only_a_heading(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    (repo_root / "docs" / "setup.md").write_text("# Setup\n", encoding="utf-8")
    process = run_validator(repo_root)

    assert process.returncode == 1
    assert "required doc must contain more than a heading" in process.stdout.lower()


def test_validator_fails_when_managed_root_doc_frontmatter_is_missing(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    (repo_root / "docs" / "setup.md").write_text(
        "# Setup\n\nInstall the dependencies, confirm tool versions, provision prerequisites, and bootstrap.\n",
        encoding="utf-8",
    )
    process = run_validator(repo_root)

    assert process.returncode == 1
    assert "managed required root doc must include frontmatter metadata" in process.stdout.lower()


def test_validator_fails_when_managed_root_doc_metadata_is_not_linked(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    (repo_root / "docs" / "configuration.md").write_text(
        "---\n"
        "doc_id: configuration\n"
        "doc_type: operator-guide\n"
        "explains:\n"
        "  docs:\n"
        "    - docs/configuration.md\n"
        "---\n\n"
        "# Configuration\n\n"
        "Each environment variable and config file has profile defaults, override rules, ownership, and repo_config guidance.\n",
        encoding="utf-8",
    )
    process = run_validator(repo_root)

    assert process.returncode == 1
    assert "configuration doc must explain one or more features or configs" in process.stdout.lower()


def test_validator_accepts_rich_lineage_generated_shape(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    process = run_validator(repo_root)

    assert process.returncode == 0


def test_validator_rejects_lineage_without_generated_header(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    _text, payload = read_lineage(repo_root)
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    process = run_validator(repo_root)

    assert process.returncode == 1
    assert "lineage.generated.yaml must include the generated-file header" in process.stdout.lower()


def test_validator_rejects_string_list_code_and_tests_in_lineage_generated(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    _text, lineage = read_lineage(repo_root)
    capability = lineage["capabilities"]["cv_system.structured-cv-generation"]
    capability["code"] = ["scripts/cv_writer.py"]
    capability["tests"] = ["tests/test_cv_writer.py"]
    write_lineage(repo_root, lineage)
    process = run_validator(repo_root)

    assert process.returncode == 1
    assert "code[0] must be a mapping" in process.stdout.lower()
    assert "tests[0] must be a mapping" in process.stdout.lower()


def test_validator_rejects_legacy_kind_path_timeline_entries(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    _text, lineage = read_lineage(repo_root)
    lineage["timeline"] = [{"kind": "plan", "path": "docs/superpowers/archive/plans/2026-04-22-cv-system-plan.md"}]
    write_lineage(repo_root, lineage)
    process = run_validator(repo_root)

    assert process.returncode == 1
    assert "timeline[0] is missing required keys" in process.stdout.lower()
