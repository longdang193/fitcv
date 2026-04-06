---
feature_type: modify
feature_name: settings_system
status: draft
summary: "Simplify the admin settings UI by removing low-value pseudo-choice controls from the active edit surface and reorganizing the page around operator tasks, advanced disclosure, and clearer current-vs-draft feedback."
invariants:
  - "No live runtime setting may be removed from the active contract unless it is truly unused or explicitly reclassified as metadata."
  - "The admin UI must stay aligned with the canonical settings contract in `settings_schema.py`."
  - "Settings changes must remain append-only and take effect on future runs only."
---

# Settings UI Usability And Contract Cleanup

## Triage

Feature type: MODIFY  
Summary: Redesign the admin settings UI so it is easier to use, more consistent, and more honest about which controls are meaningful choices versus fixed runtime metadata.  
Reasoning: The current settings system is active and broadly wired, but the UI is still heavy, overly flat, and exposes a few low-value controls as if they were meaningful decisions. This is a contract and usability refinement, not a new feature.  
Invariants:
- no currently live runtime control should silently disappear from the effective settings contract
- canonical nested settings remain the source of truth for admin editing
- settings persistence, validation, and grouped-save behavior must remain intact
Dependencies:
- `admin_control_plane_core`
- `settings_system`
- `ui_consistency_theming`
Affected stages:
- none
Affected features:
- `settings_system`
- `admin_control_plane_core`
Primary lens: feature
Affected docs:
  feature_yaml: `docs/features/settings_system/settings_system.yaml`
  feature_history: `docs/features/settings_system/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

The current admin settings page is technically functional, but it is still harder to operate than it needs to be.

The main issues are:

1. the page is organized like a registry dump rather than an operator task surface
2. all settings receive roughly equal visual priority, even though some are routine controls and some are niche tuning knobs
3. a few settings are active in code but not meaningful choices in practice because only one supported option exists
4. the current UI does not make unsaved changes, effective values, and operator impact clear enough

This produces a page that is accurate enough for engineers but still more cognitively expensive than it should be for everyday admin use.

## Current-State Audit

### A. Truly unused active settings

No fully unused active setting was found in the current `e2e-opt` admin surface.

The visible settings in:

- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/settings_schema.py)

are wired into runtime or control-plane behavior through modules such as:

- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/pipeline.py)
- [enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/enrich.py)
- [ai_score.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/ai_score.py)
- [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/evidence.py)
- [validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/validator.py)
- [app.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv_cp/app.py)

So this cleanup should not be framed as “remove lots of dead settings.”

### B. Low-value or pseudo-choice controls

Two settings are technically active but not meaningful operator choices right now:

1. `cv_preset`
- only one preset is currently supported
- [cv_presets.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/cv_presets.py) currently supports only `europass`
- presenting it as a normal editable dropdown implies a degree of freedom that does not exist yet

2. `cv_analysis.semantic_alignment.model`
- only one model option is currently exposed
- so it behaves more like fixed runtime metadata than a true tuning control

These controls should not be treated like normal user decisions while only one valid option exists.

### C. Active but easy-to-misread controls

`enrichment_concurrency` is live and used by runtime, but its practical effect is bounded by the enrich-stage global rate lock and sleep policy.

So:
- it should remain configurable
- but the UI should better explain that it does not act as a simple linear throughput multiplier

### D. Contract drift beneath the UI

The UI is already much cleaner than before, but compatibility projection still exists in runtime:

- [config.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/src/fitcv/config.py)

This is intentional compatibility logic, but it means the UI should stay clearly framed around the canonical settings contract, not legacy key shapes.

## Design Goals

The redesigned settings UI should:

1. help an operator make the most common decisions quickly
2. hide advanced tuning until it is intentionally needed
3. stop presenting pseudo-choice settings as if they were meaningful live decisions
4. make the difference between current effective values and unsaved edits obvious
5. keep grouped validation and settings persistence behavior intact

## Proposed Design

## 1. Reorganize the page around operator tasks

Replace the current “all sections feel the same” structure with a task-first information architecture.

Recommended top-level groups:

1. `Selection`
- `pipeline.vector_search_top_n`
- `pipeline.ai_score_top_n`
- `pipeline.final_top_n`
- `pipeline.evidence_top_k`
- `rule_filter.selected_filters`
- `global_job_filters.*`

2. `Ranking`
- ranking weights
- fit label thresholds
- gap thresholds

3. `CV Output`
- `cv_generation_model`
- section visibility toggles
- `cv_max_pages`

4. `Run Safety`
- `run_lifecycle.max_runtime_minutes`

5. `Advanced`
- semantic-alignment tuning
- timing and throttling controls
- any future expert-only knobs

This keeps the page aligned with the operator’s mental workflow:

- what enters the pipeline
- how candidates are ranked
- what output is produced
- what safety rails exist
- what deeper tuning is available

## 2. Introduce Basic vs Advanced disclosure

The default view should focus on the small number of settings that drive most operator outcomes.

### Default-visible controls

Recommended always-visible controls:

- `pipeline.vector_search_top_n`
- `pipeline.ai_score_top_n`
- `pipeline.final_top_n`
- `pipeline.evidence_top_k`
- `rule_filter.selected_filters`
- `global_job_filters.applications_count_max`
- `global_job_filters.max_age_days`
- ranking weights
- fit-label thresholds
- `cv_generation_model`
- CV section visibility
- `cv_max_pages`
- `run_lifecycle.max_runtime_minutes`

### Advanced-only controls

Move behind expandable advanced sections:

- `cv_analysis.semantic_alignment.enabled`
- `cv_analysis.semantic_alignment.model`
- all lexical-vs-semantic weight controls
- `cv_analysis.semantic_alignment.channel_pool_size`
- `enrichment_sleep_secs`
- `rerank_sleep_secs`
- `enrichment_batch_size`
- `enrichment_concurrency`

This reduces first-load complexity without removing power.

## 3. Reclassify single-option controls as metadata

When a setting has only one supported value, do not present it as a normal editable form field.

### Proposed rule

If a settings entry exposes only one valid option, render it as:

- read-only runtime metadata
- with a small explanation like:
  - `Currently fixed by the active runtime contract`
  - `This will become editable when additional supported options exist`

Apply this now to:

- `cv_preset`
- `cv_analysis.semantic_alignment.model`

These may still remain in the schema for contract continuity, but they should not consume the same UX weight as real choices.

## 4. Improve current vs draft visibility

The current page shows effective values plus inputs, but the distinction is still visually subtle.

### Proposed UX changes

1. sticky section footer on dirty state
- show:
  - `Unsaved changes`
  - `Reset`
  - `Save`

2. dirty-row highlighting
- any changed field should be visually marked

3. clearer effective-value label
- replace the current middle-column style with an explicit label such as:
  - `Current: 25`

4. section-level status
- examples:
  - `No changes`
  - `3 unsaved edits`

This makes the page safer and easier to operate.

## 5. Add impact-oriented helper copy

Descriptions should explain tradeoffs, not just what the field technically is.

Examples:

- `Initial Candidate Pool Size`
  - `Higher values increase recall but add shortlist and ranking latency.`

- `AI Reranking Pool Size`
  - `Higher values improve coverage but increase LLM time and cost.`

- `Enrichment Concurrency`
  - `Allows more batches in flight, but total throughput is still bounded by the enrich-stage global rate limiter.`

- `Maximum Run Duration`
  - `Safety guard for stuck queued, running, or paused runs.`

The goal is operational comprehension, not just schema correctness.

## 6. Compress the CV composition UI

The CV composition section is now mostly visibility toggles, so the current card-per-section approach is heavier than necessary.

### Proposed redesign

Replace the tall card stack with a compact composition matrix:

| Section | Included | Notes |
| ------- | -------- | ----- |
| Summary | toggle | optional |
| Education | toggle | optional |
| Experience | toggle | core |
| Skills | toggle | core |
| Certifications | toggle | optional |
| Projects | toggle | optional |
| Publications | toggle | optional |
| Languages | toggle | optional |

This is more scannable and consistent with the actual remaining setting complexity.

## 7. Add optional preset bundles for operator intent

Instead of making every user tune many individual knobs manually, add high-level UI bundles such as:

- `Fast screening`
- `Balanced`
- `High recall`
- `Debug / inspection`

These should:

- prefill a set of settings
- remain reviewable before save
- not bypass normal persistence or validation

This is an optimization layer for usability, not a replacement for fine-grained settings.

## What Should Not Change

The redesign should not:

- remove currently live runtime controls just because they are advanced
- replace canonical nested settings with legacy flat keys
- change grouped validation semantics
- change the append-only settings history model
- make current defaults ambiguous relative to loaded config

## Proposed Setting Classification

### Keep as active editable controls

- retrieval pool sizes
- evidence count
- rule-filter blocking set
- global pre-enrichment filters
- ranking weights and thresholds
- CV generation model
- CV section visibility toggles
- CV max pages
- run max runtime
- semantic alignment enable and weights
- timing / throttling controls

### Keep but re-render as metadata

- `cv_preset`
- `cv_analysis.semantic_alignment.model`

### Keep but improve explanatory copy

- `enrichment_concurrency`
- `enrichment_sleep_secs`
- `rerank_sleep_secs`

## Acceptance Criteria

1. No active runtime control is mistakenly removed from the admin contract.
2. Single-option pseudo-choice settings are no longer rendered like normal editable controls.
3. The default settings view is materially shorter and easier to scan than the current page.
4. Advanced settings remain available without dominating the first-load experience.
5. Dirty-state and current-vs-draft status become visually obvious.
6. CV composition becomes more compact and more consistent with the simplified visibility-only contract.
7. Settings persistence and validation behavior remain unchanged.

## Recommended Rollout

1. reclassify pseudo-choice controls first
2. introduce task-first grouping and advanced disclosure
3. improve dirty-state and effective-value feedback
4. compact the CV composition surface
5. optionally add operator bundles after the new IA is stable

## Source-of-Truth Alignment

Primary feature contract:

- [settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/settings_system/settings_system.yaml)

Secondary affected contracts:

- [admin_control_plane_core.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/admin_control_plane_core/admin_control_plane_core.yaml)

Expected follow-up docs:

- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/e2e-opt/docs/features/settings_system/history.md)

