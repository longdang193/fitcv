---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-job-source-option-c
targets:
  - src/fitcv/contracts.py
  - src/fitcv/ingest.py
  - src/fitcv/job_sources.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/models.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/templates/runs_list.html
  - tests/test_job_sources.py
  - tests/test_ingest.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - docs/job-data-input.md
related_features:
  - cv_system
  - trigger_run_management
related_stages:
  - normalize
---

# FitCV Job Source Option C

## Goal and Problem

### Problem

FitCV currently accepts job artifacts through file-backed and text-backed input modes and preserves a canonical run-scoped JSON snapshot. A scanner adds a new acquisition mechanism, but the scanner must not become a second ingestion contract or a parallel pipeline.

The audited Career Ops scanner demonstrates a useful provider registry and uniform `detect`/`fetch` shape, but its configured-company scanner is not an admissible FitCV boundary because it also owns filtering, blacklist decisions, deduplication, trust scoring, liveness checks, history, health state, and Markdown persistence. Its provider job contract also guarantees fewer semantic fields than FitCV requires, and several relevant providers omit job descriptions.

The current isolated spike proves that Personio, Greenhouse, and Workday can produce pipeline-compatible FitCV JSON when provider-specific payloads are adapted and descriptions are retrieved at the provider boundary. Separate provider-local parser and transport modules are acceptable implementation details, but separate registries, request contracts, file writers, or standalone exporter entry points would create asymmetric ownership as providers expand.

- current behavior or opportunity: add direct company-portal acquisition without changing downstream FitCV behavior
- affected users, systems, or maintainers: non-technical users starting runs, provider maintainers, control-plane maintainers, and pipeline consumers
- evidence:
  - `src/fitcv/contracts.py` owns required scraper fields and camelCase-to-snake_case mapping
  - `src/fitcv/ingest.py` owns file parsing, schema validation, and raw-row preparation
  - `src/fitcv_cp/app.py` owns trigger-time source resolution and immutable `jobs_input_json` snapshots
  - live Personio, Greenhouse, and Workday spike outputs pass existing parse, schema, raw-row, and normalize contracts
  - Career Ops commit `01bf8b469ad5177a9c30230bc00509ead8e006c2` confirms provider registry value but scanner-orchestration incompatibility
- consequence of no change: each provider or input mode can acquire, validate, serialize, filter, or persist jobs differently; adding providers can silently alter routing and create multiple sources of truth

### Goal

Define one source-agnostic job artifact contract and one provider-extension boundary so path, upload, paste, managed Scan output, explicit-provider, and auto-detected-provider cases produce the same canonical runtime input and use the same downstream pipeline. Managed Scan API, persistence, errors, state transitions, and UI behavior are owned by `docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md`.

- desired outcome: source selection changes acquisition and provenance only; provider selection changes boundary retrieval only
- observable success:
  - every accepted run source produces a non-empty canonical JSON array validated by the same job artifact contract
  - equivalent ordered job records produce the same `jobs_input_json` independent of source mode
  - adding an admissible provider requires one provider implementation, one registry entry, and provider contract evidence; control-plane and pipeline behavior remain unchanged
  - no Career Ops history, filtering, persistence, or user-state semantics enter FitCV

## Required Outcomes

### Outcome: One Canonical Job Artifact

- affected actor or system: ingest, control plane, worker, and pipeline stages
- required result: all acquisition modes resolve to one ordered list of FitCV job objects and one canonical JSON snapshot
- success condition: downstream code cannot distinguish path, upload, paste, or scanner inputs except through provenance metadata

### Outcome: One Provider Registry

- affected actor or system: managed Scan executor and provider maintainers
- required result: provider identity, detection, and acquisition are defined once in a deterministic registry
- success condition: no provider-specific routing branch exists outside the provider owner

### Outcome: Boundary Adaptation

- affected actor or system: Personio, Greenhouse, Workday, and future provider implementations
- required result: native XML, JSON, HTML, dates, URLs, and provider labels are converted to the FitCV job shape before leaving the provider boundary
- success condition: ingest receives no provider-native payload shape and performs no provider detection

### Outcome: Runtime Snapshot Invariance

- affected actor or system: run creation, replay, inspection, persistence, and worker execution
- required result: `jobs_input_json` remains the immutable run-scoped job truth for every source mode; `jobs_path` is only a verified run-owned execution projection
- success condition: changing the original source or the projection cannot silently change executed jobs, and provenance changes do not change job semantics

### Outcome: Non-Technical Scanner Input

- affected actor or system: users creating managed Scans and later selecting Scan output for a Run
- required result: users select tracked companies and retrieval filters without re-entering provider IDs or careers URLs
- success condition: a user can create, inspect, download, and reuse a Scan output without preparing an Apify-format file

### Outcome: Safe and Permanent Provider Expansion

- affected actor or system: maintainers adding providers
- required result: adding a detector cannot silently reroute an existing URL, and unsupported or ambiguous inputs fail before retrieval
- success condition: auto-detection accepts exactly one match; zero and multiple matches produce stable errors

### Outcome: Native, Minimal Runtime

