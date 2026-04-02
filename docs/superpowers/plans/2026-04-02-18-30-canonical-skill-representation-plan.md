---
feature_type: modify
feature_name: none
status: completed
summary: "Implement LLM-backed canonical skill representation for required and preferred skills only, replacing the current lowercased-prose canonical fields."
---

# Canonical Skill Representation Implementation Plan

## Scope

Implement the design in [2026-04-02-18-20-canonical-skill-representation-spec.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/superpowers/specs/2026-04-02-18-20-canonical-skill-representation-spec.md).

This rollout does:

- keep raw `required_skills` and `preferred_skills` exactly as extracted
- replace pseudo-canonical lowercased prose with LLM-backed canonical skill entities
- redefine `required_skills_canonical` and `preferred_skills_canonical` as flattened skill labels derived from entities
- exclude non-skill requirement content from canonical skill outputs
- keep downstream filtering and ranking aligned to the corrected canonical contract

This rollout does not:

- canonicalize every enrich field
- redesign domain, seniority, location, or contract normalization
- auto-promote discovered mappings into the trusted synonym map
- split non-skill requirements into dedicated enrich fields yet

## Source-of-Truth Alignment

Affected cross-cutting docs:

- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/rule_filter.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/ranking.yaml)

Affected code and config:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv/rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/rule_filter.py)
- [src/fitcv/ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/ranking.py)
- [src/fitcv/gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/gap_analysis.py)
- [src/fitcv/validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/validator.py)
- [config/skill_synonyms.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/config/skill_synonyms.yaml)
- BigQuery DDL and migrations for enrich-run tables if entity shape changes require schema updates

Affected tests:

- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)
- [tests/test_rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_rule_filter.py)
- [tests/test_ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_ranking.py)
- [tests/test_gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_gap_analysis.py)
- [tests/test_validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_validator.py)

Generated refresh required:

- none

## Invariants

- Raw `required_skills` and `preferred_skills` must remain preserved and inspectable.
- Canonical skill outputs must contain actual skill concepts only.
- `required_skills_canonical` and `preferred_skills_canonical` must be derived from canonical entities, not from lowercased raw phrases.
- Non-skill requirements must not appear in canonical skill outputs.
- This rollout applies only to `required_skills` and `preferred_skills`.

## Implementation Tasks

### Task 1: Redefine The Enrich Skill Contract

Update the enrich-stage contract so `required_skill_entities` and `preferred_skill_entities` are the primary normalized outputs, and flattened `*_canonical` fields are derived from those entities.

Primary files:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)

Acceptance criteria:

- entity shape includes at least `raw_text`, `canonical`, and `confidence`
- `required_skills_canonical` and `preferred_skills_canonical` are flattened from entities
- long lowercased requirement prose no longer appears in `*_canonical`

### Task 2: Add LLM-Backed Skill Normalization In Enrich

Extend the enrich prompt/response schema or add a tightly scoped enrich-side normalization step so the model returns canonical skill entities for `required_skills` and `preferred_skills`.

Primary files:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- enrich prompt/schema definitions
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)

Acceptance criteria:

- the model can emit multiple canonical skills from one raw requirement phrase
- canonical skill extraction is limited to `required_skills` and `preferred_skills`
- deterministic lowercasing is no longer the primary canonicalization mechanism

### Task 3: Exclude Non-Skill Content From Canonical Outputs

Make the enrich normalization path explicitly skip non-skill requirement content such as degrees, years, languages, and soft traits.

Primary files:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)

Acceptance criteria:

- degree requirements do not show up in canonical skill fields
- years-of-experience phrases do not show up in canonical skill fields
- language requirements do not show up in canonical skill fields
- soft traits do not show up in canonical skill fields

### Task 4: Limit Mapping Suggestions To Real Alias Cases

Adjust `mapping_suggestions` so it only captures reusable alias-to-canonical mappings discovered during the canonical skill path, not whole requirement-sentence reductions.

Primary files:

- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- [tests/test_enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_enrich.py)

Acceptance criteria:

- suggestions still include useful stable aliases like `powerbi -> power bi`
- long phrase-to-skill reductions are not emitted as synonym-map suggestions
- suggestion exports remain reviewable and high precision

### Task 5: Update Downstream Skill Consumers

Repoint downstream logic to the corrected canonical contract and remove any assumptions that extra enrich fields carry canonical skill meaning.

Primary files:

- [src/fitcv/rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/rule_filter.py)
- [src/fitcv/ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/ranking.py)
- [src/fitcv/gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/gap_analysis.py)
- [src/fitcv/validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/validator.py)
- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [tests/test_rule_filter.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_rule_filter.py)
- [tests/test_ranking.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_ranking.py)
- [tests/test_gap_analysis.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_gap_analysis.py)
- [tests/test_validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_validator.py)

Acceptance criteria:

- ranking still uses canonical required/preferred skills where appropriate
- downstream logic no longer treats lowercased requirement prose as skill canonicals
- debug artifacts remain understandable and stage-consistent

### Task 6: Update Enrich Artifact And Persistence Shapes

Ensure stage artifacts and persisted enrich rows expose the corrected entity and canonical outputs cleanly.

