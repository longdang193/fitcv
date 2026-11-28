# Spec Delta

## Purpose

Defines trustworthy continuation for partial ranking and technical failures. It prevents counters or stale checkpoints from authorizing a resume that skips failed work or lacks a validated ranking-to-CV handoff.

## ADDED Requirements

### Requirement: Partial ranking continuation requires an independently valid handoff
The system SHALL allow a partial ranking to continue only when no independent technical failure is reported and a validated ranking-to-CV handoff accounts for the ranked output.

#### Scenario: Mixed valid and invalid score outcomes have a valid handoff
- **WHEN** ranking is partial, at least one ranked item exists, no persistence or other technical failure is reported, and the handoff validates for those items
- **THEN** downstream CV stages may continue using only the validated handoff items

#### Scenario: Partial ranking reports a technical failure
- **WHEN** ranking is partial with ranked items and reports persistence failure or another explicit technical failure
- **THEN** the run is terminally classified at ranking and SHALL NOT be resumable past that failure

#### Scenario: Ranked count exists without a valid handoff
- **WHEN** ranking reports a positive ranked count but its handoff is missing, incomplete, invalid, or inconsistent with the ranked output
- **THEN** the run SHALL fail closed at the ranking-to-CV boundary and SHALL NOT expose a continuation checkpoint that skips the invalid handoff

### Requirement: Failure checkpoints reflect successful work and actual retry boundary
The system SHALL persist completed stages only through the successful prefix before the failing stage and set the next stage to the failing stage.

#### Scenario: CV generation fails after CV analysis succeeds
- **WHEN** a terminal technical failure is owned by CV generation
- **THEN** the checkpoint SHALL record CV analysis as completed and CV generation as the next stage

#### Scenario: CV analysis fails after ranking succeeds
- **WHEN** a terminal technical failure is owned by CV analysis
- **THEN** the checkpoint SHALL record ranking as the last completed stage and CV analysis as the next stage

#### Scenario: An upstream stage fails
- **WHEN** a terminal technical failure is owned by an earlier pipeline stage
- **THEN** the checkpoint SHALL not mark the failing stage or any later stage complete and SHALL retry from that failing stage
