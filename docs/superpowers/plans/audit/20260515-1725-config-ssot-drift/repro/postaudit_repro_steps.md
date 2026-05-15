Post-audit repro/verification
1) Confirm candidate profile path now canonical in env.yaml.
2) Scan overlap signatures across env/live_smoke and pipeline families.
3) Run focused config-shape tests.
Commands:
rg -n "candidate_profile" config/env.yaml
rg -n "^(gcp_project|bigquery_dataset|service_account_key|location|enrichment_max_retries|paths:|\s+candidate_profile:|seniority_ladder:|application_statuses:)" config/env.yaml config/live_smoke.yaml
rg -n "^(gemini_model|embedding_model|enrichment_sleep_secs|vector_top_n|vector_max_candidate_skills|retrieval_strategy|rerank_top_n|rerank_sleep_secs|pipeline:|\s+vector_search_top_n:|\s+ai_score_top_n:|\s+final_top_n:|\s+evidence_top_k:)" config/runtime/pipeline.yaml config/live_smoke.yaml config/env.yaml
C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.venv\Scripts\python.exe -m pytest tests/test_config.py -k "defaults_to_repo_config_shape or accepts_legacy_config_env_path_with_warning" -q
