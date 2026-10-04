---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-target-architecture-reporting-integrity
targets:
  - src/fitcv_cp/run_artifact_contracts.py
  - scripts/benchmark_cv_efficiency.py
  - scripts/verify_fitcv_acceptance.py
  - scripts/render_acceptance_state.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_benchmark_cv_efficiency.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_acceptance_state.py
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
  - docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.json
  - docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.md
---

# FitCV Target Architecture: Reporting Integrity

## Goal

Make accepted-artifact cost, generation timing, retry yield, attribution, and
operational evidence use one normalized generation-trace collection. Preserve
the frozen P0-B/P0-C scope, maintenance-only P1-A, and functional P1-B
contracts. Keep P1-B measurement status `incomplete` until fresh ordinary-use
evidence meets the measurement gate. Defer P1-C and P2.

## Review Findings

- Verdict is correct: P0-A is a rejected experiment, P0-B is closed only for
  its frozen evaluated scope, P0-C is closed for reviewed regressions, P1-A is
  maintenance-only, P1-B is functionally accepted but measurement-incomplete,
  and P1-C/P2 remain deferred.
- Current defect is reporting-only: `build_accepted_cv_effort_projection()`
  normalizes top-level and embedded traces, while `_run_snapshot()` counts raw
  top-level traces. Embedded-only work disappears from timing/yield; duplicate
  top-level work is counted twice.
- Evidence already drifted for the same two runs: baseline reports retry
  success/failure `4 / 0`; final reports `2 / 2`. `config/acceptance_state.yaml`
  still points at the older baseline pair.
- Existing projection tests already cover several lineage and failure cases;
  new work must extend them, not create a second reporting contract.
- The pasted proposal is narrowed here to the remaining architecture gap. It
  does not reopen retrieval, compiler, render contracts, global retry policy,
  or rejected optimization paths.

## Implementation Outcomes

### One normalized trace SSOT

`src/fitcv_cp/run_artifact_contracts.py` owns one reusable collector that
merges top-level and embedded trace records, enriches identity before
deduplication, collapses exact duplicates by canonical `trace_id`, and exposes
conflict/ambiguity diagnostics without selecting a winner. The accepted-CV
projection and benchmark consume that collector.

### Truthful efficiency report

`scripts/benchmark_cv_efficiency.py` computes cost, token totals, generation
duration, attempted jobs, first-pass acceptance, retry success/failure,
validation failures, and failure categories from the same normalized set.
Unknown timing stays unavailable rather than becoming `0.0`. Generation time,
accepted-artifact latency, and run wall time remain separate fields with
coverage counts.

### One canonical evidence pair

The acceptance state points to one regenerated JSON/Markdown efficiency pair.
Older duplicate reports remain explicitly historical/superseded or are
regenerated identically; no stale pair remains an active source of truth.
Rebuilding from declared run IDs verifies material-metric equality.

### Automatic measurement boundary

Acceptance verification checks report completeness and measurement eligibility
without promoting current status. The current state remains
`runtime_efficiency.measurement_status: incomplete` and `p1_c: deferred`.
Ordinary failed, cancelled, accepted, and human-reviewed runs feed the same
benchmark when measurable generation work exists.

### Target architecture preserved

The existing pipeline remains:

```text
candidate/profile SSOT
  -> verified evidence
  -> requirement_coverage
  -> cv_content_plan_v1
  -> primary generation
  -> bounded repair
  -> accepted artifact
  -> trace_id + run_job_id
  -> normalized trace collection
  -> accepted_cv_effort_v1
  -> canonical runtime-efficiency report
  -> measurement-status gate
```

No P1-C market-gap request-path feature, ESCO dependency, new agent, graph,
vector store, reranker, routing service, or global retry suppression enters
this plan.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit plan-listed source, tests, acceptance metadata, generated evidence, and docs; run declared local checks; preserve unrelated workspace files
- User-approval actions: push, merge, publication, dependency/provider changes, destructive recovery, discard, cleanup, and acceptance-status promotion
- Parallel ownership: none
- Sequential fallback: complete tasks in listed order; do not parallelize shared contract or generated-evidence edits

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-p0-p1-closure-contract`
- Base commit: `fddad591ab03d9fe2b3a1ed72af1ef9174bf8490`
- Expected workspace: `preserved dirty workspace with existing untracked scratch/data files; no cleanup or discard`
- Next action: `run skill-verification-before-completion`
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | focused contract tests | passed |
| Task 2 | `completed` | current | `codex` | Task 1 | benchmark tests and report-shape assertions | passed |
| Task 3 | `completed` | current | `codex` | Task 2 | generated-pair rebuild equality | passed |
| Task 4 | `completed` | current | `codex` | Task 3 | persistence and acceptance-state tests | passed |
| Task 5 | `completed` | current | `codex` | Task 4 | measurement-gate tests and unchanged incomplete status | passed |

## Task Breakdown

### Task 1: Extract one normalized trace collection

**Purpose:** Remove duplicate workload reconstruction and preserve safe
lineage behavior at the shared contract boundary.

**Task Function:** Refactor trace collection inside the existing artifact
contract module; do not add a new module or dependency.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded shared-contract refactor with existing tests and
  explicit lineage risk.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused contract tests provide required proof.

**Specification Coverage:** One collector merges top-level and embedded traces;
identity is enriched before deduplication; exact duplicate records collapse;
conflicts and ambiguity remain observable; legacy matching stays run-scoped.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/run_artifact_contracts.py:_normalize_trace_record`,
  `_trace_identity`, `match_trace_record`,
  `build_accepted_cv_effort_projection`
