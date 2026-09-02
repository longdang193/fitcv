---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: active
name: fitcv-residual-journey-verification
parent_spec: none
targets:
  - docs/superpowers/plans/2026-09-02-fitcv-residual-journey-verification-plan.md
---

# FitCV Residual Journey Verification Plan

## Goal

Obtain fresh, bounded evidence for residual Personal FitCV completion-gate journeys left incomplete by the 2026-08-30 closure plan. Preserve its `STAGES 11–13 INCOMPLETE` verdict until every required claim has direct browser, backend, persistence, and failure-state proof.

## Implementation Outcomes

### Residual journey evidence

Fresh disposable evidence covers first-time profile creation and confirmation, successful and failed or empty Scan behavior, mixed-result review, Scan reuse, cancellation recovery, refusal, personalization, restart, and the complete `/app` workflow.

### Safe closure decision

Each claim records request or exit status, browser evidence where applicable, persisted IDs and final state, runtime/provider identity, disposable database integrity, and exact blockers. Unsupported capability or missing fixture remains `INCOMPLETE`; no threshold, provider, router, protected database, or legacy UI change is accepted as proof.

## Execution Approach

- Mode: `parallel-capable`
- Coordination: `git-tracked`
- Default task executor: `codex`
- Required skills: `skill-plan-document-reviewer`, `skill-executing-plans`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-verification-before-completion`
- Isolation: `current workspace` for plan and evidence classification; unique disposable runtime/data directories for every live lane
- Commit policy: verified per-task checkpoint commits require explicit user approval; no push, merge, publication, source patch, external authentication, or protected-data mutation
- Preauthorized local actions: inspect source and tests, run existing validators, use configured local runtime/provider, verify approved provider model through disposable onboarding, confirm disposable profile setup, use browser against disposable runtime, create disposable evidence, and update this plan ledger after accepted proof
- User-approval actions: source or contract edits, new external provider/authentication setup, provider data egress outside approved `http://127.0.0.1:20128/v1`, external writes, threshold changes, protected database access or mutation, destructive cleanup, push, merge, publication, and scope expansion
- Latest approval: user authorized local disposable onboarding/provider model verification and confirmed-profile setup on September 2, 2026; user additionally approved one supplemental Task 3 Run and budget extension for eligible personalization proof; existing provider route and model only
- Parallel ownership: Task 2 owns `.tmp/fitcv-residual-task2` and Herdr session `fitcv-task2-retry`; Task 4 owns `.tmp/fitcv-residual-task4` and Herdr session `fitcv-task4`; no shared disposable files or runtime processes
- Sequential fallback: Task 1 → Tasks 2 and 4 in parallel → Task 3 after Task 2 → Task 5 after Tasks 2–4; stop at first hard blocker in each lane and record remaining claims incomplete

## Coordination State

