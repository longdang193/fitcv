# Spec Delta

## Purpose

Defines how requirement-aware shortlist assessments scope uncertainty, preserve clause identity, validate evidence, and decide whether persisted coverage is safe to reuse or must be recomputed.

## ADDED Requirements

### Requirement: Assessment completeness is scoped to each job and occurrence
The shortlist SHALL represent assessment completeness and failure origin per job and requirement occurrence rather than as one run-global boolean.

#### Scenario: One job retrieval fails
- **WHEN** evidence assessment fails for one job in a multi-job evaluation pool
- **THEN** every occurrence whose assessment depends on the failed retrieval or validation is marked `U`, `failure_derived=true`, incomplete, and retryable; independently completed jobs and unaffected occurrences retain their own final states

#### Scenario: One occurrence fails inside an assessed job
- **WHEN** retrieval or validation fails for one requirement occurrence
- **THEN** that occurrence records `failure_derived=true` and `U`, unrelated occurrences retain their independently assessed states, and the job is incomplete

#### Scenario: Unresolved state is policy-defined
- **WHEN** every occurrence is assessed without retrieval or validation failure but the support policy cannot establish support
- **THEN** the occurrence may remain policy-defined `U` or `E` while the job remains complete and non-retryable

#### Scenario: Stale coverage cannot be recomputed
- **WHEN** persisted coverage is missing, incompatible, incomplete, or failure-derived and the assessment boundary cannot complete recomputation
- **THEN** affected occurrences remain `U` with `failure_derived=true`, incomplete, and retryable; no new authoritative Stage 5 admission is emitted, and any dependent admission, Stage 6 handoff, or Stage 7 checkpoint is invalidated

### Requirement: Persisted coverage requires compatible assessment provenance
The system SHALL reuse persisted coverage only when all required semantic fingerprints match, the fingerprint schema is known, and the assessment is complete without failure-derived uncertainty.

#### Scenario: Coverage is safely reusable
- **WHEN** coverage contains matching contract, assessment-input, evidence-compatibility, retrieval-policy, and support-policy fingerprints and every occurrence is complete
- **THEN** the system may reuse coverage without recomputing it

#### Scenario: Coverage contains failure-derived uncertainty
- **WHEN** fingerprints match but any occurrence or compound result was derived from retrieval or validation failure
- **THEN** the system recomputes the affected assessment and records a retry/reuse rejection reason

#### Scenario: Fingerprint is missing or stale
- **WHEN** coverage lacks a required fingerprint, uses an unknown schema version, or any fingerprint differs from current inputs
- **THEN** the system rejects reuse, records the reason, and recomputes at the first affected boundary

### Requirement: Coverage fingerprints are deterministic and semantic
Coverage compatibility fingerprints SHALL include versioned semantic inputs and SHALL be computed from canonical, deterministic representations without volatile run metadata.

#### Scenario: Equivalent inputs are serialized
- **WHEN** the same requirement graph, profile/evidence revisions, retrieval policy, and support policy are presented in different input order
- **THEN** the canonical serialization sorts identity-bearing collections, preserves explicit nulls, removes duplicates, and produces the same SHA-256 fingerprint

#### Scenario: Material evidence changes
- **WHEN** an evidence record revision or content hash changes while its identifier remains the same
- **THEN** the evidence-compatibility fingerprint changes and prior coverage is not reused

### Requirement: Requirement occurrences remain identity-bound
Current requirement occurrence identity SHALL take precedence over wording equality when binding evidence or coverage.

#### Scenario: Two occurrences share identical wording
- **WHEN** two distinct requirement occurrences have the same source wording
- **THEN** evidence bound to one occurrence SHALL NOT satisfy the other solely because the wording matches

#### Scenario: Legacy evidence lacks occurrence identity
- **WHEN** legacy evidence has no occurrence identifier
- **THEN** wording fallback is allowed only when the wording maps unambiguously to one current occurrence; otherwise the result is unresolved and reuse is ineligible

