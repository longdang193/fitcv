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

FitCV accepts legacy path and paste inputs plus managed upload and Scan inputs. Acquisition changes provenance only. Every Run stores one canonical UTF-8 JSON array before pipeline execution.

## Canonical artifact

`src/fitcv/contracts.py` owns required scraper fields. `src/fitcv/ingest.py` owns validation, deterministic serialization, SHA-256 calculation, and atomic writes.

Each job requires:

- `jobUrl`
- `title`
- `companyName`
- `description`
- `contractType`
- `experienceLevel`

Optional fields remain unchanged. Source order and each source's job order remain unchanged. A successful Scan may export `[]`; empty Scan output is downloadable but cannot be selected for a Run.

## Run sources

### Path

JSON file path resolves at trigger time. Original file is acquisition input only; worker never executes it directly.

### Upload

Run UI accepts one optional JSON or JSONL file. Legacy admin route may merge multiple files in submitted order.

### Paste

Legacy admin route accepts a pasted JSON array.

### Managed Scan

Tracked companies store verified careers portals once. Scan creation selects one or more active tracked companies plus optional title, location, publication-window, and row-limit filters; users do not re-enter provider IDs or careers URLs.

A successful Scan stores one immutable canonical output and digest. Run UI may select one or more active, successful, non-empty Scan outputs. One uploaded file and ordered Scan outputs are additive: uploaded jobs first, then Scan outputs in selected order. Run creation rejects requests with neither source and records protected Scan provenance atomically.

Provider choices and portal verification remain owned by `src/fitcv/job_sources.py`; managed Scan API, persistence, and UI do not copy provider routing rules. Stable provider failures remain `provider_timeout`, `provider_http_error`, `provider_payload_error`, and `provider_detail_error`.

## Snapshot and projection

Successful run creation stores:

- `jobs_input_json`: immutable canonical job truth
- `jobs_input_source`: `upload`, `scan`, `combined`, or a legacy mode
- `jobs_input_manifest_json`: ordered source provenance and canonical SHA-256
- `jobs_path`: run-owned file written from exact `jobs_input_json` bytes

Selected Scan IDs, source order, and output digests also persist in `run_scan_inputs`. Referenced Scans cannot be deleted. Historical Runs use their copied snapshot and do not depend on current registry or Scan output availability.

Worker verifies queued path, persisted path, manifest digest, snapshot digest, and projection bytes before pipeline execution. Historical runs without `jobs_input_json` retain legacy path behavior.

## Downstream behavior

Normalize stage still owns snake-case mapping, description cleanup, date parsing, and deduplication. Scan provider identity does not affect normalization, filtering, ranking, enrichment, or CV generation.

## Apify helper

`fetch_from_apify` in `src/fitcv/ingest.py` remains an engineering helper. It is not a control-plane source mode and is not wired into scanner registry.

## Adding a provider

Add provider-owned detection and acquisition behavior, then one registry entry in `src/fitcv/job_sources.py`. Provider output must pass canonicalization, `prepare_raw_rows`, and normalization tests. No control-plane or pipeline routing branch should be required.
