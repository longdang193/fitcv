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
- Reuse existing components, semantic tokens, typography, spacing, icon family, and interaction patterns before adding design primitives.
- Prefer semantic HTML and native controls over custom scripted equivalents.
- Preserve keyboard operation, visible focus, descriptive labels, sufficient contrast, reduced-motion support, responsive layout, supported themes, and clear loading, empty, error, disabled, hover, focus, and pressed states where applicable.
- Material visual changes require fresh rendered or browser evidence at relevant viewport sizes and supported themes; source inspection alone is insufficient.
- Keep detailed style catalogs and checklists inside `ui-ux-pro-max`; do not duplicate them in repository rules or root instructions.
- If `ui-ux-pro-max` is unavailable, follow this rule and existing product design system. Do not block safe local fix.
