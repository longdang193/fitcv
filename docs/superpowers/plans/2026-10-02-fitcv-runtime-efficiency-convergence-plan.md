---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-runtime-efficiency-convergence
targets:
  - src/fitcv_cp/run_artifact_contracts.py
  - scripts/benchmark_cv_efficiency.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/evidence.py
  - scripts/verify_fitcv_acceptance.py
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_benchmark_cv_efficiency.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_evidence.py
  - tests/test_acceptance_state.py
  - docs/superpowers/evidence/
---

# FitCV Runtime Efficiency Convergence

## Goal

Reduce provider calls, regenerations, token spend, and end-to-end wall time while preserving FitCV's stable correctness architecture: P0-B/P0-C gates, unsupported-claim prevention, one-page render acceptance, compiler behavior, artifact lineage, and canonical trace identity. Keep P1-C and P2 deferred.

## Verdict Review

- P0-A: closed as a rejected negative experiment; keep incumbent retrieval.
- P0-B: closed only within frozen evaluated scope; do not widen its claim.
- P0-C: closed within reviewed qualifier, domain, degree, and related-field regression scope.
- P1-A: maintenance-only; compiler and one-page render gates remain contract.
- P1-B: lifecycle implementation and functional acceptance passed; measurement remains incomplete until attribution and workload semantics are corrected.
- P1-C: deferred; no request-path market-gap feature enters this plan.
- P2: deferred; no new retrieval or agent architecture enters this plan.

## Implementation Outcomes

### Conflict-safe attribution

`match_trace_record()` uses exact canonical `trace_id` matching. Legacy matching requires the same `run_id`, agreement across every shared strong identity field, and explicit conflict or ambiguity outcomes. `job_url` remains a last-resort legacy field only when no stronger identity is available. A contradictory strong identifier never falls through to a weaker match.

### Correct workload accounting

The efficiency benchmark includes failed and cancelled runs when measurable generation work exists. It keeps accepted-artifact attribution separate from total-workload efficiency. Accepted-artifact cost remains available for lineage analysis; total calls, tokens, regenerations, validation failures, and elapsed work remain visible even when zero CVs are accepted. Per-accepted-CV values are `null` when the denominator or attribution is incomplete.

### Actionable efficiency yield

Reports distinguish generation elapsed time from end-to-end run wall time and expose first-pass acceptance, provider calls per accepted CV, tokens per accepted CV, regenerations per accepted CV, validation failures per accepted CV, retry success, retry failure, and attribution completeness.

### Measured first-pass improvement

One bounded experiment targets `missing_or_shallow_sections`: derive deterministic required-section targets from already approved evidence in `cv_content_plan_v1` and carry them through the existing generation prompt contract. The experiment changes neither retrieval truth nor global retry policy. It is retained only when same-workload first-pass acceptance improves and all correctness gates remain unchanged.

### Lazy diagnostics and operational SSOT

Production evidence retrieval computes stage counts without constructing or sorting full pair lists. Full pair lists remain available only under diagnostics. The benchmark produces cumulative JSON and Markdown operational evidence with commit, workload, acceptance, yield, cost, latency, and attribution fields. Historical evidence remains immutable audit material.

### Explicit deferrals

