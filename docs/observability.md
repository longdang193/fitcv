---
doc_id: observability
doc_type: operator-guide
explains:
  features:
    - inspection_debugging
    - trigger_run_management
  components:
    - src/fitcv
    - src/fitcv_cp
---

# Observability

FitCV’s observability model is centered on **run truth**, **stage-owned
artifacts**, and **persisted event timelines**. There is no separate agent console; LLM-backed stages use the same run-detail,
export, and event surfaces that operators already use for the rest of the
pipeline.

This page is the front-door guide for operators and developers who want to
understand what the system did, why it did it, and where LLM runtime behavior
is visible.

## Setup Observability (Quick Start)

Use this section when bootstrapping local/dev observability from zero.

### 1) Prerequisites

- Running FitCV control plane and worker environment
- Python environment with project dependencies installed
- Optional: local OTLP collector endpoint (example: `http://localhost:4318/v1/traces`)

### 2) Set environment variables

Minimum useful baseline:

```powershell
$env:FITCV_LANGFUSE_ENABLED="true"
$env:FITCV_LANGFUSE_BASE_URL="http://localhost:3000"
$env:FITCV_LANGFUSE_RICH_IO_ENABLED="true"
$env:FITCV_OTEL_ENABLED="true"
$env:FITCV_OTEL_EXPORTER_OTLP_ENDPOINT="http://localhost:4318/v1/traces"
$env:FITCV_OTEL_SERVICE_NAME="fitcv-control-plane"
```

If Langfuse/OTel not needed, you may disable with:

```powershell
$env:FITCV_LANGFUSE_ENABLED="false"
$env:FITCV_OTEL_ENABLED="false"
```

### 3) Start stack

Use normal project startup flow (web + worker). After boot, open:

- `/admin/runs`
- `/admin/runs/{run_id}`

### 4) Validate run and event flow

Run checker script:

```powershell
python -m pytest tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_run_detail_output_availability.py -q
```

Exit code meaning:

- `0`: healthy
- `2`: alert
- `3`: checker runtime/request failure

### 6) Validate effective runtime environment

If status looks wrong, print effective values from process shell:

```powershell
Write-Host "FITCV_LANGFUSE_ENABLED=$env:FITCV_LANGFUSE_ENABLED"
Write-Host "FITCV_LANGFUSE_BASE_URL=$env:FITCV_LANGFUSE_BASE_URL"
Write-Host "FITCV_LANGFUSE_RICH_IO_ENABLED=$env:FITCV_LANGFUSE_RICH_IO_ENABLED"
Write-Host "FITCV_OTEL_ENABLED=$env:FITCV_OTEL_ENABLED"
Write-Host "FITCV_OTEL_EXPORTER_OTLP_ENDPOINT=$env:FITCV_OTEL_EXPORTER_OTLP_ENDPOINT"
Write-Host "FITCV_OTEL_SERVICE_NAME=$env:FITCV_OTEL_SERVICE_NAME"
```

## Core Observation Surfaces

### Runs list

`/admin/runs`

Use this page to find the run, its current status, trigger mode, and whether it
is worth drilling into immediately.

### Run detail

`/admin/runs/{run_id}`

This is the main observability surface. It combines:

- timeline events
- stage progress
- run health summaries
- stage-quality metrics
- run exports
- stage-artifact downloads
- synonym overlay and review-adjacent surfaces

For most debugging, start here before opening raw JSON exports.

Long-running provider work emits stage-owned liveness events without creating new
LLM calls: `enrich_heartbeat` during fresh enrichment and
`cv_generation_heartbeat` while CV-generation futures remain pending.
Both report bounded counts, elapsed time, heartbeat interval, configured concurrency,
and effective concurrency at roughly 15-second cadence. Effective concurrency is
bounded by runnable work: enrich batches or generation-ready CV rows.

## Two-Layer Langfuse Observability Model

Observability uses two complementary layers:

- **Layer 1: run-scoped summary surfaces**
  - run/root trace context remains operator entrypoint
  - aggregate summaries such as `pipeline_complete` remain run-level
  - run-summary surfaces avoid duplicating full item-level raw IO
- **Layer 2: item-level evaluable observations**
  - `cv_analysis_item` captures one item observation per candidate-job analysis attempt
  - `cv_generation_item` captures one item observation per candidate-job generation attempt
  - item observations are nested under same run trace for lineage continuity

Item observations support both audiences:

- **reviewers/operators**: readable rendered `input`/`output`
- **automation/filtering**: structured metadata payloads for filters and joins

Bounded payload policy:

- rendered `input` and `output` are capped/redacted through telemetry helpers
- item observations preserve disposition-aware summaries across success and failure paths
- raw chain-of-thought, unbounded provider payloads, and oversized blobs are not stored in item observations
- telemetry degradation must not block primary pipeline execution

Wave 1 verification status:

- focused telemetry and pipeline regression coverage verifies schema, truncation, retry/disposition semantics, and lineage expectations
- one local Langfuse validation pass has verified that the run trace still shows root/run-summary context while nested `cv_analysis_item` and `cv_generation_item` observations expose reviewer-readable rendered IO under the same trace

## OpenTelemetry Export Runtime

FitCV now supports OpenTelemetry export wiring with safe fallback behavior.

Runtime toggles:

- `FITCV_OTEL_ENABLED` (`true`/`false`)
- `FITCV_OTEL_EXPORTER_OTLP_ENDPOINT` (OTLP HTTP endpoint)
- `FITCV_OTEL_SERVICE_NAME` (optional, defaults to `fitcv-control-plane`)
- `FITCV_LANGFUSE_RICH_IO_ENABLED` (`true`/`false`; local startup scripts default to `true` when unset)
- `control_plane.observability.emit_model_routing_diagnostics` (runtime routing event toggle)
- `control_plane.observability.emit_backend_capability_diagnostics` (backend diagnostics event toggle)

Collector example:

- local collector endpoint: `http://localhost:4318/v1/traces`
- for remote collectors, set the full OTLP HTTP trace endpoint URL

Fallback behavior:

- if OTel dependencies are unavailable, export is marked degraded
- if exporter endpoint is missing, export is marked degraded
- telemetry degradation does not block stage execution or artifact persistence
- stage artifacts remain the evidence source of truth

Operator signal stays event- and artifact-driven. Use persisted events,
artifacts, and runtime logs for telemetry troubleshooting.
- `status=degraded`, `degradation_reason=otel_exporter_init_failed`
  - verify endpoint reachability, protocol path, and collector health

Environment precedence note:

- run-detail health cards reflect the process environment used by the active web/worker processes
- shell/system env overrides startup-script defaults
- startup scripts currently default `FITCV_LANGFUSE_RICH_IO_ENABLED=true` for local/dev observability unless explicitly overridden
- if Langfuse/OTel status looks unexpected, see **Setup Observability (Quick Start) -> 6) Validate effective runtime environment**



Langfuse export consumption lanes:

- raw export: keep full fidelity for forensics
- analysis-ready export: filter to rows with meaningful `input` or `output`, plus `:rich_io` rows
  (including exports where `input`/`output` are stringified JSON objects)
- reviewer-first Wave 1 item observations should surface sectioned markdown/text in Langfuse `input`/`output`, while metadata keeps structured backing payloads for filters and joins

Public-repo note: export filtering is intentionally left as a local workflow (use any JSONL tooling) so the public mirror stays minimal.

Pipeline summary quality block:

- `pipeline_complete` rich output now includes `quality_summary` with:
  - acceptance/review/failure distribution and rates
  - analysis-to-generation conversion
  - retry counts

Langfuse latency semantics:

- UI `Latency` is derived from observation/span timing (`start_time` -> `end_time`).
- `:rich_io` payload field `output.latency_ms` is a custom diagnostic metric and is not
  automatically used by Langfuse UI latency unless a timed observation exists.
- Control-plane rich IO ingestion now emits an `observation-create` span for
  high-value events when `latency_ms > 0`, so UI latency and payload latency can
  agree for those rows.

### Control-Plane Structured Diagnostics

Control-plane enqueue and backend-binding paths now emit structured diagnostics:

- `control_plane.backend_execution`
- `control_plane.model_routing`
- `control_plane.backend_fallback_binding`

Current required fields include:

- request identity: `run_id`, `trace_id`, `stage`, `task_part`
- backend/routing facts: backend identifiers, queue/backend run ids, provider/model labels

### Raw run events

`GET /runs/{run_id}/events`

Use this when you want the machine-facing event stream rather than the rendered
HTML timeline. This is especially helpful for tooling, incident review, or
cross-run comparisons.

## LLM Observation By Area

### CV analysis and generation

Main surfaces:

- `/admin/runs/{run_id}/cv-analysis-trace.json`
- `/admin/runs/{run_id}/cv-generation-trace.json`
- `/admin/runs/{run_id}/cv-debug.json`
- `/admin/runs/{run_id}/hitl-review-audit.json`
- `/admin/runs/{run_id}/stage-artifacts.json`
- `/admin/runs/{run_id}/stage-artifacts/cv_analysis.json`
- `/admin/runs/{run_id}/stage-artifacts/cv_generation.json`

`llm_runtime.py` owns one safe `llm_runtime_evidence_v1` projection. Only an
actual shared-runtime call emits evidence. Reuse, replay, resume, reranker block,
and fit-gate skip paths emit zero new evidence. Evidence excludes prompts, raw
responses, headers, credentials, and provider payloads.

### CV analysis trace

`/admin/runs/{run_id}/cv-analysis-trace.json`

Use this for reranker gates, evidence selection, gap computation, readiness, and
analysis failures. It uses `stage_execution_trace` and records stage facts such
as attempts, bounded inputs/outputs, validation, repair, and errors. Current
analysis mechanics do not call `execute_llm_task`, so this trace does not
fabricate LLM provenance or runtime evidence.

### CV generation trace

`/admin/runs/{run_id}/cv-generation-trace.json`

Use this for direct or LangGraph generation calls, retries, bounded runtime
failures, validation, repair, and final generation status. Both adapters feed the
same repo-native result contract and the same `stage_execution_trace` family.
The canonical artifact filename is `cv-generation-trace.json`.

`/admin/runs/{run_id}/agentic-live-trace.json` remains a read-only historical
alias. It uses the same response builder and must not become a second current
writer or semantic contract. Historical nested schema/family values remain
unchanged when old payloads are read.

The trace is bounded. It stores no chain-of-thought, full prompt body, raw
provider response, headers, credentials, or secrets.

### Timeline and event reasoning

The timeline in run detail and the raw event stream are the best way to inspect:

- stage starts and completions
- checkpoint pauses and continues
- snapshot persistence failures
- agentic fallback or review-related transitions
- HITL review actions (`cv_review_action`)

If something “felt weird” during a run, the timeline is often the fastest way
to locate the exact stage boundary where the behavior changed.

### Markdown quality outcomes

When CV generation is agentic and markdown quality checks are enabled, markdown
consistency outcomes are observable through:

- run detail "Markdown Quality" card
- `cv_generation.json` quality metrics and output counts
- `cv-debug.json` per-record validation snapshots
- `hitl-review-audit.json` review-required reason/action payloads

Outcome semantics:

- blocking markdown issues (for example unsupported bullet markers) route to
  validation failure
- shallow markdown structure routes to `review_required`
- accepted markdown passes both structural and grounding checks

### Mapping suggestions and synonym proposals

The current agentic synonym surfaces are:

- `/admin/runs/{run_id}/mapping-suggestions.json`
- `/admin/runs/{run_id}/synonym-proposals-trace.json`
- `/admin/runs/{run_id}/synonym-proposals.json`
- `/admin/runs/{run_id}/approved-synonym-proposals.yaml`
- `/admin/synonyms/global.yaml`
- `/admin/mapping-suggestions.json`
- `/admin/synonym-proposals.json`

These let you inspect:

- which aliases were detected from run-scoped evidence
- per-alias proposal-generation trace status and degradation
- how those suggestions were grouped into review-ready synonym proposals
- which proposals are still unreviewed versus already actioned
- which approved run-scoped mappings can be exported as overlay YAML

Run detail now also exposes synonym-review operational summaries:

- batch submit summary (`applied`, `skipped`, `failed`)
- apply-approved-to-run summary (`applied`, `skipped`, `failed`)
- promote-to-global summary (`applied`, `skipped`, `failed`)
- promote-to-global classification counts (`new`, `unchanged`, `overridden`)
- triage refresh summary (`triaged`, `reused`, `skipped`, `failed`)
- triage status badge (`fresh`, `partial`, `stale`, `not_generated`)
- advisory recommendation metadata shown per pending proposal
  (`recommended_action`, recommendation confidence, rationale, risk flags)

Recommendation display is advisory-only. Final review and promotion actions
remain explicit HITL submits by the operator.

Run-local application semantics:

- review status changes alone do not imply cross-run canonical mutation
- `Apply Approved to This Run` materializes approved pairs into the run snapshot
  for downstream stage execution
- promote-to-global remains the explicit canonical update path

Promotion semantics are merge/overlay-based:

