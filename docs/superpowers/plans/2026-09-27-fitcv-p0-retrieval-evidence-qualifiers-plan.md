---
layer: change
artifact_type: plan
contract_version: "1"
status: active
template_id: implementation-plan
name: fitcv-p0-retrieval-evidence-qualifiers
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_context.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - scripts/benchmark_ranking.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_vector_search.py
  - tests/test_pipeline.py
  - tests/test_enrich.py
  - tests/test_validator.py
  - tests/test_cv_generator.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_ranking_evaluation.py
  - tests/fixtures/requirement_support_benchmark.json
  - tests/fixtures/ranking_production_like.json
  - docs/pipeline.md
  - docs/configuration.md
---

# FitCV P0 Retrieval, Evidence, and Qualifier Completion

## Goal

Complete P0-A Job retrieval, P0-B Evidence retrieval, and P0-C Qualifier requirements without false support, cross-evidence qualifier assembly, silent retrieval strategy changes, or unmeasured recovery complexity.

Current repository baseline: `71e6260d` on `main`, with unrelated dirty and untracked files preserved. The plan is active. Tasks 2-5 execute in the isolated worktree; P0-B promotion remains blocked until reviewed requirement/evidence labels arrive.

Execution worktree: `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-completion\JOB-PROJECT`. The primary checkout retains unrelated user changes and this plan; implementation proof comes from the execution worktree.

## Implementation Outcomes

### Requirement-scoped qualified support

`src/fitcv/evidence.py` and `src/fitcv/agentic_cv_analysis.py` produce requirement-instance-scoped support. One evidence item must establish canonical skill plus every decisive qualifier before a requirement is `verified`. Existing `selected_support`, `support_strength`, validator, and generator contracts remain compatible.

### Truthful retrieval and fallback

`run_vector_search()` separates requested retrieval strategy from available job data. Compatible vectors remain vector retrieval. Missing, stale, invalid, or contract-incompatible vectors use deterministic lexical fallback only when fallback data exists, with requested strategy, effective strategy, reason, backend, contract, and counts recorded.

### Measured P0-A and P0-B decisions

Benchmarks report qualified-support recall for evidence selection and source-backed held-out DE/EN retrieval metrics for job search. Losing arms and unmeasured recovery mechanisms are removed only after reproducible comparison evidence.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Executor: `codex` local controller; lead controller resolves task profile before activation
- Required skills: `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`, `skill-performance-optimization`, `skill-verification-before-completion`
- Isolation: `optional worktree`; preserve current dirty checkout
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed source, test, benchmark, fixture, and documentation files; run listed local checks; write ignored `tmp/p0/` reports
- User-approval actions: push, merge, provider access, credentials, external writes, raw private-data publication, destructive cleanup, and production-default promotion
- Parallel ownership: none
- Sequential fallback: run tasks in listed order; stop at each blocked admission or failed exit criterion

## Task Breakdown

### Task 1: Establish baseline and evidence admission

**Purpose:** Bind work to current repository truth and prevent synthetic benchmark proof.

**Task Function:** Baseline inspection and benchmark admission.

**Template Profile:**
- Executor: `local Codex controller`
- Selection basis: local baseline inspection; no delegated implementation profile required

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: task-local commands and source review suffice

**Specification Coverage:** Current-base binding, preserved user work, source-backed P0-A evidence, and reproducible baseline.

**Required Skills:** `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:build_required_skill_descriptors`
- Inspect: `src/fitcv/agentic_cv_analysis.py:_support_ids_by_requirement`
- Inspect: `src/fitcv/vector_search.py:run_vector_search`
- Inspect: `scripts/benchmark_ranking.py:main`
- Verify: `git status --short`, `git rev-parse HEAD`

**Dependencies:** None.

**Authority:**
- Preauthorized local actions: inspect repository, run focused baseline checks, and write ignored baseline reports under `tmp/p0/`
- Stop for: changed base, missing required files, destructive workspace state, or missing source-backed corpus for P0-A promotion

**Steps:**
- [x] Record current `HEAD`, branch, dirty paths, and existing untracked plan/report files.
- [x] Run focused tests without modifying fixtures.
- [x] Check for `tmp/p0/corpus/raw_postings_de_en.jsonl`.
- [x] Require each corpus row to contain stable job ID, language, relevance grade, review status, and split; require reviewed German and English calibration/held-out examples.
- [x] Check for `tmp/p0/corpus/reviewed_requirement_evidence.jsonl`; require stable requirement/evidence IDs, raw evidence text, qualifier verdict labels, review status, language, and calibration/held-out split. Check performed; file absent, so P0-B promotion is blocked.
- [x] Mark P0-A admitted from reviewed DE/EN job rows; keep P0-B promotion blocked because its separate evidence corpus is absent. Never create synthetic production evidence.

