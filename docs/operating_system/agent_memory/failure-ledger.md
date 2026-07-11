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

## Pipeline truth keyed only by mutable job_url hides filter/outcome state

- Title: Per-job pipeline truth must not rely on mutable destination URLs alone
- Date: 2026-06-26
- Trigger / Context: Enriched Jobs rows showed empty `Filter` and `Pipeline Outcome` even when run succeeded and downstream pipeline evidence existed.
- What went wrong: Pipeline export, rule-filter truth, and control-plane joins used `job_url` string equality as primary identity. Jobs could start as Indeed URLs and later become destination-site URLs, so per-row truth split across artifacts. SQLite mode also skipped `rule_filter_results` persistence and UI guessed pass state from export rows.
- Correct behavior: Preserve stable per-job identity across stages using `raw_job_fingerprint` first, keep URL normalization only as secondary fallback, persist full rule-filter rows in sqlite as well as BigQuery, and keep unknown truth unknown rather than synthesizing `passed=True`.
- Prevention added or required: Regression tests for URL drift and sqlite parity; pipeline/control-plane helpers that index by fingerprint plus normalized URL fallback; local `rule_filter_results` persistence path.
- Related artifacts:
  - `src/fitcv/pipeline.py`
  - `src/fitcv/pipeline_stages/common.py`
  - `src/fitcv/rule_filter.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/bq_store.py`
  - `tests/test_pipeline.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_storage_backend_parity.py`
