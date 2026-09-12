"""Benchmark production Runs-list queries against synthetic SQLite data."""

from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv_cp import sqlite_store
from fitcv_cp.models import PipelineRun, RunStatus


def _percentile(values: list[float], percentile: float) -> float:
    return sorted(values)[max(0, math.ceil(percentile * len(values)) - 1)]


def _run(index: int) -> PipelineRun:
    created_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=index)
    return PipelineRun(
        run_id=f"run-{index:05d}",
        run_name=f"Run {index}",
        status=RunStatus.SUCCEEDED,
        triggered_by="benchmark",
        trigger_source="benchmark",
        jobs_path="jobs.json",
        config_path="config.yaml",
        created_at=created_at,
        finished_at=created_at,
        total_jobs=10,
        passed_filter=5,
        rejected_jobs=5,
        cvs_generated=2,
        progress_completed=10,
        progress_total=10,
        archived_at=created_at if index % 5 == 0 else None,
    )


def _seed(database_path: Path, size: int) -> None:
    os.environ["FITCV_CP_SQLITE_PATH"] = str(database_path)
    sqlite_store.insert_run(_run(0))
    with sqlite_store._sqlite_connection(database_path) as connection:
        connection.row_factory = sqlite_store.sqlite3.Row
        sqlite_store._ensure_control_plane_schema(connection)
        for index in range(1, size):
            sqlite_store._write_normalized_run(connection, _run(index), insert=True)
        connection.commit()


def _query() -> tuple[dict[str, object], dict[str, int]]:
    statements: list[str] = []
    progress_steps = [0]
    original_connect = sqlite_store.sqlite3.connect

    def connect(*args: object, **kwargs: object):
        connection = original_connect(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        connection.set_progress_handler(lambda: progress_steps.__setitem__(0, progress_steps[0] + 1) or 0, 1000)
        return connection

    sqlite_store.sqlite3.connect = connect  # type: ignore[method-assign]
    try:
        started = time.perf_counter()
        response = sqlite_store.query_runs(view="active", page=2, page_size=20)
        elapsed_ms = (time.perf_counter() - started) * 1000
    finally:
        sqlite_store.sqlite3.connect = original_connect  # type: ignore[method-assign]

    sql = [statement for statement in statements if not statement.lstrip().upper().startswith("PRAGMA")]
    return response, {
        "sql_statements": len(sql),
        "rows_returned": len(response["items"]),
        "progress_callbacks": progress_steps[0],
        "latency_ms": elapsed_ms,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sizes", default="100,1000,10000")
    parser.add_argument("--warmup-iterations", type=int, default=1)
    parser.add_argument("--measured-iterations", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if args.warmup_iterations < 0 or args.measured_iterations < 1:
        parser.error("iterations must be warmup >= 0 and measured >= 1")
    sizes = [int(value.strip()) for value in args.sizes.split(",") if value.strip()]
    if not sizes or any(size < 1 for size in sizes):
        parser.error("sizes must contain positive integers")

    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="fitcv-runs-benchmark-") as directory:
        for size in sizes:
            database_path = Path(directory) / f"runs-{size}.sqlite3"
            _seed(database_path, size)
            for _ in range(args.warmup_iterations):
                _query()
            baseline, _ = _query()
            durations: list[float] = []
            sql_counts: list[int] = []
            rows_returned: list[int] = []
            progress_counts: list[int] = []
            response_equal = True
            for _ in range(args.measured_iterations):
                current, metrics = _query()
                durations.append(float(metrics["latency_ms"]))
                sql_counts.append(int(metrics["sql_statements"]))
                rows_returned.append(int(metrics["rows_returned"]))
                progress_counts.append(int(metrics["progress_callbacks"]))
                response_equal = response_equal and current == baseline
            results.append(
                {
                    "size": size,
                    "sql_statements": max(sql_counts),
                    "rows_read": None,
                    "rows_returned": max(rows_returned),
                    "progress_callbacks": max(progress_counts),
                    "latency_ms": {
                        "p50": statistics.median(durations),
                        "p95": _percentile(durations, 0.95),
                    },
                    "response_equal": response_equal,
                    "rows_read_note": "stdlib sqlite3 exposes no exact row-visit counter; query path is production query_runs",
                }
            )

    result = {
        "schema_version": "runs_list_benchmark_v2",
        "query": "fitcv_cp.sqlite_store.query_runs(view='active', page=2, page_size=20)",
        "sizes": results,
        "warmup_iterations": args.warmup_iterations,
        "measured_iterations": args.measured_iterations,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
