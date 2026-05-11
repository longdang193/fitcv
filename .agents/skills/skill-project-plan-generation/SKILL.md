---
name: skill-project-plan-generation
description: Use when the user explicitly asks for a Markdown plan document and the
  compatibility planning layer is needed.
allowed-tools: []
hooks:
  pre: []
  post: []
required_reads:
- docs/operating_system/governance/repo-governance.md
- docs/operating_system/templates/implementation-plan-template.md
- repo_config/planning_artifact_schema.yaml
tags:
- skill
- skill-project-plan-generation
required_outputs:
- docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md
---

# Project Plan Generation Skill

## Status

This skill is a compatibility layer. Prefer `skill-writing-plans` when available.

## When to Apply

**Only apply this rule when the user explicitly requests to create a plan, roadmap, implementation plan, or structured planning document.**

Do not apply this rule to general documentation or other file generation tasks.

## Core Requirements

### Pre-Write Contract Check

Before writing any file, confirm all of the following:

- the canonical main-plan output path required by `required_outputs`:
  - `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md`
- the canonical repo plan file must be created first
- supporting docs under `docs/superpowers/plans/audit/` are optional and secondary
- if the requested file path conflicts with `required_outputs`, follow the skill
  contract unless the user explicitly overrides it
- do not satisfy this skill with an artifact-only plan

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
`repo_config/planning_artifact_schema.yaml` for `artifact_type: plan`.

```yaml
---
layer: intent | operating_system | workstream | change
artifact_type: plan
status: proposed | active | completed | superseded
template_id: implementation-plan            # optional but recommended when using the template
name: <short-plan-name>                     # recommended canonical identity field
parent_workstream: <workstream-name> | none # optional; do not restate once parent_thread is present
parent_thread: <thread-id>                  # preferred for change-layer plans
parent_spec: docs/superpowers/specs/<file>.md
targets:
  - <path>
related_features:
  - <feature_id>
related_stages:
  - <stage_id>
---
```

Rules:

- `layer`, `artifact_type`, and `status` are required.
- `artifact_type` must be `plan`.
- Prefer `name` as the canonical identity field for new plans.
- Use `template_id: implementation-plan` when the canonical implementation-plan template is the source shape.
- For change-layer plans, prefer `parent_thread` plus `parent_spec`.
- Do not restate `parent_workstream` when `parent_thread` is present; the validator derives workstream lineage from the thread.
- Use `parent_workstream: none` only for intent or operating_system scoped artifacts that intentionally have no workstream lineage.
- `targets`, `related_features`, and `related_stages` remain optional in the schema, but `targets` should be included whenever scope is cross-cutting or ambiguous.

### Markdown Standards

- Valid Markdown that passes linting.
- Proper heading hierarchy (H1 → H2 → H3).
- Use hyphens (`-`) for lists, NOT bullet points (`•`).
- One blank line between sections.

## Additional Documentation

For complete documentation, full plan structure templates, detailed examples (valid/invalid), step-by-step implementation guidelines, and extended notes, refer to: <LINK>`./docs/project-plan-guide.md`</LINK>
