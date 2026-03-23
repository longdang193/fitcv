---
name: project_plan_generation
description: "Generate project plans in Markdown format with proper structure and linting compliance"
---

# Project Plan Generation Skill

## When to Apply

**Only apply this rule when the user explicitly requests to create a plan, roadmap, implementation plan, or structured planning document.**

Do not apply this rule to general documentation or other file generation tasks.

## Core Requirements

### File Locations

- **Main plans**: `./plans/<plan-name>.md` (kebab-case filenames)
- **Supporting docs**: `./plans/audit/<doc-name>.md`
- **All files MUST be `.md` format** (unless user explicitly requests otherwise)

### File Structure

```text
./plans/
    ├── <main-plan>.md
    └── audit/
        └── <supporting-docs>.md
```

### Markdown Standards

- Valid Markdown that passes linting.
- Proper heading hierarchy (H1 → H2 → H3).
- Use hyphens (`-`) for lists, NOT bullet points (`•`).
- One blank line between sections.

## Additional Documentation

For complete documentation, full plan structure templates, detailed examples (valid/invalid), step-by-step implementation guidelines, and extended notes, refer to:
`./docs/project-plan-guide.md`