- Modify: `src/fitcv_cp/run_artifact_contracts.py` with
  `collect_normalized_generation_traces` and projection integration
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`

**Dependencies:** Existing `accepted_cv_effort_v1` schema and current
`match_trace_record()` behavior remain compatibility constraints.

**Authority:**
- Preauthorized local actions: edit shared trace-contract code and focused contract tests; run their pytest file
- Stop for: any provider-generation change, schema rename without consumer proof, or need to guess through a conflict

**Steps:**
- [x] Step 1: Define collector input order as standalone generation traces
  followed by embedded `record["cv_generation_trace"]` values, with record
  lineage enrichment before identity calculation.
- [x] Step 2: Deduplicate exact canonical identities; retain a diagnostic entry
  for same-identity payload conflicts or unresolved ambiguity instead of
  choosing one record.
- [x] Step 3: Route `build_accepted_cv_effort_projection()` through the
  collector and expose normalization diagnostics without changing existing
  accepted-artifact attribution statuses.
- [x] Step 4: Add regressions for embedded-only accepted trace, duplicate
  top-level trace, conflicting duplicate identity, cross-run separation,
  ambiguous legacy identity, failed/cancelled work, zero acceptance, and
  validation-failed retry.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Expected: exact duplicate trace appears once; embedded-only trace remains
  attributable; conflicts stay unresolved and visible; existing lineage tests
  pass.

**Exit Criteria:** Projection and all callers use one shared normalized trace
collection; no benchmark-only reconstruction remains necessary.

### Task 2: Rewire benchmark metrics and timing semantics

**Purpose:** Make timing and yield describe the same logical workload as cost
accounting.

**Task Function:** Replace raw top-level trace iteration in benchmark snapshots
with Task 1 output and separate timing concepts.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: report-contract change with small, directly testable scope.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused benchmark fixtures cover metric semantics.

**Specification Coverage:** Embedded-only trace with `100 ms` yields one job and
`100 ms`; duplicated top-level trace yields one job and `100 ms`; unavailable
timing is not zero; generation duration, artifact acceptance latency, and run
wall time are distinct.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py:_trace_records`,
  `_trace_generation_elapsed_ms`, `_run_snapshot`, `build_baseline`, `_markdown`
- Modify: `scripts/benchmark_cv_efficiency.py` and
  `tests/test_benchmark_cv_efficiency.py`
- Verify: generated report JSON and Markdown from `build_baseline()`

**Dependencies:** Task 1 collector and projection diagnostics.

**Authority:**
- Preauthorized local actions: edit benchmark code, report fields, and focused benchmark tests; run benchmark tests and CLI help
- Stop for: any reinterpretation of accepted-artifact fields consumed by acceptance tooling or any fallback of unknown timing to zero

**Steps:**
- [x] Step 1: Remove independent raw-trace reconstruction from `_run_snapshot()`;
  consume normalized records and exclude unresolved conflict rows from measured
  counts while retaining coverage diagnostics.
- [x] Step 2: Change `_trace_generation_elapsed_ms()` to return `float | None`;
  count measured and unavailable timing separately and calculate averages only
  from measured values with explicit coverage.
- [x] Step 3: Name and report separate generation-duration,
  artifact-acceptance-latency, and run-wall-clock metrics; retain compatibility
  fields only where their meaning remains exact.
- [x] Step 4: Keep failed/cancelled measurable runs in total workload and keep
  per-accepted-CV metrics `null` when denominator, attribution, or required
  timing coverage is incomplete.
- [x] Step 5: Update Markdown labels so `elapsed_ms` cannot imply one accepted
  CV when it is run wall time or an aggregate.

