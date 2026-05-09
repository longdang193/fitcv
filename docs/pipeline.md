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

Stage order:

`normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`

This page is a cross-cutting summary of runtime behavior and ownership.

## Stage Responsibilities

- `normalize`: canonicalize incoming jobs
- `enrich`: derive structured job fields and reuse-aware metadata
- `rule_filter`: deterministic gating before expensive steps
- `shortlist`: vector/retrieval candidate narrowing
- `ranking`: authoritative fit scoring and decision labels
- `cv_analysis`: evidence selection and generation readiness
- `cv_generation`: structured generation, validation, repair, persistence

## Execution Modes

- full run (`Run All`)
- checkpointed run (`Stage by Stage`)

Mode changes pacing, not stage truth semantics.

## Contracts and Evidence

- stage outcomes are stage-owned truth
- operator summaries are derived views
- run artifacts/events must remain consistent with stage-owned outcomes
- `StageResult`/trace fields and run exports are the audit surface

## Two-Layer Observability Ownership

Wave 1 Langfuse observability splits responsibilities across two layers:

- **run-summary layer**
  - root/run trace context and aggregate events remain the operator entrypoint
  - `pipeline_complete` and related summary surfaces stay aggregate-only
  - run-level quality summaries describe distribution, conversion, retry, and health facts across the run
- **item-observation layer**
  - `cv_analysis_item` captures one bounded analysis observation per candidate-job attempt
  - `cv_generation_item` captures one bounded generation observation per candidate-job attempt
  - item observations carry disposition-aware reviewer-facing `input`/`output` plus structured metadata for filtering and joins

Ownership rule:

- run-summary surfaces answer **how run behaved overall**
- item observations answer **what happened for one candidate-job attempt**
- do not duplicate full item-level raw IO into aggregate run-summary payloads

## Portability Expectations

- sqlite and bigquery backends must preserve the same operator-visible contracts
- provider/model routing must be config/env controlled, not hardcoded

## Related Docs

- [architecture.md](architecture.md)
- [usage.md](usage.md)
- [FitCV-pipeline.md](FitCV-pipeline.md)
