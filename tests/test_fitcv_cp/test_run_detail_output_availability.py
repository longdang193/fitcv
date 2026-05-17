from __future__ import annotations

import datetime

from fitcv_cp.app import (
    _build_output_availability,
    _count_dict_leaf_differences,
    _run_detail_visibility_registry,
    _run_overview_consistency_summary,
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


def test_run_detail_template_mentions_output_availability_contract() -> None:
    template_path = "src/fitcv_cp/templates/run_detail.html"
    content = open(template_path, encoding="utf-8").read()
    assert 'id="outputs-action"' in content
    assert 'id="run-overview-core"' in content
    assert 'id="advanced-diagnostics"' in content
    assert 'href="/admin/runs/{{ run.run_id }}/synonym-review"' in content
    assert 'href="/admin/runs/{{ run.run_id }}/artifacts"' in content
    assert 'href="#diag-synonym-fingerprints"' in content
    assert 'id="synonym-review-workspace"' in content
    assert 'id="synonym-review-overview"' in content
    assert 'id="artifacts-overview"' in content
    assert 'id="run-exports-workspace"' in content
    assert 'id="diag-synonym-fingerprints"' in content
    assert 'id="diag-event-delivery-health"' in content
    assert 'id="diag-telemetry-export-health"' in content
    assert 'id="diag-langfuse-trace-link-health"' in content
    assert 'id="diag-dead-letter-replay-summary"' in content
    assert 'id="diag-agentic-runtime-alignment"' in content
    assert "overview_consistency_summary.dead_letter_events" in content
    assert "Run-scoped overlay: synonym overrides applied only to this run." in content
    assert "Triage mode: strategy for recommendation freshness and reuse behavior." in content
    assert "Suppressed: proposals hidden by suppression policy or duplicate resolution." in content
    assert "Alias conflict: alias currently maps to another canonical term and needs explicit decision." in content
    assert "Confidence score: model certainty for proposed mapping." in content
    assert "output_availability." in content


def test_overview_core_excludes_diagnostic_only_snippets() -> None:
    template_path = "src/fitcv_cp/templates/run_detail.html"
    content = open(template_path, encoding="utf-8").read()
    start = content.index('id="run-overview-core"')
    end = content.index("<!-- ── Run Metadata Card", start)
    overview_block = content[start:end]
    assert "pre_run_global={{ synonym_fingerprints.pre_run_global_map_fingerprint" not in overview_block
    assert "overlay={{ synonym_fingerprints.run_overlay_fingerprint" not in overview_block
    assert "suggestions={{ synonym_fingerprints.mapping_suggestions_fingerprint" not in overview_block
    assert '/admin/cvs/{{ cv.version_id }}/download' in content
    assert 'href="#generated-outputs"' in content


def test_run_detail_visibility_registry_has_expected_tiers() -> None:
    registry = _run_detail_visibility_registry()
    assert {"core", "advanced", "diagnostic"} <= set(registry.keys())
    assert any(entry["name"] == "status" for entry in registry["core"])
    assert any(entry["name"] == "synonym_fingerprints" for entry in registry["diagnostic"])


def test_effective_settings_delta_counter_counts_leaf_changes() -> None:
    baseline = {"pipeline": {"top_n": 10, "threshold": 0.2}, "mode": "run_all"}
    effective = {"pipeline": {"top_n": 15, "threshold": 0.2}, "mode": "manual_staged"}
    assert _count_dict_leaf_differences(baseline, effective) == 2


def test_overview_consistency_summary_matches_diagnostics_sources() -> None:
    run = _run(status=RunStatus.SUCCEEDED, cvs_generated=1)
    summary = _run_overview_consistency_summary(
        run,
        stage_result_summary_rows=[{"stage_id": "a"}, {"stage_id": "b"}],
        event_delivery_health={"count": 3},
    )
    assert summary["status"] == RunStatus.SUCCEEDED.value
    assert summary["stage_count"] == 2
    assert summary["dead_letter_events"] == 3
