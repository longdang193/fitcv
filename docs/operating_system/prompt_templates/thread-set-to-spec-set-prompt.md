# Thread Set To Spec Set Prompt

Use this when you already have a set of bounded change thread files and want to
determine the complete spec set needed before detailed-spec authoring and
implementation orchestration.

```text
Turn this thread set into the complete spec set.

Context:
- workstream or branch in scope:
- thread files in scope:
- known dependencies between threads:
- known shared surfaces:
- existing specs already linked through planning_lineage:

Please:
1. decide which threads need specs
2. decide whether any threads can share one spec
3. identify missing or redundant specs
4. produce the complete spec set for this thread set
5. recommend the next artifact after the spec set
```

Expected output:
- complete spec inventory for the thread set
- uncovered or redundant spec findings
- split/merge decisions across the thread set
- next artifact recommendation, usually a spec-authoring map
