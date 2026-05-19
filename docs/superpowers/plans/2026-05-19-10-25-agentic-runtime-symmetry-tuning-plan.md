---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: agentic-runtime-throughput-symmetry-implementation
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-05-19-10-05-agentic-runtime-symmetry-tuning-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv/config.py
  - src/fitcv/pipeline.py
  - src/fitcv/ai_score.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/synonym_proposals.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_ai_score.py
related_features: []
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement stage-symmetric Advanced Runtime Tuning contract so throughput controls use one canonical stage-runtime model across agentic stages, while preserving full compatibility for legacy enrichment/reranking tuning keys.

## Key Deliverables

### Deliverable 1: Canonical stage-runtime throughput contract in settings schema

`src/fitcv_cp/settings_schema.py` defines and validates stage-runtime throughput controls as primary surfaces, with deterministic alias fallback from legacy flat keys.

### Deliverable 2: Runtime wiring for ranking and late-stage agentic paths

`pipeline`, `ai_score`, and agentic generation/analysis/synonym paths consume canonical stage-runtime throughput values (with fallback), removing enrich-only bias.

### Deliverable 3: Symmetric operator IA/UI metadata

Settings IA metadata and rendered settings cards expose truthful, stage-symmetric throughput ownership and runtime-used semantics.

### Deliverable 4: Regression-safe migration proof

Targeted tests plus GitNexus scope checks prove compatibility and bounded blast radius for this migration.

## Task/Wave Breakdown

### Task 1: Impact map and migration guardrails

**Purpose:**
- establish safe execution order and risk gates before symbol edits

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Verify: `docs/superpowers/plans/2026-05-19-10-25-agentic-runtime-symmetry-tuning-plan.md`

**Preconditions:**
- parent spec approved for implementation
- GitNexus index fresh

**Steps:**
- [ ] Step 1: run `.\scripts\get_gitnexus_freshness.ps1`; refresh via `npx gitnexus analyze` if stale.
- [ ] Step 2: run `npx gitnexus impact --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" settings_ia_contract_for_key --direction upstream`.
- [ ] Step 3: run `npx gitnexus impact --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" run_pipeline --direction upstream`.
- [ ] Step 4: run `npx gitnexus impact --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" analyze_ranked_job --direction upstream`.
- [ ] Step 5: run `npx gitnexus impact --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT" generate_from_analysis --direction upstream`.
- [ ] Step 6: record risk notes and containment order; stop if any impact reports `HIGH`/`CRITICAL`.

**Verification:**
- [ ] all edited symbols have captured upstream impact evidence
- [ ] no unreviewed high-risk symbol enters modification set

**Exit Criteria:**
- implementation order and test scope derived from measured graph impact

### Task 2: Canonical schema + alias resolution layer

**Purpose:**
- introduce stage-runtime canonical keys and keep legacy key compatibility

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv/config.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 1 complete
- existing legacy-key validation behavior baselined

**Steps:**
- [ ] Step 1: add canonical stage-runtime key family in settings schema for throughput controls (sleep/concurrency + bounded batch where valid).
- [ ] Step 2: implement deterministic precedence resolver (canonical > legacy alias > declared default).
- [ ] Step 3: wire apply/coerce/validate paths so canonical persistence and fallback reads both work.
- [ ] Step 4: mark legacy keys with explicit compatibility/deprecation metadata without removing support.
- [ ] Step 5: add schema tests for precedence matrix and value validation parity.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py -k "runtime or throughput or enrichment or rerank or stage"` passes

**Exit Criteria:**
- canonical contract active with tested alias fallback and no regression in legacy-only input

### Task 3: Runtime consumption wiring across stages

**Purpose:**
- apply canonical throughput settings to real execution paths

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv_cp/synonym_proposals.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_ai_score.py`

**Preconditions:**
- Task 2 complete
- resolver API for effective stage-runtime values available

**Steps:**
- [ ] Step 1: route ranking delay to canonical `stage_runtime.ranking.sleep_secs` with legacy fallback.
- [ ] Step 2: route late-stage generation/analysis delays/concurrency to canonical stage-runtime controls where stage path supports them.
- [ ] Step 3: wire synonym-triage runtime throttling path to canonical stage-runtime controls at control-plane layer.
- [ ] Step 4: preserve existing enrich path behavior and ensure no silent no-op knobs.
- [ ] Step 5: extend or add tests proving each wired stage actually consumes its configured effective value.

**Verification:**
- [ ] `pytest tests/test_pipeline.py -k "enrichment_parallelism or runtime"` passes
- [ ] `pytest tests/test_pipeline_agentic_late_stage.py -q` passes
- [ ] `pytest tests/test_ai_score.py -k "sleep or rerank"` passes

**Exit Criteria:**
- ranking and late-stage agentic paths consume canonical throughput controls with compatibility intact

### Task 4: IA/UI symmetry and contract truthfulness

**Purpose:**
- ensure operator-facing settings metadata matches runtime reality

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Task 3 complete
- stage-runtime key set stabilized

**Steps:**
- [ ] Step 1: update IA metadata derivation for canonical throughput settings (`stage`, `workflow_stages`, `decision_area`, `runtime_used`, risk).
- [ ] Step 2: ensure legacy alias keys render as compatibility surfaces without conflicting primary ownership.
- [ ] Step 3: adjust settings page grouping/filter logic for canonical stage-runtime entries.
- [ ] Step 4: add tests that assert badge/metadata truthfulness and stage symmetry in rendered settings HTML/context.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py -k "ia_contract or decision_area or runtime_used"` passes
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "settings and Runtime-used"` passes

**Exit Criteria:**
- UI and IA metadata are symmetric and faithful to runtime behavior

### Task 5: Final verification, scope check, and handoff

**Purpose:**
- prove bounded change and prepare execution-closeout handoff

**Files:**
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `tests/test_ai_score.py`
- Verify: `docs/superpowers/specs/2026-05-19-10-05-agentic-runtime-symmetry-tuning-spec.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: run full targeted test set for schema/app/pipeline/agentic/ranking surfaces.
- [ ] Step 2: run `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"` and compare impacted symbols against plan targets.
- [ ] Step 3: run `python scripts/hooks/run_validator.py --fast`.
- [ ] Step 4: document any residual migration debt (legacy alias retirement checkpoints) in follow-up notes.

**Verification:**
- [ ] all targeted test commands pass
- [ ] GitNexus scope output aligned with planned change envelope
- [ ] repo hook subset validator passes

**Exit Criteria:**
- implementation evidence satisfies spec validation expectations and bounded-scope guarantees

## Verification

- `pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -k "settings" -q`
- `pytest tests/test_pipeline.py -k "enrichment_parallelism or runtime" -q`
- `pytest tests/test_pipeline_agentic_late_stage.py -q`
- `pytest tests/test_ai_score.py -k "sleep or rerank" -q`
- `npx gitnexus detect-changes --repo "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
