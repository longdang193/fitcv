# FitCV Prototype-to-Backend Compatibility Audit

## Metadata

- Audit ID: `2026-07-20-18-09-fitcv-prototype-backend-audit`
- Status: `open`
- Severity: `high`
- Created At: `2026-07-20T18:09:58+02:00`
- Branch: `main`
- Commit: `cb28787076fc961b4e4bfa4d561882e343d253a8`
- Frontend contract: `docs/fitcv-settings-ui-prototype.html`
- Database decision: new empty database allowed; legacy row migration and backfill are out of scope.
- Working-tree note: audit includes existing uncommitted Settings/Runs integration work. Report does not revert or replace those changes.

## Executive verdict

Backend is **not yet compatible with prototype as a complete product contract**.

Settings support is substantially connected. Run triggering, lifecycle persistence, bookmarks, application-interest ratings, result artifacts, CV downloads, review queues, and console events already exist. However, prototype Run Details and Pipeline Results cannot be reproduced reliably from stable backend resources because required truth is split across run JSON, stage artifacts, result exports, debug payloads, and several unrelated tables. Several actions remain HTML form contracts rather than frontend-safe JSON APIs. Candidate Profiles and run names are not first-class persistent resources. CV regeneration is especially incomplete: current regenerate-once worker reuses existing Markdown instead of invoking CV generation.

Fresh-database permission removes legacy migration cost. Recommended disposition: define one prototype-compatible API/domain contract, replace JSON-blob run persistence with minimum normalized run/job/stage/CV tables, then connect existing backend capabilities through those resources.

## 1. Current situation

### 1.1 Affected environment and scope

- Local FastAPI control plane in `src/fitcv_cp`.
- Pipeline runtime and artifacts in `src/fitcv`.
- SQLite persistence.
- Prototype-defined Settings, Runs, Run Details, Pipeline Results, bookmarks, ratings, CV actions, and console behavior.
- Audit is source-first. GitNexus index was stale by 16 commits and was not used as authoritative evidence.

### 1.2 Prototype contract

Prototype defines:

- Nine Pipeline settings pages: Overview, Enrichment, Screening, Shortlisting, Ranking, CV Analysis, CV Generation, Runtime & Limits, and Automation & Reuse (`docs/fitcv-settings-ui-prototype.html:51`, `docs/fitcv-settings-ui-prototype.html:945`).
- Runs list with active/archived tabs, search, selection, pagination, trigger, cancel, archive, and permanent archived deletion.
- Trigger form requiring one JSON/JSONL job file, Candidate Profile selection, and optional Run Name.
- Run Details drawer with Run Overview, Run Input, stage-filtered Pipeline Results, passed/rejected filtering, job search, pagination, CSV export, bookmarks, Application Interest, CV download/regeneration, Stretch review, Console Log, and debug-bundle download.
- Public stage IDs: `all`, `enrichment`, `screening`, `shortlisting`, `ranking`, `cv-analysis`, `cv-generation`.
- Prototype display statuses: `Running`, `Succeeded`, `Failed`.
- Persistent product expectations even though prototype runtime itself uses in-memory fixtures and simulated actions.

### 1.3 Current implemented frontend

`src/fitcv_cp/templates/settings.html` already connects:

- Settings load, patch, and reset through `/settings/pipeline` (`src/fitcv_cp/templates/settings.html:178`).
- Runs load through `/runs` (`src/fitcv_cp/templates/settings.html:214`).
- Run trigger through `/admin/upload-trigger` (`src/fitcv_cp/templates/settings.html:576`).
- Cancel, archive, unarchive, active/archived filtering, search, selection, and client-side pagination.

Remaining live-template limitations:

- Candidate Profile selector contains only hard-coded `default_config` (`src/fitcv_cp/templates/settings.html:65`).
- Optional Run Name renames uploaded file in browser instead of sending a run-name field (`src/fitcv_cp/templates/settings.html:580`).
- Job Name derives from upload manifest filename or jobs path (`src/fitcv_cp/templates/settings.html:435`).
- Frontend locally collapses all non-terminal backend states to `Running` and maps `cancelled` to `Failed` (`src/fitcv_cp/templates/settings.html:416`).
- Run Details drawer renders only summary counters and links to legacy full details (`src/fitcv_cp/templates/settings.html:603`).
- Prototype Pipeline Results, per-job actions, Console Log, and debug bundle are not implemented inside this drawer.

