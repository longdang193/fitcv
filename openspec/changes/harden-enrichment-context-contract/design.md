# Design

## Context

See `proposal.md` for motivation and `specs/enrichment-context-contract/spec.md` for the behavioral contract. The current implementation already has typed `LlmRuntimeFailure`/`LlmRuntimeProvenance`, enrichment contract fingerprints, cached-row reuse, fallback rows, and a configured seniority ladder used by screening. The main gaps are that enrichment owns a second accepted-seniority set, task provenance is not used as a freshness gate, and `enrich_batch()` propagates the first worker exception through `future.result()`.

## Goals / Non-Goals

**Goals:**

- Make freshness depend on the existing runtime routing provenance and enrichment-specific parsed contract.
- Make the configured seniority ladder and alias map the single normalization source for enrichment and screening.
- Continue independent jobs after recoverable item-scoped failures while preserving input order and per-job diagnostics.
- Keep cached reuse, fallback rows, continuation, and existing hard-versus-uncertain shortlist behavior compatible.

**Non-Goals:**

- Do not require every fit-context field or turn missing fit context into a rejection.
- Do not add another LLM call, a second enrichment service, or a new persistence layer.
- Do not change ranking, shortlist promotion, title/contract/domain policy, or export acceptance rules.
- Do not silently convert cancellation, shared configuration/routing errors, database errors, or other global failures into item fallbacks.

## Decisions

### 1. Gate freshness at the enrichment boundary

Validate the completed result at the existing enrichment result-to-row boundary. Require the parsed enrichment contract to be valid and require runtime provenance to identify the same `enrich_extraction` routing part requested by the caller. Preserve the existing request and contract fingerprints in the row. A provenance mismatch becomes a typed item diagnostic/fallback and cannot be labeled `fresh_enrichment`.

**Alternative rejected:** validating only generic JSON shape. It cannot distinguish a response delivered under another routing task and is the defect being addressed.

### 2. Reuse the configured seniority taxonomy

Use the existing `seniority.ladder` and `seniority.aliases` configuration already consumed by screening as the canonical owner. Enrichment normalization should resolve aliases through that same policy, preserve `seniority_raw`, and emit an unknown/invalid normalization diagnostic when resolution fails. Keep any legacy `valid_seniority_enrich` input as a compatibility projection only; it must not become a competing taxonomy.

**Alternative rejected:** expanding the enrichment-only set. That preserves the split-brain behavior and can make screening and enrichment disagree about the same job.

### 3. Classify failures by scope, not by message text

Use the existing typed failure stage/code/retryability and explicit cancellation/configuration boundaries. An item-scoped parse, validation, or known recoverable provider failure may exhaust into the existing fallback row and continue. Shared routing/configuration, persistence/database, cancellation, and other non-item-scoped failures abort the batch. Each fallback retains its own failure code, stage, attempts, and runtime observation.

**Alternative rejected:** catching every `future.result()` exception and continuing. That would hide global failures and could report an unreliable batch as successful.

### 4. Preserve provenance states during reuse and continuation

Keep `fresh_enrichment`, `reused_cached_enrichment`, and fallback status mutually distinguishable. Cached rows remain eligible only when their existing raw-job and enrichment-contract fingerprints match. Fallback rows remain inspectable and resumable but are never promoted to successful fresh enrichment by continuation alone.

**Alternative rejected:** collapsing all non-fresh outcomes into one status. Operators would lose the ability to tell stale reuse from a failed new attempt.

## Risks / Trade-offs

- [Risk] A provider may return a structurally valid payload with semantically weak fit context. → Keep partial rows usable, record missing/uncertain diagnostics, and rely on the existing shortlist policy rather than making completeness a hard gate.
- [Risk] Existing deployments may still provide the legacy enrichment seniority list. → Read it only through an explicit compatibility path and test that the canonical ladder remains authoritative.
- [Risk] Failure classification can be wrong if a provider error lacks scope metadata. → Default ambiguous failures to batch-fatal instead of silently continuing; add focused tests for item-scoped versus global failures.
- [Risk] Continuing item failures changes batch counts and operator expectations. → Preserve per-item diagnostics, input ordering, and aggregate counters in existing stage observations.

## Migration Plan

1. Add contract, taxonomy, and failure-isolation tests before changing behavior.
2. Implement the smallest changes in the enrichment boundary and batch coordinator, keeping existing persisted status names and fingerprints.
3. Run focused enrichment/runtime/rule-filter tests, then the project backend verification suite.
4. Roll back by reverting the enrichment boundary/coordinator change; cached and persisted rows remain readable because no destructive migration is required.

## Open Questions

- None that change the contract or implementation approach. The exact diagnostic code names can follow the repository's existing failure-code registry during implementation.
