---
template_id: audit-report-with-evidence
status: open
resolution_status: resolved
audit_id: 20260731-0943-fitcv-settings-prototype-drift
---

# FitCV Settings Prototype Drift Audit

## 1. Current situation

- Environment: FitCV Local at `http://127.0.0.1:59726`, repository `main` at `1dec2337`.
- Affected surface: Pipeline Settings, confirmed on `/admin/settings/cv-analysis`.
- Expected reference: `docs/fitcv-settings-ui-prototype.html`, named by the active integration specification as the approved visual hierarchy and interaction reference.
- Status: resolved in isolated worktree branch `codex/fitcv-settings-prototype-drift-patch`.

## 2. Core problem

Production Settings preserves backend values and routes but does not preserve the approved prototype component hierarchy or interaction presentation.

Confirmed user-visible drift includes:

1. a second horizontal Pipeline navigation bar duplicates the sidebar;
2. boolean settings render as textual `<code>Enabled</code>` badges plus Manage buttons instead of prototype switches;
3. Manage dialogs open at the viewport top-left instead of centered;
4. dialog content lacks the prototype header/body/action structure and spacing;
5. page title and description render twice: once in the global header and once in page content;
6. generic legacy colors, code badges, buttons, rows, and cards remain mixed with copied prototype tokens.

Impact is medium: functionality remains available, but approved UX, visual hierarchy, discoverability, and consistency are not delivered.

## 3. Evidence and reproduction

1. Start FitCV Local and open `/admin/settings/cv-analysis`.
2. Observe sidebar already contains every Pipeline section.
3. Observe main content also contains `nav.workspace-tabs` with the same sections.
4. Observe Semantic Alignment status rendered as `<code>Enabled</code>`.
5. Select Manage for Semantic Alignment.
6. Observe native dialog at viewport origin.

Live browser measurements on an `866x810` viewport:

- two `h1` elements exist;
- one duplicate `Pipeline settings sections` navigation exists in main content;
- horizontal navigation occupies `483.2x176.8` CSS pixels and inherits `padding: 0 32px`;
- open `#pipeline-manage-dialog` has `position: fixed`, `inset: 0`, `margin: 0`, and rectangle `x=0`, `y=0`, `width=680`, `height=192.5`;
- Enabled badge is a block-level `<code>` element, not a switch.

Source evidence:

- `src/fitcv_cp/templates/settings.html:10` adds the duplicate horizontal navigation.
- `src/fitcv_cp/templates/base.html:637` through `src/fitcv_cp/templates/base.html:647` already own Pipeline sidebar navigation.
- `src/fitcv_cp/templates/settings.html:16` converts every value to a `<code>` badge and adds generic Manage actions.
- `docs/fitcv-settings-ui-prototype.html:1806` renders boolean settings with native checkbox-backed switches.
- `src/fitcv_cp/templates/settings.html:22` uses a flat generic dialog form.
- `docs/fitcv-settings-ui-prototype.html:26` and `docs/fitcv-settings-ui-prototype.html:2218` define the approved centered dialog styling and structured transaction form.
- `src/fitcv_cp/templates/base.html:124` globally resets all element margins to zero, including native dialogs.
- `src/fitcv_cp/templates/base.html:585` styles dialog width and appearance but never restores `margin: auto`; the native centering margin therefore remains zero.
- `src/fitcv_cp/templates/base.html:719` copies the content heading into the global header while `src/fitcv_cp/templates/settings.html:5` leaves the source heading visible.

## 4. Root cause and boundary

Primary root cause is frontend contract replacement in commit `2ca92616` (`feat: complete packaged-local frontend-backend integration`). That commit replaced the prototype-aligned `settings.html` implementation with a 40-line generic schema renderer: `993` lines removed, `40` retained/added. Backend symmetry improved, but component and interaction symmetry were not preserved at the rendering boundary.

Contributing causes:

1. **Two navigation owners.** `base.html` owns Pipeline sidebar links while `settings.html` independently renders `pipeline_pages` as horizontal tabs. No invariant prevents duplicate navigation.
2. **Generic value renderer.** One Jinja branch serializes booleans, memberships, groups, and scalar values into code badges. It discards prototype-native control semantics instead of adapting schema data into prototype components.
3. **CSS layering conflict.** Legacy global CSS and later copied prototype CSS coexist in one template. Broad selectors such as `*` and `nav` leak into new components. Dialog centering is broken specifically by global `margin: 0` combined with incomplete dialog restoration.
4. **Header synchronization without source suppression.** JavaScript mirrors content heading into the shell header but does not remove or visually demote the original page heading.
5. **Verification gap.** Tests assert route success, headings, `data-setting-row`, labels, and backend states. Prototype tests inspect the prototype file itself. No production regression compares actual component roles, duplicate navigation, dialog geometry, switch usage, or visual hierarchy against the prototype.
6. **Acceptance closure gap.** The integration specification states the prototype remains the approved visual hierarchy and interaction reference, but completion evidence emphasized URLs, backend states, accessibility mechanics, responsive behavior, and clean console/network operation. Visual/component parity had no executable acceptance gate.

Failure boundary is `src/fitcv_cp/templates/base.html` plus `src/fitcv_cp/templates/settings.html`. Settings schema and persistence are not root causes.

## 5. Resolution and verification

Resolution applied at the audited frontend boundary:

1. deleted the duplicate `workspace-tabs` navigation and retained the sidebar as sole Pipeline section navigation;
2. adapted existing `pipeline_settings_projection(...)` rows into checkbox-backed switches, bounded native number inputs, managed transaction rows, mirrors, and readonly values without creating a frontend schema copy;
3. restored one shared in-flight mutation lock, revision-safe direct and grouped PATCH behavior, native validity, `422` rollback, conflict reload, returned-resource resynchronization, and the existing reset endpoint;
4. restored prototype heading hierarchy with global `Pipeline` `h1`, active section `h2`, and section `h3` headings;
5. restored `margin: auto` on shared `.workspace-dialog`, scoped Pipeline-only geometry, and retained existing padding and semantics for shutdown and Candidate Profile dialogs;
6. added production-template regressions for navigation ownership, heading hierarchy, switches, bounded number inputs, managed summaries, mirrors, and dialog structure.

Fresh command evidence:

- `uv run pytest tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_app.py -k "pipeline_settings or pipeline_section or runtime_limits or settings_revision_conflict" -q` — `10 passed, 442 deselected`.
- `uv run pytest tests/test_fitcv_pipeline_prototype.py -q` — `6 passed`.
- `git diff --check` — passed; only existing Windows line-ending warnings were emitted.
- `python scripts/validate_template_required_sections.py --repo-root .` — repository-wide baseline still fails on 244 historical planning artifacts; zero findings reference this patch plan.

Fresh browser evidence on isolated `http://127.0.0.1:8891` data:

- production DOM has one `h1`, one active-page `h2`, no main `workspace-tabs`, no `<code>Enabled</code>`, and no horizontal overflow;
- Semantic Alignment and Screening membership switches each persisted through one successful `PATCH /settings/pipeline` request;
- native minimum validation blocked an out-of-bounds number without a request;
- relationally invalid AI pool value returned `422` and restored canonical value `50` while preserving unrelated value `51`;
- Pipeline dialog measured `560px` wide and centered within `7.4px` horizontal scrollbar allowance and `0.3px` vertically; first field received focus;
- Cancel and Escape closed without mutation and returned focus to the invoking Manage button;
- nested `Preference Fit Balance` details rendered from projection `details_groups`;
- shutdown and Candidate Profile dialogs remained centered with original `20px` padding and focus behavior;
- layouts had no horizontal overflow at `1440x900`, `375x900`, or `640x900`; light and dark themes remained readable;
- reduced-motion equivalent transition suppression did not affect dialog open/close behavior;
- browser console contained no warnings or errors from Settings interactions; successful direct mutations produced exactly one PATCH each.

## 6. Risk and next steps

- Repository-wide template validation remains red from historical planning artifacts outside this patch.
- Isolated browser data lacks a configured credential store, so API Provider and Lifecycle resource calls return existing credential-store errors; Candidate Profiles supplied the non-Pipeline shared-dialog smoke instead.
- No new browser-test framework was added. Committed TestClient regressions own durable component contracts; browser tools supplied execution evidence.

## 7. Assumptions and unresolved questions

- Prototype remains approved target because current specification and architecture name it as visual hierarchy and interaction reference.
- Approved execution decisions: direct controls save immediately; managed groups remain transactional; global header owns `Pipeline`; active section remains visible as page-content `h2`.
- No unresolved required audit finding remains.
