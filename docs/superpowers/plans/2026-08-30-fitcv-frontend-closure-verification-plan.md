---
layer: change
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: active
name: fitcv-frontend-closure-verification
parent_spec: none
targets:
  - docs/superpowers/plans/2026-08-30-fitcv-frontend-closure-verification-plan.md
---

# FitCV Frontend Closure Verification Plan

## Review Disposition

The revised verdict is correct: `NOT READY — small contract patch required; architecture and task topology are already correct.` This plan incorporates only that patch. It does not redesign the frontend, change product behavior, revise the completed specification, retire legacy surfaces, or release.

## Goal

Close lifecycle stages 11–13 with traceable evidence for the completed greenfield frontend and its affected backend/API boundaries. Reuse accepted evidence first, obtain only missing proof, run one bounded real Personal FitCV probe when Task 2 identifies a required gap, perform independent whole-change review, and return one closure verdict.

## Implementation Outcomes

### Evidence-backed stage closure

Stage 11 frontend, backend/API, rendered, accessibility, and functional claims are classified against current source, tests, and applicable runtime evidence. Stage 12 completion-critical Personal FitCV journeys are mapped to explicit proof dispositions.

### Bounded real-user proof

Only claims classified as `REQUIRED AND MISSING` may enter one bounded real probe using the existing local FitCV runtime, configured provider, and approved supported profile input. No mock proof substitutes for a required real boundary.

### Independent final review

An independent read-only reviewer assesses the final closure candidate SHA and exact Task 1–3 evidence set. The lead records `STAGES 11–13 SATISFIED` or `STAGES 11–13 INCOMPLETE`; Stage 14 is never activated automatically.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Default task executor: `codex`
- Required skills: `skill-chief-of-staff`, `skill-executing-plans`, `skill-verification-before-completion`
- Isolation: lead uses `current workspace`; Task 4 uses a fresh isolated read-only review workspace; no write-capable product lane is authorized by this plan
- Commit policy: verified per-task checkpoint commits may record lead ledger transitions; source evidence SHA remains separate from coordination checkpoint SHA; no push, merge, or publication
- Preauthorized local actions: read declared sources, run existing validators/tests, use already-configured local runtime and browser capability for bounded proof, and update this plan's coordination ledger
- User-approval actions: source-code or contract changes, new provider setup or authentication, provider data egress, external writes, push, merge, publication, destructive cleanup, legacy deletion, and scope expansion
- Parallel ownership: none
- Sequential fallback: Tasks 1 → 2 → 3 → 4 → 5; stop at first hard blocker

## Coordination State

- Coordination owner: `CoS / lead Codex controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- Expected workspace: clean current `main` worktree; existing task worktrees are preserved and out of scope
- Next action: Record latest bounded Task 3 evidence, rerun fresh Task 4 review against that evidence, then rerun Task 5 closure verification
- Blockers: A supported Awin Greenhouse fixture was imported into disposable data and Scan succeeded, but Run stopped with `Missing required section: 'preferences'`; claims 7, 9, 11, 19, 22, 26 remain BLOCKED and claims 1–6, 8, 10, 12–18, 20–21, 23–25 still lack full browser-to-completion proof; original data/fitcv_cp.sqlite3 remains untouched
- Source evidence baseline: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- Final source under review: `87e4280392e27a0709ac39ae88b098134094802e`; product source candidate remains unchanged since `c1466eb66174f3d7bda22db44df204679312b57d`
- Coordination checkpoint: derive latest checkpoint with `git log -1 --format=%H -- <plan-path>`; do not copy checkpoint SHA into plan text
- Closure verdict: `STAGES 11–13 INCOMPLETE`; latest Task 3 stopped at Run validation; Task 4 and Task 5 prior evidence invalidated by later Task 3 evidence and require fresh reruns; Stage 14 remains inactive

Activation baseline:

- `main` HEAD: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- `origin/main`: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- Current worktree: clean
- Preserved unrelated worktrees: `.worktrees/fitcv-task-4` and `.worktrees/fitcv-task-5`; both contain untracked `frontend/test-results/` only
- Source changes authorized by user approval: bounded Task 1 `/personalization` correction only; no further source changes authorized

Before activation, commit this proposed plan so Git can recover its coordination ledger. Activation then changes plan `status` from `proposed` to `active` before Task 1 starts. At activation, CoS must record exact `main` HEAD, `origin/main`, worktree status, preserved unrelated changes, and `activation_source_commit`. Require `HEAD == origin/main` and no unexpected tracked changes. Every accepted evidence item records the source commit it proves. Each accepted task transition must update its complete ledger row, `Next action`, and evidence anchor in one lead checkpoint commit. Derive that checkpoint from plan history with `git log -1 --format=%H -- <plan-path>` when resuming or reviewing.

If a required defect correction changes source, stop current proof, record `final_candidate_source_commit` after correction, invalidate only affected evidence, rerun only affected proof, and make Task 4 review the final source candidate. Ledger-only checkpoint commits do not change `final_candidate_source_commit`. Task 1 source correction is user-approved; no further source correction is authorized without approval.
The lead controller is sole coordination-state writer. Runtime threads, agent sessions, temporary todos, and memory are not recovery state.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | Stage 11 evidence matrix and fresh validators | bounded baseline policy-lookup correction committed at `c1466eb66174f3d7bda22db44df204679312b57d`; Herdr review validator `PASS`; live dark-theme `/personalization` returned HTTP 200 |
| Task 2 | `completed` | current | `codex` | Task 1 | deterministic journey map and Live Probe Contract | Stage 12 map and bounded contract recorded; 20 claims require live proof, 6 claims explicitly blocked; no claim is not applicable |
| Task 3 | `blocked` | current | `codex` | Task 2 | bounded real Personal FitCV probe or explicit blocked/incomplete result | `BLOCKED` at Run validation; disposable runtime on port `18000` returned company import `201`, profile upload `202`, baseline approve `202`, derived `200`, confirm `201`; provider egress used with approved source; company `company-475efed79a1a` (`Awin Global`, `greenhouse`), profile `profile_9c17983c121944e994bb1ebcd5c66f16`, Scan `scan-888e73590570` succeeded with 2 rows, Run `046cfb42-c4e5-4766-b9bc-b5ec7a2e4819` failed with `Missing required section: 'preferences'`; no CV, bookmark, interest, cancel/recover, or reopen performed; original DB untouched |
| Task 4 | `pending` | fresh isolated review workspace | `codex` | Tasks 1–3 | fresh independent `PASS`, `FAIL`, or `BLOCKED` review bound to updated final source and latest Task 3 evidence | Prior `PASS` invalidated by later Task 3 evidence; rerun required |
| Task 5 | `pending` | current | `codex` | Tasks 1–4 | fresh completion verification and closure verdict | Prior `incomplete` verification invalidated by later Task 3 evidence; rerun required |

## Task Breakdown

### Task 1: Reconcile Stage 11 evidence

**Purpose:**
- Determine whether whole-frontend and affected backend/API evidence is already sufficient.

**Task Function:**
- Reconcile claims against canonical documents, source, tests, and applicable runtime evidence.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: broad evidence reconciliation with cross-boundary ownership and proof risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independently challenge evidence attribution and readiness classification.

**Specification Coverage:**
- Completed production specification, completed vertical-slice plan, frontend rules, backend/API contracts, and affected `docs/intent/success-outcomes.md` claims.

**Required Skills:**
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`
- Inspect: `docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md`
- Inspect: `docs/intent/success-outcomes.md`
- Inspect: `docs/fitcv-new-frontend.integration.md`
- Inspect: `frontend/`, `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/main.py`, `src/fitcv_cp/local_app.py`, `packaging/windows/fitcv-local.spec`, `scripts/build_fitcv_local.ps1`, affected `tests/test_fitcv_cp/`, and existing verification reports
- Modify: this plan's coordination ledger only
- Verify: `scripts/validate_template_required_sections.py`, `scripts/validate_planning_lifecycle.py`, `frontend/package.json`, and exact focused backend/frontend commands listed below

