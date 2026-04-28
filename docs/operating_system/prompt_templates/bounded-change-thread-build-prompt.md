# Bounded Change Thread Build Prompt

Use this when a registered workstream exists and you want to break it into
discrete, execution-capable slices.

```text
Break this workstream into bounded change threads.

Context:
- workstream id:
- workstream doc:
- jobs to be done / success signals:
- known open gaps:
- known dependencies:
- possible shared surfaces:

Please:
1. identify bounded change threads beneath the workstream
2. separate independent slices from dependency-coupled slices
3. call out shared-surface and sequencing risks
4. recommend which threads need specs first
5. recommend the next artifact after the bounded change thread list
6. format the result so it can be turned directly into lightweight thread files
```

Expected output:
- bounded change thread candidates mapped to proposed thread files under
  `docs/intent/workstreams/threads/<workstream-id>/`
- dependency and shared-surface notes
- per-thread status and short goal statements
- next recommended artifact, usually a spec for one bounded change thread
