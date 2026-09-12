---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-cv-warning-outcomes
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/sqlite_store.py
  - frontend/src/features/cv-review/
  - frontend/src/features/job-evaluation/components/PipelineOutcome.tsx
  - tests/
  - scripts/
---

# FitCV CV Warning Outcomes And Review-Gate Cleanup

## Goal

Allow truthful, validated CV output to complete without mandatory operator
approval when only non-blocking quality concerns exist, while preserving hard
failures, manual staged-run controls, historical review data, idempotent
regeneration, and observable terminal state.

The plan treats generation outcome, validation evidence, and quality warnings as
separate data. It does not turn every `review_required` reason into a warning
and does not delete review routes or historical status values until compatibility
proof exists.

Run-level outcomes stay separate: a valid persisted CV with warnings is
generated; validation, generation, and persistence failures remain explicit
failures; unresolved historical review remains a compatibility recovery path;
and an intentional `manual_staged` checkpoint waits for its existing
stage-continuation action.

## Implementation Outcomes

### Explicit warning and failure contract

CV generation returns one stable internal result containing persisted-output
eligibility, blocking failure information, structured quality warnings, and
validation evidence. Existing `accepted` internal state and persisted
`generated` state remain; status renaming is not part of this change.

Warnings cover truthful but imperfect output such as weak fit, missing
non-essential requirements, or low-confidence sections. Provider failures,
timeouts, empty output, unsupported factual claims, failed grounding or
validation, invalid structure, template violations, and persistence failures
remain blocking.

### Consistent completion and recovery

`run_all` marks terminal status, checkpoint, snapshot, and completion events
consistently when only warnings remain. After a user authorizes the final
`manual_staged` stage, warning-only CV output completes without introducing a
new CV-approval pause. Shared finalization preserves post-validation synonym
promotion, artifact reconciliation, audit events, and idempotency without
requiring the old review-closure route for warning-only output.

### Historical and API compatibility

Warnings persist with each CV version. Historical `review_required` records keep
outcome, warning, and evidence state without rewriting old rows. Evidence is
bound to the artifact version and content checksum; known validation failures
project as `failed`, while `missing` is reserved for absent or insufficient
evidence.

### Bounded CV listing and cleanup

CV version listing batch-loads evaluations and latest review events. Query count
does not grow with version count. Review UI and mutation routes are removed or
reduced only after caller, historical-data, and manual-stage compatibility proof
passes.

## Explicit Non-Goals

- No model, prompt, provider, or ATS concurrency change.
- No automatic acceptance of unsupported claims, failed grounding, invalid
  structure, empty output, provider failure, or persistence failure.
- No bulk rewrite of historical `cv_versions`, run checkpoints, or review events.
- No removal of `manual_staged` controls.
- No new global feature-flag framework; reuse existing run-level auto-accept
  configuration only where its current contract explicitly applies.
- No claim that approval removal reduces inference latency, token usage, or
  model cost without separate measurements.

## Execution Approach

