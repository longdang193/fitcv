import json
import sqlite3

from fitcv.pipeline_store import (
    PipelineStore,
    persist_shortlist_admission_ledger,
    update_shortlist_admission_ledger_scores,
)


def test_pipeline_store_delegates_to_injected_functions() -> None:
    captured: dict[str, object] = {}

    def _lookup(normalized_jobs, config, *, raw_job_fingerprints, enrich_contract_fingerprint):
        captured["lookup_jobs"] = normalized_jobs
        captured["lookup_fp"] = raw_job_fingerprints
        captured["lookup_contract"] = enrich_contract_fingerprint
        return {"https://example.com/job": {"job_url": "https://example.com/job"}}

    def _load_raw(rows, config):
        captured["raw_rows"] = rows

    def _load_candidate(profile, config):
        captured["candidate_profile"] = profile

    def _load(rows, config):
        captured["load_rows"] = rows

    def _load_run(rows, run_id, config):
        captured["load_run_rows"] = rows
        captured["run_id"] = run_id

    def _store_filter(result, run_id, config):
        captured["filter_result"] = result
        captured["filter_run_id"] = run_id

    def _store_shortlist(rows, config):
        captured["shortlist_rows"] = rows

    def _store_ranking(rows, config):
        captured["ranking_rows"] = rows

    def _embed_jobs(rows, config):
        captured["embed_rows"] = rows

    def _store_version(version, config):
        captured["cv_version"] = version

    store = PipelineStore(
        load_raw_jobs_fn=_load_raw,
        load_candidate_profile_fn=_load_candidate,
        lookup_reusable_structured_jobs_fn=_lookup,
        load_structured_jobs_fn=_load,
        load_run_structured_jobs_fn=_load_run,
        store_filter_results_fn=_store_filter,
        embed_and_store_jobs_fn=_embed_jobs,
        store_shortlist_fn=_store_shortlist,
        store_final_ranking_fn=_store_ranking,
        store_cv_version_fn=_store_version,
    )

    rows = store.lookup_reusable_structured_jobs(
        [{"job_url": "https://example.com/job"}],
        {"gcp_project": "p"},
        raw_job_fingerprints={"https://example.com/job": "fp1"},
        enrich_contract_fingerprint="contract1",
    )
    store.load_structured_jobs([{"job_url": "https://example.com/job"}], {})
    store.load_run_structured_jobs([{"job_url": "https://example.com/job"}], "run-1", {})
    store.load_raw_jobs([{"job_url": "https://example.com/job"}], {})
    store.load_candidate_profile({"name": "Candidate"}, {})
    store.store_filter_results({"passed": ["https://example.com/job"], "rejected": []}, "run-1", {})
    store.embed_and_store_jobs([{"job_url": "https://example.com/job"}], {})
    store.store_shortlist([{"job_url": "https://example.com/job", "vector_rank": 1, "vector_similarity": 0.9}], {})
    store.store_final_ranking([{"job_url": "https://example.com/job", "final_rank": 1, "final_score": 0.8}], {})
    store.store_cv_version({"version_id": "v1"}, {})

    assert "https://example.com/job" in rows
    assert captured["run_id"] == "run-1"
    assert captured["filter_run_id"] == "run-1"
    assert captured["candidate_profile"] == {"name": "Candidate"}
    assert captured["cv_version"] == {"version_id": "v1"}


