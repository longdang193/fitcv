---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Improve shortlist candidate-query construction so retrieval uses flattened candidate skills plus inferred role-family and domain hints from the full profile evidence surface."
invariants:
  - shortlist remains the sole owner of candidate query construction for vector retrieval
  - candidate query construction stays deterministic and bounded
  - the shortlist stage still issues one candidate query text in phase 1 rather than switching to multi-query retrieval
  - profiles without richer metadata must still produce a valid retrieval query through compatibility fallbacks
---

# Shortlist Query Construction Upgrade Spec

## Summary

Upgrade `shortlist` candidate-query construction so retrieval sees more of the candidate's actual evidence surface. Instead of using only top-level profile fields and explicit root skills, the candidate query should use `flatten_skills(profile)` and bounded inferred role-family/domain hints from experiences and projects.

## Problem

`shortlist` recall is weaker than it should be because the candidate query text underuses candidate evidence.

Today, [`build_candidate_query_text()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/src/fitcv/vector_search.py) builds the retrieval query from a narrow subset of the profile:

- headline
- target role
- recent roles
- explicit root skills from `skills[].name`
- preferred domains

But [`flatten_skills()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/src/fitcv/candidate.py) already knows how to extract skills from:

- explicit root skills
- experience bullets
- projects

That richer evidence never reaches shortlist retrieval today.

This creates a mismatch:

- the candidate profile contains broader skill and role evidence
- later stages already consume richer profile signals
- shortlist retrieval still searches with a thinner candidate summary than the system can construct

As a result, semantically relevant jobs can be under-retrieved or ranked too low before `ranking` ever sees them.

## Goals

- Improve shortlist recall by using a richer but still bounded candidate retrieval query
- Use `flatten_skills(profile)` as the default skill surface instead of only `skills[].name`
- Include inferred role-family hints so jobs with semantically aligned titles are easier to retrieve
- Include inferred domain hints from candidate evidence, not only explicit preferred domains
- Keep retrieval query construction deterministic and explainable
- Expose the richer candidate-query components in shortlist debug surfaces

## Non-Goals

- Replacing the single-query shortlist model with multi-query retrieval
- Changing shortlist embedding reuse semantics
- Changing `rule_filter` behavior
- Replacing `ranking` logic
- Adding LLM-based shortlist query generation

## Current State

In [`build_candidate_query_text()`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/src/fitcv/vector_search.py), the query currently looks roughly like:

- `Candidate: <headline>`
- `Target role: <preferences.target_role>`
- `Recent roles: <up to 3 experience roles>`
- `Skills: <skills[].name up to vector_max_candidate_skills>`
- `Target domains: <preferences.domains>`

That means shortlist retrieval currently ignores:

- skills mentioned only inside experience bullets
- project-only skills
- inferred role-family signal from recent experience
- domain tags already present in experiences/projects
- bounded responsibility-aligned vocabulary already present elsewhere in the profile

## Proposed Design

### 1. Build the shortlist query from the full candidate evidence surface

`build_candidate_query_text()` should switch from a top-level-profile-only view to a bounded evidence-surface view.

The upgraded query should include:

- headline
- explicit target role when present
- recent roles
- flattened skills from `flatten_skills(profile)`
- explicit preferred domains
- inferred role-family hints
- inferred domain hints from experiences and projects

The query should remain one deterministic string, but its inputs should be broader and more faithful to the actual candidate profile.

### 2. Use `flatten_skills(profile)` as the default skills source

Instead of:

- `skills[].name`

the query should use:

- `flatten_skills(profile)`

This allows shortlist retrieval to see skills that are only present in:

- experience bullet metadata
- project skill lists

The output must still be bounded by `vector_max_candidate_skills`.

### 3. Add inferred role-family hints

Candidate query construction should include bounded role-family hints derived from:

- `preferences.role_families` when present
- recent experience `role_family` values when present
- inferred role-family values from recent roles when explicit metadata is missing

