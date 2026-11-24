from __future__ import annotations

import json
from pathlib import Path

import pytest

from fitcv.contracts import build_requirement_occurrences
from fitcv.shortlist_selection import (
    assess_requirement_occurrences,
    build_coverage_summary,
    build_pareto_fronts,
    build_requirement_aware_rows,
    select_requirement_aware_jobs,
)


def test_occurrences_preserve_duplicate_clauses_and_compound_metadata() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-1",
            "required_skill_entities": [
                {"raw_text": "Python", "canonical": "python", "source_requirement_id": "req-1"},
                {"raw_text": "Python", "canonical": "python", "source_requirement_id": "req-2"},
            ],
            "requirement_occurrences": [
                {
                    "occurrence_id": "compound-1",
                    "category": "required",
                    "source_wording": "Power BI OR Tableau",
                    "compound_operator": "OR",
                    "child_occurrence_ids": ["child-1", "child-2"],
                }
            ],
        }
    )

    assert len(occurrences) == 3
    assert occurrences[0].occurrence_id != occurrences[1].occurrence_id
    compound = next(item for item in occurrences if item.occurrence_id == "compound-1")
    assert compound.compound_operator == "OR"
    assert compound.child_occurrence_ids == ("child-1", "child-2")


def test_projection_maps_support_partial_no_support_unknown_and_contradiction() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-2",
            "requirement_occurrences": [
                {"occurrence_id": "s", "category": "required", "source_wording": "Python"},
                {"occurrence_id": "p", "category": "required", "source_wording": "Azure in production"},
                {"occurrence_id": "e", "category": "duties", "source_wording": "Reporting"},
                {"occurrence_id": "u", "category": "preferred", "source_wording": "German"},
                {"occurrence_id": "ns", "category": "required", "source_wording": "Kafka"},
                {"occurrence_id": "q", "category": "required", "source_wording": "Azure in production"},
            ],
        }
    )
    assessments = assess_requirement_occurrences(
        occurrences,
        [
            {"occurrence_id": "s", "support_status": "supported", "evidence_id": "ev-s", "provenance_grade": 3},
            {"occurrence_id": "p", "support_status": "partial", "evidence_id": "ev-p", "qualifier_status": "unverified"},
            {"occurrence_id": "e", "support_status": "unsupported", "reviewed": True},
            {"occurrence_id": "u", "status": "pending", "evidence_id": "ev-u"},
            {"occurrence_id": "ns", "status": "not_selected", "verified": True, "evidence_id": "ev-ns"},
            {"occurrence_id": "q", "support_status": "supported", "qualifier_status": "unverified", "evidence_id": "ev-q"},
            {"occurrence_id": "p", "support_status": "partial", "contradiction": True, "evidence_id": "ev-p2"},
        ]
    )
    by_id = {row["occurrence_id"]: row for row in assessments}

    assert {row["state"] for row in assessments} == {"S", "P", "E", "U"}
    assert by_id["p"]["contradiction"] is True
    assert by_id["s"]["evidence_ids"] == ["ev-s"]

    summary = build_coverage_summary(assessments)
    assert summary["required"]["ratio"] == 0.5
    assert summary["duties"]["ratio"] == 0.0
    assert summary["unknown_rate"] == 1 / 6
    assert summary["confirmed_critical_gaps"] == 1


def test_incomplete_assessment_maps_missing_occurrence_to_unknown() -> None:
    occurrences = build_requirement_occurrences(
        {"job_url": "job-incomplete", "requirement_occurrences": [{"occurrence_id": "req-1", "category": "required", "source_wording": "Python"}]}
    )
    result = assess_requirement_occurrences(occurrences, [], assessment_complete=False)
    assert result[0]["state"] == "U"


def test_requirement_assessment_ids_match_normalized_and_instance_references() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-reference-forms",
            "required_skill_entities": [
                {
                    "raw_text": "Data-driven analytical methods",
                    "canonical": "data_driven_analytical_methods",
                },
                {
                    "raw_text": "Model development and optimization",
                    "canonical": "model_development_and_optimization",
                },
            ],
        }
    )

    assessments = assess_requirement_occurrences(
        occurrences,
        [
            {
                "requirement_id": "required_skill:data-driven analytical methods",
                "support_status": "supported",
                "evidence_id": "ev-data-driven",
            },
            {
                "requirement_id": "required_skill_instance:model development and optimization:abc123",
                "support_status": "supported",
                "evidence_id": "ev-model",
            },
        ],
    )

    assert [item["state"] for item in assessments] == ["S", "S"]