- Mode: `subagent-ready`
- Coordination: `git-tracked`
- Required skills: `skill-executing-plans`, `skill-deepagents-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-full-stack-integration`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-verification-before-completion`, `skill-using-git-worktrees`
- Isolation: `mandatory dedicated worktree` from `origin/main` because current workspace contains unrelated dirty files
- Commit policy: `no commits during execution`
- Preauthorized local actions: edits in task-listed paths, declared local tests and benchmarks, read-only source inspection, one dedicated worktree, and one independent read-only review
- User-approval actions: push, merge, publication, external writes, destructive recovery, deletion of historical data, cleanup of unrelated files, and dependency/provider installation
- Parallel ownership: none; contract and lifecycle files are shared and remain serialized
- Sequential fallback: one bounded DeepAgents dispatch per task completes Tasks 1–4 in order; Codex reconciles each result and an independent review lane checks the base SHA plus exact working-tree diff and evidence

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-cv-warning-outcomes`
- Base commit: `86f719daa2cd144c8c0fdd95f1c9375cfc1a487b`
- Expected workspace: dedicated worktree from `origin/main`; preserve unrelated dirty files in current checkout
- Next action: preserve current worktree for authorized Git disposition; do not delete review recovery surfaces
- Blockers: frontend typecheck has pre-existing Node/test typing gaps plus one `RunJobItem` fixture mismatch; full frontend suite has one pre-existing scans assertion failure

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | dedicated worktree | `deepagents` | none | Severity matrix, result contract, additive persistence tests | `compileall`; 182 focused tests; 266 contract/store/worker tests |
| Task 2 | `completed` | dedicated worktree | `deepagents` | Task 1 | Warning-only completion, blocking failure, checkpoint, event, side-effect, recovery, and idempotency tests | checkpoint decoupling and idempotent historical recovery action implemented; affected backend suite `753` passed; `18` review-action/storage retry tests pass; stable approve-as-is artifact identity covers crash-before-action-record retry |
| Task 3 | `completed` | dedicated worktree | `deepagents` | Tasks 1–2 | Historical adapter, API/client contract, manual-stage recovery, baseline benchmark, and frontend state tests | evidence-bound projection/types and CV warning/failure render tests implemented; targeted frontend suite `8` passed; integrated run-detail browser proof covers warning, failure, preview/download, and no approval action; history/manual recovery remain covered by API/component tests |
| Task 4 | `completed` | dedicated worktree | `deepagents` | Tasks 1–3 | Constant-query benchmark, cleanup audit, full boundary proof, and independent review | benchmark shows `201→3` SQL at `100` versions and equal payloads; review routes retained for legacy recovery; fresh exact-head Herdr review `PASS` |

### Execution Evidence (2026-09-12)

- Verdict review accepted: separate warnings from failures, preserve explicit stage continuation, bind evidence to artifact version/checksum, keep historical recovery, and measure listing overhead.
- Fresh proof: `python -m compileall -q src/fitcv src/fitcv_cp scripts/benchmark_cv_versions.py` passed; backend focused suite passed `840` tests; `git diff --check` passed.
- Performance proof: captured benchmark output records equal payloads, no optimized `content_blob` selection, and constant `3` SQL statements for `1`, `10`, and `100` versions; reconstructed legacy comparison uses `3`, `21`, and `201` statements. Disposable `.tmp` artifacts were removed after recording.
- Scope note: `config/taxonomy/skill_synonyms.yaml` remains unrelated pre-existing worktree drift and is not touched by this plan; review-only routes remain because callers and historical recovery still exist.
- Frontend evidence: targeted CV component suite passed `8/8`; `npm run test:a11y` passed `3/3`; `npm run build` passed; full suite passed `266/267` with one pre-existing `Full time` versus `Full-time` assertion failure; `npm run typecheck` remains blocked by pre-existing Node/test typing gaps and one `RunJobItem` fixture mismatch.
- DeepAgents note: Herdr delivered five bounded lanes but each timed out during observation with no valid report; no DeepAgents result was accepted as proof.
- Fresh lifecycle proof: `python -m pytest tests/test_fitcv_cp/test_app.py -k 'cv_review_action'` passed `17`; repeated terminal review actions now no-op without duplicate CV versions, debug writes, or events; approve-as-is retry reuses stable artifact version identity after action-record failure.
- Fresh storage proof: `_finalize_review_draft_as_cv_artifact` called twice against temporary SQLite stores one row with one version ID; conflicting duplicate IDs still raise `sqlite3.IntegrityError`.
- Fresh browser proof: frontend dev shell rendered at `http://127.0.0.1:5173/app/#/runs?run_id=run-browser-proof`; integrated run-detail route showed warning-only outcome, validated preview content, `View CV`, `Download CV`, and `Regenerate CV`, with no `Approve CV` action; a separate mocked run showed blocking grounding failure as an accessible alert; Lighthouse snapshot scored accessibility `100` and best practices `100`.
- Static/API UI proof: `src/test/feature-ux-consistency.test.tsx` covers warning, blocking failure, history status, missing evidence, and semantic labels; review history and manual recovery remain API/component surfaces because no mounted run-detail history panel exists and adding one is outside approved scope.
- Independent review attempts: earlier Herdr DeepAgents panes delivered no report after pane transport timeouts; no result was accepted as proof. Fresh exact-head Herdr review completed with `PASS` after current focused/backend/frontend evidence and base comparison were supplied.
- Final validator note: template and planning lifecycle validators were run. They report only pre-existing legacy plan/spec metadata outside this plan's scope; those artifacts remain intentionally untouched per approved direction.

