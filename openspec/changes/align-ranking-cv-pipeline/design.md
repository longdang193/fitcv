# Design

## Context

See `proposal.md` and the two capability specs for the target behavior. The reviewed implementation already has separate ranking, evidence, CV analysis, CV generation, validation, rendering, checkpoint, and operator-inspection layers, but their contracts still permit stage-boundary drift.

Observed constraints that shape the design:

- `src/fitcv/ranking.py` still has a personalized ordering path, and `src/fitcv/pipeline_stage_runner.py` still resolves and passes a preference policy.
- Ranking input and admission artifacts already carry useful fingerprints and diagnostics, but the Stage 6 to Stage 7 envelope must be made explicit and evidence-preserving.
- `src/fitcv/agentic_cv_analysis.py` can emit fit-gate and reranker-blocked statuses, while the board expects analysis to describe truthful content and gaps for already-ranked jobs.
- `src/fitcv/agentic_cv_generation.py` already has preflight, validation, repair, and persistence structures, but the target requires an explicit ADJUST stage, a safe fallback, and independent review/PDF outcomes.
- `config/policy/cv.yaml` and `src/fitcv/cv_presets.py` currently make Europass the committed default, while the target requires the fixed myCVs template for new Stage 7 runs.
- The existing renderer/conversion and native acceptance checks are reusable; this change must integrate that path rather than add a second converter.
- The in-flight `requirement-aware-job-shortlisting` change owns Stage 5 admission. This change consumes its bounded Pareto output and does not duplicate its selector or release gates.

## Goals / Non-Goals

**Goals:**

- Establish one canonical, versioned contract between Pareto shortlist, AI-only ranking, CV analysis, CV generation, PDF persistence, and submission gating.
- Preserve backward-readable historical artifacts while making new-run behavior conform to the board.
- Reuse existing evidence, validator, renderer, persistence, checkpoint, and operator-inspection infrastructure.
- Make each failure or review state attributable to its owning stage.

**Non-Goals:**

- Rebuild requirement-aware shortlist admission or replace the existing evidence projection service.
- Add a new model provider, search service, PDF converter, database, or dependency.
- Decide release readiness, benchmark thresholds, rollout approval, latency, cost, or production calibration in this change.
- Remove historical personalized fields or rewrite old artifacts.

## Decisions

### 1. Make Stage 6 a strict AI-only projection

Use the existing `ai_score` result as the sole baseline authority. The ranking projection will:

- keep only valid finite scores in the rankable set;
- set `baseline_fit = ai_score` and compute `baseline_rank` from descending score with the existing fingerprint/URL tie-break;
- keep S/P/E/U, structured fit factors, strengths, risks, qualifiers, gaps, and evidence IDs as diagnostics;
- preserve invalid/unscored rows as status-only records; and
- stop new-run preference activation and personalized field emission while retaining legacy aliases for historical reads.

The ranking stage, not the shortlist stage, owns final order. The shortlist contract remains responsible for admission; AI scoring determines order only after admission.

**Alternative rejected:** keeping a zero-residual preference resolver. It still exposes a policy-dependent contract, allows nonzero policies to change order, and makes the board's AI-only guarantee conditional.

### 2. Introduce a versioned handoff envelope

Define one persisted envelope at the Stage 6 boundary containing job identity and JD reference, ranking score/status, qualifiers, gaps, source-backed evidence IDs, profile revision, requirement and ranking contract versions, input fingerprints, and provenance. Stage 7 consumes the envelope as an input contract but can retrieve additional canonical evidence and records any refinement as attributable rather than replacing the prior finding.

Use additive fields for new artifacts. Old checkpoints resolve through a read-only legacy adapter; new checkpoints fail closed when required identity/version fields are inconsistent. Do not make the 12,000-character prompt a storage boundary for canonical evidence.

**Alternative rejected:** passing only the compact AI request or re-running unrestricted retrieval in Stage 7 without a handoff. The first loses provenance; the second can silently overwrite validated shortlist support.

