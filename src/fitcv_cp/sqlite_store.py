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
import base64
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
from fitcv_cp.candidate_profile_seeds import build_candidate_profile_seeds
from fitcv_cp.models import (
    JobStageStatus,
    PipelineRun,
    ProcessEvent,
    ProcessEventIntegrityConflict,
    ResultBucket,
    RunEvent,
    RunStatus,
    build_process_event,
)
from fitcv_cp.run_lifecycle import (
    PROTOTYPE_STAGES,
    canonical_stage_id,
    can_archive_run,
    can_cancel_run,
    can_unarchive_run,
    decide_terminal_run,
    job_stage_status_from_outcome,
    result_bucket_for_job_stage,
    run_display_status,
    run_stage_status_from_pipeline,
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
CONTROL_PLANE_SCHEMA_VERSION = 2

class DatabaseSchemaIncompatibleError(RuntimeError):
    code = "database_schema_incompatible"

    def __init__(self, found_version: int) -> None:
        self.found_version = found_version
        super().__init__(
            f"Database schema is incompatible: found version {found_version}, expected {CONTROL_PLANE_SCHEMA_VERSION}."
        )


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

def _persist_initial_profile_state(
    conn: sqlite3.Connection,
    candidate_profiles: list[dict[str, Any]],
    startup_warning: dict[str, str] | None,
) -> None:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute("DELETE FROM candidate_profiles")
    conn.execute("DELETE FROM startup_warnings WHERE code = 'candidate_profile_setup_required'")
    for row in candidate_profiles:
        conn.execute(
            """
            INSERT INTO candidate_profiles (
                candidate_profile_id, name, description, profile_json, revision, checksum,
                is_active, is_default, sort_order, seed_manifest_revision, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row["candidate_profile_id"],
                row["name"],
                row["description"],
                row["profile_json"],
                row["revision"],
                row["checksum"],
                int(row["is_active"]),
                int(row["is_default"]),
                row["sort_order"],
                row["seed_manifest_revision"],
                now,
                now,
            ),
        )
    if startup_warning is not None:
        conn.execute(
            "INSERT INTO startup_warnings (code, message, action, created_at) VALUES (?, ?, ?, ?)",
            (startup_warning["code"], startup_warning["message"], startup_warning["action"], now),
        )


def _ensure_control_plane_schema(
    conn: sqlite3.Connection,
    *,
    candidate_profiles: list[dict[str, Any]] | None = None,
    startup_warning: dict[str, str] | None = None,
) -> None:
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    existing_tables = {
        str(row[0])
        for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
    }
    if version not in {0, CONTROL_PLANE_SCHEMA_VERSION} or (version == 0 and existing_tables):
        raise DatabaseSchemaIncompatibleError(version)
    schema = """
    CREATE TABLE IF NOT EXISTS candidate_profiles (
        candidate_profile_id TEXT PRIMARY KEY,
        name TEXT NOT NULL COLLATE NOCASE UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        profile_json TEXT NOT NULL CHECK (json_valid(profile_json)),
        revision INTEGER NOT NULL CHECK (revision > 0),
        checksum TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
        is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
        sort_order INTEGER NOT NULL DEFAULT 0,
        seed_manifest_revision TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_candidate_profiles_active_default
        ON candidate_profiles(is_default) WHERE is_active = 1 AND is_default = 1;

    CREATE TABLE IF NOT EXISTS startup_warnings (
        code TEXT PRIMARY KEY,
        message TEXT NOT NULL,
        action TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS pipeline_runs (
        run_id TEXT PRIMARY KEY,
        run_name TEXT NOT NULL CHECK (length(run_name) <= 120),
        backend_status TEXT NOT NULL CHECK (backend_status IN ('queued', 'running', 'awaiting_continue', 'cancelling', 'cancelled', 'succeeded', 'failed')),
        status_detail TEXT,
        triggered_by TEXT NOT NULL,
        trigger_source TEXT NOT NULL,
        trigger_mode TEXT NOT NULL,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        archived_at TEXT,
        archived_by TEXT,
        queue_job_id TEXT,
        orchestration_backend TEXT,
        orchestration_run_id TEXT,
        total_jobs INTEGER NOT NULL DEFAULT 0 CHECK (total_jobs >= 0),
        passed_jobs INTEGER NOT NULL DEFAULT 0 CHECK (passed_jobs >= 0),
        rejected_jobs INTEGER NOT NULL DEFAULT 0 CHECK (rejected_jobs >= 0),
        cvs_generated INTEGER NOT NULL DEFAULT 0 CHECK (cvs_generated >= 0),
        progress_completed INTEGER NOT NULL DEFAULT 0 CHECK (progress_completed >= 0),
        progress_total INTEGER NOT NULL DEFAULT 0 CHECK (progress_total >= 0),
        settings_revision TEXT NOT NULL,
        warning_json TEXT,
        error_code TEXT,
        error_message TEXT,
        partial_completion INTEGER NOT NULL DEFAULT 0 CHECK (partial_completion IN (0, 1)),
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0),
        compatibility_json TEXT NOT NULL CHECK (json_valid(compatibility_json)),
        CHECK (finished_at IS NULL OR backend_status IN ('cancelled', 'succeeded', 'failed')),
        CHECK (archived_at IS NULL OR backend_status NOT IN ('queued', 'running', 'awaiting_continue', 'cancelling'))
    );
    CREATE INDEX IF NOT EXISTS ix_pipeline_runs_created ON pipeline_runs(created_at DESC, run_id DESC);
    CREATE INDEX IF NOT EXISTS ix_pipeline_runs_archived ON pipeline_runs(archived_at, created_at DESC);

    CREATE TABLE IF NOT EXISTS run_inputs (
        run_id TEXT PRIMARY KEY REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
        original_filename TEXT NOT NULL,
        media_type TEXT NOT NULL,
        byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
        sha256 TEXT NOT NULL,
        record_count INTEGER NOT NULL CHECK (record_count >= 0),
        jobs_snapshot_json TEXT NOT NULL CHECK (json_valid(jobs_snapshot_json)),
        jobs_manifest_json TEXT NOT NULL CHECK (json_valid(jobs_manifest_json)),
        candidate_profile_id TEXT,
        candidate_profile_revision INTEGER,
        candidate_profile_name TEXT NOT NULL,
        candidate_profile_json TEXT NOT NULL CHECK (json_valid(candidate_profile_json)),
        settings_revision TEXT NOT NULL,
        settings_snapshot_json TEXT NOT NULL CHECK (json_valid(settings_snapshot_json)),
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS run_stage_executions (
        run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
        stage_id TEXT NOT NULL CHECK (stage_id IN ('enrichment', 'screening', 'shortlisting', 'ranking', 'cv-analysis', 'cv-generation')),
        ordinal INTEGER NOT NULL CHECK (ordinal BETWEEN 1 AND 6),
        status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'warning', 'partial', 'failed', 'cancelled', 'skipped')),
        progress_completed INTEGER NOT NULL DEFAULT 0 CHECK (progress_completed >= 0),
        progress_total INTEGER NOT NULL DEFAULT 0 CHECK (progress_total >= 0),
        passed_count INTEGER NOT NULL DEFAULT 0 CHECK (passed_count >= 0),
        rejected_count INTEGER NOT NULL DEFAULT 0 CHECK (rejected_count >= 0),
        started_at TEXT,
        finished_at TEXT,
        duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
        warning_json TEXT,
        error_code TEXT,
        error_message TEXT,
        evidence_reference TEXT,
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0),
        PRIMARY KEY (run_id, stage_id),
        UNIQUE (run_id, ordinal)
    );

    CREATE TABLE IF NOT EXISTS run_jobs (
        run_job_id TEXT PRIMARY KEY,
        run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
        source_index INTEGER NOT NULL CHECK (source_index >= 0),
        source_fingerprint TEXT NOT NULL,
        source_snapshot_json TEXT NOT NULL CHECK (json_valid(source_snapshot_json)),
        source_url TEXT,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        work_mode TEXT,
        language TEXT,
        seniority TEXT,
        role_family TEXT,
        domain TEXT,
        skills_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(skills_json)),
        current_stage_id TEXT,
        current_cv_version_id TEXT,
        current_cv_evaluation_id TEXT,
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0),
        UNIQUE (run_id, source_index)
    );
    CREATE INDEX IF NOT EXISTS ix_run_jobs_title ON run_jobs(run_id, title COLLATE NOCASE, run_job_id);
    CREATE INDEX IF NOT EXISTS ix_run_jobs_fingerprint ON run_jobs(source_fingerprint);

    CREATE TABLE IF NOT EXISTS run_job_stage_results (
        run_job_id TEXT NOT NULL REFERENCES run_jobs(run_job_id) ON DELETE CASCADE,
        stage_id TEXT NOT NULL CHECK (stage_id IN ('enrichment', 'screening', 'shortlisting', 'ranking', 'cv-analysis', 'cv-generation')),
        status TEXT NOT NULL CHECK (status IN ('pending', 'passed', 'rejected', 'blocked', 'skipped', 'failed', 'review_required', 'generated')),
        outcome_code TEXT,
        reason_code TEXT,
        evidence_json TEXT CHECK (evidence_json IS NULL OR json_valid(evidence_json)),
        started_at TEXT,
        finished_at TEXT,
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0),
        PRIMARY KEY (run_job_id, stage_id)
    );

    CREATE TABLE IF NOT EXISTS cv_versions (
        version_id TEXT PRIMARY KEY,
        run_job_id TEXT REFERENCES run_jobs(run_job_id) ON DELETE CASCADE,
        parent_cv_version_id TEXT REFERENCES cv_versions(version_id),
        ordinal INTEGER,
        generation_status TEXT NOT NULL DEFAULT 'pending' CHECK (generation_status IN ('pending', 'running', 'generated', 'review_required', 'validation_failed', 'generation_failed', 'persistence_failed', 'cancelled')),
        created_at TEXT,
        started_at TEXT,
        finished_at TEXT,
        duration_ms INTEGER CHECK (duration_ms IS NULL OR duration_ms >= 0),
        generator_id TEXT,
        model_id TEXT,
        prompt_id TEXT,
        schema_id TEXT,
        source_profile_revision TEXT,
        source_settings_revision TEXT,
        input_snapshot_json TEXT CHECK (input_snapshot_json IS NULL OR json_valid(input_snapshot_json)),
        input_checksum TEXT,
        filename TEXT,
        media_type TEXT,
        content_length INTEGER CHECK (content_length IS NULL OR content_length >= 0),
        content_checksum TEXT,
        content_blob BLOB,
        storage_path TEXT,
        error_code TEXT,
        error_message TEXT,
        action_id TEXT,
        idempotency_key TEXT,
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
        cv_generation_reuse_status TEXT,
        UNIQUE (run_job_id, ordinal),
        CHECK (generation_status NOT IN ('generated', 'review_required') OR (content_blob IS NOT NULL AND content_checksum IS NOT NULL AND content_length IS NOT NULL))
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_cv_versions_idempotency
        ON cv_versions(run_job_id, idempotency_key) WHERE idempotency_key IS NOT NULL;

    CREATE TABLE IF NOT EXISTS cv_evaluations (
        cv_evaluation_id TEXT PRIMARY KEY,
        cv_version_id TEXT NOT NULL REFERENCES cv_versions(version_id) ON DELETE CASCADE,
        status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'succeeded', 'failed')),
        fit_classification TEXT CHECK (fit_classification IS NULL OR fit_classification IN ('strong', 'stretch', 'skip')),
        score REAL,
        reason TEXT,
        evidence_json TEXT CHECK (evidence_json IS NULL OR json_valid(evidence_json)),
        evaluator_id TEXT,
        model_id TEXT,
        prompt_id TEXT,
        schema_id TEXT,
        started_at TEXT,
        finished_at TEXT,
        error_code TEXT,
        error_message TEXT,
        retry_count INTEGER NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
        next_retry_at TEXT,
        is_current INTEGER NOT NULL DEFAULT 1 CHECK (is_current IN (0, 1)),
        CHECK (status != 'succeeded' OR fit_classification IS NOT NULL)
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_cv_evaluations_current
        ON cv_evaluations(cv_version_id) WHERE is_current = 1;

    CREATE TABLE IF NOT EXISTS cv_review_events (
        review_event_id TEXT PRIMARY KEY,
        cv_version_id TEXT NOT NULL REFERENCES cv_versions(version_id) ON DELETE CASCADE,
        cv_evaluation_id TEXT REFERENCES cv_evaluations(cv_evaluation_id) ON DELETE SET NULL,
        from_state TEXT CHECK (from_state IS NULL OR from_state IN ('none', 'stretch', 'manual_required', 'approved', 'rejected')),
        to_state TEXT NOT NULL CHECK (to_state IN ('none', 'stretch', 'manual_required', 'approved', 'rejected')),
        actor TEXT NOT NULL,
        note TEXT,
        action_id TEXT,
        idempotency_key TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS bookmarks (
        bookmark_id TEXT PRIMARY KEY,
        run_id TEXT REFERENCES pipeline_runs(run_id) ON DELETE SET NULL,
        run_job_id TEXT REFERENCES run_jobs(run_job_id) ON DELETE SET NULL,
        source_fingerprint TEXT NOT NULL,
        display_snapshot_json TEXT NOT NULL CHECK (json_valid(display_snapshot_json)),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_bookmarks_run_job
        ON bookmarks(run_job_id) WHERE run_job_id IS NOT NULL;

    CREATE TABLE IF NOT EXISTS run_job_interest (
        run_job_id TEXT PRIMARY KEY REFERENCES run_jobs(run_job_id) ON DELETE CASCADE,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        rating_contract_revision TEXT NOT NULL,
        action_id TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0)
    );

    CREATE TABLE IF NOT EXISTS idempotent_actions (
        action_id TEXT PRIMARY KEY,
        action_scope TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        request_fingerprint TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
        response_json TEXT CHECK (response_json IS NULL OR json_valid(response_json)),
        error_json TEXT CHECK (error_json IS NULL OR json_valid(error_json)),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (action_scope, idempotency_key)
    );
    """
    try:
        conn.execute("BEGIN IMMEDIATE")
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)
        if candidate_profiles is not None:
            _persist_initial_profile_state(conn, candidate_profiles, startup_warning)
        conn.execute(f"PRAGMA user_version = {CONTROL_PLANE_SCHEMA_VERSION}")
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise


def initialize_control_plane_database(database_path: Path, candidate_profile_path: Path) -> None:
    warning: dict[str, str] | None = None
    try:
        from fitcv.candidate import load_profile_text

        base_profile = load_profile_text(candidate_profile_path.read_text(encoding="utf-8"))
        candidate_profiles = build_candidate_profile_seeds(base_profile)
    except (OSError, UnicodeError, ValueError) as exc:
        candidate_profiles = []
        warning = {
            "code": "candidate_profile_setup_required",
            "message": f"Candidate profile could not be loaded: {exc}",
            "action": "Update candidate_profile.yaml, then reset the database.",
        }
    with _sqlite_connection(database_path) as conn:
        _ensure_control_plane_schema(
            conn,
            candidate_profiles=candidate_profiles,
            startup_warning=warning,
        )


def ensure_control_plane_database(database_path: Path, candidate_profile_path: Path) -> None:
    if not database_path.exists():
        initialize_control_plane_database(database_path, candidate_profile_path)
        return
    with _sqlite_connection(database_path) as conn:
        _ensure_control_plane_schema(conn)


def list_candidate_profiles(
    *, database_path: Path | None = None, active_only: bool = True
) -> list[dict[str, Any]]:
    path = database_path or Path(_local_sqlite_path())
    where = "WHERE is_active = 1" if active_only else ""
    with _sqlite_connection(path) as conn:
        rows = conn.execute(
            f"""
            SELECT candidate_profile_id, name, description, is_active, is_default,
                   updated_at, revision, sort_order, checksum, seed_manifest_revision
            FROM candidate_profiles
            {where}
            ORDER BY sort_order, name COLLATE NOCASE, candidate_profile_id
            """
        ).fetchall()
    keys = (
        "candidate_profile_id", "name", "description", "is_active", "is_default",
        "updated_at", "revision", "sort_order", "checksum", "seed_manifest_revision",
    )
    return [
        {**dict(zip(keys, row)), "is_active": bool(row[3]), "is_default": bool(row[4])}
        for row in rows
    ]


def get_candidate_profile(
    candidate_profile_id: str, *, database_path: Path | None = None
) -> dict[str, Any] | None:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        row = conn.execute(
            "SELECT candidate_profile_id, name, profile_json, revision, checksum, is_active FROM candidate_profiles WHERE candidate_profile_id = ?",
            (candidate_profile_id,),
        ).fetchone()
    if row is None:
        return None
    return {
        "candidate_profile_id": row[0],
        "name": row[1],
        "profile": json.loads(row[2]),
        "revision": row[3],
        "checksum": row[4],
        "is_active": bool(row[5]),
    }


def list_startup_warnings(*, database_path: Path | None = None) -> list[dict[str, str]]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        rows = conn.execute(
            "SELECT code, message, action, created_at FROM startup_warnings ORDER BY code"
        ).fetchall()
    return [
        {"code": row[0], "message": row[1], "action": row[2], "created_at": row[3]}
        for row in rows
    ]


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
    cursor: str | None = None,
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
    cursor_key: tuple[datetime.datetime, str] | None = None
    if cursor:
        try:
            padding = "=" * (-len(cursor) % 4)
            decoded = json.loads(base64.urlsafe_b64decode(cursor + padding).decode("utf-8"))
            cursor_key = (
                datetime.datetime.fromisoformat(str(decoded["recorded_at"])),
                str(decoded["event_id"]),
            )
        except (KeyError, TypeError, ValueError, UnicodeError) as exc:
            raise ValueError("invalid_cursor") from exc
    remaining = [
        event for event in ordered
        if cursor_key is None or (event.recorded_at, event.event_id) > cursor_key
    ]
    page_events = remaining[:normalized_limit]
    next_cursor = None
    if len(remaining) > normalized_limit and page_events:
        last = page_events[-1]
        payload = json.dumps(
            {"recorded_at": last.recorded_at.isoformat(), "event_id": last.event_id},
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        next_cursor = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return {
        "events": page_events,
        "integrity_conflicts": sorted(
            [*sqlite_conflicts, *journal_conflicts],
            key=lambda item: (item.recorded_at, item.conflict_id),
        ),
        "deliveries": deliveries,
        "total_count": len(ordered),
        "next_cursor": next_cursor,
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


def _run_name(run: PipelineRun) -> str:
    return (
        str(getattr(run, "run_name", "") or "").strip()
        or Path(str(run.jobs_path or "")).stem
        or run.run_id
    )[:120]


def _settings_revision(run: PipelineRun) -> str:
    payload = str(run.effective_settings_json or run.settings_used_json or "{}")
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_normalized_run(conn: sqlite3.Connection, run: PipelineRun, *, insert: bool) -> None:
    values = (
        _run_name(run), run.status.value, run.error_stage, run.triggered_by, run.trigger_source,
        run.run_mode, run.created_at.isoformat(), run.started_at.isoformat() if run.started_at else None,
        run.finished_at.isoformat() if run.finished_at else None,
        run.archived_at.isoformat() if run.archived_at else None, run.archived_by, run.queue_job_id,
        run.orchestration_backend, run.orchestration_run_id, int(run.total_jobs or 0),
        int(run.passed_filter or 0), max(0, int(run.total_jobs or 0) - int(run.passed_filter or 0)),
        int(run.cvs_generated or 0), int(run.progress_completed or 0),
        int(run.progress_total or run.total_jobs or 0), _settings_revision(run), run.warning_json,
        run.error_stage, run.error_message, int(bool(run.partial_completion)),
        _pipeline_run_to_json(run), run.run_id,
    )
    if insert:
        conn.execute(
            """
            INSERT INTO pipeline_runs (
                run_name, backend_status, status_detail, triggered_by, trigger_source, trigger_mode,
                created_at, started_at, finished_at, archived_at, archived_by, queue_job_id,
                orchestration_backend, orchestration_run_id, total_jobs, passed_jobs, rejected_jobs,
                cvs_generated, progress_completed, progress_total, settings_revision, warning_json,
                error_code, error_message, partial_completion, compatibility_json, run_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        return
    conn.execute(
        """
        UPDATE pipeline_runs SET
            run_name=?, backend_status=?, status_detail=?, triggered_by=?, trigger_source=?, trigger_mode=?,
            created_at=?, started_at=?, finished_at=?, archived_at=?, archived_by=?, queue_job_id=?,
            orchestration_backend=?, orchestration_run_id=?, total_jobs=?, passed_jobs=?, rejected_jobs=?,
            cvs_generated=?, progress_completed=?, progress_total=?, settings_revision=?, warning_json=?,
            error_code=?, error_message=?, partial_completion=?, compatibility_json=?, row_revision=row_revision+1
        WHERE run_id=?
        """,
        values,
    )


def _normalized_run_from_row(row: sqlite3.Row) -> PipelineRun | None:
    run = _pipeline_run_from_json(str(row["compatibility_json"]))
    if run is None:
        return None
    run.status = RunStatus(str(row["backend_status"]))
    run.run_name = str(row["run_name"])
    run.started_at = _parse_dt(row["started_at"])
    run.finished_at = _parse_dt(row["finished_at"])
    run.archived_at = _parse_dt(row["archived_at"])
    run.archived_by = row["archived_by"]
    run.queue_job_id = row["queue_job_id"]
    run.orchestration_backend = row["orchestration_backend"]
    run.orchestration_run_id = row["orchestration_run_id"]
    run.total_jobs = int(row["total_jobs"])
    run.passed_filter = int(row["passed_jobs"])
    run.cvs_generated = int(row["cvs_generated"])
    run.error_stage = row["error_code"]
    run.error_message = row["error_message"]
    run.status_detail = row["status_detail"]
    run.warning_json = row["warning_json"]
    run.partial_completion = bool(row["partial_completion"])
    run.progress_completed = int(row["progress_completed"])
    run.progress_total = int(row["progress_total"])
    return run


def insert_run(run: PipelineRun, *_compat_args: Any, **_compat_kwargs: Any) -> None:
    if str(run.jobs_input_json or "").strip():
        try:
            jobs = json.loads(str(run.jobs_input_json))
        except (TypeError, ValueError) as exc:
            raise ValueError("jobs_input_invalid") from exc
        if not isinstance(jobs, list):
            raise ValueError("jobs_input_invalid")
        if not jobs:
            raise ValueError("jobs_input_empty")
        manifest = _json_dict(run.jobs_input_manifest_json)
        source_filenames = list(manifest.get("source_filenames") or [])
        profile = _json_dict(run.candidate_profile_json)
        create_run_bundle(
            run,
            input_resource={
                "original_filename": str(source_filenames[0] if source_filenames else Path(run.jobs_path).name),
                "media_type": str(manifest.get("media_type") or "application/json"),
                "byte_length": manifest.get("byte_length"),
                "sha256": manifest.get("sha256"),
                "jobs_snapshot_json": str(run.jobs_input_json),
                "jobs_manifest_json": str(run.jobs_input_manifest_json or "{}"),
                "candidate_profile_id": (
                    run.candidate_profile_source
                    if str(run.candidate_profile_source or "").startswith("candidate-")
                    else None
                ),
                "candidate_profile_revision": profile.get("revision"),
                "candidate_profile_name": str(profile.get("name") or profile.get("headline") or "Candidate Profile"),
                "candidate_profile_json": str(run.candidate_profile_json or "{}"),
                "settings_revision": _settings_revision(run),
                "settings_snapshot_json": str(run.effective_settings_json or "{}"),
            },
            jobs=[dict(job) for job in jobs if isinstance(job, dict)],
        )
        return
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        _ensure_control_plane_schema(conn)
        _write_normalized_run(conn, dataclasses.replace(run), insert=True)
        conn.commit()


def get_run(run_id: str, *_compat_args: Any, **_compat_kwargs: Any) -> Optional[PipelineRun]:
    path = Path(_local_sqlite_path())
    if not path.exists():
        return None
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        row = conn.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)).fetchone()
    return _normalized_run_from_row(row) if row is not None else None


