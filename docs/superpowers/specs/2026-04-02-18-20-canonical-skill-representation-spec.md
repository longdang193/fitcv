---
feature_type: modify
feature_name: none
status: draft
summary: "Redefine canonical skill representation so enrich emits LLM-normalized skill entities only for required and preferred skills, not lowercased requirement prose."
invariants:
  - Raw enrich outputs for `required_skills` and `preferred_skills` must remain preserved exactly as extracted.
  - Canonical skill outputs must represent actual skills, not lowercased requirement sentences.
  - Canonical skill normalization applies only to `required_skills` and `preferred_skills` in this rollout.
  - Non-skill requirement content such as degrees, years, languages, and soft traits must not be mislabeled as canonical skills.
---

# Canonical Skill Representation

## Triage

Feature type: MODIFY  
Summary: Replace the current pseudo-canonical skill fields with LLM-backed canonical skill entities for `required_skills` and `preferred_skills` only.  
Reasoning: The current enrich output labels lowercased requirement prose as “canonical”, which is materially misleading and causes poor downstream matching and debugging. This is a contract correction inside the existing enrich and downstream interpretation pipeline, not a new feature area.  
Invariants:
- Raw enrich extraction must remain available and auditable.
- Canonical skill outputs must contain skill concepts, not free-form requirement sentences.
- The enrich contract must clearly separate raw requirement items from normalized skill entities.
- Rule filter and ranking must consume canonical skill outputs only where that representation is trustworthy.
Dependencies:
- `src/fitcv/enrich.py`
- `config/skill_synonyms.yaml`
- downstream consumers in `rule_filter`, `ranking`, and related debug artifacts
Affected stages:
- `enrich`
- `rule_filter`
- `ranking`
- `cv_generation`
Affected features:
- none
Primary lens: stage
Affected docs:
- feature_yaml: `none`
- feature_history: `none`
- feature_docs:
  - `none`
