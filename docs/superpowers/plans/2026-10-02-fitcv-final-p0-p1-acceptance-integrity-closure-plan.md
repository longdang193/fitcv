---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
layer: change
---

# Final P0/P1 Acceptance Integrity Closure Plan

## Goal

Close remaining P0 and P1 acceptance defects identified in the verdict against
commit `3af97052dedd168fe5128731671e039b16268b6f`, without reopening closed
scope or adding new architecture.

The verdict is accepted as current truth over the committed status because it
reproduces four defects in committed code:

- P0-B accepts an invalid final-state vocabulary and excludes all-negative
  requirements from false-positive accounting.
- P0-C lets broad education discovery override a required degree field.
- P1-B measures accepted effort from finalized HITL actions, so automatic
  accepted CVs are absent from `accepted_cv_effort_v1`.
- P1-B accepted effort omits failed and regenerated attempts that contributed
  to the accepted artifact.

P0-A stays closed. P1-A stays maintenance-only. P1-C and P2 stay deferred.

## Implementation Outcomes

### Shared acceptance contract and provenance

Runtime evaluation, rendered acceptance state, tests, and evidence use one
status vocabulary with `passed` as the accepted state. The acceptance state
labels frozen evaluation inputs as `evaluation_freeze_commit`; generated
evaluation evidence records the runtime commit that evaluates them, and
historical status evidence is explicitly superseded rather than silently
rewritten.

### Fail-closed P0-B and P0-C behavior

P0-B reports recall over oracle-supported requirements but precision and safety
over every evaluated requirement and assignment. All-negative requirements,
unscoped assignments, unsupported assignments, and unknown assignments cannot
produce a passing safety gate. P0-C keeps broad aliases for discovery only and
requires strict proof for degree level, degree field, entity/tool/domain, and
duration or other mandatory qualifiers.

### Unified P1-B accepted-artifact measurement

Automatic and human-confirmed accepted artifacts persist through one accepted-
artifact contract and feed the existing `accepted_cv_effort_v1` projection.
Projection records include every contributing generation attempt, provider
usage, validation failure, regeneration, render retry, review question, human
action, reused resolution, and wall-clock interval. Replay is idempotent and
does not double-count accepted artifacts or actions.

### Reproducible final closure

Committed acceptance state, sanitized fixtures, evaluator output, P0-C
counterexamples, P1-B projection output, clean-checkout execution, Full Suite,
Focused Smoke Tests, and Render Acceptance provide fresh evidence for final
closure. P1-C and P2 remain explicitly deferred in the final state.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`; commit and push require explicit user authorization
- Preauthorized local actions: inspect source and committed artifacts, edit listed files, add sanitized regression fixtures and tests, run declared local checks, and write evidence docs without staging preserved scratch files
- User-approval actions: commit, push, merge, publication, external writes, destructive recovery, cleanup, dependency installation outside declared CI steps, and production-default changes
- Parallel ownership: none; shared evaluator, acceptance state, and projection contracts require serial edits
- Sequential fallback: execute Tasks 1–6 in order and stop at each exit gate before continuing

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `3af97052dedd168fe5128731671e039b16268b6f`
- Expected workspace: `main` at base commit with existing untracked scratch/runtime files preserved and excluded from all changes; stage only files named by completed tasks
- Next action: branch disposition after verified closure; commit and push require explicit authorization
- Blockers: none; P1-C and P2 are intentional scope deferrals

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | real-state contract test and renderer/evaluator agreement | `16 passed, 4 skipped`; renderer accepted committed state |
| Task 2 | `completed` | current | `codex` | Task 1 | all-negative, unsupported, unknown, and unscoped assignment tests | `14 passed, 4 skipped`; all-negative assignments counted |
| Task 3 | `completed` | current | `codex` | Task 1 | strict qualifier positive and hard-negative tests | `120 passed`; education/tool/domain/duration mismatches fail closed |
| Task 4 | `completed` | current | `codex` | Task 1 | automatic/HITL persistence and replay tests | `807 passed`; focused accepted-artifact suite passed |
| Task 5 | `completed` | current | `codex` | Task 4 | complete-effort projection and failure-taxonomy tests | `20 passed`; workload baseline `17 / 11 / 6 / 9` preserved |
| Task 6 | `completed` | current | `codex` | Tasks 2–5 | clean-checkout acceptance and fresh full verification | `verified`; final closure evidence and fresh gates recorded |

## Task Breakdown

### Task 1: Unify acceptance status and provenance

**Purpose:**
- Make committed acceptance state, renderer, runtime evaluator, and tests use
  one valid contract.

**Task Function:**
- Reconcile state vocabulary and frozen-input provenance at the existing
  acceptance boundary.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded contract correction with repository-wide test impact.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: lead controller runs the real-state regression and final
  verification.

**Specification Coverage:**
- Standardize accepted priority status on `passed`, matching P1-B and the
  committed renderer contract.
- Load real committed `config/acceptance_state.yaml` in a regression and run
  the actual runtime evaluator.
- Rename YAML field `source_commit` to `evaluation_freeze_commit` and bump the
  rendered acceptance schema only if required by the existing contract.
- Record `evaluated_commit` in generated evaluation evidence from the checked-
  out runtime, without mutating the frozen-input field.
- Add a concrete `supersedes` list to final closure evidence for historical
  `measurement_only` and earlier closure claims.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `config/acceptance_state.yaml`
- Inspect: `scripts/render_acceptance_state.py:_validate_state`, `ALLOWED_STATUSES`
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:validate_public_inputs`, `_load_acceptance_state`
- Modify: `config/acceptance_state.yaml`
- Modify: `scripts/evaluate_p0b_source_job_relevance.py:validate_public_inputs`
- Modify: `scripts/render_acceptance_state.py` only if schema/provenance validation changes
- Verify: `tests/test_acceptance_state.py`, `tests/test_p0b_source_job_relevance_evaluator.py`