def list_runs(
    *_compat_args: Any,
    limit: int = 50,
    include_archived: bool = False,
    archived_only: bool = False,
    **_compat_kwargs: Any,
) -> list[PipelineRun]:
    path = Path(_local_sqlite_path())
    if not path.exists():
        return []
    where = "WHERE archived_at IS NOT NULL" if archived_only else "" if include_archived else "WHERE archived_at IS NULL"
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        rows = conn.execute(
            f"SELECT * FROM pipeline_runs {where} ORDER BY created_at DESC, run_id DESC LIMIT ?",
            (max(1, int(limit)),),
        ).fetchall()
    return [run for row in rows if (run := _normalized_run_from_row(row)) is not None]


def _mutate_normalized_run(run_id: str, mutate: Callable[[PipelineRun], PipelineRun]) -> bool:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        row = conn.execute("SELECT * FROM pipeline_runs WHERE run_id = ?", (run_id,)).fetchone()
        if row is None:
            return False
        run = _normalized_run_from_row(row)
        if run is None:
            return False
        _write_normalized_run(conn, mutate(run), insert=False)
        conn.commit()
        return True


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
    def mutate(run: PipelineRun) -> PipelineRun:
        updated = dataclasses.replace(run, status=status)
        if started_at is not None:
            updated.started_at = started_at
        if finished_at is not None:
            updated.finished_at = finished_at
        if error_message is not None:
            updated.error_message = error_message
        if error_stage is not None:
            updated.error_stage = error_stage
        for key in ("total_jobs", "passed_filter", "ranked", "cvs_generated"):
            if summary and summary.get(key) is not None:
                setattr(updated, key, int(summary[key]))
        return updated

    if _mutate_normalized_run(run_id, mutate):
        return _persistence_result("persisted")
    return _persistence_result("degraded", "run_not_found")