- cross_cutting_docs:
  - `docs/FitCV-pipeline.md`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/ranking.yaml`
- readme: `none`
- generated:
  - `none`
Generated refresh required: no
Spec needed: yes
Plan needed: yes

## Problem

The current canonicalization behavior is not actually canonical skill normalization.

Today, long raw requirement items such as:

- `proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)`
- `at least 5 years of hands-on data science experience with proven business impact`
- `English advanced (C1) or above`

can appear in `required_skills_canonical` after only light deterministic cleanup:

- lowercasing
- trimming
- exact synonym-map replacement when the entire phrase matches

This creates bad outputs like:

```json
"required_skills_canonical": [
  "proficient in python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
  "at least 5 years of hands-on data science experience with proven business impact",
  "english advanced (c1) or above"
]
```

These values are not canonical skills. They are requirement sentences relabeled as canonical terms.

As a result:

- `required_skills_canonical` and `preferred_skills_canonical` are misleading
- downstream matching quality is poor
- debug artifacts are confusing
- ranking and filtering can inherit noisy skill signals

## Goals

- Keep `required_skills` and `preferred_skills` as raw extracted requirement items.
- Introduce a canonical representation that contains actual normalized skill concepts.
- Make canonical normalization LLM-backed, because enrich itself is already LLM-based and the task is semantic.
- Restrict this rollout to `required_skills` and `preferred_skills` only.
- Exclude non-skill requirement content from canonical skill outputs.

## Non-Goals

- Canonicalizing every enrich list field.
- Treating `responsibilities`, `tech_stack`, or `keywords` as canonical-skill sources in this rollout.
- Auto-updating the trusted synonym map from one run.
- Redesigning domain, seniority, or location normalization here.

## Current-State Summary

The current enrich flow does two separate things:

1. LLM extraction:
- produces raw list fields like `required_skills` and `preferred_skills`

2. Deterministic post-processing:
- lowercases extracted items
- applies exact alias-to-canonical replacements from `skill_synonyms.yaml`

This deterministic step is acceptable for:

- `GCP` -> `google cloud`
- `PowerBI` -> `power bi`

It is not acceptable for:

- long skill bundles
- degree requirements
- experience requirements
- language requirements
- mixed phrases containing several skills

The core mistake is that the current contract canonicalizes extracted requirement items, not extracted skills.

## Proposed Design

## 1. Separate Raw Requirement Items From Canonical Skill Entities

The enrich contract for skill-bearing fields should have two distinct layers:

### Raw requirement items

These remain the original LLM-extracted list items:

- `required_skills`
- `preferred_skills`

They are intentionally raw and may contain:

- single skills
- multi-skill bundles
- degree requirements
- years-of-experience requirements
- language requirements
- soft expectations

### Canonical skill entities

These are the normalized downstream-facing outputs:

- `required_skill_entities`
- `preferred_skill_entities`

Each entity represents one actual skill concept extracted from a raw requirement phrase.

Proposed shape:

```json
{
  "raw_text": "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
  "canonical": "python",
  "confidence": 0.96
}
```

If one raw phrase contains multiple real skills, it should produce multiple entities:

```json
[
  {
    "raw_text": "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
    "canonical": "python",
    "confidence": 0.96
  },
  {
    "raw_text": "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
    "canonical": "pandas",
    "confidence": 0.94
  },
  {
    "raw_text": "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
    "canonical": "scikit-learn",
    "confidence": 0.93
  }
]
```

This makes the contract about skill concepts, not sentence normalization.

## 2. Make Canonical Normalization LLM-Backed

Canonical skill normalization should be performed by the LLM as part of enrich-stage interpretation for `required_skills` and `preferred_skills`.

The model should be asked to:

- preserve the raw extracted requirement item
- identify whether the item contains any actual skills
- emit one normalized entity per skill found
- omit non-skill content from the canonical skill entity list
- return confidence for each entity

This is preferable to synonym-only cleanup because the task is semantic:

- `Python programming for data science` implies `python`
- `SQL and database operations` implies `sql`
- `experience with GenAI technologies (LLMs, RAG, prompt engineering, vector databases)` may imply multiple distinct skills

The current deterministic lowercasing step cannot do this correctly.

## 3. Redefine `*_canonical` As Flattened Skill Labels Derived From Entities

If flattened canonical lists are still needed for downstream convenience, they should be derived from the canonical entities, not from raw requirement-item lowercasing.

So:

- `required_skills_canonical`
- `preferred_skills_canonical`

should mean:

- unique flattened canonical skill labels extracted from the corresponding entity list

Example:

```json
"required_skills_canonical": [
  "python",
  "pandas",
  "numpy",
  "sql",
  "mlops"
]
```

This field should no longer contain:

- degrees
- experience-duration phrases
- languages
- soft traits
- long prose requirements

## 4. Explicitly Exclude Non-Skill Requirement Content

Canonical skill normalization must not emit entities for requirement phrases that are not skills.

Examples that should not appear in canonical skill outputs:

- `Master's or PhD Degree in Data Science...`
- `at least 5 years of hands-on data science experience...`
- `English advanced (C1) or above`
- `ready to learn new methods`
- `able to switch between tasks and topics quickly`

These may remain in raw extracted requirement lists, but they should not become canonical skills.

If useful later, they can be handled by separate enrich outputs such as:

- `qualification_requirements`
- `language_requirements`
- `experience_requirements`

That separation is out of scope for this rollout, but this spec reserves the distinction.

## 5. Keep Synonym Maps As Support, Not As The Main Canonicalizer

The trusted synonym map still has value, but as a support layer:

- standard alias cleanup
- conflict reduction
- post-normalization stabilization

It should not be responsible for inventing semantics out of long free-form requirement text.

Recommended role of `skill_synonyms.yaml` after this change:

- normalize common aliases to the project’s chosen canonical labels
- support light cleanup after LLM normalization
- remain the trusted reviewed vocabulary layer

Not its role:

- extract skills from requirement sentences
- decide whether a phrase is a skill at all

## 6. Downstream Contract

After this change, downstream stages should interpret the enrich contract like this:

### `rule_filter`

- if it needs skill-based logic, prefer `required_skills_canonical` and `preferred_skills_canonical`
- never infer skill canonicals from raw requirement prose on its own

### `ranking`

- use flattened canonical skill lists derived from entities
- not raw lowercased requirement items

### `cv_generation`, `gap_analysis`, and related debug surfaces

- continue to inspect raw `required_skills` / `preferred_skills`
- use canonical skill entities when comparing actual skill overlap

