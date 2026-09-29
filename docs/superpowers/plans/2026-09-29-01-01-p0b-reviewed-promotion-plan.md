---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
contract_version: "1"
name: p0b-reviewed-promotion
targets:
  - scripts/compare_requirement_support.py
  - tests/test_compare_requirement_support.py
  - tests/test_p0_public_corpus.py
  - data/fitcv-p0-corpus/p0b
  - docs/superpowers/evidence/2026-09-29-p0b-reviewed-promotion.md
  - docs/superpowers/evidence/2026-09-29-p0b-comparison.json
---

# P0-B Reviewed Promotion

## Goal

Execute the approved two-lane preparation, benchmark hardening, independent
technical review, and evidence preservation. Promote only after human-reviewed
held-out evidence and acceptance-owner thresholds exist.

## Implementation Outcomes

- Source-backed cases prepared for two independent human reviewers without
  creating model-generated verdicts or treating agent review as human approval.
- Comparisons retain supplied arms and reject invalid measurement inputs.
- Fresh three-arm diagnostic reports and exact byte hashes retained in evidence.
- Human admission, held-out evaluation, and promotion remain blocked until
  their actual prerequisites are supplied; passing synthetic checks cannot close them.

## Execution Approach

- Mode: `parallel-capable`
- Coordination: `git-tracked`
- Inspection runs in parallel; implementation and integration are serialized.
  Sole lead owns canonical fixtures and ledger.
- Required skills: `skill-executing-plans`, `skill-dispatching-parallel-agents`,
  `skill-systematic-debugging`, `skill-test-driven-development`,
  `skill-verification-before-completion`.
- Isolation: current checkout; preserve unrelated `.tmp/` and `.venv/`.
- Commit policy: user authorizes commit and push to `main` of verified work.
- Parallel ownership: corpus agent reads immutable corpus; benchmark agent owns
  comparison script/tests only; lead owns documents and integration. No shared writes.
- User-approval actions: human label adjudication and numerical acceptance thresholds.
- Sequential fallback: inspect corpus, fix benchmark, review, verify, preserve.

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `251ee0a2a7c3dbfba1404f5e620bc6383df965cb`; includes the subsequent
  late-stage evidence merge. Earlier conversation commit `fe093c73` is historical.
- Expected workspace: existing checkout, unrelated untracked `.tmp/` and `.venv/`.
- Next action: preserve verified work by commit/push; obtain human adjudications,
  approved numerical thresholds, and untouched held-out admission before Task 4.
- Blockers: no two-human adjudications, no approved non-inferiority margin or
  latency/cost thresholds, no admitted held-out benchmark fixture.

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | completed | current | codex | none | source-backed review packet | six unlabelled proposals; corpus tests pass |
| Task 2 | completed | current | codex | none | failing then passing comparison tests | focused red/green proof in evidence |
| Task 3 | active | current | codex | Task 1, Task 2 | two technical reviews, fresh reports and hashes | reviews PASS; 45 tests pass; Git disposition pending |
| Task 4 | blocked | current | unresolved | Task 1, Task 3 | human adjudication and preregistered held-out gate | missing external inputs |

## Task Breakdown

### Task 1: Prepare Reviewable Corpus Work

**Purpose:** Identify source-backed cases and exact admission gaps.
**Task Function:** Corpus inspection and review preparation.
**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded source and provenance reasoning.
**Specification Coverage:** Boundary coverage, sources, splits, two human reviewers.
**Required Skills:** `skill-dispatching-parallel-agents`.
**Files And Symbols:** Inspect `data/fitcv-p0-corpus/p0b/*` and
`tests/test_p0_public_corpus.py`; lead writes review packet under the evidence path,
corrects the proven stale manifest count, and adds count regression assertions.
**Dependencies:** Existing public admitted sources only.
**Authority:**
- Preauthorized local actions: inspect sources and prepare unlabelled review work.
- Stop for: invented labels, human identities, approval, or new external source access.
**Steps:**
- [x] Audit sources, pair identities, label coverage and split leakage.
- [x] Save unlabelled review packet and exact missing boundary categories.
**Verification:**
- [x] Run `py -3.13 -m pytest -q tests/test_p0_public_corpus.py`.
**Exit Criteria:** Review work is concrete, source-backed, and explicitly unapproved.

### Task 2: Harden Benchmark Comparison

