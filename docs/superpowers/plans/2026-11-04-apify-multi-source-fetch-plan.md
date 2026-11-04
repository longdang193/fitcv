---
artifact_type: plan
template_id: implementation-plan
contract_version: "1"
status: completed
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

`scripts/fetch_jobs.py`
fetches all enabled sources, handles Apify run polling and dataset retrieval,
preserves raw provenance, and atomically writes one canonical JSON array. The
separate dedupe report carries the same run identifier and canonical-output
digest so a partial publication is detectable.

### Symmetric source configuration

JSON input files under
`config/job_sources/`
describe WorkingStudentJobs, LinkedIn, and Indeed with one common envelope.
StepStone has no enabled configuration file in this change.

### Deterministic normalization and deduplication

The orchestrator normalizes source-specific records, removes exact duplicates,
applies a guarded description intersection-rate rule above 90%, and writes
excluded-record provenance to a separate deduplication report.

### Regression and live proof

Focused tests cover configuration, Apify lifecycle failures, all supported
source shapes, normalization, deduplication, and output compatibility. A
A bounded live smoke run starts no more than one constrained search per Apify
source and publishes at most five records per source.

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
- Branch: `main`
- Base commit: `459503c70676c21062e499b6d4b4b27f775a7fa1`
- Expected workspace: `main` with unrelated untracked artifacts preserved and not staged
- Next action: branch finishing after verified publication
- Blockers: `none`; the existing `.env` contains `APIFY_API_TOKEN`, but its value must never enter tracked files or logs

| Task | State | Workspace | Executor | Depends On | Required Proof | Evidence |
| --- | --- | --- | --- | --- | --- | --- |
| Task 1 | `completed` | current | `lead` | none | JSON configuration parse and secret-exclusion check | `14 focused tests; configs parse; no token in tracked diff` |
| Task 2 | `completed` | current | `lead` | Task 1 | source fetcher unit tests and `py_compile` | `15 focused tests; py_compile passed; live actors bounded` |
| Task 3 | `completed` | current | `lead` | Task 2 | normalization and dedupe regression tests | `strict >0.90 tests; FitCV canonicalization passed` |
| Task 4 | `completed` | current | `lead` | Task 3 | full focused suite and output-contract validation | `89 passed, 1 skipped; README and .env.example aligned` |
| Task 5 | `completed` | current | `lead` | Task 4 | bounded live smoke run for three enabled sources | `5 jobs each from WorkingStudentJobs, LinkedIn, Indeed; no StepStone; digest/schema checks passed` |

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
2. Record the validated actor input contracts: LinkedIn `rows` is per search, Indeed `limit` is the actor result cap, and smoke mode must reduce LinkedIn to one title/location pair. Do not add an Apify `maxItems` billing cap unless the selected actor explicitly accepts it; the live LinkedIn actor rejected that parameter with `max-total-charge-usd-below-minimum`.
3. Copy the approved LinkedIn and Indeed payloads under `input` without changing their production limits.
4. Add the symmetric WorkingStudentJobs config with `ref`, `pageSize`, `maxJobs`, filters, and `details.require=true`.
5. Add sanitized source-shape fixtures and exact mapping assertions before source implementation.
6. Add `APIFY_API_TOKEN=your_apify_api_token_here` to `.env.example` and explicitly ignore smoke output paths or place them under an ignored temporary directory.
7. Define the loader rule that an exported environment variable wins over `.env`.

**Verification:**

```powershell
python -c "import json, pathlib; [json.load(open(p, encoding='utf-8')) for p in pathlib.Path('config/job_sources').glob('*.json')]; print('source configs valid')"
git diff --check
git diff -- .env .env.example
```

**Exit Criteria:** all three configs parse, StepStone is absent from the enabled allowlist, actor input contracts are fixture-tested, smoke outputs are ignored, `.env` is not modified by the task, and no credential value appears in the diff.

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
- `scripts/fetch_workingstudentjobs.py:job_to_fitcv_record` — reuse only after a required full detail record is present.
- `scripts/fetch_workingstudentjobs.py:_request_bytes` and `extract_job_posting_json_ld` — own the short strict detail loop in the orchestrator without changing FitCV runtime code.

**Dependencies:** Task 1.

**Authority:**

- **Preauthorized local actions:** create the standalone script, call the three approved source boundaries, poll Apify runs, retrieve datasets, and write only the requested output/report paths.
- **Stop for:** actor authentication failure, unexpected billing or quota response, schema drift that cannot be mapped safely, or any need to modify `src/fitcv`.

**Steps:**

