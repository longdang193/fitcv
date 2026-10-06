---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-pr87-analytics-semantic-convergence
targets:
  - config/analytics_metrics.yaml
  - config/acceptance_state.yaml
  - config/evidence_registry.yaml
  - scripts/fitcv_analytics.py
  - scripts/sql/fitcv_gold_views.sql
  - scripts/benchmark_cv_efficiency.py
  - scripts/render_acceptance_state.py
  - scripts/verify_fitcv_acceptance.py
  - tests/test_fitcv_analytics.py
  - tests/test_benchmark_cv_efficiency.py
  - tests/test_acceptance_state.py
  - tests/test_fitcv_cp/test_acceptance_verifier.py
  - tests/fixtures/analytics_semantic_contract.json
  - artifacts/acceptance_state.json
  - docs/superpowers/evidence/
---

# FitCV PR #87 Analytics Semantic Convergence

## Goal

Make FitCV analytics one executable, read-only Bronze → Silver → Gold path
before starting P1-C dashboard work. Reconcile mutable source observations once,
give every Gold relation one declared grain, make acceptance dimensions follow
`status_dimensions`, and make benchmark, JSON, Markdown, CI, and future BI
consume the same semantic metrics.

This plan implements the next execution sequence from the reviewed verdict. It
does not implement the P1-C dashboard, longitudinal trends, opportunity
prioritization, or a new analytics platform.

## Implementation Outcomes

### 1. Executable analytics path

`scripts/fitcv_analytics.py` exposes deterministic Bronze, Silver, and Gold
rebuild behavior from declared source inputs. Bronze preserves raw snapshots;
Silver reconciles logical identities and validity; Gold emits stable,
decision-oriented relations off the CV-generation request path.

### 2. Explicit Gold grains and metric contracts

Artifact, run-job, and cohort metrics have separate names, schemas, and grains.
Versioned metric definitions in `config/analytics_metrics.yaml` define numerator,
denominator, dimensions, cohort policy, null policy, and coverage semantics.

### 3. Reporting and evidence convergence

`benchmark_cv_efficiency.py`, generated JSON, Markdown, acceptance state, and CI
read canonical Gold and registry data. Historical evidence remains visible and
cannot pass as current merely because optional experiment arguments were omitted.

### 4. Adversarial proof

