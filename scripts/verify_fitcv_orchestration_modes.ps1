[CmdletBinding()]
param(
    [string]$BaseUrl = "http://localhost:8000",
    [string]$RunId,
    [switch]$RequirePrefect,
    [switch]$RequireQueue
)

$ErrorActionPreference = "Stop"

function Write-Check {
    param(
        [string]$Label,
        [bool]$Passed,
        [string]$Detail
    )
    $status = if ($Passed) { "PASS" } else { "FAIL" }
    Write-Host ("[{0}] {1} - {2}" -f $status, $Label, $Detail)
    if (-not $Passed) {
        throw "Verification failed: $Label"
    }
}

$base = $BaseUrl.TrimEnd("/")

$schema = Invoke-RestMethod -Method Get -Uri "$base/admin/diagnostics/orchestration-schema"
$requiredColumns = @("orchestration_backend", "orchestration_run_id")
$schemaHasColumns = @($schema.required_columns) -join "," -eq ($requiredColumns -join ",")
Write-Check "schema-required-columns" $schemaHasColumns ("required_columns={0}" -f (@($schema.required_columns) -join ","))
Write-Check "schema-status" ($schema.status -in @("complete", "fallback")) ("status={0}" -f $schema.status)

$runs = Invoke-RestMethod -Method Get -Uri "$base/runs"
$runCount = @($runs).Count
Write-Check "runs-available" ($runCount -gt 0) ("count={0}" -f $runCount)

$backends = @()
foreach ($run in @($runs)) {
    if ($run.orchestration_backend) {
        $backends += [string]$run.orchestration_backend
    } elseif ($run.queue_job_id) {
        $backends += "default_queue"
    }
}
$backendSet = [System.Collections.Generic.HashSet[string]]::new([System.StringComparer]::OrdinalIgnoreCase)
foreach ($backend in $backends) {
    [void]$backendSet.Add($backend)
}
if ($RequirePrefect) {
    Write-Check "prefect-backend-present" ($backendSet.Contains("prefect")) ("backends={0}" -f (($backendSet | Sort-Object) -join ","))
}
if ($RequireQueue) {
    Write-Check "queue-backend-present" ($backendSet.Contains("default_queue")) ("backends={0}" -f (($backendSet | Sort-Object) -join ","))
}

$selectedRunId = $RunId
if (-not $selectedRunId) {
    $selectedRunId = [string]@($runs)[0].run_id
}
Write-Host ("[INFO] selected run_id={0}" -f $selectedRunId)

$runJson = Invoke-RestMethod -Method Get -Uri "$base/runs/$selectedRunId"
$hasBackendField = -not [string]::IsNullOrWhiteSpace([string]$runJson.orchestration_backend) -or -not [string]::IsNullOrWhiteSpace([string]$runJson.queue_job_id)
$hasRunIdField = -not [string]::IsNullOrWhiteSpace([string]$runJson.orchestration_run_id) -or -not [string]::IsNullOrWhiteSpace([string]$runJson.queue_job_id)
Write-Check "run-json-backend-evidence" $hasBackendField "orchestration_backend/queue_job_id present"
Write-Check "run-json-run-id-evidence" $hasRunIdField "orchestration_run_id/queue_job_id present"

$runDetailHtml = Invoke-WebRequest -Method Get -Uri "$base/admin/runs/$selectedRunId"
$detailBody = [string]$runDetailHtml.Content
Write-Check "run-detail-label-backend" ($detailBody.Contains("Orchestration Backend")) "Run detail contains backend label"
Write-Check "run-detail-label-run-id" ($detailBody.Contains("Backend Run ID")) "Run detail contains backend run id label"
Write-Check "run-detail-label-status" ($detailBody.Contains("Backend Status")) "Run detail contains backend status label"

Write-Host "[PASS] Orchestration verification complete."
