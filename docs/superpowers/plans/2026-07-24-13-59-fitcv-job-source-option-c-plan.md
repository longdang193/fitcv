---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-job-source-option-c-implementation
parent_spec: docs/superpowers/specs/2026-07-24-13-15-fitcv-job-source-option-c-spec.md
targets:
  - src/fitcv/ingest.py
  - src/fitcv/job_sources.py
  - src/fitcv/ats_export.py
  - src/fitcv/personio_export.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_ingest.py
  - tests/test_job_sources.py
  - tests/test_ats_export.py
  - tests/test_personio_export.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - docs/job-data-input.md
---

# FitCV Job Source Option C Implementation Plan

## Goal

Deliver Personio, Greenhouse, and Workday company-portal scanning as a first-class FitCV run source. Reuse one canonical job artifact, one static provider registry, one control-plane scanner request, and the existing path-based pipeline through a verified run-owned projection. Preserve path, upload, paste, normalization, deduplication, ranking, CV behavior, historical runs, and the unwired Apify helper.

## Implementation Outcomes

### Canonical Run Input

Path, upload, paste, and scanner inputs resolve through one canonical validator and serializer. `jobs_input_json` owns immutable run jobs, `jobs_path` contains identical run-owned UTF-8 bytes, and worker preflight rejects projection drift before pipeline execution. Standalone export permits `[]`; every run source rejects zero jobs with `empty_job_input`.

### Unified Provider Acquisition

One `src/fitcv/job_sources.py` registry owns provider metadata, detection, request normalization, shared limits, stable errors, and optional developer export. Provider-local parser and transport modules remain implementation details; their duplicate standalone exporter behavior is removed.

### Non-Technical Scanner UI

Existing run-creation page exposes upload and scanner modes. Scanner fields use registry-derived provider choices and the same backend request contract, remain keyboard accessible and responsive, and create runs without user-supplied job files.

### Focused Proof And Documentation

Unit, control-plane, worker, browser, security, empty-result, extension, and pipeline-compatibility checks prove specification invariants. Job input documentation names canonical owners, supported V1 providers, run projection behavior, and Apify helper non-scope without copying registry data.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-test-driven-development`, `skill-code-standards`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: current `career-ops-personio-spike` worktree; preserve all unrelated modified and untracked files
- Parallel ownership: none; `src/fitcv_cp/app.py`, canonical artifact types, and provider contracts are shared dependency owners
- Sequential fallback: canonical artifact, provider registry, control-plane integration, worker integrity, V1 UI, documentation and final proof

## Task Breakdown

### Task 1: Centralize Canonical Job Artifacts

**Purpose:**
- Create one reusable validator, serializer, digest, and atomic writer for every job source.

**Specification Coverage:**
- Canonical Job Artifact; Source Acquisition Symmetry; Snapshot and Provenance Separation; Empty Artifact and Empty Run Are Different Contracts.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv/contracts.py:REQUIRED_SCRAPER_FIELDS`
- Inspect: `src/fitcv/ingest.py:parse_jobs_file`
- Inspect: `src/fitcv/ingest.py:validate_linkedin_schema`
- Add: `src/fitcv/ingest.py:CanonicalJobs`
- Add: `src/fitcv/ingest.py:canonicalize_jobs`
- Add: `src/fitcv/ingest.py:write_canonical_jobs`
- Modify: `tests/test_ingest.py`

**Dependencies:**
- Existing `REQUIRED_SCRAPER_FIELDS` remains the only required-field list.
- Existing `certifi`, Pydantic, and standard library dependencies remain unchanged.

**Steps:**
- [ ] Step 1: Add failing tests for list/object validation, required-field reuse, optional-field preservation, deterministic order, UTF-8 serialization, digest stability, empty-list validity, atomic replacement, and failed-write cleanup.
- [ ] Step 2: Add frozen `CanonicalJobs` with `jobs`, `json_text`, and `sha256`; implement `canonicalize_jobs(value)` using `REQUIRED_SCRAPER_FIELDS`, `json.dumps(..., ensure_ascii=False, indent=2)`, and SHA-256 over exact UTF-8 bytes.
- [ ] Step 3: Implement `write_canonical_jobs(path, artifact)` with `tempfile.NamedTemporaryFile` in the destination directory and `os.replace`; write `artifact.json_text` exactly without an added newline.
- [ ] Step 4: Keep `parse_jobs_file`, `prepare_raw_rows`, and `fetch_from_apify` behavior unchanged; route only new trigger/export paths through `canonicalize_jobs`.

**Verification:**
- [ ] `uv run pytest tests/test_ingest.py -q`
- Expected: canonicalization and atomic-write tests pass; existing ingest and Apify helper tests remain green.

**Exit Criteria:**
- One canonical artifact object owns validated jobs, exact JSON text, and digest without new dependencies or duplicated required-field lists.

### Task 2: Replace Spike Exporters With One Provider Registry

**Purpose:**
- Consolidate Personio, Greenhouse, and Workday acquisition behind one static, source-neutral contract.

**Specification Coverage:**
- One Provider Registry; Boundary Adaptation; Provider Resolution Permanence; Scanner Request Contract; Uniform Provider Acquisition; Initial Provider Semantics; Native and Secure Transport; Error Contract; Provider Admission and Extension.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect and migrate: `src/fitcv/personio_export.py`
- Inspect and migrate: `src/fitcv/ats_export.py`
- Add: `src/fitcv/job_sources.py:ScannerRequest`
- Add: `src/fitcv/job_sources.py:ProviderDefinition`
- Add: `src/fitcv/job_sources.py:JobSourceError`
- Add: `src/fitcv/job_sources.py:PROVIDERS`
- Add: `src/fitcv/job_sources.py:build_scanner_request`
- Add: `src/fitcv/job_sources.py:list_provider_options`
- Add: `src/fitcv/job_sources.py:resolve_provider`
- Add: `src/fitcv/job_sources.py:acquire_scanner_jobs`
- Add: `src/fitcv/job_sources.py:export_scanner_jobs`
- Add: `src/fitcv/job_sources.py:main`
- Add: `tests/test_job_sources.py`
- Retain as provider-local implementation: `src/fitcv/personio_export.py`
- Retain as provider-local implementation: `src/fitcv/ats_export.py`
- Retain provider-local proof: `tests/test_personio_export.py`
- Retain provider-local proof: `tests/test_ats_export.py`

**Dependencies:**
- Task 1 provides `CanonicalJobs`, `canonicalize_jobs`, and `write_canonical_jobs`.
- Career Ops remains research evidence only; no Node code or runtime enters FitCV.

**Steps:**
- [ ] Step 1: Move existing fixture assertions into `tests/test_job_sources.py`; add request default/bound tests, keyword normalization and Unicode casefold OR matching, `max_jobs`, total-deadline, stable-error, exact-one detection, overlap, canonical-URL, redirect, TLS, query/fragment rejection, and empty standalone export tests before implementation.
- [ ] Step 2: Implement one frozen `ScannerRequest` and one frozen `ProviderDefinition`; use a static `PROVIDERS` mapping containing `personio`, `greenhouse`, and `workday` with display labels, detector, and acquisition callable.
- [ ] Step 3: Implement `build_scanner_request` with provider default `auto`, 200-character company bound, ordered deduplicated keywords, `max_jobs` default/range `50`/`1..200`, and total `timeout_seconds` default/range `60`/`1..120`.
- [ ] Step 4: Make provider URL validation return canonical scheme/host/normalized-path URLs and reject credentials, custom ports, queries, fragments, unsupported hosts, and unsafe redirects before persistence or retrieval.
- [ ] Step 5: Use `time.monotonic()` for one acquisition deadline; cap each standard-library HTTP request at `min(30, remaining_seconds)`; stop provider-internal pagination on source exhaustion, deadline, or `max_jobs`.
- [ ] Step 6: Migrate Personio XML plus same-provider public-page fallback, Greenhouse board API with `content=true`, and Workday CXS plus public-page description retrieval; fail the whole acquisition when a selected job cannot produce required canonical fields.
- [ ] Step 7: Return one canonical artifact plus provider ID and selection mode; keep request values in `ScannerRequest`, and let the control plane add retrieval time when it persists provenance.
- [ ] Step 8: Keep `python -m fitcv.job_sources` as the only unversioned developer export utility that writes the canonical artifact, including `[]`; do not add a `pyproject.toml` console script or public CLI compatibility promise.
- [ ] Step 9: Retain provider-local parser and transport modules with their fixture tests, but remove their duplicate CLI and file-writer behavior.

