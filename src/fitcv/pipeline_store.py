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
                  PRIMARY KEY (run_id, job_identity)
                )
                """
            )
            conn.executemany(
                """
                INSERT OR REPLACE INTO shortlist_admission_ledger(
                  run_id, job_identity, job_url, fusion_rank, vector_rank,
                  vector_score, lexical_rank, lexical_score, cutoff,
                  requested_strategy, effective_strategy, fusion_fingerprint,
                  admission_reason, exclusion_reason, raw_hit_present, admitted,
                  captured_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    )
                    for row in rows
                ],
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

    def store_final_ranking(
        self,
        ranked_jobs: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> None:
        self.store_final_ranking_fn(ranked_jobs, config)

    def store_cv_version(self, version: dict[str, Any], config: dict[str, Any]) -> None:
        self.store_cv_version_fn(version, config)
