# Design

## Context

The target architecture has three distinct boundaries: Stage 5 admits an evidence-gated Pareto shortlist, Stage 6 orders that bounded shortlist with AI score only, and Stage 7 turns each Final Top 15 job into a grounded CV artifact without conflating technical completion, human review, PDF production, or submission permission. The current repository already contains the required primitives, but several callers still join those boundaries: personalized ranking is still callable, the Stage 6 to Stage 7 handoff is implicit, CV analysis can reject already-ranked jobs, the committed CV preset is `europass`, and late-stage status projections do not independently represent review and PDF outcomes.

Observed implementation anchors:

- Stage 6 orchestration: `src/fitcv/pipeline_stage_runner.py:execute_ranking_stage`.
- Stage 6 input assembly: `src/fitcv/pipeline_stage_runner.py:build_ranking_job_input`, `build_ranking_input_diagnostics`, `src/fitcv/pipeline.py:build_ranking_features`.
- Score normalization and projections: `src/fitcv/ranking_contract.py:normalize_score_state`, `build_baseline_result`, `adapt_legacy_ranking_row`, `project_legacy_ranking_aliases`.
- Ranking order: `src/fitcv/ranking.py:rank_jobs`.
- Stage 7 orchestration: `execute_cv_analysis_jobs` and `execute_cv_generation_records` in `src/fitcv/pipeline_stage_runner.py`.
- CV analysis/generation: `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/agentic_cv_generation.py`, and `src/fitcv/late_stage_contract.py`.
- Rendering and conversion: `src/fitcv/cv_generator.py` and `src/fitcv/cv_presets.py`, configured through `config/policy/cv.yaml`.
- Canonical structured CV schema: `src/fitcv/contracts.py:STRUCTURED_CV_SCHEMA_VERSION` (`cv_doc_v1`).
- Existing Stage 5 admission remains owned by the `requirement-aware-job-shortlisting` change; this change consumes its output and does not duplicate its selector or admission gate.

## Goals / Non-Goals

**Goals:**

- Make the Stage 5 -> Stage 6 -> Stage 7 data contract explicit and versioned.
- Make new Stage 6 output AI-only, deterministic, evidence-preserving, and bounded.
- Make Stage 7 a fixed-order grounded workflow with an explicit ADJUST step.
- Separate technical validation, review, PDF, persistence, and submission states.
- Reuse existing scoring, evidence, checkpoint, renderer, converter, and operator-inspection code.
- Preserve historical artifacts and checkpoints through additive compatibility adapters.

**Non-Goals:**

- Rebuild Stage 5 shortlist admission or replace the existing evidence projection service.
- Add a model provider, retrieval service, converter, database, or dependency.
- Decide release readiness, rollout approval, calibration, benchmark closure, latency, or cost gates.
- Rewrite historical personalized rankings or change their meaning.

## Canonical Data Flow and Ownership

