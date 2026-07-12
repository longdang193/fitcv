---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-ssot-symmetry-phase-3-settings-schema-native-form-boundary
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-12-18-35-fitcv-ssot-symmetry-phase-3-settings-schema-native-form-boundary-spec.md
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - docs/api.md
  - docs/architecture.md
  - docs/configuration.md
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - settings_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Execute Phase 3 from
`docs/superpowers/specs/2026-07-12-18-35-fitcv-ssot-symmetry-phase-3-settings-schema-native-form-boundary-spec.md`:

- make `src/fitcv_cp/settings_schema.py` sole human-owned owner for
  settings-page semantics
- keep upstream native option/default truth with existing owners and adapt it at
  schema boundary
- replace app-local settings-page assembly with one schema-owned page contract
- make default hydration explicit and native-form behavior symmetric

## Key Deliverables

### Deliverable 1: schema owns settings-page semantics and default vocabulary

`src/fitcv_cp/settings_schema.py` owns per-key page semantics, editability,
save-scope membership, grouping metadata, and four explicit value states:
`declared_default`, `baseline_default`, `saved_override`, and
`effective_value`.

### Deliverable 2: one page contract replaces parallel registries

`src/fitcv_cp/app.py` consumes one schema-owned derived page contract for
ordered sections/cards/entry keys, decision tabs, domain filters, stage scopes,
control-surface filters, and grouped save scopes. Handwritten semantic
registries stop being independent owners.

### Deliverable 3: native form boundary stays thin and bounded

`src/fitcv_cp/templates/settings.html` renders native attrs from schema-owned
metadata. `src/fitcv_cp/app.py` keeps request state only. Runtime-env note
behavior, if preserved, stays limited to current temporary presentation fields.

### Deliverable 4: proof and docs stay bounded to Phase 3

Focused schema/store/app tests, residue greps, planning-lineage refresh, fast
validator, and minimal cross-cutting doc updates prove Phase 3 landed without
pulling Phase 4 routing/env redesign into scope.

## Task/Wave Breakdown

### Task 1: Lock schema owner boundary and default states

**Purpose:**
- make `settings_schema.py` explicit owner for page semantics while keeping
  upstream native option/default truth upstream-owned

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Verify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`

**Preconditions:**
- Phase 3 spec accepted
- no Phase 4 routing/env authority redesign mixed into this task

**Steps:**
- [ ] Step 1: inventory every page-semantic fact still owned outside schema rows
      and move only missing page-semantic metadata into schema-owned surfaces.
- [ ] Step 2: keep upstream native option/default truth with existing owners and
      adapt/reference it in schema helpers instead of copying it into new
      registries.
- [ ] Step 3: replace import-time default mutation semantics with explicit owner
      helpers that preserve `declared_default` and expose `baseline_default` and
      `effective_value` only through runtime overlay paths.
- [ ] Step 4: add schema tests that prove four-state default behavior and prove
      native upstream option/default adaptation stays boundary-local.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- one schema-owned path explains page semantics and default vocabulary for any
  admin-visible key

### Task 2: Build one derived page contract and retire parallel registries

**Purpose:**
- replace handwritten grouping registries with one authoritative derived page
  contract

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- page-semantic metadata is explicit enough to derive all required projections

**Steps:**
- [ ] Step 1: add one schema-owned page contract helper such as
      `build_settings_page_spec(...)` that returns ordered sections/cards/entry
      keys, decision tabs, domain filters, stage scopes, control-surface
      filters, and save-scope groupings.
- [ ] Step 2: delete or demote `RANKING_GROUPS`, `SETTINGS_SECTIONS`,
      `AGENTIC_SETTINGS_SECTIONS`, and `CV_GROUPS` so they are no longer
      handwritten semantic owners.
- [ ] Step 3: derive editable, metadata-only, and hidden-deprecated grouping
      behavior from schema-owned contract surfaces instead of parallel free
      sets.
- [ ] Step 4: add schema tests that lock ordering, stable IDs, and key
      membership for derived page outputs.

**Verification:**
- [ ] `rg -n "^RANKING_GROUPS:|^SETTINGS_SECTIONS:|^AGENTIC_SETTINGS_SECTIONS:|^CV_GROUPS:|^_EDITABLE_KEYS:|^_HIDDEN_DEPRECATED_KEYS:" src/fitcv_cp/settings_schema.py`
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:**
- app can consume one page contract without consulting second semantic
  registries

### Task 3: Thin app and template to boundary adapters

**Purpose:**
- keep `app.py` request-scoped and `settings.html` native-first

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete
- schema-owned page contract exists

**Steps:**
- [ ] Step 1: replace inline settings-page assembly in `app.py` with one call to
      schema-owned page contract helpers.
- [ ] Step 2: keep only request-local draft/error/dirty/current/effective state
      shaping in `app.py`.
- [ ] Step 3: keep template rendering native attrs from schema-derived metadata
      and delete any template/JS duplication of validation or key-eligibility
      rules.
- [ ] Step 4: keep runtime-env note logic, if still present, limited to current
      temporary presentation fields and prevent it from becoming page-semantic
      owner logic.
- [ ] Step 5: add app tests that lock rendered section/card/filter behavior and
      bounded runtime note behavior.

**Verification:**
- [ ] `rg -n "def _decision_domain_for_entry|settings_page_task_sections = \[|decision_tabs = \[|decision_domain_filters = \[" src/fitcv_cp/app.py`
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -q`