**Verification:**
- [x] `git status --short`
- [x] `git rev-parse HEAD`
- [x] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_vector_search.py`
- Expected: baseline completes or failures are recorded before edits; unrelated user files remain unchanged.

**Exit Criteria:** Current base and dirty-state preservation are recorded; P0-A corpus status is explicit; baseline failures are known.

### Task 2: Implement requirement-instance qualified support

**Purpose:** Close P0-C and provide one authoritative support contract for P0-B.

**Task Function:** Deterministic requirement descriptor and evidence assessment implementation.

**Template Profile:**
- Executor: `local Codex controller`
- Selection basis: qualifier grammar and compatibility risk determine depth

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused regression suite is the validator

**Specification Coverage:** Requirement identity, qualifier conjunction, comparator preservation, contradiction scope, negation, duration attribution, and reuse invalidation.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/evidence.py:build_required_skill_descriptors`
- Modify: `src/fitcv/evidence.py:_annotate_requirement_support`
- Modify: `src/fitcv/evidence.py:_requirement_support_map`
- Modify: `src/fitcv/evidence.py:build_cv_analysis_contract_fingerprint`
- Modify: `src/fitcv/evidence.py:build_cv_analysis_input_fingerprint`
- Modify: `src/fitcv/agentic_cv_analysis.py:_support_ids_by_requirement`
- Modify: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Verify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_enrich.py`, `tests/test_validator.py`, `tests/test_cv_generator.py`

**Dependencies:** Task 1 complete.

**Authority:**
- Preauthorized local actions: edit listed support functions and add focused regression tests without changing external schemas or dependencies
- Stop for: missing raw requirement wording, need for LLM qualifier inference, persistent evidence storage, schema migration, or validator/generator contract replacement

**Steps:**
- [x] Add stable `requirement_instance_id` beside legacy `requirement_id`.
- [x] Normalize descriptor payload before ID generation; use deterministic occurrence ordering for duplicate identical requirements; make reordered input arrays produce the same semantic fingerprint.
- [x] Represent decisive qualifiers as structured values: duration comparator/months, context `all_of`, action `all_of`, and level comparator/value.
- [x] Derive qualifier facts from existing evidence `text`, `name`, and `scoring_context` plus optional structured fields. Missing explicit facts stay `unverified`; do not require an upstream schema change or LLM inference for P0.
- [x] Build an ephemeral evidence assessment matrix keyed by `requirement_instance_id` and `evidence_id`.
- [x] Mark `verified` only when one evidence item proves canonical skill and all decisive qualifiers.
- [x] Keep missing decisive qualifiers `unverified`; scope contradictions to same requirement claim; do not combine facts across evidence items.
- [x] Support bounded EN/DE explicit negation. Negated matches never become positive support.
- [x] Accept explicit numeric duration forms. Keep vague duration and date-relative forms unverified unless deterministic evidence dates exist. Do not copy job-level experience into skill duration.
- [x] Preserve legacy output fields. If a legacy ID maps to multiple instances, do not guess one instance's support.
- [x] Add `requirement_support_policy_version` and normalized descriptor fingerprint to analysis reuse fingerprints.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_enrich.py tests/test_validator.py tests/test_cv_generator.py`
- Expected: classroom SQL plus production Python does not verify production SQL; one evidence item with all qualifiers verifies; duplicate canonical requirements remain separate; reuse rejects changed policy or descriptors. Fresh result: `279 passed`.

**Exit Criteria:** Every qualified verdict is traceable to same-requirement evidence; no guessed support remains; compatibility tests pass.

### Task 3: Measure P0-B channel-pool versus full-pool selection

**Purpose:** Select evidence retrieval path using qualified-support evidence, not canonical-link recall alone.

**Task Function:** Controlled support-preservation benchmark.

**Template Profile:**
- Executor: `local Codex controller`
- Selection basis: bounded local benchmark; no provider dependency

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark comparison and focused tests

**Specification Coverage:** Qualified requirement recall, evidence-pair recall, selection loss, context cost, duplicates, and validation outcomes.

**Required Skills:** `skill-backend-verification`, `skill-performance-optimization`, `skill-test-driven-development`

