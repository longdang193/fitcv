from fitcv.agentic_cv_generation import (
    build_validation_evidence_fingerprint,
    normalize_review_required_reason_code,
)
from fitcv.late_stage_contract import CV_GENERATION_REVIEW_REQUIRED_STATUS


def test_review_gate_maps_to_specific_reason_code_for_unsupported_requirements() -> None:
    code = normalize_review_required_reason_code(
        status=CV_GENERATION_REVIEW_REQUIRED_STATUS,
        error={
            "stage": "review_gate",
            "message": "Unsupported requirements require review: SQL architecture",
        },
        validation_initial=None,
    )
    assert code is not None
    assert code.value == "unsupported_requirement_gap"


def test_review_gate_maps_to_validation_guardrail_failed_when_rules_present() -> None:
    code = normalize_review_required_reason_code(
        status=CV_GENERATION_REVIEW_REQUIRED_STATUS,
        error={
            "stage": "review_gate",
            "message": "Manual review required",
        },
        validation_initial={
            "grounding_violations": [{"rule_id": "grounding_required_support"}],
            "missing_sections": [],
        },
    )
    assert code is not None
    assert code.value == "validation_guardrail_failed"


def test_review_required_fallback_no_longer_returns_unknown() -> None:
    code = normalize_review_required_reason_code(
        status=CV_GENERATION_REVIEW_REQUIRED_STATUS,
        error={"stage": "mystery", "message": "mystery"},
        validation_initial=None,
    )
    assert code is not None
    assert code.value == "manual_review_other"


def test_validation_evidence_fingerprint_is_stable_for_identical_inputs() -> None:
    payload = {
        "missing_sections": ["experience"],
        "grounding_violations": [{"rule_id": "grounding_required_support"}],
        "markdown_quality_blocking_issues": [],
        "markdown_quality_review_flags": [],
    }
    error = {"stage": "validation", "message": "CV validation failed"}
    fp1 = build_validation_evidence_fingerprint(
        status="validation_failed",
        validation=payload,
        error=error,
    )
    fp2 = build_validation_evidence_fingerprint(
        status="validation_failed",
        validation=payload,
        error=error,
    )
    assert fp1 == fp2
