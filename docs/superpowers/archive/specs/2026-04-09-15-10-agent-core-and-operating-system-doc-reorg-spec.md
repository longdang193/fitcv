---
feature_type: modify
feature_name: none
status: building
summary: "Introduce a long-term agent-core architecture and a separate operating-system doc layer so shared agent-facing material, repo governance, skills, and Codex-specific adapters are clearly separated."
invariants:
  - "Human-readable repo governance and workflow rules remain a first-class private doc layer, not an accidental byproduct of agent adapters."
  - "Agent-facing shared sources, generated adapter files, and reusable skills must have distinct responsibilities."
  - "Codex-specific rules remain adapter-specific outputs, even when they are generated from shared policy intent."
  - "The public curated repo must not depend on private operating-system or agent-core materials."
---

# Agent-Core And Operating-System Doc Reorg Spec

## Triage

Feature type: MODIFY  
Summary: Reorganize the private repo so repo rules and workflows live in a human-readable `docs/operating_system/` layer, while shared agent-facing material moves into `agent-core/` and generates adapter-specific instruction surfaces such as `AGENTS.md`, `codex/rules/*.rules`, and future agent files.  
Reasoning: The current repo has a strong skill library and a mature docs system, but instructions, workflow rules, and Codex-facing execution policy are spread across `.agents/skills`, `.cursor/rules`, and internal docs in ways that blur responsibilities. The project is also preparing for near-term multi-agent reuse across future projects, so the current Codex-only structure should evolve into a cleaner long-term model before more vendor-specific surfaces are added ad hoc.  
Invariants:
- Repo rules and workflows must remain understandable to humans without reading generated adapter files
- Shared principles/policies must be separated from adapter-specific renderings
- Skills must remain focused task playbooks rather than a dumping ground for repo governance
- Codex execution policy must be explicit and stored as real rule files, not only implied by prose
Dependencies:
- `.agents/skills/`
- `.cursor/rules/`
- `docs/operating_system/publication/public-repo-publication-policy.md`
- `docs/operating_system/publication/public-repo-publishing.md`
- `docs/features/*`
- `docs/generated/*`
- future root and nested `AGENTS.md`
- future `codex/rules/*.rules`
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
    - `docs/operating_system/publication/public-repo-publication-policy.md`
    - `docs/operating_system/publication/public-repo-publishing.md`
    - `docs/operating_system/*.md`
  readme: none
  generated: none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

The repo currently has useful pieces, but they are organized around the current tool history rather than clear long-term roles.

### 1. Instructions, rules, and workflows are mixed together

Today the repo contains:

- a real skill library under `.agents/skills/`
- process and operating docs under `.cursor/rules/operating-system/`
- publication and governance docs under `docs/`

These are all valuable, but they do not represent the same type of thing:

- repo governance and workflow rules
- reusable agent task playbooks
- adapter-specific instructions for one agent runtime
- execution policy for sandboxed command behavior

That makes the current model harder to scale and harder to reuse across future projects.

### 2. Codex-facing structure is not yet first-class

The project does not yet have:

- a root `AGENTS.md`
- nested `AGENTS.md` files for directory-specific overrides
- a real `codex/rules/` adapter layer for command execution policy

So the repo is missing the clean instruction/policy surfaces that Codex now supports directly.

### 3. Multi-agent reuse is becoming a real requirement

The current direction is not just “make Codex work better here.”  
The stated goal is to build something that can be reused across future projects and, soon, across multiple agent surfaces.

That means the repo needs to separate:

- shared human-readable intent
- structured policy intent
- reusable skill workflows
- agent-specific renderings

### 4. Repo governance should not masquerade as features or skills

The earlier discussion clarified that `operating_system` is primarily about repo rules and workflow structure, not product behavior and not ordinary platform code.

That means items like:

- publication workflow
- doc lifecycle
- planning dispatch
- GitNexus pilot
- instruction layering

need a clear home as operating-system docs, rather than being stretched into product feature language or hidden inside skills.

## Goals

1. Create a long-term structure that cleanly separates:
- repo governance and workflows
- shared agent-facing sources
- reusable skills
- adapter-specific generated files

2. Adopt Codex-native instruction layering with:
- root `AGENTS.md`
- nested `AGENTS.md` where needed
- explicit `codex/rules/*.rules`

3. Preserve a human-readable private doc source of truth for repo rules and workflows.

4. Make the model extensible to future agent adapters without prematurely over-automating everything.

## Non-Goals

This reorganization does not:

- change FitCV product behavior
- change runtime pipeline semantics
- require immediate parity across every future agent
- require that every skill be automatically compiled for every agent
- expose operating-system materials in the public curated repo

## Proposed Architecture

The target architecture should separate four layers clearly.

### 1. Human-readable operating-system docs

This is the repo governance and workflow source of truth for humans.

Proposed home:

```text
docs/operating_system/
  repo-governance.md
  doc-system-lifecycle.md
  planning-dispatch.md
  publication-workflow.md
  stage-lifecycle.md
  tooling/
    gitnexus-pilot.md
```

Purpose:

- explain how the repo is organized
- explain private/public repo policy
- explain doc-system and workflow rules
- explain internal tooling policy and pilots

These docs are private-repo-only and should not be treated as generated adapter artifacts.

### 2. Shared agent-facing core

This is the reusable source for agent-directed material that may later be rendered into adapter-specific files.

