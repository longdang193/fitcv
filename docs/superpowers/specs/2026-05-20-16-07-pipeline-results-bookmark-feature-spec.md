---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: pipeline-results-bookmark-stars-and-saved-jobs-page
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/routes
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
related_features: []
related_stages: []
---

## Goal

Define bounded product behavior and UI contract for job bookmarking from `Pipeline Results`, plus dedicated saved-bookmarks page that persists across runs.

## Key Deliverables

### Deliverable 1: Pipeline Results bookmark star action

Each row under `Generated Outputs` in run detail renders bookmark star control aligned with current row actions. Star supports save and unsave without leaving page.

### Deliverable 2: Cross-run persistent bookmark store

Bookmarks persist across app restarts/runs using stable job identity key, including minimum snapshot metadata required to render bookmark list when source run/job payload is unavailable.

### Deliverable 3: Dedicated bookmarks page

New page lists all bookmarked jobs across runs with filter/sort and quick navigation to source job URL and/or run detail context.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current run-detail output-row structure and existing job action surfaces before adding new interaction

**Steps:**
- [ ] inspect `src/fitcv_cp/templates/run_detail.html` `Pipeline Results` block and action-column layout
- [ ] inspect current persistence surface in `src/fitcv_cp/settings_store.py` (or adjacent store) for bookmark fit
- [ ] inspect route surface for admin/run-detail pages and nav entrypoint for bookmarks page
- [ ] map existing tests asserting pipeline results structure and output actions

**Verification:**
- [ ] current-state row/action contract documented with exact insertion point for star control

**Exit Criteria:**
- no design step depends on hidden assumptions about row identity or persistence scope

### Wave 2: Decision closure

**Purpose:**
- resolve bookmark identity, persistence schema, and UI behavior for list/detail surfaces

**Steps:**
- [ ] finalize bookmark identity strategy (`job_id` preferred, deterministic fallback key when absent)
- [ ] finalize persistence schema (`saved_at`, title/company/location/url, run_id/source, optional snapshot_json)
- [ ] finalize row-level UX states (empty star, filled star, optimistic toggle, error state)
- [ ] finalize dedicated page IA and sort/filter defaults
- [ ] finalize duplication policy (idempotent save)

**Verification:**
- [ ] each decision includes alternatives and impact on template, route, and tests

**Exit Criteria:**
- implementation can proceed without unresolved behavior questions

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations explicit for persistence, UX stability, and regression safety

**Steps:**
- [ ] define tests for star rendering and toggle behavior in Pipeline Results
- [ ] define tests for persistence across restarts/runs
- [ ] define tests for bookmarks page ordering/filter behavior and empty state
- [ ] define migration/backfill expectations (none vs lightweight)

**Verification:**
- [ ] each invariant has direct proof target and evidence output

**Exit Criteria:**
- spec is approval-ready and can hand off to implementation plan

## Design Decisions

### Decision: Place bookmark star in Pipeline Results row action cluster

- context: user requests bookmarking at moment of evaluating generated output job fit; current row already exposes output actions.
- choice: add star control within each `Generated Outputs` row in `Pipeline Results`, right-aligned with existing row actions.
- alternatives considered:
  - star only on job detail page
  - star only on dedicated bookmarks page
- impact:
  - lowest interaction friction during run review
  - requires row identity exposure and action endpoint wiring in run-detail surface

### Decision: Use persistent app-local store with idempotent upsert semantics

- context: bookmarks must survive across runs and restarts without requiring immediate multi-user backend redesign.
- choice: persist bookmarks in existing local persistence surface with unique identity key and upsert behavior.
- alternatives considered:
  - session-only in-memory state
  - full account-bound remote service first
- impact:
  - fast delivery, stable offline/local behavior
  - schema must capture minimal snapshot to avoid broken list rows when source data moves

### Decision: Create dedicated bookmarks page with stable default ordering

- context: user requests one dedicated page showing saved jobs across runs.
- choice: add page listing bookmarks sorted by `saved_at desc`, with text search and remove action.
- alternatives considered:
  - embed list only inside run detail
  - defer dedicated page until later milestone
