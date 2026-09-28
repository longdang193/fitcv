---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-fact-grain-benchmark-green-baseline
targets:
  - src/fitcv/evidence.py
  - scripts/benchmark_ranking.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - tests/test_evidence.py
  - tests/test_ranking_evaluation.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_p0_public_corpus.py
  - data/fitcv-p0-corpus/p0a/admission_report.json
  - data/fitcv-p0-corpus/p0a/ranking_source_backed.json
  - data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl
  - data/fitcv-p0-corpus/p0b/candidate_evidence_projection.jsonl
  - data/fitcv-p0-corpus/p0b/projection_manifest.json
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence.jsonl
  - data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_manifest.json
  - data/fitcv-p0-corpus/p0c/requirement_support_benchmark.json
  - data/fitcv-p0-corpus/README.md
  - .gitattributes
  - .github/workflows/repo-hooks.yml
  - docs/superpowers/plans/2026-09-28-fitcv-fact-grain-benchmark-green-baseline-plan.md
---

# FitCV Fact-Granularity and Benchmark Green Baseline

## Review Basis

Verdict is materially correct. Source checkout was clean on `main` at
`7a516a3fb77101b5ed9f7212a529133eb8592a51` before this plan was created. The
plan file is the intentional current untracked artifact and must be carried
into the execution worktree before implementation begins.

Source confirms:

- `src/fitcv/evidence.py:_assess_requirement_support` scans whole evidence-item text.
- `scripts/benchmark_ranking.py:_split_metric_rows` receives ranked IDs for split shortlist metrics.
- `data/fitcv-p0-corpus/p0a/ranking_source_backed.json` has 50 DE and 50 EN rows, all relevant.
- Corpus files are `i/lf w/crlf`; `.gitattributes` has no corpus EOL rule.
- `admission_report.json` records a ranking hash different from current published bytes.

This plan supersedes remaining implementation scope in the older 2026-09-27
recovery/simplification plans. It does not rewrite those historical records.

## Goal

Finish fact-granularity and benchmark correctness, then establish one green,
exact-SHA, Windows/Linux-reproducible baseline.

P0-A multilingual promotion and P0-B production-recall promotion remain
deferred until independently reviewed discriminative coverage exists.

## Non-Goals

- No new embedding provider, encoder, reranker, graph, agent, ANN index, or dependency.
- No production retrieval-default change or recovery flag.
- No fabricated or runtime-derived relevance labels.
- No P0-A promotion from current all-positive fixture.
- No P0-B promotion from current reviewed sample.
- No Git history rewrite, P1 compiler, uncertainty workflow, or UX work.

## Execution Approach

- Mode: inline sequential; one controller owns ordered edits and final verification.
- Executor: `codex` in a clean isolated worktree.
- Commit policy: no implementation commit during task execution. After final local verification, authorized Git disposition creates the reviewed commit; CI then runs on that exact commit before plan completion. Without commit authorization, local proof may be recorded but exact-SHA CI acceptance remains open.
- Shared-write control: runtime, benchmarks, fixtures, manifests, workflow, and docs are serialized by task order.
- Required skills: `skill-using-git-worktrees`, `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`.
- Source and tests override historical plan prose.
- Task profiles resolved from `agents/*.toml`: `normal` for sequential implementation and verification tasks.

## Acceptance Contract

- Focused tests and `python -m pytest -q` pass on final reviewed SHA.
- Corpus-integrity tests pass on Windows and Linux.
- Published manifest hashes equal final `read_bytes()` hashes.
- `git ls-files --eol data/fitcv-p0-corpus` reports LF index and working-tree bytes.
- Retrieval and ranking metrics use separate ID sets.
- Same-statement qualifier, negation, months, comparator, and German-alias tests pass.
- Non-timing benchmark fields are deterministic across repeated runs.
- `ranking_promotion` remains `blocked_all_positive_corpus`.
- `support_promotion` remains `blocked_reviewed_coverage`.
- Exact SHA, CI run ID, hashes, and status are recorded before this plan becomes `completed`.

## Task 0: Freeze Baseline and Admission Boundaries

**Purpose:** Bind execution to current state and block accidental promotion claims.

**Task Function:** Baseline admission and contract freeze.

**Template Profile:** `normal`.

**Specification Coverage:** Exact base, clean worktree, fixture limits, promotion deferrals.

**Required Skills:** `skill-using-git-worktrees`, `skill-code-standards`.

**Files And Symbols:** Current Git state; `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`; `data/fitcv-p0-corpus/p0b/reviewed_requirement_evidence_manifest.json`; this plan.

