---
doc_id: pipeline
doc_type: architecture-guide
explains:
  stages:
    - cv_analysis
    - cv_generation
    - enrich
    - normalize
    - ranking
    - rule_filter
    - shortlist
---

# Pipeline

FitCV processes jobs through this ordered pipeline:

`normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`

This page describes the cross-cutting flow and ownership model. Detailed stage
contracts remain in `docs/stages/`.

## What The Pipeline Does

The pipeline turns noisy job input into a smaller set of high-confidence,
inspectable application outputs. It intentionally combines:

- deterministic filtering
- retrieval and ranking
- grounded CV analysis
- validated CV generation
- strong run-detail inspection and artifact export

## Stage Roles

- `normalize`
  - turns raw input into stable run-scoped job records
- `enrich`
  - builds structured job semantics and reuse-aware normalized fields
- `rule_filter`
  - removes obvious mismatches before expensive downstream work
- `shortlist`
  - retrieves likely matches for deeper evaluation
- `ranking`
  - makes the authoritative post-filter fit decision
- `cv_analysis`
  - gathers candidate evidence and decides whether a job is truly ready for
    generation
- `cv_generation`
  - writes, validates, repairs when safe, and persists CV outputs

## Execution Model

Runs are triggered through the control plane and executed by the worker. The
repo supports both:

- end-to-end execution with `Run All`
- checkpointed execution with `Stage by Stage` and explicit continue actions

The important invariant is that input mode affects pacing and checkpoints, not
the meaning of downstream stage truth.

## Runtime Truth And Inspection

The recent pipeline work tightened a few repo-wide rules that matter to anyone
reading results:

- stage-owned statuses stay canonical
- operator labels and summaries are derived views over stage truth
- late-stage events and artifacts should agree with stage-owned outcomes
- run-detail surfaces are for inspection, not a second competing truth model

## Source Of Truth Layers

- human-owned stage metadata:
  - `docs/stages/<stage_id>.source.yaml`
- generated stage contracts:
  - `docs/stages/<stage_id>.yaml`
- feature-level cross-stage ownership:
  - `docs/features/<feature_id>/feature.source.yaml`

## Related Docs

- [FitCV-pipeline.md](FitCV-pipeline.md)
- [architecture.md](architecture.md)
- [docs/generated/architecture_dag.yaml](generated/architecture_dag.yaml)
- [docs/generated/capability_lineage.yaml](generated/capability_lineage.yaml)
