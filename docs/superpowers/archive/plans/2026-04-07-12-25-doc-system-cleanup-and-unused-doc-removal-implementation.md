# Doc-System Cleanup And Unused-Doc Removal Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean the documentation system by removing the one verified orphaned spec, fixing broken README navigation, and making the active stage-doc layer discoverable without deleting grandfathered referenced docs.

**Architecture:** Treat the cleanup as a documentation-contract alignment pass rather than a mass pruning pass. First verify reachability, then remove only the one truly orphaned spec, repair broken navigation, and add generated discovery for the stage-doc layer so `docs/stages/*.yaml` is an explicit supported layer alongside the existing feature discovery outputs.

**Tech Stack:** Markdown, YAML, generated docs

**Affected feature contracts:**

- `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
- `docs/features/cv_system/cv_system.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/pipeline_performance/pipeline_performance.yaml`
- `docs/features/settings_system/settings_system.yaml`
- `docs/features/trigger_run_management/trigger_run_management.yaml`

**Supporting docs to update during implementation:**

- `README.md`
- `docs/FitCV-pipeline.md`
- `docs/fitcv-control-plane-setup.md`
- `docs/stages/ranking.yaml`
- `docs/generated/features_index.yaml`
- `docs/generated/feature_overview.md`
- `docs/generated/feature_capabilities_index.yaml`
- `docs/generated/feature_dependency_graph.yaml`
- `docs/generated/features_by_status.yaml`
- `docs/generated/stages_index.yaml`
- `docs/generated/stage_overview.md`

---

## Task 1: Re-Verify Reachability Before Any Removal

**Files:**

- Read-only audit across:
  - `README.md`
  - `docs/**/*.md`
  - `docs/**/*.yaml`

- [x] **Step 1.1: Re-run full-docs-tree reference checks**
  - Confirm the one verified orphaned spec is still unreachable from the current docs tree
  - Confirm no additional specs or plans have become unreachable since the spec was drafted

- [x] **Step 1.2: Reconfirm root-doc usage**
  - Verify `docs/FitCV-pipeline.md` is still referenced
  - Verify `docs/fitcv-control-plane-setup.md` is still referenced

- [x] **Step 1.3: Reconfirm stage-doc usage**
  - Verify `docs/stages/ranking.yaml` is still referenced in current docs

- [x] **Step 1.4: Capture the final removal set**
  - Limit deletion scope to documents that are still provably unreachable after this recheck

---

## Task 2: Remove the One Verified Orphaned Spec

**Files:**

- Delete: `docs/superpowers/specs/2026-03-27-centralized-cv-generation-config-design.md`

- [x] **Step 2.1: Delete the orphaned spec**
  - Remove only `2026-03-27-centralized-cv-generation-config-design.md`

- [x] **Step 2.2: Verify no doc references were missed**
  - Re-run a full-docs-tree search for the deleted path after removal

- [x] **Step 2.3: Confirm no neighboring docs were changed unnecessarily**
  - Do not rename or move legacy specs/plans in this task

---

## Task 3: Fix Broken Top-Level Navigation

**Files:**

- Modify: `README.md`

- [x] **Step 3.1: Remove or replace the dead `docs/superpowers/decisions/` reference**
  - Preferred: remove the dead link entirely until a real decisions layer exists

- [x] **Step 3.2: Keep README docs navigation honest**
  - Ensure every top-level docs link resolves to a real active location

- [x] **Step 3.3: Recheck README navigation after the edit**
  - Validate that the remaining linked docs/directories exist in the worktree

---

## Task 4: Preserve And Clarify Active Cross-Cutting Docs

**Files:**

- Modify only if needed:
  - `README.md`
  - `docs/FitCV-pipeline.md`
  - `docs/fitcv-control-plane-setup.md`

- [x] **Step 4.1: Keep the two root docs in the active contract**
  - Do not delete them
  - Do not mark them unused

- [x] **Step 4.2: Align their navigation labels if needed**
  - Make sure README wording matches their actual role as cross-cutting operational/reference docs

- [x] **Step 4.3: Avoid broad content rewrites**
  - This task is only for contract clarity, not for rewriting the docs themselves

---

## Task 5: Complete Minimal Stage Discovery

**Files:**

- Modify as needed:
  - `docs/stages/ranking.yaml`
- Add:
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

- [x] **Step 5.1: Define the generated stage-discovery outputs**
  - Add a stage index with stage id, title/name, status if represented, and ref visibility
  - Add a stage overview markdown doc analogous to the feature overview

- [x] **Step 5.2: Keep the stage-discovery scope minimal**
  - Support the current stage layer as it exists today
  - Do not expand this task into full adoption of all pipeline stages

- [x] **Step 5.3: Ensure `ranking.yaml` is discoverable through generated outputs**
  - The only active stage doc must appear in both new generated stage outputs

---

## Task 6: Align Feature Contracts With The Cleaned Docs Graph

**Files:**

- Modify as needed:
  - `docs/features/admin_control_plane_core/admin_control_plane_core.yaml`
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/pipeline_performance/pipeline_performance.yaml`
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/trigger_run_management/trigger_run_management.yaml`

- [x] **Step 6.1: Update any refs affected by the orphaned-spec removal**
  - Only touch feature YAML refs if they point to removed or replaced docs

- [x] **Step 6.2: Keep referenced legacy docs intact**
  - Do not remove grandfathered refs that still point to reachable design/implementation docs

- [x] **Step 6.3: Add stage-discovery references only where appropriate**
  - If feature YAMLs or README should point at new generated stage outputs, add those references deliberately rather than broadly

---

## Task 7: Refresh Generated Discovery

**Files:**

- Modify/regenerate:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_overview.md`
  - `docs/generated/feature_capabilities_index.yaml`
  - `docs/generated/feature_dependency_graph.yaml`
  - `docs/generated/features_by_status.yaml`
  - `docs/generated/stages_index.yaml`
  - `docs/generated/stage_overview.md`