Proposed home:

```text
agent-core/
  principles/
    repo-guidelines.md
    docs-policy.md
    collaboration-model.md
  policies/
    command-execution.yaml
    publication-boundary.yaml
    instruction-layering.yaml
  skills/
    brainstorming/
    systematic-debugging/
    ...
  adapters/
    codex/
      AGENTS.md
      rules/
    claude/
      CLAUDE.md
    gemini/
      GEMINI.md
    antigravity/
      AGENT.md
```

Purpose:

- store the shared subset that actually feeds agent-native files
- keep principles/policies separate from task skills
- keep adapter outputs distinct from shared sources

### 3. Repo-local skill discovery surface

Codex still needs a repo-local skill layout it can discover directly.

Short-term target:

- keep `.agents/skills/` working
- either hand-maintain it during migration or sync it from `agent-core/skills/`

Long-term target:

- `agent-core/skills/` becomes canonical
- `.agents/skills/` becomes a generated or synchronized discovery surface for Codex

### 4. Adapter-specific instruction and policy files

These are the actual files each agent runtime consumes.

Examples:

- root `AGENTS.md`
- nested `AGENTS.md` files
- `codex/rules/*.rules`
- `CLAUDE.md`
- `GEMINI.md`

These should be reproducible from shared sources where possible, but still committed so the repo works without a generation step at read time.

## Responsibilities By Layer

### `docs/operating_system/`

Owns:

- repo rules and workflows
- publication process
- doc taxonomy and lifecycle
- internal tooling pilots
- human-readable governance

Does not own:

- task execution playbooks
- adapter-specific instruction files
- executable Codex rule syntax

### `agent-core/principles/`

Owns:

- short shared agent-facing guidance
- collaboration expectations
- repo interaction principles

Does not own:

- full human governance docs
- vendor-specific syntax

### `agent-core/policies/`

Owns:

- structured policy intent suitable for compilation or synchronization

Examples:

- command policy intent
- publication boundary policy
- instruction layering policy

Does not own:

- prose-only governance explanation
- runtime product configuration

### `agent-core/skills/`

Owns:

- reusable agent workflows
- one focused job per skill
- optional references/scripts/assets for that workflow

Does not own:

- repo governance
- publication rules
- general project policy

### `agent-core/adapters/`

Owns:

- agent-specific renderings
- adapter-specific formatting and file conventions

Does not own:

- the original shared intent

## Why This Split Is Better

### 1. It matches the actual semantics

This split reflects the real categories:

- repo rules/workflows
- shared agent guidance
- skills
- adapters

instead of blending them into one folder tree because they all feel “AI-related.”

### 2. It keeps Codex-native structure first-class

The reorg explicitly supports:

- root and nested `AGENTS.md`
- Codex rule files
- repo-local skill discovery

instead of treating Codex behavior as something implicit.

### 3. It supports future multi-agent reuse without forcing false parity

The architecture accepts that:

- skills are relatively portable
- policy intent may be portable
- actual rules and adapter files are not literally portable

So it avoids the mistake of assuming all agents can consume the same outputs unchanged.

### 4. It keeps human governance readable

If all governance is pushed into generated adapter files, humans lose the real source of truth.  
Keeping `docs/operating_system/` separate solves that.

## Recommended Migration Direction

This should be done in phases.

### Phase 1: establish the operating-system layer

- create `docs/operating_system/`
- move or rewrite current operating docs from `.cursor/rules/operating-system/` into that layer
- define what belongs in operating-system docs vs skills

### Phase 2: adopt Codex-native instruction surfaces

- add root `AGENTS.md`
- add nested `AGENTS.md` only where behavior truly differs
- add `codex/rules/` for actual Codex execution policy

### Phase 3: introduce `agent-core/`

- create `principles/`
- create `policies/`
- create `adapters/`
- decide whether `agent-core/skills/` is canonical immediately or after a transition period

### Phase 4: add sync/validation

- generate or sync adapter files
- verify generated adapter outputs are current
- keep committed outputs reproducible

### Phase 5: add future adapters only when actually needed

- do not overbuild adapter generation for unused agent targets

## Important Constraints

### 1. Do not let `agent-core/` become a second docs dump

Only shared agent-facing source material belongs there.

The full governance story should still live in `docs/operating_system/`.

### 2. Do not let `skills` become policy storage

Skills must remain execution playbooks.

### 3. Do not treat Codex rules as portable prose

Codex rules are real execution-policy artifacts.  
They may be derived from shared intent, but they remain adapter-specific outputs.

### 4. Do not introduce speculative adapters too early

The target architecture can name future adapters, but implementation should prioritize the agent surfaces that will actually be used soon.

## Decision Summary

The long-term direction is good, with two explicit guardrails:

1. `docs/operating_system/` must remain the human governance layer
2. `agent-core/` must stay focused on shared agent-facing material plus adapter generation, not all repo policy

With those boundaries, the proposed architecture becomes a strong reusable pattern for this repo and future projects.

## Recommended Next Step

Write an implementation plan that defines:

1. exact target tree
2. which current files move to `docs/operating_system/`
3. what belongs in root and nested `AGENTS.md`
4. what initial Codex rules should exist under `codex/rules/`
5. whether `.agents/skills/` or `agent-core/skills/` is canonical in phase 1
6. what sync/validation script is required to keep generated adapters trustworthy

