---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
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

## Goal and Problem

### Problem

- current behavior or opportunity: frozen UX offers View CV, while canonical API exposes Download CV only.
- affected users, systems, or maintainers: new frontend CV review and backend CV version storage.
- evidence: CV list exposes immutable version identity and review/evaluation fields, while download is the only artifact transport.
- consequence of no change: users must download to inspect a CV and may lose clear version context.

### Goal

- desired outcome: user can inspect exact immutable CV version before downloading it.
- observable success: preview returns the selected stored bytes and metadata without mutating review, evaluation, generation, or download behavior.

## Required Outcomes

### Outcome: Version-specific preview

- affected actor or system: new frontend CV review and CV version API.
- required result: selected `version_id` returns exact previewable stored bytes or a truthful unavailable error.
- success condition: preview cannot silently switch to another version or imply approval.

### Outcome: Preserve CV truth and download

- affected actor or system: CV version store, review/evaluation state, and download consumer.
- required result: preview shares integrity checks but does not alter immutable identity, review/evaluation truth, or download semantics.
- success condition: same version remains selectable and download returns unchanged attachment bytes.

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| Does CV version identity already exist? | CV list and storage use immutable version IDs and terminal version state. | `src/fitcv_cp/sqlite_store.py` | high | Preview must be keyed by `version_id`. |
| Does stored integrity validation exist? | Download path verifies stored length and SHA-256 checksum. | `src/fitcv_cp/sqlite_store.py` | high | Preview reuses equivalent integrity truth. |
| Are review and evaluation fields separate from artifact bytes? | CV projection exposes evaluation and review state. | `_cv_projection()` and `docs/api.md` | high | Preview must expose truth without mutating it. |

### Prototype and Validation Evidence

