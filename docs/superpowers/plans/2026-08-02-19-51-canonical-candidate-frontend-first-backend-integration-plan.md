---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: canonical-candidate-frontend-first-backend-integration
parent_spec: docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md
targets:
  - config/runtime/control_plane.yaml
  - data/candidate_profile.v2.sample.yaml
  - data/candidate_profile.template.yaml
  - docs/api.md
  - docs/configuration.md
  - docs/pipeline.md
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/candidate.py
  - src/fitcv/candidate_ingest.py
  - src/fitcv/config.py
  - src/fitcv/evidence.py
  - src/fitcv/llm_runtime.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/candidate_profile_service.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/candidate_profile_mock.py
  - src/fitcv_cp/queue.py
  - src/fitcv_cp/reconciler.py
  - src/fitcv_cp/reconciler_service.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/base.html
  - src/fitcv_cp/templates/candidate_profiles.html
  - src/fitcv_cp/templates/candidate_profile_creation.html
  - src/fitcv_cp/templates/candidate_profile_sections.html
  - src/fitcv_cp/templates/candidate_profile_detail.html
  - tests/test_agentic_cv_analysis.py
  - tests/test_candidate.py
  - tests/test_candidate_profile_ingest.py
  - tests/test_candidate_profile_template_contract.py
  - tests/test_evidence.py
  - tests/test_llm_runtime.py
  - tests/test_pipeline.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_candidate_profile_service.py
  - tests/test_fitcv_cp/test_local_app.py
  - tests/test_fitcv_cp/test_queue.py
  - tests/test_fitcv_cp/test_reconcile_integration_sqlite.py
  - tests/test_fitcv_cp/test_reconciler.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_store.py
  - docs/fitcv-settings-ui-prototype.integration.md
---

# Canonical Candidate Frontend-First Backend Integration Plan

## Goal

Replace approved mock-backed Candidate Profile creation with a matching durable backend, then integrate one uniform evidence projection without changing the approved frontend transport or presentation contract.

## Implementation Outcomes

### Contract SSOT

`docs/fitcv-settings-ui-prototype.html` owns presentation. `src/fitcv/candidate.py` owns canonical field metadata. `src/fitcv_cp/models.py` owns transport models. Mock data and review components consume those contracts without restating prototype layout. Verification records prototype blob before browser comparison.

Current approved prototype blob: `989af611bd7767c148022c79ac00c5069d8a3956`.

### Approval-Ready Frontend

Upload, Baseline, Controlled Derivation, Confirmation, Candidate Profiles, and Candidate Details render approved prototype behavior through real Jinja pages and HTTP calls.

### Durable Staged Backend

Markdown, DOCX, and YAML enter one accepted-upload lifecycle with deterministic extraction, bounded shared-runtime LLM assistance, attempt CAS revisions, immutable approval snapshots, idempotent confirmation, SQLite v5 persistence, recovery, and private-source retention.

### Uniform Pipeline Projection

V1 and v2 profiles converge in memory before one section-neutral evidence projector. Education, experience, projects, achievements, certifications, and volunteering use same evidence grain, scoring path, trace chain, and global selection budget without mutating canonical revisions.

### Mock Replacement And Contract Closure

Real backend passes frozen mock route assertions before production mock removal. OpenAPI, executable tests, persisted resources, and browser proof replace temporary UI Intent only after complete frontend/backend equality.

### Backend Gate

Frontend approval gate passed on August 3, 2026. Tasks 1-4 are complete against prototype blob `989af611bd7767c148022c79ac00c5069d8a3956`; backend Tasks 5-10 are authorized and remain sequential.

Reserved local port: `8765` belongs to Anki and must not be used by FitCV mock, audit, or test servers. Use explicit port `8766` or another free non-`8765` port.

## Drift Correction

Root causes:

1. Active lane held stale prototype blob `c592804fe7df93631c1fd23f61504f189381fd6d` while approved main-workspace prototype was restored to `989af611bd7767c148022c79ac00c5069d8a3956`.
2. Recovered UI Intent and full plan were replaced by abbreviated summaries, while prototype, spec, tests, templates, CSS, and mock fixtures each restated presentation independently.
3. Generic schema-to-form rendering treated canonical field presence as editability, exposing IDs, origin, confidence, support metadata, and comma-separated `evidence_refs` instead of approved stage components.
4. Markup tests asserted labels such as `Evidence references` but did not reject incompatible controls or internal-field editors.
5. Prototype and Python mock used different fixture IDs, values, selected refs, and capabilities, preventing meaningful visual comparison.
6. Browser approval lacked a complete page-by-page parity matrix and therefore missed untouched surfaces.

Correction rules:

- verify approved prototype blob before browser comparison
- preserve schema as field-contract SSOT and exact prototype blob as presentation SSOT
- use one deterministic fixture for prototype and mock comparison
- preserve exact prototype DOM hierarchy, classes, action order, and button variants
- render Confirmation and Candidate Details through one section-card wrapper plus shared baseline and derived preview components, using exact prototype section order and expanded state
- keep checksum and provenance in mock/API contracts but reject them from user-visible profile markup
- assert exact component hierarchy, action order, fixture values, computed high-risk styles, section order, and forbidden checksum output
- invalidate prior browser approval evidence whenever approved prototype blob changes