- affected actor or system: packaging, local execution, and maintenance
- required result: provider implementations use Python standard-library URL, HTTP, JSON, XML, HTML, date, file, and atomic-write facilities where they satisfy the provider contract
- success condition: no crawler framework, dynamic plugin system, Node sidecar, service, queue, or provider class hierarchy is required for the initial supported providers

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| Where is the current FitCV job shape owned? | Required scraper fields and canonical field mapping are centralized. | `src/fitcv/contracts.py` | high | Provider output must consume this owner rather than duplicate required-field lists. |
| Where is runtime parsing owned? | File parsing, field validation, raw-row preparation, and Apify acquisition live in ingest. | `src/fitcv/ingest.py` | high | A shared canonicalization entrypoint belongs with the job artifact boundary. |
| What is the run-scoped truth? | Trigger paths preserve canonical job JSON in `jobs_input_json` and source metadata separately. | `src/fitcv_cp/app.py`, `src/fitcv_cp/models.py` | high | Scanner output must enter this existing snapshot path. |
| Can current target providers produce usable FitCV input? | Live Personio, Greenhouse, and Workday exports passed schema, raw-row preparation, and normalization with non-empty descriptions. | isolated spike and focused tests | high | These three providers are admissible initial implementations. |
| Can Career Ops `scan.mjs` be reused as the artifact boundary? | It combines acquisition with filtering, user state, deduplication, verification, and persistence. | audited Career Ops `scan.mjs` at commit `01bf8b4` | high | Do not invoke or port scanner orchestration into FitCV. |
| Is the Career Ops provider pattern useful? | Provider registry uses deterministic loading and a shared `detect`/`fetch` contract with provider-local URL validation. | audited Career Ops `providers/_registry.mjs`, `_types.js`, provider modules | high | Reuse the pattern and security lessons, not the stateful runtime. |
| Does Career Ops provider output satisfy FitCV? | Its minimum shape omits FitCV-required semantic fields, and Personio, Greenhouse, and Workday listing providers omit descriptions. | audited Career Ops provider modules | high | FitCV providers must adapt and hydrate before returning jobs. |

### Target Pipeline

1. managed Scan resolves tracked-company snapshots to provider requests
2. each provider retrieves and adapts native data to canonical FitCV job objects
3. shared canonical artifact boundary validates top-level shape, item shape, and fields owned by `src/fitcv/contracts.py`
4. shared serializer produces one immutable Scan output while preserving job order
5. Run creation selects upload or one-or-many usable Scan outputs and copies canonical bytes into immutable `jobs_input_json`
6. control plane stores source provenance separately in `jobs_input_manifest_json` and writes the same bytes to a run-owned `jobs_path` projection
7. worker verifies the projection digest against the immutable Run snapshot before executing existing ingest, raw-row preparation, normalize, deduplication, ranking, and CV stages unchanged

Provider and source differences end at step 3. No later stage detects provider, reads provider-native data, or changes semantics from provenance.

### Scope

- included behavior:
  - one job-source module owning provider registry, detection, acquisition, and provider-boundary adaptation
  - one canonical job artifact validation and serialization path
  - explicit provider selection and automatic provider detection
  - Personio, Greenhouse, and Workday as initial admissible providers
  - provider use through the managed Scan executor and one runtime function
  - downloadable managed Scan output using the same acquisition and canonicalization function
  - provenance capture without alternate runtime truth
- affected boundaries:
  - provider URL and request validation
  - external HTTP/XML/JSON/HTML responses
  - job artifact validation and canonical serialization
  - control-plane source resolution
  - run snapshot and manifest construction
- admissible cases:
  - existing path, upload, and paste inputs accepted by current contracts
  - internal provider requests built from tracked-company snapshots with a supported explicit provider
  - internal automatic provider resolution whose URL matches exactly one registered provider
  - provider responses that can be fully adapted to the current FitCV required-field contract
- compatibility expectation:
  - existing accepted job files remain accepted
  - existing pipeline stage order, normalization, deduplication, ranking, and CV behavior remain unchanged
  - existing immutable run snapshots remain readable

### Non-Goals

- executing or embedding Career Ops `scan.mjs`
- importing Career Ops pipeline, scan history, blacklist, trust scoring, liveness state, or Markdown artifacts
- supporting every Career Ops provider in the initial implementation
- broad web search, browser crawling, job-board crawling, or country-wide discovery
- runtime-installed provider plugins
- a separate scanner service, database, queue, scheduler, or Docker deployment
- automatic cross-provider fallback
- company-registry persistence or administration UI, which remains a separate contract
- wiring the existing `fetch_from_apify` helper into the control plane
- changing downstream normalization or deduplication semantics
- strengthening existing uploaded-file semantic requirements beyond the current canonical contract

### Requirements and Behavioral Contract

#### Requirement: Canonical Job Artifact

- trigger or actor: any job acquisition mode
- preconditions: acquisition produced an in-memory value
- required behavior:
  - the value must be a list
  - every item must be an object
  - every item must contain fields required by `REQUIRED_SCRAPER_FIELDS`
  - provider adapters must use canonical camelCase FitCV field names at this boundary
  - canonicalization must use one shared serializer and preserve input job order
  - provider-specific optional fields may remain when JSON-compatible and must not replace canonical fields
