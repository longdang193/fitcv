# Run Detail Inspection Tabs — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorganize the run detail page into a 3-tab inspection interface (Enriched Jobs / Original Job Input / Candidate Profile). Originally planned as a template-only change; a follow-up fix also extended the snapshot rule to cover `upload` mode.

**Spec:** `docs/superpowers/specs/2026-03-26-run-detail-inspection-tabs-design.md`

**Tech Stack:** Jinja2, Vanilla JS, Vanilla CSS, Python (FastAPI)

---

## ✅ STATUS: COMPLETE — Deployed 2026-03-26

**Tests:** 374 pass, 2 pre-existing `test_enrich` failures (unrelated), 7 deselected
**Commits:**
- `feat(ui): reorganize run detail into 3-tab inspection interface`
- `fix: snapshot jobs_input_json for upload mode (not just paste)`

---

## File Map

- **Modify:** `src/fitcv_cp/templates/run_detail.html`
- **Modify:** `src/fitcv_cp/app.py` — `upload_trigger` upload mode now captures `jobs_input_json_snapshot`
- **Modify:** `tests/test_fitcv_cp/test_app.py` — 4 new tab assertions

## Task 1: Tab Bar and Pane Structure

**File:** `src/fitcv_cp/templates/run_detail.html`

- [ ] **Step 1.1: Add tab styles**

  Add a `<style>` block (or inline styles) for:
  - `.tab-bar` — flex row, gap, bottom border
  - `.tab-btn` — default inactive state (muted text, transparent background)
  - `.tab-btn.active` — active state (indigo background, white text)
  - `.tab-pane` — `display:none` by default
  - `.tab-pane.active` — `display:block`

- [ ] **Step 1.2: Add tab bar HTML**

  Below the CV results banner and above the Event Timeline, insert:

  ```html
  <div class="tab-bar">
    <button class="tab-btn active" id="tab-btn-enriched"
            onclick="showTab('enriched')">📊 Enriched Jobs</button>
    <button class="tab-btn" id="tab-btn-jobs-input"
            onclick="showTab('jobs-input')">📄 Original Job Input</button>
    <button class="tab-btn" id="tab-btn-profile"
            onclick="showTab('profile')">👤 Candidate Profile</button>
  </div>
  ```

- [ ] **Step 1.3: Add `showTab` JS function**

  ```js
  function showTab(id) {
    document.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('pane-' + id).classList.add('active');
    document.getElementById('tab-btn-' + id).classList.add('active');
  }
  ```

---

## Task 2: Move Enriched Jobs into Tab 1

- [ ] **Step 2.1: Wrap existing enriched jobs block**

  Wrap the current `<h2>Enriched Jobs</h2>` and its `<div class="card">…</div>` in:

  ```html
  <div class="tab-pane active" id="pane-enriched">
    <!-- existing enriched jobs table (unchanged) -->
  </div>
  ```

  No change to table content or filter column logic.

---

## Task 3: Build Tab 2 — Original Job Input

- [ ] **Step 3.1: Add Tab 2 pane**

  ```html
  <div class="tab-pane" id="pane-jobs-input">
    {% if run.jobs_input_json %}
      <!-- snapshot path -->
    {% else %}
      <!-- fallback path -->
    {% endif %}
  </div>
  ```

- [ ] **Step 3.2: Snapshot path**

  ```html
  <div class="card" style="margin-bottom:1rem">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem">
      <span class="badge badge-info">{{ run.jobs_input_source or 'paste' }}</span>
      <span class="meta">Raw job payload captured at trigger time (immutable snapshot)</span>
    </div>
    <pre style="...scrollable pre styles...">{{ run.jobs_input_json }}</pre>
  </div>
  ```

- [ ] **Step 3.3: Fallback path**

  ```html
  <div class="card" style="margin-bottom:1rem">
    <p class="meta">
      Source: <strong>{{ run.jobs_input_source or '—' }}</strong>
      &nbsp;·&nbsp; Path: <code>{{ run.jobs_path }}</code>
    </p>
    <p style="color:#64748b;font-size:0.85rem">
      No immutable raw snapshot was stored for this run.
      Only paste-mode runs capture a raw JSON snapshot at trigger time.
    </p>
  </div>
  ```

---

## Task 4: Build Tab 3 — Candidate Profile

- [ ] **Step 4.1: Add Tab 3 pane**

  ```html
  <div class="tab-pane" id="pane-profile">
    {% if candidate_profile_pretty %}
      <!-- snapshot path -->
    {% else %}
      <!-- fallback path -->
    {% endif %}
  </div>
  ```

