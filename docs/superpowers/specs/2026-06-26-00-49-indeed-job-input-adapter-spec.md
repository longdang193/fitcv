---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: indeed-job-input-adapter
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
targets:
  - src/fitcv/ingest.py
  - src/fitcv/contracts.py
  - tests/test_ingest.py
  - tests/test_normalize.py
related_features: []
related_stages: []
---

# Indeed Job Input Adapter Specification

## Goal

Make JOB-PROJECT accept Indeed scraper exports with minimal change by adding one thin input adapter at ingest time. The adapter must translate Indeed records into the same canonical job shape the existing LinkedIn pipeline already expects, so normalize, enrich, rule filter, ranking, and CV generation stay unchanged.

## Key Deliverables

### Canonical Indeed-to-job mapping

Define a deterministic mapping from Indeed records into the current canonical job dict. The adapter must support the live-run light sample in `data/dataset_indeed-jobs-scraper_2026-06-25_23-11-47-317.json` and stay tolerant of small Indeed shape drift such as `description` arriving as either nested object or plain string.

### No downstream contract churn

Keep the existing pipeline contract intact. The enriched, ranked, and generated artifacts should still operate on the same canonical keys used for LinkedIn data.

### Testable compatibility proof

Add unit coverage that proves Indeed input is accepted, normalized, and deduplicated through the shared path without breaking existing LinkedIn fixtures.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm which Indeed fields are needed for current pipeline behavior
- confirm which fields can remain raw-only

**Steps:**
- [x] inspect Indeed sample records against current ingest contract
- [x] identify the minimum field translation needed for canonical job shape
- [x] confirm fields that should stay deferred, especially `attributes`

**Verification:**
- [x] field mapping is explicit for every required canonical key

**Exit Criteria:**
- no downstream stage needs source-specific Indeed branching

### Wave 2: Decision closure

**Purpose:**
- lock adapter shape and reject unnecessary schema expansion

**Steps:**
- [x] define Indeed record detection rule using stable top-level Indeed markers instead of one nested-shape assumption
- [x] define flattened mapping for nested Indeed fields
- [x] define how missing LinkedIn-only fields are represented

**Verification:**
- [x] decision record distinguishes canonical data from raw audit-only data

**Exit Criteria:**
- adapter is thin, source-aware, and bounded

### Wave 3: Validation and approval readiness

**Purpose:**
- make acceptance and regression proof explicit

**Steps:**
- [x] define acceptance tests for Indeed and LinkedIn fixtures
- [x] define regression check for shared dedupe and raw row preparation

**Verification:**
- [x] tests prove Indeed and LinkedIn both flow through same pipeline path

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: Add source adapter inside ingest, not separate pipeline

- context: Indeed and LinkedIn share the same downstream runtime, ranking, and generation needs.
- choice: normalize Indeed at ingest boundary so the rest of pipeline consumes one canonical schema.
- alternatives considered:
  - add a second Indeed-specific pipeline branch
  - teach every downstream stage to handle both schemas
- impact:
  - smallest code change
  - preserves existing stage contracts
  - keeps dedupe and scoring logic source-agnostic

### Decision: Map nested Indeed fields into existing canonical keys

- context: Indeed uses `url`, nested `employer`, nested `location`, and usually `description.text`, but export variants may flatten `description` into a plain string.
- choice: flatten only the fields needed by the canonical job dict and warehouse row shape.
- alternatives considered:
  - preserve nested Indeed structure throughout runtime
  - create new Indeed-only canonical model
- impact:
  - `job_url` comes from Indeed `url`
  - `company_name` and `company_url` come from `employer`
  - `description` comes from `description.text`
  - `published_at` comes from `datePublished`
  - plain-string `description` still maps into canonical `description`
  - location becomes a readable string, not nested object or state code noise

### Decision: Detect Indeed by stable markers, not `description` shape

- context: current sample uses nested `description.text`, but future scraper variants may emit a plain string while keeping other Indeed markers stable.
- choice: detect Indeed using top-level markers such as `url`, `dateOnIndeed`, `employer`, and `jobTypes`, without requiring `description` to be a dict.
- alternatives considered:
  - require `description.text` shape as Indeed proof
  - accept silent fallback into LinkedIn mapping when shape drifts
- impact:
  - smaller compatibility risk across Indeed export variants
  - still keeps adapter thin and source-local

### Decision: Defer `attributes` normalization

- context: Indeed `attributes` is a noisy key/value bag that may contain useful hints but is not yet a stable canonical skill source.
- choice: keep `attributes` in raw JSON only for now.
- alternatives considered:
  - map attributes into skills immediately
  - expose attributes as first-class canonical output
- impact:
  - avoids premature schema expansion
  - keeps adapter focused on required runtime compatibility
  - leaves room for later enrichment experiments

## Invariants

- Canonical pipeline input remains a flat job dict with `job_url` as primary key.
- LinkedIn input behavior must remain unchanged.
- Indeed records must produce the same downstream canonical keys used by existing stages.
- `description.text` is the authoritative Indeed description source for canonical `description`.
- If Indeed `description` arrives as plain string, adapter still treats record as Indeed and uses that string as canonical `description`.
- `attributes` must not become a required downstream field in this change.
- No new source-specific branch is allowed inside normalize, enrich, ranking, or CV generation.

## Validation Plan

- proof target: live-run light Indeed dataset is accepted as input
  - method: smoke test plus unit coverage
  - evidence: `parse_jobs_file`, `prepare_raw_rows`, and `normalize_batch` accept `data/dataset_indeed-jobs-scraper_2026-06-25_23-11-47-317.json`

- proof target: nested Indeed fields are mapped correctly
  - method: unit test
  - evidence: `url -> job_url`, `employer.name -> company_name`, `employer.companyPageUrl -> company_url`, `description.text -> description`

- proof target: Indeed detection survives minor schema drift
  - method: unit test
  - evidence: record with plain-string `description` still routes through Indeed adapter and keeps `url -> job_url`

- proof target: shared normalization still works
  - method: unit test
  - evidence: `normalize_batch` accepts adapted Indeed rows and deduplicates by canonical `job_url`

- proof target: LinkedIn regression stays intact
  - method: unit test comparison against existing sample fixture
  - evidence: existing LinkedIn tests still pass without fixture changes

- proof target: raw audit payload preserved
  - method: inspection test
  - evidence: original Indeed JSON remains serialized in `raw_json`

## Acceptance Criteria

- Light Indeed sample file can be ingested without manual pre-conversion.
- Canonical output rows from Indeed have the same required keys as LinkedIn rows.
- `description.text` becomes canonical `description`.
- Plain-string Indeed `description` still becomes canonical `description`.
- `attributes` stays raw-only for this release.
- Existing LinkedIn tests continue to pass.
- No downstream stage requires special-casing for Indeed source shape.
- Location text should not surface raw state/admin codes when cleaner text is already available.

## Non-Goals

- Do not add a second pipeline.
- Do not redesign the canonical job schema.
- Do not promote `attributes` into skills in this change.
- Do not normalize HTML description content.
- Do not change enrichment, scoring, or CV generation logic.

## Risks and Mitigations

### Risk: Indeed records have inconsistent nested shape

- mitigation: adapter must use stable top-level detection markers, safe fallbacks, and keep raw JSON intact for audit/debug

### Risk: Fields like `attributes` tempt schema creep

- mitigation: keep them raw-only and explicitly defer skill extraction

### Risk: LinkedIn assumptions leak into new adapter

- mitigation: keep adapter boundary narrow and verify old fixture still passes unchanged

## Completion Criteria

A specification item is complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
