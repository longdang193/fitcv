---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Add deterministic candidate-intent inference before ranking, with explicit YAML preferences overriding inferred fallback intent and shared role normalization moved into central config."
invariants:
  - Explicit candidate YAML preferences remain authoritative.
  - Inference fills only missing target-role, role-family, and domain preferences.
  - Ranking-time candidate-intent inference remains deterministic and explainable.
  - Shared role normalization must live in central config instead of hardcoded aliases in stage code.
---

# Ranking Candidate-Intent Inference

## Why

Ranking quality is still too sensitive to how completely the candidate YAML is filled out.

Today:

- `compute_title_relevance(...)` falls back to `0.5` when `preferences.target_role` is missing.
- `compute_preference_fit_details(...)` falls back to neutral `0.5` components when `preferences.domains`, `preferences.role_families`, and `preferences.location_types` are sparse.

That means the ranking stage loses useful discrimination whenever the candidate profile is incomplete, even if recent experience already contains enough signal to infer likely role intent.

This is especially visible for candidates whose YAML captures rich experience and project history but minimal explicit preference metadata.

## Problem

The ranking stage currently mixes two concerns:

1. ranking feature computation
2. lightweight role-family normalization and candidate-intent interpretation

It also keeps role-family alias logic hardcoded in [`src/fitcv/ranking.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py), which makes normalization drift likely if other stages later need the same mapping.

## Goals

- Improve ranking robustness when candidate YAML preferences are sparse.
- Preserve explicit candidate preferences as the highest-priority source of truth.
- Infer only bounded fallback intent from profile evidence that already exists.
- Centralize role and role-family normalization in shared config.
- Make inferred vs explicit preference provenance visible in ranking artifacts.

## Non-Goals

- No LLM-based candidate-intent inference.
- No attempt to rewrite or enrich the candidate YAML automatically.
- No change to `must_have_match`.
- No UI-heavy settings work in this slice.

## Current Example

Candidate YAML:

```yaml
preferences:
  location_types: [remote, hybrid]
experiences:
  - role: Senior Data Analyst
    role_family: analytics
    domain_tags: [banking]
  - role: BI Analyst
    domain_tags: [retail]
```

Current ranking behavior:

- `target_role` missing -> `title_relevance = 0.5`
- `domains` missing -> domain component of `preference_fit` becomes neutral
- `role_families` missing -> role-family component of `preference_fit` becomes neutral

Even though recent experience strongly suggests:

- target role near `Data Analyst`
- role family `analytics`
- domains `banking` and `retail`

## Proposed Design

Add a deterministic candidate-intent inference step before ranking feature computation.

Ranking should consume:

- raw `preferences`
- inferred fallback intent
- merged `effective_preferences`

The merge rule is:

- explicit YAML wins
- inferred intent only fills missing keys

### New Runtime Shape

```json
{
  "preferences": {
    "location_types": ["remote", "hybrid"]
  },
  "effective_preferences": {
    "target_role": "Data Analyst",
    "role_families": ["analytics"],
    "domains": ["banking", "retail"],
    "location_types": ["remote", "hybrid"]
  },
  "preference_sources": {
    "target_role": "inferred_recent_experience",
    "role_families": "inferred_role_family_map",
    "domains": "inferred_profile_domain_tags",
    "location_types": "explicit_yaml"
  }
}
```

## Inference Rules

### 1. Fallback `target_role`

Infer from recent experience role titles.

Process:

1. take the most recent representative experience roles
2. normalize the title
3. map known title variants to canonical roles
4. choose the most representative recent role

Examples:

- `Senior Data Analyst` -> `Data Analyst`
- `BI Analyst` -> `Data Analyst`
- `Business Intelligence Analyst` -> `Data Analyst`
- `Analytics Engineer` -> `Analytics Engineer`

If explicit `preferences.target_role` exists, keep it unchanged.

### 2. Fallback `role_families`

Infer from:

- explicit `experiences[].role_family` when present
- otherwise normalized role titles via the shared role-family map

Recent repeated families should be favored.

Examples:

- `Data Analyst`, `BI Analyst`, `Analytics Specialist` -> `analytics`
- `Data Engineer`, `Analytics Engineer` -> `data_engineering`
- `Data Scientist`, `AI Trainer` -> `data_science`

If explicit `preferences.role_families` exists, keep it unchanged.

### 3. Fallback `domains`

Infer from profile evidence metadata, weighted toward recent experience.

Preferred sources:

- `experiences[].domain_tags`
- `projects[].domain_tags`
- optionally `achievements[].domain_tags` later if already present

Weighting:

- recent experience > older experience
- experience > project

If explicit `preferences.domains` exists, keep it unchanged.

## Shared Normalization Map

Role normalization and role-family aliases should move out of `ranking.py` and into the central config layer.

Recommended source:

- extend [`config/taxonomy.yaml`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/config/taxonomy.yaml)

Reasoning:

- this file already owns shared taxonomy and normalization policy
- it is loaded centrally by [`src/fitcv/config.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/config.py)
- role aliases are taxonomy/normalization data, not local ranking logic

