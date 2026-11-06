---
layer: change
artifact_type: plan
contract_version: "1"
status: completed
template_id: implementation-plan
name: fitcv-matching-accuracy-validated-findings
targets:
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/rule_filter.py
  - src/fitcv/ranking.py
  - src/fitcv/vector_search.py
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_rule_filter.py
  - tests/test_ranking.py
  - tests/test_vector_search.py
  - tests/test_evidence.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_scoring_input_integrity.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_ranking_contract.py
  - tests/test_agentic_cv_analysis.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - data/fitcv-p0-corpus/p0c/requirement_support_benchmark.json
---

# FitCV Matching Accuracy: Validated Findings Implementation Plan

## Goal

Preserve relevant jobs and source-backed candidate evidence through enrichment,
eligibility, retrieval, scoring, ranking, and diagnostics. Unknown metadata and
enrichment/provider failures must not become confirmed incompatibility, and
facts admitted to scoring must remain attributable and visible to the scorer.

Review basis: sequential read-only reviews by `GPT-5.6-Sol` / `High` and
`GPT-6` / `High` against the published source. Source references below use
stable file/symbol locations and must be refreshed against the execution base
before implementation; unvalidated hypotheses are explicitly excluded.

Validated source evidence:

- Partial enrichment defaults mandatory channels to empty values: `src/fitcv/enrich.py` (`merge_scraped_and_enriched`, `_enrich_result_to_row`).
- Fallback jobs are retained for retrieval but rejected by the scorer contract: `src/fitcv/rule_filter.py` (`apply_rule_filters`) and `src/fitcv/ai_score.py` (`build_ranking_job_input`).
- Contract type treats missing values as mismatch: `src/fitcv/rule_filter.py` (`check_contract_type`).
- Title outcomes bypass selected-filter policy: `src/fitcv/rule_filter.py` (`apply_rule_filters`).
- Vector fallback only fills unused production capacity: `src/fitcv/vector_search.py` (`_vector_search_result`).
- Missing preference dimensions score as mismatch and neutral title scores can qualify hybrid rescue: `src/fitcv/ranking.py` (`_preference_dimension_score`, `_preference_dimension_score_with_neighbors`) and `src/fitcv/vector_search.py` (`_hybrid_search_result`).
- Scoring evidence is capped and may be reduced by request budgeting: `src/fitcv/pipeline_stage_runner.py` (`execute_ranking_stage`) and `src/fitcv/ai_score.py` (`build_ranking_request`).
- Mandatory budget overflow becomes non-retryable unscored: `src/fitcv/ai_score.py` (`run_ai_scoring`).
- A skip result blocks the richer CV-analysis evidence path: `src/fitcv/agentic_cv_analysis.py` (`analyze_ranked_job`).
- Inline and artifact diagnostics conflate retrieval absence, cutoffs, and scoring state: `src/fitcv/pipeline.py` and `src/fitcv/pipeline_stage_artifacts.py`.
- Results export normalization fabricates `legacy_ambiguous_score_state` when a row has no explicit score fields, masking intentional early-stage unscored dispositions: `src/fitcv_cp/app.py` (`_normalize_results_export_row`). Explicit scorer failures such as `budget_exceeded` must remain intact.
- The first PR review confirmed the worker export builder normalized the same rows before app projection and that legacy parser/reasoning fields were recognized by `normalize_score_state` but omitted from the export gate. The shared export normalizer now owns both decisions: `src/fitcv/ranking_contract.py` (`normalize_score_state_for_export`), used by `src/fitcv_cp/worker_job.py` and `src/fitcv_cp/app.py`.

## Implementation Outcomes

### Truthful enrichment and score states

Enrichment exposes per-channel completeness and source-backed mandatory clauses.
Fallback, incomplete, budget-exceeded, invalid, and valid scoring states remain
distinct. A failed extraction is retryable or uses an explicitly degraded raw
text contract; it is never converted into a negative compatibility result.

### Requirement-faithful admission and retrieval

Selected rule-filter settings are honored, missing contract metadata is neutral
unless explicitly configured otherwise, and vector/lexical recovery candidates
compete before the final retrieval cutoff. Missing preference dimensions do not
score as confirmed mismatches.

