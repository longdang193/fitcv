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
artifacts**, and **persisted event timelines**. There is no separate agent
console; the agentic parts are observed through the same run-detail, export,
and event surfaces that operators already use to inspect the rest of the
pipeline.

This page is the front-door guide for operators and developers who want to
understand what the system did, why it did it, and where the agentic behavior
is visible.

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

### Raw run events

`GET /runs/{run_id}/events`

Use this when you want the machine-facing event stream rather than the rendered
HTML timeline. This is especially helpful for tooling, incident review, or
cross-run comparisons.

## Agentic Observation By Area

### CV analysis and generation

The main surfaces are:

- `/admin/runs/{run_id}/cv-debug.json`
- `/admin/runs/{run_id}/stage-artifacts.json`
- `/admin/runs/{run_id}/stage-artifacts/cv_analysis.json`
- `/admin/runs/{run_id}/stage-artifacts/cv_generation.json`

Use these to inspect:

- evidence retrieval
- bounded evidence summaries
- gap analysis outcomes
- readiness and skip decisions
- generation validation
- repair behavior
- final generation acceptance or failure

### Timeline and event reasoning

The timeline in run detail and the raw event stream are the best way to inspect:

- stage starts and completions
- checkpoint pauses and continues
- snapshot persistence failures
- agentic fallback or review-related transitions

If something “felt weird” during a run, the timeline is often the fastest way
to locate the exact stage boundary where the behavior changed.

### Mapping suggestions and synonym proposals

The current agentic synonym surfaces are:

- `/admin/runs/{run_id}/mapping-suggestions.json`
- `/admin/mapping-suggestions.json`
- `/admin/synonym-proposals.json`

These let you inspect:

- which aliases were detected from run-scoped evidence
- how those suggestions were grouped into review-ready synonym proposals
- which proposals are still unreviewed versus already actioned

### Settings and runtime context

The main runtime-context surface is:

- `/admin/runs/{run_id}/settings-used.json`

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
5. open `cv-debug.json` if the issue is in analysis or generation
6. open `settings-used.json` if behavior may be config-driven
7. open mapping-suggestion or synonym-proposal exports if the issue is
   taxonomy-related

## What Each Surface Is Good At

- run detail HTML:
  - fast human triage
- raw events:
  - sequence reconstruction and tooling
- stage artifacts:
  - stage-owned truth
- CV debug export:
  - analysis/generation internals
- settings-used export:
  - runtime context and override visibility
- mapping-suggestions and synonym-proposals exports:
  - agentic taxonomy and review surfaces

## Important Boundaries

- run-detail labels are derived views, not the source of semantic truth
- stage artifacts are the primary source for stage-owned decisions
- generated docs in `docs/generated/` explain repo structure, not live run state
- deeper behavioral ownership still lives in `docs/features/` and `docs/stages/`

## Related Docs

- [api.md](api.md)
- [usage.md](usage.md)
- [pipeline.md](pipeline.md)
- [architecture.md](architecture.md)
