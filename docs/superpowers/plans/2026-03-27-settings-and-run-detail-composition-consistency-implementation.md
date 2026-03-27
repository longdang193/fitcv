# Settings and Run Detail Composition Consistency — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the settings page Ranking section and run-detail inspection area so they use the shared sub-card and attached-tab inspection-card composition primitives defined in `base.html`, replacing page-local border/spacing hacks and visual detaching.

**Spec:** `docs/superpowers/specs/2026-03-27-settings-and-run-detail-composition-consistency-design.md`

**Prev Plans:**
- `docs/superpowers/plans/2026-03-26-ranking-settings-grouped-forms-implementation.md` — grouped editing logic already done (backend, grouped-save, section-form)
- `docs/superpowers/plans/2026-03-26-admin-ui-consistency-and-theme-toggle-implementation.md` — section-card, btn-*, badge-*, theme toggle already done
- `docs/superpowers/plans/2026-03-26-run-detail-inspection-tabs-implementation.md` — tab structure already done (tab bar + three panes), but uses page-local border/spacing

**Resolved decisions:**
- This plan is purely **template/CSS** — no backend changes needed; `RANKING_GROUPS`, `save_settings_group`, and tab JS already exist.
- **Sub-card vs. new component:** The three ranking groups use `.sub-card` (grouped sibling forms inside a parent section-card). The run-detail uses `.inspection-card` (attached-tab inspection pattern). Both patterns live in `base.html`.
- **No new section-card wrappers** — existing top-level section-card structure for Ranking stays; only its interior changes.
- **DRY rule:** No inline border/radius tweaks are added. Any missing shared helpers go into `base.html` first.

---

## File Map

- **Modify:** `src/fitcv_cp/templates/base.html` — add `.sub-card`, `.sub-card-*`, `.inspection-card`, `.tab-bar--attached`, `.pane-container`, `.pane-container .card { padding: 0; border: none; }` shared styles
- **Modify:** `src/fitcv_cp/templates/settings.html` — replace merged ranking block with three `.sub-card` siblings; migrate inline styles to shared classes
- **Modify:** `src/fitcv_cp/templates/run_detail.html` — wrap tab bar + 3 panes in `.inspection-card`; swap to `.tab-bar--attached` + `.pane-container`; `pre_enrichment_rejects` and Event Timeline stay outside the card; `.enr-table th` sticky `<style>` block (lines 371–378) is intentionally left as-is
- **Modify:** `tests/test_fitcv_cp/test_app.py` — add consistency assertions using structural/proximity checks, not exact class-string matches

---

## Task 1: Audit `base.html` — inventory existing composition primitives

**File:** `src/fitcv_cp/templates/base.html`

Read the file and document in your working notes (not in the template):

- Which shared classes already exist and their exact properties (`.section-card`, `.tab-bar`, `.tab-pane`, `.kv`, etc.)
- Where new CSS will be inserted (after which existing block)

---

## Task 2: Add shared sub-card CSS to `base.html`

**File:** `src/fitcv_cp/templates/base.html`

Add after the existing `.section-card` block:

```css
/* ── Sub-card (grouped sibling forms inside a section-card) ──────────────────── */
/* Used by the three ranking groups inside the Ranking section.                  */
.sub-card {
  border: 1px solid var(--border);
  border-radius: 8px;
  background: var(--surface-1);
  margin-bottom: 1rem;          /* consistent spacing between siblings */
  overflow: hidden;
}
/* Last sub-card in a group: no bottom margin (flush with section bottom) */
.sub-card:last-child {
  margin-bottom: 0;
}
.sub-card-header {
  padding: 0.75rem 1rem 0;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.5rem;
}
.sub-card-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: var(--text-primary);
}
.sub-card-helper {
  font-size: 0.75rem;
  color: var(--text-muted);
  margin-top: 0.2rem;
}
.sub-card-body {
  padding: 0.75rem 1rem;
}
/* Pairs label + value in a row (scoped to sub-card internals — does not
   override the existing .kv shared rule used by run-detail metadata grids) */
.sub-card .kv { display: grid; grid-template-columns: 12rem 1fr; gap: 0.25rem 0.5rem; font-size: 0.8rem; }
.sub-card-footer {
  padding: 0.75rem 1rem;
  border-top: 1px solid var(--border-soft);
  display: flex;
  justify-content: flex-end;   /* save button footer-right */
  gap: 0.5rem;
}
```