### Evidence-preserving scorer input

Typed language requirements, mandatory clause IDs, attributable project proof,
and model-visible evidence IDs survive scorer request construction and budget
bounding. Any verified evidence omitted from the request is explicitly recorded.

### Reconciled diagnostics and exports

Every admitted job has one terminal admission/scoring disposition. Inline,
resumed, shared-stage, control-plane, and export projections agree on retrieval
status, failure code, retry eligibility, mandatory completeness, and evidence
visibility.

The export projection also preserves intentional early-stage `unscored` rows
without inventing a failure code, while retaining explicit scorer failure codes.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit declared plan targets, add focused regression fixtures/tests, run declared local verification commands, and update this plan's task ledger
- User-approval actions: push, merge, external publication, destructive cleanup, deleting unrelated artifacts, or changing preserved scoring-policy/budget constraints
- Parallel ownership: none; enrichment, retrieval, scorer contracts, and admission manifests share cross-stage schemas
- Sequential fallback: execute Tasks 1–7 in dependency order in the current workspace

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-matching-accuracy`
- Base commit: `bdb9d25408ebc893ea922b4fc9b9336b3f928e33`
- Expected workspace: `completion-record change committed; PR #123 review pending`
- Next action: complete the authorized review cycles for PR #123, then merge the completion record into `main`
- Blockers: none; the provider-backed run completed, and the local optional-extra gap is covered by the successful CI `Full Suite`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex/high` | none | focused failing fixtures and baseline counts | 390 passed, 2 skipped in focused matching suite; fixtures cover filter, retrieval, evidence, scoring, and skip paths |
| Task 2 | `completed` | current | `codex/high` | Task 1 | enrichment/scoring state tests | fallback/degraded input remains retryable even with raw text; optional raw description is removed before budget failure; focused scoring tests pass |
| Task 3 | `completed` | current | `codex/high` | Task 1 | rule-filter tri-state tests | contract-type unknown literals remain neutral by default; `missing_contract_type_policy=reject` is wired through filtering; selected title-filter policy tests pass |
| Task 4 | `completed` | current | `codex/high` | Tasks 1 and 3 | retrieval recall and neutrality tests | all lexical fallback candidates compete with vector production rows before `effective_top_n`; displaced rows remain auditable; vector/lexical rescue, missing-preference neutrality, and evidence tests pass |
| Task 5 | `completed` | current | `codex/high` | Tasks 1 and 2 | scorer evidence/budget tests | 8-item evidence bound, visibility manifest, mandatory omissions, and 12,000-character budget tests pass |
| Task 6 | `completed` | current | `codex/high` | Tasks 2–5 | admission/export reconciliation tests | explicit empty `model_visible_evidence_ids` is persisted without falling back to selected IDs; persistence/checkpoint/sqlite suite: 403 passed |
| Task 7 | `completed` | current | `codex/high` | Tasks 2–6 | backend boundary, full pipeline, and evaluation proof | first review cycle found five confirmed issues and final review found four additional confirmed issues; all nine are patched with focused regressions; affected suite `1,093 passed, 3 skipped`; CI full suite `3,631 passed, 10 skipped, 6 deselected` on `2b9fe6ea55baecb6af7742fe076f8df713b7cf35`; final benchmark on `8d17feba5bc358cb8cb6ddd11be9c1ce9c6ed280` preserves selected evidence recall `0.9375`, selected requirement recall `1.0`, false negatives `1`; provider-backed run `cc509b7f-e4b7-40a6-8a65-11ca29711148` completed all `280` jobs with `18` valid objective scores and `32` explicit `budget_exceeded` failures, while four CV outputs remain in the expected operator-review lifecycle |

### Post-review remediation

The first independent review identified five confirmed issues and no speculative
changes are included. The execution patch preserves the approved defaults and
addresses only these contracts:

1. Keep `job_enrichment_fallback` as an unresolved mandatory omission even when
   a raw description is available; raw text is not proof that all structured
   mandatory facts survived extraction.
2. Treat `raw_description` as optional request context and remove it before
   rejecting a request whose structured mandatory contract fits the existing
   12,000-character limit.
3. Merge vector production candidates with every lexical fallback candidate,
   apply the existing `effective_top_n` once, and put displaced vector rows in
   the audit set.
4. Wire `rule_filter.missing_contract_type_policy` into classification and
   normalize common unknown literals without turning them into mismatches by
   default.
5. Preserve explicit empty model-visible evidence lists in both admission-ledger
   persistence paths instead of falling back to selected evidence.

Fresh proof after the remediation commit:

- `python -m pytest tests/test_enrich.py tests/test_ai_score.py tests/test_rule_filter.py tests/test_ranking.py tests/test_vector_search.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_settings_schema.py -q` → `1,088 passed, 3 skipped`.
- `python -m pytest -q` → `3,624 passed, 10 skipped`.
- The four requirement-support benchmark arms and comparison report use implementation ref `97ce898874524452497dff02bfb41b16d47a857e`; requirement-aware and current-hash arms agree with selected evidence-pair recall `0.9375`, selected requirement recall `1.0`, and false-negative count `1`.

The final independent review found four additional confirmed defects, all
addressed before merge:

1. Reuse the affirmative lexical-relevance predicate so neutral fallback rows
   cannot displace vector candidates.
2. Apply `vector_search_top_n` to the non-semantic backend fallback and retain
   the remainder as audit rows.
3. Remove newly admitted URLs from audit candidates after lexical recovery.
4. Merge scorer exception visibility with the normal ranking-input diagnostics
   before persistence, preserving selected evidence, mandatory omissions,
   completeness, and checksums.

The final review regressions cover each case, including a scorer-to-SQLite
rejection path. The final review agent reported `877 passed, 2 skipped` in its
independent subset; the lead rerun against the final worktree reports the
broader affected suite and full suite counts above.

Final benchmark proof on `8d17feba5bc358cb8cb6ddd11be9c1ce9c6ed280`:

- Baseline and ablation: selected evidence-pair recall `0.8125`, selected
  requirement recall `0.866667`, false negatives `3`.
- Requirement-aware and current-hash: selected evidence-pair recall `0.9375`,
  selected requirement recall `1.0`, false negatives `1`.
- Requirement-aware and current-hash agree exactly; no ordering regression is
  introduced by the final review fixes.

## Task Breakdown

### Task 1: Freeze cross-stage contracts and regression fixtures

**Purpose:** Establish exact expected states and counterexamples before changing behavior.

**Task Function:** Test and contract design.

**Template Profile:** `unresolved`; resolve through Planning Dispatch before activation.

**Specification Coverage:** All validated findings; preserved top-N and 12,000-character policies.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`.

