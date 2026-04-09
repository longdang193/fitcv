---
feature_type: add
feature_name: none
status: building
summary: "Extract the reusable private repo operating-system, skills, adapter-source, and publication workflow layers into the new `project-OS-starter` repository without breaking `JOB-PROJECT`."
---

# Project-OS-Starter Extraction Plan

## Objective

Create a reusable private `project-OS-starter` repository that preserves the canonical repo-operating-system layers from `JOB-PROJECT` so future private projects can start with:

- a human-readable operating-system doc layer
- a canonical Codex skill surface
- adapter-source templates for generated instruction files
- sync and verification scripts for adapter outputs
- a curated private-to-public publication workflow

The starter repo should be self-contained, generic enough for future projects, and validated without making `JOB-PROJECT` depend on it during the first extraction pass.

## Scope

This plan covers private repo infrastructure only.

It includes:

- `docs/operating_system/`
- `.agents/skills/`
- `agent-core/`
- adapter sync and verification scripts
- curated public-mirror publication workflow
- starter-repo README and bootstrap guidance

It does not include:

- `src/`
- runtime product features
- product tests
- feature YAMLs for FitCV behavior
- stage contracts or generated discovery tied to FitCV runtime behavior

## Source-Of-Truth Alignment

This extraction must preserve the current ownership model:

- repo workflow and governance remain owned by `docs/operating_system/`
- reusable task playbooks remain owned by `.agents/skills/`
- adapter source templates remain owned by `agent-core/`
- generated `AGENTS.md` and `codex/rules/*.rules` remain generated outputs

Do not make generated adapter outputs the canonical layer in the starter repo.

## Current Canonical Inputs To Extract

Copy these source layers into `project-OS-starter` first:

- `docs/operating_system/`
- `.agents/skills/`
- `agent-core/adapters/codex/`
- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`
- `scripts/publish_public_repo.ps1`

Treat these as generated or downstream and do not use them as canonical extraction sources:

- `AGENTS.md`
- nested `AGENTS.md`
- `codex/rules/*.rules`

## Constraints And Invariants

- `JOB-PROJECT` remains the source of truth until the starter repo has been validated in isolation.
- The first extraction pass is copy-first, not move-first.
- The starter repo must not depend on FitCV runtime code to explain its operating model.
- Public/private boundary rules must remain explicit and preserved.
- Generated adapter outputs must be reproducible from files owned by the starter repo.

## Phase 1: Seed The Starter Repo

Create the initial `project-OS-starter` structure by copying the reusable source layers from `JOB-PROJECT`.

Recommended starting structure:

```text
project-OS-starter/
  .agents/skills/
  agent-core/adapters/codex/
  docs/operating_system/
  scripts/
  README.md
```

Actions:

- copy the canonical source folders and scripts into the starter repo
- preserve directory structure where it already reflects clear ownership
- avoid moving any source files out of `JOB-PROJECT` during this phase

Output:

- a starter repo that contains the same source-layer concepts as `JOB-PROJECT`

## Phase 2: Classify Reusable Vs FitCV-Specific Content

Audit the copied files and classify them into:

- reusable as-is
- reusable after renaming or parameterization
- FitCV-specific example content
- not suitable for the starter repo

Expected attention points:

- `FitCV` references in docs and templates
- hardcoded repo paths such as `src/fitcv/` and `src/fitcv_cp/`
- publication allowlists that assume FitCV product structure
- rule or template text that references current project naming

Actions:

- keep generic governance and workflow concepts
- convert app-specific paths into starter-friendly placeholders or configuration
- move any still-useful project-specific examples under an explicit example section if needed
- remove content that would mislead future projects into inheriting FitCV-only structure

Output:

- a clean boundary between reusable operating-system assets and FitCV-specific implementation details

## Phase 3: Generalize Adapter Generation

Refactor the adapter scripts so the starter repo can generate adapter outputs for a new project without assuming FitCV layout.

Target files:

- `scripts/sync_agent_adapters.ps1`
- `scripts/verify_agent_adapters.ps1`

Required changes:

- remove or parameterize hardcoded output destinations such as `src/fitcv/AGENTS.md` and `src/fitcv_cp/AGENTS.md`
- define a small configuration surface for generated adapter mappings
- keep root `AGENTS.md` generation simple and explicit
- ensure verification reads the same mapping source as sync

Recommended approach:

- add a small config file that defines adapter source-to-destination mappings
- keep the config human-readable and private-repo oriented
- document the minimum required mapping for a new project

Output:

- a starter-owned adapter generation workflow that can be reused by new repos with minimal edits

## Phase 4: Generalize The Publication Workflow

Refactor the curated publish flow so the starter repo provides a reusable private-to-public mirror pattern rather than a FitCV-specific export list.

Target file:

- `scripts/publish_public_repo.ps1`

Required changes:

- separate generic boundary rules from FitCV-specific public allowlists
- parameterize or externalize `publicPaths`, `forbiddenPaths`, and `requiredPaths`
- preserve explicit exclusion of private-only operating layers

The starter workflow must continue to exclude at least:

- `.agents/`
- `agent-core/`
- `docs/operating_system/`
- `codex/rules/`
- generated `AGENTS.md`
- other private tool or workspace directories

Output:

- a reusable curated publication script with a safe allowlist-first model

## Phase 5: Write Starter-Native Documentation

Add starter-specific documentation so future projects can adopt the system intentionally.

Required docs:

- `README.md`

The README should explain:

- what the starter repo owns
- which layers are canonical vs generated
- how to bootstrap a new private repo from the starter
- how to regenerate `AGENTS.md` and `codex/rules/*.rules`
- how to configure the public-mirror publication workflow
- what must remain private by default

Optional follow-up docs if needed:

- `docs/operating_system/starter-bootstrap.md`
- `docs/operating_system/adapter-config.md`

Output:

- a self-explanatory starter repo that does not require prior knowledge of `JOB-PROJECT`

## Phase 6: Validate The Starter Repo In Isolation

Before changing `JOB-PROJECT`, prove the starter repo works on its own.

Validation steps:

1. run the starter repo sync script
2. run the starter repo verification script
3. confirm generated adapter files are reproducible from starter-owned source files only
4. confirm the starter repo docs do not point back to `JOB-PROJECT`
5. confirm the publication workflow still excludes the private operating-system layers

Output:

- evidence that the starter repo is independently coherent

## Phase 7: Bootstrap A Trial Project

Create one disposable private test repo from `project-OS-starter` and perform a minimal adoption pass.

Actions:

- rename project-specific placeholders
- configure adapter mappings for the test repo structure
- run sync and verify
- optionally dry-run the curated public export

Success criteria:

- the trial repo can generate its own adapter outputs
- the docs still make sense after renaming
- no file depends on `JOB-PROJECT` remaining in place

Output:

- proof that the starter repo is actually reusable, not just internally tidy

## Phase 8: Decide Back-Porting Strategy For `JOB-PROJECT`

Only after starter validation should `JOB-PROJECT` be updated to align with the generalized structure.

Possible follow-up work:

- adopt the generalized adapter config model in `JOB-PROJECT`
- align publication config with the starter workflow
- reduce duplicated logic if the starter repo becomes the preferred template source

Do not block starter extraction on back-porting.

Output:

- an optional second-phase alignment path instead of a coupled migration

## Risks

### Risk 1: Overfitting The Starter Repo To FitCV

If app-specific paths and names stay embedded in scripts or templates, future projects will inherit misleading structure.

Mitigation:

- explicitly audit names, paths, and references during Phase 2
- prefer configuration over hardcoded product paths

### Risk 2: Mistaking Generated Outputs For Canonical Sources

If `AGENTS.md` or `codex/rules/*.rules` are copied as the source of truth, the starter repo will drift and become harder to maintain.

Mitigation:

- keep `agent-core/` and scripts as the source layer
- regenerate adapter outputs from starter-owned templates

### Risk 3: Breaking `JOB-PROJECT` During Extraction

If files are moved too early, the current repo could lose its known-good workflow before the starter is proven.

Mitigation:

- use copy-first extraction
- validate the starter independently before any source repo restructuring

### Risk 4: Unsafe Public Export Defaults

If the starter repo weakens the allowlist-first publish model, future public mirrors may leak private process assets.

Mitigation:

- keep the current boundary checks
- externalize configuration without loosening exclusions

## Verification

Before considering the extraction successful:

1. confirm `project-OS-starter` contains only reusable private operating-system assets
2. confirm the starter repo has no unresolved `FitCV` or `JOB-PROJECT` dependencies except intentional examples
3. run starter `sync_agent_adapters.ps1` successfully
4. run starter `verify_agent_adapters.ps1` successfully
5. confirm generated adapter outputs are reproducible
6. confirm the starter publication workflow excludes private-only layers
7. validate one disposable trial project bootstrapped from the starter repo

## Completion Criteria

The extraction is complete when:

- `project-OS-starter` is a coherent private starter repo
- canonical ownership remains with docs, skills, and adapter-source layers
- adapter outputs are generated and verified rather than hand-maintained
- the publication workflow remains curated and boundary-safe
- a fresh private project can adopt the starter repo with only project-specific configuration changes

## Exact Doc Targets

This plan affects or references these source-of-truth docs:

- `docs/operating_system/repo-governance.md`
- `docs/operating_system/publication-workflow.md`
- `docs/operating_system/skills-governance.md`
- `docs/operating_system/doc-system-lifecycle.md`
- `README.md`

There is no affected feature YAML for this work because it is a cross-cutting repo-operating-system extraction rather than a managed product feature change.
