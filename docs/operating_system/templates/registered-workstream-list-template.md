---
template_id: registered-workstream-list
document_type: registered_workstream_list
target_globs:
  - docs/superpowers/workstreams/registered-workstream-list.md
required_sections:
  - Goal
  - Key Deliverables
  - Registered Workstreams
  - Traceability
  - Completion Criteria
---

# Registered Workstream List Template

## Goal

<what this registered workstream set covers>

## Key Deliverables

- <deliverable 1>
- <deliverable 2>

## Registered Workstreams

- `workstream_id`: <id>
  - status: <proposed|active|blocked|completed|dropped>
  - summary: <one line>

## Traceability

- roadmap source: `docs/intent/master-workstream-roadmap.md`

## Completion Criteria

A workstream-list item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

- `docs/operating_system/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
