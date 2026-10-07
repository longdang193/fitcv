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
import uuid
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.export_fitcv_analytics_source import export_bundle
from scripts.fitcv_analytics import rebuild_analytics_bundle, write_analytics_sqlite


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _value_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _canonical_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    metric_registry = yaml.safe_load((REPO_ROOT / "config/analytics_metrics.yaml").read_text(encoding="utf-8")) or {}
    evidence_registry = yaml.safe_load((REPO_ROOT / "config/evidence_registry.yaml").read_text(encoding="utf-8")) or {}
    state = yaml.safe_load((REPO_ROOT / "config/acceptance_state.yaml").read_text(encoding="utf-8")) or {}
    claim_priority_map = metric_registry.get("claim_priority_map") or {}
    registry = {
        "metrics": metric_registry.get("metrics") or [],
        "records": [
            record
            for record in evidence_registry.get("records") or []
            if str(record.get("claim") or "") in claim_priority_map
        ],
        "claim_priority_map": claim_priority_map,
    }
    return json.loads(_json(registry)), json.loads(_json(state))


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
        if _value_digest(source_bundle.get("sources")) != manifest["input_fingerprint"]:
            return False
        expected_registry, expected_state = _canonical_inputs()
        if source_bundle.get("registry") != expected_registry or source_bundle.get("state") != expected_state:
            return False
        if json.loads((path / "manifest.json").read_text(encoding="utf-8")) != manifest:
            return False
        analytics = json.loads((path / "analytics.json").read_text(encoding="utf-8"))
        if not isinstance(analytics, dict):
            return False
        if analytics.get("material_metrics_sha256") != manifest["material_metrics_sha256"]:
            return False
        gold = analytics.get("gold")
        if not isinstance(gold, dict):
            return False
        if analytics.get("material_metrics_sha256") != _value_digest(gold):
            return False
        if manifest["material_metrics_sha256"] != _value_digest(gold):
            return False
        expected_tables = {
            "gold_cv_artifact": "silver_cv_artifact",
            "gold_run_job_effort": "silver_run_job_effort",
            "gold_cohort_effort": "silver_cohort_effort",
            "gold_requirement_demand": "silver_requirement_demand",
            "gold_candidate_gap": "silver_candidate_gap",
            "gold_acceptance_state": "silver_acceptance_evidence",
            "gold_optimization_state": "silver_optimization_state",
            "gold_semantic_metric": "gold_semantic_metric_rows",
        }
        expected_columns = {
            "gold_cv_artifact": ["run_job_id", "artifact_id", "accepted_at", "payload_json"],
            "gold_run_job_effort": ["run_job_id", "cohort_id", "accepted_artifact_count", "provider_call_count", "token_total", "payload_json"],
            "gold_cohort_effort": ["cohort_id", "cohort_type", "attempted_job_count", "accepted_artifact_count", "provider_call_count", "token_total", "payload_json"],
            "gold_requirement_demand": ["requirement", "cohort_id", "cohort_type", "numerator_posting_count", "denominator_posting_count", "payload_json"],
            "gold_candidate_gap": ["requirement", "gap_category", "cohort_id", "cohort_type", "numerator_requirement_count", "denominator_requirement_count", "payload_json"],
            "gold_acceptance_state": ["row_key", "priority", "evidence_id", "evidence_status", "implementation_status", "acceptance_status", "measurement_status", "payload_json"],
            "gold_optimization_state": ["row_key", "priority", "evidence_id", "measurement_status", "optimization_status", "optimization_experiment", "optimization_promotion", "optimization_production_default", "optimization_evidence", "payload_json"],
            "gold_semantic_metric": ["metric_id", "metric_version", "cohort_id", "cohort_type", "dimension_key", "numerator", "denominator", "value", "coverage_status", "coverage_numerator", "coverage_denominator", "unavailable_reason", "source_commit", "input_fingerprint", "material_digest", "payload_json"],
        }
        connection = sqlite3.connect(path / "analytics.sqlite3")
        try:
            for view_name, table_name in expected_tables.items():
                actual_columns = [row[1] for row in connection.execute(f"PRAGMA table_info({view_name})")]
                if actual_columns != expected_columns[view_name]:
                    return False
                expected_rows = gold.get(view_name)
                if not isinstance(expected_rows, list):
                    return False
                actual_rows = [
                    json.loads(row[0])
                    for row in connection.execute(
                        f"SELECT payload_json FROM {table_name} ORDER BY rowid"
                    )
                ]
                if actual_rows != expected_rows:
                    return False
                actual_view_rows = [
                    json.loads(row[0])
                    for row in connection.execute(f"SELECT payload_json FROM {view_name}")
                ]
                if sorted(map(_json, actual_view_rows)) != sorted(map(_json, expected_rows)):
                    return False
                projection_columns = expected_columns[view_name][:-1]
                for actual_row in connection.execute(f"SELECT * FROM {view_name}"):
                    payload = json.loads(actual_row[-1])
                    for index, column in enumerate(projection_columns):
                        actual_value = actual_row[index]
                        expected_value = payload.get(column)
                        if isinstance(expected_value, (dict, list)) and isinstance(actual_value, str):
                            try:
                                actual_value = json.loads(actual_value)
                            except json.JSONDecodeError:
                                return False
                        if actual_value != expected_value:
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
    registry, state = _canonical_inputs()
    bundle = {**bundle, "registry": registry, "state": state}
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
        pointer = output_root / f".CURRENT.{material_digest}.{uuid.uuid4().hex}.tmp"
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