- Coordination owner: `single lead Codex controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `7ca84a8674566ddc0f177a5f28108611e85f2bdd`
- Expected workspace: current `main`; existing disposable `.tmp/`, `.playwright-mcp/`, and `frontend/test-results/` remain out of scope
- Next action: retain `STAGES 11–13 INCOMPLETE`; run final validators and leave source changes uncommitted
- Blockers: provider-app Run and CV completed, but router request-details redacts live request bodies; personalized mode activated but ordering did not change; refusal budget was consumed by screening rejection before CV evidence gate; cancellation and restart/reopen now pass through fresh `/app` evidence

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | baseline, fixture, runtime, and budget ledger | `.tmp/fitcv-residual-task1/evidence/baseline.json`; validators passed; zero Scan/Run budgets consumed |
| Task 2 | `completed` | current | `codex` | Task 1 | browser-first successful workflow with mixed outcomes and grounded CV | `.tmp/fitcv-residual-task2/evidence/status.json`, `scan-proof.json`, `run-proof.json`, `cv-preview.md`, `persistence-proof.json`; Scan `scan-eab098c1f397`, Run `059d05f6-9f8c-434e-9e7a-ff8dd42caae5`, CV `7d2a1bab-cd22-4f3e-8b8d-afed9895ccdb`; budgets `1/1/1` |
| Task 3 | `blocked` | current | `codex` | Task 2 | supplemental eligible personalization and weak-fit/high-interest ordering proof | `.tmp/fitcv-live-personalization-20260902/evidence/final-disposition.json` and `task3-reopen-disposition.json`; candidate activation, effective Personalized mode, reversible baseline, and restart/reopen pass, but ranked order is unchanged |
| Task 4 | `blocked` | current | `codex` | Task 1 | refusal and cancellation/recovery proof or exact capability blockers | `.tmp/fitcv-live-cancel-20260902/final-disposition.json` proves truthful cancellation; `.tmp/closure-live-failure-20260902/evidence2/task4-final-disposition.json` records refusal blocked before CV gate because exact refusal budget is consumed |
| Task 5 | `blocked` | current | `codex` | Tasks 2–4 | independent review and final claim disposition | Fresh Herdr `closure-review-final` returned `BLOCKED`; `.tmp/closure-review-20260902/review.json`; no source defect substantiated, but ordering, refusal-gate, and live payload observability claims remain incomplete |

## Task Breakdown

### Task 1: Establish disposable runtime and fixture contract

**Purpose:**
- Freeze source/runtime identity and prepare disposable state without consuming Scan or Run budgets.

**Task Function:**
- Validate prerequisites, fixture compatibility, evidence boundaries, and per-lane operation budgets.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: cross-boundary scope, provider risk, and completion-gate coverage.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent check of scope, budget, and evidence sufficiency.

**Specification Coverage:**
- `docs/intent/success-outcomes.md` Completion Gate claims 1–26 and normal-use boundary.

**Required Skills:**
- `skill-plan-document-reviewer`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `docs/intent/success-outcomes.md:Completion Gate`
- Inspect: `scripts/run_fitcv_local_p0_acceptance.py`
- Inspect: `scripts/run_fitcv_local_p20_acceptance.py`
- Inspect: `tests/test_fitcv_cp/acceptance_harness.py`
- Inspect: `config/runtime/control_plane.yaml`
- Verify: `data/2026-06-24-Munich_Electrification-CV.md`

**Dependencies:**
- Current `main` must equal `origin/main`; protected `data/fitcv_cp.sqlite3` remains untouched.

**Authority:**
- Preauthorized local actions: read-only inspection, fixture validation, disposable directory creation, and configured runtime readiness checks.
- Stop for: source drift, missing provider approval, authentication need, protected-data access, or fixture lacking validated `preferences` and source references.

**Steps:**
- [x] Record `git status --short --branch`, `git rev-parse HEAD`, `git rev-parse origin/main`, and `git diff --check`.
- [x] Create one disposable data root per live lane; copy only supported fixtures and configured controller overlay.
- [x] Validate profile source, confirmation prerequisites, provider route/model identity, database integrity, and `REDIS_URL`/inline-mode contract before any Scan or Run.
- [x] Record budget ledger: Task 2 one Scan/one Run/one CV; Task 3 one reuse Run and one failed-or-empty Scan; Task 4 one refusal Run and one cancellation-capable Run.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root .`
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .`
- Expected: validators pass; source SHA, runtime identity, fixture IDs, disposable paths, and unused operation budgets are recorded.

**Exit Criteria:**
- Disposable lanes are isolated, fixture passes validation, provider access is already configured, and no live Scan or Run budget was consumed.

### Task 2: Prove browser-first successful workflow

**Purpose:**
- Prove first-time profile lifecycle and useful normal workflow through `/app`, including mixed-result review and grounded CV output.

**Task Function:**
- Execute one browser-led vertical journey and reconcile visible state with direct backend and SQLite evidence.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: browser interaction, responsive/accessibility state, and frontend/backend boundary judgment.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent check of browser evidence and persisted-state claims.

**Specification Coverage:**
- Completion Gate claims 1–8, 10, 12–18, 20–21, and 25.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `frontend/e2e/candidate-profile.spec.ts`
- Inspect: `frontend/e2e/integration-flows.spec.ts`
- Inspect: `frontend/src/features/candidate-profile/route.tsx`
- Inspect: `frontend/src/features/scans/route.tsx`
- Inspect: `frontend/src/features/runs/route.tsx`
- Inspect: `frontend/src/features/cv-review/route.tsx`
- Verify: `scripts/run_fitcv_local_p0_acceptance.py`

**Dependencies:**
- Task 1 complete; profile fixture has validated `preferences`; selected tracked companies and jobs pass preflight for one suitable and one poor result.

**Authority:**
- Preauthorized local actions: one disposable browser-first profile creation, one Scan, one Run, one generated CV, bookmark create/remove, one interest rating, and one restart/reopen in Task 2 data root.
- Stop for: no mixed outcome, no suitable job, provider failure after approved local verification, unsupported browser path, unexpected mutation, or request to exceed listed budgets.

**Steps:**
- [x] Upload supported CV through `/app`, review source references, reject unsupported suggestion, save unfinished state, resume, confirm profile, and capture IDs plus browser snapshots.
- [x] Create one supported Scan, inspect output, start one Run with confirmed profile, and capture Scan/Run/job/stage IDs and terminal states.
- [x] Verify mixed good/poor result reasons, fit/interest separation, bookmark create/remove, personalization availability or insufficient-evidence message, CV preview/download, and persisted checksums.
- [x] Reopen `/app` without terminal commands and compare visible profile, Run, bookmark, feedback, personalization, and CV state with disposable SQLite/API truth.

**Verification:**
- Supplemental p0 acceptance not run; browser and persisted evidence used instead.
- Targeted candidate-profile E2E checks passed; full listed E2E suite not run.
- [x] Browser network/snapshot capture from `/app` against Task 2 disposable runtime.
- [x] Read-only SQLite/API persistence proof saved at `.tmp/fitcv-residual-task2/evidence/persistence-proof.json` for profile, Scan, Run, jobs, CV, bookmark, interest, personalization, and reopen state.
- Expected: browser flow reaches useful result; every claimed ID/state matches persisted truth; missing mixed or CV output records `INCOMPLETE` without retrying the budget.

**Exit Criteria:**
- Task 2 claims receive evidence-grade browser, HTTP, persisted-state, and final-side-effect proof, or exact incomplete dispositions.

### Task 3: Prove Scan failure, reuse, personalization, and restart

**Purpose:**
- Cover later-session and non-happy Scan journeys without changing Task 2 evidence.

**Task Function:**
- Exercise reusable Scan input, understandable empty/failed outcome, ordering controls, and restart persistence.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: state identity, reuse semantics, and failure-state correctness.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: direct verification of Scan/Run identity and final persisted state.

**Specification Coverage:**
- Completion Gate claims 9, 11, 19, 23–25.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/scan_worker.py`
- Inspect: `src/fitcv_cp/run_lifecycle.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `frontend/src/features/scans/api.ts`
- Inspect: `frontend/src/features/runs/api.ts`
- Verify: `scripts/run_fitcv_local_p0_acceptance.py`

**Dependencies:**
- Task 2 successful Scan and confirmed profile IDs are available; Task 3 uses a separate disposable data root for failed/empty Scan proof.

**Authority:**
- Preauthorized local actions: one later Run reusing Task 2 Scan, one failed-or-empty Scan in separate disposable state, one personalization selection/reversion, and one restart/reopen.
- Stop for: duplicate Scan/Run beyond budget, unsupported reuse or personalization capability, or state divergence.

**Steps:**
- [x] Start later Run using Task 2 Scan ID; verify input snapshot references same Scan output and no new Scan was created.
- [x] Execute one empty-or-failed Scan in separate disposable state; capture user-facing outcome, next action, HTTP status, terminal state, and persisted error/empty rows.
- [x] Select personalized ordering and return to normal ordering; fresh evidence proves rating persistence, candidate create/activate, effective Personalized Ranking, and baseline reversion.
- [ ] Prove weak-fit/high-interest ranked-order change; current disposable fixture produces identical baseline and personalized order, so claim remains `BLOCKED`.
- [x] Restart or reopen runtime and compare profile revisions, Scan, reused Run, settings, bookmarks, feedback, and personalization state; fresh evidence proves state identity across restart/reopen.

**Verification:**
- [x] Supplemental P0 acceptance intentionally skipped; duplicate live actions would exceed approved Scan/Run budgets.
- [x] Read-only Python `sqlite3` and HTTP assertions saved at `.tmp/fitcv-residual-task3/evidence/state-check.py` for Scan and Run identity, reuse decision, empty state, and restart state.
- [x] Browser snapshots and network capture saved for empty Scan, reuse, ordering, and reopen views.
- Expected: reuse points to earlier Scan; failed/empty Scan explains next action; ordering switch is reversible; restart preserves state.

**Exit Criteria:**
- Claims 9, 11, 19, and 24 receive direct evidence or exact capability blockers; Task 3 never relabels unsupported behavior as passed.

### Task 4: Prove refusal and cancellation recovery

**Purpose:**
- Prove truthful handling when CV generation refuses insufficient evidence and when Run cancellation or interruption occurs.

**Task Function:**
- Trigger bounded failure states and compare browser guidance with backend terminal state and stored artifacts.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: failure semantics, recovery identity, and data-safety risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent side-effect and rollback/recovery verification.

**Specification Coverage:**
- Completion Gate claims 22–23.

**Required Skills:**
- `skill-backend-verification`
- `skill-full-stack-integration`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/orchestrator.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/run_artifact_contracts.py`
- Inspect: `frontend/src/features/runs/route.tsx`
- Inspect: `frontend/src/features/cv-review/route.tsx`
- Verify: `scripts/run_fitcv_local_p20_acceptance.py`

