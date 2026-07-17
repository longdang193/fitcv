from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import time
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from fitcv_cp.local_credentials import get_credential


REPO_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_ROOT = Path(__file__).resolve().parent
BUNDLE_ROOT = REPO_ROOT / "dist" / "fitcv-local"
EXECUTABLE = BUNDLE_ROOT / "fitcv-local.exe"
SOURCE_INPUT = REPO_ROOT / "artifacts" / "packaged_admissible_live_20260717" / "admissible-input.json"
BOOTSTRAP_PATH = Path(os.environ["APPDATA"]) / "FitCV" / "bootstrap.json"
PROMPT_CANARY = "FITCV_PROMPT_CANARY_20260717_KEEP_DIRECT_EVIDENCE"
TERMINAL_STATUSES = {"succeeded", "failed", "cancelled", "awaiting_continue"}


def write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def read_json(path: Path) -> Any:`n    return json.loads(path.read_text(encoding="utf-8-sig"))


def wait_for_runtime(process: subprocess.Popen[bytes], timeout_seconds: float = 20.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"FitCV Local exited early with code {process.returncode}")
        if BOOTSTRAP_PATH.exists():
            bootstrap = read_json(BOOTSTRAP_PATH)
            runtime_path = Path(bootstrap["data_root"]) / ".fitcv-local-runtime.json"
            if runtime_path.exists():
                runtime = read_json(runtime_path)
                if int(runtime.get("pid") or 0) == process.pid:
                    return {**runtime, "data_root": bootstrap["data_root"]}
        time.sleep(0.1)
    raise TimeoutError("PID-bound FitCV Local runtime metadata not created")


def request_headers(session: requests.Session, base_url: str) -> dict[str, str]:
    token = session.cookies.get("fitcv_csrf")
    if not token:
        raise RuntimeError("fitcv_csrf cookie missing")
    origin = f"{urlparse(base_url).scheme}://{urlparse(base_url).netloc}"
    return {"Origin": origin, "X-FitCV-CSRF": token}


def save_controller(session: requests.Session, base_url: str, headers: dict[str, str]) -> None:
    form = {
        "controller_settings_present": "1",
        "provider_id": "openai_compatible",
        "base_url": "http://host.docker.internal:20128/v1",
        "auth_mode": "required",
        "wire_api": "chat_completions",
        "timeout_seconds": "300",
        "default_model": "cx/gpt-5.4-mini",
        "enrich_extraction": "cx/gpt-5.4-mini",
        "ranking_ai_score": "cx/gpt-5.4-mini",
        "cv_generation_structured_write": "cx/gpt-5.4-mini",
        "synonym_triage_recommendation": "cx/gpt-5.4-mini",
        "retry_max_attempts": "1",
        "retry_backoff_seconds": "1,2,4,8",
        "retry_lease_seconds": "900",
        "retry_reconciler_interval_seconds": "0",
        "retry_error_details_max_chars": "2048",
        "prompt_addendum_enrich_extraction": PROMPT_CANARY,
        "prompt_addendum_ranking_ai_score": "",
        "prompt_addendum_cv_generation_structured_write": "",
        "prompt_addendum_synonym_triage_recommendation": "",
    }
    response = session.post(
        urljoin(base_url, "local/onboarding/provider"),
        data=form,
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    provider_test = session.post(
        urljoin(base_url, "local/onboarding/provider/test"),
        data=form,
        headers=headers,
        timeout=60,
    )
    provider_test.raise_for_status()
    if not provider_test.json().get("ok"):
        raise RuntimeError(f"Provider test failed: {provider_test.text}")


def reset_prompt(session: requests.Session, base_url: str, headers: dict[str, str]) -> None:
    response = session.post(
        urljoin(base_url, "local/onboarding/controller/reset"),
        data={"scope": "prompt:enrich_extraction"},
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()


def fresh_input(label: str) -> Path:
    rows = read_json(SOURCE_INPUT)
    marker = f"{label}-{time.time_ns()}"
    rows[0]["jobUrl"] = f"https://example.test/fitcv-controller-prompt-{marker}"
    rows[0]["description"] = f"{rows[0]['description']} Verification marker: {marker}."
    output = EVIDENCE_ROOT / f"input-{label}.json"
    write_json(output, rows)
    return output


def submit_run(
    session: requests.Session,
    base_url: str,
    headers: dict[str, str],
    input_path: Path,
    label: str,
) -> str:
    response = session.post(
        urljoin(base_url, "runs"),
        json={
            "jobs_path": str(input_path.resolve()),
            "config_path": ".env.yaml",
            "triggered_by": f"codex-controller-prompt-{label}",
            "config_overrides": {},
            "run_mode": "run_all",
        },
        headers=headers,
        timeout=30,
    )
    response.raise_for_status()
    return str(response.json()["run_id"])


def wait_for_run(
    session: requests.Session,
    base_url: str,
    run_id: str,
    timeout_seconds: float = 480.0,
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        response = session.get(urljoin(base_url, f"runs/{run_id}"), timeout=30)
        response.raise_for_status()
        payload = response.json()
        if str(payload.get("status") or "").lower() in TERMINAL_STATUSES:
            time.sleep(3)
            return payload
        time.sleep(2)
    raise TimeoutError(f"Run {run_id} did not reach terminal state")


def fetch_run_surfaces(
    session: requests.Session,
    base_url: str,
    run_id: str,
) -> dict[str, Any]:
    endpoints = {
        "run": f"runs/{run_id}",
        "events": f"runs/{run_id}/events",
        "stage_artifacts": f"admin/runs/{run_id}/stage-artifacts.json",
        "settings_used": f"admin/runs/{run_id}/settings-used.json",
        "export": f"admin/runs/{run_id}/export.json",
        "cv_debug": f"admin/runs/{run_id}/cv-debug.json",
    }
    surfaces: dict[str, Any] = {}
    for name, endpoint in endpoints.items():
        response = session.get(urljoin(base_url, endpoint), timeout=60)
        surfaces[name] = {
            "status_code": response.status_code,
            "content_type": response.headers.get("content-type", ""),
            "text": response.text,
        }
    return surfaces


def json_values(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        if "prompt_customized" in value:
            found.append(value)
        for prefix in ("enrich", "ranking", "cv"):
            customized_key = f"{prefix}_prompt_customized"
            if customized_key in value:
                found.append(
                    {
                        "prompt_customized": value[customized_key],
                        "prompt_addendum_sha256": value.get(
                            f"{prefix}_prompt_addendum_sha256"
                        ),
                        "prompt_addendum_char_count": value.get(
                            f"{prefix}_prompt_addendum_char_count", 0
                        ),
                    }
                )
        for child in value.values():
            found.extend(json_values(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(json_values(child))
    return found


def prompt_metadata(surfaces: dict[str, Any]) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for surface in surfaces.values():
        if surface["status_code"] != 200:
            continue
        try:
            found.extend(json_values(json.loads(surface["text"])))
        except json.JSONDecodeError:
            continue
    return found


def scan_run_artifacts(data_root: Path, run_id: str, forbidden: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for root in (data_root / "artifacts", data_root / "exports", data_root / "logs"):
        if not root.exists():
            continue
        for candidate in root.rglob("*"):
            if not candidate.is_file():
                continue
            if run_id not in str(candidate) and root.name != "logs":
                continue
            raw = candidate.read_bytes()
            for value in forbidden:
                if value and value.encode("utf-8") in raw:
                    hits.append(str(candidate.relative_to(data_root)))
    return sorted(set(hits))


def save_surfaces(label: str, surfaces: dict[str, Any]) -> None:
    output_dir = EVIDENCE_ROOT / label
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, surface in surfaces.items():
        suffix = ".json" if "json" in surface["content_type"] else ".txt"
        (output_dir / f"{name}{suffix}").write_text(surface["text"], encoding="utf-8")


def verify_run(
    *,
    label: str,
    run: dict[str, Any],
    surfaces: dict[str, Any],
    data_root: Path,
    credential: str,
    expected_customized: bool,
) -> dict[str, Any]:
    status = str(run.get("status") or "").lower()
    if status not in {"succeeded", "awaiting_continue"}:
        raise AssertionError(f"{label} run failed: {run.get('error_stage')} {run.get('error_message')}")
    combined = "\n".join(surface["text"] for surface in surfaces.values())
    if PROMPT_CANARY in combined:
        raise AssertionError(f"Raw prompt canary leaked into {label} HTTP run surfaces")
    if credential and credential in combined:
        raise AssertionError(f"Credential leaked into {label} HTTP run surfaces")
    metadata = prompt_metadata(surfaces)
    expected_hash = hashlib.sha256(PROMPT_CANARY.encode("utf-8")).hexdigest()
    if expected_customized:
        matches = [
            item
            for item in metadata
            if item.get("prompt_customized") is True
            and item.get("prompt_addendum_sha256") == expected_hash
            and int(item.get("prompt_addendum_char_count") or 0) == len(PROMPT_CANARY)
        ]
        if not matches:
            raise AssertionError("Customized prompt hash-only provenance missing")
    else:
        if any(item.get("prompt_addendum_sha256") == expected_hash for item in metadata):
            raise AssertionError("Reset run retained customized prompt hash")
        false_entries = [item for item in metadata if item.get("prompt_customized") is False]
        if not false_entries:
            raise AssertionError("Reset run default prompt provenance missing")
    disk_hits = scan_run_artifacts(data_root, str(run["run_id"]), (PROMPT_CANARY, credential))
    if disk_hits:
        raise AssertionError(f"Secret or prompt canary leaked to run artifacts: {disk_hits}")
    return {
        "run_id": run["run_id"],
        "status": run["status"],
        "total_jobs": run.get("total_jobs"),
        "passed_filter": run.get("passed_filter"),
        "ranked": run.get("ranked"),
        "cvs_generated": run.get("cvs_generated"),
        "error_stage": run.get("error_stage"),
        "error_message": run.get("error_message"),
        "prompt_customized": expected_customized,
        "prompt_metadata_records": len(metadata),
        "prompt_addendum_sha256": expected_hash if expected_customized else None,
        "prompt_addendum_char_count": len(PROMPT_CANARY) if expected_customized else 0,
    }


def main() -> None:
    if not EXECUTABLE.exists():
        raise FileNotFoundError(EXECUTABLE)
    credential = get_credential("openai_compatible") or ""
    if not credential:
        raise RuntimeError("Stored openai_compatible credential is required for packaged live verification")
    EVIDENCE_ROOT.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["FITCV_NO_BROWSER"] = "1"
    process = subprocess.Popen(
        [str(EXECUTABLE)],
        env=environment,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )
    overlay_path: Path | None = None
    overlay_existed = False
    overlay_bytes = b""
    session = requests.Session()
    summary: dict[str, Any] = {}
    try:
        runtime = wait_for_runtime(process)
        base_url = str(runtime["url"])
        data_root = Path(runtime["data_root"])
        overlay_path = data_root / "config" / "local_controller_overlay.yaml"
        overlay_existed = overlay_path.exists()
        overlay_bytes = overlay_path.read_bytes() if overlay_existed else b""
        health = session.get(urljoin(base_url, "healthz"), timeout=10)
        health.raise_for_status()
        onboarding = session.get(urljoin(base_url, "local/onboarding"), timeout=30)
        onboarding.raise_for_status()
        if onboarding.headers.get("cache-control") != "no-store":
            raise AssertionError("Onboarding settings response is not Cache-Control: no-store")
        headers = request_headers(session, base_url)
        readiness = session.get(urljoin(base_url, "local/readiness"), timeout=30)
        readiness.raise_for_status()
        save_controller(session, base_url, headers)
        readiness = session.get(urljoin(base_url, "local/readiness"), timeout=30)
        readiness.raise_for_status()
        if not readiness.json().get("ready"):
            raise RuntimeError(f"FitCV Local not ready after provider test: {readiness.text}")
        customized_page = session.get(urljoin(base_url, "local/onboarding"), timeout=30)
        customized_page.raise_for_status()
        if PROMPT_CANARY not in customized_page.text:
            raise AssertionError("Customized prompt missing from loopback settings response")
        if customized_page.headers.get("cache-control") != "no-store":
            raise AssertionError("Customized settings response is not no-store")
        if not overlay_path.exists() or PROMPT_CANARY not in overlay_path.read_text(encoding="utf-8"):
            raise AssertionError("Customized prompt missing from controller overlay")
        custom_input = fresh_input("customized")
        custom_run_id = submit_run(session, base_url, headers, custom_input, "customized")
        custom_run = wait_for_run(session, base_url, custom_run_id)
        custom_run["run_id"] = custom_run_id
        custom_surfaces = fetch_run_surfaces(session, base_url, custom_run_id)
        custom_summary = verify_run(
            label="customized",
            run=custom_run,
            surfaces=custom_surfaces,
            data_root=data_root,
            credential=credential,
            expected_customized=True,
        )
        save_surfaces("customized", custom_surfaces)
        reset_prompt(session, base_url, headers)
        reset_page = session.get(urljoin(base_url, "local/onboarding"), timeout=30)
        reset_page.raise_for_status()
        if PROMPT_CANARY in reset_page.text:
            raise AssertionError("Prompt reset did not clear loopback settings response")
        if overlay_path.exists() and PROMPT_CANARY in overlay_path.read_text(encoding="utf-8"):
            raise AssertionError("Prompt reset did not clear controller overlay")
        reset_input = fresh_input("reset")
        reset_run_id = submit_run(session, base_url, headers, reset_input, "reset")
        reset_run = wait_for_run(session, base_url, reset_run_id)
        reset_run["run_id"] = reset_run_id
        reset_surfaces = fetch_run_surfaces(session, base_url, reset_run_id)
        reset_summary = verify_run(
            label="reset",
            run=reset_run,
            surfaces=reset_surfaces,
            data_root=data_root,
            credential=credential,
            expected_customized=False,
        )
        save_surfaces("reset", reset_surfaces)
        sqlite_path = data_root / "fitcv.sqlite3"
        with sqlite3.connect(sqlite_path) as connection:
            integrity = connection.execute("PRAGMA integrity_check").fetchone()[0]
            foreign_key_violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if integrity != "ok" or foreign_key_violations:
            raise AssertionError("SQLite integrity verification failed")
        database_bytes = sqlite_path.read_bytes()
        if PROMPT_CANARY.encode("utf-8") in database_bytes:
            raise AssertionError("Raw prompt canary leaked into SQLite")
        if credential.encode("utf-8") in database_bytes:
            raise AssertionError("Credential leaked into SQLite")
        summary = {
            "build": read_json(BUNDLE_ROOT / "build.json"),
            "runtime_pid": process.pid,
            "runtime_url": base_url,
            "readiness": readiness.json(),
            "customized": custom_summary,
            "reset": reset_summary,
            "privacy": {
                "raw_prompt_in_http_run_surfaces": False,
                "raw_prompt_in_run_artifacts_logs": False,
                "raw_prompt_in_sqlite": False,
                "credential_in_http_run_surfaces": False,
                "credential_in_run_artifacts_logs": False,
                "credential_in_sqlite": False,
                "settings_cache_control": "no-store",
            },
            "sqlite": {
                "integrity_check": integrity,
                "foreign_key_violations": len(foreign_key_violations),
            },
        }
        write_json(EVIDENCE_ROOT / "summary.json", summary)
        print(json.dumps(summary, indent=2))
    finally:
        if process.poll() is None:
            try:
                if "base_url" in locals() and session.cookies.get("fitcv_csrf"):
                    session.post(
                        urljoin(base_url, "local/system/shutdown"),
                        headers=request_headers(session, base_url),
                        timeout=10,
                    )
                    process.wait(timeout=15)
            except Exception:
                process.kill()
                process.wait(timeout=10)
        if overlay_path is not None:
            if overlay_existed:
                overlay_path.parent.mkdir(parents=True, exist_ok=True)
                overlay_path.write_bytes(overlay_bytes)
            elif overlay_path.exists():
                overlay_path.unlink()
        session.close()


if __name__ == "__main__":
    main()

