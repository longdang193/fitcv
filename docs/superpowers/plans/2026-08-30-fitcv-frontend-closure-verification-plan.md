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
- Next action: dispatch Task 2 journey-map main agent through Herdr
- Blockers: none; Task 1 correction approved, committed, and independently validated
- Source evidence baseline: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- Final source under review: `c1466eb66174f3d7bda22db44df204679312b57d`; Task 1 bounded correction is approved and committed
- Coordination checkpoint: derive latest checkpoint with `git log -1 --format=%H -- <plan-path>`; do not copy checkpoint SHA into plan text

Activation baseline:

- `main` HEAD: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- `origin/main`: `0e9d8b35bbb36dc0d2e85136480cc8b4b7b5cd75`
- Current worktree: clean
- Preserved unrelated worktrees: `.worktrees/fitcv-task-4` and `.worktrees/fitcv-task-5`; both contain untracked `frontend/test-results/` only
- Source changes authorized by this plan: none

Before activation, commit this proposed plan so Git can recover its coordination ledger. Activation then changes plan `status` from `proposed` to `active` before Task 1 starts. At activation, CoS must record exact `main` HEAD, `origin/main`, worktree status, preserved unrelated changes, and `activation_source_commit`. Require `HEAD == origin/main` and no unexpected tracked changes. Every accepted evidence item records the source commit it proves. Each accepted task transition must update its complete ledger row, `Next action`, and evidence anchor in one lead checkpoint commit. Derive that checkpoint from plan history with `git log -1 --format=%H -- <plan-path>` when resuming or reviewing.

If a required defect correction changes source, stop current proof, record `final_candidate_source_commit` after correction, invalidate only affected evidence, rerun only affected proof, and make Task 4 review the final source candidate. Ledger-only checkpoint commits do not change `final_candidate_source_commit`. This plan does not authorize source correction.
The lead controller is sole coordination-state writer. Runtime threads, agent sessions, temporary todos, and memory are not recovery state.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | Stage 11 evidence matrix and fresh validators | bounded baseline policy-lookup correction committed at `c1466eb66174f3d7bda22db44df204679312b57d`; Herdr review validator `PASS`; live dark-theme `/personalization` returned HTTP 200 |
| Task 2 | `pending` | current | `codex` | Task 1 | deterministic journey map and Live Probe Contract | ready; Task 1 accepted |
| Task 3 | `pending` | current | `codex` | Task 2 | bounded real Personal FitCV probe or explicit blocked/incomplete result | pending |
| Task 4 | `pending` | `.worktrees/fitcv-closure-review` | `codex` | Tasks 1–3 | independent `PASS`, `FAIL`, or `BLOCKED` review bound to final source SHA | pending
| Task 5 | `pending` | current | `codex` | Tasks 1–4 | fresh completion verification and closure verdict | pending |

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
| Browser shell and route journeys | `/app` frontend host and E2E specs | prior `npm run test:e2e`; Task 1 live route check against `http://127.0.0.1:8000` | prior `11 passed`, `1 failed`; live dark-theme `/personalization` now HTTP 200 | `c1466eb66174f3d7bda22db44df204679312b57d` | fresh-this-turn | `INCOMPLETE` | Full E2E rerun after source correction remains required |
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
- [ ] Map readiness/setup, profile creation/review/confirmation, successful and failed or empty Scan, Scan reuse, Run, fit evidence, interest, bookmarks, personalization, grounded CV generation/refusal, preview/download, and restart/history.
- [ ] Classify every claim exactly as `ALREADY PROVEN`, `REQUIRED AND MISSING`, `NOT APPLICABLE`, or `BLOCKED`.
- [ ] Produce Live Probe Contract containing only `REQUIRED AND MISSING` claims.
- [ ] Confirm every `REQUIRED AND MISSING` claim fits one bounded probe; otherwise classify it `BLOCKED` instead of broadening probe bounds.
- [ ] Record proof source, SHA, freshness, and reason for every non-required disposition.

**Verification:**
- [ ] Coverage map includes every completion-critical claim from the canonical completion gate.
- [ ] No row contains `maybe`, implicit scope, or unowned proof.
- Expected: Task 3 scope is finite and mechanically determined.

