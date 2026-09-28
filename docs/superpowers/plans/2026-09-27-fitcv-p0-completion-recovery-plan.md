---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-p0-completion-recovery

targets:
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/evidence.py
  - src/fitcv/embeddings.py
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - scripts/benchmark_ranking.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_embeddings.py
  - tests/test_evidence.py
  - tests/test_vector_search.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_compare_requirement_support.py
  - tests/test_ranking_evaluation.py
  - data/fitcv-p0-corpus/README.md
  - data/fitcv-p0-corpus/p0a/admission_report.json
  - data/fitcv-p0-corpus/p0a/ranking_source_backed.json
  - data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl
  - data/fitcv-p0-corpus/p0b/candidate_evidence_projection.jsonl
  - data/fitcv-p0-corpus/p0b/projection_manifest.json
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence.jsonl
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_manifest.json
  - docs/pipeline.md
  - docs/configuration.md
---

# FitCV P0 Completion: Recovery and Reconciliation

## Verdict review

The verdict is materially correct.

- `73e7e863` is an empty merge relative to its parents; `origin/main` at `92dc4f02` lacks the runtime and benchmark changes from `3ecadc99` and `01f20a8f`.
- Current checkout `1e911e51` contains those changes. Use it as recovery source; do not reimplement P0.
- P0-C needs exact requirement identity and evidence-local qualifier proof.
- P0-A needs production and resumed-pipeline fallback wiring plus a discriminative source-backed ranking benchmark.
- P0-B needs qualified-support metrics and broader reviewed labels before production-recall promotion.
- User-approved public status for `data/fitcv-p0-corpus` removes privacy/publication blocking. The stale README privacy wording must be corrected; no history purge belongs in this plan.

## Goal

Land one correction PR from `origin/main` `92dc4f02` that restores the accepted runtime/test delta, closes P0-C correctness, and closes P0-A runtime safety and benchmark plumbing without adding a new retrieval model or agent.

P0-B remains benchmark-only. Production promotion is explicitly out of scope until reviewed coverage and a separate acceptance decision exist.

## Non-goals

- No new embedding provider, reranker, graph, agent, or dependency.
- No production default switch based on synthetic or non-discriminative metrics.
- No deletion of hash-semantic retrieval until qualified-support comparison proves lexical parity or improvement.
- No P1-A, P1-B, latency redesign, or end-to-end UX work.
- No P0-A ranking promotion from the current all-positive corpus; do not synthesize negative labels.
- No P0-B reviewed-label expansion or public-recall promotion in this correction PR.
- No corpus history rewrite; `data/fitcv-p0-corpus` is approved for public publication.

## Base and recovery source

- Target base: `origin/main` `92dc4f02`.
- Recovery source: current checkout `1e911e51`, containing `3ecadc99` and `01f20a8f` changes.
- Execute in a clean worktree. Preserve current checkout dirty/untracked files.
- Selectively apply runtime, benchmark, and test changes; handle corpus metadata and maintained docs through their owned tasks. Do not restore the older active plan wholesale.

## Execution approach

- Mode: `inline sequential`.
- Coordination: `none`; one controller owns ordered edits and final verification.
- Executor: `codex` in a clean task worktree created from `origin/main`.
- Required skills: `skill-using-git-worktrees`, `skill-code-standards`, `skill-backend-verification`, `skill-test-driven-development`, and `skill-verification-before-completion`.
- Commit policy: no implementation commits during execution; final Git disposition requires separate authorization.
- Shared-write control: runtime contracts, pipeline callers, benchmark scripts, tests, docs, and corpus metadata are serialized by task order.
- Sequential fallback: if worktree creation is unavailable, stop before edits and use a clean checkout; never edit current dirty checkout.

## Task 1: Recover implementation and prove integration

**Purpose:** Restore accepted runtime and test changes onto current `origin/main` without reintroducing superseded plan decisions.
**Task Function:** Recovery, baseline binding, and integration-diff inspection.
**Template Profile:** `unresolved`; resolve executor profile before activation.
**Specification Coverage:** Integration-loss recovery, current-base binding, preserved user work, and visible semantic delta.
**Required Skills:** `skill-using-git-worktrees`, `skill-code-standards`.
**Files And Symbols:** Declared runtime, benchmark, test, `docs/pipeline.md`, and `docs/configuration.md` paths; `run_vector_search`; `_assess_requirement_support`; ranking and support benchmark entrypoints.
**Dependencies:** None.
**Authority:** May create isolated worktree, inspect Git history, and apply only declared recovery paths. Stop on unexpected path changes, unresolved contract conflict, or dirty-worktree access.

**Steps:**

