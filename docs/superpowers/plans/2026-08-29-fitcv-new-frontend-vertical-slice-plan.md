---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: active
name: fitcv-new-frontend-vertical-slices
parent_spec: docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md
targets:
  - frontend/
  - frontend/package-lock.json
  - src/fitcv_cp/app.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/local_app.py
  - packaging/windows/fitcv-local.spec
  - scripts/build_fitcv_local.ps1
  - docs/architecture.md
  - docs/usage.md
  - tests/
---

# FitCV New Frontend Vertical-Slice Implementation Plan

## Goal

Create one executable, Git-tracked plan for rebuilding FitCV frontend from scratch as independently verifiable vertical product slices, while preserving canonical backend truth and legacy compatibility until explicit retirement approval.

## Current-state baseline

- New frontend is greenfield. No production `frontend/` package, build tool, browser client, or frontend test surface exists in current repository.
- Existing Jinja implementation under `src/fitcv_cp/templates/` and `docs/fitcv-settings-ui-prototype.html` are historical or frozen UX evidence only. New code must not import, wrap, copy, or incrementally modify them.
- FastAPI control-plane routes already expose canonical JSON, multipart, event, artifact, lifecycle, settings, and local-control contracts through `src/fitcv_cp/app.py` and `src/fitcv_cp/local_routes.py`.
- Reconciliation is closed and marks journey contracts aligned. Backend status is `READY` for product slices, except the static-asset/SPA host and packaged-resource boundary, which is `PATCH_REQUIRED`.
- Current local launch redirects from `src/fitcv_cp/app.py::local_root` to legacy routes. Legacy `/admin/*` surfaces remain compatibility surfaces during migration.
- PyInstaller currently packages Jinja templates and prompts through `packaging/windows/fitcv-local.spec`; frontend build output is not yet packaged.
- Execution-base candidate is `9a83da1d`; production activation must capture the exact clean pre-activation `HEAD`. Future execution must preserve user changes and modify only declared plan targets.

## Preserved invariants

- Product outcome remains Personal FitCV for one trusted Windows user: setup, candidate profile, job collection, run, fit decision, bookmark/interest, grounded CV review, and return use.
- `docs/intent/project-charter.md`, `docs/intent/success-outcomes.md`, and `docs/intent/constraints-and-non-goals.md` own product scope and completion priority. The retired roadmap is not current authority.
- `docs/fitcv-settings-ui-prototype.html` owns frozen information architecture, interaction, responsive behavior, and visual intent; its implementation is not reused.
- Active Agentic design tokens own production values. Terracotta/cream remains approved product palette, bound through semantic tokens rather than a second token SSOT.
- Native controls, visible focus, keyboard operation, Escape handling, focus containment/return, live regions, reduced motion, responsive navigation, and table-local overflow remain required.
- Server owns lifecycle status, capabilities, revisions, snapshots, evidence, fit meaning, suitability, artifact identity, retryability, and historical truth.
- Client owns only view state, URL/hash state, unsaved edits, selection state, polling control, and session-scoped transient notifications.
- Provider API keys never enter client state, logs, diagnostics, exports, or persisted frontend storage.
- Fit and Application Interest remain separate. Rating or personalization never changes suitability truth.
- CV preview is exact persisted safe text; unsafe HTML/script execution is prohibited. Download remains attachment-only.
- Legacy routes remain available until retirement gates pass; new frontend never parses legacy HTML or sample prototype data for truth.

## Product/specification coverage matrix

| Product outcome | Specification owner | Vertical slice coverage | Representative proof |
| --- | --- | --- | --- |
| FitCV Local setup and readiness | Active parent spec; local readiness/profile authority spec | Slice 1: Local readiness and application shell | fresh launch, readiness/error/recovery, settings mutation, packaged asset smoke |
| Candidate Profile lifecycle | Active parent spec; candidate evidence spec | Slice 2: Candidate Profile lifecycle | upload through confirmation, revision conflict, archive/restore, profile selection |
| Job collection and Scans | Active parent spec; managed Scan lifecycle spec | Slice 3: Scans and job collection | company selection, Scan lifecycle, output Table/JSON, reuse and Run input |
| Run continuity and recovery | Active parent spec; managed Scan and Run contracts | Slice 4: Run trigger and continuity | managed trigger, polling/events, stages, cancellation, retryable queue failure |
| Job evaluation and personalization | Active parent spec; personalization JSON spec | Slice 5: Fit, interest, bookmarks, personalization | fit evidence, independent interest, bookmark workspace, CAS personalization |
| Grounded CV generation and review | Active parent spec; CV preview transport spec | Slice 6: Grounded CV review | immutable version list, safe preview, download, regenerate, review state |
| Decision/history and diagnostics | Active parent spec; transient notification spec | Slice 8 plus cross-slice acceptance | snapshots, evidence, history, event console, source-backed notification projection |
| Supporting synonym management | Active parent spec; canonical API and synonym tests | Slice 7: supporting synonym management | review actions, import/export, processing status, supporting-only boundary |

Supporting synonym management cannot block completion unless it breaks a completion-critical journey or makes results untruthful. Identifiers from retired planning are historical only and not normative ownership.

## Vertical-slice definitions

### Slice 1 — Local readiness, shell, and settings

- **User outcome:** User launches FitCV Local, understands readiness, reaches the new app without Python/Docker/Git knowledge, and manages supported provider, LLM, prompt, system, backup, and data controls.
- **Frozen UX:** Overview, grouped navigation, responsive off-canvas navigation, API Providers, LLM Configuration, Prompt Management, System/Data Backup, loading/empty/error/success states, dialogs, tabs, native validation, focus return.
- **Owning sources:** `docs/intent/success-outcomes.md`; `docs/fitcv-settings-ui-prototype.html`; `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`; `docs/fitcv-new-frontend.integration.md`; `docs/superpowers/specs/2026-08-29-fitcv-local-readiness-profile-authority-spec.md`.
- **Backend status:** `PATCH_REQUIRED` only for new frontend host/static fallback, launch redirect, CSRF-safe asset delivery, and packaged static resources. Settings/readiness APIs are `READY`.
- **Boundaries:** `/healthz`, `/local/readiness`, `/api-providers*`, `/llm-configuration`, `/prompt-configurations*`, `/system-settings`, `/settings/pipeline*`, `/local/data/status`, `/local/lifecycle/status`, `/local/system/diagnostics`, backup/import routes.
- **Dependencies:** None. Establishes client, shell, URL/hash, token binding, shared primitives, and browser verification foundation consumed by later slices.
 - **Acceptance:** Fresh local launch opens `/app` before readiness gating so readiness UI can explain onboarding; `src/fitcv_cp/app.py::local_request_guard` allows `GET /app`, `GET /app/`, `GET /app/assets/*`, and hash deep-links before readiness while unsafe API mutations retain existing readiness/CSRF guards; readiness is derived from active confirmed profile; settings mutations handle validation, stale revision, retry, and success; no secret appears in browser storage/network logs; desktop/mobile and light/dark render without overflow.
- **Verification:** Direct FastAPI route tests for host/static/fallback/CSRF behavior; frontend unit/state checks; Playwright launch/deep-link/refresh/settings flows; keyboard/focus/accessibility snapshot; console and network evidence; packaged build includes exact static files.
- **Final journey relevance:** Get ready for normal use; return and continue.

