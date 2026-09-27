---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0-retrieval-evidence-qualifiers
date: 2026-09-27
targets:
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - scripts/benchmark_ranking.py
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/preference_policy.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_ranking_evaluation.py
  - tests/test_embeddings.py
  - tests/test_vector_search.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - docs/pipeline.md
  - docs/configuration.md
---

# FitCV — P0 Retrieval, Evidence, and Qualifier Optimization Plan

## Goal

Improve FitCV job retrieval, evidence preservation, and requirement accuracy
without changing the top-level pipeline or creating a second source of truth.

P0-A, P0-B, and P0-C remain independently measurable. Production defaults stay
unchanged until each change passes its contract, correctness, and performance
gate.

## Review Reconciliation

Three independent reviews found these justified corrections:

- Existing completed retrieval and impact plans already own baseline metrics.
  Reuse their fixtures and results; do not recreate competing benchmarks.
- Existing benchmark runners hardcode four arms. Add an explicit arm registry
  before introducing any future arm; never claim a provider arm ran when no
  provider, model, or dependency exists.
- Real multilingual embeddings require separate approval for provider access or
  dependency changes. This plan defines the seam and gate, not an automatic
  provider rollout.
- Direct-support recovery remains a gated production change. Benchmark first,
  then promote only after bounded-candidate and context-cost proof.
- Existing `selected_support` and `support_strength` fields are compatibility
  contracts. Qualifier detail must be additive; replacing `verified` with new
  status values would break validation and generation consumers.
- Embedding contract changes already invalidate dependent runtime state in some
  paths but can raise on mismatch. Any new backend must define stale-state
  fallback before promotion.

## Implementation Outcomes

### Canonical experiment contract

Existing retrieval, support, and RAG-impact fixtures remain SSOT. Benchmark arms
are registry-driven, report `not_run` with a reason when capability or approval
is absent, and preserve current baseline results.

### Job retrieval experiment

FitCV can compare current deterministic shortlist vectors, lexical/taxonomy
ranking, and a separately approved multilingual backend under identical eligible
jobs and Top-N limits. Backend identity, model, dimension, summary schema, and
contract fingerprint are explicit. Existing production behavior remains the
fallback until promotion.

### Support-preserving evidence retrieval

Known canonical requirement support enters selection before channel truncation,
with deterministic bounds and provenance. Pool support and selected support
remain separate. No candidate receives fabricated semantic similarity.

### Qualifier-aware requirement audit

`requirement_coverage` gains additive qualifier evidence such as source wording,
context, duration, and proficiency resolution. Existing `selected_support` and
`support_strength` values remain unchanged and continue to drive current
validator and generator behavior.

### Safe promotion evidence

Each promoted arm has held-out recall/support evidence, latency and context-cost
comparison, failure-path proof, compatibility proof, and a rollback path to the
current deterministic behavior.

## Execution Approach

- Mode: `parallel-capable`
- Coordination mode: `plan-bound-execution`
- Coordination: `git-tracked`
- Required skills: `skill-chief-of-staff`, `skill-performance-optimization`, `skill-backend-verification`, `skill-systematic-debugging`, `skill-test-driven-development`, `skill-verification-before-completion`, `skill-plan-document-reviewer`
- Isolation: `new clean worktree; preserve current dirty primary checkout`
- Commit policy: `no commits during execution`
- Preauthorized local actions: `inspect source, edit listed files, run offline tests and benchmarks, write ignored benchmark reports`
- User-approval actions: `provider calls, credentials, dependency or lockfile changes, production default changes, persisted schema migration, push, merge, publication, destructive cleanup`
- Parallel ownership: `Task 2 owns P0-A retrieval files; Task 3 owns P0-B evidence files. Task 1 is the shared prerequisite; Task 4 follows Task 3 because both touch evidence contracts; Task 5 is Codex-only fan-in.`
- Sequential fallback: `reconcile existing evidence → Task 1 → dispatch Tasks 2–3 in parallel → Task 4 → Task 5 final verification`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-p0-retrieval-evidence-qualifiers`
- Base commit: `71e6260dbaa507a2ffe3640c179e60a569551e2b` (`HEAD` and `origin/main`; requested review commit `a40416a46f8f25f76329ff38131230d574043ddf` is an ancestor)
- Expected workspace: `clean task-owned worktree; preserve current primary checkout deletions, untracked files, and untracked plans`
- Next action: `preserve integration worktree for user disposition; no push, merge, or publication`
- Blockers: `provider-backed P0-A arm remains approval-gated; P0-B direct-support recovery remains default-off; no push or merge authority`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-task1\JOB-PROJECT` | `codex` | none | `28 passed`; unsupported arms report `not_run`; fixture `d0ce5b4e52addfc1be2a107dd7900892e84733a34cc341ad003bdf6f102f7d40` | complete |
| Task 2 | `completed` | `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-task2\JOB-PROJECT` | `codex` | Task 1 | `58 passed, 2 skipped`; ranking recall `1.0`; nDCG `1.0`; p50 `27.73 ms`; p95 `29.07 ms`; provider calls `0` | complete |
| Task 3 | `completed` | `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-task3\JOB-PROJECT` | `codex` | Task 1 | `91 passed`; canonical/pool/selected separation; bounded recovery; default `false` | complete |
| Task 4 | `completed` | `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-task4\JOB-PROJECT` | `codex` | Task 3 | `193 passed`; qualifier parsing, unsupported/unavailable filtering, legacy compatibility | complete |
| Task 5 | `completed` | `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-integration\JOB-PROJECT` | `codex` | Tasks 2, 3, 4 | `270 passed, 2 skipped`; benchmark reports in `C:\tmp\fitcv-p0-integration-evidence`; docs reconciled; rollback recorded | complete |

