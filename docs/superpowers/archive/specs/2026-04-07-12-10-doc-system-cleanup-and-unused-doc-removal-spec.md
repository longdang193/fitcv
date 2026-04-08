---
feature_type: modify
feature_name: documentation_system
status: draft
summary: "Clean the docs system by removing truly orphaned docs, fixing broken navigation, and resolving the partial stage-doc adoption layer without deleting grandfathered referenced material."
invariants:
  - "No document is removed if it is still referenced anywhere in the docs tree, README, feature YAMLs, stage YAMLs, specs, or plans."
  - "The codebase remains the source of truth; docs must describe and index existing contracts rather than invent new runtime behavior."
  - "Grandfathered legacy docs may remain in place when they are still referenced, even if their naming predates the current doc-system conventions."
  - "Generated discovery docs must remain derived outputs rather than hand-maintained source documents."
  - "Feature YAMLs and stage YAMLs must remain the structured contract layer for their respective domains."
---

# Doc-System Cleanup And Unused-Doc Removal Spec

## Affected Feature Contracts

- [docs/features/admin_control_plane_core/admin_control_plane_core.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/features/admin_control_plane_core/admin_control_plane_core.yaml)
- [docs/features/cv_system/cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/features/cv_system/cv_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/features/pipeline_performance/pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/features/pipeline_performance/pipeline_performance.yaml)
- [docs/features/settings_system/settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/features/settings_system/settings_system.yaml)
- [docs/features/trigger_run_management/trigger_run_management.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/features/trigger_run_management/trigger_run_management.yaml)

## Stage Contracts

- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/stages/ranking.yaml)

## Triage

Feature type: MODIFY  
Summary: Remove the one truly orphaned spec, fix broken doc navigation, and turn the partially adopted stage-doc layer into a coherent discoverable part of the docs system without mass-deleting grandfathered referenced docs.  
Reasoning: The current doc system is mostly healthy, but it has three verified drifts: one unreferenced legacy spec, one broken README navigation path, and a stage-doc layer that has been partially adopted but is not represented in generated discovery. This is cleanup and contract alignment work within the existing documentation system, not a new feature.  
Invariants:
- Only genuinely unreachable docs are eligible for removal.
- Root docs that are still referenced by README or feature YAMLs stay in place unless their references are updated in the same change.
- Legacy `*-design.md` and `*-implementation.md` docs remain valid when they are still linked from current docs.
- Stage docs must be either explicitly supported and discoverable or clearly demoted from the active doc-system contract.
- Generated discovery must match the active layers of the documentation system.
Dependencies:
- `README.md`
- `docs/generated/*`
- feature YAML refs
- stage YAML refs
- spec/plan cross-links
Affected stages:
- `ranking`
Affected features:
- `admin_control_plane_core`
- `cv_system`
- `inspection_debugging`
- `pipeline_performance`
- `settings_system`
- `trigger_run_management`
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
    - `docs/features/pipeline_performance/pipeline_performance.yaml`
    - `docs/features/settings_system/settings_system.yaml`
    - `docs/features/trigger_run_management/trigger_run_management.yaml`
  feature_history:
    - none
  feature_docs:
    - none
  cross_cutting_docs:
    - `README.md`
    - `docs/FitCV-pipeline.md`
    - `docs/fitcv-control-plane-setup.md`
  readme:
    - `README.md`
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
    - `docs/generated/feature_capabilities_index.yaml`
    - `docs/generated/feature_dependency_graph.yaml`
    - `docs/generated/features_by_status.yaml`
    - `docs/generated/stages_index.yaml` (new)
    - `docs/generated/stage_overview.md` (new)
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Problem Statement

The current docs system is not broadly broken, but it has a few verified integrity problems that make it harder to trust:

1. One spec is truly orphaned and appears to describe a superseded contract:
   - [2026-03-27-centralized-cv-generation-config-design.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/superpowers/specs/2026-03-27-centralized-cv-generation-config-design.md)
2. The README links to a `docs/superpowers/decisions/` directory that does not exist.
3. The stage-doc layer is only partially adopted:
   - [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/stages/ranking.yaml) exists and is referenced
   - but there is no generated stage discovery analogous to the generated feature discovery
4. Many legacy `*-design.md` and `*-implementation.md` docs still exist, but most of them are still referenced by current feature YAMLs, stage YAMLs, specs, or plans.

Without a targeted cleanup, the docs tree sends mixed signals:

- some old docs are truly obsolete
- some old docs are still valid but look obsolete
- the README points to at least one dead location
- the stage-doc layer exists without being clearly discoverable

## Audit Findings

### Docs That Are Still In Use

The following categories are still meaningfully used and should not be treated as unused just because they use older naming:

- root cross-cutting docs:
  - [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/FitCV-pipeline.md)
  - [docs/fitcv-control-plane-setup.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/fitcv-control-plane-setup.md)
- feature YAMLs under [docs/features](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/features)
- generated feature discovery docs under [docs/generated](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/generated)
- nearly all existing legacy specs and plans under [docs/superpowers/specs](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/superpowers/specs) and [docs/superpowers/plans](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/superpowers/plans)

### Verified Unused / Broken Items

The review found only one truly orphaned superpowers spec:

- [2026-03-27-centralized-cv-generation-config-design.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/superpowers/specs/2026-03-27-centralized-cv-generation-config-design.md)

The review also found one broken navigation target:

- `docs/superpowers/decisions/` is referenced from `README.md` but the directory is absent

