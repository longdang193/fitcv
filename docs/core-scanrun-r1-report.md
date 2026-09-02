# Core Scan/Run Verification R1

Date: 2026-09-02
Authority: new `/app` frontend only. Disposable local state only.

## Journey

- Upload onboarding: **BLOCKED** by real `candidate_profile_llm_unavailable`; exact backend message: `LLM routing is unavailable for candidate_profile_base_mapping`. No mock success claimed.
- Synthetic Candidate Profile: **PASS** after disposable SQLite seed because provider capability blocked UI processing; profile `profile_synthetic_scanrun_r1`, revision `1`.
- Step 2 to 3 / Step 3 to 4: **PASS** at `/app#/settings/providers`; one canonical page now exposes API Providers and LLM Configuration. No local onboarding links point to `/admin` in local mode.
- Scan terminal: **PASS**. `scan-6963a184b9ed` reached `succeeded` with `5` jobs from real Greenhouse/Awin provider flow.
- Scan persistence/reload: **PASS**. `/app#/scans?scan_id=scan-6963a184b9ed` retained Succeeded, timeline, 5 output records, and job rows after hard reload; SQLite rows persisted in `scans`, `scan_inputs`, `scan_outputs`, and `tracked_companies`.
- Run terminal/persistence: **BLOCKED** before run creation by real readiness gate. No Run row was created; this is correct dependency behavior, not run success.
- Provider blocker: **BLOCKED**. Loopback `127.0.0.1:20128/v1/models` was reachable, but no approved credential existed. Saving connection without key returned `422 provider_credential_required`. No secret printed, embedded, or committed.

## Confirmed fixes

- Readiness-blocked `/runs` now returns canonical `409` error envelope with code `local_readiness_required`, exact reasons, and action to open `/app` provider/LLM settings.
- New Run dialog renders backend `error.action`, not only HTTP `Conflict`.
- Local onboarding and local-mode shared navigation route provider/LLM setup to `/app#/settings/providers`; non-local legacy routes remain unchanged.
- `/app#/settings/providers` uses existing provider and LLM APIs. It supports custom provider creation, connection verification, model validation, and Default Route selection. API key input is password-only and never prefilled.

## Fresh checks

- `tests/test_fitcv_cp/test_local_routes.py`: `41 passed`.
- `tests/test_fitcv_cp/test_app.py -k "run or provider_api or admin_llm or onboarding"`: `232 passed, 236 deselected`.
- `frontend/npm run typecheck`: pass.
- `frontend/npm run build`: pass.
- `git diff --check`: pass.

## Evidence

Live browser/API/SQLite evidence remains under `.tmp/core-scanrun-r1/evidence/`, including `browser-run-blocker.txt`, `browser-network-console.txt`, `api-readiness.json`, `api-scan-detail.json`, `api-scan-output.json`, and `sqlite-final.txt`. Chrome DevTools snapshots captured `/app` settings, Run blocker, Scan detail, and post-reload Scan detail. Screenshot file export was unavailable due browser workspace policy.

## Limits

Real Run could not reach terminal execution without an approved provider credential and verified model/default route. Provider setup remained uncompleted intentionally; no fallback, mock, invented key, provider change, router policy change, threshold change, protected DB change, or legacy removal was used.
