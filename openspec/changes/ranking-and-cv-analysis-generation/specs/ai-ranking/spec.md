# Spec Delta

## Purpose

Defines the authoritative, auditable ranking contract used after shortlist admission and before the final CV handoff.

## ADDED Requirements

### Requirement: New-run ranking uses authoritative AI compatibility

The system SHALL use the finite AI compatibility score in the existing normalized domain `[0, 1]` as the authoritative ranking value for new runs, with the score contract version and source provenance persisted with the result. The ranking request SHALL preserve mandatory job facts, mandatory candidate facts, validated shortlist evidence, and the existing serialized request budget of at most 12,000 characters.

#### Scenario: Valid score is rankable
- **WHEN** a job receives a finite AI compatibility score under the active contract version
- **THEN** the system SHALL rank it using that score and persist the score, contract version, model/provider provenance, profile revision, and evaluation timestamp.

#### Scenario: Finite out-of-range score is invalid
- **WHEN** a provider returns a finite score below `0` or above `1`
- **THEN** the system SHALL persist an `invalid` outcome and SHALL NOT normalize or rank it as a valid score unless a future versioned contract explicitly changes the domain.

#### Scenario: Ranking input remains bounded and grounded
- **WHEN** a ranking request is built
- **THEN** it SHALL include the mandatory job and candidate facts, preserve validated shortlist evidence, and either fit within the 12,000-character serialized budget or fail explicitly with an input-budget diagnostic.

#### Scenario: Invalid or missing score is explicit
- **WHEN** the score is missing, non-finite, schema-invalid, or otherwise not rankable
- **THEN** the system SHALL persist an explicit `unscored` or `invalid` status and SHALL NOT fabricate a zero score or silently rank the job as a valid result.

#### Scenario: Retryable evaluation remains retryable
- **WHEN** evaluation fails for a retryable provider, transport, or budget reason
- **THEN** the system SHALL persist a retryable failure outcome with diagnostics and SHALL distinguish it from a valid low score and from confirmed incompatibility.

### Requirement: Ranking remains deterministic and inspectable

The system SHALL produce a deterministic order from the same job snapshot, candidate profile revision, policy/contract versions, and evaluation outputs, and SHALL retain enough data to explain each ordering decision.

#### Scenario: Equal scores use stable tie-breaking
- **WHEN** two rankable jobs have the same authoritative score
- **THEN** the system SHALL apply the documented deterministic tie-break sequence and use canonical job identity as the final fallback.

#### Scenario: Replay preserves ordering
- **WHEN** a ranking stage is resumed or replayed with the same persisted inputs and versions
- **THEN** the resulting order and decision envelope SHALL remain unchanged.

### Requirement: Ranking handoff preserves decision context

The system SHALL pass each final ranking item to CV analysis with job qualifiers, baseline rank and score, canonical source evidence, confirmed gaps, candidate profile revision, and provenance references.

#### Scenario: Complete handoff
- **WHEN** a job is selected for CV analysis and generation
- **THEN** the handoff SHALL contain all required context fields and a stable handoff fingerprint.

#### Scenario: Incomplete handoff fails closed
- **WHEN** any required qualifier, score status, profile revision, or provenance field is unavailable
- **THEN** the system SHALL mark the handoff incomplete and SHALL NOT present it as a fully grounded ranking result.

### Requirement: Historic ranking artifacts remain readable

The system SHALL continue to read historic personalized rank, residual, and related fields while preventing those fields from influencing new-run authoritative ranking decisions. New runs SHALL NOT compute or write personalized rank, preference residual, or preference-policy fields.

#### Scenario: Legacy artifact is inspected
- **WHEN** an operator opens a historic artifact containing personalized ranking fields
- **THEN** the fields SHALL remain available for inspection with their original provenance and SHALL be labeled as historic/legacy where needed.

#### Scenario: New run ignores legacy fields
- **WHEN** a new ranking run processes an input that contains historic personalized fields
- **THEN** the new decision SHALL use only the authoritative AI score contract and current tie-break policy.

#### Scenario: New run stops legacy personalization
- **WHEN** a new ranking run processes a job with preference policy or embedding data available
- **THEN** the run SHALL not activate personalized ranking computation and SHALL not emit new personalized rank, residual, or preference-policy fields.

### Requirement: Pareto promotion remains evidence-gated

The system SHALL treat Pareto promotion or strategy switching as a separately evaluated, versioned, and auditable decision; a completed evaluation SHALL NOT imply promotion eligibility unless every configured gate passes.

#### Scenario: Gate failure blocks promotion
- **WHEN** any required evidence-quality, completeness, determinism, latency, cost, or baseline comparison gate fails or is unavailable
- **THEN** the system SHALL report `promotion_eligible: false` and SHALL retain the current production strategy.

#### Scenario: Explicit override is auditable
- **WHEN** an authorized operator overrides a failed or unavailable promotion gate
- **THEN** the system SHALL persist the override actor, reason, timestamp, source evaluation, and effective strategy version.
