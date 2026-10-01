---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-approved-p0-p1-finalization
targets:
  - pyproject.toml
  - .github/workflows/repo-hooks.yml
  - scripts/evaluate_p0b_source_job_relevance.py
  - scripts/validate_p0b_holdout_review.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/run_artifact_contracts.py
  - tests/test_p0b_source_job_relevance_evaluator.py
  - tests/test_p0b_holdout_review.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_fitcv_cp/test_run_artifact_contracts.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_mirror.py
  - tests/test_cv_render_acceptance.py
  - tests/fixtures/
  - docs/pipeline.md
  - docs/superpowers/evidence/2026-10-01-fitcv-approved-p0-p1-finalization.md
---

# FitCV Approved P0/P1 Finalization

## Goal

Finalize approved P0-A, P0-B, P0-C, P1-A, and P1-B claims from a clean,
reproducible evidence path. Keep P0-A rejected, preserve P0-C, defer P1-C and
P2, and do not change production defaults until P0-B passes its frozen gate.

## Verdict Review

The pasted verdict is substantially correct.

Accepted findings:

- CI and evaluator trust defects precede calibration or retrieval tuning.
- P0-B relevance and evidence-support decisions need independent gates.
- The `91` value is a false-negative count, not hard-negative false positives.
- Responsibility matching currently occurs after final selection, so selection
  cannot optimize for responsibility coverage.
- Direct support must remain stricter than candidate retrieval.
- Greedy minimal-cover selection plus bounded recovery fits current small pools.
- P0-A remains rejected; incumbent remains default.
- P0-C remains complete and unchanged.
- P1-A product behavior is complete; render acceptance reproducibility remains.
- P1-B lifecycle behavior is complete; efficiency claims remain unmeasured.

Plan corrections:

- Do not add an LLM verifier, vector service, graph, agent, or new retrieval
  backend. Reuse current deterministic support and selection paths.
- Do not add a second manually maintained acceptance ledger. Generate any
  summary from evaluator output and hashes; keep source artifacts authoritative.
- Do not block P0-B closure on a 20–30-sample P1-B efficiency study. Record the
  authorized single accepted-CV workload now; collect normal-use data later.
- Do not modify P0-A or P0-C product behavior while closing P0-B.

## Implementation Outcomes

### Trustworthy acceptance

Clean checkout CI runs ordinary tests without a native PDF toolchain. A
separate render-acceptance job installs pinned Pandoc, XeLaTeX, and Poppler,
then runs representative page-fit tests. Evaluator tests use explicit small
sanitized fixtures and fail closed on missing or malformed artifacts.

### Correct P0-B contract

P0-B emits independent relevance and evidence-support gates. Eligibility
requires complete review coverage, valid verdict vocabulary, valid evidence
references, supported-link recall, zero unsupported selected assignments, zero
qualifier contradictions, relevance thresholds, and validation success.

### Requirement-aware support and selection

Candidate retrieval stays broad. Deterministic direct-support assessment runs
before final selection, writes one verified support map, and feeds greedy
minimal-cover selection. Bounded recovery restores verified supporters only when
mandatory requirements remain uncovered.

### Reproducible closeout

P0-B calibration errors receive one primary stage bucket. Metric names and
reports derive from structured counters. P0-A hash references form one immutable
chain. One frozen holdout run decides promotion; production defaults remain
unchanged on failure.

### P1 acceptance evidence

P1-A receives reproducible render proof. P1-B receives one sanitized end-to-end
accepted-CV proof with persisted run, review action, regeneration or failure
path, final artifact, and timestamps. P1-C and P2 remain explicit deferrals.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect source and artifacts, edit listed files, add sanitized fixtures and regression tests, run declared local checks, and write evidence docs
- User-approval actions: push, merge, publication, external writes, destructive recovery, cleanup, dependency installation outside CI configuration, and production-default changes
- Parallel ownership: `none`
- Sequential fallback: complete each task and accept its proof before starting the next task

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `9a0b8fe7`
- Expected workspace: `preserve existing untracked user artifacts; no unrelated edits`
- Next action: `Task 3 — normalize metrics and provenance`
- Blockers: `support-recall threshold approval required before P0-B promotion`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | CI workflow and focused tests prove clean-checkout behavior | 2962 passed, 4 skipped, 3 deselected; render 3 passed |
| Task 2 | `completed` | current | `codex` | Task 1 | evaluator fail-closed tests pass | 15 passed; CLI exit 1 with support gate blocked |
| Task 3 | `active` | current | `codex` | Task 2 | metric/provenance tests pass and reports reconcile | active |
| Task 4 | `pending` | current | `codex` | Task 3 | calibration decomposition covers every error | pending |
| Task 5 | `pending` | current | `codex` | Task 4 | direct-support regression tests pass | pending |
| Task 6 | `pending` | current | `codex` | Task 5 | selection and recovery tests pass | pending |
| Task 7 | `pending` | current | `codex` | Task 6 | frozen holdout gate is evaluated once | pending |
| Task 8 | `pending` | current | `codex` | Task 7 | P1-A/P1-B acceptance evidence and final verification pass | pending |

