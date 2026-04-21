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
- [docs/generated/stage_overview.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/stage_overview.md) for the generated current-state summary
- [docs/generated/stages_index.yaml](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated/stages_index.yaml) for the machine-friendly stage lookup