---

## Task 3: Add shared attached-tab inspection-card CSS to `base.html`

**File:** `src/fitcv_cp/templates/base.html`

Add after the sub-card block:

```css
/* ── Inspection card with attached tab bar ───────────────────────────────────── */
/* Used by the run-detail inspection area.                                      */
/* One shared container for tab bar + pane body.                                 */
.inspection-card {
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-1);
  overflow: hidden;
  margin-bottom: 1.5rem;
}

/* Tab bar sits flush on the top edge of the inspection card.                    */
.tab-bar--attached {
  display: flex;
  align-items: center;
  gap: 0;
  border-bottom: 1px solid var(--border);
  background: var(--surface-1);
  padding: 0 0.75rem;
}
.tab-bar--attached .tab-btn {
  padding: 0.6rem 1rem;
  font-size: 0.85rem;
  color: var(--text-secondary);
  background: transparent;
  border: none;
  border-bottom: 2px solid transparent;
  cursor: pointer;
  transition: color 0.15s, border-color 0.15s;
  margin-bottom: -1px;    /* overlaps the card top border */
}
.tab-bar--attached .tab-btn:hover {
  color: var(--text-primary);
}
.tab-bar--attached .tab-btn.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
  font-weight: 600;
}

/* Pane container — one consistent border/radius/padding for all three panes.  */
.pane-container {
  border: none;          /* border is on .inspection-card, not here */
  border-top: none;      /* no double-border at attachment edge */
  background: var(--surface-1);
  padding: 1rem;
}
/* Default: hidden; .active: shown */
.pane-container.tab-pane {
  display: none;
}
.pane-container.tab-pane.active {
  display: block;
}
```

---

## Task 4: Refactor `settings.html` — Ranking section into three sibling sub-cards

**File:** `src/fitcv_cp/templates/settings.html`

- [ ] **Step 4.1: Read the current ranking section**

  Find the current merged ranking block (three `{% for entry in schema %}` loops). Note which inline styles and Tailwind classes it still uses after the admin-ui-consistency plan.

- [ ] **Step 4.2: Wrap the existing three-group content in a shared sub-card structure**

  Replace the merged block with three `.sub-card` siblings inside the outer `.section-card`:

  ```html
  <!-- ── Ranking Weights ─────────────────────────────────────────────────── -->
  <div class="sub-card">
    <div class="sub-card-header">
      <div>
        <div class="sub-card-title">Ranking Weights</div>
        <div class="sub-card-helper">Weights must sum to 1.0</div>
      </div>
    </div>
    <div class="sub-card-body">
      <!-- existing weights table/form (keep inputs, labels, error areas unchanged) -->
    </div>
    <div class="sub-card-footer">
      <button type="submit" form="form-ranking-weights" class="btn-section">Save Ranking Weights</button>
    </div>
  </div>

  <!-- ── Fit Label Thresholds ───────────────────────────────────────────── -->
  <div class="sub-card">
    <div class="sub-card-header">
      <div>
        <div class="sub-card-title">Fit Label Thresholds</div>
        <div class="sub-card-helper">strong must be &gt; stretch</div>
      </div>
    </div>
    <div class="sub-card-body">
      <!-- existing fit-label form -->
    </div>
    <div class="sub-card-footer">
      <button type="submit" form="form-fit-label-thresholds" class="btn-section">Save Fit Label Thresholds</button>
    </div>
  </div>

  <!-- ── Gap Thresholds ─────────────────────────────────────────────────── -->
  <div class="sub-card">
    <div class="sub-card-header">
      <div>
        <div class="sub-card-title">Gap Thresholds</div>
        <div class="sub-card-helper">Minimum matched ratios</div>
      </div>
    </div>
    <div class="sub-card-body">
      <!-- existing gap-thresholds form -->
    </div>
    <div class="sub-card-footer">
      <button type="submit" form="form-gap-thresholds" class="btn-section">Save Gap Thresholds</button>
    </div>
  </div>
  ```

