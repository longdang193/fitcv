# Run Recovery Specification

## ADDED Requirements

### Requirement: Expired attempts are reconciled once per run
The reconciler MUST terminalize every expired `running` attempt it observes for an eligible run, but MUST perform at most one retry or terminal-failure decision for that run in one reconciliation pass.

#### Scenario: Duplicate expired attempts
- **WHEN** a run has more than one expired `running` attempt and retry is allowed
- **THEN** every expired attempt receives a terminal abandonment event, only the newest attempt remains retry-eligible, and the run is enqueued at most once

#### Scenario: Expired attempt with cancellation requested
- **WHEN** a run has one or more expired `running` attempts and cancellation is requested
- **THEN** every expired attempt is terminalized as cancelled, the run becomes cancelled, and no retry is enqueued

#### Scenario: Retry limit is exhausted
- **WHEN** a run has expired attempts and the configured maximum attempt count is reached
- **THEN** the run becomes failed and no retry is enqueued

#### Scenario: Owner or dispatch state is uncertain
- **WHEN** an inline attempt lease expires but a worker may still be active or dispatch ownership cannot be established as abandoned
- **THEN** the run is not terminalized and no replacement execution is enqueued

#### Scenario: Abandoned inline owner is established
- **WHEN** an inline attempt lease expires and the existing ownership evidence shows that no worker remains responsible for it
- **THEN** the attempt becomes eligible for the same single-owner reconciliation rules without starting more than one replacement execution

### Requirement: Relative persisted paths resolve from the run configuration
The recovery worker MUST resolve a relative persisted jobs projection path against the persisted run configuration directory before reading it, while preserving the original stored path value for integrity checks and lifecycle evidence.

#### Scenario: Recovery runs outside the original working directory
- **WHEN** a run stores a relative jobs projection path and recovery is invoked from another working directory
- **THEN** the worker reads the projection relative to the run configuration directory and validates the same persisted projection bytes
