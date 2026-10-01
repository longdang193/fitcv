---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
contract_version: "1"
name: fitcv-final-p0-p1-closure
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - scripts/evaluate_p0b_source_job_relevance.py
  - scripts/build_p0b_holdout_benchmark_fixture.py
  - scripts/validate_p0b_holdout_review.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - .github/workflows/repo-hooks.yml
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_p0b_source_job_relevance_evaluator.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_p0_public_corpus.py
  - tests/test_cv_render_acceptance.py
  - tests/fixtures/p0b/
  - data/fitcv-p0-corpus/p0a/
  - docs/pipeline.md
  - docs/superpowers/evidence/2026-10-01-fitcv-final-p0-p1-closure.md
---

# FitCV Final P0/P1 Closure

## Goal

Close approved P0 and P1 work from a trustworthy, clean-checkout evidence path.
Keep P0-A rejected, keep P0-C behavior protected, repair P0-B trust boundaries
before any retrieval tuning, close P1-A CI acceptance, record P1-B as measured
plumbing only, and keep P1-C/P2 deferred.

## Verdict Review

The verdict is materially correct on six blockers:

- responsibility lexical overlap can cross the verified-support boundary;
- evaluator validation errors and invalid qualifier vocabulary do not fully
  fail the support gate;
- recovery can evict more verified coverage than it adds and skips free slots;
- ordinary CI depends on non-committed P0-B artifacts, and Render Acceptance
  mixes Bash syntax into a PowerShell workflow step;
- P0-A nested artifact references still contain stale score hashes;
- calibration `by_requirement_type` counts whole buckets instead of pairs and
  leaves some named buckets unused.

Repository correction:

- responsibility support is annotated before final selection in
  `retrieve_evidence_bundle`; the fix is strict proof semantics and one shared
  authority, not moving responsibility matching earlier;
- P0-A top-level committed hashes match their files, but
  `p0a-v4-frozen-gate.json` and `p0a-v4-multilingual-final.json` still declare
  `9036fb4e...` for the score artifact whose committed hash is
  `d547cec8...`; nested lineage remains broken;
- P1-B does not need a 20–30-sample study for closure. Current evidence may
  claim only that measurement plumbing works at `n=1`.

Non-goals:

- no new embedding backend, reranker, LLM verifier, graph, agent, service, or
  datastore;
- no P0-A retrieval rerun or production-default change;
- no P0-C product redesign;
- no P1-C or P2 implementation;
- no private corpus publication.

## Implementation Outcomes

### Trust-boundary correctness

Responsibility support returns candidate, action, object, qualifier, and
contradiction state. Only strict verified support enters the authoritative
requirement-support map and `requirement_coverage`.

### Fail-closed P0-B evaluation

Evaluation validates pair-level assignments, review vocabulary, source identity,
accepted evidence references, unsupported assignments, qualifier contradictions,
and complete review coverage. Any validation error makes eligibility false.

### Monotonic selection and diagnostics

Final selection uses verified requirement coverage in its existing bounded pool.
Recovery never lowers verified coverage, uses free capacity, and calibration
assigns every error pair to exactly one stage bucket.

### Reproducible acceptance

Clean checkout ordinary CI uses committed sanitized fixtures. Render Acceptance
uses one consistent shell and native PDF tools. P0-A nested hashes pass an
integrity test. P0-B runs one protected holdout only after corrected calibration
and gates pass.

### P1 evidence boundary

