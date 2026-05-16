---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: config-razor-ssot-simplification
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
parent_spec: docs/superpowers/specs/2026-05-16-23-30-config-razor-ssot-simplification-spec.md
targets:
  - config/env.yaml
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - config/live_smoke.yaml
  - src/fitcv/config.py
  - docs/configuration.md
  - tests/test_config.py
related_features:
  - settings_system
  - cv_system
related_stages:
  - enrich
  - ranking
  - cv_generation
---

## Goal

Implement Razor + SSOT cleanup for `config/` by deleting `config/live_smoke.yaml`, enforcing one canonical owner per key family, and proving non-regressive runtime behavior with targeted tests and live evidence.

## Key Deliverables

### Deliverable 1: Canonical config ownership is enforceable

`control_plane.yaml` owns backend/provider/model routing, `pipeline.yaml` owns runtime knobs, and `env.yaml` is limited to infra bridge + approved compatibility path.

### Deliverable 2: `config/live_smoke.yaml` retirement is complete

`config/live_smoke.yaml` is removed and no active runtime path depends on it.

### Deliverable 3: Model-key ambiguity is removed

No duplicate model-owner declarations remain across config surfaces, and loader behavior preserves deterministic routing ownership.

### Deliverable 4: Validation + runtime evidence support closure

Targeted config tests, repo contract checks (scoped), and one bounded run provide closure evidence for the SSOT simplification.

## Task/Wave Breakdown

### Task 1: Establish current-state ownership evidence and deletion safety

**Purpose:**
- confirm exact key ownership and prove `live_smoke.yaml` can be deleted safely

**Files:**
- Inspect: `config/env.yaml`
- Inspect: `config/runtime/control_plane.yaml`
- Inspect: `config/runtime/pipeline.yaml`
- Inspect: `config/live_smoke.yaml`
- Inspect: `src/fitcv/config.py`
- Modify: `docs/configuration.md`

**Preconditions:**
- parent spec approved (`2026-05-16-23-30-config-razor-ssot-simplification-spec.md`)

**Steps:**
- [ ] Step 1: inventory model/backend/runtime keys across `config/` and classify canonical owners.
- [ ] Step 2: scan runtime/code references to `live_smoke.yaml` and classify any dependency as active or dead.
- [ ] Step 3: update `docs/configuration.md` ownership matrix to reflect Razor + SSOT target state and deletion intent.

**Verification:**
- [ ] `rg -n "live_smoke|gemini_model|embedding_model|model_routing|data_backend|gcp_project|bigquery_dataset|service_account_key" config src docs/configuration.md`

**Exit Criteria:**
- ownership and deletion decisions are source-grounded and documented

### Task 2: Apply canonical ownership cleanup and delete `live_smoke.yaml`

**Purpose:**
- remove duplicate config ownership and enforce minimal config surface

**Files:**
- Modify: `config/env.yaml`
- Modify: `config/runtime/control_plane.yaml`
- Modify: `config/runtime/pipeline.yaml`
- Delete: `config/live_smoke.yaml`
- Modify: `src/fitcv/config.py`

**Preconditions:**
- Task 1 complete

**Steps:**
- [ ] Step 1: remove `config/live_smoke.yaml`.
- [ ] Step 2: drain duplicated model/runtime declarations from non-owner files.
- [ ] Step 3: constrain `env.yaml` to infra bridge + explicit approved compatibility keys only.
- [ ] Step 4: tighten loader merge/compat logic in `src/fitcv/config.py` so deleted/duplicate surfaces cannot silently re-enter effective config.

**Verification:**
- [ ] `rg -n "live_smoke.yaml" config src docs tests`
- [ ] `rg -n "gemini_model|embedding_model" config/env.yaml config/runtime/control_plane.yaml config/runtime/pipeline.yaml`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- deleted surface is absent and canonical ownership rules are enforced in config + loader

### Task 3: Add regression guards for SSOT and deleted-surface invariants

**Purpose:**
- lock contract so future edits cannot reintroduce ownership drift

**Files:**
- Modify: `tests/test_config.py`
- Modify: `src/fitcv/config.py` (only if hooks/helpers needed)

**Preconditions:**
- Task 2 complete

**Steps:**
- [ ] Step 1: add test asserting no runtime dependency on `config/live_smoke.yaml`.
- [ ] Step 2: add test asserting one-owner model routing contract (no duplicated owner semantics across config load path).
- [ ] Step 3: add test for deterministic effective config under canonical load order.

**Verification:**
- [ ] `pytest -q tests/test_config.py -k "ssot or live_smoke or ownership or routing"`

**Exit Criteria:**
- tests fail if deleted surface or duplicate ownership is reintroduced

### Task 4: Runtime proof and closure evidence

**Purpose:**
- prove behavior remains stable after Razor simplification

**Files:**
- Modify: `docs/configuration.md`
- Modify: `docs/superpowers/execution_context_packs/config-razor-ssot-simplification/latest.md`
- Modify: `artifacts/execution_context_pack.md` (mirror)
- Inspect: run artifacts (`settings-used.json`, `cv_analysis.json`)

**Preconditions:**
- Task 3 complete

**Steps:**
- [ ] Step 1: trigger one bounded `run_all` run with canonical config path.
- [ ] Step 2: capture run status and artifact evidence (`/runs/{id}`, `settings-used.json`, `cv_analysis.json`).
- [ ] Step 3: record closure evidence and residual risk disposition in plan/context pack.

**Verification:**
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] `py scripts/validate_planning_lifecycle.py --strict`
- [ ] `py scripts/validate_checkpoint_packs.py`

**Exit Criteria:**
- deliverable-level evidence supports closure for this lane scope

## Verification

- `python scripts/hooks/run_validator.py --fast`
- `pytest -q tests/test_config.py -k "ssot or live_smoke or ownership or routing"`
- `py scripts/validate_planning_lifecycle.py --strict`
- `py scripts/validate_checkpoint_packs.py`
- live run evidence:
  - `GET /runs/{run_id}`
  - `GET /admin/runs/{run_id}/settings-used.json`
  - `GET /admin/runs/{run_id}/stage-artifacts/cv_analysis.json`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
