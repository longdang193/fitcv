---
layer: change
artifact_type: spec
status: proposed
template_id: draft-specification
name: fitcv-cv-preview-transport
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - docs/api.md
related_features:
  - grounded-cv-generation-and-review
  - cv-preview
  - cv-download
---

# FitCV CV Preview Transport

## Goal and Scope

- problem or opportunity: frozen UX offers View CV, while canonical API exposes only Download CV.
- affected users or systems: new frontend CV review and backend CV version storage.
- desired outcome: user can inspect exact immutable CV version before downloading it.
- included scope: read-only version-specific preview transport and lifecycle/error semantics.
- excluded scope: editing CV content, generating HTML on server, mutating review/evaluation state, or changing download behavior.

## User Flow and Business Rules

1. Client selects a CV version from `GET /runs/{run_id}/jobs/{run_job_id}/cvs`.
2. Client requests `GET /cv-versions/{version_id}/preview`.
3. Server verifies version existence, generated/review-required state, stored length, and SHA-256 checksum.
4. Server returns exact persisted bytes inline; client renders supported content safely and may still download through existing route.

- Version identity is immutable and remains selected `version_id`; preview cannot silently switch to current version.
- Evaluation, review state, parent identity, generation metadata, and immutable run snapshot remain unchanged.
- `capabilities.preview` is true exactly when `capabilities.download` is true and stored media is `text/markdown` or `text/plain`.
- Preview uses same integrity verification as download.
- Missing version returns `404 cv_not_found`; pending/unavailable content returns `409 artifact_not_available`; corrupt content returns `409 artifact_not_available` with retryable action guidance.
- Response includes checksum-backed `ETag`, `Content-Length`, `X-Content-Type-Options: nosniff`, and `Content-Disposition: inline`.
- Preview is available only for stored `text/markdown` or `text/plain` content; other media types expose `preview: false` and return `409 artifact_not_available`.
- Download remains `GET /cv-versions/{version_id}/download` with attachment disposition and unchanged bytes/headers.

## UI Intent and Known States

- target platform: new frontend CV review dialog/page.
- intended interaction: View CV opens selected immutable version, shows metadata and review/evaluation truth, and offers Download.
- loading, empty, success, error, disabled, and retry states: loading; rendered preview; no preview when generation is pending/failed; integrity error with Console/regenerate action; download remains independently available when capability says so.
- accessibility or responsive intent: semantic dialog or page, keyboard close/focus return, selectable text, visible version identity, and 44px actions.
- durable design-system owner: Agentic Design System SSOT; verified FitCV Design Export is guidance evidence.

## Assumptions and Open Questions

### Verified Facts

- CV storage already has `get_cv_download()` integrity checks and immutable terminal versions: `src/fitcv_cp/sqlite_store.py`.
- canonical list includes evaluation and review state: `_cv_projection()` and `docs/api.md`.
- API errors use standard envelope fields `code`, `message`, `field_errors`, `retryable`, and `action`.

### Assumptions

- persisted CV media is previewable as its stored media type; frontend owns safe rendering and plain-text fallback.

### Open Questions

- none that change the read-only transport contract.

## Prototype and Validation Findings

- prototype reference: `docs/fitcv-settings-ui-prototype.html` CV View CV action.
- UX approval: owner-approved frozen UX.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`; gate state: complete.
- scenario required for validation: generated version, review-required version, pending version, missing version, corrupt artifact, unsupported media type, preview then download.
- observed result: View CV needs canonical media response; download already has stable contract.
- accepted behavior: exact version bytes, separate evaluation/review truth, unchanged download.
- rejected behavior: preview of latest version by job only, server-side content rewrite, preview implying approval.
- remaining uncertainty: supported frontend renderers are implementation detail.
- boundary implication when material: backend read route plus existing store helper; frontend rendering is separate.

## Promotion Readiness

- owner approval or `Not approved: <reason>`: proposed pending independent specification review.
- approval reference: accepted reconciliation finding G-02.
- remaining blockers or `None identified`: independent review.
- approved deferrals with owner, rationale, trigger, and approval reference or `None`: None.
- unresolved behavior-changing questions or `None`: None.
