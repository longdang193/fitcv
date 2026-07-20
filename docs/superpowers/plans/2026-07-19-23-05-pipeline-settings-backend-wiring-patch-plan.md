---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: pipeline-settings-backend-wiring-patch
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv/gap_analysis.py
  - config/policy/eligibility.yaml
  - tests
---

# Pipeline Settings Backend Wiring Patch Plan

## Goal

Replace production Pipeline settings prototype state with one canonical backend resource, one serialized mutation contract, and verified stage consumption for settings that already have approved backend semantics. Preserve existing system-owned CV model, preset, and page-limit behavior outside the Pipeline resource; remove unsupported mock-only controls instead of inventing backend owners.

Contract inputs:

- UI and interaction reference: `docs/fitcv-settings-ui-prototype.html`.
- Prototype scope record: `docs/superpowers/plans/2026-07-19-screening-runtime-settings-revision-plan.md`.
- CV model ownership: `docs/superpowers/specs/2026-04-29-settings-agentic-vs-cv-generation-clarity-spec.md`.
- Integration evidence: `docs/superpowers/plans/audit/2026-07-19-22-31-01-pipeline-settings-backend-wiring/report.md`.
- Backend schema, effective config, SQLite overrides, control-plane routing, and stage consumers remain runtime truth.

## Scope Decisions

- Production exposes only settings with an existing canonical backend owner and observable consumer.
- `Skip Incomplete Listings` stays absent until a separate specification defines its completeness predicate, exclusion reason, ordering, and owner.
- Screening exposes one `Location & Work Mode` control backed by `location_type_excluded`; no new `location_preference_mismatch` rule code is added.
- `Require Manual Review` stays absent. Existing proposal, apply, promote, and reuse controls keep their explicit permission or automation semantics.
- Runtime exposes Enrichment Delay/Batch/Concurrency and Ranking, CV Analysis, and CV Generation Delay/Concurrency. No new batch-size setting or scheduler is added for the latter three stages.
- `cv_generation_model`, `cv_preset`, and `cv_max_pages` stay outside the Pipeline JSON resource. Existing config, hidden compatibility, metadata, and run-provenance behavior remain unchanged by this patch.
- Gap Thresholds leave editable settings, stored overrides, policy config, and Pipeline UI. Fixed classification behavior remains owned by `src/fitcv/gap_analysis.py`.
- Existing `/settings` and HTML routes remain compatibility surfaces; new production UI uses `/settings/pipeline` and all writes delegate to the same mutation function.

## Implementation Outcomes

### Canonical Pipeline resource

`GET /settings/pipeline` returns schema-derived Pipeline rows, effective values, defaults, override sources, disabled reasons, and warnings without copying backend defaults into JavaScript.

### Serializable persistence

PATCH, reset, and compatibility HTML writes perform read, merge, validation, insert/delete, and commit inside one SQLite `BEGIN IMMEDIATE` transaction. Concurrent requests cannot leave an invalid effective state.

### Existing consumer ownership

Saved values alter current canonical consumers. Runtime work remains in `src/fitcv/pipeline.py` and existing stage modules; this patch adds no second scheduler or batch abstraction.

### Production UI parity within backend scope

Production Settings reuses approved prototype components and interactions for supported controls. Mock-only rows are intentionally absent and documented by tests.

### Deprecated cleanup without data loss

