---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-cross-feature-api-key-resolver-unification-and-launcher-dedupe
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-17-10-fitcv-cross-feature-api-key-resolver-unification-and-launcher-dedupe-spec.md
targets:
  - src/fitcv/runtime_routing.py
  - src/fitcv/ai_score.py
  - src/fitcv/enrich.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/env_defaults.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/main.py
  - start_web.ps1
  - start_worker.ps1
  - tests/test_ai_score.py
  - tests/test_enrich.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_env_defaults.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

## Goal

Implement shared OpenAI-compatible API-key resolution across in-scope callers, preserve web/worker startup symmetry, and delete launcher-side dotenv duplication unless a minimal launcher-only wrapper is proven necessary.

## Key Deliverables

### Shared resolver migration

`src/fitcv/runtime_routing.py` owns the two canonical resolver functions, and all in-scope callers use them instead of inline env lookup chains.

### Startup symmetry proof

Web startup, pipeline worker, and regenerate-once worker all observe same `.env` default-loading semantics from clean env.

### Launcher dedupe closeout

`start_web.ps1` and `start_worker.ps1` no longer own duplicated dotenv parsing logic beyond any explicitly justified launcher-only behavior.

## Task/Wave Breakdown

### Task 1: Freeze current-state contract in tests

**Purpose:**
- lock intended env precedence and startup symmetry before broad code migration

**Files:**
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/main.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_env_defaults.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_env_defaults.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- patched spec approved as source of truth for resolver names, precedence matrix, and admissible startup cases

**Steps:**
- [ ] Step 1: add tests for `resolve_openai_compatible_api_key()` precedence using `FITCV_LLM_API_KEY`, `OPENAI_API_KEY`, and `OPENAI_COMPATIBLE_API_KEY`
- [ ] Step 2: add tests for `resolve_langgraph_openai_compatible_api_key()` precedence using `FITCV_LANGGRAPH_OPENAI_API_KEY`, `OPENAI_API_KEY`, and `OPENAI_COMPATIBLE_API_KEY`
- [ ] Step 3: extend startup symmetry tests to cover web startup, pipeline worker, and regenerate-once worker from clean env

**Verification:**
- [ ] `python -m pytest tests/test_ai_score.py tests/test_enrich.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_env_defaults.py tests/test_fitcv_cp/test_worker_job.py -k "api_key or dotenv or langgraph" -q`

**Exit Criteria:**
- tests fail correctly before migration and encode spec contract without locking unrelated implementation details

### Task 2: Migrate in-scope callers to shared resolvers

**Purpose:**
- delete duplicated inline API-key lookup logic in runtime callers

**Files:**
- Inspect: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv/runtime_routing.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv/runtime_routing.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: add or adjust the two canonical resolver functions in `src/fitcv/runtime_routing.py`
- [ ] Step 2: migrate ranking, enrich extraction, and control-plane synonym inspection paths to the shared resolvers
- [ ] Step 3: normalize missing-key failure messages only as needed to stay truthful to accepted aliases

**Verification:**
- [ ] `python -m pytest tests/test_ai_score.py tests/test_enrich.py tests/test_fitcv_cp/test_app.py -k "api_key or langgraph" -q`
- [ ] `rg -n "FITCV_LLM_API_KEY|FITCV_LANGGRAPH_OPENAI_API_KEY|OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY" src/fitcv src/fitcv_cp -g "*.py"`

**Exit Criteria:**
- in-scope caller modules no longer implement local alias-selection logic

### Task 3: Dedupe launcher dotenv ownership

**Purpose:**
- remove PowerShell-side dotenv duplication while preserving launcher behavior

**Files:**
- Inspect: `start_web.ps1`
- Inspect: `start_worker.ps1`
- Inspect: `src/fitcv_cp/env_defaults.py`
- Inspect: `src/fitcv_cp/main.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `start_web.ps1`
- Modify: `start_worker.ps1`
- Verify: `tests/test_fitcv_cp/test_env_defaults.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 1 complete
- Task 2 complete or shared resolvers merged cleanly

**Steps:**
- [ ] Step 1: remove duplicated `Set-EnvFromDotEnv` parsing from launcher scripts unless a launcher-only need is proven
- [ ] Step 2: keep only launcher-specific env setup that Python runtime does not own
- [ ] Step 3: confirm web and worker still rely on shared Python bootstrap for missing env defaults

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_env_defaults.py tests/test_fitcv_cp/test_worker_job.py -k "dotenv" -q`
- [ ] `rg -n "Set-EnvFromDotEnv" start_web.ps1 start_worker.ps1`

**Exit Criteria:**
- launcher scripts no longer contain duplicated dotenv parsing logic, or remaining wrapper is minimal and explicitly justified in code/docs

### Task 4: Final proof and drift scan

**Purpose:**
- prove SSOT, symmetry, and repo-contract compliance after migration

**Files:**
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `start_web.ps1`
- Inspect: `start_worker.ps1`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_env_defaults.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: run targeted test bundle for resolver precedence and startup symmetry
- [ ] Step 2: run explicit grep scan to confirm in-scope direct API-key reads are gone outside shared owner(s) and allowed wrappers
- [ ] Step 3: run repo fast validator and record final clean state

**Verification:**
- [ ] `python -m pytest tests/test_ai_score.py tests/test_enrich.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_env_defaults.py tests/test_fitcv_cp/test_worker_job.py -k "api_key or dotenv or langgraph" -q`
- [ ] `rg -n "FITCV_LLM_API_KEY|FITCV_LANGGRAPH_OPENAI_API_KEY|OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY" src/fitcv src/fitcv_cp -g "*.py"`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- proof shows one shared resolver owner, symmetric startup behavior, reduced launcher duplication, and passing repo fast-validation

## Verification

- `python -m pytest tests/test_ai_score.py tests/test_enrich.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_env_defaults.py tests/test_fitcv_cp/test_worker_job.py -k "api_key or dotenv or langgraph" -q`
- `rg -n "FITCV_LLM_API_KEY|FITCV_LANGGRAPH_OPENAI_API_KEY|OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY" src/fitcv src/fitcv_cp -g "*.py"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. shared resolver ownership, startup symmetry, and launcher dedupe are proven by tests plus explicit drift scan

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