- prototype reference: `docs/fitcv-settings-ui-prototype.html` CV View CV action.
- UX approval: owner-approved frozen UX.
- frozen prototype revision or reference: approved FitCV settings UX prototype.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`.
  - selected export method: verified OpenDesign export.
  - export task reference: recorded Design Export completion evidence.
  - requested deliverable: FitCV design-system guidance.
  - durable output identity: `fitcv-design-system-export.md`.
  - independent review: `PASS` for the verified export.
- validated scenarios and states: generated version, review-required version, pending version, missing version, corrupt artifact, unsupported media type, preview then download, and focus return after closing preview.
- findings incorporated into approved behavior: immutable version selection, safe inline disposition, separate review/evaluation truth, and independent download.
- rejected alternatives: latest-version-by-job preview, server-side content rewrite, preview implying approval, and changed download semantics.

### Scope

- included behavior: read-only `GET /cv-versions/{version_id}/preview`, preview capability signaling, integrity/error semantics, safe inline headers, and frontend preview rendering boundary.
- affected boundaries: CV version API, canonical store integrity checks, and new frontend CV review surface.
- admissible cases: stored `text/markdown` and `text/plain` artifacts with valid integrity metadata.
- compatibility expectation: existing CV list, review/evaluation fields, and download contract remain compatible.

### Non-Goals

- editing CV content or review state.
- generating HTML on server.
- changing generation, evaluation, approval, or download behavior.
- previewing unsupported media types through unsafe rendering.

### Requirements and Behavioral Contract

#### Requirement: Preview selected immutable version

- trigger or actor: client selects a CV version from the canonical CV list.
- preconditions: `version_id` identifies a stored version and the client has permission to read it.
- required behavior: `GET /cv-versions/{version_id}/preview` returns exact persisted bytes for previewable media.
- output or state change: response uses inline disposition and preserves version identity; no domain state changes.
- failure behavior: missing version returns `404 cv_not_found`; pending/unavailable content or invalid integrity returns `409 artifact_not_available` with retryable/action guidance; unsupported media returns the same unavailable contract.
- observable acceptance: response bytes and selected `version_id` match canonical stored version.

#### Requirement: Signal preview capability and preserve truth

- trigger or actor: client reads CV version projection.
- preconditions: version projection includes download capability and stored media type.
- required behavior: `capabilities.preview` is true exactly when download is available and media is `text/markdown` or `text/plain`; review/evaluation, parent identity, generation metadata, and immutable run snapshot remain unchanged.
- output or state change: frontend can disable View CV without changing Download CV.
- failure behavior: preview never claims approval or substitutes latest version.
- observable acceptance: capability, displayed metadata, and review/evaluation state match canonical projection.

#### Requirement: Preserve integrity and download semantics

- trigger or actor: preview or download request.
- preconditions: stored length and SHA-256 metadata exist.
- required behavior: verify integrity before serving; preview returns `ETag`, `Content-Length`, `X-Content-Type-Options: nosniff`, and `Content-Disposition: inline`; download remains attachment with unchanged bytes.
- output or state change: only read response is produced.
- failure behavior: corrupt content is not served as valid preview or download.
- observable acceptance: preview and download either pass the same integrity truth or return a consistent artifact-unavailable error.

| Boundary | Owner or canonical contract | Required evidence |
| --- | --- | --- |
| CV version identity and bytes | Canonical CV version store | Direct boundary tests and checksum proof |
| Preview transport | `GET /cv-versions/{version_id}/preview` | Route contract and response-header tests |
| Review/evaluation truth | Existing CV projection | Projection regression proof |
| Download | Existing `/cv-versions/{version_id}/download` contract | Existing and regression tests |

### Constraints and Alternatives

- constraint: immutable CV version identity and review/evaluation truth must remain separate from presentation transport.
- alternative: preview latest CV by run/job
  - benefit: simpler client URL.
  - trade-off: can display wrong version after regeneration.
  - reason accepted or rejected: rejected because it violates immutable version selection.
- alternative: server transforms Markdown to HTML
  - benefit: richer rendering.
  - trade-off: content rewriting and new sanitization/security ownership.
  - reason accepted or rejected: rejected; frontend safe rendering and plain-text fallback are sufficient for current scope.

## Design Decisions

### Decision: Add read-only version-keyed preview transport

- context: frozen UX requires View CV while download already provides stable artifact identity.
- selected approach: inline preview route keyed by immutable `version_id`, sharing integrity checks with download.
- rationale: smallest transport change that preserves domain truth and download compatibility.
- alternatives considered: job-keyed latest preview and server-side HTML transformation.
- accepted trade-offs: supported preview media is limited to Markdown/plain text; unsupported formats remain downloadable only.
- affected owners and boundaries: backend route/store owns bytes and headers; frontend owns safe rendering and review presentation.

### Compatibility, Migration, and Risk

- old behavior: CV versions can be downloaded but not inspected inline.
- new behavior: previewable versions expose exact inline bytes and explicit capability.
- compatibility boundary: download route, CV projection identity, and review/evaluation fields do not change.
- migration or backfill: none; existing stored integrity metadata is required and invalid artifacts remain unavailable.
- rollout and rollback: frontend can hide View CV if route is unavailable; removing preview route leaves download intact.
- deprecation or consumer impact: none for existing download consumers.
- risk:
  - mitigation: immutable version key, checksum validation, `nosniff`, inline disposition, and no server content rewrite.

## Invariants and Edge Cases

### Invariants

- preview response is keyed by requested immutable `version_id`.
- preview never mutates review, evaluation, generation, or parent identity.
- preview and download do not serve bytes failing integrity validation.
- unsupported media never receives a false preview capability.
- download remains attachment with unchanged content.

### Edge Cases

- empty or minimal input: missing or blank version ID returns canonical not-found behavior.
- normal and large input: exact stored bytes are served; response size follows stored artifact and transport limits.
- duplicate, missing, malformed, or unsupported data: missing metadata or checksum mismatch returns artifact unavailable; unsupported media is not inline-rendered.
- retry, cancellation, timeout, partial failure, or concurrency: read failures expose retryable/action guidance; concurrent regeneration cannot change selected version identity.
- migration or mixed-version state: older versions without valid integrity metadata remain unavailable rather than being rewritten.
- generated-source consistency: API documentation and route contract must match implementation response shape.
- security or accessibility boundary: `nosniff`, safe frontend rendering, selectable text, semantic dialog/page, keyboard close/focus return, visible version identity, and 44px actions.

## Validation Plan

### Backend Verification Claims

- direct boundary: preview route returns exact selected version bytes and required headers.
- important success and failure behavior: prove valid Markdown/plain text, missing version, pending/unavailable version, corrupt artifact, and unsupported media.
- final state or side effects: prove preview performs no store mutation and preserves review/evaluation projection.
- rollback, retry, duplicate, or idempotency behavior: repeated reads are idempotent; corrupt or transient failures expose retryable/action semantics.
- canonical contract and conformance proof: route response, capability field, error envelope, and headers match `docs/api.md`.
- real dependencies requiring proof: canonical CV store integrity metadata and route boundary.
- representative-operation trace mechanism: direct API requests plus representative CV list → preview → download trace.
- performance claim and threshold: preview must not buffer or transform beyond existing stored artifact serving limits.

### Acceptance Criterion: Preview preserves immutable version truth

- setup or precondition: two CV versions exist for one run/job with distinct bytes.
- action: request preview for older `version_id` after newer version exists.
- expected result: older exact bytes, ID, metadata, and review/evaluation truth are returned.
- failure condition: newer bytes or approval state appears.
- proof method: direct route test and projection comparison.
- expected evidence: byte equality, version identity equality, and unchanged store records.

### Acceptance Criterion: Preview and download share integrity truth

- setup or precondition: valid and corrupt stored artifacts exist.
- action: request preview and download for each.
- expected result: valid artifact succeeds; corrupt artifact is unavailable; download remains attachment for valid content.
- failure condition: corrupt content is served or download headers/bytes change.
- proof method: boundary tests with checksum and header assertions.
- expected evidence: response status, headers, bytes, and error envelope.

## Completion Criteria

Specification is complete when:

1. version identity, media capability, headers, errors, and side-effect boundaries are unambiguous
2. review/evaluation truth and download compatibility are explicitly preserved
3. unsupported, corrupt, pending, and missing artifact behavior is defined
4. frontend rendering and backend transport ownership are separated
5. each required outcome maps to acceptance and backend verification intent
6. Design Export and frozen UX evidence are preserved
7. implementation sequencing remains outside this specification
