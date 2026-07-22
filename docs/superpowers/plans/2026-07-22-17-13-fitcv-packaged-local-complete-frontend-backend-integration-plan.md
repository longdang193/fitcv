---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-packaged-local-complete-frontend-backend-integration
parent_spec: docs/superpowers/specs/2026-07-22-16-31-fitcv-packaged-local-complete-frontend-backend-integration-spec.md
targets:
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/local_credentials.py
  - src/fitcv_cp/local_setup.py
  - src/fitcv_cp/local_storage.py
  - src/fitcv_cp/local_routes.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates
  - src/fitcv_cp/retry_settings.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv/config.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/llm_runtime.py
  - src/fitcv/prompts
  - tests/test_fitcv_cp
  - docs/fitcv-settings-ui-prototype.integration.md
---

# FitCV Packaged-Local Complete Frontend-Backend Integration Implementation Plan

## Goal

Implement approved packaged-local FitCV browser application as one shared Jinja shell with real URLs, dedicated detail pages, one provider/model registry, server-owned prompt defaults, canonical LLM and retry resources, and separate System/Lifecycle ownership. Preserve existing Runs, Candidate Profile, Bookmark, Synonym, backup, relocation, diagnostics, and shutdown contracts except where parent specification explicitly changes page ownership or configuration semantics.

Cut over provider, model-routing, prompt-addendum, and retry state once. Do not create dual-read, dual-write, hash-route, duplicate Settings, or browser-secret compatibility layers. Preserve unrelated working-tree changes in `AGENTS.md`, `docs/operating_system/rules/frontend-ui-rule.md`, `docs/operating_system/templates/agents/root-AGENTS.template.md`, `scripts/sync_agent_adapters.py`, `.playwright-mcp/`, and `fitcv-synonyms-*.png`.

## Implementation Outcomes

### One canonical packaged-local state model

SQLite schema version 4 owns custom providers, connection metadata, provider models, LLM configuration, prompt replacements, System retry/recovery settings, and migration records. Predefined provider definitions and default prompt text remain packaged resources. Windows Credential Manager remains only API-key value owner.

### Verified provider and model lifecycle

Provider collection/detail APIs and pages expose predefined and custom providers, exactly zero or one connection per provider, draft test-before-save behavior, connection-revision-bound model validation, stale-model handling, routing-reference conflicts, stable errors, revisions, and no secret values.

### Runtime configuration from canonical resources

Default Route and four task configurations resolve only validated models on verified connections. Pipeline requests receive selected model, API type, timeout, temperature, credential, prompt replacement or server default, fixed retry delay, and immutable revision/provenance without reading retired local overlay.

### One real-URL Jinja application

Runs, Run Details, Candidate Profiles, Candidate Profile Details, Bookmarks, Synonyms, Pipeline, API Providers, LLM Configuration, System, and Lifecycle render through `base.html`. Direct load, refresh, normal links, enhanced History API navigation, Back, Forward, restored query state, parent back links, and JavaScript-disabled navigation remain equivalent.

### Disjoint System and Lifecycle controls

System owns backup/import plus retry/recovery settings. Lifecycle owns data location, relocation, and diagnostics. Global header owns shutdown. Every cold or shutdown action reads backend `active_work_reasons()` capabilities and retains existing loopback, same-origin, CSRF, confirmation, and restart behavior.

### Durable contract and browser proof

Focused persistence, migration, API, runtime, Jinja, security, secret-canary, and regression tests replace obsolete drawer/string assertions. Production browser proof covers navigation history, forms, async states, keyboard/focus, themes, responsive layouts, 200% zoom, reduced motion, and clean console/network behavior before temporary integration sidecar is deleted.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-code-standards`, `skill-full-stack-integration`, `skill-central-config-layer`, `skill-frontend-component-engineering`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: current workspace; preserve all unrelated modified and untracked files named in Goal
- Parallel ownership: none; schema, `app.py`, `local_routes.py`, `base.html`, runtime routing, and shared tests are dependency hubs
- Sequential fallback: execute Tasks 1 through 10 in order
- Shared-write rule: edit canonical Python/schema/template owners before assertions or sidecar cleanup; never edit generated or private tool state as substitute

## Task Breakdown

### Task 1: Add canonical schema and persistence contracts

**Purpose:**
- Add transactional storage and revision primitives for provider, model, LLM, prompt, System, and migration state before any route or runtime consumes them.

**Specification Coverage:**
- Canonical provider/model registry, mutable-state ownership, one connection per provider, LLM/prompt/System resources, stale-tab protection, idempotent migration, and no API-key persistence.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`
- `skill-central-config-layer`

**Files And Symbols:**
- Modify: `src/fitcv_cp/sqlite_store.py:CONTROL_PLANE_SCHEMA_VERSION`
- Modify: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`
- Modify: `src/fitcv_cp/sqlite_store.py:initialize_control_plane_database`
- Modify: `src/fitcv_cp/sqlite_store.py` provider definition, connection, model, and migration persistence functions
- Modify: `src/fitcv_cp/store.py:RunStore`
- Modify: `src/fitcv_cp/store.py:InMemoryRunStore`
- Modify: `src/fitcv_cp/settings_store.py` LLM, prompt, and System resource load/patch functions
- Modify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Modify: `tests/test_fitcv_cp/test_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store.py`
- Modify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`

