# Proposal

## Why

Issue #147 reports that every selected job in one CV-generation run ended with a non-persistable result and no CV artifact. The issue review does not establish the rejecting guard, so the smallest safe next step is a controlled representative investigation before another real-data batch or any relaxation of acceptance rules.

## What Changes

- Trace one representative CV-generation outcome through generation, validation, conversion, and persistence boundaries.
- Identify the exact rejecting guard and classify the outcome with the existing typed diagnostic contract.
- Add focused regression coverage for the demonstrated valid or invalid outcome and its persistence behavior.
- Keep the investigation local or synthetic where possible and record evidence without persisting private profile, CV, prompt, provider, or credential payloads.

## Capabilities

### New Capabilities

- `cv-generation-persistability`: Defines the minimum evidence and safe classification required when a generated CV cannot be persisted.

### Modified Capabilities

- None.

## Impact

CV-generation, validation, conversion, and persistence boundaries; existing diagnostic mapping; focused worker or pipeline tests and investigation notes. No provider switch, retry-policy change, acceptance-gate weakening, new diagnostic subsystem, or broad real-data rerun is included.