- [ ] **Step 4.2: Snapshot path — dual view**

  Render two sub-sections when `candidate_profile_pretty` is present:

  **Sub-section A — Formatted summary:**
  ```html
  <div class="card" style="margin-bottom:1rem">
    <div style="display:flex;align-items:center;gap:0.75rem;margin-bottom:0.75rem">
      <span class="badge badge-info">{{ run.candidate_profile_source }}</span>
      <span class="meta">Candidate profile captured at trigger time (immutable snapshot)</span>
    </div>
    {% if candidate_profile_parsed %}
    <div class="kv">
      {% for key in ['name', 'seniority_target', 'location_types', 'skills'] %}
        {% if candidate_profile_parsed.get('preferences', {}).get(key) or candidate_profile_parsed.get(key) %}
        <span class="k">{{ key }}</span>
        <span class="v">{{ candidate_profile_parsed.get('preferences', {}).get(key) or candidate_profile_parsed.get(key) }}</span>
        {% endif %}
      {% endfor %}
    </div>
    {% endif %}
  </div>
  ```

  **Sub-section B — Raw JSON:**
  ```html
  <details open>
    <summary style="cursor:pointer;color:#94a3b8;font-size:0.82rem">Raw JSON</summary>
    <pre style="...scrollable pre styles...">{{ candidate_profile_pretty }}</pre>
  </details>
  ```

- [ ] **Step 4.3: Fallback path — null-safe source display**

  ```html
  <div class="card">
    <p class="meta">
      Source:
      {% if run.candidate_profile_source %}
        <strong>{{ run.candidate_profile_source }}</strong>
      {% else %}
        <span style="color:#64748b">— not recorded</span>
      {% endif %}
    </p>
    <p style="color:#64748b;font-size:0.85rem">
      No candidate profile snapshot was stored for this run.
      Default-config and pre-feature runs do not capture a profile snapshot.
    </p>
  </div>
  ```

  > **Do not** use `{{ run.candidate_profile_source or 'default_config' }}`. A `NULL` source means the source was not recorded — it must display as `—`, not be inferred as `default_config`.

---

## Task 5: Clean Up and Move Event Timeline

- [ ] **Step 5.1: Remove old inline panels**

  Remove the current standalone `{% if candidate_profile_pretty %}` and `{% if run.jobs_input_json %}` blocks that were previously rendered inline below the enriched jobs table. Their content is now inside the tab panes.

- [ ] **Step 5.2: Ensure Event Timeline is below tabs**

  The `<h2>Event Timeline</h2>` block must remain **outside and below** all tab panes — always visible regardless of active tab.

---

## Task 6: Verify

- [ ] **Step 6.1: Run existing tests**

  ```bash
  /tmp/fitcv-test-env/bin/pytest tests/test_fitcv_cp/test_app.py -q --tb=short
  ```

- [ ] **Step 6.2: Add new test assertions** in `tests/test_fitcv_cp/test_app.py`

  Cover:

  - **Default active tab:** Assert rendered HTML contains `id="pane-enriched"` with `class` including `active`, and `id="tab-btn-enriched"` with `active` class.
  - **Tab 2 fallback (no snapshot):** Mock a run with `jobs_input_json=None`. Assert fallback text ("No immutable raw snapshot") is present. Assert `jobs_path` or `jobs_input_source` appears.
  - **Tab 3 fallback (no snapshot):** Mock a run with `candidate_profile_json=None` and `candidate_profile_source=None`. Assert fallback text is present. Assert the string `default_config` does **not** appear in the Tab 3 pane for null-source runs.
  - **Event Timeline outside panes:** Assert `<h2>Event Timeline</h2>` appears **after** the closing `</div>` of any tab pane in the raw HTML string (order-based assertion).

- [ ] **Step 6.3: Run full regression suite**

  ```bash
  /tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
  ```

- [ ] **Step 6.4: Manual verification**

  1. Open run detail for a paste-mode run (has both snapshots) → verify all 3 tabs render; Tab 3 shows formatted summary + raw JSON
  2. Open run detail for an older run → verify Tab 2 and Tab 3 show `—` (not `default_config`) for null source
  3. Verify Event Timeline is always visible below the tabs

- [ ] **Step 6.5: Commit**

  ```bash
  git add src/fitcv_cp/templates/run_detail.html tests/test_fitcv_cp/test_app.py
  git commit -m "feat(ui): reorganize run detail into 3-tab inspection interface"
  ```

---

## Important Notes

## Important Notes

- **Snapshot rule:** `paste` and `upload` capture an immutable raw JSON snapshot at trigger time. `path` (jobs) and `default_config` (candidate profile) do not — only source metadata is stored.
- `app.py` was modified: jobs `upload` mode now reads bytes once, canonicalises to pretty JSON, stores in `jobs_input_json_snapshot` (same as paste mode). Candidate profile `upload` already did this correctly.
- Old runs where all snapshot fields are `None` render gracefully via fallback branches.
- Tab switching is client-side only — no server round-trips.
