# Spec Delta

## Purpose

Provides a deterministic, inspectable contract for CV validation outcomes so formatting, factual integrity, review, rendering, persistence, reuse, and submission decisions remain distinct and recoverable.

## ADDED Requirements

### Requirement: myCVs section policy is canonical
The system SHALL use one versioned policy for canonical keys, display headings, presence rules, header handling, and order across composition, Markdown serialization, structural validation, and PDF acceptance.

#### Scenario: Skills and Certificates are both present
- **WHEN** a myCVs artifact contains meaningful Skills and Certificates sections
- **THEN** emitted and validated headings place Certificates before Skills and preserve the canonical relative order of all other sections

#### Scenario: Optional sections are omitted
- **WHEN** an optional canonical section has no meaningful source content
- **THEN** the section is omitted without changing the relative order of remaining sections

#### Scenario: Mandatory content is omitted
- **WHEN** a mandatory or canonical-profile section is expected but absent from the structured payload or rendered artifact
- **THEN** validation emits a deterministic missing-section diagnostic and does not silently treat the omission as an optional empty section

#### Scenario: A generated artifact is round-tripped
- **WHEN** a valid structured CV is serialized and passed through structural and PDF heading checks
- **THEN** all consumers accept headings produced from the same policy version

### Requirement: Structured skill provenance is authoritative
The system SHALL determine factual skill validity from canonical structured claims and provenance, not from independently reparsed rendered Markdown.

#### Scenario: A structured skill is canonically supported
- **WHEN** a structured skill claim resolves to an allowed canonical candidate skill or supported evidence identifier
- **THEN** the claim is not rejected solely because its rendered label differs in punctuation, casing, grouping, or line formatting

#### Scenario: Structured skill identity is missing or empty
- **WHEN** a new attempt has missing structured skills or an explicitly empty structured skill set
- **THEN** validation distinguishes those states from unsupported claims and does not use rendered text to invent factual authority

#### Scenario: Rendered text projects an unexpected skill
- **WHEN** a rendered Skills section contains a material skill that cannot be reconciled with the structured claim set
- **THEN** final artifact acceptance is blocked with a projection diagnostic while structured content validity remains classified from structured claims and provenance

#### Scenario: Legacy Markdown lacks structured provenance
- **WHEN** a historical artifact has only rendered skill text and no compatible structured provenance
- **THEN** the artifact remains readable, but new factual validation and reuse are marked provenance-unavailable and do not silently infer authority from text

### Requirement: Validation failures preserve quarantined drafts
When generation produces a usable structured and/or rendered draft but validation fails, the system SHALL preserve available drafts and validation evidence in an explicit quarantined state that is not an accepted artifact.

#### Scenario: Complete draft fails validation
- **WHEN** post-repair validation is invalid and structured and rendered draft payloads are both available for the same attempt and validation snapshot
- **THEN** persistence stores a quarantined draft with diagnostics, identity, fingerprints, and checksums, blocks submission, and excludes it from accepted-output projections

#### Scenario: Partial draft fails validation
- **WHEN** post-repair validation is invalid and only one inspectable draft representation is available
- **THEN** persistence stores the available representation with an explicit availability map and never fabricates the missing representation

#### Scenario: Validation fails before a usable draft exists
- **WHEN** validation fails without a usable structured or rendered draft
- **THEN** the system persists failure scope and diagnostics without fabricating an artifact and marks draft disposition unavailable rather than quarantined

#### Scenario: A quarantined draft is resumed or displayed
- **WHEN** an operator, retry, or downstream reader loads a quarantined validation draft
- **THEN** the draft is inspectable under policy but cannot be review-approved, downloaded as accepted output, submitted, or used as a reuse cache hit

#### Scenario: A quarantined attempt is retried
- **WHEN** retry policy permits a new attempt for a quarantined validation failure
- **THEN** the system creates a distinct attempt/version linked to the original and preserves the historical quarantine unchanged

### Requirement: Failure classification uses a typed diagnostic registry
The system SHALL classify validation, generation, rendering, persistence, and quality outcomes from a versioned registry of typed diagnostic codes and structured facts rather than warning text or free-form messages.

#### Scenario: A known rule fails
- **WHEN** a validator or renderer detects a known structural, provenance, projection, artifact, provider, review, or persistence failure
- **THEN** it emits a stable code with category, severity, blocking state, retryability, terminality, source, and structured facts owned by the failure producer

