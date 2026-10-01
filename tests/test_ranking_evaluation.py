"""Deterministic ranking gold-set evaluation."""

from __future__ import annotations

import json
import hashlib
import math
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from fitcv.ranking import rank_jobs
from scripts import benchmark_ranking
from scripts.benchmark_ranking import _split_metric_rows

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


def test_label_permutation_does_not_change_retrieval_request() -> None:
    from scripts.benchmark_ranking import build_retrieval_request

    pool = deepcopy(_gold()["profiles"]["backend"])
    baseline = build_retrieval_request("backend", pool)
    for index, row in enumerate(pool["candidates"]):
        row["label"], row["relevance_grade"] = ("relevant", 3) if index % 2 else ("irrelevant", 0)
        row["split"] = "held_out" if row["split"] == "calibration" else "calibration"
    assert build_retrieval_request("backend", pool) == baseline


def test_retrieval_and_ranking_metrics_use_separate_id_sets() -> None:
    rows = [
        {"candidate_id": "c1", "split": "held_out", "relevance_grade": 3},
        {"candidate_id": "c3", "split": "held_out", "relevance_grade": 0},
        {"candidate_id": "c2", "split": "held_out", "relevance_grade": 2},
        {"candidate_id": "c4", "split": "held_out", "relevance_grade": 0},
    ]

    metrics = _split_metric_rows(["c1", "c3", "c2", "c4"], rows, rows, 2, 2, 2)["held_out"]

    assert metrics["retrieval"]["recall"] == 0.5
    assert metrics["retrieval"]["precision"] == 0.5
    assert metrics["ranking"]["recall"] == 0.5
    assert metrics["ranking"]["precision"] == 0.5


def test_retrieval_mrr_preserves_return_order() -> None:
    rows = [
        {"candidate_id": "bad", "split": "held_out", "relevance_grade": 0},
        {"candidate_id": "good", "split": "held_out", "relevance_grade": 3},
    ]

    metrics = _split_metric_rows(["bad", "good"], rows, rows, 2, 2, 2)["held_out"]

    assert metrics["retrieval"]["mrr"] == 0.5


def test_split_metrics_preserve_global_rank_after_split_filter() -> None:
    rows = [
        {"candidate_id": "cal-1", "split": "calibration", "relevance_grade": 0},
        {"candidate_id": "hold-1", "split": "held_out", "relevance_grade": 0},
        {"candidate_id": "cal-2", "split": "calibration", "relevance_grade": 0},
        {"candidate_id": "hold-2", "split": "held_out", "relevance_grade": 2},
    ]

    metrics = _split_metric_rows(
        [row["candidate_id"] for row in rows],
        rows,
        rows,
        4,
        4,
        4,
    )["held_out"]

    assert metrics["retrieval"]["mrr"] == 0.25
    assert metrics["ranking"]["mrr"] == 0.25


def test_benchmark_json_writer_preserves_lf_bytes(tmp_path: Path) -> None:
    output = tmp_path / "report.json"

    benchmark_ranking._write_json(output, {"message": "line 1\nline 2"})

    assert b"\r\n" not in output.read_bytes()


def test_primary_metrics_exclude_borderline_grade() -> None:
    rows = [
        {"candidate_id": "borderline", "split": "held_out", "relevance_grade": 1},
        {"candidate_id": "relevant", "split": "held_out", "relevance_grade": 2},
    ]

    metrics = _split_metric_rows(["borderline"], rows, rows, 1, 1, 1)["held_out"]

    assert metrics["retrieval"]["recall"] == 0.0
    assert metrics["retrieval"]["mrr"] == 0.0


def test_metric_cutoffs_remain_separate() -> None:
    rows = [
        {"candidate_id": "bad-1", "split": "held_out", "relevance_grade": 0},
        {"candidate_id": "bad-2", "split": "held_out", "relevance_grade": 0},
        {"candidate_id": "bad-3", "split": "held_out", "relevance_grade": 0},
        {"candidate_id": "good", "split": "held_out", "relevance_grade": 2},
    ]

    metrics = _split_metric_rows(
        ["bad-1", "bad-2", "bad-3"],
        [rows[0], rows[3]],
        rows,
        3,
        2,
        1,
    )["held_out"]

    assert metrics["retrieval"]["mrr"] == 0.0
    assert metrics["ranking"]["mrr"] == 0.5