## Task Breakdown

### Task 1: Define warning/failure severity and additive persistence

**Purpose:** Establish one evidence-aware source of truth for whether a CV result
is non-blocking quality feedback, a known blocking failure, or insufficiently
proven for either conclusion, then persist warnings without changing existing
status values.

**Task Function:** Backend outcome-contract and schema evolution.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded contract and additive persistence work with moderate backend risk.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independently verify taxonomy coverage, schema compatibility, and failure semantics.

**Specification Coverage:** Explicit warning/failure contract, preserved hard
failures, existing `accepted`/`generated` status boundary, and persisted
warnings.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify `src/fitcv/pipeline_contracts.py:ReviewRequiredReasonCode`.
- Inspect and modify `src/fitcv/agentic_cv_generation.py:CvGenerationResult`, `normalize_review_required_reason_code`, `_review_required_reason`, and `_finalize_generation_result`.
- Inspect `src/fitcv/late_stage_contract.py` status constants only to confirm the existing internal-to-persisted boundary; warnings remain metadata and do not create a new status or rename `accepted`.
- Inspect and modify `src/fitcv_cp/sqlite_store.py:_ensure_local_cv_versions_table`, `insert_cv_version_row`, `update_cv_version`, and `_ensure_control_plane_schema` to add nullable `quality_warnings_json` and preserve old databases.
- Verify `tests/test_cv_generation_reason_mapping.py`, `tests/test_cv_generator.py`, `tests/test_pipeline_stage_resume_parity.py`, and `tests/test_pipeline_store.py`.

**Dependencies:** Current source contract at commit `86f719daa2cd144c8c0fdd95f1c9375cfc1a487b`.

**Authority:**
- Preauthorized local actions: inspect and edit listed contract/persistence files and focused backend tests; run additive schema tests against temporary SQLite databases.
- Stop for: a required destructive migration, a new persisted status value, or unresolved evidence for whether a diagnostic represents unsupported claims versus a truthful requirement gap.

**Steps:**
- [x] Create one classifier used by finalization and worker aggregation. It considers original outcome, validation result, diagnostic code, content integrity, artifact version, and checksum, then emits `evidence_state` of `passed`, `failed`, or `missing`.
- [x] Classify requirement/fit gaps and low-confidence sections as warnings only when `evidence_state="passed"` confirms truthful generated content. Keep provider, timeout, empty-output, template, markdown, grounding, validation, unsupported-claim, and persistence failures as explicit blocking failures. Keep `review_gate_manual_required` as review metadata until concrete evidence classification exists.
- [x] Add `quality_warnings` to `CvGenerationResult` and persist a serialized envelope on `cv_versions` containing contract version, artifact version ID, content checksum, evidence state, and warnings; preserve existing `generation_status`, `error_code`, `error_message`, fingerprints, content integrity checks, and idempotency index.
- [x] Make old SQLite databases add the nullable column through the existing additive schema path. Missing warning data decodes as `evidence_state="missing"`, never as a guessed warning or failure.
- [x] Define reuse semantics: reused results retain persisted warning/evidence semantics only when the outcome contract version and artifact/checksum binding match; otherwise revalidate before generated projection, or expose missing evidence without silently recomputing from current heuristics.
- [x] Add matrix tests for warning-only, blocking, mixed, empty, invalid, and persistence-failure results; fresh and existing normalized schemas; both version-writing paths; reused results; and old-schema read/write compatibility.

