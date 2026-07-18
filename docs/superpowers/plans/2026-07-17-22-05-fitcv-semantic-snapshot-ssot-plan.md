---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: fitcv-semantic-snapshot-ssot
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-cross-stage-cache-safety
parent_spec: docs/superpowers/specs/2026-07-17-21-30-fitcv-semantic-snapshot-ssot-spec.md
targets:
  - src/fitcv/semantic_snapshot.py
  - src/fitcv/config.py
  - src/fitcv/enrich.py
  - src/fitcv/rule_filter.py
  - src/fitcv/embeddings.py
  - src/fitcv/ranking.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/cv_generator.py
  - src/fitcv/validator.py
  - src/fitcv/pipeline.py
  - src/fitcv/evidence.py
  - src/fitcv/ai_score.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/reuse.py
  - tests/test_semantic_snapshot.py
  - tests/test_config.py
  - tests/test_enrich.py
  - tests/test_rule_filter.py
  - tests/test_embeddings.py
  - tests/test_ranking.py
  - tests/test_gap_analysis.py
  - tests/test_cv_generator.py
  - tests/test_validator.py
  - tests/test_ai_score.py
  - tests/test_evidence.py
  - tests/test_agentic_cv_analysis.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_pipeline_checkpoint_contract.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py
  - tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py
  - docs/features/pipeline_performance/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/trigger_run_management/feature.source.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/rule_filter.source.yaml
  - docs/stages/shortlist.source.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/architecture.md
  - docs/pipeline.md
  - docs/configuration.md
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
related_features:
  - pipeline_performance
  - cv_system
  - trigger_run_management
related_stages:
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

# FitCV Semantic Snapshot SSOT Implementation Plan

## Goal

Implement one subject-aware `SemanticSnapshot` source of truth for `job`, `candidate`, and `criteria` semantics. Compile effective synonym and taxonomy policy once, reproject reusable raw extraction facts through one resolver, and make every stage reuse decision depend only on exact stage execution input plus exact stage contract.

Required behavior for every admissible mapping pair `A:B`:

- preserve raw `A` independently from semantic policy
- reuse enrich extraction when raw source and extraction contract remain equal
- reproject `A` cheaply when effective mapping changes
- recompute a downstream stage only when that stage's consumed semantic projection changes
- keep unrelated mapping edits invisible to unaffected stage fingerprints
- deny affected reuse when historical raw facts cannot prove exact current input

Known change risk:

- `canonicalize_skill` has MEDIUM upstream impact with nine direct callers across rule filtering, gap analysis, CV generation, and validation
- `merge_scraped_and_enriched`, `build_job_summary_signature_payload`, `build_cv_analysis_contract_fingerprint`, `_skill_variants`, and `compute_must_have_match` have LOW direct impact but participate in pipeline reuse flows
- execution must rerun GitNexus impact before editing each named symbol and stop for user warning if fresh risk becomes HIGH or CRITICAL

## Key Deliverables

### One semantic policy compiler and resolver

Add one small stdlib-only semantic module that validates effective policy, resolves aliases uniformly, builds snapshots for every supported subject, and emits deterministic raw-source, derivation, and semantic-value fingerprints. Existing stage input builders retain ownership of stage-input and stage-contract fingerprints and consume exact snapshot projections. Keep fixed semantic laws in code, not runtime configuration. Do not add a service, database table, invalidation worker, plugin, factory, or resolver class.

### Symmetric fresh, cached, resumed, and historical behavior

Fresh enrich and cached enrich must build the same snapshot from the same raw facts. Policy-only changes must not rerun extraction. Historical payloads with sufficient raw facts must reproject; canonical-only or malformed payloads must become explicitly incomplete and deny only affected reuse.

### Exact stage input reuse

Rule filter, shortlist, ranking, gap analysis, AI score, CV analysis, and CV generation must fingerprint the exact object supplied to execution. Canonical projections and alias-equivalence projections must remain distinct so stages invalidate only for semantic differences they consume.

### Duplicate semantic logic removal

Migrate shared callers, retain only thin compatibility wrappers where public or widely imported APIs require them, and prohibit direct runtime reads of `skill_synonyms`, `domain_alias_map`, and `role_family_alias_map` outside policy compilation, resolver ownership, and control-plane administration surfaces.

