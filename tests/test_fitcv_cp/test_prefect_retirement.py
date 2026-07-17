from pathlib import Path

from fitcv_cp.orchestrator import OrchestrationAdapter, get_orchestration_adapter


def test_prefect_runtime_and_operator_surfaces_are_removed(monkeypatch) -> None:
    monkeypatch.setenv("FITCV_ORCHESTRATION_MODE", "prefect")

    adapter = get_orchestration_adapter()
    orchestrator_source = Path("src/fitcv_cp/orchestrator.py").read_text(encoding="utf-8")
    run_detail_template = Path("src/fitcv_cp/templates/run_detail.html").read_text(
        encoding="utf-8"
    )
    runs_list_template = Path("src/fitcv_cp/templates/runs_list.html").read_text(
        encoding="utf-8"
    )

    assert type(adapter) is OrchestrationAdapter
    assert adapter.name == "default_queue"
    assert "PrefectOrchestrationAdapter" not in orchestrator_source
    assert "PREFECT_" not in orchestrator_source
    assert "Orchestration Backend" not in run_detail_template
    assert "Backend Run ID" not in run_detail_template
    assert "Orchestration Schema Fallback Mode" not in runs_list_template
    assert not Path("scripts/verify_fitcv_orchestration_modes.ps1").exists()