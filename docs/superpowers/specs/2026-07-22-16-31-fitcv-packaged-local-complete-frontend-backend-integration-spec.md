---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-packaged-local-complete-frontend-backend-integration
targets:
  - docs/fitcv-settings-ui-prototype.html
  - docs/fitcv-settings-ui-prototype.integration.md
  - src/fitcv_cp/app.py
  - src/fitcv_cp/local_routes.py
  - src/fitcv_cp/local_credentials.py
  - src/fitcv_cp/local_setup.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates
  - src/fitcv/llm_runtime.py
  - src/fitcv/prompts
  - tests/test_fitcv_cp
related_features:
  - admin_control_plane_core
  - trigger_run_management
  - settings_system
  - run_lifecycle_controls
  - enrichment
  - synonym_management
related_stages:
  - enrichment
  - ranking
  - cv-generation
  - synonym-triage
---

# FitCV Packaged-Local Complete Frontend-Backend Integration Specification

## Authority and Supersession

- This specification is the canonical integration contract for the packaged-local FitCV browser application, including frontend routing, shared shell behavior, workspace pages, Pipeline settings, API Providers, LLM Configuration, Prompt Management, System, and Lifecycle.
- `docs/fitcv-settings-ui-prototype.html` remains the approved visual hierarchy and interaction reference. Real URLs, backend validation, persistence, security, and failure behavior are owned by this specification and runtime contracts rather than prototype-local state.
- `docs/fitcv-settings-ui-prototype.integration.md` remains temporary acceptance evidence until implementation passes. It must then be removed rather than retained as a parallel contract.
- Upon approval and activation, this specification supersedes `docs/superpowers/specs/2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md` for all covered frontend-backend integration behavior.
- `docs/superpowers/specs/2026-07-16-22-29-fitcv-local-distribution-and-onboarding-spec.md` remains authoritative for installer, bootstrap pointer, backup archive format, cold data mutation, loopback security, executable lifecycle, and Windows packaging except where this specification replaces onboarding-owned provider, model-routing, prompt, retry, or application-page ownership.
- Existing durable Runs, Candidate Profiles, Bookmarks, Synonyms, pipeline artifact, and backup contracts remain authoritative where this specification does not explicitly change visible behavior or ownership.
- Source, tests, generated OpenAPI, and packaged resources become runtime truth only after implementation and verification. Until then, this document describes required target behavior.

## Goal and Problem

### Problem

- Current frontend ownership is split across independent Jinja pages, duplicate Runs and Run Details code inside Settings, modal Candidate Profile details, prototype hash routes, and separate local onboarding/data/system pages.
- Current Settings Trigger Run submits obsolete profile fields while the canonical backend requires `profile_id`.
- Candidate Profile UI fetches reverse Run data that is not required by the approved details page and scales poorly when many Runs share one profile.
- Provider metadata, provider connection state, credentials, model routing, prompt addenda, and onboarding progress are coupled in one onboarding overlay, preventing one canonical provider/model registry.
- API Provider, LLM Configuration, Prompt Management, and several System settings have approved UI behavior but no canonical backend resource contract.
- Current prompt customization appends text to server prompts, while approved behavior requires server-owned defaults and optional full task-specific replacement text.
- Current retry configuration stores an arbitrary backoff sequence, while approved behavior exposes one scalar Initial Backoff.
- Data relocation and diagnostics are mixed with System configuration despite being application lifecycle operations.
- Existing template string tests can preserve obsolete drawers or duplicate markup without proving real navigation, browser history, async state, or backend integration.

### Goal

- Deliver one progressively enhanced Jinja application shell backed by real server URLs and canonical JSON/resource contracts.
- Make each visible setting and state read from one backend owner, with no duplicate frontend implementation and no parallel onboarding registry.
- Preserve existing durable domain APIs where still valid while adding the minimum missing provider, routing, prompt, system, and lifecycle contracts.
- Keep every new page and API packaged-local-only and enforce the existing loopback, same-origin, and CSRF boundary.
- Make implementation behavior unambiguous across loading, empty, success, validation, stale, conflict, disabled, retry, cancellation, and duplicate-submit states.

## Required Outcomes

### Outcome: One frontend route owner

- affected actor or system: packaged-local browser application
- required result: all application pages use one shared Jinja shell and real server URLs; Settings contains no duplicate Runs or Run Details implementation
- success condition: direct load, refresh, link navigation, browser Back, and browser Forward resolve the same page and URL state without hash routing

### Outcome: Dedicated entity details

- affected actor or system: Runs and Candidate Profiles
- required result: Run Details and Candidate Profile Details are dedicated pages with parent navigation; Candidate Profile UI does not fetch or render reverse Runs
- success condition: entity details remain restorable and bounded regardless of related Run count

### Outcome: Canonical provider and model registry

- affected actor or system: onboarding, API Providers, LLM routing, runtime credentials, and model validation
- required result: one registry owns predefined/custom providers, one connection per provider, verification state, credential handles, and provider-scoped models
- success condition: onboarding and application pages read/write the same registry; API key values exist only in Windows Credential Manager

### Outcome: Canonical LLM task configuration

- affected actor or system: LLM-backed pipeline tasks
- required result: Default Route and task overrides reference validated models from connected providers only
- success condition: runtime resolves provider, API type, credential, model, timeout, and temperature from one persisted configuration revision

### Outcome: Server-owned prompt defaults

- affected actor or system: prompt registry, Pipeline Prompt Management, and LLM runtime
- required result: packaged prompt templates remain canonical; persistence stores only optional task replacement text
- success condition: default prompt upgrades do not copy or fork defaults into user storage, and custom replacements are validated before runtime use

### Outcome: Scalar retry and recovery settings

- affected actor or system: request retry, queue scheduling, worker lease, reconciler, and error retention
- required result: System stores Maximum Attempts, Initial Backoff, Lease, Reconciler Interval, and Error Detail Limit under one revisioned resource
- success condition: all runtime consumers derive the same retry schedule and recovery limits from that resource

### Outcome: Separate lifecycle ownership

- affected actor or system: data relocation, diagnostics, and process lifecycle
- required result: Lifecycle owns data location and lifecycle actions; System owns configuration and backup/import
- success condition: no setting appears in both pages and all lifecycle actions preserve idle/restart safety

### Outcome: Production integration proof

