# Spec Delta

## Purpose

Defines the authoritative boundary between a valid Final Top 15 handoff, Stage 7 fit diagnostics, technical failures, resume behavior, and eligibility to produce grounded CV artifacts.

## ADDED Requirements

### Requirement: Fit diagnostics do not block valid Final Top 15 generation
For a valid Final Top 15 handoff, fit labels, unresolved JD requirements, professional-experience gaps, and requirement coverage states SHALL be diagnostics or review inputs and SHALL NOT cause a secondary fit rejection.

#### Scenario: Final Top 15 contains an unresolved fit gap
- **WHEN** Stage 7 receives a valid handoff with a skipped fit classification or an unverified professional-experience requirement
- **THEN** Stage 7 attempts grounded analysis and generation, records the gap, and does not emit a fit-gate terminal status

#### Scenario: Grounded content omits an unsupported requirement
- **WHEN** a JD requirement has no verified candidate evidence and generated content does not claim it
- **THEN** Markdown and PDF generation remain eligible while review or submission clearance may remain blocked

### Requirement: Stage 6 handoff validity is authoritative
Stage 7 SHALL accept a handoff only when the versioned ranking-to-CV payload, canonical job identity, JD reference, Final Top 15 rank, finite score/status, disposition, profile revision, ranking versions, evidence identifiers, provenance, and handoff fingerprint are present and mutually consistent.

#### Scenario: Valid admitted handoff is received
- **WHEN** the canonical payload and fingerprint validate and identify an admitted Final Top 15 row
- **THEN** Stage 7 treats the handoff as the authoritative input and proceeds to fit diagnostics and grounded generation

#### Scenario: Handoff identity or provenance conflicts
- **WHEN** the job identity, JD reference, profile revision, rank, disposition, contract version, evidence provenance, or fingerprint conflicts with the processed job or profile
- **THEN** Stage 7 rejects the handoff as a technical contract failure and does not reinterpret the conflict as a fit result

### Requirement: Invalid handoffs have a canonical technical status
A missing, invalid, or inconsistent Stage 6 handoff SHALL produce `handoff_contract_failed` with a failure code, terminal flag, retry eligibility, checkpoint reference, worker projection, and job-scoped failure identity.

#### Scenario: Missing predecessor handoff
- **WHEN** a direct or resumed invocation cannot establish a required Final Top 15 handoff
- **THEN** the current attempt is terminal with `handoff_contract_failed`, retry is allowed only when the upstream predecessor can produce the missing handoff, and the failure is not emitted as `skipped_fit_gate` or `blocked_by_reranker_fit`

#### Scenario: Corrected upstream handoff becomes available
- **WHEN** an upstream producer issues a new valid handoff with a changed handoff fingerprint
- **THEN** the prior technical failure remains historical and a new attempt may retry from the handoff boundary with the new scope and provenance

### Requirement: Technical and review states remain separate
A generated artifact SHALL expose technical completion, review state, PDF state, persistence state, and submission clearance independently.

#### Scenario: Material uncertainty remains after grounded generation
- **WHEN** grounded content is produced but a material fact remains uncertain
- **THEN** the artifact records mandatory review and blocks submission while retaining the generated artifact and its PDF state

#### Scenario: Technical validation fails
- **WHEN** no grounded artifact can satisfy hard factual or schema constraints
- **THEN** the system records technical validation failure rather than treating review approval as a successful override

### Requirement: Experience bounds use one canonical nullable contract
Experience bounds SHALL be normalized before requirement construction: missing, null, blank, zero, negative, non-numeric, non-finite, and inverted values SHALL not create synthetic requirements, while valid positive bounds SHALL remain available to downstream coverage.

#### Scenario: Unspecified or invalid bound is supplied
- **WHEN** a bound is missing, null, blank, zero, negative, non-numeric, NaN, or infinite
- **THEN** its canonical value is null and a diagnostic identifies the normalization outcome without blocking an otherwise valid job

