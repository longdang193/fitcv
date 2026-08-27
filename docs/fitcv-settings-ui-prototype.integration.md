# FitCV Prototype Runtime Integration Ledger

Prototype visual/UI-state owner: `docs/fitcv-settings-ui-prototype.html` blob
`989af611bd7767c148022c79ac00c5069d8a3956`.

Transport owners: current FastAPI/Pydantic source, registered routes,
`/openapi.json`, `docs/api.md`, and focused route/service/store tests. Prototype
sample values never define request or response payloads.

Ledger dispositions:

- `change`: confirmed runtime drift or missing applicable UI state.
- `already aligned`: exact structure and behavior have source plus browser proof.
- `not applicable`: prototype state/action has no corresponding transport or page behavior.

## Gate 0 Route Ledger

| Slice | Prototype owner | Runtime owner | Transport owner | Confirmed drift | Disposition | Affected tests |
|---|---|---|---|---|---|---|
| Shared shell | prototype shell/navigation/header/shared CSS | `src/fitcv_cp/templates/base.html` | shared `fitcvApiRequest`, canonical error handlers | Task 1 removed visible `Lifecycle`, retained direct route, added shared async rendering and duplicate-submit lock, removed duplicate `.global-header` ownership, and removed server-mode navigation gating so both modes render frozen Pipeline and Application groups. Direct TestClient plus Playwright desktop/mobile, dark/light, Escape-focus, and overflow proof pass. Independent validator remains required before closure. | change narrowly | `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_app.py` |
| Pipeline Settings | prototype settings renderer and navigation metadata | `src/fitcv_cp/templates/settings.html` | `src/fitcv_cp/settings_schema.py`, Pipeline settings routes in `src/fitcv_cp/app.py` | Task 2 aligns eyebrow, future-run copy, per-page Restore Defaults, ordered server-open collapsible sections, shared pending/error/retry/stale states, mutation locking, and recoverable revision refresh; browser viewport/theme/dialog checks remain | change narrowly | `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_settings_schema.py`, `tests/test_fitcv_cp/test_app.py` |
| API Providers | `renderApiProvidersPage`, `renderProviderDetailsPage` | `src/fitcv_cp/templates/api_providers.html`, `api_provider_detail.html` | Provider routes/models in `src/fitcv_cp/app.py` and `provider_registry.py` | Task 3 aligns list hierarchy, search, protocol-specific add actions, provider cards, detail hierarchy, credential-safe copy, and shared pending/retry/stale locks; browser validator remains pending by explicit task scope | change narrowly | `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_local_app.py`, `tests/test_fitcv_cp/test_app.py` |
| LLM Configuration | `renderLlmConfigurationPage`, shared task dialog | `src/fitcv_cp/templates/llm_configuration.html` | LLM configuration routes/models in `src/fitcv_cp/app.py` | Task 4 aligns dialog hierarchy, control order, focus return, save-close behavior, mutation lock, and recovery states. Fresh validator PASS; browser proof covers desktop/mobile, missing model, validation, success, stale reload, and retry. | already aligned | `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_local_app.py`, `tests/test_fitcv_cp/test_app.py` |
| Prompt Management | `renderPromptManagementPage`, prompt row and shared prompt dialog | `src/fitcv_cp/templates/prompt_management.html` | Prompt configuration routes/models in `src/fitcv_cp/app.py` | Task 5 aligns fixed section order, shared rows/dialog, task title, focus return, save/reset, mutation lock, and stale/retry states. Fresh validator PASS; browser proof covers desktop/mobile, light/dark, custom save, focus return, and overflow. | already aligned | `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_local_app.py`, `tests/test_fitcv_cp/test_app.py` |
| System / Data Backup | `renderSystemPage` | `src/fitcv_cp/templates/system.html`, `_data_backup_panel.html`, `local_data_backup.html` | System settings routes plus backup/import handlers in `src/fitcv_cp/app.py` and `local_routes.py` | Task 6 uses one shared Data & Backup component, restores prototype section order/default state, removes Move Data drift, and wires revision-safe settings plus backup/import recovery. Fresh validator PASS; desktop/light and mobile/dark evidence show no overflow. | already aligned | `tests/test_fitcv_cp/test_local_routes.py`, `tests/test_fitcv_cp/test_local_app.py`, `tests/test_fitcv_cp/test_app.py` |
| Runs | `renderRunsPage`, `renderRunScanPicker` | `src/fitcv_cp/templates/runs_list.html` | Run routes/models/store/queue | Audit findings `RUN-01` and `RUN-02` fixed: status detail renders, empty bulk actions use inline async state, and existing selection/lifecycle contracts remain intact. | change narrowly | `tests/test_fitcv_cp/test_app.py` |
| Run Details | `renderRunDetails` | `src/fitcv_cp/templates/run_detail.html` and run-detail partials | Run detail/stage/job/event/action routes and artifact contracts | Audit findings `DETAIL-03`, `DETAIL-04`, and `DETAIL-05` fixed: fallback skill sources survive normalization, canonical CV capability keys render, and prototype rating/clear/bookmark geometry is applied. `DETAIL-01` is covered by current URL bootstrap/tests. `DETAIL-02` fixed in the approved follow-up: the profile action follows the prototype's profile-details page transition through the canonical detail route, preserves the Run return path, and removes modal-only behavior. Run Details typography/action values are scoped to the measured prototype values. | change narrowly | `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_run_detail_output_availability.py` |
| Scans | `renderScansPage`, `renderScanDetails`, company picker | `src/fitcv_cp/templates/scans_list.html`, `scan_detail.html` | `src/fitcv_cp/scan_contracts.py`, Scan routes/store/worker | Audit findings `SCN-01` and `SCN-02` fixed: selected Scan IDs/revisions persist through URL pagination, bulk actions submit all selected items, and company search is server-backed beyond the first unsearched page. | change narrowly | `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_scan_contracts.py`, `tests/test_fitcv_cp/test_scan_worker.py` |
| Candidate Profiles | list/upload/review/confirm/detail renderers | Candidate Profile templates and shared sections | Candidate Profile models/routes/service/store and canonical field registry | Audit findings `CP-001` through `CP-004` fixed: processing state renders before polling, derived Source appears for evidence refs, replacement notice appears when undo is available, and invalid upload status receives `.error` styling. | change narrowly | `tests/test_fitcv_cp/test_candidate_profile_service.py`, `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_sqlite_store.py` |
| Bookmarks | `renderBookmarksPage` | `src/fitcv_cp/templates/bookmarks.html` | Bookmark routes and SQLite store | Header/copy, buttons, filters, toolbar, selection layout, table shell, pagination, and loading/network/export failures differ materially; extra Result filter is absent from prototype | change | `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_store.py`, `tests/test_fitcv_cp/test_sqlite_store.py` |
| Synonyms | `renderSynonymsPage`, `renderSynonymDetails` | `src/fitcv_cp/templates/synonyms.html` | Synonym routes, policy IO, SQLite store | Header/actions, section collapsibility, tab counts, editor controls, review columns, detail dialog, default Processing Log state, and async states differ materially | change | `tests/test_fitcv_cp/test_app.py`, Synonym policy/preview/commit tests |
| Preference Optimization | list/detail optimization renderers | `src/fitcv_cp/templates/optimization.html` | Optimization routes/service/settings/store | Main sections, controls, detail, and lifecycle are reusable; empty state is plain row instead of prototype guidance; PRG failures lack shared retry/stale rendering | change narrowly | `tests/test_fitcv_cp/test_optimization_page.py`, `tests/test_inverse_optimization.py`, `tests/test_fitcv_cp/test_sqlite_store.py` |

