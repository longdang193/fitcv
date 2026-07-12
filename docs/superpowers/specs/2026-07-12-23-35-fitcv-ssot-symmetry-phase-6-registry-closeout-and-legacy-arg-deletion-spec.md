---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-ssot-symmetry-phase-6-registry-closeout-and-legacy-arg-deletion
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv/config.py
  - src/fitcv/late_stage_contract.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/backend_runtime.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/worker_job.py
  - scripts/backfill_live_run_artifacts.py
  - tests/test_config.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_worker_job.py
related_features: []
related_stages: []
---

# Detailed Spec: FitCV SSOT / symmetry phase 6 registry closeout and legacy arg deletion

## Goal

Close remaining source-first SSOT and symmetry gaps left after Phases 1-5 without reopening big architecture rewrite.

This phase finishes four small but still-live problem classes:

- dead runtime-alignment residue still rendered in settings logic
- obsolete SQLite-vs-BigQuery config residue still accepted or named
- control-plane persistence helpers still shaped around `project` / `dataset` compatibility args
- stage, artifact, and lifecycle presentation still depend on parallel hardcoded maps instead of one derived registry

## Key Deliverables

### Deliverable 1: residue and active-script drift are closed

Removed runtime-alignment residue is deleted, the active live-run backfill script no longer depends on `bq_store`, and legacy backend naming is either deleted or downgraded to one explicit ingress-only compatibility behavior.

### Deliverable 2: active control-plane runtime stops exposing legacy backend shape

Public and active runtime-facing control-plane helpers no longer require `project` / `dataset` compatibility args, and any remaining local shim is explicit, isolated, and documented.

### Deliverable 3: stage/artifact presentation has one explicit owner

One small control-plane registry owner defines stage order and artifact file metadata used by bundle/download/status surfaces, so equivalent presentation paths derive from one source.

### Deliverable 4: settings boundary derivation is tightened without new registry

`SETTINGS_SCHEMA` remains canonical, while native numeric attrs and settings control-surface projections are derived from explicit schema metadata or one schema-owned projection helper rather than suffix folklore and ad hoc card filters.

## Problem

Repo moved far, but current source still has unsolved leftovers:

- `_resolve_mode_summary()` still exists in `src/fitcv_cp/app.py` even though removed alignment panel should no longer own a parallel truth surface
- obsolete key `bigquery_dataset` still survives in `src/fitcv/config.py`
- active control-plane helpers still carry `project` and `dataset` compatibility signatures in `app.py`, `worker_job.py`, and `sqlite_store.py`
- active script `scripts/backfill_live_run_artifacts.py` still imports `bq_store` and branches on `runtime.backend_type == "bigquery"`
- stage order, labels, timeline groupings, artifact availability, and artifact filenames still rely on multiple separate maps and `if filename == ...` branches inside `app.py`
- settings schema is better than before, but native input attrs and control-surface ownership are still only partly derived from canonical setting definitions

These are no longer review-only complaints. They are real remaining code owners that can drift independently.

## Non-Goals

- no new `AppServices` tree
- no FastAPI router breakup unless one tiny extraction is strictly smaller than current code
- no persistence schema migration
- no repo-wide deletion of historical one-off BigQuery migration scripts unless they are imported by active runtime or active tooling
- no redesign of pipeline semantics, CV quality policy, or run lifecycle behavior

## Triage

Layer: change
Feature type: REPLACE
Summary: replace final control-plane compatibility residue and parallel registry maps with one derived closeout path built from existing owners.

## Existing Owners To Reuse

- `SETTINGS_SCHEMA` in `src/fitcv_cp/settings_schema.py`
- `late_stage_contract.py` in `src/fitcv/late_stage_contract.py`
- `resolve_model_routing_part(...)` and current routing/runtime helpers
- `RunStatus` and existing lifecycle action predicates
- current `RunArtifactFile` shape in `src/fitcv_cp/app.py`

Phase 6 must tighten these. Do not invent parallel service or metadata trees.

## Task/Wave Breakdown

### Wave 1: delete dead residue and obsolete active script drift

**Purpose:**
- remove leftover surfaces that no longer own any live product behavior

**Steps:**
- [ ] delete `_resolve_mode_summary()` and its remaining settings-page note composition if that note is only serving removed runtime-alignment presentation
- [ ] keep trigger-time runtime envelope and settings-used truth notes; only remove parallel alignment-summary logic
- [ ] define final `bigquery_dataset` behavior explicitly: ingress-only legacy key is accepted and dropped before normalized config is returned, with no active runtime consumer and no user-facing control-plane surface
- [ ] do not create a second config path for that key; either keep one explicit ingress-drop shim in `src/fitcv/config.py` or delete it entirely if current fixture coverage proves no compatibility need
- [ ] patch `scripts/backfill_live_run_artifacts.py` to use active SQLite store path and active runtime assumptions instead of `bq_store` imports and `project` / `dataset` plumbing

