---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: final-p0-integration-closeout
targets:
  - src/fitcv/evidence.py
  - scripts/benchmark_ranking.py
  - scripts/benchmark_requirement_support.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_ranking_evaluation.py
  - tests/test_benchmark_requirement_support.py
---

# Final P0 Integration Closeout

## Review Basis

The supplied verdict is materially correct. PR #65 established the portable
baseline, but four bounded correctness gaps remain:

1. `project_candidate_evidence()` does not emit proof-safe `support_fragments`,
   so `_support_fragments()` can fall back to retrieval metadata such as
   `scoring_context` during qualifier verification.
2. Requirement-support semantics changed without changing
   `REQUIREMENT_SUPPORT_POLICY_VERSION`; old v2 CV-analysis reuse records can
   remain eligible.
3. `scripts/benchmark_ranking.py:_run_once()` passes ranked IDs where
   `_split_metric_rows()` requires retrieval IDs, corrupting shortlist metrics.
4. `scripts/benchmark_requirement_support.py:run_benchmark()` maps the
   `full-pool` diagnostic to a hardcoded pool size of 12 instead of the full
   canonical scenario pool.

Existing untracked plan
`docs/superpowers/plans/2026-09-28-fitcv-fact-grain-benchmark-green-baseline-plan.md`
is unrelated user work and must remain untouched.

## Goal

Close the four integration gaps with the smallest production-path change,
prove one green reproducible baseline, and keep P0-A quality promotion and
P0-B production-recall promotion deferred.

## Implementation Outcomes

### Proof-safe canonical evidence

Canonical projected evidence contains source-only `support_fragments` with
deterministic statement boundaries and conservative skill attribution.
`scoring_context` remains available for retrieval but cannot prove qualifiers.
Ambiguous statement-to-skill mapping remains `unverified` rather than guessing.

### Correct reuse and benchmark contracts

The support-policy version becomes `requirement-support-v3`, rejecting v2
contract fingerprints while preserving unrelated cache reuse. Ranking split
metrics use actual retrieval IDs. Full-pool diagnostics inspect every canonical
evidence item in each scenario without changing production scoring, final
`evidence_top_k`, or requirement logic.

### Reproducible acceptance evidence

Focused regressions, full test suite, benchmark checks, deterministic
non-timing comparisons, and `git diff --check` pass on one reviewed SHA.
P0-A and P0-B promotion claims remain explicitly blocked by their existing
coverage limits.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-using-git-worktrees`, `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `managed worktree from origin/main`; preserve current checkout and its untracked plans
- Commit policy: `no commits during execution`
- Preauthorized local actions: inspect source/tests, edit listed files, run declared local tests and benchmarks, write ignored `tmp/p0/` outputs
- User-approval actions: commit, push, merge, publication, destructive cleanup, branch/worktree disposal
- Parallel ownership: `none`; all changes share evidence semantics and benchmark fixtures
- Sequential fallback: tasks execute in listed order

## Task Breakdown

### Task 0: Freeze baseline and workspace boundary

**Purpose:**
- Bind implementation to merged PR #65 at `95daf9968c71c7d1ab9f11ab99dd80d45465f30a`.
- Preserve unrelated untracked work.

**Task Function:** Baseline admission.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded sequential baseline work in existing repository modules.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller owns local state check.

**Specification Coverage:** Exact base, no unrelated file changes, no promotion claims.

**Required Skills:** `skill-code-standards`

**Files And Symbols:**
- Inspect: Git status, `origin/main`, existing untracked plan
- Verify: repository root and declared target paths

**Dependencies:** None.

**Authority:**
- Preauthorized local actions: read Git state and preserve existing files.
- Stop for: any required base change, unrelated modified file, or request to discard user work.

**Steps:**
- [ ] Confirm `origin/main` resolves to `95daf9968c71c7d1ab9f11ab99dd80d45465f30a` or record approved newer base.
- [ ] Confirm the local copies of `docs/superpowers/plans/2026-09-28-fitcv-fact-grain-benchmark-green-baseline-plan.md` and this closeout plan remain byte-preserved.
- [ ] Do not fast-forward or checkout `origin/main` in current workspace; that path is tracked at `origin/main` and collides with the local untracked copy.
- [ ] Create a managed worktree from `origin/main` and perform all source/test edits there.
- [ ] Confirm the managed worktree is clean before implementation edits.

**Verification:**
- [ ] `git status --short --branch` in current workspace and managed worktree
- Expected: current workspace preserves both local plan files; managed worktree starts clean at the approved base.

