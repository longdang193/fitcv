# Roadmap Vs Execution Divergence Prompt

Use this when you want to compare the master roadmap or a named workstream
against the specs, plans, and execution completed so far.
If you need an explicit completion verdict and close/continue/re-scope
decision for one workstream, use
`workstream-completion-and-intent-check-prompt.md`.

```text
Review divergence between the roadmap/workstream intent and execution so far.

Review scope:
- roadmap-wide review or single workstream review:
- roadmap doc:
- workstream doc or id (if any):
- related specs:
- related plans:
- known executed changes or merged work:
- main concern (missing progress, drift from intent, off-roadmap work, stale artifacts, mixed workstream vs operating_system boundaries):

Please:
1. read the relevant roadmap or workstream sources first
2. compare them against downstream specs, plans, and execution completed so far
3. separate healthy evolution from real divergence
4. identify missing execution, off-roadmap execution, stale artifacts, and misclassified work
5. recommend the next correction step
```

Expected output:
- divergence findings
- explicit alignment vs misalignment calls
- recommended next moves such as refining roadmap/workstream docs, retiring stale artifacts, reclassifying work, or drafting the next bounded spec/plan
