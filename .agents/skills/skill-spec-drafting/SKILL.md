---
name: skill-spec-drafting
description: Use when drafting or refining a detailed specification before implementation planning or coding.
allowed-tools: []
hooks:
  pre:
  - python scripts/hooks/run_validator.py --fast
  post:
  - python scripts/hooks/run_validator.py --fast
required_reads:
- docs/operating_system/templates/detailed-specification-template.md
- docs/operating_system/templates/task-start-routing-guide.md
- docs/operating_system/governance/repo-governance.md
- docs/operating_system/planning/planning-dispatch.md
tags:
- skill
- planning
- specification
- skill-spec-drafting
required_outputs:
- docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md
distribution_tier: starter_kit
---

# Spec Drafting

## Role

Draft and refine detailed specification artifacts only.

## Canonical References

<MUST-READ>
- `docs/operating_system/templates/detailed-specification-template.md`
- `docs/operating_system/templates/spec-authoring-map-template.md` when spec sequencing context exists
- `docs/operating_system/templates/task-start-routing-guide.md`
- `docs/operating_system/planning/planning-dispatch.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/lifecycle/feature-lifecycle.md`
- `docs/operating_system/governance/repo-governance.md`

If this file conflicts with canonical templates/governance, follow canonical docs.
</MUST-READ>

## Mandatory Read

<MUST-READ>
Before drafting a spec, read:

- canonical references above, especially:
  - `docs/operating_system/planning/planning-dispatch.md`
  - `docs/operating_system/lifecycle/doc-system-lifecycle.md`
  - `docs/operating_system/templates/task-start-routing-guide.md`
  - `docs/operating_system/templates/detailed-specification-template.md`
</MUST-READ>

## Lifecycle Compliance

- Start from owning source layer before drafting downstream spec artifacts.
- Preserve triage classification (`intent | operating_system | workstream | change`) in spec metadata.
- Keep source-of-truth and generated-surface boundaries explicit.
- Keep design decisions, invariants, and validation proof in their canonical sections.
- Keep non-goals explicit so implementation plans stay bounded.

## Preconditions

- triage exists (`skill-planning-dispatch`)
- scope is bounded enough for a single detailed spec artifact
- unresolved design decisions are identified

## Pre-Write Contract Check

Before writing any file, confirm all:

- canonical output path required by `required_outputs`:
  - `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md`
- spec must satisfy required sections from `docs/operating_system/templates/detailed-specification-template.md`
- spec must include explicit:
  - acceptance criteria (testable)
  - non-goals (out-of-scope boundaries)
  - risks and mitigations
  - evidence fields in validation plan

## Spec Output

Default path:

- `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md`

Frontmatter should follow canonical planning schema for `artifact_type: spec`:

```yaml
---
layer: intent | operating_system | workstream | change
artifact_type: spec
status: proposed | active | completed | superseded
template_id: detailed-specification            # optional but recommended
name: <short-spec-name>                        # recommended canonical identity field
parent_workstream: <workstream-name> | none    # optional
targets:
  - <path>
related_features:
  - <feature_id>
related_stages:
  - <stage_id>
---
```

## Required Sections

Minimum required body sections:

1. Goal
2. Key Deliverables
3. Task/Wave Breakdown
4. Design Decisions
5. Invariants
6. Validation Plan
7. Completion Criteria

Add bounded sections for spec quality:

- Acceptance Criteria
- Non-Goals
- Risks and Mitigations

## Validation Plan Evidence Shape

For each proof target, record:

- proof target: <claim>
  - method: <test, inspection, run, comparison>
  - evidence: <expected proof artifact/output/path>

## Handoff Rules

- If design unresolved across multiple threads/specs, route to `skill-brainstorming`.
- After spec approval and design closure, hand off to `skill-writing-plans`.
- Do not produce implementation plan in this skill.
- Do not write code in this skill.

## Guardrails

- Keep this skill spec-only.
- Keep acceptance criteria observable and testable.
- Keep non-goals explicit; avoid scope creep.
- Avoid duplicating lifecycle policy text already owned by canonical docs.
