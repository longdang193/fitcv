from __future__ import annotations

import pytest

from fitcv.late_stage_contract import derive_lifecycle_dimensions, derive_submission_clearance


def _accepted_row(**overrides):
    row = {
        "content_validity": "valid",
        "technical_generation": "complete",
        "draft_disposition": "accepted",
        "review": "not_required",
        "pdf_artifact": "verified",
        "persistence": "persisted",
        "page_fit_required": True,
        "page_fit_status": "verified",
    }
    row.update(overrides)
    return row


def _diagnostic(code: str, *, blocking: bool | None = None) -> dict[str, object]:
    diagnostic = {"code": code, "source": "test"}
    if blocking is not None:
        diagnostic["blocking"] = blocking
    return diagnostic


def test_technical_failure_flag_blocks_strict_submission_clearance():
    row = _accepted_row(technical_failure=True)

    clearance = derive_submission_clearance(row)

    assert clearance["submission_permitted"] is False
    assert "technical_failure" in clearance["submission_blockers"]


@pytest.mark.parametrize(
    ("case", "row", "expected_clearance", "expected_blocker", "expected_draft"),
    [
        ("valid_no_review", _accepted_row(), "eligible", None, "accepted"),
        (
            "valid_mandatory_review",
            _accepted_row(review="pending", mandatory_review=True),
            "blocked",
            "review",
            "accepted",
        ),
        (
            "review_approved",
            _accepted_row(review="approved", mandatory_review=True),
            "eligible",
            None,
            "accepted",
        ),
        (
            "invalid_complete_draft",
            _accepted_row(content_validity="invalid", draft_disposition="quarantined", diagnostics={"diagnostics": [_diagnostic("validation_failed")]}),
            "blocked",
            "content_validity",
            "quarantined",
        ),
        (
            "invalid_partial_draft",
            _accepted_row(content_validity="invalid", draft_disposition="quarantined", diagnostics={"diagnostics": [_diagnostic("validation_failed")]}),
            "blocked",
            "content_validity",
            "quarantined",
        ),
        (
            "invalid_unavailable_draft",
            _accepted_row(content_validity="invalid", draft_disposition="unavailable", diagnostics={"diagnostics": [_diagnostic("validation_failed")]}),
            "blocked",
            "content_validity",
            "unavailable",
        ),
        (
            "estimated_length_warning",
            _accepted_row(diagnostics={"diagnostics": [_diagnostic("estimated_length_exceeded")]}),
            "eligible",
            None,
            "accepted",
        ),
        (
            "page_fit_failure",
            _accepted_row(page_fit_status="failed"),
            "blocked",
            "page_fit",
            "accepted",
        ),
        (
            "conversion_failure",
            _accepted_row(pdf_artifact="failed"),
            "blocked",
            "pdf_artifact",
            "accepted",
        ),
        (
            "corrupt_pdf",
            _accepted_row(diagnostics={"diagnostics": [_diagnostic("pdf_render_failed")]}),
            "blocked",
            "diagnostic",
            "accepted",
        ),
        (
            "quarantine_persistence_failure",
            _accepted_row(
                content_validity="invalid",
                draft_disposition="quarantined",
                diagnostics={"diagnostics": [_diagnostic("validation_failed"), _diagnostic("quarantine_persistence_failed")]},
            ),
            "blocked",
            "content_validity",
            "quarantined",
        ),
        (
            "accepted_persistence_failure",
            _accepted_row(persistence="failed"),
            "blocked",
            "persistence",
            "accepted",
        ),
        (
            "provider_failure",
            _accepted_row(technical_generation="failed", diagnostics={"diagnostics": [_diagnostic("provider_error")]}),
            "blocked",
            "technical_generation",
            "accepted",
        ),
        (
            "historical_insufficient_provenance",
            _accepted_row(content_validity="provenance_unavailable"),
            "blocked",
            "content_validity",
            "accepted",
        ),
    ],
)
def test_late_stage_acceptance_matrix(case, row, expected_clearance, expected_blocker, expected_draft):
    dimensions = derive_lifecycle_dimensions(row)
    clearance = derive_submission_clearance(row)

    assert dimensions["draft_disposition"] == expected_draft, case
    assert clearance["submission_clearance"] == expected_clearance, case
    if expected_blocker is None:
        assert clearance["submission_blockers"] == [], case
    else:
        assert expected_blocker in clearance["submission_blockers"], case
