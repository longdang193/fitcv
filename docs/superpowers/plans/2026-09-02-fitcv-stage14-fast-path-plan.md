---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
name: fitcv-stage14-fast-path
targets:
  - frontend/
  - frontend/package-lock.json
  - src/fitcv_cp/app.py
  - src/fitcv_cp/local_routes.py
  - packaging/windows/fitcv-local.spec
  - scripts/build_fitcv_local.ps1
  - tests/test_fitcv_cp/test_app.py
  - docs/superpowers/plans/2026-09-02-fitcv-stage14-fast-path-plan.md
---

# FitCV Stage 14 Fast-Path Release Plan

## Release Decision

`APPROVED — PERSONAL TECHNICAL PREVIEW`.

Stage 14 is complete for bounded personal use from one exact extracted bundle.
Installer execution and public beta distribution remain deferred. Current
workspace changes remain uncommitted and are not production changes. Stage 11–13
closure remains `INCOMPLETE`; this plan does not convert incomplete evidence
into closure.

## Goal

Use new `/app` as a bounded personal technical preview while preserving legacy
`/admin/*` behavior and keeping all unproven journeys explicitly out of scope.

## Implementation Outcomes

### Personal technical-preview package

One exact clean release candidate produces a lockfile-backed frontend build,
PyInstaller bundle, build manifest, and SHA-256 evidence. Disposable extracted
bundle smoke proves `/app` loads from packaged resources without static-asset
fallback or launch-time failure. Installer distribution is deferred.

### Minimum runtime proof

Read-only backend probes and browser shell/deep-link/error smoke pass against a
fresh disposable install. No new Scan or Run is created by this plan. Existing
direct tests remain the contract proof for backend behavior.

### Compatibility and rollback readiness

The legacy `/admin/*` inventory is recorded below and checked before personal
use. Legacy routes remain available. Exact candidate hash, evidence bundle,
stop conditions, and a stop-and-preserve rollback action are recorded before
personal use.

## Current Truth And Constraints

- `HEAD` and `origin/main` both equal `7ca84a8674566ddc0f177a5f28108611e85f2bdd`.
- `main` has 20 modified tracked files: frontend runs/personalization UI and tests; backend app, optimization, lifecycle, SQLite, CV, and agentic generation code; related backend tests.
- Untracked paths are `.tmp/`, `frontend/.tmp/`, and `docs/superpowers/plans/2026-09-02-fitcv-residual-journey-verification-plan.md`.
- The current dirty worktree is preserved. Do not reset, stash, commit, branch, push, or discard it as part of this plan.
- `/` redirects to `/app`; `/app` and `/app/{full_path:path}` serve `frontend/dist/index.html`; `/app/assets` serves packaged assets when present.
- `frontend/vite.config.ts` owns `base: "/app/"` and outputs `frontend/dist`.
- `scripts/build_fitcv_local.ps1` runs `npm ci`, `npm run build`, import smoke, PyInstaller, bundle-size check, `build.json`, and `SHA256SUMS.txt` generation.
- `packaging/windows/fitcv-local.spec` packages `frontend/dist` under `frontend` in the executable bundle.
- Existing residual evidence accepts successful disposable workflow, Scan reuse/empty-state behavior, cancellation, and restart/reopen; it does not prove every completion-gate claim.
- Protected `data/fitcv_cp.sqlite3`, provider route/model, router behavior, thresholds, legacy templates, and legacy UI remain unchanged.

## Fast-Path Boundary

Included:

- New `/app` launch as a single-user personal technical preview.
- Existing frontend build and packaged-resource path.
- Read-only health/readiness/settings/profile/Scan/Run/personalization smoke.
- Existing frontend unit, accessibility, build, and browser shell checks.
- Legacy `/admin/*` coexistence and compatibility inventory.
- Separate development worktree/branch for significant future product changes;
  no direct production-state development.

Excluded:

- New Scan or Run execution during plan authoring or gate execution.
- Installer execution, public beta distribution, and production deployment.
- Significant product development against personal/live runtime state.
- Provider setup, authentication, model or router changes, threshold changes,
  database migration, protected database access, source patches, test patches,
  config changes, legacy UI deletion, or Git history changes.
- Claiming Stage 11–13 closure, production readiness, full provider-boundary
  observability, personalized order change, or CV refusal proof.

## Execution Approach

