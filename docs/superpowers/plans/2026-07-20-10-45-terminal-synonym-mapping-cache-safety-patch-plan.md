---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: terminal-synonym-mapping-cache-safety-patch
parent_spec: docs/superpowers/specs/2026-07-17-21-30-fitcv-semantic-snapshot-ssot-spec.md
targets:
  - config/taxonomy/skill_synonyms.yaml
  - src/fitcv/config_loader.py
  - src/fitcv/config.py
  - src/fitcv/semantic_snapshot.py
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - docs/superpowers/plans/2026-07-17-22-05-fitcv-semantic-snapshot-ssot-plan.md
---

# Terminal Synonym Mapping And Cache Safety Patch Plan

## Goal

Make every effective synonym alias resolve directly to one terminal canonical value, reject duplicate or conflicting aliases before iteration order can select a winner, and preserve pair-local cache reuse: an unchanged `A:B` mapping must keep reusable results when unrelated mappings are added, removed, or reordered.

## Implementation Outcomes

### Terminal semantic policy

`compile_semantic_policy` becomes the single owner of terminal alias resolution for skill, domain, and role-family maps. Acyclic chains flatten deterministically, cycles and normalized conflicts fail closed, and effective maps expose terminal values only.

### Conflict-safe synonym ingestion and persistence

Canonical policy files, configured overlay files, uploaded YAML overlays, and global-promotion writes reject exact duplicate YAML keys and normalized alias conflicts. Base-versus-overlay precedence remains unchanged and intentional overrides remain valid across sources.

### Pair-local reuse identity

Semantic stage reuse and synonym-triage recommendation reuse depend only on exact consumed pair data, relevant conflict gates, runtime contract, and provider identity. Unrelated `C:D` edits do not invalidate unchanged `A:B`; changing `A:B` to `A:B2` does.

### Reconciled SSOT contracts

Runtime code, tests, and the semantic snapshot specification agree on terminal-chain behavior. Full-map synonym hashes stop acting as cache-reset predictors, and app/worker synonym-triage paths use shared recommendation and fingerprint logic.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-code-standards`, `skill-test-driven-development`, `skill-verification-before-completion`
- Isolation: manual Git worktree `C:/Users/HOANG PHI LONG DANG/repos/JOB-PROJECT/.worktrees/terminal-synonym-mapping-cache-safety` on `codex/terminal-synonym-mapping-cache-safety`; primary-checkout prototype changes remain outside this lane
- Parallel ownership: none; `src/fitcv/semantic_snapshot.py` and synonym fingerprint contracts are shared prerequisites
- Sequential fallback: semantic contract, ingestion, write paths, reuse logic, then docs and final verification
- Validation baseline: before any implementation edit, run `python scripts/validate_planning_lifecycle.py --strict 2>&1 | Set-Content "$env:TEMP\terminal-synonym-planning-before.txt"`; existing unrelated metadata errors are tolerated only when final output adds no new error path or code

## Execution Progress

- 2026-07-20: Task 1 verified with `113 passed`; terminal policy v2, captured v1 compatibility, canonical terminal mappings, and specification text now agree.
- 2026-07-20: Task 2 verified with `106 passed`; duplicate-safe loading covers dedicated synonym files, configured overlays, uploaded YAML, and synonym sections inside the supported legacy taxonomy fallback without changing unrelated taxonomy duplicate handling.
- 2026-07-20: Task 3 active; shared compiled atomic policy I/O exists and app/worker load/persist wrappers use it. Preview rejects complete-map cycles before readiness. Worker all-field promotion symmetry and final commit-path reconciliation remain open.

## Task Breakdown

### Task 1: Reconcile terminal mapping contract

**Purpose:**
- Make current specification, compiler behavior, tests, and canonical synonym data agree on terminal canonical resolution.

**Specification Coverage:**
- User-approved direct terminal mapping behavior.
- Existing semantic specification requirement to flatten alias chains to terminal canonical values.
- Existing cache law that unrelated mapping edits preserve unaffected stage reuse.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv/semantic_snapshot.py:SEMANTIC_POLICY_SCHEMA_VERSION`
- Modify: `src/fitcv/semantic_snapshot.py:SEMANTIC_RESOLVER_CONTRACT_VERSION`
- Modify: `src/fitcv/semantic_snapshot.py:_compile_map`
- Modify: `src/fitcv/semantic_snapshot.py:_resolve_value`
- Modify: `src/fitcv/semantic_snapshot.py:build_semantic_snapshot`
- Modify: `tests/test_semantic_snapshot.py:test_compile_semantic_policy_preserves_one_hop_chains_and_rejects_cycles_and_collisions`
- Modify: `config/taxonomy/skill_synonyms.yaml`
- Modify: `docs/superpowers/specs/2026-07-17-21-30-fitcv-semantic-snapshot-ssot-spec.md`

