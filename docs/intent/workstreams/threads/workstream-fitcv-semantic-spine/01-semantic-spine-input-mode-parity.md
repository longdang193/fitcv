---
thread_id: workstream-fitcv-semantic-spine.semantic-spine-input-mode-parity
status: proposed
---

# semantic-spine-input-mode-parity

## Goal

Align direct input, pasted JSON, upload, and path-driven input semantics to the same original FitCV stage meaning.

## Why Now

Input-mode drift is one of the fastest ways to accidentally redefine the pipeline.

## Dependencies

original FitCV input contracts; stage-source truth

## Shared Surfaces

src/fitcv/pipeline.py; trigger input parsers; docs/stages/*.source.yaml

## Notes

Keep this slice semantic-first, not UI-first.