### Slice 2 — Candidate Profile lifecycle

- **User outcome:** User uploads supported source, reviews deterministic baseline and controlled derivation separately, corrects evidence, confirms an active profile, then revises/archives/restores it without losing historical truth.
- **Frozen UX:** Upload, processing, Baseline, Controlled Derivation, Confirmation, catalog, detail, archive/restore, retry, conflict, and resume states.
- **Owning sources:** `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md`; candidate sections of `docs/api.md`; profile surfaces in `docs/fitcv-settings-ui-prototype.html`; `src/fitcv/candidate.py` registry.
- **Backend status:** `READY`; no backend delta unless direct contract evidence from focused tests disproves reconciliation.
- **Boundaries:** creation-attempt list/create/detail/source/source-blocks; field schema; baseline/derived GET/PATCH and actions; confirm; catalog; archive/restore/delete; active profile selection.
- **Dependencies:** Slice 1 client and primitives.
- **Acceptance:** Upload uses idempotency key; processing polls only server-declared states and honors `poll_after_ms`; edits batch by ordered ID-addressed operations; approval flushes edits; CAS/fingerprint conflict keeps local operations separate; only succeeded active profiles are selectable for Runs; prior revisions and Run snapshots remain unchanged.
- **Verification:** Direct API/store suites remain backend authority; frontend state tests cover polling, stale conflict, retry, discard, and capability gating; Playwright completes upload-to-confirmation and archive/restore from deep link; rendered responsive/accessibility/keyboard/focus/console evidence captured.
- **Final journey relevance:** Build and maintain candidate profile; return and continue.

### Slice 3 — Scans and job collection

- **User outcome:** User selects supported companies, creates a bounded Scan, reviews complete output in Table or JSON form, retries/reuses/archive/unarchives it, and supplies eligible Scan output to a Run.
- **Frozen UX:** Scans list Active/Archived tabs, New Scan, native company selection, Scan Details, Console, Table/JSON output, cancellation, retry, Run Again, delete preview.
- **Owning sources:** `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`; scan surfaces in `docs/fitcv-settings-ui-prototype.html`; `/tracked-companies*` and `/scans*` contracts.
- **Backend status:** `READY`.
- **Boundaries:** tracked companies; scans list/create/detail; events; output; cancel; run-again; archive/unarchive; delete preview/commit; Run source selection.
- **Dependencies:** Slice 1; Slice 4 consumes output but does not block Scan implementation.
- **Acceptance:** URL owns Active/Archived tab and pagination; selection actions derive from server capabilities; failed provider or required detail never becomes successful partial output; empty successful output remains truthful but unusable as sole Run source; Table and JSON render one immutable output; Run Again creates a new Scan; delete previews and rejects referenced data atomically.
- **Verification:** Existing scan/API/store tests are direct backend proof; frontend tests cover selection/action symmetry and one-output rendering; Playwright covers create, polling, cancellation, empty/error/success, output toggle, and Run source handoff; responsive/accessibility/console/network evidence included.
- **Final journey relevance:** Collect or add jobs; return and continue.

### Slice 4 — Run trigger, lifecycle, and recovery

- **User outcome:** User starts a profile-based Run from supported input, sees truthful lifecycle progress and stage results, returns later, and recovers from cancellation, queue failure, or incomplete processing.
- **Frozen UX:** Runs list, Trigger Run, Run Details, six stages, job input summary, lifecycle actions, event console, debug bundle, archived history.
- **Owning sources:** active parent specification; run contracts in `docs/api.md`; prototype Run surfaces; orchestration/store tests.
- **Backend status:** `READY`.
- **Boundaries:** managed `POST /runs`; `/runs`; `/runs/{run_id}`; stages/jobs; lifecycle actions; cursor events; debug bundle; immutable input/profile/settings snapshots.
- **Dependencies:** Slices 1–3; active confirmed profile from Slice 2; eligible Scan output from Slice 3 when used.
- **Acceptance:** Trigger validates every source before atomic snapshot; client never invents progress/status; event polling uses cursor and stops on terminal state; queue failure leaves inspectable failed Run and retry action; cancel/archive/unarchive are repeat-safe; archived deletion is idempotent and atomic; historical null/legacy snapshots display as historical.
- **Verification:** Direct backend success/failure/idempotency/state proof; frontend reducer tests; Playwright representative trigger, refresh, cancellation, failure/recovery, event console, and archived-history flows; browser console/network evidence.
- **Final journey relevance:** Start and follow a Run; narrow jobs before expensive work; return and continue.

### Slice 5 — Fit, interest, bookmarks, and personalization

- **User outcome:** User understands fit evidence and missing requirements, records independent Application Interest, bookmarks jobs, revisits/removes/exports them, and optionally changes ranking preference without changing suitability.
- **Frozen UX:** Pipeline Results, fit reasons, stage/result filters, selection/export, Application Interest, Bookmarks workspace, Baseline/Personalized Ranking and truthful fallback.
- **Owning sources:** `docs/superpowers/specs/2026-08-29-fitcv-core-personalization-json-spec.md`; results/bookmark/optimization surfaces in `docs/fitcv-settings-ui-prototype.html`; `docs/api.md`; reconciliation G-03.
- **Backend status:** `READY`.
- **Boundaries:** Run jobs/filter/export; bookmark mutations and `/bookmarks`; selection preview/export/remove; interest mutations; `GET/PATCH /personalization` with ETag/CAS.
- **Dependencies:** Slice 4 Run jobs and server capabilities.
- **Acceptance:** Fit display uses server evidence; interest never masks suitability; bookmark identity survives sessions and dependent Run removal is clear; exports use current filtered full set; personalization rejects unknown/invalid/stale writes without state corruption and surfaces `baseline_fallback` truthfully; legacy optimization administration is not used as new frontend transport.
- **Verification:** Direct API tests for rating contract, bookmark atomicity/export, personalization CAS and validation; frontend tests for reducer/state separation and optimistic-update rollback; Playwright fit review, interest, bookmark revisit/remove/export, and personalization conflict/fallback flows; accessibility and console/network evidence.
- **Final journey relevance:** Review fit and express interest; save jobs; adapt to preferences.

### Slice 6 — Grounded CV generation and review

- **User outcome:** User selects a suitable job, views ordered immutable CV versions, safely previews exact persisted content, regenerates when allowed, reviews evaluation state, and downloads the selected artifact.
- **Frozen UX:** CV history, View CV, Download CV, Regenerate CV, pending/running/failed/corrupt/unsupported preview, evaluation/review state.
- **Owning sources:** active parent specification; `docs/superpowers/specs/2026-08-29-fitcv-cv-preview-transport-spec.md`; `/cv-versions/*` contracts; reconciliation G-02.
- **Backend status:** `READY`.
- **Boundaries:** CV history; exact text preview; attachment download; regenerate action; persisted evaluation/review state.
- **Dependencies:** Slice 4 and Slice 5 selected Run Job.
- **Acceptance:** Selected version identity remains explicit; preview renders Markdown/plain text safely, rejects unsafe URL schemes, and falls back to text; pending preview is retryable; failed/corrupt/missing media uses canonical guidance; preview never mutates review/download/evaluation state; regeneration retains idempotency and separates generation success from evaluation acceptance.
- **Verification:** Direct backend checksum/media/error tests; frontend tests for safe renderer and version selection; Playwright preview/download/regenerate/retry/review-state flows; downloaded bytes/header check; CSP/console/network/accessibility evidence.
- **Final journey relevance:** Prepare grounded CV; review result before using it.

