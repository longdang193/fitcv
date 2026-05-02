---
layer: workstream
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
targets:
  - docs/intent/master-workstream-roadmap.md
  - docs/intent/workstreams/workstream-agentic-observability.md
  - docs/intent/workstreams/workstream-deterministic-acceptance-and-artifact-truth.md
  - docs/intent/workstreams/workstream-operator-control-plane.md
  - docs/observability.md
  - docs/architecture.md
  - docs/configuration.md
related_features:
  - inspection_debugging
  - trigger_run_management
  - settings_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Observability, Evidence, And Control Docs Alignment

## Summary

Align intent and cross-cutting docs around one reusable architecture model:

- observability as a standardized execution-trace layer
- evidence as a stage-owned truth envelope
- control as explicit policy gating and operator authority

This spec defines documentation updates only. It does not require runtime behavior changes in this wave.
This alignment is scoped as **Master Workstream Phase 2** (architecture hardening and portability after baseline feature delivery).

## Problem

Current docs provide strong run inspection surfaces, but they do not yet present one portable architecture contract that can be reused across FitCV and future projects.

## Goals

- define a reusable architecture contract for observability + evidence + control
- preserve FitCV runtime truth while making the model portable across future projects
- clarify boundaries:
  - orchestration responsibility
  - observability responsibility
  - evidence responsibility
  - policy/control responsibility
- document backend-agnostic design direction (BigQuery now, local DB later)

## Non-Goals

- no replacement of existing run-detail artifact routes
- no mandatory migration from BigQuery in this spec
- no UI redesign commitments
- no retroactive rewrite of archived specs/plans

## Bounded-Thread Execution Pass Checkpoint Contract

Treat each bounded-thread execution pass under this spec as a checkpoint.

- checkpoint unit = bounded change thread
- each meaningful execution pass emits one checkpoint result pack
- pack template = `docs/operating_system/templates/checkpoint-result-pack.md`
- canonical location = `docs/intent/workstreams/checkpoints/<workstream-id>/<thread-slug>/`
- verification must include `python scripts/validate_checkpoint_packs.py`

## Proposed Documentation Contract

## 0) One Source Of Truth Per Concern

Add this principle explicitly in updated docs:

- flow = orchestrator
- traces = OTel-compatible IDs
- decisions = policy layer
- evidence = stage artifacts
- operations = control plane UI

## 1) Canonical Stage Envelope (doc-level standard)

Document the portable contract:

`StageResult = { output, evidence, validation, decision, policy_version, trace_context }`

## 2) Layered Responsibility Model

1. orchestration layer (flow, retries, scheduling)
2. execution layer (deterministic and agentic stage logic)
3. evidence layer (stage-owned evidence payloads and fingerprints)
4. validation/policy layer (gates and decision authority)
5. observability layer (traces/events/diagnostics)
6. control-plane layer (inspect/replay/approve/audit)

## 3) Decision And Observability Separation

- observability captures what happened
- policy decides what is allowed next
- confidence signals are advisory and not acceptance authority

## 4) Portability Guidance

- domain code depends on storage/queue/artifact interfaces
- provider-specific implementations are adapters
- control-plane boot modes should be documented:
  - full
  - local
  - degraded

## 5) Failure-Evidence Expectations

Evidence snapshots should remain available for:

- succeeded runs
- failed runs
- cancelled runs

and degraded snapshot states must be explicit to operators.

## Execution Order (Roadmap-First)

This spec must be authored and executed in the following strict order:

1. master workstream roadmap
2. complete set of registered workstreams
3. bounded change threads
4. complete spec set
5. spec-authoring execution map
6. detailed specs
7. implementation execution map
8. implementation plans

## Targeted Doc Changes

## A) `docs/intent/master-workstream-roadmap.md`

- add explicit **Phase 2** section for architecture hardening/portability:
  - one source of truth per concern
  - OTel-compatible trace IDs
  - policy-versioned decision gates
  - backend decoupling narrative
  - failure/cancel evidence completeness
- add architecture-contract completion language:
  - stage envelope
  - policy-versioned decisions
  - trace-context continuity

## B) `docs/intent/workstreams/workstream-agentic-observability.md`

- tighten scope to execution tracing and provenance surfaces
- explicitly mark policy acceptance as out-of-scope ownership
- add cross-project portability note

## C) `docs/intent/workstreams/workstream-deterministic-acceptance-and-artifact-truth.md`

- anchor stage decision authority to `validation + decision + policy_version`
- clarify failure/cancel evidence expectations

## D) `docs/intent/workstreams/workstream-operator-control-plane.md`

- add control semantics for `manual_review`, replay visibility, and degraded evidence indicators
- clarify operator-facing difference between recommendation and acceptance

## E) `docs/observability.md`

- add architecture-contract section mapping current artifacts to canonical stage envelope
- add explicit guidance for trace vs decision interpretation
- add local/degraded mode observability expectations

## F) `docs/architecture.md` and `docs/configuration.md`

- add backend-agnostic adapter pattern guidance
- add runtime mode/config-key narratives for backend and capability selection

## Acceptance Criteria

1. Canonical stage envelope is documented once and referenced consistently.
2. Workstream ownership boundaries are explicit for observability vs policy control.
3. Portability guidance exists for BigQuery-now and local/Postgres-later modes.
4. Docs define degraded/failure evidence visibility expectations.
5. Docs follow roadmap-first sequencing and include spec/execution-map/plan completeness path.

## Validation

- `python scripts/validate_repo_contracts.py --fast`
- Manual consistency pass across all `targets` in this spec
