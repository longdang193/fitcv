---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: settings-page-v2-progressive-disclosure
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
related_features:
  - settings_system
  - cv_system
related_stages:
  - cv_generation
---

## Goal

Define a V2 Settings page architecture that reduces visual clutter and navigation cost by combining domain-based information architecture, stage-based filtering, progressive disclosure, and explicit inherited-vs-override state presentation.

## Key Deliverables

### Deliverable 1: V2 information architecture contract

One canonical IA model that groups settings by domain/layer (`General`, `Layers`, `Stages`, `Rules`, `Integrations`, `Advanced`) and supports workflow-stage filtering (`Setup`, `Draft`, `Review`, `Approved`, `Archived`) without duplicating setting ownership.

### Deliverable 2: Progressive disclosure interaction contract

A three-level interaction model that keeps the default page compact and only exposes deep editing controls contextually.

### Deliverable 3: Effective-value and override visibility contract

A consistent representation for `Effective value`, `Inherited/default source`, and `Override state`, with override controls hidden until explicitly enabled.

### Deliverable 4: Safety and diagnostics contract

Built-in search/filtering, modified/error/override indicators, and separation of destructive/rare controls into `Advanced` + `Danger Zone`.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- baseline current settings clutter causes and map existing key surfaces into V2 taxonomy

**Steps:**
- [ ] inventory current settings groups/cards/rows and identify repeated or dense blocks
- [ ] map every existing settings key to one domain and one or more workflow stages
- [ ] identify keys that are default-only, metadata-only, override-eligible, high-risk, or destructive
- [ ] define migration constraints so key names, config paths, and backend validation remain unchanged

**Verification:**
- [ ] full key inventory is mapped to V2 taxonomy with no orphan keys

**Exit Criteria:**
- V2 IA decisions rely on explicit mapping evidence, not ad-hoc layout preference

### Wave 2: Decision closure

**Purpose:**
- finalize V2 page structure and editing model

**Steps:**
- [ ] define page shell: left domain navigation, top filter/search rail, compact summary area, contextual editor surface
- [ ] define progressive disclosure levels (summary row -> inline expand -> side drawer)
- [ ] define rule for explanation density (default compact, tooltip/help/learn-more for long text)
- [ ] define state chips/badges for modified/error/override/default/inherited
- [ ] define placement and confirmation behavior for Advanced/Danger Zone settings

**Verification:**
- [ ] each major usability complaint from current page maps to a concrete V2 design response

**Exit Criteria:**
- V2 design is coherent, MECE, and operationally safe

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof obligations and rollout boundaries explicit before implementation plan

**Steps:**
- [ ] define acceptance criteria for scanability, discoverability, and editing safety
- [ ] define regression constraints for backend payload/validation invariance
- [ ] define incremental rollout gates and parity checks against current page behavior

**Verification:**
- [ ] validation plan can prove UX improvements without contract regressions

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: Two-axis navigation (domain + workflow stage)

- context: single-axis long-form grouping causes high scroll depth and low findability
- choice: use domain/layer as primary navigation and workflow stage as secondary filter
- alternatives considered:
  - single-axis domain-only layout
  - single-axis stage-only layout
- impact:
  - improves discoverability for both policy intent and execution timing
  - avoids duplicating settings across multiple pages

### Decision: Progressive disclosure as default interaction model

- context: showing full controls for every setting at once creates clutter and cognitive overload
- choice: default to compact summary rows, expand inline for common edits, open side drawer for complex edits
- alternatives considered:
  - always-expanded card model
  - modal-only editing model
- impact:
  - preserves scanability while keeping advanced context reachable

### Decision: Effective-value-first rendering with explicit override activation

- context: users misread inherited defaults as active overrides and vice versa
- choice: show effective value + source first; hide override controls until `Enable override` action
- alternatives considered:
  - always-visible editable fields
- impact:
  - reduces accidental edits and ambiguity around active runtime behavior

### Decision: Separate high-risk/destructive controls into Advanced and Danger Zone

- context: rare/high-impact settings mixed with common controls increases risk and noise
- choice: isolate risky controls, require stronger confirmation and clearer warnings
- alternatives considered:
  - leave risky controls in domain sections with only text warnings
- impact:
  - lowers accidental destructive actions and keeps common workflows cleaner

### Decision: Explanatory content policy uses contextual help over inline prose

- context: dense explanatory text reduces scanning speed and obscures action controls
- choice: keep row-level explanations concise; move long guidance to tooltips/help/learn-more expanders
- alternatives considered:
  - keep full prose inline per row
- impact:
  - improves readability and shortens visible page length

## Invariants

- Existing settings keys and `config_path` persistence contracts remain unchanged.
- Backend validation remains source of truth; UI checks can preflight but cannot replace server validation.
- Every setting key belongs to exactly one primary domain and at least one discoverable filter path.
- Effective/inherited/override state must be visible wherever edits are possible.
- Advanced/Danger settings remain isolated from default high-frequency configuration surfaces.
- V2 layout must support search and filtering without requiring full-page expansion.

## Acceptance Criteria

- Users can find any setting via either domain navigation or stage filter within at most two interaction steps from page load.
- Default page load does not render all setting controls expanded.
- Each setting row/card shows effective value and source (`Inherited` or `Override`) before deep edit interaction.
- Override controls remain hidden until explicit user action enables overrides for that setting/section.
- Long explanations are not rendered as full inline blocks by default.
- `Modified`, `Error`, and `Override` indicators are visible at row, section, and summary level.
- Destructive/rare settings are only exposed under `Advanced` or `Danger Zone` sections.

## Non-Goals

- No renaming/removal of current settings keys in this specification.
- No backend policy rewrite for scoring, filtering, or CV generation logic.
- No redesign of non-settings admin pages.
- No storage-engine migration or orchestration redesign in this spec.

## Risks and Mitigations

- Risk: taxonomy drift between schema and UI causes orphan or duplicated settings.
  - Mitigation: enforce key-to-domain/stage mapping coverage tests and fail on missing mappings.
- Risk: progressive disclosure hides critical controls too deeply.
  - Mitigation: keep strong search/filter and show summary indicators that reveal hidden modified/error state.
- Risk: preflight UI checks diverge from backend validation.
  - Mitigation: treat backend as canonical; mirror only known invariants and verify parity in tests.
- Risk: migration from V1 to V2 introduces temporary operator confusion.
  - Mitigation: phased rollout with parity mode and concise in-product migration hints.

## Validation Plan

- proof target: all settings keys are discoverable in V2 IA
  - method: mapping inspection + automated key coverage assertions
  - evidence: test output proving one-to-one domain assignment and valid stage tags for each key
- proof target: default view reduces clutter by design
  - method: template/context inspection for collapsed-by-default sections and summary-first rendering
  - evidence: rendered HTML assertions showing progressive disclosure controls and non-expanded default state
- proof target: effective/inherited/override clarity is explicit
  - method: UI rendering tests across default and overridden scenarios
  - evidence: assertions for effective value, source badges, and hidden-until-enabled override controls
- proof target: backend contract invariance is preserved
  - method: settings post/save regression tests with valid/invalid payloads
  - evidence: unchanged save endpoints behavior and server-side validation outcomes
- proof target: high-risk controls are isolated and guarded
  - method: UI placement + confirmation/preflight behavior tests
  - evidence: assertions for Advanced/Danger placement and guardrail prompts

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