**Dependencies:**
- Activation baseline captured by CoS.
- No product source changes during reconciliation.

**Authority:**
- Preauthorized local actions: read-only inspection, existing validators, and declared focused tests.
- Stop for: source/spec conflict, baseline drift, missing canonical owner, or any requested product change.

**Steps:**
- [x] Capture activation baseline and confirm workspace identity.
- [x] Classify each applicable evidence class as `ALREADY PROVEN`, `MISSING PROOF`, or `NOT APPLICABLE`.
- [x] Reconcile affected backend/API proof without treating browser evidence as backend proof.
- [x] Record one matrix row per claim with `claim`, `canonical owner`, `evidence source/command`, `result`, `evidence source commit`, `freshness`, `disposition`, and `missing proof`.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root .`
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .`
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_frontend_host.py`
- [x] From `frontend/`: `npm run typecheck`, `npm run test`, `npm run test:a11y`, and `npm run build`; run `npm run test:e2e` only when an already-healthy browser runtime is available and record that runtime with the evidence.
- Expected: every Stage 11 claim has explicit disposition and SHA-bound evidence.

**Exit Criteria:**
- Stage 11 is `SATISFIED`, or exact missing/blocked claims are recorded. No generic PASS replaces the matrix.

**Stage 11 Evidence Matrix:**

| Claim | Canonical owner | Evidence source/command | Result | Evidence source commit | Freshness | Disposition | Missing proof |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Frontend type safety and unit/state coverage | `frontend/` and frontend tests | `npm run typecheck`; `npm run test` from `frontend/` | typecheck passed; `96 passed` | `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75` | fresh-this-turn | `ALREADY PROVEN` | none |
| Frontend accessibility coverage | `frontend/src/test/a11y.test.ts` | `npm run test:a11y` from `frontend/` | `1 passed` | `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75` | fresh-this-turn | `ALREADY PROVEN` | browser accessibility states remain covered only by E2E scope below |
| Frontend production build | `frontend/` and `src/fitcv_cp/app.py` host | `npm run build` from `frontend/` | Vite build passed; `94 modules transformed` | `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75` | fresh-this-turn | `ALREADY PROVEN` | packaged-resource proof not rerun |
| Backend/API focused boundaries and local host | `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/local_app.py` | Task 1 focused pytest commands; `python -m compileall -q src`; live `POST /settings` and `GET /personalization` | `3 passed` personalization regression; `464 passed` app suite; compile passed; live dark-theme `/personalization` HTTP 200 | `c1466eb66174f3d7bda22db44df204679312b57d` | fresh-this-turn | `ALREADY PROVEN` | live provider/data-dependent paths not covered by focused suite |
| Planning and artifact integrity | planning scripts and Git | both planning validators; `git diff --check` | all passed | `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75` | fresh-this-turn | `ALREADY PROVEN` | none |
| Browser shell and route journeys | `/app` frontend host and E2E specs | fresh `npm run test:e2e` from `frontend/`; Task 1 live route check against `http://127.0.0.1:8000` | fresh run `12 failed` with `ERR_CONNECTION_REFUSED` at `http://127.0.0.1:8000`; live dark-theme `/personalization` previously returned HTTP 200 | `c1466eb66174f3d7bda22db44df204679312b57d` | fresh-this-turn | `INCOMPLETE` | Re-run after supported frontend host/runtime is healthy |
| Independent Task 1 validator | Herdr top-level Codex main agent via `scripts/herdr_main_launcher.py` | Herdr session `fitcv-task-1`, agent `fitcv-task-1-validator`, profile `review` | `PASS`; verified source patch, regression coverage, focused suite, and live dark-theme `/personalization` HTTP 200; Task 2 may proceed | `c1466eb66174f3d7bda22db44df204679312b57d` | fresh-this-turn | `ALREADY PROVEN` | none for Task 1 acceptance; full E2E rerun remains tracked above |

