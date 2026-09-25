---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
contract_version: "1"
name: fitcv-rag-impact-test-suite
date: 2026-09-25
targets:
  - data/linkedin-2026-09-25-22-54-17.json
  - tests/fixtures/rag_impact_benchmark.json
  - tests/fixtures/rag_impact_review_annotations.example.json
  - scripts/prepare_rag_impact_corpus.py
  - scripts/evaluate_requirement_support_live.py
  - scripts/compare_rag_impact.py
  - tests/test_prepare_rag_impact_corpus.py
  - tests/test_rag_impact_dataset.py
  - tests/test_evaluate_requirement_support_live.py
  - tests/test_compare_rag_impact.py
  - docs/pipeline.md
  - docs/rag-impact-review-protocol.md
  - docs/rag-impact-review-agents.md
  - tests/fixtures/rag_impact_review_agent_outputs.example.json
  - tests/test_rag_impact_review_agents.py
---

# FitCV — RAG Impact Test Suite Implementation Plan

## Goal

Build a reproducible test suite that measures whether FitCV's RAG pipeline
preserves CV quality while reducing model context, token use, cost, or latency
versus sending the candidate's complete approved profile.

The suite must separate retrieval quality, generated-CV quality, grounding
correctness, human reviewer preference, and operational economics. It must not
claim RAG value from one narrow deterministic pilot or from offline retrieval
metrics alone.

## Implementation Outcomes

### Versioned evaluation corpus

Use `data/linkedin-2026-09-25-22-54-17.json` as source input. It contains 100
scraped LinkedIn jobs. Add one deterministic sanitization/extraction step and
extend `tests/fixtures/rag_impact_benchmark.json` into one canonical derived
corpus with:

- exactly 40 paired scenarios across development, pilot, and held-out splits;
- 10 development, 10 pilot, and 20 held-out scenarios;
- at least 10 cases where FitCV selects less evidence than the full-profile arm;
- requirement labels, approved evidence IDs, answerability, difficulty, and
  expected context-difference metadata;
- immutable profile and corpus fingerprints;
- preregistered quality, token, and acceptance thresholds.

The derived fixture stores normalized job IDs, titles, descriptions,
locations, company names, work modes, contract types, experience levels, and
job functions. The extractor removes job URLs, company URLs, application URLs,
logo URLs, poster names, poster profile URLs, scraper metadata, application
counts, and other non-evaluation fields. It redacts emails, phone numbers, and
URLs embedded in descriptions. Raw candidate profile data, credentials,
generated CV text, and provider responses stay out of Git. Example review
records contain only schema-safe synthetic values.

### Trustworthy paired evaluator

Extend the existing evaluator so both arms use the same model, template,
generation settings, output budget, job input, and validation path. Only
authorized candidate context differs:

- baseline: complete approved profile;
- FitCV: evidence selected by `analyze_ranked_job()`.

Report per-pair and aggregate deterministic metrics, human-review metrics,
provider usage, latency, failure denominators, and missing-cost state. Keep
actual cost separate from estimates.

### Blind human-review protocol

Add a versioned annotation contract and reviewer instructions for blind paired
comparison. Reviewers score both outputs without seeing arm identity. Adjudicate
disagreements with a second reviewer or an explicit unresolved state; never
silently average missing reviews.

### Output-review agent set

Create three run-scoped reviewer agents, dispatched by the controller through
Herdr against blinded output artifacts:

- `grounding-reviewer`: checks claims against approved profile evidence and
  requirement labels; returns evidence references and unsupported-claim flags;
- `recruiter-quality-reviewer`: scores relevance, completeness, readability,
  and usefulness without seeing arm identity;
- `review-adjudicator`: sees only reviewer disagreements and unresolved cases,
  records a decision or preserves `unresolved`.

Reviewer agents emit versioned JSON annotations, not raw CV copies. Their
scores inform the report but do not replace controller acceptance or required
human review for disputed cases.

### Statistical and decision report

Add paired effect calculations with deterministic bootstrap confidence intervals,
raw counts, scenario fingerprints, and threshold decisions. The report must
state whether evidence supports:

1. RAG quality parity;
2. lower generation-input context;
3. lower total provider cost or latency;
4. a production rollout decision.

Cost and quality claims remain `not_applicable` when required telemetry or
review coverage is missing.

## Execution Approach

- Mode: `parallel-capable`
- Coordination: `git-tracked`
- Required skills: `skill-chief-of-staff`, `skill-dispatching-parallel-agents`, `skill-executing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-plan-document-reviewer`, `skill-verification-before-completion`
- Isolation: `task-owned Herdr worktree per write-capable lane`
- Commit policy: `verified per-task checkpoint commits preauthorized`
- Preauthorized local actions: `inspect repository sources; edit task-owned files; run declared tests and offline scripts; create ignored .tmp reports; commit exact task-owned changes; use scripts/herdr_main_launcher.py for approved lane dispatch`
- User-approval actions: `provider calls; credential use; real candidate data import; external publication; push; merge; force push; destructive cleanup; production retrieval-default changes`
- Parallel ownership: `Task 1 owns fixture and dataset-contract tests; Task 2 owns evaluator, statistics, and evaluator tests; Task 3 owns reviewer-agent contracts, example annotations, review protocol, and review-agent tests`
- Sequential fallback: `complete Task 1 and Task 2 before Task 4; complete Task 3 before Task 4; run Task 5 review and final verification after all implementation lanes retire`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/fitcv-rag-impact-test-suite`
- Base commit: `d9c67ea03d4054e4fa06ae29adbf21fb715ae553`
- Expected workspace: `new task-owned worktree from base; preserve current workspace changes outside this plan, including deleted legacy data files, untracked data/linkedin-2026-09-25-22-54-17.json, and existing untracked plans`
- Next action: `run Task 5 read-only acceptance review after Task 4 offline proof`
- Blockers: `live provider execution remains gated; stale repository planning artifacts were bypassed by explicit user instruction on 2026-09-25`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 — Corpus contract | `completed` | task-owned Herdr worktree | `codex` | none | dataset contract tests | `ce72c448`; integrated as `66551285`; 25-test suite later passed |
| Task 2 — Paired evaluator | `completed` | task-owned Herdr worktree | `codex` | none | evaluator and metric tests | `0b7ac288`; integrated as `43a9e65`; evaluator suite passed |
| Task 3 — Blind review protocol | `completed` | task-owned Herdr worktree | `codex` | none | schema and documentation checks | `5dac8eb9`; integrated as `f267f6e0`; protocol suite passed |
| Task 4 — Integration report | `completed` | lead controller worktree | `codex` | Tasks 1–3 | offline suite and report checks | `35 passed`; source SHA `5f934050146069035b84ec186846de79056339892657dc2e615a4f84198f69c5`; corpus SHA `f293bba4979b35acf1f2215de0bd8f96c67a1d832d946eb2d0dd8725f37bec39`; benchmark provider calls false; legacy validation 6/17 with limitation recorded |
| Task 5 — Independent review and acceptance | `completed` | lead controller worktree | `codex` | Task 4 | review verdict and fresh final proof | `PASS`; 33 final tests passed; `git diff --check` passed; Herdr lanes done and workspaces closed; live provider gate remains explicit |

Herdr dispatch rules:

- The lead controller is sole writer of this plan's coordination state.
- Each Herdr lane receives one exact branch, worktree, task ownership, base
  commit, and allowed-path list.
- Herdr is transport and observation only; Git and this plan own durable state.
- Herdr lanes do not call providers, import real candidate data, push, merge,
  or remove worktrees.
- Codex controller owns acceptance; reviewer agents may score output artifacts
  but cannot mark plan tasks complete, change thresholds, or merge code.
- Missing launcher preflight or delivery evidence blocks task acceptance.

## Task Breakdown

### Task 1: Freeze corpus and dataset contract

**Purpose:**
- Convert the 100-job LinkedIn source into a deterministic, sanitized,
  stratified corpus that can expose meaningful context differences without
  storing direct identifiers or contact data in the evaluation fixture.

**Task Function:**
- Dataset contract design and fixture validation.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded schema and fixture work; controller selects lowest
  profile that can verify split, evidence, and fingerprint invariants.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent fixture review; validator verifies schema and
  split invariants without changing fixture contents.

**Specification Coverage:**
- Versioned corpus, paired identity, held-out isolation, context-difference
  coverage, PII exclusion, approved evidence labels, and preregistered gates.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `data/linkedin-2026-09-25-22-54-17.json`
- Inspect: `tests/fixtures/rag_impact_benchmark.json`
- Inspect: `scripts/evaluate_requirement_support_live.py:validate_benchmark_fixture`
- Create: `scripts/prepare_rag_impact_corpus.py`
- Create: `tests/test_prepare_rag_impact_corpus.py`
- Create: `tests/test_rag_impact_dataset.py`
- Modify: `tests/fixtures/rag_impact_benchmark.json`

**Dependencies:**
- Existing fixture schema and current profile/evidence IDs.

**Authority:**
- Preauthorized local actions: `read the supplied job source; copy it as a task-owned ignored input when the Herdr worktree does not inherit untracked files; create the deterministic extractor and its tests; modify only the derived fixture and dataset-contract tests; run focused offline tests; commit exact lane changes`
- Stop for: `candidate profile import, PII retention, credential use, provider calls, threshold changes outside the fixture, or edits outside owned paths`

**Steps:**
- [x] Step 1: Compute and record the exact SHA-256 of
  `data/linkedin-2026-09-25-22-54-17.json`; fail closed when source hash changes
  without an explicit fixture refresh.
- [x] Step 2: Before lane edits, verify the source hash in the task-owned
  worktree. Keep the source file ignored and uncommitted; the derived fixture
  records only its hash and source job IDs.
- [x] Step 3: Normalize the 100 source records into an allowlisted job shape;
  redact URLs, emails, phone numbers, poster fields, scraper metadata, and
  application metadata before any record enters the derived fixture.
- [x] Step 4: Select exactly 40 jobs with deterministic seed `20260925`, split
  into 10 `development`, 10 `pilot`, and 20 `held_out` cases. Stratify on
  language signal, work mode, experience level, and description length; fail
  when any required stratum cannot be met.
- [x] Step 5: Preserve the existing fixture ID and schema lineage; add source
  hash, source job ID, corpus version, case difficulty, scenario rationale, and
  context-difference fields without changing approved evidence semantics.
- [x] Step 6: Add explicit labels for answerable requirements, approved
  evidence IDs, unsupported requirements, and expected context differences.
- [x] Step 7: Add thresholds: supported-qualification loss `<= 0.05`, reviewed
  factual-precision loss `<= 0.02`, human quality loss `<= 0.25` points on a
  five-point scale, and generation-input reduction on at least `80%` of held-out
  pairs.
- [x] Step 8: Add validation for duplicate IDs, missing evidence links, split
  overlap, empty cases, source-hash drift, profile fingerprint drift,
  PII-like fields, required strata, exact split counts, and the minimum
  context-difference count.
- [x] Step 9: Add synthetic review-annotation examples covering accepted,
  rejected, disagreement, and unresolved-review states.

**Verification:**
- [x] `uv run pytest -q tests/test_prepare_rag_impact_corpus.py tests/test_rag_impact_dataset.py tests/test_evaluate_requirement_support_live.py`
- [x] `uv run python scripts/prepare_rag_impact_corpus.py --input data/linkedin-2026-09-25-22-54-17.json --base-fixture tests/fixtures/rag_impact_benchmark.json --output .tmp/rag-impact-derived-corpus.json --seed 20260925`
- Expected: fixture loads, fingerprints remain stable, splits do not overlap,
  source records are sanitized, exact split counts pass, context-difference
  minimum passes, and no provider code executes.

**Exit Criteria:**
- Fixture and validation tests provide one immutable, PII-free source of truth
  for all later lanes.

### Task 2: Build paired evaluator and statistical metrics

**Purpose:**
- Turn the current live evaluator into a complete test harness for deterministic
  grounding, blind-review joins, token/cost accounting, and paired statistics.

**Task Function:**
- Evaluator contract, metric aggregation, and regression proof.

**Template Profile:**
- Controller-selected: `high`
- Selection basis: evaluator changes cross provider boundaries and require
  precise denominator and failure reasoning.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent review of metrics, failure accounting, and
  provider-call guards.

**Specification Coverage:**
- Fair paired generation, truthful denominators, deterministic quality review,
  blind human-review integration, cost/latency metrics, confidence intervals,
  and no live-call behavior during tests.

**Required Skills:**
- `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `scripts/evaluate_requirement_support_live.py:build_paired_inputs`
- Inspect: `scripts/evaluate_requirement_support_live.py:evaluate`
- Inspect: `scripts/evaluate_requirement_support_live.py:_review_output`
- Modify: `scripts/evaluate_requirement_support_live.py:validate_benchmark_fixture`
- Modify: `scripts/evaluate_requirement_support_live.py:evaluate`
- Create: `scripts/compare_rag_impact.py`
- Modify: `tests/test_evaluate_requirement_support_live.py`
- Create: `tests/test_compare_rag_impact.py`

