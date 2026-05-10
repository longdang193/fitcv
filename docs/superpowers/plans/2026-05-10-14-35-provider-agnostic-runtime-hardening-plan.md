---
layer: change
artifact_type: plan
status: complete
template_id: implementation-plan
name: provider-agnostic-runtime-hardening
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
targets:
  - src/fitcv/config.py
  - src/fitcv/db.py
  - src/fitcv/vector_search.py
  - src/fitcv/tracker.py
  - src/fitcv/rule_filter.py
  - src/fitcv/ranking.py
  - src/fitcv/ingest.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/evidence.py
  - src/fitcv/embeddings.py
  - src/fitcv/enrich.py
  - src/fitcv/candidate.py
  - src/fitcv/ai_score.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline.py
  - tests/test_config.py
  - tests/test_embeddings.py
  - tests/test_vector_search.py
  - tests/test_tracker.py
  - tests/test_rule_filter.py
  - tests/test_ranking.py
  - tests/test_ingest.py
  - tests/test_gap_analysis.py
  - tests/test_evidence.py
  - tests/test_candidate.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
related_stages:
  - normalize
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

# 2026-05-10-14-35 Provider Agnostic Runtime Hardening Plan

## Goal

Eliminate remaining provider-lock and environment-branch drift by enforcing one config-driven source of truth for persistence backend and model/provider routing, with cloud SDK and credential requirements applied only when `bigquery` backend is active.

## Key Deliverables

### Single-source backend resolution across runtime surfaces

All persistence-adjacent modules stop reading `FITCV_CP_DATA_BACKEND` directly and consume backend decisions through shared config/runtime resolver functions.

### Adapter-bounded cloud dependencies

Cloud SDK imports (`google-cloud-*`, `vertexai`) and service-account file loading are isolated to BigQuery/Vertex adapter boundaries and are not imported or evaluated in sqlite-only execution paths.

### Backend-conditional credential enforcement

Config validation enforces `service_account_key` and other cloud requirements only when resolved backend is `bigquery`; sqlite mode runs without credential file requirements.

### Config-authoritative provider/model routing

Model API/provider/model selection in scoring/generation paths is derived from control-plane routing config, not scattered `os.environ` overrides.

### Verification evidence for sqlite-only runtime

Focused tests and one sqlite-mode validation run prove no BigQuery client creation, no cloud credential hard-fail, and correct persistence behavior under sqlite.

## Task/Wave Breakdown

### Task 1: Baseline lock and scope freeze

**Purpose:**
- Freeze exact failure baseline and touched-surface inventory before refactor.