Gap Threshold settings are retired completely. CV model, preset, and page-limit ownership is preserved outside Pipeline rather than migrated into an unused settings path.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-systematic-debugging`, `skill-verification-before-completion`, `ui-ux-pro-max`
- Isolation: optional worktree recommended
- Parallel ownership: none; schema, store, API, pipeline, and template changes share contracts
- Sequential fallback: schema projection, serialized persistence, consumers, cleanup, frontend, integration proof

## Task Breakdown

### Task 1: Define canonical Pipeline projection

**Purpose:**
- Make backend schema sole owner of defaults, validation, dependencies, warnings, and Pipeline eligibility.

**Specification Coverage:**
- Supported controls only; merged-state invariants; no mock-only backend fields; no CV system-owner leakage into Pipeline.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv_cp/settings_schema.py:SETTINGS_SCHEMA`, `_derive_ranking_groups`, `_derive_cv_groups`, `validate_settings`
- Add: `merge_and_validate_settings`, `derive_settings_warnings`, `settings_disabled_reasons`, `pipeline_settings_projection`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`

**Dependencies:**
- `settings_schema_with_runtime_defaults()` remains baseline owner.
- `rule_filter.selected_filters` remains list SSOT; boolean rows are projections, not new stored keys.

**Steps:**
- [ ] Add failing tests for one-key changes validated against effective sibling values.
- [ ] Define one Pipeline projection for supported direct rows, managed groups, mirrors, and selected-filter membership controls.
- [ ] Add missing selectable screening projection metadata without adding a new rule-filter code.
- [ ] Enforce pool order, fit-label order, weight totals, Education-or-Experience, semantic parent dependencies, numeric ranges, and Pipeline key ownership against merged effective state.
- [ ] Derive warnings and disabled reasons from effective backend values.
- [ ] Remove Gap Thresholds from `SETTINGS_SCHEMA` and editable registries.
- [ ] Assert `cv_generation_model`, `cv_preset`, `cv_max_pages`, unsupported stage batch sizes, `Skip Incomplete Listings`, and `Require Manual Review` are absent from the Pipeline projection.

**Verification:**
- [ ] `$env:PYTHONPATH='src'; python -m pytest tests/test_fitcv_cp/test_settings_schema.py -q`
- Expected: projection ownership, merged validation, warnings, disabled reasons, and exclusions pass.

**Exit Criteria:**
- Every exposed Pipeline row maps to one canonical stored key or one explicit schema-derived projection.

### Task 2: Add serialized Pipeline mutation API

**Purpose:**
- Give direct controls, dialogs, resets, and compatibility writes one concurrency-safe persistence boundary.

**Specification Coverage:**
- Load, save, restart, reset, invalid no-write, concurrent safety, and compatibility preservation.

**Required Skills:**
- `skill-test-driven-development`
- `skill-systematic-debugging`

**Files And Symbols:**
- Modify: `src/fitcv_cp/settings_store.py:save_setting`, `save_settings_group`, `load_active_settings`
- Add: `mutate_settings_atomically`
- Modify: `src/fitcv_cp/app.py:get_settings_view`, existing HTML settings handlers
- Add: `get_pipeline_settings`, `patch_pipeline_settings`, `reset_pipeline_settings`
- Verify: `tests/test_fitcv_cp/test_settings_store.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 projection and merged validation helpers.

**Steps:**
- [ ] Add failing tests for atomic changes, reset, fresh-store reload, rollback, and two concurrent relational updates.
- [ ] Implement `mutate_settings_atomically` with one SQLite connection and `BEGIN IMMEDIATE`; load latest rows, apply resets and changes, validate effective state, write or delete, and commit once.
- [ ] Add `GET /settings/pipeline` returning `schema`, `values`, `defaults`, `sources`, `disabled_reasons`, and `warnings`.
- [ ] Add `PATCH /settings/pipeline` with `changes`; reject unknown, metadata-only, excluded, deprecated, and wrong-owner keys.
- [ ] Add `POST /settings/pipeline/actions/reset` with explicit owner-page keys; mirrors never own reset keys.
- [ ] Route existing single-key, group, section, and HTML writes through `mutate_settings_atomically` while preserving their response formats.
- [ ] Preserve existing `GET /settings` response shape for compatibility.

**Verification:**
- [ ] `$env:PYTHONPATH='src'; python -m pytest tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py -q -k "settings and (pipeline or atomic or concurrent or reset or effective or compatibility)"`
- Expected: invalid or racing changes never commit an invalid effective state; reset restores baseline; compatibility routes still work.

**Exit Criteria:**
- One serialized store mutation owns every production settings write.