**Dependencies:**
- The existing renderer remains the canonical status vocabulary owner; do not
  create a second status registry.
- Do not rewrite frozen corpus inputs or silently change historical evidence.

**Authority:**
- Preauthorized local actions: edit acceptance-state contract, evaluator validation, focused tests, and supersession metadata in listed files.
- Stop for: changing frozen thresholds, changing corpus identity, adding a new acceptance service, or modifying unrelated statuses.

**Steps:**
- [x] Step 1: Trace every consumer of `source_commit`, `p0_b`, and status values; migrate `source_commit` to `evaluation_freeze_commit` without changing frozen corpus identity.
- [x] Step 2: Reuse `scripts/render_acceptance_state.py:ALLOWED_STATUSES` from runtime validation or consolidate the existing owner without duplicating vocabulary.
- [x] Step 3: Make `passed` valid in runtime evaluation and add a regression that loads the real committed YAML rather than a handcrafted state.
- [x] Step 4: Add generated `evaluated_commit` evidence and a concrete `supersedes` list in final closure evidence; render the state deterministically.

**Verification:**
- [x] `python -m pytest -q tests/test_acceptance_state.py tests/test_p0b_source_job_relevance_evaluator.py`
- Expected: committed state renders; real-state runtime validation does not report `p0_b_status_invalid`; frozen-input provenance remains explicit.

**Exit Criteria:**
- Renderer and runtime evaluator accept the same status vocabulary, and no test relies only on a synthetic acceptance-state dictionary for this contract.

### Task 2: Fix P0-B requirement and assignment precision

**Purpose:**
- Make P0-B safety accounting include every evaluated requirement and runtime assignment.

**Task Function:**
- Separate recall scope from assignment-precision scope while preserving oracle
  support as the sole gold authority.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: high-correctness-risk evaluator change with bounded fixtures.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: focused evaluator tests cover malformed and adversarial rows.

**Specification Coverage:**
- Recall denominator includes only requirements with at least one
  oracle-supported evidence item.
- Safety denominator includes every evaluated requirement and every selected
  assignment.
- Compute candidate requirement recall, selected requirement coverage, all
  assigned pairs, supported assigned pairs, unsupported/unknown assignments,
  and assignment precision.
- Treat `unscoped_selected_pairs` as a safety failure for evaluated cohort rows
  unless explicitly classified by the review protocol.