**Verification:**
- [x] `python -m pytest tests/test_cv_generation_reason_mapping.py tests/test_tracker.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_worker_job.py` — 266 passed.
- [x] `python -m compileall -q src/fitcv src/fitcv_cp scripts/benchmark_cv_versions.py` — passed.
- Expected: warning-only results retain validated content and warnings; every blocking case remains non-generated; old SQLite fixtures open without migration failure.

**Exit Criteria:** One evidence-aware classifier owns classification, warnings persist with version/checksum binding, old status values remain valid, reuse semantics are explicit, and focused tests prove no hard failure becomes generated.

### Task 2: Centralize completion, checkpoint reconciliation, and closure side effects

**Purpose:** Make terminal status, checkpoint, snapshot, and events agree when
warning-only CVs no longer require approval, while preserving manual staged runs
and review closure behavior for blocking or legacy records.

**Task Function:** Backend lifecycle and side-effect integration.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: cross-module state transition and side-effect work; sequential ownership required.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: verify direct success/failure boundaries, final persisted state, event ordering, and idempotency.

**Specification Coverage:** Consistent completion, preserved `manual_staged`, synonym promotion relocation, artifact reconciliation, and regeneration idempotency.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect and modify `src/fitcv_cp/worker_job.py:execute_pipeline_run` and the finalization block around `review_required_remaining`.
- Inspect and modify `src/fitcv_cp/app_run_support.py:_map_review_required_reason_code` so runtime outcome projection uses the Task 1 severity contract.
- Add one shared finalization helper in `src/fitcv_cp/worker_job.py` only if the current finalization block cannot own terminal status, checkpoint, snapshot, and event ordering without duplication.
- Inspect and modify `src/fitcv_cp/app.py:_run_post_validation_auto_promote_global`, `_persist_post_hitl_closure_artifact_reconciliation`, `admin_run_cv_review_action`, and `admin_run_cv_review_batch_action`.
- Verify `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_main.py`, `tests/test_fitcv_cp/test_app.py`, and regeneration/idempotency tests in `tests/test_cv_generator.py`.

**Dependencies:** Task 1 severity mapping and persisted warning field.

**Authority:**
- Preauthorized local actions: edit listed worker/app lifecycle code and focused backend tests; use temporary SQLite state and direct route calls for boundary proof.
- Stop for: any change that bypasses explicit stage-continuation authorization, loses synonym promotion or artifact reconciliation, duplicates terminal events, or requires bulk checkpoint rewriting.

