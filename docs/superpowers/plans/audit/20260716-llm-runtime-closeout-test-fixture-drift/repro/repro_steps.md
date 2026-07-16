# Reproduction Steps

1. Restore stale fixtures by returning a bare list from the five `mock_run_vector_search` assignments and removing `ranking_policy` plus `decision_learning_policy` from `_minimal_config`.
2. Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_pipeline_agentic_late_stage.py::test_run_pipeline_emits_effective_concurrency_for_enrich_and_ranking_events tests/test_pipeline_agentic_late_stage.py::test_run_pipeline_uses_agentic_late_stage_path_under_hard_flip tests/test_pipeline_agentic_late_stage.py::test_run_pipeline_routes_through_agentic_late_stage_when_enabled tests/test_pipeline_agentic_late_stage.py::test_run_pipeline_marks_review_required_and_skips_persist_when_agentic_gate_triggers tests/test_pipeline_agentic_late_stage.py::test_run_pipeline_marks_review_required_from_markdown_quality_flags -q
```

3. Expected stale-fixture result: deterministic failure at shortlist result shape, then preference-policy config after shortlist fixture correction.
4. Restore current fixtures.
5. Run same command.
6. Expected fixed result: `5 passed`.