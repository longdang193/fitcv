---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
contract_version: "1"
name: fitcv-stepstone-input-adapter
targets:
  - src/fitcv/contracts.py
  - src/fitcv/ingest.py
  - src/fitcv/normalize.py
  - src/fitcv/pipeline.py
  - tests/test_ingest.py
  - tests/test_normalize.py
  - tests/test_pipeline.py
  - docs/job-data-input.md
  - README.md
---

# FitCV Stepstone Input Adapter

## Goal

Accept LinkedIn, Indeed, and Stepstone raw JSON records through one source-adapter boundary while preserving raw input, keeping downstream stages source-agnostic, and preventing incomplete Stepstone listing text from producing unsupported CV output.

## Implementation Outcomes

### Symmetric raw-input adapters

`src/fitcv/ingest.py` owns one adapter registry with detection, validation, and canonical mapping for LinkedIn, Indeed, and Stepstone. Existing LinkedIn and Indeed behavior remains compatible. Mixed-source arrays work without filename-based branching.

### Canonical job contract

`src/fitcv/contracts.py` owns generic canonical fields and quality metadata. Source adapters map provider fields into the same snake-case shape. Raw records remain unchanged in the immutable run input and `raw_json` audit field.

### Stepstone support and safe generation

Stepstone relative URLs become stable absolute URLs, provider IDs become stable source identity, `textSnippet` remains explicitly incomplete source text, and missing provider fields remain empty rather than fabricated. Jobs with incomplete descriptions do not enter CV generation; they receive existing `review_required` output semantics with a deterministic reason code.

### Documentation and regression proof

`docs/job-data-input.md` and `README.md` describe source-neutral input behavior. Focused tests cover adapter resolution, Stepstone mapping, URL canonicalization, mixed-source inputs, deduplication, raw preservation, and generation blocking.

## Explicit Non-Goals