**Files And Symbols:** `tests/test_scoring_input_integrity.py`, `tests/test_enrich.py`, `tests/test_rule_filter.py`, `tests/test_vector_search.py`, `tests/test_ranking.py`, `tests/test_evidence.py`, `tests/test_ai_score.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline.py`.

**Dependencies:** None.

**Authority:**
- Preauthorized local actions: add failing fixtures/tests and run focused tests.
- Stop for: any change to ranking policy, retrieval/scoring defaults, or request budget.

**Steps:**
1. Add fixtures for partial enrichment, full fallback, missing contract type, unselected title filters, full vector shortlist with a missing-embedding relevant job, missing preference dimensions, three-project evidence, oversized mandatory input, and a skip-before-richer-evidence case.
2. Freeze the existing score contract as `score_status ∈ {valid, unscored, invalid}`; represent `needs_enrichment` and `budget_exceeded` as disposition/failure codes, not new score-status values.
3. Assert source-backed mandatory facts are either model-visible or explicitly unresolved, and that every admitted job maps through prefilter rejection, post-enrichment rejection, retrieval cutoff, scoring, and ranking outcomes.

**Verification:** `python -m pytest tests/test_scoring_input_integrity.py tests/test_enrich.py tests/test_rule_filter.py tests/test_vector_search.py tests/test_ai_score.py -q`

**Exit Criteria:** Fixtures reproduce every validated failure without modifying production behavior, and baseline failure output is recorded.

### Task 2: Make enrichment completeness and fallback scoring truthful