### Partial Stage-Layer Adoption

The repo currently has exactly one stage YAML:

- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/stages/ranking.yaml)

This stage contract is not unused. It is referenced from current docs, but the documentation system does not yet surface the stage layer through generated discovery or clear top-level navigation.

That leaves the stage layer in an ambiguous state:

- active enough to exist and be linked
- incomplete enough to be hard to discover

## Goals

1. Remove only genuinely unused documentation artifacts.
2. Fix broken navigation so every top-level README link resolves to a real active destination.
3. Make the active doc-system layers explicit and discoverable.
4. Preserve grandfathered referenced docs unless there is evidence they are truly obsolete and unreachable.
5. Reduce ambiguity between:
   - active source docs
   - generated discovery docs
   - legacy but still referenced design/implementation docs

## Non-Goals

This cleanup does not:

- rename every legacy `*-design.md` or `*-implementation.md` file to new naming
- retroactively rewrite the entire historical docs tree to the latest conventions
- remove root docs that are still referenced from feature YAMLs or README
- add full stage documentation for every pipeline stage in the same pass
- change runtime code or product behavior

## Desired Documentation-System Contract

The docs system should be easy to reason about:

### 1. Active Source Layers

These remain the authoritative source layers:

- feature YAMLs in `docs/features/*/*.yaml`
- stage YAMLs in `docs/stages/*.yaml`
- selected cross-cutting root docs
- current specs and plans in `docs/superpowers/*`

### 2. Generated Discovery Layers

Generated docs should index every active structured layer that the repo intends to support:

- features
- stages

If stage YAMLs remain part of the active contract, then generated stage discovery must exist.

### 3. Legacy Grandfathered Docs

Legacy naming is acceptable when the documents are still reachable and useful. These docs should be treated as:

- valid historical design records
- not unused merely because their naming predates the current conventions

## Proposed Cleanup

### A. Remove the One Verified Orphaned Spec

Delete:

- [2026-03-27-centralized-cv-generation-config-design.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/superpowers/specs/2026-03-27-centralized-cv-generation-config-design.md)

Rationale:

- no references were found anywhere in the docs tree
- it describes an older CV-config direction that has been superseded by later prompt/config centralization work

### B. Fix Broken README Navigation

Resolve the `docs/superpowers/decisions/` drift in one of two ways:

1. Preferred:
   - remove the README link until a real decisions layer exists
2. Acceptable alternative:
   - create a real `docs/superpowers/decisions/` layer and populate it intentionally

This spec recommends option 1 because there is no evidence that a real decisions layer is active today.

### C. Keep Root Docs, But Reclassify Them Clearly

Do not remove:

- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/FitCV-pipeline.md)
- [docs/fitcv-control-plane-setup.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/fitcv-control-plane-setup.md)

Instead:

- keep them explicitly positioned as cross-cutting operational/reference docs
- ensure README and feature refs describe them consistently

### D. Complete Minimal Stage Discovery

Because [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/codex-docs-cleanup/docs/stages/ranking.yaml) is active and referenced, the cleanest contract is to support the stage layer rather than demote it.

Add generated stage discovery docs:

- `docs/generated/stages_index.yaml`
- `docs/generated/stage_overview.md`

These should provide the same kind of discoverability for stages that the repo already provides for features.

### E. Clarify That Referenced Legacy Specs/Plans Are Intentionally Retained

The cleanup should not chase broad deletion of:

- old `*-design.md` specs
- old `*-implementation.md` plans

when those docs are still referenced.

Instead, the doc system should treat them as:

- grandfathered
- valid while referenced
- removable only after their references are retired or replaced

## Options Considered

### Option 1: Mass-prune old-looking docs

Reject.

Why:

- it would remove many still-referenced design records
- it would break feature YAML, stage YAML, spec, and plan traceability
- it would create more drift than it resolves

### Option 2: Keep everything and only fix the README

Reject.

Why:

- it would leave the truly orphaned spec in place
- it would leave the stage layer partially adopted and ambiguous

### Option 3: Targeted cleanup plus minimal stage-layer completion

Accept.

Why:

- removes only verified unused material
- fixes broken navigation
- makes the stage layer discoverable without requiring a full stage-doc rewrite
- preserves the historical documentation graph that is still in use

## Risks

### Over-removal Risk

If references are checked too narrowly, a doc may appear unused when it is only linked indirectly through another spec or plan.

Mitigation:

- require full-docs-tree reachability checks before removal

### Stage-Layer Drift Risk

If stage discovery is added but not maintained, generated docs may become stale.

Mitigation:

- treat stage discovery as generated output with the same refresh discipline as feature discovery

### Navigation Churn Risk

Removing or changing README navigation may surprise users who are used to older paths.

Mitigation:

- replace dead links with accurate active-layer navigation, not just silent deletion

## Acceptance Criteria

This cleanup is complete when:

1. Every top-level README docs link resolves to a real active location.
2. The truly orphaned CV-generation-config spec is removed.
3. No still-referenced legacy spec or plan is removed.
4. The stage-doc layer is either:
   - discoverable through generated docs, or
   - explicitly demoted from the active contract

This spec chooses discoverable support.

5. Generated discovery reflects the active docs layers after cleanup.

## Recommended Follow-Up Plan Scope

The implementation plan should cover:

1. full reference verification before deletion
2. orphaned-spec removal
3. README navigation cleanup
4. generated stage discovery creation
5. feature/stage/reference updates as needed
6. generated-doc refresh
