---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Scale run detail for large runs by making the page summary-first, tab data lazy-loaded, and status polling lightweight."
invariants:
  - "Run detail initial render must not depend on loading full enriched-job, filter-result, or CV-version tables."
  - "Auto-refresh must only use a lightweight status endpoint and must not trigger overlapping polls."
  - "Heavy inspection data must be paginated server-side before it is rendered in the browser."
  - "Run-detail exports and stage diagnostics must remain available without requiring heavy tables to be preloaded."
---

# Large Run Detail Lazy Loading and Status Polling

## Related Feature Contracts

- [inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/docs/features/trigger_run_management/trigger_run_management.yaml)

## Triage

Feature type: MODIFY  
Summary: Scale run detail so runs with hundreds or thousands of jobs remain responsive by separating lightweight status/summary rendering from heavy inspection data loading.  
Reasoning: Existing run detail behavior is correct for small runs but becomes brittle as job count grows because the page eagerly loads expensive tables and diagnostics while also polling the backend.  
Invariants:
- Run detail initial paint must stay fast for runs with `500+` jobs.
- Run polling must never repeatedly fetch heavy data.
- Inspection tabs must remain useful for debugging, but their cost must be user-driven and bounded.
- Large run support must preserve current diagnostic richness rather than deleting visibility.
Dependencies:
- `inspection_debugging`
- `trigger_run_management`
- current run-detail and run-list control-plane routes in `fitcv_cp`
Affected stages:
- normalize
- enrich
- rule_filter
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- inspection_debugging
- trigger_run_management
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `docs/features/trigger_run_management/history.md`
  cross_cutting_docs: none
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

Run detail currently mixes three very different workloads into one page request:

1. Lightweight run state and lifecycle controls
2. Medium-cost diagnostic summaries such as run health and stage artifacts
3. Heavy inspection tables such as enriched jobs, filter results, and generated CV outputs

That coupling is survivable for runs with `~10` jobs, but it does not scale cleanly to runs with `500` or `1000` jobs. Symptoms include:

- run detail feeling stuck or constantly "waiting for localhost"
- repeated polling against a route that is heavier than it needs to be
- large HTML payloads and browser rendering cost
- slow tab switching because all tables were already rendered up front
- expensive repeated reads against run-scoped tables for every visit and refresh

## Design Goals

- Keep run detail usable for very large runs without sacrificing diagnostics
- Make the first paint fast and predictable
- Ensure polling only touches tiny status data
- Load expensive inspection data only when the user asks for it
- Bound large-table rendering with server-side pagination
- Preserve stage artifacts, exports, and run health as first-class diagnostics

## Recommended Model

The best scaling model is:

- **run detail = summary shell**
- **tabs = lazy-loaded detail**
- **tables = server-side pagination**
- **polling = tiny status-only endpoint**

This keeps the page operationally useful while preventing large-run inspection from turning into a monolithic render.

## Proposed Contract

### 1. Run Detail Initial Render

The initial HTML response for [run_detail.html](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-0/src/fitcv_cp/templates/run_detail.html) should include only:

- run header and lifecycle actions
- run summary card
- run exports
- run health
- synonym overlay card
- compact timeline slice
- empty inspection panes with loading hooks

The initial render must **not** eagerly load:

- full enriched jobs table
- full filter results table
- full CV versions table
- large run-results projections beyond what is needed for summary/header cards

### 2. Lightweight Status Endpoint

The polling endpoint at `/runs/{run_id}` should remain intentionally small and status-only.

Allowed fields:

- `run_id`
- `status`
- `run_mode`
- `checkpoint_status`
- `last_completed_stage`
- `next_stage`
- `started_at`
- `finished_at`
- top-line count fields only if already cheap and directly stored on the run row

It must **not**:

- parse or return stage artifacts
- parse effective settings
- query run-structured-jobs
- query filter-results
- query CV versions

### 3. Smarter Polling Behavior

Client polling should:

- run only for live statuses:
  - `queued`
  - `running`
  - `cancelling`
