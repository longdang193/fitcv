---
template_id: implementation-execution-map
document_type: implementation_execution_map
target_globs:
  - docs/superpowers/execution_maps/*.md
required_sections:
  - Goal
  - Key Deliverables
  - Execution Waves
  - Dependencies And Risks
  - Completion Criteria
required_frontmatter:
  artifact_type: execution_map
  map_type: implementation_execution
---

# Implementation Execution Map Template

## Goal

<what this execution map must orchestrate>

## Key Deliverables

- <deliverable 1>
- <deliverable 2>

## Execution Waves

- wave 1:
  - <plan>
- wave 2:
  - <plan>

## Dependencies And Risks

- dependencies:
  - <dependency>
- shared-surface risks:
  - <risk>

## Completion Criteria

An implementation-execution-map item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