**Verification:**
- [ ] settings page tests still prove current operator copy and no removed alignment panel residue
- [ ] config tests prove the chosen `bigquery_dataset` contract exactly: accepted-and-dropped or rejected-with-clear-error
- [ ] backfill script verification is executable: run one stale-run repair command against SQLite-backed local state and prove mirror/export repair without importing `fitcv_cp.bq_store`

**Exit Criteria:**
- no active runtime-facing source path in `src/` or active `scripts/` depends on removed alignment-summary surface or BigQuery-only store imports

### Wave 2: delete `project` / `dataset` compatibility signatures from active control-plane runtime

**Purpose:**
- make SQLite-only product direction visible in function shape, not only in resolved runtime values

**Steps:**
- [ ] first remove `project` / `dataset` from active script and public runtime-facing wrappers that still expose them through the control-plane path
- [ ] then remove matching pass-through kwargs from local helper families in `app.py`, `worker_job.py`, and `sqlite_store.py` only where all direct callers are updated in the same patch
- [ ] if one temporary local shim is smaller than full same-phase leaf cleanup, keep exactly one internal shim and list its owner explicitly rather than forcing repo-wide grep-zero by accident
- [ ] do same cleanup for `scripts/backfill_live_run_artifacts.py`
- [ ] leave inactive historical migration scripts alone unless Phase 6 touches them directly

**Verification:**
- [ ] app, worker, and sqlite-store tests still pass after wrapper and direct-caller cleanup
- [ ] grep-based regression check proves no public control-plane runtime boundary or active script passes `project=` or `dataset=`
- [ ] if one temporary internal shim remains, one test and one source comment lock that it is local-only and non-user-facing

**Exit Criteria:**
- active public control-plane runtime path is SQLite-shaped end to end, and any remaining local shim is explicit and isolated rather than ambient

### Wave 3: one stage/artifact registry for control-plane presentation

**Purpose:**
- stop duplicating stage order, stage labels, artifact availability, and artifact filenames across separate maps and `if` chains

**Steps:**
- [ ] introduce one small registry owner for control-plane presentation using existing stage IDs and existing artifact names, not new semantics
- [ ] registry contract is explicit and implementation-bounded:
  - `ControlPlaneStageSpec`: `stage_id`, `order`, `label`, `bundle_json_filename` or `None`
  - `ControlPlaneArtifactSpec`: `filename`, `label`, `bundle_member`, `stage_id` optional, `availability_kind`
- [ ] `availability_kind` is declarative, not ad hoc; choose from a small closed set such as `succeeded_results`, `cv_debug_required`, `late_stage_trace`, `stage_artifact`, `mapping_snapshot`, `synonym_snapshot`, or equivalent final names documented in code
- [ ] registry must derive at least:
  - stage order used by timeline/support helpers
  - operator-facing stage labels
  - artifact filename list and labels
  - artifact availability/status checks currently split across `_build_available_run_artifact_files(...)` and filename-switch helpers
- [ ] keep registry local and boring; one tuple/list of typed dicts or dataclass rows is enough
- [ ] derive current stage loops such as `("enrich", "ranking", "cv_analysis", "cv_generation")` from registry rather than retyping tuples
- [ ] derive `cv-generation-review-required.json`, `cv-debug.json`, `settings-used.json`, `stage-artifacts.json`, `agentic-live-trace.json`, and `cv-analysis-trace.json` from same owner

**Verification:**
- [ ] existing artifact download tests still pass unchanged at route boundary
- [ ] new registry invariant test proves stage IDs unique, artifact filenames unique, and displayed order stable
- [ ] grep of `app.py` no longer finds duplicate hardcoded stage tuples and parallel artifact filename switches outside registry owner

**Exit Criteria:**
- one small registry drives stage and artifact presentation surfaces in control plane

### Wave 4: finish settings-schema boundary derivation where drift still exists

**Purpose:**
- make current settings surface more honestly schema-driven without redesigning the page again

**Steps:**
- [ ] target exact current drift owners first: `settings_native_input_attrs(...)` numeric suffix heuristics and section/card key filtering in the settings-page projection helpers
- [ ] move remaining native HTML attr heuristics from suffix-based inference to explicit schema-owned metadata where practical
- [ ] ensure every grouped/sectioned/control-surface key comes from schema-owned metadata or one schema-derived projection, not hand-maintained side maps such as suffix-filtered card builders
- [ ] do not create a second settings registry; enrich `SETTINGS_SCHEMA` or its existing helper projections only
- [ ] keep rendered form behavior same unless a current mismatch is proven and fixed in same patch

**Verification:**
- [ ] settings schema tests prove section/group/control-surface membership and native attrs are schema-derived
- [ ] save/load round-trip tests still preserve typed values

**Exit Criteria:**
- settings page boundary behavior is more fully derived from canonical settings definitions, not suffix folklore

## Design Decisions

### Decision: close out with deletion first, then tiny registry extraction

- context: remaining issues are mostly residue and parallel maps, not missing abstraction
- choice: delete dead surfaces and obsolete args first; only then introduce one tiny registry for stage/artifact presentation
- alternatives considered:
  - big service rewrite
  - keep patching per-call-site drift
- impact:
  - smaller diff
  - clearer proof that SSOT improved rather than moved

