---
layer: change
artifact_type: plan
status: active
contract_version: 1
template_id: implementation-plan
name: fitcv-p0-completion-simplification-cycle
targets:
  - src/fitcv/evidence.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/vector_search.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv/embeddings.py
  - src/fitcv/enrich.py
  - src/fitcv/prompts/templates/enrich_extraction_v1.md
  - scripts/benchmark_ranking.py
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_vector_search.py
  - tests/test_embeddings.py
  - tests/test_enrich.py
  - tests/test_ranking_evaluation.py
  - tests/test_benchmark_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/fixtures/ranking_production_like.json
  - docs/pipeline.md
  - docs/configuration.md
---

# FitCV — P0 Completion and Simplification Cycle

## Review Verdict

PR `#59` is merged at `4015a0e37b0ad797d98a9d21b6e353a79e67ca54`. It is
strong groundwork, not P0 closure. Review against `origin/main` confirms:

- **P0-C remains open:** `src/fitcv/evidence.py` annotates every evidence item
  against every canonical descriptor, while
  `src/fitcv/agentic_cv_analysis.py` derives qualifier conclusions from the
  resulting broad evidence set. Qualifier evidence must be scoped to canonical
  support for the same requirement instance.
- **P0-C has identity loss:**
  `build_required_skill_descriptors()` keys by `required_skill:<canonical>`.
  Separate SQL requirements can collapse and borrow each other's qualifiers.
- **Reuse semantics remain incomplete:**
  `build_cv_analysis_contract_fingerprint()` does not include qualifier-policy
  semantics, recovery/selection policy, or a fingerprint of parsed requirement
  descriptors.
- **Retrieval fallback wiring remains unsafe:**
  `run_vector_search()` treats `structured_jobs` as a lexical-mode trigger.
  Passing jobs into production callers merely to support stale-vector fallback
  can silently replace explicit vector retrieval with lexical retrieval.
- **P0-A evidence is incomplete:** `scripts/benchmark_ranking.py` uses
  synthetic profile/job fallbacks and `tests/fixtures/ranking_gold.json` is a
  smoke fixture. Neither proves production-quality DE/EN retrieval.
- **Recovery scope needs correction:** the current `origin/main` tree has no
  `direct_support_recovery` or `overflow_limit` implementation. The cycle must
  compare current channel-pool selection with full-pool selection before adding
  any recovery mechanism. Do not add a flag for an unmeasured problem.
- **Copy optimization is unproven:** `project_candidate_evidence()` deep-copies
  projected evidence because downstream code mutates annotations. Remove copies
  only after a profile proves material cost and immutable facts are separated.

## Approved Scope

This plan derives implementation scope from the user-provided P0 completion and
simplification verdict, reconciled against `origin/main` at
`4015a0e37b0ad797d98a9d21b6e353a79e67ca54`. No repository specification owns
this cycle. The plan remains `proposed` until the user approves execution.
Missing source-backed corpus, missing launcher capability, or unresolved
behavior at admission blocks dispatch; no lane invents a replacement decision.

## Goal

Close P0-A, P0-B, and P0-C with fresh correctness and performance evidence,
then delete mechanisms that do not earn their complexity. Keep current
production behavior as the rollback path until each promotion gate passes.

## Non-Goals

- No P1 content compiler or actionable-uncertainty work.
- No GraphRAG, ANN, late-interaction retrieval, LLM reranking, learned routing,
  retrieval agents, dynamic skill graph, or preference-learning changes.
- No provider credentials, external embedding calls, dependency changes,
  lockfile changes, or production-default changes without explicit approval.
- No new persistent evidence graph, telemetry system, or coordination artifact.
- No raw private job postings or candidate profiles committed to Git.

## Completion Gates

