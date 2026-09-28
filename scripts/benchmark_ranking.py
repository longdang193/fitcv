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
from fitcv.vector_search import LEXICAL_RETRIEVAL_STRATEGY, VECTOR_RETRIEVAL_STRATEGY, run_vector_search

_EVALUATOR_FIELDS = {
    "label",
    "relevance_grade",
    "split",
    "reviewed",
    "baseline_fit",
    "ai_score",
    "ai_score_status",
}


def _percentile(values: list[float], percentile: float) -> float:
    return sorted(values)[max(0, math.ceil(percentile * len(values)) - 1)]


def _ranked(rows: list[dict[str, Any]], key: str, top_n: int) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -(float(row[key]) if row.get(key) is not None else float("-inf")),
            str(row["candidate_id"]),
        ),
    )[:top_n]


def _relevant(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row["candidate_id"])
        for row in rows
        if int(row.get("relevance_grade") or 0) > 0
    }


def _recall(returned_ids: set[str], eligible_rows: list[dict[str, Any]]) -> float:
    relevant = _relevant(eligible_rows)
    return len(returned_ids & relevant) / len(relevant) if relevant else 1.0


def _precision(returned_ids: set[str], eligible_rows: list[dict[str, Any]]) -> float:
    eligible_ids = {str(row["candidate_id"]) for row in eligible_rows}
    returned = returned_ids & eligible_ids
    return len(returned & _relevant(eligible_rows)) / len(returned) if returned else 1.0


def _ndcg(returned: list[dict[str, Any]], eligible_rows: list[dict[str, Any]], top_n: int) -> float:
    ranked = returned[:top_n]
    dcg = sum(
        (2 ** int(row.get("relevance_grade") or 0) - 1) / math.log2(index + 2)
        for index, row in enumerate(ranked)
    )
    ideal = sorted(
        (int(row.get("relevance_grade") or 0) for row in eligible_rows),
        reverse=True,
    )[:top_n]
    idcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal))
    return dcg / idcg if idcg else 1.0


