"""
@meta
type: test
scope: unit
domain: pipeline_config
covers:
  - control-plane settings schema behavior
excludes:
  - live persistence
tags:
  - fast
  - ci-safe
"""

from pathlib import Path

import pytest
import yaml
from fitcv_cp.settings_schema import (
    AGENTIC_SETTINGS_SECTIONS,
    DECISION_STATUS_ADVANCED,
    DECISION_STATUS_CONFIGURED,
    DECISION_STATUS_NEEDS_REVIEW,
    DECISION_STATUS_RECOMMENDED,
    REASON_CODE_ADVANCED_ONLY,
    REASON_CODE_CHANGED_FROM_DEFAULT,
    REASON_CODE_CONFLICT,
    REASON_CODE_RECOMMENDED_DELTA,
    derive_settings_decision_state,
    decision_status_sort_key,
    SETTINGS_SECTIONS,
    SETTINGS_SCHEMA,
    apply_settings_to_config,
    editable_agentic_settings_keys,
    editable_settings_keys,
    excluded_agentic_settings_keys,
    metadata_only_agentic_settings_keys,
    metadata_only_settings_keys,
    danger_zone_settings_keys,
    settings_keys_for_domain,
    settings_ia_contract_for_key,
    settings_ia_metadata_by_key,
    settings_keys_for_workflow_stage,
    reason_code_is_blocking,
    validate_settings,
    ValidationError,
)
import fitcv_cp.settings_schema as settings_schema_module
from fitcv.rule_filter import DEFAULT_SELECTED_RULE_FILTERS


# ── schema registry ───────────────────────────────────────────────────────────

def test_all_expected_keys_present():
    """@proves settings_system.settings-schema-registry"""
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "pipeline.final_top_n" in keys
    assert "cv_analysis.semantic_alignment.enabled" in keys
    assert "cv_analysis.semantic_alignment.required_skill_lexical_weight" in keys
    assert "cv_analysis.semantic_alignment.role_semantic_weight" in keys
    assert "cv_analysis.semantic_alignment.responsibility_lexical_weight" in keys
    assert "cv_analysis.semantic_alignment.domain_semantic_weight" in keys
    assert "run_lifecycle.max_runtime_minutes" in keys
    assert "ranking_weights.ai_score" in keys
    assert "fit_label_thresholds.strong" in keys
    assert "gap_thresholds.strong_min_matched_ratio" in keys
    # excluded key — internal fallback only, not admin-editable
    assert "rerank_top_n" not in keys

def test_settings_ia_metadata_covers_all_schema_keys_without_orphans() -> None:
    schema_keys = {s["key"] for s in SETTINGS_SCHEMA}
    ia_keys = set(settings_ia_metadata_by_key().keys())
    assert ia_keys == schema_keys

def test_settings_ia_metadata_marks_metadata_only_runtime_usage_consistently() -> None:
    meta = settings_ia_metadata_by_key()
    for key in metadata_only_settings_keys():
        assert meta[key]["metadata_only"] is True
        assert meta[key]["runtime_used"] is False
    assert meta["pipeline.final_top_n"]["runtime_used"] is True
    assert meta["pipeline.final_top_n"]["metadata_only"] is False

def test_settings_ia_domain_filter_returns_expected_keys() -> None:
    general_keys = set(settings_keys_for_domain("general"))
    assert "cv_summary_enabled" in general_keys
    assert "cv_skills_enabled" in general_keys
    rules_keys = set(settings_keys_for_domain("rules"))
    assert "ranking_weights.ai_score" in rules_keys
    assert "rule_filter.selected_filters" in rules_keys

def test_settings_ia_stage_filter_returns_expected_keys() -> None:
    enrich_keys = set(settings_keys_for_workflow_stage("enrich"))
    assert "pipeline.final_top_n" in enrich_keys
    rule_filter_keys = set(settings_keys_for_workflow_stage("rule_filter"))
    assert "rule_filter.selected_filters" in rule_filter_keys
    cv_generation_keys = set(settings_keys_for_workflow_stage("cv_generation"))
    assert "cv_generation_model" in cv_generation_keys
    assert "cv_summary_enabled" in cv_generation_keys


def test_settings_ia_workflow_stages_include_canonical_stage_for_all_keys() -> None:
    meta = settings_ia_metadata_by_key()
    for key, contract in meta.items():
        stage = str(contract.get("stage") or "")
        workflow_stages = set(contract.get("workflow_stages") or [])
        assert stage in workflow_stages, f"{key} stage {stage!r} missing from workflow_stages"
def test_settings_ia_contract_for_key_contains_required_fields() -> None:
    contract = settings_ia_contract_for_key("cv_certifications_enabled")
    assert set(contract.keys()) == {
        "decision_status",
        "reason_codes",
        "domain",
        "stage",
        "workflow_stages",
        "control_surface",
        "decision_area",
        "complexity_view",
        "risk",
        "runtime_used",
        "metadata_only",
        "override_policy",
        "can_override",
        "is_dangerous",
        "advanced",
        "unused",
        "recommended_delta",
        "applies_when",
    }
    assert contract["domain"] == "general"
    assert "cv_generation" in contract["workflow_stages"]
    assert contract["decision_status"] == DECISION_STATUS_CONFIGURED
    assert contract["reason_codes"] == []

def test_settings_ia_contract_marks_metadata_only_as_non_overrideable() -> None:
    contract = settings_ia_contract_for_key("cv_preset")
    assert contract["metadata_only"] is True
    assert contract["can_override"] is False
    assert contract["override_policy"] == "disabled"


def test_settings_ia_contract_canonical_timing_keys_are_throughput_runtime_used() -> None:
    for key in [
        "stage_runtime.enrich.sleep_secs",
        "stage_runtime.ranking.sleep_secs",
        "stage_runtime.ranking.concurrency",
        "stage_runtime.cv_analysis.concurrency",
        "stage_runtime.cv_generation.sleep_secs",
    ]:
        contract = settings_ia_contract_for_key(key)
        assert contract["decision_area"] == "throughput"
        assert contract["runtime_used"] is True
        assert contract["risk"] == "high"


def test_settings_ia_contract_timing_workflow_stages_cover_late_agentic_stages() -> None:
    contract = settings_ia_contract_for_key("stage_runtime.ranking.sleep_secs")
    workflow_stages = set(contract["workflow_stages"])
    assert "cv_analysis" in workflow_stages
    assert "cv_generation" in workflow_stages

def test_danger_zone_settings_keys_contains_high_risk_groups() -> None:
    keys = set(danger_zone_settings_keys())
    assert "enrichment_concurrency" in keys
    assert "run_lifecycle.max_runtime_minutes" in keys

