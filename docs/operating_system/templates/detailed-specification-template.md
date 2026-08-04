---
template_id: detailed-specification
target_globs:
- docs/superpowers/specs/*.md
required_sections:
- Goal and Problem
- Required Outcomes
- Design Analysis
- Design Decisions
- Invariants and Edge Cases
- Validation Plan
- Completion Criteria
required_frontmatter:
  artifact_type: spec
  status: active
  layer: change
distribution_tier: starter_kit
---

# Detailed Specification Template

Use this template after behavior and design direction are approved. Promote an existing draft in place when one exists. Specification owns required behavior and design-level boundaries. Exact files, task order, commands, dependencies, rollout steps, and execution waves belong in implementation plan.

## Goal and Problem

### Problem

- current behavior or opportunity:
- affected users, systems, or maintainers:
- evidence:
- consequence of no change:

### Goal

- desired outcome:
- observable success:

## Required Outcomes

### Outcome: <name>

- affected actor or system:
- required result:
- success condition:

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| <what must be known> | <observed fact> | <file, test, tool, or system> | high / medium / low | <decision or open question> |

### Prototype and Validation Evidence

- prototype reference or `Not applicable: <reason>`:
- validated scenarios and states:
- findings incorporated into approved behavior:
- rejected alternatives:

### Scope

- included behavior:
- affected boundaries:
- admissible cases:
- compatibility expectation:

### Non-Goals

- <explicitly excluded behavior>

### Requirements and Behavioral Contract

#### Requirement: <name>

- trigger or actor:
- preconditions:
- required behavior:
- output or state change:
- failure behavior:
- observable acceptance:

When relevant define inputs, outputs, identity, data grain, schemas, state transitions, defaults, validation, errors, retries, idempotency, ordering, cancellation, fallback, and boundary conversions.

### Constraints and Alternatives

- constraint: <design, operational, compatibility, security, accessibility, or platform constraint>
- alternative: <candidate>
  - benefit:
  - trade-off:
  - reason accepted or rejected:

## Design Decisions

### Decision: <name>

- context:
- selected approach:
- rationale:
- alternatives considered:
- accepted trade-offs:
- affected owners and boundaries:

### Compatibility, Migration, and Risk

- old behavior:
- new behavior:
- compatibility boundary:
- migration or backfill:
- rollout and rollback:
- deprecation or consumer impact:
- risk:
  - mitigation:

Use `Not applicable: <reason>` for fields that genuinely do not apply. Do not leave required decisions unresolved as implementation details.

## Invariants and Edge Cases

### Invariants

- <must remain true>

### Edge Cases

- empty or minimal input:
- normal and large input:
- duplicate, missing, malformed, or unsupported data:
- retry, cancellation, timeout, partial failure, or concurrency:
- migration or mixed-version state:
- generated-source consistency:
- security or accessibility boundary:

Remove non-applicable edge-case rows or mark them with reason. Preserve equivalent rules under one authoritative owner.

## Validation Plan

### Backend Verification Claims

- direct boundary:
- important success and failure behavior:
- final state or side effects:
- rollback, retry, duplicate, or idempotency behavior:
- canonical contract and conformance proof, or `Not applicable: <reason>`:
- real dependencies requiring proof, or `Not applicable: <reason>`:
- representative-operation trace mechanism, or `Not applicable: <reason>`:
- performance claim and threshold, or `Not applicable: <reason>`:

Frontend and browser evidence may extend these claims but never replace direct backend proof.

### Acceptance Criterion: <claim>

- setup or precondition:
- action:
- expected result:
- failure condition:
- proof method:
- expected evidence:

Every required outcome and material requirement must map to observable acceptance and proof intent. Exact commands and execution order belong in implementation plan.

## Completion Criteria

Specification is complete when:

1. problem, evidence, goal, scope, and non-goals are explicit
2. required outcomes and behavioral contracts are unambiguous
3. design decisions, ownership boundaries, compatibility, migration, and material risks are resolved
4. invariants and applicable edge cases are explicit
5. every required outcome maps to acceptance and validation intent
6. unresolved questions are closed or explicitly approved as deferred
7. implementation sequencing is left to implementation plan