**Dependencies:**
- Existing paired evaluator; Task 1 fixture contract.

**Authority:**
- Preauthorized local actions: `modify evaluator and evaluator tests; create comparison script and its tests; run mocked and offline checks; commit exact lane changes`
- Stop for: `provider calls, credentials, production generation behavior changes, retrieval-default changes, raw output persistence, or edits outside owned paths`

**Steps:**
- [x] Step 1: Preserve programmatic pairing through
  `build_paired_inputs()`; reject hand-authored prompt pairs in fixture-driven
  mode and assert baseline/FitCV parity for model, template, settings, budget,
  fixture hash, and scenario ID.
- [x] Step 2: Keep every attempted call in denominators. Report attempted,
  succeeded, failed, first-pass accepted, final accepted, and unresolved review
  counts separately for each arm.
- [x] Step 3: Add human-review annotation loading by pair ID and variant,
  requiring rubric version, reviewer ID hash, score completeness, and explicit
  adjudication state. Do not expose reviewer identity or raw CV text in reports.
- [x] Step 4: Add paired quality metrics for requirement coverage, reviewed
  factual precision, human quality score, pairwise preference, and review
  agreement. Missing reviews remain visible and excluded from quality
  denominators.
- [x] Step 5: Add token scopes for generation input, generation total, and
  workflow total. Keep actual cost, estimated cost, and unavailable cost as
  distinct fields.