**Purpose:** Prevent partial or failed extraction from erasing mandatory facts or permanently excluding eligible jobs.

**Task Function:** Backend contract and scoring-path implementation.

**Template Profile:** `unresolved`; resolve through Planning Dispatch before activation.

**Specification Coverage:** Partial enrichment loss, fallback dead-end, and mandatory omission state integrity.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:** `src/fitcv/enrich.py` (`merge_scraped_and_enriched`, `_enrich_result_to_row`, `_build_enrichment_fallback_row`), `src/fitcv/ai_score.py` (`build_ranking_job_input`, `build_ranking_request`, `run_ai_scoring`), `tests/test_enrich.py`, `tests/test_ai_score.py`, `tests/test_scoring_input_integrity.py`.

**Dependencies:** Task 1.

**Authority:**
- Preauthorized local actions: edit the named enrichment/scoring symbols and focused tests.
- Stop for: inventing mandatory facts from raw text without source-span evidence or changing provider routing.

**Steps:**
1. Add per-mandatory-channel extraction state and preserve source spans/checksum metadata for extracted clauses.
2. Make `mandatory_core_complete` depend on the actual model-visible contract, not only on a nonblank semantic row.
3. Add `needs_enrichment` as a disposition/failure code and make extraction fallback retryable.
4. Implement degraded scoring using raw description plus known structured facts and explicit unknown markers, or route the job to the retry lane before final ranking.
5. Keep budget overflow separate from provider failure and incompatibility while preserving `score_status` as `unscored`.

**Verification:** `python -m pytest tests/test_enrich.py tests/test_ai_score.py tests/test_scoring_input_integrity.py -q`, plus direct boundary tests asserting no provider call occurs when mandatory facts cannot fit and no invalid score is emitted.

**Exit Criteria:** Partial enrichment cannot claim complete mandatory coverage; fallback jobs are retryable or transparently degraded; score states remain distinct.

### Task 3: Honor configured eligibility semantics

**Purpose:** Stop missing metadata and unselected title preferences from rejecting jobs before retrieval.

**Task Function:** Rule-filter behavior correction.

**Template Profile:** `unresolved`; resolve through Planning Dispatch before activation.

**Specification Coverage:** Title filter selection and contract-type unknown semantics.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:** `src/fitcv/rule_filter.py` (`apply_rule_filters`, `check_contract_type`, new `classify_contract_type`), `src/fitcv_cp/settings_schema.py`, `tests/test_rule_filter.py`, `tests/test_fitcv_cp/test_settings_schema.py`.

**Dependencies:** Task 1.

**Authority:**
- Preauthorized local actions: edit rule-filter logic and add focused unit/contract tests.
- Stop for: weakening explicit user exclusions or changing unrelated fit-factor policies.

**Steps:**
1. Route title inclusion/exclusion results through `selected_filter_codes`.
2. Retain `check_contract_type() -> bool` for compatibility and add `classify_contract_type() -> match|mismatch|unknown`; use the classifier in `apply_rule_filters` so absent/unrecognized contract type is `unknown` when an allow-list is configured, while known disallowed values still reject.
3. Persist a diagnostic state distinguishing `unknown`, `match`, and `mismatch`, and add settings-schema coverage for the explicit missing-metadata policy.

**Verification:** `python -m pytest tests/test_rule_filter.py tests/test_fitcv_cp/test_settings_schema.py -q`

**Exit Criteria:** Unselected title filters mark but pass; selected title filters reject; missing contract type survives; known mismatches still reject.

### Task 4: Make retrieval recovery competitive and neutral to unknowns

**Purpose:** Ensure missing embeddings and incomplete metadata do not remove relevant jobs before scoring.

**Task Function:** Retrieval and ranking-channel implementation.

**Template Profile:** `unresolved`; resolve through Planning Dispatch before activation.

**Specification Coverage:** Vector fallback capacity, lexical missingness bias, and hybrid neutral rescue.

**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:** `src/fitcv/vector_search.py` (`_vector_search_result`, `_hybrid_search_result`), `src/fitcv/ranking.py` (`_preference_dimension_score`, `_preference_dimension_score_with_neighbors`), `tests/test_vector_search.py`, `tests/test_ranking.py`.

