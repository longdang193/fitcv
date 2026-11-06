"""Tests for fitcv.vector_search — all pure unit tests (no cloud calls)."""

import json
import sqlite3
from pathlib import Path
import pytest
from unittest.mock import patch
from fitcv.candidate import converge_candidate_profile_for_runtime, load_profile_json_text
from fitcv.embeddings import build_embedding_contract_fingerprint
from fitcv.vector_search import (
    _lexical_search_result,
    _hybrid_search_result,
    _dedupe_shortlist_rows,
    _technology_overlap,
    build_candidate_query_components,
    build_candidate_query_embedding_contract_fingerprint,
    build_candidate_query_signature_record,
    build_candidate_query_text,
    resolve_candidate_query_embedding,
    run_vector_search,
)


_CANDIDATE_QUERY_RECORD_KEYS = {
    "text",
    "components",
    "embedding",
    "candidate_query_signature",
    "candidate_query_contract_fingerprint",
    "candidate_query_reuse_status",
    "embedding_backend_id",
}


# ── build_candidate_query_text ────────────────────────────────────────────────

def test_build_candidate_query_text_includes_headline() -> None:
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {"domains": ["data_engineering"]},
    }
    text = build_candidate_query_text(profile)
    assert "Data Engineer" in text


def test_build_candidate_query_text_includes_skills() -> None:
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "Python"}, {"name": "BigQuery"}],
        "preferences": {"domains": []},
    }
    text = build_candidate_query_text(profile)
    assert "SQL" in text
    assert "Python" in text


def test_build_candidate_query_text_uses_flattened_skills_from_experiences_and_projects() -> None:
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "experiences": [
            {
                "role": "BI Analyst",
                "bullets": [
                    {"text": "Built dashboards", "skills": ["Power BI", "Looker"]},
                ],
            }
        ],
        "projects": [
            {"name": "Warehouse Migration", "skills": ["BigQuery", "dbt"]},
        ],
        "preferences": {"domains": []},
    }

    text = build_candidate_query_text(profile, {"vector_max_candidate_skills": 10})

    assert "Power BI" in text
    assert "Looker" in text
    assert "BigQuery" in text
    assert "dbt" in text


def test_build_candidate_query_components_include_role_family_and_domain_hints() -> None:
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {
            "target_role": "Data Analyst",
            "domains": ["banking"],
            "role_families": ["analytics"],
        },
        "experiences": [
            {
                "role": "Business Intelligence Analyst",
                "role_family": "analytics",
                "domain_tags": ["retail_banking"],
            },
            {
                "role": "Data Scientist",
                "domain_tags": ["fraud_detection"],
            },
        ],
        "projects": [
            {"name": "Fraud Dashboard", "domain_tags": ["fintech"]},
        ],
    }

    components = build_candidate_query_components(profile, {"vector_max_candidate_skills": 10})

    assert components["target_role"] == "Data Analyst"
    assert components["recent_roles"] == ["Business Intelligence Analyst", "Data Scientist"]
    assert components["role_family_hints"] == ["analytics", "data_science"]
    assert components["domain_hints"] == ["banking", "retail_banking", "fraud_detection", "fintech"]


def test_build_candidate_query_components_preserve_all_declared_role_families_and_project_evidence() -> None:
    profile = {
        "preferences": {
            "role_families": ["analytics", "data_engineering", "ml_engineering", "platform"],
        },
        "projects": [{
            "name": "Fraud Detection Platform",
            "business_value": "Reduced false positives for risk operations",
            "highlights": ["Built streaming feature pipeline"],
        }],
    }

    components = build_candidate_query_components(profile)
    text = build_candidate_query_text(profile)

    assert components["role_families"] == ["analytics", "data_engineering", "ml_engineering", "platform"]
    assert components["project_evidence_hints"] == [
        "Fraud Detection Platform",
        "Reduced false positives for risk operations",
        "Built streaming feature pipeline",
    ]
    assert "Built streaming feature pipeline" in text


def test_build_candidate_query_components_bound_skill_count() -> None:
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "experiences": [
            {
                "role": "Data Engineer",
                "bullets": [
                    {"skills": ["BigQuery", "dbt", "Airflow"]},
                ],
            }
        ],
        "projects": [{"skills": ["Looker", "Power BI"]}],
        "preferences": {"domains": []},
    }

    components = build_candidate_query_components(profile, {"vector_max_candidate_skills": 3})

    assert components["flattened_skills"] == ["SQL", "Python", "BigQuery"]


def test_build_candidate_query_components_bound_project_technology_hints() -> None:
    profile = {
        "projects": [
            {"tech_stack": ["OpenAI", "Claude Code", "OpenAI", "x" * 200]},
        ],
    }

    components = build_candidate_query_components(profile)
    signature = build_candidate_query_signature_record(components)
    text = build_candidate_query_text(profile)

    assert components["technology_hints"] == ["OpenAI", "Claude Code", "x" * 160]
    assert signature["payload"]["technology_hints"] == components["technology_hints"]
    assert "Project Technology: OpenAI | Claude Code" in text
    assert "x" * 161 not in text

def test_build_candidate_query_components_uses_config_for_inferred_role_family() -> None:
    profile = {
        "headline": "ML Engineer",
        "skills": [],
        "preferences": {"target_role": "Machine Learning Engineer"},
        "experiences": [],
        "projects": [],
    }
    config = {
        "role_taxonomy": {
            "canonical_role_by_alias": {
                "machine learning engineer": "machine learning engineer",
            },
            "role_family_by_role": {
                "machine learning engineer": "ml_platform",
            },
        }
    }

    components = build_candidate_query_components(profile, config)

    assert components["role_family_hints"] == ["ml_platform"]

