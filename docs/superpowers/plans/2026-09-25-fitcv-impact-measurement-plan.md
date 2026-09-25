---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-impact-measurement
date: 2026-09-25
targets:
  - tests/fixtures/requirement_support_benchmark.json
  - scripts/benchmark_requirement_support.py
  - scripts/compare_requirement_support.py
  - scripts/benchmark_requirement_support_legacy.py
  - tests/test_benchmark_requirement_support.py
  - docs/pipeline.md
  - scripts/evaluate_requirement_support_live.py
  - tests/test_evaluate_requirement_support_live.py
---

# FitCV — Impact Measurement Implementation Plan

## Goal

Measure whether requirement-grounded evidence selection communicates more
genuine, job-relevant qualifications than conventional relevance-based
selection under the same evidence and context budgets.

Produce:

1. A reproducible offline impact report.
2. A gated live-generation evaluation for final-CV impact.
3. Decision evidence for retrieval or selection optimization.

## Review Verdict

The supplied strategy is accepted as direction with these corrections:

- Offline evaluation is the first gate. Do not spend provider budget before
  independent scenarios prove selection benefit.
- Conventional top-k baseline is distinct from
  `requirement_gain_weight=0.0`; zero gain retains other FitCV selection terms.
- The fixture must execute genuinely independent scenarios. Scenario labels
  that reuse one profile, JD, and support map do not count as independent cases.
- Assignment precision is reported only for arms that emit explicit
  requirement–evidence links.
- Retrieval, selection, and generation loss remain separate. Do not combine
  them into one improvement percentage.
- Selected-evidence metrics cannot support final-CV quality claims by
  themselves.

## Implementation Outcomes

### Controlled offline evaluation

Run four arms over identical profiles, JDs, approved evidence, budgets,
`top_k`, trimming rules, and prompt inputs:

| Arm | Retrieval | Selection | Purpose |
| --- | --- | --- | --- |
| A — Conventional baseline | Lexical | Highest-scoring top-k | Product comparison |
| B — Ablation | Current lexical channels | Requirement gain disabled | Isolate requirement reward |
| C — FitCV | Current lexical channels | Requirement gain enabled | Primary implementation |
| D — Current configured | Hash-based channels | Requirement gain enabled | Evaluate hash scoring |

### Metrics and report

Per scenario and aggregate, report:

- Retrieved supported-requirement recall.
- Selected supported-requirement coverage.
- Evidence-pair recall.
- Evidence-assignment precision when explicit links exist.
- Correct, missed, and incorrect requirement–evidence pairs.
- Micro and macro coverage.
- Selected item count, prompt bytes, and estimated prompt tokens.
- Retrieval, selection, prompt-build, validation, and total latency.
- Fixture SHA, Git head, arm configuration, budget, `top_k`, and runtime data.

Zero-supportable-requirement scenarios are `not_applicable`, not `100%`.

### Gated live-generation evaluation

After offline acceptance, compare paired baseline and FitCV generations using
the same profile, JD, model, template, generation settings, and output budget.
Report final-CV supported-requirement coverage, unsupported factual-claim rate,
first-pass acceptance, final acceptance, repair attempts, and provider-reported
usage or cost when available.

Offline token estimates do not support provider-cost claims.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `none`
- Required skills: `skill-writing-plans`, `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`
- Isolation: clean worktree from `origin/main` after PR #51 merge (`b234a00b`)
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed benchmark, test, script, and documentation files; run declared local checks; create task-owned `.tmp/` outputs
- User-approval actions: provider calls, credential use, external publication, push, merge, destructive cleanup, or changes to production retrieval defaults
- Parallel ownership: none
- Sequential fallback: fixture contract → benchmark arms → metrics/report → offline run → gated live evaluator → documentation and final verification

## Task Breakdown

### Task 1 — Make benchmark scenarios independent

**Files:**

- `tests/fixtures/requirement_support_benchmark.json`
- `scripts/benchmark_requirement_support.py`
- `tests/test_benchmark_requirement_support.py`

**Steps:**

1. Make each scenario resolve its own profile or profile reference, JD or JD
   reference, expected support map, evidence budget, and validation cases.
