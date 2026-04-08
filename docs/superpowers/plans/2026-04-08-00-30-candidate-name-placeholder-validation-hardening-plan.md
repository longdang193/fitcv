---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Harden candidate-name placeholder validation so plain or bracketed placeholder identity text can never be accepted in final CV outputs."
---

# Candidate-Name Placeholder Validation Hardening Plan

## Outcome

Make the final-stage validation path reject unresolved candidate-name placeholders whether they appear as:

- plain `Candidate Name`
- bracketed `[Candidate Name]`
- equivalent `Your Name` variants

The fix should work consistently for both:

- structured header fields
- rendered markdown output

## Tasks

1. Trace the active candidate-name validation path

- Inspect [validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/validator.py) to confirm exactly where unresolved placeholder checks are applied.
- Confirm whether current validation operates only on markdown text or already has access to structured header values.
- Keep the scope limited to candidate-name placeholder semantics, not all placeholder families.

2. Add semantic candidate-name placeholder detection

- Expand the unresolved-placeholder logic to detect candidate-name placeholders beyond bracket syntax.
- Cover at minimum:
  - `Candidate Name`
  - `[Candidate Name]`
  - `Your Name`
  - `[Your Name]`
- Make detection:
  - case-insensitive
  - whitespace-tolerant
  - narrowly bounded so ordinary prose is not overblocked

3. Validate structured header identity directly when available

- Add a structured-field validation path for the CV header name so placeholder identity values are caught even when markdown formatting changes.
- Normalize the structured header name before comparison.
- Keep markdown scanning in place as the secondary/fallback guard.

4. Preserve current validation ownership and artifact boundaries

- Do not redesign:
  - broader grounding validation
  - soft-claim validation
  - run artifact shapes
  - stage artifact ownership
- Keep the change scoped to:
  - validation correctness
  - resulting accepted/rejected outcomes

5. Add focused regression coverage

- Extend [test_validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/tests/test_validator.py) to prove:
  - bracketed `[Candidate Name]` still fails
  - plain `Candidate Name` fails
  - structured header `Candidate Name` fails
  - real names still pass
- Add or update pipeline-level regression coverage only if needed to prove accepted final outputs cannot carry placeholder identity names anymore.

6. Sync docs and history

- Update:
  - [cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Refresh generated discovery under [docs/generated](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated).

## Verification

- Focused validator tests for candidate-name placeholder rejection
- Focused pipeline test only if the validation contract needs an end-to-end acceptance guard
- `python -m py_compile` for touched Python modules

## Completion Criteria

- Plain `Candidate Name` can no longer pass final validation
- Bracketed `[Candidate Name]` remains rejected
- Structured header identity and markdown output are both protected
- Accepted CV outputs must use a real candidate name or fail validation