1. Create clean branch/worktree from `origin/main`.
2. Generate `.tmp/p0/recovery.patch` with `git diff origin/main 1e911e51 -- src/fitcv scripts tests docs/pipeline.md docs/configuration.md`; do not use a commit-range patch because `1e911e51` is an ancestor of `origin/main`.
3. Apply only runtime, benchmark, test, and `docs/pipeline.md`/`docs/configuration.md` changes. Treat corpus files and public metadata as Task 6-owned changes.
4. Resolve conflicts by source authority: runtime contracts and tests win over plan prose; `origin/main` publication/deferral decisions win over older plan text.
5. Confirm changed paths include runtime, scripts, tests, and both maintained docs before running tests.
6. Confirm required symbols exist: `run_vector_search` requested/effective strategy diagnostics, `_assess_requirement_support`, requirement-instance descriptors, held-out ranking evaluation, and qualified-support comparison.

**Verification:**

- `git diff --name-status origin/main...HEAD` shows intended `src/`, `scripts/`, `tests/`, `docs/pipeline.md`, and `docs/configuration.md` paths.
- `git diff --check` passes.
- `rg -n "legacy_values|next\(iter\(mapped.values" src/fitcv/agentic_cv_analysis.py` returns no unsafe cardinality fallback.

**Exit Criteria:** Recovered semantic delta is visible in candidate tree; no empty-merge ambiguity remains.

## Task 2: Close P0-C exact-support and qualifier semantics

**Purpose:** Make qualified support identity-safe and evidence-local.
**Task Function:** Backend contract correction and regression proof.
**Template Profile:** `unresolved`; resolve executor profile before activation.
**Specification Coverage:** Exact requirement identity, qualifier conjunctions, contradiction handling, duplicate instances, and reuse invalidation.
**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`.
**Files And Symbols:** `src/fitcv/agentic_cv_analysis.py:_support_ids_by_requirement`; `src/fitcv/evidence.py:build_required_skill_descriptors`, `_assess_requirement_support`, `_requirement_support_map`; named tests below.
**Dependencies:** Task 1.
**Authority:** May edit only listed runtime and tests. Stop on validator/generator contract changes or any need for cross-evidence support.

**Steps:**

1. Resolve support by exact `requirement_instance_id` first.
2. Permit exact legacy `requirement_id` only when descriptor explicitly supplies that compatible identity.
3. Return unsupported on missing identity. Never select the only value in an unrelated map.
4. Keep `canonical_requirement_ids`, `supported_requirement_ids`, `requirement_assessments`, `selected_support`, and `support_strength` contracts compatible.
5. Evaluate all decisive qualifiers against one evidence item. Do not combine duration from one item with context or level from another.
6. Preserve comparator semantics: `more than N years` is `gt`; `at least N years` and `N+ years` are `gte`.
7. Require every term in compound context (`enterprise` and `production`) and reject explicit negation.
8. Preserve duplicate requirement instances as distinct references and invalidate reused support when requirement/evidence fingerprints change.

**Verification:**

- exact instance match;
- exact compatible legacy match;
- missing identity does not fall back by map cardinality;
- same-evidence duration plus context qualifies;
- split-evidence duration/context does not qualify;
- `gt` versus `gte` boundary;
- compound context requires all terms;
- negation becomes contradicted;
- duplicate canonical skills keep distinct requirement instances;
- support reuse invalidates on fingerprint change.

**Exit Criteria:** No qualified support exists without same-evidence canonical and decisive qualifier proof; compatibility tests pass.

## Task 3: Restore P0-A fallback wiring and truthful diagnostics

**Purpose:** Ensure full and resumed pipelines pass structured jobs and preserve requested retrieval strategy when vector data is unavailable.
**Task Function:** Backend integration and direct boundary verification.
**Template Profile:** `unresolved`; resolve executor profile before activation.
**Specification Coverage:** Deterministic fallback, truthful diagnostics, caller parity, and shared strategy constants.
**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`.
**Files And Symbols:** `src/fitcv/vector_search.py:run_vector_search`; `src/fitcv/pipeline.py`; `src/fitcv/pipeline_stage_runner.py`; corresponding vector, pipeline, and resume-parity tests.
**Dependencies:** Task 1.
**Authority:** May edit listed runtime callers and tests. Stop on provider, schema, dependency, or production-default changes.

**Steps:**

1. Pass `structured_jobs=passed_jobs` from full and resumed/stage retrieval callers.
2. Pass `requested_strategy=VECTOR_RETRIEVAL_STRATEGY` explicitly from production callers.
3. Keep compatible vectors on vector retrieval.
4. Use deterministic lexical fallback only when requested vector data is missing, stale, invalid, incompatible, or unavailable.
5. Preserve diagnostics fields: requested strategy, effective strategy, fallback flag/reason, backend ID, contract fingerprint, eligible/scored/shortlist counts.
6. Keep unavailable fallback data as an explicit unavailable result; do not silently change strategy or invent rows.
7. Assert full and resumed paths produce equivalent retrieval envelope and diagnostics for the same input.

