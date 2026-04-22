---
layer: operating_system
artifact_type: plan
status: completed
parent_workstream: none
targets:
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/features/pipeline_performance/feature.source.yaml
  - docs/features/pipeline_performance/pipeline_performance.yaml
  - docs/features/pipeline_performance/lineage.generated.yaml
  - src/fitcv/config.py
  - src/fitcv/enrich.py
  - src/fitcv/evidence.py
  - src/fitcv/pipeline.py
  - src/fitcv/rule_filter.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - tests/test_config.py
  - tests/test_enrich.py
  - tests/test_evidence.py
  - tests/test_pipeline.py
  - tests/test_rule_filter.py
  - tests/test_fitcv_cp/test_app.py
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

# Phase 10 Settings And Performance Residual Evidence Audit Implementation Plan

**Feature Source:** `docs/features/settings_system/feature.source.yaml`, `docs/features/pipeline_performance/feature.source.yaml`  
**Feature Contract:** `docs/features/settings_system/settings_system.yaml`, `docs/features/pipeline_performance/pipeline_performance.yaml`  
**Spec:** `docs/superpowers/archive/specs/2026-04-22-14-43-phase-10-settings-performance-residual-evidence-audit-spec.md`  
**Type:** modify  
**Plan Layer:** operating_system  
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task. Keep capability mappings sparse and defer weak evidence.

**Goal:** Complete a bounded residual evidence pass for high-confidence `settings_system` and `pipeline_performance` capabilities.

**Architecture:** This plan adds metadata to the actual owning files and proof markers to existing tests with direct assertions. The spec mentioned `src/fitcv/settings.py`, but this repo's settings schema source is `src/fitcv_cp/settings_schema.py`; use that file as the settings registry surface.

**Key Invariants:**
- Do not hand-edit generated contracts or lineage.
- Direct code evidence comes from file metadata only where the file materially owns the capability.
- Direct test evidence comes from `@proves` markers only where assertions verify the named behavior.
- Extend adoption enforcement only for capabilities completed in this batch.

**Rollout / Revert:**  
- rollback_trigger: over-attributed metadata, weak proof markers, or adoption validation failure.  
- rollback_method: remove Phase 10 metadata/proofs/enforcement, rerun architecture sync, and return to the Phase 10 spec-only baseline.

---

## File Structure First

**Files to modify**

- `docs/superpowers/archive/specs/2026-04-22-14-43-phase-10-settings-performance-residual-evidence-audit-spec.md`
- `docs/superpowers/plans/2026-04-22-14-48-phase-10-settings-performance-residual-evidence-audit-plan.md`
- `src/fitcv/config.py`
- `src/fitcv/enrich.py`
- `src/fitcv/evidence.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/rule_filter.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/settings_schema.py`
- `tests/test_config.py`
- `tests/test_enrich.py`
- `tests/test_evidence.py`
- `tests/test_pipeline.py`
- `tests/test_rule_filter.py`
- `tests/test_fitcv_cp/test_app.py`
- `repo_config/adoption-mode.yaml`
- `docs/operating_system/feature-lifecycle.md`

**Generated outputs to refresh**

- `docs/features/settings_system/settings_system.yaml`
- `docs/features/settings_system/lineage.generated.yaml`
- `docs/features/pipeline_performance/pipeline_performance.yaml`
- `docs/features/pipeline_performance/lineage.generated.yaml`
- `docs/generated/*`
- `docs/stages/*.yaml`

## Selected Mapping Audit

### Settings System

Complete in this phase:

| Capability | Code owner(s) | Proof test(s) |
| --- | --- | --- |
| `settings_system.run-safety-settings` | `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/app.py` | `test_settings_page_renders_run_lifecycle_section` |
| `settings_system.global-job-filters` | `src/fitcv_cp/settings_schema.py`, `src/fitcv/rule_filter.py` | `test_admin_setting_reaches_filter_via_apply_settings_to_config` |
| `settings_system.preference-fit-calibration` | `src/fitcv_cp/settings_schema.py` | `test_grouped_save_fit_label_thresholds_valid` |
| `settings_system.cv-composition-visibility-settings` | `src/fitcv/config.py`, `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/app.py` | `test_settings_page_renders_cv_visibility_matrix`, `test_validate_composition_accepts_valid_europass` |
| `settings_system.warning-only-cv-max-pages-validation-setting` | `src/fitcv/config.py`, `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/app.py` | `test_load_config_nested_cv_validation_max_pages_positive`, `test_settings_page_cv_max_pages_is_numeric_input` |
| `settings_system.task-first-settings-ui` | `src/fitcv_cp/app.py` | `test_settings_page_renders_task_first_sections` |
| `settings_system.advanced-settings-disclosure` | `src/fitcv_cp/app.py` | `test_settings_page_uses_advanced_disclosure_for_expert_controls` |
| `settings_system.metadata-only-fixed-controls` | `src/fitcv_cp/app.py` | `test_settings_page_renders_single_option_controls_as_metadata` |
| `settings_system.compact-cv-visibility-controls` | `src/fitcv_cp/app.py` | `test_settings_page_renders_cv_sub_cards`, `test_settings_page_uses_shared_cv_setting_row_class_across_blocks` |
| `settings_system.grouped-form-validation` | `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/app.py` | `test_grouped_save_fit_label_thresholds_invalid_order`, `test_grouped_save_cv_composition_invalid_does_not_partial_save` |
| `settings_system.per-run-overrides` | `src/fitcv_cp/app.py` | `test_post_runs_with_config_overrides`, `test_post_runs_rejects_invalid_config_overrides` |

### Pipeline Performance

Complete in this phase:

| Capability | Code owner(s) | Proof test(s) |
| --- | --- | --- |
| `pipeline_performance.pre-enrichment-global-job-filters-applications-count-max-max-age-days` | `src/fitcv/rule_filter.py`, `src/fitcv/pipeline.py` | `test_pre_filter_rejects_stale_job`, `test_pre_filter_rejects_high_count_job_using_applications_count_int` |
| `pipeline_performance.explicit-rejection-reasons-in-rule-filter-results` | `src/fitcv/rule_filter.py` | `test_rejected_jobs_include_reasons`, `test_multiple_rejection_reasons_accumulated` |
| `pipeline_performance.enrich-extraction-prompt-text-now-comes-from-a-centralized-prompt-registry-with-config-selected-prompt-ids` | `src/fitcv/config.py`, `src/fitcv/enrich.py` | `test_enrich_job_renders_prompt_via_prompt_registry`, `test_config_accessors_resolve_centralized_prompt_ids_and_model_defaults` |
| `pipeline_performance.enrich-stage-raw-plus-canonical-semantic-companions-for-repeated-downstream-fields` | `src/fitcv/enrich.py` | `test_merge_scraped_and_enriched_preserves_raw_and_canonical_enrich_fields`, `test_apply_structured_normalization_preserves_raw_scalar_companions` |
| `pipeline_performance.canonical-skill-companion-lists-and-entity-payloads-for-required-preferred-skills` | `src/fitcv/enrich.py` | `test_apply_structured_normalization_emits_canonical_skill_companions` |
| `pipeline_performance.enrich-stage-mapping-suggestion-capture-for-review-debug-surfaces` | `src/fitcv/enrich.py`, `src/fitcv_cp/app.py` | `test_apply_structured_normalization_emits_canonical_skill_companions`, `test_download_mapping_suggestions_json_endpoint_200` |
| `pipeline_performance.operator-facing-enriched-job-exports-now-keep-canonical-semantic-fields-and-fingerprint-reuse-provenance-while-omitting-retired-raw-duplicate-classification-baggage` | `src/fitcv/pipeline.py`, `src/fitcv_cp/bq_store.py` | `test_list_run_structured_jobs_preserves_reuse_provenance_fields` |
| `pipeline_performance.large-runs-avoid-some-row-scaled-layer-4-event-noise-by-relying-more-on-aggregate-stage-summaries-plus-stage-owned-artifacts` | `src/fitcv/pipeline.py`, `src/fitcv_cp/worker_job.py` | `test_worker_persists_stage_transition_artifacts_json_on_success` |
| `pipeline_performance.cv-analysis-now-uses-bounded-semantic-lift-for-required-skill-and-role-channels-instead-of-reserving-semantic-work-only-for-domain-and-responsibility-alignment` | `src/fitcv/evidence.py`, `src/fitcv/pipeline.py` | `test_retrieve_evidence_bundle_uses_semantic_alignment_for_required_skill_support`, `test_retrieve_evidence_bundle_uses_semantic_alignment_for_role_alignment` |
| `pipeline_performance.ranked-jobs-with-authoritative-reranker-fit-label-skip-now-stop-before-evidence-retrieval-gap-computation-and-semantic-alignment-inside-cv-analysis` | `src/fitcv/pipeline.py` | `test_run_pipeline_short_circuits_reranker_skip_before_cv_analysis_dependencies` |

