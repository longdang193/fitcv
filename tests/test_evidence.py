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
    assert evidence[0]["evidence_type"] == "experience_bullet"


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
