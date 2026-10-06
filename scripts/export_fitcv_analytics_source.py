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


def _normalized_query_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")


def _is_secret_query_key(key: str) -> bool:
    normalized = _normalized_query_key(key)
    return normalized in _SECRET_QUERY_PARTS or any(
        part in normalized for part in ("api_key", "apikey", "authorization", "credential", "private_key", "secret", "token", "password", "signature")
    )


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
    value = value.strip()
    url_like = "://" in value or value.startswith("//") or re.match(r"^(?:https?|wss?|ftp):", value, re.IGNORECASE)
    try:
        initial_parts = urlsplit(value)
    except ValueError:
        return "[redacted-url]"
    fragment_has_secret = any(_is_secret_query_key(key) for key, _ in parse_qsl(initial_parts.fragment, keep_blank_values=True))
    if not url_like and "?" not in value and not fragment_has_secret:
        return value
    parts = initial_parts
    if not parts.netloc and (parts.scheme or url_like):
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
            (key, _sanitize_string(item))
            for key, item in parse_qsl(parts.query, keep_blank_values=True)
            if not _is_secret_query_key(key)
        ])
    except ValueError:
        query = ""
    return urlunsplit((parts.scheme, host, parts.path, query, "")) if parts.netloc else f"{parts.path}?{query}".rstrip("?")


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


def _mark_null_telemetry(value: Any) -> None:
    if isinstance(value, dict):
        for field in ("token_usage", "usage", "provider_call_count", "total_tokens", "token_total", "prompt_tokens", "completion_tokens", "input_tokens", "output_tokens", "attempt_count"):
            if field in value and value[field] is None:
                value[f"_{field}_present"] = True
        for item in value.values():
            _mark_null_telemetry(item)
    elif isinstance(value, list):
        for item in value:
            _mark_null_telemetry(item)


def _contains_marker(value: Any, marker: str) -> bool:
    if isinstance(value, dict):
        return marker in value or any(_contains_marker(item, marker) for item in value.values())
    if isinstance(value, list):
        return any(_contains_marker(item, marker) for item in value)
    return False


