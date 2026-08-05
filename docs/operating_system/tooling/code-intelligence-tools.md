# Code Intelligence Tools

Use live code intelligence for discovery. Keep source, tests, and CI as truth.

## Ownership

| Need | Default tool |
|---|---|
| Current files and small local changes | native code tools |
| Broad unknown-location local concept search | optional Semble MCP |
| Exact local text confirmation | `rg` |
| Exact symbols, references, implementations, or diagnostics | Serena |
| Execution flows, dependencies, impact analysis, or cross-repository contracts | GitNexus |
| Repeated syntax-pattern preview | optional `sg` (ast-grep) |
| Unfamiliar external GitHub repository structure, architecture summaries, or focused repository Q&A | DeepWiki |
| Correctness and architecture enforcement | tests, static checks, CI |
| Durable architecture boundaries and rationale | `docs/architecture.md`, ADRs |

## Handoff

1. Do not query Serena and GitNexus for the same fact by default.
2. Start with Serena when exact symbol scope is known.
3. Start with GitNexus when broad flow or impact is unknown.
4. Move from GitNexus to Serena only for exact identified symbols.
5. Move from Serena to GitNexus only when local evidence exposes broader uncertainty.
6. Current source and tests win every conflict.
7. Tool absence or stale indexes never block safe source-first work.

## Optional Semble And ast-grep

- Semble is read-only and optional. Use only when broad local concept location
  is unknown; fall back to native search, Serena, or GitNexus.
- `sg` previews structural matches or JSON only. `apply_patch` remains sole
  source edit path.
- Semble MCP and ast-grep CLI are user-level choices, not repository or CI
  dependencies. See `docs/operating_system/procedures/code-intelligence-tools-setup.md`.

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

## GitNexus

- Keep GitNexus private-only and optional.
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
