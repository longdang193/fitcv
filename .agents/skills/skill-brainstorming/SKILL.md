---
name: skill-brainstorming
description: Use when exploring or defining new behavior, features, components, or
  non-trivial changes before implementation.
allowed-tools: []
hooks:
  pre: []
  post: []
required_reads:
- docs/operating_system/templates/task-start-routing-guide.md
- docs/operating_system/governance/repo-governance.md
tags:
- skill
- planning
- design
- skill-brainstorming
required_outputs:
- docs/superpowers/specs/
distribution_tier: starter_kit
---

# Brainstorming Ideas Into Designs

<HARD-GATE>
Do NOT write code or implement anything before:
1. design is presented
2. user explicitly approves
</HARD-GATE>

## Role

This skill produces design artifacts only.

## Canonical References

<MUST-READ>
- `docs/operating_system/templates/task-start-routing-guide.md`
- `docs/operating_system/templates/master-workstream-roadmap-template.md` when roadmap restructuring is in scope
- `docs/operating_system/templates/registered-workstream-list-template.md` when workstream ownership or registration is in scope
- `docs/operating_system/templates/bounded-change-thread-template.md` when bounded thread definition is in scope
- `docs/operating_system/templates/complete-specification-set-template.md`
- `docs/operating_system/templates/spec-authoring-map-template.md`
- `docs/operating_system/templates/detailed-specification-template.md`
- `docs/operating_system/templates/implementation-execution-map-template.md` when downstream execution orchestration is part of the design handoff
- `docs/operating_system/planning/planning-dispatch.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/lifecycle/feature-lifecycle.md`
- `docs/operating_system/governance/repo-governance.md`

If this file conflicts with canonical templates/governance, follow canonical docs.
</MUST-READ>

## Mandatory Read

<MUST-READ>
Before any skill-brainstorming output, read:

- canonical references above, especially:
  - `docs/operating_system/planning/planning-dispatch.md`
  - `docs/operating_system/lifecycle/doc-system-lifecycle.md`
  - `docs/operating_system/templates/task-start-routing-guide.md`
  - whichever standardized template matches the artifact being drafted
</MUST-READ>

## Lifecycle Compliance

- Start from the owning source layer before defining downstream design artifacts.
- Keep operating-system work on the operating-system branch; do not invent fake product feature ownership.
- Use the smallest truthful feature-folder reading set when feature-managed surfaces are involved.
- Keep source-of-truth and generated-surface boundaries explicit in proposed designs.
- Use the standardized template ladder so complete-spec-set, spec-authoring-map, detailed-spec, and execution-map artifacts stay structurally aligned.
- Keep section ownership distinct inside drafted artifacts: sequencing belongs in phases or waves, canonical rows belong in inventory or registry sections, constraints belong in invariant or scope sections, and proof belongs in validation sections.

## GitNexus Usage

Use GitNexus selectively for cross-file architecture lookup when it reduces
guessing.

- Prefer GitNexus for cross-cutting skill-brainstorming and dependency tracing.
- For small/local design changes, GitNexus is optional.
- Before high-trust GitNexus conclusions, check freshness via:
  - `.\\scripts\\get_gitnexus_freshness.ps1`
- If GitNexus is stale, use it only as advisory and keep source docs as truth.
- If GitNexus conflicts with source/docs/tests, trust source/docs/tests.
- If GitNexus has tooling or query issues, consult the `gitnexus-guide` skill first; if unresolved, continue source-first.

## Minimal Workflow

<MUST-DO>
1. Use `skill-planning-dispatch` triage (or verify it already exists).
2. Explore options and tradeoffs.
3. Recommend a design direction.
4. Present brainstorming output first.
5. Ask user: "Do you want a more detailed report using the brainstorming report template?"
6. If user says yes, save report using canonical bundle path `docs/superpowers/plans/brainstorming/<report_id>/` and:
   - scaffold with `.\\scripts\\new_brainstorming_report.ps1 -ReportId <report_id>`
   - write report to `docs/superpowers/plans/brainstorming/<report_id>/report.md` using `docs/operating_system/templates/brainstorming-detailed-report-template.md`
   - optionally capture supporting artifacts with `.\\scripts\\brainstorming_capture.ps1 -ReportId <report_id> -SourceFile <path> -Type input`
7. Author required roadmap/workstream/thread/spec/execution-map artifact using matching canonical template when requested.
8. Request approval before any implementation planning.
</MUST-DO>

## Output Paths

- specs -> `docs/superpowers/specs/`
- execution maps -> `docs/superpowers/execution_maps/`
- detailed brainstorming reports -> `docs/superpowers/plans/brainstorming/<report_id>/report.md`
- higher planning layers stay in their canonical docs/intent or docs/superpowers locations defined by the routing guide

## Guardrails

- Keep this skill focused on design decisions.
- Avoid duplicating lifecycle policy text already defined in templates/validators.
- Do not auto-generate detailed report unless user explicitly asks for it after brainstorming output.