## Execution Approach

- Mode: `inline sequential`
- Workspace: `.worktrees/codex-canonical-candidate-frontend-first-backend-integration`
- Branch: `codex/canonical-candidate-frontend-first-backend-integration`
- Base: `main` at `fdced4de7816a0df260e9ec026fbf08ff2683cc3`
- Required skills: `skill-executing-plans`, `skill-test-driven-development`, `skill-full-stack-integration`, `ui-ux-pro-max`
- Phase boundary: preserve approved frontend request shapes and prototype presentation while Tasks 5-10 replace mock state with deterministic ingestion, shared LLM processing, SQLite v5 persistence, recovery, retention, and uniform evidence projection

## Task Breakdown

### Task 1: Materialize mock contract SSOT

**Purpose:**
- Expose field metadata and typed staged-creation resources without implementing canonical persistence.

**Specification Coverage:**
- Field-schema API, attempt CAS revision, review envelopes, capabilities, fingerprints, ID-addressed paths, and confirmation/detail equality.

**Required Skills:**
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv/candidate.py`: `CANDIDATE_PROFILE_V2_FIELD_REGISTRY`, schema projection, checksum.
- Modify: `src/fitcv_cp/models.py`: staged Candidate Profile request/response models.
- Verify: `tests/test_candidate.py`, `tests/test_fitcv_cp/test_app.py`.

**Dependencies:**
- Approved specification.

**Steps:**
- [x] Add failing registry and OpenAPI tests.
- [x] Implement registry and transport models only.
- [x] Keep canonical payload validation deferred to backend Task 5.

**Verification:**
- [x] `uv run pytest tests/test_candidate.py tests/test_fitcv_cp/test_app.py -q`
- Expected: field schema and models are stable; existing profile API remains green.

**Exit Criteria:**
- Mock and UI can consume one field and transport contract.

### Task 2: Expose deterministic mock routes

**Purpose:**
- Serve complete mock lifecycle over real HTTP routes.

**Specification Coverage:**
- Upload, attempts, source blocks, baseline/derived patch/regenerate/approve, retry, confirmation, list/detail, archive/restore.

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`

**Files And Symbols:**
- Add: `src/fitcv_cp/candidate_profile_mock.py`: deterministic mock state and mock app export.
- Modify: `src/fitcv_cp/app.py`: staged Candidate Profile JSON/admin routes.
- Modify: `src/fitcv_cp/store.py`: mock override surface using existing `ControlPlaneStore` pattern.
- Verify: `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_store.py`.

**Dependencies:**
- Task 1 complete.

**Steps:**
- [x] Add failing lifecycle route tests.
- [x] Implement deterministic multiple-entry baseline and individually traceable derived claims.
- [x] Implement mock state transitions, idempotent confirmation, archive/restore, source dialogs, and stable conflicts.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_store.py -q`
- Expected: mock contract works through real HTTP and keeps confirmed resources separate from attempts.

**Exit Criteria:**
- Every approval UI action has callable mock operation.

### Task 3: Build production frontend against mock

**Purpose:**
- Replace direct YAML dialog with staged creation pages.

**Specification Coverage:**
- Profile Name in Upload, repeatable symmetric collections, conditional wands, Source dialogs, review batching, confirmation/details shared sections, responsive/accessibility rules.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-full-stack-integration`
- `skill-test-driven-development`

**Files And Symbols:**
- Modify: `src/fitcv_cp/templates/base.html`.
- Modify: `src/fitcv_cp/templates/candidate_profiles.html`.
- Add: `src/fitcv_cp/templates/candidate_profile_creation.html`.
- Add: `src/fitcv_cp/templates/candidate_profile_sections.html`.
- Modify: `src/fitcv_cp/templates/candidate_profile_detail.html`.
- Verify: `tests/test_fitcv_cp/test_app.py`.

**Dependencies:**
- Task 2 complete.

**Steps:**
- [x] Add failing admin route/markup tests.
- [x] Build one stage-driven creation template and one shared canonical section renderer.
- [x] Bind forms to mock operations with native controls, visible focus, dialogs, live status, and narrow layout.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_app.py -q`
- [x] Extract changed template scripts and run `node --check`.
- Expected: no field registry duplicated in template; confirmation/details render same canonical object.

**Exit Criteria:**
- Frontend mockup is complete for browser review.

### Task 4: Verify approval-ready mockup

**Purpose:**
- Produce mock browser evidence and stop before backend integration.

**Specification Coverage:**
- Desktop/narrow layout, keyboard, focus, source dialog, multiple entries, field regeneration, stage approvals, confirmation/detail equality.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-full-stack-integration`

**Files And Symbols:**
- Modify: `docs/fitcv-settings-ui-prototype.integration.md`: unresolved evidence only.
- Verify: mock app and all changed templates.

**Dependencies:**
- Task 3 complete.

