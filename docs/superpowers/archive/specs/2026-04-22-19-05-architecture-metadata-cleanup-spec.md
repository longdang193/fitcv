---
layer: change
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - docs/operating_system/project-adoption-migration-guide.md
  - docs/features/*/feature.source.yaml
  - docs/features/*/*.yaml
  - docs/generated/
  - repo_config/adoption-mode.yaml
related_features: []
related_stages: []
---

# Architecture Metadata Cleanup Spec

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Clean up the remaining metadata-system drift after the direct-evidence
phases by aligning function-level capability support, stage participation
expectations, generated contract formatting, and generated discovery shape with
the newer starter-style Mode B guidance.  
Reasoning: The evidence backfill phases closed the highest-value capability
gaps, but the repo still has structural drift in the metadata toolchain and
generated outputs. The current system can prove capability ownership at the file
level, but it does not yet support function-level capability markers, it treats
missing `stage_participation` as a silent empty list, it emits noisy generated
string formatting in some contracts such as `docs/features/cv_system/cv_system.yaml`,
and it still uses the older `docs/generated/*` summary-index family rather than
the newer starter-aligned generated-discovery target.  
Invariants:

- The private repo remains the source of truth.
- `feature.source.yaml` remains the human-owned semantic source.
- Generated contracts and lineage remain generator-owned outputs.
- Validation should become stricter only where the generator and source layer
  can satisfy the stricter contract.
- Cleanup should prefer consistent machine-readable contracts over preserving
  legacy formatting quirks.
- Generated discovery migration should be intentional and validator-backed,
  not a partial delete/add mismatch.

Dependencies:

- `docs/operating_system/feature-lifecycle.md`
- `repo_config/adoption-mode.yaml`
- latest local `project-OS-starter` adoption and doc-system guidance
- current evidence-oriented lineage generator and validator behavior

Affected stages:

- none

Affected features:

- none directly; this is repo-method cleanup with downstream feature-output impact

Primary lens: `operating_system`

Affected docs:

- feature_source:
  - `docs/features/*/feature.source.yaml`
- feature_yaml:
  - `docs/features/*/<feature_id>.yaml`
- feature_lineage:
  - `docs/features/*/lineage.generated.yaml`
- feature_history: `none unless migration notes are needed`
- stage_source: `none`
- stage_contract: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/project-adoption-migration-guide.md`
- operating_system_docs:
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/project-adoption-migration-guide.md`
- readme: `none`
- generated:
  - `docs/generated/*`

Generated refresh required: `yes`  
Capability IDs: `none`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Current Drift Snapshot

Current metadata-system drift falls into four buckets:

1. Function-level `@capability` markers are not currently parsed or validated.
   The repo only harvests file-level Python `@meta`, test-level `@proves`, and
   the bounded template metadata added in Phase 13.
2. Most feature sources still omit `stage_participation`, so generated
   contracts silently normalize the field to `[]` even when the feature clearly
   spans one or more stages.
3. Generated contract formatting is inconsistent for some multiline
   `summary`/`statement` fields, notably `docs/features/cv_system/cv_system.yaml`,
   which currently emits quoted multiline strings with trailing blank-line
   artifacts.
4. The repo still emits the older generated summary-index family under
   `docs/generated/` rather than the newer starter-style generated-discovery
   contract.

## Goal

Create a cleanup implementation plan that upgrades the architecture metadata
toolchain and source requirements so the repo can:

1. support truthful function-level capability evidence
2. stop silently treating missing stage ownership as acceptable steady-state
3. emit normalized generated contract string formatting
4. converge generated discovery to one canonical starter-aligned shape

## Non-Goals

This cleanup phase does not:

- redesign product behavior
- reopen already-complete feature capability backfill work
- require every feature source to be rewritten in one uncontrolled batch
- force immediate strict validation before generators and source surfaces are
  able to comply
