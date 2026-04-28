# Parallel Bounded Change Planning Prompt

Use this when you already have a workstream or a set of bounded change thread
files and want help deciding what can run in parallel safely.

```text
Plan safe parallel execution for these bounded change threads.

Context:
- workstream or branch in scope:
- bounded change thread files in scope:
- known shared docs/code surfaces:
- known dependencies:
- whether the main goal is parallel execution recommendation, ownership split, or sequencing:

Please:
1. identify which bounded change threads are truly independent
2. identify shared surfaces and dependency risks
3. recommend what can run in parallel and what should stay sequential
4. recommend ownership boundaries for each lane
5. recommend the next artifacts, such as separate specs/plans or one shared plan with parallel lanes
```

Expected output:
- recommended parallel lanes
- sequencing warnings
- shared-surface risks
- ownership boundaries
- next artifact recommendations, usually organized by thread file