Existing role-family inference logic already exists in [`ranking.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Shortlist/src/fitcv/ranking.py), so shortlist should reuse a shared deterministic inference path rather than invent a separate taxonomy.

The role-family signal should help retrieval capture jobs like:

- `Business Intelligence Analyst`
- `Analytics Specialist`
- `Data Analyst`

as semantically closer within the same candidate target family.

### 4. Add inferred domain hints

Candidate query construction should include a bounded union of:

- explicit `preferences.domains`
- `experiences[].domain_tags`
- `projects[].domain_tags`

This gives shortlist retrieval domain vocabulary even when the user profile is incomplete at the preference layer.

This should stay bounded and deduplicated so the query does not become noisy or overly long.

### 5. Keep the query deterministic and bounded

The upgraded query must remain:

- deterministic for the same profile
- deduplicated
- length-bounded
- stable enough for shortlist debugging and reuse analysis

That means:

- normalize and dedupe each component category
- cap skills by `vector_max_candidate_skills`
- cap inferred roles/domains by small bounded limits
- preserve a stable component order

Recommended order:

1. headline
2. target role
3. recent roles
4. role-family hints
5. flattened skills
6. explicit + inferred domain hints

### 6. Expose query components in shortlist debug surfaces

Because this changes retrieval behavior, shortlist debug surfaces should make it clear what fed the candidate query.

At minimum, shortlist debug should be able to expose bounded candidate-query components such as:

- `headline`
- `target_role`
- `recent_roles`
- `role_family_hints`
- `flattened_skill_sample`
- `domain_hints`

This belongs to `inspection_debugging` because reviewers should be able to tell whether a retrieval miss came from:

- weak candidate evidence
- weak query construction
- retrieval ranking itself

## Example

### Current behavior

Candidate profile top-level fields:

- headline: `Data Analyst`
- target role: `Data Analyst`
- root skills: `SQL`, `Python`
- preferred domains: `banking`

Deeper evidence:

- experience bullets mention `Power BI`, `Looker`, KPI reporting
- project skills include `dbt`, `BigQuery`
- experience/project metadata includes `retail banking`

Current shortlist query may look like:

```text
Candidate: Data Analyst
Target role: Data Analyst
Skills: SQL, Python
Target domains: banking
```

That query under-represents the candidate's actual evidence surface.

### Proposed behavior

The upgraded query could look more like:

```text
Candidate: Data Analyst
Target role: Data Analyst
Recent roles: Data Analyst, BI Analyst
Role families: analytics
Skills: SQL, Python, Power BI, Looker, BigQuery, dbt
Target domains: banking, retail banking
```

This is still bounded and deterministic, but it gives shortlist retrieval a much better picture of the candidate.

## Design Details

### Candidate query component contract

The shortlist query builder should conceptually resolve these component groups:

- `headline`
- `target_role`
- `recent_roles`
- `role_family_hints`
- `flattened_skills`
- `domain_hints`

Then it should render them into one candidate query text string in stable order.

### Compatibility behavior

If a profile is sparse:

- missing role families should not break query construction
- missing domain tags should fall back to explicit preferred domains only
- missing deeper skill evidence should still fall back to explicit root skills via `flatten_skills(profile)`

So the rollout is additive:

- richer profiles improve retrieval
- older profiles still work

## Risks

### 1. Query bloat

Using too many flattened skills or inferred hints can make the query noisy.

Mitigation:

- cap each component group
- preserve deterministic ordering
- keep bounded debug visibility

### 2. Overly broad retrieval

Too many generic inferred signals could weaken precision.

Mitigation:

- prefer smaller limits for inferred role-family/domain hints
- keep shortlist reranking and later ranking unchanged

### 3. Divergent taxonomies

If shortlist invents separate role-family inference from ranking/cv-analysis, the pipeline will drift.

Mitigation:

- reuse the existing deterministic role-family inference path

## Rollout Notes

This should be implemented as a bounded shortlist contract change, not a major retrieval redesign.

The rollout should:

- preserve the single-query shortlist model
- improve only the candidate query builder and related shortlist debug visibility
- avoid changing downstream ranking or CV stage contracts

## Acceptance Criteria

- shortlist candidate query text uses `flatten_skills(profile)` instead of only `skills[].name`
- shortlist candidate query text includes bounded role-family hints
- shortlist candidate query text includes bounded inferred domain hints from experiences/projects
- query construction remains deterministic and bounded
- older candidate profiles still produce valid candidate query text
- shortlist debug surfaces can expose the new query components clearly
- source-of-truth docs are updated consistently after implementation
