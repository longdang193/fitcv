---
feature_type: modify
feature_name: inspection_debugging
status: draft
summary: "Tighten the boundary between job-ledger exports and stage diagnostics so small runs stop producing two overlapping heavy artifacts."
invariants:
  - "`results.json` remains the operator-facing per-job ledger."
  - "`stage-artifacts.json` remains the bundled stage diagnostics export."
  - "No artifact download route may recompute pipeline outputs during export."
  - "Per-stage JSON files remain the deepest source for stage-local debugging."
---

# Results Ledger And Stage Diagnostics Boundary Tightening

## Triage

Feature type: MODIFY
Summary: Tighten `results.json` into a compact job ledger and keep deep debug detail owned by `stage-artifacts.json` and per-stage artifacts.
Reasoning: The current artifact contract still duplicates substantial stage-derived context across `results.json` and `stage-artifacts.json`, making even small successful runs produce two heavy overlapping exports.
Invariants:
  - `results.json` stays job-centric and readable for operators.
  - `stage-artifacts.json` stays the convenience diagnostics bundle.
  - Per-stage JSONs continue to own stage-local samples, counts, and diagnostics.
  - Existing individual artifact downloads remain available.
Dependencies:
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/app.py`
Affected stages:
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
Affected features:
  - inspection_debugging
  - pipeline_performance
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history: `docs/features/inspection_debugging/history.md`
  feature_docs:
    - `docs/features/pipeline_performance/history.md`
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

The current export split is directionally correct but still too loose:

- `results.json` is intended to be the run's per-job ledger.
- `stage-artifacts.json` is intended to be the bundled stage diagnostics export.

In practice, `results.json` still embeds a large amount of stage-derived context per row:

- `original_job`
- `enriched_job`
- `scores`
- `cv_analysis`
- `decision_chain`
- `cv`

At the same time, `stage-artifacts.json` intentionally includes:

- stage `input_counts`
- stage `output_counts`
- stage `decision_summary`
- `inputs_sample`
- `outputs_sample`
- `dropped_or_changed_sample`

That means two large exports are both carrying overlapping views of the same stage progression.

## Evidence

For run `d4a4ea1f-4292-4d47-bcc8-38f503f6c5e8`:

- [results.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-d4a4ea1f-4292-4d47-bcc8-38f503f6c5e8-artifacts/results.json) is `425,031` bytes
- [stage-artifacts.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-d4a4ea1f-4292-4d47-bcc8-38f503f6c5e8-artifacts/stage-artifacts.json) is `412,747` bytes

The row builder in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L553) shows that `results.json` rows still include substantial stage-derived payloads. The stage bundle builder in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L1651) and the late-stage sample blocks in [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2121) and [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py#L2161) show that the same run context is also being preserved in stage diagnostics. The worker then persists both independently in [worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/worker_job.py#L114) and [worker_job.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/worker_job.py#L252).

## Root Cause

The root cause is contract drift, not one isolated bug.

### 1. `results.json` is still acting partly like a debug artifact

The current per-row payload is too rich for a ledger export. It carries not just final job outcomes, but also significant stage snapshots and explanation structures.

This makes the operator-facing ledger expensive in size and fuzzy in purpose.

### 2. `stage-artifacts.json` is correctly rich, but overlaps with the ledger

The stage bundle is doing the right kind of work for diagnostics. The issue is not that it is rich; the issue is that the ledger still duplicates too much of the same story.

### 3. The worker persists both rich shapes side by side

There is no final slimming pass that enforces a hard boundary between:

- job outcome fields
- stage debugging fields

So both exports are allowed to grow independently.

## Design Goals

1. Make `results.json` feel like a compact operator ledger.
2. Keep `stage-artifacts.json` as the one-click diagnostics bundle.
3. Keep per-stage JSONs as the authoritative deep debug files.
4. Reduce artifact size and overlap without removing important debugging capability.
5. Preserve compatibility where practical, but favor cleaner ownership going forward.

## Proposed Contract

### `results.json` ownership

`results.json` should answer:

- what happened to each job
- where it stopped
- why it stopped
- what final output exists for it

Keep in each result row:

- `job_url`
- `job_title`
- `company`
- compact canonical context:
  - `location_type`
  - `domain`
- `pipeline_status`
- `reject_reasons`
- `rule_filter_marks`
- compact score outcome facts:
  - `final_score`
  - `ai_score`
  - `vector_score`
  - `fit_label`
  - `final_rank`
- compact `cv_analysis` outcome facts:
  - `status`
  - `analysis_reuse_status`
  - `analysis_input_fingerprint`
- compact `decision_chain`
- compact final `cv` outcome metadata

Remove from each result row:

- `original_job`
- full `enriched_job`
- heavy score explanation substructures such as:
  - `feature_contributions`
  - `preference_fit_components`
- any row-level stage-debug structures that are already owned by stage artifacts

If some enriched context is still needed for operator usability, keep only a bounded compact snapshot rather than the full enriched job object.

### `stage-artifacts.json` ownership

`stage-artifacts.json` should continue to own:

- per-stage counts
- decision summaries
- settings refs
- prompt/model provenance
- reuse metrics
- bounded stage samples
- late-stage evidence-selection diagnostics

This remains the convenience bundle for diagnostics and should stay intentionally richer than `results.json`.

### Per-stage JSON ownership

Per-stage JSON files remain the deepest stage-local debug surface and should not be slimmed merely to compensate for bundle size.

## Boundary Rules

The following rules should hold after the cleanup:

1. A field that is mainly useful for explaining one job's final path belongs in `results.json`.
2. A field that is mainly useful for explaining stage behavior belongs in stage artifacts.
3. A field should not appear in both places unless it is intentionally a tiny summary and the duplication is explicitly justified.
4. `results.json` should prefer compact normalized summaries over full snapshots.

## Backward-Compatibility Strategy

Use a versioned contract bump for `results.json`.

- Existing consumers should continue to work if they only depend on current top-level summary plus row outcome fields.
- Consumers that rely on removed heavy row payloads should migrate to:
  - `stage-artifacts.json`, or
  - the relevant per-stage JSON

The migration should be explicit in docs and artifact descriptions.

## UI / Export Surface Impact

No route removals are required.

The main user-facing change is conceptual clarity:

- `Results JSON (Job Ledger)` becomes smaller and more obviously operator-facing.
- `Stage Artifacts JSON (Diagnostics)` remains the heavy debug surface.
- `Download All Artifacts (.zip)` continues to include both, but the contents become less redundant.

## Non-Goals

- changing stage algorithms
- recomputing pipeline outputs during export
- removing per-stage JSON downloads
- redesigning run-detail UI beyond any wording needed to reflect the tighter contract

## Risks

- Some internal or ad hoc consumers may still depend on heavy row fields in `results.json`.
- Trimming too aggressively could remove context that the run-detail UI still expects indirectly.

These should be handled by:

- targeted contract tests
- explicit audit of run-detail consumers
- versioned artifact documentation

## Recommended Outcome

After this cleanup:

- `results.json` should be clearly smaller
- `stage-artifacts.json` should remain diagnostic-heavy
- the two exports should complement each other instead of telling the same story twice
