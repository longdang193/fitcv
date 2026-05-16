# Repro steps

1. Trigger baseline run:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/runs" -Method Post -ContentType "application/json" -Body '{"jobs_path":"data/sample_jobs.json","config_path":"config/env.yaml","triggered_by":"codex-live-debug","config_overrides":{},"run_mode":"run_all"}'
```
2. Trigger YAML paste run:
```powershell
$yaml = Get-Content -Raw data/candidate_profile.yaml
Invoke-RestMethod -Uri "http://localhost:8000/admin/upload-trigger" -Method Post -Form @{ jobs_input_mode='path'; jobs_path='data/sample_jobs.json'; candidate_profile_mode='paste'; candidate_profile_text=$yaml; run_mode='run_all'; config_path='config/env.yaml' }
```
3. Observe response 422 with detail: Invalid JSON in candidate profile.
