"""Tests for fitcv.vector_search — all pure unit tests (no cloud calls)."""

import json
import sqlite3
import pytest
from unittest.mock import patch
from fitcv.vector_search import (
    _dedupe_shortlist_rows,
    build_candidate_query_components,
    build_candidate_query_embedding_contract_fingerprint,
    build_candidate_query_signature_record,
    build_candidate_query_text,
    build_protected_terms,
    build_vector_search_query,
    build_weighted_bm25_query_terms,
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


@pytest.mark.parametrize(
    ("cached_signature", "cached_contract", "expected_status", "should_generate"),
    [
        ("matching", "matching", "reused_cached_query_embedding", False),
        ("matching", "stale", "fresh_query_embedding", True),
    ],
)
def test_resolve_candidate_query_embedding_reuses_or_refreshes_cache(
    cached_signature: str,
    cached_contract: str,
    expected_status: str,
    should_generate: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_CP_DATA_BACKEND", "bigquery")
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}, {"name": "Python"}],
        "preferences": {"target_role": "Data Analyst", "domains": ["banking"]},
    }
    config = {
        "gcp_project": "fitcv-test",
        "bigquery_dataset": "fitcv",
        "service_account_key": "/tmp/fake.json",
    }

    expected_text = build_candidate_query_text(profile, config)
    expected_components = build_candidate_query_components(profile, config)
    expected_signature = build_candidate_query_signature_record(expected_components)["signature"]
    expected_contract = build_candidate_query_embedding_contract_fingerprint(config)["fingerprint"]

    row_signature = expected_signature if cached_signature == "matching" else "stale-signature"
    row_contract = expected_contract if cached_contract == "matching" else "stale-contract"

    with (
        patch("google.cloud.bigquery.Client") as mock_bigquery_client,
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
        patch("fitcv.vector_search.generate_embedding") as mock_generate_embedding,
    ):
        client = mock_bigquery_client.return_value
        client.query.return_value.result.return_value = [
            type(
                "Row",
                (),
                {
                    "candidate_query_signature": row_signature,
                    "candidate_query_contract_fingerprint": row_contract,
                    "candidate_query_text": expected_text,
                    "candidate_query_components_json": "{}",
                    "embedding": [0.11, 0.22],
                },
            )()
        ]
        client.insert_rows_json.return_value = []
        mock_generate_embedding.return_value = [0.33, 0.44]

        record = resolve_candidate_query_embedding(profile, config)

    assert set(record.keys()) == _CANDIDATE_QUERY_RECORD_KEYS
    assert record["text"] == expected_text
    assert record["components"] == expected_components
    assert record["candidate_query_signature"] == expected_signature
    assert record["candidate_query_contract_fingerprint"] == expected_contract
    assert record["candidate_query_reuse_status"] == expected_status
    assert record["candidate_query_reuse_status"] in {
        "reused_cached_query_embedding",
        "fresh_query_embedding",
    }
    if should_generate:
        mock_generate_embedding.assert_called_once_with(expected_text, config)
        client.insert_rows_json.assert_called_once()
    else:
        mock_generate_embedding.assert_not_called()
        client.insert_rows_json.assert_not_called()


def test_resolve_candidate_query_embedding_contract_shape_when_cache_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_CP_DATA_BACKEND", "bigquery")
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {"target_role": "Data Analyst", "domains": ["banking"]},
    }
    config = {
        "gcp_project": "fitcv-test",
        "bigquery_dataset": "fitcv",
        "service_account_key": "/tmp/fake.json",
    }

    with (
        patch("google.cloud.bigquery.Client") as mock_bigquery_client,
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
        patch("fitcv.vector_search.generate_embedding") as mock_generate_embedding,
    ):
        client = mock_bigquery_client.return_value
        client.query.return_value.result.return_value = []
        client.insert_rows_json.return_value = []
        mock_generate_embedding.return_value = [0.55, 0.66]

        record = resolve_candidate_query_embedding(profile, config)

    assert set(record.keys()) == _CANDIDATE_QUERY_RECORD_KEYS
    assert record["candidate_query_reuse_status"] == "fresh_query_embedding"
    assert isinstance(record["text"], str)
    assert isinstance(record["components"], dict)
    assert isinstance(record["embedding"], list)
    assert isinstance(record["candidate_query_signature"], str)
    assert isinstance(record["candidate_query_contract_fingerprint"], str)


