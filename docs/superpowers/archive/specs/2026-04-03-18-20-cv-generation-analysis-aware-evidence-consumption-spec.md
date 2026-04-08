---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Adjust cv_generation so it uses the richer persisted cv_analysis evidence semantics for prompt construction, validation grounding, debug visibility, and output provenance instead of treating evidence as a flat list."
invariants:
  - "cv_analysis remains the sole owner of evidence retrieval, merge/dedupe, final evidence selection, and fit-gate decisions."
  - "cv_generation consumes persisted analysis outputs and does not silently recompute retrieval by default."
  - "Expected analysis outcomes such as fit-gate skips must not be represented as generation failures."
  - "CV writing must remain grounded in selected candidate evidence only."
  - "cv_generation artifacts must include bounded cv_analysis-derived inputs and selected evidence context for easier debugging."
  - "The cv_generation contract remains backward-compatible with existing persisted cv_analysis records during rollout."
---

# CV Generation Analysis-Aware Evidence Consumption Spec

## Triage

Feature type: MODIFY  
Summary: Update `cv_generation` so it consumes the richer `cv_analysis` evidence bundle as structured guidance for writing, validation, and provenance, rather than treating the analysis-selected evidence as an undifferentiated flat list.  
Reasoning: This is an internal behavior change inside an existing managed feature. The primary owner is [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/cv_system.yaml), and the main lifecycle impact sits at the stage boundary between `cv_analysis` and `cv_generation`.  
Invariants:
- `cv_analysis` remains the sole owner of evidence retrieval and final evidence selection.
- `cv_generation` consumes persisted `cv_analysis` records and does not silently rerun evidence retrieval.
- Fit-gate skips remain analysis outcomes, not generation failures.
- CV claims remain grounded in the selected evidence bundle.
- `cv_generation` artifacts must include bounded `cv_analysis`-derived inputs and selected evidence context for easier debugging.
- Existing persisted `cv_analysis` records without richer provenance must remain consumable during rollout.
Dependencies:
- `cv_generation` stage runtime in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
- CV prompt construction and rendering in [cv_generator.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/cv_generator.py)
- `cv_analysis` record schema in [pipeline.py](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/src/fitcv/pipeline.py)
Affected stages:
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `inspection_debugging`
- `trigger_run_management`
Primary lens: mixed
Affected docs:
  feature_yaml: [cv_system.yaml](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/cv_system.yaml)
  feature_history: [history.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/features/cv_system/history.md)
  feature_docs: none
  cross_cutting_docs:
  - [FitCV-pipeline.md](c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/cv-gen/docs/FitCV-pipeline.md)
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

`cv_analysis` now produces a much richer evidence-selection payload:

- multi-channel retrieval provenance
- matched channels
- selection reasons
- evidence selection summary
- clearer fit-gate ownership

But `cv_generation` still mostly consumes:

- `job_snapshot`
- `evidence_payload`
- `gap_summary`
- `fit_classification`

as if evidence were only a flat list of items.

This creates four problems:

1. Evidence semantics are lost at writing time.
- The CV writer knows which evidence items were selected.
- It does not clearly know why each item was selected.
- So summary, experience, and project writing cannot use channel intent directly.

2. Validation remains weaker than the available analysis signal.
- Validation can confirm that claims are grounded somewhere.
- It cannot yet use the richer selected-evidence intent to verify whether claims are supported by the right kind of evidence.

3. Debugging lacks generation-aware provenance.
- `cv_analysis` can explain why evidence was selected.
- `cv_generation` debug output does not yet preserve enough of that selection context to explain why the generator wrote certain claims.

4. The stage boundary is richer than the generation contract.
- `cv_analysis` already produces a stronger generation-ready bundle.
- `cv_generation` does not yet fully exploit that bundle.

## Goals

1. Make `cv_generation` use analysis-selected evidence as structured guidance, not only a flat list.

2. Use evidence intent to guide different writing surfaces:
- summary and positioning
- experience bullets
- projects
- domain familiarity statements

3. Improve generation-time and validation-time grounding with the richer analysis contract.

4. Preserve stronger provenance in CV-generation debug outputs and persisted output metadata.

5. Expose the upstream `cv_analysis` inputs and selected evidence context directly in the `cv_generation` artifact so reviewers do not need to open the previous stage artifact first.

