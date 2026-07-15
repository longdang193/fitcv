# Reproduction Steps

```powershell
python -m pytest tests/test_pipeline.py::test_run_pipeline_persists_structured_cv_and_includes_it_in_export tests/test_pipeline.py::test_run_pipeline_returns_debug_record_for_accepted_cv tests/test_pipeline.py::test_run_pipeline_cv_generation_parallel_completion_preserves_deterministic_debug_order tests/test_pipeline.py::test_enrich_jobs_with_reuse_preserves_order_and_separates_shared_upserts tests/test_pipeline.py::test_run_pipeline_builds_cv_analysis_trace_for_agentic_analysis_stage tests/test_pipeline.py::test_run_pipeline_incremental_enrich_persists_each_store_exactly_once -q
```

Expected after fix: `6 passed`.

```powershell
python -m pytest tests/test_candidate_profile_template_contract.py::test_candidate_profile_split_files_exist_and_parse tests/test_prompts.py::test_render_prompt_cv_generation_structured_write_includes_schema -q
```

Expected after local fixture setup and test repair: `2 passed`.
