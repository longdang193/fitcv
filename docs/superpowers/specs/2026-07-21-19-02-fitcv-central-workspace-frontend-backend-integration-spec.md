---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-central-workspace-frontend-backend-integration
targets:
  - docs/fitcv-settings-ui-prototype.html
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/synonym_proposals.py
  - src/fitcv_cp/synonym_policy_io.py
  - tests/test_fitcv_cp
related_features:
  - trigger_run_management
  - settings_system
  - admin_control_plane_core
  - enrichment
related_stages:
  - enrichment
  - screening
  - shortlisting
  - ranking
  - cv-analysis
  - cv-generation
---

# FitCV Central Workspace Frontend-Backend Integration Specification

## Authority and Supersession

- This specification owns central Candidate Profiles, Bookmarks, Synonyms, and their cross-page contracts.
- `docs/superpowers/specs/2026-07-20-18-23-fitcv-prototype-backend-compatibility-spec.md` remains authoritative for Runs, Run Details, pipeline results, CVs, Console, and diagnostics except where this specification changes profile, bookmark, Run Details export-selection, synonym-revision, or Run-deletion behavior.
- `docs/fitcv-settings-ui-prototype.html` owns approved visible hierarchy, labels, interaction intent, and responsive behavior. This specification supersedes its prototype-only single-YAML synonym backup transport with the approved ZIP contract.
- `docs/fitcv-settings-ui-prototype.integration.md` is temporary UI intent and is removed after this durable specification is implemented and verified.
- Source, tests, and generated OpenAPI become runtime truth after implementation.

## Goal and Problem

### Problem

- Candidate Profiles, Bookmarks, and Synonyms exist as prototype-wide concepts, but backend ownership remains fragmented or incomplete.
- Trigger Run can select profiles, but profiles have no create/detail/archive contract and failed imports cannot be represented safely.
- Run Details writes normalized `bookmarks`, while `/admin/bookmarks` reads legacy `bookmarked_jobs`, creating two owners for one fact.
- Synonym review is Run-scoped, proposal identity is not concept-level, Deferred remains exposed, and approved mapping application and promotion use separate settings and actions.
- Run input captures profile and settings revisions but not the synonym policy revision required for reproducibility.
- Current export routes cannot prove the intersection of explicit selection, stage, result filter, and search.

### Goal

- Provide one local-workspace contract for central Candidate Profiles, Bookmarks, and Synonyms without adding a second persistence owner or new frontend framework.
- Make cross-page relationships explicit: profiles feed Trigger Run; Runs own run-job bookmarks; synonym suggestions aggregate across Runs; each Run captures immutable profile, pipeline-settings, and synonym-policy revisions.
- Preserve approved behavior across loading, empty, error, stale, conflict, retry, disabled, and duplicate-submit states.

## Required Outcomes

- Candidate Profiles become durable attempt/revision resources and the only source for Trigger Run profile selection.
- Bookmarks use one Run-owned normalized record and one shared job projection across Run Details and the central page.
- Synonym policy, review, backup, processing history, and Pipeline Settings use one SQLite-owned contract.
- Unsafe operations enforce the local security, revision, idempotency, validation, and failure semantics defined below.
- Production UI and OpenAPI expose the same states, actions, and cross-page relationships described by this specification.

## Design Analysis

- Current-state evidence and consequences are recorded in `Goal and Problem`.
- Included boundaries and exclusions are recorded in `Scope` and `Contract Ownership`.
- Detailed resource, route, persistence, UI, security, compatibility, and failure contracts are authoritative in the integration sections below.

## Design Decisions

- The approved decisions below resolve ownership, lifecycle, cutover, aggregation, backup, and synonym-activation semantics.
- `Fresh Cutover and Compatibility` owns migration and rollback boundaries; implementation must not invent dual-read or legacy migration behavior.

## Approved Product Decisions

1. Deployment is one local workspace bound to loopback. No user, tenant, or workspace ownership model is added.
2. Accepted `.yaml` imports that fail parsing or profile validation remain visible as failed Candidate Profile rows.
3. Bookmark has no Submitted status or independent lifecycle status.
4. Permanent Run deletion deletes every bookmark sourced from that Run. No orphan bookmark snapshot survives.
5. Synonym review uses one aggregated alias/canonical row across source Runs.
6. Approved-synonym use has one canonical Pipeline setting. Separate apply/promote settings and actions retire.
7. Synonym backup is a ZIP containing three canonical YAML policy files and a validation manifest.
8. Cutover uses a backed-up fresh database. No legacy row migration, backfill, or dual-read is required.
9. A human-accepted invalid mapping remains `review_status=approved` with `policy_effect=blocked` until policy validation succeeds.
10. Run deletion removes source associations; zero-source Pending and Declined suggestions disappear, while Approved decisions remain.

