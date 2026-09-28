---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: fitcv-full-profile-vs-rag-impact
date: 2026-09-25
targets:
  - scripts/evaluate_requirement_support_live.py
  - src/fitcv/cv_generator.py
  - src/fitcv/llm_runtime.py
  - tests/fixtures/rag_impact_benchmark.json
  - tests/test_evaluate_requirement_support_live.py
  - tests/test_cv_generator.py
  - tests/test_llm_runtime.py
  - docs/pipeline.md
---

# FitCV — Full-Profile Versus RAG Impact Measurement Plan

## Goal

Measure whether FitCV's requirement-aware RAG pipeline produces equally useful
and trustworthy CVs with less candidate context than giving the model the
candidate's complete approved profile.

Keep retrieval quality and final-CV quality separate:

- Primary product comparison: complete profile versus FitCV RAG.
- Technical ablation: relevance-only retrieval versus requirement-aware RAG.
- No claim about production value until paired live outputs pass the corrected
  evaluator contract.

## Review Verdict

The supplied verdict has the right central recommendation but is not ready for
execution without evaluator hardening.

Required corrections:

- Current requirement coverage is term occurrence, not demonstrated support.
- Unsupported factual-claim rate uses marker counts, not factual claims.
- Failed generations are removed before acceptance denominators are calculated.
- First-pass and final acceptance are currently identical; repair is not run.
- Live input accepts preconstructed prompts instead of invoking FitCV retrieval.
- Declared output budgets are not passed to provider adapters.
- Full-profile section data can leak into RAG prompts through generation-context
  assembly.
- Full-profile data can also enter through gap guidance, structured-CV
  normalization, or post-generation backfill.
- The full-profile baseline must not fail because it lacks RAG-specific
  requirement-support metadata.
- Missing cost telemetry must not erase valid quality and token results.

Preserve the production grounding validator unless a failing experiment proves
that production behavior, rather than evaluator behavior, is defective.

## Implementation Outcomes

### Reproducible paired experiment

One versioned fixture provides the candidate profile, development jobs, held-out
jobs, approved requirement labels, approved evidence links, split membership,
and fixture fingerprint. Both arms derive prompts programmatically from the
same profile and job.

### Fair context comparison

The full-profile arm uses all approved candidate evidence. The RAG arm uses the
actual evidence selected by `analyze_ranked_job()` and
`retrieve_evidence_bundle()`. Both arms use the same model, template,
instructions, temperature, output budget, validation path, and job input.

Define one arm-specific authorized context projection and use it through prompt
construction, generation, structured-CV normalization, rendering, and
production-validator inputs. RAG context contains no unselected candidate facts
except shared identity metadata required for rendering.

Independent CV quality uses the same complete approved profile and job rubric
for both arms. Production FitCV validation is a separate diagnostic; the
full-profile arm receives equivalent full-profile requirement/evidence records,
never empty RAG metadata.

### Trustworthy metrics

Report per job and aggregate:

- supported qualification coverage;
- factual claim precision;
- generation success rate;
- accepted CV rate over attempted calls;
- first-pass acceptance;
- final acceptance after actual repair attempts;
- provider input, output, and total tokens;
- input-token reduction;
- estimated cost and actual provider cost when available;
- failed calls, latency, evidence IDs, prompt fingerprints, and limitations.

Keep token and cost scopes separate:

- generation-input tokens;
- total generation tokens;
- total workflow provider tokens, including retrieval, validation, and repair;
- local retrieval latency;
- actual provider cost;
- conservative estimated cost;
- cost per accepted CV when both quality and cost are available.

### Technical ablation

Retain existing offline arms and compare relevance-only retrieval with
requirement-aware selection under identical evidence budgets. Do not combine
retrieval, selection, generation, and validation deltas into one percentage.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-writing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: `fresh task-owned worktree from origin/main at 38735120dc6cac0435841ff6c99a3ab2c7611137`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed evaluator, runtime, prompt, fixture, test, and documentation files; run declared local checks; write task-owned `.tmp/` reports
- User-approval actions: provider calls, credential use, external publication, push, merge, destructive cleanup, or production retrieval-default changes
- Parallel ownership: `none; shared prompt and provider contracts require ordered edits`
- Sequential fallback: `fixture contract → prompt isolation → provider budget → evaluator metrics → offline acceptance gate → pilot generation → held-out evaluation → report and final verification`