### 1.4 Existing backend strengths

- Persistent and validated Pipeline settings through `GET/PATCH /settings/pipeline` (`src/fitcv_cp/app.py:7369`).
- Run lifecycle statuses: `queued`, `running`, `awaiting_continue`, `cancelling`, `cancelled`, `succeeded`, `failed` (`src/fitcv_cp/models.py:26`).
- Run input snapshots and provenance for jobs and candidate profile (`src/fitcv_cp/models.py:84`).
- Run cancellation, archive, unarchive, bulk actions, process events, and run artifacts.
- Persistent bookmarks in `bookmarked_jobs` (`src/fitcv_cp/settings_store.py:58`).
- Persistent 1–5 Application Interest through immutable decision-rating events (`src/fitcv_cp/app.py:10383`).
- Enriched job snapshots in `run_structured_jobs` (`src/fitcv/enrich.py:2379`).
- Rule-filter persistence in `rule_filter_results` (`src/fitcv_cp/sqlite_store.py:1398`).
- CV versions and Markdown download (`src/fitcv_cp/sqlite_store.py:1332`, `src/fitcv_cp/app.py:10639`).
- Stage-transition artifacts covering normalize, enrich, rule filter, shortlist, ranking, CV analysis, and CV generation (`src/fitcv/pipeline_stage_artifacts.py:228`).
- Canonical job outcome projection already maps detailed terminal states to stage, outcome, and reason code (`src/fitcv/pipeline_contracts.py:250`).
- `strong | stretch | skip` fit classification exists in CV analysis and generation.
- Legacy run-detail pages already expose many loading, unavailable, warning, failure, review-required, and output-mismatch states.

## 2. Core problem

### 2.1 Expected behavior

Backend should expose stable resources from which prototype can derive every visual state and perform every action without reading internal artifact formats, submitting legacy HTML forms, or inventing state in browser code.

### 2.2 Actual behavior

No single backend resource represents a run, its stage executions, its jobs, per-stage outcomes, CV versions, evaluations, review state, bookmarks, ratings, action capabilities, and downloadable artifacts.

Run details are assembled through fallback logic across:

- `local_pipeline_runs.run_json`
- `local_pipeline_run_events`
- `run_structured_jobs`
- `rule_filter_results`
- `results_export_json`
- `stage_transition_artifacts_json`
- `cv_generation_debug_json`
- `cv_versions`
- decision-feedback tables
- bookmark table

`_build_enriched_tab_context()` demonstrates this boundary problem directly: it loads result exports, decision feedback, structured jobs, stage-artifact fallbacks, result-export fallbacks, filter rows, CV-debug fallbacks, and legacy outcome projections before it can render one table (`src/fitcv_cp/app.py:4543`).

### 2.3 Impact

- Prototype states can disagree depending on which artifact exists.
- Running and partially completed runs cannot provide complete, stable stage/job pages.
- Frontend must know backend implementation details and legacy fallbacks.
- Actions cannot be wired consistently with JSON fetch semantics.
- Identifiers differ by surface: `job_url`, raw-job fingerprint, alternative ID, review-item ID, and CV version ID.
- Status names differ between prototype, run lifecycle, stage artifacts, outcome ledger, and CV debug records.
- Deletion can leave run-owned rows behind.
- CV regeneration currently reports success without producing a newly generated CV.

### 2.4 Severity

High. Settings and basic run lifecycle can ship incrementally, but prototype-defined Run Details and Pipeline Results are not trustworthy enough for production use until canonical persistence and API contracts exist.

## 3. Evidence and reproduction

### 3.1 Source inspection commands

```powershell
rg -n "Overview|Enrichment|Screening|Shortlisting|Ranking|CV Analysis|CV Generation|Runtime & Limits|Automation & Reuse" docs/fitcv-settings-ui-prototype.html
rg -n "runJobs|jobOutcome|cvReviewState|runConsoleEntries|Application Interest|Stretch review" docs/fitcv-settings-ui-prototype.html
rg -n "@app.get\(\"/runs|@app.post\(\"/runs|settings/pipeline|bookmarks|decision-feedback|cv-review-action|stage-artifacts" src/fitcv_cp/app.py
rg -n "CREATE TABLE IF NOT EXISTS|local_pipeline_runs|run_structured_jobs|rule_filter_results|cv_versions|bookmarked_jobs" src/fitcv_cp src/fitcv
rg -n "candidate_profiles|run_name|stretch_review|cv_evaluation" src tests docs
```

