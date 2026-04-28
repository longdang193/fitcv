---
workstream_id: workstream-bounded-agentic-cv-quality
status: active
---

# Workstream: Bounded Agentic CV Quality

## Purpose

Improve late-stage FitCV quality with selective agentic AI while preserving deterministic acceptance discipline and original pipeline semantics.

## Owns

- grounded `cv_analysis` evidence selection
- fit-readiness reasoning and explicit pre-writing hold reasons
- stronger `cv_generation` rewrite, repair, and recovery behavior
- bounded live-provider integration for approved late-stage seams
- the quality of agentic recommendations and outputs inside approved seams

## Does Not Own

- final acceptance authority
- control-plane ownership
- primary ownership of operator-facing observability surfaces
- autonomous mutation of canonical synonym state

## Dependencies

- `cv_system`
- deterministic validation and acceptance contracts
- agentic observability surfaces

## Key Risks

- turning the agentic path into a second runtime identity
- weakening deterministic validation in order to raise acceptance counts

## Notes

This workstream improves recommendation quality and generation quality inside approved seams. It does not own the final decision contract, and it does not own the dedicated synonym-management product surface.
