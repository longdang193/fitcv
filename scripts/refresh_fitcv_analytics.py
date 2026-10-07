"""Refresh FitCV analytics from one readonly snapshot and publish atomically."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.export_fitcv_analytics_source import export_bundle
from scripts.fitcv_analytics import rebuild_analytics_bundle, write_analytics_sqlite


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_json(value), encoding="utf-8")


def _release_is_valid(path: Path, manifest: dict[str, Any]) -> bool:
    required = ["source_bundle.json", "analytics.json", "analytics.sqlite3", "manifest.json"]
    if not path.is_dir() or any(not (path / name).is_file() for name in required):
        return False
    try:
        source_bundle = json.loads((path / "source_bundle.json").read_text(encoding="utf-8"))
        if not isinstance(source_bundle, dict):
            return False
        if source_bundle.get("database_sha256") != manifest["database_sha256"]:
            return False
        if source_bundle.get("input_fingerprint") != manifest["input_fingerprint"]:
            return False
        if json.loads((path / "manifest.json").read_text(encoding="utf-8")) != manifest:
            return False
        analytics = json.loads((path / "analytics.json").read_text(encoding="utf-8"))
        if analytics.get("material_metrics_sha256") != manifest["material_metrics_sha256"]:
            return False
        expected_metrics = analytics.get("gold", {}).get("gold_semantic_metric")
        if not isinstance(expected_metrics, list):
            return False
        connection = sqlite3.connect(path / "analytics.sqlite3")
        try:
            actual_metrics = [
                json.loads(row[0])
                for row in connection.execute(
                    "SELECT payload_json FROM gold_semantic_metric_rows ORDER BY rowid"
                )
            ]
            if actual_metrics != expected_metrics:
                return False
        finally:
            connection.close()
    except (OSError, sqlite3.Error, TypeError, ValueError, json.JSONDecodeError):
        return False
    return True


def refresh_analytics(
    database: Path,
    output_root: Path,
    *,
    source_commit: str,
    expected_database_sha256: str | None = None,
) -> dict[str, Any]:
    database = database.resolve()
    output_root = output_root.resolve()
    bundle = export_bundle(
        database,
        source_commit=source_commit,
        expected_database_sha256=expected_database_sha256,
    )
    output = rebuild_analytics_bundle(
        bundle,
        source_commit=source_commit,
        declared_input_fingerprint=bundle["input_fingerprint"],
        ingested_at=f"snapshot:{bundle['database_sha256']}",
    )
    material_digest = output["material_metrics_sha256"]
    manifest = {
        "schema_version": "fitcv.analytics.refresh.v1",
        "source_commit": source_commit,
        "database_sha256": bundle["database_sha256"],
        "input_fingerprint": bundle["input_fingerprint"],
        "material_metrics_sha256": material_digest,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    releases = output_root / "releases"
    releases.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".refresh-", dir=output_root.parent))
    try:
        _write(stage / "source_bundle.json", bundle)
        _write(stage / "analytics.json", output)
        write_analytics_sqlite(
            path=stage / "analytics.sqlite3",
            artifacts=output["gold"]["gold_cv_artifact"],
            run_jobs=output["gold"]["gold_run_job_effort"],
            cohorts=output["gold"]["gold_cohort_effort"],
            requirement_demand=output["gold"]["gold_requirement_demand"],
            candidate_gaps=output["gold"]["gold_candidate_gap"],
            acceptance=output["gold"]["gold_acceptance_state"],
            optimization=output["gold"]["gold_optimization_state"],
            semantic_metrics=output["gold"]["gold_semantic_metric"],
        )
        _write(stage / "manifest.json", manifest)
        if json.loads((stage / "analytics.json").read_text(encoding="utf-8"))["material_metrics_sha256"] != material_digest:
            raise ValueError("analytics_material_digest_mismatch")
        release = releases / f"{material_digest}-{bundle['database_sha256']}"
        if not _release_is_valid(release, manifest):
            current = output_root / "CURRENT.json"
            current_release: Path | None = None
            try:
                pointer = json.loads(current.read_text(encoding="utf-8"))
                current_release = output_root / str(pointer["release"])
            except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
            if current_release is not None and _release_is_valid(current_release, manifest):
                release = current_release
            else:
                staged_release = Path(tempfile.mkdtemp(prefix=".release-", dir=releases))
                try:
                    shutil.copytree(stage, staged_release, dirs_exist_ok=True)
                    if not _release_is_valid(staged_release, manifest):
                        raise ValueError("analytics_release_validation_failed")
                    release = staged_release
                except Exception:
                    shutil.rmtree(staged_release, ignore_errors=True)
                    raise
        release_reference = release.relative_to(output_root).as_posix()
        current = output_root / "CURRENT.json"
        pointer = output_root / f".CURRENT.{material_digest}.tmp"
        _write(pointer, {"release": release_reference, **manifest})
        os.replace(pointer, current)
    finally:
        if stage is not None and stage.exists():
            try:
                shutil.rmtree(stage)
            except PermissionError:
                pass
    return {"status": "ok", "release": release_reference, **manifest}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output-root", required=True, type=Path)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--expected-database-sha256")
    args = parser.parse_args()
    try:
        result = refresh_analytics(
            args.database,
            args.output_root,
            source_commit=args.source_commit,
            expected_database_sha256=args.expected_database_sha256,
        )
    except (FileNotFoundError, OSError, RuntimeError, ValueError) as exc:
        print(f"analytics_refresh_failed error={type(exc).__name__} detail={exc}")
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