## Scope

### Included

- Candidate Profile create, list, detail, archive, restore, failed-attempt visibility, related-Run links, and Trigger Run selection.
- Central Bookmark list, pipeline-stage tabs, search, result filtering, pagination, selection, batch removal, export preview, and export.
- Shared Run Details and Bookmark export-selection semantics.
- Run deletion preview, confirmation counts, transactional bookmark cascade, and deletion summary.
- Central Synonym editor, validation issues, aggregated review queue, batch actions, source evidence, processing log, backup import/export, and Pipeline Settings linkage.
- SQLite ownership, route models, OpenAPI exposure, local security, stable errors, revision checks, idempotency, frontend states, and verification.

### Non-Goals

- Multi-user authentication, remote deployment, tenant isolation, or external CORS support.
- Candidate Profile editing, replacement, or deletion. Changed profile content creates a new profile.
- Preserving bookmarks after permanent Run deletion.
- Reintroducing a Synonym section inside Run Details.
- A separate Promote Approved Synonyms action, state, setting, or route.
- A generated frontend API client before route models and OpenAPI stabilize.
- A frontend framework migration or new component library.
- Parsing canonical YAML or ZIP backup contents in browser code.

## Contract Ownership

| Concern | Canonical owner | Consumers | Constraint |
|---|---|---|---|
| Profile import attempt and lifecycle | normalized Candidate Profile tables | Candidate Profiles, Trigger Run, Run Details | failed and succeeded attempts share one resource contract |
| Profile content revision | immutable successful profile revision | Run trigger and historical Run Details | failed rows never own parsed candidate data |
| Run/profile/settings/synonym snapshot | `run_inputs` | Runs and pipeline workers | profile, settings, and synonym bundle revisions resolve in one Run-create transaction |
| Bookmark fact | normalized `bookmarks` keyed by `run_job_id` | Run Details and Bookmarks | legacy `bookmarked_jobs` cannot remain a read/write owner |
| Job display columns | shared Run job projection | Run Details, Bookmarks, CSV export | Bookmarks adds Run fields; it does not fork job fields |
| Synonym active policy | three canonical taxonomy YAML files plus immutable bundle revisions | pipeline, Synonym editor, historical Runs | every active file set resolves to one reproducible bundle snapshot |
| Synonym review lifecycle | normalized concept-level review rows and source evidence | Synonyms page | statuses are Pending, Approved, Declined only |
| Synonym processing history | canonical backend processing records | Processing Summary Log | Clear is view state only |
| Pipeline setting definitions | settings schema/store | Pipeline Settings and Run snapshot | one approved-synonym setting owns use and activation policy |
| Visible UI behavior | approved prototype and sidecar | production templates and tests | shared controls and tokens prevent page-specific drift |

## Cross-Cutting Integration Contract

### Local Workspace Security

- Server listens on `127.0.0.1`; requests with a non-loopback Host are rejected.
- Unsafe methods require same-origin `Origin` or `Referer` validation and existing CSRF token contract.
- JSON clients and multipart forms use one canonical CSRF mechanism.
- No route accepts filesystem paths from browser. Uploaded filename is basename-sanitized.
- Logs, errors, resources, and backups exclude secrets, absolute local paths, credentials, and unredacted provider payloads.
- No `user_id`, `tenant_id`, or `workspace_id` columns or authorization filters are introduced.

### Resource and Error Envelopes

- Single-resource success: `{ "data": <resource>, "meta": {...} }`.
- Collection success: `{ "data": [...], "page": { "number": 1, "size": 20, "total_items": 0, "total_pages": 0 }, "meta": {...} }`.
- Failure: `{ "error": { "code": "...", "message": "...", "field_errors": [], "retryable": false }, "meta": {...} }`.
- `404` means missing resource. `409` means state or revision conflict. `422` means invalid content/filter. `413` means upload too large.
- Stable machine codes own frontend branching; visible copy may change.

### Revisions, Idempotency, and Concurrency

- Mutable resources expose opaque `revision` values.
- Replacement or transition writes include `expected_revision`; stale writes return `409 revision_conflict` with current revision metadata.
- Candidate Profile create, archive/restore, policy save, synonym batch actions, backup import, bookmark removal/export, and Run deletion require `Idempotency-Key`. Same key and payload returns original result; changed payload returns `409 idempotency_conflict`.
- Pending controls disable duplicate submission, preserve user input on recoverable errors, and restore focus to initiating control or first actionable error.

