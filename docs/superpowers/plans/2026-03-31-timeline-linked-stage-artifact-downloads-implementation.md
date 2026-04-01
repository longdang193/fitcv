# Timeline-Linked Stage Artifact Downloads Implementation Plan

**Feature:** `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Spec:** `docs/superpowers/specs/2026-03-31-timeline-linked-stage-artifact-downloads-design.md`  
**Type:** modify  
**Status:** in_progress  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Add a dedicated run-scoped `settings-used.json` artifact plus download-only stage-slice links from the event timeline, without introducing an in-page artifact viewer or separate per-stage persistence.

**Architecture:** Phase 1.5 keeps the existing run-scoped `stage_transition_artifacts_json` as the backing source for all stage downloads, adds one dedicated `settings_used_json` persistence surface, and exposes stage-linked JSON downloads from recognized timeline events.

**Key Invariants:**
- `settings_used_json` persists the effective run settings once per run and is not duplicated into every stage block.
- Stage-slice downloads are derived from the stored `stage_transition_artifacts_json`, not stored independently.
- The timeline remains a download/navigation surface only; no stage artifact viewer is introduced in this rollout.
- Stage contracts continue to define boundary truth; downloaded stage JSON is only the runtime snapshot at that boundary.
- Existing `results_export_json`, `cv_generation_debug_json`, and run-level `stage_transition_artifacts_json` remain supported.

**Rollout / Revert:**  
- rollback_trigger: timeline-linked downloads create confusion, stage mapping proves unstable, or the new settings snapshot duplicates too much existing state  
- rollback_method: remove the settings snapshot persistence and timeline-linked download routes together, falling back to the existing run-level downloads only  

---

## Doc Update Matrix

- Feature contract:
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/cv_system/cv_system.yaml`
- Stage contracts:
  - `docs/stages/normalize.yaml`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/shortlist.yaml`
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_generation.yaml`
- Feature history:
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/cv_system/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/superpowers/specs/2026-03-31-timeline-linked-stage-artifact-downloads-design.md`
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
  - `inspection_debugging`
  - `trigger_run_management`
  - `cv_system`
- Primary lens: stage

## File Structure First

- Modify:
  - `src/fitcv_cp/models.py`
  - `src/fitcv_cp/bq_store.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/templates/run_detail.html`
  - `assets/bigquery/pipeline_runs.sql`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/cv_system/history.md`
  - `docs/stages/normalize.yaml`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/shortlist.yaml`
  - `docs/stages/ranking.yaml`
  - `docs/stages/cv_generation.yaml`
- Create:
  - `scripts/migrations/007_add_settings_used_json_to_pipeline_runs.py`
- Test:
  - `tests/test_fitcv_cp/test_bq_store.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_app.py`

---

## Task 1: Add the Run-Scoped Settings Snapshot Surface

**Files:**
- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `assets/bigquery/pipeline_runs.sql`
- Create: `scripts/migrations/007_add_settings_used_json_to_pipeline_runs.py`
- Test: `tests/test_fitcv_cp/test_bq_store.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add `settings_used_json` to the control-plane run model and BigQuery read/write helpers.
- [x] Step 2: Add the matching schema column and migration script for `pipeline_runs`.
- [x] Step 3: Write failing persistence tests covering:
  - storing `settings_used_json`
  - mapping it back through `_row_to_run`
  - keeping null/absent rows backward-compatible
- [x] Step 4: Run the failing persistence tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_bq_store.py`
- [x] Step 5: Implement the smallest passing persistence change.
- [x] Step 6: Re-run the targeted persistence tests and confirm pass.
- [ ] Step 7: Commit.

## Task 2: Persist the Settings Artifact from the Worker

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Test: `tests/test_fitcv_cp/test_worker_job.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Define a bounded `settings_used.json` payload shape built from the effective run settings already available to the worker.
- [x] Step 2: Write failing worker tests for:
  - persisting the settings snapshot on successful runs
  - keeping settings-snapshot persistence best-effort so failures do not fail the run
  - preserving clear provenance fields such as `config_path`
- [x] Step 3: Run the failing worker tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
- [x] Step 4: Implement the worker persistence hook for `settings_used_json`.
- [x] Step 5: Re-run the targeted worker tests and confirm pass.
- [ ] Step 6: Commit.

## Task 3: Add Stage-Slice Download Routes

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add one explicit server-side mapping from timeline event stage names to documented stage IDs.
- [x] Step 2: Add download routes for:
  - run-level `settings-used.json`
  - stage-slice JSON at `/admin/runs/{run_id}/stage-artifacts/{stage_id}.json`
- [x] Step 3: Keep stage-slice responses derived from stored `stage_transition_artifacts_json`, not rebuilt from other sources.
- [x] Step 4: Write failing app tests covering:
  - `settings-used.json` download
  - valid stage-slice download
  - invalid or unavailable stage download behavior
  - no regression to existing results/CV debug/stage-artifacts downloads
