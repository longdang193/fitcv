---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-event-contract
targets:
  - docs/intent/workstreams/threads/workstream-agentic-observability/01-agentic-observability-event-contract.md
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv_cp/app.py
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_analysis
  - cv_generation
---

# Agentic Observability Event Contract

## Summary

Define the bounded event-record contract for agentic late-stage seams so
invocation facts, stage-owned outcomes, snapshots, confidence, fallback, and
provenance can be emitted consistently without making the UI or export layer
guess what happened.

This spec depends on the semantic-spine stage-authority contract and the
deterministic truth outcome contract. It treats event records as observational
surfaces that must derive from those upstream meanings rather than inventing
parallel status language.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- this is a Wave 3 detailed spec from the approved first-wave authoring map
- it is bounded to observability design, not implementation planning yet
- it is stage-heavy because the event contract must preserve stage-owned truth

Invariants:

- event records are derived from stage-owned runtime truth
- deterministic outcomes and stage-owned subreasons remain inspectable
- event payloads stay bounded and operator-useful rather than row-exhaustive
- observability starts from machine-stable event contracts, not from UI copy

Dependencies:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/intent/workstreams/threads/workstream-agentic-observability/01-agentic-observability-event-contract.md`
- `src/fitcv/pipeline.py`
- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv_cp/app.py`

Primary lens: `stage`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread-to-spec lineage from
`parent_thread`.

Plan needed: `no` until the Wave 3 spec trio is complete and approved.

## Problem

The current runtime already emits useful diagnostics:

- stage transition artifacts
- pipeline run events
- decision-chain summaries
- analysis input fingerprints and reuse status
- evidence-selection summaries
- prompt provenance
- control-plane timeline messages

But those signals are still spread across several payload families, with no
single bounded contract for what one agentic event record must contain. Without
that contract, later work risks:

- flattening stage-owned outcomes into vague "success" or "failure" messages
- duplicating analysis artifacts inside event logs
- making timeline UI and export consumers infer meaning from ad hoc fields

## Goals

- define a canonical event record shape for agentic seams
- preserve stage-owned subreason and deterministic outcome together
- separate event facts from larger artifact payloads
- make operator timeline, diagnostics exports, and later review tools rely on
  the same bounded event surface

## Non-Goals

- no redesign of full stage artifact schemas in this spec
- no UI implementation details beyond what the contract must support
- no requirement that every raw micro-step become its own stored event

## Event Scope

This spec focuses on agentic late-stage seams, especially:

- `cv_analysis`
- `cv_generation`
- future review-first agentic flows that will need the same contract style

It does not require the entire pipeline to adopt the exact same event payload
shape immediately.

## Proposed Contract

## 1. Event Families

The contract should distinguish between a small number of event families.

### Invocation events

Purpose:

- record that an agentic stage or bounded agentic action was attempted

Examples:

- `cv_analysis_invoked`
- `cv_generation_invoked`

### Decision events

Purpose:

- record a stage-owned late-stage decision in bounded, inspectable form

Examples:

- `cv_analysis_decision`
- `cv_generation_decision`

### Fallback events

Purpose:

- record that a bounded fallback or guardrail path was used instead of the
  preferred path

Examples:

- analysis reuse miss followed by fresh compute
- evidence-bundle empty result followed by narrower retrieval fallback

### Provenance events

Purpose:

- record prompt, model, fingerprint, and runtime provenance that materially
  explains the agentic action without duplicating full artifacts

Examples:

- prompt id or template path used for generation
- analysis input fingerprint and reuse status

## 2. Canonical Event Record Fields

Every persisted agentic event record should be able to expose:

- `event_name`
- `event_family`
- `source_stage`
- `run_id`
- `job_url` when job-scoped
- `deterministic_outcome` when the event reports a late-stage decision
- `stage_owned_subreason`
- `event_status`
- `confidence` when an agentic score or decision confidence is meaningful
- `fallback_used`
- `provenance`
- `input_snapshot`
- `output_snapshot`
- `artifact_refs`

Rules:

- `deterministic_outcome` must come from the deterministic outcome contract
- `stage_owned_subreason` must keep the more precise runtime status
- `input_snapshot` and `output_snapshot` must be bounded summaries, not whole
  artifacts pasted inline

## 3. Stage-Specific Requirements

### `cv_analysis`

Event records should preserve:

- ranking fit label used as upstream truth
- analysis input fingerprint
- analysis reuse status
- bounded evidence-selection summary
- stage-owned outcome:
  - `blocked_by_reranker_fit`
  - `ready_for_generation`
  - `skipped_fit_gate`
  - `analysis_failed`

Mapping rule:

- if the event describes the final stage-owned decision, include both:
  - `stage_owned_subreason`
  - `deterministic_outcome` where one exists

### `cv_generation`

Event records should preserve:

- prompt provenance
- bounded evidence or validation context references
- stage-owned outcome:
  - `accepted`
  - `validation_failed`
  - `generation_failed`
  - `persistence_failed`

Mapping rule:

- accepted and rejected paths must remain distinguishable without reading the
  larger stage artifact

## 4. Confidence Contract

`confidence` should only be present when the runtime owns a meaningful
confidence-like signal.

Allowed uses:

- bounded suggestion confidence
- future review proposal confidence

Not allowed:

- made-up confidence fields for deterministic rule outcomes
- UI-only severity numbers pretending to be model confidence

## 5. Fallback Contract

`fallback_used` should answer:

- did the preferred path fail, miss, or intentionally defer?
- what bounded fallback path took over?

Examples:

- evidence-bundle selection produced no final evidence, so narrower retrieval
  fallback was used
- exact-match reuse was unavailable, so fresh compute ran

Rule:

- fallback must describe operational path selection, not replace the stage-owned
  outcome

## 6. Snapshot Boundaries

The event contract should use bounded snapshots.

### `input_snapshot`

May include:

- small job identity fields
- stage-owned upstream labels
- bounded counts
- selected settings or prompt ids

Must not include:

- full job payloads
- full evidence corpora
- full CV markdown bodies

### `output_snapshot`

May include:

- selected-evidence counts
- resulting status
- bounded metrics
- artifact ids or refs

Must not include:

- full downstream artifacts already available elsewhere

## 7. Relationship To Stage Artifacts And Timeline UI

The event contract is not a replacement for stage artifacts.

Roles:

- event record = bounded change log fact
- stage artifact = fuller stage-owned diagnostic and export surface
- timeline UI = presentation layer that reads event facts and optional artifact
  summaries

Coordination rule:

- the timeline UI should summarize event facts and link to stage artifacts when
  deeper inspection is needed
- it should not reconstruct stage truth solely from human-readable messages

## Acceptance Criteria

- a reviewer can inspect one bounded agentic event record and tell:
  - which stage emitted it
  - what deterministic outcome it implies, if any
  - what precise stage-owned subreason it preserves
  - whether fallback or reuse was involved
  - what artifact or provenance context explains it
- event payloads remain bounded instead of duplicating full stage artifacts
- operator timeline and diagnostics can rely on the same event semantics

## Risks

- if event records become too large, they will duplicate artifacts and stop
  being useful as high-signal observability surfaces
- if deterministic outcome is omitted on decision events, later UI and review
  tools will drift back to ad hoc status mapping
- if fallback fields become catch-all explanation text, they will blur runtime
  cause versus outcome

## Next Artifact

The parallel Wave 3 companions are:

- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`

After the Wave 3 trio is approved, the next sequential spec should be:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