### OpenAPI and Frontend Transport

- Every JSON request and response uses explicit Pydantic models. Public contracts do not rely on untyped `dict` return annotations.
- `POST /candidate-profiles` exposes multipart fields and `.yaml` requirements in runtime OpenAPI.
- ZIP and CSV routes declare media type, filename, and error responses.
- Production templates use one shared request helper for envelope parsing, CSRF, timeout, cancellation, error mapping, and revisions.
- Generated frontend client remains deferred. OpenAPI snapshot tests guard drift.

### URL and UI State

- URL hash/path identifies page. Query parameters own navigable tabs, search, result filter, and page.
- Candidate Profiles: `view=active|archived`, `search`, `page`.
- Bookmarks: `stage`, `result`, `search`, `page`.
- Synonyms: `type=skills|domain|role-family`, `review_status=pending|approved|declined`, `review_search`, `review_page`.
- Selection, open dialog/drawer, unsaved editor text, and cleared log view remain local state.
- Filter changes clear or prune selections outside active server query.

## Candidate Profile Integration

### Resource Model

`CandidateProfileSummary` contains:

- `profile_id`: opaque immutable server-generated ID.
- `profile_name`: optional operator label; duplicate names are allowed.
- `display_name`: server projection using `profile_name`, safe filename stem, then `Unnamed profile`.
- `original_filename`: sanitized basename ending in `.yaml`.
- `creation_status`: `succeeded | failed`.
- `lifecycle`: `active | archived`; failed profiles remain Active and cannot be archived.
- `created_at`, `updated_at`, optional `archived_at`: RFC 3339 UTC.
- `profile_revision_id`: immutable revision ID for succeeded rows, otherwise `null`.
- `failure`: `null` or `{ code, message }`; no raw YAML, stack trace, or absolute path.
- `related_run_count`, capabilities `{ inspect, archive, restore, use_for_run }`, and mutable row `revision`.

`CandidateProfileDetail` extends summary with:

- `overview`: bounded parsed candidate projection only for succeeded rows.
- `related_runs`: newest bounded Run links plus total count.
- `input`: filename, checksum, byte length, and media type; raw upload is not returned.

### Persistence

- `candidate_profiles` owns attempt identity, optional name, safe file metadata, status, lifecycle, failure summary, timestamps, and row revision.
- `candidate_profile_revisions` owns immutable validated candidate JSON, checksum, schema revision, and creation time. It references `candidate_profiles` with `ON DELETE RESTRICT` because profile deletion is unsupported.
- Profile name is not unique. `profile_id` is selector identity.
- Failed rows have no revision row and no parsed candidate JSON.
- Fresh initialization seeds existing configured profiles as succeeded active rows with one immutable revision each.

### Routes

| Method and route | Request | Response | Required behavior |
|---|---|---|---|
| `GET /candidate-profiles` | `view`, `status`, `search`, `page`, `page_size`, `sort` | Candidate Profile collection | server filtering and stable `created_desc` order |
| `POST /candidate-profiles` | multipart `profile_file`, optional `profile_name`; `Idempotency-Key` | `201 CandidateProfileDetail` | accepts `.yaml` only; persists succeeded or post-admission failed attempt |
| `GET /candidate-profiles/{profile_id}` | none | `CandidateProfileDetail` | includes failure or overview, never both |
| `GET /candidate-profiles/{profile_id}/runs` | page query | Run link collection | historical Runs remain resolvable after archive |
| `POST /candidate-profiles/{profile_id}/actions/archive` | `expected_revision` | refreshed summary | succeeded active profiles only |
| `POST /candidate-profiles/{profile_id}/actions/restore` | `expected_revision` | refreshed summary | succeeded archived profiles only |

### Import Boundary

- Browser input uses `accept=".yaml,application/yaml,text/yaml"`; backend enforces `.yaml` case-insensitively.
- Missing file, wrong extension, zero-byte input, and oversized input fail before attempt admission and do not create a row.
- Once extension and size checks pass, YAML parse, schema, canonicalization, or candidate validation failure creates a failed row and returns `201` with `creation_status=failed`.
- Unexpected failure before durable row creation returns `500 profile_import_unavailable`; unexpected failure after admission updates that row to Failed before returning.
- Profile Name trims whitespace; blank becomes `null`; length is bounded to 120 Unicode characters.

### Trigger Run Dependency

