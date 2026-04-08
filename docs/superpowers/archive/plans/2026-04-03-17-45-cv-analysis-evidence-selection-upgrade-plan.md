---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement multi-channel evidence retrieval, merge/dedupe, and smarter final evidence selection in `cv_analysis`, with additive candidate YAML metadata to improve role, domain, and responsibility alignment."
---

# CV Analysis Evidence Selection Upgrade Implementation Plan

## Scope

Implement the evidence-selection upgrade defined in [2026-04-03-17-30-cv-analysis-evidence-selection-upgrade-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/superpowers/specs/2026-04-03-17-30-cv-analysis-evidence-selection-upgrade-spec.md).

This rollout stays intentionally focused:

- keep `cv_analysis` as the sole owner of evidence retrieval and final evidence selection
- replace required-skill-only retrieval with separate retrieval channels for:
  - required skill support
  - role alignment
  - domain alignment
  - responsibility alignment
- merge and dedupe candidate evidence pools by stable `evidence_id`
- add a smarter final selector that chooses one bounded per-job `top_k` evidence bundle
- extend candidate YAML support with additive role/domain/responsibility metadata
- expose selected-evidence rationale in `cv_analysis` artifacts and debug payloads

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/trigger_run_management/trigger_run_management.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_generation.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/trigger_run_management/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/candidate.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/ai_score.py) if the final selector is implemented as an LLM-backed reranker
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/config.py) if selector budgets or channel weights become configurable
- [test_candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_candidate.py) if candidate contract validation needs focused coverage
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_pipeline.py)

Generated refresh required:

- yes

## Invariants

- `cv_analysis` remains the sole owner of evidence retrieval and final evidence selection before CV writing.
- `cv_generation` consumes persisted analysis-selected evidence and does not silently recompute evidence retrieval by default.
- Evidence selection must stay grounded in the candidate profile; no invented evidence is allowed.
- Final evidence selection is bounded by one per-job `top_k` budget, not independent unbounded per-channel budgets.
- Candidate YAML changes are additive and backward-compatible.
- Retrieval-channel metadata and final selection rationale remain inspectable in `cv_analysis` artifacts and debug payloads.

## Implementation Tasks

### Task 1: Extend the Candidate Profile Contract for Additive Alignment Metadata

Add support for optional candidate metadata that improves role, domain, and responsibility retrieval without breaking existing profiles.

Primary targets:

- [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/candidate.py)
- [test_candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_candidate.py) if needed

Changes:

- accept additive fields such as:
  - `preferences.role_families`
  - `experiences[].role_family`
  - `experiences[].domain_tags`
  - `experiences[].responsibility_themes`
  - `projects[].domain_tags`
  - `projects[].responsibility_themes`
  - `achievements[].domain_tags`
- keep current candidate YAML files valid without requiring these fields
- normalize or validate these fields enough that retrieval code can consume them predictably

Acceptance criteria:

- old candidate YAML files still load successfully
- new optional metadata is available on the profile object in a stable shape
- missing additive metadata falls back to current weaker derivation behavior

### Task 2: Refactor Evidence Normalization Around Stable `evidence_id`

Make source-item identity explicit and channel-independent so multiple retrieval channels can safely merge onto the same evidence item.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- ensure each normalized evidence item has a stable `evidence_id`
- keep the identity derived from the source candidate evidence item, not the retrieval channel
- preserve enough metadata for later merge/dedupe:
  - `evidence_id`
  - `evidence_type`
  - `source_ref`
  - anchor text or display text

Acceptance criteria:

- the same underlying evidence item dedupes across required-skill, role, domain, and responsibility retrieval
- retrieval-channel metadata can change without changing `evidence_id`
- tests cover repeated retrieval of the same item through multiple channels

### Task 3: Implement Separate Retrieval Channels for Recall

Replace the current required-skill-only retrieval entrypoint with channel-specific retrieval helpers optimized for recall.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- add separate retrieval paths for:
  - required skill support
  - role alignment
  - domain alignment
  - responsibility alignment
- make each channel return a short ranked candidate pool with:
  - `evidence_id`
  - `channel`
  - `channel_score`
  - compact rationale
- prefer canonical job inputs where available, especially:
  - `required_skills_canonical`
  - `required_skill_entities`
  - `job_family`
  - `domain`
  - `responsibilities`

Acceptance criteria:

- `cv_analysis` no longer calls evidence retrieval with only raw `required_skills`
- each channel can over-retrieve a short pool for recall
- channel outputs are structured enough for later merge/dedupe/rerank

### Task 4: Merge, Dedupe, and Build the Final Selection Pool

Add the middle-stage contract that merges separate channel pools into one deduplicated evidence pool per ranked job.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- merge all channel pools for a given job
- dedupe by `evidence_id`
- aggregate per-item metadata such as:
  - `matched_channels`
  - `channel_scores`
  - strongest rationale snippets
- preserve a bounded merged pool for the final selector

Acceptance criteria:

- one evidence item retrieved by multiple channels appears once in the merged pool
- merged-pool records explain which channels selected the item
- the merged pool is stable and bounded enough for final reranking

### Task 5: Add a Smarter Final Selector for One Global Per-Job `top_k`

