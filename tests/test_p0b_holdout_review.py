from __future__ import annotations

import json
from pathlib import Path

from scripts.validate_p0b_holdout_review import validate_review_file, validate_review_pair, validate_review_payload


ROOT = Path(__file__).parents[1]
P0B = ROOT / "data" / "fitcv-p0-corpus" / "p0b"


def test_current_v2_drafts_fail_closed() -> None:
    extraction = P0B / "p0b_holdout_requirement_extraction_v1.json"
    packet = P0B / "p0b_holdout_source_review_packet_v1.json"
    evidence = P0B / "candidate_evidence_projection_source_backed_v1.jsonl"

    for reviewer in ("a", "b"):
        errors = validate_review_file(P0B / f"p0b_holdout_source_review_reviewer_{reviewer}_v2.json", extraction, packet, evidence)
        assert "schema_version_invalid" in errors
        assert any(error.endswith(":non_supported_has_evidence") or error.endswith(":qualifier_verdicts_not_object") for error in errors)


def test_review_validator_rejects_requirement_drift_and_invalid_support() -> None:
    extraction = {"cases": [{"case_id": "case-1", "source_record_id": "job-1", "requirements": [
        {"requirement_id": "req-1", "requirement_text": "SQL", "requirement_source_span": {"start_char": 1, "end_char": 4}}
    ]}]}
    packet = {"cases": [{"case_id": "case-1"}]}
    review = {
        "schema_version": "p0b.holdout_source_review.v3",
        "status": "agent_draft_pending_human_confirmation",
        "reviewer_id": "reviewer-a",
        "reviewed_at": "2026-09-29",
        "cases": [{"case_id": "case-1", "source_record_id": "job-1", "requirement_reviews": [{
            "requirement_instance_id": "req-1", "requirement_text": "Python",
            "source_span": {"start_char": 1, "end_char": 4}, "support_verdict": "partial",
            "evidence": [], "qualifier_verdicts": {},
        }]}],
    }
    errors = validate_review_payload(review, extraction, packet, {})
    assert "req-1:requirement_text_mismatch" in errors
    assert "req-1:support_verdict_invalid" in errors


def test_review_validator_accepts_exact_supported_row() -> None:
    extraction = {"cases": [{"case_id": "case-1", "source_record_id": "job-1", "requirements": [
        {"requirement_id": "req-1", "requirement_text": "SQL", "requirement_source_span": {"start_char": 1, "end_char": 4}}
    ]}]}
    packet = {"cases": [{"case_id": "case-1"}]}
    evidence = {"ev-1": {"evidence_id": "ev-1", "text": "SQL", "source_ref": "cv-1"}}
    review = {
        "schema_version": "p0b.holdout_source_review.v3",
        "status": "agent_draft_pending_human_confirmation",
        "reviewer_id": "reviewer-a",
        "reviewed_at": "2026-09-29",
        "cases": [{"case_id": "case-1", "source_record_id": "job-1", "requirement_reviews": [{
            "requirement_instance_id": "req-1", "requirement_text": "SQL",
            "source_span": {"start_char": 1, "end_char": 4}, "support_verdict": "supported",
            "evidence": [{"evidence_id": "ev-1", "evidence_text": "SQL", "source_ref": "cv-1"}],
            "qualifier_verdicts": {"skill": {"verdict": "supported", "basis": "Exact skill text."}},
        }]}],
    }
    assert validate_review_payload(review, extraction, packet, evidence) == []



def test_review_pair_rejects_duplicate_reviewer_identity() -> None:
    extraction = {"cases": [{"case_id": "case-1", "source_record_id": "job-1", "requirements": []}]}
    packet = {"cases": [{"case_id": "case-1"}]}
    review = {
        "schema_version": "p0b.holdout_source_review.v3",
        "status": "agent_draft_pending_human_confirmation",
        "reviewer_id": "reviewer-a",
        "reviewed_at": "2026-09-29",
        "cases": [{"case_id": "case-1", "source_record_id": "job-1", "requirement_reviews": []}],
    }
    errors = validate_review_pair(review, review, extraction, packet, {})
    assert errors == ["reviewer_identity_not_distinct"]


def test_v2_cleanup_keeps_exclusions_out_of_review_packet() -> None:
    extraction = json.loads((P0B / "p0b_holdout_requirement_extraction_v2.json").read_text(encoding="utf-8"))
    packet = json.loads((P0B / "p0b_holdout_source_review_packet_v2.json").read_text(encoding="utf-8"))
    manifest = json.loads((P0B / "p0b_holdout_cleanup_v2_manifest.json").read_text(encoding="utf-8"))
    excluded = {row["requirement_id"] for row in extraction["excluded_requirements"]}
    packet_ids = {row["requirement_id"] for case in packet["cases"] for row in case["requirements"]}
    assert extraction["counts"] == {"cases": 10, "requirements_total": 198, "admitted_candidate_requirements": 173, "excluded_non_requirements": 25}
    assert manifest["counts"] == {"cases": 10, "requirements": 173, "excluded_from_review": 25}
    assert not excluded & packet_ids
    assert all(row["extraction_status"] != "agent_draft_excluded_non_requirement" for case in packet["cases"] for row in case["requirements"])



def test_v3_cleanup_excludes_team_description_and_freezes_modality_policy() -> None:
    extraction = json.loads((P0B / "p0b_holdout_requirement_extraction_v3.json").read_text(encoding="utf-8"))
    packet = json.loads((P0B / "p0b_holdout_source_review_packet_v3.json").read_text(encoding="utf-8"))
    excluded = {row["requirement_id"] for row in extraction["excluded_requirements"]}
    packet_ids = {row["requirement_id"] for case in packet["cases"] for row in case["requirements"]}
    assert extraction["counts"] == {"cases": 10, "requirements_total": 198, "admitted_candidate_requirements": 170, "excluded_non_requirements": 28}
    assert packet["counts"] == {"cases": 10, "requirements": 170, "excluded_from_review": 28}
    assert {"req_4473270212_01", "req_4473270212_02", "req_4473270212_03"} <= excluded
    assert not excluded & packet_ids
    assert packet["qualifier_policy_version"] == "p0b.qualifier-policy.v2"
    assert "is_a_plus" in packet["review_contract"]["modality_terms"]


def test_v5_reviewer_pair_validates_against_v3_packet() -> None:
    errors = validate_review_pair(
        json.loads((P0B / "p0b_holdout_source_review_reviewer_a_v5.json").read_text(encoding="utf-8")),
        json.loads((P0B / "p0b_holdout_source_review_reviewer_b_v5.json").read_text(encoding="utf-8")),
        json.loads((P0B / "p0b_holdout_requirement_extraction_v3.json").read_text(encoding="utf-8")),
        json.loads((P0B / "p0b_holdout_source_review_packet_v3.json").read_text(encoding="utf-8")),
        {
            row["evidence_id"]: row
            for row in (json.loads(line) for line in (P0B / "candidate_evidence_projection_source_backed_v1.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())
        },
    )
    assert errors == []
