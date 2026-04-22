---
layer: operating_system
artifact_type: spec
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
  - src/fitcv/embeddings.py
  - src/fitcv/enrich.py
  - src/fitcv/pipeline.py
  - src/fitcv/ranking.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/worker_job.py
  - tests/test_config.py
  - tests/test_embeddings.py
  - tests/test_enrich.py
  - tests/test_ranking.py
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

# Phase 8 Settings And Performance Evidence Backfill Spec

## Triage

Layer: `operating_system`  
Feature type: `CHANGE`  
Summary: Extend the Phase 7 direct-evidence pilot to the two highest remaining
lineage-gap features, `settings_system` and `pipeline_performance`, using sparse
truthful code ownership and `@proves` evidence instead of broad metadata spray.  
Reasoning: Phase 7 proved the evidence-backfill workflow and reduced repo-wide
gaps from `missing_code_evidence=232` / `missing_test_evidence=230` to
`missing_code_evidence=218` / `missing_test_evidence=218`. The largest remaining
feature gaps now cluster in `settings_system` and `pipeline_performance`, so the
next phase should batch those areas before considering broader enforcement.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- `<feature_id>.yaml` and `lineage.generated.yaml` remain generated outputs.
- Direct code evidence must come from explicit file metadata.
- Direct test evidence must come from truthful `@proves <capability_id>` markers.
- Capability mappings must stay sparse and materially true.
- Partial lineage is acceptable when no trustworthy direct evidence exists yet.
- We must not tag files just to reduce gap counts.

Dependencies:

- Phase 7 spec: `docs/superpowers/archive/specs/2026-04-22-12-02-phase-7-direct-evidence-backfill-spec.md`
- Phase 7 plan: `docs/superpowers/plans/2026-04-22-12-09-phase-7-direct-evidence-backfill-plan.md`
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

Primary lens: `targeted evidence backfill`

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
Capability IDs: `selected settings_system and pipeline_performance pilot capabilities`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Problem

The evidence-oriented lineage schema is now working, but many capabilities still
show `missing_code_evidence` and `missing_test_evidence`. After Phase 7, the
largest remaining gap distribution is:

| Feature | Missing code | Missing tests |
|---|---:|---:|
| `settings_system` | 40 | 40 |
| `pipeline_performance` | 38 | 38 |
| `trigger_run_management` | 30 | 30 |
| `inspection_debugging` | 28 | 28 |
| `run_lifecycle_controls` | 18 | 18 |
| `ui_consistency_theming` | 16 | 16 |
| `admin_control_plane_core` | 14 | 14 |
| `bounded_parallel_enrichment` | 12 | 12 |
| `cv_system` | 12 | 12 |
| `multi_file_job_input` | 10 | 10 |

`settings_system` and `pipeline_performance` are the most valuable next batch
because they own many central configuration, tuning, reuse, and optimization
behaviors that cross several runtime paths. Leaving them mostly spec-backed
makes lineage less useful for future refactors.

## Goal

Backfill direct evidence for a curated subset of `settings_system` and
`pipeline_performance` capabilities by:

1. selecting a small, high-confidence capability set for each feature
2. adding `capabilities:` metadata to the implementation files that materially
   own those behaviors
3. adding `@proves` markers only to tests that directly verify those behaviors
4. extending pilot enforcement in `repo_config/adoption-mode.yaml` for the
   selected capabilities
5. regenerating contracts, lineage, and generated discovery outputs
6. measuring the post-phase reduction in `missing_code_evidence` and
   `missing_test_evidence`

## Non-Goals

This phase does not:

- eliminate every remaining gap in `settings_system` or `pipeline_performance`
- tag all settings or performance-adjacent files
- infer capability ownership from filenames
- change the evidence-oriented lineage schema
- reopen Phase 5 source/contract shape decisions
- migrate `history.md` to a partial-generated starter pattern
- broaden pilot enforcement to all managed features

## Candidate Capability Set

The implementation plan should confirm or narrow this set before editing code.
If any mapping is weak during execution, leave that capability out rather than
forcing evidence.

### Settings System

Preferred Phase 8 settings capabilities:

- `settings_system.settings-schema-registry`
- `settings_system.bigquery-backed-pipeline-settings-store`
- `settings_system.retrieval-settings`
- `settings_system.ranking-settings`
- `settings_system.cv-analysis-alignment-settings`
- `settings_system.cv-generation-settings`
- `settings_system.trigger-time-effective-settings-snapshot`
- `settings_system.baseline-default-hydration`
- `settings_system.settings-used-exports`

Likely implementation surfaces:

- `src/fitcv/config.py`
- `src/fitcv_cp/settings_schema.py`
- `src/fitcv_cp/settings_store.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/worker_job.py`

Likely proof surfaces:

- `tests/test_config.py`
- `tests/test_fitcv_cp/test_settings_schema.py`
- `tests/test_fitcv_cp/test_settings_store.py`
- `tests/test_fitcv_cp/test_bq_store.py`
- `tests/test_fitcv_cp/test_worker_job.py`

### Pipeline Performance

Preferred Phase 8 performance capabilities:

- `pipeline_performance.gemini-structured-output-with-response-schema-and-pydantic`
- `pipeline_performance.fallback-path-for-unparseable-responses`
- `pipeline_performance.fingerprint-based-enrich-result-reuse-happens-before-llm-enrichment-using-normalized-raw-job-inputs`
- `pipeline_performance.enrich-contract-fingerprinting-invalidates-reuse-automatically-when-prompt-model-schema-behavior-changes`
- `pipeline_performance.shared-structured-jobs-reuse-lookup-avoids-redundant-enrich-calls-while-only-fresh-rows-are-upserted-back-into-the-shared-table`
- `pipeline_performance.shortlist-now-builds-a-stable-structured-embedding-input-signature-before-generating-job-summary-vectors`
- `pipeline_performance.shortlist-reuses-the-latest-stored-embedding-row-for-a-job-url-only-when-both-the-structured-signature-and-embedding-contract-fingerprint-still-match`
- `pipeline_performance.fresh-shortlist-embeddings-persist-signature-metadata-so-later-runs-can-skip-repeated-embedding-work-safely`
- `pipeline_performance.cv-analysis-now-uses-bounded-semantic-lift-for-required-skill-and-role-channels-instead-of-reserving-semantic-work-only-for-domain-and-responsibility-alignment`
- `pipeline_performance.ranked-jobs-with-authoritative-reranker-fit-label-skip-now-stop-before-evidence-retrieval-gap-computation-and-semantic-alignment-inside-cv-analysis`

Likely implementation surfaces:

- `src/fitcv/enrich.py`
- `src/fitcv/embeddings.py`
- `src/fitcv/ranking.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`

Likely proof surfaces:

- `tests/test_enrich.py`
- `tests/test_embeddings.py`
- `tests/test_ranking.py`
- `tests/test_fitcv_cp/test_worker_job.py`

## Proposed Shape

### 1. Curated Mapping Review

Before editing, the implementation plan should inspect the candidate source and
test files and produce exact capability-to-file mappings. The plan must mark any
candidate as deferred when the implementation or proof surface is ambiguous.

### 2. Sparse Code Metadata

Each touched implementation file should have a valid top-of-file `@meta` block
or updated existing metadata. Add only the selected capabilities that the file
materially implements.

Expected examples:

- `settings_schema.py` can own settings schema and form/control capability IDs.
- `settings_store.py` and `bq_store.py` can own BigQuery-backed settings store
  behavior when their code directly persists or retrieves those settings.
- `config.py` can own baseline hydration and central runtime defaults when the
  code directly resolves those values.
- `enrich.py` can own structured-output, fallback parsing, and enrich reuse
  capabilities when those code paths are present.
- `embeddings.py` can own shortlist embedding signature/reuse capabilities.
- `ranking.py` and `pipeline.py` should only receive performance capabilities
  if they directly implement skip/short-circuit or scoring optimization logic.

### 3. Truthful Proof Markers

Add `@proves` only to tests with direct behavioral assertions. Prefer one or two
representative proof tests per capability over tagging every related test.

The plan should avoid:

- tagging fixture-only tests
- tagging snapshot-adjacent tests that only cover rendering without the named
  behavior
- tagging tests that only exercise helper setup for a capability
- claiming proof for settings capabilities where the test only verifies generic
  schema parsing

### 4. Pilot Enforcement Extension

Extend `repo_config/adoption-mode.yaml` under the existing direct-evidence pilot
section for the selected Phase 8 capabilities. Require both code and test
evidence only for capabilities that receive trustworthy implementation and proof
links during this phase.

