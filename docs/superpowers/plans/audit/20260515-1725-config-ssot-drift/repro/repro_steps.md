Preconditions:
- Repo present at captured commit
- Target files exist:
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - config/env.private.yaml
  - config/env.yaml
  - .env

Steps:
1. Snapshot all five files (redact secret values from .env evidence).
2. Scan overlap keys across env surfaces.
3. Compare against runtime policy ownership comments and loader behavior.
4. Classify against audit-evidence mandate trigger list.

Commands:
Get-Content -Raw config/runtime/control_plane.yaml
Get-Content -Raw config/runtime/pipeline.yaml
Get-Content -Raw config/env.private.yaml
Get-Content -Raw config/env.yaml
Get-Content .env | Where-Object {$_ -match ''^[A-Za-z_][A-Za-z0-9_]*=''} | ForEach-Object { ($_ -split ''='',2)[0] }
rg -n "^(gcp_project|bigquery_dataset|service_account_key|location|enrichment_max_retries|paths:|\s+candidate_profile:|seniority_ladder:|application_statuses:)" config/env.private.yaml config/env.yaml
rg -n "^(gemini_model|embedding_model|enrichment_sleep_secs|vector_top_n|vector_max_candidate_skills|retrieval_strategy|rerank_top_n|rerank_sleep_secs|pipeline:|\s+vector_search_top_n:|\s+ai_score_top_n:|\s+final_top_n:|\s+evidence_top_k:)" config/runtime/pipeline.yaml config/env.private.yaml config/env.yaml

Expected:
- No duplicate ownership for canonical keys.

Actual:
- Duplicate key ownership across env surfaces; runtime knobs split across env + pipeline + control-plane + .env.
