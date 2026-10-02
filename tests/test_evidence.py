"""
@meta
type: test
scope: unit
domain: evidence
covers:
  - normalise_evidence_item: stable UUID, typed schema
  - score_evidence_item: weighted scoring
  - retrieve_evidence: ranking, top_k, all evidence types
excludes:
tags:
  - fast
  - ci-safe
"""

import ast
import copy
from pathlib import Path

import pytest
import yaml

from fitcv import evidence as evidence_module
from fitcv.candidate import canonical_candidate_checksum
from fitcv.config import apply_runtime_synonym_overlay
from fitcv.evidence import (
    build_required_skill_descriptors,
    build_profile_evidence_pool,
    project_candidate_evidence,
    retrieve_evidence,
    retrieve_evidence_bundle,
    score_evidence_item,
    select_ranking_evidence,
)
from fitcv.ranking import compute_title_relevance



def _stable_contract_view(value: object) -> object:
    if isinstance(value, dict):
        return {
            str(key): _stable_contract_view(value[key])
            for key in sorted(value)
            if key != "runtime_telemetry"
        }
    if isinstance(value, list):
        return [_stable_contract_view(item) for item in value]
    return value

def _v2_profile() -> dict:
    return yaml.safe_load(Path("data/candidate_profile.v2.sample.yaml").read_text(encoding="utf-8"))


def _cached_evidence_profile(*items: dict) -> dict:
    return {
        "schema_version": "candidate-profile.v2",
        "_projected_evidence_pool": [dict(item) for item in items],
    }


def _cached_evidence_item(evidence_id: str, skills: list[str], scoring_context: str) -> dict:
    return {
        "schema_version": "candidate-evidence.v1",
        "evidence_id": evidence_id,
        "kind": "project",
        "title": evidence_id,
        "text": scoring_context,
        "source_section": "projects",
        "parent_id": evidence_id,
        "source_refs": [{"document_id": f"doc-{evidence_id}"}],
        "evidence_type": "candidate_evidence",
        "name": evidence_id,
        "skills": list(skills),
        "scoring_context": scoring_context,
        "business_value": scoring_context,
        "role": "Data Engineer",
        "company": "Example",
    }

def test_uniform_projection_walks_every_evidence_section_once() -> None:
    profile = _v2_profile()
    document_id = profile["source_documents"][0]["id"]
    shared_ref = [{"document_id": document_id}]
    profile["achievements"] = [
        {
            "id": "achievement_1",
            "title": "Analytics Award",
            "source_refs": shared_ref,
            "evidence": [{"id": "ev_achievement_1", "kind": "achievement", "text": "Won analytics award", "source_refs": shared_ref}],
        }
    ]
    profile["certifications"] = [
        {
            "id": "certification_1",
            "name": "SQL Certificate",
            "issuer": "Example",
            "source_refs": shared_ref,
            "evidence": [{"id": "ev_certification_1", "kind": "certification_proof", "text": "Passed SQL certification", "source_refs": shared_ref}],
        }
    ]
    profile["volunteering"] = [
        {
            "id": "volunteering_1",
            "organization": "Data Club",
            "role": "Mentor",
            "source_refs": shared_ref,
            "evidence": [{"id": "ev_volunteering_1", "kind": "volunteer_contribution", "text": "Mentored SQL learners", "source_refs": shared_ref}],
        }
    ]
    profile["skills"].append(
        {
            "id": "skill_unsupported",
            "name": "Unsupported skill",
            "origin": "user",
            "confidence": 1.0,
            "support_status": "unsupported",
            "evidence_refs": ["ev_exp_reporting_automation"],
        }
    )

    projected = project_candidate_evidence(profile)

    assert {item["source_section"] for item in projected} == {
        "experiences",
        "education",
        "projects",
        "achievements",
        "certifications",
        "volunteering",
    }
    assert len(projected) == sum(
        len(parent.get("evidence") or [])
        for section in ("experiences", "education", "projects", "achievements", "certifications", "volunteering")
        for parent in profile[section]
    )
    sql = next(item for item in projected if item["evidence_id"] == "ev_exp_reporting_automation")
    assert sql["skills"] == ["Python", "SQL"]
    assert "Unsupported skill" not in sql["skills"]
    assert sql["parent_id"] == "exp_reporting_assistant"
    assert sql["organization"] == "Example Retail Company"

def test_uniform_projection_supports_education_only_and_is_deterministic() -> None:
    profile = _v2_profile()
    profile["experiences"] = []
    profile["projects"] = []
    profile["achievements"] = []
    profile["certifications"] = []
    profile["volunteering"] = []
    evidence_ids = {
        item["id"] for parent in profile["education"] for item in parent["evidence"]
    }
    for skill in profile["skills"]:
        skill["evidence_refs"] = [ref for ref in skill["evidence_refs"] if ref in evidence_ids]
        skill["support_status"] = "supported" if skill["evidence_refs"] else "unsupported"
    before = copy.deepcopy(profile)
    checksum = canonical_candidate_checksum(profile)

    first = retrieve_evidence_bundle(profile, {"required_skills": ["Python", "Statistics"]}, 10)
    second = retrieve_evidence_bundle(profile, {"required_skills": ["Python", "Statistics"]}, 10)

    assert first["projection_schema_version"] == "candidate-evidence.v1"
    assert first["source_profile_schema_version"] == "candidate-profile.v2"
    assert first["projection_fingerprint"] == second["projection_fingerprint"]
    assert {item["source_section"] for item in first["selected_evidence"]} == {"education"}
    assert profile == before
    assert canonical_candidate_checksum(profile) == checksum


def test_requirement_support_uses_explicit_canonical_skill_links() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item("ev-sql", ["SQL"], "Built SQL reports"),
        _cached_evidence_item("ev-python", ["Python"], "Built Python pipelines"),
    )
    bundle = retrieve_evidence_bundle(
        profile,
        {
            "required_skills": ["SQL", "Python"],
            "required_skill_entities": [
                {"raw_text": "SQL", "canonical": "sql"},
                {"raw_text": "Python", "canonical": "python"},
            ],
        },
        1,
        config={
            "cv_analysis": {
                "semantic_alignment": {"enabled": False},
                "selection_policy": {"requirement_gain_weight": 0.0},
            }
        },
    )

    support = bundle["requirement_support"]
    assert set(support["pool"]) == {"required_skill:sql", "required_skill:python"}
    assert len(bundle["selected_evidence"]) == 1
    selected_ids = set(bundle["selected_evidence_ids"])
    assert sum(len(ids) for ids in support["selected"].values()) == 1
    assert all(
        evidence_id in selected_ids
        for evidence_ids in support["selected"].values()
        for evidence_id in evidence_ids
    )
    assert set(support["canonical"]) == {"required_skill:sql", "required_skill:python"}


def test_requirement_support_reports_canonical_retrieved_and_selected_layers() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item("ev-sql", ["SQL"], "Built SQL reports"),
        _cached_evidence_item("ev-python", ["Python"], "Built Python pipelines"),
    )

    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["SQL", "Python"]},
        1,
        config={"cv_analysis": {"semantic_alignment": {"enabled": False}}},
    )

    support = bundle["requirement_support"]
    assert support["canonical"] == support["pool"]
    assert set(support["selected"]) <= set(support["pool"])


def test_requirement_support_annotations_reach_channel_selection() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item("ev-a-distractor", ["Java"], "Java"),
        _cached_evidence_item("ev-z-target", ["Python"], "Python"),
    )
    profile["_projected_evidence_pool"][0]["role"] = "Python"

    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["Python"], "job_title": "Python"},
        1,
        config={
            "cv_analysis": {
                "semantic_alignment": {"enabled": False, "channel_pool_size": 2},
                "selection_policy": {
                    "channel_weights": {channel: 0.0 for channel in evidence_module.RETRIEVAL_CHANNELS},
                    "multi_channel_bonus": 0.0,
                    "residual_score_factor": 0.05,
                    "requirement_gain_weight": 1.0,
                },
            }
        },
    )

    assert bundle["selected_evidence_ids"] == ["ev-z-target"]


def test_semantic_alignment_reports_actual_embedding_backend() -> None:
    profile = _cached_evidence_profile(_cached_evidence_item("ev-sql", ["SQL"], "Built SQL reports"))
    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["SQL"]},
        1,
        config={
            "cv_analysis": {
                "semantic_alignment": {
                    "enabled": True,
                    "model": "text-embedding-005",
                }
            }
        },
    )

    backend = bundle["semantic_alignment"]["embedding_backend"]
    assert backend["backend_id"] == "sqlite_deterministic_local"
    assert backend["configured_model"] == "text-embedding-005"
    assert backend["dimension"] > 0
    assert backend["contract_fingerprint"]


def test_disabled_semantic_alignment_reports_no_embedding_backend() -> None:
    profile = _cached_evidence_profile(_cached_evidence_item("ev-sql", ["SQL"], "Built SQL reports"))
    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["SQL"]},
        1,
        config={"cv_analysis": {"semantic_alignment": {"enabled": False}}},
    )

    assert bundle["semantic_alignment"]["embedding_backend"]["backend_id"] == "disabled"
    assert bundle["semantic_alignment"]["embedding_backend"]["dimension"] is None


def test_required_skill_descriptors_do_not_pair_reordered_arrays_by_position() -> None:
    descriptors = build_required_skill_descriptors(
        {
            "required_skills": ["SQL", "Python"],
            "required_skills_canonical": ["python", "sql"],
        }
    )

    by_requirement = {item["requirement"]: item for item in descriptors}

    assert by_requirement["SQL"]["canonical_skill"] == "sql"
    assert by_requirement["Python"]["canonical_skill"] == "python"


def test_required_skill_descriptors_collapse_raw_aliases_without_entities() -> None:
    descriptors = build_required_skill_descriptors(
        {"required_skills": ["SQL", "sql", "Python"]}
    )

    by_canonical = {item["canonical_skill"]: item for item in descriptors}

    assert set(by_canonical) == {"sql", "python"}
    assert by_canonical["sql"]["original_requirements"] == ["SQL", "sql"]


