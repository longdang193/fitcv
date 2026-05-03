---
template_id: detailed-specification
document_type: detailed_specification
target_globs:
  - docs/superpowers/specs/*.md
required_sections:
  - Goal
  - Key Deliverables
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

- <deliverable 1>
- <deliverable 2>

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

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
