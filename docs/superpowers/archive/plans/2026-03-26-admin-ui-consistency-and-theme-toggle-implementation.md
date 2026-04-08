# Admin UI Consistency and Theme Toggle — Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Introduce a token-based CSS design system with dark/light theme toggle; migrate all four admin templates from inline styles and per-row form actions to shared classes and section-level saves.

**Spec:** `docs/superpowers/specs/2026-03-26-admin-ui-consistency-and-theme-toggle-design.md`

**Decision — scope includes section-level save backend:** The spec explicitly requires independent settings sections to use a single section-form pattern with one save action. The grouped-save infrastructure (`save_settings_group`, `/admin/settings/group/{group_name}`) already exists and is reused. This adds backend work but keeps the implementation small.

**Backend changes: Yes.** Add `SETTINGS_SECTIONS` registry and `POST /admin/settings/section/{section_name}` endpoint (both modelled on the existing `RANKING_GROUPS` / group route). No new BigQuery tables or models needed.

**Anti-drift rule:** No new inline styles are introduced. All button, color, and spacing patterns go into shared CSS classes in `base.html` first.

---

## File Map

- **Modify:** `src/fitcv_cp/templates/base.html`
- **Modify:** `src/fitcv_cp/settings_schema.py`
- **Modify:** `src/fitcv_cp/app.py`
- **Modify:** `src/fitcv_cp/templates/settings.html`
- **Modify:** `src/fitcv_cp/templates/runs_list.html`
- **Modify:** `src/fitcv_cp/templates/run_detail.html`
- **Modify:** `tests/test_fitcv_cp/test_app.py`
- **Modify:** `tests/test_fitcv_cp/test_settings_schema.py`

---

## Task 1: Expand `base.html` — tokens, shared classes, theme toggle

**File:** `src/fitcv_cp/templates/base.html`

- [x] **Step 1.1: Add inline "no-flash" theme script as the very first child of `<head>`**

  Reads `localStorage` and sets `data-theme` on `<html>` before any CSS is parsed, preventing theme flash:
  ```html
  <script>
    (function() {
      var t = localStorage.getItem('fitcv-theme') || 'dark';
      document.documentElement.setAttribute('data-theme', t);
    })();
  </script>
  ```

