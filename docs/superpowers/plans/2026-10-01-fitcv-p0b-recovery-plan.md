---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
name: fitcv-p0b-recovery
targets:
  - src/fitcv/evidence.py
  - scripts/evaluate_p0b_source_job_relevance.py
  - scripts/calibrate_p0b_recovery.py
  - tests/test_evidence.py
  - tests/test_p0b_source_job_relevance_evaluator.py
  - tests/test_calibrate_p0b_recovery.py
  - docs/superpowers/evidence/
  - config/acceptance_state.yaml
  - artifacts/acceptance_state.json
---

# FitCV P0-B Recovery

## Goal

Create a new, bounded P0-B recovery path. Preserve the protected Task 8 result, expose deterministic runtime stage traces, classify the existing 200 false negatives and 7 false positives against the sanitized oracle, fix one measured dominant cause at its owner layer, and run one new protected evaluation. Promote only on pair false positives `0` and support recall `1.0`.

## Implementation Outcomes

### Recovery trace contract

`retrieve_evidence_bundle` emits bounded, deterministic stage traces for canonical pool, candidate retrieval, verification, qualification, selection, and assignment. Existing selection and support behavior stays unchanged until calibration names one measured loss.

### Measured recovery

A calibration artifact classifies each judged protected pair exactly once, reports conservation totals and dominant loss, and records whether the loss is pool, retrieval, verification, qualification, selection, or assignment. One owner-layer fix ships only when calibration proves a dominant loss with a safe bounded change.

### New acceptance evidence

The protected Task 8 result remains immutable. A new evaluator output, recovery evidence record, and acceptance-state update are written only after clean tests and clean-checkout proof. Failed gates keep P0-B blocked.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-executing-plans`, `skill-backend-verification`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edits to listed targets, bounded local calibration, tests, clean-checkout proof, and local evidence generation
- User-approval actions: push, merge, publication, destructive cleanup, protected-result replacement, or threshold changes
- Parallel ownership: none
- Sequential fallback: complete tasks in listed order; stop on missing oracle provenance, unexpected protected-file changes, or scope expansion

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `e75cfa1d`
- Expected workspace: `main` clean except protected ignored/untracked local inputs listed in repository instructions
- Next action: none; recovery diagnostic and surface-alignment patch complete
- Blockers: P0-B acceptance gates remain failed (`200` false negatives, `7` pair false positives)

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `codex` | none | focused trace tests | `2026-10-01-fitcv-p0b-recovery.md` |
| Task 2 | `completed` | current | `codex` | Task 1 | calibration artifact, conservation clean, surface reconciliation | `2026-10-01-fitcv-p0b-recovery.md` |
| Task 3 | `completed` | current | `codex` | Task 2 | no-safe-optimization decision | `2026-10-01-fitcv-p0b-recovery.md` |
| Task 4 | `completed` | current | `codex` | Task 3 | clean export: 96 passed, 4 skipped | `2026-10-01-fitcv-p0b-recovery.md` |
| Task 5 | `completed` | current | `codex` | Task 4 | new public evaluator result, promotion false | `2026-10-01-fitcv-p0b-recovery.md` |

## Task Breakdown

### Task 1: Add bounded stage traces

**Purpose:** Expose enough runtime facts to classify losses without changing production decisions.
**Task Function:** Trace contract implementation.
**Template Profile:**
- Controller-selected: `codex`
- Selection basis: shared owner, moderate ambiguity, correctness-sensitive output contract.
**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller owns focused validation.
**Specification Coverage:** Canonical pool, candidate retrieval, verification, qualification, selection, assignment; deterministic and bounded output.
**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`
**Files And Symbols:**
- Inspect: `src/fitcv/evidence.py:retrieve_evidence_bundle`, `_EvidenceSelectionEngine.run`, `_build_retrieve_evidence_bundle_payload`
- Modify: same symbols only unless a narrow helper is required
- Verify: `tests/test_evidence.py`, `tests/test_p0b_source_job_relevance_evaluator.py`
**Dependencies:** Existing protected result and current bundle schema.
**Authority:**
- Preauthorized local actions: add read-only trace fields and focused tests without changing thresholds or protected artifacts
- Stop for: behavior change not covered by calibration, private-input access, or protected-result mutation
**Steps:**
- [x] Step 1: Add pair-set trace fields derived from existing canonical, merged, qualified, selected, and responsibility-assignment maps.
- [x] Step 2: Keep trace bounded to IDs and counts; preserve current selected output and ordering.
- [x] Step 3: Add deterministic schema assertions and compatibility tests.
**Verification:**
- [ ] `python -m pytest -q tests/test_evidence.py tests/test_p0b_source_job_relevance_evaluator.py`
- Expected: all focused tests pass; repeated bundle output has identical trace fields.
**Exit Criteria:** Trace contract exposes all six stages and does not alter current decisions.

