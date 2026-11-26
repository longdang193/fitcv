# Proposal

## Why

Enrichment currently accepts any structurally parseable extraction for the `enrich_extraction` route, maintains a separate seniority vocabulary from downstream screening, and lets one item-level future failure abort the whole batch. These boundaries can produce misleading `fresh_enrichment` rows, inconsistent screening inputs, and avoidable batch-wide loss even when other jobs are recoverable.

This change hardens enrichment at its existing trust and failure boundaries without turning missing fit context into a hard rejection. The existing `requirement-aware-job-shortlisting` behavior remains authoritative: missing, uncertain, or inferred fit metadata stays inspectable and diagnostic unless a confirmed hard constraint fails.

## What Changes

- Add task-specific response-contract checks so a provider response is marked as fresh enrichment only when it matches the requested enrichment task and can be safely associated with the input job.
- Use one canonical seniority taxonomy and alias-normalization path for enrichment and screening; preserve raw values and normalization diagnostics for auditability.
- Isolate recoverable per-job enrichment failures so one failed item produces a diagnostic/fallback row and does not cancel unrelated jobs in the same batch.
- Keep global provider, configuration, persistence, and explicit-cancellation failures fatal to the batch.
- Preserve compatibility with reusable cached enrichment and existing fallback rows; do not require every fit-context field or add extra LLM calls.

## Capabilities

### New Capabilities

- `enrichment-context-contract`: Validate enrichment task identity and normalization, and define item-level versus batch-level enrichment failure boundaries.

### Modified Capabilities

<!-- Existing maintained shortlist requirements are intentionally not modified here. -->

## Impact

- `src/fitcv/enrich.py`: response-contract validation, seniority normalization, and batch failure isolation.
- Existing taxonomy/configuration sources and screening consumers: one shared seniority vocabulary and alias mapping, without changing the current hard-versus-uncertain shortlist policy.
- Enrichment persistence and diagnostics: fresh, cached, and fallback provenance must remain distinguishable and item-level failures must be queryable.
- Tests and fixtures covering response identity, seniority aliases, recoverable item failures, fatal batch failures, cached reuse, and fallback behavior.
