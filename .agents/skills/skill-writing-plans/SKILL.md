---
name: skill-writing-plans
description: Use when a confirmed design needs a multi-step implementation plan before
  code changes begin.
allowed-tools: []
hooks:
  pre:
  - python scripts/hooks/run_validator.py --fast
  post:
  - python scripts/hooks/run_validator.py --fast
required_reads:
- docs/operating_system/templates/implementation-plan-template.md
- docs/operating_system/templates/task-start-routing-guide.md
- docs/operating_system/governance/repo-governance.md
- repo_config/planning_artifact_schema.yaml
tags:
- skill
- planning
- implementation-plan
- skill-writing-plans
required_outputs:
- docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md
---

# Writing Plans

## Role

Create executable implementation plans from approved design context.

## Canonical References

<MUST-READ>
- `docs/operating_system/templates/implementation-plan-template.md`
- `docs/operating_system/templates/implementation-execution-map-template.md` when a plan is being authored from multi-lane orchestration context
- `docs/operating_system/templates/task-start-routing-guide.md`
- `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/lifecycle/feature-lifecycle.md`
- `docs/operating_system/governance/repo-governance.md`

If this file conflicts with canonical templates/governance, follow canonical docs.
</MUST-READ>

## Mandatory Read

<MUST-READ>
Before drafting a plan, read:

- canonical references above, especially:
  - `docs/operating_system/planning/planning-dispatch.md`
  - `docs/operating_system/lifecycle/doc-system-lifecycle.md`
  - `docs/operating_system/templates/task-start-routing-guide.md`
  - `docs/operating_system/templates/implementation-plan-template.md`
  - `docs/operating_system/templates/implementation-execution-map-template.md` when upstream orchestration exists
</MUST-READ>

## Lifecycle Compliance

- Preserve upstream layer classification from triage when authoring plan metadata.
- Use `parent_workstream: none` only when intent or operating-system lineage is intentionally workstream-free.
- Name exact source, generated, and cross-cutting doc targets when they clarify scope.
- Respect source-vs-generated ownership boundaries; generated feature, stage, history, and discovery surfaces must derive from owning sources.
- Keep implementation plans structurally aligned with the standardized `Goal / Key Deliverables / Task/Wave Breakdown / Verification` template shape.

## Pre-Write Contract Check

Before writing any file, confirm all of the following:

- the canonical output path required by `required_outputs`:
  - `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md`
- the canonical file must be created first; supporting artifacts are optional and
  secondary
- the plan must follow the implementation plan template shape, including:
  - frontmatter that satisfies `repo_config/planning_artifact_schema.yaml` for `artifact_type: plan`
  - required sections from `docs/operating_system/templates/implementation-plan-template.md`
- if an implementation-execution-map already owns multi-lane sequencing, carry that orchestration into task/wave ordering rather than inventing a parallel structure
- if the requested file path conflicts with `required_outputs`, follow the skill
  contract unless the user explicitly overrides it

Do not create an artifact-only plan when this skill applies.

## GitNexus Usage

Use GitNexus when plan quality depends on cross-file dependency awareness.

- Prefer GitNexus for broad impact mapping and shared-module dependency checks.
- For narrowly scoped plans, GitNexus is optional.
- Before high-trust use, check freshness:
  - `.\\scripts\\get_gitnexus_freshness.ps1`
- If stale, use GitNexus only as advisory and keep the plan source-first.
- If GitNexus conflicts with source/docs/tests, trust source/docs/tests.
- If GitNexus has tooling or query issues, consult the `gitnexus-guide` skill first; if unresolved, continue source-first.

## Preconditions

- triage exists (`skill-planning-dispatch`)
- design context exists (approved detailed spec or approved execution-map context)
- scope is bounded enough for implementation

## Plan Output

Default path:

- `docs/superpowers/plans/YYYY-MM-DD-HH-MM-<topic>-plan.md`

Use the canonical implementation plan template and fill exact paths, tests, and commands.

Plan frontmatter should follow the canonical planning schema for `artifact_type: plan`:

```yaml
---
layer: intent | operating_system | workstream | change
artifact_type: plan
status: proposed | active | completed | superseded
template_id: implementation-plan            # optional but recommended when using the template
name: <short-plan-name>                     # recommended canonical identity field
parent_workstream: <workstream-name> | none # optional; use for intent/operating_system/workstream scoped plans
parent_thread: <thread-id>                  # use for change-layer plans
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

- `layer`, `artifact_type`, and `status` are required for plans.
- `artifact_type` must be `plan`.
- Use `name` as the preferred canonical identity field for new plans.
- Use `template_id: implementation-plan` when the canonical implementation-plan template is the source shape.
- For change-layer plans, prefer `parent_thread` and `parent_spec`.
- Do not restate `parent_workstream` when `parent_thread` is present; the validator derives workstream lineage from the thread.
- Use `parent_workstream: none` only for intent or operating_system scoped artifacts that intentionally have no workstream lineage.
- Include `targets`, `related_features`, and `related_stages` whenever they clarify scope; treat `targets` as effectively required for cross-cutting work.

## Minimal Workflow

1. confirm preconditions
2. complete the pre-write contract check
3. map files/tests/docs affected
4. write small testable tasks or waves using the standardized plan template shape
5. include validation commands and rollback notes where needed
6. hand off to `skill-executing-plans` (or `skill-subagent-driven-development`)

## Guardrails

- No implementation code in this skill.
- Do not duplicate lifecycle/routing policy text here.
- Keep guidance concise; canonical template carries required structure.
- Plan tasks so later execution can pick next actions via the next-action gate prompt.
- Do not author plan steps that require inventing unrelated execution actions.
- Satisfy `required_outputs` before creating optional supporting artifacts.
