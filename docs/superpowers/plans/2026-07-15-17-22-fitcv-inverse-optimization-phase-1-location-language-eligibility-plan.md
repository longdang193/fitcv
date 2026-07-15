---
layer: change
artifact_type: plan
status: completed
completed_at: 2026-07-15T18:46:29+02:00
change_id: 2026-07-15-fitcv-inverse-optimization-phase-1-location-language-eligibility
affects:
  capabilities:
    - cv_system.location-language-eligibility
verification:
  - python -m pytest tests/test_config.py tests/test_ingest.py tests/test_normalize.py
  - python -m pytest tests/test_enrich.py tests/test_fit_factors.py tests/test_rule_filter.py
  - python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
  - python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_ranking.py
  - python scripts/hooks/run_validator.py --fast
  - python scripts/validate_planning_lifecycle.py
  - python tools/docs/generate_architecture_metadata.py --check
  - python scripts/validate_repo_contracts.py --fast
  - git diff --check
outcome:
  summary: Phase 1 now preserves canonical location and language facts, evaluates both through one symmetric policy algebra, gates only confirmed failures, and leaves ranking composition and fit labels unchanged.
template_id: implementation-plan
name: fitcv-inverse-optimization-phase-1-location-language-eligibility-implementation
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-stage-authority-contract
parent_spec: docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md
targets:
  - config/policy/eligibility.yaml
  - src/fitcv/config.py
  - src/fitcv/ingest.py
  - src/fitcv/normalize.py
  - src/fitcv/enrich.py
  - src/fitcv/fit_factors.py
  - src/fitcv/rule_filter.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/sqlite_store.py
  - docs/architecture.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/stages/normalize.source.yaml
  - docs/stages/normalize.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/enrich.yaml
  - docs/stages/rule_filter.source.yaml
  - docs/stages/rule_filter.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_config.py
  - tests/test_ingest.py
  - tests/test_normalize.py
  - tests/test_enrich.py
  - tests/test_fit_factors.py
  - tests/test_rule_filter.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_ranking.py
related_features:
  - cv_system
  - inspection_debugging
related_stages:
  - normalize
  - enrich
  - rule_filter
---

# FitCV inverse optimization Phase 1 location, language, and eligibility implementation plan

## Goal

Implement approved Phase 1 contract as one symmetric, SSOT-based eligibility path:

`raw evidence -> canonical fact -> evaluator truth -> absolute normalizer -> policy projection`

Actual geography remains distinct from `location_type` work mode. Job-language
requirements remain distinct from skills. Location and language share one result
envelope and one mode/status projection table across `disabled`, `ranking_only`,
and `gate_required` modes.

Confirmed hard-gate failures are rejected before shortlist and ranking inputs.
Unknown and not-applicable cases remain eligible with typed diagnostics. Phase 1
emits ranking-ready factor values but does not change ranking composition, final
score, or `strong | stretch | skip` behavior.

Execution constraints:

- use existing Pydantic and Python standard library only
- add no geocoder, fuzzy matcher, language package, schema framework, plugin layer,
  or policy DSL
- keep `config/policy/eligibility.yaml` as sole mutable eligibility-policy owner
- keep enums, schemas, evaluator semantics, projection semantics, and version constants in code
- preserve provider-native data at ingest boundary; downstream code stays provider-neutral
- edit human-owned stage and feature source YAML before generated outputs
- leave unrelated `.tmp-tests/` content untouched
- run GitNexus upstream impact analysis before editing every existing function,
  class, or method; stale graph output is advisory until refreshed

## Key Deliverables

### Canonical location and language facts

Ingest preserves provider location evidence in `source_location`. Enrich emits
versioned `actual_location` and `language_requirements` facts while preserving
existing display location, work mode, raw payload, and canonical skill behavior.
Changed extraction contracts invalidate incompatible enrich reuse.

### Shared eligibility algebra

`src/fitcv/fit_factors.py` owns immutable JSON-safe factor evaluation and policy
result records, candidate-context adaptation, exact normalization, location and
language evaluators, deterministic reason/evidence output, policy validation,
and policy fingerprinting without factor-specific projection logic.