Tests cover repeated snapshots, mutable events, join multiplication, zero
denominators, missing telemetry, current/historical mixing, cohort mixing, and
ratio-of-averages errors. Final proof confirms no operational request-path
dependency and no unsupported P1-C completion claim.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit declared analytics, metric-contract, evidence, test, SQL, and documentation surfaces; run declared local checks; preserve existing untracked scratch files
- User-approval actions: push, merge, publication, external writes, destructive recovery, discard, cleanup, acceptance-state promotion, or changing existing untracked scratch files
- Parallel ownership: none; same-workspace writers execute sequentially
- Sequential fallback: Task 1 → Task 2 → Task 3 → Task 4 → Task 5

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-evidence-scoped-backfill`
- Base commit: `108e5a87ea0dfdeff2eb03b5a7a34e5116865708`
- Expected workspace: `dirty baseline recorded below; preserve existing untracked scratch files and stage only declared task paths`
- Next action: commit intended files, push branch, open PR, assign independent `review-1`, address findings, and merge only after all checks pass.
- Blockers: `retained R5 manifest/database inputs remain unavailable; runtime measurement is explicitly demoted to incomplete and no current runtime claim is made.`
- Recovery owner: `single lead controller`; no worker may alter registry, acceptance state, retained evidence, or retained database bytes.
- Dirty baseline: modified tracked files are `scripts/benchmark_cv_efficiency.py`, `scripts/fitcv_analytics.py`, `scripts/sql/fitcv_gold_views.sql`, `scripts/verify_fitcv_acceptance.py`, `tests/test_benchmark_cv_efficiency.py`, `tests/test_fitcv_analytics.py`, and `tests/test_fitcv_cp/test_acceptance_verifier.py`; intended untracked files are `config/analytics_metrics.yaml`, `tests/fixtures/analytics_semantic_contract.json`, and this plan; all other existing untracked files remain scratch and out of scope.

## Post-Review Correction Sequence

- [x] Preserve actual `run_job_id` grain in benchmark Gold projections and emit no synthetic job for empty input.
- [x] Filter requirement-demand and candidate-gap Gold inputs by source type; exclude invalid facts and propagate unavailable coverage.
- [x] Require explicit claim-to-priority mapping, including `p1b_current_contract_measurement` → `p1_b`; reject unknown claims.
- [x] Require source commit, material digest, and input fingerprint provenance before accepting unavailable current-contract evidence.
- [x] Add regressions for empty input, run-job identity, invalid/source filtering, unknown claims, and unavailable-evidence provenance.
- [x] Rerun focused and full suites, deterministic rebuild, SQL smoke test, acceptance verifier, and diff-scope review — focused `72 passed`; full `3225 passed, 8 skipped`; deterministic material digest `160d274abe31dbc05519892b4d56e8706bce5ab1e58f40cd6eb21058bdd92623`; six SQL views; `git diff --check` passed.

## Evidence Recovery Contract

- Authoritative R5 pair: `.tmp/fitcv-review-final-20261005-r5/incumbent-manifest.json` and the database path recorded by that manifest. The R5 evidence JSON records this pair as the source for the current contract; no arbitrary `data/control_plane.sqlite3` substitution is allowed.
- Recovery search: inspect the recorded disposable path, repository-local retained artifact locations, and any user-supplied retained location. Do not create a replacement manifest or infer a database from matching run IDs.
- Integrity proof: verify manifest `run_ids`, `repeat_count`, `fixture_sha256`, `declared_input_fingerprint`, `arm`, `declared_model`, and `resolved_models`; compute the retained database SHA-256 before copying; copy both files into `.tmp`; compute copy SHA-256; require byte equality and manifest/database run-set equality before benchmark execution.
- Failure rule: if exact R5 inputs remain unavailable, keep runtime measurement `incomplete`, demote R5 to `historical`, publish R6-unavailable evidence, and leave no current runtime acceptance claim. This demotion is explicitly approved by the user annotation for this next action; no replacement database or manifest may be inferred.
- Projection freshness SSOT: add `projection_inputs` to `config/analytics_metrics.yaml`; implement `scripts/fitcv_analytics.py::compute_projection_input_fingerprint(repo_root)` using sorted repository-relative paths, LF-normalized bytes, and SHA-256; import that helper from `scripts/benchmark_cv_efficiency.py` and `scripts/verify_fitcv_acceptance.py`; registry records the resulting value. Runtime/provider manifest provenance remains separate.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `none (lead controller)` | none | metric contract, identity, fixture, and fingerprint tests | `74 passed`; deterministic fixture and projection-fingerprint tests |
| Task 2 | `completed` | current | `none (lead controller)` | Task 1 | Silver reconciliation, all eight Gold metric builders, and state-mapping tests | `74 passed`; requirement/gap Gold rows and acceptance mapping verified |
| Task 3 | `completed` | current | `none (lead controller)` | Task 2 | executable rebuild, SQL replacement, and projection-freshness tests | deterministic rebuild equal digest; six SQL Gold views smoke-tested |
| Task 4 | `completed` | current | `none (lead controller)` | Task 2, Task 3 | benchmark/report/evidence convergence tests | R5 demoted to historical by explicit user instruction; R6-unavailable artifacts and fail-closed verifier pass |
| Task 5 | `completed` | current | `none (lead controller)` | Task 1–4 | final analytics, acceptance, and drift proof | `3218 passed, 8 skipped`; verifier passed; rebuild/SQL/diff proof passed |

## Task Breakdown

### Task 1: Freeze metric and logical-event contracts

**Purpose:**
- Establish one SSOT for metric definitions and one deterministic identity rule
  for mutable source observations.

**Task Function:**
- Contract extraction and invariant encoding.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded semantic-contract work; no delegation benefit.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent contract and adversarial-test review without write authority.

**Specification Coverage:**
- Reviewed verdict: logical-event reconciliation, explicit denominator context,
  unknown telemetry as incomplete rather than zero, and central metric registry.
- Invariant: Bronze retains history; Silver contains one canonical fact per
  logical identity; Gold does not mix artifact, job, and cohort grains.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/fitcv_analytics.py:build_bronze_observations`, `scripts/fitcv_analytics.py:build_silver_facts`, `tests/test_fitcv_analytics.py`
- Modify: `config/analytics_metrics.yaml`, `scripts/fitcv_analytics.py`, `tests/test_fitcv_analytics.py`, `tests/fixtures/analytics_semantic_contract.json`
- Verify: metric registry schema, identity precedence, and null/coverage behavior

**Dependencies:**
- Current `config/acceptance_state.yaml` and `config/evidence_registry.yaml`
  remain authoritative for acceptance and evidence state.
- Existing untracked files remain untouched.