## Task Breakdown

### Task 1: Restore clean-checkout CI acceptance

**Purpose:**
- Remove false-green and environment-dependent acceptance from ordinary Full Suite.
- Prove P0-B artifacts use explicit sanitized fixture paths.

**Task Function:**
- CI trust-plane repair and test-boundary separation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded CI/test edits; correctness risk is observable locally.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused tests plus workflow inspection.

**Specification Coverage:**
- No large private/raw artifacts in tracked tests.
- Missing native render tools cannot pass a required render check by accident.
- Full Suite has no Pandoc/XeLaTeX/Poppler dependency.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `.github/workflows/repo-hooks.yml:full-suite`
- Modify: `pyproject.toml:[tool.pytest.ini_options]` marker registration
- Inspect: `tests/test_cv_render_acceptance.py:_render_pdf`
- Modify: `.github/workflows/repo-hooks.yml`
- Modify: `tests/test_cv_render_acceptance.py`
- Modify: `tests/fixtures/` only for small sanitized render fixtures when needed
- Verify: clean-checkout workflow commands and focused pytest targets

**Dependencies:**
- Current `main` checkout and committed P0-B corpus files.

**Authority:**
- Preauthorized local actions: edit workflow/test boundaries, add small sanitized fixtures, and run focused tests.
- Stop for: raw/private artifact tracking, production-default changes, external service setup, or unresolved toolchain ownership.

**Steps:**
- [x] Step 1: Register `render_acceptance` in `pyproject.toml`, mark render tests, and exclude them from ordinary Full Suite.
- [x] Step 2: Add required `ubuntu-24.04` render-acceptance job using `pandoc`, `texlive-xetex`, `texlive-fonts-recommended`, `texlive-plain-generic`, and `poppler-utils`; print `pandoc --version`, `xelatex --version`, `pdfinfo -v`, and `pdftotext -v`; run the marked cases.
- [x] Step 3: Verify no render test is silently skipped or falsely green.

**Verification:**
- [x] `python -m pytest -q tests/test_cv_render_acceptance.py -m "not render_acceptance"` — 3 deselected
- [x] `python -m pytest -q -m "not render_acceptance"` — 2962 passed, 4 skipped, 3 deselected
- [x] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance` — 3 passed
- [x] Workflow YAML parse and `git diff --check`
- Expected: focused and ordinary suites pass without native PDF tools.

**Exit Criteria:**
- Full Suite no longer owns native PDF installation; render acceptance has separate required proof.

### Task 2: Repair P0-B evaluator eligibility

**Purpose:**
- Make incomplete, unsupported, or structurally invalid evidence reviews fail closed.

**Task Function:**
- Evaluator contract hardening.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: high correctness risk; exact existing evaluator boundaries available.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: controlled fixtures cover empty, partial, invalid, unsupported, and valid reviews.

**Specification Coverage:**
- Approved P0-B gate v1 from `docs/superpowers/evidence/2026-09-30-fitcv-p0-p1-approval-decision.md`.
- Separate relevance gate and evidence-support gate.
- Support-recall threshold is an external approval prerequisite. Do not invent
  or infer it from the held-out result.

**Required Skills:**
- `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `scripts/evaluate_p0b_source_job_relevance.py:evaluate_actual_fitcv`
- Inspect/modify: `scripts/evaluate_p0b_source_job_relevance.py:_evaluate_selected`
- Inspect/modify: `scripts/validate_p0b_holdout_review.py:validate_review_payload`
- Modify: `tests/fixtures/` with small sanitized evaluator fixtures when current production defaults are not clean-checkout safe
- Modify: `tests/test_p0b_source_job_relevance_evaluator.py`
- Modify: `tests/test_p0b_holdout_review.py`
- Verify: `data/fitcv-p0-corpus/p0b/` review and freeze manifests