**Dependencies:**
- Parent specification approved and reviewed.
- Existing schema version 3 remains only accepted upgrade source.

**Steps:**
- [ ] Add transactional version 3 to version 4 migration; retain fresh version 0 initialization and reject every unsupported version without partial writes.
- [ ] Add `custom_api_providers`, `api_provider_connections`, and `api_provider_models` tables with provider/model uniqueness, one connection per provider, integer revisions, timestamps, validation state, connection-revision linkage, and no secret-bearing columns.
- [ ] Add singleton `llm_configuration` and `system_settings` tables plus task-keyed `prompt_configurations` and keyed `integration_migrations`; seed approved defaults only for mutable configuration values, never default prompt text.
- [ ] Extend `RunStore` and `InMemoryRunStore` with provider/custom-provider, connection, model, routing-reference, and migration-record operations used by later tasks.
- [ ] Add `settings_store.py` functions `load_llm_configuration`, `patch_llm_configuration`, `load_prompt_configurations`, `patch_prompt_configuration`, `load_system_settings`, and `patch_system_settings` with atomic complete-resource validation and expected-revision conflicts.
- [ ] Keep packaged predefined providers outside SQLite and keep API-key values out of every schema, JSON value, revision payload, audit row, and fixture.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py -q`
- Expected: fresh initialization and version 3 upgrade reach version 4; constraints, revisions, rollback, and idempotent rerun pass; secret canary is absent from SQLite bytes and decoded rows.

**Exit Criteria:**
- Schema version 4 and all low-level resources exist with one transactional owner, no route/runtime dependency, and no persisted credential value.

### Task 2: Build provider registry and credential boundary

**Purpose:**
- Centralize predefined/custom provider projection, connection testing, credential mutation, model testing, eligibility, and compensation logic for every consumer.

**Specification Coverage:**
- Predefined IDs and fixed values, custom compatibility, one connection, test-before-save, credential reuse/masking, model validation, `needs_retest`, `model_in_use`, and shared onboarding/runtime/readiness ownership.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`
- `skill-central-config-layer`

**Files And Symbols:**
- Create: `src/fitcv_cp/provider_registry.py:PREDEFINED_PROVIDERS`
- Create: `src/fitcv_cp/provider_registry.py:ProviderRegistry`
- Modify: `src/fitcv_cp/local_setup.py:ProviderSetup`
- Modify: `src/fitcv_cp/local_setup.py:discover_models`
- Modify: `src/fitcv_cp/local_setup.py:test_provider`
- Modify: `src/fitcv_cp/local_credentials.py:set_credential`
- Modify: `src/fitcv_cp/local_credentials.py:get_credential`
- Modify: `src/fitcv_cp/local_credentials.py:delete_credential`
- Create: `tests/test_fitcv_cp/test_provider_registry.py`
- Modify: `tests/test_fitcv_cp/test_local_setup.py`
- Modify: `tests/test_fitcv_cp/test_local_credentials.py`

**Dependencies:**
- Task 1 persistence contracts complete.

**Steps:**
- [ ] Define immutable predefined resources for `openai`, `anthropic`, `deepseek`, and `groq` using prototype-approved display names, compatibility, fixed Base URLs, supported API types, and fixed API type behavior.
- [ ] Merge packaged predefined resources with custom SQLite records in `ProviderRegistry`; derive connection status, credential presence, model counts, eligible counts, and capabilities rather than persisting UI projections.
- [ ] Refactor provider transport validation into shared connection-draft and model-test functions supporting OpenAI-compatible Responses/Chat Completions and Anthropic Messages behavior without mutating state.
- [ ] Implement add/update/remove connection operations that rerun shared validator, write or reuse deterministic Credential Manager account, update metadata, mark models `needs_retest` after connection revision changes, and compensate Credential Manager when SQLite write fails.
- [ ] Implement model add/retest/remove operations that rerun validation before commit, enforce provider/model uniqueness, bind validation to current connection revision, and reject removal or connection deletion with `model_in_use` while LLM configuration references model.
- [ ] Implement custom-provider rename/delete through same service; deletion requires no active LLM reference, removes connection/model metadata and Credential Manager secret as one compensated operation, and never mutates predefined providers.
- [ ] Return bounded non-secret failure codes and messages; never return, log, hash into response metadata, or persist API-key value.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_provider_registry.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_local_credentials.py -q`
- Expected: predefined/custom symmetry, one-connection invariant, test-before-write, key reuse/replacement/removal compensation, stale models, routing conflicts, and sanitized failures pass.

**Exit Criteria:**
- `ProviderRegistry` is sole provider/model behavior owner and is usable by API, onboarding, readiness, diagnostics, and runtime consumers.

### Task 3: Expose typed provider APIs

**Purpose:**
- Add packaged-local provider catalog, connection, and model HTTP contracts with stable envelopes, revisions, idempotency, and security.

**Specification Coverage:**
- Canonical provider API map, request models, resource/error conventions, packaged-local-only mounting, Host/Origin/CSRF rules, and no connection counts in provider rows.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py:create_app`
- Modify: `src/fitcv_cp/app.py:ApiError`
- Add in: `src/fitcv_cp/app.py` `CreateCustomProviderRequest`, `UpdateCustomProviderRequest`, `ConnectionTestRequest`, `ConnectionWriteRequest`, `ModelTestRequest`, and `ModelCreateRequest`
- Add in: `src/fitcv_cp/app.py` `/api-providers` route handlers
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py`

**Dependencies:**
- Task 2 registry service complete.

**Steps:**
- [ ] Add typed `GET/POST /api-providers`, `GET/PATCH/DELETE /api-providers/{provider_id}`, connection test/write/delete, and model test/create/retest/delete handlers that delegate to `ProviderRegistry`.
- [ ] Require body `expected_revision` for mutations and `Idempotency-Key` for custom-provider/model creation; reuse existing idempotency reservation/replay behavior.
- [ ] Map registry failures to approved `404`, `409`, `422`, `503`, and `500` envelopes and stable codes without exposing credentials or raw provider bodies.
- [ ] Mount every provider route only when packaged-local mode is active and apply existing loopback Host validation plus same-origin/CSRF checks to unsafe requests.
- [ ] Assert OpenAPI request/response models, enums, media types, required headers, and absence of API-key examples or response fields.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_app.py -q -k "provider or openapi or csrf or origin or host"`
- Expected: route inventory differs correctly by mode; happy, validation, stale, duplicate, missing, unavailable, and secret-safety cases match parent contract.

