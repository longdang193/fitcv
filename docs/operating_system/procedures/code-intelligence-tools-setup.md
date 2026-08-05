# Optional Code Intelligence Setup

## Semble MCP

Configure Semble only in user-level MCP client settings. Do not commit API
keys, repository `.codex` configuration, or run `semble init`. Restart client,
then run one broad local search. If unavailable, use native search, Serena, or
GitNexus. If Semble creates local cache, keep it user-private or ignore it;
remove it through client tooling when no longer needed.

## ast-grep CLI

Install `sg` through user or OS package management. Run read-only preview or
JSON output, then edit selected files with `apply_patch`. Do not use ast-grep
rewrite commands. ast-grep MCP stays deferred until an explicit harness
improvement proves repeated complex AST-rule authoring friction.
