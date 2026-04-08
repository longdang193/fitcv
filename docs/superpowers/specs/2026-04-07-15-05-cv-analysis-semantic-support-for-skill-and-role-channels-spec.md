---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Extend cv_analysis semantic alignment so required-skill support and role alignment can use bounded semantic scoring instead of staying lexical-only."
invariants:
  - "Required-skill and role channels must remain interpretable and debuggable with explicit lexical/semantic/combined subscores."
  - "Semantic support must stay bounded by the existing cv_analysis evidence-retrieval budget and must not introduce unbounded fan-out."
  - "Domain and responsibility channels remain supported and must keep their current stage-artifact visibility."
---

# CV Analysis Semantic Support For Skill And Role Channels

## Problem

The current `cv_analysis` semantic-alignment design only applies semantic scoring to:

- `domain_alignment`
- `responsibility_alignment`

It does **not** apply semantic scoring to:

- `required_skill_support`
- `role_alignment`

That behavior is hard-coded in [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py), where:

- lexical-only `required_skill_support` returns `semantic: 0.0`
- lexical-only `role_alignment` returns `semantic: 0.0`
- only domain and responsibility call the semantic component helpers

This creates a design drift between:

- what operators expect when `cv_analysis.semantic_alignment.enabled = true`
- what the pipeline actually does for the most important fit channels

In the reviewed run artifacts, that drift showed up clearly:

- technical jobs with explicit skills like `SQL`, `dbt`, `Azure`, and `Python` still produced `required_skill_support.semantic = 0.0`
- role-positioning evidence still produced `role_alignment.semantic = 0.0`
- only `domain_alignment` and `responsibility_alignment` benefited from embedding similarity

As a result, semantic alignment currently helps broad topical/contextual matching more than hard-fit channels, which weakens both:

- candidate discrimination quality
- the value of semantic-alignment cost

## Observed Evidence

### Code-level root cause

In [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py):

