---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: pipeline-settings-decision-first-categorization
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_app.py
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

Redesign Pipeline Settings information architecture so user can make next decision fast, while preserving full advanced/debug access. Enforce symmetric, invariant categorization across stages with `Basic | Advanced | All` as top complexity filter.

## Key Deliverables

### Deliverable 1: Decision-first settings IA contract

Define canonical page structure, filter model, and section/block naming contract that removes confusing surfaces and reduces duplicate/low-value guidance.

### Deliverable 2: Symmetric stage/block taxonomy

Define stage and sub-block categorization that keeps stable naming patterns across settings, including deeper decomposition for agentic controls.

### Deliverable 3: Observable UX acceptance contract

Define testable acceptance criteria, invariants, and validation evidence for implementation handoff.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish current settings surfaces and real schema keys before remapping

**Steps:**
- [ ] inventory current sections/cards/filters in `app.py` and `settings.html`
- [ ] inventory real setting keys and group registries in `settings_schema.py`
- [ ] identify duplicated, non-decision, or stale guidance blocks

**Verification:**
- [ ] old-to-new mapping references real keys/sections only

**Exit Criteria:**
- no proposed category depends on non-existent settings

### Wave 2: Decision closure

**Purpose:**
- finalize new IA, wording, and categorization contract

**Steps:**
- [ ] lock top-level filter contract (`Basic | Advanced | All`)
- [ ] lock filter dimensions (`Stage`, `Control Surface`)
- [ ] define stage and decision-area taxonomy with symmetry
- [ ] define old-to-new relocation map for settings and cards

**Verification:**
- [ ] each setting key has deterministic placement rule

**Exit Criteria:**
- categorization complete, non-overlapping, and implementation-ready

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof targets and completion boundaries for implementation

**Steps:**
- [ ] define acceptance criteria for layout, filter behavior, and discoverability
- [ ] define test updates and smoke validation checks
- [ ] define non-goals and deferred items

**Verification:**
- [ ] acceptance criteria are testable from rendered HTML/behavior

**Exit Criteria:**
- spec ready for implementation plan drafting

## Design Decisions

### Decision: Keep complexity selector fixed to `Basic | Advanced | All`

- context: user explicitly rejected alternative labels
- choice: retain exact labels and use as primary page view mode
- alternatives considered:
  - `Quick | Expert | Full`
  - status-only tabs (`Needs Review`, `Recommended`, `Configured`)
- impact:
  - consistent mental model for depth
  - separates complexity choice from status and stage scopes

### Decision: Remove non-decision top strips

- context: page currently front-loads explanatory/system strips that do not help next decision
- choice: remove from settings top area:
  - live provider/model/authority strip
  - run truth check block
  - run navigation CTA
- alternatives considered:
  - keep as collapsible banner
- impact:
  - reduces cognitive load
  - keeps settings page single-purpose (configure defaults)

### Decision: Use dual secondary filters `Stage` + `Control Surface`

- context: domain filter wording ambiguous for operators
- choice:
  - rename `Domain Filters` to `Stage`
  - add second filter axis `Control Surface`
- alternatives considered:
  - stage only
  - agent only
- impact:
  - `Stage` answers where in pipeline
  - `Control Surface` answers owning execution path

### Decision: Adopt symmetric decision-area vocabulary

- context: current block naming inconsistent and causes drift (mode/policy/advanced mixed)
- choice: standardized decision-area set:
  - `Enablement`
  - `Behavior`
  - `Quality Targets`
  - `Throughput`
  - `Automation`
  - `Safeguards`
  - `Diagnostics` (Advanced-only invariant)
- alternatives considered:
  - freeform names per stage
- impact:
  - stable operator scanning pattern
  - lower onboarding/interpretation cost

### Decision: Decompose `Agentic Controls` into sub-blocks

- context: current single block too large and semantically mixed
- choice:
  - split into:
    - `Enablement`
    - `Automation`
    - `Quality Targets`
    - `Throughput`
    - `Diagnostics` (Advanced)
- alternatives considered:
  - keep monolithic card
- impact:
  - improves edit locality
  - preserves advanced/debug surfaces without hiding business knobs

### Decision: Reclassify semantic weights/pool as non-advanced

- context: these are operator-tunable decision knobs, not internal diagnostics
- choice: move from `Advanced Agentic Tuning` into `Agentic Processing > Quality Targets/Throughput` within `Basic`
- alternatives considered:
  - keep all semantic controls under advanced
- impact:
  - better decision accessibility
  - less false “expert-only” labeling

## Invariants

- `Diagnostics` is always `Advanced`.
- Every setting key resolves to exactly one primary stage and one decision-area.
- `Basic | Advanced | All` labels remain unchanged.
- Top settings page contains no run-inspection guidance strips.
- `All` view remains complete and searchable.
- Filter chips are interactive controls (not static badges).
- No duplicated status metrics across multiple header blocks.

## Acceptance Criteria

1. Top area shows only page title + concise status line; no live runtime strip, no run truth block, no run CTA.
2. Complexity filter exists and works with exact labels: `Basic`, `Advanced`, `All`.
3. `Stage` filter exists and is clickable.
4. `Control Surface` filter exists and is clickable.
5. `Agentic Controls` no longer rendered as one monolithic card.
6. Semantic weight keys and `channel_pool_size` visible in `Basic` under agentic sub-blocks.
7. `cv_analysis.semantic_alignment.model` remains non-editable metadata/explanatory in advanced diagnostics.
8. In `Basic`, diagnostics-only rows are hidden.
9. In `All`, all settings keys remain discoverable via search.
10. Empty result state provides explicit filter-reset guidance.

## Non-Goals

- changing backend config semantics or default values
- changing run-detail observability pages
- introducing new runtime settings keys
- redesigning non-settings admin pages

## Risks and Mitigations

- risk: misclassification of keys into wrong stage
  - mitigation: maintain explicit key-to-stage map in code and test coverage for representative keys
- risk: filter interaction regressions hide too many rows
  - mitigation: add DOM behavior tests for each complexity mode and combined filter states
- risk: user confusion during transition from old labels
  - mitigation: short migration hint text near filters for one release

## Validation Plan

- proof target: top strip removal complete
  - method: template inspection + route render test
  - evidence: HTML lacks live provider/model/authority strings and run truth text

- proof target: complexity filter contract preserved
  - method: route render test + JS behavior check
  - evidence: chips with `Basic|Advanced|All` labels and active-state changes

- proof target: stage + control-surface filters functional
  - method: browser/manual smoke + DOM filter tests
  - evidence: each filter selection changes visible row subset deterministically

- proof target: agentic decomposition complete
  - method: section/card structure inspection + key placement assertions
  - evidence: separate agentic sub-blocks render with expected key groups

- proof target: semantic tuning promoted from advanced
  - method: render tests for key visibility in `Basic`
  - evidence: weight/pool keys visible in basic mode, diagnostics model key hidden unless advanced

## Completion Criteria

A specification item is complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