### Task 3: Wire supported consumers and projections

**Purpose:**
- Prove supported Pipeline values alter existing canonical consumers without new runtime concepts.

**Specification Coverage:**
- Screening membership, managed groups, supported runtime controls, reuse controls, and explicit synonym permissions.

**Required Skills:**
- `skill-test-driven-development`
- `skill-systematic-debugging`

**Files And Symbols:**
- Modify: `src/fitcv/enrich.py:enrich_batch`
- Modify: `src/fitcv/agentic_cv_analysis.py:_cv_analysis_sleep_secs`
- Modify: `src/fitcv/agentic_cv_generation.py:_cv_generation_sleep_secs`
- Inspect: `src/fitcv/pipeline.py:_cv_analysis_stage_concurrency`, CV Analysis and CV Generation executor setup
- Modify: `src/fitcv_cp/synonym_proposals.py:resolve_synonym_management_mode`, `apply_synonym_management_defaults`
- Verify: `tests/test_enrich.py`, `tests/test_rule_filter.py`, `tests/test_ai_score.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Tasks 1-2 canonical projection and persistence.

**Steps:**
- [ ] Add stage-consumption tests using persisted settings through effective run config rather than direct ad hoc config only.
- [ ] Project Screening toggles into one complete `rule_filter.selected_filters` list and prove each supported membership changes only its existing reason code.
- [ ] Replace Enrichment direct alias reads and CV Analysis/CV Generation local sleep lookups with `get_stage_runtime_value`, `get_stage_runtime_sleep_secs`, or `get_stage_runtime_concurrency`; keep `enrichment_*` and `rerank_sleep_secs` as read-only compatibility fallbacks at the existing config-helper boundary.
- [ ] Keep Ranking scheduling in `run_ai_scoring` and CV Analysis/CV Generation concurrency in `src/fitcv/pipeline.py`; do not add batch windows.
- [ ] Test Factor Weights, Preference Fit, lexical/semantic pairs, Included Sections, supported runtime groups, and reuse settings through the Pipeline API.
- [ ] Enforce Semantic Alignment dependency and Education-or-Experience in merged backend validation; prove existing runtime config validation rejects invalid composition.
- [ ] Bind synonym reuse only to `reuse.synonym_triage.enabled`; remove legacy dual writes while retaining read-only compatibility fallback.
- [ ] Keep proposal, apply, and promote controls mapped to their existing explicit fields; do not synthesize a manual-review inverse.

**Verification:**
- [ ] `$env:PYTHONPATH='src'; python -m pytest tests/test_enrich.py tests/test_rule_filter.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_worker_job.py -q -k "stage_runtime or selected_filter or weight or semantic_alignment or included_sections or reuse or synonym"`
- Expected: every supported row has one owner and observable existing-stage behavior; no new scheduler or rule code exists.

**Exit Criteria:**
- No supported Pipeline row remains UI-only or cross-wired.

### Task 4: Retire Gap Threshold settings only

**Purpose:**
- Remove obsolete mutable Gap Threshold ownership without altering system-owned CV configuration.

**Specification Coverage:**
- Gap Thresholds absent from API, storage, config projection, UI, and obsolete tests; classification behavior preserved.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv/gap_analysis.py:classify_fit`
- Modify: `config/policy/eligibility.yaml`
- Verify: `tests/test_gap_analysis.py`, `tests/test_config.py`, `tests/test_fitcv_cp/test_settings_schema.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Tasks 1-2 define exclusion and stale-row cleanup behavior.

**Steps:**
- [ ] Add fixtures containing stored Gap Threshold rows.
- [ ] Remove Gap Threshold schema, group, validation, config, and API surfaces.
- [ ] Keep fixed classification constants in `src/fitcv/gap_analysis.py` and test behavior rather than mutability.
- [ ] Let existing invalid-row cleanup remove now-unknown Gap Threshold rows; add idempotent reload proof.
- [ ] Assert Pipeline GET, PATCH, and reset exclude or reject Gap Threshold keys.
- [ ] Assert `cv_generation_model`, `cv_preset`, and `cv_max_pages` retain existing non-Pipeline behavior and stored values.

**Verification:**
- [ ] `$env:PYTHONPATH='src'; python -m pytest tests/test_gap_analysis.py tests/test_config.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py -q -k "gap_threshold or pipeline or cv_generation_model or cv_preset or cv_max_pages"`
- [ ] `rg -n "gap_thresholds\." src/fitcv_cp/settings_schema.py config/policy/eligibility.yaml src/fitcv_cp/templates/settings.html`
- Expected: tests pass; grep has no matches; system-owned CV settings remain unchanged outside Pipeline.

**Exit Criteria:**
- Gap Threshold settings cannot load, save, reset, or influence runtime through mutable paths; unrelated CV owners remain intact.

### Task 5: Wire production UI to Pipeline resource

**Purpose:**
- Implement approved interaction patterns for supported production controls without a second defaults map.

**Specification Coverage:**
- Supported pages, toggles, dialogs, disabled behavior, warnings/errors, mirrors, navigation, and page-scoped reset.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-test-driven-development`