1. Load `.env` without overriding existing process environment variables.
2. Implement CLI selection for `all`, `workingstudentjobs`, `linkedin`, and `indeed`, plus `--config-dir`, `--output`, `--dedupe-report`, `--max-records-per-source`, and bounded `--run-timeout`/`--poll-timeout` settings.
3. Start Apify actors with an Authorization header, a server-side `timeoutSecs`, a recorded run ID, bounded backoff polling, and an overall client deadline. Only `SUCCEEDED` may read the returned `defaultDatasetId`; `FAILED`, `TIMED-OUT`, and `ABORTED` fail. Abort a still-running run when the client deadline expires.
4. Convert actor IDs to the Apify URL form safely, never include the token in URLs or exception messages, and redact authorization-bearing diagnostics.
5. Reuse the existing WorkingStudentJobs pagination and JSON-LD helpers, but require a successful detail-page `JobPosting` description and exclude API structured-summary fallbacks from canonical output.
6. Use a hard `SUPPORTED_SOURCES = ("workingstudentjobs", "linkedin", "indeed")` allowlist; `all` iterates that tuple, never every JSON file in the directory.
7. Preserve `source`, `sourceJobId`, `sourceRecord`, `sourceRunId`, and `sourceDatasetId` on normalized records.
8. Fail clearly for failed runs, malformed dataset responses, missing required descriptions, and unknown source configs; treat empty successful datasets as valid empty results.

**Verification:**

```powershell
python -m py_compile scripts/fetch_jobs.py
python -m pytest tests/test_fetch_jobs.py -q
```

**Exit Criteria:** each enabled source can be selected independently, `--source all` combines only the hard-allowlisted sources, Apify execution has bounded server/client lifetimes, WorkingStudentJobs fallback summaries are excluded, failures are actionable, and output writes atomically as a JSON array.

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

1. Map every source into one LinkedIn-shaped FitCV input contract: `jobUrl` is the listing URL, `applyUrl` is the application URL, `sourceJobId` is the stable upstream identity, and `sourceRecord` preserves the untouched payload. Fill optional fields with empty strings, never invented values.
2. Map LinkedIn `description` first and `descriptionHtml` only when plain text is absent; map Indeed `description.text` or string description, `url` as listing URL, `jobUrl` as application URL, employer/location/date fields, and `key`/`refNum` as identity.
3. Normalize whitespace and HTML for comparison only. Classify descriptions as `full`, `fallback_summary`, `partial`, or `missing`; only `full` records are eligible for canonical output.
4. Apply exact canonical URL and `(source, sourceJobId)` deduplication first.
5. Apply fuzzy comparison only within normalized company/title/location buckets, using set intersection divided by the smaller meaningful-token set, requiring both descriptions to have at least 40 meaningful tokens and a strict similarity `> 0.90`; exactly `0.90` survives.
6. Use fixed source priority `workingstudentjobs`, `linkedin`, `indeed`; select survivors by `(description_status == full, published_at descending with null last, source priority, sourceJobId ascending)` and make ordering independent of input order.
7. Preserve authoritative source IDs and distinct application identities; only remove fuzzy matches after the bucket and strict threshold pass.
8. Write a report object with `runId`, `outputSha256`, retained IDs, and excluded records containing `duplicateOf`, similarity, source identity, and reason. Every reference must resolve to a retained record.

**Verification:**

```powershell
python -m pytest tests/test_fetch_jobs.py -q
python -m pytest tests/test_ingest.py tests/test_normalize.py -q
```

**Exit Criteria:** canonical records pass `validate_job_schema`, listing/application URLs and stable IDs are preserved, incomplete descriptions are excluded, below-threshold and cross-location records remain, above-threshold duplicates are removed deterministically, and every exclusion has resolvable report evidence.

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

1. Add mocked HTTP tests for Apify start, polling, dataset retrieval, every terminal state, client deadline while still running, abort, malformed response, and empty-success cases.
2. Add fixtures covering the live LinkedIn and Indeed field shapes without committing private job data, plus exact canonical serialization and application/listing URL assertions.
3. Add tests for WorkingStudentJobs detail failure, summary fallback exclusion, source identity, mixed-source arrays, deterministic source ordering, same-title separate requisitions, shared boilerplate, different locations, and description-length asymmetry.
4. Add `.env` precedence and secret-redaction tests, a stray StepStone configuration test proving zero StepStone actor calls, and publication tests for output/report digest consistency and write failure handling.
5. Document the `--source all` command, per-source selection, output/report paths, strict description policy, smoke limits, and StepStone exclusion.
6. Run focused and existing regression suites, including relevant upload-path tests where practical.

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
- ignored temporary smoke output paths such as `.tmp/fetch-jobs-smoke/jobs.json` and `.tmp/fetch-jobs-smoke/jobs.dedupe.json` — local verification outputs, never credentials.

