from fitcv.agentic_cv_analysis import build_cv_analysis_record
from fitcv.evidence import _cv_analysis_policy_settings


def _job() -> dict:
    return {"job_url": "https://example.test/job/1", "title": "Data Engineer"}


def test_explicit_none_selection_policy_uses_canonical_default() -> None:
    settings = _cv_analysis_policy_settings(
        {"cv_analysis": {"selection_policy": {"requirement_gain_weight": None}}}
    )
    assert settings["requirement_gain_weight"] == 0.10


def test_zero_selection_policy_remains_zero() -> None:
    settings = _cv_analysis_policy_settings(
        {"cv_analysis": {"selection_policy": {"requirement_gain_weight": 0.0}}}
    )
    assert settings["requirement_gain_weight"] == 0.0


def test_legacy_none_selection_policy_does_not_escape_trace_record() -> None:
    record = build_cv_analysis_record(
        job=_job(),
        status="analysis_failed",
        analysis_input_fingerprint=None,
        analysis_input_components={},
        analysis_reuse_status="fresh_compute",
        evidence_payload=[],
        evidence_selection_summary={
            "selection_policy": {"requirement_gain_weight": None}
        },
        gap_summary=None,
        requirement_coverage=[],
        section_confidence_hints={},
        do_not_claim=[],
        fit_classification=None,
        ranking_fit_label=None,
        error={"stage": "analysis", "message": "synthetic"},
    )
    assert record["status"] == "analysis_failed"
    assert record["cv_analysis_trace"]["output_summary"]["requirement_gain_weight"] == 0.10