### Deterministic rule-filter boundary

Rule filter evaluates each factor once per job under one loaded policy, attaches
complete results to retained and rejected records, rejects only confirmed
hard-gate failures, and keeps existing work-mode rule separate. Both pipeline
paths build candidate context once and preserve identical eligibility payloads.

### Durable evidence and unchanged ranking

SQLite stores factor results, policy fingerprint, decision, and reason codes in
explicit additive columns rather than `marks_json`. Ranking inputs receive only
retained jobs, while existing ranking features, final score, ordering, and fit
labels remain unchanged in Phase 1.

### Source-first documentation and proof

Stage, feature, architecture, configuration, and pipeline docs describe same
owners and boundaries as code. Generated metadata is rebuilt from source. Focused
tests, ranking regressions, lifecycle validation, repo contracts, and diff checks
provide completion evidence.

## Task/Wave Breakdown

Tasks are sequential. Later tasks consume contracts created by earlier tasks.
Implementation should use `skill-executing-plans`; do not parallelize edits to
shared modules.

### Task 1: Freeze baseline and impact map

**Purpose:**
- establish current behavior, graph freshness, touched symbols, and unrelated
  working-tree boundaries before implementation

**Files:**
- Inspect: `docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md`
- Inspect: `src/fitcv/config.py`
- Inspect: `src/fitcv/ingest.py`
- Inspect: `src/fitcv/normalize.py`
- Inspect: `src/fitcv/enrich.py`
- Inspect: `src/fitcv/rule_filter.py`
- Inspect: `src/fitcv/pipeline.py`
- Inspect: `src/fitcv/pipeline_stage_runner.py`
- Inspect: `src/fitcv_cp/sqlite_store.py`
- Inspect: `tests/test_config.py`
- Inspect: `tests/test_ingest.py`
- Inspect: `tests/test_normalize.py`
- Inspect: `tests/test_enrich.py`
- Inspect: `tests/test_rule_filter.py`
- Inspect: `tests/test_pipeline.py`
- Inspect: `tests/test_pipeline_stage_resume_parity.py`
- Inspect: `tests/test_fitcv_cp/test_sqlite_store.py`
- Inspect: `tests/test_ranking.py`

**Preconditions:**
- Phase 1 spec remains semantically unchanged
- current MASTER, Phase 1 spec, and generated-lineage changes are intended inputs
- `.tmp-tests/` remains unrelated and untouched

**Steps:**
- [x] Step 1: Run `git status --short`; record intended pre-existing changes.
- [x] Step 2: Run `.\scripts\get_gitnexus_freshness.ps1`. If stale, run
  `gitnexus analyze`; use `npx gitnexus analyze` only if direct command is absent.
- [x] Step 3: If refresh fails, record source-first fallback and treat graph results as advisory.
- [x] Step 4: Run upstream GitNexus impact analysis on every existing symbol to be
  changed, including `load_config`, `_normalize_indeed_job`, `prepare_raw_rows`,
  `normalize_job`, `EnrichmentOutput`, `_apply_structured_normalization`,
  `build_raw_job_fingerprint`, `build_enrich_contract_fingerprint`,
  `merge_scraped_and_enriched`, `apply_rule_filters`, `store_filter_results`,
  `run_pipeline`, `execute_rule_filter_stage`,
  `_ensure_local_rule_filter_results_table`, and `list_filter_results_for_run`.
- [x] Step 5: Stop and warn before edits if any impact result is `HIGH` or `CRITICAL`.
- [x] Step 6: Run current focused tests to separate baseline failures from regressions.

**Verification:**
- [x] `.\scripts\get_gitnexus_freshness.ps1`
- [x] `python -m pytest tests/test_config.py tests/test_ingest.py tests/test_normalize.py`
- [x] `python -m pytest tests/test_enrich.py tests/test_rule_filter.py`
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_ranking.py`

**Exit Criteria:**
- baseline status is known, impact risks are reviewed, and new failures can be
  attributed to Phase 1 changes

### Task 2: Add eligibility policy SSOT

**Purpose:**
- create one strict eligibility-policy file, validation boundary, and stable fingerprint

**Files:**
- Create: `config/policy/eligibility.yaml`
- Create: `src/fitcv/fit_factors.py`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_config.py`
- Create: `tests/test_fit_factors.py`

