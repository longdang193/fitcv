---
doc_id: job-data-input
doc_type: data-contract
explains:
  components:
    - src/fitcv/contracts.py
    - src/fitcv/ingest.py
    - src/fitcv/job_sources.py
    - src/fitcv_cp/app.py
    - src/fitcv_cp/worker_job.py
---

# Job-Data Input

FitCV accepts four run sources: path, upload, paste, and company-portal scanner. Source choice changes acquisition and provenance only. Every source becomes one canonical UTF-8 JSON array before run creation.

## Canonical artifact

`src/fitcv/contracts.py` owns required scraper fields. `src/fitcv/ingest.py` owns validation, deterministic serialization, SHA-256 calculation, and atomic writes.

Each job requires:

- `jobUrl`
- `title`
- `companyName`
- `description`
- `contractType`
- `experienceLevel`

Optional fields remain unchanged. Job order remains unchanged. Standalone scanner export may write `[]`; run creation rejects an empty array with `empty_job_input`.

## Run sources

### Path

JSON file path resolves at trigger time. Original file is acquisition input only; worker never executes it directly.

### Upload

Public run UI accepts one JSON or JSONL file. Legacy admin route may merge multiple files in submitted order.

### Paste

Legacy admin route accepts a pasted JSON array.

### Scanner

Run UI accepts provider selection, company name, canonical HTTPS careers URL, title keywords, maximum jobs, and total timeout. `Auto detect` requires exactly one matching provider. Provider choices come from `src/fitcv/job_sources.py`; UI and API do not copy provider routing rules.

Scanner errors use stable codes:

- input: `invalid_scanner_request`, `unknown_provider`, `unsupported_provider_url`, `ambiguous_provider_url`, `empty_job_input`
- upstream: `provider_timeout`, `provider_http_error`, `provider_payload_error`, `provider_detail_error`

## Snapshot and projection

Successful run creation stores:

- `jobs_input_json`: immutable canonical job truth
- `jobs_input_source`: acquisition mode
- `jobs_input_manifest_json`: provenance and canonical SHA-256 only
- `jobs_path`: run-owned file written from exact `jobs_input_json` bytes

Worker verifies queued path, persisted path, manifest digest, snapshot digest, and projection bytes before pipeline execution. Historical runs without `jobs_input_json` retain legacy path behavior.

## Downstream behavior

Normalize stage still owns snake-case mapping, description cleanup, date parsing, and deduplication. Scanner provider identity does not affect normalization, filtering, ranking, enrichment, or CV generation.

## Apify helper

`fetch_from_apify` in `src/fitcv/ingest.py` remains an engineering helper. It is not a control-plane source mode and is not wired into scanner registry.

## Adding a provider

Add provider-owned detection and acquisition behavior, then one registry entry in `src/fitcv/job_sources.py`. Provider output must pass canonicalization, `prepare_raw_rows`, and normalization tests. No control-plane or pipeline routing branch should be required.
