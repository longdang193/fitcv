from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ALLOWED_SUPPORT = {"supported", "unsupported", "unknown"}
ALLOWED_QUALIFIER = ALLOWED_SUPPORT | {"not_stated"}
EXPECTED_STATUS = "agent_draft_pending_human_confirmation"
ALLOWED_SCHEMAS = {"p0b.holdout_source_review.v3", "p0b.holdout_source_review.v4", "p0b.holdout_source_review.v5"}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _evidence_map(path: Path) -> dict[str, dict[str, Any]]:
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {str(row.get("evidence_id")): row for row in rows}


def _review_rows(case: dict[str, Any]) -> list[dict[str, Any]]:
    rows = case.get("requirement_reviews")
    if rows is None:
        rows = case.get("requirements", [])
    return rows if isinstance(rows, list) else []


def _review_requirement_id(row: dict[str, Any]) -> str:
    return str(row.get("requirement_instance_id", row.get("requirement_id")))


def _review_evidence(row: dict[str, Any], evidence_rows: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    raw = row.get("evidence")
    if raw is None:
        raw = row.get("candidate_evidence")
    if raw is None:
        raw = row.get("evidence_refs", [])
    if not isinstance(raw, list):
        return raw
    evidence = []
    for item in raw:
        if isinstance(item, str):
            source = evidence_rows.get(item, {})
            evidence.append({"evidence_id": item, "evidence_text": source.get("text"), "source_ref": source.get("source_ref")})
        elif isinstance(item, dict):
            evidence_id = str(item.get("evidence_id") or "")
            source = evidence_rows.get(evidence_id, {})
            evidence.append({
                "evidence_id": evidence_id,
                "evidence_text": item.get("evidence_text", item.get("text", source.get("text"))),
                "source_ref": item.get("source_ref", source.get("source_ref")),
            })
        else:
            evidence.append(item)
    return evidence


def validate_review_payload(
    review: dict[str, Any],
    extraction: dict[str, Any],
    packet: dict[str, Any],
    evidence_rows: dict[str, dict[str, Any]],
) -> list[str]:
    errors: list[str] = []
    if review.get("schema_version") not in ALLOWED_SCHEMAS:
        errors.append("schema_version_invalid")
    if review.get("status") != EXPECTED_STATUS:
        errors.append("status_invalid")
    if not str(review.get("reviewer_id") or "").strip():
        errors.append("reviewer_id_missing")
    if not str(review.get("reviewed_at") or "").strip():
        errors.append("reviewed_at_missing")

    expected_cases = {str(case.get("case_id")): case for case in extraction.get("cases", [])}
    packet_cases = {str(case.get("case_id")): case for case in packet.get("cases", [])}
    actual_cases = {str(case.get("case_id")): case for case in review.get("cases", [])}
    if set(expected_cases) != set(packet_cases):
        errors.append("canonical_packet_join_invalid")
    if set(actual_cases) != set(expected_cases):
        errors.append("case_set_mismatch")

    for case_id, expected_case in expected_cases.items():
        actual_case = actual_cases.get(case_id)
        if actual_case is None:
            continue
        if actual_case.get("source_record_id") != expected_case.get("source_record_id"):
            errors.append(f"{case_id}:source_record_id_mismatch")
        packet_requirements = packet_cases[case_id].get("requirements")
        requirement_source = packet_requirements if isinstance(packet_requirements, list) and packet_requirements else expected_case.get("requirements", [])
        expected_requirements = {
            str(item.get("requirement_id")): item for item in requirement_source
        }
        actual_reviews = {
            _review_requirement_id(item): item
            for item in _review_rows(actual_case)
        }
        if set(actual_reviews) != set(expected_requirements):
            errors.append(f"{case_id}:requirement_set_mismatch")
        for requirement_id, expected in expected_requirements.items():
            actual = actual_reviews.get(requirement_id)
            if actual is None:
                continue
            if actual.get("requirement_text") != expected.get("requirement_text"):
                errors.append(f"{requirement_id}:requirement_text_mismatch")
            actual_span = actual.get("requirement_source_span", actual.get("source_span"))
            if actual_span != expected.get("requirement_source_span"):
                errors.append(f"{requirement_id}:source_span_mismatch")
            support = actual.get("support_verdict")
            if support not in ALLOWED_SUPPORT:
                errors.append(f"{requirement_id}:support_verdict_invalid")
            evidence = _review_evidence(actual, evidence_rows)
            if not isinstance(evidence, list):
                errors.append(f"{requirement_id}:evidence_not_list")
                evidence = []
            if support == "supported" and not evidence:
                errors.append(f"{requirement_id}:supported_without_evidence")
            if support in {"unsupported", "unknown"} and evidence:
                errors.append(f"{requirement_id}:non_supported_has_evidence")
            seen_evidence: set[str] = set()
            for item in evidence:
                if not isinstance(item, dict):
                    errors.append(f"{requirement_id}:evidence_item_invalid")
                    continue
                evidence_id = str(item.get("evidence_id") or "")
                source = evidence_rows.get(evidence_id)
                if not evidence_id or source is None:
                    errors.append(f"{requirement_id}:evidence_id_invalid")
                    continue
                if evidence_id in seen_evidence:
                    errors.append(f"{requirement_id}:duplicate_evidence_id")
                seen_evidence.add(evidence_id)
                if item.get("evidence_text") != source.get("text"):
                    errors.append(f"{requirement_id}:evidence_text_mismatch")
                if item.get("source_ref") != source.get("source_ref"):
                    errors.append(f"{requirement_id}:evidence_source_ref_mismatch")
            qualifiers = actual.get("qualifier_verdicts")
            if not isinstance(qualifiers, dict):
                errors.append(f"{requirement_id}:qualifier_verdicts_not_object")
                continue
            for qualifier, decision in qualifiers.items():
                if not isinstance(decision, dict) or decision.get("verdict") not in ALLOWED_QUALIFIER:
                    errors.append(f"{requirement_id}:qualifier_verdict_invalid:{qualifier}")
                elif not str(decision.get("basis") or "").strip():
                    errors.append(f"{requirement_id}:qualifier_basis_missing:{qualifier}")
    return sorted(set(errors))


def validate_review_pair(
    reviewer_a: dict[str, Any],
    reviewer_b: dict[str, Any],
    extraction: dict[str, Any],
    packet: dict[str, Any],
    evidence_rows: dict[str, dict[str, Any]],
) -> list[str]:
    errors = [f"reviewer_a:{error}" for error in validate_review_payload(reviewer_a, extraction, packet, evidence_rows)]
    errors.extend(f"reviewer_b:{error}" for error in validate_review_payload(reviewer_b, extraction, packet, evidence_rows))
    reviewer_a_id = str(reviewer_a.get("reviewer_id") or "").strip()
    reviewer_b_id = str(reviewer_b.get("reviewer_id") or "").strip()
    if reviewer_a_id and reviewer_a_id == reviewer_b_id:
        errors.append("reviewer_identity_not_distinct")
    cases_a = {str(case.get("case_id")): case for case in reviewer_a.get("cases", [])}
    cases_b = {str(case.get("case_id")): case for case in reviewer_b.get("cases", [])}
    if set(cases_a) != set(cases_b):
        errors.append("reviewer_case_sets_mismatch")
    for case_id in sorted(set(cases_a) & set(cases_b)):
        ids_a = {_review_requirement_id(row) for row in _review_rows(cases_a[case_id])}
        ids_b = {_review_requirement_id(row) for row in _review_rows(cases_b[case_id])}
        if ids_a != ids_b:
            errors.append(f"{case_id}:reviewer_requirement_sets_mismatch")
    return sorted(set(errors))


def validate_review_file(
    review_path: Path,
    extraction_path: Path,
    packet_path: Path,
    evidence_path: Path,
) -> list[str]:
    return validate_review_payload(
        _load(review_path),
        _load(extraction_path),
        _load(packet_path),
        _evidence_map(evidence_path),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("review", type=Path)
    parser.add_argument("--review-b", type=Path)
    parser.add_argument("--extraction", type=Path, default=Path("data/fitcv-p0-corpus/p0b/p0b_holdout_requirement_extraction_v1.json"))
    parser.add_argument("--packet", type=Path, default=Path("data/fitcv-p0-corpus/p0b/p0b_holdout_source_review_packet_v1.json"))
    parser.add_argument("--evidence", type=Path, default=Path("data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl"))
    args = parser.parse_args()
    extraction = _load(args.extraction)
    packet = _load(args.packet)
    evidence = _evidence_map(args.evidence)
    if args.review_b:
        errors = validate_review_pair(_load(args.review), _load(args.review_b), extraction, packet, evidence)
    else:
        errors = validate_review_file(args.review, args.extraction, args.packet, args.evidence)
    print(json.dumps({"status": "valid" if not errors else "invalid", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