- Mode: `parallel-capable`
- Coordination: `git-tracked`
- Default task executor: `codex`
- Required skills: `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`
- Isolation: `current workspace` for read-only inspection; separate clean release checkout or exported clean artifact required for build
- Commit policy: `no commits during execution`
- Preauthorized local actions: read declared files, run existing validators/tests, build in release-owned `dist/` and `build/`, install into disposable Windows user state, run read-only HTTP/browser smoke, and record evidence in release-owned disposable output
- User-approval actions: beta distribution, provider/authentication changes, external writes, protected-data access, destructive cleanup, source/test/config edits, legacy deletion, commit, push, merge, branch creation, or publication
- Parallel ownership: Task 3 diagnosis and Task 5 compatibility smoke may run in parallel; no shared mutation.
- Dependency gates: Task 1 → Task 2 → Task 3 → Task 4; Task 5 may run beside Task 3; Task 6 joins after Tasks 2–5; stop at first hard blocker.

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `7ca84a8674566ddc0f177a5f28108611e85f2bdd`
- Expected workspace: current dirty `main` preserved; exported clean candidate r2 owns release evidence
- Next action: use exact extracted bundle for personal preview; make significant product changes only in separate development worktree/branch. Do not run new Scan or Run during gate execution.
- Blockers: none
- Deferred: installer execution, public beta distribution, formal rollback rehearsal, and production deployment. Stage 11–13 incomplete; personalized ordering, CV refusal-gate, and live provider request-body observability remain unproven.
- Approval: user approved Stage 14 personal-preview scope on September 2, 2026; no public beta distribution or legacy deletion.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | exported candidate r2 | `codex` | none | exact clean candidate, status, SHA, and protected-boundary check | `.tmp/stage14-release-candidate-r2/candidate-manifest.json`; `main` preserved |
| Task 2 | `completed` | exported candidate r2 | `codex` | Task 1 | frontend/package/build and extracted-bundle proof | `.tmp/stage14-release-candidate-r2/evidence/stage14-r2/stage14-r2-final.json`, `.tmp/stage14-release-candidate-r2/evidence/stage14-packaging-policy-exception.md`; bundle/hash/build PASS; installer deferred by scope |
| Task 3 | `completed` | disposable install | `codex` | Task 2 | read-only backend boundary smoke | `.tmp/stage14-release-candidate-r2/evidence/stage14-task3-retry-main/stage14-task3-retry-main-report.md`; 715 focused tests, GET probes, SQLite integrity, process/listener cleanup PASS |
| Task 4 | `completed` | disposable install | `codex` | Task 3 | browser `/app` shell, deep-link, error, accessibility, console smoke | `.tmp/stage14-release-candidate-r2/evidence/stage14-task4-browser-r4/STAGE14-TASK4-REPORT.md`; onboarded fixture, missing-run error/back, responsive/accessibility/security invariants PASS |
| Task 5 | `completed` | current source/read-only | `codex` | Task 1 | legacy `/admin/*` inventory and coexistence disposition | `.tmp/stage14-release-candidate-r2/evidence/stage14-task5-legacy-smoke.md`; route-manifest PASS and representative runtime PASS; `/app` authoritative |
| Task 6 | `completed` | release records | `codex` | Tasks 2–5 | personal preview authorization, monitoring, stop action, risk acceptance | `.tmp/stage14-release-candidate-r2/evidence/stage14-task6-release-decision.md`, `.tmp/stage14-release-candidate-r2/evidence/stage14-packaging-policy-exception.md`, `.tmp/stage14-release-candidate-r2/evidence/stage14-stage11-13-risk-acceptance.md`; personal preview approved; public beta and installer deferred |

## Task Breakdown

### Task 1: Freeze release candidate and boundaries

**Purpose:**
- Prevent dirty-worktree, stale-SHA, protected-data, or unapproved-runtime release.

**Task Function:**
- Release-candidate identity and safety preflight.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: exact source identity and no delegated work required.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final verification remains lead-owned.

