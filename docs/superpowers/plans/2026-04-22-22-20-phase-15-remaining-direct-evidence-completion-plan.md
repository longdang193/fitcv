---
layer: change
artifact_type: plan
status: completed
parent_workstream: none
targets:
  - docs/superpowers/archive/specs/2026-04-22-22-05-phase-15-remaining-direct-evidence-completion-spec.md
  - docs/superpowers/plans/2026-04-22-22-20-phase-15-remaining-direct-evidence-completion-plan.md
  - src/fitcv/enrich.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv/config.py
  - tests/test_enrich.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_pipeline.py
  - tests/test_config.py
  - repo_config/adoption-mode.yaml
  - docs/features/bounded_parallel_enrichment/lineage.generated.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/generated/capability_lineage.yaml
related_features:
  - bounded_parallel_enrichment
  - cv_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 15 Remaining Direct-Evidence Completion Implementation Plan

**Feature Source:** `docs/features/bounded_parallel_enrichment/feature.source.yaml`, `docs/features/cv_system/feature.source.yaml`  
**Feature Contract:** `docs/features/bounded_parallel_enrichment/bounded_parallel_enrichment.yaml`, `docs/features/cv_system/cv_system.yaml`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-22-05-phase-15-remaining-direct-evidence-completion-spec.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** completed

**Goal:** Close the remaining 12 repo-wide direct-evidence gaps with truthful
code ownership and direct proof tests, executing `bounded_parallel_enrichment`
first and `cv_system` second.

## Mapping Audit

| Capability | Code owner(s) | Proof test(s) | Confidence | Notes |
| --- | --- | --- | --- | --- |
| `bounded_parallel_enrichment.enrichment-batch-size-setting` | `src/fitcv_cp/settings_schema.py`, `src/fitcv/enrich.py` | `test_enrichment_parallelism_keys_registered`, `test_enrichment_batch_size_apply_writes_correct_path`, `test_run_pipeline_forwards_enrichment_parallelism_config_to_enrich_batch` | complete_candidate | Setting is defined in control-plane schema and consumed by `enrich_batch`. |
| `bounded_parallel_enrichment.enrichment-concurrency-setting` | `src/fitcv_cp/settings_schema.py`, `src/fitcv/enrich.py` | `test_enrichment_parallelism_keys_registered`, `test_enrichment_concurrency_apply_writes_correct_path`, `test_run_pipeline_forwards_enrichment_parallelism_config_to_enrich_batch` | complete_candidate | Same ownership cluster as batch-size setting. |
| `bounded_parallel_enrichment.pre-enrichment-global-filters-run-first` | `src/fitcv/pipeline.py` | existing pipeline export/status test or one new focused pre-filter ordering test | likely_complete | Needs direct proof that pre-filter rejected jobs are blocked before enrichment. |
| `bounded_parallel_enrichment.conservative-defaults-batch-size-10-concurrency-1` | `src/fitcv_cp/settings_schema.py`, `src/fitcv/enrich.py` | `test_enrichment_parallelism_defaults`, `test_enrich_batch_concurrency_one_behaves_like_sequential` | complete_candidate | Defaults are explicit in schema and consumed in runtime code. |
| `bounded_parallel_enrichment.deterministic-output-order` | `src/fitcv/enrich.py` | `test_enrich_batch_preserves_input_order_under_parallel_batches` | complete_candidate | `enrich_batch` docstring and behavior are already direct. |
| `bounded_parallel_enrichment.per-job-failure-isolation` | `src/fitcv/enrich.py` | retry/fallback proof in `tests/test_enrich.py`, plus add one small direct test if current coverage is too indirect | needs_audit_during_execution | Must stay truthful; defer if only chunk-fail-fast behavior is directly provable. |
| `cv_system.analysis-evidence-selection` | `src/fitcv/evidence.py`, `src/fitcv/pipeline.py` | existing provenance and evidence-selection-summary assertions in `tests/test_pipeline.py` | complete_candidate | `retrieve_evidence_bundle` and downstream analysis record already expose selected evidence bundle details. |
| `cv_system.fit-gate-resolution` | `src/fitcv/pipeline.py` | `test_run_pipeline_uses_reranker_fit_as_sole_post_filter_cv_gate` | complete_candidate | Directly asserts gate behavior and blocked CV-analysis state. |
| `cv_system.header-placeholder-repair` | `src/fitcv/pipeline.py` | `test_run_pipeline_repairs_candidate_name_placeholder_without_llm_retry` | complete_candidate | Direct repair path already covered. |
| `cv_system.stage-artifact-diagnostics` | `src/fitcv/pipeline.py` | `test_build_stage_transition_artifacts_emits_quality_metrics`, existing debug-record output sample tests | complete_candidate | Stage artifact quality metrics and debug surfaces are directly asserted. |
| `cv_system.exact-match-late-stage-reuse` | `src/fitcv/pipeline.py` | existing reuse short-circuit tests around ranking and CV-analysis reuse | complete_candidate | Need `@proves` on the direct short-circuit assertions. |
| `cv_system.config-owned-generation-contract` | `src/fitcv/config.py` | existing config/prompt runtime tests in `tests/test_config.py` | complete_candidate | Prompt/runtime ownership already has direct config assertions. |

