# Run All vs Stage by Stage Contract Alignment Plan

Status: completed

## Tasks

1. Introduce explicit progress-state persistence separate from manual checkpoint state.
Status: completed
Notes:
- Define the minimal progress facts that both modes must persist:
  - `last_completed_stage`
  - `completed_stages`
  - stage-reached artifact availability
- Keep manual checkpoint payloads and resumability metadata exclusive to `manual_staged`.
- Ensure the data model distinguishes:
  - progress state
  - checkpoint state
  rather than overloading checkpoint fields for both concerns.

2. Persist stage-boundary progress snapshots for `Run All`.
Status: completed
Notes:
- Add stage-boundary persistence for `run_all` after each reached stage without pausing execution.
- Persist stage-transition artifacts for reached stages during `run_all`, not only on final success.
- Preserve the current staged pause behavior unchanged for `manual_staged`.
- Make sure `run_all` progress writes do not imply resumability or `awaiting_continue`.

3. Align stage-owned artifact availability across both modes.
Status: completed
Notes:
- Update artifact gating so stage-owned downloads depend on reached-stage/progress state, not staged pause semantics.
- Ensure a `Run All` run that has reached `normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, or `cv_analysis` exposes the same stage-owned downloads as a staged run that has reached the same stage.
- Preserve staged-only checkpoint artifacts as staged-only.

4. Normalize run-mode terminology across trigger, list, detail, and timeline surfaces.
Status: completed
Notes:
- Replace operator-facing `Auto` / `Automatic` / `Manual` / `Manual staged` drift with canonical labels:
  - `Run All`
  - `Stage by Stage`
- Keep any short subtitle or helper copy consistent with the spec:
  - `continuous`
  - `manual pause between stages`
- Update tests that currently assert older mode strings.

5. Make timeout semantics mode-aware in UI and contract handling.
Status: completed
Notes:
- Preserve the current runtime timeout guard for active queue/runtime states.
- Reclassify `awaiting_continue` timeout as manual-wait timeout in UI/helper copy and diagnostics.
- Ensure control-plane status text makes clear when a timeout is acting on operator wait time instead of active pipeline execution.
- Update feature docs in `run_lifecycle_controls` and `trigger_run_management` to reflect this distinction.

6. Keep staged-only synonym override as an explicit, narrow exception.
Status: completed
Notes:
- Preserve trigger-time run-scoped synonym overlay upload for both modes.
- Preserve post-`enrich` replacement only for staged runs.
- Tighten UI/helper text so operators understand this is the only intentional post-trigger capability difference between the modes.
- Avoid broadening scope to add any mid-run override to `run_all` in this plan.

7. Align run-detail and runs-list rendering with the new shared mode contract.
Status: completed
Notes:
- Use progress-state facts to render stage reachability for both modes.
- Keep `next: <stage>` and `Run Next Stage` only for paused staged runs.
- Ensure run detail can show:
  - execution mode
  - progress state
  - staged-only continuation affordances
  - timeout context
- Keep timeline/manual checkpoint rows distinct from aggregate stage-complete rows.

8. Add focused regression coverage for both modes.
Status: completed
Notes:
- Add worker/control-plane tests proving `run_all` now persists stage progress and stage-owned artifacts incrementally.
- Add tests proving `manual_staged` still persists checkpoint payloads and `awaiting_continue` semantics exactly as before.
- Add UI tests proving runs list and run detail use canonical `Run All` / `Stage by Stage` labels.
- Add tests proving stage-owned artifact availability is symmetric for equal reached stages across both modes.
- Add tests proving `run_all` never exposes staged-only `continue` or staged-only synonym replacement controls.

9. Sync source-of-truth docs and generated discovery.
Status: completed
Notes:
- Update:
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/trigger_run_management/history.md`
  - `docs/features/inspection_debugging/inspection_debugging.yaml`
  - `docs/features/inspection_debugging/history.md`
  - `docs/features/run_lifecycle_controls/run_lifecycle_controls.yaml`
  - `docs/features/run_lifecycle_controls/history.md`
- Update any cross-cutting helper text in:
  - `docs/fitcv-control-plane-setup.md`
- Refresh:
  - `docs/generated/features_index.yaml`
  - `docs/generated/feature_overview.md`

## Verification

- Focused control-plane tests in:
  - `tests/test_fitcv_cp/test_app.py`
  - `tests/test_fitcv_cp/test_worker_job.py`
- Any needed orchestration coverage in:
  - `tests/test_pipeline.py`
- Manual sanity checks for:
  - one `Run All` run stopped/failing after an intermediate reached stage
  - one `Run All` run reaching `enrich` and later stages without pause
  - one `Stage by Stage` run pausing after `normalize`, `enrich`, and `cv_analysis`
- UI sanity checks that:
  - runs list uses only `Run All` / `Stage by Stage`
  - run detail shows shared stage progress for both modes
  - staged-only controls remain staged-only
  - artifact availability is symmetric for equal reached stages
- `py_compile` on touched Python modules
