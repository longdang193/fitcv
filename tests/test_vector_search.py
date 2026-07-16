"""Tests for fitcv.vector_search — all pure unit tests (no cloud calls)."""

import json
import sqlite3
from pathlib import Path
import pytest
from unittest.mock import patch
from fitcv.vector_search import (
    _dedupe_shortlist_rows,
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
    first = build_candidate_query_embedding_contract_fingerprint({})
    second = build_candidate_query_embedding_contract_fingerprint(
        {"shortlist_embedding_model": "text-embedding-004"}
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

    with patch("fitcv.vector_search.generate_embedding") as mock_generate_embedding:
        mock_generate_embedding.return_value = [0.55, 0.66]
        record = resolve_candidate_query_embedding(profile, {})

    assert set(record.keys()) == _CANDIDATE_QUERY_RECORD_KEYS
    assert record["candidate_query_reuse_status"] == "fresh_query_embedding"
    assert isinstance(record["text"], str)
    assert isinstance(record["components"], dict)
    assert record["embedding"] == [0.55, 0.66]
    assert isinstance(record["candidate_query_signature"], str)
    assert isinstance(record["candidate_query_contract_fingerprint"], str)


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


def _candidate_query_record(embedding: list[float]) -> dict:
    return {
        "text": "candidate",
        "components": {},
        "embedding": embedding,
        "candidate_query_signature": "query-signature",
        "candidate_query_contract_fingerprint": "embedding-contract",
        "candidate_query_reuse_status": "fresh_compute",
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
