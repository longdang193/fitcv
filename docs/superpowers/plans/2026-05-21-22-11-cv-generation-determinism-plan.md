---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: cv-generation-determinism-and-reason-taxonomy
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
parent_spec: docs/superpowers/specs/2026-05-21-18-52-stage-reuse-toggle-symmetry-default-on-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - tests/
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Eliminate non-deterministic terminal status drift for non-reused CV generation outcomes (`review_required` vs `validation_failed`) and remove ambiguous reason-code outputs (`unknown`) by enforcing a canonical deterministic decision/reason mapping layer with audit-grade observability.

## Key Deliverables

### Deterministic CV Generation Verdict Contract

A single canonical verdict resolver determines terminal statuses from normalized validation/policy/review evidence, so identical normalized evidence always produces identical terminal status and reason code.

### Reason Taxonomy Completeness

All review-required and validation-failed outcomes map to explicit, non-ambiguous reason codes. `unknown` is removed from active runtime paths and only allowed as migration fallback for historical records.

### Determinism Evidence Surfaces

Run artifacts include explicit evidence fingerprints for decision inputs and validation evidence. Timeline/debug payloads expose these values to prove whether divergence came from evidence drift or classifier drift.

### Regression Verification Coverage

Automated tests cover deterministic verdict mapping and repeated replay scenarios on frozen stage inputs.

## Task/Wave Breakdown

### Task 1: Formalize Root-Cause Contract And Decision Inputs

**Purpose:**
- Freeze exact decision boundary where status drift occurs and define canonical evidence model for deterministic verdicting.

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `docs/superpowers/specs/` (if spec delta needed)
- Verify: `docs/superpowers/plans/2026-05-21-22-11-cv-generation-determinism-plan.md`

**Preconditions:**
- GitNexus index refreshed (`npx gitnexus analyze` completed).
- Root-cause evidence already reproduced across five manual-staged runs.

**Steps:**
- [ ] Step 1: Document current branch points for `validation_failed`, markdown review-gate, policy gate, and agentic review-gate transitions.
- [ ] Step 2: Enumerate normalized evidence fields consumed by each branch and consolidate to one canonical input schema.
- [ ] Step 3: Define canonical precedence order for terminal verdicts and reason-code assignment.

**Verification:**
- [ ] Source trace references collected for every terminal branch in `pipeline.py`.
- [ ] Canonical input schema and precedence approved in plan/spec notes.

**Exit Criteria:**
- Deterministic verdict contract is explicit, complete, and implementation-ready.

### Task 2: Implement Canonical Verdict + Reason Mapper

**Purpose:**
- Replace branch-local status/reason derivation with one deterministic resolver.

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `src/fitcv/pipeline.py`

**Preconditions:**
- Task 1 canonical precedence complete.

**Steps:**
- [ ] Step 1: Add resolver function (for example `resolve_cv_terminal_verdict(...)`) returning both `status` and `reason_code`.
- [ ] Step 2: Route all late-stage branches through resolver before persisting debug records or emitting terminal events.
- [ ] Step 3: Add explicit mapping for `review_gate` and other currently uncategorized branches to stable reason codes.
- [ ] Step 4: Keep backward-compatible parsing for old records but prevent new `unknown` reason creation.

**Verification:**
- [ ] Grep check confirms no new runtime path writes `review_required_reason_code: unknown`.
- [ ] Manual static review confirms all terminal emits use canonical resolver output.

**Exit Criteria:**
- All terminal-status emissions derive from single canonical resolver.

### Task 3: Add Determinism Fingerprints And Runtime Guardrails

**Purpose:**
- Provide machine-verifiable proof when two runs diverge.

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`

**Preconditions:**
- Task 2 canonical resolver integrated.

**Steps:**
- [ ] Step 1: Compute and persist `validation_evidence_fingerprint` from normalized validation/policy/review evidence used by resolver.
- [ ] Step 2: Emit fingerprint in debug payload and timeline event payload snapshots.
- [ ] Step 3: Add runtime warning event (`determinism_violation`) when same `cv_generation_input_fingerprint` + same `validation_evidence_fingerprint` produce different terminal verdicts across runs.
- [ ] Step 4: Ensure `/runs/{run_id}` includes necessary artifact fields for external diff tooling.

**Verification:**
- [ ] Live-run event payload inspection shows both input and evidence fingerprints.
- [ ] Guardrail event schema validated on synthetic mismatch test.

**Exit Criteria:**
- Divergence can be classified instantly as evidence drift vs mapping drift.

### Task 4: Determinism Regression Tests (Frozen Input Replay)

**Purpose:**
- Prevent regressions and confirm deterministic classification for identical normalized evidence.

**Files:**
- Inspect: `tests/`
- Modify: `tests/` (new/updated deterministic replay tests)
- Verify: `tests/`

**Preconditions:**
- Tasks 2 and 3 complete.

**Steps:**
- [ ] Step 1: Build fixture capturing frozen cv-analysis outputs and normalized validation evidence snapshots.
- [ ] Step 2: Add test asserting canonical resolver returns stable verdict and reason code for identical evidence across repeated invocations.
- [ ] Step 3: Add integration-style replay test asserting stable per-job status across multiple runs when evidence payload is held constant.
- [ ] Step 4: Add negative test ensuring `unknown` reason code is not generated by current runtime paths.

**Verification:**
- [ ] Targeted deterministic test module passes.
- [ ] Full validator subset passes (`scripts/hooks/run_validator.py --fast`).

**Exit Criteria:**
- Test suite fails if deterministic status mapping regresses.

### Task 5: Timeline And Operator UX Consistency

**Purpose:**
- Align human-facing status messages with deterministic backend verdicts and reason taxonomy.

**Files:**
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/templates/`

**Preconditions:**
- Canonical reason taxonomy finalized in Task 2.

**Steps:**
- [ ] Step 1: Update timeline summary formatting so review-required rows surface canonical reason labels.
- [ ] Step 2: Ensure validation-failed rows consistently show deterministic rejection reason class.
- [ ] Step 3: Keep de-duplication logic intact for reuse-only informational rows.

**Verification:**
- [ ] Manual UI inspection on new runs shows no ambiguous `unknown` reason in timeline/review queue context.

**Exit Criteria:**
- Operator sees consistent reason labels matching backend deterministic mapper.

## Verification

- `python -m py_compile src/fitcv/pipeline.py src/fitcv_cp/worker_job.py src/fitcv_cp/app.py`
- `python scripts/hooks/run_validator.py --fast`
- Determinism replay check: run manual-staged scenario multiple times and diff per-job `(status, reason_code, cv_generation_input_fingerprint, validation_evidence_fingerprint)`
- Confirm zero newly generated `unknown` reason codes in fresh runs.

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. repeated identical-evidence replay no longer alternates between `review_required` and `validation_failed`
5. runtime produces explicit non-ambiguous reason codes for all terminal branches