### Task 2: Reconcile Stage 12 journey coverage

**Purpose:**
- Map completion-critical Personal FitCV journey claims to existing evidence and define only required live proof.

**Task Function:**
- Convert success outcomes into deterministic acceptance claims and a bounded Live Probe Contract.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: completion-gate interpretation and proof-scope risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent check that every disposition is explicit and supported by canonical outcomes.

**Specification Coverage:**
- `docs/intent/success-outcomes.md` Personal Job-Search Journey and Completion Gate; completed production specification journey requirements.

**Required Skills:**
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect: `docs/intent/success-outcomes.md`, completed production specification, Task 1 matrix, frontend tests, E2E specs, and affected backend tests
- Modify: this plan's coordination ledger only
- Verify: exact journey claims and existing proof references

**Dependencies:**
- Task 1 complete and accepted by CoS.

**Authority:**
- Preauthorized local actions: read-only mapping and evidence classification.
- Stop for: unresolved completion behavior, contradictory canonical sources, or need for product implementation.

**Steps:**
- [x] Map readiness/setup, profile creation/review/confirmation, successful and failed or empty Scan, Scan reuse, Run, fit evidence, interest, bookmarks, personalization, grounded CV generation/refusal, preview/download, and restart/history.
- [x] Classify every claim exactly as `ALREADY PROVEN`, `REQUIRED AND MISSING`, `NOT APPLICABLE`, or `BLOCKED`.
- [x] Produce Live Probe Contract containing only `REQUIRED AND MISSING` claims.
- [x] Confirm every `REQUIRED AND MISSING` claim fits one bounded probe; otherwise classify it `BLOCKED` instead of broadening probe bounds.
- [x] Record proof source, SHA, freshness, and reason for every non-required disposition.

**Verification:**
- [x] Coverage map includes every completion-critical claim from the canonical completion gate.
- [x] No row contains `maybe`, implicit scope, or unowned proof.
- Expected: Task 3 scope is finite and mechanically determined.

**Exit Criteria:**
- Deterministic coverage map accepted by CoS and exact Live Probe Contract recorded. Any required claim that cannot fit one bounded probe is explicitly `BLOCKED`.

**Stage 12 Coverage Map:**

The claim IDs below are the numbered claims in `docs/intent/success-outcomes.md` under `## Completion Gate`. `ALREADY PROVEN` means accepted current evidence proves the claim at its required boundary; `REQUIRED AND MISSING` means Task 3 must obtain real browser-to-backend and persisted-state proof; `NOT APPLICABLE` means the claim does not apply to this completion target; `BLOCKED` means this contract cannot prove it without violating the declared one-probe bounds or handing it to the independent review task. No Stage 12 claim is `NOT APPLICABLE`.

