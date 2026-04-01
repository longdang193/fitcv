import pytest
from fitcv_cp.settings_schema import (
    SETTINGS_SCHEMA,
    apply_settings_to_config,
    validate_settings,
    ValidationError,
)


# ── schema registry ───────────────────────────────────────────────────────────

def test_all_expected_keys_present():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "pipeline.final_top_n" in keys
    assert "ranking_weights.ai_score" in keys
    assert "fit_label_thresholds.strong" in keys
    assert "gap_thresholds.strong_min_matched_ratio" in keys
    # excluded key — internal fallback only, not admin-editable
    assert "rerank_top_n" not in keys


def test_schema_has_required_fields():
    for entry in SETTINGS_SCHEMA:
        assert "key" in entry
        assert "type" in entry       # "int" or "float"
        assert "default" in entry
        assert "label" in entry
        assert "description" in entry
        assert "group" in entry      # "retrieval" | "timing" | "ranking"


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
    with pytest.raises(ValidationError, match="ranking_weights"):
        validate_settings({
            "ranking_weights.ai_score": 0.90,
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


# ── RANKING_GROUPS registry ───────────────────────────────────────────────────

def test_ranking_groups_has_three_slugs():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    assert set(RANKING_GROUPS.keys()) == {"ranking-weights", "fit-label-thresholds", "gap-thresholds"}


def test_ranking_groups_all_keys_in_schema():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    schema_keys = {s["key"] for s in SETTINGS_SCHEMA}
    for slug, keys in RANKING_GROUPS.items():
        for key in keys:
            assert key in schema_keys, f"{key!r} from group {slug!r} not found in SETTINGS_SCHEMA"


def test_ranking_weights_group_has_six_keys():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    assert len(RANKING_GROUPS["ranking-weights"]) == 6


def test_ranking_weight_copy_matches_runtime_semantics():
    schema_by_key = {entry["key"]: entry for entry in SETTINGS_SCHEMA}
    assert schema_by_key["ranking_weights.title_relevance"]["description"] == (
        "How much influence the similarity between the job title and the candidate's target role has on the final ranking."
    )
    assert schema_by_key["ranking_weights.preference_fit"]["label"] == "Weight: Preference Alignment"
    assert schema_by_key["ranking_weights.preference_fit"]["description"] == (
        "How much influence candidate preference alignment such as domain and location type has on the final candidate ranking."
    )


def test_ranking_groups_threshold_groups_have_two_keys_each():
    from fitcv_cp.settings_schema import RANKING_GROUPS
    assert len(RANKING_GROUPS["fit-label-thresholds"]) == 2
    assert len(RANKING_GROUPS["gap-thresholds"]) == 2


# ── SETTINGS_SECTIONS registry ────────────────────────────────────────────────

def test_settings_sections_has_expected_slugs():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    assert set(SETTINGS_SECTIONS.keys()) == {"retrieval", "timing", "global-job-filters"}


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


def test_settings_sections_retrieval_has_four_keys():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    assert len(SETTINGS_SECTIONS["retrieval"]) == 4


def test_settings_sections_global_job_filters_has_two_keys():
    from fitcv_cp.settings_schema import SETTINGS_SECTIONS
    assert len(SETTINGS_SECTIONS["global-job-filters"]) == 2


# ── enrichment parallelism settings ───────────────────────────────────────────

def test_enrichment_parallelism_keys_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "enrichment_batch_size" in keys
    assert "enrichment_concurrency" in keys


def test_enrichment_parallelism_defaults():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["enrichment_batch_size"]["default"] == 10
    assert schema_by_key["enrichment_concurrency"]["default"] == 1


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
    config: dict = {}
    apply_settings_to_config(config, {"enrichment_batch_size": 5})
    assert config["enrichment_batch_size"] == 5


def test_enrichment_concurrency_apply_writes_correct_path():
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
    assert "cv_template_path" in keys  # kept for backward compat; not in UI
    assert "cv_prompt_version" in keys
    assert "cv_max_pages" in keys


def test_cv_settings_have_correct_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    # preset and composition fields are in new groups
    assert schema_by_key["cv_preset"]["group"] == "cv_preset"
    assert schema_by_key["cv_generation_model"]["group"] == "cv_composition"
    assert schema_by_key["cv_prompt_version"]["group"] == "cv_composition"
    assert schema_by_key["cv_summary_style"]["group"] == "cv_composition"
    assert schema_by_key["cv_max_pages"]["group"] == "cv_validation"
    # kept for backward compat
    assert schema_by_key["cv_template_path"]["group"] == "cv_generation"


def test_cv_settings_defaults():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["default"] == "europass"
    assert schema_by_key["cv_generation_model"]["default"] == "gemini-2.5-flash"
    assert schema_by_key["cv_prompt_version"]["default"] == "v1"
    assert schema_by_key["cv_template_path"]["default"] == "templates/cv_template.md"
    assert schema_by_key["cv_max_pages"]["default"] == 2


def test_cv_settings_types():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_preset"]["type"] == "str"
    assert schema_by_key["cv_generation_model"]["type"] == "str"
    assert schema_by_key["cv_template_path"]["type"] == "str"
    assert schema_by_key["cv_prompt_version"]["type"] == "str"
    assert schema_by_key["cv_max_pages"]["type"] == "int"
    assert schema_by_key["cv_summary_style"]["type"] == "str"
    assert schema_by_key["cv_education_enabled"]["type"] == "bool"
    assert schema_by_key["cv_education_detail"]["type"] == "str"
    assert schema_by_key["cv_experience_enabled"]["type"] == "bool"
    assert schema_by_key["cv_experience_bullet_style"]["type"] == "str"
    assert schema_by_key["cv_skills_enabled"]["type"] == "bool"
    assert schema_by_key["cv_skills_max_items"]["type"] == "int"
    assert schema_by_key["cv_certifications_enabled"]["type"] == "bool"
    assert schema_by_key["cv_projects_enabled"]["type"] == "bool"
    assert schema_by_key["cv_emphasize_required_skills"]["type"] == "bool"
    assert schema_by_key["cv_align_jd_terminology"]["type"] == "bool"
    assert schema_by_key["cv_evidence_grounded_only"]["type"] == "bool"


def test_pipeline_evidence_top_k_not_in_cv_group():
    """evidence_top_k stays in retrieval, not in the CV section."""
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["pipeline.evidence_top_k"]["group"] != "cv_generation"


def test_cv_generation_keys_in_cv_groups():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv_preset" in CV_GROUPS["cv-preset"]
    assert "cv_generation_model" in CV_GROUPS["cv-preset"]
    assert "cv_prompt_version" in CV_GROUPS["cv-preset"]


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
    assert "cv_prompt_version" in keys


def test_cv_generation_model_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["type"] == "str"


def test_cv_prompt_version_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_prompt_version"]["type"] == "str"


def test_cv_generation_model_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["group"] == "cv_composition"


def test_cv_prompt_version_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_prompt_version"]["group"] == "cv_composition"


# ── Composition fields ───────────────────────────────────────────────────────────

def test_cv_composition_fields_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    # Summary
    assert "cv_summary_style" in keys
    # Education
    assert "cv_education_enabled" in keys
    assert "cv_education_detail" in keys
    # Experience
    assert "cv_experience_enabled" in keys
    assert "cv_experience_bullet_style" in keys
    # Skills
    assert "cv_skills_enabled" in keys
    assert "cv_skills_max_items" in keys
    # Certifications
    assert "cv_certifications_enabled" in keys
    # Projects
    assert "cv_projects_enabled" in keys
    # Publications
    assert "cv_publications_enabled" in keys
    assert "cv_publications_detail" in keys
    # Languages
    assert "cv_languages_enabled" in keys
    assert "cv_languages_detail" in keys
    assert "cv_education_required" not in keys
    assert "cv_projects_required" not in keys


def test_cv_summary_style_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_summary_style"]["type"] == "str"


def test_cv_education_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_education_enabled"]["type"] == "bool"


def test_cv_education_detail_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_education_detail"]["type"] == "str"


def test_cv_experience_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_experience_enabled"]["type"] == "bool"


def test_cv_experience_bullet_style_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_experience_bullet_style"]["type"] == "str"


def test_cv_skills_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_skills_enabled"]["type"] == "bool"


def test_cv_skills_max_items_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_skills_max_items"]["type"] == "int"


def test_cv_certifications_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_certifications_enabled"]["type"] == "bool"


def test_cv_projects_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_projects_enabled"]["type"] == "bool"


def test_cv_publications_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_publications_enabled"]["type"] == "bool"


def test_cv_publications_detail_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_publications_detail"]["type"] == "str"


def test_cv_languages_enabled_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_languages_enabled"]["type"] == "bool"


def test_cv_languages_detail_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_languages_detail"]["type"] == "str"


def test_cv_composition_fields_have_correct_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    for key in ("cv_summary_style", "cv_education_enabled", "cv_education_detail",
                "cv_experience_enabled", "cv_experience_bullet_style",
                "cv_skills_enabled", "cv_skills_max_items",
                "cv_certifications_enabled", "cv_projects_enabled",
                "cv_publications_enabled", "cv_publications_detail",
                "cv_languages_enabled", "cv_languages_detail"):
        assert schema_by_key[key]["group"] == "cv_composition", f"{key} should be in cv_composition group"


# ── Content rules fields ────────────────────────────────────────────────────────

def test_cv_content_rules_fields_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_emphasize_required_skills" in keys
    assert "cv_align_jd_terminology" in keys
    assert "cv_evidence_grounded_only" in keys


def test_cv_emphasize_required_skills_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_emphasize_required_skills"]["type"] == "bool"


def test_cv_align_jd_terminology_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_align_jd_terminology"]["type"] == "bool"


def test_cv_evidence_grounded_only_type():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_evidence_grounded_only"]["type"] == "bool"


def test_cv_content_rules_have_correct_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    for key in ("cv_emphasize_required_skills", "cv_align_jd_terminology", "cv_evidence_grounded_only"):
        assert schema_by_key[key]["group"] == "cv_content_rules", f"{key} should be in cv_content_rules group"


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

def test_cv_groups_has_all_four_subgroups():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv-preset" in CV_GROUPS
    assert "cv-composition" in CV_GROUPS
    assert "cv-content-rules" in CV_GROUPS
    assert "cv-validation" in CV_GROUPS


def test_cv_groups_preset_has_correct_keys():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv_preset" in CV_GROUPS["cv-preset"]
    assert "cv_generation_model" in CV_GROUPS["cv-preset"]
    assert "cv_prompt_version" in CV_GROUPS["cv-preset"]


def test_cv_groups_composition_has_all_composition_keys():
    from fitcv_cp.settings_schema import CV_GROUPS
    expected = {
        "cv_summary_enabled",
        "cv_summary_style", "cv_education_enabled", "cv_education_detail",
        "cv_experience_enabled", "cv_experience_bullet_style",
        "cv_skills_enabled", "cv_skills_max_items",
        "cv_certifications_enabled", "cv_projects_enabled",
        "cv_publications_enabled", "cv_publications_detail",
        "cv_languages_enabled", "cv_languages_detail",
    }
    assert set(CV_GROUPS["cv-composition"]) == expected


def test_cv_groups_content_rules_has_all_content_rule_keys():
    from fitcv_cp.settings_schema import CV_GROUPS
    expected = {
        "cv_emphasize_required_skills", "cv_align_jd_terminology", "cv_evidence_grounded_only",
    }
    assert set(CV_GROUPS["cv-content-rules"]) == expected


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


def test_cv_summary_style_rejects_empty():
    with pytest.raises(ValidationError, match="cv_summary_style"):
        validate_settings({"cv_summary_style": ""})


def test_cv_education_detail_rejects_empty():
    with pytest.raises(ValidationError, match="cv_education_detail"):
        validate_settings({"cv_education_detail": ""})


def test_cv_experience_bullet_style_rejects_empty():
    with pytest.raises(ValidationError, match="cv_experience_bullet_style"):
        validate_settings({"cv_experience_bullet_style": ""})


def test_cv_skills_max_items_rejects_zero():
    with pytest.raises(ValidationError):
        validate_settings({"cv_skills_max_items": 0})


def test_cv_skills_max_items_rejects_negative():
    with pytest.raises(ValidationError):
        validate_settings({"cv_skills_max_items": -1})


def test_cv_skills_max_items_accepts_positive():
    validate_settings({"cv_skills_max_items": 15})  # must not raise


# ── apply_settings_to_config for new CV fields ──────────────────────────────────

def test_apply_settings_to_config_cv_preset():
    config: dict = {}
    apply_settings_to_config(config, {"cv_preset": "europass"})
    assert config["cv"]["preset"] == "europass"


def test_apply_settings_to_config_cv_composition_nested():
    config: dict = {}
    apply_settings_to_config(config, {
        "cv_summary_style": "achievement_focused",
        "cv_education_enabled": True,
        "cv_skills_max_items": 10,
    })
    assert config["cv"]["composition"]["summary"]["style"] == "achievement_focused"
    assert config["cv"]["composition"]["education"]["enabled"] is True
    assert config["cv"]["composition"]["skills"]["max_items"] == 10


def test_apply_settings_to_config_cv_content_rules_nested():
    config: dict = {}
    apply_settings_to_config(config, {
        "cv_emphasize_required_skills": True,
        "cv_align_jd_terminology": False,
    })
    assert config["cv"]["content_rules"]["emphasize_required_skills"] is True
    assert config["cv"]["content_rules"]["align_jd_terminology"] is False


def test_apply_settings_to_config_cv_validation_nested():
    config: dict = {}
    apply_settings_to_config(config, {"cv_max_pages": 3})
    assert config["cv"]["validation"]["max_pages"] == 3


def test_apply_settings_to_config_cv_generation_nested():
    config: dict = {}
    apply_settings_to_config(config, {
        "cv_generation_model": "gemini-2.5-flash",
        "cv_prompt_version": "v2",
    })
    assert config["cv"]["generation"]["model"] == "gemini-2.5-flash"
    assert config["cv"]["generation"]["prompt_version"] == "v2"


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
        "cv_prompt_version": "v1",
    })  # must not raise