P1-A has fresh green CI proof. P1-B has one sanitized accepted-CV projection
with persisted run, review, regeneration, final artifact, and timestamps.
No efficiency claim is made from one sample.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-writing-plans`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `verified per-task checkpoint commits preauthorized`; no merge or push
- Preauthorized local actions: inspect source and committed artifacts, edit listed files, add sanitized fixtures and regression tests, run declared local checks, create declared checkpoint commits, and write evidence docs
- User-approval actions: push, merge, publication, external writes, destructive recovery, cleanup, dependency installation outside declared CI steps, and production-default changes
- Parallel ownership: none; `src/fitcv/evidence.py`, evaluator scripts, fixtures, workflow, and evidence are serialized
- Sequential fallback: execute Tasks 1–8 in order; stop at each exit gate before continuing

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `27e715f5784f63615dcd67bcfdfb7e29617576e0`
- Expected workspace: `main` at base commit with existing untracked files preserved and excluded from all changes: `.tmp/`, `.venv/`, `HEAD_raw.jsonl`, `HEAD_v2.json`, `INDEX_v2.json`, `check.py`, `check2.py`, `check3.py`, `check4.py`, `find2.py`, `find_distractors.py`, `old_raw.jsonl`, `scan.py`, `script.py`, `script2.py`, `script3.py`, `v2_source_ids.txt`, `data/LONG DANG - BACHELOR DEGREE.private-compressed.pdf`, `data/linkedin-2026-09-29-16-10-19.json`, and `data/linkedin-2026-10-01-00-26-29.json`
- Next action: preserve Task 1 checkpoint; keep P0-B retrieval gate blocked
- Blockers: none

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | strict support regression suite | `124 passed`; accepted-link recall `1.0`; P0-B retrieval gate remains blocked |
| Task 2 | `pending` | current | `unresolved` | Task 1 | pair-level fail-closed evaluator suite | pending |
| Task 3 | `pending` | current | `unresolved` | Task 1 | monotonic selection/recovery suite | pending |
| Task 4 | `pending` | current | `unresolved` | Task 2 | clean-checkout fixture and CI tests | pending |
| Task 5 | `pending` | current | `unresolved` | none | nested P0-A hash integrity test | pending |
| Task 6 | `pending` | current | `unresolved` | Tasks 2–3 | one-bucket-per-pair calibration suite | pending |
| Task 7 | `pending` | current | `unresolved` | Tasks 1–6 | corrected calibration report and one bounded P0-B patch or explicit stop | pending |
| Task 8 | `pending` | current | `unresolved` | Task 7 | protected holdout, P1 proof, final evidence, full verification | pending |

## Task Breakdown

### Task 1: Enforce strict responsibility proof

**Purpose:**
- Prevent lexical fragments from becoming verified responsibility support.

**Task Function:**
- Implement deterministic fragment-level responsibility assessment using existing
  tokenization, canonical terms, qualifier concepts, and negation handling.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: resolve through Planning Dispatch before activation; task is
  bounded but crosses retrieval and coverage authority.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independently validate contradiction, qualifier, and object/action boundaries.

**Specification Coverage:**
- Candidate match must not imply verified support.
- Negated or incomplete action/object/qualifier evidence cannot support a requirement.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_responsibility_support_map`, `_support_fragments`, `_tokenize`
- Inspect: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Modify: `src/fitcv/evidence.py:_responsibility_support_map` and one local proof helper owned by that module
- Modify: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`

**Dependencies:**
- Existing source fragments and qualifier/negation helpers remain canonical.

**Authority:**
- Preauthorized local actions: edit responsibility support and coverage authority plus focused tests.
- Stop for: new verifier service, new model dependency, changed production defaults, or unresolved requirement semantics.

**Steps:**
- [x] Step 1: Extend responsibility assessment with deterministic proof aliases over evidence text and canonical evidence metadata; require action/object proof, mandatory context qualifiers, and negation rejection.
- [x] Step 2: Require `verified_support` before adding responsibility IDs to `supported_requirement_ids`, pool support, or selected support; contradiction wins over partial positive matches.
- [x] Step 3: Preserve diagnostic candidate information without allowing it to produce `selected_support == "verified"`.
- [x] Step 4: Add regressions for accepted equivalent proof, negated Kubernetes production experience, SQL dashboards versus SQL pipelines, advanced-office overreach, master-versus-bachelor mismatch, and missing qualifiers.

**Verification:**
- [x] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_p0b_source_job_relevance_evaluator.py`
- Result: `124 passed`; accepted-link support recall `1.0` under approved threshold `0.8`; full P0-B eligibility remains false because retrieval gates fail.