6. Keep the rollout backward-compatible with older `cv_analysis` records.

## Non-Goals

- Moving evidence retrieval back into `cv_generation`
- Replacing `cv_analysis` as the owner of final evidence selection
- Replacing the CV-generation model or prompt system wholesale
- Redesigning `gap_analysis`
- Requiring existing archived `cv_analysis` artifacts to be migrated before the rollout

## Proposed Design

### 1. Treat the `cv_analysis` Output as a Structured Generation Bundle

`cv_generation` should treat each generation-ready analysis record as a structured writing bundle with:

- `job_snapshot`
- `fit_classification`
- `gap_summary`
- `evidence_payload`
- `evidence_used`
- `evidence_selection_summary`

Instead of treating `evidence_payload` as just a generic list, the stage should interpret it as:

- skill-support evidence
- role-alignment evidence
- domain-alignment evidence
- responsibility-alignment evidence

when those semantics are present.

### 2. Evidence Intent Should Influence Writing Behavior

Different evidence purposes should guide different output surfaces.

#### A. Summary / Positioning

Use primarily:
- role-alignment evidence
- domain-alignment evidence
- strongest required-skill-support evidence

Avoid:
- overusing responsibility-only evidence for high-level positioning

Expected behavior:
- summary should describe the candidate in the role and domain framing most strongly supported by selected evidence

#### B. Experience Bullets

Use primarily:
- responsibility-alignment evidence
- required-skill-support evidence

Expected behavior:
- experience bullets should reflect similar work done before
- technical claims should come from evidence that explicitly supports those requirements

#### C. Projects Section

Use primarily:
- project entries selected for required-skill support
- project entries selected for responsibility alignment
- project entries selected for domain alignment when domain is relevant to the job

Expected behavior:
- project writeups should emphasize the aspects that match the target job, not generic project summaries

#### D. Domain Familiarity Statements

Use primarily:
- domain-alignment evidence

Expected behavior:
- domain familiarity claims should only appear when there is actual aligned evidence in the selected bundle

### 3. Prompt Construction Should Be Evidence-Aware

The generation prompt should explicitly reflect evidence purpose.

Recommended prompt structure:

1. job context
2. fit classification
3. gap summary
4. selected evidence grouped or annotated by purpose
5. writing rules per section

Recommended evidence presentation:
- include `matched_channels`
- include `selection_reasons`
- optionally group evidence into:
  - strongest skill-support items
  - strongest role/domain items
  - strongest responsibility-alignment items

The generator should be instructed:
- use skill-support evidence for concrete technical claims
- use role/domain evidence for summary positioning
- use responsibility-alignment evidence for work-history bullets
- do not invent claims outside the selected evidence bundle

### 4. Validation Should Be Aware of Analysis-Selected Evidence Intent

Validation should remain bounded and deterministic, but it should become more analysis-aware.

Recommended additions:

- when `evidence_grounded_only` is enabled, validate that substantive claims map back to selected evidence
- when claims imply domain experience, require domain-alignment evidence or a clearly grounded fallback
- when bullets imply specific responsibilities, prefer support from responsibility-alignment evidence or explicit skill-support evidence

This does not require a full semantic validator in phase 1.
It does require that validation understand more about the selected evidence bundle than a plain list of IDs.

### 5. Preserve Better Generation-Time Provenance

`cv_generation` debug records and accepted output metadata should preserve enough of the analysis contract to make later debugging easier.

Recommended additions:

- include `evidence_selection_summary` in generation debug records
- include a bounded evidence-purpose summary in generation debug records
- optionally persist a compact signature or hash of the analysis-selected evidence bundle with accepted CV versions

The goal is not to duplicate all `cv_analysis` data.
The goal is to preserve enough generation-time context to explain:
- what evidence bundle the generator saw
- what kind of evidence the generator relied on

### 6. Include Upstream Analysis Inputs in the `cv_generation` Artifact

The `cv_generation` stage artifact should show the bounded upstream analysis context that generation actually consumed.

Recommended additions:

- generation input samples should include:
  - `job_url`
  - `job_title`
  - `fit_classification`
  - `ranking_fit_label`
  - `evidence_selection_summary`
  - bounded `evidence_used`
  - bounded `gap_summary`
- changed-state samples for validation, generation, and persistence failures should include the same bounded analysis-derived context

