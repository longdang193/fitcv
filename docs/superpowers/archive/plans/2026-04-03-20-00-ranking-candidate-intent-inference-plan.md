---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Implement deterministic candidate-intent inference before ranking, centralize role normalization in shared config, and expose effective preference provenance in ranking artifacts."
---

# Ranking Candidate-Intent Inference Implementation Plan

## Scope

Implement the ranking-intent changes defined in [2026-04-03-19-45-ranking-candidate-intent-inference-spec.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/superpowers/specs/2026-04-03-19-45-ranking-candidate-intent-inference-spec.md).

This plan keeps the work intentionally bounded:

- add deterministic fallback inference for `target_role`, `role_families`, and `domains`
- keep explicit candidate YAML preferences authoritative
- move role normalization and role-family alias rules into central config
- update ranking to use merged `effective_preferences` instead of only raw sparse preferences
- make inferred-vs-explicit provenance visible in ranking artifacts and debug surfaces

## Source-of-Truth Alignment

Affected current-state docs:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/cv_system.yaml)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/stages/ranking.yaml)

Affected history docs:

- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/history.md)

Affected cross-cutting docs:

- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/FitCV-pipeline.md)

Affected generated docs:

- [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/generated/feature_overview.md)
- [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/generated/features_index.yaml)
- [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/generated/feature_capabilities_index.yaml)

Primary code and tests:

- [taxonomy.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/config/taxonomy.yaml)
- [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/config.py)
- [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/candidate.py)
- [ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py)
- [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/pipeline.py)
- [test_candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_candidate.py)
- [test_ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_ranking.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_pipeline.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_config.py)

Generated refresh required:

- yes

## Invariants

- Explicit candidate YAML preferences remain authoritative over inferred fallback intent.
- Candidate-intent inference remains deterministic and bounded.
- Ranking remains the sole owner of ranking-time `title_relevance`, `preference_fit`, and authoritative post-filter fit labels.
- Shared role normalization must come from central config rather than duplicated literals in ranking code.
- Artifact/debug outputs remain bounded and readable.

## Implementation Tasks

### Task 1: Extend Central Taxonomy for Role Normalization

Update [taxonomy.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/config/taxonomy.yaml) so shared role normalization lives in config rather than hardcoded aliases in [ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py).

Changes:

- add canonical role aliases
- add role-family membership
- add role-family neighbor relationships
- keep the shape compatible with the existing central config merge flow in [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/config.py)

Acceptance criteria:

- role and role-family mappings are no longer hardcoded only in ranking runtime code
- config load exposes one shared role taxonomy object
- the taxonomy remains human-editable and small enough to review safely

### Task 2: Add Role-Taxonomy Config Helpers

Update [config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/config.py) to normalize and expose the role taxonomy consistently.

Changes:

- add normalization helpers for role aliases and family relationships
- validate the config shape conservatively
- preserve safe fallback behavior if the new role taxonomy keys are absent

Acceptance criteria:

- consumers can read role taxonomy from config without parsing raw YAML ad hoc
- malformed optional role-taxonomy payloads fail safely or degrade predictably
- existing config tests are extended to cover the new shape

### Task 3: Implement Deterministic Candidate-Intent Inference

Update [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/candidate.py) to infer fallback ranking intent from profile evidence.

Changes:

- infer fallback `target_role` from recent representative experience roles
- infer fallback `role_families` from explicit experience metadata or the shared role taxonomy
- infer fallback `domains` from `domain_tags` on experiences and projects
- expose a merged `effective_preferences` object plus per-field source metadata

Acceptance criteria:

- sparse candidate YAML can still produce usable ranking preferences when recent evidence is strong
- explicit YAML values always override inferred values
- inference stays bounded to role titles, role families, and domain tags already present in the profile

### Task 4: Refactor Ranking to Consume `effective_preferences`

Update [ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py) so title and preference scoring use merged effective preferences rather than raw sparse YAML only.

Changes:

