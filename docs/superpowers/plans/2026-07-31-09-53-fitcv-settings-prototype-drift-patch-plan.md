---
layer: change
artifact_type: plan
status: proposed
execution_status: completed
template_id: implementation-plan
name: fitcv-settings-prototype-drift-patch
parent_spec: docs/superpowers/specs/2026-07-22-16-31-fitcv-packaged-local-complete-frontend-backend-integration-spec.md
targets:
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/settings.html
  - tests/test_fitcv_cp/test_local_routes.py
  - docs/superpowers/plans/audit/20260731-0943-fitcv-settings-prototype-drift/report.md
---

# FitCV Settings Prototype Drift Patch Plan

## Goal

Restore Pipeline Settings visual hierarchy and interaction symmetry with
`docs/fitcv-settings-ui-prototype.html` while preserving existing real URLs,
server-owned `pipeline_settings_projection(...)`, revision-safe
`PATCH /settings/pipeline`, packaged-local security, and progressive Jinja
rendering.

Bounded scope:

- remove duplicate horizontal Pipeline navigation; sidebar remains sole section navigation
- render direct settings with native prototype controls instead of `<code>` value badges
- keep grouped settings transactional through one centered native dialog
- restore prototype shell/page heading ownership and component spacing
- add focused production-template regressions and browser verification evidence
- do not change settings schema, persistence, API request/response contracts, routes, or prototype source

Approved patch decisions:

- direct boolean, membership, integer, and float controls save immediately through the canonical Pipeline PATCH endpoint
- global shell header remains `Pipeline`; active section remains visible in page content as an `h2`
- all mutable Pipeline controls share one in-flight mutation lock because they share one resource revision
- every `dialog.workspace-dialog` is intrinsically centered; Pipeline-only geometry remains separately scoped

## Implementation Outcomes

### One navigation and heading hierarchy

Pipeline sidebar links remain the only section navigation. Global header shows
`Pipeline` plus its shared description; page content uses prototype-style
`page-head` with the active section as an `h2`. No horizontal `workspace-tabs`
bar or duplicate page-level `h1` remains.

### Schema projection rendered through prototype-native components

`settings.html` continues consuming `pipeline_resource` and
`pipeline_page` from existing backend owners. Direct booleans and memberships
render checkbox-backed switches, direct integers/floats render bounded native
number inputs, managed groups retain Manage buttons and transaction summaries,
and readonly/mirror rows retain non-editable values. No second frontend schema
or state registry is introduced.

### Revision-safe direct and grouped mutations

Direct controls save one canonical change through existing
`PATCH /settings/pipeline`, disable all mutable Pipeline controls while pending,
restore server-owned value on failure, expose an inline status, and reload on
`settings_revision_conflict`. Managed groups keep Save/Cancel semantics and
submit all group fields atomically through the same endpoint and revision.

### Centered accessible dialog and durable parity proof

Pipeline Manage dialog uses approved prototype header, form, status, and action
regions. Shared `.workspace-dialog` centering is restored as the invariant for
all existing consumers; Pipeline-specific geometry remains scoped. Focus enters the
first field, Escape and Cancel close without saving, and focus returns to the
invoking Manage button. Focused tests and browser evidence prevent recurrence.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-using-git-worktrees`, `skill-executing-plans`, `skill-test-driven-development`, `skill-frontend-component-engineering`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: create `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-settings-prototype-drift-patch` on branch `codex/fitcv-settings-prototype-drift-patch` from current `main`; copy this uncommitted plan and its audit report into the same relative paths in the lane before source edits, then make the lane copies canonical for execution
- Parallel ownership: none; `base.html` and `settings.html` share component contracts and require one sequential owner
- Sequential fallback: regression tests, Settings renderer, shared CSS, browser verification, audit closeout

## Task Breakdown

### Task 1: Lock production component regressions

**Purpose:**
- make confirmed navigation, control, heading, and dialog drift fail before runtime edits

**Specification Coverage:**
- prototype remains approved visual hierarchy and interaction reference
- one shell owner, semantic controls, no duplicate frontend implementation
- audit findings 1 through 6 in `20260731-0943-fitcv-settings-prototype-drift`

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html:rowMarkup`
- Inspect: `docs/fitcv-settings-ui-prototype.html:openTransaction`
- Modify: `tests/test_fitcv_cp/test_local_routes.py:test_pipeline_section_urls_render_server_owned_settings`
- Create in existing file: `tests/test_fitcv_cp/test_local_routes.py:test_pipeline_settings_render_prototype_component_contract`