- Opening Trigger Run refreshes `GET /candidate-profiles?view=active&status=succeeded`.
- Selector contains only `capabilities.use_for_run=true` resources and labels each option `{display_name} - {profile_id}`.
- Empty state links to Candidate Profiles. Retrieval failure offers Retry without clearing jobs file or Run Name.
- `POST /runs` submits `profile_id`, never free-text profile data.
- Run creation validates Active + Succeeded state, then atomically captures `profile_revision_id`, `pipeline_settings_revision_id`, and `synonym_policy_bundle_revision_id` in `run_inputs` before enqueue.
- A profile archived between dialog load and submit returns `409 candidate_profile_unavailable`; frontend refreshes options and preserves other fields.
- Run Details links to profile. Archived profiles remain inspectable for history.

### UI States and Actions

- Active tab shows active succeeded profiles and failed attempts. Archived tab shows archived succeeded profiles only.
- Failed status opens detail with actionable failure reason and never exposes Profile Overview derived from invalid content.
- Archive and Restore never delete profile data or historical Run links.
- No delete action appears in first release.

## Bookmark Integration

### Identity and Persistence

- `bookmarks` is sole bookmark owner.
- Each row contains `bookmark_id`, non-null `run_id`, non-null `run_job_id`, `created_at`, and `updated_at`.
- `run_job_id` is unique; same source job in two Runs can have two bookmarks.
- Foreign keys use `ON DELETE CASCADE` from Run and Run Job. No display snapshot, nullable source reference, orphan mode, status, Submitted time, or archive time is stored.
- Fresh cutover creates normalized `bookmarks` only. Legacy `bookmarked_jobs` remains in backed-up old database files and is never dual-read or dual-written.

### Shared Job Projection

- One backend builder owns `JobResultSummary` for Run Details, Bookmarks, and export.
- Bookmark rows add `bookmark_id`, `run_id`, `run_name`, `run_lifecycle`, and `bookmarked_at` to shared projection.
- Pipeline stage, result, title, company, location, work mode, skills, outcome, reason, CV, and capabilities are not separately reformatted.
- Source Run lifecycle is derived. Bookmark has no lifecycle status.

### Routes

| Method and route | Request | Response | Required behavior |
|---|---|---|---|
| `GET /bookmarks` | `stage`, `result`, `search`, `page`, `page_size`, `sort` | Bookmark collection | joins normalized Runs/jobs; totals cover full filtered set |
| `POST /bookmarks/actions/remove` | selection context; `Idempotency-Key` | removal summary | removes only server-recomputed intersection |
| `POST /bookmarks/actions/export/preview` | selection context | export summary | returns count and normalized filters, no file |
| `POST /bookmarks/actions/export` | selection context + preview revision; `Idempotency-Key` | CSV stream | recomputes intersection; stale preview returns `409` |
| `POST /runs/{run_id}/jobs/actions/export/preview` | Run selection context | export summary | same selection algorithm scoped to one Run |
| `POST /runs/{run_id}/jobs/actions/export` | selection context + preview revision; `Idempotency-Key` | CSV stream | replaces page-only or filter-only semantics |

`SelectionContext` contains:

```json
{
  "selected_run_job_ids": ["..."],
  "stage": "ranking",
  "result": "passed",
  "search": "data"
}
```

- Export and batch removal target `selected_run_job_ids intersect stage intersect result intersect search` as recomputed by server.
- Empty selection returns `422 selection_required`. IDs outside current query are reported as excluded, never acted on silently.
- Preview returns selected, matched, excluded, format counts, opaque `preview_revision`, and `expires_at`. Confirmation copy uses matched count.
- Export submits unchanged selection context plus `preview_revision`. Server rechecks context; expired or changed matching identity returns `409 export_selection_changed` with a replacement summary.
- One export registry owns CSV columns. Bookmarks prepends Run ID and Run Name to Run Details columns.

### Run Deletion

- `POST /runs/actions/delete-archived/preview` accepts explicit Run IDs and returns Run count, bookmark count, blocked active IDs, missing IDs, opaque `preview_revision`, and `expires_at`.
- Confirmation text is `Deleting this run will also remove N bookmarked jobs.` or plural Run equivalent.
- `POST /runs/actions/delete-archived` submits the same Run IDs plus `preview_revision`, remains all-or-nothing, requires `Idempotency-Key`, and returns exact `runs_deleted` and `bookmarks_deleted` counts.
- Active, missing, expired-preview, or changed Run state blocks whole batch with `409 delete_preview_stale`. No submitted ID is ignored.
- Run, run-job, and bookmark rows delete in one SQLite transaction. Filesystem cleanup failure is reported separately.

