# Spec Delta

## Purpose

Defines the authoritative, auditable ranking contract used after shortlist admission and before the final CV handoff.

## ADDED Requirements

### Requirement: Ranking order is explicitly versioned

The system SHALL persist `ranking_order_version`, the active ranking-policy version, and the score contract version with every ranking decision envelope. Existing checkpoints SHALL resume their persisted order; retiring personalization SHALL use a new order version and run/checkpoint identity.

#### Scenario: Existing personalized run resumes
- **WHEN** a checkpoint persists the current personalized order or its active preference-policy snapshot
- **THEN** resume SHALL use those persisted versions and inputs, even if current configuration defaults differ.

#### Scenario: New order retires personalization
- **WHEN** a new ranking order version is explicitly selected for a fresh run
- **THEN** the decision SHALL use its documented authoritative value and tie-break sequence, and SHALL not silently mix personalized ordering with the new order.

#### Scenario: New order records compatibility fields
- **WHEN** the new order version retires personalization
- **THEN** personalized rank, residual, and preference-policy fields SHALL remain readable as non-authoritative compatibility data and SHALL not influence the new order.

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
- **THEN** the system SHALL persist `score_status=unscored` with the existing `failure_code`, `disposition=retryable_failure`, and `retry_eligible=true` fields, plus diagnostics, and SHALL distinguish it from a valid low score and from confirmed incompatibility. The system SHALL NOT introduce a fourth `score_status` value for retryability.

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

The ranking-to-CV handoff fingerprint SHALL be `ranking_cv_handoff_v1`: SHA-256 over the specified canonical UTF-8 JSON handoff object, including the schema version, canonical job identity/qualifiers, baseline rank/score, score state, ordered evidence IDs, gaps/unknowns, profile revision, ranking order/policy/contract versions, and provenance references. Object keys SHALL be sorted, separators compact, optional absent values represented as `null`, and field arrays emitted in deterministic contract order. The persisted owner is the ranking stage artifact at `stage_transition_artifacts_json.stages.ranking`, with per-job ledger references where available.

### Requirement: Historic ranking artifacts remain readable

The system SHALL continue to read historic personalized rank, residual, and related fields. For a fresh run using the new order version, those fields SHALL NOT influence authoritative ranking decisions; for an existing persisted personalized order, they remain active until that run is explicitly migrated to a new order version. New runs under the new order SHALL NOT compute or write personalized rank, preference residual, or preference-policy fields as authoritative outputs.

#### Scenario: Legacy artifact is inspected
- **WHEN** an operator opens a historic artifact containing personalized ranking fields
- **THEN** the fields SHALL remain available for inspection with their original provenance and SHALL be labeled as historic/legacy where needed.

#### Scenario: New run ignores legacy fields
- **WHEN** a new ranking run processes an input that contains historic personalized fields
- **THEN** the new decision SHALL use only the authoritative AI score contract and current tie-break policy.

#### Scenario: New order stops legacy personalization
- **WHEN** a fresh run explicitly selects the new non-personalized ranking order
- **THEN** the run SHALL not activate personalized ranking computation and SHALL not emit new personalized rank, residual, or preference-policy fields as authoritative outputs.

### Requirement: Ranking does not own shortlist promotion

The ranking stage SHALL consume the admitted shortlist and SHALL NOT promote, override, or duplicate Pareto admission or `pipeline.shortlist_strategy` promotion gates. Pareto promotion remains owned by the shortlist capability; a future ranking-strategy promotion requires a separately named ranking strategy and contract.

#### Scenario: Shortlist promotion is unresolved
- **WHEN** shortlist promotion evidence is missing or fails a configured gate
- **THEN** the ranking stage SHALL preserve the shortlist decision and SHALL not report that its own ranking evaluation promoted the shortlist strategy.
