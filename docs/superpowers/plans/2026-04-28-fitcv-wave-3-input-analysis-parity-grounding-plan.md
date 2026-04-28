---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
parent_spec: docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md
targets:
  - docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md
  - docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md
  - docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md
  - src/fitcv_cp/app.py
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/contracts.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_pipeline.py
related_features:
  - trigger_run_management
  - cv_system
  - inspection_debugging
  - settings_system
related_stages:
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Wave 3 Input And Analysis Quality Alignment Plan

**Feature Source:** `none`  
**Feature Contract:** `none`  
**Spec:** `multiple`
- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
**Implementation Execution Map:** `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`  
**Type:** add  
**Plan Layer:** change  
**Plan Status:** proposed

> **For agentic workers:** Use `executing-plans` or `subagent-driven-development` to implement task-by-task.

**Goal:** Make trigger and resume mode differences stop at the canonical run envelope, while tightening `cv_analysis` grounding surfaces so readiness, skip, block, and failure states remain explainable from bounded evidence and stage-owned summaries.

**Architecture:** This plan splits Wave 3 into two bounded seams that share the same runtime-truth foundation. The first seam aligns input-mode and checkpoint parity in the control plane and pipeline handoff. The second seam tightens `cv_analysis` quality surfaces in `src/fitcv/agentic_cv_analysis.py` and the stage-owned artifacts exported by `src/fitcv/pipeline.py`. The center of gravity is mostly runtime and control-plane orchestration, with diagnostics and stage artifacts acting as the shared read surface.

**Key Invariants:**
- input-mode differences stop at trigger assembly, validation, and pacing
- `manual_staged` changes timing only, not stage meaning
- resume-from-checkpoint restores canonical runtime truth rather than inventing alternate stage semantics
- `cv_analysis` owns evidence retrieval, selection summaries, gap reasoning, and pre-writing readiness truth
- downstream surfaces may summarize analysis quality but must not reinterpret it

**Rollout / Revert:**  
- rollback_trigger: manual or resumed runs start producing different downstream stage semantics than equivalent `run_all` runs, or `cv_analysis` records become less explainable from bounded evidence and summaries  
- rollback_method: revert the Wave 3 parity and analysis-grounding patches together until canonical run-envelope and `cv_analysis` quality semantics are restored

## Triage

Layer: `change`  
Feature type: `ADD`  
Summary: Implement the Wave 3 input-mode-parity and `cv_analysis` grounding subset across trigger preparation, checkpoint continuation, analysis artifacts, and debugging surfaces.  
Reasoning:

- the execution map explicitly groups these two specs into one bounded Wave 3 slice
- both specs rely on the now-stable Wave 1 and Wave 2 truth vocabulary
- the work is cross-surface but still bounded to canonical run-envelope parity and stage-owned analysis quality

Invariants:

- trigger provenance stays inspectable without becoming semantic truth
- checkpoint and continue flow resume canonical next-stage execution only
- `cv_analysis` summaries stay bounded, explainable, and stage-owned

Dependencies:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-input-mode-parity-spec.md`
- `docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md`
- `docs/superpowers/execution_maps/2026-04-28-fitcv-first-wave-implementation-execution-map.md`
- merged Wave 1 and Wave 2 runtime-truth work on `main`

Affected stages:

- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

Affected features:

- `trigger_run_management`
- `cv_system`
- `inspection_debugging`
- `settings_system`

Primary lens: `mixed`

Affected docs:
  feature_source: `none`
  feature_yaml: `none`
  feature_lineage: `none`
  feature_history: `none`
  stage_source: `none`
  stage_contract: `none`
  feature_docs:
    - `none`
  cross_cutting_docs:
    - `none`
  operating_system_docs:
    - `none`
  readme: `none`
  generated:
    - `docs/generated/planning_lineage.yaml`

Generated refresh required: `yes`  
Capability IDs:

- `none`

Invariant IDs:

- `none`

Spec needed: `yes`  
Plan needed: `yes`

Rollback trigger:

- canonical run-envelope fields start diverging by trigger mode, or bounded
  `cv_analysis` records stop explaining why a job was ready, blocked, skipped,
  or failed

Rollback method:

- revert the combined Wave 3 parity and analysis-grounding changes until the
  canonical envelope and stage-owned analysis semantics are consistent again

Migration needed: `no`  
Risk level: `medium`

## Doc Update Matrix

- Feature source: `none`
- Feature contract: `none`
- Feature lineage: `none`
- Stage source: `none`
- Stage contracts: `none`
- Feature history: `none`
- Feature-specific docs: `none`
- Cross-cutting docs: `none`
- Operating-system docs: `none`
- README: `none`
- Generated discovery:
  - `docs/generated/planning_lineage.yaml`

## File Structure First

Files to modify:

- `src/fitcv_cp/app.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/agentic_cv_analysis.py`
- `src/fitcv/contracts.py`
- generated:
  - `docs/generated/planning_lineage.yaml`

Tests to update:

- `tests/test_fitcv_cp/test_app.py`
- `tests/test_pipeline.py`

Files to create:

- none

## Task 1: Lock Canonical Input-Mode And Checkpoint Parity

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv_cp/app.py`
  - `src/fitcv/pipeline.py`