def test_build_candidate_query_components_uses_configless_fallback_for_inferred_role_family() -> None:
    profile = {
        "headline": "ML Engineer",
        "skills": [],
        "preferences": {"target_role": "Machine Learning Engineer"},
        "experiences": [],
        "projects": [],
    }

    components = build_candidate_query_components(profile, {})

    assert components["role_family_hints"] == ["ml_engineering"]

def test_build_candidate_query_components_role_family_hint_order_is_stable() -> None:
    profile = {
        "headline": "Data Leader",
        "skills": [],
        "preferences": {
            "target_role": "Data Analyst",
            "role_families": ["analytics", "data_engineering"],
        },
        "experiences": [
            {"role": "Machine Learning Engineer"},
            {"role": "Data Scientist"},
        ],
        "projects": [],
    }

    components = build_candidate_query_components(profile, {})

    assert components["role_family_hints"] == ["analytics", "data_engineering", "ml_engineering"]


def test_build_candidate_query_text_includes_preferred_domains() -> None:
    profile = {
        "headline": "DE",
        "skills": [],
        "preferences": {"domains": ["data_engineering", "analytics"]},
    }
    text = build_candidate_query_text(profile)
    assert "data_engineering" in text or "analytics" in text


def test_build_candidate_query_text_handles_missing_fields() -> None:
    """Should not crash when optional fields are absent."""
    profile: dict = {}
    text = build_candidate_query_text(profile)
    assert isinstance(text, str)


def test_build_candidate_query_text_is_deterministic() -> None:
    """Same profile always produces the same query text."""
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "SQL"}, {"name": "dbt"}],
        "preferences": {"domains": ["analytics"]},
    }
    assert build_candidate_query_text(profile) == build_candidate_query_text(profile)


def test_build_candidate_query_text_includes_target_role() -> None:
    profile = {
        "headline": "Senior Data Engineer",
        "skills": [{"name": "SQL"}],
        "preferences": {"target_role": "Data Analyst", "domains": ["analytics"]},
    }
    text = build_candidate_query_text(profile)
    assert "Target Role: Data Analyst" in text


def test_build_candidate_query_text_includes_recent_roles() -> None:
    profile = {
        "headline": "Senior Data Engineer",
        "skills": [{"name": "SQL"}],
        "experiences": [
            {"role": "Senior Data Engineer"},
            {"role": "Data Engineer"},
            {"role": "Junior Data Analyst"},
        ],
        "preferences": {"domains": ["analytics"]},
    }
    text = build_candidate_query_text(profile)
    assert "Recent Roles:" in text
    assert "Junior Data Analyst" in text


def test_build_candidate_query_text_includes_role_family_and_domain_hints() -> None:
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "experiences": [
            {
                "role": "Business Intelligence Analyst",
                "role_family": "analytics",
                "domain_tags": ["retail_banking"],
            }
        ],
        "projects": [{"name": "BI Project", "domain_tags": ["fintech"]}],
        "preferences": {
            "target_role": "Data Analyst",
            "domains": ["banking"],
            "role_families": ["analytics"],
        },
    }

    text = build_candidate_query_text(profile)

    assert "Role Families: analytics" in text
    assert "Domains: banking | retail_banking | fintech" in text


def test_build_candidate_query_signature_record_is_stable_for_same_effective_components() -> None:
    first = {
        "headline": "Data Analyst",
        "target_role": "Data Analyst",
        "recent_roles": ["BI Analyst", "Data Analyst"],
        "role_family_hints": ["analytics"],
        "flattened_skills": ["SQL", "Python", "Power BI"],
        "domain_hints": ["banking", "retail_banking"],
    }
    second = {
        "headline": "Data Analyst",
        "target_role": "Data Analyst",
        "recent_roles": ["BI Analyst", "Data Analyst"],
        "role_family_hints": ["analytics"],
        "flattened_skills": ["SQL", "Python", "Power BI"],
        "domain_hints": ["banking", "retail_banking"],
    }

    assert build_candidate_query_signature_record(first) == build_candidate_query_signature_record(second)


def test_build_candidate_query_embedding_contract_fingerprint_changes_with_model() -> None:
    base_config = {"embedding_backend": "sentence_transformers"}
    first = build_candidate_query_embedding_contract_fingerprint(base_config)
    second = build_candidate_query_embedding_contract_fingerprint(
        {**base_config, "shortlist_embedding_model": "text-embedding-004"}
    )

    assert first["fingerprint"] != second["fingerprint"]



def test_resolve_candidate_query_embedding_contract_shape_when_cache_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "fitcv.sqlite3"))
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {"target_role": "Data Analyst", "domains": ["banking"]},
    }

    with patch("fitcv.vector_search.generate_embedding_with_metadata") as mock_generate_embedding:
        mock_generate_embedding.return_value = {
            "embedding": [0.55, 0.66],
            "backend_id": "sqlite_deterministic_local",
            "contract_fingerprint": "deterministic-contract",
        }
        record = resolve_candidate_query_embedding(profile, {})

    assert set(record.keys()) == _CANDIDATE_QUERY_RECORD_KEYS
    assert record["candidate_query_reuse_status"] == "fresh_query_embedding"
    assert isinstance(record["text"], str)
    assert isinstance(record["components"], dict)
    assert record["embedding"] == [0.55, 0.66]
    assert isinstance(record["candidate_query_signature"], str)
    assert isinstance(record["candidate_query_contract_fingerprint"], str)


