# Spec Delta

## Purpose

This capability admits the most relevant jobs by validating candidate evidence against job-specific requirements before selection. It preserves explainable, deterministic, bounded shortlist behavior without treating retrieval similarity or missing evidence as the admission truth.

## ADDED Requirements

### Requirement: Stable requirement occurrences
The system SHALL represent each job requirement as a stable occurrence with a category, required or preferred status, source wording, qualifiers, and compound relationships. Authoritative occurrence or source identity SHALL take precedence over wording fallback.

#### Scenario: Distinct clauses remain distinct
- **WHEN** a job contains two separate required clauses that mention the same canonical skill
- **THEN** the system assigns distinct occurrence identities and evaluates each clause independently.

#### Scenario: Authoritative occurrence identity prevents wording leakage
- **WHEN** two distinct occurrences share the same or similar wording and an evidence item identifies only one occurrence
- **THEN** the evidence is evaluated only for the identified occurrence, and the other occurrence remains independently assessed.

#### Scenario: Identity-free evidence does not fan out
- **WHEN** an evidence record has no authoritative occurrence or source identity but its wording matches multiple distinct occurrences
- **THEN** the matching policy resolves it deterministically without attaching the record to multiple occurrences solely because the wording is similar.

#### Scenario: Compound requirement preserves logic
- **WHEN** a requirement contains `Python AND REST APIs` or `Power BI OR Tableau`
- **THEN** the system preserves the compound logic and reports one clause result after evaluating its components.

### Requirement: Requirement-specific evidence coverage
The system SHALL evaluate candidate evidence against each requirement occurrence and classify the result as supported, partial, not evidenced, or unknown, while preserving confirmed contradictions separately. Each top-level clause SHALL produce exactly one `S`, `P`, `E`, or `U` verdict. The final coverage state list SHALL contain top-level clauses only; child diagnostics, if retained, SHALL be separate and SHALL NOT be counted as additional clauses.

#### Scenario: Qualified evidence is partial
- **WHEN** a job requires two years of professional Azure deployment and the candidate evidence shows only a student Azure project
- **THEN** the requirement is classified as partial and the missing professional qualifier remains visible.

#### Scenario: Missing evidence is not absence
- **WHEN** no supporting candidate evidence is retrieved for a requirement
- **THEN** the result is not evidenced and the system does not claim that the candidate lacks the skill.

#### Scenario: Assessment uncertainty is distinct from no evidence
- **WHEN** assessment or retrieval fails, remains incomplete, or is ambiguous
- **THEN** the result is `U`; `E` is reserved for a completed assessment that found no supporting evidence.

#### Scenario: OR provenance follows the satisfying path
- **WHEN** an OR clause has multiple alternatives and one alternative supplies the support that makes the clause fully supported
- **THEN** the clause verdict and provenance reference the satisfying alternative(s), and weaker provenance from unused alternatives does not downgrade the clause.

### Requirement: Retrieval does not decide admission
For production runs using `core_pareto_evidence_v1`, the system SHALL use lexical or semantic retrieval only to find candidate evidence and SHALL NOT use retrieval rank, fused score, or a display evidence limit as the production job-admission criterion. The legacy strategy may retain its existing retrieval admission behavior until promotion, and shadow evaluation SHALL not change downstream inputs.

#### Scenario: Evidence outside the global query is eligible
- **WHEN** a relevant job matches a specific responsibility or project but is absent from the legacy global retrieval Top 50
- **THEN** the job remains eligible for requirement coverage evaluation before shortlist selection.

#### Scenario: Display limit does not truncate assessment
- **WHEN** more than three evidence items could support a requirement
- **THEN** the system assesses enough evidence to determine coverage and independently selects at most three complementary items for compact explanation.

#### Scenario: Legacy rollout behavior remains available
- **WHEN** the configured strategy is the legacy strategy before promotion or after rollback
- **THEN** the existing retrieval admission behavior and production eligibility policy remain unchanged, with the strategy and eligibility-policy identities persisted.