### Managed contract and evidence alignment

Update feature, stage, architecture, pipeline, and configuration sources; regenerate managed discovery from source; and produce focused, full-suite, lifecycle-parity, source-boundary, GitNexus, and live-run evidence for the three required synonym-change scenarios.

## Execution Preconditions

- Use an isolated worktree or verify explicit ownership of every target before code edits; do not mix this cross-cutting migration with unrelated dirty changes.
- Run `python scripts/hooks/run_validator.py --fast` and focused baseline tests before the first implementation edit.
- Run `.\scripts\get_gitnexus_freshness.ps1`; refresh with `gitnexus analyze` when high-trust impact data is stale.
- Before modifying any function, class, or method, run GitNexus upstream impact for that symbol as required by repo instructions.
- Preserve current external config file shapes and persisted payload compatibility unless a failing acceptance test proves a contract change is required.
- Freeze compiled semantic policy for the run lifetime; synonym promotion affects the next run rather than changing semantics mid-run.
- Follow TDD: add or expose one failing behavioral proof before each non-trivial implementation slice, then make the smallest code change that passes it.

## Task/Wave Breakdown

### Task 1: Lock semantic invariants in failing tests

**Purpose:**
- Convert approved SSOT, symmetry, normalization, and fingerprint laws into runnable tests before implementation.

**Files:**
- Inspect: `docs/superpowers/specs/2026-07-17-21-30-fitcv-semantic-snapshot-ssot-spec.md`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/enrich.py`
- Create: `tests/test_semantic_snapshot.py`
- Modify: `tests/test_config.py`
- Verify: `repo_config/planning_artifact_schema.yaml`

**Preconditions:**
- Approved spec is `active` and parent lineage validates.
- Baseline validator and focused config/enrich tests are recorded.

**Steps:**
- [ ] Reconfirm GitNexus freshness and record current upstream risk for semantic entrypoints named in this plan.
- [ ] Add failing tests for deterministic policy compilation independent of map insertion order, case, whitespace, duplicates, and equivalent list ordering.
- [ ] Add failing tests for one-hop alias-chain preservation, normalized-key collisions, conflicting canonical targets, self-reference handling, cycle rejection, and punctuation-sensitive skills such as `C`, `C++`, `C#`, `.NET`, and `Node.js`.
- [ ] Add one table-driven subject matrix proving the same resolver contract builds `job`, `candidate`, and `criteria` snapshots.
- [ ] Add tests separating raw source equality, semantic derivation equality, semantic value equality, canonical projection equality, and alias-equivalence projection equality.
- [ ] Add tests proving unrelated `C:D` edits leave an `A:B` subject value fingerprint unchanged, `A:B2` changes canonical projection, and `A2:B` changes only alias-sensitive equivalence when canonical values stay equal.
- [ ] Add tests proving set-like fields ignore ordering and duplicates while ordered fields retain order where execution consumes it.

**Verification:**
- [ ] `python -m pytest tests/test_semantic_snapshot.py tests/test_config.py -q` fails only for missing approved behavior, not fixture or import errors.

**Exit Criteria:**
- Every semantic law has one direct failing proof and no test depends on a stage-specific invalidation branch.

### Task 2: Add minimal semantic policy and snapshot core

**Purpose:**
- Establish one compiled policy, one resolver path, one snapshot shape, and deterministic fingerprints.

