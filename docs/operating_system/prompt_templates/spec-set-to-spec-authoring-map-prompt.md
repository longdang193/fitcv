# Spec Set To Spec-Authoring Map Prompt

Use this when the complete spec set is known but the detailed specs have not
all been written yet.

```text
Create a spec-authoring map for this complete spec set.

Context:
- workstream or branch in scope:
- threads in scope:
- complete spec set in scope:
- known dependencies between specs:
- known shared design surfaces:
- whether the main risk is design sequencing, shared-surface design conflicts, or authoring parallelism:

Please:
1. identify which detailed specs should be authored first
2. identify dependencies across detailed-spec authoring
3. define safe parallel authoring lanes
4. call out shared-surface design risks
5. recommend the next detailed-spec authoring sequence
6. draft the spec-authoring map in docs/superpowers/execution_maps/
```

Expected output:
- one spec-authoring map artifact in `docs/superpowers/execution_maps/`
- dependency and sequencing guidance for detailed-spec authoring
- safe parallel authoring lanes
- recommended next detailed-spec sequence
