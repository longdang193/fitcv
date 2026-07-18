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

## Patch helper availability must be verified before repeated retries

- Title: Windows patch shim can exist but remain ACL-inaccessible
- Date: 2026-07-16
- Trigger / Context: LangGraph-removal closeout attempted the required `apply_patch` command after an earlier checkpoint had already reported `Access is denied` from the local WindowsApps shim.
- What went wrong: Tool presence was mistaken for tool usability, causing a repeated failed edit attempt; a later PowerShell replacement also exposed newline-escaping risk before guards stopped further changes.
- Correct behavior: After one confirmed ACL failure, stop retrying the shim. Use count-checked literal or normalized replacements, write UTF-8 without BOM, inspect the exact edited lines, and run `git diff --check` immediately.
- Prevention added or required: Carry patch-helper availability in execution checkpoints and use one guarded shell end-to-end when the helper is unavailable.
- Related artifacts:
  - `src/fitcv_cp/app.py`
  - `tests/test_fitcv_cp/test_app.py`
  - `docs/superpowers/plans/2026-07-16-21-16-fitcv-langgraph-removal-and-llm-runtime-ssot-closeout-plan.md`

## Empty pipeline results are valid terminal outcomes

- Title: Empty ranking must resolve zero residual instead of aborting
- Date: 2026-07-16
- Trigger / Context: FitCV Local full live run with one valid input that was rejected by policy before ranking.
- What went wrong: `resolve_run_preference_policy()` required at least one ranking row and raised `ValueError`, turning a valid zero-ranked run into user-visible failure.
- Correct behavior: Empty ranking resolves a typed zero-residual policy with explicit diagnostic, then pipeline completes with zero ranked jobs and truthful export outcome.
- Prevention added or required: Keep empty-ranking regression, full zero-result live scenario, and late-stage admissible scenario. Treat zero work at each stage as normal state unless contract explicitly forbids it.
- Related artifacts:
  - `src/fitcv/preference_policy.py`
  - `tests/test_preference_policy.py`
  - `docs/superpowers/plans/audit/20260716-2325-empty-ranking-preference-policy/`
## Packaged startup smoke does not prove packaged pipeline assets

- Title: Packaged startup smoke does not prove packaged pipeline assets
- Date: 2026-07-17
- Trigger / Context: FitCV Local bundle passed health, onboarding, second-instance, and shutdown smoke, but first real packaged pipeline run failed loading `enrich_extraction_v1.md`.
- What went wrong: PyInstaller omitted runtime prompt templates; smoke never asserted exact pipeline data assets or submitted a packaged run. Smoke also accepted stale runtime metadata, and onboarding duplicated a `120s` provider timeout while canonical control-plane config owned `300s`.
- Correct behavior: Release evidence separates source pipeline proof, packaged lifecycle smoke, and fresh-fingerprint packaged pipeline proof. Smoke binds runtime metadata to started PID and asserts exact required data assets. User-facing defaults resolve runtime config SSOT.
- Prevention added or required: Keep exact prompt bundle assertion, PID-bound runtime metadata polling, canonical timeout integration regression, and one fresh packaged pipeline scenario before distribution closure.
- Related artifacts:
  - `packaging/windows/fitcv-local.spec`
  - `scripts/smoke_fitcv_local.ps1`
  - `src/fitcv_cp/local_routes.py`
  - `tests/test_fitcv_local_packaging.py`
  - `tests/test_fitcv_cp/test_local_routes.py`
  - `docs/superpowers/plans/audit/20260717-0920-packaged-prompt-assets-timeout-ssot/`

## Transient tray icons should not reuse persistent GUID identity

- Title: Stable tray GUID can collide across frozen probe and product executables
- Date: 2026-07-17
- Trigger / Context: FitCV Local server stayed healthy, but its packaged Windows tray icon never appeared and `Shell_NotifyIconW(NIM_ADD)` returned false.
- What went wrong: Tray registration first omitted the created owner `hWnd`, then used one persistent GUID across isolated probe and full product executables. Fresh GUID and GUID-free registrations succeeded, proving shell identity state—not server lifecycle—was the remaining boundary.
- Correct behavior: Set `NOTIFYICONDATA.hWnd` before `NIM_ADD`; use process-owned `hWnd + uID` identity for a transient local app tray; verify with `Shell_NotifyIconGetRect` and command dispatch in the full frozen package.
- Prevention added or required: Keep owner-before-registration and no-persistent-GUID regressions. Do not treat source mode, isolated probes, or healthy HTTP startup as packaged tray proof.
- Related artifacts:
  - `src/fitcv_cp/windows_tray.py`
  - `tests/test_fitcv_cp/test_windows_tray.py`
  - `docs/superpowers/plans/audit/20260717-1334-fitcv-local-root-icon/`

## One-time setup editors need a post-setup navigation path