**Dependencies:**
- Current source scan confirms two non-terminal skill chains: `ci/cd-prozesse -> ci/cd pipelines -> ci/cd` and `gcp -> google cloud -> google cloud platform`.
- Current specification contradicts itself: canonical contract requires terminal flattening while acceptance text and tests preserve one-hop chains.

**Steps:**
- [x] Replace the one-hop chain test with terminal-flattening assertions for `a -> b -> c`, plus existing cycle and normalized-collision rejection assertions.
- [x] Flatten acyclic chains during `_compile_map`, store terminal targets in the compiled map, and keep `_resolve_value` as one lookup over already-terminal data.
- [x] Bump compiled policy and resolver contracts to `semantic_policy_v2` and `semantic_resolver_v2`; keep `SEMANTIC_SNAPSHOT_SCHEMA_VERSION` unchanged because snapshot shape does not change.
- [x] Preserve captured `semantic_policy_v1` for persisted continue/retry runs; compile v2 for new runs and for explicit overlay replacement.
- [x] Derive each snapshot resolver fingerprint from its captured policy `resolver_contract_version`, not the current module constant; reject unsupported policy versions and deny cross-version reuse through resolver-contract fingerprint mismatch.
- [x] Rewrite current non-terminal entries to `ci/cd-prozesse: ci/cd` and `gcp: google cloud platform`; retain canonical self-mappings where already present.
- [x] Update contradictory specification acceptance and validation text from one-hop preservation to deterministic terminal flattening.
- [x] Add boundary proof that adding unrelated `C:D` preserves `A:B`, while adding `B:C` is related and changes effective `A` from `B` to terminal `C`.

**Verification:**
- [x] `python -m pytest tests/test_semantic_snapshot.py -q`
- Expected: chains resolve to terminal values; cycles and normalized collisions raise stable `ValueError` messages.
- [x] Add semantic-policy tests with a captured v1 policy fixture and a newly compiled v2 fixture.
- Expected: captured v1 maps retain one-hop resolution and v1 resolver fingerprint; compiled v2 maps resolve terminal values and produce a different resolver fingerprint.
- [x] `$env:PYTHONPATH='src'; python -c "from fitcv.config import load_config; c=load_config(); assert c['semantic_policy']['maps']['skill']['gcp']=='google cloud platform'; assert c['semantic_policy']['maps']['skill']['ci/cd-prozesse']=='ci/cd'"`
- Expected: current canonical policy has no non-terminal compiled skill targets.

**Exit Criteria:**
- Compiler, canonical data, tests, and specification expose one terminal canonical value per alias.

### Task 2: Reject duplicate and conflicting aliases at ingestion

**Purpose:**
- Stop YAML parsing and pre-compilation normalization from silently selecting the last duplicate alias.

