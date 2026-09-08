---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
contract_version: "1"
created: 2026-09-08
name: scan-provider-catalog
parent_spec: docs/superpowers/specs/2026-08-01-19-49-fitcv-managed-scan-lifecycle-spec.md
targets:
  - config/scan_catalog.yaml
  - src/fitcv/job_sources.py
  - src/fitcv/ats_export.py
  - src/fitcv_cp/company_catalog.py
  - src/fitcv_cp/scan_contracts.py
  - src/fitcv_cp/scan_worker.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/scans_list.html
  - frontend/src/features/scans/api.ts
  - frontend/src/features/scans/types.ts
  - frontend/src/features/scans/new-scan-dialog.tsx
  - frontend/src/test/scans.test.ts
  - frontend/src/test/vite-proxy.test.ts
  - frontend/e2e/integration-flows.spec.ts
  - tests/test_job_sources.py
  - tests/test_fitcv_cp/test_scan_contracts.py
  - tests/test_fitcv_cp/test_scan_worker.py
  - tests/test_fitcv_cp/test_sqlite_store.py
  - tests/test_fitcv_cp/test_app.py
  - docs/configuration.md
  - docs/superpowers/evidence/2026-09-08-scan-provider-catalog-live-probes.md
---

# Goal

Finish Scan provider catalog support without erasing current dirty work. Make
`config/scan_catalog.yaml` the only editable catalog data source, load it into
typed provider-neutral records, preserve one symmetric acquisition boundary for
Greenhouse, Ashby, Lever, Personio, and Workday, and keep Wellfound visible but
discovery-only. Track and Scan APIs, persistence, worker snapshots, React, and
server-rendered Scan UI derive from that source and retain existing lifecycle
contracts.

# Scope And Non-Goals

In scope: catalog identity and provenance, approved company profiles, trusted
provider configuration derivation/validation, provider adapter parity, Career
Ops-style source provenance, optional live verification and quarantine, Track,
ordered company selection, immutable snapshots, API/UI derivation, tests, and a
repeatable maintenance procedure.

Out of scope: changing the LLM/API provider registry, adding a `career_ops`
runtime dependency, acquiring Wellfound jobs, changing Run contracts, fixing
unrelated dirty files, committing, pushing, or running external probes as part
of automated tests.

# Repository Truth

- `HEAD` and branch are `1ab9670c217ed5aa42bad2b875ffa243c42652b8` and `main`.
- The worktree contains uncommitted provider, persistence, API, worker, React,
  template, and test edits plus a new `src/fitcv_cp/company_catalog.py`.
- Current `company_catalog.py` hardcodes a Python tuple, derives config in code,
  and contains `Example`/fake profiles. It is not an acceptable catalog SSOT.
- `src/fitcv/job_sources.py:PROVIDERS` is the Scan acquisition registry.
  `src/fitcv_cp/provider_registry.py` is the unrelated LLM/API provider
  registry; do not merge them or edit it for this work.
- Existing dirty Scan slices are preserved as partial implementation. Previous
  plan rows claiming completed tasks and validator passes are not accepted as
  current evidence because they are not reproducible from this worktree.
- `docs/core-scanrun-r1-report.md` proves one prior real Greenhouse/Awin Scan
  reached `succeeded` with five jobs and survived reload. It does not approve
  any current catalog profile, Ashby, Lever, Workday, Personio, or Wellfound.
- `tmp/liveprobe/*` is LinkedIn rerun/export evidence, not a Scan provider
  catalog approval source. Do not import it into runtime config.
- The tracked catalog and evidence artifact now provide the approved
  profile matrix and per-profile probe records, including Retool's accepted
  Gem list/detail parser record. Do not retain `Example` values as production
  profiles.

# SSOT Decision

Add `config/scan_catalog.yaml`; no existing config file owns this taxonomy.
`config/taxonomy/skill_synonyms.yaml` and `config/runtime/control_plane.yaml`
have different owners and remain untouched; no `config/runtime/control_plane.yaml`
exists in this checkout.

The YAML shape is:

```yaml
schema_version: 1
catalog_source: bundled
catalog_revision: "2026-09-08-v2"
companies: []
```

