---
name: skill-repository-research
description: Use when a read-only task needs source-grounded local findings before design, planning, or implementation.
required_reads:
- docs/operating_system/tooling/code-intelligence-tools.md
distribution_tier: starter_kit
---
# Repository Research

Produce evidence, not designs, plans, or edits.

1. State question, repository boundary, and needed evidence.
2. Use native file inspection and `rg` for exact names, paths, and text.
3. Use packet Semble MCP (`packet_semble_search`) only when broad local concept location is unknown. Confirm hits in source.
4. Use packet Serena only after exact symbols or references are known. Use GitNexus only when packet selects it and broad flow or impact remains unknown.
5. Use `sg` only for read-only structural preview. `apply_patch` remains sole edit path; this route does not edit.
6. Separate verified facts, source paths, unknowns, and next handoff: design, plan, implementation, or stop.

Do not use `skill-brainstorming` unless task asks for options or design approval. Missing optional MCPs never block source-first research.
