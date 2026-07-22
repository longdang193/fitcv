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
    assert "function archivedRunDeletionPreview" in html
    assert "previewRevision" in html
    assert "bookmarked job" in html
    assert "crypto.randomUUID" in html
    assert "Latest Synonym Overlay will be used automatically." not in html
    assert "Synonym Overlay" not in html
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
    run_details = html[html.index("function renderRunDetails"):html.index("function bindRunDetails")]
    assert run_details.count('<details class="section-card collapsible-section drawer-section" open>') == 3
    assert run_details.count('class="section-card collapsible-section drawer-section"') == 4
    assert "Console Log" in html
    assert "Clear View" in html
    assert "Download Debug Bundle" in html
    assert "canonical run events loaded" not in html
    assert 'role="log"' in html
    assert "data-console-clear" in html
    assert "data-console-download" in html
    assert 'class="section-card collapsible-section setting-section"' in html
    assert 'class="setting-section table-card"' not in html
    assert '.collapsible-section summary' in html
    assert run_details.count('class="section-content drawer-section-content"') == 4
    assert 'class="section-content settings-card"' in html
    assert 'class="settings-card drawer-section-content"' not in html
    assert '<section class="drawer-section">' not in html
    assert "event.target===runDetailsDrawer" in html
    assert "clientX<bounds.left" not in html
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
    assert "Job &amp; Actions" in html
    assert "Application Interest</th>" not in html
    assert "data-bookmark-job" in html
    assert 'class="small-action clear-rating"' in html
    assert ">Clear</button>${showBookmark?bookmarkMarkup(run,job):''}" in html
    assert "data-generated-cv-action" in html
    assert "Download CV" in html
    assert "Regenerate CV" in html
    assert "cv-review" in html
    assert ".summary-card{display:inline-flex" in html
    assert ".jobs-table th:first-child,.jobs-table td:first-child{position:sticky" in html
    assert "sizeId=bookmarksMode?'bookmarkPageSize':'jobResultsPageSize'" in html
    assert "querySelector('#jobResultsPageSize')" in html
    assert "function exportRunResults" in html
    assert "fetch(" not in html


def test_synonym_backup_prototype_uses_opaque_zip_contract() -> None:
    html = PROTOTYPE.read_text(encoding="utf-8")

    assert "fitcv-synonyms-backup.zip" in html
    assert "application/zip" in html
    assert 'accept=".zip,application/zip"' in html
    assert "skill_synonyms.yaml" in html
    assert "domain_synonyms.yaml" in html
    assert "role_family_synonyms.yaml" in html
    assert "manifest.json" in html
    assert "synonym-backup.yaml" not in html
    assert "reader.readAsText(file)" not in html
