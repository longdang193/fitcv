# Design

## Context

The issue review reports a 15-job CV-generation run with zero persisted CV versions, but the captured issue evidence does not identify whether generation, validation, conversion, or persistence rejected the output. Existing lifecycle and typed-diagnostic paths are already the source of truth, and nearby OpenSpec changes explicitly avoid a broad real-data rerun.

## Goals / Non-Goals

**Goals:**

- Follow one representative attempt across the existing generation, validation, conversion, and persistence boundaries.
- Identify the first authoritative rejecting boundary and preserve its typed outcome.
- Produce a focused regression or reproducible diagnostic probe using local or synthetic inputs.

**Non-Goals:**

- Do not redesign CV generation or persistence.
- Do not relax evidence, content, PDF, privacy, or acceptance gates.
- Do not add a diagnostic service, change provider or retry policy, or rerun the full real-data batch.

## Decisions

- Start from the persisted non-persistable outcome and trace backward through existing lifecycle records, rather than guessing from the issue summary. This preserves the current authority model.
- Use one representative controlled input before any broader probe. A larger batch adds cost and can hide a shared guard without improving diagnosis.
- Reuse the existing typed diagnostic registry and bounded persistence projections. Do not store raw prompts, profile/CV content, credentials, provider responses, or unbounded exception text.
- If the failure is a legitimate validation or artifact rejection, record it as such and add only the narrow regression needed to preserve that contract. If it is a persistence defect, fix the boundary and verify that accepted evidence remains recoverable.
- Keep investigation evidence separate from accepted CV artifacts and private run data.

## Risks / Trade-offs

- [A local reproduction may differ from the original provider or environment] -> Record the covered boundaries and exact controlled inputs; do not infer an unverified root cause.
- [A narrow regression may miss another failure mode] -> Limit the change to the demonstrated boundary and leave broader coverage for a separately justified change.
- [Diagnostic evidence may expose sensitive content] -> Assert bounded allowlisted fields and inspect persisted output for excluded payloads.

## Migration Plan

No migration is required. Existing records remain readable, and any implementation fix must use current compatibility projections and persistence contracts.


## Investigation Evidence

A controlled synthetic reproduction was run on 2026-11-28 with the existing pipeline test `test_run_pipeline_emits_cv_generation_item_observation_for_generation_failed` and a provider/runtime failure containing bounded and sensitive diagnostic fields.

- Generation boundary: exercised; the runtime returned a typed adapter failure (`adapter_http_error`, HTTP 400), and the pipeline projected the authoritative outcome as `stage=generation`, `code=generation_failed`.
- Validation boundary: not reached because generation rejected before a candidate artifact existed.
- Conversion boundary: not reached because generation rejected before Markdown/PDF conversion.
- Persistence boundary: blocked; `PipelineStore.store_cv_version` was not called, and no CV version was promoted.
- Diagnostic boundary: the persisted/observed diagnostic retained only bounded `status` and `request_id` provider fields plus a 16-character diagnostic reference; raw body, credentials, provider secrets, prompts, profile/CV content, and unbounded exception text were absent.
- Primary outcome: the generation rejection remained the authoritative result. The existing persistence-failure transition test separately confirms that an accepted artifact is preserved while a later persistence failure is typed as `persistence_failed`.

The reproduction did not demonstrate a source defect, so no production correction or broad real-data rerun is warranted by this change. The smallest useful correction is focused regression coverage for the no-promotion assertion.

## Verification

- Focused regression command: `python -m pytest -q tests/test_pipeline.py::test_run_pipeline_emits_cv_generation_item_observation_for_validation_failed tests/test_pipeline.py::test_run_pipeline_emits_cv_generation_item_observation_for_persistence_failed tests/test_pipeline.py::test_run_pipeline_emits_cv_generation_item_observation_for_generation_failed tests/test_pipeline_agentic_late_stage.py::test_persistence_failure_transition_preserves_accepted_artifacts tests/test_pipeline_agentic_late_stage.py::test_pdf_converter_failure_is_technical_and_preserves_markdown tests/test_pipeline_agentic_late_stage.py::test_render_unavailable_is_technical_pdf_failure_and_preserves_markdown tests/test_fitcv_cp/test_sqlite_store.py::test_persist_pipeline_snapshot_preserves_bounded_failure_diagnostic tests/test_fitcv_cp/test_worker_job.py::test_build_cv_generation_debug_payload_sanitizes_failure_diagnostics` -> 8 passed.
- Strict OpenSpec validation: `openspec validate investigate-cv-generation-persistability --type change --strict --no-interactive` -> passed.
- No inability to reproduce was encountered; the controlled reproduction completed without a broad real-data rerun.