**Authority:**
- Preauthorized local actions: edit declared metric, analytics, fixture, and test files; run focused Python tests
- Stop for: unresolved source identity precedence, conflicting authoritative schemas, or required changes outside declared analytics surfaces

**Steps:**
- [x] Step 1: Define `config/analytics_metrics.yaml` with `metric_id`, `version`, `source_model`, `grain`, `numerator`, `denominator`, `dimensions`, `cohort_policy`, `null_policy`, `coverage_metric`, `owner`, and `description`.
- [x] Step 2: Define canonical metric contracts for acceptance yield, provider calls per accepted CV, tokens per accepted CV, first-pass success, manual effort, verified one-page rate, skill demand, and evidence-gap categories. Map each contract to one executable builder and consumer before Task 2 closes.
- [x] Step 3: Extend Bronze rows with stable logical identity metadata separate from `observation_id`; preserve every raw snapshot and provenance.
- [x] Step 4: Apply latest-valid `observed_at` reconciliation only to observation types with stable logical IDs and monotonic mutable snapshots; preserve `collect_normalized_generation_traces` compatible top-level/embedded merging and conflicting-trace exclusion instead of winner-selecting conflicts.
- [x] Step 5: Add fixtures and tests for repeated snapshots, mutable payloads, missing logical IDs, missing telemetry, conflicting trace identities, compatible embedded traces, and ingestion-clock-independent digests.
- [x] Step 6: Extend `tests/fixtures/analytics_semantic_contract.json` with posting, requirement, candidate-evidence, and gap-category records required by `skill_demand` and `evidence_gap`; keep P1-C dashboard behavior deferred.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_analytics.py` — included in the recorded 72-test passing run.
- Expected: repeated snapshots collapse only in Silver; Bronze retains both; missing telemetry is unavailable/null with coverage metadata; metric definitions validate.

**Exit Criteria:**
- Metric registry and logical-event rules are versioned, deterministic, tested, and free of unresolved denominator or identity decisions.

### Task 2: Split Gold relations and map acceptance state correctly

**Purpose:**
- Replace ambiguous `gold_cv_effort` semantics with explicit artifact, run-job,
  and cohort relations, then map acceptance evidence to real state dimensions.

**Task Function:**
- Canonical Gold projection design and implementation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: tightly coupled to Task 1 contracts and existing projection code.

**Validator Profile:**
- Controller-selected: `review-1`
- Selection basis: independent grain, denominator, and state-schema review.

**Specification Coverage:**
- Reviewed verdict: `gold_cv_artifact`, `gold_run_job_effort`,
  `gold_cohort_effort`, and authoritative `status_dimensions` mapping.
- Invariant: accepted artifact denominator uses distinct canonical artifact IDs;
  all provider calls/retries remain in run-job workload totals; ratios are
  cohort/semantic metrics, not artifact-row fields.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/fitcv_analytics.py:build_gold_cv_effort`, `scripts/fitcv_analytics.py:build_gold_acceptance_state`, `config/acceptance_state.yaml:status_dimensions`
- Modify: `scripts/fitcv_analytics.py`, `config/acceptance_state.yaml` only when schema alignment requires it, `tests/test_fitcv_analytics.py`, `tests/test_acceptance_state.py`
- Verify: Gold row grains, acceptance/evidence dimensions, and unavailable semantics

**Dependencies:**
- Task 1 logical identity and metric registry contracts.
- Existing accepted-artifact predicate in `src/fitcv_cp/run_artifact_contracts.py` remains canonical unless source review proves a mismatch.

**Authority:**
- Preauthorized local actions: edit declared Gold, acceptance-state, and test files; run focused analytics and acceptance tests
- Stop for: changing operational SQLite tables, changing CV-generation behavior, or changing accepted-artifact semantics without source/test proof