| Priority | Completion gate |
| --- | --- |
| P0-C | EN/DE qualifier cases pass; every qualifier status names supporting or contradicting evidence IDs; negated qualifiers never become positive; skill duration never comes from employment duration; duplicate canonical skills retain requirement-instance identity; legacy support fields remain compatible. |
| P0-B | Current channel-pool and full-pool arms run on identical corrected semantics; qualified requirement and evidence-pair recall, selection loss, p95 latency, context size, duplicates, and validation outcomes are reported; winner is selected and loser code is deleted. |
| P0-A | Held-out source-backed DE/EN corpus compares available retrieval arms under identical eligible jobs and Top-N; backend identity and contract fingerprints are truthful; stale vectors fall back without changing the requested strategy; one strategy is promoted or incumbent remains explicitly retained. |
| Simplification | No unmeasured recovery flag, provider arm, prepared context, immutable evidence layer, or new operational metric remains in code. Each retained mechanism has a measured owner, purpose, and rollback path. |

## Execution Approach

- Mode: `parallel-capable`
- Coordination: `git-tracked`
- **Execution binding:** CoS uses `plan-bound-execution` when activating each
  dependency-ready task.
- **Execution owner:** Chief of Staff (CoS), using repository launcher
  `C:\Users\HOANG PHI LONG DANG\.agents\project-os\scripts\herdr_main_launcher.py`.
- **Isolation:** fresh clean worktree from current `origin/main`; preserve the
  dirty primary checkout and all unrelated deletions, raw JSON, `.tmp/`, and
  untracked plans.
- **Base admission:** refresh `origin/main`; record exact repository root,
  worktree, branch, `HEAD`, and expected base. Current verified base is
  `4015a0e37b0ad797d98a9d21b6e353a79e67ca54`; dispatch must re-check it rather
  than trust this recorded value if remote changes.
- **Lane authority:** implementation lanes may edit only owned paths, commit
  lane changes, and push their lane branch when the approved execution turn
  grants it. No lane may merge, force-push, retarget a PR, mutate unrelated
  worktrees, discard unknown files, or publish private data.
- **Runtime grant:** `executor=codex`, `grant-child-agents=deny`, local
  filesystem/Git/shell only, no provider calls, credentials, dependency
  installation, push, merge, or production-default change for implementation
  lanes.
- **Herdr identity:** CoS must pass concrete `--session`, `--pane`, `--cwd`,
  `--expected-base`, `--profile`, `--task`, assignment identity, plan identity,
  task digest, and grant digest. Never use `--current`, `--session auto`, or
  `--pane auto` for a managed execution lane.
- **Parallel waves:** Task 1 runs first. Tasks 2 and 3 may run in parallel only
  after Task 1 acceptance because they have disjoint write ownership. Task 4 is
  the serialized convergence barrier. Task 5 owns review, integration, and
  final acceptance.
- **Sequential fallback:** if Herdr cannot admit two independent lanes, run
  Task 2 then Task 3 in separate clean worktrees; do not merge write scopes.

## Coordination State

The plan is the durable workflow record. CoS records lane identity, launch
evidence, task result, accepted proof, blockers, and retirement evidence here.
Herdr status is observation only.

- Coordination owner: `Codex controller`
- Branch: `detached HEAD` on isolated execution worktree
- Base commit: `4015a0e37b0ad797d98a9d21b6e353a79e67ca54`
- Expected workspace: `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-execution\JOB-PROJECT`
- Next action: dispatch Task 1 through Herdr with explicit session, pane, and runtime grant
- Blockers: none for Task 1 admission; corpus relevance remains conditionally admitted
### Task 0 Admission Record

- Mode: `plan-bound-execution`; plan status: `active`; base: `origin/main` at `4015a0e37b0ad797d98a9d21b6e353a79e67ca54`.
- Worktree: `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-execution\JOB-PROJECT`; HEAD `1b44da2771f1ba392db6bdebacc65bab49fa5ffe`; clean before dispatch.
- Corpus: `tmp/p0/corpus/raw_postings_de_en.jsonl`; 100 rows, 100 unique IDs, 50 DE/50 EN, 40 calibration + 10 held-out per language.
- Corpus SHA-256: `05C48EB8C0B5E1E61695E02EB1334B87D1BEC88B7B09FDEEE8047D8C534E872B`.
- Independent receipts: `C:\tmp\fitcv-p0-corpus\de_review_report.json`, `C:\tmp\fitcv-p0-corpus\en_review_report.json`, `C:\tmp\fitcv-p0-corpus\combined_review_report.json`; all `PASS`.
- Admission is conditional: relevance grade follows declared grade-1 convention; no target-profile semantic rubric exists. Raw corpus and baseline outputs remain local-only through `.git/info/exclude`; never commit raw postings.
- Baseline: `213 passed, 2 skipped`; ranking smoke and support smoke completed at `tmp/p0-baseline-ranking.json` and `tmp/p0-baseline-support.json`.