- preserve both old and new `docs/generated/*` families as co-equal steady-state
  outputs

## Proposed Shape

### 1. Function-Level Capability Evidence Support

The implementation plan should decide and document:

- the exact syntax for function-level capability markers in Python
- how `scripts/sync_architecture_docs.py` harvests those markers
- whether generated lineage records function-level evidence separately or
  promotes it into the existing capability `code` list
- how `scripts/validate_adoption_shape.py` validates marker correctness and
  rejects malformed or unknown capability IDs

Preferred direction:

- keep file-level `@meta` as the broad owner surface
- add bounded function-level `@capability` support for finer-grained direct
  evidence without making it mandatory everywhere

### 2. Stage Participation Enforcement Upgrade

The implementation plan should define:

- when `stage_participation` is required versus optional
- whether `missing` and explicit `[]` are both allowed during migration
- which existing features must be backfilled first to satisfy any stricter rule
- what validator message should distinguish “missing because not migrated yet”
  from “empty but intentionally stage-agnostic”

Preferred direction:

- move away from silent normalization of missing `stage_participation` to `[]`
- require explicit stage ownership for stage-aware features in steady-state
  Mode B

### 3. Generated Contract String Normalization

The implementation plan should define a canonical emitter style for:

- feature `summary`
- capability `statement`
- invariant `statement`

Preferred direction:

- trim trailing whitespace and blank lines before YAML emission
- avoid noisy quoted multiline formatting when the logical value is a single
  sentence or paragraph
- add validator or generator-level tests so formatting regressions are caught
  automatically

### 4. Generated Discovery Migration

The implementation plan should choose one canonical `docs/generated/*` target
and migrate the repo fully to it.

This must include:

- generator changes
- validator changes
- repo-config or operating-system doc updates
- deletion of superseded generated outputs only after the new contract is in
  place and check-mode clean

Preferred direction:

- align with the newer starter-generated discovery target rather than keeping
  the older summary-index family indefinitely

## Acceptance Criteria

Cleanup is ready for implementation when:

1. the implementation plan names the exact function-level marker syntax and
   harvesting behavior
2. the plan defines the validator contract for `stage_participation`
3. the plan defines the canonical formatting contract for generated
   `summary`/`statement` fields
4. the plan defines the target generated-discovery family and the retirement
   path for superseded outputs
5. migration ordering is explicit so the repo does not land in a half-migrated
   validation state
6. validation and generator test coverage needed for the cleanup is identified

## Risks And Guardrails

- Risk: function-level capability support duplicates or conflicts with file-level
  ownership. Guardrail: keep file-level ownership authoritative and treat
  function-level markers as finer direct evidence, not a replacement.
- Risk: strict `stage_participation` validation creates a repo-wide failure
  before source backfill is ready. Guardrail: phase enforcement with a bounded
  migration list or explicit validator mode.
- Risk: string normalization rewrites large numbers of generated contracts in an
  uncontrolled way. Guardrail: define and test one deterministic emission rule
  first.
- Risk: generated-discovery migration deletes the old family before the new
  family and validator are stable. Guardrail: require sync/check parity and
  validator backing before removing superseded outputs.

## Validation Plan

Minimum validation for the eventual cleanup implementation:

- `python scripts/sync_architecture_docs.py`
- `python scripts/sync_architecture_docs.py --check`
- `python scripts/validate_adoption_shape.py`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_validate_adoption_shape.py`
- any new generator/formatter tests added for function-level marker parsing and
  string-normalization behavior
- `git diff --check`

## Rollback Plan

If the cleanup implementation over-tightens the repo contract:

1. revert the stricter validator paths
2. revert generator output contract changes
3. restore the prior generated discovery family only if the replacement target
   is not yet stable
4. rerun sync/check to return to the last valid metadata baseline

## Execution Notes

Status: `not_started`

Next step is to turn this into a cleanup-phase implementation plan before any
toolchain or source-wide mutation happens.