- output or state change: one canonical JSON array and the equivalent in-memory job list
- failure behavior: malformed top-level or item-level values fail before run creation; no partial snapshot is written
- observable acceptance: the same ordered records acquired through different modes serialize to equal `jobs_input_json`

#### Requirement: Source Acquisition Symmetry

- trigger or actor: path, upload, paste, or scanner source mode
- preconditions: source-specific parameters are present and valid
- required behavior:
  - source mode may read bytes, parse text, call an external API, or invoke provider acquisition
  - source mode must then hand the resulting job list to the same canonicalization path
  - source mode must not define separate required fields, normalization, deduplication, or downstream defaults
- output or state change: canonical jobs plus source provenance
- failure behavior: source acquisition failure prevents successful Scan output and leaves no runnable partial snapshot
- observable acceptance: downstream worker input and pipeline behavior are invariant for equivalent ordered records

#### Requirement: Provider Registry SSOT

- trigger or actor: managed Scan executor or provider-focused internal tooling
- preconditions: provider registry is loaded from the FitCV code version being executed
- required behavior:
  - registry keys are unique provider IDs
  - each provider definition supplies one URL detector and one acquisition callable
  - registry insertion order must not decide ambiguous routing
  - provider-specific routing conditions may exist only inside the provider owner
  - no provider ID is duplicated in tracked-company provider choices, internal tooling, validation lists, or control-plane branches; consumers derive choices from the registry
- output or state change: selected provider definition
- failure behavior: duplicate provider IDs are impossible in the static registry; unknown explicit IDs fail validation
- observable acceptance: adding a provider does not require modifying routing consumers

#### Requirement: Provider Resolution Permanence

- trigger or actor: explicit or automatic provider selection
- preconditions: internal provider request contains company name and HTTPS careers URL from a tracked-company snapshot
- required behavior:
  - explicit selection resolves exactly the named provider and still validates the URL through that provider
  - automatic selection evaluates every registered detector without fetching
  - zero matches produce an unsupported-provider error
  - one match selects that provider
  - multiple matches produce an ambiguous-provider error containing matching provider IDs
  - automatic selection never chooses the first match silently
- output or state change: one selected provider or a validation failure
- failure behavior: no network request occurs after unsupported or ambiguous resolution
- observable acceptance: registering a new overlapping detector cannot change existing successful routing into a different provider; it changes it into an explicit ambiguity failure

#### Requirement: Provider Acquisition Request Contract

- trigger or actor: managed Scan executor builds one provider request from an immutable tracked-company snapshot
- preconditions: Scan request and company selection satisfy the managed Scan contract
- required behavior:
  - `provider` defaults to `auto`; explicit values are registry provider IDs
  - `company_name` and `careers_url` come from the tracked-company snapshot, not ordinary user input
  - `careers_url` is an absolute provider-approved HTTPS URL without credentials, custom port, query, or fragment
  - `keywords` is an ordered list of trimmed non-empty title filters; duplicates are removed while preserving order; an empty list means all titles
  - keyword matching is case-insensitive Unicode substring OR matching against title; providers may use native search but must apply this rule before returning jobs
  - `locations` is an ordered list of trimmed non-empty location filters; duplicates are removed while preserving order; an empty list means all locations
  - location matching is case-insensitive Unicode substring OR matching against canonical location
  - `published_since` is an optional inclusive calendar date; jobs without a parseable publication date do not match when it is present
  - `max_jobs` is the remaining managed Scan output allowance and must be an integer from 1 through 200
  - `timeout_seconds` comes from central scanner configuration, not ordinary user input, and must remain within 1 through 120
  - each provider request uses no more than the smaller of 30 seconds or the remaining total deadline
  - provider pagination is internal and stops when `max_jobs`, source exhaustion, cancellation, or the total deadline is reached
- output or state change: one validated internal provider request independent of provider-native pagination
- failure behavior: invalid tracked-company or central configuration fails before provider network access
- observable acceptance: every managed Scan company uses the same internal request builder and provider behavior

#### Requirement: Managed Scan Boundary

- trigger or actor: non-technical user creates a Scan, then later creates a Run
- preconditions: tracked-company registry and Scans workspace are available
- required behavior:
  - users select one, multiple, or all valid tracked companies and never re-enter careers URLs per Scan
  - Scan output is one immutable canonical JSON array and may be `[]`
  - Run creation offers Upload or Output from Scan and accepts one or more active successful non-empty Scan outputs
  - provider choice, acquisition status, archive state, output download, Run references, UI actions, errors, and state transitions follow the managed Scan lifecycle specification
  - accessibility behavior follows the existing control-plane UI contract
- output or state change: successful acquisition creates an inspectable Scan artifact; later Run creation copies selected output into the existing Run snapshot
- failure behavior: failed or cancelled Scan remains inspectable and creates no Run; empty successful Scan remains downloadable but unusable for Run creation
- observable acceptance: a keyboard-only user can complete Scan creation, inspect progress, download output, and select usable Scan output for a Run

#### Requirement: Uniform Provider Acquisition