- impact:
  - fulfills cross-run discoverability requirement
  - adds navigation and route/test surface

### Decision: Preserve symmetry of bookmark actions across surfaces

- context: inconsistent save/remove interactions across list/detail pages create drift.
- choice: same state model and icon semantics wherever bookmark appears (Pipeline Results, later job detail/bookmarks list).
- alternatives considered:
  - page-specific action variants
- impact:
  - simpler mental model
  - reusable rendering/action helper boundary encouraged

## Invariants

- Invariant 1: Bookmark identity is deterministic and idempotent; repeated save does not create duplicates.
- Invariant 2: Bookmark persistence survives process restart and subsequent runs.
- Invariant 3: Pipeline Results row rendering remains intact; bookmark star addition must not hide or regress existing download/link actions.
- Invariant 4: Dedicated bookmarks page always renders from persisted store even if original run payload is unavailable.
- Invariant 5: Unsave action removes bookmark consistently from both row state and bookmarks page view.

## Acceptance Criteria

1. Each `Generated Outputs` row in `Pipeline Results` shows bookmark star with clear saved/unsaved visual state.
2. Clicking unsaved star persists bookmark and updates row state without page reload.
3. Clicking saved star removes bookmark and updates row state without page reload.
4. Bookmarked jobs remain visible on dedicated bookmarks page after app restart.
5. Dedicated bookmarks page shows all bookmarks across runs sorted newest first by default.
6. Existing Pipeline Results actions (`Download Markdown`, job link) remain available and behaviorally unchanged.

## Non-Goals

- Multi-user shared bookmarks or RBAC.
- External sync (cloud account/device sync).
- Full job-tracking workflow states (`applied`, `interviewing`) in this phase.
- Major run-detail layout redesign outside action-cluster extension.

## Risks and Mitigations

- Risk: missing/unstable job identity in some output rows causes duplicate entries.
  - Mitigation: define deterministic fallback key and test edge cases.
- Risk: row-action crowding reduces usability on narrow screens.
  - Mitigation: responsive action layout rule + mobile snapshot tests/manual QA.
- Risk: stale source links or deleted upstream jobs reduce bookmark usefulness.
  - Mitigation: persist snapshot fields (title/company/location/url) at save time.
- Risk: regression in existing run-detail tests due changed DOM structure.
  - Mitigation: update/add focused tests for both old actions and new star state markers.

## Validation Plan

- proof target: bookmark star appears in Pipeline Results row set
  - method: template/response inspection tests on run detail HTML
  - evidence: passing assertions in run-detail output-availability tests

- proof target: save/remove behavior is idempotent and persistent
  - method: unit/integration tests over bookmark store API and action endpoints
  - evidence: tests showing no duplicate rows and expected remove semantics

- proof target: cross-run page shows persisted bookmarks after restart
  - method: integration-style test with persisted store fixture and page render
  - evidence: bookmarks page response contains expected items after reload cycle

- proof target: legacy row actions remain intact
  - method: regression assertions for download link/job link presence and order constraints where required
  - evidence: existing and updated run-detail tests pass

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

## Triage Block

Layer: change  
Feature type: ADD  
Summary: Add bookmark-star action to run-detail Pipeline Results rows and dedicated persisted bookmarks page across runs.  
Reasoning: Bounded product behavior addition in existing run-detail/job-output interaction surface; no intent or operating-system governance change.  
Invariants:
- idempotent bookmark identity
- persistence across restart/runs
- no regression of existing Pipeline Results actions
Dependencies:
- run-detail template row identity fields
- bookmark persistence store abstraction
- route/navigation surface for bookmarks page
Affected stages:
- none
Affected features:
- none
Primary lens: cross-cutting
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- feature_docs:
  - none
- cross_cutting_docs:
  - docs/superpowers/specs/2026-05-20-16-07-pipeline-results-bookmark-feature-spec.md
- readme: none
- generated:
  - none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes
