from __future__ import annotations

import datetime

from fitcv_cp.app import (
    _build_output_availability,
    _count_dict_leaf_differences,
)
from fitcv_cp.models import PipelineRun, RunStatus


def _run(*, status: RunStatus, cvs_generated: int | None) -> PipelineRun:
    return PipelineRun(
        run_id="run-1",
        status=status,
        triggered_by="test",
        trigger_source="test",
        jobs_path="jobs.yaml",
        config_path="config.yaml",
        created_at=datetime.datetime.now(datetime.timezone.utc),
        cvs_generated=cvs_generated,
    )


def test_output_availability_available_when_version_rows_exist() -> None:
    run = _run(status=RunStatus.SUCCEEDED, cvs_generated=2)
    cv_versions = [{"version_id": "v1"}, {"version_id": "v2"}]
    result = _build_output_availability(run, cv_versions)
    assert result["state"] == "available"
    assert result["downloadable_count"] == 2


def test_output_availability_mismatch_when_generated_but_no_rows() -> None:
    run = _run(status=RunStatus.SUCCEEDED, cvs_generated=2)
    result = _build_output_availability(run, [])
    assert result["state"] == "mismatch"
    assert result["generated_count"] == 2
    assert result["downloadable_count"] == 0


def test_output_availability_not_ready_when_run_not_succeeded() -> None:
    run = _run(status=RunStatus.RUNNING, cvs_generated=None)
    result = _build_output_availability(run, [])
    assert result["state"] == "not_ready"


def test_run_detail_template_matches_prototype_drawers_and_profile_snapshot() -> None:
    content = open("src/fitcv_cp/templates/run_detail.html", encoding="utf-8").read()
    overview_pos = content.index("Run Overview")
    input_pos = content.index("Run Input")
    results_pos = content.index("Pipeline Results")
    console_pos = content.index('{% include "_process_console.html" %}')
    assert overview_pos < input_pos < results_pos < console_pos
    assert content.count("<details") >= 3
    assert "Profile ID" in content
    assert "Profile State" in content
    assert "/admin/candidate-profiles/{{ candidate_profile_id }}" in content
    assert "Cancel Run" not in content
    assert "Run Again" not in content
    assert "Archive</button>" not in content
    assert 'id="process-console"' not in content


def test_effective_settings_delta_counter_counts_leaf_changes() -> None:
    baseline = {"pipeline": {"top_n": 10, "threshold": 0.2}, "mode": "run_all"}
    effective = {"pipeline": {"top_n": 15, "threshold": 0.2}, "mode": "manual_staged"}
    assert _count_dict_leaf_differences(baseline, effective) == 2


def test_enriched_tab_matches_prototype_job_actions_and_attributes() -> None:
    content = open(
        "src/fitcv_cp/templates/run_detail_tab_enriched.html", encoding="utf-8"
    ).read()
    assert "Application Interest" in content
    assert "data-interest-rating" in content
    assert "data-clear-interest" in content
    assert "data-cv-download" in content
    assert "data-cv-regenerate" in content
    assert "cv-review" in content
    assert "Language" in content
    detail_content = open("src/fitcv_cp/templates/run_detail.html", encoding="utf-8").read()
    assert "classList.toggle('is-selected'" in detail_content


def test_enriched_tab_matches_prototype_pagination_sizes_and_controls() -> None:
    content = open(
        "src/fitcv_cp/templates/run_detail_tab_enriched.html", encoding="utf-8"
    ).read()
    assert 'target="_blank" rel="noopener noreferrer"' in content
    assert "(10, 20, 50)" in content
    assert "data-run-page-number" in content
