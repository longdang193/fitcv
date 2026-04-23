---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-22T12:48:00+02:00
change_id: 2026-04-22-phase-8-settings-performance-evidence-backfill
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the phase 8 settings and performance evidence backfill.
parent_workstream: none
targets:
  - docs/features/settings_system/lineage.generated.yaml
  - docs/features/pipeline_performance/lineage.generated.yaml
  - src/fitcv/config.py
  - src/fitcv/embeddings.py
  - src/fitcv/enrich.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/worker_job.py
  - tests/test_config.py
  - tests/test_embeddings.py
  - tests/test_enrich.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_worker_job.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
related_features:
  - settings_system
  - pipeline_performance
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 8 Settings And Performance Evidence Backfill Implementation Plan

**Feature Source:** `docs/features/settings_system/feature.source.yaml`, `docs/features/pipeline_performance/feature.source.yaml`  
**Feature Contract:** `docs/features/settings_system/settings_system.yaml`, `docs/features/pipeline_performance/pipeline_performance.yaml`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-12-35-phase-8-settings-performance-evidence-backfill-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task. Keep mappings sparse and drop any weak mapping instead of forcing evidence.

**Goal:** Extend the direct-evidence pilot to selected `settings_system` and `pipeline_performance` capabilities without broad metadata spray.

**Architecture:** This phase adds explicit capability ownership to high-signal Python files and adds `@proves` markers to tests that already verify the selected behavior. It does not change the lineage schema or the generator contract. Validation is extended only for capabilities with trustworthy direct code and test evidence.

**Key Invariants:**
- Direct code evidence must come from file metadata, not inferred filenames.
- Direct test evidence must come from truthful `@proves` markers.
- Generated contracts, lineage, and discovery are refreshed by `scripts/sync_architecture_docs.py`, not hand-edited.
- Weak or ambiguous capability mappings stay partial rather than receiving noisy evidence.

**Rollout / Revert:**  
- rollback_trigger: Phase 8 tags prove noisy, selected pilot enforcement blocks valid repo states, or regenerated lineage over-attributes ownership.  
- rollback_method: Remove Phase 8 metadata/proof markers and pilot enforcement entries, rerun `scripts/sync_architecture_docs.py`, and return to the Phase 7 checkpoint.

---

## Doc Update Matrix

- Feature source:
  - `docs/features/settings_system/feature.source.yaml` reviewed, expected unchanged
  - `docs/features/pipeline_performance/feature.source.yaml` reviewed, expected unchanged
