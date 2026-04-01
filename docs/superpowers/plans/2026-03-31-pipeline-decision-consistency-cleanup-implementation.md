# Pipeline Decision Consistency Cleanup Implementation Plan

> **For agentic workers:** Execute this as a Phase 1 consistency cleanup, not a broad pipeline redesign. Keep behavior changes bounded, verify each task before moving on, and prefer contract honesty over adding new scoring logic.

**Goal:** Remove the most confusing pipeline decision overlaps so ranking, fit labeling, CV eligibility, validation, and debug/export surfaces follow one explicit stage contract.

**Architecture:** Phase 1 keeps the layered pipeline, but narrows authority:

- rule filters remain deterministic pre-retrieval gates
- retrieval remains recall and shortlist formation
- AI reranking becomes the primary post-filter fit authority for ranking and CV eligibility
- gap analysis becomes grounded explanation and CV-support context only
- validation owns artifact acceptance
- export/debug surfaces expose stage-local truth without implying extra authority

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

**Source spec:** `docs/superpowers/specs/2026-03-31-19-10-pipeline-decision-consistency-cleanup-spec.md`

**Affected feature contracts:**

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`

**Supporting docs to update during implementation:**

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/trigger_run_management/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`

---

## Phase 1 Boundaries

This plan is intentionally limited.

Phase 1 does:

- align ranking config with runtime-computed ranking features
- establish one primary post-filter fit authority
- make reranker grounding claims honest relative to runtime
- align gap-analysis inputs with canonical runtime ownership
- align structured normalization and markdown validation around one section contract
- make export/debug artifacts expose the decision chain clearly

Phase 1 does not:

- add a new evidence-retrieval dependency before reranking
- introduce a richer deterministic ranking model
- redesign gap analysis beyond input and authority cleanup
- turn validation into an open-ended semantic quality scorer

---

## Status Snapshot

- Completed:
  - Task 1: align the active ranking contract with runtime-computed features
  - Task 2: make reranker fit the sole primary post-filter fit authority
  - Task 3: align gap-analysis inputs and demote dormant authority paths
  - Task 4: align structured normalization and markdown validation contracts
  - Task 5: make export/debug surfaces reflect the explicit decision chain
  - Task 6: update feature contracts and history
- Partially complete:
  - none
- Pending:
  - none

---

## Task 1: Align the Active Ranking Contract with Runtime Features

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `config/ranking.yaml`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1.1: Define the Phase 1 active ranking feature set**
  - Reduce the active ranking contract to the features actually produced end-to-end at runtime during Phase 1
  - Remove or mark unsupported configured ranking features as inactive rather than silently defaulting them
  - Keep runtime ranking behavior easy to explain from config and export/debug artifacts

- [ ] **Step 1.2: Align runtime score computation with the active contract**
  - Update `build_ranking_features()` so its documented contract matches what it really computes
  - Remove stale comments/docstrings that imply unsupported deterministic ranking helpers are active
  - Ensure null/default handling uses only the active feature set

- [ ] **Step 1.3: Canonicalize the ranking defaults key**
  - Choose one runtime config key for ranking fallback/default values
  - Remove the `missing_value_defaults` versus `ranking_null_defaults` split in active runtime behavior
  - Preserve backward compatibility only through a clearly bounded adapter if needed

- [ ] **Step 1.4: Add failing regression tests**
  - ranking config and runtime feature computation stay aligned
  - unsupported ranking features do not silently influence `final_score`
  - exported score semantics match the active runtime feature set

- [ ] **Step 1.5: Confirm tests pass**

---

## Task 2: Make Reranker Fit the Sole Primary Post-Filter Fit Authority

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_ai_score.py`

- [ ] **Step 2.1: Define the primary fit contract in runtime**
  - After deterministic rule filtering, make reranker `fit_label` the authoritative fit label for:
    - ranking-time fit labeling
    - CV-generation eligibility
  - Keep separately documented deterministic gates explicit rather than implicit

- [ ] **Step 2.2: Remove hidden fit-authority competition**
  - Stop treating gap-based fit classification as a second primary fit authority
  - Keep gap outputs visible as secondary explanation/risk signals only
  - Avoid later-stage reinterpretation that changes the primary fit label silently

- [ ] **Step 2.3: Correct reranker grounding contract honesty**
  - For Phase 1, do not introduce a new evidence-retrieval dependency before reranking
  - Update the active reranker contract so it does not claim evidence grounding unless runtime actually provides it
  - Keep any optional `top_evidence` support clearly secondary/inactive in the current runtime path

- [ ] **Step 2.4: Add failing regression tests**
  - contradictory AI-fit and gap-fit cases no longer produce two competing primary fit labels
  - ranked jobs keep a single authoritative fit label through export/debug surfaces
  - reranker contract/docs no longer imply active evidence grounding when none is supplied

- [ ] **Step 2.5: Confirm tests pass**

---

## Task 3: Align Gap-Analysis Inputs and Demote Dormant Authority Paths

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/gap_analysis.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_gap_analysis.py`

- [ ] **Step 3.1: Canonicalize years inputs for gap analysis**
  - Make `years_experience_min` and `years_experience_max` the canonical enriched-job years inputs used by runtime gap analysis
  - Remove `years_required` from the active runtime contract or confine it to a clearly temporary compatibility adapter

- [ ] **Step 3.2: Make overclaim support contract honest**
  - Decide the Phase 1 behavior for evidence-aware overclaim checks
  - If runtime still does not supply `candidate_evidence`, remove that branch from the active contract rather than leaving it half-active
  - Preserve non-evidence-based gap explanation and risk outputs that remain supported