- trigger or actor: selected provider
- preconditions: request validation and provider resolution succeeded
- required behavior:
  - every provider receives the validated Scanner Request Contract
  - every provider returns a list of canonical FitCV job objects
  - provider-native list responses, detail responses, XML nodes, HTML metadata, relative dates, and URLs are adapted inside the provider
  - provider implementation may use multiple internal retrieval steps when required to produce its canonical result
  - provider implementation must not write files, mutate run state, filter against applications, or deduplicate against persistent history
  - providers return at most `max_jobs` accepted jobs and enforce shared title, location, and publication-date semantics after canonical adaptation
- output or state change: canonical job list
- failure behavior:
  - list-level transport or payload failure fails the acquisition
  - failure to obtain a required canonical field for a selected job fails the acquisition rather than silently inventing content
  - a valid provider response with no matching jobs returns an empty list
- observable acceptance: all admitted providers satisfy one shared contract test and can pass existing ingest and normalize boundaries

#### Requirement: Initial Provider Semantics

- trigger or actor: Personio, Greenhouse, or Workday acquisition
- preconditions: provider-specific validated HTTPS URL
- required behavior:
  - Personio uses the public XML feed for listings and preserves feed descriptions; when the feed omits description content, it may use the public server-rendered job page within the same provider boundary
  - Greenhouse uses the public board API with content enabled so description content is acquired without per-job browser automation
  - Workday uses the public CXS listing endpoint and public job-page metadata for descriptions when detail JSON is unavailable
  - all three convert publication values to ISO calendar dates and map provider fields to the same FitCV keys
  - experience level may be derived from the title through one shared deterministic title rule
- output or state change: complete FitCV jobs suitable for current pipeline stages
- failure behavior: invalid tenant/board URL, untrusted redirect, invalid payload, or unavailable required description fails with provider and URL context
- observable acceptance: representative fixtures and live checks produce non-empty descriptions and zero canonical schema errors

#### Requirement: Native and Secure Transport

- trigger or actor: provider HTTP request
- preconditions: provider validated the requested URL
- required behavior:
  - use standard-library URL parsing and request facilities where they satisfy the provider
  - reject URL credentials, unexpected custom ports, query strings, and fragments
  - require HTTPS for supported public providers
  - constrain provider hosts through explicit allowlists or anchored hostname patterns
  - provider validation returns one canonical scheme, host, and normalized-path URL used by acquisition, canonical job fields, errors, and provenance
  - disable redirects when a redirect could escape the trusted provider host
  - keep TLS certificate verification enabled
  - augment the platform trust store with the declared current CA bundle when required; never use an unverified SSL context
  - apply the shared total acquisition deadline, per-request cap, result limit, and provider-internal bounded pagination
  - do not record secrets, authorization headers, or complete exception bodies in provenance
- output or state change: verified provider response or contextual failure
- failure behavior: timeout, TLS failure, redirect, HTTP failure, and malformed response preserve original cause
- observable acceptance: security-focused tests reject non-HTTPS, credentials, custom ports, untrusted hosts, and redirects

#### Requirement: Error Contract

- trigger or actor: internal provider acquisition during managed Scan execution
- preconditions: provider acquisition or validation fails
- required behavior:
  - internal request errors use stable codes `invalid_scanner_request`, `unknown_provider`, `unsupported_provider_url`, or `ambiguous_provider_url`
  - upstream acquisition errors use stable codes `provider_timeout`, `provider_http_error`, `provider_payload_error`, or `provider_detail_error`
  - managed Scan persists the stable code, safe message, retryability, and action; HTTP mapping is owned by the managed Scan API contract
  - UI presentation preserves stable code and actionable message without exposing unsafe response bodies
- output or state change: Scan becomes failed and stores no canonical output or Run
- failure behavior: original exception cause is preserved; provider and safe URL context are included
- observable acceptance: equivalent provider failures have the same stable code and safe contextual message independent of provider entry point

#### Requirement: Snapshot and Provenance Separation

- trigger or actor: successful managed Scan output and later Run creation
- preconditions: canonical job list exists and satisfies the managed Scan output contract
- required behavior:
  - successful Scan stores one immutable canonical output and digest, including `[]`
  - `jobs_input_json` stores the complete canonical JSON array and remains the only run-time job truth
  - `jobs_input_source` records upload or Scan acquisition mode
  - `jobs_input_manifest_json` records provenance only
  - Scan provenance contains ordered Scan IDs, output digests, record counts, and selection order; provider and company provenance remains owned by Scan snapshots
  - provenance must not contain duplicate job payloads or secrets
  - every run source atomically writes a run-owned execution projection from the exact canonical JSON string stored in `jobs_input_json`
  - worker verifies the projection SHA-256 digest against the stored canonical digest before pipeline execution
  - Scan download returns the same canonical bytes and may return `[]`; mandatory public CLI parity is not required
- output or state change: one immutable Scan output, one immutable Run snapshot when used, one provenance manifest, and one verified run-owned execution projection
- failure behavior: projection persistence or digest mismatch prevents pipeline execution; no mismatched file and snapshot pair is accepted
- observable acceptance: projection bytes equal `jobs_input_json` encoded as UTF-8; changing or deleting the original source after trigger does not change executed jobs

#### Requirement: Downstream Ownership Preservation

