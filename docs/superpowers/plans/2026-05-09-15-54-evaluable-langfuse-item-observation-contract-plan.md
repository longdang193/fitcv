---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: evaluable-langfuse-item-observation-contract
parent_thread: workstream-agentic-observability.agentic-observability-provider-provenance
parent_spec: docs/superpowers/specs/2026-05-04-langfuse-rich-input-output-observability-spec.md
targets:
  - docs/observability.md
  - docs/pipeline.md
  - src/fitcv/telemetry.py
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/reporter.py
  - src/fitcv_cp/worker_job.py
  - tests/test_fitcv/test_telemetry.py
  - tests/test_fitcv_cp/test_reporter.py
  - tests/test_pipeline.py
related_stages:
  - cv_analysis
  - cv_generation
---

# 2026-05-09 Evaluable Langfuse Item Observation Contract Plan

## Goal

Implement Wave 1 of evaluable Langfuse item observation contract so FitCV preserves existing run-level operational telemetry while adding bounded, reviewable `cv_analysis_item` and `cv_generation_item` observations with stable schema, lineage, retry, redaction, and reviewer-first rendered input/output semantics.

## Key Deliverables

### Shared item-observation telemetry helpers

Add shared telemetry helpers that build canonical observation envelopes, apply schema and redaction versions, enforce payload caps, render human-readable markdown/text for Langfuse `input` and `output`, preserve structured backing metadata for filtering and automation, and attach correlation, retry, fallback, and provider metadata without breaking current disabled or degraded telemetry behavior.

### Truthful `cv_analysis_item` and `cv_generation_item` emission

Patch nearest truthful analysis and generation boundaries so each candidate-job attempt emits one item-level Langfuse generation with reviewer-readable rendered input/output, required structured metadata, and parent-child lineage while keeping run-summary telemetry unchanged.

### Verification and doc alignment

Add focused tests and doc updates proving rendered readability, payload shape, caps, lineage, and backward-compatible run-summary behavior, then complete one live Langfuse verification pass showing nested evaluable item observations beneath existing run trace.

## Task Breakdown

### task 1: Source-first boundary confirmation and scope lock

**Files:**
- Inspect: `src/fitcv/telemetry.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/agentic_cv_analysis.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`
- Inspect: `src/fitcv_cp/worker_job.py`
- Inspect: `src/fitcv_cp/reporter.py`
- Inspect tests: `tests/test_fitcv/test_telemetry.py`, `tests/test_fitcv_cp/test_reporter.py`, `tests/test_pipeline.py`

- [ ] Step 1: Confirm exact current run-trace, stage-summary, and Langfuse/OTel helper ownership before editing any symbol.
- [ ] Step 2: Identify truthful attempt boundaries for `cv_analysis` and `cv_generation`, including where retries, reuse, fallback, validation, and final disposition are currently known.
- [ ] Step 3: Decide Wave 1 reuse shape from spec options and record it in implementation notes before code changes so all reused-analysis cases stay consistent.
- [ ] Step 4: Confirm whether docs `docs/observability.md` and `docs/pipeline.md` already describe current summary-only behavior and note exact sections needing update.
- [ ] Step 5: Confirm reviewer-facing rendered shape for Langfuse `input` and `output` at both analysis and generation boundaries before helper implementation starts.

### task 2: Shared observation envelope, bounding, rendering, and serialization helpers

**Files:**
- Modify: `src/fitcv/telemetry.py`
- Modify/Add tests: `tests/test_fitcv/test_telemetry.py`

- [ ] Step 1: Add canonical helper(s) for item observation envelope fields: `observation_type`, `schema_version`, `redaction_version`, `run_id`, `candidate_id`, `job_id`, `attempt_id`, `attempt_index`, `selected`, `parent_observation_id`, `provider`, `model`, `fallback_used`, `fallback_reason`, `input`, `output`, `metadata`.
- [ ] Step 2: Add bounded redaction helper(s) for excerpts, lists, markdown bodies, issue lists, and truncation markers using spec caps.
- [ ] Step 3: Add renderer helper(s) that transform bounded structured data into reviewer-readable markdown/text for Langfuse `input` and `output` fields.
- [ ] Step 4: Preserve structured backing objects under metadata so filtering, joins, and future evaluator automation do not depend on parsing rendered markdown.
- [ ] Step 5: Add helpers to omit `None`, normalize booleans/attempt metadata, and assemble Langfuse-recognized observation attributes without leaking forbidden classes.
- [ ] Step 6: Preserve non-blocking behavior when telemetry is disabled, exporter is degraded, or bounded payload construction fails.

### task 3: `cv_analysis_item` observation emission

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify/Add tests: `tests/test_pipeline.py` and/or focused analysis coverage if present

- [ ] Step 1: Patch truthful analysis attempt boundary to emit one `cv_analysis_item` Langfuse generation per candidate-job attempt.
- [ ] Step 2: Populate bounded structured input fields: job identity/excerpts, candidate excerpts, instructions, rubric, and analysis context refs.
- [ ] Step 3: Render reviewer-facing Langfuse `input` from those bounded structured fields using spec-defined section layout.
- [ ] Step 4: Populate bounded structured output fields: `fit_decision`, `fit_score`, `reasoning_summary`, `evidence`, `risks`, and `generation_readiness`.
- [ ] Step 5: Render reviewer-facing Langfuse `output` so fit quality is readable without opening raw JSON.
- [ ] Step 6: Populate metadata for prompt version, ranking fit label, reuse status, deterministic gate result, token usage, cost, and retry/fallback semantics.
- [ ] Step 7: Ensure blocked, reused, retried, and fallback-fresh analysis paths remain distinguishable without reading full stage artifact.

