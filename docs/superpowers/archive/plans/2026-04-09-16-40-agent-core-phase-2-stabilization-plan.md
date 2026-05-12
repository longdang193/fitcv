---
feature_type: modify
feature_name: none
status: draft
summary: "Stabilize the new operating-system and agent-core structure by reducing compatibility debt, refining Codex-facing instruction surfaces, formalizing Codex-aligned skill ownership, and integrating adapter verification into normal workflow."
---

# Agent-Core Phase 2 Stabilization Plan

## Objective

Turn the phase-1 scaffold into a stable working structure by:

- reducing old-path compatibility ambiguity
- refining root and nested `AGENTS.md`
- strengthening the first real `codex/rules/*.rules`
- formalizing `.agents/skills/` as the phase-2 canonical Codex skill surface
- integrating sync and verification into the repo operating loop

## Scope

This plan covers private-repo operating structure only.  
It does not add future-agent adapters or move canonical skill ownership into `agent-core/skills/`.

## Task 1: Audit remaining compatibility shims

Review the remaining `.cursor/rules/*` files and classify each as one of:

- keep temporarily as a thin shim
- reduce further
- retire

Priority targets:

- `.cursor/rules/project-operating-system.mdc`
- `.cursor/rules/superpowers-bootstrap.mdc`
- any remaining references to `.cursor/rules/operating-system/*`

Outcome:

- the repo no longer has ambiguous parallel operating-system sources

## Task 2: Strengthen root and nested `AGENTS.md`

Refine the current generated `AGENTS.md` files so they express a clearer contract.

Targets:

- `AGENTS.md`
- `docs/AGENTS.md`
- `src/fitcv/AGENTS.md`
- `src/fitcv_cp/AGENTS.md`

Actions:

- clarify what belongs in the root file
- clarify what local overrides belong in nested files
- remove anything that should instead live in `docs/operating_system/`
- keep all files short and operational

Outcome:

- Codex sees intentional layered instructions, not just placeholder scaffolding

## Task 3: Stabilize the first Codex rule set

Refine the first real `codex/rules/*.rules` into a small but durable policy set.

Targets:

- `codex/rules/command-execution.rules`
- `codex/rules/publication-boundary.rules`

Actions:

- confirm which execution-policy cases should be explicit
- keep the rule set focused on true policy, not workflow prose
- align the rules with current private/public publication boundaries
- avoid speculative rules for agent surfaces not yet in use

Outcome:

- a clear initial Codex-native execution-policy contract

## Task 4: Formalize the phase-2 skill ownership rule

Document clearly that:

- `.agents/skills/` is canonical in phase 2
- `agent-core/skills/` remains deferred
- skills are execution playbooks, not repo policy

Update the operating-system docs and any relevant instruction surfaces so this rule is obvious.

Outcome:

- contributors and future agents do not treat `agent-core/skills/` as canonical prematurely

## Task 5: Codex Skills-aligned skill audit

Review the current `.agents/skills/` library against the official Codex Skills model.

Audit questions:

- is each skill one focused workflow?
- does each skill have a clear `SKILL.md` entrypoint?
- is the `description` field written for trigger quality?
- are `scripts/`, `references/`, `assets/`, or `agents/openai.yaml` used only when they materially help?
- is any repo-governance or workflow-policy content wrongly stored as a skill?

Actions:

- identify skills that are too broad
- identify skills that contain policy rather than workflow
- identify candidates for optional metadata cleanup later

Outcome:

- the canonical skill surface is explicitly aligned with Codex’s discovery and usage model

## Task 6: Update sync and verify workflow expectations

Decide and document when these scripts must run:

- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`

Recommended triggers:

- after changing `agent-core/adapters/*`
- after changing `agent-core/policies/*`
- after changing root or nested generated adapter files
- before commits that touch adapter surfaces or publication-boundary rules

Outcome:

- adapter drift checks become part of the normal repo workflow

## Task 7: Update publication and governance docs

Update the relevant docs so the phase-2 stabilized model is reflected consistently.

Likely targets:

- `docs/operating_system/repo-governance.md`
- `docs/operating_system/publication-workflow.md`
- `docs/operating_system/publication/public-repo-publication-policy.md`
- `docs/operating_system/publication/public-repo-publishing.md`

Outcome:

- the human-readable governance layer matches the stabilized repo structure

## Task 8: Verification

Before closing phase 2:

1. run adapter sync
2. run adapter verification
3. confirm old `.cursor/rules` references are reduced or clearly shimmed
4. confirm root and nested `AGENTS.md` are intentional and scoped
5. confirm `.agents/skills/` remains canonical
6. confirm the public export still excludes:
   - `AGENTS.md`
   - `agent-core/`
   - `codex/rules/`
   - `docs/operating_system/`

## Completion Criteria

Phase 2 is complete when:

- the repo no longer feels split between old and new operating systems
- `AGENTS.md` layering is clear and useful
- `codex/rules/*.rules` are small but real policy files
- `.agents/skills/` is explicitly and intentionally canonical
- the skill library is aligned with the Codex Skills model
- adapter sync and verification are part of normal maintenance

