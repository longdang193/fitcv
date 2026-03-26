# Cheap-First Pipeline Narrowing — Design Spec

**Date:** 2026-03-26
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The current deterministic filter stage mixes candidate-specific preferences with generic screening rules. There is no clear admin-managed configuration layer for global job filters that should apply to every run regardless of candidate profile contents.

This makes it awkward to add operational filters such as:

- maximum applicant count
- maximum posting age
- future post-enrichment policy filters

These rules are system policy, not candidate intent, and should not be inferred from or stored in `candidate_profile`.

The current global-job-filter design also does not clearly separate filters by the stage in which their source data becomes available.

This matters because some filters can be evaluated before enrichment, while others depend on enrichment output.

The broader pipeline also does too much expensive work before it narrows the candidate set for AI scoring. Runtime latency is dominated by enrichment and LLM-based scoring, so cheap filters and cheap ranking signals should be applied as early as valid data allows.

Without an explicit phase split:

- cheap filters may run too late
- the pipeline may enrich jobs that should have been rejected earlier
- future global filters will have no clear architectural home
- too many jobs may reach AI scoring before cheaper pruning signals are used

---

## Goal

Define a cheap-before-expensive pipeline strategy with two explicit categories of global filters:

1. pre-enrichment global filters
2. post-enrichment global filters

Also define a runtime-latency strategy where:

- cheap global filters run as early as possible
- enrichment is only performed on surviving jobs
- cheap post-enrichment ranking signals prune the AI-scoring pool before LLM evaluation

The first implementation should move currently supported global filters to the earliest valid phase, while the document also establishes the future architecture for later global filters and later cheap pre-LLM pruning.

---

## Non-Goals

- Implementing all future post-enrichment global filters now
- Implementing every future latency optimization now
- Replacing candidate-specific rule filters
- Moving candidate preferences into admin-managed system policy
- Changing run-detail inspection behavior beyond existing reject-reason display

---

## Design

### Configuration Model

Introduce a distinct group of admin-editable settings for global job filters.

These filters represent system-wide screening policy and are evaluated independently of candidate preferences.

Initial pre-enrichment scope:

- `global_job_filters.applications_count_max`
- `global_job_filters.max_age_days`

Deferred for follow-up:

- post-enrichment global job filter settings that depend on enriched fields
- `global_job_filters.min_description_length` or similar quality thresholds once description-quality semantics are stable

Semantics:

- `applications_count_max`: reject jobs whose parsed applicant count exceeds the configured threshold
- `max_age_days`: reject jobs whose posting age exceeds the configured threshold

These settings should be understood as system-wide screening policy for this deployment, not as universally correct ranking rules for every possible user or workflow.

These settings should appear in a dedicated admin settings group for global job filters, not inside retrieval, ranking, or candidate-preference-oriented sections.

Suggested labels:

- `Maximum Applicant Count`
- `Maximum Posting Age (Days)`

Suggested descriptions:

- `Reject jobs when the applicant count is above this threshold.`
- `Reject jobs when the posting is older than this many days.`

---

### Field-Level Null Handling

Global job filters must define explicit behavior for missing or unparseable source fields.

- `applications_count`
  - Source field: nullable integer
  - Applicant count is approximate and derived from parsed scraper text
  - `NULL` or unparseable value: skip the check
  - Rejection condition: value is present and greater than `applications_count_max`
- `published_at`
  - Source field: nullable date/datetime
  - `NULL` or unparseable value: skip the check
  - Rejection condition: value is present and older than `max_age_days`

This keeps the first iteration fail-open for missing source data while still allowing early rejection when the required values are present.

### Phase Model

Global job filters are split by data availability, not by importance.

#### Pre-enrichment global filters

These use fields available after ingest and normalization, before enrichment.

They should run as early as possible to reject obviously unsuitable jobs before the expensive enrichment step.

Initial pre-enrichment scope:

- `global_job_filters.applications_count_max`
- `global_job_filters.max_age_days`

Source fields already available before enrichment:

- `applications_count`
- `published_at`

#### Post-enrichment global filters

These use fields that are introduced or made reliable only after enrichment.

Examples of future post-enrichment candidates:

- domain-based policy filters
- contract-type policy filters when enrichment is the trusted canonical source
- future skill-structure or semantic quality filters
- any global filter that depends on enriched `seniority`, `job_family`, `domain`, or `required_skills`

This document defines the architectural category, but does not require implementation of those future filters in the first iteration.

---

### Hard Filters vs Cheap Pruning

This design distinguishes between two different narrowing mechanisms:

1. hard filtering
2. cheap score-based pruning

Hard filtering:

- produces binary keep/reject decisions
- represents system policy or candidate constraints
- emits explicit reject reasons

Cheap score-based pruning:

- reduces the candidate pool before AI scoring
- is a ranking reduction stage, not a policy-level rejection mechanism
- should not be treated as producing reject reasons in the same sense as hard filters

This distinction matters because the system should not conflate:

- "the job was rejected by policy or constraints"
- "the job remained below the AI-scoring cutoff in a cheap narrowing stage"

---

### Ownership Boundaries

The filtering model should remain split conceptually into two ownership layers:

1. global job filters
2. candidate-specific filters

Global job filters answer:
"Should this job be considered at all by the system?"

Candidate-specific filters answer:
"Does this job match the candidate's constraints or intent?"

Examples:

- `applications_count_max` is a global job filter
- `location_types` is a candidate preference
- `domains` is a candidate preference
- `seniority_target` is a candidate preference

Missing candidate preference fields should continue to mean "no preference", not "use admin defaults".

### Freshness Migration

`max_age_days` already exists today as a candidate-preference-driven freshness check in `rule_filter.py`.

This design changes that ownership model:

- freshness becomes a global admin-managed filter
- the filter no longer reads `prefs.get("max_age_days")`
- candidate profiles no longer control posting-age filtering

Implementation note:

- `max_age_days` should be removed from candidate-profile schema and validation once the admin-managed global filter is active, so the setting has a single owner

For continuity in stored filter results and run-detail inspection, the existing reject reason should remain:

- `job_too_stale`

---

### Why `applications_count_max` and `max_age_days` Belong Pre-Enrichment

These two filters do not depend on LLM enrichment.

In the current pipeline:

- `published_at` is available from ingest
- `applications_count` is parsed during normalization
- enrichment later copies these values into structured rows, but does not create them

Therefore, applying these checks only after enrichment is logically late and operationally wasteful.

The pipeline should reject jobs on applicant count and posting age before calling the enrichment layer.

---

### Execution Order

The pipeline should be conceptually split as follows:

1. ingest raw jobs
2. normalize jobs
3. apply pre-enrichment global filters
4. enrich only the surviving jobs
5. apply candidate-specific filters at the earliest phase supported by their source fields, while keeping global filters explicitly split into pre-enrichment and post-enrichment categories
6. build the vector shortlist
7. apply cheap pre-LLM pruning on the shortlisted jobs
8. AI-score only the reduced set
9. compute the final weighted ranking on that reduced set

This preserves the existing deterministic-filter stage concept while making the pipeline progressively narrower before each more expensive step.

---

### Cheap Pre-LLM Pruning

After vector search and before AI scoring, the pipeline should support a cheap pruning phase that reduces how many jobs are sent to the LLM.

This phase is separate from global-job-filter ownership. It exists for runtime optimization, not system-policy filtering.

The pruning approach should be ranking-based rather than a single hard gate.

Recommended inputs for cheap pre-LLM pruning:

- `must_have_match`
- `vector_similarity`
- `title_relevance`
- `seniority_fit`
- optionally `preference_fit`

Recommended behavior:

- compute a cheap composite score using non-LLM features
- keep only the top slice for AI scoring
- accept some recall tradeoff in exchange for substantially lower runtime latency

This design is preferred over a hard-threshold-only approach because it degrades recall more gracefully.

This phase should produce a reduced ranked pool for AI scoring, not policy-style reject reasons.

---

### Run Inspection and Reject Reasons

All global filters, regardless of phase, should continue to emit explicit reject reasons into the existing filter-results storage and run-detail inspection UI.

For the first implementation:

- `applications_count_exceeded`
- `job_too_stale`

The admin should not need to know which phase rejected the job in order to understand the reason, but the architecture should keep the phase distinction clear in code.

---

### First Iteration Scope

Implement only the pre-enrichment subset in this iteration:

- `applications_count_max`
- `max_age_days`

Do not implement post-enrichment global filters yet.

Do not implement cheap pre-LLM pruning yet, but this document establishes where it belongs in the architecture and why it should live after vector shortlist generation and before AI scoring.

This first iteration should also preserve the ability to inspect reject reasons in the existing admin run-detail UI.

---

## Acceptance Criteria

- [ ] The architecture explicitly distinguishes pre-enrichment and post-enrichment global filters
- [ ] Admin settings include a dedicated set of global job filter controls
- [ ] Global job filters apply regardless of candidate profile contents
- [ ] `max_age_days` is migrated out of candidate preferences and into admin-managed global settings
- [ ] Candidate profile preference fields keep their current meaning
- [ ] Missing candidate preferences do not trigger hidden admin-default behavior
- [ ] `applications_count_max` runs before enrichment
- [ ] `max_age_days` runs before enrichment
- [ ] `applications_count=NULL` skips the applicant-count check
- [ ] `published_at=NULL` skips the freshness check
- [ ] Jobs rejected by pre-enrichment global filters are not sent to enrichment
- [ ] Jobs rejected by pre-enrichment global filters are recorded with explicit reject reasons before enrichment is skipped
- [ ] Reject reasons for pre-enrichment global filters still appear in run detail
- [ ] The design defines a cheap pre-LLM pruning phase between vector shortlist generation and AI scoring
- [ ] The design leaves a clear place for future post-enrichment global filters without implementing them now