| ID | Completion-critical claim | Canonical owner | Existing proof source | Evidence source commit | Freshness | Disposition | Missing proof or blocking reason |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 1 | First-time user creates Candidate Profile from supported source without writing internal format | `docs/intent/success-outcomes.md` Completion Gate; Candidate Profile Lifecycle | `frontend/e2e/candidate-profile.spec.ts`; `tests/test_fitcv_cp/test_app.py` staged-lifecycle route tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Real upload through `/app`, persisted creation attempt, and resulting profile identity |
| 2 | User reviews/corrects source-supported profile information with source references | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/candidate-profile.test.ts`; Candidate Profile route tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Browser review/edit and persisted source-reference state |
| 3 | Suggestions stay distinct and unsupported suggestions remain rejectable | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/candidate-profile.test.ts`; `tests/test_fitcv_cp/test_candidate_profile_service.py` | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Browser baseline/derived review with reject action and persisted result |
| 4 | Unfinished profile saves/resumes and unconfirmed profile cannot be selected for normal Run | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/candidate-profile.test.ts`; `tests/test_fitcv_cp/test_local_routes.py` readiness/run guards | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Real draft resume, confirmation gate, and attempted unconfirmed Run selection |
| 5 | Confirmed profile is used in normal job-search Run | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/runs.test.ts`; `tests/test_fitcv_cp/test_app.py` managed Run route tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Persisted Run input must identify confirmed profile revision |
| 6 | Confirmed profile update creates new version without changing prior Run facts; archive/restore is clear when used | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/candidate-profile.test.ts`; `tests/test_fitcv_cp/test_candidate_profile_service.py` | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Live successor revision, prior Run snapshot, and archive/restore state |
| 7 | First-time setup reaches useful job-search result | `docs/intent/success-outcomes.md` Completion Gate; local readiness/profile authority spec | `tests/test_fitcv_cp/test_local_routes.py` readiness tests; `frontend/e2e/integration-flows.spec.ts` shell navigation | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no fresh-install proof | `BLOCKED` | One normal probe reuses existing local runtime/data; fresh-install setup plus full result would expand probe and reset boundary |
| 8 | Successful Scan collects jobs from selected tracked companies and user reviews output | `docs/intent/success-outcomes.md` Completion Gate; Managed Scan lifecycle spec | `frontend/src/test/scans.test.ts`; `tests/test_fitcv_cp/test_scan_contracts.py`; `frontend/e2e/integration-flows.spec.ts` route shell | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Real selected-company Scan, terminal state, output identity, and browser review |
| 9 | Empty or failed Scan shows understandable outcome and next action | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/scans.test.ts`; `tests/test_fitcv_cp/test_scan_contracts.py` failure contracts | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `BLOCKED` | One Scan must be successful for claim 8 and downstream Run; proving both success and empty/failed outcomes needs a second Scan or a separate probe |
| 10 | Successful Scan output is used in a Run | `docs/intent/success-outcomes.md` Completion Gate; Managed Scan and Run continuity specs | `frontend/src/test/scans.test.ts`; `frontend/src/test/runs.test.ts`; `tests/test_fitcv_cp/test_app.py` Scan-only Run tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Persisted Run must reference the observed Scan output |
| 11 | Earlier successful Scan result is reused in later Run | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/scans.test.ts`; `tests/test_fitcv_cp/test_app.py` managed source tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `BLOCKED` | Requires earlier successful Scan plus later Run; one-Scan contract cannot establish both temporal states deterministically |
| 12 | Mixed good/poor batch narrows to useful jobs | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/runs.test.ts`; `tests/test_fitcv_cp/test_worker_job.py` result-bucket tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | One live Run must show both retained and rejected/held jobs with server-owned reasons |
| 13 | Important recommendations, rejections, and holds have understandable reasons | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/runs.test.ts`; `tests/test_fitcv_cp/test_app.py` Run detail/result tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Browser fit/result view must match persisted evidence and reasons |
| 14 | User bookmarks and removes jobs while reviewing results | `docs/intent/success-outcomes.md` Completion Gate; Job Evaluation and Personalization | `frontend/src/test/job-evaluation.test.ts`; `frontend/src/test/bookmarks.test.ts`; `tests/test_fitcv_cp/test_app.py` bookmark route tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Real bookmark create/remove with persisted identity |
| 15 | User later returns to bookmarked list, searches/filters, and continues review | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/bookmarks.test.ts`; `frontend/e2e/integration-flows.spec.ts` bookmark route shell | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Reopen/reload bookmarked view with real saved job and filter/revisit proof |
| 16 | Bookmark stays separate from fit, interest, and personalized ranking | `docs/intent/success-outcomes.md` Completion Gate; Job Evaluation and Personalization | `frontend/src/test/job-evaluation.test.ts`; `frontend/src/test/personalization.test.ts`; `tests/test_fitcv_cp/test_optimization_service.py` | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Live state comparison must show independent server-owned signals |
| 17 | Interest feedback remains available later | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/job-evaluation.test.ts`; `tests/test_fitcv_cp/test_app.py` interest route tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Persist interest, reopen result/bookmark view, and verify rating |
| 18 | Sufficient feedback yields personalized option or clear insufficient-evidence result | `docs/intent/success-outcomes.md` Completion Gate; Core personalization JSON spec | `frontend/src/test/personalization.test.ts`; `tests/test_fitcv_cp/test_optimization_service.py` | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Live `/personalization` response must expose truthful effective mode/fallback after probe feedback |
| 19 | User chooses personalized or normal ordering and can return to normal ordering | `docs/intent/success-outcomes.md` Completion Gate | `frontend/src/test/personalization.test.ts`; `docs/fitcv-new-frontend.integration.md` preference reconciliation | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `BLOCKED` | Demonstrating personalized ordering needs sufficient feedback and an additional ordering comparison beyond one Run; no scope expansion |
| 20 | High-interest weak-fit job remains visibly unsuitable | `docs/intent/success-outcomes.md` Completion Gate; Job Evaluation and Personalization | `frontend/src/test/job-evaluation.test.ts`; `tests/test_fitcv_cp/test_optimization_service.py` separation tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live journey proof | `REQUIRED AND MISSING` | Same live mixed batch must include weak-fit job, high interest, and unchanged suitability |
| 21 | Grounded CV generates for suitable job | `docs/intent/success-outcomes.md` Completion Gate; CV preview transport spec | `frontend/e2e/cv-review.spec.ts`; `frontend/src/features/cv-review/route.test.tsx`; `tests/test_fitcv_cp/test_app.py` CV route tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; mocked/browser contract only | `REQUIRED AND MISSING` | One real generated CV, persisted version, grounded content, preview, and download |
| 22 | CV generation is held/refused when information is insufficient | `docs/intent/success-outcomes.md` Completion Gate; CV preview transport spec | `frontend/e2e/cv-review.spec.ts`; `frontend/src/features/cv-review/route.test.tsx`; CV generation backend tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live refusal journey proof | `BLOCKED` | One generated-CV bound cannot also prove a distinct insufficient-information refusal path |
| 23 | Failed, cancelled, or interrupted Run leaves truthful status and recovery guidance when possible | `docs/intent/success-outcomes.md` Completion Gate; Run continuity and recovery spec | `frontend/src/test/runs.test.ts`; `tests/test_fitcv_cp/test_run_lifecycle.py`; `frontend/e2e/runs.spec.ts` missing-run state | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no live recovery proof | `REQUIRED AND MISSING` | Interrupt/cancel once, recover same Run when capability permits, and compare UI with persisted terminal state |
| 24 | User information, profile revisions, settings, bookmarks, and feedback survive restart | `docs/intent/success-outcomes.md` Completion Gate | `tests/test_fitcv_cp/test_local_storage.py`; `tests/test_fitcv_cp/test_local_routes.py`; frontend state tests | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted prior evidence; no full journey restart proof | `REQUIRED AND MISSING` | Reopen normal local runtime and verify captured IDs/state without creating another Run |
| 25 | Complete normal workflow works without terminal-first operation | `docs/intent/success-outcomes.md` Completion Gate | `frontend/e2e/integration-flows.spec.ts`; frontend route/unit coverage; Task 1 host proof | `c1466eb66174f3d7bda22db44df204679312b57d` | accepted shell proof; no real completion journey | `REQUIRED AND MISSING` | Entire bounded profile → Scan → Run → fit → CV flow through `/app` |
| 26 | UX review finds no issue blocking discovery, understanding, completion, or trust | `docs/intent/success-outcomes.md` Completion Gate; production frontend spec | accepted Task 1–8 browser/state evidence and pending independent Task 4 review | `c1466eb66174f3d7bda22db44df204679312b57d` | Task 4 not run | `BLOCKED` | Independent whole-change review owns this claim; Task 3 cannot self-certify UX readiness |

**Legacy UI deprecation boundary:**

- Legacy `/admin/*` UI remains coexistent supporting surface; no deletion, redirect, retirement, or repurposing occurs in Task 2 or Task 3.
- Stage 14 remains inactive. Legacy retirement requires its separate approved plan, compatibility inventory, explicit product-owner approval, rollback path, and fresh completion evidence.

**Live Probe Contract:**

Only `REQUIRED AND MISSING` claims enter Task 3: `1–6, 8, 10, 12–18, 20–21, 23–25`. Claims `7, 9, 11, 19, 22, 26` are excluded and remain `BLOCKED`; Task 3 must not relabel or silently cover them.

- **Inputs:** exactly `1` supported Candidate Profile source, using `data/2026-06-24-Munich_Electrification-CV.md` or `data/2026-06-27-Beiersdorf-CV.md`; selected tracked companies limited to `1–2`; use `data/sample_jobs_1.json` or `data/sample_jobs_2.json` only when supplied-job proof is needed.
- **Operations:** one profile creation lifecycle; one Scan; one Run using that Scan output; one interrupt/cancel-and-recover attempt only when server capability permits; one generated CV for a suitable job; one bookmark create/remove; one interest rating; one reopen/reload of FitCV state.
- **Hard limits:** no second Scan, no second Run, no second generated CV, no provider install/replacement/new authentication, no mock/fake fallback, no source or contract edits, no extra companies beyond `2`, and no scope expansion to blocked claims.
- **Required observations:** profile and revision IDs; source references and suggestion decisions; Scan ID, selected companies, output count, terminal state, and output identity; Run ID, selected Scan ID, profile revision, terminal state, fit buckets/reasons; bookmark and interest IDs/state; `/personalization` ranking/effective mode/fallback/revision; CV version ID, checksum/media type, preview, download; restart/reopen state; visible-versus-persisted truth.
- **Acceptance:** every listed required claim receives command/browser evidence, exit status or HTTP status, persisted identifier, final state, and coverage limit. Missing provider output, missing mixed batch for claims `12`/`20`, or any unsupported capability is recorded as `INCOMPLETE`, not retried through extra runs.
- **Stop/blockers:** runtime or provider unavailable; provider data egress lacks explicit approval; no usable Scan result; no mixed good/poor batch for claims `12`/`20`; source SHA drift; new authentication; product defect; unexpected data mutation; or any request to exceed hard limits. Record exact blocker and smallest rerun scope.

### Task 3: Run one bounded real Personal FitCV probe

**Purpose:**
- Prove only Task 2 claims classified `REQUIRED AND MISSING` through the normal local product boundary.

**Task Function:**
- Exercise representative browser-to-backend behavior and compare visible state with persisted system truth.

**Template Profile:**
- Controller-selected: `ui`
- Selection basis: material browser, responsive, accessibility, and cross-boundary judgment.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: independent whole-change review follows this probe.

**Specification Coverage:**
- Candidate Profile → Scan → Scan output → Run → fit result → interest/bookmark where required → grounded CV → preview/download → reopen/persistence.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: Task 2 Live Probe Contract, current `/app` routes, existing browser configuration, canonical API routes, persisted identifiers returned by the application, and the approved fixture paths listed below
- Modify: this plan's coordination ledger only
- Verify: browser flow, persisted records/events/artifacts, and existing application logs without exposing secrets

**Dependencies:**
- Task 2 complete.
- Normal local FitCV runtime available.
- Existing configured provider available; do not install, replace, or newly authenticate a provider.
- User-approved supported Candidate Profile input available. Candidate fixtures: `data/2026-06-24-Munich_Electrification-CV.md` or `data/2026-06-27-Beiersdorf-CV.md`.
- User-approved supported job input available when Scan proof requires supplied jobs. Job fixtures: `data/sample_jobs_1.json` or `data/sample_jobs_2.json`.
- Supplied aliases `data/2026-06-24-Munich/_Electrification-CV.md`, `data/sample/_jobs/_1.json`, and `data/sample/_jobs/_2.json` are absent in this checkout; use existing tracked equivalents above without copying or renaming them.
- If the configured provider sends profile or job data outside the local process, obtain explicit user approval naming provider and data categories before the probe; otherwise mark the probe `BLOCKED`.

**Authority:**
- Preauthorized local actions: one normal personal-use probe and recording compact evidence identifiers.
- Probe bounds: `1` Candidate Profile, `1` Scan, maximum `1–2` companies, `1` Run, `1` generated CV, and no additional Runs for evidence quality.
- Provider behavior: use normal application retry/rate behavior; no special retry loop.
- Persistence: records and artifacts may remain as normal personal FitCV data; no automatic cleanup required.
- Stop for: runtime unavailable, provider unavailable after normal retry, no usable Scan result, product defect preventing progression, baseline/source change, new authentication, or scope expansion.
- Mock rule: no mock/fake fallback for claims classified `REQUIRED AND MISSING`.

**Steps:**
- [x] Preflighted disposable `start_web.ps1` runtime on port `8767`; `GET /healthz` returned HTTP `200` with `{"status":"ok"}`; no user DB access.
- [x] Uploaded approved source `data/2026-06-24-Munich_Electrification-CV.md` and completed baseline/derived review and profile confirmation; persisted one active profile in disposable DB.
- [x] Submitted one bounded one-company Scan for company `5230173`; endpoint returned HTTP `422` with `tracked_company_unavailable` because disposable DB had 0 tracked companies.
- [x] Stopped at first Scan blocker; no fallback seeding, extra input, Scan retry, Run, CV, bookmark, interest, or reopen action performed.
- [x] Preserved original `data/fitcv_cp.sqlite3`; no migration, reset, copy, overwrite, or deletion performed.

**Verification:**
- [x] Record probe source commit, derived coordination checkpoint, runtime endpoint/health result, provider identity, profile ID/revision, Scan ID and terminal state, job count, Run ID and terminal state, representative fit result, CV version ID, preview result, download result, restart/persistence result, browser finding, and blocker.
- [x] Confirmed visible API states match disposable persisted records for completed profile lifecycle; no Scan output or later artifact existed after the bounded blocker.
- Expected: all required claims pass, or exact BLOCKED/INCOMPLETE result with smallest rerun scope.

**Task 3 Probe Execution & Evidence Record:**

- **Probe Source Commit:** c1466eb66174f3d7bda22db44df204679312b57d
- **Runtime Preflight:** Initial check found port 8000 listening under PID 42600 (python.exe), start time 2026-08-30 20:32:11; parent PID 18356 was dead; /healthz returned {"status": "ok"} but /personalization failed with HTTP 500 because the running process predated commit c1466eb66174f3d7bda22db44df204679312b57d. Stopped orphaned process PID 42600.
- **Runtime Startup Attempt:** Invoked `powershell -ExecutionPolicy Bypass -File .\start_web.ps1`. Uvicorn initialization failed during `build_app()` at `src/fitcv_cp/main.py:74` while calling `ensure_control_plane_database()` via `_ensure_control_plane_schema` at `src/fitcv_cp/sqlite_store.py:411`:

  `fitcv_cp.sqlite_store.DatabaseSchemaIncompatibleError: Database schema is incompatible: found version 0, expected 5.`
- **Database State:** `data/fitcv_cp.sqlite3` contains 12 tables (`job_embeddings`, `sqlite_sequence`, `candidate_embeddings`, `process_events`, `process_event_integrity_conflicts`, `process_event_deliveries`, `process_event_migrations`, `pipeline_settings`, `cv_versions`, `candidate_query_embeddings`, `vector_shortlist`, `raw_jobs`) with `PRAGMA user_version = 0`.
- **User Data & Scope Compliance:** Per instructions and Live Probe Contract, no database reset, migration, schema overwrite, copy, or deletion was performed; no product code or config was modified; no mock fallbacks were introduced.
- **Provider Identity / Data Egress:** Provider openai_compatible at http://127.0.0.1:20128/v1 (9router proxy) / model cx/gpt-5.4-mini configured in config/runtime/control_plane.yaml. No LLM requests dispatched; no profile or job data left the local process.
- **Probe Execution Summary:**
  - Candidate Profile: 0 created / 0 uploaded / 0 modified
  - Scan: 0 executed / 0 tracked companies scanned
  - Run: 0 executed
  - CV Generation: 0 generated / 0 previewed / 0 downloaded
  - Bookmarks / Interest: 0 modified
- **Claims Disposition:** All 20 Stage 12 REQUIRED AND MISSING claims (1–6, 8, 10, 12–18, 20–21, 23–25) are marked BLOCKED due to runtime startup schema failure. Claims 7, 9, 11, 19, 22, 26 remain BLOCKED per Task 2 contract.
- **Smallest Unblock Condition:** User-approved repair/migration of data/fitcv_cp.sqlite3 schema to version 5, or provision of a clean supported runtime/data fixture.

### Approved Disposable Probe Record (2026-08-31)

- **Probe Source Commit:** `87e4280392e27a0709ac39ae88b098134094802e`; product source candidate unchanged from `c1466eb66174f3d7bda22db44df204679312b57d`.
- **Runtime / Database:** `start_web.ps1` inline mode on port `8767`; disposable DB `.tmp/task3-preflight-live/fitcv_cp.sqlite3`, schema version `5`; `GET /healthz` returned HTTP `200`; runtime stopped after blocker.
- **Provider / Egress:** `openai_compatible` at `http://127.0.0.1:20128/v1` through `9router`, model `cx/gpt-5.4-mini`; approved Candidate Profile source sent for `candidate_profile_base_mapping` and `candidate_profile_derived_claims`; no new authentication or provider install.
- **Completed profile lifecycle:** source `data/2026-06-24-Munich_Electrification-CV.md` (`5843` bytes); attempt `attempt_2ab6cc3167b34c52ae0dfb564c2bbf51`; profile `profile_5ddac651235340728ebd4c7f0216cf41`; revision `profile_revision_27534bc3041846e9925794f593d13f5a`; HTTP upload `202`, baseline approve `202`, derived approve `200`, confirm `201`; disposable DB contained 1 active profile.
- **Scan blocker:** one-company request for `5230173` and one row returned HTTP `422` with `tracked_company_unavailable`; disposable DB contained 0 tracked companies. No supported path permits seeding without broadening scope.
- **Unperformed stages:** 0 Scan outputs, 0 Runs, 0 CV versions/previews/downloads, 0 bookmark or interest mutations, and 0 reopen actions.
- **User-data / Git safety:** original `data/fitcv_cp.sqlite3` was untouched; current Git tracked state was clean; task-owned disposable path remains preserved because cleanup command was blocked by local command policy.
- **Current disposition:** `BLOCKED` at Scan boundary; smallest unblock is a supported disposable fixture containing at least one tracked company, or explicit approval to seed/import the approved job/company fixture without broadening the probe.

### Approved Disposable Fixture Import Probe Record (2026-08-31)

- **Probe Source Commit:** `614019f6490bf0bccbd617209c3ec689ac0d3892`; product source candidate unchanged from `c1466eb66174f3d7bda22db44df204679312b57d`.
- **Runtime / Database:** inline runtime on port `18000`; disposable DB `.tmp/task3-import-live/fitcv_cp.sqlite3`; `GET /healthz` returned HTTP `200`; owned Uvicorn PID `30112` stopped cleanly; port `18000` closed.
- **Fixture Import:** `data/product150-dataset_linkedin-jobs-scraper_2026-05-23_08-05-06-456.json`; selected Awin Global Greenhouse board `https://job-boards.greenhouse.io/awin`; company import HTTP `201`, ID `company-475efed79a1a`, provider `greenhouse`; resolved endpoint `https://boards-api.greenhouse.io/v1/boards/awin/jobs?content=true`.
- **Provider / Egress:** `openai_compatible` at `http://127.0.0.1:20128/v1` through `9router`, model `cx/gpt-5.4-mini`, wire API `responses`; approved Candidate Profile source sent for `candidate_profile_base_mapping` and `candidate_profile_derived_claims`.
- **Completed profile lifecycle:** source `data/2026-06-24-Munich_Electrification-CV.md`; attempt `attempt_989864b828d94a08a609cb56bf3aab7c`; upload HTTP `202`; baseline HTTP `202`; derived HTTP `200`; confirm HTTP `201`; active profile `profile_9c17983c121944e994bb1ebcd5c66f16`.
- **Scan:** HTTP `201`; ID `scan-888e73590570`; final `succeeded`; one company, 2 rows, valid output integrity.
- **Run blocker:** HTTP `201`; ID `046cfb42-c4e5-4766-b9bc-b5ec7a2e4819`; final `failed`; `Candidate profile validation failed: Missing required section: 'preferences'`; failure occurred before ranking/CV generation.
- **Persisted truth:** disposable SQLite contains 1 company, 1 scan, 1 run, 1 active profile, `bookmarks=0`, `ratings=0`, `cv_versions=0`, and `integrity_check=ok`; no source/config/test/plan/user-data edits; `.tmp/task3-import-live` preserved; pre-existing `frontend/test-results/` remains untracked.
- **Unperformed stages:** cancel/recover, bookmark create/remove, interest rating, CV preview/download, and reopen/reload; claims 7, 9, 11, 19, 22, 26 untouched.
- **Current disposition:** `BLOCKED` at Run validation; smallest unblock is a supported Candidate Profile fixture containing required `preferences`, or an approved product/data correction followed by a new bounded probe.

**Exit Criteria:**
- Probe evidence is complete for every required claim, or CoS records a bounded blocker. Defects do not become an unplanned debugging lane.

### Task 4: Independent whole-change review

**Purpose:**
- Independently assess final integrated implementation and closure evidence.

**Task Function:**
- Review completion-critical behavior, ownership, cross-boundary truth, accessibility, and evidence consistency without implementing fixes.

**Template Profile:**
- Controller-selected: `review`
- Selection basis: independent repository and evidence review.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: reviewer is the independent validation lane.

**Specification Coverage:**
- Final `final_candidate_source_commit`, completed production specification, completed vertical-slice plan, success outcomes, and accepted Task 1–3 evidence.

**Required Skills:**
- `skill-requesting-code-review`
- `skill-receiving-code-review`
- `skill-using-git-worktrees`

**Files And Symbols:**
- Inspect: exact final candidate source state, named canonical docs, Task 1 matrix, Task 2 coverage map, Task 3 probe evidence, frontend tests/E2E specs, and affected backend tests
- Modify: none
- Verify: pre-review and post-review Git state remain unchanged

**Dependencies:**
- Tasks 1–3 accepted by CoS.
- `final_candidate_source_commit` resolved and all affected evidence reconciled to it.
- Reviewer starts from fresh context in the isolated read-only review workspace; reviewer does not reuse lead or producer session history.

**Authority:**
- Preauthorized local actions: read-only inspection and bounded existing checks.
- Read-only boundary: reviewer must not modify plan, source, tests, Git index, branch refs, or commits.
- [x] CoS creates `.worktrees/fitcv-closure-review` with `git worktree add --detach .worktrees/fitcv-closure-review <final_candidate_source_commit>`, dispatches a fresh top-level `review` session through `skill-requesting-code-review` and the configured CoS review path, and retires the review worktree only after pre/post Git state is recorded by its owner.
- Stop for: unexpected repository modification, missing evidence identity, source drift, or unreviewable runtime claim.

**Steps:**
- [x] Bind review to exact repository, detached review worktree, `final_candidate_source_commit`, derived coordination checkpoint, and evidence identities.
- [x] Inspect completion-critical behavior, fit/business truth, frontend/backend contracts, accessibility/usability, persistence, and probe contradictions.
- [x] Exclude enterprise hardening, speculative architecture, cosmetic redesign, legacy retirement, and performance without an approved requirement.
- [x] Return exactly `PASS`, `FAIL`, or `BLOCKED` with P1/P2/P3 findings and exact evidence: `PASS`; P3 documentation path drift only (`frontend/src/types/api.ts` → `frontend/src/api.ts`; `src/fitcv_cp/schemas.py` → `src/fitcv_cp/schema.py`); Task 3 Scan blocker remains accurately recorded and prevents closure, not review acceptance.

**Verification:**
- [x] Pre-review and post-review `git status --short --branch`, HEAD, and diff are unchanged; detached review worktree was clean at `c1466eb66174f3d7bda22db44df204679312b57d` and retired.
- Expected: independent verdict applies to exact final source candidate plus its derived coordination checkpoint, not a summary or prior commit.

**Exit Criteria:**
- Independent review returns a disposition accepted or routed by CoS. Completion-blocking P1/P2 findings remain unresolved until fixed and affected proof is rerun.

### Task 5: Lead closure reconciliation

**Purpose:**
- Reconcile all evidence and set final closure disposition.

**Task Function:**
- Lead-controller completion verification and durable coordination-state update.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: only lead controller may accept proof and write coordination state.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: fresh verification skill owns final proof; no second coordinator.

**Specification Coverage:**
- All required outcomes, Task 1–4 exits, current Git state, and no automatic Stage 14 activation.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: this plan, completed production specification, completed vertical-slice plan, success outcomes, all accepted evidence, current Git state, and required validators/tests
- Modify: this plan's coordination ledger and status only
- Verify: final artifact-level commands and fresh evidence

**Dependencies:**
- Tasks 1–4 complete or explicitly blocked/incomplete.

**Authority:**
- Preauthorized local actions: fresh verification, evidence reconciliation, ledger update, and checkpoint commit when proof is accepted.
- Stop for: unresolved required proof, stale evidence, plan/Git mismatch, reviewer P1/P2, unexpected changes, or any source/spec change requiring a new plan.

**Steps:**
- [x] Run `skill-verification-before-completion` against exact final candidate state.
- [x] Classify every task and completion claim as proven, incomplete, blocked, deferred with approval, or not applicable with reason.
- [x] Record `STAGES 11–13 INCOMPLETE`, exact blocker, and smallest rerun/fix scope: provision supported disposable fixture containing at least one tracked company, or obtain explicit approval to seed/import the approved fixture, then rerun bounded Task 3 proof and affected E2E/browser proof.
- [x] Never activate Stage 14, retire legacy frontend, push, merge, or release from this plan.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root .` passed.
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .` passed.
- [x] Fresh applicable frontend tests, E2E/browser evidence, affected backend tests, `python -m compileall -q src`, and `git diff --check` recorded; E2E remains incomplete because host returned `ERR_CONNECTION_REFUSED`.
- Expected: final result is evidence-backed, SHA-bound, and reproducible from plan plus Git.

**Exit Criteria:**
- One final closure verdict is recorded. Plan becomes `completed` only when verification returns `verified`; otherwise retain unresolved state and route next action.

## Verification

- Run planning validators after plan creation and after any coordination-state change.
- Rerun only applicable commands recorded by Tasks 1–3: `npm run typecheck`, `npm run test`, `npm run test:a11y`, `npm run build`, and `npm run test:e2e` from `frontend/`; `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_frontend_host.py`; `python -m compileall -q src`; and `git diff --check`.
- Run affected backend/API tests and `python -m compileall -q src` when backend evidence is applicable.
- Use browser/runtime evidence for rendered and real-boundary claims; source inspection or mock tests cannot replace required live proof.
- Run `git diff --check` and confirm final evidence binds to `final_candidate_source_commit`; derive checkpoint identity from `git log -1 --format=%H -- <plan-path>`.

## Completion Criteria

The plan is ready for completion verification when:

1. Task 1 records explicit Stage 11 evidence dispositions.
2. Task 2 maps every completion-critical Stage 12 claim and contains no `maybe` classification.
3. Task 3 either proves every required live claim within bounds or records exact `BLOCKED`/`INCOMPLETE` evidence.
4. Task 4 independently reviews the exact `final_candidate_source_commit` and derived coordination checkpoint.
5. Task 5 records one closure verdict and no unresolved required proof is hidden by a checkbox or agent summary.
6. Plan/Git state, preserved user changes, validators, tests, and deviations are reconciled.

User approval changes this plan from `proposed` to eligible for CoS activation. CoS activation sets `status: active`, records `activation_source_commit`, and activates Task 1; approval alone does not execute a task. If activation finds `HEAD != origin/main`, CoS stops and requests explicit push/sync authorization or a recorded exception before Task 1.