**Dependencies:**
- Task 1 complete; refusal fixture must be source-valid but insufficient for trustworthy CV generation; cancellation capability must be available without Redis/provider changes.

**Authority:**
- Preauthorized local actions: one refusal Run and one cancellation-capable Run in disposable state; read-only final-state inspection.
- Stop for: Redis or external provider/auth setup, cancellation capability unavailable, destructive recovery, or any need to lower fit thresholds.

**Steps:**
- [x] Submit refusal fixture through normal `/app` UI boundary; source-valid fixture reaches screening but is rejected with `seniority_mismatch` before CV Analysis/CV Generation. Refusal claim remains `BLOCKED`; refusal budget `1/1` is consumed.
- [x] Start cancellation-capable Run through normal `/app` UI boundary; fresh evidence proves `running → cancelling → cancelled`, Cancel control visibility, skipped outcome, replay identity, and reload state.
- [x] Record exact refusal capability blocker and cancellation proof; preserve `INCOMPLETE` for refusal only; no injected unit failure substituted for live refusal proof.

**Verification:**
- [x] Read-only SQLite/API evidence saved under `.tmp/fitcv-live-cancel-20260902/final-disposition.json`; cancellation terminal state, skipped outcome, replay identity, and SQLite integrity are `ok`.
- [x] Refusal evidence saved under `.tmp/closure-live-failure-20260902/evidence2/task4-final-disposition.json`; fixture stopped at screening, so CV refusal behavior is not claimed.
- [x] Browser captures saved under `.tmp/fitcv-live-cancel-20260902/artifacts/`; refusal remains unavailable because provider-backed profile readiness is blocked.
- Expected: failure states are truthful and side effects are consistent; unsupported capability is explicitly incomplete.