**Exit Criteria:**
- Responsibility path maps reviewed equivalent proof without bypassing negation, mandatory qualifiers, object specificity, or false-positive gates.

### Task 2: Make P0-B evaluation pair-level and fail closed

**Purpose:**
- Make evaluator status, gates, and eligibility agree on every invalid input.

**Task Function:**
- Replace requirement-level support acceptance with actual/ground-truth pair
  accounting while preserving unknown rows as unjudged.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent script/test task with high correctness risk.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: validate malformed review rows and extra assigned links.

**Specification Coverage:**
- Supported: `TP = A ∩ G`, `FP = A - G`, `FN = G - A`.
- Unsupported rows have empty gold support.
- Unknown rows do not invent gold support.
- Any validation error makes `support_gate.passed` and `eligible` false.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:validate_inputs`, `_evaluate_selected`, `evaluate_evidence_link_review`, `evaluate_actual_fitcv`
- Modify: `scripts/evaluate_p0b_source_job_relevance.py`
- Verify: `tests/test_p0b_source_job_relevance_evaluator.py`

**Dependencies:**
- Task 1 defines the support authority consumed by actual FitCV evaluation.

**Authority:**
- Preauthorized local actions: edit evaluator logic and committed sanitized evaluator tests.
- Stop for: changing frozen thresholds, changing reviewer identity policy, or treating unknown as negative without protocol evidence.

**Steps:**
- [ ] Step 1: Validate complete review vocabulary, including allowed qualifier values and required row fields; malformed ground-truth review rows make the CLI return exit code `1` before candidate evaluation.
- [ ] Step 2: Build actual and accepted evidence-pair sets per requirement and report pair precision, pair recall, false positives, and missed pairs.
- [ ] Step 3: Make `support_gate.passed` require `not validation_errors` plus every existing gate and pair-level thresholds.
- [ ] Step 4: Make `eligible` require input validation, clean review status, relevance gates, and support gates.
- [ ] Step 5: Add tests for source mismatch, invalid qualifier, accepted-plus-extra assignment, unsupported assignment, and unknown assignment.

**Verification:**
- [ ] `python -m pytest -q tests/test_p0b_source_job_relevance_evaluator.py`
- Expected: every invalid case reports `status == "invalid"`, `support_gate.passed is False`, and `eligible is False`.

**Exit Criteria:**
- No validation error can coexist with a passing support gate.

### Task 3: Make selection and recovery monotonic

**Purpose:**
- Prevent recovery from lowering verified requirement coverage or wasting free capacity.

**Task Function:**
- Use existing verified support IDs to select a bounded greedy minimal-cover set and
  retain only replacements with non-negative whole-selection coverage delta.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: bounded algorithm change in one module with direct regression proof.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: validate eviction counterexamples and tie-break determinism.

**Specification Coverage:**
- `verified_coverage_after >= verified_coverage_before` for every change.
- Add uncovered supporters when `len(selected) < top_k`.
- Full selection is scored against mandatory coverage, confidence, relevance, cost, and ID tie-breaks.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_coverage_gain`, `_select_final_evidence`, `_recover_verified_supporters`, `_EvidenceSelectionEngine.run`
- Modify: `src/fitcv/evidence.py:_select_final_evidence`, `_recover_verified_supporters`, and local coverage helpers
- Verify: `tests/test_evidence.py`

**Dependencies:**
- Task 1 supplies strict verified support IDs.

**Authority:**
- Preauthorized local actions: edit selection/recovery and focused tests without changing configured pool size or production defaults.
- Stop for: new selection service, unbounded search, or threshold retuning.

**Steps:**
- [ ] Step 1: Define whole-selection verified coverage from `supported_requirement_ids`.
- [ ] Step 2: Rank candidates by newly covered verified requirements, then mandatory coverage, support confidence, base score, context cost, and evidence ID.
- [ ] Step 3: Fill free capacity before considering replacement.
- [ ] Step 4: For full selections, accept a replacement only when net new verified coverage is positive or same-coverage tie-break quality improves deterministically.
- [ ] Step 5: Preserve recovery IDs and selection diagnostics.
- [ ] Step 6: Add a multi-coverage eviction regression and a free-slot recovery regression.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Expected: selected verified coverage never decreases across recovery cases.