### task 4: `cv_generation_item` observation emission

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify/Add tests: `tests/test_pipeline.py` and/or focused generation coverage if present

- [ ] Step 1: Patch truthful generation attempt boundary to emit one `cv_generation_item` Langfuse generation per candidate-job attempt.
- [ ] Step 2: Populate bounded structured input fields: job excerpts, candidate excerpts, analysis context, generation instructions, and template version.
- [ ] Step 3: Render reviewer-facing Langfuse `input` so reviewer can quickly inspect target job, candidate, and generation context.
- [ ] Step 4: Populate bounded structured output fields: `generated_cv_markdown`, `structured_sections`, `validation`, and `final_disposition`.
- [ ] Step 5: Render reviewer-facing Langfuse `output` so generated CV and validation/disposition are readable without nested JSON decoding.
- [ ] Step 6: Link generation observations back to analysis observation lineage through `parent_observation_id` or equivalent stable field.
- [ ] Step 7: Ensure validation failure, generation failure, persistence failure, retry, and selected-final-attempt semantics remain inspectable at observation level.

### task 5: Run-summary boundary preservation and supplemental lane containment

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Inspect/Modify if needed: `src/fitcv_cp/reporter.py`
- Inspect/Modify if needed: `src/fitcv_cp/worker_job.py`
- Modify/Add tests: `tests/test_fitcv_cp/test_reporter.py`, `tests/test_pipeline.py`

- [ ] Step 1: Verify `pipeline_complete` and other Layer 1 run-summary payloads remain aggregate-only and do not start shadow-storing item-level raw IO.
- [ ] Step 2: Check whether new nested item observations conflict with any existing reporter-side Langfuse native ingestion or naming/session semantics.
- [ ] Step 3: Apply only minimal reporter or worker-job alignment changes required to avoid duplicate or conflicting trace semantics while preserving current run detail and health surfaces.

### task 6: Docs alignment and focused verification

**Files:**
- Modify: `docs/observability.md`
- Modify: `docs/pipeline.md`
- Verify against modified code and tests above

- [ ] Step 1: Update docs to describe two-layer observability model, Wave 1 item observations, reviewer-first rendered Langfuse fields, bounded payload policy, and run-summary vs item-quality responsibilities.
- [ ] Step 2: Add or update focused tests for schema presence, rendered readability, payload caps, truncation markers, retry semantics, fallback flags, and parent-child lineage.
- [ ] Step 3: Run focused automated verification for telemetry, reporter, and pipeline surfaces touched by the patch.
- [ ] Step 4: Run one local Langfuse validation pass and confirm same run trace now contains reviewable `cv_analysis_item` and `cv_generation_item` generations with readable rendered input/output plus structured backing metadata.
- [ ] Step 5: Capture any deferred Wave 2 need, such as `acceptance_review_item` or evaluator/export work, as explicit follow-up rather than widening Wave 1 scope.

## Verification

```powershell
python -m pytest tests/test_fitcv/test_telemetry.py -q
python -m pytest tests/test_fitcv_cp/test_reporter.py -q
python -m pytest tests/test_pipeline.py -q -k "cv_analysis or cv_generation or telemetry or langfuse"
python scripts/validate_template_required_sections.py
python scripts/validate_planning_lifecycle.py --strict
python scripts/validate_repo_contracts.py --fast
```

Optional live verification lane:

```powershell
# start local FitCV surfaces and local Langfuse runtime
# execute one run with Langfuse enabled
# verify run trace still shows Layer 1 summary surfaces
# verify cv_analysis_item and cv_generation_item appear as nested generations
# verify Langfuse input/output are reviewer-readable markdown/text rather than JSON-first blobs
# verify one bad or weak-fit item is reviewable from rendered input/output alone
```

## Deferred Wave 2 Follow-Up Capture

The following work is intentionally deferred so Wave 1 stays bounded around
`cv_analysis_item` and `cv_generation_item` truth surfaces:

1. **Acceptance-review observation lane**
   - evaluate whether final acceptance deserves a separate `acceptance_review_item`
     observation once review path semantics are finalized
   - keep Wave 1 scoped to analysis/generation attempt truth rather than adding a
     third item contract now
2. **Evaluator/export follow-up**
   - define downstream evaluator-ready export shape that consumes structured item
     metadata without reparsing rendered markdown
   - decide whether evaluator/export work belongs in Langfuse export tooling,
     offline dataset generation, or both
3. **True full pipeline live pass**
   - keep future full live pipeline validation as a separate follow-up lane
   - use API-key-preferred model auth where supported, but treat BigQuery/data-plane
     runtime eligibility as separate from Wave 1 observability contract closure

These are explicit follow-ups, not open Wave 1 blockers.

## Completion Criteria

A plan item is considered complete when:

1. shared telemetry helpers emit canonical Wave 1 item observation envelope and enforce spec-defined payload bounds,
2. truthful `cv_analysis_item` and `cv_generation_item` observations are emitted for candidate-job attempts with stable lineage, retry, and fallback semantics,
3. Layer 1 run-summary telemetry remains intact and separate from item-level reviewable IO,
4. focused tests and repo planning/contract validation pass,
5. one live Langfuse verification pass confirms nested evaluable item observations beneath existing run trace,
6. deferred Wave 2 work is captured explicitly instead of leaking into Wave 1 implementation.
