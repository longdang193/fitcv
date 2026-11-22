# Spec Delta

## Purpose

Defines grounded CV analysis and deterministic CV generation behavior for the final ranked jobs, including review and PDF outcomes.

## ADDED Requirements

### Requirement: CV analysis is grounded in canonical evidence and job requirements

The system SHALL analyze a ranked job using the canonical candidate profile, attributable evidence, job-specific qualifiers, and the ranking handoff provenance; unsupported claims SHALL be identified rather than invented.

#### Scenario: Grounded analysis succeeds
- **WHEN** the handoff contains valid profile, job, evidence, and provenance inputs
- **THEN** the analysis SHALL produce strengths, gaps, unresolved uncertainties, and factual-risk findings tied to source evidence or explicit job requirements.

#### Scenario: Missing evidence remains unknown
- **WHEN** a requirement has no attributable evidence
- **THEN** the analysis SHALL represent it as unknown/not evidenced and SHALL NOT infer absence or add an unsupported claim.

### Requirement: CV adjustment is bounded and revalidated

The system SHALL perform the Stage 7 sequence in order: evidence planning, initial CV creation using the fixed template, initial ATS/achievement/impact optimization, and unified validation. It SHALL allow at most one bounded targeted-adjustment pass for material concerns, followed by revalidation of all three validation dimensions: facts/provenance, `mycvs_v1` schema/template, and ATS/recruiter quality.

#### Scenario: Material concerns are corrected once
- **WHEN** material concerns remain after initial analysis and the retry budget permits adjustment
- **THEN** the system SHALL apply one targeted correction pass and rerun the defined validation checks.

#### Scenario: Initial creation follows the fixed sequence
- **WHEN** a valid ranking handoff enters CV generation
- **THEN** the system SHALL plan evidence, create the CV with the fixed template, apply the initial ATS/achievement/impact optimization, and run the unified validation before deciding whether targeted correction is needed.

#### Scenario: Budget is exhausted
- **WHEN** the adjustment budget is exhausted or the correction cannot be applied safely
- **THEN** the system SHALL stop adjusting, preserve the unresolved concerns, and continue only with the appropriate review status.

#### Scenario: Correction revalidates quality
- **WHEN** a targeted correction pass completes
- **THEN** the system SHALL rerun facts/provenance, schema/template, and ATS/recruiter-quality checks; quality remains an optimization signal unless policy marks it material.

### Requirement: CV status dimensions are independent

The system SHALL persist generation, review, PDF, and submission-clearance outcomes independently without replacing existing persisted/public lifecycle fields. A new additive `pdf_status` MAY use `pending|generated|failed`, and a new additive submission-clearance field MAY use `blocked|eligible`.

#### Scenario: Review-required CV still attempts PDF
- **WHEN** analysis identifies unresolved factual or critical concerns
- **THEN** the system SHALL set `generation_status=review_required` and `review_state=manual_required` (or the applicable existing `stretch` policy state), still attempt PDF generation, and SHALL not treat review-required status as a PDF success.

#### Scenario: Existing status values remain readable
- **WHEN** a reader loads a historical or current CV record
- **THEN** `generation_status` SHALL accept `pending|running|generated|review_required|validation_failed|generation_failed|persistence_failed|cancelled`, and `review_state` SHALL accept `none|stretch|manual_required|approved|rejected`. A new read model MAY map `generated` to `completed` and a specific failure to `failed`, but storage and public compatibility values SHALL not be renamed.

#### Scenario: PDF conversion fails
- **WHEN** the converter fails after the Markdown artifact is valid
- **THEN** the system SHALL set additive `pdf_status=failed`, preserve diagnostics and the valid Markdown artifact, and SHALL classify the result as a technical failure requiring recovery or operator action without rewriting the generation lifecycle state into a generic value.

#### Scenario: Fully valid CV completes
- **WHEN** hard factual/provenance and template checks pass and PDF generation succeeds
- **THEN** `generation_status` SHALL be `generated`, `pdf_status` SHALL be `generated`, and `review_state` SHALL be `none` unless policy requires `stretch` or `manual_required` review. An explicit clearance changes `manual_required` or `stretch` to `approved`; rejection changes it to `rejected`.