def test_evaluation_input_rejects_unassigned_split_and_duplicate_source() -> None:
    rows = [
        {"candidate_id": "a", "source_id": "same", "source_group_id": "g1", "split": None, "reviewed": True, "relevance_grade": 0},
        {"candidate_id": "b", "source_id": "same", "source_group_id": "g2", "split": "held_out", "reviewed": True, "relevance_grade": 1},
        {"candidate_id": "c", "source_id": "other", "source_group_id": "g3", "split": "calibration", "reviewed": True, "relevance_grade": 2},
    ]

    errors = benchmark_ranking._validate_evaluation_input(
        {"profile": {"candidates": rows, "retrieval_top_n": 2, "ranking_top_n": 1, "ndcg_top_n": 1}}
    )

    assert "profile:invalid_split_values:" in next(error for error in errors if error.startswith("profile:invalid_split_values:"))
    assert "profile:same:duplicate_source_id" in errors


def test_source_backed_payload_rejects_synthetic_fallback() -> None:
    errors = benchmark_ranking._source_backed_payload_errors(
        {"profile": {"profile": {}, "candidates": [{"candidate_id": "c1", "job": {}}]}}
    )

    assert errors == [
        "profile:missing_source_backed_profile",
        "profile:c1:missing_source_backed_job_payload",
    ]


def test_source_backed_scores_are_required_before_benchmark() -> None:
    errors = benchmark_ranking._source_backed_score_errors(
        {
            "profile": {
                "candidates": [
                    {"candidate_id": "c1", "baseline_fit": 0.0, "ai_score": None},
                    {"candidate_id": "c2", "baseline_fit": None, "ai_score": 0.0},
                ]
            }
        }
    )

    assert errors == [
        "profile:c1:missing_or_invalid_ai_score",
        "profile:c2:missing_or_invalid_baseline_fit",
    ]


def _source_backed_review_profiles() -> dict[str, dict[str, Any]]:
    return {
        "profile": {
            "candidates": [
                {
                    "candidate_id": "c1",
                    "reviewed": True,
                    "label": "relevant",
                    "relevance_grade": 2,
                    "judgments": [
                        {
                            "reviewer_id": "reviewer-a",
                            "label": "relevant",
                            "relevance_grade": 2,
                            "rationale": "Direct role match.",
                            "evidence": [{"field": "description", "quote": "analytics intern"}],
                        },
                        {
                            "reviewer_id": "reviewer-b",
                            "label": "relevant",
                            "relevance_grade": 2,
                            "rationale": "Role and profile align.",
                            "evidence": [{"field": "description", "quote": "business analysis"}],
                        },
                    ],
                    "adjudication": None,
                }
            ]
        }
    }


def test_source_backed_review_accepts_two_complete_agreements() -> None:
    assert benchmark_ranking._source_backed_review_errors(_source_backed_review_profiles()) == []


@pytest.mark.parametrize(
    ("mutator", "expected"),
    [
        (lambda row: row.update(judgments=row["judgments"][:1]), "profile:c1:requires_exactly_two_judgments"),
        (lambda row: row["judgments"][1].update(reviewer_id="reviewer-a"), "profile:c1:duplicate_reviewer_identity"),
        (lambda row: row["judgments"][0].update(relevance_grade=4), "profile:c1:judgment_0_invalid_grade"),
        (lambda row: row["judgments"][0].update(label="borderline"), "profile:c1:judgment_0_label_grade_mismatch"),
        (lambda row: row["judgments"][0].update(rationale=" "), "profile:c1:judgment_0_missing_rationale"),
        (lambda row: row["judgments"][0].update(evidence=[]), "profile:c1:judgment_0_missing_evidence"),
    ],
)
def test_source_backed_review_rejects_incomplete_judgments(mutator: Any, expected: str) -> None:
    profiles = _source_backed_review_profiles()
    mutator(profiles["profile"]["candidates"][0])

    assert expected in benchmark_ranking._source_backed_review_errors(profiles)


