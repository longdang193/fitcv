---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
targets:
  - docs/intent/workstreams/threads/workstream-operator-control-plane/02-operator-control-plane-run-detail-truth.md
  - src/fitcv_cp/app.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/templates/runs_list.html
  - docs/usage.md
  - docs/api.md
related_features:
  - inspection_debugging
  - trigger_run_management
related_stages: []
---

# Delete Archived Runs

## Summary

Add one explicit destructive admin action, `Delete archived runs`, to permanently
remove archived run history that operators no longer need.

This spec keeps archive and delete as separate lifecycle steps:

- `Archive` means hide but keep.
- `Delete archived runs` means permanently remove archived runs and their
  run-scoped stored artifacts.

The goal is operational cleanup without introducing a vague `Clear cache`
control or weakening run lifecycle truth.

## Triage

Layer: `change`
Feature type: `ADD`

Reasoning:

- this is a bounded operator-control-plane lifecycle extension
- it builds on existing archive/unarchive semantics instead of replacing them
- it touches destructive data removal, so the contract must be explicit before
  implementation

Invariants:

- archive remains reversible visibility state, not deletion
- delete applies only to already archived runs
- active, paused, queued, running, and non-archived terminal runs are never
  eligible
- delete removes run records and run-scoped artifacts together so operator
  truth does not point at missing backing data
- destructive actions require explicit operator confirmation

Dependencies:

- `docs/intent/workstreams/threads/workstream-operator-control-plane/02-operator-control-plane-run-detail-truth.md`
- existing archive/unarchive lifecycle routes and list filtering
- existing run-scoped artifact persistence and download surfaces

Affected stages:

- none

Affected features:

- `trigger_run_management`
- `inspection_debugging`

Primary lens: `mixed`

Affected docs:

- cross_cutting_docs:
  - `docs/usage.md`
  - `docs/api.md`

Generated refresh required: `yes`, because new planning artifact should flow
into generated planning lineage.

Capability IDs:

- none

Invariant IDs:

- none

Spec needed: `yes`
Plan needed: `yes`

## Goal

Define one safe, concrete operator function for permanently deleting archived
runs in bulk, including eligibility, UX wording, backend semantics, audit
behavior, and validation expectations.

## Key Deliverables

### Deliverable 1: Explicit operator lifecycle contract

Define the exact meaning of `Delete archived runs`, including what qualifies,
what is deleted, what is protected, and how operators confirm the action.

### Deliverable 2: Backend deletion boundary

Define which persisted surfaces must be removed together so the control plane
does not retain broken references, half-deleted artifacts, or orphaned rows.

### Deliverable 3: Verification-ready destructive-action scope

Define testable acceptance criteria and proof targets for both success and
rejection paths.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- ground the delete action in current run lifecycle semantics and archive truth

**Steps:**
- [ ] confirm current archive/unarchive behavior and archived list entry points
- [ ] identify persisted run-scoped artifacts and event surfaces tied to a run
- [ ] identify which current routes, templates, and docs own run lifecycle copy

**Verification:**
- [ ] current archive semantics and deletion boundaries are explicit enough to
      avoid ambiguous implementation

**Exit Criteria:**
- no destructive behavior depends on implied or hand-waved data ownership

### Wave 2: Decision closure

**Purpose:**
- lock down operator wording, eligibility, filters, and deletion semantics

**Steps:**
- [ ] define UX location and wording for the action
- [ ] define bulk eligibility and default age filter behavior
- [ ] define exactly which stored records and artifacts are deleted
- [ ] define failure handling for partial or invalid requests

**Verification:**
- [ ] each destructive path has explicit scope and rejection rules

**Exit Criteria:**
- design is concrete enough to implement without inventing product behavior

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof expectations for destructive cleanup behavior

**Steps:**
- [ ] define route- and store-level proof targets
- [ ] define UI confirmation and feedback proof targets
- [ ] define artifact-deletion and protection-of-non-eligible-run proof targets

**Verification:**
- [ ] validation plan proves both destructive success and safety boundaries

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: Keep archive and delete as separate lifecycle steps

- context: operators need cleanup, but archive already means retain evidence
- choice: require runs to be archived first; deletion never acts on non-archived
  runs
- alternatives considered:
  - add `Delete Run` on each run detail page
  - replace archive with direct deletion
  - add generic `Clear cache`
- impact:
  - preserves two-step lifecycle clarity
  - lowers accidental data loss risk
  - avoids vague cache semantics unrelated to run lifecycle truth

### Decision: Scope action to bulk archived-run cleanup from runs list

