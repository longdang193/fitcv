---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
targets:
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - src/fitcv/config.py
  - src/fitcv_cp/main.py
  - src/fitcv_cp/
  - tests/test_fitcv_cp/
related_features: []
related_stages: []
---

# Phase 2 Architecture Hardening And Portability Implementation Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md`  
**Implementation Execution Map:** `none`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Implement Phase 2 config, provider, observability, and backend portability hardening while preserving BigQuery-default compatibility.

**Architecture:** The control plane moves to explicit multi-file runtime ownership through `control_plane.yaml` + `pipeline.yaml` + process env for secrets. LLM and embedding calls are routed through provider-agnostic adapter contracts and model routing keys instead of hardcoded model/provider literals. Startup becomes backend-resolved (`bigquery|sqlite`) with backend-scoped initialization and structured observability events across routing/backend/model execution.

**Key Invariants:**
- BigQuery remains the default backend and must stay backward compatible.
- SQLite startup path must not require GCP ADC or unconditional BigQuery client construction.
- Secrets and secret key names are forbidden in YAML and sourced only from process env or `.env`.
- Business logic consumes `LLMClient`/`EmbeddingClient` interfaces only, not provider-specific transport code.
- Observability contract must emit provider/model/backend diagnostics on routed calls.

**Rollout / Revert:**  
- rollback_trigger: startup failures, provider-routing regressions, or telemetry contract breakage in CI/validation gates  
- rollback_method: revert to previous config loader + startup path + direct provider wiring while preserving docs/spec history

---

## Triage Block

Layer: change  
Feature type: MODIFY  
Summary: Harden Phase 2 control-plane portability with centralized runtime contracts, provider adapters, backend-resolved startup, and observability telemetry.  
Reasoning: This is an execution-bounded architecture refinement of an existing workstream thread, not a new feature domain or operating-system governance change.  
Invariants:
- BigQuery default remains stable.
- SQLite startup path is first-class and non-GCP-coupled.
- Secret hygiene contract is strictly enforced.
- Routing/adapter contracts stay provider-agnostic.
Dependencies:
- Existing phase-2 control-plane runtime/config code
- Validation scripts and `tests/test_fitcv_cp/` suite
Affected stages:
- none
Affected features:
- none
Primary lens: cross-cutting
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- feature_docs:
  - none
- cross_cutting_docs:
  - `docs/observability.md`
  - `docs/api.md`
- operating_system_docs:
  - `docs/operating_system/agent_memory/failure-ledger.md` (only if reusable implementation lessons emerge)
- readme: none
- generated:
  - `docs/generated/planning_lineage.yaml`
Generated refresh required: yes
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: no
Plan needed: yes
Rollback trigger: startup failures, routing resolution failures, or telemetry schema regressions
Rollback method: revert control-plane config/startup/adapter changes as one bounded patch
Migration needed: yes
Risk level: medium

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `none`
- Feature lineage: `none`
- Stage source: `none`
- Stage contracts: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs: `docs/observability.md`, `docs/api.md`
- Operating-system docs: `docs/operating_system/agent_memory/failure-ledger.md` (if reusable failure/mitigation insight appears)
- README: `none`
- Generated discovery: `docs/generated/planning_lineage.yaml`

## File Structure Plan

- Create:
  - `config/runtime/control_plane.yaml`
  - `src/fitcv_cp/adapters/__init__.py`
  - `src/fitcv_cp/adapters/contracts.py`
  - `src/fitcv_cp/adapters/providers/`
  - `tests/test_fitcv_cp/test_control_plane_config.py`
  - `tests/test_fitcv_cp/test_provider_routing.py`
  - `tests/test_fitcv_cp/test_observability_contract.py`
- Modify:
  - `config/runtime/pipeline.yaml`
  - `src/fitcv/config.py`
  - `src/fitcv_cp/main.py`
  - `src/fitcv_cp/store/` (backend resolver + capability checks)
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
- Docs:
  - `docs/observability.md`
  - `docs/api.md`
  - `docs/generated/planning_lineage.yaml`

## Prerequisites

