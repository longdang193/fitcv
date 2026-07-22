---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-central-workspace-frontend-backend-integration
parent_spec: docs/superpowers/specs/2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md
targets:
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/synonym_policy_io.py
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/templates
  - tests/test_fitcv_cp
  - docs/fitcv-settings-ui-prototype.html
  - docs/fitcv-settings-ui-prototype.integration.md
---

# FitCV Central Workspace Frontend-Backend Integration Implementation Plan

## Goal

Implement approved local-workspace Candidate Profiles, Bookmarks, and Synonyms contracts as one normalized SQLite-backed control plane. Connect existing server-rendered frontend to typed FastAPI routes, preserve immutable Run inputs, replace legacy bookmark and Run-scoped synonym ownership, and keep approved prototype and temporary integration sidecar aligned until production evidence passes.

Use backed-up fresh database cutover. Do not migrate, backfill, dual-read, or dual-write legacy Candidate Profile, bookmark, synonym review, or retired settings rows. Preserve unrelated working-tree changes.

## Implementation Outcomes

### One fresh normalized persistence owner

SQLite schema initialization creates Candidate Profile attempt/revision, normalized bookmark, synonym policy draft/revision/bundle, aggregated suggestion/source, processing-history, and idempotency records with required checks, foreign keys, revisions, and deletion behavior. Unsupported old schema remains backup-only and cannot enter new runtime query path.

### Reproducible Run inputs

Trigger Run selects only Active + Succeeded Candidate Profiles and atomically captures immutable profile, Pipeline Settings, and active validated synonym bundle IDs, checksums, and snapshots before enqueue. Archived, failed, stale, or missing profiles cannot start a Run.

### One bookmark contract across pages

Run Details and Bookmarks read and write normalized `bookmarks` table through one shared job projection and selection-intersection algorithm. Submitted status and legacy `bookmarked_jobs` ownership disappear. Permanent Run deletion previews and transactionally cascades bookmark loss with exact counts.

### Central synonym policy and review lifecycle

Three canonical YAML policy files resolve to one immutable active bundle. Invalid editor drafts persist without replacing active policy. Suggestion review aggregates one normalized alias/canonical concept across Runs, exposes Pending/Approved/Declined only, preserves Approved+Blocked decisions, removes zero-source Pending/Declined rows on Run deletion, and never copies review decisions through proposal-analysis reuse.

### Safe opaque exports and backups

Bookmark and Run Details CSV exports use explicit selection intersected with current stage, result, and search, confirmed by opaque expiring preview revision. Synonym backup exports and imports one ZIP containing three canonical YAML files plus `manifest.json`, with traversal, size, shape, checksum, conflict, cycle, partial-activation protection, and SQLite-owned mirror repair.

### Approved production UI with shared behavior

Production templates expose navigation in Runs, Candidate Profiles, Bookmarks, Synonyms order and reuse shared request, tabs, filters, action toolbar, table shell, notifications, dialog, drawer, and console behavior. URL-restorable filters, internal table scrolling, keyboard focus, duplicate-submit protection, loading/empty/error/stale states, responsive layouts, light/dark themes, reduced motion, and WCAG 2.2 AA intent match approved prototype.

### Typed and verified integration contract

