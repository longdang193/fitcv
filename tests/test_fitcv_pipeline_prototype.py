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
INTEGRATION_INTENT = Path("docs/fitcv-settings-ui-prototype.integration.md")


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
    assert 'id="runDetailsDrawer"' not in html
    assert 'href="#runs">← Back to Runs</a>' in html
    assert "function runDetailsId()" in html
    assert "#run-details/" in html
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
    assert "event.target===runDetailsDrawer" not in html
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

def test_candidate_profile_theme_and_data_backup_ui_contract() -> None:
    html = PROTOTYPE.read_text(encoding="utf-8")

    assert 'id="profileDetailsDrawer"' not in html
    assert 'href="#candidate-profiles">← Back to Candidate Profiles</a>' in html
    assert "function profileDetailsId()" in html
    assert "#candidate-profiles/" in html
    assert ">Appearance<" not in html
    assert 'id="dataBackupNav" href="#data-backup"' in html
    assert "function renderDataBackupPage()" in html
    assert 'id="downloadWorkspaceBackup"' in html
    assert 'id="chooseWorkspaceBackup"' in html
    assert 'id="restoreWorkspaceBackup"' in html
    assert ".backup-actions .btn[hidden]{display:none}" in html
    assert 'accept=".fitcv.zip,.zip,application/zip"' in html
    assert "fitcv-backup.v1" in html
    assert "Switch to dark theme" in html
    assert "Switch to light theme" in html
    assert '<circle cx="12" cy="12" r="4"></circle>' in html
    assert "M20.5 14.3A8.5 8.5" in html
    assert "theme.querySelector('svg').innerHTML=dark?'<circle" in html
    assert "</path>':'<path d=\"M20.5 14.3A8.5 8.5" in html


def test_api_provider_and_llm_configuration_ui_contract() -> None:
    html = PROTOTYPE.read_text(encoding="utf-8")

    assert 'id="apiProvidersNav" href="#api-providers"' in html
    assert 'id="llmConfigurationNav" href="#llm-configuration"' in html
    assert "function providerDetailsId()" in html
    assert "#api-providers/" in html
    assert 'href="#api-providers">← Back to API Providers</a>' in html
    assert "function renderApiProvidersPage()" in html
    assert "function renderProviderDetailsPage()" in html
    assert "function renderLlmConfigurationPage()" in html
    assert "Add OpenAI-compatible" in html
    assert "Add Anthropic-compatible" in html
    assert "OpenAI" in html
    assert "Anthropic" in html
    assert "DeepSeek" in html
    assert "Groq" in html
    assert "Responses API" in html
    assert "Chat Completions" in html
    assert "Messages API" in html
    assert "Each provider supports one connection." in html
    assert "API Key Providers" in html
    assert "Shared Providers" not in html
    assert "Connected" in html
    assert "No connection" in html
    assert "1 connection" not in html
    assert "API keys are never saved in browser storage." in html
    assert "credentialConfigured" in html
    assert 'id="providerApiKey"' in html
    assert 'id="providerModelId"' not in html
    assert 'id="providerApiType"' in html
    assert 'id="providerModelDialog"' in html
    assert 'id="testProviderModel"' in html
    assert 'id="saveProviderModel"' in html
    assert "data-test-model" in html
    assert "data-toggle-model" not in html
    assert "data-remove-model" in html
    assert "Connection required before adding or testing models." in html
    assert "Add Model saves only after a successful test." in html
    assert "testedProviderModelId!==modelId" in html
    assert "Fixed by provider protocol." in html
    assert "Defined by FitCV for this provider." in html
    assert "model.verified=false" in html
    assert "provider.models.filter(model=>model.verified)" in html
    assert 'id="defaultLlmModel"' in html
    assert "Task Overrides" in html
    assert "fetch(" not in html

def test_prototype_integration_intent_tracks_profile_theme_and_backup_wiring() -> None:
    intent = INTEGRATION_INTENT.read_text(encoding="utf-8")

    assert "GET /candidate-profiles/{profile_id}" in intent
    assert "Back to Candidate Profiles" in intent
    assert "Appearance is absent from sidebar" in intent
    assert "POST /local/data/backup" in intent
    assert "POST /local/data/import" in intent
    assert "fitcv-backup.v1" in intent
    assert "## API Providers" in intent
    assert "Windows Credential Manager" in intent
    assert "one connection" in intent
    assert "## LLM Configuration" in intent
    assert "OpenAI-compatible" in intent
    assert "Anthropic-compatible" in intent
    assert "connection counts are not shown" in intent
    assert "Needs retest" in intent
    assert "validation before Add Model" in intent


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
