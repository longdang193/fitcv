---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement hybrid lexical-plus-semantic domain and responsibility alignment in `cv_analysis`, with stage-owned embedding reuse, admin-configurable weights, and bounded coverage-aware evidence selection."
---

# CV Analysis Semantic Alignment Upgrade Implementation Plan

## Scope

Implement the semantic-alignment upgrade defined in [2026-04-04-10-15-cv-analysis-semantic-alignment-upgrade-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/superpowers/specs/2026-04-04-10-15-cv-analysis-semantic-alignment-upgrade-spec.md).

This rollout stays intentionally focused:

- keep `required_skill_support` deterministic and `role_alignment` lightweight
- upgrade `domain_alignment` and `responsibility_alignment` to hybrid lexical-plus-semantic scoring
- reintroduce candidate evidence embeddings only as a `cv_analysis`-owned capability
- keep final evidence selection bounded and coverage-aware instead of turning it into a second semantic reranker
- expose the hybrid weights through the admin settings UI and settings-used snapshots
- expand `cv_analysis` debug surfaces so lexical and semantic subscores are inspectable

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/settings_system/settings_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/inspection_debugging.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_generation.yaml) if downstream analysis payload expectations need clarification

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/settings_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/embeddings.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv_cp/templates/settings.html)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_pipeline.py)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_fitcv_cp/test_settings_schema.py) if present for grouped settings validation
- [test_fitcv_cp/test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_fitcv_cp/test_app.py) if settings rendering coverage needs adjustment

Generated refresh required:

- yes

## Invariants

- `cv_analysis` remains the sole owner of evidence retrieval and final evidence selection before CV writing.
- `required_skill_support` stays deterministic/canonical.
- `role_alignment` stays lightweight and does not become a second semantic retrieval stack.
- Semantic scoring is introduced only inside `domain_alignment` and `responsibility_alignment`.
- Candidate evidence embeddings are generated or reused only when `cv_analysis` directly consumes them.
- Final evidence selection remains bounded by one per-job `top_k`.
- Admin-exposed lexical/semantic weight pairs must validate to `1.0` per hybrid channel.

## Implementation Tasks

### Task 1: Add Stage-Owned Semantic Embedding Inputs For `cv_analysis`

Introduce reusable semantic inputs for the evidence items and job-side alignment texts that `cv_analysis` actually consumes.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/embeddings.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- derive candidate evidence semantic snippets from normalized evidence items, such as:
  - experience bullet text
  - project highlight text
  - project business-value text
  - achievement text
  - optional responsibility-theme text
  - optional domain-context text
- derive job-side semantic inputs for:
  - responsibility snippets
  - bounded domain text
- reuse embeddings by stable identity plus content hash and embedding contract fingerprint

Acceptance criteria:

- semantic embedding generation is owned by `cv_analysis`, not `shortlist`
- evidence embeddings and job-side semantic inputs can be reused safely across repeated runs
- lexical-only fallback remains possible when semantic inputs are unavailable

### Task 2: Upgrade `domain_alignment` To Hybrid Lexical-Plus-Semantic Scoring

Replace the current mostly lexical domain channel score with a weighted hybrid score.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- keep lexical domain scoring for:
  - explicit `domain_tags`
  - domain and job-family overlap
- add semantic domain scoring from embedding similarity between job domain text and candidate evidence domain/context text
- combine them with explicit weights:
  - default `0.40 lexical / 0.60 semantic`

Acceptance criteria:

- semantically related domain evidence can score well even when exact domain words differ
- explicit domain-tag matches remain strong signal
- tests cover both exact-match and paraphrased-domain cases

### Task 3: Upgrade `responsibility_alignment` To Hybrid Lexical-Plus-Semantic Scoring

Replace token-overlap-only responsibility scoring with a weighted hybrid score.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- keep lexical responsibility scoring for:
  - `responsibility_themes`
  - `scoring_context`
- add semantic responsibility scoring from embedding similarity between:
  - job responsibility snippets
  - candidate evidence semantic snippets
- combine them with explicit weights:
  - default `0.25 lexical / 0.75 semantic`

Acceptance criteria:

- paraphrased but relevant evidence can score well even when token overlap is weak
- exact responsibility-theme overlap remains useful but no longer dominates by itself
- tests cover at least one semantically similar / lexically weak responsibility example

### Task 4: Keep Final Top-K Selection Bounded But Make It Coverage-Aware

Preserve the bounded bundle selector, but improve it so it rewards marginal job-coverage gain rather than just heuristic score and type diversity.

Primary targets:

- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [test_evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_evidence.py)

Changes:

- keep one final per-job `top_k`
- continue using weighted channel scores as the base
- add bounded marginal-gain logic so the selector prefers items that newly cover:
  - uncovered responsibilities
  - missing support channels
  - domain support gaps
- penalize redundant items that repeat already-covered evidence support

Acceptance criteria:

- final top-k remains bounded and deterministic
- selection does not become a second semantic reranker
- tests show that redundant items can be deprioritized in favor of broader job coverage

### Task 5: Add Admin-Editable Settings For Hybrid Alignment

Expose the new semantic-alignment controls through the admin settings system instead of leaving them as internal-only config keys.

Primary targets:

- [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv_cp/settings_schema.py)
- [settings.html](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv_cp/templates/settings.html)
- [test_fitcv_cp/test_settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_fitcv_cp/test_settings_schema.py)
- [test_fitcv_cp/test_app.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_fitcv_cp/test_app.py) if settings rendering coverage is needed

Changes:

- add settings entries for:
  - `cv_analysis.semantic_alignment.enabled`
  - `cv_analysis.semantic_alignment.model`
  - `cv_analysis.semantic_alignment.responsibility_lexical_weight`
  - `cv_analysis.semantic_alignment.responsibility_semantic_weight`
  - `cv_analysis.semantic_alignment.domain_lexical_weight`
  - `cv_analysis.semantic_alignment.domain_semantic_weight`
  - `cv_analysis.semantic_alignment.channel_pool_size`
- place them in a clear retrieval or `CV Analysis Alignment` section
- add grouped validation so each lexical/semantic pair must sum to `1.0`

Acceptance criteria:

- the admin UI exposes the new hybrid controls
- invalid weight pairs are rejected explicitly
- settings-used snapshots preserve the effective hybrid values

### Task 6: Expose Hybrid Subscores And Reuse State In `cv_analysis` Artifacts

Make the new hybrid scoring understandable from `cv_analysis` outputs and downloads.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_pipeline.py)

Changes:

- persist bounded debug fields for selected evidence items, including:
  - lexical vs semantic subscores
  - final hybrid score per upgraded channel
  - semantic method used vs lexical fallback
  - candidate evidence embedding reuse status
  - job semantic-input embedding reuse status
- expose effective hybrid weights in `cv_analysis` decision summaries or settings-used payloads

Acceptance criteria:

- `CV Analysis JSON` can explain why an item was selected even in semantic-heavy cases
- operators can see whether semantic scoring or fallback behavior drove the result
- debug payloads stay bounded and reviewer-friendly

### Task 7: Sync Feature, Stage, Settings, and Generated Docs

Update the source-of-truth docs after the runtime and settings changes are implemented.

Targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
- [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/settings_system/settings_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/inspection_debugging.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/settings_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/history.md)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_analysis.yaml)
- [cv_generation.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_generation.yaml) if downstream payload expectations need clarification
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/FitCV-pipeline.md)
- generated docs under `docs/generated/`

Acceptance criteria:

- docs describe semantic matching as a `cv_analysis` stage-owned capability
- settings docs describe the new admin-editable hybrid controls
- generated discovery files point back to the updated source-of-truth docs

## Verification

Run focused verification covering semantic evidence scoring, pipeline persistence, and settings validation:

```powershell
python -m pytest -q .worktrees\cv-analysis\tests\test_evidence.py .worktrees\cv-analysis\tests\test_pipeline.py -k "cv_analysis or evidence or semantic"
python -m pytest -q .worktrees\cv-analysis\tests\test_fitcv_cp\test_settings_schema.py .worktrees\cv-analysis\tests\test_fitcv_cp\test_app.py -k "settings or retrieval"
python -m py_compile .worktrees\cv-analysis\src\fitcv\evidence.py .worktrees\cv-analysis\src\fitcv\embeddings.py .worktrees\cv-analysis\src\fitcv\pipeline.py .worktrees\cv-analysis\src\fitcv_cp\settings_schema.py .worktrees\cv-analysis\tests\test_evidence.py .worktrees\cv-analysis\tests\test_pipeline.py
```

Optional runtime sanity check if needed:

- rerun a staged flow through `ranking -> cv_analysis`
- confirm semantically similar but lexically weak evidence can appear in selected bundles
- confirm settings-used snapshots show the active hybrid weights

## Rollout Notes

- start with the default weights from the spec rather than exposing many extra tuning knobs at once
- keep lexical fallback available so the stage degrades safely if semantic inputs or embeddings are unavailable
- if semantic scoring proves too broad, rollback can first reduce semantic weights before removing the feature entirely
- do not add a small LLM reranker in this rollout; embeddings plus bounded selector tuning are the intended first step
