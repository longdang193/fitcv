"""Benchmark Pipeline Results selection against disposable SQLite fixtures."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import statistics
import tempfile
import time
import tracemalloc
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-sizes", default="100,1000,5000")
    parser.add_argument("--filters", default="all,title,search,result")
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def _fixture_jobs(size: int) -> list[dict[str, Any]]:
    titles = (
        "Working Student – AI Analytics",
        "Duales Studium – AI Engineering",
        "Retail Analytics Intern",
        "AI/ML Engineer",
    )
    return [
        {
            "title": titles[index % len(titles)],
            "job_url": f"https://jobs.example.test/{index}",
            "company": f"Company {index % 25}",
            "location": "Berlin",
            "required_skills": ["Python", "SQL"],
            "description": "Analytics platform role",
        }
        for index in range(size)
    ]


def _filter_arguments(filter_name: str) -> dict[str, Any]:
    if filter_name == "all":
        return {"stage": "all", "result_bucket": "all"}
    if filter_name == "title":
        return {
            "stage": "all",
            "result_bucket": "all",
            "job_title_include": ["AI"],
            "job_title_exclude": ["duales"],
        }
    if filter_name == "search":
        return {"stage": "all", "result_bucket": "all", "search": "analytics"}
    if filter_name == "result":
        return {"stage": "screening", "result_bucket": "passed"}
    raise ValueError(f"unsupported filter: {filter_name}")


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    if not ordered:
        return 0.0
    position = (len(ordered) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * weight


def _create_fixture(store: Any, run_id: str, size: int) -> None:
    from fitcv_cp.models import PipelineRun, RunStatus

    jobs = _fixture_jobs(size)
    run = PipelineRun(
        run_id=run_id,
        status=RunStatus.SUCCEEDED,
        triggered_by="benchmark",
        trigger_source="benchmark",
        jobs_path="benchmark.json",
        config_path="benchmark.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
    )
    store.create_run_bundle(
        run,
        input_resource={
            "original_filename": "benchmark.json",
            "media_type": "application/json",
            "jobs_snapshot_json": json.dumps(jobs),
            "jobs_manifest_json": "{}",
            "candidate_profile_name": "Benchmark",
            "candidate_profile_json": "{}",
            "settings_revision": "benchmark",
            "settings_snapshot_json": "{}",
        },
        jobs=jobs,
    )
    run_job_ids = store.list_run_job_ids_for_run(run_id)
    with store._sqlite_connection(Path(store._local_sqlite_path())) as conn:
        conn.executemany(
            """INSERT INTO run_job_stage_results
               (run_job_id, stage_id, status, outcome_code, reason_code, evidence_json)
               VALUES (?, 'screening', ?, ?, ?, '{}')""",
            [
                (
                    run_job_id,
                    "passed" if index % 2 == 0 else "rejected",
                    "passed" if index % 2 == 0 else "rejected",
                    "benchmark",
                )
                for index, run_job_id in enumerate(run_job_ids)
            ],
        )
        conn.commit()


def _all_selected_ids(store: Any, run_id: str, arguments: dict[str, Any]) -> list[str]:
    return [
        str(row["run_job_id"])
        for row in store.iter_run_jobs_for_export(run_id, sort="score_desc", **arguments)
    ]


def _query_page_ids(store: Any, run_id: str, arguments: dict[str, Any]) -> list[str]:
    page = 1
    result: list[str] = []
    while True:
        page_result = store.query_run_jobs(
            run_id,
            page=page,
            page_size=50,
            sort="score_desc",
            **arguments,
        )
        items = list(page_result.get("items") or [])
        result.extend(str(row["run_job_id"]) for row in items)
        if not items or len(result) >= int(page_result.get("total") or 0):
            return result
        page += 1


def _measure(store: Any, run_id: str, arguments: dict[str, Any]) -> dict[str, Any]:
    query_count = {"value": 0}
    original_connection = store._sqlite_connection

    @contextmanager
    def counted_connection(*args: Any, **kwargs: Any) -> Iterator[Any]:
        with original_connection(*args, **kwargs) as conn:
            conn.set_trace_callback(lambda _statement: query_count.__setitem__("value", query_count["value"] + 1))
            yield conn

    store._sqlite_connection = counted_connection
    try:
        tracemalloc.start()
        started = time.perf_counter()
        result = store.query_run_jobs(
            run_id,
            page=1,
            page_size=50,
            sort="score_desc",
            **arguments,
        )
        elapsed_ms = (time.perf_counter() - started) * 1000
        _current, peak_bytes = tracemalloc.get_traced_memory()
        tracemalloc.stop()
    finally:
        store._sqlite_connection = original_connection
    return {
        "latency_ms": elapsed_ms,
        "query_count": query_count["value"],
        "peak_memory_bytes": peak_bytes,
        "rows": len(result.get("items") or []),
    }


def main() -> None:
    args = _parse_args()
    fixture_sizes = [int(value) for value in str(args.fixture_sizes).split(",") if value.strip()]
    filter_names = [value.strip() for value in str(args.filters).split(",") if value.strip()]
    if args.warmups < 0 or args.iterations <= 0:
        raise ValueError("warmups must be >= 0 and iterations must be > 0")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="fitcv-pipeline-results-benchmark-") as temp_dir:
        os.environ["FITCV_CP_SQLITE_PATH"] = str(Path(temp_dir) / "benchmark.sqlite3")
        from fitcv_cp import sqlite_store as store

        with store._sqlite_connection(Path(os.environ["FITCV_CP_SQLITE_PATH"])) as conn:
            store._ensure_control_plane_schema(conn)
            conn.commit()
        benchmarks: list[dict[str, Any]] = []
        for size in fixture_sizes:
            run_id = f"benchmark-{size}"
            _create_fixture(store, run_id, size)
            for filter_name in filter_names:
                filter_arguments = _filter_arguments(filter_name)
                expected_ids = _all_selected_ids(store, run_id, filter_arguments)
                actual_ids = _query_page_ids(store, run_id, filter_arguments)
                if actual_ids != expected_ids:
                    raise AssertionError(f"selector mismatch for {size}/{filter_name}")
                measurements = []
                for _ in range(args.warmups):
                    _measure(store, run_id, filter_arguments)
                for _ in range(args.iterations):
                    measurements.append(_measure(store, run_id, filter_arguments))
                benchmarks.append(
                    {
                        "fixture_size": size,
                        "filter": filter_name,
                        "selected_rows": len(expected_ids),
                        "correctness": "pass",
                        "p50_latency_ms": _percentile([item["latency_ms"] for item in measurements], 0.50),
                        "p95_latency_ms": _percentile([item["latency_ms"] for item in measurements], 0.95),
                        "query_count": statistics.median(item["query_count"] for item in measurements),
                        "peak_memory_bytes": max(item["peak_memory_bytes"] for item in measurements),
                    }
                )

    output_path.write_text(
        json.dumps(
            {
                "benchmark": "pipeline_results",
                "fixture_sizes": fixture_sizes,
                "filters": filter_names,
                "warmups": args.warmups,
                "iterations": args.iterations,
                "results": benchmarks,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(output_path), "results": len(benchmarks)}))


if __name__ == "__main__":
    main()
