---
layer: change
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/multi_file_job_input/feature.source.yaml
  - docs/features/multi_file_job_input/multi_file_job_input.yaml
  - docs/features/multi_file_job_input/lineage.generated.yaml
  - docs/features/ui_consistency_theming/feature.source.yaml
  - docs/features/ui_consistency_theming/ui_consistency_theming.yaml
  - docs/features/ui_consistency_theming/lineage.generated.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/templates/base.html
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_bq_store.py
  - tests/test_fitcv_cp/test_models.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
related_features:
  - multi_file_job_input
  - ui_consistency_theming
related_stages: []
---

# Phase 12 UI And Input Evidence Completion Spec

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Complete the next bounded Mode B evidence pass by backfilling direct
code and test evidence for `multi_file_job_input` and
`ui_consistency_theming`.  
Reasoning: After Phase 11, the smallest remaining cluster is the admin upload
and theming surface. These two features are localized to the same app/template
and snapshot-persistence flows, making them a good next batch before broader
`cv_system` or `bounded_parallel_enrichment` work.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- Generated feature contracts and lineage remain generator-owned outputs.
- File metadata must stay selective and only attach capabilities to files that
  materially implement them.
- `@proves` markers must only appear on tests that directly assert the named
  upload, snapshot, or theming behavior.
- Adoption enforcement must only expand for capabilities with both direct code
  and direct test evidence.
- This phase must not treat every HTML assertion as proof of every UI
  consistency capability.

Dependencies:

- `docs/superpowers/archive/specs/2026-04-22-15-20-phase-11-control-plane-evidence-completion-spec.md`
- `docs/superpowers/plans/2026-04-22-15-37-phase-11-control-plane-evidence-completion-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- current metadata and `@proves` parsing behavior

Affected stages:

- none

Affected features:

- `multi_file_job_input`
- `ui_consistency_theming`

Primary lens: `feature`

Affected docs:

- feature_source:
  - `docs/features/multi_file_job_input/feature.source.yaml`
  - `docs/features/ui_consistency_theming/feature.source.yaml`
- feature_yaml:
  - `docs/features/multi_file_job_input/multi_file_job_input.yaml`
  - `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`
- feature_lineage:
  - `docs/features/multi_file_job_input/lineage.generated.yaml`
  - `docs/features/ui_consistency_theming/lineage.generated.yaml`
- feature_history:
  - `docs/features/multi_file_job_input/history.md`
  - `docs/features/ui_consistency_theming/history.md`
- stage_source: `none`
- stage_contract: `none`
- feature_docs: `none unless audit finds stale feature-specific explanation`
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

Generated refresh required: `yes`  
Capability IDs:

- `multi_file_job_input.*`
- `ui_consistency_theming.*`

Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Current Gap Snapshot

As of the post-Phase-11 checkpoint:

| Feature | Missing code | Missing tests |
| --- | ---: | ---: |
| `multi_file_job_input` | 5 | 5 |
| `ui_consistency_theming` | 8 | 8 |
| Combined Phase 12 target | 13 | 13 |
| Repo-wide total | 70 | 70 |

Every capability in both features is currently doc-backed but still lacks direct
code and test evidence.

### `multi_file_job_input` Residual Capabilities

- `multi_file_job_input.multiple-file-inputs-in-trigger-form`
- `multi_file_job_input.per-file-server-side-validation`
- `multi_file_job_input.canonical-merge-preserving-order`
- `multi_file_job_input.one-immutable-snapshot-stored-per-run`
- `multi_file_job_input.all-or-nothing-rejection-on-validation-failure`

Likely implementation surfaces:

- upload-trigger parsing and canonical merge behavior in `src/fitcv_cp/app.py`
- run-scoped jobs snapshot persistence in `src/fitcv_cp/bq_store.py`
- run model input snapshot fields in `src/fitcv_cp/models.py`

Likely proof surfaces:

- multi-file upload and path/paste snapshot tests in `tests/test_fitcv_cp/test_app.py`
- jobs input persistence tests in `tests/test_fitcv_cp/test_bq_store.py`
- run input snapshot field tests in `tests/test_fitcv_cp/test_models.py`

### `ui_consistency_theming` Residual Capabilities

- `ui_consistency_theming.css-custom-properties-design-tokens`
- `ui_consistency_theming.shared-component-classes`
- `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence`
- `ui_consistency_theming.flash-free-theme-application`
- `ui_consistency_theming.consistent-action-hierarchy-primary-secondary-section`
- `ui_consistency_theming.human-readable-section-headings`
- `ui_consistency_theming.attached-tab-inspection-card-pattern`
- `ui_consistency_theming.responsive-wrapping`

Likely implementation surfaces:

- global design tokens, theme bootstrap, and component CSS in
  `src/fitcv_cp/templates/base.html`
- rendered page composition and section/title wiring in `src/fitcv_cp/app.py`

Likely proof surfaces:

- page rendering tests in `tests/test_fitcv_cp/test_app.py` for section
  headings, task-first cards, tab shells, and responsive runs-list affordances

## Goal

Create a Phase 12 implementation plan that:

1. maps each UI/input capability to concrete owner files and direct proof tests
2. defers any capability whose code or proof surface is still too indirect
3. adds sparse metadata to the real upload, snapshot, and theming owner files
4. adds truthful `@proves` markers to direct upload and UI rendering tests
5. extends pilot enforcement only for completed Phase 12 capabilities
6. regenerates feature contracts, lineage, and generated discovery
7. records before/after gap counts for both features and repo-wide totals

## Non-Goals

This phase does not:

- eliminate all remaining repo-wide evidence gaps
- redesign the admin UI
- rewrite the theme system or upload flow
- expand into `cv_system`, `bounded_parallel_enrichment`, or
  `inspection_debugging`
- infer theming proof from screenshots or broad HTML smoke tests
- force completion for capabilities that only have vague visual evidence

## Proposed Shape

### 1. UI/Input Mapping Audit

The implementation plan should begin with a mapping table containing:

- capability ID
- candidate owning file(s)
- candidate proving test(s)
- confidence: `complete_candidate` or `defer`
- rationale

This audit should explicitly distinguish:

- upload flow and snapshot persistence capabilities
- structural UI/theming capabilities
- inspection-tab layout patterns that may already overlap with other feature
  surfaces

### 2. Sparse Upload And Theme Metadata Backfill

Add metadata only where the behavior is materially implemented:

- upload parsing, validation, and merge behavior in `src/fitcv_cp/app.py`
- persisted jobs snapshot fields in `src/fitcv_cp/bq_store.py`
- shared run input contract fields in `src/fitcv_cp/models.py`
- theme bootstrap, design tokens, and component classes in
  `src/fitcv_cp/templates/base.html`

### 3. Truthful Upload And UI Proof Markers

Use `@proves <capability_id>` only where tests directly assert:

- multiple uploaded files are accepted and merged
- file order is preserved
- invalid uploads reject the whole request
- per-run canonical snapshots are stored
- theme initialization and page structure render through shared components
- action hierarchy, section headings, attached-tab patterns, or responsive
  wrapping appear in explicit HTML assertions

### 4. Enforcement Extension

Extend `repo_config/adoption-mode.yaml` only for Phase 12 capabilities that
reach both direct code and direct test evidence.

### 5. Regeneration And Measurement

Run:

- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`