**Dependencies:**
- local-mode TestClient fixture remains canonical server-rendered page proof
- existing PATCH endpoint tests remain authoritative for validation and revision conflicts

**Steps:**
- [x] Step 1: assert `/admin/settings/cv-analysis` contains no `workspace-tabs` or `Pipeline settings sections` navigation because sidebar already owns these links
- [x] Step 1a: extend the existing section-route loop to assert exactly one matching sidebar link has `aria-current="page"` for every Pipeline Settings URL
- [x] Step 2: assert Settings main metadata supplies global header title `Pipeline`, content renders active page as `h2`, and Settings content contains no page-level `h1`
- [x] Step 3: assert Semantic Alignment renders a checked checkbox inside `.switch` with stable `data-setting-key`, not `<code>Enabled</code>`
- [x] Step 4: assert direct numeric controls render native `type="number"` inputs with projection-owned `min`, `max`, and `step` attributes
- [x] Step 5: assert managed rows expose one transaction summary and Manage button while readonly/mirror rows remain non-editable
- [x] Step 6: assert Pipeline dialog contains `.dialog-head`, `.weight-form`, `.weight-status`, `.dialog-actions`, close control, and accessible title/description references

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_local_routes.py -k "pipeline_settings or pipeline_section" -q`
- Expected: new assertions fail against current generic renderer and pass only after Tasks 2-3

**Exit Criteria:**
- tests name each confirmed production drift without testing prototype-local implementation details

### Task 2: Restore prototype-native Settings renderer

**Purpose:**
- adapt existing schema projection into approved controls without changing backend ownership

**Specification Coverage:**
- one backend owner per setting
- native semantic controls and progressively enhanced Jinja page
- direct-setting and transaction interaction hierarchy from prototype

**Required Skills:**
- `skill-frontend-component-engineering`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/settings_schema.py:pipeline_settings_projection`
- Inspect: `src/fitcv_cp/app.py:_pipeline_settings_resource`
- Inspect: `src/fitcv_cp/app.py:patch_pipeline_settings`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_local_routes.py`

**Dependencies:**
- Task 1 failing component tests exist
- `pipeline_settings_projection(...)` already provides all required direct and managed field types and native input attributes

**Steps:**
- [x] Step 1: delete local-only `workspace-tabs`; keep existing `base.html` Pipeline sidebar links as sole navigation
- [x] Step 2: add `data-header-title="Pipeline"` and shared Pipeline description to Settings main; replace page-content `h1` header with prototype `page-head`, eyebrow, active-page `h2`, description, and Overview reset action
- [x] Step 3: render `kind=direct` booleans as labeled switches and integers/floats as labeled native number fields using projection `input_attrs`
- [x] Step 4: render `kind=membership` as a switch that patches the canonical ordered list value; render `kind=manage` with prototype transaction summary plus Manage; render mirror/readonly values with non-editable prototype classes
- [x] Step 5: add one direct-control save path using existing `fitcvApiRequest` and `patchSettings`: call `reportValidity()` before transport, acquire one page-level mutation lock, disable every mutable Pipeline control, submit one change with current revision, replace `resource` from the response, resynchronize displayed values, transaction summaries, warnings, and disabled managed rows from that returned resource, announce success, restore prior server-owned value on failure, reload on `settings_revision_conflict`, then release the lock from the canonical returned or restored resource state
- [x] Step 6: retain grouped atomic PATCH behavior, but render fields through prototype `.weight-row` and `.check-row` structures; use projection `details_groups` for nested detail navigation without creating copied schemas
- [x] Step 7: record dialog opener, close through Cancel/Escape/close button without mutation, clear transient draft/status state on close, and restore focus to opener
- [x] Step 8: keep reset behavior on existing `/settings/pipeline/actions/reset`; do not alter APIs, settings schema, persistence, or routes

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_local_routes.py -k "pipeline_settings or pipeline_section or runtime_limits" -q`
- [x] `uv run pytest tests/test_fitcv_cp/test_app.py -k "pipeline_settings or settings_revision_conflict" -q`
- Expected: production HTML exposes prototype-native components; existing API validation, reset, and revision-conflict contracts remain unchanged

