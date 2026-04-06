---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Upgrade cv_analysis evidence retrieval from required-skill-only heuristics to multi-channel retrieval plus reranked final evidence selection, with additive candidate YAML improvements."
invariants:
  - "cv_analysis remains the sole owner of evidence retrieval and final evidence selection before CV writing."
  - "cv_generation consumes persisted analysis-selected evidence and does not silently recompute retrieval by default."
  - "Evidence selection must stay grounded in the candidate profile; no invented evidence is allowed."
  - "Final evidence selection is bounded by one per-job top-k budget, not independent unbounded channel budgets."
  - "Candidate YAML changes must be additive and backward-compatible."
---

# CV Analysis Evidence Selection Upgrade Spec

## Triage

Feature type: MODIFY  
Summary: Replace the current required-skill-centric evidence retrieval in `cv_analysis` with multi-channel retrieval, merge/dedupe, and reranked final evidence selection, while extending the candidate YAML contract with additive metadata that improves role, domain, and responsibility alignment.  
Reasoning: This is a behavior change inside an existing managed feature. The primary lifecycle owner is [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml), and the change is stage-heavy because it reshapes `cv_analysis` runtime behavior and its artifacts.  
Invariants:
- `cv_analysis` owns evidence retrieval and final evidence selection.
- `cv_generation` remains generation/validation/persistence only.
- Evidence remains grounded in persisted candidate profile data.
- Final selection uses one bounded per-job `top_k`.
- Existing candidate YAML files remain valid.
Dependencies:
- `cv_analysis` stage runtime in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/pipeline.py)
- evidence retrieval module in [evidence.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py)
- candidate profile contract in [candidate.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/candidate.py)
Affected stages:
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml: [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/cv_system.yaml)
  feature_history: [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/docs/features/cv_system/history.md)
  feature_docs: none
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

## Current Problem

`cv_analysis` currently retrieves evidence by calling [`retrieve_evidence(...)`](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-analysis/src/fitcv/evidence.py) with the candidate profile and only the job's `required_skills`.

This has four major weaknesses:

1. Retrieval is too narrow.
- It is primarily keyed by `required_skills`.
- It does not directly retrieve evidence for role similarity, domain relevance, or responsibility alignment.

2. Matching is too lexical.
- Item scoring depends mostly on exact/lowercased skill overlap.
- Responsibility and role alignment are hard to capture with simple keyword overlap.

3. Final selection is not explicit.
- The current module retrieves and budgets evidence items directly.
- There is no clear multi-channel merge/dedupe/rerank contract before the final evidence bundle is persisted into `cv_analysis`.

4. Candidate YAML can express rich raw evidence, but not enough alignment metadata.
- Existing profiles already contain `experiences`, `projects`, `achievements`, `skills`, and `preferences`.
- But the current contract does not clearly support explicit domain tags, role-family hints, or responsibility themes on evidence-bearing items.

## Goals

1. Retrieve candidate evidence separately for:
- required skill support
- title/role alignment
- domain alignment
- responsibility alignment

2. Merge those candidate pools into one deduplicated evidence pool per ranked job.

3. Use a smarter final selector to choose the best bounded evidence subset for CV generation.

4. Keep evidence selection grounded, explainable, and stage-owned by `cv_analysis`.

5. Improve the candidate YAML contract with additive metadata that makes evidence selection better without breaking existing files.

## Non-Goals

- Replacing `cv_generation` ownership of writing, validation, repair, or persistence
- Moving evidence selection into `cv_generation`
- Replacing the central skill synonym system with candidate-local synonym maps
- Requiring all existing candidate YAML files to be rewritten

## Proposed Design

### 1. Multi-Channel Retrieval in `cv_analysis`

For each ranked job, `cv_analysis` should retrieve evidence candidates separately for four channels.

#### A. Required Skill Support

Purpose:
- Find evidence that directly supports the job's required technical skills.

Preferred job-side inputs:
- `required_skills_canonical`
- `required_skill_entities`
- fallback `required_skills`

Preferred candidate-side evidence sources:
- `experience_entry`
- `experience_bullet`
- `project_entry`
- `achievement`

Primary signals:
- canonical skill match
- synonym-backed match
- evidence type strength

