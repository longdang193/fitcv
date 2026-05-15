# Audit Report With Evidence

## Metadata

- Audit ID: `20260515-1015-cert-grounding-drift`
- Status: `resolved`
- Severity: `high`
- Owner: `antigravity`
- Created At: `2026-05-15T08:26:05Z`
- Updated At: `2026-05-15T09:46:00Z`
- Related Thread/Plan: `workstream-bounded-agentic-cv-quality.cross-section-placeholder-guardrails / docs/superpowers/plans/2026-05-15-11-01-fitcv-section-policy-algebra-plan.md`

## Scope

- Environment: `windows/python`
- Commit/Branch: `feature/fix-sqlite-shared-state @ e6694302608a2aa68e432de337c4757cf3a59c29`
- Affected Surface: `src/fitcv/cv_generator.py`, `src/fitcv/validator.py`, `src/fitcv/pipeline.py`, `src/fitcv/section_policy.py`, `tests/test_cv_generator.py`, `tests/test_validator.py`, `tests/test_pipeline_agentic_late_stage.py`

## Findings

### Finding `1`: `Certification section policy drift caused structural CV rejection`

- Classification: `data-quality`
- Impact: `FitCV control-plane runs rejected generated CVs with zero accepted outputs for affected jobs, despite real candidate certification data being present.`
- Expected Behavior: `Generator and validator should apply symmetric section policy: when Certifications has meaningful profile content and section is enabled, generator should receive enough grounding context to emit section and validator should require same section; when content is absent or placeholder-only, both sides should jointly treat section as optional.`
- Actual Behavior: `Validator repeatedly rejected CVs with missing_sections=["Certifications"], while telemetry showed no grounding, semantic, skill, or markdown-quality blockers. This exposed drift between requirement gating and grounding availability.`

## Evidence

For each finding, include links to raw artifacts:

- Logs/Text: `evidence/run_89577d8a_validation_excerpt.txt`
- Logs/Text: `evidence/run_f840d981_validation_excerpt.txt`

Each evidence item should include:

- `run_89577d8a_validation_excerpt.txt`
  - capture timestamp: `2026-05-15T10:26:05+02:00`
  - producing command/tool: `Get-Content -Tail 20`
  - checksum (sha256) from `manifest.yaml`: `908836d132da450debff04bcc416c00171a1537e4fff6495214c30b102108e50`
- `run_f840d981_validation_excerpt.txt`
  - capture timestamp: `2026-05-15T10:26:05+02:00`
  - producing command/tool: `Get-Content -Tail 20`
  - checksum (sha256) from `manifest.yaml`: `02bc16d47ed0ead4528d5650da62132b7a0bb95d5dae9d546016774aa835ae57`

## Reproduction

- Preconditions:
  - `Windows workspace with JOB-PROJECT repo`
  - `Branch feature/fix-sqlite-shared-state checked out`
  - `data/candidate_profile.private.yaml` contains real certification rows
- Steps:
  1. `Run FitCV pipeline for job set containing YouLend posting.`
  2. `Inspect event history jsonl for layer4_cv_validation_failed events.`
  3. `Confirm output_snapshot.missing_sections contains Certifications.`
  4. `Confirm grounding and markdown blocker arrays are empty.`
- Commands:

```powershell
Get-Content -Path "data/fitcv_cp_event_history/89577d8a-50b0-4264-a9ca-14fca40333e8.jsonl" -Tail 20
Get-Content -Path "data/fitcv_cp_event_history/f840d981-4872-4698-83ef-99facb23c74b.jsonl" -Tail 20
```

- Determinism notes: `Failure fingerprint reproduced across separate runs with same missing section and same empty blocker arrays. Full step log stored in repro/repro_steps.txt.`

## Root Cause And Boundary

- Failure boundary: `FitCV CV-generation section-policy contract between grounding policy assembly and structural validator requirement gating`
- Root cause summary: `Certification handling drifted into asymmetric special-case logic. Validator required Certifications based on profile presence semantics, while generator could starve certification grounding when selected evidence lacked explicit certification items. This violated symmetry: similar section structures were not passing through same availability and requirement process.`

## Fix And Verification

- Fix summary: `Introduced shared Certifications policy helper (src/fitcv/section_policy.py) and moved generator + validator decisions onto same enablement/admissibility/requiredness algebra. Validator now gates structural required-sections and meaningful-content checks via shared policy decisions; generator consumes same admissible rows semantics.`
- Verification commands and outcomes:

```powershell
python -m pytest tests/test_cv_generator.py -k "certification or grounding_policy or section"   # 12 passed
python -m pytest tests/test_validator.py -k "certification or required_structured_sections or meaningful"   # 2 passed
python -m pytest tests/test_pipeline_agentic_late_stage.py -k "certification or validation_failed or review_required"   # 2 passed
python scripts/validate_repo_contracts.py --fast   # passed
python scripts/audit_check.py docs/superpowers/plans/audit/20260515-1015-cert-grounding-drift
```

- Verification evidence links:
  - `tests/test_validator.py` regression coverage confirms `missing_sections=["Certifications"]` is only emitted when shared policy marks Certifications required for meaningful rows.
  - `src/fitcv/validator.py` (`run_all_validations`) now computes effective required sections using `certification_policy_decisions(...)` before markdown-structure validation.
  - Focused late-stage and validator/generator subsets pass with no unrelated validator-family regressions.

## Risk And Disposition

- Residual risk: `Low. Certifications drift class resolved with shared policy path; broad cross-section algebra expansion remains optional future hardening, not required for this closure.`
- Disposition decision: `resolved`
- Follow-ups: `Optional: extend same shared policy algebra pattern to additional structured sections to reduce future asymmetry risk.`

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