**Steps:**
- [x] Build parity matrix for Candidate Profiles, Upload, Baseline, Derived, Confirmation, Details, and LLM Configuration.
- [x] Align shared CSS, exact DOM hierarchy, classes, action order, button variants, and default states with prototype.
- [x] Replace independent prototype/mock content with one deterministic comparison fixture.
- [x] Generate symmetric review annotations for every admissible derived entry.
- [x] Run browser comparison for all seven surfaces at desktop and narrow viewports.
- [x] Verify native controls, dialogs, checkbox evidence editing, focus return, 200% zoom, light/dark, reduced motion, and long labels.
- [x] Stop and obtain user approval before backend Task 5; approved August 3, 2026.

**Verification:**
- [x] Exact DOM/action/fixture parity tests pass.
- [x] Full corrected browser flow and screenshot comparison pass.
- [x] Independent verifier reports specification compliance pass and UI parity approved against prototype blob `989af611bd7767c148022c79ac00c5069d8a3956`.
- [x] Source dialogs, LLM copy, derived metadata, evidence labels, and confirmation date projection match prototype exactly.
- [x] `git diff --check`.

**Exit Criteria:**
- User approved all seven mock surfaces against prototype; backend Task 5 may begin without frontend contract redesign.

### Task 5: Implement canonicalization and deterministic ingestion

**Purpose:**
- Convert supported source formats into deterministic source blocks and canonical v2 baseline candidates without model authority.

**Specification Coverage:**
- `.md`, `.docx`, and `.yaml` unified ingress
- Coarse pre-attempt rejection versus inspectable accepted-upload failure
- Safe filenames, byte limits, media verification, no path traversal, no remote dereference, safe YAML loading
- Markdown lines, DOCX paragraph/table/header/footer locators, canonical YAML uploaded/declared provenance, and verified uploaded source root
- V1 YAML compatibility input produces v2 only after staged confirmation

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Add: `src/fitcv/candidate_ingest.py`: upload classification, Markdown extractor, DOCX ZIP/XML extractor, YAML importer, source-block builder, and extraction fingerprint
- Modify: `src/fitcv/candidate.py`: v2 canonicalizer, uploaded/declared provenance normalization, v1-to-v2 draft adapter, cross-reference validation, deterministic IDs, and canonical checksum
- Modify: `data/candidate_profile.v2.sample.yaml`: synthetic Markdown or DOCX locator examples and all symmetric evidence sections
- Modify: `data/candidate_profile.template.yaml`: current supported canonical authoring guidance without private values
- Verify: `tests/test_candidate_profile_ingest.py`
- Verify: `tests/test_candidate.py`
- Verify: `tests/test_candidate_profile_template_contract.py`

**Dependencies:**
- Task 4 acceptance gate passed
- Task 1 registry is sole field and validation metadata owner
- Use Python `zipfile` and `xml.etree.ElementTree`; add no DOCX dependency

**Steps:**
- [x] Add corpus tests for valid/invalid Markdown, DOCX paragraphs, tables, headers, footers, corrupt ZIP, encrypted/unsupported package, oversized expansion, YAML v1, YAML v2, empty input, media/extension mismatch, duplicate IDs, dangling refs, invalid locators, invalid dates, and contradictory `current`/`end`.
- [x] Implement coarse validation that rejects unsupported extension/media, empty request, request byte overflow, and unsafe filename before attempt creation.
- [x] Implement deterministic Markdown and DOCX extraction with bounded normalized blocks, native locators, parser name/version, stable ordering, checksum, and fingerprint; never send binary DOCX to LLM.
- [x] Implement safe YAML import that creates verified uploaded source metadata, preserves valid supplied source documents as declared metadata, injects uploaded document refs into every evidence-bearing parent and evidence statement, and rejects contradictory or dangling supplied provenance.
- [x] Implement deterministic v1 adaptation with stable generated evidence IDs, parent-reference expansion, `current: true` to `end: Present`, legacy evidence `date` to `start`, and no rewrite of stored historical v1 revisions.
- [x] Keep search preferences user-owned and exclude them from evidence extraction.

**Verification:**
- [x] `uv run pytest tests/test_candidate_profile_ingest.py tests/test_candidate.py tests/test_candidate_profile_template_contract.py -q`
- [x] `uv run python -m compileall -q src/fitcv/candidate.py src/fitcv/candidate_ingest.py`
- Expected: repeated input produces identical blocks, IDs, locators, canonical payload, and fingerprints; every evidence chain reaches uploaded bytes; corrupt or unsupported input fails with specified stable boundary.

**Exit Criteria:**
- Deterministic ingestion and canonicalization are complete and independently tested for all three formats.

### Task 6: Implement staged processor and shared LLM routing

**Purpose:**
- Add deterministic-first baseline mapping, controlled derivation, regeneration, approval, invalidation, and retry using existing shared LLM runtime.

