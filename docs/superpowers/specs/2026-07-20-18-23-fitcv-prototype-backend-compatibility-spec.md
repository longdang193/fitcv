---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-prototype-backend-compatibility
targets:
  - docs/fitcv-settings-ui-prototype.html
  - src/fitcv_cp
  - src/fitcv
  - tests
related_features:
  - admin_control_plane_core
  - trigger_run_management
  - inspection_debugging
  - settings_system
related_stages:
  - enrichment
  - screening
  - shortlisting
  - ranking
  - cv-analysis
  - cv-generation
---

# FitCV Prototype Backend Compatibility Specification

## Goal and Problem

### Problem

- current behavior or opportunity: `docs/fitcv-settings-ui-prototype.html` defines non-navigation behavior for Settings, Runs, Run Details, and Pipeline Results, but backend truth is fragmented across run JSON, artifacts, exports, debug payloads, and unrelated tables.
- affected users, systems, or maintainers: control-plane operators, pipeline workers, API consumers, and SQLite/workflow maintainers.
- evidence: `docs/superpowers/plans/audit/2026-07-20-18-09-fitcv-prototype-backend-audit/report.md` found no canonical Run Details/Pipeline Results resource, profile catalog, independent Run Name, complete CV/evaluation state, real regeneration, JSON job actions, canonical naming, safe deletion, or stable errors.
- consequence of no change: product cannot reproduce prototype with real data; browser must infer state, parse artifacts, retain mocks, or show misleading success.

### Goal

- desired outcome: make backend, API contracts, persistence, pipeline workflow, and application state support every prototype-defined non-navigation behavior without changing prototype structure, labels, hierarchy, or interaction model.
- observable success: frontend renders and operates all in-scope views from backend resources, including empty, loading, progress, success, warning, failure, partial, CV regeneration, stretch review, download, and validation states.

> [!IMPORTANT]
> `2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md` supersedes this specification for Candidate Profile CRUD/navigation, standalone Bookmarks, bookmark deletion/orphan behavior, Run Details export-selection, central Synonyms, and captured synonym revisions. This specification remains authoritative for other Runs, Run Details, pipeline results, CVs, Console, and diagnostics behavior.

## Required Outcomes

### Outcome: Prototype-Compatible Settings

- affected actor or system: Settings UI and settings service.
- required result: existing Pipeline settings resource supplies values, metadata, validation, reset, conflict reconciliation, and actionable errors for all nine prototype settings sections.
- success condition: no in-scope setting requires mock data or second persistence owner.

### Outcome: Stable Candidate Profile Selection

- affected actor or system: Trigger Run dialog and pipeline input resolution.
- required result: backend exposes persistent selectable profiles with stable IDs and seeds three prototype profiles.
- success condition: trigger derives options/empty state from backend; each Run stores immutable profile snapshot.

### Outcome: Canonical Run and Pipeline Resources

- affected actor or system: Runs, Run Details, and Pipeline Results.
- required result: backend supports named trigger, server search/pagination, lifecycle actions, six persisted stages, and per-job results under stable identifiers/statuses.
- success condition: UI performs no lifecycle, count, stage, or job-state inference.

### Outcome: Persistent Job and CV Actions

- affected actor or system: bookmark/Application Interest controls, CV download/regeneration controls, and Stretch review state display.
- required result: JSON actions persist state; regeneration invokes real generation and creates linked version; evaluation/fit/generation/review are separate.
- success condition: actions survive reload and return deterministic loading/progress/terminal/error states.

### Outcome: Canonical Console and Diagnostics

- affected actor or system: Console Log and debug-bundle download.
- required result: bounded event pages and bundle availability derive from canonical events/artifacts.
- success condition: Clear View is local-only; unavailable diagnostics return actionable state.

### Outcome: Fresh Normalized Persistence

- affected actor or system: SQLite store and pipeline persistence.
- required result: query-critical lifecycle state resides in normalized constrained tables; artifacts remain evidence/downloads.
- success condition: fresh DB initializes deterministically, rejects incompatible old schema, and leaves no run-owned orphans.

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| What defines behavior? | Prototype contains required labels, hierarchy, states, actions, responsive behavior, and self-checks. | `docs/fitcv-settings-ui-prototype.html` | high | Prototype is authoritative for non-navigation behavior. |
| Are Settings connected? | Frontend loads, patches, and resets through `/settings/pipeline`. | `src/fitcv_cp/templates/settings.html`, `src/fitcv_cp/app.py` | high | Preserve Settings API; close contract gaps only. |
| Can Run APIs render prototype? | `/runs` and `/runs/{run_id}` return thin serialization without stable job/stage/CV contracts. | `src/fitcv_cp/app.py` | high | Replace response contract; retain bounded aliases only. |
| Is pipeline state queryable? | Truth is split across JSON blobs, exports, artifacts, and tables. | audit, `src/fitcv_cp/sqlite_store.py` | high | Persist normalized stage/job/result rows. |
| Does regeneration create new CV? | Worker rewrites existing Markdown instead of invoking generation. | `src/fitcv_cp/worker_job.py` | high | Use canonical generator and create version. |
| Are profiles first-class? | Trigger supports snapshots but no catalog. | `src/fitcv_cp/app.py`, `src/fitcv/candidate.py` | high | Add read-only catalog with prototype seeds. |
| Can Console reuse truth? | Canonical process events exist. | `src/fitcv_cp/app.py` | high | Expose Run projection; no second ledger. |
| Must old DB migrate? | User permits new empty DB. | user direction | high | No migration, backfill, or dual-read. |

### Scope

- included behavior: Pipeline Settings; Candidate Profile catalog; Run trigger/list/search/pagination/selection/lifecycle; Run Overview/Input; six stage tabs; result counts/filter/search/pagination/export; bookmark; Application Interest; CV download/regeneration; Stretch review; Console Log; debug bundle; all required loading/empty/progress/success/warning/failure/partial/stale/unavailable states; fresh normalized persistence.
- affected boundaries: FastAPI, SQLite, pipeline reporter/worker, CV generation/evaluation, settings service, and frontend consumers.
- admissible cases: one JSON/JSONL input file, one active Candidate Profile, optional Run Name, all backend lifecycle states, zero or more jobs, and partial completion at any stage.
- compatibility expectation: prototype UI remains unchanged; richer backend lifecycle remains machine detail; legacy admin routes may remain aliases but cannot own divergent behavior.