Each company item contains `catalog_id`, `company_name`, `careers_url`,
`provider_id`, `provider_label`, `trackable`, `discovery_only`, and
`verification` with `status`, `checked_at`, and `evidence_ref`. Allowed provider
IDs are `greenhouse`, `ashby`, `lever`, `personio`, `workday`, and `wellfound`.

YAML stores profile identity, canonical URL, provider metadata, capability, and
verification provenance only. It does not store `api_url`, credentials,
headers, tokens, arbitrary options, or duplicated provider endpoint rules.
`company_catalog.py` derives trusted provider config through
`fitcv.job_sources.build_trusted_provider_config` and exposes an immutable
`CompanyCatalogRecord` plus a compatibility `BUNDLED_COMPANY_CATALOG` view for
existing consumers. No runtime consumer reads YAML directly.

Loader validation must reject missing/extra top-level or record keys, unsupported
providers, non-HTTPS or non-canonical URLs, duplicate IDs, duplicate canonical
URLs, invalid revision/source, invalid booleans, mismatched provider labels,
invalid verification state, and provider/config mismatches. Rules:

- Wellfound always has `trackable: false`, `discovery_only: true`, no trusted
  config, and never enters `PROVIDERS`.
- A non-Wellfound `quarantined` record remains catalog-visible but is not
  trackable or scannable until a new approved probe changes it to `verified`.
- A `verified` record must be trackable and not discovery-only.
- Catalog IDs never change or get reused. Any identity, URL, provider, or
  capability change bumps `catalog_revision` and records the reason in the
  maintenance evidence.

# Trusted Provider And Provenance Contract

Keep `build_trusted_provider_config` and
`validate_trusted_provider_config` as the sole semantic owner for trusted
config. Keep exact host allowlists, HTTPS/SSRF checks, redirect rejection,
bounded timeout/pagination, no client endpoint/config input, and forbidden key
rules already present in the dirty provider slice. Provider endpoints remain:

| Provider | Derived endpoint | Canonical source marker |
| --- | --- | --- |
| Greenhouse | `https://boards-api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true` | `career-ops:greenhouse` |
| Ashby | `https://api.ashbyhq.com/posting-api/job-board/{board_slug}` | `career-ops:ashby` |
| Lever | `https://api.lever.co/v0/postings/{company_slug}?mode=json` | `career-ops:lever` |
| Personio | existing `build_personio_feed_url` | `career-ops:personio` |
| Workday | existing `_workday_endpoints` | `career-ops:workday` |
| Wellfound | none | no acquisition |

Adapters stay symmetric through `ProviderDefinition`, `ScannerRequest`, one
resolution path, one error mapper, one canonicalization path, and one worker
interface. `ats_export.py` remains the parser/helper owner. Career Ops
provenance is a string/field contract in canonical jobs and persisted Scan
metadata; it is not a package import or runtime service dependency.

# Execution Approach

- Mode: `inline sequential`; current Runtime Grant denies child delegation.
- Coordination: `git-tracked`; one lead owns this plan and all ledger updates.
- Executor: `codex`; validator: `review` profile, read-only.
- Isolation: current worktree; preserve all unrelated dirty files and deletions.
- Commit policy: no commits, branch changes, resets, pushes, destructive DB
  recovery, or external provider calls during automated proof.
- Shared-write rule: catalog loader/config first; provider and persistence
  consumers second; API/UI third; final evidence last. No parallel writers.
- Any existing dirty implementation that passes focused proof may be retained;
  do not revert it merely to recreate a clean patch.

## Current Dirty Scope To Preserve

Preserve unrelated changes in `config/taxonomy/skill_synonyms.yaml`, deleted
`data/*` fixtures, `.tmp/`, `data/candidate_profile.final-reviewed.yaml`,
`data/sample_jobs-2.json`, `node_modules/`, and frontend test artifacts. The
Scan plan may touch only declared targets above; source edits outside those
targets require explicit reconciliation before execution.

## Task Ledger