- replace hardcoded `_ROLE_FAMILY_ALIASES` and neighbors with config-driven helpers
- use `effective_preferences.target_role` in `compute_title_relevance(...)`
- use `effective_preferences.role_families` and `effective_preferences.domains` in `compute_preference_fit_details(...)`
- preserve the current public feature names and bounded score contracts

Acceptance criteria:

- `title_relevance` no longer defaults to neutral solely because explicit `target_role` is missing when recent role evidence is strong
- `preference_fit` can discriminate domain and role-family alignment from inferred intent
- ranking remains deterministic and testable

### Task 5: Wire Effective Preference Provenance Into Pipeline Artifacts

Update [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/pipeline.py) so ranking artifacts expose how effective preferences were resolved.

Changes:

- include explicit `preferences` snapshot where relevant
- include inferred fallback intent
- include merged `effective_preferences`
- include per-field preference sources in bounded ranking samples and summaries

Acceptance criteria:

- operators can tell whether `title_relevance` and `preference_fit` were driven by explicit YAML or inferred fallback intent
- artifact payloads remain bounded and stage-appropriate

### Task 6: Add Regression Coverage

Update tests to lock down the new behavior.

Primary targets:

- [test_candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_candidate.py)
- [test_ranking.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_ranking.py)
- [test_pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_pipeline.py)
- [test_config.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/tests/test_config.py)

Coverage should include:

- sparse YAML with strong recent-role evidence
- explicit preference override behavior
- role-family inference from explicit metadata and title normalization
- domain inference from weighted profile tags
- artifact provenance surfaces for inferred vs explicit values

Acceptance criteria:

- tests cover the main fallback and override paths
- config tests cover the central role-taxonomy structure
- no existing ranking-quality tests regress unintentionally

### Task 7: Sync Docs and Generated Discovery

Update docs to reflect the new ranking-intent behavior and central normalization ownership.

Targets:

- [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/cv_system.yaml)
- [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/history.md)
- [ranking.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/stages/ranking.yaml)
- [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/FitCV-pipeline.md)
- generated outputs listed above

Acceptance criteria:

- source-of-truth docs describe deterministic fallback intent clearly
- docs distinguish explicit preferences from inferred effective preferences
- generated discovery reflects the updated feature and stage contracts

## Verification Plan

Run targeted verification after implementation:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_config.py -k "role_taxonomy or config"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_candidate.py -k "effective_preferences or infer"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_ranking.py -k "title_relevance or preference_fit or role_family"
```

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py -k "ranking and effective_preferences"
```

If config or candidate helpers affect broader flows, run:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_pipeline.py
```

Manual verification checklist:

- inspect a ranking artifact from a sparse-YAML run and confirm effective preferences are present
- confirm an explicit `target_role` still overrides inferred recent-role intent
- confirm `title_relevance` becomes discriminative for sparse-YAML candidates with strong recent-role history
- confirm `preference_fit` can use inferred domains and role families without changing location semantics
- confirm central role taxonomy is the only active source of role-family alias truth

## Risks and Mitigations

### Over-Inference Risk

Risk:

- mixed or unusual recent roles could infer the wrong target role or family

Mitigation:

- keep inference fallback-only
- prefer recent repeated evidence
- expose provenance in artifacts

### Config Drift Risk

Risk:

- role aliases could drift again if some code paths keep private maps

Mitigation:

- remove or retire local hardcoded maps
- make the taxonomy-config path the only supported source
- add config and ranking tests that fail on mismatched assumptions

### Sparse Metadata Risk

Risk:

- some profiles may still lack enough `domain_tags` or clean roles to infer anything useful

Mitigation:

- keep neutral fallback behavior when evidence is genuinely weak
- avoid forcing inference when support is insufficient

## Done Definition

This work is done when:

- deterministic candidate-intent inference is implemented in the `Ranking` worktree
- explicit YAML preferences remain authoritative while missing values can be inferred from recent evidence
- role normalization lives in shared config rather than ranking-local literals
- ranking artifacts expose effective-preference provenance
- targeted tests pass
- source-of-truth docs and generated discovery are refreshed
