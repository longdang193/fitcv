---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: proposed
layer: change
---

# Multi-Source Job Fetch Orchestrator

## Goal

Add a standalone `scripts/fetch_jobs.py` orchestrator that retrieves jobs from
WorkingStudentJobs, the Apify LinkedIn actor, and the Apify Indeed actor; maps
all records into the existing FitCV-compatible JSON-array format; and writes a
deterministic deduplication report. StepStone is explicitly out of scope until
the source can provide complete descriptions.

The implementation must not add a new FitCV runtime function or change FitCV's
pipeline behavior. It may reuse existing standalone downloader helpers and
existing FitCV adapters as read-only implementation dependencies.

## Implementation Outcomes

### Standalone source orchestrator

`C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\scripts\fetch_jobs.py`
fetches all enabled sources, handles Apify run polling and dataset retrieval,
preserves raw provenance, and atomically writes one canonical JSON array.

### Symmetric source configuration

JSON input files under
`C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\config\job_sources\`
describe WorkingStudentJobs, LinkedIn, and Indeed with one common envelope.
StepStone has no enabled configuration file in this change.

### Deterministic normalization and deduplication

The orchestrator normalizes source-specific records, removes exact duplicates,
applies a guarded description intersection-rate rule above 90%, and writes
excluded-record provenance to a separate deduplication report.

### Regression and live proof

Focused tests cover configuration, Apify lifecycle failures, all supported
source shapes, normalization, deduplication, and output compatibility. A
bounded live smoke run uses at most five records per source.

## Execution Approach

- Mode: `inline sequential`
- Coordination: `git-tracked`
- Required skills: `skill-code-standards`, `skill-backend-verification`, `skill-test-driven-development`, `skill-systematic-debugging`, `skill-verification-before-completion`
- Isolation: `current workspace`
- Commit policy: `no commits during execution`
- Preauthorized local actions: edit the listed plan, script, configuration, documentation, and test files; run local tests, static checks, and bounded live Apify smoke probes using the existing `APIFY_API_TOKEN`
- User-approval actions: push, merge, publication, destructive cleanup, changing source scope, increasing live actor limits beyond five, or changing the canonical pipeline contract
- Parallel ownership: none; source configuration, orchestrator, normalization, tests, and documentation are intentionally sequenced
- Sequential fallback: complete configuration and source contract first, then implementation, focused tests, documentation, and final live verification

## Coordination State

- Coordination owner: `single lead controller`
- Coordination schema: `2`
- Branch: `codex/apify-multi-source-fetch`
- Base commit: `f3eb4142e377048bfdade44bdbc21ffd2e19f5b5`
- Expected workspace: `main` with unrelated untracked artifacts preserved and not staged
- Next action: approve and activate Task 1
- Blockers: `none`; the existing `.env` contains `APIFY_API_TOKEN`, but its value must never enter tracked files or logs

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `pending` | current | `unresolved` | none | JSON configuration parse and secret-exclusion check | pending |
| Task 2 | `pending` | current | `unresolved` | Task 1 | source fetcher unit tests and `py_compile` | pending |
| Task 3 | `pending` | current | `unresolved` | Task 2 | normalization and dedupe regression tests | pending |
| Task 4 | `pending` | current | `unresolved` | Task 3 | full focused suite and output-contract validation | pending |
| Task 5 | `pending` | current | `unresolved` | Task 4 | bounded live smoke run for three enabled sources | pending |

## Task Breakdown

### Task 1: Establish source configuration contract

**Purpose:** Create symmetric JSON inputs and document the single Apify credential without changing runtime behavior.

**Task Function:** configuration contract design and validation

**Template Profile:** `unresolved`

**Specification Coverage:** WorkingStudentJobs symmetry, LinkedIn input, Indeed input, StepStone exclusion, centralized `APIFY_API_TOKEN`.

**Required Skills:** `skill-code-standards`

**Files And Symbols:**

- `config/job_sources/workingstudentjobs.json` — new WorkingStudentJobs API and detail-fetch input.
- `config/job_sources/linkedin.json` — new `bebity/linkedin-jobs-scraper` actor input.
- `config/job_sources/indeed.json` — new `valig/indeed-jobs-scraper` actor input.
- `.env.example` — add `APIFY_API_TOKEN` placeholder only.
- `scripts/fetch_jobs.py` — planned config-loading symbols: `load_env_file`, `load_source_config`.

**Dependencies:** none.

**Authority:**

- **Preauthorized local actions:** add the three JSON files and `.env.example` entry; validate JSON; do not modify `.env` contents or add StepStone configuration.
- **Stop for:** missing source input semantics, any request to store a real token in tracked files, or a required change to FitCV runtime contracts.

**Steps:**

1. Add the common config envelope with `source`, `kind`, `input`, and optional `run`, `details`, or `request` settings.
2. Copy the approved LinkedIn and Indeed payloads under `input` without changing their production limits.
3. Add the symmetric WorkingStudentJobs config with `ref`, `pageSize`, `maxJobs`, filters, and detail-fetch policy.
4. Add `APIFY_API_TOKEN=your_apify_api_token_here` to `.env.example`.
5. Define the loader rule that an exported environment variable wins over `.env`.

**Verification:**

```powershell
python -c "import json, pathlib; [json.load(open(p, encoding='utf-8')) for p in pathlib.Path('config/job_sources').glob('*.json')]; print('source configs valid')"
git diff --check
git diff -- .env .env.example
```

**Exit Criteria:** all three configs parse, StepStone is absent, `.env` is not modified by the task, and no credential value appears in the diff.

### Task 2: Implement source fetching and orchestration

**Purpose:** Add the standalone fetch workflow while reusing existing WorkingStudentJobs downloader behavior.

**Task Function:** source integration implementation

**Template Profile:** `unresolved`

**Specification Coverage:** Apify actor lifecycle, dataset retrieval, WorkingStudentJobs API/detail retrieval, source selection, failure handling, atomic output.

**Required Skills:** `skill-code-standards`, `skill-backend-verification`, `skill-systematic-debugging`

**Files And Symbols:**

- `scripts/fetch_jobs.py` — new `main`, `load_env_file`, `load_source_config`, `run_apify_actor`, `fetch_apify_dataset`, `fetch_workingstudentjobs_source`, `fetch_sources`, and `write_json_array` symbols.
- `scripts/fetch_workingstudentjobs.py:build_api_url` — reuse for API URL construction.
- `scripts/fetch_workingstudentjobs.py:fetch_all_jobs` — reuse pagination and exact-source deduplication.
- `scripts/fetch_workingstudentjobs.py:job_to_fitcv_record` — reuse WorkingStudentJobs mapping and full-detail fallback.
- `scripts/fetch_workingstudentjobs.py:extract_job_posting_json_ld` — reuse detail-page extraction.

**Dependencies:** Task 1.

**Authority:**

- **Preauthorized local actions:** create the standalone script, call the three approved source boundaries, poll Apify runs, retrieve datasets, and write only the requested output/report paths.
- **Stop for:** actor authentication failure, unexpected billing or quota response, schema drift that cannot be mapped safely, or any need to modify `src/fitcv`.

**Steps:**

1. Load `.env` without overriding existing process environment variables.
2. Implement CLI selection for `all`, `workingstudentjobs`, `linkedin`, and `indeed`, plus `--config-dir`, `--output`, `--dedupe-report`, and an optional smoke-test result limit.
3. Start Apify actors using the configured JSON input, poll terminal run states, and retrieve dataset items with bounded request timeouts.
4. Convert actor IDs to the Apify URL form safely and never include the token in exception messages.
5. Reuse the existing WorkingStudentJobs functions rather than duplicating its pagination, detail-page, JSON-LD, and atomic-write logic.
6. Preserve `source`, `sourceJobId`, `sourceRecord`, `sourceRunId`, and `sourceDatasetId` on normalized records.
7. Fail clearly for failed runs, malformed dataset responses, and missing required descriptions; treat empty successful datasets as valid empty results.

**Verification:**

```powershell
python -m py_compile scripts/fetch_jobs.py
python -m pytest tests/test_fetch_jobs.py -q
```

**Exit Criteria:** each enabled source can be selected independently, `--source all` combines only the three enabled sources, failures are actionable, and output writes atomically as a JSON array.

### Task 3: Add source normalization and guarded deduplication

**Purpose:** Map LinkedIn and Indeed actor records into the existing FitCV-compatible shape and deduplicate cross-source postings without losing provenance.

**Task Function:** data normalization and correctness implementation

**Template Profile:** `unresolved`

**Specification Coverage:** common output fields, full-description preference, exact deduplication, description intersection rate above 90%, duplicate provenance.

**Required Skills:** `skill-code-standards`, `skill-test-driven-development`

**Files And Symbols:**

- `scripts/fetch_jobs.py` — planned `linkedin_to_fitcv_record`, `indeed_to_fitcv_record`, `normalize_record`, `description_tokens`, `description_intersection_rate`, `deduplicate_records`, and `build_dedupe_report` symbols.
- `tests/test_fetch_jobs.py` — source mapping and deduplication regression cases.
- `src/fitcv/ingest.py:validate_job_schema` — read-only output compatibility validator.
- `src/fitcv/normalize.py:normalize_job` — read-only reference for existing normalization semantics; do not change it in this task.

**Dependencies:** Task 2.

**Authority:**

- **Preauthorized local actions:** implement script-local normalization and dedupe; add focused regression fixtures; preserve existing FitCV behavior.
- **Stop for:** evidence that the canonical output contract requires a FitCV code change, ambiguous duplicate ownership, or a similarity rule that would remove records outside the same safety bucket.

**Steps:**

1. Map LinkedIn fields including plain `description`, `descriptionHtml` fallback, company, location, dates, application URL, and source ID.
2. Map Indeed fields including `description.text` or string description, employer, location, dates, listing URL, application URL, and `key`/`refNum`.
3. Normalize whitespace, HTML, case, and punctuation before description tokenization.
4. Apply exact URL and `(source, sourceJobId)` deduplication first.
5. Apply description comparison only within normalized company/title/location buckets, requiring more than `0.90` token intersection and at least 40 meaningful tokens.
6. Prefer complete descriptions, then newest postings, then deterministic source order.
7. Write excluded records to the dedupe report with `duplicateOf`, similarity, source identity, and reason.

**Verification:**

```powershell
python -m pytest tests/test_fetch_jobs.py -q
python -m pytest tests/test_ingest.py tests/test_normalize.py -q
```

**Exit Criteria:** LinkedIn, Indeed, and WorkingStudentJobs records pass `validate_job_schema`; descriptions remain complete; below-threshold records remain; above-threshold duplicates are removed with report evidence.

### Task 4: Complete focused regression proof and documentation

**Purpose:** Make the new standalone workflow reproducible and protect its contracts with tests and usage documentation.

**Task Function:** test-driven integration and documentation

**Template Profile:** `unresolved`

**Specification Coverage:** regression proof, CLI usage, configuration ownership, output contract, StepStone boundary.

**Required Skills:** `skill-test-driven-development`, `skill-backend-verification`, `skill-verification-before-completion`

**Files And Symbols:**

- `tests/test_fetch_jobs.py` — all new unit and integration-boundary tests.
- `tests/fixtures/` — minimal sanitized source-shape fixtures if needed.
- `README.md` — standalone orchestrator usage and source configuration notes.
- `.env.example` — documented `APIFY_API_TOKEN` placeholder.

**Dependencies:** Task 3.

**Authority:**

- **Preauthorized local actions:** add focused tests, sanitized fixtures, and documentation; run all relevant local checks.
- **Stop for:** unrelated test failures, generated-surface changes outside the listed files, or documentation that contradicts source/test behavior.

**Steps:**

1. Add mocked HTTP tests for Apify start, polling, dataset retrieval, failure, timeout, and empty-success cases.
2. Add fixtures covering the live LinkedIn and Indeed field shapes without committing private job data.
3. Add `.env` precedence and secret-redaction tests.
4. Document the `--source all` command, per-source selection, output/report paths, and StepStone exclusion.
5. Run focused and existing regression suites.

**Verification:**

```powershell
python -m pytest tests/test_fetch_jobs.py tests/test_fetch_workingstudentjobs.py tests/test_ingest.py tests/test_normalize.py -q
python -m py_compile scripts/fetch_jobs.py scripts/fetch_workingstudentjobs.py
git diff --check
```

**Exit Criteria:** focused tests pass, existing tests remain green, documentation matches the implementation, and no secret or live job export is tracked.

### Task 5: Run bounded live smoke verification

**Purpose:** Prove the real source boundaries and final output with the configured token while keeping actor usage bounded.

**Task Function:** live backend verification

**Template Profile:** `unresolved`

**Specification Coverage:** real Apify actor execution, WorkingStudentJobs boundary, normalized output, StepStone exclusion.

**Required Skills:** `skill-backend-verification`, `skill-systematic-debugging`, `skill-verification-before-completion`

**Files And Symbols:**

- `scripts/fetch_jobs.py:main` — bounded live invocation.
- `config/job_sources/*.json` — temporary smoke-test limit overrides only; production config values remain unchanged.
- `data/jobs.json` and `data/jobs.dedupe.json` — local verification outputs, never credentials.

**Dependencies:** Task 4.

**Authority:**

- **Preauthorized local actions:** run each enabled actor with a maximum of five records, retrieve WorkingStudentJobs data, validate output, and retain only non-secret local evidence.
- **Stop for:** any actor failure, unexpected cost/quota behavior, non-JSON output, missing full descriptions from LinkedIn/Indeed, or any StepStone invocation.

**Steps:**

1. Run LinkedIn with `rows: 5`.
2. Run Indeed with `limit: 5`.
3. Run WorkingStudentJobs with `maxJobs: 5` and detail fetching enabled.
4. Run `scripts/fetch_jobs.py --source all` against those bounded inputs.
5. Validate that the final output is a JSON array and every retained record passes `validate_job_schema`.
6. Verify that the dedupe report accounts for excluded duplicates and that no StepStone actor was called.

**Verification:**

```powershell
python scripts/fetch_jobs.py --source all --config-dir config/job_sources --output data/jobs.json --dedupe-report data/jobs.dedupe.json
python -c "import json; jobs=json.load(open('data/jobs.json', encoding='utf-8')); report=json.load(open('data/jobs.dedupe.json', encoding='utf-8')); assert isinstance(jobs, list); assert isinstance(report, list); print(len(jobs), 'jobs;', len(report), 'dedupe entries')"
```

**Exit Criteria:** all three enabled sources complete successfully within the five-record bound, output validates, descriptions are complete for LinkedIn/Indeed/WorkingStudentJobs detail records, and StepStone is not invoked.

## Verification

### Focused automated proof

- `python -m pytest tests/test_fetch_jobs.py -q`
- `python -m pytest tests/test_fetch_workingstudentjobs.py tests/test_ingest.py tests/test_normalize.py -q`
- `python -m py_compile scripts/fetch_jobs.py scripts/fetch_workingstudentjobs.py`
- `git diff --check`

### Boundary and failure proof

- Mock Apify start, poll, dataset, failed run, timeout, malformed response, and empty-success responses.
- Validate real LinkedIn and Indeed records through the existing schema adapters.
- Validate WorkingStudentJobs detail fallback and structured-summary fallback.
- Confirm environment precedence and token redaction.

### Live proof

- Use the existing `APIFY_API_TOKEN` only through `.env` or the process environment.
- Run LinkedIn and Indeed with a maximum of five records each.
- Run WorkingStudentJobs with a maximum of five records.
- Do not run StepStone.
- Do not commit live output or secrets.

## Completion Criteria

- `scripts/fetch_jobs.py` exists and supports `workingstudentjobs`, `linkedin`, `indeed`, and `all`.
- The three source configuration files parse and use one common envelope.
- `.env.example` documents `APIFY_API_TOKEN`; no real token is tracked.
- Output remains a FitCV-compatible JSON array and preserves raw provenance.
- Description deduplication uses the guarded `>90%` intersection rule and emits an auditable report.
- StepStone is absent from the enabled source set and is not executed.
- Focused tests, existing regression tests, static checks, and bounded live verification pass.
- Unrelated untracked workspace artifacts remain untouched and unstaged.
