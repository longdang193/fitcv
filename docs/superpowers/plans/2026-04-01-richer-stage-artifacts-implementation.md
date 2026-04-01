# Richer Stage Artifacts Implementation Plan

**Feature:** `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Spec:** `docs/superpowers/specs/2026-04-01-richer-stage-artifacts-design.md`  
**Type:** modify  
**Status:** in_progress  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Enrich the existing run-scoped `stage-artifacts.json` so each stage captures bounded input, decision, and output context instead of only high-level successful results.

**Architecture:** This rollout keeps the existing run-scoped `stage_transition_artifacts_json` and the existing download surfaces, but upgrades the per-stage block shape in `pipeline.py` to include `input_counts`, `output_counts`, `decision_summary`, `inputs_sample`, `outputs_sample`, and `dropped_or_changed_sample`. The settings snapshot remains separate in `settings_used_json`, and `cv_generation` may be richer than the other stages without introducing `run-bundle.json` or an in-page artifact viewer.

**Key Invariants:**
- Richer artifacts must continue using the existing stage-scoped model and must not introduce `run-bundle.json`.
- Each stage block must be captured from the live stage path, not reconstructed later from final outputs.
- Bounded sampling and truncation must prevent artifact growth from becoming unmanageable.
- The full effective settings snapshot remains a separate run-scoped artifact and is not duplicated wholesale into every stage block.
- `cv_generation` may be the richest stage, but `normalize`, `enrich`, `rule_filter`, `shortlist`, and `ranking` must all become materially more diagnostic.

**Rollout / Revert:**  
- rollback_trigger: richer stage blocks become too large, hide the stage boundary model, or still fail to explain stage transitions in confusing runs  
- rollback_method: revert the enriched stage-block schema and runtime capture changes together, returning to the simpler stage artifact summaries while preserving existing downloads  

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
  - `docs/superpowers/specs/2026-04-01-richer-stage-artifacts-design.md`
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
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/app.py`
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
- Test:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
  - `tests/test_fitcv_cp/test_app.py`

---

## Task 1: Lock the Richer Stage Block Contract in Tests

**Files:**
- Modify: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add failing tests that define the richer required keys for reachable stage blocks:
  - `stage_id`
  - `status`
  - `input_counts`
  - `output_counts`
  - `decision_summary`
  - `inputs_sample`
  - `outputs_sample`
  - `dropped_or_changed_sample`
- [x] Step 2: Add failing tests that assert required keys are present with empty objects/arrays when a stage is reached but has no sample rows.
- [x] Step 3: Add failing tests that assert unreached stages stay interpretable with `status: "not_reached"` and bounded empty structures.
- [x] Step 4: Run the failing pipeline tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py`
- [ ] Step 5: Commit.

## Task 2: Enrich Normalize, Enrich, and Rule Filter Blocks

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Implement richer `normalize` capture with:
  - raw input count
  - normalized count
  - deduplicated count
  - pre-enrichment rejected count
  - bounded `inputs_sample`, `outputs_sample`, and `dropped_or_changed_sample`
- [x] Step 2: Implement richer `enrich` capture with:
  - enrichment input/output counts
  - candidate profile summary used downstream
  - bounded enriched and failed/not-enriched samples
- [x] Step 3: Implement richer `rule_filter` capture with:
  - input/passed/rejected counts
  - grouped reject-reason summary
  - bounded passed/rejected samples
- [x] Step 4: Keep field selection compact and stage-local; do not embed the full settings object.
- [x] Step 5: Re-run the targeted pipeline tests and confirm the new stage blocks pass.
- [ ] Step 6: Commit.

## Task 3: Enrich Shortlist and Ranking Blocks

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Implement richer `shortlist` capture with:
  - passed input count
  - raw vector-hit count
  - scoring shortlist count
  - backfilled count
  - candidate query summary
  - bounded samples for passed inputs, shortlist outputs, and retrieval misses/backfills
- [x] Step 2: Implement richer `ranking` capture with:
  - scoring-input count
  - ranked count
  - authoritative `ranking_fit_label` distribution
  - active ranking-weights/defaults summary
  - bounded ranked and scored-not-ranked samples
- [x] Step 3: Add failing or expanded tests that prove confusing cases are visible in the stage artifact:
  - `not_shortlisted`
  - backfilled shortlist rows
  - scored-but-not-ranked rows
- [x] Step 4: Re-run the targeted pipeline tests and confirm pass.
- [ ] Step 5: Commit.

## Task 4: Enrich CV Generation Without Replacing CV Debug

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Expand `cv_generation` so it includes richer stage-local context for:
  - ranked inputs
  - attempted/accepted/skipped/failed counts
  - decision-chain context
  - evidence summary
  - gap explanation
  - validation summary
  - repair metadata summary
  - bounded output and dropped/changed samples
- [x] Step 2: Keep `cv_generation` aligned with the current stage artifact model and do not remove `cv-debug.json` in this rollout.
- [x] Step 3: Add failing or expanded tests that verify:
  - skipped rows appear in `dropped_or_changed_sample`
  - accepted rows appear in `outputs_sample`
  - the stage remains bounded and does not embed an unbounded duplicate of the full CV debug artifact
- [x] Step 4: Re-run the targeted pipeline tests and confirm pass.
- [ ] Step 5: Commit.

## Task 5: Enforce Sampling and Truncation Rules

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Implement one shared stage-artifact sampling helper or local equivalent with a default `sample_limit = 20`.
- [x] Step 2: Implement bounded truncation for heavy text fields so identifiers, statuses, and reasons survive while large text is trimmed.
- [x] Step 3: Add failing tests that verify:
  - samples are capped at 20
  - heavy text fields are truncated rather than causing the entire row to disappear first
  - persisted worker snapshots remain backward-compatible with the richer schema
- [x] Step 4: Run the targeted tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
- [x] Step 5: Implement the smallest passing boundedness change.
- [x] Step 6: Re-run the targeted tests and confirm pass.
- [ ] Step 7: Commit.

## Task 6: Preserve Existing Download Surfaces and Compatibility

**Files:**
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Confirm the richer artifact schema persists cleanly through the worker without requiring a new persistence column or route.
- [x] Step 2: Add or expand tests proving:
  - `Download Stage Artifacts JSON` still works with the richer schema
  - per-stage timeline downloads still return the correct stage slice
  - no new `run-bundle.json` or viewer route appears
- [x] Step 3: Run the targeted app/worker tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py -k "stage_artifacts or settings_used or run_detail"`
- [x] Step 4: Implement any required compatibility adjustments.
- [x] Step 5: Re-run the targeted tests and confirm pass.
- [ ] Step 6: Commit.