2. Preserve shared fixture data only through explicit references.
3. Reject duplicate IDs, missing scenario inputs, missing expected support, and
   validation cases without expected outcomes.
4. Execute each scenario once per arm instead of repeating one shared workload.

**Authority:**

- Preauthorized local actions: modify fixture validation, scenario loading, and focused tests only.
- Stop for: a fixture migration that changes production evidence contracts or requires undocumented ground truth.

**Proof:**

- A scenario JD mutation affects only that scenario.
- Executed workload count equals scenario count.
- No scenario falls back silently to shared top-level inputs.

**Exit criteria:** 12–16 independent scenarios execute per arm.

### Task 2 — Add explicit benchmark-only selection arms

**Files:**

- `scripts/benchmark_requirement_support.py`
- `tests/test_benchmark_requirement_support.py`
- `docs/pipeline.md`

**Steps:**

1. Add `lexical-baseline`, `lexical-ablation`,
   `lexical-requirement-aware`, and `current-hash` arm names.
2. Implement conventional lexical top-k with no requirement-coverage reward,
   stable evidence-ID tie-breaking, and the same evidence budget.
3. Keep ablation and FitCV arms on the same lexical retrieval channels.
4. Keep current configured hash behavior as a separate arm.
5. Preserve existing `--weight` compatibility where current tests require it.
6. Keep all adapters benchmark-only; do not change production defaults.

**Authority:**

- Preauthorized local actions: add benchmark adapters, CLI choices, and contract tests without touching production selection configuration.
- Stop for: any proposed production default, persisted schema, provider, or retrieval-channel change.

**Proof:**

- Identical inputs and budgets produce deterministic arm outputs.
- Conventional baseline never invokes requirement-coverage reward.
- Ablation and FitCV differ only by requirement-gain configuration.
- No provider calls occur.

**Exit criteria:** A/C, B/C, and C/D answer separate questions without one combined headline metric.

### Task 3 — Extend metrics and comparison report

**Files:**

- `scripts/benchmark_requirement_support.py`
- `scripts/compare_requirement_support.py`
- `tests/test_benchmark_requirement_support.py`
- `docs/pipeline.md`

**Steps:**

1. Emit per-scenario metrics and raw case matrices.
2. Add micro coverage, macro coverage, paired deltas, and min/max scenario
   deltas.
3. Keep requirement recall separate from evidence-pair recall.
4. Count unexpected requirement IDs as assignment errors.
5. Report precision only when an arm emits explicit links; otherwise emit
   `not_applicable`.
6. Reject fixture, scenario-set, budget, or schema mismatches before comparison.
7. Preserve historical comparison as supplementary engineering evidence.

**Authority:**

- Preauthorized local actions: change benchmark output schemas, comparison logic, tests, and documentation only.
- Stop for: a metric that relies on self-reported support instead of frozen approved links.

**Proof:**

- Tests cover zero denominators, unexpected IDs, missed pairs, incorrect pairs,
  empty selections, and non-link-emitting baselines.
- Comparison rejects incompatible inputs.

**Exit criteria:** Report distinguishes retrieval loss from selection loss and uses one fixture fingerprint for comparable arms.

### Task 4 — Run offline evaluation

**Files:** task-owned `.tmp/` outputs only.

**Commands:**

```powershell
uv run --extra local --extra inverse-optimization pytest -q tests/test_benchmark_requirement_support.py

uv run python scripts/benchmark_requirement_support.py --arm lexical-baseline --runs 50 --warmups 5 --output .tmp/impact-lexical-baseline.json
uv run python scripts/benchmark_requirement_support.py --arm lexical-ablation --runs 50 --warmups 5 --output .tmp/impact-lexical-ablation.json
uv run python scripts/benchmark_requirement_support.py --arm lexical-requirement-aware --runs 50 --warmups 5 --output .tmp/impact-fitcv.json
uv run python scripts/benchmark_requirement_support.py --arm current-hash --runs 50 --warmups 5 --output .tmp/impact-current-hash.json
uv run python scripts/compare_requirement_support.py --inputs .tmp/impact-lexical-baseline.json,.tmp/impact-lexical-ablation.json,.tmp/impact-fitcv.json,.tmp/impact-current-hash.json --output .tmp/fitcv-impact-report.json
```