**Exit Criteria:** Baseline and preserved user work are recorded.

### Task 1: Make canonical projection proof-safe

**Purpose:**
- Prevent retrieval metadata from satisfying requirement qualifiers.

**Task Function:** Canonical evidence projection correction.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded parser/projection change in one existing module.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused regression tests in owning module.

**Specification Coverage:** Source facts prove claims; retrieval metadata only ranks evidence; ambiguous attribution fails closed.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:project_candidate_evidence`, `_evidence_text`, `_support_fragments`, `_assess_requirement_support`, existing statement/alias helpers
- Modify: `src/fitcv/evidence.py:project_candidate_evidence`, `_evidence_text` or `_support_fragments` fallback, and the smallest existing helper seam needed for deterministic fragments
- Verify: `tests/test_evidence.py`

**Dependencies:** Task 0.

**Authority:**
- Preauthorized local actions: edit only evidence projection/support logic and its focused tests; preserve `scoring_context` for retrieval.
- Stop for: schema changes outside projected evidence, new dependency, LLM/graph solution, or production retrieval-default change.

**Steps:**
- [ ] Emit `support_fragments` from each canonical nested evidence item using source text and deterministic statement splitting.
- [ ] Attribute skills only when explicit skill names or existing canonical aliases identify the statement; keep ambiguous fragments canonical-matchable but qualifier `unverified`.
- [ ] Ensure `_assess_requirement_support()` reads source fragments, never `scoring_context`, parent role, organization, location, domain, or responsibility metadata.
- [ ] Remove `scoring_context` from `_evidence_text()` qualifier fallback, or make `_support_fragments()` fallback use only source fields; retain `scoring_context` for retrieval.
- [ ] Add regression through `project_candidate_evidence()` and `_assess_requirement_support()`: parent role `Production Engineer`, source text `SQL classroom exercises`, linked skill `SQL`; production SQL must not qualify.
- [ ] Add ambiguous-attribution regression: canonical skill match may remain true, but `qualifier_status` is `unverified` and `qualified_support` is false.
- [ ] Keep existing positive duration/context/negation and canonical projection behavior green.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py`
- Expected: metadata-leakage regression fails before fix and passes after fix; existing evidence tests pass.

**Exit Criteria:** Canonical projection carries proof-safe fragments and no retrieval-only field can prove a qualifier.

### Task 2: Invalidate stale requirement-support reuse

**Purpose:**
- Prevent pre-PR #65 analyses from being reused under changed qualifier semantics.

**Task Function:** Contract fingerprint version correction.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: one constant and contract-fingerprint regression.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: fingerprint assertions are sufficient.

**Specification Coverage:** Semantic policy changes invalidate only affected CV-analysis reuse records.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:REQUIREMENT_SUPPORT_POLICY_VERSION`, `build_cv_analysis_contract_fingerprint`
- Modify: `src/fitcv/evidence.py:REQUIREMENT_SUPPORT_POLICY_VERSION`
- Verify: `tests/test_evidence.py` and existing CV-analysis reuse checks

**Dependencies:** Task 1 defines final support semantics.

**Authority:**
- Preauthorized local actions: bump v2 to v3 and add focused fingerprint assertions only.
- Stop for: broad cache invalidation, database migration, or changes to unrelated fingerprint fields.

**Steps:**
- [ ] Set `REQUIREMENT_SUPPORT_POLICY_VERSION` to `requirement-support-v3`.
- [ ] Add a regression constructing equivalent old v2 and current v3 contract fingerprints and assert they differ.
- [ ] Assert unrelated config changes retain existing selective-fingerprint behavior.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py`
- Expected: v2 reuse is rejected; fresh requirement coverage path is selected; unrelated cache behavior remains unchanged.

**Exit Criteria:** Old support-policy fingerprints cannot authorize reuse under v3.

### Task 3: Separate retrieval and ranking metric ID sets

**Purpose:**
- Restore truthful shortlist recall in split ranking metrics.

**Task Function:** Benchmark integration correction.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: one call-site correction with end-to-end regression.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: `_run_once` regression exercises actual integration.

**Specification Coverage:** Retrieval recall measures retrieved candidates; ranking recall measures ranked candidates.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `scripts/benchmark_ranking.py:_split_metric_rows`, `_run_once`
- Modify: `scripts/benchmark_ranking.py:_run_once`
- Verify: `tests/test_ranking_evaluation.py`

