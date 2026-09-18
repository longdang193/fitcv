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

LinkedIn-shaped upload records require:

- `jobUrl`
- `title`
- `companyName`
- `description`
- `contractType`
- `experienceLevel`

Indeed scraper uploads use their raw source shape instead. They require:

- `url`
- `title`
- `description`

Indeed `employer`, `location`, and `jobTypes` fields remain source-specific
optional fields at ingress. `canonicalize_jobs` preserves these raw records;
the normalize stage maps them into the existing snake-case pipeline shape.

Stepstone search exports use the same adapter boundary. Detection uses record
shape, not filename. The adapter maps `id`, `url`, `title`, `companyName`,
`datePosted`, `location`, `textSnippet`, and `workFromHome` into the canonical
shape, resolves relative URLs against `https://www.stepstone.de`, strips the
`rltr` tracking query, and preserves the full source record in `raw_json`.
`textSnippet` is marked `description_source: text_snippet` and
`description_complete: false`; such jobs remain visible as review-required and
do not enter CV generation. Stepstone-only fields such as benefits, labels,
skills, and raw work-from-home codes remain owned by `raw_json`.

Optional fields remain unchanged. Source order and each source's job order remain unchanged.

## Run sources

### Path

JSON file path resolves at trigger time. Original file is acquisition input only; worker never executes it directly.

### Upload

Run UI accepts one optional JSON or JSONL file. Legacy admin route may merge multiple files in submitted order.

### Paste

Legacy admin route accepts a pasted JSON array.

### Managed Scan

Managed Scan fetches jobs from verified ATS careers portals through the
operator-curated catalog.

#### Lifecycle

1. **Catalog**: Operators maintain company records in
   `config/scan_catalog.yaml`. Only trackable records can be tracked.
2. **Track**: Users track companies once in Company Catalog. Provider IDs and
   careers URLs come from the catalog; users do not re-enter them.
3. **Create Scan**: Users select one or more tracked companies and may set
   title, location, publication-window, and row-limit filters.
4. **Review**: A successful Scan stores one immutable canonical JSON output and
   digest. Users can review the result and provider diagnostics.
5. **Run**: Run UI accepts one or more successful, non-empty Scan outputs.
   Uploaded jobs and selected Scan outputs combine in order: upload first, then
   Scans in selected order.

#### Empty, quarantined, and historical data

- **Empty Scan**: A successful Scan may contain `[]`. It remains downloadable,
  but cannot be selected as Run input.
- **Quarantined or discovery-only company**: The company remains visible for
  audit, but cannot be tracked or scanned.
- **Run history**: Run creation copies canonical jobs and source provenance
  into the Run snapshot. Historical Runs do not depend on current catalog
  entries or Scan output availability.
- **Provider failure**: Stable error codes are `provider_timeout`,
  `provider_http_error`, `provider_payload_error`, and
  `provider_detail_error`.

Run creation rejects requests with neither source and records protected Scan
provenance atomically.

Provider choices and portal verification remain owned by `src/fitcv/job_sources.py`; managed Scan API, persistence, and UI do not copy provider routing rules.

## External career tools

FitCV can be used alongside tools such as
[career-ops](https://github.com/career-ops-hq/career-ops) for job discovery,
portal scanning, or application tracking. FitCV does not currently provide a
dedicated career-ops adapter or shared synchronization layer; external job
data must use a supported input path and retain its source provenance.

## Snapshot and projection

Successful run creation stores:

- `jobs_input_json`: immutable canonical job truth
- `jobs_input_source`: `upload`, `scan`, `combined`, or a legacy mode
- `jobs_input_manifest_json`: ordered source provenance and canonical SHA-256
- `jobs_path`: run-owned file written from exact `jobs_input_json` bytes

Selected Scan IDs, source order, and output digests also persist in `run_scan_inputs`. Referenced Scans cannot be deleted. Historical Runs use their copied snapshot and do not depend on current registry or Scan output availability.

Worker verifies queued path, persisted path, manifest digest, snapshot digest, and projection bytes before pipeline execution. Historical runs without `jobs_input_json` retain legacy path behavior.

## Downstream behavior

Normalize stage still owns snake-case mapping, description cleanup, date parsing, and deduplication. Source identity is canonicalized as `source_provider` plus `source_job_id` before URL fallback. Provider identity does not create source-specific downstream branches.

## Apify helper

`fetch_from_apify` in `src/fitcv/ingest.py` remains an engineering helper. It is not a control-plane source mode and is not wired into scanner registry.

## Adding a provider

Add provider-owned detection and acquisition behavior, then one registry entry in `src/fitcv/job_sources.py`. Provider output must pass canonicalization, `prepare_raw_rows`, and normalization tests. No control-plane or pipeline routing branch should be required.