- All-negative requirements such as Claude Code contribute zero recall gold but
  count every assignment as false positive.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:_runtime_requirement_metrics`, `_evaluate_selected`, `evaluate_evidence_link_review`, `evaluate_actual_fitcv`
- Inspect: `scripts/calibrate_p0b_recovery.py:selected_pairs_from_review`, `classify_pairs`
- Modify: `scripts/evaluate_p0b_source_job_relevance.py`
- Modify: `scripts/calibrate_p0b_recovery.py` only where calibration consumes corrected pair sets
- Verify: `tests/test_p0b_source_job_relevance_evaluator.py`, `tests/test_calibrate_p0b_recovery.py`
- Add or extend: sanitized unit fixture under `tests/fixtures/p0b/` without changing frozen protected corpus files

**Dependencies:**
- Task 1 defines valid committed acceptance status and runtime state loading.
- Existing oracle labels, review rows, and unknown semantics remain authoritative.

**Authority:**
- Preauthorized local actions: edit evaluator/calibration pair accounting and add sanitized regression cases.
- Stop for: changing oracle labels, treating unknown as supported or unsupported without protocol evidence, or changing frozen thresholds.

**Steps:**
- [x] Step 1: Build explicit sets for all evaluated requirements, oracle-supported requirements, all assigned pairs, supported assigned pairs, and unsupported/unknown assignments.
- [x] Step 2: Keep recall and coverage denominators oracle-scoped; calculate precision and safety over all assignments.
- [x] Step 3: Make unscoped assignments fail the safety gate unless their review row explicitly classifies them outside the evaluated cohort.
- [x] Step 4: Add all-negative Claude Code, unsupported assignment, unknown assignment, extra assignment, and unscoped assignment regressions.
- [x] Step 5: Update calibration classification so every assignment pair lands in exactly one bucket and no false positive disappears through scope filtering.

**Verification:**
- [x] `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py`
- Expected: valid fixtures report `candidate_requirement_recall == 1.0`, `selected_requirement_coverage == 1.0`, `assignment_precision == 1.0`, and zero unsupported/unknown assignments; each negative case fails closed.

**Exit Criteria:**
- P0-B cannot become eligible while any evaluated assignment is unsupported, unknown, or unscoped.

### Task 3: Restore strict P0-C qualifier proof

**Purpose:**
- Prevent discovery aliases from proving essential education, tool, domain, or duration qualifiers.

**Task Function:**
- Separate candidate discovery from strict evidence verification at the existing evidence authority.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: localized rule correction with deterministic counterexamples.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: focused evidence and coverage tests provide independent positive and negative proof.

**Specification Coverage:**
- Broad aliases may discover candidates but cannot change an essential
  qualifier from false to true.
- Verified support requires strict degree level, degree field, entity/tool/domain,
  duration, and other mandatory qualifier agreement.
- Contradiction or mismatch wins over broad lexical similarity.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_assess_responsibility_support`, `_assess_requirement_support`, `_responsibility_support_map`, `_parse_requirement_qualifiers`
- Inspect: `src/fitcv/agentic_cv_analysis.py:_requirement_profile_match`, `_build_requirement_coverage`
- Modify: `src/fitcv/evidence.py:_assess_responsibility_support` and the smallest shared qualifier helper required
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`

**Dependencies:**
- Existing tokenization, canonical terms, qualifier parsing, and negation
  helpers remain canonical.
- Do not replace the retrieval system or add a new verifier dependency.

**Authority:**
- Preauthorized local actions: edit strict qualifier evaluation and add focused positive/hard-negative tests.
- Stop for: broad retrieval redesign, new model dependency, changed production thresholds, or unresolved requirement semantics.

**Steps:**
- [x] Step 1: Remove any path that forces `level_domain_match = True` from discovery-only education matches.
- [x] Step 2: Preserve candidate diagnostics while requiring strict `verified_support` before authoritative coverage or selection support.
- [x] Step 3: Add valid positives for matching degree field, tool/domain, role/domain, duration, and level.
- [x] Step 4: Add hard negatives for Computer Science versus International Business, Claude Code versus generic tooling, executive search versus generic market research, and duration/level mismatch.

**Verification:**
- [x] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Expected: valid positives remain supported; every essential-qualifier hard negative fails closed and cannot enter verified coverage.

**Exit Criteria:**
- Discovery evidence never proves a mismatched essential qualifier.

### Task 4: Persist one accepted-artifact contract for automatic and HITL paths

**Purpose:**
- Feed automatic and human-confirmed accepted CVs into one persisted SSOT.

**Task Function:**
- Extend existing run-artifact persistence with an idempotent accepted-artifact
  record, not a second measurement system.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: material backend state change with replay and data-loss risk.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: direct SQLite and worker-path tests cover both acceptance modes.

**Specification Coverage:**
- Persist artifact ID, job ID, acceptance mode (`automatic` or
  `human_confirmed`), acceptance and finalization timestamps, and linkage to
  generation telemetry and source `cv_versions` artifact.
- Both paths call the same persistence boundary.
- HITL interaction rows remain interaction history, not acceptance source of truth.
- Replayed finalization is idempotent and cannot create duplicate accepted rows.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`
- Inspect: `src/fitcv_cp/app_run_support.py` accepted-artifact and HITL finalization path
- Inspect: `src/fitcv_cp/worker_job.py` automatic acceptance/final-artifact path
- Inspect: `src/fitcv_cp/sqlite_store.py` `cv_versions` persistence and schema/migration helpers
- Inspect: `src/fitcv_cp/app.py` review finalization endpoint and transaction boundary
- Modify: the smallest shared persistence boundary among the listed modules
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 acceptance provenance changes do not alter run-artifact identity.
- Existing `cv_versions` and generation telemetry remain canonical sources for
  artifact content and effort details.