def update_run_checkpoint(run_id: str, *_compat_args: Any, **kwargs: Any) -> PersistenceResult:
    fields = {
        key: kwargs.get(key)
        for key in (
            "checkpoint_status", "next_stage", "last_completed_stage",
            "completed_stages", "checkpoint_payload_json",
        )
    }
    if _mutate_normalized_run(run_id, lambda run: dataclasses.replace(run, **fields)):
        return _persistence_result("persisted")
    return _persistence_result("degraded", "run_not_found")


def update_run_progress(run_id: str, *_compat_args: Any, **kwargs: Any) -> PersistenceResult:
    return update_run_checkpoint(
        run_id,
        last_completed_stage=kwargs.get("last_completed_stage"),
        completed_stages=kwargs.get("completed_stages"),
        checkpoint_status=None,
        next_stage=None,
        checkpoint_payload_json=None,
    )


def create_run_bundle(
    run: PipelineRun,
    *,
    input_resource: dict[str, Any],
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    from fitcv_cp.run_lifecycle import PROTOTYPE_STAGES

    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        _ensure_control_plane_schema(conn)
        try:
            conn.execute("BEGIN IMMEDIATE")
            run.total_jobs = len(jobs)
            _write_normalized_run(conn, run, insert=True)
            jobs_json = str(input_resource.get("jobs_snapshot_json") or json.dumps(jobs))
            byte_length = input_resource.get("byte_length")
            if byte_length is None:
                byte_length = len(jobs_json.encode("utf-8"))
            sha256 = str(input_resource.get("sha256") or "").strip()
            if not sha256:
                sha256 = hashlib.sha256(jobs_json.encode("utf-8")).hexdigest()
            conn.execute(
                """INSERT INTO run_inputs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    run.run_id,
                    str(input_resource.get("original_filename") or Path(run.jobs_path).name),
                    str(input_resource.get("media_type") or "application/json"),
                    int(byte_length),
                    sha256,
                    len(jobs),
                    jobs_json,
                    str(input_resource.get("jobs_manifest_json") or "{}"),
                    input_resource.get("candidate_profile_id"),
                    input_resource.get("candidate_profile_revision"),
                    str(input_resource.get("candidate_profile_name") or ""),
                    str(input_resource.get("candidate_profile_json") or "{}"),
                    str(input_resource.get("settings_revision") or _settings_revision(run)),
                    str(input_resource.get("settings_snapshot_json") or "{}"),
                    run.created_at.isoformat(),
                ),
            )
            conn.executemany(
                "INSERT INTO run_stage_executions (run_id, stage_id, ordinal, status) VALUES (?, ?, ?, 'pending')",
                [(run.run_id, stage.stage_id, stage.ordinal) for stage in PROTOTYPE_STAGES],
            )
            run_job_ids: list[str] = []
            for index, job in enumerate(jobs):
                source_json = json.dumps(job, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                run_job_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"{run.run_id}:{index}:{source_json}"))
                run_job_ids.append(run_job_id)
                conn.execute(
                    """INSERT INTO run_jobs (
                        run_job_id, run_id, source_index, source_fingerprint, source_snapshot_json,
                        source_url, title, company, location, work_mode, language, seniority,
                        role_family, domain, skills_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        run_job_id,
                        run.run_id,
                        index,
                        hashlib.sha256(source_json.encode("utf-8")).hexdigest(),
                        source_json,
                        job.get("job_url") or job.get("url"),
                        str(job.get("title") or "Untitled"),
                        job.get("company"),
                        job.get("location"),
                        job.get("work_mode"),
                        job.get("language"),
                        job.get("seniority"),
                        job.get("role_family"),
                        job.get("domain"),
                        json.dumps(job.get("skills") or []),
                    ),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"run_id": run.run_id, "run_job_ids": run_job_ids}


def list_run_stages(run_id: str) -> list[dict[str, Any]]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM run_stage_executions WHERE run_id=? ORDER BY ordinal",
            (run_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def query_run_jobs(
    run_id: str,
    *,
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    result_bucket: str | None = None,
) -> dict[str, Any]:
    if page_size not in {10, 20, 50}:
        raise ValueError("page_size must be 10, 20, or 50")
    clauses = ["j.run_id = ?"]
    params: list[Any] = [run_id]
    if search.strip():
        clauses.append("(j.title LIKE ? COLLATE NOCASE OR COALESCE(j.company,'') LIKE ? COLLATE NOCASE)")
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])
    predicate = " AND ".join(clauses)
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(f"SELECT COUNT(*) FROM run_jobs j WHERE {predicate}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT j.* FROM run_jobs j WHERE {predicate} ORDER BY j.title COLLATE NOCASE, j.run_job_id LIMIT ? OFFSET ?",
            (*params, page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["source_snapshot"] = json.loads(item.pop("source_snapshot_json"))
        item["skills"] = json.loads(item.pop("skills_json"))
    return {"items": items, "total": int(total), "page": max(1, page), "page_size": page_size}


def query_runs(
    *,
    view: str = "active",
    search: str = "",
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    if page_size not in {10, 20, 50}:
        raise ValueError("page_size must be 10, 20, or 50")
    clauses: list[str] = []
    params: list[Any] = []
    if view == "active":
        clauses.append("archived_at IS NULL")
    elif view == "archived":
        clauses.append("archived_at IS NOT NULL")
    elif view != "all":
        raise ValueError("view must be active, archived, or all")
    if search.strip():
        clauses.append("(run_name LIKE ? COLLATE NOCASE OR run_id LIKE ? COLLATE NOCASE)")
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        total = conn.execute(f"SELECT COUNT(*) FROM pipeline_runs {where}", params).fetchone()[0]
        counts = conn.execute(
            "SELECT SUM(archived_at IS NULL), SUM(archived_at IS NOT NULL) FROM pipeline_runs"
        ).fetchone()
        rows = conn.execute(
            f"SELECT * FROM pipeline_runs {where} ORDER BY created_at DESC, run_id DESC LIMIT ? OFFSET ?",
            (*params, page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
    return {
        "items": [_normalized_run_from_row(row) for row in rows],
        "total": int(total),
        "active_count": int(counts[0] or 0),
        "archived_count": int(counts[1] or 0),
        "page": max(1, page),
        "page_size": page_size,
    }


def reserve_idempotent_action(scope: str, key: str, fingerprint: str) -> dict[str, Any]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM idempotent_actions WHERE action_scope=? AND idempotency_key=?",
            (scope, key),
        ).fetchone()
        if row is not None:
            if row["request_fingerprint"] != fingerprint:
                raise ValueError("idempotency_conflict")
            return {
                "action_id": row["action_id"],
                "status": row["status"],
                "replayed": True,
                "response": json.loads(row["response_json"]) if row["response_json"] else None,
            }
        action_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            "INSERT INTO idempotent_actions VALUES (?, ?, ?, ?, 'queued', NULL, NULL, ?, ?)",
            (action_id, scope, key, fingerprint, now, now),
        )
        conn.commit()
    return {"action_id": action_id, "status": "queued", "replayed": False, "response": None}


def complete_idempotent_action(action_id: str, response: dict[str, Any]) -> None:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.execute(
            "UPDATE idempotent_actions SET status='succeeded', response_json=?, updated_at=? WHERE action_id=?",
            (json.dumps(response, sort_keys=True), datetime.datetime.now(datetime.timezone.utc).isoformat(), action_id),
        )
        conn.commit()


def set_bookmark(run_job_id: str) -> dict[str, Any]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        job = conn.execute("SELECT * FROM run_jobs WHERE run_job_id=?", (run_job_id,)).fetchone()
        if job is None:
            raise ValueError("job_not_found")
        snapshot = {key: job[key] for key in ("title", "company", "location", "source_url")}
        bookmark_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            "INSERT OR REPLACE INTO bookmarks VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                bookmark_id,
                job["run_id"],
                run_job_id,
                job["source_fingerprint"],
                json.dumps(snapshot),
                now,
                now,
            ),
        )
        conn.commit()
    return {"bookmark_id": bookmark_id, "run_job_id": run_job_id, "display_snapshot": snapshot}


def clear_bookmark(run_job_id: str) -> dict[str, Any]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        cursor = conn.execute("DELETE FROM bookmarks WHERE run_job_id=?", (run_job_id,))
        conn.commit()
    return {"cleared": bool(cursor.rowcount)}


def list_bookmarks() -> list[dict[str, Any]]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM bookmarks ORDER BY created_at DESC, bookmark_id").fetchall()
    return [
        {**dict(row), "display_snapshot": json.loads(row["display_snapshot_json"])}
        for row in rows
    ]


def set_run_job_interest(
    run_job_id: str,
    rating: int,
    *,
    rating_contract_revision: str,
    action_id: str,
) -> dict[str, Any]:
    if rating not in range(1, 6):
        raise ValueError("rating must be between 1 and 5")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.execute(
            """INSERT INTO run_job_interest VALUES (?, ?, ?, ?, ?, 1)
            ON CONFLICT(run_job_id) DO UPDATE SET rating=excluded.rating,
            rating_contract_revision=excluded.rating_contract_revision,
            action_id=excluded.action_id, updated_at=excluded.updated_at,
            row_revision=run_job_interest.row_revision+1""",
            (run_job_id, rating, rating_contract_revision, action_id, now),
        )
        conn.commit()
    return {
        "run_job_id": run_job_id,
        "rating": rating,
        "rating_contract_revision": rating_contract_revision,
    }


def archive_run(run_id: str, archived_by: str, *_compat_args: Any, **_compat_kwargs: Any) -> None:
    _mutate_normalized_run(
        run_id,
        lambda run: dataclasses.replace(
            run,
            archived_at=datetime.datetime.now(datetime.timezone.utc),
            archived_by=archived_by,
        ),
    )


def unarchive_run(run_id: str, *_compat_args: Any, **_compat_kwargs: Any) -> None:
    _mutate_normalized_run(
        run_id,
        lambda run: dataclasses.replace(run, archived_at=None, archived_by=None),
    )


def request_run_cancel(
    run_id: str,
    requested_by: str,
    new_status: str,
    *_compat_args: Any,
    **_compat_kwargs: Any,
) -> bool:
    now = datetime.datetime.now(datetime.timezone.utc)
    return _mutate_normalized_run(
        run_id,
        lambda run: dataclasses.replace(
            run,
            status=RunStatus(new_status),
            cancel_requested_at=now,
            cancel_requested_by=requested_by,
        ),
    )


def delete_archived_runs(
    older_than_days: int | str,
    *_compat_args: Any,
    run_ids: list[str] | None = None,
    **_compat_kwargs: Any,
) -> dict[str, Any]:
    cutoff = None
    if older_than_days != "all":
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=int(older_than_days))
    requested = [str(value) for value in (run_ids or [])]
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        rows = conn.execute(
            "SELECT run_id, archived_at FROM pipeline_runs WHERE archived_at IS NOT NULL"
        ).fetchall()
        eligible = [
            row["run_id"]
            for row in rows
            if (not requested or row["run_id"] in requested)
            and (cutoff is None or datetime.datetime.fromisoformat(row["archived_at"]) <= cutoff)
        ]
        if requested:
            found = {row["run_id"] for row in rows}
            not_found = [value for value in requested if value not in found]
            blocked = [value for value in requested if value in found and value not in eligible]
            if not_found or blocked:
                return {
                    "requested_run_ids": requested,
                    "deleted_count": 0,
                    "deleted_run_ids": [],
                    "not_found_run_ids": not_found,
                    "blocked_run_ids": blocked,
                }
        conn.executemany("DELETE FROM pipeline_runs WHERE run_id=?", [(value,) for value in eligible])
        conn.commit()
    return {
        "requested_run_ids": requested,
        "deleted_count": len(eligible),
        "deleted_run_ids": eligible,
        "not_found_run_ids": [],
        "blocked_run_ids": [],
    }


