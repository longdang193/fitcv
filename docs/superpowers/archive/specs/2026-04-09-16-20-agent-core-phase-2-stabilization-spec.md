---
feature_type: modify
feature_name: none
status: draft
summary: "Stabilize the new agent-core and operating-system structure by reducing compatibility debt, strengthening Codex-facing instruction and rule surfaces, and formalizing the phase-1 skill-ownership boundary."
invariants:
  - "The private repo remains the only source of operating-system and agent-core materials."
  - "Phase 2 must strengthen the new structure without prematurely migrating canonical skill ownership."
  - "Codex-facing AGENTS and rules should become intentional, trustworthy surfaces rather than thin scaffolding."
  - "Compatibility shims should be reduced or clarified, not allowed to become a permanent parallel system."
---

# Agent-Core Phase 2 Stabilization Spec

## Triage

Feature type: MODIFY  
Summary: Perform the stabilization pass after the initial repo reorganization so the new `docs/operating_system`, `agent-core`, `AGENTS.md`, and `codex/rules` layers become the trusted working structure instead of a partially duplicated transition state.  
Reasoning: Phase 1 successfully established the new architecture, but the repo still carries transitional debt: older `.cursor/rules` surfaces still exist, some internal references still point at legacy locations, the Codex-facing instruction and rule files are present but intentionally minimal, and the skill ownership transition is not yet explicitly locked down. Without a focused stabilization phase, the repo risks drifting into two competing systems instead of one stable operating model.  
Invariants:
- `docs/operating_system/` remains the human-readable governance source of truth
- `AGENTS.md` and `codex/rules/*.rules` become clearer and more intentional without turning into long workflow manuals
- `.agents/skills/` remains canonical in phase 2
- skills must remain aligned with the Codex Skills model: one focused workflow per skill folder, `SKILL.md` as the primary entrypoint, and optional `scripts/`, `references/`, `assets/`, or `agents/openai.yaml` only when they materially help the workflow
- Future-agent adapters remain out of scope until Codex stabilization is complete
Dependencies:
- `docs/operating_system/*`
- `agent-core/*`
- `AGENTS.md`
- `docs/AGENTS.md`
- `src/fitcv/AGENTS.md`
- `src/fitcv_cp/AGENTS.md`
- `codex/rules/*.rules`
- `.cursor/rules/*`
- `.agents/skills/*`
- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`
- `scripts/publish_public_repo.ps1`
Affected stages:
- none
Affected features:
- none
Primary lens: cross-cutting
Affected docs:
  feature_yaml: none
  feature_history: none
  feature_docs: none
  cross_cutting_docs:
    - `docs/operating_system/repo-governance.md`
    - `docs/operating_system/doc-system-lifecycle.md`
    - `docs/operating_system/planning-dispatch.md`
    - `docs/operating_system/publication-workflow.md`
    - `docs/operating_system/publication/public-repo-publication-policy.md`
    - `docs/operating_system/publication/public-repo-publishing.md`
  readme: none
  generated: none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Current State After Phase 1

Phase 1 established the main structural pieces:

- `docs/operating_system/` exists
- `agent-core/` exists with principles, policies, and Codex adapter templates
- root and nested `AGENTS.md` files are generated
- initial `codex/rules/*.rules` exist
- sync and verification scripts exist
- the public publication boundary excludes the new private-only layers

This is a strong start, but it is still a transition state rather than a settled operating model.

## Remaining Problems

### 1. Compatibility debt is still present

Older `.cursor/rules` content still exists and can still look authoritative, even though the tracked human-readable governance source has moved to `docs/operating_system/`.

That creates ambiguity about which layer should be trusted first.

### 2. The new Codex-facing files are still scaffolding

The current `AGENTS.md` and `codex/rules/*.rules` are working, but they are deliberately light.

They still need a clearer contract for:

- what belongs in root vs nested `AGENTS.md`
- what should be expressed as executable Codex policy
- what should stay in human docs instead of moving into agent instruction files

### 3. The skill migration boundary is not yet explicit enough

The repo has already decided that `.agents/skills/` stays canonical in phase 2, but this is not yet enforced strongly enough as an operating rule.

Without that clarity, it would be easy to accidentally start treating `agent-core/skills/` as canonical before the sync layer is proven.

There is also a formalization issue: the repo should keep skill structure aligned with the official Codex Skills model rather than drifting into a custom repo-specific format.

That means phase 2 should explicitly preserve:

- one focused workflow per skill
- `SKILL.md` as the primary skill entrypoint
- strong `description` fields for trigger quality
- optional helper material such as `scripts/`, `references/`, `assets/`, and `agents/openai.yaml` only where the workflow actually benefits

### 4. Verification exists, but it is not yet part of the normal operating loop

The adapter sync and verify scripts work, but phase 2 should make them part of the repo’s normal maintenance expectations.

## Goals

1. Reduce compatibility ambiguity so the new structure is clearly authoritative.
2. Refine `AGENTS.md` and `codex/rules/*.rules` into intentional working surfaces.
3. Formalize the phase-2 skill ownership rule.
4. Make adapter verification part of the normal repo workflow.
5. Make the skill boundary explicit in a way that matches the Codex Skills guidance.

## Non-Goals

Phase 2 does not:

- move canonical skill ownership to `agent-core/skills/`
- add `CLAUDE.md`, `GEMINI.md`, or other adapters
- add broad multi-agent sync generation
- change public product behavior or runtime behavior

## Proposed Phase 2 Work

### 1. Reduce or clarify `.cursor/rules` compatibility shims

Decide for each remaining `.cursor/rules/*` file whether it should:

- remain as a thin compatibility shim
- be reduced further
- or be retired because `docs/operating_system/` and the new adapter surfaces now own that behavior

The important rule is: old paths must not feel like a second source of truth.

### 2. Refine the `AGENTS.md` layering contract

Make root and nested `AGENTS.md` more intentional by defining:

- repo-wide expectations for the root file
- local overrides for pipeline code, control-plane code, and docs
- what content should never appear in `AGENTS.md` because it belongs in `docs/operating_system/` or skills

### 3. Strengthen the first real `codex/rules` set

Upgrade the current minimal rules into a clearer initial policy set for:

- command execution expectations
- publication-boundary protection
- any other low-risk, high-value Codex-native policy that is clearly adapter-specific

Keep the rule set small and explicit.

### 4. Formalize the phase-2 skill boundary

State clearly in governance docs that:

- `.agents/skills/` is still canonical in phase 2
- `agent-core/skills/` is deferred
- skills remain workflow playbooks rather than policy storage

Also state explicitly that, during phase 2, the repo follows the Codex Skills model for formal skill shape:

- one skill folder per focused workflow
- `SKILL.md` as the required entrypoint
- descriptions optimized for trigger discovery
- optional `scripts/`, `references/`, `assets/`, and `agents/openai.yaml` only when justified

This keeps the skills layer aligned with how Codex actually discovers and uses repo skills.

### 5. Bring adapter verification into the normal workflow

Phase 2 should define when to run:

- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`

Examples:

- before committing adapter changes
- before repo-governance changes
- before publication-boundary changes

## Desired Outcome

After phase 2:

- humans know `docs/operating_system/` is the governance source of truth
- Codex sees clearer root and nested `AGENTS.md`
- Codex rules express a small but real execution-policy contract
- `.agents/skills/` is explicitly stable as the canonical skill surface
- `.agents/skills/` is not just canonical, but intentionally aligned with the Codex Skills format
- the repo no longer feels like two competing instruction systems

## Recommended Next Step

Write the phase 2 implementation plan around:

1. compatibility-shim decisions for `.cursor/rules/*`
2. exact root vs nested `AGENTS.md` responsibilities
3. the initial stable Codex rule set
4. explicit phase-2 skill canon wording
5. workflow integration for adapter verification
6. the exact Codex Skills-aligned expectations the repo will enforce for skill shape and ownership

