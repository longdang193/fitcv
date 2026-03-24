"""Tests for fitcv.rule_filter — all pure unit tests (no cloud calls)."""

import pytest

from fitcv.rule_filter import (
    apply_rule_filters,
    check_contract_type,
    check_domain_preference,
    check_experience_level,
    check_freshness,
    check_location_type,
    check_must_have_skills,
    check_seniority,
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _prefs(**kwargs) -> dict:
    """Build a preferences dict with sensible defaults."""
    defaults = {
        "seniority_target": "mid",
        "location_types": ["remote"],
        "contract_types": ["Full-time"],
        "exclude_experience_levels": ["Internship"],
        "must_have_skills": [],
        "preferred_domains": [],
        "max_age_days": 30,
    }
    return {**defaults, **kwargs}


def _job(**kwargs) -> dict:
    """Build a job dict with sensible defaults."""
    defaults = {
        "job_url": "http://example.com/job/1",
        "seniority": "mid",
        "location_type": "remote",
        "contract_type": "Full-time",
        "experience_level": "Entry level",
        "required_skills": ["SQL"],
        "published_at": "2026-03-10",  # recent enough for 30-day window
        "domain": "data_engineering",
    }
    return {**defaults, **kwargs}


# ── return structure ──────────────────────────────────────────────────────────

def test_apply_rule_filters_returns_passed_and_rejected() -> None:
    """Return value must always be {passed, rejected} dicts, never a flat list."""
    result = apply_rule_filters([_job(seniority="senior")], _prefs())
    assert "passed" in result and "rejected" in result
    assert isinstance(result["passed"], list)
    assert isinstance(result["rejected"], list)


def test_rejected_jobs_include_reasons() -> None:
    """Each rejected job must include a non-empty reasons list."""
    # lead is 2 steps above mid → must be rejected by seniority check
    result = apply_rule_filters([_job(seniority="lead")], _prefs())
    assert len(result["rejected"]) > 0
    assert all(len(r["reasons"]) > 0 for r in result["rejected"])
    assert all("job_url" in r for r in result["rejected"])


def test_passes_when_no_filters_violated() -> None:
    result = apply_rule_filters([_job()], _prefs(must_have_skills=["SQL"]))
    assert len(result["passed"]) == 1
    assert len(result["rejected"]) == 0


def test_multiple_rejection_reasons_accumulated() -> None:
    """A job that fails two checks should accumulate both reasons."""
    # lead is 2+ above mid (seniority_mismatch) AND Internship is excluded (contract_type_excluded)
    job = _job(seniority="lead", contract_type="Internship")
    result = apply_rule_filters([job], _prefs())
    assert len(result["rejected"]) == 1
    assert len(result["rejected"][0]["reasons"]) >= 2


# ── seniority ladder ──────────────────────────────────────────────────────────

def test_seniority_accepts_exact_match() -> None:
    assert check_seniority(_job(seniority="mid"), _prefs(seniority_target="mid"))


def test_seniority_accepts_one_step_below() -> None:
    """target=mid, job=associate (one below) → pass."""
    assert check_seniority(_job(seniority="associate"), _prefs(seniority_target="mid"))


def test_seniority_accepts_one_step_above() -> None:
    """target=mid, job=senior (one above) → pass (stretch)."""
    assert check_seniority(_job(seniority="senior"), _prefs(seniority_target="mid"))


def test_seniority_rejects_two_steps_above() -> None:
    """target=mid, job=lead (two above) → reject."""
    assert not check_seniority(_job(seniority="lead"), _prefs(seniority_target="mid"))


def test_seniority_rejects_two_steps_below() -> None:
    """target=mid, job=entry (two below) → reject."""
    assert not check_seniority(_job(seniority="entry"), _prefs(seniority_target="mid"))


def test_seniority_rejects_three_steps_above() -> None:
    """target=mid, job=manager → reject."""
    assert not check_seniority(_job(seniority="manager"), _prefs(seniority_target="mid"))


def test_seniority_unknown_passes() -> None:
    """None/unknown seniority → keep (do not hard-reject)."""
    assert check_seniority(_job(seniority=None), _prefs(seniority_target="mid"))


def test_seniority_unknown_string_passes() -> None:
    assert check_seniority(_job(seniority=""), _prefs(seniority_target="mid"))


# ── location type ─────────────────────────────────────────────────────────────

def test_location_accepts_matching() -> None:
    assert check_location_type(_job(location_type="remote"), _prefs(location_types=["remote"]))


def test_location_rejects_non_matching() -> None:
    assert not check_location_type(_job(location_type="onsite"), _prefs(location_types=["remote"]))


def test_location_passes_when_prefs_empty() -> None:
    """Empty location_types = no preference = accept everything."""
    assert check_location_type(_job(location_type="onsite"), _prefs(location_types=[]))


# ── contract type ─────────────────────────────────────────────────────────────

def test_contract_type_accepts_matching() -> None:
    assert check_contract_type(_job(contract_type="Full-time"), _prefs(contract_types=["Full-time"]))


def test_contract_type_rejects_internship() -> None:
    assert not check_contract_type(_job(contract_type="Internship"), _prefs(contract_types=["Full-time"]))


def test_contract_type_reason_code_contains_contract() -> None:
    result = apply_rule_filters([_job(contract_type="Internship")], _prefs())
    rejected = result["rejected"]
    assert any("contract_type" in r for reason in rejected for r in reason["reasons"])


# ── experience level ──────────────────────────────────────────────────────────

def test_experience_level_excludes_internship() -> None:
    assert not check_experience_level(
        _job(experience_level="Internship"),
        _prefs(exclude_experience_levels=["Internship"]),
    )


def test_experience_level_passes_entry_level() -> None:
    assert check_experience_level(
        _job(experience_level="Entry level"),
        _prefs(exclude_experience_levels=["Internship"]),
    )


# ── must-have skills ──────────────────────────────────────────────────────────

def test_must_have_skills_exact_match() -> None:
    assert check_must_have_skills(_job(required_skills=["SQL", "Python"]), _prefs(must_have_skills=["SQL"]))


def test_must_have_skills_missing_skill_fails() -> None:
    assert not check_must_have_skills(_job(required_skills=["Java"]), _prefs(must_have_skills=["SQL"]))


def test_must_have_skills_empty_prefs_passes() -> None:
    """No must-have skills = always pass."""
    assert check_must_have_skills(_job(required_skills=[]), _prefs(must_have_skills=[]))


def test_must_have_skills_synonym_gcp_matches_google_cloud() -> None:
    """GCP (canonical) must match 'Google Cloud' in JD via synonym map."""
    assert check_must_have_skills(
        _job(required_skills=["Google Cloud"]),
        _prefs(must_have_skills=["GCP"]),
    )


def test_must_have_skills_synonym_k8s_matches_kubernetes() -> None:
    assert check_must_have_skills(
        _job(required_skills=["Kubernetes"]),
        _prefs(must_have_skills=["K8s"]),
    )


def test_must_have_skills_case_insensitive() -> None:
    assert check_must_have_skills(
        _job(required_skills=["bigquery"]),
        _prefs(must_have_skills=["BigQuery"]),
    )


# ── freshness ─────────────────────────────────────────────────────────────────

def test_freshness_accepts_recent_job() -> None:
    assert check_freshness(_job(published_at="2026-03-20"), _prefs(max_age_days=30))


def test_freshness_rejects_stale_job() -> None:
    assert not check_freshness(_job(published_at="2025-01-01"), _prefs(max_age_days=30))


def test_freshness_passes_when_no_published_at() -> None:
    """Missing published_at → keep (cannot determine staleness)."""
    assert check_freshness(_job(published_at=None), _prefs(max_age_days=30))


# ── domain preference ─────────────────────────────────────────────────────────

def test_domain_passes_when_no_preference() -> None:
    """Empty preferred_domains = no preference = accept all."""
    assert check_domain_preference(_job(domain="fintech"), _prefs(preferred_domains=[]))


def test_domain_accepts_matching_domain() -> None:
    assert check_domain_preference(
        _job(domain="data_engineering"),
        _prefs(preferred_domains=["data_engineering", "analytics"]),
    )


def test_domain_rejects_non_matching_domain() -> None:
    assert not check_domain_preference(
        _job(domain="fintech"),
        _prefs(preferred_domains=["data_engineering"]),
    )


# ── integration ────────────────────────────────────────────────────────────────

@pytest.mark.integration
def test_store_filter_results_integration(config: dict) -> None:
    """Integration — inserts filter results into BigQuery."""
    from fitcv.rule_filter import store_filter_results
    result = {
        "passed": ["http://example.com/job/1"],
        "rejected": [{"job_url": "http://example.com/job/2", "reasons": ["seniority_mismatch"]}],
    }
    store_filter_results(result, config)  # should not raise