### Final evidence

- Integration worktree: `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-integration\JOB-PROJECT`
- Focused suite: `270 passed, 2 skipped in 3.32s`
- Ranking benchmark: shortlist recall `1.0`, ranking recall `1.0`, nDCG `1.0`, p50 `27.2455 ms`, p95 `28.6723 ms`, LLM calls `0`
- Support benchmark: fixture SHA-256 `d0ce5b4e52addfc1be2a107dd7900892e84733a34cc341ad003bdf6f102f7d40`; provider calls `false`; direct-support recovery remains opt-in
- Promotion: promote deterministic retrieval diagnostics, stale-state fallback, and additive qualifier audit; do not promote provider-backed retrieval or enable direct-support recovery by default
- Rollback: disable `cv_analysis.direct_support_recovery.enabled`; restore incumbent retrieval strategy; invalidate only state carrying incompatible embedding contract fingerprints

### CoS MAIN AGENT lane contracts

| Lane | Task | Ownership and allowed paths | Depends on | Proof obligation | Runtime grant |
| --- | --- | --- | --- | --- | --- |
| `fitcv-p0-task1` | Task 1 | Benchmark registry: `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`; inspect ranking artifacts only | target/base and fixture reconciliation | Existing arms and compatibility tests pass; unsupported arms report `not_run` | `codex`; native turns and wall clock; child agents denied; filesystem, Git, shell only; no provider, credentials, push, merge, or production defaults |
| `fitcv-p0-task2` | Task 2 | P0-A only: `src/fitcv/embeddings.py`, `src/fitcv/vector_search.py`, `scripts/benchmark_ranking.py`, `tests/test_embeddings.py`, `tests/test_vector_search.py`, `tests/test_ranking_evaluation.py` | Task 1 | Retrieval comparison, truthful fingerprint, stale-state fallback, and compatibility tests | `codex`; native turns and wall clock; child agents denied; filesystem, Git, shell only; no provider, credentials, push, merge, or production defaults |
| `fitcv-p0-task3` | Task 3 | P0-B only: `src/fitcv/evidence.py`, `tests/test_evidence.py`, `tests/test_benchmark_requirement_support.py`, optional `config/policy/cv_analysis.yaml` rollout flag | Task 1 | Bounded support-pair recall, dedupe, selection-loss, and budget tests | `codex`; native turns and wall clock; child agents denied; filesystem, Git, shell only; no provider, credentials, push, merge, or production defaults |
| `fitcv-p0-task4` | Task 4 | P0-C only: `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`, `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, optional `tests/test_enrich.py` | Task 3 | Qualifier audit and legacy `verified` compatibility tests | `codex`; native turns and wall clock; child agents denied; filesystem, Git, shell only; no provider, credentials, push, merge, or production defaults |
| `fitcv-p0-task5` | Task 5 | Codex controller only: `docs/pipeline.md`, `docs/configuration.md`, this plan ledger, all changed files for inspection | Tasks 2–4 | Full declared suite, benchmark comparison, promotion decision, rollback proof | Controller-owned; no MAIN AGENT dispatch; no provider, credentials, push, merge, or publication |

## Task Breakdown

### Task 1: Reconcile benchmark contracts and arm registry

**Purpose:** Use existing benchmark work as SSOT and make future experiment arms
explicit instead of adding unsupported provider claims.

**Task Function:** Benchmark-contract maintenance and baseline reconciliation.

**Template Profile:**
- Controller-selected: `normal`

**Specification Coverage:** Phase 0, existing retrieval baseline, active RAG-impact suite.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:**

- Inspect: `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`, `scripts/benchmark_ranking.py`
- Modify: benchmark arm registry and comparison handling only where current hardcoded arms block explicit future arms
- Modify: `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py`
- Inspect only: `tests/test_ranking_evaluation.py`
- Inspect: `docs/superpowers/plans/2026-09-25-fitcv-retrieval-baseline-and-recall-measurement-plan.md`, `docs/superpowers/plans/2026-09-25-fitcv-rag-impact-test-suite-plan.md`

**Dependencies:** Confirm target commit and active fixture versions.

**Authority:**

- Preauthorized local actions: `edit benchmark registry/comparison code and tests; run existing offline arms; write ignored reports`
- Stop for: `provider execution, fixture replacement, threshold changes, production retrieval changes, or edits outside listed benchmark files`

**Steps:**

1. Confirm existing four arms and their recorded outputs.
2. Replace duplicated arm lists with one local registry or equivalent SSOT.
3. Allow future arms to report `not_run` plus reason without contaminating
   baseline comparisons.
4. Keep current baseline names and metric meanings backward-compatible.
5. Make active RAG-impact fixtures and completed retrieval results canonical;
   do not create another corpus.

**Verification:**

```text
uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_ranking_evaluation.py
```

**Exit Criteria:** Existing arms produce unchanged metrics; unsupported arms
fail clearly or report `not_run`, never silently fall back to another arm.

### Task 2: P0-A shortlist retrieval seam and safe migration

**Purpose:** Make job-retrieval experiments truthful and make backend changes
safe without replacing the current deterministic backend prematurely.

**Task Function:** Retrieval backend contract, benchmark integration, and
runtime-state compatibility.

**Template Profile:**
- Controller-selected: `normal`

Provider-backed work requires separate approval.

**Specification Coverage:** P0-A job retrieval, embedding contract fingerprint,
cache and preference compatibility.

**Required Skills:** `skill-performance-optimization`, `skill-backend-verification`, `skill-systematic-debugging`.

**Files And Symbols:**

- Inspect: `src/fitcv/embeddings.py:generate_embedding`, `build_embedding_contract_fingerprint`, `embed_and_store_jobs`
- Inspect: `src/fitcv/vector_search.py:run_vector_search`, `build_candidate_query_embedding_contract_fingerprint`
- Inspect: `src/fitcv/preference_policy.py` runtime-contract and vector-dimension mismatch handling
- Modify: `src/fitcv/embeddings.py`, `src/fitcv/vector_search.py` only for explicit backend metadata, experiment seam, and compatibility behavior
- Modify: `scripts/benchmark_ranking.py` and `tests/test_ranking_evaluation.py` for current deterministic and lexical arms
- Modify: `tests/test_embeddings.py`, `tests/test_vector_search.py`

**Dependencies:** Task 1. Real multilingual backend also requires explicit
provider/dependency approval and a declared model/runtime owner.

**Authority:**

- Preauthorized local actions: `add offline retrieval-arm plumbing, backend metadata, fingerprint tests, and stale-state fallback tests without provider calls or default changes`
- Stop for: `provider calls, credentials, new dependency or lockfile edits, persisted vector migration, preference schema migration, or production default promotion`

**Steps:**

1. Prove current production path uses persisted deterministic vectors and record
   actual backend identity separately from configured model name.
2. Keep current deterministic output and dimension unchanged for default runs.
3. Add experiment metadata for backend, model, dimension, summary schema, and
   retrieval strategy; include all in the experiment fingerprint.
4. Ensure candidate-query and job-vector fingerprints cannot reuse vectors or
   preference state across incompatible representations.
5. Change stale preference/runtime mismatch handling from an unhandled crash to
   explicit stale-state rejection and deterministic fallback, preserving current
   behavior when contracts match.
6. Extend benchmark registry only after the arm can provide actual backend
   evidence. A provider-backed multilingual arm remains `not_run` until approved.
7. Compare identical eligible jobs and Top-N values using relevant-job recall@N;
   report latency, missing/invalid vectors, cost, and provider calls where
   applicable.

**Verification:**

```text
uv run pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_ranking_evaluation.py
```

Run existing offline ranking/retrieval benchmark with current deterministic and
lexical arms. Provider-backed results are required only for a later approved
activation.

**Exit Criteria:** Default retrieval behavior stays unchanged; fingerprints are
truthful; stale state falls back safely; no provider arm is labeled successful
without backend evidence. Promotion requires held-out recall@N strictly above
incumbent and p95 latency/cost within an owner-approved budget. Without an
approved budget, results remain exploratory.

### Task 3: P0-B bounded direct-support recovery

**Purpose:** Prevent approved requirement support from disappearing during
channel truncation while preserving one global evidence budget.

**Task Function:** Evidence candidate-union and selection correctness.

**Template Profile:**
- Controller-selected: `normal`

**Specification Coverage:** P0-B direct support, retrieval-to-selection loss,
canonical/pool/selected support separation.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`.

