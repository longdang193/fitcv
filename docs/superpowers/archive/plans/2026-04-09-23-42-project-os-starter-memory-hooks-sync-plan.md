---
feature_type: add
feature_name: none
status: draft
summary: "Update project-OS-starter to inherit the generic Memory and Hook harness layers from FitCV."
invariants:
  - "project-OS-starter must remain generic and private-repo-operational rather than FitCV-specific"
  - "canonical starter sources must be updated instead of treating generated outputs as source"
  - "starter memory content must preserve the structure and behavior model while removing FitCV-specific incidents"
---

# Project OS Starter Memory And Hooks Sync Plan

## Spec Anchor

- Spec: [2026-04-09-23-39-project-os-starter-memory-hooks-sync-spec.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/specs/2026-04-09-23-39-project-os-starter-memory-hooks-sync-spec.md)

## Scope

Update [project-OS-starter](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter) so it inherits the generic Memory and Hook harness layers now proven in FitCV, while keeping FitCV-specific runtime behavior and failure content out of the starter baseline.

## Affected Docs

- feature_yaml: `none`
- feature_history: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - [repo-governance.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/operating_system/repo-governance.md)
  - [publication-workflow.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/operating_system/publication-workflow.md)
  - [README.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/README.md)
- readme: [README.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/README.md)
- generated:
  - [AGENTS.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/AGENTS.md)
  - [docs/AGENTS.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/AGENTS.md)
  - `codex/rules/*.rules`

## Workstreams

### 1. Add Generic Agent Memory To The Starter

- Create `docs/operating_system/agent_memory/` in `project-OS-starter`.
- Add:
  - `README.md`
  - `invariants.md`
  - `patterns.md`
  - `failure-ledger.md`
  - `open-questions.md`
- Preserve the FitCV structure and usage model.
- Rewrite starter content so it is generic:
  - no `FitCV` or `JOB-PROJECT`
  - no FitCV-specific incidents in the default failure ledger
  - no assumptions about one exact runtime layout beyond the starter’s own generic operating-system structure

### 2. Update Starter Governance To Recognize Memory

- Update [repo-governance.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/operating_system/repo-governance.md) so `agent_memory/` is part of the documented operating-system model.
- Update [publication-workflow.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/docs/operating_system/publication-workflow.md) if needed so private/public guidance stays aligned with the new memory and hook layers.
- Keep the docs short and operational.

### 3. Update Root Adapter Template And Regenerated Outputs

- Update [root-AGENTS.template.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/agent-core/adapters/codex/root-AGENTS.template.md) to:
  - mention the memory layer path
  - tell agents to consult relevant memory before planning when appropriate
  - tell agents to consult the failure ledger during debugging or retries
  - tell agents to update memory when a reusable lesson emerges
- Regenerate starter adapter outputs after the template update.

### 4. Add A Generic Hook Workflow

- Add `.github/workflows/repo-hooks.yml` to `project-OS-starter`.
- Preserve the three-job shape:
  - `Adapter Integrity`
  - `Baseline Tests`
  - `Publication Boundary`
- Keep the starter workflow generic enough to be customized during bootstrap.
- Document the baseline-test assumption clearly in the starter README.

### 5. Sync Reusable Script Hardening

- Port the repo-relative generated-header behavior from FitCV into:
  - [sync_agent_adapters.ps1](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/scripts/sync_agent_adapters.ps1)
  - [verify_agent_adapters.ps1](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/scripts/verify_agent_adapters.ps1)
- Port the dry-run public-remote guard into:
  - [publish_public_repo.ps1](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter/scripts/publish_public_repo.ps1)
- Confirm starter config files still drive mappings and publication behavior correctly after the script updates.

### 6. Update Starter README

- Add a short section explaining the Memory layer.
- Add a short section explaining the Hook workflow.
- Clarify what a new project should customize first:
  - adapter templates
  - adapter mappings
  - publication config
  - baseline test command if the starter workflow is not already correct for that project

## Execution Steps

1. Create a new working branch in [project-OS-starter](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/project-OS-starter).
2. Add the generic `agent_memory/` folder and files.
3. Update starter governance docs.
4. Update the root adapter template.
5. Add the generic hook workflow.
6. Port the reusable script fixes.
7. Update the starter README.
8. Run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

9. Review generated outputs for drift and ensure no FitCV-specific wording remains.
10. Commit and push the starter branch.

## Validation

### Content Validation

- Search for starter-breaking leftovers:
  - `FitCV`
  - `JOB-PROJECT`
  - `src/fitcv`
  - FitCV-only failure examples
- Confirm the starter failure ledger reads like a template/default memory surface, not a copied incident log from one project.

### Workflow Validation

- Confirm the starter workflow file is syntactically valid and present at `.github/workflows/repo-hooks.yml`.
- Confirm the adapter-integrity flow matches the starter’s config-driven generation model.
- Confirm the publication-boundary dry check succeeds without requiring a configured public remote unless `-Push` is used.

### Generation Validation

- Run starter sync and verify locally.
- Confirm generated outputs are stable after one regeneration pass.
- Confirm no generated-file drift remains after verification.

## Risks And Mitigations

### Risk: The starter copies FitCV incidents too literally

- Mitigation: replace repo-specific ledger entries with generic starter examples or a starter template entry.

### Risk: The starter hook workflow is too narrow

- Mitigation: keep the working default, but document the expected project-specific bootstrap edits in the README.

### Risk: The starter docs become too heavy

- Mitigation: keep the memory layer compact and operational; put deeper rationale in specs and plans, not in starter defaults.

## Done Criteria

- `project-OS-starter` contains a generic `docs/operating_system/agent_memory/` layer.
- Starter governance docs and root template recognize and activate Memory.
- `project-OS-starter` contains a generic `repo-hooks.yml` workflow.
- Starter scripts include the reusable FitCV hardening for adapter headers and publication dry runs.
- Starter README explains Memory and Hooks as part of the starter baseline.
- Starter sync and verify pass.
- No leftover FitCV-specific wording remains unless explicitly marked as an example.