**Specification Coverage:**
- `candidate_profile_base_mapping` handles only unresolved/ambiguous source blocks
- `candidate_profile_derived_claims` consumes exact approved baseline
- LLM cannot create canonical IDs, source locators, evidence text, approval, or revision
- Per-field and all-field regeneration obey server annotations
- Baseline edits invalidate all derived state; derived edits invalidate derived approval
- Existing LLM Configuration owns model routing and existing failure normalization

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`
- `skill-full-stack-integration`

**Files And Symbols:**
- Add: `src/fitcv_cp/candidate_profile_service.py`: extraction/mapping/derivation stage runner, claim validation, regeneration target resolution, approval validation, retry resume, and confirmation assembly
- Modify: `src/fitcv/llm_runtime.py`: add only reusable Candidate Profile structured request/result projections required by both tasks
- Modify: `src/fitcv/config.py`: register both prompt task IDs through existing prompt task registry
- Modify: `src/fitcv_cp/settings_store.py`: add both task IDs to existing LLM configuration resource and validation
- Modify: `config/runtime/control_plane.yaml`: define routing parts and bounded defaults for both Candidate Profile tasks
- Modify: `src/fitcv_cp/app.py`: retain existing revision-only `PATCH /llm-configuration` while exposing added task rows
- Verify: `tests/test_llm_runtime.py`
- Verify: `tests/test_fitcv_cp/test_candidate_profile_service.py`
- Verify: `tests/test_fitcv_cp/test_local_app.py`

**Dependencies:**
- Task 5 complete
- Existing shared LLM adapter, JSON-schema parsing, failure normalization, provenance, and settings revision behavior remain owners

**Steps:**
- [x] Add failing service tests for deterministic-only baseline, ambiguous baseline LLM call, structured failure, unsupported inference, derived claims with separate `evidence_refs`, per-target regeneration, wildcard regeneration, non-regenerable fields, stale revisions, upstream invalidation, approval fingerprints, retry, and exact confirmation assembly.
- [x] Implement baseline mapper that preserves deterministic facts, calls LLM only for bounded unresolved blocks, validates returned proposals against source blocks, and assigns server IDs/source refs after validation.
- [x] Implement derived-claim generator for skills, role families, domain tags, and responsibility themes with stable server IDs, `origin`, bounded confidence, and evidence-item references only.
- [x] Implement one target resolver for baseline and derived paths; annotations declare regeneration capability and source-block binding.
- [x] Implement approval snapshots and invalidation rules without mutating approved upstream snapshots on failed LLM calls or route changes.
- [x] Store one shared runtime evidence record for each actual model call; never copy provider credentials or raw provider payload into Candidate Profile tables.
- [x] Keep LLM settings mutations on current revision conflict contract and current error code.

**Verification:**
- [x] `uv run pytest tests/test_llm_runtime.py tests/test_fitcv_cp/test_candidate_profile_service.py tests/test_fitcv_cp/test_local_app.py -q`
- [x] `uv run python -m compileall -q src/fitcv/llm_runtime.py src/fitcv/config.py src/fitcv_cp/candidate_profile_service.py src/fitcv_cp/settings_store.py`
- Expected: deterministic data survives model failure, every derived claim is traceable, invalid targets fail stably, and existing LLM settings API behavior remains unchanged except added task IDs.

**Exit Criteria:**
- Staged processing logic is complete behind store-neutral service contracts and shared runtime only.

### Task 7: Migrate SQLite and add lifecycle recovery

**Purpose:**
- Persist staged creation, immutable revisions, source traceability, concurrency, idempotency, recovery, and retention atomically.

**Specification Coverage:**
- Atomic SQLite version 4 to 5 migration and rollback
- Required persistence grains and foreign keys
- Sole mutable attempt CAS revision and immutable snapshots/fingerprints
- Durable processing claim/lease, crash reconciliation, retry resume, and one publisher
- 30-day inactive unconfirmed source purge
- Legacy succeeded identity preservation and failed diagnostics-only attempt mapping
- Confirmation transaction creates exactly one profile/revision and preserves archive/history semantics

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/sqlite_store.py`: schema version `5`, migration, Candidate Profile tables, CRUD, claims, review batches, confirmation, source BLOB access, purge, lifecycle, Run eligibility, and compatibility reads
- Modify: `src/fitcv_cp/store.py`: concrete `ControlPlaneStore` forwarding methods and typed protocol parity
- Modify: `src/fitcv_cp/reconciler.py`: expired Candidate Profile claim and retention reconciliation alongside existing Run reconciliation
- Modify: `src/fitcv_cp/reconciler_service.py`: call combined reconciliation without introducing second periodic service
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`
- Verify: `tests/test_fitcv_cp/test_reconciler.py`
- Verify: `tests/test_fitcv_cp/test_reconcile_integration_sqlite.py`

**Dependencies:**
- Task 6 complete
- Store retained uploaded bytes as BLOB in `candidate_profile_source_documents` so accepted upload, source access, confirmation linkage, backup ownership, and atomic purge remain inside existing SQLite transaction boundary
- Existing `idempotent_actions`, Run input foreign keys, database backup policy, and reconciler loop remain shared owners

**Steps:**
- [x] Add version-4 migration fixtures containing succeeded active/archived/default profiles, blank Profile Name, duplicate Profile Names, v1 revision JSON, related Run inputs, and failed direct uploads.
- [x] Implement one transactional migration that rebuilds incompatible Candidate Profile tables, creates `candidate_profile_creation_attempts`, `candidate_profile_source_documents`, `candidate_profile_source_blocks`, `candidate_profile_baseline_snapshots`, `candidate_profile_derived_snapshots`, and `candidate_profile_review_batches`, then validates counts, uniqueness, and `PRAGMA foreign_key_check` before setting `user_version = 5`.
- [x] Preserve succeeded profile IDs, lifecycle, catalog revision, default/sort metadata, timestamps, revision IDs, JSON, checksum, schema revision, and every Run foreign key; persist blank-name fallback once.
- [x] Convert failed direct uploads into non-retryable legacy attempt diagnostics with migration source ID, filename, media type, byte length, checksum, timestamps, and safe failure; create no bytes, blocks, or invented provenance.
- [x] Implement accepted-upload transaction, BLOB download with checksum ETag and `nosniff`, source-block reads, append-only snapshots/review batches, expected-revision CAS, idempotent action replay, processing claim/lease publication guard, approval pointers, and exact confirmation transaction.
- [x] Implement `candidate_profile_processing_abandoned` reconciliation that preserves last valid snapshots and records owning failed stage/resume state.
- [x] Implement 30-day purge transaction that records `candidate_profile_source_expired`, clears BLOB/source blocks/private snapshots, retains safe metadata/diagnostics, returns `410`, and never purges confirmed or archived source.
- [x] Enforce active succeeded profile at new Run creation while preserving historical Run inputs after archive.
- [x] Inject migration and confirmation failures to prove rollback leaves version 4 or pre-confirmation version 5 state readable and complete.

**Verification:**
- [x] `uv run pytest tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py -q`
- [x] `uv run python -m compileall -q src/fitcv_cp/store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/reconciler.py src/fitcv_cp/reconciler_service.py`
- Expected: migration preserves counts/checksums/FKs, failure rolls back, one claim publishes, one confirmation creates one first revision, purge is atomic, and archived profiles remain historically resolvable.

**Exit Criteria:**
- SQLite v5 and reconciliation satisfy all persistence, migration, privacy, and recovery invariants.

### Task 8: Replace mock with real backend parity

**Purpose:**
- Bind unchanged frontend routes to real service/store implementation and remove direct YAML bypass.

**Specification Coverage:**
- All formats use same staged lifecycle
- Drafts never appear as profiles or Run inputs
- Exact confirmation/details canonical equality
- Server capabilities own actions and Run eligibility
- Current direct `POST /candidate-profiles` bypass is retired
- Archive blocks new Runs and preserves historical Runs

**Required Skills:**
- `skill-test-driven-development`
- `skill-full-stack-integration`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py`: bind Candidate Profile operations to real store/service, dispatch asynchronous processing, retire direct `POST /candidate-profiles`, and preserve `GET /candidate-profiles`
- Modify: `src/fitcv_cp/queue.py`: add `enqueue_candidate_profile_stage` using existing inline/RQ split and stable `candidate_profile_service.execute_candidate_profile_stage` target
- Modify: `src/fitcv_cp/store.py`: remove mock-only forwarding hooks after real parity
- Delete: `src/fitcv_cp/candidate_profile_mock.py`
- Modify: `src/fitcv_cp/templates/candidate_profile_creation.html`: only parity fixes; no request-shape redesign
- Modify: `src/fitcv_cp/templates/candidate_profiles.html`: reconcile returned server attempts/profiles only
- Modify: `src/fitcv_cp/templates/candidate_profile_detail.html`: render persisted canonical object unchanged
- Verify: `tests/test_fitcv_cp/test_app.py`
- Verify: `tests/test_fitcv_cp/test_local_app.py`
- Verify: `tests/test_fitcv_cp/test_queue.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Task 7 complete
- Task 4 request shapes are frozen; backend adapts to approved transport unless spec change is approved first

**Steps:**
- [x] Parameterize route contract tests so same assertions run against deterministic mock before deletion and SQLite-backed real app.
- [x] Bind upload acceptance to coarse validation plus atomic source/attempt persistence, then schedule extraction with durable claim identity.
- [x] Route extraction, derivation, and regeneration through `enqueue_candidate_profile_stage`; pass only attempt ID, stage, claim ID, and expected revision/fingerprint needed for guarded publication; inline and RQ execution use same service function.
- [x] Bind baseline/derived get, patch, regenerate, approve, retry, confirmation, source, list, detail, runs, archive, restore, and field-schema routes to real store/service methods.
- [x] Remove direct YAML `POST /candidate-profiles`; assert YAML can create only through `POST /candidate-profile-creation-attempts` and confirmation.
- [x] Compare confirmation response canonical JSON/checksum with saved Candidate Details and next list read; prohibit optimistic profile row creation.
- [x] Prove exact idempotent confirmation returns same Candidate Profile even with repeated same-fingerprint confirmation under a new key.
- [x] Delete production mock module and mock-only startup path after parity tests pass; keep deterministic test fixtures inside tests only.

**Verification:**
- [x] Candidate Profile scope: `631 passed, 5 deselected`; excluded five independently reproducible failures in unrelated scan styling, runtime credential/configuration, synonym routing, and pipeline settings tests.
- [x] `$matches = rg -n "candidate_profile_mock|FITCV_CANDIDATE_PROFILE_MOCK|/__mock__" src; if ($LASTEXITCODE -eq 0) { $matches; throw "Production Candidate Profile mock references remain" }; if ($LASTEXITCODE -ne 1) { exit $LASTEXITCODE }; "No production Candidate Profile mock references."`
- Expected: real backend passes frozen route contract, direct bypass is absent, frontend code requires no contract fork, and production mock code is gone.

**Exit Criteria:**
- Real staged backend replaces mock with transport and UI parity.

### Task 9: Integrate uniform evidence projection

**Purpose:**
- Make v1 and v2 Candidate Profiles feed one section-neutral evidence pipeline.

**Specification Coverage:**
- One nested evidence statement produces one `candidate-evidence.v1` item
- Education, experience, projects, achievements, certifications, and volunteering use same path
- Claims reference evidence IDs; inverse skill links are runtime-derived
- Section/kind do not change base relevance or reserve quota
- Runtime projection remains deterministic and never mutates canonical revision
- Pipeline records source profile schema and effective projection schema

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/agentic_cv_analysis.py`: record source profile and effective projection identity in analysis evidence summaries
- Modify: `src/fitcv/candidate.py`: expose v1/v2 runtime convergence function and immutable profile fingerprint
- Modify: `src/fitcv/evidence.py`: replace section collectors with one projector, build inverse skill index, use one relevance function and global selection budget, retain section/kind only as explanatory metadata
- Modify: `src/fitcv/pipeline.py`: preserve projection identity in pipeline evidence-selection metadata
- Modify: `docs/pipeline.md`: document v1/v2 convergence, projection schema, section-neutral selection, and trace chain
- Verify: `tests/test_agentic_cv_analysis.py`
- Verify: `tests/test_candidate.py`
- Verify: `tests/test_evidence.py`
- Verify: `tests/test_pipeline.py`

