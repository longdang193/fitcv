---
name: gitnexus-refresh-prompt
description: Use prompt template for gitnexus refresh prompt.
type: prompt
stage: planning
entry_points:
- use this prompt when its title scope matches the current planning/execution need
prerequisites:
- relevant in-scope roadmap/workstream/thread/spec/plan context is available
next_steps:
- implementation-next-action-gate-prompt.md
related_skills:
- planning-dispatch
required_reads:
- docs/operating_system/prompt_templates/README.md
tags:
- prompt-template
- planning
- operating_system
owner_layer: operating_system
status: active
---

# GitNexus Refresh Prompt

Use this when GitNexus is stale, partially broken, or returning results that no
longer match the current repo state.

```text
Refresh or repair GitNexus for this repo before relying on it again.

Context:
- repo:
- current GitNexus freshness state:
- whether GitNexus is stale, failing, or returning suspicious results:
- recent symptoms:
- whether this is blocking exploration, debugging, or impact analysis:

Please:
1. check GitNexus freshness first
2. report whether the current state is fresh, stale, or failed
3. rerun the recommended GitNexus refresh path for this machine
4. verify whether the refresh fixed the problem
5. report what still does not work, if anything
6. fall back to source-first guidance if GitNexus remains stale or broken
7. keep GitNexus-specific artifacts private-only
```

Expected output:
- freshness result before refresh
- refresh command used
- status after refresh
- remaining issues, if any
- source-first fallback guidance when refresh does not fully recover GitNexus

