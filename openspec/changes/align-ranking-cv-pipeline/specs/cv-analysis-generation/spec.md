# Spec Delta

## Purpose

Provides a single grounded Stage 7 workflow that turns a ranked job into a truthful, schema-valid, recruiter-usable CV while keeping review status, PDF production, persistence, and submission readiness distinct.

## ADDED Requirements

### Requirement: Stage 7 uses a fixed-order orchestrator
The system SHALL process each Final Top 15 job in the order evidence planning, CREATE, ADJUST, validation, targeted retry or fallback, review resolution, Markdown rendering, PDF generation, and persistence.

#### Scenario: Stage begins from a ranked job
- **WHEN** Stage 7 receives a valid Stage 6 handoff
- **THEN** it executes the defined order and records each stage state rather than bypassing generation because a gap exists.

### Requirement: Evidence planning uses canonical sources
Evidence planning SHALL map JD priorities to source-backed candidate evidence and SHALL retain unresolved gaps without converting missing evidence into a factual claim.

#### Scenario: Requirement has no verified support
- **WHEN** no canonical source supports a JD requirement
- **THEN** the plan records the gap and excludes unsupported duration, qualification, or achievement claims from generated content.

### Requirement: CREATE uses the fixed myCVs template
The CREATE step SHALL generate content using the committed myCVs template `templates/cv_template.md` and schema identifier `cv_doc_v1` for new Stage 7 runs.

#### Scenario: Legacy renderer is configured
- **WHEN** a new run loads a legacy or non-myCVs renderer configuration
- **THEN** the canonical Stage 7 policy selects the fixed myCVs template, while historic artifacts remain readable.

### Requirement: ADJUST is an explicit quality step
The ADJUST step SHALL improve ATS terminology, role-specific achievements, impact, clarity, and approximately 580-word page-fit content as a quality target without adding unsupported facts.

#### Scenario: Draft is factual but generic
- **WHEN** validation finds weak recruiter quality but no factual violation
- **THEN** ADJUST produces a targeted improvement and sends the result back through all validation checks.

### Requirement: Validation has three dimensions
The system SHALL validate factual integrity and provenance as hard constraints, exact myCVs Markdown schema as a hard constraint, and ATS/recruiter quality as an optimization objective.

#### Scenario: Quality conflicts with factual integrity
- **WHEN** a proposed improvement would improve keywords but require an unsupported claim or break schema
- **THEN** the improvement is rejected or revised and the hard constraints remain satisfied.

### Requirement: Retries end in a grounded fallback
The system SHALL use a bounded retry budget for targeted improvements and SHALL produce a safe grounded fallback that preserves unresolved gaps when the budget is exhausted, then re-run final hard-constraint checks.

#### Scenario: Retry budget is exhausted
- **WHEN** targeted corrections cannot satisfy all non-hard quality checks within the retry budget
- **THEN** the system emits the safest grounded content only after factual/provenance and exact-schema checks pass; unresolved quality concerns continue to review and PDF states, while an unsupported claim or hard violation becomes a technical validation failure.

### Requirement: CV concern taxonomy is explicit
The system SHALL distinguish unsupported claims or hard provenance violations, grounded omissions or unresolved JD gaps, and factual uncertainty that requires human review.

#### Scenario: Grounded gap remains optional review
- **WHEN** a requirement lacks verified support but the CV omits the claim and remains grounded
- **THEN** the artifact records an unresolved JD gap and may use optional review without blocking PDF generation.

#### Scenario: Unsupported claim is never accepted
- **WHEN** generated content asserts a fact without canonical support or violates provenance constraints
- **THEN** the claim is removed or corrected, and if no grounded artifact can be produced the system records technical validation failure rather than treating human review as an override.

#### Scenario: Uncertain fact requires mandatory review
- **WHEN** a fact is plausible but not sufficiently verified and is retained for human adjudication without being treated as established
- **THEN** the artifact enters mandatory review and submission remains blocked until an attributable decision is recorded.

### Requirement: Review state is separate from technical state
The system SHALL distinguish optional review, mandatory review, validation failure, generation failure, persistence failure, and successful technical completion.

#### Scenario: Material concern remains
- **WHEN** factual or critical concerns remain after fallback
- **THEN** the CV receives a review-required state but is still eligible for PDF generation; submission remains blocked until mandatory review is complete.

### Requirement: Exact Markdown is rendered and validated
The system SHALL render deterministic myCVs Markdown using `templates/cv_template.md` and `cv_doc_v1` as the committed versioned authority and validate its required sections, links, checksums, and configured page-fit measurement before PDF conversion.

#### Scenario: Markdown contract is invalid
- **WHEN** the rendered document has an invalid schema, link, checksum, or page-fit proof required by the authoritative template policy
- **THEN** PDF conversion is not treated as successful and the artifact records the validation failure.

### Requirement: Existing converter generates PDFs for both review states
The system SHALL run the existing myCVs converter for both optional-review and mandatory-review CVs and SHALL persist a PDF only after post-conversion integrity, render, schema/link/checksum, and configured page-fit acceptance checks succeed.

#### Scenario: Mandatory review is required
- **WHEN** a review-required CV has valid Markdown
- **THEN** the existing converter produces and persists a PDF while the review flag continues to gate submission.

#### Scenario: Converter exit is not enough
- **WHEN** the converter exits successfully but the persisted PDF is corrupt, unrenderable, mismatched, or fails required acceptance checks
- **THEN** the PDF state is technical failure and the artifact is not reported as a verified PDF.

### Requirement: PDF failure is a technical failure
A converter failure SHALL produce a bounded technical recovery or explicit PDF failure state and SHALL NOT be represented as review-required success.

#### Scenario: Converter fails
- **WHEN** PDF generation fails after permitted recovery attempts
- **THEN** the system records technical failure, does not claim a valid PDF, and does not convert the failure into a human-review status.

### Requirement: Persistence and submission states are explicit
The system SHALL save the PDF and review metadata separately from submission permission and SHALL expose submission as permitted only when the required review and technical checks are complete.

#### Scenario: Review remains outstanding
- **WHEN** a PDF is persisted but mandatory review is incomplete
- **THEN** the artifact remains available for inspection and submission is blocked.

### Requirement: Mandatory review is revision-bound
Mandatory review SHALL use pending, approved, and rejected states, and approval SHALL identify the exact CV/PDF artifact revision it covers.

#### Scenario: Stale approval is invalidated
- **WHEN** content or the PDF changes after approval
- **THEN** the approval is invalidated, the review returns to pending, and submission remains blocked until the new revision is approved.