**Dependencies:** Task 4.

**Authority:**

- **Preauthorized local actions:** run each enabled actor with a maximum of five records, retrieve WorkingStudentJobs data, validate output, and retain only non-secret local evidence.
- **Stop for:** any actor failure, unexpected cost/quota behavior, non-JSON output, missing full descriptions from LinkedIn/Indeed, or any StepStone invocation.

**Steps:**

1. Create an in-memory/copy smoke configuration: LinkedIn has exactly one title and one location with `rows: 5`; Indeed has `limit: 5`; WorkingStudentJobs has `maxJobs: 5` and `details.require=true`. Do not pass `maxItems` for the validated LinkedIn actor.
2. Run `scripts/fetch_jobs.py --source all --max-records-per-source 5 --run-timeout 120 --poll-timeout 150` against that temporary config.
3. Count actual Apify actor starts and assert no more than one LinkedIn and one Indeed run, no StepStone run, and no more than five retained records per source.
4. Validate every retained record through `validate_job_schema`, canonicalize/normalize it through the existing FitCV boundary, verify complete descriptions, stable IDs, listing/application URLs, and allowed source names.
5. Verify the dedupe report `runId`, `outputSha256`, retained IDs, and duplicate references against the same output.
6. Verify `git status --short` and staged-file checks show no live output, token, or generated secret.

**Verification:**

```powershell
python scripts/fetch_jobs.py --source all --config-dir .tmp/fetch-jobs-smoke/config --output .tmp/fetch-jobs-smoke/jobs.json --dedupe-report .tmp/fetch-jobs-smoke/jobs.dedupe.json --max-records-per-source 5 --run-timeout 120 --poll-timeout 150
python -c "import json, hashlib; jobs=json.load(open('.tmp/fetch-jobs-smoke/jobs.json', encoding='utf-8')); report=json.load(open('.tmp/fetch-jobs-smoke/jobs.dedupe.json', encoding='utf-8')); assert isinstance(jobs, list); assert report['outputSha256'] == hashlib.sha256(open('.tmp/fetch-jobs-smoke/jobs.json', 'rb').read()).hexdigest(); assert all(job['source'] in {'workingstudentjobs','linkedin','indeed'} for job in jobs); assert all(len([j for j in jobs if j['source'] == source]) <= 5 for source in {'workingstudentjobs','linkedin','indeed'}); print(len(jobs), 'jobs;', len(report['excluded']), 'dedupe entries')"
```

**Exit Criteria:** the smoke config starts at most one constrained run per Apify source, all three enabled sources complete within the five-record retained-record bound, output and report share one digest, descriptions are complete, and StepStone is not invoked.

## Verification

### Focused automated proof

- `python -m pytest tests/test_fetch_jobs.py -q`
- `python -m pytest tests/test_fetch_workingstudentjobs.py tests/test_ingest.py tests/test_normalize.py -q`
- `python -m py_compile scripts/fetch_jobs.py scripts/fetch_workingstudentjobs.py`
- `git diff --check`

### Boundary and failure proof

- Mock Apify start, poll, dataset, failed run, timeout, malformed response, and empty-success responses.
- Validate real LinkedIn and Indeed records through the existing schema adapters.
- Validate WorkingStudentJobs detail success and prove structured-summary fallback is excluded from canonical output.
- Confirm environment precedence and token redaction.

### Live proof

- Use the existing `APIFY_API_TOKEN` only through `.env` or the process environment.
- Run LinkedIn and Indeed with a maximum of five records each.
- Run WorkingStudentJobs with a maximum of five records.
- Do not run StepStone.
- Do not commit live output or secrets; smoke artifacts stay under an ignored path.

### Verified Deferral

- The selected LinkedIn actor rejects the Apify `maxItems` run parameter with
  `max-total-charge-usd-below-minimum`; smoke mode therefore constrains one
  title/location search with `rows: 5` and enforces the five-record publication
  cap locally. The generic runner still supports `maxItems` when an actor
  configuration explicitly opts into it.

## Completion Criteria

- `scripts/fetch_jobs.py` exists and supports `workingstudentjobs`, `linkedin`, `indeed`, and `all`.
- The three source configuration files parse and use one common envelope.
- `.env.example` documents `APIFY_API_TOKEN`; no real token is tracked.
- Output remains a FitCV-compatible JSON array and preserves raw provenance.
- Description deduplication uses the guarded `>90%` intersection rule and emits an auditable report.
- StepStone is absent from the enabled source set and is not executed.
- Focused tests, existing regression tests, static checks, and bounded live verification pass.
- Unrelated untracked workspace artifacts remain untouched and unstaged.