**Specification Coverage:**
- Reject unresolved conflicts rather than selecting by iteration order.
- Preserve base-versus-overlay precedence while validating each source independently.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv/config_loader.py:load_yaml_file`
- Modify: `src/fitcv/config.py:_load_yaml_file`
- Modify: `src/fitcv/config.py:_load_policy_file`
- Modify: `src/fitcv/config.py:load_config`
- Modify: `src/fitcv/config.py:_normalize_skill_synonyms`
- Modify: `src/fitcv/config.py:parse_runtime_synonym_overlay_yaml`
- Modify: `src/fitcv/config.py:parse_skill_synonym_overlay_yaml`
- Modify: `src/fitcv/config.py:_load_skill_synonym_overlays`
- Modify: `tests/test_config.py`

**Dependencies:**
- Task 1 terminal compiler contract complete.

**Steps:**
- [x] Add one duplicate-key-aware YAML loader option in `config_loader.py`; error includes normalized alias and source path or upload context.
- [x] In the `load_config` policy loop, request duplicate-key rejection for `skill_synonyms`, `domain_synonyms`, and `role_family_synonyms`; selectively inspect only synonym-map sections in the supported legacy `taxonomy.yaml` fallback so unrelated policy YAML behavior remains unchanged.
- [x] Use the same duplicate-key rejection for configured synonym overlay files and uploaded runtime synonym YAML.
- [x] Change `_normalize_skill_synonyms` from dictionary-comprehension overwrite to explicit normalized insertion that rejects same-source aliases mapping to different normalized canonicals.
- [x] Allow same-source duplicate normalized aliases only when canonical values normalize identically, then deduplicate deterministically.
- [x] Keep overlay precedence unchanged by validating base and each overlay before the existing ordered merge.

**Verification:**
- [x] `python -m pytest tests/test_config.py -q`
- Expected: exact duplicate `looker` keys and normalized `Looker`/`looker` conflicts fail; identical normalized duplicates deduplicate; overlay override of a base alias still wins.

**Exit Criteria:**
- No supported synonym YAML path can silently turn `looker: looker studio` plus `looker: powerbi` into last-write-wins runtime state.

### Task 3: Validate every global promotion write once

**Purpose:**
- Ensure manual and worker auto-promotion cannot persist conflicts, cycles, or non-terminal effective mappings through separate unchecked writers.

**Specification Coverage:**
- Canonical global synonym YAML remains policy SSOT.
- App and worker promotion paths remain behaviorally symmetric.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Create: `src/fitcv_cp/synonym_policy_io.py`
- Modify: `src/fitcv_cp/app.py:_load_global_skill_synonyms_map`
- Modify: `src/fitcv_cp/app.py:_persist_global_skill_synonyms_map`
- Modify: `src/fitcv_cp/app.py:_load_global_domain_alias_map`
- Modify: `src/fitcv_cp/app.py:_persist_global_domain_alias_map`
- Modify: `src/fitcv_cp/app.py:_load_global_role_family_alias_map`
- Modify: `src/fitcv_cp/app.py:_persist_global_role_family_alias_map`
- Modify: `src/fitcv_cp/app.py:_build_promote_global_preview`
- Modify: `src/fitcv_cp/worker_job.py:_load_global_skill_synonyms_map`
- Modify: `src/fitcv_cp/worker_job.py:_persist_global_skill_synonyms_map`
- Modify: `src/fitcv_cp/worker_job.py:_load_global_domain_alias_map`
- Modify: `src/fitcv_cp/worker_job.py:_persist_global_domain_alias_map`
- Modify: `src/fitcv_cp/worker_job.py:_load_global_role_family_alias_map`
- Modify: `src/fitcv_cp/worker_job.py:_persist_global_role_family_alias_map`
- Modify: `tests/test_fitcv_cp/test_synonym_global_policy_io.py`
- Modify: `tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py`
- Modify: `tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py`
- Modify: `tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py`

**Dependencies:**
- Tasks 1 and 2 provide compiler and YAML-validation contracts.

**Steps:**
- [x] Move duplicated skill/domain/role-family global-policy load, render, validate, and atomic-write behavior into `synonym_policy_io.py`; app and worker retain thin imports only.
- [x] Build and compile the complete candidate field map during preview; mark cycles, normalized conflicts, and invalid terminalization with stable reason codes before showing rows as ready.
- [x] Recompile the same complete candidate map before file replacement and persist compiled terminal mappings, not unchecked proposal values.
- [x] Preserve existing atomic replacement and failure cleanup behavior.
- [x] Return identical actionable promotion failure reason codes from preview, manual commit, and worker auto-promotion instead of partially writing the map.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py tests/test_fitcv_cp/test_worker_job.py -q`
- Expected: preview and commit agree, app and worker share one validated write path, and invalid complete maps leave existing files unchanged.

**Exit Criteria:**
- One implementation owns canonical synonym policy persistence and both promotion paths fail closed before mutation.

### Task 4: Make synonym-triage reuse pair-local

**Purpose:**
- Remove whole-overlay invalidation from recommendation reuse because overlay contents are not consumed by builtin or provider triage execution.

