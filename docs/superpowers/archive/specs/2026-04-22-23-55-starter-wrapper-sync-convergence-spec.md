---
layer: operating_system
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - scripts/sync_architecture_docs.py
  - scripts/validate_repo_contracts.py
  - repo_config/adoption-mode.yaml
  - docs/operating_system/feature-lifecycle.md
  - docs/operating_system/doc-system-lifecycle.md
  - AGENTS.md
  - tests/test_validate_adoption_shape.py
  - tests/test_validate_repo_contracts.py
related_features: []
related_stages: []
---

# Starter Wrapper Sync Convergence

## Summary

Reduce the highest-cost remaining shared-surface drift by migrating JOB-PROJECT
toward the current `project-OS-starter` wrapper model for architecture sync and
repo-contract validation, while preserving only the smallest truthful
repo-specific adaptations.

This phase is not about broad feature metadata changes. It is about changing the
sync/control architecture so future starter updates land in the same shape
instead of re-opening a large monolithic generator drift every time the starter
contract moves.

## Problem

The repo now passes the latest starter `validate_adoption_shape.py`, but the
larger sync surface still diverges in a costly way:

- `scripts/validate_adoption_shape.py` is exact-match aligned with starter.
- `scripts/sync_architecture_docs.py` is still a large repo-local generator with
  substantial structural drift from the starter wrapper model.
- `scripts/validate_repo_contracts.py` is a repo-local orchestrator around the
  starter-aligned validator rather than a near-starter wrapper with small
  targeted adaptations.
- operating-system docs currently describe a starter-adjacent process, but the
  implementation model underneath still differs enough that the docs require
  explicit customization entries.

This creates an expensive maintenance pattern:

- starter validator changes can be absorbed quickly
- starter sync/workflow changes cannot
- future starter contract updates will keep reopening large diffs in one local
  script instead of small repo-local adapters around shared wrapper behavior

## Decision

JOB-PROJECT should migrate toward the starter wrapper model.

That means:

- prefer starter-style orchestration entrypoints
- move shared workflow shape out of one large local script
- keep repo-specific behavior only where JOB-PROJECT truly differs in source
  layout or publication policy
- record those differences as narrow documented adaptations, not hidden
  implementation drift

## Goals

- Replace the current monolithic sync control surface with a starter-style
  wrapper approach.
- Keep `scripts/validate_adoption_shape.py` exact-match aligned.
- Move JOB-PROJECT toward a smaller adapter layer around shared starter
  orchestration rather than a fully separate implementation model.
- Shrink the documented divergence surface in `repo_config/adoption-mode.yaml`.
- Update repo-control docs so they describe the actual converged wrapper model
  instead of a partly custom sync architecture.

## Non-Goals

- Do not rewrite feature metadata, capability ownership, or lineage content in
  this phase except where generator migration requires regeneration.
- Do not force raw starter paths like `configs/` if this repo still truthfully
  uses `config/`.
- Do not claim zero repo-specific customization if real layout or publication
  differences remain.
- Do not broaden the validator contract beyond the current starter source of
  truth.

## Target State

### Sync Architecture

`scripts/sync_architecture_docs.py` should become a thin workflow wrapper in the
same spirit as starter:

- parse CLI arguments
- call the canonical generator/check flow
- call any required supporting check commands
- expose one stable repo entrypoint

The repo should stop treating `scripts/sync_architecture_docs.py` as the place
where all architecture generation logic lives directly.

### Repo-Local Adaptation Boundary

Any remaining customization should be narrow and explicit, for example:

- `config/` versus starter `configs/`
- absence of starter-only helper scripts or tool paths
- repo-local publication and adapter outputs
- deferred feature-history migration if still not completed

These adaptations should ideally live in one of:

- a small wrapper branch in `scripts/sync_architecture_docs.py`
- a repo-local helper called by the wrapper
- explicit divergence metadata in `repo_config/adoption-mode.yaml`

They should not require preserving a large independently evolved monolithic
generator.

### Repo Contract Wrapper

`scripts/validate_repo_contracts.py` should stay repo-local if needed, but its
shape should be as starter-like as possible:

- same orchestration pattern
- same intent
- only minimal substitutions for repo-local paths and validators

### Docs And Instructions

The following should be re-reviewed after convergence and either synced closer
to starter or left with smaller, clearer rationale:

- `docs/operating_system/feature-lifecycle.md`
- `docs/operating_system/doc-system-lifecycle.md`
- `AGENTS.md`

## Implementation Direction

### Option A

Copy the starter wrapper files directly and then patch for local layout
differences.

Pros:

- fastest route to visible convergence
- easiest way to keep future diffs small

Cons:

- may break immediately if starter wrappers assume helper scripts or folders not
  yet present in JOB-PROJECT

### Option B

Refactor the current repo-local wrapper surfaces to match starter structure and
command flow without forcing unavailable helper files in one step.

Pros:

- safer for the current repo layout
- lets us converge behavior first, then absorb additional helper scripts in
  follow-up work

Cons:

- requires more careful discipline to avoid re-creating a disguised custom
  wrapper model

### Chosen Direction

Use Option B with a hard constraint:

- the end result must look and behave like a starter-style wrapper
- any remaining local difference must be small, explicit, and justified

## Acceptance Criteria

- `scripts/validate_adoption_shape.py` remains exact-match aligned with the
  latest local starter baseline.
- `scripts/sync_architecture_docs.py` is reduced to a thin wrapper-style
  surface rather than a large monolithic generator.
- if helper logic must remain local, it is extracted behind the wrapper
  boundary.
- `scripts/validate_repo_contracts.py` stays starter-like in orchestration
  shape, with only explicit repo-local substitutions.
- `repo_config/adoption-mode.yaml` no longer needs a broad rationale that hides
  structural sync drift; remaining divergences are narrow and truthful.
- `docs/operating_system/feature-lifecycle.md`,
  `docs/operating_system/doc-system-lifecycle.md`, and `AGENTS.md` are either
  synced closer to starter or retain only clearly justified repo-specific text.
- the following all pass after migration:
  - `python scripts/sync_architecture_docs.py --check`
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
  - starter-side `validate_adoption_shape.py --repo-root JOB-PROJECT`
  - `.venv\Scripts\python.exe -m pytest tests/test_validate_adoption_shape.py tests/test_validate_repo_contracts.py -q`

## Risks

- A naive raw copy from starter could break because JOB-PROJECT still uses
  `config/` and repo-local generation paths.
- A weak refactor could preserve the same monolithic implementation under a
  starter-shaped filename, which would reduce clarity but not real drift.
- Doc updates could get ahead of the actual wrapper migration and create a new
  governance mismatch.

## Suggested Next Step

Turn this spec into a focused implementation plan that:

- inventories which starter wrapper dependencies are present versus missing
- chooses the final wrapper shape for `scripts/sync_architecture_docs.py`
- decides whether any local generator internals should move into a helper module
- sequences code migration before doc convergence