## Task Breakdown

### Task 1: Define frozen paired-evaluation fixture

**Purpose:** Create one source of truth for profile, jobs, evidence labels, and
experiment splits.

**Task Function:** Fixture contract and dataset preparation.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: bounded data-contract work with existing fixture patterns.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: no delegated validator.

**Specification Coverage:** Reproducibility, held-out evaluation, approved
evidence labels, and paired input identity.

**Required Skills:** `skill-writing-plans`

**Files And Symbols:**
- Inspect: `tests/fixtures/requirement_support_benchmark.json`
- Create: `tests/fixtures/rag_impact_benchmark.json`
- Verify: `scripts/evaluate_requirement_support_live.py:validate_paired_inputs`

**Dependencies:** Existing requirement-support fixture and current candidate
profile schema.

**Authority:**
- Preauthorized local actions: create the fixture and focused fixture tests.
- Stop for: changing candidate profile authority, adding external data, or
  using provider credentials.

**Steps:**
- [ ] Step 1: Freeze one approved candidate profile snapshot and record its
  SHA-256 fingerprint.
- [ ] Step 2: Add five development jobs and eight-to-ten pilot held-out jobs;
  reserve expansion to twenty held-out jobs without changing the schema.
- [ ] Step 3: Add requirement IDs, canonical requirements, answerable flags,
  approved supporting evidence IDs, and dataset split fields.
- [ ] Step 4: Add fixture validation for duplicate IDs, missing evidence links,
  empty jobs, and split overlap.
- [ ] Step 5: Register decision thresholds before any pilot or held-out review:
  RAG generation-input tokens must be lower in at least 80% of final held-out
  pairs; mean supported-qualification coverage loss must be no more than 5
  percentage points; mean reviewed factual-precision loss must be no more than
  2 percentage points. Changing thresholds or evaluator rules invalidates the
  affected held-out split.

**Verification:**
- [ ] `python -m pytest -q tests/test_evaluate_requirement_support_live.py`
- Expected: fixture fingerprints and pair identity validate without provider
  calls.

**Exit Criteria:** Fixture can generate both experiment arms from profile and
job data without storing manually authored prompts.

### Task 2: Make generation context genuinely paired

**Purpose:** Ensure the experiment measures complete-profile context against
actual FitCV-selected context rather than two hand-written prompts or leaked
profile fields.

**Task Function:** Prompt construction and production-path integration.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: existing prompt-builder ownership; no new abstraction.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: focused tests cover prompt ownership.

**Specification Coverage:** Same model and writing contract; actual retrieval;
arm-specific authorized context across prompt and postprocessing; equivalent
independent quality review; production validator remains a separate diagnostic.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:project_candidate_evidence`
- Inspect: `src/fitcv/agentic_cv_analysis.py:analyze_ranked_job`
- Modify: `src/fitcv/cv_generator.py:_build_generation_prompt_context`
- Modify: `src/fitcv/cv_generator.py:_normalize_structured_cv`
- Modify: `src/fitcv/cv_generator.py:_execute_cv_generation_runtime`
- Modify: `src/fitcv/cv_generator.py:generate_cv`
- Modify: `scripts/evaluate_requirement_support_live.py:evaluate`
- Verify: `tests/test_cv_generator.py`, `tests/test_evaluate_requirement_support_live.py`

**Dependencies:** Task 1 fixture contract.

**Authority:**
- Preauthorized local actions: modify arm-context projection, evaluator pairing,
  prompt assembly, structured normalization, and focused tests.
- Stop for: changing retrieval defaults, validator rules, persisted evidence
  schemas, or production selection budgets.

**Steps:**
- [ ] Step 1: Build full-profile evidence with
  `project_candidate_evidence(profile)`.
- [ ] Step 2: Build RAG evidence with `analyze_ranked_job()` and retain its
  selected evidence IDs, requirement coverage, and selection summary.
- [ ] Step 3: Build an arm-specific authorized profile/context projection with
  shared identity/contact fields, full approved facts for the baseline, and
  selected-supported facts for RAG.
- [ ] Step 4: Derive `gap.matched`, education, certifications, languages,
  technologies, employers, and projects from the authorized projection; never
  pass the complete profile to RAG prompt construction.
- [ ] Step 5: Pass the authorized projection through `generate_cv()`,
  `_execute_cv_generation_runtime()`, `_normalize_structured_cv()`, and
  rendering. Keep the complete approved profile only for independent scoring.
- [ ] Step 6: Run independent CV quality review against the same complete
  approved profile and job rubric for both arms. Run production FitCV
  validation separately; construct equivalent full-profile support records for
  the baseline if that diagnostic is reported.
- [ ] Step 7: Record prompt hash, prompt bytes, evidence IDs, profile hash, job
  hash, configuration hash, and authorized-context hash for every attempt.

**Verification:**
- [ ] `python -m pytest -q tests/test_cv_generator.py tests/test_evaluate_requirement_support_live.py`
- Expected: baseline prompt contains complete approved evidence; RAG prompt
  contains only selected evidence and shared identity metadata; a unique fact
  present only in unselected evidence is absent from both the RAG prompt and
  final structured CV.

**Exit Criteria:** Pair construction proves actual FitCV retrieval and clean
context separation before any live provider call.

### Task 3: Enforce output-token budget through actual generation path

**Purpose:** Make paired generation budget real at provider boundary.

**Task Function:** Runtime contract correction.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: small shared runtime contract with adapter-specific payloads.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: payload assertions are sufficient.

**Specification Coverage:** Same enforced output budget for both arms and
spending safety.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv/llm_runtime.py:LlmTaskRequest`
- Modify: `src/fitcv/llm_runtime.py:_openai_compatible_adapter`
- Modify: `src/fitcv/llm_runtime.py:_chat_payload`
- Modify: `src/fitcv/cv_generator.py:_execute_cv_generation_runtime`
- Modify: `src/fitcv/cv_generator.py:generate_cv`
- Modify: `scripts/evaluate_requirement_support_live.py:evaluate`
- Verify: `tests/test_llm_runtime.py`, `tests/test_evaluate_requirement_support_live.py`

