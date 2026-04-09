# Publication Workflow

This document defines how private work is promoted to the public curated repo.

## Rule

The private repo is the development source of truth.

The public repo is a curated publication surface.

Do not develop normally in the public repo.

## Publication Steps

1. develop and commit in the private repo
2. review whether the public-facing docs and code are ready
3. run the curated export:

```powershell
.\scripts\publish_public_repo.ps1
```

4. inspect the export
5. publish intentionally:

```powershell
.\scripts\publish_public_repo.ps1 -Push
```

## Private-Only Paths

The publication workflow must exclude internal-only material such as:

- `docs/operating_system/`
- `agent-core/`
- `codex/rules/`
- `AGENTS.md`
- `.agents/`
- `.cursor/`
- `docs/superpowers/`
- `logs/`
- `sample/`

## Review Standard

Before publication, confirm:

- the public README stands alone
- public docs do not depend on private repo workflow docs
- no internal agent/tooling assets leaked into the export

## Related Verification

If publication-boundary or adapter files changed first, run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

before running the curated publish workflow.
