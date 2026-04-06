---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Remove unused candidate chunk embedding generation from the active shortlist runtime while keeping `cv_analysis` behavior unchanged."
---

# Remove Candidate Chunk Embeddings From The Active Pipeline Implementation Plan

## Scope

Implement the cleanup defined in [2026-04-04-09-15-remove-candidate-chunk-embeddings-from-active-pipeline-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/superpowers/specs/2026-04-04-09-15-remove-candidate-chunk-embeddings-from-active-pipeline-spec.md).

This rollout stays intentionally narrow:

- remove candidate chunk embedding generation from the active `shortlist` runtime
- keep job embedding generation and reuse unchanged
- keep candidate query text and candidate query embedding behavior unchanged
- keep `cv_analysis` evidence retrieval unchanged
- update docs and debug wording so the live pipeline no longer implies candidate chunk embeddings are in use

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/inspection_debugging.yaml)
- [shortlist.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/shortlist.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_analysis.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/history.md)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/embeddings.py)
- [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py) for contract confirmation only if comments/docs need clarification
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_pipeline.py)
- [test_embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_embeddings.py)

Generated refresh required:

- yes

## Invariants

- `shortlist` must still retrieve over reusable `job_embeddings`.
- `shortlist` must still build the deterministic candidate query text and embed the query vector it actually uses for retrieval.
- `cv_analysis` must continue to retrieve evidence from the normalized candidate profile and selected evidence contract, not from `candidate_embeddings`.
- No stage should imply that candidate chunk embeddings are part of the active runtime unless that stage directly consumes them.
- Historical `candidate_embeddings` rows may remain in storage without affecting behavior.

## Implementation Tasks

### Task 1: Remove Candidate Chunk Embedding From Active `shortlist` Runtime

Delete the live pipeline call that writes candidate chunk embeddings during the shortlist stage.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)

Changes:

- remove `embed_and_store_candidate(profile, config)` from the `shortlist` stage execution path
- keep `embed_and_store_jobs(passed_jobs, config)`
- keep candidate query construction and `run_vector_search(...)` unchanged

Acceptance criteria:

- shortlist no longer writes candidate chunk embeddings during normal runtime
- shortlist still completes successfully with unchanged retrieval behavior

### Task 2: Clean Up Imports and Dead Runtime Assumptions

Remove any now-unused imports or comments that imply candidate chunk embeddings are part of the active shortlist flow.

Primary targets:

- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- [embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/embeddings.py) if comments/docstrings need clarification

Changes:

- drop unused imports if removing the pipeline call makes them unnecessary
- clarify docstrings/comments so:
  - job embeddings are active in shortlist
  - candidate query embedding is active in shortlist
  - candidate chunk embeddings are not part of the active path

Acceptance criteria:

- no stale runtime comments imply that `candidate_embeddings` are used downstream
- touched modules stay lint/compile clean

### Task 3: Update Tests To Match The Active Runtime Contract

Adjust tests so they no longer expect candidate chunk embedding work as part of the active shortlist path.

Primary targets:

- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_pipeline.py)
- [test_embeddings.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/tests/test_embeddings.py) only if test names or assumptions need clarification

Changes:

- update or remove mocks/assertions that expect `embed_and_store_candidate(...)` to be called from the active shortlist stage
- add or strengthen a regression test proving `cv_analysis` evidence retrieval still works without `candidate_embeddings`

Acceptance criteria:

- shortlist-stage tests reflect the real runtime path
- `cv_analysis` tests still pass unchanged in behavior

### Task 4: Update Stage and Feature Docs

Make the source-of-truth docs explicit that candidate chunk embeddings are not part of the live path today.

Primary targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
- [inspection_debugging.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/inspection_debugging/inspection_debugging.yaml)
- [shortlist.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/shortlist.yaml)
- [cv_analysis.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/stages/cv_analysis.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/FitCV-pipeline.md)
- feature history docs

Changes:

- remove language that suggests candidate chunk embeddings are an active dependency
- clarify the current split:
  - shortlist uses job embeddings plus one candidate query vector
  - `cv_analysis` uses profile-based selected-evidence retrieval
- preserve future-extensibility wording for later semantic chunk consumers

Acceptance criteria:

- docs accurately describe the active runtime path
- future candidate chunk embedding work remains possible without implying it is already live

### Task 5: Refresh Generated Discovery Docs

Sync generated discovery surfaces after the source-of-truth docs change.

Primary targets:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/generated/feature_capabilities_index.yaml)

Acceptance criteria:

- generated docs reflect the updated stage/feature contracts
- generated docs continue to point back to source-of-truth files

## Verification

Run focused verification covering shortlist and `cv_analysis`:

```powershell
python -m pytest -q .worktrees\cv-analysis\tests\test_embeddings.py .worktrees\cv-analysis\tests\test_pipeline.py -k "shortlist or cv_analysis or evidence"
python -m py_compile .worktrees\cv-analysis\src\fitcv\pipeline.py .worktrees\cv-analysis\src\fitcv\embeddings.py .worktrees\cv-analysis\src\fitcv\evidence.py .worktrees\cv-analysis\tests\test_pipeline.py .worktrees\cv-analysis\tests\test_embeddings.py
```

Optional runtime sanity check if needed:

- rerun a manual staged flow through `shortlist -> ranking -> cv_analysis`
- confirm outputs remain unchanged aside from the removed candidate chunk embedding side effect

## Rollout Notes

- This should be a low-risk cleanup because no active stage consumes `candidate_embeddings`.
- If a hidden dependency is discovered, rollback is simple:
  - restore the removed shortlist call
- Any future semantic evidence project should reintroduce candidate chunk embeddings under an explicit new stage-owned spec rather than silently restoring the old behavior.
