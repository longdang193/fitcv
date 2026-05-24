---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: bookmarks-application-status-tracking
parent_thread: workstream-operator-control-plane.operator-control-plane-run-detail-truth
parent_spec: docs/superpowers/specs/2026-05-24-19-37-bookmarks-application-status-tracking-spec.md
targets:
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/bookmarks.html
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

## Goal

Implement application-status tracking for bookmarked jobs with persisted status (`active`, `submitted`, `archived`), status actions, and filter tabs on Bookmarked Jobs page.

## Key Deliverables

### Deliverable 1: Persisted bookmark status schema + API

Local sqlite `bookmarked_jobs` table supports status fields with safe migration for existing DB files, plus store helpers to update and query status.

### Deliverable 2: Bookmarks page status interactions + filtering

`/admin/bookmarks` renders filter tabs (`All`, `Submitted`, `Archived`) and per-row status actions (`Submitted`, `Archive`, `Restore`, `Undo Submitted`) using SSR form POST endpoints.

### Deliverable 3: Test coverage for status + filter behavior

Tests prove status endpoint wiring, tab/filter rendering, and that legacy delete flow remains intact.

## Task/Wave Breakdown

### Task 1: Extend sqlite schema with forward-compatible migration

**Purpose:**
- add status columns without breaking existing sqlite DB files

**Files:**
- Inspect: `src/fitcv_cp/settings_store.py`
- Modify: `src/fitcv_cp/settings_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- current `bookmarked_jobs` table created by `_ensure_local_bookmarked_jobs_table()`
- migration must be additive (no destructive table rewrite)

**Steps:**
- [ ] Step 1: define canonical status vocabulary: `active`, `submitted`, `archived`
- [ ] Step 2: update `_ensure_local_bookmarked_jobs_table()` to:
  - create table if missing (current behavior)
  - detect missing columns via `PRAGMA table_info(bookmarked_jobs)`
  - `ALTER TABLE ... ADD COLUMN` for missing:
    - `status TEXT NOT NULL DEFAULT 'active'`
    - `submitted_at TEXT`
    - `archived_at TEXT`
    - optional: `status_updated_at TEXT` (only if plan wants it; keep minimal)
- [ ] Step 3: update `list_bookmarked_jobs()` to SELECT status columns and return `status` in dict result (default to `active` when column absent or NULL)
- [ ] Step 4: update `upsert_bookmarked_job()` to preserve existing status on conflict (do not overwrite to `active` on re-save)

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "admin_bookmarks"`

**Exit Criteria:**
- existing sqlite file can open and table upgraded in-place
- listing bookmarks includes `status` for each row

### Task 2: Add store helper to update bookmark status

**Purpose:**
- create single SSOT function for status transitions, including timestamps

**Files:**
- Modify: `src/fitcv_cp/settings_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: add `set_bookmarked_job_status(bookmark_key: str, status: str, *, at: str | None = None) -> bool`
- [ ] Step 2: validate `status` in allowed set; reject invalid with ValueError
- [ ] Step 3: update row by `bookmark_key`; set:
  - `status = ?`
  - `submitted_at` when status becomes `submitted` (and clear when leaving submitted, if desired)
  - `archived_at` when status becomes `archived` (and clear when leaving archived, if desired)
- [ ] Step 4: return bool whether row updated (rowcount > 0)

**Verification:**
- [ ] unit-style test via patching in route tests (Task 4) OR direct sqlite fixture if existing suite already uses local sqlite

**Exit Criteria:**
- store exposes one stable API for status updates and future extension

### Task 3: Add bookmarks status update route endpoint

**Purpose:**
- wire SSR POST action for status change with safe redirect

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 complete (`set_bookmarked_job_status` exists)
- `_safe_admin_redirect_target` helper exists and used by delete route

**Steps:**
- [ ] Step 1: add `@app.post("/admin/bookmarks/status")` handler
- [ ] Step 2: parse form fields:
  - `bookmark_key` (required)
  - `status` (required)
  - `redirect_to` (optional; default `/admin/bookmarks`)
- [ ] Step 3: call `set_bookmarked_job_status(bookmark_key, status)`
- [ ] Step 4: redirect 303 to safe `redirect_to`

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "bookmarks and status"`

**Exit Criteria:**
- endpoint updates status and returns stable redirect

### Task 4: Update bookmarks page route to support filtering + sections

**Purpose:**
- expose `All / Submitted / Archived` views and section grouping for `All`

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/bookmarks.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete (bookmark items include status)

**Steps:**
- [ ] Step 1: extend `GET /admin/bookmarks` to accept `view` query param:
  - `all` (default)
  - `submitted`
  - `archived`
- [ ] Step 2: build view-model:
  - for `all`: split list into `active_items`, `submitted_items`, optionally `archived_items`
  - for other views: return one list only
- [ ] Step 3: keep existing row fields (`job_primary_label`, `saved_at_display`, etc.) for each item, independent of status
- [ ] Step 4: pass `view` into template context for `aria-pressed` on tabs

**Verification:**
- [ ] add/extend tests to assert:
  - tabs rendered with correct `aria-pressed`
  - `view=submitted` response does not include active-only action label if excluded
  - `all` view shows section headings and correct row placement markers

**Exit Criteria:**
- server renders correct subsets/sections for all views without JS

### Task 5: Update bookmarks template actions and status badges

**Purpose:**
- add visible per-row status actions and keep UI simple/clear

**Files:**
- Inspect: `src/fitcv_cp/templates/bookmarks.html`
- Modify: `src/fitcv_cp/templates/bookmarks.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete (status POST endpoint exists)
- Task 4 complete (template has access to status + view)

**Steps:**
- [ ] Step 1: add top-of-page filter buttons modeled after `src/fitcv_cp/templates/runs_list.html`:
  - `/admin/bookmarks?view=all`
  - `/admin/bookmarks?view=submitted`
  - `/admin/bookmarks?view=archived`
- [ ] Step 2: in row action cluster add forms posting to `/admin/bookmarks/status`:
  - when `active`: button `✓ Submitted` sets `status=submitted`; button `Archive` sets `status=archived`
  - when `submitted`: button `Undo Submitted` sets `status=active`; button `Archive` sets `status=archived`
  - when `archived`: button `Restore` sets `status=active`
  - always keep existing `★ Remove` form
- [ ] Step 3: add small status badge near fit badge:
  - submitted -> `Submitted`
  - archived -> `Archived`
- [ ] Step 4: ensure action buttons keep wrapping behavior (existing flex-wrap)

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "admin_bookmarks"`

**Exit Criteria:**
- user can quickly see “needs action vs submitted vs archived” and act in 1 click

### Task 6: Regression + final verification

**Purpose:**
- confirm bounded change works and stays within intended surfaces

**Files:**
- Inspect: `src/fitcv_cp/settings_store.py`
- Inspect: `src/fitcv_cp/app.py`
- Inspect: `src/fitcv_cp/templates/bookmarks.html`
- Inspect: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-5 complete

**Steps:**
- [ ] Step 1: run targeted tests for bookmarks
- [ ] Step 2: run fast validator hook

**Verification:**
- [ ] `pytest tests/test_fitcv_cp/test_app.py -k "admin_bookmarks or bookmark"`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- tests green for touched surface; repo fast validator passes

## Verification

- `pytest tests/test_fitcv_cp/test_app.py -k "admin_bookmarks or bookmark"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
