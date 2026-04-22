# Repo Governance

This document defines how the private FitCV repo is organized for humans and agents.

## Repo Roles

- Private repo:
  - full development source of truth
  - internal docs, workflows, specs, plans, and tooling are allowed
- Public repo:
  - curated product-facing mirror
  - receives only intentionally published code and docs

Normal development happens only in the private repo.

## Structure Model

The repo uses five distinct internal layers:

1. `docs/operating_system/`
- human-readable repo rules and workflows
- publication policy
- doc-system and planning rules
- internal tooling governance
- agent memory under `docs/operating_system/agent_memory/`

2. `agent-core/`
- shared agent-facing source material
- small principles
- structured policy intent
- adapter source files

3. `.agents/skills/`
- repo-local Codex skill discovery surface
- focused task playbooks

4. `repo_config/`
- repo/system configuration
- publication boundary configuration
- adapter generation mappings
- adoption-mode record, including the Mode B starter shared-surface sync review

5. adapter outputs
- `AGENTS.md`
- nested `AGENTS.md`
- `codex/rules/*.rules`
- sync and verification scripts under `scripts/`

The repo uses `codex/` as its active Codex generated/config root while
keeping ownership split by role:

- `AGENTS.md` for repo-wide Codex instructions
- `.agents/skills/` for canonical Codex skills
- `docs/operating_system/` for human governance
- `codex/` for generated Codex rules output

The repo also splits configuration ownership by purpose:

- `repo_config/`
  - repo/system configuration such as publication boundaries, adoption mode,
    and adapter generation mappings
- `config/`
  - runtime and workflow configuration used by the product and pipeline
- `docs/features/*/feature.source.yaml` and `docs/stages/*.source.yaml`
  - human-owned lifecycle sources for managed architecture metadata
- `docs/features/*/*.yaml`, `docs/features/*/lineage.generated.yaml`, and
  `docs/stages/*.yaml`
  - generated lifecycle outputs assembled from the source layer plus metadata

Managed Mode B target state:

- edit `docs/features/<feature_id>/feature.source.yaml` for human semantic changes
- edit `docs/stages/<stage_id>.source.yaml` for human stage-boundary changes
- keep repo-local feature IDs in lowercase underscore format unless a later
  naming migration is explicitly approved
- keep managed feature capabilities as structured entries with
  `<feature_id>.<kebab-suffix>` IDs
- treat generated feature contracts, generated stage contracts, and
  `lineage.generated.yaml` as outputs rather than source-of-truth files
- keep starter-owned shared repo-control surfaces reviewed against the adopted
  starter baseline and record that review in `repo_config/adoption-mode.yaml`
- run `python scripts/sync_architecture_docs.py` to refresh generated lifecycle
  outputs and `python scripts/validate_repo_contracts.py` to check the broader
  repo contract before calling the migration work complete

## Ownership Rules

### `docs/operating_system/`

Owns:

- repo operating rules
- workflow governance
- publication workflow
- tool adoption policy
- operational agent memory

Does not own:

- product behavior
- runtime code contracts
- task playbooks

`docs/operating_system/agent_memory/` stores compact operational memory for agents. It does not replace feature docs, specs, plans, or generated rules.

### `agent-core/`

Owns:

- shared agent-facing material that may be rendered into adapter-specific files

Does not own:

- the full human governance layer
- public product docs

### `.agents/skills/`

Owns:

- reusable execution workflows
- the canonical Codex skill discovery surface in phase 2

Does not own:

- publication policy
- repo-wide governance
- adapter syntax

Formal shape is governed by `docs/operating_system/skills-governance.md`.

### `repo_config/`

Owns:

- repo/system configuration
- publication boundary configuration
- adapter generation mappings
- adoption-mode state and starter shared-surface review records

Does not own:

- runtime workflow defaults
- feature or stage contracts
- generated outputs

## Private / Public Boundary

The following are private-only by default:

- `docs/operating_system/`
- `agent-core/`
- `codex/rules/`
- root and nested `AGENTS.md`
- `.agents/`
- `.cursor/`
- `docs/superpowers/`
- `logs/`
- `sample/`

The public repo must not depend on these files to understand or use the product.

## Current Phase

Phase 2 keeps `.agents/skills/` as the canonical skill source.

This avoids breaking current Codex skill discovery while the new `agent-core/` and adapter sync layer stabilizes.

Longer term, `agent-core/skills/` may become canonical, with `.agents/skills/` generated or synchronized from it.

## Mode B Shared-Surface Sync

When the repo is in `managed_architecture_metadata` mode and adopts newer
starter updates, review the starter-owned shared repo-control surfaces rather
than updating only product metadata.

That review should cover at least:

- `repo_config/*`
- `docs/operating_system/*`
- `.agents/skills/*`
- `agent-core/adapters/**/*`
- generated `AGENTS.md` and `codex/rules/*` after sync
- validation and sync scripts

Record the review in `repo_config/adoption-mode.yaml` under `starter_sync`
with:

- `starter_baseline_ref`
- `last_shared_surface_review_at`
- `reviewed_surface_classes`
- optional `divergences`

Intentional drift is allowed, but it should be explicit and reviewable.

Current accepted local drift:

- managed feature IDs remain underscore-based instead of starter kebab-case
  naming
- capability metadata is normalized around repo-local structured entries rather
  than requiring a second ID migration immediately after the Mode B rollout

## Adapter Workflow

When changing:

- `agent-core/adapters/*`
- `agent-core/policies/*`
- generated `AGENTS.md`
- generated `codex/rules/*.rules`

run:

```powershell
.\scripts\sync_agent_adapters.ps1
.\scripts\verify_agent_adapters.ps1
```

## Hook Workflow

The repo hook workflow is part of normal enforcement.

Installed local hooks should call the repo-contract validator in its hook-facing
subset mode:

```powershell
.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast
```

Use `scripts/sync_architecture_docs.py` separately when you need to regenerate
feature, stage, or discovery outputs before rerunning the validator.

The `--fast` flag is not a no-op quick check. It still runs the architecture
sync check path and skips only the extra validator-specific pytest pass.

CI is expected to run adapter verification and baseline checks on push and pull request events so drift and broken changes are caught before merge.

When CI or repo hooks expose a repeated or important failure mode, convert that lesson into one or more of:

- an entry in `docs/operating_system/agent_memory/`
- a stronger repo rule
- a script check
- a test
- an explicit follow-up plan if immediate hardening is not appropriate
