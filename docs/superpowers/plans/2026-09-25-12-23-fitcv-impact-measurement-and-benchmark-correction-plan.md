---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-impact-measurement-and-benchmark-correction
targets:
  - scripts/benchmark_requirement_support.py
  - scripts/benchmark_requirement_support_legacy.py
  - scripts/compare_requirement_support.py
  - tests/fixtures/requirement_support_benchmark.json
  - tests/test_benchmark_requirement_support.py
  - tests/test_validator.py
  - docs/pipeline.md
---

# FitCV — Impact Measurement and Benchmark Correction Plan

## Goal

Produce trustworthy, reproducible evidence for the requirement-grounded CV
analysis milestone before changing production retrieval. Correct benchmark
grounding validation, distinguish requirement loss from evidence-pair loss,
compare the historical pre-grounding implementation with current FitCV, and
report retrieval, selection, validation, latency, and prompt-size results on a
frozen evaluation set.

## Review Verdict

The supplied verdict is accepted with two execution corrections:

1. The benchmark must use `analyze_ranked_job()` output for current positive
   trials. `_run_validation()` currently rebuilds simplified coverage rows from
   selected support, so validation can miss the production
   `canonical_skill`/`selected_support`/`supporting_evidence_ids` contract.
2. Commit `7263fba` predates the current benchmark script. Historical
   comparison therefore needs an explicit compatibility adapter and common
   output schema. Do not claim a baseline comparison from current-code
   self-reported metrics.

The verdict's other findings are valid:

- `negative_cases` are declared but not executed as independent validation
  trials.
- `_support_metrics()` currently emphasizes evidence-pair loss and loops only
  over expected keys; it does not report requirement recall or unexpected
  returned requirement IDs correctly.
- `pool_12_decision` can trigger on alternative evidence loss even when a
  requirement remains covered.
- `run_benchmark()` measures JSON serialization under `prompt_ms`, not
  `build_generation_prompt()` time.
- Five repetitions are suitable for CI smoke checks, not strong local p95
  claims.
- The current fixture is one scenario with a few probes, not the proposed
  12–20-case frozen evaluation set.

## Invariants and Non-Goals

- Do not change production retrieval defaults, selection weights, shortlist
  embeddings, validator rules, provider calls, or persisted evidence schemas.
- Keep `requirement_coverage` as the sole production requirement-support
  authority.
- Keep current benchmark compatibility: `run(weight)` and `--weight` remain
  valid.
- Compare all arms with the same fixture fingerprint, `top_k`, evidence budget,
  selection policy, and runtime environment.
- Count support as valid only when the requirement–evidence pair is present in
  frozen approved links. Self-reported support counts never define ground truth.
- Keep generated JSON reports and historical worktrees under `$env:TEMP`; do
  not commit machine-specific timings or historical worktrees.
- This phase does not claim final generated-CV quality. Provider-backed
  generation and human/independent output review remain a later phase.

## Execution Approach

- Mode: `inline sequential`.
- Coordination: `none` for implementation; use a clean isolated worktree from
  `origin/main` because the current primary checkout has unrelated dirty files.
- Order: fixture contract → production analysis/validation path → metrics and
  timing → historical adapter and comparison report → full verification.
- Do not start retrieval optimization until the corrected report identifies a
  material bottleneck.

## Evaluation Contract

The fixture becomes the single source of truth for:

- scenario/profile/JD inputs;
- canonical requirement IDs;
- approved requirement–evidence pairs;
- explicit unsupported requirements;
- positive and negative validation claims;
- expected validation decision and expected grounding violation class.

The benchmark emits `evaluation_schema_version: 1` and one normalized arm
record with:

- `git_head`, `implementation_ref`, `fixture_sha256`, `top_k`, `selection_policy`;
- canonical, retrieved, selected requirement recall;
- canonical-to-retrieved and retrieved-to-selected evidence-pair recall;
- correct pairs, missed pairs, incorrect pairs, and assignment precision;
- validation case matrix with expected/actual decision, expected/actual
  violation class, and `pass`;
- median and p95 retrieval, selection, generation-prompt-build, validation,
  and total latency;
- prompt bytes and estimated tokens;
- semantic backend metadata and production-default-change status.

Requirement recall uses requirements with at least one approved supporter as its
denominator. Evidence-pair recall uses all approved requirement–evidence pairs.
Unsupported requirements stay in the validation matrix but do not enter the
positive-support denominator.

## Task Breakdown

### Task 1: Freeze the evaluation dataset and case schema

**Purpose:** Replace one broad fixture plus unexecuted negative metadata with a
small fixed dataset that proves positive support, unsupported requirements,
retrieval loss, selection loss, and grounding rejection.

