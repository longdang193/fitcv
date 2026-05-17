---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: pipeline-settings-decision-focused-ia-v4
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
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define decision-first Pipeline Settings information architecture that minimizes operator friction by showing only next meaningful decision while preserving backend contract behavior.

## Key Deliverables

### Deliverable 1: SSOT decision-state classifier contract

One canonical per-setting classifier computes decision status (`needs_review`, `recommended`, `configured`, hidden-default, hidden-unused) from stable rule inputs, and all UI groups/actions derive from this classifier.

### Deliverable 2: MECE decision group contract

Default IA groups settings by decision urgency with mutual exclusivity and complete coverage: `Needs Review`, `Recommended`, `Configured`, `Advanced`, plus diagnostic projection `All`.

### Deliverable 3: Symmetry and equivalence interaction contract

All groups use symmetric row structure, badge semantics, and action grammar so equivalent state means equivalent interaction regardless of tab/view shape.

### Deliverable 4: Progressive disclosure razor contract

High-friction low-value details (defaults, unused, advanced internals) are hidden by default and exposed only through explicit user toggles or advanced expansion.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- define current settings-surface behavior and identify mismatch between decision urgency and current flat rendering

**Steps:**
- [ ] inventory current settings metadata available in schema/context for requirement, recommendation confidence, defaults, and advanced flags
- [ ] map current sections to decision intent and identify overlap/non-MECE collisions
- [ ] identify fields currently always-visible that qualify as hide-by-default under razor policy
- [ ] define canonical reason-code taxonomy for review/recommendation states

**Verification:**
- [ ] mapping table covers all rendered settings without orphan state

**Exit Criteria:**
- no downstream design decision depends on undocumented status logic

### Wave 2: Decision closure

**Purpose:**
- finalize V4 decision-first IA, grouping rules, and operator actions

**Steps:**
- [ ] define deterministic classifier precedence for per-setting decision status
- [ ] define group membership and sort order for `Needs Review`, `Recommended`, `Configured`, `Advanced`, `All`
- [ ] define top-of-page summary metrics and primary action set
- [ ] define tooltip vs advanced-detail boundary policy
- [ ] define hidden-default and hidden-unused toggle behavior

**Verification:**
- [ ] every setting state maps to exactly one primary decision group before projection views

**Exit Criteria:**
- grouping, actions, and disclosure policy satisfy SSOT, symmetry, invariance, equivalence, and MECE

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof obligations that demonstrate improved decision throughput without behavior regression

**Steps:**
- [ ] define UI/state assertions for classifier invariance and MECE partitioning
- [ ] define action-equivalence checks (`Accept Recommended` equals applying all recommended deltas)
- [ ] define regression checks for settings persistence/validation behavior
- [ ] define discoverability checks for unresolved items and high-risk controls

**Verification:**
- [ ] validation plan proves decision-first UX gain and backend invariance

**Exit Criteria:**
- spec is implementation-planning ready

## Design Decisions

### Decision: Adopt decision-first default IA (`Needs Review` as landing view)

- context: current long single-page layout forces users to parse equal-weight settings and slows next-action choice
- choice: default to `Needs Review` queue with severity-ordered unresolved decisions
- alternatives considered:
  - keep flat `All` default with better copy only
  - keep `All / General / Advanced` taxonomy
- impact:
  - first screen answers "what must I decide now"
  - reduces scan cost and missed blocking items

### Decision: Use dual-layer IA with decision-first tabs and domain filters

- context: operators need both urgency-first triage and domain-level orientation; making both top-level creates mixed-axis ambiguity
- choice:
  - primary axis (tabs, MECE): `Needs Review` (default), `Recommended`, `Configured`, `Advanced`, `All`
  - secondary axis (filters inside primary tabs): `Domain & Taxonomy`, `Extraction Rules`, `Synonym Review`, `Output & Artifacts`
  - `Overview` remains a header-level readiness panel, not a primary tab
- alternatives considered:
  - top-level mixed tabs (`Overview`, `Needs Review`, `Domain`, `Extraction`, `Output`, `Advanced`)
  - topic-first primary tabs with decision badges
- impact:
  - preserves SSOT status model and invariance
  - preserves user mental model for domain navigation without status duplication

### Decision: Replace topic-first tabs with SSOT decision groups

- context: topic grouping causes cross-section ambiguity where same urgency appears in many places
- choice: primary tabs are decision buckets only; domain appears as secondary filters inside each bucket
- alternatives considered:
  - `All / General / Advanced`
  - two-axis filter model as primary navigation
- impact:
  - MECE grouping on urgency
  - direct mapping from status to action

### Decision: Enforce deterministic classifier precedence for invariance

- context: ad-hoc UI branching can produce inconsistent status assignment across render paths
- choice: apply fixed precedence chain for status evaluation:
  1. missing required, conflict, high risk, low confidence => `Needs Review`
  2. safe recommendation delta => `Recommended`
  3. explicitly advanced => `Advanced`
  4. otherwise resolved => `Configured`
  hidden overlays: default-equal and unused visibility controlled by toggles, not status mutation
- reason codes (canonical):
  - `missing_required`
  - `conflict`
  - `low_confidence`
  - `quality_risk`
  - `changed_from_default`
  - `recommended_delta`
  - `advanced_only`
  - `unused`
- tie-break precedence:
  - blocking > warning > recommendation > configured > hidden overlays
- alternatives considered:
  - manual status tags in template blocks
  - per-tab custom inclusion predicates
- impact:
  - invariance across UI surfaces
  - no double-entry truth for status logic

### Decision: Split short guidance (tooltip) from deep rationale (advanced collapsible)