**Files:**
- Create: `src/fitcv/semantic_snapshot.py`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_semantic_snapshot.py`
- Modify: `tests/test_config.py`

**Preconditions:**
- Task 1 red tests exist.
- Fresh GitNexus impact is reviewed before editing affected config symbols.

**Steps:**
- [ ] Reuse existing stable JSON normalization and hashing utilities; do not introduce a dependency or second hash implementation.
- [ ] Compile effective skill, domain, and role-family mappings once after existing base-plus-overlay precedence resolves.
- [ ] Preserve existing taxonomy-specific normalization and one-hop chain behavior, reject ambiguous normalized collisions and cycles, and preserve deterministic canonical ordering.
- [ ] Add one subject-neutral snapshot builder with explicit `subject_kind`, existing-source `subject_identity`, raw entities, resolved entities, alias-equivalence data, per-field completeness, and schema version.
- [ ] Compute `raw_semantic_source_fingerprint` from reusable raw facts only.
- [ ] Compute `semantic_derivation_fingerprint` from `raw_semantic_source_fingerprint`, compiled policy fingerprint, and resolver/schema version.
- [ ] Compute `semantic_value_fingerprint` from normalized resolved snapshot value only.
- [ ] Expose projection helpers for canonical-only and alias-equivalence consumers; do not expose raw maps to stages.
- [ ] Keep compatibility APIs as thin calls into the resolver only where current callers require them.
- [ ] Add repo-required Python metadata and capability linkage to new behavioral code.

**Verification:**
- [ ] `python -m pytest tests/test_semantic_snapshot.py tests/test_config.py -q`
- [ ] `python -m compileall -q src/fitcv/semantic_snapshot.py src/fitcv/config.py`

**Exit Criteria:**
- One module owns semantic compilation, resolution, snapshot construction, and semantic fingerprint meaning; Task 1 tests pass.

### Task 3: Make fresh and cached enrich paths symmetric

**Purpose:**
- Preserve extraction cache reuse while guaranteeing current semantic projection for every job entry.

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_enrich.py`
- Modify: `tests/test_pipeline.py`
- Verify: `src/fitcv/reuse.py`

**Preconditions:**
- Task 2 semantic core passes.
- GitNexus upstream impact for `merge_scraped_and_enriched` and touched pipeline symbols is reviewed.

**Steps:**
- [ ] Add failing fresh-versus-cached parity tests using identical raw extraction facts.
- [ ] Keep enrich extraction identity independent from semantic policy when raw source and extraction contract are unchanged.
- [ ] Build and persist `semantic_snapshot` from fresh raw extraction facts before deriving flat compatibility fields.
- [ ] On cache hit, reconstruct the snapshot from preserved raw facts through the same resolver instead of trusting stored canonical fields.
- [ ] Derive legacy flat job fields one-way from the snapshot; remove any reverse authority from flat canonical fields.
- [ ] Support historical payloads with sufficient raw entity or raw-list facts; mark only canonical-only, incomplete, or malformed fields as incomplete without guessing raw aliases.
- [ ] Feed per-field completeness into stage input validation so only stages requiring unavailable projections recompute.
- [ ] Prove `A:B` unchanged reuses extraction and downstream values, `A:B2` reuses extraction but refreshes affected stages, and unrelated `C:D` changes preserve affected job snapshot values.

**Verification:**
- [ ] `python -m pytest tests/test_enrich.py tests/test_pipeline.py -q`
- [ ] Persisted fresh and cached payload fixtures contain equivalent snapshots and compatibility projections for equivalent raw facts.

**Exit Criteria:**
- Fresh, cached, and reconstructable historical paths converge on one snapshot; extraction never reruns for policy-only changes.

### Task 4: Migrate shared skill consumers and compatibility callers

**Purpose:**
- Remove parallel skill canonicalization while preserving public behavior across all current callers.

**Files:**
- Modify: `src/fitcv/rule_filter.py`
- Modify: `src/fitcv/gap_analysis.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_rule_filter.py`
- Modify: `tests/test_gap_analysis.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_validator.py`
- Create or modify: `tests/test_semantic_snapshot.py`

**Preconditions:**
- Task 3 establishes snapshot availability on job entries.
- Re-run GitNexus impact for `canonicalize_skill`, `_skill_variants`, `compute_must_have_match`, and each modified shared symbol; MEDIUM risk and nine known callers are explicitly covered.

**Steps:**
- [ ] Add failing caller-parity tests for canonical skill, alias-equivalence, must-have matching, gap matching, CV generation, and validation.
- [ ] Route `canonicalize_skill` through the shared resolver as a compatibility wrapper if removing it would widen the change unnecessarily.
- [ ] Replace `_skill_variants` and must-have comparison inputs with snapshot alias-equivalence projections.
- [ ] Migrate gap analysis, CV generation, and validation to the same projection contract without local map traversal.
- [ ] Add a source-boundary test that rejects new direct runtime reads of synonym and alias maps outside `config.py`, `semantic_snapshot.py`, and explicit control-plane policy administration surfaces.
- [ ] Delete local normalization, chain traversal, and variant-building code made redundant by the resolver.

