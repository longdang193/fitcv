"""Serve the real FitCV app with a credential-free deterministic LLM adapter."""

from __future__ import annotations

import argparse
import json
import os
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
    if Path(os.environ["FITCV_CP_SQLITE_PATH"]).resolve() != database:
        raise SystemExit("database_identity_mismatch")
    from fastapi import Response
    from fitcv.cv_generator import build_empty_structured_cv
    from fitcv.llm_runtime import LlmAdapterResponse, install_test_llm_runtime
    from fitcv_cp.app import create_app

    calls = {"provider": 0, "credential": 0}

    def credential_resolver(_route: object) -> str:
        calls["credential"] += 1
        return "fixture-key"

    def adapter(request: object, _route: object, _api_key: str, **_kwargs: object) -> LlmAdapterResponse:
        calls["provider"] += 1
        payload = build_empty_structured_cv(jd={}, profile={}, config={}, fit_classification="stretch")
        payload["sections"]["header"] = {"name": "E2E Candidate", "title": "Analytics Engineer", "location": "Remote", "contact": {"email": None, "phone": None, "linkedin": None}}
        payload["sections"]["summary"] = {"text": "SQL and Python analyst."}
        payload["sections"]["skills"] = {"groups": [{"name": "Core", "skills": ["SQL", "Python"]}]}
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
            }),
            media_type="application/json",
        )

    import uvicorn

    uvicorn.run(application, host="127.0.0.1", port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