## Task 1: Batch A – `bounded_parallel_enrichment`

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_pipeline.py`

- [ ] Add direct `@capability` ownership for the settings/default/order surfaces.
- [ ] Add or tighten `@proves` markers for existing direct settings/order tests.
- [ ] Add one focused pipeline proof test for pre-filter-before-enrich ordering if existing coverage is too indirect.
- [ ] Complete `per-job-failure-isolation` only if a direct proof surface is truthful after audit; otherwise record it as deferred for this phase.
- [ ] Regenerate lineage and check `bounded_parallel_enrichment` gap count.

## Task 2: Batch B – `cv_system`

**Files:**
- Modify: `src/fitcv/evidence.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_config.py`

- [ ] Add direct `@capability` ownership to the evidence-selection, fit-gate, reuse, placeholder-repair, diagnostics, and config-contract surfaces.
- [ ] Add `@proves` markers to the direct existing CV pipeline/config tests.
- [ ] Add only the smallest new test if one capability still lacks direct proof after audit.
- [ ] Regenerate lineage and confirm the `cv_system` remaining gaps close truthfully.

## Task 3: Enforcement, Regeneration, And Closeout

**Files:**
- Modify: `repo_config/adoption-mode.yaml`
- Regenerate: `docs/features/bounded_parallel_enrichment/lineage.generated.yaml`
- Regenerate: `docs/features/cv_system/lineage.generated.yaml`
- Regenerate: `docs/generated/capability_lineage.yaml`

- [ ] Extend adoption enforcement only for capabilities that finish with direct code and tests evidence.
- [ ] Run `python scripts/sync_architecture_docs.py`.
- [ ] Run `python scripts/sync_architecture_docs.py --check`.
- [ ] Run `python scripts/validate_adoption_shape.py`.
- [ ] Run focused pytest for the touched proof surfaces.
- [ ] Run `git diff --check`.
- [ ] Mark the plan completed with the before/after gap counts and any truthful deferments.

## Execution Notes

Status: `completed`

Starting repo-wide remaining gap count:

- `bounded_parallel_enrichment`: `6`
- `cv_system`: `6`
- repo-wide total: `12`

Completed outcome:

- `bounded_parallel_enrichment` moved from `6` incomplete capabilities to `0`
- `cv_system` moved from `6` incomplete capabilities to `0`
- repo-wide incomplete capability count moved from `12` to `0`

Verification:

- `python scripts/sync_architecture_docs.py`
- `python scripts/sync_architecture_docs.py --check`
- `python scripts/validate_adoption_shape.py`
- `.venv\Scripts\python.exe -m pytest tests/test_enrich.py tests/test_fitcv_cp/test_settings_schema.py tests/test_pipeline.py tests/test_config.py -q`
- `git diff --check` passed with line-ending warnings only