Gate 0 complete on August 4, 2026. All 13 planned slices have explicit
dispositions. Prototype hash recheck: `8d248d62003b2a8795672daaa221ef5508afdc88`.

## Runs, Scans, and Candidate Profiles parity patch evidence

- Task 1 focused proof: `87 passed`; independent DeepAgents verdict `PASS`.
- Task 2 focused proof: `19 passed`; independent DeepAgents verdict `PASS`.
- Task 3 focused proof: `69 passed`; independent DeepAgents verdict `PASS`.
- Task 3 emitted a Windows temporary SQLite cleanup `PermissionError: [WinError 32]` after tests passed. Treat as test-harness/process cleanup evidence, not product failure, unless reproduced independently.
- Unified current-source fixture runtime: `http://127.0.0.1:59904`; Runs, Scans, and Candidate Profiles all returned HTTP 200.
- Same-fixture counts now match prototype: Runs `4 active / 1 archived`, Scans `5 active / 1 archived`, Candidate Profiles `1 draft / 2 active / 1 archived`.
- Paired browser checks covered desktop, 375px dark mode, effective 200% width via 768px CSS viewport, keyboard focus, computed typography, and horizontal-overflow checks for all three list surfaces. Both source and prototype reported no horizontal overflow; focus rings and accessible roles were present in captured snapshots.
- Network reconciliation on source pages returned HTTP 200 for page and dependent candidate-profile/scan requests. Accessibility snapshots captured equivalent navigation, heading, tab, checkbox, link/button, and status roles for source and prototype pages.
- Computed-style reconciliation: Run Details now scopes `h2` to `font-weight: 700` and page action buttons to `line-height: 20.3px`; remaining cross-surface Run/Scan/Profile ID geometry differences stay explicit and are outside this narrow follow-up.
- Same-fixture evidence remains complete for the available list-page matrix; the approved Run Details follow-up resolves `DETAIL-02` without changing transport or lifecycle contracts.
- The packaged runtime at `http://127.0.0.1:59895` predates the unstaged source fixes. Its rendered output remains non-authoritative for this patch.
- Final independent DeepAgents review before the follow-up: `FAIL`; it correctly identified the prototype hash navigation versus runtime modal mismatch.
- Approved follow-up proof: focused Run Details tests `10 passed`; Run/Candidate Profile app tests `103 passed`; independent DeepAgents validator `PASS` after the navigation/style patch. Windows temporary SQLite cleanup `PermissionError: [WinError 32]` remains a non-product test-harness warning after passing tests.
- Task 4 status: `ACTIVE` because remaining cross-surface Run/Scan/Profile ID geometry is explicitly deferred; the approved Run Details interaction/style follow-up is complete. Planning, template, audit, repository-contract, and diff checks pass. No P0, packaged, Sandbox/VM, or code-signing run is required.

