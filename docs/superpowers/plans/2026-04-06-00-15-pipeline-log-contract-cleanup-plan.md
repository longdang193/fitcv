# Pipeline Log Contract Cleanup Plan

Status: completed

## Tasks

1. Close unresolved-placeholder acceptance in `cv_generation` validation.
Status: completed
Notes:
- Extend the unresolved-placeholder detector in `validator.py` to cover the accepted placeholder variants observed in real outputs, including `[Candidate Name]`.
- Preserve the current grounding/validation flow shape so this remains a narrow correctness fix rather than a broader rewrite.
- Add focused tests proving placeholder CVs are rejected.

2. Canonicalize `settings-used.json` for operator-facing export.
Status: completed
Notes:
- Keep canonical nested settings as the primary `effective_settings` truth.
- Remove or relocate compatibility-era flat keys from the primary export surface.
- If compatibility details remain useful, expose them in an explicitly labeled block such as `compatibility_projection`.
- Verify active run-detail/export consumers do not depend on flat-key duplication.

3. Add active structured prompt provenance to `cv_generation` artifacts.
Status: completed
Notes:
- Replace `cv_prompt_version` as the sole provenance field with active structured prompt metadata.
- Add at minimum:
  - `cv_prompt_id`
  - `cv_prompt_template_path`
  - `cv_generation_model`
- Keep `cv_prompt_version` only if it remains useful as a secondary derived breadcrumb during the migration window.

4. Add AI-scoring prompt/model provenance to `ranking` artifacts.
Status: completed
Notes:
- Extend ranking-stage `decision_summary` and any relevant run-level export snapshots to include:
  - `ranking_prompt_id`
  - `ranking_prompt_template_path`
  - `ai_score_model`
- Keep existing ranking calibration, thresholds, and reuse metrics intact.
- Ensure ranking provenance is stage-local so operators do not have to open `settings-used.json` to debug AI-score drift.

5. Make `cv-debug.json` coverage accounting explicit.
Status: completed
Notes:
- Add counts for:
  - `attempted_generation_jobs_total`
  - `non_attempted_ranked_jobs_total`
  - `omission_reason_counts`
- Keep `ranked_jobs_total`, `debug_records_captured`, and the existing debug records.
- Reframe `snapshot_complete` semantics so a successful run with skipped fit-gate jobs is understandable without cross-referencing other artifacts.

6. Tighten aggregate export responsibility between `results.json` and `stage-artifacts.json`.
Status: completed
Notes:
- Keep `results.json` as the primary run-summary and per-job outcome export.
- Keep `stage-artifacts.json` as the bundle export for stage-level inspection.
- Remove obviously duplicated deep-detail blocks when they are simply mirroring stage-local artifacts without adding new run-level value.
- Preserve bounded operator workflows and avoid breaking run-detail export downloads.

7. Sync docs and feature contracts.
Status: completed
Notes:
- Update:
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/settings_system/settings_system.yaml`
  - `docs/features/cv_system/cv_system.yaml`
  - `docs/FitCV-pipeline.md`
- Mark this plan complete once implementation and verification are done.

## Verification

- Focused validator tests proving unresolved placeholder rejection
- Focused artifact/export tests for:
  - `settings-used.json`
  - `ranking.json`
  - `cv_generation.json`
  - `cv-debug.json`
  - aggregate export responsibility
- One representative end-to-end run artifact snapshot check
- `py_compile` on touched Python modules
