---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: config-env-yaml-deprecation-and-deletion
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
targets:
  - config/env.yaml
  - src/fitcv/config.py
  - src/fitcv/config_loader.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/runs_list.html
  - docs/configuration.md
  - docs/api.md
  - docs/setup.md
  - docs/fitcv-control-plane-setup.md
  - docker-compose.yml
  - start_web.ps1
  - start_worker.ps1
  - tests/test_config.py
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

# Detailed Spec: `config/env.yaml` deprecation and deletion

## Goal

Remove `config/env.yaml` as ambiguous compatibility bridge and converge repo on one
clear ownership model:

- infra/bootstrap config stays in one small canonical entry surface
- runtime knobs live in `config/runtime/*`
- policy lives in `config/policy/*`
- taxonomy lives in `config/taxonomy/*`

This spec covers deprecation first, then full deletion. Product goal is no long-term
retention of `config/env.yaml` as default trigger path or silent fallback.

## Problem

`config/env.yaml` currently does too many jobs:

- acts like runtime trigger config in docs/UI/API examples
- still participates in compatibility merge logic during config load
- overlaps with canonical runtime/policy/taxonomy owners
- trains operators to edit wrong file
- creates SSOT drift and symmetry violations between docs, UI defaults, and loader behavior

Recent live-run work proved this directly:

- app/UI/docs still default to `config/env.yaml`
- loader had to special-case warnings because path is both "current default" and "legacy"
- canonical values already drain into `config/runtime/*`, `config/policy/*`, and `config/taxonomy/*`

## Decision

Deprecate `config/env.yaml` now. Delete it after one short migration wave.

### Final target state

After deletion:

- `config/env.yaml` does not exist
- `load_config()` does not probe, merge, or warn about `config/env.yaml`
- control-plane/API/UI do not suggest `config/env.yaml`
- docker/scripts do not mount or reference `config/env.yaml`
- all runtime/policy/taxonomy values come from their canonical owners only
- any remaining bootstrap entry surface is explicit and narrow, not mixed-ownership

## Non-Goals

- no redesign of policy/runtime/taxonomy schemas beyond what deletion requires
- no new abstraction layer for config bundles
- no indefinite compatibility shim
- no support for both old and new defaults forever

## Authoritative Ownership

### Canonical owners that survive

- infra/bootstrap owner: repo-root `.env.yaml` only if still needed for minimal bootstrap
- runtime knobs: `config/runtime/pipeline.yaml`
- control-plane routing/runtime: `config/runtime/control_plane.yaml`
- prompts/runtime prompt selection: `config/runtime/prompts.yaml`
- CV policy/composition/defaults: `config/policy/cv.yaml`
- ranking policy: `config/policy/ranking.yaml`
- taxonomy/synonyms: `config/taxonomy/*`

### Ownership removed

`config/env.yaml` no longer owns any of these:

- pipeline throughput / top-N knobs
- ranking knobs
- CV generation defaults
- acceptance policy
- taxonomy ladders / statuses / synonyms
- model-routing or provider selection
- candidate-profile path if that can move to a surviving bootstrap surface

## Triage

Layer: change
Feature type: DELETE
Summary: deprecate then delete `config/env.yaml` and remove all default/runtime/doc references to it
Reasoning: current bridge file creates SSOT drift, loader symmetry hacks, and operator confusion
Invariants:
  - no runtime/policy/taxonomy value loses a canonical owner during migration
  - API/UI defaults and loader behavior must agree at every wave
  - deprecation window is short and explicit
  - no silent fallback remains after deletion wave
Dependencies:
  - SQLite-only trim work already landed
  - BigQuery full deletion already landed
  - Gemini/Vertex deletion already landed
Risk anchors:
  - `src/fitcv/config.py:885` `load_config` is high-trust config entrypoint
  - `src/fitcv/config_loader.py:63` `resolve_env_path` controls default discovery behavior
  - `src/fitcv_cp/app.py` run trigger defaults must stay symmetric with loader contract
Affected stages:
  - none directly
Affected features:
  - none directly
