---
layer: change
artifact_type: spec
status: proposed
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
targets:
  - docs/intent/workstreams/threads/workstream-agentic-observability/03-agentic-observability-provider-provenance.md
  - docs/observability.md
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
related_features:
  - inspection_debugging
  - trigger_run_management
  - cv_system
related_stages:
  - cv_generation
---

# Persisted Run-Scoped Agentic Live Trace Surface

## Summary

Add a bounded, persisted, run-scoped agentic live trace surface for late-stage
CV generation so operators can download one trace artifact from the UI and see
what the live provider path actually attempted, how validation and repair
behaved, and why a run accepted, rejected, or failed.

This spec is intentionally narrower than "full LangGraph tracing." It defines a
FitCV-owned trace contract that is:

- persisted with the run
- downloadable from `/admin/runs/{run_id}`
- bundled into `artifacts.zip`
- redacted and bounded for operator debugging

## Triage

Layer: `change`  
Feature type: `ADD`

Reasoning:

- current observability already exposes bounded run artifacts, but there is no
  first-class downloadable live trace artifact
- recent debugging required hopping between `cv-debug.json`, stage artifacts,
  and transient Docker logs to learn whether the live provider was called and
  what failed
- the repo already has a strong run-export pattern, so this should land as a
  new persisted artifact surface rather than a separate console concept

Invariants:

- no raw chain-of-thought or unbounded provider transcripts
- trace truth must come from FitCV-owned runtime facts, not UI inference
- the trace must be downloadable from the run detail UI
- the trace must survive after container logs rotate away

Dependencies:

- `docs/intent/workstreams/threads/workstream-agentic-observability/03-agentic-observability-provider-provenance.md`
- `docs/superpowers/specs/2026-04-28-agentic-observability-event-contract-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-run-mode-and-synonym-proposal-observability-spec.md`
- `src/fitcv/agentic_cv_generation.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`

Primary lens: `mixed`

Generated refresh required: `yes` after the spec is added, because
`docs/generated/planning_lineage.yaml` derives thread-to-spec lineage from
frontmatter.

Plan needed: `yes` before implementation, because the work crosses runtime
generation, artifact persistence, bundle manifest, and operator UI surfaces.

## Problem

The repo already provides useful run-scoped diagnostics:

- `cv-debug.json`
- `stage-artifacts.json`
- `settings-used.json`
- the run timeline
- `artifacts.zip`

But the agentic live path still lacks one persisted artifact that answers the
questions operators actually ask during failures and quality regressions:

- did the live path run at all?
- which provider, model, and runtime path were used?
- how many provider attempts were made?
- what prompt/template/schema contract was used?
- what validation failures triggered a repair attempt?
- what exact bounded error came back from the live provider?

Today, deeper answers often depend on transient stderr or ad hoc dump files from
the sibling `fitcv-langgraph` repo. That is weaker than the rest of the control
plane, where run truth is expected to be inspectable from persisted artifacts.

The UI already knows how to offer downloadable run artifacts. What is missing is
the trace artifact itself.

## Goals

- define one canonical persisted run-scoped live trace artifact for agentic CV
  generation
- make that artifact downloadable from the run detail UI
- include it in `artifacts.zip` and its manifest
- preserve enough request, repair, and failure context to debug quality and
  reliability problems without depending on container logs
- keep the payload bounded, redacted, and fit for normal operator use

## Non-Goals

- no requirement to mirror LangGraph Studio or expose node-by-node internal
  graphs
- no storage of raw chain-of-thought
- no full prompt-body or full provider-response-body dumps by default
- no attempt in this spec to redesign all existing stage artifacts
- no requirement that agentic CV analysis adopt the exact same trace schema in
  the first implementation wave

## Proposed Contract

## 1. Owning Persistence Surface

The canonical persisted source of truth should be a run-scoped artifact payload
owned inside the existing run snapshot system, not a transient log.

Preferred ownership rule:

- persist the live trace within the existing run-scoped snapshot family that is
  already durable for completed runs
- expose it as its own downloadable artifact file

Recommended implementation shape:

- `src/fitcv/pipeline.py` builds a bounded `agentic_live_trace` payload from
  late-stage generation facts
- `src/fitcv_cp/worker_job.py` persists that payload as part of the immutable
  run-scoped artifact snapshot flow
- `src/fitcv_cp/app.py` exposes a derived
  `/admin/runs/{run_id}/agentic-live-trace.json` download route and includes
  the file in `artifacts.zip`

Steady-state rule:

- operators should not need Docker logs to inspect normal live-provider
  failures or repair flow

## 2. Artifact Name And Availability

The artifact name should be:

- `agentic-live-trace.json`

Availability rules:

- present for runs where late-stage agentic generation was enabled and the
  `cv_generation` stage was attempted
- `not_applicable` for non-agentic runs
- still present for failed live-provider attempts when any bounded trace facts
  were captured

UI contract:

- the run detail "Run Exports" card should show `Agentic Live Trace JSON` when
  the artifact is present
- the artifact should also be downloadable through the bundle zip

## 3. Run-Scoped Payload Shape

The payload should be one run-scoped document with:

- run metadata
- late-stage mode summary
- trace-level summary counts
- per-job trace records
- degradation metadata when full capture was not possible

Suggested top-level fields:

- `run_id`
- `trace_schema_version`
- `created_at`
- `late_stage_mode`
- `trace_status`
- `trace_summary`
- `job_traces`
- `degradation`

### `trace_status`

Allowed values:

- `not_applicable`
- `completed`
- `partial`
- `degraded`

Meaning:

- `not_applicable`: non-agentic or stage never attempted
- `completed`: all attempted agentic generation records captured within bounds
- `partial`: some records captured but one or more expected job traces missing
- `degraded`: trace contract exists but one or more capture steps had to fall
  back to reduced detail

## 4. Per-Job Trace Record Contract

Each `job_traces[]` entry should be bounded and operator-readable.

Minimum fields:

- `job_url`
- `job_title`
- `cv_generation_status`
- `decision_chain`
- `runtime_provenance`
- `provider_request`
- `provider_response`
- `validation_cycle`
- `repair_cycle`
- `artifact_refs`

### `runtime_provenance`

Minimum fields:

- `runtime_path`
- `provider`
- `model`
- `base_url` when relevant
- `prompt_contract`
- `template_path`
- `response_schema_name`

Rule:

- provenance must describe the actual live path used, not just configured
  defaults

### `provider_request`

Bounded request facts only:

- `request_started_at`
- `request_finished_at`
- `latency_ms`
- `attempt_index`
- `input_character_count`
- `evidence_item_count`
- `repair_missing_sections` when retrying
- `debug_flags_active`

Must not include by default:

- full prompt text
- full evidence body
- full raw request payload

### `provider_response`

Minimum fields:

- `provider_status`
- `accepted_output_present`
- `error_stage`
- `error_code`
- `error_message`
- `response_id` when the provider exposes one safely

Rule:

- provider errors should preserve the bounded upstream payload already useful
  for incident debugging, such as HTTP status and compact provider error
  message

### `validation_cycle`

Minimum fields:

- `initial_valid`
- `final_valid`
- `initial_missing_sections`
- `final_missing_sections`
- `grounding_violation_count`
- `skill_violation_count`
- `warnings_count`

Rule:

- the trace should summarize validation and repair behavior without duplicating
  the full validator payload already available elsewhere

### `repair_cycle`

Minimum fields:

- `repair_attempted`
- `repair_reason`
- `repair_missing_sections`
- `repair_attempt_count`

Examples:

- missing sections retry
- candidate name placeholder repair

## 5. Bounded Redaction Rules

The live trace must be safe and bounded by default.

Must include:

- counts
- ids and names of contracts
- timestamps
- compact error messages
- compact section lists