**Task Function:** Test-data design and benchmark contract.

**Template Profile:** `unresolved`.

**Specification Coverage:** Frozen 12–20-case dataset; approved links;
positive/negative grounding trials; common IDs across historical and current
arms.

**Required Skills:**
- `skill-writing-plans`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify `tests/fixtures/requirement_support_benchmark.json`.
- Modify `tests/test_benchmark_requirement_support.py`.
- Inspect `tests/test_validator.py` and `tests/test_agentic_cv_analysis.py` for
  existing grounding and analyzer fixtures.

**Dependencies:** None.

**Authority:**
- Preauthorized: edit benchmark fixture and focused benchmark tests.
- Stop: changing production contracts, validator policy, or expected links
  without recording the new fixture decision in the plan review.

**Steps:**
1. Add `evaluation_schema_version`, deterministic scenario IDs, and a fixture
   fingerprint input containing 16 scenarios: exact skill, canonical alias,
   paraphrase, unsupported skill, wrong evidence ID, canonical synonym,
   responsibility-only text, one item supporting multiple requirements,
   redundant support, below-cutoff support, tight `top_k`, education support,
   certification support, genuine candidate gap, long evidence text, and mixed
   supported/unsupported requirements.
2. Give each scenario `profile`, `job_context`, `top_k`, `expected_support`,
   `claims`, and `validation_cases`. Each validation case includes `case_id`,
   `cv_text`, `expected_valid`, `expected_violation_class`, and optional
   `requirement_coverage_override` for deliberately malformed negative probes.
3. Keep approved evidence IDs stable and derive expected positive pairs only
   from fixture data. Record empty expected support for unsupported requirements.
4. Add tests that reject duplicate scenario IDs, missing required case fields,
   duplicate approved pairs, and negative cases with no expected violation
   class.

**Verification:**
- `uv run pytest -q tests/test_benchmark_requirement_support.py`
- Expected: fixture schema tests pass and all 16 scenario IDs are unique.

**Exit Criteria:** Fixture can drive every benchmark arm and every declared
validation case without hand-coded expected IDs outside the fixture.

### Task 2: Route benchmark validation through production analysis coverage

**Purpose:** Prevent benchmark validation from bypassing requirement-grounding
semantics by reconstructing simplified coverage rows.

**Task Function:** Benchmark integration with analyzer and validator owners.

**Template Profile:** `unresolved`.

**Specification Coverage:** Real `requirement_coverage`; positive and negative
validation decisions; unsupported requirements remain visible.

**Required Skills:**
- `skill-backend-verification`
- `skill-test-driven-development`
- `skill-systematic-debugging`

**Files And Symbols:**
- Modify `scripts/benchmark_requirement_support.py`.
- Modify `tests/test_benchmark_requirement_support.py`.
- Add only missing focused assertions to `tests/test_validator.py`.
- Reuse `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`.
- Reuse `src/fitcv/validator.py:run_all_validations`.

**Dependencies:** Task 1.

**Authority:**
- Preauthorized: benchmark-only adapter code and tests.
- Stop: relaxing validator rules, adding a second production support field, or
  making fixture-only overrides affect production analysis.

**Steps:**
1. Add a benchmark helper that runs `analyze_ranked_job(job, profile, config,
   top_k=top_k)` for current arms and returns its `evidence_payload`,
   `evidence_selection_summary`, `requirement_coverage`, and status. Normalize
   the benchmark bundle from this one analysis record so retrieval metrics and
   validation consume the same selected evidence; do not run a second
   independent retrieval or rebuild coverage from support maps.
2. Make analyzer ranking inputs deterministic in the fixture configuration so
   the run reaches analysis. Record blocked or failed analyzer status as a
   failed benchmark case, never as an implicit pass.
3. Pass actual selected evidence, actual selection summary, and actual
   `requirement_coverage` into `run_all_validations()`.
4. Execute every fixture validation case independently. For negative probes,
   apply only the declared case-local coverage override or claim text; retain
   the production validator and selected evidence payload unchanged.
5. Classify actual violations by stable class: `missing_verified_support`,
   `wrong_evidence_id`, `unsupported_requirement`, `unrelated_validation`, or
   `none`. Require expected class and decision to match.
6. Add regression tests proving a simplified legacy row cannot make a wrong-ID
   claim pass and that a requirement with empty support remains in analyzer
   coverage.

**Verification:**
- `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_validator.py tests/test_agentic_cv_analysis.py`
- Expected: valid claims pass; wrong-ID, unsupported, and responsibility-only
  claims fail for grounding reasons; every requirement descriptor appears.