- No new upload mode, UI selector, filename convention, or source configuration file.
- No Stepstone detail-page fetch in this change.
- No invented `contract_type`, `experience_level`, salary, or full description values.
- No database schema migration; existing `raw_jobs` columns and raw JSON persistence remain compatible.
- No changes to ranking, enrichment, filtering, or CV prompt contracts beyond consuming generic canonical metadata.
- No edits to unrelated dirty files already present in the workspace.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`, `skill-plan-document-reviewer`, `skill-executing-plans`, `skill-verification-before-completion`
- Isolation: `current workspace`; preserve existing dirty changes
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit listed plan-task files, add focused tests, update listed documentation, run declared local checks, inspect local input fixtures
- User-approval actions: dependency installation, authentication, branch/worktree changes, commits, push, merge, publication, destructive recovery, cleanup, unrelated-file edits, scope changes
- Parallel ownership: none; `src/fitcv/ingest.py` and shared tests are sequentially owned
- Sequential fallback: `Task 1 → Task 2 → Task 3 → Task 4`

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `main`
- Base commit: `8fd30651`
- Expected workspace: `named preserved changes`; existing modified, deleted, and untracked files remain untouched
- Next action: retain proposed status until final verification is clean
- Blockers: `none`

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `complete` | current | `lead` | none | focused ingest tests | `71 passed, 1 skipped` in ingest/normalize focus |
| Task 2 | `complete` | current | `lead` | Task 1 | Stepstone adapter and mixed-input tests | Stepstone mapping tests pass; 200-row fixture smoke passes |
| Task 3 | `complete` | current | `lead` | Task 2 | normalization and CV-generation gate tests | generation gate regression passes; incomplete rows emit review-required debug records |
| Task 4 | `partial` | current | `lead` | Task 3 | final focused and repository checks | `git diff --check` and smoke pass; full focus has one unrelated pre-existing late-stage failure |

## Task Breakdown

### Task 1: Establish source-adapter registry

**Purpose:**
- Replace the current LinkedIn/Indeed conditional split with one explicit adapter boundary without changing accepted LinkedIn or Indeed behavior.

**Task Function:**
- Extract existing source detection and mapping into symmetric registry entries. Keep raw input preservation in `canonicalize_jobs`.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: bounded Python refactor with compatibility risk.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead-controlled focused tests.

**Specification Coverage:**
- One SSOT adapter registry.
- Source detection per record, not filename.
- Exactly one adapter or explicit validation error.
- Existing LinkedIn and Indeed behavior preserved.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `src/fitcv/ingest.py:canonicalize_jobs`, `validate_job_schema`, `_is_indeed_job`, `snake_case_keys`, `build_source_location`, `_normalize_indeed_job`
- Modify: `src/fitcv/contracts.py` canonical field constants; `src/fitcv/ingest.py` adapter definition, registry, resolver, validation, and compatibility wrappers
- Verify: `tests/test_ingest.py` existing LinkedIn/Indeed validation, normalization, and raw-preservation tests

**Dependencies:**
- Approved Stepstone input contract from this plan.

**Authority:**
- Preauthorized local actions: edit `src/fitcv/contracts.py`, `src/fitcv/ingest.py`, and focused ingest tests; run declared Python checks.
- Stop for: changed raw snapshot semantics, new dependency, database migration, or unrelated dirty-file conflict.

**Steps:**
- [x] Step 1: Define generic canonical metadata names for `source_provider`, `source_job_id`, `description_source`, and `description_complete` without making source-specific fields globally required.
- [x] Step 2: Introduce one adapter record shape with `source_id`, `detect`, `validate`, and `to_canonical` callables; register current LinkedIn and Indeed mappings using existing behavior.
- [x] Step 3: Make `validate_job_schema` resolve the adapter and make `snake_case_keys` delegate to it; preserve `canonicalize_jobs` raw-record serialization and digest behavior.
- [x] Step 4: Add focused tests proving existing LinkedIn and Indeed fixtures produce current canonical fields and unknown shapes fail with an explicit supported-source error.

**Verification:**
- [ ] `pytest -q tests/test_ingest.py tests/test_normalize.py`
- Expected: all existing LinkedIn/Indeed tests pass; raw canonical JSON remains byte-stable; unknown source errors identify supported adapters.

**Exit Criteria:**
- Adapter registry replaces source conditionals at the ingest boundary, with no Stepstone behavior yet and no downstream source branches.

### Task 2: Add Stepstone canonical mapping

**Purpose:**
- Map the supplied Stepstone records into the existing canonical job shape while retaining source evidence and stable identity.

**Task Function:**
- Implement one Stepstone adapter using the actual `dataset_stepstone-search-cheerio-ppr` record shape.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: bounded source mapping with URL and sparse-content edge cases.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: focused fixture assertions provide direct proof.

**Specification Coverage:**
- Stepstone detection by record shape, not filename.
- Relative URL conversion and tracking-query removal.
- `id` as provider job identity.
- `textSnippet` mapped as incomplete description.
- Missing fields remain empty; raw record remains preserved.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `data/dataset_stepstone-search-cheerio-ppr_2026-09-17_14-16-15-374.json`; `src/fitcv/ingest.py:build_source_location`, `prepare_raw_rows`
- Modify: `src/fitcv/ingest.py` Stepstone detector, validator, URL canonicalizer, source-location builder, and canonical mapper; `tests/test_ingest.py`
- Verify: `tests/test_ingest.py` Stepstone fixture tests and actual 200-row input smoke check

**Dependencies:**
- Task 1 adapter registry.

**Authority:**
- Preauthorized local actions: edit Stepstone adapter code and ingest tests; read local JSON fixtures; run focused Python checks.
- Stop for: external HTTP fetch, source contract requiring guessed semantics, or any change to user-uploaded files.

**Steps:**
- [ ] Step 1: Detect Stepstone records using stable keys such as `harmonisedId`, `workFromHome`, and `jobBenefitsHtml` without relying on dataset filename.
- [ ] Step 2: Canonicalize `url` against `https://www.stepstone.de` and remove `rltr` tracking parameters while preserving original raw JSON.
- [ ] Step 3: Map `id`, company fields, location, `datePosted`, `textSnippet`, and work-from-home code into canonical fields; set `description_source` to `text_snippet` and `description_complete` to `false`. Keep `jobBenefitsHtml`, labels, skills, and the raw work-from-home code source-owned inside preserved `raw_json`; do not add canonical or storage fields without a downstream consumer.
- [ ] Step 4: Keep incomplete `unifiedSalary` values unavailable rather than inventing salary data; leave absent `contract_type` and `experience_level` empty.
- [ ] Step 5: Add tests for one representative Stepstone row, malformed optional fields, relative URL output, source location provider, source identity, and raw JSON preservation.

