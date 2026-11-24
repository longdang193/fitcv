# Spec Delta

## Purpose

Defines how requirement-aware shortlist assessments represent uncertainty, preserve clause identity, and decide whether persisted coverage is safe to reuse.

## ADDED Requirements

### Requirement: Assessment completeness is scoped to the affected occurrence
The shortlist SHALL represent assessment completeness per job and requirement occurrence rather than as one run-global boolean.

#### Scenario: One job retrieval fails
- **WHEN** evidence assessment fails for one job in a multi-job evaluation pool
- **THEN** affected occurrences for that job may be `U`, while independently completed jobs retain `E` for unmatched requirements

#### Scenario: One occurrence fails inside an assessed job
- **WHEN** retrieval or validation fails for one requirement occurrence
- **THEN** that occurrence is `U` and unrelated occurrences retain their independently assessed states

### Requirement: Persisted coverage requires compatible assessment provenance
The system SHALL reuse persisted requirement coverage only when its contract, profile, evidence projection, retrieval policy, and support policy fingerprints match the current assessment inputs.

#### Scenario: Coverage fingerprint matches
- **WHEN** persisted coverage contains all required compatibility fingerprints and they match the current inputs
- **THEN** the system may reuse the coverage without recomputing it

#### Scenario: Coverage fingerprint is missing or stale
- **WHEN** persisted coverage lacks a required fingerprint or any fingerprint differs from the current inputs
- **THEN** the system recomputes coverage and records that reuse was rejected

### Requirement: Requirement occurrences remain identity-bound
Current requirement occurrence identity SHALL take precedence over wording equality when binding evidence or coverage.

#### Scenario: Two occurrences share identical wording
- **WHEN** two distinct requirement occurrences have the same source wording
- **THEN** evidence bound to one occurrence SHALL NOT satisfy the other solely because the wording matches

#### Scenario: Legacy evidence lacks occurrence identity
- **WHEN** legacy evidence has no occurrence identifier
- **THEN** wording fallback is allowed only when the wording maps unambiguously to one current occurrence, otherwise the result is unresolved

### Requirement: OR provenance follows the satisfying alternative
For an OR compound requirement, state, evidence, contradiction, and provenance SHALL be derived from the alternative or alternatives that establish the selected state rather than from unused weaker alternatives.

#### Scenario: One OR branch is strongly supported
- **WHEN** one branch is supported with strong provenance and another branch is unverified
- **THEN** the compound requirement is supported and its provenance reflects the satisfying branch rather than the unverified branch

#### Scenario: No OR branch is supported
- **WHEN** all OR branches are unresolved or unverified
- **THEN** the compound requirement remains unresolved or not evidenced according to the current support policy and preserves the relevant branch diagnostics

### Requirement: Assessment and display evidence have separate limits
The evidence used to assess requirement coverage SHALL not be limited to the compact explanation set persisted for display or handoff.

#### Scenario: More candidates are needed for assessment
- **WHEN** the compact explanation limit is smaller than the evidence candidates required to determine coverage
- **THEN** assessment may inspect the broader candidate pool while persisted display evidence remains bounded and attributable

#### Scenario: Compact evidence is persisted
- **WHEN** a shortlist decision is persisted for downstream stages
- **THEN** it retains selected evidence and complete evidence identifiers or references without duplicating an unbounded candidate pool