**Preconditions:**
- Task 1 complete
- GitNexus impact for `load_config` and changed config helpers reviewed

**Steps:**
- [x] Step 1: Add failing tests for canonical file loading, exactly two factor
  keys, closed modes, unknown-key rejection, finite `[0, 1]` values, location
  score ordering, language weight ordering, and strict missing-file behavior.
- [x] Step 2: Add failing tests proving `.env.yaml`, ranking policy, and other
  policy files cannot shadow `eligibility_policy`.
- [x] Step 3: Add failing tests proving YAML key order does not change policy
  fingerprint and one golden test for exact SHA-256 output.
- [x] Step 4: Create `config/policy/eligibility.yaml` with only mutable Phase 1
  modes and numeric normalization values from spec.
- [x] Step 5: Add canonical eligibility file to config loading without flat legacy
  fallback; include `eligibility_policy` in ownership-overlap detection.
- [x] Step 6: Implement policy validation and exact SHA-256 fingerprinting over
  UTF-8 `json.dumps(validated_policy, sort_keys=True, separators=(",", ":"),
  ensure_ascii=False, allow_nan=False)` in `fit_factors.py`; fingerprint only the
  validated `eligibility_policy` mapping.
- [x] Step 7: Expose validated policy and fingerprint through loaded config without
  copying numeric defaults into another module.

**Verification:**
- [x] `python -m pytest tests/test_config.py tests/test_fit_factors.py -k "eligibility or policy or fingerprint"`
- [x] Source search confirms one active `eligibility_policy:` config owner.

**Exit Criteria:**
- one canonical policy file loads strictly, invalid policy fails at config
  boundary, and one deterministic fingerprint identifies effective policy
### Task 3: Define shared factor contracts and candidate adapter

**Purpose:**
- establish one JSON-safe contract family and one transient candidate-fit context
  before evaluator-specific logic

**Files:**
- Modify: `src/fitcv/fit_factors.py`
- Modify: `tests/test_fit_factors.py`

**Preconditions:**
- Task 2 complete
- policy validator and fingerprint tests pass

**Steps:**
- [x] Step 1: Add failing table-driven tests for common evaluation and policy-result
  fields, enum closure, finite-score validation, deterministic serialization, and
  invalid-input degradation to typed `unknown`.
- [x] Step 2: Add failing candidate-adapter tests for preferred locations,
  work-mode tokens such as `Remote` inside locations, preferred work modes,
  absent `languages`, valid empty/non-empty lists, malformed present values,
  `native`, explicit `level`, complete `read/write/speak`, incomplete dimensions,
  and duplicates.
- [x] Step 3: Implement immutable minimal records using existing language features;
  add no class hierarchy, registry, or plugin abstraction.
- [x] Step 4: Implement one Unicode NFKC, trim, whitespace-collapse, and
  `casefold()` comparison-key helper with display evidence preserved separately.
- [x] Step 5: Implement fixed CEFR ordering and deterministic candidate-language
  reduction using `native`, explicit `level`, then minimum complete
  `read/write/speak` precedence.
- [x] Step 6: Reuse configured valid work modes to remove work-mode tokens from
  geographic preferences; keep preferred work modes in candidate context but do
  not consume them in actual-location evaluation.
- [x] Step 7: Treat absent or malformed `languages` as unknown inventory and a
  valid list, including `[]`, as complete inventory.
- [x] Step 8: Add evaluator, normalizer, extraction, and policy version constants
  named in spec; no version value comes from mutable config.

**Verification:**
- [x] `python -m pytest tests/test_fit_factors.py -k "contract or context or normalize or cefr"`
- [x] Reordered and duplicate profile inputs produce byte-equivalent JSON-safe context.

**Exit Criteria:**
- both factors can use one contract family and one deterministic candidate context
  without persisted duplicate profile state