def test_shortlist_admission_ledger_migrates_and_round_trips_score_facts(
    monkeypatch,
    tmp_path,
) -> None:
    sqlite_path = tmp_path / "pipeline.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    with sqlite3.connect(sqlite_path) as conn:
        conn.execute(
            """
            CREATE TABLE shortlist_admission_ledger (
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
        conn.commit()

    diagnostics = {
        "requested_strategy": "hybrid_rrf",
        "effective_strategy": "hybrid_rrf",
        "fusion_fingerprint": "fusion-1",
    }
    row = {
        "identity": "job-1",
        "job_url": "https://example.com/job-1",
        "shortlist_status": "shortlist_admitted",
        "raw_hit_present": True,
        "admission_order": 0,
        "vector_rank": 1,
        "vector_similarity": 0.91,
        "lexical_rank": 2,
        "lexical_score": 0.82,
        "source_provider": "indeed",
        "source_job_id": "indeed-1",
        "raw_job_fingerprint": "raw-1",
        "description_quality": "full",
        "description_source": "description",
        "description_complete": True,
        "description_source_checksum": "checksum-1",
        "description_source_length": 2400,
        "description_boundary": {"start": 0, "end": 2400},
        "enrich_reuse_status": "fresh_compute",
        "ranking_input_diagnostics": {
            "selected_evidence_ids": ["project-1"],
            "model_visible_evidence_ids": [],
            "mandatory_omissions": {},
            "canonical_checksums": {"languages": "abc"},
            "request_char_count": 4200,
            "request_within_budget": True,
        },
    }

    persist_shortlist_admission_ledger([row], diagnostics, "run-1", {"pipeline": {"vector_search_top_n": 50}})
    update_shortlist_admission_ledger_scores(
        [
            {
                "identity": "job-1",
                "score_status": "valid",
                "failure_code": None,
                "ai_score": 0.87,
                "baseline_rank": 1,
                "ranking_input_diagnostics": row["ranking_input_diagnostics"],
            }
        ],
        None,
        "run-1",
    )

    with sqlite3.connect(sqlite_path) as conn:
        columns = {str(item[1]) for item in conn.execute("PRAGMA table_info(shortlist_admission_ledger)")}
        stored = conn.execute(
            """
            SELECT score_status, score_value, final_rank,
                   selected_evidence_ids_json, model_visible_evidence_ids_json, mandatory_omissions_json,
                   canonical_checksums_json, request_char_count, request_within_budget,
                   source_provider, source_job_id, raw_job_fingerprint,
                   description_quality, description_source, description_complete,
                   description_source_checksum, description_source_length,
                   description_boundary_json, enrichment_trust, enrich_reuse_status
            FROM shortlist_admission_ledger
            WHERE run_id = 'run-1' AND job_identity = 'job-1'
            """
        ).fetchone()

    assert {"score_status", "failure_code", "selected_evidence_ids_json", "request_within_budget"} <= columns
    assert stored == (
        "valid",
        0.87,
        1,
        json.dumps(["project-1"], sort_keys=True),
        json.dumps([], sort_keys=True),
        json.dumps({}, sort_keys=True),
        json.dumps({"languages": "abc"}, sort_keys=True),
        4200,
        1,
        "indeed",
        "indeed-1",
        "raw-1",
        "full",
        "description",
        1,
        "checksum-1",
        2400,
        json.dumps({"start": 0, "end": 2400}, sort_keys=True),
        "trusted",
        "fresh_compute",
    )


def test_shortlist_admission_ledger_persists_scorer_rejection_diagnostics(
    monkeypatch,
    tmp_path,
) -> None:
    from fitcv.ai_score import build_ranking_job_input, run_ai_scoring

    sqlite_path = tmp_path / "pipeline.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    ranking_input = build_ranking_job_input(
        {"enrich_reuse_status": "enrichment_fallback", "description": "Requirements: German C1"},
        {
            "skills": [],
            "_projected_evidence_pool": [{"evidence_id": "project-1", "kind": "project", "title": "Project"}],
        },
    )
    scored = run_ai_scoring(
        [{"job_url": "https://example.com/job", "run_job_id": "job-1", "ranking_input": ranking_input}],
        "candidate",
        {},
    )[0]
    row = {
        "identity": "run:job-1",
        "job_url": "https://example.com/job",
        "shortlist_status": "shortlist_admitted",
        "raw_hit_present": True,
        "admission_order": 0,
        "ranking_input_diagnostics": scored["ranking_input_diagnostics"],
    }

    persist_shortlist_admission_ledger([row], {}, "run-1", {"pipeline": {"vector_search_top_n": 50}})
    update_shortlist_admission_ledger_scores([scored], {"rows": [row]}, "run-1")

    with sqlite3.connect(sqlite_path) as conn:
        stored = conn.execute(
            """
            SELECT score_status, failure_code, selected_evidence_ids_json,
                   mandatory_omissions_json, mandatory_core_complete,
                   model_visible_evidence_ids_json
            FROM shortlist_admission_ledger
            WHERE run_id = 'run-1' AND job_identity = 'run:job-1'
            """
        ).fetchone()

    assert stored == (
        "unscored",
        "needs_enrichment",
        json.dumps(["project-1"], sort_keys=True),
        json.dumps({"candidate_certifications": 0, "candidate_employment": 0, "candidate_education": 0, "candidate_languages": 0, "candidate_mandatory_clauses": 0, "candidate_required_skills": 0, "job_enrichment_fallback": 1, "job_language_requirements": 0, "job_mandatory_clauses": 0, "job_required_skills": 0, "job_technology_requirements": 0}, sort_keys=True),
        0,
        json.dumps([], sort_keys=True),
    )


def test_shortlist_score_updates_use_stable_identity_when_urls_collide(
    monkeypatch,
    tmp_path,
) -> None:
    sqlite_path = tmp_path / "pipeline.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    rows = [
        {
            "identity": "run:job-1",
            "run_job_id": "job-1",
            "job_url": "https://example.com/shared",
            "shortlist_status": "shortlist_admitted",
            "raw_hit_present": True,
            "admission_order": 0,
        },
        {
            "identity": "run:job-2",
            "run_job_id": "job-2",
            "job_url": "https://example.com/shared",
            "shortlist_status": "shortlist_admitted",
            "raw_hit_present": True,
            "admission_order": 1,
        },
    ]
    persist_shortlist_admission_ledger(
        rows,
        {},
        "run-1",
        {"pipeline": {"vector_search_top_n": 50}},
    )

    update_shortlist_admission_ledger_scores(
        [
            {"run_job_id": "job-1", "job_url": "https://example.com/shared", "ai_score": 0.9, "score_status": "valid", "baseline_rank": 1},
            {"run_job_id": "job-2", "job_url": "https://example.com/shared", "ai_score": 0.3, "score_status": "valid", "baseline_rank": 2},
        ],
        {"rows": rows},
        "run-1",
    )

    with sqlite3.connect(sqlite_path) as conn:
        stored = conn.execute(
            """
            SELECT job_identity, score_value, final_rank
            FROM shortlist_admission_ledger
            WHERE run_id = 'run-1'
            ORDER BY job_identity
            """
        ).fetchall()

    assert stored == [("run:job-1", 0.9, 1), ("run:job-2", 0.3, 2)]


def test_shortlist_score_updates_skip_ambiguous_url_only_ranked_rows(
    monkeypatch,
    tmp_path,
) -> None:
    sqlite_path = tmp_path / "pipeline.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_path))
    rows = [
        {"identity": "run:job-1", "run_job_id": "job-1", "job_url": "https://example.com/shared", "shortlist_status": "shortlist_admitted", "raw_hit_present": True, "admission_order": 0},
        {"identity": "run:job-2", "run_job_id": "job-2", "job_url": "https://example.com/shared", "shortlist_status": "shortlist_admitted", "raw_hit_present": True, "admission_order": 1},
    ]
    persist_shortlist_admission_ledger(rows, {}, "run-1", {"pipeline": {"vector_search_top_n": 50}})

    update_shortlist_admission_ledger_scores(
        [{"identity": "url:https://example.com/shared", "job_url": "https://example.com/shared", "ai_score": 0.9, "score_status": "valid", "baseline_rank": 1}],
        {"rows": rows},
        "run-1",
    )

    with sqlite3.connect(sqlite_path) as conn:
        stored = conn.execute(
            "SELECT job_identity, score_value FROM shortlist_admission_ledger WHERE run_id = 'run-1' ORDER BY job_identity"
        ).fetchall()

    assert stored == [("run:job-1", None), ("run:job-2", None)]