**Exit Criteria:**
- Selection is bounded, deterministic, and monotonic on verified requirement coverage.

### Task 4: Remove clean-checkout CI dependencies

**Purpose:**
- Make ordinary and render CI jobs reproducible without private ignored artifacts.

**Task Function:**
- Separate small committed sanitized fixtures from explicit full acceptance corpus paths and fix render shell consistency.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: CI/configuration task with deterministic fixture ownership.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: validate fresh checkout behavior.

**Specification Coverage:**
- Ordinary suite passes with committed fixtures only.
- Render Acceptance installs native PDF tools and runs with one shell.
- CLI failure test proves rejection rather than crash.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `.github/workflows/repo-hooks.yml:full-suite`, `.github/workflows/repo-hooks.yml:render-acceptance`
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:DEFAULT_*`, `scripts/build_p0b_holdout_benchmark_fixture.py`, `scripts/validate_p0b_holdout_review.py`, `tests/test_p0b_source_job_relevance_evaluator.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_p0b_holdout_benchmark_adapter.py`, `tests/test_p0b_holdout_review.py`
- Add: `tests/fixtures/p0b/source_job_relevance_fixture.json`, `tests/fixtures/p0b/source_job_review_packet.json`, `tests/fixtures/p0b/source_group_map.json`, `tests/fixtures/p0b/evidence_link_review.csv`, plus synthetic adapter/review-validator fixtures built by test-local helpers
- Modify: `scripts/evaluate_p0b_source_job_relevance.py`, `scripts/build_p0b_holdout_benchmark_fixture.py`, `scripts/validate_p0b_holdout_review.py`, `tests/test_p0b_source_job_relevance_evaluator.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_p0b_holdout_benchmark_adapter.py`, `tests/test_p0b_holdout_review.py`, and `.github/workflows/repo-hooks.yml`

**Dependencies:**
- Task 2 defines evaluator failure semantics.

**Authority:**
- Preauthorized local actions: add sanitized fixtures, pass explicit fixture paths, edit workflow shell, and run clean-checkout-equivalent tests.
- Stop for: committing private review packets, personal documents, ignored corpus files, or changing acceptance thresholds.

**Steps:**
- [ ] Step 1: Create minimal deterministic fixtures containing only sanitized requirement, evidence, review, and group-map rows needed by tests.
- [ ] Step 2: Change tests and evaluator calls to pass fixture paths explicitly; remove reliance on repository-local ignored defaults.
- [ ] Step 3: Strengthen CLI rejection assertions to require report existence, valid JSON, validation output, failed eligibility, expected gate, reason/counter, and exit code `1`.
- [ ] Step 4: Set `shell: bash` on the Ubuntu render job and keep PowerShell syntax only in Windows jobs.
- [ ] Step 5: Capture `git status --porcelain=v1 --ignored`, create a checkpoint commit containing only declared files, run ordinary and render jobs from a disposable checkout of that commit, and compare post-run status to the protected-path baseline.

**Verification:**
- [ ] `git status --porcelain=v1 --ignored`
- [ ] `python -m pytest -q -m "not render_acceptance"`
- [ ] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- Expected: ordinary suite and three render acceptance tests pass from committed sanitized inputs; protected untracked/private paths remain unchanged and tests do not read or write them.

**Exit Criteria:**
- CI passes from committed files plus declared native tool installation only.

### Task 5: Repair and test P0-A nested provenance

**Purpose:**
- Make every P0-A artifact reference resolve to its committed bytes.

**Task Function:**
- Regenerate stale nested score hashes from canonical artifact bytes and extend the existing public corpus integrity test.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: deterministic artifact repair with no product behavior change.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent hash-chain verification.

**Specification Coverage:**
- Manifest, candidate report, frozen gate, and score artifact agree on path and SHA-256.
- P0-A remains `evaluated_not_promoted` with incumbent defaults.

**Required Skills:**
- `skill-backend-verification`

**Files And Symbols:**
- Modify: `data/fitcv-p0-corpus/p0a/p0a-v4-frozen-gate.json`, `data/fitcv-p0-corpus/p0a/p0a-v4-multilingual-final.json`, `data/fitcv-p0-corpus/p0a/impact_measure_corpus_manifest_v4.json`, and the maintained P0-A closeout hash table in `docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md`
- Verify: `data/fitcv-p0-corpus/p0a/impact_measure_corpus_manifest_v4.json`, `tests/test_p0_public_corpus.py`, `docs/superpowers/evidence/2026-09-29-fitcv-p0-p1-acceptance-closeout.md`

**Dependencies:**
- None; no rerun or tuning.

**Authority:**
- Preauthorized local actions: update only deterministic SHA-256 fields and add nested integrity assertions.
- Stop for: score changes, fixture changes, reruns, promotion, or production-default changes.

**Steps:**
- [ ] Step 1: Replace stale nested `score_artifact_sha256` values with the committed score artifact hash.
- [ ] Step 2: Recompute `benchmark_reports.multilingual.sha256` and `benchmark_reports.frozen_gate.sha256` in `impact_measure_corpus_manifest_v4.json` after nested repairs; reconcile the maintained closeout hash table without changing scores, metrics, rejected status, or v3 history.
- [ ] Step 3: Add nested reference checks to `test_public_p0a_v4_manifest_binds_all_referenced_artifacts`.
- [ ] Step 4: Verify the negative decision and incumbent retention remain unchanged.

**Verification:**
- [ ] `python -m pytest -q tests/test_p0_public_corpus.py`
- Expected: all referenced files exist and every declared hash equals current bytes.

**Exit Criteria:**
- P0-A lineage is deterministic, tested, and permanently closed as rejected.

### Task 6: Make calibration loss one-pair-one-bucket

**Purpose:**
- Make calibration output decision-grade before using recall losses for tuning.

**Task Function:**
- Classify each missing or false pair once at the actual stage boundary and derive type counts from pair rows.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: bounded metrics correction with existing fixture coverage.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: validate exhaustive, disjoint classification.

**Specification Coverage:**
- Buckets are disjoint and exhaustive.
- `by_requirement_type` counts individual classified pairs, not whole buckets.
- Names reflect boundaries: canonical-pool loss, retrieval loss, verification loss, selection loss, assignment loss, false verified pair, qualifier loss.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py:_support_metrics`, `_calibration_loss_decomposition`, and stage-pair construction in `run_benchmark`
- Modify: `scripts/benchmark_requirement_support.py:_support_metrics`, `_calibration_loss_decomposition`, and upstream stage-pair producers required to distinguish canonical absence, retrieval loss, verification loss, selection loss, assignment loss, qualifier loss, and false verified pairs
- Verify: `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`

