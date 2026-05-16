---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: option-b-review-required-dual-gate
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-agentic-gate-integration
parent_spec: docs/superpowers/specs/2026-05-16-12-55-option-b-review-required-dual-gate-spec.md
targets:
  - config/env.yaml
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/config.py
  - tests/test_config.py
  - tests/test_fitcv_cp/
  - docs/configuration.md
  - docs/superpowers/execution_context_packs/config-ssot-option-b/latest.md
related_features: []
related_stages:
  - cv_analysis
  - cv_generation
---

## Goal

Implement Option B dual-gate acceptance strictness so weak-match `stretch` rows route to `review_required` (HITL) instead of auto-accept, while preserving runtime success path and artifact contract compatibility.

## Key Deliverables

### Central policy-config implementation

Canonical acceptance strictness policy fields are implemented and loaded from `config/env.yaml` through existing config resolution, with deterministic defaults and compatibility-safe projection.

### Dual-gate outcome enforcement

`cv_analysis` emits normalized required-match metrics, and `cv_generation` applies deterministic policy gate to produce `accepted` or `review_required` with explicit policy reason codes.

### Compatibility-safe diagnostics and proof

Stage artifacts/events include additive policy diagnostics, existing consumer-facing fields remain intact, and targeted tests + live-run verification prove stricter acceptance behavior without runtime breakdown.

## Task/Wave Breakdown

### Task 1: Implement central acceptance policy fields and loader projection

**Purpose:**
- create SSOT-config policy surface for Option B and make it available to runtime consumers

**Files:**
- Inspect: `config/env.yaml`
- Inspect: `src/fitcv/config.py`
- Modify: `config/env.yaml`
- Modify: `src/fitcv/config.py`
- Verify: `tests/test_config.py`

**Preconditions:**
- approved spec `docs/superpowers/specs/2026-05-16-12-55-option-b-review-required-dual-gate-spec.md`
- existing config-ssot lane context active

**Steps:**
- [x] Step 1: Add canonical acceptance policy block to `config/env.yaml` with fit-class-aware fields for required-match strictness.
- [x] Step 2: Extend config load/projection logic to expose policy fields deterministically (including compatibility behavior where needed).
- [x] Step 3: Add/update config tests to prove canonical policy resolution and stable projection semantics.

**Verification:**
- [x] `pytest tests/test_config.py -q`

**Exit Criteria:**
- policy fields load from canonical config and tests prove deterministic projection behavior.

### Task 2: Implement dual-gate metrics + policy downgrade path

**Purpose:**
- enforce Option B decision contract across `cv_analysis` and `cv_generation`

**Files:**
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/pipeline.py`
- Verify: `tests/test_fitcv_cp/`

**Preconditions:**
- Task 1 complete
- current acceptance/review/failure status ownership understood from source

**Steps:**
- [x] Step 1: Normalize and persist required-match metrics in `cv_analysis` output contract for downstream use.
- [x] Step 2: Implement final acceptance policy check in `cv_generation` using normalized metrics + config policy.
- [x] Step 3: Route policy failures to `review_required` (non-fatal HITL) with deterministic reason code; preserve hard-failure statuses for true failures.
- [x] Step 4: Ensure pipeline aggregation/summary logic treats policy downgrade distinctly from validation/generation/persistence failures.

**Verification:**
- [x] Run targeted tests covering accepted/review/failure status mapping in `tests/test_fitcv_cp/`.

**Exit Criteria:**
- weak-match policy-failing rows deterministically downgrade to `review_required` with reason code; passing rows retain `accepted` path.

### Task 3: Additive artifact diagnostics and consumer compatibility safeguards

**Purpose:**
- expose policy decision transparency without breaking existing artifact consumers

**Files:**
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv_cp/app.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/app.py` (only if required for display/label wiring)
- Verify: `tests/test_fitcv_cp/test_run_detail_output_availability.py`

**Preconditions:**
- Task 2 complete
- existing artifact and run-detail field expectations identified

**Steps:**
- [x] Step 1: Add additive policy-diagnostic fields/reason codes to stage artifacts/events where Option B decisions occur.
- [x] Step 2: Preserve current keys and semantics expected by run detail and existing consumers.
- [x] Step 3: Add/update tests that assert compatibility and presence of new additive diagnostics.

**Verification:**
- [x] `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -q`

**Exit Criteria:**
- diagnostics visible and test-covered; no contract-breaking key removal/rename.

### Task 4: Live-run verification and context-pack/doc sync

**Purpose:**
- prove end-to-end behavior shift from permissive acceptance to policy-governed review path and sync source-of-truth docs

**Files:**
- Inspect: `docs/configuration.md`
- Modify: `docs/configuration.md`
- Modify: `docs/superpowers/execution_context_packs/config-ssot-option-b/latest.md`
- Verify: `tmp/live_run_artifacts/` (new run bundle)

**Preconditions:**
- Tasks 1-3 complete
- local service reachable for live run trigger and artifact retrieval

**Steps:**
- [x] Step 1: Trigger live run with same baseline-style inputs (`jobs_path=data/sample_jobs.json`, `config_path=config/env.yaml`).
- [x] Step 2: Retrieve run/event/cv-debug/stage artifacts and compare accepted vs review-required split against prior baseline run evidence.
- [x] Step 3: Update `docs/configuration.md` with final policy field semantics and `review_required` meaning.
- [x] Step 4: Update execution context pack with implementation/verification evidence and next-action state.

**Verification:**
- [x] Live run reaches expected terminal semantics for Option B (`succeeded` when no review queue; `awaiting_continue` when `review_required` queue exists).
- [x] Artifact evidence shows policy downgrade behavior for weak-match `stretch` rows.
- [x] `python scripts/validate_checkpoint_packs.py`
- [x] `python scripts/validate_repo_contracts.py --fast`

**Execution Note (2026-05-16):**
- Restart + cleanup rebuild completed in worktree runtime.
- Latest confirmed run IDs: `18802f14-adc1-4b1b-9962-f54b3ff0ab4b`, `c6bbe5b2-b6f2-4d3c-87bd-a9d3f53f2911`.
- Both runs `succeeded`, but still show `review_required=0`.
- Retrieved artifact evidence shows `settings-used.json` has no `cv_acceptance_policy`, and events/stage artifacts contain no `policy_acceptance`/policy reason entries.
- Next execution action remains runtime-config composition trace to restore policy field propagation.
- Follow-up execution restored `cv_acceptance_policy` in `config/env.yaml`, added runtime policy gate in `src/fitcv/pipeline.py`, and verified live run `4407d729-358b-4dfd-9d75-89864bb9d0ca` transitions to `awaiting_continue` with `review_required=2` and `reason_counts.policy_acceptance=2`.
- Closeout strict gate attempt: `python scripts/validate_planning_lifecycle.py --strict` fails on repo-wide existing manual thread-linkage warning set outside this lane scope.

**Exit Criteria:**
- Option B behavior proven with artifact evidence; context and docs synchronized.

## Verification

- `pytest tests/test_config.py -q`
- `pytest tests/test_fitcv_cp/test_run_detail_output_availability.py -q`
- targeted `pytest tests/test_fitcv_cp/ -q` for updated status/diagnostic expectations
- `python scripts/generate_planning_lineage.py`
- `python scripts/hooks/run_validator.py --fast`
- `python scripts/validate_checkpoint_packs.py`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>