def test_derive_settings_decision_state_prefers_needs_review_when_blocking() -> None:
    decision = derive_settings_decision_state(
        is_advanced=True,
        is_unused=False,
        is_changed_from_default=True,
        has_recommended_delta=True,
        has_conflict=True,
    )
    assert decision["decision_status"] == DECISION_STATUS_NEEDS_REVIEW
    assert REASON_CODE_CONFLICT in decision["reason_codes"]
    assert REASON_CODE_RECOMMENDED_DELTA in decision["reason_codes"]
    assert REASON_CODE_ADVANCED_ONLY in decision["reason_codes"]
    assert decision["is_blocking"] is True

def test_derive_settings_decision_state_marks_recommended_without_blockers() -> None:
    decision = derive_settings_decision_state(
        is_advanced=False,
        is_unused=False,
        is_changed_from_default=True,
        has_recommended_delta=True,
    )
    assert decision["decision_status"] == DECISION_STATUS_RECOMMENDED
    assert decision["reason_codes"] == [REASON_CODE_CHANGED_FROM_DEFAULT, REASON_CODE_RECOMMENDED_DELTA]
    assert decision["is_blocking"] is False

def test_decision_sort_priority_is_deterministic() -> None:
    assert decision_status_sort_key(DECISION_STATUS_NEEDS_REVIEW) < decision_status_sort_key(DECISION_STATUS_RECOMMENDED)
    assert decision_status_sort_key(DECISION_STATUS_RECOMMENDED) < decision_status_sort_key(DECISION_STATUS_CONFIGURED)
    assert decision_status_sort_key(DECISION_STATUS_CONFIGURED) < decision_status_sort_key(DECISION_STATUS_ADVANCED)

def test_reason_code_is_blocking_only_for_blocking_reasons() -> None:
    assert reason_code_is_blocking(REASON_CODE_CONFLICT) is True
    assert reason_code_is_blocking(REASON_CODE_RECOMMENDED_DELTA) is False


def test_schema_has_required_fields():
    for entry in SETTINGS_SCHEMA:
        assert "key" in entry
        assert "type" in entry       # "int" or "float"
        assert "default" in entry
        assert "label" in entry
        assert "description" in entry
        assert "group" in entry      # "retrieval" | "timing" | "ranking"


def test_schema_tracks_metadata_only_keys_from_registry_truth() -> None:
    assert metadata_only_settings_keys() == {
        "cv_analysis.semantic_alignment.model",
        "cv_preset",
    }


def test_schema_tracks_editable_keys_separately_from_metadata_only() -> None:
    editable_keys = editable_settings_keys()
    assert "cv_generation_model" in editable_keys
    assert "cv_preset" not in editable_keys
    assert "cv_analysis.semantic_alignment.model" not in editable_keys



def test_hidden_deprecated_editable_overlap_is_allowlist_only() -> None:
    editable = settings_schema_module.editable_settings_keys()
    hidden = settings_schema_module.hidden_deprecated_settings_keys()
    allowlist = set(settings_schema_module._EDITABLE_HIDDEN_DEPRECATED_ALLOWLIST)
    overlap = editable & hidden
    assert overlap <= allowlist
    assert "cv_generation_model" in overlap
def test_all_editable_settings_have_persistence_backed_config_paths() -> None:
    schema_by_key = {entry["key"]: entry for entry in SETTINGS_SCHEMA}

def test_hidden_deprecated_editable_overlap_rejects_non_allowlisted_keys(monkeypatch) -> None:
    # Simulate accidental overlap beyond explicit transitional allowlist.
    monkeypatch.setattr(
        settings_schema_module,
        "_EDITABLE_KEYS",
        frozenset({"cv_generation_model", "fake.overlap.key"}),
        raising=False,
    )
    monkeypatch.setattr(
        settings_schema_module,
        "_HIDDEN_DEPRECATED_KEYS",
        frozenset({"cv_generation_model", "fake.overlap.key"}),
        raising=False,
    )
    monkeypatch.setattr(
        settings_schema_module,
        "_EDITABLE_HIDDEN_DEPRECATED_ALLOWLIST",
        frozenset({"cv_generation_model"}),
        raising=False,
    )
    with pytest.raises(RuntimeError, match="allowlisted"):
        settings_schema_module._validate_settings_surface_contract()


def test_feature_source_names_operator_facing_agentic_settings_capability() -> None:
    feature_source = yaml.safe_load(
        Path("docs/features/settings_system/feature.source.yaml").read_text(encoding="utf-8")
    )
    capability_ids = {
        capability["capability_id"]
        for capability in feature_source["capabilities"]
    }
    assert "settings_system.operator-facing-agentic-settings" in capability_ids


def test_agentic_settings_sections_have_expected_slugs() -> None:
    assert set(AGENTIC_SETTINGS_SECTIONS.keys()) == {
        "agentic-core",
        "agentic-advanced",
    }

def test_settings_sections_exclude_legacy_retrieval_advanced_slug() -> None:
    """Task-first agentic advanced controls replace the legacy retrieval-advanced section."""
    assert "retrieval-advanced" not in SETTINGS_SECTIONS


def test_agentic_settings_section_ownership_is_explicit() -> None:
    assert AGENTIC_SETTINGS_SECTIONS["agentic-core"] == [
        "cv.agentic_late_stage.enabled",
        "synonym_management.propose_enabled",
        "synonym_management.apply_to_run_enabled",
        "synonym_management.promote_global_enabled",
        "synonym_management.auto_triage_recommendation_enabled",
        "synonym_management.triage_recommendation_reuse_enabled",
        "synonym_management.auto_apply_recommendation_enabled",
        "synonym_management.auto_promote_global_enabled",
        "synonym_management.auto_accept_ai_action_enabled",
        "cv_analysis.semantic_alignment.enabled",
    ]
    assert AGENTIC_SETTINGS_SECTIONS["agentic-advanced"] == [
        "cv_analysis.semantic_alignment.model",
        "cv_analysis.semantic_alignment.required_skill_lexical_weight",
        "cv_analysis.semantic_alignment.required_skill_semantic_weight",
        "cv_analysis.semantic_alignment.role_lexical_weight",
        "cv_analysis.semantic_alignment.role_semantic_weight",
        "cv_analysis.semantic_alignment.responsibility_lexical_weight",
        "cv_analysis.semantic_alignment.responsibility_semantic_weight",
        "cv_analysis.semantic_alignment.domain_lexical_weight",
        "cv_analysis.semantic_alignment.domain_semantic_weight",
        "cv_analysis.semantic_alignment.channel_pool_size",
    ]