**Dependencies:**
- Tasks 1–3 establish support and selection stage truth; Task 2 and Task 3 ledger transitions are complete before calibration diagnostics are consumed.

**Authority:**
- Preauthorized local actions: edit calibration classification and focused metric tests.
- Stop for: using calibration output to tune before exhaustive pair tests pass.

**Steps:**
- [ ] Step 1: Emit one primary bucket for each expected missing pair and selected false pair, with precedence `not_in_canonical_pool`, `retrieval_loss`, `verification_loss`, `qualifier_failure`, `selection_loss`, `assignment_loss`, then `false_verified_pair`.
- [ ] Step 2: Populate qualifier and assignment buckets from actual stage evidence or report them as zero only when stage evidence proves zero.
- [ ] Step 3: Compute counts and `by_requirement_type` by iterating pair records.
- [ ] Step 4: Add overlap, exhaustiveness, mixed-type, qualifier, and false-assignment fixtures.

**Verification:**
- [ ] `python -m pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py`
- Expected: `sum(counts.values()) == total_errors`, `unclassified == 0`, and each error pair appears once.

**Exit Criteria:**
- Calibration report can identify one dominant loss stage without overcounting.

### Task 7: Run corrected calibration and apply at most one bounded P0-B patch

**Purpose:**
- Diagnose the corrected `29/143` recall path and make one evidence-led change only.