def test_source_backed_review_requires_adjudication_for_disagreement() -> None:
    profiles = _source_backed_review_profiles()
    row = profiles["profile"]["candidates"][0]
    row["judgments"][1].update(label="borderline", relevance_grade=1)

    errors = benchmark_ranking._source_backed_review_errors(profiles)

    assert "profile:c1:disagreement_requires_adjudication" in errors
    row["adjudication"] = {
        "adjudicator_id": "adjudicator-1",
        "final_grade": 2,
        "decision_rationale": "First judgment upheld after review.",
    }
    assert benchmark_ranking._source_backed_review_errors(profiles) == []


def test_source_backed_ready_fixture_requires_ready_manifest(tmp_path: Path) -> None:
    fixture = tmp_path / "ranking_source_backed_v2.json"
    fixture.write_text(json.dumps({"fixture_status": "ready", "profiles": {}}), encoding="utf-8")
    manifest = tmp_path / "ranking_source_backed_v2_manifest.json"
    manifest.write_text(json.dumps({"fixture_status": "awaiting_human_labels"}), encoding="utf-8")

    errors = benchmark_ranking._manifest_errors(fixture, json.loads(fixture.read_text()), "actual")

    assert "source_backed:manifest_fixture_not_ready" in errors


def test_benchmark_rejects_ready_source_backed_fixture_without_review_completion(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    fixture = tmp_path / "source-backed-ready.json"
    fixture.write_text(
        json.dumps(
            {
                "schema_version": "ranking_gold_source_backed_v2",
                "fixture_role": "source_backed",
                "fixture_status": "ready",
                "profiles": {
                    "profile": {
                        "candidates": [
                            {
                                "candidate_id": "c1",
                                "label": None,
                                "relevance_grade": None,
                                "judgments": [],
                            }
                        ]
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    monkeypatch.setattr(benchmark_ranking, "_manifest_errors", lambda *args: [])
    monkeypatch.setattr(benchmark_ranking, "_source_backed_payload_errors", lambda *args: [])
    monkeypatch.setattr(
        sys,
        "argv",
        ["benchmark_ranking.py", "--fixture", str(fixture), "--output", str(output)],
    )

    benchmark_ranking.main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "not_run"
    assert report["reason"] == "invalid_source_backed_review"


def test_evaluation_input_rejects_full_pool_retrieval() -> None:
    errors = benchmark_ranking._validate_evaluation_input(
        {
            "profile": {
                "retrieval_top_n": 2,
                "candidates": [
                    {"candidate_id": "a", "split": "calibration", "reviewed": True, "relevance_grade": 3},
                    {"candidate_id": "b", "split": "held_out", "reviewed": True, "relevance_grade": 1},
                ],
            }
        }
    )

    assert "profile:retrieval_top_n_must_be_less_than_pool_size" in errors


def test_evaluation_input_accepts_source_groups_reserved_to_one_split() -> None:
    rows = [
        {"candidate_id": "cal-1", "source_group_id": "group-cal", "split": "calibration", "reviewed": True, "relevance_grade": 3},
        {"candidate_id": "cal-2", "source_group_id": "group-cal", "split": "calibration", "reviewed": True, "relevance_grade": 0},
        {"candidate_id": "hold-1", "source_group_id": "group-hold", "split": "held_out", "reviewed": True, "relevance_grade": 1},
        {"candidate_id": "hold-2", "source_group_id": "group-hold", "split": "held_out", "reviewed": True, "relevance_grade": 0},
    ]

    errors = benchmark_ranking._validate_evaluation_input(
        {"profile": {"candidates": rows, "retrieval_top_n": 2, "ranking_top_n": 1, "ndcg_top_n": 1}}
    )

    assert errors == []


def test_evaluation_input_rejects_source_group_crossing_split() -> None:
    rows = [
        {"candidate_id": "cal-1", "source_group_id": "group-1", "split": "calibration", "reviewed": True, "relevance_grade": 3},
        {"candidate_id": "hold-1", "source_group_id": "group-1", "split": "held_out", "reviewed": True, "relevance_grade": 1},
        {"candidate_id": "hold-2", "source_group_id": "group-2", "split": "held_out", "reviewed": True, "relevance_grade": 0},
    ]

    errors = benchmark_ranking._validate_evaluation_input(
        {"profile": {"candidates": rows, "retrieval_top_n": 2, "ranking_top_n": 1, "ndcg_top_n": 1}}
    )

    assert "profile:group-1:source_group_crosses_split" in errors


def test_score_artifact_overlays_scores_only_for_matching_fixture(tmp_path: Path) -> None:
    profiles = {
        "profile": {
            "candidates": [
                {"candidate_id": "c1", "baseline_fit": None, "ai_score": None},
                {"candidate_id": "c2", "baseline_fit": None, "ai_score": None},
            ]
        }
    }
    artifact = tmp_path / "scores.json"
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "ranking_score_artifact_v1",
                "fixture_sha256": "fixture",
                "scores": {
                    "profile": {
                        "c1": {"baseline_fit": 0.8, "ai_score": 0.7},
                        "c2": {"baseline_fit": 0.2, "ai_score": 0.1},
                    }
                },
            }
        ),
        encoding="utf-8",
    )

    benchmark_ranking._apply_score_artifact(profiles, artifact, "fixture")

    assert profiles["profile"]["candidates"][0]["baseline_fit"] == pytest.approx(0.8)
    assert profiles["profile"]["candidates"][1]["ai_score"] == pytest.approx(0.1)


def test_score_artifact_rejects_fixture_hash_mismatch(tmp_path: Path) -> None:
    artifact = tmp_path / "scores.json"
    artifact.write_text(
        json.dumps(
            {
                "schema_version": "ranking_score_artifact_v1",
                "fixture_sha256": "wrong",
                "scores": {},
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(RuntimeError, match="score_artifact_fixture_sha256_mismatch"):
        benchmark_ranking._apply_score_artifact({"profile": {"candidates": []}}, artifact, "fixture")


def test_evaluation_input_rejects_inconsistent_cutoffs() -> None:
    rows = [
        {"candidate_id": "cal-1", "split": "calibration", "reviewed": True, "relevance_grade": 3},
        {"candidate_id": "cal-2", "split": "calibration", "reviewed": True, "relevance_grade": 0},
        {"candidate_id": "hold-1", "split": "held_out", "reviewed": True, "relevance_grade": 1},
        {"candidate_id": "hold-2", "split": "held_out", "reviewed": True, "relevance_grade": 0},
    ]

    errors = benchmark_ranking._validate_evaluation_input(
        {"profile": {"candidates": rows, "retrieval_top_n": 3, "ranking_top_n": 4, "ndcg_top_n": 5}}
    )

    assert "profile:ranking_top_n_must_not_exceed_retrieval_top_n" in errors
    assert "profile:ndcg_top_n_must_not_exceed_ranking_top_n" in errors


def test_run_once_uses_retrieval_ids_for_shortlist_metrics(monkeypatch: Any) -> None:
    rows = [
        {
            "candidate_id": f"c{index}",
            "split": "held_out",
            "relevance_grade": 2,
            "job": {"job_url": f"job-{index}"},
            "baseline_fit": float(index),
            "ai_score": float(index),
        }
        for index in range(20)
    ]

    monkeypatch.setattr(
        benchmark_ranking,
        "run_vector_search",
        lambda *args, **kwargs: {
            "production_rows": [{"job_url": row["job"]["job_url"]} for row in rows],
            "diagnostics": {"effective_strategy": "lexical", "backend_id": "test"},
        },
    )
    monkeypatch.setattr(
        benchmark_ranking,
        "rank_jobs",
        lambda ranked_rows, top_n: ranked_rows[:top_n],
    )

    metrics, _, _ = benchmark_ranking._run_once(
        {"profile": {"candidates": rows, "retrieval_top_n": 20, "ranking_top_n": 5, "ndcg_top_n": 5}},
        set(),
    )

    held_out = metrics["split_metrics"]["held_out"]
    assert held_out["retrieval"]["recall"] == 1.0
    assert held_out["ranking"]["recall"] == 0.25
    assert metrics["language_split_metrics"]["profile"]["held_out"]["ranking"]["recall"] == 0.25


def test_manifest_mismatch_blocks_source_backed_run(tmp_path: Path) -> None:
    fixture = tmp_path / "ranking_source_backed_v2.json"
    fixture.write_text(json.dumps({"profiles": {}, "source_snapshot": {"path": "", "sha256": ""}}), encoding="utf-8")
    manifest = tmp_path / "ranking_source_backed_v2_manifest.json"
    manifest.write_text(json.dumps({"fixture_path": "wrong.json", "fixture_sha256": "wrong"}), encoding="utf-8")

    errors = benchmark_ranking._manifest_errors(fixture, json.loads(fixture.read_text()), "actual")

    assert "source_backed:manifest_fixture_path_mismatch" in errors
    assert "source_backed:fixture_sha256_mismatch" in errors


def test_runtime_error_report_keeps_requested_arm(tmp_path: Path, monkeypatch: Any) -> None:
    output = tmp_path / "report.json"
    monkeypatch.setattr(benchmark_ranking, "_run_once", lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")))
    monkeypatch.setattr(
        sys,
        "argv",
        ["benchmark_ranking.py", "--fixture", str(FIXTURE), "--arm", "lexical", "--output", str(output)],
    )

    benchmark_ranking.main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "not_run"
    assert report["arm"] == "lexical"


@pytest.mark.parametrize("arm", ["lexical", "multilingual"])
def test_benchmark_report_binds_results_to_fixture_bytes(
    arm: str,
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    output = tmp_path / f"{arm}.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "benchmark_ranking.py",
            "--fixture",
            str(FIXTURE),
            "--arm",
            arm,
            "--warmup-iterations",
            "0",
            "--measured-iterations",
            "1",
            "--output",
            str(output),
        ],
    )

    benchmark_ranking.main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["fixture_sha256"] == hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    assert report["fixture_role"] == "smoke"


def test_benchmark_rejects_fixture_awaiting_human_labels(tmp_path: Path, monkeypatch: Any) -> None:
    fixture = tmp_path / "source-backed-draft.json"
    fixture.write_text(
        json.dumps({
            "schema_version": "ranking_gold_source_backed_v2",
            "fixture_role": "source_backed",
            "fixture_status": "awaiting_human_labels",
            "profiles": {},
        }),
        encoding="utf-8",
    )
    output = tmp_path / "report.json"
    monkeypatch.setattr(
        sys,
        "argv",
        ["benchmark_ranking.py", "--fixture", str(fixture), "--output", str(output)],
    )

    benchmark_ranking.main()

    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == "not_run"
    assert report["reason"] == "fixture_not_ready"
    assert report["fixture_role"] == "source_backed"


def test_calibration_loss_diagnostic_does_not_read_held_out_rows(tmp_path: Path, monkeypatch: Any) -> None:
    from scripts import diagnose_ranking_loss

    fixture = tmp_path / "fixture.json"
    fixture.write_text(
        json.dumps(
            {
                "profiles": {
                    "profile": {
                        "profile": {"preferences": {}, "skills": []},
                        "retrieval_top_n": 2,
                        "ranking_top_n": 1,
                        "candidates": [
                            {
                                "candidate_id": "cal",
                                "split": "calibration",
                                "relevance_grade": 3,
                                "baseline_fit": 0.2,
                                "ai_score": 0.2,
                                "job": {"job_url": "cal-url", "title": "Calibration"},
                            },
                            {
                                "candidate_id": "held",
                                "split": "held_out",
                                "relevance_grade": 3,
                                "baseline_fit": 0.9,
                                "ai_score": 0.9,
                                "job": {"job_url": "held-url", "title": "Held out"},
                            },
                        ],
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    seen_job_urls: list[str] = []

    def fake_embed(jobs: list[dict[str, Any]], config: dict[str, Any]) -> int:
        seen_job_urls.extend(str(job["job_url"]) for job in jobs)
        return 0

    def fake_search(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert args[1] == ["cal-url"]
        return {"production_rows": [{"job_url": "cal-url", "vector_rank": 1}], "diagnostics": {}}

    monkeypatch.setattr(diagnose_ranking_loss, "embed_and_store_jobs", fake_embed)
    monkeypatch.setattr(diagnose_ranking_loss, "run_vector_search", fake_search)

    report = diagnose_ranking_loss.diagnose_calibration_loss(fixture)

    assert seen_job_urls == ["cal-url"]
    assert report["scope"] == "calibration_only"
    assert report["held_out_rows_read"] == 0
    assert report["profiles"][0]["held_out_rows_read"] == 0
