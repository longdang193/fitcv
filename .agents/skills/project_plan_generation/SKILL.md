---
name: project_plan_generation
description: Use when the user explicitly asks for a Markdown plan document and the
  compatibility planning layer is needed.
allowed-tools: []
hooks:
  pre: []
  post: []
required_reads: []
required_outputs: []
related_skills: []
tags:
- skill
- project_plan_generation
---

# Project Plan Generation Skill

## Status

This skill is a compatibility layer. Prefer `writing-plans` when available.

## When to Apply

**Only apply this rule when the user explicitly requests to create a plan, roadmap, implementation plan, or structured planning document.**

Do not apply this rule to general documentation or other file generation tasks.

## Core Requirements

### File Locations

- **Main plans**: `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md`
- **Supporting docs**: `docs/superpowers/plans/audit/<doc-name>.md`
- **All files MUST be `.md` format** (unless user explicitly requests otherwise)

### File Structure

```text
docs/superpowers/plans/
    ├── YYYY-MM-DD-HH-MM-<topic>-plan.md
    └── audit/
        └── <supporting-docs>.md
```

### Doc-System Alignment

Every plan must anchor to the source-of-truth layers:

- `code/` → real truth
- `docs/intent/*.md` → project purpose and outcome sources
- `docs/operating_system/*.md` → repo method and governance sources
- `docs/stages/<stage_id>.source.yaml` → human-owned stage source when stage-aware work is in scope
- `docs/stages/<stage_id>.yaml` → generated stage contract when stage-aware work is in scope
- `docs/features/<feature_id>/feature.source.yaml` → human-owned feature source
- `docs/features/<feature_id>/<feature_id>.yaml` → generated current feature contract
- `docs/features/<feature_id>/lineage.generated.yaml` → generated feature-local evidence when relevant
- `docs/features/<feature_id>/` → feature-specific explanation and history
- `docs/*.md` → cross-cutting product explanation and rationale
- `README.md` → navigation
- `docs/generated/*` → generated discovery

Before saving the plan, explicitly name:

- any affected `docs/intent/*.md` when the plan layer is `intent`
- any affected `docs/operating_system/*.md` when the plan layer is `operating_system`
- the affected `docs/stages/<stage_id>.source.yaml` and generated stage contract when stage-aware work is in scope
- the affected `docs/features/<feature_id>/feature.source.yaml`
- the generated `docs/features/<feature_id>/<feature_id>.yaml`
- `docs/features/<feature_id>/lineage.generated.yaml` when evidence or generated history inputs are affected
- `docs/features/<feature_id>/history.md` or other focused docs under `docs/features/<feature_id>/`
- any cross-feature docs under `docs/*.md`
- `README.md` if navigation changes
- generated outputs that must be refreshed

`<feature_id>` is placeholder notation in plan instructions; use the concrete
generated feature-id YAML path in real plans.

Do not write a plan that says only "update docs". Name exact doc targets.

### Compatibility Metadata Rule

Even when this compatibility skill is used, new or touched plans should follow
the current plan metadata contract:

```yaml
---
layer: intent | operating_system | workstream | change
artifact_type: plan
status: proposed | active | completed | superseded
parent_workstream: <id> | none
targets:
  - <path>
related_features:
  - <feature_id>
related_stages:
  - <stage_id>
---
```

Rules:

- `layer`, `artifact_type`, and `status` are required
- `targets` is required when the plan is cross-cutting or otherwise ambiguous in scope
- `targets` may be omitted only when the plan is narrow and obviously local

### Markdown Standards

- Valid Markdown that passes linting.
- Proper heading hierarchy (H1 → H2 → H3).
- Use hyphens (`-`) for lists, NOT bullet points (`•`).
- One blank line between sections.

## Additional Documentation

For complete documentation, full plan structure templates, detailed examples (valid/invalid), step-by-step implementation guidelines, and extended notes, refer to:
`./docs/project-plan-guide.md`