### Task 4: Implement total evaluators and projection

**Purpose:**
- implement location and language truth, absolute normalization, and one shared
  mode/status projection table for every admissible case

**Files:**
- Modify: `src/fitcv/fit_factors.py`
- Modify: `tests/test_fit_factors.py`

**Preconditions:**
- Task 3 complete
- common records, comparison keys, CEFR order, and policy objects are stable

**Steps:**
- [x] Step 1: Add failing location tests for no preferences, unrestricted remote,
  exact city, exact region, exact country, multiple matches, complete mismatch,
  partial evidence, missing evidence, malformed evidence, duplicate preferences,
  comma/semicolon tokenization, diacritics, and reordered inputs.
- [x] Step 2: Add failing language tests for no requirements, complete required
  met/unmet/unknown, partial and unknown job requirements, preferred unmet,
  unspecified level, complete inventory missing language, malformed inventory,
  candidate below/above threshold, duplicates, malformed evidence, and mixed outcomes.
- [x] Step 3: Add failing exhaustive tests over both factor IDs, all four evaluator
  statuses, and all three modes against spec projection table.
- [x] Step 4: Add cohort-invariance tests proving another job, batch order, batch
  size, minimum, maximum, percentile, or rank cannot change one job's status,
  score, ranking value, reason, or fingerprint.
- [x] Step 5: Implement exact-token location evaluation in specified order and
  select highest configured factor-internal match score.
- [x] Step 6: Implement per-language truth and weighted mean score; only confirmed
  unmet `required` requirements can produce evaluator `fail`.
- [x] Step 7: Implement one shared projection function. Factor-specific logic ends
  before projection and cannot override mode/status behavior.
- [x] Step 8: Emit deterministic reason codes and bounded evidence for pass, fail,
  unknown, and not-applicable results.

**Verification:**
- [x] `python -m pytest tests/test_fit_factors.py`
- [x] Same fact/context/policy tuple serializes identically across runs and input order changes.
- [x] No evaluator reads job cohort, ranking list, percentile, or batch statistic.

**Exit Criteria:**
- every admissible factor input returns typed output, normalization is globally
  stable, and one projection table governs both factors

### Task 5: Preserve provider location evidence

**Purpose:**
- adapt provider-native location shapes once and carry one source-neutral evidence
  structure through normalization without changing display or raw payload contracts

**Files:**
- Modify: `src/fitcv/ingest.py`
- Modify: `src/fitcv/normalize.py`
- Modify: `tests/test_ingest.py`
- Modify: `tests/test_normalize.py`

**Preconditions:**
- Task 4 complete
- GitNexus impacts for `_normalize_indeed_job`, `prepare_raw_rows`, and
  `normalize_job` reviewed immediately before edits

**Steps:**
- [x] Step 1: Add failing ingest tests for LinkedIn string location, Indeed nested
  city/region/country components, absent location, malformed nested location, and
  raw-JSON replay.
- [x] Step 2: Add failing normalize tests proving only string cleanup occurs in
  `source_location`; normalization does not geocode, alias, infer country, infer
  distance, or inject work mode.
- [x] Step 3: Add one provider-boundary helper that builds `source_location` with
  `raw_text`, raw components, and provider; reuse native provider values instead
  of reparsing `raw_json` downstream.
- [x] Step 4: Preserve current `location` display string and complete `raw_json` content.
- [x] Step 5: Carry `source_location` through `prepare_raw_rows` and `normalize_job`
  while tolerating missing and malformed inputs.

**Verification:**
- [x] `python -m pytest tests/test_ingest.py tests/test_normalize.py`
- [x] Indeed nested and LinkedIn string inputs reach one source-location shape.
- [x] Raw provider payload remains replayable and unchanged.

**Exit Criteria:**
- downstream extraction receives provider-neutral source-location evidence without
  losing original display or audit truth
### Task 6: Extract durable canonical facts

**Purpose:**
- extend existing enrich Pydantic boundary with actual-location and language facts,
  deterministic reduction, skill separation, and reuse-safe versioning