| Task | State | Workspace | Executor | Dependencies | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 0 | `completed` | `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-execution\JOB-PROJECT` | codex | none | fresh base, clean isolated worktree, baseline tests and benchmark outputs | base `4015a0e37b0ad797d98a9d21b6e353a79e67ca54`; HEAD `1b44da2771f1ba392db6bdebacc65bab49fa5ffe`; 213 passed, 2 skipped; baseline outputs in ignored `tmp/` |
| Task 1 | `active` | Herdr-managed isolated worktree; explicit pane assigned at dispatch | codex | Task 0 completed | adversarial EN/DE, negation, duration, identity, fingerprint, validator compatibility tests | Herdr dispatch next |
| Task 2 | `pending` | Fresh isolated worktree after Task 1 acceptance | codex | Task 1 | stale fallback, strategy contract, source-backed DE/EN held-out metrics, truthful backend diagnostics | pending |
| Task 3 | `pending` | Fresh isolated worktree after Task 1 acceptance | codex | Task 1 | corrected support-pair recall, selection loss, latency/context budget, validation outcome comparison | pending |
| Task 4 | `pending` | `C:\Users\HOANG PHI LONG DANG\.codex\worktrees\fitcv-p0-execution\JOB-PROJECT` | codex | Tasks 2–3 | winner/loser decision, loser deletion, rollback path, docs reconciliation | pending |
| Task 5 | `pending` | Fresh integration worktree after Task 4 | codex | Task 4 | exact-head reviews, fresh full verification, remote merge proof, retirement proof | pending |

## CoS MAIN AGENT Lane Contracts

| Lane | Ownership and allowed paths | Proof obligation | Runtime grant |
| --- | --- | --- | --- |
| `fitcv-p0-qualifiers` | `src/fitcv/evidence.py`, `src/fitcv/agentic_cv_analysis.py`, `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`; inspect `src/fitcv/enrich.py`, `src/fitcv/prompts/templates/enrich_extraction_v1.md`, and `tests/test_enrich.py`; edit those only if source wording is lost before descriptor construction | scoped qualifier evidence, conservative status, requirement-instance identity, semantic fingerprint invalidation, legacy consumer compatibility | profile `high`; Codex; child agents denied; no provider, credentials, push, merge, or production defaults |
| `fitcv-p0-retrieval` | `src/fitcv/vector_search.py`, `src/fitcv/pipeline.py`, `src/fitcv/pipeline_stage_runner.py`, `src/fitcv/embeddings.py`, `scripts/benchmark_ranking.py`, `tests/test_vector_search.py`, `tests/test_embeddings.py`, `tests/test_ranking_evaluation.py`, `tests/fixtures/ranking_production_like.json` | explicit strategy/data separation, stale-vector fallback, truthful diagnostics, held-out source-backed retrieval comparison | profile `normal`; Codex; child agents denied; no provider, credentials, push, merge, or production defaults |
| `fitcv-p0-support-selection` | `src/fitcv/evidence.py` after Task 1 acceptance, `scripts/benchmark_requirement_support.py`, `scripts/compare_requirement_support.py`, `tests/test_evidence.py`, `tests/test_benchmark_requirement_support.py`, `tests/test_compare_requirement_support.py` | current channel pool versus full pool under corrected support semantics; bounded budget and comparison recommendation | profile `normal`; Codex; child agents denied; no provider, credentials, push, merge, or production defaults |
| `fitcv-p0-integration` | only accepted files from Tasks 1–4, `docs/pipeline.md`, `docs/configuration.md`, and this plan ledger; no unrelated dirty files | exact reviewed head, complete verification, merge and post-merge proof | profile `high`; Codex integration action; merge only after independent review and CI gates |

