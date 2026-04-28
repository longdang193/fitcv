# Roadmap Gap Prompt

Use this when you think the master roadmap may be missing an important durable
thread.

If the roadmap already exists and you want to compare it against execution so
far, use `roadmap-vs-execution-divergence-prompt.md` instead.

```text
Assess whether the master roadmap is missing a real workstream or just needs refinement.

Gap context:
- intent docs:
- roadmap section reviewed:
- missing need or repeated request:
- why it seems durable:
- known related workstreams:

Please:
1. assess whether this is a real roadmap gap, an existing workstream that needs refinement, or operating_system work
2. recommend whether to add a new workstream, refine an existing one, or leave the roadmap unchanged
3. name the next artifact to create
4. explain the recommendation briefly
```

Expected output:
- gap assessment plus the recommended next artifact
