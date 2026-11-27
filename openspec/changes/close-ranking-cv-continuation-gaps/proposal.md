# Proposal

## Why

The completed ranking/generation hardening change closes the original partial-ranking and typed-diagnostic gaps, but the follow-up review found remaining lifecycle holes at the ranking-to-CV continuation boundary. Explicit stage failure codes can still be bypassed by a recoverable partial result, continuation may be exposed before required checkpoint state is durable, and persisted diagnostic/status projections are not consistently safe or truthful.

These gaps should be specified before another real-data probe so recovery cannot skip failed work, observability cannot expose private provider or application data, and secondary finalization errors cannot hide the primary technical failure.

## What Changes

- Give explicit stage-level failure codes precedence over the recoverable partial-ranking exception.
- Make the ranking-to-CV handoff validation and selected-identity correspondence authoritative at every continuation boundary.
- Gate public continuation on durable persistence of the required checkpoint and handoff; keep optional telemetry best effort.
- Preserve the actual owning failure stage and retry boundary through finalization.
- Persist only bounded, allowlisted typed diagnostics and project the resolved lifecycle status consistently for generation and PDF outcomes.
- Prefer blocking diagnostics when selecting the primary failure while retaining nonblocking warnings as secondary context.
- Keep score-validity behavior and existing optional partial-ranking behavior unchanged when the required handoff is valid.

## Capabilities

### New Capabilities

- `ranking-cv-continuation-integrity`: Defines authoritative failure precedence, handoff correspondence, durable continuation gating, and stage-aligned retry checkpoints.
- `pipeline-lifecycle-diagnostics`: Defines privacy-safe diagnostic persistence, primary-diagnostic selection, lifecycle status projection, and primary/secondary finalization outcomes.

### Modified Capabilities

None. The repository currently has no canonical specs under `openspec/specs`; these are follow-up capabilities derived from the reviewed change contracts.

## Impact

Worker stage classification, ranking-to-CV transition, checkpoint and stage-artifact persistence, diagnostic normalization/projection, generation and PDF outcome mapping, and focused worker/contract/persistence tests. No new dependency, data store, or migration is required. Enrichment and shortlist uncertainty semantics remain deferred to a separate change unless a focused regression demonstrates a production defect.