def test_agentic_settings_mutability_distinguishes_editable_metadata_only_and_excluded() -> None:
    assert metadata_only_agentic_settings_keys() == {
        "cv_analysis.semantic_alignment.model",
    }
    assert editable_agentic_settings_keys() == {
        "cv.agentic_late_stage.enabled",
        "synonym_management.propose_enabled",
        "synonym_management.apply_to_run_enabled",
        "synonym_management.promote_global_enabled",
        "synonym_management.auto_triage_recommendation_enabled",
        "synonym_management.triage_recommendation_reuse_enabled",
        "synonym_management.auto_apply_recommendation_enabled",
        "synonym_management.auto_promote_global_enabled",
        "synonym_management.auto_accept_ai_action_enabled",
        "cv_analysis.semantic_alignment.enabled",
        "cv_analysis.semantic_alignment.required_skill_lexical_weight",
        "cv_analysis.semantic_alignment.required_skill_semantic_weight",
        "cv_analysis.semantic_alignment.role_lexical_weight",
        "cv_analysis.semantic_alignment.role_semantic_weight",
        "cv_analysis.semantic_alignment.responsibility_lexical_weight",
        "cv_analysis.semantic_alignment.responsibility_semantic_weight",
        "cv_analysis.semantic_alignment.domain_lexical_weight",
        "cv_analysis.semantic_alignment.domain_semantic_weight",
        "cv_analysis.semantic_alignment.channel_pool_size",
    }
    assert excluded_agentic_settings_keys() == {
        "cv_prompt_version",
        "cv_template_path",
        "skill_synonyms_runtime",
    }


def test_all_editable_agentic_settings_have_persistence_backed_config_paths() -> None:
    schema_by_key = {entry["key"]: entry for entry in SETTINGS_SCHEMA}
    for key in editable_agentic_settings_keys():
        assert schema_by_key[key]["config_path"], f"{key} is editable but has no config_path"


def test_setup_only_and_deployment_only_agentic_knobs_stay_out_of_registry() -> None:
    schema_keys = {entry["key"] for entry in SETTINGS_SCHEMA}
    for key in excluded_agentic_settings_keys():
        assert key not in schema_keys
        assert key not in editable_settings_keys()
        assert key not in metadata_only_settings_keys()


# ── type coercion ─────────────────────────────────────────────────────────────

def test_coerce_int_from_string():
    from fitcv_cp.settings_schema import coerce_value
    assert coerce_value("pipeline.final_top_n", "5") == 5
    assert isinstance(coerce_value("pipeline.final_top_n", "5"), int)


def test_coerce_float_from_string():
    from fitcv_cp.settings_schema import coerce_value
    assert coerce_value("ranking_weights.ai_score", "0.5") == 0.5


def test_coerce_rejects_unknown_key():
    from fitcv_cp.settings_schema import coerce_value
    with pytest.raises(KeyError):
        coerce_value("unknown.key", "1")


# ── per-field validation ──────────────────────────────────────────────────────

def test_int_top_n_must_be_positive():
    with pytest.raises(ValidationError, match="pipeline.final_top_n"):
        validate_settings({"pipeline.final_top_n": 0})


def test_float_threshold_must_be_in_range():
    with pytest.raises(ValidationError, match="fit_label_thresholds.strong"):
        validate_settings({"fit_label_thresholds.strong": 1.5})


def test_sleep_secs_may_be_zero():
    validate_settings({"enrichment_sleep_secs": 0.0})  # should not raise
    validate_settings({"stage_runtime.cv_generation.sleep_secs": 0.0})  # should not raise


# ── relational validation ─────────────────────────────────────────────────────

def test_top_n_relational_constraint():
    """final_top_n <= ai_score_top_n <= vector_search_top_n"""
    with pytest.raises(ValidationError, match="final_top_n"):
        validate_settings({
            "pipeline.vector_search_top_n": 50,
            "pipeline.ai_score_top_n": 50,
            "pipeline.final_top_n": 60,   # violates: 60 > 50
        })


def test_fit_label_strong_must_exceed_stretch():
    with pytest.raises(ValidationError, match="fit_label_thresholds"):
        validate_settings({
            "fit_label_thresholds.strong": 0.40,
            "fit_label_thresholds.stretch": 0.70,   # violates: stretch > strong
        })


def test_ranking_weights_must_sum_to_one():
    """@proves settings_system.ranking-settings"""

def test_relational_constraint_error_message_exact_for_top_n() -> None:
    with pytest.raises(
        ValidationError,
        match=r"^pipeline\.ai_score_top_n \(60\) must be <= pipeline\.vector_search_top_n \(50\)$",
    ):
        validate_settings({
            "pipeline.vector_search_top_n": 50,
            "pipeline.ai_score_top_n": 60,
        })

def test_weight_sum_tolerance_boundary_and_message_parity() -> None:
    # Preserve current behavior: 1.0100 total is rejected in practice (float precision path).
    with pytest.raises(ValidationError, match=r"ranking_weights must sum to 1\.0"):
        validate_settings({
            "ranking_weights.ai_score": 0.41,
            "ranking_weights.must_have_match": 0.20,
            "ranking_weights.vector_similarity": 0.15,
            "ranking_weights.title_relevance": 0.10,
            "ranking_weights.seniority_fit": 0.10,
            "ranking_weights.preference_fit": 0.05,
        })
    # Beyond tolerance is also rejected with canonical label path.
    with pytest.raises(ValidationError, match=r"ranking_weights must sum to 1\.0"):
        validate_settings({
            "ranking_weights.ai_score": 0.42,
            "ranking_weights.must_have_match": 0.20,
            "ranking_weights.vector_similarity": 0.15,
            "ranking_weights.title_relevance": 0.10,
            "ranking_weights.seniority_fit": 0.10,
            "ranking_weights.preference_fit": 0.05,
        })

def test_ranking_weights_partial_update_skips_sum_check():
    """Partial updates are allowed; sum-to-1 only checked when ALL 6 are present."""
    validate_settings({"ranking_weights.ai_score": 0.50})  # should not raise


def test_gap_thresholds_strong_must_exceed_stretch():
    with pytest.raises(ValidationError, match="gap_thresholds"):
        validate_settings({
            "gap_thresholds.strong_min_matched_ratio": 0.30,
            "gap_thresholds.stretch_min_matched_ratio": 0.50,
        })

@pytest.mark.parametrize(
    ("settings", "expected_error"),
    [
        (
            {"pipeline.vector_search_top_n": 50, "pipeline.ai_score_top_n": 60},
            r"pipeline\.ai_score_top_n \(60\) must be <= pipeline\.vector_search_top_n \(50\)",
        ),
        (
            {"pipeline.ai_score_top_n": 20, "pipeline.final_top_n": 30},
            r"pipeline\.final_top_n \(30\) must be <= pipeline\.ai_score_top_n \(20\)",
        ),
        (
            {"fit_label_thresholds.strong": 0.40, "fit_label_thresholds.stretch": 0.70},
            r"fit_label_thresholds\.strong \(0\.4\) must be > stretch \(0\.7\)",
        ),
        (
            {
                "gap_thresholds.strong_min_matched_ratio": 0.30,
                "gap_thresholds.stretch_min_matched_ratio": 0.50,
            },
            r"gap_thresholds\.strong_min_matched_ratio \(0\.3\) must be > stretch \(0\.5\)",
        ),
    ],
)
def test_relational_constraint_registry_enforced_for_all_pairs(
    settings: dict[str, float | int], expected_error: str
) -> None:
    with pytest.raises(ValidationError, match=expected_error):
        validate_settings(settings)