1. **Stage 5 input:** the requirement-aware shortlist supplies at most 50 admitted jobs, each with stable identity, JD reference, eligibility/support evidence, qualifiers, gaps, and provenance. Stage 6 must consume this record rather than recompute admission.
2. **Stage 6 evidence preparation:** `execute_ranking_stage` selects attributable complementary evidence for each admitted job, records its source IDs and retrieval diagnostics, and passes the combined record to `build_ranking_job_input`. Complementary evidence may add context but cannot replace Stage 5 support, qualifiers, gaps, or admission status.
3. **Bounded ranking request:** the ranking input builder serializes mandatory job/candidate identity and provenance first, then evidence and diagnostics by deterministic precedence. The serialized request has a 12,000-character boundary. If mandatory identity/provenance cannot fit, the row receives an explicit bounded-input failure/status and is not submitted as a normal score request.
4. **AI scoring:** `run_ai_scoring` produces `ai_score` plus score status, failure diagnostics, six diagnostic factors, reasoning, strengths, risks, and provenance. `normalize_score_state` is the trust boundary: only finite values in `[0.0, 1.0]` are valid.
5. **Stage 6 projection:** `build_ranking_features` joins shortlist rows and AI results. `rank_jobs` admits only valid finite scores, sorts by descending `ai_score`, then uses the existing deterministic raw-fingerprint/URL tie-break. New output sets `baseline_fit = ai_score`, `baseline_rank = final order`, and `final_rank = baseline_rank`. Invalid or unscored rows remain status-only and inspectable outside Final Top 15.
6. **Versioned Stage 6 handoff:** every Final Top 15 row is persisted and passed to Stage 7 through one additive envelope. The envelope is the source of truth for Stage 7 input, while Stage 7 may retrieve additional canonical evidence and records any refinement as a new attributable finding.
7. **Stage 7 analysis:** `execute_cv_analysis_jobs` and `agentic_cv_analysis` create a generation-ready evidence plan, truthful omissions, and JD gaps for each ranked job. Ranking validity is not re-decided here; a missing professional or qualification fact becomes a gap/omission or review reason, not an unintended secondary fit rejection.
8. **Stage 7 generation:** `execute_cv_generation_records` and `agentic_cv_generation` run the fixed sequence in the next section. Existing validators, persistence, and render-acceptance helpers remain the implementation owners.
9. **Artifact and gate:** the exact Markdown artifact is validated, converted by the existing myCVs path, verified after conversion, and persisted. Review and submission decisions are then evaluated from the current artifact revision and independent state dimensions.

## Canonical Stage 6 -> Stage 7 Handoff

The envelope is additive and versioned. Required field groups are:

- **Identity:** stable job identity, canonical job URL, employer/title when available, and the JD reference or snapshot identifier.
- **Admission:** Stage 5 admission status, shortlist contract/version, eligibility/support evidence, qualifiers, gaps, and the evidence/provenance IDs that justify them.
- **Ranking:** `ai_score`, `score_status`, failure code when present, `baseline_fit`, `baseline_rank`, `final_rank`, ranking contract/version, and deterministic input fingerprint.
- **Candidate context:** profile revision/fingerprint and the candidate evidence IDs used for the ranking request.
- **Traceability:** ranking request fingerprint/diagnostics, evidence-source provenance, model/strategy/version, run ID, and timestamps.
- **Stage 7 carry-forward:** the envelope identity and all admission/ranking evidence must be copied into analysis, generation, Markdown, PDF, checkpoint, and operator projections; later enrichment is additive and attributable.

A new checkpoint fails closed when required identity, version, or provenance fields are inconsistent. A historical checkpoint is loaded through a read-only adapter (`adapt_legacy_ranking_row` and the existing late-stage projection helpers); loading it must not rewrite the historical row or reinterpret personalized order as current canonical order.

## Stage 7 State Machine

The existing late-stage owners retain control of their domains, but the persisted result exposes separate dimensions rather than one opaque outcome string:

1. **Evidence plan** -> canonical source selection, supported facts, omissions, gaps, and provenance.
2. **CREATE** -> structured CV using the fixed myCVs template and `cv_doc_v1` schema.
3. **ADJUST** -> targeted improvement for ATS terminology, achievements, impact, clarity, and approximately 580 words as an optimization target.
4. **Validation** -> factual/provenance hard checks, exact Markdown schema checks, and recruiter/ATS quality diagnostics.
5. **Retry/fallback** -> bounded targeted corrections; after exhaustion, emit the safest grounded fallback and rerun factual/provenance and exact-schema checks.
6. **Review resolution** -> grounded omissions may be optional review; retained uncertain facts require mandatory review; unsupported claims or hard provenance violations remain technical validation failure.
7. **Markdown** -> deterministic render from the committed template and validation of required sections, links, checksums, and configured page-fit inputs.
8. **PDF** -> existing converter for both optional-review and mandatory-review branches, followed by persisted-PDF integrity, render, schema/link/checksum, and configured page-fit acceptance.
9. **Persistence/submission** -> persist artifacts and metadata independently; derive submission permission only from current technical states and current review decision.

The persisted dimensions are:

- `analysis_status` / `generation_status`: stage-owned technical progress and failure.
- `review_status`: `not_required`, `optional`, or mandatory lifecycle `pending`, `approved`, `rejected`.
- `pdf_status`: `not_attempted`, `verified`, or technical failure with diagnostics.
- `persistence_status`: artifact/metadata persistence outcome.
- `submission_allowed`: derived boolean, true only when required technical checks, persistence, and mandatory review approval all cover the current revision.

A mandatory review decision stores reviewer identity, decision time, reason, and exact CV/PDF revision fingerprint. Any content or PDF change invalidates an earlier approval and returns review to `pending`. A PDF may be visible while submission remains blocked. Converter or post-conversion acceptance failure is never represented as review-required success.

## Ranking Projection Rules

- Do not call `resolve_run_preference_policy` for new Stage 6 ordering and do not pass a nonzero preference policy to `rank_jobs` for a new run.
- Preserve historical preference fields and `resolved_preference_policy` only for read compatibility and inspection; do not emit them as authoritative new-run ordering fields.
- Do not convert invalid, missing, non-finite, or out-of-range scores to zero.
- Do not use structured fit, S/P/E/U, diagnostic factors, or fit labels as additional ranking weights or admission filters.
- Keep status-only rows in the ranking artifact with status and diagnostics but without `baseline_rank`, `final_rank`, or Final Top 15 membership.
- Keep the 12,000-character request boundary independent from the persisted evidence envelope; truncation may reduce prompt detail but must not delete stored canonical evidence.

## Configuration and Compatibility

- New Stage 7 runs use the committed `templates/cv_template.md` and `cv_doc_v1`. Update the policy/preset path in `config/policy/cv.yaml` and `src/fitcv/cv_presets.py` without removing the historical Europass read path.
- Existing renderer and converter behavior remains the only PDF production path; no replacement converter is introduced.
- Checkpoint/resume code must preserve new envelope and state fields on fresh runs and reuse. Legacy checkpoints remain readable through adapters and are projected with legacy semantics only.
- Operator projections and exports expose the new dimensions while retaining deterministic legacy aliases for historical rows.

## Verification Ownership

- Ranking contract and projection: `tests/test_ranking.py` and `tests/test_ranking_contract.py`.
- Stage 5 -> Stage 6 evidence and request boundary: `tests/test_pipeline.py` plus ranking-input/evidence tests.
- Analysis/generation state machine: `tests/test_agentic_cv_analysis.py`, `tests/test_agentic_cv_generation.py`, and `tests/test_pipeline_agentic_late_stage.py`.
- Markdown/PDF acceptance: `tests/test_cv_render_acceptance.py` and the focused `cv_generator` tests.
- Checkpoint/resume/legacy semantics: `tests/test_pipeline_checkpoint_contract.py`, `tests/test_pipeline_stage_resume_parity.py`, and pipeline persistence tests.
- Configuration/operator contract: `tests/test_config.py`, `tests/test_pipeline.py`, and the affected operator projection tests.

## Risks / Trade-offs

- **Historical shape drift:** additive fields and read-only adapters avoid rewriting or reinterpreting old personalized artifacts.
- **Evidence loss:** stable IDs, fingerprints, and carry-forward assertions make handoff loss observable.
- **Status combinatorics:** independent dimensions cost more fields but prevent PDF, review, and technical failures from being conflated.
- **Prompt truncation:** the request is bounded without making it the evidence database; mandatory overflow fails closed.
- **PDF variability:** existing native acceptance remains the artifact boundary; converter errors are technical failures with bounded recovery.
- **Scope creep:** release-readiness, performance/cost, rollout, benchmark, and calibration gates remain deferred.

## Migration Plan

1. Add additive envelope and independent state fields plus serializers/adapters and focused tests.
2. Change new-run Stage 6 projection to AI-only and remove preference policy from the new ordering path; preserve historical aliases.
3. Route ranked rows through the envelope and make analysis generation-ready for every valid Final Top 15 row.
4. Make the committed Stage 7 policy select myCVs, then add explicit ADJUST, validation, retry/fallback, review, Markdown, PDF, and submission transitions.
5. Update operator projections, checkpoints, resume behavior, and documentation without rewriting historical artifacts.
6. Run focused behavior tests and repository validation; defer release-readiness assessment to a separate change.
