---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: settings-page-deprecated-surface-removal
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
related_features:
  - settings_system
  - admin_control_plane_core
related_stages:
  - cv_generation
  - cv_analysis
---

## Goal

Remove deprecated AI/data-plane settings controls from operator settings page so page reflects canonical runtime authority only, while preserving compatibility layer internally until removal gates close.

## Key Deliverables

### Deliverable 1: Settings-page visibility contract for deprecated surfaces

Define explicit rule for which keys are shown, hidden, or metadata-only in `/admin/settings`, including phase-gated deprecation behavior and owner/source labels.

### Deliverable 2: Canonical AI-plane controls-only operator experience

Ensure operator-facing AI controls map only to supported unified agentic and openai-compatible paths; deprecated Gemini/legacy authority controls are not shown as active controls.

### Deliverable 3: Regression-proof validation coverage

Add/update tests proving hidden deprecated keys are absent from rendered settings UI and cannot be mutated through page save paths.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish current render pipeline and deprecated-key inventory

**Steps:**
- [ ] inventory keys rendered by `settings_page_sections` and card key lists
- [ ] classify each key as canonical-editable, metadata-only, deprecated-hidden, or internal-compat
- [ ] map current save routes and identify any deprecated-key write path

**Verification:**
- [ ] documented key classification table exists and maps to concrete schema keys

**Exit Criteria:**
- no hidden assumptions about what is currently rendered or writable

### Wave 2: Decision closure

**Purpose:**
- finalize UI visibility and enforcement policy for deprecated settings

**Steps:**
- [ ] add deprecation visibility policy in settings schema/context build
- [ ] remove deprecated keys from task cards and section/group saves
- [ ] keep compatibility projection/load behavior internal (non-UI authority)
- [ ] preserve metadata-only explanatory rows that remain canonical-relevant

**Verification:**
- [ ] every deprecated key has one explicit disposition (hide/remove/metadata-only)

**Exit Criteria:**
- settings UI and save semantics are symmetric with runtime authority

### Wave 3: Validation and approval readiness

**Purpose:**
- prove behavior and contract preservation with tests/docs

**Steps:**
- [ ] add render assertions for hidden deprecated rows
- [ ] add save-route assertions rejecting deprecated writes
- [ ] update docs to explain runtime deprecation vs UI removal

**Verification:**
- [ ] validation plan evidence collected and reproducible

**Exit Criteria:**
- patch ready for implementation planning/execution

## Design Decisions

### Decision: Deprecation visibility state machine

- context: current page mixes canonical controls and compatibility/deprecated surfaces, creating false authority signal.
- choice: introduce per-key `ui_deprecation_state` contract with values:
  - `active`: render normally
  - `metadata_only`: render read-only explanation
  - `hidden_deprecated`: do not render and do not accept page writes
- alternatives considered:
  - keep rendering deprecated rows with warning badges
  - hard-delete keys from schema immediately
- impact:
  - keeps compatibility internals intact while removing operator confusion
  - enables staged retirement without breaking old persisted settings snapshots

### Decision: Single authority for AI settings surface

- context: migration goal requires symmetry/invariance/equivalence and SSOT for AI-plane controls.
- choice: `/admin/settings` AI card set must expose only keys that influence canonical unified runtime contract; deprecated provider-authority knobs are hidden.
- alternatives considered:
  - retain dual-authority display (`legacy + canonical`) with precedence note
- impact:
  - prevents inconsistent operator edits
  - aligns UI with live-run behavior and plan invariants

### Decision: Enforced write rejection for hidden deprecated keys

- context: hiding UI alone insufficient if group/section routes still accept keys.
- choice: save paths must reject deprecated-hidden keys with 422 and explicit reason.
- alternatives considered:
  - silently ignore deprecated keys on write
- impact:
  - stronger safety and auditability
  - deterministic failure behavior in tests

## Invariants

- settings page must not present deprecated keys as active runtime controls.
- canonical runtime authority for AI-plane routing remains openai-compatible + unified agentic path.
- compatibility loading/projection may remain internal but must not create new operator-facing authority surfaces.
- run-level historical truth (`settings-used.json`) remains unchanged.
- backend symmetry (sqlite/bigquery) must not diverge due to settings-page visibility changes.

## Acceptance Criteria

- `/admin/settings` HTML contains no deprecated-hidden keys or deprecated card controls.
- deprecated-hidden keys cannot be persisted via single-key, group, or section save routes.
- metadata-only rows that remain are explicitly marked and non-editable.
- all existing canonical settings controls continue to render and save successfully.
- docs explain distinction: internal compatibility support vs operator-visible authority.

## Non-Goals

- remove legacy compatibility projection from runtime config loading.
- change late-stage pipeline logic or provider execution behavior.
- redesign overall settings IA beyond deprecated-surface removal.
- alter run history/export schemas.

## Risks and Mitigations

- risk: accidentally hide still-needed canonical control.
  - mitigation: explicit key classification table + regression tests for required visible keys.
- risk: stale templates still reference removed keys, causing form errors.
  - mitigation: render tests and route tests per card/section.
- risk: docs drift from behavior.
  - mitigation: update `docs/configuration.md` in same patch and run validators.

## Validation Plan

- proof target: deprecated keys are not rendered in settings page
  - method: integration test on `/admin/settings` HTML
  - evidence: `pytest tests/test_fitcv_cp/test_app.py -k "settings.*deprecated.*hidden"` passing assertions

- proof target: deprecated keys are rejected by all save surfaces
  - method: API/HTML route tests for `/admin/settings/{key}`, `/admin/settings/group/{group}`, `/admin/settings/section/{section}`
  - evidence: 422 responses with deterministic message for deprecated-hidden keys

- proof target: canonical settings still editable
  - method: existing settings save tests + targeted smoke updates
  - evidence: passing tests for representative keys in Selection/Agentic/Ranking/CV Output cards

- proof target: docs and governance alignment preserved
  - method: repo validators
  - evidence:
    - `python scripts/hooks/run_validator.py --fast`
    - `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