**Files:**
- Modify: `src/fitcv/enrich.py`
- Modify: `tests/test_enrich.py`

**Preconditions:**
- Task 5 complete
- GitNexus impacts for `EnrichmentOutput`, `_apply_structured_normalization`,
  `build_raw_job_fingerprint`, `build_enrich_contract_fingerprint`, and
  `merge_scraped_and_enriched` reviewed immediately before edits

**Steps:**
- [x] Step 1: Add failing structured-output tests for complete, partial, unknown,
  duplicate, malformed, missing, remote, onsite, hybrid, and multilingual cases.
- [x] Step 2: Add failing fixtures containing Python, English, German B2, and soft
  skills; prove programming skills remain and language names leave canonical
  required/preferred skill entities.
- [x] Step 3: Add failing tests for deterministic duplicate-language reduction:
  strongest requirement type, highest explicit level, stable language order, and
  preserved evidence.
- [x] Step 4: Add failing reuse tests proving changed actual-location or language
  extraction contracts invalidate old cache while unchanged contracts remain reusable.
- [x] Step 5: Extend LLM-facing `EnrichmentOutput` with bounded raw-value and
  evidence fields only; do not expose `extraction_status` to the model, create a
  second parser, or add a second LLM call.
- [x] Step 6: Compute canonical extraction status in code after Pydantic validation;
  invalid content degrades to partial or unknown, and uncertain requirements
  cannot produce confirmed `unmet`.
- [x] Step 7: Build canonical `actual_location` from provider evidence plus bounded
  extracted evidence, preserving `location_type` as work mode only.
- [x] Step 8: Build canonical `language_requirements`, reduce duplicates, and keep
  language evidence outside skill entities.
- [x] Step 9: Include source-location evidence and extraction/postprocessing
  versions in raw-job and enrich-contract fingerprints where reuse truth requires it.
- [x] Step 10: Project new facts through merge, cached-row hydration, structured
  row mapping, and JSON payload persistence without parallel storage model.

**Verification:**
- [x] `python -m pytest tests/test_enrich.py`
- [x] Complete, partial, and unknown facts serialize separately from work mode and skills.
- [x] Old enrich cache is not reused after contract-version change.

**Exit Criteria:**
- enriched rows contain durable versioned actual-location and language facts, and
  existing enrich reuse remains correct

### Task 7: Integrate symmetric rule-filter eligibility

**Purpose:**
- evaluate both factors once per job, attach canonical results, and enforce hard
  gates at existing deterministic eligibility boundary

**Files:**
- Modify: `src/fitcv/rule_filter.py`
- Modify: `tests/test_rule_filter.py`
- Modify: `src/fitcv/fit_factors.py`
- Modify: `tests/test_fit_factors.py`

**Preconditions:**
- Task 6 complete
- GitNexus impacts for `apply_rule_filters` and `store_filter_results` reviewed
  immediately before edits

**Steps:**
- [x] Step 1: Add failing tests for both factors under disabled, ranking-only, and
  hard-gate modes with pass, fail, unknown, and not-applicable evaluations.
- [x] Step 2: Add failing tests proving only hard-gated confirmed failure rejects;
  hard-gated unknown and not-applicable remain retained with diagnostics.
- [x] Step 3: Add failing tests proving ranking-only failure remains retained with
  `ranking_enabled: true`, while disabled factors never reject or emit ranking value.
- [x] Step 4: Add failing compatibility tests proving `location_type_excluded`
  remains separate and does not consume or overwrite `location_fit`.
- [x] Step 5: Extend rule-filter boundary to accept explicit candidate-fit context
  while preserving direct-call compatibility; absent context produces typed unknown.
- [x] Step 6: Evaluate each job/factor once under one policy and attach
  `fit_factor_results`, `eligibility_policy_fingerprint`,
  `eligibility_decision`, and deterministic `eligibility_reason_codes` to passed
  and rejected records.
- [x] Step 7: Convert projected hard-gate rejects into stable rule-filter reason
  codes without hiding factor evidence in generic marks.
