from __future__ import annotations

import argparse
import hashlib
import json
import statistics
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock
from pathlib import Path

from fitcv import llm_runtime
from fitcv.llm_runtime import LlmTaskRequest
from fitcv.runtime_routing import LlmRouting


class _Server(ThreadingHTTPServer):
    def __init__(self, address: tuple[str, int]) -> None:
        super().__init__(address, _Handler)
        self.accepted = 0
        self.active = 0
        self.max_active = 0
        self.responses_fallback_remaining = 1
        self.lock = Lock()

    def get_request(self):
        request, address = super().get_request()
        with self.lock:
            self.accepted += 1
        return request, address


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        self.rfile.read(length)
        with self.server.lock:
            if self.path.endswith("/responses") and self.server.responses_fallback_remaining:
                self.server.responses_fallback_remaining -= 1
                self.send_response(404)
                self.send_header("Content-Length", "0")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                return
        with self.server.lock:
            self.server.active += 1
            self.server.max_active = max(self.server.max_active, self.server.active)
        payload = json.dumps({"output": [{"content": [{"text": "ok"}]}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Connection", "keep-alive")
        self.end_headers()
        self.wfile.write(payload)
        with self.server.lock:
            self.server.active -= 1

    def log_message(self, *_args) -> None:
        return


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warmup", type=int, default=1)
    parser.add_argument("--iterations", type=int, default=5)
    parser.add_argument("--requests-per-iteration", type=int, default=5)
    parser.add_argument("--output", required=True)
    parser.add_argument("--no-reuse", action="store_true")
    parser.add_argument("--source-commit", default="working-tree")
    parser.add_argument("--source-label", default="current-source")
    args = parser.parse_args()
    server = _Server(("127.0.0.1", 0))
    route = LlmRouting("openai_compatible", f"http://127.0.0.1:{server.server_port}/v1", "responses", "test", 5.0)
    request = LlmTaskRequest("ranking", "benchmark", "text")
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    pool = None if args.no_reuse else llm_runtime.LlmTransportPool()
    latencies: list[float] = []
    values: list[str] = []
    attempt_counts: list[int] = []
    try:
        for iteration in range(args.warmup + args.iterations):
            started = time.perf_counter()
            for _ in range(args.requests_per_iteration):
                if pool is None:
                    response = llm_runtime._openai_compatible_adapter(request, route, "benchmark-key")
                else:
                    response = llm_runtime._openai_compatible_adapter(request, route, "benchmark-key", transport_pool=pool)
                values.append(response.raw_text)
                attempt_counts.append(response.attempt_count)
            if iteration >= args.warmup:
                latencies.append((time.perf_counter() - started) * 1000)
    finally:
        retained = len(pool._clients) if pool is not None else 0
        if pool is not None:
            pool.close()
        server.shutdown()
        server.server_close()
    result = {
        "source_commit": args.source_commit,
        "source_label": args.source_label,
        "benchmark_command": " ".join(sys.argv),
        "benchmark_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "mode": "reuse" if pool is not None else "baseline",
        "warmup": args.warmup,
        "iterations": args.iterations,
        "requests_per_iteration": args.requests_per_iteration,
        "latency_ms": {"p50": statistics.median(latencies), "p95": max(latencies)},
        "accepted_tcp_connections": server.accepted,
        "worker_occupancy_max": server.max_active,
        "retries": sum(max(0, attempt_count - 1) for attempt_count in attempt_counts),
        "retained_client_identities": retained,
        "correctness_checksum": hashlib.sha256("".join(values).encode()).hexdigest(),
    }
    assert result["source_commit"]
    assert result["source_label"]
    assert result["benchmark_command"]
    assert len(result["benchmark_script_sha256"]) == 64
    with open(args.output, "w", encoding="utf-8") as output:
        json.dump(result, output, indent=2)
        output.write("\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
