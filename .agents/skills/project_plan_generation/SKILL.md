---
name: project_plan_generation
description: "Generate project plans in Markdown format with proper structure and linting compliance"
---

# Project Plan Generation Skill

## Status

This skill is a compatibility layer. Prefer `writing-plans` when available.

## When to Apply

**Only apply this rule when the user explicitly requests to create a plan, roadmap, implementation plan, or structured planning document.**

Do not apply this rule to general documentation or other file generation tasks.

## Core Requirements

### File Locations

- **Main plans**: `docs/superpowers/archive/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md`
- **Supporting docs**: `docs/superpowers/archive/plans/audit/<doc-name>.md`
- **All files MUST be `.md` format** (unless user explicitly requests otherwise)

### File Structure

```text
docs/superpowers/archive/plans/
    ├── YYYY-MM-DD-HH-MM-<topic>-plan.md
    └── audit/
        └── <supporting-docs>.md
```

### Doc-System Alignment

Every plan must anchor to the source-of-truth layers:

- `code/` → real truth
- `docs/features/<feature_id>/<feature_id>.yaml` → current feature contract
- `docs/features/<feature_id>/` → feature-specific explanation and history
- `docs/*.md` → cross-cutting explanation and rationale
- `README.md` → navigation
- `docs/generated/*` → generated discovery

Before saving the plan, explicitly name:

- the affected `docs/features/<feature_id>/<feature_id>.yaml`
- `docs/features/<feature_id>/history.md` or other focused docs under `docs/features/<feature_id>/`
- any cross-feature docs under `docs/*.md`
- `README.md` if navigation changes
- generated outputs that must be refreshed

Do not write a plan that says only "update docs". Name exact doc targets.

### Markdown Standards

- Valid Markdown that passes linting.
- Proper heading hierarchy (H1 → H2 → H3).
- Use hyphens (`-`) for lists, NOT bullet points (`•`).
- One blank line between sections.

## Additional Documentation

For complete documentation, full plan structure templates, detailed examples (valid/invalid), step-by-step implementation guidelines, and extended notes, refer to:
`./docs/project-plan-guide.md`