Must not include by default:

- chain-of-thought
- full raw provider request bodies
- full raw provider response bodies
- full evidence documents
- full CV markdown bodies

Optional debug extension:

- implementation may support an explicit debug-only raw dump path behind
  existing environment flags, but that dump is outside the default persisted
  artifact contract

## 6. Relationship To Existing Artifacts

The new trace artifact should complement, not replace, existing diagnostics.

Artifact roles:

- `cv-debug.json`: CV-generation outcome ledger and bounded debug record export
- `stage-artifacts.json`: stage-owned truth and quality summaries
- `agentic-live-trace.json`: provider-attempt, validation-cycle, and repair
  trace for the live agentic path

Coordination rule:

- the live trace should reference existing artifact families through
  `artifact_refs` rather than duplicating their full payloads

## 7. Bundle Manifest Contract

`manifest.json` for `artifacts.zip` should grow a first-class entry for
`agentic-live-trace.json`.

Manifest requirements:

- include the artifact in `included_files` when present
- expose `not_applicable`, `present`, `missing`, or `degraded` state
- include a short reason when the artifact is missing or degraded

This lets an operator answer from the bundle alone:

- whether the run used the agentic live path
- whether a trace artifact should exist
- whether its absence is expected or a drift signal

## 8. UI Download Contract

The run detail page should expose the artifact directly instead of requiring the
operator to unzip `artifacts.zip`.

Required route:

- `/admin/runs/{run_id}/agentic-live-trace.json`

Required UI behavior:

- show the link in the existing run exports section
- keep the label consistent with other JSON exports
- do not invent a second observability page just for this trace

This matches the repo's current operator habit: inspect a run, then download a
specific JSON artifact when deeper debugging is needed.

## 9. Event And Failure Signaling

The event timeline should remain a quick locator, while the trace artifact owns
the deeper bounded details.

Required signaling:

- if trace persistence itself degrades, emit a compact warning event
- if the live provider fails, keep the normal stage-owned failure event and also
  preserve the bounded provider failure fields in the trace record

Rule:

- event messages stay concise; the trace artifact carries the denser diagnostic
  summary

## 10. Validation Expectations

Implementation should add verification for:

- agentic runs that produce `agentic-live-trace.json`
- non-agentic runs whose manifest marks the trace `not_applicable`
- live-provider failures that still produce bounded trace records
- UI export lists that include the new artifact when present
- artifact bundle manifests that stay aligned with the direct download routes

Recommended test cases:

- accepted live-provider generation with no repair
- live-provider validation retry due to missing sections
- live-provider failure with bounded provider error payload
- non-agentic run with explicit absence signaling

## Acceptance Criteria

- a reviewer can open `/admin/runs/{run_id}` and download one
  `agentic-live-trace.json` artifact when the run used the live agentic
  generation path
- the artifact survives independently of transient container logs
- a reviewer can tell from the artifact which provider and model actually ran,
  whether a repair was attempted, and why generation failed or succeeded
- `artifacts.zip` and `manifest.json` carry the same truth as the direct
  download route
- non-agentic runs do not masquerade as "missing trace" failures

## Risks

- if the payload grows into a raw transcript dump, it will become expensive,
  noisy, and harder to keep safe
- if the trace is only added to the UI and not to the artifact bundle, offline
  debugging will stay weak
- if the trace duplicates full validator or CV payloads, it will drift from the
  existing run-artifact boundaries
- if the implementation chooses transient logs over persisted run artifacts, the
  repo will keep losing crucial debugging context after restarts

## Next Artifact

The next artifact should be an implementation plan that splits this work into:

- runtime trace capture in `src/fitcv/agentic_cv_generation.py` and
  `src/fitcv/pipeline.py`
- run-scoped persistence wiring in `src/fitcv_cp/worker_job.py`
- artifact route, manifest, and run-export wiring in `src/fitcv_cp/app.py`
- operator-doc refresh in `docs/observability.md`