**Exit Criteria:**
- `app.py` is boundary adapter for request state, not second owner for settings
  meaning

### Task 4: Prove save flows, update docs, and close bounded scope

**Purpose:**
- prove save/read behavior still matches schema owner contract and refresh docs

**Files:**
- Modify: `src/fitcv_cp/settings_store.py`
- Modify: `docs/api.md`
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `tests/test_fitcv_cp/test_settings_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Tasks 1-3 complete

**Steps:**
- [ ] Step 1: adjust store boundary behavior only where needed so alias
      normalization, metadata-only writes, hidden-deprecated writes, and grouped
      save flows all follow same schema-owned contract.
- [ ] Step 2: add store regressions for single-key, group, and section saves so
      `saved_override` behavior stays distinct from `baseline_default` and
      `declared_default`.
- [ ] Step 3: update cross-cutting docs only where settings owner boundaries,
      page contract, or default semantics changed.
- [ ] Step 4: run residue greps, compile checks, focused pytest set, planning
      lineage refresh, and fast validator.
- [ ] Step 5: confirm no Phase 4 routing/env authority redesign slipped into
      touched files.

**Verification:**
- [ ] `py -3 -m py_compile src/fitcv_cp/settings_schema.py src/fitcv_cp/settings_store.py src/fitcv_cp/app.py`
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py -q`
- [ ] `py -3 scripts/generate_planning_lineage.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Phase 3 is proven bounded, symmetric, and ready for execution without
  reopening owner questions

## Verification

- `rg -n "^RANKING_GROUPS:|^SETTINGS_SECTIONS:|^AGENTIC_SETTINGS_SECTIONS:|^CV_GROUPS:|^_EDITABLE_KEYS:|^_HIDDEN_DEPRECATED_KEYS:" src/fitcv_cp/settings_schema.py`
- `rg -n "def _decision_domain_for_entry|settings_page_task_sections = \[|decision_tabs = \[|decision_domain_filters = \[" src/fitcv_cp/app.py`
- `rg -n "_hydrate_schema_defaults_from_config\(|settings_schema_with_runtime_defaults|FITCV_LANGGRAPH_PROVIDER|FITCV_LANGGRAPH_MODEL" src/fitcv_cp/settings_schema.py src/fitcv_cp/app.py`
- `py -3 -m py_compile src/fitcv_cp/settings_schema.py src/fitcv_cp/settings_store.py src/fitcv_cp/app.py`
- `py -3 -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py -q`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