#### Scenario: Bounds are inverted
- **WHEN** both positive bounds are present but the minimum exceeds the maximum
- **THEN** both canonical bounds are null, an `inverted_range` diagnostic is recorded, and no synthetic range requirement is created

#### Scenario: Positive bound is supplied
- **WHEN** a finite positive minimum or maximum is present
- **THEN** the canonical nullable contract preserves that bound and downstream coverage may represent the corresponding requirement

### Requirement: Legacy fit-gate records are not current decisions
The system SHALL keep historical `skipped_fit_gate` and `blocked_by_reranker_fit` records readable, but SHALL NOT reuse them as the current Stage 7 routing decision for a valid current handoff.

#### Scenario: Cached fit-gate record matches an old input fingerprint
- **WHEN** a reusable record has a historical fit-gate status and a valid current handoff exists
- **THEN** the system recomputes current routing under the active policy instead of returning the cached fit-gate decision

#### Scenario: Historical record is inspected
- **WHEN** an operator or migration reader loads a legacy fit-gate record
- **THEN** the original status and provenance remain inspectable without being emitted as a new valid Final Top 15 decision

### Requirement: Managed candidate provenance gates Stage 7 analysis reuse
The canonical Stage 7 analysis fingerprint SHALL include managed candidate profile identity, revision, and canonical checksum, and records missing any of them SHALL not authorize new cache reuse.

#### Scenario: Managed provenance matches
- **WHEN** the current managed candidate profile identity, revision, checksum, contract, evidence, and other analysis inputs match a cached analysis
- **THEN** Stage 7 reuses the cached analysis with the existing exact-match status

#### Scenario: Managed revision changes without a checksum change
- **WHEN** only the managed candidate profile revision changes
- **THEN** Stage 7 rejects the cached analysis with a deterministic revision-change reason and recomputes analysis

#### Scenario: Historical analysis lacks managed provenance
- **WHEN** a readable historical analysis record has no managed candidate profile identity, revision, or checksum
- **THEN** Stage 7 preserves the record for inspection but marks reuse ineligible and recomputes from the analysis boundary

### Requirement: Resume ownership and invalidation are explicit
A resumed decision SHALL be owned by the active contract; a checkpoint is resumable only when its handoff, contract, policy, profile, evidence, and predecessor state remain compatible, otherwise the system SHALL restart at the first affected boundary.

#### Scenario: Compatible checkpoint resumes
- **WHEN** the handoff fingerprint and all required contract, policy, profile, evidence, and predecessor revisions match
- **THEN** the system resumes from the stored checkpoint without silently changing the decision owner

#### Scenario: Upstream input changes
- **WHEN** the profile revision, JD reference, requirement contract, evidence revision, or shortlist coverage can change admission or ranking inputs
- **THEN** the system invalidates dependent Stage 6 handoff and Stage 7 checkpoints and restarts at the first affected upstream boundary

#### Scenario: Worker and checkpoint state conflict
- **WHEN** persisted worker projection and checkpoint state disagree about terminality or completion
- **THEN** the system stops with a technical resume failure and does not guess a later-stage continuation

### Requirement: PDF acceptance is required for completed behavior
A PDF SHALL be considered verified only after post-conversion integrity, renderability, schema/link/checksum, and configured page-fit checks pass for the affected review path.

#### Scenario: Optional-review artifact is accepted
- **WHEN** grounded Markdown has optional review and the existing converter completes
- **THEN** targeted acceptance verifies the persisted PDF and its required integrity checks before the change is considered complete

#### Scenario: Mandatory-review artifact is accepted
- **WHEN** grounded Markdown has mandatory review and the existing converter completes
- **THEN** targeted acceptance verifies the persisted PDF while mandatory review continues to block submission

#### Scenario: Converter exit is not enough
- **WHEN** the converter exits successfully but the PDF is corrupt, unrenderable, mismatched, or fails a required check
- **THEN** the PDF state is technical failure and the artifact is not reported as a verified PDF