- affected actor or system: tests and maintained contracts
- required result: obsolete drawer/string assertions are replaced by route, API, integration, and browser behavior coverage
- success condition: tests prove real URLs, history restoration, backend state transitions, accessibility, and security boundaries

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| Does the backend already own canonical Runs and Run Details resources? | `GET /runs`, `GET /runs/{run_id}`, stage/job/event APIs, and `/admin/runs/{run_id}` exist. | `src/fitcv_cp/app.py` | high | Reuse these owners; delete Settings duplicate implementation. |
| Is Settings Trigger Run aligned with backend identity? | Settings reads/submits obsolete Candidate Profile fields while run creation requires `profile_id`. | `src/fitcv_cp/templates/settings.html`, `src/fitcv_cp/app.py` | high | Trigger Run must use canonical Candidate Profile resources and `profile_id`. |
| Does Candidate Profile reverse Runs have an existing consumer contract? | `GET /candidate-profiles/{profile_id}/runs` exists and is typed. | `src/fitcv_cp/app.py` | high | Retain route for other consumers; Profile UI must not call it. |
| Are provider credentials already abstracted? | `local_credentials.py` uses keyring and exposes configured/get/set/delete operations. | `src/fitcv_cp/local_credentials.py` | high | Keep credential values behind this boundary and bind it to one provider registry. |
| Is provider state canonical today? | Onboarding builds one `ProviderSetup`, writes routing overlay, and stores provider test state separately. | `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/local_setup.py` | high | Replace onboarding ownership with registry-service calls; no dual write. |
| Are task IDs already canonical? | Runtime routing and prompt registry use four IDs: `enrich_extraction`, `ranking_ai_score`, `cv_generation_structured_write`, and `synonym_triage_recommendation`. | `src/fitcv/config.py`, `src/fitcv/prompts/registry.py` | high | Preserve IDs; use approved display labels in UI. |
| Does CV Analysis currently use an LLM route? | It is absent from supported model-routing and prompt task registries. | `src/fitcv/config.py`, runtime routing tests | high | Exclude CV Analysis from LLM and Prompt configuration. |
| Are prompt defaults server-owned? | Prompt registry resolves packaged template files; runtime currently injects optional addenda. | `src/fitcv/prompts` | high | Keep templates canonical and replace addenda persistence with optional replacement text. |
| Is retry configuration scalar today? | Runtime uses `backoff_seconds` sequence; queue passes sequence to RQ. | `src/fitcv_cp/retry_settings.py`, `src/fitcv_cp/queue.py` | high | Replace persisted sequence with one fixed scalar Initial Backoff. |
| Are local security guards available? | Packaged mode creates one CSRF token and enforces local Host/Origin rules. | `src/fitcv_cp/app.py`, local distribution spec | high | Mount pages/APIs only in packaged-local mode and reuse global guard. |
| Can GitNexus provide current high-trust ownership evidence? | Repository index is 25 commits behind and full-text indexes are missing. | GitNexus status/query, July 22, 2026 | high | Source and tests remain authority; stale graph output is not used for contract claims. |

### Scope

- included behavior:
  - shared application shell, navigation, theme, shutdown, real URLs, query-state restoration, and back navigation
  - Runs, Run Details, Candidate Profiles, Candidate Profile Details, Bookmarks, and Synonyms integration behavior
  - Pipeline settings IA and Prompt Management
  - API Provider catalog, custom providers, one connection per provider, connection verification, credential boundary, provider models, and model verification
  - Default Route and task-specific LLM model, timeout, and temperature
  - server-owned default prompts and optional task replacement text
  - System backup/import, request retry, worker recovery, and separate Lifecycle page
  - canonical API envelopes, validation, revisions, idempotency, errors, migration, security, and test coverage
- affected boundaries:
  - Jinja templates and shared frontend assets
  - FastAPI HTML and JSON routes
  - SQLite-backed mutable configuration and registry state
  - Windows Credential Manager
  - packaged control-plane defaults and prompt resources
  - queue, worker, reconciler, and LLM runtime consumers
- admissible cases:
  - first launch, incomplete onboarding, upgraded packaged install, direct deep link, connected/disconnected providers, stale models, empty model registry, active work, idle work, and imported legacy configuration
- compatibility expectation:
  - existing durable domain API routes remain available unless explicitly retired below
  - existing server/developer mode behavior remains unchanged because new integrated application pages and configuration APIs are packaged-local-only

### Non-Goals

- remote or hosted deployment of the integrated shell
- user accounts, login, sessions, RBAC, tenants, or multi-user concurrency semantics
- multiple connections per provider
- automatic provider model discovery as the source of routing eligibility
- OAuth provider authentication
- arbitrary provider plugin or SDK framework
- automatic prompt generation, prompt version marketplace, or shared prompt library
- CV Analysis LLM configuration
- mobile-native or desktop-native UI rewrite
- forced shutdown or automatic cancellation of active work
- new frontend framework solely for routing
- retaining prototype hash routes as production aliases

### Contract Ownership

| Concern | Canonical owner | Consumers | Forbidden parallel owner |
|---|---|---|---|
| Page URL and navigation state | FastAPI route map plus shared shell navigation contract | browser, templates, browser tests | prototype hash router or page-local route tables |
| Runs and Run Details | existing Runs APIs and run store | Runs page, Run Details page, Bookmarks, exports | Settings-local Run arrays or duplicate drawer |
| Candidate Profiles | existing Candidate Profile APIs and store | Profiles page, Trigger Run | uploaded-file lists or Settings-local copies |
| Reverse profile-to-Runs relation | `GET /candidate-profiles/{profile_id}/runs` | non-Profile consumers only | Candidate Profile Details UI |
| Provider definitions/connections/models | provider registry service | onboarding, API Providers, LLM routing, readiness, diagnostics | onboarding JSON/overlay provider registry |
| API key values | Windows Credential Manager through credential service | connection test and runtime adapter | SQLite, YAML, browser storage, logs, responses, backups |
| Default prompt text | packaged prompt registry/templates | Prompt Management read view, runtime renderer | SQLite or local overlay copy |
| Custom prompt text | task prompt configuration store | Prompt Management and runtime renderer | prompt addenda overlay |
| LLM routing | LLM configuration resource referencing provider model registry | runtime routing and UI | copied provider/model strings in task settings |
| Retry/recovery | System settings resource | queue, worker, reconciler, UI | control-plane backoff list plus separate UI values |
| Theme | browser-local preference | shared shell | backend setting or Appearance page |

### Requirements and Behavioral Contract

#### Requirement: Packaged-local-only availability

- trigger or actor: request reaches integrated HTML or configuration API route
- preconditions: application runs in packaged local mode and request passes loopback Host validation
- required behavior: integrated routes are mounted only in packaged local mode; unsafe requests also require same-origin validation and CSRF
- output or state change: valid local request proceeds; non-local mode does not advertise or expose these capabilities
- failure behavior: unavailable packaged-only routes return `404`; Host/Origin/CSRF failures use existing security response behavior and never reveal secrets
- observable acceptance: server/developer mode route inventory excludes new pages/APIs, while packaged mode exposes them

#### Requirement: Shared shell and real URLs

- trigger or actor: user opens or navigates among application pages
- preconditions: target URL belongs to canonical page map
- required behavior:
  - every page extends one shared Jinja shell owning sidebar, header, global actions, theme bootstrap, focus target, and shared assets
  - every canonical URL returns a complete usable HTML document on direct request
  - when JavaScript is available, same-origin shell navigation is progressively enhanced with the History API and page-content replacement without a full shell reload; server URLs remain the only route truth
  - no production page uses `location.hash` as route or entity identity
  - URL query parameters own collection view, search, filters, sort, page, and selected tab when state is shareable/restorable
  - user navigation writes one `history.pushState`; normalization/default removal uses `history.replaceState`; `popstate` restores from URL without adding another entry
  - failed enhanced navigation leaves current valid page intact and offers retry or normal navigation
- output or state change: URL, document title, active sidebar item, page heading, focus, and rendered data describe one route
- failure behavior: invalid query values normalize once with `replaceState`; missing entities render bounded 404 page state
- observable acceptance: direct URL, refresh, Back, Forward, copied link, and JavaScript-disabled navigation resolve equivalent server-owned content

#### Requirement: Parent navigation from detail pages