def test_default_candidate_query_embedding_reuses_after_first_generation(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {"target_role": "Data Analyst", "domains": ["banking"]},
    }

    with patch("fitcv.vector_search.generate_embedding_with_metadata") as generate:
        generate.return_value = {
            "embedding": [0.55, 0.66] + [0.0] * 254,
            "backend_id": "sqlite_deterministic_local",
            "contract_fingerprint": "deterministic-contract",
        }
        first = resolve_candidate_query_embedding(profile, {})
        second = resolve_candidate_query_embedding(profile, {})

    with sqlite3.connect(db_path) as conn:
        row_count = conn.execute(
            "SELECT COUNT(*) FROM candidate_query_embeddings"
        ).fetchone()[0]

    assert first["candidate_query_reuse_status"] == "fresh_query_embedding"
    assert second["candidate_query_reuse_status"] == "reused_cached_query_embedding"
    assert generate.call_count == 1
    assert row_count == 1


def test_invalid_cached_candidate_vector_is_regenerated(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {"target_role": "Data Analyst", "domains": ["banking"]},
    }
    valid_vector = [0.55, 0.66] + [0.0] * 254
    with patch("fitcv.vector_search.generate_embedding_with_metadata") as generate:
        generate.return_value = {
            "embedding": valid_vector,
            "backend_id": "sqlite_deterministic_local",
            "contract_fingerprint": "deterministic-contract",
        }
        resolve_candidate_query_embedding(profile, {})
        with sqlite3.connect(db_path) as conn:
            conn.execute("UPDATE candidate_query_embeddings SET embedding_json = ?", (json.dumps([1.0, 2.0]),))
            conn.commit()
        result = resolve_candidate_query_embedding(profile, {})

    assert result["candidate_query_reuse_status"] == "fresh_query_embedding"
    assert generate.call_count == 2


def test_fallback_candidate_query_is_not_reused_after_backend_recovery(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "fitcv.sqlite3"))
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {"target_role": "Data Analyst", "domains": ["banking"]},
    }
    config = {
        "embedding_backend": "sentence_transformers",
        "shortlist_embedding_model": "model",
        "embedding_model_revision": "revision-1",
        "embedding_dimension": 3,
    }

    with patch(
        "fitcv.embeddings._load_sentence_transformer_model",
        side_effect=RuntimeError("backend unavailable"),
    ):
        first = resolve_candidate_query_embedding(profile, config)

    with patch(
        "fitcv.embeddings._load_sentence_transformer_model",
        return_value=type("FakeModel", (), {"encode": lambda self, texts, **kwargs: [[1.0, 2.0, 3.0]]})(),
    ):
        second = resolve_candidate_query_embedding(profile, config)

    requested_contract = build_candidate_query_embedding_contract_fingerprint(config)["fingerprint"]
    assert first["candidate_query_contract_fingerprint"] != requested_contract
    assert second["candidate_query_contract_fingerprint"] == requested_contract
    assert second["candidate_query_reuse_status"] == "fresh_query_embedding"
    assert second["embedding_backend_id"] == "sentence_transformers"


