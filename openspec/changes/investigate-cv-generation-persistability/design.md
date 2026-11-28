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