**Purpose:** Prevent misleading comparison results.
**Task Function:** Root-cause diagnosis and minimal regression fixes.
**Template Profile:**
- Controller-selected: `normal`
- Selection basis: bounded script/test contract.
**Specification Coverage:** Three-arm retention, metric validity and provenance.
**Required Skills:** `skill-systematic-debugging`, `skill-test-driven-development`.
**Files And Symbols:** `scripts/compare_requirement_support.py:run_inputs`,
its shared validators, `tests/test_compare_requirement_support.py`.
**Dependencies:** Existing benchmark producer schema and callers.
**Authority:**
- Preauthorized local actions: edit owned comparison/test files and run focused tests.
- Stop for: production behavior change, corpus edits, or invented acceptance thresholds.
**Steps:**
- [x] Reproduce dropped lexical arm and invalid-input acceptance.
- [x] Fix shared comparison owner while retaining supported legacy comparisons.
**Verification:**
- [x] Run `py -3.13 -m pytest -q tests/test_compare_requirement_support.py tests/test_benchmark_requirement_support.py`.
**Exit Criteria:** Malformed evidence fails closed; supplied comparison arms remain visible.

### Task 3: Integrate, Review, Measure and Preserve

**Purpose:** Preserve verified progress and honest remaining gates.
**Task Function:** Lead integration with two independent read-only technical reviews.
**Template Profile:**
- Controller-selected: `none (lead controller)`
- Selection basis: lead owns integration; independent reviewers are `review-1` and `review-2`.
**Specification Coverage:** Commands, metrics, hashes, regressions, promotion decision.
**Required Skills:** `skill-verification-before-completion`.
**Files And Symbols:** Evidence document, this plan, `.tmp/p0b-20260929-010143-*`.
**Dependencies:** Tasks 1 and 2 accepted.
**Authority:**
- Preauthorized local actions: tests, offline benchmarks, technical review, commit and normal push to main.
- Stop for: failed required checks, merge conflict, or promotion without human prerequisites.
**Steps:**
- [x] Review corpus/gates and benchmark/tests independently; patch justified issues.
- [x] Run all three arms with 50 measured runs and 5 warmups; compare fresh reports.
- [x] Record exact source/report hashes, Git state, findings, and verification.
- [ ] Commit and push verified work, preserving blocked task state.

Git disposition is pending at this pre-commit snapshot; the containing commit
and remote `main` ancestry provide its subsequent preservation proof.
**Verification:**
- [x] Run focused benchmark/corpus suites and `git diff --cached --check`.
**Exit Criteria:** Work is preserved with auditable evidence; partial progress is not marked full completion.

### Task 4: Admit Human Labels and Evaluate Promotion

**Purpose:** Establish genuine held-out production evidence.
**Task Function:** Human adjudication, admission, and final evaluation.
**Template Profile:**
- Controller-selected: `unresolved`
- Selection basis: human input required before executor selection.
**Specification Coverage:** All eight approved promotion conditions.
**Required Skills:** `skill-verification-before-completion`.
**Files And Symbols:** Reviewed P0-B rows/manifest and the future admitted executable fixture.
**Dependencies:** Two independent human reviews per case, resolved disagreements,
owner-approved recall margins, latency/cost limits, approved split and source-group policy.
**Authority:**
- Preauthorized local actions: preserve pending decisions and prepare reviewable inputs.
- Stop for: absent human approval, missing thresholds, held-out contamination or inferred labels.
**Steps:**
- [ ] Obtain human verdicts and approval of baseline, margins, and latency/cost limits before tuning.
- [ ] Lead admits approved cases, separates calibration/held-out source groups, and hashes exact fixture bytes.
- [ ] Wire admitted fixture through benchmark contract and prove split/provenance checks before final held-out run.
- [ ] Evaluate held-out qualified-requirement/evidence-pair recall, zero observed false-qualified pairs and qualifier leakage, coverage, provenance, and latency/cost.
**Verification:**
- [ ] Approved fixture and gate pass all declared criteria on fresh held-out output.
**Exit Criteria:** Every required human decision and measurement exists; zero observed errors is not a population guarantee.

## Verification

- Evidence: `docs/superpowers/evidence/2026-09-29-p0b-reviewed-promotion.md`
  records final 45-test pass, lead regression extensions, two reviews, hashes,
  and historical planning-validator failures outside this plan.
- Fresh focused tests, two independent technical reviews, three-arm diagnostics,
  byte hashes, and staged whitespace check establish implemented progress.
- Existing commands consume `tests/fixtures/requirement_support_benchmark.json`;
  their synthetic results do not establish P0-B held-out performance.

## Completion Criteria

All tasks must complete before this plan is marked completed. Verified preparation
and bug fixes may be committed while Task 4 remains blocked. Production defaults
remain unchanged until every approved promotion condition is met.
