---
layer: change
artifact_type: spec
status: proposed
parent_workstream: none
targets:
  - scripts/sync_architecture_docs.py
  - scripts/validate_adoption_shape.py
  - tests/test_sync_architecture_docs.py
  - tests/test_validate_adoption_shape.py
  - docs/operating_system/feature-lifecycle.md
  - docs/operating_system/project-adoption-migration-guide.md
  - docs/features/*/lineage.generated.yaml
  - docs/superpowers/plans/*.md
related_features: []
related_stages: []
---

# Lineage Timeline Contract Patch Spec

## Triage

Layer: `change`  
Feature type: `MODIFY`  
Summary: Patch this repo's older `lineage.generated.yaml` generator contract so feature-local lineage matches the newer starter-aligned evidence schema, especially the richer `timeline` field.  
Reasoning: The repo already migrated away from older summary-style top-level lineage keys, but the current lineage generator still emits the superseded `timeline` contract:

```yaml
timeline:
  - kind: spec
    path: docs/superpowers/specs/...
  - kind: plan
    path: docs/superpowers/plans/...
```

The latest local `project-OS-starter` baseline at commit `5218402c70c410fd7c1f1c9017379268ae89a296` (committed `2026-04-22T16:33:38+02:00`) now documents that shape as migration debt, not the current managed target. The starter's current target is a richer completed-change record list sourced from completed implementation-plan metadata. This repo therefore still has a generator-contract drift even after the earlier lineage and cleanup passes.  
Invariants:

- `feature.source.yaml` remains the human-owned feature source.
- `lineage.generated.yaml` remains generated-only.
- the top-level lineage shape stays evidence-oriented:
  - `feature_id`
  - `source`
  - `invariants`
  - `capabilities`
  - `timeline`
- this phase patches the lineage contract; it does not manually edit generated lineage files.
- migration must be truthful: if completed-plan metadata is absent, the generator should prefer `timeline: []` over inventing fake richer history records.

Dependencies:

- latest local `project-OS-starter` guidance from:
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/doc-system-lifecycle.md`
  - `docs/operating_system/project-adoption-migration-guide.md`
- starter implementation reference:
  - `tools/docs/generate_architecture_metadata.py`
  - `scripts/validate_adoption_shape.py`
  - `tests/test_architecture_metadata_generation.py`
- current local generator and validator:
  - `scripts/sync_architecture_docs.py`
  - `scripts/validate_adoption_shape.py`

Affected stages:

- none

Affected features:

- all managed features with generated lineage under `docs/features/*/lineage.generated.yaml`

Primary lens: `cross-cutting`

Affected docs:

- feature_source: `none`
- feature_yaml: `none`
- feature_lineage:
  - `docs/features/*/lineage.generated.yaml`
- feature_history: `none in this phase`
- stage_source: `none`
- stage_contract: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - `docs/operating_system/feature-lifecycle.md`
  - `docs/operating_system/project-adoption-migration-guide.md`
- readme: `none`
- generated:
  - `docs/features/*/lineage.generated.yaml`

Generated refresh required: `yes`  
Capability IDs: `none`  
Invariant IDs: `none`  
Spec needed: `yes`  
Plan needed: `yes`

## Starter Reference

The latest local starter now states the following:

- `docs/operating_system/feature-lifecycle.md` says `timeline` is a list of richer completed-change records, not just spec/plan refs.
- `docs/operating_system/project-adoption-migration-guide.md` explicitly says the old `{kind, path}` timeline shape should be replaced once the repo migrates to the current managed target.
- `tools/docs/generate_architecture_metadata.py` builds timeline entries with fields such as:
  - `completed_at`
  - `source_plan`
  - `change_id`
  - `summary`
  - `capabilities`
  - `verification`
  - `outcome`

Concrete starter target:

```yaml
timeline:
  - completed_at: 2026-04-18T10:30:00+02:00
    source_plan: docs/superpowers/plans/2026-04-18-sample-plan.md
    change_id: 2026-04-18-sample-change
    summary: Add sample capability metadata.
    capabilities:
      - sample-feature.submit-job
    verification:
      - pytest tests/test_sample_script.py
    outcome: Sample capability now has explicit lineage metadata.