| Task | State | Owner | Depends on | Required proof | Evidence truth |
| --- | --- | --- | --- | --- | --- |
| 0 Reconcile worktree and profile approval gate | completed | lead | none | `git status --short`, source inventory, approved profile matrix | Current HEAD `1ab9670c`; probe evidence approves Anthropic, OpenAI, ElevenLabs, n8n, and Retool |
| 1 YAML SSOT and typed loader | completed | lead | Task 0 | loader self-check plus catalog contract tests | `config/scan_catalog.yaml` is sole catalog data source; loader and contract tests pass |
| 2 Provider boundary and Career Ops provenance | completed | lead | Task 1 | provider/parser/security tests; opt-in probe evidence | Provider tests pass; parser probes pass for four existing providers plus accepted Retool Gem list/detail record; no runtime Career Ops dependency |
| 3 Persistence, Track, and immutable snapshots | completed | lead | Tasks 1–2 | direct HTTP/store/SQLite tests, migration rollback, idempotency | Scan-focused backend proof passes, including migration revision sourced from SSOT |
| 4 API/UI derivation and Scan surfaces | completed | lead | Task 3 | typecheck delta, Vitest, a11y, Playwright, SSR flow | Vitest `12 passed`, a11y `2 passed`, Playwright `6 passed`, build passes; typecheck retains five pre-existing diagnostics outside Scan |
| 5 Live verification, quarantine, maintenance docs | completed | lead | Tasks 1–4 and approved profiles | evidence artifact, no-secret review, maintenance command | Read-only Gem list/detail evidence records one accepted Retool parser result; maintenance guidance recorded |
| 6 Final verification and retirement | completed | lead | Tasks 0–5 | full focused suite, build, `git diff --check`, scope review | Fresh post-edit `git diff --check` PASS. Existing focused proof: `39+15 deselected` provider/catalog/worker; `53+430 deselected` Scan/company-catalog app; frontend Scan/Vite `12`; a11y `2`; Playwright `6`; build PASS. Broader suite remains blocked by pre-existing deleted `data/candidate_profile.v2.sample.yaml` and unrelated dirty paths. Independent Herdr review blocked by 120-second watchdog with residual process, not source finding. No commit/push performed. |

### Acceptance Record

- Backend provider/catalog/worker proof: `39 passed, 15 deselected`; Scan/company-catalog app proof: `53 passed, 430 deselected`.
- Frontend proof: Scan/Vite tests `12 passed`; accessibility `2 passed`; Playwright `6 passed`; production build passed.
- `git diff --check` passed. Typecheck retains five baseline diagnostics in unrelated test files.
- Live probes: read-only public GETs plus Gem public GraphQL list/detail POSTs; five trackable profiles passed parser probes, with Retool recorded as one accepted list/detail result.
- Previous broader backend run: `669 passed, 20 failed`; failures are unrelated candidate-profile tests requiring pre-existing deleted `data/candidate_profile.v2.sample.yaml`. Full-suite rerun remains unnecessary until that user-owned fixture deletion is resolved.

## Lane Retirement

Lead marks a task accepted only after its declared proof runs on current
worktree state, records command/exit/result in this plan or the evidence file,
and confirms no unrelated file was edited. Until then, `partial-unverified`
means preserve existing code but do not call behavior complete.

# Task Breakdown

### Task 0: Reconcile worktree and gate approved profiles

**Purpose:** Establish truthful baseline and prevent fake or unapproved catalog data.

**Files And Symbols:** Inspect `git status`, `src/fitcv_cp/company_catalog.py`,
`src/fitcv/job_sources.py`, `src/fitcv_cp/provider_registry.py`, all current
Scan routes/UI/tests, `docs/core-scanrun-r1-report.md`, and approved handoff
evidence. Do not edit source.

**Steps:**
- Record current `HEAD`, branch, dirty paths, and historical evidence limits.
- Obtain exact requested company profile matrix: stable ID, name, canonical URL,
  provider, approval status, probe date, and evidence reference.
- If matrix is absent, stop profile population and record blocker; structural
  loader work may continue with test-only fixtures, never `Example` production
  values.
- Reconcile old ledger rows to `pending` or `partial-unverified`; do not claim
  validator or runtime proof that was not rerun on current base.