def test_dedupe_shortlist_rows_keeps_best_rank_per_job_url() -> None:
    rows = [
        {"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1},
        {"job_url": "https://example.com/1", "vector_similarity": 0.8, "vector_rank": 2},
        {"job_url": "https://example.com/2", "vector_similarity": 0.7, "vector_rank": 3},
    ]

    deduped = _dedupe_shortlist_rows(rows)

    assert deduped == [
        {"job_url": "https://example.com/1", "vector_similarity": 0.9, "vector_rank": 1},
        {"job_url": "https://example.com/2", "vector_similarity": 0.7, "vector_rank": 3},
    ]


def test_lexical_retrieval_uses_late_project_technology_inventory() -> None:
    profile = {
        "preferences": {"target_role": "Data Analyst"},
        "projects": [
            {"name": f"Project {index}", "tech_stack": [f"Tool {index}"]}
            for index in range(9)
        ] + [{"name": "Late Project", "tech_stack": ["LateTool"]}],
    }
    result = run_vector_search(
        profile,
        ["job-1"],
        {"ranking_policy": {"declared_preference_component_weights": {"domain": 0.5, "role_family": 0.3, "work_mode": 0.2}}},
        top_n=1,
        structured_jobs=[{"job_url": "job-1", "title": "Data Analyst", "tech_stack": ["LateTool"]}],
        requested_strategy="lexical_v1",
    )

    assert result["production_rows"][0]["retrieval_components"]["technology_overlap"] == 1.0


def test_lexical_retrieval_uses_raw_description_when_enrichment_falls_back() -> None:
    profile = {
        "preferences": {"target_role": "Data Analyst"},
        "skills": ["Rust"],
    }
    result = run_vector_search(
        profile,
        ["job-raw"],
        {"ranking_policy": {"declared_preference_component_weights": {"domain": 0.5, "role_family": 0.3, "work_mode": 0.2}}},
        top_n=1,
        structured_jobs=[
            {
                "job_url": "job-raw",
                "title": "Data Analyst",
                "description_cleaned": "Build a Rust service.",
                "enrich_reuse_status": "enrichment_fallback",
            }
        ],
        requested_strategy="lexical_v1",
    )

    assert result["production_rows"][0]["retrieval_components"]["description_overlap"] == 1.0


def test_lexical_neutral_skill_default_does_not_admit_unrelated_job() -> None:
    profile = {
        "preferences": {"target_role": "Data Engineer"},
        "skills": ["SQL"],
    }
    job = {"job_url": "job-nurse", "title": "Registered Nurse"}
    lexical_result = _lexical_search_result(
        profile,
        [job["job_url"]],
        {"ranking_policy": {"declared_preference_component_weights": {"domain": 0.5, "role_family": 0.3, "work_mode": 0.2}}},
        top_n=1,
        structured_jobs=[job],
        requested_strategy="lexical_v1",
    )

    lexical_row = lexical_result["production_rows"][0]
    assert lexical_row["retrieval_components"]["skill_overlap"] == 0.5
    assert lexical_row["retrieval_components"]["required_skill_intersection"] is False
    assert lexical_row["retrieval_score"] >= 0.2

    fused = _hybrid_search_result(
        vector_result={
            "production_rows": [{"job_url": "job-vector", "vector_rank": 1}],
            "audit_rows": [],
            "diagnostics": {},
        },
        lexical_result=lexical_result,
        eligible_job_urls=["job-vector", job["job_url"]],
        top_n=1,
        channel_depth=2,
    )

    assert [row["job_url"] for row in fused["production_rows"]] == ["job-vector"]
    assert fused["diagnostics"]["lexical_only_rescue_count"] == 0


def test_technology_overlap_preserves_punctuation_that_distinguishes_languages() -> None:
    assert _technology_overlap(["C++"], ["C++"]) == 1.0
    assert _technology_overlap(["C#"], ["C#"]) == 1.0
    assert _technology_overlap(["C++"], ["C#"]) == 0.0
    assert _technology_overlap(["C#"], ["C++"]) == 0.0


def test_run_vector_search_without_signature_uses_newest_embedding_per_url(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE job_embeddings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_url TEXT NOT NULL,
              chunk_type TEXT NOT NULL,
              chunk_text TEXT NOT NULL,
              embedding_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              embedding_input_signature TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at, embedding_input_signature) VALUES (?, 'job_summary', '', ?, ?, ?)",
            [
                ("https://example.com/reused", json.dumps([0.0, 1.0]), "2026-01-02T00:00:00Z", "signature-new"),
                ("https://example.com/reused", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z", "signature-old"),
            ],
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([0.0, 1.0]),
    )

    result = run_vector_search(
        {},
        ["https://example.com/reused"],
        {"pipeline": {"vector_search_top_n": 1, "shortlist_audit_sample_n": 0}},
    )

    assert result["production_rows"][0]["normalized_embedding"] == [0.0, 1.0]


# ── integration tests ─────────────────────────────────────────────────────────

@pytest.mark.integration
def test_run_vector_search_returns_shortlist(config: dict, sample_profile_path) -> None:
    """Integration — runs VECTOR_SEARCH against real BQ and returns ranked rows."""
    from pathlib import Path
    from fitcv.candidate import load_profile_yaml
    from fitcv.rule_filter import apply_rule_filters
    from fitcv.vector_search import run_vector_search

    profile = load_profile_yaml(sample_profile_path)
    # Use empty passed_job_urls to test graceful short-circuit
    result = run_vector_search(profile, passed_job_urls=[], config=config, top_n=10)
    assert result == {
        "production_rows": [],
        "audit_rows": [],
        "diagnostics": {
            "eligible_jobs_total": 0,
            "scored_jobs_total": 0,
            "missing_job_embedding_total": 0,
            "invalid_job_embedding_total": 0,
            "candidate_embedding_available": False,
            "embedding_coverage_rate": 0.0,
            "production_shortlist_total": 0,
            "production_cutoff_rank": None,
            "production_cutoff_similarity": None,
            "audit_candidate_total": 0,
            "audit_sample_total": 0,
            "audit_sample_fingerprint": "",
            "missing_job_embedding_sample": [],
            "invalid_job_embedding_sample": [],
            "duplicate_job_embedding_total": 0,
            "duplicate_job_embedding_sample": [],
            "raw_hit_anomaly_total": 0,
            "raw_hit_anomaly_sample": [],
        },
        "candidate_query": {},
    }


def _create_job_embedding_table(path: Path) -> None:
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE job_embeddings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_url TEXT NOT NULL,
              chunk_type TEXT NOT NULL,
              chunk_text TEXT NOT NULL,
              embedding_json TEXT NOT NULL,
              created_at TEXT NOT NULL
            )
            """
        )


def _candidate_query_record(embedding: list[float], backend_id: str = "sentence_transformers") -> dict:
    return {
        "text": "candidate",
        "components": {},
        "embedding": embedding,
        "candidate_query_signature": "query-signature",
        "candidate_query_contract_fingerprint": "embedding-contract",
        "candidate_query_reuse_status": "fresh_compute",
        "embedding_backend_id": backend_id,
    }


def test_run_vector_search_uses_total_order_and_bounded_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    _create_job_embedding_table(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at) VALUES (?, 'job_summary', '', ?, ?)",
            [
                ("https://example.com/b", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z"),
                ("https://example.com/a", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z"),
                ("https://example.com/c", json.dumps([0.8, 0.6]), "2026-01-01T00:00:00Z"),
            ],
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )
    config = {"pipeline": {"vector_search_top_n": 1, "shortlist_audit_sample_n": 2}}

    result = run_vector_search(
        {},
        ["https://example.com/c", "https://example.com/b", "https://example.com/a"],
        config,
    )

    production_row = result["production_rows"][0]
    assert production_row["job_url"] == "https://example.com/a"
    assert production_row["vector_similarity"] == 1.0
    assert production_row["vector_rank"] == 1
    assert production_row["shortlist_origin"] == "vector_search"
    assert production_row["retrieval_strategy"] == "vector_cosine_v1"
    assert production_row["normalized_embedding"] == [1.0, 0.0]
    assert len(production_row["embedding_vector_fingerprint"]) == 64
    assert [row["vector_rank"] for row in result["audit_rows"]] == [2, 3]
    assert result["diagnostics"]["audit_candidate_total"] == 2
    assert result["diagnostics"]["audit_sample_total"] == 2
    assert result["diagnostics"]["audit_sample_fingerprint"]


def test_run_vector_search_selects_the_current_job_input_signature(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    config = {
        "embedding_backend": "sentence_transformers",
        "embedding_dimension": 2,
        "pipeline": {"vector_search_top_n": 1, "shortlist_audit_sample_n": 0},
    }
    contract = build_embedding_contract_fingerprint(config)["fingerprint"]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE job_embeddings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_url TEXT NOT NULL,
              chunk_type TEXT NOT NULL,
              chunk_text TEXT NOT NULL,
              embedding_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              embedding_input_signature TEXT,
              embedding_contract_fingerprint TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO job_embeddings(
              job_url, chunk_type, chunk_text, embedding_json, created_at,
              embedding_input_signature, embedding_contract_fingerprint
            ) VALUES (?, 'job_summary', '', ?, ?, ?, ?)
            """,
            [
                ("https://example.com/reused", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z", "signature-a", contract),
                ("https://example.com/reused", json.dumps([0.0, 1.0]), "2026-02-01T00:00:00Z", "signature-b", contract),
            ],
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )

    result = run_vector_search(
        {},
        ["https://example.com/reused"],
        config,
        structured_jobs=[
            {"job_url": "https://example.com/reused", "embedding_input_signature": "signature-a"}
        ],
    )

    assert result["production_rows"][0]["normalized_embedding"] == [1.0, 0.0]