**Verification:**
- [x] `python -m pytest -q tests/test_benchmark_cv_efficiency.py`
- Expected: embedded-only and duplicate fixtures produce one job and `100 ms`;
  retry counts match normalized records; missing duration is unavailable;
  failed/cancelled workload remains visible.

**Exit Criteria:** Cost, timing, yield, and failure metrics use identical trace
identity and no report aliases wall time to artifact latency.

### Task 3: Establish one canonical runtime-efficiency evidence pair

**Purpose:** Remove active evidence drift and make report regeneration
reproducible from declared run IDs.

**Task Function:** Regenerate canonical evidence and mark duplicate reports as
historical without deleting audit material.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: generated-output reconciliation after code contract changes.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: deterministic material-metric comparison.

**Specification Coverage:** One active JSON/Markdown pair; acceptance state
references it; older baseline/final/fresh outputs cannot disagree silently.

**Required Skills:** `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py:main`,
  `config/acceptance_state.yaml`,
  `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-*.json`
- Modify: `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.json`,
  `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-baseline.md`,
  `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.json`,
  `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-final.md`,
  `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-fresh.json`,
  `docs/superpowers/evidence/2026-10-02-fitcv-runtime-efficiency-fresh.md`,
  and `config/acceptance_state.yaml`
- Verify: `artifacts/acceptance_state.json` after rendering

**Dependencies:** Task 2 report shape and semantics.

**Authority:**
- Preauthorized local actions: regenerate plan-listed evidence and acceptance metadata; run deterministic render and comparison checks
- Stop for: missing run IDs, changed material metrics without source explanation, or deletion/cleanup of historical evidence

**Steps:**
- [x] Step 1: Keep the acceptance-state-referenced baseline pair as the active
  output path unless a consumer requires a path change.
- [x] Step 2: Rebuild the active pair from its declared run IDs and record the
  corrected retry/yield and timing semantics.
- [x] Step 3: Mark final/fresh duplicate reports historical or superseded with
  explicit provenance; do not leave them presented as current evidence.
- [x] Step 4: Add a material-metrics rebuild check that ignores volatile
  generation timestamp/environment fields and fails on contradiction.
- [x] Step 5: Render `artifacts/acceptance_state.json` from YAML after the
  canonical paths are valid.

**Verification:**
- [x] `python scripts/benchmark_cv_efficiency.py --help`
- [x] `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json`
- [x] deterministic rebuild comparison for canonical run IDs
- Expected: YAML and JSON reference same active pair; active JSON/Markdown
  material metrics match; stale duplicate outputs are explicitly historical.

**Exit Criteria:** One report pair owns current runtime-efficiency claims and
rebuilding it cannot silently produce a second answer for the same runs.

### Task 4: Persist actual page-fit and human-effort telemetry

**Purpose:** Keep efficiency optimization from trading away usable artifacts or
claiming manual-effort reduction without human-work evidence.

**Task Function:** Carry existing render and review outcomes through the
canonical debug payload and projection; do not add a new service or datastore.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded payload-lineage change across existing pipeline
  contracts.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: worker/pipeline contract tests and projection assertions.

