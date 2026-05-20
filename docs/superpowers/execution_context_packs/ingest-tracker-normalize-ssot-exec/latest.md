# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `workstream-pipeline-efficiency-and-reuse.efficiency-reuse-exact-match-contract` / `docs/superpowers/plans/2026-05-20-20-54-fitcv-ingest-tracker-normalize-ssot-refactor-plan.md`
- **Goal:** Execute RF-001..RF-005 with SSOT/symmetry/invariance across `ingest`, `tracker`, `normalize` while preserving runtime behavior.
- **Bounded Scope (in-scope only):** `src/fitcv/ingest.py`, `src/fitcv/tracker.py`, `src/fitcv/normalize.py`, `src/fitcv/persistence.py`, scoped tests.
- **Out of Scope (explicit):** merge/PR closeout, unrelated module refactors outside plan targets.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-20-20-54-fitcv-ingest-tracker-normalize-ssot-refactor-plan.md`
- **Specs / maps / thread docs:** `docs/superpowers/specs/2026-05-20-20-54-fitcv-ingest-tracker-normalize-ssot-refactor-spec.md`; `docs/intent/workstreams/threads/workstream-pipeline-efficiency-and-reuse/01-efficiency-reuse-exact-match-contract.md`
- **Governance / workflow rules used:** `docs/operating_system/governance/execution-context-pack-governance.md`; `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:** Task 1; Task 2; Task 3; Task 4; Task 5; Task 6; Task 7.
- **In Progress:** closeout eligibility decision.
- **Deferred / Dropped:** none.
- **Known divergence from plan (if any):** none.

## 4) Files Changed This Session

- `src/fitcv/persistence.py` — unified credential fallback (`service_account_key` optional string handling).
- `src/fitcv/ingest.py` — shared persistence helper + shared scraper contracts.
- `src/fitcv/tracker.py` — shared persistence helper, shared status contract, fallback matcher hardening.
- `src/fitcv/contracts.py` — added shared scraper/status constants.
- `src/fitcv/normalize.py` — restored `_job_url` helper and added shared `_near_duplicate_key` used across dedupe paths.
- `tests/test_normalize.py` — added dedupe symmetry assertion test between standalone and exclusion-aware flow.
- `src/fitcv/normalize.py` — Task 5 Step 1 policy: reject mixed-currency or mixed-period salary strings (`None` fallback).
- `tests/test_normalize.py` — added mixed-currency and mixed-period salary regression tests.
- `src/fitcv/normalize.py` — expanded `parse_applications_count` localized/variant phrase support with explicit unknown-phrase `None` fallback.
- `tests/test_normalize.py` — added localized applicant-count and localized "among first" regression tests.
- `tests/test_tracker.py` — added non-schema BigQuery error negative-path test to prove no legacy fallback retry.
- `docs/superpowers/plans/2026-05-20-20-54-fitcv-ingest-tracker-normalize-ssot-refactor-plan.md` — corrected execution-state checkboxes.
- `docs/superpowers/execution_context_packs/ingest-tracker-normalize-ssot-exec/latest.md` — canonical context state.

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze --index-only`
  - Task 1 impact checks (`snake_case_keys`, `load_to_bigquery`, `normalize_batch_with_exclusions`, `parse_salary`, `parse_applications_count`, `store_cv_version`, `store_application_status`, `build_bigquery_client`, `get_local_sqlite_path`, `_get_valid_statuses`, `_is_missing_structured_cv_column_error`)
  - `uv run pytest tests/test_ingest.py tests/test_tracker.py tests/test_normalize.py`
  - `uv run pytest tests/test_ingest.py -k "bigquery_mode or snake_case_keys or validate_linkedin_schema"`
  - `uv run pytest tests/test_tracker.py -k "store_cv_version or update_application_status"`
  - `uv run pytest tests/test_tracker.py -k "legacy_schema or structured_columns"`
  - `npx gitnexus impact deduplicate_jobs -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\ingest-tracker-normalize-ssot-exec"`
  - `npx gitnexus impact normalize_batch_with_exclusions -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\ingest-tracker-normalize-ssot-exec"`
  - `uv run pytest tests/test_normalize.py`
  - `uv run pytest tests/test_pipeline.py -k dedupe`
  - `npx gitnexus impact parse_salary -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\ingest-tracker-normalize-ssot-exec"`
  - `npx gitnexus impact parse_applications_count -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\ingest-tracker-normalize-ssot-exec"`
  - `uv run pytest tests/test_normalize.py -k "salary or applications_count"`
  - `uv run pytest tests/test_rule_filter.py -k applications_count`
  - `uv run pytest tests/test_tracker.py -k "legacy_schema or structured_columns"`
  - `uv run pytest tests/test_ingest.py tests/test_tracker.py tests/test_normalize.py`
  - `uv run mypy src/fitcv/ingest.py src/fitcv/tracker.py src/fitcv/normalize.py src/fitcv/contracts.py src/fitcv/persistence.py --show-error-codes`
  - `npx gitnexus detect_changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\ingest-tracker-normalize-ssot-exec"`
  - `python scripts/validate_planning_lifecycle.py --strict`
  - `python scripts/validate_checkpoint_packs.py`
  - `python scripts/validate_template_required_sections.py`
  - `npx gitnexus detect_changes -r "C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\ingest-tracker-normalize-ssot-exec"`
  - `uv run mypy src/fitcv/ingest.py src/fitcv/tracker.py src/fitcv/normalize.py src/fitcv/contracts.py src/fitcv/persistence.py --show-error-codes`
- **Result summary:** scoped tests pass (`61 passed, 1 skipped`); GitNexus detects expected changed surfaces; mypy non-zero due pre-existing repository typing/stub issues and a `google.api_core.gapic_v1` environment assertion unrelated to this refactor lane.
- **Failing checks (if any):** mypy non-zero.
- **Gaps still unverified:** none for task execution. Remaining decision is closeout tolerance for known mypy baseline/environment issues.

## 6) Open Blockers / Risks

- `mypy` baseline issues outside this lane make strict green typing unavailable without broader cleanup.
- Local `mypy` run hits `google.api_core.gapic_v1` assertion in environment; not introduced by edited files.

## 7) Next Exact Action

- **Action type:** closeout gate decision
- **Target:** plan/workstream closure path
- **Exact command or edit intent:** rerun closure gate now that plan/context reconciliation and lifecycle validators passed; if baseline-policy accepts known mypy non-lane issues, proceed to merge/push closeout steps.
- **Why this is next:** all planned implementation and scoped verification steps are complete.

## 10) Migration / Deprecation Notes

- RF-004 salary parser now rejects mixed currency/period strings with deterministic `None` fallback (previous behavior could silently mix values).
- RF-004 applicant-count parser now accepts additional localized phrases and keeps explicit `None` fallback for unrecognized variants.
- RF-005 fallback write path remains backward compatible: legacy retry occurs only for qualifying structured-column-missing errors.

## 8) Resume Prompt (Copy/Paste)

```text
Read this execution context pack first. Verify its state against listed source files. Then execute the Next Exact Action immediately. Do not re-plan unless blocker is found.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** n/a
- **overview_log:** n/a
- **consult_if:** only if source files and this pack diverge.
- **notes_from_log (optional, concise):** n/a

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
