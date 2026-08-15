# Code Intelligence Tools

Use live code intelligence for discovery. Keep source, tests, and CI as truth.

## Ownership

| Need | Default tool |
|---|---|
| Current files and small local changes | native code tools |
| Exact symbols, references, implementations, or diagnostics | Serena |
| Unknown-location code concept or similar implementation | `semble_codebase_search` |
| Structural search or safe edit preview | `ast_grep_preview` |
| Execution flows, dependencies, impact analysis, or cross-repository contracts | GitNexus |
| Unfamiliar external GitHub repository structure, architecture summaries, or focused repository Q&A | DeepWiki |
| Correctness and architecture enforcement | tests, static checks, CI |
| Durable architecture boundaries and rationale | `docs/architecture.md`, ADRs |

## Handoff

1. Start with native tools for current files and bounded scope.
2. Use Serena when exact symbol scope is known.
3. Use `semble_codebase_search` when location is unknown or similar code is needed.
4. Use `ast_grep_preview` only for structural preview; source remains edit truth.
5. Use optional GitNexus only when read-only private binding is available and broader flow or impact remains unknown.
6. Do not query Serena, Semble, and GitNexus for the same fact by default.
7. Current source and tests win every conflict.
8. Tool absence or stale indexes never block safe source-first work.

## DeepWiki Workflow

1. Use `read_wiki_structure` for a low-cost topic map.
2. Use `ask_question` for focused architecture or repository questions.
3. Use `read_wiki_contents` only when full generated documentation is required.
4. Hand off to local source inspection and Serena before implementation.
5. Hand off to GitNexus before broad impact analysis, dependency tracing, or refactoring decisions.
6. Treat tests and pinned source code as final source of truth.

## Serena

- Tested with Serena `1.6.0` installed by `uv tool install -p 3.13 serena-agent`.
- Run with `--context codex --project-from-cwd`.
- Keep `no-memories` and `no-onboarding` active.
- Keep dashboard disabled unless troubleshooting locally.
- Never commit `.serena/`, memories, indexes, onboarding output, or generated wikis.

## Semble And AST-Grep

- Use `semble_codebase_search` for broad unknown-location code discovery or similar implementation lookup.
- Use `ast_grep_preview` for structural matching or edit preview before a source edit.
- Neither replaces Serena for exact references or native source inspection for current behavior.
- Both are optional; fall back to `rg`, source inspection, and tests when unavailable.

## GitNexus

- GitNexus is not a starter default. Use it only through a private read-only binding when one is available.
- Limit use to `query`, `context`, `impact`, and `api_impact`; do not use `rename`, `group_sync`, or write operations.
- Check freshness with `scripts/get_gitnexus_freshness.ps1` before high-trust impact or refactor use.
- Refresh only when graph evidence materially helps.
- Never make GitNexus refresh a universal completion gate.
- Never publish `.gitnexus/` or GitNexus-specific internal notes.

## DeepWiki

- Use DeepWiki for advisory orientation in unfamiliar external GitHub repositories, not current working-tree analysis.
- Treat output as advisory when source commit or freshness is unknown.
- Verify APIs, security assumptions, runtime behavior, and tests against pinned upstream source.
- Do not use DeepWiki as proof of exact references, diagnostics, test results, dependency impact, or refactor safety.

## Skill Association

Use DeepWiki directly with:

- `skill-brainstorming`
- `skill-spec-drafting`
- `skill-writing-plans`
- `skill-plan-document-reviewer`
- `skill-full-stack-integration`

Use DeepWiki conditionally, only when unfamiliar external repository context is material, with:

- `skill-systematic-debugging`
- `skill-refactoring-assessment`
- `skill-performance-optimization`
- `skill-code-standards`

Do not associate DeepWiki with execution, verification, testing, code-review, or branch-completion skills. Do not create a separate DeepWiki skill; this policy owns tool selection and handoff rules.

## Boundary

No code-intelligence tool owns architecture or runtime behavior. Use `docs/architecture.md`
for durable system shape, ADRs for significant decisions, and native tests/CI
for enforceable boundaries.

## Executor Boundary

Tool IDs and permissions belong to active executor. Do not assume a Codex MCP
tool, allowlist, approval setting, or result shape exists in DeepAgents. Current
`dcode-project` runs DeepAgents with `--no-mcp`; available native capabilities
depend on launch mode and task context, and current launcher grants no
runtime-authority flags. Call required MCP through Codex, write
`codex.mcp.handoff.v1` under user-local handoff root, then pass its path to
`dcode-project --handoff-file`; launcher validates file and injects sanitized
facts into task text. `--mcp-select` narrows Codex provenance only;
it does not project tools into DeepAgents. Never paste credentials, raw tool
configuration, cookies, headers, or approval authority into an executor prompt.