def test_run_vector_search_uses_older_compatible_embedding_when_newer_row_is_incompatible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    config = {
        "embedding_backend": "sentence_transformers",
        "embedding_dimension": 2,
        "pipeline": {"vector_search_top_n": 1, "shortlist_audit_sample_n": 0},
        "ranking_policy": {
            "declared_preference_component_weights": {
                "domain": 0.5,
                "role_family": 0.3,
                "work_mode": 0.2,
            }
        },
    }
    contract = build_embedding_contract_fingerprint(config)["fingerprint"]
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE job_embeddings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_url TEXT NOT NULL,
              chunk_type TEXT NOT NULL,
              chunk_text TEXT NOT NULL,
              embedding_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              embedding_input_signature TEXT,
              embedding_contract_fingerprint TEXT
            )
            """
        )
        conn.executemany(
            """
            INSERT INTO job_embeddings(
              job_url, chunk_type, chunk_text, embedding_json, created_at,
              embedding_input_signature, embedding_contract_fingerprint
            ) VALUES (?, 'job_summary', '', ?, ?, ?, ?)
            """,
            [
                (
                    "https://example.com/reused",
                    json.dumps([1.0, 0.0]),
                    "2026-01-01T00:00:00Z",
                    "signature-a",
                    contract,
                ),
                (
                    "https://example.com/reused",
                    json.dumps([0.0, 1.0]),
                    "2026-02-01T00:00:00Z",
                    "signature-a",
                    "incompatible",
                ),
            ],
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )

    result = run_vector_search(
        {},
        ["https://example.com/reused"],
        config,
        structured_jobs=[
            {"job_url": "https://example.com/reused", "embedding_input_signature": "signature-a"}
        ],
    )

    assert result["production_rows"][0]["normalized_embedding"] == [1.0, 0.0]


def test_run_vector_search_uses_latest_id_for_same_timestamp_duplicate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    _create_job_embedding_table(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at) VALUES (?, 'job_summary', '', ?, ?)",
            ("https://example.com/a", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z"),
        )
        conn.execute(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at) VALUES (?, 'job_summary', '', ?, ?)",
            ("https://example.com/a", json.dumps([0.0, 1.0]), "2026-01-01T00:00:00Z"),
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )

    result = run_vector_search(
        {},
        ["https://example.com/a"],
        {"pipeline": {"vector_search_top_n": 1, "shortlist_audit_sample_n": 0}},
    )

    assert result["production_rows"][0]["vector_similarity"] == 0.0
    assert result["diagnostics"]["duplicate_job_embedding_total"] == 1


def test_run_vector_search_reports_missing_and_invalid_embedding_coverage(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    _create_job_embedding_table(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at) VALUES (?, 'job_summary', '', ?, ?)",
            [
                ("https://example.com/valid", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z"),
                ("https://example.com/invalid", "not-json", "2026-01-01T00:00:00Z"),
            ],
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )

    result = run_vector_search(
        {},
        [
            "https://example.com/valid",
            "https://example.com/invalid",
            "https://example.com/missing",
        ],
        {"pipeline": {"vector_search_top_n": 3, "shortlist_audit_sample_n": 0}},
    )

    assert [row["job_url"] for row in result["production_rows"]] == ["https://example.com/valid"]
    assert result["diagnostics"]["eligible_jobs_total"] == 3
    assert result["diagnostics"]["scored_jobs_total"] == 1
    assert result["diagnostics"]["missing_job_embedding_sample"] == ["https://example.com/missing"]
    assert result["diagnostics"]["invalid_job_embedding_sample"] == ["https://example.com/invalid"]
    assert result["diagnostics"]["embedding_coverage_rate"] == pytest.approx(1 / 3)


def test_run_vector_search_lexical_v1_uses_canonical_signals_and_url_tie_breaking() -> None:
    config = {
        "ranking_policy": {
            "declared_preference_component_weights": {
                "domain": 1.0,
                "role_family": 1.0,
                "work_mode": 1.0,
            }
        },
        "pipeline": {"vector_search_top_n": 2},
    }
    profile = {
        "headline": "Data Engineer",
        "skills": [{"name": "Python"}, {"name": "SQL"}],
        "preferences": {
            "target_role": "Data Engineer",
            "domains": ["fintech"],
            "location_types": ["remote"],
        },
    }
    jobs = [
        {
            "job_url": "https://example.com/z",
            "title": "Marketing Manager",
            "required_skills": ["SEO"],
            "domain": "retail",
            "job_family": "marketing",
            "location_type": "onsite",
        },
        {
            "job_url": "https://example.com/a",
            "title": "Data Platform Engineer",
            "required_skills_canonical": ["python", "sql"],
            "domain": "fintech",
            "job_family": "data_engineering",
            "location_type": "remote",
        },
    ]

    result = run_vector_search(profile, [job["job_url"] for job in jobs], config, structured_jobs=jobs)

    assert result["diagnostics"]["retrieval_strategy"] == "lexical_v1"
    assert result["production_rows"][0]["job_url"] == "https://example.com/a"
    assert result["production_rows"][0]["retrieval_score"] > 0
    assert "vector_similarity" not in result["production_rows"][0]
    assert result["diagnostics"]["embedding_generation_skipped"] is True


def test_run_vector_search_reports_vector_request_and_lexical_fallback_reason(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "empty.sqlite3"))
    job = {
        "job_url": "https://example.com/a",
        "title": "Data Engineer",
        "required_skills_canonical": ["python"],
        "job_family": "data_engineering",
    }

    result = run_vector_search(
        {"skills": [{"name": "Python"}], "preferences": {"target_role": "Data Engineer"}},
        [job["job_url"]],
        {
            "pipeline": {"vector_search_top_n": 1},
            "ranking_policy": {
                "declared_preference_component_weights": {
                    "domain": 1.0,
                    "role_family": 1.0,
                    "work_mode": 1.0,
                }
            },
        },
        structured_jobs=[job],
    )

    assert result["diagnostics"]["requested_strategy"] == "vector_cosine_v1"
    assert result["diagnostics"]["effective_strategy"] == "lexical_v1"
    assert result["diagnostics"]["fallback_used"] is True
    assert result["diagnostics"]["fallback_reason"] == "non_semantic_embedding_backend"
    assert result["diagnostics"]["backend_id"] == "structured_jobs_lexical"
    assert result["diagnostics"]["embedding_backend_id"] == "sqlite_deterministic_local"


def test_run_vector_search_deterministic_backend_uses_technology_overlap() -> None:
    profile = {"projects": [{"tech_stack": ["OpenAI"]}], "preferences": {}}
    jobs = [
        {
            "job_url": "https://example.com/match",
            "title": "Role A",
            "required_skills": [],
            "preferred_skills": [],
            "job_family": "",
            "domain": "",
            "location_type": "",
            "tech_stack_canonical": ["OpenAI"],
        },
        {
            "job_url": "https://example.com/distractor",
            "title": "Role B",
            "required_skills": [],
            "preferred_skills": [],
            "job_family": "",
            "domain": "",
            "location_type": "",
            "tech_stack_canonical": ["Power BI"],
        },
    ]

    result = run_vector_search(
        profile,
        [job["job_url"] for job in jobs],
        {
            "pipeline": {"vector_search_top_n": 1},
            "ranking_policy": {
                "declared_preference_component_weights": {
                    "domain": 1.0,
                    "role_family": 1.0,
                    "work_mode": 1.0,
                }
            },
        },
        structured_jobs=jobs,
    )

    assert result["production_rows"][0]["job_url"] == "https://example.com/match"
    assert result["production_rows"][0]["retrieval_components"]["technology_overlap"] == 1.0
    assert result["diagnostics"]["fallback_reason"] == "non_semantic_embedding_backend"


def test_lexical_technology_overlap_matches_contained_terms_without_substring_false_positive() -> None:
    from fitcv.vector_search import _technology_overlap

    assert _technology_overlap(["OpenAI-compatible APIs"], ["OpenAI"]) == 1.0
    assert _technology_overlap(["SQL"], ["NoSQL"]) == 0.0


def test_run_vector_search_reads_technology_from_loaded_canonical_project_evidence() -> None:
    canonical = converge_candidate_profile_for_runtime(
        {
            "name": "Agent Builder",
            "projects": [
                {
                    "name": "Agent Platform",
                    "tech_stack": ["OpenAI"],
                    "highlights": ["Built an evaluation workflow"],
                }
            ],
            "experiences": [],
            "skills": [],
        }
    )
    profile = load_profile_json_text(json.dumps(canonical))
    jobs = [
        {
            "job_url": "https://example.com/match",
            "title": "Role A",
            "required_skills": [],
            "preferred_skills": [],
            "job_family": "",
            "domain": "",
            "location_type": "",
            "tech_stack_canonical": ["OpenAI"],
        },
        {
            "job_url": "https://example.com/distractor",
            "title": "Role B",
            "required_skills": [],
            "preferred_skills": [],
            "job_family": "",
            "domain": "",
            "location_type": "",
            "tech_stack_canonical": ["Power BI"],
        },
    ]

    result = run_vector_search(
        profile,
        [job["job_url"] for job in jobs],
        {
            "pipeline": {"vector_search_top_n": 1},
            "ranking_policy": {
                "declared_preference_component_weights": {
                    "domain": 1.0,
                    "role_family": 1.0,
                    "work_mode": 1.0,
                }
            },
        },
        structured_jobs=jobs,
    )

    assert result["candidate_query"]["components"]["technology_hints"] == ["OpenAI"]
    assert result["production_rows"][0]["job_url"] == "https://example.com/match"


def test_run_vector_search_falls_back_when_candidate_embedding_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "empty.sqlite3"))
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([]),
    )
    job = {
        "job_url": "https://example.com/a",
        "title": "Data Engineer",
        "required_skills_canonical": ["python"],
    }

    result = run_vector_search(
        {"skills": [{"name": "Python"}], "preferences": {"target_role": "Data Engineer"}},
        [job["job_url"]],
        {"ranking_policy": {"declared_preference_component_weights": {"domain": 1.0, "role_family": 1.0, "work_mode": 1.0}}},
        structured_jobs=[job],
    )

    assert result["production_rows"][0]["job_url"] == job["job_url"]
    assert result["diagnostics"]["fallback_reason"] == "candidate_embedding_unavailable"
    assert result["diagnostics"]["effective_strategy"] == "lexical_v1"


def test_run_vector_search_fallback_preserves_lexical_audit_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([]),
    )
    lexical_result = {
        "production_rows": [
            {"job_url": "https://example.com/lexical-production", "vector_rank": 1},
        ],
        "audit_rows": [
            {"job_url": "https://example.com/lexical-audit", "vector_rank": 2},
        ],
        "diagnostics": {"scored_jobs_total": 2},
    }
    monkeypatch.setattr("fitcv.vector_search._lexical_search_result", lambda *_args, **_kwargs: lexical_result)
    jobs = [
        {"job_url": "https://example.com/lexical-production", "title": "Data Engineer"},
        {"job_url": "https://example.com/lexical-audit", "title": "Data Engineer"},
    ]

    result = run_vector_search(
        {"skills": [{"name": "Python"}]},
        [job["job_url"] for job in jobs],
        {"pipeline": {"vector_search_top_n": 1, "shortlist_audit_sample_n": 1}},
        structured_jobs=jobs,
    )

    assert [row["job_url"] for row in result["production_rows"]] == ["https://example.com/lexical-production"]
    assert [row["job_url"] for row in result["audit_rows"]] == ["https://example.com/lexical-audit"]


def test_hybrid_fusion_allows_rank_51_candidate_into_fixed_top_50() -> None:
    candidate_url = "https://example.com/rank-51-both"
    vector_result = {
        "production_rows": [
            *[
                {"job_url": f"https://example.com/vector-{index}", "vector_rank": index}
                for index in range(1, 51)
            ],
            {"job_url": candidate_url, "vector_rank": 51},
        ],
        "audit_rows": [],
        "diagnostics": {},
    }
    lexical_result = {
        "production_rows": [
            {"job_url": candidate_url, "lexical_rank": 51},
            *[
                {"job_url": f"https://example.com/lexical-{index}", "lexical_rank": index}
                for index in range(52, 102)
            ],
        ],
        "audit_rows": [],
        "diagnostics": {},
    }

    result = _hybrid_search_result(
        vector_result=vector_result,
        lexical_result=lexical_result,
        eligible_job_urls=[
            row["job_url"] for row in vector_result["production_rows"] + lexical_result["production_rows"]
        ],
        top_n=50,
        channel_depth=101,
    )

    assert candidate_url in {row["job_url"] for row in result["production_rows"]}
    assert len(result["production_rows"]) == 50
    assert result["diagnostics"]["fusion_channel_depth"] == 101


def test_hybrid_fusion_rescues_the_strongest_lexical_only_candidate() -> None:
    dual_channel_rows = [
        {"job_url": f"https://example.com/dual-{index}", "vector_rank": index}
        for index in range(1, 51)
    ]
    lexical_rows = [
        {"job_url": f"https://example.com/dual-{index}", "lexical_rank": index}
        for index in range(1, 51)
    ]
    lexical_only_url = "https://example.com/lexical-only-winner"
    lexical_rows.insert(
        0,
        {
            "job_url": lexical_only_url,
            "lexical_rank": 1,
            "retrieval_score": 0.9,
            "retrieval_components": {"skill_overlap": 1.0, "required_skill_intersection": True},
        },
    )

    result = _hybrid_search_result(
        vector_result={"production_rows": dual_channel_rows, "audit_rows": [], "diagnostics": {}},
        lexical_result={"production_rows": lexical_rows, "audit_rows": [], "diagnostics": {}},
        eligible_job_urls=[row["job_url"] for row in lexical_rows],
        top_n=50,
        channel_depth=51,
    )

    assert lexical_only_url in {row["job_url"] for row in result["production_rows"]}
    assert result["diagnostics"]["lexical_only_rescue_count"] == 1


def test_hybrid_fusion_does_not_rescue_neutral_or_missing_score_rows() -> None:
    dual_channel_rows = [
        {"job_url": f"https://example.com/dual-{index}", "vector_rank": index}
        for index in range(1, 3)
    ]
    lexical_rows = [
        {
            "job_url": "https://example.com/neutral",
            "lexical_rank": 1,
            "retrieval_score": 0.9,
            "retrieval_components": {
                "skill_overlap": 0.0,
                "title_relevance": 0.0,
                "technology_overlap": 0.0,
                "description_overlap": 0.0,
                "match_details": {"domain": "neutral", "role_family": "neutral"},
            },
        },
        {"job_url": "https://example.com/missing-score", "lexical_rank": 2},
    ]

    result = _hybrid_search_result(
        vector_result={"production_rows": dual_channel_rows, "audit_rows": [], "diagnostics": {}},
        lexical_result={"production_rows": lexical_rows, "audit_rows": [], "diagnostics": {}},
        eligible_job_urls=[row["job_url"] for row in dual_channel_rows + lexical_rows],
        top_n=2,
        channel_depth=4,
    )

    production_urls = {row["job_url"] for row in result["production_rows"]}
    assert "https://example.com/neutral" not in production_urls
    assert "https://example.com/missing-score" not in production_urls
    assert result["diagnostics"]["lexical_only_rescue_count"] == 0


def test_run_vector_search_falls_back_for_invalid_job_embeddings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    _create_job_embedding_table(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at) VALUES (?, 'job_summary', '', ?, ?)",
            ("https://example.com/a", "not-json", "2026-01-01T00:00:00Z"),
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )
    job = {
        "job_url": "https://example.com/a",
        "title": "Data Engineer",
        "required_skills_canonical": ["python"],
    }

    result = run_vector_search(
        {"skills": [{"name": "Python"}], "preferences": {"target_role": "Data Engineer"}},
        [job["job_url"]],
        {"ranking_policy": {"declared_preference_component_weights": {"domain": 1.0, "role_family": 1.0, "work_mode": 1.0}}},
        structured_jobs=[job],
    )

    assert result["production_rows"][0]["job_url"] == job["job_url"]
    assert result["diagnostics"]["fallback_reason"] == "invalid_job_embeddings"
    assert result["diagnostics"]["effective_strategy"] == "lexical_v1"


def test_run_vector_search_keeps_valid_vectors_and_fills_remaining_slots_lexically(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    _create_job_embedding_table(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at) VALUES (?, 'job_summary', '', ?, ?)",
            ("https://example.com/vector", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z"),
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )
    jobs = [
        {
            "job_url": "https://example.com/vector",
            "title": "Data Engineer",
            "required_skills_canonical": ["python"],
        },
        {
            "job_url": "https://example.com/fallback",
            "title": "Data Engineer",
            "required_skills_canonical": ["python"],
        },
        {
            "job_url": "https://example.com/other",
            "title": "Unrelated Role",
            "required_skills_canonical": ["java"],
        },
    ]

    result = run_vector_search(
        {"skills": [{"name": "Python"}], "preferences": {"target_role": "Data Engineer"}},
        [job["job_url"] for job in jobs],
        {
            "pipeline": {"vector_search_top_n": 2, "shortlist_audit_sample_n": 0},
            "ranking_policy": {
                "declared_preference_component_weights": {
                    "domain": 1.0,
                    "role_family": 1.0,
                    "work_mode": 1.0,
                }
            },
        },
        structured_jobs=jobs,
    )

    assert [row["job_url"] for row in result["production_rows"]] == [
        "https://example.com/vector",
        "https://example.com/fallback",
    ]
    assert result["production_rows"][0]["shortlist_origin"] == "vector_search"
    assert result["production_rows"][1]["shortlist_origin"] == "lexical_fallback"
    assert result["diagnostics"]["effective_strategy"] == "vector_cosine_v1_with_lexical_fallback"
    assert result["diagnostics"]["fallback_admitted_total"] == 1
    assert result["diagnostics"]["vector_admitted_total"] == 1


def test_fixed_recall_fixture_reports_vector_lexical_and_merged_recall_at_50(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    _create_job_embedding_table(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at) VALUES (?, 'job_summary', '', ?, ?)",
            ("https://example.com/vector", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z"),
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )
    jobs = [
        {
            "job_url": "https://example.com/vector",
            "title": "Data Engineer",
            "required_skills_canonical": ["python"],
        },
        {
            "job_url": "https://example.com/fallback",
            "title": "Data Engineer",
            "required_skills_canonical": ["python"],
        },
        {
            "job_url": "https://example.com/unrelated",
            "title": "Unrelated Role",
            "required_skills_canonical": ["java"],
        },
    ]
    relevant_urls = {jobs[0]["job_url"], jobs[1]["job_url"]}
    common_config = {
        "pipeline": {"vector_search_top_n": 50, "shortlist_audit_sample_n": 0},
        "ranking_policy": {
            "declared_preference_component_weights": {
                "domain": 1.0,
                "role_family": 1.0,
                "work_mode": 1.0,
            }
        },
    }
    profile = {"skills": [{"name": "Python"}], "preferences": {"target_role": "Data Engineer"}}
    urls = [job["job_url"] for job in jobs]
    vector_only = run_vector_search(profile, urls, common_config, top_n=50)
    lexical_only = run_vector_search(
        profile,
        urls,
        common_config,
        top_n=50,
        structured_jobs=jobs,
        requested_strategy="lexical_v1",
    )
    merged = run_vector_search(profile, urls, common_config, top_n=50, structured_jobs=jobs)

    def recall(result: dict) -> float:
        returned = {str(row.get("job_url") or "") for row in result["production_rows"]}
        return len(returned & relevant_urls) / len(relevant_urls)

    assert recall(vector_only) == 0.5
    assert recall(lexical_only) == 1.0
    assert recall(merged) == 1.0


def test_run_vector_search_falls_back_for_stale_embedding_contract(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    db_path = tmp_path / "fitcv.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE job_embeddings (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              job_url TEXT NOT NULL,
              chunk_type TEXT NOT NULL,
              chunk_text TEXT NOT NULL,
              embedding_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              embedding_contract_fingerprint TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO job_embeddings(job_url, chunk_type, chunk_text, embedding_json, created_at, embedding_contract_fingerprint) VALUES (?, 'job_summary', '', ?, ?, ?)",
            ("https://example.com/a", json.dumps([1.0, 0.0]), "2026-01-01T00:00:00Z", "stale"),
        )
    monkeypatch.setattr(
        "fitcv.vector_search.resolve_candidate_query_embedding",
        lambda *_args, **_kwargs: _candidate_query_record([1.0, 0.0]),
    )
    job = {
        "job_url": "https://example.com/a",
        "title": "Data Engineer",
        "required_skills_canonical": ["python"],
        "job_family": "data_engineering",
    }

    result = run_vector_search(
        {"skills": [{"name": "Python"}]},
        [job["job_url"]],
        {
            "ranking_policy": {
                "declared_preference_component_weights": {
                    "domain": 1.0,
                    "role_family": 1.0,
                    "work_mode": 1.0,
                }
            }
        },
        structured_jobs=[job],
    )

    assert result["diagnostics"]["fallback_reason"] == "incompatible_embedding_contract"
    assert result["diagnostics"]["effective_strategy"] == "lexical_v1"


def test_run_vector_search_reports_unavailable_without_fallback_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "empty.sqlite3"))

    result = run_vector_search(
        {},
        ["https://example.com/a"],
        {},
        requested_strategy="lexical_v1",
    )

    assert result["production_rows"] == []
    assert result["diagnostics"]["effective_strategy"] == "unavailable"
    assert result["diagnostics"]["fallback_reason"] == "fallback_data_unavailable"