def update_run_queue_job_id(
    run_id: str,
    queue_job_id: str,
    *_args: Any,
    orchestration_backend: str | None = None,
    orchestration_run_id: str | None = None,
    **_kwargs: Any,
) -> PersistenceResult:
    if _mutate_normalized_run(
        run_id,
        lambda run: dataclasses.replace(
            run,
            queue_job_id=queue_job_id,
            orchestration_backend=orchestration_backend,
            orchestration_run_id=orchestration_run_id,
        ),
    ):
        return _persistence_result("persisted")
    return _persistence_result("degraded", "run_not_found")


def update_run_orchestration_binding(
    run_id: str,
    *_args: Any,
    queue_job_id: str | None,
    orchestration_backend: str | None,
    orchestration_run_id: str | None,
    **_kwargs: Any,
) -> PersistenceResult:
    if _mutate_normalized_run(
        run_id,
        lambda run: dataclasses.replace(
            run,
            queue_job_id=queue_job_id,
            orchestration_backend=orchestration_backend,
            orchestration_run_id=orchestration_run_id,
        ),
    ):
        return _persistence_result("persisted")
    return _persistence_result("degraded", "run_not_found")


def _update_run_compatibility_field(run_id: str, field_name: str, value: Any) -> PersistenceResult:
    if _mutate_normalized_run(
        run_id,
        lambda run: dataclasses.replace(run, **{field_name: value}),
    ):
        return _persistence_result("persisted")
    return _persistence_result("degraded", "run_not_found")


def update_run_results_export(run_id: str, results_export_json: str, *_args: Any, **_kwargs: Any) -> PersistenceResult:
    return _update_run_compatibility_field(run_id, "results_export_json", results_export_json)


def update_run_stage_transition_artifacts(
    run_id: str, stage_transition_artifacts_json: str, *_args: Any, **_kwargs: Any
) -> PersistenceResult:
    return _update_run_compatibility_field(
        run_id, "stage_transition_artifacts_json", stage_transition_artifacts_json
    )


def update_run_effective_settings(
    run_id: str, effective_settings_json: str, *_args: Any, **_kwargs: Any
) -> PersistenceResult:
    return _update_run_compatibility_field(run_id, "effective_settings_json", effective_settings_json)


def update_run_synonym_proposals(
    run_id: str, synonym_proposals_json: str, *_args: Any, **_kwargs: Any
) -> PersistenceResult:
    return _update_run_compatibility_field(run_id, "synonym_proposals_json", synonym_proposals_json)


def update_run_cv_generation_debug(
    run_id: str, cv_generation_debug_json: str, *_args: Any, **_kwargs: Any
) -> PersistenceResult:
    return _update_run_compatibility_field(run_id, "cv_generation_debug_json", cv_generation_debug_json)