### UI Behavior

- Pipeline-stage tabs, search, result filter, selection toolbar, table shell, pagination, and internal horizontal scrolling reuse Run Details patterns and tokens.
- Page-level horizontal overflow is forbidden. Table scrolls inside parent shell.
- Remove Bookmark confirmation states matched count. Success prunes rows and selection without full-page reset.
- Bookmark links open matching Run Details and job context. Run deletion cannot leave dead bookmark links.

## Synonym Integration

### Types and Canonical Files

| UI type | Canonical file | Editable mapping root |
|---|---|---|
| Skills | `config/taxonomy/skill_synonyms.yaml` | `skill_synonyms` |
| Domain | `config/taxonomy/domain_synonyms.yaml` | `domain_alias_map` |
| Role Family | `config/taxonomy/role_family_synonyms.yaml` | `role_family_alias_map` |

- Editor exposes only configured alias-to-canonical mapping root through one shared editor component.
- Backend reads and writes mapping root while preserving non-editor-owned document sections. `domain_neighbors` is not editable here.
- Browser never receives repository paths and never parses or rewrites canonical YAML files.

### Immutable Bundle Revision

- Every valid editor save, successful Approve activation, or successful backup import creates one immutable `SynonymPolicyBundleRevision` covering Skills, Domain, and Role Family together.
- Bundle contains `bundle_revision_id`, parent revision, normalized mapping snapshot for all three types, per-type revision IDs, per-file SHA-256 values, source operation, and creation time.
- Active bundle pointer and all changed canonical YAML files switch atomically. A failed switch leaves previous pointer and files active.
- `run_inputs` stores `synonym_policy_bundle_revision_id`, bundle checksum, and immutable normalized bundle snapshot so historical Run behavior remains resolvable without current files.

### Policy Resource and Validation

`SynonymPolicyResource` contains type, editor text, active type revision, active bundle revision, draft revision, validation status, issues, timestamps, and edit capability.

- Editor text uses one `alias: canonical` mapping per line. Blank lines and comments are allowed.
- Empty alias, missing canonical, list-item syntax using `-`, duplicate alias with different canonicals, normalized alias conflicts, and canonical cycles are invalid.
- Each issue contains stable code, message, severity, affected line numbers, aliases, and canonicals.
- Summary copy uses `No conflicts detected`, singular, or plural counts. Count buttons focus and scroll to affected lines.
- Invalid drafts persist as inactive drafts. Last valid active revision remains pipeline truth.
- Save uses compare-and-swap against draft revision. Valid draft activates atomically; invalid draft returns `422 synonym_policy_invalid` with persisted draft and issues.

### Review Identity and Aggregation

- Canonical review identity is `(synonym_type, normalized_alias, normalized_canonical)`.
- One review row aggregates all source Runs and evidence for that concept. Run ID is not part of concept identity.
- `review_status` is `pending | approved | declined`. Legacy `deferred` maps to Pending at ingestion boundary and never enters new storage or public enums.
- `policy_effect` is `active | blocked | absent`: Active means current bundle uses exact mapping; Blocked means accepted mapping exists in invalid draft; Absent means no active or blocked mapping exists.
- Source associations store Run ID, source proposal reference, evidence summary, first seen, and last seen. Evidence contains supporting signals only; source Run metadata belongs to Suggestion Overview.
- Run deletion cascades source associations. Zero-source Pending and Declined rows delete in same transaction. Approved rows remain as decision history with source count zero.
- Reused proposal analysis may add source evidence to same concept row. It never copies Approve or Decline decisions.
- Proposal ingestion suppresses exact Active mappings and attaches repeated Blocked mappings to existing Approved concept rows rather than creating new Pending rows.
- With Auto-accept off, every new concept enters Pending.

### Review Actions

- Pending supports Approve, Decline, and Clear.
- Approved supports Clear only.
- Declined supports Approve and Clear.
- Batch selection is constrained to current synonym type. Mixed-type action requests return `422 mixed_synonym_types`.
- Approve transactionally records decisions, merges selected mappings into affected policy draft, validates resulting type policy, and attempts atomic activation.
- Valid activation sets `review_status=approved`, `policy_effect=active`, creates one bundle revision, and increments `successfully_added` for mappings newly active.
- Invalid activation sets `review_status=approved`, `policy_effect=blocked`, preserves invalid draft/issues, does not increment blocked mappings, and keeps previous active bundle.
- Suggestion Overview shows `Approved - Blocked by policy validation` with links to editor issues. Review table needs no Conflict column.
- Saving a corrected valid draft creates a bundle revision and changes matching Approved rows from Blocked to Active without another review decision.
- Decline changes review status only. It does not edit active or draft policy.
- Clear removes selected review rows and source evidence only. Active or blocked policy mappings remain in active policy or draft and do not re-enter review as duplicates.
- Clear confirmation is `Remove the selected entries from the review queue? Approved synonyms will remain active.`

