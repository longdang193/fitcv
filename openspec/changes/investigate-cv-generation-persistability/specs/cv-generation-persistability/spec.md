# CV Generation Persistability Specification

## ADDED Requirements

### Requirement: A non-persistable CV outcome is traceable
The system SHALL preserve enough bounded evidence to identify the first rejecting generation, validation, conversion, or persistence boundary.

#### Scenario: Representative generation fails before artifact persistence
- **WHEN** a controlled CV-generation attempt produces no persisted CV artifact
- **THEN** the outcome records its owning boundary, stable typed diagnostic, retryability or terminality, and a bounded safe reference to the relevant attempt

#### Scenario: Multiple boundaries report failure
- **WHEN** more than one downstream boundary observes the same failed attempt
- **THEN** the earliest authoritative failure remains primary and later persistence or projection failures remain secondary context

### Requirement: Investigation does not weaken acceptance safeguards
The system SHALL keep existing content, evidence, artifact, and privacy gates unchanged while the rejecting condition is investigated.

#### Scenario: Generated content is invalid
- **WHEN** the representative output fails an existing validation or artifact-acceptance rule
- **THEN** the attempt is classified as a typed rejection and no invalid output is promoted to an accepted CV artifact

#### Scenario: Generated content is valid but persistence fails
- **WHEN** the representative output satisfies existing acceptance rules but persistence fails
- **THEN** the valid outcome remains distinguishable from validation failure and the persistence failure is recorded without discarding the valid evidence

### Requirement: Investigation evidence is bounded and reproducible
The system SHALL support a local or synthetic reproduction that can be rerun without requiring a broad real-data batch or unbounded private payload capture.

#### Scenario: A representative failure is reproduced
- **WHEN** the same controlled inputs are replayed through generation, validation, conversion, and persistence
- **THEN** the same owning boundary and typed outcome are observed, or the investigation records the changed input or environment that explains the difference

#### Scenario: No representative failure can be reproduced
- **WHEN** a controlled replay does not reproduce the reported non-persistable outcome
- **THEN** the investigation records the boundary coverage and stops without weakening gates, increasing retries, switching providers, or launching a replacement real-data batch
