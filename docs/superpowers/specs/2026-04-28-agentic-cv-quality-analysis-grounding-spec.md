---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
targets:
  - docs/intent/workstreams/threads/workstream-bounded-agentic-cv-quality/01-agentic-cv-quality-analysis-grounding.md
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_analysis.yaml
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/pipeline.py
  - src/fitcv/contracts.py
related_features:
  - cv_system
  - inspection_debugging
  - settings_system
related_stages:
  - cv_analysis
---

# Agentic CV Quality Analysis Grounding

## Summary

Define the bounded quality contract for `cv_analysis` so evidence selection,
scoring clarity, grounded gap reasoning, and pre-writing hold or skip reasons
stay explainable and stage-owned before any CV generation work begins.

This spec follows the stage-authority and deterministic-outcome contracts. It
keeps analysis quality focused on grounded late-stage preparation rather than
letting generation or UI needs redefine what `cv_analysis` is for.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- this is a Wave 3 detailed spec from the approved first-wave authoring map
- it is bounded to the `cv_analysis` quality seam
- it depends on stable stage and outcome vocabulary so it does not redefine fit
  or readiness meanings

Invariants:

- `cv_analysis` owns evidence retrieval, evidence selection, gap analysis, and
  generation-readiness truth
- grounding quality must be explainable from bounded evidence and channel
  summaries
- pre-writing negative outcomes must preserve stage-owned reason codes rather
  than collapsing into generic failure language
- generation does not re-own analysis semantics

Dependencies:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-deterministic-truth-outcome-contract-spec.md`
- `docs/intent/workstreams/threads/workstream-bounded-agentic-cv-quality/01-agentic-cv-quality-analysis-grounding.md`
- `docs/stages/cv_analysis.source.yaml`
- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv/pipeline.py`

Primary lens: `stage`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` should reflect the new spec linkage.

Plan needed: `no` until the Wave 3 trio is complete and approved.

## Problem

The current `cv_analysis` stage already does valuable work:

- computes analysis input fingerprints
- retrieves or reuses analysis payloads
- selects final evidence
- records evidence-selection summaries
- computes gap summaries
- decides blocked, skipped, ready, or failed outcomes

But the quality contract around that work is still implicit. Without a bounded
spec, later changes can improve one sub-part while weakening overall grounding:

- evidence counts may rise while explanation quality falls
- gap summaries may drift away from selected evidence
- skip or hold-like outcomes may lose their precise reason trail

## Goals

- define what "grounded" means for `cv_analysis`
- require explainable evidence-selection summaries
- keep gap reasoning tied to selected evidence and stage-owned inputs
- preserve pre-writing negative reasons in a structured way

## Non-Goals

- no change to CV generation validation rules here
- no redesign of final generation prompts here
- no full scoring-algorithm rewrite in this spec

## Proposed Contract

## 1. Grounding Definition

For `cv_analysis`, grounded quality means:

- the selected evidence can justify the stage’s recommendation for generation
- channel-level support is visible enough to explain why evidence was selected
- gap summaries derive from known candidate and job inputs instead of invented
  claims
- readiness or skip decisions are traceable to bounded inputs and outputs

Grounding is not:

- a large evidence dump
- a free-form narrative with no channel trace
- a generation-time validation concern only

## 2. Required Analysis Inputs

Every bounded analysis record should remain explainable from:

- ranked job snapshot
- candidate profile inputs
- analysis input fingerprint
- selected evidence payload
- evidence-selection summary
- gap summary
- stage-owned status and reason payload

Rule:

- if a reviewer cannot understand why a job was ready, skipped, blocked, or
  failed from those bounded surfaces, the analysis contract is underspecified

## 3. Evidence-Selection Contract

The evidence-selection summary should remain a first-class quality surface.

Required summary families:

- `channel_counts`
- `effective_channel_pool_size`
- `merged_pool_size`
- `deduped_pool_size`
- `selected_evidence_count`
- `selected_evidence_ids`
- `unselected_top_candidates` when bounded and helpful
- `hybrid_alignment`
- `semantic_alignment`

Quality rules:

- selected evidence should be explainable by channel support, not only by final
  presence in the payload
- summary fields should describe why selection narrowed, not just how many items
  survived
- if fallback retrieval is used, the summary should preserve that fact

## 4. Channel Clarity

The analysis channel families in `src/fitcv/contracts.py` should remain
semantically distinct:

- required skill support
- role alignment
- domain alignment
- responsibility alignment

Quality rule:

- later implementation should avoid cross-channel blur where one channel starts
  standing in for all others

This matters because the final evidence bundle must support both grounded fit
reasoning and later writing preparation.

## 5. Gap Summary Contract

Gap summaries should remain bounded and input-derived.

Must stay true:

- they derive from the candidate and job inputs known to `cv_analysis`
- they do not claim evidence the selected bundle cannot support
- they do not silently become a second fit-classification system

Rule:

- gap summaries may explain shortfalls, but they do not override ranking fit or
  generation outcome truth

## 6. Pre-Writing Negative Outcome Contract

Before generation begins, `cv_analysis` may produce negative or non-advancing
outcomes such as:

- `blocked_by_reranker_fit`
- `skipped_fit_gate`
- `analysis_failed`

Quality rules:

- every non-ready outcome should preserve a precise stage-owned reason payload
- the reason should be interpretable without inspecting downstream generation
  surfaces
- later UI and observability surfaces may summarize the reason, but should not
  replace it

This spec intentionally leaves room for future explicit `held`-style review
states, but does not invent them prematurely.

## 7. Reuse And Freshness

`analysis_reuse_status` and `analysis_input_fingerprint` are quality surfaces,
not just caching metadata.

Why they matter:

- they explain whether the analysis result was reused or freshly computed
- they help reviewers decide whether a surprising result is due to stale input
  assumptions or current-stage logic

Rule:

- later implementation should preserve these fields wherever analysis quality is
  inspected or exported

## 8. Relationship To Generation

`cv_generation` may consume:

- selected evidence
- evidence-selection summary
- gap summary

But generation must not re-own analysis quality semantics.

Rules:

- generation may validate downstream writing quality
- generation may not reinterpret what evidence selection meant upstream
- if generation fails, that does not retroactively mean the analysis was
  ungrounded unless a later bounded surface proves it

## Acceptance Criteria

- a reviewer can inspect a bounded `cv_analysis` record and understand why the
  job was ready, skipped, blocked, or failed
- evidence-selection summaries remain rich enough to explain selection quality
- gap reasoning stays tied to known inputs and selected evidence
- reuse and freshness signals remain available for debugging and diagnostics

## Risks

- if evidence-selection summaries become too shallow, analysis quality will look
  better than it really is
- if gap reasoning grows into a second hidden fit system, stage authority will
  drift
- if pre-writing negative reasons are flattened in exports or UI, later review
  flows will lose operational trust

## Next Artifact

The parallel Wave 3 companions are:

- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-operator-control-plane-run-detail-truth-spec.md`

After the Wave 3 trio is approved, the next sequential spec should be:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
