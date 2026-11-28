# Proposal

## Why

Partial ranking can currently conceal explicit persistence or handoff failures, while later technical failures are recorded against a checkpoint that rewinds to ranking. Ranking and CV-generation diagnostics also lose persistence coverage or can carry unbounded free-form content, making recovery difficult and diagnostic storage unsafe to rely on.

## What Changes

- Resume a partial ranking only when it has no independent technical failure and its validated ranking-to-CV handoff matches the ranked output.
- Derive terminal checkpoint completion and retry boundary from the actual failing stage.
- Preserve typed ranking diagnostics through the persisted stage artifact and failed stage settlement, and persist bounded, sanitized CV-generation failure diagnostics.
- Record a CV-generation failure at the stage artifact that owns it, rather than leaving the stage as not reached.

## Capabilities

### New Capabilities
- `ranking-resume-integrity`: Defines when partial ranking is safe to continue and how failure checkpoints align with the failing stage.
- `pipeline-diagnostic-persistence`: Defines safe propagation and persistence of ranking and generation diagnostics.

### Modified Capabilities
- None. `openspec list --specs` reports no canonical specs; these behavior contracts are introduced as new capabilities rather than editing completed historical deltas.

## Impact

Worker terminal classification and checkpoint persistence; ranking handoff validation; typed diagnostic normalization and ranking artifact assembly; CV-generation stage artifacts; focused worker, ranking, and pipeline tests. No data migration or new dependency is expected.