**Exit Criteria:**
- every Pipeline projection row kind uses one explicit component mapping and every mutation still routes through existing canonical resource endpoint

### Task 3: Restore bounded shared component styling

**Purpose:**
- center native dialogs and supply missing prototype component styles without broad shell redesign

**Specification Coverage:**
- approved visual hierarchy, responsive layout, supported themes, focus visibility, reduced motion
- audit CSS layering and dialog-position findings

**Required Skills:**
- `ui-ux-pro-max`

**Files And Symbols:**
- Modify: `src/fitcv_cp/templates/base.html:dialog.workspace-dialog`
- Modify: `src/fitcv_cp/templates/base.html` prototype component selector block
- Verify: `src/fitcv_cp/templates/settings.html:#pipeline-manage-dialog`
- Verify: `src/fitcv_cp/templates/base.html:#shutdown-dialog`
- Inspect: every existing `dialog.workspace-dialog` consumer under `src/fitcv_cp/templates`

**Dependencies:**
- Task 2 markup and classes are final

**Steps:**
- [x] Step 1: restore `margin: auto` on shared `dialog.workspace-dialog` so the universal reset cannot pin native modal dialogs to viewport origin
- [x] Step 2: add a Pipeline-specific dialog class for approved width, zero outer padding, radius, shadow, and backdrop treatment; preserve shutdown dialog internal padding and behavior
- [x] Step 3: reuse prototype selectors for `.dialog-head`, `.dialog-close`, `.weight-form`, `.weight-row`, `.check-row`, `.weight-status`, `.dialog-actions`, `.switch`, `.track`, `.transaction-summary`, `.mirror-value`, and inline row status
- [x] Step 4: scope added selectors to existing component classes; do not rewrite tokens, add a stylesheet pipeline, or perform unrelated legacy CSS cleanup
- [x] Step 5: retain existing narrow-viewport, theme, focus-visible, and reduced-motion rules; add only missing reflow rules for dialog rows and actions
- [x] Step 6: inventory every existing `dialog.workspace-dialog` consumer, confirm none depends on top-left placement or overrides shared margin, and browser-smoke Pipeline, shutdown, and one non-Pipeline dialog after the shared centering change

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_local_routes.py -k "pipeline_settings or pipeline_section" -q`
- [x] `git diff --check -- src/fitcv_cp/templates/base.html src/fitcv_cp/templates/settings.html tests/test_fitcv_cp/test_local_routes.py`
- Expected: dialog has intrinsic centered geometry, controls match prototype classes, and unrelated shell/page markup remains unchanged

**Exit Criteria:**
- source-level component contract passes and CSS changes remain limited to reused prototype components plus native-dialog centering

### Task 4: Prove parity and close audit

**Purpose:**
- verify affected Settings pages and shared dialog behavior in production browser before claiming completion

**Specification Coverage:**
- production browser proof replaces prototype-only confidence
- accessibility, responsive, theme, keyboard, focus, and clean runtime requirements

**Required Skills:**
- `skill-verification-before-completion`
- `ui-ux-pro-max`

**Files And Symbols:**
- Verify: `/admin/settings`
- Verify: `/admin/settings/cv-analysis`
- Verify: `/admin/settings/screening`
- Verify: `/admin/settings/ranking`
- Verify: `src/fitcv_cp/templates/base.html:#shutdown-dialog`
- Modify: `docs/superpowers/plans/audit/20260731-0943-fitcv-settings-prototype-drift/report.md`

**Dependencies:**
- Tasks 1-3 complete
- FitCV Local runs through canonical `uv run fitcv-local` launcher with representative schema-4 data

