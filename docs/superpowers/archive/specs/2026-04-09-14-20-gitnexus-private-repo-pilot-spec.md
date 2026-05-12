---
feature_type: modify
feature_name: none
status: draft
summary: "Pilot GitNexus inside the private repo as optional internal codebase-navigation tooling without changing the product or public mirror contract."
invariants:
  - "GitNexus remains private-repo-only tooling during the pilot."
  - "The pilot must not become a runtime or build dependency of FitCV."
  - "The public curated repo must not depend on GitNexus docs, config, or workflow assets."
  - "Adoption should be justified by measured workflow value, not tool novelty."
---

# GitNexus Private-Repo Pilot Spec

## Triage

Feature type: MODIFY  
Summary: Try GitNexus as optional internal tooling in the private repo to improve codebase navigation, dependency tracing, and agent context gathering before deciding whether to adopt it more broadly.  
Reasoning: The project now has a clean private/public repo split, which creates a safe place to evaluate internal-only tooling. GitNexus could help with architecture tracing across the pipeline, control plane, artifact contracts, and docs, but it should be proven in real use before it becomes part of the team workflow or future reusable skills.  
Invariants:
- The private repo remains the only place where GitNexus-related setup or workflow guidance may live during the pilot
- FitCV runtime behavior, APIs, and product docs remain independent of GitNexus
- The pilot must be removable without affecting normal development or publication
- Any later reusable skill should be based on verified usage patterns from the pilot, not assumptions
Dependencies:
- `docs/operating_system/publication/public-repo-publication-policy.md`
- `docs/operating_system/publication/public-repo-publishing.md`
- `.agents/skills/private-public-repo-governance/`
- internal repo workflow docs
- optional local GitNexus install/config assets
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
  readme: none
  generated: none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: low

## Decision

Yes: GitNexus should be tried in this project, but only as a **private-repo pilot**.

The right goal is not “integrate GitNexus into FitCV.”  
The right goal is “learn whether GitNexus materially improves internal engineering work on FitCV.”

That means:

- install and use it only in the private repo
- keep it out of the public mirror contract
- keep it optional during the trial
- evaluate it on real tasks before creating a reusable skill

## Problem

This codebase has enough moving parts that code discovery is now a meaningful productivity concern:

- multi-stage pipeline behavior
- control-plane routes and templates
- artifact contracts across runtime, worker, and UI
- feature-doc and cross-cutting-doc alignment
- repeated debugging of drifts between modes and artifact shapes

Current exploration works, but it is still fairly manual:

- search by text
- open many files
- trace links between code, docs, and artifacts by hand

GitNexus may improve this, but adopting it prematurely would add process and tooling noise without proof.

## Goals

1. Evaluate whether GitNexus helps with real internal engineering tasks in this repo.
2. Keep the trial fully private and reversible.
3. Define success criteria before adoption.
4. Capture enough learning to support or reject a future reusable GitNexus skill.

## Non-Goals

This pilot does not:

- change FitCV runtime behavior
- add GitNexus as a product dependency
- expose GitNexus setup or workflow details in the public repo
- require every contributor or every session to use GitNexus
- commit to a future GitNexus skill before the pilot proves value

## Proposed Pilot Scope

The pilot should be narrow and task-driven.

### In scope

- local private-repo installation or setup needed to run GitNexus
- using GitNexus for codebase exploration and dependency tracing
- using it during real debugging, review, or architecture-analysis tasks
- documenting internal-only usage guidance if needed
- evaluating whether it improves agent and developer workflows

### Out of scope

- product-facing documentation about GitNexus
- GitNexus-specific project runtime hooks
- changes to public publication policy beyond preserving GitNexus as private-only
- committing to GitNexus-based automation before the pilot succeeds

## Recommended Pilot Tasks

The pilot should be evaluated against real work that is already painful enough to matter.

Recommended task types:

1. Pipeline tracing
- follow a stage boundary from `ranking` into `cv_analysis` and exported artifacts

2. Control-plane tracing
- trace a run-detail UI element back to worker-produced artifacts and pipeline state

3. Artifact contract analysis
- find all producers and consumers of a field such as reranker-blocked status or run-mode metadata

4. Doc/code drift analysis
- identify where a feature doc, generated doc, and runtime behavior disagree

5. Change impact analysis
- answer “what files and contracts are likely affected if this behavior changes?”

These are good pilot tasks because they are common, cross-cutting, and expensive to do manually.

## Success Criteria

GitNexus should only be considered worth keeping if it demonstrates clear value on real tasks.

Success looks like:

1. Faster navigation
- fewer manual searches and fewer file hops to answer cross-file questions

2. Better architectural visibility
- easier tracing of producers, consumers, and boundary contracts

3. Better debugging support
- clearer identification of where a contract drift originates

4. Low workflow friction
- setup is manageable
- output is understandable
- it fits the private repo without creating constant maintenance work

5. No public-boundary leakage
- no GitNexus-specific material becomes required in the public mirror

## Failure Criteria

The pilot should be considered unsuccessful if:

- it mostly duplicates `rg`, direct code reading, and current docs without a meaningful win
- setup or maintenance cost is high
- output is too noisy or hard to trust
- it encourages shallow tool trust instead of code verification
- it pressures the project into public-facing tooling dependencies

## Repo-Boundary Rules

During the pilot, GitNexus must remain private-only.

### Allowed in private repo

- local setup notes
- internal workflow docs
- internal skills or usage guidance
- optional helper scripts if they are truly private-only

### Not allowed in public repo

- GitNexus config
- GitNexus-specific workflow docs
- GitNexus as a required setup step
- product docs that depend on GitNexus for understanding the repo

If any GitNexus artifacts are added locally, the publication boundary must continue to exclude them by default.

## Adoption Decision After the Pilot

At the end of the pilot, there should be an explicit go / no-go decision.

### If successful

- keep GitNexus as optional private internal tooling
- write a reusable future-facing skill based on real usage patterns
- optionally add a small private-only usage guide for future projects

### If unsuccessful

- remove or stop using the local setup
- avoid creating a skill
- keep the repo workflow unchanged

## Recommended Next Step

Write a short implementation plan that covers:

1. pilot setup location and private-only boundaries
2. exact evaluation tasks
3. success/failure criteria
4. any publication-boundary updates needed to keep GitNexus private-only
5. the review checkpoint where adoption is accepted or rejected