### Proposed Config Shape

```yaml
role_taxonomy:
  canonical_roles:
    data analyst:
      aliases:
        - bi analyst
        - business intelligence analyst
        - analytics specialist
    analytics engineer:
      aliases:
        - analytics engineer
    data scientist:
      aliases:
        - ai trainer

  role_families:
    analytics:
      roles:
        - data analyst
        - analytics analyst
        - business intelligence analyst
        - insights analyst
    data_engineering:
      roles:
        - data engineer
        - analytics engineer
    data_science:
      roles:
        - data scientist
        - ai trainer

  role_family_neighbors:
    analytics:
      - data_science
    data_science:
      - analytics
      - ml_engineering
```

This keeps:

- canonical role mapping
- role-family membership
- role-family neighbor relationships

in one source of truth.

## Ranking Flow Change

### Before

1. load candidate profile
2. read raw `preferences`
3. compute ranking features

### After

1. load candidate profile
2. infer bounded candidate intent from profile evidence
3. merge explicit `preferences` with inferred fallback intent
4. compute ranking features using `effective_preferences`
5. expose sources/provenance in stage artifacts

## Expected Behavior

### Example A: Sparse YAML

Candidate profile:

```yaml
preferences:
  location_types: [remote, hybrid]
experiences:
  - role: Senior Data Analyst
    role_family: analytics
    domain_tags: [banking]
  - role: BI Analyst
    domain_tags: [retail]
```

Expected effective preferences:

```yaml
target_role: Data Analyst
role_families: [analytics]
domains: [banking, retail]
location_types: [remote, hybrid]
```

Effect:

- `title_relevance` no longer defaults to neutral
- `preference_fit` can score domain and role-family alignment instead of returning mostly `0.5`

### Example B: Explicit YAML Override

Candidate profile:

```yaml
preferences:
  target_role: Analytics Engineer
  location_types: [remote]
experiences:
  - role: Senior Data Analyst
    role_family: analytics
    domain_tags: [banking]
```

Expected effective preferences:

```yaml
target_role: Analytics Engineer
role_families: [analytics]
domains: [banking]
location_types: [remote]
```

Effect:

- explicit `target_role` remains authoritative
- only missing values are inferred

## Artifact and Debugging Changes

Ranking artifacts should expose:

- explicit `preferences`
- inferred fallback intent
- merged `effective_preferences`
- per-field preference source

Suggested fields:

- `effective_target_role`
- `effective_role_families`
- `effective_domains`
- `preference_sources`

This keeps ranking explainable when a feature score comes from inferred intent rather than explicit YAML.

## Validation Rules

The inference layer should be bounded and conservative.

- Do not infer a target role when no recent role evidence exists.
- Do not infer domains from weak free-text parsing in this slice.
- Do not overwrite explicit YAML values.
- Normalize role/title aliases only through the central role taxonomy.

## Risks

- Over-inference could push candidates toward the wrong target role if recent experience is unusually mixed.
- Poorly curated role aliases could create bad canonical-role collapse.
- If ranking and future stages use different role taxonomy sources, drift would reappear.

## Mitigations

- keep inference fallback-only
- keep role taxonomy in central config
- log provenance for inferred fields
- prefer recent experience over older or weaker evidence

## Affected Sources

- [`src/fitcv/candidate.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/candidate.py)
- [`src/fitcv/ranking.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/ranking.py)
- [`src/fitcv/pipeline.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/pipeline.py)
- [`src/fitcv/config.py`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/src/fitcv/config.py)
- [`config/taxonomy.yaml`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/config/taxonomy.yaml)
- [`docs/features/cv_system/cv_system.yaml`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/features/cv_system/cv_system.yaml)
- [`docs/stages/ranking.yaml`](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Ranking/docs/stages/ranking.yaml)

## Acceptance Criteria

- Ranking no longer collapses `title_relevance` to neutral solely because explicit `target_role` is absent when recent role evidence is strong.
- Ranking no longer collapses `preference_fit` to mostly neutral solely because explicit `domains` or `role_families` are absent when profile evidence is strong.
- Explicit YAML preferences still override inferred values.
- Role normalization no longer depends on hardcoded alias maps in `ranking.py`.
- Ranking artifacts make inferred-vs-explicit preference provenance visible.
