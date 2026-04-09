---
feature_type: add
feature_name: none
status: draft
summary: "Add a minimal CI-first hook layer that automatically enforces adapter verification, tests, and publication-boundary checks for JOB-PROJECT."
invariants:
  - "The first hook layer must reuse existing repo scripts and tests rather than introducing a second policy system."
  - "Hook enforcement must be centralized and deterministic before any local-machine hook setup is considered."
  - "The initial hook set must stay small, fast, and binary so it becomes normal workflow rather than ignored noise."
  - "Private/public boundary protections must remain explicit and automatically checked before merge."
---

# CI Hook Layer Spec

## Triage

Feature type: ADD  
Summary: Introduce the first real hook layer for `JOB-PROJECT` by wiring the repo's existing verification scripts and tests into CI so key checks run automatically on push and pull request events.  
Reasoning: The repo already contains meaningful instructions, skills, rules, and verification scripts, but those checks are mostly run manually. This leaves the system dependent on memory and discipline rather than automatic enforcement. A CI-first hook layer adds the missing trigger mechanism without changing product behavior.  
Invariants:
- the initial hook layer must remain CI-first, not local-hook-first
- existing scripts remain the source of truth for adapter and publication-boundary checks
- the first version should enforce only a small number of high-value checks
- hook failures must be easy to understand and tied to clear remediation steps
Dependencies:
- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`
- `scripts/publish_public_repo.ps1`
- `tests/*`
- `AGENTS.md`
- `codex/rules/*.rules`
- `docs/operating_system/repo-governance.md`
- `docs/operating_system/publication-workflow.md`
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
    - `docs/operating_system/publication-workflow.md`
  readme: `README.md`
  generated: none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Current State

`JOB-PROJECT` already has a meaningful repo operating system:

- repo governance under `docs/operating_system/`
- agent-facing instruction surfaces through `AGENTS.md`, nested `AGENTS.md`, and `codex/rules/*.rules`
- reusable workflow memory under `.agents/skills/`
- adapter sync and verification scripts
- a curated publication workflow and private/public boundary validation
- a non-trivial automated test suite

The current gap is not missing checks. The gap is that the repo does not automatically trigger enough of them when code changes.

At the moment, the workflow depends too heavily on a person or agent remembering to run:

- `.\scripts\sync_agent_adapters.ps1`
- `.\scripts\verify_agent_adapters.ps1`
- the relevant test suite
- the publication export check when boundary-sensitive files change

That means the repo has memory and rules, but only a weak hook layer.

## Problem

The current workflow allows three avoidable failure modes:

### 1. Adapter drift can land silently

If `agent-core/adapters/*` or generated instruction files change without sync and verification, the committed repo can drift away from its canonical adapter source.

### 2. Manual verification is easy to skip

Even when the repo tells contributors what to run, check execution still depends on remembering, available time, and correct interpretation of when each script matters.

### 3. Publication-boundary safety is not part of the normal merge loop

The repo has a private/public boundary model, but there is no automatic hook ensuring boundary-sensitive changes still prepare a clean curated export before merge.

## Goals

1. Add a real automatic trigger mechanism for the highest-value repo checks.
2. Enforce adapter synchronization and verification on push and pull request events.
3. Enforce baseline test execution automatically.
4. Add a publication-boundary dry check to the CI loop.
5. Keep the first hook layer simple enough that the team will trust and keep it.

## Non-Goals

This first hook layer does not:

- add local pre-commit or pre-push hooks
- add a full agent-eval harness
- add scheduled cleanup or garbage-collection jobs
- redesign the repo's existing scripts
- replace tests or scripts with new duplicate CI-only logic

## Design Principles

### CI first

The first hook layer should live in GitHub Actions rather than local Git hooks.

Reason:

- every contributor and agent sees the same behavior
- no per-machine bootstrapping is required
- enforcement happens at the branch/PR boundary
- it keeps the system centralized and auditable

### Reuse existing checks

The repo already has meaningful checks. The hook layer should call them rather than reimplement them.

This preserves one source of truth for verification behavior.

### Binary before comprehensive

The first version should fail only on clear, high-signal conditions:

- adapter drift
- test failure
- publication-boundary preparation failure

Avoid a noisy first rollout that adds many weak signals and teaches people to ignore CI.

## Options Considered

## Option 1: CI-only hook layer

Add a GitHub Actions workflow that runs on push and pull request events.

Checks:

- adapter sync
- adapter verify
- test suite
- publication-boundary dry run

Pros:

- centralized
- deterministic
- no local setup friction
- strongest improvement per unit of effort

Cons:

- feedback arrives after push rather than before commit

## Option 2: CI plus local Git hooks

Add CI plus pre-commit or pre-push hooks.

Pros:

- faster local feedback

Cons:

- more setup complexity
- harder to standardize
- easy to bypass or misconfigure

## Option 3: Full hook mesh

Add CI, local hooks, scheduled jobs, and agent-specific eval hooks immediately.

Pros:

- strongest theoretical coverage

Cons:

- too much complexity for the first rollout
- likely to create maintenance debt before the minimal layer proves its value

## Recommendation

Choose Option 1 first.

This gives the repo a real hook layer quickly while preserving a clean path to future local hooks and scheduled harness jobs.

## Proposed Hook Workflow

Create a GitHub Actions workflow under:

```text
.github/workflows/repo-hooks.yml
```

Trigger on:

- `push`
- `pull_request`

The workflow should contain three jobs.

### Job 1: Adapter Integrity

Purpose:

- ensure generated adapter outputs match their canonical source

Steps:

1. checkout repo
2. set up the required runtime
3. run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

4. fail if sync produces diffs or verify reports drift

Expected outcome:

- any change to adapter source or generated instruction files must be reflected cleanly in the branch

### Job 2: Baseline Test Suite

Purpose:

- ensure repo changes do not break automated coverage

Steps:

1. checkout repo
2. install dependencies
3. run the baseline test command for the repo

The exact command should be chosen in the implementation plan, but it should start with the existing project test suite rather than a partial custom set.

Expected outcome:

- failures in product or control-plane behavior block merge

### Job 3: Publication Boundary Dry Check

Purpose:

- ensure the curated public export still prepares successfully and does not violate the private/public boundary model

Steps:

1. checkout repo
2. run:

```powershell
.\scripts\publish_public_repo.ps1
```

3. fail if export preparation fails

Expected outcome:

- boundary-sensitive changes are validated as part of the normal branch loop

## Failure Semantics

The hook layer should be intentionally binary:

- green means the branch satisfies the repo's baseline automated checks
- red means there is a concrete remediation path

Examples:

- adapter job fails -> run sync, inspect generated diffs, recommit
- test job fails -> fix behavior or update tests
- publication-boundary job fails -> fix export allowlist, remove private references, or correct docs

The hook layer should not begin with warning-only checks.

## Rollout Phases

## Phase 1: Minimal CI hook layer

Ship:

- adapter integrity job
- baseline test job
- publication-boundary dry check

This is the core deliverable for the current work.

## Phase 2: Tighten scope and speed

After the first version proves stable:

- optimize runtime
- split fast vs slow test layers if needed
- add path-based triggering if beneficial

## Phase 3: Optional local hooks

Only after CI is trusted:

- consider local pre-commit or pre-push helpers
- keep local hooks advisory or convenience-oriented at first

## Risks

### 1. CI becomes too slow

If the first hook layer is too expensive, contributors may see it as friction instead of support.

Mitigation:

- start with only three high-value jobs
- optimize later based on actual runtimes

### 2. Hook logic duplicates repo logic

If GitHub Actions reimplements checks separately from repo scripts, the system will drift.

Mitigation:

- call existing scripts directly wherever possible

### 3. Publication dry checks may expose environment assumptions

The publication script may assume tools or repo state that need explicit CI setup.

Mitigation:

- keep the first CI plan explicit about prerequisites
- fix environment assumptions in the implementation phase rather than skipping the check entirely

### 4. Teams may overreach too early

If local hooks, eval harnesses, and scheduled cleanups are added immediately, the hook layer may become fragile.

Mitigation:

- keep the first rollout intentionally narrow

## Success Criteria

This spec is successful when the implementation delivers:

- a GitHub Actions workflow that runs automatically on push and pull request
- automatic adapter synchronization and verification checks
- automatic baseline test execution
- automatic publication-boundary dry validation
- clear remediation when any of those checks fail

## Future Extensions

After the first hook layer is stable, the next harness improvements should be:

1. a failure ledger for repeated agent mistakes
2. structural or architectural boundary checks
3. local convenience hooks
4. scheduled cleanup and drift jobs
5. agent-task evals for repo policy compliance

## Recommended Next Step

Write the implementation plan for:

1. the exact GitHub Actions workflow file
2. the runtime and dependency setup required in CI
3. the concrete test command to use in the first rollout
4. whether publication dry checks need any CI-safe defaults
5. the doc updates needed in `docs/operating_system/` and `README.md`