def test_authoritative_identity_mismatch_does_not_fallback_to_duplicate_wording() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-duplicate-wording",
            "requirement_occurrences": [
                {"occurrence_id": "req-a", "category": "required", "source_wording": "Python"},
                {"occurrence_id": "req-b", "category": "required", "source_wording": "Python"},
            ],
        }
    )

    assessments = assess_requirement_occurrences(
        occurrences,
        [
            {"occurrence_id": "req-a", "source_wording": "Python", "support_status": "supported"},
            {"requirement_id": "unrelated", "source_wording": "Python", "support_status": "supported"},
        ]
    )

    by_id = {item["occurrence_id"]: item for item in assessments}
    assert by_id["req-a"]["state"] == "S"
    assert by_id["req-b"]["state"] == "E"


def test_identity_free_wording_fallback_requires_one_top_level_occurrence() -> None:
    duplicate = build_requirement_occurrences(
        {
            "job_url": "job-duplicate-wording",
            "requirement_occurrences": [
                {"occurrence_id": "req-a", "category": "required", "source_wording": "Python"},
                {"occurrence_id": "req-b", "category": "required", "source_wording": "Python"},
            ],
        }
    )
    duplicate_result = assess_requirement_occurrences(
        duplicate,
        [{"source_wording": "Python", "support_status": "supported"}],
    )
    assert [item["state"] for item in duplicate_result] == ["E", "E"]

    unique = build_requirement_occurrences(
        {
            "job_url": "job-unique-wording",
            "requirement_occurrences": [
                {"occurrence_id": "req-a", "category": "required", "source_wording": "Python"},
                {"occurrence_id": "req-b", "category": "required", "source_wording": "Tableau"},
            ],
        }
    )
    unique_result = assess_requirement_occurrences(
        unique,
        [{"source_wording": "Python", "support_status": "supported"}],
    )
    assert [item["state"] for item in unique_result] == ["S", "E"]


def test_mandatory_clause_occurrences_preserve_wording_and_source_span() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-mandatory-clause",
            "mandatory_clauses": [
                {
                    "clause_id": "clause-1",
                    "value": "Enrolled in a quantitative master's programme",
                    "source_spans": [{"source_field": "description", "text": "Enrolled in a quantitative master's programme"}],
                }
            ],
        }
    )

    assert occurrences[0].source_requirement_id == "clause-1"
    assert occurrences[0].source_wording == "Enrolled in a quantitative master's programme"
    assert occurrences[0].source_span == [
        {"source_field": "description", "text": "Enrolled in a quantitative master's programme"}
    ]


def test_compound_and_or_logic_and_cycle_guard() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-3",
            "requirement_occurrences": [
                {"occurrence_id": "and", "category": "required", "source_wording": "A and B", "compound_operator": "AND", "child_occurrence_ids": ["a", "b"]},
                {"occurrence_id": "a", "category": "required", "source_wording": "A"},
                {"occurrence_id": "b", "category": "required", "source_wording": "B"},
                {"occurrence_id": "or", "category": "required", "source_wording": "C or D", "compound_operator": "OR", "child_occurrence_ids": ["c", "d"]},
                {"occurrence_id": "c", "category": "required", "source_wording": "C"},
                {"occurrence_id": "d", "category": "required", "source_wording": "D"},
            ],
        }
    )
    assessments = assess_requirement_occurrences(
        occurrences,
        [
            {"occurrence_id": "a", "support_status": "supported"},
            {"occurrence_id": "b", "support_status": "partial"},
            {"occurrence_id": "c", "support_status": "unsupported", "reviewed": True},
            {"occurrence_id": "d", "support_status": "supported"},
        ]
    )
    by_id = {row["occurrence_id"]: row for row in assessments}
    assert by_id["and"]["state"] == "P"
    assert by_id["or"]["state"] == "S"


