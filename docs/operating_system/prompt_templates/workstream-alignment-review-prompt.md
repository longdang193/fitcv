---
name: workstream-alignment-review-prompt
description: Use prompt template for workstream alignment review prompt.
type: prompt
stage: drift
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
- drift
- workstream
owner_layer: workstream
status: active
---

# Workstream Alignment Review Prompt

Use this when you want to check whether a proposed change really belongs to the
named workstream.

If the work has already happened and you want to compare the workstream intent
against specs, plans, and execution so far, use
`roadmap-vs-execution-divergence-prompt.md` instead.

```text
Review whether this proposed change belongs to the named workstream.

Change context:
- proposed change:
- proposed workstream id:
- workstream doc:
- why I think it belongs there:
- possible operating_system angle:

Please:
1. assess whether the change fits the named workstream
2. recommend a different registered workstream if the fit is weak
3. say if this should really use `parent_workstream: none` because it is operating_system work
4. explain the reasoning briefly
5. recommend the next artifact or prompt to use
```

Expected output:
- alignment assessment plus the recommended next step

