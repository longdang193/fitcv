layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-bounded-agentic-cv-quality
map_type: implementation_execution
threads:
  - workstream-bounded-agentic-cv-quality.agentic-cv-quality-analysis-grounding
  - workstream-operator-control-plane.operator-control-plane-agentic-review-actions
specs:
  - docs/superpowers/specs/2026-04-30-cv-markdown-standards-and-consistency-enforcement-spec.md
---

# CV Markdown Standards And Consistency Enforcement Implementation Execution Map

## Scope

Ship a bounded markdown-consistency layer for generated CVs:

- canonical markdown contract
- deterministic normalizer
- markdown-quality validation + status routing
- operator-facing quality observability

## Waves

### Wave 1: Canonical Contract + Prompt Alignment

Primary files:

- `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`
- `src/fitcv/cv_generator.py`
- `tests/test_cv_generator.py`

Deliverables:

- explicit canonical section-order and formatting contract
- prompt alignment with heading/bullet/date expectations
- baseline contract tests for structure expectations

### Wave 2: Deterministic Markdown Normalizer

Primary files:

- `src/fitcv/cv_generator.py`
- `src/fitcv/agentic_cv_generation.py`
- `tests/test_cv_generator.py`

Deliverables:

- bounded post-generation markdown normalization before persistence
- stable heading order, bullet style, and whitespace/date normalization
- tests proving normalization is deterministic and non-destructive

### Wave 3: Markdown-Quality Validator + Runtime Routing

Primary files:

- `src/fitcv/validator.py`
- `src/fitcv/pipeline.py`
- `src/fitcv/agentic_cv_generation.py`
- `tests/test_pipeline_agentic_late_stage.py`

Deliverables:

- markdown-quality checks (required sections, order, density, placeholder guard)
- runtime routing into `accepted` / `validation_failed` / `review_required`
- bounded reason fields for review-required markdown quality cases

### Wave 4: Control Plane + Artifact Observability

Primary files:

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`
- `tests/test_fitcv_cp/test_app.py`

Deliverables:

- run detail visibility for markdown-quality-triggered outcomes
- artifact/export fields carry markdown-quality reasoning
- review audit payload alignment for markdown-quality cases

### Wave 5: Docs + Contract Gate

Primary files:

- `docs/observability.md`
- `docs/api.md` (if endpoint/export semantics changed)

Deliverables:

- operator/developer debugging workflow updated for markdown quality outcomes
- validator-facing doc and contract checks green

## Dependency Order

Hard order:

1. Wave 1 before Wave 2
2. Wave 2 before Wave 3
3. Wave 3 before Wave 4
4. Wave 4 before Wave 5

Reason:

- runtime routing depends on normalized markdown behavior; control-plane/UI must
  consume settled runtime statuses and reason payloads.

## Verification Path

```powershell
python -m pytest tests/test_cv_generator.py -k "markdown or validate or normalize"
python -m pytest tests/test_pipeline_agentic_late_stage.py -k "review_required or validation_failed"
python -m pytest tests/test_fitcv_cp/test_app.py -k "run_detail or review or export"
python scripts/validate_repo_contracts.py --fast
```

## First Buildable Subset

Wave 1 + Wave 2 only:

- canonical markdown contract
- deterministic normalizer

This yields immediate consistency improvements before routing/UI changes land.