P1-C remains offline-only future work based on imported requirements and verified candidate evidence. No ESCO request-path dependency, vector database, GraphRAG layer, reranker, LLM verifier, routing service, new agent, global `top_k` expansion, or broad retry suppression is added.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-performance-optimization`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-plan-document-reviewer`, `skill-executing-plans`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit task-listed source, tests, acceptance metadata, generated evidence, and docs; run declared local tests, benchmark, verifier, and render commands; preserve unrelated untracked files
- User-approval actions: push, merge, publication, provider or dependency installation, destructive recovery, discard, cleanup of pre-existing files, and repository disposition
- Parallel ownership: `none`; trace contracts, benchmark semantics, generation planning, and evidence retrieval remain serialized
- Sequential fallback: execute Tasks 1–10 in order; stop at the first failed correctness gate or missing required evidence

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-p0-p1-closure-contract`
- Base commit: `7fb1f0e495171f4d10d424aba3b30c4c1abb10d8`
- Expected workspace: current branch with unrelated untracked scratch files preserved and untouched
- Next action: hand off verified branch to explicitly authorized Git disposition
- Blockers: none

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | trace contract tests | `28 passed`; conflict regression added |
| Task 2 | `completed` | current | `codex` | Task 1 | benchmark selection tests | `5 passed`; failed/cancelled measurable runs included |
| Task 3 | `completed` | current | `codex` | Task 2 | metric-shape and zero-acceptance tests | `6 passed`; two cost families labeled |
| Task 4 | `completed` | current | `codex` | Task 3 | elapsed-time tests | `34 passed`; generation and wall clocks separated |
| Task 5 | `completed` | current | `codex` | Task 4 | yield metric tests | `7 passed`; first-pass and retry outcomes reported |
| Task 6 | `completed` | current | `codex` | Task 5 | attributed workload report | baseline `complete` for 2 fully attributed runs; broader sample incomplete |
| Task 7 | `completed` | current | `codex` | Task 6 | same-workload acceptance and correctness comparison | rejected; no candidate retained without broader provider-backed workload |
| Task 8 | `completed` | current | `codex` | Task 7 | diagnostics parity tests | `130 passed`; production pair sorting removed |
| Task 9 | `completed` | current | `codex` | Task 8 | cumulative SSOT generation and validation | `20 passed`; acceptance state and verifier reconciled |
| Task 10 | `completed` | current | `codex` | Task 9 | fresh final verification | `verified`; PR review fixes covered validation-failed yield and generation/artifact clock separation; full proof passed |

## Task Breakdown

### Task 1: Make legacy trace attribution conflict-aware

**Purpose:** Prevent silently attaching provider effort to the wrong accepted artifact.

**Task Function:** Repair shared lineage matching at its single projection boundary.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: shared contract logic is high-impact and requires source-first controller ownership.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused regression suite provides independent behavioral proof.

**Specification Coverage:** Canonical `trace_id` exact match; legacy same-`run_id` scope; agreement across all shared strong identifiers; explicit conflict and ambiguity; URL last resort.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:_lineage_matches`, `src/fitcv_cp/run_artifact_contracts.py:match_trace_record`, `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`
- Modify: `src/fitcv_cp/run_artifact_contracts.py:match_trace_record`; `tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`

**Dependencies:** Current canonical trace contract and existing run-scoped lineage tests.

**Authority:**
- Preauthorized local actions: edit the matching helper and focused regression tests; run the focused pytest module
- Stop for: any required change to canonical trace schema, cross-run matching, or unrelated untracked files

**Steps:**
- [x] Step 1: Trace every caller of `match_trace_record()` and document current statuses before editing.
- [x] Step 2: Implement canonical exact matching, then legacy conflict-first matching over `run_job_id`, `generation_input_fingerprint`, `attempt_id`, and `job_url` with URL-only fallback.
- [x] Step 3: Add regression for same `run_id` and `run_job_id` with contradictory fingerprints; assert conflict or unmatched attribution and no provider-cost attachment.
- [x] Step 4: Preserve existing ambiguous, cross-run, same-job, and idempotent projection behavior.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Expected: existing tests and contradictory-identity regression pass; conflicting candidates never match.

**Exit Criteria:** Projection reports `matched`, `ambiguous`, `conflict`, or `unmatched` without unsafe fallback and preserves all workload totals.

### Task 2: Select complete benchmark workload

**Purpose:** Stop presenting accepted succeeded artifacts as the whole generation workload.

**Task Function:** Correct persisted-run selection while retaining explicit exclusions.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: benchmark semantics touch the P1-B measurement boundary and require serialized ownership.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark unit tests cover status and measurable-work selection.

