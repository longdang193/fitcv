# Audit Report With Evidence

## Metadata

- Audit ID: `20260626-1907-fitcv-pipeline-identity-filter-truth`
- Status: `resolved`
- Severity: `high`
- Owner: `Codex`
- Created At: `2026-06-26T19:07:35.2162003+02:00`
- Updated At: `2026-06-26T19:07:35.2162003+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-06-26-16-45-fitcv-pipeline-identity-and-filter-truth-plan.md`

## Scope

- Environment: `Windows + PowerShell + local pytest + local sqlite control-plane store`
- Commit/Branch: `7e0278899a173eac28495b44973671307d5344a8` on `main`
- Affected Surface: `src/fitcv/pipeline.py`, `src/fitcv/pipeline_stages/common.py`, `src/fitcv/rule_filter.py`, `src/fitcv_cp/app.py`, `src/fitcv_cp/bq_store.py`

## Findings

### Finding `F1`: URL drift split one logical job across pipeline artifacts

- Classification: `data-quality`
- Impact: Enriched Jobs rows could render blank `Filter` and `Pipeline Outcome` even when downstream ranking/CV truth existed.
- Expected Behavior: One logical job should keep stable per-row truth across raw input, enrichment, results export, and control-plane rendering.
- Actual Behavior: Source URLs (for example Indeed) and destination-site URLs diverged, while joins still used raw `job_url` string equality, producing `unknown_pipeline_state` and empty UI cells.

### Finding `F2`: sqlite mode dropped canonical rule-filter truth

- Classification: `data-quality`
- Impact: Local/running sqlite-backed control-plane could not read full per-job filter truth, so UI fell back to samples or guessed pass states.
- Expected Behavior: `list_filter_results_for_run()` should expose full run-scoped rule-filter rows in sqlite and BigQuery.
- Actual Behavior: sqlite mode returned no persisted filter rows because `store_filter_results()` returned early and `list_filter_results_for_run()` returned `[]`.

## Evidence

For both findings:

- Logs/Text: `evidence/results/verification.txt`

Evidence file includes:

- capture timestamp
- exact pytest commands
- pass/fail outcomes
- local runtime-style inspection attempt result

## Reproduction

- Preconditions:
  - repo checkout at current workspace state
  - `PYTHONPATH=src`
  - pytest available
- Steps:
  1. Run regression tests that encode URL drift and sqlite parity failures.
  2. Observe `unknown_pipeline_state`, synthetic `passed=True`, or empty local filter rows before fix.
  3. Apply bounded patch to pipeline identity, sqlite filter persistence, and control-plane lookup logic.
  4. Re-run same tests and parity slices.
- Commands:

```powershell
python -m pytest tests/test_pipeline.py::test_build_export_results_uses_raw_job_fingerprint_when_urls_drift -q
python -m pytest tests/test_fitcv_cp/test_app.py::test_build_enriched_tab_context_does_not_guess_passed_for_unknown_rows -q
python -m pytest tests/test_fitcv_cp/test_app.py::test_build_enriched_tab_context_matches_truth_by_raw_job_fingerprint_when_urls_drift -q
python -m pytest tests/test_fitcv_cp/test_storage_backend_parity.py::test_filter_results_contract_parity_sqlite_vs_bigquery -q
```

- Determinism notes: synthetic fixtures pin job URLs, fingerprints, and expected pipeline states; sqlite parity test creates isolated temp DB fixture.

## Root Cause And Boundary

- Failure boundary: `pipeline export identity contract` + `rule-filter persistence backend split` + `control-plane enriched-tab join contract`
- Root cause summary: per-row truth used mutable `job_url` as primary identity, sqlite skipped canonical filter-result persistence, and control-plane guessed pass state from export rows when filter truth was absent.

## Fix And Verification

- Fix summary: add shared fingerprint/url lookup keys in pipeline + app, export `raw_job_fingerprint` and `source_job_url`, persist/read sqlite `rule_filter_results`, and remove synthetic pass fallback for missing filter truth.
- Verification commands:

```powershell
python -m pytest tests/test_pipeline.py -k "build_export_results_uses_raw_job_fingerprint_when_urls_drift or export_results or pipeline_status" -q
python -m pytest tests/test_fitcv_cp/test_app.py -k "build_enriched_tab_context or enriched and (pipeline or filter or fallback or unknown)" -q
python -m pytest tests/test_fitcv_cp/test_bq_store.py -k "filter_results" -q
python -m pytest tests/test_fitcv_cp/test_storage_backend_parity.py -q
```

- Verification evidence links:
  - `evidence/results/verification.txt`

## Risk And Disposition

- Residual risk: BigQuery schema may still lack new optional identity columns; current patch preserves backward-compatible reads and local sqlite parity, but cloud schema alignment still needs runtime migration validation before claiming BigQuery live parity.
- Disposition decision: `resolved` for local code path and verified test scope
- Follow-ups:
  - run live BigQuery-backed verification after schema alignment or deployment path confirmation
  - rebuild/restart any long-running container that does not hot-reload source files

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented (or explicit bypass)
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