Measure:

- updated `multi_file_job_input` gap counts
- updated `ui_consistency_theming` gap counts
- updated repo-wide totals
- which Phase 12 capabilities reached `completeness_status: complete`
- which capabilities, if any, were intentionally deferred

## Acceptance Criteria

Phase 12 is ready for implementation when:

1. an implementation plan exists with exact capability-to-file and
   capability-to-test mappings
2. weak or indirect mappings are explicitly deferred
3. selected capabilities have direct code evidence
4. selected capabilities have direct test evidence
5. pilot enforcement covers only completed mappings
6. generated feature contracts and lineage are refreshed
7. generated discovery outputs are refreshed
8. focused upload/UI tests for touched files pass
9. `scripts/sync_architecture_docs.py --check` passes
10. `scripts/validate_adoption_shape.py` passes
11. `git diff --check` has no whitespace errors
12. post-phase gap counts are recorded in both the plan and the completed spec

## Risks And Guardrails

- Risk: `ui_consistency_theming` gets over-tagged on `app.py` just because it
  renders templates. Guardrail: prefer `base.html` for global theme/token
  behavior and use `app.py` only for the specific rendered structural patterns
  it assembles.
- Risk: upload-mode tests get reused to prove snapshot persistence they do not
  explicitly assert. Guardrail: separate request-validation tests from
  persistence-field tests.
- Risk: attached-tab pattern overlaps with `inspection_debugging`. Guardrail:
  only prove the shared UI pattern if the test asserts the structural card/tab
  layout rather than a debugging-specific data payload.
- Risk: visual consistency capabilities become subjective. Guardrail: rely only
  on direct HTML assertions and deterministic template/bootstrap code.

## Validation Plan

Minimum validation:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_models.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Rollback Plan

If Phase 12 over-attributes upload or theming evidence:

1. remove the Phase 12 metadata and `@proves` markers
2. remove the Phase 12 adoption-mode entries
3. restore any touched semantic source if the audit changed it
4. rerun `scripts/sync_architecture_docs.py`
5. rerun validation to return to the post-Phase-11 baseline

## Execution Notes

Status: `completed`

Implemented by:
`docs/superpowers/plans/2026-04-22-16-10-phase-12-ui-input-evidence-completion-plan.md`

Outcome:

- `multi_file_job_input` residual gaps moved from `5/5` missing code/test
  evidence to `0/0`.
- `ui_consistency_theming` moved from `8/8` missing code/test evidence to
  `6/6`, with only the currently well-proven structural capabilities completed
  in this phase.
- Repo-wide missing direct evidence moved from `70/70` to `63/63`.
- Completed in this phase:
  - `ui_consistency_theming.consistent-action-hierarchy-primary-secondary-section`
  - `ui_consistency_theming.human-readable-section-headings`
- Deferred in this phase:
  - `ui_consistency_theming.css-custom-properties-design-tokens`
  - `ui_consistency_theming.shared-component-classes`
  - `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence`
  - `ui_consistency_theming.flash-free-theme-application`
  - `ui_consistency_theming.attached-tab-inspection-card-pattern`
  - `ui_consistency_theming.responsive-wrapping`

Verification:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_models.py tests/test_validate_adoption_shape.py`
  passed with `279 passed`.
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
  passed.
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py` passed.
- `git diff --check` passed with line-ending warnings only.
