---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-phase-1-legacy-surface-and-backend-trim
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md
  - docs/superpowers/specs/2026-07-11-16-56-sqlite-only-control-plane-trim-spec.md
  - docs/superpowers/specs/2026-07-11-23-55-whole-repo-bigquery-full-deletion-spec.md
  - docs/superpowers/specs/2026-07-12-00-20-config-env-yaml-deprecation-and-deletion-spec.md
  - config/env.yaml
  - src/fitcv/config.py
  - src/fitcv/config_loader.py
  - src/fitcv/persistence.py
  - src/fitcv/telemetry.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/bigquery_client.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/settings.html
  - docker-compose.yml
  - start_web.ps1
  - start_worker.ps1
  - docs/api.md
  - docs/configuration.md
  - docs/fitcv-control-plane-setup.md
  - docs/observability.md
  - docs/setup.md
  - docs/usage.md
  - tests/test_config.py
  - tests/test_fitcv/test_telemetry.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_fitcv_cp/test_main.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_reconciler.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_fitcv_cp/test_run_detail_output_availability.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

# Detailed Spec: FitCV SSOT / symmetry Phase 1 legacy-surface and backend trim

## Goal

Execute first concrete remediation lane from
`docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`:

- delete zombie operator/diagnostic surfaces already removed in product truth
- make SQLite-only control-plane truth real in active interfaces
- remove legacy default/config surfaces that keep ambiguous ownership alive

This phase is deletion-first and interface-tightening first. It does not yet
converge stage registry, lifecycle policy, settings metadata, or routing policy.

## Problem

Current repo still has three classes of Phase 1 debt:

1. visually removed or unsupported operator surfaces still leave active residue:
   - `_append_event_dead_letter()`
   - `outbox_replay_health`
   - `event_delivery_health`
   - `settings_mode_summary`
   - `langfuse_link` payload/link-status plumbing, which has no supported
     product/UI/API consumer in current active repo truth
2. SQLite-only truth is cosmetic in some places because active interfaces still
   carry ignored `bq`, `project`, and `dataset` parameters and `BackendRuntime`
   still carries fake BigQuery metadata
3. `config/env.yaml` and related defaults keep config ownership ambiguous even
   after canonical runtime/policy/taxonomy files exist

Until this lane lands, later SSOT work stays noisy because repo still contains
dead projections, fake backend portability, and ambiguous default-entry
surfaces.

## Relationship To Existing Specs

This Phase 1 spec is authoritative only for the bounded first lane from the
master remediation spec.

- `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
  remains parent authority for phase ordering, final target architecture, and
  cross-phase invariants.
- `docs/superpowers/specs/2026-07-11-16-56-sqlite-only-control-plane-trim-spec.md`
  is superseded for the specific control-plane residue deletion and active
  interface-trim work adopted here. Any broader operator-messaging context not
  executed in Phase 1 remains out of scope.
- `docs/superpowers/specs/2026-07-11-23-55-whole-repo-bigquery-full-deletion-spec.md`
  remains authoritative for broader non-control-plane and dependency/manifest
  removal. Phase 1 only severs active control-plane runtime callers from fake
  BigQuery compatibility.
- `docs/superpowers/specs/2026-07-12-00-20-config-env-yaml-deprecation-and-deletion-spec.md`
  remains authoritative for final repo-wide deletion of `config/env.yaml`.
  Phase 1 adopts its path decision and flips all active defaults to `.env.yaml`,
  but keeps explicit deprecated-path handling only during bounded migration.

## Triage

Layer: change
Feature type: REPLACE
Summary: replace zombie operator surfaces and fake backend portability with strict SQLite-only active interfaces and one clear default config-entry contract
Reasoning: Phase 1 should delete unsupported surfaces and trim legacy plumbing before deeper canonical-owner convergence starts
Invariants:
  - supported control-plane backend is SQLite only
  - deleted operator surfaces leave no hidden context, config, payload, route, or test residue
  - one active default config-entry surface is used consistently by loader, UI, scripts, and docs
  - Phase 1 does not redefine stage, lifecycle, settings, or routing canonical owners beyond residue cleanup needed for deletion truth
Dependencies:
  - `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
  - `docs/superpowers/specs/2026-07-12-00-20-config-env-yaml-deprecation-and-deletion-spec.md`
  - current sqlite-backed local workflow
  - current docs/startup/operator surfaces named in targets
