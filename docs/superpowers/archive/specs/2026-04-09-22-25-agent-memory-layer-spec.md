---
feature_type: add
feature_name: none
status: draft
summary: "Add a lightweight agent-memory layer inspired by LLM wiki patterns so recurring failures, invariants, and reusable repo workflows become durable memory for future agent work."
invariants:
  - "Agent memory must stay operational and concise rather than becoming a second general-purpose wiki."
  - "Every important failure-memory entry should either point to an existing guardrail or create a clear follow-up to add one."
  - "The first rollout must reuse the existing repo operating-system structure instead of introducing a parallel documentation hierarchy."
  - "Agent memory should reduce ambiguity and repeated mistakes without adding large context bloat to every task."
---

# Agent Memory Layer Spec

## Triage

Feature type: ADD  
Summary: Introduce a lightweight `agent_memory` layer under `docs/operating_system/` that captures repo invariants, recurring failures, reusable patterns, and unresolved questions, and wire the memory loop into the root agent instructions.  
Reasoning: `JOB-PROJECT` already has strong context surfaces through `AGENTS.md`, `.agents/skills/`, and `docs/operating_system/`, but it lacks a compact place where hard-won lessons from agent mistakes get retained and turned into future guardrails. This work adds a durable memory layer without creating a new full-scale wiki system.  
Invariants:
- agent memory must remain a small operational memory system, not a broad knowledge base
- the memory layer must live inside the existing operating-system doc structure
- repeated failures should be translated into rules, tests, hooks, or scripts rather than left as passive notes
- root agent instructions should point to the memory layer without duplicating its content
Dependencies:
- `AGENTS.md`
- `agent-core/adapters/codex/root-AGENTS.template.md`
- `docs/operating_system/repo-governance.md`
- `docs/operating_system/doc-system-lifecycle.md`
- `.agents/skills/systematic-debugging/SKILL.md`
- `.agents/skills/verification-before-completion/SKILL.md`
Affected stages:
- none
Affected features:
- none
Primary lens: feature
Affected docs:
  feature_yaml: none
  feature_history: none
  feature_docs: none
  cross_cutting_docs:
    - `docs/operating_system/repo-governance.md`
    - `docs/operating_system/agent_memory/README.md`
    - `docs/operating_system/agent_memory/invariants.md`
    - `docs/operating_system/agent_memory/patterns.md`
    - `docs/operating_system/agent_memory/failure-ledger.md`
    - `docs/operating_system/agent_memory/open-questions.md`
  readme: none
  generated: none
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: medium

## Current State

`JOB-PROJECT` already has a meaningful repo operating system:

- repo governance and workflow rules in `docs/operating_system/`
- root and nested instruction surfaces through `AGENTS.md` and generated adapter outputs
- a reusable skill surface under `.agents/skills/`
- a growing set of specs and plans under `docs/superpowers/archive/`
- product tests and verification scripts for important repo workflows

The current gap is not lack of documentation. The current gap is that the repo does not yet preserve lessons from agent mistakes in a compact, reusable, operational form.

Today, the repo can tell an agent what the ideal process is, but it has a weak mechanism for capturing:

- recurring failure modes
- non-obvious repo invariants
- small workflow patterns that prevent repeated mistakes
- unresolved questions that should stay visible across sessions

That means agent learning is still too session-local and person-dependent.

## Problem

The current workflow allows three avoidable memory failures.

### 1. Repeated mistakes are rediscovered instead of remembered

When an agent makes a repo-specific mistake, the lesson often remains in chat history, a plan, or a human memory instead of becoming a stable repo-facing memory artifact.

### 2. Important constraints are scattered across multiple sources

Important truths currently live across:

- `AGENTS.md`
- `docs/operating_system/*.md`
- skill instructions
- specs and plans

This is useful, but it makes it harder to answer:

- what must never be violated
- what keeps going wrong
- what the preferred repo pattern is for a recurring task

### 3. The repo lacks a small memory loop between failure and guardrail

The repo does not yet have a dedicated place that says:

- here is the failure
- here is the correct behavior
- here is the rule, test, script, or hook that now protects against it