**Dependencies:** Task 2 provider call path.

**Authority:**
- Preauthorized local actions: add optional request budget, actual generation
  path wiring, adapter payload wiring, validation, and tests.
- Stop for: provider API changes not represented by existing adapter contracts
  or live calls without explicit approval.

**Steps:**
- [ ] Step 1: Add `max_output_tokens: int | None` to `LlmTaskRequest`.
- [ ] Step 2: Reject non-positive explicit values.
- [ ] Step 3: Send budget through the OpenAI-compatible Responses payload and
  Chat Completions fallback using their existing fields. Extend other adapters
  only when the shared runtime contract requires it.
- [ ] Step 4: Thread fixture budget from `generate_cv()` to
  `_execute_cv_generation_runtime()`, `LlmTaskRequest`, and the provider
  payload; do not create a second evaluator-only provider path.
- [ ] Step 5: Add pre-call estimated-spend validation from pinned rate-card
  metadata, maximum call count, and bounded output tokens.
- [ ] Step 6: Preserve omitted-budget compatibility for existing callers.

**Verification:**
- [ ] `python -m pytest -q tests/test_llm_runtime.py tests/test_evaluate_requirement_support_live.py`
- Expected: Responses and Chat Completions payloads contain configured output
  budget; `generate_cv()` reaches that field; invalid budgets fail before
  network execution; omitted budgets preserve existing behavior.

**Exit Criteria:** Budget parity is enforced, not merely recorded in input
metadata.

### Task 4: Replace live evaluator heuristics and denominators

**Purpose:** Measure supported qualifications and factual claims with explicit
ground truth.

**Task Function:** Evaluation metrics and independent review contract.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: evaluator schema work uses existing deterministic reports.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: claim labels are fixture/reviewer evidence, not another agent.

**Specification Coverage:** Requirement support, claim precision, failed-call
visibility, repair accounting, independent review, comparable validation, and
optional cost telemetry.