**Verification:**
- [ ] `python -m pytest tests/test_rule_filter.py tests/test_gap_analysis.py tests/test_cv_generator.py tests/test_validator.py tests/test_semantic_snapshot.py -q`
- [ ] Source-boundary scan reports no unauthorized direct semantic-map consumer.

**Exit Criteria:**
- All shared skill consumers use one resolver contract and retain equivalent external outcomes for equivalent projections.

### Task 5: Align shortlist, ranking, and AI-score execution inputs

**Purpose:**
- Make runtime inputs and fingerprints identical for semantic consumers used before CV analysis.

**Files:**
- Modify: `src/fitcv/embeddings.py`
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_embeddings.py`
- Modify: `tests/test_ranking.py`
- Modify: `tests/test_ai_score.py`
- Modify: `tests/test_pipeline.py`

**Preconditions:**
- Task 4 completes shared canonical and equivalence projections.
- GitNexus impact for `build_job_summary_signature_payload` and ranking/AI-score entrypoints is reviewed.

**Steps:**
- [ ] Add failing tests that capture each stage execution object and compare it with the object serialized for `stage_input_fingerprint`.
- [ ] Build shortlist summary text and summary signature from one canonical snapshot projection, not independently reconstructed fields.
- [ ] Build candidate snapshots through the same resolver and pass explicit canonical or alias-equivalence projections to ranking factors.
- [ ] Build AI-score input from the exact normalized semantic values supplied to scoring.
- [ ] Keep `stage_contract_fingerprint` separate from data input and limited to executable code/schema/prompt/model contract identity.
- [ ] Prove unrelated policy edits leave shortlist, ranking, and AI-score input fingerprints stable.
- [ ] Prove canonical target changes invalidate canonical consumers and alias-set changes invalidate only stages that consume alias equivalence.

**Verification:**
- [ ] `python -m pytest tests/test_embeddings.py tests/test_ranking.py tests/test_ai_score.py tests/test_pipeline.py -q`
- [ ] Spy assertions show fingerprint payload and execution payload are the same normalized object.

**Exit Criteria:**
- Shortlist, ranking, and AI score reuse decisions depend only on exact consumed semantic inputs and exact stage contracts.

### Task 6: Align CV-analysis and generation fingerprints

**Purpose:**
- Stop whole-map invalidation and make expensive CV stages obey the same exact-match law.

**Files:**
- Modify: `src/fitcv/evidence.py`
- Modify: `src/fitcv/agentic_cv_analysis.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/test_evidence.py`
- Modify: `tests/test_agentic_cv_analysis.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_pipeline.py`

**Preconditions:**
- Task 5 establishes exact input builders for upstream stages.
- GitNexus impact for `build_cv_analysis_contract_fingerprint` and modified analysis/generation entrypoints is reviewed.

**Steps:**
- [ ] Add failing tests proving the CV-analysis contract fingerprint does not change for data-only synonym edits.
- [ ] Restrict CV-analysis and generation contract fingerprints to executable contract identity such as schema, prompt, model, and resolver version where execution semantics require it.
- [ ] Build CV-analysis stage input from the exact snapshot projection, evidence, and other values passed into analysis.
- [ ] Build CV-generation stage input from the exact analysis result, snapshot projection, generation request, and other consumed values.
- [ ] Remove whole synonym maps and unrelated effective config from expensive-stage input and contract payloads.
- [ ] Preserve fresh recomputation when a relevant canonical or alias-equivalence input changes.
- [ ] Prove no stage can execute with an object different from the one that established its reuse identity.

**Verification:**
- [ ] `python -m pytest tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py -q`

**Exit Criteria:**
- CV analysis and generation reuse survives unrelated synonym edits and invalidates for every consumed semantic change.

### Task 7: Enforce lifecycle parity and remove duplicate invalidation paths

**Purpose:**
- Apply one reuse law across initial, retry, continue, run-all, manual-staged, checkpoint, and worker execution modes.

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/reuse.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_pipeline_checkpoint_contract.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py`
- Modify: `tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py`
- Verify: `src/fitcv/enrich.py`
- Verify: `src/fitcv/rule_filter.py`
- Verify: `src/fitcv/embeddings.py`
- Verify: `src/fitcv/ranking.py`
- Verify: `src/fitcv/agentic_cv_analysis.py`
- Verify: `src/fitcv/agentic_cv_generation.py`

