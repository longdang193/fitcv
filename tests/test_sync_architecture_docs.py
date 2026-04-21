"""
@meta
type: test
scope: unit
domain: docs
covers:
  - option-b phase-2 architecture sync rollout
excludes:
  - full code metadata backfill
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
SCRIPT_PATH = REPO_ROOT / "scripts" / "sync_architecture_docs.py"


def load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_architecture_docs", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_yaml(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def build_minimal_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    write_yaml(
        repo_root / "docs" / "features" / "cv_system" / "feature.source.yaml",
        {
            "feature_id": "cv_system",
            "name": "CV System",
            "status": "active",
            "type": "add",
            "summary": "Pilot source for CV generation lifecycle ownership.",
            "owner": "fitcv",
            "domains": ["pipeline", "cv_generation"],
            "depends_on": ["admin_control_plane_core"],
            "capabilities": [
                {
                    "capability_id": "cv_system.structured-cv-generation",
                    "name": "Structured CV Generation",
                    "summary": "Generate structured CV artifacts from grounded evidence.",
                }
            ],
            "stage_participation": [
                {
                    "stage_id": "cv_analysis",
                    "capability_ids": ["cv_system.structured-cv-generation"],
                    "role": "primary",
                }
            ],
            "refs": {
                "docs": ["docs/FitCV-pipeline.md"],
                "history": ["docs/features/cv_system/history.md"],
            },
            "keywords": ["cv", "generation"],
        },
    )
    write_yaml(
        repo_root / "docs" / "stages" / "cv_analysis.source.yaml",
        {
            "stage_id": "cv_analysis",
            "name": "CV Analysis",
            "summary": "Pilot source for the pre-generation evidence stage.",
            "depends_on": ["ranking"],
            "primary_features": ["cv_system"],
            "related_features": ["inspection_debugging"],
            "inputs": ["ranked jobs", "candidate profile"],
            "outputs": ["generation-ready jobs"],
        },
    )
    write_yaml(
        repo_root / "docs" / "features" / "admin_control_plane_core" / "feature.source.yaml",
        {
            "feature_id": "admin_control_plane_core",
            "name": "Admin Control Plane Core",
            "status": "active",
            "type": "add",
            "summary": "Own the admin API and web surface for pipeline operations.",
            "owner": "fitcv_cp",
            "domains": ["admin_ui"],
            "depends_on": [],
            "capabilities": ["FastAPI web server", "Jinja2 admin pages"],
            "refs": {
                "history": ["docs/features/admin_control_plane_core/history.md"],
            },
            "keywords": ["admin", "control-plane"],
        },
    )
    (repo_root / "docs" / "features" / "cv_system" / "history.md").write_text(
        "# CV System History\n", encoding="utf-8"
    )
    (repo_root / "docs" / "features" / "admin_control_plane_core" / "history.md").write_text(
        "# Admin Control Plane Core History\n", encoding="utf-8"
    )
    (repo_root / "docs" / "generated").mkdir(parents=True, exist_ok=True)
    return repo_root


def test_sync_script_exists() -> None:
    assert SCRIPT_PATH.exists(), "Expected scripts/sync_architecture_docs.py to exist."


def test_sync_script_writes_feature_and_stage_outputs(tmp_path: Path) -> None:
    repo_root = build_minimal_repo(tmp_path)
    sync_module = load_sync_module()

    exit_code = sync_module.main(["--repo-root", str(repo_root)])

    assert exit_code == 0

    feature_contract = read_yaml(repo_root / "docs" / "features" / "cv_system" / "cv_system.yaml")
    assert feature_contract["cv_system"]["name"] == "CV System"
    assert feature_contract["cv_system"]["capabilities"][0]["capability_id"] == (
        "cv_system.structured-cv-generation"
    )

    admin_contract = read_yaml(
        repo_root / "docs" / "features" / "admin_control_plane_core" / "admin_control_plane_core.yaml"
    )
    assert admin_contract["admin_control_plane_core"]["capabilities"] == [
        "FastAPI web server",
        "Jinja2 admin pages",
    ]

    lineage = read_yaml(repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml")
    assert lineage["feature_id"] == "cv_system"
    assert lineage["source"] == "docs/features/cv_system/feature.source.yaml"
    assert lineage["generated_contract"] == "docs/features/cv_system/cv_system.yaml"

    stage_contract = read_yaml(repo_root / "docs" / "stages" / "cv_analysis.yaml")
    assert stage_contract["cv_analysis"]["primary_features"] == ["cv_system"]


def test_sync_script_refreshes_full_discovery_suite(tmp_path: Path) -> None:
    repo_root = build_minimal_repo(tmp_path)
    sync_module = load_sync_module()

    exit_code = sync_module.main(["--repo-root", str(repo_root)])

    assert exit_code == 0

    features_index = read_yaml(repo_root / "docs" / "generated" / "features_index.yaml")
    feature_ids = [entry["feature_id"] for entry in features_index["features"]]
    assert feature_ids == ["admin_control_plane_core", "cv_system"]

    dependency_graph = read_yaml(repo_root / "docs" / "generated" / "feature_dependency_graph.yaml")
    assert dependency_graph["graph"]["admin_control_plane_core"]["used_by"] == ["cv_system"]

    capability_index = read_yaml(repo_root / "docs" / "generated" / "feature_capabilities_index.yaml")
    capability_names = [entry.get("capability_name", entry.get("capability")) for entry in capability_index["capabilities"]]
    assert "FastAPI web server" in capability_names
    assert "Structured CV Generation" in capability_names

    features_by_status = read_yaml(repo_root / "docs" / "generated" / "features_by_status.yaml")
    assert features_by_status["active"] == ["admin_control_plane_core", "cv_system"]

    feature_overview = (repo_root / "docs" / "generated" / "feature_overview.md").read_text(
        encoding="utf-8"
    )
    assert "`admin_control_plane_core`" in feature_overview
    assert "Own the admin API and web surface for pipeline operations." in feature_overview

    stages_index = read_yaml(repo_root / "docs" / "generated" / "stages_index.yaml")
    stage_ids = [entry["stage_id"] for entry in stages_index["stages"]]
    assert stage_ids == ["cv_analysis"]

    stage_overview = (repo_root / "docs" / "generated" / "stage_overview.md").read_text(encoding="utf-8")
    assert "`cv_analysis`" in stage_overview
    assert "Pilot source for the pre-generation evidence stage." in stage_overview


def test_sync_script_check_mode_detects_stale_outputs(tmp_path: Path) -> None:
    repo_root = build_minimal_repo(tmp_path)
    sync_module = load_sync_module()

    assert sync_module.main(["--repo-root", str(repo_root)]) == 0
    generated_contract = repo_root / "docs" / "features" / "cv_system" / "cv_system.yaml"
    generated_contract.write_text("stale: true\n", encoding="utf-8")

    process = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--repo-root", str(repo_root), "--check"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert process.returncode == 1
    assert "stale generated file" in process.stdout.lower()
