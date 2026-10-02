from __future__ import annotations

from typing import Any


def _requirement(requirement_id: str, text: str = "SQL") -> dict[str, Any]:
    return {
        "requirement_id": requirement_id,
        "requirement_text": text,
        "requirement_source_span": {"start_char": 1, "end_char": len(text) + 1},
    }


def extraction_v1() -> dict[str, Any]:
    return {
        "cases": [{
            "case_id": "case-1",
            "source_record_id": "job-1",
            "requirements": [_requirement("req-1")],
        }]
    }


def packet_v1() -> dict[str, Any]:
    return {"cases": [{"case_id": "case-1"}]}


def pending_review(*, reviewer_id: str = "reviewer-a", support: str = "supported", evidence: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {
        "schema_version": "p0b.holdout_source_review.v3",
        "status": "agent_draft_pending_human_confirmation",
        "reviewer_id": reviewer_id,
        "reviewed_at": "2026-09-29",
        "cases": [{
            "case_id": "case-1",
            "source_record_id": "job-1",
            "requirement_reviews": [{
                "requirement_instance_id": "req-1",
                "requirement_text": "SQL",
                "source_span": {"start_char": 1, "end_char": 4},
                "support_verdict": support,
                "evidence": evidence or [],
                "qualifier_verdicts": ({"skill": {"verdict": "supported", "basis": "Exact skill text."}} if support == "supported" else {}),
            }],
        }],
    }


def cleanup_fixture(version: int) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    total = 198
    admitted = 173 if version == 2 else 170
    excluded = total - admitted
    requirements = [_requirement(f"req-{index:03d}", f"Requirement {index}") for index in range(admitted)]
    excluded_requirements = [{"requirement_id": f"excluded-{index:03d}", "extraction_status": "agent_draft_excluded_non_requirement"} for index in range(excluded)]
    extraction = {
        "cases": [{"case_id": f"case-{index:02d}", "source_record_id": f"job-{index:02d}", "requirements": []} for index in range(10)],
        "excluded_requirements": excluded_requirements,
        "counts": {
            "cases": 10,
            "requirements_total": total,
            "admitted_candidate_requirements": admitted,
            "excluded_non_requirements": excluded,
        },
    }
    packet = {
        "cases": [{"case_id": f"case-{index:02d}", "source_record_id": f"job-{index:02d}", "requirements": []} for index in range(10)],
        "counts": {"cases": 10, "requirements": admitted, "excluded_from_review": excluded},
        "qualifier_policy_version": "p0b.qualifier-policy.v2",
        "review_contract": {"modality_terms": ["is_a_plus"]},
    }
    manifest = {"counts": {"cases": 10, "requirements": admitted, "excluded_from_review": excluded}}
    return extraction, packet, manifest


def v5_review_pair_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]:
    extraction = {"cases": [{"case_id": "case-1", "source_record_id": "job-1", "requirements": [_requirement("req-1")]}]}
    packet = {"cases": [{"case_id": "case-1", "requirements": [_requirement("req-1")]}]}
    evidence = {"ev-1": {"evidence_id": "ev-1", "text": "SQL", "source_ref": "cv-1"}}
    supported = pending_review(reviewer_id="reviewer-a", evidence=[{"evidence_id": "ev-1", "evidence_text": "SQL", "source_ref": "cv-1"}])
    supported["schema_version"] = "p0b.holdout_source_review.v5"
    reviewer_b = pending_review(reviewer_id="reviewer-b", evidence=[{"evidence_id": "ev-1", "evidence_text": "SQL", "source_ref": "cv-1"}])
    reviewer_b["schema_version"] = "p0b.holdout_source_review.v5"
    return supported, reviewer_b, extraction, packet, evidence
