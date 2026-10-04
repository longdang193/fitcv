# FitCV First-Pass Acceptance Experiment

Date: 2026-10-02

## Status

Blocked before provider execution. `FITCV_LLM_API_KEY` is not configured in
isolated worktree runtime. No candidate run was started, so incumbent behavior
was not changed and no promotion claim is made.

## Frozen inputs

- Fixture: `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\data\linkedin-2026-10-02-22-52-15.json`
- Fixture SHA-256: `4BA6F4B5459C805E2455E7912120E8CDE6FFB7D274493C44613AC62AD053950D`
- Model configuration: `cx/gpt-5.6-luna`
- Candidate profile: repository private profile configured by `.env.yaml`
- Candidate change: deterministic generation preflight and strengthened existing structured-write prompt contract
- Retrieval policy, model, agent count, verifier count, and workload limits: unchanged

## Evidence

- Candidate preflight records evidence availability, section budget, grounded
  high-value claims, and impossible requirement support.
- Preflight declares `provider_call_count_effect: 0`; it does not skip or add
  provider calls.
- Prompt contract declares exact one-page target, section budgets, omission
  order, and no unsupported filler.
- Same-workload incumbent/candidate comparison remains pending API credentials.

## Decision

Do not promote first-pass changes from unavailable live evidence. Preserve
incumbent baseline and rerun both sides with identical fixture, profile, model,
job set, and run limits after `FITCV_LLM_API_KEY` becomes available.

P1-C and P2 remain deferred.