**Steps:**
- [x] Step 1: Replace `build_gold_cv_effort` with separate canonical builders for one accepted artifact, one attempted run-job, and one cohort summary; retain a temporary compatibility adapter only if consumers require it.
- [x] Step 2: Aggregate provider attempts, generation attempts, review actions, retries, and failed work at run-job grain before any artifact join.
- [x] Step 3: Compute per-accepted-artifact and cohort ratios only from declared distinct denominators; return unavailable/null for zero or incomplete denominators rather than numeric zero.
- [x] Step 4: Declare an explicit claim-to-priority mapping for broad registry claims (`p0_acceptance_scope`, `p1_acceptance_scope`) and fail closed when a claim lacks expansion; define `gold_acceptance_state` grain and uniqueness as one row per `(priority, evidence_id)` plus one status-only row for deferred priorities without evidence. Preserve acceptance status and evidence status as separate dimensions.
- [x] Step 5: Rebuild `build_gold_acceptance_state` from `status_dimensions` plus the explicit registry mapping, carrying priority, implementation status, acceptance status, measurement status, optimization status, evidence ID/status, source commit, cohort type, current/historical, and deferred state.
- [x] Step 6: Add adversarial tests for repeated joins, duplicate artifact versions, zero accepted artifacts, mixed current/historical evidence, broad-claim expansion, deferred status-only rows, mixed cohorts, and ratio-of-averages errors.
- [x] Step 7: Implement `build_gold_requirement_demand` at requirement/cohort grain and `build_gold_candidate_gap` at requirement/gap-category/cohort grain in `scripts/fitcv_analytics.py`; deduplicate repeated requirement occurrences within one posting and keep missing evidence, unmet qualifier, and uncertain interpretation separate.
- [x] Step 8: Add direct fixture assertions for all eight registry metrics, including first-pass, verified-one-page, `skill_demand`, and `evidence_gap`; assert each output names its grain and coverage fields.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_analytics.py tests/test_acceptance_state.py`
- Expected: every Gold relation has one declared grain; failed work remains visible; current evidence is not treated as acceptance; missing denominator data never becomes zero.

**Exit Criteria:**
- Python Gold builders and acceptance projection produce deterministic, grain-correct rows with complete state dimensions and no ambiguous `gold_cv_effort` meaning.

### Task 3: Make rebuild and SQL surfaces executable

**Purpose:**
- Provide one repeatable off-path rebuild command and remove stale SQL
  placeholders or make them executable against declared projection tables.

**Task Function:**
- Rebuild-path integration and SQL contract hardening.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: local integration needs source-first decisions and no independent write lane.

**Validator Profile:**
- Controller-selected: `review-2`
- Selection basis: independent verification of idempotency, SQL execution, and request-path isolation.

**Specification Coverage:**
- Reviewed verdict: SQL remains version-controlled application logic; evolving
  definitions cannot rely on `CREATE VIEW IF NOT EXISTS`; analytics stays
  rebuildable and outside the CV-generation request path.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/sql/fitcv_gold_views.sql`, `scripts/fitcv_analytics.py`, `src/fitcv_cp/sqlite_store.py`
- Modify: `scripts/fitcv_analytics.py`, `scripts/sql/fitcv_gold_views.sql`, `tests/test_fitcv_analytics.py`, new sanitized fixture only if required
- Verify: disposable analytics SQLite or equivalent isolated rebuild target; never production operational tables

**Dependencies:**
- Task 2 Gold schemas and names.
- Operational SQLite remains transactional source of truth and must not gain analytics request-path dependencies.

**Authority:**
- Preauthorized local actions: edit declared rebuild and SQL files; create disposable local analytics databases; run local SQL/Python checks
- Stop for: writing analytics tables into operational request-path schema, destructive migration of user data, or external database access

