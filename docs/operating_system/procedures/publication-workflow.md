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

## Private-Only Paths

The publication workflow must exclude internal-only material such as:

- `docs/adoption_guide.md`
- `docs/operating_system/`
- `docs/operating_system/agent_memory/`
- source-only generation machinery and private build inputs
- `.codex/`
- `AGENTS.md`
- `.agents/`
- `.cursor/`
- `docs/superpowers/`
- `logs/`
- `sample/`

Starter adoption/bootstrap docs are private-only by default. They explain how
to adapt the private starter repo, not how to use the public product-facing
repo.

That means:

- do not publish `docs/adoption_guide.md`
- do not publish starter migration runbooks or bootstrap checklists by default
- do not publish "how to customize the private starter repo" guidance unless it
  has been intentionally rewritten as public-facing documentation

This boundary does **not** mean every cross-cutting doc under `docs/` is
private. Public-facing setup, usage, architecture, or API docs may still be
published when they are written for product users or contributors rather than
private starter adopters.

For concrete rewrite guidance before publishing cross-cutting docs such as
`README.md`, `docs/setup.md`, `docs/configuration.md`, `docs/usage.md`,
`docs/pipeline.md`, or `docs/architecture.md`, use
[Public-Safe Doc Rewrite Guide](public-safe-doc-rewrite-guide.md).

When reviewing a candidate file, choose one treatment explicitly:

- keep as-is
- keep and sanitize
- omit entirely

Prefer "keep and sanitize" when the file's visible structure helps the public
mirror remain reproducible, navigable, or trustworthy and the sensitive parts
can be safely removed.

Do not over-trim files whose headings, schema, artifact slots, or metadata keys
help a downstream reader understand what exists upstream.

Lifecycle documentation now follows a stricter public-safe boundary:

- publish generated current-state feature contracts when they help explain the
  product-facing system
- publish generated stage contracts when they help explain the workflow stages
- do not publish `docs/features/*/feature.source.yaml`
- do not publish `docs/stages/*.source.yaml`
- do not publish feature-local `lineage.generated.yaml`
- do not publish feature `history.md` by default, because it may contain
  partially generated internal plan lineage
- do not publish aggregate `docs/generated/*` outputs unless they are
  explicitly allowlisted and reviewed as public-safe

In this repo, `.codex/` is the private Codex config/generated root.
It contains generated rules output and optional repo-local Codex subagent
config, but it is still not the canonical home for Codex skills or agent
memory.

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