**Dependencies:** Tasks 1 and 3.

**Authority:**
- Preauthorized local actions: edit retrieval/ranking-channel logic and add deterministic recall fixtures.
- Stop for: changing default retrieval cutoffs or introducing a new embedding provider.

**Steps:**
1. Build vector and lexical candidate unions before applying the production cutoff, preserving existing hybrid fusion where applicable.
2. Add recovery metadata: embedding state, vector rank, lexical rank, fusion rank, and admission reason.
3. Represent missing preference dimensions as `unknown` and contribute exactly `0.5` for each unknown dimension, preserving configured weights and the existing weighted-sum formula; add exact expected-score tests and a policy/version field for this behavior.
4. Require positive evidence state for hybrid rescue; project preference match details into lexical rows. Neutral/unknown title data must not qualify as affirmative rescue.

**Verification:** `python -m pytest tests/test_vector_search.py tests/test_ranking.py -q`, including a fixture proving a high-relevance missing-embedding job is considered when vector capacity is full.

**Exit Criteria:** Recovery candidates compete before cutoff; unknown data is not scored as mismatch; neutral title data cannot trigger affirmative rescue.

### Task 5: Preserve typed mandatory facts and strongest evidence in scoring

**Purpose:** Maximize model-visible information under the existing request budget.

**Task Function:** Scorer contract, evidence selection, and budget implementation.

**Template Profile:** `unresolved`; resolve through Planning Dispatch before activation.

**Specification Coverage:** Typed language facts, evidence cap, budget overflow, and skip-before-evidence ordering.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`.

**Files And Symbols:** `src/fitcv/enrich.py` (`_canonical_language_requirements`), `src/fitcv/ai_score.py` (`build_ranking_job_input`, `build_ranking_request`, `build_ranking_input_diagnostics`), `src/fitcv/evidence.py` (`select_ranking_evidence`), `src/fitcv/pipeline_stage_runner.py` (`execute_ranking_stage`), `src/fitcv/agentic_cv_analysis.py`, `tests/test_evidence.py`, `tests/test_ai_score.py`, `tests/test_agentic_cv_analysis.py`.

**Dependencies:** Tasks 1 and 2.

**Authority:**
- Preauthorized local actions: edit scorer/evidence/analysis symbols and add model-request visibility tests.
- Stop for: increasing the 12,000-character limit or changing holistic baseline weights without labeled evaluation approval.

**Steps:**
1. Preserve language records as typed objects with requirement IDs, level, requirement type, extraction state, and evidence.
2. Replace fixed evidence count with a token-aware packer prioritizing mandatory coverage, attribution, and project diversity.
3. Record selected, rendered, and model-visible evidence IDs, covered requirement IDs, and verified supporters omitted by budgeting.
4. Before irreversible skip, run a deterministic mandatory-coverage check over the full projected evidence pool. If mandatory coverage is verified or scoring uncertainty is high, route to reconsideration/re-score or `review_required`; never silently change the fit label.
5. Route irreducible mandatory overflow to `budget_exceeded` with `retry_eligible=true` or manual-review eligibility rather than permanent unscored.

**Verification:** `python -m pytest tests/test_evidence.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py -q`, and assert every model-visible evidence ID belongs to the selected pool.

**Exit Criteria:** Required language facts remain typed; evidence is selected by coverage and budget; skip and budget failures cannot hide a recoverable relevant job.

### Task 6: Reconcile admission, persistence, and export diagnostics

**Purpose:** Make every pre-scoring and scoring disposition traceable and consistent across execution paths.

**Task Function:** Cross-stage manifest and projection integration.

**Template Profile:** `unresolved`; resolve through Planning Dispatch before activation.

**Specification Coverage:** Cutoff observability, failure-state integrity, model-visible evidence visibility, and mandatory-fact diagnostics.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:** `src/fitcv/pipeline.py`, `src/fitcv/pipeline_stage_runner.py`, `src/fitcv/pipeline_stage_artifacts.py`, `src/fitcv/pipeline_store.py`, `src/fitcv_cp/sqlite_store.py` (`persist_pipeline_snapshot` and its read projection), `tests/test_pipeline.py`, `tests/test_pipeline_stage_resume_parity.py`, `tests/test_pipeline_checkpoint_contract.py`, `tests/test_fitcv_cp/test_sqlite_store.py`.

**Dependencies:** Tasks 2–5.

**Authority:**
- Preauthorized local actions: edit shared admission/projection owners and add persistence/export reconciliation tests.
- Stop for: schema migration or deletion of persisted fields without a rollback-compatible migration design.

**Steps:**
1. Make the shared admission manifest authoritative for inline and resumed shortlist execution.
2. Use mutually exclusive disposition outcomes: `filtered`, `not_retrieved`, `retrieved_below_cutoff`, `ai_not_selected`, `score_failed`, `budget_exceeded`, `needs_enrichment`, `valid_below_final_cutoff`, and `ranked`; preserve `score_status` separately as `valid`, `unscored`, or `invalid`.
3. In `persist_pipeline_snapshot()` add additive snapshot fields (or a versioned embedded evidence object if the existing schema requires it) for `failure_code`, `retry_eligible`, mandatory completeness, selected evidence IDs, and model-visible evidence IDs, and update the corresponding read projection.
4. Add a redacted mandatory-fact/provenance projection to diagnostics and exports.
5. Ensure ranking artifacts do not label invalid/unscored rows as `scored_not_ranked`.

**Verification:** `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py tests/test_fitcv_cp/test_sqlite_store.py -q`

**Exit Criteria:** Production and resumed paths agree on terminal disposition; diagnostics explain every eligible job; exports account for mandatory facts and model-visible evidence.

### Task 7: Run cross-stage backend verification and matching evaluation

**Purpose:** Prove recall and evidence preservation without silently changing the existing ranking policy.

**Task Function:** Integration verification and calibration readiness.

**Template Profile:** `unresolved`; resolve through Planning Dispatch before activation.

**Specification Coverage:** End-to-end integrity, preserved defaults, and validated-finding acceptance.

**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`.