**Files And Symbols:**
- Inspect: `docs/fitcv-settings-ui-prototype.html:PAGES`
- Inspect: `docs/pipeline-settings-page-suggestions.md`
- Modify: `src/fitcv_cp/app.py:_build_settings_context`
- Modify: `src/fitcv_cp/templates/settings.html`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Tasks 1-4 finalize response shape, supported rows, and exclusions.

**Steps:**
- [ ] Add failing render/API tests for every projected row, managed group, mirror, and excluded mock-only label.
- [ ] Reuse existing production template components and derive layout, ownership, labels, and canonical keys from one server projection.
- [ ] Add `loadSettings`, `patchSettings`, and `resetSettings` adapters for `/settings/pipeline`; remove settings-data `localStorage` from `settings.html`.
- [ ] Render booleans as native checkbox toggles and other controls from backend schema metadata.
- [ ] Direct controls PATCH one canonical change; on rejection, restore authoritative response state.
- [ ] Dialogs keep local drafts, PATCH complete groups on Save, and send nothing on Cancel, close, or Escape.
- [ ] Disabled Manage buttons remain inert and show backend-provided reason text.
- [ ] Render warnings with `role="status"`, errors with `role="alert"`, and never rely on color alone.
- [ ] Render mirrors read-only with enabled links to their owning Overview controls; exclude mirror keys from reset ownership.
- [ ] Omit `Skip Incomplete Listings`, separate Location Preference, `Require Manual Review`, unsupported batch fields, Gap Thresholds, CV model, preset, and page-limit controls from Pipeline pages.
- [ ] Preserve responsive navigation, themes, reduced motion, keyboard focus, and dialog focus return.

**Verification:**
- [ ] `$env:PYTHONPATH='src'; python -m pytest tests/test_fitcv_cp/test_app.py -q -k "settings and (pipeline or toggle or dialog or warning or disabled or mirror or reset or excluded)"`
- [ ] `rg -n "fitcv-pipeline-settings-prototype|localStorage" src/fitcv_cp/templates/settings.html`
- [ ] Browser: supported pages, direct reload/reset, every dialog Save/Cancel/error path, disabled actions, owner links, mobile, keyboard, reduced motion, and light/dark themes.
- Expected: tests and browser checks pass; grep has no matches; unsupported mock-only controls are absent.

**Exit Criteria:**
- Production UI contains no copied defaults, prototype storage, unsupported row, or duplicate owner.

### Task 6: Close audit with end-to-end proof

**Purpose:**
- Prove load, serialized save, restart, reset, stage consumption, exclusion, and preserved external ownership.

**Specification Coverage:**
- Final audit inventory, SSOT status, symmetry status, and no UI-only or wrong-owner production setting.

**Required Skills:**
- `skill-verification-before-completion`

