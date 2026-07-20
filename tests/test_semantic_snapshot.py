"""
@meta
type: test
scope: unit
domain: semantic_snapshot
covers:
  - compile_semantic_policy: deterministic taxonomy-specific policy compilation
  - build_semantic_snapshot: subject-aware values, identity, and per-field completeness
  - project_alias_equivalence: bounded alias-sensitive projection
excludes:
  - stage orchestration
  - external services
tags:
  - fast
  - ci-safe
"""

import pytest

from fitcv.semantic_snapshot import (
    build_semantic_snapshot,
    compile_semantic_policy,
    project_alias_equivalence,
    project_canonical,
    semantic_requirements_complete,
)
from fitcv.shortlist_runtime import build_contract_fingerprint


def _config(**overrides: object) -> dict[str, object]:
    config: dict[str, object] = {
        "skill_synonyms": {"gcp": "google cloud", "C++": "C++", "C#": "C#"},
        "domain_alias_map": {"Fin-Tech": "financial services"},
        "role_family_alias_map": {"BI Analyst": "analytics"},
    }
    config.update(overrides)
    return config


def test_compile_semantic_policy_is_order_invariant_and_preserves_skill_punctuation() -> None:
    first = compile_semantic_policy(_config())
    second = compile_semantic_policy(
        {
            "role_family_alias_map": {"BI Analyst": "analytics"},
            "domain_alias_map": {"Fin-Tech": "financial services"},
            "skill_synonyms": {"C#": "C#", "C++": "C++", "gcp": "google cloud"},
        }
    )

    assert first == second
    assert first["maps"]["skill"]["c++"] == "c++"
    assert first["maps"]["skill"]["c#"] == "c#"
    assert first["maps"]["domain"]["fin tech"] == "financial services"


def test_compile_semantic_policy_flattens_chains_and_rejects_cycles_and_collisions() -> None:
    policy = compile_semantic_policy(_config(skill_synonyms={"a": "b", "b": "c"}))
    snapshot = build_semantic_snapshot(
        "criteria",
        "criteria-1",
        {"must_have_skills": ["a"]},
        policy,
    )

    assert policy["schema_version"] == "semantic_policy_v2"
    assert policy["resolver_contract_version"] == "semantic_resolver_v2"
    assert policy["maps"]["skill"] == {"a": "c", "b": "c"}
    assert project_canonical(snapshot, "must_have_skills") == ["c"]
    with pytest.raises(ValueError, match="cycle"):
        compile_semantic_policy(_config(skill_synonyms={"a": "b", "b": "a"}))
    with pytest.raises(ValueError, match="collision"):
        compile_semantic_policy(
            _config(domain_alias_map={"Fin-Tech": "financial services", "fin tech": "banking"})
        )

def test_captured_v1_policy_preserves_one_hop_resolution_and_resolver_identity() -> None:
    payload = {
        "schema_version": "semantic_policy_v1",
        "resolver_contract_version": "semantic_resolver_v1",
        "maps": {"skill": {"a": "b", "b": "c"}, "domain": {}, "role_family": {}},
    }
    captured_v1 = {**payload, "policy_fingerprint": build_contract_fingerprint(payload)}
    compiled_v2 = compile_semantic_policy(_config(skill_synonyms={"a": "b", "b": "c"}))

    v1_snapshot = build_semantic_snapshot(
        "criteria",
        "criteria-1",
        {"must_have_skills": ["a"]},
        captured_v1,
    )
    v2_snapshot = build_semantic_snapshot(
        "criteria",
        "criteria-1",
        {"must_have_skills": ["a"]},
        compiled_v2,
    )

    assert project_canonical(v1_snapshot, "must_have_skills") == ["b"]
    assert project_canonical(v2_snapshot, "must_have_skills") == ["c"]
    assert v1_snapshot["resolver_contract_fingerprint"] == build_contract_fingerprint(
        {
            "version": "semantic_resolver_v1",
            "field_contracts": {"must_have_skills": ("skill", "list")},
        }
    )
    assert (
        v1_snapshot["resolver_contract_fingerprint"]
        != v2_snapshot["resolver_contract_fingerprint"]
    )

def test_semantic_snapshot_rejects_unsupported_policy_contracts() -> None:
    policy = compile_semantic_policy(_config())
    policy["schema_version"] = "semantic_policy_v3"

    with pytest.raises(ValueError, match="unsupported semantic policy contract"):
        build_semantic_snapshot(
            "criteria",
            "criteria-1",
            {"must_have_skills": ["a"]},
            policy,
        )


def test_semantic_derivation_fingerprint_changes_with_raw_source() -> None:
    policy = compile_semantic_policy(_config())
    first = build_semantic_snapshot(
        "job",
        "job-1",
        {"required_skills": ["GCP"], "preferred_skills": [], "domain": "Fin-Tech", "job_family": "BI Analyst"},
        policy,
    )
    second = build_semantic_snapshot(
        "job",
        "job-1",
        {"required_skills": ["C++"], "preferred_skills": [], "domain": "Fin-Tech", "job_family": "BI Analyst"},
        policy,
    )

    assert first["semantic_derivation_fingerprint"] != second["semantic_derivation_fingerprint"]


