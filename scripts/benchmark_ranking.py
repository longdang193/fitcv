"""Benchmark deterministic ranking replay without external services."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv.ranking import rank_jobs
from fitcv.vector_search import run_vector_search


def _percentile(values: list[float], percentile: float) -> float:
    return sorted(values)[max(0, math.ceil(percentile * len(values)) - 1)]


def _ranked(rows: list[dict[str, Any]], key: str, top_n: int) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -(float(row[key]) if row[key] is not None else float("-inf")),
            row["candidate_id"],
        ),
    )[:top_n]


def _recall(rows: list[dict[str, Any]], key: str, top_n: int) -> float:
    relevant = {row["candidate_id"] for row in rows if row["relevance_grade"] > 0}
    retrieved = {row["candidate_id"] for row in _ranked(rows, key, top_n)}
    return len(relevant & retrieved) / len(relevant) if relevant else 1.0


def _ndcg(rows: list[dict[str, Any]], key: str, top_n: int) -> float:
    ranked = _ranked(rows, key, top_n)
    dcg = sum(
        (2**row["relevance_grade"] - 1) / math.log2(index + 2)
        for index, row in enumerate(ranked)
    )
    ideal = sorted((row["relevance_grade"] for row in rows), reverse=True)[:top_n]
    idcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal))
    return dcg / idcg if idcg else 1.0


def _run_once(
    profiles: dict[str, dict[str, Any]],
    mode: str,
    cache: set[str],
) -> tuple[dict[str, float], dict[str, int]]:
    recalls: list[float] = []
    ai_recalls: list[float] = []
    ndcgs: list[float] = []
    llm_calls = 0
    cache_hits = 0
    cache_misses = 0
    for profile_id, pool in profiles.items():
        source_rows = pool["candidates"]
        profile = {
            "preferences": {
                "target_role": profile_id,
                "role_families": [profile_id],
                "domains": [profile_id],
                "location_types": ["remote"],
            },
            "skills": [profile_id],
        }
        source_by_id = {str(row["candidate_id"]): row for row in source_rows}
        structured_jobs = []
        for source in source_rows:
            candidate_id = str(source["candidate_id"])
            relevant = int(source["relevance_grade"]) > 0
            structured_jobs.append(
                {
                    "job_url": candidate_id,
                    "title": profile_id if relevant else "unrelated",
                    "job_family": profile_id if relevant else "unrelated",
                    "required_skills_canonical": [profile_id] if relevant else ["unrelated"],
                    "domain": profile_id if relevant else "unrelated",
                    "location_type": "remote",
                }
            )
        retrieval = run_vector_search(
            profile,
            [str(row["candidate_id"]) for row in source_rows],
            {
                "retrieval_strategy": "lexical_v1",
                "pipeline": {"vector_search_top_n": 50},
                "ranking_policy": {
                    "declared_preference_component_weights": {
                        "domain": 0.50,
                        "role_family": 0.30,
                        "work_mode": 0.20,
                    }
                },
            },
            top_n=50,
            structured_jobs=structured_jobs,
        )
        retrieved_ids = {str(row["job_url"]) for row in retrieval["production_rows"]}
        relevant_ids = {
            candidate_id for candidate_id, source in source_by_id.items()
            if int(source["relevance_grade"]) > 0
        }
        recalls.append(len(retrieved_ids & relevant_ids) / len(relevant_ids) if relevant_ids else 1.0)
        rows = []
        for source in source_rows:
            candidate_id = source["candidate_id"]
            cache_key = f"lexical_v1:{profile_id}:{candidate_id}"
            if cache_key in cache:
                cache_hits += 1
            else:
                cache.add(cache_key)
                cache_misses += 1
            row = {
                "candidate_id": candidate_id,
                "raw_job_fingerprint": candidate_id,
                "job_url": candidate_id,
                "baseline_fit": source["baseline_fit"],
                "ai_score": source["ai_score"],
                "relevance_grade": source["relevance_grade"],
            }
            if mode == "model" and row["ai_score"] is None:
                row["ai_score"] = row["baseline_fit"]
                llm_calls += 1
            rows.append(row)
        shortlist = [row for row in rows if row["candidate_id"] in retrieved_ids]
        ranked = rank_jobs([dict(row) for row in shortlist], 12)
        ai_recalls.append(_recall(ranked, "ai_score", 12))
        ndcgs.append(_ndcg(ranked, "baseline_fit", 15))
    return (
        {
            "shortlist_recall_at_50": statistics.mean(recalls),
            "recall_at_ai_score_top_n": statistics.mean(ai_recalls),
            "ndcg_at_15": statistics.mean(ndcgs),
        },
        {"cache_hits": cache_hits, "cache_misses": cache_misses, "llm_calls": llm_calls, "retries": 0},
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="tests/fixtures/ranking_gold.json")
    parser.add_argument("--mode", choices=("replayed", "model"), default="replayed")
    parser.add_argument("--warmup-iterations", type=int, default=1)
    parser.add_argument("--measured-iterations", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.warmup_iterations < 0 or args.measured_iterations < 1:
        parser.error("iterations must be warmup >= 0 and measured >= 1")

    data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    profiles = data["profiles"]
    cache: set[str] = set()
    for _ in range(args.warmup_iterations):
        _run_once(profiles, args.mode, cache)
    durations: list[float] = []
    quality: dict[str, float] = {}
    metrics: dict[str, int] = {}
    for _ in range(args.measured_iterations):
        started = time.perf_counter()
        quality, metrics = _run_once(profiles, args.mode, cache)
        durations.append((time.perf_counter() - started) * 1000)

    candidate_count = sum(len(pool["candidates"]) for pool in profiles.values())
    cache_total = metrics["cache_hits"] + metrics["cache_misses"]
    result = {
        "schema_version": "ranking_benchmark_v1",
        "fixture": str(args.fixture),
        "mode": args.mode,
        "warmup_iterations": args.warmup_iterations,
        "measured_iterations": args.measured_iterations,
        "latency_ms": {"p50": statistics.median(durations), "p95": _percentile(durations, 0.95)},
        "metrics": {
            "retrieval": {"strategy": "lexical_v1", "production_shortlist": 50},
            "ranking": {"profiles": len(profiles), "candidates": candidate_count, **quality},
            "cache": {**metrics, "hit_rate": metrics["cache_hits"] / cache_total if cache_total else 0.0},
            "llm": {"calls": metrics["llm_calls"], "retries": metrics["retries"]},
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