### Routes

| Method and route | Request | Response | Required behavior |
|---|---|---|---|
| `GET /synonym-policies/{type}` | none | policy resource | returns active and current draft state |
| `PUT /synonym-policies/{type}` | editor text, `expected_revision`; `Idempotency-Key` | valid policy or persisted invalid draft | mapping-root replacement with atomic validation |
| `GET /synonym-suggestions` | `type`, `status`, `search`, `page`, `page_size`, `sort` | aggregated review collection | one concept row across Runs |
| `GET /synonym-suggestions/{suggestion_id}` | none | overview and paged source evidence | source Run links resolve while Run exists |
| `POST /synonym-suggestions/actions/approve` | IDs, expected draft revision, expected active bundle revision; `Idempotency-Key` | action summary + issue summaries | validates after draft merge; no promote call |
| `POST /synonym-suggestions/actions/decline` | IDs; `Idempotency-Key` | action summary | Pending rows only |
| `POST /synonym-suggestions/actions/clear` | IDs; `Idempotency-Key` | action summary | review-only removal |
| `GET /synonym-processing-runs` | page query | processing summary collection | canonical history, newest first |
| `GET /synonym-backups/export.zip` | none | ZIP stream | server-created canonical backup |
| `POST /synonym-backups/import` | multipart ZIP, expected active bundle revision; `Idempotency-Key` | import/validation summary | validates all files before atomic replacement |

### Processing Summary Log

- Each record includes processed time, total processed, approved, declined, pending, successfully added, source operation, and issue count.
- Counts come from one completed backend operation, not independent browser recomputation.
- Clear hides loaded records locally. Reload restores canonical history.
- Backend retention is bounded by backend policy, not Clear button.

### Backup Contract

- Export ZIP contains `skill_synonyms.yaml`, `domain_synonyms.yaml`, `role_family_synonyms.yaml`, and `manifest.json`.
- Manifest contains schema version, active bundle revision, active revision per type, SHA-256 per YAML member, and RFC 3339 export time.
- Import rejects absolute paths, `..` traversal, symlinks, duplicate members, unexpected members, missing YAML members, oversized archive/member, invalid UTF-8, invalid YAML, invalid root shape, conflicts, and cycles.
- Import parses and validates all three documents before replacing any active file or revision. Partial replacement is forbidden.
- Import uses temporary files, checksum verification, atomic rename, and rollback to previous active files if activation fails.
- UI uploads/downloads opaque ZIP bytes and renders server summaries only.

### Pipeline Settings Contract

- New canonical setting: `synonym_management.apply_approved_enabled`.
- New canonical setting: `synonym_management.auto_accept_suggestions_enabled`.
- Meaning: approved mappings may activate after successful validation and active approved mappings are used by future Runs.
- `apply_approved_enabled` defaults to `true`; `auto_accept_suggestions_enabled` defaults to `false`, matching approved prototype intent.
- `synonym_management.apply_to_run_enabled`, `synonym_management.promote_global_enabled`, `synonym_management.auto_apply_recommendation_enabled`, and `synonym_management.auto_promote_global_enabled` retire from public schema and UI.
- Fresh reset performs no value migration from retired keys. Old values remain only in backed-up old database files.
- Existing `synonym_management.auto_accept_ai_action_enabled` remains unchanged and outside this UI contract; it controls CV review artifact terminalization, not synonym suggestions.
- Auto-accept suggestions controls queue entry only. When off, every suggestion enters Pending.
- Pipeline Automation & Reuse links to `#synonyms` and does not duplicate policy-edit controls.

### Run Reproducibility

- Every new Run stores `synonym_policy_bundle_revision_id`, bundle checksum, and immutable normalized bundle snapshot beside profile and pipeline-settings revisions.
- Pipeline resolves only active validated policy. Invalid drafts and blocked approved mappings are excluded.
- Completed Runs retain captured bundle identity and content after edits, approvals, imports, or settings changes.

## Frontend Component and Interaction Rules