# Candidate Profile Creation Integration

Operation: `getCandidateProfileFieldSchema`, `listCandidateProfiles`, `createCandidateProfileCreationAttempt`, `listCandidateProfileCreationAttempts`, `getCandidateProfileCreationAttempt`, `downloadCandidateProfileSource`, `getCandidateProfileSourceBlock`, `getCandidateProfileBaseline`, `patchCandidateProfileBaseline`, `regenerateCandidateProfileBaseline`, `approveCandidateProfileBaseline`, `getCandidateProfileDerived`, `patchCandidateProfileDerived`, `regenerateCandidateProfileDerived`, `approveCandidateProfileDerived`, `getCandidateProfileConfirmation`, `confirmCandidateProfileCreationAttempt`, `retryCandidateProfileCreationAttempt`, `getCandidateProfile`, `listCandidateProfileRuns`, `archiveCandidateProfile`, `restoreCandidateProfile`, `getLlmConfiguration`, `patchLlmConfiguration`
Contract owner: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md#api-contract`
Canonical field owner: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md#requirement-required-canonical-surface`
State and error owner: `docs/superpowers/specs/2026-08-01-23-49-canonical-candidate-uniform-evidence-projection-spec.md#state-transition-contract` and `#error-contract`
Status: mock-backed frontend approved August 3, 2026; backend Tasks 5-10 authorized against frozen frontend contract

## Candidate Profile Task 1 Contract Freeze

### Prototype-to-server-template parity matrix

