# Checkpoint Result Pack

## Metadata

- Checkpoint ID: `workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-policy-versioned-stage-result-envelope.20260503-0808`
- Workstream ID: `workstream-deterministic-acceptance-and-artifact-truth`
- Thread ID: `workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-policy-versioned-stage-result-envelope`
- Thread file: `docs/intent/workstreams/threads/workstream-deterministic-acceptance-and-artifact-truth/05-deterministic-truth-policy-versioned-stage-result-envelope.md`
- Timestamp (UTC): `2026-05-03T08:08:25Z`
- Owner: `codex`

## Intent

Close Plan G replay-mode and policy-provenance runtime behavior.

## Actions

- added strict vs policy_replay mode handling on manual continue route
- added strict policy-envelope drift rejection and policy_replay bypass behavior
- persisted replay context (`replay_mode`, `replay_source_run_id`, `policy_registry_version`, `policy_envelope_signature`) in checkpoint, settings-used, and results-export artifacts
- added run-detail replay metadata surface and tests

## Visible Output

- Artifacts:
  - `src/fitcv_cp/app.py`
  - `src/fitcv_cp/worker_job.py`
  - `src/fitcv_cp/templates/run_detail.html`
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Verification output:
  - `python -m pytest tests/test_fitcv_cp/test_app.py -q` passed
  - `python -m pytest tests/test_fitcv_cp/test_worker_job.py -q` passed
- Diff summary:
  - replay mode contract and policy provenance are now explicit and operator-visible

## Status

`pass`

## Next Decision

`continue`