#### Scenario: Promoted strategy uses coverage admission
- **WHEN** the configured production strategy is `core_pareto_evidence_v1`
- **THEN** admission is decided by requirement coverage, Pareto ordering, and deterministic tie-breaking rather than retrieval rank.

### Requirement: Recall-safe eligibility
The system SHALL exclude a job before requirement-aware shortlisting only for a confirmed hard constraint or an explicitly configured global hard filter; uncertain, missing, or inferred metadata SHALL remain inspectable rather than becoming an automatic rejection.

#### Scenario: Uncertain fit context remains comparable
- **WHEN** a job's fit context cannot be established reliably and no confirmed hard constraint fails
- **THEN** the job remains in the comparison set with an uncertainty diagnostic.

#### Scenario: Confirmed hard constraint excludes
- **WHEN** a job violates an explicitly configured hard constraint
- **THEN** the system excludes it before shortlisting and records the rule and reason.

### Requirement: Core coverage metrics
The system SHALL compute required-coverage and duties-coverage proportions from fully supported distinct clauses, keep partial, not-evidenced, unknown, and preferred results visible, and represent categories with no clauses as `N/A`. For every category, `T` SHALL equal `S + P + E + U` over distinct top-level clauses, and full coverage SHALL be `S / T` when `T > 0`; Required, Duties, and Preferred SHALL remain separate metrics.

#### Scenario: Coverage counts clauses once
- **WHEN** two evidence items jointly satisfy one AND clause
- **THEN** the system counts one fully supported clause rather than two.

#### Scenario: Empty category is explicit
- **WHEN** a job has no duties clauses
- **THEN** duties coverage is `N/A` and is not silently converted to zero or full coverage.

### Requirement: Core Pareto ordering
The system SHALL construct Pareto fronts using required coverage and duties coverage as the primary objectives, compare only jobs with identical active-core masks for dominance, and ensure preferred coverage SHALL NOT dominate a job with weaker core coverage.

#### Scenario: Non-dominated core trade-off
- **WHEN** Job A has higher required coverage and Job C has higher duties coverage, with neither lower on both core dimensions
- **THEN** both jobs belong to the same Pareto front.

#### Scenario: Preferred cannot bypass core weakness
- **WHEN** one job has much higher preferred coverage but is dominated on the core dimensions
- **THEN** the preferred-heavy job is ranked behind the stronger core jobs.

#### Scenario: Different active masks are incomparable
- **WHEN** two jobs have different sets of active required and duties categories
- **THEN** neither job dominates the other because `N/A` is not converted to zero or one, and both remain subject to the deterministic front tie-break.

#### Scenario: N/A handling is acyclic and permutation-stable
- **WHEN** four jobs exercise all required/duties active-mask combinations, including a trade-off across `N/A` dimensions
- **THEN** front construction produces no dominance cycle and the final order is unchanged under every permutation of the same input rows.

### Requirement: Deterministic front tie-breaking
The system SHALL resolve a Pareto-front overflow with the canonical lexicographic tuple: evidence validity/provenance descending, confirmed critical gaps ascending, preferred coverage descending, and canonical job identity ascending. `N/A` core metrics remain inactive; missing evidence remains `U` and is not imputed. Balanced core support and assessment completeness remain diagnostics and SHALL NOT introduce additional tie-break precedence.

#### Scenario: Overflow is reproducible
- **WHEN** a Pareto front contains more jobs than the remaining capacity
- **THEN** the same inputs, policy version, and candidate profile produce the same admitted order on every run.

#### Scenario: Evidence quality beats preference
- **WHEN** two jobs have equivalent core coverage but one has stronger attributable evidence and fewer confirmed critical gaps
- **THEN** the stronger-evidence job wins before preferred coverage is considered.

#### Scenario: Expected tie-break order is exact
- **WHEN** jobs tie on an earlier tuple component
- **THEN** the next tuple component decides in the documented order, and canonical job identity is the final deterministic fallback.

