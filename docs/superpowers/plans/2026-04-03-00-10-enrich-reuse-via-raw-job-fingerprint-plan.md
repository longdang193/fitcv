---
feature_type: modify
feature_name: pipeline_performance
status: completed
summary: "Implement enrich-result reuse using a stable normalized raw-job fingerprint plus enrich-contract fingerprint so repeated runs can skip redundant LLM enrichment safely."
invariants:
  - "Reuse must be decided before the enrich LLM call using normalized raw inputs."
  - "Reuse remains valid only when both the raw-job fingerprint and enrich-contract fingerprint match."
  - "Run-scoped enriched outputs must preserve reuse-versus-fresh provenance for debugging."
  - "Disabling reuse must always fall back cleanly to the existing always-enrich path."
---

# Enrich Reuse Via Raw-Job Fingerprint Plan

## Triage

Feature type: MODIFY
Summary: Add fingerprint-based enrichment reuse so repeated normalized jobs can skip redundant LLM extraction while preserving enrich contract safety and inspection visibility.
Reasoning: The enrich stage already normalizes jobs first, already persists shared structured rows, and already exposes enrich-stage artifacts. The missing capability is a safe pre-enrichment reuse decision keyed by normalized raw inputs plus enrich contract provenance. This is a performance and cost optimization of existing enrich behavior.
Invariants:
- Reuse decisions happen before enrich-model invocation.
- Reuse must use normalized raw-job inputs, not enriched output text.
- Enrich contract changes must invalidate reuse automatically.
- Reused rows must remain visible as reused in run-scoped inspection/output surfaces.
Dependencies:
- `pipeline_performance`
- `inspection_debugging`
- enrich runtime in `src/fitcv/enrich.py`
- enrich-stage orchestration in `src/fitcv/pipeline.py`
- shared persistence in `structured_jobs` and `run_structured_jobs`
Affected stages:
- enrich
Affected features:
- pipeline_performance
- inspection_debugging
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/pipeline_performance/pipeline_performance.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/pipeline_performance/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
Generated refresh required: yes
Spec needed: no
Plan needed: yes
Rollback trigger: reuse returns stale enrich rows after prompt/model/schema changes or produces confusing provenance in inspection surfaces
Rollback method: disable fingerprint-based reuse and fall back to the current always-enrich path while keeping additive fingerprint columns inert
Migration needed: yes
Risk level: medium

## Scope

This plan implements [2026-04-02-23-55-enrich-reuse-via-raw-job-fingerprint-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Enrich/docs/superpowers/specs/2026-04-02-23-55-enrich-reuse-via-raw-job-fingerprint-spec.md).

In scope:

- stable raw-job fingerprint generation from normalized raw job rows
- enrich-contract fingerprint generation from effective prompt/model/schema contract inputs
- pre-enrichment lookup in `structured_jobs`
- skipping enrich LLM calls on exact reuse hits
- persistence of reuse provenance into shared and run-scoped enriched rows
- enrich-stage artifact and inspection visibility for reuse/fresh behavior

Out of scope:

- approximate reuse by URL only
- cross-URL reuse
- embedding reuse in shortlist
- redesigning the enrich prompt/schema itself

## Implementation Tasks

### Task 1: Define the raw-job fingerprint contract

Add one code-owned function that projects a normalized raw job into a stable fingerprint payload and hash.

Requirements:

- include only stable pre-enrichment fields
- exclude volatile scrape/runtime metadata
- normalize strings consistently
- serialize deterministically
- return both:
  - a machine-stable fingerprint
  - a testable intermediate payload shape if needed

Recommended input candidates:

- `job_url`
- `title`
- `company`
- `location`
- `description_cleaned`
- `employment_type`
- `experience_level`
- `source`

Deliverables:

- fingerprint helper implementation
- deterministic unit tests

### Task 2: Define the enrich-contract fingerprint

Add one code-owned function that hashes the effective enrich contract used for this run.

Requirements:

- include enrich prompt provenance
- include enrich model
- include enrich response schema / parsing contract version
- include relevant post-processing contract version where needed
- remain stable for identical enrich behavior

Deliverables:

- enrich-contract fingerprint helper
- tests proving contract changes invalidate the fingerprint

### Task 3: Extend enrich persistence schemas with reuse fields

Add the minimum schema support needed to persist fingerprint and reuse provenance.

Requirements:

- add `raw_job_fingerprint`
- add `enrich_contract_fingerprint`
- add `enrich_reuse_status`
- optionally add reuse provenance helpers like `reused_from_enriched_at` if justified

Likely touchpoints:

- `src/fitcv/enrich.py`
- BigQuery DDL assets for `structured_jobs` and `run_structured_jobs`
- migration script(s)

### Task 4: Implement structured-jobs reuse lookup before LLM enrichment

Wire the pipeline so normalized jobs can reuse existing enriched rows on exact match.

Requirements:

- compute both fingerprints before enrich
- look up candidate shared rows in `structured_jobs`
- reuse only when:
  - `job_url` matches
  - `raw_job_fingerprint` matches
  - `enrich_contract_fingerprint` matches
- call the enrich LLM only for misses
- merge reused rows back into the same enrich output contract shape as fresh rows

Important constraint:

- the downstream enrich output shape must not depend on whether a row was reused or freshly enriched

### Task 5: Persist run-scoped reuse provenance

Make sure `run_structured_jobs` and any run-scoped enrich outputs carry reuse/fresh provenance.

Requirements:

- reused rows should say `reused_cached_enrichment`
- fresh rows should say `fresh_enrichment`
- the run-scoped row contract should remain parseable by existing inspection readers

### Task 6: Expand enrich-stage diagnostics and inspection surfaces

Expose reuse behavior clearly in stage artifacts and run detail.

Requirements:

- enrich stage decision summary should report:
  - reused row count
  - fresh row count
  - total enriched row count
- enrich sample rows should include reuse provenance fields when present
- inspection readers should parse and display the new fields cleanly

Likely touchpoints:

- `src/fitcv/pipeline.py`
- `src/fitcv_cp/bq_store.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`

### Task 7: Sync source-of-truth docs and generated discovery

Update docs once the runtime behavior is in place.

Required updates:

- `docs/features/pipeline_performance/pipeline_performance.yaml`
- `docs/features/pipeline_performance/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/stages/enrich.yaml`
- `docs/FitCV-pipeline.md`

Generated refresh:

- regenerate `docs/generated/feature_overview.md`

## Verification Plan

### Unit and contract tests

- raw-job fingerprint determinism tests
- enrich-contract fingerprint invalidation tests
- enrich reuse lookup tests:
  - exact fingerprint + contract match -> reuse
  - raw-job mismatch -> fresh enrich
  - contract mismatch -> fresh enrich
- persistence mapping tests for new reuse provenance fields
- enrich artifact tests for reuse/fresh counts and sample visibility

### Regression checks

- always-enrich behavior remains the fallback when no reuse hit exists
- downstream rule-filter/ranking consumers receive identical enrich contract shape for reused and fresh rows
- manual staged runs still pause/resume cleanly when enrich outputs include reuse provenance

## Execution Order

1. Define raw-job fingerprint contract and tests.
2. Define enrich-contract fingerprint and tests.
3. Extend persistence schemas and mappings.
4. Add reuse lookup before enrich calls.
5. Persist run-scoped reuse provenance.
6. Expand enrich diagnostics and inspection.
7. Sync docs and generated discovery.

## Risks and Notes

- The biggest correctness risk is under-hashing raw jobs and reusing stale enrich output.
- The biggest effectiveness risk is over-hashing raw jobs so reuse almost never triggers.
- The most important guardrail is enrich-contract fingerprinting; prompt/model/schema drift must invalidate reuse automatically.

## Task Status

- [x] Task 1: Define the raw-job fingerprint contract
- [x] Task 2: Define the enrich-contract fingerprint
- [x] Task 3: Extend enrich persistence schemas with reuse fields
- [x] Task 4: Implement structured-jobs reuse lookup before LLM enrichment
- [x] Task 5: Persist run-scoped reuse provenance
- [x] Task 6: Expand enrich-stage diagnostics and inspection surfaces
- [x] Task 7: Sync source-of-truth docs and generated discovery

## Verification Status

- [x] Focused enrich fingerprint/reuse tests passed:
  - `.worktrees\\Enrich\\tests\\test_enrich.py -k "fingerprint or reusable"` -> `3 passed`
- [x] Focused pipeline reuse tests passed:
  - `.worktrees\\Enrich\\tests\\test_pipeline.py -k "reuse or enrich_summary_reports_reuse_counts"` -> `2 passed`
- [x] Regression pipeline slice passed:
  - `.worktrees\\Enrich\\tests\\test_pipeline.py -k "manual_pause_after_enrich or passes_enriched_shortlist_rows_to_ai_scoring or layer4_uses_enriched_job_fields_for_gap_and_debug or calls_load_run_structured_jobs or forwards_enrichment_parallelism"` -> `5 passed`
- [x] Broader targeted suite passed:
  - `.worktrees\\Enrich\\tests\\test_enrich.py .worktrees\\Enrich\\tests\\test_pipeline.py .worktrees\\Enrich\\tests\\test_fitcv_cp\\test_bq_store.py -k "enrich or fingerprint or reusable or run_structured_jobs or stage_transition_artifacts"` -> `78 passed, 73 deselected`