Without that loop, mistakes can be documented but not operationalized.

## Goals

1. Add a compact memory layer that stores the most valuable agent-facing lessons.
2. Keep the structure small enough that agents can actually use it.
3. Capture repeated failures, invariants, patterns, and open questions as first-class repo memory.
4. Wire the memory layer into root agent instructions so it becomes part of normal workflow.
5. Make memory entries actionable by linking them to guardrails or explicit follow-up work.

## Non-Goals

This first rollout does not:

- create a full wiki platform
- add a new app, database, or UI for memory
- mirror all repo documentation inside agent memory
- ingest every chat or terminal session automatically
- create a full ontology of entities, concepts, and relationships
- replace existing docs, specs, or feature contracts

## Design Principles

### Operational over encyclopedic

The memory layer should help an agent act correctly, not become a second knowledge base about everything in the repo.

Entries should be short, stable, and corrective.

### Memory should compile into guardrails

A memory entry is most valuable when it leads to one of:

- a repo rule
- a test
- a script check
- a CI hook
- a clearer instruction surface

If the repo only records a failure but never changes behavior, the memory layer will become passive documentation.

### Reuse the existing doc system

The first rollout should live under:

```text
docs/operating_system/agent_memory/
```

This keeps ownership aligned with the existing operating-system layer instead of creating a parallel system.

### Load selectively

Agent memory should not add large context to every task.

The intended loading pattern is:

- always relevant: `invariants.md`
- situational: `patterns.md`, `open-questions.md`
- failure/debugging: `failure-ledger.md`

## Inspiration From LLM Wiki

The useful lesson from LLM wiki systems is not the full platform. The useful lesson is the shape of memory:

- separate stable memory from raw evidence
- keep a few clear page types
- make pages readable by both humans and models
- preserve open questions as real memory, not just resolved knowledge

For `JOB-PROJECT`, the lightweight translation is:

- `failure-ledger.md` for recurring mistakes
- `invariants.md` for non-negotiable truths
- `patterns.md` for preferred repo workflows
- `open-questions.md` for unresolved ambiguities worth surfacing across sessions

Raw incident evidence can stay in plans, specs, chat history, or future `sources/` notes if the repo later needs that depth.

## Options Considered

## Option 1: Single failure-ledger file only

Add only one file:

- `docs/operating_system/agent_memory/failure-ledger.md`

Pros:

- minimal effort
- fastest rollout

Cons:

- mixes stable invariants with one-off incidents
- makes it harder to load the right memory for the right phase
- encourages the ledger to become an unstructured log

## Option 2: Small four-file agent-memory layer

Add:

- `README.md`
- `invariants.md`
- `patterns.md`
- `failure-ledger.md`
- `open-questions.md`

Pros:

- small but structured
- low cognitive overhead
- easy to consult selectively
- closely matches the useful parts of the LLM wiki idea without platform overhead

Cons:

- requires a bit more discipline than one file

## Option 3: Full wiki-style memory system

Add many content types such as:

- `sources/`
- `entities/`
- `concepts/`
- `comparisons/`
- generated machine-readable exports

Pros:

- strongest long-term knowledge architecture

Cons:

- too much complexity for the current repo stage
- likely to create maintenance debt before the team proves the basic memory loop
- duplicates existing feature/stage/doc layers

## Recommendation

Choose Option 2.

It captures the key advantage of the LLM wiki idea, which is structured memory, without adding a second documentation platform.

## Proposed Structure

Create:

```text
docs/operating_system/agent_memory/
  README.md
  invariants.md
  patterns.md
  failure-ledger.md
  open-questions.md
```

### `README.md`

Purpose:

- explain what agent memory is for
- define when each file should be consulted
- define how new memory gets added
- state the rule that repeated failures should become guardrails

### `invariants.md`

Purpose:

- capture non-negotiable repo truths that agents should not rediscover the hard way

Examples:

- generated adapter files are not edited directly
- private/public boundaries remain strict
- feature YAML owns current feature truth when a managed feature is in scope

### `patterns.md`

Purpose:

- document high-value recurring repo workflows in short operational form