def test_semantic_value_fingerprint_excludes_subject_identity() -> None:
    policy = compile_semantic_policy(_config())
    fields = {"candidate_skills": ["GCP", "C++"]}

    first = build_semantic_snapshot("candidate", "candidate-1", fields, policy)
    second = build_semantic_snapshot("candidate", "candidate-2", fields, policy)

    assert first["subject_identity"] != second["subject_identity"]
    assert first["semantic_value_fingerprint"] == second["semantic_value_fingerprint"]


def test_per_field_completeness_allows_unrelated_projection_reuse() -> None:
    policy = compile_semantic_policy(_config())
    snapshot = build_semantic_snapshot(
        "job",
        "job-1",
        {"required_skills": ["GCP"], "preferred_skills": [], "job_family": "BI Analyst"},
        policy,
    )

    assert semantic_requirements_complete(snapshot, ["required_skills"])
    assert not semantic_requirements_complete(snapshot, ["domain"])
    assert project_canonical(snapshot, "required_skills") == ["google cloud"]


def test_alias_equivalence_projection_is_bounded_to_consumed_values() -> None:
    policy = compile_semantic_policy(
        _config(skill_synonyms={"gcp": "google cloud", "google cloud platform": "google cloud", "k8s": "kubernetes"})
    )
    snapshot = build_semantic_snapshot(
        "candidate",
        "candidate-1",
        {"candidate_skills": ["GCP"]},
        policy,
    )

    assert project_alias_equivalence(snapshot, "candidate_skills", policy) == {
        "google cloud": ["gcp", "google cloud", "google cloud platform"]
    }


def test_mapping_edits_change_only_consumed_semantic_projection() -> None:
    baseline_policy = compile_semantic_policy(_config(skill_synonyms={"a": "b"}))
    unrelated_policy = compile_semantic_policy(_config(skill_synonyms={"a": "b", "c": "d"}))
    related_policy = compile_semantic_policy(_config(skill_synonyms={"a": "b", "b": "c"}))
    target_changed_policy = compile_semantic_policy(_config(skill_synonyms={"a": "b2"}))
    alias_added_policy = compile_semantic_policy(_config(skill_synonyms={"a": "b", "a2": "b"}))

    def snapshot(policy: dict[str, object]) -> dict[str, object]:
        return build_semantic_snapshot(
            "candidate",
            "candidate-1",
            {"candidate_skills": ["a"]},
            policy,
        )

    baseline = snapshot(baseline_policy)
    unrelated = snapshot(unrelated_policy)
    related = snapshot(related_policy)
    target_changed = snapshot(target_changed_policy)
    alias_added = snapshot(alias_added_policy)

    assert baseline["semantic_value_fingerprint"] == unrelated["semantic_value_fingerprint"]
    assert project_canonical(baseline, "candidate_skills") == project_canonical(
        unrelated, "candidate_skills"
    )
    assert project_alias_equivalence(
        baseline, "candidate_skills", baseline_policy
    ) == project_alias_equivalence(unrelated, "candidate_skills", unrelated_policy)

    assert project_canonical(related, "candidate_skills") == ["c"]
    assert baseline["semantic_value_fingerprint"] != related["semantic_value_fingerprint"]

    assert baseline["semantic_value_fingerprint"] != target_changed["semantic_value_fingerprint"]
    assert project_canonical(baseline, "candidate_skills") != project_canonical(
        target_changed, "candidate_skills"
    )

    assert baseline["semantic_value_fingerprint"] == alias_added["semantic_value_fingerprint"]
    assert project_canonical(baseline, "candidate_skills") == project_canonical(
        alias_added, "candidate_skills"
    )
    assert project_alias_equivalence(
        baseline, "candidate_skills", baseline_policy
    ) != project_alias_equivalence(alias_added, "candidate_skills", alias_added_policy)

@pytest.mark.parametrize(
    ("field", "expected"),
    [
        ("domain", {"financial services": ["fin tech", "financial services"]}),
        ("job_family", {"analytics": ["analytics", "bi analyst"]}),
    ],
)
def test_alias_equivalence_projection_uses_field_taxonomy(
    field: str,
    expected: dict[str, list[str]],
) -> None:
    policy = compile_semantic_policy(_config())
    snapshot = build_semantic_snapshot(
        "job",
        "job-1",
        {
            "required_skills": [],
            "preferred_skills": [],
            "domain": "Fin-Tech",
            "job_family": "BI Analyst",
        },
        policy,
    )

    assert project_alias_equivalence(snapshot, field, policy) == expected

def test_runtime_semantic_consumers_do_not_read_raw_maps_or_duplicate_variants() -> None:
    from pathlib import Path

    root = Path(__file__).parents[1] / "src" / "fitcv"
    forbidden = {
        "enrich.py": (
            'cfg.get("skill_synonyms")',
            'cfg.get("domain_alias_map")',
            'cfg.get("role_family_alias_map")',
        ),
        "rule_filter.py": ('config.get("skill_synonyms")',),
        "gap_analysis.py": ("get_skill_synonyms", "def _skill_variants"),
        "ranking.py": ("def _canonicalize_with_alias_map",),
    }
    violations = [
        f"{name}: {token}"
        for name, tokens in forbidden.items()
        for token in tokens
        if token in (root / name).read_text(encoding="utf-8")
    ]

    assert violations == []