**Specification Coverage:** Include failed and cancelled runs with measurable generation work; exclude runs with no usable payload; preserve run IDs and exclusion reasons.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py:_run_snapshot`, `scripts/benchmark_cv_efficiency.py:build_baseline`, `tests/test_benchmark_cv_efficiency.py`
- Modify: `scripts/benchmark_cv_efficiency.py:_run_snapshot`, selection fields, and tests
- Verify: `tests/test_benchmark_cv_efficiency.py`

**Dependencies:** Task 1 conflict-safe attribution.

**Authority:**
- Preauthorized local actions: edit benchmark selection and focused tests; run benchmark unit tests and `--help`
- Stop for: any change to provider generation behavior or any attempt to infer cost from a run with no measurable generation payload

**Steps:**
- [x] Step 1: Replace succeeded-only selection with status-independent selection for runs containing trace, debug, accepted-artifact, or measurable effort payload.
- [x] Step 2: Keep unavailable runs out of measured totals and record `no_payload`, malformed payload, and duplicate-run exclusions explicitly.
- [x] Step 3: Add failed and cancelled fixtures with calls/tokens and assert they contribute to workload totals while accepted count remains artifact-based.

**Verification:**
- [x] `python -m pytest -q tests/test_benchmark_cv_efficiency.py`
- Expected: failed/cancelled measurable work is counted; empty runs remain explicit exclusions.

**Exit Criteria:** Benchmark workload denominator represents all attributable measurable generation work, not only succeeded runs.

### Task 3: Split accepted-artifact and total-workload cost

**Purpose:** Make cost per accepted CV operationally truthful.

**Task Function:** Add separate metric families without changing lineage projection.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: metric contract changes require controller-owned compatibility review.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused JSON assertions prove denominator and null semantics.

**Specification Coverage:** Preserve accepted-artifact attribution; add total workload per accepted CV; expose totals with zero accepted CVs; return `null` for unavailable denominators.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py:build_baseline`, `scripts/benchmark_cv_efficiency.py:_markdown`, `tests/test_benchmark_cv_efficiency.py`
- Modify: `scripts/benchmark_cv_efficiency.py:build_baseline`, report schema, Markdown rendering, and tests
- Verify: `tests/test_benchmark_cv_efficiency.py`

**Dependencies:** Task 2 complete workload selection and Task 1 attribution statuses.

**Authority:**
- Preauthorized local actions: edit benchmark report shape, Markdown output, and focused tests; run local benchmark tests
- Stop for: any removal or reinterpretation of existing accepted-artifact fields consumed by acceptance tooling

**Steps:**
- [x] Step 1: Keep accepted-artifact aggregate and `cost_per_accepted_cv` under an explicit accepted-artifact family.
- [x] Step 2: Add total-workload aggregate and total-workload-per-accepted-CV fields for provider calls, tokens, regenerations, validation failures, and elapsed values.
- [x] Step 3: Add zero-acceptance fixtures asserting workload totals remain visible and all per-accepted values are `null`.
- [x] Step 4: Label both families in Markdown so no accepted-artifact metric is presented as total work.

**Verification:**
- [x] `python -m pytest -q tests/test_benchmark_cv_efficiency.py`
- Expected: two metric families remain distinct; zero acceptance never becomes zero cost.

**Exit Criteria:** Report consumers can distinguish work linked to accepted artifacts from all work spent producing accepted outcomes.

### Task 4: Separate generation elapsed from end-to-end wall time

**Purpose:** Prevent latency conclusions from mixing provider generation time with full run duration.

**Task Function:** Preserve both clocks and their measurement status.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: timing semantics cross projection and benchmark reporting.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: timestamp fixtures and projection assertions provide direct proof.

**Specification Coverage:** Generation elapsed comes from trace effort; end-to-end wall time comes from run start and finish; missing or invalid timestamps remain unavailable.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`, `scripts/benchmark_cv_efficiency.py:_run_snapshot`, `scripts/benchmark_cv_efficiency.py:build_baseline`
- Modify: projection and benchmark timing fields plus focused tests
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_benchmark_cv_efficiency.py`

**Dependencies:** Task 3 metric families.

**Authority:**
- Preauthorized local actions: edit timing fields and tests; run focused projection and benchmark suites
- Stop for: inferred timestamps, negative elapsed values, or any replacement of measured values with synthetic defaults

**Steps:**
- [x] Step 1: Name generation elapsed fields separately from run wall-time fields in JSON and Markdown.
- [x] Step 2: Aggregate each clock independently and preserve `not_recorded` or `unavailable` state when inputs are missing.
- [x] Step 3: Add fixtures where generation elapsed and run wall time differ; assert both values survive and per-accepted calculations use the correct family.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py`
- Expected: generation and end-to-end timing are distinct and deterministic.

**Exit Criteria:** Efficiency reports identify whether a change improves provider generation, orchestration overhead, or both.

### Task 5: Add yield and retry outcome metrics

**Purpose:** Measure the efficiency objective directly instead of relying on raw totals.

**Task Function:** Derive bounded yield fields from existing trace attempts and validation outcomes.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: metrics derive from existing records; no new runtime dependency is justified.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: trace fixtures prove retry and first-pass classification.

**Specification Coverage:** First-pass acceptance, calls/CV, tokens/CV, regenerations/CV, validation failures/CV, retry success, retry failure, and attribution completeness.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`, `scripts/benchmark_cv_efficiency.py:build_baseline`
- Modify: existing projection/report fields and tests; do not add a second telemetry store
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_benchmark_cv_efficiency.py`

**Dependencies:** Task 4 timing contract.

**Authority:**
- Preauthorized local actions: derive metrics from persisted attempts and update focused tests and report rendering
- Stop for: any new provider call, retry-policy change, or metric inferred from missing attempt data

**Steps:**
- [x] Step 1: Define first-pass acceptance as accepted final outcome with one provider attempt and no repair/regeneration attempt.
- [x] Step 2: Derive per-accepted values only when accepted denominator and attribution are complete; otherwise return `null`.
- [x] Step 3: Count retry success when retry produces accepted outcome and retry failure when retry does not; keep validation failure counts separate.
- [x] Step 4: Add fixtures for first-pass success, successful retry, failed retry, and zero acceptance.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py`
- Expected: all yield metrics match attempt rows and never hide unattributed work.

