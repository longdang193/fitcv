---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-trustworthy-final-cv-path
targets:
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/cv_generator.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/run_artifact_contracts.py
  - scripts/benchmark_cv_efficiency.py
  - scripts/verify_fitcv_acceptance.py
  - scripts/render_acceptance_state.py
  - tests/test_agentic_cv_generation.py
  - tests/test_cv_generator.py
  - tests/test_cv_render_acceptance.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_benchmark_cv_efficiency.py
  - tests/test_fitcv_cp/test_acceptance_verifier.py
  - docs/superpowers/evidence/
---

# FitCV Trustworthy Final CV Path

## Goal

Create one lossless, low-cost path from verified candidate evidence to a final
accepted one-page CV. Fresh generation, safe reuse, overflow trim, HITL
approval, persistence, and reporting must share one final-artifact contract.
Overflow handling must preserve every uniquely supported required/high-priority
requirement. Unknown or ambiguous provenance must fail closed to review rather
than silently weaken relevance.

Keep the change narrow:

- Do not add host provenance IDs to the LLM response schema.
- Do not reopen retrieval, prompt architecture, routing, vector search, or
  agent topology.
- Keep P1-C deferred and P2 frozen.
- Treat the failed first-pass experiment as rejected completed evidence, not as
  an acceptance blocker.

## Implementation Outcomes

### One final-artifact acceptance contract

All accepted paths produce and persist one equivalent proof set: exact content
identity, generation/input identity, template and render configuration identity,
renderer contract version, page count, page-fit status, render acceptance,
artifact checksum, trace lineage, and run-job lineage. A cached result is
accepted only after local content validation and exact render-proof matching.
Stale proof triggers local native rerender without another provider call.

### Host-managed evidence-aware trim

Add `render_item_provenance_v1` between `cv_content_plan_v1` and normalized CV
content. It contains deterministic item identity, section, evidence IDs,
supported requirement IDs, requirement priority, and protection status. The
LLM schema remains production-shaped. Ambiguous joins stay protected. Trim
considers only removable/value-safe items, preserves requirement support before
and after trim, reruns exact validation, and natively rerenders once.

### One lossless reporting path

Benchmark projection, acceptance verification, and generated scorecard consume
the same normalized accepted-artifact events. Current-contract cohorts exclude
legacy or incomplete page-fit records. Reports expose page-fit coverage and
success separately from first-pass acceptance, calls, tokens, regenerations,
reuse, latency, questions, and human actions.

### Measured cost optimization

After correctness closure, classify retry causes and optimize only the dominant
measured cause. Load `FITCV_LLM_API_KEY` from repository-local `.env` through
existing runtime configuration when running the bounded experiment; never print,
persist, commit, or include the secret in evidence. Measure safe-reuse hits and
stage p50/p95 only from current-contract persisted timings.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-plan-document-reviewer`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve existing unrelated untracked files and local data
- Commit policy: `no commits during execution`; commit or publish only after fresh verification and explicit Git disposition
- Preauthorized local actions: inspect source/history, edit plan-listed code/tests/docs/evidence, read `.env` through existing configuration without printing secrets, run declared local checks, and regenerate declared local outputs
- User-approval actions: push, merge, publication, credential changes, dependency installation, destructive cleanup, discard, and acceptance-status promotion
- Parallel ownership: none; provenance, trim, finalization, and reporting share contracts and execute serially
- Sequential fallback: execute Tasks 1–7 in order in one controller-owned workspace

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-p0-p1-closure-contract`
- Base commit: `d7e7047e`
- Expected workspace: dirty; preserve existing untracked `.tmp/`, `.venv/`, scratch files, local datasets, and prior evidence/plans
- Next action: hand off verified branch to explicit Git disposition
- Blockers: P1-C and P2 remain intentional deferrals; no implementation blocker remains

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `complete` | current | `codex` | none | focused regressions and root-cause proof | `3067 passed, 8 skipped`; production-shaped schema and caller trace recorded |
| Task 2 | `complete` | current | `codex` | Task 1 | production-shaped provenance sidecar | `render_item_provenance_v1` tests pass |
| Task 3 | `complete` | current | `codex` | Task 2 | evidence-aware trim and coverage preservation | trim/protected-support/native-render tests pass |
| Task 4 | `complete` | current | `codex` | Tasks 2–3 | all final-artifact paths converge | fresh/reuse/HITL/persistence contract tests pass |
| Task 5 | `complete` | current | `codex` | Task 4 | lossless current-contract report/verifier | current-contract reconciliation evidence; verifier passed |
| Task 6 | `complete` | current | `codex` | Task 5 | bounded reuse and retry-cost evidence | first-pass promotion rejected; current re-projection is fail-closed |
| Task 7 | `complete` | current | `codex` | Tasks 1–6 | fresh final verification and reconciliation | full suite, verifier, generated state, and diff checks pass |