- trigger or actor: user opens Run Details, Candidate Profile Details, or Provider Details
- preconditions: entity detail URL is valid
- required behavior:
  - page exposes `Back to Runs`, `Back to Candidate Profiles`, or `Back to API Providers`
  - if navigation originated from same collection, back link preserves validated collection path/query in `history.state`
  - direct loads or invalid return targets fall back to canonical collection URL
  - return targets must be same-origin and restricted to matching parent route; arbitrary redirects are rejected
- output or state change: user returns to prior collection filter/page where available
- failure behavior: missing history state never disables back link
- observable acceptance: back link and browser Back both behave predictably after filtered collection navigation and direct deep links

#### Requirement: Global navigation, theme, and shutdown

- trigger or actor: user uses shared header/sidebar
- preconditions: packaged shell rendered
- required behavior:
  - sidebar order is Workspace: Runs, Candidate Profiles, Bookmarks, Synonyms; Pipeline: Overview, stage/settings sections, Prompt Management; Application: API Providers, LLM Configuration, System, Lifecycle
  - Health and Appearance are absent from sidebar
  - header theme action precedes Shutdown FitCV
  - light theme shows moon icon with accessible name `Switch to dark theme`; dark theme shows sun icon with `Switch to light theme`
  - theme and shutdown use same borderless icon-button rest contract; shutdown retains danger semantics
  - title icons use fixed non-shrinking dimensions
  - Shutdown opens confirmation, consumes backend action capability derived from canonical active-work evaluation, prevents duplicate submission, and posts only to canonical shutdown route
- output or state change: theme persists in browser local storage; successful shutdown transitions to stopped page
- failure behavior: active-work shutdown returns conflict and preserves running service/page state
- observable acceptance: light/dark, narrow, keyboard, focus, active-work, cancellation, and success states pass

#### Requirement: Runs collection and Trigger Run

- trigger or actor: user opens Runs or submits Trigger Run
- preconditions: canonical Candidate Profile collection and run APIs available
- required behavior:
  - Runs page is the only collection implementation
  - collection URL owns `view`, `search`, `page`, and supported filters
  - Trigger Run loads only Active + Succeeded Candidate Profiles and submits `profile_id`
  - job file and optional run name follow existing canonical run contract and limits
  - no available profile disables Trigger and links to Candidate Profiles
  - submit prevents duplicates and preserves entered values on recoverable failure
- output or state change: successful create returns canonical Run and navigates to its dedicated Run Details URL
- failure behavior: invalid profile, stale archived profile, invalid file, enqueue failure, and conflict use canonical error envelope; persisted failed Run remains visible where existing contract requires it
- observable acceptance: no Settings code or data store renders/owns Runs

#### Requirement: Dedicated Run Details

- trigger or actor: user opens `/admin/runs/{run_id}`
- preconditions: Run exists or canonical API can return not found
- required behavior:
  - page uses existing Run detail/stage/job/event APIs
  - page sections use one parent-owned gap and shared section component
  - heading does not repeat lifecycle status already shown in Overview
  - active Runs preserve bounded refresh/stale behavior and do not erase last valid data during refresh
  - Run actions, bookmarks, exports, CV actions, and console behavior continue to follow their durable contracts
- output or state change: one dedicated page reflects canonical Run state
- failure behavior: missing Run renders bounded 404; partial endpoint failure identifies affected section and permits retry without discarding other valid sections
- observable acceptance: no drawer implementation or drawer-specific test remains

#### Requirement: Candidate Profiles collection and dedicated details

- trigger or actor: user opens collection/detail or imports/archives/restores profile
- preconditions: existing Candidate Profile APIs available
- required behavior:
  - collection uses real query state and existing resource identity/revision
  - details page uses `GET /candidate-profiles/{profile_id}` only
  - details page omits reverse Runs, `Used by Runs`, and related Run lists/count presentation
  - frontend never calls `GET /candidate-profiles/{profile_id}/runs`
  - backend retains that route unchanged for other consumers
  - failed imports and archived profiles remain inspectable according to existing durable profile contract
  - archive/restore use expected revision and idempotency behavior
- output or state change: collection/detail reflect canonical lifecycle state
- failure behavior: stale revision returns conflict and reload action; missing profile returns bounded 404 without raw upload leakage
- observable acceptance: detail cost and layout do not grow with related Run count

#### Requirement: Bookmarks and Synonyms

- trigger or actor: user opens Bookmarks or Synonyms and performs existing actions
- preconditions: durable central-workspace contracts available
- required behavior:
  - pages remain first-class shell routes and use their canonical normalized APIs
  - Bookmark Run cells show linked Run ID only; `Active run` or duplicate lifecycle copy is absent
  - row hover, section boundaries, tables, filters, selection, exports, and empty/error states use shared components/tokens
  - Synonym Recommendation remains display label only; backend task ID remains `synonym_triage_recommendation`
  - existing synonym policy/review/backup contracts remain unchanged unless prompt routing is involved
- output or state change: existing bookmark/synonym resource transitions persist normally
- failure behavior: stale selection, conflicts, partial export, and validation use existing canonical errors
- observable acceptance: no page-specific duplicate hover/border behavior remains

#### Requirement: Pipeline settings and Prompt Management IA

- trigger or actor: user opens Pipeline navigation
- preconditions: pipeline settings resource available
- required behavior:
  - `/admin/settings` is Pipeline Overview and contains no Runs collection or Run Details UI
  - section URLs are real routes under `/admin/settings/{section}`
  - supported sections are `enrichment`, `screening`, `shortlisting`, `ranking`, `cv-analysis`, `cv-generation`, `runtime-limits`, `automation-reuse`, and `prompt-management`
  - existing pipeline-owned settings continue through `GET/PATCH /settings/pipeline` and reset action
  - Prompt Management uses its dedicated section URL but remains under Pipeline navigation
  - Request Retry, Worker Recovery, provider, model routing, and lifecycle controls are not duplicated in Pipeline settings
- output or state change: pipeline settings save under existing revision/ETag contract
- failure behavior: unsupported/read-only keys remain rejected; stale revisions return `settings_revision_conflict`
- observable acceptance: each setting has one navigation location and one backend owner

#### Requirement: Provider catalog and custom providers

- trigger or actor: user opens API Providers or creates custom provider
- preconditions: packaged provider registry initialized
- required behavior:
  - API Key Providers contains immutable predefined definitions for OpenAI, Anthropic, DeepSeek, and Groq
  - Custom Providers contains user-created OpenAI-compatible or Anthropic-compatible definitions
  - collection rows show exactly `Connected` or `No connection`; connection counts are absent
  - predefined Base URL and protocol are packaged defaults and cannot be changed through API
  - custom provider definitions require unique Display Name and compatibility type; their connection owns editable Base URL
  - one provider ID owns at most one connection
  - custom provider deletion requires confirmation, removes its connection metadata/model records, deletes credential from Windows Credential Manager, and rejects deletion while referenced by active LLM configuration
- output or state change: custom provider metadata persists in canonical registry
- failure behavior: duplicate name, invalid URL, unsupported protocol/API type, predefined mutation, or active reference returns stable field/conflict error
- observable acceptance: onboarding-created and application-created providers appear in same collection without merge logic in frontend

#### Requirement: Provider connection verification and persistence