**Exit Criteria:**
- Provider registry is fully reachable through one typed packaged-local HTTP surface and no caller needs onboarding overlay data.

### Task 4: Wire canonical LLM configuration into runtime

**Purpose:**
- Persist Default Route and four task configurations, expose typed APIs, resolve only eligible provider models, and snapshot exact runtime configuration for Runs.

**Specification Coverage:**
- Default Route, four canonical task IDs, model/default behavior, timeout, temperature, eligible options, atomic patching, disconnected/stale rejection, and immutable provenance.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py` `LlmConfigurationPatchRequest` and `/llm-configuration` handlers
- Modify: `src/fitcv_cp/settings_store.py:load_llm_configuration`
- Modify: `src/fitcv_cp/settings_store.py:patch_llm_configuration`
- Modify: `src/fitcv/runtime_routing.py:resolve_llm_routing`
- Modify: `src/fitcv/runtime_routing.py:resolve_openai_compatible_api_key`
- Modify: `src/fitcv/llm_runtime.py:LlmTaskRequest`
- Add in: `src/fitcv/llm_runtime.py:_anthropic_messages_adapter`
- Modify: `src/fitcv_cp/app.py:_execute_trigger` Run input snapshot construction
- Modify: `src/fitcv_cp/worker_job.py` effective runtime configuration loading
- Modify: `src/fitcv/pipeline.py` LLM provenance projection
- Modify: `src/fitcv/pipeline_stage_artifacts.py` LLM provenance fields
- Modify: `tests/test_fitcv_cp/test_provider_routing.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`
- Modify: `tests/test_llm_runtime.py`

**Dependencies:**
- Task 3 provider API and eligibility behavior complete.

**Steps:**
- [ ] Add `GET/PATCH /llm-configuration` with task IDs `enrich_extraction`, `ranking_ai_score`, `cv_generation_structured_write`, and `synonym_triage_recommendation`, eligible model metadata, revision, timestamp, and ETag.
- [ ] Register LLM configuration routes only inside `create_app` packaged-local branch so server/developer mode returns `404` and does not advertise them in OpenAPI.
- [ ] Validate complete patched resource atomically: task/default references must resolve to validated models whose provider connection is verified at same connection revision; Timeout defaults to 120 and stays within 1..3600; Temperature defaults to 0.2 and stays within 0..2 at 0.1 precision.
- [ ] Replace local-overlay provider/model resolution in packaged-local runtime with `ProviderRegistry` plus LLM configuration projection held in memory for request/worker; keep non-local control-plane config behavior unchanged.
- [ ] Resolve each task to explicit override or Default Route without silent unrelated fallback; pass resolved provider, API type, model, timeout, temperature, and Credential Manager secret to `LlmTaskRequest`; dispatch OpenAI-compatible Responses/Chat Completions and Anthropic Messages through explicit adapters.
- [ ] Capture LLM configuration revision and resolved task routing/provenance in existing Run input/settings snapshot before enqueue so later edits do not alter an admitted Run.
- [ ] Preserve explicit unavailable references after connection/model invalidation and block affected LLM work until user selects an eligible model; preserve built-in Synonym Recommendation fallback only under existing runtime fallback rule.
- [ ] Remove hardcoded task model/timeout/temperature assumptions from packaged-local execution paths and update provenance names from provider/model strings to model-record-backed values.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_provider_routing.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_app.py tests/test_llm_runtime.py -q -k "llm or routing or model or runtime or settings_snapshot"`
- Expected: eligible selection, Default behavior, task overrides, stale/disconnected rejection, exact adapter arguments, immutable Run snapshots, revision conflicts, and non-local compatibility pass.

**Exit Criteria:**
- Every packaged-local LLM task resolves through canonical provider/model and LLM configuration resources with reproducible Run provenance.