**Exit Criteria:**
- Claims 22–23 receive direct boundary, failure, final-state, and browser evidence or exact blockers.

### Task 5: Independent review and closure reconciliation

**Purpose:**
- Audit residual evidence and produce one final closure verdict without modifying historical evidence.

**Task Function:**
- Review claim coverage, evidence identity, safety boundaries, and plan/Git consistency.

**Template Profile:**
- Controller-selected: `review`
- Selection basis: independent whole-change and evidence-set assessment.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead accepts one independent review result.

**Specification Coverage:**
- Completion Gate claim 26 and all residual claims from Tasks 2–4.

**Required Skills:**
- `skill-plan-document-reviewer`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/superpowers/plans/2026-08-30-fitcv-frontend-closure-verification-plan.md`
- Inspect: this plan and all task evidence roots
- Verify: current `main` source and test state

**Dependencies:**
- Tasks 2–4 completed or explicitly blocked with evidence.

**Authority:**
- Preauthorized local actions: read-only review, validators, evidence reconciliation, and this plan ledger update.
- Stop for: evidence identity mismatch, stale source SHA, unrecorded mutation, or unresolved required claim.

**Steps:**
- [x] Reconcile every residual claim with one disposition: Task 1 and Task 2 `ALREADY PROVEN`; Task 3 lifecycle, effective mode, and restart `PROVEN` with ranked-order change blocked; Task 4 cancellation `PROVEN` with refusal blocked; full closure `REQUIRED AND MISSING`.
- [x] Run fresh independent read-only review against exact source SHA and evidence index; Herdr reviewer returned `BLOCKED` with no source defect substantiated, citing incomplete ranked-order, refusal-gate, and live payload-observability proof.
- [x] Run final planning validators, `git diff --check`, and `git status --short --branch`; validators and whitespace checks pass, with disposable evidence and plan remaining untracked under existing policy.
- [x] Retain `STAGES 11–13 INCOMPLETE` because live provider payload assertion, effective order change, and CV refusal-gate proof remain incomplete; Stage 14 remains inactive.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root .`
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .`
- [x] `git diff --check`
- Expected: no stale status, unowned claim, unexplained blocker, or plan/Git mismatch remains.

**Exit Criteria:**
- Independent review completed with `PASS`; final claim matrix and `STAGES 11–13 INCOMPLETE` verdict match fresh repository and disposable-runtime evidence.

## Verification

- `python scripts/validate_template_required_sections.py --repo-root .`
- `python scripts/validate_planning_lifecycle.py --repo-root .`
- `git diff --check`
- From `frontend/`: `npm run typecheck`, `npm run test`, `npm run test:a11y`, and `npm run build` when source changes occur.
- Direct backend evidence for every live lane; browser evidence for every `/app` journey.

## Completion Criteria

The plan is ready for completion verification when:

1. every residual claim has fresh evidence or an exact `INCOMPLETE`/`BLOCKED` disposition
2. browser evidence covers first-time, success, failure, reuse, cancellation, refusal, personalization, and restart journeys where capability permits
3. direct backend and persistence proof accompanies every material live claim
4. disposable runtime/provider/database boundaries are recorded and protected data remains untouched
5. independent review passes and plan/Git state reconcile cleanly

This plan does not authorize Stage 14, legacy UI removal, threshold changes, provider/router changes, protected database mutation, new authentication, or publication.

## Approved Residual Remediation (2026-09-02)

- **Policy activation:** New `/app` JSON contract exposes `GET /personalization/optimization`, candidate creation at `POST /personalization/optimization/candidate`, and activation at `POST /personalization/optimization/candidates/{snapshot_id}/activate`. Evidence-head, parent, actor, and stale-state checks remain required.
- **Profile payload:** Provider-facing CV generation now removes persistence-only `candidate_profile_id` and `revision` metadata while preserving stored run snapshots and canonical profile content.
- **Cancellation:** Local cancellation terminalizes unclaimed queued and awaiting-continue runs safely, closes open stages, preserves terminal replay identity, and keeps `/app` cancellation UI polling and failure messaging truthful.
- **Fresh checks:** Backend focused suites pass; frontend personalization and runs tests pass `17/17`; frontend `typecheck` and `build` pass; `/app` `runs.spec.ts` passes `4/4`; `git diff --check` passes.
- **Independent review:** Herdr top-level review returns `PASS`, with no P1/P2/P3 finding substantiated.
- **Remaining disposition:** Live provider-boundary and full first-time disposable browser/provider journey evidence remains absent. Keep `STAGES 11–13 INCOMPLETE`; do not activate Stage 14, push, or claim product closure from automated checks alone.