#### B. Title / Role Alignment

Purpose:
- Find evidence that the candidate has already worked in roles similar to the target job.

Preferred job-side inputs:
- `job_title`
- `job_family`

Preferred candidate-side sources:
- `experiences[].role`
- `projects[].name`
- optional candidate YAML `preferences.target_role`
- optional candidate YAML `preferences.role_families`

Primary signals:
- semantic similarity between job title and candidate role text
- explicit or inferred role-family match

#### C. Domain Alignment

Purpose:
- Find evidence that the candidate has worked in the same or adjacent domain.

Preferred job-side inputs:
- `domain`
- `job_family`

Preferred candidate-side sources:
- experience-level domain tags
- project-level domain tags
- achievement-level domain tags
- business-value text and project context text as fallback

Primary signals:
- explicit domain tag match
- adjacent-domain mapping
- semantic similarity over domain context text

#### D. Responsibility Alignment

Purpose:
- Find evidence that the candidate has done similar work to the job's stated responsibilities.

Preferred job-side inputs:
- `responsibilities`

Preferred candidate-side sources:
- `experiences[].bullets`
- `projects[].highlights`
- `projects[].business_value`

Primary signals:
- semantic similarity between responsibility text and candidate evidence text
- optional explicit responsibility-theme overlap

### 2. Candidate Retrieval Pools

Each retrieval channel should over-retrieve a small candidate pool instead of trying to decide the final evidence set immediately.

Recommended contract:
- each channel returns a short ranked list, for example 3 to 5 candidates
- each returned item carries:
  - `evidence_id`
  - `evidence_type`
  - `source_ref`
  - `channel`
  - `channel_score`
  - channel-specific rationale fields

This stage is optimized for recall, not final precision.

### 3. Stable Evidence Identity

Evidence identity must be channel-independent so the same evidence item retrieved by multiple channels appears once in the merged pool.

Stable identity should be derived from the source candidate evidence item, not the retrieval reason.

Recommended identity contract:
- `evidence_id` remains the canonical dedupe key
- the ID should be based on:
  - `evidence_type`
  - stable source anchor such as `source_ref`
  - normalized item anchor text or name

Important rule:
- retrieval channel must never be part of the evidence identity

If the same experience bullet is retrieved by:
- required skill support
- responsibility alignment

it must still dedupe to one evidence item with multiple matched channels.

### 4. Merge and Dedupe

After separate retrieval:

1. merge all retrieved channel pools into one list
2. dedupe by `evidence_id`
3. aggregate metadata per item:
- `matched_channels`
- `channel_scores`
- strongest rationale snippets

Result:
- one deduplicated merged evidence pool per ranked job

### 5. Smarter Final Evidence Selection

The final evidence subset should be selected from the merged deduplicated pool by a smarter reranker.

#### Recommended Selection Architecture

1. separate retrieval channels for recall
2. merge/dedupe
3. rerank the merged pool
4. select one final bounded `top_k`

#### Reranker Choice

This spec recommends:
- a smarter reranker, preferably LLM-based, over pure heuristic-only final selection

Reason:
- the final evidence subset must balance:
  - required skill support
  - responsibility coverage
  - role alignment
  - domain alignment
  - credibility
  - non-redundancy
  - diversity across evidence types

That is difficult to do well with a single heuristic score.

#### Reranker Input Contract

The reranker should receive:
- compact job context
  - target title
  - domain
  - role family
  - required skills
  - preferred skills
  - responsibilities
- the deduplicated candidate evidence pool
- one global final `top_k`

Each evidence candidate should include:
- `evidence_id`
- `evidence_type`
- short display text
- `matched_channels`
- summarized channel scores

#### Reranker Output Contract

The reranker should return structured selection only, not generated prose.

Recommended output:

```json
{
  "selected_evidence_ids": ["e1", "e7", "e3", "e2", "e9"],
  "selection_reasons": {
    "e1": ["required_skill_support", "responsibility_alignment"],
    "e7": ["role_alignment"],
    "e3": ["domain_alignment"]
  }
}
```

### 6. Final `top_k` Semantics

`top_k` should mean:
- the final number of evidence items selected per job for downstream CV generation