### Slice 7 — Supporting synonym management

- **User outcome:** User can inspect and manage synonym suggestions without confusing supporting taxonomy work with core fit truth.
- **Frozen UX:** Synonym list/details, approve/decline/clear, import/export, processing status, backup boundary.
- **Owning sources:** active parent specification; synonym route decorators in `src/fitcv_cp/app.py::create_app`, `tests/test_fitcv_cp/test_synonym_global_policy_io.py`, `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`, `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`; synonym surfaces in `docs/fitcv-settings-ui-prototype.html`; supporting-only disposition.
- **Backend status:** `READY`.
- **Boundaries:** `/synonym-policies*`, `/synonym-suggestions*`, `/synonym-processing-runs`, synonym backup routes.
- **Dependencies:** Slice 1 shared shell and canonical synonym contracts; no dependency on Task 5 UI completion.
- **Acceptance:** UI exposes server capabilities and review states, preserves atomic batch behavior, and never presents synonym changes as accepted candidate facts or suitability decisions.
- **Verification:** Existing route/store tests plus focused frontend state and browser flows for empty/loading/error/success and confirmation dialogs.
- **Final journey relevance:** Supporting only; cannot block Personal FitCV absent a demonstrated truth break.

### Slice 8 — Cross-slice history, notifications, diagnostics, and hardening

- **User outcome:** User can understand what happened, clear transient notices, return to prior work, and recover without losing server-owned history.
- **Frozen UX:** Global notification bell, per-Run/Scan Console, prior decisions, recovery actions, diagnostics, zero-badge and clear-one/clear-all behavior.
- **Owning sources:** active parent specification; `docs/superpowers/specs/2026-08-29-fitcv-client-transient-notifications-spec.md`; reconciliation G-01; Run/Scan event and debug-bundle contracts; decision/history and reliability requirements.
- **Backend status:** `READY`; notifications remain client-only, with no notification service.
- **Boundaries:** Run/Scan immutable events and debug bundle; client dedupe identities and session-scoped notification projection.
- **Dependencies:** Slices 1–6; Task 7 is supporting and must not block this slice. Only cross-slice concerns belong here.
- **Acceptance:** Dedupe priority is `action`, `event`, `state`, then `request`; rendered items mark read; clear-one/clear-all are symmetric; zero badge is hidden; event history remains server truth; diagnostics are redacted and actionable; no UI Clear View calls a delete route.
- **Verification:** frontend reducer/state tests; Playwright multi-slice notification and recovery flows; direct debug-bundle/event contract checks; final console/network/accessibility evidence.
- **Final journey relevance:** Return and continue; decision/history truth.

## Implementation Outcomes

1. A rebuilt `frontend/` TypeScript application uses React and Vite as its only frontend foundation, with no imports from Jinja templates or prototype JavaScript, and exposes explicit API, server-state, URL/hash-state, client-state, safe-rendering, and accessibility boundaries.
2. New frontend serves all completion-critical journeys and supporting synonym/settings surfaces through a same-origin `/app` entry while legacy `/admin/*` compatibility routes remain unchanged until retirement gates pass.
3. FastAPI local hosting, CSRF-safe mutation access, deep-link refresh, static assets, PyInstaller packaging, and Windows launch behavior are reconciled with the new build output.
4. Every slice has task-local proof, slice acceptance proof, and final whole-product evidence; backend deltas receive direct boundary proof and frontend work receives rendered/browser, responsive, accessibility, keyboard/focus, state, console, and network evidence.
5. Documentation records the new frontend boundary, legacy retirement gate, build commands, and canonical ownership without copying API or design-system truth into duplicate registries.

## Dependency graph

```text
Slice 1
  ├── Slice 2 ──┐
  ├── Slice 3 ──┼── Slice 4 ── Slice 5 ── Slice 6
  └─────────────┘       └────────────── Slice 7
Completion-critical Slices 1–6 ──────── Slice 8
Supporting Slice 7 may join when ready
```

Slice 4 begins after Tasks 2 and 3 complete with task-local proof. Slice 5 requires Slice 4's jobs boundary. Slice 6 requires Slice 5's selected-job state. Slice 8 follows completion-critical Slices 1–6; supporting Slice 7 may join when ready but cannot block.

## Task Breakdown

### Task 1: Build new frontend foundation and local host boundary

**Purpose:** Deliver Slice 1 from a clean frontend implementation and make it launchable without touching legacy UI code.

**Task Function:** Establish React/Vite/TypeScript application boundary, shared primitives, API client, state ownership, `/app` hash routing, accessibility foundation, static serving, and packaged asset delivery.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: material visual, interaction, responsive, accessibility, browser, and host-boundary judgment.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent contract, ownership, and browser-readiness validation.

**Specification Coverage:** Frozen UX contract; local-readiness spec; design export; success outcomes 1 and 11; no legacy implementation reuse.

