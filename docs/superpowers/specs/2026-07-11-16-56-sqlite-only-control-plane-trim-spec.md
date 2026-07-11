---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: sqlite-only-control-plane-trim
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - src/fitcv_cp/main.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/bigquery_client.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/data_plane.py
  - src/fitcv_cp/store.py
  - config/runtime/control_plane.yaml
  - docker-compose.yml
  - start_web.ps1
  - start_worker.ps1
  - scripts/check_outbox_replay_health.py
  - scripts/route_outbox_replay_health_alert.py
  - docs/api.md
  - docs/configuration.md
  - docs/usage.md
  - docs/observability.md
  - docs/fitcv-control-plane-setup.md
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Detailed Spec: SQLite-only control-plane trim

## Goal

Define smallest safe product-direction change that makes SQLite the only supported
control-plane backend, removes dead or over-engineered operator diagnostics UI,
and sets explicit deletion rules for remaining BigQuery and observability debt.

This spec is not a generic storage refactor. It is a product-direction cut:
remove backend portability as a supported story, trim operator surfaces that the
project will not invest in, and keep only the runtime/reporting pieces that still
serve a real local workflow.

## Triage

Layer: change
Feature type: REPLACE
Summary: replace dual-backend control-plane direction with sqlite-only product direction and trim operator diagnostics surfaces that are hidden, low-value, or over-engineered
Reasoning: current repo already defaults local runtime to sqlite, while BigQuery and advanced diagnostics keep cross-cutting code, docs, tests, and UI complexity alive for product paths the owner does not want to develop further
Invariants:
  - local web + worker startup must work without BigQuery credentials
  - sqlite remains the single authoritative control-plane persistence backend
  - run trigger, run list, run detail, archive/unarchive, events, settings, synonym review, and enriched detail must keep current local behavior
  - hidden UI must not keep live backend computation or routes alive without a consumer
  - removed diagnostics must not leave broken template context references
  - deletion order must preserve a green sqlite-local verification path at each step
Dependencies:
  - current sqlite-backed control-plane store behavior
  - current docker/local startup scripts
  - current run-detail template sections and route context builders
Affected stages:
  - none
Affected features:
  - none
Primary lens: cross-cutting
Affected docs:
  feature_source: none
  feature_yaml: none
  feature_lineage: none
  feature_history: none
  stage_source: none
  stage_contract: none
  feature_docs: []
  cross_cutting_docs:
    - docs/api.md
    - docs/configuration.md
    - docs/usage.md
    - docs/observability.md
    - docs/fitcv-control-plane-setup.md
  readme: none
  generated: []
Generated refresh required: no
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: Product direction becomes explicitly sqlite-only

The codebase, docs, and startup surfaces must stop presenting BigQuery as a
supported control-plane runtime backend.

### Deliverable 2: Dead and overbuilt diagnostics surfaces are removed

Hidden runs-list replay health UI, outbox replay health automation surfaces,
explicitly removed run-detail diagnostics cards, and any audited control-plane
element marked as having no active script/operator usage must be removed
together with their now-unneeded routes, scripts, docs, tests, and context
plumbing.

### Deliverable 3: BigQuery deletion is staged, not half-removed

The repo must define a bounded deletion sequence so BigQuery support is not left
in a misleading half-supported state.

## Acceptance Criteria

1. Operator-facing docs and startup surfaces state SQLite-only control-plane support.
2. `start_web.ps1`, `start_worker.ps1`, and `docker-compose.yml` run with sqlite defaults and do not require BigQuery credentials for supported paths.
3. Hidden Outbox Replay Health UI, `/admin/outbox-replay-health.json`, `/admin/outbox-replay-health/check`, and their supporting scripts/docs/tests are removed together.
4. Run-detail cards for Event Delivery Health, Telemetry Export Health, Langfuse Trace-Link Health, Agentic Runtime Alignment, and Dead-letter Replay Summary are removed.
5. UI for removed diagnostics is deleted fully, including headings, buttons, download links, labels, helper copy, hidden blocks, and any template-only styling or context wiring that exists only for those surfaces.
6. Within this audited trim scope, any control-plane UI, route, script, or test marked by repo review as having no active script/operator usage is deleted now rather than kept behind hidden UI or soft deprecation.
7. `POST /admin/runs/{run_id}/replay-dead-letter-events`, its tests, and stale doc mentions are removed together because no active script/operator usage was found in the repo.
8. BigQuery code paths are either fully retained for temporary migration-only compatibility with explicit deprecation language, or fully deleted in the planned removal lane; no silent “maybe supported” state remains.
9. SQLite-local control-plane regression coverage remains green after each execution slice.

