# Audit Report With Evidence

## Metadata

- Audit ID: `20260714-2237-phase5-focused-test-drift`
- Status: `resolved`
- Severity: `medium`
- Owner: `Codex`
- Created At: `2026-07-14T22:37:38+02:00`
- Updated At: `2026-07-15T11:19:36+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-14-20-54-fitcv-llm-runtime-spine-phase-5-observability-parity-closeout-plan.md`

## Scope

- Environment: `Windows, PowerShell, Python 3.13.5, pytest 8.3.5`
- Commit/Branch: `732383cf41afd6cb032dcf4c61f2dc4e193e237d` on `codex/fitcv-llm-runtime-spine-phase1`
- Affected Surface: Phase 5 pipeline fixtures, runtime-observation contract tests, and Windows local startup safety

## Findings

### Finding `F1`: stale fixtures did not model canonical runtime observations

- Classification: `spec-mismatch`
- Impact: six focused pipeline tests failed after the runtime-evidence contract became canonical.
- Expected Behavior: fresh LLM calls expose ordered `llm_runtime_observations`; stage traces use `stage_execution_trace`; enrich doubles accept the runtime observation callback.
- Actual Behavior: generation fixtures exposed legacy provenance only, analysis asserted the former trace family and synthetic provenance, and enrich doubles omitted the callback.

### Finding `F2`: full-suite environment fixture and stale prompt test

- Classification: `environment` and `spec-mismatch`
- Impact: full regression reported two failures outside the focused Phase 5 gate.
- Expected Behavior: worktree contains the gitignored local private profile fixture, and structured prompt tests supply every required allow-list variable.
- Actual Behavior: the private profile existed only in the root workspace, while the unchanged structured prompt test omitted variables added to its template in May 2026.

### Finding `F3`: false-like dotenv value selected queue mode without Redis

- Classification: `environment` and `runtime-safety`
- Impact: closure regression failed because Windows startup retained `FITCV_CP_INLINE_EXECUTION=false` even when `REDIS_URL` was absent.
- Expected Behavior: bare Windows startup without a configured queue backend uses inline execution.
- Actual Behavior: `build_app` reloaded the dotenv value and the safety guard treated any non-empty value as authoritative.

## Evidence

- Logs/Text: `evidence/results/before.log`
- Logs/Text: `evidence/results/after.log`
- Logs/Text: `evidence/results/full-suite-before.log`
- Logs/Text: `evidence/results/full-suite-after.log`
- Logs/Text: `evidence/results/closure-full-suite-before.txt`
- Logs/Text: `evidence/results/closure-full-suite-after.txt`

## Reproduction

- Preconditions:
  - Phase 5 working tree before focused fixture repair
- Steps:
  1. Run the six focused pipeline tests listed in `repro/repro_steps.md`.
  2. Observe six deterministic failures in `before.log`.
  3. Apply canonical fixture and assertion updates.
  4. Rerun the same command and observe `6 passed` in `after.log`.
  5. Run the closure full suite and observe the deterministic Windows startup failure in `closure-full-suite-before.txt`.
  6. Apply the shared startup guard fix and observe `1931 passed, 3 skipped` in `closure-full-suite-after.txt`.
- Commands: see `repro/repro_steps.md`.
- Determinism notes: same tests, process type, and repository state; no network calls.

## Root Cause And Boundary

- Failure boundary: test fixtures at the pipeline/runtime-observation contract boundary.
- Root cause summary: Phase 5 tests still modeled old runtime contracts; full-suite setup lacked one gitignored local fixture, one prompt test lagged required variables, and the Windows startup guard trusted a false-like dotenv value without confirming a queue backend existed.

## Fix And Verification

- Fix summary: add canonical generation observations, update enrich doubles and stage-neutral trace assertions, restore the ignored local profile, add required prompt variables, and force Windows inline execution when `REDIS_URL` is absent.
- Verification commands: see `repro/repro_steps.md`.
- Verification evidence links:
  - `evidence/results/after.log`
  - `evidence/results/closure-full-suite-after.txt`

## Risk And Disposition

- Residual risk: queue mode still requires an explicit reachable `REDIS_URL`; bare Windows startup now avoids silently selecting it.
- Disposition decision: `resolved`
- Follow-ups: none for current closure lane.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