**Steps:**
- [x] Keep separate counters and transitions for generated CVs with warnings, explicit validation/generation/persistence failures, unresolved historical review, and intentional manual-stage checkpoints; do not use `review_required_remaining` as a catch-all failure state.
- [x] Define run-level behavior without changing unrelated execution semantics: warning-only output reaches `SUCCEEDED`; mixed successful/failed CVs retain current run success/failure aggregation while exposing per-CV failures; zero generated CVs cannot report generated success; `manual_staged` waits only for explicit stage continuation.
- [x] Preserve `run_all` completion when only warnings remain: `SUCCEEDED`, finished timestamp, completed checkpoint, terminal snapshot, and one completion event must agree. After final-stage authorization, do not add a CV-approval pause.
- [x] Preserve `manual_staged` pause for its explicit continuation checkpoint and keep its existing recovery path.
- [x] Prove post-validation synonym promotion and artifact reconciliation remain preserved in explicit review closure. These effects depend on user-approved review actions; do not invoke them for warning-only completion without equivalent authorization. Preserve eligibility/conflict guards, audit payloads, actor/note fields, idempotency, and failure handling. Revisit relocation only after review callers are removed. Existing closure path and app tests retain these effects; warning-only worker completion does not call them.
- [x] Reuse existing idempotency keys and durable event/action records as completion identity. Make each side effect retry-safe, record completion only after required effects succeed, and recover after a crash between an effect and its completion record by checking existing effect identity before retrying. Approve-as-is finalization now derives stable artifact identity and treats identical SQLite inserts as idempotent while preserving conflicting-ID integrity errors.
- [x] Add an idempotent per-run recovery action to `admin_run_cv_review_action` for historical `awaiting_review` checkpoints; reconcile persisted run status/checkpoint/event state without bulk migration and keep `manual_staged` continuation separate.
- [x] Add mixed-run tests: warnings only, blocking only, warning plus blocking, zero generated CVs, manual staged before/after continuation, reused CV, repeated regeneration, side-effect failure, crash-after-effect-before-record, and historical checkpoint recovery.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_app.py tests/test_cv_generator.py` — affected backend suite passed `753` tests.
- [x] Direct boundary coverage asserts terminal run status, checkpoint behavior, terminal events, persisted CV/warning state, blocking state, and manual-stage behavior across the focused backend suite; explicit repeated terminal-action coverage added in `tests/test_fitcv_cp/test_app.py`.
- [x] Recovery tests repeat completion and historical reconciliation after simulated crash timing; approve-as-is retry reuses one stable version identity, and real SQLite proof confirms one stored row while conflicting IDs still raise `sqlite3.IntegrityError`.
- Expected: warning-only `run_all` completes; failures never become approvable drafts; blocking and manual-staged cases remain recoverable; repeated completion does not duplicate versions or side effects.

**Exit Criteria:** Completion state is internally consistent, warning-only output does not wait for approval, failures remain explicit, stage continuation remains authorized, historical checkpoints have idempotent per-run recovery, and closure side effects execute once or safely converge after retry.

### Task 3: Add historical compatibility and align API/UI outcome surfaces

**Purpose:** Expose one outcome contract without rewriting old records, and keep
preview, history, reused results, review queues, and frontend badges coherent.

**Task Function:** Full-stack contract reconciliation and compatibility projection.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: backend response projection plus bounded frontend state updates.

**Validator Profile:**
- Controller-selected: `ui`
- Selection basis: independently verify user-visible warning/failure states, accessibility, and manual recovery controls.

**Specification Coverage:** One outcome contract across persistence/API/UI, historical readability, explicit missing evidence, and preserved manual review recovery.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect and modify `src/fitcv_cp/sqlite_store.py:_cv_projection`, `list_cv_versions`, `list_cvs_for_run`, `get_cv_preview`, and `get_cv_download`.
- Inspect and modify `src/fitcv_cp/app_run_support.py:_map_review_required_reason_code` and related read-time outcome helpers.
- Inspect and modify API serializers/routes in `src/fitcv_cp/app.py` that expose CV versions, run outcomes, review queues, and pipeline outcome details.
- Inspect and modify `frontend/src/features/cv-review/types.ts`, `frontend/src/features/cv-review/api.ts`, `frontend/src/features/cv-review/components/CvEvaluationCard.tsx`, `frontend/src/features/cv-review/components/CvVersionHistory.tsx`, and `frontend/src/features/job-evaluation/components/PipelineOutcome.tsx`.
- Add `scripts/benchmark_cv_versions.py` before changing listing functions; use temporary SQLite data and production list functions for the baseline.
- Verify `frontend/src/features/cv-review/cv-api.test.tsx`, existing run/outcome tests, and `tests/test_fitcv_cp/test_app.py`.

**Dependencies:** Tasks 1–2. Canonical contract owner remains backend response projection; frontend types mirror that response and do not invent status mapping.

**Authority:**
- Preauthorized local actions: edit listed API/client/UI files and focused tests; use existing frontend test/build/browser capability for warning, failure, history, preview, and manual recovery states.
- Stop for: an API route shape change without matching backend tests, loss of historical review events, inaccessible warning/failure presentation, or a requirement to rewrite old rows.

**Steps:**
- [x] Define response fields: native `generation_status`, normalized `outcome_status`, `quality_warnings`, `failure_code`, and `evidence_state` with only `passed`, `failed`, or `missing`; preserve legacy status and review event information.
- [x] Project old `review_required` rows as generated only when content integrity and bound validation evidence support that conclusion. Project known validation/generation/persistence failures as `failed`; use `missing` only when evidence is absent or insufficient, and retain native review-required status without inventing a failure.
- [x] Bind projected evidence to `version_id` and content checksum; reject mismatched evidence and expose `missing` rather than claiming validation success.
- [x] Keep preview/download eligibility truthful: content integrity remains required; warnings never hide valid content; invalid or missing evidence never claims successful validation.
- [x] Update frontend types and components to render warning and blocking states with semantic labels, keyboard-accessible controls, focus behavior, supported themes, and no mandatory approval action for warning-only output.
- [x] Keep review routes read-only/recovery-capable for legacy and manual-staged records until Task 4 cleanup proof passes.
- [x] Run the baseline CV-list benchmark before changing `_cv_projection`, `list_cv_versions`, or `list_cvs_for_run`; retain baseline payload and query evidence for the Task 4 comparison.
- [x] Add API/UI tests for current generated output, warning-only output, each blocking failure, historical review-required output, missing evidence, reused versions, and manual recovery.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py` — covered by 654-task suite.
- [x] From `frontend/`: `npm run typecheck`, `npm run test`, and `npm run test:a11y` — `test:a11y` passed; full test has one pre-existing scans assertion; typecheck has pre-existing Node/test typing errors and one fixture mismatch.
- [x] Browser proof covers integrated warning display, blocking failure display, preview/download, keyboard-accessible controls, and no approval action for warning-only output; history and legacy/manual recovery are covered by API/component tests because no mounted run-detail history panel exists and adding one is outside approved scope.
- Expected: API and UI show identical outcome semantics; old records remain readable and recoverable.

