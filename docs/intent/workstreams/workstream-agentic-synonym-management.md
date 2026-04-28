---
workstream_id: workstream-agentic-synonym-management
status: active
---

# Workstream: Agentic Synonym Management

## Purpose

Reduce the manual synonym-maintenance burden with a review-first agentic assistance flow while keeping canonical runtime synonym authority deterministic and explicitly approved.

## Owns

- unmatched-term and low-confidence synonym detection
- agentic candidate mappings, clustering, confidence, and rationale
- operator review queues for proposed synonym changes
- run-scoped overlay suggestions and approval flows
- explicit promotion paths from reviewed proposals into canonical synonym state

## Does Not Own

- unreviewed mutation of canonical synonym data
- final fit or acceptance authority in downstream stages
- generic late-stage CV generation quality

## Dependencies

- semantic-spine invariants around deterministic runtime matching authority
- operator control-plane surfaces for review and approval
- agentic observability for proposal provenance and downstream impact visibility

## Key Risks

- letting suggestions silently become active runtime truth
- hiding downstream impact of synonym changes from operators
- collapsing ambiguous terms into overconfident canonical mappings

## Notes

This workstream exists because manual synonym upkeep is a real product bottleneck. The correct upgrade is agentic assistance plus explicit review, not autonomous synonym mutation.