**Specification Coverage:**
- Current Git state, residual closure plan, protected-data boundary, and no-new-Scan/Run constraint.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md`
- Inspect: `docs/superpowers/plans/2026-08-30-fitcv-frontend-closure-verification-plan.md`
- Inspect: `docs/superpowers/plans/2026-09-02-fitcv-residual-journey-verification-plan.md`
- Inspect: `src/fitcv_cp/app.py:_resolve_frontend_dist_dir`, `src/fitcv_cp/app.py:serve_app`
- Verify: `git status --short --branch`, `git rev-parse HEAD`, `git rev-parse origin/main`, `git diff --check`

**Dependencies:**
- User-approved clean candidate must exist without discarding current changes.

**Authority:**
- Preauthorized local actions: read-only Git/source inspection and evidence recording.
- Stop for: dirty release candidate, SHA drift, protected database access, provider/auth change, or request to create Scan/Run.

**Steps:**
- [x] Record exact candidate SHA, origin SHA, worktree status, and release operator.
- [x] Confirm candidate source is clean and matches intended reviewed source; preserve current dirty worktree unchanged.
- [x] Record that personal preview uses disposable validation state and never `data/fitcv_cp.sqlite3`.

**Verification:**
- [x] `git status --short --branch; git rev-parse HEAD; git rev-parse origin/main; git diff --check`
- Expected: clean selected release candidate, exact SHA recorded, no protected-data or provider action.

**Exit Criteria:**
- Candidate identity and safety boundaries pass for personal preview.

### Task 2: Build package and prove extracted-bundle launch

**Purpose:**
- Prove lockfile, frontend bundle, packaged resources, hashes, and extracted-bundle launch on fresh disposable state.

**Task Function:**
- Reproducible package and clean extracted-bundle smoke.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: deterministic existing build script.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final release verification owns acceptance.

**Specification Coverage:**
- Vertical-slice whole-frontend/package proof and `/app` static-asset boundary.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `frontend/package.json`, `frontend/package-lock.json`, `frontend/vite.config.ts`
- Inspect: `scripts/build_fitcv_local.ps1`, `packaging/windows/fitcv-local.spec`
- Verify: `frontend/dist/index.html`, `dist/fitcv-local/fitcv-local.exe`, `dist/fitcv-local/build.json`, `dist/SHA256SUMS.txt`

**Dependencies:**
- Task 1 complete; release candidate clean.

**Authority:**
- Preauthorized local actions: build and extracted-bundle launch only in release-owned disposable output/state.
- Stop for: missing `npm ci`, failed build/typecheck/test, missing assets, bundle over 600 MB, missing executable, or protected-data touch.

**Steps:**
- [x] From `frontend/`, run `npm ci`, `npm run typecheck`, `npm run test`, `npm run test:a11y`, `npm run build`.
- [x] From repository root, run `$buildId = (git rev-parse --short HEAD).Trim(); pwsh -File scripts/build_fitcv_local.ps1 -Version 0.1.0 -BuildId $buildId`.
- [x] Verify `frontend/dist/index.html`, at least one hashed asset, `dist/fitcv-local/fitcv-local.exe`, `build.json`, and `SHA256SUMS.txt`; installer output remains deferred.
- [x] Launch exact extracted bundle in clean disposable Windows user state; record executable hash, launch URL, and bundle size.

**Verification:**
- [x] `Get-Content dist/fitcv-local/build.json; Get-FileHash dist/fitcv-local/fitcv-local.exe -Algorithm SHA256; Get-ChildItem dist/fitcv-local -Recurse -File`
- Expected: manifest build ID equals candidate short SHA; hash list matches files; bundle is at or below existing 600 MB budget; extracted bundle launches without 503 asset fallback.

**Exit Criteria:**
- Extracted-bundle/package/build gate passes. Installer execution and public beta packaging remain deferred by personal-use scope.

### Task 3: Run read-only backend smoke

**Purpose:**
- Prove packaged local host and canonical JSON boundaries without creating new work.

**Task Function:**
- Backend boundary, response-shape, and side-effect smoke.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: read-only checks fit current risk and user constraint.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: no separate validator needed for bounded read-only probes.

**Specification Coverage:**
- Server-owned readiness, settings, profile, Scan, Run, personalization, and `/app` host contracts.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`
- Verify: `tests/test_fitcv_cp/test_app.py`, affected existing backend test modules

**Dependencies:**
- Task 2 extracted bundle available on loopback; no new Scan or Run budget.

**Authority:**
- Preauthorized local actions: GET/HEAD requests and existing test execution only.
- Stop for: mutation request, external provider call, protected DB access, non-2xx readiness failure, malformed JSON, or secret exposure.

