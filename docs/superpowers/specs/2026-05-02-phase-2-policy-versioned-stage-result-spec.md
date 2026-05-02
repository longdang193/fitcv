---
layer: workstream
artifact_type: spec
status: proposed
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-policy-versioned-stage-result-envelope
targets:
  - docs/intent/workstreams/workstream-deterministic-acceptance-and-artifact-truth.md
  - docs/observability.md
  - docs/architecture.md
related_features:
  - inspection_debugging
  - trigger_run_management
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Phase 2 Policy-Versioned Stage Result Envelope

## Summary

Define and align the canonical stage-result decision/evidence contract:

`StageResult = { output, evidence, validation, decision, policy_version, trace_context }`

## Scope

- document decision authority as policy-layer owned
- document evidence ownership as stage-artifact owned
- include failed/cancelled evidence expectations in contract narratives

## Non-Goals

- no immediate code migration requirement
- no redesign of run export surface shape

## Bounded-Thread Execution Pass Checkpoint Contract

Treat each bounded-thread execution pass under this spec as a checkpoint.

- checkpoint unit = bounded change thread
- each meaningful execution pass emits one checkpoint result pack
- pack template = `docs/operating_system/templates/checkpoint-result-pack.md`
- canonical location = `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- verification must include `python scripts/validate_checkpoint_packs.py`

## Acceptance Criteria

1. Canonical `StageResult` envelope appears once as the doc-level default contract.
2. Deterministic acceptance docs explicitly anchor decision authority to `policy_version`.
3. Failure/cancel evidence expectations are documented alongside success.
