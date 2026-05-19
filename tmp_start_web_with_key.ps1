$line = Get-Content 'C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.env' | Where-Object { $_ -match '^OPENAI_API_KEY\s*=' } | Select-Object -First 1
if (-not $line) { throw 'OPENAI_API_KEY not found in .env' }
$openaiKey = ($line -split '=',2)[1].Trim()
$env:FITCV_LLM_API_KEY = $openaiKey
$env:FITCV_ENRICH_DEBUG_HEARTBEAT = '1'
$env:FITCV_ENRICH_JOB_TIMEOUT_SECS = '10'
Set-Location 'C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT'
./start_web.ps1 -Port 8000
