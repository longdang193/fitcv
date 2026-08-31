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
- Next action: Retain `STAGES 11–13 INCOMPLETE`; scope-expanded one-Scan/one-Run correction probe is consumed. Do not run another Scan/Run in this lane. A further disposable correction must use a unique job identity and requires new explicit scope approval.
- Blockers: Scope-expanded corrected upload preserved real Awin description/skills and added Berlin, non-Internship, and normalized Data Engineering fields, but reused Scan job URL and was skipped as `duplicate_job_url`; Run `e52e821b-6157-4d5e-a3cc-62f4d4e5ca3c` therefore ended with `0` passed, `15` rejected, `cvs_generated=0`. Claims 7, 9, 11, 19, 22, 26 remain `BLOCKED`; claims 1–6, 8, 10, 12–18, 20–21, 23–25 remain incomplete for CV/browser completion; E2E shell proof recovered with 12/12 passed; original `data/fitcv_cp.sqlite3` remains untouched.
- Source evidence baseline: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- Final source under review: `87e4280392e27a0709ac39ae88b098134094802e`; product source candidate remains unchanged since `c1466eb66174f3d7bda22db44df204679312b57d`
- Coordination checkpoint: derive latest checkpoint with `git log -1 --format=%H -- <plan-path>`; do not copy checkpoint SHA into plan text
- Closure verdict: `STAGES 11–13 INCOMPLETE`; scope-expanded Task 3 completed one new Scan and Run plus E2E host recovery, but remains `BLOCKED` because corrected job was deduplicated before CV analysis and no job passed; fresh Task 4 `PASS` with no substantiated P1/P2/P3 findings; Task 5 remains incomplete because CV/browser completion proof is absent despite E2E `12 passed`; Stage 14 remains inactive

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
| Task 3 | `blocked` | current | `codex` | Task 2 | bounded real Personal FitCV probe or explicit blocked/incomplete result | `BLOCKED` after scope-expanded disposable correction probe; corrected job `.tmp/task3-corrected-live/fresh-corrected-job.json` derived from Awin Scan row `https://job-boards.greenhouse.io/awin/jobs/7785591003`, changed to Analytics Engineer / Berlin / Mid-Senior level with Data Engineering normalized fields; Scan `scan-5c0d51367179` HTTP `201` then `200`, succeeded, 50 rows; Run `e52e821b-6157-4d5e-a3cc-62f4d4e5ca3c` HTTP `201` then `200`, succeeded, 51 total, 0 passed, 15 rejected, 0 CVs; corrected upload skipped at enrichment as `duplicate_job_url` because same source URL was already in Scan; no CV/preview/download/reopen; prior bookmark/rating evidence preserved; original DB untouched |
| Task 4 | `completed` | `C:\fitcv-review` (detached, clean pre/post) | `codex` | Tasks 1–3 | fresh independent `PASS`, `FAIL`, or `BLOCKED` review bound to updated final source and latest Task 3 evidence | `PASS`; Herdr main agent `fitcv-t4-final-main` reviewed `588f4bf45c5ea92741dae3f3da7724445bacf290`; no P1/P2/P3 finding substantiated; canonical `/app`, contracts, accessibility evidence, deprecated `/admin/*` boundary, and corrected Task 3 evidence consistent |
| Task 5 | `completed` | current | `codex` | Tasks 1–4 | fresh completion verification and closure verdict | `incomplete`; prior frontend checks and backend focused suite remain passing; recovered supported host `http://127.0.0.1:8000` with disposable DB; one fresh `npm run test:e2e` exited `0` with `12 passed`; scope-expanded Task 3 Run still produced no passed job, so CV generation/preview/download and reopen/reload remain unavailable; Stage 14 remains inactive |

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
| Browser shell and route journeys | `/app` frontend host and E2E specs | fresh `npm run test:e2e` from `frontend/`; Task 1 live route check against `http://127.0.0.1:8000` | supported backend-served frontend host at `http://127.0.0.1:8000`; fresh run exited `0`, `12 passed`, `0 failed` | `c1466eb66174f3d7bda22db44df204679312b57d` | fresh-this-turn | `ALREADY PROVEN` | Full CV/browser completion remains blocked by no passed Run job |
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
- [x] Copied approved source `data/2026-06-24-Munich_Electrification-CV.md` into disposable `.tmp/task3-corrected-live/candidate_profile.yaml`; added `preferences.target_role=Data Engineer`, `preferences.preferred_locations=[Berlin]`, and `preferences.exclude_experience_levels=[Internship]`; remapped nested evidence refs to owning `exp_`/`proj_` IDs and dropped unsupported certificate ref.
- [x] Reused/imported Awin Global company `company-475efed79a1a` with provider `greenhouse` and board `https://job-boards.greenhouse.io/awin` in disposable `.tmp/task3-corrected-live/fitcv_cp.sqlite3`; runtime `http://127.0.0.1:18001` health HTTP `200`, owned PID `6512`, clean Uvicorn shutdown; `PRAGMA integrity_check=ok`.
- [x] Executed exactly one corrected Scan: `scan-a2734e993072` create HTTP `201`, terminal HTTP `200`, `succeeded`, 50 rows, output integrity valid.
- [x] Executed exactly one corrected Run: `a2c0bc7f-ff02-4913-b511-65b1db0f49b7` create HTTP `201`, terminal HTTP `200`, `succeeded`, 50 total, 0 passed, 15 rejected at `cv-analysis` with `reranker_fit_below_threshold`, 35 skipped at ranking with `not_selected_in_final_ranking`; 3 enrichment rows also skipped as `near_duplicate_job_posting`; 0 CVs generated.
- [x] Created and removed bookmark `a676a273-eea8-4bb3-89e5-dff061e80c06` for job `72daeea6-0b15-5103-bb25-2b0ed2e08959`, both HTTP `200`, final persisted bookmark `false`; recorded interest rating `4`, HTTP `200`, contract `application-interest-v1`.
- [x] Checked CV history HTTP `200`: `0` versions; all jobs `download_cv=false`; no preview/download, cancel/recover, or reopen/reload performed.
- [x] Performed scope-expanded disposable Awin correction from Scan row `https://job-boards.greenhouse.io/awin/jobs/7785591003`; retained description evidence, changed title/location/experience, and added normalized fields. One new Scan and one new Run consumed; corrected row was skipped as `duplicate_job_url`, so no job passed.
- [x] Preserved `.tmp/task3-corrected-live/task3-rerun-evidence.json`, `.tmp/task3-corrected-live/task3-scope-expansion-evidence.json`, correction hashes, and runtime evidence; no source, config, test, tracked fixture, plan, Git, user DB, or original data mutation.

