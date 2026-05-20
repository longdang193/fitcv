"""
@meta
type: test
scope: unit
domain: ranking
covers:
  - ranking contract invariants
  - fit-label symmetry between pipeline and ranking contract
tags:
  - fast
  - ci-safe
"""

import pytest

from fitcv.pipeline import _resolve_layer4_fit
from fitcv.ranking_contract import (
    fit_label_from_score,
    get_fit_label_thresholds,
    validate_missing_defaults_contract,
    validate_weight_contract,
)


def test_get_fit_label_thresholds_rejects_inverted_values() -> None:
    with pytest.raises(ValueError, match="Invalid fit_label_thresholds"):
        get_fit_label_thresholds({"fit_label_thresholds": {"strong": 0.3, "stretch": 0.6}})


def test_validate_weight_contract_rejects_invalid_sum() -> None:
    with pytest.raises(ValueError, match="Invalid ranking weights sum"):
        validate_weight_contract({"ai_score": 0.6, "must_have_match": 0.3}, expected_sum=1.0)


def test_validate_missing_defaults_contract_rejects_missing_keys() -> None:
    with pytest.raises(ValueError, match="Missing defaults for ranking features"):
        validate_missing_defaults_contract(
            {"ai_score": 0.0},
            supported_features=("ai_score", "must_have_match"),
        )


@pytest.mark.parametrize(
    ("score", "expected_label"),
    [
        (0.9, "strong"),
        (0.5, "stretch"),
        (0.1, "skip"),
    ],
)
def test_pipeline_layer4_fit_matches_contract(score: float, expected_label: str) -> None:
    config = {"fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}}
    job = {"ai_score": score}
    assert _resolve_layer4_fit(job, gap_fit=None, config=config) == expected_label
    assert fit_label_from_score(score, config=config) == expected_label