- Use this worktree/branch only:
  - worktree: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\phase-2-architecture-hardening-portability-plan`
  - branch: `codex/phase-2-architecture-hardening-portability-plan`
- Capture baseline before Task 1 to prevent pre-existing failure confusion:
  - `pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py`
- If baseline fails, record failures and get explicit proceed/no-proceed confirmation before continuing.

## Tasks

### Task 1: Centralize Control-Plane Runtime Config

**Files:**
- Create: `config/runtime/control_plane.yaml`
- Modify: `config/runtime/pipeline.yaml`, `src/fitcv/config.py`
- Test: `tests/test_fitcv_cp/test_control_plane_config.py`
- Docs: `docs/api.md`, `docs/generated/planning_lineage.yaml`

- [ ] Step 1: Add `control_plane` schema sections (`data_backend`, `providers`, `model_routing`, `observability`, `feature_flags`) with no secret values and no secret key names.
- [ ] Step 2: Implement typed loader/accessor support in `src/fitcv/config.py` with precedence rules (`.env`/process env overrides where allowed).
- [ ] Step 3: Write failing config hydration/precedence tests.
- [ ] Step 4: Run `pytest tests/test_fitcv_cp/test_control_plane_config.py` and confirm initial failure.
- [ ] Step 5: Implement minimal fixes until tests pass.
- [ ] Step 6: Update API/config docs and regenerate planning lineage if lifecycle metadata changed.
- [ ] Step 7: Commit.

### Task 2: Introduce Provider-Agnostic Adapter Contracts

**Files:**
- Create: `src/fitcv_cp/adapters/contracts.py`, `src/fitcv_cp/adapters/__init__.py`, provider adapter modules under `src/fitcv_cp/adapters/providers/`
- Modify: control-plane call sites under `src/fitcv_cp/` that invoke LLM/embedding providers directly
- Test: `tests/test_fitcv_cp/test_provider_routing.py`
- Docs: `docs/api.md`, `docs/observability.md`

- [ ] Step 1: Define `LLMClient.generate(...)` and `EmbeddingClient.embed(...)` contracts.
- [ ] Step 2: Implement provider registry/resolution from config (`control_plane.providers` + `model_routing.parts`).
- [ ] Step 3: Refactor business logic call sites to consume routing keys/tiers instead of provider/model literals.
- [ ] Step 4: Write failing tests for routing resolution and unsupported-part validation errors.
- [ ] Step 5: Run `pytest tests/test_fitcv_cp/test_provider_routing.py` and confirm initial failure.
- [ ] Step 6: Implement minimal pass and rerun targeted tests.
- [ ] Step 7: Commit.

### Task 3: Decouple Startup From BigQuery-Only Assumptions

**Files:**
- Modify: `src/fitcv_cp/main.py`, backend initialization/store modules in `src/fitcv_cp/store/`
- Test: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_bq_store.py`
- Docs: `docs/api.md`

- [ ] Step 1: Introduce backend resolver (`bigquery|sqlite`) using centralized config + optional env override.
- [ ] Step 2: Ensure startup initializes only selected backend dependencies.
- [ ] Step 3: Add clear backend-scoped diagnostics for missing prerequisites (not import-time generic traces).
- [ ] Step 4: Write failing startup tests for both modes (`bigquery` default and `sqlite` non-GCP path).
- [ ] Step 5: Run `pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py` and confirm targeted failures.
- [ ] Step 6: Implement minimal pass and rerun the targeted suite.
- [ ] Step 7: Commit.

### Task 4: Implement Observability Contract

**Files:**
- Modify: observability/logging hooks under `src/fitcv_cp/` (routing, provider invocation, backend operations)
- Create/Modify Test: `tests/test_fitcv_cp/test_observability_contract.py`
- Docs: `docs/observability.md`

- [ ] Step 1: Define event fields for request identity, model execution, backend execution, and policy/routing decisions.
- [ ] Step 2: Implement structured local log emission and OTEL-exporter-enabled path behind config toggles.
- [ ] Step 3: Write failing tests asserting required diagnostics fields for routed calls and backend selection events.
- [ ] Step 4: Run `pytest tests/test_fitcv_cp/test_observability_contract.py` and confirm failure.
- [ ] Step 5: Implement minimal pass and rerun targeted tests.
- [ ] Step 6: Update observability docs.
- [ ] Step 7: Commit.

### Task 5: Validation Gates And Closeout

**Files:**
- Modify: any remaining touched implementation/test/doc files
- Docs: `docs/generated/planning_lineage.yaml`, `docs/operating_system/agent_memory/failure-ledger.md` (only if a reusable lesson emerged)

- [ ] Step 1: Run repo validation gates:
  - `python scripts/validate_repo_contracts.py --fast`
  - `python scripts/validate_planning_lifecycle.py --strict`
- [ ] Step 2: Run full targeted portability suite:
  - `pytest tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_provider_routing.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py tests/test_fitcv_cp/test_observability_contract.py`
- [ ] Step 3: Execute explicit secret-hygiene checks (must return no matches):
  - `rg -n "(api[_-]?key|token|secret|password|credential).*:" config/runtime/*.yaml`
  - `rg -n "api_key_env|token_env|secret_env|password_env|credential_env" config/runtime/*.yaml`
- [ ] Step 4: Confirm acceptance criteria from spec are all satisfied.
- [ ] Step 5: Refresh generated discovery docs if required and verify clean regeneration:
  - `python scripts/generate_planning_lineage.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 6: Commit final integration checkpoint.

## Validation Command Set

```powershell
python scripts/validate_repo_contracts.py --fast
python scripts/validate_planning_lifecycle.py --strict
pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py
pytest tests/test_fitcv_cp/test_control_plane_config.py tests/test_fitcv_cp/test_provider_routing.py tests/test_fitcv_cp/test_observability_contract.py
```

## Acceptance Mapping

- AC1 config/model tiers/backend selection: Tasks 1, 3
- AC2 sqlite startup without GCP ADC: Task 3
- AC3 BigQuery default backward compatibility: Task 3 + Task 5
- AC4 config-only model switching by task family: Task 2
- AC5 explicit backend capability boundaries in docs: Tasks 3, 5
- AC6 observability diagnostics coverage: Task 4
- AC7 secret hygiene enforcement: Tasks 1, 5

## Plan Review Loop

- Run `plan-document-reviewer` on this plan with:
  - plan path: `docs/superpowers/plans/2026-05-03-14-20-phase-2-architecture-hardening-and-portability-plan.md`
  - spec path: `docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md`
  - feature source path: `none`
  - generated contract path: `none`
- Apply review fixes and repeat up to 3 cycles if needed.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-03-14-20-phase-2-architecture-hardening-and-portability-plan.md`. Two execution options:

1. **Subagent-Driven (recommended)** — fresh subagent per task
2. **Inline Execution** — execute in this session with `executing-plans`
