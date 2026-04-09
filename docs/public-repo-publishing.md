# Public Repo Publishing

This guide explains how this project should manage the private development repo and the public curated repo.

## Remote Roles

- `origin`
  - private source repo
  - primary development remote
- `public`
  - public curated repo
  - downstream publication target

Use `origin` for normal development and collaboration. Use `public` only through the curated publish workflow.

## Operating Rule

The private repo is the development source of truth.

The public repo is not a second development repo. It is a curated publication surface for:

- stable code
- product-facing documentation
- setup guides
- examples

## Publish Workflow

Use the allowlist-first publish script:

```powershell
.\scripts\publish_public_repo.ps1
```

That prepares a clean export under a temporary directory and validates that internal-only materials are not included.

To publish to the public repo after inspection:

```powershell
.\scripts\publish_public_repo.ps1 -Push
```

## What The Script Does

1. resolves the repo root
2. prepares a clean export target
3. copies only approved public-facing paths
4. validates forbidden paths are absent
5. checks that required public docs exist
6. optionally commits and pushes to the `public` remote

The script also keeps private-only repo operating layers out of the public export, including:

- `AGENTS.md`
- `.agents/`
- `.cursor/`
- `agent-core/`
- `codex/rules/`
- `docs/operating_system/`
- `docs/superpowers/`
- `logs/`
- `sample/`

These exclusions are public-mirror exclusions, not private-repo exclusions. For example, `.agents/` remains tracked in the private repo and is filtered only during public publication.

## Before Publishing

Review:

- [public-repo-publication-policy.md](public-repo-publication-policy.md)
- the generated export contents
- the public README and docs from an external-reader perspective

## Ongoing Maintenance Rules

- Develop in the private repo only.
- Keep internal workflow assets private.
- Refresh public docs only when they help an external reader understand the product.
- Update the publish allowlist when new product-facing paths become intentionally public.
- Keep agent-core, operating-system docs, and adapter outputs private unless an explicit publication rule is added later.