## Task Breakdown

### Task 0: Admit plan and establish baseline

**Purpose:** Bind execution to current repository truth without touching the
dirty primary checkout.

**Task Function:** CoS admission, baseline verification, and lane dispatch.

**Template Profile:**
- Controller-selected: `none (lead controller)`

**Specification Coverage:** Execution binding, rollback baseline, and clean
workspace requirement.

**Required Skills:** `skill-chief-of-staff`, `skill-executing-plans`,
`skill-using-git-worktrees`, `skill-performance-optimization`.

**Files And Symbols:**

- Inspect `C:\Users\HOANG PHI LONG DANG\.agents\project-os\scripts\herdr_main_launcher.py`.
- Inspect `agents/*.toml`, `AGENTS.md`, scoped `AGENTS.md` files, and this plan.
- Inspect `origin/main` at dispatch; do not edit the primary checkout.

**Dependencies:** None.

**Authority:**

- Preauthorized local actions: fetch, inspect, create isolated worktree, run baseline commands,
  record evidence, and dispatch dependency-ready lanes.
- Stop for: ambiguous plan binding, dirty isolated worktree, missing launcher
  capability, missing source-backed corpus, unknown files, or base mismatch.

**Steps:**

1. Refresh `origin/main` and record its exact SHA.
2. Create or reuse one clean managed worktree from that SHA.
3. Verify launcher admission with `python C:\Users\HOANG PHI LONG DANG\.agents\project-os\scripts\herdr_main_launcher.py --help`; missing executable or required flags return `BLOCKED`.
4. Verify source-backed corpus admission at `tmp/p0/corpus/raw_postings_de_en.jsonl`. Each line must contain `job_url`, `language`, `job`, `relevance_grade`, `reviewed`, and `split`; require at least 50 German and 50 English postings, an 80/20 calibration/held-out split, and at least 10 reviewed relevant held-out postings per language. Do not commit this raw file.
5. Run the current focused baseline:
   `uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_vector_search.py tests/test_embeddings.py tests/test_enrich.py`.
6. Run existing smoke benchmarks without changing fixtures:
   `uv run python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_gold.json --output tmp/p0-baseline-ranking.json` and
   `uv run python scripts/benchmark_requirement_support.py --arm current-hash --output tmp/p0-baseline-support.json`.
7. Record baseline metrics and dispatch Task 1 through the launcher with
   concrete session, pane, workspace, branch, expected-base, profile, task
   digest, and runtime grant.

**Verification:** Git status is clean in isolated worktree; baseline commands
complete; primary checkout remains unchanged.

**Exit Criteria:** Current base, worktree, launcher capability, admitted corpus,
baseline outputs, and next lane are recorded. Missing corpus or launcher
admission returns `BLOCKED` before any write-capable lane starts.

### Task 1: Implement requirement-scoped qualifier semantics

**Purpose:** Make P0-C conservative, evidence-backed, and cache-safe.

**Task Function:** Requirement descriptor contract and support-matrix behavior.

**Template Profile:**
- Controller-selected: `high`

**Specification Coverage:** P0-C requirement scoping, negation, German parsing,
duration attribution, overall-versus-skill duration, requirement identity, and
reuse invalidation.

**Required Skills:** `skill-backend-verification`, `skill-systematic-debugging`,
`skill-test-driven-development`, `skill-code-standards`.

**Files And Symbols:**

- `src/fitcv/evidence.py`: `build_required_skill_descriptors`,
  `_annotate_requirement_support`, `_build_requirement_coverage`,
  `build_cv_analysis_contract_fingerprint`,
  `build_cv_analysis_input_fingerprint`, and evidence-selection helpers.
- `src/fitcv/agentic_cv_analysis.py`: requirement coverage assembly and
  compatibility output.
- `src/fitcv/enrich.py` and
  `src/fitcv/prompts/templates/enrich_extraction_v1.md`: inspect only; change
  only if tests prove raw requirement wording is discarded before descriptors
  are built.
- `tests/test_evidence.py`, `tests/test_agentic_cv_analysis.py`, and
  `tests/test_enrich.py` when enrichment contract changes.

