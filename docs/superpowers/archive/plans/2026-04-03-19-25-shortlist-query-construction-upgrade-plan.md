---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Improve shortlist candidate-query construction so vector retrieval uses flattened skills plus bounded inferred role-family and domain hints from the full candidate evidence surface."
invariants:
  - "Shortlist remains the sole owner of candidate query construction for vector retrieval."
  - "Candidate query construction must stay deterministic, bounded, and explainable."
  - "The shortlist stage still issues one candidate query text in phase 1 rather than switching to multi-query retrieval."
  - "Profiles without richer metadata must still produce a valid retrieval query through compatibility fallbacks."
---

# Shortlist Query Construction Upgrade Plan

## Triage

Feature type: MODIFY  
Summary: Upgrade shortlist candidate-query construction so retrieval uses `flatten_skills(profile)` plus bounded inferred role-family and domain hints instead of a thin top-level profile summary.  
Reasoning: The shortlist stage already owns candidate query construction and retrieval. This change improves recall within the existing single-query retrieval model and adds debug visibility for the richer query inputs. It modifies existing shortlist behavior rather than introducing a new feature family or stage.  
Invariants:
- `shortlist` remains the sole owner of candidate query construction for vector retrieval.
- Query construction must stay deterministic, bounded, and explainable.
- The shortlist stage still uses one candidate query text in phase 1.
- Profiles without richer metadata must still produce a valid retrieval query through fallback behavior.
Dependencies:
- `cv_system`
- `inspection_debugging`
- shortlist runtime in `src/fitcv/vector_search.py`
- candidate profile skill extraction in `src/fitcv/candidate.py`
- shared role-family inference in `src/fitcv/ranking.py` or an equivalent shared helper
Affected stages:
- shortlist
Affected features:
- cv_system
- inspection_debugging
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/inspection_debugging/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes
Spec needed: no
Plan needed: yes
Rollback trigger: shortlist recall becomes noisier, query text becomes too bloated, or shortlist debug no longer explains what retrieval actually used
Rollback method: restore the old top-level-profile query builder while leaving additive debug helpers inert
Migration needed: no
Risk level: medium

## Scope

This plan implements [2026-04-03-19-10-shortlist-query-construction-upgrade-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/docs/superpowers/specs/2026-04-03-19-10-shortlist-query-construction-upgrade-spec.md).

In scope:

- use `flatten_skills(profile)` as the default shortlist skill surface
- add bounded role-family hints to the candidate query
- add bounded domain hints from preferences plus experience/project metadata
- keep the shortlist query deterministic and bounded
- expose richer candidate-query components in shortlist debug surfaces

Out of scope:

- multi-query shortlist retrieval
- LLM-generated shortlist query text
- changes to embedding reuse semantics
- changes to ranking logic
- redesigning the candidate YAML contract beyond using fields that already exist

## Implementation Tasks

### Task 1: Define the candidate-query component contract

Add an explicit code-owned contract for the candidate query components that shortlist retrieval is allowed to use.

Required component groups:

- `headline`
- `target_role`
- `recent_roles`
- `role_family_hints`
- `flattened_skills`
- `domain_hints`

Requirements:

- stable component order
- bounded per-component limits
- deduped values
- compatibility when some component groups are missing

Likely touchpoints:

- `src/fitcv/vector_search.py`

### Task 2: Switch shortlist skills to `flatten_skills(profile)`

Replace the current root-skill-only shortlist query logic with the broader flattened skill surface.

Requirements:

- use `flatten_skills(profile)` instead of only `skills[].name`
- preserve `vector_max_candidate_skills`
- keep skill ordering deterministic
- avoid duplicates and empty values

Likely touchpoints:

- `src/fitcv/vector_search.py`
- `src/fitcv/candidate.py`
- `tests/test_vector_search.py`

### Task 3: Add bounded role-family hints

Add shortlist role-family hints that reflect the candidate's likely role space.

Sources, in priority order:

- `preferences.role_families`
- explicit `experiences[].role_family`
- inferred role families from recent experience roles

Requirements:

- reuse the existing deterministic role-family inference path where possible
- keep hints bounded and deduped
- avoid introducing a second divergent role-family taxonomy