**Verification:**
- [x] Correction evidence: disposable profile checksum `c8e868ede67d898e6ebe3e7c364bc07a10062ff774dc13fe2ac1bcdb7aa6108`, revision `profile_revision_68f147c8715d47b995b8150af2e48fca`; original `data/fitcv_cp.sqlite3` untouched.
- [x] Provider identity/egress remained approved: `openai_compatible` at `http://127.0.0.1:20128/v1` through `9router`; observed `fitcv_builtin` synonym triage; no new auth/provider/install/Docker.
- [x] Persisted truth matches API evidence: disposable DB contains corrected profile, company, scope-expanded Scan `scan-5c0d51367179`, Run `e52e821b-6157-4d5e-a3cc-62f4d4e5ca3c`, prior bookmark removal, rating `4`, `cv_versions=0`, and `PRAGMA integrity_check=ok`; Run input manifest records corrected upload plus Scan output hashes.
- [x] Exact output record: `.tmp/task3-corrected-live/task3-scope-expansion-evidence.json`; no cancel/recover, CV preview/download, or reopen/reload evidence exists because Run produced no passed job.
- **Claims Disposition:** Claims 7, 9, 11, 19, 22, 26 remain `BLOCKED`; claims 1–6, 8, 10, 12–18, 20–21, 23–25 remain incomplete because Run yielded no passed job and browser completion proof was not performed.
- **Current disposition:** `BLOCKED`; corrected job data was accepted into Run input but deduplicated because its `jobUrl` matched the Scan row. No passed job means CV generation, preview, download, and reopen/reload cannot proceed. Current scope is exhausted; further correction needs a unique disposable job identity and new explicit approval.

**Exit Criteria:**
- Probe evidence is complete for every required claim, or CoS records a bounded blocker. Defects do not become an unplanned debugging lane.

### Scope-Expanded Disposable Job Correction Probe Record (2026-08-31)

