# Execution Maps

This folder holds orchestration artifacts for two different planning phases.

Use this folder for:

- spec-authoring maps
- implementation execution maps

Use a spec-authoring map when the complete spec set exists and the next
question is:

- which detailed specs should be authored first
- which detailed-spec authoring tasks depend on others
- what can be authored in parallel safely
- where shared-surface design risks exist

Use an implementation execution map when the approved detailed specs exist and
the next question is:

- what depends on what
- what can run in parallel
- what should run in sequence
- how the bounded plans should be split

Execution maps sit here in the ladder:

`thread set -> complete spec set -> spec-authoring map -> detailed specs -> implementation execution map -> implementation plans -> execution passes with thread checkpoint result packs`

Execution maps are:

- human-authored orchestration decisions
- cross-spec dependency and lane maps
- plan-breakdown guidance

Execution maps are not:

- design specs
- implementation plans
- generated lineage registries

Suggested frontmatter:

```yaml
---
layer: change
artifact_type: execution_map
status: proposed | active | completed | superseded
parent_workstream: <id> | none
map_type: spec_authoring | implementation_execution
threads:
  - <thread-id>
specs:
  - docs/superpowers/specs/<file>.md
---
```

Suggested sections:

- scope
- dependency graph
- authoring waves or execution waves
- authoring lanes or parallel lanes
- shared-surface risks
- recommended next detailed-spec sequence or recommended plan breakdown
- orchestration notes

If you want the structural lineage view, use
`docs/generated/planning_lineage.yaml`.
If you want the human orchestration decision about ordering and parallelism,
use the right map type in this folder.
