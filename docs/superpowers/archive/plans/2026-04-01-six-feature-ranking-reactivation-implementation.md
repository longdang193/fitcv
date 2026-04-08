# Six-Feature Ranking Reactivation Implementation Plan

**Feature:** `docs/features/settings_system/settings_system.yaml`  
**Related Feature:** `docs/features/inspection_debugging/inspection_debugging.yaml`  
**Stage:** `docs/stages/ranking.yaml`  
**Spec:** `docs/superpowers/specs/2026-04-01-six-feature-ranking-reactivation-design.md`  
**Type:** modify  
**Status:** complete  

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Re-enable the full six-feature ranking contract end-to-end, make zero-weight semantics explicit in runtime scoring, and update the ranking stage artifact so new run JSONs report the exact six-feature weights, defaults, feature values, and ranked-vs-not-ranked context used by each run.

**Architecture:** This rollout removes the hidden two-feature runtime subset and replaces it with a single six-feature ranking contract spanning config resolution, ranking feature assembly, final score computation, and ranking-stage artifact capture. `build_ranking_features()` becomes the canonical place that assembles the six ranking inputs using enriched job fields, candidate preferences, shortlist fields, and reranker outputs. Ranking artifacts continue to live in the existing run-scoped `stage_transition_artifacts_json`, but the ranking block now reports the full six-feature weight/default maps plus sampled rows that carry all six feature values and `final_score`.

**Key Invariants:**
- The supported ranking feature set is always exactly:
  - `ai_score`
  - `must_have_match`
  - `vector_similarity`
  - `title_relevance`
  - `seniority_fit`
  - `preference_fit`
- A feature is disabled only by an explicit configured weight of `0.0`, not by hidden runtime exclusion.
- The six configured ranking weights must still sum to `1.0` within tolerance.
- `final_score` must be explainable from the six feature values and weights recorded for the run.
- The ranking artifact must reflect the run-scoped effective settings snapshot, not the current repo defaults.
- Historical runs do not need migration or artifact rewrites.

**Rollout / Revert:**  
- rollback_trigger: ranking outputs or artifacts still disagree with the visible six-weight settings model, or enabling the four additional features changes ranking behavior without being explainable from artifacted inputs  
- rollback_method: revert the six-feature runtime contract, ranking feature-assembly changes, and ranking artifact schema changes together so runtime and artifacts return to a single older contract

---

## Doc Update Matrix

- Feature contract:
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
- Stage contracts:
  - `docs/stages/ranking.yaml`
- Feature history:
  - `docs/features/settings_system/history.md`
  - `docs/features/inspection_debugging/history.md`
- Feature-specific docs: `none`
- Cross-cutting docs:
  - `docs/superpowers/specs/2026-04-01-six-feature-ranking-reactivation-design.md`
- README: `none`
- Generated discovery: `none`

## Stage and Feature Scope

- Affected stages:
  - `ranking`
- Affected features:
  - `settings_system`
  - `inspection_debugging`
- Primary lens: mixed

## File Structure First

- Modify:
  - `config/ranking.yaml`
  - `src/fitcv/ranking.py`
  - `src/fitcv/pipeline.py`
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/settings_system/history.md`
  - `docs/features/inspection_debugging/history.md`
  - `docs/stages/ranking.yaml`
- Test:
  - `tests/test_ranking.py`
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`

---

## Task 1: Lock the Six-Feature Runtime Contract in Tests

**Files:**
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add failing ranking tests that define the supported six-feature contract and assert `get_active_ranking_weights()` and `get_active_missing_value_defaults()` now resolve all six features.
- [x] Step 2: Add failing tests that prove zero-weight features stay present in resolved runtime maps rather than being filtered out.
- [x] Step 3: Add failing tests that prove `compute_final_score()` uses six-feature weights and defaults correctly.
- [x] Step 4: Add failing pipeline tests that expect `build_ranking_features()` to populate all six ranking feature values for each scored shortlist row.
- [x] Step 5: Run the failing targeted tests:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_ranking.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "build_ranking_features or ranking"`
- [ ] Step 6: Commit if requested.

## Task 2: Replace the Hidden Two-Feature Runtime Contract

**Files:**
- Modify: `src/fitcv/ranking.py`
- Modify: `config/ranking.yaml`
- Modify: `tests/test_ranking.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Replace `ACTIVE_RANKING_FEATURES` and two-feature defaults with a six-feature supported-ranking contract.
- [x] Step 2: Define six-feature default ranking weights and six-feature missing-value defaults that preserve conservative vs neutral semantics appropriately.
- [x] Step 3: Ensure weight resolution keeps zero-value configured weights instead of treating them as unsupported.
- [x] Step 4: Update `config/ranking.yaml` so the baseline checked-in config expresses the intended six-feature policy explicitly.
- [x] Step 5: Re-run `tests/test_ranking.py` and confirm the runtime contract tests pass.
- [ ] Step 6: Commit if requested.

