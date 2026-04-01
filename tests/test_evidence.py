"""
@meta
type: test
scope: unit
domain: evidence
covers:
  - normalise_evidence_item: stable UUID, typed schema
  - score_evidence_item: weighted scoring
  - retrieve_evidence: ranking, top_k, all evidence types
excludes:
  - BigQuery integration (store_evidence_selection)
tags:
  - fast
  - ci-safe
"""

from fitcv.evidence import retrieve_evidence, score_evidence_item


# ── schema and ordering ───────────────────────────────────────────────────────

def test_retrieve_evidence_returns_normalized_schema() -> None:
    """All returned items must have evidence_id, evidence_type, score, source_ref."""
    mock_profile = {
        "projects": [
            {"name": "GA4", "skills": ["SQL", "BigQuery"], "business_value": "analytics"},
            {"name": "ETL", "skills": ["Python", "Airflow"], "business_value": "automation"},
        ],
        "achievements": [{"text": "Reduced latency", "category": "performance"}],
    }
    jd_skills = ["SQL", "BigQuery"]
    evidence = retrieve_evidence(mock_profile, jd_skills, top_k=3)
    assert len(evidence) <= 3
    assert evidence[0]["name"] == "GA4"  # best match first
    for item in evidence:
        assert "evidence_id" in item
        assert "evidence_type" in item
        assert "score" in item
        assert "source_ref" in item


# ── evidence types ────────────────────────────────────────────────────────────

def test_retrieve_evidence_achievement_with_no_skills() -> None:
    """Achievements with no explicit skills still appear in ranked output."""
    mock_profile = {
        "projects": [],
        "achievements": [{"text": "Promoted to senior engineer", "category": "career"}],
    }
    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "achievement"


def test_retrieve_evidence_experience_bullets() -> None:
    """Experience bullets are included in the ranked pool."""
    mock_profile = {
        "projects": [],
        "achievements": [],
        "experiences": [{
            "role": "DE", "company": "Acme",
            "bullets": [{"text": "Built SQL pipelines", "skills": ["SQL"]}],
        }],
    }
    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "experience_entry"
    assert evidence[0]["role"] == "DE"
    assert evidence[0]["company"] == "Acme"
    assert evidence[0]["bullets"] == ["Built SQL pipelines"]


