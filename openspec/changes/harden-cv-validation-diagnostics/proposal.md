# Proposal

## Why

The CV acceptance pipeline has several verified contract mismatches at the Stage 7 boundary: the validator derives a different required section order than the myCVs serializer emits, skill authority can fall back to reparsing rendered Markdown, deterministic validation failures discard otherwise useful drafts, and failure reasons are re-inferred from warnings or free-form messages. These defects make internal formatting and projection problems look like provider failures, hide useful evidence, and prevent operators from distinguishing invalid content from review, rendering, and persistence outcomes.

## What Changes

- Make one versioned myCVs section-order policy authoritative for structured composition, Markdown serialization, structural validation, and PDF acceptance; omitted sections retain their relative order.
- Preserve a generated structured CV, rendered draft, validation snapshot, and typed diagnostics in an explicit quarantined-draft state after validation failure when those artifacts exist; keep submission blocked and prevent quarantined content from being treated as accepted output.
- Make structured skill claims and their canonical provenance the factual authority. Rendered Markdown remains a serialization and syntax projection only and SHALL NOT create or reject skill facts by itself.
- Replace warning/message substring classification with typed diagnostics carrying stable codes, category, severity, blocking, retryability, source, and structured facts. Keep human-readable messages for display only.
- Keep content validity, review state, artifact/PDF state, and submission clearance independent so a valid review-required artifact, an invalid quarantined draft, and a renderer failure are represented without overwriting one another.
- Treat length/page-fit warnings as quality or artifact diagnostics according to the actual acceptance stage; they SHALL NOT be classified as generation-format defects merely because their message contains length or budget text.
- Preserve legacy status and reason projections for readers during migration, but make new routing, persistence, retry, and operator summaries use typed diagnostic codes and explicit state fields.

## Verified Review Basis

- Confirmed: `src/fitcv/validator.py` builds `Skills` before `Certificates`, while the myCVs serializer emits `Certificates` before `Skills`.
- Confirmed: skill validation has a rendered-text fallback when structured skill items are absent.
- Confirmed: `validation_failed` results currently lose the final structured/Markdown payload in the generation result path and are not eligible for the same persistence path as review-required drafts.
- Confirmed: review-reason mapping contains repeated message-based branches and a `manual_review_other` fallback; length warnings can enter generation-format classification.
- Not established from the review alone: the reported run's exact source of the `python` finding, the actual PDF page count, and the original run's persistence outcome. This change does not treat those as proven root causes.

## Capabilities

### New Capabilities

- `cv-validation-diagnostics`: Deterministic CV validation, quarantine preservation, structured factual authority, and typed diagnostic/state projections for generation and acceptance.

### Modified Capabilities

None. The repository has no maintained `openspec/specs/` capability inventory yet; the existing Stage 6/7 and generation documents are change-local historical context.

## Impact

- CV policy and serialization: `src/fitcv/section_policy.py`, `src/fitcv/cv_presets.py`, and `src/fitcv/cv_generator.py`.
- Validation and factual authority: `src/fitcv/validator.py`, structured CV normalization, skill canonicalization, and grounding/provenance inputs.
- Lifecycle and persistence: `src/fitcv/agentic_cv_generation.py`, `src/fitcv/pipeline.py`, `src/fitcv/pipeline_contracts.py`, persistence projections, and operator exports.
- Tests and fixtures: validator, renderer/acceptance, generation reason mapping, pipeline persistence/status, and Stage 6/7 contract coverage.
- Compatibility: existing accepted, review-required, PDF-failed, and legacy status values remain readable; no page-count policy is changed by this proposal.
