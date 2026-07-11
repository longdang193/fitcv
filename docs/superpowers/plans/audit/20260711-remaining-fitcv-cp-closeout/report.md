# Audit Report With Evidence

## Metadata

- Audit ID: `20260711-remaining-fitcv-cp-closeout`
- Status: `resolved`
- Severity: `medium`
- Owner: `codex`
- Created At: `2026-07-11T00:00:00Z`
- Updated At: `2026-07-11T00:00:00Z`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-11-14-56-fitcv-cp-template-correctness-patch-plan.md`

## Scope

- Environment: `Windows / PowerShell / Python 3.13.5`
- Commit/Branch: `main @ 29c0da86813d162ae4dec4e5af8aafdc399bdb9a`
- Affected Surface: `src/fitcv_cp/app.py`, `tests/test_fitcv_cp/test_app.py`

## Findings

### Finding `1`: `Enriched tab default outcome filter hid unknown-status rows`

- Classification: `regression`
- Impact: `Enriched tab rendered empty-state and broke pagination in cases where rows existed but lacked explicit pipeline-outcome truth.`
- Expected Behavior: `Default selected outcomes should not hide rows whose pipeline outcome is still unknown.`
- Actual Behavior: `Rows without explicit outcome status were filtered out because empty status failed the default selected-outcomes check.`

### Finding `2`: `Promotion tests drifted from checkbox-only contract`

- Classification: `spec-mismatch`
- Impact: `Closeout verification stayed red even though server/template contract already moved to checkbox-only promotion submission and rendered grouped review rows without raw blocked proposal ids.`
- Expected Behavior: `Tests should submit promote_proposal_id and assert current rendered grouping contract.`
- Actual Behavior: `Tests still posted selected_ids_csv and expected hidden blocked proposal ids in response HTML.`

## Evidence

- Logs/Text: `evidence/broader_slice_pytest.log`
- Logs/Text: `evidence/validator_fast.log`
- Logs/Text: `repro/repro_steps.txt`

Each evidence item should include:

- `broader_slice_pytest.log`
  - capture timestamp: `2026-07-11`
  - producing command/tool: `python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or promote or archived or enriched"`
- `validator_fast.log`
  - capture timestamp: `2026-07-11`
  - producing command/tool: `python scripts/hooks/run_validator.py --fast`
- `repro_steps.txt`
  - capture timestamp: `2026-07-11`
  - producing command/tool: `Set-Content`

## Reproduction

- Preconditions:
  - `Windows workspace with JOB-PROJECT repo`
  - `Python 3.13 environment`
- Steps:
  1. `Run focused control-plane pytest slice.`
  2. `Observe enriched tab and promotion verification failures.`
  3. `Patch truth owner: keep unknown-status rows visible under default outcome selection; update stale tests to current contract.`
  4. `Rerun focused slice and validator.`
- Commands:

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or promote or archived or enriched"
python scripts/hooks/run_validator.py --fast
```

- Determinism notes: `Focused pytest slice reproduced consistently before patch and passes consistently after patch. Validator failure remains deterministic and unrelated.`

## Root Cause And Boundary

- Failure boundary: `FitCV control-plane enriched-tab filter contract and stale regression tests`
- Root cause summary: `Enriched-tab filtering treated empty pipeline-outcome status as failing the default selected-outcome set. Separate regression tests still asserted pre-refactor promotion request and HTML shapes.`

## Fix And Verification

- Fix summary: `Allow unknown-status rows through default outcome filter; update stale promotion and enriched regression tests to current checkbox-only and default-outcome contracts.`
- Verification commands:

```powershell
python -m pytest tests/test_fitcv_cp/test_app.py::test_admin_run_synonym_promote_commit_updates_global_policy_and_redirects -q
python -m pytest tests/test_fitcv_cp/test_app.py::test_admin_run_synonym_promote_review_groups_ready_already_global_and_blocked -q
python -m pytest tests/test_fitcv_cp/test_app.py::test_run_detail_enriched_tab_paginates_server_side -q
python -m pytest tests/test_fitcv_cp/test_app.py::test_run_detail_enriched_tab_uses_stage_artifacts_sample_for_running_run -q
python -m pytest tests/test_fitcv_cp/test_app.py::test_run_detail_enriched_uses_rule_filter_dropped_sample_for_rejected_rows tests/test_fitcv_cp/test_app.py::test_run_detail_enriched_pagination_fragment_url_matches_href -q
python -m pytest tests/test_fitcv_cp/test_app.py -k "settings or promote or archived or enriched"
python scripts/hooks/run_validator.py --fast
```

- Verification evidence links:
  - `evidence/broader_slice_pytest.log` shows `157 passed, 364 deselected`.
  - `evidence/validator_fast.log` shows only unrelated pre-existing Indeed adapter doc metadata failures.

## Risk And Disposition

- Residual risk: `Low. Targeted control-plane behavior is covered by focused route tests and broader slice. Fast validator remains blocked by unrelated doc metadata debt.`
- Disposition decision: `resolved`
- Follow-ups: `Fix or quarantine docs/superpowers/specs/2026-06-26-00-49-indeed-job-input-adapter-spec.md and docs/superpowers/plans/2026-06-26-00-50-indeed-job-input-adapter-plan.md in separate lane.`

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
