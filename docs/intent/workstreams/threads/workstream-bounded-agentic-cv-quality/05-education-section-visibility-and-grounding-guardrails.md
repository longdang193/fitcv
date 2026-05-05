---
thread_id: workstream-bounded-agentic-cv-quality.education-section-visibility-and-grounding-guardrails
status: completed
---

# Bounded Change Thread: Education Section Visibility And Grounding Guardrails

## Goal

Prevent Education from appearing in generated CV markdown when settings disable it, and prevent synthetic placeholder education content when no grounded education evidence exists.

## Key Deliverables

- Confirm root-cause boundary for settings, structured generation contract, validator behavior, and rendering.
- Implement bounded guardrails that enforce section visibility and evidence-grounded Education output.
- Add regression tests that cover disabled Education and empty/no-profile-education paths.

## Scope

- in scope:
  - `src/fitcv/cv_generator.py`
  - `src/fitcv/validator.py`
  - `src/fitcv/agentic_cv_generation.py`
  - `tests/test_cv_generator.py`
  - `tests/test_validator.py`
- out of scope:
  - non-Education section policy redesign
  - unrelated control-plane UI refactors

## Dependencies

- Existing CV composition settings contract under `cv.composition.*.enabled`
- Existing structured CV schema and markdown template rendering path
- Existing validator rule set for required/missing section behavior

## Completion Criteria

A thread item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