def test_required_skill_descriptors_support_canonical_only_input() -> None:
    descriptors = build_required_skill_descriptors(
        {"required_skills_canonical": ["sql", "python"]}
    )

    assert [(item["requirement_id"], item["requirement"]) for item in descriptors] == [
        ("required_skill:sql", "sql"),
        ("required_skill:python", "python"),
    ]


def test_required_skill_descriptors_ignore_incomplete_entity_rows() -> None:
    descriptors = build_required_skill_descriptors(
        {
            "required_skills": ["SQL", "Python"],
            "required_skill_entities": [
                {"raw_text": "SQL", "canonical": "sql"},
                {"raw_text": "Python"},
                {"canonical": ""},
                "invalid",
            ],
        }
    )

    assert descriptors == [
        {
            "requirement_id": "required_skill:sql",
            "requirement": "SQL",
            "canonical_skill": "sql",
            "original_requirements": ["SQL"],
            "requirement_type": "required_skill",
            "requirement_priority": "must_have",
        },
        {
            "requirement_id": "required_skill:python",
            "requirement": "Python",
            "canonical_skill": "python",
            "original_requirements": ["Python"],
            "requirement_type": "required_skill",
            "requirement_priority": "must_have",
        },
    ]


def test_required_skill_descriptors_keep_same_text_source_ids_distinct() -> None:
    descriptors = build_required_skill_descriptors(
        {
            "required_skill_entities": [
                {"raw_text": "Python", "canonical": "python", "source_requirement_id": "req-1"},
                {"raw_text": "Python", "canonical": "python", "source_requirement_id": "req-2"},
            ]
        }
    )

    assert [item["source_requirement_id"] for item in descriptors] == ["req-1", "req-2"]
    assert {item["requirement_id"] for item in descriptors} == {"required_skill:python"}
    assert len({item["requirement_instance_id"] for item in descriptors}) == 2


@pytest.mark.parametrize(
    ("requirement", "expected_skill", "expected_qualifiers"),
    [
        (
            "more than 3 years production SQL",
            "sql",
            {"duration": {"comparator": "gt", "months": 36}, "context": {"all_of": ["production"]}},
        ),
        (
            "mindestens 3 Jahre SQL",
            "sql",
            {"duration": {"comparator": "gte", "months": 36}},
        ),
        (
            "SQL in enterprise production",
            "sql",
            {"context": {"all_of": ["enterprise", "production"]}},
        ),
    ],
)
def test_required_skill_descriptors_strip_qualifiers_before_canonicalizing(
    requirement: str,
    expected_skill: str,
    expected_qualifiers: dict,
) -> None:
    descriptor = build_required_skill_descriptors({"required_skills": [requirement]})[0]

    assert descriptor["canonical_skill"] == expected_skill
    assert descriptor["qualifiers"] == expected_qualifiers


def test_qualified_requirement_support_requires_one_evidence_item_to_meet_all_qualifiers() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item(
            "ev-qualified",
            ["SQL"],
            "4 years production SQL in enterprise systems",
        ),
        _cached_evidence_item("ev-duration", ["SQL"], "4 years SQL in classroom training"),
        _cached_evidence_item("ev-context", ["SQL"], "production SQL with no duration stated"),
    )
    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["more than 3 years production SQL"]},
        3,
        config={"cv_analysis": {"semantic_alignment": {"enabled": False}}},
    )

    descriptor = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]
    requirement_ref = descriptor["requirement_instance_id"]
    assert descriptor["canonical_skill"] == "sql"
    assert bundle["requirement_support"]["qualified"]["canonical"] == {
        requirement_ref: ["ev-qualified"]
    }


def test_qualified_requirement_does_not_combine_duration_and_context_across_evidence_items() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item("ev-duration", ["SQL"], "4 years SQL"),
        _cached_evidence_item("ev-context", ["SQL"], "production SQL"),
    )
    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["more than 3 years production SQL"]},
        2,
        config={"cv_analysis": {"semantic_alignment": {"enabled": False}}},
    )

    requirement_ref = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]["requirement_instance_id"]
    assert bundle["requirement_support"]["qualified"]["canonical"] == {}


def test_requirement_support_binds_qualifiers_to_one_structured_bullet() -> None:
    item = evidence_module._normalise_experience_entry(
        {
            "role": "Engineer",
            "company": "Example",
            "bullets": [
                {"text": "5 years production Python", "skills": ["Python"]},
                {"text": "SQL classroom exercises", "skills": ["SQL"]},
            ],
        },
        experience_index=0,
    )
    descriptor = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]

    assessment = evidence_module._assess_requirement_support(item, descriptor, None)

    assert assessment["canonical_match"] is True
    assert assessment["qualified_support"] is False


def test_explicit_source_requirement_id_survives_support_annotation() -> None:
    descriptors = build_required_skill_descriptors(
        {
            "required_skills": ["Marketing background"],
            "required_skill_entities": [
                {
                    "raw_text": "Marketing background",
                    "canonical": "marketing",
                    "source_requirement_id": "req-1",
                }
            ],
        }
    )
    assert descriptors[0]["source_requirement_id"] == "req-1"
    assert evidence_module._descriptor_requirement_ref(descriptors[0]) == "req-1"

    item = _cached_evidence_item("ev-marketing", ["marketing"], "Marketing background")
    annotated = evidence_module._annotate_requirement_support(
        [item], descriptors, None
    )[0]

    assert annotated["supported_requirement_ids"] == ["req-1"]


def test_canonical_projection_keeps_parent_metadata_out_of_qualifier_proof() -> None:
    profile = _v2_profile()
    profile["experiences"] = [
        {
            "id": "exp_production_engineer",
            "role": "Production Engineer",
            "company": "Example",
            "source_refs": [{"document_id": "doc_cv_1"}],
            "evidence": [
                {
                    "id": "ev_sql_classroom",
                    "kind": "work_achievement",
                    "text": "SQL classroom exercises",
                    "source_refs": [{"document_id": "doc_cv_1"}],
                }
            ],
        }
    ]
    profile["skills"] = [
        {
            "id": "skill_sql",
            "name": "SQL",
            "origin": "user",
            "confidence": 1.0,
            "support_status": "supported",
            "evidence_refs": ["ev_sql_classroom"],
        }
    ]

    item = next(
        item for item in project_candidate_evidence(profile)
        if item["evidence_id"] == "ev_sql_classroom"
    )
    descriptor = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]
    assessment = evidence_module._assess_requirement_support(item, descriptor, None)

    assert item["support_fragments"] == [
        {"text": "SQL classroom exercises", "skills": ["sql"]}
    ]
    assert assessment["canonical_match"] is True
    assert assessment["qualifier_status"] == "unverified"
    assert assessment["qualified_support"] is False


def test_ambiguous_support_fragment_fails_qualified_support_closed() -> None:
    item = {
        "skills": ["SQL"],
        "text": "5 years production SQL",
        "support_fragments": [{"text": "5 years production SQL", "skills": []}],
    }
    descriptor = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]

    assessment = evidence_module._assess_requirement_support(item, descriptor, None)

    assert assessment["canonical_match"] is True
    assert assessment["qualifier_status"] == "unverified"
    assert assessment["qualified_support"] is False


def test_requirement_support_accepts_same_statement_duration_and_context() -> None:
    item = evidence_module._normalise_experience_entry(
        {
            "role": "Engineer",
            "company": "Example",
            "bullets": [{"text": "5 years production SQL", "skills": ["SQL"]}],
        },
        experience_index=0,
    )
    descriptor = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]

    assessment = evidence_module._assess_requirement_support(item, descriptor, None)

    assert assessment["qualified_support"] is True


def test_responsibility_support_rejects_negated_experience() -> None:
    support = evidence_module._responsibility_support_map(
        [{"evidence_id": "ev-k8s", "text": "No experience deploying Kubernetes in production"}],
        [{"source_requirement_id": "req-k8s", "text": "Deploy Kubernetes in production"}],
    )

    assert support == {}


def test_responsibility_support_requires_specific_object_match() -> None:
    support = evidence_module._responsibility_support_map(
        [{"evidence_id": "ev-sql", "text": "Build SQL dashboards"}],
        [{"source_requirement_id": "req-sql", "text": "Build SQL pipelines"}],
    )

    assert support == {}


def test_responsibility_support_accepts_reviewed_equivalent_proof() -> None:
    cases = [
        (
            "You reach for a tool instead of grinding through something manually.",
            "Built a framework for coordinating AI coding agents with controlled tool access.",
            {"skills": ["workflow automation"]},
        ),
        (
            "You would rather check twice than be corrected.",
            "Verification before completed work is accepted.",
            {"skills": ["quality assurance"]},
        ),
        (
            "You have strong problem-solving skills.",
            "Conducted consumer research and refined product concepts.",
            {"skills": ["consumer research", "concept validation"]},
        ),
        (
            "Support stakeholder management.",
            "Supported SOP development and interdepartmental coordination.",
            {"skills": ["stakeholder management"]},
        ),
        (
            "Analytical and detail-focused work.",
            "Data Analyst in Power BI.",
            {"source_section": "certifications", "skills": ["microsoft power bi", "reporting"]},
        ),
    ]

    for requirement, evidence, metadata in cases:
        assessment = evidence_module._assess_responsibility_support(
            requirement,
            evidence,
            metadata,
        )
        assert assessment["verified_support"] is True


def test_responsibility_support_preserves_qualifier_and_requirement_boundaries() -> None:
    missing_context = evidence_module._assess_responsibility_support(
        "Deploy Kubernetes in production",
        "Deploy Kubernetes",
    )
    advanced_office = evidence_module._assess_responsibility_support(
        "Advanced MS Office skills",
        "Conducted research using Microsoft Excel",
        {"skills": ["microsoft excel"], "source_section": "experiences"},
    )
    master_degree = evidence_module._assess_responsibility_support(
        "A master's degree in data science",
        "Supply Chain Management",
        {
            "role": "Bachelor's Degree International Business",
            "source_section": "education",
        },
    )

    assert missing_context["qualifier_status"] == "unverified"
    assert missing_context["verified_support"] is False
    assert advanced_office["verified_support"] is False
    assert master_degree["verified_support"] is False