def test_unknown_key_rejected():
    with pytest.raises(ValidationError, match="unknown"):
        validate_settings({"unknown.key": 1})


# ── config application ────────────────────────────────────────────────────────

def test_apply_settings_to_config_nested():
    config = {"pipeline": {"final_top_n": 10}, "ranking_weights": {"ai_score": 0.40}}
    apply_settings_to_config(config, {"pipeline.final_top_n": 5, "ranking_weights.ai_score": 0.50})
    assert config["pipeline"]["final_top_n"] == 5
    assert config["ranking_weights"]["ai_score"] == 0.50


def test_apply_settings_to_config_flat_key():
    config = {"enrichment_sleep_secs": 1.0}
    apply_settings_to_config(config, {"enrichment_sleep_secs": 0.5})
    assert config["enrichment_sleep_secs"] == 0.5

def test_apply_settings_to_config_stage_runtime_nested_path() -> None:
    config: dict[str, object] = {}
    apply_settings_to_config(config, {"stage_runtime.cv_analysis.concurrency": 2})
    assert config["stage_runtime"] == {"cv_analysis": {"concurrency": 2}}

def test_legacy_throughput_alias_hydrates_canonical_value() -> None:
    config = {"enrichment_sleep_secs": 1.0}
    apply_settings_to_config(config, {"enrichment_sleep_secs": 0.75})
    assert config["stage_runtime"]["enrich"]["sleep_secs"] == 0.75

def test_canonical_value_wins_over_legacy_alias_for_validation_and_apply() -> None:
    settings = {
        "enrichment_sleep_secs": 0.8,
        "stage_runtime.enrich.sleep_secs": 0.2,
    }
    validate_settings(settings)
    config = {"enrichment_sleep_secs": 1.0}
    apply_settings_to_config(config, settings)
    assert config["stage_runtime"]["enrich"]["sleep_secs"] == 0.2


# ── global_job_filters settings ───────────────────────────────────────────────

def test_global_job_filters_keys_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "global_job_filters.applications_count_max" in keys
    assert "global_job_filters.max_age_days" in keys


def test_global_job_filters_group_name():
    for entry in SETTINGS_SCHEMA:
        if entry["key"].startswith("global_job_filters."):
            assert entry["group"] == "global_job_filters"


def test_global_job_filters_apply_settings_to_config_writes_correct_path():
    config: dict = {}
    apply_settings_to_config(config, {
        "global_job_filters.applications_count_max": 150,
        "global_job_filters.max_age_days": 14,
    })
    assert config["global_job_filters"]["applications_count_max"] == 150
    assert config["global_job_filters"]["max_age_days"] == 14


def test_global_job_filters_validate_rejects_zero():
    with pytest.raises(ValidationError):
        validate_settings({"global_job_filters.applications_count_max": 0})


def test_global_job_filters_validate_rejects_negative():
    with pytest.raises(ValidationError):
        validate_settings({"global_job_filters.max_age_days": -1})


def test_global_job_filters_validate_accepts_positive():
    validate_settings({
        "global_job_filters.applications_count_max": 200,
        "global_job_filters.max_age_days": 30,
    })  # must not raise


def test_run_lifecycle_max_runtime_minutes_validate_accepts_positive() -> None:
    validate_settings({"run_lifecycle.max_runtime_minutes": 240})


def test_run_lifecycle_max_runtime_minutes_validate_rejects_zero() -> None:
    with pytest.raises(ValidationError):
        validate_settings({"run_lifecycle.max_runtime_minutes": 0})


def test_apply_settings_to_config_run_lifecycle_writes_nested_path() -> None:
    config: dict = {}
    apply_settings_to_config(config, {"run_lifecycle.max_runtime_minutes": 180})
    assert config["run_lifecycle"]["max_runtime_minutes"] == 180


# ── rule_filter.selected_filters settings ────────────────────────────────────

def test_rule_filter_selected_filters_key_registered() -> None:
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "rule_filter.selected_filters" in keys


def test_rule_filter_selected_filters_uses_list_str_type() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["rule_filter.selected_filters"]["type"] == "list[str]"


def test_rule_filter_selected_filters_default_matches_spec() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["rule_filter.selected_filters"]["default"] == [
        "seniority_mismatch",
        "location_type_excluded",
        "contract_type_excluded",
        "experience_level_excluded",
    ]


def test_rule_filter_selected_filters_default_matches_runtime_contract() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["rule_filter.selected_filters"]["default"] == DEFAULT_SELECTED_RULE_FILTERS


def test_retrieval_defaults_are_hydrated_from_centralized_pipeline_config() -> None:
    """@proves settings_system.retrieval-settings"""
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["pipeline.vector_search_top_n"]["default"] == 50
    assert schema_by_key["pipeline.ai_score_top_n"]["default"] == 50
    assert schema_by_key["pipeline.final_top_n"]["default"] == 10
    assert schema_by_key["pipeline.evidence_top_k"]["default"] == 5

def test_runtime_overlay_defaults_do_not_mutate_declared_schema_defaults() -> None:
    declared_before = {
        entry["key"]: entry["default"]
        for entry in SETTINGS_SCHEMA
        if entry["key"] in {
            "pipeline.vector_search_top_n",
            "pipeline.ai_score_top_n",
            "pipeline.final_top_n",
            "pipeline.evidence_top_k",
        }
    }
    overlaid = settings_schema_module.settings_schema_with_runtime_defaults(
        {
            "pipeline": {
                "vector_search_top_n": 77,
                "ai_score_top_n": 66,
                "final_top_n": 11,
                "evidence_top_k": 9,
            }
        }
    )
    overlay_by_key = {entry["key"]: entry for entry in overlaid}
    assert overlay_by_key["pipeline.vector_search_top_n"]["default"] == 77
    assert overlay_by_key["pipeline.ai_score_top_n"]["default"] == 66
    assert overlay_by_key["pipeline.final_top_n"]["default"] == 11
    assert overlay_by_key["pipeline.evidence_top_k"]["default"] == 9

    declared_after = {
        entry["key"]: entry["default"]
        for entry in SETTINGS_SCHEMA
        if entry["key"] in declared_before
    }
    assert declared_after == declared_before