- Reuse existing section cards, tabs, filter bars, action toolbars, table shells, status badges, dialogs, drawers, notifications, console surfaces, and design tokens.
- Similar controls keep same padding, gap, height, alignment, wrapping, hover, focus, disabled, loading, and destructive-action treatment.
- Primary color is reserved for primary actions and navigation. Equivalent links use same variant when consequence and hierarchy match.
- Tables use semantic markup, keyboard-reachable actions, and internal horizontal scrolling.
- Tabs expose selected state, `aria-selected`, keyboard focus, and URL synchronization.
- Dialogs and drawers trap focus, close on Escape when safe, restore initiating focus, and protect unsaved editor changes.
- Loading preserves layout. Empty states distinguish no data from filtered no-results.
- Failed requests preserve last safe data with stale/retry messaging where possible. Destructive success reports exact counts.
- Affected flows meet WCAG 2.2 AA intent: keyboard operation, visible focus, accessible names/descriptions, non-color status cues, contrast, zoom/reflow, reduced motion, and light/dark parity.
- Narrow layouts may stack controls, but order stays filters, selection actions, table, pagination. Page-level horizontal scrolling is not accepted.

## Data Safety and Failure Semantics

- Server validates files regardless of browser `accept` hints.
- Profile failure rows contain safe summaries only; invalid YAML never reaches pipeline snapshots.
- Run deletion is transactional for database ownership and returns exact bookmark loss before and after confirmation.
- Bookmark export/removal use server-recomputed intersections to prevent hidden or stale selection acting on unintended rows.
- Synonym invalid drafts never replace active policy. Backup import never partially replaces taxonomy files.
- Approve, policy save, import, archive/restore, Run delete, export, and batch removal are idempotent under documented keys.
- Responses after uncertain writes include enough resource/action identity for frontend reconciliation before retry.

## Invariants and Edge Cases

- SQLite is the runtime SSOT; YAML files are repaired mirrors and cannot override the active synonym bundle implicitly.
- IDs, revisions, checksums, and concept keys remain stable under retries, duplicate names, aggregation across Runs, and page refresh.
- Empty, malformed, unsupported, oversized, stale, duplicate, cyclic, conflicting, missing-source, and partial-failure cases follow the route-specific contracts above.
- Approved invalid synonym mappings remain Approved + Blocked; zero-source Pending and Declined suggestions are deleted with their final source Run.
- Permanent Run deletion removes its bookmarks and source associations; no orphan bookmark snapshot survives.
- Fresh cutover rejects incompatible schemas while preserving timestamped DB, WAL, and SHM backups.

## Fresh Cutover and Compatibility

1. Refuse incompatible old schema and move old DB, WAL, and SHM files to timestamped backup.
2. Initialize fresh profile attempt/revision, bookmark, synonym review, policy draft/bundle revision, processing-history, and idempotency tables transactionally.
3. Seed Candidate Profiles from current validated profile configuration and create one immutable revision per seed.
4. Validate three canonical synonym YAML files and create initial active bundle revision before accepting Runs.
5. Initialize new settings schema with approved defaults; do not import retired setting rows.
6. Start with empty Runs, bookmarks, and synonym review queue. No legacy row migration, backfill, or dual-read occurs.
7. Expose typed routes and OpenAPI, then connect production templates page by page.
8. Remove compatibility aliases after route, browser, and persistence parity tests pass.

- Old database files remain operator-accessible backups but are never opened by new schema runtime.
- Silent partial mutation and dual-read compatibility are forbidden.
- Legacy admin routes may delegate temporarily to canonical services, but cannot write separate tables or return divergent enums.

## Verification Requirements

### Backend and Persistence

- Fresh-schema tests prove foreign keys, uniqueness, status checks, revisions, and Run-to-bookmark cascade.
- Profile tests cover valid YAML, optional/duplicate names, wrong extension, oversize, malformed YAML retained as Failed, schema failure retained as Failed, archive/restore conflicts, and selector eligibility.
- Run trigger tests prove atomic capture of profile, settings, and immutable synonym bundle revisions and no enqueue with invalid/archived profile.
- Bookmark tests prove one owner, Run-specific identity, list filters, batch removal, selection intersection, preview/export conflict, and exact deletion counts.
- Synonym tests prove concept aggregation, Pending/Approved/Declined transitions, Deferred ingestion normalization, Approved+Blocked behavior, blocked-to-active reconciliation, source deletion cleanup, zero-source row rules, no decision reuse, syntax issues, conflicts, cycles, and last-valid-bundle use.
- Backup tests prove deterministic members/checksums, traversal and zip-bomb rejection, missing/extra member rejection, all-or-nothing validation, atomic replacement, and rollback.
- Security tests prove loopback Host, same-origin, CSRF, safe filenames, no absolute paths, and no secret-bearing errors.