- Feature contract:
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/pipeline_performance/pipeline_performance.yaml`
- Feature lineage:
  - `docs/features/settings_system/lineage.generated.yaml`
  - `docs/features/pipeline_performance/lineage.generated.yaml`
- Feature history:
  - `docs/features/settings_system/history.md` reviewed, expected unchanged
  - `docs/features/pipeline_performance/history.md` reviewed, expected unchanged
- Stage source: `none`
- Stage contracts: `docs/stages/*.yaml`
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs:
  - `docs/operating_system/feature-lifecycle.md`
- README: `none`
- Generated discovery:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_by_status.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-12-35-phase-8-settings-performance-evidence-backfill-spec.md`
- `docs/superpowers/plans/2026-04-22-12-48-phase-8-settings-performance-evidence-backfill-plan.md`
- `src/fitcv/config.py`
- `src/fitcv/embeddings.py`
- `src/fitcv/enrich.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/settings_store.py`
- `src/fitcv_cp/worker_job.py`
- `tests/test_config.py`
- `tests/test_embeddings.py`
- `tests/test_enrich.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_settings_schema.py`
- `tests/test_fitcv_cp/test_settings_store.py`
- `tests/test_fitcv_cp/test_worker_job.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`

**Files expected to be reviewed but not manually changed**

- `docs/features/settings_system/feature.source.yaml`
- `docs/features/pipeline_performance/feature.source.yaml`
- `docs/features/settings_system/history.md`
- `docs/features/pipeline_performance/history.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- `tests/test_sync_architecture_docs.py`
- `tests/test_validate_adoption_shape.py`
- `README.md`
- `docs/intent/*.md`
- `docs/operating_system/agent_memory/*`

**Generated outputs to refresh**

- `docs/features/settings_system/settings_system.yaml`
- `docs/features/settings_system/lineage.generated.yaml`
- `docs/features/pipeline_performance/pipeline_performance.yaml`
- `docs/features/pipeline_performance/lineage.generated.yaml`
- `docs/generated/*`
- `docs/stages/*.yaml`

## Selected Capability Mappings

### Settings System

- `src/fitcv/config.py`
  - `settings_system.baseline-default-hydration`
  - `settings_system.cv-analysis-alignment-settings`
  - `settings_system.cv-generation-settings`
- `src/fitcv_cp/settings_schema.py`
  - `settings_system.settings-schema-registry`
  - `settings_system.retrieval-settings`
  - `settings_system.ranking-settings`
  - `settings_system.cv-analysis-alignment-settings`
  - `settings_system.cv-generation-settings`
- `src/fitcv_cp/settings_store.py`
  - `settings_system.bigquery-backed-pipeline-settings-store`
- `src/fitcv_cp/bq_store.py`
  - `settings_system.trigger-time-effective-settings-snapshot`
- `src/fitcv_cp/worker_job.py`
  - `settings_system.settings-used-exports`

### Pipeline Performance

- `src/fitcv/enrich.py`
  - `pipeline_performance.gemini-structured-output-with-response-schema-and-pydantic`
  - `pipeline_performance.fallback-path-for-unparseable-responses`
  - `pipeline_performance.fingerprint-based-enrich-result-reuse-happens-before-llm-enrichment-using-normalized-raw-job-inputs`
  - `pipeline_performance.enrich-contract-fingerprinting-invalidates-reuse-automatically-when-prompt-model-schema-behavior-changes`
  - `pipeline_performance.shared-structured-jobs-reuse-lookup-avoids-redundant-enrich-calls-while-only-fresh-rows-are-upserted-back-into-the-shared-table`
- `src/fitcv/embeddings.py`
  - `pipeline_performance.shortlist-now-builds-a-stable-structured-embedding-input-signature-before-generating-job-summary-vectors`
  - `pipeline_performance.shortlist-reuses-the-latest-stored-embedding-row-for-a-job-url-only-when-both-the-structured-signature-and-embedding-contract-fingerprint-still-match`
  - `pipeline_performance.fresh-shortlist-embeddings-persist-signature-metadata-so-later-runs-can-skip-repeated-embedding-work-safely`
- `src/fitcv_cp/worker_job.py`
  - `pipeline_performance.results-json-now-keeps-only-compact-job-ledger-fields-instead-of-repeating-full-job-snapshots-heavy-score-explanation-internals-and-full-cv-bodies-already-represented-elsewhere`

Deferred from the spec candidate set:

- `pipeline_performance.cv-analysis-now-uses-bounded-semantic-lift-for-required-skill-and-role-channels-instead-of-reserving-semantic-work-only-for-domain-and-responsibility-alignment`
- `pipeline_performance.ranked-jobs-with-authoritative-reranker-fit-label-skip-now-stop-before-evidence-retrieval-gap-computation-and-semantic-alignment-inside-cv-analysis`

Reason: the obvious proof surfaces are not part of this small settings/performance metadata batch, so these should stay partial until a dedicated `cv_analysis` / reranker skip batch.

## Tasks

### Task 1: Seed Settings Code Ownership

- [x] Replace or update top-of-file metadata in `src/fitcv/config.py`.
- [x] Replace or update top-of-file metadata in `src/fitcv_cp/settings_schema.py`.
- [x] Replace or update top-of-file metadata in `src/fitcv_cp/settings_store.py`.
- [x] Replace or update top-of-file metadata in `src/fitcv_cp/bq_store.py`.
- [x] Replace or update top-of-file metadata in `src/fitcv_cp/worker_job.py`.
- [x] Keep the mappings exactly to the selected settings capabilities above.

### Task 2: Seed Performance Code Ownership

- [x] Replace or update top-of-file metadata in `src/fitcv/enrich.py`.
- [x] Replace or update top-of-file metadata in `src/fitcv/embeddings.py`.
- [x] Add selected performance capability metadata to `src/fitcv_cp/worker_job.py`.
- [x] Keep deferred performance capabilities untagged.

### Task 3: Seed Truthful Proof Metadata

- [x] Add `@proves` markers to representative config tests for baseline hydration and CV settings.
- [x] Add `@proves` markers to settings schema tests for schema registry, retrieval, ranking, CV analysis, and CV generation settings.
- [x] Add `@proves` markers to settings store tests for BigQuery-backed settings persistence.
- [x] Add `@proves` markers to BQ store tests for trigger-time effective settings snapshots.
- [x] Add `@proves` markers to worker job tests for settings-used exports and compact results exports.
- [x] Add `@proves` markers to enrich tests for structured output, fallback parsing, enrich fingerprinting, and reusable structured job lookup.
- [x] Add `@proves` markers to embedding tests for shortlist signature, reuse, and persisted reuse metadata.

### Task 4: Extend Enforcement And Governance

- [x] Add the completed Phase 8 capability set to `repo_config/adoption-mode.yaml` under the direct-evidence pilot section.
- [x] Update `docs/operating_system/feature-lifecycle.md` to state Phase 8 extends the pilot to settings/performance but still permits partial evidence elsewhere.

### Task 5: Regenerate And Measure

- [x] Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Record post-sync gap counts for `settings_system`, `pipeline_performance`, and repo-wide totals.
- [x] Confirm selected capabilities now have code and tests evidence in lineage.

### Task 6: Verify And Close

- [x] Run focused pytest:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_enrich.py tests/test_embeddings.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
- [x] Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`.
- [x] Run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`.
- [x] Run `git diff --check`.
- [x] Mark the Phase 8 spec and plan completed with execution notes.
- [x] Decide memory disposition and document it in the final response.

## Validation Commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_enrich.py tests/test_embeddings.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py
.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py
.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check
.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py
git diff --check
```

## Execution Notes

Status: `completed`

Completed scope:

- selected settings capabilities now have direct code and test evidence
- selected pipeline performance capabilities now have direct code and test evidence
- deferred `cv_analysis` / reranker skip performance capabilities remain partial by design
- touched tests were normalized to keep one top-level `@meta` block and direct `@proves` markers on proving tests

Measured result:

- `settings_system`: `missing_code_evidence=40` / `missing_test_evidence=40`
  before Phase 8, `22` / `22` after Phase 8
- `pipeline_performance`: `missing_code_evidence=38` /
  `missing_test_evidence=38` before Phase 8, `20` / `20` after Phase 8
- repo-wide totals: `218` / `218` before Phase 8, `182` / `182` after Phase 8

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_enrich.py tests/test_embeddings.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
  passed with `352 passed, 2 skipped`
- final sync/check/validator/whitespace evidence is recorded in the session
  closeout