def test_responsibility_support_accepts_bounded_or_compound_requirement_proof() -> None:
    cases = [
        (
            "Sicherer Umgang mit MS Office sowie Online-Systemen und Datenbanken",
            "Prepared recurring analysis and reporting materials in Excel and PowerPoint.",
            {"source_section": "experiences", "skills": ["microsoft excel", "microsoft powerpoint"]},
        ),
        (
            "a bachelor’s degree or higher in data science;",
            "Bachelor's Degree in Data Science",
            {"source_section": "education", "role": "Bachelor's Degree in Data Science"},
        ),
        (
            "a bachelor’s degree or higher in economics, finance, data science or a related field;",
            "Bachelor's Degree in International Business",
            {"source_section": "education", "role": "Bachelor's Degree in International Business"},
        ),
        (
            "Previous experience in executive search, recruitment, research or another professional environment would be beneficial but is not essential.",
            "Managed end-to-end new product development from market research and concept validation to launch.",
            {"source_section": "experiences", "role": "R&D Staff"},
        ),
    ]

    for requirement, evidence, metadata in cases:
        assert evidence_module._assess_responsibility_support(
            requirement,
            evidence,
            metadata,
        )["verified_support"] is True


def test_responsibility_support_rejects_essential_qualifier_mismatches() -> None:
    cases = [
        (
            "a bachelor's degree or higher in computer science",
            "Bachelor's Degree in International Business",
            {"source_section": "education", "role": "Bachelor's Degree in International Business"},
        ),
        (
            "Use Claude Code daily",
            "Used a generic coding tool daily",
            {"source_section": "experiences"},
        ),
        (
            "Experience in executive search",
            "Conducted generic market research",
            {"source_section": "experiences"},
        ),
        (
            "Deploy Kubernetes in production for 3 years",
            "Deployed Kubernetes in production for 1 year",
            {"source_section": "experiences"},
        ),
    ]

    for requirement, evidence, metadata in cases:
        assessment = evidence_module._assess_responsibility_support(
            requirement,
            evidence,
            metadata,
        )
        assert assessment["verified_support"] is False


def test_degree_domain_alternatives_match_complete_concepts_only() -> None:
    cases = [
        (
            "a bachelor's degree or higher in computer science",
            "Bachelor's Degree in Political Science",
            False,
        ),
        (
            "a bachelor's degree or higher in computer science",
            "Bachelor's Degree in International Business",
            False,
        ),
        (
            "a bachelor's degree or higher in computer science or a related field",
            "Bachelor's Degree in Political Science",
            False,
        ),
        (
            "a bachelor's degree or higher in economics, finance, data science",
            "Bachelor's Degree in Finance",
            True,
        ),
        (
            "a bachelor's degree or higher in economics or a related field",
            "Bachelor's Degree in International Business",
            True,
        ),
    ]

    for requirement, evidence, expected in cases:
        assessment = evidence_module._assess_responsibility_support(
            requirement,
            evidence,
            {"source_section": "education", "role": evidence},
        )
        assert assessment["verified_support"] is expected


def test_responsibility_support_does_not_promote_generic_essential_evidence() -> None:
    generic_tool = evidence_module._assess_responsibility_support(
        "Use Claude Code daily",
        "Used a generic tool daily",
    )
    generic_domain = evidence_module._assess_responsibility_support(
        "Experience in executive search",
        "Conducted product-market research",
    )
    exact_tool = evidence_module._assess_responsibility_support(
        "Use Claude Code daily",
        "Used Claude Code daily",
    )
    exact_domain = evidence_module._assess_responsibility_support(
        "Experience in executive search",
        "Conducted executive search research",
    )

    assert generic_tool["candidate_match"] is True
    assert generic_tool["verified_support"] is False
    assert generic_domain["candidate_match"] is True
    assert generic_domain["verified_support"] is False
    assert exact_tool["verified_support"] is True
    assert exact_domain["verified_support"] is True


def test_responsibility_support_requires_all_mandatory_constraint_facts() -> None:
    cases = [
        (
            "Build reports using Python",
            "Built reports using Excel",
            False,
        ),
        (
            "Use Claude Code for at least 3 years",
            "Built a tool for workflow automation",
            False,
        ),
        (
            "Bachelor degree in computer science",
            "Bachelor degree in international business",
            False,
        ),
        (
            "Build reports using Python",
            "Built reports using Python",
            True,
        ),
        (
            "Use Claude Code for at least 3 years",
            "Used Claude Code for 4 years",
            True,
        ),
        (
            "Bachelor degree in computer science",
            "Bachelor degree in computer science",
            True,
        ),
    ]

    for requirement, evidence, expected in cases:
        assessment = evidence_module._assess_responsibility_support(requirement, evidence)

        assert set(assessment) >= {
            "candidate_match",
            "action_match",
            "object_match",
            "entity_match",
            "duration_match",
            "level_domain_match",
            "verified_support",
        }
        assert assessment["verified_support"] is expected


def test_project_fragment_does_not_inherit_unrelated_project_skill() -> None:
    item = evidence_module._normalise_project_entry(
        {
            "name": "Mixed project",
            "skills": ["SQL"],
            "highlights": ["5 years production Python"],
        },
        project_index=0,
    )
    descriptor = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]

    assessment = evidence_module._assess_requirement_support(item, descriptor, None)

    assert assessment["qualified_support"] is False


@pytest.mark.parametrize(
    ("requirement", "evidence", "expected"),
    [
        ("more than 3 years SQL", "less than 4 years SQL", False),
        ("more than 3 years SQL", "more than 4 years SQL", True),
        ("more than 3 years SQL", "at least 3 years SQL", False),
        ("18 months SQL", "2 years SQL", True),
        ("at most 3 years SQL", "2 years SQL", False),
        ("under 3 years SQL", "2 years SQL", False),
        ("no less than 3 years SQL", "4 years SQL", True),
        ("weniger als 3 Jahre SQL", "2 years SQL", False),
    ],
)
def test_duration_qualifiers_compare_intervals(
    requirement: str,
    evidence: str,
    expected: bool,
) -> None:
    requirement_duration = evidence_module._parse_duration_qualifier(requirement)
    evidence_duration = evidence_module._parse_duration_qualifier(evidence)

    assert evidence_module._duration_satisfies(requirement_duration or {}, evidence_duration or {}) is expected


def test_duration_negation_and_german_context_aliases_fail_closed() -> None:
    assert evidence_module._parse_duration_qualifier("without 3 years SQL")["negated"] is True
    descriptor = build_required_skill_descriptors(
        {"required_skills": ["mindestens 3 Jahre Produktionsumgebung SQL"]}
    )[0]
    item = _cached_evidence_item("ev-sql", ["SQL"], "5 Jahre Produktion SQL")

    assessment = evidence_module._assess_requirement_support(item, descriptor, None)

    assert descriptor["qualifiers"]["context"] == {"all_of": ["production"]}
    assert assessment["qualified_support"] is True


def test_qualified_requirement_does_not_transfer_qualifiers_between_skills_in_one_evidence_item() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item(
            "ev-mixed",
            ["SQL", "Python"],
            "4 years production SQL and Python in classroom training",
        )
    )

    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["more than 3 years production SQL"]},
        1,
        config={"cv_analysis": {"semantic_alignment": {"enabled": False}}},
    )

    assert bundle["requirement_support"]["qualified"]["canonical"] == {}


def test_qualified_requirement_uses_same_skill_bound_source_fragment() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item(
            "ev-bound",
            ["SQL", "Python"],
            "4 years production SQL; Python used in classroom training",
        )
    )

    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["more than 3 years production SQL"]},
        1,
        config={"cv_analysis": {"semantic_alignment": {"enabled": False}}},
    )

    requirement_ref = build_required_skill_descriptors(
        {"required_skills": ["more than 3 years production SQL"]}
    )[0]["requirement_instance_id"]
    assert bundle["requirement_support"]["qualified"]["canonical"] == {
        requirement_ref: ["ev-bound"]
    }


def test_requirement_gain_preserves_global_budget_and_weight_zero_matches_baseline() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item("ev-broad", ["SQL"], "SQL Python"),
        _cached_evidence_item("ev-a-sql", ["SQL"], "SQL"),
        _cached_evidence_item("ev-b-python", ["Python"], "Python"),
    )
    job = {
        "required_skills": ["SQL", "Python"],
        "required_skill_entities": [
            {"raw_text": "SQL", "canonical": "sql"},
            {"raw_text": "Python", "canonical": "python"},
        ],
    }
    baseline_config = {
        "cv_analysis": {
            "semantic_alignment": {"enabled": False},
            "selection_policy": {"requirement_gain_weight": 0.0},
        }
    }
    baseline = retrieve_evidence_bundle(profile, job, 2, config=baseline_config)
    explicit_zero = retrieve_evidence_bundle(
        profile,
        job,
        2,
        config={
            "cv_analysis": {
                "semantic_alignment": {"enabled": False},
                "selection_policy": {"requirement_gain_weight": 0.0},
            }
        },
    )
    treatment = retrieve_evidence_bundle(
        profile,
        job,
        2,
        config={
            "cv_analysis": {
                "semantic_alignment": {"enabled": False},
                "selection_policy": {"requirement_gain_weight": 0.10},
            }
        },
    )

    assert baseline["selected_evidence_ids"] == explicit_zero["selected_evidence_ids"]
    assert len(treatment["selected_evidence_ids"]) == 2
    assert baseline["selected_evidence_ids"] != treatment["selected_evidence_ids"]
    assert "ev-b-python" in treatment["selected_evidence_ids"]
    assert treatment["selection_policy"]["requirement_gain_weight"] == 0.10