**Required tests:**

- missing job embeddings;
- incompatible/stale embedding contract;
- invalid job embeddings;
- incompatible embedding contract;
- missing candidate query embedding;
- lexical request with structured jobs;
- fallback data unavailable;
- full pipeline caller passes structured jobs;
- resumed/stage caller passes the same arguments and preserves envelope parity.

**Verification:** Each named fallback reason is asserted, including `candidate_embedding_unavailable` and `invalid_job_embeddings`; resume mocks assert `structured_jobs` and `requested_strategy`; stage runner imports shared `VECTOR_RETRIEVAL_STRATEGY`.
**Exit Criteria:** Operator gets deterministic fallback without intervention; diagnostics tell truth about requested and effective strategy.

## Task 4: Restore P0-A ranking evidence reporting

**Purpose:** Restore held-out ranking evaluation plumbing without claiming promotion from an all-positive corpus.
**Task Function:** Benchmark contract repair and evidence classification.
**Template Profile:** `unresolved`; resolve executor profile before activation.
**Specification Coverage:** Source-backed DE/EN split reporting, evaluator-field isolation, URL/ID mapping, latency, and explicit promotion block.
**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-code-standards`.
**Files And Symbols:** `scripts/benchmark_ranking.py:main`, `_split_metric_rows`; `tests/test_ranking_evaluation.py`; `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`.
**Dependencies:** Task 1.
**Authority:** May repair benchmark code and tests. Do not synthesize negative labels, add a backend, or change production retrieval defaults.

**Steps:**

1. Keep source-backed DE/EN language and calibration/held-out splits.
2. Run the admitted 100-row source-backed fixture for plumbing and held-out reporting. Record that its all-positive candidate composition cannot support production ranking promotion; do not synthesize negatives.
3. Keep evaluator-only fields out of retrieval requests and retain URL/ID mapping repair from `01f20a8f`.
4. Evaluate retrieval before ranking with `Recall@20`, `Precision@20`, `nDCG@20`, false-negative count, p50, and p95.
5. Report calibration and held-out metrics separately for DE and EN.
6. Keep multilingual backend arm `not_run` when no approved backend is available. Do not add infrastructure only to fill that arm.

**Verification:**

- `fixture_role` reports `source_backed` for `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`.
- Calibration and held-out DE/EN metrics, false-negative count, p50, and p95 are reproducible.
- Report explicitly states `ranking_promotion: blocked_all_positive_corpus`; no numerical promotion threshold is invented for this PR.

**Exit Criteria:** P0-A runtime/benchmark plumbing is restored; ranking promotion remains explicitly blocked until a separately admitted mixed-label corpus exists.

## Task 5: Preserve P0-B qualified-support benchmark

**Purpose:** Preserve qualified-support benchmark diagnostics and keep production promotion explicitly deferred.
**Task Function:** Benchmark comparison and gate-status reporting.
**Template Profile:** `unresolved`; resolve executor profile before activation.
**Specification Coverage:** Canonical versus qualified support metrics, false-qualified detection, selection loss, context cost, validation, and deferral status.
**Required Skills:** `skill-test-driven-development`, `skill-code-standards`.
**Files And Symbols:** `scripts/benchmark_requirement_support.py:run_benchmark`, `scripts/compare_requirement_support.py:run_inputs`; benchmark and comparison tests; public P0-B manifests.
**Dependencies:** Task 2.
**Authority:** May edit benchmark scripts/tests and record metrics. Do not add a corpus adapter, label expansion, provider call, or production promotion in this correction PR.

**Steps:**

1. Preserve current selection arm and full-pool comparison; do not add recovery complexity.
2. Run existing synthetic current/full-pool arms on identical inputs and budgets.
3. Report canonical support recall separately from qualified support recall.
4. Report qualified support precision, false-qualified count, retrieval-to-selection loss, context size, p95, duplicate count, and validation outcome.
5. Include `promotion_status: blocked_reviewed_coverage` because the public reviewed sample remains 10 pairs across 3 postings.

**Verification:** Existing CLI runs without new flags; comparison output contains all named metrics and explicit block status.
**Exit Criteria:** Benchmark distinguishes canonical skill retrieval from valid qualified support; P0-B production promotion remains explicitly blocked pending a separately approved reviewed-label expansion.

## Task 6: Reconcile public corpus metadata and documentation

**Purpose:** Align public-corpus approval, provenance metadata, and maintained documentation.
**Task Function:** Documentation and metadata reconciliation.
**Template Profile:** `unresolved`; resolve executor profile before activation.
**Specification Coverage:** Public publication boundary, repository-relative provenance, truthful tracking status, runtime diagnostics, and deferred promotion.
**Required Skills:** `skill-code-standards`.
**Files And Symbols:** `data/fitcv-p0-corpus/README.md`, `data/fitcv-p0-corpus/p0a/admission_report.json`, `data/fitcv-p0-corpus/p0b/projection_manifest.json`, `data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence.jsonl`, `docs/pipeline.md`, `docs/configuration.md`.
**Dependencies:** Tasks 2–5.
**Authority:** May edit approved public metadata and maintained docs. Stop on unapproved data removal, history rewrite, credential exposure, or content publication beyond the user-approved corpus directory.

**Steps:**

1. Replace stale local/private wording with explicit public-corpus approval and sanitized/public contents boundary.
2. Keep candidate profile YAML and original CV files excluded; replace absolute workstation and `data.private` references in committed manifests with repository-relative provenance.
3. Correct notes that claim raw corpus is untracked when `data/fitcv-p0-corpus` is tracked; preserve hashes, row counts, language/split counts, and benchmark-only P0-B status.
4. Align pipeline/config docs with actual fallback, support identity, diagnostics, and deferred promotion behavior.
5. Do not rewrite Git history or remove already-approved public corpus files.

**Verification:** `rg -n "C:\\Users\\|data\.private|keep this directory local/private" data/fitcv-p0-corpus` returns no matches; docs match runtime diagnostics and block statuses.
**Exit Criteria:** Public corpus policy, source metadata, runtime behavior, and docs agree.

## Task 7: Final verification and merge gate

**Purpose:** Prove cross-task integration and preserve explicit P0-A/P0-B blocks.
**Task Function:** Final verification and acceptance reconciliation.
**Template Profile:** `unresolved`; resolve executor profile before activation.
**Specification Coverage:** Focused backend proof, benchmark proof, documentation consistency, and merge-path integrity.
**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`.
**Files And Symbols:** All changed paths; final benchmark outputs under ignored `tmp/p0/`; `run_vector_search`; support and ranking benchmark entrypoints.
**Dependencies:** Tasks 2–6.
**Authority:** May run declared tests/checks and write ignored `tmp/p0/` reports. Stop on failed focused tests, missing recovery paths, unexpected production-default changes, or unverified public metadata.