#### Scenario: A length or page-fit warning is emitted
- **WHEN** a length estimate produces a non-blocking quality warning or an actual page-fit check produces an artifact failure
- **THEN** the diagnostic category and decision effect follow the acceptance stage and cannot change solely because the message mentions length or budget

#### Scenario: Multiple diagnostics coexist
- **WHEN** one attempt produces multiple diagnostics in different producer or execution orders
- **THEN** persistence deduplicates and orders them deterministically and selects the same primary diagnostic under the registry precedence rules

#### Scenario: A consumer projects a reason
- **WHEN** pipeline, worker, persistence, review, reuse, or UI code needs a status or reason
- **THEN** it maps typed codes and explicit state fields directly while human-readable messages remain display text

#### Scenario: A diagnostic is unknown
- **WHEN** a failure source cannot provide a recognized typed code
- **THEN** the system records an explicit unclassified diagnostic with source and facts, preserves a required compatibility projection, and does not infer a more specific reason from the message

### Requirement: Acceptance dimensions remain independent
The system SHALL represent content validity, technical generation, draft disposition, review, PDF/artifact, persistence, and derived submission clearance as independent dimensions.

#### Scenario: Valid content needs review
- **WHEN** content and provenance validation pass but policy requires human review
- **THEN** content remains valid, PDF may be verified and persisted, review is pending, persistence is recorded independently, and submission remains blocked

#### Scenario: Invalid content has a preserved draft
- **WHEN** content validation fails and a draft is quarantined
- **THEN** content is invalid, technical completion reflects the failed attempt, draft disposition is quarantined, review is not approved, PDF is not attempted unless evidence says otherwise, and submission is blocked

#### Scenario: PDF conversion fails after valid content
- **WHEN** content is valid but conversion, PDF integrity, or post-conversion acceptance fails
- **THEN** content validity remains valid, PDF/artifact state records technical failure, any permitted grounded draft remains distinct, and submission is blocked

#### Scenario: Persistence fails after a known outcome
- **WHEN** persistence fails while storing an accepted, review-required, PDF-failed, or quarantined attempt
- **THEN** the original content, review, PDF, and validation outcome remains recoverable and persistence is recorded as failed without replacing the original diagnostic

#### Scenario: Hard validation is followed by review approval
- **WHEN** a hard validation failure is present and a review approval event is received
- **THEN** review approval cannot make the attempt accepted or submission-clear

### Requirement: Submission clearance is derived
The system SHALL derive submission eligibility from authoritative lifecycle dimensions and existing page-fit gates rather than allowing a diagnostic, review event, or legacy status to grant it directly.

#### Scenario: All required gates pass
- **WHEN** technical generation, content validity, required review, verified PDF, persistence, and page-fit gates pass
- **THEN** submission clearance is eligible and the compatibility status is projected deterministically

#### Scenario: Any required gate fails
- **WHEN** any required technical, content, review, PDF, persistence, or page-fit gate is missing or failed
- **THEN** submission clearance is blocked and the failed dimension remains inspectable

### Requirement: Reuse and checkpoint compatibility is versioned
The system SHALL include validation-policy, diagnostic-schema, section-policy, and skill-provenance versions in Stage 7 reuse and checkpoint compatibility decisions.

#### Scenario: Validation policy changes
- **WHEN** one of the validation, diagnostic, section, or skill-provenance versions changes
- **THEN** affected Stage 7 validation/generation reuse and checkpoints are invalidated at the first affected boundary without unnecessarily invalidating compatible Stage 6 ranking work

#### Scenario: Historical provenance is insufficient
- **WHEN** a historical record lacks required provenance or compatibility inputs
- **THEN** it remains readable but cannot authorize new factual reuse or checkpoint resume

#### Scenario: Quarantine is considered for reuse
- **WHEN** a cache lookup encounters a quarantined attempt
- **THEN** the attempt may provide retry context but never qualifies as an accepted-output cache hit

### Requirement: Legacy projections remain compatible
The system SHALL keep existing status and reason values readable while making new decisions from typed diagnostics and independent lifecycle fields.

#### Scenario: A legacy record is read
- **WHEN** a stored record contains historical statuses such as `validation_failed`, `review_required`, or `pdf_failed`
- **THEN** the record remains readable and is projected into the new dimensions without rewriting its historical provenance

#### Scenario: A new record is emitted
- **WHEN** a new generation attempt completes or terminalizes
- **THEN** the canonical diagnostics and lifecycle fields are persisted and legacy status/reason fields are emitted only as deterministic compatibility projections
