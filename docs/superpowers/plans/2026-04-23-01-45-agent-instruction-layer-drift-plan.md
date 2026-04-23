---
layer: operating_system
artifact_type: plan
status: completed
completed_at: 2026-04-23T01:45:00+02:00
change_id: 2026-04-23-agent-instruction-layer-drift
verification:
  - See plan body closeout verification notes.
outcome:
  summary: Completed the agent instruction layer drift work.
parent_workstream: none
targets:
  - agent-core/adapters/codex/root-AGENTS.template.md
  - agent-core/adapters/codex/docs-AGENTS.template.md
  - agent-core/adapters/codex/src-fitcv-AGENTS.template.md
  - AGENTS.md
  - docs/AGENTS.md
  - src/fitcv/AGENTS.md
  - repo_config/agent-adapter-mappings.json
  - repo_config/adoption-mode.yaml
related_features: []
related_stages: []
---

# Agent Instruction Layer Drift Implementation Plan

**Feature Source:** `none`
**Feature Contract:** `none`
**Spec:** `docs/superpowers/specs/2026-04-23-01-35-agent-instruction-layer-drift-spec.md`
**Type:** modify
**Plan Layer:** operating_system
**Plan Status:** completed

> **For agentic workers:** Use `executing-plans` to implement task-by-task.

**Goal:** Update generated Codex instruction layers so JOB-PROJECT agents get clearer scoped rules while reducing future drift from `project-OS-starter`.

**Architecture:** The template files under `agent-core/adapters/codex/` are the source of truth for generated instruction surfaces. `scripts/sync_agent_adapters.ps1` renders those templates into `AGENTS.md`, `docs/AGENTS.md`, and `src/fitcv/AGENTS.md`, while `scripts/verify_agent_adapters.ps1` proves generated outputs are in sync.

**Key Invariants:**
- Generated `AGENTS.md` files are never hand-edited; templates own content.
- Starter guidance must be translated to JOB-PROJECT paths, especially `config/` instead of starter-only `configs/`.
- `src/fitcv/AGENTS.md` remains because it scopes real pipeline-runtime rules.
- No unused nested AGENTS mapping such as `src/fitcv_cp/AGENTS.md` is recreated.

**Rollout / Revert:**
- rollback_trigger: adapter verification fails or generated instructions claim false repo paths
- rollback_method: revert the template/adoption-mode edits and rerun `.\scripts\sync_agent_adapters.ps1`

---

## Triage

Layer: operating_system
Feature type: MODIFY
Summary: Refresh Codex instruction templates and generated surfaces to reduce starter drift.
Reasoning: This changes repo-control guidance, not product behavior or managed feature state.
Invariants:
- generated AGENTS surfaces derive from templates
- docs and runtime scoped layers stay narrowly scoped
- GitNexus remains advisory, not mandatory
Dependencies:
- latest local `project-OS-starter` baseline: `362289d Enforce optional root doc metadata when present`
Affected stages:
- none
Affected features:
- none
Primary lens: cross-cutting
Affected docs:
- feature_source: none
- feature_yaml: none
- feature_lineage: none
- feature_history: none
- stage_source: none
- stage_contract: none
- feature_docs: none
- cross_cutting_docs: none
- operating_system_docs:
  - `docs/superpowers/specs/2026-04-23-01-35-agent-instruction-layer-drift-spec.md`
  - `docs/superpowers/plans/2026-04-23-01-45-agent-instruction-layer-drift-plan.md`
- readme: none
- generated:
  - `AGENTS.md`
  - `docs/AGENTS.md`
  - `src/fitcv/AGENTS.md`
Generated refresh required: yes
Capability IDs:
- none
Invariant IDs:
- none
Spec needed: yes
Plan needed: yes
Risk level: low

## Doc Update Matrix

- Feature source: none
- Feature contract: none
- Feature lineage: none
- Stage source: none
- Stage contracts: none
- Feature history: none
- Feature-specific docs: none
- Cross-cutting docs: none
- Operating-system docs: `docs/superpowers/specs/2026-04-23-01-35-agent-instruction-layer-drift-spec.md`, `docs/superpowers/plans/2026-04-23-01-45-agent-instruction-layer-drift-plan.md`
- README: none
- Generated discovery: none
- Generated instruction surfaces: `AGENTS.md`, `docs/AGENTS.md`, `src/fitcv/AGENTS.md`

## Batch A: Root Template Starter-Guidance Merge

### Task 1: Patch Root Instruction Template

**Files:**
- Modify: `agent-core/adapters/codex/root-AGENTS.template.md`
- Generated: `AGENTS.md`

- [x] Step 1: Merge applicable latest starter root guidance into the JOB-PROJECT root template.
- [x] Step 2: Translate starter `configs/` wording to JOB-PROJECT's actual `config/` root.
- [x] Step 3: Keep public/private governance and agent-memory rules intact.
- [x] Step 4: Add GitNexus as optional, private-only, advisory guidance.
- [x] Step 5: Run `.\scripts\sync_agent_adapters.ps1`.
- [x] Step 6: Run `.\scripts\verify_agent_adapters.ps1`.

## Batch B: Scoped Layer Audit And Full Validation

### Task 2: Audit Scoped Layers And Mapping

**Files:**
- Review: `agent-core/adapters/codex/docs-AGENTS.template.md`
- Review: `agent-core/adapters/codex/src-fitcv-AGENTS.template.md`
- Review: `repo_config/agent-adapter-mappings.json`
- Modify if needed: `repo_config/adoption-mode.yaml`
- Generated: `docs/AGENTS.md`, `src/fitcv/AGENTS.md`

- [x] Step 1: Confirm docs template still matches starter or document why no change is needed.
- [x] Step 2: Confirm `src-fitcv` template remains repo-local and truthful.
- [x] Step 3: Confirm adapter mappings include no stale `src/fitcv_cp/AGENTS.md` entry.
- [x] Step 4: Update `repo_config/adoption-mode.yaml` baseline/divergence wording if this phase changes the truth.
- [x] Step 5: Run `.\scripts\sync_agent_adapters.ps1`.
- [x] Step 6: Run `.\scripts\verify_agent_adapters.ps1`.
- [x] Step 7: Run `python scripts\validate_adoption_shape.py`.
- [x] Step 8: Run `python scripts\validate_repo_contracts.py --fast`.
- [x] Step 9: Run `git diff --check`.

## Completion Checklist

- intent docs updated? no
- operating-system docs updated? yes, spec and plan
- stage sources updated? no
- stage contracts updated? no
- feature sources updated? no
- contract updated? no
- feature lineage updated? no
- feature history updated? no
- other feature-specific docs updated? no
- cross-cutting docs updated? no
- agent memory updated or explicitly not needed? not needed; this is a planned drift-prevention cleanup, not a new reusable failure lesson
- README updated? no
- generated docs refreshed? no
- generated instruction surfaces refreshed? yes, via `.\scripts\sync_agent_adapters.ps1`
