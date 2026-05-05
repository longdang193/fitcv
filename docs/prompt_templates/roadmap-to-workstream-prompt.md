---
prompt_id: roadmap-to-workstream-prompt
type: prompt
stage: planning
owner_layer: intent
entry_points:
  - use this prompt when its title scope matches the current planning/execution need
prerequisites:
  - relevant in-scope roadmap/workstream/thread/spec/plan context is available
next_steps:
  - implementation-next-action-gate-prompt.md
skills:
  - planning-dispatch
status: active
---
# Roadmap To Workstream Prompt

Use this when you have a roadmap thread, intent note, or fuzzy delivery idea
and want help choosing the right next workstream.

```text
Help me translate this roadmap or intent thread into the right next workstream.

Upstream context:
- intent docs:
- roadmap thread or section:
- related workstream docs already considered:
- change idea:
- desired outcome:
- constraints:

Please:
1. decide whether this belongs to a product workstream or to `operating_system`
2. identify the best matching existing workstream from `docs/intent/workstreams/`, if one exists
3. say whether we should refine an existing workstream or add a new one
4. name the recommended next artifact after this step
5. explain the recommendation briefly and plainly
```

Expected output:
- recommended workstream routing, or `operating_system` routing, plus the next
  artifact to create