**Dependencies:**
- Task 1 fixture-path and clean-checkout proof.

**Authority:**
- Preauthorized local actions: edit evaluator logic/tests and emit deterministic diagnostics from existing artifacts.
- Stop for: changing approved thresholds, fabricating labels, accepting incomplete review data, or changing production retrieval.

**Steps:**
- [x] Step 1: Record an approved support-recall threshold in the approval decision before implementation. Define denominator as authoritative rows with `support_verdict == "supported"`; zero denominator fails closed and cannot produce eligibility. Threshold remains externally unapproved, so promotion stays blocked.
- [x] Step 2: Require review row count and requirement ID set to equal the canonical fixture set.
- [x] Step 3: Require verdicts in `supported | unsupported | unknown`; require evidence only for supported rows; validate accepted IDs against the canonical projection and requirement/source identity.
- [x] Step 4: Treat `selected_evidence_ids` in the review as historical diagnostic metadata, not current-selection truth; accepted gold IDs remain immutable when selection changes.
- [x] Step 5: Make evaluator tests pass fixture paths explicitly and replace return-code-only assertions with parsed report and gate assertions.
- [x] Step 6: Add support-gate fields for supported-link recall, unsupported selected assignments, qualifier contradictions, invalid verdicts, accepted-pair integrity, and zero-denominator handling.
- [x] Step 7: Compute `eligible = relevance_gate.passed and support_gate.passed and validation.passed`.
- [x] Step 8: Add controlled tests for empty review, partial review, unsupported selected evidence, invalid vocabulary, changed current selection with unchanged gold, zero supported rows, and valid review.

**Verification:**
- [x] `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_p0b_holdout_review.py` — 15 passed
- [x] `python scripts/evaluate_p0b_source_job_relevance.py --output .tmp/p0b-task2-evaluation.json` — exit 1; support threshold unapproved and unsupported assignments explicit
- Expected: every controlled defect fails eligibility; valid complete review preserves eligibility.

**Exit Criteria:**
- Structural cleanliness alone cannot produce eligibility; missing threshold approval remains explicitly not promotable.

### Task 3: Normalize metrics and provenance

**Purpose:**
- Remove ambiguous counters, manual summaries, and hash drift before optimization.

**Task Function:**
- Measurement contract and evidence-chain repair.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded report/schema changes with direct regression coverage.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: named counters and byte-level hashes are mechanically testable.

**Specification Coverage:**
- False negatives and hard-negative false positives remain distinct.
- Reports derive Markdown/evidence summaries from structured counters.
- P0-A v4 provenance remains immutable and internally consistent.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect/modify: `scripts/evaluate_p0b_source_job_relevance.py:_evaluate_selected`
- Inspect/modify: `scripts/benchmark_requirement_support.py:_aggregate_scenario_metrics`
- Inspect/modify: `scripts/compare_requirement_support.py`
- Verify: `data/fitcv-p0-corpus/p0a/` v4 manifest, score, and frozen-gate artifacts
- Verify: `docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md`

**Dependencies:**
- Task 2 evaluator contract.

**Authority:**
- Preauthorized local actions: rename/report counters, add structured output fields, repair generated references, and update regression tests/docs.
- Stop for: rewriting historical v3 artifacts, changing P0-A thresholds, or adding a second manual acceptance SSOT.

**Steps:**
- [x] Step 1: Emit named totals for relevant, borderline, irrelevant, true-positive, false-negative, hard-negative false-positive, and incorrect-pair counts.
- [x] Step 2: Generate summaries from those fields; remove hand-entered counter claims.
- [x] Step 3: Validate every referenced P0-A artifact hash from committed bytes and preserve v3 as historical.
- [x] Step 4: If a single machine-readable acceptance summary is still missing, derive one from evaluator outputs; do not hand-edit it.

**Verification:**
- [x] `python -m pytest -q tests/test_compare_requirement_support.py tests/test_benchmark_requirement_support.py tests/test_p0b_source_job_relevance_evaluator.py`
- Expected: counters reproduce reports; P0-A hash chain resolves without mismatch.