**Dependencies:**
- Task 8 complete
- Existing configured global evidence limits remain; section-specific weights, quotas, and diversity bonuses cannot influence base score or reserve slots

**Steps:**
- [x] Add tests for experienced-only, education-only fresh graduate, mixed sections, certifications, volunteering, repeated equivalent statements, dangling skill refs, duplicate IDs, unchanged profile checksum, and repeated projection fingerprint.
- [x] Adapt immutable v1 profile snapshot to v2-compatible nested evidence in memory with deterministic IDs; never rewrite stored v1 JSON.
- [x] Project all nested evidence through one function that adds parent context, resolves source refs, derives linked skills from `skills[].evidence_refs`, and emits one globally unique evidence ID per canonical evidence entry.
- [x] Remove `TYPE_WEIGHTS` and per-section quota/reservation effects from active v2 selection path; use content, linked skills, recency/completeness rules approved by specification, and one global budget.
- [x] Keep compatibility output fields only where current downstream consumers require them; mark projection schema explicitly and test equal content from different sections receives equal base treatment.
- [x] Ensure CV analysis/generation traceability resolves `claim -> evidence_refs -> evidence item -> source_refs -> uploaded source document` without profile mutation.

**Verification:**
- [x] `uv run pytest tests/test_candidate.py tests/test_evidence.py -q`
- [x] `uv run python -m compileall -q src/fitcv/candidate.py src/fitcv/evidence.py`
- Expected: education competes uniformly, v1 and v2 converge, repeated projection is stable, and runtime fields never enter canonical JSON.