Primary files:

- [src/fitcv/pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/pipeline.py)
- [src/fitcv/enrich.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/src/fitcv/enrich.py)
- BigQuery DDL and migrations if the entity JSON shape changes materially
- [tests/test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/tests/test_pipeline.py)

Acceptance criteria:

- enrich-stage artifacts show the corrected canonical skill representation
- `required_skill_entities` and `preferred_skill_entities` are visible and useful for debugging
- persisted JSON companions remain parseable and stable

### Task 7: Sync Cross-Cutting Docs And Stage Contracts

Update the enrich and downstream docs to reflect the corrected meaning of canonical skill representation.

Primary files:

- [docs/FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/FitCV-pipeline.md)
- [docs/stages/enrich.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/enrich.yaml)
- [docs/stages/rule_filter.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/rule_filter.yaml)
- [docs/stages/ranking.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/.worktrees/Stage-by-stage-flow/docs/stages/ranking.yaml)

Acceptance criteria:

- docs describe canonical skills as LLM-normalized skill concepts rather than lowercased phrases
- docs clearly state that only `required_skills` and `preferred_skills` are canonicalized in this rollout
- docs distinguish raw requirement items, canonical skill lists, and skill entities

## Execution Order

1. Complete Task 1 first so the contract is corrected before downstream behavior is touched.
2. Complete Task 2 next because the LLM-backed normalization path is the core behavioral change.
3. Complete Task 3 immediately after to prevent non-skill leakage into canonical outputs.
4. Complete Task 4 once entity normalization is trustworthy.
5. Complete Task 5 after the corrected contract is stable.
6. Complete Task 6 once the runtime representation is final enough to persist and inspect.
7. Complete Task 7 last so docs reflect the implemented contract.

## Verification Plan

Targeted verification should cover:

```powershell
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Stage-by-stage-flow\src'; python -m pytest -q tests\test_enrich.py -k "canonical or entity or mapping"
```

```powershell
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Stage-by-stage-flow\src'; python -m pytest -q tests\test_pipeline.py -k "enrich_sample or required_skills_canonical"
```

```powershell
$env:PYTHONPATH='C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Lib\site-packages;C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\Stage-by-stage-flow\src'; python -m pytest -q tests\test_rule_filter.py tests\test_ranking.py tests\test_gap_analysis.py tests\test_validator.py -k "skill or canonical"
```

Manual verification checklist:

- trigger a run and confirm enrich-stage artifacts no longer show long lowercased requirement prose in `required_skills_canonical`
- confirm non-skill requirements remain visible in raw `required_skills` / `preferred_skills` but not in canonical outputs
- confirm one raw phrase can produce multiple canonical skill entities when appropriate
- confirm `mapping_suggestions` only contains reusable alias cases rather than whole requirement sentences
- confirm ranking still uses the corrected canonical skill outputs as intended

Verification completed in this implementation session:

- `python -m pytest -q '.worktrees\Stage-by-stage-flow\tests\test_enrich.py' -k 'canonical_skill_companions or excludes_non_skill_requirement_content or conservative_alias_fallback or merge_scraped_and_enriched_preserves_raw_and_canonical_enrich_fields'`
- `python -m pytest -q '.worktrees\Stage-by-stage-flow\tests\test_enrich.py' -k 'uses_skill_entities_for_canonical_fields or canonical_skill_companions or excludes_non_skill_requirement_content or conservative_alias_fallback'`
- `python -m pytest -q '.worktrees\Stage-by-stage-flow\tests\test_pipeline.py' -k 'prefers_required_skills_canonical_when_present or enrich_sample_includes_canonical_fields'`
- `python -m pytest -q '.worktrees\Stage-by-stage-flow\tests\test_rule_filter.py' '.worktrees\Stage-by-stage-flow\tests\test_ranking.py' -k 'canonical or must_have_skills_prefers_canonical_skill_list_when_present'`
- `python -m py_compile` over the touched Python modules

## Risks And Mitigations

### Prompt Complexity Risk

Adding LLM-backed canonical normalization can make the enrich response schema and prompt more complex.

Mitigation:

- keep the new normalization scope limited to `required_skills` and `preferred_skills`
- prefer one well-scoped enrich schema extension over many separate semantic passes

### Downstream Contract Drift Risk

Downstream consumers may still assume the old pseudo-canonical behavior.

Mitigation:

- update downstream tests alongside the enrich contract
- make the new entity-first contract explicit in code and docs

### Over-Extraction Risk

The model may extract too many broad or weak concepts from one phrase.

Mitigation:

- require confidence on each entity
- keep raw text attached to each entity
- add tests around representative bad cases from real run artifacts

## Task Status

- [x] Task 1: Redefine the enrich skill contract
- [x] Task 2: Add LLM-backed skill normalization in enrich
- [x] Task 3: Exclude non-skill content from canonical outputs
- [x] Task 4: Limit mapping suggestions to real alias cases
- [x] Task 5: Update downstream skill consumers
- [x] Task 6: Update enrich artifact and persistence shapes
- [x] Task 7: Sync cross-cutting docs and stage contracts