### 3. Keep Stage 7 as one stateful orchestrator

Extend the existing late-stage orchestration instead of adding a parallel pipeline. The state machine is:

1. evidence planning from JD priorities and canonical sources;
2. CREATE with the fixed myCVs template;
3. ADJUST for ATS terms, achievements, impact, clarity, and approximately 580 words;
4. unified validation of facts/provenance, exact myCVs schema, and recruiter quality;
5. bounded targeted corrections, returning to validation after each correction;
6. safe grounded fallback when the retry budget is exhausted;
7. review-state resolution;
8. exact Markdown rendering and validation;
9. existing myCVs conversion with a separate PDF result; and
10. persistence of PDF, review metadata, checksums, and submission gate.

`late_stage_contract.py` remains the status owner. Review-required is a human-review state, while validation/generation/PDF/persistence failures remain technical states. A ranked job with unresolved gaps is not skipped merely because the gaps affect what can be written.

**Alternative rejected:** treating the current validation repair loop as the implicit ADJUST step. It does not guarantee recruiter-quality optimization for factually valid drafts and makes the workflow hard to inspect.

### 4. Use the existing renderer and converter as the artifact boundary

Make the committed Stage 7 policy select the fixed myCVs template and route both optional-review and mandatory-review outcomes through the existing converter/render acceptance path. Require exact schema, links, checksums, and page-fit evidence before declaring PDF success. Converter failure gets bounded technical recovery and then an explicit failure state; it never becomes review-required success.

**Alternative rejected:** creating a new converter or treating an internal Markdown result as a PDF substitute. That duplicates infrastructure and weakens artifact verification.

### 5. Preserve observability and compatibility additively

Persist separate fields for ranking status, review status, PDF status, persistence status, and submission permission, plus a versioned provenance/handoff envelope. Keep old status aliases and personalized fields available only for historical inspection. Update operator projections so a PDF can be visible while submission remains blocked by review.

**Alternative rejected:** collapsing all outcomes into `ranked_no_cv`, `review_required`, or `accepted`. That loses the distinction the board requires and makes technical failure unrecoverable by inspection.

### 6. Verify behavior with focused contract tests

Add or update tests around ranking order, invalid score handling, preference invariance, evidence-preserving handoff, analysis gaps, explicit adjustment, three-axis validation, bounded fallback, both review states, converter failure, persistence, resume, and submission gating. Reuse current fixtures and native rendering checks; add only the smallest fixtures needed for the new state combinations.

## Risks / Trade-offs

- **Historical artifact shape drift** -> use additive versioned envelopes and read-only legacy adapters; never reinterpret old personalized order as current canonical order.
- **Evidence loss during handoff** -> require stable IDs and provenance in the envelope, then assert preservation across ranking, analysis, and generation tests.
- **Quality optimization overclaiming** -> keep ATS/recruiter quality subordinate to factual integrity, schema, and page fit; emit review-required when material concerns remain.
- **PDF tool variability** -> keep converter invocation and native acceptance in the existing renderer owner; classify missing tools or conversion errors as technical failure with explicit diagnostics.
- **Status combinatorics** -> model review, PDF, persistence, and submission as separate dimensions rather than multiplying opaque status strings; expose a deterministic projection for legacy consumers.
- **Scope creep into readiness work** -> do not add latency, cost, benchmark, rollout, or calibration gates to this implementation contract; track them as deferred follow-up evidence.

## Migration Plan

1. Add the ranking and Stage 7 contract fields and focused tests without deleting historical fields.
2. Change new-run ranking to AI-only and make the myCVs template the Stage 7 policy default.
3. Route ranked jobs through the evidence-preserving handoff and fixed-order Stage 7 state machine.
4. Enable the existing converter for both review branches, persist independent PDF/review/submission outcomes, and verify resume compatibility.
5. Update operator views and documentation to display the new dimensions while retaining legacy projections.
6. Leave release-readiness assessment and rollout approval for a later evidence task; rollback of behavior remains possible through the existing configuration/checkpoint compatibility path.
