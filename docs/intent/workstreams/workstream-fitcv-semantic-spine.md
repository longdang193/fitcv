---
workstream_id: workstream-fitcv-semantic-spine
status: active
---

# Workstream: FitCV Semantic Spine

## Purpose

Keep the original FitCV pipeline meaning authoritative while the upgraded line adds selective agentic AI.

## Owns

- original stage order and stage-owned boundaries
- checkpoint and continue semantics
- authoritative fit and eligibility meaning
- direct-input and manual-input behavior that should match the original pipeline
- protection against replay-first or shadow-runtime drift

## Does Not Own

- agentic quality improvements by themselves
- observability implementation details outside semantic truth
- repo governance or publication policy

## Dependencies

- original FitCV runtime contracts in `src/fitcv/`
- stage source docs under `docs/stages/`
- operator run-flow contracts that must reflect true stage meaning

## Key Risks

- introducing agentic behavior that silently changes eligibility meaning
- letting new UI or replay concepts redefine what a stage means
- allowing synonym assistance to become unreviewed semantic authority

## Notes

Synonym management belongs here only at the semantic-boundary level: canonical synonym meaning and runtime matching authority stay deterministic. Agentic synonym help may exist, but only as reviewed assistance layered on top.