**Exit Criteria:** Benchmark validation consumes production-shaped coverage and
  reports a case matrix with no hardcoded zero or omitted unsupported row.

### Task 3: Correct support metrics and production prompt timing

**Purpose:** Separate requirement coverage from alternative evidence loss and
  measure the real prompt builder instead of JSON serialization.

**Task Function:** Benchmark metrics and performance instrumentation.

**Template Profile:** `unresolved`.

**Specification Coverage:** Requirement recall, evidence-pair recall,
  assignment precision/errors, pool expansion trigger, prompt size, repeated
  timing.

**Required Skills:**
- `skill-performance-optimization`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify `scripts/benchmark_requirement_support.py:_support_metrics`.
- Modify `scripts/benchmark_requirement_support.py:run_benchmark`.
- Modify `tests/test_benchmark_requirement_support.py`.
- Reuse `src/fitcv/cv_generator.py:build_generation_prompt`.

**Dependencies:** Tasks 1–2.

**Authority:**
- Preauthorized: benchmark metrics, CLI flags, and offline timing probes.
- Stop: changing production defaults or interpreting submillisecond noise as a
  product improvement.

**Steps:**
1. Build metric key space from the union of expected and returned requirement
   IDs. Compute valid stage pairs as `expected_pairs ∩ stage_pairs`, missed
   pairs as `expected_pairs - stage_pairs`, and incorrect pairs as
   `stage_pairs - expected_pairs`.
2. Compute requirement recall from requirements whose valid stage pair set is
   non-empty. Keep pair recall and requirement recall separate for canonical,
   retrieved, and selected stages.
3. Trigger pool expansion only when a positive-support requirement has no valid
   retrieved supporter. Report alternative supporter loss separately.
4. Replace `prompt_ms` with `generation_prompt_build_ms` measured around
   `build_generation_prompt()` using the selected evidence, actual gap,
   actual requirement coverage, selection summary, and fixture template.
   Report `benchmark_payload_serialization_ms` separately if retained.
5. Add `--runs` and `--warmups`; default to `5` and `1` for CI. Use `50` or
   more measured runs for local comparison commands. Report median and p95 with
   identical workload ordering and no provider calls.
6. Add tests for full coverage with partial pair loss, unexpected returned
   requirement IDs, requirement-level pool trigger behavior, and prompt metric
   naming.

**Verification:**
- `uv run pytest -q tests/test_benchmark_requirement_support.py`
- `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 4 --runs 5 --warmups 1 --output .tmp/fitcv-lexical-4.json`
- Expected: requirement recall stays 100% when one alternative supporter is
  omitted; pool expansion stays skipped; output has separate prompt-build and
  payload-serialization fields.

**Exit Criteria:** Metrics answer requirement loss, pair loss, assignment error,
  selection loss, and timing questions without conflating them.

### Task 4: Add historical baseline adapter and common comparison report

**Purpose:** Compare pre-grounding FitCV at `7263fba` with current FitCV at
  `b2700fb` or its descendant using one independent evaluator and common IDs.

**Task Function:** Historical compatibility and report assembly.

**Template Profile:** `unresolved`.

**Specification Coverage:** Experiment A feature impact; normalized evidence
  IDs; reproducible JSON comparison report.

**Required Skills:**
- `skill-using-git-worktrees`
- `skill-backend-verification`
- `skill-test-driven-development`

**Files And Symbols:**
- Add `scripts/benchmark_requirement_support_legacy.py`.
- Add `scripts/compare_requirement_support.py`.
- Modify `tests/test_benchmark_requirement_support.py`.
- Reuse `tests/fixtures/requirement_support_benchmark.json`.

**Dependencies:** Tasks 1–3.

**Authority:**
- Preauthorized: create task-owned detached worktrees under `$env:TEMP`, install
  existing dependencies, run offline benchmark code, and write `.tmp` JSON.
- Stop: changing either checked-out ref, using provider credentials, or
  substituting current self-reported support metrics for the legacy run.

**Steps:**
1. Make `benchmark_requirement_support_legacy.py` accept `--source-root`,
   `--fixture`, and `--output`. Prepend the selected ref's `src` directory to
   `sys.path`, call the historical `retrieve_evidence_bundle()` contract, and
   normalize selected evidence to common `evidence_id` pairs. Emit an explicit
   `baseline_adapter_status` and fail closed when the historical contract is
   unavailable.
2. Make `compare_requirement_support.py` accept baseline JSON, current JSON,
   retrieval-arm JSON files, and output path. Verify fixture SHA, scenario IDs,
   `top_k`, and approved-pair fingerprint match before comparing.
3. Report Experiment A and Experiment B as separate sections. Never combine
   feature impact and retrieval-policy impact into one headline percentage.
