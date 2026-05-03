# Starter Baseline Sync Prompt

Use this when you want to sync another repo/worktree to the latest local
`project-OS-starter` baseline.

```text
Sync this repo to the latest local `project-OS-starter` baseline.

Baseline:
- `C:\Users\HOANG PHI LONG DANG\repos\project-OS-starter` (pull latest first)

Target:
- repo/worktree: <path>
- branch: <branch>

Do:
1. Diff target vs latest baseline.
2. Classify each change: adopt / adapt / defer (with reason).
3. Apply relevant updates across docs, prompts, scripts, validators, tests, and config contracts.
4. Preserve target-specific product behavior; keep starter governance/validator intent.
5. Reconcile lineage/status metadata if required by new validator rules.
6. Run verification:
   - `python scripts/validate_repo_contracts.py --fast`
   - plus `validate_planning_lifecycle.py --strict` and `validate_checkpoint_packs.py` if present.
7. Output a short report:
   - baseline commit synced
   - files changed
   - adopted/adapted/deferred list
   - validation results
   - required follow-ups
8. Commit:
   - `Sync latest project-OS-starter baseline`
```

Expected output:
- synced target repo with a concise migration report
