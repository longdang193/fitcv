# Spec Delta

## Purpose

This capability keeps enrichment outputs task-bound, consistently normalized, and resilient to isolated item failures while preserving diagnostics for incomplete or uncertain fit context.

## ADDED Requirements

### Requirement: Enrichment responses are task-bound
The system SHALL mark an enrichment row as fresh only when the completed runtime result matches the requested enrichment task contract and passes task-specific validation.

#### Scenario: Matching enrichment response is fresh
- **WHEN** an `enrich_extraction` request returns a valid enrichment result with matching runtime provenance
- **THEN** the row may be persisted with fresh-enrichment provenance and its request contract evidence

#### Scenario: Response from another task is not fresh
- **WHEN** a result has runtime provenance for a different routing task or fails the enrichment-specific contract
- **THEN** the system SHALL NOT label it `fresh_enrichment` and SHALL persist a typed contract diagnostic or the configured fallback outcome

#### Scenario: Partial fit context remains usable
- **WHEN** a task-bound response contains at least one usable structured enrichment signal but omits other optional fit-context fields
- **THEN** the system SHALL retain the usable fields and record uncertainty or missing-field diagnostics instead of treating the row as invalid solely for being incomplete

### Requirement: Seniority uses one canonical taxonomy
The system SHALL normalize enrichment and screening seniority values through the same configured ladder and alias map, while preserving the raw value and any normalization diagnostic.

#### Scenario: Alias normalization is shared
- **WHEN** enrichment or screening receives a configured seniority alias such as `sr` or `mid-level`
- **THEN** both consumers SHALL resolve it to the same canonical ladder value

#### Scenario: Unknown seniority stays diagnostic
- **WHEN** a seniority value is absent or not present in the canonical taxonomy
- **THEN** the system SHALL preserve the raw value when available, record an unknown-value diagnostic, and SHALL NOT reject the job solely for that uncertainty

### Requirement: Recoverable item failures do not abort the batch
The system SHALL isolate recoverable failures for individual jobs and return an item-level fallback or diagnostic row so unrelated jobs can continue processing.

#### Scenario: One job exhausts recoverable enrichment attempts
- **WHEN** one job reaches the retry limit for a recoverable parse, validation, or item-scoped provider failure
- **THEN** the system SHALL record the typed failure on that job, produce the configured fallback outcome, and continue processing other jobs

#### Scenario: Multiple item failures remain independently observable
- **WHEN** more than one job fails enrichment during the same batch
- **THEN** each failed job SHALL retain its own failure stage, code, attempts, and provenance without overwriting another job's diagnostics

### Requirement: Global failures remain fatal
The system SHALL stop the enrichment batch for explicit cancellation and failures of shared configuration, routing, persistence, or other non-item-scoped infrastructure required to process the batch.

#### Scenario: Cancellation stops remaining work
- **WHEN** the cancellation boundary is triggered during enrichment
- **THEN** the system SHALL stop or cancel remaining work and expose cancellation as the batch outcome rather than converting it to an item fallback

#### Scenario: Shared infrastructure failure stops the batch
- **WHEN** a shared configuration, routing, database, or persistence failure prevents reliable processing of the batch
- **THEN** the system SHALL abort the batch with a typed batch-level diagnostic and SHALL NOT report the batch as successfully enriched

### Requirement: Cached and fallback provenance stays distinct
The system SHALL preserve distinct provenance for fresh, reused-cached, and fallback enrichment rows across persistence and continuation.

#### Scenario: Cached row is reused without becoming fresh
- **WHEN** a reusable cached row matches the current raw-job and enrichment-contract fingerprints
- **THEN** the system SHALL retain its cached provenance and SHALL NOT relabel it as fresh enrichment

#### Scenario: Fallback row remains resumable and inspectable
- **WHEN** enrichment falls back after a recoverable item failure
- **THEN** the row SHALL remain inspectable with its failure diagnostic and SHALL not be treated as a successful fully enriched result