**Required Skills:** `skill-frontend-component-engineering`, `skill-full-stack-integration`, `ui-ux-pro-max`, `build-web-apps:react-best-practices`, `skill-backend-verification`.

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py::create_app`, `src/fitcv_cp/app.py::local_root`, `src/fitcv_cp/app.py::local_request_guard`, `src/fitcv_cp/main.py::build_app`, `src/fitcv_cp/local_app.py::main`, `packaging/windows/fitcv-local.spec`, `scripts/build_fitcv_local.ps1`.
- Modify: `frontend/package.json`, `frontend/package-lock.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`, `frontend/src/app/**`, `frontend/src/components/**`, `frontend/src/styles/**`, `frontend/src/lib/**`, `frontend/src/main.tsx`, `src/fitcv_cp/app.py`, `src/fitcv_cp/main.py`, `src/fitcv_cp/local_app.py`, `packaging/windows/fitcv-local.spec`, `scripts/build_fitcv_local.ps1`, focused tests under `tests/`.
- Verify: `frontend/dist/`, host routes, packaged `dist/fitcv-local/`.

**Dependencies:** None. Do not copy or import `src/fitcv_cp/templates/` or `docs/fitcv-settings-ui-prototype.html` implementation.

**Authority:**
- Preauthorized local actions: create declared frontend files, add host/package wiring, run `npm install --package-lock-only --ignore-scripts` once to generate the initial lockfile, run `npm ci` for the exact locked dependency set, record `node --version` and `npm --version`, run frontend/backend checks, and create disposable build output.
- Stop for: stack change beyond React/Vite/TypeScript, route contract change, legacy template modification, destructive cleanup, or any dependency outside the exact locked set.

**Steps:**
- [x] Create minimal frontend package and manifests with exact pins `react@19.1.1`, `react-dom@19.1.1`, `@types/react@19.1.10`, `@types/react-dom@19.1.7`, `vite@7.1.3`, `@vitejs/plugin-react@5.0.2`, `typescript@5.9.2`, `vitest@3.2.4`, and `@playwright/test@1.55.0`; set `engines.node` to `24.15.0` and `packageManager` to `npm@11.13.0`; require `node --version` to return `v24.15.0` and `npm --version` to return `11.13.0`, blocking on mismatch before any install; then run `npm install --package-lock-only --ignore-scripts` to generate `frontend/package-lock.json`, followed by `npm ci`; define `frontend/vitest.config.ts`, `frontend/playwright.config.ts`, `npm run typecheck`, `npm run test`, `npm run test:e2e`, `npm run test:a11y`, and `npm run build`; bind production tokens through one CSS entry and semantic component contracts.
- [x] Implement API client with same-origin credentials, CSRF handling, standard error envelope, idempotency-key retention, ETag/CAS support, safe file/download handling, and no secret persistence.
- [x] Implement shell, grouped navigation, hash/deep-link routing, responsive drawer/scrim, shared Button/Field/Dialog/Tabs/Status/Table/Navigation, loading/empty/error/success states, focus lifecycle, and reduced-motion behavior; define `frontend/src/app/route-registry.ts` with Vite-discovered feature route modules so feature tasks do not edit shared registration files.
- [x] Resolve source-tree assets from `frontend/dist/` and frozen assets from `_MEIPASS/frontend/`; mount `/app/assets/*`, serve `/app` and `/app/*` SPA entry only for non-API paths, redirect local `/` to `/app`, preserve `/admin/*`, update PyInstaller destination mapping to `frontend`, update build inputs, and add host/package contract tests.

**Verification:**
- [x] `npm ci`, `npm run typecheck`, `npm run test`, `npm run test:e2e`, `npm run test:a11y`, and `npm run build` from `frontend/`; Expected: lockfile-backed dependency install, state/browser/accessibility checks, typecheck, and no build errors.
- [x] Focused host tests; Expected: `/app` entry/assets/deep-link work before readiness, API paths are not swallowed, `/admin/*` remains reachable, unsafe local requests retain existing protection.
- [x] Browser proof on desktop/mobile and light/dark; Expected: no overflow, visible focus, keyboard/Escape/focus return, no uncaught console errors, expected API/network requests only.

**Exit Criteria:** New app launches in local mode, Slice 1 acceptance passes, packaged static assets are present, and no legacy implementation is imported or modified.

### Task 2: Implement Candidate Profile lifecycle slice

**Purpose:** Deliver Slice 2 against canonical creation-attempt and profile contracts.

**Task Function:** Implement upload, processing, staged review, evidence/source inspection, CAS-safe edits, confirmation, catalog, detail, archive/restore, and Run eligibility.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: stateful forms, evidence review, async lifecycle, responsive and accessibility judgment.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent lifecycle/contract/readiness validation.

**Specification Coverage:** Canonical candidate uniform evidence projection spec; candidate routes in `docs/api.md`; decision/history invariants.

**Required Skills:** `skill-frontend-component-engineering`, `skill-full-stack-integration`, `skill-backend-verification`.

**Files And Symbols:**
- Inspect: `src/fitcv/candidate.py`, candidate route handlers in `src/fitcv_cp/app.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`.
- Modify: `frontend/src/features/candidate-profile/**`, `frontend/src/features/candidate-profile/route.tsx`, focused frontend tests, only backend files if a failing canonical contract requires a demonstrated delta.
- Verify: candidate API tests and browser journey.

**Dependencies:** Task 1 complete.

**Authority:** Preauthorized declared frontend and focused test edits; stop for schema/lifecycle changes not covered by active spec or source/tests.

**Steps:**
- [x] Load field schema and attempt resource before rendering stage; follow server `next_action` and capabilities.
- [x] Implement staged upload/polling, baseline/derived review, source references, ordered local operation queue, flush/approval sequencing, conflict handling, retry, and discard.
- [x] Implement catalog/detail and revision-safe archive/restore/delete; expose only server-permitted Run selection.

**Verification:**
- [x] Frontend state tests for polling, CAS/fingerprint conflict, batching, retry, and capability gating.
- [x] Existing direct API/store suites; Expected: no regression and canonical revisions/snapshots remain immutable.
- [x] Playwright upload → review → confirm → catalog → archive/restore; Expected: refresh/deep-link and keyboard/focus paths pass.

**Exit Criteria:** Profile slice acceptance passes with direct backend evidence and browser evidence.

### Task 3: Implement Scans and job collection slice

**Purpose:** Deliver Slice 3 with one truthful Scan output boundary.

**Task Function:** Implement tracked-company selection, Scan creation/lifecycle, output Table/JSON views, event console, reuse, archive, unarchive, delete preview, and Run source handoff.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: async lifecycle, selection/action symmetry, table responsiveness, and browser judgment.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent contract and acceptance review.

**Specification Coverage:** Active parent specification; Managed Scan lifecycle spec; scan contracts in `docs/api.md`.

**Required Skills:** `skill-frontend-component-engineering`, `skill-full-stack-integration`, `skill-backend-verification`.

**Files And Symbols:**
- Inspect: scan route decorators in `src/fitcv_cp/app.py::create_app`, scan persistence in `src/fitcv_cp/sqlite_store.py`, and `tests/test_fitcv_cp/test_scan_contracts.py`.
- Modify: `frontend/src/features/scans/**`, `frontend/src/features/scans/route.tsx`, `frontend/src/features/scans/run-source-selection.tsx`, focused frontend tests; backend only on proven contract delta.
- Verify: scan API/store tests and browser flows.

**Dependencies:** Task 1 complete; Slice 4 consumes output but does not block Scan implementation.

**Authority:** Declared frontend and focused test edits; stop for provider/security policy changes.

**Steps:**
- [x] Implement URL-owned Active/Archived tabs, pagination, native multi-selection, capability-driven actions, and delete preview.
- [x] Implement New Scan with verified company selection, stable publication-window enum, idempotent submit, polling, cancel, retry, and terminal states.
- [x] Render immutable output as Table/JSON views and expose ordered eligible Scan sources to Run trigger.

**Verification:** Existing scan suites plus frontend state tests; Playwright Scans navigation/dialog/empty-state proof; typecheck, Vitest `15 passed`, a11y `1 passed`, Vite build, `pytest -k "scan" -q` `73 passed`, `git diff --check`, and independent Herdr review `PASS` at `9848b9eeda46cd5144ef6f3ff42258127f5e20c5`.

**Exit Criteria:** Scan output and lifecycle truth pass without duplicate client-owned job schema.

### Task 4: Implement Run trigger and continuity slice

**Purpose:** Deliver Slice 4 across managed trigger, lifecycle, event, and recovery boundaries.

**Task Function:** Implement Run trigger, source validation UI, list/detail/stages/jobs, event cursor, lifecycle actions, debug bundle, and recovery states.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: high-state-density lifecycle and cross-boundary browser judgment.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent failure/idempotency/history validation.

**Specification Coverage:** Run contracts in `docs/api.md`; continuity/recovery and history invariants.

**Required Skills:** `skill-frontend-component-engineering`, `skill-full-stack-integration`, `skill-backend-verification`.

**Files And Symbols:**
- Inspect: Run handlers in `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py`, `tests/test_fitcv_cp/test_run_lifecycle.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py`.
- Modify: `frontend/src/features/runs/**`, `frontend/src/features/runs/route.tsx`, `frontend/src/features/run-detail/**`, focused frontend tests; backend only on proven delta.
- Verify: direct route/store/orchestrator tests and browser journey.

**Dependencies:** Tasks 1–3 complete, including task-local proof and usable source-selection fixtures.

**Authority:** Declared frontend and focused backend test edits; stop for orchestration semantics changes or unapproved retry behavior.

**Steps:**
- [x] Implement managed source picker and trigger with idempotency, active confirmed profile, and immutable input summary.
- [x] Implement list/detail/stages/jobs, server-owned statuses/capabilities, cursor event polling, and terminal/recovery rendering.
- [x] Implement cancel/archive/unarchive/archive-delete/debug-bundle actions with confirmation and state-specific locks.

**Verification:** Direct backend success/failure/idempotency/state proof; frontend reducer tests; Playwright trigger, refresh, cancel, queue-failure recovery, event console, and archived history.

**Exit Criteria:** Run remains truthful across refresh, retry, interruption, and historical records.

### Task 5: Implement fit, interest, bookmarks, and personalization slice

**Purpose:** Deliver Slice 5 while preserving separate suitability and preference truth.

**Task Function:** Implement result filters/table, fit evidence, interest mutations, bookmark workspace/export/remove, and core personalization read/CAS update.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: decision clarity, state separation, tables, dialogs, and accessibility judgment.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent contract and truth-boundary review.

**Specification Coverage:** Core personalization JSON spec; result/bookmark/interest contracts; reconciliation G-03.

**Required Skills:** `skill-frontend-component-engineering`, `skill-full-stack-integration`, `skill-backend-verification`.

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py::set_canonical_bookmark`, `src/fitcv_cp/app.py::clear_canonical_bookmark`, `src/fitcv_cp/app.py::set_canonical_interest`, `src/fitcv_cp/app.py::clear_canonical_interest`, `src/fitcv_cp/app.py::get_personalization`, `src/fitcv_cp/app.py::patch_personalization`, `src/fitcv_cp/sqlite_store.py::set_bookmark`, `src/fitcv_cp/sqlite_store.py::clear_bookmark`, `src/fitcv_cp/sqlite_store.py::set_run_job_interest`, `src/fitcv_cp/sqlite_store.py::clear_run_job_interest`, `src/fitcv_cp/sqlite_store.py::list_filter_results_for_run`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, and `tests/test_fitcv_cp/test_optimization_page.py`.
- Modify: `frontend/src/features/job-evaluation/**`, `frontend/src/features/job-evaluation/route.tsx`, `frontend/src/features/bookmarks/**`, `frontend/src/features/bookmarks/route.tsx`, `frontend/src/features/personalization/**`, `frontend/src/features/personalization/route.tsx`, focused frontend tests.
- Verify: `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_optimization_page.py`; `frontend/src/features/job-evaluation/route.test.tsx`, `frontend/src/features/bookmarks/route.test.tsx`, and `frontend/src/features/personalization/route.test.tsx`; Playwright fit-review, interest, bookmark, export, and personalization-conflict flows.

**Dependencies:** Task 4 job results available.

**Authority:** Declared frontend and focused tests; stop for changes to suitability or rating semantics.

**Steps:**
- [x] Render server fit/evidence and stage/result filters; keep personal interest separate.
- [x] Implement bookmark identity, selection preview, filtered export, remove, and dependent-removal messaging.
- [x] Implement personalization GET/PATCH using ETag/revision, validation, conflict recovery, and truthful fallback; do not call legacy optimization HTML.

**Verification:** Direct API tests; frontend state tests for separation/CAS rollback; Playwright review/interest/bookmark/export/personalization conflict and fallback flows.

**Exit Criteria:** User decisions remain explainable and no preference signal changes suitability display.

### Task 6: Implement grounded CV review slice

**Purpose:** Deliver Slice 6 with safe immutable CV preview and download.

**Task Function:** Implement CV history, selected-version preview, safe Markdown/plain-text renderer, download, regeneration, and review/evaluation state.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: material safe rendering, artifact UX, responsive review, and browser judgment.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent artifact integrity and unsafe-content validation.

**Specification Coverage:** Active parent specification; CV preview transport spec; reconciliation G-02.

**Required Skills:** `skill-frontend-component-engineering`, `skill-full-stack-integration`, `skill-backend-verification`.

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py::get_canonical_cv_versions`, `src/fitcv_cp/app.py::download_canonical_cv`, `src/fitcv_cp/app.py::preview_canonical_cv`, `src/fitcv_cp/app.py::regenerate_canonical_cv`, `src/fitcv_cp/sqlite_store.py::list_cv_versions`, `src/fitcv_cp/sqlite_store.py::get_cv_download`, `src/fitcv_cp/sqlite_store.py::get_cv_preview`, `src/fitcv_cp/sqlite_store.py::reserve_cv_regeneration`, `src/fitcv_cp/sqlite_store.py::get_cv_markdown`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py`, and `tests/test_fitcv_cp/test_sqlite_store.py`.
- Modify: `frontend/src/features/cv-review/**`, `frontend/src/features/cv-review/route.tsx`, focused safe-renderer and browser tests.
- Verify: `python -m pytest tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_sqlite_store.py`; `frontend/src/features/cv-review/safe-renderer.test.tsx` and `frontend/src/features/cv-review/route.test.tsx`; Playwright preview/download/regenerate/retry/review-state flows plus downloaded-byte checksum and media-type assertions.

**Dependencies:** Task 5 selected job boundary.

**Authority:** Declared frontend and focused tests; stop for media-type or integrity contract changes.

**Steps:**
- [ ] Implement ordered version history and explicit selected-version state.
- [ ] Fetch exact preview bytes and render only safe Markdown/plain text; reject unsafe URL schemes and never execute HTML/script.
- [ ] Implement retryable pending state, terminal failure guidance, download, regeneration idempotency, and separate review/evaluation state.

**Verification:** Direct checksum/media/error tests; safe-renderer tests; Playwright preview/download/regenerate/retry/review-state and header/content checks.

**Exit Criteria:** Preview and download preserve immutable version truth and no unsafe content executes.

### Task 7: Implement supporting synonym management slice

**Purpose:** Rebuild synonym surfaces without making supporting taxonomy work a completion blocker.

**Task Function:** Implement list/detail/review/batch actions, import/export, and processing states against canonical routes.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: material interaction and accessibility judgment, bounded supporting scope.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: scope and truth-boundary review.

**Specification Coverage:** Active parent specification supporting-synonym boundary; synonym route behavior in `src/fitcv_cp/app.py::create_app`, persistence behavior in `src/fitcv_cp/sqlite_store.py`, and the named synonym tests as current executable contract. No focused synonym specification exists; do not invent one during implementation planning.

**Required Skills:** `skill-frontend-component-engineering`, `skill-full-stack-integration`.

**Files And Symbols:**
- Inspect: synonym route decorators in `src/fitcv_cp/app.py::create_app`, persistence helpers in `src/fitcv_cp/sqlite_store.py`, and `tests/test_fitcv_cp/test_synonym_global_policy_io.py`, `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`, `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`.
- Modify: `frontend/src/features/synonyms/**`, `frontend/src/features/synonyms/route.tsx`, focused frontend tests only. Task 7 does not edit shared app registration, navigation, notification, or integration files; those belong to Task 8.
- Verify: existing synonym route/store suites and browser flows.

**Dependencies:** Task 1 shared shell and current source/test synonym contract; no dependency on Task 5 UI completion.

**Authority:** Declared frontend/test files; stop if work would change candidate, fit, or suitability truth.

**Steps:**
- [ ] Implement capability-driven list/detail and review states.
- [ ] Implement atomic batch approve/decline/clear and import/export feedback.
- [ ] Keep synonym feature-local status and review feedback; shared navigation and notification registration belongs to Task 8.

**Verification:** Existing direct tests; browser empty/loading/error/success/confirmation/accessibility flow.

**Exit Criteria:** Supporting surfaces work without duplicating taxonomy or candidate-field registries.

### Task 8: Integrate history, notifications, diagnostics, and cross-slice hardening

**Purpose:** Deliver Slice 8 and resolve cross-slice integration defects after completion-critical slices exist; supporting Slice 7 may join but cannot block.

**Task Function:** Integrate client notification reducer, event projections, recovery links, global error handling, responsive/theme consistency, and cross-slice navigation/history.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: cross-surface browser, accessibility, responsive, and recovery judgment.

**Validator Profile (optional):**
- Controller-selected: `review`
- Selection basis: independent whole-product readiness review.

**Specification Coverage:** Active parent specification; transient notifications spec; reconciliation G-01; decision/history and reliability requirements.

**Required Skills:** `skill-full-stack-integration`, `skill-backend-verification`.

**Files And Symbols:**
- Inspect: `frontend/src/app/route-registry.ts`, `frontend/src/state/notifications/**`, each `frontend/src/features/*/route.tsx`, `src/fitcv_cp/app.py::get_process_events`, `src/fitcv_cp/app.py::download_run_cv_debug_json`, `src/fitcv_cp/app.py::download_run_cv_generation_trace_json`, `src/fitcv_cp/app.py::download_run_cv_analysis_trace_json`, `tests/test_fitcv_cp/test_run_lifecycle.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py`, and `tests/test_fitcv_cp/test_app.py`.
- Modify: `frontend/src/state/notifications/**`, `frontend/src/app/**`, `frontend/src/features/**` only for integration defects, `docs/architecture.md`, `docs/usage.md`, focused integration/browser tests.
- Verify: `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_run_lifecycle.py tests/test_fitcv_cp/test_run_detail_output_availability.py`; `frontend/src/app/route-registry.test.tsx`, `frontend/src/state/notifications/notifications.test.ts`, and `frontend/src/app/integration.test.tsx`; full frontend typecheck/test/build and Playwright desktop/mobile, theme, keyboard, recovery, notification, and history flows.

**Dependencies:** Tasks 1–6 complete. Task 7 may be included when complete, but cannot block integration or completion-critical verification.

**Workspace:** Dedicated integration worktree created from the verified fan-in commit for Tasks 1–6; never use the controller's current workspace for write-capable integration.

**Authority:** Cross-slice integration and declared proof/docs edits; stop for new product behavior, new backend services, or scope promotion of supporting work.

**Steps:**
- [ ] Add source-backed session notification projection with specified dedupe order, mark-read, clear-one, clear-all, and zero-badge behavior.
- [ ] Wire event consoles, diagnostics/recovery actions, cross-route return links, and server capability-driven action availability.
- [ ] Run cross-slice responsive/theme/accessibility/keyboard/focus/console/network matrix and fix only integration defects; preserve `docs/fitcv-new-frontend.integration.md` as historical reconciliation evidence and remove only temporary execution mappings created during this plan.

**Verification:** Reducer tests; representative browser recovery and notification flows; direct event/debug-bundle contract checks; no UI Clear View delete calls.

**Exit Criteria:** Cross-slice acceptance passes, no temporary contract mapping remains, and historical reconciliation evidence remains intact.

## Execution waves / parallelism opportunities

## Execution Approach

- Mode: `parallel-capable`
- Coordination: `git-tracked`
- Default task executor: `codex`
- Required skills: `skill-chief-of-staff`, `skill-full-stack-integration`, `skill-backend-verification`, `skill-frontend-component-engineering`
- Isolation: isolated Git worktree per concurrent writer; same-worktree work is sequential.
- CoS/profile preflight: before any write-capable dispatch, follow `docs/operating_system/procedures/personal-local-worktree-procedure.md` and `docs/operating_system/tooling/runtime-tool-resolution.md`; set `$base = git rev-parse HEAD`, prove `git cat-file -e "$base:agents/ui.toml"`, `git cat-file -e "$base:agents/review.toml"`, `git cat-file -e "$base:agents/xhigh.toml"`, `git cat-file -e "$base:scripts/herdr_main_launcher.py"`, each tracked `.agents/skills/<skill>/SKILL.md`, resolved runtime/model bindings, and `git hash-object` values for profiles, skills, and launcher. Resolve external skills `ui-ux-pro-max` and `build-web-apps:react-best-practices` through the configured runtime capability path and record provider/version evidence; do not require those external skills to be Git-tracked. Current-worktree untracked files do not satisfy this gate. Missing or mismatched profiles, skills, launcher, hashes, runtime capability, or runtime evidence blocks dispatch; do not fall back to another profile or current-workspace writes. If required profile/coordination-skill inputs are not tracked at activation base, stop and obtain a separate approved repository-configuration change before activation. Record `git status --short --ignored` and inventory pre-existing ignored SQLite sidecars before creating worktrees; cleanup may remove only task-created sidecars after proof.
- Commit policy: no commits during plan drafting; execution tasks use verified per-task checkpoint commits only when approved CoS run authorizes them.
- Preauthorized local actions: declared frontend/backend/test/docs edits, configured local checks, browser verification, package/build checks, and isolated worktree operations.
- User-approval actions: push, merge, publication, external writes/authentication, destructive cleanup, and legacy deletion.
- Parallel ownership: Task 2 owns `frontend/src/features/candidate-profile/**`; Task 3 owns `frontend/src/features/scans/**`; Task 4 owns `frontend/src/features/runs/**`; later tasks own declared directories. Task 1 owns only `frontend/src/app/**`, `frontend/src/components/**`, `frontend/src/styles/**`, `frontend/src/lib/**`, `frontend/src/main.tsx`, host/package files, and no feature directories. No concurrent task edits shared foundation or another task's feature directory.
- Sequential fallback: run Tasks 2 and 3 sequentially if worktree setup or shared route fixtures make isolation unsafe; run Task 4 after both; run Tasks 5–8 sequentially except Task 7 may run independently after Task 1.

## Coordination State

- Coordination schema: `2`
- Coordination owner: lead Codex controller
- Branch: `main`
- Base commit: `e98ce80df2f5a73ae88a2815af62143256aec8da`
- Expected workspace: `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT`
- Next action: create Task 8 integration worktree from accepted Task 6 HEAD and add accepted Task 7 branch
- Blockers: none
- Preserved pre-existing changes: user-owned `.gitignore` modification in lead workspace; preserved and excluded from task lane.

Before activation, lead controller records one durable lane entry per task in this ledger: exact branch, isolated worktree path, base commit, current `HEAD`, allowed paths, dependency gate, checkpoint commit, accepted proof, fan-in source and target, blocker, and next action. Values come from Git and fresh command output, not runtime session state. Lead remains sole ledger writer; lane commits do not change task state. Task 8 integration starts only from the verified fan-in commit in its dedicated integration worktree. Replace every pending activation value before dispatch; no runtime session may supply missing recovery state.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | completed | `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-task-1` | codex | none | build, host, browser, package | accepted at `75d9eb542ffa3a60760f3bbcc5fcc8030b9a7b30`; frontend bootstrap/typecheck/unit/a11y/build passed; browser preview shell/theme/deep-link proof passed; 534 backend/host regression tests passed; foundation fallback kept under `frontend/src/app/**` |
| Task 2 | completed | `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-task-2` | codex | Task 1 | lifecycle API and browser journey | accepted at `24ad1bfda7c227cd70b66faa0464c511c7648a6e`; frontend typecheck passed; Vitest `34 passed`; a11y `1 passed`; Vite build passed; candidate pytest `210 passed, 1 skipped`; focused app tests `26 passed`; Playwright `3 passed`; `git diff --check` passed; independent Herdr `review` returned `PASS`; lane clean |
| Task 3 | completed | `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-task-3` | codex | Task 1 | scan API and browser journey | accepted at `9848b9eeda46cd5144ef6f3ff42258127f5e20c5`; frontend, backend, browser, lifecycle, and independent review proof recorded below; lane clean |
| Task 4 | completed | `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-task-4` | codex | Task 1, Task 2, Task 3 | run API and recovery browser journey | accepted at `e14c7ada170ba7922d4c498b8145efdc100d605b`; frontend typecheck, focused Vitest `11 passed`, a11y `1 passed`, Vite build, Playwright `5 passed`, backend Run tests `18 passed`, `compileall`, `git diff --check`; independent Herdr `review` fresh `PASS`; lane clean and pushed |
| Task 5 | completed | `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-task-5` | codex | Task 4 | decision API and browser journey | accepted at `5f23ffa30aade7a3ac0f58e51e4416f5b0720a57`; frontend typecheck, Vitest `63 passed`, a11y `1 passed`, Vite build, Playwright `5 passed`, backend focused tests `616 passed`; independent Herdr `review` `PASS`; browser route probes passed; lane clean and pushed |
| Task 6 | active | `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-task-6` | codex | Task 5 | artifact API and safe preview browser journey | activated from accepted Task 5 HEAD `5f23ffa30aade7a3ac0f58e51e4416f5b0720a57`; Herdr launcher bound profile `ui` / `combo-ui` to session `default`, pane `w6:p1`, exact worktree; implementation active |
| Task 7 | active | `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/fitcv-task-7` | codex | Task 1 | synonym API and browser journey | activated from Task 1 HEAD `75d9eb542ffa3a60760f3bbcc5fcc8030b9a7b30`; Herdr launcher bound profile `ui` / `combo-ui` to session `default`, pane `w7:p1`, exact worktree; implementation active |
| Task 8 | pending | dedicated integration worktree from verified fan-in commit | codex | Tasks 1–6 | whole-frontend and cross-slice proof | pending |

### Durable Lane Record

| Task | Branch | Worktree | Base / HEAD | Allowed Paths | Checkpoint | Accepted Proof | Fan-in | Blocker / Next Action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Task 1 | completed | `codex/fitcv-task-1` | `e98ce80df2f5a73ae88a2815af62143256aec8da` / `75d9eb542ffa3a60760f3bbcc5fcc8030b9a7b30` | Task 1 Modify paths | `75d9eb542ffa3a60760f3bbcc5fcc8030b9a7b30` | npm ci with pinned Node/npm; frontend typecheck, Vitest, a11y, Vite build; browser preview `/app/#/overview`, navigation, title, light/dark toggle; `pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_frontend_host.py` = 534 passed; `python -m compileall -q src`; `git diff --check`; post-proof ownership correction moved overview fallback into `frontend/src/app/**` and reran frontend checks | source for Tasks 2–8 | Task 1 accepted; select Task 2 or Task 3 |
| Task 2 | completed | `codex/fitcv-task-2` | `75d9eb542ffa3a60760f3bbcc5fcc8030b9a7b30` / `24ad1bfda7c227cd70b66faa0464c511c7648a6e` | `frontend/src/features/candidate-profile/**`, focused frontend tests; backend only for proven canonical contract delta | `24ad1bfda7c227cd70b66faa0464c511c7648a6e` | frontend typecheck; Vitest `34 passed`; a11y `1 passed`; Vite build; candidate pytest `210 passed, 1 skipped`; focused app tests `26 passed`; Playwright `3 passed`; `git diff --check`; independent Herdr `review` `PASS`; clean lane | source for Task 4 | Task 2 accepted; activate Task 3 |
| Task 3 | completed | `codex/fitcv-task-3` | `75d9eb542ffa3a60760f3bbcc5fcc8030b9a7b30` / `9848b9eeda46cd5144ef6f3ff42258127f5e20c5` | `frontend/src/features/scans/**`, `frontend/src/features/scans/route.tsx`, `frontend/src/features/scans/run-source-selection.tsx`, focused frontend tests; backend only for proven contract delta | `9848b9eeda46cd5144ef6f3ff42258127f5e20c5` | typecheck; Vitest `15 passed`; a11y `1 passed`; Vite build; existing scan pytest `73 passed`; `git diff --check`; browser Scans navigation/dialog/empty-state proof; independent Herdr `review` first returned FAIL, bounded contract patch accepted, fresh review returned PASS; lane clean | source for Task 4 | Task 3 accepted; publish lane and prepare Task 4 fan-in |
| Task 4 | completed | `codex/fitcv-task-4` | `49ac283e` / `e14c7ada170ba7922d4c498b8145efdc100d605b` | `frontend/src/features/runs/**`, `frontend/src/features/runs/route.tsx`, `frontend/src/features/run-detail/**`, focused frontend tests; backend only for proven delta | `e14c7ada170ba7922d4c498b8145efdc100d605b` | frontend typecheck; focused Vitest `11 passed`; a11y `1 passed`; Vite build; Playwright `5 passed`; backend Run tests `18 passed`; `python -m compileall -q src`; `git diff --check`; independent Herdr `review` fresh `PASS`; pushed `origin/codex/fitcv-task-4`; clean lane | source for Task 5 | Task 4 accepted; activate Task 5 |
| Task 5 | completed | `codex/fitcv-task-5` | `e14c7ada170ba7922d4c498b8145efdc100d605b` / `5f23ffa30aade7a3ac0f58e51e4416f5b0720a57` | `frontend/src/features/job-evaluation/**`, `frontend/src/features/job-evaluation/route.tsx`, `frontend/src/features/bookmarks/**`, `frontend/src/features/bookmarks/route.tsx`, `frontend/src/features/personalization/**`, `frontend/src/features/personalization/route.tsx`, focused frontend tests; backend only for proven delta | `5f23ffa30aade7a3ac0f58e51e4416f5b0720a57` | frontend typecheck; Vitest `63 passed`; a11y `1 passed`; Vite build; Playwright `5 passed`; backend focused tests `616 passed`; browser route probes for Evaluation, Bookmarks, Personalization; independent Herdr `review` `PASS`; pushed `origin/codex/fitcv-task-5`; clean lane | source for Task 6/8 | Task 5 accepted; activate Task 6 |
| Task 6 | completed | `codex/fitcv-task-6` | `5f23ffa30aade7a3ac0f58e51e4416f5b0720a57` / `94c5bce6adbfb0232b5b733d2ef5573bf564fc02` | `frontend/src/features/cv-review/**`, `frontend/src/features/cv-review/route.tsx`, focused safe-renderer and browser tests | `94c5bce6adbfb0232b5b733d2ef5573bf564fc02` | focused Vitest `14 passed`; Vite build; Playwright CV review `3 passed` against Task 6 Vite host; backend CV artifact/store suite `156 passed`; `git diff --check`; lane clean; review attempt returned stale-path findings, lead source inspection rejected mismatched evidence and found no applicable remaining blocker | source for Task 8 | Task 6 accepted; fan in to Task 8 |
| Task 7 | completed | `codex/fitcv-task-7` | `75d9eb542ffa3a60760f3bbcc5fcc8030b9a7b30` / `70daef0c7db6a83d35941d421aff64c87ad491a4` | `frontend/src/features/synonyms/**`, `frontend/src/features/synonyms/route.tsx`, focused frontend tests only | `70daef0c7db6a83d35941d421aff64c87ad491a4` | focused Vitest `10 passed`; frontend typecheck; Vite build; `git diff --check`; lane clean; independent review returned PASS with no P1/P2, plus noted live/browser proof gap; supporting slice accepted and remains non-blocking | optional; never gates Task 8 | Task 7 accepted; optionally add during Task 8 fan-in |
| Task 8 | active | dedicated integration worktree | Tasks 1–6 fan-in / pending | Task 8 Modify paths | pending | accepted Task 6 source `94c5bce6adbfb0232b5b733d2ef5573bf564fc02`; Task 7 optional source `70daef0c7db6a83d35941d421aff64c87ad491a4`; integration worktree not yet created | final integration target | create Task 8 worktree from Task 6 and merge Task 7 |

### Wave 0 — Foundation

- Task 1 only.
- Gate: build, host, CSRF, launch, deep-link, and packaged asset proof.

### Wave 1 — Independent product entry slices

- Tasks 2 and 3 may run concurrently in isolated worktrees after Task 1.
- CoS selects one dependency-ready task using task ledger, declared ownership, and proof requirements.

### Wave 2 — Run continuity

- Task 4 after Tasks 2 and 3 complete with task-local proof.

### Wave 3 — Decision and artifact slices

- Task 5 then Task 6; Task 7 may run after Task 1 in a separate worktree because it owns its route module and does not edit shared registration; shared navigation/notification registration is serialized in Task 8; it should not delay completion-critical slices.

### Wave 4 — Cross-slice integration

- Task 8 after Tasks 1–6 in its dedicated integration worktree. Task 7 may be added if complete, but does not block final integration. No parallel writers during final integration or verification.

## Cross-slice integration/hardening phase

Task 8 is the only planned cross-slice hardening phase. It covers shared error normalization, notification projection, event/debug recovery links, navigation return paths, responsive/theme/accessibility consistency, duplicate-submit locks, safe download behavior, stale-state handling, and removal of temporary integration sidecars. It does not introduce a notification backend, client-owned domain schema, duplicate design-system token file, or speculative component library.

## Verification

### Whole-frontend verification

- `npm ci`, `npm run typecheck`, `npm run test`, `npm run test:e2e`, `npm run test:a11y`, and `npm run build` from `frontend/`; Expected: lockfile-backed dependency install, state/browser/accessibility checks, typecheck, and production bundle pass.
- Frontend unit/state checks cover API error mapping, reducers, polling, URL/hash state, idempotency keys, ETag/CAS, safe CV rendering, notification dedupe, and capability gating.
- Playwright covers fresh launch, deep-link/refresh/back-forward, every completion-critical slice, loading/empty/error/success/retry/pending states, representative recovery, and legacy route coexistence.
- Browser evidence covers desktop and narrow viewport, light and dark theme, zoom/overflow, keyboard-only navigation, focus visibility/return/containment, Escape, native validation, reduced motion, semantic names/roles, and zero uncaught console errors.
- Network evidence confirms same-origin API calls, no duplicate mutation on repeated input, correct idempotency/ETag headers, no secrets in request/storage/log output, and no legacy HTML parsing.
- Package proof runs `scripts/build_fitcv_local.ps1` and verifies static bundle presence, build manifest/hash output, launch path, and existing size budget.

### Affected backend/API regression verification

- Run direct focused suites for `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/sqlite_store.py`, and affected route/service tests after each backend host change.
- Preserve direct proof for local readiness/profile authority, candidate CAS/revisions, Scan atomicity/idempotency/output integrity, Run snapshot/lifecycle/recovery, bookmark/interest semantics, personalization CAS/fallback, CV checksum/media errors, events/debug bundle, and CSRF/host guards.
- Backend changes are limited to static host, launch, packaging, or proven contract deltas. Any material API behavior delta requires `skill-backend-verification` evidence: direct boundary, important success/failure, final state/side effect, idempotency/rollback where applicable, and fresh automated output.
- Run `python -m compileall -q src`, `git diff --check`, `python scripts/validate_template_required_sections.py --repo-root .`, and `python scripts/validate_planning_lifecycle.py --repo-root .` after documentation or planning-surface changes.

### Representative E2E journey verification

1. Fresh FitCV Local launch → readiness failure/recovery or ready Overview → settings change → new app route.
2. Upload supported profile → deterministic processing → baseline/derived evidence review → confirm active profile.
3. Add/select tracked company → create Scan → review output Table/JSON → choose Scan source → trigger Run.
4. Refresh Run Details → observe cursor events/stages → inspect fit evidence → set Application Interest → bookmark job.
5. Revisit Bookmarks → filter/remove/export → optionally set Personalized Ranking and recover from stale revision.
6. Select suitable job → inspect CV history → safe preview exact version → regenerate or retry pending → download selected artifact → review result.
7. Interrupt/recover Run or Scan → inspect diagnostics/debug bundle → clear notification one/all → return to prior history.

E2E does not replace direct frontend state proof or direct backend/API proof.

## Independent final review

- Before plan approval, run `skill-plan-document-reviewer` against this plan and all named canonical inputs.
- Assign one `xhigh` profile for deep architecture, dependency, ownership, and proof review.
- Assign one independent `review` profile for repository evidence, plan-contract validation, scope, and execution-readiness review.
- Reviewers do not modify plan or repository files. Findings use `P1/P2/P3`, exact path/line evidence, smallest safe correction, and one readiness verdict.
- Lead controller reconciles both reports, revises this proposed plan, reruns planning validation, and only then presents approval request.

## Legacy frontend retirement gate

Do not delete or repurpose legacy templates during slice execution. Retire legacy implementation only after:

- all completion-critical and required supporting frontend routes have new-app browser proof;
- direct backend/API regression suites remain green;
- new `/app` launch and packaged Windows build pass on fresh installation;
- legacy `/admin/*` compatibility consumers are inventoried and either preserved, redirected by explicit policy, or retired by a separate approved change;
- no new frontend import, fetch, parser, or state path depends on legacy HTML/templates/prototype JavaScript;
- product owner explicitly approves retirement scope and rollback path;
- a separate retirement plan authorizes deletion or continued compatibility ownership.

## Completion Criteria

The plan is implementation-ready when:

1. All required sections, task contracts, paths, dependencies, ownership, profiles, skills, and proof commands are concrete and validator-clean.
2. Both assigned independent reviewers return `implementation-ready`, or all required P1/P2 findings are corrected and re-reviewed.
3. User approves this `status: proposed` plan; approval does not activate CoS or execute any task.

The plan is complete only after later execution and `skill-verification-before-completion` confirm every task-local proof, slice acceptance, whole-frontend check, backend regression, E2E journey, deviation, blocker, and legacy retirement decision.
