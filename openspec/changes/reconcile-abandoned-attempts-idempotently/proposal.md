# Proposal

## Why

The abandoned-attempt reconciler treats every expired `running` attempt for a run as independently retryable. If a worker dies and a later continuation also expires, one reconciliation pass can enqueue the same run more than once. That violates single-owner execution and can corrupt lifecycle evidence.

## What Changes

- Reconcile all expired running attempts for a run in one pass.
- Mark superseded expired attempts terminal without retrying them.
- Permit at most one retry enqueue per run and preserve existing retry and cancellation policy.
- Require evidence that the inline owner is gone before terminalizing an abandoned attempt; uncertain dispatch state must not trigger replacement execution.
- Resolve relative persisted projection paths from the run configuration directory during recovery without changing the stored path contract.
- Add regression coverage for duplicate expired attempts and document the recovery contract.

## Scope

This change is limited to run-attempt reconciliation. It does not alter private profile data, the stored jobs input path, pipeline stage behavior, retry limits, or real-data artifacts. Verification uses controlled or synthetic recovery evidence rather than an unconditional real-data replay.
