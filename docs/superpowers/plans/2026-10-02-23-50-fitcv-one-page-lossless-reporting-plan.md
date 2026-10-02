---
layer: change
artifact_type: plan
status: blocked
template_id: implementation-plan
contract_version: "1"
name: fitcv-one-page-lossless-reporting
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/run_artifact_contracts.py
  - src/fitcv_cp/worker_job.py
  - scripts/benchmark_cv_efficiency.py
  - scripts/verify_fitcv_acceptance.py
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
  - tests/
  - docs/superpowers/evidence/
---

# FitCV One-Page Finalization And Lossless Reporting

## Goal

Make final-artifact acceptance truthful and make runtime-efficiency reporting
lossless. An artifact is accepted only when content validation passes, native
render succeeds, and final page count is exactly one. Every efficiency metric
comes from one normalized trace set that preserves duplicate and conflict
diagnostics. After integrity gates pass, run one same-workload experiment to
raise first-pass acceptance above the current `3 / 18 = 16.7%` baseline.

P0-A, P0-B, and P0-C stay frozen. P1-C and P2 stay deferred. No new agent,
service, database, vector store, reranker, retrieval policy, or request-path
market-gap feature enters this plan.

## Verdict Review

Verdict is correct at merge `039a5ee625799f44734fe7dc3e732b7659c126c5`.
Repository checks are green, but acceptance semantics are not:

- one of eleven ordinary artifacts is recorded accepted while native output is
  two pages;
- `page_fit` coverage is complete but page-fit success is not `100%`;
- `_run_snapshot()` normalizes traces, discards diagnostics, then the
  projection normalizes again;
- a report can claim complete total workload accounting while known conflicting
  traces were excluded;
- accepted-artifact validation failures and terminal workload validation
  failures use one ambiguous field name;
- first-pass acceptance is `3 / 18`, so the next optimization target is
  generation-format readiness, not retrieval architecture.

## Implementation Outcomes

### Truthful final artifact lifecycle

`generate_from_analysis()`, worker persistence, HITL finalization, and accepted
artifact events share one final-artifact gate. Content acceptance and final
artifact acceptance remain separate. Final acceptance requires:

1. required content and grounding validation pass;
2. native render succeeds;
3. final `page_count == 1` and `page_fit_status == "pass"`.

One bounded deterministic trim/rerender may repair overflow. Unresolved
overflow, missing renderer tools, render failure, or unverifiable page count
stays `review_required`/pending and cannot create an accepted artifact event.

### Lossless measurement contract

`collect_normalized_generation_traces()` becomes the only normalization
boundary. Its result preserves records and diagnostics together:

```text
records
duplicate_count
conflict_count
conflict_trace_ids
source_candidate_count
normalized_trace_count
```

The accepted-artifact projection consumes that normalized result without
normalizing again. Safe accepted-lineage metrics remain available. Total
workload cost and completeness become unavailable when conflicts, unmatched
accepted artifacts, or unattributed accepted artifacts prevent accounting.

### Honest outcome and coverage reporting

Reports expose coverage and outcome separately:

```text
page_fit_coverage: measured / total
page_fit_success: passed / accepted artifacts
```

Accepted one-page success must be `100%` before P1-A can pass. Validation
metrics use explicit names:

```text
validation_failure_event_count
terminal_validation_failed_job_count
```

The acceptance verifier rejects `measurement_status: measured` when trace
conflicts or accepted-artifact page-fit failures remain.

### First-pass improvement evidence

