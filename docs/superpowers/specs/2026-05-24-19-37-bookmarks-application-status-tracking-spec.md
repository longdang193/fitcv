---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: bookmarks-application-status-tracking
parent_thread: workstream-operator-control-plane.operator-control-plane-settings-surface-alignment
targets:
  - src/fitcv_cp/templates/bookmarks.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_store.py
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

## Goal

Add application-status tracking to Bookmarked Jobs page so user can mark bookmarked job as `Submitted` (CV sent) or `Archived`, filter by status, and keep status persisted across refresh/app restart.

## Key Deliverables

### Deliverable 1: Persisted bookmark status model

Bookmark persistence supports stable status values (`active`, `submitted`, `archived`) with forward-compatible schema migration for existing local sqlite DB.

### Deliverable 2: Bookmarks page status UX

Bookmarked Jobs page exposes:

- per-row action to mark `Submitted`
- per-row action to `Archive` / `Restore`
- filter tabs/buttons: `All`, `Submitted`, `Archived`

### Deliverable 3: Regression-safe tests

Existing bookmarks page + delete flow remains valid, with added tests proving status persistence wiring and filter behavior.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current bookmarks persistence + page rendering contract before adding status logic

**Steps:**
- [x] inspect current `bookmarked_jobs` sqlite schema and access API in `src/fitcv_cp/settings_store.py`
- [x] inspect `/admin/bookmarks` route + template expectations in `src/fitcv_cp/app.py` + `src/fitcv_cp/templates/bookmarks.html`
- [x] inspect existing tests around bookmarks page in `tests/test_fitcv_cp/test_app.py`

**Verification:**
- [x] current page uses server-rendered template and sqlite-backed persistence (no JS required)

**Exit Criteria:**
- no core decision depends on unknown persistence backend or client state

### Wave 2: Decision closure

**Purpose:**
- resolve status semantics, persistence shape, schema migration, and page interaction contract

**Steps:**
- [x] define status taxonomy and transitions (`active` <-> `submitted`, `archived` as separate terminal bucket)
- [x] decide whether status is single enum column vs multiple booleans
- [x] decide migration approach for existing sqlite DB files
- [x] define UI contract for filter tabs and per-row actions (including button labels)

**Verification:**
- [x] decisions include fallback behavior for legacy DB without new columns

**Exit Criteria:**
- implementation can proceed without unresolved UX/state questions

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations explicit before writing implementation plan

**Steps:**
- [x] specify test cases for status actions and filters
- [x] specify minimal manual QA checks on page

**Verification:**
- [x] validation plan proves persistence across refresh and correct filtering

**Exit Criteria:**
- spec ready for implementation planning

## Design Decisions

### Decision: Use single `status` enum on bookmarked job

- context: user needs mutually exclusive “Submitted vs Archived vs Needs action” views; page already uses sqlite SSOT
- choice: store `status` as single TEXT column with allowed values:
  - `active` (default; needs action)
  - `submitted`
  - `archived`
- alternatives considered:
  - two booleans (`is_submitted`, `is_archived`)
  - store status only in `snapshot_json` (opaque JSON)
- impact:
  - simpler invariants: exactly one status at a time
  - easier SQL filtering and template logic
  - avoids duplicated truth across structured column + JSON

### Decision: Forward-compatible sqlite schema migration via “add missing columns”

- context: local sqlite file may already exist; `CREATE TABLE IF NOT EXISTS` does not add columns
- choice: keep existing table name and add missing columns using `PRAGMA table_info(bookmarked_jobs)` + `ALTER TABLE ... ADD COLUMN ...`
- alternatives considered:
  - require user delete sqlite file
  - create new table and copy rows (heavier migration)
- impact:
  - preserves existing bookmarks without manual intervention
  - keeps migration logic bounded and low-risk

### Decision: Server-rendered form actions (no JS required)

- context: bookmarks page today uses form POST for delete; consistent SSR pattern preferred
- choice:
  - add `POST /admin/bookmarks/status` form action to update status
  - redirect back to `redirect_to` or `/admin/bookmarks`