Select the final evidence subset from the merged pool using a smarter reranker instead of direct heuristic budgeting alone.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [ai_score.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/ai_score.py) if reused for an LLM-backed selector
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/config.py) if selector settings become configurable
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- introduce one final selector over the merged deduplicated pool
- keep `top_k` semantics as:
  - final number of evidence items selected per job
- prefer an LLM-backed or otherwise smarter reranker that optimizes:
  - required-skill support
  - role alignment
  - domain alignment
  - responsibility coverage
  - non-redundancy
  - diversity across evidence types
- return structured selection only, not generated prose

Acceptance criteria:

- the final selected evidence bundle is one bounded per-job list
- final selection is not interpreted as top-k per channel or top-k per evidence type
- selected items carry explicit `selection_reasons`
- selection remains grounded in the merged candidate evidence pool

### Task 6: Persist and Expose `cv_analysis` Evidence-Selection Provenance

Make the new retrieval and selection process inspectable in `cv_analysis` outputs, artifacts, and run-detail downloads.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_pipeline.py)

Changes:

- add `cv_analysis` payload fields for:
  - per-channel retrieval counts
  - merged-pool size
  - deduped-pool size
  - final selected-evidence count
  - selected evidence IDs
  - `matched_channels`
  - `selection_reasons`
- keep payloads bounded and reviewer-friendly
- ensure `cv_generation` consumes only the final selected evidence bundle plus needed rationale, not raw internal retrieval noise by default

Acceptance criteria:

- `CV Analysis JSON` clearly shows how evidence was selected
- fit-gate and evidence-selection reasoning can be inspected without reading runtime code
- backward-compatible consumers still receive a coherent analysis payload

### Task 7: Sync Feature, Stage, History, and Generated Docs

Update source-of-truth docs after the runtime behavior is implemented.

Targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/inspection_debugging.yaml)
- [trigger_run_management.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/trigger_run_management/trigger_run_management.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_generation.yaml)
- history files listed above
- generated outputs listed above

Acceptance criteria:

- source-of-truth docs reflect multi-channel retrieval plus reranked final evidence selection
- candidate YAML additive metadata is documented at the feature/stage level where relevant
- generated discovery is refreshed in the same rollout

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_evidence.py
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "cv_analysis or evidence"
```

If candidate-contract validation changes land:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_candidate.py
```

If the final selector becomes LLM-backed or config-driven, also run the focused slices that cover:

- final evidence selector contract
- selection-reason serialization
- `cv_generation` consumption of selected evidence only

Manual verification checklist:

- run a job through `ranking -> cv_analysis -> cv_generation`
- inspect `CV Analysis JSON` and confirm it shows:
  - per-channel retrieval
  - deduped merged pool
  - final selected evidence
  - selection reasons
- confirm the final selected evidence count matches the configured global `top_k`
- confirm a repeated evidence item retrieved through multiple channels appears once with aggregated channel metadata
- confirm `cv_generation` receives only the final selected evidence bundle for downstream writing

## Risks and Mitigations

### Candidate Contract Drift Risk

Risk:

- additive candidate YAML metadata may be inconsistently populated across profiles

Mitigation:

- keep all new fields optional
- preserve strong fallback behavior from existing fields
- cover missing-field behavior in tests

### Over-Selection Complexity Risk

Risk:

- separate channel retrieval plus final reranking could become hard to reason about or overfit the sample data

Mitigation:

- keep channel contracts explicit
- keep final selector output structured and inspectable
- expose merged-pool and selected-item rationale in `cv_analysis`

### LLM Selector Cost and Latency Risk

Risk:

- an LLM-backed reranker may add cost or slow down analysis

Mitigation:

- rerank only a bounded merged pool
- keep per-channel candidate pools small
- preserve the option to fall back to deterministic selection if needed

### Artifact Noise Risk

Risk:

- exposing too much retrieval detail can make `CV Analysis JSON` harder to review

Mitigation:

- keep raw retrieval diagnostics bounded
- prefer compact counts plus selected-item rationale over large unbounded dumps

## Done Definition

The work is complete when:

- `cv_analysis` retrieves candidate evidence separately for required-skill, role, domain, and responsibility channels
- retrieved channel pools are merged and deduped by stable `evidence_id`
- one smarter final selector chooses the final per-job evidence bundle
- final `top_k` means one global per-job evidence budget
- candidate YAML supports additive role/domain/responsibility metadata without breaking old files
- `CV Analysis JSON` explains why final evidence items were selected
- `cv_generation` consumes the selected evidence bundle without silently redoing retrieval
- targeted tests pass
- affected docs and generated discovery are updated in the same rollout

## Task Status

Status: completed

- [x] Task 1: Extend the candidate profile contract for additive alignment metadata
- [x] Task 2: Refactor evidence normalization around stable `evidence_id`
- [x] Task 3: Implement separate retrieval channels for recall
- [x] Task 4: Merge, dedupe, and build the final selection pool
- [x] Task 5: Add a smarter final selector for one global per-job `top_k`
- [x] Task 6: Persist and expose `cv_analysis` evidence-selection provenance
- [x] Task 7: Sync feature, stage, history, and generated docs
- [x] Run targeted verification
- [x] Update plan status after implementation
