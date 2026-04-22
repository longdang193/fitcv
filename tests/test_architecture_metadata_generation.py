"""
@meta
name: test_architecture_metadata_generation
type: test
scope: unit
domain: docs
covers:
  - Direct architecture metadata generation helper write and check flows
  - Generator-side support for validate-only mode
tags:
  - fast
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
GENERATOR_PATH = REPO_ROOT / "tools" / "docs" / "generate_architecture_metadata.py"


def load_generator_module():
    spec = importlib.util.spec_from_file_location("generate_architecture_metadata", GENERATOR_PATH)
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
            "depends_on": [],
            "primary_features": ["cv_system"],
            "related_features": [],
            "inputs": ["ranked jobs"],
            "outputs": ["generation-ready jobs"],
        },
    )
    (repo_root / "docs" / "superpowers" / "archive" / "specs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "superpowers" / "archive" / "plans").mkdir(parents=True, exist_ok=True)
    (repo_root / "scripts").mkdir(parents=True, exist_ok=True)
    (repo_root / "tests").mkdir(parents=True, exist_ok=True)
    (repo_root / "config" / "runtime").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "generated").mkdir(parents=True, exist_ok=True)
    (repo_root / "scripts" / "cv_writer.py").write_text(
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
        "    return None\n",
        encoding="utf-8",
    )
    (repo_root / "tests" / "test_cv_writer.py").write_text(
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
        "prompts:\n  cv_generation:\n    structured_write:\n      prompt_id: cv_generation.structured_write.v1\n",
        encoding="utf-8",
    )
    return repo_root


def test_generator_writes_outputs_and_check_passes(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    generator = load_generator_module()

    assert generator.main(["--repo-root", str(repo_root)]) == 0
    history_text = (repo_root / "docs" / "features" / "cv_system" / "history.md").read_text(
        encoding="utf-8"
    )
    assert "<!-- GENERATED HISTORY START -->" in history_text
    assert "## Human Notes" in history_text
    assert "Legacy CV note." in history_text
    assert (repo_root / "docs" / "features" / "cv_system" / "cv_system.yaml").exists()
    assert (repo_root / "docs" / "features" / "cv_system" / "lineage.generated.yaml").exists()
    assert generator.main(["--repo-root", str(repo_root), "--check"]) == 0


def test_generator_validate_only_accepts_renderable_inputs(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    generator = load_generator_module()

    assert generator.main(["--repo-root", str(repo_root), "--validate-only"]) == 0


def test_generator_builds_history_from_completed_plan_metadata(tmp_path: Path) -> None:
    repo_root = build_repo(tmp_path)
    generator = load_generator_module()
    plan_path = (
        repo_root
        / "docs"
        / "superpowers"
        / "plans"
        / "2026-04-22-cv-system-history-rollup.md"
    )
    plan_path.parent.mkdir(parents=True, exist_ok=True)
    plan_path.write_text(
        "---\n"
        "artifact_type: plan\n"
        "status: completed\n"
        "related_features:\n"
        "  - cv_system\n"
        "completed_at: 2026-04-22T10:15:00+00:00\n"
        "change_id: phase-history-rollup\n"
        "verification:\n"
        "  - python scripts/sync_architecture_docs.py --check\n"
        "outcome:\n"
        "  summary: Regenerated the CV history surface.\n"
        "affects:\n"
        "  capabilities:\n"
        "    - cv_system.structured-cv-generation\n"
        "---\n\n"
        "# CV history rollup\n",
        encoding="utf-8",
    )

    assert generator.main(["--repo-root", str(repo_root)]) == 0

    history_text = (repo_root / "docs" / "features" / "cv_system" / "history.md").read_text(
        encoding="utf-8"
    )
    assert "## 2026-04-22" in history_text
    assert "### 2026-04-22-Cv-System-History-Rollup" not in history_text
    assert "### CV history rollup" in history_text
    assert (
        "Source plan: `docs/superpowers/plans/2026-04-22-cv-system-history-rollup.md`"
        in history_text
    )
    assert "- `cv_system.structured-cv-generation`" in history_text
    assert "- `python scripts/sync_architecture_docs.py --check`" in history_text
    assert "Regenerated the CV history surface." in history_text