### Non-Goals

- central Bookmarks and Candidate Profile management behavior owned by `2026-07-21-19-02-fitcv-central-workspace-frontend-backend-integration-spec.md`.
- System and Health remain navigation-only. Appearance is removed; the global theme toggle owns light/dark preference. API Providers, LLM Configuration, and Data & Backup UI intent are owned by `docs/fitcv-settings-ui-prototype.integration.md`; current backend provider constraints remain authoritative until dedicated contracts are approved.
- frontend redesign, replacement component system, changed labels, hierarchy, or navigation.
- PDF/DOCX generation; Markdown download is sufficient when metadata is complete.
- legacy DB migration, backfill, dual-read, or mixed old/new schema support.
- speculative API versioning, external multi-user authorization, or new always-on service.
- changing navigation-only frontend areas unless another in-scope feature requires shared behavior.

### Contract Conventions

#### Authority and Ownership

- prototype owns visible non-navigation structure, labels, states, and interactions.
- settings schema owns keys, types, defaults, constraints, and help metadata.
- normalized rows own query-critical Run, stage, job, CV, evaluation, bookmark, and interest state.
- canonical process-event ledger owns Console chronology.
- artifacts own downloadable evidence and diagnostics, not lifecycle truth.
- shared service/resource builders own API projection so JSON and retained HTML views cannot drift.

#### Identifiers and Timestamps

- `candidate_profile_id`: stable lowercase kebab-case. Seed IDs: `candidate-product-data`, `candidate-analytics`, `candidate-platform`.
- `run_id`, `run_job_id`, `cv_version_id`, `cv_evaluation_id`, and `action_id`: opaque immutable server-generated strings.
- source URL, fingerprint, filename, queue ID, and orchestration ID are evidence/aliases, never public row identity.
- timestamps use RFC 3339 UTC or `null`; durations use integer milliseconds; IDs are never recycled.

#### Success and Error Shape

- single resources return `{ "data": <resource> }`.
- collections return `{ "data": [...], "page": { "number": 1, "size": 25, "total_items": 0, "total_pages": 0 }, "meta": {...} }`.
- asynchronous actions return HTTP `202` with `{ "data": { "action_id": "...", "status": "queued", ... } }`.
- synchronous actions return `{ "data": <refreshed resource or result> }`.
- mutating resources use `Idempotency-Key` HTTP header as sole transport for action idempotency. Header is required for Run trigger, archived deletion, and CV regeneration; optional for naturally idempotent PUT/DELETE and repeat-safe lifecycle actions.
- same key and request fingerprint returns original result; same key with different fingerprint returns `idempotency_conflict`.
- errors use:

```json
{
  "error": {
    "code": "candidate_profile_invalid",
    "message": "Candidate Profile contains invalid fields.",
    "field_errors": [{"field": "experiences[0].start_date", "code": "invalid_date", "message": "Use YYYY-MM format."}],
    "retryable": false,
    "action": "Fix highlighted fields and retry."
  }
}
```

- `field_errors` is empty when not applicable; `action` is `null` only when no user action can resolve failure.
- stable codes include `validation_failed`, `settings_revision_conflict`, `run_not_found`, `run_action_not_allowed`, `run_state_conflict`, `candidate_profile_not_found`, `candidate_profile_inactive`, `candidate_profile_invalid`, `job_not_found`, `stage_not_ready`, `results_not_ready`, `cv_not_found`, `cv_regeneration_not_allowed`, `cv_regeneration_failed`, `evaluation_not_ready`, `rating_contract_stale`, `artifact_not_available`, `idempotency_conflict`, and `database_schema_incompatible`.

#### Pagination, Search, and Ordering

- Runs and results use `page`/`page_size`; allowed values are exactly `10 | 20 | 50`. Runs default to `20`; Pipeline Results default to `10`; maximum is `50`.
- Run search covers ID, Run Name, input filename, and profile name case-insensitively.
- job search covers title, company, location, work mode, language, seniority, family, domain, skills, outcome, and reason.
- Run order is `(created_at DESC, run_id DESC)`, matching prototype newest-first insertion. Job order is case-insensitive title ascending with `run_job_id ASC` tie-break, matching prototype title sorting while remaining stable during polling.
- events use opaque cursor ordered `(recorded_at ASC, event_id ASC)`.
- out-of-range page returns empty data with correct totals, not `404`.

### Requirements and Behavioral Contract

#### Requirement: Settings Resource Compatibility

- trigger or actor: Settings page loads, edits, saves, resets, or sees concurrent changes.
- preconditions: active settings store is readable.
- required behavior:
  - retain `GET /settings/pipeline`, `PATCH /settings/pipeline`, and `POST /settings/pipeline/actions/reset`.
  - `GET` returns every prototype-owned setting with key, current/effective/default values, type, constraints, read-only state, section ID, label/help metadata, revision, and update metadata.
  - `PATCH` accepts sparse `changes`, validates atomically, and uses `expected_revision` for optimistic concurrency.
  - reset accepts explicit keys and resets atomically to schema defaults.
  - responses return full refreshed Settings resource and revision.
- output or state change: one revision owns committed values; rejected changes write nothing.
- failure behavior: field errors map to setting keys; stale revision returns `settings_revision_conflict`; persistence failure is retryable only when safe.
- observable acceptance: all nine sections render, save, reset, show dirty state, and recover from validation/conflict without mocks.

#### Requirement: Candidate Profile Catalog

