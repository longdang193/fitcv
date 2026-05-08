---
name: command-execution-rule
description: Define command execution safety boundaries and escalation conditions.
alwaysApply: true
required_reads:
  - docs/operating_system/repo-governance.md
tags:
  - rule
  - safety
  - commands
---

# Command Execution Rule

Use source-first command execution.

## Requirements

- Prefer read-only inspection before mutating commands.
- Require explicit approval for mutating or risky commands unless platform policy auto-allows them.
- Keep working directories inside repo workspace.
- Use validator and sync scripts through canonical repo paths.
- Treat destructive actions, installs, network side effects, and long-running mutations as escalation points.

## Escalation Conditions

- command deletes or rewrites repo state
- command installs dependencies or changes environment state
- command pushes, publishes, or syncs external systems
- command scope is uncertain or blast radius is not bounded