**Files And Symbols:**
- Modify: `scripts/benchmark_requirement_support.py:run`
- Modify: `scripts/compare_requirement_support.py:run`
- Modify: `tests/fixtures/requirement_support_benchmark.json`
- Create: `tests/test_compare_requirement_support.py`
- Verify: `src/fitcv/evidence.py:retrieve_evidence_bundle`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`

**Dependencies:** Task 2 complete.

**Authority:**
- Preauthorized local actions: add local benchmark arms, sanitized fixture cases, comparison output, and tests; write ignored reports under `tmp/p0/`
- Stop for: unbounded candidate expansion, provider calls, new recovery flags, production rollout before comparison, or missing reviewed requirement/evidence labels

**Steps:**
- [x] Keep isolated qualifier semantics cases in the existing fixture; do not treat them as source-backed promotion evidence.
- [ ] Admit only reviewed, source-backed requirement/evidence cases from `tmp/p0/corpus/reviewed_requirement_evidence.jsonl`; keep raw input ignored and write only sanitized stable-ID cases to the fixture. Mark P0-B blocked when the corpus is absent.
- [x] Expand the benchmark tooling to compare current channel-pool and `full_pool` arms under identical assessment, selector, `top_k`, validation, and prompt paths.
- [x] Report qualified requirement recall, qualified evidence-pair recall, false qualified pairs, retrieval-to-selection loss, pool size, selected context size, p50/p95 latency, duplicates, and validation status.
- [x] Compare arms under identical warmup and measured-run settings.
- [ ] Apply fixed gates before comparison: zero false qualified pairs; qualified requirement recall non-decreasing; qualified evidence-pair recall non-decreasing; p95 latency and selected context characters no more than `1.20x` incumbent. A tie retains the lower-cost arm; no promotion occurs without admitted labels.
- [x] Retain current arm when full-pool lacks admissible evidence or fails a gate; delete losing code only during convergence.

**Current blocker:** `C:\Users\HOANG PHI LONG DANG\repos\career-ops\data.private\fitcv-p0-corpus` contains no `reviewed_requirement_evidence.jsonl`. P0-B implementation tests and tooling may run; P0-B promotion and fixture admission stay blocked. Do not fabricate labels.

**Verification:**
- [x] `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py`
- [x] `uv run python scripts/benchmark_requirement_support.py --arm current --output tmp/p0/support-current.json`
- [x] `uv run python scripts/benchmark_requirement_support.py --arm full-pool --output tmp/p0/support-full-pool.json`
- [x] `uv run python scripts/compare_requirement_support.py --inputs tmp/p0/support-current.json,tmp/p0/support-full-pool.json --output tmp/p0/support-comparison.json`
- Expected: comparison uses qualified metrics and reports a reproducible recommendation; no arm creates false verified support. Fresh result: `18 passed`; both arms report zero incorrect pairs and equal qualified recall, but P0-B promotion remains blocked by missing reviewed labels and fixture validation `6/17`.

**Exit Criteria:** P0-B comparison tooling is verified; current arm is retained and promotion stays blocked until reviewed source-backed labels make qualified-support gates admissible. No unmeasured recovery mechanism is added.

### Task 4: Separate P0-A strategy from fallback data

**Purpose:** Fix silent lexical substitution and make stale-vector behavior truthful.

**Task Function:** Retrieval contract and production caller correction.

**Template Profile:**
- Executor: `local Codex controller`
- Selection basis: cross-caller backend behavior and resume compatibility

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct retrieval and pipeline tests

**Specification Coverage:** Requested/effective strategy, stale-vector fallback, backend identity, checkpoint compatibility, and direct production callers.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/vector_search.py:run_vector_search`
- Modify: `src/fitcv/pipeline.py:3529`
- Modify: `src/fitcv/pipeline_stage_runner.py:264`
- Modify: `src/fitcv/pipeline_stage_context.py:_validate_checkpoint_retrieval_strategy`
- Verify: `src/fitcv/pipeline.py:_validate_checkpoint_retrieval_strategy`
- Verify: `tests/test_vector_search.py`, `tests/test_pipeline.py`

**Dependencies:** Task 1 baseline complete; Task 2 policy version available for diagnostics.

**Authority:**
- Preauthorized local actions: edit local retrieval contract and callers, add fallback/checkpoint tests, and write ignored diagnostics
- Stop for: provider access, credentials, dependency changes, silent production-default changes, or incompatible checkpoint migration without explicit approval