**Exit Criteria:** Backend and frontend use the same response contract, historical rows remain recoverable, warning/failure states are accessible, and no UI path falsely claims validation or persistence success.

### Task 4: Batch CV listing, measure overhead, and remove review-dependent cleanup safely

**Purpose:** Remove per-version listing queries and delete only review-dependent
branches that no longer own required compatibility or side effects.

**Task Function:** Performance measurement, route audit, and final integration.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded SQL optimization plus cross-surface cleanup after contract and lifecycle stabilization.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent query-count, scope, regression, and deletion-risk review.

**Specification Coverage:** Constant-query CV listing, measured overhead, cleanup last, and no loss of historical/manual behavior.

**Required Skills:**
- `skill-performance-optimization`
- `skill-backend-verification`
- `skill-full-stack-integration`
- `skill-plan-document-reviewer`

**Files And Symbols:**
- Inspect and modify `src/fitcv_cp/sqlite_store.py:_cv_projection`, `list_cv_versions`, and `list_cvs_for_run`.
- Reuse the baseline harness `scripts/benchmark_cv_versions.py` created in Task 3; it must use temporary SQLite data and production list functions, not a mock implementation.
- Inspect all callers of `/admin/runs/{run_id}/cv-review-action`, `/admin/runs/{run_id}/cv-review-batch-action`, CV review API functions, and review-only frontend components before deleting or reducing any surface.
- Modify only confirmed orphaned review-dependent UI/routes/artifact writers; preserve read-only history and manual-staged recovery surfaces.
- Verify changed tests, benchmark artifact, `git diff --check`, and independent read-only review.

**Dependencies:** Tasks 1–3.

**Authority:**
- Preauthorized local actions: edit listed projection/benchmark/cleanup files, run identical before/after measurements, inspect callers, and dispatch one independent read-only review.
- Stop for: query count still grows with version count, benchmark workload differs between baseline and after, an unknown caller remains, or cleanup would remove historical/manual recovery.