- [x] **Step 1.2: Replace existing `<style>` block with a full token-based CSS design system**

  **Token definitions for both themes:**
  ```css
  :root[data-theme="dark"] {
    --bg: #0f1117; --surface-1: #1a1d2e; --surface-2: #1e2235;
    --border: #2d3148; --border-soft: #1e2235;
    --text-primary: #e2e8f0; --text-secondary: #94a3b8; --text-muted: #64748b;
    --accent: #6366f1; --accent-hover: #4f46e5;
    --badge-success-bg:#14532d; --badge-success-fg:#4ade80;
    --badge-error-bg:#450a0a;   --badge-error-fg:#f87171;
    --badge-warning-bg:#422006; --badge-warning-fg:#fb923c;
    --badge-info-bg:#1e3a5f;    --badge-info-fg:#60a5fa;
    --badge-neutral-bg:#334155; --badge-neutral-fg:#94a3b8;
    --table-header-bg: var(--surface-2); --table-row-hover: #1a1e30;
    --input-bg: var(--surface-2);
  }
  :root[data-theme="light"] {
    --bg: #f8fafc; --surface-1: #ffffff; --surface-2: #f1f5f9;
    --border: #e2e8f0; --border-soft: #f1f5f9;
    --text-primary: #0f172a; --text-secondary: #475569; --text-muted: #94a3b8;
    --accent: #4f46e5; --accent-hover: #3730a3;
    --badge-success-bg:#dcfce7; --badge-success-fg:#166534;
    --badge-error-bg:#fee2e2;   --badge-error-fg:#991b1b;
    --badge-warning-bg:#ffedd5; --badge-warning-fg:#9a3412;
    --badge-info-bg:#dbeafe;    --badge-info-fg:#1e40af;
    --badge-neutral-bg:#f1f5f9; --badge-neutral-fg:#475569;
    --table-header-bg: #f8fafc; --table-row-hover: #f1f5f9;
    --input-bg: #ffffff;
  }
  ```

  **Shared base styles (all tokens — no hard-coded hex):**
  ```css
  body         { background: var(--bg); color: var(--text-primary); ... }
  nav          { background: var(--surface-1); border-color: var(--border); ... }
  th           { background: var(--table-header-bg); color: var(--text-muted); ... }
  td           { border-color: var(--border-soft); color: var(--text-secondary); }
  tr:hover td  { background: var(--table-row-hover); }
  ```

  **Shared input styles (covers text, number, textarea, select):**
  ```css
  input[type="text"], input[type="number"], textarea, select {
    background: var(--input-bg); border: 1px solid var(--border);
    color: var(--text-primary); ...
  }
  *:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
  ```

  **Button classes — three levels:**
  ```css
  /* Primary — grouped ranking saves */
  .btn-primary { background: var(--accent); color: #fff; border: none; ... }
  .btn-primary:hover { background: var(--accent-hover); }

  /* Secondary — supporting actions (Refresh, theme toggle) */
  .btn-secondary { background: transparent; color: var(--text-secondary);
                   border: 1px solid var(--border); ... }
  .btn-secondary:hover { border-color: var(--accent); color: var(--accent); }

  /* Section — settings section saves */
  .btn-section { background: var(--surface-2); color: var(--accent);
                 border: 1px solid var(--border); ... }
  .btn-section:hover { background: var(--accent); color: #fff; }
  ```

  **Shared layout classes:**
  ```css
  .section-card  { background: var(--surface-1); border: 1px solid var(--border);
                   border-radius: 10px; padding: 1.5rem; margin-bottom: 1.5rem; }
  .page-header   { display: flex; align-items: center; justify-content: space-between;
                   margin-bottom: 1.5rem; gap: 1rem; flex-wrap: wrap; }
  .section-title  { font-size: 1rem; font-weight: 600; color: var(--text-primary); }
  .section-helper { font-size: 0.8rem; color: var(--text-muted); margin-top: 0.25rem; }
  .meta          { font-size: 0.8rem; color: var(--text-muted); }
  .nav-actions   { margin-left: auto; display: flex; align-items: center; gap: 0.75rem; }
  ```

  **Badge classes migrated to tokens:**
  ```css
  .badge-succeeded { background: var(--badge-success-bg); color: var(--badge-success-fg); }
  .badge-failed    { background: var(--badge-error-bg);   color: var(--badge-error-fg);   }
  /* … all variants */
  .badge-error     { background: var(--badge-error-bg);   color: var(--badge-error-fg);   }
  ```

- [x] **Step 1.3: Add theme toggle button inside a `.nav-actions` div in `<nav>`**

  No inline styles. Nav toggle uses `.btn-secondary`:
  ```html
  <div class="nav-actions">
    <button class="btn-secondary" id="theme-toggle" aria-label="Toggle theme"
            onclick="toggleTheme()">
      <span id="theme-icon">☀️</span> <span id="theme-label">Light</span>
    </button>
  </div>
  ```

- [x] **Step 1.4: Add theme toggle script at end of `<body>`**

  ```html
  <script>
  function applyTheme(t) {
    document.documentElement.setAttribute('data-theme', t);
    localStorage.setItem('fitcv-theme', t);
    var icon = document.getElementById('theme-icon');
    var label = document.getElementById('theme-label');
    if (icon && label) {
      icon.textContent  = t === 'dark' ? '☀️' : '🌙';
      label.textContent = t === 'dark' ? 'Light' : 'Dark';
    }
  }
  function toggleTheme() {
    applyTheme(
      document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark'
    );
  }
  applyTheme(document.documentElement.getAttribute('data-theme') || 'dark');
  </script>
  ```

---

## Task 2: Settings — backend: `SETTINGS_SECTIONS` registry and section-save endpoint

### `src/fitcv_cp/settings_schema.py`

- [x] **Step 2.1: Add `SETTINGS_SECTIONS` registry**

  Modelled on `RANKING_GROUPS`. Maps section slug → ordered list of schema keys:
  ```python
  SETTINGS_SECTIONS: dict[str, list[str]] = {
      "retrieval": [
          "retrieval.top_n",
          "retrieval.search_radius_km",
          # … all retrieval keys
      ],
      "timing": [
          "timing.max_age_days",
          # … all timing keys
      ],
      "global-job-filters": [
          "global_job_filters.applications_count_max",
          "global_job_filters.max_age_days",
      ],
  }
  ```

  Determine exact keys by iterating `SETTINGS_SCHEMA` for each group.