### 3.2 Browser evidence

Prototype was opened through a local HTTP helper and inspected with Playwright accessibility snapshot. Snapshot confirmed nine Pipeline pages, Runs and Bookmarks navigation, settings controls, dialogs, and prototype interaction hierarchy. Only browser console error was a missing favicon; no prototype script failure was observed.

### 3.3 Focused verification

Command:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_fitcv_cp/test_app.py::test_get_pipeline_settings_returns_effective_resource tests/test_fitcv_cp/test_app.py::test_patch_pipeline_settings_uses_atomic_mutation tests/test_fitcv_cp/test_app.py::test_get_runs_returns_frontend_run_metadata tests/test_fitcv_cp/test_app.py::test_admin_bulk_delete_archived_runs_returns_deleted_summary tests/test_fitcv_cp/test_app.py::test_admin_run_cv_review_action_regenerate_once_does_not_auto_complete_review tests/test_fitcv_cp/test_worker_job.py::test_execute_cv_regenerate_once_updates_target_record_and_emits_success tests/test_fitcv_cp/test_sqlite_store.py::test_delete_archived_runs_prunes_old_rows_only -q
```

Result: `7 passed in 2.54s`.

Pytest emitted an unrelated Windows cleanup `PermissionError` for `C:\tmp\pytest-of-HOANG PHI LONG DANG\pytest-current` after test completion. Tests themselves passed.

Report-specific checks confirmed all seven required audit sections and no trailing whitespace. Repository-wide `scripts/validate_template_required_sections.py` remains blocked by pre-existing plan/spec template mismatches outside this audit; it reported no issue for this report.

### 3.4 Prototype feature support matrix

| Prototype feature | Backend support | Current UI connection | Audit result |
|---|---|---|---|
| Nine Settings pages and grouped transactions | Settings schema, validation, persistence, reset exist | Connected in prototype-derived Settings template | Supported |
| Active/archived Runs list | Run list and archive state exist | Connected; pagination/search are client-side | Partial |
| Trigger one JSON/JSONL file | Upload trigger validates JSON/JSONL and persists snapshot | Connected | Supported |
| Candidate Profile catalog | Only default/upload/paste snapshot modes exist | One hard-coded default option | Missing |
| Optional Run Name | No `run_name` field in `PipelineRun` or trigger request | Browser renames uploaded file | Missing/incompatible |
| Cancel/archive/unarchive | Endpoints and lifecycle guards exist | Connected | Supported |
| Delete selected archived runs | Store accepts optional IDs | Route ignores submitted IDs; cleanup incomplete | Defective |
| Run Overview and Run Input | Raw run resource includes some metadata | Drawer shows summary only | Partial |
| Stage progress | Run has completed/next-stage fields and stage artifacts | Prototype drawer not connected | Partial |
| Pipeline Results stage tabs | Data exists across artifacts/tables | No JSON resource; not connected | Missing contract |
| Passed/rejected filters | Outcome projection exists | Legacy enriched HTML supports richer filters | Backend capability not connected |
| Job attributes and required skills | Persisted enriched snapshots exist | Legacy enriched HTML renders them | Backend capability not connected |
| Persistent bookmarks | SQLite bookmark table and form actions exist | Not connected in prototype drawer | Partial |
| Persistent 1–5 Application Interest | Append-only rating events exist for v4 ledgers | Legacy enriched HTML forms only | Partial |
| Generated CV metadata | CV version rows exist | Legacy page renders limited fields | Partial |
| Download generated CV | Markdown endpoint exists | Legacy page only | Partial |
| Regenerate CV | Review-only queue/action exists | Not connected; worker does not regenerate | Defective |
| LLM CV evaluation and Stretch review | Fit label `stretch` exists; review-required debug state exists | No canonical evaluation resource | Partial/incompatible |
| Console Log | Persistent process events and event export exist | Prototype drawer not connected | Backend capability not connected |
| Debug bundle | Artifact ZIP endpoint exists | Prototype drawer not connected | Backend capability not connected |
| Loading/empty/warning/failure/partial states | Many states exist in legacy HTML and artifacts | No unified JSON state contract | Partial |
| Actionable validation errors | Many `HTTPException.detail` messages exist | Frontend displays plain strings | Partial |

### 3.5 Mocked or hard-coded frontend elements

Prototype intentionally mocks:

- Run catalog and simulated completion timing.
- Candidate Profile catalog.
- Per-run jobs and per-stage outcomes.
- CV review state.
- Console entries.
- Bookmarks and interest ratings in memory.
- CV download/regeneration notifications.
- CSV export from in-memory rows.

Implemented `settings.html` still hard-codes or derives:

- Candidate Profile option (`default_config`).
- Run display status mapping.
- Job Name from uploaded filename/path.
- Run Details summary shape.
- Action capability rules in JavaScript instead of receiving server capabilities.

### 3.6 Answers to requested audit questions

| # | Requested question | Answer |
|---|---|---|
| 1 | Which prototype features are already supported? | Settings persistence/validation, run trigger/lifecycle, archive/unarchive, events, input snapshots, bookmarks, 1–5 ratings, job enrichment/filter facts, stage artifacts, CV versions/download, review queue, and artifact/debug exports. |
| 2 | Which frontend elements remain mocked or hard-coded? | Prototype run/job/profile/console/CV/action state; live template default-only profile, filename-derived Run Name/Job Name, local status projection, summary-only drawer, and local action capability logic. |
| 3 | Which endpoints/actions are missing? | Candidate Profile resources, paginated Runs contract, stage/results JSON, per-job bookmark/rating JSON, general CV regeneration, CV version/evaluation resources, and prototype-ready debug bundle metadata. |
| 4 | Which endpoints are incomplete or incompatible? | `/runs`, `/runs/{id}`, form/redirect bookmark/rating/review actions, `/admin/upload-trigger`, archived bulk delete, and Markdown-only CV download metadata. |
| 5 | Which models require changes? | Candidate Profile, normalized Run, Run Input, Run Stage Execution, Run Job, Run Job Stage Result, CV Version, CV Evaluation, and bookmark source references. |
| 6 | Which pipeline states are not persisted/exposed? | Stage pending/running/warning/partial/failure progression and normalized per-job/per-stage outcomes are not first-class rows; several states exist only in events or artifact/debug JSON. |
| 7 | Which frontend states cannot be derived reliably? | Stage-tab rows for running/partial runs, Stretch review, general regeneration progress/result, selected-delete result, complete CV availability, and consistent warning/partial states. |
| 8 | Which naming/status shapes need standardization? | Prototype versus internal stage IDs, display versus lifecycle run status, detailed pipeline status versus passed/rejected result, and fit classification versus evaluation/review state. |
| 9 | Which backend capabilities are not connected? | Legacy enriched results, bookmark/rating forms, CV downloads, review queue, events, stage summaries, exports, and artifact ZIP. |
| 10 | Which risks or migration requirements exist? | Identity drift, partial-state disagreement, fake regeneration, destructive-delete defects, orphan rows, status drift, duplicated actions, unstable polling pages, old/new UI divergence, and explicit fresh-DB cutover. |

## 4. Root cause and boundary

### 4.1 Root cause

Backend evolved around operator HTML pages and diagnostic artifact exports, not around a stable frontend resource model. Pipeline truth is persisted, but it is persisted at several layers for different historical consumers. New prototype UI currently calls thin run endpoints that return raw run records rather than purpose-built view resources.

### 4.2 Confirmed findings

#### F-001 — No canonical prototype Run Details API (`P0`)

- `GET /runs` returns a raw list with no pagination envelope, filtering contract, action capabilities, links, or display projection (`src/fitcv_cp/app.py:7318`).
- `GET /runs/{run_id}` returns only `_run_to_dict()` fields (`src/fitcv_cp/app.py:7324`, `src/fitcv_cp/app.py:11243`).
- No JSON endpoint returns prototype Pipeline Results by stage.
- Current drawer therefore stops at summary counters and links to legacy HTML (`src/fitcv_cp/templates/settings.html:603`).

#### F-002 — Run/job/stage truth is fragmented (`P0`)

- Run record is stored as one JSON blob in `local_pipeline_runs` (`src/fitcv_cp/sqlite_store.py:1364`).
- Enriched jobs, filter decisions, terminal result ledger, stage samples, CV debug rows, CV versions, bookmarks, and ratings have separate identities and availability rules.
- Control-plane rendering uses multiple fallback sources (`src/fitcv_cp/app.py:4543`).
- Running/partial runs can expose different row sets from completed runs.

#### F-003 — CV regenerate-once is not real regeneration (`P0`)

- Action is limited to records already in `review_required` state (`src/fitcv_cp/app.py:8866`).
- Worker reads existing draft Markdown, hashes it, writes it back, increments an attempt count, and emits success (`src/fitcv_cp/worker_job.py:323`).
- Worker does not call CV generation or an LLM. Generated content is unchanged.
- Prototype requires a real per-job CV regeneration action and observable progress/result.

#### F-004 — Candidate Profiles are not first-class resources (`P1`)

- Trigger supports `default_config`, upload, or paste snapshots (`src/fitcv_cp/app.py:7111`).
- No `candidate_profiles` table or Candidate Profile CRUD/list API exists.
- Prototype requires stable profile IDs and names for selection and Run Input display.

#### F-005 — Run Name is missing (`P1`)

- `PipelineRun` has no `run_name` (`src/fitcv_cp/models.py:54`).
- JSON trigger request has no `run_name` (`src/fitcv_cp/app.py:5490`).
- Frontend renames uploaded file to simulate Run Name (`src/fitcv_cp/templates/settings.html:580`).
- This corrupts provenance semantics: display name and source filename become same field.

#### F-006 — Persistent actions lack stable JSON contracts (`P1`)

- Bookmark save/delete are HTML form endpoints returning `303` redirects (`src/fitcv_cp/app.py:8670`).
- Application Interest is an HTML form endpoint with source-fingerprint hidden fields and `303` redirect (`src/fitcv_cp/app.py:10383`).
- CV review action is also form-based and coupled to debug payload shape (`src/fitcv_cp/app.py:8835`).
- Prototype drawer needs fetch-friendly resources with JSON success/error bodies and current resource state.

#### F-007 — CV version and evaluation model is incomplete (`P1`)

- `cv_versions` stores version ID, run ID, job URL, fit classification, generation metadata, structured JSON, Markdown, fingerprint, and reuse status (`src/fitcv_cp/sqlite_store.py:1332`).
- Missing: canonical run-job ID, parent version, generation state, regeneration request identity, evaluation state, review state, downloadable filename, media type, size, checksum, and failure details.
- `stretch` is a fit classification, while `review_required` is a generation/debug status. Prototype `Stretch review` cannot be derived from one canonical resource.

#### F-008 — Status and stage identifiers drift across boundaries (`P1`)

- Prototype display statuses: `Running`, `Succeeded`, `Failed`.
- Backend run lifecycle has seven values (`src/fitcv_cp/models.py:26`).
- Prototype public stages use `enrichment`, `screening`, `shortlisting`, `cv-analysis`, and `cv-generation`.
- Backend stage artifacts use `enrich`, `rule_filter`, `shortlist`, `cv_analysis`, and `cv_generation` (`src/fitcv/pipeline_stage_artifacts.py:265`).
- Job outcome ledger adds accepted/held/blocked/rejected/skipped plus detailed pipeline status codes (`src/fitcv/pipeline_contracts.py:250`).
- Current frontend owns an undocumented projection (`src/fitcv_cp/templates/settings.html:416`).

#### F-009 — Archived deletion ignores selection and lacks complete ownership cleanup (`P1`)

- Request model accepts `run_ids` (`src/fitcv_cp/app.py:5540`).
- Route calls `delete_archived_runs(payload.older_than_days)` without passing `payload.run_ids` (`src/fitcv_cp/app.py:8111`).
- Store supports `run_ids`, so route behavior contradicts request contract (`src/fitcv_cp/sqlite_store.py:2795`).
- Local deletion removes only run JSON, run events, and artifact mirror (`src/fitcv_cp/sqlite_store.py:2775`). It does not remove run-owned structured jobs, filter results, CV versions, or decision-feedback rows.
- Existing endpoint test checks returned summary but not forwarded IDs (`tests/test_fitcv_cp/test_app.py:10684`).

#### F-010 — Error responses are human-readable but not stable (`P1`)

- Endpoints mostly return FastAPI `detail` strings.
- Frontend understands only a string or validation-message array (`src/fitcv_cp/templates/settings.html:142`).
- No stable error code, field map, retryability flag, conflict version, or action recovery hint exists.
- Prototype warning/failure/partial states therefore cannot use consistent recovery behavior.

#### F-011 — Run list contract cannot scale or remain consistent (`P2`)

- `/runs` returns an unwrapped list and frontend performs all filtering and pagination locally.
- API exposes serialized JSON strings such as `jobs_input_manifest_json`, `effective_settings_json`, and stage/debug JSON rather than parsed resource fields (`src/fitcv_cp/app.py:11243`).
- No stable totals, cursor/page metadata, sort contract, or server-side active/archived/search filters exist.

#### F-012 — Existing backend capabilities are stranded in legacy UI (`P2`)

- Legacy run details already render bookmarks, CV download, Application Interest, stage summaries, result filters, review queue, and diagnostic artifacts.
- Prototype-derived drawer links away instead of consuming those capabilities.
- Integration should reuse backend logic but expose it through stable JSON resources; it should not embed or reproduce legacy HTML.

### 4.3 Boundary and ownership

- Pipeline runtime owns canonical stage facts, job decisions, CV analysis, CV generation, and event emission.
- Persistence owns normalized durable state and constraints.
- Control-plane API owns public prototype-compatible IDs, display projections, action capabilities, pagination, and error envelopes.
- Frontend owns rendering and local view state only. It must not infer domain truth from filenames, raw debug JSON, or combinations of missing artifacts.

## 5. Resolution and verification

### 5.1 Resolution status

No backend implementation change is included in this audit. Current mitigation is continued access to legacy `/admin/runs/{run_id}` pages for capabilities not yet present in prototype drawer.

### 5.2 Required target API contract

Keep existing Settings API. Add or replace only resources required by prototype:

| Resource/action | Required behavior |
|---|---|
| `GET /candidate-profiles` | Stable profile IDs, names, updated timestamps, active/default flags |
| `POST/PATCH/DELETE /candidate-profiles` | Validate and persist profile content; protect default/in-use rows |
| `POST /runs` | Multipart one-file trigger with `candidate_profile_id` and optional `run_name`; persist immutable input/profile snapshots |
| `GET /runs` | Server pagination, search, active/archived filter, sort, totals, display status, backend status, capabilities |
| `GET /runs/{run_id}` | Run Overview, Run Input, counts, stage summary, links, capabilities, current error/warning state |
| `POST /runs/{run_id}/actions/{cancel|archive|unarchive}` | Idempotent JSON action result and refreshed run state |
| `POST /runs/actions/delete-archived` | Selected IDs and/or explicit age scope; transactional ownership cleanup |
| `GET /runs/{run_id}/stages` | Ordered prototype stages with persisted status, progress, counts, timestamps, warning/error summary |
| `GET /runs/{run_id}/jobs` | Stage/result/search/page filters; attributes, skills, canonical outcome, bookmark/rating/CV/evaluation state |
| `PUT/DELETE /runs/{run_id}/jobs/{run_job_id}/bookmark` | JSON persistence result and current bookmark state |
| `PUT/DELETE /runs/{run_id}/jobs/{run_job_id}/interest` | Rating 1–5 or clear; server validates current rating contract |
| `GET /runs/{run_id}/jobs/{run_job_id}/cvs` | Version history, generation/evaluation/review state, download metadata |
| `POST /runs/{run_id}/jobs/{run_job_id}/cvs/actions/regenerate` | Real CV-generation job, idempotency, progress, parent-version linkage, terminal result |
| `GET /cv-versions/{version_id}/download` | Stable filename, media type, length/checksum metadata; current Markdown endpoint may remain compatibility alias |
| `GET /runs/{run_id}/events` | Cursor pagination and canonical console entries |
| `GET /runs/{run_id}/debug-bundle` | Downloadable diagnostic bundle with availability state |

### 5.3 Required public status contract

Use one public mapping registry. Internal names may remain where required, but all APIs must expose these stable fields.

#### Run

- `backend_status`: `queued | running | awaiting_continue | cancelling | cancelled | succeeded | failed`
- `display_status`: `Running | Succeeded | Failed`
- `status_detail`: explicit queued, waiting, cancelling, cancelled, failed-stage, or partial-completion copy
- `capabilities`: booleans for cancel, archive, unarchive, delete, export, inspect

#### Prototype stage IDs

- `enrichment`
- `screening`
- `shortlisting`
- `ranking`
- `cv-analysis`
- `cv-generation`

Internal mapping should be declared once:

- `enrich` -> `enrichment`
- `rule_filter` -> `screening`
- `shortlist` -> `shortlisting`
- `cv_analysis` -> `cv-analysis`
- `cv_generation` -> `cv-generation`
- `normalize` remains preprocessing evidence under Enrichment rather than becoming an extra prototype tab.

#### Stage execution

- `pending | running | succeeded | warning | partial | failed | cancelled | skipped`

#### Job-stage result

- `pending | passed | rejected | blocked | skipped | failed | review_required | generated`
- Detailed backend reason stays in stable `outcome_code` and `reason_code`; labels are presentation metadata, not persisted truth.

#### CV

- `generation_status`: `pending | running | generated | review_required | validation_failed | generation_failed | persistence_failed | cancelled`
- `evaluation_status`: `pending | running | succeeded | failed`
- `fit_classification`: `strong | stretch | skip`
- `review_state`: `none | stretch | manual_required | approved | rejected`

This separation makes prototype `Stretch review` deterministic without treating every `stretch` fit as a generation failure or every review-required item as a stretch fit.

### 5.4 Required error envelope

```json
{
  "error": {
    "code": "candidate_profile_invalid",
    "message": "Candidate Profile contains invalid fields.",
    "field_errors": [
      {"field": "experiences[0].start_date", "code": "invalid_date", "message": "Use YYYY-MM format."}
    ],
    "retryable": false,
    "action": "Fix highlighted fields and retry."
  }
}
```

Required stable codes include at least:

- `validation_failed`
- `run_not_found`
- `run_action_not_allowed`
- `run_state_conflict`
- `candidate_profile_not_found`
- `candidate_profile_invalid`
- `job_not_found`
- `stage_not_ready`
- `results_not_ready`
- `cv_not_found`
- `cv_regeneration_not_allowed`
- `cv_regeneration_failed`
- `rating_contract_stale`
- `artifact_not_available`

### 5.5 Fresh-database target schema

Minimum normalized schema:

| Table | Purpose |
|---|---|
| `candidate_profiles` | Stable catalog, display name, validated profile JSON, default/active state |
| `pipeline_runs` | First-class run name, lifecycle, timestamps, counts, archive state, orchestration binding, error fields |
| `run_inputs` | Immutable job-file manifest/snapshot and Candidate Profile snapshot used by run |
| `run_stage_executions` | One row per prototype stage with status, progress, timestamps, counts, warning/error fields |
| `run_jobs` | Stable `run_job_id`, source identity, job URL, normalized attributes, enrichment snapshot |
| `run_job_stage_results` | One row per run-job-stage with status, outcome/reason codes, stage evidence reference |
| `cv_versions` | Run-job FK, parent version, generation status, model/prompt/schema, file metadata, content/checksum |
| `cv_evaluations` | Version FK, evaluation status, fit classification, stretch/manual review state, score/reason/evidence |
| `bookmarks` | Persistent job snapshot; source run/job references nullable so bookmark can survive run deletion |
| Existing decision-feedback tables | Retain append-only rating history; link alternatives to canonical `run_job_id` |

Constraints:

- Foreign keys enabled.
- Run-owned stage/job/result/CV/evaluation rows use `ON DELETE CASCADE`.
- Bookmarks use `ON DELETE SET NULL` for source references while retaining snapshot.
- One unique run-job identity per run.
- One unique stage row per run and prototype stage.
- CV parent version belongs to same run job.
- Status columns use checked canonical values.
- Structured JSON remains for immutable evidence payloads, not for query-critical lifecycle fields.

### 5.6 Fresh-database rollout

No legacy migration or backfill is required.

Recommended cutover:

1. Introduce one new schema version and initialize a fresh SQLite database.
2. Move existing database aside as a timestamped backup; do not dual-read it.
3. Refuse silent startup against incompatible old schema. Require explicit reset/new-database action.
4. Seed default Candidate Profile from current configured profile.
5. Remove legacy fallback reads after new APIs and pipeline persistence pass parity tests.
6. Keep artifact exports as diagnostics/downloads, not primary UI storage.

### 5.7 Verification required after implementation

- Contract tests for every API response and error envelope.
- DB constraint and cascade tests.
- Full-run and partial-run tests for every stage status.
- Per-stage job pagination/filter/search tests.
- Candidate Profile CRUD and immutable run-snapshot tests.
- Run Name independence from uploaded filename.
- Real CV regeneration test proving changed version ID, parent link, generation invocation, persisted content, and terminal status.
- Stretch evaluation tests proving independent fit, evaluation, and review fields.
- Bookmark survival after run deletion and rating ownership behavior.
- Playwright flows for Settings, trigger, active/archived runs, Run Details, stage tabs, filters, bookmark/rating, CV actions, console, errors, narrow viewport, keyboard operation, and both themes.
- Console/network inspection for failed requests, stale state, duplicate actions, and unhandled errors.

## 6. Risk and next steps

### 6.1 Integration risks

| Risk | Level | Required containment |
|---|---|---|
| Identity drift across job URL, fingerprint, alternative, review item, and CV version | High | Add canonical `run_job_id`; store aliases/evidence separately |
| Partial-run rows disagree across artifacts | High | Persist stage/job execution state transactionally as pipeline progresses |
| Regeneration action claims success without new generation | High | Replace worker with real generation path and versioned state machine |
| Selected archived deletion removes wrong runs | High | Forward IDs, validate explicit scope, transactional delete summary |
| Orphan run-owned rows after deletion | High | Foreign keys and cascade tests |
| Public status drift | High | One mapping registry and contract tests shared by list/detail/results APIs |
| Browser retries duplicate actions | Medium | Idempotency key or action-request ID for trigger/regenerate/destructive actions |
| Running-stage pagination changes while polling | Medium | Stable sort key and cursor/version in responses |
| Old HTML and new JSON surfaces diverge | Medium | Make both consume same service/resource builders during transition |
| Large result sets loaded into browser | Medium | Server-side pagination and bounded event cursors |
| Fresh DB reset surprises user | Medium | Explicit backup/reset confirmation and clear startup state |

### 6.2 Dependency order

1. Specify public identifiers, status enums, resource shapes, and errors.
2. Define fresh normalized SQLite schema and ownership rules.
3. Persist canonical run/stage/job/CV/evaluation state from pipeline.
4. Implement list/detail/results/action APIs.
5. Connect prototype drawer and interactions without visual redesign.
6. Remove legacy fallbacks only after parity verification.

### 6.3 Immediate next action

Draft one implementation specification for **canonical Run Details/Pipeline Results resources plus fresh-database schema**. This is first dependency for Candidate Profiles, CV regeneration, ratings/bookmarks JSON actions, and prototype drawer integration. Owning next-stage skill: `skill-spec-drafting`, followed by `skill-writing-plans` after contract approval.

## 7. Assumptions and unresolved questions

### Assumptions

- Prototype remains authoritative for labels, hierarchy, stage tabs, interactions, and display states.
- Backend may expose richer machine states as long as prototype projection remains exact.
- New empty database is acceptable and no production data must be migrated.
- Existing diagnostic artifacts remain useful but cease being primary UI query sources.
- Bookmarks should survive deletion of source runs because bookmark state is independently persistent.
- Application Interest remains 1–5 and separate from application-submission status.

### Unresolved questions

- Should generated CV download remain Markdown only, or must first release also provide PDF/DOCX? API should expose media metadata either way.
- Should Candidate Profiles be editable in this same phase or only selectable from a persistent catalog?
- Should archived-run deletion preserve decision-rating history for optimization, or delete/anonymize it with run-owned evidence? Policy must be explicit before foreign keys are finalized.
- Should `awaiting_continue` remain supported in product UI even though prototype trigger currently uses `run_all` only? Recommended: preserve backend state and project it as `Running` with detail/capability metadata.
- Should prototype CSV export be generated client-side from current page/filter data or server-side for full filtered result set? Recommended: server-side full filtered export for correctness.

## Audit disposition

- Prototype compatibility: `not ready`
- Settings integration: `substantially supported`
- Runs integration: `partial`
- Run Details/Pipeline Results integration: `not supported by stable contract`
- Data model readiness: `requires fresh normalized schema`
- Highest-priority defects: canonical run/job/stage resource absence, fake CV regeneration, deletion selection/cascade defects
- Recommended next artifact: approved API/domain/schema specification before implementation
