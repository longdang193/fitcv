---
layer: operating_system
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - agent-core/adapters/codex/root-AGENTS.template.md
  - agent-core/adapters/codex/docs-AGENTS.template.md
  - agent-core/adapters/codex/src-fitcv-AGENTS.template.md
  - AGENTS.md
  - docs/AGENTS.md
  - src/fitcv/AGENTS.md
  - repo_config/agent-adapter-mappings.json
  - scripts/sync_agent_adapters.ps1
  - scripts/verify_agent_adapters.ps1
  - repo_config/adoption-mode.yaml
related_features: []
related_stages: []
---

# Agent Instruction Layer Drift Prevention

## Summary

Update JOB-PROJECT's Codex instruction layers so agents get clearer scoped
guidance while keeping generated `AGENTS.md` surfaces aligned with their
templates and the latest local `project-OS-starter` baseline.

This is an operating-system instruction-surface phase. It should improve agent
behavior and reduce future drift, but it must not change product behavior,
pipeline runtime behavior, or feature metadata semantics.

Latest local starter evidence reviewed for this spec:

- `project-OS-starter` commit: `362289d Enforce optional root doc metadata when present`
- starter `docs-AGENTS.template.md`: no meaningful drift from JOB-PROJECT
- starter `root-AGENTS.template.md`: includes newer repo-wide guidance not yet
  reflected in JOB-PROJECT
- starter does not own a FitCV-specific `src/fitcv` template; that layer is
  intentionally repo-local

## Problem

JOB-PROJECT has three active generated Codex instruction surfaces:

- root `AGENTS.md`, generated from
  `agent-core/adapters/codex/root-AGENTS.template.md`
- `docs/AGENTS.md`, generated from
  `agent-core/adapters/codex/docs-AGENTS.template.md`
- `src/fitcv/AGENTS.md`, generated from
  `agent-core/adapters/codex/src-fitcv-AGENTS.template.md`

The layering is correct, but the content contract needs tightening:

- the root template lags newer starter guidance around canonical skills,
  config roots, generated `.codex/rules/`, and optional GitNexus usage
- `docs/AGENTS.md` appears aligned today, but the repo needs an explicit rule
  that docs-specific instruction drift is verified through the template, not by
  editing the generated file
- `src/fitcv/AGENTS.md` is useful because it scopes pipeline-runtime rules, but
  it is project-specific and should not be overwritten by starter examples
- the adapter mapping should continue to include only instruction files that
  have real scoped value; unused nested mappings such as the previously removed
  `src/fitcv_cp/AGENTS.md` must stay out unless a new scoped instruction layer
  is justified

Without this cleanup, future agents can either miss useful starter governance or
reintroduce stale nested AGENTS files because the intended instruction-layer
contract is implicit.

## Goals

- Make the root Codex instruction layer clearer and closer to starter without
  losing JOB-PROJECT-specific governance.
- Keep `docs/AGENTS.md` as the docs-only scoped layer and avoid unnecessary
  changes when the starter docs template already matches.
- Keep `src/fitcv/AGENTS.md` as a FitCV pipeline-runtime scoped layer because it
  maps to real code ownership.
- Document that deleted or absent nested AGENTS mappings should not be recreated
  unless they govern a real subtree with distinct operating rules.
- Ensure generated `AGENTS.md` files are synchronized from templates and
  verified by scripts.
- Record any intentional starter divergence in `repo_config/adoption-mode.yaml`
  only if the divergence is still real after the update.

## Non-Goals

- Do not hand-edit generated `AGENTS.md`, `docs/AGENTS.md`, or
  `src/fitcv/AGENTS.md` directly.
- Do not import starter example runtime/admin templates unless JOB-PROJECT has
  matching subtrees that need those exact scoped rules.
- Do not recreate `src/fitcv_cp/AGENTS.md`; that control-plane layer was removed
  because it had no active mapped use.
- Do not move product documentation rules into root AGENTS when they belong in
  `docs/AGENTS.md` or `docs/operating_system/`.
- Do not make GitNexus mandatory. It should remain an advisory private-only
  tool, subordinate to source code, tests, and docs.

## Target State

### Root Instruction Layer

`agent-core/adapters/codex/root-AGENTS.template.md` should retain
JOB-PROJECT-specific governance while adopting applicable starter improvements:

- `.agents/skills/` is the canonical Codex skill surface
- runtime/workflow config lives in `config/` for JOB-PROJECT, while repo/system
  config lives in `repo_config/`
- `.codex/rules/` and `codex/rules/` are generated rules output surfaces, not
  canonical homes for skills, memory, or governance
- private operating-system and GitNexus material must not leak into the public
  mirror
- GitNexus, when available, is advisory and source-first:
  - check freshness for high-trust impact/refactor use
  - use graph output to guide exploration, not to override source code/tests
  - continue source-first if GitNexus refresh fails

### Docs Instruction Layer

`agent-core/adapters/codex/docs-AGENTS.template.md` should remain the scoped
docs layer unless a new starter baseline introduces meaningful drift.

Expected behavior:

- applies only inside `docs/`
- points agents to `docs/operating_system/doc-system-lifecycle.md`
- keeps product docs separate from operating-system docs
- prevents hand-editing generated discovery

### FitCV Runtime Instruction Layer

`agent-core/adapters/codex/src-fitcv-AGENTS.template.md` should remain a
JOB-PROJECT-specific scoped layer because `src/fitcv/` owns pipeline runtime
behavior.

Expected behavior:

- applies only inside `src/fitcv/`
- reminds agents to preserve stage and artifact truth
- routes stage-aware changes back to `docs/stages/*.source.yaml` and relevant
  feature docs
- keeps repo operating rules out of pipeline code comments
- requires tests when changing stage flow, fit gating, artifacts, or validation

### Adapter Mapping

`repo_config/agent-adapter-mappings.json` should include only active generated
surfaces:

- root AGENTS
- docs AGENTS
- `src/fitcv` AGENTS
- current Codex rules outputs

It should not include deleted or speculative nested AGENTS files.

## Implementation Notes

The implementation phase should edit templates first, then regenerate:

1. Patch `agent-core/adapters/codex/root-AGENTS.template.md` with applicable
   starter guidance, translated to JOB-PROJECT's actual `config/` root.
2. Leave `agent-core/adapters/codex/docs-AGENTS.template.md` unchanged unless a
   fresh comparison shows new starter drift.
3. Review `agent-core/adapters/codex/src-fitcv-AGENTS.template.md` for small
   clarity improvements only; do not replace it from starter examples.
4. Confirm `repo_config/agent-adapter-mappings.json` has no stale nested mapping.
5. Run `scripts/sync_agent_adapters.ps1` so generated `AGENTS.md` files update
   from their templates.
6. Run `scripts/verify_agent_adapters.ps1` to prove no generated adapter drift
   remains.

## Acceptance Criteria

- `AGENTS.md`, `docs/AGENTS.md`, and `src/fitcv/AGENTS.md` are generated from
  their mapped templates.
- root AGENTS guidance incorporates applicable latest starter governance without
  claiming starter-only paths that are false for JOB-PROJECT.
- `docs/AGENTS.md` remains docs-scoped and is not edited directly.
- `src/fitcv/AGENTS.md` remains present and scoped to real pipeline runtime
  ownership.
- no mapping exists for `src/fitcv_cp/AGENTS.md` or any other unused nested
  instruction layer.
- any remaining starter divergence is intentional and, if necessary, reflected
  in `repo_config/adoption-mode.yaml`.
- the following pass:
  - `.\scripts\sync_agent_adapters.ps1`
  - `.\scripts\verify_agent_adapters.ps1`
  - `python scripts\validate_adoption_shape.py`
  - `python scripts\validate_repo_contracts.py --fast`
  - `git diff --check`

## Risks

- Copying starter root guidance too literally could introduce false paths such
  as `configs/` when JOB-PROJECT currently uses `config/`.
- Removing the `src/fitcv` scoped layer would make pipeline-runtime expectations
  less visible to future agents.
- Recreating speculative nested AGENTS files would add noise and increase the
  chance of future generated-surface drift.
- Making GitNexus sound mandatory could block safe source-first work when the
  graph is stale or unavailable.

## Suggested Next Step

Turn this spec into a focused implementation plan with two batches:

- Batch A: root template starter-guidance merge, adapter sync, adapter verify
- Batch B: scoped-layer audit, adoption-mode divergence cleanup if needed, full
  validator pass