Affected stages:
  - none directly
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
    - docs/fitcv-control-plane-setup.md
    - docs/observability.md
    - docs/setup.md
    - docs/usage.md
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

### Deliverable 1: Zombie operator surfaces are fully deleted

All explicitly removed diagnostics/replay surfaces are deleted at code, config,
template, payload, and test level rather than left as hidden residue.

### Deliverable 2: Active control-plane interfaces are SQLite-native

Control-plane runtime/store/worker interfaces no longer accept ignored
`bq`/`project`/`dataset` compatibility parameters, and `BackendRuntime` no
longer pretends BigQuery metadata is part of supported runtime truth.

### Deliverable 3: Default config-entry truth is unambiguous

Repo-root `.env.yaml` is sole active default config-entry surface. Loader
defaults, control-plane defaults, startup scripts, compose, and operator docs
stop using `config/env.yaml` as active default surface.

### Deliverable 4: Phase boundary stays tight

This lane finishes deletion and interface trim only. Stage taxonomy, lifecycle
convergence, settings-schema completion, and routing convergence remain for later
phases.

## Task/Wave Breakdown

### Wave 1: Source-first deletion inventory

**Purpose:**
- turn audit findings into exact delete/keep decisions before touching code

**Steps:**
- [ ] enumerate every removed/operator-dead surface and its remaining owners
- [ ] classify each residue as `delete now` or `explicitly retain with reason`
- [ ] confirm active control-plane interface sites that still carry ignored
      backend parameters
- [ ] confirm current default config-entry path across loader, app, scripts,
      docs, and compose

**Verification:**
- [ ] each deletion target maps to exact source paths and proof method

**Exit Criteria:**
- no implementation step depends on vague “clean up leftovers” wording

### Wave 2: Operator-surface deletion cut

**Purpose:**
- fully remove unsupported diagnostics and replay/dead-letter residue

**Steps:**
- [ ] delete dead-letter/outbox replay residue, including config keys,
      helpers, routes, scripts, tests, and docs
- [ ] delete `event_delivery_health`, `dead_letter_events`, and
      `settings_mode_summary` projections where no supported consumer remains
- [ ] delete `langfuse_link` payload field, `langfuse_link_status()` helper, and
      related tests/docs that survive only as unsupported trace-link health
      contract residue
- [ ] remove empty `runPreflightGuardrails()` and related dead path if no real
      cross-field responsibility is introduced in same lane

**Verification:**
- [ ] removed labels, helper names, route names, payload keys, and config keys
      are absent from active source/docs/tests except approved allowlist

**Exit Criteria:**
- no zombie operator surface remains in active repo paths

### Wave 3: Backend-interface trim

**Purpose:**
- make SQLite-only product direction true in active control-plane signatures

**Steps:**
- [ ] remove `bq`, `project`, and `dataset` from active control-plane app/store/
      sqlite-store/worker/queue/reconciler interfaces
- [ ] shrink `BackendRuntime` to sqlite-native fields only
- [ ] remove `bq_store.py` and `bigquery_client.py` from all supported active
      runtime imports/callers; whole-file deletion stays with whole-repo
      BigQuery deletion unless Phase 1 makes them unreachable and trivial to
      delete safely
- [ ] route shared SQLite path reads through one owner instead of ad hoc env
      reads where Phase 1 touches them

**Verification:**
- [ ] repo search shows no active call path still passes ignored backend
      compatibility args in supported control-plane runtime

**Exit Criteria:**
- active control-plane backend portability is no longer fake

### Wave 4: Config-entry default cleanup

**Purpose:**
- stop ambiguous `config/env.yaml` ownership from surviving as active default

**Steps:**
- [ ] set repo-root `.env.yaml` as sole active default config-entry surface
- [ ] remove `config/env.yaml` as active default from loader, control-plane UI,
      scripts, compose, and operator docs
- [ ] keep only explicit `load_config("config/env.yaml")` deprecated-path
      behavior during bounded migration window; remove implicit default discovery
      for that path in this phase

**Verification:**
- [ ] default path contract is same in loader, UI, scripts, and docs

**Exit Criteria:**
- repo no longer teaches two contradictory config-entry truths