- trigger or actor: successful canonical input resolution
- preconditions: run enters existing pipeline
- required behavior:
  - normalization remains owned by existing normalize logic
  - exact and near-duplicate handling remains owned by existing normalize logic
  - ranking, enrichment, filtering, and CV generation receive no scanner-specific branch
  - Career Ops title, location, salary, content, blacklist, trust, history, cooldown, and liveness policies are not imported
- output or state change: existing stage behavior over a new source mode
- failure behavior: implementation is incomplete if any downstream stage reads provider ID to change semantics
- observable acceptance: source scans find no provider-specific pipeline branch outside acquisition and provenance presentation

#### Requirement: Provider Admission and Extension

- trigger or actor: maintainer proposes another provider
- preconditions: public retrieval method and provider boundary are understood
- required behavior:
  - provider must map representative payloads to the canonical artifact contract
  - provider must define secure URL detection and validation
  - provider must produce useful descriptions for representative supported postings
  - provider must pass canonical validation, raw-row preparation, and normalization
  - provider must not require control-plane or pipeline branching
  - provider-specific fixed behavior stays in code; only values that vary by request belong in request data
- output or state change: one new provider definition and registry entry
- failure behavior: provider remains unsupported until admission evidence passes
- observable acceptance: adding provider changes provider-owned code and tests only, except derived UI/provider listings that consume registry data

### Constraints and Alternatives

- constraint: FitCV is Python-first and already has a working artifact snapshot path.
- alternative: invoke Career Ops `scan.mjs` as a subprocess
  - benefit: immediate access to many providers
  - trade-off: Node runtime, dependencies, stateful filtering, history, Markdown persistence, incomplete FitCV fields, and a second contract owner
  - reason rejected: violates artifact invariance and adds more management than the admitted-provider approach
- alternative: invoke Career Ops provider modules through a thin Node wrapper
  - benefit: reuses provider detection and listing acquisition
  - trade-off: cross-language deployment remains, provider output still lacks required FitCV semantics, and FitCV still needs provider-specific hydration
  - reason rejected: does not remove provider-specific work and creates a second runtime boundary
- alternative: dynamic Python plugin framework
  - benefit: providers can be installed without FitCV deployment
  - trade-off: discovery, trust, versioning, compatibility, packaging, and support complexity
  - reason rejected: no demonstrated runtime-installation requirement
- alternative: generic browser crawler
  - benefit: broader custom-site coverage
  - trade-off: slower, less deterministic, harder to secure, and unnecessary for current public feeds/APIs
  - reason rejected: native provider interfaces already satisfy initial cases
- alternative: automatic cross-provider fallback
  - benefit: some failures may recover
  - trade-off: hidden routing, non-deterministic provenance, duplicate requests, and future detector overlap
  - reason rejected: explicit provider resolution and provider-internal retrieval steps preserve predictable behavior

## Design Decisions

### Decision: FitCV Owns the Provider Boundary

- context: Career Ops offers a useful registry pattern but an incompatible stateful scanner boundary
- selected approach: implement the admitted providers inside FitCV and use Career Ops as research and security reference only
- rationale: keeps one language, one dependency graph, one artifact contract, and one runtime truth
- alternatives considered: direct scanner subprocess, provider-module wrapper, generic browser crawler
- accepted trade-offs: providers are admitted incrementally rather than inheriting broad nominal coverage
- affected owners and boundaries: job-source acquisition, ingest, control-plane source resolution, and job-input documentation

### Decision: Registry Data Replaces Routing Branches

- context: provider-specific `if` branches would spread as providers expand
- selected approach: one static provider registry whose entries expose detection and acquisition callables
- rationale: new providers extend one collection without changing consumers
- alternatives considered: subclass hierarchy, factory, dynamic plugins, repeated CLI/UI choices
- accepted trade-offs: provider changes require FitCV deployment
- affected owners and boundaries: job-source module and derived provider choices

### Decision: Provider Output Is Already Canonical

- context: returning provider-native payloads would move adaptation into ingest and duplicate provider knowledge
- selected approach: provider acquisition returns canonical FitCV job objects
- rationale: external variability is contained at the trust boundary
- alternatives considered: generic raw-job intermediate schema, provider-specific ingest adapters
- accepted trade-offs: each provider owns its field mapping and required-detail retrieval
- affected owners and boundaries: provider implementations and canonical validation

### Decision: Auto-Detection Must Be Unambiguous

- context: first-match routing changes behavior when a new detector overlaps an existing detector
- selected approach: evaluate all detectors and require exactly one match
- rationale: preserves existing behavior under extension and makes overlap visible
- alternatives considered: registry order, priority numbers, most-specific scoring
- accepted trade-offs: an overlapping provider requires explicit selection or detector correction
- affected owners and boundaries: provider resolution and request validation

### Decision: Acquisition Is Atomic

- context: partial provider output can silently produce incomplete or misleading run snapshots
- selected approach: do not create a run when acquisition cannot produce the required canonical result for selected jobs
- rationale: immutable snapshots should represent complete successful acquisition, not hidden partial failure
- alternatives considered: skip failed detail rows, create partial runs with warnings
- accepted trade-offs: one failed required-detail request can fail the scan
- affected owners and boundaries: provider acquisition, error handling, and run creation

