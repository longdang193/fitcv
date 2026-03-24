"""
@meta
type: test
scope: unit
domain: gap_analysis
covers:
  - compute_gap: matched/partial/missing classification, years_risk, overclaim_risk
  - classify_fit: config-driven strong/stretch/skip thresholds
excludes:
  - BigQuery integration (store_gap_analysis)
tags:
  - fast
  - ci-safe
"""

import pytest

from fitcv.gap_analysis import classify_fit, compute_gap


# ── matched / missing / partial ───────────────────────────────────────────────

def test_compute_gap_identifies_missing_skills() -> None:
    result = compute_gap(
        required_skills=["SQL", "Python", "Airflow", "Terraform"],
        candidate_skills=["SQL", "Python", "dbt"],
        years_required=5,
        years_candidate=3,
    )
    assert "SQL" in result["matched"]
    assert "Airflow" in result["missing"]
    assert "dbt" not in result["missing"]
    assert result["years_risk"] is True


def test_compute_gap_partial_via_synonym() -> None:
    """gcp matches google cloud via synonym map → partial, not missing."""
    result = compute_gap(
        required_skills=["Google Cloud"],
        candidate_skills=["GCP"],
        years_required=None,
        years_candidate=None,
    )
    assert "Google Cloud" in result["partial"]
    assert "Google Cloud" not in result["missing"]


def test_compute_gap_no_required_skills() -> None:
    """No required skills → all fields empty, no risk."""
    result = compute_gap(
        required_skills=[],
        candidate_skills=["SQL"],
        years_required=None,
        years_candidate=5,
    )
    assert result["matched"] == []
    assert result["missing"] == []
    assert result["years_risk"] is False


def test_compute_gap_full_match() -> None:
    result = compute_gap(
        required_skills=["SQL", "Python"],
        candidate_skills=["SQL", "Python"],
        years_required=3,
        years_candidate=4,
    )
    assert set(result["matched"]) == {"SQL", "Python"}
    assert result["missing"] == []
    assert result["years_risk"] is False


def test_compute_gap_all_missing() -> None:
    result = compute_gap(
        required_skills=["Terraform", "Rust"],
        candidate_skills=["SQL"],
        years_required=5,
        years_candidate=2,
    )
    assert set(result["missing"]) == {"Terraform", "Rust"}
    assert result["years_risk"] is True


# ── years_risk edge cases ─────────────────────────────────────────────────────

def test_compute_gap_unknown_years_no_risk() -> None:
    """Unknown years on either side must not set years_risk."""
    result = compute_gap(
        required_skills=["SQL"],
        candidate_skills=["SQL"],
        years_required=None,
        years_candidate=None,
    )
    assert result["years_risk"] is False


def test_compute_gap_years_required_zero_no_risk() -> None:
    """years_required=0 treated as unknown → no risk."""
    result = compute_gap(
        required_skills=["SQL"],
        candidate_skills=["SQL"],
        years_required=0,
        years_candidate=5,
    )
    assert result["years_risk"] is False


def test_compute_gap_years_range_string_parses_minimum() -> None:
    """'3-5' years required → minimum of 3; candidate with 2 years → risk."""
    result = compute_gap(
        required_skills=["SQL"],
        candidate_skills=["SQL"],
        years_required="3-5",  # type: ignore[arg-type]
        years_candidate=2,
    )
    assert result["years_risk"] is True


# ── classify_fit ──────────────────────────────────────────────────────────────

def test_classify_fit_uses_config_thresholds() -> None:
    """classify_fit must derive strong/stretch/skip from config, not hardcoded values."""
    gap_strong = {
        "matched": ["SQL", "Python"], "partial": [], "missing": [],
        "years_risk": False, "overclaim_risk": [],
    }
    gap_skip = {
        "matched": [], "partial": [], "missing": ["SQL", "Python", "Terraform"],
        "years_risk": True, "overclaim_risk": [],
    }
    config = {"gap_thresholds": {"strong_min_matched_ratio": 0.8, "stretch_min_matched_ratio": 0.5}}
    assert classify_fit(gap_strong, required_count=2, config=config) == "strong"
    assert classify_fit(gap_skip, required_count=3, config=config) == "skip"


def test_classify_fit_stretch_band() -> None:
    """matched_ratio between stretch and strong thresholds → stretch."""
    gap = {
        "matched": ["SQL"], "partial": [], "missing": ["Python"],
        "years_risk": False, "overclaim_risk": [],
    }
    config = {"gap_thresholds": {"strong_min_matched_ratio": 0.8, "stretch_min_matched_ratio": 0.5}}
    assert classify_fit(gap, required_count=2, config=config) == "stretch"


def test_classify_fit_default_thresholds_when_no_config() -> None:
    """classify_fit works with no config (uses built-in defaults)."""
    gap_strong = {
        "matched": ["A", "B", "C", "D", "E"],
        "partial": [], "missing": [], "years_risk": False, "overclaim_risk": [],
    }
    result = classify_fit(gap_strong, required_count=5, config=None)
    assert result in ("strong", "stretch", "skip")