**Steps:**
- [x] Step 1: Add a deterministic CLI/rebuild entrypoint to the analytics module or a minimal adjacent script; accept declared source bundle, source commit, input fingerprint, and output path.
- [x] Step 2: Execute Bronze → Silver → Gold in one idempotent rebuild; sort outputs deterministically and include schema/version/provenance metadata.
- [x] Step 3: Replace `CREATE VIEW IF NOT EXISTS` behavior with controlled rebuild semantics (`DROP VIEW`/`CREATE VIEW`, versioned names, or deterministic disposable schema setup).
- [x] Step 4: Ensure SQL names and columns match Python Gold outputs; if a current SQL view has no executable source table, remove that placeholder rather than preserving a false contract.
- [x] Step 5: Add an isolated smoke test that runs rebuild twice and proves identical material digests while ingestion timestamps may differ.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_analytics.py`
- [x] Run the new rebuild command against the sanitized fixture and inspect emitted Gold rows and digest.
- Expected: rebuild is repeatable, SQL executes against its declared projection schema, and no operational request path is touched.

**Exit Criteria:**
- One documented local command produces canonical Gold artifacts; SQL is either executable against that declared schema or absent rather than misleading.

### Task 4: Converge benchmark, reports, CI, and evidence registry

**Purpose:**
- Stop independent metric reconstruction and make evidence discovery registry-driven.

**Task Function:**
- Consumer migration and acceptance-evidence reconciliation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: cross-file consumer change requires one sequential owner.

**Validator Profile:**
- Controller-selected: `review-2`
- Selection basis: independent consumer parity and evidence-freshness review.

**Specification Coverage:**
- Reviewed verdict: benchmark/JSON/Markdown/CI consume canonical Gold;
  `acceptance_state.yaml` and `evidence_registry.yaml` answer current evidence,
  proving artifact, paths, and fingerprints; historical rejected R15 is visible
  as historical/rejected, not silently passed.

**Required Skills:**
- `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/benchmark_cv_efficiency.py:build_baseline`, `scripts/benchmark_cv_efficiency.py:material_report_metrics`, `scripts/benchmark_cv_efficiency.py:build_canonical_evidence`, `scripts/render_acceptance_state.py`, `scripts/verify_fitcv_acceptance.py`
- Modify: `scripts/benchmark_cv_efficiency.py`, `scripts/render_acceptance_state.py`, `scripts/verify_fitcv_acceptance.py`, `config/evidence_registry.yaml`, `tests/test_benchmark_cv_efficiency.py`, `tests/test_acceptance_state.py`, related evidence fixtures
- Verify: JSON/Markdown parity, registry freshness, declared input fingerprints, and historical promotion status

**Dependencies:**
- Tasks 1–3 canonical metrics and rebuild output.
- Existing benchmark trace and accepted-artifact contracts remain source-authoritative.

**Authority:**
- Preauthorized local actions: edit declared reporting, verifier, registry, fixture, and test files; regenerate local derived acceptance JSON when required
- Stop for: promoting historical evidence, changing current production routing, external provider calls, or modifying unrelated scratch files

**Steps:**
- [x] Step 1: Remove independent Gold-shaped aggregation from `build_baseline`; consume canonical run-job/cohort projections and attach one material digest.
- [x] Step 2: Make Markdown and JSON render from the same semantic metric object; preserve coverage, source mix, date range, cohort, and missingness metadata.
- [x] Step 3: Make acceptance verification discover required evidence from registry records and declared paths/fingerprints; omitted optional experiment arguments cannot produce `not_requested → passed`.
- [x] Step 4: Search for and verify exact R5 manifest/database pair; none exists locally, so approved demotion path is used and no replacement input is inferred.
- [x] Step 5: Mark retained R5 unavailable without copying or mutating any database; publish explicit R6-unavailable evidence.
- [x] Step 6: Compute and bind projection freshness through `compute_projection_input_fingerprint(repo_root)`; runtime/provider provenance remains separate.
- [x] Step 7: Do not run retained current rebuild because exact inputs are unavailable; fail-closed verifier and demotion artifacts replace fabricated current evidence.
- [x] Step 8: Generate durable R6-unavailable `.json`, `.md`, and `.sha256`; update registry/state/generated acceptance artifact only after verifier and render checks pass.
- [x] Step 9: Preserve R5 provenance as historical and encode incomplete runtime measurement with explicit unavailable reason.
- [x] Step 10: Add parity tests for canonical Gold, registry, state, projection freshness, and retained-input non-mutation boundaries.

**Verification:**
- [x] `python -m pytest -q tests/test_benchmark_cv_efficiency.py tests/test_acceptance_state.py`
- [x] `python -m pytest -q tests/test_fitcv_cp/test_acceptance_verifier.py`
- [x] `python scripts/verify_fitcv_acceptance.py --timeout-seconds 300 --output .tmp/fitcv-acceptance-report.json`
- [x] `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output .tmp/acceptance_state.json`
- Expected: all consumers report identical canonical values; stale or missing declared evidence fails closed; historical rejected evidence never passes as current; omitted experiment arguments exercise the same verifier boundary used by CI.

**Exit Criteria:**
- Reporting and CI have one semantic source, registry-driven evidence checks, explicit historical status, and no independently reconstructed Gold metric.

### Task 5: Run final convergence proof and record closure evidence

**Purpose:**
- Validate the complete analytics contract before authorizing any P1-C dashboard
  implementation plan.

**Task Function:**
- Final verification and evidence packaging.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: final acceptance requires controller-owned repository proof.

**Validator Profile:**
- Controller-selected: `review-3`
- Selection basis: independent final review of scope, regressions, and completion evidence.

**Specification Coverage:**
- Analytics convergence closure statement from reviewed verdict.
- Non-goals: no dashboard, trend claim, prioritization score, architecture
  expansion, provider routing change, or operational request-path dependency.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: all Task 1–4 targets, `docs/superpowers/plans/2026-10-05-fitcv-p0-p1-evidence-analytics-convergence-plan.md`
- Modify: `docs/superpowers/evidence/` with proof only; do not mark this plan completed before fresh verification returns `verified`
- Verify: repository tests, rebuild output, registry drift, SQL execution, and Git diff scope

**Dependencies:**
- Tasks 1–4 complete with accepted task-local proof.
- Existing untracked scratch files remain preserved and excluded from the diff.

**Authority:**
- Preauthorized local actions: run declared local verification, write task-owned evidence, and reconcile this plan’s ledger
- Stop for: failed required check, plan/Git mismatch, unexplained diff, stale evidence, unsupported closure claim, or any request for commit/push/merge/cleanup

**Steps:**
- [x] Step 1: Run focused analytics, benchmark, acceptance-state, and acceptance-verifier test suites — `74 passed`.
- [x] Step 2: Run final rebuild twice and compare material Gold digests — equal `9469602449d191c4c182244522bc8ed363693547b9ba15f7e814ce9406161307`.
- [x] Step 3: Inspect SQL execution and confirm operational SQLite/request-path isolation — six disposable Gold views pass; operational DB untouched.
- [x] Step 4: Run `skill-verification-before-completion`; record deviations, substitutions, blockers, and evidence paths — verified with approved runtime demotion.
- [x] Step 5: Keep P1-C and P2 explicitly deferred; dashboard remains out of scope.

**Verification:**
- [x] `python -m pytest -q tests/test_fitcv_analytics.py tests/test_benchmark_cv_efficiency.py tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py` — `74 passed`.
- [x] `python scripts/verify_fitcv_acceptance.py --timeout-seconds 300 --output .tmp/fitcv-acceptance-report.json` — passed.
- [x] `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output .tmp/acceptance_state.json` — passed.
- [x] Compare `.tmp/acceptance_state.json` with tracked `artifacts/acceptance_state.json` using normalized LF bytes — equal.
- [x] Run the analytics rebuild command twice against `tests/fixtures/analytics_semantic_contract.json` and compare material Gold digests — equal.
- [x] `git diff --check`
- Expected: fresh proof passes; all metrics trace through executable Bronze → Silver → Gold; JSON, Markdown, CI, and registry agree; no P1-C completion claim appears; no out-of-scope file changes exist.

**Exit Criteria:**
- `skill-verification-before-completion` returns `verified`; every task ledger item has accepted evidence; analytics convergence is proven; P1-C remains deferred; plan status may then be changed from `proposed`/`active` to `completed` by the lead controller only.

## Verification

Final artifact verification must establish:

- [x] `python -m pytest -q tests/test_fitcv_analytics.py tests/test_benchmark_cv_efficiency.py tests/test_acceptance_state.py tests/test_fitcv_cp/test_acceptance_verifier.py`
- [x] `python scripts/verify_fitcv_acceptance.py --timeout-seconds 300 --output .tmp/fitcv-acceptance-report.json`
- [x] `python scripts/render_acceptance_state.py --input config/acceptance_state.yaml --output .tmp/acceptance_state.json`
- [x] compare normalized `.tmp/acceptance_state.json` bytes with tracked `artifacts/acceptance_state.json`
- [x] deterministic analytics rebuild twice with equal material Gold digest
- [x] SQL projection smoke test against declared disposable analytics schema
- [x] `git diff --check`
- [x] `skill-verification-before-completion` returns `verified`

Source inspection, historical reports, or unchecked task boxes cannot close this
plan. Browser proof is not required because this sequence changes no frontend
behavior.

## Completion Criteria

The plan is ready for completion verification when:

1. every implementation outcome is satisfied
2. every task and task-local verification item is complete
3. Bronze preserves source history and Silver reconciles logical identities once
4. each Gold relation has one declared grain and explicit cohort/coverage semantics
5. acceptance state maps to `status_dimensions` and evidence registry records
6. benchmark, JSON, Markdown, CI, and registry consume canonical Gold values
7. SQL is executable against a declared projection schema or stale placeholders are removed
8. P1-C dashboard, trends, prioritization, and architecture expansion remain deferred
9. deviations, substitutions, blockers, and evidence paths are recorded
10. `skill-verification-before-completion` returns `verified`

This plan does not authorize acceptance-state promotion beyond the explicit R5
demotion, external API use, discard, cleanup of existing untracked scratch
files, or changes to the CV-generation request path. Git disposition follows
the user’s separate commit, push, PR, review, and merge authorization.
