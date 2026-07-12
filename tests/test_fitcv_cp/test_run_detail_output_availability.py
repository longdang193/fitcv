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
    assert 'id="outputs-action"' not in content
    assert 'id="run-overview-core"' in content
    assert "<h3 style=\"margin:0\">Synonyms (List Entities)</h3>" in content
    assert "<h3>Pipeline Results</h3>" in content
    assert "<h2>Event Timeline</h2>" in content
    assert "<h3 style=\"margin:0 0 0.85rem\">Artifacts</h3>" in content
    assert "Compatibility note: outputs/download actions moved to <strong>Artifacts</strong>." in content
    assert "output_availability." in content




def test_run_detail_template_enforces_canonical_section_order_and_no_overview_duplication() -> None:
    template_path = "src/fitcv_cp/templates/run_detail.html"
    content = open(template_path, encoding="utf-8").read()
    assert content.count(">Run Overview</h3>") == 1
    overview_pos = content.index(">Run Overview</h3>")
    synonym_pos = content.index(">Synonyms (List Entities)</h3>")
    pipeline_pos = content.index(">Pipeline Results</h3>")
    timeline_pos = content.index(">Event Timeline</h2>")
    artifacts_pos = content.index('id="artifacts"')
    advanced_pos = content.index('id="advanced-diagnostics"')
    assert overview_pos < synonym_pos < pipeline_pos < timeline_pos < artifacts_pos < advanced_pos
    assert 'id="outputs-action"' not in content

def test_advanced_diagnostics_collapsed_container_preserves_evidence_sections() -> None:
    template_path = "src/fitcv_cp/templates/run_detail.html"
    content = open(template_path, encoding="utf-8").read()
    assert '<details class="card" id="advanced-diagnostics">' in content
    assert "Advanced &amp; Diagnostics" in content
    assert "<h3 style=\"margin:0\">Stage Result Policy + Trace Summary</h3>" in content
    assert "<h3 style=\"margin:0\">Event Delivery Health</h3>" not in content
    assert "<h3 style=\"margin:0\">Telemetry Export Health</h3>" not in content
    assert "<h3 style=\"margin:0\">Langfuse Trace-Link Health</h3>" not in content
    assert "<h3 style=\"margin:0\">Dead-letter Replay Summary</h3>" not in content
    assert "<h3 style=\"margin:0\">Agentic Runtime Alignment</h3>" not in content
    assert content.index('id="artifacts"') < content.index('id="advanced-diagnostics"')
    assert "Replay Dead-letter Events" not in content
    assert "Synonym Fingerprints" not in content
    assert "Trace Links" not in content

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
    assert '/admin/runs/{{ run.run_id }}/bookmarks/save' in content
    assert '/admin/runs/{{ run.run_id }}/bookmarks/delete' in content
    assert 'href="#generated-outputs"' not in content


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
    )
    assert summary["status"] == RunStatus.SUCCEEDED.value
    assert summary["stage_count"] == 2




def test_enriched_tab_select_shell_wrappers_are_closed() -> None:
    template_path = "src/fitcv_cp/templates/run_detail_tab_enriched.html"
    content = open(template_path, encoding="utf-8").read()
    assert '<span class="enr-select-shell"><select id="enr-filter"' in content
    assert '</select></span>' in content
    assert content.count('</select></span>') >= 2


def test_enriched_tab_blank_links_use_noopener() -> None:
    template_path = "src/fitcv_cp/templates/run_detail_tab_enriched.html"
    content = open(template_path, encoding="utf-8").read()
    assert 'target="_blank" rel="noopener"' in content