- exported `approved-synonym-proposals.yaml` is run-approved delta only
- exported `global.yaml` is the full canonical synonym map snapshot
- promote-to-global applies selected delta rows onto the global canonical map
- alias collisions are surfaced as overrides rather than silent replacement

Triage refresh emits run events for timeline/debug usage:

- `synonym_proposal_triage_completed`
  - includes counts (`triaged`, `reused`, `skipped`, `failed`)
  - includes runtime metadata (`provider`, `model`, `wire_api`, `base_url`)

### Synonym proposals trace

`/admin/runs/{run_id}/synonym-proposals-trace.json`

Use this when debugging proposal-generation flow quality rather than reviewing
proposal payload content itself.

This artifact follows the same shared stage-execution trace contract as:

- `cv-analysis-trace.json`
- `cv-generation-trace.json`

Its `step_id` is `synonym_proposals`, and it captures:

- proposal-generation attempt status
- alias-scoped records
- persistence degradation status such as `bundle_only_degraded`

### Settings and runtime context

The main runtime-context surface is:

- `/admin/runs/{run_id}/settings-used.json`

Route handlers stay in `src/fitcv_cp/app.py`. Shared review/export shaping now
lives in `src/fitcv_cp/app_run_support.py`, while shared worker snapshot payload
builders live in `src/fitcv_cp/worker_run_support.py`.

Use it to answer:

- which effective settings this run actually used
- whether a per-run override changed behavior
- whether synonym overlay or prompt/runtime configuration influenced the result

## Recommended Observation Workflow

When debugging a surprising run:

1. open `/admin/runs/{run_id}`
2. scan run status, run health, and stage progress
3. read the timeline around the first suspicious transition
4. open `stage-artifacts.json` for stage-owned truth
5. open `cv-analysis-trace.json` if the issue starts before generation
6. open `cv-generation-trace.json` for direct or LangGraph generation runtime, retry, or validation issues
7. open `synonym-proposals-trace.json` when proposal persistence or proposal
   generation status looks degraded
8. open `cv-debug.json` for the broader CV-generation ledger
9. open `hitl-review-audit.json` for review queue status and action history
10. inspect the run detail "Markdown Quality" card when quality drift or shallow
    outputs are suspected
11. open `settings-used.json` if behavior may be config-driven
12. open mapping-suggestion or synonym-proposal exports if the issue is
   taxonomy-related

## What Each Surface Is Good At

- run detail HTML:
  - fast human triage
- raw events:
  - sequence reconstruction and tooling
- CV analysis trace export:
  - analysis-stage attempt, evidence-selection, and pre-generation debugging
- CV generation trace export:
  - direct or LangGraph attempt, retry, bounded failure debugging, and shared
    stage-execution trace inspection
- synonym proposals trace export:
  - proposal-generation attempt and persistence-degradation debugging
- stage artifacts:
  - stage-owned truth
- CV debug export:
  - compact CV-generation ledger and per-job debug records
- HITL review audit export:
  - run-scoped `review_required` queue, pending/resolved status, and operator
    action history (`approve`, `regenerate_once`, `reject`)
- Markdown Quality card:
  - compact view of markdown-quality review-required and blocking outcomes
  - sample reasons to accelerate triage before drilling into raw artifacts
- settings-used export:
  - runtime context and override visibility
- mapping-suggestions and synonym-proposals exports:
  - agentic taxonomy and review surfaces

## Important Boundaries

- run-detail labels are derived views, not the source of semantic truth
- stage artifacts are the primary source for stage-owned decisions
- run-scoped persisted fields and export endpoints are artifact SSOT
- `artifacts/live_run_<run_id>/` is deterministic local evidence mirror/cache, not authority

## Local Artifact Mirror

Terminal runs now mirror available run artifacts to local filesystem:

- `artifacts/live_run_<run_id>/`

Mirror content is generated from run-scoped persisted payloads and event history.
Mirror does not redefine artifact contracts.

When historical runs are missing mirror folders, backfill with:

```powershell
python scripts/backfill_live_run_artifacts.py --run-id <run_id> --dry-run
python scripts/backfill_live_run_artifacts.py --run-id <run_id>
```

Backfill command behavior:

- terminal runs only (`succeeded`, `failed`, `cancelled`)
- idempotent: existing mirror folders are skipped
- summary output reports `created`, `skipped_existing`, `missing_payload`, `errors`

## Related Docs

- [api.md](api.md)
- [usage.md](usage.md)
- [pipeline.md](pipeline.md)
- [architecture.md](architecture.md)