## Task 7: Sync Feature Contracts, Stage Contracts, and Histories

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
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Update the three feature contracts so they describe richer stage artifacts as input/output/decision debugging surfaces rather than simple summary blocks.
- [x] Step 2: Update the three history files to record the richer artifact adoption.
- [x] Step 3: Update the six stage contracts only as needed so the runtime artifact semantics remain compatible with stage-boundary truth.
- [x] Step 4: Re-read the spec and docs together to ensure:
  - no `run-bundle.json` drift was introduced
  - `settings_used.json` remains separate
  - `cv_generation` is allowed to be richest without forcing every stage to be equally heavy
- [ ] Step 5: Commit.

## Task 8: Final Verification and Consistency Pass

**Files:**
- Modify: `docs/superpowers/specs/2026-04-01-richer-stage-artifacts-design.md` only if terminology drift needs a bounded sync patch

- [x] Step 1: Run final focused verification:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py -k "stage_artifacts or settings_used or run_detail"`
- [x] Step 2: Review diffs for completeness and confirm:
  - each stage exposes bounded input/decision/output context
  - sampling is capped at 20 by default
  - no full-settings duplication was introduced
  - no `run-bundle.json` or viewer scope crept in
- [ ] Step 3: If terminology drifted during implementation, make one bounded sync patch to the spec.
- [ ] Step 4: Commit.

---

## Execution Order

1. Complete Task 1 first so the richer contract is pinned down in tests before runtime capture changes.
2. Complete Tasks 2 and 3 next so the earlier and middle pipeline stages become meaningfully diagnostic.
3. Complete Task 4 after that so `cv_generation` becomes richer without destabilizing the earlier contract work.
4. Complete Task 5 once all stage blocks exist, so one boundedness policy can be applied consistently.
5. Complete Task 6 after the richer schema is stable, ensuring existing download surfaces continue to work.
6. Complete Task 7 once runtime behavior is settled.
7. Complete Task 8 last so verification and any final spec sync reflect the full rollout.

## Verification Checklist

- [ ] Every reachable stage block contains required input/output/decision keys.
- [ ] Default row-oriented samples are capped at 20 unless a smaller stage-specific cap is justified.
- [ ] `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, and `cv_generation` all become more diagnostic than simple output summaries.
- [ ] `cv_generation` remains compatible with the separate `cv-debug.json` surface in this rollout.
- [ ] `settings_used.json` remains the single full-settings snapshot.
- [ ] Run-level and per-stage downloads still work without new persistence surfaces.
- [ ] No `run-bundle.json` or in-page artifact viewer was introduced.

## Risks and Notes

### Artifact Growth Risk

Richer stage blocks can become too large if sample rows or text fields are not bounded aggressively enough.

Mitigation:
- centralize the default sample cap at 20
- truncate heavy text before dropping useful identifiers and reasons
- keep stage samples focused on debugging-relevant fields only

### Hidden Recompute Risk

It is easy to accidentally populate richer samples by reconstructing them from later-stage or final outputs.

Mitigation:
- capture each stage sample from the live stage path where the rows actually exist
- add tests around dropped, backfilled, rejected, and scored-not-ranked rows

### Scope Drift Risk

This work could drift into a unified all-payloads bundle or artifact viewer.

Mitigation:
- keep the implementation limited to the existing `stage-artifacts.json`
- keep settings in `settings-used.json`
- treat `run-bundle.json` and viewer work as explicitly out of scope
