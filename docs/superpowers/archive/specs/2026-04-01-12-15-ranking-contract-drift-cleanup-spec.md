---
feature_type: modify
feature_name: settings_system
status: draft
summary: "Clean up ranking contract drift by versioning the changed artifact shape, aligning ranking settings copy with runtime semantics, and correcting stale ranking documentation."
invariants:
  - "The six-feature ranking runtime contract remains `ai_score`, `must_have_match`, `vector_similarity`, `title_relevance`, `seniority_fit`, and `preference_fit`."
  - "A supported ranking feature becomes non-contributing only through an explicit configured weight of 0.0."
  - "Ranking artifact consumers must be able to distinguish incompatible artifact shapes by schema version."
  - "Admin-facing ranking labels and descriptions must describe the actual runtime feature semantics."
  - "Cross-cutting ranking documentation must use the current runtime field names."
---

# Ranking Contract Drift Cleanup Spec

## Affected Feature Contracts

- [docs/features/settings_system/settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/settings_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)

## Stage Contracts

- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)

## Triage

Feature type: MODIFY  
Summary: Clean up post-rollout ranking drift by making the changed ranking artifact shape version-detectable, aligning admin settings copy with six-feature runtime semantics, and correcting stale pipeline terminology.  
Reasoning: The six-feature ranking rollout corrected runtime scoring, but a few contract surfaces still drift from the real behavior. The ranking artifact shape changed without a schema-version bump, two admin settings descriptions still describe older meanings, and one cross-cutting pipeline doc still uses an outdated feature name. This is a modification of existing settings and inspection features centered on the ranking stage.  
Invariants:
- The six-feature runtime scoring contract is already correct and should not be redefined in this cleanup.
- Explicit zero-weight semantics remain valid and visible.
- Artifact compatibility signaling must be truthful for newly produced runs.
- Admin copy must match the feature computations implemented in code.
- Historical runs remain readable without retroactive migration.
Dependencies:
- `settings_system`
- `inspection_debugging`
- `ranking` stage contract
- ranking artifact export path in [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py)
- ranking settings schema in [src/fitcv_cp/settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/settings_schema.py)
Affected stages:
- `ranking`
Affected features:
- `settings_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
- feature_yaml: [docs/features/settings_system/settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/settings_system.yaml)
- feature_history: [docs/features/settings_system/history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/history.md)
- feature_docs:
  - none
- cross_cutting_docs:
  - [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- readme: none
- generated:
  - none
Generated refresh required: no  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Problem Statement

The six-feature ranking rollout fixed the underlying scoring behavior, but three smaller drifts remain:

1. The ranking stage artifact now emits a different decision-summary shape, but the artifact still reports `schema_version: "stage_transition_artifacts_v2"` in [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py). Consumers cannot safely tell the old ranking block from the new one.
2. The admin settings registry still describes `title_relevance` and `preference_fit` using older language that no longer matches runtime computation in [src/fitcv_cp/settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/settings_schema.py).
3. The cross-cutting pipeline explainer still uses the obsolete term `must_have_skill_match` in [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md), which no longer matches code, tests, or ranking artifacts.

This creates avoidable confusion for operators, reviewers, and any downstream consumer of exported ranking artifacts.

## Goals

- Make the ranking artifact shape change explicit and machine-detectable.
- Remove stale ranking terminology from admin-facing settings text.
- Align cross-cutting ranking docs with current runtime field names.
- Keep the runtime six-feature ranking implementation unchanged.

## Non-Goals

- Reworking ranking math or feature composition again.
- Introducing a compatibility alias layer for both old and new artifact keys unless implementation discovers an external dependency that requires it.
- Migrating or rewriting historical ranking artifact files.

## Options Considered

### Option 1: Copy-Only Cleanup

Update settings descriptions and stale docs, but leave artifact schema version unchanged.

Pros:
- smallest code change
- no artifact version transition

Cons:
- leaves the most important consumer-facing drift unresolved
- forces clients to infer shape from key presence instead of schema version

### Option 2: Contract Cleanup With Version Bump

Bump the stage-transition artifact schema version for the changed ranking block, update settings copy, and fix stale docs.

Pros:
- truthful compatibility signaling
- low implementation risk
- keeps the current runtime contract intact

Cons:
- requires tests and any artifact readers to accept the new version

### Option 3: Transitional Dual-Key Compatibility

Emit both old and new ranking artifact keys for a temporary period, while also updating copy and docs.

Pros:
- safest if an unknown external consumer still expects the old keys

Cons:
- extends ambiguity
- increases maintenance and cleanup debt
- weakens the benefit of the new explicit contract

## Decision

Choose Option 2.

The ranking artifact already changed in a meaningful way. The cleanest follow-up is to version that change explicitly, then align the supporting settings copy and docs around the already-correct runtime semantics.

## Proposed Changes

### 1. Bump Stage-Transition Artifact Schema Version

For newly produced run artifacts, bump the top-level stage-transition artifact version from:

```json
{
  "schema_version": "stage_transition_artifacts_v2"
}
```

to:

```json
{
  "schema_version": "stage_transition_artifacts_v3"
}
```

This bump reflects the ranking-block contract change introduced by the six-feature rollout, including:

- replacing partial `active_ranking_weights`
- recording `configured_ranking_weights`
- recording `configured_missing_value_defaults`
- recording `zero_weight_features`
- recording `contributing_features`

### 2. Keep the Ranking Block Shape As-Is

This cleanup should not redesign the ranking block again. The current six-feature fields remain the intended shape for new artifacts.

The change here is to make that shape versioned and explicit, not to rename it again.

### 3. Align Admin Settings Copy With Runtime Semantics

Update the ranking settings registry in [src/fitcv_cp/settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/settings_schema.py) so the UI text matches actual computation:

- `title_relevance` should describe similarity between the job title and the candidate target role.
- `preference_fit` should describe candidate preference alignment such as domain and location type, not nice-to-have skills.

These changes are wording-only and should not alter keys, defaults, validation, or saved-setting compatibility.

### 4. Correct Stale Cross-Cutting Ranking Terminology

Update [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md) so the ranking formula and surrounding explanation use:

- `must_have_match`
- current six-feature terminology

This document should stay aligned with the runtime formula and ranking artifact fields used in the codebase.

### 5. Refresh Feature and Stage Contracts

Update the current-state docs to reflect the cleanup:

- [docs/features/settings_system/settings_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/settings_system/settings_system.yaml)
- [docs/features/inspection_debugging/inspection_debugging.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/inspection_debugging/inspection_debugging.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/stages/ranking.yaml)

Expected contract updates:

- settings documentation should mention that ranking labels describe target-role and preference alignment semantics accurately
- inspection debugging should mention the artifact schema version transition if the feature contract tracks versioned downloads
- ranking stage docs should reflect the new artifact schema version for newly triggered runs

## Expected Runtime Semantics After Cleanup

The runtime scoring behavior remains:

```text
final_score =
weight(ai_score) * ai_score
+ weight(must_have_match) * must_have_match
+ weight(vector_similarity) * vector_similarity
+ weight(title_relevance) * title_relevance
+ weight(seniority_fit) * seniority_fit
+ weight(preference_fit) * preference_fit
```

The cleanup does not change scoring. It changes:

- compatibility signaling
- operator-facing wording
- current-state documentation accuracy

## Compatibility and Historical Behavior

- Historical artifacts that already exist remain `stage_transition_artifacts_v2`.
- Newly produced artifacts after this cleanup become `stage_transition_artifacts_v3`.
- No backfill or migration of stored historical artifacts is required.
- Artifact readers that branch by `schema_version` should use that version rather than key inference.

## Verification Requirements

Implementation should prove:

1. Newly produced stage-transition artifacts report `schema_version: "stage_transition_artifacts_v3"`.
2. Ranking decision-summary fields remain the six-feature shape introduced by the six-feature ranking rollout.
3. Admin ranking labels/descriptions match actual computation semantics.
4. Cross-cutting ranking docs use current runtime field names.
5. Existing tests for six-feature ranking behavior still pass unchanged or with only expected schema-version updates.

## Risks

### Consumer Compatibility Risk

Any downstream logic that hardcodes `stage_transition_artifacts_v2` for newly produced artifacts may need a small test or parser update.

Mitigation:

- keep the ranking block field names unchanged from the current implementation
- change only the explicit schema version marker
- update in-repo tests that assert the old version

### Scope Creep Risk

This cleanup could expand into a broader reranking redesign if not kept bounded.

Mitigation:

- do not revisit ranking weights, formulas, or feature construction
- restrict implementation to version signaling, wording, and documentation synchronization

## Handoff

If approved, the implementation plan should be a small follow-up focused on:

1. updating the stage-transition artifact version and related assertions
2. fixing settings copy in the admin schema registry
3. fixing stale naming in [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
4. updating affected feature/stage docs and history entries