**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`

**Files And Symbols:**
- Modify: `scripts/evaluate_requirement_support_live.py:_review_output`
- Modify: `scripts/evaluate_requirement_support_live.py:evaluate`
- Modify: `tests/test_evaluate_requirement_support_live.py`
- Inspect: `src/fitcv/validator.py:run_all_validations`
- Verify: `src/fitcv/validator.py:run_all_validations` remains unchanged unless
  a production defect is separately proven.

**Dependencies:** Tasks 1–3.

**Authority:**
- Preauthorized local actions: change evaluator schema, metrics, review records,
  dry-run validation, and focused tests.
- Stop for: altering production grounding semantics or introducing an LLM judge,
  GraphRAG, vector database, or new agent.

**Steps:**
- [ ] Step 1: Add structured claim records from generated CV output; exclude
  headings and non-factual boilerplate.
- [ ] Step 2: Emit a blind claim-review queue under `.tmp/` with
  `claim_id`, `claim_text`, `support_status`, `supporting_evidence_ids`, and
  `review_status`. Use `supported`, `unsupported`, and `partially_supported`
  support labels plus `reviewed`, `unreviewed`, and `adjudicated` review states.
- [ ] Step 3: Have an independent reviewer assess both variants without arm
  labels; review ambiguous claims and baseline–RAG disagreements, then record
  adjudication. Never count `unreviewed` claims as supported.
- [ ] Step 4: Label claims against approved profile evidence and, separately,
  against RAG-selected evidence.
- [ ] Step 5: Calculate qualification coverage from approved requirement IDs,
  not term occurrence.
- [ ] Step 6: Evaluate independent CV quality for both arms against the same
  complete profile and job rubric. Report production FitCV validation as a
  separate diagnostic with equivalent full-profile baseline records.
- [ ] Step 7: Keep every attempted call in output; calculate success and
  acceptance over attempted calls.
- [ ] Step 8: Report first-pass and final acceptance separately only when repair
  attempts actually run.
- [ ] Step 9: Preserve quality and token results when actual cost telemetry is
  absent; report actual cost as `unavailable`, estimated cost separately, and
  enforce the pre-call spending safeguard.
- [ ] Step 10: Add per-variant generation-input tokens, total generation tokens,
  total workflow tokens, local retrieval latency, cost fields, prompt-token
  reduction, and raw pair results to the report schema.

**Verification:**
- [ ] `python -m pytest -q tests/test_evaluate_requirement_support_live.py tests/test_validator.py`
- Expected: job-description mentions do not count as candidate support; failed
  calls remain in denominators; unresolved claims are visible and excluded from
  supported precision; baseline is not rejected for missing RAG metadata;
  missing actual cost does not erase quality results.

**Exit Criteria:** Dry-run and mocked live tests prove truthful metrics before
provider execution, and the independent review queue can reach zero unresolved
claims for a final held-out report.

## Offline Acceptance Gate

Do not start pilot or held-out provider generation until this gate passes on
development fixtures:

- requirement mentions without candidate evidence are rejected;
- unsupported and partially supported claims are represented explicitly;
- failed attempts remain in attempted denominators;
- unreviewed claims are not treated as supported;
- both arms receive equivalent independent quality review conditions;
- baseline production-validator diagnostics use full-profile support records;
- RAG prompt and normalized output exclude unique unselected facts;
- configured output budget reaches the actual `generate_cv()` request;
- actual cost may be unavailable without disabling quality/token reporting;
- estimated spend stays below approved pre-call ceiling.

### Task 5: Run staged pilot and technical ablation

**Purpose:** Produce decision evidence without overclaiming from a small sample.

**Task Function:** Controlled evaluation execution and report assembly.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: sequential execution protects provider budget and held-out
  integrity.

**Validator Profile:**
- Controller-selected: `<none>`
- Selection basis: final report checks are repository-local.

**Specification Coverage:** Development checks, pilot feasibility, preregistered
held-out evaluation, technical ablation, cost safeguards, and reproducible
report.

**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `scripts/benchmark_requirement_support.py`
- Inspect: `scripts/compare_requirement_support.py`
- Modify: `docs/pipeline.md`
- Verify: task-owned `.tmp/` reports and fixture fingerprints.

**Dependencies:** Tasks 1–4; explicit provider approval before live calls.

**Authority:**
- Preauthorized local actions: run offline benchmarks, dry-run evaluator, and
  write task-owned `.tmp/` reports.
- Stop for: provider calls, credentials, cost-bearing execution, or held-out
  prompt changes without explicit approval.

**Steps:**
- [ ] Step 1: Run five development jobs and inspect prompt/context parity plus
  the offline acceptance gate.
- [ ] Step 2: Run eight-to-ten pilot jobs only for feasibility and measurement
  debugging; do not use them as final held-out evidence.
- [ ] Step 3: Freeze prompts, evaluator, claim-review policy, thresholds, and
  configuration before selecting the final held-out split. If pilot inspection
  changes any of these, exclude pilot jobs from final claims.
- [ ] Step 4: Run final held-out jobs, up to twenty, without inspecting outputs
  before the final report is locked.
- [ ] Step 5: Run existing relevance-only versus requirement-aware offline
  arms under identical budgets.
- [ ] Step 6: Before live calls, calculate conservative estimated spend from
  pinned model rates, maximum calls, measured input-token upper bounds, and
  bounded output tokens. Require explicit provider approval and use provider
  spending limits when available.
- [ ] Step 7: Report paired per-job deltas, raw counts, generation-input tokens,
  total generation tokens, total workflow tokens, local retrieval latency,
  failures, actual-cost availability, estimated cost, and limitations.
- [ ] Step 8: Write only supported CV-impact wording; keep current sixteen-case
  result as engineering benchmark evidence.

**Verification:**
- [ ] `uv run pytest -q tests/test_benchmark_requirement_support.py tests/test_evaluate_requirement_support_live.py`
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm lexical-ablation --output .tmp/rag-impact-lexical-ablation.json`
- [ ] `uv run python scripts/benchmark_requirement_support.py --arm lexical-requirement-aware --output .tmp/rag-impact-lexical-requirement-aware.json`
- Expected: offline outputs share fixture, scenario, budget, and arm metadata;
  live report preserves every attempted pair and final held-out results are
  evaluated against preregistered thresholds.