**Steps:**
- [x] Probe `GET /healthz`, `GET /local/readiness`, `GET /settings`, `GET /candidate-profiles`, `GET /scans`, `GET /runs`, and `GET /personalization`.
- [x] Probe `GET /app` and one emitted `/app/assets/*` URL; confirm no `503` fallback text and no missing asset.
- [x] Run existing focused backend tests without enabling live Scan/Run actions; record status, response envelope, and final disposable DB integrity.
- [x] Confirm requests remain same-origin/loopback and contain no provider key or credential material.

**Verification:**
- [x] Save HTTP status/shape evidence and read-only DB integrity result in release-owned disposable output.
- Expected: all probes return documented success/error envelopes; no mutation, provider egress, protected DB access, or secret exposure occurs.

**Exit Criteria:**
- Backend host and JSON smoke pass with no side effects.

### Task 4: Run browser `/app` smoke

**Purpose:**
- Prove new-app shell and safe navigation on fresh install without claiming unproven live journeys.

**Task Function:**
- Browser smoke, accessibility, and failure-state verification.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing Playwright coverage is sufficient for minimum smoke.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final verification owns result reconciliation.

**Specification Coverage:**
- `/app` launch, navigation, deep link/hash state, graceful error, keyboard/accessibility basics, and no legacy HTML parsing.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `frontend/playwright.config.ts`
- Verify: `frontend/e2e/smoke.spec.ts`, `frontend/e2e/runs.spec.ts`, `frontend/src/test/a11y.test.ts`

**Dependencies:**
- Tasks 2–3 pass; packaged host is available at configured loopback base URL.

**Authority:**
- Preauthorized local actions: browser navigation, read-only UI checks, existing mocked/unit E2E checks, screenshots/snapshots.
- Stop for: uncaught console error, broken `/app` deep link, inaccessible required control, mutation beyond existing test mocks, or request to create Scan/Run.

**Steps:**
- [x] Run `npm run test:e2e -- --grep "FitCV Frontend Smoke & Shell|Runs Feature Journey"` from `frontend/` against fresh host.
- [x] Verify `/app/#/overview`, `/app/#/runs`, direct refresh/deep-link, missing-run error, navigation back, visible focus, and light theme.
- [x] Check desktop and narrow viewport shell, no uncaught console errors, no legacy HTML parser/fetch path, and no provider key in browser storage/network.
- [x] Record browser output and snapshots; do not treat mocked cancellation or missing-run checks as live backend proof.

**Verification:**
- [x] Existing Playwright smoke passes; `npm run test:a11y` passes; browser console has zero uncaught errors.
- Expected: `/app` renders from packaged assets, navigation and error state remain usable, accessibility smoke passes, and no new Scan/Run occurs.

**Exit Criteria:**
- Browser minimum gate passes on fresh install and supported desktop/narrow smoke views.

### Task 5: Inventory and protect legacy `/admin/*`

**Purpose:**
- Prove personal preview does not strand existing operators, artifact links, or compatibility consumers.

**Task Function:**
- Legacy route inventory and coexistence disposition.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: read-only route/source inventory; no legacy edits.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing route-manifest test supplies contract check.

**Specification Coverage:**
- Vertical-slice legacy retirement gate: preserve, explicitly redirect, or separately retire; personal preview does not retire.

