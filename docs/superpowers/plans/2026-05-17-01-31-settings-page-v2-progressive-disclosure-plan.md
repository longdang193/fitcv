---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: settings-page-v2-progressive-disclosure-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-17-01-24-settings-page-v2-progressive-disclosure-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - settings_system
  - cv_system
related_stages:
  - cv_generation
---

## Goal

Implement Settings page V2 with compact domain-first navigation, workflow-stage filtering, progressive disclosure editing, and explicit effective/inherited/override visibility while preserving existing backend settings semantics.

## Key Deliverables

### Deliverable 1: V2 IA shell and compact navigation

Settings page ships a compact shell with domain navigation (`General`, `Layers`, `Stages`, `Rules`, `Integrations`, `Advanced`) and stage filter chips (`Setup`, `Draft`, `Review`, `Approved`, `Archived`) without rendering all controls expanded.

### Deliverable 2: Progressive disclosure and contextual editing

Settings controls migrate to summary-first rows, inline expanders, and contextual detail surfaces so deep editing is available without default clutter.

### Deliverable 3: Effective/default/override clarity and diagnostics

Every editable setting visibly reports effective value, inherited/default source, override state, and state indicators for modified/errors/overrides.

### Deliverable 4: Risk-isolated advanced controls and regression safety

Rare/destructive controls are isolated under `Advanced`/`Danger Zone` with guardrails; automated tests verify discoverability, compactness, and backend contract invariance.

## Task/Wave Breakdown

### Task 1: Define canonical V2 taxonomy and mapping contract

**Purpose:**
- establish one source for domain/stage/risk/override metadata used by backend and template

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- V2 spec approved (`2026-05-17-01-24-settings-page-v2-progressive-disclosure-spec.md`)

**Steps:**
- [ ] Step 1: extend per-key IA metadata to include V2 domains, workflow stages, risk tier, and override policy flags.
- [ ] Step 2: add helper accessors for domain groups, stage groups, and danger-zone key selection.
- [ ] Step 3: add mapping coverage tests to fail on orphan/duplicate taxonomy assignments.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- all settings keys are mapped to exactly one V2 domain and at least one stage tag

### Task 2: Build V2 backend view-model surface

**Purpose:**
- provide template-ready compact summaries, filtered collections, and override metadata without changing save endpoints

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: construct domain navigation model and stage-filter model in settings context payload.
- [ ] Step 2: emit per-row summary fields (`effective_value`, `source_label`, `override_state`, `has_error`, `is_modified`).
- [ ] Step 3: emit advanced/danger-zone partitions and guarded-save requirements.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -q -k settings`

**Exit Criteria:**
- backend context supports compact default rendering and contextual expansion workflows

### Task 3: Implement V2 template shell with progressive disclosure

**Purpose:**
- replace dense long-form layout with compact summary-first UX and contextual editing

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: add domain nav rail, stage chips, search/filter bar, and section summary cards.
- [ ] Step 2: implement collapsed-by-default rows with inline expand and contextual detail panel patterns.
- [ ] Step 3: move long explanatory copy into tooltip/help/learn-more expanders; keep row copy compact.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -q -k "settings and (render or template)"`

**Exit Criteria:**
- default page is compact; users can navigate/edit without full-page expansion

### Task 4: Add override-first editing and diagnostics indicators

**Purpose:**
- make inherited/default state explicit and expose override controls only on intent

**Files:**
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: render effective/source badges and hide direct override inputs until `Enable override` activation.
- [ ] Step 2: add modified/error/override chips at row and section summaries.
- [ ] Step 3: add reset actions (`Reset field`, `Reset section`) while preserving backend payload semantics.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -q -k "override or modified or error"`

**Exit Criteria:**
- users can clearly distinguish inherited defaults from active overrides before editing

### Task 5: Isolate advanced/danger settings and guardrails

**Purpose:**
- separate rare/destructive controls and enforce safer interactions

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-4 complete

**Steps:**
- [ ] Step 1: mark dangerous/rare keys in taxonomy and route them to dedicated Advanced/Danger sections.
- [ ] Step 2: add confirmation/preflight guardrails for risky saves and keep backend validation canonical.
- [ ] Step 3: verify risky controls are absent from default high-frequency views.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q -k "danger or advanced or guardrail"`

**Exit Criteria:**
- destructive/rare settings are isolated and guarded without changing backend validation outcomes

### Task 6: V2 parity and regression closure

**Purpose:**
- prove V2 UX goals and invariants are met without behavior regressions

**Files:**
- Inspect: `src/fitcv_cp/settings_schema.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/settings.html`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [ ] Step 1: add tests for key discoverability via both domain and stage filters.
- [ ] Step 2: add tests for compact default render (not fully expanded) and contextual disclosure behavior.
- [ ] Step 3: run full settings-focused regression checks and document any residual manual smoke gaps.

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- automated evidence confirms V2 navigation clarity and contract preservation

## Verification

- `pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- `pytest tests/test_fitcv_cp/test_app.py -q`
- `python scripts/validate_planning_lifecycle.py --strict`
- `python scripts/validate_checkpoint_packs.py`
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