- context: always-expanded long prose creates vertical noise and hides urgent controls
- choice: keep micro-guidance in tooltips; move tradeoffs/dependencies/raw config to collapsible advanced details
- alternatives considered:
  - keep all prose inline
  - move all help to external docs
- impact:
  - improved scannability with local comprehension preserved

### Decision: Add top action bar aligned to decision states

- context: current actions are scattered and not aligned to priority queue semantics
- choice: sticky top actions: `Review Next Issue`, `Accept Recommended`, `Run Validation`, `Save Changes`
- alternatives considered:
  - keep only Save/Reset
  - add many context actions per section only
- impact:
  - consistent flow from unresolved to accepted to validated

### Decision: Keep readiness `Overview` as summary panel only

- context: overview value is quick orientation, not full decision workspace
- choice: render readiness panel above tabs with counts, next-step guidance, and primary CTAs:
  - `Review Required Settings`
  - `Accept Recommended Settings`
  - `Run Pipeline`
- alternatives considered:
  - make `Overview` a full top-level tab
  - remove overview surface entirely
- impact:
  - preserves fast orientation without mixed-axis primary navigation
  - keeps default work area anchored on actionable decision buckets

## Invariants

- Backend settings keys, persistence payload contracts, and validation behavior remain unchanged.
- Every setting resolves to exactly one primary decision status from one canonical classifier.
- Grouping logic is SSOT-owned by classifier output; templates cannot invent alternate status semantics.
- Equivalent setting state must render equivalent badge semantics and action affordances across tabs/views.
- `Needs Review` must include all blocking or risky unresolved decisions.
- Hidden-by-default settings remain reachable through explicit toggles or `All` view.
- High-risk controls remain clearly labeled and never auto-applied by bulk recommendation action.
- Each setting ID appears in exactly one primary decision bucket at a time.
- Domain membership labels are secondary filters only and cannot override primary decision status.
- `All` is projection surface over classifier output, not separate status taxonomy.

## Acceptance Criteria

- Landing page opens to `Needs Review` and shows only unresolved decision items by default.
- `Accept Recommended` applies only settings classified as `Recommended` and does not change `Needs Review` items.
- Any setting appears in one primary decision tab only (MECE), excluding deliberate projection in `All`.
- Default-equal and unused settings are hidden in primary decision tabs unless user enables visibility toggles.
- Tooltip content is concise (purpose, valid range, default, one-line impact); deeper rationale lives in advanced expandable section.
- Symmetric row layout and action labels are consistent across all primary decision tabs.
- Domain filter selection changes visibility scope only; it does not mutate status classification.
- `Recommended` excludes settings carrying blocking or warning reason codes.
- `Needs Review` item ordering is deterministic: blocking, warning, quality risk, changed-from-default.
- Overview panel shows readiness counts and next recommended action without exposing raw settings controls.

## Non-Goals

- No migration of backend settings schema key names or persisted config format.
- No runtime pipeline stage taxonomy redesign.
- No replacement of server-side validation with client-only validation.
- No expansion of settings count or new domain capability introduction.
- No replacement of decision-first primary tabs with domain-first top-level navigation.
- No per-tab local status logic that diverges from SSOT classifier.
- No long-form logs, JSON payloads, hashes, or diagnostics inside tooltips.

## Risks and Mitigations

- risk: classifier misclassification hides important settings
  - mitigation: golden-fixture tests for representative setting states and reason-code coverage checks
- risk: operators lose access to familiar full-page mental model
  - mitigation: keep `All` tab with search/filter and one-click access from header
- risk: bulk accept applies unsafe changes
  - mitigation: classifier gating excludes high-risk/low-confidence items from `Recommended`
- risk: ambiguity between configured vs advanced states
  - mitigation: explicit advanced flag policy and stable badge copy in row metadata
- risk: dual-axis mental-model confusion (urgency vs domain)
  - mitigation: persistent helper text near filters: "Tabs show decision urgency; filters scope by domain."
- risk: hidden defaults/unused reduce operator trust
  - mitigation: always-visible counter chip `Hidden defaults/unused: N` with one-click reveal
- risk: bulk accept surprises due to implicit exclusions
  - mitigation: preview modal lists included/excluded settings with exclusion reason codes before apply

## Validation Plan

- proof target: SSOT classifier determinism and invariance
  - method: unit tests over classifier precedence with fixed input fixtures
  - evidence: passing tests proving same input metadata yields same status across render paths
- proof target: MECE group partition
  - method: integration test asserting exactly-one primary tab membership per setting
  - evidence: automated membership assertions with zero overlap across primary groups
- proof target: equivalence of bulk action semantics
  - method: apply `Accept Recommended` in test harness and compare delta set to recommended subset
  - evidence: exact match between applied keys and classifier output for recommended items
- proof target: progressive disclosure behavior
  - method: template rendering and UI tests for hidden-default/hidden-unused toggles and advanced collapse behavior
  - evidence: DOM assertions showing default hidden state and explicit reveal controls
- proof target: backend behavior invariance
  - method: existing save/validation regression suite
  - evidence: unchanged pass/fail outcomes for valid/invalid payload scenarios
- proof target: cross-surface status equivalence
  - method: compare status-derived counts and labels across overview panel, tab rows, and API payload from same fixtures
  - evidence: exact parity assertions for counts, IDs, and reason codes
- proof target: domain-filter non-semantic behavior
  - method: switch domain filters and assert underlying status map unchanged
  - evidence: before/after classifier snapshot equivalence with visibility-only delta
- proof target: CTA correctness and safety gating
  - method: integration tests for enable/disable and outcome behavior of `Review Required Settings`, `Accept Recommended Settings`, and `Run Pipeline`
  - evidence: expected CTA availability and resulting state transitions across blocking/warning/ready scenarios

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