- trigger or actor: Trigger Run dialog opens.
- preconditions: fresh schema initialized.
- required behavior:
  - `GET /candidate-profiles?active=true` returns options ordered by `sort_order`, then name.
  - each item contains `candidate_profile_id`, `name`, `description`, `is_active`, `is_default`, `updated_at`, and `revision`.
  - fresh DB with a valid configured Candidate Profile seeds `candidate-product-data` — `Product Data Specialist`; `candidate-analytics` — `Analytics & Operations`; `candidate-platform` — `Data Platform Engineer`.
  - seed definitions live in one repository-owned manifest and apply only validated preference overlays to the configured profile snapshot:
    - `candidate-product-data`: `target_role=Product Data Specialist`, `role_families=[analytics]`, `domains=[product]`;
    - `candidate-analytics`: `target_role=Analytics & Operations`, `role_families=[analytics]`, `domains=[operations]`;
    - `candidate-platform`: `target_role=Data Platform Engineer`, `role_families=[data_engineering]`, `domains=[data platform]`.
  - seed overlays do not rewrite candidate identity, headline, experience, education, skills, projects, or contact facts.
  - seeded snapshot checksums/revisions and seed-manifest revision are persisted.
  - missing or invalid configured base profile does not fail DB initialization: catalog remains empty, startup records actionable setup warning, and frontend renders prototype empty-profile state.
  - list omits profile content; trigger resolves content server-side.
- output or state change: trigger stores profile ID, revision, name, and canonical validated content snapshot.
- failure behavior: missing/inactive selection returns `candidate_profile_not_found` or `candidate_profile_inactive`.
- observable acceptance: no profile option is hard-coded in frontend.

#### Requirement: Run Trigger

- trigger or actor: user submits Trigger Run dialog.
- preconditions: one active profile and one file.
- required behavior:
  - `POST /runs` accepts multipart `jobs_file`, `candidate_profile_id`, and optional `run_name`; `Idempotency-Key` header is required.
  - accepted extensions are `.json` and `.jsonl`; exactly one file is required.
  - server validates size, JSON syntax, record grain, trust-boundary fields, profile state, and Run Name length of at most `120` characters.
  - blank Run Name falls back to original filename without extension; server never renames upload to simulate Run Name.
  - server snapshots original filename, media type, length, SHA-256, parsed input/manifest, selected profile ID/revision/name/content, effective settings revision/snapshot, actor, and time before queue submission.
  - a created Run whose enqueue fails becomes terminal `failed` with orchestration error; it never disappears.
  - idempotency follows shared header contract.
- output or state change: HTTP `201` canonical Run resource; input snapshot is immutable.
- failure behavior: validation uses `422`; profile absence/state uses `404`/`409`; safe enqueue failure returns persisted failed Run.
- observable acceptance: Run appears immediately with independent name and correct immutable input.

#### Requirement: Runs Collection

- trigger or actor: Runs page loads, searches, switches tab, changes page, or polls.
- preconditions: none.
- required behavior:
  - `GET /runs?view=active|archived&search=&page=1&page_size=20&sort=created_desc` filters/paginates server-side.
  - `meta` includes `active_count`, `archived_count`, and `server_time`.
  - each summary contains identity, name, filename, profile, timestamps/duration, counts, progress, warning/error summary, archive state, statuses, and capabilities.
  - `backend_status`: `queued | running | awaiting_continue | cancelling | cancelled | succeeded | failed`.
  - `display_status`: queued/running/awaiting/cancelling map to `Running`; succeeded to `Succeeded`; cancelled/failed to `Failed`.
  - `status_detail` distinguishes queued, waiting, cancelling, cancelled, failed stage, warning, and partial completion.
  - capabilities contain `inspect`, `cancel`, `archive`, `unarchive`, `delete`, and `export` booleans.
- output or state change: read-only paginated collection.
- failure behavior: invalid query returns `validation_failed`; transient polling failure preserves current UI and exposes retry.
- observable acceptance: frontend performs no local status mapping, archive inference, or full-list pagination.

#### Requirement: Run Detail and Stage Summary

- trigger or actor: user opens Run Details or polling refreshes it.
- preconditions: Run exists.
- required behavior:
  - `GET /runs/{run_id}` returns Run Overview/Input, aggregate counts, warnings/errors, links, and capabilities.
  - input includes original filename/checksum/record count, profile ID/name/revision, settings revision, trigger mode, and immutable timestamps; secrets are omitted/redacted.
  - `GET /runs/{run_id}/stages` returns exactly six ordered prototype stages.
  - one registry maps `enrich` to `enrichment`, `rule_filter` to `screening`, `shortlist` to `shortlisting`, `ranking` to `ranking`, `cv_analysis` to `cv-analysis`, and `cv_generation` to `cv-generation`; `normalize` is Enrichment evidence, not extra tab.
  - stage status: `pending | running | succeeded | warning | partial | failed | cancelled | skipped`.
  - each stage includes ID/label/ordinal, status, progress, counts, timestamps/duration, warning/error summaries, and result availability.
  - no-stage-data case returns all six rows with correct pending/skipped state.
- output or state change: read-only resources from normalized rows.
- failure behavior: missing Run returns `run_not_found`; unavailable direct result returns `results_not_ready`, never fabricated zero.
- observable acceptance: drawer renders overview/input/stage/progress without artifact parsing.

#### Requirement: Lifecycle Actions and Archived Deletion

- trigger or actor: user cancels, archives, unarchives, or permanently deletes selected archived Runs.
- preconditions: capability is true or request is safe idempotent repetition.
- required behavior:
  - `POST /runs/{run_id}/actions/cancel`, `/archive`, and `/unarchive` accept optional `Idempotency-Key` header and return refreshed Run.
  - repeat cancel/archive/unarchive returns current state; invalid transitions return `run_action_not_allowed` or `run_state_conflict` plus current state metadata.
  - `POST /runs/actions/delete-archived` accepts `{ "run_ids": [...] }` plus required `Idempotency-Key` header; at least one explicit ID is required.
  - server verifies every ID exists and is archived before transactional delete.
  - response reports `requested_ids`, `deleted_ids`, `not_found_ids`, and `blocked_ids`; mixed invalid request deletes none.
  - delete cascades run-owned DB/files and bookmarks; response includes exact deleted Run and bookmark counts.
