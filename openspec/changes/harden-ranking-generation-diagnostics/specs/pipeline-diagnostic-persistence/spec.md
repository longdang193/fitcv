# Spec Delta

## Purpose

Defines how pipeline diagnostics remain useful across stage boundaries and durable records without exposing private application content or storing unbounded provider and exception text.

## ADDED Requirements

### Requirement: Typed ranking diagnostics survive stage persistence
The system SHALL preserve typed ranking diagnostics from score parsing through the persisted ranking artifact and failed stage settlement.

#### Scenario: Explanatory score metadata is malformed
- **WHEN** a score remains valid but one or more explanatory metadata fields produce typed non-blocking diagnostics
- **THEN** the persisted ranking artifact SHALL include those diagnostics with their code, source, and safe facts

#### Scenario: Ranking fails during stage settlement
- **WHEN** ranking fails with a typed diagnostic that is available in the run or process-event record
- **THEN** the failed ranking stage record SHALL persist the same safe failure code and bounded diagnostic reference when available

#### Scenario: A ranking execution succeeds after an earlier failure
- **WHEN** a ranking stage execution settles successfully
- **THEN** its failure code, message, and evidence fields SHALL be empty or reset rather than retaining stale failure metadata

### Requirement: Persisted failure diagnostics are bounded and privacy-safe
The system SHALL persist failure diagnostics using bounded typed fields or a bounded reference and SHALL exclude prompts, CV or profile content, credentials, and raw provider payloads.

#### Scenario: CV generation fails with sensitive or verbose debug data
- **WHEN** a CV-generation failure includes exception text or arbitrary debug fields
- **THEN** the persisted job and stage records SHALL contain only a typed failure code, owning stage, and bounded sanitized summary or diagnostic reference

#### Scenario: Failure is persisted after an earlier diagnostic snapshot
- **WHEN** a later generation or persistence transition changes a job outcome to failure
- **THEN** the persisted result SHALL reflect the latest typed failure outcome rather than retaining stale diagnostics or omitting the failure

### Requirement: Failure stage artifacts report owned failures
The system SHALL record each CV-generation failure outcome in the CV-generation stage artifact and its output counts.

#### Scenario: A job fails during CV generation
- **WHEN** CV generation, PDF conversion, or artifact persistence fails for a job
- **THEN** the CV-generation stage artifact SHALL record the corresponding failure outcome and SHALL NOT report that work as not reached