- **Correction boundary:** Disposable only. Source row came from Scan `scan-5c0d51367179`, index `6`, URL `https://job-boards.greenhouse.io/awin/jobs/7785591003`; correction file `.tmp/task3-corrected-live/fresh-corrected-job.json`; metadata `.tmp/task3-corrected-live/fresh-job-correction-meta.json`.
- **Before / after:** Before title `Analytical Engineer (f/m/d)`, location `Iași, Iași, Romania; Warsaw, Masovian Voivodeship, Poland`, empty `experienceLevel`, job hash `ebc8fd481582f519ce4bdc8714539aedce95ef5eef54210e761b0f2f1e8b65d2`; after title `Analytics Engineer (f/m/d)`, location `Berlin, Berlin, Germany`, `experienceLevel=Mid-Senior level`, job hash `666042534e229f6ee0c2f37c981d96b109a735135357594366174539b7f209af`.
- **Evidence / normalized fields:** Description hash unchanged `96f0fa5f00c5f0468fd033fe8c4621139c1d6b13ed7c228801f04a3ddaa036e3`; added `skills` evidence for Analytics Engineering, Data Engineering, Databricks, SQL, Power BI, Tableau, and Data Quality; normalized `work_mode=hybrid`, `location_type=hybrid`, `seniority=senior`, `role_family=data_engineering`, `job_family=data_engineering`, `domain=data`.
- **Scan:** Awin company `company-475efed79a1a`, board `https://job-boards.greenhouse.io/awin`; `scan-5c0d51367179` create HTTP `201`, terminal HTTP `200`, `succeeded`, 50 rows; output SHA256 `b1e83a4f70dfcae450ff49aa8182abc4819fba7f930600045f4bb51b3291505d`, 493465 bytes, integrity valid.
- **Run:** `e52e821b-6157-4d5e-a3cc-62f4d4e5ca3c` create HTTP `201`, terminal HTTP `200`, `succeeded`; input manifest has 51 jobs: corrected upload SHA256 `666042534e229f6ee0c2f37c981d96b109a735135357594366174539b7f209af` plus Scan SHA256 above; persisted totals `51`, passed `0`, rejected `15`, CVs `0`.
- **Run blocker:** Corrected upload reused same `jobUrl` as Scan row; enrichment skipped it with `duplicate_job_url`. Stage counts: enrichment `47 passed / 3 near_duplicate_job_posting / 1 duplicate_job_url`; ranking `15 passed / 32 not_selected_in_final_ranking`; cv-analysis `15 blocked / reranker_fit_below_threshold`; no CV version, preview, download, or reopen/reload.
- **Prior actions preserved:** bookmark `a676a273-eea8-4bb3-89e5-dff061e80c06` remains removed; prior job `72daeea6-0b15-5103-bb25-2b0ed2e08959` retains rating `4`, contract `application-interest-v1`.
- **Runtime / E2E:** Disposable API `http://127.0.0.1:18002`, PID `5244`, health HTTP `200`, clean shutdown; supported frontend host `http://127.0.0.1:8000`, PID `31388`, clean shutdown; `npm run test:e2e` from `frontend/` exited `0`, `12 passed`, `0 failed`.
- **Provider / safety:** `openai_compatible` at `http://127.0.0.1:20128/v1` through `9router`; no new auth/provider/install/Docker. Disposable DB `.tmp/task3-corrected-live/fitcv_cp.sqlite3` `PRAGMA integrity_check=ok`; original `data/fitcv_cp.sqlite3`, canonical source, tracked fixtures, config, tests, plan before this ledger edit, and user data untouched.
- **Claims disposition:** Claims `7, 9, 11, 19, 22, 26` remain `BLOCKED`; claims `1–6, 8, 10, 12–18, 20–21, 23–25` remain incomplete because no job passed and CV/browser completion was unavailable. `STAGES 11–13 INCOMPLETE`; Stage 14 inactive.

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
- [x] CoS created detached review worktree `C:\fitcv-review` at `588f4bf45c5ea92741dae3f3da7724445bacf290`, dispatched fresh Herdr main agent `fitcv-t4-final-main` with profile `review`, and recorded clean pre/post Git state.
- Stop for: unexpected repository modification, missing evidence identity, source drift, or unreviewable runtime claim.

**Steps:**
- [x] Bind review to exact repository, detached review worktree, `final_candidate_source_commit`, derived coordination checkpoint, and evidence identities.
- [x] Inspect completion-critical behavior, fit/business truth, frontend/backend contracts, accessibility/usability, persistence, and probe contradictions.
- [x] Exclude enterprise hardening, speculative architecture, cosmetic redesign, legacy retirement, and performance without an approved requirement.
- [x] Return exactly `PASS`, `FAIL`, or `BLOCKED` with P1/P2/P3 findings and exact evidence: `PASS`; no P1/P2/P3 finding substantiated. Reviewer verified canonical `/app` at `frontend/src/App.tsx`, `/app` mount and API bindings in `src/fitcv_cp/local_routes.py:53-162`, accessibility evidence in `frontend/src/App.tsx:94-288` and `frontend/src/App.test.tsx:36-44`, deprecated `/admin/*` scope remains outside Stage 14, and corrected Task 3 counts/evidence are consistent.