**Verification:** `git status --short`; `git rev-parse HEAD`; source/evidence
inventory reviewed by lead.

**Exit Criteria:** Worktree identity and preserved paths recorded; approved
profile matrix present or explicit blocker recorded; no fake profile accepted.

### Task 1: Make YAML catalog SSOT and load typed provider-neutral records

**Purpose:** Replace hardcoded catalog data without duplicating provider logic.

**Ownership:** `config/scan_catalog.yaml` and
`src/fitcv_cp/company_catalog.py`; tests in
`tests/test_fitcv_cp/test_scan_contracts.py`.

**Steps:**
- Add YAML with only approved profiles and exact schema above. Keep test-only
  synthetic fixtures separate from production config.
- Add loader using installed `yaml.safe_load`, defaulting to repository config
  path, with explicit file/top-level/record validation and deterministic order.
- Reuse existing `CompanyCatalogRecord`, `validate_catalog`, and provider
  config builder where semantics match; turn `BUNDLED_COMPANY_CATALOG` into a
  loaded compatibility view, not a second data source.
- Derive provider config for trackable profiles; return `None` for Wellfound or
  quarantined profiles. Never expose config JSON to API/UI.
- Add tests for malformed YAML, duplicate identity, URL normalization, exact
  provider config, Wellfound, quarantine, revision, and stable ordering.

**Verification:** `python -m pytest tests/test_fitcv_cp/test_scan_contracts.py -q`.

**Exit Criteria:** Removing or changing a YAML record changes catalog output;
editing Python data is no longer required; all loader failures are explicit.

### Task 2: Finish symmetric adapters and provenance without runtime Career Ops

**Purpose:** Make every supported ATS use one safe acquisition contract.

**Ownership:** `src/fitcv/job_sources.py`, `src/fitcv/ats_export.py`,
`tests/test_job_sources.py`.

**Steps:**
- Preserve current shared request/definition/resolution/error path and verify
  Greenhouse host variants plus Ashby, Lever, Personio, and Workday endpoint
  derivation from validated config.
- Verify parser outputs satisfy existing canonical job schema, include stable
  provider source markers and provider IDs, and retain required description,
  URL, company, location, and date fields.
- Prove timeout, malformed payload, HTTP failure, DNS/SSRF, redirect, caps,
  pagination, and detail-fetch behavior symmetrically. No external call in
  automated tests.
- Keep Wellfound absent from `PROVIDERS`; reject explicit and catalog-derived
  acquisition before network access.
- Do not add or import any runtime `career_ops` package. Career Ops naming is
  provenance only.

**Verification:** `python -m pytest tests/test_job_sources.py -q`.

**Exit Criteria:** Provider addition does not add Scan-worker branches; all
adapters return same `AcquisitionResult`/canonical job contract; Wellfound
has rejection proof.

### Task 3: Reconcile persistence, Track, and immutable Scan snapshots

**Purpose:** Persist trusted config/provenance while keeping ordered inputs and
historical Scans immutable.

**Ownership:** `src/fitcv_cp/scan_contracts.py`, `src/fitcv_cp/store.py`,
`src/fitcv_cp/sqlite_store.py`, `src/fitcv_cp/app.py`,
`tests/test_fitcv_cp/test_scan_contracts.py`,
`tests/test_fitcv_cp/test_scan_worker.py`,
`tests/test_fitcv_cp/test_sqlite_store.py`, `tests/test_fitcv_cp/test_app.py`.

**Steps:**
- Adopt current migration only after checking actual schema/version. Migration
  6→7 adds nullable provider/catalog fields, deterministic legacy backfill,
  quarantine warnings, and partial uniqueness for `(catalog_source,catalog_id)`.
- Validate trusted config once at write/read boundary; `{}` remains compatible
  only for legacy rows and is derived during snapshot creation. Malformed JSON,
  unknown providers, and quarantined records never become scannable.
- Keep Track request body to `catalog_id`; derive all other fields server-side.
  Enforce atomic insert, replay-safe `Idempotency-Key`, duplicate identity
  handling, and no persistence on failure.
