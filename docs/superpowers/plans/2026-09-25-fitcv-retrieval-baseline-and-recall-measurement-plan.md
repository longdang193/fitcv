---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-retrieval-baseline-and-recall-measurement
targets:
  - src/fitcv/embeddings.py
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - scripts/benchmark_requirement_support.py
  - tests/fixtures/requirement_support_benchmark.json
  - tests/test_embeddings.py
  - tests/test_evidence.py
  - tests/test_validator.py
  - tests/test_benchmark_requirement_support.py
  - docs/pipeline.md
  - docs/configuration.md
---

# FitCV — Retrieval Baseline and Recall Measurement Plan

## Goal

Establish trustworthy retrieval-quality evidence after PR #47. Prove which
embedding backend CV-analysis semantic alignment actually uses, compare the
configured deterministic path with lexical/taxonomy retrieval, and measure
canonical-to-retrieved and retrieved-to-selected support loss on fixed
candidate-evidence fixtures.

This plan covers P1-A only: measurement and diagnostics. It does not change
production retrieval defaults, shortlist embeddings, final `top_k`, provider
usage, or evidence-selection behavior.

## Review Verdict

The supplied verdict is accepted with these execution corrections:

- The SHA-256 vector path is a P1 measurement blocker, not permission to
  replace `generate_embedding()` globally. Shortlist embedding behavior and
  persisted SQLite vectors remain outside this plan.
- Lexical-only retrieval is the first baseline. Pool-size and direct-support
  strategies are measured only after that baseline is recorded.
- Direct-link recovery remains a benchmark-only diagnostic in this phase. A
  production candidate-union or selector change requires a later approved
  implementation plan.
- Live generation waits for an offline retrieval winner. This plan reports
  prompt construction and validation cost only; it makes no provider-quality
  claim.

## Non-Goals

- No real embedding provider, SDK, network call, credential, vector database,
  GraphRAG layer, agentic retrieval loop, or memory system.
- No global change to `src/fitcv/embeddings.py:generate_embedding()` output,
  dimension, persistence format, or shortlist behavior.
- No production increase to channel pool size, direct-support recovery, global
  `top_k`, generation budget, or validation policy.
- No claim that lexical or hash retrieval improves final CV quality until a
  separate paired live-generation evaluation is approved.

## Implementation Outcomes

### Backend-truth diagnostics

CV-analysis evidence diagnostics expose actual backend identity, configured model
name, vector dimension, and embedding contract fingerprint. Enabled semantic
alignment reports the deterministic local/hash backend currently used by
`generate_embedding()`; disabled alignment reports no semantic backend. The
shortlist path remains behaviorally unchanged.

### Reproducible retrieval benchmark

One fixed fixture exercises supported, unsupported, synonym, wrong-ID, and
responsibility-only cases. Every requirement descriptor appears in benchmark
coverage, including requirements with no selected support. Metrics derive from
actual analysis/retrieval output and expected evidence pairs rather than
hardcoded correctness values.

### Ordered retrieval comparison

Benchmark output separates these arms under identical profile, JD, `top_k`,
selection policy, and workload:

1. Configured semantic alignment, deterministic local/hash backend, pool 4.
2. Semantic alignment disabled, lexical/taxonomy baseline, pool 4.
3. Lexical/taxonomy baseline, pool 8.
4. Pool 12 only when pool 8 still shows material retrieved-support loss.

The benchmark reports canonical, retrieved, selected, and validation coverage;
support loss at each boundary; selected IDs; duplicate IDs; retrieval,
selection, prompt, and validation timing; estimated context tokens; and the
backend metadata for each arm.

### Decision-ready evidence

