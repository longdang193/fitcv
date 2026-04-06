---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Preserve grouped work-history evidence for CV generation so experience sections stay rich, grounded, and structurally faithful."
invariants:
  - "CV generation must remain grounded in persisted candidate profile data."
  - "Disabled CV sections must stay excluded from final rendered markdown."
  - "Experience evidence should preserve role, company, and date grouping rather than flattening everything into standalone bullets."
  - "The change must improve experience richness without requiring prompt-time hallucinated reconstruction."
  - "Evidence retrieval for CV generation should become section-aware rather than purely snippet-ranked."
---

# Experience Evidence Preservation Design

## Affected Feature Contract

- [`docs/features/cv_system/cv_system.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)

## Triage

Feature type: MODIFY  
Summary: Preserve grouped work-history evidence in CV generation so experience sections are not shallow when the candidate profile contains richer history.  
Reasoning: This is a behavior correction and architectural refinement of the existing CV generation system, not a new standalone feature.  
Invariants:
- CV generation remains grounded in the candidate profile and selected evidence.
- Structured CV generation remains the canonical semantic path.
- Prompt and render behavior must stay aligned with composition settings.
- Existing markdown and export flows remain supported.
Dependencies:
- `cv_system`
- evidence retrieval and CV generation pipeline stages
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

This spec came from debugging a real generated CV artifact:

- [`cv_b630bed0-40ec-458d-9c55-a632e4805565.md`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/cv_b630bed0-40ec-458d-9c55-a632e4805565.md)

The problem was that the Experience section looked much shallower than the source candidate profile:

- the source profile contains 3 experience entries and 9 experience bullets in [`data/candidate_profile.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/data/candidate_profile.yaml)
- the generated CV surfaced only 1 experience entry and 2 bullets

During debugging, the root cause was not primarily "bad model writing." The upstream pipeline was compressing and de-structuring the candidate's work history before generation:

- experience evidence was flattened into standalone bullet-level items in [`src/fitcv/evidence.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py)
- evidence retrieval selected a single global top-k across projects, achievements, and experience bullets
- the current config uses `evidence_top_k: 5`, which is too small to preserve rich work-history context when projects and achievements compete for the same slots
- projects are weighted above experience bullets, so project evidence can crowd out experience evidence
- prompt formatting only passes thin evidence snippets, not grouped role/company/date blocks

As a result, the model often has to reconstruct an Experience section from sparse fragments instead of being handed structured work history directly.

## Problem Statement

The CV system currently retrieves evidence in a way that is strong for relevance ranking but weak for preserving the semantic structure of experience.

That causes three user-visible problems:

1. Experience sections in generated CVs can become shallow even when the candidate profile contains richer history.
2. The model is forced to infer grouping across jobs from loose bullet snippets.
3. Supporting evidence types like projects can dominate the evidence budget and crowd out core work-history context.

The system is currently optimized for global snippet relevance rather than section-faithful CV composition.

## Current Behavior

Today, evidence retrieval does the following:

1. Collects all projects, achievements, and experience bullets into one flat pool.
2. Scores all items globally against JD skills.
3. Returns only the top-k items.
4. Passes those selected items into the CV prompt as flat evidence lines.

This means a full role entry like:

```text
Senior Data Engineer — Acme Analytics GmbH (2023-01 to present)
- Built GA4 to BigQuery pipeline...
- Designed Pub/Sub → Dataflow → BigQuery...
- Automated data quality checks...
- Led migration of legacy Spark jobs...
```

is reduced to something more like:

```text
- Automated data quality checks with Great Expectations...
- Automated weekly reporting workflows with Python scripts...
- FitCV — AI-Powered CV Generation Pipeline
- Open-Source dbt Package for Marketing Attribution
- Real-Time Fraud Detection on AWS
```

That is enough to keep the CV grounded, but not enough to preserve strong work-history composition.

## Design Goal

Preserve grouped work-history context through evidence selection and CV prompting so the model can generate richer, more faithful Experience sections without giving up grounding or relevance ranking.

## Core Design Principle

CV evidence retrieval should become section-aware:

- grouped experience-entry evidence is the primary construction input for the Experience section
- project entries are the primary construction input for the Projects section when that section is enabled
- education entries remain the primary construction input for the Education section when that section is enabled
- achievements, project highlights, and skill-oriented snippets act as supporting evidence unless they are being used to build their own dedicated sections

This change is not just about adding more evidence. It is about preserving the right evidence shape for each section.

## Options Considered

### Option 1: Increase `evidence_top_k` only

Raise the global evidence budget from 5 to a larger number.

Pros:
- simple
- low implementation cost

Cons:
- does not restore job grouping
- still mixes projects, achievements, and experience bullets in one pool
- prompts may become noisier rather than more structured

Verdict:
- not sufficient on its own

### Option 2: Keep global selection, but raise experience-bullet weight

Bias scoring so more experience bullets survive the top-k.

Pros:
- small behavior change
- likely improves some runs

Cons:
- still loses role/company/date grouping
- still makes the model reconstruct jobs from fragments
- tuning weights alone is brittle

Verdict:
- partial mitigation only

### Option 3: Preserve grouped experience evidence and reserve capacity for it

Introduce a grouped experience evidence path where work history is selected and passed as role-level blocks, not only bullet fragments.

Pros:
- directly addresses the structural loss
- aligns better with the structured CV generation model
- gives the model richer experience input without requiring hallucinated reconstruction
- still allows projects and achievements as supporting evidence

Cons:
- requires changes across retrieval, prompt assembly, and likely tests/config semantics

Verdict:
- recommended

## Recommended Design

### 1. Distinguish section-construction evidence from supporting evidence

The evidence layer should no longer treat all evidence as one interchangeable relevance pool.

Instead, it should distinguish between:

- section-construction evidence
- supporting evidence

Section-construction evidence is used to build a specific section:

- Experience section → grouped experience entries
- Projects section → project entries
- Education section → education entries

Supporting evidence is used to strengthen wording, bullet emphasis, or prioritization:

- achievements
- selected project highlights
- skill-oriented snippets

This directly addresses the current failure mode where all evidence competes in one flat mixed pool.

### 2. Add an experience-entry evidence representation

The evidence layer should support a grouped experience item that preserves:

- role
- company
- location
- start/end dates
- selected bullets
- aggregated skills
- source reference to the original experience entry

This should coexist with finer-grained bullet evidence where useful, but grouped experience should become the primary input for CV Experience generation.

### 3. Make Experience section generation explicitly section-aware

The generation path should explicitly treat grouped experience-entry evidence as the primary source for constructing the Experience section.

Projects and achievements may enrich the final CV, but they must not replace grouped work-history as the main evidence source for Experience composition.

This requirement should be reflected in both:

- evidence retrieval semantics
- prompt construction semantics

### 4. Change evidence selection from one flat budget to a shaped budget

Instead of one global top-k across all evidence types, the CV pipeline should use a shaped budget, for example:

- top N grouped experience entries
- top M projects
- top P achievements

The exact counts can remain configurable, but the key design change is:

- experience should not have to compete for every slot against projects and achievements
- when multiple relevant grounded experience entries exist, the budget should preserve enough grouped work-history context to represent more than one role in the generated CV

This preserves relevance while ensuring the Experience section receives enough grounded input.

For the first implementation, the design should explicitly preserve multi-role capacity rather than relying on weight tuning alone.

### 5. Add selection rules inside each grouped experience entry

Grouped experience entries should preserve role-level structure while still allowing bounded bullet selection within each entry.

That means the selection layer should define how to:

- choose the most relevant bullets within an experience entry
- cap bullets per entry so prompts remain bounded
- preserve role, company, and date context even when only a subset of bullets is used

This avoids trading one problem for another:

- too little structure in the current system
- too much prompt bloat in an unbounded grouped-entry system

### 6. Pass grouped work-history blocks into the generation prompt

Prompt assembly should include structured experience blocks such as:

```text
Experience Entry
Role: Senior Data Engineer
Company: Acme Analytics GmbH
Dates: 2023-01 to present
Relevant bullets:
- Built GA4 to BigQuery pipeline...
- Designed Pub/Sub → Dataflow → BigQuery...
```

This gives the model the context it needs to generate a real Experience section instead of improvising from isolated bullets.

### 7. Keep projects and achievements as supporting evidence

Projects and achievements should remain available, but they should support the CV rather than dominate the evidence budget. Experience should be first-class evidence for experience composition.

### 8. Keep the structured CV model as the canonical output

This change should improve what the model receives before generation. It should not replace the structured CV document model or the render path introduced in the structured CV work.

The structured CV `experience` section should be generated primarily from grouped experience-entry evidence, not reverse-engineered from mixed flat snippets.

## Proposed Behavior

For CV generation:

1. Retrieve grouped experience entries relevant to the job.
2. Retrieve supporting projects and achievements.
3. Build a prompt that includes grouped work-history context plus supporting evidence.
4. Generate structured CV JSON from that richer, more faithful input.
5. Render markdown from the structured CV as usual.

## Data Contract Direction

The evidence layer should move toward a model like:

```json
{
  "evidence_type": "experience_entry",
  "source_ref": "experiences[0]",
  "role": "Senior Data Engineer",
  "company": "Acme Analytics GmbH",
  "start": "2023-01",
  "end": "present",
  "skills": ["BigQuery", "SQL", "dbt", "Python"],
  "bullets": [
    "Built GA4 to BigQuery pipeline processing 2M daily events...",
    "Designed and implemented a Pub/Sub -> Dataflow -> BigQuery streaming architecture..."
  ]
}
```

This is illustrative rather than final, but the key requirement is preserving grouped job structure.

## Non-Goals

- redesigning the entire ranking pipeline
- changing how final markdown rendering works beyond consuming improved structured CV content
- replacing structured CV generation with a fully deterministic template-only experience composer
- backfilling old generated CVs

## Risks

### Prompt bloat

Grouped experience entries are larger than bullet fragments. The new shaped evidence budget should keep prompts bounded.

### Over-selection of irrelevant history

If grouped experience is too coarse, irrelevant older roles may enter the prompt. Selection logic should still rank by JD relevance.

### Divergence between evidence retrieval and export/read models

If grouped evidence is added only for prompting but not reflected in tests and documentation, the system may become harder to reason about. The implementation should keep retrieval semantics explicit.

### Section imbalance

If experience capacity is preserved but supporting evidence is not budgeted carefully, the generated CV could overfit to work history and underrepresent projects or other enabled sections.

Mitigation:

- keep section-aware evidence budgets
- preserve explicit project-section evidence where that section is enabled
- treat supporting evidence as complementary rather than interchangeable

## Acceptance Criteria

- Experience evidence for CV generation preserves grouped role/company/date structure.
- CV evidence selection no longer relies solely on one global flat top-k of mixed snippets.
- The Experience section in structured CV generation is primarily built from grouped experience-entry evidence rather than mixed flat bullet snippets.
- Projects and achievements are treated as supporting evidence for experience composition unless they are being used to construct their own dedicated sections.
- When multiple relevant grounded experience entries exist, the evidence budget preserves enough grouped work-history context to represent more than one role.
- Projects and achievements remain available as supporting evidence.
- Generated CVs for profiles with rich work history no longer collapse to shallow one-role experience sections due to evidence flattening alone.
- The change does not break structured CV generation, markdown rendering, or existing composition controls.

## Recommendation

Proceed with Option 3.

This is the smallest design that actually addresses the real root cause. The problem is not merely that the model needs "more evidence"; it is that the model currently receives the wrong shape of evidence for composing a strong Experience section.