**Authority:**
- Preauthorized local actions: edit SQLite schema/accessors, worker/app finalization wiring, contract projection, migrations, and focused tests.
- Stop for: destructive schema migration, dropping existing artifact data, changing user-visible review semantics, or adding a new datastore/service.

**Steps:**
- [x] Step 1: Trace automatic and HITL final-artifact paths to locate their common final-state boundary.
- [x] Step 2: Add the minimum persisted accepted-artifact fields and uniqueness/idempotency constraint needed for one row per accepted artifact.
- [x] Step 3: Write both automatic and human-confirmed paths through the same insert-or-ignore/upsert contract and retain HITL actions separately.
- [x] Step 4: Make `build_accepted_cv_effort_projection` consume accepted-artifact records plus linked telemetry instead of only finalized HITL actions.
- [x] Step 5: Add replay, duplicate-action, missing-telemetry, and final-state tests.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`
- Expected: automatic and human-confirmed acceptance each produce one projection record; replay leaves row count and totals unchanged; accepted artifact state is durable after process restart.

**Exit Criteria:**
- `accepted_cv_effort_v1` denominator includes every accepted artifact regardless of acceptance mode, with no duplicate rows after replay.

### Task 5: Include complete contributing effort in P1-B projection

**Purpose:**
- Make accepted-CV efficiency truthful by retaining all attempts and failure causes that led to acceptance.

**Task Function:**
- Extend existing telemetry aggregation to account for full accepted-artifact lineage.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded aggregation change with accounting correctness risk.

**Validator Profile (optional):**
- Controller-selected: `<none>`
- Selection basis: projection tests assert each metric and failure category.

**Specification Coverage:**
- Accepted effort includes provider calls, input/output tokens, regeneration
  count, validation failures, render retries, review questions, human actions,
  reused resolutions, and wall-clock time for every contributing attempt.
- Failed attempts are not dropped from accepted-artifact effort.
- Classify the six known failures by owner: unsupported claim, missing
  requirement evidence, generation-format defect, page overflow, render
  failure, provider failure, or `other`.
- Preserve `accepted_cv_effort_v1`; do not introduce a second metric schema.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`
- Inspect: `src/fitcv_cp/worker_job.py` generation trace/debug payload builders
- Inspect: `src/fitcv_cp/app_run_support.py` review, regeneration, and human-action records
- Modify: `src/fitcv_cp/run_artifact_contracts.py` and only upstream payload fields required to expose existing data
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py` plus focused worker/app tests
- Document: `docs/superpowers/evidence/2026-10-02-fitcv-p1b-live-measurement.md` or successor evidence file

**Dependencies:**
- Task 4 provides one accepted-artifact lineage and stable join key.
- Existing telemetry records are preferred over new instrumentation; add fields
  only when current persisted data cannot answer a required metric.

**Authority:**
- Preauthorized local actions: edit projection aggregation, existing telemetry joins, failure classification, focused tests, and sanitized evidence output.
- Stop for: inventing retrospective data, excluding failed attempts to improve metrics, or changing the `accepted_cv_effort_v1` schema name without migration approval.

**Steps:**
- [x] Step 1: Map every contributing attempt and persisted event to the existing accepted artifact lineage.
- [x] Step 2: Aggregate all required effort fields and classify terminal failures without dropping attempts.
- [x] Step 3: Preserve reused resolutions and human actions as effort inputs while deduplicating replayed event IDs.
- [x] Step 4: Add a fixture matching the live baseline shape: 17 attempts, 11 accepted, 6 validation failures, and 9 regenerations; assert accepted-artifact totals include all contributing attempts.
- [x] Step 5: Record measurement limitations and sample size in evidence without claiming general performance improvement.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py`
- Expected: projection contains complete attempt counts, failure categories, regeneration count, latency, provider/token usage, and stable deduplicated totals.

