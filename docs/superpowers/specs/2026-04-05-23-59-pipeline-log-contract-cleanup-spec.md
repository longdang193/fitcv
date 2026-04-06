---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Tighten pipeline log contracts, close the unresolved-placeholder validation gap, prefer canonical config and prompt provenance, reduce redundant aggregate payloads, and make late-stage debug coverage easier to interpret."
invariants:
  - Stage-local artifacts remain the primary per-stage debugging surface.
  - The pipeline must not accept generated CVs containing unresolved template placeholders.
  - Compatibility support in runtime config access may remain, but exported logs must distinguish canonical truth from legacy compatibility projection.
  - Prompt provenance must identify the actual active runtime prompt contract, not only a version label.
  - Aggregate run exports should stay useful for operators without silently duplicating the full detail contract of every stage artifact.
---

# Pipeline Log Contract Cleanup

## Triage

Feature type: MODIFY  
Summary: Clean up exported pipeline log contracts so run artifacts reflect the centralized config/prompt system more accurately, close the accepted-placeholder validation bug, reduce redundant aggregate payloads, and improve coverage explanations for late-stage debug logs.  
Reasoning: The audit of `logs/fitcv-run-f8db5e7f-49ff-4c10-a3a3-79b6c11a6e75-*` shows both artifact drift and one real correctness bug: a succeeded run accepted `[Candidate Name]` in the final CV. This is still primarily a modification to inspection/debugging and export behavior, but it must also tighten the CV-generation validation contract where the artifact exposed a real bug.  
Invariants:
- Stage-local artifacts remain the authoritative run-scoped debug surface for one stage.
- `settings-used.json` must describe canonical effective settings first, not compatibility-era aliases as equal truths.
- `cv_generation` provenance must expose the actual active structured prompt contract.
- `ranking` provenance must expose the actual active AI scoring prompt contract.
- `cv-debug.json` must explain missing late-stage records instead of making operators infer gaps by cross-checking other files.
- Aggregate exports must remain bounded and operator-friendly.
Dependencies:
- `src/fitcv/pipeline.py`
- `src/fitcv/cv_generator.py`
- `src/fitcv/config.py`
- `src/fitcv/validator.py`
- `src/fitcv_cp/worker_job.py`
- `src/fitcv_cp/app.py`
- exported run artifacts under `logs/`
Affected stages:
- enrich
- shortlist
- ranking
- cv_analysis
- cv_generation
Affected features:
- inspection_debugging
- settings_system
- cv_system
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `none`
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: `none`
  generated:
    - `none`
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Migration needed: no
Risk level: medium

## Problem

The current exported artifacts are operationally useful, but the log audit revealed four classes of cleanup issues:

1. **Correctness gap**
- A succeeded run still accepted a CV with the unresolved placeholder `[Candidate Name]`.
- The validator does check unresolved placeholders, but the current pattern set does not cover the accepted placeholder variant that appeared in the artifact.

2. **Contract drift**
- `settings-used.json` exports both canonical nested config and legacy flat compatibility keys as if they were equally authoritative.
- `cv_generation.json` still reports `cv_prompt_version` instead of the actual centralized prompt identity that now governs runtime behavior.
- `ranking.json` exposes weights, thresholds, and reuse, but not the active AI scoring prompt/model provenance for the stage that actually generated the AI score.

3. **Coverage ambiguity**
- `cv-debug.json` can show fewer debug records than ranked jobs without explaining how many ranked jobs were never attempted for generation and why that is expected.

4. **Aggregate redundancy**
- `stage-artifacts.json` bundles full stage payloads that are already persisted as dedicated per-stage files.
- `results.json` usefully summarizes run outcomes, but it also repeats some high-detail debug structures already available elsewhere.

These issues mean the exported debug contract is noisier and more misleading than it should be, and in one case the artifact is exposing a real validator bug rather than a logging-only problem.

## Goals

