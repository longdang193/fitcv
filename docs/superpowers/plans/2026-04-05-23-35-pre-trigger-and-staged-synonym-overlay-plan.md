# Pre-Trigger And Staged Synonym Overlay Plan

Status: completed

## Tasks

1. Add trigger-time synonym overlay input to the runs page.
Status: completed
Notes:
- Add a `Synonym Overlay` block beside Jobs Input and Candidate Profile.
- Support `Default Config` and `Upload YAML` in the trigger form for both `run_all` and `manual_staged`.
- Keep the trigger page copy explicit that staged runs can later replace the overlay after `enrich`.

2. Persist trigger-time run-scoped synonym overlay snapshots.
Status: completed
Notes:
- Store the uploaded overlay as run-owned input at trigger time.
- Reuse the existing synonym-overlay validation contract so trigger-time and staged uploads stay aligned.
- Keep the base shared synonym config unchanged.

3. Preserve staged override upload after `enrich` and before `rule_filter`.
Status: completed
Notes:
- Keep the staged-only upload path for `manual_staged` runs paused at `awaiting_continue`.
- Reclassify this as a run-scoped override rather than the only entry point.
- Ensure the staged upload replaces the currently active run-owned overlay for the rest of the run.

4. Unify runtime synonym-overlay resolution and precedence.
Status: completed
Notes:
- Make the effective synonym map deterministic:
  - base/default config
  - plus trigger-time run overlay
  - plus staged override when present
- Ensure all downstream synonym-aware stages consume the same effective map for the run.

5. Move synonym-overlay inspection and staged upload into a dedicated run-detail card.
Status: completed
Notes:
- Remove the file picker from the crowded top action row.
- Add a `Synonym Overlay` card that shows:
  - source/status
  - filename
  - uploaded time
  - entry count
- For staged paused runs at `enrich -> rule_filter`, expose the replacement upload there.

6. Keep `run_all` mode constrained to trigger-time upload only.
Status: completed
Notes:
- Do not add any mid-run upload path for `run_all`.
- Make this constraint explicit in the UI and run detail messaging.

7. Add focused regression coverage and sync docs.
Status: completed
Notes:
- Add tests for:
  - trigger form rendering and submission with synonym overlay
  - staged override behavior
  - run-detail synonym-overlay card rendering
  - deterministic runtime precedence
- Update:
  - `docs/features/trigger_run_management/trigger_run_management.yaml`
  - `docs/features/trigger_run_management/history.md`
  - any stage/cross-cutting docs touched by the new trigger-time overlay lifecycle

## Verification

- Focused control-plane tests for trigger form handling, run detail rendering, and staged override lifecycle
- Focused runtime tests for synonym-overlay precedence and snapshot loading
- `py_compile` on touched Python modules
