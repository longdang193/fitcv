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
import hashlib
import json
import logging
import os
import shutil
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
from typing import Any, Callable, Optional

from fitcv.decision_feedback import (
    DecisionAlternative,
    DecisionEpisode,
    DecisionRatingEvent,
    RatingEventType,
    RatingValue,
)
from fitcv.inverse_optimization import InverseOptimizationRequest, InverseTrainingEpisode
from fitcv.persistence import get_local_sqlite_path
from fitcv.preference_policy import build_policy_snapshot_identity, build_training_run_identity
from fitcv.shortlist_runtime import build_contract_fingerprint
from fitcv_cp.backend_runtime import get_backend_runtime
from fitcv_cp.models import (
    PipelineRun,
    ProcessEvent,
    ProcessEventIntegrityConflict,
    RunEvent,
    RunStatus,
    build_process_event,
)

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
    return str(get_local_sqlite_path())

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
    _safe_pragma("PRAGMA foreign_keys=ON;", "foreign_keys")


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
def _sqlite_connection(db_path: Path) -> Iterator[sqlite3.Connection]:
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


def _ensure_local_decision_feedback_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS decision_episodes (
            episode_id TEXT PRIMARY KEY,
            domain_id TEXT NOT NULL,
            run_id TEXT NOT NULL,
            preference_context_fingerprint TEXT NOT NULL,
            qualification_context_fingerprint TEXT NOT NULL,
            ranking_contract_fingerprint TEXT NOT NULL,
            embedding_contract_fingerprint TEXT NOT NULL,
            baseline_policy_fingerprint TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension > 0),
            rating_scale_version TEXT NOT NULL,
            candidate_set_fingerprint TEXT NOT NULL,
            source_stage_artifact_fingerprint TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE (episode_id, rating_scale_version)
        );
        CREATE TABLE IF NOT EXISTS decision_episode_alternatives (
            episode_id TEXT NOT NULL,
            alternative_id TEXT NOT NULL,
            displayed_rank INTEGER NOT NULL CHECK (displayed_rank > 0),
            baseline_fit REAL NOT NULL CHECK (baseline_fit >= 0 AND baseline_fit <= 1),
            baseline_fit_label TEXT NOT NULL CHECK (baseline_fit_label IN ('strong', 'stretch', 'skip')),
            normalized_embedding_json TEXT NOT NULL,
            embedding_vector_fingerprint TEXT NOT NULL,
            source_job_url TEXT NOT NULL,
            shortlist_origin TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY (episode_id, alternative_id),
            UNIQUE (episode_id, displayed_rank),
            FOREIGN KEY (episode_id) REFERENCES decision_episodes(episode_id)
        );
        CREATE TABLE IF NOT EXISTS decision_rating_events (
            event_sequence INTEGER PRIMARY KEY,
            event_id TEXT NOT NULL UNIQUE,
            episode_id TEXT NOT NULL,
            alternative_id TEXT NOT NULL,
            event_type TEXT NOT NULL CHECK (event_type IN ('set_rating', 'clear_rating')),
            rating INTEGER,
            rating_scale_version TEXT NOT NULL,
            acted_by TEXT NOT NULL,
            created_at TEXT NOT NULL,
            CHECK (
                (event_type = 'set_rating' AND rating BETWEEN 1 AND 5)
                OR (event_type = 'clear_rating' AND rating IS NULL)
            ),
            FOREIGN KEY (episode_id, alternative_id)
                REFERENCES decision_episode_alternatives(episode_id, alternative_id),
            FOREIGN KEY (episode_id, rating_scale_version)
                REFERENCES decision_episodes(episode_id, rating_scale_version)
        );
        CREATE INDEX IF NOT EXISTS idx_decision_episodes_run_created
            ON decision_episodes(run_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_decision_rating_events_episode_alternative_sequence
            ON decision_rating_events(episode_id, alternative_id, event_sequence);
        """
    )
    for table_name in (
        "decision_episodes",
        "decision_episode_alternatives",
        "decision_rating_events",
    ):
        conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS {table_name}_append_only_update
            BEFORE UPDATE ON {table_name}
            BEGIN
                SELECT RAISE(ABORT, 'decision feedback ledger is append-only');
            END
            """
        )
        conn.execute(
            f"""
            CREATE TRIGGER IF NOT EXISTS {table_name}_append_only_delete
            BEFORE DELETE ON {table_name}
            BEGIN
                SELECT RAISE(ABORT, 'decision feedback ledger is append-only');
            END
            """
        )


_TRAINING_COLUMNS = (
    "training_run_id", "schema_version", "domain_id", "status", "cohort_fingerprint",
    "event_watermark", "edge_set_fingerprint", "rating_scale_version", "compiler_version",
    "compiler_policy_fingerprint", "decision_learning_policy_fingerprint",
    "optimizer_policy_fingerprint", "activation_policy_fingerprint",
    "baseline_policy_fingerprint", "ranking_contract_fingerprint", "embedding_model",
    "embedding_contract_fingerprint", "embedding_dimension", "learned_alpha",
    "parent_policy_kind", "parent_policy_ref", "problem_fingerprint",
    "evaluation_fingerprint", "result_json", "created_at",
)
_SNAPSHOT_COLUMNS = (
    "policy_snapshot_id", "schema_version", "domain_id", "status",
    "runtime_contract_fingerprint", "baseline_policy_fingerprint",
    "ranking_contract_fingerprint", "embedding_model", "embedding_contract_fingerprint",
    "embedding_dimension", "learned_alpha", "preference_vector_norm_bound",
    "parent_policy_kind", "parent_policy_ref", "preference_vector_json",
    "preference_vector_fingerprint", "payload_fingerprint", "training_run_id",
    "event_watermark", "cohort_fingerprint", "edge_set_fingerprint",
    "rating_scale_version", "compiler_version", "compiler_policy_fingerprint",
    "decision_learning_policy_fingerprint", "optimizer_policy_fingerprint",
    "activation_policy_fingerprint", "problem_fingerprint", "solver_metadata_json",
    "evaluation_version", "evaluation_fingerprint", "evaluation_json", "created_at",
    "activated_at",
)
_JSON_COLUMNS = frozenset(
    {"result_json", "preference_vector_json", "solver_metadata_json", "evaluation_json"}
)