**Exit Criteria:**
- No acceptance decision relies on ambiguous names, manually transcribed counts, or stale artifact hashes.

### Task 4: Produce calibration-only P0-B loss decomposition

**Purpose:**
- Classify each calibration miss or false assignment before changing thresholds or retrieval.

**Task Function:**
- Stage attribution and bounded diagnosis.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: diagnostic-only work; no product behavior change.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: every error must map to one primary bucket.

**Specification Coverage:**
- Buckets: `not_in_pool`, `in_pool_not_support_candidate`, `false_support_candidate`, `support_candidate_not_selected`, `selected_not_assigned`, `assigned_false_positive`, `qualifier_failure`.

**Required Skills:**
- `skill-systematic-debugging`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py:run_benchmark`
- Inspect: `src/fitcv/evidence.py:retrieve_evidence_bundle`
- Modify: benchmark diagnostic output/tests only
- Verify: calibration fixture and output hashes

**Dependencies:**
- Tasks 2 and 3.

**Authority:**
- Preauthorized local actions: add diagnostic classification and tests without changing production thresholds or defaults.
- Stop for: tuning before classification, expanding pool size globally, or using held-out rows for diagnosis.

**Steps:**
- [x] Step 1: Trace canonical evidence through pool, candidate set, support map, selected set, and assignment.
- [x] Step 2: Assign exactly one primary bucket to each missed or false pair.
- [x] Step 3: Emit counts by source group and requirement type.

**Verification:**
- [x] Calibration diagnostic reports zero unclassified errors and zero held-out rows consumed.
- Expected: next implementation task has a measured failure distribution.

**Exit Criteria:**
- Every calibration error has a reproducible stage owner.

### Task 5: Add deterministic direct responsibility support

**Purpose:**
- Stop lexical retrieval similarity from acting as proof of responsibility support.

**Task Function:**
- Root-cause support verification.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: reuse existing qualifier-aware deterministic support pattern.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: targeted false-positive and qualifier regression cases.

**Specification Coverage:**
- Broad relevance remains candidate discovery.
- Strict direct support is fail-closed and feeds final coverage.
- No second retrieval service or LLM verifier.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/evidence.py:_responsibility_support_map`
- Inspect/modify: `src/fitcv/evidence.py:_assess_requirement_support`
- Inspect/modify: `src/fitcv/evidence.py:_build_support_fragments`
- Inspect/modify: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Modify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, benchmark fixture tests

**Dependencies:**
- Task 4 failure distribution; P0-C qualifier behavior remains unchanged.

**Authority:**
- Preauthorized local actions: change responsibility support assessment, shared feature preparation, and focused tests.
- Stop for: merging responsibility semantics into skill qualifiers, weakening P0-C checks, adding model calls, or changing retrieval defaults.

**Steps:**
- [x] Step 1: Normalize requirement and evidence features once per bundle.
- [x] Step 2: Require responsibility-specific direct support rather than token overlap alone.
- [x] Step 3: Preserve source-fragment boundaries and fail closed on ambiguous or contradictory qualifiers.
- [x] Step 4: Extend `_build_requirement_coverage` to consume responsibility support using stable source requirement IDs and the existing coverage status contract; do not create a second support authority.
- [x] Step 5: Add Kubernetes/production-schedule and equivalent hard-negative regressions, including responsibility-only input reaching final `requirement_coverage`.