- [ ] **Step 3.3: Keep gap analysis secondary**
  - Ensure gap outputs remain:
    - matched requirements
    - missing requirements
    - overclaim/risk signals that are truly supported
    - grounded emphasis guidance
  - Ensure they do not become the primary fit label or a hidden eligibility decision

- [ ] **Step 3.4: Add failing regression tests**
  - runtime gap analysis reads canonical years fields
  - unsupported evidence-aware overclaim behavior is not silently claimed
  - gap outputs remain explanatory and secondary in pipeline summaries

- [ ] **Step 3.5: Confirm tests pass**

---

## Task 4: Align Structured Normalization and Markdown Validation Contracts

**Files:**

- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_validator.py`
- Modify: `tests/test_config.py`

- [ ] **Step 4.1: Choose one section contract**
  - Make one shared config-driven section contract authoritative across:
    - structured CV normalization
    - markdown validation
    - composition-driven required-section behavior
  - Remove the current split between hardcoded structured section requirements and config-derived markdown section requirements

- [ ] **Step 4.2: Add bounded semantic completeness checks**
  - Keep Phase 1 bounded
  - Apply semantic completeness checks only to enabled required sections
  - Avoid turning validation into a broad content-scoring system
  - Cover concrete cases such as empty-but-present Summary content

- [ ] **Step 4.3: Add failing regression tests**
  - structured normalization and markdown validation use the same section contract
  - disabled sections are not still treated as mandatory elsewhere
  - enabled required sections fail bounded completeness checks when empty

- [ ] **Step 4.4: Confirm tests pass**

---

## Task 5: Make Export and Debug Surfaces Reflect the Decision Chain

**Files:**

- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv_cp/worker_job.py`
- Modify: `src/fitcv_cp/app.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 5.1: Surface authority versus visibility explicitly**
  - Keep stage-local signals visible in export/debug artifacts
  - Make clear which stage owns:
    - shortlist inclusion
    - primary fit label
    - CV attempt/skip decision
    - validation acceptance/rejection
  - Avoid fields that make secondary explanations look authoritative

- [ ] **Step 5.2: Align naming with the new contract**
  - Separate authoritative ranking fit from explanatory gap output in export/debug payloads
  - Prefer naming that makes the difference clear, even if compatibility fields need a bounded transition

- [ ] **Step 5.3: Add failing regression tests**
  - for any ranked job, an operator can identify:
    - shortlist path
    - authoritative fit source
    - whether CV generation was attempted or skipped
    - validation outcome
  - export/debug artifacts do not require inference about which of two fit systems “won”

- [ ] **Step 5.4: Confirm tests pass**

---

## Task 6: Update Feature Contracts and History

**Files:**

- Modify: `docs/features/cv_system/cv_system.yaml`
- Modify: `docs/features/cv_system/history.md`
- Modify: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Modify: `docs/features/trigger_run_management/history.md`
- Modify: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Modify: `docs/features/inspection_debugging/history.md`

- [ ] **Step 6.1: Update feature contracts**
  - Record the Phase 1 authority model:
    - reranker fit as primary post-filter fit authority
    - gap analysis as secondary explanation/support
    - validation as artifact acceptance
  - Record config-key alignment and section-contract alignment
  - Record export/debug visibility of the stage decision chain
  - Link the cleanup spec and this implementation plan

- [ ] **Step 6.2: Record implementation history**
  - Note the previous contradictions that were removed
  - Record the Phase 1 decision to prefer contract honesty over adding new reranker evidence dependencies
  - Record the narrower ranking contract and shared section-validation contract

---

## Execution Order

1. Complete Task 1 first so the active ranking contract is explicit and testable.
2. Complete Task 2 next so primary fit authority is settled before changing downstream explanation and validation behavior.
3. Complete Task 3 after fit authority is explicit, so gap analysis can be safely demoted to explanation/support.
4. Complete Task 4 once authority boundaries are stable, so one section contract governs normalization and validation.
5. Complete Task 5 after stage authority and section policy are stable, so export/debug semantics reflect the final Phase 1 design.
6. Complete Task 6 last so feature contracts and history describe the implemented behavior rather than the pre-cleanup state.

---

## Verification Checklist

- [ ] Active ranking config matches runtime-computed ranking features
- [ ] The pipeline exposes one authoritative post-filter fit label for ranking and CV eligibility
- [ ] Gap analysis remains visible but secondary
- [ ] Reranker docs/contracts do not overstate evidence grounding in Phase 1
- [ ] Gap analysis consumes canonical runtime-owned years inputs
- [ ] Structured normalization and markdown validation share one section contract
- [ ] Enabled required sections fail bounded completeness checks when empty
- [ ] Export/debug artifacts expose the stage decision chain clearly
- [ ] No ranked job requires the operator to infer which fit system was authoritative

---

## Risks and Notes

### Ranking Behavior Risk

Reducing the active ranking contract can reorder jobs if config previously implied unsupported features were active.

Mitigation:

- keep Phase 1 focused on contract honesty
- add regression fixtures around active score decomposition
- avoid expanding deterministic feature computation in the same rollout

### Fit-Authority Transition Risk

Removing hidden fit competition can change which jobs receive CVs.

Mitigation:

- compare before/after behavior on saved run fixtures
- keep deterministic gates explicit
- update export/debug naming at the same time as runtime changes

### Validation Policy Risk

Sharing one section contract can surface failures that were previously hidden.

Mitigation:

- keep completeness checks bounded
- scope them to enabled required sections only
- add targeted fixtures for empty-but-present section cases

### Compatibility Risk

Export/debug field names may need a bounded transition if current consumers rely on old names.

Mitigation:

- preserve compatibility fields only temporarily and document the transition clearly
- prefer explicit stage-labeled fields over generic fit/status fields during rollout