Focused evidence: `92 passed, 1 skipped` across Candidate Profile convergence, evidence projection, and CV analysis; `137 passed` across pipeline tests.

**Exit Criteria:**
- Candidate Profile creation and pipeline consumption share one canonical truth and one symmetric evidence projector.

### Task 10: Reconcile docs and prove integrated flow

**Purpose:**
- Close contract ownership, preserve restored UI Intent as an approved source, and produce fresh completion evidence.

**Specification Coverage:**
- OpenAPI/tests replace specification as current transport truth after implementation
- Restored UI Intent remains an approved source until the user explicitly supersedes it
- Documentation, samples, settings, pipeline, migration, and private-data boundaries match implemented behavior
- Complete MD, DOCX, and YAML user flow is verified end to end

**Required Skills:**
- `skill-full-stack-integration`
- `ui-ux-pro-max`
- `skill-verification-before-completion`

**Files And Symbols:**
- Modify: `docs/api.md`: implemented Candidate Profile operations, errors, idempotency, ETag, and removal of direct upload
- Modify: `docs/configuration.md`: Candidate Profile LLM task routing, source retention, and local data ownership
- Modify: `docs/pipeline.md`: final profile selection and projection behavior
- Inspect: `docs/fitcv-settings-ui-prototype.html`: preserve exact approved visual SSOT blob `989af611bd7767c148022c79ac00c5069d8a3956`; do not edit during backend integration
- Preserve: `docs/fitcv-settings-ui-prototype.integration.md` as restored UI Intent designated source of truth
- Verify: all files listed in plan targets