**Exit Criteria:**
- P1-B measurement is complete for accepted artifacts and cannot look better by omitting failed or regenerated attempts.

### Task 6: Re-run clean-checkout acceptance and close state

**Purpose:**
- Produce fresh evidence and update acceptance state only after all required gates pass.

**Task Function:**
- Execute final validation, reconcile documentation, and record explicit deferrals.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final verification and evidence reconciliation.

**Validator Profile (optional):**
- Controller-selected: `review-1`
- Selection basis: independent review of final proof and stale-status risks; no implementation edits.

**Specification Coverage:**
- Final state may mark P0-B and P0-C passed only after their exact gates pass.
- P1-A remains `maintenance_only`; P1-B becomes passed only with unified
  persistence and complete-effort proof.
- P1-C and P2 remain `deferred`.
- Clean checkout must reproduce committed acceptance without preserved local
  scratch files.

**Required Skills:**
- `skill-verification-before-completion`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `.github/workflows/repo-hooks.yml` Full Suite, Focused Smoke Tests, Render Acceptance commands
- Inspect: `config/acceptance_state.yaml` and referenced manifests/evidence
- Modify: `config/acceptance_state.yaml` only after fresh gates pass
- Add/update: `docs/superpowers/evidence/2026-10-02-fitcv-final-p0-p1-closure.md`
- Verify: clean-checkout output and generated acceptance-state artifact

**Dependencies:**
- Tasks 1–5 completed with task-local proof.
- No acceptance status is promoted from source inspection alone.

**Authority:**
- Preauthorized local actions: run declared checks, create evidence docs, update acceptance state after gates pass, and inspect clean-checkout results.
- Stop for: any failed required gate, stale or ambiguous evidence, unexpected tracked/untracked mutation, external publication, or request to close P1-C/P2.

**Steps:**
- [x] Step 1: Run focused P0-B, P0-C, and P1-B suites and inspect JSON/projection outputs.
- [x] Step 2: Run clean-checkout-equivalent evaluation using committed sanitized fixtures and confirm preserved local files are irrelevant.
- [x] Step 3: Run Full Suite, Focused Smoke Tests, and Render Acceptance using workflow commands.
- [x] Step 4: Reconcile acceptance state, evidence paths, supersession metadata, and explicit P1-C/P2 deferrals.
- [x] Step 5: Run `git diff --check`, `git status --short`, and final verification skill before any later commit or push request.

**Verification:**
- [x] `python -m pytest -q tests/test_acceptance_state.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`
- [x] `python -m pytest -q -m "not render_acceptance"`
- [x] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- [x] clean-checkout rerun of committed acceptance commands from `.github/workflows/repo-hooks.yml`
- Expected met: all required checks pass; final state contains no P0/P1 correctness blocker; P1-C and P2 remain deferred; preserved scratch files are not staged.

**Exit Criteria:**
- `skill-verification-before-completion` returns `verified`, with fresh command output and no unresolved required task, failed gate, stale status, or unrecorded scope deviation.

## Verification

Result: `verified`.

- `python -m pytest -q tests/test_acceptance_state.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py`
- `python -m pytest -q -m "not render_acceptance"`
- `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- Clean-checkout rerun of committed evaluator and workflow commands.
- `git diff --check`
- `git status --short --branch`; only intended tracked files may be staged.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-B status and provenance contract pass against real committed state.
2. P0-B recall, coverage, and all-assignment precision gates pass with zero
   unsupported or unknown assignments.
3. P0-C strict qualifier positives pass and required hard negatives fail closed.
4. Automatic and human-confirmed accepted artifacts feed one idempotent
   `accepted_cv_effort_v1` projection.
5. P1-B effort includes all contributing attempts and failure categories.
6. Full Suite, Focused Smoke Tests, Render Acceptance, and clean-checkout
   acceptance rerun pass.
7. Acceptance state and evidence supersede stale claims explicitly.
8. P1-C and P2 remain explicitly deferred; no new service, agent, datastore,
   graph, vector store, management surface, or performance optimization is
   added as part of closure.
9. `skill-verification-before-completion` confirms fresh proof and returns
   `verified` before any branch disposition.