**Steps:**
- [x] Add explicit requested strategy input; treat `structured_jobs` only as fallback data.
- [x] Pass `structured_jobs=passed_jobs` from both production callers so fallback has the eligible batch it must rank.
- [x] Preserve vector retrieval when compatible vectors exist.
- [x] Use deterministic lexical fallback for a missing, stale, invalid, or contract-incompatible vector batch only when structured fallback data exists; do not mix vector and lexical rows in one shortlist.
- [x] Return explicit unavailable diagnostics when fallback data is absent; never silently change strategy.
- [x] Emit requested strategy, effective strategy, fallback reason, backend ID, configured model, dimension, contract fingerprint, and result counts.
- [x] Update both production callers and checkpoint/resume validation.
- [x] Test missing vectors, stale contract, invalid vectors, compatible vectors, absent fallback rows, and mixed-strategy checkpoint rejection.

**Verification:**
- [x] `uv run pytest -q tests/test_vector_search.py tests/test_pipeline.py`
- [x] Assert checkpoint/resume preserves requested and effective strategy, rejects mixed strategy rows, and retains fallback reason.
- [x] Assert both production callers expose requested strategy, effective strategy, fallback reason, backend identity, contract fingerprint, and result counts.
- [x] Assert `src/fitcv/pipeline_stage_context.py:_validate_checkpoint_retrieval_strategy` accepts compatible fallback diagnostics and rejects mixed effective strategies.
- Expected: compatible vectors remain vector retrieval; fallback is deterministic and diagnosed; absent fallback data is explicit failure/unavailable state.

**Exit Criteria:** Retrieval strategy cannot change merely because structured data is present; both production callers preserve the contract.

### Task 5: Run P0-A source-backed retrieval benchmark

**Purpose:** Establish truthful DE/EN job retrieval evidence and decide promotion or incumbent retention.

**Task Function:** Held-out retrieval evaluation.

**Template Profile:**
- Executor: `local Codex controller`
- Selection basis: evaluation validity and measured workload determine depth

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark schema and output inspection

**Specification Coverage:** Source-backed corpus, calibration/held-out separation, arm identity, recall, nDCG, latency, fallback, and multilingual status.

**Required Skills:** `skill-backend-verification`, `skill-performance-optimization`

**Files And Symbols:**
- Modify: `scripts/benchmark_ranking.py:main`
- Modify: `tests/test_ranking_evaluation.py`
- Modify: `tests/fixtures/ranking_production_like.json` only from approved sanitized corpus
- Verify: `src/fitcv/vector_search.py:run_vector_search`, `src/fitcv/pipeline.py`, `src/fitcv/pipeline_stage_runner.py`

**Dependencies:** Task 4 complete; admitted source-backed corpus from Task 1.

**Authority:**
- Preauthorized local actions: add explicit local benchmark arms and sanitized fixture metadata; write ignored benchmark outputs
- Stop for: absent reviewed corpus, fabricated labels, provider access, credentials, or multilingual arm without approved capability

**Steps:**
- [x] Add explicit `--arm incumbent`, `--arm lexical`, and `--arm multilingual` handling.
- [x] Define arm semantics in output: `incumbent` requests current production strategy and records fallback separately; `lexical` requests lexical retrieval and is not a vector-fallback result; `multilingual` requests only an approved multilingual backend and returns `not_run` when unavailable.
- [x] Keep unavailable multilingual capability as `not_run` with reason.
- [x] Preserve source language, review labels, stable IDs, and calibration/held-out split fields.
- [x] Run every arm against identical eligible jobs and Top-N.
- [x] Keep absolute recall and nDCG floors unset until admitted corpus baseline exists; promotion compares challengers against the measured incumbent on the same split.
- [x] Report shortlist recall, nDCG, p50/p95 latency, coverage, fallback count, backend identity, cache reuse, and split counts.
- [x] Apply fixed gates before promotion: held-out recall and nDCG non-decreasing; zero correctness failures; p95 latency no more than `1.20x` incumbent; backend and fallback identity present. No promotion occurs without admitted source-backed labels; otherwise retain incumbent and record reason.