- [x] Step 6: Add deterministic paired bootstrap intervals using seed
  `20260925`, `10_000` resamples, and scenario-level resampling. Report point
  deltas, interval bounds, sample counts, and zero-variance cases explicitly.
- [x] Step 7: Add `scripts/compare_rag_impact.py` to validate compatible
  fixture/rubric/config fingerprints and emit one report with raw counts,
  arm-level metrics, FitCV-minus-baseline deltas, confidence intervals, gate
  decisions, and limitations.
- [x] Step 8: Ensure dry-run and all mocked tests make zero provider calls and
  never require credentials.

**Verification:**
- [x] `uv run pytest -q tests/test_evaluate_requirement_support_live.py tests/test_compare_rag_impact.py`
- [x] `uv run python scripts/evaluate_requirement_support_live.py --input .tmp/paired-evaluation.json --output .tmp/live-dry-run.json`
- Expected: deterministic and mocked live tests pass; failed calls remain in
  denominators; missing cost does not erase quality or token metrics; bootstrap
  output is reproducible; dry-run performs no provider call.

**Exit Criteria:**
- Evaluator and comparison script produce reproducible, paired, review-aware
  reports without live credentials.

### Task 3: Define blind review protocol and annotation handoff

**Purpose:**
- Make output review repeatable, blinded, and safe for later live runs; create
  three bounded reviewer-agent contracts for grounding, recruiter quality, and
  disagreement adjudication.

