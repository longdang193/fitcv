---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: run-detail-overview-progressive-disclosure-ssot
author: codex
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/run_detail_tab_profile.html
  - src/fitcv_cp/templates/run_detail_tab_enriched.html
  - src/fitcv_cp/templates/run_detail_tab_jobs_input.html
  - src/fitcv_cp/templates/synonym_promote_preview.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/run_artifact_mirror.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - docs/usage.md
related_features:
  - run_lifecycle_controls
  - trigger_run_management
  - settings_system
related_stages:
  - cv_generation
---

## Goal

Define run-detail UX redesign that minimizes cognitive load while preserving full auditability and debugging access. Enforce SSOT, symmetry, invariance, and equivalence so overview, workflow pages, and diagnostics remain drift-resistant and low-maintenance.

## Triage

Layer: change
Feature type: MODIFY
Summary: Restructure run detail into decision-first overview plus progressive disclosure and task-separated workflows.
Reasoning: Existing long-form page mixes operator decision surfaces with deep technical evidence, increasing scan time and maintenance drift.
Invariants:
- Same run truth must project consistently across overview, workflow pages, and diagnostics.
- Non-default/effective settings must be computed from canonical defaults + run overrides only.
- Hidden diagnostic data must remain accessible through deterministic deep links.
Dependencies:
- Existing run JSON and stage artifact contracts
- Existing synonym proposal and artifact routes
Affected stages:
- cv_generation
Affected features:
- run_lifecycle_controls
- trigger_run_management
- settings_system
Primary lens: mixed
Affected docs:
  feature_source: none
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs:
    - docs/usage.md
  cross_cutting_docs:
    - docs/operating_system/planning/planning-dispatch.md
  readme: none
  generated:
    - none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: Decision-first run overview contract

One canonical overview that answers three operator questions first: run outcome, immediate risk/warnings, next action.

### Deliverable 2: Progressive disclosure and field-tier contract

One canonical field-classification system (`core`, `advanced`, `diagnostic`) with deterministic visibility behavior.

### Deliverable 3: Task-workflow separation contract

Dedicated surfaces for task-heavy workflows (synonym proposal review, artifact browsing) with lightweight links from overview.

### Deliverable 4: Equivalence-proof observability contract

Cross-surface assertions proving counts, statuses, and effective settings are semantically equivalent projections of one source.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- baseline current run-detail information density and classify every rendered field by decision value

**Steps:**
- [ ] inventory all run-detail fields/cards/tables currently rendered in `run_detail.html` and partial tabs
- [ ] classify each field as `core`, `advanced`, or `diagnostic` using decision-value rubric
- [ ] map existing routes/data providers for synonym review and artifacts to assess extraction effort
- [ ] identify duplicated/computed-in-template values likely to violate SSOT/equivalence

**Verification:**
- [ ] field matrix complete with no orphan field and no unresolved owner

**Exit Criteria:**
- no redesign decision depends on implicit field ownership or unverified data source

### Wave 2: Decision closure

**Purpose:**
- finalize IA, disclosure behaviors, and workflow boundaries

**Steps:**
- [ ] lock top-level IA: `Overview`, `Synonym Review`, `Artifacts`, `Diagnostics`
- [ ] define overview card grammar: `Outcome`, `Warnings`, `Next Actions`, `Stage Snapshot`, `Effective Settings`
- [ ] define tooltip policy for short glossary-only terms
- [ ] define collapsible advanced panels and diagnostics gating behavior
- [ ] define registry-driven field metadata schema (tier, owner surface, explanation mode)

**Verification:**
- [ ] every major current pain point maps to one explicit decision in spec

**Exit Criteria:**
- architecture bounded, symmetric, and implementation-plan ready

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof that simplification improves usability without losing audit/debug truth

**Steps:**
- [ ] define invariance/equivalence assertions for status, counts, settings delta, and stage state
- [ ] define tests for hidden-by-default diagnostics with guaranteed discoverability
- [ ] define acceptance metrics for reduced cognitive load (scroll depth, first-decision latency)
- [ ] define migration guardrails to avoid route fragmentation

**Verification:**
- [ ] validation plan can fail implementation if any cross-surface truth drift appears

**Exit Criteria:**
- spec approved for plan drafting

## Design Decisions

### Decision: Split run detail into decision surface and evidence surface

- context: one long page currently mixes decisions, workflows, and diagnostics
- choice: make `Overview` decision-first; move heavy evidence to dedicated surfaces
- alternatives considered:
  - keep single page and add more collapses
  - tab everything including core signals
- impact:
  - faster operator decisions
  - lower cognitive load
  - preserves audit access via links, not inline clutter

### Decision: Registry-driven field classification as SSOT for visibility

- context: manual per-template visibility causes drift and inconsistent behavior
- choice: define one field registry with metadata: `tier`, `surface_owner`, `tooltip_text`, `collapse_group`, `source_key`
- alternatives considered:
  - hand-coded card-specific visibility rules