#### Scenario: Page-fit acceptance is required
- **WHEN** PDF conversion exits successfully
- **THEN** the system SHALL set PDF status to `generated` only after the existing render proof passes, including the configured one-page acceptance gate; converter exit success alone SHALL NOT complete the CV.

#### Scenario: Review blocks submission
- **WHEN** review status is `required`, regardless of PDF status
- **THEN** submission clearance SHALL be `blocked` until an explicit review event records `review_state=approved`; `rejected` remains blocked. A `none` review state is eligible only when generation and PDF acceptance also pass.

### Requirement: Generated CV uses deterministic `mycvs_v1` Markdown

The system SHALL render and validate the canonical `mycvs_v1` Markdown schema defined in `schemas/mycvs_v1.md` before invoking the external converter, including stable section ordering, links, source references, UTF-8/LF byte normalization, and checksum metadata whose scope is defined by that schema.

#### Scenario: Markdown validation passes
- **WHEN** all required fields and schema constraints are satisfied
- **THEN** the system SHALL persist the exact Markdown payload, schema version, validation result, and checksum used for conversion.

#### Scenario: Markdown validation fails
- **WHEN** required content, links, provenance, or checksum constraints fail
- **THEN** the system SHALL not invoke PDF conversion and SHALL persist a generation failure with actionable validation diagnostics.

### Requirement: Accepted PDF artifacts remain durable and downloadable

The system SHALL persist a complete accepted PDF artifact and its media type, length, and checksum separately from the Markdown artifact, and SHALL expose the persisted bytes through the existing CV artifact boundary without accepting missing or checksum-mismatched PDF content.

#### Scenario: Accepted PDF survives the generation boundary
- **WHEN** Markdown validation and one-page render proof pass
- **THEN** the worker SHALL persist the PDF bytes and matching checksum, and a PDF download SHALL return the same bytes with `application/pdf` media type.

#### Scenario: PDF persistence is incomplete
- **WHEN** render proof passes but the PDF bytes are absent or their checksum does not match
- **THEN** `pdf_status` SHALL remain failed and submission clearance SHALL remain blocked.

### Requirement: Historic CV artifacts are preserved

The system SHALL preserve historic CV artifacts, their original preset/schema and status fields, and SHALL not rewrite them during migration to the new contract.

#### Scenario: Historic artifact is opened
- **WHEN** an operator inspects a CV generated under a legacy preset
- **THEN** the artifact SHALL remain readable with its original metadata and SHALL be distinguishable from a new `mycvs_v1` artifact.

### Requirement: External conversion is a pinned integration boundary

The system SHALL identify the converter version/commit, stylesheet or template revision, input checksum, and output checksum for every generated PDF, and SHALL bind external conversion to the existing render-proof contract.

Before an external `myCVs` PDF is accepted, its adapter SHALL emit the existing render-proof fields and the registered `renderer_contract_version=mycvs_external_render_v1`. Converter commit and stylesheet/template revision SHALL be recorded separately as provenance.

#### Scenario: Converter provenance is complete
- **WHEN** PDF generation completes or fails
- **THEN** the artifact SHALL include converter provenance, render-proof fields sufficient to reproduce or diagnose the attempt, and an input checksum; the render proof SHALL be verified only when all required identity fields pass, and an output checksum SHALL be present only when a complete PDF artifact exists.

#### Scenario: External renderer contract is recognized
- **WHEN** an external adapter returns a candidate PDF
- **THEN** the existing final-artifact predicate SHALL recognize `mycvs_external_render_v1` only when `render_status=pass`, `page_count=1`, `page_fit_status=pass`, valid artifact/content/template checksums, and a render-config fingerprint are present; an unrecognized renderer contract SHALL remain unaccepted.

#### Scenario: Converter is not pinned
- **WHEN** a release attempts to enable the external converter without a pinned revision and deterministic stylesheet/template
- **THEN** release readiness SHALL remain blocked and the system SHALL retain the current safe path.