**Authority:**

- Preauthorized local actions: run offline benchmark commands and write task-owned `.tmp/` reports.
- Stop for: provider access, credential requests, cost-bearing calls, or an offline result that violates comparability.

**Acceptance gate:** Proceed to live generation only if C improves selected supported-requirement coverage over A at fixed budget, evidence correctness does not materially regress, and B/C isolates a measurable requirement-gain contribution.

### Task 5 — Add gated live-generation evaluator

**Files:**

- `scripts/evaluate_requirement_support_live.py`
- `tests/test_evaluate_requirement_support_live.py`
- `docs/pipeline.md`

**Steps:**

1. Select 6–10 representative JDs from the frozen fixture.
2. Generate paired baseline and FitCV CVs with identical model and generation
   settings.
3. Capture provider usage from provider response metadata.
4. Separate selection effects from prompt, validator, and repair effects.
5. Add a structured independent-review rubric for represented requirements,
   supported claims, specificity, and unsupported claims.
6. Add dry-run mode that validates pairs without provider calls.
7. Fail closed when credentials or paired configuration are missing.

**Authority:**

- Preauthorized local actions: implement dry-run harness, schemas, and tests without live provider calls.
- Stop for: live generation until offline gate, credentials, cost ceiling, and evaluator approval are explicit.

**Proof:**

- Dry-run validates paired inputs and fingerprints.
- Missing credentials fail closed.
- Mismatched model or settings fail validation.

**Exit criteria:** Final-CV coverage and unsupported-claim rate are reported separately from offline selection metrics.

### Task 6 — Document decision and next optimization

**Files:** `docs/pipeline.md` and final task-owned reports.

**Steps:**

1. Document commands, schemas, arm meanings, denominators, and limitations.
2. Record offline and live results separately.
3. Select next action only from measured bottleneck:
   - selection tuning;
   - pool-size evaluation;
   - hash-scoring evaluation;
   - generation improvement;
   - semantic retrieval evaluation;
   - measured latency optimization.
4. Do not add GraphRAG or agentic follow-up retrieval without evidence.

**Authority:**

- Preauthorized local actions: update benchmark documentation and record measured outcomes.
- Stop for: claiming final-CV quality, provider economics, or retrieval optimization without required evidence.

## Verification

```powershell
uv run --extra local --extra inverse-optimization pytest -q tests/test_benchmark_requirement_support.py
uv run --extra local --extra inverse-optimization pytest -q
git diff --check
git status --short
```

Expected:

- Focused and full suites pass.
- Reports reject incompatible inputs.
- No production retrieval configuration changes.
- No provider calls occur during offline evaluation.
- Machine-specific reports remain under `.tmp/`.

Verification note: focused benchmark/live tests pass (`17 passed` after the
ranking-conflict regression). Frontend build passes, frontend/packaging tests
pass (`14 passed`), and the full suite passes (`2777 passed, 4 skipped`). The
50-run offline report uses fixture SHA-256
`c35c1d9027809e8cad204e048e1c7d89c304013b22e98e91bc9404e9e6923c3c` and shows
FitCV improving selected requirement recall over baseline and ablation by
`0.066667`, with evidence-pair recall improvement `0.0625`; hash scoring ties
FitCV. The live evaluator remains dry-run only because no provider adapter,
credential, cost ceiling, or independent reviewer approval is configured.

## Completion Criteria

- [x] 12–16 independent scenarios execute per arm.
- [x] Four arms use explicit, truthful names.
- [x] A/C reports product-level coverage impact.
- [x] B/C reports requirement-gain impact.
- [x] C/D reports hash-scoring impact separately.
- [x] Micro and macro coverage are reported.
- [x] Evidence correctness remains separate from coverage.
- [x] Retrieval, selection, and generation losses are distinguishable.
- [x] Comparable reports share one fixture fingerprint and evidence budget.
- [x] Historical comparison remains supplementary.
- [x] Live generation remains gated after offline approval; provider execution is deferred without adapter, credentials, cost ceiling, and reviewer approval.
- [x] Final-CV claims are not made from selected-evidence metrics alone.
- [x] No retrieval complexity is added without measured need.