| Surface | Prototype contract | Server/template acceptance contract |
| --- | --- | --- |
| Creation fields | Profile name plus source upload | `profile_name` plus one non-empty `profile_file`; canonical fields render from field schema |
| Accepted source formats | Markdown, DOCX, YAML | `.md`, `.docx`, `.yaml`; media type and content validated at boundary; one ingest path |
| Draft/review/resume | Upload processing, Baseline, Controlled Derivation, Confirmation; Save and exit resumes attempt | Attempt resource owns `creation_status`, `revision`, `next_action`, fingerprints, failure, and retry capability |
| Active/Archived views | Candidate Profiles table switches views | `GET /candidate-profiles?view=active|archived`; lifecycle is server-owned and archive/restore controls are capability-gated |
| Detail traceability | Candidate Details shows canonical values and source evidence | Detail returns immutable canonical revision, input metadata, source refs, and source-block IDs; Source uses creation-attempt route |
| Lifecycle controls | Archive, restore, inspect, use for Run | Only `active -> archived` and `archived -> active`; each mutation requires revision CAS; archived profile cannot start Candidate Profile-selected run |
| Related runs | Details exposes related run count and list | `GET /candidate-profiles/{profile_id}/runs`; run rows reference persisted profile revision, not mutable current profile |
| Async states | Processing, retryable error, non-retryable error, stale conflict | Attempt exposes processing lease, failure diagnostics, retry capability, and `409` revision/fingerprint conflicts |

### Frozen revision and trigger rules

- Creation is one staged flow. `converge_candidate_profile_for_runtime()` is sole V1/V2 compatibility adapter; no second adapter.
- Source block request is `GET /candidate-profile-creation-attempts/{attempt_id}/source-blocks/{source_block_id}`. Response `data` contains `source_block_id`, `text`, `kind`, `locator`, `source_document`, and content `checksum`. No profile-level alias.
- Successor revision update input: `expected_revision` CAS plus ordered ID-addressed review operations. Server validates canonical V2, computes canonical checksum, and persists new immutable `profile_revision_id`; prior revision and run snapshots remain unchanged. Response returns `profile_id`, new `profile_revision_id`, `revision`, `checksum`, `lifecycle`, `canonical`, and capabilities.
- Active/archived rules: archive and restore are symmetric successor-revision lifecycle mutations; no in-place confirmed-profile overwrite; active only permits Run selection.
- JSON trigger: historical `POST /runs` JSON body remains compatibility delegate. Managed multipart trigger: `POST /runs` requires active `profile_id`; `/admin/upload-trigger` remains legacy form with separate `candidate_profile_id`. Candidate Profile-selected runs require persisted active profile. Legacy `default_config` is allowed only for explicit legacy requests and is documented/tested as a run with no profile selection; it is not a Candidate Profile-selected run.
- Run input/profile/settings snapshots are persisted once at trigger time. Legacy empty snapshots remain inspectable and render “No immutable ... snapshot”; no parallel snapshot source.


- prototype and shared components: `docs/fitcv-settings-ui-prototype.html`
- field labels, descriptions, controls, requirements, kinds, date grammar, and section order load from `getCandidateProfileFieldSchema`
- Upload, Baseline, Controlled Derivation, Confirmation, Candidate Details, and Candidate Profiles table use one Candidate Profile creation flow
- confirmation and Candidate Details render same server-owned `profile.canonical`; UI keeps no reconstructed baseline/derived copy
- server capabilities own action availability, retryability, stage progression, and disabled reasons

## Prototype Parity Contract

- approved visual and interaction SSOT is `docs/fitcv-settings-ui-prototype.html` blob `989af611bd7767c148022c79ac00c5069d8a3956`; implementation review must verify this blob before comparing mock UI
- prototype owns page headings, section names, section order, default expanded/collapsed state, component classes, visible metadata, and responsive layout; this note maps behavior and transport only and must not restate a competing presentation contract
- canonical field registry owns field inventory, labels, descriptions, requirement state, control shape, evidence kinds, section descriptions, and derived-claim metadata; templates do not copy these lists
- schema shape does not grant editability: stable IDs and provenance remain contextual display, while `origin`, `confidence`, and `support_status` render as derived metadata unless server contract explicitly enables editing
- one shared derived-claim component renders every skill, role family, domain tag, and responsibility theme with editable Name, checkbox evidence refs, metadata chips, server-owned Source/wand actions, Add, and Remove
- one shared baseline collection component hides internal `id` and `source_refs` controls, displays IDs in entry headings, and renders nested evidence through same evidence component
- regression checks assert required structures and forbidden fallbacks; text-presence assertions alone do not prove prototype parity
## State Ownership