**Files And Symbols:**

- Inspect: `src/fitcv/evidence.py:_select_channel_candidates`, `_merge_channel_pools`, `_annotate_requirement_support`, `_select_final_evidence`, `retrieve_evidence_bundle`
- Modify: `src/fitcv/evidence.py`
- Modify: `tests/test_evidence.py`, `tests/test_benchmark_requirement_support.py`
- Update: `config/policy/cv_analysis.yaml` only if an explicit rollout flag is required

**Dependencies:** Task 1. Production promotion requires a separate review of
benchmark evidence; default remains off until then.

**Authority:**

- Preauthorized local actions: `implement bounded direct-support candidate recovery, preserve provenance, add focused tests, and run offline support benchmarks`
- Stop for: `unbounded candidate union, global top_k or context-budget changes, ANN/index work, provider calls, or production-default promotion without gate evidence`

**Steps:**

1. Build deterministic direct-support candidates from canonical approved links.
2. Union them with lexical and semantic candidates before final selection.
3. Preserve direct-support provenance without fabricating channel scores.
4. Bound recovery: retain at least one deterministic representative per
   requirement, then allow only a bounded overflow tied to `top_k`; dedupe by
   `evidence_id`.
5. Keep `canonical`, `pool`, and `selected` support maps distinct.
6. Verify selection can intentionally omit support under budget, but reports
   omission as selection loss rather than unsupported candidate evidence.