**Required Skills:**
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py` admin route registrations and `src/fitcv_cp/templates/`
- Verify: `tests/test_fitcv_cp/test_app.py::test_admin_route_manifest_matches_native_fastapi_contract`

**Dependencies:**
- Task 1 candidate identity recorded; no route or template changes allowed.

**Authority:**
- Preauthorized local actions: read-only route enumeration and GET compatibility checks.
- Stop for: missing legacy route, changed redirect policy, template deletion, or any request to repurpose `/admin/*`.

**Inventory:**

- **HTML workspaces:** `/admin/api-providers`, `/admin/api-providers/{provider_id}`, `/admin/llm-configuration`, `/admin/prompt-management`, `/admin/system`, `/admin/settings`, `/admin/settings/{section}`, `/admin/scans`, `/admin/scans/{scan_id}`, `/admin/runs`, `/admin/runs/{run_id}`, `/admin/candidate-profiles`, `/admin/candidate-profiles/create`, `/admin/candidate-profiles/{profile_id}`, `/admin/synonyms`, `/admin/bookmarks`.
- **Run review and tabs:** `/admin/runs/{run_id}/review-queue`, `/admin/runs/{run_id}/tabs/enriched`, `/admin/runs/{run_id}/tabs/jobs-input`, `/admin/runs/{run_id}/tabs/profile`.
- **Run controls:** `/admin/runs/{run_id}/stop`, `/admin/runs/bulk/cancel`, `/admin/runs/bulk/archive`, `/admin/runs/bulk/unarchive`, `/admin/runs/{run_id}/continue`, `/admin/runs/{run_id}/retry`, `/admin/runs/{run_id}/archive`, `/admin/runs/{run_id}/repair-cancellation`, `/admin/runs/{run_id}/unarchive`, `/admin/upload-trigger`, `/admin/reconciler/run-attempts`, `/admin/runs/{run_id}/cv-review-action`, `/admin/runs/{run_id}/cv-review-batch-action`, `/admin/runs/{run_id}/decision-feedback/{alternative_id}`.
- **Artifacts and exports:** `/admin/cvs/{version_id}/download`, `/admin/runs/{run_id}/export.json`, `/admin/runs/{run_id}/hitl-review-audit.json`, `/admin/runs/{run_id}/cv-debug.json`, `/admin/runs/{run_id}/cv-generation-review-required.json`, `/admin/runs/{run_id}/cv-generation-trace.json`, `/admin/runs/{run_id}/agentic-live-trace.json`, `/admin/runs/{run_id}/cv-analysis-trace.json`, `/admin/runs/{run_id}/stage-artifacts.json`, `/admin/runs/{run_id}/stage-artifacts/{stage_id}.json`, `/admin/runs/{run_id}/artifacts.zip`, `/admin/runs/{run_id}/settings-used.json`, `/admin/runs/{run_id}/mapping-suggestions.json`, `/admin/runs/{run_id}/synonym-proposals.json`, `/admin/runs/{run_id}/synonym-proposals-trace.json`, `/admin/runs/{run_id}/synonym-suppression-diff.json`, `/admin/mapping-suggestions.json`, `/admin/synonym-proposals.json`, `/admin/runs/{run_id}/approved-synonym-proposals.yaml`, `/admin/synonyms/global.yaml`, `/admin/synonyms/global-domain.yaml`, `/admin/synonyms/global-role-family.yaml`, `/admin/enriched/export-filtered.zip`.
- **Diagnostics:** `/admin/diagnostics/orchestration-schema`, `/admin/process-events.json`.

**Steps:**
- [x] Compare inventory to native FastAPI registrations and route-manifest test.
- [x] Check representative legacy HTML, control, and artifact URLs remain reachable from fresh install.
- [x] Record every route as `preserved`; no route receives implicit redirect to `/app`.
- [x] Record that retirement needs separate approved plan, owner approval, and rollback path.

**Verification:**
- [x] Existing route-manifest test passes; representative legacy routes return expected status/content type; no legacy template is modified.
- Expected: all listed compatibility surfaces remain available and no personal-preview action deletes or repurposes them.

**Exit Criteria:**
- Legacy compatibility is inventoried, smoke-checked, and explicitly preserved.

### Task 6: Authorize personal technical preview

**Purpose:**
- Make personal-use decision explicit, limit exposure, and provide safe stop behavior without source or data rollback.

**Task Function:**
- Personal-preview acceptance, risk recording, and stop control.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: approval and evidence reconciliation are controller-owned.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: no independent execution lane authorized by user.

**Specification Coverage:**
- Personal technical preview, bounded stop behavior, incomplete-claim acceptance, and legacy coexistence.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: this plan, all Task 1–5 evidence, and residual closure disposition
- Verify: package manifest, hash list, smoke logs, compatibility matrix, and personal-preview record

**Dependencies:**
- Tasks 1–5 pass. Product owner explicitly accepts bounded personal-preview risk.

**Authority:**
- Preauthorized local actions: evidence reconciliation and release record update.
- Stop for: any failed gate, data-integrity warning, provider/router drift, legacy break, or unresolved safety finding.

**Steps:**
- [x] Set cohort to current personal user, one exact extracted-bundle hash, disposable validation state, and personal-preview labeling.
- [x] Exclude personalized ranked-order change, CV refusal-at-evidence-gate, and live provider request-body observability from acceptance claims.
- [x] Monitor launch failure, `/app` 5xx/503, missing assets, backend readiness errors, uncaught browser errors, data-integrity errors, and any legacy route regression.
- [x] Record stop-and-preserve action; prior package hash and installer distribution remain deferred by personal-use scope.
- [x] Obtain explicit product-owner risk acceptance for Stage 11–13 incomplete claims; acceptance is bounded and recorded in `.tmp/stage14-release-candidate-r2/evidence/stage14-stage11-13-risk-acceptance.md`.

**Rollback Path:**

1. Stop personal preview when any stop condition fires.
2. Capture package hash, build ID, runtime logs, browser evidence, HTTP evidence, and database-integrity result before cleanup.
3. Stop FitCV Local process through its normal UI/tray path; do not kill or delete user data as first action.
4. Preserve exact candidate bundle and stop using it; do not rebuild from dirty source.
5. Return to prior personal installation only if one exists; otherwise keep preview stopped until a verified package is available.
6. Keep personal-preview data backed up and isolated; never run destructive migrations or mutate protected DB during rollback.
7. Preserve failed package and evidence for diagnosis. Any fix requires a separate approved source/config plan and a new candidate gate run.

**Verification:**
- [x] Personal-preview record names candidate SHA, package hash, cohort, approver, incomplete claims, monitoring owner, and stop action; installer/public-beta fields are explicitly deferred.
- Expected: `PASS` for bounded personal technical preview only; installer execution, public distribution, and production readiness remain out of scope.

**Exit Criteria:**
- Personal technical preview is authorized, bounded, observable, and stoppable. Stage 14 is not public beta or production readiness.

## Known Incomplete Claims And Risk Acceptance

Current residual evidence records these limits:

- Personalized mode activation and reversion work, but weak-fit/high-interest
  ranked order did not change with current disposable fixture. Ranked-order
  claim remains `BLOCKED`.
- Refusal fixture stopped at screening with `seniority_mismatch` before CV
  Analysis/CV Generation. CV refusal-at-evidence-gate behavior remains
  `BLOCKED`; refusal budget is consumed and no injected failure substitutes for
  live proof.
- Provider router request details redact live request bodies. Provider payload
  observability claim remains incomplete even though provider-backed Run/CV
  success evidence exists.
- Automated checks and bounded disposable journeys do not prove full Stage
  11–13 closure. Stage 14 must not be described as production readiness.

Personal-preview risk acceptance requires all of the following in release record:

- One trusted user and fresh disposable install only.
- Explicit feature/use-case exclusion for the three incomplete claims above.
- Product owner acceptance of `STAGES 11–13 INCOMPLETE` during personal preview.
- Legacy `/admin/*` remains available as fallback.
- Candidate bundle remains available for immediate stop/recovery.
- Any user-visible failure, data-integrity anomaly, or legacy regression stops
  preview; no threshold lowering or provider workaround is permitted.

## Verification

- `python scripts/validate_template_required_sections.py --repo-root .`
- `python scripts/validate_planning_lifecycle.py --repo-root .`
- `git diff --check`
- Fresh release-candidate frontend commands: `npm ci`, `npm run typecheck`, `npm run test`, `npm run test:a11y`, `npm run build`
- Fresh package command: `pwsh -File scripts/build_fitcv_local.ps1 -Version 0.1.0 -BuildId $((git rev-parse --short HEAD).Trim())`
- Existing backend focused tests and route-manifest test; no new Scan or Run
- Existing Playwright shell/runs smoke and accessibility test against fresh install

## Completion Criteria

The plan is ready for completion verification when:

1. One clean candidate SHA and package hash are recorded; current dirty user work remains untouched.
2. Frontend lockfile, typecheck, unit tests, accessibility tests, build, bundle, hash, and extracted-bundle launch gates pass; installer is deferred.
3. Read-only backend probes pass with documented envelopes, no provider secret exposure, no mutation, and disposable DB integrity intact.
4. Browser `/app` shell, deep-link, error, accessibility, viewport, and console smoke pass without new Scan or Run.
5. Every listed legacy `/admin/*` compatibility surface is preserved or explicitly escalated to a separate approved retirement plan.
6. Stop conditions, stop/recovery sequence, monitoring owner, and personal-preview risk acceptance are recorded; prior package hash and installer rollback remain deferred.
7. Known incomplete claims remain labeled `BLOCKED`/incomplete; no Stage 11–13 or production-readiness overclaim appears.

Plan status may become `completed` after fresh verification confirms every
personal-preview criterion. Installer/public-beta gates and Stage 11–13 closure
remain explicitly deferred.
