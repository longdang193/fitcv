---
layer: change
artifact_type: plan
status: proposed
parent_workstream: none
parent_thread: workstream-operator-control-plane.operator-control-plane-phase-2-degraded-mode-and-portability-surface
parent_spec: docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md
targets:
  - src/fitcv/ai_score.py
  - src/fitcv/cv_generator.py
  - src/fitcv/enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
related_features:
  - none
related_stages:
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Ranking And CV Provider Routing Hardening Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md`  
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-05-04-provider-storage-agnostic-parity-implementation-execution-map.md`  
**Type:** modify  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Enforce config-file-controlled OpenAI-compatible routing with fail-fast behavior for ranking and CV generation paths, eliminating silent/implicit Google fallback and preserving sqlite vs bigquery parity contracts.

**Architecture:** Runtime provider/model/base_url for LLM parts must resolve from `control_plane.model_routing.parts` plus env-only secrets. Scoring and CV lanes should share the same fail-fast semantics: unresolved routing is an explicit runtime error, not an implicit provider fallback. Observability payloads must continue exposing stage outcomes and error reasons without schema drift.

**Key Invariants:**
- `ranking_ai_score` and `cv_generation_structured_write` are controlled by control-plane routing, not hardcoded provider defaults.
- YAML never carries secret values; API keys come from process env / `.env` only.
- StageResult/event payload shapes remain backward-compatible for UI and artifact exports.
- sqlite data-plane indicators remain `state_backend=sqlite` and `artifact_backend=sqlite_json` when sqlite mode is active.

**Rollout / Revert:**  
- rollback_trigger: increased run failures where routed provider is correctly configured but runtime behavior regresses (timeouts aside)  
- rollback_method: revert routing-hardening commits for this bounded lane and restore prior scorer/generator client logic while keeping poison-reuse guards

---

## Triage

Layer: change  
Feature type: MODIFY  
Summary: Harden provider-routing semantics for ranking and CV lanes so config controls provider, with explicit fail-fast and no Google fallback drift.  
Reasoning: Existing live runs proved reranker fallback drift and downstream CV provider inconsistencies under sqlite parity lane.  
Invariants:
- config-driven routing is authoritative
- env-only secret hygiene
- no StageResult schema drift
Dependencies:
- `docs/superpowers/specs/2026-05-03-phase-2-architecture-hardening-and-portability-spec.md`
- `docs/superpowers/execution_maps/2026-05-04-provider-storage-agnostic-parity-implementation-execution-map.md`
Affected stages:
- shortlist
- ranking
- cv_analysis
- cv_generation
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
- feature_docs: none
- cross_cutting_docs: none
- readme: none
- generated: none
Generated refresh required: no
Capability IDs:
- trigger_run_management.reranker-fit-authority
- operator-control-plane-phase-2-portability
Invariant IDs:
- config-routed-provider-authority
- env-only-secret-hygiene
Spec needed: no (already exists)
Plan needed: yes

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `none`
- Feature lineage: `none`
- Stage source: `none`
- Stage contracts: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs: `none`
- README: `none`
- Generated discovery: `none`

---

### Task 1: Lock Ranking Provider Routing Contract

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Test: `tests/test_ai_score.py`
- Docs: none

- [ ] Step 1: Add/extend failing tests for strict routed-provider behavior (`provider`, `model`, `base_url`, API key) and forbidden fallback.
- [ ] Step 2: Run `pytest -q tests/test_ai_score.py -k "routing or openai_compatible or requires"` and confirm failure before patch.
- [ ] Step 3: Implement smallest change so `ranking_ai_score` strictly uses control-plane routing + env secrets and fails fast when unresolved.
- [ ] Step 4: Run `pytest -q tests/test_ai_score.py` and confirm pass.
- [ ] Step 5: Commit bounded ranking routing patch.

### Task 2: Align CV Generation Routing Semantics With Ranking

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/enrich.py` (only if shared helper alignment is required)
- Test: `tests/test_cv_generator.py`
- Docs: none

- [ ] Step 1: Add failing tests proving CV generation respects routed provider/model/base_url and fails fast on unresolved config/env.
- [ ] Step 2: Run `pytest -q tests/test_cv_generator.py -k "routing or openai_compatible"` and confirm failure before patch.
- [ ] Step 3: Implement minimal alignment patch (no broad refactor) to match ranking fail-fast semantics.
- [ ] Step 4: Re-run focused tests and confirm pass.
- [ ] Step 5: Commit bounded CV routing patch.

### Task 3: Wire Compatibility And Live Validation (sqlite lane)

**Files:**
- Modify: `src/fitcv/ai_score.py` and/or `src/fitcv/cv_generator.py` (only if fallback compatibility bug remains)
- Verify artifacts under: `data/fitcv_cp.sqlite3`, `data/fitcv_cp_event_history/`
- Docs: none

- [ ] Step 1: Run endpoint probes against configured base URL for both `/responses` and `/chat/completions` using current model/env.
- [ ] Step 2: If `/responses` unsupported (404), enforce safe fallback/override behavior without schema drift.
- [ ] Step 3: Trigger one fresh sqlite run (inline execution allowed when Redis unavailable) with `sample_data_engineer_jobs.json`.
- [ ] Step 4: Validate run artifacts for: reranker parser `ok`, no ADC fallback errors, stable stage contracts, and CV generation outcomes.
- [ ] Step 5: Commit live-lane compatibility patch (if any).

### Task 4: Pattern Detection And Scope Control Report

**Files:**
- Inspect only: `src/fitcv/enrich.py`, `src/fitcv/cv_generator.py`, `src/fitcv/agentic_cv_generation.py`
- Docs: none

- [ ] Step 1: Scan for same failure pattern: routed provider exists but runtime can silently degrade to Google/default path.
- [ ] Step 2: Classify findings as `confirmed | likely | risk` with exact file+function references.
- [ ] Step 3: Fix only low-risk confirmed same-pattern items in this lane; defer others with explicit follow-up notes.
- [ ] Step 4: Produce bounded scope decision log in execution response.

### Task 5: Verification Gate Before Completion

**Files:**
- Verify code+tests only
- Docs: none

- [ ] Step 1: Run focused regression suite:
  - `pytest -q tests/test_ai_score.py tests/test_cv_generator.py`
  - `pytest -q tests/test_pipeline.py -k "reranker or cv_analysis or late_stage_reuse"`
- [ ] Step 2: Run one final live sqlite rerun and collect evidence summary (run id, stage outcomes, parser statuses, cv counts).
- [ ] Step 3: Confirm no contract drift in run detail artifacts/events payload structures.
- [ ] Step 4: Publish patch summary + pattern detection + risks + next eligible action.

---

## Validation Commands

```powershell
pytest -q tests/test_ai_score.py
pytest -q tests/test_cv_generator.py
pytest -q tests/test_pipeline.py -k "reranker or cv_analysis or late_stage_reuse"
```

Live validation (sqlite parity lane):
```powershell
# trigger run (inline mode if Redis unavailable)
# then inspect data/fitcv_cp.sqlite3 and data/fitcv_cp_event_history/<run_id>.jsonl
```

---

## Completion Criteria

An implementation-plan item is complete when:

1. strict config-routed provider authority is enforced for ranking and CV generation lanes
2. no silent Google/ADC fallback remains in these routed lanes
3. focused tests pass and live sqlite run evidence confirms behavior
4. stage/event/result contracts remain compatible for UI + artifact exports
5. deferred findings (if any) are explicitly documented with bounded follow-up scope

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