**Files And Symbols:** all Task 2–6 owners and tests; repository-configured profile/job fixtures used by pipeline integration tests.

**Dependencies:** Tasks 2–6.

**Authority:**
- Preauthorized local actions: run declared tests, direct boundary checks, and same-corpus evaluation commands.
- Stop for: provider/authentication failures, destructive data changes, or unexplained score-policy/default changes.

**Steps:**
1. Run focused tests from Tasks 2–6.
2. Run `python -m pytest -q`.
3. Execute a representative pipeline run and verify the ledger, stage artifacts, log console, and exports agree on each terminal disposition.
4. On the pinned `data/fitcv-p0-corpus/p0c/requirement_support_benchmark.json` corpus at the revision recorded by `config/acceptance_state.yaml` (`evaluation_freeze_commit: 5cfd25ff31b3b620dbfda5f25e54a0718cb1cb50`), run the four documented arms and preserve the pre-change report as `.tmp/fitcv-matching-accuracy-baseline.json`:
   - `uv run python scripts/benchmark_requirement_support.py --fixture data/fitcv-p0-corpus/p0c/requirement_support_benchmark.json --arm lexical-baseline --runs 50 --warmups 5 --output .tmp/lexical-baseline.json`
   - `uv run python scripts/benchmark_requirement_support.py --fixture data/fitcv-p0-corpus/p0c/requirement_support_benchmark.json --arm lexical-ablation --runs 50 --warmups 5 --output .tmp/lexical-ablation.json`
   - `uv run python scripts/benchmark_requirement_support.py --fixture data/fitcv-p0-corpus/p0c/requirement_support_benchmark.json --arm lexical-requirement-aware --runs 50 --warmups 5 --output .tmp/lexical-requirement-aware.json`
   - `uv run python scripts/benchmark_requirement_support.py --fixture data/fitcv-p0-corpus/p0c/requirement_support_benchmark.json --arm current-hash --runs 50 --warmups 5 --output .tmp/current-hash.json`
   - `uv run python scripts/compare_requirement_support.py --inputs .tmp/lexical-baseline.json,.tmp/lexical-ablation.json,.tmp/lexical-requirement-aware.json,.tmp/current-hash.json --output .tmp/fitcv-matching-accuracy-report.json`
   Require selected requirement/evidence-pair recall and mandatory-fact visibility to be no lower than the baseline, with no increase in false-negative cases and no unexplained ordering reversals.
