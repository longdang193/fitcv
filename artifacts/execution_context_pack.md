# Execution Context Pack

## 1) Objective

- **Workstream / Plan:** `docs/superpowers/plans/2026-05-23-22-56-fitcv-pipeline-contract-refactor-plan.md`
- **Goal:** Execute A1–A5 refactor in `src/fitcv/pipeline.py` with SSOT + symmetry + invariance; proceed into gated A5 module split.
- **Bounded Scope (in-scope only):** `src/fitcv/pipeline.py`, `src/fitcv/pipeline_stage_context.py`, `src/fitcv/pipeline_contracts.py`, `src/fitcv/pipeline_stages/*`, `src/fitcv_cp/*`, and focused tests.
- **Out of Scope (explicit):** Merge/PR/closeout orchestration; fixing unrelated baseline failures in `tests/test_pipeline.py`.

## 2) Canonical Inputs (Source of Truth)

- **Primary plan:** `docs/superpowers/plans/2026-05-23-22-56-fitcv-pipeline-contract-refactor-plan.md`
- **Specs / maps / thread docs:**
  - `docs/superpowers/specs/2026-05-23-22-45-fitcv-pipeline-refactor-ssot-spec.md`
  - `docs/intent/workstreams/threads/workstream-pipeline-efficiency-and-reuse/03-efficiency-reuse-operator-diagnostics.md`
- **Governance / workflow rules used:**
  - `docs/operating_system/templates/execution-context-pack-template.md`
  - `docs/operating_system/governance/execution-context-pack-governance.md`
  - `docs/operating_system/prompt_templates/implementation-next-action-gate-prompt.md`

## 3) Current Task State

- **Completed:**
  - Task 1: impact + consumer inventory (GitNexus impact + `rg`)
  - Task 2 (A1): SSOT reason-code Enum (`ReviewRequiredReasonCode`) + pipeline/CP mapping updates + focused tests
  - Task 3 (A2): removed duplicate `_build_stage_dispatch_map`
  - Task 4 (A3): unified Top-N config reads via `_pipeline_int`; removed stale `embed_scope` promise
  - Task 5 (A4): checkpoint payload now includes `schema_version`; `candidate_query_debug` serialized as dict; restore supports wrapped `checkpoint_payload`; `PipelineState.payload_keys()` now includes `cv_results`
- **In Progress:**
  - none
- **Deferred / Dropped:**
  - Task 6 (A5) stage-body moves dropped (stop at helper consolidation; keep `run_pipeline` stable).
- **Known divergence from plan (if any):**
  - `tests/test_pipeline.py` baseline remains red; rely on focused tests + `gitnexus detect-changes` scope checks.
  - Plan checklist reconciled: all unchecked items cleared; completed/dropped items marked `- [x]` in plan.

## 4) Files Changed This Session

- `src/fitcv/pipeline_contracts.py` — SSOT review-required reason codes enum
- `src/fitcv/pipeline.py` — reason-code normalization returns Enum; persisted payload stores `.value`; `_pipeline_int`; checkpoint payload schema_version; embed_scope docstring update; removed duplicate stage helper
- `src/fitcv/pipeline_stage_context.py` — schema version constant; wrapped-checkpoint restore; payload keys updated (incl `cv_results`)
- `src/fitcv_cp/app.py` — review reason mapping uses SSOT enum
- `src/fitcv_cp/worker_job.py` — review reason mapping uses SSOT enum
- `src/fitcv/pipeline_stages/__init__.py` — A5 scaffold
- `src/fitcv/pipeline_stages/types.py` — A5 interface skeleton (not wired)
- `src/fitcv/pipeline_stages/common.py` — extracted helper `pipeline_int` (first A5 move; behavior preserved)
- `src/fitcv/pipeline_stages/common.py` — extracted helpers `extract_job_url` and `extract_job_title`; pipeline call sites updated
- `src/fitcv/pipeline_stages/common.py` — extracted helper `normalize_shortlist_row`; pipeline call sites updated
- `src/fitcv/pipeline_stages/common.py` — extracted helper `json_safe_value`; pipeline checkpoint payload builder uses it
- `src/fitcv/pipeline_stages/common.py` — extracted helper `shortlist_outcome_for_row`; pipeline call sites updated
- `src/fitcv/pipeline_stages/common.py` — extracted helper `unique_job_urls`; pipeline call sites updated
- `src/fitcv/pipeline_stages/common.py` — extracted helper `compute_raw_shortlist_anomaly_urls`; pipeline call sites updated
- `src/fitcv/pipeline_stages/common.py` — extracted helper `job_sample`; pipeline keeps thin wrapper `_job_sample` to bind `_EXPORT_ENRICHED_JOB_FIELDS`
- `src/fitcv/pipeline_stages/common.py` — extracted helper `candidate_profile_summary`; pipeline keeps thin wrapper `_candidate_profile_summary` for existing builder surface
- `src/fitcv/pipeline_stages/common.py` — extracted helper `shortlist_row_sample`; pipeline keeps thin wrapper `_shortlist_row_sample` for existing builder surface
- `src/fitcv/pipeline_stages/common.py` — extracted helper `ranking_row_sample`; pipeline keeps thin wrapper `_ranking_row_sample` for existing builder surface
- `src/fitcv/pipeline_stages/common.py` — extracted helper `analysis_record_output_sample`; pipeline keeps thin wrapper `_analysis_record_output_sample` for existing builder surface
- `src/fitcv/pipeline_stages/common.py` — extracted helper `analysis_record_changed_sample`; pipeline keeps thin wrapper `_analysis_record_changed_sample` for existing builder surface
- `src/fitcv/pipeline_stages/common.py` — extracted helper `debug_record_output_sample`; pipeline keeps thin wrapper `_debug_record_output_sample` for existing builder surface
- `src/fitcv/pipeline_stages/common.py` — extracted helper `debug_record_changed_sample`; pipeline keeps thin wrapper `_debug_record_changed_sample` for existing builder surface
- `tests/test_cv_generation_reason_mapping.py` — updated for Enum return
- `tests/test_pipeline.py` — updated mapping tests for Enum return
- `tests/test_pipeline_config_access.py` — new tests for `_pipeline_int`
- `tests/test_pipeline_checkpoint_contract.py` — new tests for checkpoint schema version + wrapped restore
- `artifacts/execution_context_pack.md` — mirror pointer