## Design Decisions

### Decision: Phase 1 is delete-first, not architecture-first

- context: repo still has unsupported residue that pollutes later SSOT work
- choice: Phase 1 removes zombie surfaces and trims fake backend portability
  before deeper structural convergence
- alternatives considered:
  - start with stage/lifecycle/settings abstractions first
  - postpone deletions until final cleanup phase
- impact:
  - later phases work against cleaner, truthful surfaces

### Decision: Remove unsupported operator residue fully in one lane

- context: prior trims removed UI labels but left helper/config/payload debt
- choice: when a surface is unsupported, delete all owners in same lane unless a
  supported contract is explicitly retained
- alternatives considered:
  - leave hidden helper functions and payload fields
  - keep replay/dead-letter scripts or routes without visible UI
- impact:
  - no zombie product debt
  - simple grep-based absence proof

### Decision: SQLite-only truth must reach function signatures

- context: repo already resolves SQLite-only backend truth, but active
  interfaces still advertise dead portability through ignored arguments
- choice: remove compatibility args from supported active control-plane runtime
  interfaces in this phase
- alternatives considered:
  - keep compatibility args for convenience
  - wait for larger service/repository rewrite
- impact:
  - less fake abstraction
  - simpler later lifecycle/routing/settings work

### Decision: Keep deeper owner convergence out of Phase 1

- context: stage registry, lifecycle policy, settings completion, and routing
  convergence are real problems, but not needed to delete residue and trim
  interfaces
- choice: do not broaden this lane into Phases 2–4
- alternatives considered:
  - fold stage/lifecycle/settings/routing changes into same execution lane
- impact:
  - smaller diff
  - less cross-phase merge risk

### Decision: `config/env.yaml` stops being taught as current default

- context: ambiguous config-entry truth keeps SSOT drift alive even after backend
  truth is simplified
- choice: Phase 1 removes `config/env.yaml` as active default surface and keeps
  only one truthful default path across loader/UI/scripts/docs
- alternatives considered:
  - keep `config/env.yaml` as permanent compatibility bridge
  - let docs and loader diverge temporarily
- impact:
  - one truthful operator entry point
  - fewer config-path conditionals later

### Decision: repo-root `.env.yaml` is the sole active default path in Phase 1

- context: Phase 1 needs exact default-path contract, not a future choice
- choice: `load_config(None)` resolves repo-root `.env.yaml` only; explicit
  `load_config("config/env.yaml")` remains deprecated-path support for one
  bounded migration window only
- alternatives considered:
  - keep `config/env.yaml` as current default
  - keep two implicit default candidates
- impact:
  - one SSOT default path
  - loader/UI/scripts/docs can be verified uniformly

### Decision: `langfuse_link` is deleted in Phase 1

- context: current active repo has reporter/test residue but no supported
  product/UI/API consumer for this derived health projection
- choice: delete `langfuse_link` payload emission and `langfuse_link_status()`;
  keep native trace IDs and other telemetry fields that still have supported
  owners
- alternatives considered:
  - retain hidden payload field for possible future use
  - keep helper without supported consumer
- impact:
  - removes unsupported derived telemetry contract
  - preserves native telemetry truth instead of custom health projection

## Invariants

- supported control-plane runtime backend is SQLite only
- active control-plane interfaces do not expose ignored backend-compatibility
  parameters
- deleted operator surfaces do not retain route/context/payload/config/test debt
  in active repo paths
- default config-entry truth is same across loader, control-plane UI, scripts,
  compose, and supported docs
- Phase 1 does not introduce second owners for stage, lifecycle, settings, or
  routing concepts
- domain vocabulary like `BigQuery` remains allowed only where it is content,
  not runtime backend infrastructure

## Acceptance Criteria

1. `_append_event_dead_letter`, `outbox_replay_health`, `event_delivery_health`,
   `dead_letter_events`, and `settings_mode_summary` are removed from active
   source unless explicitly retained with named supported contract.
2. Removed diagnostics/replay labels and routes are absent from active templates,
   route code, docs, and tests.
3. `langfuse_link` and `langfuse_link_status()` are removed from active
   reporter/telemetry/test surfaces.
4. Empty `runPreflightGuardrails()` path is deleted unless Phase 1 gives it real
   cross-field responsibility.