- [x] Step 8: Keep existing selected/unselected legacy checks and marks unchanged
  outside eligibility additions.

**Verification:**
- [x] `python -m pytest tests/test_fit_factors.py tests/test_rule_filter.py`
- [x] Every retained and rejected record carries complete factor and policy identity.
- [x] No rule-filter branch recomputes evaluator truth after results are attached.

**Exit Criteria:**
- one deterministic boundary owns factor evaluation and rejection, with unknown
  safety and legacy work-mode behavior preserved

### Task 8: Preserve payload through both pipeline paths

**Purpose:**
- build candidate context once, pass complete eligibility records through main and
  staged orchestration, and prove rejected jobs never reach shortlist or ranking

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/pipeline_stage_runner.py`
- Modify: `tests/test_pipeline.py`
- Modify: `tests/test_pipeline_stage_resume_parity.py`
- Modify: `tests/test_ranking.py`

**Preconditions:**
- Task 7 complete
- GitNexus impacts for `run_pipeline`, `execute_rule_filter_stage`, and changed
  stage-transition helpers reviewed immediately before edits

**Steps:**
- [x] Step 1: Add failing main-pipeline and stage-runner tests proving full profile,
  including top-level languages, is adapted once into candidate-fit context.
- [x] Step 2: Add failing parity tests proving both paths emit identical passed
  jobs, rejected jobs, factor results, policy fingerprint, decision, reason codes,
  and marks for same inputs.
- [x] Step 3: Add failing resume/checkpoint tests proving complete eligibility
  payload survives stage-boundary serialization and staged continuation.
- [x] Step 4: Add failing boundary tests with retained, rejected, unknown,
  duplicate-URL, and empty-URL jobs; require one unique non-empty canonical
  `job_url` per rule-filter input row and prove rejected IDs never enter
  `passed_jobs`, shortlist, vector search, AI scoring, or ranking.
- [x] Step 5: Replace marks-only merge with bounded complete passed-record merge in
  both orchestration paths.
- [x] Step 6: Build candidate context immediately after full profile load and pass
  it explicitly to rule filter; create no second profile loader or persisted model.
- [x] Step 7: Keep existing shortlist and ranking functions unchanged except for
  receiving already-filtered enriched job payload.
- [x] Step 8: Add ranking regressions proving factor artifacts do not alter active
  weights, final score, sort order, or `strong | stretch | skip` labels.

**Verification:**
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py`
- [x] `python -m pytest tests/test_ranking.py`
- [x] Main and stage-runner eligibility payloads are structurally and value-equal.

**Exit Criteria:**
- both orchestration paths are symmetric, rejected jobs stop before ranking, and
  Phase 1 causes no ranking or fit-label drift
### Task 9: Add explicit SQLite eligibility columns

**Purpose:**
- persist eligibility evidence as owned schema fields with additive migration and
  null-safe compatibility

**Files:**
- Modify: `src/fitcv_cp/sqlite_store.py`
- Modify: `src/fitcv/rule_filter.py`
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_rule_filter.py`

**Preconditions:**
- Task 8 complete
- GitNexus impacts for `_ensure_local_rule_filter_results_table`,
  `list_filter_results_for_run`, and `store_filter_results` reviewed immediately
  before edits

**Steps:**
- [x] Step 1: Add failing schema-upgrade tests starting from old
  `rule_filter_results` table and proving additive creation of
  `fit_factor_results_json`, `eligibility_policy_fingerprint`,
  `eligibility_decision`, and `eligibility_reason_codes_json`.
- [x] Step 2: Add failing round-trip tests for retained, rejected, unknown,
  not-applicable, and legacy null rows.
- [x] Step 3: Add failing tests proving factor results and policy identity are not
  serialized into `marks_json`.
- [x] Step 4: Extend table creation and idempotent `ALTER TABLE` migration using
  native SQLite only; add no ORM or migration framework.
- [x] Step 5: Add one `sqlite_store.py` replace operation owning migration,
  delete/insert SQL, deterministic JSON encoding, and transaction boundaries.
- [x] Step 6: Reduce `rule_filter.store_filter_results` to domain-row construction
  plus delegation; keep SQL and JSON codecs out of `rule_filter.py`.
- [x] Step 7: Update control-plane reader to decode factor-result and reason-code
  JSON while preserving existing `passed`, `reasons`, and `marks` outputs.
- [x] Step 8: Verify repeated schema initialization and repeated reads are safe.

**Verification:**
- [x] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_rule_filter.py -k "filter or eligibility"`
- [x] Old and new tables both read without data loss or exception.
- [x] Complete eligibility JSON round-trips exactly for passed and rejected rows.