- [ ] **Step 4.3: Give each existing ranking subgroup `<form>` a matching `id`**

  Each subgroup form already posts to `/admin/settings/group/{slug}`. Give it `id="form-ranking-weights"`, `id="form-fit-label-thresholds"`, `id="form-gap-thresholds"` so the footer `<button type="submit" form="...">` can submit it from outside the `<form>`.

- [ ] **Step 4.4: Migrate any remaining Tailwind classes and inline hex in the ranking section**

  Replace Tailwind color classes (e.g., `text-gray-400`, `bg-slate-800`) with `.sub-card-*` shared classes or existing helpers (`.meta`, `.text-muted`). No new inline `style=""` attributes.

- [ ] **Step 4.5: Verify the outer Ranking `.section-card` still wraps the three sub-cards**

  The outer `<div class="section-card">` (added in the admin-ui-consistency plan) must remain. Sub-cards are its direct children.

---

## Task 5: Refactor `run_detail.html` — wrap inspection area in shared inspection-card

**File:** `src/fitcv_cp/templates/run_detail.html`

- [ ] **Step 5.1: Read current inspection area structure**

  Find the current tab-bar and tab-pane HTML (added in the run-detail-inspection-tabs plan). Note which inline styles, Tailwind classes, or page-local CSS rules remain on `.tab-bar`, `.tab-pane`, and their containers.

- [ ] **Step 5.2: Wrap the inspection area in `.inspection-card`**

  Wrap **only** the tab bar + all three tab panes in one `.inspection-card`. The `pre_enrichment_rejects` section (a separate `.section-card`-classed block that shows summary stats for rejected jobs) stays **outside** `.inspection-card` — it is not a tab pane. It renders after pane 1 but before pane 2 in source order and is always visible regardless of active tab.

  Exact boundary: the `.inspection-card` opens **before** line 94 (`<div class="tab-bar">`) and closes **after** line 300 (`</div><!-- Tab 3 -->`). Everything from `<!-- ── Inspection Tab Bar -->` through the end of `<!-- ── Tab 3: Candidate Profile -->` goes inside.

  The `pre_enrichment_rejects` block (lines 197–223 in the current template) and the Event Timeline (lines 302–327) remain **outside** `.inspection-card`. The Event Timeline always renders below all tabs regardless of which tab is active.

  ```html
  <div class="inspection-card">
    <!-- ── Inspection Tab Bar ── -->
    <div class="tab-bar--attached">
      ...
    </div>

    <!-- ── Tab 1: Enriched Jobs ── -->
    <div class="pane-container tab-pane active" id="pane-enriched">
      ...
    </div>

    <!-- ── Tab 2: Original Job Input ── -->
    <div class="pane-container tab-pane" id="pane-jobs-input">
      ...
    </div>

    <!-- ── Tab 3: Candidate Profile ── -->
    <div class="pane-container tab-pane" id="pane-profile">
      ...
    </div>
  </div><!-- /.inspection-card -->

  <!-- pre_enrichment_rejects — always visible, outside inspection card -->
  {% if pre_enrichment_rejects %}
  <div class="section-card" style="margin:1.5rem 0">
    ...
  </div>
  {% endif %}

  <!-- Event Timeline — always visible, outside inspection card -->
  <h2>Event Timeline</h2>
  ...
  ```