## Task 3: Make Ranking Own Full Feature Assembly

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Update `build_ranking_features()` so it computes or assembles:
  - `ai_score`
  - `must_have_match`
  - `vector_similarity`
  - `title_relevance`
  - `seniority_fit`
  - `preference_fit`
- [x] Step 2: Use canonical ranking helpers in `ranking.py` for the four non-LLM feature computations so ownership is local to ranking.
- [x] Step 3: Source job-side inputs from structured/enriched shortlist rows and candidate-side inputs from the loaded profile preferences and skills.
- [x] Step 4: Preserve supporting fields needed by downstream ranking artifacts and CV/debug flows:
  - `job_url`
  - `title` and or `job_title`
  - `required_skills`
  - `seniority`
  - `job_family`
  - `domain`
  - `location_type`
  - `vector_rank`
  - `fit_label`
  - `fit_label_source`
- [x] Step 5: Re-run the targeted ranking-feature assembly tests and confirm pass.
- [ ] Step 6: Commit if requested.

## Task 4: Recompute Final Score Across All Six Features

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_pipeline.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Ensure ranking inputs now call `compute_final_score()` with the resolved six-feature weight/default maps.
- [x] Step 2: Add or expand tests proving `final_score` changes when the newly re-enabled feature weights are non-zero.
- [x] Step 3: Add or expand tests proving a feature with weight `0.0` stays visible in the row payload but contributes nothing to score.
- [x] Step 4: Confirm no renormalization logic is introduced, because the six-feature sum-to-one contract remains the single normalization rule.
- [x] Step 5: Re-run the targeted ranking and pipeline tests and confirm pass.
- [ ] Step 6: Commit if requested.

## Task 5: Upgrade the Ranking Stage Artifact Contract

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Replace the ranking-stage partial weight summary with a six-feature decision summary that includes:
  - `configured_ranking_weights`
  - `configured_missing_value_defaults`
  - `zero_weight_features`
  - `contributing_features`
  - existing `ranking_fit_label_counts`
- [x] Step 2: Update `inputs_sample` so sampled ranking rows carry all six feature values plus `final_score`.
- [x] Step 3: Update `outputs_sample` so ranked rows carry all six feature values plus rank outcome and fit label.
- [x] Step 4: Update `dropped_or_changed_sample` so scored-but-not-ranked rows are visible with the same six-feature context.
- [x] Step 5: Add failing or expanded tests that prove the ranking JSON artifact is self-explanatory for:
  - full six-feature contributing runs
  - runs with several zero-weight features
  - scored-but-not-ranked rows
- [x] Step 6: Re-run the targeted pipeline and control-plane tests and confirm the persisted/downloaded JSON shape is correct.
- [ ] Step 7: Commit if requested.

## Task 6: Preserve Effective-Settings Truth in Ranking Artifacts

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add or expand tests proving the ranking artifact reflects the effective run settings snapshot rather than current repo defaults.
- [x] Step 2: Cover a run case where saved settings or per-run overrides set multiple ranking features to `0.0`, and assert the artifact reports those exact zeros.
- [x] Step 3: Confirm the worker path still uses stored `effective_settings_json` and does not need new persistence fields for the richer ranking block.
- [x] Step 4: Re-run the targeted worker/app tests that cover settings-used and stage-artifact persistence.
- [ ] Step 5: Commit if requested.

## Task 7: Align Settings UI Expectations and Validation Tests