def test_uniform_projection_does_not_select_equal_cross_section_filler() -> None:
    profile = _v2_profile()
    document_id = profile["source_documents"][0]["id"]
    source_refs = [{"document_id": document_id}]
    profile["experiences"] = [
        {
            "id": "exp_equal",
            "role": "Analyst",
            "company": "Example",
            "source_refs": source_refs,
            "evidence": [{"id": "ev_b", "kind": "work_achievement", "title": "SQL", "text": "Built SQL reports", "source_refs": source_refs}],
        }
    ]
    profile["education"] = [
        {
            "id": "edu_equal",
            "degree": "Analyst",
            "institution": "Example",
            "source_refs": source_refs,
            "evidence": [{"id": "ev_a", "kind": "thesis", "title": "SQL", "text": "Built SQL reports", "source_refs": source_refs}],
        }
    ]
    for section in ("projects", "achievements", "certifications", "volunteering"):
        profile[section] = []
    profile["skills"] = []
    profile["role_families"] = []
    profile["domain_tags"] = []
    profile["responsibility_themes"] = []

    bundle = retrieve_evidence_bundle(profile, {"required_skills": ["SQL"]}, 2)

    assert [item["evidence_id"] for item in bundle["selected_evidence"]] == ["ev_a"]


# ── schema and ordering ───────────────────────────────────────────────────────

def test_retrieve_evidence_returns_normalized_schema() -> None:
    """All returned items must have evidence_id, evidence_type, score, source_ref."""
    mock_profile = {
        "projects": [
            {"name": "GA4", "skills": ["SQL", "BigQuery"], "business_value": "analytics"},
            {"name": "ETL", "skills": ["Python", "Airflow"], "business_value": "automation"},
        ],
        "achievements": [{"text": "Reduced latency", "category": "performance"}],
    }
    jd_skills = ["SQL", "BigQuery"]
    evidence = retrieve_evidence(mock_profile, jd_skills, top_k=3)
    assert len(evidence) <= 3
    assert evidence[0]["name"] == "GA4"  # best match first
    for item in evidence:
        assert "evidence_id" in item
        assert "evidence_type" in item
        assert "score" in item
        assert "source_ref" in item


# ── evidence types ────────────────────────────────────────────────────────────

def test_retrieve_evidence_achievement_with_no_skills() -> None:
    """Achievements with no explicit skills still appear in ranked output."""
    mock_profile = {
        "projects": [],
        "achievements": [{"text": "Promoted to senior engineer", "category": "career"}],
    }
    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "achievement"


def test_retrieve_evidence_experience_bullets() -> None:
    """Experience bullets are included in the ranked pool."""
    mock_profile = {
        "projects": [],
        "achievements": [],
        "experiences": [{
            "role": "DE", "company": "Acme",
            "bullets": [{"text": "Built SQL pipelines", "skills": ["SQL"]}],
        }],
    }
    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "experience_entry"
    assert evidence[0]["role"] == "DE"
    assert evidence[0]["company"] == "Acme"
    assert evidence[0]["bullets"] == ["Built SQL pipelines"]


def test_retrieve_evidence_preserves_multiple_relevant_experience_entries() -> None:
    mock_profile = {
        "projects": [
            {"name": "GA4 Platform", "skills": ["BigQuery", "dbt"], "business_value": "analytics"},
            {"name": "Fraud Detection", "skills": ["Python", "SQL"], "business_value": "fraud"},
        ],
        "achievements": [{"text": "Reduced latency by 40%", "skills": ["BigQuery"]}],
        "experiences": [
            {
                "role": "Senior Data Engineer",
                "company": "Acme",
                "start": "2023-01",
                "end": "present",
                "bullets": [
                    {"text": "Built BigQuery pipelines", "skills": ["BigQuery", "SQL"]},
                    {"text": "Maintained dbt models", "skills": ["dbt", "SQL"]},
                ],
            },
            {
                "role": "Data Engineer",
                "company": "Fintech Startup",
                "start": "2021-06",
                "end": "2022-12",
                "bullets": [
                    {"text": "Implemented fraud detection features", "skills": ["Python", "SQL"]},
                    {"text": "Built self-service reporting", "skills": ["SQL"]},
                ],
            },
        ],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL", "BigQuery", "Python"], top_k=5)

    experience_entries = [item for item in evidence if item["evidence_type"] == "experience_entry"]
    assert len(experience_entries) >= 2
    assert experience_entries[0]["role"] == "Senior Data Engineer"
    assert experience_entries[1]["role"] == "Data Engineer"


def test_retrieve_evidence_project_entry_preserves_rich_fields() -> None:
    mock_profile = {
        "projects": [
            {
                "name": "FitCV",
                "duration": "2024-01 — present",
                "url": "https://example.com/fitcv",
                "skills": ["Python", "BigQuery"],
                "tech_stack": [
                    "Backend: Python, FastAPI",
                    "Data: BigQuery",
                    "AI: Gemini",
                ],
                "business_value": "Reduced CV tailoring time from 2 hours to 5 minutes.",
                "highlights": [
                    "Ingested 5000+ postings",
                    "Achieved 89% relevance score",
                    "Serves 20+ candidates",
                ],
            }
        ],
        "achievements": [],
        "experiences": [],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["Python", "BigQuery", "Gemini"], top_k=5)

    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "project_entry"
    assert evidence[0]["name"] == "FitCV"
    assert evidence[0]["duration"] == "2024-01 — present"
    assert evidence[0]["url"] == "https://example.com/fitcv"
    assert evidence[0]["business_value"] == "Reduced CV tailoring time from 2 hours to 5 minutes."
    assert evidence[0]["tech_stack"] == [
        "Backend: Python, FastAPI",
        "Data: BigQuery",
    ]
    assert evidence[0]["highlights"] == [
        "Ingested 5000+ postings",
        "Achieved 89% relevance score",
    ]


def test_retrieve_evidence_sparse_project_entry_is_valid() -> None:
    mock_profile = {
        "projects": [
            {
                "name": "Internal Reporting Tool",
                "duration": "2022",
                "skills": ["Python", "SQL"],
            }
        ],
        "achievements": [],
        "experiences": [],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["Python"], top_k=5)

    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "project_entry"
    assert evidence[0]["name"] == "Internal Reporting Tool"
    assert evidence[0]["duration"] == "2022"
    assert evidence[0]["skills"] == ["Python", "SQL"]
    assert evidence[0]["tech_stack"] == []
    assert evidence[0]["highlights"] == []
    assert evidence[0]["business_value"] == ""


def test_retrieve_evidence_preserves_multiple_relevant_project_entries() -> None:
    mock_profile = {
        "projects": [
            {
                "name": "FitCV",
                "skills": ["Python", "BigQuery", "Gemini"],
                "business_value": "Reduced CV tailoring time",
                "highlights": ["Ingested 5000+ postings"],
            },
            {
                "name": "Fraud Detection",
                "skills": ["Python", "Kafka", "SQL"],
                "business_value": "Processed 10000 transactions/minute",
                "highlights": ["94% precision"],
            },
        ],
        "achievements": [
            {"text": "Promoted to team lead", "skills": ["Leadership"]},
            {"text": "Published analytics package", "skills": ["Python"]},
        ],
        "experiences": [],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["Python", "SQL", "BigQuery"], top_k=4)

    project_entries = [item for item in evidence if item["evidence_type"] == "project_entry"]
    assert len(project_entries) >= 2
    assert [item["name"] for item in project_entries[:2]] == ["FitCV", "Fraud Detection"]


def test_retrieve_evidence_caps_bullets_within_experience_entries() -> None:
    mock_profile = {
        "projects": [],
        "achievements": [],
        "experiences": [
            {
                "role": "Senior Data Engineer",
                "company": "Acme",
                "start": "2023-01",
                "end": "present",
                "bullets": [
                    {"text": "Built BigQuery pipelines", "skills": ["BigQuery", "SQL"]},
                    {"text": "Maintained dbt models", "skills": ["dbt", "SQL"]},
                    {"text": "Ran Airflow orchestration", "skills": ["Airflow"]},
                ],
            }
        ],
    }

    evidence = retrieve_evidence(mock_profile, jd_skills=["SQL", "BigQuery"], top_k=5)

    assert len(evidence) == 1
    assert evidence[0]["evidence_type"] == "experience_entry"
    assert len(evidence[0]["bullets"]) == 2
    assert evidence[0]["bullets"] == [
        "Built BigQuery pipelines",
        "Maintained dbt models",
    ]


def test_retrieve_evidence_selects_different_experience_bullets_for_different_jds() -> None:
    mock_profile = {
        "projects": [],
        "achievements": [],
        "experiences": [
            {
                "role": "Data Engineer",
                "company": "Fintech Startup",
                "start": "2021-06",
                "end": "2022-12",
                "bullets": [
                    {"text": "Built self-service Looker dashboards for KPI monitoring.", "skills": ["Looker", "Analytics"]},
                    {"text": "Automated KPI reporting workflows for analytics stakeholders.", "skills": ["Python", "Analytics"]},
                    {"text": "Implemented fraud detection features using BigQuery ML.", "skills": ["BigQuery ML", "Python"]},
                ],
            }
        ],
    }

    analytics_evidence = retrieve_evidence(mock_profile, jd_skills=["Analytics", "Looker", "Reporting"], top_k=5)
    ml_evidence = retrieve_evidence(mock_profile, jd_skills=["Python", "BigQuery ML", "Fraud"], top_k=5)

    analytics_bullets = analytics_evidence[0]["bullets"]
    ml_bullets = ml_evidence[0]["bullets"]

    assert analytics_bullets != ml_bullets
    assert "Built self-service Looker dashboards for KPI monitoring." in analytics_bullets
    assert "Implemented fraud detection features using BigQuery ML." in ml_bullets


# ── edge cases ────────────────────────────────────────────────────────────────

def test_retrieve_evidence_empty_jd_skills() -> None:
    """Empty JD skill list: items still returned (no crash), scores are low but defined."""
    mock_profile = {
        "projects": [{"name": "X", "skills": ["SQL"], "business_value": ""}],
        "achievements": [],
    }
    evidence = retrieve_evidence(mock_profile, jd_skills=[], top_k=5)
    assert len(evidence) == 1
    assert 0.0 <= evidence[0]["score"] <= 1.0


def test_retrieve_evidence_tie_breaking_is_deterministic() -> None:
    """Two items with identical scores must return in a stable, deterministic order."""
    mock_profile = {
        "projects": [
            {"name": "A", "skills": ["SQL"], "business_value": ""},
            {"name": "B", "skills": ["SQL"], "business_value": ""},
        ],
        "achievements": [],
    }
    ev1 = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    ev2 = retrieve_evidence(mock_profile, jd_skills=["SQL"], top_k=5)
    assert [e["name"] for e in ev1] == [e["name"] for e in ev2]


def test_retrieve_evidence_bundle_merges_channels_and_dedupes_by_evidence_id() -> None:
    profile = {
        "preferences": {
            "target_role": "Data Analyst",
            "role_families": ["analytics"],
            "domains": ["banking"],
        },
        "experiences": [
            {
                "id": "exp_1",
                "role": "Business Data Analyst",
                "company": "Bank Corp",
                "role_family": "analytics",
                "domain_tags": ["banking"],
                "responsibility_themes": ["dashboarding", "kpi_reporting"],
                "bullets": [
                    {
                        "text": "Built KPI dashboards in Power BI and SQL for banking stakeholders.",
                        "skills": ["SQL", "Power BI"],
                    }
                ],
            }
        ],
        "projects": [],
        "achievements": [],
        "skills": [{"name": "SQL"}],
    }
    job = {
        "job_url": "https://example.com/job-1",
        "title": "Data Analyst - Retail Banking",
        "job_family": "analytics",
        "domain": "banking",
        "required_skills_canonical": ["sql"],
        "responsibilities": ["Build KPI dashboards for retail banking stakeholders"],
    }

    bundle = retrieve_evidence_bundle(profile, job, top_k=3)

    assert bundle["channel_counts"]["required_skill_support"] >= 1
    assert bundle["channel_counts"]["role_alignment"] >= 1
    assert bundle["channel_counts"]["domain_alignment"] >= 1
    assert bundle["channel_counts"]["responsibility_alignment"] >= 1
    assert bundle["merged_pool_size"] >= 1
    assert bundle["deduped_pool_size"] == 1
    assert len(bundle["selected_evidence"]) == 1
    assert bundle["selected_evidence_ids"] == [bundle["selected_evidence"][0]["evidence_id"]]
    assert set(bundle["selected_evidence"][0]["matched_channels"]) == {
        "required_skill_support",
        "role_alignment",
        "domain_alignment",
        "responsibility_alignment",
    }


def test_retrieve_evidence_bundle_returns_bounded_final_top_k_with_selection_reasons() -> None:
    profile = {
        "preferences": {
            "target_role": "Data Engineer",
            "role_families": ["data_engineering"],
            "domains": ["banking", "analytics"],
        },
        "experiences": [
            {
                "id": "exp_1",
                "role": "Data Engineer",
                "company": "Finbank",
                "role_family": "data_engineering",
                "domain_tags": ["banking"],
                "responsibility_themes": ["etl", "reporting_automation"],
                "bullets": [
                    {"text": "Built SQL ETL pipelines for banking reporting.", "skills": ["SQL", "ETL"]},
                ],
            }
        ],
        "projects": [
            {
                "id": "proj_1",
                "name": "Analytics Platform",
                "skills": ["Python", "dbt"],
                "domain_tags": ["analytics"],
                "responsibility_themes": ["dashboarding"],
                "business_value": "Supported KPI reporting across analytics teams.",
                "highlights": ["Created KPI dashboards for analytics stakeholders."],
            },
            {
                "id": "proj_2",
                "name": "Streaming Fraud Detection",
                "skills": ["Python", "Kafka"],
                "domain_tags": ["banking"],
                "responsibility_themes": ["fraud_detection"],
                "business_value": "Improved fraud detection in banking.",
                "highlights": ["Implemented real-time fraud detection features."],
            },
        ],
        "achievements": [
            {"id": "ach_1", "text": "Improved KPI reporting latency", "domain_tags": ["analytics"]},
        ],
        "skills": [{"name": "SQL"}, {"name": "Python"}],
    }
    job = {
        "job_url": "https://example.com/job-2",
        "title": "Senior Data Engineer",
        "job_family": "data_engineering",
        "domain": "banking",
        "required_skills_canonical": ["sql", "python"],
        "responsibilities": [
            "Build ETL pipelines",
            "Support KPI reporting for banking stakeholders",
        ],
    }

    bundle = retrieve_evidence_bundle(profile, job, top_k=2)

    assert len(bundle["selected_evidence"]) == 2
    assert len(bundle["selected_evidence_ids"]) == 2
    assert len(set(bundle["selected_evidence_ids"])) == 2
    for item in bundle["selected_evidence"]:
        assert item["selection_reasons"]
        assert item["matched_channels"]
        assert item["selection_score"] >= 0.0


def test_retrieve_evidence_bundle_does_not_fill_top_k_without_marginal_gain() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item("ev-sql-a", ["SQL"], "SQL reporting"),
        _cached_evidence_item("ev-sql-b", ["SQL"], "SQL reporting"),
    )

    bundle = retrieve_evidence_bundle(
        profile,
        {"required_skills": ["SQL"]},
        top_k=2,
        config={
            "cv_analysis": {
                "semantic_alignment": {"enabled": False, "channel_pool_size": 2},
                "selection_policy": {
                    "channel_weights": {channel: 1.0 if channel == "required_skill_support" else 0.0 for channel in evidence_module.RETRIEVAL_CHANNELS},
                    "multi_channel_bonus": 0.0,
                    "residual_score_factor": 0.0,
                    "requirement_gain_weight": 0.0,
                },
            }
        },
    )

    assert bundle["selected_evidence_ids"] == ["ev-sql-a"]