- trigger or actor: user tests then adds/updates/removes provider connection
- preconditions: provider exists
- required behavior:
  - form fields are Base URL, API Key, and API Type; Model ID is absent
  - predefined Base URL is disabled; custom Base URL is editable
  - OpenAI-compatible API Type supports `chat_completions` and `responses`
  - Anthropic-compatible API Type is disabled and fixed to `messages`
  - existing API key is represented only by `credential_configured=true`; value is never returned
  - Test validates exact current draft using submitted key or existing stored credential and returns bounded validation result without persistence
  - Test does not persist or stage submitted API key; Add/Update resubmits same in-memory key or explicitly reuses existing credential
  - frontend enables Add/Update only while current fields exactly match latest successful Test; editing any tested field or key invalidates that local UI state
  - Add/Update reruns same backend connection validator before commit and never trusts frontend Test state
  - API key replacement is written to Windows Credential Manager only inside successful Add/Update transaction
  - `Connected` means persisted connection status `verified`; a successful test alone does not change collection status
  - existing verified connection remains active after failed test/update; it changes only after successful verified replacement
  - Remove Connection returns `409 model_in_use` while Default Route or any task references provider models
  - after references are removed, Remove Connection deletes credential and connection verification state, retains model metadata as `needs_retest`, disables model actions, and makes models ineligible for routing
- output or state change: one verified connection revision persists without secret value
- failure behavior: unavailable provider, missing key, failed test, expired/mismatched token, credential-store failure, or revision conflict leaves prior verified connection unchanged
- observable acceptance: DB, YAML, logs, responses, browser storage, diagnostics, and backups contain no API key canary

#### Requirement: Provider model registry

- trigger or actor: user tests/adds/retests/removes model
- preconditions: provider connection is verified
- required behavior:
  - without verified connection, Available Models is disabled and explains connection requirement
  - Add Model accepts one provider model identifier and exposes text-only Test action
  - Test validates provider ID, current connection revision, and normalized model identifier without persistence
  - frontend enables Add Model only while identifier exactly matches latest successful Test
  - Add Model reruns same backend model validator before commit and never trusts frontend Test state
  - duplicate model identifier within provider is rejected case-sensitively after surrounding whitespace normalization
  - saved row exposes Test and Remove only
  - model states are `validated` or `needs_retest`; removed is deletion, not a disabled state
  - connection, Base URL, API Type, or credential revision change marks all provider models `needs_retest`
  - retest success returns model to `validated`; retest failure preserves row as `needs_retest`
  - only `validated` models on a verified connection are routing eligible
- output or state change: provider-scoped model record and verification metadata persist
- failure behavior: invalid identifier, duplicate, stale provider revision, disconnected provider, transport failure, or active configuration reference produces stable error and preserves prior record
- observable acceptance: routing selector options derive from registry query rather than copied model lists

#### Requirement: LLM Configuration

- trigger or actor: user opens or saves LLM Configuration
- preconditions: provider registry available
- required behavior:
  - resource contains one Default Route and exactly four task entries
  - task IDs and labels are:
    - `enrich_extraction` — Enrich Extraction
    - `ranking_ai_score` — Ranking AI Score
    - `cv_generation_structured_write` — CV Generation
    - `synonym_triage_recommendation` — Synonym Recommendation
  - CV Analysis is absent
  - model options are `Default` for task rows plus routing-eligible provider models
  - Default Route may be null only while no routing-eligible model exists; this is an explicit incomplete-readiness state that blocks new LLM work
  - once eligible models exist, saving LLM Configuration requires Default Route to reference one of them and has no implicit arbitrary fallback
  - task `model_ref=null` means inherit Default Route
  - each task stores Timeout seconds and Temperature
  - Timeout default is `120`, minimum `1`, maximum `3600`
  - Temperature default is `0.2`, minimum `0`, maximum `2`, step/precision `0.1`
  - runtime resolves model reference to provider connection revision, API type, credential handle, and model ID at request time
  - run snapshots record effective provider ID, connection revision, model record ID, model ID, timeout, temperature, and configuration revision
  - if a referenced model becomes ineligible after connection update, configuration keeps explicit unavailable reference and blocks affected LLM work until user selects eligible model; no automatic repair or unrelated substitution occurs
  - built-in Synonym Recommendation fallback remains available only under its existing runtime fallback rule; UI does not describe provider routing implementation
- output or state change: one revisioned LLM configuration persists
- failure behavior: unavailable model, invalid number, stale revision, or credential/provider loss returns stable error and preserves prior configuration
- observable acceptance: runtime no longer hardcodes task temperature and all four tasks resolve through same owner

#### Requirement: Prompt Management

- trigger or actor: user opens/saves prompt for one supported task
- preconditions: server prompt registry contains task prompt definition
- required behavior:
  - groups are Pipeline Prompts: Enrich Extraction, Ranking AI Score, CV Generation; Synonym Prompts: Synonym Recommendation
  - GET response includes task ID, display label, canonical prompt ID/version, canonical editable default template text, required runtime variables, mode, optional replacement text, migration state, and revision
  - `Default` mode stores no prompt text and renders current packaged default
  - selecting `Custom` initializes editor from current default in browser memory; nothing persists until Save
  - Custom Save requires normalized non-empty text that differs from current default
  - replacement is a full task template used instead of default template; it must retain all required runtime variables and contain no unsupported variables
  - `prompt_addendum` is a retired customization slot, not a runtime variable; it is absent from new packaged templates, editable default text, and replacement validation
  - newline normalization is CRLF/CR to LF; meaningful user whitespace is otherwise preserved
  - new/updated replacement maximum is 4000 characters; UI shows count, warning at 3800, and prevents input beyond 4000
  - persistence stores only optional replacement text plus task identity/revision metadata; canonical default text is never copied to mutable storage
  - runtime uses replacement when present, otherwise packaged default, through one renderer
  - dirty dialog close requires discard confirmation; Save affects one task only
- output or state change: task prompt configuration revision increments
- failure behavior: empty/unchanged/oversize replacement, missing/unknown variables, stale revision, or missing task returns field/conflict error and leaves prior prompt active
- observable acceptance: packaged default file changes appear immediately for Default mode without data migration

#### Requirement: System settings

- trigger or actor: user opens System or saves retry/recovery values
- preconditions: packaged-local mode
- required behavior:
  - System contains Data & Backup, Request Retry, and Worker Recovery only
  - Data & Backup shows resolved database location, Download Backup, and Import Backup/Restore confirmation
  - backup/import continue to follow `fitcv-backup.v1`, idle-work, validation, atomic replacement, restart, and secret-exclusion rules
  - Request Retry fields and defaults are:
    - Maximum Attempts: default `3`, range `1..10`, includes initial attempt
    - Initial Backoff seconds: default `10`, range `0..3600`
    - Error Detail Limit characters: default `10000`, range `1000..100000`
  - Worker Recovery fields and defaults are:
    - Lease seconds: default `300`, range `30..86400`
    - Reconciler Interval seconds: default `30`, range `5..3600`
  - no separate retry-enabled toggle exists; Maximum Attempts `1` means no retry
  - Initial Backoff is a fixed delay used before every retry; no multiplier, jitter, or separate cap is applied beyond the field maximum
  - queue, packaged executor, worker, reconciler, and error artifact writers read the same effective resource
  - System does not duplicate theme, shutdown, data relocation, or diagnostics
- output or state change: one revisioned System settings resource persists
- failure behavior: out-of-range values, stale revision, persistence failure, active-work backup/import, invalid archive, or duplicate submission preserve prior state and return canonical error
- observable acceptance: arbitrary backoff list is absent from API, persistence, UI, and runtime configuration

