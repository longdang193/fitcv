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
import math
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
from fitcv.preference_policy import (
    PreferenceRuntimeContract,
    build_policy_snapshot_identity,
    build_preference_optimization_run_id,
    build_training_run_identity,
)
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
from fitcv_cp.scan_contracts import derive_scan_capabilities, resolve_publication_cutoff
from fitcv_cp.synonym_policy_io import (
    compile_global_synonym_map,
    load_global_synonym_map,
    repair_synonym_policy_mirrors,
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
CONTROL_PLANE_SCHEMA_VERSION = 5
_CANDIDATE_PROFILE_MAX_BYTES = 1024 * 1024
_CANDIDATE_PROFILE_LEASE_SECONDS = 15 * 60

class DatabaseSchemaIncompatibleError(RuntimeError):
    code = "database_schema_incompatible"

    def __init__(self, found_version: int) -> None:
        self.found_version = found_version
        super().__init__(
            f"Database schema is incompatible: found version {found_version}, expected {CONTROL_PLANE_SCHEMA_VERSION}."
        )

class SynonymPolicyRevisionConflict(RuntimeError):
    pass

class CandidateProfileUnavailableError(RuntimeError):
    pass


class ProviderPersistenceRevisionConflict(RuntimeError):
    pass


def _legacy_profile_name(profile_name: Any, original_filename: Any) -> str:
    return str(profile_name or "").strip() or Path(str(original_filename or "")).stem.strip() or "Unnamed profile"


def _migrate_candidate_profiles_v4_to_v5(conn: sqlite3.Connection) -> None:
    profiles = conn.execute(
        "SELECT * FROM candidate_profiles ORDER BY candidate_profile_id"
    ).fetchall()
    columns = [str(row[1]) for row in conn.execute("PRAGMA table_info(candidate_profiles)")]
    records = [dict(zip(columns, row)) for row in profiles]
    succeeded = [record for record in records if record["creation_status"] == "succeeded"]
    failed = [record for record in records if record["creation_status"] == "failed"]
    revision_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM candidate_profile_revisions WHERE candidate_profile_id IN "
            "(SELECT candidate_profile_id FROM candidate_profiles WHERE creation_status='succeeded')"
        ).fetchone()[0]
    )
    run_links = (
        conn.execute(
            "SELECT run_id, candidate_profile_id, candidate_profile_revision_id FROM run_inputs ORDER BY run_id"
        ).fetchall()
        if "run_inputs" in {
            str(row[0]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        else []
    )
    conn.execute(
        """
        CREATE TABLE candidate_profiles_v5 (
            candidate_profile_id TEXT PRIMARY KEY,
            profile_name TEXT COLLATE NOCASE CHECK (
                profile_name IS NULL OR (length(trim(profile_name)) BETWEEN 1 AND 120)
            ),
            original_filename TEXT NOT NULL,
            media_type TEXT NOT NULL,
            byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
            input_checksum TEXT NOT NULL,
            creation_status TEXT NOT NULL CHECK (creation_status IN ('succeeded', 'failed')),
            lifecycle TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle IN ('active', 'archived')),
            failure_code TEXT,
            failure_message TEXT,
            is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
            sort_order INTEGER NOT NULL DEFAULT 0,
            seed_manifest_revision TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT,
            revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
            CHECK (
                (creation_status = 'succeeded' AND failure_code IS NULL AND failure_message IS NULL)
                OR
                (creation_status = 'failed' AND failure_code IS NOT NULL AND failure_message IS NOT NULL)
            ),
            CHECK (creation_status != 'failed' OR lifecycle = 'active'),
            CHECK (
                (lifecycle = 'active' AND archived_at IS NULL)
                OR
                (lifecycle = 'archived' AND archived_at IS NOT NULL)
            ),
            CHECK (is_default = 0 OR (creation_status = 'succeeded' AND lifecycle = 'active'))
        )
        """
    )
    for record in succeeded:
        conn.execute(
            """
            INSERT INTO candidate_profiles_v5 (
                candidate_profile_id, profile_name, original_filename, media_type, byte_length,
                input_checksum, creation_status, lifecycle, failure_code, failure_message,
                is_default, sort_order, seed_manifest_revision, created_at, updated_at,
                archived_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["candidate_profile_id"],
                _legacy_profile_name(record["profile_name"], record["original_filename"]),
                record["original_filename"],
                record["media_type"],
                record["byte_length"],
                record["input_checksum"],
                record["creation_status"],
                record["lifecycle"],
                record["failure_code"],
                record["failure_message"],
                record["is_default"],
                record["sort_order"],
                record["seed_manifest_revision"],
                record["created_at"],
                record["updated_at"],
                record["archived_at"],
                record["revision"],
            ),
        )
    for record in failed:
        profile_id = str(record["candidate_profile_id"])
        attempt_id = f"legacy-attempt-{profile_id}"
        source_document_id = f"legacy-source-{profile_id}"
        failure = {
            "code": str(record["failure_code"] or "candidate_profile_legacy_upload_failed"),
            "message": str(record["failure_message"] or "Legacy Candidate Profile upload failed."),
            "retryable": False,
            "stage": "legacy_direct_upload",
            "migration_source_id": profile_id,
        }
        conn.execute(
            """
            INSERT INTO candidate_profile_creation_attempts (
                attempt_id, profile_name, creation_status, revision, source_document_id,
                processing_attempt, failure_json, next_action, source_purge_after,
                created_at, updated_at
            ) VALUES (?, ?, 'failed', 1, ?, 0, ?, 'new_upload', ?, ?, ?)
            """,
            (
                attempt_id,
                _legacy_profile_name(record["profile_name"], record["original_filename"]),
                source_document_id,
                json.dumps(failure, sort_keys=True, separators=(",", ":")),
                record["updated_at"],
                record["created_at"],
                record["updated_at"],
            ),
        )
        conn.execute(
            """
            INSERT INTO candidate_profile_source_documents (
                source_document_id, attempt_id, original_filename, media_type, byte_length,
                checksum, source_bytes, source_available, purged_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, NULL, 0, ?, ?)
            """,
            (
                source_document_id,
                attempt_id,
                record["original_filename"],
                record["media_type"],
                record["byte_length"],
                record["input_checksum"],
                record["updated_at"],
                record["created_at"],
            ),
        )
        conn.execute(
            "DELETE FROM candidate_profile_revisions WHERE candidate_profile_id = ?",
            (profile_id,),
        )
    conn.execute("DROP TABLE candidate_profiles")
    conn.execute("ALTER TABLE candidate_profiles_v5 RENAME TO candidate_profiles")
    conn.execute(
        """
        CREATE UNIQUE INDEX ux_candidate_profiles_active_default
        ON candidate_profiles(is_default)
        WHERE creation_status = 'succeeded' AND lifecycle = 'active' AND is_default = 1
        """
    )
    if int(conn.execute("SELECT COUNT(*) FROM candidate_profiles").fetchone()[0]) != len(succeeded):
        raise RuntimeError("candidate_profile_migration_count_mismatch")
    if int(conn.execute("SELECT COUNT(*) FROM candidate_profile_revisions").fetchone()[0]) != revision_count:
        raise RuntimeError("candidate_profile_migration_revision_count_mismatch")
    if len({str(record["candidate_profile_id"]) for record in succeeded}) != len(succeeded):
        raise RuntimeError("candidate_profile_migration_identity_mismatch")
    if run_links != conn.execute(
        "SELECT run_id, candidate_profile_id, candidate_profile_revision_id FROM run_inputs ORDER BY run_id"
    ).fetchall():
        raise RuntimeError("candidate_profile_migration_run_link_mismatch")
    if conn.execute("PRAGMA foreign_key_check").fetchall():
        raise RuntimeError("candidate_profile_migration_foreign_key_mismatch")


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
    conn.execute("DELETE FROM candidate_profile_revisions")
    conn.execute("DELETE FROM candidate_profiles")
    conn.execute("DELETE FROM startup_warnings WHERE code = 'candidate_profile_setup_required'")
    for row in candidate_profiles:
        profile_json = str(row["profile_json"])
        profile_revision_id = f"{row['candidate_profile_id']}:1"
        conn.execute(
            """
            INSERT INTO candidate_profiles (
                candidate_profile_id, profile_name, original_filename, media_type, byte_length,
                input_checksum, creation_status, lifecycle, failure_code, failure_message,
                is_default, sort_order, seed_manifest_revision, created_at, updated_at,
                archived_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, 'succeeded', 'active', NULL, NULL, ?, ?, ?, ?, ?, NULL, 1)
            """,
            (
                row["candidate_profile_id"],
                row["name"],
                "candidate_profile.yaml",
                "application/yaml",
                len(profile_json.encode("utf-8")),
                row["checksum"],
                int(row["is_default"]),
                row["sort_order"],
                row["seed_manifest_revision"],
                now,
                now,
            ),
        )
        conn.execute(
            """
            INSERT INTO candidate_profile_revisions (
                profile_revision_id, candidate_profile_id, revision, profile_json,
                checksum, schema_revision, created_at
            ) VALUES (?, ?, 1, ?, ?, ?, ?)
            """,
            (
                profile_revision_id,
                row["candidate_profile_id"],
                profile_json,
                row["checksum"],
                row["seed_manifest_revision"],
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
    if version not in {0, 3, 4, CONTROL_PLANE_SCHEMA_VERSION} or (version == 0 and existing_tables):
        raise DatabaseSchemaIncompatibleError(version)
    schema = """
    CREATE TABLE IF NOT EXISTS candidate_profiles (
        candidate_profile_id TEXT PRIMARY KEY,
        profile_name TEXT COLLATE NOCASE CHECK (profile_name IS NULL OR (length(trim(profile_name)) BETWEEN 1 AND 120)),
        original_filename TEXT NOT NULL,
        media_type TEXT NOT NULL,
        byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
        input_checksum TEXT NOT NULL,
        creation_status TEXT NOT NULL CHECK (creation_status IN ('succeeded', 'failed')),
        lifecycle TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle IN ('active', 'archived')),
        failure_code TEXT,
        failure_message TEXT,
        is_default INTEGER NOT NULL DEFAULT 0 CHECK (is_default IN (0, 1)),
        sort_order INTEGER NOT NULL DEFAULT 0,
        seed_manifest_revision TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        archived_at TEXT,
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        CHECK (
            (creation_status = 'succeeded' AND failure_code IS NULL AND failure_message IS NULL)
            OR
            (creation_status = 'failed' AND failure_code IS NOT NULL AND failure_message IS NOT NULL)
        ),
        CHECK (creation_status != 'failed' OR lifecycle = 'active'),
        CHECK (
            (lifecycle = 'active' AND archived_at IS NULL)
            OR
            (lifecycle = 'archived' AND archived_at IS NOT NULL)
        ),
        CHECK (is_default = 0 OR (creation_status = 'succeeded' AND lifecycle = 'active'))
    );
    CREATE UNIQUE INDEX IF NOT EXISTS ux_candidate_profiles_active_default
        ON candidate_profiles(is_default)
        WHERE creation_status = 'succeeded' AND lifecycle = 'active' AND is_default = 1;

    CREATE TABLE IF NOT EXISTS candidate_profile_revisions (
        profile_revision_id TEXT PRIMARY KEY,
        candidate_profile_id TEXT NOT NULL REFERENCES candidate_profiles(candidate_profile_id) ON DELETE RESTRICT,
        revision INTEGER NOT NULL CHECK (revision > 0),
        profile_json TEXT NOT NULL CHECK (json_valid(profile_json)),
        checksum TEXT NOT NULL,
        schema_revision TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (candidate_profile_id, revision)
    );

    CREATE TABLE IF NOT EXISTS candidate_profile_creation_attempts (
        attempt_id TEXT PRIMARY KEY,
        profile_name TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(profile_name)) BETWEEN 1 AND 120),
        creation_status TEXT NOT NULL CHECK (creation_status IN ('uploaded', 'extracting_base', 'base_review', 'deriving', 'derived_review', 'ready_to_confirm', 'succeeded', 'failed')),
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        source_document_id TEXT NOT NULL UNIQUE,
        processing_stage TEXT,
        processing_claim_id TEXT,
        processing_attempt INTEGER NOT NULL DEFAULT 0 CHECK (processing_attempt >= 0),
        lease_expires_at TEXT,
        extraction_fingerprint TEXT,
        baseline_fingerprint TEXT,
        approved_baseline_fingerprint TEXT,
        derived_fingerprint TEXT,
        approved_derived_fingerprint TEXT,
        confirmation_fingerprint TEXT,
        failure_json TEXT CHECK (failure_json IS NULL OR json_valid(failure_json)),
        resume_stage TEXT,
        next_action TEXT NOT NULL,
        source_purge_after TEXT NOT NULL,
        profile_id TEXT REFERENCES candidate_profiles(candidate_profile_id) ON DELETE RESTRICT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS candidate_profile_source_documents (
        source_document_id TEXT PRIMARY KEY,
        attempt_id TEXT NOT NULL UNIQUE REFERENCES candidate_profile_creation_attempts(attempt_id) ON DELETE CASCADE,
        original_filename TEXT NOT NULL,
        media_type TEXT NOT NULL,
        byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
        checksum TEXT NOT NULL,
        source_bytes BLOB,
        source_available INTEGER NOT NULL DEFAULT 1 CHECK (source_available IN (0, 1)),
        purged_at TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS candidate_profile_source_blocks (
        source_block_id TEXT PRIMARY KEY,
        attempt_id TEXT NOT NULL REFERENCES candidate_profile_creation_attempts(attempt_id) ON DELETE CASCADE,
        source_document_id TEXT NOT NULL REFERENCES candidate_profile_source_documents(source_document_id) ON DELETE CASCADE,
        ordinal INTEGER NOT NULL CHECK (ordinal > 0),
        kind TEXT NOT NULL,
        locator_json TEXT NOT NULL CHECK (json_valid(locator_json)),
        text TEXT NOT NULL,
        checksum TEXT NOT NULL,
        UNIQUE (attempt_id, ordinal)
    );

    CREATE TABLE IF NOT EXISTS candidate_profile_baseline_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        attempt_id TEXT NOT NULL REFERENCES candidate_profile_creation_attempts(attempt_id) ON DELETE CASCADE,
        fingerprint TEXT NOT NULL,
        document_json TEXT NOT NULL CHECK (json_valid(document_json)),
        annotations_json TEXT NOT NULL CHECK (json_valid(annotations_json)),
        runtime_evidence_json TEXT CHECK (runtime_evidence_json IS NULL OR json_valid(runtime_evidence_json)),
        approved INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0, 1)),
        created_at TEXT NOT NULL,
        UNIQUE (attempt_id, fingerprint)
    );

    CREATE TABLE IF NOT EXISTS candidate_profile_derived_snapshots (
        snapshot_id TEXT PRIMARY KEY,
        attempt_id TEXT NOT NULL REFERENCES candidate_profile_creation_attempts(attempt_id) ON DELETE CASCADE,
        baseline_fingerprint TEXT NOT NULL,
        fingerprint TEXT NOT NULL,
        document_json TEXT NOT NULL CHECK (json_valid(document_json)),
        annotations_json TEXT NOT NULL CHECK (json_valid(annotations_json)),
        runtime_evidence_json TEXT CHECK (runtime_evidence_json IS NULL OR json_valid(runtime_evidence_json)),
        approved INTEGER NOT NULL DEFAULT 0 CHECK (approved IN (0, 1)),
        created_at TEXT NOT NULL,
        UNIQUE (attempt_id, fingerprint)
    );

    CREATE TABLE IF NOT EXISTS candidate_profile_review_batches (
        review_batch_id TEXT PRIMARY KEY,
        attempt_id TEXT NOT NULL REFERENCES candidate_profile_creation_attempts(attempt_id) ON DELETE CASCADE,
        stage TEXT NOT NULL CHECK (stage IN ('baseline', 'derived')),
        expected_revision INTEGER NOT NULL,
        operations_json TEXT NOT NULL CHECK (json_valid(operations_json)),
        result_fingerprint TEXT NOT NULL,
        created_at TEXT NOT NULL
    );

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
        candidate_profile_id TEXT REFERENCES candidate_profiles(candidate_profile_id) ON DELETE RESTRICT,
        candidate_profile_revision_id TEXT REFERENCES candidate_profile_revisions(profile_revision_id) ON DELETE RESTRICT,
        candidate_profile_revision INTEGER,
        candidate_profile_name TEXT NOT NULL,
        candidate_profile_json TEXT NOT NULL CHECK (json_valid(candidate_profile_json)),
        settings_revision TEXT NOT NULL,
        settings_snapshot_json TEXT NOT NULL CHECK (json_valid(settings_snapshot_json)),
        synonym_policy_bundle_revision_id TEXT REFERENCES synonym_policy_bundle_revisions(bundle_revision_id) ON DELETE RESTRICT,
        synonym_policy_bundle_checksum TEXT,
        synonym_policy_bundle_snapshot_json TEXT CHECK (
            synonym_policy_bundle_snapshot_json IS NULL OR json_valid(synonym_policy_bundle_snapshot_json)
        ),
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS tracked_companies (
        company_id TEXT PRIMARY KEY,
        company_name TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(company_name)) BETWEEN 1 AND 120),
        careers_url TEXT NOT NULL COLLATE NOCASE UNIQUE,
        provider_id TEXT NOT NULL,
        provider_label TEXT,
        is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
        is_scannable INTEGER NOT NULL DEFAULT 1 CHECK (is_scannable IN (0, 1)),
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS ix_tracked_companies_active_name
        ON tracked_companies(is_active, is_scannable, company_name COLLATE NOCASE, company_id);

    CREATE TABLE IF NOT EXISTS scans (
        scan_id TEXT PRIMARY KEY,
        scan_name TEXT NOT NULL CHECK (length(scan_name) <= 120),
        execution_status TEXT NOT NULL CHECK (execution_status IN ('queued', 'running', 'cancelling', 'succeeded', 'failed', 'cancelled')),
        lifecycle TEXT NOT NULL DEFAULT 'active' CHECK (lifecycle IN ('active', 'archived')),
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0),
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT,
        archived_at TEXT,
        cancel_requested_at TEXT,
        rerun_of_scan_id TEXT REFERENCES scans(scan_id) ON DELETE SET NULL,
        failure_code TEXT,
        failure_message TEXT,
        progress_completed INTEGER NOT NULL DEFAULT 0 CHECK (progress_completed >= 0),
        progress_total INTEGER NOT NULL DEFAULT 0 CHECK (progress_total >= 0),
        CHECK ((lifecycle = 'active' AND archived_at IS NULL) OR (lifecycle = 'archived' AND archived_at IS NOT NULL)),
        CHECK (archived_at IS NULL OR execution_status IN ('succeeded', 'failed', 'cancelled'))
    );
    CREATE INDEX IF NOT EXISTS ix_scans_lifecycle_created
        ON scans(lifecycle, created_at DESC, scan_id DESC);

    CREATE TABLE IF NOT EXISTS scan_inputs (
        scan_id TEXT PRIMARY KEY REFERENCES scans(scan_id) ON DELETE CASCADE,
        input_json TEXT NOT NULL CHECK (json_valid(input_json)),
        company_snapshots_json TEXT NOT NULL CHECK (json_valid(company_snapshots_json)),
        publication_cutoff TEXT,
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS scan_outputs (
        scan_id TEXT PRIMARY KEY REFERENCES scans(scan_id) ON DELETE CASCADE,
        output_json TEXT NOT NULL CHECK (json_valid(output_json) AND json_type(output_json) = 'array'),
        sha256 TEXT NOT NULL,
        byte_length INTEGER NOT NULL CHECK (byte_length >= 0),
        record_count INTEGER NOT NULL CHECK (record_count >= 0),
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS run_scan_inputs (
        run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
        scan_id TEXT NOT NULL REFERENCES scans(scan_id) ON DELETE RESTRICT,
        source_ordinal INTEGER NOT NULL CHECK (source_ordinal >= 0),
        scan_output_sha256 TEXT NOT NULL,
        PRIMARY KEY (run_id, scan_id),
        UNIQUE (run_id, source_ordinal)
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
        run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
        run_job_id TEXT NOT NULL REFERENCES run_jobs(run_job_id) ON DELETE CASCADE,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (run_job_id)
    );
    CREATE INDEX IF NOT EXISTS ix_bookmarks_run_created
        ON bookmarks(run_id, created_at DESC, bookmark_id);

    CREATE TABLE IF NOT EXISTS run_job_interest (
        run_job_id TEXT PRIMARY KEY REFERENCES run_jobs(run_job_id) ON DELETE CASCADE,
        rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
        rating_contract_revision TEXT NOT NULL,
        action_id TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        row_revision INTEGER NOT NULL DEFAULT 1 CHECK (row_revision > 0)
    );

    CREATE TABLE IF NOT EXISTS synonym_policy_type_revisions (
        type_revision_id TEXT PRIMARY KEY,
        synonym_type TEXT NOT NULL CHECK (synonym_type IN ('skills', 'domain', 'role_family')),
        revision INTEGER NOT NULL CHECK (revision > 0),
        editor_text TEXT NOT NULL,
        normalized_policy_json TEXT NOT NULL CHECK (json_valid(normalized_policy_json)),
        checksum TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (synonym_type, revision),
        UNIQUE (synonym_type, checksum)
    );

    CREATE TABLE IF NOT EXISTS synonym_policy_drafts (
        synonym_type TEXT PRIMARY KEY CHECK (synonym_type IN ('skills', 'domain', 'role_family')),
        editor_text TEXT NOT NULL,
        normalized_policy_json TEXT CHECK (normalized_policy_json IS NULL OR json_valid(normalized_policy_json)),
        issues_json TEXT NOT NULL DEFAULT '[]' CHECK (json_valid(issues_json)),
        validation_status TEXT NOT NULL CHECK (validation_status IN ('valid', 'invalid')),
        base_type_revision_id TEXT REFERENCES synonym_policy_type_revisions(type_revision_id) ON DELETE RESTRICT,
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        updated_at TEXT NOT NULL,
        CHECK (
            (validation_status = 'valid' AND normalized_policy_json IS NOT NULL)
            OR validation_status = 'invalid'
        )
    );

    CREATE TABLE IF NOT EXISTS synonym_policy_bundle_revisions (
        bundle_revision_id TEXT PRIMARY KEY,
        revision INTEGER NOT NULL UNIQUE CHECK (revision > 0),
        skills_type_revision_id TEXT NOT NULL REFERENCES synonym_policy_type_revisions(type_revision_id) ON DELETE RESTRICT,
        domain_type_revision_id TEXT NOT NULL REFERENCES synonym_policy_type_revisions(type_revision_id) ON DELETE RESTRICT,
        role_family_type_revision_id TEXT NOT NULL REFERENCES synonym_policy_type_revisions(type_revision_id) ON DELETE RESTRICT,
        bundle_checksum TEXT NOT NULL UNIQUE,
        normalized_bundle_json TEXT NOT NULL CHECK (json_valid(normalized_bundle_json)),
        created_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS synonym_policy_state (
        state_id INTEGER PRIMARY KEY CHECK (state_id = 1),
        active_bundle_revision_id TEXT REFERENCES synonym_policy_bundle_revisions(bundle_revision_id) ON DELETE RESTRICT,
        mirror_status TEXT NOT NULL DEFAULT 'in_sync' CHECK (mirror_status IN ('in_sync', 'repair_required', 'repair_failed')),
        mirror_error_code TEXT,
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        updated_at TEXT NOT NULL,
        CHECK (mirror_status = 'repair_failed' OR mirror_error_code IS NULL)
    );

    CREATE TABLE IF NOT EXISTS synonym_suggestions (
        suggestion_id TEXT PRIMARY KEY,
        synonym_type TEXT NOT NULL CHECK (synonym_type IN ('skills', 'domain', 'role_family')),
        alias TEXT NOT NULL,
        canonical TEXT NOT NULL,
        normalized_alias TEXT NOT NULL,
        normalized_canonical TEXT NOT NULL,
        concept_key TEXT NOT NULL UNIQUE,
        review_status TEXT NOT NULL CHECK (review_status IN ('pending', 'approved', 'declined')),
        policy_effect TEXT NOT NULL DEFAULT 'absent' CHECK (policy_effect IN ('absent', 'active', 'blocked')),
        decided_at TEXT,
        decided_by TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        UNIQUE (synonym_type, normalized_alias, normalized_canonical),
        CHECK (
            (review_status = 'approved' AND policy_effect IN ('active', 'blocked'))
            OR
            (review_status IN ('pending', 'declined') AND policy_effect = 'absent')
        )
    );
    CREATE INDEX IF NOT EXISTS ix_synonym_suggestions_queue
        ON synonym_suggestions(synonym_type, review_status, updated_at DESC, suggestion_id);

    CREATE TABLE IF NOT EXISTS synonym_suggestion_sources (
        suggestion_id TEXT NOT NULL REFERENCES synonym_suggestions(suggestion_id) ON DELETE CASCADE,
        run_id TEXT NOT NULL REFERENCES pipeline_runs(run_id) ON DELETE CASCADE,
        evidence_json TEXT NOT NULL CHECK (json_valid(evidence_json)),
        occurrence_count INTEGER NOT NULL DEFAULT 1 CHECK (occurrence_count > 0),
        first_seen_at TEXT NOT NULL,
        last_seen_at TEXT NOT NULL,
        PRIMARY KEY (suggestion_id, run_id)
    );

    CREATE TABLE IF NOT EXISTS synonym_processing_runs (
        processing_run_id TEXT PRIMARY KEY,
        processed_at TEXT NOT NULL,
        total_processed INTEGER NOT NULL CHECK (total_processed >= 0),
        approved_count INTEGER NOT NULL CHECK (approved_count >= 0),
        declined_count INTEGER NOT NULL CHECK (declined_count >= 0),
        pending_count INTEGER NOT NULL CHECK (pending_count >= 0),
        successfully_added_count INTEGER NOT NULL CHECK (successfully_added_count >= 0),
        source_operation TEXT NOT NULL,
        issue_count INTEGER NOT NULL DEFAULT 0 CHECK (issue_count >= 0),
        summary_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(summary_json))
    );
    CREATE INDEX IF NOT EXISTS ix_synonym_processing_runs_processed
        ON synonym_processing_runs(processed_at DESC, processing_run_id);

    CREATE TABLE IF NOT EXISTS pipeline_settings (
        setting_key TEXT NOT NULL,
        setting_value_json TEXT NOT NULL,
        updated_by TEXT,
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS custom_api_providers (
        provider_id TEXT PRIMARY KEY,
        display_name TEXT NOT NULL COLLATE NOCASE CHECK (length(trim(display_name)) BETWEEN 1 AND 120),
        compatibility TEXT NOT NULL CHECK (compatibility IN ('openai', 'anthropic')),
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (display_name)
    );

    CREATE TABLE IF NOT EXISTS api_provider_connections (
        provider_id TEXT PRIMARY KEY,
        base_url TEXT,
        api_type TEXT NOT NULL,
        verification_status TEXT NOT NULL CHECK (verification_status IN ('verified', 'not_configured')),
        verified_at TEXT,
        connection_revision INTEGER NOT NULL CHECK (connection_revision > 0),
        credential_account TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        CHECK (
            (verification_status = 'verified' AND verified_at IS NOT NULL)
            OR
            (verification_status = 'not_configured' AND verified_at IS NULL)
        )
    );

    CREATE TABLE IF NOT EXISTS api_provider_state (
        provider_id TEXT PRIMARY KEY,
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS api_provider_models (
        model_record_id TEXT PRIMARY KEY,
        provider_id TEXT NOT NULL,
        model_id TEXT NOT NULL CHECK (length(trim(model_id)) BETWEEN 1 AND 255),
        validation_status TEXT NOT NULL CHECK (validation_status IN ('validated', 'needs_retest')),
        validated_connection_revision INTEGER CHECK (validated_connection_revision > 0),
        last_tested_at TEXT,
        last_test_error_code TEXT CHECK (last_test_error_code IS NULL OR length(last_test_error_code) <= 120),
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (provider_id, model_id),
        CHECK (
            validation_status != 'validated'
            OR
            (validated_connection_revision IS NOT NULL AND last_tested_at IS NOT NULL AND last_test_error_code IS NULL)
        )
    );

    CREATE TABLE IF NOT EXISTS configuration_resources (
        resource_name TEXT PRIMARY KEY,
        resource_json TEXT NOT NULL CHECK (json_valid(resource_json)),
        revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
        updated_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS integration_migrations (
        migration_key TEXT PRIMARY KEY,
        details_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details_json)),
        completed_at TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS idempotent_actions (
        action_id TEXT PRIMARY KEY,
        action_scope TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        request_fingerprint TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('queued', 'running', 'succeeded', 'failed')),
        response_json TEXT CHECK (response_json IS NULL OR json_valid(response_json)),
        response_blob BLOB,
        response_media_type TEXT,
        response_filename TEXT,
        response_checksum TEXT,
        error_json TEXT CHECK (error_json IS NULL OR json_valid(error_json)),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (action_scope, idempotency_key),
        CHECK (
            status != 'succeeded'
            OR
            (
                response_json IS NOT NULL
                AND response_blob IS NULL
                AND response_media_type IS NULL
                AND response_filename IS NULL
                AND response_checksum IS NULL
            )
            OR
            (
                response_json IS NULL
                AND response_blob IS NOT NULL
                AND response_media_type IS NOT NULL
                AND response_filename IS NOT NULL
                AND response_checksum IS NOT NULL
            )
        )
    );
    """
    foreign_keys_disabled = version == 4
    if foreign_keys_disabled:
        conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        for statement in schema.split(";"):
            if statement.strip():
                conn.execute(statement)
        if version == 4:
            _migrate_candidate_profiles_v4_to_v5(conn)
        if candidate_profiles is not None:
            _persist_initial_profile_state(conn, candidate_profiles, startup_warning)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        from fitcv_cp.settings_store import CONFIGURATION_RESOURCE_DEFAULTS

        conn.executemany(
            """
            INSERT OR IGNORE INTO configuration_resources (
                resource_name, resource_json, revision, updated_at
            ) VALUES (?, ?, 1, ?)
            """,
            [
                (
                    resource_name,
                    json.dumps(value, sort_keys=True, separators=(",", ":")),
                    now,
                )
                for resource_name, value in CONFIGURATION_RESOURCE_DEFAULTS.items()
            ],
        )
        for key, value in (
            ("synonym_management.apply_approved_enabled", True),
            ("synonym_management.auto_accept_suggestions_enabled", False),
        ):
            if conn.execute(
                "SELECT 1 FROM pipeline_settings WHERE setting_key = ? LIMIT 1",
                (key,),
            ).fetchone() is None:
                conn.execute(
                    "INSERT INTO pipeline_settings VALUES (?, ?, ?, ?)",
                    (key, json.dumps(value), "system", now),
                )
        conn.execute(f"PRAGMA user_version = {CONTROL_PLANE_SCHEMA_VERSION}")
        conn.commit()
    except Exception:
        if conn.in_transaction:
            conn.rollback()
        raise
    finally:
        if foreign_keys_disabled:
            conn.execute("PRAGMA foreign_keys = ON")


def _policy_checksum(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def _policy_editor_text(mappings: dict[str, str]) -> str:
    return "".join(f"{alias}: {canonical}\n" for alias, canonical in sorted(mappings.items()))

def _seed_synonym_policy_bundle(conn: sqlite3.Connection, policies: dict[str, dict[str, str]]) -> None:
    if conn.execute("SELECT active_bundle_revision_id FROM synonym_policy_state WHERE state_id = 1").fetchone():
        return
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    type_ids: dict[str, str] = {}
    for synonym_type in ("skills", "domain", "role_family"):
        normalized = dict(sorted((policies.get(synonym_type) or {}).items()))
        checksum = _policy_checksum(normalized)
        type_revision_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"synonym-policy:{synonym_type}:1:{checksum}"))
        type_ids[synonym_type] = type_revision_id
        editor_text = _policy_editor_text(normalized)
        conn.execute(
            "INSERT INTO synonym_policy_type_revisions VALUES (?, ?, 1, ?, ?, ?, ?)",
            (type_revision_id, synonym_type, editor_text, json.dumps(normalized), checksum, now),
        )
        conn.execute(
            "INSERT INTO synonym_policy_drafts VALUES (?, ?, ?, '[]', 'valid', ?, 1, ?)",
            (synonym_type, editor_text, json.dumps(normalized), type_revision_id, now),
        )
    bundle = {synonym_type: dict(sorted((policies.get(synonym_type) or {}).items())) for synonym_type in type_ids}
    bundle_checksum = _policy_checksum(bundle)
    bundle_revision_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"synonym-bundle:1:{bundle_checksum}"))
    conn.execute(
        "INSERT INTO synonym_policy_bundle_revisions VALUES (?, 1, ?, ?, ?, ?, ?, ?)",
        (
            bundle_revision_id,
            type_ids["skills"],
            type_ids["domain"],
            type_ids["role_family"],
            bundle_checksum,
            json.dumps(bundle),
            now,
        ),
    )
    conn.execute(
        "INSERT INTO synonym_policy_state VALUES (1, ?, 'in_sync', NULL, 1, ?)",
        (bundle_revision_id, now),
    )

def initialize_control_plane_database(
    database_path: Path,
    candidate_profile_path: Path,
    *,
    synonym_paths: dict[str, Path] | None = None,
) -> None:
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
    paths = synonym_paths or {}
    policies = {
        synonym_type: load_global_synonym_map(
            synonym_type,
            path=paths.get(synonym_type),
        )
        for synonym_type in ("skills", "domain", "role_family")
    }
    with _sqlite_connection(database_path) as conn:
        _ensure_control_plane_schema(
            conn,
            candidate_profiles=candidate_profiles,
            startup_warning=warning,
        )
        conn.execute("BEGIN IMMEDIATE")
        _seed_synonym_policy_bundle(conn, policies)
        conn.commit()


def ensure_control_plane_database(
    database_path: Path,
    candidate_profile_path: Path,
    *,
    synonym_paths: dict[str, Path] | None = None,
) -> None:
    if not database_path.exists():
        initialize_control_plane_database(
            database_path,
            candidate_profile_path,
            synonym_paths=synonym_paths,
        )
        return
    with _sqlite_connection(database_path) as conn:
        _ensure_control_plane_schema(conn)
    repair_active_synonym_policy_mirrors(
        database_path=database_path,
        synonym_paths=synonym_paths,
    )

def _synonym_policy_resource(conn: sqlite3.Connection, synonym_type: str) -> dict[str, Any]:
    conn.row_factory = sqlite3.Row
    draft = conn.execute(
        "SELECT * FROM synonym_policy_drafts WHERE synonym_type = ?",
        (synonym_type,),
    ).fetchone()
    state = conn.execute(
        "SELECT active_bundle_revision_id, revision, mirror_status, mirror_error_code FROM synonym_policy_state WHERE state_id = 1"
    ).fetchone()
    active_type = None
    if state and state["active_bundle_revision_id"]:
        column = {
            "skills": "skills_type_revision_id",
            "domain": "domain_type_revision_id",
            "role_family": "role_family_type_revision_id",
        }[synonym_type]
        active_type = conn.execute(
            f"""SELECT tr.* FROM synonym_policy_bundle_revisions br
                JOIN synonym_policy_type_revisions tr ON tr.type_revision_id = br.{column}
                WHERE br.bundle_revision_id = ?""",
            (state["active_bundle_revision_id"],),
        ).fetchone()
    return {
        "synonym_type": synonym_type,
        "editor_text": str(draft["editor_text"]) if draft else (_policy_editor_text(json.loads(active_type["normalized_policy_json"])) if active_type else ""),
        "normalized_policy": json.loads(draft["normalized_policy_json"]) if draft and draft["normalized_policy_json"] else None,
        "issues": json.loads(draft["issues_json"]) if draft else [],
        "validation_status": str(draft["validation_status"]) if draft else "valid",
        "draft_revision": int(draft["revision"]) if draft else 0,
        "active_type_revision_id": str(active_type["type_revision_id"]) if active_type else None,
        "active_type_revision": int(active_type["revision"]) if active_type else 0,
        "active_bundle_revision_id": str(state["active_bundle_revision_id"]) if state and state["active_bundle_revision_id"] else None,
        "active_bundle_revision": int(state["revision"]) if state else 0,
        "mirror_status": str(state["mirror_status"]) if state else "in_sync",
        "mirror_error_code": state["mirror_error_code"] if state else None,
    }

def get_synonym_policy(
    synonym_type: str,
    *,
    database_path: Path | None = None,
) -> dict[str, Any]:
    if synonym_type not in {"skills", "domain", "role_family"}:
        raise ValueError(f"unsupported synonym type: {synonym_type}")
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        return _synonym_policy_resource(conn, synonym_type)

def save_synonym_policy_draft(
    synonym_type: str,
    *,
    editor_text: str,
    normalized_policy: dict[str, str] | None,
    issues: list[dict[str, Any]],
    expected_draft_revision: int,
    database_path: Path | None = None,
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        current = conn.execute(
            "SELECT revision FROM synonym_policy_drafts WHERE synonym_type = ?",
            (synonym_type,),
        ).fetchone()
        current_revision = int(current[0]) if current else 0
        if current_revision != int(expected_draft_revision):
            conn.rollback()
            raise SynonymPolicyRevisionConflict("Synonym policy draft changed since last read")
        active = _synonym_policy_resource(conn, synonym_type)
        revision = current_revision + 1
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            """INSERT INTO synonym_policy_drafts (
                    synonym_type, editor_text, normalized_policy_json, issues_json,
                    validation_status, base_type_revision_id, revision, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(synonym_type) DO UPDATE SET
                    editor_text=excluded.editor_text,
                    normalized_policy_json=excluded.normalized_policy_json,
                    issues_json=excluded.issues_json,
                    validation_status=excluded.validation_status,
                    base_type_revision_id=excluded.base_type_revision_id,
                    revision=excluded.revision,
                    updated_at=excluded.updated_at""",
            (
                synonym_type,
                editor_text,
                json.dumps(normalized_policy) if normalized_policy is not None else None,
                json.dumps(issues),
                "valid" if not issues else "invalid",
                active["active_type_revision_id"],
                revision,
                now,
            ),
        )
        conn.commit()
        return _synonym_policy_resource(conn, synonym_type)

def resolve_active_synonym_bundle(*, database_path: Path | None = None) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            """SELECT br.*, ps.mirror_status, ps.mirror_error_code,
                      skills.revision AS skills_type_revision,
                      domain.revision AS domain_type_revision,
                      role_family.revision AS role_family_type_revision
               FROM synonym_policy_state ps
               JOIN synonym_policy_bundle_revisions br
                 ON br.bundle_revision_id = ps.active_bundle_revision_id
               JOIN synonym_policy_type_revisions skills
                 ON skills.type_revision_id = br.skills_type_revision_id
               JOIN synonym_policy_type_revisions domain
                 ON domain.type_revision_id = br.domain_type_revision_id
               JOIN synonym_policy_type_revisions role_family
                 ON role_family.type_revision_id = br.role_family_type_revision_id
               WHERE ps.state_id = 1"""
        ).fetchone()
    if row is None:
        return {
            "bundle_revision_id": None,
            "revision": 0,
            "bundle_checksum": None,
            "normalized_bundle": {"skills": {}, "domain": {}, "role_family": {}},
            "type_revisions": {},
            "mirror_status": "in_sync",
            "mirror_error_code": None,
        }
    return {
        "bundle_revision_id": str(row["bundle_revision_id"]),
        "revision": int(row["revision"]),
        "bundle_checksum": str(row["bundle_checksum"]),
        "normalized_bundle": json.loads(row["normalized_bundle_json"]),
        "type_revisions": {
            "skills": {
                "type_revision_id": str(row["skills_type_revision_id"]),
                "revision": int(row["skills_type_revision"]),
            },
            "domain": {
                "type_revision_id": str(row["domain_type_revision_id"]),
                "revision": int(row["domain_type_revision"]),
            },
            "role_family": {
                "type_revision_id": str(row["role_family_type_revision_id"]),
                "revision": int(row["role_family_type_revision"]),
            },
        },
        "mirror_status": str(row["mirror_status"]),
        "mirror_error_code": row["mirror_error_code"],
    }

def repair_active_synonym_policy_mirrors(
    *,
    database_path: Path | None = None,
    synonym_paths: dict[str, Path] | None = None,
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    active = resolve_active_synonym_bundle(database_path=path)
    try:
        repair_synonym_policy_mirrors(active["normalized_bundle"], paths=synonym_paths)
    except (OSError, UnicodeError, ValueError):
        with _sqlite_connection(path) as conn:
            _ensure_control_plane_schema(conn)
            conn.execute(
                """UPDATE synonym_policy_state
                   SET mirror_status='repair_failed', mirror_error_code=?, updated_at=?
                   WHERE state_id=1""",
                (
                    "synonym_mirror_repair_failed",
                    datetime.datetime.now(datetime.timezone.utc).isoformat(),
                ),
            )
            conn.commit()
        raise
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.execute(
            """UPDATE synonym_policy_state
               SET mirror_status='in_sync', mirror_error_code=NULL, updated_at=?
               WHERE state_id=1""",
            (datetime.datetime.now(datetime.timezone.utc).isoformat(),),
        )
        conn.commit()
    return resolve_active_synonym_bundle(database_path=path)

def _activate_synonym_policy_bundle_in_transaction(
    conn: sqlite3.Connection,
    synonym_type: str,
    *,
    editor_text: str,
    normalized_policy: dict[str, str],
    expected_draft_revision: int,
    expected_active_bundle_revision_id: str | None,
) -> dict[str, Any]:
    draft = conn.execute(
        "SELECT revision FROM synonym_policy_drafts WHERE synonym_type = ?",
        (synonym_type,),
    ).fetchone()
    draft_revision = int(draft["revision"]) if draft else 0
    state = conn.execute("SELECT * FROM synonym_policy_state WHERE state_id = 1").fetchone()
    active_bundle_id = str(state["active_bundle_revision_id"]) if state and state["active_bundle_revision_id"] else None
    if draft_revision != int(expected_draft_revision) or active_bundle_id != expected_active_bundle_revision_id:
        raise SynonymPolicyRevisionConflict("Synonym policy changed since last read")
    active_bundle = conn.execute(
        "SELECT * FROM synonym_policy_bundle_revisions WHERE bundle_revision_id = ?",
        (active_bundle_id,),
    ).fetchone() if active_bundle_id else None
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    type_ids: dict[str, str] = {}
    bundle_maps = {"skills": {}, "domain": {}, "role_family": {}}
    if active_bundle:
        bundle_maps = json.loads(active_bundle["normalized_bundle_json"])
        type_ids = {
            "skills": str(active_bundle["skills_type_revision_id"]),
            "domain": str(active_bundle["domain_type_revision_id"]),
            "role_family": str(active_bundle["role_family_type_revision_id"]),
        }
    for current_type in ("skills", "domain", "role_family"):
        if current_type in type_ids:
            continue
        empty_checksum = _policy_checksum({})
        empty_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"synonym-policy:{current_type}:1:{empty_checksum}"))
        conn.execute(
            "INSERT OR IGNORE INTO synonym_policy_type_revisions VALUES (?, ?, 1, '', '{}', ?, ?)",
            (empty_id, current_type, empty_checksum, now),
        )
        type_ids[current_type] = empty_id
    normalized = dict(sorted(normalized_policy.items()))
    checksum = _policy_checksum(normalized)
    existing_type = conn.execute(
        "SELECT type_revision_id, revision FROM synonym_policy_type_revisions WHERE synonym_type = ? AND checksum = ?",
        (synonym_type, checksum),
    ).fetchone()
    if existing_type:
        type_revision_id = str(existing_type["type_revision_id"])
    else:
        next_type_revision = int(conn.execute(
            "SELECT COALESCE(MAX(revision), 0) + 1 FROM synonym_policy_type_revisions WHERE synonym_type = ?",
            (synonym_type,),
        ).fetchone()[0])
        type_revision_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO synonym_policy_type_revisions VALUES (?, ?, ?, ?, ?, ?, ?)",
            (type_revision_id, synonym_type, next_type_revision, editor_text, json.dumps(normalized), checksum, now),
        )
    type_ids[synonym_type] = type_revision_id
    bundle_maps[synonym_type] = normalized
    bundle_checksum = _policy_checksum(bundle_maps)
    existing_bundle = conn.execute(
        "SELECT bundle_revision_id, revision FROM synonym_policy_bundle_revisions WHERE bundle_checksum = ?",
        (bundle_checksum,),
    ).fetchone()
    if existing_bundle:
        bundle_revision_id = str(existing_bundle["bundle_revision_id"])
        bundle_revision = int(existing_bundle["revision"])
    else:
        bundle_revision = int(conn.execute(
            "SELECT COALESCE(MAX(revision), 0) + 1 FROM synonym_policy_bundle_revisions"
        ).fetchone()[0])
        bundle_revision_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO synonym_policy_bundle_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                bundle_revision_id,
                bundle_revision,
                type_ids["skills"],
                type_ids["domain"],
                type_ids["role_family"],
                bundle_checksum,
                json.dumps(bundle_maps),
                now,
            ),
        )
    conn.execute(
        """INSERT INTO synonym_policy_drafts VALUES (?, ?, ?, '[]', 'valid', ?, ?, ?)
           ON CONFLICT(synonym_type) DO UPDATE SET
             editor_text=excluded.editor_text,
             normalized_policy_json=excluded.normalized_policy_json,
             issues_json='[]', validation_status='valid',
             base_type_revision_id=excluded.base_type_revision_id,
             revision=excluded.revision, updated_at=excluded.updated_at""",
        (synonym_type, editor_text, json.dumps(normalized), type_revision_id, draft_revision + 1, now),
    )
    state_revision = int(state["revision"]) + 1 if state else 1
    conn.execute(
        """INSERT INTO synonym_policy_state VALUES (1, ?, 'repair_required', NULL, ?, ?)
           ON CONFLICT(state_id) DO UPDATE SET
             active_bundle_revision_id=excluded.active_bundle_revision_id,
             mirror_status='repair_required', mirror_error_code=NULL,
             revision=excluded.revision, updated_at=excluded.updated_at""",
        (bundle_revision_id, state_revision, now),
    )
    for alias, canonical in normalized.items():
        conn.execute(
            """UPDATE synonym_suggestions
               SET policy_effect='active', updated_at=?, revision=revision + 1
               WHERE synonym_type=? AND normalized_alias=? AND normalized_canonical=?
                 AND review_status='approved' AND policy_effect='blocked'""",
            (now, synonym_type, alias, canonical),
        )
    return {
        "active_bundle_revision_id": bundle_revision_id,
        "active_bundle_revision": bundle_revision,
        "bundle_checksum": bundle_checksum,
        "normalized_bundle": bundle_maps,
    }

def activate_synonym_policy_bundle(
    synonym_type: str,
    *,
    editor_text: str,
    normalized_policy: dict[str, str],
    expected_draft_revision: int,
    expected_active_bundle_revision_id: str | None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    if synonym_type not in {"skills", "domain", "role_family"}:
        raise ValueError(f"unsupported synonym type: {synonym_type}")
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = _activate_synonym_policy_bundle_in_transaction(
                conn,
                synonym_type,
                editor_text=editor_text,
                normalized_policy=normalized_policy,
                expected_draft_revision=expected_draft_revision,
                expected_active_bundle_revision_id=expected_active_bundle_revision_id,
            )
        except Exception:
            conn.rollback()
            raise
        conn.commit()
    result["policy"] = get_synonym_policy(synonym_type, database_path=path)
    return result

def activate_synonym_policy_bundle_set(
    policies: dict[str, dict[str, str]],
    *,
    expected_active_bundle_revision_id: str | None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    normalized = {
        synonym_type: compile_global_synonym_map(synonym_type, policies.get(synonym_type) or {})
        for synonym_type in ("skills", "domain", "role_family")
    }
    path = database_path or Path(_local_sqlite_path())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        state = conn.execute("SELECT * FROM synonym_policy_state WHERE state_id = 1").fetchone()
        active_id = str(state["active_bundle_revision_id"]) if state and state["active_bundle_revision_id"] else None
        if active_id != expected_active_bundle_revision_id:
            conn.rollback()
            raise SynonymPolicyRevisionConflict("Synonym policy changed since backup was inspected")
        type_ids: dict[str, str] = {}
        for synonym_type, mapping in normalized.items():
            checksum = _policy_checksum(mapping)
            existing = conn.execute(
                "SELECT type_revision_id FROM synonym_policy_type_revisions WHERE synonym_type = ? AND checksum = ?",
                (synonym_type, checksum),
            ).fetchone()
            if existing:
                type_revision_id = str(existing[0])
            else:
                revision = int(conn.execute(
                    "SELECT COALESCE(MAX(revision), 0) + 1 FROM synonym_policy_type_revisions WHERE synonym_type = ?",
                    (synonym_type,),
                ).fetchone()[0])
                type_revision_id = str(uuid.uuid4())
                conn.execute(
                    "INSERT INTO synonym_policy_type_revisions VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (type_revision_id, synonym_type, revision, _policy_editor_text(mapping), json.dumps(mapping), checksum, now),
                )
            type_ids[synonym_type] = type_revision_id
            draft = conn.execute(
                "SELECT revision FROM synonym_policy_drafts WHERE synonym_type = ?",
                (synonym_type,),
            ).fetchone()
            next_draft_revision = int(draft[0]) + 1 if draft else 1
            conn.execute(
                """INSERT INTO synonym_policy_drafts VALUES (?, ?, ?, '[]', 'valid', ?, ?, ?)
                   ON CONFLICT(synonym_type) DO UPDATE SET
                     editor_text=excluded.editor_text,
                     normalized_policy_json=excluded.normalized_policy_json,
                     issues_json='[]', validation_status='valid',
                     base_type_revision_id=excluded.base_type_revision_id,
                     revision=excluded.revision, updated_at=excluded.updated_at""",
                (synonym_type, _policy_editor_text(mapping), json.dumps(mapping), type_revision_id, next_draft_revision, now),
            )
        bundle_checksum = _policy_checksum(normalized)
        existing_bundle = conn.execute(
            "SELECT bundle_revision_id, revision FROM synonym_policy_bundle_revisions WHERE bundle_checksum = ?",
            (bundle_checksum,),
        ).fetchone()
        if existing_bundle:
            bundle_revision_id, bundle_revision = str(existing_bundle[0]), int(existing_bundle[1])
        else:
            bundle_revision = int(conn.execute(
                "SELECT COALESCE(MAX(revision), 0) + 1 FROM synonym_policy_bundle_revisions"
            ).fetchone()[0])
            bundle_revision_id = str(uuid.uuid4())
            conn.execute(
                "INSERT INTO synonym_policy_bundle_revisions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (bundle_revision_id, bundle_revision, type_ids["skills"], type_ids["domain"], type_ids["role_family"], bundle_checksum, json.dumps(normalized), now),
            )
        state_revision = int(state["revision"]) + 1 if state else 1
        conn.execute(
            """INSERT INTO synonym_policy_state VALUES (1, ?, 'repair_required', NULL, ?, ?)
               ON CONFLICT(state_id) DO UPDATE SET
                 active_bundle_revision_id=excluded.active_bundle_revision_id,
                 mirror_status='repair_required', mirror_error_code=NULL,
                 revision=excluded.revision, updated_at=excluded.updated_at""",
            (bundle_revision_id, state_revision, now),
        )
        conn.commit()
    return resolve_active_synonym_bundle(database_path=path)

def _normalized_synonym_pair(synonym_type: str, alias: str, canonical: str) -> tuple[str, str]:
    compiled = compile_global_synonym_map(synonym_type, {alias: canonical})
    return next(iter(compiled.items()), ("", ""))

def ingest_synonym_suggestions(
    suggestions: list[dict[str, Any]],
    *,
    database_path: Path | None = None,
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    active = resolve_active_synonym_bundle(database_path=path)["normalized_bundle"]
    created_count = 0
    source_count = 0
    suppressed_count = 0
    suggestion_ids: list[str] = []
    actionable_suggestion_ids: list[str] = []
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        for item in suggestions:
            synonym_type = str(item.get("synonym_type") or "").strip()
            if synonym_type not in {"skills", "domain", "role_family"}:
                raise ValueError("unsupported_synonym_type")
            alias = str(item.get("alias") or "").strip()
            canonical = str(item.get("canonical") or "").strip()
            normalized_alias, normalized_canonical = _normalized_synonym_pair(
                synonym_type, alias, canonical
            )
            if not normalized_alias or not normalized_canonical:
                raise ValueError("invalid_synonym_suggestion")
            if (active.get(synonym_type) or {}).get(normalized_alias) == normalized_canonical:
                suppressed_count += 1
                continue
            concept_key = _policy_checksum(
                [synonym_type, normalized_alias, normalized_canonical]
            )
            existing = conn.execute(
                "SELECT suggestion_id, review_status FROM synonym_suggestions WHERE concept_key = ?",
                (concept_key,),
            ).fetchone()
            if existing:
                suggestion_id = str(existing[0])
                review_status = str(existing[1])
                conn.execute(
                    "UPDATE synonym_suggestions SET updated_at = ?, revision = revision + 1 WHERE suggestion_id = ?",
                    (now, suggestion_id),
                )
            else:
                suggestion_id = str(uuid.uuid4())
                review_status = "pending"
                conn.execute(
                    """INSERT INTO synonym_suggestions (
                        suggestion_id, synonym_type, alias, canonical, normalized_alias,
                        normalized_canonical, concept_key, review_status, policy_effect,
                        decided_at, decided_by, created_at, updated_at, revision
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', 'absent', NULL, NULL, ?, ?, 1)""",
                    (
                        suggestion_id, synonym_type, alias, canonical, normalized_alias,
                        normalized_canonical, concept_key, now, now,
                    ),
                )
                created_count += 1
            suggestion_ids.append(suggestion_id)
            if review_status in {"pending", "declined"}:
                actionable_suggestion_ids.append(suggestion_id)
            run_id = str(item.get("run_id") or "").strip()
            if run_id:
                evidence_json = json.dumps(item.get("evidence") or {}, ensure_ascii=False)
                conn.execute(
                    """INSERT INTO synonym_suggestion_sources (
                        suggestion_id, run_id, evidence_json, occurrence_count, first_seen_at, last_seen_at
                    ) VALUES (?, ?, ?, 1, ?, ?)
                    ON CONFLICT(suggestion_id, run_id) DO UPDATE SET
                        evidence_json=excluded.evidence_json,
                        occurrence_count=synonym_suggestion_sources.occurrence_count + 1,
                        last_seen_at=excluded.last_seen_at""",
                    (suggestion_id, run_id, evidence_json, now, now),
                )
                source_count += 1
        conn.commit()
    return {
        "created_count": created_count,
        "source_count": source_count,
        "suppressed_count": suppressed_count,
        "suggestion_ids": list(dict.fromkeys(suggestion_ids)),
        "actionable_suggestion_ids": list(dict.fromkeys(actionable_suggestion_ids)),
    }

def query_synonym_suggestions(
    *,
    synonym_type: str | None = None,
    review_status: str | None = None,
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    sort: str = "updated_desc",
    database_path: Path | None = None,
) -> dict[str, Any]:
    if page_size not in {10, 20, 50}:
        raise ValueError("page_size must be 10, 20, or 50")
    if sort != "updated_desc":
        raise ValueError("synonym_sort_invalid")
    clauses: list[str] = []
    params: list[Any] = []
    if synonym_type:
        clauses.append("s.synonym_type = ?")
        params.append(synonym_type)
    if review_status:
        clauses.append("s.review_status = ?")
        params.append("pending" if review_status == "deferred" else review_status)
    if search.strip():
        clauses.append("(s.alias LIKE ? COLLATE NOCASE OR s.canonical LIKE ? COLLATE NOCASE)")
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        total = int(conn.execute(
            f"SELECT COUNT(*) FROM synonym_suggestions s {where}", params
        ).fetchone()[0])
        rows = conn.execute(
            f"""SELECT s.*, COUNT(src.run_id) AS source_count
                FROM synonym_suggestions s
                LEFT JOIN synonym_suggestion_sources src ON src.suggestion_id = s.suggestion_id
                {where}
                GROUP BY s.suggestion_id
                ORDER BY s.updated_at DESC, s.suggestion_id
                LIMIT ? OFFSET ?""",
            (*params, page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": total, "page": max(1, page), "page_size": page_size}

def get_synonym_suggestion(
    suggestion_id: str,
    *,
    evidence_page: int = 1,
    evidence_page_size: int = 20,
    database_path: Path | None = None,
) -> dict[str, Any] | None:
    if evidence_page_size not in {10, 20, 50}:
        raise ValueError("page_size must be 10, 20, or 50")
    evidence_page = max(1, evidence_page)
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        row = conn.execute(
            """SELECT s.*, COUNT(src.run_id) AS source_count
               FROM synonym_suggestions s
               LEFT JOIN synonym_suggestion_sources src ON src.suggestion_id = s.suggestion_id
               WHERE s.suggestion_id = ? GROUP BY s.suggestion_id""",
            (suggestion_id,),
        ).fetchone()
        if row is None:
            return None
        source_total = int(conn.execute(
            "SELECT COUNT(*) FROM synonym_suggestion_sources WHERE suggestion_id = ?",
            (suggestion_id,),
        ).fetchone()[0])
        sources = conn.execute(
            """SELECT src.run_id, src.evidence_json, src.occurrence_count,
                      src.first_seen_at, src.last_seen_at, run.run_name,
                      run.backend_status AS run_status, run.created_at AS run_created_at
               FROM synonym_suggestion_sources src
               LEFT JOIN pipeline_runs run ON run.run_id = src.run_id
               WHERE src.suggestion_id = ?
               ORDER BY src.last_seen_at DESC, src.run_id
               LIMIT ? OFFSET ?""",
            (
                suggestion_id,
                evidence_page_size,
                (evidence_page - 1) * evidence_page_size,
            ),
        ).fetchall()
    resource = dict(row)
    resource["sources"] = []
    for source in sources:
        source_resource = dict(source)
        source_resource["evidence"] = json.loads(source_resource.pop("evidence_json"))
        resource["sources"].append(source_resource)
    resource["source_page"] = {
        "page": evidence_page,
        "page_size": evidence_page_size,
        "total_items": source_total,
        "total_pages": (source_total + evidence_page_size - 1) // evidence_page_size,
    }
    return resource

def _record_synonym_processing_run(
    conn: sqlite3.Connection,
    *,
    action: str,
    total: int,
    approved: int = 0,
    declined: int = 0,
    pending: int = 0,
    added: int = 0,
    issues: int = 0,
) -> str:
    processing_run_id = str(uuid.uuid4())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    summary = {
        "action": action, "total_processed": total, "approved": approved,
        "declined": declined, "pending": pending, "successfully_added": added,
    }
    conn.execute(
        "INSERT INTO synonym_processing_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (processing_run_id, now, total, approved, declined, pending, added, action, issues, json.dumps(summary)),
    )
    conn.execute(
        """DELETE FROM synonym_processing_runs WHERE processing_run_id IN (
               SELECT processing_run_id FROM synonym_processing_runs
               ORDER BY processed_at DESC, processing_run_id DESC LIMIT -1 OFFSET 1000
           )"""
    )
    return processing_run_id

def apply_synonym_suggestion_action(
    suggestion_ids: list[str],
    *,
    action: str,
    acted_by: str,
    expected_draft_revision: int | None = None,
    expected_active_bundle_revision_id: str | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    ids = list(dict.fromkeys(str(value).strip() for value in suggestion_ids if str(value).strip()))
    if not ids:
        raise ValueError("selection_required")
    if len(ids) > 1000:
        raise ValueError("selection_too_large")
    if action not in {"approve", "decline", "clear"}:
        raise ValueError("invalid_synonym_action")
    path = database_path or Path(_local_sqlite_path())
    placeholders = ",".join("?" for _ in ids)
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        try:
            conn.execute("BEGIN IMMEDIATE")
            rows = conn.execute(
                f"SELECT * FROM synonym_suggestions WHERE suggestion_id IN ({placeholders})",
                ids,
            ).fetchall()
            if len(rows) != len(ids):
                raise ValueError("synonym_suggestion_not_found")
            types = {str(row["synonym_type"]) for row in rows}
            if len(types) != 1:
                raise ValueError("mixed_synonym_types")
            synonym_type = next(iter(types))
            statuses = {str(row["review_status"]) for row in rows}
            if action == "decline" and statuses != {"pending"}:
                raise ValueError("invalid_synonym_transition")
            if action == "approve" and not statuses.issubset({"pending", "declined"}):
                raise ValueError("invalid_synonym_transition")

            added = 0
            policy_effect = "absent"
            issue_count = 0
            if action == "approve":
                policy = _synonym_policy_resource(conn, synonym_type)
                if expected_draft_revision is not None and (
                    int(policy["draft_revision"]) != int(expected_draft_revision)
                    or policy["active_bundle_revision_id"] != expected_active_bundle_revision_id
                ):
                    raise ValueError("revision_conflict")
                state = conn.execute(
                    "SELECT active_bundle_revision_id FROM synonym_policy_state WHERE state_id = 1"
                ).fetchone()
                active_bundle_id = str(state[0]) if state and state[0] else None
                active_row = conn.execute(
                    "SELECT normalized_bundle_json FROM synonym_policy_bundle_revisions WHERE bundle_revision_id = ?",
                    (active_bundle_id,),
                ).fetchone() if active_bundle_id else None
                active_bundle = json.loads(active_row[0]) if active_row else {
                    "skills": {}, "domain": {}, "role_family": {}
                }
                before = dict(active_bundle.get(synonym_type) or {})
                merged = dict(before)
                requested: dict[str, str] = {}
                conflict = False
                for row in rows:
                    alias = str(row["normalized_alias"])
                    canonical = str(row["normalized_canonical"])
                    if alias in requested and requested[alias] != canonical:
                        conflict = True
                    if alias in before and before[alias] != canonical:
                        conflict = True
                    requested[alias] = canonical
                    merged[alias] = canonical
                editor_text = _policy_editor_text(merged)
                try:
                    if conflict:
                        raise ValueError("synonym alias conflict")
                    compiled = compile_global_synonym_map(synonym_type, merged)
                    _activate_synonym_policy_bundle_in_transaction(
                        conn,
                        synonym_type,
                        editor_text=editor_text,
                        normalized_policy=compiled,
                        expected_draft_revision=int(policy["draft_revision"]),
                        expected_active_bundle_revision_id=policy["active_bundle_revision_id"],
                    )
                    policy_effect = "active"
                    added = sum(
                        1 for alias, canonical in requested.items()
                        if before.get(alias) != canonical
                    )
                except ValueError as exc:
                    issue_count = 1
                    policy_effect = "blocked"
                    issue = {
                        "code": "synonym_cycle" if "cycle" in str(exc).lower() else "synonym_alias_conflict",
                        "message": "Approved mapping is blocked by synonym policy validation.",
                        "severity": "error", "lines": [], "aliases": [], "canonicals": [],
                    }
                    conn.execute(
                        """INSERT INTO synonym_policy_drafts (
                               synonym_type, editor_text, normalized_policy_json, issues_json,
                               validation_status, base_type_revision_id, revision, updated_at
                           ) VALUES (?, ?, NULL, ?, 'invalid', ?, ?, ?)
                           ON CONFLICT(synonym_type) DO UPDATE SET
                             editor_text=excluded.editor_text,
                             normalized_policy_json=NULL,
                             issues_json=excluded.issues_json,
                             validation_status='invalid',
                             base_type_revision_id=excluded.base_type_revision_id,
                             revision=excluded.revision,
                             updated_at=excluded.updated_at""",
                        (
                            synonym_type,
                            editor_text,
                            json.dumps([issue]),
                            policy["active_type_revision_id"],
                            int(policy["draft_revision"]) + 1,
                            datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        ),
                    )
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            if action == "clear":
                conn.execute(
                    f"DELETE FROM synonym_suggestions WHERE suggestion_id IN ({placeholders})",
                    ids,
                )
            else:
                conn.execute(
                    f"""UPDATE synonym_suggestions SET review_status = ?, policy_effect = ?,
                        decided_at = ?, decided_by = ?, updated_at = ?, revision = revision + 1
                        WHERE suggestion_id IN ({placeholders})""",
                    (
                        "approved" if action == "approve" else "declined",
                        policy_effect if action == "approve" else "absent",
                        now,
                        acted_by,
                        now,
                        *ids,
                    ),
                )
            processing_run_id = _record_synonym_processing_run(
                conn, action=action, total=len(ids),
                approved=len(ids) if action == "approve" else 0,
                declined=len(ids) if action == "decline" else 0,
                pending=0, added=added, issues=issue_count,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return {
        "processing_run_id": processing_run_id,
        "processed_count": len(ids),
        "approved_count": len(ids) if action == "approve" else 0,
        "declined_count": len(ids) if action == "decline" else 0,
        "successfully_added_count": added,
        "issue_count": issue_count,
    }

def query_synonym_processing_runs(
    *, page: int = 1, page_size: int = 20, database_path: Path | None = None
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        total = int(conn.execute("SELECT COUNT(*) FROM synonym_processing_runs").fetchone()[0])
        rows = conn.execute(
            "SELECT * FROM synonym_processing_runs ORDER BY processed_at DESC, processing_run_id DESC LIMIT ? OFFSET ?",
            (page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": total, "page": max(1, page), "page_size": page_size}

def delete_run_synonym_sources(
    run_id: str, *, database_path: Path | None = None
) -> dict[str, int]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        deleted_sources = conn.execute(
            "DELETE FROM synonym_suggestion_sources WHERE run_id = ?", (run_id,)
        ).rowcount
        deleted_suggestions = conn.execute(
            """DELETE FROM synonym_suggestions
               WHERE review_status IN ('pending', 'declined')
                 AND NOT EXISTS (
                   SELECT 1 FROM synonym_suggestion_sources src
                   WHERE src.suggestion_id = synonym_suggestions.suggestion_id
                 )"""
        ).rowcount
        conn.commit()
    return {"deleted_source_count": deleted_sources, "deleted_suggestion_count": deleted_suggestions}


def list_candidate_profiles(
    *, database_path: Path | None = None, active_only: bool = True
) -> list[dict[str, Any]]:
    path = database_path or Path(_local_sqlite_path())
    where = "WHERE cp.creation_status = 'succeeded' AND cp.lifecycle = 'active'" if active_only else ""
    with _sqlite_connection(path) as conn:
        rows = conn.execute(
            f"""
            SELECT cp.candidate_profile_id, cp.profile_name, '',
                   CASE WHEN cp.creation_status = 'succeeded' AND cp.lifecycle = 'active' THEN 1 ELSE 0 END,
                   cp.is_default, cp.updated_at, cp.revision, cp.sort_order,
                   pr.checksum, cp.seed_manifest_revision
            FROM candidate_profiles AS cp
            LEFT JOIN candidate_profile_revisions AS pr
              ON pr.candidate_profile_id = cp.candidate_profile_id
            {where}
            ORDER BY cp.sort_order, cp.profile_name COLLATE NOCASE, cp.candidate_profile_id
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
            """
            SELECT cp.candidate_profile_id, cp.profile_name, pr.profile_json,
                   cp.revision, pr.checksum, pr.profile_revision_id,
                   cp.creation_status, cp.lifecycle,
                   CASE WHEN cp.creation_status = 'succeeded' AND cp.lifecycle = 'active' THEN 1 ELSE 0 END
            FROM candidate_profiles AS cp
            JOIN candidate_profile_revisions AS pr
              ON pr.candidate_profile_id = cp.candidate_profile_id
            WHERE cp.candidate_profile_id = ?
            """,
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
        "profile_revision_id": row[5],
        "creation_status": row[6],
        "lifecycle": row[7],
        "is_active": bool(row[8]),
    }


def _candidate_profile_attempt_resource(conn: sqlite3.Connection, attempt_id: str) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """SELECT a.*, d.original_filename, d.media_type, d.byte_length, d.checksum, d.source_available
           FROM candidate_profile_creation_attempts a
           JOIN candidate_profile_source_documents d ON d.source_document_id = a.source_document_id
           WHERE a.attempt_id = ?""",
        (attempt_id,),
    ).fetchone()
    if row is None:
        return None
    failure = json.loads(row["failure_json"]) if row["failure_json"] else None
    status = str(row["creation_status"])
    return {
        "attempt_id": row["attempt_id"],
        "profile_name": row["profile_name"],
        "creation_status": status,
        "revision": int(row["revision"]),
        "source_document": {
            "source_document_id": row["source_document_id"],
            "original_filename": row["original_filename"],
            "media_type": row["media_type"],
            "byte_length": int(row["byte_length"]),
            "checksum": row["checksum"],
            "source_available": bool(row["source_available"]),
        },
        "processing": {
            "stage": row["processing_stage"],
            "claim_id": row["processing_claim_id"],
            "attempt": int(row["processing_attempt"]),
            "lease_expires_at": row["lease_expires_at"],
        },
        "source_purge_after": row["source_purge_after"],
        "fingerprints": {
            "extraction": row["extraction_fingerprint"],
            "baseline_draft": row["baseline_fingerprint"],
            "approved_baseline": row["approved_baseline_fingerprint"],
            "derived_draft": row["derived_fingerprint"],
            "approved_derived": row["approved_derived_fingerprint"],
            "confirmation": row["confirmation_fingerprint"],
        },
        "failure": failure,
        "next_action": row["next_action"],
        "capabilities": {
            "view_source": bool(row["source_available"]),
            "review_baseline": status == "base_review",
            "approve_baseline": status == "base_review",
            "review_derived": status == "derived_review",
            "approve_derived": status == "derived_review",
            "confirm": status == "ready_to_confirm",
            "retry": status == "failed" and bool(failure and failure.get("retryable")),
        },
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def create_candidate_profile_creation_attempt(
    *, profile_name: str, original_filename: str, media_type: str, content: bytes,
    idempotency_key: str, database_path: Path | None = None,
) -> dict[str, Any]:
    normalized_name = profile_name.strip()
    if not normalized_name:
        raise ValueError("candidate_profile_name_required")
    path = database_path or Path(_local_sqlite_path())
    checksum = hashlib.sha256(content).hexdigest()
    request_fingerprint = hashlib.sha256(json.dumps([normalized_name, original_filename, media_type, checksum], separators=(",", ":")).encode()).hexdigest()
    now = datetime.datetime.now(datetime.timezone.utc)
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        existing = conn.execute("SELECT request_fingerprint, response_json FROM idempotent_actions WHERE action_scope='candidate_profile_create' AND idempotency_key=?", (idempotency_key,)).fetchone()
        if existing is not None:
            if existing["request_fingerprint"] != request_fingerprint:
                raise ValueError("idempotency_conflict")
            return json.loads(existing["response_json"])
        attempt_id = f"attempt_{uuid.uuid4().hex}"
        document_id = f"doc_{checksum[:16]}"
        timestamp = now.isoformat()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """INSERT INTO candidate_profile_creation_attempts
               (attempt_id, profile_name, creation_status, revision, source_document_id, next_action, source_purge_after, created_at, updated_at)
               VALUES (?, ?, 'uploaded', 1, ?, 'process_baseline', ?, ?, ?)""",
            (attempt_id, normalized_name, document_id, (now + datetime.timedelta(days=30)).isoformat(), timestamp, timestamp),
        )
        conn.execute(
            """INSERT INTO candidate_profile_source_documents
               (source_document_id, attempt_id, original_filename, media_type, byte_length, checksum, source_bytes, source_available, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)""",
            (document_id, attempt_id, original_filename, media_type, len(content), checksum, content, timestamp),
        )
        resource = _candidate_profile_attempt_resource(conn, attempt_id)
        assert resource is not None
        conn.execute(
            """INSERT INTO idempotent_actions
               (action_id, action_scope, idempotency_key, request_fingerprint, status, response_json, created_at, updated_at)
               VALUES (?, 'candidate_profile_create', ?, ?, 'succeeded', ?, ?, ?)""",
            (f"action_{uuid.uuid4().hex}", idempotency_key, request_fingerprint, json.dumps(resource), timestamp, timestamp),
        )
        conn.commit()
        return resource


def get_candidate_profile_creation_attempt(attempt_id: str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        return _candidate_profile_attempt_resource(conn, attempt_id)


def query_candidate_profile_creation_attempts(*, database_path: Path | None = None, **_kwargs: Any) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        ids = [str(row[0]) for row in conn.execute("SELECT attempt_id FROM candidate_profile_creation_attempts ORDER BY created_at DESC")]
        items = [_candidate_profile_attempt_resource(conn, attempt_id) for attempt_id in ids]
    return {"items": [item for item in items if item is not None], "total": len(items)}


def get_candidate_profile_source(attempt_id: str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        row = conn.execute("SELECT original_filename, media_type, checksum, source_bytes, source_available FROM candidate_profile_source_documents WHERE attempt_id=?", (attempt_id,)).fetchone()
        if row is None:
            return None
        if not row[4] or row[3] is None:
            raise ValueError("candidate_profile_source_purged")
        return {"filename": row[0], "media_type": row[1], "checksum": row[2], "content": bytes(row[3])}


def get_candidate_profile_source_block(
    attempt_id: str,
    source_block_id: str,
    *,
    database_path: Path | None = None,
) -> dict[str, Any] | None:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        row = conn.execute(
            """
            SELECT source_block_id, text, locator_json, kind, checksum
            FROM candidate_profile_source_blocks
            WHERE attempt_id=? AND source_block_id=?
            """,
            (attempt_id, source_block_id),
        ).fetchone()
    if row is None:
        return None
    return {
        "source_block_id": row[0],
        "text": row[1],
        "locator": json.loads(row[2]),
        "kind": row[3],
        "checksum": row[4],
    }


def _candidate_profile_snapshot_table(stage: str) -> tuple[str, str]:
    if stage == "baseline":
        return "candidate_profile_baseline_snapshots", "baseline_fingerprint"
    if stage == "derived":
        return "candidate_profile_derived_snapshots", "derived_fingerprint"
    raise ValueError("candidate_profile_transition_invalid")


def get_candidate_profile_review(
    attempt_id: str,
    stage: str,
    *,
    database_path: Path | None = None,
) -> dict[str, Any] | None:
    table, fingerprint_column = _candidate_profile_snapshot_table(stage)
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        attempt = conn.execute(
            f"SELECT revision, creation_status, {fingerprint_column} AS fingerprint FROM candidate_profile_creation_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone()
        if attempt is None:
            return None
        if not attempt["fingerprint"]:
            raise ValueError("candidate_profile_invalid_transition")
        snapshot = conn.execute(
            f"SELECT document_json, annotations_json, runtime_evidence_json FROM {table} WHERE attempt_id=? AND fingerprint=?",
            (attempt_id, attempt["fingerprint"]),
        ).fetchone()
    if snapshot is None:
        raise RuntimeError("candidate_profile_snapshot_missing")
    expected_status = "base_review" if stage == "baseline" else "derived_review"
    editable = attempt["creation_status"] == expected_status
    return {
        "attempt_id": attempt_id,
        "stage": stage,
        "revision": int(attempt["revision"]),
        "fingerprint": attempt["fingerprint"],
        "document": json.loads(snapshot["document_json"]),
        "annotations": json.loads(snapshot["annotations_json"]),
        "runtime_evidence": (
            json.loads(snapshot["runtime_evidence_json"])
            if snapshot["runtime_evidence_json"]
            else None
        ),
        "validation": {"field_errors": []},
        "capabilities": {
            "patch": editable,
            "regenerate_all": editable,
            "approve": editable,
        },
    }


def publish_candidate_profile_stage_result(
    attempt_id: str,
    *,
    stage: str,
    claim_id: str,
    expected_revision: int,
    result: dict[str, Any],
    source_blocks: list[dict[str, Any]] | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    table, fingerprint_column = _candidate_profile_snapshot_table(stage)
    processing_stage = "base_mapping" if stage == "baseline" else "derived_claims"
    path = database_path or Path(_local_sqlite_path())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            attempt = conn.execute(
                """
                SELECT revision, processing_stage, processing_claim_id, source_document_id
                FROM candidate_profile_creation_attempts WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise ValueError("candidate_profile_attempt_not_found")
            if int(attempt["revision"]) != expected_revision:
                raise ValueError("candidate_profile_revision_conflict")
            if attempt["processing_stage"] != processing_stage or attempt["processing_claim_id"] != claim_id:
                raise ValueError("candidate_profile_processing_claim_conflict")
            if stage == "baseline":
                for ordinal, block in enumerate(source_blocks or [], start=1):
                    conn.execute(
                        """
                        INSERT INTO candidate_profile_source_blocks (
                            source_block_id, attempt_id, source_document_id, ordinal, kind,
                            locator_json, text, checksum
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            block.get("source_block_id") or block.get("block_id"),
                            attempt_id,
                            attempt["source_document_id"],
                            ordinal,
                            str(block.get("kind") or "text"),
                            json.dumps(block.get("locator") or {}, sort_keys=True, separators=(",", ":")),
                            str(block.get("text") or ""),
                            str(block.get("checksum") or hashlib.sha256(str(block.get("text") or "").encode("utf-8")).hexdigest()),
                        ),
                    )
            snapshot_id = f"snapshot_{uuid.uuid4().hex}"
            values: list[Any] = [
                snapshot_id,
                attempt_id,
            ]
            columns = ["snapshot_id", "attempt_id"]
            if stage == "derived":
                columns.append("baseline_fingerprint")
                values.append(str(result.get("baseline_fingerprint") or ""))
            columns.extend(
                ["fingerprint", "document_json", "annotations_json", "runtime_evidence_json", "created_at"]
            )
            values.extend(
                [
                    str(result["fingerprint"]),
                    json.dumps(result["document"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    json.dumps(result.get("annotations") or {}, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    (
                        json.dumps(result["runtime_evidence"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        if result.get("runtime_evidence") is not None
                        else None
                    ),
                    now,
                ]
            )
            conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
            updates = [
                "creation_status=?",
                "revision=revision+1",
                f"{fingerprint_column}=?",
                "processing_stage=NULL",
                "processing_claim_id=NULL",
                "lease_expires_at=NULL",
                "failure_json=NULL",
                "resume_stage=NULL",
                "next_action=?",
                "updated_at=?",
            ]
            params: list[Any] = [
                "base_review" if stage == "baseline" else "derived_review",
                str(result["fingerprint"]),
                "review_baseline" if stage == "baseline" else "review_derived",
                now,
            ]
            if stage == "baseline":
                extraction_fingerprint = result.get("extraction_fingerprint")
                if extraction_fingerprint is None and source_blocks is not None:
                    extraction_fingerprint = hashlib.sha256(
                        json.dumps(source_blocks, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    ).hexdigest()
                updates.append("extraction_fingerprint=?")
                params.append(extraction_fingerprint)
            params.append(attempt_id)
            conn.execute(
                f"UPDATE candidate_profile_creation_attempts SET {', '.join(updates)} WHERE attempt_id=?",
                params,
            )
            resource = _candidate_profile_attempt_resource(conn, attempt_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    assert resource is not None
    return resource


def _candidate_profile_request_fingerprint(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _candidate_profile_idempotent_replay(
    conn: sqlite3.Connection,
    *,
    scope: str,
    idempotency_key: str,
    request_fingerprint: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        "SELECT request_fingerprint, response_json FROM idempotent_actions WHERE action_scope=? AND idempotency_key=?",
        (scope, idempotency_key),
    ).fetchone()
    if row is None:
        return None
    if row[0] != request_fingerprint:
        raise ValueError("idempotency_conflict")
    return json.loads(row[1])


def _record_candidate_profile_idempotent_result(
    conn: sqlite3.Connection,
    *,
    scope: str,
    idempotency_key: str,
    request_fingerprint: str,
    response: dict[str, Any],
    now: str,
) -> None:
    conn.execute(
        """
        INSERT INTO idempotent_actions (
            action_id, action_scope, idempotency_key, request_fingerprint,
            status, response_json, created_at, updated_at
        ) VALUES (?, ?, ?, ?, 'succeeded', ?, ?, ?)
        """,
        (
            f"action_{uuid.uuid4().hex}",
            scope,
            idempotency_key,
            request_fingerprint,
            json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            now,
            now,
        ),
    )


def _candidate_profile_snapshot(
    conn: sqlite3.Connection,
    attempt_id: str,
    stage: str,
    fingerprint: str,
) -> dict[str, Any]:
    table, _ = _candidate_profile_snapshot_table(stage)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        f"SELECT document_json, annotations_json, runtime_evidence_json, "
        f"{'baseline_fingerprint' if stage == 'derived' else 'NULL AS baseline_fingerprint'} "
        f"FROM {table} WHERE attempt_id=? AND fingerprint=?",
        (attempt_id, fingerprint),
    ).fetchone()
    if row is None:
        raise RuntimeError("candidate_profile_snapshot_missing")
    return {
        "document": json.loads(row["document_json"]),
        "annotations": json.loads(row["annotations_json"]),
        "runtime_evidence": json.loads(row["runtime_evidence_json"]) if row["runtime_evidence_json"] else None,
        "baseline_fingerprint": row["baseline_fingerprint"],
    }


def _candidate_profile_review_resource_in_transaction(
    conn: sqlite3.Connection,
    attempt_id: str,
    stage: str,
) -> dict[str, Any]:
    _, fingerprint_column = _candidate_profile_snapshot_table(stage)
    conn.row_factory = sqlite3.Row
    attempt = conn.execute(
        f"SELECT revision, creation_status, {fingerprint_column} AS fingerprint FROM candidate_profile_creation_attempts WHERE attempt_id=?",
        (attempt_id,),
    ).fetchone()
    if attempt is None:
        raise ValueError("candidate_profile_attempt_not_found")
    snapshot = _candidate_profile_snapshot(conn, attempt_id, stage, str(attempt["fingerprint"] or ""))
    expected_status = "base_review" if stage == "baseline" else "derived_review"
    editable = attempt["creation_status"] == expected_status
    return {
        "attempt_id": attempt_id,
        "stage": stage,
        "revision": int(attempt["revision"]),
        "fingerprint": attempt["fingerprint"],
        "document": snapshot["document"],
        "annotations": snapshot["annotations"],
        "runtime_evidence": snapshot["runtime_evidence"],
        "validation": {"field_errors": []},
        "capabilities": {"patch": editable, "regenerate_all": editable, "approve": editable},
    }


def patch_candidate_profile_review(
    attempt_id: str,
    stage: str,
    *,
    expected_revision: int,
    operations: list[dict[str, Any]],
    idempotency_key: str,
    database_path: Path | None = None,
) -> dict[str, Any]:
    from fitcv_cp.candidate_profile_service import apply_review_operations, approve_review

    table, fingerprint_column = _candidate_profile_snapshot_table(stage)
    scope = f"candidate_profile:{attempt_id}:{stage}:patch"
    request_fingerprint = _candidate_profile_request_fingerprint(
        {"expected_revision": expected_revision, "operations": operations}
    )
    path = database_path or Path(_local_sqlite_path())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            replay = _candidate_profile_idempotent_replay(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                conn.rollback()
                return replay
            attempt = conn.execute(
                f"SELECT revision, creation_status, {fingerprint_column} AS fingerprint FROM candidate_profile_creation_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise ValueError("candidate_profile_attempt_not_found")
            if int(attempt["revision"]) != expected_revision:
                raise ValueError("candidate_profile_revision_conflict")
            if attempt["creation_status"] != ("base_review" if stage == "baseline" else "derived_review"):
                raise ValueError("candidate_profile_invalid_transition")
            current = _candidate_profile_snapshot(conn, attempt_id, stage, str(attempt["fingerprint"]))
            document = apply_review_operations(stage, current["document"], operations)
            approval = approve_review(
                stage,
                document,
                expected_fingerprint=None,
                baseline_fingerprint=current["baseline_fingerprint"],
            )
            fingerprint = str(approval["fingerprint"])
            columns = ["snapshot_id", "attempt_id"]
            values: list[Any] = [f"snapshot_{uuid.uuid4().hex}", attempt_id]
            if stage == "derived":
                columns.append("baseline_fingerprint")
                values.append(current["baseline_fingerprint"])
            columns.extend(
                ["fingerprint", "document_json", "annotations_json", "runtime_evidence_json", "created_at"]
            )
            values.extend(
                [
                    fingerprint,
                    json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    json.dumps(current["annotations"], ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    (
                        json.dumps(current["runtime_evidence"], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                        if current["runtime_evidence"] is not None
                        else None
                    ),
                    now,
                ]
            )
            conn.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                values,
            )
            conn.execute(
                """
                INSERT INTO candidate_profile_review_batches (
                    review_batch_id, attempt_id, stage, expected_revision,
                    operations_json, result_fingerprint, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"review_{uuid.uuid4().hex}",
                    attempt_id,
                    stage,
                    expected_revision,
                    json.dumps(operations, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                    fingerprint,
                    now,
                ),
            )
            if stage == "baseline":
                conn.execute(
                    """
                    UPDATE candidate_profile_creation_attempts
                    SET revision=revision+1, baseline_fingerprint=?, approved_baseline_fingerprint=NULL,
                        derived_fingerprint=NULL, approved_derived_fingerprint=NULL,
                        confirmation_fingerprint=NULL, creation_status='base_review',
                        next_action='review_baseline', updated_at=?
                    WHERE attempt_id=?
                    """,
                    (fingerprint, now, attempt_id),
                )
            else:
                conn.execute(
                    """
                    UPDATE candidate_profile_creation_attempts
                    SET revision=revision+1, derived_fingerprint=?, approved_derived_fingerprint=NULL,
                        confirmation_fingerprint=NULL, creation_status='derived_review',
                        next_action='review_derived', updated_at=?
                    WHERE attempt_id=?
                    """,
                    (fingerprint, now, attempt_id),
                )
            response = _candidate_profile_review_resource_in_transaction(conn, attempt_id, stage)
            _record_candidate_profile_idempotent_result(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response=response,
                now=now,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return response


def regenerate_candidate_profile_review(
    attempt_id: str,
    stage: str,
    *,
    expected_revision: int,
    targets: list[str],
    idempotency_key: str,
    database_path: Path | None = None,
) -> dict[str, Any]:
    from fitcv_cp.candidate_profile_service import resolve_regeneration_targets

    _, fingerprint_column = _candidate_profile_snapshot_table(stage)
    scope = f"candidate_profile:{attempt_id}:{stage}:regenerate"
    request_fingerprint = _candidate_profile_request_fingerprint(
        {"expected_revision": expected_revision, "targets": targets}
    )
    path = database_path or Path(_local_sqlite_path())
    current = datetime.datetime.now(datetime.timezone.utc)
    now = current.isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            replay = _candidate_profile_idempotent_replay(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                conn.rollback()
                return replay
            attempt = conn.execute(
                f"SELECT revision, creation_status, {fingerprint_column} AS fingerprint FROM candidate_profile_creation_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise ValueError("candidate_profile_attempt_not_found")
            if int(attempt["revision"]) != expected_revision:
                raise ValueError("candidate_profile_revision_conflict")
            if attempt["creation_status"] != ("base_review" if stage == "baseline" else "derived_review"):
                raise ValueError("candidate_profile_invalid_transition")
            snapshot = _candidate_profile_snapshot(conn, attempt_id, stage, str(attempt["fingerprint"]))
            resolved_targets = resolve_regeneration_targets(snapshot["annotations"], targets)
            processing_stage = "base_mapping" if stage == "baseline" else "derived_claims"
            conn.execute(
                """
                INSERT INTO candidate_profile_review_batches (
                    review_batch_id, attempt_id, stage, expected_revision,
                    operations_json, result_fingerprint, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    f"review_{uuid.uuid4().hex}",
                    attempt_id,
                    stage,
                    expected_revision,
                    json.dumps(
                        {"regeneration_targets": list(resolved_targets)},
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    attempt["fingerprint"],
                    now,
                ),
            )
            conn.execute(
                """
                UPDATE candidate_profile_creation_attempts
                SET creation_status=?, revision=revision+1, processing_stage=?,
                    processing_claim_id=?, processing_attempt=processing_attempt+1,
                    lease_expires_at=?, next_action='wait', updated_at=?
                WHERE attempt_id=?
                """,
                (
                    "extracting_base" if stage == "baseline" else "deriving",
                    processing_stage,
                    f"claim_{uuid.uuid4().hex}",
                    (current + datetime.timedelta(seconds=_CANDIDATE_PROFILE_LEASE_SECONDS)).isoformat(),
                    now,
                    attempt_id,
                ),
            )
            response = _candidate_profile_attempt_resource(conn, attempt_id)
            assert response is not None
            _record_candidate_profile_idempotent_result(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response=response,
                now=now,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return response


def approve_candidate_profile_review(
    attempt_id: str,
    stage: str,
    *,
    expected_revision: int,
    expected_fingerprint: str,
    idempotency_key: str,
    expected_baseline_fingerprint: str | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    _, fingerprint_column = _candidate_profile_snapshot_table(stage)
    scope = f"candidate_profile:{attempt_id}:{stage}:approve"
    request_fingerprint = _candidate_profile_request_fingerprint(
        {
            "expected_revision": expected_revision,
            "expected_fingerprint": expected_fingerprint,
            "expected_baseline_fingerprint": expected_baseline_fingerprint,
        }
    )
    path = database_path or Path(_local_sqlite_path())
    current = datetime.datetime.now(datetime.timezone.utc)
    now = current.isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            replay = _candidate_profile_idempotent_replay(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                conn.rollback()
                return replay
            attempt = conn.execute(
                f"SELECT revision, creation_status, {fingerprint_column} AS fingerprint, approved_baseline_fingerprint FROM candidate_profile_creation_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise ValueError("candidate_profile_attempt_not_found")
            if int(attempt["revision"]) != expected_revision:
                raise ValueError("candidate_profile_revision_conflict")
            if attempt["creation_status"] != ("base_review" if stage == "baseline" else "derived_review"):
                raise ValueError("candidate_profile_invalid_transition")
            if attempt["fingerprint"] != expected_fingerprint:
                raise ValueError("candidate_profile_fingerprint_conflict")
            if stage == "derived" and attempt["approved_baseline_fingerprint"] != expected_baseline_fingerprint:
                raise ValueError("candidate_profile_fingerprint_conflict")
            if stage == "baseline":
                conn.execute(
                    """
                    UPDATE candidate_profile_creation_attempts
                    SET revision=revision+1, approved_baseline_fingerprint=?,
                        creation_status='deriving', processing_stage='derived_claims',
                        processing_claim_id=?, processing_attempt=processing_attempt+1,
                        lease_expires_at=?, next_action='wait', updated_at=?
                    WHERE attempt_id=?
                    """,
                    (
                        expected_fingerprint,
                        f"claim_{uuid.uuid4().hex}",
                        (current + datetime.timedelta(seconds=_CANDIDATE_PROFILE_LEASE_SECONDS)).isoformat(),
                        now,
                        attempt_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    UPDATE candidate_profile_creation_attempts
                    SET revision=revision+1, approved_derived_fingerprint=?,
                        creation_status='ready_to_confirm', confirmation_fingerprint=NULL,
                        next_action='confirm', updated_at=?
                    WHERE attempt_id=?
                    """,
                    (expected_fingerprint, now, attempt_id),
                )
            response = _candidate_profile_attempt_resource(conn, attempt_id)
            assert response is not None
            _record_candidate_profile_idempotent_result(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response=response,
                now=now,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return response


def _candidate_profile_confirmation_in_transaction(
    conn: sqlite3.Connection,
    attempt_id: str,
) -> dict[str, Any]:
    from fitcv_cp.candidate_profile_service import assemble_confirmation

    conn.row_factory = sqlite3.Row
    attempt = conn.execute(
        """
        SELECT profile_name, revision, creation_status,
               approved_baseline_fingerprint, approved_derived_fingerprint
        FROM candidate_profile_creation_attempts WHERE attempt_id=?
        """,
        (attempt_id,),
    ).fetchone()
    if attempt is None:
        raise ValueError("candidate_profile_attempt_not_found")
    if attempt["creation_status"] not in {"ready_to_confirm", "succeeded"}:
        raise ValueError("candidate_profile_invalid_transition")
    baseline_fingerprint = str(attempt["approved_baseline_fingerprint"] or "")
    derived_fingerprint = str(attempt["approved_derived_fingerprint"] or "")
    if not baseline_fingerprint or not derived_fingerprint:
        raise ValueError("candidate_profile_invalid_transition")
    baseline = _candidate_profile_snapshot(conn, attempt_id, "baseline", baseline_fingerprint)
    derived = _candidate_profile_snapshot(conn, attempt_id, "derived", derived_fingerprint)
    confirmation = assemble_confirmation(
        str(attempt["profile_name"]),
        {"stage": "baseline", "document": baseline["document"], "fingerprint": baseline_fingerprint},
        {
            "stage": "derived",
            "document": derived["document"],
            "fingerprint": derived_fingerprint,
            "baseline_fingerprint": derived["baseline_fingerprint"],
        },
    )
    return {"attempt_id": attempt_id, "revision": int(attempt["revision"]), **confirmation}


def get_candidate_profile_confirmation(
    attempt_id: str,
    *,
    database_path: Path | None = None,
) -> dict[str, Any] | None:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        if conn.execute(
            "SELECT 1 FROM candidate_profile_creation_attempts WHERE attempt_id=?",
            (attempt_id,),
        ).fetchone() is None:
            return None
        return _candidate_profile_confirmation_in_transaction(conn, attempt_id)


def _insert_confirmed_candidate_profile(
    conn: sqlite3.Connection,
    *,
    attempt_id: str,
    confirmation: dict[str, Any],
    now: str,
) -> str:
    conn.row_factory = sqlite3.Row
    source = conn.execute(
        """
        SELECT a.profile_name, d.original_filename, d.media_type, d.byte_length, d.checksum
        FROM candidate_profile_creation_attempts a
        JOIN candidate_profile_source_documents d ON d.attempt_id=a.attempt_id
        WHERE a.attempt_id=?
        """,
        (attempt_id,),
    ).fetchone()
    if source is None:
        raise ValueError("candidate_profile_attempt_not_found")
    profile_id = f"profile_{uuid.uuid4().hex}"
    profile_revision_id = f"profile_revision_{uuid.uuid4().hex}"
    canonical = confirmation["profile"]["canonical"]
    conn.execute(
        """
        INSERT INTO candidate_profiles (
            candidate_profile_id, profile_name, original_filename, media_type, byte_length,
            input_checksum, creation_status, lifecycle, failure_code, failure_message,
            is_default, sort_order, seed_manifest_revision, created_at, updated_at,
            archived_at, revision
        ) VALUES (?, ?, ?, ?, ?, ?, 'succeeded', 'active', NULL, NULL, 0, 0, NULL, ?, ?, NULL, 1)
        """,
        (
            profile_id,
            source["profile_name"],
            source["original_filename"],
            source["media_type"],
            source["byte_length"],
            source["checksum"],
            now,
            now,
        ),
    )
    conn.execute(
        """
        INSERT INTO candidate_profile_revisions (
            profile_revision_id, candidate_profile_id, revision, profile_json,
            checksum, schema_revision, created_at
        ) VALUES (?, ?, 1, ?, ?, ?, ?)
        """,
        (
            profile_revision_id,
            profile_id,
            json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
            confirmation["profile"]["checksum"],
            confirmation["profile"]["schema_version"],
            now,
        ),
    )
    return profile_id


def confirm_candidate_profile_creation_attempt(
    attempt_id: str,
    *,
    expected_revision: int,
    expected_baseline_fingerprint: str,
    expected_derived_fingerprint: str,
    expected_confirmation_fingerprint: str,
    idempotency_key: str,
    database_path: Path | None = None,
) -> dict[str, Any]:
    request_fingerprint = _candidate_profile_request_fingerprint(
        {
            "attempt_id": attempt_id,
            "expected_baseline_fingerprint": expected_baseline_fingerprint,
            "expected_derived_fingerprint": expected_derived_fingerprint,
            "expected_confirmation_fingerprint": expected_confirmation_fingerprint,
        }
    )
    scope = f"candidate_profile:{attempt_id}:confirm"
    path = database_path or Path(_local_sqlite_path())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            replay = _candidate_profile_idempotent_replay(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                conn.rollback()
                return replay
            attempt = conn.execute(
                "SELECT revision, profile_id FROM candidate_profile_creation_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise ValueError("candidate_profile_attempt_not_found")
            confirmation = _candidate_profile_confirmation_in_transaction(conn, attempt_id)
            if confirmation["approval_fingerprints"]["baseline"] != expected_baseline_fingerprint:
                raise ValueError("candidate_profile_fingerprint_conflict")
            if confirmation["approval_fingerprints"]["derived"] != expected_derived_fingerprint:
                raise ValueError("candidate_profile_fingerprint_conflict")
            if confirmation["fingerprint"] != expected_confirmation_fingerprint:
                raise ValueError("candidate_profile_fingerprint_conflict")
            if attempt["profile_id"]:
                response = _candidate_profile_resource(conn, str(attempt["profile_id"]))
                assert response is not None
            else:
                if int(attempt["revision"]) != expected_revision:
                    raise ValueError("candidate_profile_revision_conflict")
                profile_id = _insert_confirmed_candidate_profile(
                    conn,
                    attempt_id=attempt_id,
                    confirmation=confirmation,
                    now=now,
                )
                conn.execute(
                    """
                    UPDATE candidate_profile_creation_attempts
                    SET creation_status='succeeded', revision=revision+1, profile_id=?,
                        confirmation_fingerprint=?, next_action='view_profile', updated_at=?
                    WHERE attempt_id=?
                    """,
                    (profile_id, confirmation["fingerprint"], now, attempt_id),
                )
                response = _candidate_profile_resource(conn, profile_id)
                assert response is not None
            _record_candidate_profile_idempotent_result(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response=response,
                now=now,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return response


def retry_candidate_profile_creation_attempt(
    attempt_id: str,
    *,
    expected_revision: int,
    idempotency_key: str,
    database_path: Path | None = None,
) -> dict[str, Any]:
    scope = f"candidate_profile:{attempt_id}:retry"
    request_fingerprint = _candidate_profile_request_fingerprint(
        {"expected_revision": expected_revision}
    )
    path = database_path or Path(_local_sqlite_path())
    current = datetime.datetime.now(datetime.timezone.utc)
    now = current.isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            replay = _candidate_profile_idempotent_replay(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
            )
            if replay is not None:
                conn.rollback()
                return replay
            attempt = conn.execute(
                """
                SELECT revision, creation_status, failure_json, resume_stage
                FROM candidate_profile_creation_attempts WHERE attempt_id=?
                """,
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise ValueError("candidate_profile_attempt_not_found")
            if int(attempt["revision"]) != expected_revision:
                raise ValueError("candidate_profile_revision_conflict")
            failure = json.loads(attempt["failure_json"]) if attempt["failure_json"] else {}
            stage = str(attempt["resume_stage"] or "")
            if attempt["creation_status"] != "failed" or not failure.get("retryable"):
                raise ValueError("candidate_profile_invalid_transition")
            if stage not in {"base_mapping", "derived_claims"}:
                raise ValueError("candidate_profile_invalid_transition")
            conn.execute(
                """
                UPDATE candidate_profile_creation_attempts
                SET creation_status=?, revision=revision+1, processing_stage=?,
                    processing_claim_id=?, processing_attempt=processing_attempt+1,
                    lease_expires_at=?, failure_json=NULL, resume_stage=NULL,
                    next_action='wait', updated_at=?
                WHERE attempt_id=?
                """,
                (
                    "extracting_base" if stage == "base_mapping" else "deriving",
                    stage,
                    f"claim_{uuid.uuid4().hex}",
                    (current + datetime.timedelta(seconds=_CANDIDATE_PROFILE_LEASE_SECONDS)).isoformat(),
                    now,
                    attempt_id,
                ),
            )
            response = _candidate_profile_attempt_resource(conn, attempt_id)
            assert response is not None
            _record_candidate_profile_idempotent_result(
                conn,
                scope=scope,
                idempotency_key=idempotency_key,
                request_fingerprint=request_fingerprint,
                response=response,
                now=now,
            )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    return response


def claim_candidate_profile_processing(
    attempt_id: str, *, stage: str, expected_revision: int, lease_seconds: int,
    database_path: Path | None = None,
) -> dict[str, Any]:
    if stage not in {"base_mapping", "derived_claims"}:
        raise ValueError("candidate_profile_transition_invalid")
    path = database_path or Path(_local_sqlite_path())
    now = datetime.datetime.now(datetime.timezone.utc)
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT revision FROM candidate_profile_creation_attempts WHERE attempt_id=?", (attempt_id,)).fetchone()
        if row is None:
            raise ValueError("candidate_profile_attempt_not_found")
        if int(row[0]) != expected_revision:
            raise ValueError("candidate_profile_revision_conflict")
        conn.execute(
            """UPDATE candidate_profile_creation_attempts
               SET creation_status=?, revision=revision+1, processing_stage=?, processing_claim_id=?,
                   processing_attempt=processing_attempt+1, lease_expires_at=?, next_action='wait', updated_at=?
               WHERE attempt_id=?""",
            (
                "extracting_base" if stage == "base_mapping" else "deriving", stage,
                f"claim_{uuid.uuid4().hex}", (now + datetime.timedelta(seconds=lease_seconds)).isoformat(),
                now.isoformat(), attempt_id,
            ),
        )
        resource = _candidate_profile_attempt_resource(conn, attempt_id)
        conn.commit()
    assert resource is not None
    return resource


def fail_candidate_profile_stage(
    attempt_id: str,
    *,
    claim_id: str,
    expected_revision: int,
    code: str,
    message: str,
    retryable: bool,
    stage: str,
    database_path: Path | None = None,
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            attempt = conn.execute(
                "SELECT revision, processing_claim_id, processing_stage FROM candidate_profile_creation_attempts WHERE attempt_id=?",
                (attempt_id,),
            ).fetchone()
            if attempt is None:
                raise ValueError("candidate_profile_attempt_not_found")
            if int(attempt["revision"]) != expected_revision:
                raise ValueError("candidate_profile_revision_conflict")
            if attempt["processing_claim_id"] != claim_id or attempt["processing_stage"] != stage:
                raise ValueError("candidate_profile_processing_claim_conflict")
            failure = {
                "code": code,
                "message": message,
                "retryable": bool(retryable),
                "stage": stage,
            }
            conn.execute(
                """
                UPDATE candidate_profile_creation_attempts
                SET creation_status='failed', revision=revision+1, failure_json=?,
                    resume_stage=?, processing_stage=NULL, processing_claim_id=NULL,
                    lease_expires_at=NULL, next_action=?, updated_at=?
                WHERE attempt_id=?
                """,
                (
                    json.dumps(failure, sort_keys=True, separators=(",", ":")),
                    stage if retryable else None,
                    "retry" if retryable else "new_upload",
                    now,
                    attempt_id,
                ),
            )
            resource = _candidate_profile_attempt_resource(conn, attempt_id)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    assert resource is not None
    return resource


def reconcile_candidate_profile_attempts(
    *, now: datetime.datetime | None = None, database_path: Path | None = None
) -> dict[str, int]:
    current = now or datetime.datetime.now(datetime.timezone.utc)
    path = database_path or Path(_local_sqlite_path())
    abandoned = 0
    purged = 0
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        expired_claims = conn.execute(
            """SELECT attempt_id, processing_stage FROM candidate_profile_creation_attempts
               WHERE processing_claim_id IS NOT NULL AND lease_expires_at < ?
                 AND creation_status IN ('extracting_base', 'deriving')""",
            (current.isoformat(),),
        ).fetchall()
        for attempt_id, stage in expired_claims:
            failure = {
                "code": "candidate_profile_processing_abandoned",
                "message": "Processing lease expired.",
                "retryable": True,
                "stage": stage,
            }
            conn.execute(
                """UPDATE candidate_profile_creation_attempts
                   SET creation_status='failed', revision=revision+1, failure_json=?, resume_stage=?,
                       processing_stage=NULL, processing_claim_id=NULL, lease_expires_at=NULL,
                       next_action='retry', updated_at=? WHERE attempt_id=?""",
                (json.dumps(failure), stage, current.isoformat(), attempt_id),
            )
            abandoned += 1
        expired_sources = conn.execute(
            """SELECT a.attempt_id FROM candidate_profile_creation_attempts a
               JOIN candidate_profile_source_documents d ON d.attempt_id=a.attempt_id
               WHERE a.source_purge_after < ? AND a.creation_status != 'succeeded' AND d.source_available=1""",
            (current.isoformat(),),
        ).fetchall()
        for (attempt_id,) in expired_sources:
            conn.execute("DELETE FROM candidate_profile_source_blocks WHERE attempt_id=?", (attempt_id,))
            conn.execute("DELETE FROM candidate_profile_review_batches WHERE attempt_id=?", (attempt_id,))
            conn.execute("DELETE FROM candidate_profile_baseline_snapshots WHERE attempt_id=?", (attempt_id,))
            conn.execute("DELETE FROM candidate_profile_derived_snapshots WHERE attempt_id=?", (attempt_id,))
            conn.execute(
                "UPDATE candidate_profile_source_documents SET source_bytes=NULL, source_available=0, purged_at=? WHERE attempt_id=?",
                (current.isoformat(), attempt_id),
            )
            failure = {
                "code": "candidate_profile_source_expired",
                "message": "Inactive Candidate Profile source expired.",
                "retryable": False,
                "stage": "source_retention",
            }
            conn.execute(
                """UPDATE candidate_profile_creation_attempts
                   SET creation_status='failed', revision=revision+1, failure_json=?, resume_stage=NULL,
                       next_action='new_upload', updated_at=? WHERE attempt_id=?""",
                (json.dumps(failure), current.isoformat(), attempt_id),
            )
            purged += 1
        conn.commit()
    return {"abandoned": abandoned, "purged": purged}


def _candidate_profile_resource(conn: sqlite3.Connection, profile_id: str) -> dict[str, Any] | None:
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        """
        SELECT cp.*, pr.profile_revision_id, pr.revision AS profile_revision,
               pr.profile_json, pr.checksum AS profile_checksum, pr.schema_revision
        FROM candidate_profiles AS cp
        LEFT JOIN candidate_profile_revisions AS pr
          ON pr.candidate_profile_id = cp.candidate_profile_id
        WHERE cp.candidate_profile_id = ?
        """,
        (profile_id,),
    ).fetchone()
    if row is None:
        return None
    profile = json.loads(row["profile_json"]) if row["profile_json"] else None
    display_name = row["profile_name"] or Path(row["original_filename"]).stem or "Unnamed profile"
    succeeded = row["creation_status"] == "succeeded"
    active = row["lifecycle"] == "active"
    related_run_count = int(
        conn.execute(
            "SELECT COUNT(*) FROM run_inputs WHERE candidate_profile_id = ?", (profile_id,)
        ).fetchone()[0]
    )
    attempt_row = conn.execute(
        "SELECT attempt_id FROM candidate_profile_creation_attempts WHERE profile_id=?",
        (profile_id,),
    ).fetchone()
    attempt_id = str(attempt_row[0]) if attempt_row is not None else None
    return {
        "profile_id": row["candidate_profile_id"],
        "profile_name": row["profile_name"],
        "display_name": display_name,
        "original_filename": row["original_filename"],
        "creation": {
            "attempt_id": attempt_id,
            "source_format": Path(row["original_filename"]).suffix.lstrip(".").upper() or "YAML",
            "method": "staged-hybrid" if attempt_id else "legacy",
        },
        "creation_status": row["creation_status"],
        "lifecycle": row["lifecycle"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "archived_at": row["archived_at"],
        "profile_revision_id": row["profile_revision_id"],
        "failure": (
            {"code": row["failure_code"], "message": row["failure_message"]}
            if row["failure_code"]
            else None
        ),
        "related_run_count": related_run_count,
        "capabilities": {
            "inspect": True,
            "archive": succeeded and active,
            "restore": succeeded and not active,
            "use_for_run": succeeded and active,
        },
        "revision": row["revision"],
        "overview": profile,
        "input": {
            "original_filename": row["original_filename"],
            "checksum": row["input_checksum"],
            "byte_length": row["byte_length"],
            "media_type": row["media_type"],
        },
        "profile": (
            {
                "profile_revision_id": row["profile_revision_id"],
                "revision": int(row["profile_revision"]),
                "checksum": row["profile_checksum"],
                "schema_version": row["schema_revision"],
                "canonical": profile,
            }
            if profile is not None
            else None
        ),
    }


def create_candidate_profile_attempt(
    *,
    profile_bytes: bytes,
    original_filename: str,
    profile_name: str | None,
    media_type: str = "application/yaml",
    database_path: Path | None = None,
) -> dict[str, Any]:
    safe_filename = Path(str(original_filename or "").replace("\\", "/")).name
    if not safe_filename.lower().endswith(".yaml"):
        raise ValueError("profile_file_type_invalid")
    if not profile_bytes:
        raise ValueError("profile_file_empty")
    if len(profile_bytes) > _CANDIDATE_PROFILE_MAX_BYTES:
        raise ValueError("profile_file_too_large")
    normalized_name = str(profile_name or "").strip() or None
    if normalized_name is not None and len(normalized_name) > 120:
        raise ValueError("profile_name_too_long")

    profile_id = f"profile-{uuid.uuid4().hex}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    input_checksum = hashlib.sha256(profile_bytes).hexdigest()
    failure_code: str | None = None
    failure_message: str | None = None
    profile: dict[str, Any] | None = None
    try:
        raw_text = profile_bytes.decode("utf-8")
        from fitcv.candidate import load_profile_text

        profile = load_profile_text(raw_text, format_hint="yaml")
    except UnicodeDecodeError:
        failure_code, failure_message = "invalid_utf8", "Profile file must use UTF-8 encoding."
    except ValueError as exc:
        failure_code = "invalid_yaml" if "Invalid YAML" in str(exc) else "invalid_profile"
        failure_message = "Profile YAML is invalid." if failure_code == "invalid_yaml" else "Candidate profile validation failed."
    except Exception:
        failure_code = "profile_processing_failed"
        failure_message = "Candidate profile could not be processed."

    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO candidate_profiles (
                candidate_profile_id, profile_name, original_filename, media_type, byte_length,
                input_checksum, creation_status, lifecycle, failure_code, failure_message,
                is_default, sort_order, created_at, updated_at, archived_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, 0, 0, ?, ?, NULL, 1)
            """,
            (
                profile_id,
                normalized_name,
                safe_filename,
                media_type,
                len(profile_bytes),
                input_checksum,
                "succeeded" if profile is not None else "failed",
                failure_code,
                failure_message,
                now,
                now,
            ),
        )
        if profile is not None:
            profile_json = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            conn.execute(
                """
                INSERT INTO candidate_profile_revisions (
                    profile_revision_id, candidate_profile_id, revision, profile_json,
                    checksum, schema_revision, created_at
                ) VALUES (?, ?, 1, ?, ?, 'candidate-profile.v1', ?)
                """,
                (
                    f"profile-revision-{uuid.uuid4().hex}",
                    profile_id,
                    profile_json,
                    hashlib.sha256(profile_json.encode("utf-8")).hexdigest(),
                    now,
                ),
            )
        conn.commit()
        resource = _candidate_profile_resource(conn, profile_id)
    assert resource is not None
    return resource


def get_candidate_profile_detail(
    profile_id: str, *, database_path: Path | None = None
) -> dict[str, Any] | None:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        return _candidate_profile_resource(conn, profile_id)


def query_candidate_profiles(
    *,
    view: str = "active",
    status: str | None = None,
    search: str = "",
    page: int = 1,
    page_size: int = 20,
    sort: str = "created_desc",
    database_path: Path | None = None,
) -> dict[str, Any]:
    if view not in {"active", "archived"}:
        raise ValueError("profile_view_invalid")
    if status not in {None, "succeeded", "failed"}:
        raise ValueError("profile_status_invalid")
    if page_size not in {10, 20, 50}:
        raise ValueError("page_size must be 10, 20, or 50")
    if sort != "created_desc":
        raise ValueError("profile_sort_invalid")
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        params: list[Any] = [view]
        where = ["lifecycle = ?"]
        if status:
            where.append("creation_status = ?")
            params.append(status)
        normalized_search = search.strip().casefold()
        if normalized_search:
            where.append("lower(candidate_profile_id || ' ' || coalesce(profile_name, '') || ' ' || original_filename) LIKE ?")
            params.append(f"%{normalized_search}%")
        clause = " AND ".join(where)
        total = int(conn.execute(f"SELECT COUNT(*) FROM candidate_profiles WHERE {clause}", params).fetchone()[0])
        ids = conn.execute(
            f"""
            SELECT candidate_profile_id FROM candidate_profiles
            WHERE {clause}
            ORDER BY created_at DESC, candidate_profile_id DESC
            LIMIT ? OFFSET ?
            """,
            (*params, page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
        counts = conn.execute(
            "SELECT SUM(lifecycle = 'active'), SUM(lifecycle = 'archived') FROM candidate_profiles"
        ).fetchone()
        items = [_candidate_profile_resource(conn, str(row[0])) for row in ids]
    return {
        "items": [item for item in items if item is not None],
        "total": total,
        "active_count": int(counts[0] or 0),
        "archived_count": int(counts[1] or 0),
        "page": max(1, page),
        "page_size": page_size,
    }


def transition_candidate_profile_lifecycle(
    profile_id: str,
    *,
    lifecycle: str,
    expected_revision: int,
    database_path: Path | None = None,
) -> dict[str, Any]:
    if lifecycle not in {"active", "archived"}:
        raise ValueError("profile_lifecycle_invalid")
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT creation_status, lifecycle, revision FROM candidate_profiles WHERE candidate_profile_id = ?",
            (profile_id,),
        ).fetchone()
        if row is None:
            raise ValueError("profile_not_found")
        if int(row["revision"]) != expected_revision:
            raise ValueError("revision_conflict")
        if row["creation_status"] != "succeeded":
            raise ValueError("profile_transition_unavailable")
        if row["lifecycle"] != lifecycle:
            now = datetime.datetime.now(datetime.timezone.utc).isoformat()
            conn.execute(
                """
                UPDATE candidate_profiles
                SET lifecycle = ?, archived_at = ?, updated_at = ?, revision = revision + 1
                WHERE candidate_profile_id = ?
                """,
                (lifecycle, now if lifecycle == "archived" else None, now, profile_id),
            )
            conn.commit()
        resource = _candidate_profile_resource(conn, profile_id)
    assert resource is not None
    return resource


def query_candidate_profile_runs(
    profile_id: str,
    *,
    page: int = 1,
    page_size: int = 20,
    database_path: Path | None = None,
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        total = int(
            conn.execute(
                "SELECT COUNT(*) FROM run_inputs WHERE candidate_profile_id = ?", (profile_id,)
            ).fetchone()[0]
        )
        rows = conn.execute(
            """
            SELECT r.run_id, r.run_name, r.backend_status, r.created_at
            FROM run_inputs AS i
            JOIN pipeline_runs AS r ON r.run_id = i.run_id
            WHERE i.candidate_profile_id = ?
            ORDER BY r.created_at DESC, r.run_id DESC
            LIMIT ? OFFSET ?
            """,
            (profile_id, page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": total, "page": max(1, page), "page_size": page_size}


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


@contextmanager
def _provider_store_connection(database_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        yield conn

@contextmanager
def _scan_store_connection(database_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        yield conn

def _scan_resource(conn: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
    input_row = conn.execute("SELECT * FROM scan_inputs WHERE scan_id = ?", (row["scan_id"],)).fetchone()
    output_row = conn.execute("SELECT * FROM scan_outputs WHERE scan_id = ?", (row["scan_id"],)).fetchone()
    referenced_count = int(conn.execute("SELECT COUNT(*) FROM run_scan_inputs WHERE scan_id = ?", (row["scan_id"],)).fetchone()[0])
    integrity_valid = False
    output_manifest = None
    if output_row is not None:
        raw = str(output_row["output_json"]).encode("utf-8")
        digest = hashlib.sha256(raw).hexdigest()
        integrity_valid = digest == str(output_row["sha256"]) and len(raw) == int(output_row["byte_length"])
        output_manifest = {
            "sha256": str(output_row["sha256"]),
            "byte_length": int(output_row["byte_length"]),
            "record_count": int(output_row["record_count"]),
        }
    capabilities = derive_scan_capabilities(
        execution_status=str(row["execution_status"]),
        lifecycle=str(row["lifecycle"]),
        output_manifest_exists=output_row is not None,
        output_integrity_valid=integrity_valid,
        output_record_count=int(output_row["record_count"]) if output_row is not None else None,
        cancellation_requested=row["cancel_requested_at"] is not None,
        referenced_by_run=referenced_count > 0,
    ).model_dump()
    logical_input = json.loads(str(input_row["input_json"])) if input_row is not None else {}
    companies = json.loads(str(input_row["company_snapshots_json"])) if input_row is not None else []
    return {
        "scan_id": str(row["scan_id"]),
        "scan_name": str(row["scan_name"]),
        "execution_status": str(row["execution_status"]),
        "lifecycle": str(row["lifecycle"]),
        "row_revision": int(row["row_revision"]),
        "created_at": str(row["created_at"]),
        "started_at": row["started_at"],
        "finished_at": row["finished_at"],
        "archived_at": row["archived_at"],
        "cancel_requested_at": row["cancel_requested_at"],
        "rerun_of_scan_id": row["rerun_of_scan_id"],
        "failure_code": row["failure_code"],
        "failure_message": row["failure_message"],
        "progress_completed": int(row["progress_completed"]),
        "progress_total": int(row["progress_total"]),
        "company_count": len(companies),
        "company_snapshots": companies,
        "input": logical_input,
        "publication_cutoff": input_row["publication_cutoff"] if input_row is not None else None,
        "output_record_count": int(output_row["record_count"]) if output_row is not None else None,
        "output_integrity_valid": integrity_valid,
        "output_manifest": output_manifest,
        "referenced_by_run": referenced_count > 0,
        "warnings": [],
        "capabilities": capabilities,
    }

def query_tracked_companies(
    *, search: str = "", page: int = 1, page_size: int = 20, database_path: Path | None = None
) -> dict[str, Any]:
    if page_size not in {10, 20, 50, 100}:
        raise ValueError("page_size_invalid")
    needle = f"%{search.strip()}%"
    where = "WHERE is_active = 1 AND is_scannable = 1"
    params: list[Any] = []
    if search.strip():
        where += " AND (company_name LIKE ? COLLATE NOCASE OR provider_id LIKE ? COLLATE NOCASE OR careers_url LIKE ? COLLATE NOCASE)"
        params.extend([needle, needle, needle])
    with _scan_store_connection(database_path) as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM tracked_companies {where}", params).fetchone()[0])
        rows = conn.execute(
            f"SELECT * FROM tracked_companies {where} ORDER BY company_name COLLATE NOCASE, company_id LIMIT ? OFFSET ?",
            (*params, page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
    return {"items": [dict(row) for row in rows], "total": total}

def create_tracked_company(
    *, company_name: str, careers_url: str, provider_id: str, provider_label: str | None = None,
    database_path: Path | None = None, **_extra: Any,
) -> dict[str, Any]:
    company_id = f"company-{uuid.uuid4().hex[:12]}"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with _scan_store_connection(database_path) as conn:
            conn.execute(
                "INSERT INTO tracked_companies VALUES (?, ?, ?, ?, ?, 1, 1, 1, ?, ?)",
                (company_id, company_name.strip(), careers_url.strip(), provider_id.strip(), provider_label, now, now),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM tracked_companies WHERE company_id = ?", (company_id,)).fetchone()
    except sqlite3.IntegrityError as exc:
        if "careers_url" in str(exc).lower() or "unique" in str(exc).lower():
            raise ValueError("tracked_company_url_conflict") from exc
        raise
    return dict(row)

def create_scan(
    *, request: dict[str, Any], rerun_of_scan_id: str | None = None,
    idempotency_action_id: str | None = None, database_path: Path | None = None,
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        _ensure_control_plane_schema(conn)
        conn.row_factory = sqlite3.Row
        conn.execute("BEGIN IMMEDIATE")
        try:
            if idempotency_action_id:
                action = conn.execute("SELECT * FROM idempotent_actions WHERE action_id = ?", (idempotency_action_id,)).fetchone()
                if action is None:
                    raise ValueError("idempotency_action_not_found")
                response = json.loads(action["response_json"]) if action["response_json"] else None
                if isinstance(response, dict) and response.get("scan_id"):
                    existing = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (response["scan_id"],)).fetchone()
                    if existing is not None:
                        conn.rollback()
                        return _scan_resource(conn, existing)
            company_ids = list(request.get("company_ids") or [])
            placeholders = ",".join("?" for _ in company_ids)
            rows = conn.execute(
                f"SELECT * FROM tracked_companies WHERE company_id IN ({placeholders}) AND is_active = 1 AND is_scannable = 1",
                company_ids,
            ).fetchall() if company_ids else []
            by_id = {str(row["company_id"]): row for row in rows}
            if len(by_id) != len(company_ids):
                raise ValueError("tracked_company_unavailable")
            companies = [dict(by_id[company_id]) for company_id in company_ids]
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            now = now_dt.isoformat()
            scan_id = f"scan-{uuid.uuid4().hex[:12]}"
            scan_name = str(request.get("scan_name") or f"Scan {scan_id[5:]}")
            cutoff = resolve_publication_cutoff(str(request.get("published_window") or "any"), now_dt)
            conn.execute(
                "INSERT INTO scans (scan_id, scan_name, execution_status, lifecycle, created_at, rerun_of_scan_id) VALUES (?, ?, 'queued', 'active', ?, ?)",
                (scan_id, scan_name, now, rerun_of_scan_id),
            )
            conn.execute(
                "INSERT INTO scan_inputs VALUES (?, ?, ?, ?, ?)",
                (scan_id, json.dumps(request, ensure_ascii=False, separators=(",", ":")), json.dumps(companies, ensure_ascii=False, separators=(",", ":")), cutoff.isoformat() if cutoff else None, now),
            )
            if idempotency_action_id:
                conn.execute(
                    "UPDATE idempotent_actions SET response_json = ?, updated_at = ? WHERE action_id = ?",
                    (json.dumps({"scan_id": scan_id}, separators=(",", ":")), now, idempotency_action_id),
                )
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    detail = get_scan_detail(scan_id, database_path=path)
    if detail is None:
        raise RuntimeError("scan_persistence_failed")
    return detail

def get_scan_detail(scan_id: str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with _scan_store_connection(database_path) as conn:
        row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
        return _scan_resource(conn, row) if row is not None else None

def query_scans(
    *, lifecycle: str = "active", execution_status: str | None = None, usable_for_run: bool | None = None,
    search: str = "", page: int = 1, page_size: int = 20, database_path: Path | None = None,
) -> dict[str, Any]:
    with _scan_store_connection(database_path) as conn:
        rows = conn.execute(
            "SELECT * FROM scans WHERE lifecycle = ? ORDER BY created_at DESC, scan_id DESC",
            (lifecycle,),
        ).fetchall()
        resources = [_scan_resource(conn, row) for row in rows]
    needle = search.strip().casefold()
    resources = [row for row in resources if (not execution_status or row["execution_status"] == execution_status) and (usable_for_run is None or row["capabilities"]["use_for_run"] is usable_for_run) and (not needle or needle in row["scan_id"].casefold() or needle in row["scan_name"].casefold())]
    return {"items": resources[(max(1, page) - 1) * page_size : max(1, page) * page_size], "total": len(resources)}

def request_scan_cancel(
    scan_id: str, *, expected_revision: int | None = None, database_path: Path | None = None
) -> dict[str, Any]:
    with _scan_store_connection(database_path) as conn:
        row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
        if row is None:
            raise ValueError("scan_not_found")
        resource = _scan_resource(conn, row)
        if expected_revision is not None and expected_revision != resource["row_revision"]:
            raise ValueError("scan_revision_conflict")
        if not resource["capabilities"]["cancel"]:
            raise ValueError("scan_not_cancellable")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute("UPDATE scans SET execution_status='cancelling', cancel_requested_at=?, row_revision=row_revision+1 WHERE scan_id=?", (now, scan_id))
        conn.commit()
    return get_scan_detail(scan_id, database_path=database_path) or {}

def claim_scan_execution(scan_id: str, *, database_path: Path | None = None) -> bool:
    with _scan_store_connection(database_path) as conn:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cursor = conn.execute(
            "UPDATE scans SET execution_status='running', started_at=?, row_revision=row_revision+1 WHERE scan_id=? AND execution_status='queued' AND lifecycle='active'",
            (now, scan_id),
        )
        conn.commit()
        return cursor.rowcount == 1

def fail_scan_execution(
    scan_id: str, *, error_code: str, error_message: str, database_path: Path | None = None
) -> dict[str, Any]:
    with _scan_store_connection(database_path) as conn:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            "UPDATE scans SET execution_status='failed', failure_code=?, failure_message=?, finished_at=?, row_revision=row_revision+1 WHERE scan_id=? AND execution_status IN ('queued','running','cancelling')",
            (error_code[:120], error_message[:1000], now, scan_id),
        )
        conn.commit()
    return get_scan_detail(scan_id, database_path=database_path) or {}

def cancel_scan_execution(scan_id: str, *, database_path: Path | None = None) -> dict[str, Any]:
    with _scan_store_connection(database_path) as conn:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            "UPDATE scans SET execution_status='cancelled', finished_at=?, row_revision=row_revision+1 WHERE scan_id=? AND execution_status='cancelling'",
            (now, scan_id),
        )
        conn.commit()
    return get_scan_detail(scan_id, database_path=database_path) or {}

def commit_scan_output(scan_id: str, *, output_json: str, database_path: Path | None = None) -> dict[str, Any]:
    try:
        jobs = json.loads(output_json)
    except (TypeError, ValueError) as exc:
        raise ValueError("scan_output_invalid") from exc
    if not isinstance(jobs, list):
        raise ValueError("scan_output_invalid")
    raw = output_json.encode("utf-8")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _scan_store_connection(database_path) as conn:
        row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
        if row is None:
            raise ValueError("scan_not_found")
        if conn.execute("SELECT 1 FROM scan_outputs WHERE scan_id = ?", (scan_id,)).fetchone():
            raise ValueError("scan_output_immutable")
        if str(row["execution_status"]) in {"succeeded", "failed", "cancelled"}:
            raise ValueError("scan_terminal")
        conn.execute("INSERT INTO scan_outputs VALUES (?, ?, ?, ?, ?, ?)", (scan_id, output_json, hashlib.sha256(raw).hexdigest(), len(raw), len(jobs), now))
        conn.execute("UPDATE scans SET execution_status='succeeded', finished_at=?, row_revision=row_revision+1 WHERE scan_id=?", (now, scan_id))
        conn.commit()
    return get_scan_detail(scan_id, database_path=database_path) or {}

def get_scan_output(scan_id: str, *, database_path: Path | None = None) -> dict[str, Any] | None:
    with _scan_store_connection(database_path) as conn:
        scan = conn.execute("SELECT execution_status FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
        if scan is None:
            return None
        output = conn.execute("SELECT * FROM scan_outputs WHERE scan_id = ?", (scan_id,)).fetchone()
        if output is None:
            raise ValueError("scan_output_not_ready" if scan["execution_status"] in {"queued", "running", "cancelling"} else "scan_output_unavailable")
        raw = str(output["output_json"]).encode("utf-8")
        if hashlib.sha256(raw).hexdigest() != str(output["sha256"]) or len(raw) != int(output["byte_length"]):
            raise ValueError("scan_output_integrity_failed")
        return {"output_json": str(output["output_json"]), "sha256": str(output["sha256"]), "byte_length": int(output["byte_length"]), "record_count": int(output["record_count"])}

def query_scan_jobs(
    scan_id: str, *, page: int = 1, page_size: int = 20, database_path: Path | None = None
) -> dict[str, Any]:
    output = get_scan_output(scan_id, database_path=database_path)
    if output is None:
        raise ValueError("scan_not_found")
    jobs = json.loads(output["output_json"])
    return {"items": jobs[(max(1, page) - 1) * page_size : max(1, page) * page_size], "total": len(jobs)}

def transition_scan_lifecycle(
    items: list[dict[str, Any]], *, target: str, database_path: Path | None = None
) -> dict[str, Any]:
    if target not in {"active", "archived"}:
        raise ValueError("scan_lifecycle_invalid")
    with _scan_store_connection(database_path) as conn:
        resources: list[dict[str, Any]] = []
        for item in items:
            row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (item["scan_id"],)).fetchone()
            if row is None:
                raise ValueError("scan_not_found")
            resource = _scan_resource(conn, row)
            if resource["row_revision"] != int(item["expected_revision"]):
                raise ValueError("scan_revision_conflict")
            capability = "archive" if target == "archived" else "unarchive"
            if not resource["capabilities"][capability]:
                raise ValueError(f"scan_not_{capability}able")
            resources.append(resource)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        for resource in resources:
            conn.execute(
                "UPDATE scans SET lifecycle=?, archived_at=?, row_revision=row_revision+1 WHERE scan_id=?",
                (target, now if target == "archived" else None, resource["scan_id"]),
            )
        conn.commit()
    return {"items": [get_scan_detail(resource["scan_id"], database_path=database_path) for resource in resources]}

def _scan_delete_preview(conn: sqlite3.Connection, scan_ids: list[str]) -> dict[str, Any]:
    eligible: list[str] = []
    referenced: list[dict[str, Any]] = []
    blocked: list[str] = []
    missing: list[str] = []
    revisions: list[tuple[str, int]] = []
    for scan_id in scan_ids:
        row = conn.execute("SELECT * FROM scans WHERE scan_id = ?", (scan_id,)).fetchone()
        if row is None:
            missing.append(scan_id)
            continue
        resource = _scan_resource(conn, row)
        revisions.append((scan_id, resource["row_revision"]))
        count = int(conn.execute("SELECT COUNT(*) FROM run_scan_inputs WHERE scan_id = ?", (scan_id,)).fetchone()[0])
        if count:
            referenced.append({"scan_id": scan_id, "run_count": count})
        elif resource["capabilities"]["delete"]:
            eligible.append(scan_id)
        else:
            blocked.append(scan_id)
    fingerprint = hashlib.sha256(json.dumps({"scan_ids": scan_ids, "revisions": revisions, "eligible": eligible, "referenced": referenced, "blocked": blocked, "missing": missing}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {"requested_scan_ids": list(scan_ids), "eligible_scan_ids": eligible, "referenced_scan_ids": referenced, "blocked_scan_ids": blocked, "missing_scan_ids": missing, "preview_revision": fingerprint}

def preview_delete_archived_scans(scan_ids: list[str], *, database_path: Path | None = None) -> dict[str, Any]:
    with _scan_store_connection(database_path) as conn:
        return _scan_delete_preview(conn, scan_ids)

def delete_archived_scans(
    scan_ids: list[str], *, preview_revision: str, database_path: Path | None = None
) -> dict[str, Any]:
    with _scan_store_connection(database_path) as conn:
        preview = _scan_delete_preview(conn, scan_ids)
        if preview["preview_revision"] != preview_revision or preview["referenced_scan_ids"] or preview["blocked_scan_ids"] or preview["missing_scan_ids"]:
            raise ValueError("delete_preview_stale")
        conn.executemany("DELETE FROM scans WHERE scan_id = ?", [(scan_id,) for scan_id in preview["eligible_scan_ids"]])
        conn.commit()
    return {"deleted_count": len(preview["eligible_scan_ids"]), "deleted_scan_ids": preview["eligible_scan_ids"]}


def _ensure_provider_state(conn: sqlite3.Connection, provider_id: str) -> int:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        "INSERT OR IGNORE INTO api_provider_state (provider_id, revision, updated_at) VALUES (?, 1, ?)",
        (provider_id, now),
    )
    row = conn.execute(
        "SELECT revision FROM api_provider_state WHERE provider_id = ?",
        (provider_id,),
    ).fetchone()
    if row is None:
        raise RuntimeError("provider state did not persist")
    return int(row["revision"])


def _require_provider_revision(
    conn: sqlite3.Connection, provider_id: str, expected_revision: int
) -> int:
    revision = _ensure_provider_state(conn, provider_id)
    if revision != expected_revision:
        raise ProviderPersistenceRevisionConflict("provider changed since last read")
    return revision


def _bump_provider_revision(conn: sqlite3.Connection, provider_id: str) -> int:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn.execute(
        "UPDATE api_provider_state SET revision = revision + 1, updated_at = ? WHERE provider_id = ?",
        (now, provider_id),
    )
    return _ensure_provider_state(conn, provider_id)


def get_api_provider_revision(
    provider_id: str, *, database_path: Path | None = None
) -> int:
    with _provider_store_connection(database_path) as conn:
        revision = _ensure_provider_state(conn, provider_id)
        conn.commit()
    return revision


def list_custom_api_providers(*, database_path: Path | None = None) -> list[dict[str, Any]]:
    with _provider_store_connection(database_path) as conn:
        rows = conn.execute(
            """
            SELECT providers.*, state.revision AS provider_revision
            FROM custom_api_providers AS providers
            JOIN api_provider_state AS state USING (provider_id)
            ORDER BY providers.display_name, providers.provider_id
            """
        ).fetchall()
    return [dict(row) for row in rows]


def get_custom_api_provider(
    provider_id: str, *, database_path: Path | None = None
) -> dict[str, Any] | None:
    with _provider_store_connection(database_path) as conn:
        row = conn.execute(
            "SELECT * FROM custom_api_providers WHERE provider_id = ?",
            (provider_id,),
        ).fetchone()
        if row is not None:
            result = dict(row)
            result["provider_revision"] = _ensure_provider_state(conn, provider_id)
            conn.commit()
            return result
    return None


def create_custom_api_provider(
    provider_id: str,
    *,
    display_name: str,
    compatibility: str,
    database_path: Path | None = None,
) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            """
            INSERT INTO custom_api_providers (
                provider_id, display_name, compatibility, revision, created_at, updated_at
            ) VALUES (?, ?, ?, 1, ?, ?)
            """,
            (provider_id, display_name, compatibility, now, now),
        )
        _ensure_provider_state(conn, provider_id)
        conn.commit()
    result = get_custom_api_provider(provider_id, database_path=database_path)
    if result is None:
        raise RuntimeError("custom provider insert did not persist")
    return result


def update_custom_api_provider(
    provider_id: str,
    *,
    display_name: str,
    compatibility: str,
    expected_revision: int,
    database_path: Path | None = None,
) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _require_provider_revision(conn, provider_id, expected_revision)
        cursor = conn.execute(
            """
            UPDATE custom_api_providers
            SET display_name = ?, compatibility = ?, revision = revision + 1, updated_at = ?
            WHERE provider_id = ?
            """,
            (display_name, compatibility, now, provider_id),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise ProviderPersistenceRevisionConflict("custom provider changed since last read")
        _bump_provider_revision(conn, provider_id)
        conn.commit()
    result = get_custom_api_provider(provider_id, database_path=database_path)
    if result is None:
        raise KeyError(provider_id)
    return result


def delete_custom_api_provider(
    provider_id: str,
    *,
    expected_revision: int,
    database_path: Path | None = None,
) -> None:
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _require_provider_revision(conn, provider_id, expected_revision)
        cursor = conn.execute("DELETE FROM custom_api_providers WHERE provider_id = ?", (provider_id,))
        if cursor.rowcount != 1:
            conn.rollback()
            raise ProviderPersistenceRevisionConflict("custom provider changed since last read")
        conn.commit()


def delete_custom_api_provider_bundle(
    provider_id: str,
    *,
    expected_revision: int,
    database_path: Path | None = None,
) -> None:
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _require_provider_revision(conn, provider_id, expected_revision)
        if conn.execute("SELECT 1 FROM custom_api_providers WHERE provider_id = ?", (provider_id,)).fetchone() is None:
            raise KeyError(provider_id)
        conn.execute("DELETE FROM api_provider_models WHERE provider_id = ?", (provider_id,))
        conn.execute("DELETE FROM api_provider_connections WHERE provider_id = ?", (provider_id,))
        conn.execute("DELETE FROM custom_api_providers WHERE provider_id = ?", (provider_id,))
        conn.execute("DELETE FROM api_provider_state WHERE provider_id = ?", (provider_id,))
        conn.commit()


def get_api_provider_connection(
    provider_id: str, *, database_path: Path | None = None
) -> dict[str, Any] | None:
    with _provider_store_connection(database_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_provider_connections WHERE provider_id = ?",
            (provider_id,),
        ).fetchone()
        if row is not None:
            result = dict(row)
            result["provider_revision"] = _ensure_provider_state(conn, provider_id)
            conn.commit()
            return result
    return None


def save_api_provider_connection(
    provider_id: str,
    *,
    base_url: str | None,
    api_type: str,
    verification_status: str,
    verified_at: str | None,
    credential_account: str,
    expected_revision: int,
    database_path: Path | None = None,
) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _require_provider_revision(conn, provider_id, expected_revision)
        current = conn.execute(
            "SELECT connection_revision, created_at FROM api_provider_connections WHERE provider_id = ?",
            (provider_id,),
        ).fetchone()
        current_revision = int(current["connection_revision"]) if current is not None else None
        revision = (current_revision or 0) + 1
        created_at = str(current["created_at"]) if current is not None else now
        conn.execute(
            """
            INSERT INTO api_provider_connections (
                provider_id, base_url, api_type, verification_status, verified_at,
                connection_revision, credential_account, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(provider_id) DO UPDATE SET
                base_url = excluded.base_url,
                api_type = excluded.api_type,
                verification_status = excluded.verification_status,
                verified_at = excluded.verified_at,
                connection_revision = excluded.connection_revision,
                credential_account = excluded.credential_account,
                updated_at = excluded.updated_at
            """,
            (
                provider_id,
                base_url,
                api_type,
                verification_status,
                verified_at,
                revision,
                credential_account,
                created_at,
                now,
            ),
        )
        if current_revision is not None:
            conn.execute(
                """
                UPDATE api_provider_models
                SET validation_status = 'needs_retest', revision = revision + 1, updated_at = ?
                WHERE provider_id = ?
                """,
                (now, provider_id),
            )
        _bump_provider_revision(conn, provider_id)
        conn.commit()
    result = get_api_provider_connection(provider_id, database_path=database_path)
    if result is None:
        raise RuntimeError("provider connection write did not persist")
    return result


def delete_api_provider_connection(
    provider_id: str,
    *,
    expected_revision: int,
    database_path: Path | None = None,
) -> None:
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _require_provider_revision(conn, provider_id, expected_revision)
        cursor = conn.execute(
            "DELETE FROM api_provider_connections WHERE provider_id = ?",
            (provider_id,),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise ProviderPersistenceRevisionConflict("provider connection changed since last read")
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            """
            UPDATE api_provider_models
            SET validation_status = 'needs_retest', revision = revision + 1, updated_at = ?
            WHERE provider_id = ?
            """,
            (now, provider_id),
        )
        _bump_provider_revision(conn, provider_id)
        conn.commit()


def list_api_provider_models(
    provider_id: str, *, database_path: Path | None = None
) -> list[dict[str, Any]]:
    with _provider_store_connection(database_path) as conn:
        provider_revision = _ensure_provider_state(conn, provider_id)
        rows = conn.execute(
            "SELECT * FROM api_provider_models WHERE provider_id = ? ORDER BY model_id, model_record_id",
            (provider_id,),
        ).fetchall()
        conn.commit()
    return [{**dict(row), "provider_revision": provider_revision} for row in rows]


def get_api_provider_model(
    model_record_id: str, *, database_path: Path | None = None
) -> dict[str, Any] | None:
    with _provider_store_connection(database_path) as conn:
        row = conn.execute(
            "SELECT * FROM api_provider_models WHERE model_record_id = ?",
            (model_record_id,),
        ).fetchone()
        if row is not None:
            result = dict(row)
            result["provider_revision"] = _ensure_provider_state(conn, str(row["provider_id"]))
            conn.commit()
            return result
    return None


def create_api_provider_model(
    model_record_id: str,
    *,
    provider_id: str,
    model_id: str,
    validated_connection_revision: int,
    last_tested_at: str,
    expected_revision: int,
    database_path: Path | None = None,
) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        _require_provider_revision(conn, provider_id, expected_revision)
        conn.execute(
            """
            INSERT INTO api_provider_models (
                model_record_id, provider_id, model_id, validation_status,
                validated_connection_revision, last_tested_at, last_test_error_code,
                revision, created_at, updated_at
            ) VALUES (?, ?, ?, 'validated', ?, ?, NULL, 1, ?, ?)
            """,
            (
                model_record_id,
                provider_id,
                model_id,
                validated_connection_revision,
                last_tested_at,
                now,
                now,
            ),
        )
        _bump_provider_revision(conn, provider_id)
        conn.commit()
    result = get_api_provider_model(model_record_id, database_path=database_path)
    if result is None:
        raise RuntimeError("provider model insert did not persist")
    return result


def update_api_provider_model(
    model_record_id: str,
    *,
    validation_status: str,
    validated_connection_revision: int | None,
    last_tested_at: str | None,
    last_test_error_code: str | None,
    expected_revision: int,
    database_path: Path | None = None,
) -> dict[str, Any]:
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT provider_id FROM api_provider_models WHERE model_record_id = ?",
            (model_record_id,),
        ).fetchone()
        if row is None:
            raise KeyError(model_record_id)
        provider_id = str(row["provider_id"])
        _require_provider_revision(conn, provider_id, expected_revision)
        cursor = conn.execute(
            """
            UPDATE api_provider_models
            SET validation_status = ?, validated_connection_revision = ?, last_tested_at = ?,
                last_test_error_code = ?, revision = revision + 1, updated_at = ?
            WHERE model_record_id = ?
            """,
            (
                validation_status,
                validated_connection_revision,
                last_tested_at,
                last_test_error_code,
                now,
                model_record_id,
            ),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise ProviderPersistenceRevisionConflict("provider model changed since last read")
        _bump_provider_revision(conn, provider_id)
        conn.commit()
    result = get_api_provider_model(model_record_id, database_path=database_path)
    if result is None:
        raise KeyError(model_record_id)
    return result


def delete_api_provider_model(
    model_record_id: str,
    *,
    expected_revision: int,
    database_path: Path | None = None,
) -> None:
    with _provider_store_connection(database_path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT provider_id FROM api_provider_models WHERE model_record_id = ?",
            (model_record_id,),
        ).fetchone()
        if row is None:
            raise KeyError(model_record_id)
        provider_id = str(row["provider_id"])
        _require_provider_revision(conn, provider_id, expected_revision)
        cursor = conn.execute(
            "DELETE FROM api_provider_models WHERE model_record_id = ?",
            (model_record_id,),
        )
        if cursor.rowcount != 1:
            conn.rollback()
            raise ProviderPersistenceRevisionConflict("provider model changed since last read")
        _bump_provider_revision(conn, provider_id)
        conn.commit()


def integration_migration_applied(
    migration_key: str, *, database_path: Path | None = None
) -> bool:
    with _provider_store_connection(database_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM integration_migrations WHERE migration_key = ?",
            (migration_key,),
        ).fetchone()
    return row is not None


def record_integration_migration(
    migration_key: str,
    *,
    details: dict[str, Any],
    database_path: Path | None = None,
) -> dict[str, Any]:
    completed_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with _provider_store_connection(database_path) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO integration_migrations (
                migration_key, details_json, completed_at
            ) VALUES (?, ?, ?)
            """,
            (
                migration_key,
                json.dumps(details, sort_keys=True, separators=(",", ":")),
                completed_at,
            ),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM integration_migrations WHERE migration_key = ?",
            (migration_key,),
        ).fetchone()
    if row is None:
        raise RuntimeError("integration migration record did not persist")
    result = dict(row)
    result["details"] = json.loads(result.pop("details_json"))
    return result


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
_PREFERENCE_OPTIMIZATION_RUN_COLUMNS = (
    "preference_optimization_run_id",
    "training_run_id",
    "policy_snapshot_id",
    "schema_version",
    "domain_id",
    "historical_snapshot_status",
    "settings_revision",
    "ranking_mode",
    "personalization_strength",
    "evidence_head_fingerprint",
    "event_watermark",
    "source_rating_event_ids_json",
    "rating_evidence_rows_json",
    "created_at",
    "hidden_at",
    "hidden_by",
)
_JSON_COLUMNS = frozenset(
    {
        "result_json",
        "preference_vector_json",
        "solver_metadata_json",
        "evaluation_json",
        "source_rating_event_ids_json",
        "rating_evidence_rows_json",
    }
)

_PREFERENCE_OPTIMIZATION_PROJECTION_MIGRATION = "preference_optimization_projection_v1"
_RATING_EVIDENCE_ROW_FIELDS = frozenset(
    {
        "source_rating_event_id",
        "run_id",
        "alternative_id",
        "job_label",
        "source_job_url",
        "displayed_rank",
        "baseline_fit",
        "baseline_fit_label",
        "rating",
        "rated_at",
    }
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
        CREATE TABLE IF NOT EXISTS integration_migrations (
            migration_key TEXT PRIMARY KEY,
            details_json TEXT NOT NULL DEFAULT '{}' CHECK (json_valid(details_json)),
            completed_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS pipeline_settings (
            setting_key TEXT NOT NULL,
            setting_value_json TEXT NOT NULL,
            updated_by TEXT,
            updated_at TEXT NOT NULL
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
    _ensure_process_event_tables(conn)
    _apply_preference_optimization_projection_migration(conn)


def _preference_optimization_migration_context() -> dict[str, Any]:
    from fitcv.config import load_config
    from fitcv.embeddings import build_embedding_contract_fingerprint

    config = load_config()
    decision_policy = config["decision_learning_policy"]
    optimizer = decision_policy["inverse_optimization"]
    bounds = optimizer["learned_alpha_bounds"]
    embedding_contract = build_embedding_contract_fingerprint(config)
    embedding_payload = embedding_contract["payload"]
    return {
        "domain_id": str(decision_policy["domain_id"]),
        "baseline_policy_fingerprint": str(build_contract_fingerprint(config["ranking_policy"])),
        "ranking_contract_fingerprint": str(
            config["ranking_contract"]["ranking_contract_fingerprint"]
        ),
        "embedding_model": str(embedding_payload["embedding_model"]),
        "embedding_dimension": int(embedding_payload["embedding_dimension"]),
        "embedding_contract_fingerprint": str(embedding_contract["fingerprint"]),
        "preference_vector_norm_bound": float(optimizer["preference_vector_norm_bound"]),
        "recommended_strength": float(optimizer["learned_alpha"]),
        "minimum_strength": float(bounds["minimum"]),
        "maximum_strength": float(bounds["maximum"]),
    }


def _snapshot_matches_current_preference_runtime(
    snapshot: dict[str, Any], context: dict[str, Any]
) -> bool:
    strength = float(snapshot["learned_alpha"])
    if not context["minimum_strength"] <= strength <= context["maximum_strength"]:
        return False
    if str(snapshot["domain_id"]) != context["domain_id"]:
        return False
    runtime = PreferenceRuntimeContract.build(
        domain_id=context["domain_id"],
        baseline_policy_fingerprint=context["baseline_policy_fingerprint"],
        ranking_contract_fingerprint=context["ranking_contract_fingerprint"],
        embedding_model=context["embedding_model"],
        embedding_dimension=context["embedding_dimension"],
        embedding_contract_fingerprint=context["embedding_contract_fingerprint"],
        learned_alpha=strength,
        preference_vector_norm_bound=context["preference_vector_norm_bound"],
    )
    return runtime.runtime_contract_fingerprint == snapshot["runtime_contract_fingerprint"]


def _create_preference_optimization_projection_schema(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS preference_optimization_runs (
            preference_optimization_run_id TEXT PRIMARY KEY
                CHECK (preference_optimization_run_id GLOB 'por_*'),
            training_run_id TEXT NOT NULL UNIQUE
                REFERENCES inverse_training_runs(training_run_id) ON DELETE RESTRICT,
            policy_snapshot_id TEXT
                REFERENCES ranking_policy_snapshots(policy_snapshot_id) ON DELETE RESTRICT,
            schema_version TEXT NOT NULL CHECK (schema_version = 'preference_optimization_run_v1'),
            domain_id TEXT NOT NULL CHECK (length(trim(domain_id)) > 0),
            historical_snapshot_status TEXT NOT NULL
                CHECK (historical_snapshot_status IN ('complete', 'legacy_unavailable')),
            settings_revision TEXT,
            ranking_mode TEXT CHECK (ranking_mode IS NULL OR ranking_mode = 'personalized'),
            personalization_strength REAL
                CHECK (personalization_strength IS NULL OR (
                    personalization_strength > 0.0 AND personalization_strength <= 0.25
                )),
            evidence_head_fingerprint TEXT,
            event_watermark INTEGER CHECK (event_watermark IS NULL OR event_watermark >= 0),
            source_rating_event_ids_json TEXT NOT NULL
                CHECK (json_valid(source_rating_event_ids_json))
                CHECK (json_type(source_rating_event_ids_json) = 'array'),
            rating_evidence_rows_json TEXT NOT NULL
                CHECK (json_valid(rating_evidence_rows_json))
                CHECK (json_type(rating_evidence_rows_json) = 'array'),
            created_at TEXT NOT NULL,
            hidden_at TEXT,
            hidden_by TEXT,
            CHECK (
                (
                    historical_snapshot_status = 'complete'
                    AND settings_revision IS NOT NULL
                    AND ranking_mode = 'personalized'
                    AND personalization_strength IS NOT NULL
                    AND evidence_head_fingerprint IS NOT NULL
                    AND event_watermark IS NOT NULL
                )
                OR
                (
                    historical_snapshot_status = 'legacy_unavailable'
                    AND settings_revision IS NULL
                    AND ranking_mode IS NULL
                    AND personalization_strength IS NULL
                    AND evidence_head_fingerprint IS NULL
                    AND event_watermark IS NULL
                    AND json_array_length(source_rating_event_ids_json) = 0
                    AND json_array_length(rating_evidence_rows_json) = 0
                )
            ),
            CHECK (
                (hidden_at IS NULL AND hidden_by IS NULL)
                OR (hidden_at IS NOT NULL AND length(trim(hidden_by)) > 0)
            )
        )
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS preference_optimization_runs_immutable_payload
        BEFORE UPDATE OF preference_optimization_run_id, training_run_id, policy_snapshot_id,
            schema_version, domain_id, historical_snapshot_status, settings_revision,
            ranking_mode, personalization_strength, evidence_head_fingerprint,
            event_watermark, source_rating_event_ids_json, rating_evidence_rows_json,
            created_at
        ON preference_optimization_runs BEGIN
            SELECT RAISE(ABORT, 'immutable optimization run payload');
        END
        """
    )
    conn.execute(
        """
        CREATE TRIGGER IF NOT EXISTS preference_optimization_runs_no_delete
        BEFORE DELETE ON preference_optimization_runs BEGIN
            SELECT RAISE(ABORT, 'optimization run history is append-only');
        END
        """
    )


def _backfill_preference_optimization_runs(conn: sqlite3.Connection) -> int:
    count = 0
    training_cursor = conn.execute(
        "SELECT training_run_id, domain_id, created_at FROM inverse_training_runs "
        "ORDER BY created_at, training_run_id"
    )
    for training_run_id, domain_id, created_at in training_cursor.fetchall():
        internal_id = str(training_run_id)
        public_id = build_preference_optimization_run_id(internal_id)
        existing_public = conn.execute(
            "SELECT training_run_id FROM preference_optimization_runs "
            "WHERE preference_optimization_run_id = ?",
            (public_id,),
        ).fetchone()
        existing_internal = conn.execute(
            "SELECT preference_optimization_run_id FROM preference_optimization_runs "
            "WHERE training_run_id = ?",
            (internal_id,),
        ).fetchone()
        if existing_public is not None or existing_internal is not None:
            if (
                existing_public is None
                or str(existing_public[0]) != internal_id
                or existing_internal is None
                or str(existing_internal[0]) != public_id
            ):
                raise ValueError("preference optimization run identity mapping conflict")
            continue
        snapshot_ids = conn.execute(
            "SELECT policy_snapshot_id FROM ranking_policy_snapshots "
            "WHERE training_run_id = ? ORDER BY created_at, policy_snapshot_id",
            (internal_id,),
        ).fetchall()
        policy_snapshot_id = str(snapshot_ids[0][0]) if len(snapshot_ids) == 1 else None
        _insert_policy_row(
            conn,
            "preference_optimization_runs",
            _PREFERENCE_OPTIMIZATION_RUN_COLUMNS,
            {
                "preference_optimization_run_id": public_id,
                "training_run_id": internal_id,
                "policy_snapshot_id": policy_snapshot_id,
                "schema_version": "preference_optimization_run_v1",
                "domain_id": str(domain_id),
                "historical_snapshot_status": "legacy_unavailable",
                "settings_revision": None,
                "ranking_mode": None,
                "personalization_strength": None,
                "evidence_head_fingerprint": None,
                "event_watermark": None,
                "source_rating_event_ids_json": [],
                "rating_evidence_rows_json": [],
                "created_at": str(created_at),
                "hidden_at": None,
                "hidden_by": None,
            },
        )
        count += 1
    return count


def _collapse_active_preference_policies(
    conn: sqlite3.Connection, context: dict[str, Any]
) -> tuple[dict[str, dict[str, Any]], set[str], int]:
    cursor = conn.execute(
        "SELECT * FROM ranking_policy_snapshots WHERE status = 'active' "
        "ORDER BY domain_id, activated_at DESC, policy_snapshot_id DESC"
    )
    active_rows = [_row_dict(cursor, row) for row in cursor.fetchall()]
    by_domain: dict[str, list[dict[str, Any]]] = {}
    for row in active_rows:
        if row is not None:
            by_domain.setdefault(str(row["domain_id"]), []).append(row)
    winners: dict[str, dict[str, Any]] = {}
    compatible_ids: set[str] = set()
    retired_count = 0
    for domain_id, rows in by_domain.items():
        compatible = [
            row for row in rows if _snapshot_matches_current_preference_runtime(row, context)
        ]
        winner = (compatible or rows)[0]
        winners[domain_id] = winner
        if compatible:
            compatible_ids.add(str(winner["policy_snapshot_id"]))
        for row in rows:
            if row["policy_snapshot_id"] == winner["policy_snapshot_id"]:
                continue
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'retired' "
                "WHERE policy_snapshot_id = ?",
                (row["policy_snapshot_id"],),
            )
            _append_policy_event(
                conn,
                domain_id=domain_id,
                runtime_contract_fingerprint=str(row["runtime_contract_fingerprint"]),
                previous_snapshot_id=str(row["policy_snapshot_id"]),
                target_snapshot_id=str(winner["policy_snapshot_id"]),
                action="retire",
                reason_code="domain_single_active_migration",
                expected_parent_ref=None,
                evidence_head_fingerprint=None,
                acted_by="system_migration",
            )
            retired_count += 1
    return winners, compatible_ids, retired_count


def _initialize_preference_optimization_settings(
    conn: sqlite3.Connection,
    context: dict[str, Any],
    winners: dict[str, dict[str, Any]],
    compatible_ids: set[str],
) -> None:
    winner = winners.get(context["domain_id"])
    compatible_winner = (
        winner
        if winner is not None and str(winner["policy_snapshot_id"]) in compatible_ids
        else None
    )
    defaults = {
        "preference_optimization.ranking_mode": (
            "personalized" if compatible_winner is not None else "baseline"
        ),
        "preference_optimization.personalization_strength": (
            float(compatible_winner["learned_alpha"])
            if compatible_winner is not None
            else context["recommended_strength"]
        ),
    }
    existing = {
        str(row[0])
        for row in conn.execute(
            "SELECT DISTINCT setting_key FROM pipeline_settings "
            "WHERE setting_key IN (?, ?)",
            tuple(defaults),
        ).fetchall()
    }
    now = _policy_now()
    for key, value in defaults.items():
        if key not in existing:
            conn.execute(
                "INSERT INTO pipeline_settings "
                "(setting_key, setting_value_json, updated_by, updated_at) VALUES (?, ?, ?, ?)",
                (key, json.dumps(value), "system_migration", now),
            )


def _apply_preference_optimization_projection_migration(conn: sqlite3.Connection) -> None:
    if conn.execute(
        "SELECT 1 FROM integration_migrations WHERE migration_key = ?",
        (_PREFERENCE_OPTIMIZATION_PROJECTION_MIGRATION,),
    ).fetchone() is not None:
        return
    conn.commit()
    conn.execute("BEGIN IMMEDIATE")
    try:
        context = _preference_optimization_migration_context()
        _create_preference_optimization_projection_schema(conn)
        backfilled_count = _backfill_preference_optimization_runs(conn)
        winners, compatible_ids, retired_count = _collapse_active_preference_policies(
            conn, context
        )
        conn.execute("DROP INDEX IF EXISTS one_active_ranking_policy")
        conn.execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS one_active_ranking_policy_per_domain "
            "ON ranking_policy_snapshots (domain_id) WHERE status = 'active'"
        )
        _initialize_preference_optimization_settings(
            conn, context, winners, compatible_ids
        )
        conn.execute(
            "INSERT INTO integration_migrations "
            "(migration_key, details_json, completed_at) VALUES (?, ?, ?)",
            (
                _PREFERENCE_OPTIMIZATION_PROJECTION_MIGRATION,
                json.dumps(
                    {
                        "backfilled_run_count": backfilled_count,
                        "retired_active_policy_count": retired_count,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                _policy_now(),
            ),
        )
        conn.commit()
    except Exception:
        conn.rollback()
        raise


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


def _required_projection_text(value: Any, field: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field} must be nonempty")
    return text


def _prepare_preference_optimization_run(
    training: dict[str, Any],
    snapshot: dict[str, Any] | None,
    projection_payload: dict[str, Any],
) -> dict[str, Any]:
    settings_revision_value = _required_projection_text(
        projection_payload.get("settings_revision"), "settings_revision"
    )
    if projection_payload.get("ranking_mode") != "personalized":
        raise ValueError("ranking_mode must be personalized")
    raw_strength = projection_payload.get("personalization_strength")
    if raw_strength is None:
        raise ValueError("personalization_strength must be finite")
    try:
        strength = float(raw_strength)
    except (TypeError, ValueError) as exc:
        raise ValueError("personalization_strength must be finite") from exc
    if not math.isfinite(strength) or not 0.0 < strength <= 0.25:
        raise ValueError("personalization_strength must be within (0, 0.25]")
    evidence_head_fingerprint = _required_projection_text(
        projection_payload.get("evidence_head_fingerprint"),
        "evidence_head_fingerprint",
    )
    event_watermark = projection_payload.get("event_watermark")
    if isinstance(event_watermark, bool) or not isinstance(event_watermark, int):
        raise ValueError("event_watermark must be a nonnegative integer")
    if event_watermark < 0 or event_watermark != int(training["event_watermark"]):
        raise ValueError("event_watermark must match training run")
    raw_event_ids = projection_payload.get("source_rating_event_ids")
    if not isinstance(raw_event_ids, list):
        raise ValueError("source_rating_event_ids must be a list")
    source_event_ids = [
        _required_projection_text(value, "source_rating_event_ids") for value in raw_event_ids
    ]
    if len(source_event_ids) != len(set(source_event_ids)):
        raise ValueError("source_rating_event_ids must be ordered unique")
    raw_rows = projection_payload.get("rating_evidence_rows")
    if not isinstance(raw_rows, list):
        raise ValueError("rating_evidence_rows must be a list")
    rows: list[dict[str, Any]] = []
    seen_row_event_ids: set[str] = set()
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict) or frozenset(raw_row) != _RATING_EVIDENCE_ROW_FIELDS:
            raise ValueError("rating_evidence_rows must use the canonical fields")
        source_event_id = _required_projection_text(
            raw_row["source_rating_event_id"], "source_rating_event_id"
        )
        if source_event_id not in source_event_ids:
            raise ValueError("rating evidence row references unknown source event")
        if source_event_id in seen_row_event_ids:
            raise ValueError("rating evidence rows must reference unique source events")
        seen_row_event_ids.add(source_event_id)
        displayed_rank = raw_row["displayed_rank"]
        if isinstance(displayed_rank, bool) or not isinstance(displayed_rank, int) or displayed_rank <= 0:
            raise ValueError("displayed_rank must be positive")
        rating = raw_row["rating"]
        if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
            raise ValueError("rating must be within [1, 5]")
        try:
            baseline_fit = float(raw_row["baseline_fit"])
        except (TypeError, ValueError) as exc:
            raise ValueError("baseline_fit must be finite") from exc
        if not math.isfinite(baseline_fit):
            raise ValueError("baseline_fit must be finite")
        rated_at = _required_projection_text(raw_row["rated_at"], "rated_at")
        try:
            datetime.datetime.fromisoformat(rated_at)
        except ValueError as exc:
            raise ValueError("rated_at must be ISO-8601") from exc
        rows.append(
            {
                "source_rating_event_id": source_event_id,
                "run_id": _required_projection_text(raw_row["run_id"], "run_id"),
                "alternative_id": _required_projection_text(
                    raw_row["alternative_id"], "alternative_id"
                ),
                "job_label": _required_projection_text(raw_row["job_label"], "job_label"),
                "source_job_url": _required_projection_text(
                    raw_row["source_job_url"], "source_job_url"
                ),
                "displayed_rank": displayed_rank,
                "baseline_fit": baseline_fit,
                "baseline_fit_label": _required_projection_text(
                    raw_row["baseline_fit_label"], "baseline_fit_label"
                ),
                "rating": rating,
                "rated_at": rated_at,
            }
        )
    training_run_id = str(training["training_run_id"])
    return {
        "preference_optimization_run_id": build_preference_optimization_run_id(
            training_run_id
        ),
        "training_run_id": training_run_id,
        "policy_snapshot_id": (
            str(snapshot["policy_snapshot_id"]) if snapshot is not None else None
        ),
        "schema_version": "preference_optimization_run_v1",
        "domain_id": str(training["domain_id"]),
        "historical_snapshot_status": "complete",
        "settings_revision": settings_revision_value,
        "ranking_mode": "personalized",
        "personalization_strength": strength,
        "evidence_head_fingerprint": evidence_head_fingerprint,
        "event_watermark": event_watermark,
        "source_rating_event_ids_json": source_event_ids,
        "rating_evidence_rows_json": rows,
        "created_at": str(training["created_at"]),
        "hidden_at": None,
        "hidden_by": None,
    }


def _same_preference_optimization_run(
    existing: dict[str, Any], expected: dict[str, Any]
) -> bool:
    envelope_columns = {"created_at", "hidden_at", "hidden_by"}
    return all(
        existing.get(column) == expected.get(column)
        for column in _PREFERENCE_OPTIMIZATION_RUN_COLUMNS
        if column not in envelope_columns
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
    training: dict[str, Any],
    snapshot: dict[str, Any] | None,
    optimization_run: dict[str, Any],
) -> ProcessEvent:
    status = str(training["status"])
    training_id = str(training["training_run_id"])
    snapshot_id = str(snapshot["policy_snapshot_id"]) if snapshot is not None else None
    public_id = str(optimization_run["preference_optimization_run_id"])
    refs = [
        {"kind": "preference_optimization_run", "id": public_id},
        {"kind": "inverse_training_run", "id": training_id},
    ]
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
        payload={
            "status": status,
            "preference_optimization_run_id": public_id,
            "training_run_id": training_id,
            "policy_snapshot_id": snapshot_id,
        },
        diagnostic_refs=refs,
        event_id=f"optimization:{training_id}",
        recorded_at=datetime.datetime.fromisoformat(str(training["created_at"])),
    )


def persist_candidate_attempt(
    training_payload: dict[str, Any],
    snapshot_payload: dict[str, Any] | None = None,
    projection_payload: dict[str, Any] | None = None,
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
    if projection_payload is None:
        raise ValueError("preference optimization projection is required")
    optimization_run = _prepare_preference_optimization_run(
        training,
        snapshot,
        dict(projection_payload),
    )
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
        existing_optimization_run = _fetch_policy_row(
            conn,
            "preference_optimization_runs",
            "preference_optimization_run_id",
            str(optimization_run["preference_optimization_run_id"]),
        )
        if existing_optimization_run is None:
            mapped_run = _fetch_policy_row(
                conn,
                "preference_optimization_runs",
                "training_run_id",
                expected_training_id,
            )
            if mapped_run is not None:
                raise ValueError("preference optimization run identity mapping conflict")
            _insert_policy_row(
                conn,
                "preference_optimization_runs",
                _PREFERENCE_OPTIMIZATION_RUN_COLUMNS,
                optimization_run,
            )
        elif not _same_preference_optimization_run(
            existing_optimization_run, optimization_run
        ):
            raise ValueError("existing preference optimization run conflicts with payload")
        _insert_process_event(
            conn,
            _build_optimization_attempt_event(
                existing_training or training,
                existing_snapshot or snapshot,
                existing_optimization_run or optimization_run,
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
            "optimization_run": _fetch_policy_row(
                conn,
                "preference_optimization_runs",
                "preference_optimization_run_id",
                str(optimization_run["preference_optimization_run_id"]),
            ),
        }


def _preference_optimization_run_view(
    conn: sqlite3.Connection, projection: dict[str, Any]
) -> dict[str, Any]:
    training = _fetch_policy_row(
        conn,
        "inverse_training_runs",
        "training_run_id",
        str(projection["training_run_id"]),
    )
    if training is None:
        raise ValueError("preference optimization run has no training record")
    policy_snapshot = None
    if projection.get("policy_snapshot_id") is not None:
        policy_snapshot = _fetch_policy_row(
            conn,
            "ranking_policy_snapshots",
            "policy_snapshot_id",
            str(projection["policy_snapshot_id"]),
        )
        if policy_snapshot is None:
            raise ValueError("preference optimization run has no policy snapshot")
    return {
        **projection,
        "status": training["status"],
        "result_json": training["result_json"],
        "policy_status": (
            policy_snapshot["status"] if policy_snapshot is not None else None
        ),
        "activated_at": (
            policy_snapshot["activated_at"] if policy_snapshot is not None else None
        ),
    }


def get_preference_optimization_run(
    preference_optimization_run_id: str,
) -> dict[str, Any]:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        projection = _fetch_policy_row(
            conn,
            "preference_optimization_runs",
            "preference_optimization_run_id",
            preference_optimization_run_id,
        )
        if projection is None:
            raise KeyError(preference_optimization_run_id)
        return _preference_optimization_run_view(conn, projection)


def list_preference_optimization_runs(*, limit: int = 100) -> list[dict[str, Any]]:
    if limit <= 0:
        raise ValueError("limit must be positive")
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        cursor = conn.execute(
            "SELECT * FROM preference_optimization_runs WHERE hidden_at IS NULL "
            "ORDER BY created_at DESC, preference_optimization_run_id DESC LIMIT ?",
            (limit,),
        )
        projections = [_row_dict(cursor, row) for row in cursor.fetchall()]
        return [
            _preference_optimization_run_view(conn, projection)
            for projection in projections
            if projection is not None
        ]


def hide_preference_optimization_run(
    preference_optimization_run_id: str,
) -> dict[str, Any]:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        projection = _fetch_policy_row(
            conn,
            "preference_optimization_runs",
            "preference_optimization_run_id",
            preference_optimization_run_id,
        )
        if projection is None:
            raise KeyError(preference_optimization_run_id)
        if projection["hidden_at"] is not None:
            conn.commit()
            return _preference_optimization_run_view(conn, projection)
        active_owner = conn.execute(
            "SELECT 1 FROM ranking_policy_snapshots "
            "WHERE training_run_id = ? AND status = 'active' LIMIT 1",
            (projection["training_run_id"],),
        ).fetchone()
        if active_owner is not None:
            raise ValueError("active_policy_must_be_inactivated")
        hidden_at = _policy_now()
        conn.execute(
            "UPDATE preference_optimization_runs SET hidden_at = ?, hidden_by = ? "
            "WHERE preference_optimization_run_id = ?",
            (hidden_at, "local_workspace", preference_optimization_run_id),
        )
        event = build_process_event(
            process_type="optimization",
            process_id=str(projection["domain_id"]),
            operation="optimization_run_hidden",
            state="succeeded",
            level="info",
            message=f"Optimization run removed: {preference_optimization_run_id}",
            payload={
                "preference_optimization_run_id": preference_optimization_run_id,
                "hidden_at": hidden_at,
                "hidden_by": "local_workspace",
            },
            diagnostic_refs=[
                {
                    "kind": "preference_optimization_run",
                    "id": preference_optimization_run_id,
                }
            ],
            event_id=f"optimization:hidden:{preference_optimization_run_id}",
            recorded_at=datetime.datetime.fromisoformat(hidden_at),
        )
        _insert_process_event(
            conn,
            event,
            delivery_sinks=("langfuse",),
            raise_on_conflict=True,
        )
        conn.commit()
        hidden = _fetch_policy_row(
            conn,
            "preference_optimization_runs",
            "preference_optimization_run_id",
            preference_optimization_run_id,
        )
        if hidden is None:
            raise RuntimeError("hidden preference optimization run disappeared")
        return _preference_optimization_run_view(conn, hidden)


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
                events_loaded_through_sequence=event_watermark,
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


def _activate_ranking_policy_candidate_in_connection(
    conn: sqlite3.Connection,
    policy_snapshot_id: str,
    *,
    expected_parent_ref: str,
    acted_by: str,
    evidence_head_fingerprint: str | None,
    current_runtime_contract_fingerprint: str,
    current_compiler_policy_fingerprint: str,
    current_decision_learning_policy_fingerprint: str,
    current_optimizer_policy_fingerprint: str,
    current_activation_policy_fingerprint: str,
    mark_stale_on_conflict: bool,
) -> dict[str, Any]:
    candidate = _fetch_policy_row(
        conn, "ranking_policy_snapshots", "policy_snapshot_id", policy_snapshot_id
    )
    if candidate is None:
        raise KeyError(policy_snapshot_id)
    if candidate["status"] == "active":
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
    active_cursor = conn.execute(
        "SELECT * FROM ranking_policy_snapshots WHERE domain_id = ? AND status = 'active'",
        (candidate["domain_id"],),
    )
    active_rows = active_cursor.fetchall()
    if len(active_rows) > 1:
        raise ValueError("multiple active ranking policies")
    domain_active = _row_dict(active_cursor, active_rows[0]) if active_rows else None
    compatible_active = (
        domain_active
        if domain_active is not None
        and domain_active["runtime_contract_fingerprint"]
        == candidate["runtime_contract_fingerprint"]
        else None
    )
    current_parent = (
        f"learned:{compatible_active['policy_snapshot_id']}"
        if compatible_active is not None
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
        if mark_stale_on_conflict:
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'stale' "
                "WHERE policy_snapshot_id = ?",
                (policy_snapshot_id,),
            )
            _append_policy_event(
                conn,
                domain_id=str(candidate["domain_id"]),
                runtime_contract_fingerprint=str(
                    candidate["runtime_contract_fingerprint"]
                ),
                previous_snapshot_id=(
                    str(domain_active["policy_snapshot_id"])
                    if domain_active is not None
                    else None
                ),
                target_snapshot_id=policy_snapshot_id,
                action="stale",
                reason_code=stale_reason[0],
                expected_parent_ref=expected_parent_ref,
                evidence_head_fingerprint=evidence_head_fingerprint,
                acted_by=acted_by,
            )
        raise ValueError(stale_reason[1])
    if domain_active is not None:
        conn.execute(
            "UPDATE ranking_policy_snapshots SET status = 'retired' "
            "WHERE policy_snapshot_id = ?",
            (domain_active["policy_snapshot_id"],),
        )
        _append_policy_event(
            conn,
            domain_id=str(candidate["domain_id"]),
            runtime_contract_fingerprint=str(
                domain_active["runtime_contract_fingerprint"]
            ),
            previous_snapshot_id=str(domain_active["policy_snapshot_id"]),
            target_snapshot_id=policy_snapshot_id,
            action="retire",
            reason_code="superseded",
            expected_parent_ref=expected_parent_ref,
            evidence_head_fingerprint=evidence_head_fingerprint,
            acted_by=acted_by,
        )
    conn.execute(
        "UPDATE ranking_policy_snapshots SET status = 'active', activated_at = ? "
        "WHERE policy_snapshot_id = ?",
        (_policy_now(), policy_snapshot_id),
    )
    _append_policy_event(
        conn,
        domain_id=str(candidate["domain_id"]),
        runtime_contract_fingerprint=str(candidate["runtime_contract_fingerprint"]),
        previous_snapshot_id=(
            str(domain_active["policy_snapshot_id"])
            if domain_active is not None
            else None
        ),
        target_snapshot_id=policy_snapshot_id,
        action="activate",
        reason_code="manual_activation",
        expected_parent_ref=expected_parent_ref,
        evidence_head_fingerprint=evidence_head_fingerprint,
        acted_by=acted_by,
    )
    return _fetch_policy_row(
        conn, "ranking_policy_snapshots", "policy_snapshot_id", policy_snapshot_id
    ) or candidate


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
        try:
            result = _activate_ranking_policy_candidate_in_connection(
                conn,
                policy_snapshot_id,
                expected_parent_ref=expected_parent_ref,
                acted_by=acted_by,
                evidence_head_fingerprint=evidence_head_fingerprint,
                current_runtime_contract_fingerprint=current_runtime_contract_fingerprint,
                current_compiler_policy_fingerprint=current_compiler_policy_fingerprint,
                current_decision_learning_policy_fingerprint=(
                    current_decision_learning_policy_fingerprint
                ),
                current_optimizer_policy_fingerprint=current_optimizer_policy_fingerprint,
                current_activation_policy_fingerprint=current_activation_policy_fingerprint,
                mark_stale_on_conflict=True,
            )
            conn.commit()
            return result
        except ValueError:
            candidate = _fetch_policy_row(
                conn,
                "ranking_policy_snapshots",
                "policy_snapshot_id",
                policy_snapshot_id,
            )
            if candidate is not None and candidate["status"] == "stale":
                conn.commit()
            else:
                conn.rollback()
            raise


def activate_preference_optimization_run(
    preference_optimization_run_id: str,
    *,
    expected_parent_ref: str,
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
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            projection = _fetch_policy_row(
                conn,
                "preference_optimization_runs",
                "preference_optimization_run_id",
                preference_optimization_run_id,
            )
            if projection is None:
                raise KeyError(preference_optimization_run_id)
            if projection["hidden_at"] is not None:
                raise ValueError("optimization_run_hidden")
            policy_snapshot_id = projection.get("policy_snapshot_id")
            if policy_snapshot_id is None:
                raise ValueError("optimization_run_has_no_policy")
            _activate_ranking_policy_candidate_in_connection(
                conn,
                str(policy_snapshot_id),
                expected_parent_ref=expected_parent_ref,
                acted_by="local_workspace",
                evidence_head_fingerprint=evidence_head_fingerprint,
                current_runtime_contract_fingerprint=(
                    current_runtime_contract_fingerprint
                ),
                current_compiler_policy_fingerprint=(
                    current_compiler_policy_fingerprint
                ),
                current_decision_learning_policy_fingerprint=(
                    current_decision_learning_policy_fingerprint
                ),
                current_optimizer_policy_fingerprint=(
                    current_optimizer_policy_fingerprint
                ),
                current_activation_policy_fingerprint=(
                    current_activation_policy_fingerprint
                ),
                mark_stale_on_conflict=False,
            )
            conn.commit()
            current_projection = _fetch_policy_row(
                conn,
                "preference_optimization_runs",
                "preference_optimization_run_id",
                preference_optimization_run_id,
            )
            if current_projection is None:
                raise RuntimeError("activated preference optimization run disappeared")
            return _preference_optimization_run_view(conn, current_projection)
        except Exception:
            conn.rollback()
            raise


def inactivate_preference_optimization_run(
    preference_optimization_run_id: str,
    *,
    expected_active_snapshot_id: str,
) -> dict[str, Any]:
    db_path = Path(_local_sqlite_path())
    with _sqlite_connection(db_path) as conn:
        _ensure_local_preference_policy_tables(conn)
        conn.commit()
        conn.execute("BEGIN IMMEDIATE")
        try:
            projection = _fetch_policy_row(
                conn,
                "preference_optimization_runs",
                "preference_optimization_run_id",
                preference_optimization_run_id,
            )
            if projection is None:
                raise KeyError(preference_optimization_run_id)
            if projection["hidden_at"] is not None:
                raise ValueError("optimization_run_hidden")
            policy_snapshot_id = projection.get("policy_snapshot_id")
            if (
                policy_snapshot_id is None
                or str(policy_snapshot_id) != expected_active_snapshot_id
            ):
                raise ValueError("active snapshot changed")
            active = _fetch_policy_row(
                conn,
                "ranking_policy_snapshots",
                "policy_snapshot_id",
                expected_active_snapshot_id,
            )
            if active is None or active["status"] != "active":
                raise ValueError("active snapshot changed")
            domain_active = conn.execute(
                "SELECT policy_snapshot_id FROM ranking_policy_snapshots "
                "WHERE domain_id = ? AND status = 'active'",
                (active["domain_id"],),
            ).fetchall()
            if domain_active != [(expected_active_snapshot_id,)]:
                raise ValueError("active snapshot changed")
            conn.execute(
                "UPDATE ranking_policy_snapshots SET status = 'retired' "
                "WHERE policy_snapshot_id = ?",
                (expected_active_snapshot_id,),
            )
            _append_policy_event(
                conn,
                domain_id=str(active["domain_id"]),
                runtime_contract_fingerprint=str(
                    active["runtime_contract_fingerprint"]
                ),
                previous_snapshot_id=expected_active_snapshot_id,
                target_snapshot_id=None,
                action="rollback",
                reason_code="manual_inactivation",
                expected_parent_ref=f"learned:{expected_active_snapshot_id}",
                evidence_head_fingerprint=None,
                acted_by="local_workspace",
            )
            conn.commit()
            current_projection = _fetch_policy_row(
                conn,
                "preference_optimization_runs",
                "preference_optimization_run_id",
                preference_optimization_run_id,
            )
            if current_projection is None:
                raise RuntimeError("inactivated preference optimization run disappeared")
            return _preference_optimization_run_view(conn, current_projection)
        except Exception:
            conn.rollback()
            raise


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
    runtime_contract_fingerprint: str | None = None,
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
        snapshots = [
            payload
            for row in snapshots_cursor.fetchall()
            if (payload := _row_dict(snapshots_cursor, row)) is not None
        ]
        events_cursor = conn.execute(
            f"SELECT * FROM policy_activation_events WHERE domain_id = ? ORDER BY created_at {order}, activation_event_id {order}{limit_sql}",
            parameters,
        )
        events = [
            payload
            for row in events_cursor.fetchall()
            if (payload := _row_dict(events_cursor, row)) is not None
        ]
        training_cursor = conn.execute(
            f"SELECT * FROM inverse_training_runs WHERE domain_id = ? ORDER BY created_at {order}, training_run_id {order}{limit_sql}",
            parameters,
        )
        training_runs = [
            payload
            for row in training_cursor.fetchall()
            if (payload := _row_dict(training_cursor, row)) is not None
        ]
        domain_active = next(
            (row for row in snapshots if row["status"] == "active"), None
        )
        if domain_active is None and limit is not None:
            active_cursor = conn.execute(
                "SELECT * FROM ranking_policy_snapshots WHERE domain_id = ? AND status = 'active'",
                (domain_id,),
            )
            active_row = active_cursor.fetchone()
            domain_active = (
                _row_dict(active_cursor, active_row) if active_row is not None else None
            )
        compatible_active = (
            domain_active
            if domain_active is not None
            and runtime_contract_fingerprint is not None
            and domain_active["runtime_contract_fingerprint"]
            == runtime_contract_fingerprint
            else None
        )
        for snapshot in snapshots:
            snapshot["rollback_eligible"] = bool(
                domain_active is not None
                and snapshot["status"] == "retired"
                and snapshot["runtime_contract_fingerprint"]
                == domain_active["runtime_contract_fingerprint"]
            )
        return {
            "snapshots": snapshots,
            "events": events,
            "training_runs": training_runs,
            "active_snapshot": domain_active,
            "domain_active_snapshot": domain_active,
            "compatible_active_snapshot": compatible_active,
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
            strict_profile = bool(input_resource.get("strict_candidate_profile"))
            profile_id = str(input_resource.get("candidate_profile_id") or "").strip()
            if strict_profile:
                profile_row = conn.execute(
                    """SELECT cp.candidate_profile_id, cp.profile_name, cp.revision,
                              pr.profile_revision_id, pr.profile_json, pr.checksum
                       FROM candidate_profiles cp
                       JOIN candidate_profile_revisions pr
                         ON pr.candidate_profile_id = cp.candidate_profile_id
                       WHERE cp.candidate_profile_id = ?
                         AND cp.creation_status = 'succeeded'
                         AND cp.lifecycle = 'active'
                         AND pr.revision = cp.revision""",
                    (profile_id,),
                ).fetchone()
                if profile_row is None:
                    raise CandidateProfileUnavailableError("candidate_profile_unavailable")
                input_resource = {
                    **input_resource,
                    "candidate_profile_id": profile_row[0],
                    "candidate_profile_name": str(profile_row[1] or ""),
                    "candidate_profile_revision": int(profile_row[2]),
                    "candidate_profile_revision_id": str(profile_row[3]),
                    "candidate_profile_json": str(profile_row[4]),
                }

                from fitcv_cp.settings_schema import merge_and_validate_settings
                from fitcv_cp.settings_store import settings_revision

                settings_overrides: dict[str, Any] = {}
                for setting_key, setting_value_json in conn.execute(
                    "SELECT setting_key, setting_value_json FROM pipeline_settings ORDER BY rowid"
                ).fetchall():
                    try:
                        settings_overrides[str(setting_key)] = json.loads(setting_value_json)
                    except (TypeError, ValueError):
                        continue
                effective_settings = merge_and_validate_settings({}, current_settings=settings_overrides)
                active_bundle_row = conn.execute(
                    """SELECT br.bundle_revision_id, br.bundle_checksum, br.normalized_bundle_json
                       FROM synonym_policy_state ps
                       JOIN synonym_policy_bundle_revisions br
                         ON br.bundle_revision_id = ps.active_bundle_revision_id
                       WHERE ps.state_id = 1"""
                ).fetchone()
                active_bundle = (
                    json.loads(active_bundle_row[2])
                    if active_bundle_row is not None
                    else {"skills": {}, "domain": {}, "role_family": {}}
                )
                approved_projection = (
                    active_bundle
                    if bool(effective_settings["synonym_management.apply_approved_enabled"])
                    else {"skills": {}, "domain": {}, "role_family": {}}
                )
                run_config = _json_dict(run.effective_settings_json)
                run_config.update(effective_settings)
                run_config["skill_synonyms"] = approved_projection["skills"]
                run_config["domain_alias_map"] = approved_projection["domain"]
                run_config["role_family_alias_map"] = approved_projection["role_family"]
                run.effective_settings_json = json.dumps(run_config, ensure_ascii=False)
                bundle_snapshot = {
                    "normalized_bundle": active_bundle,
                    "approved_mapping_projection": approved_projection,
                }
                input_resource = {
                    **input_resource,
                    "settings_revision": settings_revision(effective_settings),
                    "settings_snapshot_json": json.dumps(effective_settings, ensure_ascii=False),
                    "synonym_policy_bundle_revision_id": active_bundle_row[0] if active_bundle_row else None,
                    "synonym_policy_bundle_checksum": active_bundle_row[1] if active_bundle_row else None,
                    "synonym_policy_bundle_snapshot_json": json.dumps(bundle_snapshot, ensure_ascii=False),
                }
            run.total_jobs = len(jobs)
            _write_normalized_run(conn, run, insert=True)
            jobs_json = str(input_resource.get("jobs_snapshot_json") or json.dumps(jobs))
            byte_length = input_resource.get("byte_length")
            if byte_length is None:
                byte_length = len(jobs_json.encode("utf-8"))
            sha256 = str(input_resource.get("sha256") or "").strip()
            if not sha256:
                sha256 = hashlib.sha256(jobs_json.encode("utf-8")).hexdigest()
            candidate_profile_revision_id = input_resource.get("candidate_profile_revision_id")
            candidate_profile_id = (
                input_resource.get("candidate_profile_id")
                if candidate_profile_revision_id
                else None
            )
            conn.execute(
                """
                INSERT INTO run_inputs (
                    run_id, original_filename, media_type, byte_length, sha256, record_count,
                    jobs_snapshot_json, jobs_manifest_json, candidate_profile_id,
                    candidate_profile_revision_id, candidate_profile_revision,
                    candidate_profile_name, candidate_profile_json, settings_revision,
                    settings_snapshot_json, synonym_policy_bundle_revision_id,
                    synonym_policy_bundle_checksum, synonym_policy_bundle_snapshot_json,
                    created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run.run_id,
                    str(input_resource.get("original_filename") or Path(run.jobs_path).name),
                    str(input_resource.get("media_type") or "application/json"),
                    int(byte_length),
                    sha256,
                    len(jobs),
                    jobs_json,
                    str(input_resource.get("jobs_manifest_json") or "{}"),
                    candidate_profile_id,
                    candidate_profile_revision_id,
                    input_resource.get("candidate_profile_revision"),
                    str(input_resource.get("candidate_profile_name") or ""),
                    str(input_resource.get("candidate_profile_json") or "{}"),
                    str(input_resource.get("settings_revision") or _settings_revision(run)),
                    str(input_resource.get("settings_snapshot_json") or "{}"),
                    input_resource.get("synonym_policy_bundle_revision_id"),
                    input_resource.get("synonym_policy_bundle_checksum"),
                    input_resource.get("synonym_policy_bundle_snapshot_json"),
                    run.created_at.isoformat(),
                ),
            )
            manifest = json.loads(str(input_resource.get("jobs_manifest_json") or "{}"))
            scan_sources = [source for source in manifest.get("sources", []) if isinstance(source, dict) and source.get("type") == "scan"]
            for ordinal, source in enumerate(scan_sources):
                conn.execute(
                    "INSERT INTO run_scan_inputs (run_id, scan_id, source_ordinal, scan_output_sha256) VALUES (?, ?, ?, ?)",
                    (run.run_id, str(source["scan_id"]), ordinal, str(source.get("sha256") or "")),
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
                "binary_response": {
                    "content": bytes(row["response_blob"]),
                    "media_type": str(row["response_media_type"]),
                    "filename": str(row["response_filename"]),
                    "checksum": str(row["response_checksum"]),
                } if row["response_blob"] is not None else None,
            }
        action_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO idempotent_actions (
                action_id, action_scope, idempotency_key, request_fingerprint,
                status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'queued', ?, ?)
            """,
            (action_id, scope, key, fingerprint, now, now),
        )
        conn.commit()
    return {
        "action_id": action_id,
        "status": "queued",
        "replayed": False,
        "response": None,
        "binary_response": None,
    }


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
            """
            INSERT INTO bookmarks (bookmark_id, run_id, run_job_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(run_job_id) DO UPDATE SET updated_at = excluded.updated_at
            """,
            (bookmark_id, job["run_id"], run_job_id, now, now),
        )
        bookmark_id = str(
            conn.execute(
                "SELECT bookmark_id FROM bookmarks WHERE run_job_id = ?", (run_job_id,)
            ).fetchone()[0]
        )
        conn.commit()
    return {"bookmark_id": bookmark_id, "run_job_id": run_job_id, "display_snapshot": snapshot}

def complete_idempotent_binary_action(
    action_id: str,
    content: bytes,
    *,
    media_type: str,
    filename: str,
) -> None:
    checksum = hashlib.sha256(content).hexdigest()
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.execute(
            """UPDATE idempotent_actions
               SET status='succeeded', response_json=NULL, response_blob=?,
                   response_media_type=?, response_filename=?, response_checksum=?, updated_at=?
               WHERE action_id=?""",
            (
                content,
                media_type,
                filename,
                checksum,
                datetime.datetime.now(datetime.timezone.utc).isoformat(),
                action_id,
            ),
        )
        conn.commit()


def clear_bookmark(run_job_id: str) -> dict[str, Any]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        cursor = conn.execute("DELETE FROM bookmarks WHERE run_job_id=?", (run_job_id,))
        conn.commit()
    return {"cleared": bool(cursor.rowcount)}


def list_bookmarks() -> list[dict[str, Any]]:
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT b.*, j.source_fingerprint, j.title, j.company, j.location, j.source_url
            FROM bookmarks AS b
            JOIN run_jobs AS j ON j.run_job_id = b.run_job_id
            ORDER BY b.created_at DESC, b.bookmark_id
            """
        ).fetchall()
    return [
        {
            **dict(row),
            "display_snapshot": {
                key: row[key] for key in ("title", "company", "location", "source_url")
            },
        }
        for row in rows
    ]

def _bookmark_filter_sql(
    *, search: str, stage: str | None, result: str | None
) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if search.strip():
        clauses.append("(j.title LIKE ? COLLATE NOCASE OR COALESCE(j.company, '') LIKE ? COLLATE NOCASE)")
        params.extend([f"%{search.strip()}%", f"%{search.strip()}%"])
    if stage:
        clauses.append(
            "EXISTS (SELECT 1 FROM run_job_stage_results sr WHERE sr.run_job_id = j.run_job_id AND sr.stage_id = ?)"
        )
        params.append(stage)
    if result:
        clauses.append(
            "EXISTS (SELECT 1 FROM run_job_stage_results sr WHERE sr.run_job_id = j.run_job_id AND sr.result_bucket = ?)"
        )
        params.append(result)
    return clauses, params

def query_bookmarks(
    *,
    search: str = "",
    stage: str | None = None,
    result: str | None = None,
    page: int = 1,
    page_size: int = 20,
    sort: str = "bookmarked_desc",
    database_path: Path | None = None,
) -> dict[str, Any]:
    if page_size not in {10, 20, 50}:
        raise ValueError("page_size must be 10, 20, or 50")
    if sort != "bookmarked_desc":
        raise ValueError("bookmark_sort_invalid")
    clauses, params = _bookmark_filter_sql(search=search, stage=stage, result=result)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        total = int(conn.execute(
            f"SELECT COUNT(*) FROM bookmarks b JOIN run_jobs j ON j.run_job_id=b.run_job_id {where}",
            params,
        ).fetchone()[0])
        rows = conn.execute(
            f"""SELECT b.bookmark_id, b.created_at AS bookmarked_at,
                       r.run_id, r.run_name, j.*
                FROM bookmarks b
                JOIN run_jobs j ON j.run_job_id=b.run_job_id
                JOIN pipeline_runs r ON r.run_id=b.run_id
                {where}
                ORDER BY b.created_at DESC, b.bookmark_id
                LIMIT ? OFFSET ?""",
            (*params, page_size, (max(1, page) - 1) * page_size),
        ).fetchall()
    items = [dict(row) for row in rows]
    for item in items:
        item["source_snapshot"] = json.loads(item.pop("source_snapshot_json"))
        item["skills"] = json.loads(item.pop("skills_json"))
    return {"items": items, "total": total, "page": max(1, page), "page_size": page_size}

def resolve_job_selection(
    run_job_ids: list[str],
    *,
    scope: str,
    run_id: str | None = None,
    search: str = "",
    stage: str | None = None,
    result: str | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    selected = list(dict.fromkeys(str(value).strip() for value in run_job_ids if str(value).strip()))
    if not selected:
        raise ValueError("selection_required")
    if len(selected) > 5000:
        raise ValueError("selection_too_large")
    clauses, params = _bookmark_filter_sql(search=search, stage=stage, result=result)
    if scope == "bookmarks":
        from_sql = "bookmarks b JOIN run_jobs j ON j.run_job_id=b.run_job_id"
    elif scope == "run_jobs" and run_id:
        from_sql = "run_jobs j"
        clauses.append("j.run_id = ?")
        params.append(run_id)
    else:
        raise ValueError("invalid_selection_scope")
    placeholders = ",".join("?" for _ in selected)
    clauses.append(f"j.run_job_id IN ({placeholders})")
    params.extend(selected)
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        matched = {
            str(row[0])
            for row in conn.execute(
                f"SELECT j.run_job_id FROM {from_sql} WHERE {' AND '.join(clauses)}",
                params,
            ).fetchall()
        }
    matched_ids = [value for value in selected if value in matched]
    excluded_ids = [value for value in selected if value not in matched]
    return {
        "selected_count": len(selected),
        "matched_count": len(matched_ids),
        "excluded_count": len(excluded_ids),
        "matched_run_job_ids": matched_ids,
        "excluded_run_job_ids": excluded_ids,
    }

def remove_bookmarks(
    run_job_ids: list[str],
    *,
    search: str = "",
    stage: str | None = None,
    result: str | None = None,
    database_path: Path | None = None,
) -> dict[str, Any]:
    path = database_path or Path(_local_sqlite_path())
    selection = resolve_job_selection(
        run_job_ids, scope="bookmarks", search=search, stage=stage, result=result,
        database_path=path,
    )
    matched = selection["matched_run_job_ids"]
    if matched:
        placeholders = ",".join("?" for _ in matched)
        with _sqlite_connection(path) as conn:
            conn.execute(f"DELETE FROM bookmarks WHERE run_job_id IN ({placeholders})", matched)
            conn.commit()
    return {**selection, "removed_count": len(matched)}

def list_selected_jobs(
    run_job_ids: list[str],
    *,
    bookmarks_only: bool = False,
    database_path: Path | None = None,
) -> list[dict[str, Any]]:
    ids = list(dict.fromkeys(run_job_ids))
    if not ids:
        return []
    placeholders = ",".join("?" for _ in ids)
    bookmark_join = "JOIN bookmarks b ON b.run_job_id=j.run_job_id" if bookmarks_only else ""
    path = database_path or Path(_local_sqlite_path())
    with _sqlite_connection(path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            f"""SELECT r.run_id, r.run_name, j.* FROM run_jobs j
                JOIN pipeline_runs r ON r.run_id=j.run_id
                {bookmark_join}
                WHERE j.run_job_id IN ({placeholders})""",
            ids,
        ).fetchall()
    by_id = {str(row["run_job_id"]): dict(row) for row in rows}
    return [by_id[value] for value in ids if value in by_id]


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


def preview_delete_archived_runs(run_ids: list[str]) -> dict[str, Any]:
    requested = list(dict.fromkeys(str(value).strip() for value in run_ids if str(value).strip()))
    if not requested:
        raise ValueError("selection_required")
    if len(requested) > 5000:
        raise ValueError("selection_too_large")
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        return _delete_archived_run_state(conn, requested)

def _delete_archived_run_state(
    conn: sqlite3.Connection,
    requested: list[str],
) -> dict[str, Any]:
    placeholders = ",".join("?" for _ in requested)
    rows = conn.execute(
        f"""SELECT r.run_id, r.archived_at,
                   COUNT(DISTINCT b.bookmark_id) AS bookmark_count,
                   COUNT(DISTINCT src.suggestion_id) AS synonym_source_count
            FROM pipeline_runs r
            LEFT JOIN bookmarks b ON b.run_id = r.run_id
            LEFT JOIN synonym_suggestion_sources src ON src.run_id = r.run_id
            WHERE r.run_id IN ({placeholders})
            GROUP BY r.run_id, r.archived_at""",
        requested,
    ).fetchall()
    by_id = {str(row["run_id"]): row for row in rows}
    eligible = [run_id for run_id in requested if run_id in by_id and by_id[run_id]["archived_at"]]
    blocked = [run_id for run_id in requested if run_id in by_id and not by_id[run_id]["archived_at"]]
    missing = [run_id for run_id in requested if run_id not in by_id]
    return {
        "requested_run_ids": requested,
        "eligible_run_ids": eligible,
        "blocked_run_ids": blocked,
        "missing_run_ids": missing,
        "bookmark_count": sum(int(by_id[run_id]["bookmark_count"]) for run_id in eligible),
        "state_tokens": [
            _policy_checksum({
                "run_id": run_id,
                "archived_at": by_id[run_id]["archived_at"],
                "bookmark_count": int(by_id[run_id]["bookmark_count"]),
                "synonym_source_count": int(by_id[run_id]["synonym_source_count"]),
            })
            for run_id in eligible
        ],
    }

def _cleanup_deleted_run_files(run_id: str) -> None:
    legacy_event_file = _local_event_history_file(run_id)
    legacy_event_file.unlink(missing_ok=True)
    journal_dir = _process_event_journal_dir("pipeline", run_id)
    if journal_dir.exists():
        shutil.rmtree(journal_dir)
    artifact_root = Path("artifacts").resolve()
    artifact_dir = (artifact_root / f"live_run_{run_id}").resolve()
    if artifact_dir.parent != artifact_root:
        raise OSError("run artifact path is outside artifact root")
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)

def delete_archived_runs(
    older_than_days: int | str,
    *_compat_args: Any,
    run_ids: list[str] | None = None,
    expected_state_tokens: list[str] | None = None,
    **_compat_kwargs: Any,
) -> dict[str, Any]:
    cutoff = None
    if older_than_days != "all":
        cutoff = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=int(older_than_days))
    requested = list(dict.fromkeys(str(value).strip() for value in (run_ids or []) if str(value).strip()))
    with _sqlite_connection(Path(_local_sqlite_path())) as conn:
        conn.row_factory = sqlite3.Row
        _ensure_control_plane_schema(conn)
        conn.execute("BEGIN IMMEDIATE")
        state = _delete_archived_run_state(conn, requested) if requested else None
        if state is not None and expected_state_tokens is not None:
            if (
                state["blocked_run_ids"]
                or state["missing_run_ids"]
                or state["state_tokens"] != list(expected_state_tokens)
            ):
                conn.rollback()
                raise ValueError("delete_preview_stale")
        if requested:
            rows = conn.execute(
                "SELECT run_id, archived_at FROM pipeline_runs WHERE run_id IN ({})".format(
                    ",".join("?" for _ in requested)
                ),
                requested,
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT run_id, archived_at FROM pipeline_runs WHERE archived_at IS NOT NULL"
            ).fetchall()
        eligible = [
            str(row["run_id"])
            for row in rows
            if row["archived_at"]
            and (cutoff is None or datetime.datetime.fromisoformat(str(row["archived_at"])) <= cutoff)
        ]
        if requested:
            found = {str(row["run_id"]) for row in rows}
            not_found = [value for value in requested if value not in found]
            blocked = [value for value in requested if value in found and value not in eligible]
            if not_found or blocked:
                conn.rollback()
                return {
                    "requested_run_ids": requested,
                    "deleted_count": 0,
                    "deleted_run_ids": [],
                    "not_found_run_ids": not_found,
                    "blocked_run_ids": blocked,
                }
        bookmark_count = 0
        if eligible:
            placeholders = ",".join("?" for _ in eligible)
            bookmark_count = int(conn.execute(
                f"SELECT COUNT(*) FROM bookmarks WHERE run_id IN ({placeholders})", eligible
            ).fetchone()[0])
        conn.executemany("DELETE FROM pipeline_runs WHERE run_id=?", [(value,) for value in eligible])
        deleted_suggestions = conn.execute(
            """DELETE FROM synonym_suggestions
               WHERE review_status IN ('pending', 'declined')
                 AND NOT EXISTS (
                   SELECT 1 FROM synonym_suggestion_sources src
                   WHERE src.suggestion_id = synonym_suggestions.suggestion_id
                 )"""
        ).rowcount
        conn.commit()
    cleanup_failed_run_ids: list[str] = []
    for run_id in eligible:
        try:
            _cleanup_deleted_run_files(run_id)
        except OSError:
            cleanup_failed_run_ids.append(run_id)
    return {
        "requested_run_ids": requested,
        "deleted_count": len(eligible),
        "deleted_run_ids": eligible,
        "not_found_run_ids": [],
        "blocked_run_ids": [],
        "deleted_bookmark_count": bookmark_count,
        "deleted_synonym_suggestion_count": deleted_suggestions,
        "filesystem_cleanup_failed_run_ids": cleanup_failed_run_ids,
        "filesystem_cleanup_error_code": (
            "run_files_cleanup_failed" if cleanup_failed_run_ids else None
        ),
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
            """SELECT j.run_job_id, j.source_snapshot_json,
                      CASE WHEN b.bookmark_id IS NULL THEN 0 ELSE 1 END AS bookmarked
               FROM run_jobs j
               LEFT JOIN bookmarks b ON b.run_job_id=j.run_job_id
               WHERE j.run_id=? ORDER BY j.title COLLATE NOCASE, j.run_job_id""",
            (run_id,),
        ).fetchall()
    return [
        json.loads(str(row["source_snapshot_json"]))
        | {"run_job_id": row["run_job_id"], "bookmarked": bool(row["bookmarked"])}
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

