---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: pipeline-settings-decision-first-categorization-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-17-21-54-pipeline-settings-decision-first-categorization-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
  - docs/superpowers/execution_context_packs/pipeline-settings-decision-focused-ia-v4/latest.md
related_features:
  - settings_system
  - cv_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Implement decision-first Pipeline Settings UX that preserves `Basic | Advanced | All`, introduces symmetric stage and control-surface categorization, decomposes oversized agentic controls, and keeps diagnostics always advanced.

## Delta Update (Real Stage Alignment)

Adjust stage-setting categorization to use canonical runtime stage IDs from `PIPELINE_STAGE_SEQUENCE` in `src/fitcv/pipeline.py`:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`
- `cross_stage` (non-stage runtime guardrails only)

## Key Deliverables

### Deliverable 1: Canonical categorization and placement contract in app/schema

All settings keys map deterministically to one stage and one decision-area with no duplicate ownership, including explicit decomposition of current agentic blocks.

### Deliverable 2: Settings page IA simplification and filter behavior

Settings page removes non-decision top strips, uses `Basic | Advanced | All` complexity filter, replaces domain filter wording with stage filter, adds control-surface filter, and preserves full discoverability in `All`.

### Deliverable 3: Agentic decomposition with semantic tuning promoted to Basic

Current monolithic/advanced agentic tuning is split into smaller decision blocks (`Enablement`, `Automation`, `Quality Targets`, `Throughput`, `Diagnostics`) with semantic weights and pool controls visible in Basic.

### Deliverable 4: Regression-proof behavior and documentation alignment

Tests cover filter interactivity and placement invariants; execution context pack updated with implementation evidence and next-action state.

### Deliverable 5: Real pipeline stage mapping contract replaces synthetic stage buckets

Synthetic buckets (`intake_filtering`, `scoring`, `cv_composition`, `agentic_processing`, `runtime_operations`) are removed from stage filter ownership and replaced by real stage ownership with `cross_stage` reserved for runtime guardrails.

## Task/Wave Breakdown

### Task 1: Encode stage + control-surface + decision-area mapping contract

**Purpose:**
- establish SSOT categorization model used by template and JS filters

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- approved spec `2026-05-17-21-54-pipeline-settings-decision-first-categorization-spec.md`

**Steps:**
- [x] Add explicit per-key metadata derivation for `stage`, `control_surface`, `decision_area`, and `complexity_view`.
- [x] Add deterministic mapping for all keys currently rendered on settings page.
- [x] Ensure diagnostics-tagged keys are always `Advanced`.
- [x] Add helper accessors for template context counts and filter chip payloads.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- [x] HTML inspection confirms metadata is available in app entry model and ready for template data attrs.

**Exit Criteria:**
- every rendered key has stable category metadata with no fallback ambiguity

### Task 2: Recompose settings page structure to decision-minimum top surface

**Purpose:**
- remove confusing non-decision blocks and anchor page on direct setting decisions

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Remove top strips: live provider/model/authority, run truth check, run CTA.
- [x] Keep compact page title + one-line status only.
- [x] Render complexity chips with exact labels `Basic | Advanced | All`.
- [x] Render filter rows: `Stage` and `Control Surface` (interactive, aria state tracked).

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- [x] Rendered HTML no longer contains removed block labels and includes new filter labels.

**Exit Criteria:**
- top section contains only decision-relevant controls and status

### Task 3: Decompose oversized agentic controls into symmetric sub-blocks

**Purpose:**
- make agentic configuration scannable and action-oriented with invariant block naming

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [x] Split current agentic card into sub-blocks: `Enablement`, `Automation`, `Quality Targets`, `Throughput`, `Diagnostics`.
- [x] Move semantic weight keys + `channel_pool_size` to Basic agentic sub-blocks.
- [x] Keep metadata-only semantic model key under diagnostics/advanced presentation.
- [x] Ensure block ordering is symmetric with other stage blocks.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- [x] Manual browser check: agentic controls no longer one monolith; semantic tuning visible in Basic.

**Exit Criteria:**
- agentic surface is segmented into bounded decision groups with preserved advanced diagnostics

### Task 4: Implement combined filter logic and empty-state guidance

**Purpose:**
- ensure users never hit confusing “nothing visible” states without explanation

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [x] Update JS filter engine to apply complexity + stage + control-surface axes deterministically.
- [x] Add explicit empty-state message with reset guidance when filters hide all rows.
- [x] Preserve `All` as complete searchable view.
- [x] Keep action status feedback inline (no blocking alert popups).

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- [x] Browser smoke: each filter axis changes result set and empty-state guidance appears when appropriate.

**Exit Criteria:**
- filtering behavior is predictable and self-explanatory

### Task 5: Update tests + execution context evidence

**Purpose:**
- lock contract against regressions and keep planning execution state synchronized

**Files:**
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `docs/superpowers/execution_context_packs/pipeline-settings-decision-focused-ia-v4/latest.md`
- Optional mirror: `artifacts/execution_context_pack.md`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [x] Replace obsolete assertions tied to removed top strips and old filter labels.
- [x] Add assertions for `Basic | Advanced | All`, `Stage`, and `Control Surface` controls.
- [x] Add assertions for agentic sub-block decomposition and diagnostics advanced-only rule.
- [x] Record completed evidence and next-action state in canonical execution context pack.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- [x] `python scripts/validate_checkpoint_packs.py`
- [x] `python scripts/validate_planning_lifecycle.py --strict`
- [x] `python scripts/validate_repo_contracts.py --fast`

**Exit Criteria:**
- tests and execution context pack both reflect finalized behavior contract

### Task 6: Migrate stage filter + metadata to real pipeline stages

**Purpose:**
- align settings stage chips and per-key metadata with canonical runtime stages

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `docs/superpowers/execution_context_packs/pipeline-settings-decision-focused-ia-v4/latest.md`

**Preconditions:**
- Tasks 1-5 complete baseline

**Steps:**
- [x] Replace stage-id derivation:
  - `intake_filtering -> normalize | enrich | rule_filter | shortlist` (per key)
  - `scoring -> ranking`
  - `cv_composition -> cv_generation`
  - `agentic_processing -> enrich | rule_filter | cv_analysis | cv_generation` (per key)
  - `runtime_operations -> cross_stage`
- [x] Apply per-key mapping contract:
  - `normalize`: none
  - `enrich`: `global_job_filters.*`, `enrichment_*`, `synonym_management.{propose_enabled,auto_triage_recommendation_enabled,triage_recommendation_reuse_enabled,auto_apply_recommendation_enabled,apply_to_run_enabled,promote_global_enabled,auto_promote_global_enabled}`
  - `rule_filter`: `rule_filter.selected_filters`, plus `synonym_management.{apply_to_run_enabled,promote_global_enabled}`
  - `shortlist`: `pipeline.vector_search_top_n`
  - `ranking`: `pipeline.ai_score_top_n`, `pipeline.final_top_n`, `rerank_sleep_secs`, `ranking_weights.*`, `preference_fit_weights.*`, `fit_label_thresholds.*`, `gap_thresholds.*`
  - `cv_analysis`: `pipeline.evidence_top_k`, `cv_analysis.semantic_alignment.*`, `cv.agentic_late_stage.enabled`
  - `cv_generation`: `cv_generation_model`, `cv_preset`, `cv_*_enabled`, `cv_max_pages`, `synonym_management.auto_accept_ai_action_enabled`
  - `cross_stage`: `run_lifecycle.max_runtime_minutes`
- [x] Ensure stage chips render exactly:
  - `All | normalize | enrich | rule_filter | shortlist | ranking | cv_analysis | cv_generation | cross_stage`
- [x] Preserve control-surface filter and `Basic | Advanced | All` behavior unchanged.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- [x] Manual browser check: each stage chip shows expected settings and no empty chips except `normalize` (expected none).
- [x] `python scripts/validate_checkpoint_packs.py`
- [x] `python scripts/validate_planning_lifecycle.py --strict`

**Exit Criteria:**
- stage filter is fully canonical, MECE by stage ownership, and matches runtime stage vocabulary

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -q -k settings`
- `python scripts/validate_checkpoint_packs.py`
- `python scripts/validate_planning_lifecycle.py --strict`
- `python scripts/validate_repo_contracts.py --fast`

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
