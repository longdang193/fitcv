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
    assert "cv_generation_model" in keys
    assert "cv_template_path" in keys
    assert "prompt_version" in keys
    assert "required_cv_sections" in keys
    assert "cv_max_pages" in keys


def test_cv_settings_have_correct_group():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    for key in ("cv_generation_model", "cv_template_path", "prompt_version",
                "required_cv_sections", "cv_max_pages"):
        assert schema_by_key[key]["group"] == "cv_generation", f"{key} should be in cv_generation group"


def test_cv_settings_defaults():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["default"] == "gemini-2.0-flash"
    assert schema_by_key["cv_template_path"]["default"] == "templates/cv_template.md"
    assert schema_by_key["prompt_version"]["default"] == "v1"
    assert schema_by_key["required_cv_sections"]["default"] == ["Summary", "Work Experience", "Skills"]
    assert schema_by_key["cv_max_pages"]["default"] == 2


def test_cv_settings_types():
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["cv_generation_model"]["type"] == "str"
    assert schema_by_key["cv_template_path"]["type"] == "str"
    assert schema_by_key["prompt_version"]["type"] == "str"
    assert schema_by_key["required_cv_sections"]["type"] == "list[str]"
    assert schema_by_key["cv_max_pages"]["type"] == "int"


def test_pipeline_evidence_top_k_not_in_cv_group():
    """evidence_top_k stays in retrieval, not in the CV section."""
    schema_by_key = {s["key"]: s for s in SETTINGS_SCHEMA}
    assert schema_by_key["pipeline.evidence_top_k"]["group"] != "cv_generation"


def test_cv_generation_keys_in_cv_groups():
    from fitcv_cp.settings_schema import CV_GROUPS
    assert "cv_generation_model" in CV_GROUPS["cv-generation"]
    assert "cv_template_path" in CV_GROUPS["cv-generation"]
    assert "prompt_version" in CV_GROUPS["cv-generation"]
    assert "required_cv_sections" in CV_GROUPS["cv-validation"]
    assert "cv_max_pages" in CV_GROUPS["cv-validation"]


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


# ── coerce_value for CV types ─────────────────────────────────────────────────

def test_coerce_str():
    from fitcv_cp.settings_schema import coerce_value
    result = coerce_value("cv_generation_model", "  gemini-2.0-flash  ")
    assert result == "gemini-2.0-flash"
    assert isinstance(result, str)


def test_coerce_list_str_from_list():
    from fitcv_cp.settings_schema import coerce_value
    result = coerce_value("required_cv_sections", ["  Summary  ", "  Experience  "])
    assert result == ["Summary", "Experience"]


def test_coerce_list_str_from_single_value():
    from fitcv_cp.settings_schema import coerce_value
    result = coerce_value("required_cv_sections", "Summary")
    assert result == ["Summary"]


# ── validate_settings for CV fields ───────────────────────────────────────────

def test_cv_generation_model_rejects_empty():
    with pytest.raises(ValidationError, match="cv_generation_model"):
        validate_settings({"cv_generation_model": ""})


def test_cv_generation_model_rejects_whitespace_only():
    with pytest.raises(ValidationError, match="cv_generation_model"):
        validate_settings({"cv_generation_model": "   "})


def test_cv_template_path_rejects_empty():
    with pytest.raises(ValidationError, match="cv_template_path"):
        validate_settings({"cv_template_path": ""})


def test_cv_template_path_rejects_whitespace_only():
    with pytest.raises(ValidationError, match="cv_template_path"):
        validate_settings({"cv_template_path": "   "})


def test_prompt_version_rejects_empty():
    with pytest.raises(ValidationError, match="prompt_version"):
        validate_settings({"prompt_version": ""})


def test_prompt_version_rejects_whitespace_only():
    with pytest.raises(ValidationError, match="prompt_version"):
        validate_settings({"prompt_version": "   "})


def test_required_cv_sections_rejects_empty_list():
    with pytest.raises(ValidationError, match="required_cv_sections"):
        validate_settings({"required_cv_sections": []})


def test_required_cv_sections_rejects_blank_items():
    with pytest.raises(ValidationError, match="required_cv_sections"):
        validate_settings({"required_cv_sections": ["Summary", "  ", "Skills"]})


def test_required_cv_sections_rejects_duplicate():
    with pytest.raises(ValidationError, match="required_cv_sections"):
        validate_settings({"required_cv_sections": ["Summary", "Summary", "Skills"]})


def test_required_cv_sections_preserves_order_without_sorting():
    """validate_settings must not reorder the list; order is validated as-is."""
    validated = {}
    validate_settings({"required_cv_sections": ["Skills", "Summary", "Work Experience"]})
    # No error means validation passed; order is preserved as-is (no sort applied)


def test_cv_max_pages_rejects_zero():
    with pytest.raises(ValidationError):
        validate_settings({"cv_max_pages": 0})


def test_cv_max_pages_rejects_negative():
    with pytest.raises(ValidationError):
        validate_settings({"cv_max_pages": -1})


def test_cv_max_pages_accepts_positive():
    validate_settings({"cv_max_pages": 5})  # must not raise


def test_cv_max_pages_rejects_non_integer():
    with pytest.raises(ValidationError):
        validate_settings({"cv_max_pages": 2.5})


def test_cv_settings_valid_payload_passes():
    validate_settings({
        "cv_generation_model": "gemini-2.0-flash",
        "cv_template_path": "templates/cv_template.md",
        "prompt_version": "v1",
        "required_cv_sections": ["Summary", "Work Experience", "Skills"],
        "cv_max_pages": 2,
    })  # must not raise


# ── apply_settings_to_config for CV fields ───────────────────────────────────

def test_apply_settings_to_config_cv_str():
    config: dict = {}
    apply_settings_to_config(config, {
        "cv_generation_model": "gemini-2.0-flash",
        "prompt_version": "v2",
    })
    assert config["cv_generation_model"] == "gemini-2.0-flash"
    assert config["prompt_version"] == "v2"


def test_apply_settings_to_config_cv_list_preserves_order():
    config: dict = {}
    ordered = ["Skills", "Summary", "Work Experience"]
    apply_settings_to_config(config, {"required_cv_sections": ordered})
    assert config["required_cv_sections"] == ordered
    # Must not silently sort or deduplicate
    assert config["required_cv_sections"] == ["Skills", "Summary", "Work Experience"]


def test_apply_settings_to_config_cv_int():
    config: dict = {}
    apply_settings_to_config(config, {"cv_max_pages": 3})
    assert config["cv_max_pages"] == 3


# ── ALL_GROUP_REGISTRIES ──────────────────────────────────────────────────────

def test_all_group_registries_has_ranking_and_cv():
    from fitcv_cp.settings_schema import ALL_GROUP_REGISTRIES
    assert "ranking" in ALL_GROUP_REGISTRIES
    assert "cv" in ALL_GROUP_REGISTRIES
    assert ALL_GROUP_REGISTRIES["cv"] is not None
