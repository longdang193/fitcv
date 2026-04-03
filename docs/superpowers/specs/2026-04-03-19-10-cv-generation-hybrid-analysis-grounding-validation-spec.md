---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Upgrade `cv_generation` validation from profile-grounded checks to a hybrid model that validates hard facts deterministically against selected `cv_analysis` evidence and uses bounded semantic validation for softer responsibility/domain claims."
invariants:
  - "`cv_analysis` remains the sole owner of evidence retrieval, final evidence selection, and fit-gate decisions."
  - "`cv_generation` validation must stay bounded and must not silently rerun evidence retrieval."
  - "Hard facts must be validated deterministically against the selected evidence bundle whenever possible."
  - "Semantic validation is limited to soft claims such as responsibility and domain alignment, not basic fact extraction."
  - "Backward compatibility with older `cv_analysis` records that only expose flatter evidence payloads must be preserved."
---

# CV Generation Hybrid Analysis-Grounded Validation

## Why

Current `cv_generation` validation is still profile-grounded rather than analysis-grounded.

Today, validation in [`validator.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/validator.py) checks:

- employer names against the full candidate profile
- project names against the full candidate profile
- skills in the Skills section against the full candidate profile

That means a generated CV can pass validation even when it is not well-supported by the specific evidence bundle selected by `cv_analysis` for that job.

Example:

- `cv_analysis` selects retail-reporting evidence for a banking analyst job
- `cv_generation` writes a strong fraud-detection or streaming claim taken from some other true part of the candidate profile
- current validation may still pass because the claim is profile-true
- but it is not analysis-grounded for this job

This spec upgrades validation so it answers the stronger question:

> “Is this claim grounded by the specific selected evidence bundle for this job?”

without turning validation into a second full analysis stage.

## Feature and Stage Alignment

Feature type: `MODIFY`

Summary:
- upgrade final-stage validation so `cv_generation` checks claims against the selected `cv_analysis` evidence bundle, using deterministic checks for hard facts and bounded semantic validation for soft alignment claims

Reasoning:
- this is an existing `cv_system` behavior change rather than a new feature family
- the work is stage-heavy because it changes the `cv_analysis -> cv_generation -> validator` boundary

Affected stages:

- `cv_analysis`
- `cv_generation`

Affected features:

- `cv_system`
- `inspection_debugging`

Primary lens:

- `mixed`

Affected docs:

- feature_yaml: [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/cv_system.yaml)
- feature_history: [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/history.md)
- feature_docs: none
- cross_cutting_docs:
  - [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/FitCV-pipeline.md)
- readme: none
- generated:
  - [feature_overview.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/feature_overview.md)
  - [features_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/features_index.yaml)
  - [feature_capabilities_index.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/generated/feature_capabilities_index.yaml)

Generated refresh required:

- yes

Spec needed:

- yes

Plan needed:

- yes

Risk level:

- medium

Migration needed:

- no

## Current Problem

Current validation is good at checking:

- invented employers
- invented project names
- unsupported skills in the Skills section
- structural completeness

But it is still weak at checking whether the final CV stayed inside the selected job-specific evidence bundle.

That leaves a gap between:

- what `cv_analysis` decided should support the job
- what `cv_generation` is actually allowed to claim

The weakest area is soft claims such as:

- responsibility alignment
- domain familiarity
- role-positioning language

Pure deterministic validation works well for hard facts, but it struggles when the generated wording is semantically close but lexically different from the selected evidence.

## Goals

The upgraded validation should:

- validate hard facts against the selected evidence bundle, not only the full profile
- preserve deterministic validation for bounded, high-confidence fact checks
- add semantic validation only where deterministic matching is known to be weak
- keep runtime bounded and stage-correct
- expose enough validator provenance in `cv_generation` artifacts for debugging

## Non-Goals

This slice does not:

- rerun evidence retrieval in `cv_generation`
- move ownership away from `cv_analysis`
- turn the validator into a free-form LLM reviewer for the whole CV
- attempt full hallucination-proof validation of all narrative wording

## Proposed Design

### 1. Split Validation Into Two Classes

#### A. Deterministic Analysis-Grounded Validation

Use deterministic checks for hard facts derived from the selected evidence bundle.

Examples:

- employers
- project names
- explicit skills
- selected evidence identities

These checks answer:

- is this fact present in the selected evidence?
- if not, is it only present elsewhere in the profile?

If it is only profile-grounded and not selected-evidence-grounded, flag it.

#### B. Semantic Analysis-Grounded Validation

Use bounded semantic validation for softer claims where lexical matching is weak.

Examples:

- responsibility alignment
- domain familiarity statements
- role-positioning phrases derived from selected evidence

These checks answer:

- is this generated phrase semantically supported by the selected evidence bundle?

This semantic path should be limited to:

- selected evidence bullet/highlight text
- selected `responsibility_themes`
- selected `domain_tags`
- selected role-family/role context

### 2. Add an Explicit Validation Input Contract

`cv_generation` should pass a bounded analysis-grounding payload into validation.

Minimum contract:

- `evidence_used`
- `evidence_selection_summary`
- compact `analysis_input_summary`
- optional selected evidence raw snippets already carried in `evidence_payload`

The validator must not inspect full checkpoint state directly.

### 3. Build an Allowed Facts Surface From Selected Evidence

Before validation, derive deterministic allowed facts from the selected evidence bundle.

Examples:

- allowed employers
- allowed project names
- allowed canonical skills
- allowed role families
- allowed domain tags
- allowed responsibility themes

This becomes the deterministic fact surface for `cv_generation`.

### 4. Use Hybrid Claim Validation Rules

#### Hard-fact rules

Use deterministic validation for:

- employer mentions
- project mentions
- explicit skill claims

Expected behavior:

- exact or canonical match against selected evidence -> pass
- only found elsewhere in profile -> fail as analysis-grounding violation

#### Soft-claim rules

Use a semantic path for:

- responsibility-like bullets
- domain-familiarity claims
- role-positioning text

Expected behavior:

- deterministic theme/tag alias match -> pass directly
- otherwise run bounded semantic comparison against selected evidence text and themes
- fail only when both deterministic and semantic checks find insufficient support

### 5. Bounded Semantic Validator

The semantic validator should remain narrow.

Recommended phase-1 behavior:

- compare generated soft claims only against the selected evidence bundle
- use embeddings similarity or a small structured LLM check
- never validate the whole CV with a general-purpose rubric
- return compact support decisions, not long prose

Preferred output shape:

```json
{
  "claim_text": "Delivered stakeholder-facing dashboards and reporting workflows.",
  "claim_type": "responsibility_alignment",
  "supported": true,
  "support_source": "semantic",
  "matched_evidence_ids": ["exp_retail_1"],
  "matched_themes": ["dashboarding", "stakeholder_reporting"]
}
```

## Concrete Examples

### Example 1: Deterministic Hard-Fact Validation

Selected evidence:

```json
[
  {
    "evidence_id": "exp_retail_1",
    "company": "RetailCo AG",
    "skills": ["SQL", "Power BI", "Python"]
  }
]
```

Generated bullet:

```text
Built KPI dashboards with SQL and Power BI.
```

Validation:

- `SQL` in selected evidence skills -> pass
- `Power BI` in selected evidence skills -> pass

Outcome:

- analysis-grounded

Bad bullet:

```text
Built Kafka streaming pipelines for fraud detection.
```

Validation:

- `Kafka` not in selected evidence skills
- `fraud detection` not in selected evidence context

Outcome:

- fail deterministic analysis-grounding

### Example 2: Hybrid Soft-Claim Validation

Selected evidence:

```json
[
  {
    "evidence_id": "exp_retail_1",
    "responsibility_themes": ["dashboarding", "stakeholder_reporting"],
    "bullets": [
      "Maintained Power BI dashboards for sales and inventory reporting"
    ]
  }
]
```

Generated bullet:

```text
Delivered stakeholder-facing dashboards and reporting workflows.
```

Deterministic path:

- `dashboarding` theme matches `dashboards`
- `stakeholder_reporting` theme matches `stakeholder-facing reporting`

Outcome:

- pass without semantic fallback

Generated bullet:

```text
Enabled cross-functional business communication around KPI performance.
```

Deterministic path:

- weak lexical overlap

Semantic path:

- compare generated phrase with selected bullet text and selected themes
- semantic support is close to `stakeholder_reporting`

Outcome:

- pass via bounded semantic validation

## Artifact and Debugging Changes

`cv_generation` artifacts should expose:

- deterministic analysis-grounding violations
- semantic analysis-grounding violations
- whether a claim passed via deterministic or semantic support
- compact matched evidence IDs and matched themes when available

This should make final-stage debugging answer:

- what was generated
- what evidence bundle was selected
- why the validator accepted or rejected the claim

## Compatibility

Older `cv_analysis` records may lack:

- `matched_channels`
- `selection_reasons`
- richer `analysis_input_summary`

Compatibility behavior:

- deterministic hard-fact validation still works from whatever selected evidence payload exists
- semantic validation degrades gracefully when richer tags/themes are absent
- no run should fail simply because an older analysis record used the flatter contract

## Rollout Strategy

Recommended rollout:

1. deterministic selected-evidence grounding for hard facts
2. bounded semantic validation for soft claims
3. artifact/debug additions
4. threshold tuning after observing real runs

## Risks

- semantic validation can become too expensive or too broad if it is allowed to inspect the whole CV or full profile
- over-strict deterministic checks can reject valid paraphrases
- under-specified selected evidence payloads can reduce semantic validator usefulness

Mitigations:

- keep semantic validation scoped to selected evidence only
- keep hard-fact checks deterministic
- keep artifact/debug outputs explicit so tuning is observable

## Acceptance Criteria

This work is successful when:

- `cv_generation` validation can distinguish profile-grounded claims from selected-evidence-grounded claims
- hard facts are validated deterministically against the selected evidence bundle
- soft responsibility/domain claims can pass through bounded semantic validation when lexically different but semantically supported
- unsupported soft claims fail when neither deterministic nor semantic support is found
- `cv_generation` artifacts make deterministic-versus-semantic support visible enough for debugging
- older `cv_analysis` records remain consumable through a compatibility path
