from __future__ import annotations

import datetime

from fitcv_cp.app import _build_output_availability
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


def test_run_detail_template_mentions_output_availability_contract() -> None:
    template_path = "src/fitcv_cp/templates/run_detail.html"
    content = open(template_path, encoding="utf-8").read()
    assert 'id="outputs-action"' in content
    assert "output_availability." in content
    assert '/admin/cvs/{{ cv.version_id }}/download' in content
    assert 'href="#generated-outputs"' in content