Results identify whether the dominant loss is semantic ordering, channel
truncation, global selection budget, or validation rejection. Results also show
whether bounded direct-support recovery has enough missing-support candidates to
justify a separate P1-B implementation plan. No production behavior changes as
part of this measurement.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`, `skill-using-git-worktrees`
- Isolation: `task-specific worktree from merged `origin/main` commit `cc1b90f4881f7043ea3ca4284f71faf60c2d2375`; preserve dirty primary checkout`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed source, benchmark, tests, and docs; run fixed offline probes; write task-owned `.tmp` benchmark output
- User-approval actions: `real provider access, dependency or lockfile changes, production default changes, push, merge, publication, destructive cleanup`
- Parallel ownership: `none; benchmark and diagnostics share evidence contracts`
- Sequential fallback: `backend truth → fixture/benchmark contract → retrieval arms → cost/loss analysis → final verification`

## Task Breakdown

### Task 1: Expose actual semantic backend identity

**Purpose:** Stop diagnostics and benchmark reports from calling deterministic
hash vectors semantic embeddings without evidence.

**Task Function:** Add backend metadata at the canonical embedding owner and
thread it through CV-analysis semantic diagnostics without changing vectors.

**Template Profile:**
- Executor: current Codex lead
- Selection basis: inline sequential execution; bounded source and diagnostics change.

**Validator Profile:**
- Validator: current Codex lead through focused tests and direct backend probes
- Selection basis: no delegated validator; proof is local, deterministic, and reviewable.

**Specification Coverage:** Backend-truth diagnostics; shortlist isolation;
embedding contract compatibility.

**Required Skills:**
- `skill-systematic-debugging`
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/embeddings.py:generate_embedding`, `src/fitcv/embeddings.py:_deterministic_local_embedding`, `src/fitcv/embeddings.py:build_embedding_contract_fingerprint`, `src/fitcv/evidence.py:_semantic_methods`, `src/fitcv/evidence.py:_semantic_alignment_settings`
- Modify: `src/fitcv/embeddings.py` backend metadata owner; `src/fitcv/evidence.py` semantic diagnostics; `tests/test_embeddings.py`; `tests/test_evidence.py`
- Verify: `src/fitcv/embeddings.py`, `src/fitcv/evidence.py`, `tests/test_embeddings.py`, `tests/test_evidence.py`

**Dependencies:** Merged PR #47 at `cc1b90f4881f7043ea3ca4284f71faf60c2d2375`.

**Authority:**
- Preauthorized local actions: add metadata and diagnostics; add focused tests; update no vector or persistence behavior.
- Stop for: provider access, embedding dependency changes, shortlist contract changes, or persisted-vector migration.

**Steps:**
- [ ] Step 1: Add failing tests proving configured model name does not imply a remote semantic backend and that deterministic output remains unchanged.
- [ ] Step 2: Add one canonical backend metadata result containing backend ID, configured model, dimension, and embedding contract fingerprint.
- [ ] Step 3: Emit metadata in enabled CV-analysis semantic diagnostics; emit `disabled` backend state when semantic alignment is off.
- [ ] Step 4: Prove shortlist embedding callers and SQLite contract fingerprints remain unchanged.

**Verification:**
- [ ] `uv run pytest -q tests/test_embeddings.py tests/test_evidence.py -k "embedding or semantic_alignment"`
- Expected: backend reports deterministic local/hash identity; vector shape and shortlist tests remain green; no network call occurs.

**Exit Criteria:** Diagnostics distinguish configured model from actual backend without changing embedding output or shortlist behavior.

### Task 2: Build complete representative grounding fixtures

**Purpose:** Make benchmark correctness cover both positive and negative
requirement-specific support instead of validating one fixed SQL claim.

**Task Function:** Extend the existing benchmark fixture and validation path
with complete requirement rows and expected support pairs.

**Template Profile:**
- Executor: current Codex lead
- Selection basis: inline sequential execution; fixture and metric work share one benchmark contract.

**Validator Profile:**
- Validator: current Codex lead through fixture assertions and validation matrix
- Selection basis: no delegated validator; assertions are deterministic and local.

**Specification Coverage:** Actual analysis-path requirement coverage; valid and
invalid structured grounding; no hardcoded assignment correctness.

**Required Skills:**
- `skill-test-driven-development`
- `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py:main` (new), `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`, `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`, `src/fitcv/validator.py:run_all_validations`, `src/fitcv/evidence.py:retrieve_evidence_bundle`
- Create: `scripts/benchmark_requirement_support.py`, `tests/fixtures/requirement_support_benchmark.json`, `tests/test_benchmark_requirement_support.py`
- Modify: `tests/test_validator.py` only for missing benchmark boundary cases
- Verify: benchmark fixture output and validation result matrix

**Dependencies:** Task 1 backend metadata; canonical support maps from PR #47.

**Authority:**
- Preauthorized local actions: modify benchmark-only fixtures, metric calculation, and focused tests.
- Stop for: changing production support authority, relaxing validator rules, or adding a second evidence schema.

**Steps:**
- [ ] Step 1: Create `tests/fixtures/requirement_support_benchmark.json` as the single fixture source. Store requirement IDs, canonical skill IDs, approved evidence IDs, explicit no-support requirements, and responsibility-only negative cases.
- [ ] Step 2: Create `scripts/benchmark_requirement_support.py` with CLI `--arm {current-hash,lexical}`, `--pool-size INT`, and `--output PATH`; load fixture, clone runtime config in memory, and call existing analysis/retrieval and validation owners without changing repository config.
- [ ] Step 3: Build coverage rows from actual `analyze_ranked_job()` or retrieval output for every requirement descriptor, including empty selected support.
- [ ] Step 4: Add validation cases for approved support, missing support, wrong evidence ID, canonical synonym, unsupported structured skill, and legacy Markdown fallback.
- [ ] Step 5: Calculate incorrect assignments from actual selected pairs versus fixture expectations; keep generation marked `prompt_only`.

