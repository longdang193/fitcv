"""@meta
name: pipeline_store
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.pipeline_store.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from dataclasses import dataclass
from typing import Any, Callable

from fitcv.persistence import sqlite_connection
from fitcv.pipeline_stages.common import job_identity_index_keys, primary_job_identity_key
from fitcv.shortlist_runtime import configure_sqlite_connection, run_sqlite_io_retry, sqlite_path


def persist_shortlist_admission_ledger(
    rows: list[dict[str, Any]],
    diagnostics: dict[str, Any],
    run_id: str,
    config: dict[str, Any],
) -> None:
    """Persist complete per-job admission facts outside bounded artifacts."""
    if not rows:
        return
    captured_at = datetime.now(tz=timezone.utc).isoformat()
    fusion_fingerprint = str(diagnostics.get("fusion_fingerprint") or "")
    effective_strategy = str(diagnostics.get("effective_strategy") or "")
    cutoff = int((config.get("pipeline") or {}).get("vector_search_top_n") or 50)

    def _write() -> None:
        with sqlite_connection(sqlite_path(), timeout=30) as conn:
            configure_sqlite_connection(conn)
            _ensure_shortlist_admission_ledger(conn)
            conn.executemany(
                """
                INSERT OR REPLACE INTO shortlist_admission_ledger(
                  run_id, job_identity, job_url, fusion_rank, vector_rank,
                  vector_score, lexical_rank, lexical_score, cutoff,
                  requested_strategy, effective_strategy, fusion_fingerprint,
                  admission_reason, exclusion_reason, raw_hit_present, admitted,
                  captured_at, score_status, failure_code, score_value, final_rank,
                  ranking_input_diagnostics_json, selected_evidence_ids_json,
                  mandatory_omissions_json, canonical_checksums_json,
                  request_char_count, request_within_budget
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(run_id),
                        str(row.get("identity") or row.get("job_url") or ""),
                        str(row.get("job_url") or ""),
                        row.get("admission_order") + 1 if row.get("admission_order") is not None else None,
                        row.get("vector_rank"),
                        row.get("vector_similarity"),
                        row.get("lexical_rank"),
                        row.get("lexical_score"),
                        cutoff,
                        row.get("requested_strategy") or diagnostics.get("requested_strategy"),
                        row.get("effective_strategy") or effective_strategy,
                        row.get("fusion_fingerprint") or fusion_fingerprint,
                        row.get("admission_reason"),
                        row.get("exclusion_reason"),
                        int(bool(row.get("raw_hit_present"))),
                        int(row.get("shortlist_status") == "shortlist_admitted"),
                        captured_at,
                        row.get("score_status"),
                        row.get("failure_code"),
                        row.get("score_value"),
                        row.get("final_rank"),
                        json.dumps(row.get("ranking_input_diagnostics") or {}, sort_keys=True),
                        json.dumps(
                            (row.get("ranking_input_diagnostics") or {}).get("selected_evidence_ids") or [],
                            sort_keys=True,
                        ),
                        json.dumps(
                            (row.get("ranking_input_diagnostics") or {}).get("mandatory_omissions") or {},
                            sort_keys=True,
                        ),
                        json.dumps(
                            (row.get("ranking_input_diagnostics") or {}).get("canonical_checksums") or {},
                            sort_keys=True,
                        ),
                        (row.get("ranking_input_diagnostics") or {}).get("request_char_count"),
                        int(bool((row.get("ranking_input_diagnostics") or {}).get("request_within_budget")))
                        if (row.get("ranking_input_diagnostics") or {}).get("request_within_budget") is not None
                        else None,
                    )
                    for row in rows
                ],
            )
            conn.commit()

    run_sqlite_io_retry(_write)