Existing validator details classify `generation_format_defect` into bounded
causes. One feature-flagged section-sufficiency preflight and output-contract
experiment runs on the same workload and settings as incumbent. Promotion
requires higher first-pass acceptance without violating frozen P0 gates,
grounding, one-page finalization, or reporting integrity.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-using-git-worktrees`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: task-specific worktree created from `origin/main`; current dirty checkout remains untouched
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed source, tests, acceptance metadata, generated evidence, and plan-owned docs; run declared local checks; create approved isolated worktree
- User-approval actions: push, merge, publication, dependency installation, destructive recovery, discard, cleanup, and acceptance-status promotion
- Parallel ownership: none; shared lifecycle and reporting contracts force serialization
- Sequential fallback: execute Tasks 1–7 in order in one controller-owned worktree
- Experiment fixture: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\linkedin-2026-10-02-22-52-15.json`. Treat this untracked file as read-only input; capture its SHA-256 before Task 1, do not copy it into tracked files, and stop if it is missing or changes between incumbent and candidate runs.

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-one-page-lossless-reporting` created from `origin/main` at activation
- Base commit: `039a5ee625799f44734fe7dc3e732b7659c126c5`
- Expected workspace: `current checkout contains preserved untracked .tmp/, .venv/, scratch scripts, and local data; no cleanup or discard`
- Next action: `rerun same-workload incumbent/candidate experiment after FITCV_LLM_API_KEY is available; refresh evidence after legacy non-one-page/unattributed records are resolved`
- Blockers: `P1-A ordinary-workload page-fit gate remains blocked by one historical non-one-page accepted record; P1-B measurement remains incomplete with unattributed accepted artifacts; Task 6 live comparison is blocked by missing FITCV_LLM_API_KEY; P1-C and P2 are intentional deferrals`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | isolated worktree | `codex` | none | baseline tests and report snapshot | focused baseline captured; implementation tests pass |
| Task 2 | `completed` | isolated worktree | `codex` | Task 1 | normalization conflict regression | shared lossless collector and conflict tests pass |
| Task 3 | `completed` | isolated worktree | `codex` | Task 2 | one-page lifecycle regression | render, trim, and final-gate tests pass |
| Task 4 | `completed` | isolated worktree | `codex` | Task 3 | persistence and HITL boundary tests | persistence, worker, and HITL tests pass |
| Task 5 | `completed` | isolated worktree | `codex` | Task 2, Task 4 | report/verifier contract tests | report/verifier tests pass; P1-B remains incomplete |
| Task 6 | `blocked` | isolated worktree | `codex` | Task 5 | same-workload experiment evidence | blocked before provider execution; `FITCV_LLM_API_KEY` absent |
| Task 7 | `blocked` | isolated worktree | `codex` | Task 6 | full verification and reconciled state | frontend typecheck, `328` frontend tests, build, and audit passed; backend suite `3063 passed, 10 skipped`; verifier passed; promotion gates remain blocked only by evidence/API-key gates |

## Task Breakdown

### Task 1: Freeze contracts and capture failing proof

**Purpose:** Establish exact baseline and convert verdict failures into focused
regressions before implementation.

**Files And Symbols:**

- Inspect: `src/fitcv_cp/run_artifact_contracts.py:collect_normalized_generation_traces`, `build_accepted_cv_effort_projection`; `scripts/benchmark_cv_efficiency.py:_run_snapshot`, `build_baseline`; `src/fitcv/agentic_cv_generation.py:generate_from_analysis`; `src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact`.
- Modify tests: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_benchmark_cv_efficiency.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_cv_render_acceptance.py`.

**Steps:**

1. Run the focused baseline suite and record current counts, current canonical
   report digest, and the ordinary `3 / 18` first-pass baseline.
2. Add a regression fixture with one valid accepted trace and two conflicting
   failed copies sharing identity.
3. Add a fixture where final render reports `page_count: 2` while content
   validation is valid.
4. Add assertions that current behavior fails the new contract; do not weaken
   existing P0 tests or mutate historical evidence.

**Authority:**

- Preauthorized local actions: add focused failing tests and run baseline commands
- Stop for: missing authoritative renderer boundary, changed P0 behavior, or inability to reproduce either verdict defect

**Exit Criteria:** Baseline is recorded, both regressions fail against current
code, and no unrelated tracked file changes exist in the isolated worktree.