- output or state change: lifecycle transition or permanent removal.
- failure behavior: submitted IDs are never ignored; partial silent deletion is forbidden; cleanup failure is recorded and actionable.
- observable acceptance: only selected archived Runs disappear; active Runs cannot delete; no run-owned orphan remains.

#### Requirement: Pipeline Results Resource

- trigger or actor: user selects stage/result filter, searches, pages, polls, or exports.
- preconditions: Run exists.
- required behavior:
  - `GET /runs/{run_id}/jobs?stage=all|enrichment|screening|shortlisting|ranking|cv-analysis|cv-generation&result=all|passed|rejected&search=&page=1&page_size=10&sort=title_asc` returns one row per addressable `run_job_id`.
  - `stage=all` returns latest meaningful outcome per job while preserving stage summaries.
  - job-stage status: `pending | passed | rejected | blocked | skipped | failed | review_required | generated`.
  - every returned evaluated row has `result_bucket: passed | rejected`; `pending` and not-applicable rows are not evaluated and are omitted.
  - `passed` maps `passed`, `generated`, and `review_required` when usable downloadable output exists, including Stretch review.
  - `rejected` maps `rejected`, `blocked`, `failed`, `review_required` without usable output, and `skipped` only when caused by earlier rejection/block/failure. A genuinely not-applicable skip is omitted rather than counted.
  - raw status remains separate and `total_evaluated = passed + rejected` for every stage/filter response.
  - each row includes identity/source order/fingerprint/URL; title/company; bookmark/rating/actions; location/work mode/language/seniority/family/domain; ordered skills; stage/status/outcome/reason codes and labels; warning/error summary; latest CV/evaluation/review summary and capabilities.
  - `outcome_code` and `reason_code` are persisted truth; labels/text are projection.
  - totals cover full filtered result, not current page; no matches returns prototype empty state.
  - Run Details export preview and download routes, selection intersection, stale-preview behavior, and CSV scope follow the central-workspace specification.
- output or state change: read-only page or CSV download.
- failure behavior: invalid filter returns `validation_failed`; unstarted stage returns `stage_not_ready`; missing persistence returns `results_not_ready`.
- observable acceptance: table, counts, search, pagination, empty state, and Export are mutually consistent.

#### Requirement: Bookmark and Application Interest Actions

- trigger or actor: user toggles bookmark, sets rating 1–5, or clears rating.
- preconditions: Run and job exist.
- required behavior:
  - `PUT /runs/{run_id}/jobs/{run_job_id}/bookmark` returns `{run_job_id, bookmarked: true, bookmark_id}`; `DELETE` clears it.
  - bookmark references non-null Run and Run Job owners and deletes with source Run through `ON DELETE CASCADE`.
  - `PUT /runs/{run_id}/jobs/{run_job_id}/interest` accepts `{ "rating": 1..5, "rating_contract_revision": "..." }`; `DELETE` clears current rating.
  - set/clear writes append-only decision-feedback event and current projection.
  - same action request is idempotent and cannot duplicate feedback history.
- output or state change: persistent bookmark/current interest plus feedback event.
- failure behavior: missing job returns `job_not_found`; invalid value returns `validation_failed`; stale contract returns `rating_contract_stale` with current metadata.
- observable acceptance: reload preserves controls; clear works; Run deletion preserves bookmark.

#### Requirement: CV Version Resource and Download

- trigger or actor: result row requests CV history or download.
- preconditions: Run/job exists.
- required behavior:
  - `GET /runs/{run_id}/jobs/{run_job_id}/cvs` returns newest-first versions.
  - each version includes ID, parent ID, ordinal, generation status, timestamps/duration, generator/model/prompt/schema IDs, source profile/settings revisions, checksum/length/media type/filename, evaluation/review summaries, and capabilities.
  - generation status: `pending | running | generated | review_required | validation_failed | generation_failed | persistence_failed | cancelled`.
  - `GET /cv-versions/{cv_version_id}/download` returns stored bytes with stable `Content-Type`, `Content-Length`, checksum/ETag, and attachment filename.
  - first compatible release requires Markdown (`text/markdown; charset=utf-8`); later formats do not replace version identity.
  - download requires terminal downloadable state and verified file integrity.
- output or state change: read-only history or file download.
- failure behavior: unavailable version/file returns `cv_not_found` or `artifact_not_available`; checksum mismatch blocks download and records integrity error.
- observable acceptance: Download targets exact persisted version and metadata.

#### Requirement: Real CV Regeneration

- trigger or actor: user selects Regenerate.
- preconditions: job is eligible, parent exists when supplied, generation inputs remain, and no conflicting active regeneration exists.
- required behavior:
  - `POST /runs/{run_id}/jobs/{run_job_id}/cvs/actions/regenerate` accepts optional `parent_cv_version_id` plus required `Idempotency-Key` header.
  - action creates new version in `pending`, links parent, snapshots inputs, and queues canonical generation path used by initial generation.
  - transitions: `pending -> running -> generated|review_required|validation_failed|generation_failed|persistence_failed|cancelled`.
  - successful generation atomically persists content/checksum before terminal state; previous versions stay immutable/downloadable.
  - same key returns same version/action; concurrent different request returns `cv_regeneration_not_allowed` with active version ID.
  - restart reconciles durable pending/running action; generated is impossible without new content/checksum.
- output or state change: HTTP `202` action and new version summary; normal reads expose progress/terminal state.
- failure behavior: failure remains on new version with actionable code/message; parent remains fallback.
- observable acceptance: generator invocation, distinct ID, parent link, new bytes/checksum, and terminal state are proven.

#### Requirement: LLM Evaluation and Stretch Review State

