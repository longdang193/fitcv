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

Input jobs contract and normalization: [job-data-input.md](job-data-input.md).

## Stage Responsibilities

- `normalize`: canonicalize incoming jobs
- `enrich`: derive structured job fields and reuse-aware metadata
- `rule_filter`: deterministic gating before expensive steps
- `shortlist`: vector/retrieval candidate narrowing
- `ranking`: authoritative fit scoring and decision labels
- `cv_analysis`: one canonical per-job analyzer owns evidence selection, gap, fit-gate, reuse validity, and generation readiness; pipeline owns batch invocation, persistence, and observations
- `cv_generation`: one canonical `generate_from_analysis` contract for fingerprints, reuse validity, structured generation, validation, repair, acceptance/review meaning, and result shape; direct and LangGraph writers are transport adapters, while pipeline persists canonical `accepted` results only

Shared LLM runtime rule: `enrich`, `ranking`, and `cv_generation` build stage-owned prompts and parse stage-owned outputs through `src/fitcv/llm_runtime.py`. Shared runtime owns routing, credentials, transport, wire fallback, normalized operational failures, provenance, and the only persistable per-call evidence projection. LangGraph remains adapter/orchestrator only.

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

Observability separates run-level and item-level surfaces:

- **run-summary layer**
  - run-level events and summaries remain operator entrypoint surfaces
  - aggregate completion/debug surfaces describe run-wide behavior
- **item-observation layer**
  - item-level analysis/generation traces capture one candidate-job attempt at a time
  - item observations carry reviewer-facing input/output plus structured metadata for filtering

Ownership rule:

- run-summary surfaces answer **how run behaved overall**
- item observations answer **what happened for one candidate-job attempt**
- avoid duplicating full item raw IO into aggregate run-summary payloads

## Portability Expectations

- sqlite backend must preserve operator-visible contracts
- provider/model routing must be config/env controlled, not hardcoded

## Symmetry and Invariance Rules

- AI-stage decisions are backend-invariant: the same input must resolve the same routed AI provider/model regardless of SQLite file location or startup surface.
- Backend differences are persistence-only: storage schema/adapter metadata may differ, but AI decision logic, runtime evidence, stage traces, and provenance semantics remain equivalent.
- Fresh calls emit ordered `llm_runtime_observations`; reuse, replay, resume, blocked, and skipped cases emit zero new evidence.
- The runtime must treat `control_plane.model_routing.parts.*` as authoritative for AI stage provider/model selection.
- Historical late-stage mode fields are read-only compatibility data and never override unified routing or stage meaning.

## AI Credential and Error Contract

- Sole repo-native AI credential input: `FITCV_LLM_API_KEY`.
- Direct and LangGraph adapters receive the same bounded `FITCV_LLM_*` mapping; no credential alias projection is used.

Fail-fast guarantees:

- missing routed AI model/provider -> explicit runtime configuration failure
- missing AI API key for routed provider -> explicit runtime credential failure
- no hidden fallback to legacy provider defaults in unified runtime path

## Related Docs

- [architecture.md](architecture.md)
- [usage.md](usage.md)
- [FitCV-pipeline.md](FitCV-pipeline.md)

