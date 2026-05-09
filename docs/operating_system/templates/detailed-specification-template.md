---
template_id: detailed-specification
document_type: detailed_specification
target_globs:
- docs/superpowers/specs/*.md
required_sections:
- Goal
- Key Deliverables
- Task/Wave Breakdown
- Design Decisions
- Invariants
- Validation Plan
- Completion Criteria
required_frontmatter:
  artifact_type: spec
---

# Detailed Specification Template

## Goal

<what this specification must define>

## Key Deliverables

### <deliverable 1>

Describe one concrete specification outcome this document must deliver, such as a resolved design boundary, contract decision, or validated implementation constraint.

### <deliverable 2>

Describe another concrete specification result this document must deliver, such as clarified invariants, interface shape, or validation confidence.

## Task/Wave Breakdown

### Wave 1

Describe the first design or analysis pass needed to define the specification correctly.

### Wave 2

Describe the follow-up pass needed to resolve open questions, tighten decisions, or prepare the spec for approval.

## Design Decisions

- <decision>

## Invariants

- <must remain true>

## Validation Plan

- <how to verify>

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