**Verification:**
- [ ] `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_validator.py`
- Expected: valid claims pass; unsupported, wrong-ID, and wrong-canonical claims fail; every requirement appears in output.

**Exit Criteria:** Benchmark correctness metrics reflect actual support relationships and cannot pass through a hardcoded zero or omitted unsupported row.

### Task 3: Compare configured hash retrieval with lexical baseline

**Purpose:** Establish whether semantic alignment's actual deterministic backend
adds retrieval value before pool-size or recovery changes are considered.

**Task Function:** Run identical fixtures through current and lexical-only
configuration arms and report comparable support and cost metrics.

**Template Profile:**
- Executor: current Codex lead
- Selection basis: inline sequential measurement; no production edit.

**Validator Profile:**
- Validator: current Codex lead through benchmark output and direct probes
- Selection basis: no delegated validator; identical offline workload makes comparison deterministic.

**Specification Coverage:** Phase A current-vs-lexical comparison; fixed
workload; support and latency attribution.

**Required Skills:**
- `skill-performance-optimization`
- `skill-systematic-debugging`

**Files And Symbols:**
- Inspect: `config/policy/cv_analysis.yaml`; `src/fitcv/evidence.py:retrieve_evidence_bundle`; `src/fitcv/evidence.py:_select_channel_candidates`
- Modify: `scripts/benchmark_requirement_support.py`; `tests/test_benchmark_requirement_support.py`
- Verify: four-arm JSON output and unchanged config defaults

**Dependencies:** Tasks 1–2 complete.

**Authority:**
- Preauthorized local actions: add benchmark arm selection and deterministic timing fields; run offline measurements.
- Stop for: changing `config/policy/cv_analysis.yaml`, changing default `channel_pool_size`, or calling an external embedding provider.

**Steps:**
- [ ] Step 1: Add explicit arm parameters for current hash-enabled pool 4 and lexical-only pool 4; clone config in memory while keeping `top_k`, selection policy, fixture, and input ordering constant.
- [ ] Step 2: Run fixed warm-up plus repeated measurements and report median and p95 retrieval, selection, prompt, and validation latency; report estimated context size, not provider token usage.
- [ ] Step 3: Report backend metadata, canonical/retrieved/selected support, boundary loss counts, expected-pair errors, and final selected IDs per arm.
- [ ] Step 4: Keep all outputs task-owned and offline; do not alter production defaults or persisted evidence.

**Verification:**
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm current-hash --pool-size 4 --output .tmp/retrieval-current-hash.json`
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 4 --output .tmp/retrieval-lexical-4.json`
- Expected: same fixture and final `top_k`; output identifies hash backend explicitly and separates coverage from local timing.

**Exit Criteria:** A reproducible lexical-vs-configured comparison exists with no production behavior change.

### Task 4: Measure deterministic pool expansion and direct-support opportunity

**Purpose:** Locate recall loss after the baseline without prematurely adding a
second production retrieval mechanism.

**Task Function:** Add measurement-only pool-size arms and bounded direct-link
opportunity accounting from existing canonical support maps.

**Template Profile:**
- Executor: current Codex lead
- Selection basis: inline sequential measurement after lexical baseline; implementation decision remains deferred.

**Validator Profile:**
- Validator: current Codex lead through deterministic output comparison
- Selection basis: no delegated validator; same fixture and selection contract apply to every arm.

**Specification Coverage:** Phase B measurement; canonical-to-retrieved and
retrieved-to-selected loss; direct-support decision gate.

**Required Skills:**
- `skill-performance-optimization`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:_select_channel_candidates`, `src/fitcv/evidence.py:_merge_channel_pools`, `src/fitcv/evidence.py:_select_final_evidence`, `src/fitcv/evidence.py:_EvidenceSelectionEngine`
- Modify: `scripts/benchmark_requirement_support.py`; `tests/test_benchmark_requirement_support.py`
- Verify: pool 4, pool 8, and conditional pool 12 output; direct-support opportunity counts

**Dependencies:** Task 3 lexical baseline.

**Authority:**
- Preauthorized local actions: benchmark-only pool-size runs and direct-support opportunity metrics.
- Stop for: adding candidate union to production retrieval, changing global `top_k`, or claiming direct-link selection quality from opportunity counts alone.

**Steps:**
- [ ] Step 1: Run lexical pool 4 and pool 8 with identical final selection budget. Run pool 12 only when pool 8 has at least one approved-support requirement missing from retrieved support; record triggering requirement IDs.
- [ ] Step 2: Count requirements with canonical support absent from retrieved support and list bounded direct-link candidate IDs as an opportunity metric.
- [ ] Step 3: Separate retrieved-to-selected loss from canonical-to-retrieved loss and report selected context-size and latency deltas.
- [ ] Step 4: Produce a decision record: retain pool 4, adopt pool 8, or draft a separate P1-B direct-recovery plan; do not implement the choice here.

**Verification:**
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 8 --output .tmp/retrieval-lexical-8.json`
- [ ] If pool 8 has pre-selection support loss, run `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 12 --output .tmp/retrieval-lexical-12.json`; otherwise record `pool_12_skipped` with reason in comparison output.
- Expected: reports show whether support loss occurs before or after merge/selection; final `top_k` remains constant; conditional pool-12 execution is reproducible.