# ── build_vector_search_query ─────────────────────────────────────────────────

def test_build_vector_search_query_contains_vector_search() -> None:
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "VECTOR_SEARCH" in query


def test_build_vector_search_query_targets_job_summary_chunk() -> None:
    """Query must filter to chunk_type = 'job_summary' only."""
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])
    assert "job_summary" in query


def test_build_vector_search_query_enforces_top_n() -> None:
    """top_n must appear in the query."""
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "50" in query


def test_build_vector_search_query_filters_passed_universe() -> None:
    """Query must restrict to the rule-filtered job universe."""
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])
    assert "job_url IN UNNEST(@passed_job_urls)" in query


def test_build_vector_search_query_filters_job_universe_inside_vector_search() -> None:
    """Universe restriction must happen inside VECTOR_SEARCH, not only afterward."""
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])
    assert "CREATE TEMP TABLE _latest_job_embeddings AS" in query
    assert "VECTOR_SEARCH(\n    TABLE _latest_job_embeddings" in query
    assert "chunk_type = 'job_summary' AND job_url IN UNNEST(@passed_job_urls)" in query


def test_build_vector_search_query_does_not_interpolate_raw_urls() -> None:
    url_with_quote = "https://example.com/job?x=O'Reilly"
    query = build_vector_search_query(top_n=10, passed_job_urls=[url_with_quote])
    assert url_with_quote not in query
    assert "@passed_job_urls" in query


def test_build_vector_search_query_materializes_latest_rows_before_vector_search() -> None:
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1", "url2"])

    assert "ROW_NUMBER() OVER (" in query
    assert "PARTITION BY job_url" in query
    assert "ORDER BY created_at DESC" in query
    assert "WHERE rn = 1" in query


def test_build_vector_search_query_outputs_job_url() -> None:
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "job_url" in query


def test_build_vector_search_query_references_job_embeddings_table() -> None:
    query = build_vector_search_query(top_n=50, passed_job_urls=["url1"])
    assert "job_embeddings" in query


def test_build_vector_search_query_empty_passed_urls() -> None:
    """Empty passed_job_urls → query should still be a valid SQL string."""
    query = build_vector_search_query(top_n=50, passed_job_urls=[])
    assert isinstance(query, str)
    assert "VECTOR_SEARCH" in query


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
    assert isinstance(result, list)


def test_run_vector_search_prefers_nested_pipeline_top_n_over_legacy_flat_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("FITCV_CP_DATA_BACKEND", "bigquery")
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {"domains": ["banking"]},
    }

    with (
        patch("google.cloud.bigquery.Client") as mock_bigquery_client,
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
        patch("fitcv.vector_search.resolve_candidate_query_embedding") as mock_resolve_embedding,
    ):
        mock_resolve_embedding.return_value = {
            "embedding": [0.1, 0.2],
            "candidate_query_signature": "sig",
            "candidate_query_contract_fingerprint": "contract",
            "candidate_query_reuse_status": "fresh_query_embedding",
            "text": "query",
            "components": {},
        }
        client = mock_bigquery_client.return_value
        client.query.return_value.result.return_value = []

        run_vector_search(
            profile=profile,
            passed_job_urls=["https://example.com/job-1"],
            config={
                "gcp_project": "fitcv-test",
                "bigquery_dataset": "fitcv",
                "service_account_key": "/tmp/fake.json",
                "pipeline": {"vector_search_top_n": 7},
                "vector_top_n": 99,
            },
        )

    rendered_query = client.query.call_args.args[0]
    assert "top_k => 7" in rendered_query
    assert "top_k => 99" not in rendered_query