def _ensure_shortlist_admission_ledger(conn: Any) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS shortlist_admission_ledger (
          run_id TEXT NOT NULL,
          job_identity TEXT NOT NULL,
          job_url TEXT NOT NULL,
          fusion_rank INTEGER,
          vector_rank INTEGER,
          vector_score REAL,
          lexical_rank INTEGER,
          lexical_score REAL,
          cutoff INTEGER NOT NULL,
          requested_strategy TEXT,
          effective_strategy TEXT,
          fusion_fingerprint TEXT,
          admission_reason TEXT,
          exclusion_reason TEXT,
          raw_hit_present INTEGER NOT NULL,
          admitted INTEGER NOT NULL,
          captured_at TEXT NOT NULL,
          score_status TEXT,
          failure_code TEXT,
          score_value REAL,
          final_rank INTEGER,
          ranking_input_diagnostics_json TEXT,
          selected_evidence_ids_json TEXT,
          mandatory_omissions_json TEXT,
          canonical_checksums_json TEXT,
          request_char_count INTEGER,
          request_within_budget INTEGER,
          PRIMARY KEY (run_id, job_identity)
        )
        """
    )
    existing = {str(row[1]) for row in conn.execute("PRAGMA table_info(shortlist_admission_ledger)").fetchall()}
    columns = {
        "score_status": "TEXT",
        "failure_code": "TEXT",
        "score_value": "REAL",
        "final_rank": "INTEGER",
        "ranking_input_diagnostics_json": "TEXT",
        "selected_evidence_ids_json": "TEXT",
        "mandatory_omissions_json": "TEXT",
        "canonical_checksums_json": "TEXT",
        "request_char_count": "INTEGER",
        "request_within_budget": "INTEGER",
    }
    for name, sql_type in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE shortlist_admission_ledger ADD COLUMN {name} {sql_type}")


def update_shortlist_admission_ledger_scores(
    ranked_rows: list[dict[str, Any]],
    ranking_manifest: dict[str, Any] | None,
    run_id: str,
) -> None:
    manifest_rows: dict[str, dict[str, Any]] = {}
    manifest_by_url: dict[str, dict[str, Any] | None] = {}
    for row in list((ranking_manifest or {}).get("rows") or []):
        if not isinstance(row, dict):
            continue
        identity = str(row.get("identity") or "").strip()
        identity_keys = [identity, *job_identity_index_keys(row)]
        for key in identity_keys:
            if key and key not in manifest_rows:
                manifest_rows[key] = row
        job_url = str(row.get("job_url") or "").strip()
        if job_url:
            if job_url in manifest_by_url and manifest_by_url[job_url] is not row:
                manifest_by_url[job_url] = None
            else:
                manifest_by_url[job_url] = row

    def _write() -> None:
        with sqlite_connection(sqlite_path(), timeout=30) as conn:
            configure_sqlite_connection(conn)
            _ensure_shortlist_admission_ledger(conn)
            for final_rank, ranked in enumerate(ranked_rows, start=1):
                ranked_identity = str(ranked.get("identity") or "").strip()
                identity_keys = [ranked_identity, *job_identity_index_keys(ranked)]
                manifest = next(
                    (manifest_rows[key] for key in identity_keys if key and key in manifest_rows),
                    None,
                )
                if manifest is None:
                    job_url = str(ranked.get("job_url") or "").strip()
                    manifest = manifest_by_url.get(job_url)
                if manifest is None and not ranked_identity:
                    continue
                manifest = manifest or {}
                identity = str(
                    manifest.get("identity")
                    or primary_job_identity_key(manifest)
                    or ranked_identity
                    or primary_job_identity_key(ranked)
                    or manifest.get("job_url")
                    or ranked.get("job_url")
                    or ""
                ).strip()
                if not identity:
                    continue
                diagnostics = dict(
                    ranked.get("ranking_input_diagnostics")
                    or manifest.get("ranking_input_diagnostics")
                    or {}
                )
                persisted_final_rank = (
                    ranked.get("final_rank")
                    or ranked.get("personalized_rank")
                    or ranked.get("baseline_rank")
                )
                conn.execute(
                    """
                    UPDATE shortlist_admission_ledger
                    SET score_status = ?, failure_code = ?, score_value = ?, final_rank = ?,
                        ranking_input_diagnostics_json = ?, selected_evidence_ids_json = ?,
                        mandatory_omissions_json = ?, canonical_checksums_json = ?,
                        request_char_count = ?, request_within_budget = ?
                    WHERE run_id = ? AND job_identity = ?
                    """,
                    (
                        ranked.get("score_status"),
                        ranked.get("failure_code"),
                        ranked.get("ai_score"),
                        persisted_final_rank,
                        json.dumps(diagnostics, sort_keys=True),
                        json.dumps(diagnostics.get("selected_evidence_ids") or [], sort_keys=True),
                        json.dumps(diagnostics.get("mandatory_omissions") or {}, sort_keys=True),
                        json.dumps(diagnostics.get("canonical_checksums") or {}, sort_keys=True),
                        diagnostics.get("request_char_count"),
                        int(bool(diagnostics.get("request_within_budget")))
                        if diagnostics.get("request_within_budget") is not None
                        else None,
                        str(run_id),
                        identity,
                    ),
                )
            conn.commit()

    run_sqlite_io_retry(_write)


@dataclass
class PipelineStore:
    load_raw_jobs_fn: Callable[..., None]
    load_candidate_profile_fn: Callable[..., None]
    lookup_reusable_structured_jobs_fn: Callable[..., dict[str, dict[str, Any]]]
    load_structured_jobs_fn: Callable[..., None]
    load_run_structured_jobs_fn: Callable[..., None]
    store_filter_results_fn: Callable[..., None]
    embed_and_store_jobs_fn: Callable[..., None]
    store_shortlist_fn: Callable[..., None]
    store_final_ranking_fn: Callable[..., None]
    store_cv_version_fn: Callable[..., None]

    def load_raw_jobs(self, raw_rows: list[dict[str, Any]], config: dict[str, Any]) -> None:
        self.load_raw_jobs_fn(raw_rows, config)

    def load_candidate_profile(self, profile: dict[str, Any], config: dict[str, Any]) -> None:
        self.load_candidate_profile_fn(profile, config)

    def lookup_reusable_structured_jobs(
        self,
        normalized_jobs: list[dict[str, Any]],
        config: dict[str, Any],
        *,
        raw_job_fingerprints: dict[str, str],
        enrich_contract_fingerprint: str,
    ) -> dict[str, dict[str, Any]]:
        return self.lookup_reusable_structured_jobs_fn(
            normalized_jobs,
            config,
            raw_job_fingerprints=raw_job_fingerprints,
            enrich_contract_fingerprint=enrich_contract_fingerprint,
        )

    def load_structured_jobs(
        self,
        rows: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> None:
        self.load_structured_jobs_fn(rows, config)

    def load_run_structured_jobs(
        self,
        rows: list[dict[str, Any]],
        run_id: str,
        config: dict[str, Any],
    ) -> None:
        self.load_run_structured_jobs_fn(rows, run_id, config)

    def store_filter_results(
        self,
        result: dict[str, list[Any]],
        run_id: str,
        config: dict[str, Any],
    ) -> None:
        self.store_filter_results_fn(result, run_id, config)

    def embed_and_store_jobs(
        self,
        jobs: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> None:
        self.embed_and_store_jobs_fn(jobs, config)

    def store_shortlist(
        self,
        shortlist: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> None:
        self.store_shortlist_fn(shortlist, config)

    def store_shortlist_admission_ledger(
        self,
        rows: list[dict[str, Any]],
        diagnostics: dict[str, Any],
        run_id: str,
        config: dict[str, Any],
    ) -> None:
        persist_shortlist_admission_ledger(rows, diagnostics, run_id, config)

    def update_shortlist_admission_ledger_scores(
        self,
        ranked_rows: list[dict[str, Any]],
        ranking_manifest: dict[str, Any] | None,
        run_id: str,
    ) -> None:
        update_shortlist_admission_ledger_scores(ranked_rows, ranking_manifest, run_id)

    def store_final_ranking(
        self,
        ranked_jobs: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> None:
        self.store_final_ranking_fn(ranked_jobs, config)

    def store_cv_version(self, version: dict[str, Any], config: dict[str, Any]) -> None:
        self.store_cv_version_fn(version, config)
