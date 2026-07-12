---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-phase-3-settings-schema-native-form-boundary
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
  - docs/superpowers/specs/2026-05-18-22-49-settings-schema-ssot-refactor-spec.md
  - docs/superpowers/specs/2026-05-17-19-22-pipeline-settings-decision-focused-ia-v4-spec.md
  - docs/features/settings_system/feature.source.yaml
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

# Detailed Spec: FitCV SSOT / symmetry Phase 3 settings-schema and native-form boundary convergence

## Goal

Execute third concrete remediation lane from
`docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`:

- make `src/fitcv_cp/settings_schema.py` the sole human-owned registry for
  settings-page semantics, while upstream native option/default truth stays with
  its existing owners and is adapted at schema boundary
- derive one canonical settings-page contract from schema-owned metadata instead
  of rebuilding sections/cards/groups/filters in `app.py`
- keep browser-native form behavior primary and adapt schema data at the HTML
  boundary instead of recreating validation/affordances in route or JavaScript
- stop mutating schema defaults at import time; make runtime default hydration an
  explicit overlay step

This phase is settings-owner convergence only. It does not redesign runtime
routing truth, LangGraph env interpretation, or SQLite backend semantics.

## Problem

Current repo already has useful settings owner pieces, but Phase 3 drift is
still live in four places:

1. `SETTINGS_SCHEMA` is not yet full page-semantic SSOT.
   - key/type/declared-default/config-path metadata lives in schema rows
   - but task sections, cards, stage grouping, decision-board grouping, and
     some domain classification still depend on parallel constants or app-local
     assembly logic
   - schema also overclaims ownership when upstream native option/default truth
     should stay with existing owners and only be adapted at boundary

2. settings page projections are still partly owned in `src/fitcv_cp/app.py`.
   - `_decision_domain_for_entry(...)`
   - task-section/card assembly
   - decision-tab/domain/stage/control-surface filter assembly
   - dirty/read-only/current-vs-draft view shaping intermixed with schema
     meaning

3. native-form truth is only partially symmetric.
   - `settings_native_input_attrs(...)` already exists
   - but editable/metadata-only/hidden-deprecated handling still depends on
     parallel set registries and route/template logic
   - template and server do not yet derive their full control contract from one
     owner row per key

4. schema defaults still mutate at import via
   `_hydrate_schema_defaults_from_config()`.
   - this makes schema truth environment-dependent before any caller asks for
     runtime overlay
   - callers cannot cleanly distinguish declared default from active baseline

Until this lane lands, settings behavior remains explainable only by reading
schema rows plus app-local shaping code plus parallel registries plus implicit
default mutation. That violates SSOT, breaks symmetry between server
validation/template rendering, and hides which defaults are declared vs runtime
baseline vs saved override.

## Relationship To Existing Specs

This Phase 3 spec is authoritative only for bounded settings-owner convergence
after Phase 1 and Phase 2.

