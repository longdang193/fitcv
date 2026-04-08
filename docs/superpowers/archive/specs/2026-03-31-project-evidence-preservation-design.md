---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Preserve richer grouped project evidence for CV generation so project sections stay grounded, action-oriented, and consistent across runs."
invariants:
  - "CV generation must remain grounded in persisted candidate profile data."
  - "Structured CV generation remains the canonical semantic path."
  - "Projects should not collapse into tool lists when richer grounded project context exists."
  - "Project-section generation should stay aligned with preset/composition/content rules."
  - "The change must improve project-section faithfulness without weakening the recent experience-evidence preservation work."
---

# Project Evidence Preservation Design

## Affected Feature Contract

- [`docs/features/cv_system/cv_system.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)

## Triage

Feature type: MODIFY  
Summary: Preserve richer grouped project evidence in CV generation so project sections do not vary between shallow tool lists and grounded action-oriented summaries.  
Reasoning: This is a behavior correction and design refinement of the existing CV generation system, not a new standalone feature.  
Invariants:
- CV generation remains grounded in the candidate profile and selected evidence.
- Structured CV generation remains the canonical semantic path.
- Experience-evidence preservation remains intact and should not regress.
- Prompt and render behavior must stay aligned with composition settings.
- Existing markdown and export flows remain supported.
Dependencies:
- `cv_system`
- evidence retrieval and CV generation pipeline stages
- recent grouped experience-evidence preservation work
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

The observed behavior was asymmetric:

- the Experience section looked almost identical across both files
- the Projects section varied much more
- one CV described projects mostly as tool or skill lists
- the other described what the candidate actually built, using what tools, and why it mattered

During debugging, the root cause was not markdown rendering. The renderer was faithfully printing whatever structured project content the model had already generated.

The real issue was upstream in project evidence shaping:

- the source profile contains rich project data in [`data/candidate_profile.yaml`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/data/candidate_profile.yaml), including:
  - `name`
  - `duration`
  - `skills`
  - `tech_stack`
  - `business_value`
  - `highlights`
- prompt assembly in [`src/fitcv/cv_generator.py`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/cv_generator.py) currently formats most non-experience evidence as:

```text
- <project name>: <comma-separated skills>
```

That means project evidence is still skills-heavy but action-light. The model gets enough context to echo tools, but not enough structured context to consistently explain:

- what the candidate built
- why it mattered
- what outcomes or impact it achieved

After the recent experience-evidence preservation change, Experience became more stable because it now receives grouped role/company/date blocks. Projects did not receive a similar preservation upgrade, so the project path is now the weaker, more variable part of CV generation.

## Problem Statement

The CV system currently preserves much richer structure for Experience than for Projects.

That causes three user-visible problems:

1. Projects can be rendered as shallow tool lists even when richer grounded project context exists.
2. Project descriptions vary more from run to run because the model has to improvise action and impact language from underspecified evidence.
3. The system now has an asymmetry where Experience is structured and stable, while Projects are still under-specified and inconsistent.

The system is currently optimized for project-skill relevance rather than section-faithful project composition.

## Current Behavior

Today, project source data is rich, but project prompt evidence is thin.

At the profile level, a project entry can look like:

```yaml
name: "FitCV — AI-Powered CV Generation Pipeline"
duration: "2024-01 — present"
skills: ["Python", "BigQuery", "Vertex AI", "Gemini"]
tech_stack:
  - "Backend: Python, FastAPI, RQ (Redis Queue)"
  - "AI: Vertex AI Gemini 2.5 Flash"
business_value: >
  End-to-end AI pipeline that ingests job postings, matches against candidate profiles,
  and generates tailored CVs via Gemini. Reduced manual CV tailoring time from 2 hours
  to under 5 minutes per application.
highlights:
  - "Ingested 5,000+ LinkedIn job postings via scraper pipeline"
  - "Achieved 89% relevance score on candidate–job matching"
```

But by the time most project evidence reaches the generation prompt, it is effectively reduced to:

```text
- FitCV — AI-Powered CV Generation Pipeline: Python, BigQuery, Vertex AI, Gemini
```

That preserves grounding, but loses the most important composition signals:

- project purpose
- candidate actions
- measurable outcomes
- selected implementation details

When the model receives only the thin form above, it may produce either:

- a better project summary if it improvises well
- or a shallow skill list if it stays literal

## Design Goal

Preserve richer grouped project context through evidence selection and CV prompting so the model can generate project sections that are grounded, action-oriented, and more consistent across runs.

## Core Design Principle

Project evidence retrieval should become section-aware:

- grouped project evidence is the primary construction input for the Projects section when that section is enabled
- grouped experience evidence remains the primary construction input for the Experience section
- project evidence may also serve as supporting evidence elsewhere when grounded and relevant
- achievements and skill-oriented snippets remain supporting evidence unless they are being used to build their own dedicated sections

This change is not about making project prompts longer for their own sake. It is about preserving the right evidence shape for project composition.

The evidence contract should explicitly distinguish:

- section-construction evidence
- supporting evidence

For this change:

- Projects section
  - primary construction evidence: grouped `project_entry`
  - optional supporting evidence: selected project highlights, achievements, and skill-oriented snippets where grounded and relevant
- Experience section
  - primary construction evidence: grouped `experience_entry`
  - optional supporting evidence: achievements and other explicitly allowed supporting snippets

## Options Considered

### Option 1: Increase `evidence_top_k` or project weight only

Raise the total evidence budget or bias project scoring upward.

Pros:
- simple
- low implementation cost

Cons:
- does not preserve richer project structure
- still leaves projects under-specified in prompt construction
- may increase prompt size without improving project composition quality

Verdict:
- not sufficient on its own

### Option 2: Keep current retrieval, but enrich project prompt formatting only

Leave project retrieval unchanged, but pass more project fields into the prompt when project entries happen to be selected.

Pros:
- smaller change
- likely improves some project summaries

Cons:
- still treats projects mostly as generic evidence instead of section-construction evidence
- does not make project budgeting explicit
- may still let shallow project items compete poorly against other evidence types

Verdict:
- partial mitigation only

### Option 3: Preserve grouped project evidence and make project composition section-aware

Introduce a grouped project evidence path where projects are selected and passed as richer structured blocks, not only as name-plus-skill snippets.

Pros:
- directly addresses the under-specification problem
- aligns project handling with the recent grouped experience-evidence design
- reduces project-output variability by preserving purpose, impact, and implementation context
- still keeps projects grounded in persisted candidate data

Cons:
- requires changes across evidence shaping, prompt assembly, and likely tests/config semantics

Verdict:
- recommended

Example:

Current thin project evidence:

```text
- FitCV — AI-Powered CV Generation Pipeline: Python, BigQuery, Vertex AI, Gemini
```

Proposed grouped project evidence:

```text
Project Entry
Name: FitCV — AI-Powered CV Generation Pipeline
Duration: 2024-01 — present
Business value: End-to-end AI pipeline that reduced manual CV tailoring time from 2 hours to under 5 minutes per application.
Relevant stack:
- Python
- BigQuery
- Vertex AI Gemini
Relevant highlights:
- Ingested 5,000+ LinkedIn job postings via scraper pipeline
- Achieved 89% relevance score on candidate–job matching
```

Likely effect on output:

- thin evidence often leads to:

```text
FitCV — AI-Powered CV Generation Pipeline
Python, BigQuery, Vertex AI, Gemini
```

- grouped evidence is much more likely to lead to:

```text
Built and operated FitCV, an AI-powered CV generation pipeline using Python, BigQuery, and Vertex AI Gemini, reducing manual CV tailoring time from 2 hours to under 5 minutes and processing 5,000+ scraped job postings.
```

The important change is not just “more text.” It is that the model receives grounded purpose, action, and outcome signals in a project-shaped block rather than a tool list.

## Recommended Design

### 1. Distinguish project section-construction evidence from supporting project evidence

The evidence layer should not treat projects as only generic supporting evidence.

Instead:

- grouped project entries are section-construction evidence for the Projects section
- selected project highlights may also act as supporting evidence elsewhere when grounded and relevant

This mirrors the recent experience-evidence correction and removes the current asymmetry between work history and project handling.

### 2. Add a first-class grouped project evidence representation

`project_entry` should become a first-class evidence type in the evidence layer, not just a prompt-only intermediate shape created late in generation.

That means grouped project evidence should be visible and testable in:

- evidence collection
- evidence ranking and shaping
- prompt assembly
- regression coverage

This mirrors the recent `experience_entry` correction and avoids burying important section-construction logic inside prompt formatting.

The evidence layer should support a grouped project item that preserves:

- required:
  - `evidence_type`
  - `source_ref`
  - `name`
- optional but preserved when present:
  - `duration`
  - `url`
  - `skills`
  - `tech_stack`
  - `business_value`
  - `highlights`
- derived or selected:
  - selected skills
  - selected tech stack lines
  - selected highlights
  - prompt-facing summary text when needed

This should become the primary project input for Projects composition.

### 3. Make Projects section generation explicitly section-aware

The generation path should explicitly treat grouped project evidence as the primary source for constructing the Projects section.

That means the model should no longer have to infer action and impact from a thin `name + skills` line alone.

Projects may still reinforce other sections when grounded, but the Projects section itself should be built from grouped project evidence.

### 4. Use a shaped project budget instead of leaving project richness accidental

Project evidence should not depend on whichever thin snippet survives a generic relevance pool.

The CV pipeline should explicitly preserve enough grouped project evidence to support section-faithful Projects composition when that section is enabled.

The first-pass budget semantics should be:

- reserve bounded grouped-project capacity when the Projects section is enabled
- preserve grouped project capacity independently from grouped experience capacity
- keep supporting project evidence separate from the reserved grouped-project budget
- apply bounded intra-project selection after grouped project entries are chosen

The exact counts can remain configurable, but the first implementation should preserve multi-project capacity when relevant grounded project evidence exists.

This budget can remain internal for the first rollout, but it should have an explicit config home or a clearly owned default in the evidence-selection layer.

### 5. Add bounded selection within each grouped project entry

Grouped projects should preserve project-level structure while still keeping prompts bounded.

That means selection rules should define how to:

- choose the most relevant highlights within a project
- cap highlights or detail lines per project
- preserve purpose, outcome, or impact context when present
- preserve implementation context when present

This avoids replacing today’s under-specification with unbounded prompt bloat.

Selection should use a two-stage logic:

1. rank project entries as grouped units
2. within selected project entries, choose bounded highlights/details

This prevents grouping from becoming only cosmetic.

### 6. Pass richer project blocks into the generation prompt

Prompt assembly should include structured project blocks such as:

```text
Project Entry
Name: FitCV — AI-Powered CV Generation Pipeline
Duration: 2024-01 — present
Business value: End-to-end AI pipeline that reduced manual CV tailoring time from 2 hours to under 5 minutes per application.
Relevant stack:
- Python
- BigQuery
- Vertex AI Gemini
Relevant highlights:
- Ingested 5,000+ LinkedIn job postings via scraper pipeline
- Achieved 89% relevance score on candidate–job matching
```

This gives the model enough context to produce a project summary that is grounded in what the candidate built and why it mattered.

If a project is sparse and contains only fields like:

- `name`
- `duration`
- `skills`

then grouped project evidence should still exist, but prompt assembly should degrade gracefully. It should not invent impact language that is absent from the source profile.

### 7. Keep Experience preservation intact

This work should not weaken the recent grouped experience-evidence path.

Experience should remain the primary source for the Experience section, while grouped project evidence should become the primary source for the Projects section.

### 8. Keep the structured CV model as the canonical output

This change should improve what the model receives before generation. It should not replace the structured CV document model or the render path introduced in the structured CV work.

The structured CV `projects` section should be generated primarily from grouped project evidence, not reconstructed from tool-only snippets.

### 9. Make the old thin project formatting path explicit

The current thin `name + skills` formatting path should no longer be the primary construction path for the Projects section.

It should either:

- remain only as fallback or supporting evidence formatting
- or be treated as deprecated for project-section construction

The implementation should choose one of those paths explicitly rather than letting both remain ambiguous.

## Proposed Behavior

For CV generation:

1. Retrieve grouped experience entries relevant to the job.
2. Retrieve grouped project entries relevant to the job.
3. Retrieve supporting achievements or other supporting evidence where appropriate.
4. Build a prompt that includes grouped work-history context plus grouped project context.
5. Generate structured CV JSON from that richer, more faithful input.
6. Render markdown from the structured CV as usual.

## Data Contract Direction

The evidence layer should move toward a model like:

```json
{
  "evidence_type": "project_entry",
  "source_ref": "projects[0]",
  "name": "FitCV — AI-Powered CV Generation Pipeline",
  "duration": "2024-01 — present",
  "url": "https://github.com/nguyenvana/fitcv",
  "skills": ["Python", "BigQuery", "Vertex AI", "Gemini"],
  "tech_stack": [
    "Backend: Python, FastAPI, RQ (Redis Queue)",
    "AI: Vertex AI Gemini 2.5 Flash"
  ],
  "business_value": "End-to-end AI pipeline that reduced manual CV tailoring time...",
  "highlights": [
    "Ingested 5,000+ LinkedIn job postings via scraper pipeline",
    "Achieved 89% relevance score on candidate–job matching"
  ]
}
```

This is illustrative rather than final, but the key requirement is preserving grouped project structure and grounded project context.

Grouped-project relevance should be computed at the project-entry level, not only from isolated sub-snippets. Selection of highlights or detail lines should happen after grouped-project ranking, not before.

## Non-Goals

- redesigning the entire ranking pipeline
- replacing structured CV generation with a fully deterministic template-only project composer
- backfilling old generated CVs
- weakening the recent grouped experience-evidence design

## Risks

### Prompt bloat

Grouped project entries are larger than `name + skills` snippets. The shaped project budget should keep prompts bounded.

### Over-detailing the Projects section

If project entries become too verbose, the CV may overweight projects relative to other enabled sections.

Mitigation:

- keep section-aware budgets
- cap highlights or detail lines per project
- preserve section-composition controls

### Section coupling drift

If grouped project evidence is added only to prompt construction but not clearly reflected in tests and docs, the system may become harder to reason about.

### Experience regression

Project improvements must not undo the stability gains from grouped experience preservation.

### Composition-rule regression

Richer project evidence must not override existing preset or composition controls.

Examples:

- if the Projects section is disabled, grouped project evidence must not force project output
- if composition limits Projects to one item, richer evidence must still respect that cap
- if a preset intentionally prioritizes Experience over Projects, grouped project evidence must not override that intent

## Acceptance Criteria

- Grouped `project_entry` evidence exists as a first-class evidence type rather than only as prompt-formatting output.
- Project evidence for CV generation preserves grouped project structure rather than collapsing immediately to `name + skills`.
- The Projects section in structured CV generation is primarily built from grouped project evidence rather than tool-only snippets.
- Project evidence preserves grounded purpose, outcome, or impact context when that context exists in the source profile.
- Project evidence preserves enough implementation detail to explain what the candidate built, not just which tools were used.
- When multiple relevant grounded projects exist, the evidence budget preserves enough grouped project context to represent more than one project.
- Grouped project entries are ranked as grouped units, and bounded highlight/detail selection happens inside selected projects.
- When source project data includes contextual fields beyond skills, prompt assembly includes at least one such contextual field when present.
- Sparse project entries degrade gracefully without invented impact language.
- Experience-evidence preservation continues to function without regression.
- When the Projects section is disabled or composition-limited, grouped project evidence still respects those controls.
- The change does not break structured CV generation, markdown rendering, or existing composition controls.
- Generated project sections become more consistent across runs for the same source profile and job context.

## Recommendation

Proceed with Option 3.

This is the smallest design that actually addresses the current project-section failure mode. The problem is not merely that project evidence needs "more text"; it is that the model currently receives the wrong shape of project evidence for composing a strong Projects section.