- Test:
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_pipeline.py`
- Docs:
  - `none`

- [ ] Step 1: Add or tighten failing tests for:
  - `run_all` versus `manual_staged` preserving the same downstream stage semantics
  - candidate-profile input mode resolving into one canonical runtime payload
  - checkpoint continuation resuming only from the canonical next stage
  - run-detail provenance showing mode differences without changing outcome meaning
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "continue or run_mode or checkpoint or candidate_profile"`
  - `python -m pytest tests/test_pipeline.py -k "checkpoint or resume or manual_staged or candidate_profile_json"`
- [ ] Step 3: Update `src/fitcv_cp/app.py` and `src/fitcv/pipeline.py` so:
  - all supported trigger modes normalize into one canonical post-trigger envelope
  - `manual_staged` remains a pacing mode only
  - continue flow resumes from canonical `next_stage` and does not reinterpret completed stages
  - mode provenance remains inspectable without being required to interpret pipeline truth
- [ ] Step 4: Re-run the targeted tests and confirm pass.
- [ ] Step 5: Commit the input-mode parity change.

## Task 2: Tighten Bounded `cv_analysis` Grounding Surfaces

**Files:**
- Create: `none`
- Modify:
  - `src/fitcv/agentic_cv_analysis.py`
  - `src/fitcv/pipeline.py`
  - `src/fitcv/contracts.py`
- Test:
  - `tests/test_pipeline.py`
- Docs:
  - `none`

- [ ] Step 1: Add or tighten failing tests for:
  - `cv_analysis` records keeping bounded evidence-selection summaries
  - gap summaries staying input-derived and not acting as a second fit system
  - reused and fresh analysis records preserving `analysis_reuse_status` and fingerprint explainability
  - blocked, skipped, ready, and failed pre-writing outcomes keeping precise stage-owned reason payloads
- [ ] Step 2: Run the targeted failing tests:
  - `python -m pytest tests/test_pipeline.py -k "cv_analysis or evidence_selection_summary or analysis_reuse_status or gap_summary"`
- [ ] Step 3: Update `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/contracts.py`, and `src/fitcv/pipeline.py` so:
  - evidence-selection summaries keep the bounded required families from the spec
  - channel families stay semantically distinct
  - `cv_analysis` outputs remain explainable from ranked job snapshot, candidate inputs, selected evidence, summary, gap summary, and stage-owned reason fields
  - generation consumers reuse analysis outputs without re-owning analysis meaning
- [ ] Step 4: Re-run the targeted tests and confirm pass.
- [ ] Step 5: Commit the analysis-grounding change.

## Task 3: Run Wave 3 Validation And Refresh Discovery

**Files:**
- Create: `none`
- Modify:
  - `docs/generated/planning_lineage.yaml`
- Test:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
- Docs:
  - exact entries from the Doc Update Matrix

- [ ] Step 1: Run the focused regression suite for the Wave 3 subset:
  - `python -m pytest tests/test_pipeline.py tests/test_fitcv_cp/test_app.py -k "cv_analysis or evidence_selection_summary or checkpoint or continue or run_mode or candidate_profile"`
- [ ] Step 2: If failures reveal cross-surface drift, make the smallest bounded fix in the owning file and re-run the affected tests.
- [ ] Step 3: Refresh generated discovery and managed-doc outputs:
  - `python scripts/generate_planning_lineage.py`
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
- [ ] Step 4: Run repo contract validation:
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
- [ ] Step 5: Confirm the worktree only contains intended Wave 3 changes plus any unrelated pre-existing files.
- [ ] Step 6: Commit the Wave 3 validation and generated-output refresh.

## Shared-Surface Risks

- `src/fitcv_cp/app.py`
  - trigger or continue convenience logic can become a second semantic system
    if provenance and truth get mixed together
- `src/fitcv/pipeline.py`
  - checkpoint restoration and downstream stage handoff can drift if canonical
    next-stage semantics are not enforced consistently
- `src/fitcv/agentic_cv_analysis.py`
  - evidence-selection summaries can become too shallow, making analysis look
    grounded without actually explaining selection quality
- `src/fitcv/contracts.py`
  - channel-family definitions can blur together and weaken explainability

## Sequencing Notes

- finish canonical input-mode and checkpoint parity before tightening
  `cv_analysis` quality surfaces that depend on consistent run-envelope behavior
- keep `cv_analysis` grounding bounded and stage-owned before exposing any new
  UI or generation-time interpretation layers
- run focused pipeline and control-plane regression suites before broad contract
  validation so parity drift is easier to localize

## Acceptance Criteria

- `run_all`, `manual_staged`, and resumed runs preserve the same downstream
  stage semantics once the run enters the pipeline
- continue flow resumes canonical next-stage execution only
- bounded `cv_analysis` records explain why a job was ready, blocked, skipped,
  or failed without depending on downstream generation interpretation
- evidence-selection summaries and reuse signals stay rich enough for debugging
  and operator inspection

## Next Artifact

After this plan, the next plan should cover Wave 4 from the execution map:

- `docs/superpowers/specs/2026-04-28-agentic-synonym-proposal-engine-spec.md`