FastAPI routes use explicit Pydantic request/response models, stable envelopes and error codes, loopback/same-origin/CSRF enforcement, revisions, idempotency, media declarations, and OpenAPI assertions. Focused persistence/API/frontend tests, full-suite checks, fresh-reset proof, and browser evidence cover parent specification before integration sidecar is removed.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-code-standards`, `skill-full-stack-integration`, `skill-central-config-layer`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: current workspace; inspect and preserve existing uncommitted changes before every shared-file edit
- Parallel ownership: none; `src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/store.py`, `src/fitcv_cp/app.py`, templates, and integration tests are shared across all vertical slices
- Sequential fallback: execute Tasks 1 through 8 in order in one workspace
- Shared-write rule: do not reset, checkout, regenerate, or overwrite `AGENTS.md`, `docs/operating_system/rules/frontend-ui-rule.md`, `docs/operating_system/templates/agents/root-AGENTS.template.md`, or `scripts/sync_agent_adapters.py`; preserve their unrelated current diffs
- Database rule: increment `CONTROL_PLANE_SCHEMA_VERSION`; reject old schema; use existing `reset_database` operator path to archive DB/WAL/SHM and initialize new empty runtime
- Synonym policy rule: SQLite active bundle pointer and normalized bundle snapshot are runtime SSOT; canonical YAML files are repaired mirrors used for operator compatibility, initialization, import, and export only
- Synonym setting rule: Approve always validates and installs the mapping; `apply_approved_enabled` gates active bundle use by future Runs; `auto_accept_suggestions_enabled=true` invokes the same Approve transaction with automation actor, while `false` creates Pending rows
- Idempotency rule: JSON actions store JSON responses; CSV actions store exact bounded response bytes, media type, filename, and checksum in existing `idempotent_actions` so replay returns original output
- Limit rule: profile YAML is limited to 1 MiB; synonym ZIP to 8 MiB compressed, 2 MiB per member, and 6 MiB total extracted; selection/export requests to 5,000 IDs; synonym batch actions to 1,000 IDs; previews expire after 300 seconds; processing history retains newest 1,000 records; page size reuses existing `10|20|50` with default `20`
- Contract rule: `docs/superpowers/specs/2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md` owns behavior; source, tests, and runtime OpenAPI become transport truth after implementation
- Pre-execution documentation gate: normalize parent specification to required detailed-specification headings before changing plan status from `proposed` to `active`; do not defer this repair into implementation tasks
- Sidecar rule: keep `docs/fitcv-settings-ui-prototype.integration.md` only while required integration evidence is incomplete; remove it in Task 8 only after every referenced flow passes
- Baseline rule: capture current full-suite and repository-validator failures before execution; final proof may retain only exact unchanged unrelated failures, while touched plans/specs/code/tests must add no new failure

## Task Breakdown

### Task 1: Stabilize baseline and define fresh schema ownership

**Purpose:**
- restore reliable regression evidence and establish fresh schema before adding route or UI consumers

**Specification Coverage:**
- Approved Product Decision 8: backed-up fresh database with no migration, backfill, or dual-read
- Cross-Cutting Integration Contract: revisions and idempotency
- Fresh Cutover and Compatibility steps 1 through 6
- Existing Test Baseline requirement

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect/modify: `tests/test_fitcv_cp/test_app.py:test_post_runs_multipart_enqueue_failure_returns_persisted_failed_run`
- Modify: `src/fitcv_cp/sqlite_store.py:CONTROL_PLANE_SCHEMA_VERSION`
- Modify: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`
- Modify: `src/fitcv_cp/sqlite_store.py:_persist_initial_profile_state`
- Modify: `src/fitcv_cp/sqlite_store.py` `idempotent_actions` schema
- Modify: `src/fitcv_cp/sqlite_store.py:initialize_control_plane_database`
- Modify: `src/fitcv_cp/sqlite_store.py:ensure_control_plane_database`
- Verify: `src/fitcv_cp/local_storage.py:reset_local_database`
- Verify: `src/fitcv_cp/local_app.py:_process_pending_operation`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_local_app.py:test_process_pending_database_reset_archives_old_database_and_seeds_new_one`

**Dependencies:**
- approved parent specification exists and contains no open product decision
- existing database reset path already archives SQLite DB/WAL/SHM files

**Steps:**
- [x] Add missing injected `complete_idempotent_action_fn` test double to enqueue-failure regression; prove failure is fixture isolation, not runtime schema defect.
- [x] Run single regression before schema work and record passing baseline.
- [x] Increase `CONTROL_PLANE_SCHEMA_VERSION` and keep existing refusal for non-empty version-0 or mismatched database.
- [x] Replace current direct-content `candidate_profiles` definition with attempt/lifecycle metadata and add immutable `candidate_profile_revisions` with `ON DELETE RESTRICT`.
- [x] Change `bookmarks` to non-null `run_id` and `run_job_id`, unique `run_job_id`, and `ON DELETE CASCADE`; remove display snapshot and nullable/orphan columns.
- [x] Extend `run_inputs` with `candidate_profile_revision_id`, `synonym_policy_bundle_revision_id`, synonym bundle checksum, and immutable normalized synonym bundle snapshot.
- [x] Add smallest normalized synonym tables: `synonym_policy_type_revisions`, singleton `synonym_policy_state`, `synonym_policy_drafts`, `synonym_policy_bundle_revisions`, `synonym_suggestions`, `synonym_suggestion_sources`, and `synonym_processing_runs`; `synonym_policy_state` also owns mirror status and safe mirror error code.
- [x] Extend `idempotent_actions` with nullable `response_blob`, `response_media_type`, `response_filename`, and `response_checksum`; retain `response_json` for non-binary actions and require exactly one response representation for succeeded actions.
- [x] Add checks for profile states, synonym types, review statuses, policy effects, positive revisions, JSON validity, unique concept identity, and source foreign keys.
- [x] Seed configured profiles as Active + Succeeded attempts with one immutable revision each; allow duplicate names and use Profile ID as identity.
- [x] Extend fresh-schema tests for tables, constraints, indexes, foreign keys, initial profile revisions, binary/JSON idempotent response checks, empty collections, and incompatible-schema refusal; Task 3 owns initial synonym bundle/default-settings seeding.
- [x] Extend reset tests for timestamped DB/WAL/SHM preservation and successful initialization at new schema version.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py::test_post_runs_multipart_enqueue_failure_returns_persisted_failed_run -q`
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_sqlite_store.py -q -k "control_plane_schema or initialize_control_plane_database"`
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_local_storage.py::test_reset_local_database_archives_then_retires_matched_sqlite_set tests/test_fitcv_cp/test_local_app.py::test_process_pending_database_reset_archives_old_database_and_seeds_new_one -q`
- Expected: fixture no longer touches real uninitialized idempotency storage; new schema initializes transactionally; old schema refuses startup; reset preserves DB/WAL/SHM and creates empty normalized runtime state.

**Exit Criteria:**
- fresh schema and reset boundary support later tasks without compatibility tables, migration, dual-read, or second persistence owner

### Task 2: Implement Candidate Profile resources

**Purpose:**
- make profile imports durable resources with visible failed attempts, immutable successful revisions, and lifecycle transitions

**Specification Coverage:**
- Candidate Profile Integration: Resource Model, Persistence, Routes, Import Boundary, UI States and Actions
- Approved Product Decision 2: failed admitted imports remain visible

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/candidate.py:load_candidate_profile`
- Inspect: `src/fitcv_cp/candidate_profile_seeds.py:build_candidate_profile_seeds`
- Modify: `src/fitcv_cp/store.py:RunStore`
- Modify: `src/fitcv_cp/store.py:ControlPlaneStore`
- Modify: `src/fitcv_cp/sqlite_store.py:list_candidate_profiles`
- Modify: `src/fitcv_cp/sqlite_store.py:get_candidate_profile`
- Add in `src/fitcv_cp/sqlite_store.py`: `create_candidate_profile_attempt`, `get_candidate_profile_detail`, `query_candidate_profile_runs`, `transition_candidate_profile_lifecycle`
- Modify: `src/fitcv_cp/app.py:create_app`
- Modify: `src/fitcv_cp/app.py` Pydantic models near `DeleteArchivedRunsRequest`
- Modify: `src/fitcv_cp/app.py` route handler at `GET /candidate-profiles`
- Verify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 schema and baseline complete

**Steps:**
- [x] Add store protocol/adapter methods for paged profile queries, admitted import persistence, detail lookup, related Run lookup, and archive/restore; reuse `ControlPlaneStore._call` instead of adding service layer.
- [x] Add immutable profile revision creation using existing candidate parser/validator and canonical JSON/checksum conventions.
- [x] Enforce pre-admission rejection for missing file, non-`.yaml` extension, zero bytes, and input larger than 1 MiB without creating row.
- [x] After admission, persist YAML parse, schema, canonicalization, and candidate-validation failures as `creation_status=failed` with safe failure code/message and no revision row.
- [x] Trim optional Profile Name, convert blank to null, reject over 120 Unicode characters, sanitize original filename to basename, and never expose raw YAML or absolute paths.
- [x] Add explicit Pydantic resource, page, failure, capability, overview, input, related Run, archive/restore request, and envelope models.
- [x] Implement `GET /candidate-profiles`, multipart `POST /candidate-profiles`, `GET /candidate-profiles/{profile_id}`, `GET /candidate-profiles/{profile_id}/runs`, and archive/restore routes with stable errors.
- [x] Apply loopback Host, same-origin, CSRF, expected revision, and `Idempotency-Key` checks to unsafe profile operations.
- [x] Add persistence/route tests for valid import, duplicate/blank names, wrong extension, empty/oversize file, admitted malformed/invalid YAML, unexpected failures, detail variants, archive/restore conflicts, related Runs, stale revision, idempotent replay/conflict, and selector eligibility.
- [x] Add OpenAPI assertions for multipart fields, `.yaml` description, typed responses, action bodies, and error envelopes.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q -k "candidate_profile"`
- Expected: admitted invalid YAML remains Failed; successful revisions are immutable; archive/restore and selector eligibility follow current state/revision.