**Specification Coverage:** Accepted records retain actual page-fit outcome,
review questions, human actions, reused resolutions, and acceptance latency;
missing fields remain explicitly unavailable.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:_build_cv_generation_debug_payload`,
  `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`,
  `src/fitcv/agentic_cv_generation.py:_empty_cv_generation_trace`,
  `tests/test_fitcv_cp/test_worker_job.py`
- Modify: existing trace/debug payload propagation and focused tests only
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`,
  `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:** Task 1 normalized identity; existing render acceptance and
HITL action contracts.

**Authority:**
- Preauthorized local actions: edit existing payload propagation and focused tests; run backend contract checks
- Stop for: any new persistence layer, fabricated historical telemetry, or weakening of render/acceptance gates

**Steps:**
- [x] Step 1: Trace actual page-fit result from finalized render/acceptance
  output into the accepted generation trace or artifact event.
- [x] Step 2: Preserve existing review-question, human-action, and reused-
  resolution fields through worker serialization and projection.
- [x] Step 3: Keep absent telemetry as `not_recorded`/unavailable and expose
  coverage counts instead of converting it to zero.
- [x] Step 4: Add fixtures for accepted one-page, accepted non-one-page, no
  human-review, and actual HITL resolution outcomes.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Expected: serialized accepted records retain actual page-fit and human-work
  values; missing telemetry remains explicit; artifact lineage stays intact.

**Exit Criteria:** Normal accepted artifacts can prove page fit and manual
effort from persisted SSOT fields; synthetic render acceptance remains a
separate implementation gate.

### Task 5: Add automatic measurement gate and deferred optimization boundary

**Purpose:** Automate truthful P1-B measurement status without prematurely
claiming stability or implementing P1-C.

**Task Function:** Extend acceptance verification to validate evidence coverage,
then define the next bounded optimization experiment behind that gate.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: acceptance-state and evidence-status change with explicit
  deferral boundary.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: acceptance-state and verifier tests.

**Specification Coverage:** Gate requires heterogeneous ordinary runs,
complete attribution, complete core cost telemetry, sufficient timing coverage,
multiple job types, actual page-fit coverage, and measured HITL fields before
promotion. Current status stays incomplete. P1-C remains deferred/offline-only.

**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `scripts/verify_fitcv_acceptance.py:build_acceptance_report`,
  `verify_acceptance`, `scripts/render_acceptance_state.py:_validate_state`,
  `tests/test_acceptance_state.py`,
  `tests/test_fitcv_cp/test_acceptance_verifier.py`
- Modify: verifier measurement checks, acceptance-state tests, and evidence
  status fields; keep `config/acceptance_state.yaml` at incomplete/deferred
- Verify: `.tmp/fitcv-acceptance-report.json` and final verifier output

**Dependencies:** Tasks 1–4 and canonical evidence pair.

**Authority:**
- Preauthorized local actions: edit verifier/tests and keep status metadata at incomplete/deferred; run declared acceptance checks
- Stop for: any automatic promotion to measured, any P1-C implementation, or failed P0-B/P0-C/P1-B contract evidence

**Steps:**
- [x] Step 1: Add machine-checkable report coverage fields for attribution,
  cost, timing, page fit, run/job diversity, review questions, human actions,
  and resolution reuse.
- [x] Step 2: Make verifier reject a measured claim when any required coverage
  or canonical-report equality gate fails; preserve current incomplete result.
- [x] Step 3: Add tests for incomplete coverage, contradictory report/state,
  and eligible future evidence without changing current state.
- [x] Step 4: Record the next optimization boundary only: after gate passes,
  run one same-workload section-sufficiency experiment using existing
  `cv_content_plan_v1`; retain it only if first-pass acceptance and total-work
  KPIs improve with all correctness gates unchanged.
- [x] Step 5: Leave P1-C as future offline aggregation over imported jobs,
  canonical requirements, and `requirement_coverage`; do not implement it in
  this plan.

**Verification:**
- [x] `python -m pytest -q tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- [x] `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --output .tmp/fitcv-acceptance-report.json`
- Expected: verifier passes current declared frozen scope, reports P1-B
  measurement `incomplete`, and reports P1-C/P2 deferred.

**Exit Criteria:** Measurement promotion is automatic and conservative; current
state remains honest; future optimization and P1-C have explicit gates and no
request-path architecture is added.

## Verification

- `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_benchmark_cv_efficiency.py tests/test_fitcv_cp/test_worker_job.py tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output artifacts/acceptance_state.json`
- `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --output .tmp/fitcv-acceptance-report.json`
- `git diff --check`
- `git status --short --branch`

Final proof must show one normalized trace collection, correct embedded-only
and duplicate handling, explicit unavailable timing, no active evidence
contradiction, unchanged frozen-scope acceptance, `measurement_status:
incomplete`, `p1_c: deferred`, and `p2: deferred`. Full Suite, Focused Smoke,
and Render Acceptance remain required before any later acceptance closure, but
are not duplicated as task-local implementation proof here.

## Completion Criteria

The plan is ready for completion verification when:

1. all five tasks have task-local proof and no unresolved scope deviation;
2. projection and benchmark use the same normalized traces;
3. duplicate, embedded-only, conflict, failure, and unavailable-timing cases
   have regression coverage;
4. one canonical evidence pair is referenced by acceptance state and rebuilds
   to identical material metrics;
5. actual page-fit and human-effort fields remain lineage-safe and unavailable
   values are not fabricated;
6. verifier enforces conservative measurement eligibility without promoting
   current incomplete evidence;
7. P0-B/P0-C/P1-A contracts remain frozen and P1-C/P2 remain deferred;
8. `skill-verification-before-completion` runs fresh final checks and returns
   `verified` before any branch disposition.

## Post-plan defect closure

The shared pipeline trace-summary boundary also preserves run, artifact, and
render lineage copied from accepted debug records. This closes reporting
attribution without changing request-path behavior. P1-C remains deferred.

## Measurement promotion

Follow-up run `1f270c23-b90a-4020-b120-6546776438d0` plus native rendering
closed page-fit and two-run diversity gates. Acceptance state now records
`measurement_status: measured`; P1-C and P2 remain deferred.
