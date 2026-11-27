# Spec Delta

## Purpose

Defines the conditions under which ranking results may authorize CV-stage continuation and how technical failures remain aligned with durable retry state.

## ADDED Requirements

### Requirement: Explicit technical failures take precedence over partial continuation
The system SHALL classify an explicit technical failure reported by the ranking stage before applying any recoverable partial-ranking exception.

#### Scenario: Partial ranking has a valid handoff but reports persistence failure
- **WHEN** ranking is partial, the handoff is structurally valid, ranked output is nonempty, and the ranking stage reports an explicit persistence or other technical failure
- **THEN** the run SHALL be terminally classified at ranking and SHALL NOT expose a continuation checkpoint

#### Scenario: Partial ranking contains only mixed valid and invalid outcomes
- **WHEN** ranking is partial, no independent technical failure is reported, and the handoff validates for the usable ranked items
- **THEN** downstream CV stages MAY continue using only that validated handoff

### Requirement: Continuation requires an authoritative ranking-to-CV handoff
The system SHALL validate the ranking-to-CV handoff at the continuation boundary and SHALL confirm its cardinality, schema, fingerprints, uniqueness, and correspondence to the authoritative selected ranking identities.

#### Scenario: Positive ranked count has no usable handoff
- **WHEN** a ranking summary reports a positive count but the handoff is absent, incomplete, malformed, duplicated, fingerprint-invalid, or identity-mismatched
- **THEN** the run SHALL fail closed at the ranking-to-CV boundary and SHALL NOT expose a resumable checkpoint

#### Scenario: Handoff and selected ranking identities correspond
- **WHEN** every continued item has a valid handoff and its canonical identity belongs to the authoritative selected ranking output
- **THEN** the continuation input SHALL contain only those validated items

### Requirement: Required continuation state is durable before exposure
The system SHALL expose a continuation state only after the authoritative checkpoint and ranking-to-CV handoff have been durably persisted.

#### Scenario: Required checkpoint persistence fails
- **WHEN** the run is otherwise eligible to continue but required checkpoint or handoff persistence fails
- **THEN** the run SHALL NOT be exposed as awaiting continuation and SHALL record a terminal persistence failure at the owning stage

#### Scenario: Optional projection persistence fails
- **WHEN** a non-authoritative telemetry or debug projection fails after required continuation state is durable
- **THEN** the run MAY retain its continuation state and SHALL record the projection failure as secondary diagnostic context

### Requirement: Failure checkpoints reflect the owning stage
The system SHALL preserve the original technical failure stage and set completed stages only to the successful prefix before that stage.

#### Scenario: CV-generation failure follows successful CV analysis
- **WHEN** CV generation, PDF conversion, or generation-artifact persistence fails after CV analysis succeeds
- **THEN** the checkpoint SHALL record CV analysis as completed, CV generation as the retry boundary, and CV generation as the owning failure stage

#### Scenario: Finalization fails after a primary technical failure
- **WHEN** finalization or secondary artifact persistence fails after a primary stage failure has been classified
- **THEN** the primary stage and failure code SHALL remain authoritative and the secondary failure SHALL be recorded separately