### Task 5: Replace prompt addenda with server defaults and replacements

**Purpose:**
- Make packaged prompt templates only default owner and persist only optional validated full replacement templates for four LLM tasks.

**Specification Coverage:**
- Prompt Management resource, Default/Custom semantics, required variables, 4000-character saves, `needs_review`, reset, no empty/unchanged custom save, and runtime provenance.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/prompts/templates/enrich_extraction_v1.md`
- Modify: `src/fitcv/prompts/templates/ranking_ai_score_v2.md`
- Modify: `src/fitcv/prompts/templates/cv_generation_structured_write_v1.md`
- Modify: `src/fitcv/prompts/templates/synonym_triage_recommendation_v1.md`
- Modify: `src/fitcv/prompts/registry.py:get_prompt_definition`
- Modify: `src/fitcv/prompts/models.py:RenderedPrompt`
- Modify: `src/fitcv/prompts/renderer.py:render_prompt`
- Modify: `src/fitcv/config.py:get_prompt_addendum`
- Modify: `src/fitcv/config.py:get_prompt_addendum_metadata`
- Modify: `src/fitcv/enrich.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv_cp/app.py` `PromptConfigurationPatchRequest` and `/prompt-configurations` handlers
- Modify: `src/fitcv_cp/worker_job.py` prompt configuration resolution
- Modify: `src/fitcv/pipeline.py` prompt provenance projection
- Modify: `src/fitcv/pipeline_stage_artifacts.py` prompt provenance fields
- Modify: `tests/test_prompts.py`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Task 4 task identity and Run snapshot seam complete.

**Steps:**
- [ ] Remove `${prompt_addendum}` from four packaged templates while preserving every actual runtime context variable.
- [ ] Change `render_prompt` to select current packaged template or supplied full replacement, validate replacement variables against canonical task definition, and emit prompt ID/version plus replacement hash/character count.
- [ ] Normalize CRLF and CR to LF before prompt comparison/validation while preserving all other meaningful user whitespace.
- [ ] Add `GET /prompt-configurations` and `PATCH /prompt-configurations/{task_id}`; derive default text, mode, required variables, and display metadata from prompt registry and persist only `replacement_text`, `migration_state`, revision, and timestamps.
- [ ] Register prompt configuration routes only inside `create_app` packaged-local branch so server/developer mode returns `404` and does not advertise them in OpenAPI.
- [ ] Reject unknown variables, missing required variables, text above 4000 characters for new saves, empty custom text, and custom text identical to current default; allow `null` to reset to Default.
- [ ] Replace all runtime `get_prompt_addendum` calls and addendum provenance with task replacement lookup from canonical prompt configuration at task execution; record prompt ID/version and replacement hash/character count, never default or replacement text in Run snapshots/artifacts unless an existing artifact contract already requires rendered prompt retention.
- [ ] Keep default prompt upgrades live for Default mode and keep grandfathered over-limit migrated replacements executable while preventing re-save until corrected or reset.

**Verification:**
- [ ] `py -3 -m pytest tests/test_prompts.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q -k "prompt or replacement or addendum or provenance"`
- Expected: Default follows packaged file changes, valid replacements render, invalid variables and bounds fail, reset works, no default text persists, and runtime provenance records only bounded metadata.

**Exit Criteria:**
- Prompt defaults and replacements have separate canonical owners and no packaged-local runtime path appends mutable addenda.

### Task 6: Replace retry list with one System settings resource

**Purpose:**
- Store and apply Maximum Attempts, Initial Backoff, Lease, Reconciler Interval, and Error Detail Limit through one revisioned resource and one loader.

**Specification Coverage:**
- Scalar fixed backoff, shared retry/recovery revision, bounds/defaults, worker/reconciler/queue consumers, error truncation, and stable API conflicts.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/retry_settings.py:RetrySettings`
- Modify: `src/fitcv_cp/retry_settings.py:load_retry_settings`
- Modify: `src/fitcv_cp/queue.py:enqueue_run_with_job_id`
- Modify: `src/fitcv_cp/reconciler.py:reconcile_abandoned_attempts`
- Modify: `src/fitcv_cp/reconciler_service.py:run_reconciler_forever`
- Modify: `src/fitcv_cp/worker_job.py` lease and error-detail consumers
- Modify: `src/fitcv_cp/app.py` `SystemSettingsPatchRequest` and `/system-settings` handlers
- Modify: `tests/test_fitcv_cp/test_retry_settings.py`
- Modify: `tests/test_fitcv_cp/test_queue.py`
- Modify: `tests/test_fitcv_cp/test_reconciler.py`
- Modify: `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`
- Modify: `tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 System persistence complete.

**Steps:**
- [ ] Replace `enabled` and `backoff_seconds` tuple with `maximum_attempts`, `initial_backoff_seconds`, and `error_detail_limit`; enforce defaults/ranges 3 and 1..10, 10 and 0..3600, 10000 and 1000..100000, Lease 300 and 30..86400, Reconciler Interval 30 and 5..3600; adapt `error_detail_limit` only at existing artifact field boundary `error_details_max_chars`.
- [ ] Configure RQ retry with same scalar delay for each retry and no multiplier, sequence, jitter, or fallback list.
- [ ] Make queue, worker lease renewal, reconciler, reconciler service, and error-detail truncation consume same persisted revisioned values.
- [ ] Add `GET/PATCH /system-settings` with complete-resource validation, expected revision, ETag, field errors, and `system_settings_revision_conflict`.
- [ ] Register System settings routes only inside `create_app` packaged-local branch so server/developer mode returns `404` and does not advertise them in OpenAPI.
- [ ] Remove packaged-local retry reads from `control_plane.yaml` and local controller overlay after Task 7 migration is wired; preserve non-local behavior only through explicit non-local defaults.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py tests/test_fitcv_cp/test_app.py -q -k "retry or backoff or lease or reconciler or error_detail or system_settings"`
- Expected: identical fixed delay precedes every retry, attempts include initial attempt, all consumers share values/revision, bounds and stale writes fail, and error truncation remains exact.