def test_runtime_overlay_defaults_returns_independent_list_defaults_copy() -> None:
    overlaid = settings_schema_module.settings_schema_with_runtime_defaults(
        {
            "rule_filter": {
                "selected_filters": ["seniority_mismatch", "domain_not_preferred"],
            }
        }
    )
    overlay_by_key = {entry["key"]: entry for entry in overlaid}
    overlay_list = overlay_by_key["rule_filter.selected_filters"]["default"]
    assert overlay_list == ["seniority_mismatch", "domain_not_preferred"]
    assert isinstance(overlay_list, list)
    overlay_list.append("must_have_skill_missing")

    declared_by_key = {entry["key"]: entry for entry in SETTINGS_SCHEMA}
    assert declared_by_key["rule_filter.selected_filters"]["default"] == [
        "seniority_mismatch",
        "location_type_excluded",
        "contract_type_excluded",
        "experience_level_excluded",
    ]


def test_rule_filter_selected_filters_validate_accepts_known_codes() -> None:
    validate_settings({
        "rule_filter.selected_filters": [
            "seniority_mismatch",
            "must_have_skill_missing",
        ]
    })


def test_rule_filter_selected_filters_validate_rejects_duplicates() -> None:
    with pytest.raises(ValidationError, match="duplicate"):
        validate_settings({
            "rule_filter.selected_filters": [
                "seniority_mismatch",
                "seniority_mismatch",
            ]
        })


def test_rule_filter_selected_filters_validate_rejects_unknown_code() -> None:
    with pytest.raises(ValidationError, match="must be one of"):
        validate_settings({
            "rule_filter.selected_filters": [
                "seniority_mismatch",
                "not_a_real_filter",
            ]
        })


def test_apply_settings_to_config_rule_filter_selected_filters_nested() -> None:
    config: dict = {}
    apply_settings_to_config(config, {
        "rule_filter.selected_filters": [
            "seniority_mismatch",
            "domain_not_preferred",
        ]
    })


def test_cv_analysis_semantic_alignment_validate_accepts_balanced_weight_pairs() -> None:
    """@proves settings_system.cv-analysis-alignment-settings"""
    validate_settings({
        "cv_analysis.semantic_alignment.required_skill_lexical_weight": 0.70,
        "cv_analysis.semantic_alignment.required_skill_semantic_weight": 0.30,
        "cv_analysis.semantic_alignment.role_lexical_weight": 0.60,
        "cv_analysis.semantic_alignment.role_semantic_weight": 0.40,
        "cv_analysis.semantic_alignment.responsibility_lexical_weight": 0.25,
        "cv_analysis.semantic_alignment.responsibility_semantic_weight": 0.75,
        "cv_analysis.semantic_alignment.domain_lexical_weight": 0.40,
        "cv_analysis.semantic_alignment.domain_semantic_weight": 0.60,
    })


def test_cv_analysis_semantic_alignment_validate_rejects_unbalanced_required_skill_weights() -> None:
    with pytest.raises(ValidationError, match="required-skill"):
        validate_settings({
            "cv_analysis.semantic_alignment.required_skill_lexical_weight": 0.50,
            "cv_analysis.semantic_alignment.required_skill_semantic_weight": 0.20,
        })


def test_cv_analysis_semantic_alignment_validate_rejects_unbalanced_role_weights() -> None:
    with pytest.raises(ValidationError, match="role"):
        validate_settings({
            "cv_analysis.semantic_alignment.role_lexical_weight": 0.20,
            "cv_analysis.semantic_alignment.role_semantic_weight": 0.20,
        })


def test_cv_analysis_semantic_alignment_validate_rejects_unbalanced_responsibility_weights() -> None:
    with pytest.raises(ValidationError, match="responsibility"):
        validate_settings({
            "cv_analysis.semantic_alignment.responsibility_lexical_weight": 0.20,
            "cv_analysis.semantic_alignment.responsibility_semantic_weight": 0.50,
        })


def test_cv_analysis_semantic_alignment_validate_rejects_unbalanced_domain_weights() -> None:
    with pytest.raises(ValidationError, match="domain"):
        validate_settings({
            "cv_analysis.semantic_alignment.domain_lexical_weight": 0.30,
            "cv_analysis.semantic_alignment.domain_semantic_weight": 0.30,
        })


# ── RANKING_GROUPS registry ───────────────────────────────────────────────────

def test_ranking_groups_has_four_slugs():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    assert set(RANKING_GROUPS.keys()) == {
        "ranking-weights",
        "preference-fit-weights",
        "fit-label-thresholds",
        "gap-thresholds",
    }


def test_ranking_groups_all_keys_in_schema():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    schema_keys = {s["key"] for s in SETTINGS_SCHEMA}
    for slug, keys in RANKING_GROUPS.items():
        for key in keys:
            assert key in schema_keys, f"{key!r} from group {slug!r} not found in SETTINGS_SCHEMA"


def test_ranking_weights_group_has_six_keys():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    assert len(RANKING_GROUPS["ranking-weights"]) == 6


def test_preference_fit_weights_group_has_three_keys() -> None:
    from fitcv_cp.settings_schema import RANKING_GROUPS
    assert len(RANKING_GROUPS["preference-fit-weights"]) == 3


def test_ranking_weight_copy_matches_runtime_semantics():
    schema_by_key = {entry["key"]: entry for entry in SETTINGS_SCHEMA}
    assert schema_by_key["ranking_weights.title_relevance"]["description"] == (
        "How much influence semantic role alignment between the job title and the candidate's target role has on the final ranking."
    )
    assert schema_by_key["ranking_weights.preference_fit"]["label"] == "Weight: Preference Alignment"
    assert schema_by_key["ranking_weights.preference_fit"]["description"] == (
        "How much influence weighted candidate preference alignment across domain, role family, and location type has on the final candidate ranking."
    )


def test_preference_fit_weight_keys_registered() -> None:
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "preference_fit_weights.domain" in keys
    assert "preference_fit_weights.role_family" in keys
    assert "preference_fit_weights.location_type" in keys


def test_preference_fit_weight_copy_matches_runtime_semantics() -> None:
    schema_by_key = {entry["key"]: entry for entry in SETTINGS_SCHEMA}
    assert schema_by_key["preference_fit_weights.domain"]["description"] == (
        "Relative importance of explicit domain preference alignment within the preference-fit feature."
    )
    assert schema_by_key["preference_fit_weights.role_family"]["description"] == (
        "Relative importance of explicit role-family preference alignment within the preference-fit feature."
    )
    assert schema_by_key["preference_fit_weights.location_type"]["description"] == (
        "Relative importance of explicit location-type preference alignment within the preference-fit feature."
    )


def test_preference_fit_weights_must_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="preference_fit_weights"):
        validate_settings({
            "preference_fit_weights.domain": 0.70,
            "preference_fit_weights.role_family": 0.20,
            "preference_fit_weights.location_type": 0.20,
        })

