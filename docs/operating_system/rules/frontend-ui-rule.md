---
name: frontend-ui
description: Route material front-end work through repository UI and accessibility requirements.
alwaysApply: true
required_reads: []
distribution_tier: starter_kit
---

# Front-End UI Rule

- Use `ui-ux-pro-max` when available for new screens, substantial restyling, design systems, responsive layout, interaction design, accessibility remediation, or visual critique.
- Skip skill invocation for copy-only edits, mechanical selector changes, or isolated nonvisual front-end logic.
- Prefer intrinsic, relational, and bounded layout over fixed coordinates, magic offsets, fixed heights on text-bearing containers, and duplicated calculations. Use Grid, Flexbox, `gap`, `minmax()`, `clamp()`, `auto`, `fr`, `aspect-ratio`, and wrapping where they express the relationship directly.
- Declare each layout relationship once. Parents own child arrangement; children own internal layout and behavior. Reuse existing components, semantic tokens, typography, spacing, icon family, and interaction patterns, but do not create abstractions or tokens for one-off values.
- Design components to reflow in narrow containers and under long, localized, missing, or zoomed content. Use container queries when behavior depends on container size; use media queries when behavior depends on viewport or device capability.
- Prefer semantic HTML and native controls over custom scripted equivalents.
- Preserve keyboard operation, visible focus, descriptive labels, sufficient contrast, reduced-motion support, responsive layout, supported themes, and clear loading, empty, error, disabled, hover, focus, and pressed states where applicable.
- Among equally correct and safe options, minimize total user burden through safe defaults, recognition over recall, progressive disclosure, error prevention, and reversible actions.
- Material visual changes require fresh rendered or browser evidence for affected container sizes, supported themes, long content and zoom, keyboard and focus behavior, console errors, and unexpected layout shifts. Reuse existing visual-regression tooling; do not add tooling solely for this rule. Source inspection alone is insufficient.
- Use Playwright MCP for repeatable navigation, forms, accessibility snapshots, viewport checks, and screenshots. Use Chrome DevTools MCP for existing-session inspection, console and network evidence, computed layout and styles, Lighthouse, and performance diagnosis. When both are needed, reproduce and verify with Playwright MCP and diagnose with Chrome DevTools MCP; do not duplicate the same check in both.
- Browser MCP sessions provide live evidence, not durable regression coverage. Preserve important behavior in the existing Playwright Test or end-to-end suite when one exists; do not add a new test framework solely for this rule.
- Keep detailed style catalogs and checklists inside `ui-ux-pro-max`; do not duplicate them in repository rules or root instructions.
- If `ui-ux-pro-max` is unavailable, follow this rule and existing product design system. Do not block safe local fix.
