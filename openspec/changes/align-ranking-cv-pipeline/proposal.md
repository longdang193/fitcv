# Proposal

## Why

The target FitCV architecture makes Stage 6 ranking an AI-only, evidence-preserving decision and makes Stage 7 a single grounded CV workflow that separates content quality, human review, and PDF production. The reviewed implementation already contains useful ranking, evidence, validation, persistence, and rendering primitives, but the assessment identifies behavior that can still cross those stage boundaries: personalized ordering, incomplete evidence handoff, secondary fit rejection, noncanonical rendering, and conflated review/PDF outcomes.

This change turns the Figma board contract into implementation-ready requirements without treating release-readiness benchmarking, rollout approval, or latency/cost evidence as immediate blockers.

## What Changes

- Define the Stage 6 contract from Pareto Top 50 to Final Top 15: valid finite `ai_score` is the only baseline ranking authority; `baseline_fit = ai_score`, `baseline_rank` is the final order, and preferences never rerank new runs.
- Preserve validated shortlist evidence, qualifiers, gaps, score/status, job identity, JD references, profile revision, versions, and provenance across the Stage 6 to Stage 7 handoff.
- Keep the 12,000-character ranking request bounded while ensuring Stage 7 can retrieve additional canonical evidence instead of treating the ranking prompt as the evidence database.
- Make invalid or unscored AI results status-only and keep promotion override records auditable with operator, reason, strategy/version, evidence-gate state, timestamp, and readable persistence.
- Define a fixed-order Stage 7 orchestrator: evidence planning, `CREATE CV`, explicit `ADJUST CV`, unified validation, targeted retries, safe grounded fallback, review-state resolution, exact myCVs Markdown rendering/validation, and mandatory PDF generation.
- Require factual integrity/provenance and exact myCVs Markdown schema as hard constraints; treat ATS/recruiter quality as an optimization objective that cannot override factual or page-fit constraints.
- Require review-required CVs to produce and persist a valid PDF while blocking submission until mandatory review is complete; classify converter failure as technical recovery/failure, never as human review success.
- Integrate the existing myCVs converter for both optional-review and mandatory-review states; do not create a replacement converter in this change.
- Preserve historical personalized artifacts and legacy statuses as read-only compatibility data while preventing new runs from emitting or consuming personalized ranking fields.

## Capabilities

### New Capabilities

- `ai-ranking`: AI-only final ranking, evidence-preserving Stage 6 handoff, score/status validation, and auditable promotion overrides.
- `cv-analysis-generation`: Unified grounded CV analysis and generation workflow with explicit adjustment, validation, review, PDF, persistence, and submission states.

### Modified Capabilities

None. No maintained capability specs currently exist in `openspec/specs/`; the in-flight `requirement-aware-job-shortlisting` change remains the owner of its shortlist-admission proposal and is not duplicated here.

## Impact

- Ranking contract and orchestration: `src/fitcv/ranking_contract.py`, `src/fitcv/ranking.py`, `src/fitcv/pipeline_stage_runner.py`, and ranking exports.
- Stage handoff and evidence: `src/fitcv/ai_score.py`, `src/fitcv/evidence.py`, `src/fitcv/contracts.py`, `src/fitcv/pipeline.py`, and stage artifact/persistence modules.
- CV analysis and generation: `src/fitcv/agentic_cv_analysis.py`, `src/fitcv/agentic_cv_generation.py`, `src/fitcv/late_stage_contract.py`, `src/fitcv/validator.py`, and `src/fitcv/cv_generator.py`.
- Canonical rendering and configuration: `config/policy/cv.yaml`, `src/fitcv/cv_presets.py`, and the existing myCVs conversion path.
- Tests and documentation: ranking, pipeline, analysis, generation, rendering, persistence, resume, and operator-inspection tests plus the relevant pipeline/configuration documentation.
- No new service, model provider, converter, or dependency is required.
- Deferred from this change: release-readiness risk assessment, performance/cost gates, rollout approval, and benchmark closure. These remain follow-up evidence after behavior is aligned.