### Decision: active runtime and active scripts first, historical scripts later

- context: many old migration/bootstrap scripts still mention BigQuery, but not all are product-path blockers
- choice: Phase 6 patches active runtime and active operator tooling first; historical one-off scripts stay out unless imported or used in current workflow
- alternatives considered:
  - repo-wide script purge in same lane
- impact:
  - bounded scope
  - less noise in same patch

### Decision: derive from existing owners, not new domain trees

- context: review diagnosis was strong, but `AppServices` / repository tree proposal was too big for current closeout lane
- choice: reuse `SETTINGS_SCHEMA`, `RunStatus`, current artifact file shape, and existing late-stage contracts
- alternatives considered:
  - introduce new service registry hierarchy
- impact:
  - lower churn
  - less parallel architecture

## Design Decisions

### Decision: `bigquery_dataset` is boundary compatibility, not runtime truth

- context: current loader tests already expect `bigquery_dataset` to disappear from normalized config, but source still names it as an obsolete ingress key
- choice: Phase 6 must pick one explicit behavior and test it; preferred shape is ingress-only accept-and-drop with no downstream runtime consumer
- alternatives considered:
  - immediate hard error on presence
  - silent ambient acceptance with downstream residue
- impact:
  - keeps boundary adaptation explicit
  - avoids parallel backend truth inside runtime

### Decision: Phase 6 removes public legacy args first, then local leaf residue

- context: full same-phase grep-zero over every internal caller may sprawl if enforced blindly
- choice: public wrappers and active scripts lose `project` / `dataset` first; local leaf cleanup follows only where covered in same patch, otherwise one explicit local shim is allowed temporarily
- alternatives considered:
  - repo-wide hard delete in one pass
  - leave legacy args ambient everywhere
- impact:
  - smaller safe diff
  - no hidden user-facing compatibility leakage

### Decision: one boring presentation registry beats parallel maps

- context: stage/artifact drift now comes from repeated tuples, repeated `RunArtifactFile(...)` rows, and filename switches
- choice: add one small owner with explicit row shapes for stage and artifact presentation metadata, then derive current app helpers from it
- alternatives considered:
  - keep current maps and add tests only
  - introduce broad service or metadata tree
- impact:
  - one SSOT for equivalent presentation semantics
  - less route/download/bundle drift

### Decision: settings cleanup is limited to named boundary helpers

- context: settings surface already has useful schema ownership, but a few boundary helpers still infer semantics from key suffixes and card-specific filters
- choice: patch `settings_native_input_attrs(...)` and current settings-page projection helpers only; do not redesign IA or create a new settings registry
- alternatives considered:
  - full settings page redesign
  - leave suffix folklore in place
- impact:
  - bounded fix
  - better schema-driven boundary behavior

## Invariants

- no active `src/fitcv_cp/` runtime path depends on `bq`, `project`, or `dataset` arguments
- no active product/runtime config key named `bigquery_dataset` remains in accepted control-plane config path
- every control-plane stage ID is declared once in registry owner
- every downloadable artifact filename is declared once in registry owner
- artifact availability/status logic is derived from registry owner plus run state, not parallel filename switches
- settings native attrs and control-surface ownership are schema-derived or explicitly documented as intentional compatibility projection
- Phase 6 introduces no new broad architecture layer

## Validation Plan

- proof target: removed runtime-alignment residue stays gone
  - method: settings-page tests plus source grep for `_resolve_mode_summary`
  - evidence: no live helper or rendered copy depends on that summary surface
- proof target: `bigquery_dataset` behavior is explicit and stable
  - method: `tests/test_config.py`
  - evidence: test proves chosen accept-and-drop or reject-with-error contract exactly
- proof target: active script and public wrappers no longer expose BigQuery-era shape
  - method: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`, `tests/test_fitcv_cp/test_sqlite_store.py`, plus grep over active `src/fitcv_cp/` wrappers and `scripts/backfill_live_run_artifacts.py`
  - evidence: no active public control-plane path or active script passes `project=` / `dataset=`
- proof target: stage/artifact presentation is registry-driven
  - method: artifact download tests plus one new invariant test
  - evidence: stage IDs unique, artifact filenames unique, displayed order stable, and `app.py` no longer owns parallel hardcoded stage tuple + filename switch logic outside registry owner
- proof target: settings boundary behavior is schema-driven where touched
  - method: `tests/test_fitcv_cp/test_settings_schema.py`
  - evidence: native attrs and section/card ownership come from explicit schema metadata or one schema-owned projection helper

## Completion Criteria

A Phase 6 item is complete when:

1. all Key Deliverables are satisfied
2. all Validation Plan proof targets are green
3. public control-plane runtime and active script surfaces no longer expose legacy backend shape
4. any intentionally retained local shim or ingress-only compatibility drop is explicit, tested, and documented as boundary-only

## Follow-Up

- if Phase 6 still leaves large monolith pain after registry closeout, next lane may target `pipeline.py` or broader settings simplification separately
- do not fold that future work into Phase 6 unless current bounded spec proves insufficient
