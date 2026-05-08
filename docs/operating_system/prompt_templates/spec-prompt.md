---
name: spec-prompt
description: a specific detailed spec must be drafted from an approved bounded work
  item context.
type: prompt
stage: planning
entry_points:
- use this prompt when its title scope matches the current planning/execution need
prerequisites:
- relevant in-scope roadmap/workstream/thread/spec/plan context is available
next_steps:
- implementation-next-action-gate-prompt.md
related_skills:
- planning-dispatch
required_reads:
- docs/operating_system/prompt_templates/README.md
tags:
- prompt-template
- planning
- change
owner_layer: change
status: active
---

# Detailed Spec Prompt

## Use When

a specific detailed spec must be drafted from an approved bounded work item context

## Prerequisites

### Required

- bounded thread context known or explicit operating_system justification

### Optional

- spec authoring map

## Next Prompts

- spec-set-execution-map-prompt.md
- plan-prompt.md

## Not For

direct implementation without spec context
Use this when the complete spec set is known, a detailed-spec target is chosen,
and you want the actual design spec.

If the roadmap thread or workstream is still unclear, use
`roadmap-to-workstream-prompt.md` or `workstream-to-spec-prompt.md` first.
If the detailed-spec authoring order is still unclear across a multi-spec set,
use `spec-set-to-spec-authoring-map-prompt.md` first.

```text
Draft a spec for this work item.

Work item:
- problem:
- desired outcome:
- affected area:
- constraints:
- what should stay true:
- bounded change thread this follows (use a valid `thread_id` from `docs/intent/workstreams/threads/`; use `none` only for true operating_system work):
- if `none`, explain why this should not attach to a product workstream thread:

Please:
1. classify the work as intent, operating_system, workstream, or change
2. identify the owning docs and targets
3. state how this follows the chosen thread via `parent_thread`; if truly operating_system scoped, state why `parent_thread: none` is intentional
4. draft the detailed spec in docs/superpowers/specs/
5. call out whether the next artifact should be another detailed spec or an implementation execution map
```

Expected output:
- a spec in `docs/superpowers/specs/`