- [x] **Step 7.1: Refresh feature-generated docs after source-layer changes**
  - Ensure removed or updated refs do not leave stale generated content

- [x] **Step 7.2: Generate the new stage-discovery outputs**
  - Produce `stages_index.yaml`
  - Produce `stage_overview.md`

- [x] **Step 7.3: Reconfirm generated/source alignment**
  - Generated outputs must reflect actual source docs, not inferred future structure

---

## Task 8: Add Focused Regression Coverage For The Docs Graph

**Files:**

- Modify or add the existing docs-validation/generation tooling tests as appropriate

- [x] **Step 8.1: Add or update validation for dead README links**
  - Catch missing top-level documentation targets

- [x] **Step 8.2: Add or update validation for generated stage discovery**
  - Ensure stage-generated docs are present when stage YAMLs exist

- [x] **Step 8.3: Add or update validation for orphaned-doc detection if tooling exists**
  - Prefer lightweight guardrails that prevent obvious future unreachable specs

---

## Task 9: Final Verification And Plan Close-Out

**Files:**

- Modify: `docs/superpowers/plans/2026-04-07-12-25-doc-system-cleanup-and-unused-doc-removal-implementation.md`

- [x] **Step 9.1: Run focused docs verification**
  - Validate Markdown/YAML formatting as appropriate
  - Validate generated-doc refresh results
  - Validate link/reference integrity for touched docs

- [x] **Step 9.2: Mark the plan complete**
  - Update this file to reflect completed task status once implementation is finished

- [x] **Step 9.3: Record any intentional deferrals**
  - Note any future stage-doc expansion work that was explicitly kept out of scope

---

## Verification Checklist

- [x] The orphaned CV-generation-config spec is removed
- [x] No still-referenced legacy spec or plan is removed
- [x] `README.md` no longer links to a missing `docs/superpowers/decisions/` directory
- [x] `docs/FitCV-pipeline.md` and `docs/fitcv-control-plane-setup.md` remain reachable and intentionally retained
- [x] `docs/generated/stages_index.yaml` exists and includes `ranking`
- [x] `docs/generated/stage_overview.md` exists and reflects the active stage layer
- [x] Generated feature docs remain in sync after the cleanup

---

## Risks And Notes

### Reachability Misclassification Risk

A doc can look orphaned if only direct feature-YAML references are checked. The implementation must always recheck reachability across the full `docs/` tree before deleting anything.

### Partial Stage-Adoption Risk

This plan intentionally supports the current stage-doc layer at a minimal level. It does not commit the repo to documenting every pipeline stage immediately.

### Scope Guard

Do not turn this plan into a mass migration of legacy naming. The objective is contract cleanup and discoverability, not renaming the historical docs archive.

### Intentional Deferrals

- Full stage-doc adoption beyond `ranking` remains out of scope.
- Legacy referenced `*-design.md` and `*-implementation.md` files remain grandfathered rather than renamed in this pass.