## Task Breakdown

### Task 1: Reproduce defect and freeze contract baseline

**Purpose:** Confirm verdict root cause against current source, trace shared
callers, and add focused production-shaped failing proof before behavior edits.

**Task Function:** systematic root-cause tracing and regression design.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: contract-sensitive backend tracing with lowest reliable reasoning depth.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent review of root cause, callers, and regression scope.

**Specification Coverage:** Production schemas strip unsupported project/language metadata; unique requirement evidence must survive overflow; all accepted paths need exact final-render proof.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_generation.py:build_cv_content_plan`, `_reusable_result_or_none`, `_build_result`, `generate_from_analysis`.
- Inspect: `src/fitcv/cv_generator.py:_normalize_projects_section`, `_normalize_languages_section`, `trim_structured_cv_for_page_fit`, `final_artifact_acceptance_passes`, `render_proof_matches`, `render_cv_native_acceptance`.
- Inspect: `src/fitcv/pipeline.py`, `src/fitcv_cp/app.py`, `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/run_artifact_contracts.py` shared callers and persisted fields.
- Modify: focused tests in `tests/test_agentic_cv_generation.py`, `tests/test_cv_generator.py`, `tests/test_cv_render_acceptance.py`, `tests/test_pipeline.py`, and control-plane contract tests.

**Dependencies:** Verdict attachment and current branch HEAD `d7e7047e` are authoritative; existing unrelated untracked files remain untouched.

**Authority:**
- Preauthorized local actions: record status/HEAD, inspect history/source/callers, run baseline tests, and add focused failing tests in listed test files.
- Stop for: unexpected tracked changes, missing render boundary, inability to reproduce the schema/provenance defect, or any P0 contract change.

**Steps:**
- [x] Record `git status --short --branch`, HEAD, focused baseline, and current acceptance-state status.
- [x] Trace fresh generation, reuse, trim, HITL, persistence, and report projection callers; assign one owner per final-artifact field.
- [x] Add production-shaped fixtures with only `name/context/bullets` projects and `name/level` languages; prove unsupported metadata cannot be the protection mechanism.
- [x] Add failing cases for unique requirement evidence loss, ambiguous provenance, stale render proof, and incomplete aggregate page-fit records.

**Verification:**
- [x] `python -m pytest -q tests/test_cv_generator.py tests/test_cv_render_acceptance.py tests/test_pipeline.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- Expected: baseline recorded; new tests fail only on intended contract gaps; no historical evidence is rewritten.

**Exit Criteria:** Root cause, shared callers, field owners, and focused failing proof are recorded.

### Task 2: Build host-managed rendered-item provenance

**Purpose:** Preserve evidence and requirement ownership without changing the
LLM output schema.

**Task Function:** deterministic provenance mapping at the host/content-plan boundary.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: narrow data-contract change with deterministic identity requirements.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent review of identity stability and fail-closed behavior.