def _split_metric_rows(
    retrieved_ids: set[str],
    ranked_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    top_n: int,
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for split in ("calibration", "held_out"):
        eligible = [row for row in source_rows if row.get("split") == split]
        ranked = [row for row in ranked_rows if row.get("split") == split]
        ranked_ids = {str(row.get("candidate_id")) for row in ranked[:top_n]}
        metrics[split] = {
            "count": len(eligible),
            "retrieval_recall_at_n": _recall(retrieved_ids, eligible),
            "retrieval_precision_at_n": _precision(retrieved_ids, eligible),
            "ranking_recall_at_n": _recall(ranked_ids, eligible),
            "ranking_precision_at_n": _precision(ranked_ids, eligible),
            "ranking_ndcg_at_n": _ndcg(ranked, eligible, top_n),
        }
    return metrics


def _profile_request(profile_id: str, pool: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = dict(pool.get("profile") or {})
    if not profile:
        profile = {
            "preferences": {
                "target_role": profile_id,
                "role_families": [profile_id],
                "domains": [profile_id],
                "location_types": ["remote"],
            },
            "skills": [profile_id],
        }
    jobs: list[dict[str, Any]] = []
    for source in pool["candidates"]:
        job = {
            key: value
            for key, value in dict(source.get("job") or source.get("retrieval") or {}).items()
            if key not in _EVALUATOR_FIELDS
        }
        if not job:
            candidate_id = str(source["candidate_id"])
            job = {
                "job_url": candidate_id,
                "title": profile_id,
                "job_family": profile_id,
                "required_skills_canonical": [profile_id],
                "domain": profile_id,
                "location_type": "remote",
            }
        job["job_url"] = str(job.get("job_url") or source["candidate_id"])
        jobs.append(job)
    return profile, jobs


def build_retrieval_request(
    profile_id: str,
    pool: dict[str, Any],
    *,
    requested_strategy: str = LEXICAL_RETRIEVAL_STRATEGY,
) -> dict[str, Any]:
    """Build retrieval input without evaluator-only fields."""
    profile, jobs = _profile_request(profile_id, pool)
    return {
        "profile": profile,
        "job_urls": [job["job_url"] for job in jobs],
        "structured_jobs": jobs,
        "config": {
            "pipeline": {"vector_search_top_n": pool.get("retrieval_top_n", 50)},
            "ranking_policy": {
                "declared_preference_component_weights": {
                    "domain": 0.50,
                    "role_family": 0.30,
                    "work_mode": 0.20,
                }
            },
        },
        "top_n": int(pool.get("retrieval_top_n", 50)),
        "requested_strategy": requested_strategy,
    }


def _run_once(
    profiles: dict[str, dict[str, Any]],
    cache: set[str],
    *,
    arm: str = "lexical",
) -> tuple[dict[str, float], dict[str, int], dict[str, Any]]:
    shortlist_recalls: list[float] = []
    shortlist_precisions: list[float] = []
    ranking_recalls: list[float] = []
    ranking_precisions: list[float] = []
    ndcgs: list[float] = []
    llm_calls = 0
    scoring_failures = 0
    cache_hits = 0
    cache_misses = 0
    retrieval_returned_count = 0
    ranking_returned_count = 0
    eligible_count = 0
    shortlist_top_n = 0
    ranking_top_n = 0
    split_counts = {"calibration": 0, "held_out": 0}
    language_split_counts: dict[str, dict[str, int]] = {}
    split_metrics: dict[str, list[dict[str, float | int]]] = {}
    fallback_count = 0
    effective_strategies: set[str] = set()
    backend_ids: set[str] = set()
    requested_strategy = VECTOR_RETRIEVAL_STRATEGY if arm == "incumbent" else LEXICAL_RETRIEVAL_STRATEGY
    for profile_id, pool in profiles.items():
        source_rows = list(pool["candidates"])
        eligible_count += len(source_rows)
        for source in source_rows:
            split = str(source.get("split") or "")
            if split in split_counts:
                split_counts[split] += 1
            language = str(source.get("language") or profile_id)
            language_counts = language_split_counts.setdefault(language, {"calibration": 0, "held_out": 0})
            if split in language_counts:
                language_counts[split] += 1
        request = build_retrieval_request(
            profile_id,
            pool,
            requested_strategy=requested_strategy,
        )
        retrieval = run_vector_search(
            request["profile"],
            request["job_urls"],
            request["config"],
            top_n=request["top_n"],
            structured_jobs=request["structured_jobs"],
            requested_strategy=request["requested_strategy"],
        )
        diagnostics = dict(retrieval.get("diagnostics") or {})
        fallback_count += int(bool(diagnostics.get("fallback_used")))
        effective_strategies.add(str(diagnostics.get("effective_strategy") or ""))
        backend_ids.add(str(diagnostics.get("backend_id") or ""))
        source_ids_by_url: dict[str, str] = {}
        for source in source_rows:
            candidate_id = str(source["candidate_id"])
            job = dict(source.get("job") or {})
            for value in (
                candidate_id,
                job.get("job_url"),
                job.get("source_job_url"),
                source.get("job_url"),
                source.get("source_job_url"),
            ):
                if value:
                    source_ids_by_url[str(value)] = candidate_id
        retrieved_ids = {
            source_ids_by_url.get(str(row["job_url"]), str(row["job_url"]))
            for row in retrieval["production_rows"]
        }
        retrieval_returned_count += len(retrieved_ids)
        shortlist_top_n = request["top_n"]
        shortlist_recalls.append(_recall(retrieved_ids, source_rows))
        shortlist_precisions.append(_precision(retrieved_ids, source_rows))
        source_by_id = {str(row["candidate_id"]): row for row in source_rows}
        rows: list[dict[str, Any]] = []
        for source in source_rows:
            candidate_id = str(source["candidate_id"])
            cache_key = f"lexical_v1:{profile_id}:{candidate_id}"
            if cache_key in cache:
                cache_hits += 1
            else:
                cache.add(cache_key)
                cache_misses += 1
            ai_score = source.get("ai_score")
            if ai_score is None:
                scoring_failures += 1
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "raw_job_fingerprint": candidate_id,
                    "job_url": str(
                        dict(source.get("job") or {}).get("job_url") or candidate_id
                    ),
                    "baseline_fit": source.get("baseline_fit"),
                    "ai_score": ai_score,
                    "relevance_grade": source.get("relevance_grade", 0),
                }
            )
        shortlist = [row for row in rows if row["candidate_id"] in retrieved_ids]
        ranking_top_n = int(pool.get("ranking_top_n", 12))
        ranked = rank_jobs([dict(row) for row in shortlist], ranking_top_n)
        ranking_returned_count += len(ranked)
        ranked_by_id = {str(row.get("raw_job_fingerprint") or row.get("candidate_id")): row for row in ranked}
        ranked_eval = [
            {**source_by_id[candidate_id], **row, "candidate_id": candidate_id}
            for candidate_id, row in ranked_by_id.items()
            if candidate_id in source_by_id
        ]
        pool_split_metrics = _split_metric_rows(
            set(ranked_by_id),
            ranked_eval,
            source_rows,
            int(pool.get("ndcg_top_n", 15)),
        )
        ranked_ids = set(ranked_by_id)
        ranking_recalls.append(_recall(ranked_ids, source_rows))
        ranking_precisions.append(_precision(ranked_ids, source_rows))
        ndcgs.append(_ndcg(ranked_eval, source_rows, int(pool.get("ndcg_top_n", 15))))
        split_metrics.setdefault("calibration", []).append(pool_split_metrics["calibration"])
        split_metrics.setdefault("held_out", []).append(pool_split_metrics["held_out"])
    return (
        {
            "shortlist_recall": statistics.mean(shortlist_recalls),
            "shortlist_precision": statistics.mean(shortlist_precisions),
            "ranking_recall": statistics.mean(ranking_recalls),
            "ranking_precision": statistics.mean(ranking_precisions),
            "ndcg": statistics.mean(ndcgs),
            "split_metrics": {
                split: {
                    "count": int(statistics.mean(item["count"] for item in values)),
                    "retrieval_recall_at_n": statistics.mean(item["retrieval_recall_at_n"] for item in values),
                    "retrieval_precision_at_n": statistics.mean(item["retrieval_precision_at_n"] for item in values),
                    "ranking_recall_at_n": statistics.mean(item["ranking_recall_at_n"] for item in values),
                    "ranking_precision_at_n": statistics.mean(item["ranking_precision_at_n"] for item in values),
                    "ranking_ndcg_at_n": statistics.mean(item["ranking_ndcg_at_n"] for item in values),
                }
                for split, values in split_metrics.items()
            },
        },
        {
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "llm_calls": llm_calls,
            "retries": 0,
            "scoring_failure_count": scoring_failures,
        },
        {
            "retrieval_returned_count": retrieval_returned_count,
            "ranking_returned_count": ranking_returned_count,
            "eligible_count": eligible_count,
            "split_counts": split_counts,
            "language_split_counts": language_split_counts,
            "shortlist_top_n": shortlist_top_n,
            "ranking_top_n": ranking_top_n,
            "fallback_count": fallback_count,
            "requested_strategy": requested_strategy,
            "effective_strategies": sorted(effective_strategies),
            "backend_ids": sorted(backend_ids),
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="tests/fixtures/ranking_gold.json")
    parser.add_argument("--mode", default="replayed")
    parser.add_argument("--arm", choices=("incumbent", "lexical", "multilingual"), default="incumbent")
    parser.add_argument("--warmup-iterations", type=int, default=1)
    parser.add_argument("--measured-iterations", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.mode != "replayed":
        parser.error(f"unsupported mode: {args.mode}; only replayed is supported")
    if args.warmup_iterations < 0 or args.measured_iterations < 1:
        parser.error("iterations must be warmup >= 0 and measured >= 1")

    if args.arm == "multilingual":
        result = {
            "schema_version": "ranking_benchmark_v3",
            "arm": "multilingual",
            "status": "not_run",
            "reason": "approved multilingual retrieval backend unavailable",
            "fixture": str(args.fixture),
        }
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, separators=(",", ":")))
        return

    data = json.loads(Path(args.fixture).read_text(encoding="utf-8"))
    profiles = data["profiles"]
    cache: set[str] = set()
    for _ in range(args.warmup_iterations):
        _run_once(profiles, cache, arm=args.arm)
    durations: list[float] = []
    quality: dict[str, float] = {}
    cache_metrics: dict[str, int] = {}
    observation: dict[str, Any] = {}
    for _ in range(args.measured_iterations):
        started = time.perf_counter()
        quality, cache_metrics, observation = _run_once(profiles, cache, arm=args.arm)
        durations.append((time.perf_counter() - started) * 1000)

    cache_total = cache_metrics["cache_hits"] + cache_metrics["cache_misses"]
    result = {
        "schema_version": "ranking_benchmark_v3",
        "fixture": str(args.fixture),
        "arm": args.arm,
        "status": "measured",
        "fixture_role": "source_backed" if "data/fitcv-p0-corpus" in str(args.fixture).replace("\\", "/") else "smoke",
        "mode": args.mode,
        "warmup_iterations": args.warmup_iterations,
        "measured_iterations": args.measured_iterations,
        "latency_ms": {"p50": statistics.median(durations), "p95": _percentile(durations, 0.95)},
        "metrics": {
            "retrieval": {
                "requested_strategy": observation["requested_strategy"],
                "effective_strategies": observation["effective_strategies"],
                "backend_ids": observation["backend_ids"],
                "fallback_count": observation["fallback_count"],
                "top_n": observation["shortlist_top_n"],
                "returned_count": observation["retrieval_returned_count"],
                "eligible_count": observation["eligible_count"],
                "coverage": observation["retrieval_returned_count"] / observation["eligible_count"] if observation["eligible_count"] else 0.0,
                "recall_at_n": quality["split_metrics"]["held_out"]["retrieval_recall_at_n"],
                "precision_at_n": quality["split_metrics"]["held_out"]["retrieval_precision_at_n"],
            },
            "ranking": {
                "evaluation_scope": "held_out",
                "profiles": len(profiles),
                "top_n": observation["ranking_top_n"],
                "returned_count": observation["ranking_returned_count"],
                "eligible_count": observation["eligible_count"],
                "coverage": observation["ranking_returned_count"] / observation["eligible_count"] if observation["eligible_count"] else 0.0,
                "recall_at_n": quality["split_metrics"]["held_out"]["ranking_recall_at_n"],
                "precision_at_n": quality["split_metrics"]["held_out"]["ranking_precision_at_n"],
                "ndcg_at_n": quality["split_metrics"]["held_out"]["ranking_ndcg_at_n"],
                "split_metrics": quality["split_metrics"],
                "split_counts": observation["split_counts"],
                "language_split_counts": observation["language_split_counts"],
            },
            "calibration": {"count": observation["split_counts"]["calibration"]},
            "held_out": {"count": observation["split_counts"]["held_out"]},
            "cache": {
                "adapter": "replay_fingerprint_set",
                **cache_metrics,
                "hit_rate": cache_metrics["cache_hits"] / cache_total if cache_total else 0.0,
            },
            "llm": {"calls": 0, "retries": 0, "scoring_failure_count": cache_metrics["scoring_failure_count"]},
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
