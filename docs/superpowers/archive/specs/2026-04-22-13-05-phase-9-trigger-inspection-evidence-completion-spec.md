---
layer: operating_system
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/features/trigger_run_management/trigger_run_management.yaml
  - docs/features/trigger_run_management/lineage.generated.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_worker_job.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
related_features:
  - trigger_run_management
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 9 Trigger And Inspection Evidence Completion Spec

## Triage

Layer: `operating_system`  
Feature type: `CHANGE`  
Summary: Extend the direct-evidence pilot to the remaining high-confidence
`trigger_run_management` and `inspection_debugging` capabilities while cleaning
source-level YAML anchor noise in their human-owned feature sources.  
Reasoning: After Phase 8, the largest remaining evidence gaps are
`trigger_run_management` at `30/30` and `inspection_debugging` at `28/28`.
Both features already participated in the Phase 7 pilot, but many capabilities
still have only generated/spec/plan evidence. Their strongest remaining code and
test surfaces are concentrated in the control-plane app, BQ store, queue, and
worker tests, so they are good candidates for a second bounded pass.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- Generated contracts and `lineage.generated.yaml` remain generated outputs.
- Direct code evidence must come from explicit file metadata.
- Direct test evidence must come from truthful `@proves <capability_id>` markers.
- Capability mappings must remain sparse and materially true.
- Partial lineage remains acceptable for capabilities without direct proof.
- Do not tag files only to reduce counts.
- Human-owned YAML source files should avoid noisy anchors like `&id001` and
  `*id001` when explicit repeated lists are more reviewable.

Dependencies:

- Phase 7 spec: `docs/superpowers/archive/specs/2026-04-22-12-02-phase-7-direct-evidence-backfill-spec.md`
- Phase 8 spec: `docs/superpowers/archive/specs/2026-04-22-12-35-phase-8-settings-performance-evidence-backfill-spec.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- existing Python metadata and `@proves` parser behavior

Affected stages:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

Affected features:

- `trigger_run_management`
- `inspection_debugging`

Primary lens: `targeted evidence completion`

Affected docs:

- feature_source:
  - `docs/features/trigger_run_management/feature.source.yaml`
  - `docs/features/inspection_debugging/feature.source.yaml`
- feature_yaml:
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
- feature_lineage:
  - `docs/features/trigger_run_management/lineage.generated.yaml`
  - `docs/features/inspection_debugging/lineage.generated.yaml`
- feature_history:
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/inspection_debugging/history.md`
- stage_source: `none`
- stage_contract:
  - `docs/stages/*.yaml`
- feature_docs: `none`
- cross_cutting_docs: `none`
- operating_system_docs:
  - `docs/operating_system/feature-lifecycle.md`
- readme: `none`
- generated:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_by_status.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

Generated refresh required: `yes`  
Capability IDs: `selected trigger_run_management and inspection_debugging capabilities`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Problem

Phase 7 seeded the first direct evidence for `trigger_run_management` and
`inspection_debugging`, but these two features now have the highest remaining
gap counts:

| Feature | Missing code | Missing tests |
|---|---:|---:|
| `trigger_run_management` | 30 | 30 |
| `inspection_debugging` | 28 | 28 |

The remaining gaps are not schema bugs. They mean many capabilities still lack
explicit implementation ownership and direct proof markers. At the same time,
both feature source files currently contain YAML aliases in `stage_participation`
lists, such as `&id001` and `*id001`. That is valid YAML, but it makes the
human-owned source harder to review and conflicts with the readability direction
we already applied to generated lineage.

## Goal

Complete a second bounded evidence pass for `trigger_run_management` and
`inspection_debugging` by:

1. selecting high-confidence capabilities with obvious code/test surfaces
2. adding sparse code ownership metadata only where files materially implement
   the named capability
3. adding truthful `@proves` markers only where tests directly verify the named
   behavior
4. extending pilot enforcement only for the completed mappings
5. replacing source-level YAML anchors in the two feature source files with
   explicit stage participation lists
6. regenerating contracts, lineage, and generated discovery outputs
7. recording before/after gap counts

## Non-Goals

This phase does not:

- eliminate all evidence gaps across the repo
- require every capability in the two features to become `complete`
- change the evidence-oriented lineage schema
- infer evidence from filenames
- tag broad app files with every nearby capability
- migrate `history.md` to the starter partial-generated pattern
- solve remaining gaps for `run_lifecycle_controls`, `ui_consistency_theming`,
  or `admin_control_plane_core`

## Candidate Capability Set

The implementation plan must confirm exact mappings before editing. Drop any
candidate that does not have direct proof.

### Trigger Run Management

Preferred Phase 9 candidates:

- `trigger_run_management.runs-list-management`
- `trigger_run_management.run-detail-actions`
- `trigger_run_management.job-input-modes`
- `trigger_run_management.candidate-profile-input-modes`
- `trigger_run_management.synonym-overlay-at-trigger`
- `trigger_run_management.shared-stage-progress`
- `trigger_run_management.synonym-overlay-replacement`
- `trigger_run_management.run-health-surface`
- `trigger_run_management.run-owned-artifact-exports`
- `trigger_run_management.stage-artifact-downloads`
- `trigger_run_management.synonym-overlay-inspection`
- `trigger_run_management.run-results-export`
- `trigger_run_management.shortlist-debug-exports`
- `trigger_run_management.decision-chain-outcomes`
- `trigger_run_management.reranker-fit-authority`

Likely implementation surfaces:

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/queue.py`
- `src/fitcv_cp/worker_job.py`

Likely proof surfaces:

- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_queue.py`
- `tests/test_fitcv_cp/test_worker_job.py`