### Task 2: Classify current failures by calibration

**Purpose:** Map the 200 false negatives and 7 false positives to one measured stage cause.
**Task Function:** Sanitized oracle calibration.
**Template Profile:**
- Controller-selected: `codex`
- Selection basis: deterministic data accounting and existing repository fixtures.
**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller validates conservation and provenance.
**Specification Coverage:** Full-pool oracle truth; disjoint/exhaustive stage classification; calibration only.
**Required Skills:** `skill-backend-verification`
**Files And Symbols:**
- Inspect: `scripts/evaluate_p0b_source_job_relevance.py:evaluate_actual_fitcv`, `src/fitcv/evidence.py:retrieve_evidence_bundle`
- Modify: `scripts/calibrate_p0b_recovery.py`, calibration tests
- Verify: sanitized projection, review, oracle, and current acceptance state
**Dependencies:** Task 1.
**Authority:**
- Preauthorized local actions: read sanitized tracked corpus and write `.tmp`/evidence calibration outputs
- Stop for: missing independent oracle labels, unjudged pairs, or any attempt to rerun/overwrite protected Task 8 output
**Steps:**
- [x] Step 1: Run current pipeline on sanitized source-job rows and persist stage traces.
- [x] Step 2: Compare judged oracle pairs against traces with precedence `not_in_canonical_pool`, `retrieval_loss`, `verification_failure`, `qualification_failure`, `selection_loss`, `assignment_loss`, `supported_through_pipeline`, `unsupported_selected`, `unsupported_not_selected`, `unjudged`.
- [x] Step 3: Assert each judged pair is classified once and totals reconcile to oracle counts; protected aggregate reconciliation remains blocked (`205/1` versus `200/7`).
**Verification:**
- [ ] `python scripts/calibrate_p0b_recovery.py --output .tmp/p0b-recovery-calibration.json`
- Expected: `0` validation errors, complete conservation, dominant loss named or explicit `none`.
**Exit Criteria:** One immutable calibration artifact separates protected review-surface metrics from live runtime diagnostics and records no safe optimization.

### Task 3: Fix one measured dominant cause

**Purpose:** Recover only the dominant calibrated loss with smallest owner-layer change.
**Task Function:** Root-cause correction.
**Template Profile:**
- Controller-selected: `codex`
- Selection basis: owner-layer patch selected from Task 2 evidence, no speculative architecture.
**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused regression and calibration comparison.
**Specification Coverage:** One measured recovery; no embeddings, rerankers, LLM verifier, graph, service, datastore, or global `top_k` expansion.
**Required Skills:** `skill-backend-verification`, `skill-test-driven-development`
**Files And Symbols:** Task 2 named owner only; corresponding focused tests.
**Dependencies:** Task 2.
**Authority:**
- Preauthorized local actions: one bounded owner-layer code change and its regression test
- Stop for: more than one dominant cause, no measurable improvement, any false-positive increase, or need for threshold/input changes
**Steps:**
- [x] Step 1: Test one bounded strict-support recovery at retrieval owner.
- [x] Step 2: Re-run calibration on identical inputs and compare counts.
- [x] Step 3: Remove experiment because support false negatives did not improve and selection loss increased.
**Verification:**
- [ ] Same calibration command as Task 2 plus focused owner tests.
- Expected: dominant loss decreases; no new unsupported selected pairs; trace conservation remains clean.
**Exit Criteria:** One measured fix ships, or Task 3 records no-safe-optimization and leaves P0-B blocked.

