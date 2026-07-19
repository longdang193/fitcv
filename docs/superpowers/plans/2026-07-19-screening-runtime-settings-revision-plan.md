---
artifact_type: plan
status: in_progress
layer: change
template_id: implementation-plan
name: pipeline-settings-prototype-revision
targets:
  - docs/fitcv-settings-ui-prototype.html
---

# Pipeline Settings Prototype Revision Plan

## Goal

Finish the interactive Pipeline settings prototype as the approved UI contract draft. Extend the shell committed in `a30d2f29`, reuse its components and interaction patterns, and model all required pages, dialogs, dependencies, validation messages, mock persistence, and restore behavior without backend wiring.

## Scope Boundaries

### Included

- Modify only `docs/fitcv-settings-ui-prototype.html`.
- Preserve the persistent sidebar, header/search/theme controls, responsive drawer, native dialog, and existing settings components.
- Use local mock state and `localStorage` for immediate and transactional persistence demonstrations.
- Complete eight Pipeline pages: Overview, Enrichment, Screening & Shortlisting, Ranking, CV Analysis, CV Generation, Runtime & Limits, and Automation & Reuse.
- Record backend and integration gaps found during prototype work at final handoff.

### Excluded

- Production settings template changes.
- Backend configuration defaults, normalization, schemas, validators, compatibility projections, or runtime behavior.
- Settings store, API request, API response, or production persistence changes.
- Backend, API, runtime, schema, persistence-store, or production-template tests.
- Backend Gap Thresholds cleanup. Prototype removes only its own related UI, state, validation, and mock persistence.

## Implementation Outcomes

### Complete eight-page prototype

Each approved Pipeline page appears once, settings have one visible owner, Shortlist is merged into Screening & Shortlisting, and deprecated Gap Thresholds content is absent from prototype UI and mock state.

### Complete interaction contract

Direct settings persist immediately in mock storage. Interdependent settings use transactional dialogs whose drafts remain local until Save. Disabled controls are non-interactive, dependencies have visible supporting text, and warning/error states use text and behavior rather than color alone.

### Preserved committed shell

Implementation extends the `a30d2f29` shell. It does not replace `document.body`, add a second component system, restore a global save bar, or break themes, keyboard focus, responsive navigation, or reduced motion.

### Prototype proof and handoff

Source assertions, script parsing, browser checks, responsive/theme checks, and accessibility inspection prove the prototype contract. Deferred backend and integration work is listed after verification, not implemented here.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve unrelated working-tree changes.
- Parallel ownership: none; one HTML file owns page data, state, rendering, dialogs, and interactions.
- Sequential fallback: page map and content, managed interactions, mock persistence and validation, then browser verification and deferred-work notes.

## Task Breakdown

### Task 1: Complete page map and content

**Purpose:**
- Establish final navigation and settings content before completing behavior.

**Specification Coverage:**
- Candidate Scope moves to Overview.
- Skip Incomplete Listings defaults to On.
- Rules & Filters and Shortlist merge into Screening & Shortlisting.
- Approved Ranking, CV Analysis, CV Generation, Runtime & Limits, and Automation & Reuse labels and descriptions replace old content.
- Gap Thresholds disappear from prototype UI and mock state.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html` shell, `PAGES`, navigation, settings-card renderer
- Modify: `docs/fitcv-settings-ui-prototype.html` page definitions and copy
- Verify: `docs/fitcv-settings-ui-prototype.html` source assertions

**Dependencies:**
- Preserve shell and reusable `.setting-section`, `.settings-card`, `.row`, `.field`, `.switch`, and `.btn` structures from `a30d2f29`.

**Steps:**
- [ ] Add a failing source assertion for the eight required page IDs and labels; assert no standalone Shortlist page.
- [ ] Update navigation and page definitions to the eight approved Pipeline pages.
- [ ] Put Candidate Scope and key outcome controls in Overview; remove Candidate Scope from Enrichment and set Skip Incomplete Listings mock default to On.
- [ ] Split Location and Work Mode into separate rows and merge shortlisting controls into Screening & Shortlisting.
- [ ] Rename Structured Factor Weights to Factor Weights. Describe every factor, including Preference Fit as declared domain, role-family, and work-mode preference fit, and explain that a higher weight increases its influence on final score.
- [ ] Improve Semantic Alignment copy, remove “Read-only” and “Metadata only” from Embedding Model, and add Skills Match, Role Match, Responsibilities Match, and Domain Match rows.
- [ ] Reduce CV Generation to Included Sections only.
- [ ] Rename Synonym Triage to Synonym Review and Advanced Automation to Synonym Automation; rewrite automation labels without internal terminology.
- [ ] Remove every Gap Thresholds row, mock key, validation branch, and persisted prototype key.
- [ ] Omit empty Advanced sections and empty settings cards.

**Verification:**
- [ ] Run a Node source assertion for all eight labels, required renamed rows, no standalone Shortlist page, no `gap_thresholds`, and no `document.body.innerHTML`.
- Expected: exactly eight Pipeline page definitions and no deprecated prototype content.

**Exit Criteria:**
- Navigation and right-panel content match approved prototype information architecture with no duplicated setting ownership.

### Task 2: Complete managed dialogs and dependencies

**Purpose:**
- Model transactional settings and parent-child dependencies without backend calls.

**Specification Coverage:**
- Factor Weights total `1.00` before Save.
- Four CV match rows configure exact wording versus semantic similarity; each pair totals `1.00`.
- CV match Manage controls stay disabled until Semantic Alignment is On.
- Runtime stage rows manage Request Delay, Batch Size, and Concurrency.
- Disabled controls never open dialogs.

**Required Skills:**
- `skill-test-driven-development`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html` native dialog, draft state, Manage handling
- Modify: `docs/fitcv-settings-ui-prototype.html` dialogs, validation, dependency state, supporting text
- Verify: browser interactions and console assertions

