---
template_id: implementation-plan
document_type: implementation_plan
target_globs:
- docs/superpowers/plans/*.md
required_sections:
- Goal
- Key Deliverables
- Task/Wave Breakdown
- Verification
- Completion Criteria
required_frontmatter:
  artifact_type: plan
---

# Implementation Plan Template

## Goal

<what this plan must deliver>

## Key Deliverables

### <deliverable 1>

Describe one concrete implementation outcome this plan must deliver, including changed surfaces, expected behavior, and verification intent.

### <deliverable 2>

Describe another concrete implementation result this plan must deliver, such as test coverage, documentation alignment, or downstream handoff readiness.

## Task/Wave Breakdown

### task 1:

Describe the first executable task, including touched surfaces, intended result, and how it will be verified.

### task 2:

Describe the next executable task, including dependency order, expected outcome, and follow-up verification or handoff.

## Verification

- <command>

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
