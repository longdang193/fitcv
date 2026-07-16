# Audit Report With Evidence

## Metadata

- Audit ID: `20260716-1413-phase7-live-run-master-spec`
- Status: `resolved`
- Severity: `medium`
- Owner: `Codex`
- Created At: `2026-07-16T14:13:46.6930988+02:00`
- Updated At: `2026-07-16T15:11:00.9810646+02:00`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-16-11-29-fitcv-inverse-optimization-phase-7-policy-lifecycle-runtime-residual-closeout-plan.md`

## Scope

- Environment: `Windows 11, PowerShell, Python 3.13.5 via uv, SQLite, CVXPY 1.9.2, CLARABEL 0.11.1`
- Commit/Branch: `98a921353fcf41166ec37e7cb44179cb5fee9978 on codex/phase-6-inverse-optimization with uncommitted Phase 7 blocker closeout`
- Affected Surface: `inverse-optimization Phases 1-7, ranking artifacts/export, lifecycle CLI, SQLite policy state, live pipeline replay`

## Findings

### Finding `F1`: row-level personalization evidence was dropped at artifact/export boundaries

- Classification: `data-quality`
- Impact: active learned policy affected scores, but persisted ranking samples and export rows did not preserve personalized rank, residual, score, clipping, or policy identity.
- Expected Behavior: old runs retain baseline and personalized score evidence plus exact policy identity.
- Actual Behavior: pre-fix run `612f221c-c16b-4b1e-a0f3-ac012caa57e9` had active residual summary but omitted row-level fields.
- Disposition: `resolved` by projecting existing ranking fields through `ranking_row_sample(...)` and `_build_export_results(...)`.

### Finding `F2`: rollback compare-and-swap conflict returned invalid-input exit semantics

- Classification: `spec-mismatch`
- Impact: automation could not distinguish operator input errors from lifecycle contention.
- Expected Behavior: `status=conflict`, `error_code=active_snapshot_changed`, exit code `4`.
- Actual Behavior: `status=invalid_input`, `ValueError:active snapshot changed`, exit code `2`.
- Disposition: `resolved` through typed CLI lifecycle error mapping.

### Finding `F3`: activation ignored evidence-head compare-and-swap token

- Classification: `spec-mismatch`
- Impact: candidate could activate after rating evidence changed, contrary to immutable-evidence lifecycle contract.
- Expected Behavior: candidate becomes `stale`, append-only event records `evidence_changed`, no active snapshot is created.
- Actual Behavior: supplied evidence-head fingerprint was recorded but not compared.
- Disposition: `resolved` with transactional comparison against candidate training provenance and focused regression coverage.

### Finding `F4`: current config/runtime provenance is not rechecked at activation

- Classification: `spec-mismatch`
- Impact: candidate may become active for its old runtime contract after baseline, ranking, embedding, optimizer, activation, or decision-learning config changes. Current runtime resolver remains compatibility-safe, but lifecycle state does not satisfy master-spec staleness semantics.
- Expected Behavior: activation transaction compares current config/runtime tokens and marks candidate stale on any bound provenance change.
- Actual Behavior: activation checks parent, evidence head, current runtime contract, compiler, activation, optimizer, and decision-learning fingerprints inside one `BEGIN IMMEDIATE` transaction.
- Disposition: `resolved`; every provenance mismatch marks the candidate stale, appends one typed event, commits, and returns typed CLI exit code `4`.

### Finding `F5`: live scenario did not exercise all admissible location/language cases

- Classification: `other`
- Impact: live evidence proves ranking-only location/language projection, but not city discrimination or hard-gate behavior.
- Expected Behavior: live or bounded scenario evidence covers ranking-only and hard-gate normalization behavior.
- Actual Behavior: bounded mutation-safe scenario now uses preferred cities Berlin and Magdeburg, rejects confirmed language failure before ranking, retains unknown with diagnostics, removes hard-gated language from effective ranking weights, renormalizes remaining weights to `1.0`, and preserves baseline-derived `strong|stretch|skip` labels.
- Disposition: `resolved`; evidence is recorded in `evidence/results/hard-gate-summary.json` and reproduced by `repro/run_hard_gate_scenario.ps1`.

### Finding `F6`: completed Phase 7 plan overstated lifecycle proof

- Classification: `spec-mismatch`
- Impact: completion metadata claimed stale, concurrent activation, failed-transaction, and rollback proofs, but scoped source search found no dedicated concurrency/stale-config tests; one documented `-k` proof command selected zero tests.
- Expected Behavior: each completion claim cites a runnable test that selects and executes intended cases.
- Actual Behavior: dedicated current-provenance, two-thread sibling activation, injected event failure, exact learned rollback, zero-residual rollback, and typed CLI tests now execute under named filters.
- Disposition: `resolved`; plan verification commands and completion metadata now cite runnable proof.

## Evidence

- Result JSON: `evidence/results/live-run-summary.json`
- Result JSON: `evidence/results/findings.json`
- Logs/Text: `evidence/results/verification.txt`
- Reproduction: `repro/repro_steps.md`
- Source live artifacts:
  - `artifacts/live_audit_inverse_optimization_20260716/postfix-personalization-summary.json`
  - `artifacts/live_audit_inverse_optimization_20260716/rollback-conflict-fixed.json`
  - `artifacts/live_audit_inverse_optimization_20260716/fitcv.sqlite3`
  - `artifacts/live_run_ee9f783a-e606-482f-9a97-2172f2f9a81d/`
- Capture timestamp, producer, and checksums are recorded in `manifest.yaml`.

## Reproduction

- Preconditions:
  - isolated SQLite through `FITCV_CP_SQLITE_PATH`
  - synonym promotion disabled for mutation-safe verification
  - local OpenAI-compatible router available at configured endpoint
- Steps:
  1. Run baseline pipeline with no active learned policy.
  2. Submit two 1-5-star decision episodes through admin POST endpoint.
  3. Build candidate, evaluate, activate, and run personalized pipeline.
  4. Inspect ranking stage artifact, export, SQLite lifecycle tables, and CLI exit behavior.
  5. Run focused and broad regression/static/contract checks.
- Commands: see `repro/repro_steps.md`.
- Determinism notes: candidate IDs, payload fingerprints, training IDs, policy IDs, edge order, and CLI JSON are content-addressed; provider stages used persisted reuse where available.

## Root Cause And Boundary

- Failure boundary: artifact/export adapters, CLI exception adapter, SQLite activation transaction, and completion-evidence reconciliation.
- Root cause summary: Phase 7 core ranking and lifecycle work existed, but boundary projections and lifecycle proof were not reconciled against master acceptance criteria. Activation accepted a token it did not validate, while plan checkboxes were marked complete without matching runnable tests.

## Fix And Verification

- Fix summary:
  - preserve personalized row evidence in stage artifact and export
  - map lifecycle conflicts/staleness to typed CLI statuses
  - compare activation evidence head against persisted candidate provenance
  - compare all current runtime/config provenance inside activation transaction
  - prove one activation winner, atomic event rollback, and exact learned rollback
  - exercise preferred-city ranking plus language hard-gate normalization
  - refresh stale decision-feedback test fixtures
  - correct one ranking typing defect found by isolated mypy
- Verification commands:

```powershell
uv run --extra inverse-optimization python -m pytest tests/test_config.py tests/test_preference_policy.py tests/test_inverse_optimization.py -q
uv run python -m pytest tests/test_ranking.py tests/test_ranking_contract.py tests/test_ai_score.py -q
uv run python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
uv run python -m pytest tests/test_decision_feedback.py -q
uv run python -m pytest tests/test_fitcv_cp/test_app.py -q
uv run python -m pytest tests/test_fitcv_cp/test_sqlite_store.py -q
uv run python -m pytest tests/test_fitcv_cp/test_sqlite_store.py -q -k "concurrent_sibling_activation or activation_event_failure or current_provenance_changed or rollback_restores_exact or evidence_head_changed"
uv run python -m pytest tests/test_inverse_optimization.py -q -k "activation_provenance or rollback_cas_conflict or current_activation_provenance"
& repro/run_hard_gate_scenario.ps1 -OutputPath evidence/results/hard-gate-summary.json
ruff check src/fitcv/preference_policy.py src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py src/fitcv/ranking.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py scripts/run_inverse_optimization.py tests/test_preference_policy.py tests/test_inverse_optimization.py tests/test_decision_feedback.py
mypy src/fitcv/preference_policy.py src/fitcv/decision_feedback.py src/fitcv/inverse_optimization.py src/fitcv/ranking.py src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py scripts/run_inverse_optimization.py --show-error-codes --follow-imports=skip
uv run python tools/docs/generate_architecture_metadata.py --check
uv run python scripts/validate_planning_lifecycle.py
uv run python scripts/validate_repo_contracts.py
git diff --check
```

- Verification evidence links:
  - `evidence/results/verification.txt`
  - `evidence/results/live-run-summary.json`
  - `evidence/results/hard-gate-summary.json`

## Risk And Disposition

- Residual risk: none within Phase 7 scope; future policy schema versions must add their canonical fingerprint to the same activation comparison set.
- Disposition decision: `resolved`
- Follow-ups: none required for Phase 7 closure.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented (or explicit bypass)
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