**Exit Criteria:**
- Candidate Profiles have one typed persistence/API contract ready for Trigger Run consumption

### Task 3: Implement synonym policy, settings, and Run snapshot integration

**Purpose:**
- establish active validated synonym bundle/settings truth and make Trigger Run atomically capture eligible profile, settings, and synonym revisions

**Specification Coverage:**
- Synonym Integration: Types and Canonical Files, Immutable Bundle Revision, Policy Resource and Validation, Pipeline Settings Contract, Run Reproducibility
- Candidate Profile Integration: Trigger Run Dependency
- Approved Product Decisions 6, 7, and 9

**Required Skills:**
- `skill-test-driven-development`
- `skill-central-config-layer`
- `skill-full-stack-integration`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/synonym_policy_io.py:_field_spec`
- Modify: `src/fitcv_cp/synonym_policy_io.py:load_global_synonym_map`
- Modify: `src/fitcv_cp/synonym_policy_io.py:persist_global_synonym_map`
- Add in `src/fitcv_cp/synonym_policy_io.py`: `parse_synonym_editor_text`, `validate_synonym_mapping`, `render_synonym_policy_mirrors`, `repair_synonym_policy_mirrors`
- Modify: `src/fitcv_cp/settings_schema.py:SETTINGS_SCHEMA`
- Modify: `src/fitcv_cp/settings_store.py` settings revision/load/update functions
- Modify: `src/fitcv_cp/store.py:RunStore`
- Modify: `src/fitcv_cp/store.py:ControlPlaneStore`
- Add in `src/fitcv_cp/sqlite_store.py`: `get_synonym_policy`, `save_synonym_policy_draft`, `activate_synonym_policy_bundle`, `resolve_active_synonym_bundle`
- Modify: `src/fitcv_cp/sqlite_store.py:initialize_control_plane_database`
- Modify: `src/fitcv_cp/sqlite_store.py:ensure_control_plane_database`
- Modify: `src/fitcv_cp/sqlite_store.py:create_run_bundle`
- Modify: `src/fitcv_cp/app.py:create_app`
- Add in `src/fitcv_cp/app.py`: `get_synonym_policy`, `put_synonym_policy`
- Modify: `src/fitcv_cp/app.py` route handler at `POST /runs`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_store.py`
- Verify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`
- Verify: `tests/test_fitcv_cp/test_synonym_global_policy_io.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 synonym revision tables complete
- Task 2 Candidate Profile resource and eligibility contract complete