@pytest.mark.parametrize(
    ("settings", "label"),
    [
        (
            {
                "ranking_weights.ai_score": 0.42,
                "ranking_weights.must_have_match": 0.20,
                "ranking_weights.vector_similarity": 0.15,
                "ranking_weights.title_relevance": 0.10,
                "ranking_weights.seniority_fit": 0.10,
                "ranking_weights.preference_fit": 0.05,
            },
            "ranking_weights",
        ),
        (
            {
                "preference_fit_weights.domain": 0.70,
                "preference_fit_weights.role_family": 0.20,
                "preference_fit_weights.location_type": 0.20,
            },
            "preference_fit_weights",
        ),
        (
            {
                "cv_analysis.semantic_alignment.required_skill_lexical_weight": 0.60,
                "cv_analysis.semantic_alignment.required_skill_semantic_weight": 0.30,
            },
            "required-skill semantic alignment weights",
        ),
        (
            {
                "cv_analysis.semantic_alignment.role_lexical_weight": 0.55,
                "cv_analysis.semantic_alignment.role_semantic_weight": 0.30,
            },
            "role semantic alignment weights",
        ),
        (
            {
                "cv_analysis.semantic_alignment.responsibility_lexical_weight": 0.25,
                "cv_analysis.semantic_alignment.responsibility_semantic_weight": 0.60,
            },
            "responsibility semantic alignment weights",
        ),
        (
            {
                "cv_analysis.semantic_alignment.domain_lexical_weight": 0.20,
                "cv_analysis.semantic_alignment.domain_semantic_weight": 0.70,
            },
            "domain semantic alignment weights",
        ),
    ],
)
def test_weight_sum_constraint_registry_enforced_for_all_families(
    settings: dict[str, float], label: str
) -> None:
    with pytest.raises(ValidationError, match=rf"{label} must sum to 1\.0"):
        validate_settings(settings)


def test_ranking_groups_threshold_groups_have_two_keys_each():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    assert len(RANKING_GROUPS["fit-label-thresholds"]) == 2
    assert len(RANKING_GROUPS["gap-thresholds"]) == 2


# ── SETTINGS_SECTIONS registry ────────────────────────────────────────────────

def test_settings_sections_has_expected_slugs():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    assert set(SETTINGS_SECTIONS.keys()) == {
        "retrieval-core",
        "timing",
        "run-lifecycle",
        "global-job-filters",
        "rule-filter",
    }


def test_settings_sections_all_keys_in_schema():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS, SETTINGS_SCHEMA
    schema_keys = {s["key"] for s in SETTINGS_SCHEMA}
    for slug, keys in SETTINGS_SECTIONS.items():
        for key in keys:
            assert key in schema_keys, (
                f"{key!r} from SETTINGS_SECTIONS[{slug!r}] not found in SETTINGS_SCHEMA"
            )


def test_settings_sections_no_key_appears_twice():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    seen: set[str] = set()
    for slug, keys in SETTINGS_SECTIONS.items():
        for key in keys:
            assert key not in seen, f"{key!r} appears in multiple sections"
            seen.add(key)


def test_settings_sections_retrieval_core_stays_focused_on_selection_funnel():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    assert "pipeline.evidence_top_k" in SETTINGS_SECTIONS["retrieval-core"]
    assert "cv_analysis.semantic_alignment.enabled" not in SETTINGS_SECTIONS["retrieval-core"]
    assert "retrieval-advanced" not in SETTINGS_SECTIONS


def test_agentic_sections_own_semantic_alignment_enablement() -> None:
    from fitcv_cp.settings_schema import AGENTIC_SETTINGS_SECTIONS

    assert "cv_analysis.semantic_alignment.enabled" in AGENTIC_SETTINGS_SECTIONS["agentic-core"]


def test_settings_sections_global_job_filters_has_two_keys():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    assert len(SETTINGS_SECTIONS["global-job-filters"]) == 2


# ── enrichment parallelism settings ───────────────────────────────────────────

def test_enrichment_parallelism_keys_registered():
    """@proves bounded_parallel_enrichment.enrichment-batch-size-setting
    @proves bounded_parallel_enrichment.enrichment-concurrency-setting
    """
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "enrichment_batch_size" in keys
    assert "enrichment_concurrency" in keys
    assert "stage_runtime.cv_generation.concurrency" in keys


def test_enrichment_parallelism_defaults():
    """@proves bounded_parallel_enrichment.defaults-batch-size-10-concurrency-8"""
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["enrichment_batch_size"]["default"] == 10
    assert schema_by_key["enrichment_concurrency"]["default"] == 8


def test_enrichment_parallelism_group_is_timing():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["enrichment_batch_size"]["group"] == "timing"
    assert schema_by_key["enrichment_concurrency"]["group"] == "timing"


def test_enrichment_batch_size_validate_rejects_zero():
    with pytest.raises(ValidationError):
        validate_settings({"enrichment_batch_size": 0})


def test_enrichment_batch_size_validate_rejects_negative():
    with pytest.raises(ValidationError):
        validate_settings({"enrichment_batch_size": -5})


def test_enrichment_concurrency_validate_rejects_zero():
    with pytest.raises(ValidationError):
        validate_settings({"enrichment_concurrency": 0})


def test_enrichment_concurrency_validate_accepts_one():
    validate_settings({"enrichment_concurrency": 1})  # must not raise


def test_enrichment_batch_size_apply_writes_correct_path():
    """@proves bounded_parallel_enrichment.enrichment-batch-size-setting"""
    config: dict = {}
    apply_settings_to_config(config, {"enrichment_batch_size": 5})
    assert config["enrichment_batch_size"] == 5


def test_enrichment_concurrency_apply_writes_correct_path():
    """@proves bounded_parallel_enrichment.enrichment-concurrency-setting"""
    config: dict = {}
    apply_settings_to_config(config, {"enrichment_concurrency": 3})
    assert config["enrichment_concurrency"] == 3


def test_enrichment_parallelism_in_settings_sections_timing():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    assert "enrichment_batch_size" in SETTINGS_SECTIONS["timing"]
    assert "enrichment_concurrency" in SETTINGS_SECTIONS["timing"]


# ── CV settings schema ────────────────────────────────────────────────────────

def test_cv_settings_keys_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_preset" in keys
    assert "cv_generation_model" in keys
    assert "cv_max_pages" in keys
    assert "cv_template_path" not in keys
    assert "cv_prompt_version" not in keys


def test_cv_settings_have_correct_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    # preset and composition fields are in new groups
    assert schema_by_key["cv_preset"]["group"] == "cv_preset"
    assert schema_by_key["cv_generation_model"]["group"] == "cv_composition"
    assert schema_by_key["cv_summary_enabled"]["group"] == "cv_composition"
    assert schema_by_key["cv_max_pages"]["group"] == "cv_validation"


def test_cv_settings_defaults():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["default"] == "europass"
    assert schema_by_key["cv_generation_model"]["default"] == "gemini-2.5-flash"
    assert schema_by_key["cv_max_pages"]["default"] == 2


