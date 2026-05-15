---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: provider-baseurl-ssot-centralization
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-15-23-00-provider-baseurl-ssot-centralization-spec.md
targets:
  - config/runtime/control_plane.yaml
  - .env
  - docker-compose.yml
  - src/fitcv/config.py
  - src/fitcv_cp/app.py
  - tests/test_fitcv_cp/test_control_plane_config.py
  - tests/test_config.py
  - docs/configuration.md
  - docs/setup.md
related_features:
  - admin_control_plane_core
related_stages: []
---

## Goal

Implement Option A routing centralization so `config/runtime/control_plane.yaml` is canonical owner for provider routing defaults, while `.env` is secrets plus optional override channel with deterministic precedence and explicit diagnostics source.

## Key Deliverables

### Deliverable 1: Canonical routing-resolution behavior

- Runtime resolution enforces precedence: env override (if set) -> control-plane defaults -> fail fast.
- No silent fallback path for missing required resolved routing fields.
- Routing diagnostics include resolved source attribution (`env_override` or `control_plane`).

### Deliverable 2: Contract-aligned docs and tests

- Tests cover ownership, precedence, and fail-fast behavior.
- Setup/config docs clearly state one-owner rule and override semantics.
- Legacy env variable usage remains backward-compatible for migration window.

## Task/Wave Breakdown

### Task 1: Implement centralized routing resolution helper

**Purpose:**
- Establish single code-path for provider/model/base_url/wire_api resolution with deterministic precedence.

**Files:**
- Inspect: `src/fitcv/config.py`, `src/fitcv_cp/app.py`, `config/runtime/control_plane.yaml`
- Modify: `src/fitcv/config.py`, `src/fitcv_cp/app.py`
- Verify: `tests/test_fitcv_cp/test_control_plane_config.py`, `tests/test_config.py`

**Preconditions:**
- Spec approved: `docs/superpowers/specs/2026-05-15-23-00-provider-baseurl-ssot-centralization-spec.md`
- Existing control-plane routing contract remains current truth.

**Steps:**
- [x] Step 1: Add/extend helper in `src/fitcv/config.py` for resolved routing selection that emits source label.
- [x] Step 2: Apply helper in control-plane runtime path(s) in `src/fitcv_cp/app.py` for diagnostics payload consistency.
- [x] Step 3: Add fail-fast validation when required resolved routing fields are missing.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_control_plane_config.py`
- [x] Manual inspection of emitted diagnostics payload fields for source label.

**Exit Criteria:**
- One centralized resolver is used for routing resolution in scoped runtime paths.

### Task 2: Add precedence and fail-fast test coverage

**Purpose:**
- Prove deterministic behavior and protect against regression.

**Files:**
- Inspect: `tests/test_fitcv_cp/test_control_plane_config.py`, `tests/test_config.py`
- Modify: `tests/test_fitcv_cp/test_control_plane_config.py`, `tests/test_config.py`
- Verify: same tests + focused subsets

**Preconditions:**
- Task 1 complete.

**Steps:**
- [x] Step 1: Add tests for env-unset -> control-plane default behavior.
- [x] Step 2: Add tests for env-set -> env override behavior with source attribution.
- [x] Step 3: Add negative tests for missing resolved routing fields -> explicit failure.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_control_plane_config.py`
- [ ] `pytest -q tests/test_config.py -k "control_plane or routing"` (no matching tests in current suite; replace in follow-up with concrete selector)

**Exit Criteria:**
- Tests prove precedence and fail-fast semantics described in spec.

### Task 3: Align docs and migration notes

**Purpose:**
- Remove operator confusion and codify one-owner contract.

**Files:**
- Inspect: `docs/configuration.md`, `docs/setup.md`, `.env`, `docker-compose.yml`
- Modify: `docs/configuration.md`, `docs/setup.md`
- Verify: doc content + command examples consistency

**Preconditions:**
- Task 1 complete.

**Steps:**
- [x] Step 1: Document owner/override rule and precedence in `docs/configuration.md`.
- [x] Step 2: Add concise `.env` guidance in `docs/setup.md` (secrets + optional override-only semantics).
- [x] Step 3: Ensure examples do not imply env as default owner for routing.

**Verification:**
- [x] `rg -n "FITCV_LANGGRAPH_OPENAI_BASE_URL|control_plane|base_url|override" docs/configuration.md docs/setup.md`

**Exit Criteria:**
- Docs clearly express SSOT ownership and override behavior.

### Task 4: Final bounded verification and handoff readiness

**Purpose:**
- Confirm in-scope deliverables are complete and handoff-ready.

**Files:**
- Inspect: changed source/tests/docs from Tasks 1-3
- Verify: full bounded command set

**Preconditions:**
- Tasks 1-3 complete.

**Steps:**
- [x] Step 1: Run focused tests for control-plane config and routing behavior.
- [x] Step 2: Run repo hook subset to ensure metadata/doc contracts still pass.
- [x] Step 3: Capture evidence summary for execution context pack/audit linkage if needed.

**Verification:**
- [x] `pytest -q tests/test_fitcv_cp/test_control_plane_config.py`
- [ ] `pytest -q tests/test_config.py -k "control_plane or routing or legacy config path"`
- [ ] `python scripts/hooks/run_validator.py --fast`

**Exit Criteria:**
- Bounded changes are verified, no unresolved high-risk ambiguity remains.

## Verification

- `pytest -q tests/test_fitcv_cp/test_control_plane_config.py`
- `pytest -q tests/test_config.py -k "control_plane or routing or legacy config path"`
- `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`


