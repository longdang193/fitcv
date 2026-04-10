---
feature_type: add
feature_name: none
status: draft
summary: "Sync the reusable agent-memory and hook layers from FitCV into project-OS-starter without carrying FitCV-specific runtime or failure content."
invariants:
  - "project-OS-starter must keep only reusable operating-system assets, not FitCV-specific product/runtime behavior"
  - "agent memory in the starter must preserve the structure and usage model, while example content stays generic"
  - "hook updates in the starter must enforce generic repo guardrails without assuming FitCV-specific test layout or publication details"
---

# Project OS Starter Memory And Hook Sync Spec

## Triage

Feature type: `ADD`  
Summary: Sync the reusable Memory and Hook harness layers from `JOB-PROJECT` into `project-OS-starter` as generic operating-system infrastructure.  
Reasoning: This is new cross-project starter capability, not a change to a managed product feature contract.  
Invariants:
- `project-OS-starter` remains private and repo-operational, not product-specific.
- The starter must preserve canonical source layers, not elevate generated outputs to source of truth.
- Memory should be persisted as a reusable operating-system layer, but FitCV incident details must not become starter defaults.
- Hook automation should be starter-generic and configurable where project-specific assumptions exist.
Dependencies:
- `docs/operating_system/agent_memory/`
- `docs/operating_system/repo-governance.md`
- `agent-core/adapters/codex/root-AGENTS.template.md`
- `.github/workflows/repo-hooks.yml`
- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`
- `scripts/publish_public_repo.ps1`
- `C:\Users\HOANG PHI LONG DANG\repos\project-OS-starter`
Affected stages:
- `none`
Affected features:
- `none`
Primary lens: `feature`
Affected docs:
  feature_yaml: `none`
  feature_history: `none`
  feature_docs: `none`
  cross_cutting_docs:
    - `docs/operating_system/repo-governance.md`
    - `docs/operating_system/publication-workflow.md`
    - `README.md`
  readme: `README.md`
  generated: `none`
Generated refresh required: `yes`
Spec needed: `yes`
Plan needed: `yes`

## Problem

`JOB-PROJECT` now has two harness improvements that are valuable across projects:

- a compact `docs/operating_system/agent_memory/` layer that stores reusable operational memory for agents
- a CI-first hook workflow that automatically enforces adapter integrity, baseline tests, and publication-boundary checks

`project-OS-starter` currently preserves the broader operating-system, skills, adapter-source, and publication setup, but it does not yet include these newer Memory and Hook layers. If the starter is not updated, future projects will inherit an older operating-system baseline and immediately drift from the more reliable harness now proven in FitCV.

## Goals

- Persist the reusable `agent_memory` layer structure into `project-OS-starter`.
- Persist the reusable hook workflow pattern into `project-OS-starter`.
- Update starter governance and adapter templates so new projects know how to use Memory and Hooks from day one.
- Keep the starter generic enough that a new repo can adopt it without inheriting FitCV-specific runtime assumptions.

## Non-Goals

- Do not move FitCV runtime code, tests, or product contracts into the starter.
- Do not copy FitCV-specific failure-ledger entries verbatim as starter defaults.
- Do not hardcode the starter hook workflow to `python -m pytest` if the starter is meant to support wider project shapes later without adjustment.
- Do not treat generated `AGENTS.md` or `codex/rules/*.rules` as the source to copy.

## Current Source Of Truth

The sync should draw from the canonical FitCV layers, not their downstream artifacts:

- `docs/operating_system/agent_memory/`
- `docs/operating_system/repo-governance.md`
- `agent-core/adapters/codex/root-AGENTS.template.md`
- `.github/workflows/repo-hooks.yml`
- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`
- `scripts/publish_public_repo.ps1`

For `project-OS-starter`, the target canonical layers remain:

- `docs/operating_system/`
- `agent-core/adapters/codex/`
- `scripts/`
- `config/`
- `README.md`

## Proposed Design

### 1. Add Agent Memory As A First-Class Starter Layer

Add `docs/operating_system/agent_memory/` to `project-OS-starter` with the same structural shape used in FitCV:

- `README.md`
- `invariants.md`
- `patterns.md`
- `failure-ledger.md`
- `open-questions.md`

The starter should preserve:

- the purpose of the layer
- when agents are expected to consult it
- the rule that memory should stay compact, operational, and guardrail-oriented

The starter should generalize:

- any repo name references
- any FitCV-specific incident details
- any references to a specific test suite, runtime package, or app layout

### 2. Update Starter Governance To Recognize Memory

Update the starter’s operating-system docs so Memory is treated as part of the durable repo-operating-system model:

- mention `docs/operating_system/agent_memory/` in starter governance
- explain that Memory complements, but does not replace, specs, plans, governance docs, and generated outputs
- clarify that repeated important failures should eventually become rules, tests, hooks, or explicit follow-up work

### 3. Update Root Agent Instructions To Activate Memory

Sync the generic memory activation contract from FitCV into the starter’s root adapter template so future repos inherit the same operating behavior:

- consult relevant memory before planning when work touches reusable repo workflows or known invariants
- consult the failure ledger during debugging, retries, or after important mistakes
- update the memory layer when a significant reusable lesson emerges

This must stay generic and must not mention FitCV-specific file paths beyond the generic starter path `docs/operating_system/agent_memory/`.

### 4. Add A Generic Hook Workflow To The Starter

Add a starter version of `.github/workflows/repo-hooks.yml` that preserves the FitCV hook architecture:

- `Adapter Integrity`
- `Baseline Tests`
- `Publication Boundary`

The workflow should preserve the proven enforcement pattern:

- sync adapter outputs
- verify adapter outputs
- fail on untracked generated outputs
- fail on generated drift
- run the repo’s baseline test command
- run the publication-boundary dry check

The workflow must be generalized so a starter consumer can adapt it cleanly. The spec allows one of two acceptable starter defaults:

- a small generic default that assumes Python projects and documents how to change the test command
- or a configurable/default-disabled baseline-test step if the starter is intended to support non-Python repos without immediate friction

Recommended first version: keep the Python-oriented default because the current starter already ships Python-oriented scripts and structure, but document clearly that new repos should update the test command as part of bootstrap.

### 5. Carry Forward The Generic Script Fixes

The starter should inherit the reusable script hardening that came out of the FitCV hook rollout:

- repo-relative source-path handling in `sync_agent_adapters.ps1`
- matching verification logic in `verify_agent_adapters.ps1`
- publication dry-run behavior in `publish_public_repo.ps1` that does not require resolving a public remote unless `-Push` is requested

These are harness-level fixes and should be part of the starter baseline.

### 6. Update Starter README And Bootstrap Guidance

The starter `README.md` should gain a short section that explains:

- what the Memory layer is for
- that Hooks are part of the default operating-system enforcement model
- which starter files a new project should customize first
- that generated agent outputs must still be regenerated after source-layer changes

## Generalization Rules

### Safe To Sync Nearly As-Is

- `agent_memory` folder structure
- generic memory usage guidance
- generic governance references to the memory layer
- root instruction reminders to consult memory
- repo-relative adapter script fixes
- publication dry-run remote guard
- the overall hook workflow shape

### Must Be Generalized Before Sync

- failure-ledger entries
- any references to `FitCV`, `JOB-PROJECT`, or repo-specific runtime modules
- any workflow text that assumes a specific project name
- any baseline-test wording that implies all projects must use the exact FitCV test stack

### Must Stay In FitCV Only

- runtime/test bug fixes from the FitCV hook rollout
- FitCV-specific pipeline or control-plane failure examples
- FitCV-specific test files and package assumptions beyond what the starter deliberately standardizes

## Acceptance Criteria

- `project-OS-starter` contains `docs/operating_system/agent_memory/` with generic reusable content.
- Starter governance and root adapter templates mention and activate the memory layer.
- `project-OS-starter` contains a working generic `repo-hooks.yml` workflow.
- Starter scripts include the repo-relative adapter-path fix and the publication dry-run remote guard.
- Starter `README.md` explains Memory and Hooks as part of the operating-system baseline.
- No synced starter file contains FitCV-specific runtime/test references unless explicitly marked as an example.

## Risks

### Overfitting The Starter To FitCV

If the workflow or memory content is copied too literally, the starter will feel coupled to one project and future repos will either ignore it or immediately fork it.

Mitigation:

- generalize examples
- keep the structure and behavior model, not the incident specifics

### Making The Hook Workflow Too Abstract

If the workflow becomes too configurable too early, the starter may lose the very enforcement value it is meant to provide.

Mitigation:

- keep a real default workflow
- document exactly which parts new repos should customize

### Making Memory Too Verbose

If the starter ships a large or overly theoretical memory layer, agents will stop using it.

Mitigation:

- keep memory compact
- prefer stable operational notes
- move project-specific detail back into specs, plans, or feature docs

## Recommended Follow-Up

After this spec is approved:

1. write an implementation plan for the `project-OS-starter` sync
2. update the starter repo in a dedicated branch
3. run starter sync/verify after the changes
4. review the starter for leftover FitCV-specific wording before pushing
