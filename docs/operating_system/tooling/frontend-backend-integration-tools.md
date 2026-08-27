# Frontend-Backend Integration Tools

Use one primary method per trigger. Load supporting skills or tools only when boundary or claim requires them. Source, canonical contracts, tests, and runtime evidence remain authoritative.

Lifecycle ownership remains in `docs/operating_system/planning/planning-dispatch.md`.
This document owns frontend/backend/shared-contract integration triggers,
mapping, and evidence only; it does not define the general delivery lifecycle
or runtime tool-resolution policy.

## Artifact Ownership

| Artifact | Owner |
|---|---|
| exploratory UI intent and open questions | draft specification |
| prototype findings | validation evidence in current specification |
| approved behavior and state transitions | final specification |
| durable visual primitives | project design system |
| transport schema | canonical contract such as OpenAPI |
| temporary contract-to-UI mapping and blockers | colocated `*.integration.md` sidecar |
| implementation behavior | source and tests |
| deployed behavior | runtime evidence |

## Routing Matrix

| Trigger | Owning rule or invariant source | Primary method | Conditional support | Required evidence | Next handoff |
|---|---|---|---|---|---|
| problem or options unclear | planning dispatch | `skill-brainstorming` | external documentation capability for version-specific library facts | grounded recommendation or resolved questions | `skill-spec-drafting` when durable behavior needs approval |
| draft or final behavior needs definition | documentation contracts and planning dispatch | `skill-spec-drafting` | prototype, external documentation capability, `skill-backend-verification` claim selection | approved behavior, states, boundaries, validation intent | `skill-writing-plans` |
| material backend behavior changes | `docs/operating_system/rules/backend-verification-rule.md` | `skill-backend-verification` | real dependencies, `skill-systematic-debugging`, `skill-test-driven-development` | direct boundary, business/failure, state, automated proof | consumer integration or final verification |
| frontend crosses backend contract or route | `docs/operating_system/rules/frontend-backend-integration-rule.md` | `skill-full-stack-integration` | `skill-backend-verification`, `skill-frontend-component-engineering` | canonical contract, backend proof, frontend tests, browser flow | `skill-verification-before-completion` |
| stateful frontend component or page | `docs/operating_system/rules/frontend-ui-rule.md` | `skill-frontend-component-engineering` | selected applicable design skill (`impeccable`, `ui-ux-pro-max`, or `skill-distinctive-frontend-design`), external documentation capability | state ownership, tests, required rendered/accessibility evidence | integration or final verification |
| approved plan execution | planning dispatch | `skill-executing-plans` | `skill-subagent-driven-development` only with authorized per-task commits | task-local proof | `skill-verification-before-completion` |
| independent disjoint lanes | plan execution ownership | `skill-dispatching-parallel-agents` | platform subagent tools | lane-local and combined proof | `skill-executing-plans` |
| failure or unexpected behavior | source and tests | `skill-systematic-debugging` | trace, browser diagnosis, code intelligence | reproduced root cause and regression proof | implementation skill |
| completion claim | approved plan/specification | `skill-verification-before-completion` | affected validators, browser/runtime evidence | fresh claim-to-evidence map | authorized branch finishing |

## MCP Boundaries

### External Documentation Capability

Use when pinned local source or maintained docs do not answer current version-specific external-library question. Record library and relevant version. Do not use for project architecture, local behavior, or contract ownership. Resolve through `docs/operating_system/tooling/runtime-tool-resolution.md` and treat output as advisory.

### Existing Tools

- native search: current files and small local scope
- symbol-aware code intelligence: exact symbols, references, implementations, diagnostics
- flow/impact analysis: broad flows, route consumers, or impact when fresh
- browser-interaction capability: repeatable browser flows, accessibility snapshots, viewports, screenshots when available
- native test runner and CI: durable enforcement

External service, API-client, database, and repository capabilities remain
target-project options with active consumers, not Starter defaults.

### DeepAgents

Current `dcode-project` forces `--no-mcp`. Codex performs required MCP calls and
passes only validated `codex.mcp.handoff.v1` facts to DeepAgents; selected MCP
IDs narrow handoff provenance and never grant DeepAgents tools.

## Source-First Fallback

If optional capability is unavailable, continue with pinned documentation, local source, canonical contracts, tests, existing command-line tools, and runtime systems. Do not create substitute truth layers or downgrade mandatory evidence.