**Dependencies:**
- Task 9 complete
- Production mock scan from Task 8 passes
- Real-backend browser flow must pass before completion

**Execution Evidence — August 3, 2026:**
- YAML completed real SQLite upload, baseline approval, controlled derivation approval, idempotent confirmation, exact Confirmation/Candidate Details canonical equality, catalog visibility, archive replay, restore symmetry, and Run eligibility capability checks on port `8766`.
- Real attempt resources now expose baseline and derived approval timestamps from approved immutable snapshots; focused SQLite and Candidate Profile app suites pass.
- Candidate Profile RQ jobs now use RQ-valid stable IDs; focused queue and Candidate Profile app suites pass.
- Markdown and DOCX pass upload validation, source persistence, queue dispatch, deterministic extraction, and terminal failure projection, but full review remains blocked by missing `candidate_profile_base_mapping` LLM routing in the isolated runtime.
- Packaged-local `/llm-configuration` exists but isolated live verification returns retryable `credential_store_failed`; existing route and settings tests remain current proof until an available credential store and configured model unblock live MD/DOCX completion.
- Integration sidecar remains because real MD/DOCX completion, full browser/accessibility matrix, and live LLM settings verification are not complete.

**Execution Evidence — August 4, 2026:**
- Markdown, DOCX, and YAML complete one real SQLite staged lifecycle through review, approval, idempotent confirmation, exact Confirmation/Candidate Details equality, archive/restore, and Run eligibility on port `8766`.
- Candidate Profile LLM routes load `FITCV_LLM_API_KEY` from `.env` and use `cx/gpt-5.4-mini`; live single-field and wildcard baseline regeneration completed at revisions `5` and `7`.
- Regeneration response schemas now constrain proposal paths to exact resolved targets; unchanged model output completes as a successful immutable-snapshot no-op instead of violating SQLite uniqueness.
- Browser evidence covers Save and exit/resume, Source dialog and focus return, one source request, individual evidence-ref editing, archive/restore, narrow layouts, dark mode, reduced motion, and zero console errors. Direct API/store tests cover stale conflict, retry, restart recovery, idempotency, and rollback boundaries.
- Plan-owned suite passes `763 passed, 1 skipped`; the guarded live-key integration passes separately with `.env`; focused changed-file suite passes `506 passed`; direct service/store suite passes `123 passed`. Compilation, JavaScript syntax, focused planning metadata, mock scan, prototype hash, and whitespace checks pass.
- Deviation: restored `docs/fitcv-settings-ui-prototype.integration.md` remains because user explicitly designated restored prototype and UI Intent as source of truth. Deletion gate is superseded; preservation is required.

**Steps:**
- [x] Update API, configuration, pipeline, sample, and template documentation from executable routes, registry, tests, and SQLite schema; do not copy second field registry into prose.
- [x] Run real SQLite MD, DOCX, and YAML creation through upload, polling, review, regeneration, evidence tracing, approvals, idempotent confirmation, details equality, archive/restore, resume, and Run-picker eligibility; use direct backend tests for conflict, retry, and restart recovery.
- [x] Run keyboard, focus, live-region, dialog, effective 200% width, narrow viewport, theme, reduced-motion, and long-content checks against real backend.
- [x] Use Chrome DevTools MCP to confirm request parity with Task 4, no duplicate source actions, correct status, no console errors, and stable confirmed-profile layout.
- [x] Run SQLite migration and restart scenarios through confirmation and historical Run access in focused backend tests.
- [x] Preserve restored integration sidecar until explicit user supersession.
- [x] Reconcile this plan: record deviations, substitutions, failures, and deferrals; `skill-verification-before-completion` returned `verified` on August 4, 2026.

**Verification:**
- [x] `uv run --extra local pytest tests/test_candidate.py tests/test_candidate_profile_ingest.py tests/test_candidate_profile_template_contract.py tests/test_evidence.py tests/test_llm_runtime.py tests/test_fitcv_cp/test_candidate_profile_service.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_app.py -q` — `763 passed, 1 skipped`
- [x] `uv run python -m compileall -q src/fitcv/candidate.py src/fitcv/candidate_ingest.py src/fitcv/config.py src/fitcv/evidence.py src/fitcv/llm_runtime.py src/fitcv_cp/app.py src/fitcv_cp/candidate_profile_service.py src/fitcv_cp/models.py src/fitcv_cp/queue.py src/fitcv_cp/reconciler.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/settings_store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/store.py`
- [x] `git diff --check`
- [x] `$matches = rg -n "candidate_profile_mock|FITCV_CANDIDATE_PROFILE_MOCK|/__mock__" src; if ($LASTEXITCODE -eq 0) { $matches; throw "Production Candidate Profile mock references remain" }; if ($LASTEXITCODE -ne 1) { exit $LASTEXITCODE }; "No production Candidate Profile mock references."`
- [x] `if ((git hash-object docs/fitcv-settings-ui-prototype.html) -ne '989af611bd7767c148022c79ac00c5069d8a3956') { throw 'Approved Candidate Profile prototype changed' } else { 'Approved prototype hash preserved.' }`
- [x] `if (-not (Test-Path -LiteralPath 'docs/fitcv-settings-ui-prototype.integration.md')) { throw 'Restored Candidate Profile UI Intent missing' } else { 'Restored Candidate Profile UI Intent preserved.' }`
- Expected: focused suites, compile checks, migration proof, real browser matrix, accessibility checks, documentation reconciliation, mock removal, restored UI Intent preservation, and whitespace validation pass.