### Decision: Snapshot Owns the Execution Projection

- context: current workers execute `jobs_path`, while run inspection and replay preserve `jobs_input_json`
- selected approach: canonicalize once, store that string as `jobs_input_json`, atomically write it to a run-owned execution projection, and verify its digest before pipeline execution
- rationale: preserves the existing path-based pipeline without allowing original source files to become mutable runtime truth
- alternatives considered: queue original paths, rewrite pipeline interfaces around in-memory jobs, or let worker trust an unchecked projection
- accepted trade-offs: each run stores one small derived JSON file beside the immutable snapshot
- affected owners and boundaries: control-plane source resolution, run persistence, worker preflight, and existing pipeline path interface

### Decision: Empty Scan Artifact and Empty Run Are Different Contracts

- context: managed acquisition can legitimately find zero jobs, but an empty pipeline run has no useful work and existing upload paths reject it
- selected approach: canonical artifact and successful managed Scan output permit `[]`; every control-plane Run source rejects zero jobs with HTTP 422 and code `empty_job_input`
- rationale: keeps Scan output truthful while making Run behavior uniform across upload and Scan modes
- alternatives considered: create empty runs or make empty validity depend on source mode
- accepted trade-offs: Scan completion and Run creation have intentionally different empty-result policies
- affected owners and boundaries: canonicalization, managed Scan output, control-plane validation, and Run creation

### Decision: Existing Pipeline Owns Filtering and Deduplication

- context: Career Ops filtering and history logic would create source-dependent results
- selected approach: acquisition applies only explicit user retrieval constraints; FitCV retains downstream normalization and deduplication ownership
- rationale: source mode must not change artifact semantics or persistent decision policy
- alternatives considered: importing Career Ops filters, pre-deduping against scan history
- accepted trade-offs: scanner may return records later removed by FitCV normalization
- affected owners and boundaries: provider acquisition and normalize stage

### Decision: No Generic Fallback Engine Initially

- context: current providers need internal retrieval variation but no demonstrated cross-provider fallback contract
- selected approach: keep retrieval alternatives inside the selected provider and fail cross-provider acquisition explicitly
- rationale: avoids hidden routing and speculative configuration
- alternatives considered: ordered strategy chains and local-parser-first fallback
- accepted trade-offs: operator may retry with another explicit provider when supported
- affected owners and boundaries: provider implementation and request model

### Compatibility, Migration, and Risk

- old behavior: path, upload, and paste sources produce jobs for the existing pipeline; `fetch_from_apify` exists as an unwired helper; isolated provider exporters can create compatible files outside the control plane
- new behavior: scanner becomes another source acquisition mode and all supported providers resolve through one provider owner and one canonical job boundary
- compatibility boundary:
  - existing accepted file shapes and pipeline stages remain supported
  - existing job snapshots remain valid
  - canonical required fields remain owned by `src/fitcv/contracts.py`
- migration or backfill: no historical data migration or snapshot rewrite
- rollout and rollback:
  - rollout admits Personio, Greenhouse, and Workday only after contract evidence passes
  - rollback removes or disables scanner source exposure while leaving existing modes and snapshots unchanged
- deprecation or consumer impact:
  - separate exporter contracts are superseded by the unified job-source owner; provider-local parser and transport modules may remain implementation details
  - no public API compatibility is promised for uncommitted spike module names
- risk: provider sites change payloads or anti-bot behavior
  - mitigation: provider-local fixtures, contextual errors, bounded live verification, and no silent fallback
- risk: provider expansion creates detector overlap
  - mitigation: exact-one auto-detection rule
- risk: scanner output and stored snapshot drift
  - mitigation: serialize once, write one run-owned projection, store its digest, and verify it before execution
- risk: provider descriptions are incomplete
  - mitigation: provider admission requires representative non-empty descriptions; acquisition fails rather than inventing required content
- risk: SSRF or credential leakage through user-supplied URLs
  - mitigation: provider host validation, HTTPS-only policy, credential/port rejection, redirect controls, verified TLS, and secret-free provenance

## Invariants and Edge Cases

### Invariants

- `src/fitcv/contracts.py` remains the canonical owner of required job fields and canonical key mapping.
- Every source mode hands an in-memory job list to the same artifact canonicalization path.
- Every admitted provider returns canonical FitCV jobs; ingest contains no provider-native parsing.
- Exactly one provider is selected before any network request.
- Provider selection never depends on registry iteration order.
- No provider-specific branch exists in run execution or downstream pipeline stages.
- `jobs_input_json` is the only run-scoped job truth.
- `jobs_path` is a run-owned projection derived from `jobs_input_json`, never the original input path.
- Worker execution cannot begin until the projection digest matches the canonical snapshot digest.
- Provenance never duplicates the job payload or changes pipeline semantics.
- Canonical serialization occurs once per run input resolution.
- Provider acquisition does not write Career Ops state or consume Career Ops user files.
- TLS verification, URL validation, total deadline, per-request cap, result limit, and provider-internal pagination cannot be disabled by ordinary request input.
- Adding a provider cannot silently alter routing for an existing careers URL.

### Edge Cases

