# Design

## Root cause

Attempt state is reconstructed from append-only events, but the reconciler loops over every expired attempt and calls `enqueue_run_with_job_id` inside that loop. Historical stale attempts therefore remain retry triggers after a newer attempt has already been created.

## Decision

For each eligible run, collect expired `running` attempts and select the newest attempt by lease start time, with event time as a tie-breaker. Persist a terminal abandonment event for every expired attempt. Only the newest attempt may apply cancellation, max-attempt handling, or one retry enqueue; older expired attempts are marked superseded and are not retryable. Inline recovery is eligible only when available ownership evidence shows that no worker remains responsible for the attempt; lease expiry or uncertain dispatch alone is insufficient.

This keeps the event stream complete while making the recovery side effect single-owner and idempotent per reconciliation pass. A later reconciliation can act only on a newly-created attempt, not on the superseded historical attempts.

## Constraints

- Preserve the existing retry settings and backoff.
- Preserve cancellation semantics: cancellation terminalizes the run and never enqueues.
- Preserve active-worker safety: an active or uncertain owner leaves the run nonterminal and does not trigger replacement execution.
- Preserve the native jobs path and config path passed to the existing enqueue function.
- Resolve relative jobs paths from the run configuration directory at worker execution time; do not rewrite the persisted path value.
- Do not persist raw job, profile, provider, or credential payloads.