- URL owns attempt ID and stage route: upload, baseline, derived, or confirmation
- server owns attempt status, revision, fingerprints, drafts, approvals, validation, failure, capabilities, confirmation payload, Candidate Profile revision, and lifecycle
- component-local state owns selected upload before submit, unsaved form batch, open Source dialog, pending request ID, and focus restoration
- Profile Name is submitted during Upload and read-only afterward; candidate Full name remains `profile.canonical.name`

## Upload

- form requires Profile Name and one `.md`, `.docx`, or `.yaml` file; one shared control and validation path handles every format
- submitting locks Profile Name, file control, and primary action; duplicate submit reuses same idempotency key
- `202` navigates to attempt baseline route and shows processing state while polling `getCandidateProfileCreationAttempt`
- unsupported, unsafe, corrupt, empty, mismatched, or oversized file errors remain on Upload with selected filename and Profile Name preserved where browser security permits
- Save and exit after attempt creation flushes pending review batch, then returns to Candidate Profiles without creating a profile revision

## Baseline Review

- loading keeps page heading, stepper, source action, and footer visible; field regions use skeletons
- processing preserves last valid draft read-only and shows server stage; no client-estimated completion percentage
- fields and repeatable collections render from canonical field metadata and draft `document`; annotations drive Source, warning, and regeneration affordances
- `i` opens field description; `Source` opens dialog backed by exact `source_block_id`; View Source uses original source operation
- user edits accumulate locally and persist as one ordered review batch on blur, collection action, stage navigation, Save and exit, or approval; never send one mutation per keystroke
- Add, edit, and remove use same ID-addressed operation grammar for experiences, education, projects, achievements, certifications, volunteering, and nested evidence
- Regenerate all sends `targets: ["*"]`; field wand sends one path. UI shows wand only when annotation says `regenerable: true`
- stale revision preserves unsaved operations, reloads server draft, highlights conflicts, and requires explicit reapply or discard
- Approve flushes pending edits first, then submits returned revision and fingerprint; success shows derivation processing

## Controlled Derivation

- Skills, role families, domain tags, and responsibility themes use same repeatable claim component
- each claim has stable ID, value, origin, confidence, and editable `evidence_refs`; Source opens evidence-resolution dialog without side inspector
- Add, edit, remove, regenerate all, regenerate one, stale recovery, and approval follow same baseline interaction contract
- unsupported user claims stay visible with clear unsupported state; backend capability decides whether claim can affect pipeline
- navigating back and editing baseline accepts full derived invalidation; UI does not retain a hidden client copy

## Confirmation

- request `getCandidateProfileConfirmation`; do not assemble confirmation from local baseline and derived state
- render restored prototype structure in order: Confirmation Overview, Source Input, Approval Status, Baseline Facts, and Derived Claims
- reuse shared section-card, baseline-preview, and derived-preview renderers used by Candidate Details; checksums, source-document IDs, parser provenance, and LLM provenance remain non-visual
- primary action stays disabled while request is pending, fingerprints are stale, validation blocks readiness, or capability denies confirmation
- confirmation uses one idempotency key; duplicate clicks remain locked until stored result returns
- success navigates to returned Candidate Profile details; details render returned `profile.canonical` unchanged
- persistence failure keeps confirmation visible, shows retry action, and never adds table row optimistically

## Candidate Profiles and Details

- table lists only confirmed Candidate Profiles as pipeline resources; resumable attempts use creation-attempt query and are visually distinct from profiles
- list rows, status, lifecycle, and capabilities come from server summaries; UI does not infer `use_for_run`
- details load `getCandidateProfile`; every confirmed field comes from `profile.canonical`, while Profile Name, Candidate Profile ID, source input, lifecycle, capabilities, and Related Runs come from resource metadata
- render restored prototype structure in order: Profile Overview, Source Input, Baseline Facts, Derived Claims, collapsed Traceability, and collapsed Related Runs; integrity checksums and parser/LLM provenance remain transport/persistence fields only
- archive and restore reconcile returned resource and preserve immutable `profile.canonical`
- archived selection uses server `capabilities.delete`; permanent delete requires current revision and idempotency key, rejects related Runs, and removes linked creation artifacts atomically
- failed attempts link back to owning stage or retry action; they never appear selectable in Run creation