**Task Function:**
- Review rubric, annotation contract, reviewer instructions, and privacy rules.

**Template Profile:**
- Controller-selected: `normal`
- Selection basis: documentation and contract work with bounded ambiguity.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent review checks that arm identity cannot leak into
  reviewer material.

**Specification Coverage:**
- Blind paired scoring, reviewer independence, adjudication, privacy, and
  review completeness; bounded output-review agent roles and JSON contracts.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Create: `docs/rag-impact-review-protocol.md`
- Create: `docs/rag-impact-review-agents.md`
- Create: `tests/fixtures/rag_impact_review_annotations.example.json`
- Create: `tests/fixtures/rag_impact_review_agent_outputs.example.json`
- Create: `tests/test_rag_impact_review_protocol.py`
- Create: `tests/test_rag_impact_review_agents.py`
- Inspect: `scripts/evaluate_requirement_support_live.py:_review_output`
- Verify: `tests/test_rag_impact_review_protocol.py`

**Dependencies:**
- Existing deterministic rubric and Task 1 annotation example shape.

**Authority:**
- Preauthorized local actions: `create reviewer-agent contracts, review protocol, synthetic annotation examples, and review-agent tests; run documentation and JSON validation; commit exact lane changes`
- Stop for: `real candidate data, raw generated CV publication, reviewer identity data, provider calls, or edits to evaluator implementation`

**Steps:**
- [x] Step 1: Define rubric version `rag-human-review-v1` with five-point
  scores for requirement relevance, factual accuracy, completeness, readability,
  and recruiter usefulness.
- [x] Step 2: Define pairwise preference, confidence, issue tags, reviewer
  notes, and `adjudication_status` values `single_review`, `adjudicated`, and
  `unresolved`.
- [x] Step 3: Require blinded arm labels, stable pair IDs, fixture hash,
  evaluator version, and rubric version in every annotation record.
- [x] Step 4: Define reviewer workflow: independent scoring first, disagreement
  detection second, adjudication third, unresolved retention fourth.
- [x] Step 5: Define privacy handling: raw CV text remains in an access-
  controlled untracked artifact; tracked examples use synthetic text only;
  reports contain hashes and scores, not names, email addresses, or raw output.
- [x] Step 6: Define `grounding-reviewer` input, output, and failure contract:
  blinded pair artifact, approved evidence map, claim list, evidence IDs,
  unsupported-claim flags, confidence, and `review_status`.
- [x] Step 7: Define `recruiter-quality-reviewer` contract: blinded pair
  artifact, job rubric, five-point dimension scores, pairwise preference,
  issue tags, confidence, and no arm-identifying fields.
- [x] Step 8: Define `review-adjudicator` contract: disagreement records only,
  reviewer annotations, decision rationale, selected score or `unresolved`,
  and no ability to alter source outputs.
- [x] Step 9: Define Herdr dispatch inputs and receipts for each reviewer agent:
  exact run ID, fixture/rubric fingerprints, read-only artifact path, allowed
  output path, timeout, and delivery status. Runtime sessions remain
  disposable; annotations and receipts remain durable evidence.

**Verification:**
- [x] `uv run python -c "import json; json.load(open('tests/fixtures/rag_impact_review_annotations.example.json', encoding='utf-8')); print('ok')"`
- [x] `uv run python -c "import json; json.load(open('tests/fixtures/rag_impact_review_agent_outputs.example.json', encoding='utf-8')); print('ok')"`
- [x] `uv run pytest -q tests/test_rag_impact_review_protocol.py tests/test_rag_impact_review_agents.py`
- Expected: example annotation JSON is valid and contract assertions reject
  unblinded, incomplete, mismatched, or unresolved-as-accepted records;
  reviewer-agent outputs contain no raw CV text or arm identity.

**Exit Criteria:**
- A reviewer can score one paired result without knowing which arm produced it,
  reviewer agents can emit valid grounding and quality annotations, and
  adjudication preserves disagreement without inventing consensus.