- trigger or actor: generation completes or evaluation runs.
- preconditions: generated content exists.
- required behavior:
  - evaluation status: `pending | running | succeeded | failed`.
  - successful evaluation persists `fit_classification: strong | stretch | skip`, optional score, reason/evidence, evaluator/model/prompt/schema IDs, and timestamps.
  - review state: `none | stretch | manual_required | approved | rejected`, independent from fit and generation.
  - successful `stretch` initializes review state `stretch`; other successful accepted output may project `approved`; existing internal/manual workflows may persist `manual_required` or `rejected` without adding prototype UI interaction.
  - prototype renders `Stretch review` badge when and only when `review_state=stretch`; badge is not interactive.
  - this specification adds no review mutation endpoint because prototype defines state display, not review action. Existing backend review capability may remain outside this UI if it uses same persisted state contract.
  - failed evaluation never infers skip/stretch/generation failure.
- output or state change: evaluation and review projection visible in job/CV resources.
- failure behavior: not-ready returns `evaluation_not_ready`; provider failure sets evaluation failed with retry metadata.
- observable acceptance: Stretch review badge derives only from structured state and survives reload.

#### Requirement: Console Events and Debug Bundle

- trigger or actor: Console expands, loads more, clears view, or downloads bundle.
- preconditions: Run exists.
- required behavior:
  - `GET /runs/{run_id}/events?cursor=&limit=100` projects canonical process events unchanged.
  - item fields: event ID/time, stage ID, level, operation, state, message, safe payload summary, and diagnostic references; default limit 100, maximum 500.
  - Clear View deletes only loaded browser rows; no backend delete endpoint exists.
  - `GET /runs/{run_id}/debug-bundle` downloads when ready; Run detail exposes `not_ready | available | unavailable | failed` plus reason/action.
  - bundle manifest names Run, generation time, included artifacts, redactions, checksums, and missing optional artifacts.
- output or state change: read-only events or bundle download.
- failure behavior: unavailable bundle returns `artifact_not_available`; integrity conflicts remain visible, not dropped.
- observable acceptance: chronology matches ledger; reload after Clear View restores events.

#### Requirement: Deterministic State Projection

- trigger or actor: pipeline writes transitions; frontend polls any Run resource.
- preconditions: Run input persisted.
- required behavior:
  - run/stage/job public states derive from normalized fields plus one shared registry.
  - transitions persist status, timestamps, counters, and error/warning data transactionally with affected result rows where feasible.
  - stage `warning` means usable output with non-fatal warnings; stage `partial` means usable output exists but stage stopped with unresolved/failed work.
  - Run terminal decision table is authoritative:
    - `succeeded`: orchestration completed every planned stage and every addressable job has an allowed terminal domain outcome; expected rejection, blocked, skipped-after-rejection, generated, Stretch review, and non-fatal warning outcomes do not fail Run;
    - `failed`: required stage, system, generation persistence, or orchestration failure prevents planned completion, or any addressable job remains `pending`/`running` when attempt terminates;
    - `cancelled`: explicit cancellation or cancellation-policy timeout terminates attempt.
  - terminal Run exposes `partial_completion=true` when failed/cancelled Run retains any usable stage/job/CV result; otherwise false. `status_detail` names partial completion without changing backend terminal status.
  - succeeded Run may contain warnings and domain rejections but cannot contain unresolved running/pending rows or stage `partial`.
  - counts are recomputable; mismatch surfaces integrity warning, not silent API correction.
- output or state change: same projection across list, detail, stage, job, export, and actions.
- failure behavior: illegal transition is rejected/recorded; partial results remain after failure.
- observable acceptance: same DB state yields same status/count after restart and across endpoints.

### Persistence Contract

#### `candidate_profiles`

- primary key: `candidate_profile_id`.
- fields: name, description, canonical profile JSON, revision, checksum, active/default flags, sort order, timestamps.
- constraints: stable ID; unique case-insensitive name; at most one active default; validate JSON before write.

#### `pipeline_runs` and `run_inputs`

- `pipeline_runs` fields: `run_id`, first-class `run_name`, checked backend status/detail code, trigger metadata, timestamps, archive state, orchestration binding, aggregate counts, settings revision, errors/warnings, row revision.
- `run_inputs` is one-to-one `ON DELETE CASCADE`; fields include filename/media/length/SHA-256, immutable job manifest/snapshot, profile ID/revision/name/content snapshot, settings snapshot, and creation time.
- constraints: terminal timestamps consistent; archived Runs cannot be running; Run Name differs from filename evidence; input snapshot is immutable.

#### `run_stage_executions`, `run_jobs`, and `run_job_stage_results`

- `run_stage_executions`: unique `(run_id, stage_id)`, checked status, ordinal, progress/counts, timestamps, warning/error data, evidence reference, row revision; six rows created with Run; `ON DELETE CASCADE`.
- `run_jobs`: primary `run_job_id`, Run FK, source index/fingerprint/snapshot/URL, normalized attributes, skills JSON, current projection references; unique `(run_id, source_index)`; source fingerprint is indexed correlation evidence, not uniqueness constraint; `ON DELETE CASCADE`.
- `run_job_stage_results`: unique `(run_job_id, stage_id)`, checked status, outcome/reason codes, evidence, timestamps, row revision; `ON DELETE CASCADE`.
- denormalized summaries are transactional projections only, never separate truth.

#### `cv_versions`, `cv_evaluations`, and `cv_review_events`

- `cv_versions`: primary ID, job FK, nullable same-job parent FK, ordinal, checked generation status, timestamps, generator/model/prompt/schema IDs, input snapshot/checksum, filename/media/length/content checksum/storage, errors, action/idempotency metadata; `ON DELETE CASCADE`.
- constraints: unique `(run_job_id, ordinal)`; parent belongs to same job; generated/review-required terminal state requires persisted content and matching checksum.
- `cv_evaluations`: primary ID, version FK, checked status, optional fit/score/reason/evidence, evaluator/model/prompt/schema IDs, timestamps/errors, current/superseded marker; at most one current evaluation; fit required only when succeeded.
- `cv_review_events`: immutable event ID, version/evaluation FKs, from/to state, actor, note, action/idempotency ID, timestamp; checked transitions.

#### `bookmarks`, Interest, and Existing Process Events