- context: deleting old history is list-management work, not single-run
  inspection work
- choice: surface `Delete archived runs` on `/admin/runs?view=archived`, not on
  run detail
- alternatives considered:
  - place delete button on every archived run detail page
  - add delete controls to both runs list and run detail
- impact:
  - keeps run detail focused on inspect, export, and reversible lifecycle
    actions
  - keeps destructive cleanup tied to the archived collection view

### Decision: Require explicit age filter, default `Older than 30 days`

- context: archived view may contain recently archived runs that operators still
  want to inspect
- choice: bulk delete uses an age threshold selector with default
  `Older than 30 days`
- alternatives considered:
  - delete all archived runs with no filter
  - require manual checkbox selection only
  - expose freeform date input
- impact:
  - gives safe default cleanup boundary
  - avoids over-building custom retention UI
  - still allows later expansion to other fixed thresholds if needed

### Decision: Confirmation dialog owns irreversible warning and count preview

- context: destructive actions need one final, explicit operator checkpoint
- choice: clicking `Delete archived runs` opens confirmation dialog showing
  matched run count, age filter, irreversible warning, and delete target
- alternatives considered:
  - one-click delete
  - browser-native confirm with no scoped details
- impact:
  - makes destructive scope visible before mutation
  - reduces accidental deletion due to ambiguous label meaning

### Decision: Delete run record and run-scoped persisted artifacts together

- context: keeping artifact rows or download links after run deletion would
  break operator truth and leave orphaned data
- choice: hard-delete each eligible run and all run-scoped persisted artifacts,
  stage artifacts, event rows, and local mirrored run-artifact bundles keyed to
  that run
- alternatives considered:
  - delete only top-level run row
  - delete only local artifact mirror and keep database state
  - anonymize rows instead of deleting
- impact:
  - prevents dangling run-detail or artifact references
  - forces implementation to define one authoritative per-run deletion helper
    across storage backends

### Decision: All-or-reject by eligibility filter, best-effort inside eligible set is not allowed

- context: partial destructive behavior is hard to explain and recover from
- choice: route computes eligible set from archive state plus age filter;
  ineligible runs are excluded before confirmation, and confirmed deletion
  should succeed transactionally per backend or fail with no reported success
- alternatives considered:
  - silently skip rows that fail during deletion
  - delete what can be deleted and report partial success
- impact:
  - success message remains trustworthy
  - backend implementation may need storage-specific rollback or staged delete
    guardrails

## Proposed Contract

### 1. Entry Point And Copy

Primary surface:

- runs list archived view: `GET /admin/runs?view=archived`

Primary action label:

- `Delete archived runs`

Helper text:

- `Permanently deletes archived runs you no longer need.`

The action should live near archived-view bulk controls, not inside generic app
settings and not behind cache language.

### 2. Filter Model

The delete action targets archived runs matching an age threshold.

Initial threshold options:

- `Older than 7 days`
- `Older than 30 days` (default)
- `Older than 90 days`
- `All archived runs`

Age should be calculated from `archived_at`, not run `created_at` or
`finished_at`.

Reason:

- retention intent begins when operator archives the run, not when the run was
  first created.

### 3. Eligibility Rules

A run is deletable only when all are true:

- `archived_at` is not null
- archived age matches selected threshold
- run is not currently referenced by any still-active control-plane workflow
  contract that requires persisted run detail after archive

Initial simplification:

- if a run is archived, it is assumed not to require active lifecycle actions
- there is no separate protected/locked flag in v1

Non-eligible runs:

- unarchived runs
- queued, running, cancelling, or paused runs even if their terminal truth is
  inconsistent elsewhere
- any run missing required archive state

### 4. Confirmation Contract

Before mutation, UI should show confirmation dialog containing:

- selected threshold label
- matched run count
- irreversible warning
- deletion scope summary

Canonical confirmation copy shape:

- title: `Delete archived runs?`
- body: `This permanently deletes <count> archived runs and their stored
  artifacts. This cannot be undone.`
- detail: `Filter: Older than <N days>` or `Filter: All archived runs`
- confirm button: `Delete permanently`
- cancel button: `Cancel`

If matched count is zero, the destructive confirm path should not open. UI
should show non-error feedback instead, such as `No archived runs match this
filter.`

### 5. Backend Route Contract

Add one bulk admin route for archived-run deletion.

Proposed route:

- `POST /admin/runs/bulk/delete-archived`

Request payload fields:

- `older_than_days`: integer or sentinel for `all`

Response payload on success:

```json
{
  "status": "deleted",
  "deleted_count": 42,
  "older_than_days": 30
}
```

