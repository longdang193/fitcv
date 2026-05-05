---
layer: change
artifact_type: plan
status: proposed
parent_thread: workstream-bounded-agentic-cv-quality.cross-section-placeholder-guardrails
parent_spec: docs/superpowers/specs/2026-04-28-agentic-cv-quality-analysis-grounding-spec.md
targets:
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - tests/test_cv_generator.py
  - tests/test_validator.py
related_features:
  - cv_system.analysis-grounded-validation
related_stages:
  - cv_generation
---

# 2026-05-05 Cross-Section Placeholder Guardrails Implementation Plan

## Bounded Change Classification

`change` layer bounded patch: follow-up hardening of existing CV-generation guardrails to close the same synthetic-placeholder risk in non-Education list sections.

## Goal

Prevent synthetic placeholder rows from surviving normalization/validation in additional structured CV list sections (`projects`, `certifications`, `publications`, `languages`, and lightweight checks for `experience`).

## Execution-Map Fit

This plan is a follow-up lane to the completed execution map:
`docs/superpowers/execution_maps/2026-05-05-education-section-visibility-and-grounding-guardrails-implementation-execution-map.md`.

Fit rationale:
- the previous lane closed Education-specific drift;
- this lane applies the same bounded pattern to adjacent sections discovered during post-fix pattern scan.

## Files To Modify

- `src/fitcv/cv_generator.py`
  - generalize placeholder-token sanitization helpers for additional list sections
  - sanitize synthetic rows during `_normalize_structured_cv` and pre-render path
- `src/fitcv/validator.py`
  - add deterministic synthetic-row validation checks for in-scope non-Education sections
- `tests/test_cv_generator.py`
  - add normalization/render tests for synthetic row filtering in new sections
- `tests/test_validator.py`
  - add validation tests asserting synthetic row violations for new sections

## Task Breakdown

- task 1: confirm exact synthetic-row predicates per section
- task 2: implement normalization-time sanitization for in-scope sections
- task 3: implement validator-time synthetic-row checks for in-scope sections
- task 4: add focused regression tests for sanitizer + validator behavior
- task 5: run targeted test suites and capture evidence for checkpoint pack

## Verification

```powershell
pytest -q tests/test_cv_generator.py -k "synthetic or placeholder or normalize_structured_cv"
pytest -q tests/test_validator.py -k "synthetic or placeholder or run_all_validations"
pytest -q tests/test_cv_generator.py tests/test_validator.py
```

## Completion Criteria

1. synthetic placeholder rows are filtered or rejected for each in-scope section,
2. no regression in existing Education guardrail behavior,
3. targeted verification commands pass,
4. thread checkpoint result pack is recorded with evidence and residual-risk notes.