- `bookmarks`: primary ID, non-null Run/job FKs using `ON DELETE CASCADE`, timestamps; one bookmark per `run_job_id`. Same listing in different Runs has independent bookmark state. Central listing and deletion behavior are owned by the central-workspace specification.
- current interest is one projection per `run_job_id` and rating-contract revision; each set/clear writes existing append-only decision feedback.
- Run deletion cascades current run-job interest projection. Feedback event survives with Run/job FKs set null and retains only source fingerprint, rating/clear action, rating-contract revision, policy/model identifiers already required by optimization, and timestamp; uploaded raw job payload, Candidate Profile snapshot, and CV content are not copied into retained feedback.
- existing process-event ledger remains Console SSOT; canonical Run/job/stage/CV/action IDs become references. No competing event table is added.

### Constraints and Alternatives

- constraint: prototype UI cannot be weakened to fit backend.
- constraint: fresh empty DB is allowed, but reset is explicit and old DB is timestamped backup.
- constraint: secrets, provider credentials, and unsafe uploaded content never appear in API, Console, CSV, or bundle.
- constraint: large inputs use indexed server queries, bounded pages/cursors, and streaming downloads.
- alternative: keep JSON/artifacts as UI source.
  - benefit: smaller schema change.
  - trade-off: unreliable partial state, pagination, constraints, and restart recovery.
  - reason accepted or rejected: rejected.
- alternative: redesign prototype around current summaries.
  - benefit: less backend work.
  - trade-off: violates authoritative contract.
  - reason accepted or rejected: rejected.
- alternative: full Candidate Profile CRUD.
  - benefit: broader administration.
  - trade-off: expands this Run-focused specification.
  - reason accepted or rejected: moved to the central-workspace specification.
- alternative: client-side current-page CSV.
  - benefit: no export endpoint.
  - trade-off: incomplete under server pagination.
  - reason accepted or rejected: rejected.
- alternative: overwrite CV during regeneration.
  - benefit: simpler storage.
  - trade-off: destroys auditability and cannot prove regeneration.
  - reason accepted or rejected: rejected.

## Design Decisions

### Decision: Prototype Is Non-Navigation Product Contract

- context: prototype contains functional surfaces and links explicitly labeled navigation-only.
- selected approach: implement every non-navigation behavior; exclude only explicit navigation-only areas.
- rationale: preserves frontend truth without inventing placeholder-destination work.
- alternatives considered: implement every link; treat prototype as illustrative.
- accepted trade-offs: Candidate Profile management and standalone Bookmarks are governed by the central-workspace specification rather than duplicated here.
- affected owners and boundaries: frontend integration, APIs, domain model, tests.

### Decision: Preserve Settings API and Stable Profile Identity

- context: Settings is connected; Trigger Run requires stable profile options and immutable snapshots.
- selected approach: retain Settings routes/schema and stable seeded profile IDs; central profile creation and lifecycle follow the central-workspace specification.
- rationale: prevents Trigger Run from hard-coding labels or owning profile data.
- alternatives considered: new Settings family; frontend hard-coding; duplicated profile catalog.
- accepted trade-offs: profile administration remains a separate central resource rather than part of Run APIs.
- affected owners and boundaries: settings schema/store, profile resource, DB initialization, trigger validation.

### Decision: One Public Stage and Status Registry

- context: prototype and pipeline use different names; prototype status is coarser.
- selected approach: one registry owns stage IDs/order/labels/aliases and run display projection; APIs expose both backend/display statuses and detail/capabilities.
- rationale: prevents list/detail/result/export drift while preserving operational truth.
- alternatives considered: endpoint mappings; internal rename; persisted collapsed state.
- accepted trade-offs: explicit internal/public boundary remains.
- affected owners and boundaries: reporter, resource builders, tests.

### Decision: Normalized Query Truth With Stable Run-Job Identity

- context: artifact reconstruction and mixed URL/fingerprint identity cannot support live UI reliably.
- selected approach: normalized stage/job/result/CV/evaluation rows; assign `run_job_id` during ingestion; keep artifacts/evidence JSON diagnostic.
- rationale: supports partial progress, FK constraints, pagination, restart recovery, and consistent actions.
- alternatives considered: artifact indexing; URL/fingerprint primary key.
- accepted trade-offs: same listing in separate Runs has distinct `run_job_id`; fingerprint correlates it.
- affected owners and boundaries: ingestion, pipeline persistence, API queries, all job actions.

### Decision: Real Versioned Regeneration and Separate Evaluation State

- context: current regeneration is not generation; stretch/review/failure meanings are conflated.
- selected approach: initial/regeneration share canonical generator; every regeneration creates immutable linked version; generation/evaluation/fit/review have separate enums.
- rationale: symmetric generation, auditability, deterministic Stretch review, actionable failure.
- alternatives considered: rewrite old Markdown; separate generator; combined status/prose inference.
- accepted trade-offs: durable async version/action state and extra constrained rows.
- affected owners and boundaries: worker, CV generation/evaluation, persisted review projection, storage, APIs.

### Decision: Server-Side Selected Filtered Export

- context: prototype Export applies while results are paginated.
- selected approach: preview and CSV routes reuse exact result predicates and export explicit selection intersected with current stage, result filter, and search.
- rationale: correct export independent of loaded page without exporting unselected matches.
- alternatives considered: browser current-page export.
- accepted trade-offs: backend streams export.
- affected owners and boundaries: result query and CSV response.

### Compatibility, Migration, and Risk

- old behavior: thin Run JSON, mixed truth, frontend status inference, HTML actions, filename-based name, pseudo-regeneration, permissive old schema.
- new behavior: stable resources, normalized truth, JSON actions, immutable snapshots, versioned regeneration, structured evaluation/review, and shared projections.
- compatibility boundary: prototype frontend uses canonical resources; legacy `/admin/upload-trigger`, forms, downloads, details, and exports may remain temporary aliases only through same service/resource owners.
- migration or backfill: none; old SQLite rows are not imported.
- rollout and rollback:
  - initialize one new schema version in new DB or after explicit reset;
  - move old DB/WAL/SHM to timestamped backup before new startup;
  - refuse incompatible schema with `database_schema_incompatible` and explicit action;
  - seed profiles/settings transactionally;
  - rollback restores matched old app/DB pair; no new-to-old conversion.
