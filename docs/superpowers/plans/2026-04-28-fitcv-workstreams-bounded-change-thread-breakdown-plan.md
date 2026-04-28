---
layer: operating_system
artifact_type: plan
status: proposed
parent_workstream: none
targets:
  - docs/intent/README.md
  - docs/intent/master-workstream-roadmap.md
  - docs/intent/workstream-coverage-and-progress-guide.md
  - docs/intent/workstreams/
  - docs/intent/workstreams/threads/
  - docs/operating_system/planning-dispatch.md
  - docs/operating_system/prompt_templates/
  - docs/superpowers/specs/2026-04-28-fitcv-workstreams-bounded-change-thread-breakdown-spec.md
related_features: []
related_stages: []
---

# FitCV Workstreams Bounded Change Thread Breakdown Plan

## Summary

Turn the registered FitCV product workstreams into explicit bounded change
thread files and align the repo guidance so the planning ladder is visible and
usable in the worktree.

This plan executes the work described in:

- `docs/superpowers/specs/2026-04-28-fitcv-workstreams-bounded-change-thread-breakdown-spec.md`

## Scope

In scope:

- create the bounded thread registry beneath `docs/intent/workstreams/threads/`
- create lightweight thread files for each registered product workstream
- align the intent and operating-system docs to the new ladder
- align prompt-template guidance with the thread layer
- refresh generated architecture docs if the new docs affect managed metadata linkage

Out of scope:

- drafting the downstream specs for every thread
- executing any product change thread itself
- adding a parallel `operating_system` thread branch

## Execution Steps

- [ ] Step 1: Confirm the current product workstream set is the source of truth.
  - Inputs:
    - `docs/intent/master-workstream-roadmap.md`
    - `docs/intent/workstreams/*.md`
  - Verify:
    - each product workstream has a stable registered file
    - `operating_system` threads remain outside the product registry

- [ ] Step 2: Add the bounded change thread registry structure.
  - Create:
    - `docs/intent/workstreams/threads/README.md`
    - one folder per registered product workstream
  - Verify:
    - the thread registry explains the ladder
    - the folder naming matches registered workstream names

- [ ] Step 3: Materialize lightweight thread files beneath each product workstream.
  - Create thread files that capture:
    - goal
    - why now
    - dependencies
    - shared surfaces
    - linked spec
    - linked plan
    - notes
  - Verify:
    - independent and dependency-coupled slices are visible
    - recommended first-spec threads are easy to spot

- [ ] Step 4: Align the intent-layer guidance with the new structure.
  - Update:
    - `docs/intent/README.md`
    - `docs/intent/workstreams/README.md`
    - `docs/intent/workstream-coverage-and-progress-guide.md`
  - Verify:
    - the repo explains `roadmap -> workstreams -> threads -> specs -> plans -> execution`
    - coverage, progress, and divergence are treated as distinct review modes

- [ ] Step 5: Align the operating-system guidance with the new structure.
  - Update:
    - `docs/operating_system/planning-dispatch.md`
    - `docs/operating_system/repo-governance.md`
    - `docs/operating_system/prompt_templates/*` as needed
  - Verify:
    - planning dispatch names the thread layer explicitly
    - repo governance treats bounded change threads as the safe parallel execution unit

- [ ] Step 6: Refresh starter-sync bookkeeping without overwriting FitCV-specific meaning.
  - Update:
    - `repo_config/adoption-mode.yaml`
  - Verify:
    - the latest local starter baseline ref is recorded
    - divergences remain explicit where FitCV intentionally differs

- [ ] Step 7: Run the managed-doc validation flow.
  - Run:
    - `python scripts/sync_architecture_docs.py`
    - `python scripts/sync_architecture_docs.py --check`
    - `python scripts/validate_adoption_shape.py`
    - `python scripts/validate_repo_contracts.py --fast`
  - Verify:
    - root-doc metadata checks pass
    - managed architecture docs are refreshed if linkage changed

## Shared-Surface Risks

- `docs/intent/master-workstream-roadmap.md`
  - changing the strategic layer too often can make thread files stale immediately
- `docs/intent/workstreams/*.md`
  - workstream IDs and filenames must stay stable or the thread folders drift
- `docs/operating_system/planning-dispatch.md`
  - if the ladder here disagrees with the thread registry, future specs and plans will route inconsistently
- `docs/operating_system/prompt_templates/`
  - prompt guidance must not point straight from workstream to spec when thread files now exist
- managed generated docs
  - intent/governance doc updates may change metadata-derived references and require a sync

## Sequencing Notes

- create the thread registry before updating routing docs so the docs point to a real surface
- update the governance and prompt surfaces before drafting downstream thread specs
- run the architecture sync/check path after the doc-layer changes, not before

## Acceptance Criteria

- the repo contains an explicit `docs/intent/workstreams/threads/` layer
- each registered product workstream has lightweight bounded thread files
- the intent and operating-system docs describe the new planning ladder consistently
- prompt-template guidance mentions bounded change threads as the bridge between workstreams and specs
- the managed-doc validation flow passes after the changes

## Next Artifact

After this plan, the next artifact should be the first dedicated thread spec:

- `docs/superpowers/specs/2026-04-28-fitcv-semantic-spine-stage-authority-contract-spec.md`

Then follow with the matching implementation plan:

- `docs/superpowers/plans/2026-04-28-fitcv-semantic-spine-stage-authority-contract-plan.md`
