"""
@meta
name: validate_adoption_shape
type: script
domain: docs
responsibility:
  - Validate required Mode B repo surfaces for managed architecture metadata.
  - Detect missing feature/stage source files and root explanatory docs.
  - Fail when generated architecture docs are stale.
inputs:
  - repo_config/adoption-mode.yaml
  - docs/features/
  - docs/stages/
  - docs/generated/
  - docs/intent/
  - scripts/sync_architecture_docs.py
outputs:
  - stdout validation report
tags:
  - docs
  - architecture
  - ci-safe
lifecycle:
  status: active
"""

from __future__ import annotations

import argparse
import importlib.util
from pathlib import Path
from typing import Any, cast

import yaml


REQUIRED_DOC_PATHS = [
    "docs/setup.md",
    "docs/configuration.md",
    "docs/usage.md",
    "docs/pipeline.md",
    "docs/architecture.md",
    "docs/intent/README.md",
    "docs/intent/project-charter.md",
    "docs/intent/stakeholders.md",
    "docs/intent/success-outcomes.md",
    "docs/intent/constraints-and-non-goals.md",
]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate Mode B adoption shape.")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to this script's repo.",
    )
    return parser.parse_args(argv)


def read_yaml(path: Path) -> object:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def relpath(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def load_sync_module(sync_script_path: Path):
    spec = importlib.util.spec_from_file_location("sync_architecture_docs", sync_script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load sync script from {sync_script_path}.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_required_files(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for relative_path in REQUIRED_DOC_PATHS:
        target = repo_root / relative_path
        if not target.exists():
            errors.append(f"Missing required file: {relative_path}")
    return errors


def validate_features(repo_root: Path) -> list[str]:
    errors: list[str] = []
    for feature_dir in sorted((repo_root / "docs" / "features").iterdir()):
        if not feature_dir.is_dir():
            continue
        feature_id = feature_dir.name
        source_path = feature_dir / "feature.source.yaml"
        contract_path = feature_dir / f"{feature_id}.yaml"
        lineage_path = feature_dir / "lineage.generated.yaml"
        history_path = feature_dir / "history.md"
        if not source_path.exists():
            errors.append(f"Missing feature source: {relpath(source_path, repo_root)}")
        if not contract_path.exists():
            errors.append(f"Missing feature contract: {relpath(contract_path, repo_root)}")
        if not lineage_path.exists():
            errors.append(f"Missing feature lineage: {relpath(lineage_path, repo_root)}")
        if not history_path.exists():
            errors.append(f"Missing feature history: {relpath(history_path, repo_root)}")
    return errors


def validate_stages(repo_root: Path) -> list[str]:
    errors: list[str] = []
    stage_dir = repo_root / "docs" / "stages"
    stage_ids: set[str] = set()
    for contract_path in sorted(stage_dir.glob("*.yaml")):
        if contract_path.name.endswith(".source.yaml"):
            continue
        stage_ids.add(contract_path.stem)
    for source_path in sorted(stage_dir.glob("*.source.yaml")):
        stage_ids.add(source_path.name.replace(".source.yaml", ""))
    for stage_id in sorted(stage_ids):
        source_path = stage_dir / f"{stage_id}.source.yaml"
        contract_path = stage_dir / f"{stage_id}.yaml"
        if not source_path.exists():
            errors.append(f"Missing stage source: {relpath(source_path, repo_root)}")
        if not contract_path.exists():
            errors.append(f"Missing stage contract: {relpath(contract_path, repo_root)}")
    return errors


def validate_adoption_mode(repo_root: Path) -> list[str]:
    adoption_path = repo_root / "repo_config" / "adoption-mode.yaml"
    errors: list[str] = []
    if not adoption_path.exists():
        return ["Missing required file: repo_config/adoption-mode.yaml"]

    payload = cast(dict[str, Any], read_yaml(adoption_path))
    if payload.get("adoption_mode") != "managed_architecture_metadata":
        errors.append("adoption_mode must be `managed_architecture_metadata`.")
    if payload.get("managed_architecture_metadata") is not True:
        errors.append("managed_architecture_metadata must be true.")
    if payload.get("architecture_generator") != "scripts/sync_architecture_docs.py":
        errors.append("architecture_generator must be `scripts/sync_architecture_docs.py`.")

    starter_sync = cast(dict[str, Any], payload.get("starter_sync", {}))
    if not starter_sync.get("starter_baseline_ref"):
        errors.append("starter_sync.starter_baseline_ref is required.")
    if not starter_sync.get("last_shared_surface_review_at"):
        errors.append("starter_sync.last_shared_surface_review_at is required.")

    return errors


def validate_sync_freshness(repo_root: Path) -> list[str]:
    sync_script_path = repo_root / "scripts" / "sync_architecture_docs.py"
    if not sync_script_path.exists():
        return ["Missing required file: scripts/sync_architecture_docs.py"]

    sync_module = load_sync_module(sync_script_path)
    exit_code = sync_module.main(["--repo-root", str(repo_root), "--check"])
    if exit_code != 0:
        return ["Generated architecture docs are stale. Run scripts/sync_architecture_docs.py."]
    return []


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = args.repo_root.resolve()

    errors: list[str] = []
    errors.extend(validate_required_files(repo_root))
    errors.extend(validate_features(repo_root))
    errors.extend(validate_stages(repo_root))
    errors.extend(validate_adoption_mode(repo_root))
    if not errors:
        errors.extend(validate_sync_freshness(repo_root))

    if errors:
        for error in errors:
            print(error)
        return 1

    print("Mode B adoption shape is valid.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
