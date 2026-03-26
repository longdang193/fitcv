# Admin Control Plane UX Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the user experience of the FitCV Admin CP by (1) making settings labels end-user friendly, (2) adding global navigation links, and (3) highlighting CV generation outcomes on the run detail page.

**Spec:** `docs/superpowers/specs/2026-03-25-admin-ux-improvements-design.md`

---

## ✅ STATUS: COMPLETE — Deployed 2026-03-25

Verified against codebase: all features present in production code.

---

## Task 1 — Settings Schema Friendliness

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`

- [x] **Step 1.1: Write failing schema tests**
- [x] **Step 1.2: Run to confirm failure**
- [x] **Step 1.3: Update `settings_schema.py`**

  All entries have `label` (plain English) and `description` fields.
  Verified: `grep -n "description\|label" settings_schema.py` returns all 6 schema entries with both keys.

- [x] **Step 1.4: Update `settings.html` template**
- [x] **Step 1.5: Run tests**
- [x] **Step 1.6: Commit**

---

## Task 2 — Add Global Navigation

**Files:**
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/settings.html` (remove old backlink)

- [x] **Step 2.1: Update `base.html`**

  Verified: `base.html` contains:
  ```html
  <a href="/admin/settings">Settings</a>
  <a href="/healthz">Health</a>
  ```

- [x] **Step 2.2: Remove redundant backlink**
- [x] **Step 2.3: Write automated tests for navigation**
- [x] **Step 2.4: Commit**

---

## Task 3 — Highlight Generated CVs

**Files:**
- Modify: `src/fitcv_cp/templates/run_detail.html`

- [x] **Step 3.1: Create CV Success Banner Component**

  Verified: `run_detail.html` includes the `{% if run.status.value == 'succeeded' and run.cvs_generated is not none %}` block with green success / red zero-CV states and per-CV download links.

- [x] **Step 3.2: Remove redundant field**
- [x] **Step 3.3: Write automated tests for CV banner**
- [x] **Step 3.4: Manual UI Verification**
- [x] **Step 3.5: Commit**

---

## Task 4 — Final Suite-Level Verification

- [x] **Step 4.1: Run all tests in the package**

  Current suite: `372 passed, 7 deselected` (2026-03-26 run including all later tasks)
