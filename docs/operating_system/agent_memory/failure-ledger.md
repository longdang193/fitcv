# Failure Ledger

Use this file for repeated or important failures, not every small mistake.

## Entry Template

- Title:
- Date:
- Trigger / Context:
- What went wrong:
- Correct behavior:
- Prevention added or required:
- Related artifacts:

## Adapter headers drift across worktrees

- Title: Generated adapter headers used absolute paths
- Date: 2026-04-09
- Trigger / Context: CI hook implementation in a git worktree
- What went wrong: Generated `AGENTS.md` and rule files embedded absolute local paths, so sync and verify drifted across worktrees and would fail in CI.
- Correct behavior: Generated headers should use repo-relative source paths so outputs are stable across machines and worktrees.
- Prevention added or required: Added repo-relative path handling in adapter sync and verify scripts.
- Related artifacts:
  - `scripts/sync_agent_adapters.ps1`
  - `scripts/verify_agent_adapters.ps1`

## Baseline tests drift after pipeline contract changes

- Title: Tests expected old pipeline and control-plane contracts
- Date: 2026-04-09
- Trigger / Context: CI hook rollout exposed failing baseline tests
- What went wrong: Several tests still expected older statuses, older queue helpers, and older export or stage-artifact shapes after the runtime contracts had changed.
- Correct behavior: When pipeline or admin contracts evolve, tests should be updated to the current public contract before those tests are used as CI gates.
- Prevention added or required: Baseline tests were updated before enabling CI hooks; follow-up memory should capture future contract shifts the same way.
- Related artifacts:
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_models.py`
