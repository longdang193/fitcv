---
name: workflow-and-prompt-metadata-spec
description: Define one minimal metadata contract for `workflows/` and `prompt_templates/`
  that supports routing and execution with low management overhead.
allowed-tools: []
required_reads:
- docs/operating_system/prompt_templates/README.md
required_outputs:
- workflow decision or completion evidence
related_skills:
- doc-system-lifecycle
tags:
- workflow
- maintenance
- operating_system
workflow_id: workflow-and-prompt-metadata-spec
type: workflow
stage: maintenance
owner_layer: operating_system
entry_points:
- creating or updating prompt/workflow governance documents
prerequisites:
- target prompt/workflow files are identified
next_steps:
- validate-or-drift-prompt.md
status: active
---

# Workflow And Prompt Metadata Specification

## Goal

Define one minimal metadata contract for `workflows/` and `prompt_templates/`
that supports routing and execution with low management overhead.

## Required Fields

Use YAML frontmatter at the top of each prompt/workflow file.

- `workflow_id` for workflow files, `prompt_id` for prompt files
- `type`: `workflow|prompt`
- `stage`: `planning|execution|closeout|drift|maintenance`
- `entry_points`: non-empty list
- `prerequisites`: non-empty list
- `next_steps`: non-empty list
- `owner_layer`: `intent|operating_system|workstream|change`
- `status`: `active|draft|deprecated`
- `skills`: non-empty list

Optional fields:

- `outputs`
- `validators`
- `notes`

## No Duplication Rule

If a field is in frontmatter, do not duplicate it as a routing/classification
section in the body.

Examples:

- metadata has `prerequisites`: do not add a body section that restates the same list
- metadata has `next_steps`: do not add a duplicate transition list in prose
- metadata has `skills`: do not add a second standalone skills catalog

The body should focus on execution logic:

- ordered actions
- decision gates
- evidence requirements
- failure and recovery handling
- exit criteria

## Agent Usage Model

1. Filter files by `type` and `stage`.
2. Match `entry_points` to observed context.
3. Check `prerequisites`; if missing, return minimal unblock action.
4. Execute body logic using listed `skills`.
5. Transition using `next_steps`.
6. Run listed `validators` when present.