**Exit Criteria:**
- SQLite durably owns eligibility results in explicit columns and remains backward
  compatible with existing local databases

### Task 10: Synchronize source docs and generated metadata

**Purpose:**
- align human-owned architecture contracts with implemented behavior, then rebuild
  managed outputs

**Files:**
- Modify: `docs/architecture.md`
- Modify: `docs/configuration.md`
- Modify: `docs/pipeline.md`
- Modify: `docs/stages/normalize.source.yaml`
- Modify: `docs/stages/enrich.source.yaml`
- Modify: `docs/stages/rule_filter.source.yaml`
- Modify: `docs/features/cv_system/feature.source.yaml`
- Generate: `docs/stages/normalize.yaml`
- Generate: `docs/stages/enrich.yaml`
- Generate: `docs/stages/rule_filter.yaml`
- Generate: `docs/features/cv_system/cv_system.yaml`
- Generate: `docs/features/cv_system/lineage.generated.yaml`
- Generate: `docs/features/inspection_debugging/inspection_debugging.yaml`
- Generate: `docs/features/inspection_debugging/lineage.generated.yaml`
- Generate: `docs/generated/architecture_dag.yaml`
- Generate: `docs/generated/capability_lineage.yaml`
- Generate: `docs/generated/planning_lineage.yaml`

**Preconditions:**
- Task 9 complete
- code and focused tests define final implemented contract

**Steps:**
- [x] Step 1: Document actual geography, work mode, provider source evidence,
  candidate-fit context, language levels, policy modes, unknown behavior, and
  hard-gate ordering in cross-cutting docs.
- [x] Step 2: State explicitly that Phase 1 emits ranking-ready values but Phase 3
  owns score composition and fit-label migration.
- [x] Step 3: Update normalize, enrich, and rule-filter human-owned stage sources
  with exact inputs, outputs, boundaries, and evidence ownership.
- [x] Step 4: Update CV-system feature source with bounded factor-evidence support;
  do not hand-edit generated feature contracts or lineage.
- [x] Step 5: Regenerate planning lineage after plan/spec metadata changes.
- [x] Step 6: Regenerate architecture metadata from stage and feature sources.
- [x] Step 7: Inspect generated diffs for only expected feature, stage, lineage,
  and discovery changes.
- [x] Step 8: Search active config and code for second policy owner, copied numeric
  defaults, cohort normalization, location/work-mode conflation, or language
  requirements re-entering skill lists.

**Verification:**
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python tools/docs/generate_architecture_metadata.py`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/validate_planning_lifecycle.py`

**Exit Criteria:**
- human-owned docs and generated metadata describe implemented SSOT and symmetry
  contracts without generated-file authority drift

### Task 11: Run final verification and scope audit

**Purpose:**
- prove Phase 1 behavior, ranking non-regression, document lifecycle, and bounded
  change scope before completion

**Files:**
- Verify: all targets in plan frontmatter
- Inspect: `docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md`
- Inspect: `docs/superpowers/plans/2026-07-15-17-22-fitcv-inverse-optimization-phase-1-location-language-eligibility-plan.md`

**Preconditions:**
- Tasks 1 through 10 complete
- no unresolved focused-test failure remains

**Steps:**
- [x] Step 1: Run focused config, ingest, normalize, enrich, factor, rule-filter,
  pipeline, SQLite, and ranking test groups.
- [x] Step 2: Run fast hook, planning lifecycle, architecture check, repo-contract,
  and whitespace validation.