Response payload on empty match:

```json
{
  "status": "no_matches",
  "deleted_count": 0,
  "older_than_days": 30
}
```

The route is admin-only and server-authoritative. Client must not submit run ids
as trusted delete scope in v1; server should derive eligible targets from the
archived filter request.

### 6. Deletion Boundary

For each deleted run, implementation must remove all run-scoped persisted data
owned by that run, including:

- run record
- run event timeline records
- run-scoped stage-artifact persistence owned by that run
- run-scoped export/debug/settings-used/results artifacts owned by that run
- deterministic local artifact mirror under `artifacts/live_run_<run_id>/`, if
  present

Deletion must not remove:

- shared settings defaults
- unrelated cached enrichments or embeddings reused across runs
- bookmarked jobs or other non-run operator records
- non-run-scoped product configuration

This boundary is why the feature is named `Delete archived runs`, not
`Clear cache`.

### 7. Audit Semantics

Deletion is destructive, so audit still matters even though run detail will no
longer exist after success.

Required audit behavior:

- write one aggregate admin log entry before deletion starts or immediately
  after successful commit
- include threshold and deleted count in server logs
- UI success banner should report deleted count

V1 does not need a new persistent tombstone table unless backend constraints
make aggregate deletion auditing impossible without it.

### 8. Error Handling

The route should reject malformed destructive requests clearly.

Examples:

- invalid threshold value -> `422`
- unauthorized caller -> auth failure per existing admin model
- backend delete failure -> `500` with no success banner

Operator-facing rule:

- never report successful deletion count unless backing delete completed for the
  full eligible set

### 9. UX After Success

After successful deletion:

- archived runs list refreshes
- success banner shows deleted count and threshold used
- empty archived view should render normal empty state if nothing remains

Canonical success copy shape:

- `Deleted 42 archived runs.`

Optional extended copy:

- `Deleted 42 archived runs older than 30 days.`

## Acceptance Criteria

- operator can trigger `Delete archived runs` from archived runs view
- action defaults to `Older than 30 days`
- confirmation dialog shows matched run count before destructive commit
- runs not archived are never included in delete scope
- deletion removes archived run records and their run-scoped persisted artifacts
  together
- deletion does not remove shared caches or unrelated non-run records
- empty-match request returns non-destructive success-like feedback, not a fake
  deletion count
- UI success feedback reflects actual deleted count
- route rejects malformed threshold values
- docs use `Delete archived runs` language and do not describe this function as
  cache clearing

## Non-Goals

- no generic `Clear cache` button
- no per-run `Delete Run` button in run detail for v1
- no custom retention policy builder
- no restore-from-trash workflow after deletion
- no deletion of unarchived runs
- no deletion of shared reuse caches such as enrichment or embedding stores

## Risks and Mitigations

- risk: operators confuse archive with delete
  - mitigation: keep both labels explicit and distinct; confirm dialog repeats
    permanent-delete warning
- risk: backend leaves orphaned artifacts or rows
  - mitigation: define one run-owned deletion boundary and test stored artifact
    removal explicitly
- risk: route deletes too broadly because threshold logic uses wrong timestamp
  - mitigation: key threshold to `archived_at` and test boundary cases
- risk: partial deletion produces misleading UI success
  - mitigation: no partial-success contract in v1; success only after full
    eligible-set completion

## Validation Plan

- proof target: archived runs view exposes destructive action with default age
  filter
  - method: test
  - evidence: focused app test covering archived view render and default filter

- proof target: confirmation path uses matched archived-run count and threshold
  semantics
  - method: test
  - evidence: route/UI test proving zero-match, non-zero-match, and displayed
    copy behavior

- proof target: backend deletes only archived runs matching threshold
  - method: test
  - evidence: store-level tests for `archived_at` boundary selection and delete
    count

- proof target: backend removes run-owned persisted artifacts together with run
  record
  - method: test
  - evidence: store/integration tests covering run row, events, artifact
    payloads, and local artifact mirror cleanup

- proof target: shared caches and unrelated records are preserved
  - method: test
  - evidence: negative tests proving non-run-scoped tables/paths remain intact

- proof target: malformed threshold requests fail safely
  - method: test
  - evidence: route test returning `422` for invalid threshold input

- proof target: operator docs describe archive vs delete distinction clearly
  - method: inspection
  - evidence: updated `docs/usage.md` and `docs/api.md`

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. implementation plan exists for route, store, UI, and docs updates
3. destructive-scope proof targets are explicit enough to prevent ambiguous
   implementation