**Exit Criteria:**
- Deterministic coverage map accepted by CoS and exact Live Probe Contract recorded. Any required claim that cannot fit one bounded probe is explicitly `BLOCKED`.

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
- [ ] Preflight `Get-NetTCPConnection -LocalPort 8000 -State Listen` and `Invoke-RestMethod http://localhost:8000/healthz`; record listener PID and confirm existing runtime ownership before reuse. If unavailable, start `start_web.ps1` in an owned background process from a separate shell, capture parent PID, verify the serving listener PID and health, and record resolved endpoint and provider identity; if queued execution is required, start `start_worker.ps1` only after Redis readiness and capture its PID.
- [ ] Use resolved endpoint in all browser/API checks. Stop only the owned process tree after proof, confirm owned listener shutdown, and do not stop an existing runtime owned outside this probe.
- [ ] Launch actual `/app` through normal local runtime.
- [ ] Use approved supported profile input; review and confirm persisted active profile.
- [ ] Run one bounded Scan against at most two tracked companies; inspect actual output.
- [ ] Use Scan output in one Run; inspect actual fit/evidence state and direct API/persisted state for each required persistence or failure claim, recording command, exit status, IDs, final state, and coverage limit.
- [ ] Exercise only required interest/bookmark or negative-condition proof; preserve separation between fit, interest, bookmark, and ranking.
- [ ] Generate one grounded CV for a suitable job; preview persisted version and download it.
- [ ] Reopen FitCV and verify required persisted state/history.

**Verification:**
- [ ] Record `probe source commit`, derived coordination checkpoint, runtime endpoint/health result, provider identity, profile ID/revision, Scan ID and terminal state, job count, Run ID and terminal state, representative fit result, CV version ID, preview result, download result, restart/persistence result, browser finding, and blocker.
- [ ] Confirm visible states match persisted records/events/artifacts.
- Expected: all required claims pass, or exact `BLOCKED`/`INCOMPLETE` result with smallest rerun scope.

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
- [ ] CoS creates `.worktrees/fitcv-closure-review` with `git worktree add --detach .worktrees/fitcv-closure-review <final_candidate_source_commit>`, dispatches a fresh top-level `review` session through `skill-requesting-code-review` and the configured CoS review path, and retires the review worktree only after pre/post Git state is recorded by its owner.
- Stop for: unexpected repository modification, missing evidence identity, source drift, or unreviewable runtime claim.

**Steps:**
- [ ] Bind review to exact repository, detached review worktree, `final_candidate_source_commit`, derived coordination checkpoint, and evidence identities.
- [ ] Inspect completion-critical behavior, fit/business truth, frontend/backend contracts, accessibility/usability, persistence, and probe contradictions.
- [ ] Exclude enterprise hardening, speculative architecture, cosmetic redesign, legacy retirement, and performance without an approved requirement.
- [ ] Return exactly `PASS`, `FAIL`, or `BLOCKED` with P1/P2/P3 findings and exact evidence.

**Verification:**
- [ ] Pre-review and post-review `git status --short --branch`, HEAD, and diff are unchanged.
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
- [ ] Run `skill-verification-before-completion` against exact final candidate state.
- [ ] Classify every task and completion claim as proven, incomplete, blocked, deferred with approval, or not applicable with reason.
- [ ] If all required claims pass, record `STAGES 11–13 SATISFIED` and `READY FOR STAGE 14 DECISION — LEGACY FRONTEND RETIREMENT`.
- [ ] Otherwise record `STAGES 11–13 INCOMPLETE`, exact blocker, and smallest rerun/fix scope.
- [ ] Never activate Stage 14, retire legacy frontend, push, merge, or release from this plan.

**Verification:**
- [ ] `python scripts/validate_template_required_sections.py --repo-root .`
- [ ] `python scripts/validate_planning_lifecycle.py --repo-root .`
- [ ] Fresh applicable frontend tests, E2E/browser evidence, affected backend tests, `python -m compileall -q src`, and `git diff --check`.
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