- reset/cutover owner: operator-only CLI/startup command reusing existing local backup/archive mechanism. No HTTP endpoint and no Data & Backup UI change is introduced by this specification.
- deprecation or consumer impact: switch current Run frontend as one compatible slice; remove aliases only after parity verification.
- risk: identity drift; mitigation: mandatory `run_job_id` FK/API identity.
- risk: summary/result drift; mitigation: transactional writes, constraints, recomputation integrity checks.
- risk: duplicate actions; mitigation: durable idempotency key bound to payload fingerprint.
- risk: polling reshuffles pages; mitigation: immutable sort keys and server totals.
- risk: Run deletion removes curated bookmarks; mitigation: preview and confirmation expose exact bookmark count, while response proves exact cascade.
- risk: large result/bundle memory; mitigation: indexes, bounds, and streaming.

## Invariants and Edge Cases

### Invariants

- prototype remains authoritative for all non-navigation labels, hierarchy, component states, and interactions.
- navigation-only areas receive no backend changes solely from this specification.
- every Run has one immutable input snapshot and exactly six prototype stage rows.
- every input job receives immutable `run_job_id` before stage processing.
- one registry owns stage/status projections; list, detail, stage, job, CSV, and action responses agree for same revision.
- terminal downloadable CV requires stored bytes and verified checksum; regeneration never mutates prior version.
- evaluation failure never implies fit; `stretch` and review state are never inferred from prose.
- bookmark and Application Interest are independent; bookmark deletes with source Run while feedback retention follows its separate contract.
- Clear View never deletes process events.
- run-owned stage/job/result/CV/evaluation rows cascade on permanent Run deletion.
- input/profile/settings snapshots, CV bytes, evaluation evidence, and review history are immutable after creation.
- errors always include stable machine code and actionable message.
- secrets and credentials never leave trusted backend through in-scope resources/downloads.

### Edge Cases

- empty or minimal input:
  - missing/invalid configured base profile or no active profiles returns successful empty catalog, setup warning, and disabled trigger state.
  - empty job file is rejected; valid file with zero accepted records creates no Run.
  - zero result matches returns successful empty page and zero totals.
- normal and large input:
  - indexed server pagination/search/export is required.
  - CSV and debug bundle stream output; page/cursor limits remain enforced.
- duplicate, missing, malformed, or unsupported data:
  - duplicate source records follow existing pipeline dedup policy and retain evidence.
  - malformed JSON/JSONL reports record/line field error without creating Run.
  - unsupported extension/media returns `validation_failed`.
  - missing optional attributes render empty/unknown values without changing identity.
- retry, cancellation, timeout, partial failure, or concurrency:
  - trigger, regeneration, rating, and destructive actions use durable idempotency.
  - cancellation preserves completed rows and marks unresolved work cancelled/skipped consistently.
  - timeout persists failure at action/stage/Run owner without deleting partial outputs.
  - concurrent bookmark/rating writes use row revision/action ID; stale contract/revision is explicit.
  - one active regeneration per job unless same idempotent request.
- migration or mixed-version state:
  - unsupported old DB never opens for write; no dual-read or partial backfill exists.
  - old backup remains outside new query path.
- generated-source consistency:
  - artifacts never override normalized state; retained legacy routes call canonical owners.
- security or accessibility boundary:
  - upload paths stay in controlled storage; display filenames are escaped and response filenames sanitized.
  - CSV formula-leading cells are escaped; download headers prevent injection.
  - API supplies explicit capabilities and validation states needed by semantic controls, keyboard/focus behavior, reduced motion, responsive layout, and both themes defined by prototype.

## Validation Plan

### Acceptance Criterion: Settings and Profiles Cover Prototype

- setup or precondition: fresh DB and valid settings schema.
- action: load all Settings sections; save valid/invalid/stale changes; reset; initialize with valid and invalid/missing base profiles; query catalog; trigger each seed.
- expected result: complete Settings metadata and atomic writes; valid base creates exact three seeded IDs/names and validated overlays; missing/invalid base creates empty catalog plus setup warning without failing DB startup; Run snapshots remain immutable.
- failure condition: mock option/value, partial commit, missing setting, mutable snapshot, or free-text-only error.
- proof method: schema/resource/API/DB tests plus browser save/reset/trigger flows.
- expected evidence: all nine sections and profile cases match contract.

### Acceptance Criterion: Run Trigger Is Named and Idempotent

- setup or precondition: active profile and valid JSON/JSONL fixtures.
- action: trigger with explicit/blank name, retry same key, retry conflicting payload, and submit malformed file.
- expected result: independent name, filename fallback, one Run for safe retry, explicit conflict, no Run for malformed input.
- failure condition: filename rewrite, duplicate Run, or partial input state.
- proof method: API integration and DB transaction tests.
- expected evidence: Run/Input rows, checksums, queue binding, and response agree.

### Acceptance Criterion: Runs and Lifecycle Are Canonical

- setup or precondition: Runs in every backend/archive state.
- action: list/search/page/poll with prototype page sizes/defaults; execute allowed/disallowed/repeated actions; terminate fixtures through normal completion, required failure, and cancellation with/without usable partial results.
- expected result: stable prototype order/totals/page defaults, exact display projection/detail/capabilities, authoritative terminal decision table, correct `partial_completion`, idempotent repeats, and actionable conflicts.
- failure condition: frontend inference, reshuffle, silent invalid action, or count mismatch.
- proof method: parameterized API tests and browser active/archived flow.
- expected evidence: status/capability matrix snapshots.

### Acceptance Criterion: Selected Archived Deletion Is Safe