- not poll for:
  - `awaiting_continue`
  - `succeeded`
  - `failed`
  - `cancelled`
- use a conservative interval such as `10-15s`
- never overlap requests
- pause while the tab is hidden
- reload the page only when real state changes occur

This turns polling into state monitoring rather than pseudo-live page re-rendering.

### 4. Lazy-Loaded Inspection Tabs

The following tab content should load only when opened:

- `Enriched Jobs`
- `Original Job Input`
- `Candidate Profile`
- optionally a separate `Generated CVs` or `Outputs` tab if the feature continues to grow

Recommended route shape:

- `/admin/runs/{run_id}/inspection/enriched-jobs`
- `/admin/runs/{run_id}/inspection/original-job-input`
- `/admin/runs/{run_id}/inspection/candidate-profile`

The server may return:

- HTML fragments for drop-in rendering, or
- JSON payloads rendered client-side

Preferred default:

- HTML fragments for consistency with the existing control-plane templating style

### 5. Server-Side Pagination for Large Tables

Heavy tables must move to server-side pagination.

Required for:

- enriched jobs
- filter-result-backed inspection rows
- timeline once event count becomes large
- CV version list if it grows materially

Recommended defaults:

- page size `25` or `50`
- server-side search/query filtering
- explicit total counts

The browser must never render all `500+` jobs in the first response.

### 6. Timeline Strategy

Timeline should remain visible on first paint, but bounded.

Recommended behavior:

- show latest `25` or `50` rows first
- add `Load more` or paginated older slices
- preserve stage-download ownership on aggregate stage rows

This keeps timeline useful without making it the dominant payload for long runs.

### 7. Run Health Remains First-Class

Run health stays in the initial shell because it is compact and high value.

But it must continue to be computed from:

- stage-transition artifacts
- compact metric rows

And not depend on loading heavy tab content.

### 8. Exports Remain Available Without Table Prefetch

Exports should continue to work independently of lazy tabs.

That means:

- run exports remain available from run-owned snapshots and stage artifacts
- users do not need to open `Enriched Jobs` or `Outputs` first
- stage diagnostics stay decoupled from large inspection table rendering

## Data Ownership After This Change

### Summary Shell Owns

- run row metadata
- lifecycle actions
- exports
- run health
- top-level timeline slice

### Lazy Tabs Own

- enriched job inspection rows
- filter-backed inspection detail
- large raw snapshots meant for browsing
- potentially generated-output browsing

### Polling Owns

- state transition detection only

## Why This Is the Best Design

This design scales both backend and frontend cost:

- small payload on first paint
- small payload during polling
- expensive data only loaded on demand
- large tables bounded with pagination

It also preserves the current product model:

- run detail remains the control center
- diagnostics remain rich
- users can still inspect stage results deeply
- exports remain explicit and reliable

The change is therefore an architectural separation, not a feature reduction.

## Non-Goals

This spec does not require:

- removing run health
- removing timeline
- deleting inspection tabs
- replacing stage artifacts
- rewriting the control plane into a client-heavy SPA

## Risks

### Risk: More routes and partials

Mitigation:

- keep the shell simple
- use a small number of fragment endpoints
- reuse existing render helpers

### Risk: Users may expect immediate tab content

Mitigation:

- show loading skeletons/spinners
- keep the first request fast enough that the tradeoff is clearly worth it

### Risk: Partial endpoint/query duplication

Mitigation:

- centralize table query helpers
- keep tab payload contracts narrow and paginated

## Recommended Rollout Order

1. Keep the existing run detail route, but remove eager heavy-table loading from first paint
2. Add lazy-loaded tab endpoints
3. Add server-side pagination and search for enriched jobs
4. Bound timeline rendering
5. Tune polling interval and visibility behavior if needed

## Expected Outcome

After this change:

- a run with `10` jobs still feels fine
- a run with `500` jobs remains responsive
- a run with `1000` jobs does not require rendering or shipping all jobs at once
- polling stops feeling like the page is stuck or constantly waiting on localhost