def test_retrieve_evidence_bundle_emits_responsibility_scoped_selected_support() -> None:
    profile = _cached_evidence_profile(
        _cached_evidence_item("ev-sql", ["SQL"], "Built SQL pipelines"),
        _cached_evidence_item("ev-dashboard", ["dashboarding"], "Created dashboards"),
    )

    bundle = retrieve_evidence_bundle(
        profile,
        {
            "responsibilities": ["Build SQL pipelines", "Create dashboards"],
            "responsibility_entities": [
                {"source_requirement_id": "req-sql", "text": "Build SQL pipelines"},
                {"source_requirement_id": "req-dashboard", "text": "Create dashboards"},
            ],
        },
        top_k=2,
        config={
            "cv_analysis": {
                "semantic_alignment": {"enabled": False, "channel_pool_size": 2},
            }
        },
    )

    selected = bundle["requirement_support"]["responsibility"]["selected"]
    assert selected["req-sql"] == ["ev-sql"]
    assert selected["req-dashboard"] == ["ev-dashboard"]


def test_retrieve_evidence_bundle_uses_semantic_alignment_for_paraphrased_matches(monkeypatch) -> None:
    profile = {
        "preferences": {
            "target_role": "Data Analyst",
            "role_families": ["analytics"],
            "domains": ["banking"],
        },
        "experiences": [
            {
                "id": "exp_1",
                "role": "Analytics Specialist",
                "company": "Finance Co",
                "bullets": [
                    {
                        "text": "Built executive reporting that guided loan portfolio decisions.",
                        "skills": ["SQL", "Power BI"],
                    }
                ],
            }
        ],
        "projects": [],
        "achievements": [],
        "skills": [{"name": "SQL"}],
    }
    job = {
        "job_url": "https://example.com/job-3",
        "title": "Data Analyst - Retail Banking",
        "job_family": "analytics",
        "domain": "retail banking",
        "required_skills_canonical": ["sql"],
        "responsibilities": [
            "Translate raw data into recommendations for banking stakeholders",
        ],
    }
    config = {
        "cv_analysis": {
            "semantic_alignment": {
                "enabled": True,
                "model": "text-embedding-005",
                "required_skill_lexical_weight": 0.70,
                "required_skill_semantic_weight": 0.30,
                "role_lexical_weight": 0.60,
                "role_semantic_weight": 0.40,
                "responsibility_lexical_weight": 0.25,
                "responsibility_semantic_weight": 0.75,
                "domain_lexical_weight": 0.40,
                "domain_semantic_weight": 0.60,
                "channel_pool_size": 4,
            }
        }
    }

    vector_by_text = {
        "retail banking analytics": [1.0, 0.0, 0.0],
        "data analyst retail banking analytics": [0.9, 0.0, 0.0],
        "translate raw data into recommendations for banking stakeholders": [0.0, 1.0, 0.0],
        "built executive reporting that guided loan portfolio decisions power bi sql analytics specialist finance co": [0.8, 0.9, 0.0],
    }

    def fake_generate_embedding(text: str, runtime_config: dict[str, object], model_name: str | None = None) -> list[float]:
        del runtime_config, model_name
        normalized = " ".join(str(text).lower().split())
        return vector_by_text.get(normalized, [0.0, 0.0, 1.0])

    monkeypatch.setattr(evidence_module, "generate_embedding", fake_generate_embedding)

    bundle = retrieve_evidence_bundle(profile, job, top_k=1, config=config)

    selected = bundle["selected_evidence"][0]
    responsibility_subscores = selected["channel_subscores"]["responsibility_alignment"]
    domain_subscores = selected["channel_subscores"]["domain_alignment"]

    assert selected["semantic_alignment"]["enabled"] is True
    assert selected["semantic_alignment"]["semantic_methods"]["required_skill_support"] == "embedding_similarity"
    assert selected["semantic_alignment"]["semantic_methods"]["role_alignment"] == "embedding_similarity"
    assert selected["semantic_alignment"]["semantic_methods"]["responsibility_alignment"] == "embedding_similarity"
    assert selected["semantic_alignment"]["semantic_methods"]["domain_alignment"] == "embedding_similarity"
    assert responsibility_subscores["semantic"] > 0.7
    assert responsibility_subscores["lexical"] == 0.0
    assert domain_subscores["semantic"] > 0.5
    assert domain_subscores["semantic"] > domain_subscores["lexical"]
    assert bundle["effective_channel_pool_size"] == 4
    assert bundle["selected_evidence_count"] == 1
    assert bundle["semantic_alignment"]["embedding_counts"]["candidate_evidence"]["fresh"] >= 1
    assert bundle["semantic_alignment"]["embedding_counts"]["job_context"]["fresh"] >= 1
    assert isinstance(bundle["unselected_top_candidates"], list)