7. Benchmark current truncation, bounded recovery, and full-pool scoring. Do not
   add ANN unless measured pool size makes full-pool scoring materially costly.

**Verification:**

```text
uv run pytest -q tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_agentic_cv_analysis.py
```

**Exit Criteria:** Approved support-pair recall improves or remains equal,
duplicate IDs stay zero, recovered candidates remain bounded, selected context
stays within existing budget, and unsupported-claim rate does not increase.

### Task 4: P0-C additive qualifier audit

**Purpose:** Distinguish canonical skill support from support for duration,
context, action, and proficiency requirements without breaking existing
generation and validation contracts.

**Task Function:** Conservative requirement parsing and additive coverage audit.

**Template Profile:**
- Controller-selected: `normal`

**Specification Coverage:** P0-C qualifier-aware requirements.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:**

- Inspect: `src/fitcv/evidence.py:build_required_skill_descriptors`
- Modify: `src/fitcv/evidence.py` descriptor derivation and qualifier-support helpers
- Modify: `src/fitcv/agentic_cv_analysis.py:_build_requirement_coverage`
- Inspect and preserve: `src/fitcv/validator.py`, `src/fitcv/cv_generator.py`, `src/fitcv/agentic_cv_analysis.py` existing `verified` consumers
- Modify: `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`
- Modify: `tests/test_enrich.py` only if raw requirement wording is lost upstream

**Dependencies:** Task 1. Existing `selected_support` and `support_strength`
remain authoritative compatibility fields.

**Authority:**

- Preauthorized local actions: `add derived qualifier parsing, additive audit fields, conservative support mapping, and focused regression tests`
- Stop for: `new requirement graph, LLM qualifier inference, replacement of legacy support values, unapproved schema migration, or unsupported threshold invention`

**Steps:**

