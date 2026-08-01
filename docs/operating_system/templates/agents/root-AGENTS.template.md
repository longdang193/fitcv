# Project Agent Instructions

This file is repo-wide instruction layer. More specific directory instructions override it.

## Core Rules

- Keep changes aligned with owning code, documentation, and configuration layers.
- Read scoped `AGENTS.md` files before modifying files under their directories.
- Treat source code and tests as authoritative when documentation or analysis tools disagree.
- Update tests and documentation when behavior or contracts change.
- Never expose private governance, credentials, agent memory, or internal tooling through public publication.
- For generated agent surfaces, edit canonical sources, then run required sync and verification commands.

## Project Design Rules

### Use SSOT

Each fact, rule, setting, or policy should have one main source.

Do not store the same information in several places. Other parts of the project should read from the main source instead of copying it.

### Build Reusable Components

Do not create a new solution for every similar case.

Create shared components, functions, and rules that can be reused in different parts of the project.

### Follow the Principle of Permanence

Extend systems in a way that preserves as many existing properties, rules, contracts, and valid behaviors as possible.

Example:

If a component initially supports light mode and is later extended to support dark mode, dark-mode support should not require a separate component or change the component’s existing behavior. The same component contract should remain valid, while theme-specific values are supplied through configuration.

### Maintain Symmetry

Similar or opposite cases should use the same structure and logic.

Examples:

- light mode and dark mode
- day mode and night mode
- enable and disable
- import and export
- create and delete
- forward and reverse

Do not build two separate systems when one shared system can support both cases.

Represent the difference through:

- configuration
- parameters
- themes
- data
- shared strategies

Example:

Light mode and dark mode should use the same UI components. Only the theme values should change.

### Avoid Unnecessary Special Cases

Before adding separate logic, ask:

> Is this case truly different, or can the existing general solution handle it?

Prefer one consistent system that works for all equivalent cases.

## Agent Memory

Use configured MCP Memory Server only when current work can benefit from reusable project knowledge. Fetch memory for shared workflows, known invariants, recurring failures, resumed work, or high-risk changes. Store only verified, reusable lessons; never store transient progress, guesses, secrets, personal data, or facts already obvious from authoritative sources.

Memory informs work but never overrides explicit instructions, source code, tests, ADRs, or current governance. If memory tools are unavailable, continue source-first without recreating repository-file memory.

Detailed policy: `docs/operating_system/rules/agent-memory-rule.md`.

## Front-End Work

For material UI, UX, accessibility, responsive-layout, or visual-design work, use `ui-ux-pro-max` when available. Reuse existing components and design tokens, prefer semantic native controls, and verify affected states, keyboard access, focus, contrast, responsive behavior, reduced motion, and supported themes.

When a matching `*.integration.md` exists, use `skill-full-stack-integration`. Integration notes own temporary UI intent and acceptance evidence, not transport schemas; canonical schemas, generated clients, backend routes, and tests establish current behavior. Report any conflict and affected owners, then ask the user to decide before implementation.

When browser MCPs are available, use Playwright MCP for repeatable user flows, accessibility snapshots, viewport checks, and screenshots; use Chrome DevTools MCP for console, network, computed layout and styles, Lighthouse, and performance diagnosis. Use both only when their roles differ. Browser evidence does not replace committed regression tests.

Skip skill for copy-only edits, mechanical selector changes, or isolated nonvisual logic. If unavailable, follow existing product design system and `docs/operating_system/rules/frontend-ui-rule.md`; do not block safe local fix.

## Code Intelligence

Use native code tools for small local work, Serena for exact symbols and references, and GitNexus for broad flows or impact. Do not query both by default. Source and tests win every conflict; unavailable tools never block safe source-first work.

- Serena runs with `--context codex --project-from-cwd`, `no-memories`, and `no-onboarding`. Never commit `.serena/` state.
- GitNexus remains optional and private-only. Check freshness before high-trust impact or refactor use; never make refresh a universal completion gate.
- Tests and CI own enforcement. `docs/architecture.md` and ADRs own durable architecture intent.
- Detailed policy: `docs/operating_system/tooling/code-intelligence-tools.md`.
