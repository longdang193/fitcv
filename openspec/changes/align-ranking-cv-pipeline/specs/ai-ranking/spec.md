# Spec Delta

## Purpose

Provides the canonical Stage 6 contract that converts an evidence-gated Pareto shortlist into a deterministic Final Top 15 without personalization, evidence loss, or ambiguous score status.

## ADDED Requirements

### Requirement: Pareto shortlist is the ranking input
Stage 6 SHALL accept up to 50 jobs selected by the canonical Pareto shortlist and SHALL preserve each job's eligibility, coverage, evidence, qualifiers, gaps, and provenance for ranking and handoff.

#### Scenario: Shortlist evidence reaches ranking
- **WHEN** a Pareto-selected job has validated support, qualifiers, gaps, and evidence IDs
- **THEN** the ranking input and resulting handoff retain those fields without replacing them with a new evidence selection.

### Requirement: AI score is the sole baseline authority
For new runs, the system SHALL set `baseline_fit` from the holistic `ai_score` and SHALL derive `baseline_rank` and Final Top 15 order from valid scores only.

#### Scenario: Higher valid AI score ranks first
- **WHEN** two eligible jobs have finite AI scores in the inclusive range 0.0 through 1.0
- **THEN** the job with the higher score receives the better baseline rank, subject only to the documented deterministic tie-break.

### Requirement: Invalid scores remain status-only
The system SHALL treat missing, non-finite, out-of-range, or otherwise invalid AI scores as unranked status-only results and SHALL never substitute an artificial zero.

#### Scenario: Invalid score is excluded from ordered output
- **WHEN** an AI result has an invalid or unscored compatibility value
- **THEN** it remains inspectable with its status and is not assigned a baseline rank or included in the Final Top 15 by fabricated score.

### Requirement: Ranking input is bounded and attributable
The system SHALL build the AI request from mandatory job and candidate facts plus strongest attributable evidence within a 12,000-character request budget.

#### Scenario: Request exceeds the budget
- **WHEN** the available facts and evidence exceed the request budget
- **THEN** the system deterministically bounds the request, records the input diagnostics, and does not silently omit the job identity or required provenance fields.

### Requirement: Stage handoff is evidence-preserving
The Stage 6 to Stage 7 handoff SHALL include stable job identity, JD reference, requirement qualifiers, source-backed evidence IDs, gaps, score/status, profile revision, contract versions, and provenance.

#### Scenario: Final-ranked job is handed to CV analysis
- **WHEN** a job enters the Final Top 15 with a valid score or explicit score status
- **THEN** Stage 7 receives the complete handoff envelope and can resolve canonical source evidence independently of the bounded ranking request.

### Requirement: Stage 7 may retrieve canonical evidence
The ranking request SHALL NOT be the sole evidence database for downstream CV analysis or generation.

#### Scenario: Additional source evidence is required
- **WHEN** the bounded ranking request lacks a source-backed fact needed for truthful CV content
- **THEN** Stage 7 may retrieve that fact from canonical sources and records the attributable evidence used.

### Requirement: New runs do not personalize final order
New runs SHALL NOT emit or consume personalized rank fields, preference residuals, or preference-driven ordering; historic personalized artifacts remain readable but read-only.

#### Scenario: Nonzero preference policy is present
- **WHEN** a new run has a nonzero learned or declared preference vector
- **THEN** the Final Top 15 order remains identical to the AI-only baseline order and no personalized residual changes rank.

### Requirement: Promotion overrides are auditable
Any promotion of a ranking strategy before its normal evidence gates pass SHALL persist operator identity, reason, strategy/version, evidence-gate state, timestamp, rollback target, and a readable audit record.

#### Scenario: Operator overrides a blocked gate
- **WHEN** an operator enables a strategy with one or more blocked promotion gates
- **THEN** the run records the override envelope and exposes it for later inspection without marking the blocked gates as passed.