- [x] **Step 2.2: Add `SETTINGS_SECTIONS` to module public API**

### `src/fitcv_cp/app.py`

- [x] **Step 2.3: Import `SETTINGS_SECTIONS`**

- [x] **Step 2.4: Add `POST /admin/settings/section/{section_name}` route**

  Modelled on the existing group route. Key differences from the group route:
  - Uses `SETTINGS_SECTIONS` not `RANKING_GROUPS`
  - No cross-key constraints for these sections — validates each key independently via `validate_settings({key: value})`
  - Saves the entire section as a batch via `save_settings_group()`
  - Returns 422 on any validation error, 303 redirect on success

  ```python
  @app.post("/admin/settings/section/{section_name}")
  async def admin_settings_section_save(section_name: str, ...):
      if section_name not in SETTINGS_SECTIONS:
          raise HTTPException(status_code=404)
      keys = SETTINGS_SECTIONS[section_name]
      payload: dict[str, Any] = {}
      errors: dict[str, str] = {}
      for key in keys:
          raw = form.get(key)
          if raw is None:
              continue
          try:
              coerced = float(raw)  # all current section settings are numeric
              error_msg = validate_settings({key: coerced})
              if error_msg:
                  errors[key] = error_msg
              else:
                  payload[key] = coerced
          except (ValueError, TypeError):
              errors[key] = f"Invalid value: {raw!r}"
      if errors:
          # Re-render settings page with inline errors
          return templates.TemplateResponse(
              request=request, name="settings.html",
              context={..., "section_errors": errors, "section_draft": form},
              status_code=422
          )
      save_settings_group(payload, bq, project=project, dataset=dataset)
      return RedirectResponse(url="/admin/settings", status_code=303)
  ```

---

## Task 3: Settings — template: section-form pattern

**File:** `src/fitcv_cp/templates/settings.html`

- [x] **Step 3.1: Rewrite the per-row `{% for group in groups %}` loop as section-level forms**

  Replace the current per-row form pattern with one `<form>` per section, posting to `/admin/settings/section/{section_slug}`:
  ```html
  {% for section_slug, section_label in [
      ("retrieval",          "Retrieval Settings"),
      ("timing",             "Timing Settings"),
      ("global-job-filters", "Global Job Filters"),
  ] %}
  <div class="section-card">
    <div class="page-header">
      <div>
        <div class="section-title">{{ section_label }}</div>
      </div>
    </div>
    <form method="post" action="/admin/settings/section/{{ section_slug }}">
      <table>
        <thead>...</thead>
        <tbody>
          {% for entry in schema if entry.group == section_slug.replace('-', '_') %}
          <tr>
            <td>
              <div class="section-title">{{ entry.label }}</div>
              <div class="section-helper">{{ entry.description }}</div>
            </td>
            <td class="meta">{{ active.get(entry.key, '—') }}</td>
            <td class="meta">{{ entry.default }}</td>
            <td>
              <input type="number" name="{{ entry.key }}" step="any"
                     value="{{ section_draft[entry.key] if section_draft else active.get(entry.key, entry.default) }}">
              {% if section_errors and entry.key in section_errors %}
              <p class="field-error">{{ section_errors[entry.key] }}</p>
              {% endif %}
            </td>
          </tr>
          {% endfor %}
        </tbody>
      </table>
      <div class="section-actions">
        <button type="submit" class="btn-primary">Save {{ section_label }}</button>
      </div>
    </form>
  </div>
  {% endfor %}
  ```

- [x] **Step 3.2: Fix ranking section heading — change `ranking` to `Ranking`**

  Replace raw `<h2>ranking</h2>` with `<div class="section-title">Ranking</div>`.

- [x] **Step 3.3: Migrate grouped ranking save buttons to `.btn-primary`**

  Replace inline `bg-blue-600` / `bg-indigo-600` class strings on the three ranking group save buttons with `class="btn-primary"`.

- [x] **Step 3.4: Replace all Tailwind-style classes and inline hex with shared classes**

  No Tailwind or inline hex colors should remain. Add any missing shared helpers to `base.html` first, then reuse them in the template. Expected shared helpers include:
  - `.section-actions` for footer-aligned section buttons
  - `.field-error` for inline validation messages
  - `.current-value` / `.empty-value` if needed for active vs missing values

  Use `.section-card`, `.section-title`, `.section-helper`, `.meta`, `.field-error`, `.btn-*`, and shared table classes throughout.