**Files:**
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_ranking.py`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Add or update tests that validate six-weight sum-to-one still holds when some supported features are explicitly zero-weighted.
- [x] Step 2: Add or update tests that assert zero weights remain accepted and do not cause runtime filtering artifacts.
- [x] Step 3: If needed, add bounded assertions around settings-page helper text or effective-value presentation so the UI and runtime semantics no longer conflict.
- [x] Step 4: Re-run the targeted settings/app tests and confirm pass.
- [ ] Step 5: Commit if requested.

## Task 8: Sync Feature Contracts, Stage Contract, and Histories

**Files:**
- Modify: `docs/features/settings_system/settings_system.yaml`
- Modify: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Modify: `docs/features/settings_system/history.md`
- Modify: `docs/features/inspection_debugging/history.md`
- Modify: `docs/stages/ranking.yaml`
- Docs: exact entries from the Doc Update Matrix

- [x] Step 1: Update `settings_system.yaml` so ranking settings are described as a real six-feature runtime contract with explicit zero-weight semantics.
- [x] Step 2: Update `inspection_debugging.yaml` so ranking-stage artifacts are described as exposing the six-feature ranking contract and ranked-vs-not-ranked context.
- [x] Step 3: Update `ranking.yaml` so the stage contract reflects six-feature scoring inputs and richer ranking artifact outputs.
- [x] Step 4: Add history entries documenting the contract alignment and artifact changes.
- [x] Step 5: Re-read the spec and docs together to ensure terminology is consistent:
  - no remaining “active two-feature contract” wording
  - zero-weight semantics are explicit
  - artifact field names match runtime behavior
- [ ] Step 6: Commit if requested.

## Task 9: Final Verification and Consistency Pass

**Files:**
- Modify: `docs/superpowers/specs/2026-04-01-six-feature-ranking-reactivation-design.md` only if terminology drift requires a bounded sync patch

- [x] Step 1: Run final focused verification:
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_ranking.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "build_ranking_features or ranking or artifacts"`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_worker_job.py`
  - `.\.venv\Scripts\python.exe -m pytest -q tests\test_fitcv_cp\test_app.py -k "ranking or stage_artifacts or settings_used"`
- [x] Step 2: Review diffs for completeness and confirm:
  - runtime uses all six supported features
  - zero-weight features remain visible in runtime maps and artifacts
  - ranking artifact decision summaries and row samples are internally consistent
  - no hidden fallback to the old two-feature contract remains
- [x] Step 3: If terminology drifted during implementation, make one bounded sync patch to the spec.
- [ ] Step 4: Commit if requested.

---

## Execution Order

1. Complete Task 1 first so the six-feature contract and zero-weight semantics are pinned down in tests before runtime edits.
2. Complete Task 2 next so ranking config resolution and defaults become coherent.
3. Complete Tasks 3 and 4 together so feature assembly and final-score computation move to the new contract in one pass.
4. Complete Task 5 after runtime scoring is stable so the ranking artifact can report the exact contract actually used.
5. Complete Task 6 once the artifact schema is stable, ensuring run-scoped effective settings propagate correctly.
6. Complete Task 7 after runtime and artifact behavior are settled, so settings/UI tests reflect the new semantics instead of blocking discovery.
7. Complete Task 8 once implementation is stable.
8. Complete Task 9 last so verification covers the full rollout.

## Verification Checklist

- [x] Runtime ranking supports all six features end-to-end.
- [x] A supported feature is disabled only when its configured weight is `0.0`.
- [x] Six-feature ranking weights still validate to sum to `1.0` within tolerance.
- [x] `build_ranking_features()` explicitly populates all six ranking feature values.
- [x] `final_score` is explainable from the six feature values and the recorded six-feature weight map.
- [x] The ranking stage artifact reports:
  - `configured_ranking_weights`
  - `configured_missing_value_defaults`
  - `zero_weight_features`
  - `contributing_features`
  - six-feature sampled rows
- [x] Ranking `inputs_sample`, `outputs_sample`, and scored-but-not-ranked samples all include all six ranking feature values plus `final_score`.
- [x] Downloaded ranking JSON reflects the run-scoped effective settings snapshot used by that run.
- [x] No hidden two-feature filtering logic remains in runtime or artifact generation.

## Risks and Notes

### Behavior Shift Risk

Re-enabling four additional ranking features may materially reorder rankings when those weights are non-zero.

Mitigation:
- lock expected behavior in focused tests
- keep zero-weight semantics explicit
- make the artifact sufficient to explain ranking changes row-by-row

### Input-Source Drift Risk

The four non-LLM features currently exist ambiguously across reranker payloads, shortlist rows, and enriched job data.

Mitigation:
- make `build_ranking_features()` the canonical assembly point
- compute the four non-LLM features from ranking helpers and explicit inputs
- preserve supporting job/profile fields in sampled artifact rows

### Artifact Semantics Risk

Changing the ranking artifact keys can break tests or consumers that expect the old `active_ranking_weights` shape.

Mitigation:
- update tests and any stage-download expectations in the same rollout
- keep artifact naming explicit and consistent with the runtime contract

### Historical Comparison Risk

Old runs will still show two-feature artifacts while new runs show six-feature artifacts.

Mitigation:
- document that the new contract applies only to newly triggered runs
- avoid rewriting historical artifacts
