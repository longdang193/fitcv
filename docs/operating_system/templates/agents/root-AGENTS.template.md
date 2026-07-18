# Project Agent Instructions

This file is repo-wide instruction layer. More specific directory instructions override it.

## Core Rules

- Keep changes aligned with owning code, documentation, and configuration layers.
- Read scoped `AGENTS.md` files before modifying files under their directories.
- Treat source code and tests as authoritative when documentation or analysis tools disagree.
- Update tests and documentation when behavior or contracts change.
- Never expose private governance, credentials, agent memory, or internal tooling through public publication.
- For generated agent surfaces, edit canonical sources, then run required sync and verification commands.

## Agent Memory

Use configured MCP Memory Server only when current work can benefit from reusable project knowledge. Fetch memory for shared workflows, known invariants, recurring failures, resumed work, or high-risk changes. Store only verified, reusable lessons; never store transient progress, guesses, secrets, personal data, or facts already obvious from authoritative sources.

Memory informs work but never overrides explicit instructions, source code, tests, ADRs, or current governance. If memory tools are unavailable, continue source-first without recreating repository-file memory.

Detailed policy: `docs/operating_system/rules/agent-memory-rule.md`.

## Front-End Work

For material UI, UX, accessibility, responsive-layout, or visual-design work, use `ui-ux-pro-max` when available. Reuse existing components and design tokens, prefer semantic native controls, and verify affected states, keyboard access, focus, contrast, responsive behavior, reduced motion, and supported themes.

Skip skill for copy-only edits, mechanical selector changes, or isolated nonvisual logic. If unavailable, follow existing product design system and `docs/operating_system/rules/frontend-ui-rule.md`; do not block safe local fix.

## Code Intelligence

Use native code tools for small local work, Serena for exact symbols and references, and GitNexus for broad flows or impact. Do not query both by default. Source and tests win every conflict; unavailable tools never block safe source-first work.

- Serena runs with `--context codex --project-from-cwd`, `no-memories`, and `no-onboarding`. Never commit `.serena/` state.
- GitNexus remains optional and private-only. Check freshness before high-trust impact or refactor use; never make refresh a universal completion gate.
- Tests and CI own enforcement. `docs/architecture.md` and ADRs own durable architecture intent.
- Detailed policy: `docs/operating_system/tooling/code-intelligence-tools.md`.
