# Spec Delta

## Purpose

Provides a deterministic, inspectable contract for CV validation outcomes so formatting, factual integrity, review, rendering, persistence, and submission decisions remain distinct and recoverable.

## ADDED Requirements

### Requirement: myCVs section order is canonical
The system SHALL use one versioned section-order policy for structured composition, Markdown serialization, structural validation, and PDF acceptance.

#### Scenario: Skills and Certificates are both present
- **WHEN** a myCVs artifact contains meaningful Skills and Certificates sections
- **THEN** the emitted and validated order places Certificates before Skills, with all other sections in canonical relative order

#### Scenario: Optional sections are omitted
- **WHEN** one or more canonical sections have no meaningful source content
- **THEN** the omitted sections are removed without changing the relative order of the remaining sections

#### Scenario: A generated artifact is round-tripped
- **WHEN** a valid structured CV is serialized and passed through structural validation
- **THEN** validation accepts the serialized headings when they follow the same versioned policy used by the serializer

### Requirement: Structured skill provenance is authoritative
The system SHALL determine factual skill validity from canonical structured claims and provenance, not from independently reparsed rendered Markdown.

#### Scenario: A structured skill is canonically supported
- **WHEN** a structured skill claim resolves to an allowed canonical candidate skill or supported evidence identifier
- **THEN** the claim is not rejected solely because its rendered label differs in punctuation, casing, grouping, or line formatting

#### Scenario: Rendered text contains a skill-like token
- **WHEN** a rendered Skills section contains a token that is absent from the structured claim set
- **THEN** the token does not create a new factual claim; the system records a serialization/projection diagnostic if the rendered output disagrees with the structured model

#### Scenario: Legacy Markdown lacks structured provenance
- **WHEN** a historical artifact has only rendered skill text and no compatible structured provenance
- **THEN** the artifact remains readable, but new factual validation or reuse is marked provenance-unavailable and does not silently infer authority from the text

### Requirement: Validation failures preserve quarantined drafts
When generation produces a structured draft and rendered draft but validation fails, the system SHALL preserve those drafts and their validation evidence in an explicit quarantined state.

#### Scenario: Deterministic validation failure has a draft
- **WHEN** post-repair validation is invalid and structured and rendered draft payloads are available
- **THEN** persistence stores a quarantined validation draft with the validation snapshot and diagnostics, blocks submission, and excludes it from accepted-output projections

#### Scenario: Validation fails before a usable draft exists
- **WHEN** validation fails without a structurally usable structured or rendered draft
- **THEN** the system persists the failure diagnostics and scope without fabricating an artifact, and marks the artifact as unavailable or failed rather than quarantined

#### Scenario: A quarantined draft is resumed or displayed
- **WHEN** an operator, retry, or downstream reader loads a quarantined validation draft
- **THEN** the draft remains inspectable and retryable under policy, but it cannot be treated as accepted, review-approved, or submission-clear

### Requirement: Failure classification uses typed diagnostics
The system SHALL classify validation, generation, rendering, persistence, and quality outcomes from typed diagnostic codes and structured facts rather than warning text or free-form messages.

#### Scenario: A validation rule fails
- **WHEN** a validator detects a missing section, invalid section order, unsupported structured claim, or other known rule failure
- **THEN** it emits a stable diagnostic code with category, severity, blocking state, retryability, source, and structured facts sufficient for downstream classification

#### Scenario: A length or page-fit warning is emitted
- **WHEN** a length estimate or page-fit check produces a non-blocking warning
- **THEN** the warning is classified as quality or artifact information and is not promoted to a generation-format defect solely because its message mentions length or budget

#### Scenario: A consumer projects a reason
- **WHEN** pipeline, worker, persistence, or UI code needs a status or review reason
- **THEN** it maps the diagnostic code and explicit state fields directly, while human-readable messages remain display text and cannot change the classification

#### Scenario: A diagnostic is unknown
- **WHEN** a failure source cannot provide a recognized typed code
- **THEN** the system records an explicit unclassified diagnostic with its source and facts, preserves a compatibility projection if required, and does not infer a more specific reason from the message

### Requirement: Acceptance dimensions remain independent
The system SHALL represent content validity, review state, artifact/PDF state, and submission clearance as independent dimensions.

#### Scenario: Valid content needs review
- **WHEN** content and provenance validation pass but policy requires human review
- **THEN** the artifact may remain persisted and render-verified while review is pending and submission remains blocked

#### Scenario: Invalid content has a preserved draft
- **WHEN** content validation fails but a draft is quarantined
- **THEN** content is invalid, artifact state is quarantined, and submission is blocked without projecting the draft as accepted output

#### Scenario: PDF conversion fails after valid content
- **WHEN** content is valid but PDF conversion or post-conversion acceptance fails
- **THEN** content validity remains intact, artifact state records the technical PDF failure, and the persisted Markdown/structured content is not reclassified as a content-generation failure

### Requirement: Legacy status projections remain compatible
The system SHALL keep existing status and reason values readable while making new decisions from the typed diagnostic and independent-state contract.

#### Scenario: A legacy record is read
- **WHEN** a stored record contains historical statuses such as `validation_failed`, `review_required`, or `pdf_failed`
- **THEN** the record remains readable and is projected into the new dimensions without rewriting its historical provenance

#### Scenario: A new record is emitted
- **WHEN** a new generation attempt completes
- **THEN** the canonical typed diagnostics and independent state fields are persisted, and legacy status/reason fields are emitted only as deterministic compatibility projections
