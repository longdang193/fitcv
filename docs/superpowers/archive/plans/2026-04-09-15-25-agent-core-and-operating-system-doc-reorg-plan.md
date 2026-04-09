---
feature_type: modify
feature_name: none
status: building
summary: "Phase the repo reorganization into an operating-system doc layer, Codex-native instruction surfaces, an agent-core source tree, and adapter sync/validation without breaking current skill discovery."
---

# Agent-Core And Operating-System Doc Reorg Plan

## Objective

Implement the long-term repo reorganization so:

- repo governance and workflows live in `docs/operating_system/`
- Codex-native instruction surfaces are explicit (`AGENTS.md`, nested `AGENTS.md`, `codex/rules/`)
- shared agent-facing material lives in `agent-core/`
- skill workflows remain focused and reusable
- generated or synced adapter files stay trustworthy

## Scope

This plan covers the private repo only.  
It does not change product runtime behavior or public-repo publication content.

## Phase Strategy

Implement in five phases so the repo remains usable throughout the migration.

## Task 1: Establish `docs/operating_system/`

Create the new human-readable governance layer:

```text
docs/operating_system/
  repo-governance.md
  doc-system-lifecycle.md
  planning-dispatch.md
  publication-workflow.md
  stage-lifecycle.md
  tooling/
```

Actions:

- create the folder structure
- move or rewrite current operating docs from `.cursor/rules/operating-system/`
- keep the docs human-readable and vendor-neutral
- update any internal references that currently point to `.cursor/rules/operating-system/*`

Output:

- a stable private-only governance/workflow doc layer

## Task 2: Define the instruction-layering contract

Design the initial `AGENTS.md` structure before generating or syncing anything.

Target files:

- `AGENTS.md`
- `src/fitcv/AGENTS.md`
- `src/fitcv_cp/AGENTS.md`
- `docs/AGENTS.md`

Actions:

- define what belongs in root `AGENTS.md`
- define what truly needs nested overrides
- keep each file short and scope-specific
- avoid duplicating skills or long workflow manuals inside `AGENTS.md`

Output:

- a written responsibility split for root vs nested `AGENTS.md`

## Task 3: Introduce initial Codex rules

Create the first explicit `codex/rules/` layer for execution policy.

Target:

```text
codex/rules/
  command-execution.rules
  publication-boundary.rules
```

Actions:

- identify the minimum real policy worth expressing as Codex rules
- keep rules focused on execution policy, not workflow prose
- align rule intent with the existing private/public publication boundary
- avoid overbuilding policy coverage on the first pass

Output:

- explicit Codex execution policy files

## Task 4: Introduce `agent-core/` source folders

Create the long-term shared agent-facing source tree:

```text
agent-core/
  principles/
  policies/
  adapters/
```

Initial files:

- `principles/repo-guidelines.md`
- `principles/docs-policy.md`
- `principles/collaboration-model.md`
- `policies/command-execution.yaml`
- `policies/publication-boundary.yaml`
- `policies/instruction-layering.yaml`

Actions:

- create the directories
- seed them with concise initial content derived from the new operating-system docs
- keep them smaller than the full human governance docs

Output:

- a clean shared source for agent-facing principles and policy intent

## Task 5: Decide the phase-1 canonical skill source

Choose how to handle skills during the transition.

Recommended decision:

- keep `.agents/skills/` canonical in phase 1
- do not move canonical ownership to `agent-core/skills/` yet

Reason:

- this avoids breaking current Codex discovery during the larger reorg
- it lets the repo prove the adapter/sync model first

Actions:

- document this transitional rule
- postpone skill canon migration until the sync layer is stable

Output:

- a clear, low-risk migration boundary for skills

## Task 6: Add adapter outputs for Codex first

Implement only the adapter outputs that are immediately useful.

Phase-1 adapters:

- root `AGENTS.md`
- nested `AGENTS.md`
- `codex/rules/*.rules`

Deferred:

- `CLAUDE.md`
- `GEMINI.md`
- other agent adapters

Actions:

- create or sync Codex-facing files from the shared source where practical
- add generated-file headers where files are generated
- keep manual ownership explicit where generation is not ready yet

Output:

- a working Codex-native repo structure without speculative adapter churn

## Task 7: Add sync and validation tooling

Create a small internal script layer that can:

- sync shared source into adapter outputs
- verify committed adapter outputs are current
- fail when generated adapter files drift

Recommended targets:

- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`

Actions:

- define which files are generated vs synchronized vs hand-authored
- implement minimal sync behavior first
- add a verification step that can be used before commits or releases

Output:

- a trustworthy adapter maintenance workflow

## Task 8: Update internal docs and publication rules

Once the new structure exists:

- update private docs to reference `docs/operating_system/`
- update publication-boundary docs if any new private-only paths must be excluded
- confirm the public repo export does not include:
  - `agent-core/`
  - `codex/rules/`
  - new operating-system-only docs unless intentionally allowed

Output:

- consistent private/public boundary after the reorg

## Task 9: Add future-agent support only after Codex stabilizes

Do not implement additional adapters until:

- root and nested `AGENTS.md` are working well
- Codex rule files are stable
- sync/validation has proven reliable

After that, evaluate whether:

- `CLAUDE.md`
- `GEMINI.md`
- other adapters

should be added from the same shared sources.

Output:

- deliberate multi-agent expansion instead of speculative adapter churn

## Verification

Before closing the work:

1. confirm the repo has a clear human-readable governance layer under `docs/operating_system/`
2. confirm root and nested `AGENTS.md` exist where intended
3. confirm `codex/rules/` contains only execution policy, not workflow manuals
4. confirm `.agents/skills/` still works for current Codex usage
5. run sync and verification scripts successfully
6. confirm public publication excludes the new private-only structures

## Completion Criteria

The reorganization is complete when:

- humans can find repo rules in `docs/operating_system/`
- Codex can read explicit `AGENTS.md` layers and rules
- the repo has a shared `agent-core/` source for future reuse
- skills remain focused playbooks
- adapter outputs are reproducible and validated
- the public/private boundary still holds cleanly
