---
thread_id: workstream-bounded-agentic-cv-quality.cross-section-placeholder-guardrails
status: active
---

# Bounded Change Thread: Cross-Section Placeholder Guardrails

## Goal

Extend the Education placeholder-guardrail pattern to other generated CV list sections that can still admit synthetic placeholder rows.

## Key Deliverables

- Confirm which sections remain exposed after the Education fix.
- Implement bounded sanitization/validation guardrails for in-scope sections.
- Add focused regression tests for synthetic placeholder-row rejection across those sections.

## Scope

- in scope:
  - `src/fitcv/cv_generator.py`
  - `src/fitcv/validator.py`
  - `tests/test_cv_generator.py`
  - `tests/test_validator.py`
- out of scope:
  - control-plane UI changes
  - prompt-template redesign beyond bounded placeholder handling

## Dependencies

- Existing Education guardrail implementation (`05-education-section-visibility-and-grounding-guardrails`)
- Existing bounded-agentic-cv-quality analysis grounding spec

## Completion Criteria

A thread item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