### Task 2: Make normalized traces one lossless shared contract

**Purpose:** Remove duplicate normalization and prevent known conflicts from
being erased before reporting.

**Files And Symbols:**

- Modify: `src/fitcv_cp/run_artifact_contracts.py:collect_normalized_generation_traces`, `build_accepted_cv_effort_projection`.
- Modify: `scripts/benchmark_cv_efficiency.py:_run_snapshot`, `_sum_workload`, `build_baseline`.
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_benchmark_cv_efficiency.py`.

**Steps:**

1. Preserve existing lineage enrichment, exact duplicate collapse, conflict
   exclusion, and `trace_id + run_job_id` matching.
2. Extend the normalized result with `source_candidate_count` and
   `normalized_trace_count` while retaining conflict IDs and counts.
3. Let `_run_snapshot()` collect once and pass the complete normalized result
   to the projection. The projection must consume that result directly and
   must not call normalization again on already-normalized records.
4. Keep a compatibility path for direct projection callers that still provide
   raw records; that path performs one collection internally and is covered by
   existing tests.
5. Add separate statuses for accepted-artifact attribution and total-workload
   accounting. Set total workload accounting to incomplete when any trace
   conflict, unmatched accepted artifact, or unattributed accepted artifact is
   present.
6. Keep safely attributable accepted-lineage cost available. Set
   `total_workload_cost_per_accepted_cv` to `null` when total-workload
   accounting is incomplete; never choose between conflicting copies.

**Authority:**

- Preauthorized local actions: edit shared trace/report contracts and their focused tests; run contract and benchmark tests
- Stop for: schema ambiguity, guessed conflict resolution, or a second normalization owner

**Exit Criteria:** The reproduced three-trace fixture surfaces conflict IDs,
reports incomplete workload accounting, keeps safe accepted-lineage metrics,
and never claims complete total-workload cost.

### Task 3: Enforce one-page final artifact acceptance

**Purpose:** Make every accepted CV a real, rendered, one-page deliverable.

**Files And Symbols:**

- Modify: `src/fitcv/cv_generator.py:render_cv_markdown`, new `render_cv_native_acceptance`, and bounded page-budget helpers; `src/fitcv/validator.py:check_length_constraints` only if shared status semantics require it.
- Add one shared final-artifact predicate in `src/fitcv/cv_generator.py:final_artifact_acceptance_passes`; generation, persistence, and HITL paths consume this predicate instead of reimplementing page-fit checks.
- Modify: `src/fitcv/agentic_cv_generation.py:generate_from_analysis`, `_run_repair_cycle`, `_build_result`, and trace summary builders.
- Verify: `tests/test_cv_render_acceptance.py`, `tests/test_cv_generator.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_pipeline.py`.

**Steps:**

1. Add one renderer boundary using the existing native toolchain contract from
   `tests/test_cv_render_acceptance.py` (`pandoc`, `xelatex`, `pdfinfo`,
   `pdftotext`). Missing tools or render failure produce an explicit
   `render_unavailable`/`render_failed` result, never an accepted artifact.
2. Keep content validation separate from final-artifact validation. Record
   `content_acceptance` and `final_artifact_acceptance` in the generation result
   and trace output.
3. After content validation, render once and require `page_count == 1`.
4. On overflow, run at most one deterministic compiler trim using existing
   `cv_content_plan_v1` ordering. Remove duplicate claims first, then lowest JD
   relevance, lowest evidence differentiation, lowest marginal requirement
   coverage, verbose wording, and lower-priority project detail. Preserve
   mandatory requirement coverage, quantified outcomes, grounded claims, and
   identity/education/work data.
5. Rerender the trimmed structured document. A second overflow or any failed
   render yields `page_fit_status: unresolved` and final status
   `review_required`/pending, not `accepted`.
6. Store final page count, page-fit status, renderer status, trim count, and
   artifact checksum in the canonical trace/result. Do not treat the content
   plan's `page_fit_status: unverified` as final render proof.

**Authority:**

- Preauthorized local actions: edit generation/render helpers and focused tests; use configured native render tools already required by render acceptance
- Stop for: renderer unavailable in the target runtime, protected claim removal, more than one deterministic trim, or a request for a second LLM verifier

**Exit Criteria:** Synthetic one-page output passes; two-page output trims and
passes when safe; irreducible overflow, missing tools, and render failure cannot
be marked accepted; page count is sourced from native render evidence.

### Task 4: Apply final gate at persistence and HITL boundaries

**Purpose:** Prevent downstream status mapping from re-accepting content that
failed final artifact acceptance.

**Files And Symbols:**

- Modify: `src/fitcv_cp/worker_job.py:execute_pipeline_run` generation-status mapping and `_build_cv_generation_debug_payload`.
- Modify: `src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact`, `_append_accepted_artifact_event`, review action handlers.
- Inspect/modify only if required by existing status constraints: `src/fitcv_cp/sqlite_store.py` CV-version status/metadata contract.
- Verify: `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py`.

**Steps:**

1. Map generation output to persisted `generated` only when
   `final_artifact_acceptance_passes` passes. Keep validation-passed/content-only drafts in
   `review_required` until render evidence exists.
2. Make `approve_as_is` and equivalent HITL finalization reject missing,
   failed, unresolved, or non-one-page render evidence.
3. Emit `accepted_artifact_events` only after the final gate. Persist the same
   `trace_id`, `run_job_id`, `page_fit_status`, `render_acceptance`, and final
   status in debug records and events.
4. Preserve idempotency: repeated approval cannot create duplicate accepted
   events or versions. Do not add a database migration unless the current
   metadata columns cannot preserve the contract.

**Authority:**

- Preauthorized local actions: edit worker/app persistence gates and focused backend tests; preserve current status vocabulary and idempotency behavior
- Stop for: destructive migration, changed retry semantics, or any path that emits an accepted event without final render proof

**Exit Criteria:** Automated generation, manual approval, batch approval, and
regeneration paths all reject non-final artifacts and preserve accepted lineage
on one-page success.

### Task 5: Rebuild honest efficiency and acceptance gates

**Purpose:** Make every efficiency number derive from the one normalized path and
make acceptance state distinguish coverage, success, and accounting integrity.

**Files And Symbols:**

- Modify: `scripts/benchmark_cv_efficiency.py:_run_snapshot`, `build_baseline`, `material_report_metrics`.
- Modify: `scripts/verify_fitcv_acceptance.py:_verify_runtime_efficiency`, `build_acceptance_report`.
- Modify: `src/fitcv_cp/run_artifact_contracts.py` aggregate field names and schema version.
- Update after fresh evidence: `config/acceptance_state.yaml`, `artifacts/acceptance_state.json`, `docs/superpowers/evidence/` canonical JSON/Markdown pair.
- Verify: `tests/test_benchmark_cv_efficiency.py`, `tests/test_fitcv_cp/test_acceptance_verifier.py`, `tests/test_acceptance_state.py`.

**Steps:**

1. Expose `page_fit_coverage` and `page_fit_success` separately. The latter
   counts only final accepted artifacts with native `page_count == 1`.
2. Rename ambiguous metrics to
   `validation_failure_event_count` for failed attempts in accepted lineages
   and `terminal_validation_failed_job_count` for terminal workload failures.
3. Add conflict and workload-accounting gates. `measurement_status: measured`
   is invalid when conflict count, unmatched accepted count, unattributed count,
   or accepted non-one-page count is nonzero.
4. Preserve historical reports as immutable evidence. Regenerate one canonical
   current JSON/Markdown pair with a bumped schema version and material digest.
5. Set current state conservatively after verification: P1-A
   `implementation_status: verified` plus `acceptance_status:
   blocked_by_ordinary_page_fit` until the ordinary workload passes; P1-B
   `measurement_status: incomplete` until conflict-free accounting is proven;
   P1-C and P2 remain deferred.

**Authority:**

- Preauthorized local actions: edit reporting/verifier contracts and regenerate declared acceptance artifacts after source proof
- Stop for: any promotion based on stale evidence, altered frozen P0 metrics, or a report that mixes accepted-lineage and total-workload denominators

**Exit Criteria:** Reports show coverage versus outcome separately, conflicts
fail closed for total-workload numbers, metric names are unambiguous, and the
verifier rejects the old false-complete state.

### Task 6: Run one bounded first-pass acceptance experiment

**Purpose:** Improve `16.7%` first-pass acceptance only after finalization and
reporting integrity are correct.

**Files And Symbols:**

- Modify: `src/fitcv/agentic_cv_generation.py:build_cv_content_plan`, `generate_from_analysis`, `_writer_attempt` trace fields.
- Modify: `src/fitcv/cv_generator.py:build_structured_generation_prompt`, `build_live_structured_cv_response_schema` only for the selected contract change.
- Modify if required for an explicit candidate toggle: `src/fitcv_cp/settings_schema.py` and its focused tests.
- Verify: `tests/test_pipeline_agentic_late_stage.py`, `tests/test_cv_generator.py`, `tests/test_config.py`, `tests/test_benchmark_cv_efficiency.py`.

**Steps:**

1. Derive `generation_format_defect` subcategories from existing validation
   details: missing mandatory section, shallow section, malformed section,
   invalid heading/schema, missing required field, length/budget violation, and
   other deterministic format defect.
2. Use the experiment fixture declared in Execution Approach for both incumbent
   and candidate runs. Record fixture SHA-256, `.env.yaml` path, effective
   model, run IDs, and fresh SQLite database paths in the evidence file; use the
   existing local submission path (`jobs_path`, `config_path`, and inline local
   execution), not a new runner or service.
3. Add deterministic section-sufficiency preflight before the provider call.
   It must check evidence, section budget, grounded high-value claims, and
   impossible requirements, and record its result without inflating provider
   call counts.
4. Strengthen only the existing generation prompt/schema contract with section
   order, min/max budgets, deterministic omission rules, one-page target, and
   no unsupported filler. Do not add another agent or verifier.
5. Keep retries selective: bounded retry for provider variance, deterministic
   repair for structural defects, no repeated full provider call for the same
   deterministic defect, and compiler trim for overflow.
6. Run incumbent and candidate on identical candidate/profile/jobs/model
   settings. Promote only if first-pass acceptance rises and all hard gates
   remain true: unsupported claims `0`, frozen P0 metrics unchanged, final
   accepted page-fit success `100%`, trace conflicts `0`, unattributed artifacts
   `0`.

**Authority:**

- Preauthorized local actions: edit existing content-plan/prompt/validator paths, add one bounded candidate toggle if required, and run same-workload experiment
- Stop for: retrieval-policy change, provider/model change, global retry suppression, second LLM verifier, or no identical incumbent comparison

**Exit Criteria:** Experiment report includes first-pass rate, calls per accepted
CV, tokens per accepted CV, retry outcomes, failure categories, and final-artifact
gates. Candidate is either promoted from evidence or rejected without changing
the incumbent.

### Task 7: Reconcile state and complete verification

**Purpose:** Prove integrated behavior and leave durable evidence without
claiming deferred work.

**Files And Symbols:**

- Verify changed source and tests across Tasks 2–6.
- Update only canonical acceptance/evidence files owned by Task 5.
- Keep `docs/superpowers/plans/` and historical evidence consistent with the
  approved deferrals.

**Steps:**

1. Run focused backend, lifecycle, render, benchmark, and verifier tests.
2. Run full suite and native render acceptance with `pandoc`, `xelatex`,
   `pdfinfo`, and `pdftotext` available.
3. Rebuild the canonical report from the declared ordinary workload and verify
   material digest equality.
4. Run `git diff --check`, generated-surface checks, and acceptance verifier.
5. Use `skill-verification-before-completion` to confirm fresh HEAD, workspace
   inventory, evidence, deferrals, and residual risks.

**Authority:**

- Preauthorized local actions: run declared verification and update plan-owned evidence from fresh outputs
- Stop for: any failed hard gate, stale evidence, unexpected tracked mutation, or request to close P1-C/P2

**Exit Criteria:** Every accepted artifact in the measured workload is final and
one-page; one normalized trace path feeds all efficiency numbers; conflicts and
unattributed work are zero; first-pass experiment has a same-workload verdict;
P1-C and P2 remain deferred.

## Verification

### Focused contract proof

```powershell
python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_acceptance_verifier.py
```

Proves one normalization boundary, preserved conflict diagnostics, null total
workload cost on conflict, separate validation names, and coverage/success
reporting.

### Finalization and backend proof

```powershell
python -m pytest -q tests/test_pipeline_agentic_late_stage.py tests/test_cv_generator.py tests/test_cv_render_acceptance.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py
```

Proves content acceptance versus final artifact acceptance, native page count,
bounded trim/rerender, persistence gates, HITL approval gates, idempotency, and
accepted-event lineage.

### Full proof

```powershell
Push-Location frontend
npm ci --ignore-scripts
npm run build
Pop-Location
python -m pytest -q
python scripts/verify_fitcv_acceptance.py --output .tmp/fitcv-acceptance-final.json
python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json
git diff --check
```

The frontend build is required before the full suite because `frontend/dist/`
is ignored generated output consumed by both `/app` host tests and the
PyInstaller packaging contract. Missing output is an environment precondition
failure, not a reason to weaken those tests.

The final report must be rebuilt from one declared ordinary workload, include
material digest equality, show `page_fit_coverage` separately from
`page_fit_success`, and set total workload metrics unavailable when accounting
is incomplete.

### Experiment proof

Use identical incumbent/candidate workload, profile, job set, model, and run
limits. Record:

- attempted generations and first-pass acceptance rate;
- accepted final one-page artifacts;
- provider calls, tokens, regenerations, retry success/failure;
- generation-format defect categories;
- artifact acceptance and generation latency;
- trace conflicts and unattributed artifacts;
- frozen P0-B/P0-C results.

No promotion occurs without same-workload comparison and all hard gates.

## Completion Criteria

- [ ] No accepted artifact lacks native render proof. Current historical
  evidence still contains one pre-gate accepted record without one-page proof.
- [ ] Every accepted measured artifact has `page_count == 1` and
  `page_fit_status == "pass"`.
- [x] Overflow uses at most one deterministic trim/rerender; unresolved
  overflow remains pending/review-required.
- [x] `collect_normalized_generation_traces()` is the only normalization
  boundary for benchmark metrics.
- [x] Conflict IDs survive into reports and conflict-bearing workload reports
  cannot claim complete total cost.
- [x] Accepted-lineage and total-workload metrics remain distinct and validation
  fields use explicit semantics.
- [x] Page-fit coverage and page-fit success are separate report fields.
- [x] Acceptance verifier rejects false `measured` status for conflicts or
  accepted non-one-page artifacts.
- [ ] First-pass experiment uses identical workload and preserves frozen P0
  gates. Live comparison blocked before provider execution by missing API key.
- [x] P1-C and P2 remain explicitly deferred.
- [x] Fresh verification returns `verified` before any branch publication or
  merge action.

## Non-Goals And Deferred Work

- P1-C offline market-gap aggregation remains deferred.
- P2 remains frozen: no GraphRAG, new vector database, LLM verifier, reranker,
  dynamic routing, extra agents, or larger retrieval pools.
- No broad deep-copy refactor.
- No retrieval-policy replacement.
- No global retry suppression.
- No claim that reduced human effort is proven while genuine HITL telemetry is
  zero.