def test_or_provenance_uses_only_the_best_satisfying_alternative() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-or-provenance",
            "requirement_occurrences": [
                {"occurrence_id": "or", "category": "required", "source_wording": "A or B", "compound_operator": "OR", "child_occurrence_ids": ["a", "b"]},
                {"occurrence_id": "a", "category": "required", "source_wording": "A"},
                {"occurrence_id": "b", "category": "required", "source_wording": "B"},
            ],
        }
    )
    assessments = assess_requirement_occurrences(
        occurrences,
        [
            {"occurrence_id": "a", "support_status": "supported", "evidence_id": "ev-a", "provenance_grade": 3},
            {"occurrence_id": "b", "support_status": "partial", "evidence_id": "ev-b", "provenance_grade": 1, "contradiction": True},
        ]
    )
    compound = next(item for item in assessments if item["occurrence_id"] == "or")
    assert compound["state"] == "S"
    assert compound["evidence_ids"] == ["ev-a"]
    assert compound["provenance"] == 3
    assert compound["contradiction"] is False
    assert compound["satisfying_child_ids"] == ["a"]


def test_supported_or_branch_does_not_inherit_failure_from_unused_branch() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-or-failure",
            "requirement_occurrences": [
                {
                    "occurrence_id": "or",
                    "category": "required",
                    "source_wording": "A or B",
                    "compound_operator": "OR",
                    "child_occurrence_ids": ["a", "b"],
                },
                {"occurrence_id": "a", "category": "required", "source_wording": "A"},
                {"occurrence_id": "b", "category": "required", "source_wording": "B"},
            ],
        }
    )

    result = {row["occurrence_id"]: row for row in assess_requirement_occurrences(
        occurrences,
        [
            {"occurrence_id": "a", "support_status": "supported", "evidence_id": "ev-a"},
            {"occurrence_id": "b", "status": "assessment_failed", "failure_derived": True},
        ],
    )}

    assert result["or"]["state"] == "S"
    assert result["or"]["failure_derived"] is False
    assert result["or"]["assessment_complete"] is True
    assert result["or"]["retry_eligible"] is False


def test_equal_or_branches_union_provenance_and_evidence_deterministically() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-or-tie",
            "requirement_occurrences": [
                {
                    "occurrence_id": "or",
                    "category": "required",
                    "source_wording": "A or B",
                    "compound_operator": "OR",
                    "child_occurrence_ids": ["b", "a"],
                },
                {"occurrence_id": "b", "category": "required", "source_wording": "B"},
                {"occurrence_id": "a", "category": "required", "source_wording": "A"},
            ],
        }
    )
    result = {row["occurrence_id"]: row for row in assess_requirement_occurrences(
        occurrences,
        [
            {"occurrence_id": "b", "support_status": "partial", "evidence_id": "ev-b", "provenance_grade": 2},
            {"occurrence_id": "a", "support_status": "partial", "evidence_id": "ev-a", "provenance_grade": 2},
        ],
    )}["or"]

    assert result["satisfying_child_ids"] == ["a", "b"]
    assert result["evidence_ids"] == ["ev-a", "ev-b"]
    assert result["display_representative_occurrence_id"] == "a"


def test_coverage_summary_keeps_only_top_level_states_and_child_diagnostics() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "job-compound-summary",
            "requirement_occurrences": [
                {"occurrence_id": "and", "category": "required", "source_wording": "A and B", "compound_operator": "AND", "child_occurrence_ids": ["a", "b"]},
                {"occurrence_id": "a", "category": "required", "source_wording": "A"},
                {"occurrence_id": "b", "category": "required", "source_wording": "B"},
            ],
        }
    )
    summary = build_coverage_summary(
        assess_requirement_occurrences(
            occurrences,
            [
                {"occurrence_id": "a", "support_status": "supported", "evidence_id": "ev-a"},
                {"occurrence_id": "b", "support_status": "supported", "evidence_id": "ev-b"},
            ],
        )
    )
    assert [item["occurrence_id"] for item in summary["states"]] == ["and"]
    assert {item["occurrence_id"] for item in summary["compound_diagnostics"]} == {"a", "b"}
    assert summary["total"] == 1


def test_tie_break_ignores_balanced_support_and_assessment_completeness() -> None:
    def make(identity: str, balanced: float, completeness: float) -> dict:
        return {
            "canonical_job_identity": identity,
            "coverage": {
                "active_core_mask": {"required": True, "duties": False},
                "required": {"ratio": 1.0},
                "duties": {"ratio": None},
                "preferred": {"ratio": 0.5},
                "balanced_core_support": balanced,
                "assessment_completeness": completeness,
                "evidence_validity_provenance": 2,
                "confirmed_critical_gaps": 0,
            },
        }

    result = select_requirement_aware_jobs(
        [make("b", 1.0, 1.0), make("a", 0.1, 0.0)],
        capacity=1,
    )
    assert result["admitted"][0]["canonical_job_identity"] == "a"


