# Precedence

Runtime precedence is provider-native first. Canonical repo sources generate the runtime surfaces each provider loads.

## Rule Order

1. emergency deny/block rules
2. root runtime instructions (`AGENTS.md`, `CLAUDE.md`, or `GEMINI.md`)
3. provider-native skills when deployed
4. provider-native rule files when directly supported
5. canonical shared rules as source material
6. personal preferences

## Provider Notes

- Codex: `AGENTS.md` is authoritative; generated rule mirrors are not behavioral dependencies unless runtime support is verified.
- Claude: `CLAUDE.md`, rules, and skills are provider-native runtime surfaces.
- Antigravity/Gemini: `GEMINI.md` and deployed skills are primary runtime surfaces; rule mirrors are informational unless verified.

## Conflict Policy

- fail on duplicate rule or prompt names in same layer
- fail on missing `required_reads` targets
- fail on broken prompt metadata references
- fail when generated runtime surfaces drift from canonical sources