- Close the unresolved-placeholder acceptance bug in `cv_generation` validation.
- Make exported settings snapshots prefer canonical config ownership.
- Make CV-generation prompt provenance identify the real active structured prompt contract.
- Make ranking artifacts identify the active AI scoring prompt/model contract.
- Make late-stage debug coverage self-explanatory.
- Reduce redundant or oversized aggregate log surfaces without losing the operator workflows they support.
- Preserve the strengths of existing stage-local artifacts such as:
  - enrich prompt provenance
  - shortlist retrieval and embedding reuse provenance
  - ranking calibration and reuse metrics
  - `cv_analysis` evidence-selection diagnostics

## Non-Goals

- Changing ranking, retrieval, or CV-writing semantics beyond the placeholder-validation fix.
- Removing per-stage artifacts.
- Replacing compatibility support in runtime config loading.
- Introducing a brand-new log storage format.
- Redesigning the control-plane UI in this cleanup.

## Current Audit Summary

### Strong artifacts

- `enrich.json`
  - already exports prompt ID, template path, model, and fresh-vs-reused row counts
- `shortlist.json`
  - already exports query reuse status, embedding reuse counts, and `settings_refs`
- `ranking.json`
  - already exports configured weights, fit-label counts, quality metrics, reuse metrics, and `settings_refs`
- `cv_analysis.json`
  - already exports effective channel pool size, embedding fresh/reused counts, reuse metrics, and `unselected_top_candidates`

### Weaker / drifting artifacts

- `results.json`
  - currently exposes the accepted placeholder bug clearly, which means the artifact itself is correct but the pipeline contract behind it is not
- `settings-used.json`
  - exposes canonical nested config and compatibility-era flat keys side by side
- `cv_generation.json`
  - exposes `cv_prompt_version` instead of the active prompt ID/runtime prompt contract
- `ranking.json`
  - exposes ranking calibration and reuse well, but not the active AI scoring prompt/model provenance
- `cv-debug.json`
  - exposes `ranked_jobs_total` and `debug_records_captured`, but not a clear explanation of omitted ranked jobs

### Redundant aggregate artifacts

- `stage-artifacts.json`
  - acts as a bundled copy of per-stage artifacts
- `results.json`
  - appropriately acts as the run summary export, but currently carries some repeated deep-debug context too

## Design

### 1. Close unresolved-placeholder acceptance

The cleanup must tighten the CV-generation validation path so unresolved placeholders such as:

- `[Candidate Name]`
- `[Your Name]`

cannot be accepted in a succeeded run.

This is a correctness fix, not only an export cleanup. The exported artifacts should continue to show the accepted output, but after this rollout the validator must block these unresolved placeholders deterministically.

### 2. Canonical settings export

`settings-used.json` should export:

- canonical effective settings as the primary `effective_settings`
- optional compatibility metadata in a separate block, for example:
  - `compatibility_projection`
  - `legacy_aliases_emitted`

It should no longer present legacy flat keys like:

- `vector_top_n`
- `rerank_top_n`
- `cv_generation_model`
- `cv_max_pages`

as if they are equal peers to:

- `pipeline.vector_search_top_n`
- `pipeline.ai_score_top_n`
- `cv.generation.model`
- `cv.validation.max_pages`

If compatibility-era values are still needed for debugging, they must be explicitly labeled as derived compatibility output rather than canonical settings truth.

### 3. Stronger CV-generation prompt provenance

`cv_generation.json` and related run-level exports should report the active prompt contract using the centralized prompt system. The minimum target is:

- `cv_prompt_id`
- `cv_prompt_template_path`
- `cv_generation_model`

`cv_prompt_version` may remain only as a secondary convenience field if it is clearly derived from the prompt contract, not the primary provenance field.

This should align the CV-generation artifact with the stronger enrich-stage prompt provenance pattern.

### 4. Ranking AI-scoring prompt provenance

`ranking.json` and any related run-level exports that summarize ranking behavior should report the active AI scoring contract used for reranker scoring. The minimum target is:

- `ranking_prompt_id`
- `ranking_prompt_template_path`
- `ai_score_model`

This should make ranking-stage diagnostics self-sufficient when investigating AI-score drift across runs.

### 5. Clearer CV-debug coverage accounting

`cv-debug.json` should distinguish:

- ranked jobs total
- generation-attempted jobs total
- debug records captured
- ranked jobs skipped before generation

It should also expose a compact skipped summary, for example:

- `skipped_fit_gate_count`
- `non_attempted_ranked_jobs_total`
- `omission_reason_counts`

This allows an operator to understand why `debug_records_captured < ranked_jobs_total` without opening other exports.

### 6. Aggregate artifact responsibility split

The cleanup should preserve two different aggregate exports, but with clearer responsibility:

- `results.json`
  - run summary and per-job business outcome surface
- `stage-artifacts.json`
  - run-scoped bundle of stage artifacts

The contracts should be tightened so:

- `results.json` prefers summary/debug fields that support operator outcome interpretation
- `stage-artifacts.json` remains the bundle export for stage-level inspection

This cleanup does **not** require deleting either file, but it should remove obviously duplicated deep-detail blocks when one aggregate export is simply mirroring the other without adding value.

### 7. Stage-local artifact pattern as the standard

The project should standardize around the strongest current stage-artifact pattern:

- stage-local artifact owns:
  - stage counts
  - decision summary
  - bounded inputs sample
  - bounded outputs sample
  - settings refs when applicable
  - prompt provenance when stage-owned prompts exist
  - reuse metrics when stage-owned reuse exists

This cleanup should treat:

- `enrich.json`
- `shortlist.json`
- `ranking.json`
- `cv_analysis.json`

as the reference pattern to align the remaining weaker artifacts against.

## Proposed Contract Changes

### Placeholder validation

Add or tighten:
- unresolved placeholder detection for the accepted placeholder variants observed in real outputs

Keep:
- artifact visibility of the final generated output for debugging

### `settings-used.json`

Add or preserve:
- canonical nested settings
- source attribution

Retire from primary effective settings:
- duplicated flat compatibility keys

Optional:
- add a dedicated `compatibility_projection` block if still needed

### `cv_generation.json`

Add:
- `cv_prompt_id`
- `cv_prompt_template_path`

Keep:
- `cv_generation_model`

Demote or retire:
- `cv_prompt_version` as sole provenance field

### `ranking.json`

Add:
- `ranking_prompt_id`
- `ranking_prompt_template_path`
- `ai_score_model`

Keep:
- configured weights
- thresholds
- reuse metrics

### `cv-debug.json`

Add:
- `attempted_generation_jobs_total`
- `non_attempted_ranked_jobs_total`
- `omission_reason_counts`

Keep:
- `ranked_jobs_total`
- `debug_records_captured`

### `results.json`

Keep:
- run summary
- top-level shortlist debug
- stage quality metrics
- late-stage reuse metrics
- per-job result records

Review and reduce:
- repeated high-detail nested blocks that are already fully owned by stage artifacts

### `stage-artifacts.json`

Keep:
- bundle structure
- stage artifact snapshots

Review:
- whether any run-level wrapper fields are redundant with stage-local files and can be simplified

## Rollout Notes

- This is an artifact-contract cleanup, so runtime behavior should remain unchanged.
- Exception: unresolved placeholder acceptance in `cv_generation` validation must be fixed.
- Backward compatibility is desirable for one migration window where practical, especially for:
  - `cv_prompt_version`
  - compatibility projections in settings export
- The UI should continue to work if it consumes existing run summary fields; this rollout is mainly about making exported JSON cleaner and more truthful.

## Verification Expectations

- Compare new exports against one representative full successful run.
- Verify:
  - unresolved placeholder CVs are rejected deterministically
  - canonical settings appear once as the main truth source
  - CV-generation prompt provenance includes the active prompt ID
  - ranking artifacts include AI-scoring prompt/model provenance
  - CV-debug clearly explains missing ranked jobs
  - no important stage-local diagnostics are lost
- Confirm run detail and export endpoints still load the cleaned artifacts correctly.

## Expected Outcome

After this cleanup:

- unresolved placeholder CVs can no longer be accepted
- operators can trust `settings-used.json` as the canonical settings snapshot
- operators can identify the exact active CV-generation prompt contract
- operators can identify the exact active ranking AI-scoring prompt contract
- operators can understand CV-debug coverage without cross-referencing multiple files
- aggregate exports remain useful but less redundant
- stage-local artifacts stay the preferred deep-debug surface