It should **not** mean:
- top-k per channel
- top-k per evidence type

Channels may over-retrieve before merge. The final selection is one bounded evidence bundle per job.

Recommended behavior:
- per-channel retrieval budget is internal
- final `top_k` is global and per job
- diversity constraints apply during final selection, not before merge

Example diversity constraints:
- prefer at least one experience-derived item if available
- avoid returning many nearly identical bullets
- do not let one evidence type dominate if a more balanced set gives better job coverage

## Candidate YAML Changes

### Design Principle

Candidate YAML changes must be additive and optional.

Existing candidate profiles should remain valid and should still work with fallback derivation. New fields improve retrieval quality but are not required for correctness.

### Existing Fields That Become More Important

The following existing fields become strongly recommended for better evidence selection:

- `preferences.target_role`
- `preferences.role_families`
- `preferences.domains`
- `experiences[].role`
- `experiences[].bullets[].skills`
- `projects[].skills`
- `projects[].business_value`
- `projects[].highlights`
- `achievements[].text`

### New Additive Candidate YAML Fields

#### Preferences

```yaml
preferences:
  target_role: "Data Analyst"
  role_families: ["analytics"]
  domains: ["banking", "fintech"]
```

Status:
- existing and already supported in part
- now explicitly part of the evidence-selection contract

#### Experience-Level Metadata

```yaml
experiences:
  - id: "exp_1"
    role: "Business Data Analyst"
    role_family: "analytics"            # optional explicit override
    domain_tags: ["banking", "retail_banking"]
    responsibility_themes:
      - "dashboarding"
      - "kpi_reporting"
      - "stakeholder_communication"
```

Purpose:
- improve role alignment
- improve domain alignment
- improve responsibility alignment

#### Project-Level Metadata

```yaml
projects:
  - id: "proj_1"
    name: "Credit KPI Dashboard"
    domain_tags: ["banking", "credit_risk"]
    responsibility_themes:
      - "dashboarding"
      - "reporting_automation"
```

Purpose:
- make project evidence more retrievable for domain and responsibility channels

#### Achievement-Level Metadata

```yaml
achievements:
  - id: "ach_1"
    text: "Reduced reporting latency by 40%"
    domain_tags: ["banking"]
```

Purpose:
- let achievements contribute to domain-aware retrieval when relevant

### Explicit Non-Goal for Candidate YAML

This spec does **not** add candidate-local synonym maps into the main candidate profile contract.

Reason:
- synonym normalization remains a shared system concern
- candidate facts and normalization rules should stay separate

If candidate-local alias support is ever needed later, it should live in a separate optional normalization section, not be mixed into the main profile facts.

## Runtime Artifact and Inspection Changes

`cv_analysis` artifact should expose:
- per-channel retrieval counts
- merged pool size
- deduplicated pool size
- final selected evidence count
- selected evidence samples
- skipped-fit-gate records
- analysis-failed records

Each `cv_analysis_result` should be able to show:
- `matched_channels`
- `selection_reasons`
- final selected evidence IDs

This keeps evidence selection explainable and auditable.

## Backward Compatibility

- Existing candidate YAML files remain valid.
- If additive fields like `role_family`, `domain_tags`, or `responsibility_themes` are absent, the system falls back to current fields and weaker derivation.
- `cv_generation` continues consuming persisted `cv_analysis` outputs; this spec only changes how those outputs are produced.

## Recommended Rollout

1. Add additive candidate YAML support and validation acceptance
2. Implement multi-channel retrieval contract in `cv_analysis`
3. Merge/dedupe into one evidence pool by `evidence_id`
4. Add the final reranker-based evidence selector
5. Expand `cv_analysis` artifacts and debug payloads

## Acceptance Criteria

- `cv_analysis` no longer relies only on required-skill overlap for evidence retrieval.
- Evidence candidates are retrieved separately for required skill, role, domain, and responsibility alignment.
- Retrieved pools are merged and deduped by stable `evidence_id`.
- Final evidence selection uses one bounded per-job `top_k`.
- Candidate YAML supports additive role/domain/responsibility metadata without breaking existing profiles.
- `cv_analysis` artifacts can explain why a final evidence item was selected.
