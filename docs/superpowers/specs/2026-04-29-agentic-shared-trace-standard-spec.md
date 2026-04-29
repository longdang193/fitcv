---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-shared-trace-standard
targets:
  - docs/intent/workstreams/threads/workstream-agentic-observability/05-agentic-observability-shared-trace-standard.md
  - docs/observability.md
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_analysis
  - cv_generation
---

# Agentic Shared Trace Standard

## Summary

Define one canonical, bounded, persisted trace standard for AI-agent-based
steps so every agentic stage or review flow can expose the same operator-facing
truth families:

- actual runtime path
- provider and model provenance
- bounded input and output summaries
- attempt and retry behavior
- validation or acceptance outcome
- degradation and persistence status

The existing `agentic-live-trace.json` for CV generation should become the
first implementation of this broader standard rather than a one-off trace
format.

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- the repo now has one persisted agentic trace surface, but the broader
  question is whether all AI-agent-based steps should expose comparable
  observability
- without a shared standard, each future agentic surface will invent its own
  payload shape, artifact naming, and degradation language
- this is cross-cutting observability design work, not a single-stage bug fix

Invariants:

- every persisted agentic trace remains bounded and operator-readable
- trace truth derives from runtime facts, not UI inference
- artifact absence must distinguish `not_applicable` from `missing` and
  `degraded`
- no raw chain-of-thought or unbounded provider transcripts by default
- shared fields stay stable across steps even when step-specific details differ

Dependencies:

- `docs/intent/workstreams/threads/workstream-agentic-observability/01-agentic-observability-event-contract.md`
- `docs/intent/workstreams/threads/workstream-agentic-observability/02-agentic-observability-operator-surface.md`
- `docs/intent/workstreams/threads/workstream-agentic-observability/03-agentic-observability-provider-provenance.md`
- `docs/intent/workstreams/threads/workstream-agentic-observability/04-agentic-observability-synonym-proposal-trace.md`
- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec.md`
- `docs/superpowers/specs/2026-04-29-persisted-run-scoped-agentic-live-trace-surface-spec.md`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread-to-spec lineage from
frontmatter.

Plan needed: `yes` after approval, because implementation should be split into
step-specific waves rather than landed as one large observability rewrite.

## Problem

FitCV is increasingly relying on AI-agent-based steps, but our observability is
still uneven.

Today we have a strong run-artifact pattern for:

- stage artifacts
- CV debug ledgers
- run bundle manifests
- settings-used snapshots
- timeline events

We now also have one persisted trace surface for agentic CV generation. That is
good progress, but it creates a new architectural fork if we stop there:

- CV generation would have one trace contract
- CV analysis could expose a different trace contract later
- synonym proposal generation could expose a third
- future agentic review or repair loops could expose none at all

That drift would make debugging much harder than it needs to be. Operators
should not have to relearn a different artifact vocabulary for each agentic
step.

## Goals

- define a shared persisted trace vocabulary for AI-agent-based steps
- make artifact naming, applicability state, and degradation state consistent
- standardize the minimum trace facts every agentic step should expose
- allow step-specific extensions without breaking the shared operator model
- ensure all persisted traces remain downloadable from the UI and bundle-visible

## Non-Goals

- no requirement that every internal micro-step becomes its own trace artifact
- no requirement to expose raw provider payloads or LangGraph-internal graphs
- no forced schema identity between all steps; the goal is a shared contract
  family, not a single giant universal payload
- no immediate implementation of every future agentic step in the first wave

## In-Scope Step Families

This standard should apply to any step that is genuinely AI-agent-based and
whose runtime behavior materially affects operator debugging or output quality.

Current and near-term examples:

- `cv_generation`
- `cv_analysis`
- synonym or mapping proposal generation
- future agentic review, repair, or adjudication flows

Rule:

- deterministic stages with no model invocation do not need an agentic trace
  just for symmetry

## Proposed Contract

## 1. Trace Family Standard

Every AI-agent-based step should expose a persisted run-scoped trace artifact
that follows the same top-level contract family.

Required properties:

- one artifact per run per agentic step family
- downloadable from run detail UI
- included in `artifacts.zip` when applicable
- represented in `manifest.json` with applicability state

Naming convention:

- `<step-id>-trace.json`

Examples:

- `agentic-live-trace.json` for `cv_generation`
- `cv-analysis-trace.json` for an agentic analysis trace
- `synonym-proposals-trace.json` for proposal-generation trace

Rule:

- the filename may stay step-specific, but the payload shape must follow the
  shared standard below

## 2. Shared Top-Level Payload Contract

Every trace artifact should expose:

- `run_id`
- `trace_schema_version`
- `trace_family`
- `step_id`
- `trace_status`
- `trace_summary`
- `records`
- `degradation`
- `artifact_refs`

### `trace_family`

Allowed values should describe the broad kind of trace, for example:

- `agentic_step_trace`
- `agentic_review_trace`

Initial recommendation:

- use `agentic_step_trace` for all first-wave persisted traces

### `step_id`

Examples:

- `cv_generation`
- `cv_analysis`
- `synonym_proposals`

Rule:

- the step id must match the runtime step being traced, not a UI label

### `trace_status`

Allowed values:

- `not_applicable`
- `completed`
- `partial`
- `degraded`

Meaning:

- `not_applicable`: this run never entered the relevant agentic step
- `completed`: bounded trace facts were fully captured for expected records
- `partial`: some expected records are absent, but useful trace data exists
- `degraded`: the trace exists, but one or more capture or persistence paths
  fell back to reduced detail

## 3. Shared Per-Record Contract

Each `records[]` entry should represent one job-scoped or unit-of-work-scoped
agentic action.

Required shared fields:

- `record_id`
- `scope_type`
- `scope_key`
- `status`
- `decision_chain`
- `runtime_provenance`
- `attempts`
- `input_summary`
- `output_summary`
- `validation_summary`
- `repair_summary`
- `error_summary`
- `artifact_refs`

### `scope_type`

Examples:

- `job`
- `proposal_batch`
- `review_item`

### `scope_key`

Examples:

- job URL
- proposal batch id
- review item id

Rule:

- scope keys must help operators map the trace back to the affected artifact or
  row without needing hidden internal identifiers

## 4. Runtime Provenance Contract

Every traced agentic step should expose the actual runtime used.

Minimum fields:

- `runtime_path`
- `provider`
- `model`
- `base_url` when relevant
- `prompt_contract`
- `template_path` when relevant
- `response_schema_name` when relevant
- `mode_source` when runtime routing is configurable

Rule:

- provenance must describe what actually ran, not only what was configured in
  theory

## 5. Attempt Contract

Every trace record should summarize bounded invocation attempts.

Each `attempts[]` entry should be able to expose:

- `attempt_index`
- `attempt_type`
- `started_at`
- `finished_at`
- `latency_ms`
- `provider_status`
- `input_character_count`
- `input_item_count`
- `retry_reason`
- `error_stage`
- `error_code`
- `error_message`
- `response_id` when safely available

Examples of `attempt_type`:

- `initial_generation`
- `repair_retry`
- `proposal_retry`
- `review_retry`

Rule:

- attempts must stay bounded and must not store full raw request or response
  bodies by default

## 6. Shared Input And Output Summary Contract

Every trace record should summarize what went in and what came out.

### `input_summary`

May include:

- bounded counts
- prompt or template ids
- selected setting refs
- evidence or source-item counts
- candidate or job identity summaries

Must not include:

- full prompts
- full source corpora
- full evidence bodies

### `output_summary`

May include:

- accepted output present or not
- output counts
- compact outcome labels
- selected section lists
- proposal counts

Must not include:

- full CV markdown
- full generated proposal bodies when a smaller bounded summary is enough

## 7. Validation And Repair Contract

Not every step validates or repairs in the same way, but the trace surface
should still use consistent summary keys.

### `validation_summary`

May expose:

- `initial_valid`
- `final_valid`
- `initial_missing_fields`
- `final_missing_fields`
- `violation_count`
- `warning_count`

### `repair_summary`

May expose:

- `repair_attempted`
- `repair_attempt_count`
- `repair_reason`
- `repair_targets`

Rule:

- steps that do not support repair should still expose a stable empty or false
  summary rather than omitting the concept unpredictably

## 8. Error And Degradation Contract

The shared standard should clearly separate business-path failure from
observability degradation.

### `error_summary`

Use for the step's own runtime failure facts, such as:

- provider unavailable
- validation failure
- proposal-generation error

### `degradation`

Use for trace-capture or persistence problems, such as:

- bounded trace capture lost some attempt details
- durable persistence failed and bundle-only fallback was used
- a trace artifact should exist but only a reduced summary could be persisted

Rule:

- a step may be successful while its observability is degraded
- the reverse is also possible: the step may fail cleanly while the trace is
  fully captured

## 9. Bundle Manifest Standard

All agentic trace artifacts should participate in one shared manifest model.

Per-artifact states:

- `present`
- `not_applicable`
- `missing`
- `degraded`

Manifest requirements:

- include each expected agentic trace artifact by filename
- preserve the same truth as direct download routes
- provide a compact reason when state is `missing` or `degraded`

Rule:

- operators should be able to answer from `manifest.json` alone whether a trace
  was expected and whether its absence is a bug or simply not applicable

## 10. UI Download Standard

All applicable traces should be downloadable directly from the run detail page.

UI rules:

- expose traces in the existing exports area
- keep labels consistent with other JSON exports
- avoid creating one special-purpose UI screen per trace family

This keeps debugging ergonomic and aligned with the repo's existing run-export
pattern.

## 11. Relationship To Existing Artifacts

Agentic traces complement rather than replace:

- event records
- stage artifacts
- debug ledgers
- settings-used exports

Role separation:

- event records: quick bounded change facts
- stage artifacts: stage-owned diagnostic truth
- debug ledgers: broader result and decision context
- agentic traces: provider/attempt/validation/repair visibility for one
  agentic step family

Rule:

- traces should link to related artifact families rather than duplicating their
  full payloads

## 12. Rollout Model

Implementation should happen in waves rather than one large cross-repo rewrite.

Recommended order:

1. `cv_generation` stays the first reference implementation
2. `cv_analysis` adopts the shared trace standard next
3. synonym or mapping proposal generation adopts the same trace family
4. future agentic review or repair flows opt in as they land

Rule:

- later waves may add step-specific fields, but they should not break the
  shared top-level and shared per-record vocabulary

## Acceptance Criteria

- a reviewer can inspect any persisted agentic trace artifact and immediately
  recognize the same top-level vocabulary
- a reviewer can tell for any AI-agent-based step:
  - whether it ran
  - which runtime path/provider/model actually ran
  - how many attempts occurred
  - whether validation or repair was involved
  - whether failure belonged to the business path or only to observability
- `manifest.json`, direct download routes, and run exports remain aligned
- new agentic steps can adopt the standard without inventing a fresh operator
  vocabulary

## Risks

- if the standard is too abstract, teams will keep inventing per-step
  exceptions and drift will return
- if the standard becomes a giant universal payload, traces will become noisy
  and expensive
- if raw transcripts leak into the default persisted contract, operator safety
  and maintainability will degrade quickly
- if the rollout tries to convert every step at once, implementation risk will
  swamp the design benefits

## Next Artifact

The next artifact should be an implementation execution map or staged plan set
that breaks adoption into waves:

- align `cv_generation` naming with the shared standard where needed
- add a `cv_analysis` persisted trace surface
- add a synonym-proposal trace surface
- refresh `docs/observability.md` so all agentic trace families are documented
  together