@pytest.mark.parametrize(
    ("required", "duties"),
    [(None, None), (1.0, None), (None, 1.0), (1.0, 1.0)],
)
def test_core_metric_masks_preserve_na_categories(required: float | None, duties: float | None) -> None:
    def occurrence(category: str, occurrence_id: str) -> dict:
        return {"occurrence_id": occurrence_id, "category": category, "source_wording": occurrence_id}

    raw_occurrences = []
    evidence = []
    if required is not None:
        raw_occurrences.append(occurrence("required", "required"))
        evidence.append({"occurrence_id": "required", "support_status": "supported"})
    if duties is not None:
        raw_occurrences.append(occurrence("duties", "duties"))
        evidence.append({"occurrence_id": "duties", "support_status": "supported"})
    occurrences = build_requirement_occurrences({"job_url": "mask", "requirement_occurrences": raw_occurrences})
    summary = build_coverage_summary(assess_requirement_occurrences(occurrences, evidence))
    assert summary["required"]["active"] is (required is not None)
    assert summary["duties"]["active"] is (duties is not None)
    assert summary["required"]["ratio"] == required
    assert summary["duties"]["ratio"] == duties


def test_pareto_masks_prevent_na_comparisons_and_capacity_keeps_decisions() -> None:
    def row(identity: str, required: float | None, duties: float | None, preferred: float | None = 0.0) -> dict:
        def metric(ratio: float | None) -> dict:
            return {"supported": int(ratio or 0), "partial": 0, "not_evidenced": 0, "unknown": 0, "total": 1 if ratio is not None else 0, "ratio": ratio, "active": ratio is not None}

        return {
            "canonical_job_identity": identity,
            "coverage": {
                "required": metric(required),
                "duties": metric(duties),
                "preferred": metric(preferred),
                "active_core_mask": {"required": required is not None, "duties": duties is not None},
                "balanced_core_support": min(value for value in (required, duties) if value is not None) if any(value is not None for value in (required, duties)) else None,
                "assessment_completeness": 1.0,
                "evidence_validity_provenance": 3,
                "confirmed_critical_gaps": 0,
            },
        }

    rows = [row("b", 1.0, 0.0), row("a", 0.5, 0.5), row("na", 1.0, None), row("c", 0.4, 0.4)]
    fronts = build_pareto_fronts(rows)
    assert {item["canonical_job_identity"] for item in fronts[0]} == {"a", "b", "na"}
    result = select_requirement_aware_jobs(rows, capacity=2)
    assert len(result["admitted"]) == 2
    assert len(result["non_admitted"]) == 2
    assert all("exclusion_reason" in item for item in result["rows"])
    assert result["admission_capacity"] == 2


def test_selector_is_deterministic_under_input_permutation() -> None:
    rows = [
        {"canonical_job_identity": "b", "coverage": {"active_core_mask": {"required": True, "duties": False}, "required": {"ratio": 1.0}, "duties": {"ratio": None}, "preferred": {"ratio": 0.0}, "balanced_core_support": 1.0, "assessment_completeness": 1.0, "evidence_validity_provenance": 2, "confirmed_critical_gaps": 0}},
        {"canonical_job_identity": "a", "coverage": {"active_core_mask": {"required": True, "duties": False}, "required": {"ratio": 1.0}, "duties": {"ratio": None}, "preferred": {"ratio": 0.0}, "balanced_core_support": 1.0, "assessment_completeness": 1.0, "evidence_validity_provenance": 2, "confirmed_critical_gaps": 0}},
    ]
    first = select_requirement_aware_jobs(rows, capacity=1)
    second = select_requirement_aware_jobs(list(reversed(rows)), capacity=1)
    assert [row["canonical_job_identity"] for row in first["rows"]] == [row["canonical_job_identity"] for row in second["rows"]]
    assert first["decision_fingerprint"] == second["decision_fingerprint"]


