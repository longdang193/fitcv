# Stage Transition Artifacts Implementation Plan

**Feature:** `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Spec:** `docs/superpowers/specs/2026-03-31-stage-transition-artifacts-design.md`  
**Type:** modify  
**Status:** in_progress  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Persist one bounded run-scoped stage transition artifact so each major pipeline handoff can be inspected directly without reconstructing stage outputs later.

**Architecture:** Phase 1 adds a single run-scoped JSON artifact with explicit blocks for `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation`. The implementation should capture each block from the live runtime seam, reuse existing CV-generation debug capture where possible, and keep the artifact aligned with the documented stage contracts in `docs/stages/*.yaml`.

**Key Invariants:**
- Each stage block is captured from the live runtime path, not reconstructed later from final outputs.
- Stage artifacts remain debugging/inspection surfaces, not new systems of record.
- Runtime artifact blocks stay aligned to the documented stage contracts.
- The first rollout remains bounded and does not duplicate the full heavy CV-generation payload.

**Rollout / Revert:**  
- rollback_trigger: artifact capture adds confusion, excessive storage growth, or stage-block semantics drift from the documented stage boundaries  
- rollback_method: revert the new persistence/download path and runtime stage capture hooks together, returning to the existing run export and CV debug snapshot only  

---

## Doc Update Matrix

- Feature contract:
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
- Stage contracts:
  - `docs/stages/normalize.yaml`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/shortlist.yaml`
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_generation.yaml`
- Feature history:
  - `docs/features/cv_system/history.md`
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/inspection_debugging/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/superpowers/specs/2026-03-31-stage-transition-artifacts-design.md`
- README: `none`
- Generated discovery: `none`

## Stage and Feature Scope

- Affected stages:
  - `normalize`
  - `enrich`
  - `rule_filter`
  - `shortlist`
  - `ranking`
  - `cv_generation`
- Affected features:
  - `cv_system`
  - `trigger_run_management`
  - `inspection_debugging`
- Primary lens: stage

## File Structure First

- Modify:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/models.py`
  - `src/fitcv_cp/bq_store.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/templates/run_detail.html`
  - `assets/bigquery/pipeline_runs.sql`
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/cv_system/history.md`
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/inspection_debugging/history.md`
  - `docs/stages/normalize.yaml`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/shortlist.yaml`
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_generation.yaml`
- Create:
  - `scripts/migrations/006_add_stage_transition_artifacts_json_to_pipeline_runs.py`
- Test:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_app.py`

---

## Task 1: Define the Run-Scoped Artifact Persistence Surface

**Files:**
- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `assets/bigquery/pipeline_runs.sql`
- Create: `scripts/migrations/006_add_stage_transition_artifacts_json_to_pipeline_runs.py`
- Test: `tests/test_fitcv_cp/test_bq_store.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add the new run-scoped persistence field for the stage transition artifact to the control-plane model and BigQuery write/read paths.
- [x] Step 2: Add the matching BigQuery schema update and migration script for the new artifact field on `pipeline_runs`.
- [x] Step 3: Write failing persistence tests covering:
  - storing a bounded stage artifact JSON
  - reading it back through the run model
  - best-effort behavior when the field is absent or null
- [x] Step 4: Run the failing test and confirm the new field is not yet wired end to end:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_bq_store.py`
- [x] Step 5: Implement the smallest passing persistence change.
- [x] Step 6: Re-run the targeted persistence tests and confirm pass.
- [ ] Step 7: Commit.

## Task 2: Capture Live Stage Blocks in the Runtime Pipeline

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Test: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Define one explicit runtime capture seam for each stage block:
  - `normalize`
  - `enrich`
  - `rule_filter`
  - `shortlist`
  - `ranking`
  - `cv_generation`
- [x] Step 2: Write failing pipeline tests covering:
  - stage blocks are present even when a run stops early
  - `normalize`, `shortlist`, and `ranking` capture the most important counts/summaries
  - `cv_generation` remains summarized rather than duplicating the full existing heavy debug payload
- [x] Step 3: Run the failing test and confirm the runtime does not yet assemble the new stage artifact:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py`
- [x] Step 4: Implement bounded runtime capture for the five lighter stage blocks and a summarized `cv_generation` block that reuses existing Layer 4 debug capture where appropriate.
- [x] Step 5: Ensure unreached stages remain present with `status: "not_reached"` and interpretable empty content.
- [x] Step 6: Re-run the targeted pipeline tests and confirm pass.
- [ ] Step 7: Commit.

## Task 3: Persist the Assembled Artifact from the Worker

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Test: `tests/test_fitcv_cp/test_worker_job.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Write failing worker tests for:
  - persisting the completed stage artifact on successful runs
  - keeping persistence best-effort so artifact failures do not fail the run
  - preserving partial/snapshot-complete semantics when runtime capture is incomplete
- [x] Step 2: Run the failing worker tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
- [x] Step 3: Implement the worker persistence hook for the assembled stage artifact JSON.
- [x] Step 4: Re-run the targeted worker tests and confirm pass.
- [ ] Step 5: Commit.

## Task 4: Expose a Minimal Admin Download Surface

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Test: `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add the admin download endpoint/action for the stage transition artifact.
- [x] Step 2: Keep the UI bounded to:
  - one download action
  - optional minimal completeness indicator only if it fits the current run-detail layout cleanly
- [x] Step 3: Write failing app tests covering:
  - the button appears only when the artifact exists
  - the download route returns the stored JSON
  - this does not replace existing results export or CV debug downloads
- [x] Step 4: Run the failing app tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py`
- [x] Step 5: Implement the smallest passing UI/control-plane change.
- [x] Step 6: Re-run the targeted app tests and confirm pass.
- [ ] Step 7: Commit.

## Task 5: Align Stage Docs and Feature Contracts with the Artifact Surface

**Files:**
- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Modify: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Modify: `docs/features/cv_system/history.md`
- Modify: `docs/features/trigger_run_management/history.md`
- Modify: `docs/features/inspection_debugging/history.md`
- Modify: `docs/stages/normalize.yaml`
- Modify: `docs/stages/enrich.yaml`
- Modify: `docs/stages/rule_filter.yaml`
- Modify: `docs/stages/shortlist.yaml`
- Modify: `docs/stages/ranking.yaml`
- Modify: `docs/stages/cv_generation.yaml`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Update the three feature contracts so they explicitly mention the new stage-transition artifact surface where relevant.
- [x] Step 2: Update the three feature history files to record the new run-scoped artifact capability.
- [x] Step 3: Update the six stage contracts only as needed so each stage boundary stays compatible with the runtime artifact block that now captures it.
- [x] Step 4: Verify the stage docs still own boundary truth while the artifact feature owns runtime inspection payloads.
- [ ] Step 5: Commit.

## Task 6: Final Consistency Pass and Verification

**Files:**
- Modify: `docs/superpowers/specs/2026-03-31-stage-transition-artifacts-design.md` only if terminology drift needs correction
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Re-read the updated stage contracts, feature contracts, worker/app paths, and the stage-transition-artifacts spec together.
- [x] Step 2: Confirm a reader/operator can answer:
  - what each stage boundary is
  - what runtime artifact block captures that boundary
  - where to download or inspect that artifact
- [x] Step 3: Run final focused verification:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_bq_store.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py`
- [ ] Step 4: If terminology drifted during implementation, make one bounded sync patch to the spec.
- [x] Step 5: Review diffs for completeness and confirm:
  - the artifact stayed bounded
  - no recomputation path was introduced
  - no generated-discovery work was accidentally pulled into this rollout
- [ ] Step 6: Commit.

---

## Execution Order

1. Complete Task 1 first so the persistence surface exists before runtime capture is wired to it.
2. Complete Task 2 next so the live runtime stage blocks are assembled against a known destination and test shape.
3. Complete Task 3 after runtime capture exists, so the worker can persist the assembled artifact.
4. Complete Task 4 once the artifact can actually be stored and retrieved.
5. Complete Task 5 after the runtime surface is stable, so docs describe the implemented artifact instead of the pre-rollout draft.
6. Complete Task 6 last so verification and final wording review cover the full end-to-end slice.

## Verification Checklist

- [x] `pipeline_runs` can persist a bounded stage transition artifact JSON.
- [x] Runtime capture produces explicit blocks for `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation`.
- [x] Unreached stages remain interpretable with explicit `not_reached` semantics.
- [x] `cv_generation` summary reuses existing debug capture where appropriate instead of duplicating the full heavy payload.
- [x] The worker persists the artifact best-effort.
- [x] Admin run detail exposes a download action for the new artifact without replacing existing export/debug downloads.
- [x] Stage contracts and feature contracts remain aligned with the new runtime artifact surface.
- [x] No generated discovery work was pulled into this rollout.

## Risks and Notes

### Storage Bloat Risk

The artifact can grow quickly if stage samples or text fields are not tightly bounded.

Mitigation:
- keep every stage block summary-first
- sample only key rows and identifiers
- keep the `cv_generation` block summarized instead of embedding the full existing debug payload again

### Boundary Drift Risk

Runtime stage blocks can become inconsistent with the documented stage contracts.

Mitigation:
- treat `docs/stages/*.yaml` as the stage-boundary truth
- update stage docs only when the artifact rollout reveals a real boundary mismatch
- do one final source-layer consistency pass before completion

### Scope-Creep Risk

This could easily expand into a broader storage redesign or in-page stage explorer.

Mitigation:
- keep persistence to one run-scoped JSON in Phase 1
- keep UI to one download action plus minimal completeness visibility at most
- defer broader table/query and generated-discovery work to later follow-up
