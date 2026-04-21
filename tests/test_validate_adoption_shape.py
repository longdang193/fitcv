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
            "owner": "fitcv",
            "domains": ["pipeline"],
            "depends_on": [],
            "capabilities": [
                {
                    "capability_id": "cv_system.structured-cv-generation",
                    "name": "Structured CV Generation",
                    "summary": "Generate CV artifacts.",
                }
            ],
            "stage_participation": [
                {
                    "stage_id": "cv_analysis",
                    "role": "primary",
                    "capability_ids": ["cv_system.structured-cv-generation"],
                }
            ],
            "refs": {"history": ["docs/features/cv_system/history.md"]},
            "keywords": ["cv"],
        },
    )
    (repo_root / "docs" / "features" / "cv_system" / "history.md").write_text(
        "# CV System History\n", encoding="utf-8"
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
        },
    )

    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    (scripts_dir / "sync_architecture_docs.py").write_text(
        SYNC_SCRIPT_PATH.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    (repo_root / "docs" / "generated").mkdir(parents=True, exist_ok=True)
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

    feature_source_path = repo_root / "docs" / "features" / "cv_system" / "feature.source.yaml"
    payload = yaml.safe_load(feature_source_path.read_text(encoding="utf-8"))
    payload["capabilities"] = ["Structured CV Generation"]
    feature_source_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "must use structured capability entries" in process.stdout.lower()


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
            "owner": "fitcv",
            "domains": ["pipeline"],
            "depends_on": [],
            "capabilities": [
                {
                    "capability_id": "cv-system.bad-capability",
                    "name": "Bad Capability",
                }
            ],
            "refs": {"history": ["docs/features/cv-system/history.md"]},
            "keywords": ["bad"],
        },
    )
    (feature_dir / "history.md").write_text("# Bad Feature Id History\n", encoding="utf-8")

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0

    process = subprocess.run(
        [sys.executable, str(VALIDATOR_PATH), "--repo-root", str(repo_root)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "invalid feature_id naming policy" in process.stdout.lower()


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
