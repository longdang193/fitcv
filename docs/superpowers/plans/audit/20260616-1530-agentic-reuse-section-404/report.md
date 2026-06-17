# Audit Report

## Metadata

- Audit ID: `20260616-1530-agentic-reuse-section-404`
- Status: `resolved`
- Severity: `medium`
- Owner: `codex`
- Created At: `2026-06-16T15:30:00+02:00`
- Updated At: `2026-06-16T15:30:00+02:00`
- Related Thread/Plan: `none`

## Scope

- Environment: `Windows, Python 3.13.5, FastAPI control-plane settings route`
- Commit/Branch: `working tree`
- Affected Surface: `agentic settings UI -> section save route -> reuse controls`

## Findings

### Finding F1: Agentic reuse settings form posted to an unregistered section slug

- Classification: `regression`
- Impact: operator attempts to save reuse settings, including `Reuse CV Generation`, receive `404 {"detail":"Unknown section: 'agentic-reuse'"}` and cannot persist those controls.
- Expected Behavior: posting `/admin/settings/section/agentic-reuse` validates the reuse keys and redirects back to `/admin/settings`.
- Actual Behavior: the UI rendered `submit_slug="agentic-reuse"` but the backend registry omitted that slug, so the section-save route rejected the request before validation.

## Evidence

- `evidence/results/pre_fix_findings.md`
- `evidence/results/post_fix_verification.md`
- `repro/repro_steps.md`

## Reproduction

- Preconditions:
  - control-plane app wired to current `fitcv_cp` settings schema
- Steps:
  1. Open `/admin/settings`
  2. Use the Agentic Processing "Reuse" card
  3. Submit the form containing `reuse.cv_generation.enabled`
- Commands: see `repro/repro_steps.md`
- Determinism notes: deterministic because the rendered slug and backend section registry were statically inconsistent.

## Root Cause And Boundary

- Failure boundary: `fitcv_cp` settings section registry used by `/admin/settings/section/{section_name}`
- Root cause summary: `AGENTIC_REUSE_SECTION_KEYS` existed, and the UI rendered `submit_slug="agentic-reuse"`, but `AGENTIC_SETTINGS_SECTIONS` did not register `"agentic-reuse"`, so `all_settings_sections` never recognized the slug.

## Fix And Verification

- Fix summary: register `"agentic-reuse"` in `AGENTIC_SETTINGS_SECTIONS` and add tests covering the schema slug list, section ownership, route save, and rendered form action.
- Verification commands:
  - `python -m pytest tests/test_fitcv_cp/test_settings_schema.py -k "agentic_settings_sections or agentic_settings_section_ownership"`
  - `python -m pytest tests/test_fitcv_cp/test_app.py -k "agentic_reuse_valid_redirects or late_stage_stage_runtime_controls_in_agentic_section"`
  - `.\.venv\Scripts\python.exe scripts\audit_check.py docs/superpowers/plans/audit/20260616-1530-agentic-reuse-section-404`
- Verification evidence links:
  - `evidence/results/post_fix_verification.md`

## Risk And Disposition

- Residual risk: low; this fix only expands the accepted section registry to match an already-rendered UI form.
- Disposition decision: `resolved`
- Follow-ups: keep adding a route test whenever a new section slug is introduced.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] verification evidence attached
- [x] final status recorded