**Verification:**
- [x] `uv run pytest -q tests/test_ranking_evaluation.py tests/test_vector_search.py tests/test_embeddings.py`
- [x] `uv run python scripts/benchmark_ranking.py --fixture tmp/p0/corpus/ranking_source_backed.json --arm incumbent --output tmp/p0/ranking-incumbent.json`
- [x] `uv run python scripts/benchmark_ranking.py --fixture tmp/p0/corpus/ranking_source_backed.json --arm lexical --output tmp/p0/ranking-lexical.json`
- [x] `uv run python scripts/benchmark_ranking.py --fixture tmp/p0/corpus/ranking_source_backed.json --arm multilingual --output tmp/p0/ranking-multilingual.json`
- Expected: outputs distinguish measured, unavailable, and `not_run`; held-out metrics are not derived from synthetic fallback jobs. Fresh result: `60 passed, 2 skipped`; incumbent retained because lexical does not improve nDCG and multilingual is `not_run`.

**Exit Criteria:** P0-A promotion or incumbent retention has source-backed held-out evidence and rollback choice.

### Task 6: Converge, document, and verify

**Purpose:** Keep one authoritative path and reconcile maintained documentation.

**Task Function:** Simplification and final verification.

**Template Profile:**
- Executor: `local Codex controller`
- Selection basis: changed-surface size and verification results

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: final repository checks

**Specification Coverage:** Losing-arm deletion, documentation alignment, compatibility, rollback, and final proof.

**Required Skills:** `skill-verification-before-completion`

**Files And Symbols:**
- Modify: `docs/pipeline.md`, `docs/configuration.md`
- Modify: losing benchmark/retrieval paths proven unnecessary by Tasks 3 and 5
- Verify: all changed source, tests, fixtures, and ignored reports

**Dependencies:** Tasks 2–5 complete with accepted evidence.

**Authority:**
- Preauthorized local actions: delete only measured losing paths, update maintained documentation, run final checks, and write final ignored reports
- Stop for: deletion without consumer/test proof, unrelated cleanup, changed acceptance thresholds, or unresolved P0 blocker

**Steps:**
- [ ] Record P0-A and P0-B decision tables with incumbent, winner, metrics, compatibility, and rollback.
- [ ] Delete unmeasured recovery flags and losing paths only when no live consumer remains.
- [x] Update pipeline and configuration documentation to match actual strategy, fallback, support, and fingerprint contracts.
- [x] Confirm P1 remains deferred.

**Verification:**
- [x] `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_vector_search.py tests/test_pipeline.py tests/test_validator.py tests/test_cv_generator.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_ranking_evaluation.py`
- [ ] `uv run pytest -q`
- [x] `git diff --check`
- [x] `rg -n "direct_support_recovery|overflow_limit|PreparedCandidateContext" src scripts tests docs`
- Expected: changed-surface suite `388 passed, 1 skipped`; full suite remains unrun because P0-B is blocked and prior full-suite failures are unrelated local credential/frontend-storage and inverse-optimization tests. No unmeasured mechanism references found; docs and diagnostics match source.

**Exit Criteria:** P0-A, P0-B, and P0-C acceptance evidence is complete or explicitly blocked; source, tests, docs, and benchmark artifacts agree.

## Verification

- `uv run pytest -q`
- `git diff --check`
- Focused benchmark outputs exist under ignored `tmp/p0/` paths.
- P0-A report contains source-backed DE/EN split counts, arm identity, held-out recall, nDCG, p50/p95 latency, fallback count, and backend identity.
- P0-B report contains qualified requirement recall, evidence-pair recall, false qualified pairs, selection loss, context size, latency, duplicates, and validation status.
- P0-B promotion remains blocked until `tmp/p0/corpus/reviewed_requirement_evidence.jsonl` exists with reviewed stable requirement/evidence labels.
- P0-C tests prove same-evidence qualifier support, scoped contradiction, negation handling, duplicate requirement identity, duration comparator preservation, and reuse invalidation.

## Completion Criteria

The plan is ready for completion verification when:

1. P0-C uses requirement-instance-scoped evidence assessments and never assembles qualified claims across unrelated evidence items.
2. P0-B selection is promoted or retained using qualified-support metrics, with losing complexity deleted only after proof.
3. P0-A retrieval strategy and fallback diagnostics are truthful in both production callers and checkpoint/resume paths.
4. Source-backed held-out DE/EN evidence supports retrieval acceptance, or P0-A remains explicitly blocked for missing corpus/capability.
5. Existing validator, generator, support, and reuse contracts remain compatible.
6. No provider, dependency, credential, raw private-data, or production-default change bypasses approval.
7. P1 work remains deferred until P0 residual errors, latency, cost, and manual review impact are measured.

The plan status stays `active` until `skill-verification-before-completion` marks it `completed` after fresh proof.
