"""@meta
name: sqlite_store
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - SQLite-only control-plane store helpers.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

import datetime
import dataclasses
import json
import logging
import os
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable, Optional

from fitcv.persistence import get_local_sqlite_path
from fitcv_cp.backend_runtime import get_backend_runtime
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus

logger = logging.getLogger(__name__)

PersistenceResult = dict[str, str]

_PIPELINE_RUNS_UPDATE_RETRY_ATTEMPTS = 3
_PIPELINE_RUNS_UPDATE_RETRY_DELAY_SECONDS = 0.25
_EVENT_APPEND_RETRY_ATTEMPTS = 3
_EVENT_APPEND_RETRY_DELAY_SECONDS = 0.2
_DEGRADATION_REASON_NONE = "none"
_SQLITE_OPEN_RETRY_ATTEMPTS = 3
_SQLITE_OPEN_RETRY_DELAY_SECONDS = 0.2


def _is_transient_sqlite_open_error(exc: sqlite3.OperationalError) -> bool:
    message = str(exc).strip().lower()
    return "unable to open database file" in message or "disk i/o error" in message


def _local_sqlite_path() -> str:
    runtime = get_backend_runtime()
    if runtime is not None and str(runtime.sqlite_path or "").strip():
        return str(runtime.sqlite_path).strip()
    return get_local_sqlite_path()

def _configure_sqlite_connection(conn: sqlite3.Connection) -> None:
    def _safe_pragma(sql: str, label: str) -> None:
        try:
            conn.execute(sql)
        except sqlite3.OperationalError as exc:
            if _is_transient_sqlite_open_error(exc):
                logger.warning("sqlite %s pragma skipped due to transient open failure: %s", label, exc)
                return
            raise

    _safe_pragma("PRAGMA journal_mode=WAL;", "journal_mode")
    _safe_pragma("PRAGMA synchronous=NORMAL;", "synchronous")
    _safe_pragma("PRAGMA busy_timeout=30000;", "busy_timeout")


def _is_sqlite_malformed_error(exc: BaseException) -> bool:
    return "database disk image is malformed" in str(exc).strip().lower()

def _sqlite_auto_rotate_enabled() -> bool:
    return str(os.environ.get("FITCV_CP_SQLITE_AUTO_ROTATE_ON_MALFORMED") or "").strip().lower() in {"1", "true", "yes"}


def _rotate_corrupt_sqlite_artifacts(db_path: Path) -> None:
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d-%H%M%S")
    for candidate in (db_path, Path(f"{db_path}-wal"), Path(f"{db_path}-shm")):
        if not candidate.exists():
            continue
        rotated = candidate.with_name(f"{candidate.name}.corrupt.{stamp}")
        try:
            candidate.replace(rotated)
        except OSError as exc:
            logger.warning("sqlite recovery rotate failed [%s]: %s", candidate, exc)
        else:
            logger.warning("sqlite recovery rotated corrupt artifact: %s", candidate)


@contextmanager
def _sqlite_connection(db_path: Path):
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn: sqlite3.Connection | None = None
    for attempt in range(_SQLITE_OPEN_RETRY_ATTEMPTS):
        try:
            conn = sqlite3.connect(db_path, timeout=30)
            _configure_sqlite_connection(conn)
            break
        except sqlite3.OperationalError as exc:
            if _is_transient_sqlite_open_error(exc) and attempt < (_SQLITE_OPEN_RETRY_ATTEMPTS - 1):
                time.sleep(_SQLITE_OPEN_RETRY_DELAY_SECONDS)
                continue
            raise
        except sqlite3.DatabaseError as exc:
            if attempt == 0 and _is_sqlite_malformed_error(exc) and _sqlite_auto_rotate_enabled():
                logger.warning("sqlite malformed DB detected; rotating artifacts for recovery: %s", db_path)
                _rotate_corrupt_sqlite_artifacts(db_path)
                continue
            raise
    if conn is None:
        raise RuntimeError(f"failed to open sqlite connection: {db_path}")
    try:
        yield conn
    finally:
        conn.close()

def _ensure_local_cv_versions_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cv_versions (
            version_id TEXT PRIMARY KEY,
            run_id TEXT,
            job_url TEXT,
            fit_classification TEXT,
            generated_at TEXT,
            cv_generation_model TEXT,
            cv_prompt_version TEXT,
            cv_schema_version TEXT,
            cv_structured_json TEXT,
            cv_markdown TEXT,
            cv_generation_input_fingerprint TEXT,
            cv_generation_reuse_status TEXT
        )
        """
    )
    existing_columns = {
        str(row[1] or "")
        for row in conn.execute("PRAGMA table_info(cv_versions)").fetchall()
    }
    if "cv_generation_input_fingerprint" not in existing_columns:
        conn.execute(
            "ALTER TABLE cv_versions ADD COLUMN cv_generation_input_fingerprint TEXT"
        )
    if "cv_generation_reuse_status" not in existing_columns:
        conn.execute(
            "ALTER TABLE cv_versions ADD COLUMN cv_generation_reuse_status TEXT"
        )