def test_retrieve_evidence_preserves_multiple_relevant_experience_entries() -> None:
    mock_profile = {
        "projects": [
            {"name": "GA4 Platform", "skills": ["BigQuery", "dbt"], "business_value": "analytics"},
            {"name": "Fraud Detection", "skills": ["Python", "SQL"], "business_value": "fraud"},
        ],
        "achievements": [{"text": "Reduced latency by 40%", "skills": ["BigQuery"]}],
        "experiences": [
            {
                "role": "Senior Data Engineer",
                "company": "Acme",
                "start": "2023-01",
                "end": "present",
                "bullets": [
                    {"text": "Built BigQuery pipelines", "skills": ["BigQuery", "SQL"]},
                    {"text": "Maintained dbt models", "skills": ["dbt", "SQL"]},
                ],
            },
            {
                "role": "Data Engineer",
                "company": "Fintech Startup",
                "start": "2021-06",
                "end": "2022-12",
                "bullets": [
                    {"text": "Implemented fraud detection features", "skills": ["Python", "SQL"]},
                    {"text": "Built self-service reporting", "skills": ["SQL"]},
                ],
            },
        ],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL", "BigQuery", "Python"], top_k=5)

    experience_entries = [item for item in evidence if item["evidence_type"] == "experience_entry"]
    assert len(experience_entries) >= 2
    assert experience_entries[0]["role"] == "Senior Data Engineer"
    assert experience_entries[1]["role"] == "Data Engineer"


def test_retrieve_evidence_project_entry_preserves_rich_fields() -> None:
    mock_profile = {
        "projects": [
            {
                "name": "FitCV",
                "duration": "2024-01 — present",
                "url": "https://example.com/fitcv",
                "skills": ["Python", "BigQuery"],
                "tech_stack": [
                    "Backend: Python, FastAPI",
                    "Data: BigQuery",
                    "AI: Gemini",
                ],
                "business_value": "Reduced CV tailoring time from 2 hours to 5 minutes.",
                "highlights": [
                    "Ingested 5000+ postings",
                    "Achieved 89% relevance score",
                    "Serves 20+ candidates",
                ],
            }
        ],
        "achievements": [],
        "experiences": [],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["Python", "BigQuery", "Gemini"], top_k=5)

    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "project_entry"
    assert evidence[0]["name"] == "FitCV"
    assert evidence[0]["duration"] == "2024-01 — present"
    assert evidence[0]["url"] == "https://example.com/fitcv"
    assert evidence[0]["business_value"] == "Reduced CV tailoring time from 2 hours to 5 minutes."
    assert evidence[0]["tech_stack"] == [
        "Backend: Python, FastAPI",
        "Data: BigQuery",
    ]
    assert evidence[0]["highlights"] == [
        "Ingested 5000+ postings",
        "Achieved 89% relevance score",
    ]


def test_retrieve_evidence_sparse_project_entry_is_valid() -> None:
    mock_profile = {
        "projects": [
            {
                "name": "Internal Reporting Tool",
                "duration": "2022",
                "skills": ["Python", "SQL"],
            }
        ],
        "achievements": [],
        "experiences": [],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["Python"], top_k=5)

    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "project_entry"
    assert evidence[0]["name"] == "Internal Reporting Tool"
    assert evidence[0]["duration"] == "2022"
    assert evidence[0]["skills"] == ["Python", "SQL"]
    assert evidence[0]["tech_stack"] == []
    assert evidence[0]["highlights"] == []
    assert evidence[0]["business_value"] == ""


def test_retrieve_evidence_preserves_multiple_relevant_project_entries() -> None:
    mock_profile = {
        "projects": [
            {
                "name": "FitCV",
                "skills": ["Python", "BigQuery", "Gemini"],
                "business_value": "Reduced CV tailoring time",
                "highlights": ["Ingested 5000+ postings"],
            },
            {
                "name": "Fraud Detection",
                "skills": ["Python", "Kafka", "SQL"],
                "business_value": "Processed 10000 transactions/minute",
                "highlights": ["94% precision"],
            },
        ],
        "achievements": [
            {"text": "Promoted to team lead", "skills": ["Leadership"]},
            {"text": "Published analytics package", "skills": ["Python"]},
        ],
        "experiences": [],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["Python", "SQL", "BigQuery"], top_k=4)

    project_entries = [item for item in evidence if item["evidence_type"] == "project_entry"]
    assert len(project_entries) >= 2
    assert [item["name"] for item in project_entries[:2]] == ["FitCV", "Fraud Detection"]


def test_retrieve_evidence_caps_bullets_within_experience_entries() -> None:
    mock_profile = {
        "projects": [],
        "achievements": [],
        "experiences": [
            {
                "role": "Senior Data Engineer",
                "company": "Acme",
                "start": "2023-01",
                "end": "present",
                "bullets": [
                    {"text": "Built BigQuery pipelines", "skills": ["BigQuery", "SQL"]},
                    {"text": "Maintained dbt models", "skills": ["dbt", "SQL"]},
                    {"text": "Ran Airflow orchestration", "skills": ["Airflow"]},
                ],
            }
        ],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL", "BigQuery"], top_k=5)

    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "experience_entry"
    assert len(evidence[0]["bullets"]) == 2
    assert evidence[0]["bullets"] == [
        "Built BigQuery pipelines",
        "Maintained dbt models",
    ]


def test_retrieve_evidence_selects_different_experience_bullets_for_different_jds() -> None:
    mock_profile = {
        "projects": [],
        "achievements": [],
        "experiences": [
            {
                "role": "Data Engineer",
                "company": "Fintech Startup",
                "start": "2021-06",
                "end": "2022-12",
                "bullets": [
                    {"text": "Built self-service Looker dashboards for KPI monitoring.", "skills": ["Looker", "Analytics"]},
                    {"text": "Automated KPI reporting workflows for analytics stakeholders.", "skills": ["Python", "Analytics"]},
                    {"text": "Implemented fraud detection features using BigQuery ML.", "skills": ["BigQuery ML", "Python"]},
                ],
            }
        ],
    }

    analytics_evidence = retrieve_evidence(mock_profile, jd_skills=["Analytics", "Looker", "Reporting"], top_k=5)
    ml_evidence = retrieve_evidence(mock_profile, jd_skills=["Python", "BigQuery ML", "Fraud"], top_k=5)

    analytics_bullets = analytics_evidence[0]["bullets"]
    ml_bullets = ml_evidence[0]["bullets"]

    assert analytics_bullets != ml_bullets
    assert "Built self-service Looker dashboards for KPI monitoring." in analytics_bullets
    assert "Implemented fraud detection features using BigQuery ML." in ml_bullets


# ── edge cases ────────────────────────────────────────────────────────────────

def test_retrieve_evidence_empty_jd_skills() -> None:
    """Empty JD skill list: items still returned (no crash), scores are low but defined."""
    mock_profile = {
        "projects": [{"name": "X", "skills": ["SQL"], "business_value": ""}],
        "achievements": [],
    }
    evidence = retrieve_evidence(mock_profile, jd_skills=[], top_k=5)
    assert len(evidence) == 1
    assert 0.0 <= evidence[0]["score"] <= 1.0


def test_retrieve_evidence_tie_breaking_is_deterministic() -> None:
    """Two items with identical scores must return in a stable, deterministic order."""
    mock_profile = {
        "projects": [
            {"name": "A", "skills": ["SQL"], "business_value": ""},
            {"name": "B", "skills": ["SQL"], "business_value": ""},
        ],
        "achievements": [],
    }
    ev1 = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    ev2 = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    assert [e["name"] for e in ev1] == [e["name"] for e in ev2]