- alternatives considered:
  - client-side JS toggles with fetch
- impact:
  - minimal moving parts; consistent with current UI
  - filtering can be query-param driven (`/admin/bookmarks?view=submitted`)

### Decision: `All` view uses sections; other views use single list

- context: user wants “move to Submitted section/status”; also wants filter tabs
- choice:
  - `view=all`: show sections in order:
    1) `Needs Action` (`active`)
    2) `Submitted` (`submitted`)
    (omit archived section by default, or show small `Archived (n)` footer; exact final UX decided in plan)
  - `view=submitted`: show submitted only
  - `view=archived`: show archived only
- alternatives considered:
  - always show one combined list with inline status badges
- impact:
  - preserves “move to Submitted section” semantics
  - gives fast focus views via tabs

## Invariants

- Invariant 1: Each bookmark row has exactly one status in `{active, submitted, archived}`.
- Invariant 2: Default status for existing and new bookmarks is `active`.
- Invariant 3: Status persistence survives page refresh and app restart (sqlite-backed).
- Invariant 4: Existing bookmark identity (`bookmark_key`) remains stable; status updates address rows by `bookmark_key`.
- Invariant 5: Existing `/admin/bookmarks/delete` behavior remains unchanged.

## Acceptance Criteria

1. Bookmarks page shows filter tabs/buttons: `All`, `Submitted`, `Archived`.
2. Each bookmark row shows a `Submitted` action when status is `active`.
3. Submitting a bookmarked job moves it out of “Needs Action” and into “Submitted” section in `All` view.
4. Submitted view shows only submitted rows; Archived view shows only archived rows.
5. Status remains correct after hard refresh and after restarting app.
6. User can archive and restore a bookmark without losing bookmark entry.
7. Remove bookmark still removes row regardless of status.

## Non-Goals

- Multi-user accounts, shared bookmarks, or cloud sync.
- Additional pipeline states (`interviewing`, `offer`, etc.).
- Client-side realtime updates without reload.
- Major redesign of bookmarks page layout beyond adding status controls and filter tabs.

## Risks and Mitigations

- Risk: sqlite migration fails on existing db due to unexpected schema drift.
  - Mitigation: “add missing columns” strategy only; avoid destructive migration; keep safe defaults (`active`).
- Risk: status stored in both column and JSON diverges.
  - Mitigation: store status only in structured column; keep `snapshot_json` for job snapshot only.
- Risk: action-button crowding reduces usability.
  - Mitigation: reuse existing flex-wrap action cluster; keep buttons short; prioritize 1 primary status action + secondary archive/remove.

## Validation Plan

- proof target: status persists and filters correct
  - method: extend/add tests in `tests/test_fitcv_cp/test_app.py` using patched `list_bookmarked_jobs()` outputs containing status values
  - evidence: assertions on response HTML for tabs, sections, and row placement

- proof target: status update endpoint wired correctly
  - method: test POST to `/admin/bookmarks/status` calls new store function with expected args and returns 303 redirect
  - evidence: passing tests asserting store-call + redirect location

- proof target: legacy delete flow intact
  - method: keep existing test `test_admin_bookmarks_page_and_delete_flow` passing with minimal updates
  - evidence: passing test suite subset

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

## Triage Block

Layer: change
Feature type: ADD
Summary: Add submitted/archived status tracking + filters to Bookmarked Jobs page, persisted in local sqlite.
Reasoning: Bounded UX + persistence extension to existing bookmark feature; no intent/workstream governance changes.
Invariants:
- exactly-one status enum per bookmark
- persistence across refresh/restart
- no regression to delete/remove flow
Dependencies:
- `bookmarked_jobs` sqlite schema migration behavior
- bookmarks route/template rendering
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
- cross_cutting_docs:
  - docs/superpowers/specs/2026-05-24-19-37-bookmarks-application-status-tracking-spec.md
- generated:
  - none
Generated refresh required: no
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes
