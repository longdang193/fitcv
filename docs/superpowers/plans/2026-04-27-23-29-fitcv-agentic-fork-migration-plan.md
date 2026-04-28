---
layer: operating_system
artifact_type: plan
status: active
parent_workstream: none
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/runs_list.html
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/
related_features:
  - cv_system
  - trigger_run_management
  - inspection_debugging
related_stages:
  - cv_analysis
  - cv_generation
---

# FitCV Agentic Fork Migration Implementation Plan

**Feature Source:** `docs/features/cv_system/feature.source.yaml`
**Feature Contract:** `docs/features/cv_system/cv_system.yaml`
**Spec:** `none`
**Type:** replace
**Plan Layer:** workstream
**Plan Status:** active

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Rebase the selective-agentic upgrade onto the original FitCV repo so the original control plane, run semantics, and deterministic acceptance discipline stay authoritative while bounded agentic behavior improves only late-stage CV analysis and CV generation.

**Architecture:** The original FitCV repo remains the product spine: trigger, run list, run detail, lifecycle controls, checkpoints, stage order, artifacts, and deterministic validator-owned acceptance stay intact. Agentic behavior is introduced only as a bounded late-stage seam that accepts original-FitCV-ranked inputs, produces generation-ready analysis or an explicit hold, and runs a narrow plan-write-validate-repair loop without inventing a second runtime, replay shell, or operator model.

**Key Invariants:**
- Preserve original `run_all` and `manual_staged` semantics, including checkpoint ownership and per-stage continuation.
- Preserve canonical stage order: `normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`.
- Preserve deterministic validation as the final acceptance gate.
- Keep original `fitcv_cp` operator information architecture as the primary operator-facing surface.
- Keep agentic changes bounded to late-stage seams and stage-owned artifacts.

**Rollout / Revert:**
- rollback_trigger: late-stage migration changes alter trigger/run/checkpoint meaning, break original operator flows, or bypass deterministic validation
- rollback_method: disable the new late-stage seam behind a config-owned adapter toggle and fall back to the original `cv_analysis` and `cv_generation` path

---

## Triage

Layer: workstream
Feature type: REPLACE
Summary: Rebase the selective-agentic CV upgrade onto the original FitCV repo and keep the original control plane and pipeline semantics authoritative.
Reasoning: The previous bounded shadow-runtime fork proved some late-stage agentic pieces, but the operator-facing and lifecycle foundation drifted from the original FitCV product shape; the correct durable path is to preserve the original repo as the base and transplant only bounded late-stage improvements.
Invariants:
- original trigger, run-mode, and checkpoint semantics remain authoritative
- original control-plane UI and inspection model remain authoritative
- deterministic validation remains the final acceptance gate
- late-stage agentic logic must stay stage-bounded and evidence-grounded
Dependencies:
- `docs/FitCV-pipeline.md`
- `docs/features/cv_system/feature.source.yaml`
- `docs/stages/cv_analysis.source.yaml`
- `docs/stages/cv_generation.source.yaml`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/worker_job.py`
- reference-only transplant candidates from `C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph\src\fitcv_langgraph\`
Affected stages:
- cv_analysis
- cv_generation
Affected features:
- cv_system
- trigger_run_management
- inspection_debugging
Primary lens: mixed
Affected docs:
- feature_source: `docs/features/cv_system/feature.source.yaml`
- feature_yaml: `docs/features/cv_system/cv_system.yaml`
- feature_lineage: `docs/features/cv_system/lineage.generated.yaml`
- feature_history: `docs/features/cv_system/history.md`
- stage_source: `docs/stages/cv_analysis.source.yaml`
- stage_contract: `docs/stages/cv_analysis.yaml`
- feature_docs: none
- cross_cutting_docs:
  - `docs/FitCV-pipeline.md`
- readme: `README.md`
- generated:
  - `docs/generated/architecture_dag.yaml`
  - `docs/generated/capability_lineage.yaml`
Generated refresh required: yes
Capability IDs:
- `cv_system.analysis-evidence-selection`
- `cv_system.fit-gate-resolution`
- `cv_system.structured-cv-generation`
- `cv_system.analysis-grounded-validation`
- `cv_system.stage-artifact-diagnostics`
Invariant IDs:
- none
Spec needed: no
Plan needed: yes
Migration needed: yes
Risk level: medium

## Doc Update Matrix

- Feature source: `docs/features/cv_system/feature.source.yaml`
- Feature contract: `docs/features/cv_system/cv_system.yaml`
- Feature lineage: `docs/features/cv_system/lineage.generated.yaml`
- Stage source: `docs/stages/cv_analysis.source.yaml`, `docs/stages/cv_generation.source.yaml`
- Stage contracts: `docs/stages/cv_analysis.yaml`, `docs/stages/cv_generation.yaml`
- Feature history: `docs/features/cv_system/history.md`
- Feature-specific docs: none
- Cross-cutting docs: `docs/FitCV-pipeline.md`
- Operating-system docs: none
- README: `README.md`
- Generated discovery: `docs/generated/architecture_dag.yaml`, `docs/generated/capability_lineage.yaml`

## Preserve-As-Is Contract

1. Original operator flows in `src/fitcv_cp/`:
   - run trigger form
   - runs inbox
   - run detail shell
   - lifecycle actions
   - three inspection tabs
   - always-visible event timeline
2. Original run-state vocabulary and checkpoint fields in `src/fitcv_cp/models.py`, `src/fitcv_cp/app.py`, and `src/fitcv_cp/worker_job.py`.
3. Original pipeline stage order and stop-after-stage continuation semantics.
4. Original stage-owned artifacts, exports, and deterministic validation acceptance discipline.
5. Original paused-after-`enrich` synonym overlay override behavior.

## Transplant-First Contract

1. Pre-writing analysis gate:
   - explicit generation-ready analysis output
   - explicit hold reasons
   - grounded evidence-selection diagnostics
2. Bounded generation graph behavior:
   - plan -> write -> validate -> repair
   - adapter seams for planner, writer, and repair
3. Deterministic validator-compatible repair:
   - repair only within bounded failure classes
   - never bypass deterministic acceptance
4. Optional later sidecar:
   - synonym review core only, if it can support the original paused-after-`enrich` review semantics without replacing them

## Explicit Non-Goals

- Do not transplant replay-console UI, replay-reporting contracts, or debug-first runtime shells.
- Do not replace the original operator information architecture with a new single-page console.
- Do not broaden agentic AI into normalize, enrich, rule_filter, shortlist, or ranking unless a later bounded slice explicitly proves that need.

## Task 1: Establish The Late-Stage Adapter Seam

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Create: `src/fitcv/agentic_cv_analysis.py`
- Create: `src/fitcv/agentic_cv_generation.py`
- Test: `tests/test_pipeline.py`
- Docs: `docs/FitCV-pipeline.md`, `docs/stages/cv_analysis.source.yaml`, `docs/stages/cv_generation.source.yaml`

- [ ] Step 1: Add failing coverage proving the original pipeline can route late-stage ranked jobs through a bounded adapter without changing stage order, checkpoint semantics, or deterministic validation ownership.
- [ ] Step 2: Introduce a config-owned late-stage adapter seam that defaults to original behavior.
- [ ] Step 3: Extract a minimal generation-ready analysis contract in original-repo terms, including explicit hold reasons.
- [ ] Step 4: Add the first bounded agentic generation entrypoint that consumes analysis output and still returns validator-owned accepted or rejected outcomes.
- [ ] Step 5: Re-run the focused pipeline tests and confirm both original and adapter-enabled paths pass.

## Task 2: Preserve Control-Plane Semantics While Surfacing Late-Stage Truth

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Test: `tests/test_fitcv_cp/`
- Docs: `docs/FitCV-pipeline.md`

- [ ] Step 1: Add failing tests that assert original trigger, run-mode, continue, and checkpoint behavior remain unchanged when the late-stage adapter is enabled.
- [ ] Step 2: Ensure stage-owned artifact surfaces can show explicit late-stage hold, accepted, and rejected outcomes without changing run lifecycle semantics.
- [ ] Step 3: Keep original run list and run detail information architecture intact while adding only narrowly scoped late-stage diagnostics where needed.
- [ ] Step 4: Re-run the relevant control-plane tests.

## Task 3: Upgrade CV Analysis Realism Without Shifting Ownership

**Files:**
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/evidence.py`
- Modify: `src/fitcv/gap_analysis.py`
- Test: `tests/test_pipeline.py`
- Docs: `docs/stages/cv_analysis.source.yaml`