def get_pipeline_runs_schema_status(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
    path = Path(_local_sqlite_path())
    if not path.exists():
        return {"backend": "sqlite", "schema_version": 0, "compatible": True}
    with _sqlite_connection(path) as conn:
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    return {
        "backend": "sqlite",
        "schema_version": version,
        "expected_schema_version": CONTROL_PLANE_SCHEMA_VERSION,
        "compatible": version == CONTROL_PLANE_SCHEMA_VERSION,
        "warning": "sqlite_mode_no_remote_schema_check",
    }


def list_run_structured_jobs(
    run_id: str, *_args: Any, **_kwargs: Any
) -> list[dict[str, Any]]:
    return [item["source_snapshot"] | {"run_job_id": item["run_job_id"]} for item in query_run_jobs(
        run_id, page=1, page_size=50
    )["items"]]


def list_filter_results_for_run(
    run_id: str, *_args: Any, **_kwargs: Any
) -> list[dict[str, Any]]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT j.run_job_id, j.source_url AS job_url, r.status, r.reason_code,
                      r.outcome_code, r.evidence_json, r.finished_at
               FROM run_jobs j
               JOIN run_job_stage_results r ON r.run_job_id = j.run_job_id
               WHERE j.run_id = ? AND r.stage_id = 'screening'
               ORDER BY j.title COLLATE NOCASE, j.run_job_id""",
            (run_id,),
        ).fetchall()
    results: list[dict[str, Any]] = []
    for row in rows:
        evidence = json.loads(row["evidence_json"] or "{}")
        results.append(
            {
                "run_job_id": row["run_job_id"],
                "job_url": row["job_url"],
                "source_job_url": evidence.get("source_job_url") or row["job_url"],
                "raw_job_fingerprint": evidence.get("raw_job_fingerprint"),
                "passed": row["status"] == "passed",
                "reasons": evidence.get("reasons", []),
                "marks": evidence.get("marks", []),
                "fit_factor_results": evidence.get("fit_factor_results", {}),
                "eligibility_policy_fingerprint": evidence.get("eligibility_policy_fingerprint"),
                "eligibility_decision": evidence.get("eligibility_decision"),
                "eligibility_reason_codes": evidence.get("eligibility_reason_codes", []),
                "filtered_at": row["finished_at"],
            }
        )
    return results


def replace_filter_results(run_id: str, rows: list[dict[str, Any]]) -> None:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        jobs = conn.execute(
            "SELECT run_job_id, source_url FROM run_jobs WHERE run_id=?",
            (run_id,),
        ).fetchall()
        job_by_url = {str(row["source_url"] or ""): row["run_job_id"] for row in jobs}
        conn.execute(
            "DELETE FROM run_job_stage_results WHERE stage_id='screening' AND run_job_id IN (SELECT run_job_id FROM run_jobs WHERE run_id=?)",
            (run_id,),
        )
        for row in rows:
            run_job_id = job_by_url.get(str(row.get("job_url") or row.get("source_job_url") or ""))
            if run_job_id is None:
                raise ValueError("job_not_found")
            evidence = {
                "source_job_url": row.get("source_job_url") or row.get("job_url"),
                "raw_job_fingerprint": row.get("raw_job_fingerprint"),
                "reasons": row.get("reasons") or [],
                "marks": row.get("marks") or [],
                "fit_factor_results": row.get("fit_factor_results") or {},
                "eligibility_policy_fingerprint": row.get("eligibility_policy_fingerprint"),
                "eligibility_decision": row.get("eligibility_decision"),
                "eligibility_reason_codes": row.get("eligibility_reason_codes") or [],
            }
            conn.execute(
                """INSERT INTO run_job_stage_results (
                    run_job_id, stage_id, status, reason_code, evidence_json, finished_at
                ) VALUES (?, 'screening', ?, ?, ?, ?)""",
                (
                    run_job_id,
                    "passed" if row.get("passed") else "rejected",
                    (row.get("reasons") or [None])[0],
                    json.dumps(evidence, sort_keys=True),
                    str(row.get("filtered_at") or datetime.datetime.now(datetime.timezone.utc).isoformat()),
                ),
            )
        conn.commit()


def _json_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    try:
        decoded = json.loads(str(value or "{}"))
    except (TypeError, ValueError):
        return {}
    return dict(decoded) if isinstance(decoded, dict) else {}


def _run_capabilities(run: PipelineRun) -> dict[str, bool]:
    return {
        "inspect": True,
        "cancel": can_cancel_run(run),
        "archive": can_archive_run(run),
        "unarchive": can_unarchive_run(run),
        "delete": can_unarchive_run(run),
        "export": int(run.total_jobs or 0) > 0,
    }


def _usable_cv_job_ids(conn: sqlite3.Connection, run_id: str) -> set[str]:
    return {
        str(row[0])
        for row in conn.execute(
            """SELECT DISTINCT v.run_job_id
               FROM cv_versions v
               JOIN run_jobs j ON j.run_job_id = v.run_job_id
               WHERE j.run_id = ?
                 AND v.generation_status IN ('generated', 'review_required')
                 AND v.content_blob IS NOT NULL
                 AND v.content_length = length(v.content_blob)
                 AND v.content_checksum IS NOT NULL""",
            (run_id,),
        ).fetchall()
        if row[0]
    }


def _job_result_bucket(
    status: str,
    *,
    run_job_id: str,
    evidence: dict[str, Any],
    usable_cv_job_ids: set[str],
) -> ResultBucket | None:
    return result_bucket_for_job_stage(
        JobStageStatus(status),
        has_usable_output=run_job_id in usable_cv_job_ids,
        skip_is_terminal_rejection=bool(evidence.get("skip_is_terminal_rejection")),
    )


def get_run_detail(run_id: str, *_args: Any, **_kwargs: Any) -> dict[str, Any] | None:
    path = Path(_local_sqlite_path())
    if not path.exists():
        return None
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        run_row = conn.execute(
            "SELECT * FROM pipeline_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run_row is None:
            return None
        input_row = conn.execute(
            "SELECT * FROM run_inputs WHERE run_id=?", (run_id,)
        ).fetchone()
        stage_rows = conn.execute(
            "SELECT * FROM run_stage_executions WHERE run_id=? ORDER BY ordinal", (run_id,)
        ).fetchall()
        result_rows = conn.execute(
            """SELECT r.* FROM run_job_stage_results r
               JOIN run_jobs j ON j.run_job_id=r.run_job_id
               WHERE j.run_id=?""",
            (run_id,),
        ).fetchall()
        usable_cv_job_ids = _usable_cv_job_ids(conn, run_id)

    run = _normalized_run_from_row(run_row)
    if run is None:
        return None
    results_by_stage: dict[str, list[sqlite3.Row]] = {}
    for result_row in result_rows:
        results_by_stage.setdefault(str(result_row["stage_id"]), []).append(result_row)
    projected_stages: list[dict[str, Any]] = []
    recomputed_by_stage: dict[str, dict[str, int]] = {}
    stage_spec_by_id = {stage.stage_id: stage for stage in PROTOTYPE_STAGES}
    for stage_row in stage_rows:
        stage_id = str(stage_row["stage_id"])
        stage_results = results_by_stage.get(stage_id, [])
        passed = 0
        rejected = 0
        for result_row in stage_results:
            evidence = _json_dict(result_row["evidence_json"])
            bucket = _job_result_bucket(
                str(result_row["status"]),
                run_job_id=str(result_row["run_job_id"]),
                evidence=evidence,
                usable_cv_job_ids=usable_cv_job_ids,
            )
            passed += int(bucket == ResultBucket.PASSED)
            rejected += int(bucket == ResultBucket.REJECTED)
        recomputed_by_stage[stage_id] = {"passed": passed, "rejected": rejected}
        stage = dict(stage_row)
        spec = stage_spec_by_id[stage_id]
        stage.update(
            {
                "label": spec.label,
                "warnings": _json_dict(stage.pop("warning_json", None)),
                "results_available": bool(stage_results),
                "recomputed_counts": {"passed": passed, "rejected": rejected},
            }
        )
        projected_stages.append(stage)

    screening_counts = recomputed_by_stage.get("screening", {"passed": 0, "rejected": 0})
    integrity_warnings: list[dict[str, Any]] = []
    stored_counts = {
        "passed": int(run_row["passed_jobs"]),
        "rejected": int(run_row["rejected_jobs"]),
    }
    if stored_counts != screening_counts:
        integrity_warnings.append(
            {
                "code": "run_count_mismatch",
                "stored": stored_counts,
                "recomputed": screening_counts,
            }
        )
    return {
        "run_id": run.run_id,
        "run_name": str(run_row["run_name"]),
        "backend_status": run.status.value,
        "display_status": run_display_status(run.status),
        "status_detail": run_row["status_detail"],
        "created_at": run.created_at.isoformat(),
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "archived_at": run.archived_at.isoformat() if run.archived_at else None,
        "counts": {
            "total": int(run_row["total_jobs"]),
            "passed": stored_counts["passed"],
            "rejected": stored_counts["rejected"],
            "cvs_generated": int(run_row["cvs_generated"]),
        },
        "progress": {
            "completed": int(run_row["progress_completed"]),
            "total": int(run_row["progress_total"]),
        },
        "warnings": _json_dict(run_row["warning_json"]),
        "errors": {
            "code": run_row["error_code"],
            "message": run_row["error_message"],
        },
        "partial_completion": bool(run_row["partial_completion"]),
        "input": dict(input_row) if input_row is not None else None,
        "stages": projected_stages,
        "capabilities": _run_capabilities(run),
        "integrity_warnings": integrity_warnings,
        "debug_bundle": get_debug_bundle_availability(run_id),
        "links": {},
    }


def _filtered_run_job_rows(
    run_id: str,
    *,
    stage: str | None,
    result_bucket: str | None,
    search: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if stage not in {None, "all", *(item.stage_id for item in PROTOTYPE_STAGES)}:
        raise ValueError("stage must be all or a canonical stage id")
    if result_bucket not in {None, "all", "passed", "rejected"}:
        raise ValueError("result_bucket must be all, passed, or rejected")
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        jobs = conn.execute(
            "SELECT * FROM run_jobs WHERE run_id=? ORDER BY title COLLATE NOCASE, run_job_id",
            (run_id,),
        ).fetchall()
        result_rows = conn.execute(
            """SELECT r.* FROM run_job_stage_results r
               JOIN run_jobs j ON j.run_job_id=r.run_job_id
               WHERE j.run_id=?""",
            (run_id,),
        ).fetchall()
        bookmark_rows = conn.execute(
            "SELECT * FROM bookmarks WHERE run_id=? AND run_job_id IS NOT NULL", (run_id,)
        ).fetchall()
        interest_rows = conn.execute(
            """SELECT i.* FROM run_job_interest i
               JOIN run_jobs j ON j.run_job_id=i.run_job_id WHERE j.run_id=?""",
            (run_id,),
        ).fetchall()
        usable_cv_job_ids = _usable_cv_job_ids(conn, run_id)

    results_by_job: dict[str, dict[str, sqlite3.Row]] = {}
    for result_row in result_rows:
        results_by_job.setdefault(str(result_row["run_job_id"]), {})[
            str(result_row["stage_id"])
        ] = result_row
    bookmarks = {str(row["run_job_id"]): dict(row) for row in bookmark_rows}
    interests = {str(row["run_job_id"]): dict(row) for row in interest_rows}
    projected: list[dict[str, Any]] = []
    normalized_search = search.strip().casefold()
    for job_row in jobs:
        run_job_id = str(job_row["run_job_id"])
        job_results = results_by_job.get(run_job_id, {})
        selected_result: sqlite3.Row | None = None
        selected_bucket: ResultBucket | None = None
        selected_evidence: dict[str, Any] = {}
        candidate_stage_ids = (
            [stage]
            if stage not in {None, "all"}
            else [item.stage_id for item in reversed(PROTOTYPE_STAGES)]
        )
        for stage_id in candidate_stage_ids:
            result_row = job_results.get(str(stage_id))
            if result_row is None:
                continue
            evidence = _json_dict(result_row["evidence_json"])
            bucket = _job_result_bucket(
                str(result_row["status"]),
                run_job_id=run_job_id,
                evidence=evidence,
                usable_cv_job_ids=usable_cv_job_ids,
            )
            if stage is None or bucket is not None:
                selected_result = result_row
                selected_bucket = bucket
                selected_evidence = evidence
                break
        if stage is not None and selected_bucket is None:
            continue
        skills = json.loads(str(job_row["skills_json"] or "[]"))
        source_snapshot = json.loads(str(job_row["source_snapshot_json"]))
        outcome_code = selected_result["outcome_code"] if selected_result is not None else None
        reason_code = selected_result["reason_code"] if selected_result is not None else None
        searchable = " ".join(
            str(value or "")
            for value in (
                job_row["title"], job_row["company"], job_row["location"], job_row["work_mode"],
                job_row["language"], job_row["seniority"], job_row["role_family"], job_row["domain"],
                " ".join(str(item) for item in skills), outcome_code, reason_code,
            )
        ).casefold()
        if normalized_search and normalized_search not in searchable:
            continue
        bookmark = bookmarks.get(run_job_id)
        interest = interests.get(run_job_id)
        projected.append(
            {
                **{key: job_row[key] for key in job_row.keys() if key not in {"source_snapshot_json", "skills_json"}},
                "source_snapshot": source_snapshot,
                "skills": skills,
                "stage_id": selected_result["stage_id"] if selected_result is not None else None,
                "status": selected_result["status"] if selected_result is not None else "pending",
                "outcome_code": outcome_code,
                "reason_code": reason_code,
                "evidence": selected_evidence,
                "result_bucket": selected_bucket.value if selected_bucket is not None else None,
                "stage_summaries": [
                    {
                        "stage_id": item.stage_id,
                        "status": job_results[item.stage_id]["status"] if item.stage_id in job_results else "pending",
                    }
                    for item in PROTOTYPE_STAGES
                ],
                "bookmarked": bookmark is not None,
                "bookmark_id": bookmark["bookmark_id"] if bookmark else None,
                "rating": int(interest["rating"]) if interest else None,
                "rating_contract_revision": interest["rating_contract_revision"] if interest else None,
                "capabilities": {
                    "bookmark": True,
                    "rate": True,
                    "download_cv": run_job_id in usable_cv_job_ids,
                    "regenerate_cv": bool(job_row["current_cv_version_id"]),
                },
            }
        )
    totals = {
        "passed": sum(row["result_bucket"] == "passed" for row in projected),
        "rejected": sum(row["result_bucket"] == "rejected" for row in projected),
    }
    filtered = (
        projected
        if result_bucket in {None, "all"}
        else [row for row in projected if row["result_bucket"] == result_bucket]
    )
    return filtered, totals


def query_run_jobs(
    run_id: str,
    *,
    page: int = 1,
    page_size: int = 10,
    search: str = "",
    stage: str | None = None,
    result_bucket: str | None = None,
) -> dict[str, Any]:
    if page_size not in {10, 20, 50}:
        raise ValueError("page_size must be 10, 20, or 50")
    rows, totals = _filtered_run_job_rows(
        run_id, stage=stage, result_bucket=result_bucket, search=search
    )
    page_number = max(1, int(page))
    offset = (page_number - 1) * page_size
    return {
        "items": rows[offset:offset + page_size],
        "total": len(rows),
        "total_evaluated": totals["passed"] + totals["rejected"],
        "passed": totals["passed"],
        "rejected": totals["rejected"],
        "page": page_number,
        "page_size": page_size,
    }


def get_run_job(run_id: str, run_job_id: str) -> dict[str, Any] | None:
    rows, _totals = _filtered_run_job_rows(
        run_id,
        stage=None,
        result_bucket=None,
        search="",
    )
    return next(
        (row for row in rows if str(row.get("run_job_id") or "") == run_job_id),
        None,
    )


def iter_run_jobs_for_export(
    run_id: str,
    *,
    stage: str = "all",
    result_bucket: str = "all",
    search: str = "",
) -> Iterator[dict[str, Any]]:
    rows, _totals = _filtered_run_job_rows(
        run_id, stage=stage, result_bucket=result_bucket, search=search
    )
    return iter(rows)


def list_run_structured_jobs(
    run_id: str, *_args: Any, **_kwargs: Any
) -> list[dict[str, Any]]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT run_job_id, source_snapshot_json FROM run_jobs
               WHERE run_id=? ORDER BY title COLLATE NOCASE, run_job_id""",
            (run_id,),
        ).fetchall()
    return [
        json.loads(str(row["source_snapshot_json"])) | {"run_job_id": row["run_job_id"]}
        for row in rows
    ]