- impact:
  - symmetry by construction
  - lower maintenance effort
  - easier extension with predictable behavior

### Decision: Dedicated task pages for synonym review and artifact browsing

- context: these flows are action-heavy and overwhelm run overview
- choice: keep only concise status + CTA on overview; move full workflow UI to dedicated pages
- alternatives considered:
  - inline workflow blocks with pagination
- impact:
  - overview remains task-focused
  - workflows gain room for focused controls and bulk actions

### Decision: Diagnostics gate for fingerprints/hashes/raw payload/logs/internal IDs

- context: high-volume low-frequency technical data currently competes with operator actions
- choice: hide by default under `Diagnostics` (or `Advanced diagnostics` collapse), accessible by deterministic deep links
- alternatives considered:
  - expose all with stronger visual hierarchy
- impact:
  - major clutter reduction
  - no loss of debugging/audit capability

### Decision: Effective-settings delta only on overview

- context: defaults and unused settings dilute summary signal
- choice: show only settings that affected run result; full settings available behind expand or settings page
- alternatives considered:
  - display all settings always
- impact:
  - better signal-to-noise
  - aligns with equivalence principle through deterministic delta computation

### Decision: Tooltip scope limited to short glossary terms

- context: tooltips overloaded with long prose become hidden documentation
- choice: use tooltips only for short terms (`confidence score`, `triage mode`, `suppressed`, `alias conflict`, `run-scoped overlay`)
- alternatives considered:
  - long explanatory tooltip strategy
- impact:
  - faster comprehension
  - less documentation drift

## Invariants

- Canonical run object remains single source of truth for all rendered run state.
- Overview status must equal timeline status and diagnostics status for same run.
- Overview warning/error counts must equal diagnostics query counts.
- Effective settings on overview must equal deterministic `defaults XOR overrides actually used` result.
- Field tier assignment is global and symmetric across run pages; same field cannot be `core` on one run and `diagnostic` on another without registry change.
- Data hidden by default must remain reachable via deterministic route anchor/deep link.
- Workflow extraction must not duplicate business rules between overview and dedicated pages.

## Acceptance Criteria

- Main run overview shows only: status/outcome, top warnings/blockers, next actions, stage snapshot, effective settings delta.
- Fingerprints, hashes, raw payloads, raw logs, stack traces, internal IDs are hidden by default and available in diagnostics.
- Synonym proposal review has dedicated page/tab with full task controls; overview only shows summary + entry CTA.
- Artifact browsing has dedicated page/tab; overview shows only artifact availability summary.
- Unused/default settings are not shown in default overview state.
- Tooltip usage limited to short glossary terms; no long-form instructional tooltip content.
- Cross-surface equivalence tests pass for status, counts, and effective settings.
- Operator can reach any diagnostic record from overview via at most two clicks.

## Non-Goals

- Rewriting run processing pipeline or policy evaluation logic.
- Changing run artifact persistence/storage engine.
- Redesigning unrelated admin pages outside run detail and linked run workflows.
- Changing canonical schema of persisted run payloads in this spec.

## Risks and Mitigations

- Risk: over-pruning overview hides important context.
  - mitigation: keep explicit warning/blocker summary and add quick-link to exact diagnostics records.
- Risk: split pages create navigation friction.
  - mitigation: stable top-level tabs and contextual CTA links from overview cards.
- Risk: field registry drift from templates.
  - mitigation: tests asserting each rendered field has one registry entry and valid tier/surface mapping.
- Risk: equivalence break between overview and diagnostics counts.
  - mitigation: shared query helpers + invariance tests in run-detail suite.
- Risk: historical run payload shape variance breaks effective-settings delta logic.
  - mitigation: compatibility normalization layer with explicit fallback behavior tests.

## Validation Plan

- proof target: overview reduced to decision-first content
  - method: template inspection + rendering tests for card presence/absence by default state
  - evidence: test snapshots show only core cards visible on initial load

- proof target: diagnostics are hidden by default but discoverable
  - method: UI interaction tests for collapses/routes/deep links
  - evidence: tests verify no diagnostic raw fields on initial load and successful navigation to each diagnostic category

- proof target: equivalence across surfaces
  - method: run fixture comparison tests between overview summary values and diagnostics source tables
  - evidence: assertions for equal status, warning/error counts, and stage states

- proof target: effective-settings SSOT invariance
  - method: deterministic fixtures with known defaults/overrides/usage flags
  - evidence: overview effective-settings list exactly equals computed delta output

- proof target: task workflow separation integrity
  - method: route tests and template assertions for synonym/artifact workflow extraction
  - evidence: overview includes summary CTA only; full controls render on dedicated pages

- proof target: symmetry of tier behavior
  - method: registry contract tests validating tier, owner, and explanation mode constraints
  - evidence: failing test when field appears in unauthorized tier/surface

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
