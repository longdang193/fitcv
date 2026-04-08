---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Implement bounded semantic support for required-skill and role channels in cv_analysis while preserving artifact clarity and runtime bounds."
---

# Implementation Plan: CV Analysis Semantic Support For Skill And Role Channels

## Objective

Implement bounded hybrid lexical-plus-semantic scoring for:

- `required_skill_support`
- `role_alignment`

while preserving:

- current domain/responsibility semantic behavior
- explicit lexical / semantic / combined artifact reporting
- the existing bounded channel-pool evidence-retrieval model

## Scope

Primary code areas:

- [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py)
- [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py)
- [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/settings_schema.py)

Primary docs:

- [cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
- [pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/pipeline_performance/pipeline_performance.yaml)
- [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)

Primary tests:

- [test_evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_evidence.py)
- [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py)

## Tasks

### 1. Extend semantic-alignment config for skill and role channels

Add explicit hybrid-weight settings for:

- required-skill lexical weight
- required-skill semantic weight
- role lexical weight
- role semantic weight

Work:

- extend semantic-alignment defaults in [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py)
- surface the settings in [settings_schema.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv_cp/settings_schema.py)
- keep backward-compatible defaults so existing configs remain valid

Done when:

- missing config still behaves safely
- new weights are available to runtime and admin settings

### 2. Add semantic text construction for required-skill support

Create a bounded semantic comparison path for required-skill support.

Work:

- define compact job-side required-skill text assembly
- define compact candidate-evidence skill text assembly
- reuse existing semantic runtime-state and embedding cache helpers
- keep lexical overlap as part of the hybrid score

Done when:

- `required_skill_support` can produce a non-zero semantic component
- artifact output still contains lexical / semantic / combined

### 3. Add semantic text construction for role alignment

Create a bounded semantic comparison path for role alignment.

Work:

- define compact role-intent text for the job
- define compact role-positioning text for candidate evidence
- preserve lexical/family heuristics as part of the hybrid score

Done when:

- `role_alignment` can produce a non-zero semantic component
- family/title lexical heuristics still participate in the final score

### 4. Extend channel scoring and semantic-method reporting

Update the channel-score dispatcher so the two upgraded channels use hybrid scoring instead of forced `semantic: 0.0`.

Work:

- replace lexical-only returns in [evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/evidence.py)
- expand `_semantic_methods(...)` to include all channels that can use semantic support
- keep output shape stable for downstream consumers

Done when:

- stage artifacts no longer imply semantics only exist for domain/responsibility
- semantic-method reporting is accurate for all supported channels

### 5. Keep runtime bounded and observable

Ensure the upgrade does not create unbounded semantic fan-out.

Work:

- stay within the current per-channel pool model
- reuse existing runtime-state accounting
- verify channel-pool size still bounds candidate selection
- confirm embedding-count diagnostics remain interpretable

Done when:

- no new unbounded retrieval path exists
- diagnostics still expose bounded counts and reuse state

### 6. Refresh stage artifact and results diagnostics as needed

Update stage artifact assembly only where needed so the richer semantic output is reflected clearly in `cv_analysis` diagnostics.

Work:

- verify [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py) preserves the new channel subscores and semantic methods
- ensure `cv_generation` still receives the intended channel semantics through selected evidence

Done when:

- `cv_analysis.json` shows meaningful semantic support for skill and role channels when available
- downstream CV-generation debug remains coherent

### 7. Add focused regression tests

Add tests that prove the new behavior and protect against regression.

Required coverage:

- required-skill channel can receive semantic lift from non-exact but related wording
- role-alignment channel can receive semantic lift from semantically similar role phrasing
- lexical-only exact matches still work
- stage artifact reporting includes updated `semantic_methods`
- bounded runtime invariants still hold

Suggested test locations:

- [test_evidence.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_evidence.py)
- [test_pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_pipeline.py)

Done when:

- focused evidence/pipeline slices pass

### 8. Sync docs and generated discovery

Update the source-of-truth docs after behavior changes.

Work:

- update [cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
- update [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
- update [pipeline_performance.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/pipeline_performance/pipeline_performance.yaml)
- update [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md) if channel semantics are described there
- refresh generated discovery files if the docs generator depends on the touched source docs

Done when:

- docs reflect the new hybrid semantic contract

## Verification

Before completion:

1. Run focused evidence tests.
2. Run focused pipeline tests covering `cv_analysis` artifacts.
3. Run `python -m py_compile` on touched Python modules.
4. Inspect one representative `cv_analysis` artifact to confirm:
   - `required_skill_support.semantic` can be non-zero
   - `role_alignment.semantic` can be non-zero
   - `semantic_methods` names all supported channels accurately

## Risks

- semantic support may become too permissive and blur genuine skill distinctions
- role semantic lift may over-credit adjacent roles
- runtime cost may rise if text construction is not kept compact

## Completion Criteria

- required-skill and role channels both support bounded hybrid scoring
- artifacts remain explicit and interpretable
- tests cover the new channel behavior
- docs and generated discovery are synced