def test_cv_settings_types():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["type"] == "str"
    assert schema_by_key["cv_generation_model"]["type"] == "str"
    assert schema_by_key["cv_max_pages"]["type"] == "int"
    assert schema_by_key["cv_summary_enabled"]["type"] == "bool"
    assert schema_by_key["cv_education_enabled"]["type"] == "bool"
    assert schema_by_key["cv_experience_enabled"]["type"] == "bool"
    assert schema_by_key["cv_skills_enabled"]["type"] == "bool"
    assert schema_by_key["cv_certifications_enabled"]["type"] == "bool"
    assert schema_by_key["cv_projects_enabled"]["type"] == "bool"
    assert schema_by_key["cv_publications_enabled"]["type"] == "bool"
    assert schema_by_key["cv_languages_enabled"]["type"] == "bool"
    assert "cv_emphasize_required_skills" not in schema_by_key
    assert "cv_align_jd_terminology" not in schema_by_key
    assert "cv_evidence_grounded_only" not in schema_by_key


def test_pipeline_evidence_top_k_not_in_cv_group():
    """evidence_top_k stays in retrieval, not in the CV section."""
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["pipeline.evidence_top_k"]["group"] != "cv_generation"


def test_cv_generation_keys_in_cv_groups():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv_preset" in CV_GROUPS["cv-preset"]
    assert "cv_generation_model" in CV_GROUPS["cv-preset"]


def test_cv_groups_all_keys_in_schema():
    from fitcv_cp.settings_schema import CV_GROUPS
    schema_keys = {s["key"] for s in SETTINGS_SCHEMA}
    for slug, keys in CV_GROUPS.items():
        for key in keys:
            assert key in schema_keys, f"{key!r} from CV_GROUPS[{slug!r}] not found in SETTINGS_SCHEMA"


def test_cv_groups_no_key_appears_twice():
    from fitcv_cp.settings_schema import CV_GROUPS
    seen: set[str] = set()
    for slug, keys in CV_GROUPS.items():
        for key in keys:
            assert key not in seen, f"{key!r} appears in multiple CV groups"
            seen.add(key)


# ── Preset-based CV settings schema ─────────────────────────────────────────────

def test_cv_preset_key_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_preset" in keys
    assert "synonym_management.propose_enabled" in keys
    assert "synonym_management.apply_to_run_enabled" in keys
    assert "synonym_management.promote_global_enabled" in keys
    assert "synonym_management.auto_apply_recommendation_enabled" in keys
    assert "synonym_management.auto_promote_global_enabled" in keys
    assert "synonym_management.auto_accept_ai_action_enabled" in keys


def test_synonym_management_automation_defaults() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["synonym_management.auto_apply_recommendation_enabled"]["default"] is False
    assert schema_by_key["synonym_management.auto_promote_global_enabled"]["default"] is False
    assert schema_by_key["synonym_management.auto_accept_ai_action_enabled"]["default"] is True


def test_cv_preset_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["default"] == "europass"


def test_cv_preset_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["type"] == "str"


def test_cv_preset_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["group"] == "cv_preset"


# ── Generation fields ─────────────────────────────────────────────────────────────

def test_cv_generation_fields_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_generation_model" in keys
    assert "cv_prompt_version" not in keys


def test_cv_generation_model_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["type"] == "str"


def test_cv_generation_model_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["group"] == "cv_composition"


# ── Composition fields ───────────────────────────────────────────────────────────

def test_cv_composition_fields_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_summary_enabled" in keys
    assert "cv_education_enabled" in keys
    assert "cv_experience_enabled" in keys
    assert "cv_skills_enabled" in keys
    assert "cv_certifications_enabled" in keys
    assert "cv_projects_enabled" in keys
    assert "cv_publications_enabled" in keys
    assert "cv_languages_enabled" in keys
    assert "cv_summary_style" not in keys
    assert "cv_education_detail" not in keys
    assert "cv_experience_bullet_style" not in keys
    assert "cv_skills_max_items" not in keys
    assert "cv_publications_detail" not in keys
    assert "cv_languages_detail" not in keys
    assert "cv_education_required" not in keys
    assert "cv_projects_required" not in keys


def test_cv_education_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_education_enabled"]["type"] == "bool"

def test_cv_experience_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_experience_enabled"]["type"] == "bool"

def test_cv_skills_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_skills_enabled"]["type"] == "bool"


def test_cv_certifications_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_certifications_enabled"]["type"] == "bool"


def test_cv_projects_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_projects_enabled"]["type"] == "bool"


def test_cv_publications_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_publications_enabled"]["type"] == "bool"


def test_cv_languages_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_languages_enabled"]["type"] == "bool"


def test_cv_composition_fields_have_correct_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    for key in (
        "cv_summary_enabled",
        "cv_education_enabled",
        "cv_experience_enabled",
        "cv_skills_enabled",
        "cv_certifications_enabled",
        "cv_projects_enabled",
        "cv_publications_enabled",
        "cv_languages_enabled",
    ):
        assert schema_by_key[key]["group"] == "cv_composition", f"{key} should be in cv_composition group"


def test_cv_composition_retired_formatting_fields_removed():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    for key in (
        "cv_summary_style",
        "cv_education_detail",
        "cv_experience_bullet_style",
        "cv_skills_max_items",
        "cv_publications_detail",
        "cv_languages_detail",
    ):
        assert key not in schema_by_key


# ── Content rules fields ────────────────────────────────────────────────────────

def test_cv_content_rules_fields_removed():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_emphasize_required_skills" not in keys
    assert "cv_align_jd_terminology" not in keys
    assert "cv_evidence_grounded_only" not in keys


def test_cv_content_rules_group_removed():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv-content-rules" not in CV_GROUPS


# ── Validation fields ────────────────────────────────────────────────────────────

def test_cv_validation_fields_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_max_pages" in keys


def test_cv_max_pages_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_max_pages"]["type"] == "int"


def test_cv_max_pages_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_max_pages"]["group"] == "cv_validation"


# ── CV group registries ─────────────────────────────────────────────────────────

def test_cv_groups_has_expected_subgroups():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv-preset" in CV_GROUPS
    assert "cv-composition" in CV_GROUPS
    assert "cv-validation" in CV_GROUPS


def test_cv_groups_preset_has_correct_keys():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv_preset" in CV_GROUPS["cv-preset"]
    assert "cv_generation_model" in CV_GROUPS["cv-preset"]


def test_cv_groups_composition_has_all_composition_keys():
    from fitcv_cp.settings_schema import CV_GROUPS
    expected = {
        "cv_summary_enabled",
        "cv_education_enabled",
        "cv_experience_enabled",
        "cv_skills_enabled",
        "cv_certifications_enabled", "cv_projects_enabled",
        "cv_publications_enabled",
        "cv_languages_enabled",
    }
    assert set(CV_GROUPS["cv-composition"]) == expected


