"""Diagnose multilingual retrieval-to-ranking losses on calibration rows only."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv.embeddings import (
    DEFAULT_SENTENCE_TRANSFORMERS_MODEL,
    DEFAULT_SENTENCE_TRANSFORMERS_REVISION,
    SENTENCE_TRANSFORMERS_BACKEND,
    embed_and_store_jobs,
)
from fitcv.ranking import rank_jobs
from fitcv.vector_search import VECTOR_RETRIEVAL_STRATEGY, run_vector_search
from scripts.benchmark_ranking import build_retrieval_request


def _fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_id_by_url(rows: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in rows:
        candidate_id = str(row["candidate_id"])
        job = dict(row.get("job") or {})
        for value in (candidate_id, job.get("job_url"), row.get("job_url"), row.get("source_job_url")):
            if value:
                result[str(value)] = candidate_id
    return result


def _ranking_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "candidate_id": str(row["candidate_id"]),
            "raw_job_fingerprint": str(row["candidate_id"]),
            "job_url": str(dict(row.get("job") or {}).get("job_url") or row["candidate_id"]),
            "baseline_fit": row.get("baseline_fit"),
            "ai_score": row.get("ai_score"),
            "relevance_grade": row.get("relevance_grade", 0),
        }
        for row in rows
    ]


def _apply_calibration_scores(
    profiles: dict[str, dict[str, Any]],
    artifact_path: Path,
    fixture_sha256: str,
) -> str:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact.get("schema_version") != "ranking_score_artifact_v1":
        raise RuntimeError("invalid_score_artifact_schema")
    if artifact.get("fixture_sha256") != fixture_sha256:
        raise RuntimeError("score_artifact_fixture_sha256_mismatch")
    scores = artifact.get("scores")
    if not isinstance(scores, dict):
        raise RuntimeError("invalid_score_artifact_scores")
    for profile_id, pool in profiles.items():
        profile_scores = scores.get(profile_id)
        if not isinstance(profile_scores, dict):
            raise RuntimeError("invalid_score_artifact_profile_scores")
        for row in pool["candidates"]:
            if row.get("split") != "calibration":
                continue
            score = profile_scores.get(str(row["candidate_id"]))
            if not isinstance(score, dict):
                raise RuntimeError("score_artifact_candidate_mismatch")
            row["baseline_fit"] = float(score["baseline_fit"])
            row["ai_score"] = float(score["ai_score"])
    return _fixture_sha256(artifact_path)


def diagnose_calibration_loss(fixture_path: Path) -> dict[str, Any]:
    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    profiles = data["profiles"]
    score_artifact_path = fixture_path.with_name("p0a-v4-production-scores.json")
    score_artifact_sha256 = None
    if any(row.get("baseline_fit") is None for pool in profiles.values() for row in pool["candidates"] if row.get("split") == "calibration"):
        if score_artifact_path.is_file():
            score_artifact_sha256 = _apply_calibration_scores(
                profiles, score_artifact_path, _fixture_sha256(fixture_path)
            )
        else:
            raise RuntimeError("missing_calibration_score_artifact")
    profile_reports: list[dict[str, Any]] = []
    for profile_id, pool in profiles.items():
        calibration_rows = [deepcopy(row) for row in pool["candidates"] if row.get("split") == "calibration"]
        assert all(row.get("split") == "calibration" for row in calibration_rows)
        calibration_pool = dict(pool)
        calibration_pool["candidates"] = calibration_rows
        request = build_retrieval_request(
            profile_id,
            calibration_pool,
            requested_strategy=VECTOR_RETRIEVAL_STRATEGY,
        )
        request["config"].update(
            {
                "embedding_backend": SENTENCE_TRANSFORMERS_BACKEND,
                "shortlist_embedding_model": DEFAULT_SENTENCE_TRANSFORMERS_MODEL,
                "embedding_model_revision": DEFAULT_SENTENCE_TRANSFORMERS_REVISION,
                "embedding_dimension": 384,
                "embedding_failure_policy": "raise",
            }
        )
        embed_and_store_jobs(request["structured_jobs"], request["config"])
        retrieval = run_vector_search(
            request["profile"],
            request["job_urls"],
            request["config"],
            top_n=request["top_n"],
            structured_jobs=request["structured_jobs"],
            requested_strategy=request["requested_strategy"],
        )
        source_ids = _source_id_by_url(calibration_rows)
        retrieved_rows = []
        for item in retrieval["production_rows"]:
            candidate_id = source_ids.get(str(item["job_url"]))
            if candidate_id:
                retrieved_rows.append({"candidate_id": candidate_id, "retrieval_rank": int(item["vector_rank"])})
        retrieved_ids = [row["candidate_id"] for row in retrieved_rows]
        source_by_id = {str(row["candidate_id"]): row for row in calibration_rows}
        shortlist = [source_by_id[candidate_id] for candidate_id in retrieved_ids]
        ranked_input = _ranking_rows(shortlist)
        full_ranked = rank_jobs(ranked_input, len(ranked_input))
        ranking_top_n = int(pool.get("ranking_top_n", 12))
        ranked = full_ranked[:ranking_top_n]
        final_ids = {str(row["candidate_id"]) for row in ranked}
        retrieval_rank_by_id = {row["candidate_id"]: row["retrieval_rank"] for row in retrieved_rows}
        ranking_by_id = {str(row["candidate_id"]): row for row in full_ranked}
        removed = []
        for candidate_id in retrieved_ids:
            source = source_by_id[candidate_id]
            if int(source.get("relevance_grade") or 0) < 2 or candidate_id in final_ids:
                continue
            ranked_row = ranking_by_id.get(candidate_id, {})
            removed.append(
                {
                    "candidate_id": candidate_id,
                    "retrieval_rank": retrieval_rank_by_id[candidate_id],
                    "ranking_score": ranked_row.get("personalized_rank_score"),
                    "final_rank": ranked_row.get("personalized_rank"),
                    "relevance_grade": source.get("relevance_grade"),
                    "removal_reason": "ranking_cutoff",
                }
            )
        rrf_ranked = sorted(
            full_ranked,
            key=lambda row: (
                -(
                    1 / (60 + int(row["personalized_rank"]))
                    + 1 / (60 + retrieval_rank_by_id[str(row["candidate_id"])])
                ),
                str(row["candidate_id"]),
            ),
        )
        rrf_top = rrf_ranked[:ranking_top_n]
        relevant = {str(row["candidate_id"]) for row in calibration_rows if int(row.get("relevance_grade") or 0) >= 2}
        profile_reports.append(
            {
                "profile_id": profile_id,
                "calibration_row_count": len(calibration_rows),
                "held_out_rows_read": 0,
                "relevant_retrieval_hits_removed_by_ranking": removed,
                "baseline": {
                    "relevant_retrieved": len(set(retrieved_ids) & relevant),
                    "relevant_in_final_ranking": len(final_ids & relevant),
                },
                "rrf_tie_break_diagnostic": {
                    "ranking_top_n": ranking_top_n,
                    "relevant_in_final_ranking": len(
                        {str(row["candidate_id"]) for row in rrf_top} & relevant
                    ),
                    "changed_order": [str(row["candidate_id"]) for row in rrf_top]
                    != [str(row["candidate_id"]) for row in ranked],
                },
            }
        )
    return {
        "schema_version": "ranking_loss_diagnostic_v1",
        "fixture": str(fixture_path),
        "fixture_sha256": _fixture_sha256(fixture_path),
        "arm": "multilingual",
        "score_artifact": str(score_artifact_path) if score_artifact_sha256 else None,
        "score_artifact_sha256": score_artifact_sha256,
        "scope": "calibration_only",
        "held_out_rows_read": 0,
        "production_change": False,
        "profiles": profile_reports,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault("FITCV_CP_SQLITE_PATH", str(output.with_suffix(".sqlite3")))
    report = diagnose_calibration_loss(Path(args.fixture))
    with output.open("w", encoding="utf-8", newline="") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps(report, separators=(",", ":")))


if __name__ == "__main__":
    main()
def _apply_calibration_scores(
    profiles: dict[str, dict[str, Any]],
    artifact_path: Path,
    fixture_sha256: str,
) -> str:
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    if artifact.get("schema_version") != "ranking_score_artifact_v1":
        raise RuntimeError("invalid_score_artifact_schema")
    if artifact.get("fixture_sha256") != fixture_sha256:
        raise RuntimeError("score_artifact_fixture_sha256_mismatch")
    scores = artifact.get("scores")
    if not isinstance(scores, dict):
        raise RuntimeError("invalid_score_artifact_scores")
    for profile_id, pool in profiles.items():
        profile_scores = scores.get(profile_id)
        if not isinstance(profile_scores, dict):
            raise RuntimeError("invalid_score_artifact_profile_scores")
        for row in pool["candidates"]:
            if row.get("split") != "calibration":
                continue
            score = profile_scores.get(str(row["candidate_id"]))
            if not isinstance(score, dict):
                raise RuntimeError("score_artifact_candidate_mismatch")
            row["baseline_fit"] = float(score["baseline_fit"])
            row["ai_score"] = float(score["ai_score"])
    return _fixture_sha256(artifact_path)