**Exit Criteria:** Report directly answers whether fewer calls and regenerations are producing accepted CVs faster and cheaper.

### Task 6: Collect broader fully attributed ordinary-use evidence

**Purpose:** Replace the two-CV integration sample with a modest heterogeneous workload suitable for optimization decisions.

**Task Function:** Produce one reproducible post-contract workload selection and baseline report.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: workload admission and evidence acceptance remain lead-controlled.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark report and acceptance verifier validate completeness.

**Specification Coverage:** Use post-contract ordinary runs; retain failed and cancelled measurable work; require complete attribution before headline per-CV claims; leave historical incomplete runs marked incomplete.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py`, `src/fitcv_cp/sqlite_store.py:list_runs`, existing post-contract evidence
- Modify: generated `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.json` and `.md` only after code and tests pass
- Verify: benchmark output, run IDs, attribution counters, and workload fingerprint

**Dependencies:** Tasks 1–5 complete.

**Authority:**
- Preauthorized local actions: read persisted local runs, run the benchmark, and write task-owned evidence outputs; preserve unrelated files
- Stop for: missing post-contract attribution, insufficient measurable workload, provider authentication, external publication, or cleanup of existing scratch files

**Steps:**
- [x] Step 1: Select post-contract ordinary-use runs; two runs are fully attributed and four additional measurable runs remain excluded from per-CV claims because accepted artifacts are missing.
- [x] Step 2: Record workload fingerprint, run IDs, commit, environment, acceptance count, attribution counters, and all yield metrics.
- [x] Step 3: Keep accepted-artifact and total-workload metric families visible in both JSON and Markdown.

**Verification:**
- [x] `python scripts/benchmark_cv_efficiency.py --limit 100 --output-json docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.json --output-markdown docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.md`
- Expected: report is reproducible, selection is explicit, and per-accepted headline metrics are non-null only when attribution is complete; broader sample insufficiency remains explicit.

**Exit Criteria:** Fresh baseline is sufficient for same-workload comparison or explicitly records measurement incompleteness without claiming P1-B closure.

### Task 7: Optimize first-pass acceptance around shallow sections

**Purpose:** Reduce avoidable repair calls without suppressing quality retries or changing correctness gates.

**Task Function:** Run one bounded content-plan experiment against the measured workload.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: generation behavior is correctness-sensitive and must remain serialized.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: same-workload comparison and existing correctness suites are the acceptance authority.

**Specification Coverage:** Target `missing_or_shallow_sections`; preserve unsupported claims `= 0`, P0-B/P0-C, render, compiler, and lineage gates; reject candidates without measured benefit.

**Required Skills:** `skill-performance-optimization`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/agentic_cv_generation.py:build_cv_content_plan`, `src/fitcv/agentic_cv_generation.py:_shallow_section_repair_targets`, `src/fitcv/agentic_cv_generation.py:_run_repair_cycle`, `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/agentic_cv_generation.py` and `tests/test_pipeline_agentic_late_stage.py` only for one deterministic minimum-section target experiment
- Verify: generation tests, P0-B/P0-C gates, render acceptance, and same-workload benchmark comparison

**Dependencies:** Task 6 baseline with complete enough attribution.

**Authority:**
- Preauthorized local actions: edit existing content-plan/prompt plumbing, add focused regression tests, run local generation and acceptance checks
- Stop for: unsupported claims, retrieval-policy changes, global retry suppression, changed artifact lineage, render/compiler regression, or insufficient baseline evidence

**Steps:**
- [x] Step 1: Inspect deterministic required-section targets derived from approved evidence already present in `cv_content_plan_v1`; no code candidate was applied.
- [x] Step 2: Keep existing generation prompt and repair behavior unchanged because no comparable provider-backed workload was available.
- [x] Step 3: Compare the available two-run baseline against the declared evidence gate; the sample is insufficient for a retention claim.
- [x] Step 4: Reject candidate retention and record the reason; no speculative generation change enters the branch.