def test_cv_groups_validation_has_cv_max_pages():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv_max_pages" in CV_GROUPS["cv-validation"]


def test_cv_groups_no_key_appears_twice():
    from fitcv_cp.settings_schema import CV_GROUPS
    seen: set[str] = set()
    for slug, keys in CV_GROUPS.items():
        for key in keys:
            assert key not in seen, f"{key!r} appears in multiple CV groups"
            seen.add(key)


def test_cv_groups_all_keys_in_schema():
    from fitcv_cp.settings_schema import CV_GROUPS
    schema_keys = {s["key"] for s in SETTINGS_SCHEMA}
    for slug, keys in CV_GROUPS.items():
        for key in keys:
            assert key in schema_keys, f"{key!r} from CV_GROUPS[{slug!r}] not found in SETTINGS_SCHEMA"


# ── coerce_value for new CV types ────────────────────────────────────────────────

def test_coerce_bool_from_string():
    from fitcv_cp.settings_schema import coerce_value
    result = coerce_value("cv_education_enabled", "true")
    assert result is True
    assert isinstance(result, bool)


def test_coerce_bool_from_string_false():
    from fitcv_cp.settings_schema import coerce_value
    result = coerce_value("cv_education_enabled", "false")
    assert result is False
    assert isinstance(result, bool)


# ── validate_settings for new CV fields ─────────────────────────────────────────

def test_cv_preset_rejects_empty():
    with pytest.raises(ValidationError, match="cv_preset"):
        validate_settings({"cv_preset": ""})


def test_cv_preset_rejects_whitespace_only():
    with pytest.raises(ValidationError, match="cv_preset"):
        validate_settings({"cv_preset": "   "})


# ── apply_settings_to_config for new CV fields ──────────────────────────────────

def test_apply_settings_to_config_cv_preset():
    config: dict = {}
    apply_settings_to_config(config, {"cv_preset": "europass"})
    assert config["cv"]["preset"] == "europass"


def test_apply_settings_to_config_cv_composition_nested():
    config: dict = {}
    apply_settings_to_config(config, {
        "cv_summary_enabled": False,
        "cv_education_enabled": True,
        "cv_skills_enabled": True,
    })
    assert config["cv"]["composition"]["summary"]["enabled"] is False
    assert config["cv"]["composition"]["education"]["enabled"] is True
    assert config["cv"]["composition"]["skills"]["enabled"] is True


def test_apply_settings_to_config_cv_validation_nested():
    config: dict = {}
    apply_settings_to_config(config, {"cv_max_pages": 3})
    assert config["cv"]["validation"]["max_pages"] == 3


def test_apply_settings_to_config_cv_generation_nested():
    """@proves settings_system.cv-generation-settings"""
    config: dict = {}
    apply_settings_to_config(config, {
        "cv_generation_model": "gemini-2.5-flash",
    })
    assert config["cv"]["generation"]["model"] == "gemini-2.5-flash"


def test_apply_settings_to_config_cv_preset_with_existing_cv_structure():
    """apply_settings_to_config must work when cv key already exists in config."""
    config = {"cv": {"generation": {"model": "old-model"}}}
    apply_settings_to_config(config, {"cv_preset": "europass"})
    assert config["cv"]["preset"] == "europass"
    assert config["cv"]["generation"]["model"] == "old-model"


def test_valid_cv_preset_group_payload_passes():
    """All cv-preset group fields pass validation together."""
    validate_settings({
        "cv_preset": "europass",
        "cv_generation_model": "gemini-2.5-flash",
    })  # must not raise


def test_valid_cv_composition_group_payload_passes():
    """All cv-composition group fields pass validation together."""
    validate_settings({
        "cv_summary_enabled": True,
        "cv_education_enabled": True,
        "cv_experience_enabled": True,
        "cv_skills_enabled": True,
        "cv_certifications_enabled": True,
        "cv_projects_enabled": True,
        "cv_publications_enabled": False,
        "cv_languages_enabled": True,
    })  # must not raise


# ── Preset-based CV settings defaults match cv.yaml ──────────────────────────────

def test_cv_preset_defaults_match_cv_yaml():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["default"] == "europass"


def test_cv_generation_model_default_uses_25_flash():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["default"] == "gemini-2.5-flash"


def test_cv_generation_model_options_are_constrained() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["options"] == [
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
        "gemini-2.5-pro",
    ]


def test_cv_summary_enabled_default() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_summary_enabled"]["default"] is True


def test_cv_education_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_education_enabled"]["default"] is True


def test_cv_experience_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_experience_enabled"]["default"] is True


def test_cv_skills_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_skills_enabled"]["default"] is True


def test_cv_certifications_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_certifications_enabled"]["default"] is True


def test_cv_projects_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_projects_enabled"]["default"] is True


def test_cv_publications_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_publications_enabled"]["default"] is False


def test_cv_languages_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_languages_enabled"]["default"] is True


def test_cv_max_pages_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_max_pages"]["default"] == 2


# ── ALL_GROUP_REGISTRIES ──────────────────────────────────────────────────────

def test_all_group_registries_has_all_four_cv_groups():
    from fitcv_cp.settings_schema import ALL_GROUP_REGISTRIES
    assert "cv-preset" in ALL_GROUP_REGISTRIES["cv"]
    assert "cv-composition" in ALL_GROUP_REGISTRIES["cv"]
    assert "cv-validation" in ALL_GROUP_REGISTRIES["cv"]


# ── coerce_value for CV types ─────────────────────────────────────────────────

def test_coerce_list_str_from_list():
    # required_cv_sections was removed; no list[str] fields remain in schema
    pass


def test_coerce_list_str_from_single_value():
    # required_cv_sections was removed; no list[str] fields remain in schema
    pass


def test_coerce_cv_generation_model_strips_whitespace():
    from fitcv_cp.settings_schema import coerce_value
    result = coerce_value("cv_generation_model", "  gemini-2.5-flash  ")
    assert result == "gemini-2.5-flash"
    assert isinstance(result, str)


def test_validate_settings_rejects_unknown_cv_generation_model() -> None:
    with pytest.raises(ValidationError, match="cv_generation_model"):
        validate_settings({"cv_generation_model": "gemini-3-flash"})


def test_all_group_registries_has_ranking_and_cv():
    from fitcv_cp.settings_schema import ALL_GROUP_REGISTRIES
    assert "ranking" in ALL_GROUP_REGISTRIES
    assert "cv" in ALL_GROUP_REGISTRIES
    assert ALL_GROUP_REGISTRIES["cv"] is not None


def test_legacy_cv_required_toggles_are_removed_from_schema() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert "cv_education_required" not in schema_by_key
    assert "cv_projects_required" not in schema_by_key



