# Public Repo Publication Policy

This document defines what should move from the private development repo into the public curated repo.

## Repo Roles

- Private repo:
  - full engineering source of truth
  - internal plans, specs, workflow assets, and experiments are allowed
- Public repo:
  - curated product-facing mirror
  - only stable, understandable, product-facing materials should appear

Day-to-day development happens in the private repo only.

## Always Include

- `src/`
- `assets/`
- `config/`
- `data/`
- `templates/`
- `tests/`
- `README.md`
- `docs/FitCV-pipeline.md`
- `docs/fitcv-control-plane-setup.md`
- `docs/features/`
- `docs/stages/`
- selected generated discovery docs
- `Dockerfile`
- `docker-compose.yml`
- `.dockerignore`
- `.gitignore`
- `pyproject.toml`
- `requirements.txt`
- `uv.lock`
- stable utility scripts that support public usage

## Always Exclude

- `AGENTS.md`
- `.agents/`
- `.cursor/`
- `agent-core/`
- `codex/rules/`
- `docs/operating_system/`
- `docs/superpowers/`
- `logs/`
- `sample/`
- `.worktrees/`
- debug-only temp folders
- local caches and virtual environments
- scratch notes and local-only helper artifacts

## Review Before Publish

- generated docs beyond the main discovery surfaces
- config examples that might reveal internal-only operational detail
- sample artifacts, benchmark outputs, and demo-only bundles
- generated agent adapter files beyond intentionally public ones
- new scripts that may be more internal than product-facing
- cross-cutting docs that mention internal process rather than product behavior

## Public README Standard

The public README should focus on:

- what the product does
- key capabilities
- high-level architecture
- setup and usage
- stable docs and examples

The public README should not depend on internal plans, archived specs, agent assets, or internal process docs.

## Publication Rule

Use an allowlist-first publication workflow:

1. export approved paths into a clean publication target
2. validate that forbidden content is absent
3. verify required public docs exist
4. inspect the result
5. then publish to the public repo
