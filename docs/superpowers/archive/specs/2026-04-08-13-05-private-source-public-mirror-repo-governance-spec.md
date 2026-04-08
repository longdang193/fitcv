---
feature_type: modify
feature_name: repository_governance
status: draft
summary: "Establish the private repository as the full internal source of truth and the public repository as a curated product-facing mirror with an explicit publication workflow."
invariants:
  - "Internal planning, agent, and operating-system materials remain in the private repository only."
  - "The public repository must be intentionally curated rather than used as a direct development source."
  - "Publishing to the public repository must be reproducible and reviewable."
  - "Product-facing documentation must stay clean, stable, and understandable without internal context."
---

# Private-Source / Public-Mirror Repo Governance Spec

## Triage

Feature type: MODIFY  
Summary: Split repository responsibilities cleanly by treating the private repository as the development source of truth and the public repository as a curated downstream mirror for product-facing code and documentation.  
Reasoning: The project now has two distinct audiences with conflicting needs. Internal development needs full plans, specs, agent/rule assets, experiments, and operational history. The public presentation needs a clean product story, stable docs, and minimal code noise. A branch-only policy cannot satisfy both once the public repo is meant to stay polished.  
Invariants:
- The private repo remains the only place where all internal materials are guaranteed to exist.
- The public repo contains only curated product-facing content.
- Promotion from private to public is an explicit publish action, not an automatic side effect of normal development.
- Public history should not expose internal plans, drafts, agent skills, or abandoned experiments.
Dependencies:
- `README.md`
- `docs/features/*`
- `docs/generated/*`
- `docs/superpowers/archive/*`
- `.agents/`
- `.cursor/`
- release/publish workflow documentation
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
    - `README.md`
    - `docs/FitCV-pipeline.md`
    - `docs/fitcv-control-plane-setup.md`
  readme:
    - `README.md`
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
Generated refresh required: likely
Spec needed: yes
Plan needed: yes
Risk level: medium

## Decision

Yes: development should continue in the **private repository**, and the **public repository** should be maintained as a curated downstream mirror.

This is the cleanest model because it aligns with the real split in purpose:

- the private repo is for building
- the public repo is for presenting and distributing

Trying to use both repos as equal development sources would create immediate drift, duplicated cleanup work, and constant confusion about what belongs where.

## Problem

The project now needs to support two valid but different goals:

1. **Internal Work**
- save all current work
- keep specs, plans, archived design history
- keep `.agents` and `.cursor`
- keep operational/debugging materials when useful
- allow unfinished or exploratory work

2. **Product-Facing Presentation**
- show what the product is and does
- present stable features and usage guides
- avoid internal planning noise
- avoid agent/rules details
- keep the repo clean, understandable, and portfolio-friendly

These goals conflict if they share a single publication surface.

## Why Branches Alone Are Not Enough

A “private branch / public branch” model inside one repo is not enough for this use case:

- if the repo is public, its branches are public too
- even with two repos, long-lived development on both sides will drift quickly
- branch discipline alone does not solve content curation
- accidental publication risk stays high if the public repo is also used as a normal dev repo

So the right unit of separation is not just a branch. It is a **repo role**.

## Proposed Repo Roles

### 1. Private Repo: Internal Source of Truth

The private repo is the only full-fidelity development repo.

It should contain:

- all source code
- all tests
- full docs tree
- `docs/superpowers/archive/*`
- `.agents/`
- `.cursor/`
- internal operating-system/process docs
- experiment branches
- release preparation work

This is where normal development continues.

### 2. Public Repo: Product-Facing Mirror

The public repo is a curated downstream publication target.

It should contain only product-facing materials, for example:

- stable source code
- stable tests worth showing publicly
- clean `README.md`
- usage/setup docs
- `docs/features/*`
- `docs/FitCV-pipeline.md`
- selected generated discovery docs if they are helpful and clean

It should exclude:

- `.agents/`
- `.cursor/`
- `docs/superpowers/`
- internal plans/specs/drafts
- noisy logs/debug artifacts
- abandoned experiments
- internal workflow or prompt-governance details

## Operating Model

### Private-first development

All day-to-day work happens in the private repo:

1. implement
2. test
3. document
4. decide what is mature enough to publish

### Intentional publication to public

Publishing to the public repo is a separate action with a different standard:

1. prepare a release/publication branch in private
2. remove or exclude internal-only content
3. verify public docs are coherent on their own
4. push curated content to the public repo

This keeps the public repo understandable and prevents internal process material from leaking into the product-facing story.

## Publication Strategy

The recommended strategy is:

### Option A: Curated export workflow

Create a small publish workflow that exports only approved files from the private repo into a temp/release worktree, then pushes that curated result to the public repo.

This is the preferred direction because:

- it is explicit
- it is reproducible
- it minimizes accidental publication
- it scales better than repeated manual cleanup

The export workflow should operate from an allowlist-oriented policy rather than a vague “delete bad stuff before pushing” policy.

### Option B: Manual curated branch

A simpler initial step is a manually maintained publication branch in the private repo that is pushed to the public repo.

This is acceptable as an intermediate stage, but weaker because:

- it is easier to make mistakes
- cleanup logic lives in people’s heads
- reproducibility is lower

Recommended long-term direction: start simple if needed, but move to a scripted curated export.

## Content Policy

### Always private-only

- `.agents/`
- `.cursor/`
- `docs/superpowers/`
- internal plans/specs
- internal decision notes
- debug-only operational artifacts
- ad hoc scratch files

### Usually public-facing

- `src/`
- `config/` if no secrets or internal-only policies are exposed
- `tests/` when they improve trust and readability
- `README.md`
- `docs/features/*`
- cross-cutting product docs
- clean examples

### Needs explicit review before publish

- generated docs
- sample artifacts
- benchmark outputs
- settings/config examples
- pipeline artifacts that may reveal internal operational details

## Documentation Contract

The two repos should tell different stories:

### Private repo docs

Purpose:
- full engineering memory
- implementation history
- design rationale
- workflow/process support

### Public repo docs

Purpose:
- explain the product
- explain how to run and use it
- demonstrate quality and architecture
- present stable contracts only

The public repo should read like a polished product/portfolio repository, not like a workbench.

## Recommended Next Changes

### 1. Keep working in the private repo

This should be the only normal development repo going forward.

### 2. Define a public export policy

Create a written allowlist/exclude policy for what is published.

At minimum, define:

- always include
- always exclude
- review-before-publish

### 3. Add a publish workflow

Introduce either:

- a script such as `scripts/publish_public_repo.ps1`, or
- a dedicated release procedure doc

The script should:

- stage curated content into an export directory or release worktree
- remove internal-only files
- verify expected docs exist
- publish to the public repo remote

### 4. Reframe the public README

The public repo README should lead with:

- product purpose
- key capabilities
- architecture summary
- usage/setup
- examples

and should avoid internal methodology framing.

## Non-Goals

This change does not:

- require both repos to stay byte-identical
- require the public repo to preserve full engineering history
- expose internal planning material publicly
- make the public repo the primary development location

## Recommendation

Adopt this operating rule immediately:

> **Private repo = source of truth. Public repo = curated downstream mirror.**

That gives you the cleanest long-term setup for both:

- serious internal development
- strong public presentation of your product and work