## Non-Goals

- no migration to another remote DB backend
- no redesign of run detail layout beyond removing selected cards
- no new observability feature work
- no attempt to preserve BigQuery as a secondary “advanced” mode for power users
- no generic abstraction layer for future backends

## Task/Wave Breakdown

### Wave 1: Direction lock and dead UI removal

**Purpose:**
- remove dead/hidden operator surfaces and lock product narrative to sqlite-only before deeper backend deletion

**Steps:**
- [ ] remove hidden Outbox Replay Health runs-list block
- [ ] remove `/admin/outbox-replay-health.json` route
- [ ] remove `/admin/outbox-replay-health/check` route
- [ ] remove `scripts/check_outbox_replay_health.py` and `scripts/route_outbox_replay_health_alert.py`
- [ ] remove runs-list dead-letter replay aggregate computation when route/script removal leaves it unused
- [ ] remove run-detail cards for Event Delivery Health, Telemetry Export Health, Langfuse Trace-Link Health, Agentic Runtime Alignment, and Dead-letter Replay Summary
- [ ] remove UI leftovers for those surfaces, including headings, download links, helper copy, hidden blocks, and template-only CSS/hooks
- [ ] remove any other audited control-plane element in this trim scope tagged `No active script/operator usage found`
- [ ] remove `POST /admin/runs/{run_id}/replay-dead-letter-events` because no active repo script/operator usage was found
- [ ] remove replay/outbox endpoint tests and stale practical doc mentions in same slice
- [ ] remove template/context plumbing that exists only for those removed diagnostics surfaces
- [ ] update docs/startup text to say sqlite-only is supported direction

**Verification:**
- [ ] runs list renders without hidden dead-health plumbing
- [ ] run detail renders without removed card context
- [ ] local sqlite startup docs/scripts remain truthful

**Exit Criteria:**
- operator UI no longer advertises or computes dead surfaces with no product future

### Wave 2: BigQuery support deprecation boundary

**Purpose:**
- make temporary BigQuery retention explicit and bounded instead of accidental

**Steps:**
- [ ] identify every active BigQuery runtime entrypoint, helper, route assumption, and test family
- [ ] decide whether any temporary compatibility window is needed
- [ ] if temporary retention remains, mark BigQuery as deprecated-in-source and unsupported in docs
- [ ] define exact delete targets for final removal lane

**Verification:**
- [ ] no doc or startup path describes BigQuery as supported product direction
- [ ] temporary retained code, if any, has explicit removal boundary

**Exit Criteria:**
- BigQuery is either unsupported-and-marked or scheduled for immediate deletion with bounded scope

### Wave 3: SQLite-only backend removal lane

**Purpose:**
- delete backend portability code in one coherent pass once docs/UI are already aligned

**Steps:**
- [ ] remove BigQuery runtime selection from startup/runtime resolver
- [ ] remove BigQuery client/bootstrap code
- [ ] collapse control-plane store to sqlite-only authority
- [ ] remove BigQuery-specific tests and parity expectations
- [ ] simplify docs/config that currently describe backend dual-mode behavior

**Verification:**
- [ ] sqlite-only startup and regression suite pass
- [ ] no supported code path references BigQuery backend selection
- [ ] docs no longer claim backend portability

**Exit Criteria:**
- control plane is structurally sqlite-only, not merely sqlite-by-default

## Design Decisions

### Decision: Remove all operator diagnostics surfaces with no desired product future

- context: owner explicitly does not want to keep investing in orchestration/advanced diagnostics, and repo search found no active practical operator/script usage for the per-run replay surface or the run-detail diagnostics cards being discussed
- choice: delete those UI and repair surfaces now rather than carry a deprecation banner, hidden card shell, or internal-only endpoint set
- alternatives considered:
  - keep hidden UI and defer cleanup
  - show cards behind a feature flag
  - mark cards deprecated but leave rendering and context live
- impact:
  - shortest safe diff removes dead template branches, routes, scripts, docs, tests, and context work together
  - operator surface becomes smaller and more truthful immediately

### Decision: Do not keep long deprecation for internal over-engineered surfaces

- context: these surfaces are internal operator tooling, not public API contracts with external integrators
- choice: remove dead/overbuilt UI directly; use spec/plan/docs as the deprecation record instead of shipping long-lived compatibility shims
- alternatives considered:
  - one-release soft deprecation with warnings
  - config toggle to re-enable removed cards
- impact:
  - less maintenance debt
  - no fake promise that these surfaces remain supported

### Decision: Treat BigQuery removal as a dedicated coherent lane

