---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: ai-plane-unification-and-backend-symmetry-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-05-17-15-20-ai-plane-symmetry-invariance-equivalence-migration-spec.md
targets:
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - src/fitcv/config.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - docs/configuration.md
  - docs/pipeline.md
  - tests/test_config.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
related_features:
  - cv_system
  - settings_system
  - trigger_run_management
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement AI-plane unification so model routing/auth are single-source and backend-agnostic, while preserving BigQuery and SQLite symmetry as persistence-only variants.

## Key Deliverables

### Deliverable 1

Unified AI routing and auth contract across `enrich`, `ranking_ai_score`, and `cv_generation` paths, with `control_plane.model_routing.parts.*` as runtime SSOT and API-key auth as canonical contract.

### Deliverable 2

Removal of legacy runtime ownership ambiguity (`gemini` fallback defaults, non-agentic decision branch ownership, flat compatibility model authority) while retaining compatibility telemetry and bounded deprecation windows.

### Deliverable 3

Backend equivalence verification suite proving same AI-stage decisions/provenance across sqlite and bigquery for identical inputs, with divergence allowed only in persistence substrate metadata.

## Task/Wave Breakdown

### Task 1: Freeze contracts and deprecation policy surface

**Purpose:**
- establish deterministic migration contract before code-path edits

**Files:**
- Inspect: `docs/superpowers/specs/2026-05-17-15-20-ai-plane-symmetry-invariance-equivalence-migration-spec.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Verify: `config/runtime/control_plane.yaml`

**Preconditions:**
- approved migration spec remains source of truth
- GitNexus freshness remains `fresh` for dependency lookup

**Steps:**
- [ ] Step 1: Document canonical AI auth contract (`FITCV_LLM_API_KEY` primary) and alias deprecation window.
- [ ] Step 2: Document strict plane boundary (`data_plane` vs `ai_plane`) and prohibited backend-to-AI coupling.
- [ ] Step 3: Add explicit runtime error contract text for missing routing/model/key.

**Verification:**
- [ ] `rg -n "FITCV_LLM_API_KEY|non-agentic|gemini_model|control_plane.model_routing" docs/configuration.md docs/pipeline.md -S`

**Exit Criteria:**
- docs define single runtime truth and deprecation semantics without contradictory ownership language

### Task 2: Remove legacy model fallback ownership in config resolution

**Purpose:**
- eliminate Gemini/default fallback authority and force routing-based model truth

**Files:**
- Inspect: `src/fitcv/config.py`
- Modify: `src/fitcv/config.py`
- Modify: `config/runtime/pipeline.yaml`
- Verify: `tests/test_config.py`

**Preconditions:**
- Task 1 complete
- GitNexus impact acknowledged for `get_cv_generation_model` (MEDIUM; direct callers in pipeline/cv_generator/worker_job path)

**Steps:**
- [ ] Step 1: Refactor `get_cv_generation_model` and related helpers to remove `gemini-2.5-flash` fallback authority.
- [ ] Step 2: Restrict compatibility projection fields to non-authoritative metadata only.
- [ ] Step 3: Update tests to require fail-fast behavior when model unresolved.

**Verification:**
- [ ] `pytest tests/test_config.py -q`
- [ ] `rg -n "gemini-2\.5-flash|gemini_model" src/fitcv/config.py config/runtime/pipeline.yaml tests/test_config.py -S`

**Exit Criteria:**
- no config runtime path can silently choose Gemini/default model when routing is unresolved

### Task 3: Unify AI auth and client construction across enrich/ranking/generation

**Purpose:**
- make auth/routing invariant across all AI stages

**Files:**
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/cv_generator.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_cv_generator.py`

**Preconditions:**
- Task 2 complete
- GitNexus impact reviewed for:
  - `Function:src/fitcv/enrich.py:_build_openai_compat_client` (LOW)
  - `Function:src/fitcv/ai_score.py:_make_genai_client` (LOW)
  - `Function:src/fitcv/cv_generator.py:_build_openai_compat_client` (LOW)

**Steps:**
- [ ] Step 1: Standardize key lookup order around canonical key + bounded alias fallback with warning.
- [ ] Step 2: Remove any AI client dependence on `service_account_key`.
- [ ] Step 3: Ensure routing source/provenance fields emitted consistently across stages.

**Verification:**
- [ ] `pytest tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py -q`
- [ ] `rg -n "service_account_key|OPENAI_API_KEY|OPENAI_COMPATIBLE_API_KEY|FITCV_LLM_API_KEY" src/fitcv/enrich.py src/fitcv/ai_score.py src/fitcv/cv_generator.py -S`

**Exit Criteria:**
- all AI stages share same auth/routing contract and reject account-key-only AI execution

### Task 4: Remove non-agentic runtime authority for AI decisions

**Purpose:**
- enforce single AI execution path independent of legacy mode split

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`

**Preconditions:**
- Task 3 complete
- GitNexus impact reviewed for `_build_settings_used_payload` (LOW) and `execute_pipeline_run` call chain

**Steps:**
- [ ] Step 1: Remove decision-critical non-agentic branch ownership for AI stages.
- [ ] Step 2: Keep trace/diagnostic fields compatible but ensure they report unified path.
- [ ] Step 3: Update mode/status expectations in tests to reflect unified runtime path.

**Verification:**
- [ ] `pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -q`
- [ ] `rg -n "non_agentic|agentic_late_stage|late_stage_mode" src/fitcv/pipeline.py src/fitcv_cp/worker_job.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py -S`

**Exit Criteria:**
- backend or legacy mode toggles no longer alter AI decision path

### Task 5: Preserve backend symmetry as persistence-only difference

**Purpose:**
- guarantee equivalence across sqlite/bigquery for AI outcomes

**Files:**
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_pipeline.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`

**Preconditions:**
- Task 4 complete
- deterministic provider/test doubles available

**Steps:**
- [ ] Step 1: Add paired sqlite/bigquery parity tests using identical fixture inputs.
- [ ] Step 2: Assert equal AI stage decision/provenance payloads across backends.
- [ ] Step 3: Restrict allowed diff set to persistence substrate metadata only.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_worker_job.py tests/test_pipeline.py -q`

**Exit Criteria:**
- parity tests fail on AI-plane drift and pass on allowed persistence-only differences

### Task 6: Final deprecation gates and repo validation closeout

**Purpose:**
- close migration with explicit removal gates and contract validation

**Files:**
- Inspect: `docs/configuration.md`
- Inspect: `docs/pipeline.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Verify: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [ ] Step 1: Document sunset criteria and enforcement timing for auth aliases and legacy fields.
- [ ] Step 2: Run planning/doc lineage refresh if metadata graph changed.
- [ ] Step 3: Run full fast repo contract validation.

**Verification:**
- [ ] `python scripts/generate_planning_lineage.py`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- migration plan artifacts, docs, and validation gates are aligned and green

## Verification

- `pytest tests/test_config.py tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py -q`
- `pytest tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py -q`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