#### Requirement: Lifecycle page

- trigger or actor: user opens Lifecycle or requests relocation/diagnostics
- preconditions: packaged-local mode
- required behavior:
  - Lifecycle shows active data root, Change Data Location, and diagnostics download
  - Change Data Location uses existing cold relocation contract, native folder picker where available, destination validation, active-work rejection, restart requirement, and recoverable rollback
  - diagnostics uses existing redaction/exclusion contract
  - Lifecycle does not duplicate backup/import, retry, worker recovery, theme, or shutdown section
  - shutdown remains global header action, not Lifecycle content
- output or state change: successful relocation schedules restart with new bootstrap pointer only after validated copy
- failure behavior: invalid destination, insufficient space, active work, copy/validation failure, or unsupported folder picker leaves current data root active
- observable acceptance: System and Lifecycle have disjoint settings/actions except shared read-only local status

#### Requirement: Async and form state model

- trigger or actor: any frontend data request or unsafe action
- preconditions: page is mounted
- required behavior:
  - every async surface models initial loading, success, empty, filtered empty, error, retry, stale/refreshing, disabled, and duplicate-submit states where applicable
  - prior valid data remains visible during refresh with non-blocking stale indicator
  - form submit disables only conflicting actions, exposes pending text, and restores controls on recoverable failure
  - success messages use `role=status`; validation/destructive errors use `role=alert` only when immediate interruption is required
  - server field errors map to labeled controls; summary links focus first invalid control
  - cancellation closes modal/dialog without mutation and restores focus to invoker
- output or state change: user can determine current state and recover without re-entering unaffected values
- failure behavior: network/parse/unexpected errors show bounded generic message and log no secret/request body
- observable acceptance: browser tests cover each material state rather than only HTML strings

## Design Decisions

### Decision: Canonical page URL map

| Area | Canonical URL | Notes |
|---|---|---|
| Runs | `/admin/runs` | Query owns view/search/page/filter state. |
| Run Details | `/admin/runs/{run_id}` | Existing dedicated route; no drawer alias. |
| Candidate Profiles | `/admin/candidate-profiles` | Query owns view/status/search/page. |
| Candidate Profile Details | `/admin/candidate-profiles/{profile_id}` | New dedicated page. |
| Bookmarks | `/admin/bookmarks` | Query owns stage/result/search/page. |
| Synonyms | `/admin/synonyms` | Query owns type/status/search/page/tab. |
| Pipeline Overview | `/admin/settings` | Existing route, duplicate Runs removed. |
| Pipeline section | `/admin/settings/{section}` | Includes `prompt-management`. |
| API Providers | `/admin/api-providers` | Packaged-local-only. |
| Provider Details | `/admin/api-providers/{provider_id}` | Packaged-local-only. |
| LLM Configuration | `/admin/llm-configuration` | Packaged-local-only. |
| System | `/admin/system` | Backup/import plus retry/recovery. |
| Lifecycle | `/admin/lifecycle` | Data location and diagnostics. |

- Existing GET `/local/data` redirects to `/admin/system`.
- Existing GET `/local/system` redirects to `/admin/lifecycle`.
- Existing unsafe `/local/data/*` and `/local/system/*` action routes remain canonical until a separate approved API-version migration; redirecting unsafe methods is forbidden.
- `/local/onboarding` remains first-run flow only. After completion, it redirects to `/admin/runs` and uses canonical provider/LLM APIs rather than owning provider state.

### Decision: Canonical JSON API map

#### Existing resources retained

| Method and route | Contract |
|---|---|
| `GET /runs` | Run collection. |
| `POST /runs` | Trigger Run using `profile_id`. |
| `GET /runs/{run_id}` and subordinate routes | Run Details, stages, jobs, events, exports, actions. |
| `GET/POST /candidate-profiles` | Profile collection/create. |
| `GET /candidate-profiles/{profile_id}` | Profile detail. |
| `GET /candidate-profiles/{profile_id}/runs` | Retained for non-Profile consumers; not called by Profile UI. |
| Candidate Profile archive/restore routes | Existing lifecycle actions with revision/idempotency. |
| Bookmark and Synonym routes | Existing durable central-workspace contracts. |
| `GET/PATCH /settings/pipeline` and reset | Existing pipeline settings revision contract. |

#### Provider registry

| Method and route | Request/result |
|---|---|
| `GET /api-providers` | Collection plus counts/filter metadata; never secret values. |
| `POST /api-providers` | Create custom provider; requires `Idempotency-Key`. |
| `GET /api-providers/{provider_id}` | Provider, connection summary, and models. |
| `PATCH /api-providers/{provider_id}` | Update custom Display Name with expected revision. Compatibility is immutable after creation. |
| `DELETE /api-providers/{provider_id}` | Delete unreferenced custom provider with expected revision. |
| `POST /api-providers/{provider_id}/connection/actions/test` | Test exact connection draft; returns bounded result, no persistence. |
| `PUT /api-providers/{provider_id}/connection` | Revalidate and add/update one connection with expected provider revision. |
| `DELETE /api-providers/{provider_id}/connection` | Remove connection and credential; requires expected revision. |
| `POST /api-providers/{provider_id}/models/actions/test` | Test unsaved model identifier; returns bounded result, no persistence. |
| `POST /api-providers/{provider_id}/models` | Revalidate and add model; requires `Idempotency-Key`. |
| `POST /api-providers/{provider_id}/models/{model_record_id}/actions/test` | Retest saved model against current connection revision. |
| `DELETE /api-providers/{provider_id}/models/{model_record_id}` | Remove model or return conflict when actively referenced. |

#### LLM and prompt configuration

| Method and route | Request/result |
|---|---|
| `GET /llm-configuration` | Default Route, four task configurations, eligible model options, revision/ETag. |
| `PATCH /llm-configuration` | Partial default/task changes with expected revision; atomic validation. |
| `GET /prompt-configurations` | Four task prompt resources with server defaults and optional replacements. |
| `PATCH /prompt-configurations/{task_id}` | Set `replacement_text` or `null` with expected revision. |

#### System and lifecycle

| Method and route | Request/result |
|---|---|
| `GET /system-settings` | Retry/recovery values, bounds, defaults, revision/ETag. |
| `PATCH /system-settings` | Atomic validated changes with expected revision. |
| `GET /local/data/status` | Resolved data/database/backup status without secrets. |
| `POST /local/data/backup` | Existing backup stream contract. |
| `POST /local/data/import` | Existing validated cold import/restart contract. |
| `GET /local/lifecycle/status` | Data root, active-work reasons, action capabilities, folder-picker support, and diagnostics capability. |
| `POST /local/data/relocate` | Existing validated cold relocation/restart contract. |
| `GET /local/system/diagnostics` | Existing sanitized ZIP. |
| `POST /local/system/shutdown` | Existing confirmed idle shutdown. |

### Decision: Canonical request models

- All JSON request fields use `snake_case`.
- `CreateCustomProviderRequest`:
  - `display_name`: required, trimmed, unique case-insensitively
  - `compatibility`: `openai | anthropic`
- `UpdateCustomProviderRequest`:
  - optional `display_name`
  - `expected_revision`: required
- `ConnectionTestRequest`:
  - `base_url`: required for custom providers; omitted for predefined providers
  - `api_type`: required for configurable providers; fixed value may be omitted
  - `api_key`: optional only when an existing stored credential may be reused; otherwise required