### API and OpenAPI

- Route tests assert status codes, envelopes, stable error codes, idempotent retries, stale revisions, pagination, and media headers.
- Runtime OpenAPI includes multipart profile/backup imports, JSON action schemas, CSV/ZIP responses, and error models.
- OpenAPI snapshot or schema assertions fail when public fields, enums, bodies, or responses disappear without contract update.

### Frontend

- Tests cover URL restoration, loading, empty, filtered empty, stale, retry, conflict, disabled, duplicate-submit, and destructive confirmation states.
- Candidate Profile tests cover failed rows, detail variants, archive/restore, related Run navigation, dialog refresh, stale selection, and input preservation.
- Bookmark tests cover shared columns, contained overflow, toolbar/table spacing, selection pruning, remove summary, export preview, preview conflict, and Run Details parity.
- Synonym tests cover read-only/edit/save, search highlighting/navigation, issue navigation, unsaved changes, status action matrices, overview/evidence separation, local log clear, settings link, and backup summaries.

### Browser and Accessibility

- Playwright covers keyboard-only primary flows at desktop and narrow viewport and verifies focus restoration.
- Screenshots cover light/dark, 200% zoom/reflow, empty/error states, long tables/editors, and internal horizontal scrolling.
- Chrome DevTools checks no uncaught console errors, failed network requests, page-level horizontal overflow, or duplicate submissions.
- Lighthouse/accessibility checks supplement, but do not replace, semantic and keyboard assertions.

## Validation Plan

- Persistence and reset tests prove normalized schema ownership, constraints, immutable revisions, transactional cleanup, and fresh-cutover refusal/backup behavior.
- Route and OpenAPI tests prove typed envelopes, stable errors, local security, revisions, idempotency, pagination, imports, actions, exports, and media metadata.
- Frontend and browser tests prove URL restoration, cross-page entity flow, accessible states, shared components, responsive containment, and duplicate-submit prevention.
- The acceptance criteria below are the observable completion claims; the implementation plan owns exact commands and execution order.

### Existing Test Baseline

- Before implementation acceptance, repair or isolate existing failing `test_post_runs_multipart_enqueue_failure_returns_persisted_failed_run`; it reaches uninitialized SQLite `idempotent_actions` and cannot provide reliable regression evidence.
- Unrelated pre-existing failures must be recorded explicitly; they cannot be presented as integration proof.

## Acceptance Criteria

### Candidate Profiles

- Valid `.yaml` creates Succeeded row and immutable revision; admitted invalid YAML creates visible Failed row without parsed profile data.
- Trigger Run options come only from current Active + Succeeded resources and use Profile ID as submitted identity.
- Run creation atomically stores profile, settings, and immutable synonym bundle revision IDs and snapshots.

### Bookmarks

- Run Details and Bookmarks read/write one normalized table and render one shared job projection.
- Submitted is absent from storage, API, filters, and UI.
- Exported row IDs equal explicit selection intersected with current stage, result filter, and search as recomputed by server.
- Run deletion confirmation names bookmark loss; completion deletes bookmarks and reports exact counts.

### Synonyms

- Review displays one concept row across source Runs and only Pending, Approved, Declined tabs.
- Approve has no Promote action. Valid mappings become Approved+Active; invalid accepted mappings become Approved+Blocked until corrected policy activates.
- Run deletion removes source associations, deletes zero-source Pending/Declined rows, and preserves Approved decision history.
- `apply_approved_enabled` owns activation/use; `auto_accept_suggestions_enabled` owns queue bypass. Auto-accept off sends every suggestion to Pending.
- Backup export/import uses three canonical YAML files and cannot partially replace active policy.

### UI and Contract Quality

- Every route has explicit OpenAPI models, stable errors, security checks, revision behavior, and verification.
- Shared controls and tables retain approved spacing, alignment, scrolling, focus, responsive, and theme behavior.
- Fresh cutover preserves timestamped old database files but imports no legacy rows or retired settings.
- No unresolved behavior or ownership conflict remains hidden as an implementation detail.

## Completion Criteria

This specification is complete when all required outcomes have an implemented owner, every acceptance criterion has fresh verification evidence, generated OpenAPI and maintained UI intent match runtime behavior, the fresh-reset boundary is proven, and no approved decision remains deferred to implementation.
