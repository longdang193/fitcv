from fitcv.pipeline_stages.common import pipeline_int
from fitcv.config import get_cv_renderer_strategy


def test_pipeline_int_returns_default_when_pipeline_block_missing() -> None:
    assert pipeline_int({}, "vector_search_top_n", default=7) == 7


def test_pipeline_int_coerces_int_values() -> None:
    assert pipeline_int({"pipeline": {"final_top_n": "10"}}, "final_top_n", default=0) == 10


def test_pipeline_int_returns_default_on_invalid_values() -> None:
    assert pipeline_int({"pipeline": {"ai_score_top_n": "nope"}}, "ai_score_top_n", default=5) == 5


def test_cv_renderer_strategy_is_nested_and_defaults_to_europass() -> None:
    assert get_cv_renderer_strategy({}) == "europass"
    assert get_cv_renderer_strategy({"cv": {"preset": "europass"}}) == "europass"
    assert get_cv_renderer_strategy({"cv": {"renderer": {"strategy": "mycvs_v1"}}}) == "mycvs_v1"
