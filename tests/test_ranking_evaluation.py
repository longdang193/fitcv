"""Deterministic ranking gold-set evaluation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from fitcv.ranking import rank_jobs

FIXTURE = Path(__file__).parent / "fixtures" / "ranking_gold.json"
PROFILE_NAMES = {"backend", "frontend", "data", "product"}
REVIEWED_CASES = {
    "direct_match",
    "paraphrase",
    "missing_requirement",
    "language_conflict",
    "location_conflict",
    "clear_mismatch",
}


def _gold() -> dict[str, Any]:
    data = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert set(data["profiles"]) == PROFILE_NAMES
    return data


def _ranked(rows: list[dict[str, Any]], score_key: str, top_n: int) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -(float(row[score_key]) if row[score_key] is not None else float("-inf")),
            row["candidate_id"],
        ),
    )[:top_n]


def _recall(rows: list[dict[str, Any]], score_key: str, top_n: int) -> float:
    relevant = {row["candidate_id"] for row in rows if row["relevance_grade"] > 0}
    retrieved = {row["candidate_id"] for row in _ranked(rows, score_key, top_n)}
    return len(relevant & retrieved) / len(relevant) if relevant else 1.0


def _ndcg(rows: list[dict[str, Any]], score_key: str, top_n: int) -> float:
    ranked = _ranked(rows, score_key, top_n)
    dcg = sum(
        (2**row["relevance_grade"] - 1) / math.log2(index + 2)
        for index, row in enumerate(ranked)
    )
    ideal = sorted((row["relevance_grade"] for row in rows), reverse=True)[:top_n]
    idcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal))
    return dcg / idcg if idcg else 1.0


def test_fixture_shape_and_reviewed_cases() -> None:
    data = _gold()
    assert sum(len(pool["candidates"]) for pool in data["profiles"].values()) == 240
    for profile_name, pool in data["profiles"].items():
        rows = pool["candidates"]
        assert pool["profile_id"] == profile_name
        assert len(rows) == 60
        assert sum(row["split"] == "calibration" for row in rows) == 48
        assert sum(row["split"] == "held_out" for row in rows) == 12
        assert {row["relevance_grade"] for row in rows} == {0, 1, 2, 3}
        assert {row["description"] for row in rows} >= REVIEWED_CASES
        assert all(row["reviewed"] is True for row in rows)


def test_recall_at_50() -> None:
    for pool in _gold()["profiles"].values():
        assert _recall(pool["candidates"], "baseline_fit", 50) == 1.0


def test_recall_at_ai_score_top_n() -> None:
    top_n = _gold()["evaluation"]["cutoffs"]["ai_score_top_n"]
    for pool in _gold()["profiles"].values():
        assert _recall(pool["candidates"], "ai_score", top_n) == 1.0


def test_ndcg_at_15() -> None:
    top_n = _gold()["evaluation"]["cutoffs"]["ndcg_at_15"]
    for pool in _gold()["profiles"].values():
        assert _ndcg(pool["candidates"], "baseline_fit", top_n) > 0.99


def test_false_rejection_rate_is_zero() -> None:
    for pool in _gold()["profiles"].values():
        rows = pool["candidates"]
        relevant = {row["candidate_id"] for row in rows if row["relevance_grade"] > 0}
        retrieved = {row["candidate_id"] for row in _ranked(rows, "baseline_fit", 50)}
        assert not relevant - retrieved


def test_valid_zero_score_is_distinct_from_unscored() -> None:
    for pool in _gold()["profiles"].values():
        rows = pool["candidates"]
        valid_zero = [row for row in rows if row["baseline_fit"] == 0.0 and row["ai_score"] == 0.0]
        unscored = [row for row in rows if row["ai_score"] is None]
        assert valid_zero and unscored
        assert all(row["ai_score_status"] == "valid" for row in valid_zero)
        assert all(row["ai_score_status"] == "unscored" for row in unscored)


def test_unscored_ai_rows_sort_after_scored_rows() -> None:
    rows = _gold()["profiles"]["backend"]["candidates"]
    ranked = _ranked(rows, "ai_score", len(rows))
    first_unscored = next(index for index, row in enumerate(ranked) if row["ai_score"] is None)
    assert all(row["ai_score"] is not None for row in ranked[:first_unscored])
    assert all(row["ai_score"] is None for row in ranked[first_unscored:])


def test_deterministic_replay() -> None:
    rows = _gold()["profiles"]["backend"]["candidates"]
    jobs = [
        {
            "raw_job_fingerprint": row["candidate_id"],
            "baseline_fit": row["baseline_fit"],
        }
        for row in rows
    ]
    first = rank_jobs([dict(job) for job in jobs], 50)
    replay = rank_jobs([dict(job) for job in reversed(jobs)], 50)
    assert [row["raw_job_fingerprint"] for row in first] == [
        row["raw_job_fingerprint"] for row in replay
    ]
    assert [row["baseline_rank"] for row in first] == [row["baseline_rank"] for row in replay]