def _valid_debug_identity(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_accepted_debug_event(value: dict[str, Any]) -> bool:
    artifact_identity_fields = ("artifact_id", "artifact_version_id", "version_id", "cv_version_id")
    if not any(_valid_debug_identity(value.get(field)) for field in artifact_identity_fields):
        return False
    if any(field in value and not _valid_debug_identity(value[field]) for field in artifact_identity_fields + ("run_id", "run_job_id")):
        return False
    aliases = [_normalized for field in artifact_identity_fields if (_normalized := value.get(field)) is not None]
    if len({item.strip() for item in aliases if isinstance(item, str)}) > 1:
        return False
    for field in ("accepted", "accepted_outcome"):
        if field in value and (not isinstance(value[field], bool) or not value[field]):
            return False
    for field in ("final_status", "status"):
        if field in value:
            if not isinstance(value[field], str) or value[field].strip().lower() not in {"accepted", "succeeded", "success"}:
                return False
    return True


def _debug_matches_version(debug: dict[str, Any], version_id: str, run_job_id: str, run_id: str) -> bool:
    if debug.get("_debug_run_id_conflict") or debug.get("_debug_event_run_id_conflict") or debug.get("_debug_run_job_id_conflict"):
        return False
    if debug.get("_debug_run_id") != run_id:
        return False
    event_run_id = debug.get("_debug_event_run_id")
    if event_run_id is not None and (not _valid_debug_identity(event_run_id) or event_run_id.strip() != run_id):
        return False
    for field in ("artifact_id", "artifact_version_id", "version_id", "cv_version_id"):
        value = debug.get(field)
        if value is not None and (not _valid_debug_identity(value) or value.strip() != version_id):
            return False
    debug_run_job_id = debug.get("run_job_id")
    return debug_run_job_id is None or (
        _valid_debug_identity(debug_run_job_id) and debug_run_job_id.strip() == run_job_id
    )


def _debug_owned_by_run(debug: dict[str, Any], run_id: str) -> bool:
    return bool(debug) and debug.get("_debug_run_id") == run_id and not debug.get("_debug_run_id_conflict")


def _debug_record_key(run_id: str, identifier: str) -> str:
    return f"{run_id}::{identifier}"


def _acceptance_rejection_present(value: dict[str, Any]) -> bool:
    if value.get("accepted") is False or value.get("accepted_outcome") is False:
        return True
    return any(
        isinstance(value.get(field), str)
        and value[field].strip().lower() in {"rejected", "failed", "failure", "generation_failed", "validation_failed", "persistence_failed"}
        for field in ("status", "final_status")
    )


def _acceptance_evidence_invalid(value: dict[str, Any]) -> bool:
    return any(
        field in value and not isinstance(value[field], bool)
        for field in ("accepted", "accepted_outcome")
    ) or any(
        field in value and not isinstance(value[field], str)
        for field in ("status", "final_status")
    )


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


def _flatten_debug_values(
    value: Any, *, acceptance_context: bool = False, acceptance_items: bool = False
) -> Iterable[dict[str, Any]]:
    if isinstance(value, list):
        if acceptance_items:
            for item in value:
                if isinstance(item, dict):
                    yield {**item, "_acceptance_container_context": True}
                else:
                    yield {"_malformed_acceptance_event": True, "_acceptance_container_context": True}
            return
        for item in value:
            yield from _flatten_debug_values(item, acceptance_context=acceptance_context)
        return
    if not isinstance(value, dict):
        if acceptance_context:
            yield {"_malformed_acceptance_event": True, "_acceptance_container_context": True}
        return
    if any(str(key) in value for key in ("artifact_id", "artifact_version_id", "version_id", "cv_version_id", "run_job_id", "accepted", "accepted_outcome", "final_status")):
        yield {**value, "_acceptance_container_context": True} if acceptance_context else value
    elif acceptance_context:
        yield {**value, "_acceptance_container_context": True}
    for key in (
        "records", "debug_records", "cv_generation_debug_records", "accepted_artifact_events",
        "accepted_cv_effort", "cv_generation_trace",
    ):
        if key in value:
            if key == "accepted_artifact_events":
                if isinstance(value[key], list):
                    yield from _flatten_debug_values(value[key], acceptance_context=True, acceptance_items=True)
                else:
                    yield {"_malformed_acceptance_event": True, "_acceptance_container_context": True}
            else:
                yield from _flatten_debug_values(value[key])


def _debug_records(run_rows: Iterable[Any]) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    for row in run_rows:
        parsed = _run_debug_payload(row)
        compatibility = _json(row["compatibility_json"] if "compatibility_json" in row.keys() else None)
        compatibility = compatibility if isinstance(compatibility, dict) else {}
        cohort_id = compatibility.get("cohort_id") or "operational"
        cohort_type = compatibility.get("cohort_type") or "imported"
        for source_key in ("debug_records", "cv_generation_debug_records", "accepted_artifact_events", "accepted_cv_effort", "cv_generation_trace"):
            raw_value = parsed.get(source_key)
            if source_key == "accepted_artifact_events" and source_key in parsed and not isinstance(raw_value, list):
                raw_values = [{"_malformed_acceptance_container": True}]
            else:
                raw_values = raw_value or []
            values = list(_flatten_debug_values(
                raw_values,
                acceptance_context=source_key == "accepted_artifact_events",
                acceptance_items=source_key == "accepted_artifact_events",
            ))
            for event_index, value in enumerate(values):
                value = dict(value)
                value["_debug_record_groups"] = [f"{row['run_id']}:{source_key}:{event_index}"]
                value["_debug_event_run_id"] = value.get("run_id")
                value["_debug_event_run_job_id"] = value.get("run_job_id")
                value["_debug_run_id"] = str(row["run_id"])
                value["_debug_cohort_id"] = cohort_id
                value["_debug_cohort_type"] = cohort_type
                if source_key == "accepted_artifact_events" or value.get("_acceptance_container_context") or any(
                    field in value for field in ("accepted", "accepted_outcome", "final_status")
                ):
                    value["_acceptance_evidence_seen"] = True
                if source_key == "accepted_artifact_events" or value.get("_acceptance_container_context"):
                    value["_acceptance_evidence_seen"] = True
                    value["_accepted_event_seen"] = True
                    value["_accepted_event_valid"] = _valid_accepted_debug_event(value)
                trace = value.get("cv_generation_trace")
                if isinstance(trace, dict):
                    summary = trace.get("efficiency_summary") or {}
                if "token_usage" in value and value["token_usage"] is None:
                    value["_token_usage_present"] = True
                if "usage" in value and value["usage"] is None:
                    value["_usage_present"] = True
                _mark_null_telemetry(value)
                sanitized = _sanitize(value) or {}
                current_rejection = _acceptance_rejection_present(value)
                current_acceptance_evidence = source_key == "accepted_artifact_events" or bool(
                    value.get("_acceptance_container_context")
                ) or any(
                    field in value for field in ("accepted", "accepted_outcome", "final_status")
                )
                current_invalid = _acceptance_evidence_invalid(value) or (
                    current_acceptance_evidence and not _valid_accepted_debug_event(value)
                )
                identifiers = (
                    value.get("version_id"), value.get("cv_version_id"),
                    value.get("artifact_version_id"), value.get("artifact_id"), value.get("run_job_id"),
                ) if source_key == "accepted_artifact_events" else (
                    value.get("artifact_id"), value.get("artifact_version_id"),
                    value.get("version_id"), value.get("cv_version_id"), value.get("run_job_id"),
                )
                if current_acceptance_evidence and not any(_valid_debug_identity(item) for item in identifiers):
                    identifiers = [f"__unbound_acceptance__:{row['run_id']}:{source_key}:{event_index}"]
                elif source_key == "accepted_artifact_events":
                    identifier = next((item for item in identifiers if _valid_debug_identity(item)), None)
                    identifiers = [identifier] if identifier is not None else [
                        f"__unbound_acceptance__:{row['run_id']}:{source_key}:{event_index}"
                    ]
                for identifier in identifiers:
                    if str(identifier or "").strip():
                        key = identifier.strip() if isinstance(identifier, str) else str(identifier)
                        record_key = _debug_record_key(str(row["run_id"]), key)
                        previous = records.get(record_key, {})
                        merged = {**previous, **sanitized}
                        merged["_debug_identifier"] = key
                        merged["_debug_record_groups"] = sorted(set(
                            previous.get("_debug_record_groups", []) + sanitized.get("_debug_record_groups", [])
                        ))
                        merged["_debug_run_id_conflict"] = bool(previous.get("_debug_run_id_conflict")) or (
                            bool(previous.get("_debug_run_id"))
                            and previous.get("_debug_run_id") != sanitized.get("_debug_run_id")
                        )
                        merged["_debug_event_run_id_conflict"] = bool(previous.get("_debug_event_run_id_conflict")) or (
                            bool(previous.get("_debug_event_run_id"))
                            and bool(sanitized.get("_debug_event_run_id"))
                            and previous.get("_debug_event_run_id") != sanitized.get("_debug_event_run_id")
                        )
                        merged["_debug_run_job_id_conflict"] = bool(previous.get("_debug_run_job_id_conflict")) or (
                            bool(previous.get("_debug_event_run_job_id"))
                            and bool(sanitized.get("_debug_event_run_job_id"))
                            and previous.get("_debug_event_run_job_id") != sanitized.get("_debug_event_run_job_id")
                        )
                        merged["_acceptance_rejection_present"] = bool(previous.get("_acceptance_rejection_present")) or current_rejection
                        merged["_acceptance_evidence_invalid"] = bool(previous.get("_acceptance_evidence_invalid")) or current_invalid
                        merged["_acceptance_evidence_seen"] = bool(previous.get("_acceptance_evidence_seen")) or bool(
                            sanitized.get("_acceptance_evidence_seen")
                        )
                        if source_key == "accepted_artifact_events":
                            merged["_accepted_event_seen"] = True
                            merged["_accepted_event_valid"] = previous.get("_accepted_event_valid", True) and value["_accepted_event_valid"]
                        records[record_key] = merged
                        if source_key == "accepted_artifact_events":
                            break
    return records


def _debug_number(debug: dict[str, Any], field: str) -> Any:
    candidates = [debug, debug.get("efficiency"), debug.get("efficiency_summary")]
    trace = debug.get("cv_generation_trace")
    if isinstance(trace, dict):
        candidates.append(trace.get("efficiency_summary"))
    if field == "token_total":
        if any(
            isinstance(candidate, dict)
            and (candidate.get("_token_usage_present") or candidate.get("_usage_present"))
            for candidate in candidates
        ):
            return None
        invalid_statuses = {"incomplete", "not_run", "unavailable"}
        if any(
            isinstance(candidate, dict)
            and str(candidate.get("token_usage_status") or "").strip().lower() in invalid_statuses
            for candidate in candidates
        ):
            return None
    if field == "token_total":
        def token_number(value: Any) -> int | None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            try:
                numeric = float(value)
            except (OverflowError, ValueError):
                return None
            return int(numeric) if math.isfinite(numeric) and numeric >= 0 and numeric.is_integer() else None

        def usage_total(usage: Any, provider_calls: Any) -> int | None:
            expected_calls = token_number(provider_calls) if provider_calls is not None else None
            if provider_calls is not None and expected_calls is None:
                return None
            if isinstance(usage, list):
                if not usage or expected_calls is not None and expected_calls != len(usage):
                    return None
                totals = [usage_total(block, None) for block in usage]
                return sum(total for total in totals) if all(total is not None for total in totals) else None
            if not isinstance(usage, dict):
                return None
            if any(str(key).endswith("_present") for key in usage):
                return None
            if expected_calls not in (None, 1):
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

        usage_seen = False
        inherited_provider_calls = next(
            (
                candidate.get("provider_call_count")
                for candidate in candidates
                if isinstance(candidate, dict) and candidate.get("provider_call_count") is not None
            ),
            None,
        )
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            if "token_usage" in candidate:
                usage = candidate["token_usage"]
            elif "usage" in candidate:
                usage = candidate["usage"]
            else:
                continue
            if usage is not None or "token_usage" in candidate or "usage" in candidate:
                usage_seen = True
                if candidate.get("_provider_call_count_present"):
                    return None
                if "provider_call_count" not in candidate and any(
                    _contains_marker(item, "_provider_call_count_present") for item in candidates
                ):
                    return None
                provider_calls = candidate.get("provider_call_count", inherited_provider_calls)
                return usage_total(usage, provider_calls)
        if usage_seen:
            return None
        for candidate in candidates:
            if isinstance(candidate, dict) and "token_total" in candidate:
                if str(candidate.get("token_usage_status") or "").strip().lower() == "available":
                    return token_number(candidate.get("token_total"))
                return None
        return None
    for candidate in candidates:
        if field == "attempt_count" and isinstance(candidate, dict) and candidate.get("_attempt_count_present"):
            return None
        if field == "provider_call_count" and isinstance(candidate, dict) and candidate.get("_provider_call_count_present"):
            return None
        if isinstance(candidate, dict) and candidate.get(field) is not None:
            return candidate[field]
    return None


def _debug_attempt_count(debug: dict[str, Any], fallback: int) -> int:
    if _contains_marker(debug, "_attempt_count_present"):
        return 0
    value = _debug_number(debug, "attempt_count")
    if value is None and isinstance(debug.get("attempts"), list):
        value = len(debug["attempts"])
    if value is None:
        return max(1, fallback)
    if isinstance(value, bool):
        return 0
    try:
        numeric = float(value)
    except (OverflowError, TypeError, ValueError):
        return 0
    return int(numeric) if math.isfinite(numeric) and numeric >= 1 and numeric.is_integer() else 0


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

    run_input_identity_by_id: dict[str, dict[str, Any]] = {}
    if _table_exists(connection, "run_inputs"):
        for row in connection.execute("SELECT * FROM run_inputs ORDER BY run_id"):
            profile_json = _json(row["candidate_profile_json"] if "candidate_profile_json" in row.keys() else None)
            profile_fingerprint = row["candidate_profile_checksum"] if "candidate_profile_checksum" in row.keys() else None
            if not profile_fingerprint and isinstance(profile_json, dict):
                try:
                    profile_fingerprint = canonical_candidate_checksum(profile_json)
                except (TypeError, ValueError, KeyError):
                    profile_fingerprint = None
            run_input_identity_by_id[str(row["run_id"])] = {
                "candidate_profile_id": row["candidate_profile_id"],
                "candidate_profile_revision": row["candidate_profile_revision"],
                "candidate_profile_fingerprint": profile_fingerprint,
            }
            if str(row["candidate_profile_id"] or "").strip():
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
    run_job_run_ids = {str(row["run_job_id"]): str(row["run_id"]) for row in jobs}
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
        requirements = snapshot.get("requirements") or snapshot.get("requirement_coverage") or _json(row["skills_json"] if "skills_json" in row.keys() else None) or []
        if isinstance(requirements, dict):
            requirements = list(requirements.values())
        for index, item in enumerate(requirements):
            requirement = item if isinstance(item, str) else next((item.get(field) for field in ("requirement", "canonical", "name", "skill", "title") if item.get(field)), None) if isinstance(item, dict) else None
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
                **run_input_identity_by_id.get(str(row["run_id"]), {}),
            })

    evaluations_by_version: dict[str, Any] = {}
    if _table_exists(connection, "cv_evaluations"):
        for evaluation in connection.execute("SELECT * FROM cv_evaluations WHERE is_current=1 ORDER BY cv_evaluation_id"):
            evaluations_by_version[str(evaluation["cv_version_id"])] = evaluation

    versions = []
    if _table_exists(connection, "cv_versions"):
        versions = connection.execute("SELECT * FROM cv_versions ORDER BY version_id").fetchall()
    versions_by_run_job: dict[str, list[str]] = {}
    for version in versions:
        versions_by_run_job.setdefault(str(version["run_job_id"] or ""), []).append(str(version["version_id"]))
    consumed_debug_keys: set[str] = set()
    for row in versions:
        version_id = str(row["version_id"])
        run_job_id = str(row["run_job_id"] or "")
        ordinal = int(row["ordinal"] or 0)
        status = str(row["generation_status"] or "").lower()
        artifact_debug_key = _debug_record_key(str(row["run_id"]), version_id)
        artifact_debug = debug_by_artifact.get(artifact_debug_key, {})
        artifact_debug = artifact_debug if _debug_owned_by_run(artifact_debug, str(row["run_id"])) else {}
        job_debug_key = _debug_record_key(str(row["run_id"]), run_job_id)
        job_debug_all = debug_by_artifact.get(job_debug_key, {})
        job_debug_all = job_debug_all if _debug_owned_by_run(job_debug_all, str(row["run_id"])) else {}
        job_debug = (
            job_debug_all
            if len(versions_by_run_job.get(run_job_id, [])) == 1
            else {}
        )
        debug = {**job_debug, **artifact_debug}
        debug["_acceptance_rejection_present"] = bool(
            job_debug_all.get("_acceptance_rejection_present") or artifact_debug.get("_acceptance_rejection_present")
        )
        debug["_acceptance_evidence_invalid"] = bool(
            job_debug_all.get("_acceptance_evidence_invalid") or artifact_debug.get("_acceptance_evidence_invalid")
        )
        debug["_debug_run_id_conflict"] = bool(
            job_debug_all.get("_debug_run_id_conflict") or artifact_debug.get("_debug_run_id_conflict")
        )
        if artifact_debug.get("_accepted_event_seen") or artifact_debug.get("_acceptance_evidence_seen"):
            consumed_debug_keys.add(artifact_debug_key)
            consumed_groups = set(artifact_debug.get("_debug_record_groups", []))
            if consumed_groups:
                consumed_debug_keys.update(
                    key for key, candidate in debug_by_artifact.items()
                    if consumed_groups.intersection(candidate.get("_debug_record_groups", []))
                )
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
        common.update(run_input_identity_by_id.get(str(row["run_id"]), {}))
        evaluation = evaluations_by_version.get(version_id)
        evidence = _json(evaluation["evidence_json"] if evaluation is not None and "evidence_json" in evaluation.keys() else None)
        if isinstance(evidence, dict) and str(evaluation["status"] or "") == "succeeded":
            for index, item in enumerate(evidence.get("requirement_coverage") or []):
                if not isinstance(item, dict) or not str(item.get("requirement") or "").strip():
                    continue
                selected_support = str(item.get("selected_support") or "").strip().lower()
                gap_category = {
                    "unsupported": "missing_evidence",
                    "pending": "missing_evidence",
                    "relevant_unverified": "uncertain_interpretation",
                    "contradicted": "unmet_qualifier",
                }.get(selected_support)
                if gap_category:
                    _append(sources, "candidate_gap", {
                        **common,
                        "source_id": f"{version_id}:gap:{index}",
                        "run_job_id": run_job_id,
                        "posting_id": run_job_id,
                        "requirement": item["requirement"],
                        "requirement_instance_id": item.get("requirement_instance_id") or f"{run_job_id}:{index}",
                        "gap_category": gap_category,
                    })
        normalized_status = "succeeded" if status == "generated" else status
        attempt_count = _debug_attempt_count(debug, ordinal or 1)
        provider_call_count = _debug_number(debug, "provider_call_count")
        token_total = _debug_number(debug, "token_total")
        acceptance_evidence_observed = bool(
            artifact_debug.get("_accepted_event_seen") or artifact_debug.get("_acceptance_evidence_seen")
        )
        acceptance_rejection_present = bool(debug.get("_acceptance_rejection_present"))
        acceptance_evidence_invalid = bool(debug.get("_acceptance_evidence_invalid"))
        lineage_available = bool(run_job_id) and run_job_run_ids.get(run_job_id) == str(row["run_id"])
        accepted_event = bool(
            (
                artifact_debug.get("_accepted_event_seen")
                and artifact_debug.get("_accepted_event_valid") is True
                and not acceptance_rejection_present
                and not acceptance_evidence_invalid
                and lineage_available
                and _debug_matches_version(artifact_debug, version_id, run_job_id, str(row["run_id"]))
            )
            or (
                artifact_debug.get("accepted_outcome") is True
                and _valid_accepted_debug_event(artifact_debug)
                and not acceptance_rejection_present
                and not acceptance_evidence_invalid
                and lineage_available
                and _debug_matches_version(artifact_debug, version_id, run_job_id, str(row["run_id"]))
            )
            or (
                isinstance(artifact_debug.get("final_status"), str)
                and artifact_debug["final_status"].lower() == "accepted"
                and _valid_accepted_debug_event(artifact_debug)
                and not acceptance_rejection_present
                and not acceptance_evidence_invalid
                and lineage_available
                and _debug_matches_version(artifact_debug, version_id, run_job_id, str(row["run_id"]))
            )
        )
        accepted_event_invalid = acceptance_evidence_observed and not accepted_event
        artifact_emitted = False
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
        if status == "generated" and (accepted_event or accepted_event_invalid) and row["content_checksum"] and row["content_length"] is not None:
            artifact = {
                **common,
                "source_id": version_id,
                "artifact_id": version_id,
                "run_job_id": run_job_id,
                "status": "accepted",
                "validity": "invalid" if accepted_event_invalid else "valid",
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
            artifact_emitted = True
            if isinstance(debug.get("render_acceptance"), dict):
                _append(sources, "render_proof", {
                    **common,
                    "source_id": f"{version_id}:render",
                    "render_proof_id": f"{version_id}:render",
                    "artifact_id": version_id,
                    **debug["render_acceptance"],
                })
        if acceptance_evidence_observed and not artifact_emitted:
            _append(sources, "accepted_artifact", {
                **common,
                "source_id": version_id,
                "artifact_id": version_id,
                "run_job_id": run_job_id,
                "status": "accepted",
                "validity": "invalid",
            })

    for debug_key, debug in sorted(debug_by_artifact.items()):
        if not (debug.get("_accepted_event_seen") or debug.get("_acceptance_evidence_seen")) or debug_key in consumed_debug_keys:
            continue
        run_id = str(debug.get("_debug_run_id") or "unknown")
        debug_identifier = str(debug.get("_debug_identifier") or debug_key)
        debug_run_job_id = debug.get("run_job_id")
        run_job_id = (
            debug_run_job_id
            if _valid_debug_identity(debug_run_job_id) and run_job_run_ids.get(str(debug_run_job_id)) == run_id
            else f"unbound:{run_id}:{debug_identifier}"
        )
        _append(sources, "accepted_artifact", {
            "source_id": f"{run_id}:invalid-acceptance:{debug_identifier}",
            "artifact_id": f"unresolved:{run_id}:{debug_identifier}",
            "run_id": run_id,
            "run_job_id": run_job_id,
            "cohort_id": debug.get("_debug_cohort_id") or "operational",
            "cohort_type": debug.get("_debug_cohort_type") or "imported",
            "status": "accepted",
            "validity": "invalid",
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
    if _table_exists(connection, "requirement_resolutions") and _table_exists(connection, "requirement_resolution_enqueue_intents") and _table_exists(connection, "run_jobs"):
        for row in connection.execute(
            """SELECT rr.*, i.run_id, j.run_job_id
               FROM requirement_resolutions rr
               JOIN requirement_resolution_enqueue_intents i ON i.resolution_id=rr.resolution_id
               JOIN run_jobs j ON j.run_id=i.run_id AND j.source_url=i.job_url
               ORDER BY rr.resolution_id"""
        ):
            run = run_by_id.get(str(row["run_id"]))
            run_payload = _json(run["compatibility_json"] if run is not None and "compatibility_json" in run.keys() else None)
            run_payload = run_payload if isinstance(run_payload, dict) else {}
            _append(sources, "review_action", {
                "source_id": row["resolution_id"],
                "review_action_id": row["resolution_id"],
                "run_id": row["run_id"],
                "run_job_id": row["run_job_id"],
                "action": row["resolution_action"],
                "candidate_profile_id": row["candidate_profile_id"],
                "candidate_profile_revision": row["candidate_profile_revision"],
                "candidate_profile_fingerprint": row["source_profile_fingerprint"],
                "requirement_instance_id": row["requirement_instance_id"],
                "cohort_id": run_payload.get("cohort_id") or "operational",
                "cohort_type": run_payload.get("cohort_type") or "imported",
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
