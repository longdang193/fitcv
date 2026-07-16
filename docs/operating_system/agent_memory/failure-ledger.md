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

## Inline terminal status can precede artifact mirror settle

- Title: Inline run verification must wait for mirror settle, not status alone
- Date: 2026-07-12
- Trigger / Context: Artifact parity verification for FitCV inline/TestClient runs after terminal `succeeded` state.
- What went wrong: Verification checked endpoint and bundle immediately after run status became terminal. Inline background thread had not finished mirror write yet, causing false drift: missing mirror files and transient payload fingerprint mismatch.
- Correct behavior: For inline runs, wait for deterministic mirror file set or equivalent post-terminal settle signal before concluding artifact parity.
- Prevention added or required: Live-run verification scripts should use a short settle loop after terminal status when `FITCV_CP_INLINE_EXECUTION=true`.
- Related artifacts:
  - `docs/superpowers/plans/audit/20260712-2358-review-synonym-artifact-truth-split/report.md`
  - `runtime/inline-artifact-parity-settled-e92720d8-e703-4879-bd67-689e0f643cd3/comparison.json`

## Launcher-only dotenv loading breaks worker/web symmetry

- Title: Runtime entry modules must self-load `.env` defaults, not rely on launcher scripts alone
- Date: 2026-07-12
- Trigger / Context: Local queue-mode CV generation failed with `OpenAI-compatible CV generation routing requires API key in env.` even though repo `.env` contained `OPENAI_API_KEY`.
- What went wrong: `fitcv_cp.main` loaded `.env` defaults in-process, but `fitcv_cp.worker_job` did not. Web path could see env-backed routing inputs while worker path depended on external launcher injection. Starting worker outside canonical PowerShell script, or before `.env` changed, split runtime truth.
- Correct behavior: Web and worker entrypoints should share one Python-side dotenv default loader so runtime env behavior is symmetric regardless of launcher.
- Prevention added or required: Keep shared loader in `src/fitcv_cp/env_defaults.py`; call it from control-plane web startup and worker execution entrypoints before routing/key validation. On Windows, force inline execution when `REDIS_URL` is absent so a false-like dotenv value cannot select an unavailable queue backend.
- Related artifacts:
  - `src/fitcv_cp/env_defaults.py`
  - `src/fitcv_cp/main.py`
  - `src/fitcv_cp/worker_job.py`
  - `tests/test_fitcv_cp/test_env_defaults.py`
  - `tests/test_fitcv_cp/test_worker_job.py`

## PowerShell `$args` parameter swallowed verification command arguments

- Title: Do not name PowerShell wrapper parameters `$args`
- Date: 2026-07-14
- Trigger / Context: Phase 3 verification used a PowerShell helper intended to run several `python -m pytest` commands.
- What went wrong: The helper declared a parameter named `$args`, colliding with PowerShell's automatic `$args` variable. `python` received no CLI arguments, launched interactive mode, and flooded terminal output until the process was stopped.
- Correct behavior: Use a distinct parameter such as `$commandArgs`, or invoke verification commands directly with explicit `$LASTEXITCODE` checks.
- Prevention added or required: Avoid `$args` as a declared parameter in PowerShell command wrappers; prefer direct commands for verification gates.
- Related artifacts:
  - `docs/superpowers/plans/2026-07-14-17-58-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-plan.md`
## PowerShell double-quoted Markdown can corrupt backticks and line endings

- Title: Use literal-safe writes for Markdown containing backticks
- Date: 2026-07-14
- Trigger / Context: Phase 4 lifecycle closeout inserted Markdown code spans through PowerShell double-quoted replacement strings.
- What went wrong: PowerShell treated backticks as escape characters, mutating words such as `stage`, and a broad rewrite introduced line-ending drift that `git diff --check` reported as trailing whitespace.
- Correct behavior: Use single-quoted literal strings for Markdown code spans, normalize edited text to LF before writing, and run `git diff --check` immediately after scripted doc edits.
- Prevention added or required: Avoid PowerShell double-quoted replacement text when content contains Markdown backticks; restore and reapply only affected files if corruption appears.
- Related artifacts:
  - `docs/pipeline.md`
  - `docs/architecture.md`
  - `docs/configuration.md`
  - `docs/stages/enrich.source.yaml`
  - `docs/stages/ranking.source.yaml`

## Provider work can be healthy while stage timeline appears stalled

- Title: Reporter callbacks are liveness contracts, not debug toggles
- Date: 2026-07-15
- Trigger / Context: A 13-job live run continued making provider calls while enrichment and CV generation emitted no periodic stage events.
- What went wrong: Enrichment silently discarded an available heartbeat callback unless an env switch was enabled, and CV generation blocked on `as_completed` without timed progress emission.
- Correct behavior: When a reporter callback exists, long provider stages emit bounded periodic heartbeats without changing business semantics or creating extra LLM calls. Single-item and concurrent CV-generation batches use the same executor/wait skeleton.
- Prevention added or required: Keep liveness callback activation contract-driven; use timed `wait(..., FIRST_COMPLETED)` around pending futures; cover callback-enabled, single-item, concurrent, and live artifact cases. Verification runs must also disable tracked SSOT mutation unless mutation is scenario scope.
- Related artifacts:
  - `src/fitcv/pipeline.py`
  - `tests/test_pipeline.py`
  - `tests/test_pipeline_agentic_late_stage.py`
  - `docs/superpowers/plans/audit/20260714-2350-phase5-live-run-drift/`

