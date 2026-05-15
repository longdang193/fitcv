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

## Generated adapter headers drift across worktrees

- Title: Generated adapter headers must use repo-relative source paths
- Date: 2026-04-09
- Trigger / Context: Adapter verification ran in a different machine path or git worktree.
- What went wrong: Generated `AGENTS.md` or rule files embedded absolute local paths, so sync and verify drifted across worktrees and CI.
- Correct behavior: Generated headers should use repo-relative source paths so outputs stay stable across machines and worktrees.
- Prevention added or required: Keep repo-relative path handling in the adapter sync and verify scripts.
- Related artifacts:
  - `scripts/sync_agent_adapters.ps1`
  - `scripts/verify_agent_adapters.ps1`

## Publication dry runs should not require a public remote

- Title: Dry-run publication should not depend on push-only remote state
- Date: 2026-04-09
- Trigger / Context: Publication-boundary validation ran in CI or a local repo without a configured public remote.
- What went wrong: The publication script resolved the public remote even when `-Push` was not requested, causing dry runs to fail for the wrong reason.
- Correct behavior: Dry-run publication should validate the export boundary without requiring the public remote; remote resolution is only required for `-Push`.
- Prevention added or required: Keep the public-remote lookup behind the `-Push` path.
- Related artifacts:
  - `scripts/publish_public_repo.ps1`

## Control-plane run detail showed "No events yet" while worker completed run

- Title: Web/worker data volume split causes false queued/no-events state
- Date: 2026-05-15
- Trigger / Context: Live run debugging for FitCV control-plane showed run detail stuck at queued with empty timeline.
- What went wrong: Worker consumed and completed RQ jobs, but web API still returned `status=queued`, `started_at=null`, and `events=[]`. Root cause was split storage: web and worker containers did not share `/app/data`, so state/events persisted to different filesystems.
- Correct behavior: Web and worker must mount same runtime data directory so run state/events/jobs are single-source and immediately visible across services.
- Prevention added or required: In `docker-compose.yml`, mount `./data:/app/data` for both `web` and `worker` services (not uploads-only mount).
- Related artifacts:
  - `docker-compose.yml`
  - `docs/usage.md`
  - `docs/setup.md`
  - Live run evidence: run `d054af9b-efd2-4fd0-997b-503300b8b464` transitioned to running/succeeded with non-empty events after mount fix.