- [evidence.py:1085](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py#L1085)
  - `required_skill_support` returns lexical-only output with `semantic: 0.0`
- [evidence.py:1088](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py#L1088)
  - `role_alignment` returns lexical-only output with `semantic: 0.0`
- [evidence.py:1010](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py#L1010)
  - `domain_alignment` has hybrid lexical+semantic scoring
- [evidence.py:1043](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py#L1043)
  - `responsibility_alignment` has hybrid lexical+semantic scoring
- [evidence.py:363](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py#L363)
  - semantic methods are only declared for `domain_alignment` and `responsibility_alignment`

### Artifact-level evidence

In the reviewed run:

- [cv_analysis.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-d4a4ea1f-4292-4d47-bcc8-38f503f6c5e8-artifacts/cv_analysis.json)
  - repeated `required_skill_support.semantic = 0.0`
  - repeated `role_alignment.semantic = 0.0`
  - positive semantic signal on `domain_alignment`
  - positive semantic signal on `responsibility_alignment`

And the sample job input:

- [sample_data_engineer_jobs2.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/data/sample_data_engineer_jobs2.json)
  - contains concrete technical/role-heavy language such as `SQL`, `dbt`, `Azure`, `Python`, `machine learning`, and explicit role expectations

So the observed zero semantic lift is not explained by vague input alone. It is explained by the scoring contract.

## Goal

Make semantic alignment meaningfully available to the two most important CV-analysis fit channels:

- `required_skill_support`
- `role_alignment`

while keeping the system:

- bounded
- debuggable
- backward-compatible in artifact shape

## Non-Goals

- replacing lexical scoring
- removing existing domain/responsibility semantic support
- introducing unbounded all-to-all embedding comparisons
- changing the final meaning of channel labels in the CV prompt contract

## Proposed Design

### 1. Upgrade required-skill support to hybrid scoring

`required_skill_support` should move from lexical-only scoring to hybrid lexical+semantic scoring.

#### Lexical portion

Keep the current exact/near-exact overlap behavior as the lexical component.

This preserves strong precision for:

- explicit skill matches
- canonicalized skills already extracted into evidence items

#### Semantic portion

Add a bounded semantic component that compares:

- job-side required-skill text
- candidate evidence skill text / skill-bearing evidence text

The semantic path should help with cases like:

- related but differently phrased tools
- skill statements expressed in bullets rather than canonical skill arrays
- partial synonym / abstraction matches

This semantic support must remain bounded by the same evidence-selection runtime budget model already used in `cv_analysis`.

### 2. Upgrade role alignment to hybrid scoring

`role_alignment` should move from role-family/title lexical heuristics to hybrid lexical+semantic scoring.

#### Lexical portion

Keep:

- role-family exact match
- role-family neighbor match
- title token overlap

These are still valuable and should remain part of the score.

#### Semantic portion

Add a bounded semantic comparison between:

- job-side role/title intent
- candidate evidence role/title/career-positioning text

This semantic support should help in cases like:

- `Data Engineer` vs `Analytics Engineer`
- `Platform Data Engineer` vs `Data Infrastructure Engineer`
- evidence whose strongest role match appears in description text rather than the normalized role field alone

### 3. Extend semantic configuration explicitly

The config contract should become explicit that semantic alignment supports four channels, not two.

Current config already covers:

- enable flag
- model
- domain lexical/semantic weights
- responsibility lexical/semantic weights
- channel pool size

The upgraded design should add bounded weight controls for:

- required-skill lexical weight
- required-skill semantic weight
- role lexical weight
- role semantic weight

These should live beside the existing semantic-alignment settings, not in a separate ad hoc room.

### 4. Extend semantic-method reporting

The stage artifact should no longer imply that semantic alignment only exists for domain and responsibility.

`semantic_methods` should report active methods for any channel that can use semantic support:

- `required_skill_support`
- `role_alignment`
- `domain_alignment`
- `responsibility_alignment`

If a channel is configured lexical-only for a run, that should be explicit rather than silently surfacing `semantic: 0.0`.

### 5. Keep artifacts debuggable

For every channel, the artifact contract should remain:

- `lexical`
- `semantic`
- `combined`

This is important because the purpose of the upgrade is not just stronger retrieval. It is also clearer diagnosis.

After the change, `semantic: 0.0` should mean:

- semantic was attempted but found no lift

not:

- semantic is structurally impossible for this channel

### 6. Preserve bounded runtime behavior

The upgrade must not explode evidence-retrieval work.

The semantic additions should:

- reuse the existing semantic runtime-state / embedding cache machinery
- stay inside the current channel-pool model
- avoid separate unbounded candidate fan-out for skills or roles

If needed, the implementation may derive compact job-side texts for:

- required skills
- role intent

but should not create a second parallel retrieval system.

## Expected Outcome

After this change:

- semantic alignment will assist hard-fit channels, not just contextual channels
- required-skill and role evidence should no longer be trapped in lexical-only matching
- `cv_analysis` artifacts will better reflect what semantic alignment is actually doing
- operators can more honestly evaluate whether semantic alignment is worth its cost

## Risks

### 1. Semantic overreach on skill matching

If semantic scoring is too permissive, it may blur important distinctions between:

- adjacent but non-equivalent tools
- broad domain familiarity and concrete skill support

Mitigation:

- keep lexical support in the hybrid score
- keep skill-channel weights conservative
- preserve artifact transparency

### 2. Role inflation

Semantic role support may over-credit loosely adjacent positions.

Mitigation:

- retain role-family lexical heuristics
- use semantic support as additive/bounded lift, not sole authority

### 3. Latency increase

Adding semantic support to two more channels can increase CV-analysis cost.

Mitigation:

- reuse existing embedding runtime-state
- keep bounded pool size
- instrument channel-level semantic counts clearly

## Acceptance Criteria

1. `required_skill_support` and `role_alignment` can produce non-zero semantic subscores when semantic alignment is enabled.
2. Their artifacts still expose lexical / semantic / combined subscores explicitly.
3. `semantic_methods` and related provenance clearly describe all channels capable of semantic support.
4. The runtime remains bounded by the existing channel-pool/evidence-selection design.
5. Existing domain/responsibility semantic behavior remains intact.
6. Stage artifacts and feature docs no longer imply that semantic alignment only applies to domain and responsibility.

## Triage

Feature type: MODIFY  
Summary: Extend `cv_analysis` semantic alignment so required-skill and role channels use bounded hybrid scoring instead of lexical-only scoring.  
Reasoning: This is an existing `cv_system` behavior change with secondary performance implications, not a new feature family.  
Invariants:
- Required-skill and role channels must remain interpretable and artifact-visible.
- Semantic support must stay bounded within the current `cv_analysis` evidence-selection architecture.
- Domain and responsibility semantic support must remain preserved.
Dependencies:
- `src/fitcv/evidence.py`
- `src/fitcv/pipeline.py`
- `docs/features/cv_system/cv_system.yaml`
- `docs/features/pipeline_performance/pipeline_performance.yaml`
Affected stages:
- `cv_analysis`
- `cv_generation`
Affected features:
- `cv_system`
- `pipeline_performance`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/cv_system/cv_system.yaml`
  feature_history: `docs/features/cv_system/history.md`
  feature_docs:
    - `docs/features/cv_system/history.md`
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
Generated refresh required: yes
Spec needed: yes
Plan needed: yes
Risk level: medium