def test_run_vector_search_sqlite_and_bigquery_paths_keep_shortlist_semantics(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> None:
    sqlite_file = tmp_path / "fitcv_cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(sqlite_file))
    profile = {
        "headline": "Data Analyst",
        "skills": [{"name": "SQL"}],
        "preferences": {"domains": ["banking"]},
    }
    passed_job_urls = [
        "https://example.com/job-1",
        "https://example.com/job-2",
        "https://example.com/job-3",
    ]
    config = {
        "gcp_project": "fitcv-test",
        "bigquery_dataset": "fitcv",
        "service_account_key": "/tmp/fake.json",
    }
    candidate_query_record = {
        "embedding": [1.0, 0.0],
        "candidate_query_signature": "sig",
        "candidate_query_contract_fingerprint": "contract",
        "candidate_query_reuse_status": "fresh_query_embedding",
        "text": "query",
        "components": {},
    }
    with sqlite3.connect(str(sqlite_file), timeout=30) as conn:
        conn.execute(
            """
            CREATE TABLE job_embeddings (
                job_url TEXT NOT NULL,
                chunk_type TEXT NOT NULL,
                embedding_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.executemany(
            "INSERT INTO job_embeddings(job_url, chunk_type, embedding_json, created_at) VALUES (?, ?, ?, ?)",
            [
                ("https://example.com/job-1", "job_summary", json.dumps([1.0, 0.0]), "2026-01-01T10:00:00+00:00"),
                ("https://example.com/job-1", "job_summary", json.dumps([0.2, 0.8]), "2026-01-01T09:00:00+00:00"),
                ("https://example.com/job-2", "job_summary", json.dumps([0.8, 0.2]), "2026-01-01T10:00:00+00:00"),
                ("https://example.com/job-3", "job_summary", json.dumps([0.0, 1.0]), "2026-01-01T10:00:00+00:00"),
            ],
        )
        conn.commit()

    with patch("fitcv.vector_search.resolve_candidate_query_embedding") as mock_resolve:
        mock_resolve.return_value = candidate_query_record
        monkeypatch.setenv("FITCV_CP_DATA_BACKEND", "sqlite")
        sqlite_rows = run_vector_search(
            profile=profile,
            passed_job_urls=passed_job_urls,
            config=config,
            top_n=2,
        )

    with (
        patch("fitcv.vector_search.resolve_candidate_query_embedding") as mock_resolve,
        patch("google.cloud.bigquery.Client") as mock_bigquery_client,
        patch("google.oauth2.service_account.Credentials.from_service_account_file"),
    ):
        mock_resolve.return_value = candidate_query_record
        client = mock_bigquery_client.return_value
        client.query.return_value.result.return_value = [
            type(
                "Row",
                (),
                {
                    "job_url": row["job_url"],
                    "vector_similarity": row["vector_similarity"],
                    "vector_rank": row["vector_rank"],
                },
            )()
            for row in sqlite_rows
        ]
        monkeypatch.setenv("FITCV_CP_DATA_BACKEND", "bigquery")
        bigquery_rows = run_vector_search(
            profile=profile,
            passed_job_urls=passed_job_urls,
            config=config,
            top_n=2,
        )

    assert bigquery_rows == sqlite_rows
    assert [row["job_url"] for row in sqlite_rows] == [
        "https://example.com/job-1",
        "https://example.com/job-2",
    ]
    assert [row["vector_rank"] for row in sqlite_rows] == [1, 2]
"""
@meta
type: test
scope: unit
domain: shortlist
covers:
  - vector search behavior
excludes:
  - external vector services
tags:
  - fast
  - ci-safe
"""



def test_build_protected_terms_includes_manual_seed_even_without_taxonomy() -> None:
    config = {
        "shortlist_lexical": {
            "protected_terms": {
                "manual_seed": ["ml", "etl", "dbt", "gcp", "sql", "nlp"],
                "derive_from_taxonomy": False,
            }
        }
    }

    result = build_protected_terms(config)

    assert result["protected_terms"] == ["dbt", "etl", "gcp", "ml", "nlp", "sql"]
    assert result["protected_terms_count"] == 6
    assert isinstance(result["protected_terms_hash"], str)


def test_build_protected_terms_filters_taxonomy_candidates_deterministically() -> None:
    config = {
        "skill_synonyms": {
            "dbt": "dbt",
            "gcp": "google cloud platform",
            "machine learning": "machine learning",
            "etl": "extract transform load",
            "python": "python",
            "nlp": "natural language processing",
        },
        "shortlist_lexical": {
            "protected_terms": {
                "manual_seed": ["sql"],
                "derive_from_taxonomy": True,
                "max_len_auto_protect": 4,
                "punctuation_markers": ["+", "#", "."],
                "stopword_exclusions": ["and", "or", "the"],
            }
        },
    }

    result = build_protected_terms(config)

    # Includes short/acronym candidates; excludes whitespace phrases.
    assert "dbt" in result["protected_terms"]
    assert "gcp" in result["protected_terms"]
    assert "etl" in result["protected_terms"]
    assert "nlp" in result["protected_terms"]
    assert "sql" in result["protected_terms"]
    assert "machine learning" not in result["protected_terms"]
    assert result["protected_terms"] == sorted(result["protected_terms"])



def test_build_weighted_bm25_query_terms_is_deterministic() -> None:
    profile = {
        "headline": "Senior Data Engineer",
        "preferences": {
            "target_role": "Lead Data Engineer",
            "role_families": ["data engineering"],
            "domains": ["fintech", "payments"],
            "location_types": ["remote", "hybrid"],
        },
        "experiences": [
            {"role": "Senior Data Engineer"},
            {"role": "Data Engineer"},
            {"role": "Analytics Engineer"},
        ],
        "skills": {"languages": ["Python", "SQL"], "tools": ["Airflow", "dbt", "BigQuery", "Kafka"]},
    }
    config = {
        "shortlist_lexical": {
            "field_weights": {
                "target_role": 3.0,
                "headline": 3.0,
                "skills": 2.5,
                "recent_roles": 1.5,
                "role_families": 1.0,
                "domains": 0.75,
                "location_types": 0.5,
            },
            "protected_terms": {
                "manual_seed": ["ml", "etl", "dbt", "gcp", "sql", "nlp"],
                "derive_from_taxonomy": False,
            },
        }
    }

    components = build_candidate_query_components(profile, config)
    first = build_weighted_bm25_query_terms(components, config)
    second = build_weighted_bm25_query_terms(components, config)

    assert first["bm25_terms_hash"] == second["bm25_terms_hash"]
    assert first["payload"] == second["payload"]


def test_build_weighted_bm25_query_terms_includes_role_phrases_and_weights() -> None:
    components = {
        "headline": "Senior Data Engineer",
        "target_role": "Lead Data Engineer",
        "recent_roles": ["Senior Data Engineer", "Data Engineer", "Analytics Engineer"],
        "skills": ["Python", "SQL", "Airflow", "dbt", "BigQuery", "Kafka"],
        "role_families": ["data engineering"],
        "domains": ["fintech", "payments"],
        "location_types": ["remote", "hybrid"],
    }
    config = {
        "shortlist_lexical": {
            "field_weights": {
                "target_role": 3.0,
                "headline": 3.0,
                "skills": 2.5,
                "recent_roles": 1.5,
                "domains": 0.75,
                "location_types": 0.5,
            },
            "protected_terms": {"manual_seed": ["dbt", "sql"], "derive_from_taxonomy": False},
        }
    }

    result = build_weighted_bm25_query_terms(components, config)

    phrases = result["payload"]["role_phrases"]
    assert "data engineer" in phrases
    assert "senior data engineer" in phrases
    assert "lead data engineer" in phrases
    assert result["payload"]["field_weights"]["skills"] == 2.5
    assert "dbt" in result["payload"]["terms_by_field"]["skills"]


def test_build_weighted_bm25_query_terms_normalizes_invalid_scoring_mode() -> None:
    components = {
        "headline": "Senior Data Engineer",
        "target_role": "Lead Data Engineer",
        "recent_roles": ["Senior Data Engineer"],
        "skills": ["SQL", "dbt"],
        "role_families": ["data engineering"],
        "domains": ["fintech"],
        "location_types": ["remote"],
    }
    config = {
        "shortlist_lexical": {
            "scoring_mode": "invalid_mode",
            "protected_terms": {"manual_seed": ["sql", "dbt"], "derive_from_taxonomy": False},
        }
    }

    result = build_weighted_bm25_query_terms(components, config)

    assert result["payload"]["scoring_mode"] == "weighted_sum_fallback"
    assert result["payload"]["scoring_formula"] == "sum_f(weight_f * bm25_f(doc, query_terms_f))"


def test_build_weighted_bm25_query_terms_includes_phrase_boost_and_tie_break_contract() -> None:
    components = {
        "headline": "Senior Data Engineer",
        "target_role": "Lead Data Engineer",
        "recent_roles": ["Data Engineer"],
        "skills": ["SQL"],
        "role_families": ["data engineering"],
        "domains": ["fintech"],
        "location_types": ["remote"],
    }
    config = {
        "shortlist_lexical": {
            "scoring_mode": "bm25f",
            "phrase_boost": {"per_phrase": 0.3, "cap_ratio_of_max_base": 0.2},
            "protected_terms": {"manual_seed": ["sql"], "derive_from_taxonomy": False},
        }
    }

    result = build_weighted_bm25_query_terms(components, config)

    assert result["payload"]["scoring_mode"] == "bm25f"
    assert result["payload"]["scoring_formula"] == "bm25f_weighted"
    assert result["payload"]["phrase_boost"]["per_phrase"] == 0.3
    assert result["payload"]["phrase_boost"]["cap_ratio_of_max_base"] == 0.2
    assert result["payload"]["tie_break_order"] == [
        "lexical_base_score_desc",
        "phrase_hit_count_desc",
        "job_url_asc",
    ]

def test_shortlist_intent_invariance_hashes_are_stable_for_same_profile_and_config() -> None:
    profile = {
        "headline": "Senior Data Engineer",
        "preferences": {
            "target_role": "Lead Data Engineer",
            "role_families": ["data engineering"],
            "domains": ["fintech", "payments"],
            "location_types": ["remote", "hybrid"],
        },
        "experiences": [
            {"role": "Senior Data Engineer"},
            {"role": "Data Engineer"},
            {"role": "Analytics Engineer"},
        ],
        "skills": {
            "languages": ["Python", "SQL"],
            "tools": ["Airflow", "dbt", "BigQuery", "Kafka"],
        },
    }
    config = {
        "shortlist_lexical": {
            "protected_terms": {
                "manual_seed": ["ml", "etl", "dbt", "gcp", "sql", "nlp"],
                "derive_from_taxonomy": False,
            }
        }
    }

    components_first = build_candidate_query_components(profile, config)
    components_second = build_candidate_query_components(profile, config)
    signature_first = build_candidate_query_signature_record(components_first)
    signature_second = build_candidate_query_signature_record(components_second)
    text_first = build_candidate_query_text(profile, config)
    text_second = build_candidate_query_text(profile, config)
    weighted_first = build_weighted_bm25_query_terms(components_first, config)
    weighted_second = build_weighted_bm25_query_terms(components_second, config)

    assert components_first == components_second
    assert signature_first["signature"] == signature_second["signature"]
    assert text_first == text_second
    assert weighted_first["bm25_terms_hash"] == weighted_second["bm25_terms_hash"]
    assert weighted_first["protected_terms_hash"] == weighted_second["protected_terms_hash"]


def test_shortlist_vector_and_lexical_channels_share_same_canonical_component_values() -> None:
    profile = {
        "headline": "Senior Data Engineer",
        "preferences": {
            "target_role": "Lead Data Engineer",
            "role_families": ["data engineering"],
            "domains": ["fintech", "payments"],
            "location_types": ["remote", "hybrid"],
        },
        "experiences": [
            {"role": "Senior Data Engineer"},
            {"role": "Data Engineer"},
            {"role": "Analytics Engineer"},
        ],
        "skills": {
            "languages": ["Python", "SQL"],
            "tools": ["Airflow", "dbt", "BigQuery", "Kafka"],
        },
    }
    config = {
        "shortlist_lexical": {
            "protected_terms": {
                "manual_seed": ["ml", "etl", "dbt", "gcp", "sql", "nlp"],
                "derive_from_taxonomy": False,
            }
        }
    }

    components = build_candidate_query_components(profile, config)
    text = build_candidate_query_text(profile, config)
    weighted = build_weighted_bm25_query_terms(components, config)

    assert f"Headline: {components['headline']}" in text
    assert f"Target Role: {components['target_role']}" in text
    assert " | ".join(components["recent_roles"]) in text
    assert " | ".join(components["skills"]) in text
    assert weighted["payload"]["terms_by_field"]["headline"] == ["senior", "data", "engineer"]
    assert weighted["payload"]["terms_by_field"]["target_role"] == ["lead", "data", "engineer"]