- [x] Step 3: Run `gitnexus_detect_changes` on all uncommitted changes and inspect
  affected processes; treat stale results as advisory and source/tests as authority.
- [x] Step 4: Review `git diff --stat`, `git diff --name-only`, and targeted diffs;
  confirm `.tmp-tests/` and unrelated source remain untouched.
- [x] Step 5: Search for forbidden additions: BM25/BM25F restoration, cohort score
  normalization, new dependency, geocoder, fuzzy matcher, plugin framework, policy
  DSL, duplicated eligibility config, or ranking composition changes.
- [x] Step 6: Review implementation against every Phase 1 acceptance proof and
  completion criterion; do not mark plan complete while any child task is open.

**Verification:**
- [x] `python -m pytest tests/test_config.py tests/test_ingest.py tests/test_normalize.py`
- [x] `python -m pytest tests/test_enrich.py tests/test_fit_factors.py tests/test_rule_filter.py`
- [x] `python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py`
- [x] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_ranking.py`
- [x] `python scripts/generate_planning_lineage.py`
- [x] `python tools/docs/generate_architecture_metadata.py`
- [x] `python scripts/hooks/run_validator.py --fast`
- [x] `python scripts/validate_planning_lifecycle.py`
- [x] `python tools/docs/generate_architecture_metadata.py --check`
- [x] `python scripts/validate_repo_contracts.py --fast`
- [x] `git diff --check`

**Exit Criteria:**
- all commands exit zero, GitNexus scope review has no unexplained high-risk
  process impact, and every Phase 1 proof target has evidence

## Verification

Final artifact-level verification:

```powershell
python -m pytest tests/test_config.py tests/test_ingest.py tests/test_normalize.py
python -m pytest tests/test_enrich.py tests/test_fit_factors.py tests/test_rule_filter.py
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py
python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_ranking.py
python scripts/generate_planning_lineage.py
python tools/docs/generate_architecture_metadata.py
python scripts/hooks/run_validator.py --fast
python scripts/validate_planning_lifecycle.py
python tools/docs/generate_architecture_metadata.py --check
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Required behavioral evidence:

- provider location evidence remains replayable and provider-neutral downstream
- actual location, work mode, and language requirements serialize separately
- language requirements do not contaminate canonical skill lists
- both factors cover every status/mode pair through one projection table
- same fact/context/policy tuple is invariant to cohort and input order
- hard gates reject only confirmed failures
- rejected jobs never enter shortlist or ranking inputs
- main pipeline and stage runner preserve identical eligibility payloads
- SQLite round-trips factor results and policy identity outside `marks_json`
- existing ranking score, order, and `strong | stretch | skip` labels do not change
- generated docs match human-owned stage and feature sources
- no second eligibility-policy owner or copied numeric policy defaults exist

Rollback boundaries:

- config or evaluator failure: revert Tasks 2 through 4 together; do not leave
  loaded policy without executable validation
- extraction failure: revert Tasks 5 and 6 together; preserve existing display
  location, work mode, skills, and enrich reuse contract
- orchestration failure: revert Tasks 7 through 9 together; do not retain partial
  payload merge or half-migrated persistence
- documentation failure: fix source YAML or cross-cutting docs, regenerate, and
  never patch generated contracts directly

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. every existing symbol edit has preceding upstream GitNexus impact evidence
5. all factor admissible cases have deterministic test coverage
6. hard-gated rejects are proven absent from downstream ranking inputs
7. ranking regressions prove no Phase 1 score, order, or fit-label change
8. SQLite evidence round-trips through explicit owned columns with
   `sqlite_store.py` as sole SQL/codec owner
9. human-owned docs and generated outputs are synchronized
10. final verification commands exit zero

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-15-16-40-fitcv-inverse-optimization-phase-1-location-language-eligibility-spec.md`
- `docs/superpowers/specs/2026-07-14-22-25-fitcv-inverse-optimization-master-ssot-symmetry-spec.md`
- `docs/operating_system/governance/repo-governance.md`
- `docs/operating_system/lifecycle/doc-system-lifecycle.md`
- `docs/operating_system/templates/implementation-plan-template.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>