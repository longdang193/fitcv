---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Improve ranking quality by redesigning the reranker rubric, replacing lexical title matching with semantic role alignment, introducing weighted preference scoring, and making score contributions and calibration more explicit."
invariants:
  - "The runtime ranking contract remains the same six features: `ai_score`, `must_have_match`, `vector_similarity`, `title_relevance`, `seniority_fit`, and `preference_fit`."
  - "`must_have_match` remains job-driven required-skill coverage and is not redesigned in this slice."
  - "Ranking remains the sole owner of authoritative post-filter fit labels and final ranked selection."
  - "Preference signals remain softer than hard requirement coverage and must not outweigh major required-skill gaps by default."
  - "Ranking artifacts must stay explainable enough for an operator to understand why one job outranked another."
---

# Ranking Quality Tuning Spec

## Affected Feature Contracts

- `docs/features/cv_system/cv_system.yaml`
- `docs/features/settings_system/settings_system.yaml`
- `docs/features/inspection_debugging/inspection_debugging.yaml`

## Stage Contracts

- `docs/stages/ranking.yaml`

## Triage

Feature type: MODIFY  
Summary: Improve ranking quality by tightening reranker scoring instructions, upgrading title matching to semantic role alignment, expanding preference scoring into weighted domain or role-family or location alignment, and exposing clearer score contributions and calibration surfaces.  
Reasoning: The ranking stage already uses the intended six-feature runtime contract, but several high-impact features are still too shallow. `ai_score` uses a broad rubric, `title_relevance` is lexical token overlap, and `preference_fit` treats all preference categories equally while overloading domains and role-family semantics. These are modifications to existing ranking behavior, settings, and inspection surfaces centered on the ranking stage.  
Invariants:
- The six-feature ranking contract stays intact.
- `must_have_match` stays unchanged in this slice.
- Ranking remains explainable through bounded artifacts and run inspection.
- Fit-label thresholds remain explicit configuration or code-owned policy rather than hidden prompt behavior.
- Preference alignment remains a soft ranking signal rather than a hard filter in ranking.
Dependencies:
- `cv_system`
- `settings_system`
- `inspection_debugging`
- `ranking` stage contract
- candidate profile preferences contract
- reranker prompt contract in `src/fitcv/ai_score.py`
Affected stages:
- `ranking`
Affected features:
- `cv_system`
- `settings_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml:
    - `docs/features/cv_system/cv_system.yaml`
    - `docs/features/settings_system/settings_system.yaml`
    - `docs/features/inspection_debugging/inspection_debugging.yaml`
  feature_history:
    - `docs/features/cv_system/history.md`
    - `docs/features/settings_system/history.md`
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
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Problem Statement

The six-feature ranking contract is active, but three of its most important quality levers are still shallow:

1. `ai_score` depends on a reranker rubric that is directionally correct but too vague about factor priority, evidence quality, and how to handle conflicting signals.
2. `title_relevance` uses token overlap between the candidate target role and the job title, which underestimates semantically close role titles.
3. `preference_fit` uses a coarse fractional match over domains and location types, while candidate preferences do not yet separate `domains` from `role_families`.

In addition, operators still lack a clean explanation of:

- how much each feature actually contributed to `final_score`
- why one ranked job beat another nearby job
- how weight and fit-label thresholds should be calibrated after feature-quality changes

This means ranking can be numerically stable while still being qualitatively weak or difficult to tune.

## Goals

- Improve `ai_score` consistency and grounding through a stricter reranker rubric.
- Replace lexical `title_relevance` with semantic role alignment while keeping the feature interpretable and bounded.
- Replace coarse equal-category `preference_fit` with a weighted preference model that separates domain, role-family, and location alignment.
- Make ranking artifacts and run inspection show clearer per-feature contribution detail.
- Add an explicit calibration surface for ranking weights and fit-label thresholds.

## Non-Goals

- Redesigning `must_have_match` in this slice.
- Changing shortlist retrieval logic or reranker execution scope.
- Making preference alignment a hard filter inside ranking.
- Introducing a new seventh ranking feature.
- Rewriting historical ranking artifacts or scores.

## Current Behavior Summary

### `ai_score`

The reranker prompt in `src/fitcv/ai_score.py` instructs the model to:

- heavily weight required skills
- penalize missing core tech, seniority mismatch, and years-of-experience gap
- reward project evidence and domain relevance

This is useful but underspecified. It does not strongly define:

- primary vs secondary factors
- what should cap a score
- what evidence is strong enough for `strong`
- how to behave when evidence is ambiguous

### `title_relevance`

`title_relevance` in `src/fitcv/ranking.py` is token overlap between:

- candidate target role
- job title

This is cheap and explainable, but brittle. Semantically adjacent titles can score lower than they should.

### `preference_fit`

`preference_fit` in `src/fitcv/ranking.py` currently:

- checks candidate `preferences.domains`
- checks candidate `preferences.location_types`
- treats domain and location as equally weighted categories
- uses `preferences.domains` as a loose proxy for both `job.domain` and `job.job_family`

This is directionally useful but too coarse to model nuanced preference alignment.

### Contribution Visibility

Ranking artifacts expose feature values and weights, but they do not yet provide a compact explanation of:

- weighted contribution per feature
- nearby-job comparison context
- whether a low-ranked job lost mainly on `ai_score`, `title_relevance`, or preference mismatch

### Calibration

Weights exist in settings, and fit labels exist in reranker output, but there is no explicit ranking-quality calibration contract tying together:

- improved reranker semantics
- deterministic feature shifts
- final weight adjustments
- fit-label threshold interpretation

## Decision

Modify ranking quality in five coordinated but bounded ways:

1. redesign the reranker rubric
2. replace lexical `title_relevance` with semantic role alignment
3. upgrade `preference_fit` to a weighted model with separate domain, role-family, and location signals
4. expose per-feature contribution visibility in ranking artifacts and inspection surfaces
5. define explicit weight and threshold calibration guidance as part of the ranking contract

Keep `must_have_match` unchanged for now.

## Proposed Changes

## 1. Reranker Rubric Redesign

The reranker prompt should become a stricter ranking policy rather than a broad judging instruction.

### Desired Rubric Behavior

The reranker should treat factors in this order:

1. required-skill coverage and evidence quality
2. seniority and practical readiness
3. role alignment
4. preference alignment such as domain and location

Preference signals must remain secondary. They should not outweigh major required-skill gaps.

### Rubric Requirements

The rubric should explicitly define:

- what counts as strong evidence
- what kinds of gaps should materially reduce score
- what should prevent a `strong` fit label
- how to behave when the evidence is incomplete or ambiguous

### Expected Semantic Policy

The reranker should follow rules like:

- Do not give `strong` when multiple core required skills appear unsupported.
- Prefer conservative scoring when evidence is weak or indirect.
- Domain or location preference alignment can improve a close comparison, but should not rescue a fundamentally weak match.
- Nice-to-have signals should not dominate required-skill coverage.

### Output Contract

The existing structured output can remain, but the reasoning fields should be grounded against explicit requirement evidence and explicit gap evidence rather than generic prose.

## 2. Semantic `title_relevance`

`title_relevance` should stop being token overlap and become semantic role alignment.

### Desired Meaning

`title_relevance` should answer:

> How semantically aligned is this job title with the candidate's target role?

### Proposed Inputs

- candidate target role from the profile
- job title from the structured job
- optional enriched `job_family` as a supporting fallback signal

### Scoring Semantics

Use a bounded semantic alignment score in `[0.0, 1.0]`:

- `1.0`: same or near-equivalent role
- `0.5`: partially aligned or ambiguous
- `0.0`: clearly different role

The implementation may use an LLM-backed classifier, a curated semantic-role normalization layer, or a hybrid approach, but the exposed runtime feature remains a bounded scalar named `title_relevance`.

### Guardrails

- It should remain independent from `preference_fit`.
- It should describe role alignment, not domain alignment.
- It should not silently become a second holistic AI score.

## 3. Weighted `preference_fit`

`preference_fit` should become a weighted preference model instead of a plain category average.

### Candidate Preference Contract

Separate these candidate-side preference fields:

- `preferences.domains`
- `preferences.role_families`
- `preferences.location_types`

This avoids overloading `domains` to also stand in for role family.

### Job-Side Inputs

Use:

- `job.domain`
- `job.job_family`
- `job.location_type`

### Weighted Preference Formula

`preference_fit` becomes a weighted sum of sub-scores:

```text
preference_fit =
  domain_score * domain_weight +
  role_family_score * role_family_weight +
  location_type_score * location_type_weight