Examples:

- how to handle adapter-source changes
- how to add cross-cutting docs without inventing a fake feature
- how to route between specs, plans, and execution

### `failure-ledger.md`

Purpose:

- record repeated or important failures in a way that directly improves the harness

Each entry should include:

- title
- date
- trigger/context
- what went wrong
- correct behavior
- prevention added or required
- links to the relevant docs, rules, tests, or scripts

### `open-questions.md`

Purpose:

- preserve unresolved repo ambiguities that can affect future work

Examples:

- decisions deferred until the hook layer stabilizes
- places where agent behavior still depends on convention rather than explicit rule

## Activation Model

The memory layer should become active in three moments.

### 1. Task start

Consult:

- `invariants.md`
- relevant `patterns.md` entries
- `open-questions.md` when the task touches unsettled areas

### 2. Failure or debugging

Consult:

- `failure-ledger.md`

If the issue is new and meaningful, the resolution should create or update a ledger entry.

### 3. Task closeout

Before claiming work complete, check whether the task revealed:

- a new invariant
- a new pattern
- a new open question
- a repeated failure that should become ledger memory

## AGENTS Integration

The root instruction layer should mention the memory loop, but only briefly.

The root `AGENTS.md` contract should say that agents should consult `docs/operating_system/agent_memory/`:

- before planning when relevant
- during debugging and retries
- before closing work when a task revealed reusable lessons

Because `AGENTS.md` is generated, the real source of truth for that change should be:

- `agent-core/adapters/codex/root-AGENTS.template.md`

Generated outputs to refresh during implementation:

- `AGENTS.md`

## Skill Integration

The first rollout should keep skill integration light.

Recommended immediate integration:

- update the root instruction surface first

Recommended later integration:

- `systematic-debugging` should point to the failure ledger during repeated failures
- `verification-before-completion` should remind agents to promote significant lessons into memory

This keeps the initial scope small while preserving a path to deeper harness integration.

## Memory Quality Rules

To prevent the memory layer from turning into clutter:

- entries must be short and operational
- entries must prefer stable truths over transient chat details
- entries should link to source-of-truth docs instead of copying large explanations
- entries should be removed or rewritten if they become obsolete
- memory should not duplicate full feature docs or specs

## Risks

### 1. The memory layer becomes a second wiki

If too much content is pushed into agent memory, it will become noisy and stop being useful.

Mitigation:

- start with four focused file types plus a README
- reject broad encyclopedic content

### 2. Entries become passive notes

If memory records a failure but no prevention follows, the same mistake will recur.

Mitigation:

- require each important failure entry to name the prevention artifact or explicit follow-up

### 3. Root instructions become bloated

If `AGENTS.md` copies the entire memory model, the repo will gain more instruction bulk instead of clearer activation.

Mitigation:

- keep `AGENTS.md` to a short pointer and workflow trigger only

### 4. Memory duplicates existing source layers

If feature contracts, specs, and cross-cutting docs are mirrored into agent memory, the doc system will become inconsistent.

Mitigation:

- use memory for invariants, patterns, failures, and open questions only
- link outward to feature and operating-system docs when deeper explanation is needed

## Success Criteria

This spec is successful when the implementation delivers:

- a small `docs/operating_system/agent_memory/` structure
- a clear activation model for task start, failure handling, and task closeout
- root instructions that point to the memory layer without duplicating it
- at least one clear path from repeated failure memory to future guardrail creation

## Future Extensions

After the first rollout proves useful, the next extensions should be:

1. lightweight incident source notes for important failures
2. skill-level integration for debugging and closeout workflows
3. CI or review checks that ensure important repeated failures are converted into guardrails
4. optional generated AI-facing summary output such as `agent-memory.txt`

## Recommended Next Step

Write the implementation plan for:

1. the exact `agent_memory/` file scaffolding
2. the root template change in `agent-core/adapters/codex/root-AGENTS.template.md`
3. the generated `AGENTS.md` refresh via sync and verify scripts
4. the initial content rubric for invariants, patterns, failures, and open questions
5. any lightweight follow-up changes to debugging or verification skills