**Steps:**
- [x] Step 1: verify sidebar is sole Pipeline navigation, active link is correct, shell header reads Pipeline, and active page heading remains visible as `h2`
- [x] Step 2: toggle Semantic Alignment and one Screening membership switch; confirm pending disablement, live status, persisted value after reload, and no `<code>Enabled</code>` badge
- [x] Step 3: edit one valid direct numeric field, then test one out-of-bounds value and one relationally invalid value; confirm native validity blocks the out-of-bounds PATCH, API `422` restores the relationally invalid field from canonical resource state, and unrelated page values remain unchanged
- [x] Step 4: open one managed group and nested details group; verify centered geometry, structured content, validation, Save/Cancel/Escape behavior, duplicate-submit prevention, and focus return
- [x] Step 5: open shutdown dialog and one non-Pipeline `.workspace-dialog`; confirm shared centering, padding, action semantics, and focus behavior remain correct
- [x] Step 6: repeat affected flows in light and dark themes at `1440x900`, `375x900`, and `640x900` as 200%-zoom equivalent, then repeat dialog open/close with reduced motion enabled; verify no page-level horizontal overflow, long descriptions reflow, and no transition-dependent interaction
- [x] Step 7: inspect console and network for uncaught errors, unexpected failed requests, duplicate PATCH calls, or full-page client-only rendering
- [x] Step 8: update audit Resolution and Verification with exact commands and browser evidence; set audit status resolved only after final verification passes

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_app.py -k "pipeline_settings or pipeline_section or runtime_limits or settings_revision_conflict" -q`
- [x] `uv run pytest tests/test_fitcv_pipeline_prototype.py -q`
- [x] `git diff --check`
- [x] Playwright browser verification evidence for navigation count, control roles, persistence, validation, dialog center, keyboard/focus, themes, narrow viewport, and zoom
- [x] Chrome DevTools evidence for computed dialog geometry, overflow, console, and PATCH request count/status
- Expected: prototype hierarchy and interaction intent are restored while backend contracts remain unchanged

**Exit Criteria:**
- fresh source, test, browser, and DevTools evidence closes every audit finding with no unresolved required deviation

## Verification

Execution result: verified on branch `codex/fitcv-settings-prototype-drift-patch` from base `1dec2337`. Frontmatter `status` remains `proposed` because the current repository template validator requires that literal; `execution_status` and checked tasks record completed execution without adding a validator exception.

- `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_app.py -k "pipeline_settings or pipeline_section or runtime_limits or settings_revision_conflict" -q`
- `uv run pytest tests/test_fitcv_pipeline_prototype.py -q`
- `python scripts/validate_template_required_sections.py --repo-root .`
- `git diff --check`
- production browser verification on Overview, CV Analysis, Screening, Ranking, shutdown dialog, and one non-Pipeline dialog across desktop, narrow, dark/light, keyboard, reduced-motion, and zoom states
- Chrome DevTools proof: centered modal bounds, no horizontal overflow, no console errors, and exactly one PATCH per successful setting action

Repository-wide template validation currently has unrelated pre-existing planning-artifact failures. Execution must record exact unchanged baseline and separately prove this plan and audit contain required sections.

## Completion Criteria

The plan is ready for completion verification when:

1. sidebar is sole Pipeline section navigation and active state works for every Settings URL
2. global header and page heading match prototype hierarchy without duplicate page-level `h1`
3. direct booleans, memberships, numbers, managed groups, mirrors, and readonly values each use approved native component mapping
4. direct and grouped saves use existing revision-safe Pipeline endpoint with one shared in-flight mutation lock plus visible pending, success, validation, conflict, and failure behavior
5. shared workspace dialogs center correctly; Pipeline dialog matches prototype structure and restores focus without changing unrelated dialog semantics
6. focused tests and browser evidence cover all confirmed audit drifts across themes, narrow layout, keyboard, and zoom
7. no settings schema, persistence, API, route, or prototype-source change was introduced
8. audit report contains fresh resolution evidence and no unresolved required finding
9. plan deviations, substitutions, blockers, and deferrals are recorded

The plan may be marked `completed` only when `skill-verification-before-completion`:

1. runs fresh final verification
2. confirms completion criteria against repository evidence
3. finds no unresolved required task, failed required check, stale status, or unrecorded scope deviation
4. returns `verified` and updates plan status

A checked box records progress; it is not proof by itself.
