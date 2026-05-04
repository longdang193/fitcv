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

## Portability Expectations

- sqlite and bigquery backends must preserve the same operator-visible contracts
- provider/model routing must be config/env controlled, not hardcoded

## Related Docs

- [architecture.md](architecture.md)
- [usage.md](usage.md)
- [FitCV-pipeline.md](FitCV-pipeline.md)
