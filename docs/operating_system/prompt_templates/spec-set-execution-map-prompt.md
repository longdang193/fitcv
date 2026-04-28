# Spec Set To Implementation Execution Map Prompt

Use this when the approved detailed specs already exist and you want a distinct
implementation execution map that decides ordering, waves, and parallel lanes.

```text
Create an implementation execution map for this approved detailed-spec set.

Context:
- workstream or branch in scope:
- threads in scope:
- approved detailed specs in scope:
- known dependencies:
- known shared docs/code surfaces:
- whether the main risk is sequencing, parallelism, or shared-surface coordination:

Please:
1. identify the dependency graph across the spec set
2. define execution waves
3. define safe parallel lanes
4. call out shared-surface coordination risks
5. recommend the bounded implementation-plan breakdown
6. draft the execution map in docs/superpowers/execution_maps/
```

Expected output:
- one implementation execution map artifact in `docs/superpowers/execution_maps/`
- dependency graph
- execution waves
- parallel lanes
- recommended plan breakdown