### Task 4: Verify clean checkout

**Purpose:** Prove recovery is reproducible without private or ignored inputs.
**Task Function:** Reproducibility verification.
**Template Profile:**
- Controller-selected: `codex`
- Selection basis: repository-owned clean-checkout proof.
**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller owns final checks.
**Specification Coverage:** Public sanitized corpus, tests, trace contract, calibration artifact.
**Required Skills:** `skill-verification-before-completion`
**Files And Symbols:** Clean exported tree or detached worktree; no private local inputs.
**Dependencies:** Task 3.
**Authority:**
- Preauthorized local actions: create disposable clean checkout/export and run repository tests
- Stop for: private input dependency, untracked protected-file mutation, or failing required test
**Steps:**
- [x] Step 1: Run focused tests in clean export.
- [x] Step 2: Run public corpus and calibration validation from tracked inputs.
- [x] Step 3: Record exact commands and results in recovery evidence.
**Verification:**
- [ ] Focused suite, public corpus suite, and `git diff --check`.
- Expected: clean checkout passes; no private paths appear in outputs.
**Exit Criteria:** Recovery code and calibration are reproducible from tracked sanitized inputs.

### Task 5: Run one new protected evaluation

**Purpose:** Freeze new behavior and measure P0-B without touching old protected evidence.
**Task Function:** Protected acceptance evaluation.
**Template Profile:**
- Controller-selected: `codex`
- Selection basis: acceptance authority and evidence reconciliation.
**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller performs final gate checks.
**Specification Coverage:** Pair false positives `0`, support recall `1.0`, explicit blocked status otherwise.
**Required Skills:** `skill-backend-verification`, `skill-verification-before-completion`
**Files And Symbols:** New `.tmp` result, recovery evidence, `config/acceptance_state.yaml`, rendered acceptance state.
**Dependencies:** Task 4.
**Authority:**
- Preauthorized local actions: one new protected evaluator run and evidence/state updates
- Stop for: any request to overwrite old protected result, alter thresholds, or publish/push
**Steps:**
- [x] Step 1: Freeze recovery inputs and record code/input hashes.
- [x] Step 2: Run exactly one new protected evaluator output.
- [x] Step 3: Keep `p0_b: blocked`; gates remain false.
**Verification:**
- [ ] Validate new result, evidence links, acceptance-state schema, and generated state.
- Expected: old Task 8 JSON unchanged; new result and status agree.
**Exit Criteria:** New P0-B status is reproducible and accurately recorded; P1-C and P2 remain deferred.

## Verification

- `python -m pytest -q tests/test_evidence.py tests/test_p0b_source_job_relevance_evaluator.py tests/test_calibrate_p0b_recovery.py tests/test_p0_public_corpus.py tests/test_acceptance_state.py`
- `python scripts/calibrate_p0b_recovery.py --output .tmp/p0b-recovery-calibration.json`
- Clean-checkout focused suite and `git diff --check`
- Validate old protected result hash and new recovery evidence/state consistency

## Completion Criteria

1. Stage traces are bounded, deterministic, and behavior-preserving.
2. Every judged oracle pair is classified exactly once with conservation proof.
3. No-safe-optimization is recorded after protected/runtime surface reconciliation.
4. Clean-checkout proof passes without private inputs.
5. One new public evaluator result exists; old Task 8 result remains unchanged.
6. Promotion remains blocked until gates reach pair false positives `0` and support recall `1.0`.
7. P1-C and P2 stay deferred.
