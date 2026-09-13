"""Benchmark local /runs endpoint projection against deterministic SQLite state."""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fastapi.testclient import TestClient

from fitcv_cp import sqlite_store
from fitcv_cp.app import create_app
from fitcv_cp.models import PipelineRun, RunStatus


def _percentile(values: list[float], percentile: float) -> float:
    return sorted(values)[max(0, math.ceil(percentile * len(values)) - 1)]


def _run(index: int) -> PipelineRun:
    created_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc) + datetime.timedelta(seconds=index)
    status = RunStatus.SUCCEEDED
    return PipelineRun(
        run_id=f"run-{index:05d}",
        run_name=f"Run {index}",
        status=status,
        triggered_by="benchmark",
        trigger_source="benchmark",
        jobs_path="jobs.json",
        config_path="config.yaml",
        created_at=created_at,
        started_at=created_at,
        finished_at=created_at,
        total_jobs=10,
        passed_filter=5,
        rejected_jobs=5,
        cvs_generated=2,
        progress_completed=10,
        progress_total=10,
        archived_at=created_at if status == RunStatus.SUCCEEDED and index % 5 == 0 else None,
    )


def _seed(database_path: Path, size: int) -> None:
    os.environ["FITCV_CP_SQLITE_PATH"] = str(database_path)
    sqlite_store.initialize_control_plane_database(
        database_path,
        database_path.with_name("missing-candidate-profile.yaml"),
    )
    sqlite_store.insert_run(_run(0))
    with sqlite_store._sqlite_connection(database_path) as connection:
        connection.row_factory = sqlite_store.sqlite3.Row
        sqlite_store._ensure_control_plane_schema(connection)
        for index in range(1, size):
            sqlite_store._write_normalized_run(connection, _run(index), insert=True)
        connection.commit()


def _checksum(payload: bytes) -> str:
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return hashlib.sha256(payload).hexdigest()
    if isinstance(data, dict):
        meta = data.get("meta")
        if isinstance(meta, dict):
            meta.pop("server_time", None)
    canonical = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _request(client: TestClient, page_size: int) -> tuple[dict[str, Any], dict[str, Any]]:
    statements: list[str] = []
    original_connect = sqlite_store.sqlite3.connect

    def connect(*args: object, **kwargs: object):
        connection = original_connect(*args, **kwargs)
        connection.set_trace_callback(statements.append)
        return connection

    sqlite_store.sqlite3.connect = connect  # type: ignore[method-assign]
    try:
        started = time.perf_counter()
        response = client.get("/runs", params={"view": "all", "page": 1, "page_size": page_size})
        elapsed_ms = (time.perf_counter() - started) * 1000
    finally:
        sqlite_store.sqlite3.connect = original_connect  # type: ignore[method-assign]
    sql_statements = [statement for statement in statements if not statement.lstrip().upper().startswith("PRAGMA")]
    payload = response.content
    try:
        body = response.json()
    except ValueError:
        body = {}
    error = body.get("detail") if isinstance(body, dict) else None
    return body, {
        "status_code": response.status_code,
        "error": error,
        "latency_ms": elapsed_ms,
        "sql_query_count": len(sql_statements),
        "response_bytes": len(payload),
        "correctness_checksum": _checksum(payload),
        "returned_count": len(body.get("data", [])) if isinstance(body, dict) else 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", default="20,100,500")
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    sizes = [int(value.strip()) for value in str(args.runs).split(",") if value.strip()]
    if not sizes or any(size < 1 for size in sizes):
        parser.error("runs must contain positive integers")
    if args.warmup < 0 or args.iterations < 1:
        parser.error("warmup must be >= 0 and iterations must be >= 1")

    results: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="fitcv-runs-endpoint-") as directory:
        for size in sizes:
            database_path = Path(directory) / f"runs-{size}.sqlite3"
            _seed(database_path, max(500, size))
            app = create_app(redis_url="redis://localhost:6379/0")
            with TestClient(app) as client:
                for _ in range(args.warmup):
                    _request(client, size)
                baseline, baseline_metrics = _request(client, size)
                measurements: list[dict[str, Any]] = []
                for _ in range(args.iterations):
                    current, metrics = _request(client, size)
                    metrics["response_equal"] = (
                        current == baseline
                        or metrics["correctness_checksum"] == baseline_metrics["correctness_checksum"]
                    )
                    measurements.append(metrics)
            results.append(
                {
                    "page_size": size,
                    "status_code": measurements[-1]["status_code"],
                    "error": measurements[-1]["error"],
                    "returned_count": measurements[-1]["returned_count"],
                    "response_bytes": measurements[-1]["response_bytes"],
                    "correctness_checksum": measurements[-1]["correctness_checksum"],
                    "response_equal": all(bool(item["response_equal"]) for item in measurements),
                    "sql_query_count": max(int(item["sql_query_count"]) for item in measurements),
                    "latency_ms": {
                        "p50": statistics.median(float(item["latency_ms"]) for item in measurements),
                        "p95": _percentile([float(item["latency_ms"]) for item in measurements], 0.95),
                    },
                }
            )

    result = {
        "schema_version": "runs_endpoint_benchmark_v1",
        "endpoint": "/runs",
        "view": "all",
        "page": 1,
        "warmup": args.warmup,
        "iterations": args.iterations,
        "runs": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
