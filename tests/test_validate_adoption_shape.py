"""
@meta
type: test
scope: unit
domain: docs
covers:
  - option-b adoption-shape validation
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


REPO_ROOT = Path(__file__).resolve().parents[1]
SYNC_SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_architecture_docs.py"
VALIDATOR_PATH = REPO_ROOT / "scripts" / "validate_adoption_shape.py"


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


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
        "docs/setup.md": "# Setup\n",
        "docs/configuration.md": "# Configuration\n",
        "docs/usage.md": "# Usage\n",
        "docs/pipeline.md": "# Pipeline\n",
        "docs/architecture.md": "# Architecture\n",
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
                "starter_baseline_ref": "814e1a063541e79e6ca6e09268bfc5b81df057f2",
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
            "phase_7_direct_evidence_pilot": {
                "capabilities": {
                    "cv_system.structured-cv-generation": {
                        "require_code": True,
                        "require_tests": True,
                    }
                }
            },
        },
    )

    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "sync_architecture_docs.py").write_text(
        SYNC_SCRIPT_PATH.read_text(encoding="utf-8"),
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
        "# components:\n"
        "#   - config.runtime.prompts\n"
        "# role: config\n"
        "# canonical: true\n\n"
        "prompts:\n"
        "  cv_generation:\n"
        "    structured_write:\n"
        "      prompt_id: cv_generation.structured_write.v1\n",
        encoding="utf-8",
    )
    return repo_root


def test_validator_script_exists() -> None:
    assert VALIDATOR_PATH.exists(), "Expected scripts/validate_adoption_shape.py to exist."


def test_validator_passes_for_complete_repo(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")
    validator_module = load_module(VALIDATOR_PATH, "validate_adoption_shape")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    assert validator_module.main(["--repo-root", str(repo_root)]) == 0


def test_validator_fails_when_required_docs_are_missing(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    (repo_root / "docs" / "architecture.md").unlink()

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "missing required file" in process.stdout.lower()
    assert "docs/architecture.md" in process.stdout


def test_validator_fails_for_string_only_capabilities(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")
    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    feature_source_path = repo_root / "docs" / "features" / "cv_system" / "feature.source.yaml"
    payload = yaml.safe_load(feature_source_path.read_text(encoding="utf-8"))
    payload["capabilities"] = ["Structured CV Generation"]
    feature_source_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "must use structured capability entries" in process.stdout.lower()


def test_validator_fails_when_stage_participation_is_missing(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")
    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    source_path = repo_root / "docs" / "features" / "cv_system" / "feature.source.yaml"
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    payload.pop("stage_participation", None)
    source_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "must declare stage_participation" in process.stdout.lower()


def test_validator_fails_for_invalid_stage_participation_capability(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")
    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    source_path = repo_root / "docs" / "features" / "cv_system" / "feature.source.yaml"
    payload = yaml.safe_load(source_path.read_text(encoding="utf-8"))
    payload["stage_participation"][0]["capability_ids"] = ["cv_system.unknown-capability"]
    source_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "references unknown feature capability" in process.stdout.lower()


def test_validator_fails_for_non_underscore_feature_ids(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    feature_dir = repo_root / "docs" / "features" / "cv-system"
    feature_dir.mkdir(parents=True, exist_ok=True)
    write_yaml(
        feature_dir / "feature.source.yaml",
        {
            "feature_id": "cv-system",
            "name": "Bad Feature Id",
            "status": "active",
            "type": "add",
            "summary": "Invalid naming policy fixture.",
            "invariants": [],
            "domains": ["pipeline"],
            "depends_on": [],
            "capabilities": [
                {
                    "capability_id": "cv-system.bad-capability",
                    "statement": "Bad capability statement.",
                    "state": "active",
                }
            ],
        },
    )
    (feature_dir / "history.md").write_text("# History\n\n## Human Notes\nBad history note.\n", encoding="utf-8")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "invalid feature_id naming policy" in process.stdout.lower()


def test_validator_fails_for_legacy_lineage_schema(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage_path.write_text(
        yaml.safe_dump(
            {
                "feature_id": "cv_system",
                "source": "docs/features/cv_system/feature.source.yaml",
                "generated_contract": "docs/features/cv_system/cv_system.yaml",
                "capability_ids": ["cv_system.structured-cv-generation"],
                "capabilities": [],
                "refs_by_type": {},
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "legacy lineage keys are not allowed" in process.stdout.lower()


def test_validator_fails_when_lineage_contains_yaml_aliases(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage_path.write_text(
        lineage_path.read_text(encoding="utf-8").replace("evidence_gaps:", "evidence_gaps: &id001", 1).replace(
            "allowed_evidence_gaps:", "allowed_evidence_gaps: *id001", 1
        ),
        encoding="utf-8",
    )

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "yaml aliases are not allowed" in process.stdout.lower()


def test_validator_rejects_legacy_timeline_entry_shape(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage = yaml.safe_load(lineage_path.read_text(encoding="utf-8"))
    lineage["timeline"] = [{"kind": "plan", "path": "docs/superpowers/archive/plans/2026-04-22-cv-system-plan.md"}]
    lineage_path.write_text(yaml.safe_dump(lineage, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "is missing required keys" in process.stdout.lower()


def test_validator_accepts_empty_timeline_during_migration(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    plan_path = repo_root / "docs" / "superpowers" / "archive" / "plans" / "2026-04-22-cv-system-plan.md"
    plan_path.write_text(
        "---\n"
        "artifact_type: plan\n"
        "related_features:\n"
        "  - cv_system\n"
        "---\n\n"
        "# CV System Plan\n",
        encoding="utf-8",
    )

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    validator_module = load_module(VALIDATOR_PATH, "validate_adoption_shape")
    assert validator_module.main(["--repo-root", str(repo_root)]) == 0


def test_validator_fails_when_complete_lineage_lacks_direct_evidence(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage = yaml.safe_load(lineage_path.read_text(encoding="utf-8"))
    capability_lineage = lineage["capabilities"]["cv_system.structured-cv-generation"]
    capability_lineage["code"] = []
    capability_lineage["tests"] = []
    capability_lineage["completeness_status"] = "complete"
    lineage_path.write_text(yaml.safe_dump(lineage, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "complete lineage claims require direct code or test evidence" in process.stdout.lower()


def test_validator_fails_when_phase_7_pilot_lacks_required_test_evidence(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")
    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage = yaml.safe_load(lineage_path.read_text(encoding="utf-8"))
    lineage["capabilities"]["cv_system.structured-cv-generation"]["tests"] = []
    lineage_path.write_text(yaml.safe_dump(lineage, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "phase_7_direct_evidence_pilot requires test evidence" in process.stdout.lower()


def test_validator_fails_when_generated_outputs_are_stale(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    (repo_root / "docs" / "features" / "cv_system" / "cv_system.yaml").write_text(
        "stale: true\n", encoding="utf-8"
    )

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "generated architecture docs are stale" in process.stdout.lower()


def test_validator_fails_for_unknown_function_level_capability(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    script_path = repo_root / "scripts" / "cv_writer.py"
    script_path.write_text(
        script_path.read_text(encoding="utf-8").replace(
            "@capability cv_system.structured-cv-generation",
            "@capability cv_system.unknown-capability",
        ),
        encoding="utf-8",
    )

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "unknown @capability id" in process.stdout.lower()


def test_validator_fails_when_legacy_generated_discovery_remains(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    (repo_root / "docs" / "generated" / "features_index.yaml").write_text(
        "legacy: true\n", encoding="utf-8"
    )

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "legacy generated discovery output must be removed" in process.stdout.lower()


def test_validator_fails_when_required_script_metadata_is_missing(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    script_path = repo_root / "scripts" / "bootstrap_bigquery.py"
    script_path.write_text("#!/usr/bin/env python3\nprint('hi')\n", encoding="utf-8")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "missing required @meta docstring" in process.stdout.lower()
    assert "scripts/bootstrap_bigquery.py" in process.stdout


def test_validator_fails_when_required_test_metadata_is_missing(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    test_path = repo_root / "tests" / "test_sample.py"
    test_path.parent.mkdir(parents=True, exist_ok=True)
    test_path.write_text("def test_placeholder():\n    assert True\n", encoding="utf-8")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "missing required @meta docstring" in process.stdout.lower()
    assert "tests/test_sample.py" in process.stdout


def test_validator_fails_when_config_metadata_is_missing(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    config_path = repo_root / "config" / "runtime" / "prompts.yaml"
    config_path.write_text(
        "prompts:\n  cv_generation:\n    structured_write:\n      prompt_id: cv_generation.structured_write.v1\n",
        encoding="utf-8",
    )

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "missing required # @architecture metadata" in process.stdout.lower()
    assert "config/runtime/prompts.yaml" in process.stdout


def test_validator_fails_for_unknown_config_capability_id(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    config_path = repo_root / "config" / "runtime" / "prompts.yaml"
    config_path.write_text(
        config_path.read_text(encoding="utf-8").replace(
            "#   - cv_system.structured-cv-generation",
            "#   - cv_system.unknown-capability",
        ),
        encoding="utf-8",
    )

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "unknown config metadata capability id" in process.stdout.lower()
    assert "config/runtime/prompts.yaml" in process.stdout


def test_validator_accepts_rich_lineage_generated_shape(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 0


def test_validator_rejects_string_list_code_and_tests_in_lineage_generated(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage = yaml.safe_load(lineage_path.read_text(encoding="utf-8"))
    capability = lineage["capabilities"]["cv_system.structured-cv-generation"]
    capability["code"] = ["scripts/cv_writer.py"]
    capability["tests"] = ["tests/test_cv_writer.py"]
    lineage_path.write_text(yaml.safe_dump(lineage, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "lineage field code[0] must be a mapping" in process.stdout.lower()
    assert "lineage field tests[0] must be a mapping" in process.stdout.lower()


def test_validator_rejects_legacy_kind_path_timeline_entries(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    sync_module = load_module(SYNC_SCRIPT_PATH, "sync_architecture_docs")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    lineage_path = repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml"
    lineage = yaml.safe_load(lineage_path.read_text(encoding="utf-8"))
    lineage["timeline"] = [{"kind": "plan", "path": "docs/superpowers/archive/plans/2026-04-22-cv-system-plan.md"}]
    lineage_path.write_text(yaml.safe_dump(lineage, sort_keys=False), encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "feature lineage timeline entry 1 is missing required keys" in process.stdout.lower()