**Specification Coverage:** Add `render_item_provenance_v1` between verified evidence/content plan and normalized generated CV; ambiguous mapping protects item.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv/agentic_cv_generation.py:build_cv_content_plan` and adjacent host-side provenance helpers.
- Modify: `src/fitcv/pipeline.py` generation/debug payload propagation.
- Verify: `tests/test_agentic_cv_generation.py`, `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_worker_job.py`.

**Dependencies:** Task 1 field ownership and production-shaped fixtures.

**Authority:**
- Preauthorized local actions: add host-managed provenance fields, deterministic canonicalization, propagation, and focused tests in listed files.
- Stop for: adding provenance fields to the LLM schema, nondeterministic item IDs, or any ambiguous join treated as removable.

**Steps:**
- [x] Define sidecar version and fields: `item_id`, `section`, `canonical_item_key`, `evidence_ids`, `supported_requirement_ids`, `requirement_priority`, `protected`.
- [x] Derive project identity from canonical project name plus normalized content; derive language identity from canonicalized language name.
- [x] Join generated items to existing candidate/evidence and `requirement_coverage` data; mark ambiguous, missing, or conflicting joins protected.
- [x] Carry sidecar through fresh, reused, trimmed, HITL, and persisted generation payloads without making it part of provider output validation.

**Verification:**
- [x] `python -m pytest -q tests/test_agentic_cv_generation.py tests/test_pipeline.py tests/test_fitcv_cp/test_worker_job.py`
- Expected: production-shaped output has no unsupported metadata, sidecar identity is deterministic, and ambiguous mapping remains protected.

**Exit Criteria:** Every normalized trim candidate has host provenance or an explicit fail-closed protected state.

### Task 3: Make trim evidence-aware and coverage-preserving

**Purpose:** Produce one-page output without removing unique relevance evidence.

**Task Function:** bounded deterministic trim and post-trim coverage gate.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: behavior change affecting accepted artifacts; requires regression proof.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent trim/value and one-page acceptance review.

**Specification Coverage:** Trim only removable/value-safe items; preserve requirement support before and after; fail closed to `review_required` when overflow or grounding remains.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `src/fitcv/cv_generator.py:trim_structured_cv_for_page_fit`, `final_artifact_acceptance_passes`, `render_proof_matches`, `render_cv_native_acceptance`.
- Modify: adjacent normalization/coverage helpers only where required to consume sidecar, not provider schema metadata.
- Verify: `tests/test_cv_generator.py`, `tests/test_cv_render_acceptance.py`, `tests/test_pipeline.py`.

**Dependencies:** Task 2 sidecar and Task 1 failing trim fixtures.

**Authority:**
- Preauthorized local actions: edit trim/coverage/acceptance logic and focused tests; run native render checks on local fixtures.
- Stop for: removing uniquely supported requirements, accepting unknown provenance, unbounded repair loops, or changing provider response schema.

**Steps:**
- [x] Replace generated-item ID checks with sidecar/value protection; protect required/high-priority unique support and all unknown/ambiguous items.
- [x] Rank only eligible content by deterministic space saved versus marginal requirement value; prefer redundant optional bullets before whole items/sections.
- [x] Snapshot protected requirement support before trim and require exact support equality after trim.
- [x] On coverage loss, failed validation, or irreducible overflow, return `review_required`; otherwise rerun validation and native render once.

**Verification:**
- [x] `python -m pytest -q tests/test_cv_generator.py tests/test_cv_render_acceptance.py tests/test_pipeline.py -k "trim or page_fit or render or requirement"`
- Expected: one-page accepted output preserves protected support; production-shaped overflow never relies on stripped metadata; unsafe overflow fails closed.

**Exit Criteria:** Trim cannot silently trade requirement relevance for page count, and successful trim carries fresh exact proof for trimmed content.

### Task 4: Converge fresh, reuse, HITL, and persistence on final acceptance

**Purpose:** Make every accepted CV genuinely final and one-page through one
shared final-artifact decision path.

**Task Function:** finalization and lifecycle integration.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: cross-module backend contract integration with persistence risk.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent lifecycle and boundary verification.

**Specification Coverage:** Accepted means exact content validated, natively rendered, page count `1`, page-fit `pass`, proof matched, and lineage complete.

**Required Skills:** `skill-full-stack-integration`, `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv/agentic_cv_generation.py:_reusable_result_or_none`, `_build_result`, `generate_from_analysis`.
- Modify: `src/fitcv/pipeline.py`, `src/fitcv_cp/app.py:_finalize_review_draft_as_cv_artifact`, `src/fitcv_cp/worker_job.py` accepted-artifact/debug payloads.
- Modify: `src/fitcv_cp/run_artifact_contracts.py:accepted_cv_artifact_event_v1` only to preserve one canonical accepted shape.
- Verify: `tests/test_pipeline.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_cv_render_acceptance.py`.

**Dependencies:** Tasks 2–3 complete; current persisted field names remain authoritative.

**Authority:**
- Preauthorized local actions: unify finalization fields, reuse proof checks, local rerender fallback, persistence propagation, and lifecycle tests.
- Stop for: provider calls on reusable exact proof, acceptance without `page_count == 1`, render-proof/content mismatch, or duplicate field owners.

**Steps:**
- [x] Define one render-proof payload keyed by content SHA-256, template SHA-256, render-config fingerprint, renderer contract/version, page count, page-fit status, and artifact checksum.
- [x] Require local validation plus exact proof match for reuse; absent/stale proof triggers local rerender only.
- [x] Route fresh, reused, trimmed, HITL-approved, and persisted artifacts through the same final-artifact acceptance helper and event shape.
- [x] Preserve trace/run-job lineage and sidecar provenance through accepted-artifact persistence and reporting.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline.py tests/test_cv_render_acceptance.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Expected: fresh, reuse-hit, stale-proof rerender, trim, HITL, and persistence cases converge on identical acceptance fields and call counts.

**Exit Criteria:** No path can report accepted while lacking exact one-page native render proof or complete lineage.

### Task 5: Make reporting one lossless current-contract path

**Purpose:** Ensure every efficiency and acceptance number derives from the same
complete accepted-artifact event contract.

**Task Function:** reporting contract and cohort integrity.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: data-contract change with historical evidence boundary risk.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent aggregate/verifier consistency review.

**Specification Coverage:** Separate current-contract evidence from legacy history; expose page-fit coverage/success, first-pass acceptance, calls/tokens/regenerations, reuse, latency, human effort, and explicit deferrals.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv_cp/run_artifact_contracts.py:collect_normalized_generation_traces`, `build_accepted_cv_effort_projection`, and accepted event normalization.
- Modify: `scripts/benchmark_cv_efficiency.py`, `scripts/verify_fitcv_acceptance.py`, `scripts/render_acceptance_state.py`.
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_benchmark_cv_efficiency.py`, `tests/test_fitcv_cp/test_acceptance_verifier.py`, `tests/test_acceptance_state.py`.
- Record: derived evidence under `docs/superpowers/evidence/`; do not mutate historical records to add missing facts.

**Dependencies:** Task 4 canonical accepted event and current persisted field names.

**Authority:**
- Preauthorized local actions: edit projections/verifier/scorecard logic, add contract fixtures, and write derived local evidence without secrets.
- Stop for: synthesizing missing page-fit facts, mixing legacy and current cohorts, manual metric duplication, or acceptance promotion from incomplete data.

**Steps:**
- [x] Define current-contract cohort eligibility from required fields and contract versions; retain legacy data as audit-only.
- [x] Project one normalized row per accepted artifact/run with complete page-fit, attribution, cost, timing, retry, reuse, question, and human-action fields.
- [x] Derive scorecard metrics from normalized rows, including page-fit coverage and success separately from first-pass acceptance.
- [x] Make verifier fail closed on incomplete or conflicting reporting and explicitly label rejected experiment evidence, P1-C deferred, and P2 frozen.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_acceptance_verifier.py tests/test_acceptance_state.py`
- Expected: benchmark and verifier agree on identical rows, no metric invents unavailable facts, and historical data remains unchanged.