**Focused commands:**

```powershell
uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_vector_search.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_compare_requirement_support.py tests/test_ranking_evaluation.py
uv run pytest -q tests/test_benchmark_requirement_support.py
uv run python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --output tmp/p0/final-ranking.json
uv run python scripts/benchmark_requirement_support.py --arm current --output tmp/p0/final-support-current.json
uv run python scripts/benchmark_requirement_support.py --arm full-pool --output tmp/p0/final-support-full-pool.json
uv run python scripts/compare_requirement_support.py --inputs tmp/p0/final-support-current.json,tmp/p0/final-support-full-pool.json --output tmp/p0/final-support-comparison.json
uv run pytest -q
git diff --check
```

**Merge gate:**

- Recovered paths are present in final diff against `origin/main`.
- P0-C focused tests pass.
- Full and resumed fallback tests pass.
- P0-A report contains source-backed DE/EN held-out metrics and latency plus `ranking_promotion: blocked_all_positive_corpus`.
- P0-B report contains qualified-support metrics and `promotion_status: blocked_reviewed_coverage`.
- No provider, dependency, credential, or production-default change is introduced.
- P1 remains deferred until P0 residual errors, latency, cost, and manual-review impact are measured.

**Verification:** Focused tests, benchmark commands, `uv run pytest -q`, `git diff --check`, and declared-path review all complete. Any full-suite failure is classified against the pre-change baseline and recorded; unrelated failures are not fixed in this PR.
**Exit Criteria:** Candidate tree contains recovered runtime/tests, truthful P0-A diagnostics, explicit P0-A/P0-B promotion blocks, public corpus metadata without local-path leakage, and no undeclared implementation paths.

## Rollback

No production-default or external-state migration occurs. If focused verification fails, do not merge. If a deployed candidate regresses, disable vector retrieval through the existing retrieval-strategy configuration and retain lexical fallback; do not roll back to `92dc4f02` while claiming fallback safety. Keep public corpus and benchmark artifacts.

## Completion definition

P0 completion means:

- P0-C exact identity and evidence-local qualifier contract passes focused regression proof.
- P0-A full/resumed fallback wiring is restored and truthful; source-backed ranking benchmark is discriminative, or its promotion remains explicitly blocked with reason and evidence.
- P0-B comparison reports qualified-support outcomes on expanded reviewed labels; production promotion occurs only if held-out gates pass.
- Public corpus metadata no longer contradicts approved publication status.
- No speculative retrieval system is added.
