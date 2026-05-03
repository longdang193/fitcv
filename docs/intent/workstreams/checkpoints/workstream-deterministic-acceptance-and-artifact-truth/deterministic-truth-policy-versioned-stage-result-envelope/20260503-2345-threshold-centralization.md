# Checkpoint Result Pack

- Workstream ID: `workstream-deterministic-acceptance-and-artifact-truth`
- Thread Slug: `deterministic-truth-policy-versioned-stage-result-envelope`
- Checkpoint ID: `workstream-deterministic-acceptance-and-artifact-truth.deterministic-truth-policy-versioned-stage-result-envelope.20260503-2345-threshold-centralization`
- Execution pass timestamp (UTC): `2026-05-03T23:45:00Z`

## Intent

Centralize outbox replay alert threshold defaults into one config source and enforce CLI override precedence in checker/wrapper tooling.

## Actions

- Added default policy threshold in `config/runtime/pipeline.yaml`:
  - `outbox_replay_health.min_replay_success_ratio: 0.95`
- Updated `scripts/check_outbox_replay_health.py`:
  - reads default threshold from config via `load_config`
  - preserves CLI override precedence (`--min-replay-success-ratio`)
  - adds `--config-path` support
- Updated `scripts/route_outbox_replay_health_alert.py`:
  - forwards `--config-path` and optional threshold override to checker
- Updated `src/fitcv_cp/app.py`:
  - `/admin/outbox-replay-health/check` now resolves default threshold from config when query param is omitted
- Added/extended tests:
  - `tests/test_check_outbox_replay_health.py` (config default + CLI override precedence)
  - `tests/test_route_outbox_replay_health_alert.py` (wrapper argument propagation)
  - `tests/test_fitcv_cp/test_app.py` (endpoint config-default threshold behavior)
- Updated phase-2 closeout matrix evidence for Plan G partial progression.

## Visible Output

- `config/runtime/pipeline.yaml`
- `scripts/check_outbox_replay_health.py`
- `scripts/route_outbox_replay_health_alert.py`
- `src/fitcv_cp/app.py`
- `tests/test_check_outbox_replay_health.py`
- `tests/test_route_outbox_replay_health_alert.py`
- `tests/test_fitcv_cp/test_app.py`
- `docs/superpowers/plans/2026-05-03-phase-2-master-closeout-matrix.md`
- `docs/intent/workstreams/checkpoints/workstream-deterministic-acceptance-and-artifact-truth/deterministic-truth-policy-versioned-stage-result-envelope/20260503-2345-threshold-centralization.md`

## Verification Evidence

- `python -m pytest tests/test_check_outbox_replay_health.py tests/test_route_outbox_replay_health_alert.py` → `5 passed`
- `python -m pytest tests/test_fitcv_cp/test_app.py -k "outbox_replay_health_check"` → `3 passed`
- `python scripts/validate_checkpoint_packs.py` → pass
- `python scripts/validate_repo_contracts.py --fast` → pass

## Status

`pass`

## Next Decision

Proceed to explicit Phase-2 completion gate artifact and plan-level closure resolution (`done|waived`) for remaining partial plans.
