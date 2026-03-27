# Settings and Run Detail Composition Consistency — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the settings page Ranking section and run-detail inspection area so they use the shared sub-card and attached-tab inspection-card composition primitives defined in `base.html`, replacing page-local border/spacing hacks and visual detaching.

**Spec:** `docs/superpowers/specs/2026-03-27-settings-and-run-detail-composition-consistency-design.md`

**Prev Plans:**
- `docs/superpowers/plans/2026-03-26-ranking-settings-grouped-forms-implementation.md` — grouped editing logic already done (backend, grouped-save, section-form)
- `docs/superpowers/plans/2026-03-26-admin-ui-consistency-and-theme-toggle-implementation.md` — section-card, btn-\*, badge-\*, theme toggle already done
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
- **Modify:** `src/fitcv_cp/templates/run_detail.html` — wrap tab bar + 3 panes in `.inspection-card`; swap to `.tab-bar--attached` + `.pane-container`; `pre_enrichment_rejects` and Event Timeline stay outside the card; `.enr-table th` sticky `<style>` block is intentionally left as-is
- **Modify:** `tests/test_fitcv_cp/test_app.py` — add consistency assertions using structural/proximity checks, not exact class-string matches

---

## Task 1: Audit `base.html` — inventory existing composition primitives

**File:** `src/fitcv_cp/templates/base.html`

**[COMPLETED]** — Inventory done during implementation. All existing primitives (`.section-card`, `.tab-bar`, `.tab-btn`, `.tab-pane`, `.kv`, `.card`, etc.) were confirmed in `base.html` lines 120–399 before new CSS was inserted.

---

## Task 2: Add shared sub-card CSS to `base.html`

**File:** `src/fitcv_cp/templates/base.html`

**[COMPLETED]** — `.sub-card` and all sub-card variants added to `base.html` at lines 138–180:

```css
.sub-card { ... }
.sub-card-header { ... }
.sub-card-title { ... }
.sub-card-helper { ... }
.sub-card-body { ... }
.sub-card .kv { ... }
.sub-card-footer { ... }
```

---

## Task 3: Add shared attached-tab inspection-card CSS to `base.html`

**File:** `src/fitcv_cp/templates/base.html`

**[COMPLETED]** — `.inspection-card`, `.tab-bar--attached`, `.pane-container`, and `.pane-container .card { padding: 0; border: none; }` added to `base.html` at lines 182–236.

---

## Task 4: Refactor `settings.html` — Ranking section into three sibling sub-cards

**File:** `src/fitcv_cp/templates/settings.html`

**[COMPLETED]**

- [x] **Step 4.1: Read the current ranking section**
- [x] **Step 4.2: Wrap the existing three-group content in a shared sub-card structure** — confirmed: three `.sub-card` siblings at lines 89, 148, 204
- [x] **Step 4.3: Give each existing ranking subgroup `<form>` a matching `id`** — confirmed: `id="form-ranking-weights"`, `id="form-fit-label-thresholds"`, `id="form-gap-thresholds"`
- [x] **Step 4.4: Migrate any remaining Tailwind classes and inline hex in the ranking section** — confirmed: grep shows no Tailwind in ranking section
- [x] **Step 4.5: Verify the outer Ranking `.section-card` still wraps the three sub-cards** — confirmed: outer `.section-card` present

---

## Task 5: Refactor `run_detail.html` — wrap inspection area in shared inspection-card

**File:** `src/fitcv_cp/templates/run_detail.html`

**[COMPLETED]**

- [x] **Step 5.1: Read current inspection area structure**
- [x] **Step 5.2: Wrap the inspection area in `.inspection-card`** — confirmed: opens at line 94, closes at `</div><!-- /.inspection-card -->` (line 301); `pre_enrichment_rejects` and Event Timeline remain outside
- [x] **Step 5.3: Replace `.tab-bar` class with `.tab-bar--attached`** — confirmed: line 96
- [x] **Step 5.4: Replace `.tab-pane` class on pane wrappers with `.pane-container tab-pane`** — confirmed: all three panes use `.pane-container tab-pane` (lines 103, 226, 250)
- [x] **Step 5.5: Remove page-local `<style>` block for tabs if present** — confirmed: no page-local tab styles inside `.inspection-card`
- [x] **Step 5.6: Migrate any remaining inline styles on tab bar or pane containers** — confirmed: uses shared classes only

---

## Task 6: Tests — consistency assertions

**File:** `tests/test_fitcv_cp/test_app.py`

**[COMPLETED]**

- [x] **Step 6.1: Settings page — no Tailwind classes in rendered ranking section** — `test_settings_ranking_section_has_no_tailwind_classes` (line 1130)
- [x] **Step 6.2: Settings page — ranking section contains three `.sub-card` elements** — `test_settings_ranking_section_has_three_sub_cards` (line 1145)
- [x] **Step 6.3: Settings page — each sub-card has a save button with the correct form target** — `test_settings_sub_cards_have_submit_buttons` (line 1156)
- [x] **Step 6.4: Run detail — inspection area wrapped in `.inspection-card`** — `test_run_detail_inspection_card_wraps_tab_bar` (line 1172)
- [x] **Step 6.5: Run detail — tab bar uses `.tab-bar--attached`** — `test_run_detail_tab_bar_uses_attached_modifier` (line 1201)
- [x] **Step 6.6: Run detail — panes use `.pane-container`** — `test_run_detail_panes_use_pane_container` (line 1227)
- [x] **Step 6.7: Run detail — no tab-related page-local `<style>` blocks** — `test_run_detail_no_style_tag_in_inspection_card` (line 1251)

---

## Task 7: Verify and commit

**[COMPLETED]**

- [x] **Step 7.1: Run full test suite** — all tests pass
- [x] **Step 7.2: Manual verification — settings page** — three sub-cards render correctly, no Tailwind visible, dark/light themes consistent
- [x] **Step 7.3: Manual verification — run detail** — tab bar flush on inspection card top edge, all three panes share border/radius/padding, Event Timeline outside card
- [x] **Step 7.4: Commit** — committed as `f91e0dc` and pushed to `origin/main`

---

## Resolution Notes

- **`.tab-bar--attached` replaces `.tab-bar`:** The existing `base.html` defines `.tab-bar` (detached style, lines 386–399). `.tab-bar--attached` is a separate CSS rule with different border/attachment behavior. No conflict.
- **`pre_enrichment_rejects` stays outside `.inspection-card`:** This block is a collapsible summary table of jobs rejected before enrichment. It is not a tab pane and must remain always-visible, outside the inspection card.
- **Existing `.enr-table th` sticky style block stays:** The `<style>.enr-table th { position: sticky; ... }` block keeps table headers sticky during scroll. Intentionally left in place.
- **`.pane-container .card` padding suppression:** Solution 1 was used — `.pane-container .card { padding: 0; border: none; }` added to `base.html` to prevent double-padding when pane content uses `.card` wrappers.

---

## Implementation Complete

All tasks finished. The settings Ranking section and run-detail inspection area now use the shared `.sub-card` and `.inspection-card` composition primitives from `base.html`. No page-local border/spacing hacks remain. All 7 consistency tests pass and are committed.
