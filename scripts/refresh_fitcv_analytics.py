"""Refresh FitCV analytics from one readonly snapshot and publish atomically."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import shutil
import tempfile
from pathlib import Path
from typing import Any

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
        if json.loads((path / "manifest.json").read_text(encoding="utf-8")) != manifest:
            return False
        analytics = json.loads((path / "analytics.json").read_text(encoding="utf-8"))
        if analytics.get("material_metrics_sha256") != manifest["material_metrics_sha256"]:
            return False
        connection = sqlite3.connect(path / "analytics.sqlite3")
        try:
            connection.execute("SELECT 1 FROM gold_semantic_metric LIMIT 1").fetchone()
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
        release = releases / material_digest
        if not _release_is_valid(release, manifest):
            repaired_release = releases / f"{material_digest}.rebuild"
            if not _release_is_valid(repaired_release, manifest):
                if repaired_release.exists():
                    shutil.rmtree(repaired_release)
                shutil.copytree(stage, repaired_release)
            if not _release_is_valid(repaired_release, manifest):
                raise ValueError("analytics_release_validation_failed")
            release = repaired_release
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