**Dependencies:** Task 0.

**Authority:**

- Preauthorized local actions: additive fields, deterministic parsing, compatibility-preserving
  support-map changes, focused tests, and ignored local reports.
- Stop for: new persistent graph, LLM qualifier inference, validator/generator
  contract replacement, or schema migration not explicitly approved.

**Steps:**

1. Preserve `requirement_id: required_skill:<canonical>` for compatibility and
   add deterministic `requirement_instance_id` derived from source wording,
   canonical skill, and qualifier payload. Use instance IDs for support maps so
   two SQL requirements cannot share qualifier conclusions.
2. Build one ephemeral requirement-instance/evidence support matrix. Derive
   canonical, pool, and selected views by filtering that matrix; do not run
   qualifier checks over unrelated evidence.
3. Add additive qualifier audit fields with `supported`, `unverified`, and
   `contradicted` status plus `supporting_evidence_ids` and
   `contradicting_evidence_ids`. Keep `selected_support`, `support_strength`,
   and existing validator/generator statuses unchanged.
4. Parse only explicit duration, context, action, and proficiency wording.
   Recognize deterministic EN/DE forms including `at least 3 years`, `3+ years`,
   `more than 3 years`, `mindestens 3 Jahre`, `3 Jahre Erfahrung mit SQL`,
   `seit 2022`, `B2`, `C1`, and `fortgeschrittene Kenntnisse`. Keep vague
   `mehrjährige Erfahrung` unverified.
5. Add bounded EN/DE negation handling for `no`, `not`, `never`, `without`,
   `haven't`, `didn't`, `kein`, `keine`, `keinen`, `nicht`, `nie`, and `ohne`.
   Negated qualifier matches cannot be positive support.
6. Do not derive skill duration from parent employment dates or job-level
   `years_experience_min`. Represent job-level experience separately as an
   overall-experience requirement or leave it unverified; never copy it into
   every skill descriptor.
7. Add `requirement_support_policy_version: requirement-support-v2` and a
   deterministic fingerprint of parsed requirement instances to the analysis
   contract and input fingerprint. Changed semantics invalidate only affected
   CV analysis reuse.
8. Verify selected `verified` remains possible only when canonical support and
   all decisive qualifiers are supported by the same requirement's evidence.

**Verification:**

```text
uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_validator.py tests/test_cv_generator.py tests/test_enrich.py
uv run pytest -q tests/test_benchmark_requirement_support.py
```

Required cases: SQL classroom evidence plus production Python evidence; explicit
SQL production evidence; negated EN/DE context; explicit and inherited dates;
overall experience only; duplicate canonical SQL requirements; aliases; missing
qualifiers; contradictory level; reordered raw/canonical arrays; reused analysis
before and after policy changes.

**Exit Criteria:** Every qualifier conclusion is traceable to same-requirement
evidence; unsupported duration/context stays unverified; legacy consumers pass;
fingerprints differ when qualifier semantics or descriptor instances differ.

### Task 2: Separate retrieval strategy from data availability and finish P0-A

**Purpose:** Make stale-vector fallback correct, then measure retrieval on real
source-backed DE/EN data.

**Task Function:** Retrieval contract, pipeline wiring, benchmark arm registry,
and held-out evaluation.

**Template Profile:**
- Controller-selected: `high`

**Specification Coverage:** P0-A strategy comparison, stale-state fallback,
truthful backend identity, and production promotion gate.