**Task Function:**
- Run calibration, rank loss buckets, and patch the single dominant existing stage when the gate permits.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: decision depends on fresh corrected calibration evidence.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: independent regression and hard-negative review.

**Specification Coverage:**
- Rank by pair count, percentage, source-group spread, and mandatory-requirement impact.
- Patch one dominant stage only; do not start an architecture cycle.
- Holdout remains untouched until calibration regression passes.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py:run_benchmark`, `_aggregate_scenario_metrics`, corrected calibration output
- Inspect: `scripts/compare_requirement_support.py:run_inputs`
- Modify: only the existing canonical owner identified by the dominant stage: `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`, or the evaluator/benchmark script that owns that stage
- Verify: focused regression tests for the selected stage plus `tests/test_benchmark_requirement_support.py`

**Dependencies:**
- Tasks 1–6 complete.

**Authority:**
- Preauthorized local actions: run calibration, add one bounded patch and its regression tests, and rerun calibration fixtures.
- Stop for: no single dominant stage, tied dominant stages, hard-negative false-positive regression, threshold changes, or holdout access before approval gates pass.

**Steps:**
- [ ] Step 1: Run calibration only and save report outside tracked private corpus paths.
- [ ] Step 2: Rank buckets using the declared four-factor rule.
- [ ] Step 3: Patch only when one stage accounts for more than 50% of total pair loss and more than twice the next-highest stage; modify only its existing canonical owner and add a focused regression. Otherwise record a blocked optimization decision and leave code unchanged.
- [ ] Step 4: Re-run calibration and compare recall, hard-negative false positives, mandatory coverage, and latency against the pre-patch report.

**Verification:**
- [ ] `python -m pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Expected: corrected decomposition passes; no hard-negative false-positive increase; no production-default mutation.

**Exit Criteria:**
- One bounded P0-B correction is either regression-proven or explicitly not applied because evidence did not justify it.

### Task 8: Execute protected holdout and close P1 evidence

**Purpose:**
- Make final P0-B and P1 acceptance decisions from fresh proof without automatic promotion.

**Task Function:**
- Run the frozen holdout once, refresh render/P1-B evidence, and reconcile final status documentation.

**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: final acceptance requires fresh backend, CI, and artifact proof.

**Validator Profile:**
- Controller-selected: `unresolved`
- Selection basis: verify holdout immutability, report hashes, and status consistency.

**Specification Coverage:**
- One protected holdout run decides P0-B.
- P0-B failure leaves production defaults unchanged.
- P1-A render proof is green.
- P1-B records `accepted_cv_effort_v1` at `n=1` without efficiency claims.
- P1-C/P2 remain deferred.