### Task 4: Integrate commands, reports, and offline acceptance gate

**Purpose:**
- Make the test suite executable by a fresh controller from plan plus Git and
  document the exact boundary before any provider run.

**Task Function:**
- Integration, command wiring, documentation, and offline acceptance.

**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: integration requires repository authority and cross-lane
  judgment.

**Validator Profile:**
- Controller-selected: `review`
- Selection basis: independent read-only review of integrated commands, paths,
  and acceptance gates.

**Specification Coverage:**
- Reproducible handoff, Herdr recovery, offline proof, live-call boundary,
  report interpretation, and no production-default changes.

**Required Skills:**
- `skill-executing-plans`, `skill-backend-verification`

**Files And Symbols:**
- Modify: `docs/pipeline.md`
- Modify: `docs/superpowers/plans/2026-09-25-fitcv-rag-impact-test-suite-plan.md`
- Verify: `scripts/evaluate_requirement_support_live.py`
- Verify: `scripts/compare_rag_impact.py`
- Verify: `tests/fixtures/rag_impact_benchmark.json`

**Dependencies:**
- Tasks 1–3 complete and accepted by the lead controller.

**Authority:**
- Preauthorized local actions: `reconcile accepted lane commits; update pipeline documentation and this plan ledger; run declared offline checks; create ignored .tmp reports; commit integration checkpoint`
- Stop for: `provider calls, credential use, real-data import, push, merge, production retrieval changes, or unresolved lane conflicts`

**Steps:**
- [x] Step 1: Reconcile lane commits against base and reject out-of-scope
  changes, stale-head evidence, missing Herdr delivery evidence, and plan/Git
  mismatches.
- [x] Step 2: Document fixture preparation, dry-run, mocked live, review
  annotation, reviewer-agent dispatch, statistical comparison, and final
  report commands in `docs/pipeline.md`.
- [x] Step 3: Document the live gate: provider/model, credential source,
  maximum spend, reviewer approval, held-out lock, and no raw output commit.
- [x] Step 4: Run offline benchmark arms and the new suite with fixed fixture,
  rubric, and configuration fingerprints. Run reviewer agents against mocked
  paired outputs before any live provider call.
- [x] Step 5: Record actual results, limitations, and deferred decisions in the
  plan without claiming live quality evidence.

**Verification:**
- [x] `uv run pytest -q tests/test_prepare_rag_impact_corpus.py tests/test_rag_impact_dataset.py tests/test_evaluate_requirement_support_live.py tests/test_compare_rag_impact.py tests/test_benchmark_requirement_support.py`
- [x] `uv run python scripts/benchmark_requirement_support.py --arm lexical-ablation --runs 50 --warmups 5 --output .tmp/rag-impact-lexical-ablation.json`
- [x] `uv run python scripts/benchmark_requirement_support.py --arm lexical-requirement-aware --runs 50 --warmups 5 --output .tmp/rag-impact-lexical-requirement-aware.json`
- [x] `git diff --check`
- Expected: all offline checks pass, reports share fingerprints, no provider
  call occurs, and only owned files change.

**Exit Criteria:**
- Fresh controller can resume from plan plus Git, run the offline suite, and
  identify exactly what approval is still required before live execution.

### Task 5: Independent review and final acceptance

**Purpose:**
- Challenge the completed test suite and accept only evidence-backed scope.

**Task Function:**
- Read-only implementation review and final verification.

**Template Profile:**
- Controller-selected: `review`
- Selection basis: independent verification profile; no implementation edits.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: review lane is itself read-only validation.

**Specification Coverage:**
- Scope integrity, test adequacy, privacy, denominator correctness, and
  Herdr/Git recovery evidence.

**Required Skills:**
- `skill-plan-document-reviewer`, `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/superpowers/plans/2026-09-25-fitcv-rag-impact-test-suite-plan.md`
- Inspect: `scripts/evaluate_requirement_support_live.py`
- Inspect: `scripts/compare_rag_impact.py`
- Inspect: `tests/test_rag_impact_dataset.py`
- Inspect: `tests/test_evaluate_requirement_support_live.py`
- Inspect: `tests/test_compare_rag_impact.py`
- Verify: `docs/pipeline.md`

