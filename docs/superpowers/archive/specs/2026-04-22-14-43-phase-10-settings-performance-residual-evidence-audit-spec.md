---
layer: operating_system
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/features/pipeline_performance/feature.source.yaml
  - docs/features/pipeline_performance/pipeline_performance.yaml
  - docs/features/pipeline_performance/lineage.generated.yaml
  - src/fitcv/settings.py
  - src/fitcv/config.py
  - src/fitcv/enrich.py
  - src/fitcv/embeddings.py
  - src/fitcv/ranking.py
  - src/fitcv/cv_analysis.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/worker_job.py
  - tests/test_settings*.py
  - tests/test_config*.py
  - tests/test_enrich*.py
  - tests/test_embeddings*.py
  - tests/test_ranking*.py
  - tests/test_cv_analysis*.py
  - tests/test_fitcv_cp/*.py
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

# Phase 10 Settings And Performance Residual Evidence Audit Spec

## Triage

Layer: `operating_system`  
Feature type: `MODIFY`  
Summary: Audit and backfill the remaining direct code/test evidence gaps for
`settings_system` and `pipeline_performance` after Phases 8 and 9, while
deferring any capability whose proof surface is not direct enough.  
Reasoning: Phase 8 started the settings/performance evidence pilot, but current
lineage still reports `settings_system` at `22/22` and
`pipeline_performance` at `20/20`. These are now the two largest remaining
managed-feature evidence buckets. The next safe step is not blanket tagging; it
is a residual audit that maps each gap to a truthful source file and proof test,
then promotes only completed mappings into pilot enforcement.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- Generated contracts and `lineage.generated.yaml` remain generated outputs.
- Direct code evidence must come from explicit file metadata on materially
  owning files.
- Direct test evidence must come from truthful `@proves <capability_id>`
  markers in tests that directly assert the named behavior.
- Do not tag files only to reduce gap counts.
- Long capability IDs may be retained when they already describe shipped
  behavior, but the plan should flag candidates that deserve later ID
  simplification.
- Pilot enforcement in `repo_config/adoption-mode.yaml` must include only
  capabilities with both direct code and test evidence.

Dependencies:

- Phase 8 spec:
  `docs/superpowers/archive/specs/2026-04-22-12-35-phase-8-settings-performance-evidence-backfill-spec.md`
- Phase 9 spec:
  `docs/superpowers/archive/specs/2026-04-22-13-05-phase-9-trigger-inspection-evidence-completion-spec.md`
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

- `settings_system`
- `pipeline_performance`

Primary lens: `mixed`

Affected docs:

- feature_source:
  - `docs/features/settings_system/feature.source.yaml`
  - `docs/features/pipeline_performance/feature.source.yaml`
- feature_yaml:
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/pipeline_performance/pipeline_performance.yaml`
- feature_lineage:
  - `docs/features/settings_system/lineage.generated.yaml`
  - `docs/features/pipeline_performance/lineage.generated.yaml`
- feature_history:
  - `docs/features/settings_system/history.md`
  - `docs/features/pipeline_performance/history.md`
- stage_source: `none`
- stage_contract:
  - `docs/stages/*.yaml`
- feature_docs: `none unless audit discovers stale feature-specific explanation`
- cross_cutting_docs:
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
Capability IDs: `selected settings_system and pipeline_performance residual capabilities`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Current Gap Snapshot

As of the Phase 9 checkpoint:

| Feature | Missing code | Missing tests |
|---|---:|---:|
| `settings_system` | 22 | 22 |
| `pipeline_performance` | 20 | 20 |
| Repo-wide total | 128 | 128 |

The current residual capability sets are listed below. The implementation plan
must confirm each mapping before editing and may defer candidates that do not
have direct proof.

### `settings_system` Residual Capabilities

- `settings_system.run-safety-settings`
- `settings_system.global-job-filters`
- `settings_system.preference-fit-calibration`
- `settings_system.cv-composition-visibility-settings`
- `settings_system.warning-only-cv-max-pages-validation-setting`
- `settings_system.task-first-settings-ui`
- `settings_system.advanced-settings-disclosure`
- `settings_system.metadata-only-fixed-controls`
- `settings_system.compact-cv-visibility-controls`
- `settings_system.grouped-form-validation`
- `settings_system.per-run-overrides`

Likely implementation surfaces:

- settings schema and config ownership in `src/fitcv/settings.py` and
  `src/fitcv/config.py`
- admin settings rendering and form handling in `src/fitcv_cp/app.py`
- persisted settings store helpers in `src/fitcv_cp/bq_store.py`
- trigger-time / worker effective-setting use in `src/fitcv_cp/worker_job.py`

Likely proof surfaces:

- settings schema/config tests
- admin settings route/render tests in `tests/test_fitcv_cp/test_app.py`
- BQ settings persistence tests in `tests/test_fitcv_cp/test_bq_store.py`
- worker/effective-settings tests in `tests/test_fitcv_cp/test_worker_job.py`

### `pipeline_performance` Residual Capabilities

- `pipeline_performance.pre-enrichment-global-job-filters-applications-count-max-max-age-days`
- `pipeline_performance.explicit-rejection-reasons-in-rule-filter-results`
- `pipeline_performance.enrich-extraction-prompt-text-now-comes-from-a-centralized-prompt-registry-with-config-selected-prompt-ids`
- `pipeline_performance.enrich-stage-raw-plus-canonical-semantic-companions-for-repeated-downstream-fields`
- `pipeline_performance.canonical-skill-companion-lists-and-entity-payloads-for-required-preferred-skills`
- `pipeline_performance.enrich-stage-mapping-suggestion-capture-for-review-debug-surfaces`
- `pipeline_performance.operator-facing-enriched-job-exports-now-keep-canonical-semantic-fields-and-fingerprint-reuse-provenance-while-omitting-retired-raw-duplicate-classification-baggage`
- `pipeline_performance.large-runs-avoid-some-row-scaled-layer-4-event-noise-by-relying-more-on-aggregate-stage-summaries-plus-stage-owned-artifacts`
- `pipeline_performance.cv-analysis-now-uses-bounded-semantic-lift-for-required-skill-and-role-channels-instead-of-reserving-semantic-work-only-for-domain-and-responsibility-alignment`
- `pipeline_performance.ranked-jobs-with-authoritative-reranker-fit-label-skip-now-stop-before-evidence-retrieval-gap-computation-and-semantic-alignment-inside-cv-analysis`

Likely implementation surfaces:

- pre-enrichment filter and stage artifact handling in pipeline orchestration
- enrichment extraction, canonical companions, and mapping-suggestion handling in
  `src/fitcv/enrich.py`
- rule-filter rejection reason handling in rule-filter code and control-plane
  export surfaces
- shortlist/ranking/cv-analysis behavior in `src/fitcv/embeddings.py`,
  `src/fitcv/ranking.py`, and `src/fitcv/cv_analysis.py`
- operator-facing export trimming and aggregate stage summaries in
  `src/fitcv_cp/worker_job.py` and `src/fitcv_cp/app.py`

Likely proof surfaces:

- enrichment tests for prompt registry, canonical companions, and mapping
  suggestions
- rule-filter tests for explicit rejection reasons
- worker/control-plane tests for export trimming and aggregate diagnostics
- CV-analysis/ranking tests for bounded semantic lift and reranker `skip`
  short-circuit behavior

## Goal

Create a Phase 10 implementation plan that:

1. maps each residual capability to concrete code and test surfaces
2. drops or defers weak mappings before editing
3. adds sparse file-level capability metadata to owning implementation files
4. adds `@proves` markers only to tests with direct behavioral assertions
5. extends pilot enforcement only for completed mappings
6. regenerates generated feature contracts, lineage, stages, and discovery
7. records before/after gap counts and remaining deferred work

## Non-Goals

This phase does not:

- eliminate all repo-wide gaps
- rewrite the evidence-oriented lineage schema
- infer evidence from filenames or broad directory ownership
- force every residual settings/performance capability to complete
- rename long capability IDs unless a later source-contract cleanup is approved
- migrate feature histories to the starter partial-generated history pattern
- change product behavior unless a missing proof requires a small regression test

## Proposed Shape

### 1. Residual Mapping Audit

The implementation plan should inspect code and tests before editing. It should
produce a mapping table with:

- capability ID
- implementation owner file(s)
- direct proof test(s)
- confidence: `complete_candidate` or `defer`
- rationale

### 2. Sparse Metadata Backfill

Add file-level `capabilities` entries only to files that materially implement
the capability. Avoid treating broad orchestration files as owners for every
downstream performance capability.

### 3. Truthful Proof Markers

Use `@proves <capability_id>` only when the test directly asserts the named
settings control, persistence behavior, export boundary, enrichment behavior,
filter behavior, or performance optimization behavior.

### 4. Enforcement Extension

Extend `repo_config/adoption-mode.yaml` only for capabilities that reached both
direct code and direct test evidence during this phase.

### 5. Regeneration And Measurement

Run:

- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`

Measure:

- updated `settings_system` gap counts
- updated `pipeline_performance` gap counts
- updated repo-wide totals
- selected capabilities that reached `completeness_status: complete`
- selected capabilities intentionally left `partial`

## Acceptance Criteria

Phase 10 is ready for implementation when:

1. an implementation plan exists with exact mapping decisions
2. weak settings/performance mappings are explicitly deferred
3. selected mappings have direct code evidence
4. selected mappings have direct test evidence
5. pilot enforcement covers only completed mappings
6. generated feature contracts and lineage are refreshed
7. generated discovery files are refreshed
8. focused tests for touched code pass
9. `scripts/sync_architecture_docs.py --check` passes
10. `scripts/validate_adoption_shape.py` passes
11. `git diff --check` has no whitespace errors
12. post-phase gap counts are recorded in the implementation plan and spec

## Risks And Guardrails

- Risk: settings UI tests get used to prove schema/config capabilities they do
  not directly validate. Guardrail: split UI, schema, persistence, and runtime
  capabilities by the surface under test.
- Risk: pipeline-performance IDs are long and tempting to tag broadly.
  Guardrail: tag the narrow implementation file where the behavior actually
  lives, and defer if the behavior is only described in history.
- Risk: performance capabilities span multiple stages. Guardrail: use the
  smallest truthful owning surface and avoid duplicating capability ownership
  across passive adapters.
- Risk: enforcement becomes stricter than evidence. Guardrail: run adoption
  validation immediately after adding enforcement.

## Validation Plan

Minimum validation:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_settings*.py tests/test_config*.py tests/test_enrich*.py tests/test_embeddings*.py tests/test_ranking*.py tests/test_cv_analysis*.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Rollback Plan

If Phase 10 over-attributes evidence or validation becomes too strict:

1. remove Phase 10 metadata/proof markers
2. remove Phase 10 pilot enforcement entries
3. restore any touched feature sources to their prior semantic content
4. rerun `scripts/sync_architecture_docs.py`
5. rerun validation to return to the Phase 9 baseline

## Execution Notes

Status: `not_started`

To execute, turn this spec into an implementation plan first. The plan should
confirm exact mappings and explicitly list deferred capabilities before editing.