def test_candidate_embedding_cache_reuses_across_runtime_calls(monkeypatch) -> None:
    evidence_module._CANDIDATE_EMBEDDING_CACHE.clear()
    calls = 0

    def fake_generate_embedding(text: str, runtime_config: dict[str, object], model_name: str | None = None) -> list[float]:
        nonlocal calls
        del text, runtime_config, model_name
        calls += 1
        return [1.0]

    monkeypatch.setattr(evidence_module, "generate_embedding", fake_generate_embedding)
    first_state = evidence_module._semantic_runtime_state()
    second_state = evidence_module._semantic_runtime_state()

    evidence_module._embed_text_cached(
        "Candidate text",
        config={},
        model_name="text-embedding-005",
        runtime_state=first_state,
        cache_namespace="candidate",
    )
    evidence_module._embed_text_cached(
        "Candidate text",
        config={},
        model_name="text-embedding-005",
        runtime_state=second_state,
        cache_namespace="candidate",
    )

    assert calls == 1
    assert first_state["candidate_embedding_fresh_count"] == 1
    assert second_state["candidate_embedding_reused_count"] == 1
    evidence_module._CANDIDATE_EMBEDDING_CACHE.clear()


def test_retrieve_evidence_bundle_uses_semantic_alignment_for_required_skill_support(monkeypatch) -> None:
    """@proves pipeline_performance.cv-analysis-now-uses-bounded-semantic-lift-for-required-skill-and-role-channels-instead-of-reserving-semantic-work-only-for-domain-and-responsibility-alignment"""
    profile = {
        "projects": [
            {
                "name": "Warehouse Schema Redesign",
                "skills": ["Schema Design"],
                "highlights": ["Restructured core warehouse entities for cleaner reporting."],
            }
        ],
        "experiences": [],
        "achievements": [],
        "skills": [],
    }
    job = {
        "job_url": "https://example.com/job-required-skill",
        "title": "",
        "job_family": "",
        "domain": "",
        "required_skills_canonical": ["data modeling"],
        "responsibilities": [],
    }
    config = {
        "cv_analysis": {
            "semantic_alignment": {
                "enabled": True,
                "model": "text-embedding-005",
                "required_skill_lexical_weight": 0.70,
                "required_skill_semantic_weight": 0.30,
                "role_lexical_weight": 0.60,
                "role_semantic_weight": 0.40,
                "responsibility_lexical_weight": 0.25,
                "responsibility_semantic_weight": 0.75,
                "domain_lexical_weight": 0.40,
                "domain_semantic_weight": 0.60,
                "channel_pool_size": 4,
            }
        }
    }

    def fake_generate_embedding(text: str, runtime_config: dict[str, object], model_name: str | None = None) -> list[float]:
        del runtime_config, model_name
        normalized = " ".join(str(text).lower().split())
        if normalized == "data modeling":
            return [1.0, 0.0, 0.0]
        if "schema design" in normalized and "warehouse schema redesign" in normalized:
            return [1.0, 0.0, 0.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setattr(evidence_module, "generate_embedding", fake_generate_embedding)

    bundle = retrieve_evidence_bundle(profile, job, top_k=1, config=config)

    selected = bundle["selected_evidence"][0]
    required_subscores = selected["channel_subscores"]["required_skill_support"]

    assert required_subscores["lexical"] == 0.0
    assert required_subscores["semantic"] > 0.9
    assert required_subscores["combined"] > 0.25
    assert selected["semantic_alignment"]["semantic_methods"]["required_skill_support"] == "embedding_similarity"


def test_retrieve_evidence_bundle_uses_semantic_alignment_for_role_alignment(monkeypatch) -> None:
    """@proves pipeline_performance.cv-analysis-now-uses-bounded-semantic-lift-for-required-skill-and-role-channels-instead-of-reserving-semantic-work-only-for-domain-and-responsibility-alignment"""
    profile = {
        "experiences": [
            {
                "role": "Decision Support Lead",
                "company": "Insight Co",
                "bullets": [{"text": "Guided reporting strategy for executive stakeholders.", "skills": []}],
            }
        ],
        "projects": [],
        "achievements": [],
        "skills": [],
    }
    job = {
        "job_url": "https://example.com/job-role",
        "title": "Business Intelligence Strategist",
        "job_family": "",
        "domain": "",
        "required_skills_canonical": [],
        "responsibilities": [],
    }
    config = {
        "cv_analysis": {
            "semantic_alignment": {
                "enabled": True,
                "model": "text-embedding-005",
                "required_skill_lexical_weight": 0.70,
                "required_skill_semantic_weight": 0.30,
                "role_lexical_weight": 0.60,
                "role_semantic_weight": 0.40,
                "responsibility_lexical_weight": 0.25,
                "responsibility_semantic_weight": 0.75,
                "domain_lexical_weight": 0.40,
                "domain_semantic_weight": 0.60,
                "channel_pool_size": 4,
            }
        }
    }

    def fake_generate_embedding(text: str, runtime_config: dict[str, object], model_name: str | None = None) -> list[float]:
        del runtime_config, model_name
        normalized = " ".join(str(text).lower().split())
        if normalized == "business intelligence strategist":
            return [0.0, 1.0, 0.0]
        if "decision support lead" in normalized and "guided reporting strategy" in normalized:
            return [0.0, 1.0, 0.0]
        return [0.0, 0.0, 1.0]

    monkeypatch.setattr(evidence_module, "generate_embedding", fake_generate_embedding)
    monkeypatch.setattr(evidence_module, "infer_role_family", lambda _text: None)

    bundle = retrieve_evidence_bundle(profile, job, top_k=1, config=config)

    selected = bundle["selected_evidence"][0]
    role_subscores = selected["channel_subscores"]["role_alignment"]

    assert role_subscores["lexical"] == 0.0
    assert role_subscores["semantic"] > 0.9
    assert role_subscores["combined"] > 0.35
    assert selected["semantic_alignment"]["semantic_methods"]["role_alignment"] == "embedding_similarity"


def test_retrieve_evidence_bundle_role_alignment_honors_configured_role_family_neighbors(monkeypatch) -> None:
    profile = {
        "experiences": [
            {
                "id": "exp_neighbor",
                "role": "Platform Engineer",
                "company": "Data Co",
                "role_family": "platform_engineering",
                "bullets": [{"text": "Built platform tooling.", "skills": []}],
            }
        ],
        "projects": [],
        "achievements": [],
        "skills": [],
    }
    job = {
        "job_url": "https://example.com/job-role-neighbor",
        "title": "Data Engineer",
        "job_family": "data_engineering",
        "domain": "",
        "required_skills_canonical": [],
        "responsibilities": [],
    }
    config = {
        "cv_analysis": {"semantic_alignment": {"enabled": False}},
        "role_taxonomy": {
            "role_family_neighbors": {
                "data_engineering": ["platform_engineering"],
            }
        },
    }

    monkeypatch.setattr(evidence_module, "infer_role_family", lambda _text: None)

    bundle = retrieve_evidence_bundle(profile, job, top_k=1, config=config)

    selected = bundle["selected_evidence"][0]
    role_subscores = selected["channel_subscores"]["role_alignment"]

    assert role_subscores["semantic"] == 0.0
    assert role_subscores["lexical"] == evidence_module.ROLE_ALIGNMENT_NEIGHBOR_SCORE
    assert role_subscores["combined"] == evidence_module.ROLE_ALIGNMENT_NEIGHBOR_SCORE


def test_runtime_overlay_role_family_neighbors_drive_ranking_and_evidence(monkeypatch) -> None:
    base_config = {
        "cv_analysis": {"semantic_alignment": {"enabled": False}},
        "role_taxonomy": {
            "canonical_role_by_alias": {
                "data engineer": "data engineer",
                "platform engineer": "platform engineer",
            },
            "role_family_by_role": {
                "data engineer": "data_engineering",
                "platform engineer": "platform_engineering",
            },
            "role_family_neighbors": {},
        },
        "role_family_neighbors": {},
        "skill_synonyms_runtime": {},
    }
    config = apply_runtime_synonym_overlay(
        base_config,
        {"role_family_neighbors": {"data_engineering": ("platform_engineering",)}},
        source="upload",
        filename="role-neighbors.yaml",
        uploaded_at="2026-06-25T15:15:00Z",
    )
    profile = {
        "experiences": [
            {
                "id": "exp_neighbor",
                "role": "Platform Engineer",
                "company": "Data Co",
                "role_family": "platform_engineering",
                "bullets": [{"text": "Built platform tooling.", "skills": []}],
            }
        ],
        "projects": [],
        "achievements": [],
        "skills": [],
    }
    job = {
        "job_url": "https://example.com/job-overlay-neighbor",
        "title": "Data Engineer",
        "job_family": "data_engineering",
        "domain": "",
        "required_skills_canonical": [],
        "responsibilities": [],
    }

    monkeypatch.setattr(evidence_module, "infer_role_family", lambda _text: None)

    assert compute_title_relevance("Platform Engineer", "Data Engineer", config=config) == 0.75

    bundle = retrieve_evidence_bundle(profile, job, top_k=1, config=config)
    selected = bundle["selected_evidence"][0]
    role_subscores = selected["channel_subscores"]["role_alignment"]

    assert role_subscores["semantic"] == 0.0
    assert role_subscores["lexical"] == evidence_module.ROLE_ALIGNMENT_NEIGHBOR_SCORE
    assert role_subscores["combined"] == evidence_module.ROLE_ALIGNMENT_NEIGHBOR_SCORE
def test_retrieve_evidence_bundle_uses_global_relevance_without_section_reservations() -> None:
    profile = {
        "preferences": {
            "target_role": "Data Engineer",
            "role_families": ["data_engineering"],
            "domains": ["banking"],
        },
        "experiences": [
            {
                "id": "exp_1",
                "role": "Data Engineer",
                "company": "Bank One",
                "role_family": "data_engineering",
                "domain_tags": ["banking"],
                "responsibility_themes": ["etl", "stakeholder_reporting"],
                "bullets": [
                    {"text": "Built SQL ETL pipelines for banking reporting.", "skills": ["SQL", "ETL"]},
                ],
            },
            {
                "id": "exp_2",
                "role": "Data Engineer",
                "company": "Bank Two",
                "role_family": "data_engineering",
                "domain_tags": ["banking"],
                "responsibility_themes": ["etl"],
                "bullets": [
                    {"text": "Maintained SQL ETL pipelines.", "skills": ["SQL", "ETL"]},
                ],
            },
        ],
        "projects": [
            {
                "id": "proj_1",
                "name": "Stakeholder Reporting Platform",
                "skills": ["Python"],
                "domain_tags": ["banking"],
                "responsibility_themes": ["stakeholder_reporting"],
                "business_value": "Supported executive reporting for retail banking leaders.",
                "highlights": ["Delivered reporting used by banking stakeholders."],
            }
        ],
        "achievements": [],
        "skills": [{"name": "SQL"}, {"name": "Python"}],
    }
    job = {
        "job_url": "https://example.com/job-4",
        "title": "Senior Data Engineer",
        "job_family": "data_engineering",
        "domain": "banking",
        "required_skills_canonical": ["sql"],
        "responsibilities": [
            "Build ETL pipelines",
            "Support stakeholder reporting for banking teams",
        ],
    }

    bundle = retrieve_evidence_bundle(profile, job, top_k=2)
    selected = bundle["selected_evidence"]

    assert selected[0]["parent_id"] == "exp_1"
    assert len(selected) == 1
    assert all(item["schema_version"] == "candidate-evidence.v1" for item in selected)
    assert bundle["selected_evidence_count"] == 1
    assert len(bundle["unselected_top_candidates"]) >= 1
    assert bundle["unselected_top_candidates"][0]["source_ref"].startswith("experiences/exp_2/")


def test_retrieve_evidence_bundle_contract_is_deterministic_across_repeated_runs() -> None:
    profile = {
        "preferences": {
            "target_role": "Data Engineer",
            "role_families": ["data_engineering"],
            "domains": ["finance", "analytics"],
        },
        "experiences": [
            {
                "id": "exp_a",
                "role": "Senior Data Engineer",
                "company": "Bank Alpha",
                "role_family": "data_engineering",
                "domain_tags": ["finance"],
                "responsibility_themes": ["etl", "reporting"],
                "bullets": [
                    {"text": "Built SQL ETL pipelines for finance reporting.", "skills": ["SQL", "ETL"]},
                    {"text": "Maintained stakeholder KPI dashboards.", "skills": ["Reporting"]},
                ],
            },
            {
                "id": "exp_b",
                "role": "Analytics Engineer",
                "company": "Bank Beta",
                "role_family": "data_engineering",
                "domain_tags": ["analytics"],
                "responsibility_themes": ["modeling"],
                "bullets": [
                    {"text": "Modeled warehouse marts for BI teams.", "skills": ["dbt", "SQL"]},
                ],
            },
        ],
        "projects": [
            {
                "id": "proj_a",
                "name": "Finance Insights Platform",
                "skills": ["Python", "SQL"],
                "domain_tags": ["finance"],
                "responsibility_themes": ["reporting"],
                "business_value": "Accelerated finance insight delivery.",
                "highlights": [
                    "Unified KPI model for finance stakeholders.",
                    "Reduced reporting latency.",
                ],
            }
        ],
        "achievements": [{"id": "ach_a", "text": "Improved ETL reliability"}],
        "skills": [{"name": "SQL"}, {"name": "Python"}],
    }
    job = {
        "job_url": "https://example.com/job-deterministic",
        "title": "Senior Data Engineer",
        "job_family": "data_engineering",
        "domain": "finance",
        "required_skills_canonical": ["sql", "python"],
        "responsibilities": [
            "Build ETL pipelines",
            "Enable finance stakeholder reporting",
        ],
    }

    first = retrieve_evidence_bundle(profile, job, top_k=2)
    second = retrieve_evidence_bundle(profile, job, top_k=2)

    assert _stable_contract_view(first) == _stable_contract_view(second)
    assert first["selected_evidence_ids"] == [
        item["evidence_id"] for item in first["selected_evidence"]
    ]
    assert all(evidence_id.startswith("ev_") for evidence_id in first["selected_evidence_ids"])

    selected = first["selected_evidence"]
    assert len(selected) == 2
    for item in selected:
        assert item["selection_reasons"]
        assert item["matched_channels"]
        semantic_alignment = item["semantic_alignment"]
        assert semantic_alignment["enabled"] is False
        assert semantic_alignment["semantic_methods"]["required_skill_support"] == "disabled"
        assert semantic_alignment["semantic_methods"]["role_alignment"] == "disabled"
        assert semantic_alignment["semantic_methods"]["responsibility_alignment"] == "disabled"
        assert semantic_alignment["semantic_methods"]["domain_alignment"] == "disabled"
        assert semantic_alignment["reuse_state"]["candidate_evidence"] == "not_requested"
        assert semantic_alignment["reuse_state"]["job_context"] == "not_requested"
        for components in dict(item.get("channel_subscores") or {}).values():
            assert components["semantic"] == 0.0
            assert components["combined"] == components["lexical"]

    assert first["hybrid_alignment"]["required_skill_support"] == {
        "lexical_weight": 1.0,
        "semantic_weight": 0.0,
    }
    assert first["hybrid_alignment"]["role_alignment"] == {
        "lexical_weight": 1.0,
        "semantic_weight": 0.0,
    }
    assert first["hybrid_alignment"]["responsibility"] == {
        "lexical_weight": 1.0,
        "semantic_weight": 0.0,
    }
    assert first["hybrid_alignment"]["domain"] == {
        "lexical_weight": 1.0,
        "semantic_weight": 0.0,
    }


def test_retrieve_evidence_bundle_preserves_selection_and_debug_schema_contract() -> None:
    profile = {
        "preferences": {
            "target_role": "Data Engineer",
            "role_families": ["data_engineering"],
            "domains": ["banking"],
        },
        "experiences": [
            {
                "id": "exp_1",
                "role": "Data Engineer",
                "company": "Bank One",
                "role_family": "data_engineering",
                "domain_tags": ["banking"],
                "responsibility_themes": ["etl", "reporting"],
                "bullets": [{"text": "Built SQL ETL pipelines.", "skills": ["SQL", "ETL"]}],
            }
        ],
        "projects": [
            {
                "id": "proj_1",
                "name": "Risk Dashboard Platform",
                "skills": ["Python", "SQL"],
                "domain_tags": ["banking"],
                "responsibility_themes": ["reporting"],
                "business_value": "Improved risk visibility.",
                "highlights": ["Shipped banking KPI dashboards."],
            },
            {
                "id": "proj_2",
                "name": "Compliance Reporting Automation",
                "skills": ["SQL"],
                "domain_tags": ["banking"],
                "responsibility_themes": ["reporting"],
                "business_value": "Reduced compliance report effort.",
                "highlights": ["Automated reporting pipeline."],
            },
        ],
        "achievements": [],
        "skills": [{"name": "SQL"}, {"name": "Python"}],
    }
    job = {
        "job_url": "https://example.com/job-schema-contract",
        "title": "Senior Data Engineer",
        "job_family": "data_engineering",
        "domain": "banking",
        "required_skills_canonical": ["sql", "python"],
        "responsibilities": [
            "Build ETL pipelines",
            "Support banking reporting",
        ],
    }

    bundle = retrieve_evidence_bundle(profile, job, top_k=2)

    assert bundle["selected_evidence_count"] == 2
    assert bundle["selected_evidence_ids"] == [item["evidence_id"] for item in bundle["selected_evidence"]]
    assert isinstance(bundle["unselected_top_candidates"], list)
    assert bundle["unselected_top_candidates"]

    for selected in bundle["selected_evidence"]:
        assert isinstance(selected["selection_score"], float)
        assert selected["selection_score"] >= 0.0
        assert isinstance(selected["selection_reasons"], list)
        assert selected["selection_reasons"]
        channel_subscores = selected["channel_subscores"]
        assert isinstance(channel_subscores, dict)
        for components in channel_subscores.values():
            assert set(components) == {"lexical", "semantic", "combined"}
            assert isinstance(components["combined"], float)

    sample = bundle["unselected_top_candidates"][0]
    assert set(sample).issuperset(
        {
            "evidence_id",
            "evidence_type",
            "source_ref",
            "name",
            "matched_channels",
            "selection_score",
        }
    )
    if "selection_reasons" in sample:
        assert isinstance(sample["selection_reasons"], list)
    assert isinstance(sample["selection_score"], float)

    traces = bundle["stage_traces"]
    assert traces["schema_version"] == "fitcv.evidence_stage_trace.v1"
    assert set(traces) == {"schema_version", "counts"}
    assert traces["counts"]["selection"] >= traces["counts"]["assignment"]

    diagnostic_bundle = evidence_module.retrieve_evidence_bundle(
        profile,
        job,
        top_k=2,
        config={"cv_analysis": {"diagnostics": {"full_stage_traces": True}}},
    )
    diagnostic_traces = diagnostic_bundle["stage_traces"]
    assert set(diagnostic_traces) == {
        "schema_version",
        "canonical_pool",
        "candidate_retrieval",
        "verification",
        "qualification",
        "selection",
        "assignment",
        "counts",
    }
    assert diagnostic_traces["counts"]["selection"] == len(diagnostic_traces["selection"])
    telemetry = diagnostic_bundle["runtime_telemetry"]
    assert telemetry["schema_version"] == "fitcv.evidence_runtime_telemetry.v1"
    assert telemetry["retrieval_latency_ms"] >= 0
    assert telemetry["counts"]["canonical"] >= telemetry["counts"]["candidate"]
    assert telemetry["counts"]["selected"] == bundle["selected_evidence_count"]
    assert "embedding_counts" in telemetry


def test_selection_policy_model_matches_public_policy_dict_defaults() -> None:
    model = evidence_module._selection_policy_model(None)
    policy = evidence_module._cv_analysis_policy_settings(None)

    assert model.as_dict() == policy
    assert policy["quotas"]["experience_entry_top_k"] == 2
    assert policy["trimming"]["bullets_per_experience"] == 2


def test_semantic_alignment_model_matches_public_settings_dict_partial_config() -> None:
    config = {
        "cv_analysis": {
            "semantic_alignment": {
                "enabled": True,
                "channel_pool_size": 6,
                "required_skill_semantic_weight": 0.45,
            }
        }
    }

    model = evidence_module._semantic_alignment_settings_model(config)
    settings = evidence_module._semantic_alignment_settings(config)

    assert model.as_dict() == settings
    assert settings["enabled"] is True
    assert settings["channel_pool_size"] == 6
    assert settings["required_skill_semantic_weight"] == 0.45
    assert settings["required_skill_lexical_weight"] == 0.70


# ── store_evidence_selection ───────────────────────────────────────────────────


def test_store_evidence_selection_writes_sqlite_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import json
    import sqlite3

    from fitcv.evidence import store_evidence_selection

    db_path = tmp_path / "fitcv_cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))

    selected = [
        {
            "evidence_id": "proj_1",
            "evidence_type": "project_entry",
            "name": "FitCV",
            "skills": ["Python", "BigQuery"],
            "business_value": "Reduced tailoring time",
            "selection_score": 0.91,
            "source_ref": "projects[0]",
        },
        {
            "evidence_id": "exp_1",
            "evidence_type": "experience_entry",
            "name": "Data Engineer @ Acme",
            "skills": ["SQL"],
            "business_value": "",
            "score": 0.67,
            "source_ref": "experiences[0]",
        },
    ]

    store_evidence_selection("https://example.com/job-1", selected, config={})

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT job_url, evidence_id, evidence_type, name, skills_json,
                   business_value, score, source_ref
            FROM evidence_selections
            ORDER BY evidence_id
            """
        ).fetchall()

    assert len(rows) == 2
    assert rows[0][0] == "https://example.com/job-1"
    assert rows[0][1] == "exp_1"
    assert json.loads(str(rows[0][4])) == ["SQL"]
    assert float(rows[0][6]) == 0.67
    assert rows[1][1] == "proj_1"
    assert json.loads(str(rows[1][4])) == ["Python", "BigQuery"]
    assert float(rows[1][6]) == 0.91



def test_store_evidence_selection_sqlite_upsert_is_idempotent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import sqlite3

    from fitcv.evidence import store_evidence_selection

    db_path = tmp_path / "fitcv_cp.sqlite3"
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(db_path))

    first = [
        {
            "evidence_id": "proj_1",
            "evidence_type": "project_entry",
            "name": "FitCV",
            "skills": ["Python"],
            "business_value": "v1",
            "selection_score": 0.40,
            "source_ref": "projects[0]",
        }
    ]
    second = [
        {
            "evidence_id": "proj_1",
            "evidence_type": "project_entry",
            "name": "FitCV Updated",
            "skills": ["Python", "BigQuery"],
            "business_value": "v2",
            "selection_score": 0.88,
            "source_ref": "projects[1]",
        }
    ]

    job_url = "https://example.com/job-upsert"
    store_evidence_selection(job_url, first, config={})
    store_evidence_selection(job_url, second, config={})

    with sqlite3.connect(db_path) as conn:
        count = conn.execute(
            "SELECT COUNT(*) FROM evidence_selections WHERE job_url = ? AND evidence_id = ?",
            (job_url, "proj_1"),
        ).fetchone()
        row = conn.execute(
            """
            SELECT name, skills_json, business_value, score, source_ref
            FROM evidence_selections
            WHERE job_url = ? AND evidence_id = ?
            """,
            (job_url, "proj_1"),
        ).fetchone()

    assert count is not None and int(count[0]) == 1
    assert row is not None
    assert row[0] == "FitCV Updated"
    assert '"BigQuery"' in str(row[1])
    assert row[2] == "v2"
    assert float(row[3]) == 0.88
    assert row[4] == "projects[1]"

def test_normalize_evidence_selection_records_contract() -> None:
    records = evidence_module._normalize_evidence_selection_records(
        "https://example.com/job-3",
        [
            {
                "evidence_id": "exp_7",
                "evidence_type": "experience_entry",
                "name": "Data Engineer @ Example",
                "skills": ["SQL"],
                "business_value": "",
                "score": 0.73,
                "source_ref": "experiences[0]",
            }
        ],
        selected_at="2026-05-18T12:00:00+00:00",
    )

    assert len(records) == 1
    record = records[0]
    assert record.job_url == "https://example.com/job-3"
    assert record.evidence_id == "exp_7"
    assert record.skills == ["SQL"]
    assert record.score == 0.73

    sqlite_params = evidence_module._record_to_sqlite_params(record)
    assert sqlite_params[0] == "https://example.com/job-3"
    assert sqlite_params[1] == "exp_7"
    assert sqlite_params[6] == 0.73





def test_cv_analysis_contract_ignores_synonym_data_changes() -> None:
    baseline = evidence_module.build_cv_analysis_contract_fingerprint(
        {"skill_synonyms": {"gcp": "google cloud platform"}}
    )
    changed = evidence_module.build_cv_analysis_contract_fingerprint(
        {"skill_synonyms": {"gcp": "google cloud", "unrelated": "value"}}
    )

    assert baseline == changed


def test_cv_analysis_contract_rejects_v2_requirement_support_policy_fingerprint() -> None:
    current = evidence_module.build_cv_analysis_contract_fingerprint({})
    legacy_payload = copy.deepcopy(current["payload"])
    legacy_payload["requirement_support_policy_version"] = "requirement-support-v2"
    legacy_fingerprint = evidence_module._stable_json_fingerprint(legacy_payload)

    assert current["payload"]["requirement_support_policy_version"] == "requirement-support-v6"
    assert current["fingerprint"] != legacy_fingerprint


def test_projected_evidence_declares_one_source_support_fragment_field() -> None:
    tree = ast.parse(Path("src/fitcv/evidence.py").read_text(encoding="utf-8"))
    function = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name == "project_candidate_evidence"
    )
    support_fragment_keys = [
        key.value
        for node in ast.walk(function)
        if isinstance(node, ast.Dict)
        for key in node.keys
        if isinstance(key, ast.Constant) and key.value == "support_fragments"
    ]

    assert support_fragment_keys == ["support_fragments"]


def test_cv_analysis_input_fingerprint_tracks_bounded_alias_equivalence() -> None:
    profile = {"skills": ["GCP"]}
    job = {
        "raw_job_fingerprint": "raw-1",
        "job_url": "https://example.com/job",
        "title": "Cloud Analyst",
        "required_skills": ["GCP"],
        "preferred_skills": [],
        "responsibilities": ["Operate cloud data pipelines"],
    }
    baseline_config = {"skill_synonyms": {"gcp": "google cloud"}}
    unrelated_config = {
        "skill_synonyms": {"gcp": "google cloud", "unused alias": "unused canonical"}
    }
    target_changed_config = {"skill_synonyms": {"gcp": "google cloud changed"}}
    alias_added_config = {
        "skill_synonyms": {"gcp": "google cloud", "gcp snapshot alias": "google cloud"}
    }

    baseline = evidence_module.build_cv_analysis_input_fingerprint(
        profile, job, baseline_config
    )
    unrelated = evidence_module.build_cv_analysis_input_fingerprint(
        profile, job, unrelated_config
    )
    target_changed = evidence_module.build_cv_analysis_input_fingerprint(
        profile, job, target_changed_config
    )
    alias_added = evidence_module.build_cv_analysis_input_fingerprint(
        profile, job, alias_added_config
    )

    assert baseline["fingerprint"] == unrelated["fingerprint"]
    assert baseline["fingerprint"] != target_changed["fingerprint"]
    assert baseline["fingerprint"] != alias_added["fingerprint"]


def test_ranking_selector_gives_different_jobs_relevant_evidence() -> None:
    pool = [
        {"evidence_id": "sql", "text": "Built SQL warehouse", "skills": ["SQL"], "scoring_context": "SQL warehouse"},
        {"evidence_id": "python", "text": "Built Python service", "skills": ["Python"], "scoring_context": "Python service"},
    ]
    sql = select_ranking_evidence(pool, {"required_skills": ["SQL"]})
    python = select_ranking_evidence(pool, {"required_skills": ["Python"]})
    assert sql[0]["evidence_id"] == "sql"
    assert python[0]["evidence_id"] == "python"
    assert sql[0]["text"] == "Built SQL warehouse"


def test_ranking_selector_is_stable_and_empty_safe() -> None:
    pool = [
        {"evidence_id": "b", "text": "same", "skills": ["SQL"], "scoring_context": "same"},
        {"evidence_id": "a", "text": "same", "skills": ["SQL"], "scoring_context": "same"},
    ]
    first = select_ranking_evidence(pool, {"required_skills": ["SQL"]})
    second = select_ranking_evidence(pool, {"required_skills": ["SQL"]})
    assert [item["evidence_id"] for item in first] == ["a", "b"]
    assert first == second
    assert select_ranking_evidence([], {"required_skills": ["SQL"]}) == []


def test_ranking_selector_uses_job_context_when_skills_are_missing() -> None:
    pool = [
        {
            "evidence_id": "irrelevant",
            "text": "Led payroll migration",
            "skills": [],
            "scoring_context": "Led payroll migration",
            "role": "Finance Manager",
        },
        {
            "evidence_id": "relevant",
            "text": "Built ETL pipelines",
            "skills": [],
            "scoring_context": "Built ETL pipelines",
            "role": "Data Engineer",
        },
    ]
    job = {
        "title": "Senior Data Engineer",
        "job_family": "data_engineering",
        "domain": "banking",
        "responsibilities": ["Build ETL pipelines", "Support banking reporting"],
    }

    selected = select_ranking_evidence(pool, job, limit=1)

    assert selected[0]["evidence_id"] == "relevant"


def test_profile_evidence_pool_projects_once_per_revision(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = 0
    original = evidence_module.project_candidate_evidence

    def projected(profile: dict) -> list[dict]:
        nonlocal calls
        calls += 1
        return original(profile)

    monkeypatch.setattr(evidence_module, "project_candidate_evidence", projected)
    profile = _v2_profile()
    pool = build_profile_evidence_pool(profile)
    select_ranking_evidence(pool, {"required_skills": ["SQL"]})
    select_ranking_evidence(pool, {"required_skills": ["Python"]})
    assert calls == 1
