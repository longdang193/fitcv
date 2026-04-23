---
doc_id: pipeline
doc_type: architecture-guide
explains:
  stages:
    - normalize
    - enrich
    - rule_filter
    - shortlist
    - ranking
    - cv_analysis
    - cv_generation
---

# Pipeline

FitCV processes jobs through these ordered stages:

`normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`

## Purpose

The pipeline narrows noisy raw job inputs into a smaller set of grounded, reviewable application outputs while preserving strong operator visibility.

## Ownership Model

- stage boundaries live in `docs/stages/*.source.yaml`
- generated stage contracts live in `docs/stages/*.yaml`
- cross-stage capabilities live in `docs/features/*/feature.source.yaml`

## Recommended References

- [FitCV-pipeline.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md) for the detailed narrative
- [docs/generated/architecture_dag.yaml](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/architecture_dag.yaml) for the generated stage, feature, and dependency topology
- [docs/generated/capability_lineage.yaml](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/capability_lineage.yaml) for the generated capability-level evidence summary
