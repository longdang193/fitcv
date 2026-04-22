---
layer: change
artifact_type: spec
status: completed
parent_workstream: none
targets:
  - docs/features/ui_consistency_theming/feature.source.yaml
  - docs/features/ui_consistency_theming/ui_consistency_theming.yaml
  - docs/features/ui_consistency_theming/lineage.generated.yaml
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/base.html
  - scripts/sync_architecture_docs.py
  - tests/test_fitcv_cp/test_app.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
  - docs/superpowers/plans/2026-04-22-17-05-phase-13-ui-theming-completion-plan.md
related_features:
  - ui_consistency_theming
related_stages: []
---

# Phase 13 UI Theming Completion Spec

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Complete the remaining deferred `ui_consistency_theming` capability
evidence by auditing the shared base template and adding only the smallest
explicit proof tests needed.  
Reasoning: After Phase 12, `ui_consistency_theming` is the warmest and
smallest remaining cluster. The remaining gaps are all concentrated around
`src/fitcv_cp/templates/base.html` plus a handful of explicit structural
rendering tests in `tests/test_fitcv_cp/test_app.py`, so this is a good
opportunity to finish the feature cleanly before moving to broader domains like
`cv_system`.  
Invariants:

- The private repo remains the development source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- Generated feature contracts and lineage remain generator-owned outputs.
- File metadata must stay selective and only attach capabilities to files that
  materially implement them.
- `@proves` markers must only appear on tests that directly assert the named
  theme/bootstrap/layout behavior.
- Adoption enforcement must only expand for capabilities with both direct code
  and direct test evidence.
- If a global theming capability still lacks a direct proof test after audit, it
  should remain deferred rather than being forced complete.

Dependencies:

- `docs/superpowers/archive/specs/2026-04-22-16-02-phase-12-ui-input-evidence-completion-spec.md`
- `docs/superpowers/plans/2026-04-22-16-10-phase-12-ui-input-evidence-completion-plan.md`
- `scripts/sync_architecture_docs.py`
- `scripts/validate_adoption_shape.py`
- current metadata and `@proves` parsing behavior

Affected stages:

- none

Affected features:

- `ui_consistency_theming`

Primary lens: `feature`

Affected docs:

- feature_source:
  - `docs/features/ui_consistency_theming/feature.source.yaml`
- feature_yaml:
  - `docs/features/ui_consistency_theming/ui_consistency_theming.yaml`
- feature_lineage:
  - `docs/features/ui_consistency_theming/lineage.generated.yaml`
- feature_history:
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

- `ui_consistency_theming.css-custom-properties-design-tokens`
- `ui_consistency_theming.shared-component-classes`
- `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence`
- `ui_consistency_theming.flash-free-theme-application`
- `ui_consistency_theming.attached-tab-inspection-card-pattern`
- `ui_consistency_theming.responsive-wrapping`

Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Current Gap Snapshot

As of the post-Phase-12 checkpoint:

| Feature | Missing code | Missing tests |
| --- | ---: | ---: |
| `ui_consistency_theming` | 6 | 6 |
| Repo-wide total | 63 | 63 |

Two `ui_consistency_theming` capabilities are already complete:

- `ui_consistency_theming.consistent-action-hierarchy-primary-secondary-section`
- `ui_consistency_theming.human-readable-section-headings`

Residual capabilities for this phase:

- `ui_consistency_theming.css-custom-properties-design-tokens`
- `ui_consistency_theming.shared-component-classes`
- `ui_consistency_theming.dark-light-theme-toggle-with-localstorage-persistence`
- `ui_consistency_theming.flash-free-theme-application`
- `ui_consistency_theming.attached-tab-inspection-card-pattern`
- `ui_consistency_theming.responsive-wrapping`

Likely implementation surfaces:

- global theme bootstrap, design tokens, shared component classes, attached tab
  styles, and wrapping rules in `src/fitcv_cp/templates/base.html`
- rendered page structures in `src/fitcv_cp/app.py` only where a capability is
  truly assembled in app rather than merely styled by the template

Likely proof surfaces:

- existing inspection-card and attached-tab tests in
  `tests/test_fitcv_cp/test_app.py`
- existing runs-list structure tests in `tests/test_fitcv_cp/test_app.py`
- potentially a few small new explicit HTML assertions for theme bootstrap or
  token presence if current coverage is still too indirect

## Goal

Create a Phase 13 implementation plan that:

1. audits the remaining six theming capabilities against the actual base-template
   and existing test surface
2. identifies which capabilities can be completed with current explicit tests
   versus which need a small direct proof test
3. adds sparse metadata to `base.html` and only to `app.py` if app materially
   owns the capability
4. adds truthful `@proves` markers to explicit structural/theming tests
5. extends pilot enforcement only for completed theming capabilities
6. regenerates feature contracts, lineage, and generated discovery
7. records before/after gap counts and any residual deliberate deferrals

## Non-Goals

This phase does not:

- redesign the admin UI or theme system
- broaden into `cv_system`, `bounded_parallel_enrichment`, or
  `inspection_debugging`
- infer visual behavior from screenshots or subjective inspection
- claim a capability complete without direct code and direct proof evidence
- force every deferred capability to complete if direct proof still is not
  truthful

## Proposed Shape

### 1. Base-Template Theming Audit

The implementation plan should start with a mapping table containing:

- capability ID
- candidate owning file(s)
- candidate proving test(s)
- confidence: `complete_candidate` or `defer`
- rationale

This audit should distinguish:

- pure base-template capabilities, such as token definitions and theme bootstrap
- rendered structural capabilities, such as attached tabs and wrapping
- capabilities that may need a tiny new direct HTML assertion to become
  truthful proof

### 2. Sparse Template Metadata Backfill

Add metadata only where the behavior is materially implemented:

- `src/fitcv_cp/templates/base.html` for theme bootstrap, tokens, shared
  classes, attached tab styles, and wrapping rules
- `src/fitcv_cp/app.py` only if a capability depends on server-side page
  assembly rather than template-level styling alone
- if template-owned behavior cannot be truthfully attached to Python, add the
  smallest repo-local sync support needed to ingest bounded template metadata
  rather than forcing ownership onto unrelated Python surfaces

### 3. Truthful Theme And Layout Proof Markers

Use `@proves <capability_id>` only where tests directly assert:

- the presence of the attached inspection card and attached tab bar pattern
- the presence of shared structural hooks for action bars or wrapped layouts
- the theme bootstrap script and localStorage-based `data-theme` behavior, if a
  direct HTML assertion is added
- the presence of CSS token definitions or shared class hooks, if a direct
  template assertion is added

### 4. Enforcement Extension

Extend `repo_config/adoption-mode.yaml` only for the theming capabilities that
reach both direct code and direct test evidence in this phase.

### 5. Regeneration And Measurement

Run:

- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`

Measure:

- updated `ui_consistency_theming` gap counts
- updated repo-wide totals
- which Phase 13 capabilities reached `completeness_status: complete`
- which capabilities, if any, remain deliberately deferred

## Acceptance Criteria

Phase 13 is ready for implementation when:

1. an implementation plan exists with exact theming capability-to-file and
   capability-to-test mappings
2. weak or indirect mappings are explicitly deferred
3. selected capabilities have direct code evidence
4. selected capabilities have direct test evidence
5. pilot enforcement covers only completed mappings
6. generated feature contracts and lineage are refreshed
7. generated discovery outputs are refreshed
8. focused theming/UI tests for touched files pass
9. `scripts/sync_architecture_docs.py --check` passes
10. `scripts/validate_adoption_shape.py` passes
11. `git diff --check` has no whitespace errors
12. post-phase gap counts are recorded in both the plan and the completed spec

## Risks And Guardrails

- Risk: `base.html` gets tagged for everything just because it holds the shared
  stylesheet. Guardrail: only tag capabilities actually implemented there, and
  keep app-owned structural assembly distinct.
- Risk: attached-tab and inspection-card tests prove debugging content rather
  than the shared UI pattern. Guardrail: only use tests that explicitly assert
  `.inspection-card` and `.tab-bar--attached` structure.
- Risk: token/localStorage/flash-free capabilities still have only code
  evidence. Guardrail: add a tiny direct template assertion if needed; otherwise
  keep them deferred.
- Risk: responsive wrapping remains subjective. Guardrail: require explicit HTML
  hook or class assertions tied to the shared layout, not implied screen-size
  behavior.

## Validation Plan

Minimum validation:

- `.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py tests/test_validate_adoption_shape.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py`
- `.\.venv\Scripts\python.exe scripts/sync_architecture_docs.py --check`
- `.\.venv\Scripts\python.exe scripts/validate_adoption_shape.py`
- `git diff --check`

## Rollback Plan

If Phase 13 over-attributes theming evidence:

1. remove the Phase 13 metadata and `@proves` markers
2. remove the Phase 13 adoption-mode entries
3. restore any touched semantic source if the audit changed it
4. rerun `scripts/sync_architecture_docs.py`
5. rerun validation to return to the post-Phase-12 baseline

## Execution Notes

Status: `completed`

Executed via `docs/superpowers/plans/2026-04-22-17-05-phase-13-ui-theming-completion-plan.md`.

Completed changes:

- added repo-local template architecture parsing in `scripts/sync_architecture_docs.py`
- added selective `base.html` ownership metadata for all six deferred
  `ui_consistency_theming` capabilities
- added direct `@proves` coverage for theme bootstrap, design tokens, shared
  classes, attached inspection tabs, and responsive wrapping
- extended the direct-evidence pilot in `repo_config/adoption-mode.yaml`

Measured result:

- `ui_consistency_theming` moved from `6/6` missing code/test evidence to `0/0`
- repo-wide missing direct evidence moved from `63/63` to `14/14`