### Inspection Debugging

Preferred Phase 9 candidates:

- `inspection_debugging.synonym-overlay-inspection`
- `inspection_debugging.run-owned-artifact-exports`
- `inspection_debugging.settings-used-export`
- `inspection_debugging.results-ledger-inspection`
- `inspection_debugging.stage-transition-diagnostics`
- `inspection_debugging.prompt-provenance-diagnostics`
- `inspection_debugging.ranking-diagnostics`
- `inspection_debugging.shortlist-diagnostics`
- `inspection_debugging.reuse-diagnostics`
- `inspection_debugging.quality-metrics-diagnostics`
- `inspection_debugging.enriched-job-debug-export`
- `inspection_debugging.rule-filter-diagnostics`

Likely implementation surfaces:

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv/enrich.py`
- `src/fitcv/embeddings.py`
- `src/fitcv/ranking.py`

Likely proof surfaces:

- `tests/test_fitcv_cp/test_app.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `tests/test_enrich.py`
- `tests/test_embeddings.py`
- `tests/test_ranking.py`

Deferred unless direct proof is obvious:

- `inspection_debugging.cv-analysis-diagnostics`
- `inspection_debugging.cv-generation-diagnostics`

Reason: these may need a focused `cv_analysis` / `cv_generation` diagnostic
batch rather than a control-plane inspection batch.

## Proposed Shape

### 1. Mapping Review

The implementation plan should first inspect the candidate files and list exact
capability-to-file/test mappings. It should explicitly defer weak mappings.

### 2. Source-Level YAML Anchor Cleanup

Normalize the two human-owned feature source files so `stage_participation`
uses explicit lists instead of YAML aliases. This is a source readability fix,
not generated lineage output cleanup.

Targets:

- `docs/features/trigger_run_management/feature.source.yaml`
- `docs/features/inspection_debugging/feature.source.yaml`

### 3. Sparse Code Metadata

Update existing top-of-file metadata only where the file directly owns the
selected capability. `src/fitcv_cp/app.py` is broad, so it should receive only
capabilities for UI routing, render, actions, and downloads it materially owns.
Persistence helpers and worker snapshots should stay in `bq_store.py` and
`worker_job.py`.

### 4. Truthful Proof Markers

Add `@proves` only to tests with direct assertions. Prefer one representative
proof test per capability. Do not tag fixture setup, broad smoke tests, or tests
that only happen to exercise nearby routes.

### 5. Pilot Enforcement Extension

Extend `repo_config/adoption-mode.yaml` only for capabilities that receive both
direct code and test evidence during this phase.

### 6. Regeneration And Measurement

Run:

- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`

Measure:

- updated `trigger_run_management` gap counts
- updated `inspection_debugging` gap counts
- updated repo-wide totals
- selected capabilities that reached `completeness_status: complete`
- selected capabilities intentionally left `partial`

## Acceptance Criteria

Phase 9 is complete when:

1. a Phase 9 implementation plan exists with exact selected mappings
2. selected `trigger_run_management` capabilities have truthful code and proof
   evidence
3. selected `inspection_debugging` capabilities have truthful code and proof
   evidence
4. pilot enforcement covers only completed mappings
5. the two feature source files no longer contain YAML anchors for
   `stage_participation`
6. generated feature contracts and lineage are refreshed
7. generated discovery files are refreshed
8. focused tests for touched code pass
9. `scripts/sync_architecture_docs.py --check` passes
10. `scripts/validate_adoption_shape.py` passes
11. `git diff --check` has no whitespace errors
12. post-phase gap counts are recorded in the implementation plan and spec

## Risks And Guardrails

- Risk: `src/fitcv_cp/app.py` becomes over-tagged because it touches many admin
  flows. Guardrail: tag only capabilities with direct route/render/action
  ownership.
- Risk: inspection and trigger capabilities overlap. Guardrail: use trigger IDs
  for control behavior and inspection IDs for diagnostic visibility.
- Risk: source YAML anchor cleanup creates noisy diffs. Guardrail: limit it to
  the two targeted feature source files.
- Risk: tests prove rendering presence but not behavior. Guardrail: only use
  `@proves` when assertions check the named behavior, action, export, or
  diagnostic state.

## Validation Plan

Minimum validation:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_enrich.py tests/test_embeddings.py tests/test_ranking.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Rollback Plan

If Phase 9 over-attributes evidence or validation becomes too strict:

1. remove Phase 9 metadata/proof markers
2. remove Phase 9 pilot enforcement entries
3. restore the two feature sources to their prior semantic content while
   preserving source validity
4. rerun `scripts/sync_architecture_docs.py`
5. rerun validation to return to the Phase 8 baseline

## Execution Notes

Status: `completed`

Completed: 2026-04-22

Implementation plan:
`docs/superpowers/plans/2026-04-22-13-18-phase-9-trigger-inspection-evidence-completion-plan.md`

Outcome:

- `trigger_run_management` evidence gaps reduced from `30/30` to `0/0`.
- `inspection_debugging` evidence gaps reduced from `28/28` to `4/4`.
- Remaining `inspection_debugging` gaps are the intentionally deferred
  `cv-analysis-diagnostics` and `cv-generation-diagnostics` capabilities.
- Repo-wide evidence gaps reduced from `182/182` to `128/128`.
- Source YAML anchors were removed from the two targeted human-owned feature
  source files.

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
  passed with `306 passed`.
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
  passed.
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with only LF/CRLF working-copy warnings.
