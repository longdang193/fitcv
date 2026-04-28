---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: starter-adoption-experience
threads:
  - starter-adoption-experience.prompt-template-metadata-and-validation
  - starter-adoption-experience.adoption-prompt-discoverability-without-duplication
specs:
  - docs/superpowers/specs/2026-04-28-planning-lineage-minimal-metadata-and-validator-spec.md
  - docs/superpowers/specs/2026-04-28-derived-thread-linkage-via-planning-lineage-spec.md
---

# Sample Execution Map

## Scope

- lineage-hardening and prompt-discoverability follow-up work under
  `starter-adoption-experience`

## Dependency Graph

- planning-lineage hardening should happen before stricter prompt-surface
  polish if the prompt changes depend on lineage contract wording

## Execution Waves

### Wave 1

- planning-lineage hardening

### Wave 2

- prompt-surface discoverability refinement

## Parallel Lanes

### Lane A

- lineage contract and validation work

### Lane B

- none yet; this sample stays sequential to avoid false precision

## Shared-Surface Risks

- `docs/operating_system/prompt_templates/`
- `docs/operating_system/repo-governance.md`

## Recommended Plan Breakdown

- one bounded plan per approved spec unless the shared surfaces justify a
  smaller follow-up split

## Orchestration Notes

- keep execution maps orchestration-only
- move detailed implementation steps into bounded plans
