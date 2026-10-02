from __future__ import annotations

from scripts.validate_p0b_holdout_review import validate_review_file, validate_review_pair, validate_review_payload
from tests.fixtures.p0b.holdout_review_fixtures import (
    cleanup_fixture,
    extraction_v1,
    packet_v1,
    pending_review,
    v5_review_pair_inputs,
)
def test_current_v2_drafts_fail_closed() -> None:
    extraction = extraction_v1()
    packet = packet_v1()
    evidence = {"ev-1": {"evidence_id": "ev-1", "text": "SQL", "source_ref": "cv-1"}}
    review = pending_review(support="unsupported", evidence=[{"evidence_id": "ev-1", "evidence_text": "SQL", "source_ref": "cv-1"}])
    review["schema_version"] = "p0b.holdout_source_review.v2"
    errors = validate_review_payload(review, extraction, packet, evidence)
    assert "schema_version_invalid" in errors
    assert "req-1:non_supported_has_evidence" in errors


def test_review_validator_rejects_requirement_drift_and_invalid_support() -> None:
    extraction = extraction_v1()
    packet = packet_v1()
    review = pending_review(support="unknown")
    review["cases"][0]["requirement_reviews"][0].update({"requirement_text": "Python", "support_verdict": "partial"})
    assert validate_review_payload(review, extraction, packet, {}) == [
        "req-1:requirement_text_mismatch",
        "req-1:support_verdict_invalid",
    ]


def test_review_validator_accepts_exact_supported_row() -> None:
    extraction = extraction_v1()
    packet = packet_v1()
    evidence = {"ev-1": {"evidence_id": "ev-1", "text": "SQL", "source_ref": "cv-1"}}
    review = pending_review(evidence=[{"evidence_id": "ev-1", "evidence_text": "SQL", "source_ref": "cv-1"}])
    assert validate_review_payload(review, extraction, packet, evidence) == []


def test_review_pair_rejects_duplicate_reviewer_identity() -> None:
    review = pending_review(support="unknown")
    assert validate_review_pair(review, review, extraction_v1(), packet_v1(), {}) == ["reviewer_identity_not_distinct"]


def test_v2_cleanup_keeps_exclusions_out_of_review_packet() -> None:
    extraction, packet, manifest = cleanup_fixture(2)
    excluded = {row["requirement_id"] for row in extraction["excluded_requirements"]}
    packet_ids = {row["requirement_id"] for case in packet["cases"] for row in case["requirements"]}
    assert extraction["counts"] == {"cases": 10, "requirements_total": 198, "admitted_candidate_requirements": 173, "excluded_non_requirements": 25}
    assert manifest["counts"] == {"cases": 10, "requirements": 173, "excluded_from_review": 25}
    assert not excluded & packet_ids


def test_v3_cleanup_excludes_team_description_and_freezes_modality_policy() -> None:
    extraction, packet, manifest = cleanup_fixture(3)
    excluded = {row["requirement_id"] for row in extraction["excluded_requirements"]}
    packet_ids = {row["requirement_id"] for case in packet["cases"] for row in case["requirements"]}
    assert extraction["counts"] == {"cases": 10, "requirements_total": 198, "admitted_candidate_requirements": 170, "excluded_non_requirements": 28}
    assert packet["counts"] == {"cases": 10, "requirements": 170, "excluded_from_review": 28}
    assert not excluded & packet_ids
    assert packet["qualifier_policy_version"] == "p0b.qualifier-policy.v2"
    assert "is_a_plus" in packet["review_contract"]["modality_terms"]


def test_v5_reviewer_pair_validates_against_v3_packet() -> None:
    reviewer_a, reviewer_b, extraction, packet, evidence = v5_review_pair_inputs()
    assert validate_review_pair(reviewer_a, reviewer_b, extraction, packet, evidence) == []