## Configured concurrency cap was reported as effective runtime use

- Title: Effective concurrency must be derived from runnable work, not copied from settings
- Date: 2026-07-15
- Trigger / Context: Live-run artifacts reported enrichment and CV-generation effective concurrency equal to configured caps even when only two enrich batches or three CV rows existed; CV-analysis concurrency and CV-generation pacing settings were present but not fully consumed.
- What went wrong: Stage events treated configured limits as observed execution, while one stage remained serial and one persisted pacing setting was a no-op. This split settings truth, executor behavior, and observability.
- Correct behavior: Keep configured concurrency as a cap, derive effective concurrency as `min(configured, runnable_work_items)`, use that value for executor size and worker slots, and emit both values. Persisted runtime settings must be consumed or removed.
- Prevention added or required: Route all LLM stages through the shared effective-concurrency rule; preserve deterministic result order; test zero-work, under-cap, over-cap, concurrent overlap, and pacing cases.
- Related artifacts:
  - `src/fitcv/pipeline.py`
  - `tests/test_pipeline.py`
  - `tests/test_pipeline_agentic_late_stage.py`
  - `docs/configuration.md`
  - `docs/observability.md`

## Cross-repo adapters need symmetric secret containment

- Title: Cross-repo adapters need symmetric secret containment
- Date: 2026-07-15
- Trigger / Context: LLM vocabulary audit found a credential-shaped JSON ignored in JOB-PROJECT but still visible as untracked in fitcv-langgraph.
- What went wrong: Runtime credential vocabulary was unified, but local secret-file containment remained asymmetric across the adapter boundary.
- Correct behavior: Repos participating in one runtime contract must apply equivalent secret ignore controls without reading, copying, staging, or deleting local credential files.
- Prevention added or required: Keep filename-scoped ignore checks in cross-repo credential audits and record security-control drift in an evidence bundle.
- Related artifacts:
  - `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.gitignore`
  - `C:\Users\HOANG PHI LONG DANG\repos\fitcv-langgraph\.gitignore`
  - `docs/superpowers/plans/audit/20260715-1407-langgraph-secret-ignore-gap/`

## Completion checklists need executable evidence at every boundary

- Title: Passing core logic tests does not prove artifact or lifecycle contracts
- Date: 2026-07-16
- Trigger / Context: Inverse-optimization Phase 7 live run and master-spec reconciliation after implementation plan was marked completed.
- What went wrong: Ranking computed personalized fields correctly, but artifact/export adapters dropped them; activation accepted an evidence-head token without comparing it; completed plan named lifecycle proof commands that selected zero tests or had no dedicated test.
- Correct behavior: Verify each owned boundary separately: computation, adapter projection, persisted artifact, CLI typing, transactional CAS, replay, and runnable acceptance-test selection. A checked plan item must cite a command that executes the intended case.
- Prevention added or required: Keep row-level artifact/export regressions, evidence-head activation CAS test, typed CLI conflict test, and audit reconciliation against exact master acceptance criteria. Add current config/runtime CAS plus concurrency and injected-failure lifecycle tests before closure.
- Related artifacts:
  - `src/fitcv/pipeline.py`
  - `src/fitcv/pipeline_stages/common.py`
  - `src/fitcv_cp/sqlite_store.py`
  - `scripts/run_inverse_optimization.py`
  - `docs/superpowers/plans/audit/20260716-1413-phase7-live-run-master-spec/`
## Run-detail adapters must preserve canonical facts and full-page navigation

- Title: Fragment endpoints and snapshot allowlists are not source-of-truth boundaries
- Date: 2026-07-16
- Trigger / Context: Rating a job from the Enriched Jobs tab returned raw fragment HTML; Fit Context showed work mode as location and omitted language evidence.
- What went wrong: Decision-feedback redirect used a tab-fragment endpoint as a browser destination, while the run-scoped enrichment projection omitted canonical `actual_location` and `language_requirements`. The template then mislabeled `location_type` as Location.
- Correct behavior: Browser mutations return to the full run page and select the pane; run-scoped projections preserve canonical facts; UI reads canonical location/language first and uses existing factor evidence only as an honest legacy-run fallback.
- Prevention added or required: Keep regressions for full-page redirects, canonical snapshot preservation, field-label symmetry, fallback display, and vertical Fit Context layout.
- Related artifacts:
  - `src/fitcv/enrich.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/templates/run_detail_tab_enriched.html`
  - `docs/superpowers/plans/audit/20260716-run-detail-feedback-fit-context/`