def _ensure_local_preference_policy_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS inverse_training_runs (
            training_run_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN (
                'candidate_created', 'no_op', 'evaluation_rejected', 'insufficient_evidence',
                'invalid_input', 'infeasible_policy', 'solver_error'
            )),
            cohort_fingerprint TEXT NOT NULL,
            event_watermark INTEGER NOT NULL CHECK (event_watermark >= 0),
            edge_set_fingerprint TEXT NOT NULL,
            rating_scale_version TEXT NOT NULL,
            compiler_version TEXT NOT NULL,
            compiler_policy_fingerprint TEXT NOT NULL,
            decision_learning_policy_fingerprint TEXT NOT NULL,
            optimizer_policy_fingerprint TEXT NOT NULL,
            activation_policy_fingerprint TEXT NOT NULL,
            baseline_policy_fingerprint TEXT NOT NULL,
            ranking_contract_fingerprint TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding_contract_fingerprint TEXT NOT NULL,
            embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension > 0),
            learned_alpha REAL NOT NULL,
            parent_policy_kind TEXT NOT NULL CHECK (parent_policy_kind IN ('zero_residual', 'learned')),
            parent_policy_ref TEXT NOT NULL,
            problem_fingerprint TEXT,
            evaluation_fingerprint TEXT,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS ranking_policy_snapshots (
            policy_snapshot_id TEXT PRIMARY KEY,
            schema_version TEXT NOT NULL,
            domain_id TEXT NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('candidate', 'active', 'rejected', 'stale', 'retired')),
            runtime_contract_fingerprint TEXT NOT NULL,
            baseline_policy_fingerprint TEXT NOT NULL,
            ranking_contract_fingerprint TEXT NOT NULL,
            embedding_model TEXT NOT NULL,
            embedding_contract_fingerprint TEXT NOT NULL,
            embedding_dimension INTEGER NOT NULL CHECK (embedding_dimension > 0),
            learned_alpha REAL NOT NULL,
            preference_vector_norm_bound REAL NOT NULL,
            parent_policy_kind TEXT NOT NULL CHECK (parent_policy_kind IN ('zero_residual', 'learned')),
            parent_policy_ref TEXT NOT NULL,
            preference_vector_json TEXT NOT NULL,
            preference_vector_fingerprint TEXT NOT NULL,
            payload_fingerprint TEXT NOT NULL UNIQUE,
            training_run_id TEXT NOT NULL REFERENCES inverse_training_runs(training_run_id),
            event_watermark INTEGER NOT NULL CHECK (event_watermark >= 0),
            cohort_fingerprint TEXT NOT NULL,
            edge_set_fingerprint TEXT NOT NULL,
            rating_scale_version TEXT NOT NULL,
            compiler_version TEXT NOT NULL,
            compiler_policy_fingerprint TEXT NOT NULL,
            decision_learning_policy_fingerprint TEXT NOT NULL,
            optimizer_policy_fingerprint TEXT NOT NULL,
            activation_policy_fingerprint TEXT NOT NULL,
            problem_fingerprint TEXT NOT NULL,
            solver_metadata_json TEXT NOT NULL,
            evaluation_version TEXT NOT NULL,
            evaluation_fingerprint TEXT NOT NULL,
            evaluation_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            activated_at TEXT
        );
        CREATE UNIQUE INDEX IF NOT EXISTS one_active_ranking_policy
            ON ranking_policy_snapshots (domain_id, runtime_contract_fingerprint)
            WHERE status = 'active';
        CREATE TABLE IF NOT EXISTS policy_activation_events (
            activation_event_id TEXT PRIMARY KEY,
            domain_id TEXT NOT NULL,
            runtime_contract_fingerprint TEXT NOT NULL,
            previous_snapshot_id TEXT,
            target_snapshot_id TEXT,
            action TEXT NOT NULL CHECK (action IN ('activate', 'reject', 'stale', 'retire', 'rollback')),
            reason_code TEXT NOT NULL,
            expected_parent_ref TEXT,
            evidence_head_fingerprint TEXT,
            acted_by TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS inverse_training_runs_immutable_update
        BEFORE UPDATE ON inverse_training_runs BEGIN
            SELECT RAISE(ABORT, 'immutable training run');
        END;
        CREATE TRIGGER IF NOT EXISTS inverse_training_runs_immutable_delete
        BEFORE DELETE ON inverse_training_runs BEGIN
            SELECT RAISE(ABORT, 'immutable training run');
        END;
        CREATE TRIGGER IF NOT EXISTS ranking_policy_snapshots_immutable_payload
        BEFORE UPDATE OF schema_version, domain_id, runtime_contract_fingerprint,
            baseline_policy_fingerprint, ranking_contract_fingerprint, embedding_model,
            embedding_contract_fingerprint, embedding_dimension, learned_alpha,
            preference_vector_norm_bound, parent_policy_kind, parent_policy_ref,
            preference_vector_json, preference_vector_fingerprint, payload_fingerprint,
            training_run_id, event_watermark, cohort_fingerprint, edge_set_fingerprint,
            rating_scale_version, compiler_version, compiler_policy_fingerprint,
            decision_learning_policy_fingerprint, optimizer_policy_fingerprint,
            activation_policy_fingerprint, problem_fingerprint, solver_metadata_json,
            evaluation_version, evaluation_fingerprint, evaluation_json, created_at
        ON ranking_policy_snapshots BEGIN
            SELECT RAISE(ABORT, 'immutable snapshot payload');
        END;
        CREATE TRIGGER IF NOT EXISTS ranking_policy_snapshots_no_delete
        BEFORE DELETE ON ranking_policy_snapshots BEGIN
            SELECT RAISE(ABORT, 'snapshot history is append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS policy_activation_events_no_update
        BEFORE UPDATE ON policy_activation_events BEGIN
            SELECT RAISE(ABORT, 'activation history is append-only');
        END;
        CREATE TRIGGER IF NOT EXISTS policy_activation_events_no_delete
        BEFORE DELETE ON policy_activation_events BEGIN
            SELECT RAISE(ABORT, 'activation history is append-only');
        END;
        """
    )


def _policy_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _policy_value(column: str, value: Any) -> Any:
    if column in _JSON_COLUMNS:
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return value


def _row_dict(cursor: sqlite3.Cursor, row: tuple[Any, ...] | None) -> dict[str, Any] | None:
    if row is None:
        return None
    payload = {description[0]: value for description, value in zip(cursor.description, row, strict=True)}
    for column in _JSON_COLUMNS & payload.keys():
        payload[column] = json.loads(payload[column])
    return payload


def _fetch_policy_row(conn: sqlite3.Connection, table: str, key: str, value: str) -> dict[str, Any] | None:
    cursor = conn.execute(f"SELECT * FROM {table} WHERE {key} = ?", (value,))
    return _row_dict(cursor, cursor.fetchone())


def _insert_policy_row(
    conn: sqlite3.Connection,
    table: str,
    columns: tuple[str, ...],
    payload: dict[str, Any],
) -> None:
    placeholders = ", ".join("?" for _ in columns)
    conn.execute(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        tuple(_policy_value(column, payload.get(column)) for column in columns),
    )


def persist_inverse_training_result(payload: dict[str, Any]) -> dict[str, Any]:
    row = dict(payload)
    row.setdefault("created_at", _policy_now())
    expected_id = build_training_run_identity(row)
    row.setdefault("training_run_id", expected_id)
    if row["training_run_id"] != expected_id:
        raise ValueError("training_run_id fingerprint mismatch")
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        existing = _fetch_policy_row(conn, "inverse_training_runs", "training_run_id", expected_id)
        if existing is not None:
            return existing
        _insert_policy_row(conn, "inverse_training_runs", _TRAINING_COLUMNS, row)
        conn.commit()
        return _fetch_policy_row(conn, "inverse_training_runs", "training_run_id", expected_id) or row


def insert_ranking_policy_candidate(payload: dict[str, Any]) -> dict[str, Any]:
    row = dict(payload)
    row.setdefault("status", "candidate")
    row.setdefault("created_at", _policy_now())
    row.setdefault("activated_at", None)
    fingerprint, snapshot_id = build_policy_snapshot_identity(row)
    row.setdefault("payload_fingerprint", fingerprint)
    row.setdefault("policy_snapshot_id", snapshot_id)
    if row["status"] != "candidate":
        raise ValueError("new snapshot status must be candidate")
    if row["payload_fingerprint"] != fingerprint or row["policy_snapshot_id"] != snapshot_id:
        raise ValueError("snapshot fingerprint mismatch")
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        existing = _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", snapshot_id)
        if existing is not None:
            return existing
        _insert_policy_row(conn, "ranking_policy_snapshots", _SNAPSHOT_COLUMNS, row)
        conn.commit()
        return _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", snapshot_id) or row


def _optimization_process_state(status: str) -> str:
    if status == "candidate_created":
        return "succeeded"
    if status == "no_op":
        return "skipped"
    if status in {"evaluation_rejected", "insufficient_evidence", "invalid_input"}:
        return "rejected"
    return "failed"


def _build_optimization_attempt_event(
    training: dict[str, Any], snapshot: dict[str, Any] | None
) -> ProcessEvent:
    status = str(training["status"])
    training_id = str(training["training_run_id"])
    snapshot_id = str(snapshot["policy_snapshot_id"]) if snapshot is not None else None
    refs = [{"kind": "inverse_training_run", "id": training_id}]
    if snapshot_id is not None:
        refs.append({"kind": "ranking_policy_snapshot", "id": snapshot_id})
    return build_process_event(
        process_type="optimization",
        process_id=str(training["domain_id"]),
        operation="candidate_create" if status == "candidate_created" else status,
        state=_optimization_process_state(status),
        level="error" if _optimization_process_state(status) == "failed" else (
            "warning" if _optimization_process_state(status) == "rejected" else "info"
        ),
        message=f"Optimization attempt {status}",
        payload={"status": status, "training_run_id": training_id, "policy_snapshot_id": snapshot_id},
        diagnostic_refs=refs,
        event_id=f"optimization:{training_id}",
        recorded_at=datetime.datetime.fromisoformat(str(training["created_at"])),
    )


def persist_candidate_attempt(
    training_payload: dict[str, Any],
    snapshot_payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    training = dict(training_payload)
    training.setdefault("created_at", _policy_now())
    expected_training_id = build_training_run_identity(training)
    training.setdefault("training_run_id", expected_training_id)
    if training["training_run_id"] != expected_training_id:
        raise ValueError("training run fingerprint mismatch")
    snapshot: dict[str, Any] | None = None
    if snapshot_payload is not None:
        snapshot = dict(snapshot_payload)
        snapshot.setdefault("status", "candidate")
        snapshot.setdefault("created_at", _policy_now())
        snapshot.setdefault("activated_at", None)
        fingerprint, snapshot_id = build_policy_snapshot_identity(snapshot)
        snapshot.setdefault("payload_fingerprint", fingerprint)
        snapshot.setdefault("policy_snapshot_id", snapshot_id)
        if snapshot["training_run_id"] != expected_training_id:
            raise ValueError("snapshot training reference mismatch")
        if snapshot["status"] != "candidate":
            raise ValueError("new snapshot status must be candidate")
        if snapshot["payload_fingerprint"] != fingerprint or snapshot["policy_snapshot_id"] != snapshot_id:
            raise ValueError("snapshot fingerprint mismatch")
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        _ensure_process_event_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        existing_training = _fetch_policy_row(
            conn, "inverse_training_runs", "training_run_id", expected_training_id
        )
        if existing_training is None:
            _insert_policy_row(conn, "inverse_training_runs", _TRAINING_COLUMNS, training)
        elif build_training_run_identity(existing_training) != expected_training_id:
            raise ValueError("existing training run conflicts with payload")
        existing_snapshot = None
        if snapshot is not None:
            existing_snapshot = _fetch_policy_row(
                conn,
                "ranking_policy_snapshots",
                "policy_snapshot_id",
                str(snapshot["policy_snapshot_id"]),
            )
            if existing_snapshot is None:
                _insert_policy_row(conn, "ranking_policy_snapshots", _SNAPSHOT_COLUMNS, snapshot)
            elif existing_snapshot["payload_fingerprint"] != snapshot["payload_fingerprint"]:
                raise ValueError("existing snapshot conflicts with payload")
        _insert_process_event(
            conn,
            _build_optimization_attempt_event(
                existing_training or training, existing_snapshot or snapshot
            ),
            delivery_sinks=("langfuse",),
            raise_on_conflict=True,
        )
        conn.commit()
        return {
            "training_run": _fetch_policy_row(
                conn, "inverse_training_runs", "training_run_id", expected_training_id
            ),
            "snapshot": (
                _fetch_policy_row(
                    conn,
                    "ranking_policy_snapshots",
                    "policy_snapshot_id",
                    str(snapshot["policy_snapshot_id"]),
                )
                if snapshot is not None
                else None
            ),
        }


def _load_decision_training_rows(
    conn: sqlite3.Connection,
    domain_id: str,
) -> tuple[list[dict[str, Any]], int]:
    episode_cursor = conn.execute(
        """
        SELECT episode_id, domain_id, run_id, preference_context_fingerprint,
               qualification_context_fingerprint, ranking_contract_fingerprint,
               embedding_contract_fingerprint, baseline_policy_fingerprint,
               embedding_model, embedding_dimension, rating_scale_version,
               candidate_set_fingerprint, source_stage_artifact_fingerprint, created_at
        FROM decision_episodes
        WHERE domain_id = ?
        ORDER BY episode_id
        """,
        (domain_id,),
    )
    episodes: list[dict[str, Any]] = []
    for episode_row in episode_cursor.fetchall():
        episode = {
            description[0]: value
            for description, value in zip(episode_cursor.description, episode_row, strict=True)
        }
        alternative_cursor = conn.execute(
            """
            SELECT alternative_id, displayed_rank, baseline_fit, baseline_fit_label,
                   normalized_embedding_json, embedding_vector_fingerprint,
                   source_job_url, shortlist_origin, created_at
            FROM decision_episode_alternatives
            WHERE episode_id = ?
            ORDER BY displayed_rank, alternative_id
            """,
            (episode["episode_id"],),
        )
        alternatives = [
            {
                description[0]: value
                for description, value in zip(
                    alternative_cursor.description, alternative_row, strict=True
                )
            }
            for alternative_row in alternative_cursor.fetchall()
        ]
        event_cursor = conn.execute(
            """
            SELECT event_sequence, event_id, episode_id, alternative_id, event_type,
                   rating, rating_scale_version, acted_by, created_at
            FROM decision_rating_events
            WHERE episode_id = ?
            ORDER BY event_sequence, event_id
            """,
            (episode["episode_id"],),
        )
        events = [
            {
                description[0]: value
                for description, value in zip(event_cursor.description, event_row, strict=True)
            }
            for event_row in event_cursor.fetchall()
        ]
        episodes.append({**episode, "alternatives": alternatives, "events": events})
    watermark_row = conn.execute(
        """
        SELECT COALESCE(MAX(e.event_sequence), 0)
        FROM decision_rating_events e
        JOIN decision_episodes p ON p.episode_id = e.episode_id
        WHERE p.domain_id = ?
        """,
        (domain_id,),
    ).fetchone()
    return episodes, int(watermark_row[0]) if watermark_row else 0


def _decision_evidence_head_from_rows(
    domain_id: str,
    episodes: list[dict[str, Any]],
    event_watermark: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": "decision_evidence_head_v1",
        "domain_id": domain_id,
        "event_watermark": event_watermark,
        "episodes": [
            {
                "episode_id": episode["episode_id"],
                "domain_id": episode["domain_id"],
                "preference_context_fingerprint": episode["preference_context_fingerprint"],
                "qualification_context_fingerprint": episode["qualification_context_fingerprint"],
                "ranking_contract_fingerprint": episode["ranking_contract_fingerprint"],
                "embedding_contract_fingerprint": episode["embedding_contract_fingerprint"],
                "baseline_policy_fingerprint": episode["baseline_policy_fingerprint"],
                "embedding_model": episode["embedding_model"],
                "embedding_dimension": episode["embedding_dimension"],
                "rating_scale_version": episode["rating_scale_version"],
                "candidate_set_fingerprint": episode["candidate_set_fingerprint"],
                "source_stage_artifact_fingerprint": episode[
                    "source_stage_artifact_fingerprint"
                ],
                "alternatives": [
                    {
                        "alternative_id": alternative["alternative_id"],
                        "displayed_rank": alternative["displayed_rank"],
                        "baseline_fit": alternative["baseline_fit"],
                        "baseline_fit_label": alternative["baseline_fit_label"],
                        "normalized_embedding": json.loads(
                            alternative["normalized_embedding_json"]
                        ),
                        "embedding_vector_fingerprint": alternative[
                            "embedding_vector_fingerprint"
                        ],
                        "shortlist_origin": alternative["shortlist_origin"],
                    }
                    for alternative in episode["alternatives"]
                ],
                "events": [
                    {
                        "event_sequence": event["event_sequence"],
                        "event_id": event["event_id"],
                        "episode_id": event["episode_id"],
                        "alternative_id": event["alternative_id"],
                        "event_type": event["event_type"],
                        "rating": event["rating"],
                        "rating_scale_version": event["rating_scale_version"],
                    }
                    for event in episode["events"]
                ],
            }
            for episode in episodes
        ],
    }
    return {**payload, "evidence_head_fingerprint": build_contract_fingerprint(payload)}


def get_decision_evidence_head(domain_id: str) -> dict[str, Any]:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        conn.execute("BEGIN")
        _ensure_local_decision_feedback_tables(conn)
        episodes, event_watermark = _load_decision_training_rows(conn, domain_id)
        result = _decision_evidence_head_from_rows(domain_id, episodes, event_watermark)
        conn.commit()
        return result


def load_inverse_optimization_request(domain_id: str) -> InverseOptimizationRequest:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        conn.execute("BEGIN")
        _ensure_local_decision_feedback_tables(conn)
        episode_rows, event_watermark = _load_decision_training_rows(conn, domain_id)
        episodes = tuple(
            InverseTrainingEpisode(
                episode=DecisionEpisode(
                    episode_id=str(row["episode_id"]),
                    domain_id=str(row["domain_id"]),
                    run_id=str(row["run_id"]),
                    preference_context_fingerprint=str(row["preference_context_fingerprint"]),
                    qualification_context_fingerprint=str(
                        row["qualification_context_fingerprint"]
                    ),
                    ranking_contract_fingerprint=str(row["ranking_contract_fingerprint"]),
                    embedding_contract_fingerprint=str(row["embedding_contract_fingerprint"]),
                    baseline_policy_fingerprint=str(row["baseline_policy_fingerprint"]),
                    embedding_model=str(row["embedding_model"]),
                    embedding_dimension=int(row["embedding_dimension"]),
                    rating_scale_version=str(row["rating_scale_version"]),
                    candidate_set_fingerprint=str(row["candidate_set_fingerprint"]),
                    source_stage_artifact_fingerprint=str(
                        row["source_stage_artifact_fingerprint"]
                    ),
                    created_at=datetime.datetime.fromisoformat(str(row["created_at"])),
                ),
                alternatives=tuple(
                    DecisionAlternative(
                        episode_id=str(row["episode_id"]),
                        alternative_id=str(alternative["alternative_id"]),
                        displayed_rank=int(alternative["displayed_rank"]),
                        baseline_fit=float(alternative["baseline_fit"]),
                        baseline_fit_label=str(alternative["baseline_fit_label"]),
                        normalized_embedding_json=str(
                            alternative["normalized_embedding_json"]
                        ),
                        embedding_vector_fingerprint=str(
                            alternative["embedding_vector_fingerprint"]
                        ),
                        source_job_url=str(alternative["source_job_url"]),
                        shortlist_origin=str(alternative["shortlist_origin"]),
                        created_at=datetime.datetime.fromisoformat(
                            str(alternative["created_at"])
                        ),
                    )
                    for alternative in row["alternatives"]
                ),
                events=tuple(
                    DecisionRatingEvent(
                        event_sequence=int(event["event_sequence"]),
                        event_id=str(event["event_id"]),
                        episode_id=str(event["episode_id"]),
                        alternative_id=str(event["alternative_id"]),
                        event_type=RatingEventType(str(event["event_type"])),
                        rating=(
                            None
                            if event["rating"] is None
                            else RatingValue(int(event["rating"]))
                        ),
                        rating_scale_version=str(event["rating_scale_version"]),
                        acted_by=str(event["acted_by"]),
                        created_at=datetime.datetime.fromisoformat(str(event["created_at"])),
                    )
                    for event in row["events"]
                ),
                events_loaded_through_sequence=max(
                    (int(event["event_sequence"]) for event in row["events"]),
                    default=0,
                ),
                evaluation_context=None,
            )
            for row in episode_rows
        )
        conn.commit()
        return InverseOptimizationRequest(
            schema_version="inverse_optimization_request_v1",
            domain_id=domain_id,
            event_watermark=event_watermark,
            episodes=episodes,
        )

def _append_policy_event(
    conn: sqlite3.Connection,
    *,
    domain_id: str,
    runtime_contract_fingerprint: str,
    previous_snapshot_id: str | None,
    target_snapshot_id: str | None,
    action: str,
    reason_code: str,
    expected_parent_ref: str | None,
    evidence_head_fingerprint: str | None,
    acted_by: str,
) -> dict[str, Any]:
    created_at = _policy_now()
    payload = {
        "domain_id": domain_id,
        "runtime_contract_fingerprint": runtime_contract_fingerprint,
        "previous_snapshot_id": previous_snapshot_id,
        "target_snapshot_id": target_snapshot_id,
        "action": action,
        "reason_code": reason_code,
        "expected_parent_ref": expected_parent_ref,
        "evidence_head_fingerprint": evidence_head_fingerprint,
        "acted_by": str(acted_by).strip(),
    }
    if not payload["acted_by"]:
        raise ValueError("acted_by must be nonempty")
    payload["created_at"] = created_at
    payload["activation_event_id"] = f"pae_{build_contract_fingerprint(payload)}"
    columns = (
        "activation_event_id", "domain_id", "runtime_contract_fingerprint",
        "previous_snapshot_id", "target_snapshot_id", "action", "reason_code",
        "expected_parent_ref", "evidence_head_fingerprint", "acted_by", "created_at",
    )
    _insert_policy_row(conn, "policy_activation_events", columns, payload)
    process_event = build_process_event(
        process_type="optimization",
        process_id=domain_id,
        operation=action,
        state="rejected" if action in {"reject", "stale"} else "succeeded",
        level="warning" if action in {"reject", "stale"} else "info",
        message=f"Optimization {action}: {reason_code}",
        payload=payload,
        diagnostic_refs=[
            {"kind": "policy_activation_event", "id": payload["activation_event_id"]},
            *([{"kind": "ranking_policy_snapshot", "id": target_snapshot_id}] if target_snapshot_id else []),
        ],
        event_id=str(payload["activation_event_id"]),
        recorded_at=datetime.datetime.fromisoformat(created_at),
    )
    _insert_process_event(
        conn, process_event, delivery_sinks=("langfuse",), raise_on_conflict=True
    )
    return payload


def activate_ranking_policy_candidate(
    policy_snapshot_id: str,
    *,
    expected_parent_ref: str,
    acted_by: str,
    evidence_head_fingerprint: str | None = None,
    current_runtime_contract_fingerprint: str,
    current_compiler_policy_fingerprint: str,
    current_decision_learning_policy_fingerprint: str,
    current_optimizer_policy_fingerprint: str,
    current_activation_policy_fingerprint: str,
) -> dict[str, Any]:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        _ensure_process_event_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        candidate = _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", policy_snapshot_id)
        if candidate is None:
            raise KeyError(policy_snapshot_id)
        if candidate["status"] == "active":
            conn.commit()
            return candidate
        if candidate["status"] != "candidate":
            raise ValueError("snapshot is not candidate")
        training = _fetch_policy_row(
            conn,
            "inverse_training_runs",
            "training_run_id",
            str(candidate["training_run_id"]),
        )
        candidate_evidence_head = (
            (training.get("result_json") or {}).get("evidence_head_fingerprint")
            if training is not None
            else None
        )
        cursor = conn.execute(
            "SELECT * FROM ranking_policy_snapshots WHERE domain_id = ? AND runtime_contract_fingerprint = ? AND status = 'active'",
            (candidate["domain_id"], candidate["runtime_contract_fingerprint"]),
        )
        active = _row_dict(cursor, cursor.fetchone())
        current_parent = (
            f"learned:{active['policy_snapshot_id']}"
            if active is not None
            else f"zero_residual:{candidate['baseline_policy_fingerprint']}"
        )
        stale_reason = None
        if (
            evidence_head_fingerprint is not None
            and candidate_evidence_head is not None
            and evidence_head_fingerprint != candidate_evidence_head
        ):
            stale_reason = ("evidence_changed", "candidate evidence changed")
        elif expected_parent_ref != current_parent or candidate["parent_policy_ref"] != current_parent:
            stale_reason = ("parent_changed", "candidate parent changed")
        else:
            provenance_checks = (
                (
                    "runtime_contract_fingerprint",
                    current_runtime_contract_fingerprint,
                    "runtime_contract_changed",
                    "candidate runtime contract changed",
                ),
                (
                    "compiler_policy_fingerprint",
                    current_compiler_policy_fingerprint,
                    "compiler_policy_changed",
                    "candidate compiler policy changed",
                ),
                (
                    "activation_policy_fingerprint",
                    current_activation_policy_fingerprint,
                    "activation_policy_changed",
                    "candidate activation policy changed",
                ),
                (
                    "optimizer_policy_fingerprint",
                    current_optimizer_policy_fingerprint,
                    "optimizer_policy_changed",
                    "candidate optimizer policy changed",
                ),
                (
                    "decision_learning_policy_fingerprint",
                    current_decision_learning_policy_fingerprint,
                    "decision_learning_policy_changed",
                    "candidate decision learning policy changed",
                ),
            )
            stale_reason = next(
                (
                    (reason_code, message)
                    for field, current_value, reason_code, message in provenance_checks
                    if candidate[field] != current_value
                ),
                None,
            )
        if stale_reason is not None:
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'stale' WHERE policy_snapshot_id = ?",
                (policy_snapshot_id,),
            )
            _append_policy_event(
                conn,
                domain_id=candidate["domain_id"],
                runtime_contract_fingerprint=candidate["runtime_contract_fingerprint"],
                previous_snapshot_id=active["policy_snapshot_id"] if active else None,
                target_snapshot_id=policy_snapshot_id,
                action="stale",
                reason_code=stale_reason[0],
                expected_parent_ref=expected_parent_ref,
                evidence_head_fingerprint=evidence_head_fingerprint,
                acted_by=acted_by,
            )
            conn.commit()
            raise ValueError(stale_reason[1])
        if active is not None:
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'retired' WHERE policy_snapshot_id = ?",
                (active["policy_snapshot_id"],),
            )
            _append_policy_event(
                conn,
                domain_id=candidate["domain_id"],
                runtime_contract_fingerprint=candidate["runtime_contract_fingerprint"],
                previous_snapshot_id=active["policy_snapshot_id"],
                target_snapshot_id=policy_snapshot_id,
                action="retire",
                reason_code="superseded",
                expected_parent_ref=expected_parent_ref,
                evidence_head_fingerprint=evidence_head_fingerprint,
                acted_by=acted_by,
            )
        conn.execute(
            "UPDATE ranking_policy_snapshots SET status = 'active', activated_at = ? WHERE policy_snapshot_id = ?",
            (_policy_now(), policy_snapshot_id),
        )
        _append_policy_event(
            conn,
            domain_id=candidate["domain_id"],
            runtime_contract_fingerprint=candidate["runtime_contract_fingerprint"],
            previous_snapshot_id=active["policy_snapshot_id"] if active else None,
            target_snapshot_id=policy_snapshot_id,
            action="activate",
            reason_code="manual_activation",
            expected_parent_ref=expected_parent_ref,
            evidence_head_fingerprint=evidence_head_fingerprint,
            acted_by=acted_by,
        )
        conn.commit()
        return _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", policy_snapshot_id) or candidate


def reject_ranking_policy_candidate(
    policy_snapshot_id: str,
    *,
    acted_by: str,
    reason: str,
) -> dict[str, Any]:
    if not str(reason).strip():
        raise ValueError("reason must be nonempty")
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        _ensure_process_event_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        candidate = _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", policy_snapshot_id)
        if candidate is None:
            raise KeyError(policy_snapshot_id)
        if candidate["status"] == "rejected":
            cursor = conn.execute(
                "SELECT reason_code FROM policy_activation_events WHERE target_snapshot_id = ? AND action = 'reject'",
                (policy_snapshot_id,),
            )
            event = cursor.fetchone()
            if event is None or str(event[0]) != str(reason).strip():
                raise ValueError("conflicting rejection reason")
            conn.commit()
            return candidate
        if candidate["status"] != "candidate":
            raise ValueError("snapshot is not candidate")
        conn.execute(
            "UPDATE ranking_policy_snapshots SET status = 'rejected' WHERE policy_snapshot_id = ?",
            (policy_snapshot_id,),
        )
        _append_policy_event(
            conn,
            domain_id=candidate["domain_id"],
            runtime_contract_fingerprint=candidate["runtime_contract_fingerprint"],
            previous_snapshot_id=None,
            target_snapshot_id=policy_snapshot_id,
            action="reject",
            reason_code=str(reason).strip(),
            expected_parent_ref=candidate["parent_policy_ref"],
            evidence_head_fingerprint=None,
            acted_by=acted_by,
        )
        conn.commit()
        return _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", policy_snapshot_id) or candidate


def rollback_ranking_policy(
    domain_id: str,
    *,
    expected_active: str,
    target: str,
    acted_by: str,
) -> dict[str, Any]:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        _ensure_process_event_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        current = _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", expected_active)
        if current is None or current["domain_id"] != domain_id or current["status"] != "active":
            raise ValueError("active snapshot changed")
        conn.execute(
            "UPDATE ranking_policy_snapshots SET status = 'retired' WHERE policy_snapshot_id = ?",
            (expected_active,),
        )
        target_id: str | None = None
        status = "zero_residual"
        if target != "zero_residual":
            restored = _fetch_policy_row(conn, "ranking_policy_snapshots", "policy_snapshot_id", target)
            if restored is None or restored["status"] != "retired":
                raise ValueError("rollback target must be retired")
            if restored["runtime_contract_fingerprint"] != current["runtime_contract_fingerprint"]:
                raise ValueError("rollback target is incompatible")
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'active', activated_at = ? WHERE policy_snapshot_id = ?",
                (_policy_now(), target),
            )
            target_id = target
            status = "active"
        _append_policy_event(
            conn,
            domain_id=domain_id,
            runtime_contract_fingerprint=current["runtime_contract_fingerprint"],
            previous_snapshot_id=expected_active,
            target_snapshot_id=target_id,
            action="rollback",
            reason_code="manual_rollback",
            expected_parent_ref=f"learned:{expected_active}",
            evidence_head_fingerprint=None,
            acted_by=acted_by,
        )
        conn.commit()
        return {"status": status, "policy_snapshot_id": target_id}


def resolve_active_ranking_policy(domain_id: str, runtime_contract_fingerprint: str) -> dict[str, Any] | None:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        cursor = conn.execute(
            "SELECT * FROM ranking_policy_snapshots WHERE domain_id = ? AND runtime_contract_fingerprint = ? AND status = 'active'",
            (domain_id, runtime_contract_fingerprint),
        )
        rows = cursor.fetchall()
        if len(rows) > 1:
            raise ValueError("multiple active ranking policies")
        return _row_dict(cursor, rows[0]) if rows else None


def inspect_ranking_policy_lifecycle(
    domain_id: str,
    *,
    limit: int | None = None,
) -> dict[str, Any]:
    if limit is not None and limit <= 0:
        raise ValueError("limit must be positive")
    order = "DESC" if limit is not None else "ASC"
    limit_sql = " LIMIT ?" if limit is not None else ""
    parameters: tuple[Any, ...] = (domain_id, limit) if limit is not None else (domain_id,)
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        snapshots_cursor = conn.execute(
            f"SELECT * FROM ranking_policy_snapshots WHERE domain_id = ? ORDER BY created_at {order}, policy_snapshot_id {order}{limit_sql}",
            parameters,
        )
        snapshots = [_row_dict(snapshots_cursor, row) for row in snapshots_cursor.fetchall()]
        events_cursor = conn.execute(
            f"SELECT * FROM policy_activation_events WHERE domain_id = ? ORDER BY created_at {order}, activation_event_id {order}{limit_sql}",
            parameters,
        )
        events = [_row_dict(events_cursor, row) for row in events_cursor.fetchall()]
        training_cursor = conn.execute(
            f"SELECT * FROM inverse_training_runs WHERE domain_id = ? ORDER BY created_at {order}, training_run_id {order}{limit_sql}",
            parameters,
        )
        training_runs = [_row_dict(training_cursor, row) for row in training_cursor.fetchall()]
        active = next((row for row in snapshots if row["status"] == "active"), None)
        if active is None and limit is not None:
            active_cursor = conn.execute(
                "SELECT * FROM ranking_policy_snapshots WHERE domain_id = ? AND status = 'active'",
                (domain_id,),
            )
            active_row = active_cursor.fetchone()
            active = _row_dict(active_cursor, active_row) if active_row is not None else None
        for snapshot in snapshots:
            snapshot["rollback_eligible"] = bool(
                active is not None
                and snapshot["status"] == "retired"
                and snapshot["runtime_contract_fingerprint"]
                == active["runtime_contract_fingerprint"]
            )
        return {
            "snapshots": snapshots,
            "events": events,
            "training_runs": training_runs,
            "active_snapshot": active,
        }

def _episode_values(episode: DecisionEpisode) -> tuple[Any, ...]:
    return (
        episode.episode_id,
        episode.domain_id,
        episode.run_id,
        episode.preference_context_fingerprint,
        episode.qualification_context_fingerprint,
        episode.ranking_contract_fingerprint,
        episode.embedding_contract_fingerprint,
        episode.baseline_policy_fingerprint,
        episode.embedding_model,
        episode.embedding_dimension,
        episode.rating_scale_version,
        episode.candidate_set_fingerprint,
        episode.source_stage_artifact_fingerprint,
        episode.created_at.isoformat(),
    )


def _alternative_values(alternative: DecisionAlternative) -> tuple[Any, ...]:
    return (
        alternative.episode_id,
        alternative.alternative_id,
        alternative.displayed_rank,
        alternative.baseline_fit,
        alternative.baseline_fit_label,
        alternative.normalized_embedding_json,
        alternative.embedding_vector_fingerprint,
        alternative.source_job_url,
        alternative.shortlist_origin,
        alternative.created_at.isoformat(),
    )


def materialize_episode_and_append_rating(
    episode: DecisionEpisode,
    alternatives: tuple[DecisionAlternative, ...] | list[DecisionAlternative],
    event: DecisionRatingEvent,
) -> dict[str, str]:
    db_path = Path(_local_sqlite_path())
    alternative_rows = tuple(alternatives)
    if not alternative_rows:
        raise ValueError("decision episode requires alternatives")
    if event.episode_id != episode.episode_id:
        raise ValueError("rating event episode mismatch")
    if event.rating_scale_version != episode.rating_scale_version:
        raise ValueError("rating scale conflicts with episode")
    with _sqlite_connection(db_path) as conn:
        try:
            conn.execute("BEGIN IMMEDIATE")
            _ensure_local_decision_feedback_tables(conn)
            existing_episode = conn.execute(
                """
                SELECT episode_id, domain_id, run_id, preference_context_fingerprint,
                       qualification_context_fingerprint, ranking_contract_fingerprint,
                       embedding_contract_fingerprint, baseline_policy_fingerprint,
                       embedding_model, embedding_dimension, rating_scale_version,
                       candidate_set_fingerprint, source_stage_artifact_fingerprint, created_at
                FROM decision_episodes WHERE episode_id = ?
                """,
                (episode.episode_id,),
            ).fetchone()
            expected_episode = _episode_values(episode)
            if existing_episode is None:
                conn.execute(
                    """
                    INSERT INTO decision_episodes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    expected_episode,
                )
                conn.executemany(
                    """
                    INSERT INTO decision_episode_alternatives VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    [_alternative_values(alternative) for alternative in alternative_rows],
                )
            elif tuple(existing_episode[:-1]) != expected_episode[:-1]:
                raise ValueError("existing decision episode conflicts with source")
            else:
                existing_alternatives = conn.execute(
                    """
                    SELECT episode_id, alternative_id, displayed_rank, baseline_fit,
                           baseline_fit_label, normalized_embedding_json,
                           embedding_vector_fingerprint, source_job_url, shortlist_origin, created_at
                    FROM decision_episode_alternatives
                    WHERE episode_id = ? ORDER BY displayed_rank, alternative_id
                    """,
                    (episode.episode_id,),
                ).fetchall()
                expected_alternatives = sorted(
                    (_alternative_values(alternative) for alternative in alternative_rows),
                    key=lambda row: (int(row[2]), str(row[1])),
                )
                if [tuple(row[:-1]) for row in existing_alternatives] != [row[:-1] for row in expected_alternatives]:
                    raise ValueError("existing decision alternatives conflict with source")
            target_exists = conn.execute(
                """
                SELECT 1 FROM decision_episode_alternatives
                WHERE episode_id = ? AND alternative_id = ?
                """,
                (episode.episode_id, event.alternative_id),
            ).fetchone()
            if target_exists is None:
                raise ValueError("unknown decision alternative")
            conn.execute(
                """
                INSERT INTO decision_rating_events (
                    event_id, episode_id, alternative_id, event_type, rating,
                    rating_scale_version, acted_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.episode_id,
                    event.alternative_id,
                    event.event_type.value,
                    int(event.rating) if event.rating is not None else None,
                    event.rating_scale_version,
                    event.acted_by,
                    event.created_at.isoformat(),
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"persistence_status": "persisted", "degradation_reason": "none"}


def list_decision_rating_events_for_run(run_id: str) -> list[DecisionRatingEvent]:
    db_path = Path(_local_sqlite_path())
    if not db_path.exists():
        return []
    with _sqlite_connection(db_path) as conn:
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'decision_rating_events'"
        ).fetchone()
        if table_exists is None:
            return []
        rows = conn.execute(
            """
            SELECT event_sequence, event_id, e.episode_id, alternative_id, event_type,
                   rating, e.rating_scale_version, acted_by, e.created_at
            FROM decision_rating_events e
            JOIN decision_episodes p ON p.episode_id = e.episode_id
            WHERE p.run_id = ?
            ORDER BY event_sequence
            """,
            (run_id,),
        ).fetchall()
    return [
        DecisionRatingEvent(
            event_sequence=int(row[0]),
            event_id=str(row[1]),
            episode_id=str(row[2]),
            alternative_id=str(row[3]),
            event_type=RatingEventType(str(row[4])),
            rating=RatingValue(int(row[5])) if row[5] is not None else None,
            rating_scale_version=str(row[6]),
            acted_by=str(row[7]),
            created_at=datetime.datetime.fromisoformat(str(row[8])),
        )
        for row in rows
    ]
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
            source_job_url TEXT,
            fit_factor_results_json TEXT,
            eligibility_policy_fingerprint TEXT,
            eligibility_decision TEXT,
            eligibility_reason_codes_json TEXT
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
    for column_name in (
        "fit_factor_results_json",
        "eligibility_policy_fingerprint",
        "eligibility_decision",
        "eligibility_reason_codes_json",
    ):
        if column_name not in existing_columns:
            conn.execute(
                f"ALTER TABLE rule_filter_results ADD COLUMN {column_name} TEXT"
            )

def _encode_filter_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def replace_filter_results(run_id: str, rows: list[dict[str, Any]]) -> None:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_rule_filter_results_table(conn)
        conn.execute("DELETE FROM rule_filter_results WHERE run_id = ?", (run_id,))
        conn.executemany(
            """
            INSERT INTO rule_filter_results (
                run_id,
                job_url,
                passed,
                reasons,
                marks_json,
                filtered_at,
                raw_job_fingerprint,
                source_job_url,
                fit_factor_results_json,
                eligibility_policy_fingerprint,
                eligibility_decision,
                eligibility_reason_codes_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    run_id,
                    str(row.get("job_url") or ""),
                    1 if bool(row.get("passed")) else 0,
                    _encode_filter_json(list(row.get("reasons") or [])),
                    _encode_filter_json(list(row.get("marks") or [])),
                    str(row.get("filtered_at") or ""),
                    row.get("raw_job_fingerprint"),
                    row.get("source_job_url"),
                    _encode_filter_json(dict(row.get("fit_factor_results") or {})),
                    row.get("eligibility_policy_fingerprint"),
                    row.get("eligibility_decision"),
                    _encode_filter_json(list(row.get("eligibility_reason_codes") or [])),
                )
                for row in rows
            ],
        )
        conn.commit()

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


def _ensure_process_event_tables(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS process_events (
            schema_version TEXT NOT NULL,
            event_id TEXT PRIMARY KEY,
            process_type TEXT NOT NULL,
            process_id TEXT NOT NULL,
            operation TEXT NOT NULL,
            state TEXT NOT NULL,
            level TEXT NOT NULL,
            message TEXT NOT NULL,
            payload_json TEXT,
            diagnostic_refs_json TEXT,
            trace_context_json TEXT,
            recorded_at TEXT NOT NULL,
            event_fingerprint TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS process_events_process_order
            ON process_events(process_type, process_id, recorded_at, event_id);
        CREATE TABLE IF NOT EXISTS process_event_integrity_conflicts (
            conflict_id TEXT PRIMARY KEY,
            process_type TEXT NOT NULL,
            process_id TEXT NOT NULL,
            event_id TEXT,
            reason TEXT NOT NULL,
            evidence_json TEXT NOT NULL,
            recorded_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS process_event_conflicts_process_order
            ON process_event_integrity_conflicts(process_type, process_id, recorded_at, conflict_id);
        CREATE TABLE IF NOT EXISTS process_event_deliveries (
            event_id TEXT NOT NULL,
            sink TEXT NOT NULL,
            status TEXT NOT NULL,
            reason TEXT,
            attempt_count INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(event_id, sink),
            FOREIGN KEY(event_id) REFERENCES process_events(event_id)
        );
        CREATE TABLE IF NOT EXISTS process_event_migrations (
            migration_id TEXT PRIMARY KEY,
            completed_at TEXT NOT NULL,
            source_row_count INTEGER NOT NULL,
            source_fingerprint TEXT NOT NULL
        );
        CREATE TRIGGER IF NOT EXISTS process_events_immutable_update
        BEFORE UPDATE ON process_events BEGIN
            SELECT RAISE(ABORT, 'process_events are immutable');
        END;
        CREATE TRIGGER IF NOT EXISTS process_events_immutable_delete
        BEFORE DELETE ON process_events BEGIN
            SELECT RAISE(ABORT, 'process_events are immutable');
        END;
        """
    )
    _migrate_legacy_process_events(conn)


def _process_event_record(event: ProcessEvent) -> dict[str, Any]:
    payload = dataclasses.asdict(event)
    payload["recorded_at"] = event.recorded_at.isoformat()
    return payload


def _process_event_from_record(record: dict[str, Any]) -> ProcessEvent:
    timestamp = datetime.datetime.fromisoformat(str(record["recorded_at"]))
    if timestamp.tzinfo is None:
        timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
    event = ProcessEvent(
        schema_version=str(record["schema_version"]),
        event_id=str(record["event_id"]),
        process_type=str(record["process_type"]),
        process_id=str(record["process_id"]),
        operation=str(record["operation"]),
        state=str(record["state"]),
        level=str(record["level"]),
        message=str(record["message"]),
        payload_json=record.get("payload_json"),
        diagnostic_refs_json=record.get("diagnostic_refs_json"),
        trace_context_json=record.get("trace_context_json"),
        recorded_at=timestamp.astimezone(datetime.timezone.utc),
        event_fingerprint=str(record["event_fingerprint"]),
    )
    rebuilt = build_process_event(
        process_type=event.process_type,
        process_id=event.process_id,
        operation=event.operation,
        state=event.state,
        level=event.level,
        message=event.message,
        payload=_decode_json_or_none(event.payload_json),
        diagnostic_refs=_decode_json_or_none(event.diagnostic_refs_json),
        trace_context=_decode_json_or_none(event.trace_context_json),
        event_id=event.event_id,
        recorded_at=event.recorded_at,
    )
    if rebuilt.event_fingerprint != event.event_fingerprint:
        raise ValueError("process event fingerprint mismatch")
    return event


def _insert_process_event(
    conn: sqlite3.Connection,
    event: ProcessEvent,
    *,
    delivery_sinks: tuple[str, ...] = (),
    raise_on_conflict: bool = False,
) -> str:
    existing = conn.execute(
        "SELECT event_fingerprint FROM process_events WHERE event_id = ?",
        (event.event_id,),
    ).fetchone()
    if existing is not None:
        if str(existing[0]) == event.event_fingerprint:
            return "equal"
        conflict = ProcessEventIntegrityConflict(
            conflict_id=str(uuid.uuid4()),
            process_type=event.process_type,
            process_id=event.process_id,
            event_id=event.event_id,
            reason="fingerprint_mismatch",
            evidence_json=json.dumps(
                {
                    "existing_fingerprint": str(existing[0]),
                    "incoming_fingerprint": event.event_fingerprint,
                },
                sort_keys=True,
                separators=(",", ":"),
            ),
            recorded_at=datetime.datetime.now(datetime.timezone.utc),
        )
        conn.execute(
            """
            INSERT INTO process_event_integrity_conflicts(
                conflict_id, process_type, process_id, event_id, reason, evidence_json, recorded_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                conflict.conflict_id,
                conflict.process_type,
                conflict.process_id,
                conflict.event_id,
                conflict.reason,
                conflict.evidence_json,
                conflict.recorded_at.isoformat(),
            ),
        )
        if raise_on_conflict:
            raise ValueError("process event fingerprint conflict")
        return "conflict"
    record = _process_event_record(event)
    conn.execute(
        """
        INSERT INTO process_events(
            schema_version, event_id, process_type, process_id, operation, state, level,
            message, payload_json, diagnostic_refs_json, trace_context_json, recorded_at,
            event_fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        tuple(record[key] for key in (
            "schema_version", "event_id", "process_type", "process_id", "operation",
            "state", "level", "message", "payload_json", "diagnostic_refs_json",
            "trace_context_json", "recorded_at", "event_fingerprint"
        )),
    )
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for sink in delivery_sinks:
        conn.execute(
            """
            INSERT OR IGNORE INTO process_event_deliveries(
                event_id, sink, status, reason, attempt_count, updated_at
            ) VALUES (?, ?, 'pending', NULL, 0, ?)
            """,
            (event.event_id, sink, now),
        )
    return "inserted"


def _migrate_legacy_process_events(conn: sqlite3.Connection) -> None:
    migration_id = "local_pipeline_run_events_to_process_events_v1"
    if conn.execute(
        "SELECT 1 FROM process_event_migrations WHERE migration_id = ?",
        (migration_id,),
    ).fetchone():
        return
    table_exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'local_pipeline_run_events'"
    ).fetchone()
    rows: list[sqlite3.Row] = []
    if table_exists:
        previous_factory = conn.row_factory
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT run_id, event_id, stage, level, message, payload_json, created_at
            FROM local_pipeline_run_events
            ORDER BY created_at, rowid
            """
        ).fetchall()
        conn.row_factory = previous_factory
        for row in rows:
            payload = _decode_json_or_none(row["payload_json"])
            if payload is None and row["payload_json"] is not None:
                payload = {"legacy_payload_json": str(row["payload_json"])}
            event = build_process_event(
                process_type="pipeline",
                process_id=str(row["run_id"]),
                operation=str(row["stage"]),
                state="recorded",
                level=str(row["level"]),
                message=str(row["message"]),
                payload=payload,
                event_id=str(row["event_id"]),
                recorded_at=datetime.datetime.fromisoformat(str(row["created_at"])),
            )
            _insert_process_event(conn, event)
    source_identity = [
        [str(row["run_id"]), str(row["event_id"]), str(row["created_at"])]
        for row in rows
    ]
    conn.execute(
        """
        INSERT INTO process_event_migrations(
            migration_id, completed_at, source_row_count, source_fingerprint
        ) VALUES (?, ?, ?, ?)
        """,
        (
            migration_id,
            datetime.datetime.now(datetime.timezone.utc).isoformat(),
            len(rows),
            hashlib.sha256(
                json.dumps(source_identity, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest(),
        ),
    )


def _process_event_journal_dir(process_type: str, process_id: str) -> Path:
    identity = json.dumps(
        [str(process_type), str(process_id)],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return _local_event_history_dir() / hashlib.sha256(identity).hexdigest()


def _process_event_journal_file(event: ProcessEvent) -> Path:
    event_name = hashlib.sha256(event.event_id.encode("utf-8")).hexdigest()
    return _process_event_journal_dir(event.process_type, event.process_id) / f"{event_name}.json"


def _write_json_atomically(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("x", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _write_process_event_journal(event: ProcessEvent) -> None:
    path = _process_event_journal_file(event)
    if path.exists():
        existing = _process_event_from_record(json.loads(path.read_text(encoding="utf-8")))
        if existing.event_fingerprint == event.event_fingerprint:
            return
        conflict_path = path.parent / "_conflicts" / f"{uuid.uuid4().hex}.json"
        _write_json_atomically(
            conflict_path,
            {
                "conflict_id": conflict_path.stem,
                "process_type": event.process_type,
                "process_id": event.process_id,
                "event_id": event.event_id,
                "reason": "fingerprint_mismatch",
                "evidence_json": json.dumps(
                    {
                        "existing_fingerprint": existing.event_fingerprint,
                        "incoming_fingerprint": event.event_fingerprint,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "recorded_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            },
        )
        raise ValueError("process event journal fingerprint conflict")
    _write_json_atomically(path, _process_event_record(event))


def _read_process_event_journal(
    process_type: str, process_id: str
) -> tuple[list[tuple[ProcessEvent, Path]], list[ProcessEventIntegrityConflict]]:
    directory = _process_event_journal_dir(process_type, process_id)
    events: list[tuple[ProcessEvent, Path]] = []
    conflicts: list[ProcessEventIntegrityConflict] = []
    if not directory.exists():
        return events, conflicts
    for path in sorted(directory.glob("*.json")):
        try:
            events.append((_process_event_from_record(json.loads(path.read_text(encoding="utf-8"))), path))
        except Exception as exc:
            conflicts.append(ProcessEventIntegrityConflict(
                conflict_id=f"journal:{path.name}",
                process_type=process_type,
                process_id=process_id,
                event_id=None,
                reason="journal_malformed",
                evidence_json=json.dumps({"file": path.name, "error": str(exc)}, sort_keys=True),
                recorded_at=datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc),
            ))
    conflict_dir = directory / "_conflicts"
    if conflict_dir.exists():
        for path in sorted(conflict_dir.glob("*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
                conflicts.append(ProcessEventIntegrityConflict(
                    conflict_id=str(record["conflict_id"]),
                    process_type=str(record["process_type"]),
                    process_id=str(record["process_id"]),
                    event_id=record.get("event_id"),
                    reason=str(record["reason"]),
                    evidence_json=str(record["evidence_json"]),
                    recorded_at=datetime.datetime.fromisoformat(str(record["recorded_at"])),
                ))
            except Exception as exc:
                conflicts.append(ProcessEventIntegrityConflict(
                    conflict_id=f"journal-conflict:{path.name}",
                    process_type=process_type,
                    process_id=process_id,
                    event_id=None,
                    reason="journal_malformed",
                    evidence_json=json.dumps({"file": path.name, "error": str(exc)}, sort_keys=True),
                    recorded_at=datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc),
                ))
    return events, conflicts


def append_process_event(
    event: ProcessEvent,
    *,
    delivery_sinks: tuple[str, ...] = (),
    conn: sqlite3.Connection | None = None,
    raise_on_conflict: bool = False,
) -> dict[str, str]:
    if conn is not None:
        _ensure_process_event_tables(conn)
        disposition = _insert_process_event(
            conn, event, delivery_sinks=delivery_sinks, raise_on_conflict=raise_on_conflict
        )
        return {
            "persistence_status": "persisted" if disposition != "conflict" else "failed",
            "degradation_reason": "none" if disposition != "conflict" else "event_fingerprint_conflict",
            "persistence_backend": "sqlite",
        }
    db_path = Path(_local_sqlite_path())
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with _sqlite_connection(db_path) as local_conn:
            _ensure_process_event_tables(local_conn)
            disposition = _insert_process_event(
                local_conn,
                event,
                delivery_sinks=delivery_sinks,
                raise_on_conflict=raise_on_conflict,
            )
            local_conn.commit()
        return {
            "persistence_status": "persisted" if disposition != "conflict" else "failed",
            "degradation_reason": "none" if disposition != "conflict" else "event_fingerprint_conflict",
            "persistence_backend": "sqlite",
        }
    except Exception as exc:
        logger.warning(
            "process event sqlite persistence degraded for process_type=%s process_id=%s: %s",
            event.process_type,
            event.process_id,
            exc,
        )
        try:
            _write_process_event_journal(event)
            return {
                "persistence_status": "persisted",
                "degradation_reason": "sqlite_event_insert_failed",
                "persistence_backend": "journal",
            }
        except Exception as file_exc:
            logger.warning(
                "process event journal persistence degraded for process_type=%s process_id=%s: %s",
                event.process_type,
                event.process_id,
                file_exc,
            )
            return {
                "persistence_status": "failed",
                "degradation_reason": "event_insert_failed_no_local_fallback",
                "persistence_backend": "none",
            }


def record_process_event_delivery(
    event_id: str, sink: str, status: str, reason: str | None = None
) -> None:
    if status not in {"pending", "delivered", "failed"}:
        raise ValueError("invalid process event delivery status")
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_process_event_tables(conn)
        conn.execute(
            """
            INSERT INTO process_event_deliveries(
                event_id, sink, status, reason, attempt_count, updated_at
            ) VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(event_id, sink) DO UPDATE SET
                status = excluded.status,
                reason = excluded.reason,
                attempt_count = process_event_deliveries.attempt_count + 1,
                updated_at = excluded.updated_at
            """,
            (
                event_id, sink, status, reason,
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
            ),
        )
        conn.commit()


def list_pending_process_event_deliveries(
    *, limit: int = 20
) -> list[dict[str, Any]]:
    db_path = Path(_local_sqlite_path())
    if not db_path.exists():
        return []
    with _sqlite_connection(db_path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_process_event_tables(conn)
        rows = conn.execute(
            """
            SELECT e.*, d.sink, d.status AS delivery_status, d.reason AS delivery_reason,
                   d.attempt_count, d.updated_at
            FROM process_event_deliveries d
            JOIN process_events e ON e.event_id = d.event_id
            WHERE d.status IN ('pending', 'failed')
            ORDER BY d.updated_at, e.recorded_at, e.event_id
            LIMIT ?
            """,
            (max(1, min(int(limit), 100)),),
        ).fetchall()
    return [
        {
            "event": _process_event_from_record(dict(row)),
            "sink": str(row["sink"]),
            "status": str(row["delivery_status"]),
            "reason": row["delivery_reason"],
            "attempt_count": int(row["attempt_count"]),
        }
        for row in rows
    ]


def get_process_events(
    process_type: str,
    process_id: str,
    *,
    limit: int = 200,
) -> dict[str, Any]:
    normalized_limit = max(1, min(int(limit), 500))
    sqlite_events: list[ProcessEvent] = []
    sqlite_conflicts: list[ProcessEventIntegrityConflict] = []
    deliveries: list[dict[str, Any]] = []
    db_path = Path(_local_sqlite_path())
    if db_path.exists():
        with _sqlite_connection(db_path) as conn:
            conn.row_factory = sqlite3.Row
            _ensure_process_event_tables(conn)
            rows = conn.execute(
                """
                SELECT * FROM process_events
                WHERE process_type = ? AND process_id = ?
                ORDER BY recorded_at, event_id
                """,
                (process_type, process_id),
            ).fetchall()
            sqlite_events = [_process_event_from_record(dict(row)) for row in rows]
            conflict_rows = conn.execute(
                """
                SELECT * FROM process_event_integrity_conflicts
                WHERE process_type = ? AND process_id = ?
                ORDER BY recorded_at, conflict_id
                """,
                (process_type, process_id),
            ).fetchall()
            sqlite_conflicts = [
                ProcessEventIntegrityConflict(
                    conflict_id=str(row["conflict_id"]),
                    process_type=str(row["process_type"]),
                    process_id=str(row["process_id"]),
                    event_id=row["event_id"],
                    reason=str(row["reason"]),
                    evidence_json=str(row["evidence_json"]),
                    recorded_at=datetime.datetime.fromisoformat(str(row["recorded_at"])),
                )
                for row in conflict_rows
            ]
            deliveries = [dict(row) for row in conn.execute(
                """
                SELECT d.* FROM process_event_deliveries d
                JOIN process_events e ON e.event_id = d.event_id
                WHERE e.process_type = ? AND e.process_id = ?
                ORDER BY d.event_id, d.sink
                """,
                (process_type, process_id),
            ).fetchall()]
            journal_events, journal_conflicts = _read_process_event_journal(process_type, process_id)
            replayed_paths: list[Path] = []
            for journal_event, journal_path in journal_events:
                try:
                    disposition = _insert_process_event(conn, journal_event)
                    if disposition in {"inserted", "equal"}:
                        replayed_paths.append(journal_path)
                except Exception:
                    continue
            if replayed_paths:
                conn.commit()
                for replayed_path in replayed_paths:
                    replayed_path.unlink(missing_ok=True)
                rows = conn.execute(
                    """
                    SELECT * FROM process_events
                    WHERE process_type = ? AND process_id = ?
                    ORDER BY recorded_at, event_id
                    """,
                    (process_type, process_id),
                ).fetchall()
                sqlite_events = [_process_event_from_record(dict(row)) for row in rows]
    else:
        journal_events, journal_conflicts = _read_process_event_journal(process_type, process_id)
    by_id = {event.event_id: event for event in sqlite_events}
    for event, _path in journal_events:
        existing = by_id.get(event.event_id)
        if existing is None:
            by_id[event.event_id] = event
        elif existing.event_fingerprint != event.event_fingerprint:
            journal_conflicts.append(ProcessEventIntegrityConflict(
                conflict_id=f"merge:{event.event_id}:{event.event_fingerprint}",
                process_type=process_type,
                process_id=process_id,
                event_id=event.event_id,
                reason="fingerprint_mismatch",
                evidence_json=json.dumps({
                    "sqlite_fingerprint": existing.event_fingerprint,
                    "journal_fingerprint": event.event_fingerprint,
                }, sort_keys=True),
                recorded_at=datetime.datetime.now(datetime.timezone.utc),
            ))
    ordered = sorted(by_id.values(), key=lambda item: (item.recorded_at, item.event_id))
    return {
        "events": ordered[-normalized_limit:],
        "integrity_conflicts": sorted(
            [*sqlite_conflicts, *journal_conflicts],
            key=lambda item: (item.recorded_at, item.conflict_id),
        ),
        "deliveries": deliveries,
        "total_count": len(ordered),
        "next_cursor": None,
    }


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
    payload = _decode_json_or_none(event.payload_json)
    if payload is None and event.payload_json is not None:
        payload = {"legacy_payload_json": str(event.payload_json)}
    process_event = build_process_event(
        process_type="pipeline",
        process_id=event.run_id,
        operation=event.stage,
        state="recorded",
        level=event.level,
        message=event.message,
        payload=payload,
        event_id=event.event_id,
    )
    return append_process_event(process_event)


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
    page = get_process_events("pipeline", run_id, limit=500)
    return [
        RunEvent(
            run_id=event.process_id,
            event_id=event.event_id,
            stage=event.operation,
            level=event.level,
            message=event.message,
            created_at=event.recorded_at,
            payload_json=event.payload_json,
        )
        for event in page["events"]
    ]


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
        factor_results = _decode_json_or_none(row_dict.get("fit_factor_results_json"))
        row_dict["fit_factor_results"] = (
            factor_results if isinstance(factor_results, dict) else {}
        )
        row_dict["eligibility_reason_codes"] = _decode_reason_list(
            row_dict.get("eligibility_reason_codes_json")
        )
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