**Preconditions:**
- Tasks 3 through 6 migrate stage inputs.
- Existing checkpoint and worker contracts remain backward readable.

**Steps:**
- [ ] Add a table-driven lifecycle matrix for equivalent semantic inputs across initial, retry, continue, run-all, and manual-staged execution.
- [ ] Assert each mode produces identical semantic value, stage input, and stage contract fingerprints for equivalent inputs.
- [ ] Centralize exact-match reuse comparison in the existing reuse decision path; delete stage-specific synonym refresh conditions.
- [ ] Persist enough fingerprint and completeness metadata for resume decisions without persisting semantic policy as a second authority.
- [ ] Make incomplete historical projections produce explicit fresh-compute decisions rather than false cache hits or global invalidation.
- [ ] Verify checkpoint restore preserves the same frozen policy, snapshot, and reuse decisions; promoted synonyms become visible only to a new run.
- [ ] Run repository source scans for direct map reads, duplicate canonicalizers, whole-map stage fingerprints, and legacy invalidation branches; delete confirmed duplicates.

**Verification:**
- [ ] `python -m pytest tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py tests/test_pipeline.py -q`
- [ ] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py -q`
- [ ] Source scans find no unauthorized direct semantic-map reads or stage-specific synonym invalidation branches.

**Exit Criteria:**
- Equivalent inputs produce equivalent reuse outcomes in every supported lifecycle mode, and incomplete inputs fail closed uniformly.

### Task 8: Align docs, regenerate metadata, and prove live behavior

**Purpose:**
- Close source-of-truth, managed-doc, cache-safety, and audit evidence obligations.

**Files:**
- Modify: `docs/features/pipeline_performance/feature.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Modify: `docs/features/trigger_run_management/feature.source.yaml`
- Modify: `docs/stages/enrich.source.yaml`
- Modify: `docs/stages/rule_filter.source.yaml`
- Modify: `docs/stages/shortlist.source.yaml`
- Modify: `docs/stages/ranking.source.yaml`
- Modify: `docs/stages/cv_analysis.source.yaml`
- Modify: `docs/stages/cv_generation.source.yaml`
- Modify: `docs/architecture.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/configuration.md`
- Generate: `docs/generated/architecture_dag.yaml`
- Generate: `docs/generated/capability_lineage.yaml`
- Create: `docs/superpowers/plans/audit/<run-date>-fitcv-semantic-snapshot-ssot/`
- Verify: `docs/superpowers/specs/2026-07-17-21-30-fitcv-semantic-snapshot-ssot-spec.md`
- Verify: `docs/superpowers/plans/2026-07-17-22-05-fitcv-semantic-snapshot-ssot-plan.md`

**Preconditions:**
- Tasks 1 through 7 pass focused tests.
- Runtime credentials and disposable live-run output locations are available without committing secrets.

**Steps:**
- [ ] Update owning feature and stage source contracts with semantic snapshot ownership, exact reuse law, compatibility behavior, and linked code/test evidence.
- [ ] Update architecture, pipeline, and configuration docs to distinguish raw source facts, compiled policy, semantic values, stage input identity, and stage contract identity.
- [ ] Normalize changed contract YAML and regenerate architecture metadata from source; never edit generated discovery manually.
- [ ] Run focused suites, then full Python tests and compile checks.
- [ ] Run planning, template, architecture, repo-contract, and hook validators.
- [ ] Run `git diff --check` and inspect the complete diff for accidental generated or private/public boundary churn.
- [ ] Run GitNexus `detect_changes` before any commit and reconcile affected flows with this plan.
- [ ] Execute live scenario 1: add unrelated `C:D`; prove current `A:B` job keeps downstream cache hits.
- [ ] Execute live scenario 2: change used `A:B` to `A:B2`; prove enrich extraction cache hit, snapshot reprojection, and fresh execution only for stages consuming changed projection.
- [ ] Execute live scenario 3: add alias `A2:B`; prove canonical-only stages reuse while relevant alias-equivalence consumers refresh.
- [ ] Save redacted inputs, fingerprints, reuse decisions, stage outcomes, command logs, and reconciliation notes in the dated audit folder; do not commit secrets or bulky disposable runtime artifacts.