**Verification:**
- [x] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py`
- Expected: hard negatives do not become support; existing P0-C qualifier cases remain green.

**Exit Criteria:**
- Responsibility support map contains only directly verified pairs, and verified responsibility support reaches final `requirement_coverage`.

### Task 6: Move verified support before selection and add bounded recovery

**Purpose:**
- Let selection optimize verified requirement coverage without increasing global `top_k`.

**Task Function:**
- Selection correctness and bounded recovery.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: current greedy selector already exists; change its input authority only.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: small deterministic pools make coverage and tie breaks inspectable.

**Specification Coverage:**
- One support map feeds selection and `requirement_coverage`.
- Current selection changes cannot invalidate immutable gold evidence links.
- Greedy score favors new verified mandatory requirements, then support strength,
  context cost, existing score, and evidence ID.
- Recovery restores only verified supporters from the merged pool.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect/modify: `src/fitcv/evidence.py:_EvidenceSelectionEngine.run`
- Inspect/modify: `src/fitcv/evidence.py:_select_final_evidence`
- Inspect/modify: `src/fitcv/evidence.py:_coverage_gain`
- Inspect/modify: `src/fitcv/evidence.py:retrieve_evidence_bundle`
- Verify: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Modify: `tests/test_evidence.py`, benchmark tests

**Dependencies:**
- Task 5 direct-support map.

**Authority:**
- Preauthorized local actions: reorder support annotation and selection, add bounded recovery, and add focused tests.
- Stop for: global pool expansion, generic set-cover framework, unbounded recovery, or requirement-support duplication.

**Steps:**
- [x] Step 1: Annotate merged candidates with verified responsibility support before final selection.
- [x] Step 2: Include verified coverage gain in deterministic greedy selection.
- [x] Step 3: Recover best verified supporter only for uncovered mandatory requirements.
- [x] Step 4: Emit one support map for canonical, pool, selected, and recovered evidence; preserve accepted gold links separately from historical selected snapshots.

**Verification:**
- [x] Test a case where a valid supporter is outside current top-ranked item but inside merged pool.
- [x] Test no supporter case remains `unknown` rather than fabricated support.
- Expected: coverage improves without increasing configured global pool size.

**Exit Criteria:**
- Selection and final requirement coverage use one verified support authority.

### Task 7: Freeze and evaluate P0-B holdout once

**Purpose:**
- Decide P0-B promotion using approved thresholds and protected reviewed data.

**Task Function:**
- Final benchmark execution and promotion decision.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: one bounded final run after code/config freeze.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: fresh artifact/hash inspection and gate recomputation.

**Specification Coverage:**
- Selected requirement recall `>= 0.80`.
- Minimum source-group recall `>= 0.60`.
- Incorrect pairs `0`.
- Hard-negative false positives `0`.
- Validation `100%`.
- Protected holdout has `>=100` independently reviewed pairs across `>=20` source groups and freezes before rerun.
- Qualifying package: `data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json`, `p0b_source_job_review_packet_v2_human_adjudicated.json`, and `p0b_source_job_source_group_map_v2.json`; the 170-row source-backed benchmark fixture is diagnostic only and cannot satisfy this gate.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Verify: `scripts/evaluate_p0b_source_job_relevance.py:evaluate_documents`
- Verify: `scripts/evaluate_p0b_source_job_relevance.py:evaluate_actual_fitcv`
- Verify: `scripts/validate_p0b_holdout_review.py`
- Verify: `data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json`
- Verify: `data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json`
- Verify: `data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json`
- Write: `docs/superpowers/evidence/2026-10-01-fitcv-approved-p0-p1-finalization.md`

**Dependencies:**
- Tasks 1–6 complete; code and config frozen; qualifying review package has independently verified reviewer provenance and meets the required threshold.

**Authority:**
- Preauthorized local actions: run one frozen holdout evaluation and write its evidence record.
- Stop for: fewer than `100` reviewed pairs, fewer than `20` source groups, missing independent review, holdout mutation, threshold changes, or any production promotion without a passing gate.

**Steps:**
- [x] Step 1: Verify the qualifying fixture, packet, group map, reviewer provenance, `212` requirement rows, `25` source groups, and hashes. Independent reviewer identity is not verified, so record `not_promotable`; do not promote.
- [x] Step 2: Run production arm once with declared code, policy, fixture, and script hashes.
- [x] Step 3: Recompute both gates and record pass/fail with all blockers.
- [x] Step 4: Keep production defaults unchanged if any gate fails.

**Verification:**
- [x] `python scripts/evaluate_p0b_source_job_relevance.py --fixture data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json --packet data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json --group-map data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json --projection data/fitcv-p0-corpus/p0b/p0b_source_job_candidate_pool_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --policy config/policy/cv_analysis.yaml --output .tmp/p0b-final-evaluation.json` — exits `1` as required for ineligible result.
- [x] Validate output against package hashes and reviewer-provenance requirements; result is `not_promotable` because reviewer identity is unverified and support threshold is absent.
- Expected: one immutable result decides P0-B; no tuning follows from holdout output.

**Exit Criteria:**
- P0-B is either promoted with all gates passing or explicitly retained as failed/not promotable.

### Task 8: Close P1-A/P1-B and publish final status

**Purpose:**
- Reconcile P0/P1 status with fresh acceptance evidence without overstating benefit.

**Task Function:**
- Product-flow acceptance and final evidence reconciliation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing acceptance scripts and lifecycle contracts; no new workflow machinery.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: native render output and persisted accepted-CV artifact inspection.

**Specification Coverage:**
- P1-A runtime invariant is rendered page count `<= 1`, not universal guarantee.
- P1-B proof includes persisted run, review action, regeneration or failure path,
  final artifact, and timestamps.
- P1-C and P2 remain deferred.

**Required Skills:**
- `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Verify: `tests/test_cv_render_acceptance.py`
- Verify: `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`
- Verify: `tests/test_fitcv_cp/test_run_artifact_contracts.py`
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_run_artifact_mirror.py`
- Verify: `.tmp/p1b-approved-workload/` sanitized evidence snapshot
- Update: `docs/pipeline.md`
- Write: `docs/superpowers/evidence/2026-10-01-fitcv-approved-p0-p1-finalization.md`

**Dependencies:**
- Task 7 decision; render job proof from Task 1.

**Authority:**
- Preauthorized local actions: run sanitized local acceptance, update status/evidence docs, and reconcile documentation.
- Stop for: private data publication, production-default changes, or claims based on one sample as an efficiency result.

**Steps:**
- [x] Step 1: Run required render-acceptance cases and record page counts and artifact hashes.
- [x] Step 2: Verify approved sanitized workload `p1b-approved-sanitized-001` under `.tmp/p1b-approved-workload/`: persisted SQLite snapshot, `regenerate_once`, `approve_as_is`, `cv_regenerate_once_requested`, finalized artifact version, timestamps, and `accepted_cv_effort_v1` with accepted denominator `1`.
- [x] Step 3: Update status matrix: P0-A rejected, P0-B `not_promotable`, P0-C accepted, P1-A accepted with render proof, P1-B functional with sample count, P1-C/P2 deferred.
- [x] Step 4: Record future P1-B measurement as follow-up only; do not optimize before normal-use data exists.

**Verification:**
- [x] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- [x] `python -m pytest -q tests/test_fitcv_cp/test_run_artifact_contracts.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_pipeline_agentic_late_stage.py`
- [x] Inspect `.tmp/p1b-approved-workload/` and verify run `p1b-approved-sanitized-001`, review actions, final artifact, timestamps, and accepted denominator `1` from `build_accepted_cv_effort_projection` over persisted SQLite compatibility data.
- [x] `git diff --check`
- Expected: final evidence matches source, tests, hashes, and explicit deferrals.

**Exit Criteria:**
- P0/P1 claims are current, source-backed, and reproducible; no required task or acceptance blocker is hidden.

## Verification

- `python -m pytest -q -m "not render_acceptance"`
- `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py tests/test_p0b_holdout_review.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py`
- `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- Exact approved P0-B evaluator command from Task 7 against qualifying fixture, packet, group map, projection, review, and policy.
- Exact P1-B contract test command and sanitized workload inspection from Task 8.
- `git diff --check`
- Final inspection of `git status --short`, changed-file scope, generated outputs, hashes, and evidence doc.

## Completion Criteria

The plan is ready for completion verification when:

1. clean-checkout CI separates ordinary tests from native render acceptance
2. P0-B evaluator fails closed on incomplete, invalid, unsupported, or contradictory evidence reviews
3. counters, reports, and P0-A provenance reconcile from structured artifacts
4. calibration diagnostics classify every observed error without consuming holdout rows
5. direct responsibility support is strict and feeds selection before final coverage
6. minimal-cover selection and bounded recovery pass focused regression tests
7. one protected holdout run records an explicit P0-B pass or failure with no automatic promotion on failure
8. P1-A and P1-B acceptance evidence is fresh and sanitized
9. P0-C behavior remains green; P1-C and P2 remain explicit deferrals
10. final verification finds no unrelated edits, stale generated surfaces, failed required checks, or unrecorded scope deviation

Plan status becomes `completed` only after `skill-verification-before-completion`
returns `verified`. No commit, merge, push, publication, or cleanup is part of
this plan.