def clear_run_job_interest(
    run_job_id: str, *, action_id: str, **_kwargs: Any
) -> dict[str, Any]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        cursor = conn.execute(
            "DELETE FROM run_job_interest WHERE run_job_id=?", (run_job_id,)
        )
        conn.commit()
    return {"run_job_id": run_job_id, "cleared": bool(cursor.rowcount), "action_id": action_id}


def _cv_projection(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    evaluation_row = conn.execute(
        """SELECT * FROM cv_evaluations
           WHERE cv_version_id=? AND is_current=1 LIMIT 1""",
        (row["version_id"],),
    ).fetchone()
    review_row = conn.execute(
        """SELECT * FROM cv_review_events WHERE cv_version_id=?
           ORDER BY created_at DESC, review_event_id DESC LIMIT 1""",
        (row["version_id"],),
    ).fetchone()
    item = dict(row)
    item.pop("content_blob", None)
    item["cv_structured"] = _decode_json_or_none(item.get("cv_structured_json"))
    item["evaluation"] = dict(evaluation_row) if evaluation_row is not None else None
    item["review_state"] = str(review_row["to_state"]) if review_row is not None else "none"
    item["capabilities"] = {
        "download": (
            item.get("generation_status") in {"generated", "review_required"}
            and item.get("content_checksum") is not None
            and item.get("content_length") is not None
        ),
        "regenerate": bool(item.get("run_job_id")),
    }
    return item


def list_cv_versions(run_job_id: str, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM cv_versions WHERE run_job_id=?
               ORDER BY ordinal DESC, created_at DESC, version_id DESC""",
            (run_job_id,),
        ).fetchall()
        return [_cv_projection(conn, row) for row in rows]


def list_cvs_for_run(run_id: str, *_args: Any, **_kwargs: Any) -> list[dict[str, Any]]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM cv_versions WHERE run_id=?
               ORDER BY created_at DESC, ordinal DESC, version_id DESC""",
            (run_id,),
        ).fetchall()
        return [_cv_projection(conn, row) for row in rows]


def insert_cv_version_row(row: dict[str, Any], *_args: Any, **_kwargs: Any) -> list[Any]:
    version_id = str(row.get("version_id") or "").strip()
    if not version_id:
        raise ValueError("version_id is required")
    run_job_id = str(row.get("run_job_id") or "").strip() or None
    markdown = str(row.get("cv_markdown") or "")
    content_value = row.get("content_blob")
    content = (
        bytes(content_value)
        if isinstance(content_value, (bytes, bytearray, memoryview))
        else markdown.encode("utf-8") if markdown else None
    )
    generation_status = str(
        row.get("generation_status") or ("generated" if content is not None else "pending")
    )
    content_checksum = str(row.get("content_checksum") or "").strip() or (
        hashlib.sha256(content).hexdigest() if content is not None else None
    )
    content_length = row.get("content_length")
    if content is not None:
        actual_checksum = hashlib.sha256(content).hexdigest()
        if content_checksum != actual_checksum:
            raise ValueError("artifact_integrity_mismatch")
        if content_length is not None and int(content_length) != len(content):
            raise ValueError("artifact_integrity_mismatch")
        content_length = len(content)
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        run_id = str(row.get("run_id") or "").strip() or None
        job_url = str(row.get("job_url") or "").strip() or None
        ordinal = row.get("ordinal")
        if run_job_id is not None:
            job = conn.execute(
                "SELECT run_id, source_url FROM run_jobs WHERE run_job_id=?", (run_job_id,)
            ).fetchone()
            if job is None:
                raise ValueError("job_not_found")
            run_id = run_id or str(job["run_id"])
            job_url = job_url or job["source_url"]
            if ordinal is None:
                ordinal = int(
                    conn.execute(
                        "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM cv_versions WHERE run_job_id=?",
                        (run_job_id,),
                    ).fetchone()[0]
                )
            parent_id = str(row.get("parent_cv_version_id") or "").strip() or None
            if parent_id is not None:
                parent = conn.execute(
                    "SELECT run_job_id FROM cv_versions WHERE version_id=?", (parent_id,)
                ).fetchone()
                if parent is None or str(parent[0] or "") != run_job_id:
                    raise ValueError("parent_cv_version_invalid")
        conn.execute(
            """INSERT INTO cv_versions (
                version_id, run_job_id, parent_cv_version_id, ordinal, generation_status,
                created_at, started_at, finished_at, duration_ms, generator_id, model_id,
                prompt_id, schema_id, source_profile_revision, source_settings_revision,
                input_snapshot_json, input_checksum, filename, media_type, content_length,
                content_checksum, content_blob, storage_path, error_code, error_message,
                action_id, idempotency_key, run_id, job_url, fit_classification, generated_at,
                cv_generation_model, cv_prompt_version, cv_schema_version, cv_structured_json,
                cv_markdown, cv_generation_input_fingerprint, cv_generation_reuse_status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                version_id, run_job_id, row.get("parent_cv_version_id"), ordinal, generation_status,
                row.get("created_at") or row.get("generated_at") or now, row.get("started_at"),
                row.get("finished_at") or row.get("generated_at"), row.get("duration_ms"),
                row.get("generator_id"), row.get("model_id") or row.get("cv_generation_model"),
                row.get("prompt_id") or row.get("cv_prompt_version"),
                row.get("schema_id") or row.get("cv_schema_version"),
                row.get("source_profile_revision"), row.get("source_settings_revision"),
                json.dumps(row.get("input_snapshot_json"), sort_keys=True)
                if isinstance(row.get("input_snapshot_json"), dict)
                else row.get("input_snapshot_json"),
                row.get("input_checksum"), row.get("filename") or f"{version_id}.md",
                row.get("media_type") or "text/markdown; charset=utf-8", content_length,
                content_checksum, content, row.get("storage_path"), row.get("error_code"),
                row.get("error_message"), row.get("action_id"), row.get("idempotency_key"),
                run_id, job_url, row.get("fit_classification"), row.get("generated_at") or now,
                row.get("cv_generation_model"), row.get("cv_prompt_version"),
                row.get("cv_schema_version"), row.get("cv_structured_json"), markdown or None,
                row.get("cv_generation_input_fingerprint"), row.get("cv_generation_reuse_status"),
            ),
        )
        if run_job_id is not None:
            conn.execute(
                """UPDATE run_jobs SET current_cv_version_id=?, row_revision=row_revision+1
                   WHERE run_job_id=?""",
                (version_id, run_job_id),
            )
        conn.commit()
    return []


def reserve_cv_regeneration(
    run_job_id: str,
    *,
    version_id: str,
    idempotency_key: str,
    action_id: str,
    input_snapshot: dict[str, Any],
    parent_cv_version_id: str | None = None,
    source_profile_revision: str | None = None,
    source_settings_revision: str | None = None,
) -> dict[str, Any]:
    normalized_job_id = str(run_job_id or "").strip()
    normalized_version_id = str(version_id or "").strip()
    normalized_key = str(idempotency_key or "").strip()
    if not normalized_job_id or not normalized_version_id or not normalized_key:
        raise ValueError("run_job_id, version_id, and idempotency_key are required")
    snapshot_json = json.dumps(input_snapshot, sort_keys=True, separators=(",", ":"))
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        try:
            conn.execute("BEGIN IMMEDIATE")
            job = conn.execute(
                "SELECT run_id, source_url FROM run_jobs WHERE run_job_id=?", (normalized_job_id,)
            ).fetchone()
            if job is None:
                raise ValueError("job_not_found")
            existing = conn.execute(
                "SELECT * FROM cv_versions WHERE run_job_id=? AND idempotency_key=?",
                (normalized_job_id, normalized_key),
            ).fetchone()
            if existing is not None:
                conn.commit()
                return {**_cv_projection(conn, existing), "idempotent_replay": True}
            active = conn.execute(
                """SELECT version_id FROM cv_versions WHERE run_job_id=?
                   AND generation_status IN ('pending','running')
                   ORDER BY created_at DESC, version_id DESC LIMIT 1""",
                (normalized_job_id,),
            ).fetchone()
            if active is not None:
                raise ValueError(f"cv_regeneration_not_allowed:{active['version_id']}")
            parent_id = str(parent_cv_version_id or "").strip() or None
            if parent_id is not None:
                parent = conn.execute(
                    "SELECT run_job_id FROM cv_versions WHERE version_id=?", (parent_id,)
                ).fetchone()
                if parent is None or str(parent["run_job_id"] or "") != normalized_job_id:
                    raise ValueError("parent_cv_version_invalid")
            ordinal = int(
                conn.execute(
                    "SELECT COALESCE(MAX(ordinal), 0) + 1 FROM cv_versions WHERE run_job_id=?",
                    (normalized_job_id,),
                ).fetchone()[0]
            )
            conn.execute(
                """INSERT INTO cv_versions (
                       version_id, run_job_id, parent_cv_version_id, ordinal, generation_status,
                       created_at, source_profile_revision, source_settings_revision,
                       input_snapshot_json, input_checksum, filename, media_type,
                       action_id, idempotency_key, run_id, job_url
                   ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, 'text/markdown; charset=utf-8', ?, ?, ?, ?)""",
                (
                    normalized_version_id,
                    normalized_job_id,
                    parent_id,
                    ordinal,
                    now,
                    source_profile_revision,
                    source_settings_revision,
                    snapshot_json,
                    hashlib.sha256(snapshot_json.encode("utf-8")).hexdigest(),
                    f"{normalized_version_id}.md",
                    str(action_id or "").strip() or None,
                    normalized_key,
                    str(job["run_id"]),
                    job["source_url"],
                ),
            )
            conn.execute(
                "UPDATE run_jobs SET current_cv_version_id=?, row_revision=row_revision+1 WHERE run_job_id=?",
                (normalized_version_id, normalized_job_id),
            )
            row = conn.execute(
                "SELECT * FROM cv_versions WHERE version_id=?", (normalized_version_id,)
            ).fetchone()
            conn.commit()
            return {**_cv_projection(conn, row), "idempotent_replay": False}
        except Exception:
            conn.rollback()
            raise


def update_cv_version(
    version_id: str,
    *,
    generation_status: str,
    content: bytes | None = None,
    metadata: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    terminal_statuses = {
        "generated", "review_required", "validation_failed", "generation_failed",
        "persistence_failed", "cancelled",
    }
    normalized_status = str(generation_status or "").strip()
    if normalized_status not in {"running", *terminal_statuses}:
        raise ValueError("generation_status_invalid")
    metadata = dict(metadata or {})
    content_bytes = bytes(content) if content is not None else None
    if normalized_status in {"generated", "review_required"} and not content_bytes:
        raise ValueError("generated_content_required")
    now = datetime.datetime.now(datetime.timezone.utc)
    now_iso = now.isoformat()
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        try:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT * FROM cv_versions WHERE version_id=?", (version_id,)
            ).fetchone()
            if existing is None:
                raise ValueError("cv_not_found")
            current_status = str(existing["generation_status"])
            if current_status in terminal_statuses:
                raise ValueError("cv_version_immutable")
            if current_status == "pending" and normalized_status not in {"running", *terminal_statuses}:
                raise ValueError("cv_generation_transition_invalid")
            if current_status == "running" and normalized_status == "running":
                conn.commit()
                return _cv_projection(conn, existing)
            checksum = hashlib.sha256(content_bytes).hexdigest() if content_bytes is not None else None
            started_at = str(existing["started_at"] or "") or now_iso
            duration_ms = (
                max(0, int((now - datetime.datetime.fromisoformat(started_at)).total_seconds() * 1000))
                if normalized_status in terminal_statuses else None
            )
            conn.execute(
                """UPDATE cv_versions SET generation_status=?, started_at=?, finished_at=?,
                       duration_ms=?, generator_id=COALESCE(?, generator_id),
                       model_id=COALESCE(?, model_id), prompt_id=COALESCE(?, prompt_id),
                       schema_id=COALESCE(?, schema_id), content_length=?, content_checksum=?,
                       content_blob=?, error_code=?, error_message=?, fit_classification=COALESCE(?, fit_classification),
                       generated_at=?, cv_generation_model=COALESCE(?, cv_generation_model),
                       cv_prompt_version=COALESCE(?, cv_prompt_version),
                       cv_schema_version=COALESCE(?, cv_schema_version),
                       cv_structured_json=COALESCE(?, cv_structured_json), cv_markdown=COALESCE(?, cv_markdown),
                       cv_generation_input_fingerprint=COALESCE(?, cv_generation_input_fingerprint),
                       cv_generation_reuse_status=COALESCE(?, cv_generation_reuse_status)
                   WHERE version_id=?""",
                (
                    normalized_status,
                    started_at,
                    now_iso if normalized_status in terminal_statuses else None,
                    duration_ms,
                    metadata.get("generator_id"), metadata.get("model_id"), metadata.get("prompt_id"),
                    metadata.get("schema_id"), len(content_bytes) if content_bytes is not None else None,
                    checksum, content_bytes, error_code, error_message,
                    metadata.get("fit_classification"),
                    now_iso if normalized_status in {"generated", "review_required"} else None,
                    metadata.get("cv_generation_model"), metadata.get("cv_prompt_version"),
                    metadata.get("cv_schema_version"),
                    json.dumps(metadata.get("cv_structured_json"), sort_keys=True)
                    if isinstance(metadata.get("cv_structured_json"), dict)
                    else metadata.get("cv_structured_json"),
                    content_bytes.decode("utf-8") if content_bytes is not None else None,
                    metadata.get("cv_generation_input_fingerprint"),
                    metadata.get("cv_generation_reuse_status"),
                    version_id,
                ),
            )
            row = conn.execute("SELECT * FROM cv_versions WHERE version_id=?", (version_id,)).fetchone()
            conn.commit()
            return _cv_projection(conn, row)
        except Exception:
            conn.rollback()
            raise


def insert_cv_evaluation_row(row: dict[str, Any]) -> dict[str, Any]:
    evaluation_id = str(row.get("cv_evaluation_id") or "").strip()
    version_id = str(row.get("cv_version_id") or "").strip()
    if not evaluation_id or not version_id:
        raise ValueError("cv_evaluation_id and cv_version_id are required")
    is_current = bool(row.get("is_current", True))
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        if is_current:
            conn.execute(
                "UPDATE cv_evaluations SET is_current=0 WHERE cv_version_id=?", (version_id,)
            )
        conn.execute(
            """INSERT INTO cv_evaluations (
                cv_evaluation_id, cv_version_id, status, fit_classification, score, reason,
                evidence_json, evaluator_id, model_id, prompt_id, schema_id, started_at,
                finished_at, error_code, error_message, retry_count, next_retry_at, is_current
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                evaluation_id, version_id, row.get("status") or "pending",
                row.get("fit_classification"), row.get("score"), row.get("reason"),
                json.dumps(row.get("evidence_json"), sort_keys=True)
                if isinstance(row.get("evidence_json"), dict)
                else row.get("evidence_json"),
                row.get("evaluator_id"), row.get("model_id"), row.get("prompt_id"),
                row.get("schema_id"), row.get("started_at"), row.get("finished_at"),
                row.get("error_code"), row.get("error_message"), int(row.get("retry_count") or 0),
                row.get("next_retry_at"), int(is_current),
            ),
        )
        if is_current:
            conn.execute(
                """UPDATE run_jobs SET current_cv_evaluation_id=?, row_revision=row_revision+1
                   WHERE current_cv_version_id=?""",
                (evaluation_id, version_id),
            )
        conn.commit()
    return dict(row)


def update_cv_evaluation(
    cv_evaluation_id: str,
    *,
    status: str,
    fit_classification: str | None = None,
    score: float | None = None,
    reason: str | None = None,
    evidence: dict[str, Any] | None = None,
    error_code: str | None = None,
    error_message: str | None = None,
    retry_count: int = 0,
    next_retry_at: str | None = None,
) -> dict[str, Any]:
    normalized_status = str(status or "").strip()
    if normalized_status not in {"running", "succeeded", "failed"}:
        raise ValueError("evaluation_status_invalid")
    if normalized_status == "succeeded" and fit_classification not in {"strong", "stretch", "skip"}:
        raise ValueError("fit_classification_invalid")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        cursor = conn.execute(
            """UPDATE cv_evaluations SET status=?, fit_classification=?, score=?, reason=?,
                   evidence_json=?, finished_at=?, error_code=?, error_message=?, retry_count=?,
                   next_retry_at=? WHERE cv_evaluation_id=?""",
            (
                normalized_status,
                fit_classification,
                score,
                reason,
                json.dumps(evidence, sort_keys=True) if evidence is not None else None,
                now if normalized_status in {"succeeded", "failed"} else None,
                error_code,
                error_message,
                max(0, int(retry_count)),
                next_retry_at,
                cv_evaluation_id,
            ),
        )
        if not cursor.rowcount:
            raise ValueError("evaluation_not_found")
        row = conn.execute(
            "SELECT * FROM cv_evaluations WHERE cv_evaluation_id=?", (cv_evaluation_id,)
        ).fetchone()
        conn.commit()
        return dict(row)


def insert_cv_review_event(row: dict[str, Any]) -> dict[str, Any]:
    created_at = str(row.get("created_at") or datetime.datetime.now(datetime.timezone.utc).isoformat())
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.execute(
            """INSERT INTO cv_review_events (
                review_event_id, cv_version_id, cv_evaluation_id, from_state, to_state,
                actor, note, action_id, idempotency_key, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                row.get("review_event_id"), row.get("cv_version_id"),
                row.get("cv_evaluation_id"), row.get("from_state"), row.get("to_state"),
                row.get("actor"), row.get("note"), row.get("action_id"),
                row.get("idempotency_key"), created_at,
            ),
        )
        conn.commit()
    return {**row, "created_at": created_at}


def get_cv_download(version_id: str, *_args: Any, **_kwargs: Any) -> dict[str, Any] | None:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM cv_versions WHERE version_id=?", (version_id,)
        ).fetchone()
    if row is None:
        return None
    if str(row["generation_status"]) not in {"generated", "review_required"}:
        return None
    content = bytes(row["content_blob"] or b"")
    if (
        not content
        or int(row["content_length"] or -1) != len(content)
        or str(row["content_checksum"] or "") != hashlib.sha256(content).hexdigest()
    ):
        raise ValueError("artifact_integrity_mismatch")
    return {
        "version_id": version_id,
        "content": content,
        "content_length": len(content),
        "content_checksum": str(row["content_checksum"]),
        "media_type": str(row["media_type"] or "text/markdown; charset=utf-8"),
        "filename": str(row["filename"] or f"{version_id}.md"),
    }


def get_cv_markdown(version_id: str, *_args: Any, **_kwargs: Any) -> str | None:
    download = get_cv_download(version_id)
    if download is None:
        return None
    return bytes(download["content"]).decode("utf-8")


def get_debug_bundle_availability(
    run_id: str, *_args: Any, **_kwargs: Any
) -> dict[str, Any]:
    run = get_run(run_id)
    if run is None:
        return {
            "run_id": run_id,
            "status": "unavailable",
            "reason": "run_not_found",
            "action": None,
        }
    evidence_fields = (
        run.results_export_json,
        run.settings_used_json,
        run.effective_settings_json,
        run.cv_generation_debug_json,
        run.stage_transition_artifacts_json,
    )
    if any(str(value or "").strip() for value in evidence_fields):
        return {"run_id": run_id, "status": "available", "reason": None, "action": "download"}
    if run.status in {RunStatus.QUEUED, RunStatus.RUNNING, RunStatus.AWAITING_CONTINUE, RunStatus.CANCELLING}:
        return {
            "run_id": run_id,
            "status": "not_ready",
            "reason": "run_in_progress",
            "action": "wait",
        }
    return {
        "run_id": run_id,
        "status": "unavailable",
        "reason": "artifact_not_available",
        "action": "inspect_console",
    }


def persist_pipeline_snapshot(
    run_id: str,
    summary: dict[str, Any],
    *,
    run_status: RunStatus,
    snapshot_at: datetime.datetime,
) -> dict[str, Any]:
    snapshot_iso = snapshot_at.isoformat()
    completed_stage_ids = {
        canonical
        for raw_stage_id in list(summary.get("completed_stages") or [])
        if (canonical := canonical_stage_id(str(raw_stage_id))) is not None
    }
    stage_artifacts = dict(summary.get("stage_transition_artifacts") or {})
    if isinstance(stage_artifacts.get("artifacts"), dict):
        stage_artifacts = dict(stage_artifacts["artifacts"])
    stage_blocks = dict(stage_artifacts.get("stages") or {})
    export_results = [
        dict(row) for row in list(summary.get("export_results") or []) if isinstance(row, dict)
    ]
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        run_row = conn.execute(
            "SELECT run_id FROM pipeline_runs WHERE run_id=?", (run_id,)
        ).fetchone()
        if run_row is None:
            raise ValueError("run_not_found")
        try:
            conn.execute("BEGIN IMMEDIATE")
            for raw_stage_id, block_value in stage_blocks.items():
                stage_id = canonical_stage_id(str(raw_stage_id))
                if stage_id is None or not isinstance(block_value, dict):
                    continue
                block = dict(block_value)
                stage_status = run_stage_status_from_pipeline(str(block.get("status") or ""))
                if stage_status.value == "pending" and stage_id in completed_stage_ids:
                    stage_status = run_stage_status_from_pipeline("completed")
                output_counts = dict(block.get("output_counts") or {})
                progress_total = int(summary.get("total_jobs") or 0)
                progress_completed = (
                    progress_total
                    if stage_status.value in {"succeeded", "warning"}
                    else max([0, *[int(value) for value in output_counts.values() if isinstance(value, int)]])
                )
                conn.execute(
                    """UPDATE run_stage_executions SET status=?, progress_completed=?,
                       progress_total=?, started_at=COALESCE(started_at, ?),
                       finished_at=CASE WHEN ? IN ('succeeded','warning','partial','failed','cancelled','skipped')
                                        THEN COALESCE(finished_at, ?) ELSE finished_at END,
                       warning_json=?, error_code=?, error_message=?, evidence_reference=?,
                       row_revision=row_revision+1
                       WHERE run_id=? AND stage_id=?""",
                    (
                        stage_status.value,
                        progress_completed,
                        progress_total,
                        snapshot_iso,
                        stage_status.value,
                        snapshot_iso,
                        json.dumps(block.get("warnings"), sort_keys=True)
                        if block.get("warnings") is not None else None,
                        block.get("error_code"),
                        block.get("error_message"),
                        json.dumps(block.get("evidence_ref"), sort_keys=True)
                        if block.get("evidence_ref") is not None else None,
                        run_id,
                        stage_id,
                    ),
                )
            for stage_id in completed_stage_ids:
                conn.execute(
                    """UPDATE run_stage_executions SET status='succeeded',
                       progress_completed=CASE WHEN progress_total > 0 THEN progress_total ELSE ? END,
                       progress_total=CASE WHEN progress_total > 0 THEN progress_total ELSE ? END,
                       started_at=COALESCE(started_at, ?), finished_at=COALESCE(finished_at, ?),
                       row_revision=row_revision+1
                       WHERE run_id=? AND stage_id=? AND status IN ('pending','running')""",
                    (
                        int(summary.get("total_jobs") or 0),
                        int(summary.get("total_jobs") or 0),
                        snapshot_iso,
                        snapshot_iso,
                        run_id,
                        stage_id,
                    ),
                )

            stage_ordinal = {stage.stage_id: stage.ordinal for stage in PROTOTYPE_STAGES}
            jobs_by_index = {
                int(row["source_index"]): str(row["run_job_id"])
                for row in conn.execute(
                    "SELECT run_job_id, source_index FROM run_jobs WHERE run_id=?", (run_id,)
                ).fetchall()
            }
            for result_row in export_results:
                outcome = dict(result_row.get("job_outcome") or {})
                job_key = str(outcome.get("job_key") or "")
                if not job_key.startswith("input:"):
                    continue
                try:
                    source_index = int(job_key.split(":", 1)[1])
                except ValueError:
                    continue
                run_job_id = jobs_by_index.get(source_index)
                stage_id = canonical_stage_id(str(outcome.get("stage") or ""))
                if run_job_id is None or stage_id is None:
                    continue
                final_ordinal = stage_ordinal[stage_id]
                for prior_stage in PROTOTYPE_STAGES:
                    if prior_stage.ordinal >= final_ordinal:
                        break
                    conn.execute(
                        """INSERT OR IGNORE INTO run_job_stage_results
                           (run_job_id, stage_id, status, outcome_code, reason_code,
                            evidence_json, started_at, finished_at)
                           VALUES (?, ?, 'passed', 'advanced', NULL, '{}', ?, ?)""",
                        (run_job_id, prior_stage.stage_id, snapshot_iso, snapshot_iso),
                    )
                job_status = job_stage_status_from_outcome(
                    str(outcome.get("outcome") or ""), stage_id
                )
                evidence = {
                    "evidence_ref": outcome.get("evidence_ref"),
                    "skip_is_terminal_rejection": False,
                    "pipeline_status": result_row.get("pipeline_status"),
                }
                conn.execute(
                    """INSERT INTO run_job_stage_results (
                        run_job_id, stage_id, status, outcome_code, reason_code,
                        evidence_json, started_at, finished_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(run_job_id, stage_id) DO UPDATE SET
                        status=excluded.status, outcome_code=excluded.outcome_code,
                        reason_code=excluded.reason_code, evidence_json=excluded.evidence_json,
                        finished_at=excluded.finished_at, row_revision=run_job_stage_results.row_revision+1""",
                    (
                        run_job_id,
                        stage_id,
                        job_status.value,
                        outcome.get("outcome"),
                        outcome.get("reason_code"),
                        json.dumps(evidence, sort_keys=True),
                        snapshot_iso,
                        snapshot_iso,
                    ),
                )
                conn.execute(
                    "UPDATE run_jobs SET current_stage_id=?, row_revision=row_revision+1 WHERE run_job_id=?",
                    (stage_id, run_job_id),
                )

            for stage in PROTOTYPE_STAGES:
                counts = conn.execute(
                    """SELECT
                         SUM(r.status IN ('passed','generated')),
                         SUM(r.status IN ('rejected','blocked','failed')),
                         COUNT(*)
                       FROM run_job_stage_results r
                       JOIN run_jobs j ON j.run_job_id=r.run_job_id
                       WHERE j.run_id=? AND r.stage_id=?""",
                    (run_id, stage.stage_id),
                ).fetchone()
                conn.execute(
                    """UPDATE run_stage_executions SET passed_count=?, rejected_count=?,
                       progress_completed=MAX(progress_completed, ?), row_revision=row_revision+1
                       WHERE run_id=? AND stage_id=?""",
                    (
                        int(counts[0] or 0),
                        int(counts[1] or 0),
                        int(counts[2] or 0),
                        run_id,
                        stage.stage_id,
                    ),
                )

            terminal = run_status in {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}
            if terminal:
                unresolved_stage_status = (
                    "cancelled" if run_status == RunStatus.CANCELLED else
                    "failed" if run_status == RunStatus.FAILED else "skipped"
                )
                conn.execute(
                    """UPDATE run_stage_executions SET status=?, finished_at=COALESCE(finished_at, ?),
                       row_revision=row_revision+1
                       WHERE run_id=? AND status IN ('pending','running')""",
                    (unresolved_stage_status, snapshot_iso, run_id),
                )
            usable_results = int(
                conn.execute(
                    """SELECT COUNT(*) FROM run_job_stage_results r
                       JOIN run_jobs j ON j.run_job_id=r.run_job_id
                       WHERE j.run_id=? AND r.status IN ('passed','generated','review_required')""",
                    (run_id,),
                ).fetchone()[0]
            )
            partial_stage_count = int(
                conn.execute(
                    "SELECT COUNT(*) FROM run_stage_executions WHERE run_id=? AND status='partial'",
                    (run_id,),
                ).fetchone()[0]
            )
            _decision_status, partial_completion, status_detail = decide_terminal_run(
                orchestration_completed=run_status == RunStatus.SUCCEEDED,
                cancelled=run_status == RunStatus.CANCELLED,
                required_failure=run_status == RunStatus.FAILED,
                unresolved_jobs=0,
                partial_stages=partial_stage_count,
                usable_results=usable_results,
            )
            total_jobs = int(summary.get("total_jobs") or len(jobs_by_index))
            passed_jobs = int(summary.get("passed_filter") or 0)
            conn.execute(
                """UPDATE pipeline_runs SET backend_status=?, total_jobs=?, passed_jobs=?,
                   rejected_jobs=?, cvs_generated=?, progress_completed=?, progress_total=?,
                   partial_completion=?, status_detail=?, row_revision=row_revision+1
                   WHERE run_id=?""",
                (
                    run_status.value,
                    total_jobs,
                    passed_jobs,
                    max(0, total_jobs - passed_jobs),
                    int(summary.get("cvs_generated") or 0),
                    len(completed_stage_ids),
                    len(PROTOTYPE_STAGES),
                    int(partial_completion if terminal else False),
                    status_detail if terminal else run_status.value,
                    run_id,
                ),
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {"run_id": run_id, "status": run_status.value}

