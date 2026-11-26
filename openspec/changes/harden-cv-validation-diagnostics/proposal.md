# Proposal

## Why

The CV acceptance pipeline has several verified contract mismatches at the Stage 7 boundary: the validator derives a different required section order than the myCVs serializer emits, skill authority can fall back to reparsing rendered Markdown, deterministic validation failures discard otherwise useful drafts, and failure reasons are re-inferred from warnings or free-form messages. These defects make internal formatting and projection problems look like provider failures, hide useful evidence, and prevent operators from distinguishing invalid content from review, rendering, and persistence outcomes.

## What Changes

- Make one versioned myCVs section policy authoritative for structured composition, Markdown serialization, structural validation, and PDF acceptance. The policy owns canonical keys, display names, presence rules, header handling, and meaningful-content omission.
- Preserve a generated structured and/or rendered draft, validation snapshot, and typed diagnostics in an explicit quarantined-draft state after validation failure when usable evidence exists; keep submission blocked and prevent quarantined content from being treated as accepted output.
- Make structured skill claims and their canonical provenance the factual authority. Rendered Markdown remains a projection and SHALL NOT create a structured skill fact; material projection discrepancies SHALL block final artifact acceptance without falsely changing the structured fact result.
- Extend the existing outcome-classification contract with one versioned typed diagnostic registry carrying stable codes, category, severity, blocking, retryability, terminality, source, and structured facts. Keep human-readable messages for display only.
- Extend the existing Stage 6/7 lifecycle contract rather than introduce a competing state machine: keep technical/generation, content validity, draft disposition, review, PDF/artifact, persistence, and derived submission-clearance states independent.
- Treat length/page-fit warnings as quality or artifact diagnostics according to the actual acceptance stage; they SHALL NOT be classified as generation-format defects merely because their message contains length or budget text.
- Version validation policy, diagnostic schema, section policy, and skill provenance in Stage 7 fingerprints and checkpoints so affected validation/generation reuse is invalidated without unnecessarily recomputing compatible Stage 6 work.
- Preserve legacy status and reason projections for readers during migration, but make new routing, persistence, retry, reuse, and operator summaries use typed diagnostic codes and explicit state fields.

## Preserved Accepted Behavior

- Stage 6 handoff validity remains the authoritative Stage 7 admission boundary.
- Hard factual and schema safeguards remain blocking; review approval cannot override a hard validation failure.
- Verified PDF acceptance and the configured page-fit policy remain required for completed artifact behavior.
- Existing accepted, review-required, PDF-failed, persistence-failed, validation-failed, and historical records remain readable without historical rewriting.

The state, diagnostic, quarantine, provenance, and versioning rules below are proposed behavior for new attempts. They are not claims that the current implementation already satisfies them.

## Verified Review Basis

- Confirmed: `src/fitcv/validator.py` builds `Skills` before `Certificates`, while the myCVs serializer emits `Certificates` before `Skills`.
- Confirmed: skill validation has rendered-text authority in more than one validation path when structured provenance is absent or not used.
- Confirmed: `validation_failed` results currently lose the final structured/Markdown payload in the generation result path and are not eligible for the same persistence path as review-required drafts.
- Confirmed: review-reason mapping contains repeated message-based branches and a `manual_review_other` fallback; length warnings can enter generation-format classification.
- Confirmed: existing `pipeline_contracts.py` and late-stage helpers already own outcome and submission concepts; this change must extend them rather than create a parallel authority.
- Confirmed: pipeline and control-plane worker persistence have separate write/read boundaries, and SQLite uses explicit columns, status constraints, and artifact-integrity checks.
- Not established from the review alone: the reported run's exact source of the `python` finding, the actual PDF page count, and the original run's persistence outcome. This change does not treat those as proven root causes.

## Capabilities

### New Capabilities

- `cv-validation-diagnostics`: Deterministic CV validation, quarantine preservation, structured factual authority, and typed diagnostic/state projections for generation and acceptance.

### Modified Capabilities

None. The repository has no maintained `openspec/specs/` capability inventory yet; the existing Stage 6/7 and generation documents are change-local historical context.

## Impact

- CV policy and serialization: `src/fitcv/section_policy.py`, `src/fitcv/cv_presets.py`, `src/fitcv/cv_generator.py`, and PDF acceptance helpers.
- Validation and factual authority: `src/fitcv/validator.py`, structured CV normalization, skill canonicalization, provenance/evidence inputs, and projection checks.
- Lifecycle and diagnostic authority: `src/fitcv/pipeline_contracts.py`, `src/fitcv/late_stage_contract.py`, `src/fitcv/agentic_cv_generation.py`, and compatibility projections.
- Lifecycle and persistence: `src/fitcv/pipeline.py`, `src/fitcv_cp/worker_job.py`, `src/fitcv_cp/sqlite_store.py`, checkpoint/reuse helpers, and operator exports.
- Tests and fixtures: validator, renderer/acceptance, generation reason mapping, pipeline persistence/status, worker/SQLite migration, reuse/checkpoint, and Stage 6/7 contract coverage.
- Documentation: pipeline, observability, API/configuration status contracts, and migration notes.
- Compatibility: existing accepted, review-required, PDF-failed, persistence-failed, and legacy status values remain readable; no page-count policy is changed by this proposal.