### Requirement: Bounded and explainable admission
The system SHALL admit no more than 50 jobs, and every admitted or non-admitted job SHALL retain its strategy version, policy identity, coverage summary, Pareto front or rank, decision reason, relevant evidence or exclusion references, and deterministic assessment/decision fingerprints.

#### Scenario: Capacity is enforced
- **WHEN** more than 50 jobs are eligible after ordering
- **THEN** exactly the highest-priority 50 are admitted and the remaining jobs remain inspectable with non-admission reasons.

#### Scenario: Decision is inspectable
- **WHEN** an operator inspects a shortlist decision
- **THEN** the system exposes enough coverage, evidence, and policy data to explain why the job was admitted or not admitted.

### Requirement: Migration-safe strategy rollout
The system SHALL support running the requirement-aware selector in shadow mode against a shared recall-safe evaluation pool while preserving the legacy production eligibility policy and recording its exclusions separately before making it the production admission strategy.

#### Scenario: Shadow comparison uses the same pool
- **WHEN** legacy and requirement-aware strategies run in shadow mode
- **THEN** both strategies see the same recall-safe evaluation-pool job IDs before either applies a shortlist capacity cutoff.

#### Scenario: Legacy exclusions are visible in shadow mode
- **WHEN** legacy production eligibility excludes a job that the recall-safe evaluation pool retains
- **THEN** the shadow artifact records the legacy exclusion and still evaluates the job with the requirement-aware selector without changing legacy downstream inputs.

#### Scenario: Rollback preserves compatibility
- **WHEN** an acceptance gate fails after controlled promotion
- **THEN** switching back to the legacy strategy restores legacy production behavior without destructive persistence migration, and resumed runs honor the persisted strategy.

#### Scenario: Strategy remains versioned
- **WHEN** a run persists shortlist results
- **THEN** the result identifies the strategy and policy version used, and checkpoint resume does not silently switch strategy.

### Requirement: Downstream contract preservation
The system SHALL preserve the meaning of downstream ranking, CV analysis, CV generation, checkpoint, resume, and operator inspection contracts while changing only shortlist admission behavior. Shortlist admission and shortlist order SHALL remain diagnostic selection inputs; they SHALL NOT become final ranking truth or override Stage 6 AI scoring and Final Top 15 ordering.

#### Scenario: Resume preserves selection
- **WHEN** a run resumes after the shortlist stage has completed
- **THEN** the persisted shortlist order, decision reasons, and evidence identities remain unchanged.

#### Scenario: Late-stage fit truth remains authoritative
- **WHEN** a job is admitted by the requirement-aware selector but later fails a downstream evidence or readiness gate
- **THEN** the late-stage gate remains authoritative and the shortlist admission does not force a positive fit or generation outcome.

### Requirement: Selection quality is measurable
The system SHALL expose evaluation data sufficient to compare requirement-aware and legacy admission using Recall@50 as the primary metric and latency, cost, evidence correctness, determinism, and assessment completeness as secondary metrics, with all documented promotion gates required before changing the production default.

#### Scenario: Recall is measured against the full pool
- **WHEN** a shadow evaluation is executed
- **THEN** Recall@50 is calculated against manually reviewed relevance labels over the full eligible pre-cutoff pool, not only the legacy shortlist.

#### Scenario: Low-confidence assessment is visible
- **WHEN** a job's coverage cannot be assessed reliably
- **THEN** the evaluation artifacts report that uncertainty separately from confirmed lack of evidence.

#### Scenario: Promotion gates are explicit
- **WHEN** a promotion evaluation completes
- **THEN** the artifact reports pass/fail for evidence correctness at least 95%, unknown assessment rate at most 10%, exact replay and input-permutation determinism at 100%, Recall@50 no lower than the legacy baseline, and shortlist-stage p95 latency and estimated evidence-retrieval cost no more than 2x legacy.
