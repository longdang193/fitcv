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


def test_runtime_limits_prototype_uses_shared_pacing_and_concurrency_only() -> None:
    text = PROTOTYPE.read_text(encoding="utf-8")

    assert "Minimum Request Start Interval (seconds)" in text
    assert "same provider connection" in text
    assert "Zero disables pacing" in text
    assert "retry backoff remains separate" in text
    assert text.count("label:'Maximum Concurrent Jobs'") == 1
    assert "maximum concurrent jobs`" in text
    assert "Request Delay" not in text
    assert "Batch Size" not in text
    assert "CV Analysis runs locally and does not use provider request pacing." in text


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
    profile_details = html[html.index("function renderProfileDetails"):html.index("function openProfileDetails")]
    assert run_details.count('<details class="section-card collapsible-section drawer-section" open>') == 3
    assert run_details.count('class="section-card collapsible-section drawer-section"') == 4
    assert run_details.count('class="drawer-status"') == 1
    assert profile_details.count('class="drawer-status"') == 1
    assert "Used by Runs" not in profile_details
    assert "data-profile-run-details" not in profile_details
    assert "const relatedRuns=" not in profile_details
    assert ".details-page-layout{display:grid;gap:18px}" in html
    assert "form.classList.toggle('details-page-layout',isProfileDetailsPage()||isRunDetailsPage()||isOptimizationDetailsPage())" in html
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
    assert "${run.archived?'Archived run':'Active run'}" not in html
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
    assert 'id="systemNav" href="#system"' in html
    assert 'id="dataBackupNav"' not in html
    assert ">Health</a>" not in html
    assert "function renderSystemPage()" in html
    assert 'id="downloadWorkspaceBackup"' in html
    assert 'id="chooseWorkspaceBackup"' in html
    assert 'id="restoreWorkspaceBackup"' in html
    assert ".backup-actions .btn[hidden]{display:none}" in html
    assert 'accept=".fitcv.zip,.zip,application/zip"' in html
    assert "fitcv-backup.v1" in html
    assert 'id="shutdownDialog"' in html
    assert 'id="openShutdownDialog"' in html
    assert 'id="confirmShutdown"' in html
    assert html.index('id="theme"') < html.index('id="openShutdownDialog"')
    assert ".icon-btn.danger{color:#b91c1c}" in html
    assert ".btn.danger,.icon-btn.danger{border-color" not in html
    assert "system-danger" not in html
    assert "Shutdown FitCV" in html
    assert "Shutdown is unavailable while work is active." in html
    assert ".title-icon{width:23px;height:23px;flex:0 0 23px" in html
    assert ".run-table tbody tr:hover,.provider-card:hover{background:var(--surface-2)}" in html
    assert "transform:translateY(-1px)" not in html
    assert "Switch to dark theme" in html
    assert "Switch to light theme" in html
    assert '<circle cx="12" cy="12" r="4"></circle>' in html
    assert "M20.5 14.3A8.5 8.5" in html
    assert "theme.querySelector('svg').innerHTML=dark?'<circle" in html
    assert "</path>':'<path d=\"M20.5 14.3A8.5 8.5" in html

def test_preference_optimization_prototype_contract() -> None:
    html = PROTOTYPE.read_text(encoding="utf-8")
    main = html[
        html.index("function renderPreferenceOptimizationPage()"):
        html.index("function startPreferenceOptimization()")
    ]
    start = html[
        html.index("function startPreferenceOptimization()"):
        html.index("function toggleOptimizationPolicy")
    ]
    details = html[
        html.index("function renderOptimizationDetailsPage()"):
        html.index("function isSynonymsPage()")
    ]

    assert main.count('class="section-card collapsible-section setting-section"') == 4
    assert "Baseline Ranking" in main
    assert "Personalized Ranking" in main
    assert "Restore Defaults" not in main
    assert "Higher values allow larger changes from Baseline Ranking." in main
    assert "Inactivate Policy before changing Personalization Strength." in main
    assert "Baseline Ranking is being used until a policy is activated." in main
    assert "Optimize Current Ratings" in main
    assert "Eligible Comparisons" not in main
    assert "Optimization ID" in main
    assert "Policy" in main
    assert "Actions" in main
    assert "Active · Not in use" in html
    assert "Optimizing…" in start
    assert "status:'Running'" not in start
    assert "item.hiddenAt=Date.now()" in html
    assert "optimizationState.history=optimizationState.history.filter" not in html
    assert "filter(item=>!item.hiddenAt)" in html
    assert "por_${date}_${sequence}" in html
    assert details.count('class="section-card collapsible-section drawer-section"') == 3
    assert "Overview" in details
    assert "Rating Evidence" in details
    assert "Console Log" in details
    assert "Removed from Optimization Runs" in details
    assert "Results Summary" not in details
    assert "Technical Details" not in details
    assert "Policy Version" not in details
    assert "Reject Version" not in details
    assert "optimizationConsoleMarkup(item)" in details
    assert "data-optimization-console-clear" in html


