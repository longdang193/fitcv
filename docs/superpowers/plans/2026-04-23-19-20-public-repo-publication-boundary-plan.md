---
layer: operating_system
artifact_type: plan
status: completed
created_at: 2026-04-23T19:20:00+02:00
completed_at: 2026-04-23T19:45:00+02:00
parent_workstream: none
related_specs:
  - docs/superpowers/specs/2026-04-23-public-repo-publication-boundary-spec.md
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

# Public Repo Publication Boundary Implementation Plan

## Summary

Align the curated private-to-public export with the intended product-facing
boundary by publishing the right top-level docs, trimming private-oriented
language from those docs, and omitting or sanitizing internal lifecycle-heavy
feature surfaces.

## Batch A: Export Policy And Script

1. Update `repo_config/publication-config.json` so the public allowlist includes
   the public-safe top-level docs:
   - `docs/setup.md`
   - `docs/configuration.md`
   - `docs/usage.md`
   - `docs/pipeline.md`
   - `docs/architecture.md`
2. Stop treating `docs/features/` as an unconditional public family.
3. Add explicit export omissions for:
   - `docs/features/*/history.md`
   - `docs/features/*/lineage.generated.yaml`
   - feature-local migration checklists and other internal-only feature docs
4. Extend `scripts/publish_public_repo.ps1` so it can remove configured omitted
   paths after allowlist copy and before validation.

## Batch B: Sanitize Public Top-Level Docs

1. Rewrite top-level docs to be public-safe and repo-relative:
   - `docs/setup.md`
   - `docs/configuration.md`
   - `docs/usage.md`
   - `docs/pipeline.md`
   - `docs/architecture.md`
2. Remove private-repo workflow wording that teaches internal lifecycle or
   publication operations instead of product usage.
3. Replace desktop-local absolute links with repo-relative links suitable for
   GitHub rendering in the public repo.

## Batch C: Validate Curated Export

1. Run a dry export with `scripts/publish_public_repo.ps1`.
2. Inspect the exported `docs/` surface to confirm:
   - the new top-level docs are present
   - `docs/features/*/history.md` is absent
   - `docs/features/*/lineage.generated.yaml` is absent
   - no local absolute paths remain
   - no `docs/superpowers/` or `docs/operating_system/` references remain
3. Run `git diff --check`.

## Verification

- `.\scripts\publish_public_repo.ps1 -ExportRoot .tmp-public-audit`
- `git diff --check`

## Expected Outcome

`fitcv-public` will have a stronger public-facing docs surface with setup,
usage, pipeline, and architecture guidance, while omitting internal
plan/history/evidence layers that belong only in the private repo.

## Closeout

Completed.

Implemented:

- expanded the public top-level doc allowlist
- added configurable omitted-public-path handling to the publish script
- sanitized `setup`, `configuration`, `usage`, `pipeline`, and `architecture`
  docs for public-safe export
- verified the dry public export now includes the intended top-level docs and
  excludes feature `history.md`, `lineage.generated.yaml`, and migration
  checklists
