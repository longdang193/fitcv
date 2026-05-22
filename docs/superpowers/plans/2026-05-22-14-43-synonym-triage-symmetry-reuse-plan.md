---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: synonym-triage-symmetry-first-reuse-focused-scope
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
parent_spec: docs/superpowers/specs/2026-04-28-operator-control-plane-agentic-settings-surface-spec.md
targets:
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_app.py
  - artifacts/live_run_*/unzipped/synonym-proposals-trace.json
related_stages:
  - enrich
  - cv_analysis
---

## Goal

Raise synonym triage reuse from near-zero drift pattern to stable non-trivial reuse while keeping safety boundaries and making reuse semantics symmetric with enrich-style reuse principles.

## Key Deliverables

### Symmetry-first reuse contract for synonym triage

Introduce explicit two-level reuse contract for triage recommendations:
- strict fingerprint (existing full-safety key)
- core fingerprint (stable semantic key, resilient to non-meaningful proposal-set drift)

Reuse decision becomes deterministic and symmetric in both worker automation path and admin triage-refresh path:
- reuse when `strict_match || core_match`
- preserve strict-only invalidation for true semantic/runtime changes

### Focused-scope safety gates and observability

Add guardrails so core reuse cannot bypass semantic safety boundaries:
- candidate set compatibility gate
- status/conflict bundle compatibility gate
- runtime/config version compatibility gate

Expose split counters and reasons:
- `reused_strict_count`
- `reused_core_count`
- `fresh_count`
- trace reason labels for each decision path

### Regression and live-run proof for drift-resilient reuse

Lock behavior with tests and live-run artifact evidence so minor proposal-set drift no longer forces full recompute, while meaningful changes still recompute.

## Task/Wave Breakdown

### Task 1: Define symmetry-first triage reuse contract and invariants

**Purpose:**
- Codify minimal, safe, shared contract before implementation edits.

**Files:**
- Inspect: `src/fitcv_cp/synonym_proposals.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Verify: `artifacts/live_run_*/unzipped/synonym-proposals-trace.json`

**Preconditions:**
- Baseline evidence for near-zero triage reuse captured from recent runs.

**Steps:**
- [ ] Step 1: Enumerate current strict fingerprint payload fields and classify each as `semantic-critical` vs `drift-prone`.
- [ ] Step 2: Define core fingerprint field set with explicit exclusions for drift-prone fields.
- [ ] Step 3: Define reuse safety gates required for core-match acceptance.
- [ ] Step 4: Document final decision table (`strict`, `core+gates`, `fresh`).

**Verification:**
- [ ] Decision table reviewed against both worker and admin code paths with no path-specific rule divergence.

**Exit Criteria:**
- Reuse contract precise enough for direct coding without interpretation gaps.

### Task 2: Implement dual-fingerprint primitives in synonym proposal module

**Purpose:**
- Create SSOT helpers for strict/core fingerprint generation and match evaluation.

**Files:**
- Modify: `src/fitcv_cp/synonym_proposals.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 contract frozen.

**Steps:**
- [ ] Step 1: Keep existing strict fingerprint helper intact for backward compatibility.
- [ ] Step 2: Add core fingerprint helper with deterministic normalization/sorting.
- [ ] Step 3: Add reusable evaluator helper returning `strict_reuse`, `core_reuse`, or `fresh` with reason code.
- [ ] Step 4: Persist both fingerprint values in recommendation runtime payload.

**Verification:**
- [ ] Unit tests validate strict/core helper determinism across ordering noise and run-scoped identity drift.

**Exit Criteria:**
- Single module owns fingerprint semantics; no duplicated ad-hoc matching logic elsewhere.

### Task 3: Apply symmetric reuse decision in worker and admin paths

**Purpose:**
- Enforce same reuse logic across execution surfaces to prevent drift between paths.

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 2 primitives available.

**Steps:**
- [ ] Step 1: Replace direct strict-only equality checks with shared evaluator helper in worker path.
- [ ] Step 2: Replace triage-refresh path matching logic with same shared evaluator helper.
- [ ] Step 3: Align counters/trace fields so both paths emit same reuse taxonomy.
- [ ] Step 4: Preserve existing fallback behavior where no reusable record exists.

**Verification:**
- [ ] Worker and admin tests assert identical outcomes for identical synthetic payloads.

**Exit Criteria:**
- Symmetry achieved: same inputs produce same reuse classification independent of path.

### Task 4: Add focused safety-gate regression coverage

**Purpose:**
- Ensure core reuse increases hit rate without semantic leakage.

**Files:**
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 3 complete.

**Steps:**
- [ ] Step 1: Add positive test where strict mismatches but core+gates match, expecting `reused_core_count` increment.
- [ ] Step 2: Add negative tests where core matches but safety gate fails (candidate/status/runtime mismatch), expecting fresh recompute.
- [ ] Step 3: Add parity test asserting worker/admin counter totals and reason labels stay aligned.

**Verification:**
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py -k "synonym and triage and reuse"`
- [ ] `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "triage_refresh and reuse"`

**Exit Criteria:**
- Tests prove drift-resilient reuse and strict safety invalidation boundaries.

### Task 5: Live-run validation and acceptance threshold

**Purpose:**
- Validate behavior on real run artifacts, not test-only evidence.

**Files:**
- Verify: `artifacts/live_run_*/unzipped/synonym-proposals-trace.json`
- Verify: `artifacts/live_run_*/unzipped/enrich.json`
- Verify: `artifacts/live_run_*/unzipped/settings-used.json`

**Preconditions:**
- Tasks 1-4 merged into runnable build.

**Steps:**
- [ ] Step 1: Trigger two consecutive runs with minimal input drift and auto-promote global setting unchanged.
- [ ] Step 2: Confirm second run shows non-zero triage reuse through strict or core path.
- [ ] Step 3: Trigger one controlled semantic change run and confirm triage recompute remains active where expected.
- [ ] Step 4: Record before/after reuse ratios for auditability.

**Verification:**
- [ ] Live-run traces show `reused_strict_count + reused_core_count > 0` on stable rerun.
- [ ] Controlled semantic-change run increases `fresh_count` for affected proposals.

**Exit Criteria:**
- Focused-scope acceptance met: near-zero reuse pattern materially reduced without safety regression evidence.

## Verification

- `python -m pytest -q tests/test_fitcv_cp/test_worker_job.py -k "synonym and triage and reuse"`
- `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "triage_refresh and reuse"`
- `python -m pytest -q tests/test_fitcv_cp/test_app.py -k "synonym_proposal_action"`
- Two stable live reruns + one controlled-change run with artifact diff on `synonym-proposals-trace.json`

## Completion Criteria

1. Triage reuse decision uses shared strict/core contract in both worker and admin paths.
2. Safety gates prevent core reuse when semantic compatibility is broken.
3. Split counters and reason labels expose strict vs core reuse clearly in run artifacts.
4. Regression tests cover positive core-reuse and negative gate-fail recompute cases.
5. Live-run evidence shows measurable reuse improvement over prior near-zero baseline without incorrect promotion/triage behavior.