- `ConnectionWriteRequest`:
  - same draft fields as test
  - `expected_revision`: required provider revision
- `ModelTestRequest`:
  - `model_id`: required, trimmed, non-empty, maximum 255 characters
- `ModelCreateRequest`:
  - `model_id`: required
  - `expected_revision`: required provider revision
- `LlmConfigurationPatchRequest`:
  - optional `default_model_ref`: model record ID or null
  - optional `tasks`: mapping of canonical task ID to partial `model_ref`, `timeout_seconds`, and `temperature`
  - `expected_revision`: required
- `PromptConfigurationPatchRequest`:
  - `replacement_text`: string or null
  - `expected_revision`: required
- `SystemSettingsPatchRequest`:
  - optional `maximum_attempts`
  - optional `initial_backoff_seconds`
  - optional `lease_seconds`
  - optional `reconciler_interval_seconds`
  - optional `error_detail_limit`
  - `expected_revision`: required
- Partial configuration patches validate the complete resulting resource atomically. Unknown fields are rejected rather than ignored.

### Decision: Common resource and error conventions

- JSON success uses existing `{ "data": ... }`; collections additionally use existing `page` and `meta` members.
- Mutable singleton resources return `revision`, `updated_at`, and `ETag`.
- Mutable provider/model resources return integer `revision`; prompt, LLM, Pipeline, and System configuration use opaque revision strings or integers consistently with their owning store.
- Writes use request-body `expected_revision` as the sole concurrency input; responses may expose `ETag` for cache/reload diagnostics but writes do not accept a second revision channel.
- Existing error envelope remains:
  - `error.code`
  - `error.message`
  - `error.field_errors[]`
  - `error.retryable`
  - `error.action`
- Stable codes added by this scope include:
  - `provider_not_found`
  - `provider_predefined_read_only`
  - `provider_name_conflict`
  - `provider_connection_required`
  - `provider_connection_test_failed`
  - `credential_store_failed`
  - `model_not_found`
  - `model_already_exists`
  - `model_test_failed`
  - `model_needs_retest`
  - `model_in_use`
  - `llm_configuration_invalid`
  - `prompt_configuration_invalid`
  - `system_settings_revision_conflict`
  - `active_work_conflict`
- `404` owns missing resource/unmounted packaged capability, `409` owns stale revisions/state conflicts, `422` owns field validation, `503` owns retryable provider/credential/native-service unavailability, and `500` owns unexpected persistence failure.
- API key, prompt replacement, uploaded archive contents, and raw candidate/job/CV content never appear in error messages, logs, telemetry, or diagnostics.

### Decision: Provider registry data model

#### Provider resource

- `provider_id`: opaque stable ID
- predefined IDs are `openai`, `anthropic`, `deepseek`, and `groq`; custom IDs are server-generated and never derived from mutable Display Name
- `kind`: `predefined | custom`
- `display_name`
- `compatibility`: `openai | anthropic`
- `base_url`: fixed packaged value for predefined providers, persisted connection value for connected custom providers, otherwise null
- `base_url_editable`
- `supported_api_types[]`
- `api_type_fixed`
- `connection_status`: `verified | not_configured`
- `credential_configured`: boolean
- `connection_revision`: integer or null
- `model_count`
- `eligible_model_count`
- `revision`
- `capabilities`: create/update/delete/test/remove flags

#### Connection persistence

- one row per `provider_id`
- persisted fields: provider ID, normalized Base URL when custom, API type, verification status, verification timestamp, connection revision, credential account handle, metadata timestamps
- forbidden fields: API key value, authorization header, model IDs
- credential account naming is deterministic from provider ID and service namespace; account handle may persist, secret may not

#### Model resource

- `model_record_id`: server-generated opaque ID used in URLs
- `provider_id`
- `model_id`: provider-supplied identifier
- `validation_status`: `validated | needs_retest`
- `validated_connection_revision`
- `last_tested_at`
- `last_test_error_code`: bounded non-secret code or null
- `revision`

### Decision: LLM and prompt data model

#### LLM configuration resource

- `default_model_ref`: model record ID or null
- `tasks`: mapping of four canonical task IDs to:
  - `model_ref`: model record ID or null for Default
  - `timeout_seconds`
  - `temperature`
- `revision`
- `updated_at`
- derived eligible model options are response metadata, not persisted copies

#### Prompt configuration resource

- `task_id`
- derived `display_name`, `group`, `prompt_id`, `prompt_version`, `default_text`, and `required_runtime_variables`
- persisted `replacement_text`: string or null
- derived `mode`: `custom` when replacement exists, otherwise `default`
- derived `migration_state`: `clean | needs_review`
- `revision`
- `updated_at`
- default text is never stored in mutable settings or snapshots; Run artifacts record prompt ID/version and replacement hash/character count, not secret-bearing full prompt unless an existing artifact contract explicitly requires rendered prompt retention

### Decision: Persistence ownership

- Packaged resources remain immutable defaults:
  - predefined provider definitions
  - supported API types and fixed Base URLs
  - default LLM task values
  - default System setting values/bounds
  - canonical prompt templates and prompt registry
- SQLite under active data root owns mutable non-secret state:
  - custom provider definitions
  - provider connection metadata and revisions
  - provider model registry and validation state
  - LLM configuration
  - prompt replacement text
  - System retry/recovery settings
  - migration markers and non-secret audit timestamps
- Windows Credential Manager exclusively owns API key values.
- `%APPDATA%\FitCV\bootstrap.json` continues to own only active data-root pointer and minimal bootstrap metadata.
- `onboarding.json` may retain wizard completion/progress only; provider, connection, model, LLM, prompt, and retry values are forbidden after migration.
- local controller overlay stops being mutable owner for provider/model/prompt/retry settings after cutover. Runtime compatibility adapters may read canonical registry/settings and project effective configuration in memory, but must not persist a second representation.

### Decision: Revision, idempotency, and concurrency

- Local single-user scope does not remove stale-tab protection.
- All configuration writes require expected revision and are atomic.
- Resource creation and non-idempotent action routes require `Idempotency-Key` where duplicate execution can create durable state or files.
- Same idempotency key plus same fingerprint replays prior response; same key plus different fingerprint returns conflict.
- Provider connection save, provider/model deletion, LLM configuration writes, and credential mutation must leave either prior complete state or new complete state; partial DB/credential success must be compensated or reported as blocked without claiming success.
- Browser duplicate-submit prevention supplements but never replaces backend idempotency/revision checks.

### Decision: Active-work capability ownership

- Existing backend `active_work_reasons()` remains sole owner for backup, import, relocation, and shutdown safety.
- Active work includes process executor busy state and Runs in `queued`, `running`, `awaiting_continue`, or `cancelling` status.
- Local status resources expose bounded `active_work_reasons[]` plus `can_backup`, `can_import`, `can_relocate`, and `can_shutdown`.
- Frontend renders disabled states and explanations from capabilities; it does not reproduce status enums or infer safety from visible Runs.

### Decision: Migration and cutover

#### Frontend cutover

- Delete Runs collection and Run Details drawer code from Settings.
- Replace Candidate Profile modal/drawer with dedicated detail template and route.
- Replace hash links with canonical server URLs.
- Existing bookmarks/synonyms/runs/profile APIs remain; frontend adapters change only where required by canonical payloads.
- Old GET page URLs redirect as defined above; no hash-route compatibility layer is retained.