5. Active supported control-plane interfaces no longer accept ignored
   `bq`/`project`/`dataset` parameters.
6. `BackendRuntime` and startup/runtime surfaces no longer expose fake BigQuery
   metadata as supported control-plane truth.
7. Repo-root `.env.yaml` is sole active default config-entry surface, and
   `config/env.yaml` is no longer taught or used as implicit default.
8. `bq_store.py` and `bigquery_client.py` are absent from supported active
   runtime imports/callers even if file deletion is deferred.
9. Targeted tests and fast validator pass after planning-lineage refresh.

## Non-Goals

- no stage registry consolidation in this phase
- no lifecycle-policy convergence in this phase
- no full settings-schema enrichment in this phase
- no routing-resolver convergence beyond deleting stale projections and aligning
  default config-entry truth
- no full monolith extraction or service-layer rewrite
- no deletion of domain-skill vocabulary mentioning BigQuery

## Risks and Mitigations

- risk: phase balloons into repo-wide BigQuery or architecture rewrite
  - mitigation: keep only active control-plane interface trim and explicit
    default-config cleanup in scope
- risk: deleted diagnostics still have hidden test or doc references
  - mitigation: require repo-search absence proof plus focused template/app tests
- risk: removing compatibility args breaks untouched call sites
  - mitigation: enumerate all call sites first and patch them in same lane
- risk: config-entry default flip breaks operator workflows
  - mitigation: lock `.env.yaml` now, update scripts/docs/UI together, and keep
    only explicit deprecated-path support during short migration window
- risk: `langfuse_link` deletion removes an undocumented external consumer
  - mitigation: repo-supported contract is delete; if an out-of-repo consumer
    exists it must be reintroduced later as explicit supported contract

## Validation Plan

- proof target: zombie operator surfaces are fully removed
  - method: repo search + focused tests
  - evidence: no active hits for removed helper names, labels, route paths,
    payload keys, and config keys outside approved allowlist

- proof target: active control-plane interfaces are SQLite-native
  - method: repo search + targeted tests
  - evidence: no supported runtime signature or call path still passes ignored
    backend compatibility args; control-plane startup/worker tests remain green

- proof target: default config-entry truth is unambiguous
  - method: inspection + targeted config/app tests
  - evidence: repo-root `.env.yaml` appears as same default path in loader
    behavior, control-plane UI, scripts, compose, and supported docs, while
    `config/env.yaml` appears only in explicit deprecated-path handling if still
    retained during migration

- proof target: active runtime no longer depends on supported BigQuery-style
  control-plane portability
  - method: repo search + targeted tests
  - evidence: no supported active runtime imports/calls `bq_store.py` or
    `bigquery_client.py`; startup, queue, reconciler, and worker tests remain
    green

### Required commands

```powershell
rg -n "_append_event_dead_letter|outbox_replay_health|event_delivery_health|dead_letter_events|settings_mode_summary|langfuse_link_status|langfuse_link|runPreflightGuardrails" src docs tests -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'
rg -n "\bbq\b|project=project|dataset=dataset|GCP_PROJECT|FITCV_CP_DATASET" src/fitcv_cp tests/test_fitcv_cp -g '!src/New folder/**'
rg -n "config/env.yaml|legacy config path in use" src docs tests start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'
py -3 -m pytest tests/test_config.py tests/test_fitcv/test_telemetry.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_main.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reporter.py tests/test_fitcv_cp/test_run_detail_output_availability.py tests/test_fitcv_cp/test_worker_job.py -q
py -3 scripts/generate_planning_lineage.py
py -3 scripts/hooks/run_validator.py --fast
```

- proof target: planning and docs stay coherent after new spec
  - method: generation + validator run
  - evidence: `python scripts/generate_planning_lineage.py` and
    `python scripts/hooks/run_validator.py --fast` both pass

## Completion Criteria

1. all Key Deliverables are satisfied
2. implementation plan can execute deletion + interface trim without reopening
   stage/lifecycle/settings/routing design
3. later phases may assume zombie surfaces and fake backend portability are gone
4. every child item is `completed`, `superseded`, or `dropped`

Canonical source-of-truth:

- `docs/superpowers/specs/2026-07-12-01-17-fitcv-ssot-symmetry-master-remediation-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `scripts/validate_planning_lifecycle.py`
