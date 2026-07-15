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
    validate_weight_contract,
)


def test_fit_label_from_score_rejects_inverted_values() -> None:
    with pytest.raises(ValueError, match="ranking_policy.fit_label_thresholds"):
        fit_label_from_score(
            0.5,
            {"ranking_policy": {"fit_label_thresholds": {"strong": 0.3, "stretch": 0.6}}},
        )


def test_validate_weight_contract_rejects_invalid_sum() -> None:
    with pytest.raises(ValueError, match="Invalid ranking weights sum"):
        validate_weight_contract({"ai_score": 0.6, "must_have_match": 0.3}, expected_sum=1.0)



@pytest.mark.parametrize(
    ("score", "expected_label"),
    [
        (0.9, "strong"),
        (0.5, "stretch"),
        (0.1, "skip"),
    ],
)
def test_pipeline_layer4_fit_matches_contract(score: float, expected_label: str) -> None:
    config = {"ranking_policy": {"fit_label_thresholds": {"strong": 0.7, "stretch": 0.4}}}
    job = {"baseline_fit": score}
    assert _resolve_layer4_fit(job, gap_fit=None, config=config) == expected_label
    assert fit_label_from_score(score, config=config) == expected_label

