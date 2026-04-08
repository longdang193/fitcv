---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Upgrade cv_analysis domain and responsibility alignment from mostly lexical heuristics to hybrid lexical-plus-semantic scoring with explicit weights and stage-owned embedding reuse."
invariants:
  - "`cv_analysis` remains the sole owner of evidence retrieval and final evidence selection before CV writing."
  - "`required_skill_support` and `role_alignment` remain bounded, interpretable channels and are not replaced by a full semantic-only stack."
  - "Semantic candidate embeddings may be generated only inside `cv_analysis` when that stage directly consumes them."
  - "Final evidence selection stays a bounded per-job top-k selector and does not become an unbounded free-form reranker."
  - "`cv_generation` continues consuming persisted analysis outputs rather than recomputing evidence retrieval by default."
---

# CV Analysis Semantic Alignment Upgrade Spec

## Triage

Feature type: MODIFY  
Summary: Upgrade `cv_analysis` so `domain_alignment` and `responsibility_alignment` score candidate evidence with a hybrid lexical-plus-semantic method, backed by stage-owned embedding reuse and a bounded final evidence selector.  
Reasoning: This changes existing `cv_system` behavior inside an already managed stage contract. The work is stage-heavy because it changes `cv_analysis` retrieval/scoring internals, and it also touches settings and inspection surfaces because the new hybrid scores and weights must be understandable and tunable.  
Invariants:
- `cv_analysis` remains the owner of evidence retrieval and final evidence selection.
- `required_skill_support` stays primarily deterministic/canonical.
- `role_alignment` stays lightweight and bounded rather than becoming a second semantic retrieval stack.
- Semantic matching happens inside channel scoring, not by making the final top-k selector do semantic reasoning twice.
- Any candidate chunk embeddings reintroduced by this rollout must be stage-owned by `cv_analysis`.
Dependencies:
- evidence retrieval module in [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- `cv_analysis` stage runtime in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- candidate profile contract in [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/candidate.py)
- settings contract in [settings_schema.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv_cp/settings_schema.py)
Affected stages:
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `settings_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml: [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
  feature_history: [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/history.md)
  feature_docs:
  - [settings_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/settings_system/settings_system.yaml)
  - [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/settings_system/history.md)
  cross_cutting_docs:
  - [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/FitCV-pipeline.md)
  readme: none
  generated:
  - `docs/generated/feature_overview.md`
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_capabilities_index.yaml`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Why

`cv_analysis` already has a good stage shape:

- retrieve separate evidence pools for:
  - required skill support
  - role alignment
  - domain alignment
  - responsibility alignment
- merge and dedupe those pools by stable `evidence_id`
- select one bounded final evidence bundle

The remaining weakness is *how* two of those channels score evidence:

- [_score_domain_alignment()](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- [_score_responsibility_alignment()](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)

Today they are mostly lexical and heuristic:

- explicit tag overlap
- token overlap over `scoring_context`
- token overlap over `responsibility_themes`

That means semantically relevant evidence can still be missed when wording differs.

## Current Problem

Examples of the failure mode:

Job responsibility:

```text
Translate raw data into recommendations for business stakeholders.
```

Candidate evidence:

```text
Built executive dashboards and reporting used by leadership for pricing decisions.
```

Current lexical behavior:

- weak token overlap
- candidate evidence may under-score or miss the responsibility channel entirely

Desired behavior:

- strong responsibility alignment
- both texts describe stakeholder-facing decision support from analytics work

Another example:

Job domain:

```text
retail banking
```

Candidate evidence:

```text
Built credit risk reporting and loan operations analytics.
```

Current lexical behavior:

- weak if `retail banking` is not written explicitly

Desired behavior:

- strong domain alignment
- credit risk / loan operations / reporting are semantically close to banking work

## Goals

1. Keep `required_skill_support` deterministic and `role_alignment` lightweight.
2. Upgrade `domain_alignment` and `responsibility_alignment` to hybrid lexical-plus-semantic scoring.
3. Reintroduce candidate evidence embeddings only where `cv_analysis` directly consumes them.
4. Keep final evidence selection bounded, explainable, and coverage-oriented.
5. Make semantic/lexical weights explicit and configurable.
6. Expose those weights through the admin settings UI, not only internal config.
7. Expose enough debug detail that operators can understand *why* an evidence item was selected.

## Non-Goals

- Replacing all evidence retrieval with embeddings only
- Making `cv_analysis` fully LLM-dependent
- Moving final evidence selection into `cv_generation`
- Replacing the existing candidate YAML metadata contract
- Reintroducing unused candidate chunk embeddings in `shortlist`

## Proposed Design

### 1. Keep The Four-Channel Retrieval Shape

`cv_analysis` should keep the current four channels:

- `required_skill_support`
- `role_alignment`
- `domain_alignment`
- `responsibility_alignment`

This structure is already good because it is:

- bounded
- explainable
- stage-local

The upgrade is *inside* the weak channels, not by replacing the whole retrieval design.

### 2. Reintroduce Candidate Evidence Embeddings As A `cv_analysis`-Owned Capability

This rollout should reintroduce candidate chunk embeddings only for `cv_analysis`.

Scope:

- candidate evidence snippets derived from normalized evidence items:
  - experience bullet text
  - project highlight text
  - project business-value text
  - achievement text
  - optional normalized `responsibility_themes` text
  - optional normalized domain-context text

Ownership rule:

- `shortlist` must not generate these embeddings
- `cv_analysis` may generate or reuse them because it directly consumes them

Reuse rule:

- key by:
  - stable `evidence_id`
  - snippet content hash
  - embedding contract fingerprint

This keeps semantic scoring efficient across repeated runs without restoring dead work to the earlier stages.

### 3. Build Small Job-Side Semantic Inputs

For each ranked job, `cv_analysis` should derive two semantic input groups.

#### A. Responsibility snippets

Use each job responsibility as its own snippet.

Example:

```json
[
  "Build KPI dashboards for stakeholders",
  "Translate raw data into business recommendations"
]
```

#### B. Domain text

Build one bounded domain context text from:

- `domain`
- `job_family`
- optional short domain-related phrases from responsibilities if useful

Example:

```text
retail banking analytics stakeholder reporting
```

Reuse rule:

- job-side semantic inputs should also be reusable by content hash + embedding contract fingerprint

### 4. Upgrade Channel Scoring With A Hybrid Method

This is the core behavioral change.

#### Required skill support

Keep as-is:

- deterministic / canonical
- explicit skill overlap remains the primary signal

#### Role alignment

Keep mostly as-is:

- role-family match
- lexical title similarity

This channel is already bounded and interpretable enough for now.

#### Domain alignment

Upgrade to:

```text
domain_alignment_score =
  domain_lexical_weight * lexical_domain_score
  + domain_semantic_weight * semantic_domain_score
```

Recommended default weights:

- `domain_lexical_weight = 0.40`
- `domain_semantic_weight = 0.60`

Lexical domain score should still use:

- explicit `domain_tags`
- explicit domain/job-family overlap

Semantic domain score should use:

- embedding similarity between job domain text and candidate evidence domain/context text

#### Responsibility alignment

Upgrade to:

```text
responsibility_alignment_score =
  responsibility_lexical_weight * lexical_responsibility_score
  + responsibility_semantic_weight * semantic_responsibility_score
```

Recommended default weights:

- `responsibility_lexical_weight = 0.25`
- `responsibility_semantic_weight = 0.75`

Lexical responsibility score should still use:

- `responsibility_themes`
- token overlap over `scoring_context`

Semantic responsibility score should use:

- the best similarity between each evidence item’s semantic snippets and the job responsibility snippets

Fallback rule:

- if semantic scoring is unavailable for a given item, fall back to lexical-only for that item rather than failing the whole channel

### 5. Final Top-K Selector Stays Bounded, But Becomes Coverage-Aware

The final selector should *not* become another semantic reranker.

Its job should remain:

- choose the best small final evidence bundle
- avoid redundancy
- preserve evidence diversity
- maximize job coverage under the top-k budget

That means:

- semantic understanding happens in channel scoring
- final top-k uses the resulting channel scores plus coverage logic

Recommended selector behavior:

- keep a base selection score from weighted channel scores
- add marginal-gain bonuses when an item covers:
  - a not-yet-covered responsibility
  - a not-yet-covered domain/context need
  - a missing support channel
- penalize redundant items that mostly repeat already-covered evidence

This keeps the selector bounded and more job-aware without asking it to do semantics twice.

### 6. Keep Artifacts And Debugging Explicit

`cv_analysis` artifacts should expose:

- lexical vs semantic subscore for:
  - `domain_alignment`
  - `responsibility_alignment`
- whether semantic scoring was used or lexical fallback was used
- matched job responsibility snippets for selected evidence
- matched domain-context summary for selected evidence
- candidate evidence embedding reuse status
- job semantic-input embedding reuse status

Example per selected item:

```json
{
  "evidence_id": "exp_1",
  "matched_channels": ["responsibility_alignment", "domain_alignment"],
  "channel_scores": {
    "responsibility_alignment": 0.81,
    "domain_alignment": 0.67
  },
  "channel_subscores": {
    "responsibility_alignment": {
      "lexical": 0.22,
      "semantic": 0.96,
      "method": "hybrid"
    },
    "domain_alignment": {
      "lexical": 0.35,
      "semantic": 0.88,
      "method": "hybrid"
    }
  }
}
```

### 7. Settings Contract

This rollout should introduce explicit settings for the hybrid channels.

Recommended config shape:

```yaml
pipeline:
  cv_analysis:
    semantic_alignment:
      enabled: true
      model: text-embedding-3-large
      responsibility_lexical_weight: 0.25
      responsibility_semantic_weight: 0.75
      domain_lexical_weight: 0.40
      domain_semantic_weight: 0.60
      channel_pool_size: 5
```

Rules:

- lexical + semantic weight for each hybrid channel must sum to `1.0`
- disabling semantic alignment should keep the current lexical behavior available as a safe fallback

These settings must also be part of the admin-editable settings contract, not just static config.

### 8. Settings UI Contract

The admin settings UI should expose these as explicit `cv_analysis` tuning controls.

Recommended admin-visible settings:

- `cv_analysis.semantic_alignment.enabled`
- `cv_analysis.semantic_alignment.model`
- `cv_analysis.semantic_alignment.responsibility_lexical_weight`
- `cv_analysis.semantic_alignment.responsibility_semantic_weight`
- `cv_analysis.semantic_alignment.domain_lexical_weight`
- `cv_analysis.semantic_alignment.domain_semantic_weight`
- `cv_analysis.semantic_alignment.channel_pool_size`

UI expectations:

- responsibility weights and domain weights should be shown as paired controls with clear “must sum to 1.0” guidance
- the UI copy should explain that:
  - lexical weight rewards explicit wording and tag matches
  - semantic weight rewards meaning-based similarity when wording differs
- validation should block invalid weight pairs rather than silently normalizing them
- the settings-used snapshot and `cv_analysis` artifact should expose the effective hybrid-weight values used for the run

Suggested placement:

- either a new `CV Analysis Alignment` section
- or a dedicated subsection under retrieval settings

This rollout therefore changes both runtime scoring behavior and the admin settings surface owned by `settings_system`.

## Concrete Example

### Current behavior

Job:

```text
Domain: retail banking
Responsibility: Translate raw data into recommendations for stakeholders
```

Candidate evidence A:

```text
Built executive dashboards and reporting used by leadership for pricing decisions.
```

Candidate evidence B:

```text
Maintained SQL cleanup scripts for internal datasets.
```

Today:

- A may under-score on responsibility and domain because wording differs
- B may look competitive because it contains explicit technical words

### Upgraded behavior

Domain channel:

- A gets a strong semantic domain score because leadership reporting and pricing decisions are close to banking/analytics business work
- B gets weak domain support

Responsibility channel:

- A gets a strong semantic responsibility score because it supports stakeholder-facing decision-making from analytics output
- B gets weak responsibility support

Final top-k:

- A is selected first because it covers stakeholder-facing responsibility and domain context
- B is selected only if additional technical support is still needed

This gives a more realistic evidence bundle for CV writing.

## Risks

- semantic scoring could over-generalize weakly related evidence if weights are too semantic-heavy
- embedding reuse adds persistence complexity to `cv_analysis`
- new debug detail may increase artifact size if not bounded

## Rollout Notes

Recommended rollout order:

1. add stage-owned candidate evidence embeddings to `cv_analysis`
2. add hybrid scoring to:
   - `domain_alignment`
   - `responsibility_alignment`
3. expose debug subscores and reuse state
4. tune final top-k coverage bonuses if needed

Do not start with an LLM reranker.

Embeddings provide the strongest first upgrade while keeping the stage:

- cheaper
- more deterministic
- easier to debug

## Acceptance Criteria

1. `required_skill_support` remains deterministic and unchanged in principle.
2. `role_alignment` remains lightweight and bounded in principle.
3. `domain_alignment` and `responsibility_alignment` can score semantically similar evidence higher even when lexical overlap is weak.
4. `cv_analysis` may reuse candidate evidence embeddings, but only as a stage-owned capability.
5. Final top-k selection stays bounded and coverage-aware rather than becoming a second semantic reranker.
6. Artifacts and debug outputs can show lexical vs semantic subscores plus reuse state.
7. The settings contract exposes explicit hybrid-weight controls with safe defaults.
