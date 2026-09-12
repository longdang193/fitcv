"""Measure legacy versus production CV version listing overhead."""

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


def _seed(database_path: Path, versions: int) -> None:
    os.environ["FITCV_CP_SQLITE_PATH"] = str(database_path)
    created_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
    sqlite_store.insert_run(PipelineRun(
        run_id="run-benchmark",
        run_name="CV benchmark",
        status=RunStatus.SUCCEEDED,
        triggered_by="benchmark",
        trigger_source="benchmark",
        jobs_path="jobs.json",
        config_path="config.yaml",
        created_at=created_at,
        finished_at=created_at,
        total_jobs=1,
        passed_filter=1,
        ranked=1,
        cvs_generated=versions,
    ))
    with sqlite_store._sqlite_connection(database_path) as conn:
        sqlite_store._ensure_control_plane_schema(conn)
        conn.execute(
            """INSERT INTO run_jobs (
                run_job_id, run_id, source_index, source_fingerprint, source_snapshot_json,
                source_url, title, skills_json
            ) VALUES (?, ?, 0, ?, ?, ?, ?, '[]')""",
            ("job-benchmark", "run-benchmark", "source", "{}", "https://example.com/job", "Benchmark"),
        )
        content = b"# CV\n\nBenchmark content."
        checksum = sqlite_store.hashlib.sha256(content).hexdigest()
        for ordinal in range(1, versions + 1):
            conn.execute(
                """INSERT INTO cv_versions (
                    version_id, run_job_id, ordinal, generation_status, created_at,
                    content_length, content_checksum, content_blob, filename, media_type,
                    run_id, job_url, generated_at
                ) VALUES (?, ?, ?, 'generated', ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    f"cv-{ordinal}", "job-benchmark", ordinal, created_at.isoformat(),
                    len(content), checksum, content, f"cv-{ordinal}.md", "text/markdown; charset=utf-8",
                    "run-benchmark", "https://example.com/job", created_at.isoformat(),
                ),
            )
        conn.commit()


def _measure(query, versions: int, iterations: int) -> dict[str, object]:
    original_connect = sqlite_store.sqlite3.connect
    durations: list[float] = []
    counts: list[int] = []
    content_blob_selected: list[bool] = []
    baseline_response = query() if query is not sqlite_store.list_cv_versions else None

    def run_once() -> object:
        statements: list[str] = []

        def connect(*args: object, **kwargs: object):
            connection = original_connect(*args, **kwargs)
            connection.set_trace_callback(statements.append)
            return connection

        sqlite_store.sqlite3.connect = connect  # type: ignore[method-assign]
        try:
            started = time.perf_counter()
            response = query()
            durations.append((time.perf_counter() - started) * 1000)
        finally:
            sqlite_store.sqlite3.connect = original_connect  # type: ignore[method-assign]
        sql = [statement for statement in statements if not statement.lstrip().upper().startswith("PRAGMA")]
        counts.append(len(sql))
        content_blob_selected.append(any(
            "content_blob" in statement.lower() or "select * from cv_versions" in statement.lower()
            for statement in sql
        ))
        return response

    for _ in range(iterations):
        response = run_once()
        if baseline_response is None:
            baseline_response = response
    return {
        "versions": versions,
        "sql_statements": max(counts),
        "content_blob_selected": any(content_blob_selected),
        "latency_ms": {"p50": statistics.median(durations), "p95": _percentile(durations, 0.95)},
        "response": baseline_response,
    }


def _legacy_list() -> list[dict[str, object]]:
    with sqlite_store._sqlite_connection(Path(os.environ["FITCV_CP_SQLITE_PATH"])) as conn:
        conn.row_factory = sqlite_store.sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM cv_versions WHERE run_job_id=? ORDER BY ordinal DESC, created_at DESC, version_id DESC",
            ("job-benchmark",),
        ).fetchall()
        return [sqlite_store._cv_projection(conn, row) for row in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--versions", default="1,10,100")
    parser.add_argument("--warmup-iterations", type=int, default=5)
    parser.add_argument("--measured-iterations", type=int, default=30)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    versions = [int(value.strip()) for value in args.versions.split(",") if value.strip()]
    if not versions or any(value < 1 for value in versions):
        parser.error("versions must contain positive integers")
    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="fitcv-cv-versions-") as directory:
        for count in versions:
            database_path = Path(directory) / f"versions-{count}.sqlite3"
            _seed(database_path, count)
            for _ in range(args.warmup_iterations):
                _legacy_list()
                sqlite_store.list_cv_versions("job-benchmark")
            legacy = _measure(_legacy_list, count, args.measured_iterations)
            optimized = _measure(lambda: sqlite_store.list_cv_versions("job-benchmark"), count, args.measured_iterations)
            results.append({
                "versions": count,
                "baseline": {key: value for key, value in legacy.items() if key != "response"},
                "optimized": {key: value for key, value in optimized.items() if key != "response"},
                "response_equal": legacy["response"] == optimized["response"],
            })
    result = {
        "schema_version": "cv_versions_benchmark_v1",
        "results": results,
        "warmup_iterations": args.warmup_iterations,
        "measured_iterations": args.measured_iterations,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
