"""Serve the real FitCV app with a credential-free deterministic LLM adapter."""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if os.environ.get("FITCV_REVIEW_E2E") != "1":
        raise SystemExit("FITCV_REVIEW_E2E=1 required")
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    database = Path(str(manifest["database"])).resolve()
    source_profile_fingerprint = str(manifest.get("source_profile_fingerprint") or "").strip()
    if Path(os.environ["FITCV_CP_SQLITE_PATH"]).resolve() != database:
        raise SystemExit("database_identity_mismatch")
    from fastapi import Response
    from fitcv.cv_generator import build_empty_structured_cv
    from fitcv.llm_runtime import LlmAdapterResponse, install_test_llm_runtime
    from fitcv_cp import sqlite_store
    from fitcv_cp.app import create_app

    calls = {"provider": 0, "credential": 0}
    initial_debug_json = json.loads(
        sqlite_store.get_run(manifest["run_id"]).cv_generation_debug_json or "{}"
    )

    def credential_resolver(_route: object) -> str:
        calls["credential"] += 1
        return "fixture-key"

    def adapter(request: object, _route: object, _api_key: str, **_kwargs: object) -> LlmAdapterResponse:
        calls["provider"] += 1
        payload = build_empty_structured_cv(jd={}, profile={}, config={}, fit_classification="stretch")
        payload["sections"]["header"] = {"name": "E2E Candidate", "title": "Analytics Engineer", "location": "Remote", "contact": {"email": None, "phone": None, "linkedin": None}}
        payload["sections"]["summary"] = {"text": "SQL and Python analyst."}
        payload["sections"]["experience"] = [{
            "role": "Analyst",
            "company": "Example",
            "start": "2020-01",
            "end": "2024-01",
            "location": "Remote",
            "bullets": [
                "Built SQL reports.",
                "Used Python for analytics automation.",
            ],
        }]
        payload["sections"]["skills"] = {"groups": [{"label": "Core", "items": ["SQL", "Python"]}]}
        return LlmAdapterResponse(
            adapter="fitcv_e2e_fixture",
            runtime_path="fitcv_llm_e2e_fixture",
            raw_text=json.dumps(payload),
            provider_payload={"model": "e2e-fixture"},
            response_id=f"e2e-response-{calls['provider']}",
            trace_id=f"e2e-trace-{calls['provider']}",
        )

    install_test_llm_runtime(adapter=adapter, credential_resolver=credential_resolver)
    application = create_app(redis_url="redis://e2e-unused")

    @application.get("/__e2e/diagnostics")
    def diagnostics() -> Response:
        from fitcv_cp import sqlite_store

        run = sqlite_store.get_run(manifest["run_id"])
        debug_payload = json.loads(run.cv_generation_debug_json or "{}") if run else {}
        review_actions = [
            item for item in list(debug_payload.get("hitl_review_actions") or [])
            if isinstance(item, dict)
        ]
        return Response(
            content=json.dumps({
                "pid": os.getpid(),
                "database": str(database),
                "fitcv_local_mode": os.environ.get("FITCV_LOCAL_MODE"),
                "inline_execution": os.environ.get("FITCV_CP_INLINE_EXECUTION"),
                "run_id": manifest["run_id"],
                "run_job_id": manifest["run_job_id"],
                "provider_calls": calls["provider"],
                "credential_resolver_calls": calls["credential"],
                "review_action_count": len(review_actions),
                "regeneration_job_ids": [
                    str(item.get("regeneration_job_id") or "")
                    for item in review_actions
                    if item.get("regeneration_job_id")
                ],
            }),
            media_type="application/json",
        )

    @application.post("/__e2e/reset")
    def reset_fixture() -> Response:
        run_id = manifest["run_id"]
        run_job_id = manifest["run_job_id"]
        with sqlite3.connect(database) as connection:
            connection.execute(
                "DELETE FROM requirement_resolution_enqueue_intents WHERE resolution_id IN (SELECT resolution_id FROM requirement_resolutions WHERE candidate_profile_id=? AND source_profile_fingerprint=?)",
                ("e2e-profile", source_profile_fingerprint),
            )
            connection.execute(
                "DELETE FROM requirement_resolutions WHERE candidate_profile_id=? AND source_profile_fingerprint=?",
                ("e2e-profile", source_profile_fingerprint),
            )
            connection.execute(
                "DELETE FROM idempotent_actions WHERE action_scope=?",
                (f"cv.review_resolution:{run_job_id}",),
            )
            connection.execute("DELETE FROM cv_versions WHERE run_job_id=?", (run_job_id,))
            connection.execute(
                "UPDATE run_jobs SET current_cv_version_id=NULL WHERE run_job_id=?",
                (run_job_id,),
            )
            connection.commit()
        sqlite_store.update_run_cv_generation_debug(run_id, json.dumps(initial_debug_json, sort_keys=True))
        calls["provider"] = 0
        calls["credential"] = 0
        return Response(content=json.dumps({"status": "reset"}), media_type="application/json")

    import uvicorn

    uvicorn.run(application, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
