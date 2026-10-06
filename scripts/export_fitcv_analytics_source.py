"""Export sanitized FitCV operational state into a deterministic analytics bundle."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = REPO_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from fitcv_cp.sqlite_store import open_readonly_snapshot
from fitcv.candidate import canonical_candidate_checksum


EXPORT_SCHEMA_VERSION = "fitcv.analytics.source.v1"
_SECRET_PARTS = (
    "api_key", "apikey", "authorization", "credential", "password", "secret",
    "access_token", "refresh_token", "private_key", "content_blob", "cv_markdown",
    "cv_structured_json", "prompt", "message",
)
_REQUIRED_ID_FIELDS = {
    "posting_inventory": "posting_id",
    "posting_requirement": "requirement_instance_id",
    "candidate_profile_revision": "candidate_profile_id",
    "generation_attempt": "generation_attempt_id",
    "provider_attempt": "provider_attempt_id",
    "review_action": "review_action_id",
    "accepted_artifact": "artifact_id",
    "artifact": "artifact_id",
    "render_proof": "render_proof_id",
}
_SECRET_QUERY_PARTS = {
    "access_token", "api_key", "apikey", "authorization", "client_secret",
    "id_token", "password", "refresh_token", "secret", "signature", "sig", "token",
}
_SAFE_TELEMETRY_FIELDS = {"prompt_tokens", "completion_tokens", "input_tokens", "output_tokens", "total_tokens", "token_total"}


def _digest_bytes(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(value: Any) -> Any:
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _sanitize_string(value: str) -> str:
    if not ("://" in value or value.startswith("//") or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:/", value)):
        return value
    try:
        parts = urlsplit(value)
    except ValueError:
        return "[redacted-url]"
    if not parts.netloc:
        return "[redacted-url]"
    invalid_port = False
    try:
        hostname = parts.hostname or ""
        port = parts.port
    except ValueError:
        hostname = ""
        port = None
        invalid_port = True
    host = f"[{hostname}]" if ":" in hostname and not hostname.startswith("[") else hostname
    if host and port is not None and not invalid_port:
        host = f"{host}:{port}"
    if not host:
        host = "[redacted-host]"
    try:
        query = urlencode([
            (key, item)
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
            if key.lower() not in _SECRET_QUERY_PARTS
            and not any(secret in key.lower() for secret in ("auth", "credential", "secret", "token", "password", "signature"))
        ])
    except ValueError:
        query = ""
    return urlunsplit((parts.scheme, host, parts.path, query, ""))


def _sanitize(value: Any, *, key: str = "") -> Any:
    lowered = key.lower()
    if lowered not in _SAFE_TELEMETRY_FIELDS and any(part in lowered for part in _SECRET_PARTS):
        return None
    if isinstance(value, dict):
        return {
            str(name): sanitized
            for name, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if (sanitized := _sanitize(item, key=str(name))) is not None
        }
    if isinstance(value, list):
        return [_sanitize(item, key=key) for item in value]
    if isinstance(value, (bytes, bytearray, memoryview)):
        return None
    if isinstance(value, str):
        return _sanitize_string(value)
    return value


def _run_debug_payload(row: Any) -> dict[str, Any]:
    compatibility = _json(row["compatibility_json"] if "compatibility_json" in row.keys() else None)
    compatibility = compatibility if isinstance(compatibility, dict) else {}
    raw = compatibility.get("cv_generation_debug_json")
    if raw is None and "cv_generation_debug_json" in row.keys():
        raw = row["cv_generation_debug_json"]
    payload = _json(raw)
    return payload if isinstance(payload, dict) else {}


def _table_exists(connection: Any, table: str) -> bool:
    return connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
    ).fetchone() is not None


def _flatten_debug_values(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        for item in value:
            yield from _flatten_debug_values(item)
        return
    if not isinstance(value, dict):
        return
    if any(str(key) in value for key in ("artifact_id", "artifact_version_id", "version_id", "cv_version_id", "run_job_id")):
        yield value
    for key in (
        "records", "debug_records", "cv_generation_debug_records", "accepted_artifact_events",
        "accepted_cv_effort", "cv_generation_trace",
    ):
        if key in value:
            yield from _flatten_debug_values(value[key])


def _debug_records(run_rows: Iterable[Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for row in run_rows:
        parsed = _run_debug_payload(row)
        for source_key in ("debug_records", "cv_generation_debug_records", "accepted_artifact_events", "accepted_cv_effort", "cv_generation_trace"):
            for value in _flatten_debug_values(parsed.get(source_key) or []):
                value = dict(value)
                if source_key == "accepted_artifact_events":
                    value["_accepted_event"] = True
                trace = value.get("cv_generation_trace")
                if isinstance(trace, dict):
                    summary = trace.get("efficiency_summary") or {}
                    if isinstance(summary, dict):
                        value = {**value, **summary}
                sanitized = _sanitize(value) or {}
                for identifier in (
                    value.get("artifact_id"), value.get("artifact_version_id"),
                    value.get("version_id"), value.get("cv_version_id"), value.get("run_job_id"),
                ):
                    if str(identifier or "").strip():
                        key = str(identifier)
                        records[key] = {**records.get(key, {}), **sanitized}
    return records


def _debug_number(debug: dict[str, Any], field: str) -> Any:
    candidates = [debug, debug.get("efficiency"), debug.get("efficiency_summary")]
    trace = debug.get("cv_generation_trace")
    if isinstance(trace, dict):
        candidates.append(trace.get("efficiency_summary"))
    for candidate in candidates:
        if isinstance(candidate, dict) and candidate.get(field) is not None:
            return candidate[field]
    if field == "token_total":
        def token_number(value: Any) -> int | None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            try:
                numeric = float(value)
            except (OverflowError, ValueError):
                return None
            return int(numeric) if math.isfinite(numeric) and numeric >= 0 and numeric.is_integer() else None

        def usage_total(usage: Any) -> int | None:
            if not isinstance(usage, dict):
                return None
            for key in ("total_tokens", "token_total"):
                if key in usage:
                    return token_number(usage[key])
            for left, right in (("prompt_tokens", "completion_tokens"), ("input_tokens", "output_tokens")):
                if left in usage and right in usage:
                    left_value = token_number(usage[left])
                    right_value = token_number(usage[right])
                    return left_value + right_value if left_value is not None and right_value is not None else None
            return None

        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            usage = candidate.get("token_usage") or candidate.get("usage")
            if isinstance(usage, list) and usage:
                totals = [usage_total(block) for block in usage]
                expected_calls = token_number(candidate.get("provider_call_count"))
                if expected_calls is not None and expected_calls != len(usage):
                    continue
                if all(total is not None for total in totals):
                    return sum(total for total in totals if total is not None)
            elif isinstance(usage, dict):
                total = usage_total(usage)
                if total is not None:
                    return total
    return None


def _debug_attempt_count(debug: dict[str, Any], fallback: int) -> int:
    value = _debug_number(debug, "attempt_count")
    if value is None and isinstance(debug.get("attempts"), list):
        value = len(debug["attempts"])
    try:
        return max(1, int(value)) if value is not None else max(1, fallback)
    except (TypeError, ValueError):
        return max(1, fallback)


def _append(sources: dict[str, list[dict[str, Any]]], kind: str, row: dict[str, Any]) -> None:
    required = _REQUIRED_ID_FIELDS.get(kind)
    if required and not str(row.get(required) or "").strip():
        raise ValueError(f"source_identity_missing:{kind}")
    sources.setdefault(kind, []).append(_sanitize(row) or {})


def collect_source(connection: Any) -> dict[str, list[dict[str, Any]]]:
    """Collect only analytics-owned fields from one explicit read transaction."""
    sources: dict[str, list[dict[str, Any]]] = {}
    if not _table_exists(connection, "pipeline_runs"):
        raise ValueError("analytics_source_table_missing:pipeline_runs")
    runs = connection.execute("SELECT * FROM pipeline_runs ORDER BY run_id").fetchall()
    run_by_id = {str(row["run_id"]): row for row in runs}
    debug_by_artifact = _debug_records(runs)

    if _table_exists(connection, "run_inputs"):
        for row in connection.execute("SELECT * FROM run_inputs ORDER BY run_id"):
            profile_json = _json(row["candidate_profile_json"] if "candidate_profile_json" in row.keys() else None)
            profile_fingerprint = row["candidate_profile_checksum"] if "candidate_profile_checksum" in row.keys() else None
            if not profile_fingerprint and isinstance(profile_json, dict):
                try:
                    profile_fingerprint = canonical_candidate_checksum(profile_json)
                except (TypeError, ValueError, KeyError):
                    profile_fingerprint = None
            _append(sources, "candidate_profile_revision", {
                "source_id": f"{row['run_id']}:candidate-profile",
                "candidate_profile_id": row["candidate_profile_id"],
                "candidate_profile_revision": row["candidate_profile_revision"],
                "candidate_profile_revision_id": row["candidate_profile_revision_id"],
                "candidate_profile_fingerprint": profile_fingerprint,
                "profile_schema_version": row["candidate_profile_schema_version"],
                "run_id": row["run_id"],
                "observed_at": row["created_at"],
            })

    jobs = []
    if _table_exists(connection, "run_jobs"):
        jobs = connection.execute("SELECT * FROM run_jobs ORDER BY run_job_id").fetchall()
    for row in jobs:
        run = run_by_id.get(str(row["run_id"]))
        run_payload = _json(run["compatibility_json"] if run is not None and "compatibility_json" in run.keys() else None)
        run_payload = run_payload if isinstance(run_payload, dict) else {}
        snapshot = _json(row["source_snapshot_json"])
        snapshot = snapshot if isinstance(snapshot, dict) else {}
        cohort_id = run_payload.get("cohort_id") or "operational"
        cohort_type = run_payload.get("cohort_type") or "imported"
        inventory = {
            "source_id": row["run_job_id"],
            "posting_id": row["run_job_id"],
            "run_id": row["run_id"],
            "run_job_id": row["run_job_id"],
            "cohort_id": cohort_id,
            "cohort_type": cohort_type,
            "eligible": True,
            "extraction_status": snapshot.get("extraction_status") or "unknown",
            "source": row["source_url"],
            "source_fingerprint": row["source_fingerprint"],
            "title": row["title"],
            "company": row["company"],
            "collected_at": run["created_at"] if run is not None else None,
        }
        _append(sources, "posting_inventory", inventory)
        requirements = snapshot.get("requirements") or snapshot.get("requirement_coverage") or []
        if isinstance(requirements, dict):
            requirements = list(requirements.values())
        for index, item in enumerate(requirements):
            requirement = item if isinstance(item, str) else item.get("requirement") if isinstance(item, dict) else None
            if not str(requirement or "").strip():
                continue
            _append(sources, "posting_requirement", {
                "source_id": f"{row['run_job_id']}:requirement:{index}",
                "requirement_instance_id": f"{row['run_job_id']}:{index}",
                "posting_id": row["run_job_id"],
                "run_job_id": row["run_job_id"],
                "requirement": str(requirement),
                "cohort_id": cohort_id,
                "cohort_type": cohort_type,
                "eligible": True,
                "extraction_status": inventory["extraction_status"],
                "source": row["source_url"],
            })

    versions = []
    if _table_exists(connection, "cv_versions"):
        versions = connection.execute("SELECT * FROM cv_versions ORDER BY version_id").fetchall()
    versions_by_run_job: dict[str, list[str]] = {}
    for version in versions:
        versions_by_run_job.setdefault(str(version["run_job_id"] or ""), []).append(str(version["version_id"]))
    for row in versions:
        version_id = str(row["version_id"])
        run_job_id = str(row["run_job_id"] or "")
        ordinal = int(row["ordinal"] or 0)
        status = str(row["generation_status"] or "").lower()
        artifact_debug = debug_by_artifact.get(version_id, {})
        job_debug = (
            debug_by_artifact.get(run_job_id, {})
            if len(versions_by_run_job.get(run_job_id, [])) == 1
            else {}
        )
        debug = {**job_debug, **artifact_debug}
        run = run_by_id.get(str(row["run_id"]))
        run_payload = _json(run["compatibility_json"] if run is not None and "compatibility_json" in run.keys() else None)
        run_payload = run_payload if isinstance(run_payload, dict) else {}
        common = {
            "run_job_id": run_job_id,
            "run_id": row["run_id"],
            "cohort_id": run_payload.get("cohort_id") or "operational",
            "cohort_type": run_payload.get("cohort_type") or "imported",
            "observed_at": row["created_at"],
        }
        normalized_status = "succeeded" if status == "generated" else status
        attempt_count = _debug_attempt_count(debug, ordinal or 1)
        provider_call_count = _debug_number(debug, "provider_call_count")
        token_total = _debug_number(debug, "token_total")
        accepted_event = bool(
            artifact_debug.get("_accepted_event")
            or artifact_debug.get("accepted_outcome") is True
            or str(artifact_debug.get("final_status") or "").lower() == "accepted"
        )
        _append(sources, "generation_attempt", {
            **common,
            "source_id": version_id,
            "generation_attempt_id": version_id,
            "attempt_count": attempt_count,
            "version_ordinal": ordinal or 1,
            "status": normalized_status,
        })
        _append(sources, "provider_attempt", {
            **common,
            "source_id": f"{version_id}:provider",
            "provider_attempt_id": f"{version_id}:provider",
            "provider_call_count": provider_call_count,
            "token_total": token_total,
            "status": normalized_status,
        })
        if status == "generated" and accepted_event and row["content_checksum"] and row["content_length"] is not None:
            artifact = {
                **common,
                "source_id": version_id,
                "artifact_id": version_id,
                "run_job_id": run_job_id,
                "status": "accepted",
                "accepted_at": row["finished_at"] or row["created_at"],
                "durable": True,
                "generation_attempt": attempt_count,
                "version_ordinal": ordinal or 1,
                "regeneration": attempt_count > 1,
                "content_checksum": row["content_checksum"],
                "content_length": row["content_length"],
                "render_acceptance": artifact_debug.get("render_acceptance"),
            }
            _append(sources, "accepted_artifact", artifact)
            _append(sources, "artifact", artifact)
            if isinstance(debug.get("render_acceptance"), dict):
                _append(sources, "render_proof", {
                    **common,
                    "source_id": f"{version_id}:render",
                    "render_proof_id": f"{version_id}:render",
                    "artifact_id": version_id,
                    **debug["render_acceptance"],
                })

    if _table_exists(connection, "cv_review_events"):
        version_by_id = {str(item["version_id"]): item for item in versions}
        for row in connection.execute("SELECT * FROM cv_review_events ORDER BY review_event_id"):
            version = version_by_id.get(str(row["cv_version_id"]))
            if version is None:
                raise ValueError("source_identity_missing:review_action")
            run = run_by_id.get(str(version["run_id"]))
            run_payload = _json(run["compatibility_json"] if run is not None and "compatibility_json" in run.keys() else None)
            run_payload = run_payload if isinstance(run_payload, dict) else {}
            _append(sources, "review_action", {
                "source_id": row["review_event_id"],
                "review_action_id": row["review_event_id"],
                "run_id": version["run_id"],
                "run_job_id": version["run_job_id"],
                "cv_version_id": row["cv_version_id"],
                "action": row["to_state"],
                "cohort_id": run_payload.get("cohort_id") or "operational",
                "cohort_type": run_payload.get("cohort_type") or "imported",
                "observed_at": row["created_at"],
            })
    if _table_exists(connection, "requirement_resolutions"):
        for row in connection.execute("SELECT * FROM requirement_resolutions ORDER BY resolution_id"):
            _append(sources, "review_action", {
                "source_id": row["resolution_id"],
                "review_action_id": row["resolution_id"],
                "action": row["resolution_action"],
                "candidate_profile_id": row["candidate_profile_id"],
                "candidate_profile_revision": row["candidate_profile_revision"],
                "requirement_instance_id": row["requirement_instance_id"],
                "observed_at": row["updated_at"],
            })
    return {
        kind: sorted(rows, key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")))
        for kind, rows in sorted(sources.items())
    }


def export_bundle(database: Path, *, source_commit: str, expected_database_sha256: str | None = None) -> dict[str, Any]:
    database = database.resolve()
    before_hash = _digest_bytes(database)
    if expected_database_sha256 and before_hash != expected_database_sha256:
        raise ValueError("source_hash_mismatch")
    with open_readonly_snapshot(database) as connection:
        sources = collect_source(connection)
    after_hash = _digest_bytes(database)
    if before_hash != after_hash:
        raise RuntimeError("source_hash_changed")
    input_fingerprint = hashlib.sha256(
        json.dumps(sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema_version": EXPORT_SCHEMA_VERSION,
        "source_commit": source_commit,
        "input_fingerprint": input_fingerprint,
        "database_sha256": before_hash,
        "sources": sources,
        "registry": {},
        "state": {},
    }


def export_to_path(
    database: Path,
    output: Path,
    *,
    source_commit: str,
    expected_database_sha256: str | None = None,
) -> dict[str, Any]:
    database = database.resolve()
    output = output.resolve()
    source_files = [database, Path(f"{database}-wal"), Path(f"{database}-shm")]
    if output in source_files or any(
        output.exists() and source.exists() and os.path.samefile(output, source)
        for source in source_files
    ):
        raise ValueError("analytics_source_output_aliases_database")
    bundle = export_bundle(
        database,
        source_commit=source_commit,
        expected_database_sha256=expected_database_sha256,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(bundle, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return bundle


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--source-commit", default=None)
    parser.add_argument("--expected-database-sha256")
    args = parser.parse_args()
    try:
        bundle = export_bundle(
            args.database,
            source_commit=args.source_commit or _git_commit(),
            expected_database_sha256=args.expected_database_sha256,
        )
    except (FileNotFoundError, RuntimeError, ValueError, OSError) as exc:
        print(f"analytics_source_export_failed error={type(exc).__name__} detail={exc}", file=sys.stderr)
        return 2
    try:
        export_to_path(
            args.database,
            args.output,
            source_commit=bundle["source_commit"],
            expected_database_sha256=bundle["database_sha256"],
        )
    except (RuntimeError, ValueError, OSError) as exc:
        print(f"analytics_source_export_failed error={type(exc).__name__} detail={exc}", file=sys.stderr)
        return 2
    print(json.dumps({"status": "ok", "database_sha256": bundle["database_sha256"], "input_fingerprint": bundle["input_fingerprint"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