- empty or minimal input:
  - a valid source containing no jobs produces `[]`
  - successful managed Scan output may persist and download `[]`
  - every run source rejects an empty canonical list before projection persistence or run creation with HTTP 422 and code `empty_job_input`
  - missing or invalid tracked-company snapshot fields fail before provider resolution
- normal and large input:
  - provider retrieval is bounded by validated `max_jobs`, total deadline, per-request cap, and provider-internal pagination
  - canonicalization preserves acquisition order
  - file size and upload limits remain owned by existing control-plane boundaries
- duplicate, missing, malformed, or unsupported data:
  - duplicate URLs remain present until existing normalize-stage deduplication
  - non-object rows and missing required fields fail the artifact contract
  - unsupported URLs fail with matching-provider absence
  - overlapping detectors fail with matching-provider ambiguity
  - unknown explicit provider IDs fail without detection fallback
- retry, cancellation, timeout, partial failure, or concurrency:
  - requests use bounded timeouts
  - no automatic retry is required except provider-local bounded retry where the provider protocol demonstrates a transient status
  - no successful Scan output or Run is created after provider failure
  - concurrent scans share no mutable provider or scanner state
  - managed Scan cancellation and terminal state are owned by the managed Scan lifecycle contract
- migration or mixed-version state:
  - historical runs without scanner provenance remain readable
  - a run snapshot remains executable without the provider that originally acquired it
  - provider registry changes affect new acquisition only
- generated-source consistency:
  - provider routing in tracked-company management or internal tooling must derive from the provider registry, not copied lists
  - job-input documentation references canonical code owners and does not become a parallel schema
- security or accessibility boundary:
  - credentials in URLs, untrusted hosts, non-HTTPS provider URLs, custom ports, and unsafe redirects are rejected
  - managed Scan and Run input UIs use existing accessible labels, validation summaries, focus behavior, error presentation, keyboard behavior, and responsive layout in V1
  - secrets and raw authorization data never enter run manifests or user-visible errors
- provider-specific cases:
  - Personio feeds with empty description containers use the provider's public-page fallback or fail
  - Greenhouse boards must request content explicitly
  - Workday relative posting dates are resolved against acquisition time, which is recorded in provenance
  - Workday detail API rejection may use public-page metadata within the same provider boundary
  - a provider unable to produce useful descriptions remains unsupported even if it can discover titles and URLs

## Validation Plan

### Acceptance Criterion: Source Modes Are Symmetric

- setup or precondition: equivalent non-empty ordered job objects are available through path, upload, paste, and scanner acquisition modes
- action: resolve each source through its normal entry point
- expected result: every mode hands the same ordered in-memory job list to the shared canonicalization boundary
- failure condition: a source mode bypasses canonicalization, applies unique job semantics, or requires a downstream branch
- proof method: source-resolution contract tests using equivalent fixtures
- expected evidence: identical canonical objects and no source-specific branch after resolution

### Acceptance Criterion: Provider Resolution Is Permanent

- setup or precondition: registry contains existing provider detectors plus a candidate detector
- action: resolve representative existing, unsupported, and intentionally overlapping careers URLs with automatic detection
- expected result: existing URLs retain their provider, unsupported URLs report zero matches, and overlapping URLs report ambiguity
- failure condition: registry order selects a provider, adding a provider changes an existing unique match, or retrieval begins before exact-one resolution
- proof method: parameterized provider-resolution tests independent of registry ordering
- expected evidence: stable provider IDs and deterministic zero-match and multiple-match errors

### Acceptance Criterion: Providers Return Canonical Jobs

- setup or precondition: representative Personio, Greenhouse, and Workday native fixtures include listings, details, dates, locations, and provider-specific URL forms
- action: acquire each fixture through its registered provider
- expected result: each provider returns only canonical FitCV job objects satisfying `src/fitcv/contracts.py`
- failure condition: provider-native keys escape the boundary, required fields are invented, descriptions are unusable, or ingest performs provider parsing
- proof method: provider contract tests plus canonical schema validation
- expected evidence: all three providers satisfy one shared assertion set without provider-specific downstream expectations

### Acceptance Criterion: Live Provider Output Enters Existing Pipeline

- setup or precondition: bounded representative public endpoints are available for one Personio, one Greenhouse, and one Workday company portal
- action: acquire a small result set, canonicalize it, then run existing parse, schema, raw-row, and normalize stages
- expected result: every acquired job reaches normalize with useful description content and no provider-specific pipeline configuration
- failure condition: provider output requires manual editing, alternate schema handling, or downstream knowledge of provider identity
- proof method: opt-in bounded live smoke checks backed by committed fixtures for deterministic regression
- expected evidence: successful pipeline reports for each admitted provider and recorded endpoint/commit context

### Acceptance Criterion: Managed Scan Uses One Provider Request Contract

- setup or precondition: managed Scan resolves tracked-company snapshots for explicit-provider and auto-detected cases
- action: execute equivalent provider requests through the shared runtime function
- expected result: both cases resolve the same validated internal request, canonical jobs, provenance, and stable provider errors
- failure condition: Scan UI or lifecycle duplicates provider routing, accepts arbitrary URLs, or changes provider semantics
- proof method: provider runtime tests plus managed Scan integration tests
- expected evidence: one shared provider call, immutable company snapshot, and provider-local routing only

