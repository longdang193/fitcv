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

The system SHALL persist generation status, review status, and PDF status as independent fields with the allowed values `running|completed|failed`, `optional|required`, and `pending|generated|failed` respectively.

#### Scenario: Review-required CV still attempts PDF
- **WHEN** analysis identifies unresolved factual or critical concerns
- **THEN** the system SHALL set review status to `required`, still attempt PDF generation, and SHALL not treat review-required status as a PDF success.

#### Scenario: PDF conversion fails
- **WHEN** the converter fails after the Markdown artifact is valid
- **THEN** the system SHALL set PDF status to `failed`, preserve diagnostics and the valid Markdown artifact, and SHALL classify the result as a technical failure requiring recovery or operator action.

#### Scenario: Fully valid CV completes
- **WHEN** hard factual/provenance and template checks pass and PDF generation succeeds
- **THEN** generation status SHALL be `completed`, PDF status SHALL be `generated`, and review status SHALL be `optional` unless an explicit policy requires review.

#### Scenario: Page-fit acceptance is required
- **WHEN** PDF conversion exits successfully
- **THEN** the system SHALL set PDF status to `generated` only after the existing render proof passes, including the configured one-page acceptance gate; converter exit success alone SHALL NOT complete the CV.

#### Scenario: Review blocks submission
- **WHEN** review status is `required`, regardless of PDF status
- **THEN** submission eligibility SHALL be `blocked` until an explicit review-clearance decision is recorded.

### Requirement: Generated CV uses deterministic `mycvs_v1` Markdown

The system SHALL render and validate the canonical `mycvs_v1` Markdown schema defined in `schemas/mycvs_v1.md` before invoking the external converter, including stable section ordering, links, source references, UTF-8/LF byte normalization, and checksum metadata whose scope is defined by that schema.

#### Scenario: Markdown validation passes
- **WHEN** all required fields and schema constraints are satisfied
- **THEN** the system SHALL persist the exact Markdown payload, schema version, validation result, and checksum used for conversion.

#### Scenario: Markdown validation fails
- **WHEN** required content, links, provenance, or checksum constraints fail
- **THEN** the system SHALL not invoke PDF conversion and SHALL persist a generation failure with actionable validation diagnostics.

### Requirement: Historic CV artifacts are preserved

The system SHALL preserve historic CV artifacts, their original preset/schema and status fields, and SHALL not rewrite them during migration to the new contract.

#### Scenario: Historic artifact is opened
- **WHEN** an operator inspects a CV generated under a legacy preset
- **THEN** the artifact SHALL remain readable with its original metadata and SHALL be distinguishable from a new `mycvs_v1` artifact.

### Requirement: External conversion is a pinned integration boundary

The system SHALL identify the converter version/commit, stylesheet or template revision, input checksum, and output checksum for every generated PDF.

#### Scenario: Converter provenance is complete
- **WHEN** PDF generation completes or fails
- **THEN** the artifact SHALL include converter provenance and an input checksum sufficient to reproduce or diagnose the conversion; an output checksum SHALL be present only when a complete PDF artifact exists, with absent or partial output represented explicitly.

#### Scenario: Converter is not pinned
- **WHEN** a release attempts to enable the external converter without a pinned revision and deterministic stylesheet/template
- **THEN** release readiness SHALL remain blocked and the system SHALL retain the current safe path.
