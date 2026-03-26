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