Primary lens: cross-cutting
Affected docs:
  cross_cutting_docs:
    - docs/configuration.md
    - docs/api.md
    - docs/setup.md
    - docs/fitcv-control-plane-setup.md
Generated refresh required: no
Capability IDs:
  - none
Invariant IDs:
  - none
Spec needed: yes
Plan needed: yes

## Key Deliverables

### Deliverable 1: deprecation contract is explicit

Repo declares `config/env.yaml` deprecated as compatibility-only input with clear removal gate.

### Deliverable 2: defaults stop pointing at deprecated file

UI, API examples, docs, scripts, and compose stop using `config/env.yaml` as default path.

### Deliverable 3: loader no longer needs path-identity hacks

Config loader behavior becomes symmetric: canonical default path is canonical, deprecated path is deprecated, not both.

### Deliverable 4: file is deleted cleanly

After migration wave, `config/env.yaml` and its fallback/merge logic are removed fully.

## Migration Waves

### Wave 1: deprecate `config/env.yaml` as owner

**Purpose:**
- keep repo running while freezing further dependence on wrong file

**Steps:**
- mark `config/env.yaml` deprecated in docs
- stop describing it as canonical/default runtime config
- stop adding new keys there
- trim file contents to bootstrap-only fields that still truly need entry-surface ownership
- document exact removal date or next milestone gate

**Verification:**
- docs no longer call `config/env.yaml` canonical
- no new runtime/policy/taxonomy key is introduced under `config/env.yaml`

**Exit Criteria:**
- repo language treats `config/env.yaml` as temporary compatibility surface only

### Wave 2: replace all default references

**Purpose:**
- align operator-facing defaults with actual canonical ownership

**Steps:**
- change run trigger default path in control plane and templates
- change docs/API examples to new canonical entry path
- change scripts/compose mounts if still tied to `config/env.yaml`
- update tests that assume `config/env.yaml` is default/current path

**Verification:**
- grep finds no active "default `config/env.yaml`" language in shipped surfaces
- UI/API/script defaults all point to same surviving path

**Exit Criteria:**
- operator no longer reaches for `config/env.yaml` during normal use

### Wave 3: loader hardening

**Purpose:**
- remove ambiguous merge/fallback semantics

**Steps:**
- stop treating `config/env.yaml` as default candidate
- keep explicit deprecated-path read only if temporary migration gate still open
- emit deterministic deprecation warning when explicitly requested
- fail strict overlap when deprecated file still carries keys now owned elsewhere

**Verification:**
- loader default path and docs/UI defaults are symmetric
- deprecated path only works by explicit request during migration window

**Exit Criteria:**
- no silent fallback or implicit merge through `config/env.yaml`

### Wave 4: deletion

**Purpose:**
- finish cleanup instead of carrying dead compatibility forever

**Steps:**
- delete `config/env.yaml`
- delete loader fallback/compatibility path
- delete compose/script/test/doc references
- delete deprecation warning branch itself

**Verification:**
- grep finds no active `config/env.yaml` references outside historical/archive docs
- loader works without probing deleted file

**Exit Criteria:**
- `config/env.yaml` fully removed from active repo behavior

## Acceptance Criteria

1. `config/env.yaml` is not described as canonical/default in active docs or UI.
2. Active defaults across loader, control-plane UI, API examples, scripts, and compose are symmetric.
3. `config/env.yaml` does not own runtime knobs, policy, taxonomy, or routing after deprecation wave.
4. During migration, `config/env.yaml` is only read by explicit path, never by implicit default discovery.
5. After deletion wave, `config/env.yaml` does not exist and no active code probes it.
6. `load_config()` does not contain special-case warning suppression or path-identity hacks caused by `config/env.yaml` ambiguity.
7. Tests cover both deprecation behavior and final deletion behavior.

## Implementation Notes

### Smallest safe path

Prefer one surviving bootstrap entry surface, not two.
If repo-root `.env.yaml` already serves that role, use it and delete `config/env.yaml`.
If another bootstrap file is better, choose one and move everything else off it.
Do not invent config-bundle abstractions.

