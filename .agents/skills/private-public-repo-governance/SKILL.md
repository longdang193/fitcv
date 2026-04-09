---
name: private-public-repo-governance
description: Use when a project needs a private internal repo and a separate public curated repo, or when deciding what should stay private versus what can be published in a clean product-facing repository.
---

# Private / Public Repo Governance

## Overview

Use this skill to set up or maintain a **private-source / public-mirror** workflow.

Core rule:

- private repo = development source of truth
- public repo = curated downstream mirror

Do not treat both repos as equal day-to-day development sources.

## When to Use

Use this skill when:

- a project needs a private internal repo plus a public showcase/product repo
- a public repo must stay clean while the internal repo keeps plans, drafts, agent assets, or experiments
- you need to define what stays private vs public
- you need a repeatable publish workflow between repos
- you need to validate that internal-only materials do not leak into a public release

Do not use this skill for:

- runtime/product validation
- normal single-repo branching strategy
- deployment/release engineering that is unrelated to repo boundary management

## Repo Role Model

### Private repo

The private repo is the full engineering workspace.

Typical contents:

- all source code
- tests
- full docs tree
- internal plans/specs/history
- agent/rules assets
- experiments
- debug and operating materials when useful

### Public repo

The public repo is the product-facing publication surface.

Typical contents:

- stable code
- polished README
- product-facing docs
- usage/setup guides
- examples worth showing
- clean generated discovery docs when useful

## Content Classification

Classify paths into three buckets before designing a publish workflow.

### `always_private`

Examples:

- `.agents/`
- `.cursor/`
- `docs/superpowers/`
- logs/debug artifacts
- internal prompts/workflow docs
- abandoned experiments
- scratch files

### `usually_public`

Examples:

- `src/`
- `tests/` when they improve clarity and trust
- `README.md`
- product-facing docs
- setup guides
- examples

### `review_before_publish`

Examples:

- generated docs
- config examples
- benchmark outputs
- sample artifacts
- architecture notes that may include internal workflow detail

## Publication Workflow

Preferred model:

1. Develop in the private repo.
2. Decide what is mature enough to publish.
3. Build a curated export for the public repo.
4. Validate the export boundary.
5. Push only the curated result to the public repo.

Prefer an **allowlist-first** publish workflow:

- copy approved paths
- avoid "copy everything, then delete bad stuff"

Choose between:

- **manual curated publish**
  Use when publication is infrequent and repo structure is still evolving.
- **scripted export workflow**
  Use when publication is recurring and boundary mistakes would be costly.

## Boundary Validation

Before publishing, run a public-release boundary validation pass.

At minimum, check:

- no `.agents/` content
- no `.cursor/` content
- no `docs/superpowers/` content
- no logs/debug artifact folders
- no internal-only process docs
- no private-path references in public-facing docs
- public README still makes sense without internal context

If any of those fail, stop and fix the export boundary before pushing public changes.

## Public Repo Smell Checks

Treat these as warning signs:

- the public repo mentions internal planning systems
- public docs depend on archived internal specs/plans to be understandable
- the public repo contains agent/rule folders
- the public repo looks like a workbench instead of a product repo
- contributors are developing directly in the public repo instead of publishing into it

## Common Mistakes

### Developing in both repos

Problem:

- drift
- duplicated cleanup work
- unclear source of truth

Fix:

- keep development in private only
- publish outward intentionally

### Treating the public repo as "private minus a few deletions"

Problem:

- easy leakage of internal material

Fix:

- use an allowlist-oriented export policy

### Mixing runtime validation with publish validation

Problem:

- repo-governance checks get confused with product correctness checks

Fix:

- keep this skill focused on publication-boundary validation only

## References

- Publish policy template:
  [references/publish-policy-template.md](references/publish-policy-template.md)
- Public release checklist:
  [references/public-release-checklist.md](references/public-release-checklist.md)