- context: BigQuery support is spread across startup, runtime resolution, storage helpers, worker behavior, docs, and many tests
- choice: lock product direction now, then delete BigQuery in a dedicated backend-removal lane rather than mixing all deletion into the first UI trim patch
- alternatives considered:
  - delete BigQuery in same pass as UI trim
  - leave BigQuery indefinitely as unsupported hidden complexity
- impact:
  - first pass stays small and low-risk
  - final removal still has explicit bounded scope

### Decision: Remove replay and outbox health surfaces in same slice

- context: owner now wants both replay and outbox replay health gone, including supporting automation; these surfaces are advanced operational plumbing rather than core local-product value
- choice: remove Telemetry Export Health, Outbox Replay Health, the Dead-letter Replay Summary card, the per-run replay endpoint, and any other audited trim-scope element marked with no active script/operator usage, together with dependent UI blocks, routes, scripts, tests, and stale practical doc mentions
- alternatives considered:
  - keep backend route without UI
  - keep scripts but remove UI
  - add visible buttons and friendlier wording
- impact:
  - deletes unsupported repair plumbing instead of making it more official
  - removes dead-letter/outbox replay state from templates, routes, scripts, docs, and tests in one bounded cut

## Invariants

- sqlite is single supported control-plane backend after this change direction is applied
- supported local workflow must not depend on GCP credentials or BigQuery schema state
- no hidden or removed UI section may retain live route/context/script debt without a consumer
- replay/outbox removal and no-active-usage sweep must include their cards/routes/scripts/tests and stale practical doc mentions in same slice
- template removals must include adjacent UI copy, links, and styling hooks that exist only for removed surfaces
- template removals must be matched by route-context removals in same execution lane
- docs must describe only supported product direction, not historical optionality
- if BigQuery remains temporarily in source, it must be explicitly unsupported and bounded for later deletion

## Risks and Mitigations

- risk: partial BigQuery removal leaves source in ambiguous half-supported state
  - mitigation: keep first pass to direction/docs/UI trim; do backend deletion in one dedicated follow-up lane
- risk: removed run-detail cards still have tests or template context dependencies
  - mitigation: delete UI and paired context/tests together from same owner paths
- risk: repo search misses an external human workflow that calls replay or outbox health endpoints/scripts manually
  - mitigation: remove stale in-repo docs/tests now, but mention external-usage uncertainty in plan and commit note
- risk: docs drift from code during staged removal
  - mitigation: update sqlite-only narrative in same pass as startup/UI trim, then finish backend-doc cleanup in deletion lane

## Validation Plan

- proof target: sqlite-only direction is explicit in supported operator/runtime surfaces
  - method: inspection
  - evidence: updated `docs/api.md`, `docs/configuration.md`, `docs/usage.md`, `start_web.ps1`, `start_worker.ps1`, `docker-compose.yml`

- proof target: hidden runs-list replay health and supporting automation are fully removed
  - method: inspection + route/script test removal verification
  - evidence: no `{% if false %}` block, no `Outbox Replay Health (Visible Runs)` label, no `/admin/outbox-replay-health.json` download link, no `/admin/outbox-replay-health.json`, no `/admin/outbox-replay-health/check`, no outbox replay health scripts, and related tests/docs updated or deleted

- proof target: run-detail no longer renders removed diagnostics cards or replay summary
  - method: template inspection + route tests
  - evidence: `run_detail.html` no longer contains Event Delivery Health, Telemetry Export Health, Langfuse Trace-Link Health, Agentic Runtime Alignment, or Dead-letter Replay Summary sections, or template-only helpers that exist only to render them; run-detail tests pass

- proof target: audited no-active-usage surfaces are fully removed from this trim scope
  - method: repo search + template/route/script removal verification
  - evidence: no retained trim-scope surface still justified only by hidden UI or stale internal tooling after being marked `No active script/operator usage found`

- proof target: per-run replay endpoint is fully removed because no active repo script/operator usage was found
  - method: repo search + route removal verification
  - evidence: no `/replay-dead-letter-events` route, no caller scripts, endpoint tests deleted or replaced, stale practical docs removed

- proof target: supported local startup path does not require BigQuery credentials
  - method: inspection + targeted startup tests
  - evidence: sqlite startup tests for `fitcv_cp.main` and PowerShell startup scripts remain green/truthful

- proof target: BigQuery removal lane is bounded and non-ambiguous
  - method: comparison
  - evidence: implementation plan lists exact delete targets and verification scope for backend deletion lane

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. downstream implementation plan exists with separate slices for immediate UI/docs trim and backend-removal lane
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