- [x] Step 5: Run the failing app tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py`
- [x] Step 6: Implement the smallest passing route changes.
- [x] Step 7: Re-run the targeted app tests and confirm pass.
- [ ] Step 8: Commit.

## Task 4: Add Download-Only Timeline Affordances

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Test: `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add a run-level `Download Settings Used JSON` button when the snapshot exists.
- [x] Step 2: Add timeline-row download affordances only for events that map cleanly to a documented stage ID.
- [x] Step 3: Keep the UI bounded:
  - links/buttons only
  - no stage viewer
  - no inline JSON rendering
- [x] Step 4: Write failing app tests covering:
  - settings download button visibility
  - timeline stage-download visibility for recognized events
  - no download link for unmapped events
- [x] Step 5: Run the failing app tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py`
- [x] Step 6: Implement the smallest passing template/server-context change.
- [x] Step 7: Re-run the targeted app tests and confirm pass.
- [ ] Step 8: Commit.

## Task 5: Sync Stage and Feature Docs

**Files:**
- Modify: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Modify: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/inspection_debugging/history.md`
- Modify: `docs/features/trigger_run_management/history.md`
- Modify: `docs/features/cv_system/history.md`
- Modify: `docs/stages/normalize.yaml`
- Modify: `docs/stages/enrich.yaml`
- Modify: `docs/stages/rule_filter.yaml`
- Modify: `docs/stages/shortlist.yaml`
- Modify: `docs/stages/ranking.yaml`
- Modify: `docs/stages/cv_generation.yaml`

- [x] Step 1: Update the three feature contracts to mention:
  - the dedicated `settings-used.json`
  - timeline-linked stage downloads
  - the continued download-only scope
- [x] Step 2: Update the three history files to record the new artifact set.
- [x] Step 3: Update the six stage contracts only as needed so each stage remains compatible with the new per-stage download surface.
- [x] Step 4: Verify the docs still preserve the split:
  - stage contracts = boundary truth
  - settings-used JSON = run config snapshot
  - stage downloads = runtime stage snapshot slices
- [ ] Step 5: Commit.

## Task 6: Final Consistency Pass and Verification

**Files:**
- Modify: `docs/superpowers/specs/2026-03-31-timeline-linked-stage-artifact-downloads-design.md` only if terminology drift needs correction

- [x] Step 1: Re-read the updated spec, worker/app paths, feature contracts, and stage contracts together.
- [x] Step 2: Confirm an operator can answer:
  - where to get the full settings used by a run
  - where to get the full stage-artifacts JSON
  - how to download one stage directly from the timeline
- [x] Step 3: Run final focused verification:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_bq_store.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py`
- [ ] Step 4: If terminology drifted during implementation, make one bounded sync patch to the spec.
- [x] Step 5: Review diffs for completeness and confirm:
  - no in-page artifact viewer was introduced
  - settings were not duplicated into every stage block
  - stage slices are derived from stored stage artifacts rather than separately persisted
  - no generated-discovery work was accidentally pulled into this rollout
- [ ] Step 6: Commit.

---

## Execution Order

1. Complete Task 1 first so the new settings snapshot has a persistence surface.
2. Complete Task 2 next so the worker produces the new run-scoped settings artifact.
3. Complete Task 3 once both backing snapshots exist, so the new download routes have stable sources.
4. Complete Task 4 after the routes exist, keeping the UI strictly download-only.
5. Complete Task 5 once the runtime surfaces are stable.
6. Complete Task 6 last so verification and wording review cover the full end-to-end slice.

## Verification Checklist

- [x] `pipeline_runs` can persist `settings_used_json`.
- [x] The worker persists `settings_used_json` best-effort on successful runs.
- [x] A succeeded run can download `settings-used.json`.
- [x] A succeeded run can download a single stage slice derived from `stage_transition_artifacts_json`.
- [x] Timeline rows for recognized stage-boundary events expose stage download links.
- [x] Unmapped timeline rows do not show fake stage downloads.
- [x] The rollout remains download-only; no artifact viewer was introduced.
- [x] Full effective settings are not duplicated into every stage block.

## Risks and Notes

### Mapping Drift Risk

Timeline event names and documented stage IDs can drift.

Mitigation:
- centralize the event-to-stage mapping in one server-side constant/function
- test both mapped and unmapped events

### Config Duplication Risk

It is easy to accidentally embed the full settings object into stage blocks.

Mitigation:
- persist one dedicated `settings_used_json`
- keep stage blocks limited to stage-local summaries plus optional `relevant_setting_keys`

### UI Scope-Creep Risk

Once timeline links exist, it is tempting to add modals or inline viewers immediately.

Mitigation:
- keep this rollout download-only
- defer any viewer design to a later focused spec