- [ ] **Step 5.3: Replace `.tab-bar` class with `.tab-bar--attached`**

  ```html
  <div class="tab-bar--attached">
    <button class="tab-btn active" ...>Enriched Jobs</button>
    <button class="tab-btn"        ...>Original Job Input</button>
    <button class="tab-btn"        ...>Candidate Profile</button>
  </div>
  ```

- [ ] **Step 5.4: Replace `.tab-pane` class on pane wrappers with `.pane-container tab-pane`**

  Each pane's opening `<div>` changes from `class="tab-pane active"` to:

  ```html
  <div class="pane-container tab-pane active" id="pane-enriched">
  ```

  And from `class="tab-pane"` to:

  ```html
  <div class="pane-container tab-pane" id="pane-jobs-input">
  <div class="pane-container tab-pane" id="pane-profile">
  ```

- [ ] **Step 5.5: Remove page-local `<style>` block for tabs if present**

  If `run_detail.html` contains a `<style>` block defining `.tab-bar`, `.tab-btn`, `.tab-pane`, or `.active`, remove it. All styles now come from `.tab-bar--attached` and `.pane-container` in `base.html`.

- [ ] **Step 5.6: Migrate any remaining inline styles on tab bar or pane containers**

  Replace inline `style="..."` on the tab bar and pane wrappers with shared classes from `base.html` or CSS variables. Use `background: var(--surface-1)` instead of inline hex.

---

## Task 6: Tests — consistency assertions