**Dependencies:** None.

**Authority:** Create isolated worktree and record baseline facts. Stop on dirty-worktree access, unexpected SHA, missing fixtures, or label fabrication.

**Steps:**

1. Create worktree from `7a516a3fb77101b5ed9f7212a529133eb8592a51`.
2. Copy this plan into the execution worktree before implementation and record its path as the coordination source.
3. Resolve pending task profiles from `agents/*.toml` before activation.
4. Record status, SHA, EOL state, and current manifest hashes.
5. Confirm P0-A is 50 DE/50 EN and all-positive.
6. Confirm P0-B is benchmark-only with coverage block.

**Verification:** Baseline record contains exact SHA, fixture counts, and promotion blocks.

**Exit Criteria:** Execution starts from declared SHA without touching private work.

## Task 1: Add Statement-Grain Requirement Support

**Purpose:** Prevent qualifiers transferring between unrelated statements in one evidence item.

**Task Function:** Backend contract correction and regression proof.

**Template Profile:** `normal`.

**Specification Coverage:** Fact granularity, identity, same-evidence support, contradiction safety, legacy compatibility.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`.

**Files And Symbols:** `src/fitcv/evidence.py:_normalise_experience_entry`; `src/fitcv/evidence.py:_normalise_project_entry`; `src/fitcv/evidence.py:_assess_requirement_support`; `src/fitcv/evidence.py:_annotate_requirement_support`; `tests/test_evidence.py`.

**Dependencies:** Task 0.

**Authority:** Change derived assessment fields and tests only. Preserve stable evidence IDs, provenance, persisted profile schema, budgets, and cross-evidence behavior.

**Steps:**

1. Add derived internal `support_fragments`.
2. Derive one fragment per structured bullet with bullet-local text and skills. Derive highlight and tech-stack fragments with parent project skills as inherited skill metadata; qualifiers remain local to each fragment.
3. Preserve explicit projected fragments. Use one compatibility fragment from full item text only when no structured statement fields exist; structured V1 bullets are not legacy flat evidence.
4. Assess canonical skill and every qualifier against one fragment.
5. Set `qualified_support` only when one fragment satisfies all qualifiers.
6. Never combine facts across fragments or evidence items.
7. Apply contradiction within each fragment only. A supported fragment may qualify an item even when another fragment has a contradictory fact; record fragment-level assessments without transferring facts between fragments.

**Verification:** Test mixed Python/SQL, same-statement success, split-fragment failure, explicit contradiction, duplicate requirements, stable IDs, and legacy flat evidence.

**Exit Criteria:** `5 years production Python; SQL classroom exercises` cannot support `3 years production SQL`; `5 years production SQL` can.

## Task 2: Normalize Qualifier Semantics

**Purpose:** Make requirement and evidence parsing symmetric and fail closed.

**Task Function:** Deterministic parser and backend boundary verification.

**Template Profile:** `normal`.

**Specification Coverage:** Months, inequalities, negation, German aliases, unresolved qualifier state.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`, `skill-code-standards`.

**Files And Symbols:** `src/fitcv/evidence.py:_parse_duration_qualifier`; `_parse_requirement_qualifiers`; `_duration_satisfies`; `_is_negated_term`; `tests/test_evidence.py`.

**Dependencies:** Task 1.

**Authority:** Extend deterministic parsing only. No LLM, external language service, or dependency.

**Steps:**

1. Normalize duration as comparator plus months.
2. Parse years, fractional years, months, `less than`, `under`, `more than`, `at least`, `minimum`, and `+`.
3. Compare both requirement and evidence duration intervals, not only numeric points. For example, evidence `< 4 years` cannot satisfy requirement `> 3 years`; evidence `> 4 years` can; evidence `>= 3 years` cannot satisfy `> 3 years`.
4. Detect duration negation.
5. Map `Produktionsumgebung`/`Produktion` to `production`, `Echtzeit` to `real_time`, and exact `Unternehmensumfeld` to `enterprise`.
6. Preserve `unverified` for recognized but unresolved qualifiers.

**Verification:** Test all verdict-table cases: `3 years`, `more than 3 years`, `less than 3 years`, `18 months`, negated duration, German production alias, classroom-versus-production, compound context, and unknown qualifier.

**Exit Criteria:** Unsupported or contradictory facts never become positive qualified support.

## Task 3: Separate Retrieval and Ranking Metrics

**Purpose:** Make each benchmark metric use its owning pipeline stage.

**Task Function:** Benchmark contract correction.

**Template Profile:** `normal`.