def test_valid_cv_composition_group_payload_passes():
    """All cv-composition group fields pass validation together."""
    validate_settings({
        "cv_summary_style": "concise",
        "cv_education_enabled": True,
        "cv_education_detail": "standard",
        "cv_experience_enabled": True,
        "cv_experience_bullet_style": "action_project_result",
        "cv_skills_enabled": True,
        "cv_skills_max_items": 12,
        "cv_certifications_enabled": True,
        "cv_projects_enabled": True,
        "cv_publications_enabled": False,
        "cv_publications_detail": "compact",
        "cv_languages_enabled": True,
        "cv_languages_detail": "compact",
    })  # must not raise


def test_valid_cv_content_rules_group_payload_passes():
    """All cv-content-rules group fields pass validation together."""
    validate_settings({
        "cv_emphasize_required_skills": True,
        "cv_align_jd_terminology": True,
        "cv_evidence_grounded_only": False,
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


def test_cv_prompt_version_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_prompt_version"]["default"] == "v1"


def test_cv_summary_enabled_default() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_summary_enabled"]["default"] is True


def test_cv_summary_style_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_summary_style"]["default"] == "concise"


def test_cv_education_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_education_enabled"]["default"] is True


def test_cv_education_detail_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_education_detail"]["default"] == "compact"


def test_cv_experience_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_experience_enabled"]["default"] is True


def test_cv_experience_bullet_style_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_experience_bullet_style"]["default"] == "action_project_result"


def test_cv_skills_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_skills_enabled"]["default"] is True


def test_cv_skills_max_items_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_skills_max_items"]["default"] == 12


def test_cv_certifications_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_certifications_enabled"]["default"] is True


def test_cv_projects_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_projects_enabled"]["default"] is True


def test_cv_publications_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_publications_enabled"]["default"] is False


def test_cv_publications_detail_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_publications_detail"]["default"] == "compact"


def test_cv_languages_enabled_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_languages_enabled"]["default"] is True


def test_cv_languages_detail_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_languages_detail"]["default"] == "compact"


def test_cv_emphasize_required_skills_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_emphasize_required_skills"]["default"] is True


def test_cv_align_jd_terminology_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_align_jd_terminology"]["default"] is True


def test_cv_evidence_grounded_only_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_evidence_grounded_only"]["default"] is True


def test_cv_max_pages_default():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_max_pages"]["default"] == 2


# ── coerce for new types ─────────────────────────────────────────────────────────

def test_coerce_int_from_string_new_field():
    from fitcv_cp.settings_schema import coerce_value
    result = coerce_value("cv_skills_max_items", "15")
    assert result == 15
    assert isinstance(result, int)


# ── ALL_GROUP_REGISTRIES ──────────────────────────────────────────────────────

def test_all_group_registries_has_all_four_cv_groups():
    from fitcv_cp.settings_schema import ALL_GROUP_REGISTRIES
    assert "cv-preset" in ALL_GROUP_REGISTRIES["cv"]
    assert "cv-composition" in ALL_GROUP_REGISTRIES["cv"]
    assert "cv-content-rules" in ALL_GROUP_REGISTRIES["cv"]
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


# ── validate_settings for CV fields ───────────────────────────────────────────

# required_cv_sections was removed; sections are now controlled by cv_*_enabled fields

def test_cv_preset_rejects_empty():
    with pytest.raises(ValidationError, match="cv_preset"):
        validate_settings({"cv_preset": ""})


def test_cv_preset_rejects_whitespace_only():
    with pytest.raises(ValidationError, match="cv_preset"):
        validate_settings({"cv_preset": "   "})


def test_cv_summary_style_rejects_empty():
    with pytest.raises(ValidationError, match="cv_summary_style"):
        validate_settings({"cv_summary_style": ""})


def test_cv_education_detail_rejects_empty():
    with pytest.raises(ValidationError, match="cv_education_detail"):
        validate_settings({"cv_education_detail": ""})


def test_cv_experience_bullet_style_rejects_empty():
    with pytest.raises(ValidationError, match="cv_experience_bullet_style"):
        validate_settings({"cv_experience_bullet_style": ""})


def test_cv_skills_max_items_rejects_zero():
    with pytest.raises(ValidationError):
        validate_settings({"cv_skills_max_items": 0})


def test_cv_skills_max_items_rejects_negative():
    with pytest.raises(ValidationError):
        validate_settings({"cv_skills_max_items": -1})


def test_cv_skills_max_items_accepts_positive():
    validate_settings({"cv_skills_max_items": 15})  # must not raise


# required_cv_sections replaced by cv_*_enabled fields; old tests removed


# ── apply_settings_to_config for CV fields ───────────────────────────────────

def test_apply_settings_to_config_cv_preset_nested():
    """cv_generation_model and cv_prompt_version write to cv.generation.* nested path."""
    config: dict = {}
    apply_settings_to_config(config, {
        "cv_generation_model": "gemini-2.5-flash",
        "cv_prompt_version": "v2",
    })
    assert config["cv"]["generation"]["model"] == "gemini-2.5-flash"
    assert config["cv"]["generation"]["prompt_version"] == "v2"


def test_apply_settings_to_config_cv_summary_enabled_nested() -> None:
    config: dict = {}
    apply_settings_to_config(config, {"cv_summary_enabled": False})
    assert config["cv"]["composition"]["summary"]["enabled"] is False


def test_apply_settings_to_config_cv_list_removed():
    # required_cv_sections was removed; no list[str] fields remain in schema
    pass


def test_apply_settings_to_config_cv_int():
    config: dict = {}
    apply_settings_to_config(config, {"cv_max_pages": 3})
    assert config["cv"]["validation"]["max_pages"] == 3


# ── ALL_GROUP_REGISTRIES ──────────────────────────────────────────────────────

def test_all_group_registries_has_ranking_and_cv():
    from fitcv_cp.settings_schema import ALL_GROUP_REGISTRIES
    assert "ranking" in ALL_GROUP_REGISTRIES
    assert "cv" in ALL_GROUP_REGISTRIES
    assert ALL_GROUP_REGISTRIES["cv"] is not None


def test_legacy_cv_required_toggles_are_removed_from_schema() -> None:
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert "cv_education_required" not in schema_by_key
    assert "cv_projects_required" not in schema_by_key