### Acceptance Criterion: Scan Output and Run Snapshot Are Identical

- setup or precondition: one successful acquisition produces canonical ordered jobs
- action: store managed Scan output, create a Run from it, and create the run-owned projection
- expected result: Scan output, `jobs_input_json`, and projection contain the same ordered job values, and worker digest verification succeeds
- failure condition: any output reserializes independently, changes ordering or values, or worker accepts a changed projection
- proof method: byte-equality, digest-mismatch, and original-source-mutation tests
- expected evidence: one canonical serialization path reused by Scan and Run snapshots; worker rejects projection drift

### Acceptance Criterion: Empty Scan and Empty Run Policies Are Explicit

- setup or precondition: provider or file acquisition resolves to an empty list
- action: complete managed Scan output, then attempt Run creation through upload and Scan modes
- expected result: managed Scan stores and downloads `[]`; every Run attempt returns HTTP 422 with code `empty_job_input` and creates no projection or Run
- failure condition: empty behavior differs by run source or an empty run is persisted
- proof method: parameterized Run source tests plus managed Scan output test
- expected evidence: one artifact rule and one uniform run policy

### Acceptance Criterion: Acquisition Failure Is Atomic

- setup or precondition: provider fixtures cover listing failure, required-detail failure, timeout, malformed payload, and invalid canonical output
- action: execute managed Scan acquisition for each failure, then inspect Scan and Run availability
- expected result: Scan becomes failed with contextual error, no successful output exists, and no Run can select it
- failure condition: failed jobs are silently skipped, partial jobs become successful output, or prior provider state affects result
- proof method: failure-path tests with persistence assertions
- expected evidence: one failed Scan record, zero successful output, and zero new Runs for every failed acquisition case

### Acceptance Criterion: Security Controls Are Mandatory

- setup or precondition: inputs include valid provider URLs plus HTTP, credential-bearing, custom-port, unsupported-host, private-address, and unsafe-redirect variants
- action: validate and acquire each input using ordinary public request options
- expected result: only provider-approved canonical HTTPS URLs without query or fragment proceed; TLS verification, deadline, request cap, result limit, and pagination bounds remain enabled
- failure condition: request input can disable verification, reach an unapproved target, expose credentials, or persist secrets in errors or provenance
- proof method: URL-validation, redirect, transport-configuration, and redaction tests
- expected evidence: rejected unsafe inputs before content processing and secret-free persisted metadata

### Acceptance Criterion: Provider Extension Is Isolated

- setup or precondition: a fixture-backed candidate provider can satisfy the canonical job contract and security policy
- action: add its provider implementation and single registry entry without modifying source resolution or downstream pipeline code
- expected result: explicit and automatic selection work through existing entry points and all existing provider tests remain unchanged
- failure condition: extension requires new control-plane routing, ingest logic, pipeline branches, duplicated provider metadata, or altered existing detector outcomes
- proof method: changed-file review, registry tests, and full provider contract suite
- expected evidence: provider-local change plus registry registration and evidence fixtures only

### Acceptance Criterion: Downstream Runtime Is Source-Agnostic

- setup or precondition: canonical snapshots from existing file modes and managed Scan output contain equivalent jobs
- action: execute existing worker and pipeline stages from each snapshot
- expected result: stage inputs, normalized records, and source-independent outputs are equivalent
- failure condition: worker or pipeline reads provider configuration, scanner state, source-mode fields, or provenance to interpret jobs
- proof method: replay tests using equivalent snapshots with different provenance
- expected evidence: equal source-independent outputs and unchanged stage interfaces

### Acceptance Criterion: Documentation Has One Contract Owner

- setup or precondition: canonical field contract, provider registry, user input documentation, and generated or presented provider choices exist
- action: inspect references and run documentation validators
- expected result: documentation points to code owners, provider choices derive from registry data, and no copied schema or provider list becomes authoritative
- failure condition: documentation defines a competing job schema, provider list, or routing policy
- proof method: documentation review plus repository validation scripts
- expected evidence: one canonical contract owner, one provider owner, and passing required-section and planning-lifecycle validation

## Completion Criteria

Specification is complete when:

1. scanner is defined as an acquisition mode, not a second ingestion or pipeline contract
2. canonical field ownership, provider ownership, artifact ownership, and provenance ownership each have one explicit boundary
3. path, upload, paste, managed Scan output, explicit-provider, and auto-detected cases converge before canonicalization
4. Personio, Greenhouse, and Workday satisfy one provider contract and one downstream pipeline contract
5. provider detection requires exactly one match and remains independent of registry order
6. provider request fields, defaults, bounds, keyword semantics, stable error codes, and managed Scan ownership are unambiguous
7. acquisition, canonicalization, serialization, projection verification, managed Scan output, replay, and empty-result semantics are unambiguous
8. security controls, canonical URL handling, error mapping, atomicity, bounded retrieval, and useful-description requirements are explicit
9. every required outcome has observable acceptance evidence in this validation plan
10. no unresolved design decision is deferred to implementation without explicit approval
11. implementation file order, task sequencing, commands, and rollout execution remain owned by a later implementation plan