**Exit Criteria:** One lossless reporting path produces reproducible, current-contract acceptance and efficiency numbers.

### Task 6: Optimize only measured cost and safe reuse

**Purpose:** Lower provider calls and latency without sacrificing correctness or
reopening architecture.

**Task Function:** bounded performance experiment and reuse measurement.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: measured optimization after correctness gates; lowest reliable performance reasoning depth.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent experiment reproducibility and regression review.

**Specification Coverage:** One provider call plus zero/one narrow correction target; safe reuse is primary optimization; stage p50/p95 follows current-contract evidence.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`

**Files And Symbols:**
- Modify only if measurement exposes a dominant deterministic cause: `src/fitcv/agentic_cv_generation.py`, `src/fitcv/cv_generator.py`, or the owning reporting script.
- Use: `scripts/benchmark_cv_efficiency.py`, `scripts/verify_fitcv_acceptance.py`.
- Fixture: `data/linkedin-2026-10-02-22-52-15.json`; record SHA-256 before both arms and stop if changed.
- Evidence: `docs/superpowers/evidence/` current-contract experiment record.

**Dependencies:** Task 5 current-contract reporting passes; Tasks 2–4 correctness gates pass.

**Authority:**
- Preauthorized local actions: read `FITCV_LLM_API_KEY` through existing `.env` configuration, run bounded incumbent/candidate cohorts, measure reuse and stage timings, and write secret-free evidence.
- Stop for: missing key, changed fixture/model/settings, P0/P1 correctness regression, reporting conflict, or need for broad prompt/retrieval redesign.

**Steps:**
- [x] Record fixture hash, code revision, model/provider/settings, workload order, contract versions, and environment metadata for both arms.
- [x] Measure unchanged-input reuse hits, exact proof reuse, local rerenders, provider calls avoided, tokens avoided, reuse p50/p95, and resolution reuse.
- [x] Classify every non-first-pass outcome by provider/transient, schema/heading, missing section, overflow, or repeated deterministic defect.
- [x] Optimize only the dominant measured cost; keep narrow correction bounded and record incumbent retention when no benefit appears.
- [x] Derive stage p50/p95 only from persisted current-contract timing fields.

**Verification:**
- [x] `python scripts/benchmark_cv_efficiency.py --database <current-contract database> --output-json <evidence>.json --output-markdown <evidence>.md`
- [x] `python scripts/verify_fitcv_acceptance.py`
- Expected: repeatable current-contract results; failed first-pass experiment remains rejected if not improved; `.env` secret absent from stdout, logs, evidence, artifacts, and diff.

**Exit Criteria:** Optimization has measured benefit or a recorded rejection; no correctness gate is weakened and no architecture expansion occurs.

## Execution Reconciliation

- Root cause: production normalization strips project `evidence_id`/`claim_id`/`required` and language evidence metadata; trim protection therefore belongs in a host-managed sidecar, not provider output.
- Shared owners patched: `agentic_cv_generation.py` owns final-artifact acceptance and provenance; `cv_generator.py` owns native render/proof/trim; `app.py` owns HITL finalization; `worker_job.py` owns debug propagation; `run_artifact_contracts.py` owns normalized reporting rows.
- HITL approval now rerenders exact draft content and rejects missing, stale, non-native, or non-one-page proof before persistence.
- Reporting no longer treats content-plan page-fit claims as verified. Legacy/incomplete proof remains audit-visible; verified coverage and success stay separate.
- Historical first-pass experiment remains rejected for promotion. Current-contract re-projection is recorded in `docs/superpowers/evidence/2026-10-03-fitcv-current-contract-reconciliation.md` and `.json`.
- P1-C remains deferred. P2 remains frozen. No provider, retrieval, prompt, routing, or model architecture change made.
- Fresh proof: `3067 passed, 8 skipped`; `python scripts/verify_fitcv_acceptance.py` passed; acceptance-state render passed; `git diff --check` passed.

### Task 7: Final verification and repository reconciliation

**Purpose:** Prove implementation completeness, reconcile generated surfaces, and
leave deferrals explicit.

**Task Function:** final acceptance verification and change-control review.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: fresh full-scope verification and repository-state reconciliation.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent final verification before any branch disposition.

**Specification Coverage:** All outcomes, focused regressions, backend boundary proof, current-contract evidence, safe reuse, and explicit P1-C/P2 deferrals.

**Required Skills:** `skill-verification-before-completion`, `skill-backend-verification`, `skill-plan-document-reviewer`

**Files And Symbols:** Verify all Task 1–6 targets, `config/acceptance_state.yaml`, `artifacts/acceptance_state.json`, evidence outputs, and plan file.

**Dependencies:** Tasks 1–6 complete or explicitly blocked with evidence.

**Authority:**
- Preauthorized local actions: run fresh verification, regenerate declared deterministic outputs, inspect diff, and record deviations/deferrals.
- Stop for: unresolved required failure, stale generated output, leaked secret, unrecorded scope change, false acceptance claim, or unrelated tracked modification.

**Steps:**
- [x] Run focused regression suites, backend boundary checks, benchmark/verifier checks, and full applicable test suite.
- [x] Rebuild acceptance state from canonical source and verify deterministic output.
- [x] Run `git diff --check`; inspect tracked diff; confirm preserved untracked files remain untouched.
- [x] Confirm P1-A/P1-B status uses current-contract evidence, optimization status is separate, P1-C is deferred, and P2 is frozen.
- [x] Record final commands, evidence paths, deviations, rollback/stop conditions, and next action in coordination state.

**Verification:**
- [x] `python -m pytest -q`
- [x] `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json`
- [x] `python scripts/verify_fitcv_acceptance.py`
- [x] `git diff --check`
- Expected: fresh tests pass, generated state is deterministic, verifier is consistent, whitespace is clean, and no required contract remains unverified.

**Exit Criteria:** `skill-verification-before-completion` returns `verified`; only then may plan status move from `proposed` to `completed`.

## Verification

Final artifact proof must show:

- fresh generation, exact reuse, stale-proof local rerender, trim, HITL approval,
  and persistence converge on one accepted final-artifact contract;
- every accepted artifact has fresh native one-page proof bound to exact content;
- production-shaped project/language output cannot lose unique requirement
  evidence through schema-stripped metadata assumptions;
- trim preserves protected requirement support before and after, and unsafe
  overflow fails closed to `review_required`;
- accepted-artifact projections, benchmark, verifier, and scorecard consume one
  lossless current-contract path;
- first-pass/retry/reuse/cost/latency numbers are reproducible and secret-free;
- P1-C remains deferred and P2 remains frozen.

## Completion Criteria

The plan is ready for completion verification when:

1. every implementation outcome is satisfied;
2. every task and task-local verification item is complete;
3. root-cause fixes, shared callers, deviations, blockers, and deferrals are recorded;
4. source, tests, reporting scripts, generated state, evidence, and documentation reconcile with repository truth;
5. fresh final verification commands are identified and runnable.

The plan may move to `completed` only after `skill-verification-before-completion`
confirms no unresolved required task, failed required check, stale status, or
unrecorded scope deviation.