```

Each sub-score uses bounded semantics:

- `1.0` = explicit match
- `0.5` = no explicit preference / neutral
- `0.0` = explicit mismatch

### Default Weighting Direction

Initial design should support config-driven weights, with a likely default direction such as:

- domain: highest
- role_family: medium
- location_type: lowest

Exact defaults belong to implementation planning and calibration, but the spec direction is that location should not automatically count the same as domain.

## 4. Contribution Visibility

Ranking artifacts and inspection should expose how the final score was built, not just the raw feature values.

### Desired Visibility

For scored rows, show:

- raw feature values
- effective weights
- weighted contribution per feature
- `final_score`

### Example Artifact Shape

```json
{
  "job_url": "...",
  "ai_score": 0.78,
  "must_have_match": 0.80,
  "vector_similarity": 0.74,
  "title_relevance": 0.92,
  "seniority_fit": 1.0,
  "preference_fit": 0.60,
  "feature_contributions": {
    "ai_score": 0.312,
    "must_have_match": 0.160,
    "vector_similarity": 0.111,
    "title_relevance": 0.092,
    "seniority_fit": 0.100,
    "preference_fit": 0.030
  },
  "final_score": 0.805
}
```

### Comparison Visibility

Ranking inspection should make it easier to see why one nearby job outranked another by surfacing the largest deltas rather than forcing the operator to mentally recompute them from raw values.

## 5. Weight and Threshold Calibration

This ranking-quality change needs an explicit calibration contract.

### Weight Calibration

After feature-quality changes, operators should be able to tune weights with an understanding of:

- what each feature now means
- which features are primary vs secondary
- how much the reranker already captures holistically

This requires updated settings descriptions and ranking docs.

### Fit-Label Calibration

The system should explicitly define how `strong`, `stretch`, and `skip` relate to:

- reranker output behavior
- score ranges
- evidence quality expectations

This does not require moving fit-label authority away from ranking. It means the thresholds and prompt semantics should be calibrated together rather than independently drifting.

## Expected Runtime Semantics After Change

The six-feature final score remains:

```text
final_score =
weight(ai_score) * ai_score
+ weight(must_have_match) * must_have_match
+ weight(vector_similarity) * vector_similarity
+ weight(title_relevance) * title_relevance
+ weight(seniority_fit) * seniority_fit
+ weight(preference_fit) * preference_fit
```

But the feature meanings become stronger:

- `ai_score`: stricter, more grounded reranker judgment
- `must_have_match`: unchanged job-required-skill coverage
- `vector_similarity`: unchanged shortlist retrieval closeness
- `title_relevance`: semantic role alignment
- `seniority_fit`: unchanged ladder closeness
- `preference_fit`: weighted domain or role-family or location alignment

## Compatibility and Migration Notes

- Historical ranking artifacts remain valid and are not rewritten.
- Newly generated artifacts may need new ranking decision-summary or row fields to expose contribution visibility and richer preference inputs.
- Candidate profile contracts may need an additive change to support `preferences.role_families`.
- Existing profiles without `role_families` should remain valid and default that dimension to neutral.

## Risks

### Rubric Drift Risk

Improving the reranker rubric without enough guardrails could make the LLM score feel less stable rather than more stable.

Mitigation:

- keep the output schema unchanged or minimally changed
- make factor priority explicit
- test against representative ranking comparisons

### Feature Entanglement Risk

Semantic `title_relevance` and richer `preference_fit` could overlap conceptually if role, family, and domain are not separated cleanly.

Mitigation:

- define role alignment and preference alignment as distinct semantics
- separate candidate `role_families` from `domains`

### Explainability Risk

A stronger model can become harder to reason about if contribution visibility is not added at the same time.

Mitigation:

- treat contribution visibility as part of the same rollout, not a later cleanup

## Verification Requirements

Implementation should prove:

1. `must_have_match` remains unchanged in runtime behavior.
2. The reranker rubric becomes stricter and better grounded while keeping structured outputs stable.
3. `title_relevance` no longer relies only on token overlap.
4. `preference_fit` uses separate domain, role-family, and location inputs with explicit weighting.
5. Ranking artifacts expose per-feature contribution detail.
6. Settings and docs explain weight and fit-label calibration in current-state terms.

## Handoff

If approved, the implementation plan should be organized into these workstreams:

1. reranker rubric redesign and prompt provenance updates
2. semantic `title_relevance`
3. weighted `preference_fit` plus candidate preference contract extension
4. ranking artifact and run-detail contribution visibility
5. settings and threshold calibration sync