### Requirement: Compound uncertainty propagates by occurrence
Compound and job-level coverage SHALL preserve the distinction between a complete no-support result and a failure-derived unknown result.

#### Scenario: Failed child in an AND compound
- **WHEN** an AND compound contains a failure-derived child and no policy-valid result can bypass it
- **THEN** the compound and job record `U`, `failure_derived=true`, incomplete completeness, and retryability

#### Scenario: Supported OR branch exists
- **WHEN** an OR compound has a qualifying supported branch and another branch is unresolved or failure-derived
- **THEN** the compound follows the satisfying branch under the support policy and does not downgrade because of an unused weaker branch

#### Scenario: No OR branch establishes support
- **WHEN** no OR branch is supported
- **THEN** if any branch is failure-derived, the compound is `U` and failure-derived; otherwise the active support policy deterministically selects the unresolved/contradictory outcome while preserving all material branch diagnostics and failure origin

### Requirement: Equal OR branches use deterministic provenance
When multiple OR alternatives qualify equally, the system SHALL preserve a deterministic union of their provenance and evidence.

#### Scenario: Multiple branches tie
- **WHEN** two or more OR branches have equal qualifying support under the active policy
- **THEN** selected branch identifiers and evidence identifiers are the sorted deduplicated union of all tied branches

#### Scenario: A single display representative is needed
- **WHEN** a downstream display requires one representative for tied qualifying branches
- **THEN** the representative is selected by the stable branch-identity order and does not change with input order

### Requirement: Evidence references are bounded and integrity-complete
Persisted coverage SHALL retain bounded selected evidence plus complete deduplicated references that bind each evidence item to its occurrence and evidence revision.

#### Scenario: Evidence references are persisted
- **WHEN** a shortlist decision is persisted for downstream stages
- **THEN** references include occurrence identity, evidence identifier, evidence revision or content hash, evidence projection version, and deterministic ordering without duplicate identity tuples

#### Scenario: A reference is missing or inconsistent
- **WHEN** a selected or referenced evidence item is missing, malformed, stale, or contradicts its occurrence binding
- **THEN** the affected occurrence becomes unresolved, coverage reuse is ineligible, and the integrity reason is recorded instead of silently dropping the reference

#### Scenario: Reference manifest exceeds its bound
- **WHEN** the complete evidence reference manifest required for persisted occurrence states exceeds its configured bound
- **THEN** persistence records an integrity failure and makes reuse ineligible; the implementation SHALL recompute or retry rather than silently truncating the manifest

### Requirement: Assessment and display evidence have separate limits
The evidence used to assess requirement coverage SHALL not be limited to the compact explanation set persisted for display or handoff.

#### Scenario: More candidates are needed for assessment
- **WHEN** the compact explanation limit is smaller than the evidence candidates required to determine coverage
- **THEN** assessment may inspect the broader bounded candidate pool while persisted display evidence remains bounded and attributable

#### Scenario: Assessment evidence is broader than display evidence
- **WHEN** a candidate outside the selected display set establishes a coverage state
- **THEN** the state retains that candidate's complete evidence reference even if only bounded selected evidence is displayed

### Requirement: Recomputed coverage invalidates dependent decisions
When coverage compatibility or completeness changes, downstream admission and ranking decisions SHALL be invalidated according to their dependency on the changed coverage.

#### Scenario: Recomputed coverage can change admission
- **WHEN** recomputed occurrence states can change Stage 5 admission or its ranking inputs
- **THEN** the affected Stage 5 decision, dependent Stage 6 handoff, and Stage 7 checkpoint are invalidated and recomputed from the first affected boundary

#### Scenario: Recomputed coverage cannot change authoritative admission
- **WHEN** recomputation changes only non-authoritative display metadata and the admitted set and ranking inputs are proven unchanged
- **THEN** the authoritative admission may remain while dependent evidence/checkpoint metadata is replaced with new provenance