**Steps:**
- [x] Replace public settings keys `apply_to_run_enabled`, `promote_global_enabled`, `auto_apply_recommendation_enabled`, and `auto_promote_global_enabled` with `synonym_management.apply_approved_enabled=true` and `synonym_management.auto_accept_suggestions_enabled=false`.
- [x] Keep `synonym_management.auto_accept_ai_action_enabled` unchanged and document/test its separate CV-review meaning.
- [x] Remove retired keys from settings UI metadata, validation, public schema, and fresh defaults; do not add compatibility reads from backed-up rows.
- [x] Extend fresh initialization to validate three canonical synonym files, create first active bundle revision, and initialize approved settings defaults before Runs are accepted.
- [x] Implement one line-oriented editor parser supporting comments and blank lines and reporting stable issues for empty aliases, missing canonicals, `-` list syntax, duplicate/normalized conflicts, and canonical cycles.
- [x] Preserve non-editor-owned YAML sections when replacing only `skill_synonyms`, `domain_alias_map`, or `role_family_alias_map`; keep `domain_neighbors` untouched.
- [x] Persist invalid editor text and validation issues as current inactive draft; keep previous active type revision and bundle pointer unchanged.
- [x] Make every runtime policy reader resolve `synonym_policy_state.active_bundle_revision_id` and immutable SQLite bundle snapshot; restrict direct YAML reads to fresh initialization, import validation, export generation, and mirror repair.
- [x] For valid saves, calculate normalized snapshots and SHA-256 values, create immutable type/bundle revisions, switch active SQLite pointer in one transaction, and mark mirror status Pending; this DB commit is policy activation.
- [x] After activation, stage/fsync and `os.replace` each canonical YAML mirror, then mark mirror status Synced; mirror failure records safe Failed status without rolling back active DB policy or exposing paths.
- [x] On startup and before backup export, reconcile any Pending/Failed or checksum-mismatched YAML mirror from active SQLite snapshot; fault-injection tests cover failure after DB commit and after each file replacement.
- [x] Use compare-and-swap on draft revision and active bundle revision; return `409 revision_conflict` with current metadata for stale writes.
- [x] Implement typed `GET /synonym-policies/{type}` and `PUT /synonym-policies/{type}` routes with stable issue/resource envelopes, `422 synonym_policy_invalid` for persisted invalid drafts, and idempotent replay/conflict behavior.
- [x] Reconcile matching Approved+Blocked suggestion rows to Approved+Active when corrected valid draft activates; do not require another approval.
- [x] Ensure pipeline policy resolution uses only active validated SQLite bundle data; `apply_approved_enabled=false` stores the active bundle identity for traceability but supplies an empty approved-mapping projection to future Run snapshots, while invalid drafts and blocked mappings are always excluded.
- [x] Update `POST /runs` to accept `profile_id`, re-read profile and active revisions inside create transaction, reject anything except Active + Succeeded with `409 candidate_profile_unavailable`, and never accept free-text profile payload.
- [x] Update `create_run_bundle` to store profile revision/content, Settings revision/content, and active synonym bundle revision/checksum/content before enqueue.
- [x] Return persisted failed Run and complete idempotent action when queue submission fails; preserve retryable `run_enqueue_failed` contract.
- [x] Add tests for syntax/semantic issues, issue line data, last-valid-bundle behavior, SQLite runtime resolution, preserved non-editor sections, revision conflicts, idempotency, mirror failure/startup repair, corrected blocked activation, settings defaults/retired-key absence, Apply-off empty projection, stale Trigger selection, immutable Run bundle capture, and no enqueue on invalid profile.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q -k "synonym_policy or synonym_management or run_bundle or post_runs_multipart"`
- Expected: one validated bundle owns all three types; invalid drafts persist but remain inactive; retired settings cannot diverge; Runs capture immutable active bundle data.

**Exit Criteria:**
- active synonym policy, settings, Candidate Profile selection, and all three Run snapshots have one atomic SQLite owner; YAML mirror drift cannot alter runtime behavior

### Task 4: Implement aggregated synonym review, history, and ZIP backup

**Purpose:**
- replace Run-scoped review decisions with one concept-level queue and complete safe policy import/export workflows

**Specification Coverage:**
- Synonym Integration: Review Identity and Aggregation, Review Actions, Routes, Processing Summary Log, Backup Contract
- Approved Product Decisions 5, 7, 9, and 10

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/synonym_proposals.py:build_synonym_proposal_identity`
- Modify: `src/fitcv_cp/synonym_proposals.py:build_synonym_triage_input`
- Modify: `src/fitcv_cp/app.py:_aggregate_mapping_suggestion_payloads`
- Modify: `src/fitcv_cp/app.py:_aggregate_synonym_proposal_payloads`
- Retire from public workflow: Run-scoped approve/defer/promote handlers near `src/fitcv_cp/app.py:admin_run_synonym_proposal_action`
- Add in `src/fitcv_cp/sqlite_store.py`: `ingest_synonym_suggestions`, `query_synonym_suggestions`, `get_synonym_suggestion`, `apply_synonym_suggestion_action`, `query_synonym_processing_runs`, `delete_run_synonym_sources`
- Add in `src/fitcv_cp/synonym_policy_io.py`: `export_synonym_backup_zip`, `inspect_synonym_backup_zip`, `import_synonym_backup_zip`
- Modify: `src/fitcv_cp/store.py:RunStore`
- Modify: `src/fitcv_cp/store.py:ControlPlaneStore`
- Add in `src/fitcv_cp/app.py`: central suggestion, processing-history, and backup route handlers
- Verify: `tests/test_fitcv_cp/test_synonym_global_policy_io.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 3 policy draft/activation and settings contract complete

**Steps:**
- [x] Change proposal identity to `(synonym_type, normalized_alias, normalized_canonical)` and remove Run ID from concept identity while preserving Run/source proposal references in source rows.
- [x] Normalize incoming legacy `deferred` to Pending at ingestion; reject Deferred in new storage, Pydantic enums, settings, templates, and responses.
- [x] Bound each suggestion action request to 1,000 unique IDs and reject larger requests with `422 selection_too_large` before mutation.
- [x] Ingest repeated proposal analysis as additional source evidence for same concept; never copy Approved or Declined decisions from another Run.
- [x] When `auto_accept_suggestions_enabled=false`, create or update Pending concepts; when `true`, call the same Approve transaction with actor `automation`, producing Approved+Active or Approved+Blocked with identical validation, processing counts, and idempotency rules.
- [x] Suppress exact Active mappings and attach repeated Blocked mappings to existing Approved concept instead of creating Pending duplicates.
- [x] Implement paged suggestion list/detail with type/status/search filters, source counts, Suggestion Overview Run metadata, paged evidence-only signals, and resolvable Run links.
- [x] Implement Pending action matrix Approve/Decline/Clear, Approved Clear only, and Declined Approve/Clear; reject mixed types and invalid transitions with stable `422` codes.
- [x] Implement Approve as one transaction: record decision, merge mappings into affected draft, validate, activate one bundle when valid, or persist Approved+Blocked draft/issues while retaining previous active bundle when invalid.
- [x] Count `successfully_added` only for mappings newly Active; record one processing summary row from completed operation rather than browser recomputation.
- [x] Implement Clear as queue/source deletion only; retain active or blocked policy mappings and suppress only those retained mappings from re-entering as duplicates.
- [x] Hook permanent Run deletion to cascade source associations, delete zero-source Pending/Declined concepts in same transaction, and preserve zero-source Approved decisions.
- [x] Retain newest 1,000 `synonym_processing_runs` rows by deleting older rows in the same transaction that inserts a completed processing record; Clear remains browser-local.
- [x] Export deterministic ZIP members from active SQLite snapshot: `skill_synonyms.yaml`, `domain_synonyms.yaml`, `role_family_synonyms.yaml`, and `manifest.json`; include schema version, active bundle/type revisions, checksums, and RFC 3339 export time.
- [x] Import ZIP with stdlib `zipfile`, `hashlib`, `json`, and `tempfile`; reject archives over 8 MiB, members over 2 MiB, extracted totals over 6 MiB, and absolute/traversal/symlink/duplicate/unexpected/missing/invalid UTF-8/invalid YAML/invalid-root/conflict/cycle cases before activation.
- [x] Verify manifest checksums, validate all policies, then use Task 3 SQLite activation and mirror-repair path; never partially update active revisions.
- [x] Add explicit Pydantic models and routes for suggestions, detail, batch actions, processing runs, `GET /synonym-backups/export.zip`, and multipart `POST /synonym-backups/import`.
- [x] Remove or delegate legacy Run-scoped approve/promote/defer routes so they cannot remain second decision owner or expose divergent statuses.
- [x] Add tests for aggregation, source association, no decision reuse, auto-accept through shared Approve path, action matrix, batch limit, Approved+Blocked, reconciliation, Deferred normalization, clear semantics, Run-deletion cleanup, bounded processing retention, deterministic/malicious ZIPs, SQLite activation/mirror repair, media headers, and idempotent retries.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py -q -k "synonym_suggestion or synonym_backup or processing_run or deferred"`
- Expected: one concept row aggregates sources; only Pending/Approved/Declined persist; invalid accepted mappings remain Approved+Blocked; ZIP replacement is all-or-nothing.

