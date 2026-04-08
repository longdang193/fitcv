---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Stop `cv_generation` from emitting unresolved candidate-name placeholders such as `Candidate Name`, and add a narrow deterministic repair path when that specific validation failure still occurs."
invariants:
  - "Accepted CVs must never contain unresolved candidate-name placeholders in either structured or markdown output."
  - "The writer fix and repair path must stay narrow: no broader CV-generation redesign, prompt-overhaul, or artifact-contract change is part of this rollout."
  - "The repair path must only rewrite candidate-identity placeholder fields; it must not invent new facts or alter evidence-grounded content."
---

# Candidate-Name Writer And Repair Hardening Spec

## Triage

Feature type: MODIFY  
Summary: Prevent the structured CV writer from emitting `Candidate Name`, and add a deterministic fallback repair so this specific validation failure does not zero out the only generation-ready job.  
Reasoning: Latest `Run All` and `Stage by Stage` artifact bundles both show the same remaining CV-generation failure: the writer still emits `Candidate Name`, validation correctly catches it, and no repair path attempts the obvious deterministic fix. This is a narrow correctness and resilience improvement inside `cv_system`, not a broader generation-parity or prompt-redesign project.  
Invariants:
- Accepted CVs must not retain unresolved candidate-name placeholders.
- The repair path must only touch candidate-name placeholder identity fields.
- Existing validation ownership and artifact boundaries must remain intact.
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

The latest bundles in both modes show the same failure pattern:

- `cv_generation` attempts one CV
- the generated structured header still uses `Candidate Name`
- validation correctly rejects it
- no repair attempt is made
- the run ends with `cvs_generated = 0`

Concrete evidence:

- `Stage by Stage`:
  - [cv-debug.json#L645](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a956652b-39d3-4516-8988-f0245ec637d3-artifacts/cv-debug.json#L645)
  - [cv-debug.json#L718](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-a956652b-39d3-4516-8988-f0245ec637d3-artifacts/cv-debug.json#L718)
- `Run All`:
  - [cv-debug.json#L645](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e02e8298-8e6a-42c5-8c18-da564d7e57a2-artifacts/cv-debug.json#L645)
  - [cv-debug.json#L721](/c:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/logs/fitcv-run-e02e8298-8e6a-42c5-8c18-da564d7e57a2-artifacts/cv-debug.json#L721)

So the validator hardening is now doing its job, but the upstream writer and retry behavior are still weak.

## Goal

Make candidate identity in `cv_generation` robust enough that:

- the writer no longer emits placeholder names such as `Candidate Name`
- if that exact failure still slips through, the pipeline applies one safe deterministic repair before final rejection

## Non-Goals

- Redesigning the full structured writer prompt
- Solving cross-mode wording parity
- Redesigning general validation-repair strategy for all validation errors
- Broad artifact-schema changes

## Design

### 1. Make candidate header identity deterministic before generation output is accepted

`cv_generation` should not leave the candidate header name to an unresolved template-like fallback if the real profile name is already known.

The final structured CV header name should be sourced deterministically from the candidate profile identity already available to the stage.

That means:

- if candidate profile has a real name, the generated structured header name must be normalized to that real name
- the writer must not be allowed to keep `Candidate Name`, `[Candidate Name]`, `Your Name`, or similar unresolved identity placeholders as the final header identity

This is a narrow deterministic identity fill, not a broad rewrite of other generated text.

### 2. Add one deterministic repair pass for candidate-name placeholder failures

When validation fails specifically because of an unresolved candidate-name placeholder:

- perform one deterministic repair
- replace only the candidate header identity fields with the real candidate name from the profile
- regenerate markdown from the repaired structured CV if needed
- rerun validation once

This repair should apply only when:

- the real candidate name is known
- the failure reason is limited to the candidate-name placeholder family

The repair must not:

- alter section selection
- rewrite evidence-grounded bullets
- synthesize new claims
- retry with a broader LLM rewrite

### 3. Preserve clear debug provenance

`cv-debug.json` should remain explicit about:

- initial invalid output still containing the placeholder
- repair attempt performed = true
- repaired final output if validation passes
- whether the final acceptance came from deterministic repair rather than first-pass generation

This is an inspection/debugging detail, not an artifact redesign.

### 4. Keep validation as the final safety gate

The existing validator remains the authority that blocks unresolved candidate-name placeholders.

The writer hardening and deterministic repair reduce the chance of failure, but validation must still reject any remaining unresolved candidate-name placeholder after repair.

## Accepted Contract

After this rollout:

- generated CVs must not fail solely because the writer left `Candidate Name` unresolved when a real candidate name is available
- candidate-name placeholder failures should either:
  - be corrected deterministically and accepted, or
  - remain rejected only when the profile lacks a usable real candidate name
- both `Run All` and `Stage by Stage` should show the same repaired behavior because the fix belongs to shared `cv_generation`

## Verification

Required checks:

- structured writer output with `Candidate Name` and a known profile name is deterministically repaired and then accepted
- the repair path does not run for unrelated validation failures
- the repair path updates both structured header identity and rendered markdown header
- debug artifacts record that repair occurred
- both `Run All` and `Stage by Stage` share the same final behavior because they use the same `cv_generation` logic
