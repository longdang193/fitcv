---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-pipeline-identity-and-filter-truth
parent_thread: workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-results-ledger-contract
targets:
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv/pipeline_stages/common.py
  - src/fitcv/rule_filter.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/bq_store.py
  - src/fitcv_cp/store.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_storage_backend_parity.py
related_features:
  - admin_control_plane_core
  - inspection_debugging
related_stages:
  - rule_filter
  - cv_generation
---

# FitCV Pipeline Identity And Filter Truth

## Goal

Define bounded design that makes per-job pipeline truth stable across enrichment, filtering, scoring, ranking, CV generation, results export, and control-plane rendering so operators no longer see silent `Filter`/`Pipeline Outcome` gaps caused by URL drift or storage-mode fallbacks.

## Key Deliverables

### Stable per-job identity contract

Specify one run-scoped identity contract that survives source URL drift, redirect canonicalization, and stage-local field reshaping.

### Full rule-filter truth persistence contract

Specify required persisted row shape and backend parity rules so every enriched job has deterministic filter truth in both BigQuery and sqlite-backed runs.

### Truthful control-plane fallback and diagnostics policy

Specify how control-plane derives, degrades, and surfaces missing truth without silently converting unknown state into pass/accepted state.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current mismatch boundaries across pipeline export, filter persistence, and control-plane joins before finalizing decisions

**Steps:**
- [x] inspect `extract_job_url()` and all pipeline stage maps that key rows by `job_url`
- [x] inspect results-export construction and `unknown_pipeline_state` classification path
- [x] inspect rule-filter persistence path in BigQuery and sqlite modes
- [x] inspect control-plane enriched-tab join/fallback behavior for filter and pipeline outcome columns
- [x] confirm live-run evidence showing enriched rows, filter rows, and results rows diverge in coverage and identity

**Verification:**
- [x] current-state evidence identifies at least three independent failure surfaces: URL identity drift, sqlite filter persistence gap, and sample-only artifact fallback

**Exit Criteria:**
- no core design choice depends on unstated assumptions about how a job is identified or how filter truth is stored

### Wave 2: Decision closure

**Purpose:**
- resolve canonical identity, persistence, and fallback behavior with bounded implementation surface

**Steps:**
- [ ] define canonical run-scoped job identity fields and precedence rules
- [ ] define full rule-filter persistence contract for both BigQuery and sqlite
- [ ] define results-export status derivation behavior when identity mismatches or missing stage evidence occur
- [ ] define control-plane join precedence and operator-facing diagnostics for missing truth
- [ ] define minimal backward-compatible artifact and storage migration expectations

**Verification:**
- [ ] every enriched row state is explainable by one deterministic join path or one explicit diagnostic state

**Exit Criteria:**
- design covers all current bug classes without adding parallel truth systems

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof expectations explicit for implementation handoff

**Steps:**
- [ ] define regression matrix for URL drift, duplicate URLs, sqlite mode, and missing filter rows
- [ ] define backend parity proof between BigQuery and sqlite paths
- [ ] define live-run verification expectations and operator-visible diagnostics checks

**Verification:**
- [ ] validation plan proves truth preservation, parity, and explicit degradation behavior

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: Introduce canonical run-scoped job identity separate from display URL

- context: current pipeline uses `extract_job_url()` string equality as primary identity across raw, enriched, shortlist, ranking, CV, export, and UI joins; source URL often mutates from aggregator URL to destination URL mid-pipeline
- choice: define canonical identity contract with `raw_job_fingerprint` as primary join key when available, `source_job_url` as secondary stable source reference, and `job_url` as display/canonical URL rather than sole identity field
- alternatives considered:
  - continue URL-only joins and add more UI normalization
  - join by title/company heuristics
- impact:
  - eliminates source-vs-destination URL split as primary truth key
  - keeps displayed job URL flexible without breaking downstream joins
  - reduces need for stage-specific patch logic

Required identity fields:
- `raw_job_fingerprint`: primary run-scoped identity for one logical input job
- `source_job_url`: original source URL captured before enrichment/canonical redirects
- `job_url`: current canonical/display URL for downstream links and operator actions

Identity precedence:
1. `raw_job_fingerprint`
2. normalized `source_job_url`
3. normalized `job_url`

### Decision: Persist full rule-filter results for every enriched job in all storage modes

- context: BigQuery path can persist `rule_filter_results`, but sqlite path returns early and persists nothing; control-plane then falls back to samples or synthetic pass/fail guesses
- choice: require full run-scoped `rule_filter_results` persistence in sqlite and BigQuery with identical semantic row shape
- alternatives considered:
  - keep sqlite as degraded mode and derive from results export
  - rely on stage artifacts as source of truth
- impact:
  - removes backend-mode truth split
  - makes filter column deterministic for all enriched rows
  - allows parity testing against one row contract

Required persisted row minima:
- `run_id`
- `raw_job_fingerprint` when available
- `source_job_url`
- `job_url`
- `passed`
- `reasons`
- `marks`
- `filtered_at`

### Decision: Keep stage artifacts as diagnostics/sample surfaces, not canonical truth

- context: `outputs_sample` and `dropped_or_changed_sample` are intentionally samples, but control-plane fallback currently treats them as truth source when persisted rows are absent
- choice: preserve stage-artifact samples for diagnostics only; canonical per-row truth must come from full persisted rows or results export rows keyed by stable identity
- alternatives considered:
  - expand stage artifacts into full row ledger
  - continue sample-based fallback
- impact:
  - keeps artifact payloads bounded
  - avoids dual full-truth ledgers
  - clarifies ownership: artifacts for debugging, store/export for truth

### Decision: Unknown remains unknown; control-plane must not synthesize pass/accepted from missing truth

- context: sqlite fallback currently converts most rows to `passed=True` when `results_export_json` exists, even if `pipeline_status` is unknown or drifted
- choice: require explicit `unknown`/`missing_truth` handling for filter and pipeline outcome surfaces instead of optimistic pass/default mapping
- alternatives considered:
  - continue current synthetic pass/reject derivation
  - hide missing states in UI
- impact:
  - prevents false operator confidence
  - makes root-cause debugging faster
  - preserves correctness over cosmetic completeness

Required degradation rules:
- if canonical filter row missing, `Filter` surface must render explicit unknown state
- if results export row exists but status cannot be resolved, `Pipeline Outcome` must render explicit unknown state with diagnostic detail
- fallback layers may enrich diagnostics but must not overwrite known truth with guessed truth

### Decision: Normalize URL keys in pipeline core only as compatibility aid, not as identity replacement

- context: control-plane already normalizes URLs for UI joins, but pipeline core still uses raw strings; normalization helps compatibility but cannot solve source-to-destination URL swaps
- choice: introduce one shared normalization helper in pipeline core for secondary key matching and storage consistency, while keeping canonical identity contract above it
- alternatives considered:
  - no normalization in core
  - rely on normalization alone as primary identity
- impact:
  - collapses trivial slash/query/case drift
  - avoids conflating URL cleanup with job identity semantics

## Invariants

- One logical enriched job must map to at most one canonical pipeline truth row per run.
- `raw_job_fingerprint` identity, when present, must survive all pipeline stages and storage backends unchanged.
- Source URL drift from aggregator URL to destination URL must not change filter or pipeline outcome truth for same logical job.
- Full rule-filter truth must be available in both BigQuery and sqlite-backed runs for every enriched job that reached rule filter.
- Stage artifacts remain diagnostic/sample surfaces and must not become hidden source of canonical per-row truth.
- Control-plane must never render synthetic pass/accepted state for rows whose filter/pipeline truth is unknown.
- Existing operator link behavior may keep using canonical/display `job_url`; identity and navigation concerns stay separate.

## Acceptance Criteria

1. A run where enriched rows keep Indeed URLs and later stages use destination URLs still renders non-empty `Filter` and `Pipeline Outcome` for matched logical jobs.
2. Same run data produces equivalent enriched-tab filter/outcome surfaces in BigQuery and sqlite modes.
3. If full filter truth is unavailable, UI renders explicit unknown/missing-truth state instead of `passed=True` synthesis.
4. `unknown_pipeline_state` count drops to zero for rows whose downstream truth exists under same logical identity but different URL forms.
5. Duplicate or variant URLs for same logical input do not create multiple conflicting truth rows for one `raw_job_fingerprint`.
6. Stage-artifact samples can be absent or partial without causing empty columns when canonical persisted truth exists.
7. Regression tests cover URL-drift, sample-only artifact presence, sqlite parity, and duplicate-URL edge cases.

## Non-Goals

- No redesign of enriched-tab layout beyond explicit unknown-state messaging required for truthfulness.
- No broad refactor of ranking, CV generation, or HITL review business policy.
- No replacement of `results_export_json` with a new full ledger format unless required as minimal implementation detail in plan.
- No migration of historical runs to retroactively backfill missing per-row truth.
- No title-based fuzzy matching as canonical identity policy.

## Risks and Mitigations

- risk: historical rows lack `raw_job_fingerprint`, forcing compatibility joins.
  - mitigation: define deterministic fallback precedence to normalized `source_job_url`, then normalized `job_url`, with explicit unknown state if still unresolved.
- risk: adding new persisted fields causes backend parity drift.
  - mitigation: define one semantic row contract and add parity tests that compare BigQuery and sqlite outputs field-for-field on normalized fixtures.
- risk: duplicate logical jobs in same run may share same URL but differ by input context.
  - mitigation: make `raw_job_fingerprint` primary identity and keep URL-only joins as compatibility fallback, not authority.
- risk: explicit unknown state may surface more visible warnings short-term.
  - mitigation: treat this as intended truth exposure and include run-level diagnostics to explain missing persisted truth.
- risk: multiple helpers may reimplement normalization/identity logic.
  - mitigation: require one shared helper surface for identity/secondary URL-key derivation across pipeline and control-plane code paths.

## Validation Plan

- proof target: canonical identity survives source-to-destination URL drift
  - method: unit/integration test with same logical job carrying different enriched and downstream URLs
  - evidence: export rows and enriched-tab context show resolved filter/outcome truth for drifted URLs

- proof target: sqlite and BigQuery expose equivalent rule-filter truth
  - method: backend parity test using same rule-filter fixture in both modes
  - evidence: normalized row sets match for `passed`, `reasons`, `marks`, identity fields, and run scoping

- proof target: control-plane does not synthesize pass from missing truth
  - method: render/context test with missing filter rows and `unknown_pipeline_state`
  - evidence: row surfaces explicit unknown state instead of `passed=True`

- proof target: stage-artifact samples remain non-authoritative
  - method: test where artifact samples are partial but persisted truth is complete
  - evidence: UI derives row truth from persisted rows, not sample coverage

- proof target: duplicate URL variants do not create conflicting truth rows
  - method: pipeline/export test with repeated logical job under URL variants and stable fingerprint
  - evidence: one canonical truth row per logical job and deterministic status resolution

- proof target: live-run diagnostics expose missing-truth drift clearly
  - method: inspection or targeted route test of run-level diagnostics payload
  - evidence: counts/diagnostic state identify rows with missing canonical filter or outcome truth

## Completion Criteria

1. All Key Deliverables are finalized and approved.
2. Acceptance criteria map to automated proofs or deterministic inspection outputs.
3. Downstream implementation plan stays bounded to identity, persistence, and truthful degradation surfaces named in `targets`.
4. Spec is ready for handoff to implementation planning without unresolved source-of-truth ambiguity.