Likely touchpoints:

- `src/fitcv/vector_search.py`
- `src/fitcv/ranking.py` or a shared helper extracted from it
- shortlist tests

### Task 4: Add bounded domain hints

Make shortlist query construction see more domain signal than `preferences.domains` alone.

Sources:

- `preferences.domains`
- `experiences[].domain_tags`
- `projects[].domain_tags`

Requirements:

- merge and dedupe these sources
- keep bounded limits
- preserve explicit preferences while still benefiting from evidence-derived hints

Likely touchpoints:

- `src/fitcv/vector_search.py`
- candidate/profile fixtures in tests

### Task 5: Render the richer query text deterministically

Update `build_candidate_query_text()` so it renders the richer component contract into one stable text string.

Requirements:

- preserve deterministic formatting for the same profile
- keep component ordering stable
- avoid query bloat by enforcing bounded lists
- keep the output explainable enough for debug artifacts and tests

Acceptance examples should cover:

- sparse profile fallback
- profile with deep experience/project skills
- profile with explicit and inferred role/domain hints

### Task 6: Expose shortlist query components in debug surfaces

Add bounded visibility into what fed the shortlist query.

Required surfaces:

- shortlist stage decision summary or debug block
- shortlist artifact samples or summary fields
- any run-level shortlist debug payload that already includes candidate query text

Recommended fields:

- `candidate_query_components.headline`
- `candidate_query_components.target_role`
- `candidate_query_components.recent_roles`
- `candidate_query_components.role_family_hints`
- `candidate_query_components.flattened_skill_sample`
- `candidate_query_components.domain_hints`

Requirements:

- keep these bounded
- do not dump the full candidate profile
- make retrieval misses easier to interpret

Likely touchpoints:

- `src/fitcv/pipeline.py`
- shortlist stage artifact builders
- shortlist tests

### Task 7: Sync source-of-truth docs and generated discovery

Update docs once the runtime behavior is in place.

Required updates:

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/cv_system/history.md`
- `docs/features/inspection_debugging/inspection_debugging.yaml`
- `docs/features/inspection_debugging/history.md`
- `docs/stages/shortlist.yaml`
- `docs/FitCV-pipeline.md`

Generated refresh:

- `docs/generated/feature_overview.md`
- `docs/generated/features_index.yaml`
- `docs/generated/feature_capabilities_index.yaml`

## Verification Plan

### Unit and contract tests

- candidate-query tests that prove flattened experience/project skills now reach query construction
- tests for role-family hint resolution from:
  - explicit preferences
  - explicit experience metadata
  - inferred recent roles
- tests for domain-hint resolution from:
  - preferences
  - experience domain tags
  - project domain tags
- deterministic-order tests for the final candidate query text
- shortlist artifact/debug tests for new query-component visibility

### Regression checks

- sparse/legacy candidate profiles still produce valid candidate query text
- shortlist query remains bounded by configured limits
- existing vector search integration continues to consume one query text string
- shortlist retrieval semantics remain unchanged apart from richer query construction

## Execution Order

1. Define the shortlist candidate-query component contract.
2. Switch skill extraction to `flatten_skills(profile)`.
3. Add bounded role-family hints.
4. Add bounded domain hints.
5. Render the richer query text deterministically.
6. Expose candidate-query components in shortlist debug surfaces.
7. Sync docs and regenerate discovery outputs.

## Risks and Notes

- The biggest quality risk is query bloat if too many inferred hints are added without limits.
- The biggest architecture risk is duplicating role-family inference instead of reusing the existing deterministic helper.
- The biggest debugging risk is improving query construction without surfacing the actual component groups used by retrieval.

## Task Status

Status: completed

- [x] Task 1: Define the candidate-query component contract
- [x] Task 2: Switch shortlist skills to `flatten_skills(profile)`
- [x] Task 3: Add bounded role-family hints
- [x] Task 4: Add bounded domain hints
- [x] Task 5: Render the richer query text deterministically
- [x] Task 6: Expose shortlist query components in debug surfaces
- [x] Task 7: Sync source-of-truth docs and generated discovery