1. Derive qualifiers from retained raw requirement wording and existing job
   fields; do not add a second canonical requirement store.
2. Support additive fields such as `source_text`, `qualifiers`, and
   `qualifier_support` with unresolved qualifier names.
3. Use conservative deterministic rules:
   - explicit date ranges may support duration;
   - explicit normalized context/tags may support context;
   - explicit proficiency or language-level evidence may support level;
   - absence means `unverified`, not `contradicted`;
   - contradiction requires explicit conflicting evidence.
4. Keep `selected_support: "verified"` only when existing canonical support and
   all decisive qualifiers are supported. Otherwise preserve existing values
   such as `relevant_unverified`, `not_selected`, or `unsupported`.
5. Expose richer qualifier detail as audit data; do not make validator or
   generator consumers switch to new status names in this task.
6. Add cases for plain skill, duration, production context, proficiency,
   contradictory language level, missing qualifier, alias collapse, and no
   positional pairing of independent raw/canonical arrays.

**Verification:**

```text
uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py tests/test_cv_generator.py
```

**Exit Criteria:** Qualifier gaps are visible and conservative; existing
`verified`-based validation and generation behavior remains compatible; no
unsupported claim becomes verified through similarity alone.

### Task 5: Promotion decision and final verification

**Purpose:** Reconcile results, promote only proven changes, and leave a clear
rollback path.

**Task Function:** Integration verification and decision record.

**Template Profile:**
- Controller-selected: `normal`

Controller selects validator independently.

**Specification Coverage:** All implementation outcomes and promotion gates.

**Required Skills:** `skill-plan-document-reviewer`, `skill-verification-before-completion`, `skill-backend-verification`, `skill-performance-optimization`.

**Files And Symbols:**

- Update: `docs/pipeline.md`, `docs/configuration.md`
- Update: this plan's task ledger and evidence links
- Inspect: all changed files and benchmark reports

**Dependencies:** Tasks 2–4 complete with fresh proof.

**Authority:**

- Preauthorized local actions: `run focused and declared full verification, reconcile documentation, record promotion or no-promotion decisions, and preserve ignored reports`
- Stop for: `promotion without gate evidence, threshold changes after measurement, provider/dependency approval gaps, unrelated cleanup, push, merge, or publication`

**Steps:**

1. Run focused tests for all changed owners.
2. Run canonical benchmark commands from existing plans and compare against
   recorded baseline under identical workload and environment.
3. Verify backend success, fallback, stale-state, bounded-recovery, and
   compatibility failure paths.
4. Promote only arms with owner-approved metric and safety gates; otherwise keep
   experiment output and leave current defaults active.
5. Update docs only from canonical implementation/configuration behavior.
6. Record rollback: disable experiment flag or restore incumbent backend and
   invalidate only incompatible derived state.

**Verification:**

```text
uv run pytest -q tests/test_embeddings.py tests/test_vector_search.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py tests/test_cv_generator.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_ranking_evaluation.py
```

**Exit Criteria:** Fresh tests pass; benchmark outputs are reproducible; all
promotion decisions are explicit; production defaults remain unchanged for any
arm lacking approval or evidence; plan ledger records final proof.

## Verification

Required evidence:

- Existing benchmark fixtures remain unchanged unless contract tests justify a
  versioned additive change.
- Current deterministic and lexical arms reproduce prior baseline results.
- P0-A reports actual backend identity and safe stale-state behavior.
- P0-B reports canonical, pool, selected, and validation support separately.
- P0-C preserves legacy `verified` consumers and reports qualifier gaps without
  inventing support.
- Performance comparisons use identical workload, warm/cold condition, and
  environment; report p50/p95 latency, context tokens, and provider calls when
  applicable.
- No provider, credentials, dependency, persisted schema, or production-default
  change occurs without explicit approval.

## Completion Criteria

1. Plan tasks have terminal states and linked evidence.
2. Existing retrieval and RAG-impact work remains the benchmark SSOT.
3. No unsupported multilingual-provider result is presented as measured.
4. Direct support recovery is bounded and separately promoted.
5. Qualifier audit is additive and legacy support contracts remain valid.
6. Current production behavior remains a tested rollback path.
7. Documentation matches canonical code and configuration ownership.

Skipped: GraphRAG, retrieval agents, ANN, late-interaction retrieval, LLM
reranking, learned routing, dynamic skill graph, and preference-learning
changes. Add only after P0 residual errors and cost are measured.
