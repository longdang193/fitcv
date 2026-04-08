---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Harden CV validation so unresolved candidate-name placeholders such as plain `Candidate Name` can never be accepted."
invariants:
  - "Accepted CVs must not contain unresolved candidate-identity placeholders in either structured or markdown output."
  - "This rollout must stay narrow: fix placeholder-name correctness without redesigning broader validation, artifact, or generation behavior."
---

# Candidate-Name Placeholder Validation Hardening Spec

## Triage

Feature type: MODIFY  
Summary: Close the remaining candidate-name placeholder validation gap so accepted CVs cannot ship with unresolved placeholder identity text.  
Reasoning: `cv_system` already claims unresolved placeholder headers are rejected, but the latest real artifacts still accept plain `Candidate Name` without brackets. This is a narrow correctness fix to the validation contract, not a broader generation redesign.  
Invariants:
- Accepted CVs must never retain unresolved candidate-name placeholder text.
- The validator must treat structured-header and markdown-header candidate-name placeholders consistently.
- Existing non-name placeholder checks and late-stage artifact ownership must remain intact.
Dependencies:
- `cv_system`
- `inspection_debugging`
Affected stages:
- `cv_generation`
Affected features:
- `cv_system`
- `inspection_debugging`
Primary lens: mixed
Affected docs:
  feature_yaml: `docs/features/cv_system/cv_system.yaml`
  feature_history: `docs/features/cv_system/history.md`
  feature_docs:
    - none
  cross_cutting_docs:
    - `docs/FitCV-pipeline.md`
  readme: none
  generated:
    - `docs/generated/features_index.yaml`
    - `docs/generated/feature_overview.md`
Generated refresh required: yes  
Spec needed: yes  
Plan needed: yes

## Problem

The validator already rejects bracketed placeholders such as `[Candidate Name]`, but current succeeded runs still accept plain `Candidate Name` in the final structured header and markdown output.

Current code evidence:

- [validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/validator.py) defines `_UNRESOLVED_PLACEHOLDER_PATTERNS` only for bracketed forms such as:
  - `[your name]`
  - `[candidate name]`
- [validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/validator.py) then merges `_check_unresolved_placeholders(...)` into final grounding violations.

Latest artifact evidence:

- `Run All` accepted output still contains plain `Candidate Name`:
  - [cv-debug.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-c77298c2-2abc-4b02-85b0-5e60b54e6727-artifacts/cv-debug.json)
- `Stage by Stage` accepted output still contains plain `Candidate Name`:
  - [cv-debug.json](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-ae1e3291-ad2f-4758-8f24-7d49d226b40c-artifacts/cv-debug.json)

So the remaining bug is no longer “we miss `[Candidate Name]`”. The real remaining gap is:

- the validator treats bracket syntax as a placeholder
- but it does not treat the plain fallback token `Candidate Name` as a placeholder identity value

## Goal

Make candidate-name placeholder validation semantic enough that placeholder identity text cannot slip through simply by losing brackets.

After this rollout:

- `Candidate Name` must be rejected
- `[Candidate Name]` must still be rejected
- equivalent case/spacing variants must be rejected
- accepted outputs with a real candidate name must continue to pass

## Non-Goals

- Redesigning all unresolved placeholder validation
- Changing ranking, evidence retrieval, or CV-writing behavior broadly
- Introducing exact cross-mode wording parity rules
- Redesigning artifact shapes beyond reflecting the corrected validation outcome

## Design

### 1. Add explicit candidate-name placeholder detection beyond bracket syntax

The validator must detect candidate-name placeholder values in both:

- raw markdown text
- structured CV header fields when available

At minimum, the candidate-name placeholder family should include:

- `Candidate Name`
- `[Candidate Name]`
- `Your Name`
- `[Your Name]`

Detection should be:

- case-insensitive
- whitespace-tolerant
- bounded narrowly to candidate-identity fields and obvious header-line usage so ordinary prose is not overblocked

### 2. Treat structured header identity as authoritative when available

When structured output exists, validation should inspect the structured header name field directly instead of relying only on markdown string scanning.

Why:

- the bug is fundamentally about unresolved identity in the generated header
- structured-field inspection is more precise than only scanning rendered markdown

The structured check should reject if header name resolves to a placeholder-family token after normalization.

### 3. Keep markdown scanning as the fallback/secondary guard

Markdown scanning should remain in place because:

- some validation paths still operate on rendered markdown
- it provides protection when structured output is absent or malformed

But the markdown check should be expanded to catch plain header tokens like:

- `# Candidate Name`
- `**Candidate Name**`

without requiring brackets.

### 4. Preserve narrowness

This fix must stay narrow:

- candidate-name placeholder semantics only
- no speculative expansion into every capitalized phrase
- no redesign of the broader grounding or soft-claim validation model

## Accepted Contract

The validation contract after this rollout is:

- unresolved candidate-name placeholders are correctness failures
- they appear in `grounding_violations`
- they make `valid = false`
- accepted CV artifacts must no longer contain placeholder identity names

## Verification

Required tests:

- existing bracketed `[Candidate Name]` rejection still passes
- plain `Candidate Name` in markdown header is rejected
- plain `Candidate Name` in structured header name is rejected
- real candidate names such as `Nguyen Van A` still pass
- both `Run All` and `Stage by Stage` final accepted outputs fail validation if they carry placeholder identity text

## Expected Source-of-Truth Updates

- [cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
- [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
- [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- generated discovery under [docs/generated](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated)

## Recommendation

Implement this as a focused validation hardening pass now, before any larger cross-mode parity or generation-planning upgrade. It is a small, high-value correctness fix with clear artifact evidence and minimal product ambiguity.
