# Workstream Coverage And Progress Guide

Use this guide to keep the planning ladder precise, check whether the roadmap
is fully covered, track workstream progress, and advance work in parallel
without drifting.

## The Precise Ladder

Use this model consistently:

```text
intent
-> master workstream roadmap
-> complete set of registered workstreams
-> bounded change thread files
-> complete spec set
-> spec-authoring map
-> detailed specs
-> implementation execution map
-> implementation plans
-> execution
```

Definitions:

- `intent`
  - the end goal, outcomes, constraints, and non-goals
- `master workstream roadmap`
  - the strategic map of the major threads required to reach the end goal
- `registered workstreams`
  - the concrete named set of durable product-direction threads that together
    cover the roadmap
- `bounded change threads`
  - the discrete execution-capable slices beneath a workstream, expressed
    through `docs/intent/workstreams/threads/`
- `complete spec set`
  - the inventory of all detailed specs needed for a chosen thread set
- `spec-authoring map`
  - the orchestration artifact for detailed-spec authoring order and safe
    parallel authoring lanes
- `detailed specs`
  - bounded design artifacts for one change thread or one approved shared
    thread surface
- `implementation execution map`
  - the orchestration artifact for implementing an approved detailed-spec set
- `implementation plans`
  - bounded execution artifacts for one approved detailed spec or approved
    implementation-execution-map wave

## What Each Layer Tracks

### 1. Coverage tracking

Lives in:

- [master-workstream-roadmap.md](./master-workstream-roadmap.md)

Answers:

- do we have all major threads needed to reach the end goal?
- are any major jobs to be done still unowned?
- are some registered workstreams overlapping or too vague?

Do not turn the roadmap into a progress board.

### 2. Workstream progress tracking

Lives in:

- [docs/intent/workstreams/](./workstreams)

Answers:

- how far along is this durable thread?
- what is done?
- what remains?
- what bounded change threads should advance next?

### 3. Thread progress tracking

Lives in:

- [docs/intent/workstreams/threads/](./workstreams/threads)

Answers:

- what exact bounded slices exist under this workstream?
- which ones are proposed, active, blocked, or completed?
- which ones produced specs or plans?

### 4. Execution artifact tracking

Lives in:

- [docs/superpowers/execution_maps/](../superpowers/execution_maps)
- [docs/superpowers/specs/](../superpowers/specs)
- [docs/superpowers/plans/](../superpowers/plans)

Answers:

- what complete spec set exists for a thread set?
- what detailed specs should be authored first?
- what bounded slices have been designed?
- what approved detailed specs are ready for implementation ordering?
- what slices have plans?
- what has been executed?

### 5. Divergence review

Uses:

- the roadmap
- the registered workstreams
- downstream specs/plans/execution

Answers:

- does actual execution still align with roadmap and workstream intent?
- what has gone missing, stale, or off-roadmap?

## Coverage Review

The registered workstreams should collectively cover the master roadmap.

Use this question:

`Does the current set of registered workstreams completely and specifically cover the roadmap well enough to reach the end goal?`

Review for:

- missing major delivery threads
- duplicate or overlapping workstreams
- workstreams that are too vague to guide downstream work
- product work that really belongs in `operating_system`
- operating-system work incorrectly forced into product workstreams

## Registered Workstream Progress

Each workstream doc should stay small, but it should be able to answer:

- why this thread exists
- what jobs to be done or outcomes it serves
- what success looks like
- what does not belong here
- where the thread folder lives
- what active thread files matter right now
- what bounded change threads are already completed at a roll-up level
- what specs/plans are linked
- what gaps remain

## Bounded Change Threads

A workstream is not the unit of execution.

The practical execution unit is the **bounded change thread**:

- one discrete gap
- one discrete improvement slice
- one discrete design/execution thread

Each bounded change thread may produce:

- a place in the complete spec set
- a spec-authoring map
- a detailed spec
- an implementation execution map
- an implementation plan
- direct execution when already bounded and clear

For product workstreams, prefer expressing active threads as lightweight files
under `docs/intent/workstreams/threads/<workstream-id>/` instead of burying the
same slices inside long workstream-doc bullet lists.

## Parallel Execution Rules

Parallel work is encouraged across bounded change threads, not directly across
broad workstreams.

Healthy parallel conditions:

- ownership is clear
- dependencies are explicit
- shared source-of-truth surfaces are minimized or coordinated
- each slice is independently understandable
- each slice has its own spec/plan when needed

Unsafe parallel patterns:

- two broad efforts under the same workstream with no boundary
- multiple threads editing the same shared truth surface without coordination
- parallel work where one slice depends on unfinished decisions in another

Use this simple rule:

`Parallelize bounded change threads, not vague workstream intent.`

## Three Distinct Review Types

Keep these reviews separate:

1. `coverage review`
   - do the registered workstreams fully cover the roadmap/end goal?
2. `progress review`
   - how far along is each workstream?
3. `divergence review`
   - does execution still match roadmap/workstream intent?

## Prompt And Artifact Routing

Use these prompts when helpful:

- roadmap completeness questions:
  - `docs/operating_system/prompt_templates/roadmap-gap-prompt.md`
- route roadmap into the right workstream:
  - `docs/operating_system/prompt_templates/roadmap-to-workstream-prompt.md`
- route a workstream into the next bounded design slice:
  - `docs/operating_system/prompt_templates/bounded-change-thread-build-prompt.md`
- turn a thread set into the complete spec set:
  - `docs/operating_system/prompt_templates/thread-set-to-spec-set-prompt.md`
- turn the complete spec set into the next detailed-spec authoring sequence:
  - `docs/operating_system/prompt_templates/spec-set-to-spec-authoring-map-prompt.md`
- route a chosen bounded thread into the next detailed spec:
  - `docs/operating_system/prompt_templates/workstream-to-spec-prompt.md`
- turn approved detailed specs into the next implementation execution sequence:
  - `docs/operating_system/prompt_templates/spec-set-execution-map-prompt.md`
- review roadmap/workstream vs execution:
  - `docs/operating_system/prompt_templates/roadmap-vs-execution-divergence-prompt.md`

## Anti-Patterns

- using the master roadmap as a task board
- treating a workstream as if it were already a spec or plan
- treating the complete spec set as if it were already detailed-spec authoring
- treating a spec-authoring map as if it were already an implementation plan
- running parallel work directly against a broad workstream with no bounded
  change split
- tracking progress only in scattered specs/plans with no workstream roll-up
- assuming roadmap coverage is complete just because some workstreams exist