**Exit Criteria:**
- central synonym editing, review, history, source cleanup, and backup operations are complete without Run-scoped decision or file-transport ownership

### Task 5: Unify bookmarks, selection previews, exports, and Run deletion

**Purpose:**
- make Run Details and Bookmarks share one normalized fact, projection, selection algorithm, and destructive confirmation contract

**Specification Coverage:**
- Bookmark Integration: Identity and Persistence, Shared Job Projection, Routes, Run Deletion, UI Behavior
- Approved Product Decisions 3 and 4
- Data Safety: server-recomputed intersection and exact deletion counts

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/sqlite_store.py:set_bookmark`
- Modify: `src/fitcv_cp/sqlite_store.py:clear_bookmark`
- Modify: `src/fitcv_cp/sqlite_store.py:list_bookmarks`
- Modify: `src/fitcv_cp/sqlite_store.py:query_run_jobs`
- Modify: `src/fitcv_cp/sqlite_store.py:iter_run_jobs_for_export`
- Modify: `src/fitcv_cp/sqlite_store.py:delete_archived_runs`
- Modify: `src/fitcv_cp/sqlite_store.py:reserve_idempotent_action`
- Modify: `src/fitcv_cp/sqlite_store.py:complete_idempotent_action`
- Add in `src/fitcv_cp/sqlite_store.py`: `query_bookmarks`, `resolve_job_selection`, `remove_bookmarks`
- Modify: `src/fitcv_cp/settings_store.py:_ensure_local_bookmarked_jobs_table`
- Modify: `src/fitcv_cp/settings_store.py` legacy bookmark load/save/delete functions
- Modify: `src/fitcv_cp/store.py:RunStore`
- Modify: `src/fitcv_cp/store.py:ControlPlaneStore`
- Add in `src/fitcv_cp/app.py`: `SelectionContext`, preview models, removal models, delete preview models
- Modify: `src/fitcv_cp/app.py` routes at `/runs/{run_id}/jobs`, `/runs/{run_id}/jobs/export.csv`, `/runs/actions/delete-archived`, and `/admin/bookmarks`
- Retire: `src/fitcv_cp/app.py:admin_bookmarks_status`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 normalized bookmark FKs complete
- Task 4 Run-deletion source cleanup contract available for one deletion transaction

**Steps:**
- [x] Delete runtime creation/use of legacy `bookmarked_jobs`; keep it only in backed-up old databases and remove Submitted/Archived bookmark status from schema, API, templates, filters, and tests.
- [x] Extract one shared Run job projection builder used by Run Details, Bookmarks, and CSV export; Bookmarks may only prepend bookmark and Run fields.
- [x] Implement paged `query_bookmarks` with stage/result/search/sort filters and totals over full filtered set; reuse `_validated_page` values `10|20|50` with default `20`.
- [x] Implement one `resolve_job_selection` query returning selected, matched, excluded, and ordered matched IDs for explicit IDs intersected with stage, result, and search; use it for removal and both export scopes.
- [x] Reject selection contexts over 5,000 unique Run Job IDs with `422 selection_too_large` before preview or mutation.
- [x] Add opaque preview helper in `app.py` that signs normalized context, matched identity checksum, scope, and a 300-second expiry with process-local secret; recompute on action and return `409 export_selection_changed` or `409 delete_preview_stale` when changed or expired.
- [x] Implement `GET /bookmarks`, `POST /bookmarks/actions/remove`, `POST /bookmarks/actions/export/preview`, and `POST /bookmarks/actions/export` with typed envelopes, exclusions, exact matched counts, and idempotency.
- [x] Render final CSV once, complete `idempotent_actions` with exact response BLOB/media type/filename/checksum, and return stored bytes on same-key replay; changed payload keeps `409 idempotency_conflict`.
- [x] Replace Run Details export with `POST /runs/{run_id}/jobs/actions/export/preview` and `POST /runs/{run_id}/jobs/actions/export`; keep one export column registry and prepend Run ID/Run Name only for Bookmarks.
- [x] Reject empty selection with `422 selection_required`; report IDs outside current server query as excluded and never act on them silently.
- [x] Add `POST /runs/actions/delete-archived/preview` for explicit Run IDs, blocked active IDs, missing IDs, bookmark count, expiry, and revision.
- [x] Update final delete to require unchanged IDs and preview revision, reject whole batch on active/missing/stale state, delete Run/run-job/bookmark/synonym-source records in one transaction, and report exact counts.
- [x] Keep filesystem cleanup after committed database deletion and report failure separately without falsifying database counts.
- [x] Delegate legacy admin bookmark route to canonical normalized query/action or remove it after template migration; no route may write `bookmarked_jobs` or mutate bookmark status.
- [x] Add tests for same job across Runs, shared columns, allowed page sizes, selection limit, removal intersection, 300-second preview expiry, stale conflict, exact binary idempotent replay after source changes, CSV hardening/headers, Run Details parity, exact deletion counts, all-or-nothing stale deletion, cascade, source cleanup, and no orphan links.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py -q -k "bookmark or export or delete_archived"`
- Expected: normalized bookmarks are sole owner; selection actions affect only server-recomputed intersections; Run deletion removes bookmarks and source associations transactionally with exact counts.

**Exit Criteria:**
- Run Details, Bookmarks, CSV export, and Run deletion share one projection and one selection/deletion truth with no bookmark status or legacy table ownership

### Task 6: Build shared production UI and navigation

**Purpose:**
- connect approved Candidate Profiles, Bookmarks, and Synonyms pages to canonical routes without adding frontend framework or page-specific interaction systems

**Specification Coverage:**
- Frontend Component and Interaction Rules
- Candidate Profile, Bookmark, and Synonym UI states and actions
- URL and UI State contract
- UI and Contract Quality acceptance criteria