**Specification Coverage:** Retrieval/ranking separation, precision/recall denominators, deterministic schema.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-code-standards`.

**Files And Symbols:** `scripts/benchmark_ranking.py:_split_metric_rows`; `scripts/benchmark_ranking.py:_run_once`; `scripts/benchmark_ranking.py:main`; `tests/test_ranking_evaluation.py`.

**Dependencies:** Task 0.

**Authority:** Change benchmark output and tests only. Do not change production retrieval or ranking.

**Steps:**

1. Pass `retrieved_ids` into `_split_metric_rows`.
2. Compute retrieval metrics from retrieved IDs and ranking metrics from ranked output after `ranking_top_n`.
3. Emit `retrieval.recall_at_n`, `retrieval.precision_at_n`, `ranking.recall_at_n`, `ranking.precision_at_n`, and `ranking.ndcg_at_n`.
4. Define recall as relevant returned divided by relevant eligible; precision as relevant returned divided by returned.
5. Bump benchmark schema version.
6. Add mixed-relevance regression data where retrieval returns more rows than ranking.

**Verification:** Independent expected values prove retrieval and ranking recall differ; repeated runs match on all non-timing fields.

**Exit Criteria:** No retrieval metric reuses ranked IDs.

## Task 4: Make P0-B Arms Truthful

**Purpose:** Align arm names with effective behavior.

**Task Function:** Benchmark configuration correction.

**Template Profile:** `normal`.

**Specification Coverage:** Production policy, lexical comparison, full-pool diagnostic, report compatibility.

**Required Skills:** `skill-performance-optimization`, `skill-test-driven-development`, `skill-code-standards`.

**Files And Symbols:** `scripts/benchmark_requirement_support.py:_runtime_config`; `scripts/compare_requirement_support.py:run_inputs`; `tests/test_benchmark_requirement_support.py`; `tests/test_compare_requirement_support.py`.

**Dependencies:** Tasks 1–2.

**Authority:** Rename benchmark arms and comparison output only. Do not change production defaults or add recovery behavior.

**Steps:**

1. Define `production`, `lexical_only`, and `full_pool_diagnostic`.
2. Make `production` load canonical policy unchanged.
3. Make `lexical_only` disable semantic alignment.
4. Make `full_pool_diagnostic` change only channel-pool bound.
5. Accept `current` and `full-pool` as legacy input aliases where needed; emit canonical names.
6. Preserve `promotion_status: blocked_reviewed_coverage`.

**Verification:** Tests prove effective config and reject mismatched fixture, budget, or schema comparisons.

**Exit Criteria:** Reports cannot call lexical behavior unchanged production.

## Task 5: Normalize Corpus Bytes and Hashes

**Purpose:** Make public artifacts reproducible across checkout platforms.

**Task Function:** Corpus integrity repair and metadata regeneration.

**Template Profile:** `normal`.

**Specification Coverage:** LF policy, final-byte hashing, admission/publication separation, manifest consistency.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`.

**Files And Symbols:** `.gitattributes`; `data/fitcv-p0-corpus/p0a/admission_report.json`; `data/fitcv-p0-corpus/p0a/ranking_source_backed.json`; `data/fitcv-p0-corpus/p0a/raw_postings_de_en.jsonl`; `data/fitcv-p0-corpus/p0b/*.jsonl`; `data/fitcv-p0-corpus/p0b/*_manifest.json`; `tests/test_p0_public_corpus.py`.

**Dependencies:** Task 0.

**Authority:** Normalize approved public bytes and metadata only. Preserve content, labels, privacy boundary, and provenance meaning. No history rewrite.

**Steps:**

1. Add `data/fitcv-p0-corpus/** text eol=lf` to `.gitattributes`.
2. Renormalize tracked corpus files.
3. Recompute publication hashes from final bytes after all transformations.
4. Keep admission-input hashes distinct from publication hashes.
5. Update ranking publication hash from final committed bytes.
6. Add tests rejecting CRLF and checking every manifest hash against `Path.read_bytes()`.
7. Do not add a corpus generator; current tree has no canonical generator.

**Verification:** `git ls-files --eol data/fitcv-p0-corpus` reports `i/lf w/lf`; `tests/test_p0_public_corpus.py` passes.

**Exit Criteria:** No line-ending or stale-publication-hash failure remains.

## Task 6: Add Cross-Platform Integrity Gate

**Purpose:** Prove corpus policy from fresh Windows and Linux checkouts.

**Task Function:** CI verification.

**Template Profile:** `normal`.

**Specification Coverage:** Cross-platform artifact integrity.

