from fitcv.pipeline_stages.common import pipeline_int


def test_pipeline_int_returns_default_when_pipeline_block_missing() -> None:
    assert pipeline_int({}, "vector_search_top_n", default=7) == 7


def test_pipeline_int_coerces_int_values() -> None:
    assert pipeline_int({"pipeline": {"final_top_n": "10"}}, "final_top_n", default=0) == 10


def test_pipeline_int_returns_default_on_invalid_values() -> None:
    assert pipeline_int({"pipeline": {"ai_score_top_n": "nope"}}, "ai_score_top_n", default=5) == 5