4. Include raw case matrices, requirement/pair recall, incorrect/missed pairs,
   validation results, timing, prompt bytes/tokens, backend metadata, commit
   refs, and known limitations.
5. Use detached worktrees for `7263fba` and current `origin/main`; leave them
   under `$env:TEMP` until verification completes, then remove only those task-owned
   worktrees after clean-state confirmation.

**Verification:**
- `git worktree add --detach "$env:TEMP/fitcv-legacy-7263fba" 7263fba`
- `git worktree add --detach "$env:TEMP/fitcv-current-origin-main" origin/main`
- `uv run python scripts/benchmark_requirement_support_legacy.py --source-root "$env:TEMP/fitcv-legacy-7263fba" --fixture tests/fixtures/requirement_support_benchmark.json --output "$env:TEMP/fitcv-baseline.json"`
- `uv run python scripts/benchmark_requirement_support.py --arm current-hash --pool-size 4 --runs 50 --warmups 5 --output "$env:TEMP/fitcv-current-hash.json"`
- `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 4 --runs 50 --warmups 5 --output "$env:TEMP/fitcv-lexical-4.json"`
- `uv run python scripts/benchmark_requirement_support.py --arm lexical --pool-size 8 --runs 50 --warmups 5 --output "$env:TEMP/fitcv-lexical-8.json"`
- `uv run python scripts/compare_requirement_support.py --baseline "$env:TEMP/fitcv-baseline.json" --current "$env:TEMP/fitcv-current-hash.json" --retrieval "$env:TEMP/fitcv-lexical-4.json,$env:TEMP/fitcv-lexical-8.json" --output "$env:TEMP/fitcv-impact-report.json"`
- Expected: report rejects mismatched fixture fingerprints and contains separate
  Experiment A/B results.

**Exit Criteria:** One JSON report compares historical feature impact and
current retrieval arms using the same independent metrics, or stops with an
explicit baseline-adapter failure instead of a false comparison.

### Task 5: Document measurement contract and complete verification

**Purpose:** Make the corrected benchmark reproducible without implying that
  final CV quality or provider cost was measured.

**Task Function:** Documentation and final verification.

**Template Profile:** `unresolved`.

**Specification Coverage:** Reproducibility, non-goals, report interpretation,
  optimization gate.

**Required Skills:**
- `skill-verification-before-completion`
- `skill-backend-verification`

**Files And Symbols:**
- Modify `docs/pipeline.md` with benchmark commands and metric definitions.
- Modify `tests/test_benchmark_requirement_support.py` only if documentation
  examples need executable contract assertions.

**Dependencies:** Tasks 1–4.

**Authority:**
- Preauthorized: documentation and verification commands.
- Stop: changing production configuration or claiming final generated-CV
  quality from selected evidence alone.

**Steps:**
1. Document fixture fingerprinting, arm definitions, requirement-vs-pair recall,
   validation case matrices, timing fields, and the distinction between
   selected coverage and final generated-CV coverage.
2. Document CI smoke command (`5` runs) and local comparison command (`50`
   runs), including no-provider and no-production-default-change guarantees.
3. Record the report's baseline and retrieval results without choosing an
   optimization unless a metric-defined bottleneck is material.
4. Remove task-owned `$env:TEMP` worktrees and outputs only after report files,
   verification logs, and Git state are captured in the handoff.

**Verification:**
- `uv run pytest -q`
- `git diff --check`
- `git status --short`
- Expected: all tests pass; no production config changes; only planned files
  are modified; report schema and commands execute from a clean worktree.

**Exit Criteria:** Corrected benchmark and report are reproducible, documented,
  and ready to gate a separate retrieval-optimization plan.

## Final Acceptance

Accept only when all conditions hold:

- current positive validation uses `analyze_ranked_job()` coverage;
- every declared negative case executes and matches its violation class;
- requirement recall and evidence-pair recall are separate for all stages;
- unexpected requirement IDs count toward assignment errors;
- pool expansion triggers only on uncovered supported requirements;
- prompt-build timing measures `build_generation_prompt()`;
- CI and local run counts are explicit;
- baseline and current outputs use one fixture fingerprint and independent
  normalized metrics;
- production retrieval defaults, shortlist embedding behavior, validator rules,
  and provider usage remain unchanged;
- full test suite and `git diff --check` pass.

## Deferred Work

- Do not add real semantic embeddings, direct-link recovery, pool-size changes,
  selection-policy tuning, or global hash-backend replacement in this plan.
- Do not claim final generated-CV coverage, provider token usage, or human
  quality improvement. Plan that work only after this report identifies its
  measured bottleneck.