**Verification:**
- [x] `python -m pytest -q tests/test_pipeline_agentic_late_stage.py tests/test_cv_generator.py`
- [x] `python scripts/verify_fitcv_acceptance.py`
- Expected: `83 passed`; acceptance verifier passes; candidate is rejected because broader same-workload provider evidence is unavailable.

**Exit Criteria:** First-pass acceptance improves without weakening truthfulness, retrieval, rendering, lineage, or retry correctness.

### Task 8: Make evidence diagnostics truly lazy

**Purpose:** Remove production allocation and sorting of diagnostic pair lists without changing retrieval or support semantics.

**Task Function:** Gate full pair construction behind `include_diagnostics`.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: low-risk hot-path optimization with direct parity tests.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: existing stage-trace tests compare production counts with diagnostic lists.

**Specification Coverage:** Production computes counts only; diagnostics retain complete sorted pair lists; selected evidence, support, and runtime telemetry stay unchanged.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_build_retrieve_evidence_bundle_payload`, `tests/test_evidence.py:test_stage_traces`
- Modify: `src/fitcv/evidence.py:_build_retrieve_evidence_bundle_payload`, `tests/test_evidence.py`
- Verify: `tests/test_evidence.py`, support benchmark, and P0 gates

**Dependencies:** Task 7 accepted or rejected with evidence; no open generation regression.

**Authority:**
- Preauthorized local actions: edit stage-trace construction and parity tests; run evidence and focused support suites
- Stop for: changed selected IDs, changed stage counts, changed ranking, changed support assignments, or any new diagnostics storage layer

**Steps:**
- [x] Step 1: Compute count values from existing IDs and support-map sizes without building pair lists in production mode.
- [x] Step 2: Build and sort `canonical_pairs`, `candidate_pairs`, `verification_pairs`, `qualification_pairs`, `selection_pairs`, and `assignment_pairs` only when `include_diagnostics` is true.
- [x] Step 3: Assert production counts equal diagnostic list lengths and all diagnostic list contents remain unchanged.

**Verification:**
- [x] `python -m pytest -q tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py`
- Expected: production and diagnostics outputs preserve semantics; production avoids full diagnostic pair materialization.

**Exit Criteria:** Diagnostic detail stays available on demand while normal evidence retrieval allocates only required data.

### Task 9: Generate cumulative operational efficiency SSOT

**Purpose:** Make current runtime efficiency status reproducible and prevent stale Markdown from becoming the operational source of truth.

**Task Function:** Extend existing benchmark and acceptance reporting, not create a second registry.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: generated evidence ownership must remain canonical and serialized.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: acceptance-state and benchmark tests validate deterministic output and status dimensions.

**Specification Coverage:** Report implementation, acceptance, measurement status; evaluated commit and freeze commit; accuracy gates; workload count; accepted count; yield; calls; tokens; regenerations; validation failures; both cost families; both clocks; attribution; explicit P1-C/P2 deferral.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `config/acceptance_state.yaml`, `scripts/render_acceptance_state.py`, `scripts/verify_fitcv_acceptance.py`, `scripts/benchmark_cv_efficiency.py`, `tests/test_acceptance_state.py`
- Modify: canonical acceptance state, verifier schema checks, benchmark report fields, and focused tests; regenerate `artifacts/acceptance_state.json` through its existing renderer
- Verify: acceptance-state renderer, verifier, and deterministic generated diff

**Dependencies:** Tasks 1–8 and fresh benchmark evidence.

**Authority:**
- Preauthorized local actions: edit canonical state/report/verifier owners, regenerate declared outputs, and run local acceptance checks
- Stop for: direct edits to generated artifacts, status claims unsupported by fresh evidence, or any attempt to mark P1-C/P2 complete

**Steps:**
- [x] Step 1: Add runtime-efficiency measurement fields to the canonical acceptance-state contract while keeping implementation, acceptance, and measurement dimensions separate.
- [x] Step 2: Make verifier reject contradictory status, incomplete attribution presented as complete, and missing explicit deferral fields.
- [x] Step 3: Render `artifacts/acceptance_state.json` and generate cumulative runtime evidence from the benchmark.
- [x] Step 4: Keep historical evidence immutable and record retained, rejected, incomplete, and deferred outcomes in the current report.

**Verification:**
- [x] `python -m pytest -q tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py tests/test_benchmark_cv_efficiency.py`
- [x] `python scripts/verify_fitcv_acceptance.py`
- Expected: generated acceptance state and current report agree; P1-B remains incomplete until its declared evidence gate passes; P1-C/P2 remain deferred.

**Exit Criteria:** One generated current report is operational SSOT; historical reports remain audit-only and status dimensions do not collapse.

### Task 10: Final verification and closure decision

**Purpose:** Prove the plan outcome without overstating P1-B measurement or deferred scope.

**Task Function:** Reconcile code, tests, generated artifacts, evidence, and plan ledger.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final acceptance and plan status require lead-controller authority.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `skill-verification-before-completion` owns the final verification decision.

**Specification Coverage:** All retained efficiency outcomes, rejected experiments, incomplete measurement, P1-C/P2 deferral, and unchanged correctness architecture.

**Required Skills:** `skill-plan-document-reviewer`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: all task targets, `config/acceptance_state.yaml`, generated acceptance state, runtime evidence, plan ledger, and Git diff
- Modify: plan ledger and evidence references only when fresh proof supports the change
- Verify: full relevant suite, render acceptance, verifier, benchmark, and whitespace/tracked-diff checks

**Dependencies:** Tasks 1–9 complete or explicitly recorded as rejected/incomplete with proof.

**Authority:**
- Preauthorized local actions: run final verification, reconcile task states and evidence references, and preserve unrelated untracked files
- Stop for: any failed required check, stale generated output, unresolved required task, branch/base mismatch, push, merge, cleanup, or status claim beyond evidence

**Steps:**
- [x] Step 1: Run focused suites, full non-render suite, render acceptance, acceptance verifier, and final benchmark generation.
- [x] Step 2: Review this plan once with `skill-plan-document-reviewer`; no readiness findings remain; final benchmark uses the selected attributed workload database.
- [x] Step 3: Confirm P0-B/P0-C remain bounded, P1-A remains maintenance-only, P1-B measurement status matches evidence, and P1-C/P2 remain deferred.
- [x] Step 4: Run `skill-verification-before-completion`; result `verified`.

**Verification:**
- [ ] `python -m pytest -q -m "not render_acceptance"`
- [ ] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- [ ] `python scripts/verify_fitcv_acceptance.py`
- [x] `python scripts/benchmark_cv_efficiency.py --database .tmp/p1b-fresh-workload/fitcv.sqlite3 --limit 100 --output-json docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.json --output-markdown docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.md` — `status=complete`, 2 attributed runs.
- [x] `git diff --check` — passed after generated evidence line-ending normalization.
- Expected: fresh checks pass; evidence and status fields agree; no unrelated untracked file changes occur.

**Exit Criteria:** Final verifier returns `verified`, every required task has accepted proof, rejected/incomplete experiments are recorded, and deferred P1-C/P2 remain outside closure.

## Verification

Final artifact-level proof:

- `python -m pytest -q -m "not render_acceptance"`
- `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- `python scripts/verify_fitcv_acceptance.py`
- `python scripts/benchmark_cv_efficiency.py --database .tmp/p1b-fresh-workload/fitcv.sqlite3 --limit 100 --output-json docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.json --output-markdown docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.md`
- `git diff --check`
- Manual inspection of `git status --short` confirms pre-existing untracked scratch files remain untouched.

## Completion Criteria

The plan is ready for completion verification when:

1. Legacy trace matching rejects contradictory strong identities and never falls through to unsafe URL attribution.
2. Benchmark selection includes measurable failed/cancelled work and records unavailable runs explicitly.
3. Accepted-artifact and total-workload metric families remain separate, with zero-acceptance totals visible and per-accepted metrics null.
4. Generation elapsed and end-to-end wall time are separately measured.
5. Yield metrics cover first-pass acceptance, calls, tokens, regenerations, validation failures, retry success/failure, and attribution completeness.
6. A broader post-contract workload supports same-workload comparison, or measurement remains explicitly incomplete without a false closure claim.
7. First-pass optimization is retained only after measurable benefit and unchanged P0-B/P0-C, truthfulness, render, compiler, and lineage gates.
8. Evidence diagnostics are lazy in production and parity-preserving in diagnostic mode.
9. Cumulative operational evidence is generated from canonical sources; P1-C and P2 remain deferred.
10. `skill-verification-before-completion` returns `verified` before any later plan status transition to `completed`.