- [ ] Step 1: Add failing tests for grounded evidence selection, readiness scoring transparency, and explicit pre-writing hold reasons.
- [ ] Step 2: Implement bounded analysis improvements that emit original-stage-owned outputs rather than a new runtime abstraction.
- [ ] Step 3: Confirm that blocked rows stay blocked before writing and that stage artifacts explain why.

## Task 4: Upgrade CV Generation Quality Without Relaxing Acceptance

**Files:**
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Test: `tests/test_pipeline.py`
- Docs: `docs/stages/cv_generation.source.yaml`

- [ ] Step 1: Add failing tests for borderline accepted drafts and validator-rejected drafts that should trigger bounded rewrite or repair behavior.
- [ ] Step 2: Implement stronger rewrite and repair from analysis signals while leaving validator-owned rejection authoritative.
- [ ] Step 3: Confirm unsupported claims and unresolved placeholders still reject when repair cannot truthfully fix them.

## Task 5: Refresh Docs And Generated Contracts

**Files:**
- Modify: `docs/features/cv_system/feature.source.yaml`
- Generated: `docs/features/cv_system/cv_system.yaml`
- Generated: `docs/features/cv_system/lineage.generated.yaml`
- Generated: `docs/features/cv_system/history.md`
- Generated: `docs/stages/cv_analysis.yaml`
- Generated: `docs/stages/cv_generation.yaml`
- Generated: `docs/generated/architecture_dag.yaml`
- Generated: `docs/generated/capability_lineage.yaml`

- [ ] Step 1: Update source docs only when the shipped contract truly changes.
- [ ] Step 2: Run `python scripts/sync_architecture_docs.py`.
- [ ] Step 3: Run `python scripts/sync_architecture_docs.py --check`.

## Task 6: Verify The Migration Spine

**Files:**
- Test: `tests/test_pipeline.py`
- Test: `tests/test_fitcv_cp/`

- [ ] Step 1: Run focused pipeline tests for late-stage analysis and generation.
- [ ] Step 2: Run focused control-plane tests for trigger, checkpoint, and run-detail behavior.
- [ ] Step 3: Run `git diff --check`.

## First Execution Slice

Start with Task 1 only:

1. Add a late-stage adapter seam in `src/fitcv/pipeline.py`.
2. Keep the default path original and deterministic.
3. Add one bounded agentic analysis handoff plus one bounded generation entrypoint.
4. Prove the seam with focused pipeline tests before touching control-plane behavior.

## Completion Checklist

- intent docs updated? no
- operating-system docs updated? no
- stage sources updated? pending
- stage contracts updated? pending
- feature sources updated? pending
- contract updated? pending
- feature lineage updated? pending
- feature history updated? pending
- other feature-specific docs updated? no
- cross-cutting docs updated? pending
- agent memory updated or explicitly not needed? not needed yet
- README updated? pending
- generated docs refreshed? pending