Deferred:

- none selected for deferral in this implementation plan; if validation reveals a weak mapping, remove it before enforcement.

## Tasks

### Task 1: Settings Code Evidence

- [x] Extend `src/fitcv_cp/settings_schema.py` capability metadata for residual settings schema, validation, grouping, and runtime config controls.
- [x] Extend `src/fitcv_cp/app.py` capability metadata for settings UI layout, draft/current rendering, grouped forms, per-run overrides, and run-safety controls.
- [x] Extend `src/fitcv/config.py` metadata for CV composition and max-pages config ownership.
- [x] Extend `src/fitcv/rule_filter.py` metadata for global job filter settings participation.

### Task 2: Performance Code Evidence

- [x] Extend `src/fitcv/rule_filter.py` metadata for pre-enrichment global filters and explicit rejection reasons.
- [x] Extend `src/fitcv/enrich.py` metadata for prompt registry use, raw/canonical companions, canonical skill companions, and mapping suggestions.
- [x] Add/extend `src/fitcv/evidence.py` metadata for bounded semantic lift in required-skill and role channels.
- [x] Add/extend `src/fitcv/pipeline.py` metadata for pre-filter orchestration, export trimming, aggregate stage summaries, semantic-lift integration, and reranker skip short-circuiting.
- [x] Extend `src/fitcv_cp/worker_job.py` or existing metadata only if needed for aggregate stage snapshot evidence.

### Task 3: Test Proof Evidence

- [x] Add settings `@proves` markers to representative admin app tests.
- [x] Add settings `@proves` markers to representative config/rule-filter tests.
- [x] Add performance `@proves` markers to representative enrich, rule-filter, evidence, pipeline, BQ, and worker tests.
- [x] Avoid adding proof markers to broad smoke tests or fixture-only tests.

### Task 4: Enforcement And Governance

- [x] Add completed Phase 10 capabilities to `repo_config/adoption-mode.yaml`.
- [x] Update `docs/operating_system/feature-lifecycle.md` to mention Phase 10 residual settings/performance extension.

### Task 5: Regenerate And Measure

- [x] Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`.
- [x] Measure `settings_system`, `pipeline_performance`, and repo-wide gap counts.
- [x] Confirm selected capabilities now have code and test evidence in lineage.

### Task 6: Verify And Close

- [x] Run focused pytest:
  - `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_config.py tests/test_enrich.py tests/test_evidence.py tests/test_pipeline.py tests/test_rule_filter.py tests/test_validate_adoption_shape.py`
- [x] Run `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`.
- [x] Run `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`.
- [x] Run `git diff --check`.
- [x] Mark the Phase 10 spec and plan completed with execution notes.

## Execution Notes

Status: `completed`

Outcome:

- Completed all selected Phase 10 residual evidence mappings for
  `settings_system` and `pipeline_performance`.
- `settings_system` moved from `22/22` missing code/test evidence to `0/0`.
- `pipeline_performance` moved from `20/20` missing code/test evidence to
  `0/0`.
- Repo-wide missing direct evidence moved from `128/128` to `86/86`.
- No selected Phase 10 capability was deferred.
- Stabilized freshness tests by replacing stale hard-coded "recent" dates with
  a UTC-relative helper.

Verification:

- Focused pytest passed: `568 passed, 1 skipped`.
- `scripts/sync_architecture_docs.py --check` passed.
- `scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with line-ending warnings only.