### Loader contract

Target contract after Wave 3:

- `load_config(None)` resolves only canonical default candidates
- `load_config("config/env.yaml")` works only during deprecation window and warns clearly
- deleted wave removes explicit deprecated-path support too

### Docs contract

Active docs must separate:

- bootstrap entry surface
- runtime canonical owners
- policy canonical owners
- taxonomy canonical owners

No table should imply `config/env.yaml` is both compatibility-only and current default.

## Risks

### Risk 1: hidden operator/script dependence

Some manual flows may still pass `config/env.yaml` explicitly.

**Mitigation:**
- grep repo for active references before deletion
- keep short deprecation window with explicit warning
- update scripts/docs in same patch set as default change

### Risk 2: bootstrap values lose a home

Deleting bridge file too early can orphan a few remaining infra values.

**Mitigation:**
- decide bootstrap SSOT first
- move only real bootstrap survivors there
- delete bridge after that move lands

### Risk 3: tests encode old default behavior

Loader and control-plane tests may still expect `config/env.yaml` as default/current path.

**Mitigation:**
- patch tests in same wave as runtime default changes
- keep one test for explicit deprecated-path warning during window
- replace it with deletion/failure test in final wave

## Validation

### Grep proof

Run after Wave 2:

```powershell
rg -n "config/env.yaml|legacy config path in use" src docs tests start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'
```

Run after Wave 4:

```powershell
rg -n "config/env.yaml" src docs tests start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'
```

Expected after Wave 4: no active hits.

### Focused verification

- `tests/test_config.py`
- `tests/test_fitcv_cp/test_app.py`
- any tests covering run trigger defaults / config path fields
- fast validator if docs are changed

### Live proof

- trigger one control-plane run with default path only
- confirm no deprecation noise for canonical path
- confirm run succeeds without `config/env.yaml`

## Recommendation

Deprecate now. Delete soon.

Do not keep `config/env.yaml` as permanent bridge.
That is dead-weight SSOT drift by design.

## Task/Wave Breakdown

### Wave 1: choose final bootstrap surface

- keep repo-root `.env.yaml` as only surviving bootstrap file
- move surviving bootstrap values there
- stop treating `config/env.yaml` as active owner

### Wave 2: flip active defaults

- change control-plane defaults to `.env.yaml`
- change docs and compose mounts to `.env.yaml`
- update tests that still encode `config/env.yaml`

### Wave 3: remove loader compatibility

- remove `config/env.yaml` from default candidate discovery
- remove merge and fallback behavior tied to legacy path
- keep loader contract single-path and deterministic

### Wave 4: delete dead residue

- delete `config/env.yaml`
- delete stale script/operator tests for removed surfaces
- regenerate planning lineage and re-run validator

## Design Decisions

- choose one bootstrap path: `.env.yaml`
- delete compatibility behavior instead of carrying deprecation shim
- update docs/tests in same wave as runtime behavior to keep symmetry
- remove stale tests for already-deleted outbox replay scripts instead of rebuilding dead surfaces

## Invariants

- `load_config()` resolves only `.env.yaml` by default
- active UI/docs/compose/test defaults match loader contract
- runtime, policy, and taxonomy ownership stay in canonical files
- no active repo surface references `config/env.yaml`
- deleted operator surfaces do not keep orphaned tests

## Validation Plan

- grep for `config/env.yaml`, `legacy config path in use`, and deleted helper hooks in active `src`, `docs`, `tests`, and startup surfaces
- run targeted config/control-plane tests
- run pipeline test sets that pass explicit `config_path`
- run `py -3 scripts/generate_planning_lineage.py`
- run `py -3 scripts/hooks/run_validator.py --fast`

## Completion Criteria

- repo-root `.env.yaml` exists and is tracked
- `config/env.yaml` is deleted
- loader, control-plane defaults, docs, compose, and tests use `.env.yaml`
- stale outbox replay tests are deleted with their removed scripts
- targeted tests pass
- fast validator passes