**File:** `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 6.1: Settings page — no Tailwind classes in rendered ranking section**

  Render settings page, find the ranking section, assert none of these Tailwind strings appear:
  `text-gray-`, `bg-slate-`, `bg-indigo-`, `text-indigo-`, `rounded-`, `px-`, `py-`

- [ ] **Step 6.2: Settings page — ranking section contains three `.sub-card` elements**

  Assert the rendered HTML contains at least three occurrences of `class="sub-card"`. Use a count assertion (`html.count('class="sub-card"') >= 3`) rather than a substring equality check.

- [ ] **Step 6.3: Settings page — each sub-card has a save button with the correct form target**

  For each of the three ranking subgroup form IDs (`form-ranking-weights`, `form-fit-label-thresholds`, `form-gap-thresholds`), assert a `<button type="submit" form="form-id">` exists within the corresponding `.sub-card` in the rendered HTML. Use structural lookups (substring match on `form="form-..."`) rather than fragile exact-class-string comparisons.

- [ ] **Step 6.4: Run detail — inspection area wrapped in `.inspection-card`**

  Render run detail page. Assert `class="inspection-card"` is present **and** that `id="tab-btn-enriched"` (first tab button) appears somewhere after the `.inspection-card` opening tag in the rendered HTML. This proves the tab bar is inside the card, not just somewhere on the page.

- [ ] **Step 6.5: Run detail — tab bar uses `.tab-bar--attached`**

  Assert `tab-bar--attached` is present in the rendered HTML. Also assert the detached class `tab-bar` (without `--attached`) does **not** appear as a standalone class token in the inspection area. Use a regex or token-level check rather than `in` on the full raw HTML string to avoid false positives from CSS in `<style>` blocks.

- [ ] **Step 6.6: Run detail — panes use `.pane-container`**

  Assert each of `id="pane-enriched"`, `id="pane-jobs-input"`, and `id="pane-profile"` appears in the rendered HTML and that `pane-container` appears in the same context (within ~200 chars before or after each pane ID). Structural proximity checks are more robust than exact substring matching on the raw HTML.

- [ ] **Step 6.7: Run detail — no tab-related page-local `<style>` blocks**

  Render run detail. Find the character offset of the first `.inspection-card` open tag. Assert that no `<style>` tag appears **before** the first tab button (`id="tab-btn-enriched"`). This catches regressions where tab styling gets re-introduced as a page-local block inside the inspection area.

---

## Task 7: Verify and commit

- [ ] **Step 7.1: Run full test suite**

  ```bash
  pytest -q --tb=short -m "not integration"
  ```

  Expected: all existing tests pass + new consistency assertions pass.

- [ ] **Step 7.2: Manual verification — settings page**

  1. Open settings page, scroll to Ranking section
  2. Confirm Ranking appears as one section-card with three clearly separated sibling sub-cards
  3. Confirm each sub-card has its own header, body, and footer save button
  4. Confirm no Tailwind classes visible in Ranking area
  5. Confirm dark/light themes both look consistent

- [ ] **Step 7.3: Manual verification — run detail**

  1. Open any run detail page
  2. Confirm the tab bar sits flush on the top of one inspection card
  3. Confirm all three panes share the same border, radius, and padding
  4. Confirm the Event Timeline is outside the inspection card
  5. Confirm dark/light themes both look consistent

- [ ] **Step 7.4: Commit**

  ```bash
  git add src/fitcv_cp/templates/base.html \
         src/fitcv_cp/templates/settings.html \
         src/fitcv_cp/templates/run_detail.html \
         tests/test_fitcv_cp/test_app.py
  git commit -m "feat(ui): composition consistency — shared sub-card and inspection-card patterns"
  ```

---

## Important Notes

- **No backend changes.** All changes are template/CSS. The grouped editing logic (from `2026-03-26-ranking-settings-grouped-forms`) and tab structure (from `2026-03-26-run-detail-inspection-tabs`) are already done.
- **DRY enforcement:** If you find yourself wanting to add `style="..."` or a Tailwind class in `settings.html` or `run_detail.html`, stop — add the missing shared class to `base.html` first, then use it.
- **Sub-card vs. section-card:** `.section-card` is for top-level settings sections. `.sub-card` is for grouped sibling forms inside a section. The Ranking section is one `.section-card` containing three `.sub-card` siblings.
- **Anti-regression:** The admin-ui-consistency plan (commit `fffe62c`) already removed most Tailwind. This plan closes the remaining gaps specifically in the Ranking section and run-detail inspection area.
- **`.tab-bar--attached` replaces `.tab-bar`:** The existing `base.html` defines `.tab-bar`, `.tab-btn`, and `.tab-pane` (lines 286–299). These are the detached style. `.tab-bar--attached` is a separate CSS rule with different border/attachment behavior. Elements that receive `.tab-bar--attached` will not pick up the old `.tab-bar` properties — that is the intent. No conflict; just a deliberate replacement.
- **`.pane-container` vs. existing `.card` padding inside panes:** Each tab pane in `run_detail.html` wraps content in `<div class="card">` (e.g., lines 228, 236, 252, 283). `.card` carries `padding: 1.5rem` from `base.html`. Adding `.pane-container` (which also has `padding: 1rem`) will cause double-padding unless addressed. Two solutions, pick one:
  1. Keep `<div class="card">` inside panes, suppress its padding: add `.pane-container .card { padding: 0; border: none; }` to `base.html` alongside the `.pane-container` rule.
  2. Remove `<div class="card">` wrappers from inside tab panes (the pane itself provides the container padding). This is cleaner but changes the pane-content HTML structure more.
  Either approach works; the implementer decides based on what looks right visually. Both are valid as long as there is no double-padding artifact.
- **`pre_enrichment_rejects` stays outside `.inspection-card`:** This block (lines 197–223 of the current `run_detail.html`) is a collapsible summary table of jobs rejected before enrichment. It is not a tab pane and must remain always-visible, outside the inspection card. Step 5.2 shows the exact boundary.
- **Existing `.enr-table th` sticky style block stays:** The `<style>.enr-table th { position: sticky; top: 0; ... }` block (lines 371–378) is an existing `<style>` tag that has nothing to do with tab styling — it keeps the enriched table headers sticky during scroll. It is intentionally left in place and is not covered by the "no page-local tab styles" rule.