5. Keep `vector_search_top_n`, `ai_score_top_n`, `final_top_n`, the 12,000-character request limit, and `holistic_ai_only` unchanged unless a separate calibration decision is approved.

**Completed verification evidence:**

- Provider-backed run `cc509b7f-e4b7-40a6-8a65-11ca29711148` processed all `280` jobs: enrichment `280/280`, screening `264` passed and `16` seniority rejects, shortlist `50`, ranking `15` final-ranked with `32` budget-limited, CV analysis completed, and CV generation completed with `4` review-required items.
- The persisted export reported `status: succeeded`, `280` rows, `18` valid objective compatibility scores, `32` explicit `budget_exceeded` failures, and `230` legacy ambiguous labels in the pre-fix artifact. The latter is the confirmed defect addressed by `_normalize_results_export_row`; the artifact is not rewritten retroactively.
- The run’s `awaiting_continue` / `awaiting_review` lifecycle is expected because four CV outputs require operator review; pipeline compute completed and is not a hang.
- TDD regression proof covers both intentional early-stage unscored rows and preservation of explicit `budget_exceeded` failures. The focused export tests pass, and `tests/test_fitcv_cp/test_app.py` passes `544` tests.
- Review-fix regression proof covers the production worker export boundary plus `parser_status`, `reranker_parser_status`, `score_reasoning`, and `reranker_score_reasoning` legacy failure contracts; the affected ranking-contract, worker, and app suites pass `664` tests.
- Final review identified and the follow-up patch fixed the composition case where app projection re-normalized worker output and invented `score_unavailable`; `normalize_score_state_for_export` is now idempotent for stage-only rows, proven by a two-pass regression.
- Repository-wide `uv run pytest -q` was attempted and produced `3597 passed, 10 skipped, 34 failed`. The failures are outside this patch: local credential-store/page tests require the optional `local` extra (`keyring`, absent in the environment), and inverse-optimization tests require the optional `inverse-optimization` extra (`cvxpy`, absent in the environment). No optional dependency was installed without authorization.
- The repository's CI `Full Suite` completed successfully for commit `2b9fe6ea55baecb6af7742fe076f8df713b7cf35`; this supplies the declared full-suite proof despite the local environment lacking the optional extras.

**Verification:** Direct backend boundary tests, failure-path tests, persisted-state assertions, full automated suite, same-corpus evaluation report, and the committed `config/acceptance_state.yaml` thresholds (`support_recall_threshold: 1.0`, `minimum_oracle_coverage: 1.0`, `maximum_pair_false_positives: 0`).

**Exit Criteria:** All cross-stage invariants pass; no unknown or infrastructure failure is represented as incompatibility; export normalization does not fabricate failure codes for unscored stage dispositions; evaluation evidence is sufficient for any future ranking-weight decision.

## Verification

Final verification must prove:

- Every normalized job has exactly one terminal outcome.
- Unknown metadata never creates a confirmed mismatch without explicit policy.
- Every verified mandatory fact is model-visible or has an omission and unresolved-coverage reason.
- Every model-visible evidence ID belongs to the selected evidence pool.
- Provider, enrichment, and budget failures remain distinct from compatibility scores.
- Inline, resumed, shared-stage, control-plane, and export records reconcile.

## Completion Criteria

- Tasks 1–7 contain fresh evidence and the ledger is updated to `completed` after verification. Task 7’s provider-backed run, export-normalization regression evidence, and the successful CI `Full Suite` are complete; the local optional-extra gap is recorded as an environment limitation rather than a plan blocker.
- Focused tests pass. The full suite has been attempted; unrelated missing-optional-extra failures are recorded rather than patched opportunistically.
- Same-corpus evaluation shows improved or preserved recall and mandatory-fact visibility without unexplained false-positive growth.
- Holistic ranking weights and default cutoffs remain unchanged without a separate approved calibration decision.
- Final branch disposition remains outside this plan and requires explicit authorization through the branch-finishing workflow.
