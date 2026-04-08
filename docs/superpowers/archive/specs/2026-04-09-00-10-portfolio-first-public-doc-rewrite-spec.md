---
feature_type: modify
feature_name: repository_governance
status: draft
summary: "Rewrite the public-facing README and pipeline architecture doc so they present FitCV as a polished product/portfolio system, not an internal engineering notebook."
invariants:
  - "The rewritten docs must describe current system behavior truthfully and must not invent product capabilities that do not exist."
  - "The public-facing docs must explain who the system is for, what problem it solves, and what engineering value it delivers."
  - "Internal planning voice, obsolete proposal language, and private-process framing must be removed from the public-facing versions."
  - "Cross-cutting docs should remain concise and navigable for an external reader."
---

# Portfolio-First Public Doc Rewrite Spec

## Triage

Feature type: MODIFY  
Summary: Rewrite the public-facing `README.md` and `docs/FitCV-pipeline.md` so they explain FitCV as a product and engineering system clearly, accurately, and portfolio-first for the curated public repo.  
Reasoning: The current docs are functionally informative, but they still carry internal-note framing, outdated proposal language, and insufficient product storytelling. That weakens the first public release because an external reader does not get a clean answer to who uses the system, what problem it solves, what the major pipeline stages are, and what the strongest engineering work was.  
Invariants:
- Public docs must stay grounded in current code and current pipeline behavior
- Public docs must not depend on internal specs/plans to make sense
- Internal working-note voice such as “your old flow,” “you need,” or proposal-heavy “add X” guidance must not survive in the public-facing versions
- The rewritten docs should emphasize delivered architecture and engineering outcomes, not internal methodology
Dependencies:
- `README.md`
- `docs/FitCV-pipeline.md`
- `docs/fitcv-control-plane-setup.md`
- `docs/features/*`
- `docs/generated/feature_overview.md`
- `docs/generated/stage_overview.md`
Affected stages:
- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`
Affected features:
- `admin_control_plane_core`
- `cv_system`
- `inspection_debugging`
- `pipeline_performance`
- `trigger_run_management`
Primary lens: mixed
Affected docs:
  feature_yaml: none
  feature_history: none
  feature_docs: none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
    - `docs/fitcv-control-plane-setup.md`
  readme:
    - `README.md`
  generated:
    - `docs/generated/feature_overview.md`
    - `docs/generated/stage_overview.md`
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

The current public-facing docs are no longer wrong in the narrow technical sense, but they still undersell the project and leak too much internal-note style.

### 1. The README is only partially portfolio-first

The current [README.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/README.md) is much better than the earlier internal-control-plane version, but it still does not clearly answer:

- who uses the system
- what operational problem it solves
- what value the system creates
- what the strongest engineering work was

An external reader should be able to understand the user, the pain point, and the solution in the first screenful of content.

### 2. The pipeline doc still reads like an internal working note

[docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md) still contains:

- obsolete frontmatter and note-style metadata
- second-person advice such as “your old flow”
- proposal-heavy language such as “add,” “do not,” and “you need”
- a mix of current behavior, design rationale, future ideas, and historical evolution

That makes it difficult for a public reader to tell what the system actually does today.

### 3. The strongest engineering achievements are not surfaced clearly enough

The public-facing docs should highlight the system-level work that makes this repo strong as a portfolio piece, especially:

- staged pipeline architecture
- admin control plane and run lifecycle management
- artifact export and inspection design
- reranker short-circuiting before expensive CV-analysis work
- artifact truth alignment and run-mode-aware diagnostics
- performance/reuse improvements across late stages

These are currently scattered across docs and features, but not told as a clean public narrative.

## Goals

1. Make the public README explain the system in product terms first.
2. Recast `docs/FitCV-pipeline.md` as a current-state architecture walkthrough rather than a design notebook.
3. Surface the most important pipeline stages, control-plane capabilities, and engineering improvements clearly.
4. Remove obsolete, incorrect, or misleading phrasing from both docs.

## Non-Goals

This rewrite does not:

- change runtime behavior
- change feature contracts
- expose internal superpowers/spec/plan history publicly
- turn the public docs into exhaustive implementation documentation

## Desired Public Narrative

The public repo should tell a coherent story:

### Who uses it

FitCV is for an operator or builder who needs to process many job postings against a candidate profile, inspect the reasoning, and generate grounded CV outputs for the strongest matches.

### What problem it solves

Without the system, the workflow is fragmented and manual:

- raw jobs are noisy
- ranking is hard to trust
- generated CVs are difficult to ground and inspect
- operating the pipeline requires terminal-only workflows

FitCV solves that by combining:

- structured enrichment
- deterministic narrowing
- shortlist and ranking stages
- grounded CV generation
- an admin control plane for run inspection and tuning

### Why the implementation is strong

The public docs should make the engineering value legible:

- explicit stage boundaries
- operator-facing run diagnostics
- stable artifact contracts
- performance-aware late-stage short-circuiting and reuse
- safer generation validation and repair logic

## Proposed README Rewrite

The README should be organized around:

1. one-sentence product framing
2. who uses it and why
3. problem -> solution
4. key capabilities
5. concise architecture
6. key pipeline stages
7. major control-plane features
8. biggest engineering/optimization wins
9. links to setup and deeper architecture docs

### Specific improvements

- Add an explicit “Who it is for” section
- Add a “Problem / Solution” framing block
- Add a short “Key pipeline stages” section instead of only listing components
- Add a short “What’s technically notable” or “Engineering highlights” section
- Remove wording that still sounds internal or maintenance-oriented where product-oriented wording is clearer

## Proposed Pipeline Doc Rewrite

`docs/FitCV-pipeline.md` should become a public architecture doc with this structure:

1. system purpose
2. current pipeline stages
3. stage-by-stage responsibilities
4. control-plane interaction with pipeline runs
5. major safeguards and validation rules
6. major optimization/debugging work delivered
7. current execution modes (`Run All` vs `Stage by Stage`)
8. concise mental model / data flow diagram

### Specific removals

Remove or rewrite:

- obsolete frontmatter (`aliases`, `#zoomcamp`, empty status metadata)
- second-person design-journal language
- sections that are primarily historical proposal text rather than current architecture
- repetitive advisory sections that do not help an external reader understand the current system

### Specific additions

Add or elevate:

- explicit current stage order
- why each stage exists
- reranker short-circuit behavior
- artifact truth and inspection model
- execution-mode support
- reuse/performance improvements that materially changed the pipeline

## Public-Facing Engineering Achievements To Emphasize

Both docs should make these visible:

1. Admin control plane
- trigger runs
- inspect runs
- manage settings
- operate lifecycle actions without terminal-only workflows

2. Clear stage pipeline
- normalize
- enrich
- rule filter
- shortlist
- ranking
- cv_analysis
- cv_generation

3. Inspection and artifact design
- compact job ledger vs stage diagnostics split
- stage artifacts
- downloadable bundles
- truthful reranker-blocked vs analyzed-and-skipped semantics

4. Performance and reliability work
- reranker short-circuit before expensive analysis
- late-stage reuse
- execution-aware diagnostics
- deterministic validation and repair safeguards

## Acceptance Criteria

The rewrite is successful when:

- a new reader can answer who uses FitCV, what problem it solves, and what the product does from the README alone
- `docs/FitCV-pipeline.md` reads as a current-state system design doc instead of a notebook or advisory memo
- obsolete/internal-note phrasing is removed
- the strongest system-design and debugging work is visible in the public docs
- the public export no longer feels like it requires internal background knowledge