**Verification:**
- [ ] `pytest -q tests/test_ingest.py`
- [ ] `python -c "import json; from fitcv.ingest import snake_case_keys; p='data/dataset_stepstone-search-cheerio-ppr_2026-09-17_14-16-15-374.json'; rows=json.load(open(p, encoding='utf-8')); assert len(rows)==200; mapped=[snake_case_keys(row) for row in rows]; assert all(row['job_url'].startswith('https://www.stepstone.de/') and row['title'].strip() for row in mapped)"`
- Expected: 200 rows adapt without network access; canonical URLs are absolute and tracking-stable; Stepstone rows retain incomplete-content metadata.

**Exit Criteria:**
- Supplied Stepstone file passes ingestion and produces canonical records compatible with existing raw-row preparation.

### Task 3: Apply generic identity, quality, and generation gates

**Purpose:**
- Make downstream behavior symmetric: all sources use canonical identity and content-quality metadata, while incomplete Stepstone listings cannot produce CVs.

**Task Function:**
- Update shared normalization deduplication and the existing CV-generation dispatch boundary; do not add Stepstone-specific pipeline branches.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: cross-stage behavior change with deterministic failure-path proof.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: direct boundary tests in existing pipeline suites.

**Specification Coverage:**
- Prefer `source_provider + source_job_id`, then canonical URL, for identity.
- Preserve current near-duplicate behavior.
- Incomplete description blocks generation with existing `review_required` status and reason code.

**Required Skills:**
- `skill-code-standards`, `skill-test-driven-development`, `skill-backend-verification`

**Files And Symbols:**
- Inspect: `src/fitcv/normalize.py:deduplicate_jobs`, `_job_url`, `_near_duplicate_key`; `src/fitcv/pipeline.py:generation_ready_records`; `src/fitcv/late_stage_contract.py:CV_GENERATION_REVIEW_REQUIRED_STATUS`
- Modify: `src/fitcv/normalize.py` identity selection and metadata preservation; `src/fitcv/pipeline.py` CV-generation dispatch guard and review-required diagnostics; `tests/test_normalize.py`, `tests/test_pipeline.py`
- Verify: existing stage artifacts and generation result status projections

**Dependencies:**
- Task 2 Stepstone canonical fields.

**Authority:**
- Preauthorized local actions: edit listed normalization, pipeline, and test symbols; run focused backend tests.
- Stop for: new status taxonomy, persistence schema migration, changed ranking semantics, or changed existing generation outcomes.

**Steps:**
- [x] Step 1: Change exact dedupe identity to use source identity when available and canonical URL otherwise; keep insertion order and existing near-duplicate key behavior.
- [x] Step 2: Preserve `source_provider`, `source_job_id`, `description_source`, and `description_complete` through normalization and stage snapshots.
- [x] Step 3: At `src/fitcv/pipeline.py:generation_ready_records`, split records with `description_complete == false` before generator work. Append one skipped-generation debug record to `cv_generation_debug_records` per job with `source_stage = "cv_generation"`, `stage_owned_subreason = "review_required"`, `status = "review_required"`, `review_required_reason_code = "job_description_incomplete"`, the job snapshot, and the existing outcome/error fields; exclude those records from generator invocation.
- [x] Step 4: Add mixed-source normalization tests and pipeline tests proving complete LinkedIn/Indeed jobs still generate while incomplete Stepstone jobs remain visible and ungenerated.

