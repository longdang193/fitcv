# Checkpoint Result Pack

## Metadata

- Checkpoint ID: `workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface.20260504-1745`
- Workstream ID: `workstream-operator-control-plane`
- Thread ID: `workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface`
- Thread file: `docs/intent/workstreams/threads/workstream-operator-control-plane/06-operator-control-plane-phase-2-degraded-mode-and-portability-surface.md`
- Timestamp (UTC): `2026-05-04T15:45:00Z`
- Owner: `codex`

## Intent

Close out the sqlite CV-generation live-run failure lane by proving root-cause traceability (failure -> bounded fix -> live rerun evidence) and recording explicit follow-up learning decisions.

## Actions

- Root-cause investigation (systematic debugging):
  - traced CV-generation failure to agentic live-provider runtime env assembly divergence in `src/fitcv/agentic_cv_generation.py`
  - confirmed previous failure signature moved from missing key / `sa_key.json` to provider auth (`401 Unauthorized`), indicating env-source mismatch rather than Google credential fallback
- Applied bounded fix:
  - removed external `.env` merge behavior in `agentic_cv_generation` live-runtime env assembly
  - enforced process-env-only runtime source for CV live-provider calls
- Added regression test coverage:
  - replaced env-file precedence tests with process-env-only invariant test in `tests/test_pipeline_agentic_late_stage.py`
- Validation:
  - `pytest -q tests/test_pipeline_agentic_late_stage.py -k "fitcv_langgraph_env_values or live_provider_failure_marks_generation_failed"`
  - `pytest -q tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py`
- Live-run verification sequence:
  - direct provider probe to `http://localhost:20128/v1/chat/completions` with `.env` key/model returned success (`OK`)
  - clean app restart on sqlite backend with `.env` loaded
  - triggered live run with fixture `data/sample_data_engineer_jobs.json`

## Visible Output

- Code artifacts:
  - `src/fitcv/agentic_cv_generation.py`
  - `tests/test_pipeline_agentic_late_stage.py`
- Runtime evidence:
  - failing run before clean restart: `88839a57-28eb-46c1-81d4-9e95bde2eb65`
    - `status=succeeded`, `cvs_generated=0`, CV debug statuses: `blocked_by_reranker_fit:1, generation_failed:3`
    - no `sa_key.json`, no missing-key error, `401 Unauthorized` present
  - direct provider probe after loading `.env`: success (`OK`) for model `cx/gpt-5.2`
  - passing run after clean restart and env alignment: `cba41d26-e9ef-492f-a01f-d99a6ec3e214`
    - `status=succeeded`, `passed_filter=4`, `ranked=4`, `cvs_generated=3`
    - CV debug statuses: `accepted:3, blocked_by_reranker_fit:1`
    - no `401 Unauthorized`, no `sa_key.json`, no missing-key error
- Evidence file:
  - `.tmp-tests/latest-cv-debug.json`

## Root Cause and Failure Boundary

- Root cause:
  - CV-generation agentic live-provider path allowed runtime env drift by merging external `.env` sources outside the active process runtime envelope.
- Failure boundary:
  - bounded to CV-generation live-provider lane in agentic late stage.
  - earlier pipeline stages were not failing for the same reason because they did not depend on that exact divergent runtime assembly path in the failing runs.

## Bounded Fix and Scope

- Fix:
  - process-env-only runtime env assembly for live provider in `agentic_cv_generation`.
- Scope boundary:
  - no broad config refactor, no cross-module provider contract rewrite.
  - preserved StageResult/event contracts and run artifact surfaces.

## Learning Backfeed Decisions

- Tests:
  - `update now` (done): added process-env-only invariant coverage for CV live-runtime env assembly.
- Specs:
  - `defer with reason`: no spec text change in this checkpoint; behavior aligns with existing env-only secret/routing intent and provider-agnostic Phase 2 portability contract.
- Scenario catalog:
  - `update now` (recorded here): add regression scenario requirement for "clean restart + env alignment + live CV generation acceptance" when investigating 401-only CV lane failures.

## Status

`pass`

## Next Decision

`closeout ready -> thread-closeout-readiness-prompt.md`