def test_api_provider_and_llm_configuration_ui_contract() -> None:
    html = PROTOTYPE.read_text(encoding="utf-8")

    assert 'id="apiProvidersNav" href="#api-providers"' in html
    assert 'id="llmConfigurationNav" href="#llm-configuration"' in html
    assert 'id="promptManagementNav" href="#prompt-management"' in html
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
    assert "function providerConnected(provider)" in html
    assert "provider.connectionStatus==='verified'" in html
    assert 'id="providerApiKey"' in html
    assert 'id="providerModelId"' not in html
    assert 'id="providerApiType"' in html
    assert 'id="providerModelDialog"' in html
    assert 'id="testProviderConnection"' in html
    assert ">Test</button>" in html
    assert "Verify Connection" not in html
    assert 'id="saveProviderConnection" type="button" disabled' in html
    assert "connectionTestPassed=false" in html
    assert "Test this connection successfully before saving it." in html
    assert 'id="testProviderModel"' in html
    assert '<button class="btn" id="testProviderModel" type="button">Test</button>' in html
    assert '<button class="btn" id="testProviderModel" type="button"><svg' not in html
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
    assert ".provider-grid{display:grid;grid-template-columns:1fr;gap:0}" in html
    assert ".provider-grid{display:grid;grid-template-columns:1fr;gap:0;overflow:hidden" not in html
    assert '<div class="provider-add-actions">' in html
    assert ".provider-empty{padding:22px;color:var(--muted);text-align:center}" in html
    assert ".provider-empty{padding:22px;border:" not in html
    assert "provider.models.filter(model=>model.verified)" in html
    assert 'id="defaultLlmModel"' in html
    assert "Task Overrides" not in html
    assert "Stage LLM Configuration" not in html
    assert "Task Configuration" in html
    assert "function taskLlmRowMarkup" in html
    assert "data-manage-llm-task" in html
    assert 'id="taskLlmDialog"' in html
    assert 'id="taskLlmModel"' in html
    assert 'id="taskLlmTimeout"' in html
    assert 'id="taskLlmTemperature"' in html
    assert "Enrich Extraction" in html
    assert "Ranking AI Score" in html
    assert "CV Generation" in html
    assert "Synonym Recommendation" in html
    assert "Synonym Triage Recommendation" not in html
    assert "function renderPromptManagementPage()" in html
    assert "Pipeline Prompts" in html
    assert "Synonym Prompts" in html
    assert "Prompt used to review synonym proposals and recommend an action." in html
    assert "routes through an external LLM provider" not in html
    assert "Manage Prompt" in html
    assert 'id="stagePromptDialog"' in html
    assert 'id="stagePromptType"' in html
    assert 'id="stagePromptEditor"' in html
    assert 'maxlength="4000"' in html
    assert "4000 characters" in html
    assert "Character limit reached." in html
    assert "Request Retry" in html
    assert 'id="systemMaximumAttempts"' in html
    assert 'id="systemInitialBackoff"' in html
    assert 'id="systemLeaseSeconds"' in html
    assert 'id="systemReconcilerInterval"' in html
    assert 'id="systemErrorDetailLimit"' in html
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
