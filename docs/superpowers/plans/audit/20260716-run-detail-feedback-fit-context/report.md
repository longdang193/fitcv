# Audit Report With Evidence

## Metadata

- Audit ID: `20260716-run-detail-feedback-fit-context`
- Status: `resolved`
- Severity: `medium`
- Owner: `Codex`
- Created At: `2026-07-16T16:00:00+02:00`
- Updated At: `2026-07-16T16:54:20.8203594+02:00`
- Related Thread/Plan: current run-detail rating and fit-context repair

## Scope

- Environment: `Windows 11, PowerShell, Python 3.13.5, uv 0.10.8, SQLite, Docker 28.5.1`
- Commit/Branch: `98a921353fcf41166ec37e7cb44179cb5fee9978 on codex/phase-6-inverse-optimization with uncommitted repair`
- Affected Surface: `run detail enriched tab, decision-feedback POST redirect, run_structured_jobs snapshot projection`

## Findings

### Finding `F1`: rating POST redirected to fragment-only HTML

- Classification: `regression`
- Impact: user returned to an unstyled partial table after rating a job.
- Expected Behavior: browser returns to full run-detail page with Enriched Jobs pane selected.
- Actual Behavior: redirect targeted `/admin/runs/{run_id}/tabs/enriched`, which is an HTML fragment endpoint.

### Finding `F2`: Fit Context mislabeled work mode as location

- Classification: `data-quality`
- Impact: users saw `hybrid` or `onsite` under Location while real city/country remained hidden.
- Expected Behavior: Location displays canonical actual location, Work Mode displays `location_type`.
- Actual Behavior: template rendered `job.location_type` under Location.

### Finding `F3`: location and language evidence was dropped or hidden

- Classification: `data-quality`
- Impact: future run snapshots lost `actual_location` and `language_requirements`; current run could not surface language factor evidence.
- Expected Behavior: run snapshot preserves canonical fields; UI uses canonical values and honest fallback evidence.
- Actual Behavior: `_RUN_SCHEMA_FIELDS` omitted both canonical fields and template rendered neither language nor expected level state.

### Finding `F4`: Fit Context fields rendered inline

- Classification: `spec-mismatch`
- Impact: labels and values formed one dense line, reducing scanability.
- Expected Behavior: each field occupies its own line.
- Actual Behavior: `.fit-context-stack` had no vertical layout rule.

## Evidence

- Screenshot: `evidence/images/post-rating-fragment.png`
- Screenshot: `evidence/images/run-detail-fit-context-before.png`
- Focused regression output: `evidence/results/focused-tests.txt`
- Full verification summary: `evidence/results/verification.txt`
- Raw verification output: `evidence/results/verification-raw.txt`
- Post-fix screenshot: `evidence/images/run-detail-fit-context-after.png`
- Live verification output: `evidence/results/live-verification.txt`
- Checksums: `manifest.yaml`

## Reproduction

- Preconditions: run `1690f50c-bb0a-465a-8460-b2f5fb28f06a` available in local control-plane database.
- Steps and exact commands: `repro/repro_steps.md`.
- Determinism notes: unit regressions use fixed fixtures; live proof uses named immutable run.

## Root Cause And Boundary

- Failure boundary: server-rendered run-detail boundary plus run-scoped enriched snapshot projection.
- Root cause summary: POST used fragment route as navigation target; template conflated `location_type` with location; snapshot allowlist omitted canonical location/language fields; layout lacked column styling.

## Fix And Verification

- Fix summary: redirect to full run page anchor; preserve canonical fields; render Location, Work Mode, Language, Seniority, Family, and Domain vertically; use filter-factor language evidence only when canonical language requirements are absent.
- Verification commands: listed in `repro/repro_steps.md`.
- Verification evidence links: `evidence/results/focused-tests.txt`, `evidence/results/verification.txt`, `evidence/results/live-verification.txt`.

## Risk And Disposition

- Residual risk: current run lacks extracted expected language level, so UI must state `level unspecified`; future runs preserve extracted levels such as B2.
- Disposition decision: `resolved`.
- Follow-ups: pre-existing broad Ruff debt remains outside this repair; no stale BM25 or `preference_fit` label exists in run-detail templates.

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