**Files And Symbols:**
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`, `tests/test_fitcv_cp/test_settings_store.py`, `tests/test_fitcv_cp/test_settings_store_sqlite.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_worker_job.py`
- Verify: `tests/test_enrich.py`, `tests/test_rule_filter.py`, `tests/test_ai_score.py`, `tests/test_agentic_cv_analysis.py`, `tests/test_pipeline.py`, `tests/test_pipeline_agentic_late_stage.py`, `tests/test_gap_analysis.py`
- Update: `docs/superpowers/plans/audit/2026-07-19-22-31-01-pipeline-settings-backend-wiring/report.md`

**Dependencies:**
- Tasks 1-5.

**Steps:**
- [ ] Add a table-driven inventory for each production row: canonical key or projection, owner page, control type, persistence mode, group, and consumer proof.
- [ ] For every direct key, test baseline GET, PATCH, fresh app/store reload, reset, and baseline restoration.
- [ ] For every managed group, test invalid no-write, valid atomic write, reload, and browser Cancel-without-request.
- [ ] Run one concurrent relational-update test proving serialization.
- [ ] Run representative stage-consumption tests for every supported Pipeline page.
- [ ] Assert excluded mock-only rows and external CV owners are absent from Pipeline payloads without banning their legitimate repository contracts.
- [ ] Append post-patch audit status using: Setting label, frontend component, backend owner, API/config field, wiring status, expected behavior, issue, SSOT/symmetry status, result.

**Verification:**
- [ ] Run final commands from `## Verification`.
- Expected: focused suites pass and audit contains no unresolved required Pipeline wiring defect.

**Exit Criteria:**
- Audit inventory contains no UI-only, duplicated, unused, incorrectly mapped, or wrong-page supported Pipeline setting.

## Verification

- `$env:PYTHONPATH='src'; python -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- `$env:PYTHONPATH='src'; python -m pytest tests/test_enrich.py tests/test_rule_filter.py tests/test_ai_score.py tests/test_agentic_cv_analysis.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_gap_analysis.py tests/test_config.py -q`
- Browser at `1280x900` and `390x844`: supported Pipeline pages, direct save/reload/reset, dialogs, disabled actions, warnings/errors, mirrors, keyboard focus, reduced motion, and light/dark themes.
- Lighthouse snapshot accessibility audit on `/admin/settings` at desktop and mobile sizes.
- `rg -n "fitcv-pipeline-settings-prototype|localStorage" src/fitcv_cp/templates/settings.html`
- `rg -n "gap_thresholds\." src/fitcv_cp/settings_schema.py config/policy/eligibility.yaml src/fitcv_cp/templates/settings.html`
- `rg -n "llm_runtime\.model_routing" src config tests`
- `git diff --check` and `git status --short`; preserve unrelated user work and audit evidence.

Expected grep results: no matches. Existing `cv_generation_model` provenance, control-plane routing, theme storage, and process-console storage are not deprecated by this plan and are intentionally outside these scans.

## Completion Criteria

The plan is ready for completion verification when:

1. every production Pipeline row resolves through one canonical backend key or explicit schema projection
2. every write and reset uses one serialized read-merge-validate-write transaction
3. concurrent requests cannot commit an invalid effective state
4. persisted values survive restart and alter existing owning consumers
5. unsupported mock-only controls remain absent instead of gaining speculative backend fields
6. Enrichment exposes Delay/Batch/Concurrency and other runtime stages expose Delay/Concurrency only
7. Gap Threshold settings are removed while CV model, preset, and page-limit external ownership remains unchanged
8. binary controls use native toggles; disabled actions stay inert; warnings and errors include text
9. mirrors remain non-editable and navigate to enabled owner controls
10. backend, pipeline, UI, browser, and accessibility verification passes
11. audit report records final per-setting wiring with no unresolved required SSOT or symmetry violation

The plan may be marked `completed` only after `skill-verification-before-completion` runs fresh proof and returns `verified`.

A checked box records progress; it is not proof by itself.