---

## Task 4: Migrate `runs_list.html` and `run_detail.html`

### `runs_list.html`

- [x] **Step 4.1: Remove page-local `<style>` block (`.mode-btn`)**

  Replace `.mode-btn` / `.mode-btn-active` with `.btn-secondary` and a `data-active` variant or a `[aria-selected="true"]` input class. Add to `base.html` if needed:
  ```css
  .btn-secondary[data-active="true"] {
    background: var(--surface-1); border-color: var(--accent);
    color: var(--accent); font-weight: 600;
  }
  ```

- [x] **Step 4.2: Replace all inline hex colors and Tailwind classes with shared classes**

  - "Trigger Run" button → `class="btn-primary"`
  - "Refresh Status" → `class="btn-secondary"`
  - Status badge colors → `class="badge badge-*"`
  - `.meta` for timestamps, job counts

### `run_detail.html`

- [x] **Step 4.3: Remove any page-local `<style>` block**

- [x] **Step 4.4: Replace inline hex in card/section wrappers with `.section-card`**

- [x] **Step 4.5: Replace inline reject-reason colors with shared classes**

  The pre-enrichment rejects section currently uses inline reject colors. Replace them with shared primitives such as `.badge badge-error`, `.field-error`, `.meta`, or a dedicated shared helper added to `base.html`. Do not introduce new inline token references in page templates.

---

## Task 5: Tests

### `tests/test_fitcv_cp/test_settings_schema.py`

- [x] **Step 5.1: `SETTINGS_SECTIONS` registry integrity**

  - Each section slug is present
  - Every key in each section exists in `SETTINGS_SCHEMA`
  - No key appears in more than one section

### `tests/test_fitcv_cp/test_app.py`

- [x] **Step 5.2: `POST /admin/settings/section/retrieval` — valid payload redirects 303**

- [x] **Step 5.3: `POST /admin/settings/section/retrieval` — unknown section returns 404**

- [x] **Step 5.4: `POST /admin/settings/section/retrieval` — invalid value returns 422 with section_errors**

- [x] **Step 5.5: `GET /admin/settings` renders section-level save actions for independent sections**

  Assert the page contains:
  - `Save Retrieval Settings`
  - `Save Timing Settings`
  - `Save Global Job Filters`

  And no longer renders repeated standalone row-save buttons for those sections.

---

## Task 6: Verification

- [x] **Step 6.1: Run full test suite**

  ```bash
  /tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
  ```

  Result: **421 passed**, 2 pre-existing `test_enrich` failures unrelated to this work.

- [x] **Step 6.2: Dark theme visual check** — confirmed via screenshots

- [x] **Step 6.3: Light theme visual check** — confirmed via screenshots

- [x] **Step 6.4: No-flash reload test** — inline script confirmed first in `<head>` via curl

- [ ] **Step 6.5: Keyboard focus check** *(spec requirement)*

  Tab through all interactive elements on Settings and Run Detail. Confirm focus-visible ring is visible in both dark and light themes.

- [ ] **Step 6.6: Narrow viewport check** *(spec requirement)*

  Reduce browser width to ~768px. Confirm:
  - Section headers and action rows wrap cleanly (no overlapping controls)
  - Wide tables overflow horizontally rather than collapsing

- [x] **Step 6.7: Commit**

  Committed as `fffe62c` on `feat/admin-control-plane`. Additional fix committed: section save buttons changed from `.btn-section` to `.btn-primary` for visual consistency with ranking group saves.

---

## Important Notes

- **No inline styles in new code.** All color, spacing, and button patterns are defined in `base.html`. If a template needs a new common layout or state pattern, add a shared class to `base.html` first instead of using `style=""`.
- **Section endpoints reuse `save_settings_group`** from `settings_store.py` — no new BQ logic needed.
- **`global_job_filters` → `global-job-filters` slug:** The section route slug uses hyphens, but `entry.group` in the schema uses underscores. The template uses `section_slug.replace('-', '_')` to filter schema entries correctly.
- **No-flash guarantee:** The inline theme script must be the first element in `<head>`, before `<style>`, so it runs before any rendering.
- **`focus-visible` over `focus`:** Use `*:focus-visible` to avoid unwanted focus rings on mouse clicks while keeping them visible for keyboard navigation.
