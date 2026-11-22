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
The CREATE step SHALL generate content using the committed myCVs template and its exact document schema for new Stage 7 runs.

#### Scenario: Legacy renderer is configured
- **WHEN** a new run loads a legacy or non-myCVs renderer configuration
- **THEN** the canonical Stage 7 policy selects the fixed myCVs template, while historic artifacts remain readable.

### Requirement: ADJUST is an explicit quality step
The ADJUST step SHALL improve ATS terminology, role-specific achievements, impact, clarity, and approximately 580-word page-fit content without adding unsupported facts.

#### Scenario: Draft is factual but generic
- **WHEN** validation finds weak recruiter quality but no factual violation
- **THEN** ADJUST produces a targeted improvement and sends the result back through all validation checks.

### Requirement: Validation has three dimensions
The system SHALL validate factual integrity and provenance as hard constraints, exact myCVs Markdown schema as a hard constraint, and ATS/recruiter quality as an optimization objective.

#### Scenario: Quality conflicts with factual integrity
- **WHEN** a proposed improvement would improve keywords but require an unsupported claim or break schema
- **THEN** the improvement is rejected or revised and the hard constraints remain satisfied.

### Requirement: Retries end in a grounded fallback
The system SHALL use a bounded retry budget for targeted improvements and SHALL produce a safe grounded fallback that preserves unresolved gaps when the budget is exhausted.

#### Scenario: Retry budget is exhausted
- **WHEN** targeted corrections cannot satisfy all non-hard quality checks within the retry budget
- **THEN** the system emits the safest grounded content, records the unresolved concerns, and continues to review and PDF states.

### Requirement: Review state is separate from technical state
The system SHALL distinguish optional review, mandatory review, validation failure, generation failure, persistence failure, and successful technical completion.

#### Scenario: Material concern remains
- **WHEN** factual or critical concerns remain after fallback
- **THEN** the CV receives a review-required state but is still eligible for PDF generation; submission remains blocked until mandatory review is complete.

### Requirement: Exact Markdown is rendered and validated
The system SHALL render deterministic myCVs Markdown and validate its schema, links, checksums, and page-fit inputs before PDF conversion.

#### Scenario: Markdown contract is invalid
- **WHEN** the rendered document has an invalid schema, link, checksum, or page-fit proof
- **THEN** PDF conversion is not treated as successful and the artifact records the validation failure.

### Requirement: Existing converter generates PDFs for both review states
The system SHALL run the existing myCVs converter for both optional-review and mandatory-review CVs and SHALL persist a verified PDF when conversion succeeds.

#### Scenario: Mandatory review is required
- **WHEN** a review-required CV has valid Markdown
- **THEN** the existing converter produces and persists a PDF while the review flag continues to gate submission.

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
