# Spec Delta

## Purpose

Defines the safe persistence and projection rules for technical diagnostics and lifecycle outcomes across ranking, CV generation, PDF conversion, and finalization.

## ADDED Requirements

### Requirement: Persisted diagnostics are bounded and privacy-safe
The system SHALL persist technical diagnostics using bounded, allowlisted typed fields or a bounded reference and SHALL exclude prompts, CV/profile content, credentials, raw provider payloads, raw exception text, and arbitrary nested debug fields.

#### Scenario: Verbose or sensitive generation failure
- **WHEN** a generation failure contains verbose exception text or unexpected nested debug data
- **THEN** persisted job and stage records SHALL contain only the stable failure code, owning stage, safe status, bounded summary or reference, and bounded facts permitted by the diagnostic contract

#### Scenario: Quarantine persistence also fails
- **WHEN** persistence of a quarantine or failure record raises an exception
- **THEN** compatibility/debug fields SHALL use the normalized safe diagnostic representation and SHALL NOT retain the raw exception string

### Requirement: Typed diagnostics preserve severity and valid score outcomes
The system SHALL map supported legacy failure outcomes to registered typed diagnostic codes, bound the total diagnostic collection and fact payload, and preserve a finite valid score when only explanatory metadata is malformed.

#### Scenario: Blocking and nonblocking diagnostics coexist
- **WHEN** a result contains both blocking technical diagnostics and nonblocking warnings
- **THEN** a blocking diagnostic SHALL be selected as the primary failure, with warnings retained as secondary context

#### Scenario: Explanatory metadata is malformed
- **WHEN** a finite score is valid but explanatory fields are malformed
- **THEN** the score SHALL remain valid and malformed metadata SHALL produce only bounded nonblocking diagnostic context

### Requirement: Lifecycle projections reflect the resolved outcome
The system SHALL project the resolved lifecycle status consistently across job records, stage artifacts, debug payloads, and PDF outcomes.

#### Scenario: Generation or PDF conversion fails
- **WHEN** CV generation or PDF conversion fails
- **THEN** the CV-generation projection SHALL report the corresponding failed outcome and SHALL NOT report success or not-reached for the attempted work

#### Scenario: Valid Markdown survives PDF failure
- **WHEN** Markdown generation succeeds but PDF conversion fails
- **THEN** the Markdown artifact MAY remain available for review while the PDF outcome is recorded independently as failed

### Requirement: Finalization cannot replace the primary failure
The system SHALL preserve the first authoritative technical failure and record later finalization or projection errors as secondary outcomes.

#### Scenario: Late persistence failure follows generation failure
- **WHEN** a later artifact or projection write fails after a generation failure is already recorded
- **THEN** the persisted lifecycle SHALL retain the generation failure as primary and expose the later persistence error separately
