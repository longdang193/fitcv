"""Parity tests for shared normalization behavior across candidate/ranking/evidence."""

from fitcv import candidate as candidate_module
from fitcv import evidence as evidence_module
from fitcv import ranking as ranking_module


def test_normalize_text_parity_candidate_vs_ranking() -> None:
    raw = "  Senior-Data/Engineer (ML)  "
    assert candidate_module._normalize_text(raw) == ranking_module._normalize_text(raw)


def test_evidence_canonicalize_terms_matches_normalize_text_semantics() -> None:
    raw_values = [" Data Engineering ", "data-engineering", "DATA_engineering", "", " "]
    candidate_normalized = sorted(
        {
            candidate_module._normalize_text(value)
            for value in raw_values
            if candidate_module._normalize_text(value)
        }
    )
    evidence_normalized = sorted(evidence_module._canonicalize_terms(raw_values))
    assert evidence_normalized == candidate_normalized