This is explicitly for debugging:
- reviewers should be able to understand what `cv_generation` received from `cv_analysis`
- they should not need to download the previous stage artifact first to understand why generation failed or why a generated CV looks the way it does

This must remain bounded:
- use the already-trimmed `evidence_used` view rather than duplicating full raw payloads
- cap long text consistently with existing artifact truncation rules
- preserve reviewer-friendly summaries instead of mirroring full checkpoint state

### 7. Backward-Compatible Rollout

`cv_generation` must continue to work with older `cv_analysis` records that may lack:

- `matched_channels`
- `selection_reasons`
- `evidence_selection_summary`

Fallback rules:

- if richer evidence semantics are missing, use the existing flat evidence behavior
- if `evidence_selection_summary` is missing, treat it as empty metadata
- if channel tags are missing, do not block generation; degrade gracefully

This allows the rollout to happen without rewriting historical records.

## Example

### Current Behavior

`cv_analysis` selects:

```json
[
  {
    "evidence_type": "experience_entry",
    "name": "Data Engineer — Fintech Startup GmbH"
  },
  {
    "evidence_type": "project_entry",
    "name": "Real-Time Fraud Detection on AWS"
  },
  {
    "evidence_type": "experience_entry",
    "name": "Junior Data Analyst — RetailCo AG"
  }
]
```

`cv_generation` mostly sees a flat list and may produce generic writing such as:

```text
Data professional with experience in analytics, engineering, and reporting. Skilled in SQL, Python, and dashboards.
```

### Proposed Behavior

`cv_analysis` selected evidence carries purpose:

```json
[
  {
    "evidence_type": "experience_entry",
    "name": "Data Engineer — Fintech Startup GmbH",
    "matched_channels": [
      "required_skill_support",
      "responsibility_alignment"
    ]
  },
  {
    "evidence_type": "project_entry",
    "name": "Real-Time Fraud Detection on AWS",
    "matched_channels": [
      "domain_alignment",
      "responsibility_alignment"
    ]
  },
  {
    "evidence_type": "experience_entry",
    "name": "Junior Data Analyst — RetailCo AG",
    "matched_channels": [
      "role_alignment"
    ]
  }
]
```

Expected writing behavior:

```text
Data professional with hands-on experience delivering analytics and reporting solutions across fintech and retail contexts. Strong in SQL, Python, and stakeholder-facing KPI analysis, with prior work aligned to reporting-heavy analyst responsibilities.
```

Compared with the current output, the revised CV:
- positions the candidate using role/domain evidence
- supports technical claims with skill-support evidence
- uses responsibility-alignment evidence to shape work-history bullets

## Artifact and Debugging Changes

`cv_generation` artifacts and debug records should add bounded fields such as:

- bounded `cv_analysis`-derived input sample context
- bounded `evidence_used`
- `evidence_selection_summary`
- `evidence_purpose_summary`
- `analysis_contract_version` or equivalent bounded provenance indicator

This should remain bounded and reviewer-friendly.

## Risks

1. Prompt complexity can grow too quickly.
- Mitigation: keep the evidence-purpose structure compact and bounded.

2. Generation may overweight one evidence channel.
- Mitigation: make prompt rules explicit about section-specific evidence usage.

3. Validation may become too strict too early.
- Mitigation: phase in analysis-aware validation incrementally.

4. Artifact duplication can become noisy or oversized.
- Mitigation: include bounded `cv_analysis`-derived context only, not full raw analysis payload duplication.

5. Backward compatibility with older `cv_analysis` records can be missed.
- Mitigation: require graceful fallback to flat-evidence behavior when richer semantics are absent.

## Acceptance Criteria

1. `cv_generation` consumes persisted `cv_analysis` evidence semantics when available and falls back gracefully when absent.

2. The generation prompt or prompt-building layer distinguishes evidence intent for at least:
- summary positioning
- experience bullets
- project/domain support

3. Generation debug outputs preserve bounded analysis-aware evidence provenance.

4. The `cv_generation` stage artifact shows bounded upstream `cv_analysis` inputs and selected evidence context for generated and failed rows.

5. `cv_generation` continues to treat fit-gate skips as non-attempted outcomes, not generation failures.

6. Existing historical `cv_analysis` records without the richer fields still generate successfully under the compatibility path.
