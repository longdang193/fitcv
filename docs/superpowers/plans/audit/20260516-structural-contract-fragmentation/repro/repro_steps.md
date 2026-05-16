## Reproduction

- Preconditions:
  - Python virtual environment available at `.venv`.
  - Repository root at `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT`.
- Steps:
  1. Capture cross-module symbol usage for proposal lifecycle, stage artifacts, policy projection, and decision contracts.
  2. Inspect output files in `evidence/results/`.
  3. Confirm duplicated or fragmented symbols appear in multiple modules.
- Commands:

```powershell
rg -n "def _build_synonym_proposals_trace_payload|def _persist_synonym_proposals_snapshot|transition_synonym_proposal_status|build_synonym_proposals_payload" src/fitcv_cp/worker_job.py src/fitcv_cp/synonym_proposals.py
rg -n "def _build_stage_transition_artifacts_payload|stage_transition_artifacts|schema_version|artifact_schema_version" src/fitcv/pipeline.py src/fitcv_cp/worker_job.py src/fitcv_cp/app.py
rg -n "synonym_proposals_enabled|proposal_review_enabled|proposal_global_promotion_enabled|proposal_triage_auto_recommend_enabled|proposal_auto_apply_recommendations|proposal_auto_promote_global" src/fitcv_cp/settings_schema.py src/fitcv_cp/app.py src/fitcv_cp/worker_job.py
rg -n "RunStatus|status|decision_reason|transition" src/fitcv_cp/app.py src/fitcv_cp/synonym_proposals.py src/fitcv_cp/worker_job.py
```

- Determinism notes: deterministic symbol search against checked-out source at captured commit.