def _ensure_local_pipeline_runs_table(conn: sqlite3.Connection) -> None:
    for attempt in range(_SQLITE_OPEN_RETRY_ATTEMPTS):
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS local_pipeline_runs (
                    run_id TEXT PRIMARY KEY,
                    run_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
            return
        except sqlite3.OperationalError as exc:
            if _is_transient_sqlite_open_error(exc) and attempt < (_SQLITE_OPEN_RETRY_ATTEMPTS - 1):
                time.sleep(_SQLITE_OPEN_RETRY_DELAY_SECONDS)
                continue
            raise

def _ensure_local_pipeline_run_events_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS local_pipeline_run_events (
            run_id TEXT NOT NULL,
            event_id TEXT NOT NULL,
            stage TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            payload_json TEXT,
            created_at TEXT NOT NULL
        )
        """
    )

def _ensure_local_rule_filter_results_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rule_filter_results (
            run_id TEXT NOT NULL,
            job_url TEXT NOT NULL,
            passed INTEGER NOT NULL,
            reasons TEXT NOT NULL,
            marks_json TEXT,
            filtered_at TEXT NOT NULL,
            raw_job_fingerprint TEXT,
            source_job_url TEXT
        )
        """
    )
    existing_columns = {
        str(row[1] or "")
        for row in conn.execute("PRAGMA table_info(rule_filter_results)").fetchall()
    }
    if "raw_job_fingerprint" not in existing_columns:
        conn.execute("ALTER TABLE rule_filter_results ADD COLUMN raw_job_fingerprint TEXT")
    if "source_job_url" not in existing_columns:
        conn.execute("ALTER TABLE rule_filter_results ADD COLUMN source_job_url TEXT")

def _pipeline_run_to_json(run: PipelineRun) -> str:
    payload = dataclasses.asdict(run)
    payload["status"] = run.status.value
    # Backward-compat alias for legacy artifact readers.
    payload["stage_artifacts_json"] = run.stage_transition_artifacts_json
    for field_name in (
        "created_at",
        "started_at",
        "finished_at",
        "cancel_requested_at",
        "archived_at",
    ):
        value = payload.get(field_name)
        if isinstance(value, datetime.datetime):
            payload[field_name] = value.isoformat()
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)

def _parse_dt(value: Any) -> Optional[datetime.datetime]:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text)
    except ValueError:
        return None

def _decode_json_or_none(raw: Any) -> Any:
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return None
    return None

def _decode_json_list(raw: Any) -> list[Any]:
    parsed = _decode_json_or_none(raw)
    return parsed if isinstance(parsed, list) else []

def _decode_reason_list(raw: Any) -> list[str]:
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    if isinstance(raw, str):
        parsed = _decode_json_or_none(raw)
        if isinstance(parsed, list):
            return [str(item).strip() for item in parsed if str(item).strip()]
    return []