**Dependencies:**
- Task 1 page definitions and row ownership complete.

**Steps:**
- [ ] Add failing interaction assertions for disabled Manage actions, invalid totals, Cancel discard, and valid Save commit.
- [ ] Build Factor Weights dialog with every factor description, visible remaining-total validation, and Save enabled only when finite non-negative values total `1.00`.
- [ ] Build one reusable two-value dialog for Skills Match, Role Match, Responsibilities Match, and Domain Match; require exact wording and semantic similarity to total `1.00`.
- [ ] Disable those four Manage buttons while Semantic Alignment is Off, associate visible supporting text with each action, and block mouse and keyboard opening.
- [ ] Revalidate dependent controls when Semantic Alignment changes; close and discard an open dependent draft when it turns Off.
- [ ] Build one Runtime & Limits row for Enrichment, Ranking, CV Analysis, and CV Generation. Each row opens a dialog with Request Delay, Batch Size, and Concurrency.
- [ ] Give every Manage row clear copy explaining what changes and how it affects scoring or processing.
- [ ] Keep dialog drafts local until Save; Cancel, Escape, and close discard drafts.

**Verification:**
- [ ] Confirm disabled CV Manage actions are mouse- and keyboard-inert while supporting text remains visible.
- [ ] Confirm invalid factor and match totals disable Save and show remaining difference; valid `1.00` totals save.
- [ ] Confirm four runtime stage rows and three approved fields in every runtime dialog.
- Expected: only valid complete drafts commit; disabled actions never open dialogs.

**Exit Criteria:**
- All managed settings demonstrate approved transaction and dependency behavior within prototype state.

### Task 3: Complete persistence, restore, warnings, and errors

**Purpose:**
- Make prototype state behavior consistent and user-friendly.

**Specification Coverage:**
- Valid direct changes save immediately.
- Managed changes save only through dialog Save.
- Restore Defaults operates per page.
- Runtime warnings are non-blocking; validation errors block Save.
- State meaning remains clear without color.

**Required Skills:**
- `skill-test-driven-development`
- `ui-ux-pro-max`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html` localStorage helper, defaults, restore handler, status messages
- Modify: `docs/fitcv-settings-ui-prototype.html` mock persistence, validation messages, restore behavior
- Verify: reload and page-scope browser checks

**Dependencies:**
- Tasks 1 and 2 define final controls and dialog contracts.

**Steps:**
- [ ] Keep one prototype state owner and one guarded localStorage read/write helper; invalid stored data falls back to defaults without replacing unrelated page state.
- [ ] Persist each valid direct change immediately and show concise saved confirmation without a global save bar.
- [ ] Commit valid dialog drafts atomically; never persist invalid, cancelled, or closed drafts.
- [ ] Use one page-scoped Restore Defaults handler and the same button label on every page.
- [ ] Add blocking runtime errors for non-finite values, negative Request Delay, Batch Size below `1`, and Concurrency below `1`; show text and disable Save.
- [ ] Add non-blocking warnings for Request Delay `0` with Concurrency above `8`, Concurrency above `16`, and Batch Size above `50`; show text and keep Save enabled.
- [ ] Preserve theme preference, mobile drawer behavior, focus visibility, native labels, and reduced-motion handling.

**Verification:**
- [ ] Reload after direct changes and saved transactions; committed values return.
- [ ] Cancel a changed transaction and reload; prior committed values remain.
- [ ] Trigger every runtime warning and error threshold; warnings allow Save, errors block Save, and both explain the issue.
- [ ] Restore one page and reload; only that page returns to defaults.
- Expected: every control has one persistence path, one default source, and visible state feedback.

**Exit Criteria:**
- Mock persistence, defaults, restore behavior, warnings, and errors are symmetric across pages and transaction types.

### Task 4: Verify prototype and record deferred work

**Purpose:**
- Prove prototype contract and separate remaining integration work.

**Specification Coverage:**
- Complete interactive prototype only.
- No backend or API validation.
- Record backend and integration gaps after prototype completion.

**Required Skills:**
- `browser:control-in-app-browser`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html` rendered states
- Modify: plan progress or handoff notes only when recording deferrals
- Verify: source assertions, inline script parsing, browser states, Lighthouse accessibility audit