**Exit Criteria:** Reproducible pilot or expanded report supports or rejects the
claim that RAG reduces generation-input context while preserving qualification
coverage and factual precision. Total workflow savings are reported only if
retrieval, validation, repair, and generation usage support that separate claim.

## Verification

```powershell
uv run pytest -q tests/test_evaluate_requirement_support_live.py tests/test_llm_runtime.py tests/test_cv_generator.py tests/test_validator.py tests/test_benchmark_requirement_support.py
uv run python scripts/benchmark_requirement_support.py --arm lexical-ablation --output .tmp/rag-impact-lexical-ablation.json
uv run python scripts/benchmark_requirement_support.py --arm lexical-requirement-aware --output .tmp/rag-impact-lexical-requirement-aware.json
git diff --check
git status --short
```

Expected:

- Focused evaluator, runtime, prompt, validator, and benchmark tests pass.
- Provider budget reaches adapter payloads.
- Full-profile and RAG prompts are reproducible and context-distinct.
- Failed generations remain visible in attempted denominators.
- Missing cost telemetry reports unavailable cost without losing quality data.
- Estimated spending is bounded before live calls; actual billed cost is never
  represented by the estimate.
- Generation-input, total-generation, and total-workflow token scopes remain
  separate.
- Offline ablation remains separate from final-CV impact.
- No production retrieval defaults or validator rules change.
- No generated report under `.tmp/` is committed.

## Completion Criteria

The plan is ready for completion verification when:

1. Fixture contains immutable profile, development jobs, held-out jobs, support
   labels, evidence links, claim-review policy, decision thresholds, and one
   fingerprint.
2. Both arms invoke the real FitCV prompt and generation path with only context
   selection differing.
3. Arm-specific authorized context controls prompt construction, gap guidance,
   structured normalization, rendering, and validation diagnostics.
4. RAG prompt and final structured CV contain no unselected candidate facts.
5. Baseline independent quality review uses the same complete-profile rubric and
   is not penalized for missing RAG metadata.
6. Output-token budget reaches the actual `generate_cv()` request and configured
   provider payloads.
7. Requirement coverage uses approved support labels, not keyword presence.
8. Factual claim precision uses independently reviewed factual claims; all
   unreviewed claims remain visible and excluded from support.
9. Provider failures remain in attempted, success, and acceptance accounting.
10. Repair metrics are reported only when repair attempts execute.
11. Quality and token results survive missing monetary telemetry.
12. Pre-call estimated spending is bounded and actual billed cost remains
    distinct from the estimate.
13. Generation-input, total-generation, and total-workflow token scopes are
    reported separately.
14. Final held-out results use preregistered thresholds and exclude any jobs
    used to tune prompts or evaluator rules.
15. Pilot and offline ablation reports include raw counts, fingerprints, tokens,
    evidence IDs, failures, limitations, and exact configuration.
16. Full verification passes with no unrelated file changes.

Deferred: GraphRAG, vector database, learned embeddings, LLM-as-judge platform,
additional agents, and production retrieval optimization. Add only after this
measurement produces a specific, reproducible bottleneck.
