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

## Starter-Kit Generation vs Public Publication

`project-OS-starter-kit` is not public-mirror publication output. It is a
separate generated starter derived from `project-OS-starter`.

Rules:

- build or refresh the starter kit only from `project-OS-starter`
- do not edit generated `project-OS-starter-kit` output directly
- starter-kit generation may ship private operating-system and planning
  surfaces on purpose when they are part of the clone-ready starter contract
- public publication must still exclude those private-only surfaces unless they
  are intentionally rewritten for public use
- adapter regeneration stays source-only even when the starter kit ships final
  `AGENTS.md`, `GEMINI.md`, and `CLAUDE.md`

Treat these as separate workflows:

- public mirror workflow -> curated product-facing export
- starter-kit workflow -> clone-ready consume-only starter export

For exact maintainer rebuild and validation steps, use
[Starter-Kit Workflow](starter-kit-workflow.md).

## Publication Boundary Reference

Boundary rules and deny policy are authoritative in:

- [Public Repo Publication Policy](../publication/public-repo-publication-policy.md)

Doc sanitization and keep/sanitize/omit patterns are defined in:

- [Public-Safe Doc Rewrite Guide](../publication/public-safe-doc-rewrite-guide.md)

When reviewing candidate files, classify each as:

- keep as-is
- keep and sanitize
- omit entirely

Do not duplicate boundary rule lists in this procedure doc; update policy doc when boundary rules change.

In this repo, `.codex/` is private Codex config/generated root and stays excluded from public export.

## Review Standard

Before publication, confirm:

- the public README stands alone
- public docs do not depend on private repo workflow docs
- no internal agent/tooling assets leaked into the export
- no source-layer lifecycle authoring files leaked into the export
- no feature history files leaked into the export unless intentionally curated
- generated lifecycle or discovery docs are published only when they are
  explicitly public-safe
- candidate files were explicitly classified as keep, sanitize, or omit
- sanitized files remain structurally valid and understandable
- structural visibility needed for reproducibility was not removed by reflex

## Related Verification

If publication-boundary or adapter files changed first, run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

before running the curated publish workflow.

Dry-run publication checks should work without a configured public remote. The remote is only required when `-Push` is requested.

If repo-level config ownership or publication config under `repo_config/` changes, run:

```powershell
.\.venv\Scripts\python.exe .\scripts\validate_repo_config.py
```

before publishing so publication boundaries and adapter mapping inputs are still
internally consistent.

Starter-kit rebuilds use a different workflow and different verification target.
Do not substitute public-mirror publication checks for starter-kit validation.