**Required Skills:**
- `skill-backend-verification`
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:main`, `scripts/validate_p0b_holdout_review.py:validate_review_file`, `src/fitcv_cp/run_artifact_contracts.py:build_accepted_cv_effort_projection`, holdout manifests and freeze metadata
- Modify: `docs/pipeline.md`, `docs/superpowers/evidence/2026-10-01-fitcv-final-p0-p1-closure.md`
- Verify: `.github/workflows/repo-hooks.yml`, `tests/test_cv_render_acceptance.py`, `tests/test_fitcv_cp/test_run_artifact_contracts.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_run_artifact_mirror.py`, P0/P1 focused suites, generated report hashes

**Dependencies:**
- Tasks 1–7 complete; holdout preflight must pass before execution, while evaluated gate failure remains a valid final `not_promotable` outcome.

**Authority:**
- Preauthorized local actions: run one declared holdout, generate reports, refresh evidence docs, and run final verification.
- Stop for: holdout mutation, reviewer provenance failure, failed support/relevance gate, production-default change, push, merge, or publication.

**Steps:**
- [ ] Step 1: Verify hashes, source-group disjointness, row/group minimums, and reviewer provenance for `data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json`, `data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json`, `data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json`, `data/fitcv-p0-corpus/p0b/p0b_source_job_candidate_pool_v1.jsonl`, `data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv`, and `data/fitcv-p0-corpus/p0b/p0b_holdout_freeze_manifest_v1.json`; preflight failure means holdout is not run.
 - [ ] Step 2: If preflight passes, execute exactly one evaluation with `python scripts/evaluate_p0b_source_job_relevance.py --fixture data/fitcv-p0-corpus/p0b/p0b_source_job_relevance_fixture_v2_human_frozen.json --packet data/fitcv-p0-corpus/p0b/p0b_source_job_review_packet_v2_human_adjudicated.json --group-map data/fitcv-p0-corpus/p0b/p0b_source_job_source_group_map_v2.json --projection data/fitcv-p0-corpus/p0b/candidate_evidence_projection_source_backed_v1.jsonl --evidence-link-review data/fitcv-p0-corpus/p0b/p0b_source_job_evidence_link_review_v1.csv --policy config/policy/cv_analysis.yaml --output .tmp/p0b-final-evaluation.json`; missing approved support threshold keeps result `not_promotable` and blocks promotion.
- [ ] Step 3: Persist `.tmp/p0b-final-evaluation.json` SHA-256, every input hash, and base commit SHA; evaluated gate failure means `not_promotable`, followed by evidence closure without tuning or promotion.
- [ ] Step 4: Refresh P1-A CI proof and reproduce the existing P1-B projection from `.tmp/p1b-approved-workload/control-plane.sqlite3` and `.tmp/p1b-approved-workload/evidence.json` through `build_accepted_cv_effort_projection`; assert schema `accepted_cv_effort_v1`, run `p1b-approved-sanitized-001`, accepted denominator `1`, `regenerate_once`, `approve_as_is`, final artifact, and timestamps.
- [ ] Step 5: Write final evidence with explicit P0-A, P0-B, P0-C, P1-A, P1-B, P1-C, and P2 states.
- [ ] Step 6: Run final verification and confirm protected paths are unchanged and no private artifacts entered the diff.

**Verification:**
- [ ] `python -m pytest -q -m "not render_acceptance"`
- [ ] `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- [ ] `python -m pytest -q tests/test_p0_public_corpus.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- [ ] `git diff --check`
- Expected: all required checks pass, holdout is read-only when run, preflight and evaluated outcomes are distinguished, reports are hash-bound, and final evidence matches source/test truth.

**Exit Criteria:**
- `skill-verification-before-completion` returns `verified`; only then may plan status change to `completed`.

## Verification

- `python -m pytest -q -m "not render_acceptance"`
- `python -m pytest -q tests/test_cv_render_acceptance.py -m render_acceptance`
- `python -m pytest -q tests/test_p0_public_corpus.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- `git diff --check`
- `git status --short`

## Completion Criteria

The plan is ready for completion verification when:

1. strict responsibility proof and unified requirement coverage pass focused regressions;
2. evaluator gates are pair-level, fail closed, and provenance-aware;
3. selection/recovery is deterministic and monotonic;
4. ordinary and render CI pass from clean committed inputs;
5. P0-A nested hashes pass integrity checks and its rejected decision remains unchanged;
6. calibration error pairs are disjoint, exhaustive, and correctly typed;
7. one protected holdout records an explicit P0-B pass or failure with no automatic promotion on failure;
8. P1-A and P1-B evidence is fresh and bounded by its actual sample size;
9. P0-C remains green while P1-C and P2 remain deferred;
10. `skill-verification-before-completion` returns `verified` with no failed required check, stale status, or unrecorded scope deviation.

No merge, push, publication, or cleanup is part of this plan. Checkpoint commits remain local and limited to declared files.