**Dependencies:**
- Tasks 1 through 3 complete with focused checks passing.

**Steps:**
- [ ] Parse every inline script with Node `vm.Script`.
- [ ] Run final source assertions for page count, labels, removed content, and shell-preservation constraints.
- [ ] Inspect all eight pages in desktop viewport; confirm no empty cards or empty Advanced sections.
- [ ] Verify Factor Weights, four CV match dialogs, four runtime dialogs, Cancel/Save, disabled dependencies, warning/error behavior, Restore Defaults, and reload persistence.
- [ ] Verify narrow viewport navigation and content layout.
- [ ] Verify light/dark themes, keyboard focus, dialog focus behavior, accessible names, and reduced motion.
- [ ] Run Lighthouse accessibility audit and resolve prototype-owned failures within scope.
- [ ] Record deferred backend work at handoff: config/default projection, runtime stage behavior, Require Fit Context processing, production persistence/API contracts, and backend Gap Thresholds cleanup. Do not implement it here.

**Verification:**
- [ ] `node -e "const fs=require('fs'),vm=require('vm');const html=fs.readFileSync('docs/fitcv-settings-ui-prototype.html','utf8');[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].forEach((match)=>new vm.Script(match[1]));console.log('all inline scripts parse');"`
- [ ] Run final prototype source assertion command established in Task 1.
- [ ] Browser console has no prototype-owned errors across required interactions.
- [ ] Lighthouse accessibility audit has no unresolved prototype-owned critical failures.
- Expected: prototype works in desktop/mobile and light/dark states without backend dependencies.

**Exit Criteria:**
- Fresh prototype evidence passes and deferred integration work is explicitly separated from completed UI scope.

## Verification

- Parse inline scripts with Node `vm.Script`.
- Run Node source assertions for eight-page structure, required labels, removed content, and shell-preservation rules.
- Exercise direct, managed, disabled, warning, error, restore, reload, responsive, and theme states in browser.
- Run Lighthouse accessibility audit.
- Do not run backend, API, runtime, schema, persistence-store, or production-template test suites for this plan.

## Execution Notes

- Prototype implementation completed on July 19, 2026.
- Source contract, script parsing, ownership, dependency, warning/error, responsive-source, and accessibility-source checks pass.
- Browser and Lighthouse verification remain blocked because the in-app browser rejects automated access to the current `file://` URL. Manual browser refresh and review are still required before completion status.
- Deferred backend work: config/default projection, Enrichment stage behavior, Require Fit Context persistence and processing, production persistence/API contracts, and backend Gap Thresholds cleanup.

## Completion Criteria

The plan is ready for completion verification when:

1. `docs/fitcv-settings-ui-prototype.html` contains all eight approved Pipeline pages and no separate Shortlist or Gap Thresholds UI
2. every approved direct and managed interaction works against mock state with correct immediate or transactional persistence behavior
3. Semantic Alignment dependency, runtime warnings, blocking errors, and page-scoped Restore Defaults are visible and enforced
4. committed shell structure and reusable components remain intact
5. source assertions, inline script parsing, browser checks, responsive/theme checks, and accessibility audit pass
6. backend and integration gaps are recorded as deferred work without implementation
7. unrelated working-tree changes remain untouched

The plan may be marked `completed` only after `skill-verification-before-completion` runs fresh checks and finds no unresolved prototype-scope failure.

A checked box records progress; it is not proof by itself.
