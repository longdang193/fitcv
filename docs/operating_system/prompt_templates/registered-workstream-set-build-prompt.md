# Registered Workstream Set Build Prompt

Use this when the master roadmap exists and you want to derive the concrete,
complete set of registered workstreams from it.

```text
Build the complete set of registered workstreams from the master roadmap.

Context:
- master roadmap doc:
- intent docs:
- existing workstream docs:
- known missing or overlapping areas:
- whether any thread might really belong to `operating_system`:

Please:
1. convert roadmap threads into concrete named workstream docs
2. identify missing, duplicate, or too-vague workstreams
3. distinguish true product workstreams from `operating_system`
4. assess whether the set covers the roadmap adequately
5. recommend the next artifact after the workstream set
```

Expected output:
- proposed registered workstream set
- coverage findings about the set
- next recommended artifact, usually bounded change threads for one workstream
