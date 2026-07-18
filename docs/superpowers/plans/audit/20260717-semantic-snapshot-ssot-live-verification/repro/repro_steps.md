# Reproduction

## Preconditions

- Windows source-mode runtime.
- Repo virtual environment with configured provider dependencies.
- Valid provider credential loaded without printing its value.
- `data/sample_data_engineer_jobs.json` and configured private candidate profile exist.
- Fresh isolated SQLite database for baseline.
- Both global synonym-promotion toggles disabled.
- Identical input, profile, prompt, runtime policy, and cache lineage across comparison scenarios.

## Baseline

1. Hash tracked taxonomy, prompt, configuration, profile, and input surfaces.
2. Start `fitcv_cp.main:app` on loopback with fresh `FITCV_CP_SQLITE_PATH` and inline execution.
3. POST `/runs` with the 13-job input, `run_all`, and promotion toggles disabled.
4. Wait for terminal status and require completion through `cv_generation`.
5. Download run JSON, events, export, artifact bundle, and structured-job rows.
6. Require 13 persisted snapshots plus exported semantic value and derivation fingerprints.
7. Preserve baseline cache lineage for the overlay scenarios.

## Overlay Scenarios

Run each scenario with baseline input and profile unchanged. Change only the runtime semantic overlay.

| Scenario | Overlay | Required law |
| --- | --- | --- |
| Unrelated mapping | `C:D` where neither term is consumed by the jobs | Exact reuse remains valid for enrich, AI score, and CV analysis. |
| Relevant target change | `sql:sql ssot changed` | Jobs consuming `sql` change canonical semantic value; affected AI score and CV analysis recompute. |
| Relevant alias add | `sql snapshot alias:sql` | Canonical semantic values remain unchanged; AI score reuses, while alias-sensitive CV analysis recomputes. |

For every overlay run:

1. Reuse baseline cache lineage.
2. Submit the same 13-job run with only the named overlay changed.
3. Wait for terminal status and require completion through `cv_generation`.
4. Compare semantic values and exact stage input fingerprints against baseline.
5. Record enrich, AI-score, and CV-analysis reuse decisions.
6. Re-hash tracked SSOT surfaces and require no tracked-file mutation.

## Expected Resolution Evidence

- Baseline: 13 of 13 snapshots persisted; 68 snapshot, value-fingerprint, and derivation-fingerprint occurrences exported.
- Unrelated mapping: 13 enrich cache hits, 4 AI exact reuses, 1 CV-analysis exact reuse.
- Relevant target change: 13 enrich cache hits, 5 semantic values changed, 1 AI fresh compute, 1 CV-analysis fresh compute.
- Relevant alias add: 13 enrich cache hits, 0 semantic values changed, 4 AI exact reuses, 1 CV-analysis fresh compute.
- Source scan: no raw semantic-map authority in audited data-plane consumers.

## Verification Commands

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_semantic_snapshot.py tests/test_config.py tests/test_enrich.py tests/test_rule_filter.py tests/test_embeddings.py tests/test_ranking.py tests/test_gap_analysis.py tests/test_cv_generator.py tests/test_validator.py tests/test_ai_score.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py -q
rg -n "semantic_snapshot|skill_synonyms|domain_alias_map|role_family_alias_map|def _skill_variants" src/fitcv src/fitcv_cp
.\.venv\Scripts\python.exe scripts/audit_check.py docs/superpowers/plans/audit/20260717-semantic-snapshot-ssot-live-verification
```

## Determinism

Fixed 13-row input, baseline cache lineage, frozen run policy, disabled global promotion, one changed overlay per scenario, and before/after SSOT hashes. Provider output may vary; persistence, fingerprint presence, reuse decisions, and bounded invalidation laws are structural assertions.