- Preserve request `company_ids` order. Snapshot company name, URL, provider,
  trusted config, catalog provenance, and row revision before queueing. Worker
  reads snapshot only.
- Use direct HTTP/store tests for success, failure, duplicate delivery,
  idempotency conflict, migration rerun/rollback, registry mutation, and
  provider failure atomicity.

**Verification:**
`python -m pytest tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -k "catalog or tracked_company or scan_routes or snapshot or migration" -q`.

**Exit Criteria:** API envelopes/status/error codes match tests and OpenAPI;
Track cannot accept client provider fields; queued/running Scan behavior is
unchanged by later catalog or registry edits.

### Task 4: Derive React and server-rendered Scan UI from API

**Purpose:** Keep both Scan surfaces symmetric and safe.

**Ownership:** `frontend/src/features/scans/api.ts`, `types.ts`,
`new-scan-dialog.tsx`, `frontend/src/test/scans.test.ts`,
`frontend/src/test/vite-proxy.test.ts`, `frontend/e2e/integration-flows.spec.ts`,
`src/fitcv_cp/templates/scans_list.html`.

**Steps:**
- Use existing API client and idempotency helper for catalog GET and Track POST;
  no provider config or endpoint is accepted from browser.
- Derive labels, tracked state, loading/error/retry, and selected company IDs
  from server response. Preserve ordered selection.
- Render Wellfound and quarantined records as visible discovery-only rows with
  disabled/no Track action and no company ID.
- Mirror the same route calls, states, and redaction in `/admin/scans`; keep
  `/app/#/scans` and `/admin/scans` behavior aligned.
- Prove keyboard/focus/contrast, narrow viewport, no horizontal overflow, and
  no raw config/secrets in rendered HTML.

**Verification:**
`npm --prefix frontend run typecheck`; `npm --prefix frontend test -- --run src/test/scans.test.ts src/test/vite-proxy.test.ts`; `npm --prefix frontend run test:a11y`; `npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts`.

**Exit Criteria:** Supported verified profile can be tracked and selected;
Wellfound/quarantined profiles cannot be tracked; both UI surfaces show same
server-derived capability state.

### Task 5: Run opt-in live verification and publish quarantine evidence

**Purpose:** Separate real provider reachability from deterministic automated
proof and prevent failed profiles from entering Scan execution.

**Ownership:** `docs/superpowers/evidence/2026-09-08-scan-provider-catalog-live-probes.md`,
`docs/configuration.md`, and approved `config/scan_catalog.yaml` updates.

**Steps:**
- Run only after approved profile matrix exists and only with explicit operator
  authorization. Use existing CLI/provider entrypoint, bounded timeout and
  max-jobs, disposable output under `.tmp/`, and no credentials.
- Record one redacted row per profile: catalog ID, provider, host, probe date,
  HTTP/result status, job count, output checksum, adapter/config revision, and
  failure code. Never record payloads, query-bearing URLs, headers, cookies, or
  secrets.
- On redirect, SSRF, timeout, malformed payload, empty required detail, or
  schema failure, mark profile `quarantined` in YAML and keep it visible but
  untrackable. Do not silently fall back to another provider or URL.
- Mark `verified` only when approved probe evidence matches canonical URL,
  provider, parser contract, and output validation. Bump catalog revision for
  every capability/status change.
- Document edit → validate → probe → quarantine/approve → test workflow in
  `docs/configuration.md`.

**Verification:** Evidence file review; loader tests; no-secret grep over the
evidence artifact; automated suites remain network-free.

**Exit Criteria:** Every production catalog record has explicit evidence or is
quarantined; Wellfound remains permanently discovery-only; no runtime Career Ops
dependency exists.

### Task 6: Final verification, evidence acceptance, and retirement

**Purpose:** Prove complete behavior on current dirty worktree and close plan
without touching unrelated work.

**Steps:**
- Capture a fresh frontend typecheck baseline from current `HEAD` in a
  disposable clean checkout before comparing changed-scope diagnostics. The old
  `b868138d` five-diagnostic record is historical only.
- Run focused backend proof, then frontend proof, then build. Run live probes
  only through Task 5, never as part of this automated gate.
