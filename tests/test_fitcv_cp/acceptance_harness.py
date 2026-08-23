"""Test-owned controls and disposable fixtures for FitCV Local acceptance."""

from __future__ import annotations

import hashlib
import json
import threading
import uuid
from datetime import datetime, timezone
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable, TypeVar

from fitcv_cp import sqlite_store

_Result = TypeVar("_Result")


class ControlledLocalJobExecutor:
    """Serialize one Local job while allowing deterministic acceptance races."""

    def __init__(self) -> None:
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="fitcv-acceptance")
        self._lock = threading.Lock()
        self._release = threading.Event()
        self._submitted = threading.Event()
        self._active: Future[Any] | None = None
        self._released = False
        self._failure: BaseException | None = None

    def submit(self, function: Callable[..., _Result], *args: object) -> Future[_Result]:
        with self._lock:
            if self._active is not None and not self._active.done():
                raise RuntimeError("acceptance executor already owns active work")
            self._submitted.clear()
            self._release.clear()
            self._released = False

            def run() -> _Result:
                self._submitted.set()
                self._release.wait()
                if self._failure is not None:
                    raise self._failure
                return function(*args)

            self._active = self._executor.submit(run)
            return self._active

    def fail_next(self, error: BaseException) -> None:
        with self._lock:
            if self._active is None or self._active.done():
                raise RuntimeError("acceptance job was not submitted")
            self._failure = error

    def wait_submitted(self, timeout: float = 10.0) -> None:
        if not self._submitted.wait(timeout):
            raise TimeoutError("acceptance job was not submitted")

    def release(self) -> None:
        with self._lock:
            if self._released:
                raise RuntimeError("acceptance job was already released")
            self._released = True
            self._release.set()

    def result(self, timeout: float = 120.0) -> Any:
        with self._lock:
            future = self._active
        if future is None:
            raise RuntimeError("acceptance job was not submitted")
        return future.result(timeout=timeout)

    def shutdown(self) -> None:
        if self._active is not None and not self._active.done():
            self._release.set()
        self._executor.shutdown(wait=True, cancel_futures=False)

    def __enter__(self) -> "ControlledLocalJobExecutor":
        return self

    def __exit__(self, _exc_type: object, _exc: object, _traceback: object) -> None:
        self.shutdown()


def create_scan_fixture(
    database_path: Path,
    *,
    scan_name: str,
    jobs: list[dict[str, Any]],
) -> dict[str, Any]:
    company = sqlite_store.create_tracked_company(
        company_name=f"Acceptance {scan_name} Company",
        careers_url=f"https://acceptance.example/{hashlib.sha256(scan_name.encode()).hexdigest()[:12]}",
        provider_id="fixture",
        provider_label="Acceptance Fixture",
        database_path=database_path,
    )
    scan = sqlite_store.create_scan(
        request={
            "scan_name": scan_name,
            "company_ids": [company["company_id"]],
            "job_titles": [],
            "locations": [],
            "published_window": "any",
            "total_rows": len(jobs),
        },
        database_path=database_path,
    )
    output_json = sqlite_store.canonicalize_jobs(jobs).json_text
    sqlite_store.commit_scan_output(scan["scan_id"], output_json=output_json, database_path=database_path)
    return sqlite_store.get_scan_detail(scan["scan_id"], database_path=database_path) or {}


def create_profile_fixture(database_path: Path, canonical: dict[str, Any]) -> dict[str, Any]:
    profile_id = f"profile-acceptance-{uuid.uuid4().hex[:12]}"
    revision_id = f"profile_revision_{uuid.uuid4().hex}"
    now = datetime.now(timezone.utc).isoformat()
    profile_json = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    checksum = sqlite_store.canonical_candidate_checksum(canonical)
    with sqlite_store._sqlite_connection(database_path) as connection:
        connection.execute(
            """
            INSERT INTO candidate_profiles (
                candidate_profile_id, profile_name, original_filename, media_type, byte_length,
                input_checksum, creation_status, lifecycle, failure_code, failure_message,
                is_default, sort_order, created_at, updated_at, archived_at, revision
            ) VALUES (?, ?, ?, ?, ?, ?, 'succeeded', 'active', NULL, NULL, 0, 0, ?, ?, NULL, 1)
            """,
            (profile_id, "Acceptance P0 Profile", "acceptance-profile.json", "application/json", len(profile_json), checksum, now, now),
        )
        connection.execute(
            """
            INSERT INTO candidate_profile_revisions (
                profile_revision_id, candidate_profile_id, revision, profile_json,
                checksum, schema_revision, created_at
            ) VALUES (?, ?, 1, ?, ?, 'candidate-profile.v2', ?)
            """,
            (revision_id, profile_id, profile_json, checksum, now),
        )
        connection.commit()
    return sqlite_store.get_candidate_profile(profile_id, database_path=database_path) or {}