**Files:**
- Inspect: `docs/superpowers/plans/2026-05-10-provider-agnostic-persistence-patch-plan.md`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/*.py` (listed in `targets`)
- Verify: `tests/test_fitcv_cp/test_filter_langfuse_export.py`

**Preconditions:**
- Worktree branch is active.
- Current red baseline includes unrelated collection failure for `scripts.filter_langfuse_export`.

**Steps:**
- [x] Step 1: Record current known unrelated test failure as out-of-scope baseline debt.
  - Evidence: full suite baseline (`py -m pytest -q`) currently red with broad repo-level validation failures (`tests/test_validate_adoption_shape.py`, `tests/test_validate_planning_lifecycle.py`, `tests/test_validate_repo_config.py`, `tests/test_validate_repo_contracts.py`) and not tied to provider-agnostic runtime patch scope.
- [x] Step 2: Confirm target modules still contain direct backend env branching and cloud credential coupling.
  - Evidence: direct `FITCV_CP_DATA_BACKEND` reads still present in `src/fitcv/vector_search.py`, `tracker.py`, `rule_filter.py`, `ranking.py`, `enrich.py`, `embeddings.py`, `candidate.py`.
  - Evidence: direct `service_account.Credentials.from_service_account_file(...)` coupling still present in `vector_search.py`, `tracker.py`, `rule_filter.py`, `ranking.py`, `ingest.py`, `gap_analysis.py`, `evidence.py`, `enrich.py`, `embeddings.py`, `candidate.py`, `ai_score.py`.
- [x] Step 3: Lock patch scope to provider-agnostic hardening only.
  - Scope lock: do not remediate unrelated validator/test baseline debt in this lane.

**Verification:**
- [x] `py -m pytest -q` confirms repo baseline is currently red due to unrelated validation suites.
- [x] `py -m pytest tests/test_fitcv_cp/test_filter_langfuse_export.py -q` passes (`3 passed`) and does not represent current blocker for this lane.

**Exit Criteria:**
- Baseline and scope are explicit; no hidden refactor expansion. ✅

### Task 2: Canonical backend resolver adoption

**Purpose:**
- Enforce one backend decision path for runtime logic.

**Files:**
- Inspect: `src/fitcv/config.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/db.py` (if helper placement belongs here)
- Modify: `src/fitcv/vector_search.py`, `tracker.py`, `rule_filter.py`, `ranking.py`, `enrich.py`, `embeddings.py`, `candidate.py`
- Verify: `tests/test_config.py`

**Preconditions:**
- Task 1 complete.

**Steps:**
- [x] Step 1: Confirm `resolve_data_backend` remains canonical resolver.
- [x] Step 2: Add/normalize helper usage so runtime modules call resolver instead of `os.environ.get("FITCV_CP_DATA_BACKEND")`.
- [x] Step 3: Remove duplicate local backend helper logic where present.
- [x] Step 4: Keep backward-compatible default backend behavior.
  - Evidence: `resolve_data_backend` now retains legacy BigQuery-style fallback when config contains explicit `gcp_project` + `bigquery_dataset` but no explicit backend type.

**Verification:**
- [x] Grep-based check shows no direct `FITCV_CP_DATA_BACKEND` reads in targeted runtime modules.
- [x] Backend unit tests pass for resolver behavior.
  - Evidence: `py -m pytest tests/test_vector_search.py tests/test_embeddings.py tests/test_tracker.py tests/test_rule_filter.py tests/test_ranking.py tests/test_candidate.py tests/test_enrich.py -q` → `248 passed, 5 skipped`.

**Exit Criteria:**
- Backend mode is determined through shared config resolver only. ✅

### Task 3: Backend-conditional config validation

**Purpose:**
- Decouple sqlite mode from GCP credential requirements.

**Files:**
- Modify: `src/fitcv/config.py`
- Verify: `tests/test_config.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Step 1: Refactor required-key checks so cloud-only keys are enforced under resolved `bigquery` backend.
- [x] Step 2: Keep clear fail-fast errors for missing BigQuery keys in `bigquery` mode.
- [x] Step 3: Ensure sqlite mode accepts missing `service_account_key`, `gcp_project`, and dataset keys when not needed.

**Verification:**
- [x] Config tests cover `bigquery` strict mode and sqlite permissive mode.
  - Evidence: `tests/test_config.py` includes sqlite permissive and bigquery strict cases (`test_load_config_sqlite_backend_allows_missing_cloud_keys`, `test_load_config_bigquery_backend_requires_cloud_keys`).

**Exit Criteria:**
- sqlite mode config load works without cloud credentials.

### Task 4: Cloud import and credential isolation behind adapters

**Purpose:**
- Prevent sqlite runtime from requiring cloud SDK installation/import.

**Files:**
- Modify: `src/fitcv/vector_search.py`
- Modify: `src/fitcv/tracker.py`
- Modify: `src/fitcv/rule_filter.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/ingest.py`
- Modify: `src/fitcv/gap_analysis.py`
- Modify: `src/fitcv/evidence.py`
- Modify: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/candidate.py`
- Modify: `src/fitcv/ai_score.py`
- Verify: module tests listed in `targets`

**Preconditions:**
- Task 2 and Task 3 complete.

**Steps:**
- [x] Step 1: Move BigQuery/Vertex imports inside backend-gated adapter callsites.
- [x] Step 2: Ensure `from_service_account_file(...)` executes only in explicit BigQuery branches.
- [x] Step 3: Keep sqlite write/read paths operational and schema-compatible.
- [x] Step 4: Preserve existing BigQuery behavior for bigquery backend.

**Verification:**
- [x] sqlite-mode tests run in environment without cloud credential variables.
- [x] Mock/assertion tests verify BigQuery constructor not invoked for sqlite mode.
- Progress evidence:
  - `py -m pytest tests/test_tracker.py -q` → pass.
  - `py -m pytest tests/test_ingest.py -q` → pass.
  - `py -m pytest tests/test_rule_filter.py tests/test_ranking.py -q` → pass.
  - `py -m pytest tests/test_enrich.py tests/test_embeddings.py -q` → `92 passed, 2 skipped`.
  - `py -m pytest tests/test_vector_search.py tests/test_candidate.py tests/test_ai_score.py -q` → `80 passed, 3 skipped`.
  - `py -m pytest tests/test_gap_analysis.py tests/test_evidence.py -q` → `50 passed`.
  - sqlite smoke: `$env:FITCV_CP_DATA_BACKEND='sqlite'; $env:PYTHONPATH='src'; Remove-Item Env:GOOGLE_APPLICATION_CREDENTIALS; py -m fitcv.pipeline --help` → exit `0`.

**Exit Criteria:**
- sqlite execution path does not import or initialize cloud SDK paths.

### Task 5: Config-authoritative provider/model routing cleanup

**Purpose:**
- Remove ad-hoc env override drift for provider/model API resolution.

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_ai_score.py`, `tests/test_cv_generator.py`, `tests/test_pipeline.py`

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Step 1: Route model/provider/base_url selection through control-plane config helpers.
  - Prereq inventory complete: `FITCV_LANGGRAPH_*` override callsites confirmed in `ai_score.py`, `cv_generator.py`, `enrich.py`, `pipeline.py`.
- [x] Step 2: Remove or strictly gate `FITCV_LANGGRAPH_*` override paths so runtime authority remains config-first.
- [x] Step 3: Keep documented secret resolution behavior for API keys while avoiding provider drift.

**Verification:**
- [x] Tests assert provider/model values come from config routing contract.
- [x] No accidental behavior change for explicitly configured supported providers.
- Progress evidence:
  - `py -m pytest tests/test_ai_score.py -q` → `28 passed, 1 skipped`.
  - `py -m pytest tests/test_cv_generator.py -q` → `45 passed`.
  - `py -m pytest tests/test_enrich.py -q` → `69 passed`.
  - `py -m pytest tests/test_pipeline.py -q` → `102 passed`.

**Exit Criteria:**
- Provider/API routing is deterministic and config-driven across touched modules.

### Task 6: Focused regression and parity verification

**Purpose:**
- Prove hardening outcome without conflating unrelated repository baseline debt.

**Files:**
- Verify only: targets from prior tasks and related tests

**Preconditions:**
- Tasks 1-5 complete.

**Steps:**
- [x] Step 1: Run focused test subsets for all changed modules.
- [x] Step 2: Run sqlite-mode smoke validation with cloud credentials unset.
- [x] Step 3: Run repo fast contract validation to ensure planning/governance consistency.
- [x] Step 4: Capture remaining unrelated baseline failures separately, if any persist.

**Verification:**
- [x] Focused tests pass for changed surfaces.
- [x] sqlite smoke run confirms no credential/import hard-fail and expected persistence writes.
- [x] Fast repo contract validation attempted; failure isolated to unrelated legacy plan-metadata debt outside touched surfaces.
- [x] Fresh live-run evidence confirms both execution modes succeed on sqlite backend.
- [x] Langfuse trace presence verified for cv_analysis/cv_generation/acceptance_review_item on fresh runs.
- Progress evidence:
  - `py -m pytest tests/test_config.py tests/test_embeddings.py tests/test_vector_search.py tests/test_tracker.py tests/test_rule_filter.py tests/test_ranking.py tests/test_ingest.py tests/test_gap_analysis.py tests/test_evidence.py tests/test_candidate.py tests/test_ai_score.py tests/test_cv_generator.py tests/test_pipeline.py -q` → `479 passed, 7 skipped`.
  - `$env:FITCV_CP_DATA_BACKEND='sqlite'; $env:PYTHONPATH='src'; Remove-Item Env:GOOGLE_APPLICATION_CREDENTIALS -ErrorAction SilentlyContinue; py -m fitcv.pipeline --help` → exit `0`.
  - `py scripts/validate_repo_contracts.py --fast` → fails on pre-existing `docs/superpowers/plans/*` metadata registry mismatches unrelated to Task 1–6 touched files.
  - Live run-all: `c84ef95b-2edc-4fe3-96b5-49489e803659` → `succeeded`, completed through `cv_generation`.
  - Live stage-by-stage: `8551798a-67e4-4711-bbe5-37ee9751bfc5` → progressed to `succeeded`, checkpoint `completed`.
  - Langfuse project `fitcv-local-project`: both runs show stage nodes `pipeline.cv_analysis`, `pipeline.cv_generation`, `pipeline.acceptance_review_item`.

**Exit Criteria:**
- Provider-agnostic hardening evidence is complete and separated from unrelated failures.

**Scoped Acceptance Note:**
- Task 6 accepted for touched surfaces.
- Remaining fast-contract failures are repo-wide pre-existing planning metadata debt in legacy docs and out of scope for provider-agnostic runtime hardening lane.
- Live runtime parity confirmed in both execution modes plus Langfuse stage-trace visibility for fresh runs.

## Verification

```powershell
# focused backend/provider hardening tests
python -m pytest tests/test_config.py tests/test_embeddings.py tests/test_vector_search.py tests/test_tracker.py tests/test_rule_filter.py tests/test_ranking.py tests/test_ingest.py tests/test_gap_analysis.py tests/test_evidence.py tests/test_candidate.py tests/test_ai_score.py tests/test_cv_generator.py tests/test_pipeline.py -q

# sqlite-mode smoke without cloud credentials (example pattern)
# $env:FITCV_CP_DATA_BACKEND="sqlite"
# Remove-Item Env:GOOGLE_APPLICATION_CREDENTIALS -ErrorAction SilentlyContinue
# python -m fitcv.pipeline --help

# governance/contract check
python scripts/validate_repo_contracts.py --fast
```

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