**Verification:**
- [ ] `python -m pytest tests/test_semantic_snapshot.py tests/test_config.py tests/test_enrich.py tests/test_rule_filter.py tests/test_embeddings.py tests/test_ranking.py tests/test_gap_analysis.py tests/test_cv_generator.py tests/test_validator.py tests/test_ai_score.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py -q`
- [ ] `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py -q`
- [ ] `python -m pytest -q`
- [ ] `python -m compileall -q src/fitcv src/fitcv_cp`
- [ ] `.\.venv\Scripts\python.exe scripts\format_contract_yaml.py --check`
- [ ] `.\.venv\Scripts\python.exe tools\docs\generate_architecture_metadata.py`
- [ ] `.\.venv\Scripts\python.exe tools\docs\generate_architecture_metadata.py --check`
- [ ] `python scripts/validate_planning_lifecycle.py`
- [ ] `python scripts/validate_template_required_sections.py`
- [ ] `.\.venv\Scripts\python.exe scripts\validate_repo_contracts.py --fast`
- [ ] `.\.venv\Scripts\python.exe scripts\validate_repo_contracts.py`
- [ ] `python scripts/hooks/run_validator.py --fast`
- [ ] `git diff --check`
- [ ] GitNexus change detection contains only expected semantic, pipeline, test, and documentation flows.
- [ ] Live evidence proves unrelated-change reuse, relevant canonical-change refresh, and bounded alias-equivalence refresh.

**Exit Criteria:**
- Code, tests, docs, generated lineage, graph impact, and live evidence agree on one semantic SSOT and one exact-match reuse law.

## Verification

- `python -m pytest tests/test_semantic_snapshot.py tests/test_config.py tests/test_enrich.py tests/test_rule_filter.py tests/test_embeddings.py tests/test_ranking.py tests/test_gap_analysis.py tests/test_cv_generator.py tests/test_validator.py tests/test_ai_score.py tests/test_evidence.py tests/test_agentic_cv_analysis.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_pipeline_checkpoint_contract.py -q`
- `python -m pytest tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_worker_job_auto_promote_skill_only.py tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py -q`
- `python -m pytest -q`
- `python -m compileall -q src/fitcv src/fitcv_cp`
- `.\.venv\Scripts\python.exe tools\docs\generate_architecture_metadata.py --check`
- `python scripts/validate_planning_lifecycle.py`
- `python scripts/validate_template_required_sections.py`
- `.\.venv\Scripts\python.exe scripts\validate_repo_contracts.py --fast`
- `.\.venv\Scripts\python.exe scripts\validate_repo_contracts.py`
- `python scripts/hooks/run_validator.py --fast`
- `git diff --check`
- GitNexus `detect_changes` confirms expected blast radius before commit.
- Redacted live-run evidence reconciles semantic snapshots, stage input fingerprints, contract fingerprints, reuse decisions, and stage outcomes for all three required mapping scenarios.

## Completion Criteria

A plan item is complete when:

1. one compiled semantic policy and one resolver own all runtime synonym and taxonomy resolution
2. `SemanticSnapshot` is sole runtime authority for resolved job, candidate, and criteria semantics
3. fresh, cached, resumed, staged, and reconstructable historical paths produce equivalent snapshots for equivalent raw facts under one run-frozen policy
4. enrich extraction reuse remains independent from policy-only changes
5. every migrated stage fingerprints the exact object supplied to execution plus a separate exact stage contract
6. unrelated mapping edits do not invalidate unaffected stages
7. relevant canonical and alias-equivalence changes invalidate every and only consuming stages
8. incomplete historical semantic fields deny reuse only for consuming stages without guessing or global invalidation
9. direct runtime map reads, duplicate canonicalization, and stage-specific synonym invalidation paths are removed or reduced to documented thin compatibility wrappers
10. focused, full, lifecycle-parity, source-boundary, managed-doc, GitNexus, and live-run proofs pass
11. audit evidence is redacted and sufficient to support cache-safety and determinism claims
12. every downstream task is `completed` or explicitly `dropped`

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-17-21-30-fitcv-semantic-snapshot-ssot-spec.md`
- `docs/intent/workstreams/threads/workstream-pipeline-efficiency-and-reuse/04-efficiency-reuse-cross-stage-cache-safety.md`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>