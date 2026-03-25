# Admin Control Plane UX Polish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve the user experience of the FitCV Admin CP by (1) making settings labels end-user friendly, (2) adding global navigation links, and (3) highlighting CV generation outcomes on the run detail page.

**Spec:** `docs/superpowers/specs/2026-03-25-admin-ux-improvements-design.md`

---

## Task 1 — Settings Schema Friendliness

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`

- [ ] **Step 1.1: Write failing schema tests**
Update `test_schema_has_required_fields` in `tests/test_fitcv_cp/test_settings_schema.py` to assert that `"description" in entry`.

- [ ] **Step 1.2: Run to confirm failure**
```bash
/tmp/fitcv-test-env/bin/pytest tests/test_fitcv_cp/test_settings_schema.py -v
```

- [ ] **Step 1.3: Update `settings_schema.py`**
Add a `description` string to every dictionary in `SETTINGS_SCHEMA`. Update all `label` strings to be plain English (e.g. "Initial Candidate Pool Size").

- [ ] **Step 1.4: Update `settings.html` template**
Modify `src/fitcv_cp/templates/settings.html`.
Replace: `<td class="py-2 pr-4 font-mono text-xs text-blue-300">{{ entry.key }}</td>`
With:
```html
<td class="py-3 pr-4">
  <div class="font-semibold text-gray-200">{{ entry.label }}</div>
  <div class="text-xs text-gray-400 mt-1 max-w-sm leading-relaxed">{{ entry.description }}</div>
</td>
```

- [ ] **Step 1.5: Run tests**
Verify the schema tests pass.

- [ ] **Step 1.6: Commit**
Commit changes related to the UX settings enhancements.

---

## Task 2 — Add Global Navigation

**Files:**
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/settings.html` (remove old backlink)

- [ ] **Step 2.1: Update `base.html`**
Add `<a href="/admin/settings">Settings</a>` inside the `<nav>` component, next to the "Runs" link.

- [ ] **Step 2.2: Remove `<a href="/admin/runs">← Back to runs</a>`**
Since navigation is in the header, remove the redundant standalone backlink from the bottom of `settings.html` and the top of `run_detail.html`.

- [ ] **Step 2.3: Write automated tests for navigation**
Update `test_app.py` wrapper tests to assert that `<a href="/admin/settings">Settings</a>` is present in the rendered HTML output.

- [ ] **Step 2.4: Commit**
Commit navigation changes.

---

## Task 3 — Highlight Generated CVs

**Files:**
- Modify: `src/fitcv_cp/templates/run_detail.html`

- [ ] **Step 3.1: Create CV Success Banner Component**
In `src/fitcv_cp/templates/run_detail.html`, just below the run status badges but above the event timeline, inject a custom highlight box component specifically tied to `run.cvs_generated`:

```html
{% if run.status.value == 'succeeded' %}
<div class="card" style="background: rgba(20, 83, 45, 0.2); border-color: #166534; margin-bottom: 1.5rem;">
  <h3 style="color: #4ade80; font-size: 1.1rem; font-weight: 600; margin-bottom: 0.5rem;">
    🎉 Pipeline Completed Successfully!
  </h3>
  {% if run.cvs_generated and run.cvs_generated > 0 %}
    <p style="color: #bbf7d0; font-size: 0.9rem;">
      <strong>{{ run.cvs_generated }}</strong> candidate CV(s) were successfully generated. 
      The generated CV markdowns have been persisted to the <strong>cv_versions</strong> BigQuery table.
    </p>
  {% else %}
    <p style="color: #fca5a5; font-size: 0.9rem;">
      No candidates met the minimum ranking thresholds to generate CVs.
    </p>
  {% endif %}
</div>
{% endif %}
```

- [ ] **Step 3.2: Remove redundant field**
Remove the plain `<span class="k">CVs Generated</span>` from the `kv` properties grid.

- [ ] **Step 3.3: Write automated tests for CV banner**
Update `test_app.py` to mock `get_run` returning a run with `cvs_generated=5` and `status=RunStatus.SUCCEEDED`, and assert the success banner is correctly rendered with the BigQuery storage message. Ensure `cvs_generated=0` shows the warning banner.

- [ ] **Step 3.4: Manual UI Verification**
Ensure the server is running and load `http://localhost:8000/admin/runs/{succeeded_run_id}` to verify styles overlap appropriately.

- [ ] **Step 3.5: Commit**
Commit the template changes.

---

## Task 4 — Final Suite-Level Verification

- [ ] **Step 4.1: Run all tests in the package**
Confirm that no broader regressions were introduced by running the complete suite for the admin control plane.
```bash
/tmp/fitcv-test-env/bin/python -m pytest tests/test_fitcv_cp/ -v
```
