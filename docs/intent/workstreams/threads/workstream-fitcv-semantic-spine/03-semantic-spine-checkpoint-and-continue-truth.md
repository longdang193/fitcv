---
thread_id: workstream-fitcv-semantic-spine.semantic-spine-checkpoint-and-continue-truth
status: proposed
---

# semantic-spine-checkpoint-and-continue-truth

## Goal

Preserve pause, continue, and reached-stage meaning across run modes.

## Why Now

Checkpoint drift quietly breaks operator trust even when stages still run.

## Dependencies

run-state persistence; operator run detail

## Shared Surfaces

src/fitcv_cp/; pipeline checkpoint persistence

## Notes

Keep status vocabulary aligned with stage authority.