#### Provider/onboarding cutover

- Migration runs once before canonical registry is writable.
- If legacy onboarding/provider overlay exists and registry is empty:
  - import supported provider metadata into predefined provider or one custom compatible provider
  - copy credential inside Credential Manager from legacy account to canonical provider account, then delete legacy account only after verification of new lookup
  - import configured model strings as provider model records marked `needs_retest`
  - import routing references only after matching model records exist; imported references remain ineligible until retest
  - collection displays `No connection` until canonical connection test succeeds because legacy state lacks required connection revision/fingerprint proof
- After successful migration, remove provider/model/routing values from onboarding state and retire mutable overlay writes.
- Migration is restart-safe and idempotent. Failure keeps legacy state untouched and blocks canonical write UI with actionable migration error; it never starts dual-write mode.
- Provider migration does not reset completed onboarding. It blocks only actions requiring a verified provider/model until canonical retest succeeds.

#### Prompt cutover

- New packaged prompt templates remove reserved `${prompt_addendum}` customization slot while preserving all runtime context variables.
- Each legacy non-empty addendum becomes one full replacement template by applying existing addendum composition to legacy template before slot removal.
- Resulting replacement preserves current effective behavior and becomes the only mutable prompt owner.
- If migrated replacement exceeds 4000 characters, it is grandfathered as `needs_review`: runtime continues using it, editor allows deletion, and Save remains disabled until text is at most 4000 characters and otherwise valid.
- Empty addenda migrate to null replacement.
- After successful migration, prompt addenda keys are removed from mutable overlay and runtime no longer reads them.

#### Retry cutover

- Legacy `enabled=false` migrates to Maximum Attempts `1`.
- Legacy `enabled=true` preserves Maximum Attempts.
- Initial Backoff becomes first legacy `backoff_seconds` value; missing/empty sequence uses new default `10`.
- Lease and Error Detail Limit preserve valid legacy values within new bounds.
- Legacy Reconciler Interval `0` migrates to new default `30`; positive values preserve within bounds.
- Remaining backoff sequence values are not persisted. New fixed-delay schedule becomes authoritative after migration.
- Migration record stores prior non-secret values and resulting revision for diagnostics/rollback evidence.

### Compatibility, Migration, and Risk

- old behavior: multiple page shells, hash prototype routes, Settings-owned Runs, Candidate Profile modal/reverse Runs, onboarding-owned provider/routing/prompt/retry overlay, prompt addenda, arbitrary retry sequence, and mixed local data/system pages
- new behavior: one shell, real URLs, dedicated details, canonical provider/model registry, server defaults plus replacement prompts, scalar Initial Backoff, System/Lifecycle split
- compatibility boundary:
  - domain API routes retained as listed
  - packaged-only UI/API additions unavailable in server/developer mode
  - old safe GET local pages redirect
  - unsafe routes retain exact method/path until separately migrated
- migration or backfill: one-time provider/prompt/retry cutover described above
- rollout and rollback:
  - take canonical backup before schema/config migration
  - migration transaction records version and prior non-secret values
  - rollback restores DB/config backup and legacy Credential Manager account only when canonical cutover has not accepted new writes
  - after canonical writes occur, rollback requires forward migration rather than silent dual-read
- deprecation or consumer impact:
  - Candidate Profile UI stops calling reverse Runs route; route remains supported
  - obsolete Settings drawer tests and hash assertions are deleted/replaced
  - local onboarding templates stop posting provider/routing/prompt/retry fields to private overlay
- risk: credential-store and DB mutation cannot be one native transaction
  - mitigation: staged credential write, DB commit, verification, and compensating credential rollback; never expose secret in transaction journal
- risk: stale model references can block LLM execution
  - mitigation: explicit `needs_retest`, affected-task summary, reference conflicts for destructive removal, and no silent model substitution
- risk: prompt replacement can invalidate required runtime variables
  - mitigation: server variable validation at save and startup; prior valid replacement remains active on rejected update
- risk: browser enhancement can become second router
  - mitigation: server route map remains complete and testable without JavaScript; client derives behavior from current URL only

## Invariants and Edge Cases

### Invariants

- One shared Jinja shell owns global navigation, theme, shutdown, and page framing.
- Every visible page has one canonical real URL and a direct server response.
- No production route uses URL hash as page/entity identity.
- Settings contains no Runs collection, Run Details drawer, Candidate Profile drawer, provider registry copy, retry copy, or lifecycle copy.
- Candidate Profile UI never requests reverse Runs; backend route remains available.
- One provider has zero or one connection.
- `Connected` means persisted verified connection, not credential presence or last UI test alone.
- API key values exist only in Windows Credential Manager.
- Provider model routing eligibility requires verified connection plus validated model against current connection revision.
- LLM task list contains exactly four canonical task IDs; CV Analysis is excluded.
- Default prompt text remains packaged/server-owned and is never persisted as default-mode user data.
- Mutable prompt storage contains only optional replacement text.
- Maximum Attempts includes initial attempt; Initial Backoff is scalar; retry schedule derivation has one owner.
- System and Lifecycle ownership is disjoint.
- Packaged-local-only routes do not expand remote attack surface or create auth/session state.
- Source/test/OpenAPI contracts use same resource names, enums, bounds, and error codes.

### Edge Cases

- empty or minimal input:
  - no Candidate Profiles disables Trigger Run
  - no providers/models produces clear empty state and blocks Default Route
  - no prompt replacement renders current server default
  - Maximum Attempts `1` performs no retry
- normal and large input:
  - Profile detail remains bounded when thousands of Runs reference profile
  - provider/model lists paginate or remain bounded without exposing connection counts in rows
  - long model IDs, provider names, errors, and prompt text wrap without page overflow
- duplicate, missing, malformed, or unsupported data:
  - duplicate custom name/model ID, malformed URL, unknown task/model/provider, bad archive, unsupported API type, and unknown template variable return field errors
  - missing stored credential turns connection unavailable without returning secret details
- retry, cancellation, timeout, partial failure, or concurrency:
  - failed connection update preserves old verified connection
  - failed model retest preserves row as `needs_retest`
  - stale tabs receive conflict and reload path
  - active work rejects backup/import/relocation/shutdown
  - duplicate submissions replay or conflict through idempotency
- migration or mixed-version state:
  - incomplete migration blocks writes and exposes recovery action; no dual writes
  - migrated prompt above 4000 remains runtime-safe but cannot be re-saved until corrected
  - imported models remain ineligible until canonical retest
- generated-source consistency:
  - OpenAPI models and any generated clients update from route schemas, not copied prototype objects
- security or accessibility boundary:
  - direct external navigation cannot use back-link return target as open redirect
  - secret fields never repopulate after navigation/error
  - dialogs trap focus only while open, Escape follows cancellation rules, destructive confirmation names effect, and focus returns to invoker
  - 200% zoom and narrow viewport reflow without page-level horizontal scrolling; data tables may scroll inside labeled containers

## Validation Plan

### Acceptance Criterion: Shared routing and shell

- setup or precondition: packaged application with representative data
- action: direct-load every canonical URL; navigate through links, filters, detail pages, Back, Forward, refresh, and JavaScript-disabled fallback
- expected result: one shell contract, correct active navigation/title/focus, restored query/entity state, no hash route, no duplicate history entries
- failure condition: 404 for valid deep link, wrong active navigation, lost filter, duplicate shell owner, or client-only page
- proof method: route tests plus production browser automation
- expected evidence: URL/title/heading assertions, history sequence, accessibility snapshot, no console/network errors