**Required Skills:** `skill-verification-before-completion`, `skill-code-standards`.

**Files And Symbols:** `.github/workflows/repo-hooks.yml`; `tests/test_p0_public_corpus.py`.

**Dependencies:** Task 5.

**Authority:** Add read-only integrity job. Do not alter unrelated CI jobs.

**Steps:**

1. Add `corpus-integrity` matrix for `windows-latest` and `ubuntu-latest`.
2. Checkout and install dependencies required by corpus tests.
3. Run `python -m pytest -q tests/test_p0_public_corpus.py`.
4. Fail unless published files report LF working-tree bytes.
5. Leave Full Suite on Windows.

**Verification:** Both matrix legs pass on exact reviewed SHA.

**Exit Criteria:** CI proves platform-independent bytes and hashes.

## Task 7: Final Verification and Acceptance Reconciliation

**Purpose:** Establish one green reproducible baseline.

**Task Function:** Final backend, benchmark, corpus, and CI verification.

**Template Profile:** `normal`.

**Specification Coverage:** Focused proof, Full Suite, deterministic benchmarks, promotion status, exact-SHA record.

**Required Skills:** `skill-backend-verification`, `skill-performance-optimization`, `skill-verification-before-completion`.

**Files And Symbols:** All changed paths; ignored `tmp/p0/` outputs; final CI metadata.

**Dependencies:** Tasks 1–6.

**Authority:** Run declared checks and write ignored benchmark outputs. Stop on failed tests, changed production defaults, stale hashes, EOL drift, or unreviewed labels.

**Steps:**

1. Run focused tests and `python -m pytest -q`.
2. Run corrected ranking benchmark against admitted source-backed fixture.
3. Run `production`, `lexical_only`, and `full_pool_diagnostic` support benchmarks and comparison.
4. Repeat benchmark runs; compare non-timing fields.
5. Run `git diff --check` and declared-path review.
6. Record final SHA, CI run ID, hashes, schema version, and promotion blocks.
7. Keep plan `proposed` until fresh verification returns `verified`.

**Verification Commands:**

```powershell
python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_p0_public_corpus.py
python -m pytest -q
python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --output tmp/p0/ranking.json
python scripts/benchmark_requirement_support.py --arm production --output tmp/p0/support-production.json
python scripts/benchmark_requirement_support.py --arm lexical_only --output tmp/p0/support-lexical.json
python scripts/benchmark_requirement_support.py --arm full_pool_diagnostic --output tmp/p0/support-full-pool.json
python scripts/compare_requirement_support.py --inputs tmp/p0/support-production.json,tmp/p0/support-lexical.json,tmp/p0/support-full-pool.json --output tmp/p0/support-comparison.json
git diff --check
git ls-files --eol data/fitcv-p0-corpus
```

**Exit Criteria:** Focused tests, Full Suite, local integrity checks, cross-platform CI, deterministic benchmarks, and exact-SHA acceptance record pass. P0-A/P0-B promotion remains blocked for stated coverage reasons.

## Execution Record — 2026-09-28

- Baseline worktree: `7a516a3fb77101b5ed9f7212a529133eb8592a51`.
- Implementation commit: `27d03903cb81fa8b0f69199190db65e305e1e8fb` (`fix: close fact-grain benchmark correctness gaps`).
- Focused verification: `119 passed`.
- Full verification: `2832 passed, 6 skipped, 52 warnings`.
- Corpus integrity: all tracked `data/fitcv-p0-corpus` files report `i/lf w/lf`; manifest hashes match final `read_bytes()` values.
- Ranking benchmark schema: `ranking_benchmark_v3`; retrieval and ranking metrics use separate ID sets.
- Support benchmark arms: `production`, `lexical_only`, `full_pool_diagnostic`; repeated non-timing fields match.
- Promotion status remains blocked: ranking fixture is all-positive; reviewed P0-B coverage remains insufficient.
- CI exact-SHA run: `36404840399` — all jobs passed: Focused Smoke Tests, Adapter Integrity, Full Suite, Architecture Docs, Public Corpus Integrity (Ubuntu), and Public Corpus Integrity (Windows).

## Rollback

No production-default or external-state migration occurs. If checks fail, do not
merge. Preserve failed benchmark and hash outputs. Existing lexical fallback
remains runtime rollback path.

## Completion Definition

Fresh verification proves same-statement qualifier binding, symmetric fail-closed
parsing, separate retrieval/ranking metrics, truthful benchmark arms, stable
Windows/Linux corpus bytes, and one green Full Suite SHA without implying P0-A or
P0-B promotion.
