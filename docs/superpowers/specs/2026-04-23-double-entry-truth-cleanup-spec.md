---
layer: change
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - docs/features/*/history.md
  - docs/pipeline.md
  - docs/FitCV-pipeline.md
  - docs/features/*/feature.source.yaml
  - docs/features/*/<feature_id>.yaml
  - docs/features/*/lineage.generated.yaml
  - docs/stages/*.source.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
related_features:
  - cv_system
  - inspection_debugging
  - trigger_run_management
  - pipeline_performance
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Double-Entry Truth Cleanup

## Summary

Remove or demote documentation surfaces that manually re-enter current-state
truth already owned upstream by code, feature sources, stage sources, and
completed plan metadata.

This phase is a doc-system cleanup phase. It should preserve useful narrative
and operator context while tightening the source-of-truth flow:

- upstream truth stays in code, feature sources, stage sources, and plan
  metadata
- downstream contracts, lineage, generated history, and discovery stay derived
- prose docs explain and orient rather than becoming a second editable contract

No product runtime behavior should change in this phase.

## Problem

The current architecture-doc system is mostly aligned, but it still contains a
few real or likely double-entry spots where downstream layers restate facts that
should flow from upstream sources.

### 1. Manual changelog truth inside feature histories

At least these feature histories contain large manual `## Changelog` sections:

- `docs/features/cv_system/history.md`
- `docs/features/inspection_debugging/history.md`

Those sections restate feature behavior version-by-version in prose even though
the same current-state truth is already represented upstream by:

- code and tests
- `feature.source.yaml`
- completed plan metadata
- generated feature contracts and lineage outputs

That creates a second editable current-state truth surface inside a downstream
history document.

### 2. Detailed pipeline narrative acting like a second contract

`docs/pipeline.md` already points readers to stage sources, generated stage
contracts, and generated discovery outputs as the canonical architecture layer.

However, `docs/FitCV-pipeline.md` currently carries detailed manual stage
responsibilities and “important current behavior” notes for all seven stages.

That makes `docs/FitCV-pipeline.md` behave like a second hand-maintained
pipeline contract instead of a conceptual explainer that references the owning
stage and feature sources.

### 3. Generated history noise from broad completed plans

Generated history blocks correctly derive from completed plan metadata, but many
older broad rollout plans now emit repetitive history entries such as:

- `Affected capabilities: none recorded`
- `Verification: See plan body closeout verification notes.`
- generic outcome summaries repeated across many features

This is not a manual source-of-truth violation, but it does create noisy
downstream repetition that makes the doc system feel more double-entered than it
really is.

## Goals

- Remove manual current-state truth from feature-history changelog sections.
- Keep feature histories focused on generated implementation chronology plus
  genuinely human-only notes.
- Demote `docs/FitCV-pipeline.md` from quasi-contract to explainer/reference
  doc.
- Keep `docs/pipeline.md` as the short navigation layer that points to
  canonical stage and generated views.
- Preserve lawful generated derivation such as feature freshness, lineage
  timeline, and generated history blocks.
- Reduce generated history noise where the generator can truthfully omit
  low-signal repeated text without losing source traceability.

## Non-Goals

- Do not change product runtime code, tests, settings, or routes.
- Do not move current behavior truth out of feature sources or stage sources.
- Do not hand-edit generated feature contracts, lineage files, stage contracts,
  or generated discovery files except through source changes and regeneration.
- Do not delete human notes that provide rollout context, operator caveats, or
  rationale not already represented upstream.
- Do not collapse all narrative docs into generated files; explanatory prose is
  still allowed when it is clearly downstream and non-authoritative.

## Target State

### Feature History Contract

`docs/features/<feature_id>/history.md` should have this role:

- generated block:
  - completed-plan chronology only
  - source plan link
  - derived capability list when available
  - verification and outcome only when plan metadata is specific enough to add
    real signal
- human notes block:
  - rollout notes
  - migration caveats
  - operator guidance
  - rationale that is not already represented in source metadata

It should not contain long manual version-by-version changelog sections that
restate current feature behavior.

### Pipeline Doc Contract

`docs/pipeline.md` should remain:

- short
- navigational
- explicit about where canonical stage truth lives

`docs/FitCV-pipeline.md` should become:

- a conceptual end-to-end explainer
- a mental model for readers
- a reference to stage sources, feature sources, and generated discovery

It should not remain the place where stage-by-stage current contract behavior is
manually maintained in parallel with stage sources.

### Generated Derivation Contract

These repeated facts remain acceptable because they are derived, not re-entered:

- freshness in generated feature contracts
- timeline in `lineage.generated.yaml`
- generated history sections built from completed plan metadata
- generated discovery indexes

If cleanup is applied here, it should reduce low-signal noise rather than remove
useful derived traceability.

## Proposed Changes

### Batch A: Remove manual changelog truth from feature histories

Start with:

- `docs/features/cv_system/history.md`
- `docs/features/inspection_debugging/history.md`

Expected change:

- remove the large manual `## Changelog` sections
- keep `## Human Notes`
- if needed, replace the changelog with a short note that current behavior truth
  lives in source contracts and plans

Then audit the remaining feature histories for similar manual current-state
changelog content.

### Batch B: Demote `docs/FitCV-pipeline.md` to explainer-only

Expected change:

- keep high-level purpose, operator mental model, and execution overview
- trim or rewrite sections that restate current stage contracts
- replace manual current-stage assertions with references to:
  - `docs/stages/*.source.yaml`
  - `docs/stages/*.yaml`
  - `docs/features/*/feature.source.yaml`
  - `docs/generated/architecture_dag.yaml`
  - `docs/generated/capability_lineage.yaml`

### Batch C: Reduce generated-history noise

Inspect the architecture-doc generator and generated history section rules for
entries that add little signal when plan metadata is generic.

Possible truthful reductions:

- suppress `Affected capabilities: none recorded`
- suppress generic placeholder verification text
- suppress generic placeholder outcome text

Only do this if the resulting generated history still truthfully reflects the
available plan metadata.

## Acceptance Criteria

- `docs/features/cv_system/history.md` no longer contains a large manual
  behavior changelog.
- `docs/features/inspection_debugging/history.md` no longer contains a large
  manual behavior changelog.
- `docs/FitCV-pipeline.md` no longer acts as a parallel stage contract surface.
- `docs/pipeline.md` still clearly points readers to canonical stage and
  feature-source layers.
- No manual `revision`, `latest_change_id`, `last_updated_at`, `timeline`, or
  `manual_refs` fields are introduced into feature sources.
- Generated feature contracts, lineage, history, and discovery continue to be
  regenerated from source.
- The following pass:
  - `python scripts/sync_architecture_docs.py`
  - `python scripts/sync_architecture_docs.py --check`
  - `python scripts/validate_adoption_shape.py`
  - `python scripts/validate_repo_contracts.py --fast`
  - `git diff --check`

## Risks

- Removing too much manual narrative from feature histories could erase useful
  operator context. Cleanup should remove duplicated current-state truth, not
  rationale or rollout notes.
- Over-compressing `docs/FitCV-pipeline.md` could make the system harder to
  understand for humans. The goal is “explainer, not contract,” not “delete the
  narrative.”
- Reducing generated history text too aggressively could make plan lineage less
  understandable. Any generator cleanup should remove placeholder noise only
  when the source metadata is genuinely empty or generic.