**Dependencies:** Task 0.

**Authority:**
- Preauthorized local actions: pass existing `retrieved_ids`; add one integration fixture/test; preserve metric definitions.
- Stop for: changing ranking algorithms, fixture labels, retrieval backends, or helper semantics.

**Steps:**
- [ ] Pass `retrieved_ids` into `_split_metric_rows()` at the current `_run_once()` call site.
- [ ] Add an end-to-end `_run_once()` test with 20 relevant eligible rows, 20 retrieved rows, and 5 ranked rows.
- [ ] Assert retrieval recall is `1.0` and ranking recall is `0.25` for the same split.

**Verification:**
- [ ] `python -m pytest -q tests/test_ranking_evaluation.py`
- Expected: retrieval and ranking metrics differ exactly as fixture construction requires.

**Exit Criteria:** Split shortlist metrics use retrieval IDs and ranking metrics use ranked IDs.

### Task 4: Derive true full-pool diagnostic ceiling

**Purpose:**
- Make `full-pool` a truthful diagnostic over all canonical scenario evidence.

**Task Function:** Benchmark diagnostic-bound correction.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded benchmark harness change with scenario-level regression.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: benchmark tests assert arm isolation and coverage.

**Specification Coverage:** Diagnostic changes only intermediate channel-pool cutoff; production scoring and final evidence budget remain unchanged.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py:run_benchmark`, `_run_benchmark_scenario`, canonical projected evidence construction
- Modify: `scripts/benchmark_requirement_support.py` effective diagnostic pool bound
- Verify: `tests/test_benchmark_requirement_support.py`

**Dependencies:** Task 0; use Task 1's canonical projection contract where the fixture exercises projected evidence.

**Authority:**
- Preauthorized local actions: derive per-scenario diagnostic pool size or bypass only intermediate truncation; add a 20-item scenario fixture.
- Stop for: changing production arm policy, final `evidence_top_k`, requirement assessment, or unrelated benchmark output schema.

**Steps:**
- [ ] Remove hardcoded `12` mapping for full-pool diagnostics.
- [ ] Derive the bound inside `_run_benchmark_scenario()` from that scenario's canonical projected evidence count; do not keep one scalar bound in `run_benchmark()` across scenarios.
- [ ] Add at least 20 canonical evidence items with qualifying support beyond position 12.
- [ ] Assert production can miss that support while `full_pool_diagnostic` sees it; assert diagnostic pool IDs equal canonical projected evidence IDs for every scenario, with no omitted IDs; assert final evidence budget and requirement logic remain unchanged.

**Verification:**
- [ ] `python -m pytest -q tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py`
- Expected: full-pool diagnostic reaches all canonical evidence; production remains bounded; arm comparison remains interpretable.

**Exit Criteria:** Full-pool diagnostic ceiling equals each scenario's true canonical pool, not a fixed constant.

### Task 5: Run final integration verification

**Purpose:**
- Establish one green, reproducible baseline without promoting deferred outcomes.

**Task Function:** Final acceptance reconciliation.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: fresh final verification after all edits.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller runs repository checks.

**Specification Coverage:** All four corrections, deterministic benchmark fields, full suite, and explicit deferrals.

**Required Skills:** `skill-verification-before-completion`, `skill-backend-verification`

**Files And Symbols:** All changed files; ignored `tmp/p0/` benchmark outputs.

**Dependencies:** Tasks 1–4.

**Authority:**
- Preauthorized local actions: run listed tests/benchmarks and inspect diffs/status.
- Stop for: failed required checks, changed production defaults, nondeterministic non-timing fields, stale fixture hashes, or unreviewed promotion claims.

**Steps:**
- [ ] Run focused regressions.
- [ ] Run the full suite.
- [ ] Run ranking and each support benchmark arm twice; compare outputs after removing every `timing_ms` object.
- [ ] Run `git diff --check` and inspect only declared changes plus the preserved untracked plan.
- [ ] Record final SHA, benchmark implementation ref, fixture hashes, and deferred promotion status for later execution/PR review.

**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_ranking_evaluation.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py`
- [ ] `python -m pytest -q`
- [ ] `python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --output tmp/p0/ranking.json`
- [ ] `python scripts/benchmark_ranking.py --fixture data/fitcv-p0-corpus/p0a/ranking_source_backed.json --output tmp/p0/ranking-run2.json`
- [ ] `python scripts/benchmark_requirement_support.py --arm current --output tmp/p0/support-production.json`
- [ ] `python scripts/benchmark_requirement_support.py --arm current --output tmp/p0/support-production-run2.json`
- [ ] `python scripts/benchmark_requirement_support.py --arm lexical-baseline --output tmp/p0/support-lexical.json`
- [ ] `python scripts/benchmark_requirement_support.py --arm lexical-baseline --output tmp/p0/support-lexical-run2.json`
- [ ] `python scripts/benchmark_requirement_support.py --arm full-pool --output tmp/p0/support-full-pool.json`
- [ ] `python scripts/benchmark_requirement_support.py --arm full-pool --output tmp/p0/support-full-pool-run2.json`
- [ ] `python scripts/compare_requirement_support.py --inputs tmp/p0/support-production.json,tmp/p0/support-lexical.json,tmp/p0/support-full-pool.json --output tmp/p0/support-comparison.json`
- [ ] `python -c "import json,sys; strip=lambda x: ({k:strip(v) for k,v in x.items() if k != 'timing_ms'} if isinstance(x,dict) else [strip(v) for v in x] if isinstance(x,list) else x); a=strip(json.load(open(sys.argv[1],encoding='utf-8'))); b=strip(json.load(open(sys.argv[2],encoding='utf-8'))); raise SystemExit(a != b)" tmp/p0/ranking.json tmp/p0/ranking-run2.json`
- [ ] `python -c "import json,sys; strip=lambda x: ({k:strip(v) for k,v in x.items() if k != 'timing_ms'} if isinstance(x,dict) else [strip(v) for v in x] if isinstance(x,list) else x); a=strip(json.load(open(sys.argv[1],encoding='utf-8'))); b=strip(json.load(open(sys.argv[2],encoding='utf-8'))); raise SystemExit(a != b)" tmp/p0/support-production.json tmp/p0/support-production-run2.json`
- [ ] `python -c "import json,sys; strip=lambda x: ({k:strip(v) for k,v in x.items() if k != 'timing_ms'} if isinstance(x,dict) else [strip(v) for v in x] if isinstance(x,list) else x); a=strip(json.load(open(sys.argv[1],encoding='utf-8'))); b=strip(json.load(open(sys.argv[2],encoding='utf-8'))); raise SystemExit(a != b)" tmp/p0/support-lexical.json tmp/p0/support-lexical-run2.json`
- [ ] `python -c "import json,sys; strip=lambda x: ({k:strip(v) for k,v in x.items() if k != 'timing_ms'} if isinstance(x,dict) else [strip(v) for v in x] if isinstance(x,list) else x); a=strip(json.load(open(sys.argv[1],encoding='utf-8'))); b=strip(json.load(open(sys.argv[2],encoding='utf-8'))); raise SystemExit(a != b)" tmp/p0/support-full-pool.json tmp/p0/support-full-pool-run2.json`
- [ ] `git diff --check`
- [ ] `git status --short --branch`
- Expected: all required tests pass; repeated non-timing benchmark fields match; P0-A remains `blocked_all_positive_corpus`; P0-B remains `blocked_reviewed_coverage`.