### Acceptance Criterion: Runs and Candidate Profiles

- setup or precondition: active/archived/failed profiles and Runs
- action: Trigger Run with canonical profile, open details, archive/restore, and inspect network calls
- expected result: `profile_id` submitted, dedicated pages used, Profile detail makes no reverse Runs request, retained reverse route still passes API tests
- failure condition: obsolete field, drawer, Settings duplicate, reverse Runs UI/network request, or lost back state
- proof method: API integration tests and browser network assertions
- expected evidence: request payloads, route responses, browser history/focus proof

### Acceptance Criterion: Provider registry and credential boundary

- setup or precondition: predefined provider, custom provider, Credential Manager test double/canary, connected and disconnected states
- action: create, test, add/update/remove connection, add/retest/remove model, migrate legacy onboarding state
- expected result: one registry, one connection, shared server-side validation on Test and commit, correct model eligibility, no secret outside credential service
- failure condition: parallel onboarding record, false Connected state, stale model selectable, second connection, canary in DB/YAML/log/response/backup/browser storage
- proof method: persistence, route, migration, and secret-scanning tests
- expected evidence: registry rows/revisions, credential calls, redacted artifacts, stable errors

### Acceptance Criterion: LLM runtime configuration

- setup or precondition: two connected providers, validated/stale models, four task configs
- action: change Default Route/task model/timeout/temperature; invalidate provider connection; execute task
- expected result: only eligible models save, runtime resolves exact referenced provider/model/settings revision, stale reference blocks or explicitly repairs to Default per contract
- failure condition: hardcoded temperature, copied model string, silent unrelated fallback, disconnected model execution
- proof method: API tests, runtime unit/integration tests, Run snapshot assertions
- expected evidence: resolved request parameters and immutable provenance

### Acceptance Criterion: Prompt semantics

- setup or precondition: four packaged prompt definitions and legacy addenda fixtures
- action: read default, create valid/invalid custom replacement, reset to default, upgrade default file, migrate addenda including over-limit case
- expected result: default is server-owned, only replacement persists, required runtime variables validate, 4000 limit applies to new saves, migration preserves effective behavior
- failure condition: copied default in DB, addendum still read, invalid variable accepted, empty/unchanged custom saved, truncated migration
- proof method: prompt registry/renderer, persistence, migration, API, and browser editor tests
- expected evidence: stored row content, rendered prompt hash, validation errors, dirty-discard/focus behavior

### Acceptance Criterion: Retry and recovery semantics

- setup or precondition: defaults, valid bounds, legacy retry fixtures, transient failures
- action: save settings, trigger repeated failures, run reconciler, migrate old list
- expected result: scalar value persists, same fixed delay is used before every retry, all consumers share one revision, migration mapping is exact
- failure condition: arbitrary list remains, queue and UI differ, out-of-range save, disabled flag conflicts with attempts
- proof method: settings, queue, reconciler, worker, migration, and API tests
- expected evidence: calculated delays, loaded settings, revision conflicts, artifact error truncation

### Acceptance Criterion: System and Lifecycle

- setup or precondition: idle and active work, valid/invalid backup, relocation destinations, diagnostics canary
- action: backup/import, relocate, download diagnostics, cancel/confirm shutdown
- expected result: page ownership is disjoint; active work rejects mutation; secrets/content excluded; successful cold actions require restart; shutdown remains global
- failure condition: duplicated control, unsafe active-work mutation, leaked content, broken rollback, Lifecycle shutdown section
- proof method: local route tests and browser flows
- expected evidence: status codes, restart payloads, archive contents, filesystem/bootstrap checks, focus/confirmation proof

### Acceptance Criterion: Frontend quality contract

- setup or precondition: light/dark themes, desktop/narrow containers, 200% zoom, long/missing/localized content, keyboard-only input
- action: traverse all changed pages and material states
- expected result: WCAG 2.2 AA semantics, visible focus, correct labels, no page overflow, shared hover/border/section behavior, reduced-motion support, stable layout
- failure condition: inaccessible control, focus loss, icon shrink, inconsistent row hover/border, clipped content, theme contrast failure
- proof method: production browser automation, accessibility assertions, screenshots, and targeted DevTools diagnostics
- expected evidence: light/dark/narrow/zoom captures, keyboard sequence, console/network clean state

### Test Matrix

| Layer | Required coverage |
|---|---|
| Schema/persistence | provider uniqueness, one connection, model uniqueness/state, credential-handle-only storage, LLM/prompt/system revisions, migration idempotency, rollback |
| API/OpenAPI | page/API route availability by mode, typed requests/responses, enums/bounds, stable errors, revisions, ETags, idempotency, CSRF/Host/Origin |
| Runtime | provider resolution, credential lookup, API type dispatch, timeout, temperature, prompt replacement/default rendering, retry schedule, recovery settings |
| Jinja/frontend unit | shared shell, canonical hrefs, no hash routes, no duplicate Runs/Profile drawer markup, semantic controls, field-error mapping |
| Browser integration | direct URLs, history, query restoration, back links, async states, provider test/save sequence, model test/add sequence, prompt dirty state, shutdown/backup/lifecycle flows |
| Regression | existing Runs/Profile/Bookmark/Synonym domain contracts and retained reverse Profile Runs route |
| Secret safety | canary absent from SQLite, YAML, logs, HTML, JSON, OpenAPI examples, browser storage, diagnostics, and backup |

- Remove obsolete assertions that require Run Details or Candidate Profile drawers.
- Replace Settings string assertions with route/component/API behavior assertions.
- Keep prototype self-checks only as design-intent regression; they do not count as production integration proof.
- Because real History API behavior cannot be proven by TestClient/string checks, add the smallest production browser test surface needed for these flows. Do not build a second general test framework.

## Completion Criteria

Specification implementation is complete only when:

1. every canonical page URL directly renders through one shared shell and passes Back/Forward/refresh proof
2. Settings duplicate Runs/Run Details code and Candidate Profile drawer are deleted
3. Candidate Profile UI omits reverse Runs while retained backend route remains tested
4. one provider registry serves onboarding, API Providers, readiness, diagnostics, LLM Configuration, and runtime
5. API key values exist only in Windows Credential Manager and secret canary tests pass
6. provider verification, one-connection invariant, model validation/retest, and routing eligibility are enforced server-side
7. LLM Default Route and four task configurations persist and drive runtime timeout/temperature/model resolution
8. server prompt defaults remain canonical and only optional replacement text persists
9. scalar Initial Backoff and shared retry/recovery resource drive every runtime consumer
10. System and Lifecycle pages have disjoint approved ownership and lifecycle safety passes
11. packaged-local-only mounting and existing Host/Origin/CSRF rules cover every new unsafe route
12. migration is idempotent, restart-safe, non-secret, and leaves no dual-read/dual-write provider, prompt, or retry owner
13. OpenAPI, source types, frontend assumptions, and maintained tests agree on fields, enums, bounds, revisions, and errors
14. production browser coverage replaces obsolete drawer/string assertions and proves accessibility/responsive/theme states
15. `docs/fitcv-settings-ui-prototype.integration.md` is removed after all acceptance evidence passes
16. no unresolved ownership or behavioral decision is deferred to implementation
