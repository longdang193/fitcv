---
feature_type: modify
feature_name: cv_system
status: completed
summary: "Stop `cv_generation` from emitting unresolved candidate-name placeholders such as `Candidate Name`, and add one deterministic repair pass for that specific validation failure."
---

# Candidate-Name Writer And Repair Hardening Plan

## Outcome

Make `cv_generation` robust against unresolved candidate-name placeholders so the only generation-ready job does not get dropped for an easily repairable header identity failure.

After this change:

- the shared writer path should no longer leave `Candidate Name` in the final structured header when a real candidate name is available
- the same narrow deterministic repair should run in both:
  - `Run All`
  - `Stage by Stage`
- validation remains the final safety gate
- debug artifacts clearly show whether acceptance came from the initial write or the deterministic repair pass

## Tasks

1. Trace the active candidate-name source in `cv_generation`

- Inspect the shared final-stage write path in:
  - [pipeline.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/pipeline.py)
  - any CV writer/renderer helpers used by `cv_generation`
- Confirm where the final structured header name currently comes from:
  - prompt output
  - template fallback
  - renderer default
  - post-processing normalization
- Verify that both `Run All` and `Stage by Stage` already converge on the same shared generation logic so the fix can stay mode-agnostic.

2. Make candidate header identity deterministic before acceptance

- Add a narrow normalization step in shared `cv_generation` logic so the final structured header name uses the real candidate profile name when available.
- Ensure unresolved placeholder values such as:
  - `Candidate Name`
  - `[Candidate Name]`
  - `Your Name`
  - `[Your Name]`
  cannot remain as the final structured header identity when a usable real profile name exists.
- Keep the scope limited to candidate identity fields only.

3. Add one deterministic repair path for candidate-name placeholder failures

- When validation fails specifically because of the candidate-name placeholder family:
  - perform one deterministic repair
  - replace only the header identity fields with the real profile name
  - rerender markdown if needed
  - rerun validation once
- Do not use an LLM retry for this repair.
- Do not broaden the repair path to unrelated validation failures.

4. Preserve validation ownership and narrow repair scope

- Keep [validator.py](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/src/fitcv/validator.py) as the final authority that blocks unresolved candidate-name placeholders.
- Do not redesign:
  - broader validation rules
  - section selection
  - evidence grounding
  - general repair strategy for all failures
- Ensure unrelated validation failures still behave exactly as before.

5. Keep debug artifacts explicit

- Update the shared CV-debug capture so it records:
  - initial invalid placeholder output when it occurs
  - `repair_attempt.performed = true`
  - repaired structured/markdown output when the deterministic repair succeeds
  - final acceptance or failure outcome
- Keep artifact scope narrow; do not redesign other debug payloads.

6. Add focused regression coverage

- Extend tests around shared `cv_generation` behavior to prove:
  - placeholder header output is corrected when a real candidate name exists
  - repaired output passes validation
  - markdown and structured header stay aligned after repair
  - unrelated validation failures do not trigger this repair path
- Add focused validator and/or pipeline tests only where needed to prove the end-to-end acceptance behavior.
- Add worker/app tests only if debug artifact behavior or UI rendering depends on the new repair metadata.

7. Sync docs and generated discovery

- Update:
  - [cv_system.yaml](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/cv_system.yaml)
  - [history.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/features/cv_system/history.md)
  - [FitCV-pipeline.md](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/FitCV-pipeline.md)
- Refresh generated discovery under [docs/generated](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/generated).

## Verification

- Focused `cv_generation` / pipeline tests for deterministic candidate-name repair
- Focused validator tests if the repair path depends on specific validation signals
- Focused worker or app tests only if debug artifact fields change materially
- `python -m py_compile` for touched Python modules

## Completion Criteria

- `cv_generation` no longer drops an otherwise valid CV solely because the writer emitted `Candidate Name`
- candidate-name placeholder failures are deterministically repaired when a real profile name is available
- repaired outputs keep structured header and markdown header aligned
- validation remains the final guardrail for unresolved candidate-name placeholders
- both `Run All` and `Stage by Stage` share the same corrected final-stage behavior