- Inspect OpenAPI paths/envelopes, migration version/backfill, catalog revision,
  Track idempotency, Wellfound/quarantine rejection, snapshots, ordered IDs,
  and both UI surfaces.
- Run `git diff --check`; compare changed paths against declared targets and
  explicitly preserved dirty paths. Do not clean or reset unrelated files.
- Record exact command outputs and retire each lane only after proof.

**Verification:**

```text
python -m pytest tests/test_job_sources.py tests/test_fitcv_cp/test_scan_contracts.py tests/test_fitcv_cp/test_scan_worker.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_app.py -q
npm --prefix frontend run typecheck
npm --prefix frontend test -- --run src/test/scans.test.ts src/test/vite-proxy.test.ts
npm --prefix frontend run test:a11y
npm --prefix frontend run test:e2e -- e2e/integration-flows.spec.ts
npm --prefix frontend run build
git diff --check
```

**Exit Criteria:** All required checks pass or have an explicit documented
blocker; no stale completion claim remains; only lead updates this ledger; no
commit or branch disposition occurs.

# Maintenance Workflow

1. Edit only `config/scan_catalog.yaml`; never add catalog records to Python,
   frontend fixtures used as production truth, or database seed code.
2. Keep IDs stable, use canonical HTTPS careers URLs, and bump
   `catalog_revision` for identity/provider/capability/status changes.
3. Run loader/contract tests before any probe. Use disposable probe output and
   append redacted evidence; automated tests never call providers.
4. Quarantine failures immediately. Quarantine removes Track/Scan capability
   but does not delete history or hide discovery.
5. Promote only from approved evidence; update API/UI fixtures only to model
   response shape, not to become a second catalog.
6. Re-run migration/snapshot/Track tests when record fields or revision change.
7. Review evidence for secrets and raw payloads before publication. Preserve
   prior revisions and evidence references; never reuse catalog IDs.

# Unresolved Conflicts And Stop Conditions

- **Profile matrix source:** `config/scan_catalog.yaml` and its referenced
  evidence artifact own approved names, URLs, and probe records. Do not infer
  them from `docs/core-scanrun-r1-report.md` or `tmp/liveprobe/*`.
- **SSOT conflict:** old plan names `company_catalog.py` as data owner; this
  plan resolves it to YAML with Python loader/facade only.
- **Ledger conflict:** old plan marks Tasks 1–6 completed. This plan resets
  those claims to pending or partial-unverified because current-base proof is
  absent.
- **Baseline conflict:** old typecheck evidence references `b868138d`, not
  current `HEAD`; recapture before final gating.
- **External probe boundary:** no live provider call is permitted in automated
  tests. Any probe requiring credentials, non-public endpoints, or approval
  pauses Task 5 and leaves record quarantined.
- **Scope conflict:** unrelated dirty files/deletions remain user-owned and
  must not be reverted, staged, deleted, or folded into this work.

# Completion Criteria

1. YAML is sole catalog data source; loader validation and typed records are
   tested, deterministic, and free of secrets.
2. Approved profiles use real canonical URLs; unknown/unapproved/quarantined
   profiles cannot become trackable; Wellfound is always discovery-only.
3. Greenhouse, Ashby, Lever, Personio, and Workday share one adapter boundary,
   canonical jobs, security rules, and Career Ops provenance markers without a
   runtime Career Ops dependency.
4. SQLite migration, deterministic legacy backfill, Track atomicity/idempotency,
   provenance, immutable snapshots, worker replay safety, and ordered IDs pass
   direct backend proof.
5. API, React, and server-rendered Scan surfaces derive capabilities from the
   same response and redact provider config.
6. Live verification/quarantine evidence and maintenance procedure are present
   and reproducible without network calls in normal tests.
7. Fresh focused backend/frontend checks, build, `git diff --check`, and scope
   review pass; no commit, push, reset, or unrelated-file cleanup occurs.

Plan is `completed`; Task 6 accepted on recorded focused proof, fresh post-edit `git diff --check` PASS, preserved broader-suite blocker, and independent Herdr watchdog blockage (120 seconds with residual process, not source finding). No commit or push performed.
