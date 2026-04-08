---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Keep grouped experience evidence intact while making Experience sections more JD-sensitive, less repetitive, and better tailored across runs."
invariants:
  - "CV generation must remain grounded in persisted candidate profile data."
  - "Structured CV generation remains the canonical semantic path."
  - "Grouped experience-entry preservation must not regress back to flat bullet reconstruction."
  - "Adaptive experience composition must not invent roles, dates, employers, or unsupported achievements."
  - "Prompt and render behavior must stay aligned with preset/composition/content rules."
---

# Adaptive Experience Composition Design

## Affected Feature Contract

- [`docs/features/cv_system/cv_system.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)

## Triage

Feature type: MODIFY  
Summary: Keep grouped experience evidence intact while making Experience composition more adaptive to the target JD and less repetitive across runs.  
Reasoning: This is a quality refinement of the existing CV generation system, not a new standalone feature. The prior experience-evidence work fixed structural shallowness; this follow-on work addresses over-deterministic experience composition.  
Invariants:
- CV generation remains grounded in the candidate profile and selected evidence.
- Structured CV generation remains the canonical semantic path.
- Grouped experience-entry preservation remains intact and should not regress.
- Prompt and render behavior must stay aligned with composition settings.
- Existing markdown and export flows remain supported.
Dependencies:
- `cv_system`
- recent grouped experience-evidence preservation work
- CV generation prompt assembly
Affected docs:
  feature_yaml: `docs/features/cv_system/cv_system.yaml`
  feature_history: `docs/features/cv_system/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - none
  readme: none
  generated:
    - none
Generated refresh required: no  
Spec needed: yes  
Plan needed: yes  
Risk level: medium

## Why We Came Up With This Spec

This spec came from debugging two real generated CV artifacts:

- [`cv_5b738397-50a2-4f57-ba60-395770d4bef9.md`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/cv_5b738397-50a2-4f57-ba60-395770d4bef9.md)
- [`cv_e88ca50e-566e-4d2d-9f4d-d3619b1a041c.md`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/cv_e88ca50e-566e-4d2d-9f4d-d3619b1a041c.md)

After the grouped experience-evidence fix, the Experience sections in those two files became almost identical.

That exposed a second problem:

- the earlier fix successfully stopped shallow one-role collapse
- but the Experience section now appears too deterministic
- the same roles and the same bullets are selected too often
- the model tends to restate those bullets rather than reframe them around the target JD

So the problem has shifted:

- before: Experience was too shallow because structure was lost
- now: Experience is structurally correct, but often too frozen to feel job-sensitive

This is not a rendering bug. It is a composition problem in how grouped experience evidence is selected, shaped, and framed before generation.

## Problem Statement

The CV system now preserves grouped experience structure well, but it does not adapt that structure enough to the target JD.

That causes three user-visible problems:

1. Experience sections can look nearly identical across different CV runs.
2. The same narrow bullet slice is selected too often, even when the target JD emphasizes different strengths.
3. The model often restates bullets literally instead of summarizing the same grounded facts with job-specific emphasis.

The system is currently optimized for stable grouped experience preservation, but not yet for adaptive experience composition.

## Current Behavior

Today, the experience path does the following:

1. Selects grouped `experience_entry` evidence.
2. Preserves role, company, dates, and a bounded set of bullets.
3. Passes those grouped blocks into the prompt.

That fixed the previous structural-loss bug, but it can still produce repetitive composition.

Example of the current style of input:

```text
Experience Entry
Role: Data Engineer
Company: Fintech Startup GmbH
Dates: 2021-06 to 2022-12
Relevant bullets:
- Built self-service Looker dashboards for product KPI monitoring, reducing ad-hoc reporting requests by 60%.
- Implemented real-time fraud detection features using BigQuery ML (random forest) on transaction streams.
```

If those same bullets are selected for different target jobs, the resulting Experience section often ends up nearly the same.

That means the current path is:

- structurally grounded
- but not yet adaptive enough in what it selects
- and not yet strong enough in how it asks the model to re-emphasize the same facts

## Design Goal

Keep grouped experience evidence intact while making the Experience section more adaptive to the target JD through better bullet selection, bounded supporting context, and stronger prompt guidance for grounded re-emphasis.

## Core Design Principle

Experience composition should become adaptive without becoming ungrounded.

That means:

- grouped `experience_entry` remains the primary construction evidence for the Experience section
- bullet selection inside each grouped role should become more JD-sensitive
- optional supporting evidence may reinforce a role when clearly related and grounded
- prompt instructions should encourage re-emphasis and summarization, not just bullet restatement

The goal is not to make Experience more random. The goal is to make it more responsive to the target job while staying grounded in the same underlying facts.

## Options Considered

### Option 1: Keep current grouped experience behavior

Accept the current output stability as a tradeoff for groundedness.

Pros:
- lowest risk
- preserves the gains from grouped experience preservation

Cons:
- Experience remains repetitive across runs
- JD-specific emphasis remains weak
- CVs can feel less tailored than they should

Verdict:
- not sufficient

### Option 2: Increase bullet count or model freedom only

Allow more bullets or loosen the prompt without changing selection semantics.

Pros:
- small implementation change
- may create somewhat more variation

Cons:
- can increase prompt noise without improving focus
- may not actually make selection more JD-sensitive
- risks trading repetition for verbosity

Verdict:
- partial mitigation only

### Option 3: Add adaptive experience composition on top of grouped experience preservation

Keep grouped experience entries, but make role-level bullet selection, supporting evidence, and prompt framing more JD-sensitive.

Pros:
- preserves the successful structural fix
- improves tailoring without requiring hallucinated reconstruction
- addresses repetition at the correct layer
- aligns with the structured CV model

Cons:
- requires changes across evidence shaping, prompt semantics, and regression coverage

Verdict:
- recommended

Example:

Current experience block:

```text
Experience Entry
Role: Data Engineer
Company: Fintech Startup GmbH
Dates: 2021-06 to 2022-12
Relevant bullets:
- Built self-service Looker dashboards for product KPI monitoring, reducing ad-hoc reporting requests by 60%.
- Implemented real-time fraud detection features using BigQuery ML (random forest) on transaction streams.
```

Current-style output:

```text
- Built self-service Looker dashboards for product KPI monitoring, reducing ad-hoc reporting requests by 60%.
- Implemented real-time fraud detection features using BigQuery ML (random forest) on transaction streams.
```

Proposed adaptive input for an analytics-focused JD:

```text
Experience Entry
Role: Data Engineer
Company: Fintech Startup GmbH
Dates: 2021-06 to 2022-12
Relevant bullets:
- Built self-service Looker dashboards for product KPI monitoring, reducing ad-hoc reporting requests by 60%.
- Automated KPI reporting workflows for product and analytics stakeholders.
- Implemented real-time fraud detection features using BigQuery ML (random forest) on transaction streams.
Supporting evidence:
- Achievement: reduced ad-hoc reporting requests by 60%
Instruction: emphasize analytics delivery, reporting automation, and measurable business impact while staying grounded in the evidence above.
```

Likely adaptive output:

```text
- Delivered KPI dashboards and reporting automation that improved access to product metrics and reduced manual reporting demand.
- Applied BigQuery ML in fraud-monitoring workflows while supporting analytics-driven decision-making.
```

The important change is not “more bullets.” It is that the same grounded role can be framed differently for different target jobs.

## Recommended Design

### 1. Keep grouped `experience_entry` as the primary construction evidence

The existing grouped experience design remains correct and should not be rolled back.

Adaptive experience composition should build on top of:

- role
- company
- dates
- grouped bullet context

This spec is about improving experience composition, not replacing grouped experience preservation.

### 2. Make bullet selection inside each experience entry more JD-sensitive

The selection layer should choose bullets within a role based on the target job’s priorities, not only on a generic relevance ranking that tends to pick the same small slice every time.

That means:

- the selected bullets for a role may differ across target jobs
- the bullet set should remain bounded
- the role/company/date grouping should remain intact

The goal is for the same role to support different emphasis when the JD changes.

### 3. Preserve bounded multi-bullet flexibility per role

The current path can feel too narrow if it always carries the same 2 bullets.

The adaptive path should:

- allow a bounded 2-3 bullet slice per role
- preserve enough variety to represent different strengths
- stay small enough to avoid prompt bloat

The exact count can remain configurable, but the first implementation should allow slightly richer per-role evidence than the current frozen-feeling slice.

### 4. Allow optional supporting evidence per role

Role composition may be reinforced by bounded supporting evidence when it is clearly related and grounded.

Examples of allowed supporting evidence:

- an achievement tightly tied to the same role
- a strongly related project that reinforces the same capability area

This supporting evidence should remain secondary to the grouped role block. It exists to enrich emphasis, not replace core work-history evidence.

### 5. Make Experience prompt instructions explicitly adaptive

The prompt should no longer only imply “turn these bullets into a CV.”

It should explicitly instruct the model to:

- use grouped experience evidence as canonical source material
- emphasize the bullets most relevant to the target JD
- summarize or combine grounded facts where helpful
- avoid inventing unsupported responsibilities, outcomes, or technologies

This encourages re-emphasis instead of literal bullet restatement.

### 6. Keep Experience section generation section-aware

The structured CV `experience` section should still be built primarily from grouped `experience_entry` evidence.

Projects and achievements may support the Experience section when explicitly allowed and grounded, but they must not replace grouped work-history as the main construction path.

### 7. Respect preset and composition controls

Adaptive experience composition must not override:

- section visibility rules
- per-section detail limits
- preset intent
- other composition constraints already enforced by the CV system

Richer adaptive experience should still be bounded by the same composition framework as the rest of the CV.

## Proposed Behavior

For Experience composition:

1. Retrieve grouped experience entries relevant to the job.
2. Select a bounded JD-sensitive bullet set within each chosen role.
3. Attach optional supporting evidence per role when clearly related and grounded.
4. Build a prompt that treats grouped role blocks as canonical evidence and explicitly asks for job-sensitive emphasis.
5. Generate structured CV JSON from that richer but still grounded input.
6. Render markdown from the structured CV as usual.

## Data Contract Direction

The grouped experience shape can remain the same at its core, but should allow role-level selected evidence such as:

```json
{
  "evidence_type": "experience_entry",
  "source_ref": "experiences[1]",
  "role": "Data Engineer",
  "company": "Fintech Startup GmbH",
  "start": "2021-06",
  "end": "2022-12",
  "bullets": [
    "Built self-service Looker dashboards for product KPI monitoring, reducing ad-hoc reporting requests by 60%.",
    "Implemented real-time fraud detection features using BigQuery ML on transaction streams.",
    "Automated KPI reporting workflows for product and analytics stakeholders."
  ],
  "supporting_evidence": [
    {
      "evidence_type": "achievement",
      "source_ref": "achievements[0]",
      "text": "Reduced ad-hoc reporting requests by 60%"
    }
  ]
}
```

This is illustrative rather than final, but the key requirement is:

- preserve grouped work-history
- allow JD-sensitive bullet choice
- allow bounded grounded support when appropriate

## Non-Goals

- rolling back grouped experience preservation
- replacing structured CV generation with a deterministic hand-written experience composer
- making Experience highly variable or stylistically random
- backfilling old generated CVs

## Risks

### Reintroducing shallow experience

If adaptive logic weakens grouped role structure, the system could drift back toward the original flattening problem.

### Prompt bloat

More bullets and role-level supporting evidence can make prompts too large if left unbounded.

### Overfitting to the JD

If adaptive emphasis becomes too aggressive, the model may over-compress the candidate’s history toward one narrow framing.

Mitigation:

- keep grouped roles intact
- use bounded bullet selection
- require grounding in actual evidence

### Experience-project overlap

If supporting project evidence is allowed per role, the system may duplicate the same story across Experience and Projects unless support is bounded and clearly secondary.

### Composition-rule regression

Adaptive Experience composition must not override preset and section-detail controls.

## Acceptance Criteria

- Grouped `experience_entry` remains the primary construction evidence for the Experience section.
- Experience bullet selection becomes JD-sensitive rather than always reusing the same narrow slice across runs.
- The Experience section can vary its emphasis across target jobs while staying grounded in the same role/company/date evidence.
- Prompt assembly includes explicit instructions to summarize and re-emphasize grounded facts rather than merely restating bullets.
- Optional role-level supporting evidence, when used, remains bounded and secondary to grouped work-history evidence.
- Adaptive Experience composition does not regress back to shallow one-role or flat-snippet behavior.
- Existing preset/composition/content controls remain respected.
- Structured CV generation, markdown rendering, and current export/read paths continue to work.

## Recommendation

Proceed with Option 3.

The previous experience spec fixed the structural failure mode. This follow-on design addresses the new quality problem: Experience is now structurally grounded, but often not adaptive enough to the target JD. The right fix is to keep grouped experience intact while making selection and emphasis more job-sensitive.