## 5) Verification State

- **Last commands run:**
  - `npx gitnexus analyze -f --index-only` (PASS, refreshed 2026-05-24)
  - `npx gitnexus analyze -f --index-only` (PASS)
  - `python scripts/hooks/run_validator.py --fast` (PASS)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline.py -k reason_code -q` (PASS)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after A5 extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium; Admin_continue_run still flagged; after helper extraction Build_ranking_features also flagged)
  - `npx gitnexus analyze -f --index-only` (PASS, refreshed)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after normalize_shortlist_row extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after normalize_shortlist_row extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after shortlist_outcome_for_row extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after shortlist_outcome_for_row extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS, after shortlist_outcome_for_row extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after shortlist_outcome_for_row extraction; flows still include `Admin_continue_run` + `Build_ranking_features`)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after unique_job_urls extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after unique_job_urls extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after unique_job_urls extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after compute_raw_shortlist_anomaly_urls extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after compute_raw_shortlist_anomaly_urls extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after compute_raw_shortlist_anomaly_urls extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after job_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after job_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after job_sample extraction; now only `Admin_continue_run`)
  - `npx gitnexus analyze -f --index-only` (PASS, refreshed 2026-05-24)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after candidate_profile_summary extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after candidate_profile_summary extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS, after candidate_profile_summary extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after candidate_profile_summary extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after shortlist_row_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after shortlist_row_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS, after shortlist_row_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after shortlist_row_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after ranking_row_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after ranking_row_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after ranking_row_sample extraction; only `Admin_continue_run` persists)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after analysis_record_output_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after analysis_record_output_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS, after analysis_record_output_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after analysis_record_output_sample extraction; only `Admin_continue_run` persists)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after analysis_record_changed_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after analysis_record_changed_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS, after analysis_record_changed_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after analysis_record_changed_sample extraction; only `Admin_continue_run` persists)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after debug_record_output_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after debug_record_output_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS, after debug_record_output_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after debug_record_output_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_config_access.py -q` (PASS, after debug_record_changed_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_pipeline_checkpoint_contract.py -q` (PASS, after debug_record_changed_sample extraction)
  - `.venv\\Scripts\\python.exe -m pytest tests/test_cv_generation_reason_mapping.py -q` (PASS, after debug_record_changed_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium, after debug_record_changed_sample extraction)
  - `npx gitnexus detect-changes -r <worktree-path> -s all` (Risk: medium; affected flow `Admin_continue_run` via `PipelineState.payload_keys`/`from_checkpoint_payload`)
- **Failing checks (if any):**
  - `tests/test_pipeline.py` full suite failing at baseline (pre-existing)
  - `python scripts/hooks/run_validator.py --fast` (PASS)
  - `python scripts/validate_planning_lifecycle.py --strict` (PASS)
  - `python scripts/validate_checkpoint_packs.py` (PASS)
  - `python scripts/validate_repo_contracts.py --fast` (PASS)

## 6) Open Blockers / Risks

- `gitnexus detect-changes` flags `Admin_continue_run` flow impact (expected from checkpoint contract changes). Must keep A5 changes isolated from CP continue behavior unless explicitly planned/tested.

## 7) Next Exact Action

- **Action type:** close now
- **Target:** `docs/superpowers/plans/2026-05-23-22-56-fitcv-pipeline-contract-refactor-plan.md`
- **Exact command or edit intent:** no further code edits in lane; open PR from `codex/fitcv-pipeline-contract-refactor`.
- **Why this is next:** Key Deliverables satisfied (A1/A3/A4). A5 stage-body moves dropped with rationale recorded. Closeout validators + focused tests have evidence.

## 8) Resume Prompt (Copy/Paste)

```text
Read docs/superpowers/execution_context_packs/fitcv-pipeline-contract-refactor/latest.md first. Execute Next Exact Action: extract one helper-only unit into src/fitcv/pipeline_stages/ and update imports without behavior change. Then rerun focused pytest commands and npx gitnexus detect-changes -r <worktree-path> -s all.
```

## 9) Optional Deep Context (Consult Only)

- **conversation_id:** none
- **overview_log:** none

## Source-Truth Rule

If context pack, source files, and raw log disagree:
1. source files and current tests/checks win
2. then context pack
3. raw log is fallback evidence only
