---
layer: workstream
artifact_type: plan
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-policy-versioned-stage-result-envelope
parent_spec: docs/superpowers/specs/2026-05-02-phase-2-policy-versioned-stage-result-spec.md
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/validator.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - docs/observability.md
  - docs/usage.md
related_features:
  - trigger_run_management
  - inspection_debugging
related_stages:
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 2 Plan G Replay Modes And Policy Registry

**Goal:** Add policy-evolution-safe replay behavior:

- `strict` replay
- `policy_replay`

and bind decisions to explicit policy registry versions.

## Scope

- introduce replay mode contract and run-level replay metadata
- enforce policy-version linkage in replay decisions
- expose replay mode and policy provenance in operator artifacts

## Non-Goals

- storage backend migration
- full policy engine replacement (OPA deferred)

## Execution-Pass Checkpoint Requirement

Each bounded-thread execution pass in this plan must publish one checkpoint result pack.

Required:

- create/update one pack per meaningful execution pass
- store pack at `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- follow `docs/operating_system/templates/checkpoint-result-pack.md`
- mark status as `pass`, `partial`, or `fail`
- include intent, actions, visible output, and next decision

## Tasks

## Task 1: Replay Mode Contract
- [ ] Add replay mode enum/contract (`strict`, `policy_replay`) to pipeline/control-plane runtime paths.
- [ ] Persist replay mode and replay source refs in run snapshots.

## Task 2: Policy Registry Linkage
- [ ] Introduce policy registry identifier/version surface used by validators/gates.
- [ ] Ensure all replayed stage decisions record policy version used at replay time.

## Task 3: Behavior Rules
- [ ] `strict`: require same config/policy envelope compatibility checks.
- [ ] `policy_replay`: allow new policy evaluation over historical inputs with explicit mode labeling.

## Task 4: Operator Surface + Tests
- [ ] Show replay mode and policy provenance in run detail/exports.
- [ ] Add tests for strict mismatch handling and policy_replay acceptance path.

## Verification

```powershell
python -m pytest tests/test_pipeline.py
python -m pytest tests/test_fitcv_cp/test_app.py
python scripts/validate_repo_contracts.py --fast
python scripts/validate_checkpoint_packs.py
```

## Exit Criteria

1. Replay mode is explicit and persisted.
2. Policy version is explicit for replay decisions.
3. Strict vs policy_replay behavior is test-covered and operator-visible.