## Resolved Candidate Profile Transport Decisions

- archived selection calls `POST /candidate-profiles/{profile_id}/actions/delete`; server permits only archived succeeded profiles with no Run reference through either profile or profile-revision FK. The deletion receipt is idempotent and linked creation artifacts are permanently removed.
- `Undo regeneration` calls stage-specific `undo-regeneration`. Server restores only snapshot retained immediately before latest regeneration, uses expected-revision CAS plus idempotency, invalidates downstream approvals, and advertises `undo_regeneration` only while restore remains valid.

## Errors and Recovery

- validation: map `field_errors[].field` to canonical ID-addressed controls; keep page-level summary and first-error focus
- stale revision or fingerprint: preserve local changes, fetch current stage, and require explicit reconciliation
- invalid transition: replace local attempt metadata with response `data`, navigate only when server `next_action` changes
- retryable processing or LLM error: retain last valid draft and expose server retry capability
- non-retryable source error: retain attempt diagnostics and offer new Upload; do not fake retry
- already confirmed: open returned/existing Candidate Profile rather than creating another row

## Accessibility and Responsive Behavior

- use native file input, buttons, links, labels, selects, dialogs, and fieldsets; repeatable entries expose clear group names and remove confirmations
- processing and save status use polite live regions; errors use assertive summary without repeatedly announcing unchanged polling state
- Source and `i` controls have distinct accessible names; dialog returns focus to invoking control
- stepper exposes current step, completed steps, and blocked navigation without color-only meaning
- footer actions wrap in source order without overlap; content remains visible at 200% zoom and narrow width
- long field names, values, evidence refs, filenames, and localized copy wrap without truncation
- preserve visible focus, keyboard order, supported themes, reduced motion, and existing contrast tokens

## Required Evidence

Prior mock approval evidence from August 2, 2026 is invalidated. Required parity work:

- [x] field-schema regression covers canonical evidence kinds, optional title, complete help descriptions, `support_status`, section descriptions, and shared derived shape
- [x] exact markup regression covers prototype DOM hierarchy, classes, action order, button variants, and hidden internal controls
- [x] one deterministic fixture supplies prototype and runtime mock values, IDs, selected refs, and capabilities
- [x] browser flow covers Candidate Profiles, Upload, Baseline, Controlled Derivation, Confirmation, Candidate Details, and LLM Configuration
- [x] desktop, 375px, effective 200% width, dark theme, Source dialog focus return, long evidence labels, computed high-risk styles, screenshots, and zero console warnings pass
- [x] independent verifier reports `Spec compliance: PASS` and `UI parity quality: APPROVED` against prototype blob `989af611bd7767c148022c79ac00c5069d8a3956`
- [x] exact presentation projections cover Source excerpt/locator values, validated-model copy, evidence-kind labels, derived origin labels, and confirmation date labels without changing canonical raw values
- [x] user approved corrected mock UI on August 3, 2026 before backend Tasks 5-10

- backend contract tests cover upload safety, all three formats, ID-addressed mutations, regeneration targets, approvals, invalidation, errors, idempotency, and exact confirmation/detail canonical equality
- store tests cover migration idempotency, immutable source/snapshots/revisions, review batches, concurrency, transaction rollback, one revision per confirmation, archive symmetry, and Run eligibility
- frontend state tests cover processing, field and collection edits, Source dialogs, regenerable capabilities, stale reconciliation, upstream invalidation, confirmation retry, and exact Candidate Details rendering
- Playwright flow covers MD, DOCX, and YAML creation; multiple entries; per-field and all regeneration; evidence-ref editing; Save and exit/resume; stale conflict; confirmation; details; archive/restore; keyboard and narrow layout
- Chrome DevTools evidence confirms operation payloads, status codes, no duplicate submissions, no console errors, and no layout shift across processing and error states
