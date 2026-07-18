# Semantic Snapshot SSOT Live Verification Audit

## Metadata

- Audit ID: `20260717-semantic-snapshot-ssot-live-verification`
- Status: `resolved`
- Severity: `high`
- Owner: `FitCV maintainers`
- Created At: `2026-07-17`
- Updated At: `2026-07-18`
- Related Thread/Plan: `docs/superpowers/plans/2026-07-17-22-05-fitcv-semantic-snapshot-ssot-plan.md`

## Scope

- Environment: Windows source-mode control plane, Python 3.13, fresh SQLite databases
- Commit/Branch: working tree on `codex/phase-6-inverse-optimization`
- Affected Surface: enrich persistence, semantic consumer authority, stage reuse fingerprints, lifecycle parity
- Failing Evidence Root: `artifacts/live_run_semantic_snapshot_ssot_20260717-3c255cb2`
- Resolution Evidence Root: `artifacts/live_run_semantic_snapshot_ssot_fixed_20260718-022717`
- Governing Date: Saturday, July 18, 2026

## Findings

### Finding F1: Semantic snapshots disappeared before persistence

- Classification: `spec-mismatch`
- Original Impact: Cached, resumed, and downstream stages could not use `SemanticSnapshot` as runtime SSOT.
- Original Evidence: All 13 `run_structured_jobs` payloads and exported stage artifacts contained zero `semantic_snapshot` objects.
- Resolution: Run-scoped structured jobs now preserve `semantic_snapshot`; stage artifact export preserves the same object.
- Verification: Resolution baseline persisted 13 of 13 snapshots and exported 68 snapshot occurrences.

### Finding F2: Semantic fingerprint reuse law was absent from live artifacts

- Classification: `spec-mismatch`
- Original Impact: Canonical-value versus alias-equivalence invalidation could not be proven uniformly.
- Original Evidence: Live artifacts contained zero `semantic_value_fingerprint` and zero `semantic_derivation_fingerprint` occurrences.
- Resolution: Persisted and exported snapshots now carry canonical value and derivation identity; exact CV-analysis input identity also includes bounded alias equivalence consumed by that stage.
- Verification: Resolution artifacts contain 68 semantic value fingerprints and 68 semantic derivation fingerprints.

### Finding F3: Multiple runtime semantic authorities remained

- Classification: `spec-mismatch`
- Original Impact: Equivalent cases could resolve through different normalization and alias-expansion paths.
- Original Evidence: Enrich, rule filter, ranking, and gap analysis retained direct semantic-map reads or duplicate traversal helpers.
- Resolution: Data-plane consumers derive semantic facts from `semantic_snapshot.py`; raw map access remains only in configuration, snapshot construction, and explicit control-plane administration.
- Verification: `evidence/results/ssot-source-scan-fixed.txt` reports no direct raw-map authority in audited runtime consumers.

### Finding F4: Required reuse scenarios were unverified

- Classification: `spec-mismatch`
- Original Impact: Unrelated mapping reuse, canonical-target refresh, and alias-equivalence-only refresh lacked live proof.
- Original Evidence: Only one baseline run completed, and missing persisted snapshot identity prevented scenario comparison.
- Resolution: Baseline plus three overlay scenarios now prove bounded symmetric invalidation.
- Verification:
  - Unrelated `C:D`: 13 enrich cache hits, 4 AI exact reuses, 1 CV-analysis exact reuse.
  - Relevant target change `sql:sql ssot changed`: 13 enrich cache hits, 5 semantic values changed, 1 AI fresh compute, 1 CV-analysis fresh compute.
  - Relevant alias add `sql snapshot alias:sql`: 13 enrich cache hits, 0 semantic values changed, 4 AI exact reuses, 1 CV-analysis fresh compute.

## Evidence

- Pre-fix:
  - `evidence/results/semantic-verification-summary.json`
  - `evidence/results/live-run-result.txt`
  - `evidence/results/ssot-source-scan.txt`
- Post-fix:
  - `evidence/results/semantic-verification-summary-fixed.json`
  - `evidence/results/reuse-scenario-summary.json`
  - `evidence/results/live-run-result-fixed.txt`
  - `evidence/results/ssot-source-scan-fixed.txt`
  - `evidence/results/verification-results.txt`
- Reproduction: `repro/repro_steps.md`

Checksums are recorded in `manifest.yaml`.

## Reproduction

See `repro/repro_steps.md` for baseline and three overlay scenarios.

## Root Cause And Boundary

- Persistence boundary: `merge_scraped_and_enriched()` created the snapshot, but a downstream structured-job projection omitted it.
- Artifact boundary: Stage serialization exported compatibility fields without the canonical snapshot.
- Consumer boundary: Multiple stages read raw maps or rebuilt semantic variants independently.
- Reuse boundary: Canonical semantic value identity alone did not represent alias-sensitive input consumed by CV gap analysis.

## Fix And Verification

- Fix summary:
  - Preserve `semantic_snapshot` through structured-job persistence, cache reconstruction, and stage artifacts.
  - Route enrich, rule filter, ranking, and gap analysis through the semantic snapshot authority.
  - Make alias-equivalence projection symmetric across skill, domain, and role-family fields.
  - Add bounded alias-equivalence identity to CV-analysis input fingerprints, leaving unrelated mappings invisible.
  - Add persistence, source-boundary, symmetry-matrix, mapping-law, and stage-fingerprint regressions.
- Verification results:
  - Focused Semantic Snapshot suite: 705 passed, 3 skipped.
  - Affected post-fix suite: 209 passed.
  - Inverse optimization suite in repo virtual environment: 36 passed.
  - Full repo suite in repo virtual environment: 2274 passed, 3 skipped, 1 documented unrelated baseline failure.
  - Compile, planning lifecycle, template sections, architecture metadata, fast repo contracts, fast hook validator, and targeted plan YAML checks passed.
  - Baseline live run `8dc9b773-9875-4b6a-ac86-9b1a916180fc` succeeded through `cv_generation`.
  - Tracked taxonomy, prompt, profile, configuration, and input hashes remained unchanged.
- Validation limits:
  - Full repo suite retains unrelated `tests/test_deferred_cleanup_characterization.py::test_deferred_cleanup_modules_have_no_active_src_or_test_importers` baseline failure.
  - Full repo-contract validator was blocked by OS-locked `.tmp-tests/repo-contract-pytest`; fast contract validation passed.
- SSOT disposition: No remaining SSOT violation found in audited semantic runtime scope. Canonical semantic facts have one data-plane authority; compatibility and control-plane map access stays bounded outside that authority.

## Risk And Disposition

- Residual risk: Low. Provider output may vary, but persistence, fingerprint presence, source boundaries, and all three invalidation laws are structural and live-verified.
- Disposition decision: `resolved`
- Follow-ups: Keep the persistence path assertion, source-boundary scan, symmetry matrix, and three mapping-law scenarios in regression coverage.

## Artifact Index

- Manifest: `manifest.yaml`
- Evidence root: `evidence/`
- Repro root: `repro/`

## Completion Checklist

- [x] qualifying trigger documented
- [x] evidence bundle linked and hashed
- [x] deterministic repro steps included
- [x] expected vs actual included
- [x] bounded fix applied
- [x] post-fix live verification attached
- [x] SSOT disposition recorded
- [x] final status recorded as `resolved`