**Verification:**
- [ ] `pytest -q tests/test_normalize.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py`
- [ ] Pipeline assertions inspect `cv_generation_debug_records` and confirm incomplete jobs retain `source_stage`, `stage_owned_subreason`, and `review_required_reason_code`.
- Expected: mixed-source deduplication is deterministic; incomplete-content records produce `review_required`; existing complete-content generation tests remain green.

**Exit Criteria:**
- Shared pipeline consumes canonical metadata only; no downstream code checks `stepstone` source ID.

### Task 4: Align maintained documentation and complete verification

**Purpose:**
- Make the new input contract discoverable and verify the full implementation against repository truth.

**Task Function:**
- Update canonical data-contract documentation, then run final checks without touching unrelated files.

**Template Profile:**
- Controller-selected: `unresolved while task is pending`
- Selection basis: documentation and release-readiness verification.

**Validator Profile:**
- Controller-selected: `none`
- Selection basis: lead controller runs final commands and reconciles evidence.

**Specification Coverage:**
- Documentation names raw-source preservation, adapter registry, Stepstone limitations, and generic quality gating.
- Final proof covers ingestion, normalization, pipeline behavior, and documentation consistency.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Inspect: `docs/job-data-input.md`, `README.md`, `src/fitcv/contracts.py`, `src/fitcv/ingest.py`, `src/fitcv/normalize.py`, `src/fitcv/pipeline.py`
- Modify: `docs/job-data-input.md`, `README.md`
- Verify: `git diff --check`, focused pytest suites, actual Stepstone fixture smoke check, and `git status --short`

**Dependencies:**
- Tasks 1–3 complete.

**Authority:**
- Preauthorized local actions: edit listed documentation and run final local verification commands.
- Stop for: generated-surface regeneration request, unrelated formatting churn, failing pre-existing tests that obscure changed behavior, or any need to clean/discard workspace files.

**Steps:**
- [x] Step 1: Replace LinkedIn-only README wording with source-neutral JSON input wording and list supported adapters.
- [x] Step 2: Update `docs/job-data-input.md` with adapter ownership, Stepstone field mapping, relative URL handling, incomplete-text semantics, and no-filename-detection rule.
- [x] Step 3: Run final checks and record fresh outputs in plan evidence without changing plan status to completed.

**Verification:**
- [ ] `pytest -q tests/test_ingest.py tests/test_normalize.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py`
- [ ] `git diff --check`
- [ ] `python -c "import json; from fitcv.ingest import snake_case_keys; p='data/dataset_stepstone-search-cheerio-ppr_2026-09-17_14-16-15-374.json'; rows=json.load(open(p, encoding='utf-8')); assert len(rows)==200; mapped=[snake_case_keys(row) for row in rows]; assert all(row['job_url'].startswith('https://www.stepstone.de/') and row['title'].strip() for row in mapped)"`
- Expected: all changed behavior passes; documentation matches code; unrelated dirty files remain present and untouched.

**Exit Criteria:**
- Implementation evidence is complete enough for `skill-verification-before-completion`; plan remains `proposed` until that skill returns `verified` after execution.

## Verification

- `pytest -q tests/test_ingest.py tests/test_normalize.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py`
- `git diff --check`
- Read-only 200-row Stepstone fixture smoke check with no network access.
- `git status --short` confirms only plan-task files changed beyond preserved pre-existing workspace state.

## Completion Criteria

The plan is ready for completion verification when:

1. LinkedIn, Indeed, and Stepstone raw records resolve through one adapter registry.
2. Raw input snapshots remain unchanged and auditable.
3. Stepstone records normalize to stable absolute URLs and canonical metadata.
4. Mixed-source normalization and deduplication remain deterministic.
5. Incomplete Stepstone descriptions cannot enter CV generation and remain visible as `review_required`.
6. Documentation names one canonical contract and no source-specific downstream branches.
7. Focused tests, actual Stepstone smoke check, and `git diff --check` pass.
8. Existing unrelated dirty files remain untouched.

The plan may be marked `completed` only when `skill-verification-before-completion` runs fresh final verification, confirms repository evidence, finds no unresolved required task or scope deviation, and returns `verified`.
