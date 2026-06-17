# Audit Report

## Metadata

- Audit ID: `20260617-1043-enrich-required-skills-sparsity`
- Status: `resolved`
- Severity: `medium`
- Owner: `codex`
- Created At: `2026-06-17T10:43:07.1008220+02:00`
- Updated At: `2026-06-17T10:43:07.1008220+02:00`
- Related Thread/Plan: `none`

## Scope

- Environment: `Windows, Python 3.13.5, sqlite-backed FitCV enrich pipeline`
- Commit/Branch: `working tree`
- Affected Surface: `shared enrich contract -> required_skills repair -> reusable structured enrichment cache`

## Findings

### Finding F1: Sparse enrich outputs kept under-specified required skills despite richer structured evidence

- Classification: `data-quality`
- Impact: enriched jobs could render with only one broad required-skill phrase even when the same row already contained richer atomic tools in `tech_stack`, reducing ranking signal quality and making the UI appear inconsistent.
- Expected Behavior: the shared enrich contract should preserve non-empty `required_skills`, but when that list is clearly sparse and richer structured skill evidence already exists in the same payload, the row should be repaired centrally so fresh and reused rows expose the same stronger required-skill signal.
- Actual Behavior: `_repair_required_skill_signal` only backfilled when `required_skills` was fully empty. Rows such as `["Excel/Sheets"]` plus `tech_stack=["Excel", "Sheets", "SQL", "BI-Tools"]` stayed sparse forever, including after cache reuse.

## Evidence

- `evidence/results/pre_fix_findings.md`
- `evidence/results/post_fix_verification.md`
- `repro/repro_steps.md`

## Reproduction

- Preconditions:
  - repo checkout at current working tree
  - pytest available in environment
- Steps:
  1. Run the targeted enrich regression test before the patch.
  2. Observe that `merge_scraped_and_enriched(...)` keeps only the thin `required_skills` value.
  3. Apply the shared repair change and rerun the enrich suite.
- Commands: see `repro/repro_steps.md`
- Determinism notes: deterministic because the failing case is a fixed unit-test fixture with a single sparse `required_skills` phrase and richer `tech_stack` values.

## Root Cause And Boundary

- Failure boundary: `src/fitcv/enrich.py` shared repair contract used by fresh merge output and reusable cached enrichment rows
- Root cause summary: the SSOT repair boundary treated only fully empty `required_skills` as repairable, so sparse-but-incomplete rows bypassed repair and their canonical companion fields stayed aligned to the weak source value instead of the richer structured signal already present in the same payload.

## Fix And Verification

- Fix summary: add a bounded sparse-signal supplement step that promotes missing atomic entries from `tech_stack` into `required_skills` when the list is below the sparsity threshold, and recompute canonical companions when the repair changes the row.
- Verification commands:
  - `pytest tests/test_enrich.py -k "supplements_sparse_required_skills_from_tech_stack"`
  - `pytest tests/test_enrich.py`
  - `python scripts/hooks/run_validator.py --fast`
  - `python scripts/audit_check.py docs/superpowers/plans/audit/20260617-1043-enrich-required-skills-sparsity`
- Verification evidence links:
  - `evidence/results/post_fix_verification.md`

## Risk And Disposition

- Residual risk: low; this only supplements sparse rows from already-extracted `tech_stack`, and only within the shared enrichment repair boundary.
- Disposition decision: `resolved`
- Follow-ups: consider future prompt/schema tuning if we want more atomic `required_skills` directly from the model, but keep repair logic centralized in `fitcv.enrich`.

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