def test_pareto_front_extraction_remains_acyclic_across_na_masks() -> None:
    def make(identity: str, required: float | None, duties: float | None) -> dict:
        return {
            "canonical_job_identity": identity,
            "coverage": {
                "required": {"ratio": required},
                "duties": {"ratio": duties},
                "active_core_mask": {"required": required is not None, "duties": duties is not None},
                "balanced_core_support": min(value for value in (required, duties) if value is not None),
                "assessment_completeness": 1.0,
                "evidence_validity_provenance": 1,
                "confirmed_critical_gaps": 0,
            },
        }

    rows = [
        make("a", 0.9, 0.2),
        make("b", 0.8, None),
        make("c", 0.7, 0.9),
        make("d", None, 0.8),
    ]
    fronts = build_pareto_fronts(rows)
    assert fronts
    assert {row["canonical_job_identity"] for row in sum(fronts, [])} == {"a", "b", "c", "d"}


def test_tie_break_prefers_evidence_provenance_before_preferred_coverage() -> None:
    def make(identity: str, provenance: int, preferred: float) -> dict:
        return {
            "canonical_job_identity": identity,
            "coverage": {
                "active_core_mask": {"required": True, "duties": False},
                "required": {"ratio": 1.0},
                "duties": {"ratio": None},
                "preferred": {"ratio": preferred},
                "balanced_core_support": 1.0,
                "assessment_completeness": 1.0,
                "evidence_validity_provenance": provenance,
                "confirmed_critical_gaps": 0,
            },
        }

    result = select_requirement_aware_jobs([make("low-evidence", 1, 1.0), make("verified", 3, 0.0)], capacity=1)
    assert result["admitted"][0]["canonical_job_identity"] == "verified"


def test_requirement_aware_admission_fixture_exercises_capacity_overflow() -> None:
    fixture = json.loads(Path("tests/fixtures/requirement_aware_admission_pool.json").read_text())
    rows = fixture["jobs"]

    assert len(rows) > fixture["admission_capacity"]
    assert any(row["legacy_excluded"] and row["label"] == "relevant" for row in rows)
    result = select_requirement_aware_jobs(rows, capacity=fixture["admission_capacity"])

    assert len(result["admitted"]) == 50
    assert len(result["non_admitted"]) == 1
    assert result["non_admitted"][0]["exclusion_reason"] == "capacity_exceeded"


def test_nested_compound_children_are_not_counted_as_active_requirements() -> None:
    occurrences = build_requirement_occurrences(
        {
            "job_url": "nested-compound",
            "requirement_occurrences": [
                {
                    "occurrence_id": "outer",
                    "category": "required",
                    "source_wording": "A and (B or C)",
                    "compound_operator": "AND",
                    "child_occurrence_ids": ["leaf-a", "inner"],
                },
                {
                    "occurrence_id": "inner",
                    "category": "required",
                    "source_wording": "B or C",
                    "compound_operator": "OR",
                    "child_occurrence_ids": ["leaf-b", "leaf-c"],
                },
                {"occurrence_id": "leaf-a", "category": "required", "source_wording": "A"},
                {"occurrence_id": "leaf-b", "category": "required", "source_wording": "B"},
                {"occurrence_id": "leaf-c", "category": "required", "source_wording": "C"},
            ],
        }
    )
    assessments = assess_requirement_occurrences(
        occurrences,
        [
            {"occurrence_id": "leaf-a", "support_status": "supported", "evidence_id": "a"},
            {"occurrence_id": "leaf-b", "support_status": "supported", "evidence_id": "b"},
        ],
    )

    summary = build_coverage_summary(assessments)
    assert summary["required"]["total"] == 1
    assert summary["required"]["ratio"] == 1.0


def test_legacy_requirement_coverage_preserves_all_support_evidence_ids() -> None:
    rows = build_requirement_aware_rows(
        [
            {
                "job_url": "legacy-coverage",
                "requirement_occurrences": [
                    {"occurrence_id": "req-1", "category": "duties", "source_wording": "Coordinate stakeholders"}
                ],
                "requirement_coverage": [
                    {
                        "requirement_id": "req-1",
                        "selected_support": "verified",
                        "supporting_evidence_ids": ["ev-a", "ev-b"],
                    }
                ],
            }
        ]
    )

    assert rows[0]["coverage"]["duties"]["ratio"] == 1.0
    assert rows[0]["coverage"]["evidence_validity_provenance"] == 1