Do not require code/test evidence for deferred capabilities.

### 5. Regeneration And Measurement

Run the architecture sync and validate:

- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`

Measure:

- updated `missing_code_evidence` count
- updated `missing_test_evidence` count
- selected capabilities that reached `completeness_status: complete`
- selected capabilities intentionally left `partial`

## Acceptance Criteria

Phase 8 is complete when:

1. a Phase 8 implementation plan exists and lists exact selected capability
   mappings
2. selected `settings_system` capabilities have truthful code and proof evidence
3. selected `pipeline_performance` capabilities have truthful code and proof
   evidence
4. pilot enforcement covers only the selected completed mappings
5. generated feature contracts and lineage are refreshed
6. generated discovery files are refreshed
7. `scripts/sync_architecture_docs.py --check` passes
8. `scripts/validate_adoption_shape.py` passes
9. focused tests for touched code and validation pass
10. post-phase gap counts are recorded in the implementation plan and spec

## Risks And Guardrails

- Risk: settings files are broad and could attract too many capabilities.
  Guardrail: tag only capabilities directly implemented by each file.
- Risk: performance capabilities have long legacy IDs that are harder to map.
  Guardrail: keep the candidate set narrow and defer weak mappings.
- Risk: `worker_job.py` participates in both settings and performance flows.
  Guardrail: only tag direct trigger-time snapshot or skip/reuse behavior if the
  file contains the decision or handoff logic.
- Risk: test files may prove helpers rather than feature behavior.
  Guardrail: require direct assertions for `@proves`.
- Risk: regenerated lineage may reveal more gaps than this phase closes.
  Guardrail: record the counts honestly; Phase 8 is not a zero-gap phase.

## Validation Plan

Minimum validation:

- `.\.venv\Scripts\python.exe -m pytest tests/test_config.py tests/test_enrich.py tests/test_embeddings.py tests/test_ranking.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_worker_job.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Rollback Plan

If Phase 8 over-attributes evidence or validation becomes too strict:

1. remove the new Phase 8 capability metadata from touched source files
2. remove the new Phase 8 `@proves` markers from touched tests
3. remove the Phase 8 pilot enforcement entries from `repo_config/adoption-mode.yaml`
4. rerun `scripts/sync_architecture_docs.py`
5. rerun validation to return to the Phase 7 baseline

## Execution Notes

Status: `completed`

Implementation plan:

- `docs/superpowers/plans/2026-04-22-12-48-phase-8-settings-performance-evidence-backfill-plan.md`

Completed scope:

- added sparse code ownership metadata for selected `settings_system`
  capabilities in `src/fitcv/config.py`,
  `src/fitcv_cp/settings_schema.py`, `src/fitcv_cp/settings_store.py`,
  `src/fitcv_cp/bq_store.py`, and `src/fitcv_cp/worker_job.py`
- added sparse code ownership metadata for selected `pipeline_performance`
  capabilities in `src/fitcv/enrich.py`, `src/fitcv/embeddings.py`, and
  `src/fitcv_cp/worker_job.py`
- added truthful `@proves` markers to representative tests under
  `tests/test_config.py`, `tests/test_enrich.py`, `tests/test_embeddings.py`,
  and selected `tests/test_fitcv_cp/*` files
- extended the direct-evidence pilot enforcement in
  `repo_config/adoption-mode.yaml`
- refreshed generated feature contracts, lineage files, and discovery outputs

Measured result:

- `settings_system` dropped from `missing_code_evidence=40` /
  `missing_test_evidence=40` to `22` / `22`
- `pipeline_performance` dropped from `missing_code_evidence=38` /
  `missing_test_evidence=38` to `20` / `20`
- repo-wide totals dropped from `218` / `218` to `182` / `182`

Deferred:

- `pipeline_performance.cv-analysis-now-uses-bounded-semantic-lift-for-required-skill-and-role-channels-instead-of-reserving-semantic-work-only-for-domain-and-responsibility-alignment`
- `pipeline_performance.ranked-jobs-with-authoritative-reranker-fit-label-skip-now-stop-before-evidence-retrieval-gap-computation-and-semantic-alignment-inside-cv-analysis`

These stay partial until a focused `cv_analysis` / reranker skip evidence pass.
