# Design

## Context

The worker already has a validator for per-job ranking-to-CV handoff items, while stage summaries expose both counts and artifacts. Typed diagnostics are normalized centrally, but normalized messages and debug payload fields are not uniformly bounded. Terminal checkpoint construction currently uses one ranking boundary for all technical failures.

## Goals / Non-Goals

**Goals:** Reuse existing handoff validation and stage ordering; preserve source diagnostics into the existing ranking artifact; constrain persisted failure data to safe typed/allowlisted fields; align persisted stage and checkpoint facts with the actual failure.

**Non-Goals:** Change ranking policy, score validity, CV acceptance, provider behavior, or run scheduling; migrate existing stored runs; run another real-data probe.

## Decisions

- Treat explicit failure counters as authoritative before considering the mixed-outcome partial-ranking exception. A continuation decision also requires a structurally complete, fingerprint-valid handoff; a positive count alone is not evidence of a valid boundary.
- Derive `completed_stages`, `last_completed_stage`, and `next_stage` from the ordered pipeline stage list and the actual terminal failure owner. This avoids per-failure hard-coded checkpoints and does not mark failed work complete.
- Keep the existing diagnostic registry and normalization path. Bound free-form text and canonical fact payloads at normalization, and persist only stable typed summaries for generation failures rather than exception/provider payloads.
- Carry scorer diagnostics into the ranking artifact at the existing aggregator boundary, and copy the same safe typed code/reference into failed ranking stage settlement. Clear stale failure fields on successful settlement. Update the generation-stage status/count projection where failure records are already produced.
- Verify with focused unit/integration regressions over summaries and persisted stage artifacts; no external provider or private data is needed.

## Risks / Trade-offs

- [Overly permissive handoff coverage could still resume with mismatched rows] → Validate each handoff item's schema and fingerprint and compare its identities/count with the ranked output.
- [Diagnostic sanitization may reduce forensic detail] → Retain stable code, stage/source, and bounded safe facts; exclude arbitrary messages and payloads.
- [Earlier-stage failures could be marked complete accidentally] → Derive only the successful prefix strictly before the actual failing stage and assert retry boundaries in tests.

## Migration Plan

No data migration is required. Existing persisted checkpoints remain readable; newly terminalized runs use stage-aligned checkpoint metadata. Existing diagnostic readers retain the stable typed fields while oversized or untrusted free-form fields are bounded or omitted.