- `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
  remains parent authority for phase order, final target architecture, and
  cross-phase invariants.
- `docs/superpowers/specs/2026-05-18-22-49-settings-schema-ssot-refactor-spec.md`
  is the closest precursor and remains useful design background, but this Phase
  3 spec supersedes it for current bounded implementation scope.
- `docs/superpowers/specs/2026-05-17-19-22-pipeline-settings-decision-focused-ia-v4-spec.md`
  remains historical UI-background context only. This Phase 3 spec owns current
  runtime/code convergence rules.
- Phase 2 outputs are preconditions here. Stage and lifecycle owners are now
  stable enough that settings stage metadata can bind to canonical stage IDs
  without parallel reinterpretation.

## Triage

Layer: change
Feature type: REPLACE
Summary: replace parallel settings registries, app-local page classification,
and import-time default mutation with one schema-owned settings contract plus
native boundary adapters
Reasoning: repo already has `SETTINGS_SCHEMA`, IA metadata helpers,
`settings_native_input_attrs(...)`, and canonical key normalization. Phase 3
should finish those owners, not add second registries or service layers.
Invariants:
  - each admin-editable or admin-visible setting key has one schema row as the
    human-owned source of truth for settings-page semantics
  - upstream native option/default truth stays with its existing owner and is
    referenced or adapted at schema boundary rather than recopied into parallel
    registries
  - page sections/cards/groups/filters are derived projections, not second
    human-maintained registries
  - app consumes one authoritative derived page contract instead of assembling
    independent tabs/domains/stage scopes/control-surface filters inline
  - server coercion/validation and browser-native control attrs are derived
    from same owner metadata
  - declared schema defaults are immutable; runtime baseline defaults are
    explicit overlay output
  - compatibility aliases and hidden-deprecated write rules stay boundary-local
    and do not spread into unrelated routes or templates
Dependencies:
  - completed Phase 1 and Phase 2 remediation lanes
  - existing `SETTINGS_SCHEMA`, `settings_ia_metadata_by_key()`,
    `settings_native_input_attrs()`, `canonical_settings_key()`, and
    `_normalize_settings_aliases()` owner surfaces
Affected stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
Affected features:
  - settings_system
Primary lens: cross-cutting
Affected docs:
  feature_source:
    - docs/features/settings_system/feature.source.yaml
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs: []
  cross_cutting_docs:
    - docs/api.md
    - docs/architecture.md
    - docs/configuration.md
  readme: none
  generated: []
Generated refresh required: no
Capability IDs:
  - settings_system.settings-schema-registry
  - settings_system.task-first-settings-ui
  - settings_system.grouped-form-validation
  - settings_system.metadata-only-fixed-controls
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: per-key schema row becomes sole settings registry

Phase 3 must make one per-key row in `SETTINGS_SCHEMA` the only human-owned
registry for settings-page semantics.

That does not mean every default or option list gets duplicated into schema.
When option/default truth already belongs to a native upstream owner, Phase 3
must keep that truth there and adapt/reference it at the schema boundary.

That owner must be sufficient to derive:

- key, type, declared default, and config path
- editable vs metadata-only vs hidden-deprecated surface state
- task section and card placement
- stage and workflow-stage participation
- decision-board grouping metadata
- native input attrs and option lists
- save-scope membership where the UI batches settings together

If current row shape cannot express one of these cleanly, Phase 3 may add the
minimum new row metadata needed. It must not add a second top-level registry to
hold the missing concept.

### Deliverable 2: settings page assembly becomes schema-derived

`src/fitcv_cp/app.py` must stop owning settings-page meaning.

Phase 3 must expose one schema-owned derived page contract. Preferred owner
surface: `build_settings_page_spec(...)` in `src/fitcv_cp/settings_schema.py`.
If an existing helper is extended instead, result must still behave as one
authoritative contract, not a loose bundle of parallel registries.

Minimum contract fields:

- ordered `sections` with stable `id`, `title`, ordered `cards`, and ordered
  `entry_keys`
- ordered `decision_tabs`
- ordered `decision_domain_filters`
- ordered `stage_scopes`
- ordered `control_surface_filters`
- save-scope/group membership keyed by stable IDs instead of app-local lists

App-layer responsibility after Phase 3:

- load effective settings
- hold request-scoped draft/error/dirty state
- call schema-owned helpers to get page spec / filters / grouping
- pass rendered boundary data to template

Schema-layer responsibility after Phase 3:

- derive task sections, cards, stage groups, decision groups, and control
  surface filters from canonical row metadata
- own decision-domain/stage/control-surface classification rules
- own page-level grouping order and stable IDs for those projections

Examples of app-local owner logic that should retire or move behind
schema-owned helpers:

- `_decision_domain_for_entry(...)`
- inline task-section/card/group builders
- inline decision-tab/domain/stage/control-surface assembly

### Deliverable 3: native-form boundary is explicit and symmetric

Phase 3 must preserve browser-native controls as primary behavior.

Rules:

- template renders native attrs from schema-derived metadata
- server coercion and validation use same owner metadata
- metadata-only keys render as non-editable informational controls, not fake
  editable fields later blocked by route code
- hidden-deprecated keys stay absent from editable UI except explicit bounded
  compatibility surface already approved by schema contract
- JavaScript may keep submit-preflight, dirty-state, and filter/disclosure UX,
  but must not become a second validation engine

### Deliverable 4: default hydration becomes explicit overlay, not mutation

`SETTINGS_SCHEMA` declared defaults must stop changing at import time.

After Phase 3:

- schema rows preserve declared defaults as static truth
- callers that need runtime baseline defaults use explicit overlay helpers such
  as `settings_schema_with_runtime_defaults(...)`
- admin UI can still show effective baseline/default values, but only through
  explicit runtime overlay output

Required default vocabulary after Phase 3:

- `declared_default`: immutable value authored in schema row
- `baseline_default`: runtime default after explicit overlay from native runtime
  owner/config
- `saved_override`: persisted admin-authored override in settings store
- `effective_value`: value used by page/runtime consumer after applying
  `saved_override` first, else `baseline_default`

### Deliverable 5: compatibility and save-scope rules stay boundary-local

Phase 3 must keep compatibility logic minimal and local.

Allowed boundary-local surfaces:

- `canonical_settings_key(...)`
- `_normalize_settings_aliases(...)`
- persistence/read-path normalization in settings store if still needed

Disallowed after Phase 3:

- route-local duplicate alias maps
- template-local knowledge of compatibility aliases
- parallel writable-key registries outside schema-owned contract

## Design Decisions

### Decision: expand existing `settings_schema.py`; do not create a second UI registry

- context: repo already has `SETTINGS_SCHEMA`, IA metadata helpers, native attr
  helpers, and decision-state helpers
- choice: finish owner convergence in that file instead of creating
  `settings_registry.py`, `settings_ui_model.py`, or similar parallel layers
- consequences:
  - shortest path to SSOT
  - fewer files and fewer sync points
  - settings page remains boundary consumer, not semantic owner

### Decision: retire handwritten grouping registries in favor of row-derived projections

- context: `RANKING_GROUPS`, `SETTINGS_SECTIONS`, `AGENTIC_SETTINGS_SECTIONS`,
  and `CV_GROUPS` are current drift candidates because they restate grouping
  facts already implied by key semantics
- choice: make these groupings generated projections from per-key metadata, or
  remove them entirely in favor of helper outputs
- alternatives considered:
  - keep manual registries and harden parity tests only
  - move grouping rules into `app.py` instead
- consequences:
  - grouping edits happen in one row, not two registries
  - task-first page stays stable without hidden duplication
  - any surviving constants become generated projections only, not handwritten
    semantic owners

### Decision: app computes state, schema computes meaning through one page contract

- context: settings page needs request-scoped dirty/error/current-vs-draft
  values that do belong at boundary, but card/section meaning does not
- choice: keep app responsible only for request/runtime state; move semantic
  section/card/filter/group derivation into one schema-owned page contract
- consequences:
  - clean boundary split
  - no second semantic owner in route code

### Decision: defaults use four explicit value states

- context: current import-time mutation blurs declared default, runtime
  baseline, stored override, and final effective value
- choice: Phase 3 uses four explicit states only:
  - `declared_default`
  - `baseline_default`
  - `saved_override`
  - `effective_value`
- alternatives considered:
  - keep mutating schema defaults at import time
  - infer runtime baseline implicitly in route code
- consequences:
  - tests can prove each state separately
  - UI/store/runtime consumers stop guessing what “default” means

### Decision: browser-native constraints remain first-class

- context: user explicitly prefers native components with boundary adaptation
- choice: continue native `<input>`, `<select>`, checkbox, min/max/step, and
  option rendering; derive attrs from schema owner and keep JS non-authoritative
- alternatives considered:
  - custom validation rules in JS
  - parallel template metadata registry
- consequences:
  - stronger symmetry between what browser allows and what server accepts
  - less custom code to maintain

### Decision: runtime-env routing note stays only as bounded temporary exception

- context: settings page currently shows agentic runtime env drift notes, but
  runtime routing truth belongs to Phase 4
- choice: Phase 3 may preserve current app-local runtime note behavior only as
  temporary presentation output for these existing fields:
  - `agentic_mode`
  - `runtime_provider`
  - `runtime_model`
  - `authority_state`
  - `drift_reason`
  - appended `agentic_runtime_note` text in `settings_truth_notes`
  It must not own settings grouping, editability, save-scope, or routing
  authority semantics beyond that note.
- consequences:
  - phase boundary stays tight
  - note cannot grow into second semantic owner
  - routing truth still converges in Phase 4, not opportunistically here

## Task/Wave Breakdown

### Wave 1: source-first owner map

**Purpose:**
- turn current settings surface into exact owner/deletion decisions before code
  planning

**Steps:**
- [ ] enumerate every settings meaning currently owned outside schema rows
- [ ] classify each as `move into row metadata`, `derive from existing row
      metadata`, or `delete as duplicate`
- [ ] identify which option/default surfaces stay upstream-native and which only
      need boundary adaptation in schema helpers
- [ ] confirm which compatibility aliases and hidden-deprecated keys are still
      intentionally supported
- [ ] confirm which settings docs/feature-source claims change when schema
      owner converges

**Verification:**
- [ ] every page/group/filter/save-scope concept maps to one chosen owner

**Exit Criteria:**
- no implementation step depends on vague “settings cleanup” wording

### Wave 2: schema-owner completion

**Purpose:**
- make `SETTINGS_SCHEMA` row metadata sufficient to derive all active settings
  surface projections

**Steps:**
- [ ] add minimal per-row metadata needed for task section, card, save-scope,
      stage-group, and surface placement if current fields are insufficient
- [ ] define one authoritative derived page contract for sections/cards/tabs/
      filters/scopes instead of multiple app-facing registries
- [ ] retire or generate current manual registries such as
      `RANKING_GROUPS`, `SETTINGS_SECTIONS`, `AGENTIC_SETTINGS_SECTIONS`, and
      `CV_GROUPS`
- [ ] make editable / metadata-only / hidden-deprecated classification derive
      from schema-owned contract rather than parallel free-floating sets
- [ ] keep explicit transitional allowlist only where a bounded compatibility
      surface is still intentional

**Verification:**
- [ ] repo search shows no second handwritten settings grouping registry
      survives outside schema-owned derivation path
- [ ] any remaining constant projection is generated from schema-owned metadata
      and not edited as independent semantic truth

**Exit Criteria:**
- one schema row is enough to explain where and how a key appears

### Wave 3: boundary convergence in app and template

**Purpose:**
- keep app/template thin and native-first

**Steps:**
- [ ] move semantic task-section/card/filter/group derivation out of
      `src/fitcv_cp/app.py` and behind schema-owned helpers
- [ ] make `src/fitcv_cp/app.py` consume one authoritative page contract rather
      than assembling `decision_tabs`, `decision_domain_filters`, stage scopes,
      or control-surface filters inline
- [ ] keep app-layer draft/error/dirty/current state assembly only
- [ ] keep template rendering native attrs from schema-derived metadata
- [ ] remove any JS or template logic that duplicates server validation or key
      eligibility rules
- [ ] keep runtime-env note logic bounded to existing temporary presentation
      fields only; do not expand it into schema/page ownership

**Verification:**
- [ ] route/template logic does not restate decision-domain, stage, or control
      surface ownership independently of schema owner

**Exit Criteria:**
- settings page is boundary adapter, not semantic co-owner

### Wave 4: default overlay and compatibility proof

**Purpose:**
- make defaults and alias handling explicit, deterministic, and bounded

**Steps:**
- [ ] remove import-time mutation of declared schema defaults
- [ ] preserve runtime baseline-default behavior through explicit overlay helper
      output only
- [ ] prove `declared_default`, `baseline_default`, `saved_override`, and
      `effective_value` remain distinct in schema/store/app tests
- [ ] keep alias normalization in one boundary owner path
- [ ] verify group/section/single-key save flows honor same write contract for
      metadata-only and hidden-deprecated keys

**Verification:**
- [ ] schema import no longer depends on local environment to define declared
      defaults

**Exit Criteria:**
- declared default, active value, and compatibility alias are all distinct and
  traceable

## Invariants

- every admin-visible setting key maps to exactly one human-owned schema row for
  settings-page semantics
- upstream native option/default truth remains upstream-native and is only
  adapted at schema boundary
- settings page sections/cards/groups/filters are derived projections, not
  second manual owner registries
- app consumes one authoritative derived page contract rather than rebuilding
  independent settings-page structures inline
- browser-native attrs and server coercion/validation stay symmetric for the
  same key
- declared schema defaults stay immutable across environments and process
  startup order
- `declared_default`, `baseline_default`, `saved_override`, and
  `effective_value` remain distinct concepts
- compatibility alias and hidden-deprecated handling stays boundary-local and
  explicit

## Acceptance Criteria

1. `SETTINGS_SCHEMA` row metadata is sufficient to derive all active settings
   page structure and settings selection helpers, while upstream native
   option/default truth remains upstream-owned and only boundary-adapted.
2. `src/fitcv_cp/app.py` consumes one schema-owned page contract and no longer
   owns independent settings-domain/section/group/filter meaning.
3. browser-native attrs and server validation derive from same schema-owned
   contract.
4. declared defaults are immutable; runtime default hydration is explicit; the
   four default-value states are testable and distinct.
5. metadata-only / hidden-deprecated / editable write rules are enforced from
   one owner contract and remain backward-compatible only where intentionally
   allowlisted.
6. runtime-env note behavior, if preserved, stays limited to current temporary
   presentation fields and does not become second owner for page semantics.

## Non-Goals

- no routing/env authority redesign; that stays in Phase 4
- no new settings micro-framework or second registry layer
- no broad visual redesign of `settings.html`
- no renaming of public settings keys or run export payloads except existing
  canonical compatibility behavior already approved
- no backend-interface cleanup or SQLite-path normalization beyond settings
  boundary consumers directly touched here

## Risks and Mitigations

- risk: row metadata expansion becomes second DSL harder to maintain than
  current constants
  - mitigation: add only fields needed to remove existing parallel owners; do
    not generalize beyond live page/runtime requirements
- risk: removing manual registries breaks save-group or card layout behavior
  - mitigation: keep golden app tests for rendered sections/cards and grouped
    save behavior
- risk: default-overlay change surprises callers depending on mutated schema
  - mitigation: explicit overlay helper remains stable and app/store tests prove
    effective default behavior
- risk: compatibility key handling leaks into route/template edge cases
  - mitigation: centralize alias and hidden-deprecated write rules; add focused
    store/app regression tests

## Validation Plan

- proof target: one settings owner exists
  - method: repo search + unit tests
  - evidence:
    - `tests/test_fitcv_cp/test_settings_schema.py`
    - absence or generated-only treatment of handwritten grouping registries

- proof target: one authoritative derived page contract exists
  - method: schema tests + app tests + repo search
  - evidence:
    - `tests/test_fitcv_cp/test_settings_schema.py`
    - `tests/test_fitcv_cp/test_app.py`
    - absence of inline page-structure registry ownership in
      `src/fitcv_cp/app.py`

- proof target: app boundary no longer owns semantic settings grouping
  - method: repo search + app tests
  - evidence:
    - `tests/test_fitcv_cp/test_app.py`
    - absence of `_decision_domain_for_entry` and inline section/group/filter
      registries in `src/fitcv_cp/app.py`

- proof target: native-form symmetry is real
  - method: app tests + schema tests
  - evidence:
    - schema attr tests in `tests/test_fitcv_cp/test_settings_schema.py`
    - rendered settings-page assertions in `tests/test_fitcv_cp/test_app.py`

- proof target: default-overlay contract is explicit and stable
  - method: schema/store tests
  - evidence:
    - overlay/default tests in `tests/test_fitcv_cp/test_settings_schema.py`
    - read/write persistence tests in `tests/test_fitcv_cp/test_settings_store.py`
      and `tests/test_fitcv_cp/test_settings_store_sqlite.py`

- proof target: runtime-env note exception stays bounded
  - method: source inspection + app tests
  - evidence:
    - no new settings grouping/editability/save-scope ownership added under
      `_resolve_mode_summary()` path in `src/fitcv_cp/app.py`
    - `tests/test_fitcv_cp/test_app.py` covers preserved note fields if note is
      still rendered

- proof target: scope stays bounded to Phase 3
  - method: grep + focused pytest set
  - evidence:
    - no opportunistic routing/env-resolver redesign in touched files
    - focused settings-related tests pass without reopening Phase 4 concerns

## Verification

- `rg -n "^RANKING_GROUPS:|^SETTINGS_SECTIONS:|^AGENTIC_SETTINGS_SECTIONS:|^CV_GROUPS:|^_EDITABLE_KEYS:|^_HIDDEN_DEPRECATED_KEYS:" src/fitcv_cp/settings_schema.py`
- `rg -n "def _decision_domain_for_entry|settings_page_task_sections = \[|decision_tabs = \[|decision_domain_filters = \[" src/fitcv_cp/app.py`
- `py -3 -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py -q`
- `py -3 scripts/generate_planning_lineage.py`
- `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. settings-system owner contract is explicit in code and updated docs
3. later Phase 4 routing work remains smaller because settings page no longer
   owns semantic settings meaning
4. downstream implementation plan can execute without reopening owner questions

Canonical source-of-truth:

- `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
- `docs/features/settings_system/feature.source.yaml`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