**Exit Criteria:**
- Product uses one field registry, one staged API, one durable backend, one canonical profile revision, and one evidence projector; temporary mock is absent, restored UI Intent is preserved, and fresh verification evidence is ready.

## Verification

- `uv run pytest tests/test_candidate.py tests/test_candidate_profile_ingest.py tests/test_candidate_profile_template_contract.py tests/test_evidence.py tests/test_llm_runtime.py tests/test_fitcv_cp/test_candidate_profile_service.py tests/test_fitcv_cp/test_queue.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_reconciler.py tests/test_fitcv_cp/test_reconcile_integration_sqlite.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_app.py -q`
- `uv run python -m compileall -q src/fitcv/candidate.py src/fitcv/candidate_ingest.py src/fitcv/config.py src/fitcv/evidence.py src/fitcv/llm_runtime.py src/fitcv_cp/app.py src/fitcv_cp/candidate_profile_service.py src/fitcv_cp/models.py src/fitcv_cp/queue.py src/fitcv_cp/reconciler.py src/fitcv_cp/reconciler_service.py src/fitcv_cp/settings_store.py src/fitcv_cp/sqlite_store.py src/fitcv_cp/store.py`
- Focused planning metadata validation calls `validate_artifact` from `scripts/validate_planning_lifecycle.py` for this plan and parent specification; unrelated historical repository findings remain outside this change.
- Extract inline JavaScript from affected Jinja templates and `docs/fitcv-settings-ui-prototype.html`; run `node --check` on each extracted script.
- `$matches = rg -n "candidate_profile_mock|FITCV_CANDIDATE_PROFILE_MOCK|/__mock__" src; if ($LASTEXITCODE -eq 0) { $matches; throw "Production Candidate Profile mock references remain" }; if ($LASTEXITCODE -ne 1) { exit $LASTEXITCODE }; "No production Candidate Profile mock references."`
- `if (-not (Test-Path -LiteralPath 'docs/fitcv-settings-ui-prototype.integration.md')) { throw 'Restored Candidate Profile UI Intent missing' } else { 'Restored Candidate Profile UI Intent preserved.' }`
- `git diff --check`
- Playwright MCP completes required real-backend creation, recovery, traceability, lifecycle, Run-picker, keyboard, viewport, zoom, theme, reduced-motion, and focus flows.
- Chrome DevTools MCP confirms frozen request parity, response status/headers, no duplicate actions, bounded polling, no uncaught console errors, and stable layout.

## Completion Criteria

Plan is ready for completion verification when:

1. executable field registry is sole canonical field metadata owner and all consumers project from it
2. frontend mock acceptance gate passed before deterministic ingestion, LLM processing, or SQLite v5 implementation began
3. temporary mock and real backend pass same route-contract assertions
4. Markdown, DOCX, and YAML converge through one staged lifecycle and no direct-YAML bypass remains
5. baseline and derived review use one attempt CAS revision, immutable snapshots, ID-addressed batches, exact fingerprints, and symmetric regeneration/approval behavior
6. deterministic extraction owns source fidelity and LLM owns only ambiguous normalization or controlled derived proposals
7. every derived claim is separately editable and traceable to evidence items and verified uploaded source bytes
8. SQLite v5 migration preserves succeeded identity, immutable revisions, lifecycle, Run references, counts, checksums, and foreign keys; migrated failed rows remain diagnostics-only without invented bytes
9. processing leases, retry resume, source purge, idempotent confirmation, transaction rollback, archive symmetry, and restart recovery pass focused tests
10. Confirmation, Candidate Details, Candidate Profiles, and Run selection reconcile from same persisted resource, revision ID, canonical checksum, and lifecycle capabilities
11. v1 and v2 profiles converge before one section-neutral evidence projector and canonical revisions remain immutable across repeated Runs
12. Candidate Profile LLM tasks use existing Settings, prompt registry, adapters, runtime evidence, and revision-only configuration mutation contract
13. production mock code and mock-only startup paths are deleted
14. restored integration sidecar remains until explicit user supersession; executable contracts and tests own runtime behavior
15. focused tests, compilation, JavaScript syntax checks, migration checks, browser checks, accessibility checks, mock scan, sidecar scan, and whitespace validation pass
16. unrelated working-tree changes and unrelated historical planning-validator findings remain untouched and classified
17. implementation deviations, substitutions, blockers, and deferrals are recorded in this plan

Plan may be marked `completed` only when `skill-verification-before-completion` runs fresh final proof, reconciles every task and acceptance criterion against repository evidence, finds no unresolved required work or unrecorded deviation, returns `verified`, and updates plan status.
