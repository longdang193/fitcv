---
name: publication-boundary-rule
description: Enforce private/public publication boundaries and controlled export workflow.
alwaysApply: true
required_reads:
  - docs/operating_system/publication-workflow.md
tags:
  - rule
  - publication
  - privacy
---

# Publication Boundary Rule

Protect private-only material during publication flows.

## Requirements

- Keep private operating-system and agent-core material out of public mirrors.
- Use curated publication workflow for any repo export.
- Review generated artifacts and adapter outputs for private references before publish.
- Treat GitNexus artifacts, internal memory, and private governance docs as non-public by default.