## Data Contract

## Raw fields kept

```json
{
  "required_skills": ["raw requirement item 1", "raw requirement item 2"],
  "preferred_skills": ["raw preferred item 1", "raw preferred item 2"]
}
```

## Canonical fields redefined

```json
{
  "required_skills_canonical": ["python", "sql", "mlops"],
  "preferred_skills_canonical": ["power bi", "airflow"]
}
```

## Entity fields

```json
{
  "required_skill_entities": [
    {
      "raw_text": "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
      "canonical": "python",
      "confidence": 0.96
    }
  ],
  "preferred_skill_entities": [
    {
      "raw_text": "PowerBI",
      "canonical": "power bi",
      "confidence": 0.99
    }
  ]
}
```

## Mapping suggestions

`mapping_suggestions` remains a reviewable artifact, but it should be derived only from meaningful alias-to-canonical cases inside the skill entity normalization path.

That means suggestions are appropriate for:

- `gcp` -> `google cloud`
- `powerbi` -> `power bi`

They are not appropriate for:

- `proficient in Python programming for data science (...)` -> `python`

because that is an extraction/normalization result, not a reusable synonym-map entry.

## Example

### Raw enrich extraction

```json
"required_skills": [
  "Master's or PhD Degree in Data Science, Statistics, Mathematics, Computer Science, or related quantitative field",
  "at least 5 years of hands-on data science experience with proven business impact",
  "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
  "proficient in SQL and database operations for data manipulation and analysis",
  "good understanding of MLOps practices and model deployment workflows",
  "English advanced (C1) or above"
]
```

### Desired canonical result

```json
"required_skills_canonical": [
  "python",
  "pandas",
  "numpy",
  "scikit-learn",
  "sql",
  "mlops"
],
"required_skill_entities": [
  {
    "raw_text": "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
    "canonical": "python",
    "confidence": 0.96
  },
  {
    "raw_text": "proficient in Python programming for data science (pandas, numpy, scipy, scikit-learn, statsmodels)",
    "canonical": "pandas",
    "confidence": 0.94
  },
  {
    "raw_text": "proficient in SQL and database operations for data manipulation and analysis",
    "canonical": "sql",
    "confidence": 0.95
  },
  {
    "raw_text": "good understanding of MLOps practices and model deployment workflows",
    "canonical": "mlops",
    "confidence": 0.92
  }
]
```

Notice that the following raw requirement items remain visible but do not become canonical skills:

- degree requirements
- years-of-experience requirements
- language requirements

## Acceptance Criteria

- `required_skills_canonical` and `preferred_skills_canonical` contain only actual canonical skill labels.
- Long requirement prose no longer appears in canonical skill fields.
- Canonical skill normalization is LLM-backed for `required_skills` and `preferred_skills`.
- `required_skill_entities` and `preferred_skill_entities` can represent multiple canonical skills from one raw phrase.
- Non-skill requirement content is excluded from canonical skill outputs.
- Mapping suggestions are limited to real reusable alias-to-canonical cases.

## Risks And Mitigations

## Cost Risk

LLM-backed canonical normalization increases enrich-stage cost and prompt complexity.

Mitigation:

- limit the new normalization path strictly to `required_skills` and `preferred_skills`
- keep other enrich fields raw in this rollout
- reuse the same enrich request when possible rather than adding a second round trip if the response schema can be extended cleanly

## Contract Migration Risk

Downstream logic may currently assume `*_canonical` exists for fields beyond required and preferred skills.

Mitigation:

- explicitly narrow the contract in code and docs
- keep downstream consumers focused on required/preferred canonical skill fields only

## Over-Normalization Risk

The model may over-extract broad concepts or normalize too aggressively.

Mitigation:

- require one entity per actual skill concept
- require confidence
- keep raw requirement items for auditability
- preserve the synonym map as a stabilizing vocabulary layer

## Open Questions

- Should confidence be stored on flattened `*_canonical` outputs, or only on entity rows?
- Should one raw phrase be allowed to emit many canonical entities without a cap, or should the prompt constrain output volume?
- Should future rollouts split non-skill requirement content into separate enrich fields rather than leaving it embedded in raw `required_skills` / `preferred_skills`?