**Exit Criteria:** Fresh verification proves all four corrections on one SHA, with no deferred outcome promoted and no unrelated user work changed.

## Verification

Final artifact-level proof consists of the focused commands and full suite in
Task 5, plus repeated benchmark runs with timing fields excluded from equality
comparison. The final review must confirm `scoring_context` remains retrieval
input only, v2 fingerprints are rejected, retrieval/ranking ID sets are
separate, and full-pool diagnostics cover all canonical evidence.

## Rollback

No production default or persistent data migration changes. If any required
check fails, do not merge. Revert only the closeout patch; existing retrieval,
ranking, and lexical fallback behavior remain available. Preserve failed test
and benchmark outputs for diagnosis.

## Completion Criteria

The plan is ready for completion verification when:

1. canonical projection emits proof-safe fragments and qualifier verification
   cannot consume retrieval metadata;
2. `requirement-support-v3` rejects old v2 reuse fingerprints without broad
   cache invalidation;
3. `_run_once()` reports truthful retrieval and ranking split metrics;
4. `full_pool_diagnostic` reaches every canonical evidence item per scenario;
5. focused tests, full suite, benchmark repeatability, and diff checks pass;
6. P0-A and P0-B promotion remain deferred for their stated coverage limits;
7. no unrelated untracked plan or user change is modified.

The plan remains `proposed` until fresh execution evidence satisfies these
criteria and `skill-verification-before-completion` returns `verified`.
