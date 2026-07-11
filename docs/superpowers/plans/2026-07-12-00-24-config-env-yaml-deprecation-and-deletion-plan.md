---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: config-env-yaml-deprecation-and-deletion
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-07-12-00-20-config-env-yaml-deprecation-and-deletion-spec.md
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

## Goal

Deprecate `config/env.yaml` immediately, stop using it as active default anywhere,
then delete it cleanly once canonical bootstrap/runtime ownership is fully
symmetric across loader, UI, scripts, compose, docs, and tests.

## Key Deliverables

### Deliverable 1: deprecation window is explicit and bounded

`config/env.yaml` is compatibility-only during one short migration wave, with no
new ownership added and no active surface presenting it as canonical.

### Deliverable 2: defaults are symmetric before deletion

Loader defaults, control-plane defaults, API examples, scripts, and compose all
point to one surviving bootstrap path instead of `config/env.yaml`.

### Deliverable 3: deletion removes file and fallback logic together

`config/env.yaml` is deleted in same wave as loader fallback/remnant references,
so repo does not carry dead compatibility code.

## Task/Wave Breakdown

### Task 1: Freeze `config/env.yaml` ownership and mark deprecation

**Purpose:**
- stop further SSOT drift before changing runtime defaults

**Files:**
- Modify: `docs/superpowers/specs/2026-07-12-00-20-config-env-yaml-deprecation-and-deletion-spec.md`
- Modify: `docs/configuration.md`
- Modify: `config/env.yaml`

**Preconditions:**
- deprecation spec approved

**Steps:**
- [ ] Step 1: mark `config/env.yaml` deprecated in active docs.
- [ ] Step 2: trim `config/env.yaml` to bootstrap-only values that still lack a surviving owner.
- [ ] Step 3: document exact removal gate and state that runtime/policy/taxonomy ownership may not expand there.

**Verification:**
- [ ] grep active docs for canonical/default wording tied to `config/env.yaml`
- [ ] inspect `config/env.yaml` for non-bootstrap runtime/policy/taxonomy keys

**Exit Criteria:**
- repo documents `config/env.yaml` as temporary compatibility input only

### Task 2: Replace all shipped default references

**Purpose:**
- make user-facing defaults agree with desired final state

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `docs/api.md`
- Modify: `docs/setup.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Modify: `docs/configuration.md`
- Modify: `docker-compose.yml`
- Modify: `start_web.ps1`
- Modify: `start_worker.ps1`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Task 1 complete
- surviving canonical bootstrap path chosen

**Steps:**
- [ ] Step 1: change run-trigger default `config_path` in control-plane code and UI.
- [ ] Step 2: change API/setup docs and examples to same canonical path.
- [ ] Step 3: change compose/script references that still mount or mention `config/env.yaml` as active default.
- [ ] Step 4: update tests that assume `config/env.yaml` is current default path.

**Verification:**
- [ ] `rg -n "config/env.yaml" src/fitcv_cp docs start_web.ps1 start_worker.ps1 docker-compose.yml tests/test_fitcv_cp/test_app.py -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- [ ] targeted app/default-path tests

**Exit Criteria:**
- no shipped surface suggests `config/env.yaml` as normal default path

### Task 3: Harden loader contract for deprecation window

**Purpose:**
- remove current ambiguity where deprecated path and default path are effectively same workflow

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/config_loader.py`
- Modify: `tests/test_config.py`

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: remove `config/env.yaml` from implicit default discovery candidates.
- [ ] Step 2: keep explicit deprecated-path support only if migration wave still needs it.
- [ ] Step 3: emit one deterministic warning only for explicit deprecated-path usage.
- [ ] Step 4: fail or warn clearly when deprecated file still carries keys owned by canonical runtime/policy/taxonomy surfaces.

**Verification:**
- [ ] `py -3 -m pytest tests/test_config.py -q`
- [ ] one manual `load_config(None)` check for canonical path
- [ ] one manual explicit `load_config("config/env.yaml")` deprecation-path check during migration window

**Exit Criteria:**
- loader default path is canonical; deprecated path is explicit-only

### Task 4: Delete `config/env.yaml` and all active residue

**Purpose:**
- finish cleanup instead of leaving compatibility zombie code

**Files:**
- Delete: `config/env.yaml`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/config_loader.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `docs/configuration.md`
- Modify: `docs/api.md`
- Modify: `docs/setup.md`
- Modify: `docs/fitcv-control-plane-setup.md`
- Modify: `docker-compose.yml`
- Modify: `start_web.ps1`
- Modify: `start_worker.ps1`
- Modify: `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Preconditions:**
- Tasks 1-3 complete
- no active operator/script dependence remains

**Steps:**
- [ ] Step 1: delete file `config/env.yaml`.
- [ ] Step 2: delete fallback/merge/deprecation branches that exist only for that file.
- [ ] Step 3: delete final active references in docs, scripts, compose, UI, and tests.
- [ ] Step 4: replace migration-window test coverage with final deletion/failure coverage.

**Verification:**
- [ ] `rg -n "config/env.yaml|legacy config path in use" src docs tests start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- [ ] `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py -q`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- `config/env.yaml` does not exist and active repo no longer probes or documents it

## Verification

- `py -3 -m pytest tests/test_config.py tests/test_fitcv_cp/test_app.py -q`
- `rg -n "config/env.yaml|legacy config path in use" src docs tests start_web.ps1 start_worker.ps1 docker-compose.yml -g '!docs/superpowers/**' -g '!docs/intent/**' -g '!docs/operating_system/**'`
- `py -3 scripts/hooks/run_validator.py --fast`
- one live control-plane run using default path only after Task 3

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
