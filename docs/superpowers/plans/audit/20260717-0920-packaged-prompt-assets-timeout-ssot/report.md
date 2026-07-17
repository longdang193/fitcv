# Audit Report With Evidence

## Metadata

- Audit ID: `20260717-0920-packaged-prompt-assets-timeout-ssot`
- Status: `resolved`
- Severity: `high`
- Owner: `Codex`
- Created At: `2026-07-17T09:31:16+02:00`
- Updated At: `2026-07-17T09:31:16+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-16-22-40-fitcv-local-distribution-and-onboarding-plan.md`

## Scope

- Environment: `Windows 10 19045, PowerShell 7, Python 3.13.5, PyInstaller 6.21.0, FitCV Local onedir bundle`
- Commit/Branch: `d210f5486988f702646950b1093fe26d01eb5f36 on codex/phase-6-inverse-optimization with uncommitted fixes`
- Affected Surface: `Windows bundle data manifest, packaged smoke lifecycle, local onboarding provider timeout, packaged inline enrichment pipeline`

## Findings

### Finding `F1`: packaged prompt template absent

- Classification: `regression`
- Impact: packaged full pipeline fails during enrichment with `FileNotFoundError`; startup and onboarding still appear healthy.
- Expected Behavior: all runtime prompt templates required by packaged pipeline exist below `_internal/fitcv/prompts/templates`.
- Actual Behavior: PyInstaller data manifest omitted `src/fitcv/prompts/templates`; smoke checked generic startup only.

### Finding `F2`: smoke accepts stale runtime metadata

- Classification: `regression`
- Impact: smoke may read a dead previous process URL and fail with connection refused before new process rewrites runtime metadata.
- Expected Behavior: smoke accepts runtime metadata only when metadata PID matches process started by smoke.
- Actual Behavior: first existing `.fitcv-local-runtime.json` was accepted regardless of PID.

### Finding `F3`: local onboarding timeout drifts from runtime SSOT

- Classification: `spec-mismatch`
- Impact: representative enrichment calls can exceed local hardcoded `120s` timeout although canonical control-plane provider timeout is `300s`.
- Expected Behavior: onboarding default and missing-value fallback resolve timeout from `config/runtime/control_plane.yaml` through shared config loader.
- Actual Behavior: template and route fallbacks duplicated `120`; minimal provider test passed in `2.955s`, while full enrich request timed out after `120s`.

## Evidence

- Initial packaged error: `evidence/results/initial-missing-prompt.txt`
- Package asset and hashes: `evidence/results/package-summary.json`
- Stale-metadata-safe packaged smoke: `evidence/results/package-smoke.txt`
- Packaged timeout run: `evidence/results/packaged-run-timeout-120.json`
- Timeout event sequence: `evidence/results/events-timeout-120.json`
- Minimal provider test: `evidence/results/provider-minimal-test.json`
- Timeout SSOT comparison: `evidence/results/ssot-timeout-summary.json`
- Final fresh packaged run: `evidence/results/packaged-run-final.json`
- Final event sequence: `evidence/results/events-final.json`
- SQLite reconciliation: `evidence/results/sqlite-reconciliation.json`
- Packaged admissible downstream run: `evidence/results/packaged-run-admissible.json`
- Admissible downstream events: `evidence/results/events-admissible.json`
- Admissible SQLite reconciliation: `evidence/results/sqlite-reconciliation-admissible.json`
- Focused regressions: `evidence/results/focused-tests.txt`
- Canonical config tests: `evidence/results/config-tests.txt`
- Ruff: `evidence/results/ruff.txt`
- Repo contracts: `evidence/results/repo-contracts-fast.txt`
- Targeted mypy baseline: `evidence/results/mypy-targeted.txt`

## Reproduction

- Preconditions and commands: `repro/repro_steps.md`.
- Determinism notes: one row derived from first public `data/sample_jobs.json` record; final run adds unique URL/description marker so enrichment cannot reuse prior structured-job cache.

## Root Cause And Boundary

- Failure boundary: packaged enrichment runtime loads prompt file, then calls configured OpenAI-compatible provider through inline local executor.
- Root cause summary: package manifest excluded prompt templates; smoke verified only startup surfaces; onboarding duplicated `120s` instead of consuming canonical `300s` provider timeout. These independent gaps allowed startup smoke to pass while packaged full pipeline failed.

## Fix And Verification

- Fix summary: bundle `src/fitcv/prompts/templates`; assert exact prompt path in package tests and smoke; require runtime metadata PID match; resolve onboarding timeout from shared model-routing config; render same value in web form.
- Verification commands:

```powershell
pytest -q tests/test_fitcv_local_packaging.py tests/test_fitcv_cp/test_local_routes.py
pytest -q tests/test_config.py -k model_routing_part
uv run ruff check src/fitcv_cp/local_routes.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_local_packaging.py
.\scripts\build_fitcv_local.ps1 -Version 0.1.0 -BuildId packaged-prompt-timeout-fix
.\scripts\smoke_fitcv_local.ps1 -BundlePath .\dist\fitcv-local
uv run python scripts/validate_repo_contracts.py --fast
```

- Final packaged proof: build `packaged-prompt-timeout-fix`, executable `dist/fitcv-local/fitcv-local.exe`, fresh run `7505a7e0-42e6-4334-aa43-3551ec4cdcc1`, status `succeeded`.
- Packaged downstream proof: run `e8a1f515-56f2-484a-8f12-4522e31acd37` completed `1 input -> 1 passed -> 1 ranked`; CV analysis returned ready and CV generation completed with `review_required`, no runtime error.
- SQLite proof: `integrity_check=ok`, zero foreign-key violations, one local run row, one structured-job row, one filter-result row, and 23 run events.
- Downstream SQLite proof: `integrity_check=ok`, zero foreign-key violations, one ranked run, 41 events, run-scoped CV debug and results export present; accepted CV count remains `0` because item requires operator review.

## Risk And Disposition

- Residual risk: clean Windows VM, code signing, and representative slow-provider coverage remain release gates. Targeted mypy remains non-clean because existing project/dependency stubs and unrelated typing debt produce 48 errors.
- Disposition decision: `resolved`.
- Follow-ups: keep exact prompt asset assertion, PID-bound smoke metadata, canonical timeout regression, fresh-fingerprint packaged pipeline scenario, and add explicit operator review/acceptance automation if release scope requires accepted-CV proof.

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