def _coerce_int_or_none(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

def _persistence_result(status: str, reason: str = _DEGRADATION_REASON_NONE) -> PersistenceResult:
    return {"persistence_status": status, "degradation_reason": reason}

_PIPELINE_RUNS_JSON_FIELDS = {
    "cv_generation_debug_json",
    "effective_settings_json",
    "mapping_suggestions_json",
    "results_export_json",
    "settings_used_json",
    "stage_transition_artifacts_json",
    "synonym_proposals_json",
}

_PIPELINE_RUNS_MISSING_COLUMN_POLICY: dict[str, PersistenceResult] = {
    "synonym_proposals_json": _persistence_result(
        "bundle_only_degraded", "missing_synonym_proposals_json_column"
    ),
    "results_export_json": _persistence_result(
        "bundle_only_degraded", "missing_results_export_json_column"
    ),
    "cv_generation_debug_json": _persistence_result(
        "bundle_only_degraded", "missing_cv_generation_debug_json_column"
    ),
    "stage_transition_artifacts_json": _persistence_result(
        "bundle_only_degraded", "missing_stage_transition_artifacts_json_column"
    ),
    "settings_used_json": _persistence_result(
        "bundle_only_degraded", "missing_settings_used_json_column"
    ),
    "mapping_suggestions_json": _persistence_result(
        "bundle_only_degraded", "missing_mapping_suggestions_json_column"
    ),
    "effective_settings_json": _persistence_result(
        "bundle_only_degraded", "missing_effective_settings_json_column"
    ),
}

def _validate_pipeline_runs_json_field_name(field_name: str) -> None:
    normalized = str(field_name or "").strip()
    if normalized not in _PIPELINE_RUNS_JSON_FIELDS:
        raise ValueError(
            f"Unexpected pipeline_runs JSON field name: {field_name!r}. "
            f"Expected one of: {sorted(_PIPELINE_RUNS_JSON_FIELDS)}"
        )

def _update_local_run(
    run_id: str,
    mutator: Callable[[PipelineRun], PipelineRun],
) -> bool:
    existing = _local_get_run(run_id)
    if existing is None:
        return False
    _local_save_run(mutator(existing))
    return True

def _update_single_pipeline_run_json_field(
    *,
    run_id: str,
    field_name: str,
    field_value: str,
    client: Any | None = None,
    local_mutator: Callable[[PipelineRun], PipelineRun],
) -> None:
    _validate_pipeline_runs_json_field_name(field_name)
    _update_local_run(run_id, local_mutator)
    return

def _update_pipeline_run_json_field_with_result(
    *,
    run_id: str,
    field_name: str,
    field_value: str,
    client: Any | None = None,
    local_mutator: Callable[[PipelineRun], PipelineRun],
    missing_column_result: PersistenceResult | None = None,
) -> PersistenceResult:
    _validate_pipeline_runs_json_field_name(field_name)
    updated = _update_local_run(run_id, local_mutator)
    if not updated:
        return _persistence_result("degraded", "run_not_found")
    return _persistence_result("persisted")

def _pipeline_run_from_json(run_json: str) -> Optional[PipelineRun]:
    try:
        payload = json.loads(run_json)
    except Exception:
        return None
    if not isinstance(payload, dict):
        return None
    raw_status = str(payload.get("raw_status") or "").strip().lower()
    status_value = str(payload.get("status") or "").strip().lower()
    try:
        status = RunStatus(status_value)
        raw_status_value: str | None = raw_status or None
    except ValueError:
        status = RunStatus.FAILED
        raw_status_value = raw_status or status_value or None
    return PipelineRun(
        run_id=str(payload.get("run_id") or ""),
        status=status,
        triggered_by=str(payload.get("triggered_by") or ""),
        trigger_source=str(payload.get("trigger_source") or ""),
        jobs_path=str(payload.get("jobs_path") or ""),
        config_path=str(payload.get("config_path") or ""),
        created_at=_parse_dt(payload.get("created_at")) or datetime.datetime.now(datetime.timezone.utc),
        started_at=_parse_dt(payload.get("started_at")),
        finished_at=_parse_dt(payload.get("finished_at")),
        total_jobs=payload.get("total_jobs"),
        passed_filter=payload.get("passed_filter"),
        ranked=payload.get("ranked"),
        cvs_generated=payload.get("cvs_generated"),
        error_message=payload.get("error_message"),
        error_stage=payload.get("error_stage"),
        effective_settings_json=payload.get("effective_settings_json"),
        results_export_json=payload.get("results_export_json"),
        cv_generation_debug_json=payload.get("cv_generation_debug_json"),
        stage_transition_artifacts_json=(
            payload.get("stage_transition_artifacts_json")
            or payload.get("stage_artifacts_json")
        ),
        settings_used_json=payload.get("settings_used_json"),
        mapping_suggestions_json=payload.get("mapping_suggestions_json"),
        synonym_proposals_json=payload.get("synonym_proposals_json"),
        run_mode=str(payload.get("run_mode") or "run_all"),
        checkpoint_status=payload.get("checkpoint_status"),
        next_stage=payload.get("next_stage"),
        last_completed_stage=payload.get("last_completed_stage"),
        completed_stages=list(payload.get("completed_stages") or []) or None,
        checkpoint_payload_json=payload.get("checkpoint_payload_json"),
        jobs_input_source=payload.get("jobs_input_source"),
        jobs_input_json=payload.get("jobs_input_json"),
        jobs_input_manifest_json=payload.get("jobs_input_manifest_json"),
        candidate_profile_source=payload.get("candidate_profile_source"),
        candidate_profile_json=payload.get("candidate_profile_json"),
        queue_job_id=payload.get("queue_job_id"),
        orchestration_backend=payload.get("orchestration_backend"),
        orchestration_run_id=payload.get("orchestration_run_id"),
        cancel_requested_at=_parse_dt(payload.get("cancel_requested_at")),
        cancel_requested_by=payload.get("cancel_requested_by"),
        archived_at=_parse_dt(payload.get("archived_at")),
        archived_by=payload.get("archived_by"),
        raw_status=raw_status_value,
    )

def _upsert_local_pipeline_run(run: PipelineRun) -> None:
    db_path = Path(_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(_PIPELINE_RUNS_UPDATE_RETRY_ATTEMPTS):
        try:
            with _sqlite_connection(db_path) as conn:
                _ensure_local_pipeline_runs_table(conn)
                conn.execute(
                    """
                    INSERT INTO local_pipeline_runs(run_id, run_json, created_at)
                    VALUES (?, ?, ?)
                    ON CONFLICT(run_id) DO UPDATE SET
                      run_json = excluded.run_json,
                      created_at = excluded.created_at
                    """,
                    (run.run_id, _pipeline_run_to_json(run), run.created_at.isoformat()),
                )
                conn.commit()
            return
        except sqlite3.OperationalError as exc:
            last_error = exc
            if "disk I/O error" not in str(exc):
                raise
            if attempt >= _PIPELINE_RUNS_UPDATE_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(_PIPELINE_RUNS_UPDATE_RETRY_DELAY_SECONDS * (attempt + 1))
    if last_error is not None:
        raise last_error

def _load_local_pipeline_run(run_id: str) -> Optional[PipelineRun]:
    db_path = Path(_local_sqlite_path())
    if not db_path.exists():
        return None
    with _sqlite_connection(db_path) as conn:
        _ensure_local_pipeline_runs_table(conn)
        row = conn.execute(
            "SELECT run_json FROM local_pipeline_runs WHERE run_id = ? LIMIT 1",
            (run_id,),
        ).fetchone()
    if not row:
        return None
    return _pipeline_run_from_json(str(row[0] or ""))

def _list_local_pipeline_runs() -> list[PipelineRun]:
    db_path = Path(_local_sqlite_path())
    if not db_path.exists():
        return []
    with _sqlite_connection(db_path) as conn:
        _ensure_local_pipeline_runs_table(conn)
        rows = conn.execute(
            "SELECT run_json FROM local_pipeline_runs ORDER BY created_at DESC"
        ).fetchall()
    runs: list[PipelineRun] = []
    for row in rows:
        run = _pipeline_run_from_json(str(row[0] or ""))
        if run is not None and run.run_id:
            runs.append(run)
    return runs

def _local_get_run(run_id: str) -> Optional[PipelineRun]:
    # Always consult sqlite source-of-truth first.
    #
    # When `web` and `worker` run in separate processes/containers (common in
    # docker-compose), relying on in-process cache can cause stale reads for
    # status/timestamps written by the other process.
    run = _load_local_pipeline_run(run_id)
    return dataclasses.replace(run) if run is not None else None

def _local_save_run(run: PipelineRun) -> None:
    _upsert_local_pipeline_run(run)


def _local_event_history_dir() -> Path:
    raw = str(
        os.environ.get("FITCV_CP_LOCAL_EVENT_HISTORY_DIR")
        or "data/fitcv_cp_event_history"
    ).strip()
    return Path(raw)


def _local_event_history_file(run_id: str) -> Path:
    safe_run_id = "".join(ch for ch in str(run_id) if ch.isalnum() or ch in {"-", "_"})
    return _local_event_history_dir() / f"{safe_run_id}.jsonl"

def _append_local_pipeline_run_event(event: RunEvent) -> None:
    db_path = Path(_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _sqlite_connection(db_path) as conn:
        _ensure_local_pipeline_run_events_table(conn)
        conn.execute(
            """
            INSERT INTO local_pipeline_run_events(
                run_id, event_id, stage, level, message, payload_json, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event.run_id,
                event.event_id,
                event.stage,
                event.level,
                event.message,
                event.payload_json,
                event.created_at.isoformat(),
            ),
        )
        conn.commit()

def _list_local_pipeline_run_events(run_id: str) -> list[RunEvent]:
    db_path = Path(_local_sqlite_path())
    if not db_path.exists():
        return []
    with _sqlite_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_local_pipeline_run_events_table(conn)
        rows = conn.execute(
            """
            SELECT run_id, event_id, stage, level, message, payload_json, created_at
            FROM local_pipeline_run_events
            WHERE run_id = ?
            ORDER BY created_at ASC, rowid ASC
            """,
            (run_id,),
        ).fetchall()
    events: list[RunEvent] = []
    for row in rows:
        created_raw = str(row["created_at"] or "").strip()
        created_at = (
            datetime.datetime.fromisoformat(created_raw)
            if created_raw
            else datetime.datetime.now(datetime.timezone.utc)
        )
        events.append(
            RunEvent(
                run_id=str(row["run_id"] or run_id),
                event_id=str(row["event_id"] or ""),
                stage=str(row["stage"] or ""),
                level=str(row["level"] or ""),
                message=str(row["message"] or ""),
                created_at=created_at,
                payload_json=row["payload_json"],
            )
        )
    return events



def insert_run(run: PipelineRun, *_compat_args: Any, **_compat_kwargs: Any) -> None:
    _local_save_run(dataclasses.replace(run))
    return



def update_run_status(
    run_id: str,
    status: RunStatus,
    *_compat_args: Any,
    started_at: Optional[datetime.datetime] = None,
    finished_at: Optional[datetime.datetime] = None,
    summary: Optional[dict[str, Any]] = None,
    error_message: Optional[str] = None,
    error_stage: Optional[str] = None,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    def _mutate(existing: PipelineRun) -> PipelineRun:
        updated = dataclasses.replace(existing, status=status)
        if started_at:
            updated.started_at = started_at
        if finished_at:
            updated.finished_at = finished_at
        if error_message:
            updated.error_message = error_message
        if error_stage:
            updated.error_stage = error_stage
        if summary:
            for key in ("total_jobs", "passed_filter", "ranked", "cvs_generated"):
                raw_value = summary.get(key)
                if raw_value is None:
                    continue
                try:
                    setattr(updated, key, int(raw_value))
                except (TypeError, ValueError):
                    logger.warning(
                        "Ignoring non-integer run summary value for %s on run_id=%s: %r",
                        key,
                        run_id,
                        raw_value,
                    )
        return updated
    updated = _update_local_run(run_id, _mutate)
    if not updated:
        return _persistence_result("degraded", "run_not_found")
    return _persistence_result("persisted")


def update_run_checkpoint(
    run_id: str,
    *_compat_args: Any,
    checkpoint_status: Optional[str] = None,
    next_stage: Optional[str] = None,
    last_completed_stage: Optional[str] = None,
    completed_stages: Optional[list[str]] = None,
    checkpoint_payload_json: Optional[str] = None,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    existing = _local_get_run(run_id)
    if existing is None:
        return _persistence_result("degraded", "run_not_found")
    _local_save_run(dataclasses.replace(
        existing,
        checkpoint_status=checkpoint_status,
        next_stage=next_stage,
        last_completed_stage=last_completed_stage,
        completed_stages=completed_stages,
        checkpoint_payload_json=checkpoint_payload_json,
    ))
    return _persistence_result("persisted")


def update_run_progress(
    run_id: str,
    *_compat_args: Any,
    last_completed_stage: Optional[str] = None,
    completed_stages: Optional[list[str]] = None,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist shared stage progress without implying resumability."""
    existing = _local_get_run(run_id)
    if existing is None:
        return _persistence_result("degraded", "run_not_found")
    _local_save_run(dataclasses.replace(
        existing,
        checkpoint_status=None,
        next_stage=None,
        last_completed_stage=last_completed_stage,
        completed_stages=completed_stages,
        checkpoint_payload_json=None,
    ))
    return _persistence_result("persisted")



def append_event(event: RunEvent, *_compat_args: Any, **_compat_kwargs: Any) -> dict[str, str]:
    # Use persistence-time timestamp as canonical ordering key so mixed producers
    # cannot backdate events and scramble timeline order.
    persisted_event = dataclasses.replace(
    event,
    created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    try:
        _append_local_pipeline_run_event(persisted_event)
        return _persistence_result("persisted")
    except Exception as exc:
        logger.warning(
            "local append_event sqlite persistence degraded for run_id=%s: %s",
            persisted_event.run_id,
            exc,
        )
        try:
            event_file = _local_event_history_file(persisted_event.run_id)
            event_file.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "run_id": persisted_event.run_id,
                "event_id": persisted_event.event_id,
                "stage": persisted_event.stage,
                "level": persisted_event.level,
                "message": persisted_event.message,
                "payload_json": persisted_event.payload_json,
                "created_at": persisted_event.created_at.isoformat(),
            }
            with event_file.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            return _persistence_result("persisted")
        except Exception as file_exc:
            logger.warning(
                "local append_event file fallback degraded for run_id=%s: %s",
                persisted_event.run_id,
                file_exc,
            )
            return _persistence_result(
                "failed", "event_insert_failed_no_local_fallback"
            )


def get_run(run_id: str, *_compat_args: Any, **_compat_kwargs: Any) -> Optional[PipelineRun]:
    return _local_get_run(run_id)


def list_runs(
    *_compat_args: Any,
    limit: int = 50,
    include_archived: bool = False,
    archived_only: bool = False,
    **_compat_kwargs: Any,
) -> list[PipelineRun]:
    """List pipeline runs with archive visibility control.

    - include_archived=False (default): active runs only (archived_at IS NULL)
    - archived_only=True: archived runs only (archived_at IS NOT NULL)
    - include_archived=True: all runs, no archive filter

    DEPLOY NOTE: migration must be applied before this code is deployed.
    """
    runs = _list_local_pipeline_runs()
    if archived_only:
        runs = [r for r in runs if r.archived_at is not None]
    elif not include_archived:
        runs = [r for r in runs if r.archived_at is None]
    runs.sort(key=lambda r: r.created_at, reverse=True)
    return [dataclasses.replace(r) for r in runs[: int(limit)]]

def get_pipeline_runs_schema_status(
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> dict[str, Any]:
    """Report whether orchestration-binding columns exist on pipeline_runs."""
    return {
        "status": "unknown",
        "missing_columns": [],
        "warning": "sqlite_mode_no_remote_schema_check",
    }


def update_run_queue_job_id(
    run_id: str,
    queue_job_id: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist the RQ job id onto the run row immediately after enqueue."""
    existing = _local_get_run(run_id)
    if existing is None:
        return _persistence_result("degraded", "run_not_found")
    _local_save_run(dataclasses.replace(existing, queue_job_id=queue_job_id))
    return _persistence_result("persisted")

def update_run_orchestration_binding(
    run_id: str,
    *,
    queue_job_id: str | None,
    orchestration_backend: str | None,
    orchestration_run_id: str | None,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    existing = _local_get_run(run_id)
    if existing is None:
        return _persistence_result("degraded", "run_not_found")
    _local_save_run(dataclasses.replace(
        existing,
        queue_job_id=queue_job_id,
        orchestration_backend=orchestration_backend,
        orchestration_run_id=orchestration_run_id,
    ))
    return _persistence_result("persisted")


def update_run_results_export(
    run_id: str,
    results_export_json: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist the immutable run-results export snapshot for a completed run."""
    return _update_pipeline_run_json_field_with_result(
        run_id=run_id,
        field_name="results_export_json",
        field_value=results_export_json,
        local_mutator=lambda existing: dataclasses.replace(
            existing, results_export_json=results_export_json
        ),
    )


def update_run_cv_generation_debug(
    run_id: str,
    cv_generation_debug_json: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist the immutable run-scoped CV-generation debug snapshot."""
    return _update_pipeline_run_json_field_with_result(
        run_id=run_id,
        field_name="cv_generation_debug_json",
        field_value=cv_generation_debug_json,
        local_mutator=lambda existing: dataclasses.replace(
            existing, cv_generation_debug_json=cv_generation_debug_json
        ),
    )


def update_run_stage_transition_artifacts(
    run_id: str,
    stage_transition_artifacts_json: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist the immutable run-scoped stage transition artifacts snapshot."""
    return _update_pipeline_run_json_field_with_result(
        run_id=run_id,
        field_name="stage_transition_artifacts_json",
        field_value=stage_transition_artifacts_json,
        local_mutator=lambda existing: dataclasses.replace(
            existing, stage_transition_artifacts_json=stage_transition_artifacts_json
        ),
    )


def update_run_settings_used(
    run_id: str,
    settings_used_json: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist the immutable run-scoped settings-used snapshot."""
    return _update_pipeline_run_json_field_with_result(
        run_id=run_id,
        field_name="settings_used_json",
        field_value=settings_used_json,
        local_mutator=lambda existing: dataclasses.replace(
            existing, settings_used_json=settings_used_json
        ),
    )


def update_run_mapping_suggestions(
    run_id: str,
    mapping_suggestions_json: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist the immutable run-scoped mapping suggestions snapshot."""
    return _update_pipeline_run_json_field_with_result(
        run_id=run_id,
        field_name="mapping_suggestions_json",
        field_value=mapping_suggestions_json,
        local_mutator=lambda existing: dataclasses.replace(
            existing, mapping_suggestions_json=mapping_suggestions_json
        ),
    )


def update_run_synonym_proposals(
    run_id: str,
    synonym_proposals_json: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> dict[str, str]:
    """Persist the mutable run-scoped synonym proposal review snapshot."""
    return _update_pipeline_run_json_field_with_result(
        run_id=run_id,
        field_name="synonym_proposals_json",
        field_value=synonym_proposals_json,
        local_mutator=lambda existing: dataclasses.replace(
            existing, synonym_proposals_json=synonym_proposals_json
        ),
    )


def update_run_effective_settings(
    run_id: str,
    effective_settings_json: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> PersistenceResult:
    """Persist the mutable run-scoped effective settings snapshot."""
    return _update_pipeline_run_json_field_with_result(
        run_id=run_id,
        field_name="effective_settings_json",
        field_value=effective_settings_json,
        local_mutator=lambda existing: dataclasses.replace(
            existing, effective_settings_json=effective_settings_json
        ),
    )


def request_run_cancel(
    run_id: str,
    requested_by: str,
    new_status: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> bool:
    """Set cancel_requested_at/by and update status (running→cancelling, queued→cancelled)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    existing = _local_get_run(run_id)
    if existing is None:
        return False
    updated = dataclasses.replace(
        existing,
        cancel_requested_at=now,
        cancel_requested_by=requested_by,
        status=RunStatus(new_status),
    )
    _local_save_run(updated)
    return True


def archive_run(
    run_id: str,
    archived_by: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> None:
    """Persist archive state on the run record (non-destructive)."""
    now = datetime.datetime.now(datetime.timezone.utc)
    existing = _local_get_run(run_id)
    if existing is None:
        return
    updated = dataclasses.replace(
        existing,
        archived_at=now,
        archived_by=archived_by,
    )
    _local_save_run(updated)
    return


def unarchive_run(
    run_id: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> None:
    """Clear archive state, returning run to the active list."""
    existing = _local_get_run(run_id)
    if existing is None:
        return
    updated = dataclasses.replace(
        existing,
        archived_at=None,
        archived_by=None,
    )
    _local_save_run(updated)
    return



def _delete_local_pipeline_run(run_id: str) -> None:
    db_path = Path(_local_sqlite_path())
    if db_path.exists():
        with _sqlite_connection(db_path) as conn:
            _ensure_local_pipeline_runs_table(conn)
            _ensure_local_pipeline_run_events_table(conn)
            conn.execute("DELETE FROM local_pipeline_runs WHERE run_id = ?", (run_id,))
            conn.execute("DELETE FROM local_pipeline_run_events WHERE run_id = ?", (run_id,))
            conn.commit()
    event_file = _local_event_history_file(run_id)
    if event_file.exists():
        event_file.unlink()


def _delete_run_artifact_mirror(run_id: str) -> None:
    mirror_dir = Path("artifacts") / f"live_run_{run_id}"
    if mirror_dir.exists():
        shutil.rmtree(mirror_dir, ignore_errors=True)


def delete_archived_runs(
    older_than_days: int | str,
    *_compat_args: Any,
    run_ids: list[str] | None = None,
    **_compat_kwargs: Any,
) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc)
    delete_all = isinstance(older_than_days, str) and older_than_days == "all"
    cutoff = None if delete_all else now - datetime.timedelta(days=int(older_than_days))
    selected_run_ids = {str(run_id).strip() for run_id in (run_ids or []) if str(run_id).strip()}
    deleted_run_ids: list[str] = []
    for run in _list_local_pipeline_runs():
        if run.archived_at is None:
            continue
        if selected_run_ids and run.run_id not in selected_run_ids:
            continue
        if cutoff is not None and run.archived_at > cutoff:
            continue
        deleted_run_ids.append(run.run_id)
        _delete_local_pipeline_run(run.run_id)
        _delete_run_artifact_mirror(run.run_id)
    return {"deleted_count": len(deleted_run_ids), "deleted_run_ids": deleted_run_ids}
def get_events(run_id: str, *_compat_args: Any, **_compat_kwargs: Any) -> list[RunEvent]:
    events = _list_local_pipeline_run_events(run_id)
    if events:
        return events
    event_file = _local_event_history_file(run_id)
    if not event_file.exists():
        return []
    file_events: list[RunEvent] = []
    try:
        with event_file.open("r", encoding="utf-8") as handle:
            for line in handle:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    record = _decode_json_or_none(raw)
                    if not isinstance(record, dict):
                        continue
                    created_raw = str(record.get("created_at") or "").strip()
                    created_at = (
                        datetime.datetime.fromisoformat(created_raw)
                        if created_raw
                        else datetime.datetime.now(datetime.timezone.utc)
                    )
                    file_events.append(
                        RunEvent(
                            run_id=str(record.get("run_id") or run_id),
                            event_id=str(record.get("event_id") or ""),
                            stage=str(record.get("stage") or ""),
                            level=str(record.get("level") or ""),
                            message=str(record.get("message") or ""),
                            created_at=created_at,
                            payload_json=record.get("payload_json"),
                        )
                    )
                except Exception:
                    continue
    except Exception as exc:
        logger.warning(
            "local get_events file read degraded for run_id=%s: %s",
            run_id,
            exc,
        )
    file_events.sort(key=lambda ev: ev.created_at)
    return file_events


def _row_to_run(row: Any) -> PipelineRun:
    r = dict(row)
    raw_status = str(r.get("status") or "").strip().lower()
    try:
        status = RunStatus(raw_status)
        raw_status_value: str | None = None
    except ValueError:
        logger.warning(
            "Unknown pipeline run status %r for run_id=%s; preserving raw_status for diagnostics",
            raw_status,
            r.get("run_id"),
        )
        status = RunStatus.FAILED
        raw_status_value = raw_status or None
    completed_stages_raw = r.get("completed_stages_json")
    completed_stages: list[str] | None = None
    if isinstance(completed_stages_raw, str) and completed_stages_raw.strip():
        parsed_completed_stages = _decode_json_or_none(completed_stages_raw)
        if isinstance(parsed_completed_stages, list):
            completed_stages = [str(item) for item in parsed_completed_stages]
    elif isinstance(completed_stages_raw, list):
        completed_stages = [str(item) for item in completed_stages_raw]
    return PipelineRun(
        run_id=r["run_id"],
        status=status,
        triggered_by=r.get("triggered_by") or "",
        trigger_source=r.get("trigger_source") or "",
        jobs_path=r.get("jobs_path") or "",
        config_path=r.get("config_path") or "",
        created_at=r["created_at"],
        started_at=r.get("started_at"),
        finished_at=r.get("finished_at"),
        total_jobs=r.get("total_jobs"),
        passed_filter=r.get("passed_filter"),
        ranked=r.get("ranked"),
        cvs_generated=r.get("cvs_generated"),
        error_message=r.get("error_message"),
        error_stage=r.get("error_stage"),
        effective_settings_json=r.get("effective_settings_json"),
        results_export_json=r.get("results_export_json"),
        cv_generation_debug_json=r.get("cv_generation_debug_json"),
        stage_transition_artifacts_json=r.get("stage_transition_artifacts_json"),
        settings_used_json=r.get("settings_used_json"),
        mapping_suggestions_json=r.get("mapping_suggestions_json"),
        synonym_proposals_json=r.get("synonym_proposals_json"),
        run_mode=r.get("run_mode") or "run_all",
        checkpoint_status=r.get("checkpoint_status"),
        next_stage=r.get("next_stage"),
        last_completed_stage=r.get("last_completed_stage"),
        completed_stages=completed_stages,
        checkpoint_payload_json=r.get("checkpoint_payload_json"),
        jobs_input_source=r.get("jobs_input_source"),
        jobs_input_json=r.get("jobs_input_json"),
        jobs_input_manifest_json=r.get("jobs_input_manifest_json"),
        candidate_profile_source=r.get("candidate_profile_source"),
        candidate_profile_json=r.get("candidate_profile_json"),
        queue_job_id=r.get("queue_job_id"),
        orchestration_backend=r.get("orchestration_backend"),
        orchestration_run_id=r.get("orchestration_run_id"),
        cancel_requested_at=r.get("cancel_requested_at"),
        cancel_requested_by=r.get("cancel_requested_by"),
        archived_at=r.get("archived_at"),
        archived_by=r.get("archived_by"),
        raw_status=raw_status_value,
    )


def _row_to_event(row: Any) -> RunEvent:
    r = dict(row)
    return RunEvent(
        run_id=r["run_id"],
        event_id=r["event_id"],
        stage=r["stage"],
        level=r["level"],
        message=r["message"],
        created_at=r["created_at"],
        payload_json=r.get("payload_json"),
    )


def list_cvs_for_run(run_id: str, *_compat_args: Any, **_compat_kwargs: Any) -> list[dict[str, Any]]:
    db_path = Path(_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _sqlite_connection(db_path) as conn:
        _ensure_local_cv_versions_table(conn)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
                version_id,
                job_url,
                fit_classification,
                generated_at,
                cv_generation_model,
                cv_prompt_version,
                cv_schema_version,
                cv_structured_json,
                cv_generation_input_fingerprint,
                cv_generation_reuse_status
            FROM cv_versions
            WHERE run_id = ?
            ORDER BY generated_at DESC
            """,
            (run_id,),
        ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        row_dict = dict(row)
        structured_raw = row_dict.get("cv_structured_json")
        row_dict["cv_structured"] = _decode_json_or_none(structured_raw)
        results.append(row_dict)
    return results

def lookup_reusable_cv_versions(
    fingerprints: list[str],
    *_compat_args: Any,
    limit: int = 500,
    **_compat_kwargs: Any,
) -> dict[str, dict[str, Any]]:
    normalized = [str(item or "").strip() for item in fingerprints if str(item or "").strip()]
    if not normalized:
        return {}
    db_path = Path(_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _sqlite_connection(db_path) as conn:
        _ensure_local_cv_versions_table(conn)
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in normalized)
        rows = conn.execute(
            f"""
            SELECT
                version_id,
                run_id,
                job_url,
                fit_classification,
                generated_at,
                cv_generation_model,
                cv_prompt_version,
                cv_schema_version,
                cv_structured_json,
                cv_markdown,
                cv_generation_input_fingerprint,
                cv_generation_reuse_status
            FROM cv_versions
            WHERE cv_generation_input_fingerprint IN ({placeholders})
            ORDER BY generated_at DESC
            """,
            tuple(normalized),
        ).fetchall()
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        row_dict = dict(row)
        fingerprint = str(row_dict.get("cv_generation_input_fingerprint") or "").strip()
        if not fingerprint or fingerprint in indexed:
            continue
        row_dict["cv_structured"] = _decode_json_or_none(row_dict.get("cv_structured_json"))
        indexed[fingerprint] = row_dict
    return indexed


def get_cv_markdown(version_id: str, *_compat_args: Any, **_compat_kwargs: Any) -> Optional[str]:
    db_path = Path(_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _sqlite_connection(db_path) as conn:
        _ensure_local_cv_versions_table(conn)
        row = conn.execute(
            "SELECT cv_markdown FROM cv_versions WHERE version_id = ? LIMIT 1",
            (version_id,),
        ).fetchone()
    if row is None:
        return None
    return str(row[0] or "")


def list_run_structured_jobs(
    run_id: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> list[dict[str, Any]]:
    """Return run-scoped enriched job rows for the given run_id.

    Rows are returned as plain dicts and ordered by title, job_url for
    deterministic display. Uses parameterized SQL to avoid injection.
    """
    import json
    import sqlite3
    db_path = _local_sqlite_path()
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT payload_json
                FROM run_structured_jobs
                WHERE run_id = ?
                """,
                (run_id,),
            ).fetchall()
    except sqlite3.OperationalError:
        return []
    parsed: list[dict[str, Any]] = []
    for (payload_json,) in rows:
        try:
            parsed.append(json.loads(payload_json or "{}"))
        except (TypeError, ValueError):
            continue
    parsed.sort(key=lambda row: (str(row.get("title") or ""), str(row.get("job_url") or "")))
    return parsed


def list_filter_results_for_run(
    run_id: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> list[dict[str, Any]]:
    """Return run-scoped filter results for a given run_id.

    Rows include job_url, passed (bool), reasons, marks, and run_id.
    Ordered by job_url for deterministic display. Uses parameterized SQL.
    """
    db_path = _local_sqlite_path()
    try:
        with sqlite3.connect(db_path) as conn:
            _ensure_local_rule_filter_results_table(conn)
            cursor = conn.execute(
                """
                SELECT *
                FROM rule_filter_results
                WHERE run_id = ?
                ORDER BY job_url
                """,
                (run_id,),
            )
            columns = [str(item[0] or "") for item in (cursor.description or [])]
            rows = cursor.fetchall()
    except sqlite3.OperationalError:
        return []
    results: list[dict[str, Any]] = []
    for row in rows:
        row_dict = dict(zip(columns, row))
        row_dict["passed"] = bool(row_dict.get("passed"))
        row_dict["reasons"] = _decode_reason_list(row_dict.get("reasons"))
        row_dict["marks"] = _decode_json_list(row_dict.get("marks_json"))
        results.append(row_dict)
    return results


def insert_cv_version_row(row: dict[str, Any], *_compat_args: Any, **_compat_kwargs: Any) -> list[Any]:
    db_path = Path(_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    last_error: Exception | None = None
    for attempt in range(_PIPELINE_RUNS_UPDATE_RETRY_ATTEMPTS):
        try:
            with _sqlite_connection(db_path) as conn:
                _ensure_local_cv_versions_table(conn)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO cv_versions (
                        version_id,
                        run_id,
                        job_url,
                        fit_classification,
                        generated_at,
                        cv_generation_model,
                        cv_prompt_version,
                        cv_schema_version,
                        cv_structured_json,
                        cv_markdown,
                        cv_generation_input_fingerprint,
                        cv_generation_reuse_status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(row.get("version_id") or ""),
                        str(row.get("run_id") or ""),
                        str(row.get("job_url") or ""),
                        str(row.get("fit_classification") or ""),
                        str(row.get("generated_at") or ""),
                        str(row.get("cv_generation_model") or ""),
                        str(row.get("cv_prompt_version") or ""),
                        str(row.get("cv_schema_version") or ""),
                        str(row.get("cv_structured_json") or ""),
                        str(row.get("cv_markdown") or ""),
                        str(row.get("cv_generation_input_fingerprint") or ""),
                        str(row.get("cv_generation_reuse_status") or ""),
                    ),
                )
                conn.commit()
            return []
        except sqlite3.OperationalError as exc:
            last_error = exc
            if "disk I/O error" not in str(exc):
                raise
            if attempt >= _PIPELINE_RUNS_UPDATE_RETRY_ATTEMPTS - 1:
                raise
            time.sleep(_PIPELINE_RUNS_UPDATE_RETRY_DELAY_SECONDS * (attempt + 1))
    if last_error is not None:
        raise last_error
    return []




def insert_application_tracker_row(
    row: dict[str, Any],
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> list[Any]:
    db_path = Path(_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with _sqlite_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS application_tracker (
                tracker_id TEXT PRIMARY KEY,
                job_url TEXT,
                cv_version_id TEXT,
                status TEXT,
                notes TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO application_tracker (
                tracker_id,
                job_url,
                cv_version_id,
                status,
                notes,
                updated_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(row.get("tracker_id") or ""),
                str(row.get("job_url") or ""),
                str(row.get("cv_version_id") or "") or None,
                str(row.get("status") or ""),
                str(row.get("notes") or ""),
                str(row.get("updated_at") or ""),
            ),
        )
        conn.commit()
    return []

