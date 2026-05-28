---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: path-1-reranker-diagnostic-fields-clarity
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md
targets:
  - src/fitcv/prompts/templates/ranking_ai_score_v1.md
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/pipeline.py
  - tests/
  - docs/
related_features:
  - cv_system
related_stages:
  - ranking
---
## Goal

Make Path 1 explicit and safe: keep `matched_strengths` and `key_risks` as diagnostic-only fields, remove ambiguity in naming/docs, and add tests proving no ranking or fit-gate behavior depends on those fields.

## Key Deliverables

### Diagnostic-only contract is explicit

Prompt/template and developer-facing docs state that `matched_strengths` and `key_risks` are emitted for diagnostics/observability only and are not ranking, gating, or CV-generation control inputs.

### Artifact naming communicates non-decision role

Stage artifact sample keys use diagnostic-prefixed names so downstream readers do not infer decision semantics from those payload fields.

### Guardrail tests prevent accidental semantic drift

Automated tests fail if ranking score computation, fit-label resolution, or reranker fit-gate behavior starts depending on `matched_strengths`/`key_risks`.

## Task/Wave Breakdown

### Task 1: Confirm root-cause and baseline usage map

**Purpose:**
- Freeze current truth before edits so Path 1 changes remain behavioral no-op for ranking/gating.

**Files:**
- Inspect: `src/fitcv/prompts/templates/ranking_ai_score_v1.md`
- Inspect: `src/fitcv/pipeline_stages/common.py`
- Inspect: `src/fitcv/pipeline.py`
- Verify: `docs/operating_system/agent_memory/failure-ledger.md`

**Preconditions:**
- GitNexus index refreshed (`npx gitnexus analyze`) and source-first findings available.
- Existing usage audit shows `fit_label` used for decisions, `score_reasoning` used for poisoned-cache filtering, `matched_strengths`/`key_risks` debug-only.

**Steps:**
- [x] Re-run targeted symbol/text queries for `matched_strengths` and `key_risks` to confirm no decision-path consumers.
- [x] Record baseline expectation: behavior must stay identical for ranking order and fit-gate outcomes.
- [x] Note one accepted exception: debug/sample artifact key rename only.

**Verification:**
- [x] `rg --line-number "matched_strengths|key_risks|score_reasoning|fit_label" src/fitcv src/fitcv_cp`

**Exit Criteria:**
- Baseline map is explicit and no hidden decision consumer remains unaccounted.

### Task 2: Clarify prompt/docs semantics

**Purpose:**
- Remove contract ambiguity at source by documenting diagnostic-only semantics.

**Files:**
- Modify: `src/fitcv/prompts/templates/ranking_ai_score_v1.md`
- Modify: nearest ranking contract docs under `docs/` (exact file picked during execution)
- Verify: `src/fitcv/prompts/registry.py`

**Preconditions:**
- Task 1 baseline confirmed.

**Steps:**
- [x] Add explicit note in prompt template that `matched_strengths` and `key_risks` are diagnostics-only fields.
- [x] Keep `fit_label` and `score_reasoning` semantics unchanged.
- [x] Align companion docs so engineers and operators read same contract intent.

**Verification:**
- [x] Prompt render/usage path still resolves via `ranking.ai_score.v1` without schema/placeholder drift.

**Exit Criteria:**
- Prompt + docs communicate single unambiguous meaning for these fields.

### Task 3: Rename debug artifact keys without behavior change

**Purpose:**
- Make observability payload self-describing while preserving backward compatibility as needed.

**Files:**
- Modify: `src/fitcv/pipeline_stages/common.py`
- Inspect/Modify if needed: artifact consumers in `src/fitcv/pipeline.py` and `src/fitcv_cp/app.py`
- Verify: tests touching stage artifacts/debug samples

**Preconditions:**
- Task 2 complete.

**Steps:**
- [x] Rename sample keys to `diagnostic_matched_strengths` and `diagnostic_key_risks` (and optional `diagnostic_score_reasoning` if chosen for naming symmetry).
- [x] Decide compatibility mode:
- [x] either dual-write old+new keys for one release window,
- [x] or single-write new keys if no external dependency exists.
- [x] Update any direct readers/tests of old key names.

**Verification:**
- [x] Targeted tests for stage artifact/sample serialization pass.
- [x] Manual snapshot inspection confirms renamed keys present and values preserved.

**Exit Criteria:**
- Artifact payload names reflect diagnostic intent; no ranking/gating behavior change observed.

### Task 4: Add non-decision dependency guardrail tests

**Purpose:**
- Prevent regressions where diagnostic fields accidentally influence ranking or gating logic.

**Files:**
- Modify: relevant tests under `tests/fitcv/` (ranking/pipeline/analysis suites)
- Verify: same test modules

**Preconditions:**
- Task 3 complete.

**Steps:**
- [x] Add test: varying `matched_strengths`/`key_risks` with fixed numeric features does not change `final_score` ordering.
- [x] Add test: varying `matched_strengths`/`key_risks` does not change fit-gate outcome (skip vs non-skip) when `fit_label`/`ai_score` held constant.
- [x] Add test/documentation assertion that `score_reasoning` remains cache-poison filter input only.

**Verification:**
- [x] `pytest -q tests/test_pipeline.py -k "ignores_diagnostic_reranker_lists_for_scoring"` and `pytest -q tests/test_agentic_cv_analysis.py -k "ignores_diagnostic_lists"`

**Exit Criteria:**
- Failing tests would catch future semantic drift from diagnostic-only to decision input.

## Verification

- `rg --line-number "diagnostic_matched_strengths|diagnostic_key_risks|matched_strengths|key_risks" src tests`
- `pytest -q tests/fitcv -k "ranking or pipeline or analysis"`
- Run repo fast validator:
  - `python scripts/hooks/run_validator.py --fast`

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`