**Required Skills:**
- `skill-full-stack-integration`
- `ui-ux-pro-max`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv_cp/templates/base.html`
- Modify: `src/fitcv_cp/templates/runs_list.html`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Replace: `src/fitcv_cp/templates/bookmarks.html`
- Modify: `src/fitcv_cp/templates/settings.html`
- Add: `src/fitcv_cp/templates/candidate_profiles.html`
- Add: `src/fitcv_cp/templates/synonyms.html`
- Modify: `src/fitcv_cp/app.py` HTML page handlers for Runs, Candidate Profiles, Bookmarks, Synonyms, and Settings
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `docs/fitcv-settings-ui-prototype.html` visual/interaction authority

**Dependencies:**
- Tasks 2 through 5 typed routes and transitions complete

**Steps:**
- [x] Add one shared `fitcvApiRequest` helper in `base.html` for envelope parsing, CSRF, timeout/cancellation, stable errors, expected revisions, and duplicate-submit locking; add no JS dependency or generated client.
- [x] Centralize only repeated UI primitives in base styles/scripts: tabs, filter bar, selection toolbar, scroll-contained table shell, badges, notifications, dialog/drawer focus, local console clearing, and disabled/loading states.
- [x] Order sidebar/navigation links Runs, Candidate Profiles, Bookmarks, Synonyms; retain other approved destinations after these four.
- [x] Add Candidate Profiles page with Active/Archived tabs, search/page URL state, Create Profile multipart dialog, `.yaml` hint, failed-row detail, overview/input/related-Run drawer, archive/restore, exact notifications, stale retry, and focus restoration.
- [x] Update Trigger Run dialog to refresh `GET /candidate-profiles?view=active&status=succeeded` on open, label `{display_name} - {profile_id}`, link empty state to Candidate Profiles, preserve jobs/Run Name on errors, and submit Profile ID only.
- [x] Replace Bookmarks page with stage tabs, result/search/page URL state, selection pruning, shared job columns, Run ID/Name, Remove/Export, preview summary, stale retry, exact success summary, pagination, and internal horizontal scrollbar.
- [x] Update Run Details export controls to use same selection toolbar, preview confirmation, excluded count, and export behavior as Bookmarks.
- [x] Add Synonyms page with type tabs, read-only/resizable editor, Edit/Save, search navigation, issue navigation, unsaved protection, active/draft/blocked state, Pending/Approved/Declined tabs, status actions, Suggestion Overview drawer, evidence-only list, processing log, local Clear, ZIP import/export, and Settings link.
- [x] Keep conflict information in editor feedback and suggestion detail only; do not add review-table Conflict column.
- [x] Remove Run Details Synonym Workspace decision/promote controls after central routes are live; retain captured bundle identity and central Synonyms link where appropriate.
- [x] Update Pipeline Automation & Reuse to expose only Apply Approved Synonyms and Auto-accept Suggestions, retain unrelated `auto_accept_ai_action_enabled`, and link to Synonyms instead of duplicating editor controls.
- [x] Synchronize tabs/search/result/page to approved query parameters and restore on refresh/Back/Forward; keep selection, dialogs, drawers, editor draft, and cleared logs local.
- [x] Add template/route tests for navigation order, labels, URL hooks, loading/empty/filtered-empty/error/stale/conflict/disabled states, duplicate locks, destructive copy, action matrices, selection pruning, overflow shell classes, and absence of Submitted/Deferred/Promote controls.
- [x] Verify semantic controls, names/descriptions, `aria-selected`, keyboard tabs, visible focus, Escape, focus trap/restore, non-color cues, contrast, reduced motion, 200% zoom/reflow, long content, and light/dark parity.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -q -k "candidate_profile or bookmark or synonym or settings or navigation"`
- [x] Playwright MCP: run Candidate Profile create/detail/archive/restore/Trigger Run, Bookmark filter/select/remove/export, Run Details export, Synonym edit/review/clear/import/export, and Back/Forward flows at desktop and narrow viewport with keyboard only.
- [x] Chrome DevTools MCP: verify no uncaught console errors, duplicate requests, unexpected failed requests, page-level horizontal overflow, or focus loss; table overflow remains internal.
- Expected: production pages match approved prototype hierarchy/shared behavior while visible state derives from canonical API resources.

**Exit Criteria:**
- all central pages and dependent Run/Settings surfaces operate through shared production UI patterns with browser/accessibility evidence

### Task 7: Lock security, OpenAPI, prototype parity, and sidecar status

**Purpose:**
- reconcile every public contract and temporary UI-intent artifact after vertical slices are functional

**Specification Coverage:**
- Local Workspace Security
- Resource and Error Envelopes
- Revisions, Idempotency, and Concurrency
- OpenAPI and Frontend Transport
- Data Safety and Failure Semantics
- API, frontend, browser, and accessibility verification requirements

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py` Pydantic models, route declarations, security helpers, response media metadata, and `create_app`
- Modify: `tests/test_fitcv_cp/test_app.py` route inventory, OpenAPI, security, error, idempotency, and media assertions
- Modify: `docs/fitcv-settings-ui-prototype.html`
- Modify: `docs/fitcv-settings-ui-prototype.integration.md`
- Modify: `docs/superpowers/specs/2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md`
- Verify: `docs/superpowers/specs/2026-07-20-18-23-fitcv-prototype-backend-compatibility-spec.md`

**Dependencies:**
- Tasks 2 through 6 complete and route behavior stable

**Steps:**
- [x] Audit every new/changed unsafe route for loopback Host, same-origin Origin/Referer, shared CSRF, `Idempotency-Key`, safe filename, upload size, and secret/path redaction.
- [x] Ensure JSON routes use explicit request/response Pydantic models and standard single-resource, collection, page, and error envelopes; remove untyped public `dict` responses for integrated routes.
- [x] Assert `404`, `409`, `413`, and `422` status/error-code matrices, current revision metadata, retryability, and reconciliation identity after uncertain writes.
- [x] Assert runtime OpenAPI includes profile/ZIP multipart forms, action bodies, page/query enums, CSV/ZIP media types/filenames, stable errors, and all Candidate Profile/Bookmark/Synonym routes.
- [x] Update prototype backup behavior/self-checks from single YAML/mock object to opaque ZIP summary intent; keep approved layout/interactions otherwise unchanged.
- [x] Update integration sidecar to reference implemented operation/contract owners and remove completed Known Gaps as proof lands; do not copy OpenAPI schemas.
- [x] Search source/templates/tests for retired public terms/owners: `Submitted`, `Deferred`, `Promote Approved Synonyms`, `promote_global_enabled`, `apply_to_run_enabled`, `auto_apply_recommendation_enabled`, `auto_promote_global_enabled`, and runtime `bookmarked_jobs`.
- [x] Confirm retained historical compatibility parser normalizes only at ingestion and cannot appear in new storage, UI, settings, or public enums.
- [x] Keep sidecar if any required route, frontend state, browser flow, OpenAPI assertion, or security proof remains unresolved; delete only after Task 8 final evidence passes.

**Verification:**
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_app.py -q -k "openapi or csrf or origin or host or idempotent or candidate_profile or bookmark or synonym"`
- [x] `py -3 scripts/validate_template_required_sections.py --repo-root .` (executed; only recorded repository-wide template-status debt remains)
- [x] `rg -n "Submitted|Deferred|Promote Approved Synonyms|promote_global_enabled|apply_to_run_enabled|auto_apply_recommendation_enabled|auto_promote_global_enabled|bookmarked_jobs" src/fitcv_cp docs/fitcv-settings-ui-prototype.html tests/test_fitcv_cp`
- Expected: parent spec/plan have no template error; any remaining repository-wide template failures match recorded unrelated baseline; retired-term matches are approved historical fixtures/ingestion normalization or absent.