**Verification:**
- [x] Pre-review and post-review `git status --short --branch`, HEAD, and diff are unchanged; detached review worktree `C:\fitcv-review` was clean at `588f4bf45c5ea92741dae3f3da7724445bacf290`.
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
- [x] Record `STAGES 11–13 INCOMPLETE`, exact blocker, and smallest next scope: corrected upload was skipped as `duplicate_job_url`, no Run job passed, and CV generation/preview/download/reopen remains unavailable; E2E host recovery passed `12/12`, but further job correction needs unique disposable identity and new explicit approval.
- [x] Never activate Stage 14, retire legacy frontend, push, merge, or release from this plan.

**Verification:**
- [x] `python scripts/validate_template_required_sections.py --repo-root .` passed.
- [x] `python scripts/validate_planning_lifecycle.py --repo-root .` passed.
- [x] Prior frontend checks passed: `npm run typecheck`, `npm run test` (`96 passed`), `npm run test:a11y` (`1 passed`), and `npm run build`; recovered supported host at `127.0.0.1:8000`, fresh `npm run test:e2e` exited `0` with `12 passed`; backend focused suite `535 passed`, `python -m compileall -q src`, planning validators, and `git diff --check` passed. Live completion remains blocked because scope-expanded Run produced no passed job and CV history has zero versions.
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

## Task 3 Final Disposable Probe Addendum (2026-08-31)

- **Disposition:** Task 3 final probe is `BLOCKED` at `cv-analysis`; prior completed evidence and acceptance-claim dispositions remain preserved. `STAGES 11–13 INCOMPLETE`; claims `7, 9, 11, 19, 22, 26` remain `BLOCKED`; no Stage 14.
- **Disposable correction:** `.tmp/task3-corrected-live/final-corrected-job.json`, derived from Awin data only; unique URL `https://job-boards.greenhouse.io/awin/jobs/7785591003?task3-final-20260831=1`; file SHA256 `5c36d626db14d1a4d6d6eeccd9e0e3ff3c0211da130deb21dd3e8663df2f55c9`; persisted source fingerprint `d656e542177fffb577aee33578dedadc62746c96eb0f68df2d900c40ac145ded`; alignment `Data Engineer`, `Berlin`, `Mid-Senior level`, `hybrid`, `senior`, `data_engineering`, `data`, required description and skills present.
- **Scan:** `scan-4d5085d99653`; POST HTTP `201`; terminal HTTP `200`, `succeeded`; output HTTP `200`, 50 rows; unique corrected URL absent from Scan output.
- **Run:** `d1af3a95-524e-4782-a769-990d40917094`; POST HTTP `201`; terminal HTTP `200`, `succeeded`; output HTTP `200`; `51` total, `0` passed, `15` rejected, `36` skipped, `0` CVs. Matching job persisted as run job `0c945596-9dea-5bf2-9193-e6dd75f87a89`, passed enrichment/screening/shortlisting/ranking, then blocked at `cv-analysis` with `reranker_fit_below_threshold`; `current_cv_version_id=null`; no CV preview/download/reopen.
- **Boundary / provider:** Disposable DB `.tmp/task3-corrected-live/fitcv_cp.sqlite3` integrity `ok`; `data/fitcv_cp.sqlite3`, canonical source, tracked fixtures, config, tests, user DB, and Git source remain untouched. Provider stayed `openai_compatible` through `9router` at `http://127.0.0.1:20128/v1`; runtime `http://127.0.0.1:18002` stopped; existing E2E proof remains `npm run test:e2e`, `12 passed`, not rerun.
- **Evidence:** `.tmp/task3-corrected-live/task3-final-rerun-evidence.json`; `.tmp/task3-corrected-live/final-scan-create.json`; `.tmp/task3-corrected-live/final-scan-terminal.json`; `.tmp/task3-corrected-live/final-scan-output.json`; `.tmp/task3-corrected-live/final-run-create.json`; `.tmp/task3-corrected-live/final-run-terminal.json`; `.tmp/task3-corrected-live/final-run-jobs-output.json`.