- setup or precondition: multiple archived Runs, one active Run, children, bookmarks, feedback, and files.
- action: delete selected IDs; submit active/unknown mix; retry same request.
- expected result: only selected archived Runs delete transactionally; invalid mix deletes none; children/files clean; source bookmarks cascade; response lists exact Run and bookmark outcomes.
- failure condition: ignored IDs, unselected deletion, orphan, or unreported bookmark loss.
- proof method: API, FK/cascade, filesystem, and idempotency tests.
- expected evidence: before/after DB and file assertions.

### Acceptance Criterion: Stage Progress Survives Restart

- setup or precondition: fixtures covering every stage status and partial Run.
- action: persist transitions, restart app/store, query list/detail/stages/jobs.
- expected result: exact state/count/timestamps remain; endpoints agree.
- failure condition: artifact reconstruction, missing tabs, fabricated zero, or drift.
- proof method: reporter/store integration and restart tests.
- expected evidence: normalized rows and projections match transition table.

### Acceptance Criterion: Pipeline Results Match Filters and Export

- setup or precondition: Run with diverse attributes/outcomes across six stages.
- action: query stage/result/search/page combinations, select explicit jobs, preview export, and download selected-filtered CSV.
- expected result: stable job IDs, title-ascending order, page default `10`, page sizes `10|20|50`, exhaustive Passed/Rejected partition with `total_evaluated = passed + rejected`, correct empty state, and CSV containing only selected jobs still matching current predicates.
- failure condition: page-only export, unselected row export, identity drift, wrong totals, stale-preview download, or unstable order.
- proof method: query/API tests plus browser filter/search/pagination/export flow.
- expected evidence: API and CSV row-ID sets match.

### Acceptance Criterion: Bookmark and Interest Persist

- setup or precondition: addressable job and current rating contract.
- action: use same listing in two Runs; set/clear/retry one Run's bookmark and ratings 1–5; reload; delete source Run.
- expected result: bookmark remains independent per `run_job_id`; state persists; retry is idempotent; feedback records actions; source Run deletion cascades bookmark; stale contract rejects.
- failure condition: redirect-only behavior, duplicate history, state loss, or invalid rating.
- proof method: API, DB ownership, and browser control tests.
- expected evidence: projections and append-only events match actions.

### Acceptance Criterion: CV Regeneration Is Real and Versioned

- setup or precondition: generated parent CV and test spy at existing generation boundary.
- action: regenerate, observe transitions, retry key, issue concurrent request, download old/new versions.
- expected result: generator invoked; new linked ID/content/checksum exists; old version unchanged; retry returns same version; conflict is explicit.
- failure condition: copied old Markdown, same ID, missing content, or prior mutation.
- proof method: worker/service/API integration and download integrity tests.
- expected evidence: invocation, version rows, checksums, and state sequence.

### Acceptance Criterion: Stretch Evaluation and Review Are Independent

- setup or precondition: strong, stretch, skip, and provider-failure fixtures.
- action: evaluate each fixture, restart, and inspect job/CV resources and prototype result row.
- expected result: evaluation/generation/fit/review stay independent; stretch initializes persisted `review_state=stretch`; only stretch renders badge; state survives restart.
- failure condition: prose inference, failure mapped to skip/stretch, non-stretch badge, or lost state.
- proof method: evaluator/store/API tests and browser Stretch review rendering flow.
- expected evidence: constrained response matrix for every combination.

### Acceptance Criterion: Console and Debug Bundle Are Truthful

- setup or precondition: multi-page events, diagnostics, missing optional artifact, and integrity-conflict fixture.
- action: page events, clear browser view, reload, and request ready/not-ready bundle.
- expected result: deterministic chronology, local-only clear, visible conflict evidence, safe bundle manifest, actionable unavailable state.
- failure condition: deleted/duplicate/omitted event, leaked secret, or broken unavailable link.
- proof method: event/bundle tests, Playwright Console flow, and DevTools network/console inspection.
- expected evidence: event order and bundle manifest match canonical records.

### Acceptance Criterion: Prototype Interaction and Accessibility Remain Intact

- setup or precondition: integrated frontend with fixtures for every visible state.
- action: execute all in-scope flows at desktop/narrow viewport with keyboard, reduced motion, light, and dark modes.
- expected result: prototype structure, labels, hierarchy, states, focus, responsive behavior, and interactions remain unchanged except mocks become real data/actions.
- failure condition: redesign, missing state, inaccessible control, focus loss, layout break, or uncaught request/console error.
- proof method: Playwright snapshots/flows/screenshots and Chrome DevTools console/network/Lighthouse checks.
- expected evidence: parity against prototype self-checks and no unhandled frontend errors.

### Acceptance Criterion: Fresh Database Cutover Is Explicit

- setup or precondition: old-schema DB and no new DB.
- action: start without reset, invoke operator CLI/startup backup-reset command, initialize new DB, start again, and inspect HTTP routes/UI.
- expected result: first start refuses writes with actionable incompatibility; reset preserves timestamped files; new schema/seeds initialize transactionally; Runs are empty.
- failure condition: silent mutation, dual-read, lost backup, partial seed, old rows exposed, or new reset HTTP/UI surface.
- proof method: startup integration and filesystem assertions.
- expected evidence: error code, backups, schema version/constraints, seeds, and empty collections.

## Completion Criteria

Specification is approved for implementation planning when:

1. prototype authority and navigation-only exclusions are explicit and testable;
2. Settings, profiles, Runs, stages, jobs, actions, CVs, evaluation/review, Console, export, download, and errors are unambiguous;
3. identifiers, enums, mappings, pagination, ordering, idempotency, and transitions have one owner;
4. normalized schema, FK ownership, cascade behavior, immutable snapshots, and backup/reset boundary are resolved;
5. real regeneration and structured Stretch review have observable state machines and proof requirements;
6. loading, empty, progress, success, warning, failure, partial, unavailable, stale, retry, cancellation, and concurrency are covered;
7. outcomes map to API, DB, worker, browser, accessibility, Console, network, and download evidence;
8. no behavior-changing question remains hidden as implementation detail;
9. file/task/command sequencing remains deferred to approved implementation plan.