```

## Current Drift In This Repo

Current repo-local drift is concrete:

1. `scripts/sync_architecture_docs.py` still builds lineage `timeline` from all linked specs and plans as shallow refs only:

```python
timeline = [{"kind": "spec", "path": path} for path in refs.get("spec", [])] + [
    {"kind": "plan", "path": path} for path in refs.get("plan", [])
]
```

2. Current generated lineage files, for example `docs/features/cv_system/lineage.generated.yaml`, still use that older timeline contract.
3. `scripts/validate_adoption_shape.py` currently checks only that `timeline` exists and is a list. It does not reject legacy `{kind, path}` timeline entries.
4. This repo's current plan artifacts are mixed:
   - many older plans do not carry newer completed-plan metadata such as `completed_at`, `change_id`, `verification`, and `outcome`
   - therefore a truthful migration cannot assume that every historical plan can immediately produce a rich timeline record

## Goal

Patch the repo-local lineage generator contract so `docs/features/*/lineage.generated.yaml` no longer emits the superseded `{kind, path}` timeline shape and instead converges toward the newer starter-aligned completed-change record contract.

## Non-Goals

This phase does not:

- fully port the starter `tools/docs/generate_architecture_metadata.py`
- require a repo-wide historical backfill of all legacy plans in one batch
- redesign capability evidence semantics outside the timeline contract
- require generated feature-history rollout in the same phase
- require `revision`, `latest_change_id`, or `last_updated_at` in generated feature contracts unless the implementation deliberately reuses the same metadata source later

## Proposed Patch Shape

### 1. Replace The Legacy Timeline Contract

The local generator should stop emitting timeline entries shaped only as:

```yaml
- kind: spec
  path: ...
```

and

```yaml
- kind: plan
  path: ...
```

Those shapes should be treated as superseded generator output.

### 2. Use Completed-Plan Metadata As The Only Rich Timeline Source

The new generator path should build lineage timeline entries only from plan artifacts that truthfully expose completed-change metadata.

Preferred minimum source fields:

- plan status indicating completion
- `completed_at`
- `change_id`
- affected capability list
- `verification`
- outcome summary

Preferred generated entry shape:

- `completed_at`
- `source_plan`
- `change_id`
- `summary`
- `capabilities`
- `verification`
- `outcome`

### 3. Keep Migration Truthful When Historical Metadata Is Missing

Because many existing local plans do not yet expose the richer starter-style completed metadata, the patch should be migration-safe:

- if no valid completed-plan metadata exists for a feature, generate `timeline: []`
- do not preserve the old `{kind, path}` entries as fallback
- do not synthesize fake timestamps, change IDs, or outcomes from filenames alone

This keeps the lineage contract honest while still moving the repo off the older generator shape.

### 4. Extend Validation

The repo-local validator should be strengthened so that:

- `timeline` must still be a list
- legacy `{kind, path}` timeline entries are rejected
- when timeline entries exist, they must use the richer completed-change shape
- the validation message should clearly distinguish:
  - `timeline: []` because richer source metadata has not been backfilled yet
  - invalid legacy timeline entries from the old generator contract

### 5. Add Regression Coverage

Tests should cover at least:

- generator emits `timeline: []` when no valid completed-plan metadata exists
- generator emits richer completed-change timeline entries when valid plan metadata exists
- validator rejects legacy `{kind, path}` timeline entries
- validator accepts empty timeline lists during migration

## Open Design Question

The implementation plan should decide whether this phase also introduces a small canonical completed-plan metadata shape for this repo's future plans, for example:

- `change_id`
- `completed_at`
- `verification`
- `outcome`
- `affects.capabilities`

Preferred direction:

- yes, define the minimal frontmatter needed for future rich timeline generation
- no, do not backfill every historical plan in this patch

## Acceptance Criteria

This patch is complete when:

1. `scripts/sync_architecture_docs.py` no longer emits legacy `{kind, path}` timeline entries.
2. `scripts/validate_adoption_shape.py` rejects legacy timeline entries.
3. generated `docs/features/*/lineage.generated.yaml` files use either:
   - `timeline: []`, or
   - the richer completed-change entry shape
4. the patch does not fabricate richer timeline records from insufficient metadata.
5. focused regression tests cover both the empty-timeline migration case and the richer-timeline success case.
6. repo-local operating-system docs mention that the old `{kind, path}` timeline shape is no longer the current contract.

## Risks And Guardrails

- Risk: trying to emulate the full starter generator in one pass broadens scope too far.
  Guardrail: keep this patch focused on lineage timeline contract and validator alignment.
- Risk: validation becomes too strict before this repo has richer completed-plan metadata.
  Guardrail: allow `timeline: []` as the truthful migration-safe state.
- Risk: generated files lose useful historical links when old spec/plan refs disappear.
  Guardrail: record that this is intentional contract cleanup and handle historical metadata backfill in a later phase if desired.
- Risk: agents treat `timeline: []` as a bug even when metadata is absent.
  Guardrail: document that empty timeline is preferred over fabricated richer entries during migration.

## Validation Plan

Minimum validation for the eventual implementation:

- `python scripts/sync_architecture_docs.py`
- `python scripts/sync_architecture_docs.py --check`
- `python scripts/validate_adoption_shape.py`
- `.\\.venv\\Scripts\\python.exe -m pytest tests/test_sync_architecture_docs.py tests/test_validate_adoption_shape.py`
- `git diff --check`

## Rollback Plan

If the timeline patch proves too strict or too lossy:

1. revert the new timeline-entry validation rules
2. revert the generator timeline contract changes
3. keep the starter-guidance doc clarifications if they remain truthful
4. revisit whether this repo needs a separate completed-plan metadata phase before reattempting the lineage timeline migration

## Execution Notes

Status: `not_started`

Next step is to turn this into a bounded implementation plan that:

- defines the minimal completed-plan metadata contract for future timeline entries
- keeps historical migration safe through `timeline: []`
- updates generator, validator, tests, and docs together