**Dependencies:**
- Task 4 complete; all Herdr implementation lanes retired and worktree
  ownership released.

**Authority:**
- Preauthorized local actions: `read-only inspection; run declared tests and git diff checks; record review evidence in the plan ledger`
- Stop for: `editing implementation files, changing thresholds, provider calls, credential use, push, merge, or cleanup before lane retirement proof`

**Steps:**
- [x] Step 1: Check every outcome against source, tests, fixture, and report
  evidence; treat unchecked boxes as unproven.
- [x] Step 2: Confirm deterministic and human metrics remain separate and that
  missing cost/review data cannot produce a false positive.
- [x] Step 3: Confirm no raw outputs, credentials, PII, or provider payloads
  entered tracked files.
- [x] Step 4: Confirm Herdr delivery receipts, branch/base/head identity, lane
  retirement, and worktree release evidence.
- [x] Step 5: Run final verification and return `PASS`, `FAIL`, or `BLOCKED`
  with path-and-line evidence.

**Verification:**
- [x] `uv run pytest -q tests/test_rag_impact_dataset.py tests/test_evaluate_requirement_support_live.py tests/test_compare_rag_impact.py tests/test_benchmark_requirement_support.py`
- [x] `git diff --check`
- [x] `git status --short --branch`
- Expected: fresh checks pass, review finds no unresolved required scope, and
  worktree contains only accepted changes plus declared ignored artifacts.

**Exit Criteria:**
- Lead controller accepts independent review evidence and leaves plan status
  `proposed` until execution begins; no live-result claim is added by this
  plan.

## Verification

Final artifact checks after all lanes retire:

```powershell
uv run pytest -q tests/test_rag_impact_dataset.py tests/test_evaluate_requirement_support_live.py tests/test_compare_rag_impact.py tests/test_benchmark_requirement_support.py
uv run python scripts/compare_rag_impact.py --help
git diff --check
git status --short --branch
```

Expected:

- Dataset, evaluator, comparison, and offline benchmark tests pass.
- Mock reviewer agents produce valid grounding, quality, and adjudication
  annotations against blinded sample outputs.
- Dry-run and mocked live paths make zero provider calls.
- Paired reports preserve failures, missing reviews, missing cost, fingerprints,
  token scopes, and confidence intervals.
- No raw CV output, credential, PII, or provider payload is tracked.
- Production retrieval defaults and validator rules remain unchanged.
- Herdr lanes have successful delivery evidence and released worktrees.

## Completion Criteria

The plan is ready for completion verification when:

1. The 100-job source file is fingerprinted and produces exactly 40 sanitized
   scenarios: 10 development, 10 pilot, and 20 held-out.
2. The corpus has at least 10 measurable baseline-versus-FitCV context
   differences.
3. Fixture, rubric, evaluator, source, and configuration fingerprints are
   validated.
4. Both arms use programmatic pairing and identical generation settings.
5. Deterministic grounding, human review, retrieval, token, cost, and latency
   metrics remain separate.
6. Failed calls, missing reviews, and missing cost telemetry remain visible and
   cannot improve acceptance rates by disappearing from denominators.
7. Bootstrap intervals are reproducible from scenario-level paired samples.
8. Dry-run, mocked live, focused, and offline benchmark checks pass.
9. Documentation gives a fresh controller exact commands and live-call gates.
10. Grounding, recruiter-quality, and adjudication reviewer agents have
   versioned contracts, mocked proof, and Herdr delivery evidence.
11. No provider call, credential use, real-data import, push, merge, or cleanup
   occurs without its explicit approval boundary.
12. Independent review returns `PASS` and all Herdr lanes retire cleanly.

Deferred until this suite identifies a concrete bottleneck: GraphRAG, vector
database changes, learned retrieval, LLM-as-judge infrastructure, production
retrieval-default changes, and larger-scale provider execution.