**Exit Criteria:**
- Packaged-local retry/recovery has one scalar-backed System resource and no consumer reads an arbitrary delay list.

### Task 7: Perform restart-safe cutover and local lifecycle reconciliation

**Purpose:**
- Migrate legacy onboarding/overlay state once, make canonical resources drive readiness, and expose disjoint System/Lifecycle capability resources without changing unsafe action URLs.

**Specification Coverage:**
- Provider/onboarding, prompt, and retry migration rules; overlay retirement; onboarding completion preservation; redirects; active-work SSOT; status capabilities; backup/import/relocation/diagnostics/shutdown safety.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/local_storage.py:LocalStoragePaths`
- Add in: `src/fitcv_cp/local_storage.py:migrate_packaged_local_integration_state`
- Modify: `src/fitcv_cp/local_routes.py:load_onboarding_state`
- Modify: `src/fitcv_cp/local_routes.py:save_onboarding_state`
- Modify: `src/fitcv_cp/local_routes.py:local_readiness_status`
- Modify: `src/fitcv_cp/local_routes.py:active_work_reasons`
- Modify: `src/fitcv_cp/local_routes.py:build_local_router`
- Modify: `src/fitcv_cp/local_routes.py:_system_metadata`
- Modify: `src/fitcv_cp/local_app.py:prepare_local_environment`
- Modify: `src/fitcv_cp/local_app.py:process_pending_storage_operation`
- Modify: `src/fitcv/config.py:load_local_controller_overlay`
- Modify: `src/fitcv/config.py:_merge_controller_overlay`
- Modify: `tests/test_fitcv_cp/test_local_storage.py`
- Modify: `tests/test_fitcv_cp/test_local_routes.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py`
- Modify: `tests/test_config.py`

**Dependencies:**
- Tasks 2, 4, 5, and 6 canonical write paths complete.

**Steps:**
- [ ] Run `migrate_packaged_local_integration_state` during packaged-local startup before canonical configuration becomes writable; record completion only after every provider, credential, model, routing, prompt, retry, and onboarding cleanup action succeeds.
- [ ] Import legacy provider metadata, copy Credential Manager value to deterministic canonical account with verified lookup before deleting legacy account, import models as `needs_retest`, and retain imported routing references as ineligible until retest.
- [ ] Compose each non-empty legacy addendum against its legacy template into one full replacement; set `needs_review` without truncation when above 4000 characters; migrate empty addenda to `null`.
- [ ] Map retry fields exactly: disabled to one attempt, enabled to preserved attempts, first delay or 10, positive reconciler interval or 30, and bounded lease/error values; record old non-secret values and new revision.
- [ ] On success, remove provider/model/routing/prompt/retry values from onboarding and mutable overlay ownership; on failure, leave legacy files and credentials intact, expose bounded migration error, and block canonical writes without dual-write behavior.
- [ ] Change `/local/onboarding` to wizard-progress-only behavior using canonical provider/LLM APIs and redirect completed onboarding to `/admin/runs`.
- [ ] Make `local_readiness_status` read canonical verified connection, eligible Default Route, migration state, and required Candidate Profile state; remove `provider_test_ok` as readiness truth after migration.
- [ ] Redirect GET `/local/data` to `/admin/system` and GET `/local/system` to `/admin/lifecycle`; keep existing unsafe `/local/data/*` and `/local/system/*` actions unchanged.
- [ ] Add `GET /local/data/status` and `GET /local/lifecycle/status`; derive `can_backup`, `can_import`, `can_relocate`, and `can_shutdown` from `active_work_reasons()` including executor busy and `queued`, `running`, `awaiting_continue`, and `cancelling` Runs; expose folder-picker and diagnostics capabilities without duplicating safety enums in frontend.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_config.py -q -k "migration or onboarding or readiness or data or lifecycle or shutdown or active_work or overlay"`
- Expected: migration is idempotent and restart-safe, failure preserves legacy truth, completed onboarding remains complete, capabilities use one owner, redirects are GET-only, unsafe actions preserve contracts, and retired values no longer load after success.

**Exit Criteria:**
- Canonical resources own all packaged-local provider/model/LLM/prompt/retry state and local lifecycle safety remains backend-derived.

### Task 8: Consolidate shared shell and entity navigation

**Purpose:**
- Remove duplicate Settings/Drawer implementations and make Runs and Candidate Profiles use dedicated real-URL detail pages through one responsive accessible shell.

**Specification Coverage:**
- Shared shell, canonical page URLs, parent back navigation, History API rules, query restoration, dedicated Run/Profile pages, Profile UI reverse-Runs omission, theme/shutdown global controls, and design SSOT.

**Required Skills:**
- `skill-frontend-component-engineering`
- `ui-ux-pro-max`
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `src/fitcv_cp/templates/candidate_profiles.html`
- Create: `src/fitcv_cp/templates/candidate_profile_detail.html`
- Modify: `src/fitcv_cp/templates/bookmarks.html`
- Modify: `src/fitcv_cp/templates/synonyms.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py:admin_runs`
- Modify: `src/fitcv_cp/app.py:admin_run_detail`
- Modify: `src/fitcv_cp/app.py:admin_candidate_profiles`
- Add in: `src/fitcv_cp/app.py:admin_candidate_profile_detail`
- Modify: `src/fitcv_cp/app.py:admin_bookmarks`
- Modify: `src/fitcv_cp/app.py:admin_synonyms`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 7 packaged-local routing and global shutdown capability complete.

**Steps:**
- [ ] Make `base.html` sole owner of sidebar, header, page-content target, title synchronization, active navigation, theme bootstrap/toggle, shutdown dialog, common buttons/rows/cards/dialogs, focus handling, and reduced-motion behavior.
- [ ] Keep sidebar limited to approved application destinations; remove Health and Appearance entries while retaining theme action in global header.
- [ ] Correct theme action semantics: dark mode displays sun action to switch to Light; light mode displays moon action to switch to Dark; theme remains browser-local.
- [ ] Add same-origin enhanced navigation that fetches complete canonical URLs, replaces only page-content region, updates title/sidebar/focus, writes one `pushState`, uses `replaceState` only for normalization, and restores on `popstate`; preserve ordinary anchor navigation when enhancement fails or JavaScript is disabled.
- [ ] Parse, validate, and normalize collection query parameters in page handlers so direct requests and JavaScript-disabled navigation render same filtered/search/sort/page/tab state that enhanced navigation restores.
- [ ] Keep `/admin/runs/{run_id}` as only Run Details UI, add validated `Back to Runs`, remove repeated heading status, and use one parent-owned vertical gap between detail sections.
- [ ] Add `/admin/candidate-profiles/{profile_id}` with `Back to Candidate Profiles`, canonical detail data, archive/restore actions, no repeated heading status, and no request to `/candidate-profiles/{profile_id}/runs`.
- [ ] Keep newly integrated shared-shell page routes packaged-local-only while preserving existing durable JSON domain APIs for non-Profile consumers.
- [ ] Delete Runs collection, Run Details drawer, Candidate Profile drawer, hash routes, duplicate global controls, duplicate row/card CSS, and obsolete Settings-local data arrays from `settings.html`.
- [ ] Keep Bookmark Run cells limited to linked Run ID and keep retained reverse Profile Runs API test for non-UI consumers.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -q -k "admin_runs or run_detail or candidate_profile or bookmarks or synonyms or settings or template"`
- Expected: canonical hrefs and dedicated pages render, reverse Runs route remains, Profile UI omits it, duplicate drawers/hash routes are absent, and shared shell semantics are present.

**Exit Criteria:**
- Existing workspace pages have one shell and one implementation per collection/detail behavior with no duplicate Settings route owner.

### Task 9: Build provider, LLM, Prompt, System, and Lifecycle pages

**Purpose:**
- Connect approved prototype page behavior to canonical APIs using shared controls and complete async/form states.

**Specification Coverage:**
- Pipeline information architecture, API Key Providers/custom providers, provider details and Add Model dialog, LLM task rows, Prompt Management editor, System backup/import/retry, Lifecycle relocation/diagnostics, shutdown placement, validation, disabled states, and accessibility.

**Required Skills:**
- `skill-frontend-component-engineering`
- `ui-ux-pro-max`
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv_cp/templates/settings.html`
- Create: `src/fitcv_cp/templates/api_providers.html`
- Create: `src/fitcv_cp/templates/api_provider_detail.html`
- Create: `src/fitcv_cp/templates/llm_configuration.html`
- Create: `src/fitcv_cp/templates/prompt_management.html`
- Create: `src/fitcv_cp/templates/system.html`
- Create: `src/fitcv_cp/templates/lifecycle.html`
- Modify: `src/fitcv_cp/app.py` `/admin/settings/{section}`, `/admin/api-providers`, `/admin/api-providers/{provider_id}`, `/admin/llm-configuration`, `/admin/system`, and `/admin/lifecycle` page handlers
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_local_routes.py`

**Dependencies:**
- Tasks 3 through 8 APIs, resources, redirects, and shell complete.

**Steps:**
- [ ] Keep Pipeline Overview plus real section URLs for `enrichment`, `screening`, `shortlisting`, `ranking`, `cv-analysis`, `cv-generation`, `runtime-limits`, `automation-reuse`, and `prompt-management`; remove Request Retry, Worker Recovery, provider, model-routing, and lifecycle controls from Pipeline.
- [ ] Render API Providers as flat setting rows under Custom Providers and API Key Providers with shared separators/hover/borders, `Connected` or `No connection`, no connection counts, and canonical detail links.
- [ ] Implement provider detail form state: predefined Base URL disabled, custom Base URL editable, masked existing key, fixed API type disabled, configurable API type select, Test action, Add/Update enabled only for unchanged successfully tested draft, and Connected only after write revalidation succeeds.
- [ ] Disable Available Models when disconnected; implement Add Model dialog with identifier, Test, Add enabled only after successful validation, and saved model rows with Test and Remove only.
- [ ] Populate LLM Default Route and four task rows from eligible model metadata; each task Manage dialog owns Model, Timeout, and Temperature, excludes CV Analysis, and handles revision-conflict reload without copying provider/model registries into browser state.
- [ ] Implement Prompt Management groups Pipeline Prompts and Synonym Prompts, Default/Custom mode, read-only default text, default-copy initialization for Custom, 4000-character counter, warning at 3800, hard limit, dirty-discard confirmation, `needs_review` behavior, field errors, and focus restoration.
- [ ] Implement System backup/import and retry/recovery forms from `/local/data/status` and `/system-settings`; implement Lifecycle data root, relocate, folder-picker capability, and diagnostics from `/local/lifecycle/status`; omit shutdown from Lifecycle because global header owns it.
- [ ] Use native labels, buttons, details, dialogs, form validation, live regions, focus return, duplicate-submit disabling, loading/empty/error/stale/success states, and backend capability explanations across all pages.
- [ ] Register API Providers, LLM Configuration, System, Lifecycle, and new Settings section page routes only in packaged-local mode; assert `404` and absent OpenAPI/page navigation in server/developer mode.
- [ ] Resolve initial page resources in server handlers and render usable collection/detail/form state into Jinja HTML; use JSON APIs for refresh and mutations without making JavaScript prerequisite for reading page content or following canonical links.

**Verification:**
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_routes.py -q -k "api_providers or llm_configuration or prompt_management or system or lifecycle or pipeline_settings"`
- Expected: every canonical page route renders semantic controls and canonical API URLs; provider/model/prompt/retry/lifecycle disabled and error states match backend capabilities.

**Exit Criteria:**
- All approved settings and lifecycle UI behaviors are connected to one backend owner with no prototype-only state or duplicate style/interaction implementation.

### Task 10: Prove complete integration and retire temporary intent

**Purpose:**
- Replace obsolete assertions, run cross-stack regression/security/browser proof, reconcile OpenAPI and source, and remove sidecar only after every acceptance criterion passes.

**Specification Coverage:**
- Complete Test Matrix and Completion Criteria, production browser coverage, secret safety, retained domain routes, packaged-local-only behavior, accessibility/responsiveness/themes, and sidecar removal condition.

**Required Skills:**
- `skill-full-stack-integration`
- `ui-ux-pro-max`
- `skill-verification-before-completion`

**Files And Symbols:**
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_local_app.py`
- Modify: `tests/test_fitcv_cp/test_local_routes.py`
- Modify: `tests/test_fitcv_cp/test_structural_contract_guardrails.py`
- Create: `tests/test_fitcv_cp/test_packaged_local_integration.py`
- Verify: `docs/fitcv-settings-ui-prototype.html`
- Delete after passing evidence: `docs/fitcv-settings-ui-prototype.integration.md`
- Update during execution: `docs/superpowers/plans/2026-07-22-17-13-fitcv-packaged-local-complete-frontend-backend-integration-plan.md`

**Dependencies:**
- Tasks 1 through 9 complete with task-local tests passing.

**Steps:**
- [ ] Delete assertions that require Run Details or Candidate Profile drawers, Settings-owned Runs, hash routes, connection counts, prompt addenda, retry sequences, duplicated shutdown sections, or template-string copies of prototype implementation.
- [ ] Add contract tests covering direct page URLs, packaged/non-packaged route inventory, retained reverse Profile Runs API, JSON schemas, revisions, ETags, idempotency, stable errors, Host/Origin/CSRF, migration restart behavior, and secret canary absence from SQLite, YAML, logs, HTML, JSON, OpenAPI, browser storage, diagnostics, and backup.
- [ ] Use Playwright MCP against production Jinja app for direct load, refresh, Runs/Profile/provider parent links, Back/Forward/query restoration, failed enhanced navigation fallback, provider test/save, model test/add/remove, LLM task save, prompt Default/Custom/dirty/limit behavior, backup/import, relocate, diagnostics, and shutdown cancel/confirm.
- [ ] Capture light/dark desktop, narrow, long-content, and 200% zoom screenshots; verify keyboard-only traversal, visible focus, accessible names, dialog focus trap/return, reduced motion, no page-level horizontal overflow, stable icon size, and shared row/card hover/border/spacing.
- [ ] Use Chrome DevTools MCP only for console, network payload/status, computed overflow/style, or runtime diagnosis found during Playwright flows; require no uncaught console error, unexpected failed request, duplicate mutation, or secret/path leak.
- [ ] Run focused and full automated verification, compare failures only against captured pre-execution baseline, remove integration sidecar when all evidence passes, and record every plan deviation before completion verification.

**Verification:**
- [ ] `py -3 -m py_compile src/fitcv_cp/provider_registry.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/store.py src/fitcv_cp/settings_store.py src/fitcv_cp/local_credentials.py src/fitcv_cp/local_setup.py src/fitcv_cp/local_storage.py src/fitcv_cp/local_routes.py src/fitcv_cp/app.py src/fitcv_cp/retry_settings.py src/fitcv_cp/queue.py src/fitcv_cp/reconciler.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/worker_job.py src/fitcv/config.py src/fitcv/runtime_routing.py src/fitcv/llm_runtime.py src/fitcv/prompts/models.py src/fitcv/prompts/registry.py src/fitcv/prompts/renderer.py`
- [ ] `py -3 -m pytest tests/test_fitcv_cp/test_provider_registry.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_local_credentials.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_provider_routing.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py tests/test_fitcv_cp/test_packaged_local_integration.py tests/test_prompts.py tests/test_llm_runtime.py tests/test_config.py -q`
- [ ] `py -3 -m pytest tests -q`
- [ ] `py -3 scripts/validate_planning_lifecycle.py`
- [ ] `py -3 scripts/validate_template_required_sections.py`
- [ ] `py -3 scripts/hooks/run_validator.py --fast`
- [ ] `git diff --check`
- Expected: all changed tests and validators pass; full-suite differences match only documented unrelated baseline; browser evidence satisfies every parent acceptance criterion; sidecar is absent.

**Exit Criteria:**
- Automated and browser evidence proves complete parent specification, no obsolete parallel owner remains, and temporary integration sidecar is deleted.

## Verification

- `py -3 -m pytest tests/test_fitcv_cp/test_provider_registry.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_local_credentials.py tests/test_fitcv_cp/test_local_setup.py tests/test_fitcv_cp/test_provider_routing.py tests/test_fitcv_cp/test_retry_settings.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_local_app.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_worker_job_attempt_terminalization.py tests/test_fitcv_cp/test_packaged_local_integration.py tests/test_prompts.py tests/test_llm_runtime.py tests/test_config.py -q`
- `py -3 -m pytest tests -q`
- `py -3 scripts/validate_planning_lifecycle.py`
- `py -3 scripts/validate_template_required_sections.py`
- `py -3 scripts/hooks/run_validator.py --fast`
- `git diff --check`
- Playwright MCP evidence covers every canonical URL, direct load/refresh/history/back link, collection query restoration, provider/model/LLM/prompt/System/Lifecycle flow, duplicate-submit guard, confirmation, keyboard/focus, light/dark, narrow, long content, reduced motion, and 200% zoom.
- Chrome DevTools MCP evidence confirms expected request routes/status/payloads, no uncaught console errors, no unexpected failed requests, no page overflow or icon shrink, and no credential/content/path leakage.
- Full-suite and validator results are compared with captured pre-execution baseline; only exact unchanged unrelated failures may remain.

## Completion Criteria

Plan is ready for completion verification when:

1. schema version 4 owns all approved mutable provider/model/LLM/prompt/System state and upgrades version 3 transactionally;
2. predefined provider/default prompt data remain packaged resources and API-key values exist only in Windows Credential Manager;
3. one `ProviderRegistry` serves onboarding, pages, APIs, readiness, diagnostics, LLM routing, and runtime validation;
4. provider connection and model writes rerun shared validation, enforce revisions/idempotency, compensate partial credential failures, and preserve stable non-secret errors;
5. Default Route and four task configurations select only validated models on verified current connections and are snapshotted before Run enqueue;
6. server prompt defaults remain live, persistence contains only optional replacement text, migrated addenda preserve effective behavior, and runtime no longer appends addenda;
7. every retry uses same scalar Initial Backoff and queue, worker, reconciler, and error truncation share one System resource;
8. migration is restart-safe and idempotent, leaves legacy state untouched on failure, removes retired ownership on success, and never enters dual-read or dual-write mode;
9. all canonical HTML URLs render through `base.html`, History API enhancement preserves normal navigation semantics, and query/back state is restorable;
10. Settings contains no duplicate Runs/Run Details/Profile drawer/provider/retry/lifecycle implementation and Candidate Profile UI never calls retained reverse Runs route;
11. API Providers, LLM Configuration, Prompt Management, System, and Lifecycle pages implement every approved loading, empty, disabled, validation, test, success, stale, conflict, and error state;
12. System and Lifecycle ownership is disjoint, shutdown is global, and every cold action consumes `active_work_reasons()` capabilities;
13. packaged-local route mounting, Host/Origin/CSRF, OpenAPI, revisions, ETags, idempotency, field validation, stable errors, and secret safety agree across source and tests;
14. focused tests, full tests, planning validators, repository validator, diff hygiene, and production browser evidence pass or match only documented unrelated baseline;
15. `docs/fitcv-settings-ui-prototype.integration.md` is removed only after all acceptance evidence passes;
16. every task, deviation, blocker, substitution, and deferral is reconciled against parent specification and current repository truth.

Plan may be marked `completed` only when `skill-verification-before-completion`:

1. runs fresh final verification;
2. confirms these completion criteria against repository evidence;
3. finds no unresolved required task, failed required check, stale status, or unrecorded scope deviation;
4. returns `verified` and updates plan status.

A checked box records progress; it is not proof by itself.