**Verification:**
- [ ] `uv run pytest tests/test_job_sources.py tests/test_ingest.py -q`
- [ ] `uv run python -m fitcv.job_sources --help`
- Expected: shared and provider-local tests pass; unit proof confirms standalone `[]` export; utility help loads; no duplicate provider CLI or writer remains.

**Exit Criteria:**
- One registry and one request/error contract own all three providers; adding a provider requires provider-owned code, one registry entry, and contract tests only.

### Task 3: Route Every Run Source Through One Snapshot Projection

**Purpose:**
- Make canonical snapshot, empty-run policy, provenance, projection persistence, and enqueue behavior uniform across path, upload, paste, and scanner sources.

**Specification Coverage:**
- One Canonical Job Artifact; Runtime Snapshot Invariance; Source Acquisition Symmetry; Scanner Request Contract; Error Contract; Snapshot and Provenance Separation; Acquisition Is Atomic; Snapshot Owns the Execution Projection; Empty Artifact and Empty Run Are Different Contracts.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/app.py:TriggerRequest`
- Inspect: `src/fitcv_cp/app.py:_resolve_jobs_path_snapshot`
- Inspect: `src/fitcv_cp/app.py:_execute_trigger`
- Modify: `src/fitcv_cp/app.py:_execute_trigger_with_inputs`
- Modify: `src/fitcv_cp/app.py:trigger_run`
- Modify: `src/fitcv_cp/app.py:upload_trigger`
- Add: `src/fitcv_cp/app.py:_materialize_run_jobs_projection`
- Add: `src/fitcv_cp/app.py:_job_source_api_error`
- Modify: `src/fitcv_cp/models.py:PipelineRun.jobs_input_source`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 1 owns canonical artifacts and atomic writes.
- Task 2 owns scanner validation, acquisition, provider options, and stable source error codes.
- Existing candidate-profile, idempotency, configuration, persistence, and enqueue owners remain unchanged.

**Steps:**
- [ ] Step 1: Add failing route tests for JSON path compatibility, multipart upload compatibility, scanner auto/explicit success, request defaults/bounds, each stable 422/502 code, all-source empty rejection, acquisition atomicity, registry-derived providers, canonical provenance, projection bytes, original-source mutation, and enqueue failure.
- [ ] Step 2: Extend `TriggerRequest` with `source_mode` defaulting to `path` and optional scanner fields while preserving existing JSON path requests; pass scanner values to `build_scanner_request` instead of duplicating domain validation.
- [ ] Step 3: Add scanner handling to multipart `POST /runs` while preserving its existing one-file public contract; add scanner handling separately to `/admin/upload-trigger`, where existing candidate-profile and run-name validation remains owned.
- [ ] Step 4: Replace source-specific JSON serialization with `canonicalize_jobs` for JSON path, multipart upload, legacy path/upload/paste, and scanner results; reject empty canonical artifacts before projection persistence with `ApiError(422, "empty_job_input", ...)`.
- [ ] Step 5: Refactor `_execute_trigger` into a path-source wrapper over `_execute_trigger_with_inputs` so configuration, runtime envelope, run persistence, projection, and enqueue logic have one owner.
- [ ] Step 6: Change `_execute_trigger_with_inputs` to accept `CanonicalJobs`, source ID, and manifest data rather than a caller-provided execution path or independently serialized snapshot.
- [ ] Step 7: Generate `run_id`, atomically write `data/uploads/{run_id}_jobs.json` from the canonical artifact, create or merge a provenance manifest containing `canonical_sha256` for every source mode, then persist and enqueue that run-owned path; projection failure creates no run.
- [ ] Step 8: For scanner provenance persist provider ID, selection mode, company name, canonical careers URL, requested keywords, `max_jobs`, `timeout_seconds`, retrieval timestamp, job count, and canonical digest only.
- [ ] Step 9: Map `JobSourceError` codes to the approved 422/502 `ApiError` contract with safe provider/canonical-URL context; never include response bodies or raw query strings.
- [ ] Step 10: Update idempotency fingerprints to use canonical digest, candidate profile ID/revision, run name, and source provenance fields so equivalent retries replay and changed scanner requests conflict.
- [ ] Step 11: Preserve legacy `PipelineRun` schema and update the `jobs_input_source` comment to include `scanner`; no database migration is required.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_app.py -q -k "post_runs or upload_trigger or jobs_input or scanner"`
- Expected: every source stores one canonical snapshot and run-owned projection, empty sources create no run, scanner errors retain approved status/code, and existing path/upload/paste assertions remain green.

**Exit Criteria:**
- Trigger-time acquisition has one artifact owner, one empty policy, one provenance owner, one projection writer, and one enqueue path.

### Task 4: Verify Projection Integrity Before Pipeline Execution

**Purpose:**
- Prevent a changed or mismatched `jobs_path` projection from overriding immutable `jobs_input_json`.

**Specification Coverage:**
- Runtime Snapshot Invariance; Snapshot and Provenance Separation; Snapshot Owns the Execution Projection; Downstream Ownership Preservation; migration and mixed-version invariants.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `src/fitcv_cp/worker_job.py:execute_pipeline_run`
- Add: `src/fitcv_cp/worker_job.py:_verify_jobs_input_projection`
- Modify: `src/fitcv_cp/worker_job.py:execute_pipeline_run`
- Modify: `tests/test_fitcv_cp/test_worker_job.py`

**Dependencies:**
- Task 3 persists canonical snapshot, digest, and run-owned projection before enqueue.
- Existing `run_pipeline(jobs_path=...)` interface remains unchanged.

**Steps:**
- [ ] Step 1: Add failing worker tests for matching bytes, changed projection, missing projection, manifest/snapshot digest mismatch, passed-path versus persisted-path mismatch, and historical runs without `jobs_input_json`.
- [ ] Step 2: Implement `_verify_jobs_input_projection(run_record, jobs_path)` using exact UTF-8 snapshot bytes, `hashlib.sha256`, projection bytes, manifest `canonical_sha256`, and persisted `run_record.jobs_path`.
- [ ] Step 3: Call verification after loading the run record and before `run_pipeline`; preserve legacy path execution only when the run has no `jobs_input_json` snapshot.
- [ ] Step 4: On integrity failure, use existing worker failure terminalization with safe message and `error_stage="jobs_input_integrity"`; do not invoke `run_pipeline` or mutate snapshot/projection.
- [ ] Step 5: Keep cancellation, retry, manual-stage continuation, reuse, and downstream provider-agnostic behavior unchanged.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_worker_job.py -q -k "jobs_input_integrity or projection or legacy_jobs_input"`
- Expected: valid new runs reach `run_pipeline`; projection drift fails before pipeline; historical snapshot-less runs retain current behavior.

**Exit Criteria:**
- Worker treats `jobs_input_json` as runtime truth while preserving the existing path-based pipeline and historical runs.

### Task 5: Add Scanner Mode To Existing Run UI

**Purpose:**
- Let non-technical users create scanner-backed runs without preparing job files.

**Specification Coverage:**
- Non-Technical Scanner Input; Scanner Control-Plane UI; Registry Data Replaces Routing Branches; accessibility and generated-source consistency invariants; Scanner API and UI Share One Request Contract.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/app.py:admin_runs`
- Modify: `src/fitcv_cp/templates/runs_list.html:Trigger Run form`
- Modify: `src/fitcv_cp/templates/runs_list.html:triggerRun`
- Add: `src/fitcv_cp/templates/runs_list.html:setJobsSourceMode`
- Modify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Task 2 provides `list_provider_options`.
- Task 3 provides multipart scanner fields and stable API errors.
- No matching `*.integration.md` exists; production route, template, and tests are authoritative.

**Steps:**
- [ ] Step 1: Add failing render tests proving provider options come from `list_provider_options`, scanner controls exist, upload remains default, and the template contains no copied provider-ID list.
- [ ] Step 2: Pass registry-derived provider options from `admin_runs` template context.
- [ ] Step 3: Add a native source `<select>` with `upload` and `scanner`; keep existing upload controls in one fieldset and add scanner provider, company, careers URL, one-keyword-per-line textarea, `max_jobs`, and `timeout_seconds` controls in a second fieldset.
- [ ] Step 4: Implement `setJobsSourceMode` with native `hidden`, `disabled`, and `required` state so inactive controls never validate or submit; preserve existing candidate-profile, run-name, and config controls.
- [ ] Step 5: Update `triggerRun` to send `source_mode`; send one upload only for upload mode and scanner fields only for scanner mode; append each trimmed keyword line as a repeated `keyword` form field, and read scanner keywords with `form.getlist("keyword")`.
- [ ] Step 6: Reuse existing buttons, form layout, CSS variables, status region, and `fitcvApiRequest`; add no new visual system, dependency, modal, or client-side provider rule.
- [ ] Step 7: On validation failure, render the safe message in the existing live region and focus the first relevant field; keep the submitted mode and values available for correction.
- [ ] Step 8: Verify keyboard order, labels, required-state changes, focus, live-region output, 390x844 and desktop layouts, supported light/dark themes, and reduced-motion behavior with Playwright MCP; use Chrome DevTools MCP only for console or network diagnosis.

**Verification:**
- [ ] `uv run pytest tests/test_fitcv_cp/test_app.py -q -k "admin_runs or runs_list or scanner"`
- [ ] Start source mode with `.\start_web.ps1`, open `http://localhost:8000/admin/runs`, then run Playwright scanner-mode success, validation, keyboard, mobile, desktop, and theme checks.
- Expected: file upload behavior remains intact; scanner mode requires no file; providers are registry-derived; accessible UI submits the shared scanner contract.

**Exit Criteria:**
- Existing run page supports complete upload and scanner flows with one backend contract and no duplicated provider knowledge.

### Task 6: Align Documentation And Run Final Proof

**Purpose:**
- Reconcile user documentation, provider adapter ownership, focused validation, optional live evidence, and final implementation readiness.

**Specification Coverage:**
- Compatibility, Migration, and Risk; Provider Admission and Extension; Documentation Has One Contract Owner; all completion criteria.

**Required Skills:**
- `skill-code-standards`
- `skill-verification-before-completion`

**Files And Symbols:**
- Modify: `docs/job-data-input.md`
- Verify deletion: `src/fitcv/ats_export.py`
- Verify deletion: `src/fitcv/personio_export.py`
- Verify deletion: `tests/test_ats_export.py`
- Verify deletion: `tests/test_personio_export.py`
- Verify: `docs/superpowers/specs/2026-07-24-13-15-fitcv-job-source-option-c-spec.md`
- Verify: `docs/superpowers/plans/2026-07-24-13-59-fitcv-job-source-option-c-plan.md`

**Dependencies:**
- Tasks 1 through 5 complete.
- Live provider smoke checks are external evidence; committed fixture tests remain the deterministic gate.

**Steps:**
- [ ] Step 1: Rewrite `docs/job-data-input.md` around one canonical artifact and four run sources: path, upload, paste, and scanner; retain Apify as an engineering helper not exposed by control plane.
- [ ] Step 2: Document registry-owned V1 providers, auto versus explicit selection, scanner fields/defaults, stable errors, empty standalone export versus empty-run rejection, provenance, run-owned projection, worker digest verification, and provider-extension admission evidence without copying provider IDs into a second authoritative list.
- [ ] Step 3: Search for duplicate exporter entry points and documentation references; keep provider-local implementations private to `fitcv.job_sources`.
- [ ] Step 4: Run focused tests, Ruff, strict changed-source mypy, compile checks, and whitespace checks; fix only regressions caused by this implementation.
- [ ] Step 5: Run template and planning validators; record current unrelated historical template findings and the pre-existing missing `repo_config/planning_artifact_schema.yaml` lifecycle-validator blocker without modifying governance files in this feature.
- [ ] Step 6: Run bounded live exports for the three known representative portals when network access is available, then pass each output through `parse_jobs_file`, `prepare_raw_rows`, and `normalize_batch`; record endpoint, date, count, and description lengths without committing live payloads.
- [ ] Step 7: Run `skill-verification-before-completion`; reconcile every plan task, specification acceptance criterion, known deviation, and final command before changing plan status.