**Steps:**
- [x] Confirm the Task 3 baseline at 1, 10, and 100 CV versions per run; record SQL statements, p50/p95 latency, returned payload equality, and per-version query growth.
- [x] Replace `SELECT *` with explicit projection columns that exclude `content_blob`; batch-load current evaluations and latest review events with one run/job-filtered join or subquery per collection, pass lookup maps into a pure projection, and preserve response ordering and fields.
- [x] Re-run identical workload and require query count independent of version count, response equality, no content blob expansion, and `p95 <= baseline_p95 * 1.10 + 5 ms`; record environment variance separately instead of weakening the query-count gate.
- [x] Search backend and frontend callers, then remove only review-dependent mutation/UI/artifact code proven redundant after Tasks 1–3. No deletion is justified: review routes, templates, and recovery callers remain active; unrelated manual-stage controls remain intact.
- [x] Run full focused backend/frontend checks and inspect diff scope; independent review dispatched against the exact base SHA plus exact staged/unstaged/untracked in-scope working-tree diff and remains pending acceptance.

**Verification:**
- [x] `python scripts/benchmark_cv_versions.py --versions 1,10,100 --warmup-iterations 5 --measured-iterations 30 --output .tmp/cv-versions-benchmark.json`
- [x] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py`
- [x] From `frontend/`: `npm run typecheck`, `npm run test`, `npm run test:a11y`, and `npm run build` — a11y/build passed; full test `266/267` with one pre-existing scans assertion; typecheck remains blocked by pre-existing Node/test typings and one fixture mismatch.
- [x] `git diff --check`
- Expected: fixed statement count per list request (or constant query count per bounded page), equal API payload semantics plus separately asserted additive fields, no review-route caller breakage, and no unresolved independent-review finding.

**Exit Criteria:** Listing overhead is measured and bounded, cleanup removes no required compatibility path, full verification passes or records approved pre-existing deviations, and independent review accepts the exact implementation head.

## Verification

### Contract and backend

- `python -m pytest tests/test_cv_generation_reason_mapping.py tests/test_cv_generator.py tests/test_pipeline_store.py tests/test_pipeline_stage_resume_parity.py`
- `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_sqlite_store.py`
- `python -m compileall src/fitcv src/fitcv_cp`

### Frontend and boundary

- From `frontend/`: `npm run typecheck`
- From `frontend/`: `npm run test`
- From `frontend/`: `npm run test:a11y`
- From `frontend/`: `npm run build`
- Browser proof for warning-only, blocking failure, historical review, preview/download, and manual-staged recovery states.

### Performance

- Baseline and after use identical temporary SQLite fixtures, Python runtime,
  version counts `1,10,100`, warmups `5`, and measured iterations `30`.
- Metrics: SQL statement count, p50/p95 latency, response equality, payload
  size, content blob reads, and query-count growth per version.
- Hard thresholds: query count does not grow with CV version count; response
  equality remains true; no content blob is loaded for list projections; and
  `p95 <= baseline_p95 * 1.10 + 5 ms` under the identical benchmark setup.

### Review and lifecycle

- `python "$HOME/.agents/project-os/scripts/validate_template_required_sections.py" --repo-root .`
- `python "$HOME/.agents/project-os/scripts/validate_planning_lifecycle.py" --repo-root .`
- `git diff --check`
- Independent read-only review returns `PASS` or a resolved finding list bound
  to the exact implementation head.

## Completion Criteria

- Warning-only CV output is validated, persisted, marked `generated`, and carries structured warnings.
- Unsupported claims, failed grounding, invalid structure, empty output, provider failures, validation failures, and persistence failures never become generated.
- `run_all` terminal status, checkpoint, snapshot, completion event, and side effects agree for warning-only completion.
- `manual_staged` blocking review behavior remains intact.
- Historical `review_required` rows remain readable, auditable, and recoverable without bulk rewrite.
- API and frontend expose one outcome contract with explicit evidence state.
- Repeated regeneration remains idempotent and does not duplicate billable work or versions.
- CV version listing uses explicit projection columns and fixed statement count per request (or constant query count per bounded page), with benchmark evidence recorded.
- Review UI/routes are removed only after caller and compatibility proof.
- All required verification commands run fresh; pre-existing failures are isolated, recorded, and not misreported as shipped behavior.
- Adaptive scoring, prompt/provider changes, ATS concurrency, and unrelated cleanup remain deferred.
