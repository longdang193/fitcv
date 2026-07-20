"""
@meta
type: test
scope: unit
domain: admin_ui
covers:
  - Local-only Run page prototype contract
tags:
  - fast
  - ci-safe
"""

from pathlib import Path


PROTOTYPE = Path("docs/fitcv-settings-ui-prototype.html")


def test_run_page_prototype_contract() -> None:
    html = PROTOTYPE.read_text(encoding="utf-8")

    assert 'href="#runs"' in html
    assert 'id="runDialog"' in html
    assert 'id="jobFile"' in html
    assert 'id="candidateProfile"' in html
    assert 'id="runName"' in html
    assert 'role="tablist"' in html
    assert '>Active<' in html
    assert '>Archived<' in html
    assert "Cancel Run" in html
    assert "Archive Run" in html
    assert "Delete Run" in html
    assert "function deleteSelectedRuns" in html
    assert "crypto.randomUUID" in html
    assert "Latest Synonym Overlay will be used automatically." in html
    assert "Execution Mode" not in html
    assert 'id="jobFile" type="file" required multiple' not in html
    assert "Supported: JSON and JSONL. One file per run." in html
    assert "Control how many shortlisted listings continue to ranking." in html
    assert "Listings collected before shortlisting begins." in html
    assert 'id="runPageSize"' in html
    assert "function paginationItems" in html
    assert "data-run-page" in html
    assert 'id="runDetailsDrawer"' in html
    assert 'id="runDetailsBody"' in html
    assert html.count('<dl class="details-grid') >= 2
    assert ".detail-item dt,.job-attribute span" in html
    assert ".detail-item dd,.job-attribute strong" in html
    assert "data-run-details" in html
    assert "Pipeline Results" in html
    assert "All Jobs" in html
    assert "CV Generation" in html
    assert "data-pipeline-stage" in html
    assert 'aria-label="Pipeline stages"' in html
    assert ".stage-filter{width:100%" in html
    assert ".pipeline-stage-tabs .btn{flex:1 0" in html
    assert html.index('aria-label="Pipeline stages"') < html.index('aria-label="Pipeline result filter"')
    assert html.index('id="jobResultsSearch"') < html.index('aria-label="Pipeline result filter"')
    assert "data-pipeline-result" in html
    assert 'id="pipelineResult"' not in html
    assert 'id="jobResultsSort"' not in html
    assert 'id="jobResultsSearch"' in html
    assert 'id="exportRunResults"' in html
    assert "data-interest-rating" in html
    assert "data-clear-interest" in html
    assert 'id="jobResultsPageSize"' in html
    assert "function exportRunResults" in html
    assert "fetch(" not in html
