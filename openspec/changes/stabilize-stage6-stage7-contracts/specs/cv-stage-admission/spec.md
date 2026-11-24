# Spec Delta

## Purpose

Defines the boundary between valid Final Top 15 handoffs, Stage 7 fit diagnostics, technical contract failures, and eligibility to produce a grounded CV artifact.

## ADDED Requirements

### Requirement: Fit diagnostics do not block valid Final Top 15 generation
For a valid Final Top 15 handoff, fit labels, unresolved JD requirements, professional-experience gaps, and requirement coverage states SHALL be carried as diagnostics or review inputs and SHALL NOT prevent grounded CV generation.

#### Scenario: Final Top 15 contains an unresolved fit gap
- **WHEN** Stage 7 receives a valid handoff with `fit_classification` equal to `skip` or an unverified professional-experience requirement
- **THEN** Stage 7 attempts grounded analysis and generation, records the gap, and does not emit a fit-gate terminal status

#### Scenario: Grounded content omits an unsupported requirement
- **WHEN** a JD requirement has no verified candidate evidence and the generated content does not claim it
- **THEN** the artifact may require review or submission clearance, but Markdown and PDF generation remain eligible

### Requirement: Invalid handoffs fail as technical contract errors
Stage 7 SHALL distinguish an invalid, missing, or inconsistent Stage 6 handoff from a fit rejection.

#### Scenario: Handoff identity or rank is invalid
- **WHEN** the job URL, profile revision, admission state, JD reference, score, or Final Top 15 rank fails the handoff contract
- **THEN** Stage 7 records a technical handoff-contract failure and SHALL NOT emit `skipped_fit_gate` or `blocked_by_reranker_fit`

#### Scenario: Legacy direct entry lacks a valid handoff
- **WHEN** a direct or resumed invocation cannot establish the required Final Top 15 provenance
- **THEN** the invocation is rejected as an invalid handoff rather than changing the meaning of fit diagnostics

### Requirement: Experience bounds use one canonical nullable contract
Experience bounds SHALL be normalized before downstream requirement construction; a zero bound that represents an unspecified enrichment default SHALL become null and SHALL not create a synthetic requirement.

#### Scenario: Zero is the unspecified minimum
- **WHEN** enrichment supplies `years_experience_min = 0` without an explicit source assertion
- **THEN** downstream coverage contains no minimum-years requirement

#### Scenario: Zero is the unspecified maximum
- **WHEN** enrichment supplies `years_experience_max = 0` without an explicit source assertion
- **THEN** downstream coverage contains no maximum-years requirement

#### Scenario: A positive bound is sourced
- **WHEN** enrichment supplies a positive minimum or maximum bound
- **THEN** the canonical nullable contract preserves that bound and downstream coverage may represent the corresponding requirement

### Requirement: Fit-gate failures are not reusable current decisions
The system SHALL NOT reuse a persisted fit-gate terminal record as the current Stage 7 routing decision; historical fit-gate records SHALL remain readable for audit and migration.

#### Scenario: Cached fit-gate record matches the input fingerprint
- **WHEN** a reusable record has status `skipped_fit_gate` or `blocked_by_reranker_fit`
- **THEN** the system recomputes current routing under the active Stage 7 policy instead of returning the cached terminal decision

#### Scenario: Historical record is inspected
- **WHEN** an operator or migration reader loads a legacy fit-gate record
- **THEN** the record remains inspectable with its original status and provenance, without being emitted as a new valid Final Top 15 decision

### Requirement: Technical, review, and submission states remain separate
A generated artifact SHALL expose technical completion, review state, PDF state, and submission clearance independently.

#### Scenario: Material uncertainty remains after grounded generation
- **WHEN** grounded content is produced but a material fact remains uncertain
- **THEN** the system records mandatory review and blocks submission while retaining the generated artifact and its PDF state

#### Scenario: Technical validation fails
- **WHEN** no grounded artifact can satisfy hard factual or schema constraints
- **THEN** the system records technical validation failure rather than treating review as a successful override
