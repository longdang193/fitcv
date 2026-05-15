---
layer: audit
artifact_type: report
template_id: audit-report-with-evidence
status: open
name: live-run-disk-io-error
---

# Audit Report With Evidence

## Metadata

- Audit ID: `20260515-1633-live-run-disk-io-error`
- Status: `mitigated`
- Severity: `medium`
- Owner: `codex`
- Created At: `2026-05-15T16:30:00+02:00`
- Updated At: `2026-05-15T16:59:00+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-05-15-15-43-cv-generation-selected-evidence-grounding-plan.md`

## Scope

- Environment: Windows host + docker compose (`web`, `worker`, `redis`) on `http://localhost:8000`
- Commit/Branch: `a9f750651eb53c1f11c0516c8031ec308de3c9b4` (working tree)
- Affected Surface: control-plane live run persistence/runtime storage (run fails before `rank` / `cv_generation`)

## Findings

### Finding F-1: Live run fails with `disk I/O error`

- Classification: `environment`
- Impact: Live-run trigger sometimes fails early; blocks runtime verification; user-visible run status becomes `failed`.
- Expected Behavior: Live run progresses through pipeline stages and completes (succeeded or deterministic stage-owned failure with artifacts).
- Actual Behavior: Run fails after `rule_filter` with `error_message="disk I/O error"` and no completed CV stage.

## Evidence

- Result JSON: `evidence/results/run.json`
  - `run_id=db3b22e8-8672-4c92-b74c-2eb692402320`
  - `status=failed`
  - `error_message="disk I/O error"`
- Result JSON: `evidence/results/events.json`
  - shows `pipeline_failed` event with message `disk I/O error`
- Capture timestamp: `evidence/results/captured_at.txt`
- Post-fix verification runs (all succeeded):
  - `evidence/results/postfix-run-449820b5-0382-4dba-b8c8-a9f72ed75088.json`
  - `evidence/results/postfix-run-35cc209e-686c-4f86-861c-68dbcd75f0fe.json`
  - `evidence/results/postfix-run-7b5f3ce3-f1bf-4c90-a08f-628c9c04f388.json`
  - `evidence/results/postfix-captured_at.txt`
- Checksums: `manifest.yaml`

## Reproduction

- Preconditions:
  - docker compose running (`web`, `worker`, `redis`)
  - control plane reachable at `http://localhost:8000`
- Steps:
  1. Trigger run via `POST /runs` with `jobs_path=data/sample_jobs.json` and `config_path=config/env.yaml`.
  2. Observe run transitions to `failed`.
- Commands:

```powershell
$body = @{ jobs_path = 'data/sample_jobs.json'; config_path = 'config/env.yaml'; triggered_by = 'codex'; run_mode = 'run_all' } | ConvertTo-Json
$resp = Invoke-RestMethod -Method Post -Uri "http://localhost:8000/runs" -ContentType "application/json" -Body $body
Invoke-RestMethod -Method Get -Uri ("http://localhost:8000/runs/" + $resp.run_id)
Invoke-RestMethod -Method Get -Uri ("http://localhost:8000/runs/" + $resp.run_id + "/events")
```

- Determinism notes: appears intermittent/flaky; immediate rerun may succeed.

## Root Cause And Boundary

- Failure boundary: sqlite persistence write paths used by worker during live runs.
- Root cause summary: sqlite `conn.commit()` intermittently throws `sqlite3.OperationalError: disk I/O error` on Docker Desktop Windows bind mount (`./data:/app/data`) under concurrent runtime access.
  - observed boundaries:
    - vector shortlist persistence: `src/fitcv/vector_search.py` `store_shortlist()` commit
    - run status persistence: `src/fitcv_cp/bq_store.py` `_upsert_local_pipeline_run()` commit

## Fix And Verification

- Fix summary (bounded):
  - sqlite connections now use WAL + busy timeout (`busy_timeout=30000`, `timeout=30`) across key write paths
  - critical commits now retry on `"disk I/O error"` with short backoff
- Files changed:
  - `src/fitcv/vector_search.py`
  - `src/fitcv/embeddings.py`
  - `src/fitcv/enrich.py`
  - `src/fitcv_cp/bq_store.py`
- Verification commands:

```powershell
$body = @{ jobs_path = 'data/sample_jobs.json'; config_path = 'config/env.yaml'; triggered_by = 'codex'; run_mode = 'run_all' } | ConvertTo-Json
Invoke-RestMethod -Method Post -Uri "http://localhost:8000/runs" -ContentType "application/json" -Body $body
Invoke-RestMethod -Method Get -Uri "http://localhost:8000/runs/<run_id>"
```

- Verification evidence links:
  - succeeded post-fix runs (in evidence bundle):
    - `449820b5-0382-4dba-b8c8-a9f72ed75088`
    - `35cc209e-686c-4f86-861c-68dbcd75f0fe`
    - `7b5f3ce3-f1bf-4c90-a08f-628c9c04f388`

## Risk And Disposition

- Residual risk: disk I/O error may still occur at low rate on this Docker Desktop + Windows bind mount; retry reduces impact but does not prove root cause eliminated.
- Disposition decision: `mitigated` (evidence: 3/3 post-fix runs succeeded).
- Follow-ups:
  - if errors recur: move sqlite to named volume (container filesystem) or switch to postgres for control-plane persistence
  - add metric counter for sqlite OperationalError by callsite to quantify residual rate

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented (live-run/runtime failure with user-impacting behavior)
- [x] evidence bundle linked and hashed
- [ ] deterministic repro steps included (currently flaky)
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