**Exit Criteria:** Pool expansion and direct-support opportunity are measured independently, with no production retrieval change.

### Task 5: Reconcile documentation and final evidence

**Purpose:** Make repository docs and handoff state match measured backend and
retrieval behavior.

**Task Function:** Update canonical documentation and assemble final offline
evidence for the next implementation decision.

**Template Profile:**
- Executor: current Codex lead
- Selection basis: inline sequential closeout after all measurement tasks.

**Validator Profile:**
- Validator: current Codex lead through final commands and diff audit
- Selection basis: no delegated validator; final evidence is repository-local.

**Specification Coverage:** Backend truth, measurement-only scope, and future
P1-B/P1-C handoff.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/pipeline.md`, `docs/configuration.md`, benchmark outputs
- Modify: `docs/pipeline.md`, `docs/configuration.md`
- Verify: all changed files, benchmark JSON, and Git state

**Dependencies:** Tasks 1–4 complete.

**Authority:**
- Preauthorized local actions: update docs to describe observed behavior and run final checks.
- Stop for: documenting unverified semantic quality, committing generated benchmark output, or changing unrelated dirty files.

**Steps:**
- [ ] Step 1: Document that configured CV-analysis semantic alignment currently uses deterministic local/hash vectors and that configured model name is metadata, not proof of provider execution.
- [ ] Step 2: Document benchmark arm definitions, support-loss boundaries, and the rule that live generation waits for offline retrieval evidence.
- [ ] Step 3: Record remaining decision gates for P1-B retrieval behavior and P1-C paired live generation without implementing them.
- [ ] Step 4: Reconcile plan, Git diff, generated outputs, and preserved unrelated checkout changes.

**Verification:**
- [ ] `uv run pytest -q tests/test_embeddings.py tests/test_evidence.py tests/test_validator.py tests/test_benchmark_requirement_support.py`
- [ ] `git diff --check`
- [ ] Run required benchmark commands from Tasks 3–4, run conditional pool-12 command only when its trigger is present, and inspect JSON fields
- Expected: focused proof passes; output is reproducible; production defaults and shortlist behavior remain unchanged.

**Exit Criteria:** Next-phase evidence is complete, truthful, reproducible, and sufficient to choose one later retrieval implementation plan.

## Verification

- `uv run pytest -q tests/test_embeddings.py tests/test_evidence.py tests/test_validator.py tests/test_benchmark_requirement_support.py`
- `uv run python scripts/benchmark_requirement_support.py --arm current-hash --pool-size 4 --output .tmp/retrieval-current-hash.json`
- `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 4 --output .tmp/retrieval-lexical-4.json`
- `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 8 --output .tmp/retrieval-lexical-8.json`
- `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 12 --output .tmp/retrieval-lexical-12.json`
- `git diff --check`
- Direct backend probes: configured model versus actual backend identity, disabled semantic path, unchanged shortlist embedding output, canonical/retrieved/selected loss, valid and invalid grounding fixtures.

## Completion Criteria

The plan is ready for completion verification when:

1. Diagnostics identify actual CV-analysis embedding backend, configured model,
   dimension, and contract fingerprint without changing vectors or shortlist
   behavior.
2. Benchmark fixtures cover supported, unsupported, synonym, wrong-ID, and
   responsibility-only cases with every requirement represented.
3. Current hash-enabled and lexical-only pool-4 arms run on identical inputs and
   report comparable coverage, loss, timing, context, and validation metrics.
4. Lexical pool-8 and conditional pool-12 measurements separate retrieval loss
   from selection-budget loss without changing production defaults.
5. Direct-support recovery is reported only as a bounded opportunity metric and
   any production decision is explicitly deferred to P1-B.
6. No real provider access, shortlist behavior, persisted vector contract,
   final `top_k`, generation budget, or unrelated dirty file changes occur.
7. Focused tests, direct backend probes, benchmark outputs, docs, and Git diff
   reconcile with current repository truth.

Execution completed after approval. Fresh verification returned `verified`.