**Exit Criteria:**
- transport, security, OpenAPI, prototype, and temporary sidecar agree with implemented behavior and no retired owner remains reachable

### Task 8: Prove fresh cutover and complete integration handoff

**Purpose:**
- run fresh end-to-end evidence, reconcile plan, and remove temporary sidecar only when full approved contract passes

**Specification Coverage:**
- all Verification Requirements and Acceptance Criteria
- Fresh Cutover and Compatibility
- sidecar removal condition from `skill-full-stack-integration`

**Required Skills:**
- `skill-verification-before-completion`
- `skill-full-stack-integration`

**Files And Symbols:**
- Verify: `src/fitcv_cp/store.py`
- Verify: `src/fitcv_cp/sqlite_store.py`
- Verify: `src/fitcv_cp/synonym_policy_io.py`
- Verify: `src/fitcv_cp/synonym_proposals.py`
- Verify: `src/fitcv_cp/settings_schema.py`
- Verify: `src/fitcv_cp/settings_store.py`
- Verify: `src/fitcv_cp/app.py`
- Verify: `src/fitcv_cp/templates`
- Verify: `tests/test_fitcv_cp`
- Verify: `docs/fitcv-settings-ui-prototype.html`
- Conditionally delete: `docs/fitcv-settings-ui-prototype.integration.md`
- Modify after verification only: `docs/superpowers/plans/2026-07-21-19-35-fitcv-central-workspace-frontend-backend-integration-plan.md`

**Dependencies:**
- Tasks 1 through 7 complete
- no unresolved required test, browser, security, OpenAPI, reset, or sidecar evidence gap

**Steps:**
- [x] Create old-schema local database fixture, confirm startup refuses writes with `database_schema_incompatible`, run existing operator reset flow, and prove timestamped DB/WAL/SHM backup preservation.
- [x] Start fresh runtime and prove seeded Active + Succeeded profiles, initial active synonym bundle, approved settings defaults, and empty Runs/bookmarks/suggestion queue.
- [x] Execute valid profile import, admitted failed import, Trigger Run snapshot capture, bookmark create/list/remove/export, archived Run delete preview/final cascade, synonym pending/approve/blocked/corrected/decline/clear, processing history, and ZIP export/import plus forced YAML mirror repair.
- [x] Run desktop/narrow browser flows with keyboard, light/dark, reduced motion, long content, 200% zoom, focus restoration, internal table overflow, stale retries, and duplicate-submit checks.
- [x] Inspect browser network/console for correct requests, envelopes, CSV/ZIP headers, no duplicate writes, no unexpected failures, no secrets/absolute paths, and no page-level horizontal overflow.
- [x] Run focused/full Python suites, compile checks, planning lifecycle validator, fast repository validator, and whitespace check.
- [x] Compare full-suite and validator failures with recorded baseline; document exact unchanged unrelated failures, reject every new or changed failure, and never present baseline debt as integration proof.
- [x] Remove `docs/fitcv-settings-ui-prototype.integration.md` only when every referenced backend, frontend, browser, security, and OpenAPI item passes; otherwise retain only exact unresolved items.
- [x] Reconcile every task checkbox, substitution, deviation, and proof result; set status `completed` only after `skill-verification-before-completion` returns `verified`.

**Verification:**
- [x] `py -3 -m py_compile src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/synonym_policy_io.py src/fitcv_cp/synonym_proposals.py src/fitcv_cp/settings_schema.py src/fitcv_cp/settings_store.py src/fitcv_cp/app.py`
- [x] `py -3 -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_app.py -q`
- [x] `py -3 -m pytest tests -q` (same 51 unrelated baseline failures; `2234 passed, 4 skipped`)
- [x] `py -3 scripts/validate_planning_lifecycle.py` (same repository-wide planning metadata baseline failures)
- [x] `py -3 scripts/hooks/run_validator.py --fast` (same planning metadata baseline failures)
- [x] `git diff --check`
- Expected: fresh reset, persistence, API, OpenAPI, security, frontend, browser, accessibility, CSV, ZIP, deletion cascade, and immutable snapshot evidence pass; touched artifacts add no test or validator failure; any remaining failure exactly matches documented unrelated baseline.

**Exit Criteria:**
- parent specification is implemented and freshly verified; temporary sidecar is removed or contains only exact unresolved evidence; plan is eligible for verified completion

## Execution Evidence And Blockers

Evidence captured on July 21–22, 2026 in worktree `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\.worktrees\fitcv-central-workspace-integration-impl`:

- `py -3 -m pytest tests/test_fitcv_cp/test_app.py -q --tb=short`: `417 passed`.
- Focused contract suite: `762 passed, 1 skipped`; complete control-plane suite: `1006 passed, 1 skipped`.
- Prototype contract suite: `2 passed`; focused OpenAPI/security/profile/bookmark/synonym suite: `50 passed, 367 deselected`.
- Compile command and `git diff --check` passed. Pytest emitted only known Windows temporary-directory cleanup warnings after successful exits.
- Playwright verified synonym editor search/focus, read-only/edit/save protection, Pending/Approved/Declined action matrices, Candidate Profile-derived Trigger Run options, archived Run dependency confirmation, Bookmark internal scrolling and 14px toolbar/table gap, desktop/narrow layouts, light/dark themes, reduced motion, 200% zoom emulation, keyboard order, and dialog focus restoration.
- Chrome DevTools verified prototype self-check, no page-level horizontal overflow, internal Bookmark table overflow, and no console or failed-resource errors after the inline favicon fix.
- Launcher-equivalent fresh runtime created one active synonym bundle, three type revisions, three valid drafts, approved settings defaults, and empty Run/bookmark/suggestion collections before serving requests.
- Live ZIP proof returned `200`, `application/zip`, filename `fitcv-synonyms-backup.zip`, exactly three canonical YAML files plus `manifest.json`, successful round-trip import, and semantically identical idempotent replay.
- Repository-wide `py -3 -m pytest tests -q --tb=short` completed with `2234 passed, 4 skipped, 51 failed`. No `tests/test_fitcv_cp` failure remains. Failure identities and count exactly match recorded baseline: missing private Candidate Profile fixture, deferred-cleanup characterization debt, unavailable inverse-optimization solver behavior, and repository planning/config/template validator debt.
- `validate_planning_lifecycle.py`, `run_validator.py --fast`, and `validate_template_required_sections.py --repo-root .` remain blocked by pre-existing repository-wide metadata/template debt in historical artifacts outside this plan's write scope.
- Live production Candidate Profile import/detail/archive/restore, Trigger Run profile population, Bookmark projection/export/stale-preview behavior, CSV headers, and Synonym ZIP transport passed.
- Live production Synonym browser proof passed on July 22, 2026: editor read-only/Edit/Save and search selection, Pending/Approved/Declined action matrices, Suggestion Overview and evidence separation, processing-log local Clear, ZIP download/import, Settings linkage, Back/Forward restoration, dialog focus restoration, long editor scrolling/manual resize, desktop/narrow internal table overflow, light/dark themes, reduced-motion media state, no page-level overflow, no exposed absolute paths/secrets, no browser warnings/errors, and only intended successful writes in server request logs.
- Browser proof found processing summary fields rendered as `undefined` because template read deprecated short names instead of canonical `*_count` response fields. A failing template-contract assertion reproduced the mismatch before the minimal fix; focused regression now passes and live output reads `Approved 1 | Declined 0 | Pending 0 | Added 1`.

Plan is `completed`. Temporary integration sidecar is removed; unchanged repository-wide planning/template validator debt remains documented as unrelated baseline.

## Verification

- `py -3 -m py_compile src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/synonym_policy_io.py src/fitcv_cp/synonym_proposals.py src/fitcv_cp/settings_schema.py src/fitcv_cp/settings_store.py src/fitcv_cp/app.py`
- `py -3 -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_synonym_global_policy_io.py tests/test_fitcv_cp/test_local_storage.py tests/test_fitcv_cp/test_local_app.py -q`
- `py -3 -m pytest tests -q`
- `py -3 scripts/validate_planning_lifecycle.py`
- `py -3 scripts/hooks/run_validator.py --fast`
- `git diff --check`
- Full-suite and validator results are compared with captured pre-implementation baseline; only exact unchanged unrelated failures may remain.
- Playwright MCP evidence covers Candidate Profile, Trigger Run, Bookmark, Run Details export, Synonym editor/review/log/backup, Settings linkage, deletion confirmation, URL restoration, keyboard/focus, desktop/narrow, light/dark, reduced motion, long content, 200% zoom, and internal horizontal scrolling.
- Chrome DevTools MCP evidence confirms stable API requests/errors, correct CSV/ZIP downloads, no duplicate submissions, no uncaught console errors, no unexpected failed requests, no secret/path leakage, and no page-level horizontal overflow.
- Fresh-database evidence covers incompatible-schema refusal, timestamped DB/WAL/SHM backup, transactional schema/profile seed/initial bundle/default settings initialization, empty collections, successful restart, and no legacy row exposure.

## Completion Criteria

The plan is ready for completion verification when:

1. every implementation outcome is satisfied;
2. every task and task-local verification item is complete;
3. Candidate Profile attempts/revisions, bookmarks, synonym policies/bundles/drafts/review/history, Run inputs, settings, and idempotency have one normalized owner;
4. failed admitted profile imports remain visible without exposing invalid content, and only Active + Succeeded profiles can create Runs;
5. every new Run atomically captures immutable profile, settings, and active validated synonym bundle identities/snapshots before enqueue;
6. bookmark Submitted status, legacy `bookmarked_jobs`, orphan snapshots, and divergent Run Details/Bookmarks projection or export logic are absent;
7. Run deletion preview/final action are all-or-nothing, report exact bookmark loss, cascade bookmarks/source associations, remove zero-source Pending/Declined suggestions, and preserve Approved decisions;
8. synonym review aggregates concept identity across Runs, exposes only Pending/Approved/Declined, preserves Approved+Blocked decisions, and activates corrected valid drafts without another approval;
9. Approve always installs valid mappings, `apply_approved_enabled` gates their use by future Runs, `auto_accept_suggestions_enabled` reuses the same Approve transaction with automation actor, and `auto_accept_ai_action_enabled` remains separate;
10. synonym ZIP import/export validates all canonical YAML files and manifest before one SQLite activation; YAML mirrors are repaired from active SQLite snapshot and never own runtime behavior;
11. public routes use explicit models, stable envelopes/errors, revisions, idempotency, loopback/same-origin/CSRF checks, safe filenames, declared media, and OpenAPI drift assertions;
12. production templates match approved prototype hierarchy, navigation, shared spacing/components, URL state, asynchronous states, keyboard/focus, responsive overflow, themes, reduced motion, and accessibility behavior;
13. old database remains backup-only, no migration/backfill/dual-read occurs, and reset preserves timestamped DB/WAL/SHM evidence;
14. integration sidecar is removed only after all referenced evidence passes, or retained with exact unresolved work;
15. plan deviations, substitutions, blockers, unrelated baseline failures, and deferrals are recorded;
16. final commands are runnable, touched artifacts add no failure, and any remaining failure exactly matches documented unrelated pre-implementation baseline.

The plan may be marked `completed` only when `skill-verification-before-completion`:

1. runs fresh final verification;
2. confirms these completion criteria against repository evidence;
3. finds no unresolved required task, failed required check, stale status, or unrecorded scope deviation;
4. returns `verified` and updates plan status.

A checked box records progress; it is not proof by itself.
