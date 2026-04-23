---
layer: change
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - repo_config/publication-config.json
  - scripts/publish_public_repo.ps1
  - docs/setup.md
  - docs/configuration.md
  - docs/usage.md
  - docs/pipeline.md
  - docs/FitCV-pipeline.md
  - docs/architecture.md
  - docs/features/*/feature.source.yaml
  - docs/features/*/<feature_id>.yaml
  - docs/features/*/history.md
  - docs/features/*/lineage.generated.yaml
  - docs/stages/*.source.yaml
  - docs/stages/*.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
related_features:
  - cv_system
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - normalize
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# Public Repo Publication Boundary Cleanup

## Summary

Tighten the private-to-public publication boundary so `fitcv-public` becomes a
clean product-facing mirror instead of a thin subset in some areas and an
overexposed internal lifecycle mirror in others.

This phase should follow the private/public repo governance model:

- private repo stays the full development source of truth
- public repo stays a curated downstream mirror
- allowlist-first export remains the publication mechanism
- files should be classified as `keep as-is`, `keep and sanitize`, or `omit`
  rather than copied wholesale by directory

No runtime product behavior should change in this phase.

## Problem

The current publication shape has two opposing issues.

### 1. Useful top-level public docs are missing

`fitcv-public/docs` currently includes:

- `docs/FitCV-pipeline.md`
- `docs/fitcv-control-plane-setup.md`
- `docs/features/`
- `docs/stages/`
- selected generated discovery

But it omits several top-level docs that are useful for an external reader:

- `docs/setup.md`
- `docs/usage.md`
- `docs/pipeline.md`
- `docs/architecture.md`

`docs/configuration.md` is also absent, and its current content is partly
public-useful and partly private-governance-oriented.

### 2. Internal lifecycle detail is over-published

The public export currently includes `docs/features/` wholesale. That means the
public repo receives files such as:

- `docs/features/*/history.md`
- `docs/features/*/lineage.generated.yaml`
- generated feature contracts containing refs to private `docs/superpowers/*`

These files preserve useful structure, but the current raw forms still expose
internal design and execution lineage that belongs in the private repo.

## Goals

- Publish the public-safe top-level docs that help external readers understand
  setup, usage, architecture, and pipeline flow.
- Stop publishing internal lifecycle material in raw form when it points back
  to private plans, specs, or workflow history.
- Preserve public-facing structure where possible by sanitizing fields rather
  than deleting whole document families unnecessarily.
- Keep the publish workflow allowlist-first and script-driven.
- Add enough publication-boundary validation that the private repo does not
  accidentally leak local absolute links or internal workflow references again.

## Non-Goals

- Do not turn the public repo into a second development source.
- Do not publish `docs/operating_system/`, `docs/superpowers/`, `.agents/`,
  `agent-core/`, or generated instruction surfaces.
- Do not change product code, tests, runtime settings, or architecture-doc
  generation semantics for private-repo use.
- Do not remove public-safe generated discovery just because some generated
  lifecycle files are too internal in their current shape.

## Content Classification

### Keep As-Is

These are already good public surfaces or close enough to remain public without
structural change:

- `README.md`
- `docs/FitCV-pipeline.md`
- `docs/fitcv-control-plane-setup.md`
- `docs/stages/*.source.yaml`
- `docs/stages/*.yaml`
- `docs/generated/architecture_dag.yaml`
- `docs/generated/capability_lineage.yaml`
- `src/`
- `templates/`
- stable runtime config under `config/`
- product-facing scripts already in the public allowlist

### Keep And Sanitize

These should be public, but not in their current private-oriented form:

- `docs/setup.md`
  - replace local absolute links with repo-relative public-safe links
  - keep product setup guidance
- `docs/usage.md`
  - keep operator workflow guidance
  - trim private-repo engineering workflow wording where it teaches private
    lifecycle maintenance rather than public product usage
- `docs/pipeline.md`
  - keep as the short architecture/pipeline index
  - replace local absolute links
- `docs/architecture.md`
  - keep runtime architecture explanation
  - trim Mode B / private doc-system maintenance wording
- `docs/configuration.md`
  - either rewrite to focus on public runtime configuration only, or split the
    public-safe runtime portion from private repo-governance config guidance
- `docs/features/*/<feature_id>.yaml`
  - keep only if refs to private `docs/superpowers/*` are scrubbed
- `docs/features/*/feature.source.yaml`
  - keep only if these remain understandable and free of private-only guidance
- `docs/features/*/lineage.generated.yaml`
  - keep only if a public-safe export variant can remove or sanitize private
    `specs`, `plans`, and other internal evidence paths while preserving useful
    public structure

### Omit Entirely

These should remain private in the current model:

- `docs/AGENTS.md`
- `docs/operating_system/*`
- `docs/superpowers/*`
- `docs/features/*/history.md`
- `docs/public-repo-publication-policy.md`
- `docs/public-repo-publishing.md`
- internal migration checklists such as
  `docs/features/inspection_debugging/migration-checklist.md`

Rationale:

- `history.md` is internal rollout chronology derived from private plans
- publication-policy docs describe the private/public workflow itself, not the
  public product
- operating-system and superpowers layers are explicitly private repo-governance
  surfaces

## Proposed Boundary Changes

### 1. Expand the top-level doc allowlist

Add these to the public export after sanitization:

- `docs/setup.md`
- `docs/usage.md`
- `docs/pipeline.md`
- `docs/architecture.md`

Add `docs/configuration.md` only if it is rewritten or export-sanitized to
exclude private repo-governance content such as `repo_config/` workflow rules.

### 2. Narrow the feature-doc export model

Replace the current blanket `docs/features` export with a more selective model.

Preferred direction:

- omit `history.md`
- omit raw `lineage.generated.yaml` unless a public-safe sanitization path is
  added
- keep `feature.source.yaml` and generated feature contracts only if they do
  not expose private `docs/superpowers/*` refs or internal process guidance

If sanitization is added, prefer:

- preserve keys and public-safe evidence categories
- remove or rewrite values that point at private plans/specs/history

Short rule:

- redact payload, not evidence shape

### 3. Strengthen publish-script sanitization

`scripts/publish_public_repo.ps1` should validate or scrub:

- local absolute filesystem links
- references to `docs/superpowers/`
- references to `docs/operating_system/`
- references to private lifecycle plans/specs inside generated feature docs

The script should not merely drop lines opportunistically if that leaves broken
or misleading documents. Prefer targeted sanitization rules tied to the file
family being exported.

### 4. Align publication config to the intended public information model

`repo_config/publication-config.json` should reflect the new classification:

- top-level product docs explicitly included
- feature-doc subtypes exported intentionally rather than by whole-folder copy
- internal publication-policy docs excluded
- generated discovery kept explicitly

## Acceptance Criteria

- A dry export from `scripts/publish_public_repo.ps1` includes public-safe top
  level docs for setup, usage, pipeline, and architecture.
- The dry export contains no:
  - `.agents/`
  - `docs/operating_system/`
  - `docs/superpowers/`
  - `AGENTS.md`
  - local absolute filesystem links
  - raw refs to private `docs/superpowers/*` inside exported feature docs
- `docs/features/*/history.md` is absent from the public export.
- Public README and docs make sense without requiring internal plans or
  operating-system context.
- The publication config and publish script clearly express the keep/sanitize/
  omit boundary.

## Risks

- Over-trimming feature docs could make the public repo less credible or less
  navigable. This phase should preserve safe structure where possible instead of
  deleting whole document families reflexively.
- Under-trimming generated lifecycle docs could continue to leak private design
  and execution lineage. Sanitization rules must be explicit and testable.
- Top-level docs like `configuration.md` may need real rewriting rather than
  simple allowlist changes because they currently mix public runtime guidance
  with private repo-governance detail.