**Verification:**
- [ ] `uv run pytest tests/test_ingest.py tests/test_job_sources.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- [ ] `ruff check src/fitcv/ingest.py src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/worker_job.py tests/test_ingest.py tests/test_job_sources.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py`
- [ ] `mypy src/fitcv/ingest.py src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/worker_job.py`
- [ ] `python -m compileall -q src/fitcv/ingest.py src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/worker_job.py`
- [ ] `git diff --check`
- [ ] `uv run python scripts/validate_template_required_sections.py`
- [ ] `uv run python scripts/validate_planning_lifecycle.py`
- Expected: focused implementation checks pass; new spec and plan produce no template finding; any repository-wide historical findings remain unrelated; lifecycle validation remains externally blocked only while `repo_config/planning_artifact_schema.yaml` is absent.

**Optional Live Evidence Commands:**
- `uv run python -m fitcv.job_sources --provider personio --company "areto consulting" --careers-url https://areto.jobs.personio.de --keyword "data engineer" --max-jobs 3 --timeout-seconds 60 --output .tmp-tests/personio-live.json`
- `uv run python -m fitcv.job_sources --provider greenhouse --company GROPYUS --careers-url https://job-boards.eu.greenhouse.io/gropyus --keyword "data engineer" --max-jobs 3 --timeout-seconds 60 --output .tmp-tests/greenhouse-live.json`
- `uv run python -m fitcv.job_sources --provider workday --company Zalando --careers-url https://zalando.wd3.myworkdayjobs.com/ZalandoSiteWD --keyword "data engineer" --max-jobs 3 --timeout-seconds 60 --output .tmp-tests/workday-live.json`
- `uv run python -c "from pathlib import Path; from fitcv.ingest import parse_jobs_file, prepare_raw_rows; from fitcv.normalize import normalize_batch; paths=list(Path('.tmp-tests').glob('*-live.json')); assert paths; [prepare_raw_rows(parse_jobs_file(path)) for path in paths]; [normalize_batch(parse_jobs_file(path)) for path in paths]; print({path.name: len(parse_jobs_file(path)) for path in paths})"`

**Exit Criteria:**
- Documentation, source, tests, UI proof, provider fixtures, optional live evidence, adapter ownership, and final verification agree with the approved specification.

## Verification

- `uv run pytest tests/test_ingest.py tests/test_job_sources.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py -q`
- `ruff check src/fitcv/ingest.py src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/worker_job.py tests/test_ingest.py tests/test_job_sources.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py`
- `mypy src/fitcv/ingest.py src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/worker_job.py`
- `python -m compileall -q src/fitcv/ingest.py src/fitcv/job_sources.py src/fitcv_cp/app.py src/fitcv_cp/models.py src/fitcv_cp/worker_job.py`
- `git diff --check`
- Playwright MCP: scanner success, stable validation errors, keyboard-only flow, 390x844 mobile, desktop, supported themes, and reduced motion on `http://localhost:8000/admin/runs`.
- Provider-extension proof: add a test-only overlapping detector and a test-only valid provider definition without changing control-plane or pipeline routing code.
- Source-agnostic proof: equivalent path, upload, paste, and scanner jobs produce equal `jobs_input_json`, equal projection bytes, and equal normalized results.
- Known repository validation constraint: `validate_template_required_sections.py` currently reports unrelated historical artifacts, and `validate_planning_lifecycle.py` currently cannot load missing `repo_config/planning_artifact_schema.yaml`; neither condition authorizes changes outside this feature.

## Completion Criteria

The plan is ready for completion verification when:

1. `CanonicalJobs`, one serializer, one digest, and one atomic writer own every new run input
2. Personio, Greenhouse, and Workday use one static registry, one request contract, one error contract, and one canonical boundary
3. path, upload, paste, and scanner runs reject empty jobs uniformly and queue only run-owned projections
4. worker digest verification blocks changed projections while historical snapshot-less runs remain executable
5. existing run UI supports accessible upload and scanner modes with registry-derived provider choices
6. standalone developer export permits `[]` without becoming a public CLI compatibility contract
7. Apify helper, downstream pipeline semantics, candidate-profile flow, run settings, and historical runs remain unchanged
8. provider-local adapters retain only parsing and transport behavior; `fitcv.job_sources` remains the sole registry and standalone exporter
9. documentation and acceptance evidence reference canonical owners without copied schemas or provider routing lists
10. focused tests, lint, types, compilation, whitespace, browser checks, and applicable document checks complete with only classified unrelated repository failures
11. plan deviations, substitutions, external live-check results, and blockers are recorded

The plan may be marked `completed` only when `skill-verification-before-completion` runs fresh final proof, confirms every required outcome against repository evidence, finds no unresolved required task or unrecorded deviation, and returns `verified`.