**Required Skills:** `skill-performance-optimization`,
`skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**

- `src/fitcv/vector_search.py`: `run_vector_search` and retrieval diagnostics.
- `src/fitcv/pipeline.py` and `src/fitcv/pipeline_stage_runner.py`: production
  shortlist callers and passed-job data flow.
- `src/fitcv/embeddings.py`: backend and contract fingerprint helpers.
- `scripts/benchmark_ranking.py`: explicit available-arm registry and truthful
  `not_run` output for unavailable providers.
- `tests/test_vector_search.py`, `tests/test_embeddings.py`,
  `tests/test_ranking_evaluation.py`.
- `tests/fixtures/ranking_production_like.json`: sanitized, source-backed
  DE/EN postings with stable IDs and review labels; no private raw content.

**Dependencies:** Task 1 accepted descriptor/fingerprint contract; Task 0
baseline.

**Authority:**

- Preauthorized local actions: local deterministic/lexical benchmark arms, fallback wiring, test
  fixtures, and ignored reports.
- Stop for: provider access, credentials, new dependency, lockfile change, or
  production strategy promotion without user approval and gate evidence.

**Steps:**

1. Make retrieval strategy explicit. `structured_jobs` supplies data only; it
   must not implicitly select lexical retrieval. Preserve the current explicit
   strategy as the default behavior.
2. Pass eligible `passed_jobs` to production fallback logic without changing
   the requested vector strategy when compatible vectors exist.
3. When vector state is missing, stale, invalid, or contract-incompatible,
   fall back to deterministic lexical/taxonomy retrieval and emit diagnostics
   naming the requested strategy, fallback strategy, stale reason, and result
   counts.
4. Include strategy, backend ID, configured model, dimension, summary schema,
   contract fingerprint, and requirement-support policy version in reusable
   state diagnostics. Reuse must reject incompatible state, not raise without a
   safe fallback.
5. Add explicit benchmark arms for incumbent deterministic retrieval, lexical
   retrieval, and approved multilingual retrieval. If multilingual capability
   is absent or unapproved, emit `not_run` with reason; never report fabricated
   metrics.
6. Convert admitted `tmp/p0/corpus/raw_postings_de_en.jsonl` into
   `tests/fixtures/ranking_production_like.json` with stable IDs, preserved
   language, review labels, and calibration/held-out split fields. Keep raw
   local corpus inputs under ignored `tmp/` paths.
7. Add `--arm incumbent`, `--arm lexical`, and `--arm multilingual` to the
   benchmark CLI. `multilingual` must return `not_run` when provider capability
   or approval is absent.
8. Run calibration and held-out splits with identical eligible jobs and Top-N.
   Report recall, nDCG, p50/p95 latency, coverage, fallback count, and backend
   identity. Promote only a strategy with non-decreasing held-out recall and
   nDCG, no correctness failure, p95 within 20% of incumbent, and explicit
   rollback to incumbent.

**Verification:**

```text
uv run pytest -q tests/test_vector_search.py tests/test_embeddings.py tests/test_ranking_evaluation.py
uv run python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_production_like.json --arm incumbent --output tmp/p0-retrieval-incumbent.json
uv run python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_production_like.json --arm lexical --output tmp/p0-retrieval-lexical.json
uv run python scripts/benchmark_ranking.py --fixture tests/fixtures/ranking_production_like.json --arm multilingual --output tmp/p0-retrieval-multilingual.json
```

**Exit Criteria:** Production callers retain explicit strategy semantics;
stale vectors fall back safely; benchmark output distinguishes measured,
unavailable, and not-run arms; P0-A promotion or incumbent retention is
recorded with rollback evidence.

### Task 3: Compare P0-B channel-pool and full-pool selection

**Purpose:** Finish evidence retrieval without adding an unmeasured recovery
mechanism.

**Task Function:** Support-preservation experiment and comparison recommendation.

**Template Profile:**
- Controller-selected: `normal`

**Specification Coverage:** P0-B canonical/pool/selected support, retrieval-to-
selection loss, context budget, and simplification.

**Required Skills:** `skill-performance-optimization`,
`skill-backend-verification`, `skill-test-driven-development`.

**Files And Symbols:**

- `src/fitcv/evidence.py`: retrieval bundle, channel-pool merge, final
  selection, support matrix views, and selection diagnostics.
- `scripts/benchmark_requirement_support.py`: registry-driven current-pool and
  full-pool arms.
- `scripts/compare_requirement_support.py`: comparable report and decision
  output.
- `tests/test_evidence.py`, `tests/test_benchmark_requirement_support.py`,
  `tests/test_compare_requirement_support.py`.

**Dependencies:** Task 1 accepted; Task 2 may run in parallel.

**Authority:**

- Preauthorized local actions: deterministic local experiments, bounded selector changes, ignored
  benchmark reports, and comparison-tool/test changes.
- Stop for: adding `direct_support_recovery` solely because a plan mentions it,
  unbounded candidate expansion, LLM/reranker use, or production rollout before
  comparison.

**Steps:**

1. Measure current channel-pool selection as Arm A.
2. Add a `full-pool` arm to `scripts/benchmark_requirement_support.py`. It must
   annotate the complete candidate evidence pool once, then run one global
   selection with the same final `top_k`, candidate profile, job, qualifier
   semantics, selector, validation, and warm/cold conditions as Arm A.
3. Update `scripts/compare_requirement_support.py` so `--inputs` accepts two or
   more named arm reports; add `tests/test_compare_requirement_support.py` for
   pairwise comparison and missing-arm validation.
4. Report qualified requirement recall, qualified evidence-pair recall,
   retrieval-to-selection loss, candidate pool size, selected context tokens
   and characters, p50/p95 latency, duplicates, and validation outcomes.
5. Promote Arm B only when qualified recall is non-decreasing, evidence-pair
   recall improves by at least five percentage points, p95 latency and context
   size each stay within 20% of Arm A, and validation remains compatible.
6. Return metrics and recommendation to Task 4. Do not delete either arm in
   this task. Do not add a recovery flag. If a future measured regression
   requires recovery, open a separate plan with a concrete failure corpus and
   bounded budget.

**Verification:**

```text
uv run pytest -q tests/test_evidence.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py
uv run python scripts/benchmark_requirement_support.py --arm current-hash --output tmp/p0-support-current.json
uv run python scripts/benchmark_requirement_support.py --arm full-pool --output tmp/p0-support-full-pool.json
uv run python scripts/compare_requirement_support.py --inputs tmp/p0-support-current.json,tmp/p0-support-full-pool.json --output tmp/p0-support-comparison.json
```

**Exit Criteria:** Support layers are separately measurable; selected support
never borrows qualifiers from unrelated evidence; pairwise comparison returns a
reproducible winner recommendation for Task 4.

### Task 4: Converge and simplify

**Purpose:** Remove complexity that did not improve correctness or measured
performance, then reconcile documentation and plan state.

**Task Function:** Codex-controlled fan-in and simplification decision.

**Template Profile:**
- Controller-selected: `high`

**Specification Coverage:** P0 promotion, deletion decision, rollback, and
operational simplicity.

**Required Skills:** `skill-plan-document-reviewer`,
`skill-performance-optimization`, `skill-verification-before-completion`.

**Files And Symbols:** accepted files from Tasks 1–3, `docs/pipeline.md`,
`docs/configuration.md`, and this plan.

**Dependencies:** Tasks 1–3 accepted with fresh evidence.

**Authority:**

- Preauthorized local actions: delete losing arms, obsolete flags, duplicate paths, unsupported
  benchmark claims, and stale docs; update rollback and decision records.
- Stop for: unrelated cleanup, private-data publication, threshold changes after
  measurement, or code removal without consumer and test proof.

**Steps:**

1. Build a decision table for P0-A and P0-B with baseline, winner, metrics,
   compatibility, rollback, and owner.
2. Delete the losing P0-B arm and any unmeasured recovery scaffolding.
3. Retain only measured retrieval strategies. Keep unavailable providers as
   truthful `not_run` registry entries, not fake implementations.
4. Do not add `PreparedCandidateContext`, immutable evidence records, or new
   operational telemetry in this cycle. Run one profile of representative CV
   analysis; open a separate performance plan only if projection/deep-copy work
   consumes at least 20% of measured CV-analysis CPU time.
5. Update `docs/pipeline.md` and `docs/configuration.md` to match canonical
   behavior, fallback diagnostics, fingerprints, and promotion decisions.
6. Update this plan ledger with accepted proof, rejected alternatives, and
   rollback commands. Keep P1 deferred.

**Verification:** `git diff --check`; targeted tests from Tasks 1–3; benchmark
comparison reports present; `rg` confirms deleted flags and paths have no live
consumer.

**Exit Criteria:** One small production path remains for each P0 outcome; losing
complexity is deleted; docs, tests, diagnostics, and plan ledger agree.

### Task 5: Review, integrate, and accept

**Purpose:** Merge only the exact reviewed head with fresh proof.

**Task Function:** Independent review, PR integration, post-merge verification,
and lane retirement.

**Template Profile:**
- Controller-selected: `high`

**Specification Coverage:** Review, verification, merge, and cleanup gates.

**Required Skills:** `skill-requesting-code-review`,
`skill-reviewing-pull-requests`, `skill-verification-before-completion`,
`skill-finishing-a-development-branch`, `skill-dispatching-parallel-agents`.

**Files And Symbols:** PR metadata, `docs/pipeline.md`,
`docs/configuration.md`, and this plan ledger. Source files are immutable after
Task 4 acceptance unless a review finding is accepted and the PR head is
re-reviewed.

**Dependencies:** Task 4 accepted.

**Authority:**

- Preauthorized local actions: review lanes are read-only; integration may push the approved branch and merge only the exact reviewed SHA after CI and required approvals pass.
- Stop for: review FAIL/BLOCKED, unexpected post-review changes, missing CI,
  stale remote head, missing eligible review identity, or dirty integration
  worktree.

**Steps:**

1. Capture pre-review Git state and exact PR head SHA.
2. CoS dispatches independent `review-1` and `review-2` MAIN AGENT sessions
   through Herdr before activating integration. Each review gets separate
   explicit session, pane, workspace, and read-only contracts. Review scope:
   P0-C correctness, P0-A fallback/benchmark truth, P0-B deletion decision,
   tests, and docs.
3. Accept only `PASS` reviews with path/line evidence and no P0/P1 findings;
   resolve findings before integration.
4. Run final verification:

   ```text
   uv run pytest -q tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_vector_search.py tests/test_embeddings.py tests/test_enrich.py tests/test_validator.py tests/test_cv_generator.py tests/test_benchmark_requirement_support.py tests/test_compare_requirement_support.py tests/test_ranking_evaluation.py
   uv run pytest -q
   git diff --check
   ```

5. Confirm remote PR head equals reviewed SHA, required checks pass, and merge
   uses the normal PR path. Never mutate `main` directly.
6. Verify post-merge `origin/main`, record merge SHA, retire Herdr lanes, and
   hand exact cleanup authority to `skill-finishing-a-development-branch`.

**Exit Criteria:** Exact reviewed head is merged; fresh tests and CI pass;
post-merge base proof and retirement evidence are recorded; primary checkout
remains untouched.

## Final Verification Contract

Required evidence:

- P0-C adversarial EN/DE qualifier tests and legacy validator/generator tests.
- Analysis reuse mismatch proof for changed qualifier policy and requirement
  descriptors.
- P0-A source-backed held-out DE/EN benchmark with actual arm identity,
  calibration/held-out split counts, recall, nDCG, p50/p95, and fallback counts.
- P0-B current-pool versus full-pool report with qualified requirement recall,
  evidence-pair recall, selection loss, context budget, latency, duplicates, and
  validation result.
- Explicit winner/loser/deletion decisions and rollback path.
- Fresh focused suite, full suite, `git diff --check`, exact reviewed SHA,
  remote merge proof, and lane retirement proof.

## Completion Criteria

1. P0-C conclusions are requirement-scoped and evidence-backed.
2. P0-B has one retained selection path; unmeasured recovery code does not
   exist.
3. P0-A has one promoted or incumbent retrieval strategy backed by source-based
   held-out DE/EN evidence.
4. Reuse fingerprints invalidate changed semantics without manual cache clearing.
5. Existing `selected_support`, `support_strength`, validator, and generator
   contracts remain compatible.
6. No provider, dependency, private-data, or production-default change bypasses
   approval.
7. P1 remains deferred until P0 residual errors, cost, and manual effort are
   measured.

Skipped: P1 content compiler, actionable uncertainty, GraphRAG, retrieval
agents, ANN, late interaction, LLM reranking, learned routing, dynamic skill
graph, preference learning, new telemetry, and speculative immutable evidence
architecture. Add only through a new approved plan with measured justification.