- Title: Existing controller editor became undiscoverable after onboarding
- Date: 2026-07-17
- Trigger / Context: A completed FitCV Local user could not find any UI for changing provider, API root, API key, or models.
- What went wrong: The canonical editor remained at `/local/onboarding`, but navigation only linked generic pipeline Settings and the page continued presenting itself as first-run Setup.
- Correct behavior: Reuse the same controller editor and write paths; expose a clear post-setup navigation link and completed-state labels instead of adding another settings backend.
- Prevention added or required: Keep a completed-user navigation regression whenever onboarding owns durable settings. Separate navigation labels for pipeline settings and LLM/API settings.
- Related artifacts:
  - `src/fitcv_cp/templates/base.html`
  - `src/fitcv_cp/templates/local_onboarding.html`
  - `tests/test_fitcv_cp/test_local_routes.py`
  - `docs/superpowers/plans/audit/20260717-1601-fitcv-local-llm-settings-discoverability/`

## Fallback file edits must use bounded anchors

- Title: Generic line removal corrupted unrelated Python blocks
- Date: 2026-07-17
- Trigger / Context: `apply_patch` was blocked by the packaged WindowsApps ACL during Prefect retirement, so a PowerShell fallback removed lines by global exact-value lookup.
- What went wrong: Generic lines such as `        )`, `        }`, and `            client=client,` matched earlier unrelated code before the intended route block.
- Correct behavior: When patch tooling is unavailable, edit only between unique start/end anchors or use context-checked indexed ranges; compile immediately after each fallback write.
- Prevention added or required: Keep exact-context guards, inspect targeted diff hunks, and run `compileall` before tests after any fallback edit of Python files.
- Related artifacts:
  - `src/fitcv_cp/app.py`
  - `tests/test_fitcv_cp/test_prefect_retirement.py`
## Canonical outcome truth and compatibility projections are separate responsibilities

- Title: Canonical outcome truth and compatibility projections are separate responsibilities
- Date: 2026-07-17
- Trigger / Context: Post-fix live run persisted `Review required:` correctly, but run-detail formatter independently rendered the same terminal event as `Run paused`; an attempted native/legacy status collapse also broke historical filters.
- What went wrong: Canonical JobOutcomeFact truth, minimal event references, user-facing formatting, and legacy filter compatibility were treated as one namespace. Fixing producer wording did not fix a separate UI projection, while collapsing legacy values changed adapter behavior rather than removing SSOT drift.
- Correct behavior: Canonical JobOutcomeFact semantics and event-stage identity have one owner; every current UI projection derives from canonical surfaces. Historical pipeline-status values remain a bounded compatibility namespace and are translated at adapter boundaries, not promoted to canonical truth or deleted blindly.
- Prevention added or required: Live-verify both persisted events and rendered UI, centralize event-stage identity, keep exact event-shape regressions, and test legacy filters separately from canonical outcome semantics.
- Related artifacts:
  - `src/fitcv/pipeline_contracts.py`
  - `src/fitcv/pipeline.py`
  - `src/fitcv_cp/reporter.py`
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/templates/run_detail_tab_enriched.html`
  - `docs/superpowers/plans/audit/20260717-2332-outcome-fact-live-run-contract-drift/`

## Unit-only semantic snapshots can disappear at persistence allowlists

- Title: Unit-level SSOT construction does not prove live persistence
- Date: 2026-07-17
- Trigger / Context: Semantic Snapshot SSOT live verification passed focused tests and completed a 13-job source-mode run, but exported artifacts and all `run_structured_jobs` payloads contained zero snapshots.
- What went wrong: `merge_scraped_and_enriched()` produced the new field in unit scope, while a downstream structured-job projection or persistence allowlist silently dropped it before stage artifacts and cache rows. Downstream stages therefore continued using flat compatibility fields and legacy fingerprints.
- Correct behavior: Any new runtime authority must have one end-to-end persistence assertion covering fresh output, cached reconstruction, stage artifact export, and database payload before calling migration complete.
- Prevention added or required: Keep a live or integration persistence test for `semantic_snapshot`, add source-boundary enforcement for direct semantic-map reads, and require all three mapping-change reuse scenarios before closing SSOT work.
- Related artifacts:
  - `src/fitcv/semantic_snapshot.py`
  - `src/fitcv/enrich.py`
  - `docs/superpowers/plans/audit/20260717-semantic-snapshot-ssot-live-verification/`

## Canonical fingerprints must include bounded alias identity for alias-sensitive consumers

- Title: Canonical value identity alone is insufficient for alias-sensitive stage reuse
- Date: 2026-07-18
- Trigger / Context: Semantic Snapshot SSOT preserved canonical values across a relevant alias addition, but CV gap analysis also consumed alias equivalence and initially reused its prior result.
- What went wrong: The CV-analysis input fingerprint represented canonical semantic values but omitted the bounded alias projection consumed by that stage. An alias-only LHS change therefore remained invisible even though stage behavior could change.
- Correct behavior: Exact stage identity includes every semantic input the stage consumes: canonical snapshot identity plus a bounded alias-equivalence projection for relevant terms. Unrelated mappings remain invisible; canonical-target changes and relevant alias changes invalidate only affected consumers.
- Prevention added or required: Keep symmetric skill/domain/role alias projection tests and three mapping laws: unrelated mapping preserves input, target change alters canonical input, and alias-only change alters alias-sensitive input.
- Related artifacts:
  - `src/fitcv/semantic_snapshot.py`
  - `src/fitcv/evidence.py`
  - `tests/test_semantic_snapshot.py`
  - `tests/test_evidence.py`
  - `docs/superpowers/plans/audit/20260717-semantic-snapshot-ssot-live-verification/`