**Specification Coverage:**
- Unchanged `A:B` retains reuse after unrelated `C:D` edits.
- Changed canonical, conflict candidate set, status gate, provider, model, wire API, or triage contract triggers fresh evaluation.
- App refresh and worker auto-triage use symmetric execution and reuse identity.

**Required Skills:**
- `skill-code-standards`
- `skill-test-driven-development`

**Files And Symbols:**
- Create: `src/fitcv_cp/synonym_proposals.py:build_synonym_triage_input`
- Modify: `src/fitcv_cp/synonym_proposals.py:build_synonym_triage_fingerprint`
- Modify: `src/fitcv_cp/synonym_proposals.py:build_synonym_triage_core_fingerprint`
- Modify: `src/fitcv_cp/synonym_proposals.py:evaluate_synonym_triage_reuse`
- Modify: `src/fitcv_cp/synonym_proposals.py` shared builtin recommendation function
- Modify: `src/fitcv_cp/app.py:admin_run_synonym_proposals_triage_refresh`
- Modify: `src/fitcv_cp/app.py:_triage_synonym_proposal_recommendation`
- Modify: `src/fitcv_cp/worker_run_support.py:_triage_synonym_proposal_recommendation_builtin`
- Modify: `src/fitcv_cp/worker_job.py` auto-triage call path
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Task 1 defines terminal pair identity.

**Steps:**
- [x] Add failing tests proving unrelated overlay pair changes preserve strict/core triage reuse for unchanged `A:B`.
- [x] Remove whole `run_overlay_fingerprint` from strict and core triage fingerprint payloads and evaluator inputs; retain overlay fingerprints only as observability metadata.
- [x] Build one normalized triage-input object containing field, alias, terminal canonical, sorted candidate canonicals, and six-decimal confidence; use it for builtin recommendation logic, provider prompt input, and fingerprinting.
- [x] Keep compatible status gate, runtime provider/model/wire API, and triage version beside the shared triage input in reuse identity.
- [x] Remove run-scoped `proposal_id`, open-state `proposal_status`, and volatile `now_iso` from provider decision input; keep status only as reuse eligibility gate and timestamps only in emitted recommendation metadata after decision generation.
- [x] Move duplicated builtin recommendation decision logic into `synonym_proposals.py`; app and worker call the same pure function.
- [x] Add negative tests proving `A:B2`, changed confidence across decision thresholds, changed conflict candidates, or changed runtime contract forces fresh recommendation.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_app.py -k "synonym_triage and (fingerprint or reuse)" -q`
- [x] `python -m pytest tests/test_fitcv_cp/test_worker_job.py -k "synonym and (triage or reuse)" -q`
- Expected: unrelated map edits reuse; pair, confidence, conflict-gate, or runtime changes refresh; app and worker counters agree.

**Exit Criteria:**
- Synonym-triage cache identity hashes exact recommendation inputs, not whole-map context absent from execution.

### Task 5: Remove stale full-map cache warning and align docs

**Purpose:**
- Stop control-plane observability from claiming likely CV-analysis cache reset whenever any synonym entry changes.

**Specification Coverage:**
- Operator surfaces remain observability, never semantic reuse authority.
- Exact stage-input fingerprints remain sole cache decision source.

**Required Skills:**
- `skill-code-standards`
- `skill-verification-before-completion`

**Files And Symbols:**
- Delete: `src/fitcv_cp/app.py:_stable_synonym_hash`
- Modify: `src/fitcv_cp/app.py` trigger paths currently emitting `cv_analysis_reuse_reset_likely`
- Modify: `docs/configuration.md`
- Modify: `docs/architecture.md`
- Modify: `docs/features/pipeline_performance/feature.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/superpowers/plans/2026-07-17-22-05-fitcv-semantic-snapshot-ssot-plan.md`
- Generate: affected feature/lineage outputs through repository generators

**Dependencies:**
- Tasks 1 through 4 complete.

**Repository Divergence:**
- `docs/features/*`, `docs/stages/*`, and `docs/generated/*` were intentionally removed by commit `b253bb44` before this lane started. Do not recreate retired starter-kit metadata. `docs/architecture.md` and `docs/configuration.md` are current canonical documentation owners. The retained generator validates with `--validate-only`; write mode creates empty retired outputs and must not be used for this tree.

**Steps:**
- [x] Remove both whole-map comparison blocks and `_stable_synonym_hash`; preserve trigger API response shape with an empty warnings list when no real warning exists.
- [x] Document terminal compilation, conflict rejection, overlay precedence, pair-local semantic reuse, and pair-local triage reuse.
- [x] Add a concise amendment note to the completed 2026-07-17 semantic snapshot plan pointing to this patch plan; preserve its historical checked one-hop execution record unchanged.
- [x] Record retired feature-source divergence, update current canonical docs, and validate retained generator inputs without recreating empty generated outputs.
- [x] Run source scans proving no cache decision or warning uses the complete skill synonym map as a proxy for exact consumed values.
- [x] Capture final output with `python scripts/validate_planning_lifecycle.py --strict 2>&1 | Set-Content "$env:TEMP\terminal-synonym-planning-after.txt"`; final output may retain only identical pre-existing error paths/codes and must add no error for either touched planning artifact.

**Verification:**
- [x] `rg -n "_stable_synonym_hash|cv_analysis_reuse_reset_likely" src tests docs --glob '!docs/superpowers/plans/2026-07-20-10-45-terminal-synonym-mapping-cache-safety-patch-plan.md'`
- Expected: no runtime or contract references remain.
- [x] `python tools/docs/generate_architecture_metadata.py --validate-only`
- Expected: retained generator accepts current source tree without recreating retired metadata outputs.
- [x] `python scripts/validate_planning_lifecycle.py --strict 2>&1 | Set-Content "$env:TEMP\terminal-synonym-planning-after.txt"`
- [x] `Compare-Object (Get-Content "$env:TEMP\terminal-synonym-planning-before.txt") (Get-Content "$env:TEMP\terminal-synonym-planning-after.txt")`
- Expected: no added planning error path/code; unrelated baseline errors may remain until their owning work is executed.

**Exit Criteria:**
- Runtime reuse decisions and operator messaging obey same exact-input law.

## Verification

- `python -m pytest tests/test_semantic_snapshot.py tests/test_config.py tests/test_enrich.py tests/test_gap_analysis.py tests/test_evidence.py tests/test_pipeline.py -q`
- `python -m pytest tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_synonym_promote_preview_field_aware.py tests/test_fitcv_cp/test_synonym_promote_commit_field_aware.py tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py -q`
- `python -m compileall -q src/fitcv src/fitcv_cp`
- `python scripts/validate_planning_lifecycle.py --strict` before and after implementation with output captured under `$env:TEMP`; no new error path/code is allowed
- `python scripts/validate_checkpoint_packs.py`
- `python scripts/validate_repo_contracts.py --fast`
- `python scripts/hooks/run_validator.py --fast`
- `git diff --check`
- `rg -n "preserve.*one-hop|one-hop.*chain|_stable_synonym_hash|cv_analysis_reuse_reset_likely" src tests docs --glob '!docs/superpowers/plans/2026-07-20-10-45-terminal-synonym-mapping-cache-safety-patch-plan.md' --glob '!docs/superpowers/plans/2026-07-17-22-05-fitcv-semantic-snapshot-ssot-plan.md'`

## Completion Criteria

The plan is ready for completion verification when:

1. every supported synonym source rejects ambiguous duplicate aliases before merge
2. every compiled semantic map resolves aliases to terminal canonical values
3. current global skill policy contains no non-terminal chains
4. app and worker global-promotion paths share one validated atomic writer
5. unchanged `A:B` keeps semantic-stage and synonym-triage reuse after unrelated `C:D` edits, while related `B:C` terminalization refreshes affected `A`
6. changed `A:B2`, confidence threshold, conflict gate, or runtime contract forces only affected fresh work
7. v1 persisted runs remain reproducible, new runs use v2, and cross-version reuse fails closed
8. no full-map hash remains a cache decision or cache-reset warning proxy
9. specification, amended historical plan, runtime code, tests, canonical docs, and generated outputs agree
10. all task-local and final verification commands pass except explicitly baselined planning-lifecycle errors, with no new error path/code and unrelated workspace changes preserved

The plan may be marked `completed` only after `skill-verification-before-completion` runs fresh evidence and returns `verified`.
