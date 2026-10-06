---
layer: change
artifact_type: plan
status: active
template_id: implementation-plan
name: fitcv-next-pr-sequence
targets:
  - scripts/fitcv_analytics.py
  - scripts/export_fitcv_analytics_source.py
  - src/fitcv_cp/analytics_dashboard.py
  - src/fitcv_cp/app.py
  - config/analytics_metrics.yaml
  - config/acceptance_state.yaml
  - config/evidence_registry.yaml
  - scripts/sql/fitcv_gold_views.sql
  - scripts/benchmark_cv_efficiency.py
  - scripts/verify_fitcv_acceptance.py
  - tests/test_fitcv_analytics.py
  - tests/test_acceptance_state.py
  - tests/test_export_fitcv_analytics_source.py
  - tests/test_analytics_dashboard.py
  - frontend/src/features/analytics-dashboard/
  - frontend/e2e/analytics-dashboard.spec.ts
  - docs/superpowers/evidence/
---

# FitCV Next PR Sequence

## Review conclusion

The supplied verdict is directionally correct and becomes the canonical next
step after PR #88. P0-A remains closed by rejection; P0-B/C remain closed only
within declared scopes; P1-A acceptance is historically established; P1-B
implementation and acceptance are verified but current measurement remains
incomplete; P1-C remains unfinished; P2 stays deferred.

The verdict needs four execution constraints:

1. PR #89 must fix analytics correctness before any dashboard contract is
   exposed. It must not change CV-generation behavior or recover R5 by
   inference.
2. PR #90 owns both operational-source export and the executable semantic
   metric relation. A dashboard must not reconstruct KPI formulas.
3. PR #91 must use imported-corpus wording, candidate revision identity, and
   coverage metadata. It must not claim market trends or predictive insight.
4. PR #92 creates a new R7-style measurement package only from retained,
   replayable inputs. Optimization remains blocked until R7 independently
   rebuilds and verifies.

## Goal

Deliver the next narrow FitCV sequence without reopening broad P0/P1
convergence work:

```text
correct Silver/Gold semantics
    -> export operational state into canonical Bronze input
    -> expose executable semantic metrics
    -> deliver P1-C dashboard MVP
    -> produce fresh reproducible P1-B measurement
```

The sequence preserves the existing read-only Bronze → Silver → Gold
architecture, separates implementation, acceptance, measurement, and
optimization status, and keeps analytics outside the CV-generation request
path.

## Non-goals

- Do not recover or fabricate the unavailable R5 manifest/database pair.
- Do not promote R6-unavailable evidence into current runtime measurement.
- Do not change provider routing, CV-generation behavior, accepted-artifact
  semantics, or `local_first` production default in PR #89–#92.
- Do not add predictive market trends, market-wide claims, or optimization
  changes before a verified R7 baseline.
- Do not query operational SQLite directly from frontend code.
- Do not edit generated acceptance artifacts without rebuilding them from their
  canonical sources.

## Execution approach

- Mode: sequential PRs `#89` → `#90` → `#91` → `#92`.
- Coordination: Git-tracked; one lead controller owns plan state and merge
  order.
- Isolation: fresh `codex/` branch from updated `main` for each PR.
- Parallel ownership: none. PR #89 and PR #90 share analytics contracts and
  must not run concurrently; PR #91 depends on PR #90; PR #92 depends on the
  corrected analytics and evidence contracts.
- Commit policy: bootstrap this tracked plan before implementation; then commit
  each PR only after its local proof passes. Push, review, and merge happen per
  PR. Coordination-state commits are allowed only for durable checkpoints and
  never replace implementation proof.
- Preserve existing untracked scratch files; do not clean or modify them.
- Required skills by scope: `skill-backend-verification`,
  `skill-test-driven-development`, `skill-full-stack-integration`,
  `skill-frontend-component-engineering`, `skill-verification-before-completion`.

## Coordination state

- Base commit: `66b0ba6fb04cc4a3c88f75998872586cd58cc4a4` (PR #88 merge).
- Active task: PR #90 source export and semantic metric implementation.
- Task ledger: PR #89 is `merged` at `a890849c9d72d3ebf09bc6bd7a2d293928b67ab2`;
  PR #90 is `admitted`; PR #91 and PR #92 remain `proposed` and are admitted
  only after their dependency merges.
- PR #89 admission: branch `codex/fitcv-pr89-analytics-correctness`, base
  `66b0ba6fb04cc4a3c88f75998872586cd58cc4a4`, owner `Codex`, write set
  `scripts/fitcv_analytics.py`, `scripts/sql/fitcv_gold_views.sql`,
  `config/analytics_metrics.yaml`, and focused analytics tests; local proof
  is `python -m pytest -q tests/test_fitcv_analytics.py tests/test_acceptance_state.py`,
  fixture digest replay, acceptance verifier, and `git diff --check`.
- Admission rule: record branch name, base commit, owner, declared write set,
  and local verification command before each PR starts.
- PR #90 admission: branch `codex/fitcv-pr90-analytics-source`, base commit
  `a890849c9d72d3ebf09bc6bd7a2d293928b67ab2`, owner `Codex`, write set
  `scripts/export_fitcv_analytics_source.py`, `scripts/fitcv_analytics.py`,
  `scripts/sql/fitcv_gold_views.sql`, `config/analytics_metrics.yaml`,
  `src/fitcv_cp/sqlite_store.py`, and focused PR #90 tests; local proof is the
  prescribed exporter/analytics/acceptance test selection plus source-byte,
  replay, SQL, verifier, and `git diff --check` evidence.
- Checkpoint rule: after each PR's local proof, record accepted evidence paths,
  test output, blockers, and next PR before push/merge.
- PR #90 review checkpoint: first `review-1` pass found exporter aliasing,
  free-text leakage, native compatibility-payload omission, status mismatch,
  review lineage drift, acceptance-yield grain drift, metric-specific coverage
  drift, and manual-effort denominator drift; all are patched with focused
  regressions before second review.
- Recovery rule: Git plus this plan are authoritative; runtime thread state,
  untracked scratch files, and chat summaries are not recovery sources.
- Approval boundary: external push, pull-request creation, review assignment,
  merge, operational database access, and evidence promotion require explicit
  user authorization.

## Shared contracts

### Evidence dimensions

Keep these fields independent in state and dashboard output:

```text
implementation_status
acceptance_status
measurement_status
optimization_status
```

P1-A and P1-B use separate evidence responsibilities:

```text
P1-A: final artifact correctness, native render, one-page acceptance
P1-B: runtime workload, provider calls, tokens, latency, regeneration, effort
```

R6-unavailable belongs to the P1-B measurement branch. It must not erase the
historical P1-A acceptance basis.

### Semantic metric row

PR #90 establishes one executable relation with this minimum shape:

```text
metric_id
metric_version
cohort_id
cohort_type
dimension_key
numerator
denominator
value
coverage_status
coverage_numerator
coverage_denominator
unavailable_reason
source_commit
input_fingerprint
material_digest
```

`config/analytics_metrics.yaml` remains the contract registry; code computes
the row; SQL, CI, evidence, and dashboard consume the row.

Candidate-gap semantic uniqueness is stricter:

```text
metric_id + metric_version + cohort_id + cohort_type
  + candidate_profile_id + candidate_profile_revision
  + candidate_profile_fingerprint + dimension_key
```

Candidate denominators, coverage, and API selection must use this same profile
revision partition. Two profiles or revisions in one cohort never aggregate
into one candidate-gap row.

## PR #89 — Analytics correctness closure

### Purpose

Fix four reproduced Silver/Gold defects and separate P1-A evidence semantics
from P1-B measurement semantics before dashboard work begins.

### Task function

Analytics identity, revision, denominator, acceptance, and evidence-state
correctness.

### Files and symbols

- Modify `scripts/fitcv_analytics.py`:
  `build_bronze_observations`, `build_silver_facts`,
  `_logical_entity_id`, `_coverage_issue`, `build_gold_run_job_effort`,
  `build_gold_cohort_effort`, `build_gold_requirement_demand`,
  `build_gold_candidate_gap`, `build_gold_acceptance_state`, and
  `rebuild_analytics_bundle`.
- Modify `config/analytics_metrics.yaml` for posting-inventory coverage,
  first-pass accepted-artifact semantics, and evidence dimensions.
- Modify `config/acceptance_state.yaml` only if schema alignment requires
  `optimization_result` to remain outside `status_dimensions`.
- Modify `scripts/sql/fitcv_gold_views.sql` to expose corrected columns and a
  separate `gold_optimization_state` view when the builder is split.
- Add adversarial cases in `tests/test_fitcv_analytics.py` and
  `tests/test_acceptance_state.py`.

### Required behavior

1. **Authoritative invalidation:** group observations by logical entity, order
   by authoritative revision or `observed_at`, and let the newest authoritative
   state determine current validity. Retain all Bronze observations and expose
   history/supersession IDs. A newer invalid or retracted observation makes the
   Silver current fact unavailable; an older valid observation must not win.
2. **Independent cohort membership:** preserve canonical requirement identity
   separately from posting-requirement observation and cohort membership. A
   requirement observed in two windows must remain present in both cohorts.
3. **Posting inventory denominator:** add an explicit `posting_inventory`
   observation contract containing `posting_id`, `cohort_id`, `eligible`,
   `extraction_status`, `source`, and `collected_at`. Skill demand counts all
   eligible postings, including valid-empty extraction results. Unknown
   extraction coverage returns unavailable rather than a false percentage.
4. **First-pass accepted artifact:** count first-pass success only when
   generation attempt one succeeds, the canonical accepted-artifact predicate
   in `src/fitcv_cp/run_artifact_contracts.py` confirms a durable accepted
   artifact, and no regeneration preceded acceptance. A successful generation
   without accepted artifact remains unsuccessful/unavailable for this metric.
5. **Optimization separation:** remove `optimization_status` from
   `gold_acceptance_state` unless the state contract proves it belongs there;
   prefer a separate `gold_optimization_state` projection sourced from
   `state.optimization_result`.
6. **P1-A/P1-B display semantics:** preserve historical P1-A acceptance rows
   while marking R6-unavailable as P1-B measurement unavailable/incomplete.
   Acceptance verifier success must mean state consistency, not runtime proof.
7. **Candidate revision identity:** candidate-gap rows carry
   `candidate_profile_id`, `candidate_profile_revision`, and
   `candidate_profile_fingerprint`; old gap rows remain interpretable after
   profile changes.

### Steps

- [x] Add failing fixtures for newer invalidation, mixed cohorts, valid-empty
  postings, unknown extraction, missing accepted artifacts, optimization-state
  separation, mixed P1-A/P1-B evidence, and candidate revision changes.
- [x] Implement revision ordering and invalidation handling in
  `build_silver_facts` without deleting Bronze history.
- [x] Add posting-inventory and cohort-membership paths to Silver and update
  `build_gold_requirement_demand` denominator/coverage logic.
- [x] Rebuild first-pass fields from accepted-artifact identity and regeneration
  lineage; update `config/analytics_metrics.yaml` wording and null policy.
- [x] Split acceptance and optimization projections; update SQL views and
  generated acceptance-state references through canonical rebuild commands.
- [x] Add direct regression assertions for all four reproduced defects and
  deterministic digest stability.

### Verification

- `python -m pytest -q tests/test_fitcv_analytics.py tests/test_acceptance_state.py`
- `python scripts/verify_fitcv_acceptance.py --timeout-seconds 300 --output .tmp/pr89-acceptance-report.json`
- Rebuild `tests/fixtures/analytics_semantic_contract.json` twice and compare
  material Gold digests.
- Execute all declared Gold SQL views against disposable SQLite.
- `git diff --check`
- Confirm no files under `src/fitcv/agentic_cv_generation.py`,
  `src/fitcv/cv_generator.py`, or provider routing modules changed.

### Exit criteria

All four reproduced defects fail before the patch and pass afterward; every
corrected metric has explicit grain and coverage; P1-A historical acceptance
does not imply P1-B current measurement; candidate gaps are revision-bound;
and CV-generation behavior is unchanged.

## PR #90 — Analytics source integration and semantic metrics

### Purpose

Provide one read-only operational-to-Bronze export path and make registry
metrics executable through one semantic relation.

### Task function

Source export, replayability, semantic metric materialization, and contract
integration.

### Files and symbols

- Add `scripts/export_fitcv_analytics_source.py` with pure collection helpers
  and CLI `main`.
- Add or reuse an explicit database-bound snapshot helper in
  `src/fitcv_cp/sqlite_store.py`, such as `open_readonly_snapshot(database_path)`;
  it must open SQLite with URI `mode=ro`, begin one consistent read
  transaction, and never execute writable setup such as `PRAGMA journal_mode=WAL`.
  Adapt `list_runs`, `get_run_detail`, `iter_run_jobs_for_export`,
  `list_cv_versions`, `list_requirement_resolutions`, and review/evaluation
  readers to consume that connection or query through exporter-owned readers.
  Do not resolve the global default database and do not add schema mutations.
- Reuse canonical profile identity from `src/fitcv/candidate.py`:
  `canonical_candidate_checksum` and persisted profile revision fields.
- Extend `scripts/fitcv_analytics.py` with one semantic-metric builder called
  by `rebuild_analytics_bundle`.
- Extend `scripts/sql/fitcv_gold_views.sql` with `gold_semantic_metric`.
- Add `tests/test_export_fitcv_analytics_source.py` and extend
  `tests/test_fitcv_analytics.py`.
- Update `config/analytics_metrics.yaml` with executable metric versions and
  semantic output fields.

### Required behavior

- `python scripts/export_fitcv_analytics_source.py --database .tmp/fitcv-analytics.sqlite3
  --output .tmp/analytics-source.json` reads operational/imported state without
  modifying it.
- Export contains imported postings, posting source metadata, posting
  inventory/extraction status, requirements, candidate profile revision,
  requirement/evidence coverage, generation attempts, provider attempts,
  review actions, accepted artifacts, render proof, and cohort/source metadata.
- Export has a versioned schema, source database hash, source commit, input
  fingerprint, deterministic ordering, and no credentials or raw private
  secrets.
- Export reads one consistent snapshot. Two database paths produce two
  independent exports; a missing path fails before output creation; concurrent
  writes do not produce a mixed-run export; source database bytes and sidecars
  remain unchanged.
- Existing `scripts/fitcv_analytics.py --input` accepts the exported bundle
  without manual fixture construction.
- Semantic builder computes every registry metric from corrected Gold rows,
  including numerator, denominator, value, coverage, and unavailable reason.
- Rebuild is idempotent and isolated from the request path.

### Steps

- [x] Add a temporary SQLite fixture containing one run, one accepted artifact,
  one failed/retried job, imported postings, valid-empty extraction, candidate
  profile revision, review action, and render proof.
- [x] Implement read-only source collection with explicit table/API ownership;
  reject missing required source identity instead of silently dropping rows.
  Verify explicit database binding, URI read-only mode, one transaction
  snapshot, no WAL/journal mutation, and no global database fallback. If a
  live `-wal`/`-shm` sidecar exists, fail closed unless a caller supplies a
  separately checkpointed snapshot; never open the source in a way that creates
  or mutates sidecars.
- [x] Add sanitized export and replay tests, including byte-stable output,
  database non-mutation, secret-field exclusion, and source-hash mismatch.
- [x] Implement `build_gold_semantic_metric` and materialize one row per
  registry metric/dimension/cohort.
- [x] Add SQL smoke queries and compare semantic values against direct Gold
  builder outputs.
- [x] Document one clean rebuild command using the exported source bundle.

### Verification

- `python -m pytest -q tests/test_export_fitcv_analytics_source.py tests/test_fitcv_analytics.py tests/test_acceptance_state.py` (50 passed)
- Export from disposable SQLite, hash database and any sidecars before/after,
  and assert byte equality; verify live-WAL inputs fail closed without changing
  source bytes.
- Re-run export and analytics rebuild twice; compare source bundle and material
  digest bytes.
- Execute `gold_semantic_metric` SQL view and assert all eight registry metrics
  appear with declared grain, coverage, and unavailable semantics.
- `python scripts/verify_fitcv_acceptance.py --timeout-seconds 300 --output .tmp/pr90-acceptance-report.json` (passed at `a890849c9d72d3ebf09bc6bd7a2d293928b67ab2`)
- `python -m pytest -q` (3262 passed, 8 skipped)
- `git diff --check`

### Exit criteria

A clean command exports supported operational state, rebuilds Bronze → Silver →
Gold → semantic metrics without fixture hand-editing, preserves source DB
bytes, excludes secrets, and gives CI/evidence/dashboard one canonical KPI
record.

## PR #91 — P1-C dashboard MVP

### Purpose

Deliver user-facing imported-corpus intelligence from canonical semantic
metrics and corrected Gold projections.

### Task function

Full-stack dashboard integration, API contract, accessible presentation, and
source-posting drill-down.

### Files and symbols

- Add `src/fitcv_cp/analytics_dashboard.py` with read-only projection loading,
  response shaping, coverage guards, and source-posting drill-down helpers.
- Modify `src/fitcv_cp/app.py` to expose `GET /analytics/overview` and
  `GET /analytics/postings/{posting_id}` through existing app wiring.
- Add `tests/test_analytics_dashboard.py` for API shape, authorization/error
  paths, stale/unavailable metrics, candidate revision mismatch, and
  posting drill-down.
- Modify `config/acceptance_state.yaml`, `config/evidence_registry.yaml`, and
  regenerate `artifacts/acceptance_state.json` only after P1-C dashboard
  acceptance proof passes; do not change P1-B measurement status here.
- Add frontend feature files:
  `frontend/src/features/analytics-dashboard/route.tsx`, `api.ts`, `types.ts`,
  `page.tsx`, and focused components for overview, demand, gaps, metadata, and
  drill-down.
- Add `frontend/e2e/analytics-dashboard.spec.ts` and component tests beside
  the feature.

### Required behavior

- Sections: opportunity landscape, requirement demand, personal evidence gaps.
- Labels say **Imported-corpus demand**, never market-wide demand.
- Every section shows sample size, source mix, collection window, cohort ID,
  coverage status, and candidate profile revision where applicable.
- Gap categories remain separate: `missing_evidence`, `unmet_qualifier`,
  `uncertain_interpretation`.
- UI wording says “No verified evidence for X exists in profile revision R”;
  it must not claim the candidate lacks skill X.
- R6-unavailable renders as measurement unavailable/incomplete while P1-A
  historical acceptance remains visible and separately labeled.
- Incomparable cohorts and incomplete denominators render unavailable with a
  reason; no zero substitution.
- Posting drill-down shows source posting, requirement evidence, extraction
  status, and the exact cohort/profile revision used.
- API reads the canonical semantic projection; no frontend KPI formulas and no
  direct operational SQLite access.

### Steps

- [ ] Freeze API response schema from `gold_semantic_metric`,
  `gold_requirement_demand`, `gold_candidate_gap`, and posting inventory.
- [ ] Freeze candidate-gap uniqueness and API selection on
  `candidate_profile_id`, `candidate_profile_revision`, and
  `candidate_profile_fingerprint`; add simultaneous same-cohort/two-profile and
  two-revision fixtures.
- [ ] Implement backend projection and route tests before frontend wiring.
- [ ] Implement route registration using existing feature-route discovery and
  reuse current design tokens/components.
- [ ] Add keyboard/focus, responsive, empty/unavailable, error, and reduced
  motion states.
- [ ] Add browser proof for overview, demand, gap category, revision metadata,
  and posting drill-down.
- [ ] Confirm all displayed values match API semantic rows exactly.
- [ ] Publish P1-C acceptance evidence, update only P1-C implementation and
  acceptance dimensions from `deferred` to their verified state, refresh
  `config/evidence_registry.yaml`, and regenerate `artifacts/acceptance_state.json`
  through `scripts/render_acceptance_state.py`. Keep P1-B measurement
  `incomplete` and P1-B evidence unavailable unless PR #92 passes.

### Verification

- `python -m pytest -q tests/test_analytics_dashboard.py tests/test_fitcv_analytics.py tests/test_acceptance_state.py`
- `npm --prefix frontend run test -- analytics-dashboard`
- `npm --prefix frontend run typecheck`
- `npm --prefix frontend run build`
- Create disposable projection data with
  `python scripts/fitcv_analytics.py --input tests/fixtures/analytics_semantic_contract.json --output .tmp/analytics-dashboard.json --sqlite-output .tmp/analytics-dashboard.sqlite3 --source-commit (git rev-parse HEAD) --declared-input-fingerprint dashboard-fixture --ingested-at 2026-10-06T00:00:00Z`.
- Start an owned backend with the disposable projection bound explicitly:
  set `FITCV_CP_SQLITE_PATH` and `FITCV_ANALYTICS_SQLITE_PATH` to the absolute
  `.tmp/analytics-dashboard.sqlite3` path, launch
  `python -m uvicorn fitcv_cp.main:app --host 127.0.0.1 --port 8000` with
  `Start-Process -PassThru`, and retain its PID. Poll `GET /healthz` until it
  returns `200`, then call `GET /analytics/overview` and require response
  `input_fingerprint=dashboard-fixture` before browser tests start. Run
  `npm --prefix frontend run test:e2e -- e2e/analytics-dashboard.spec.ts`.
  Use a `try/finally` cleanup that stops the owned PID; fail if port `8000` was
  already occupied or if the probe reports any operational input path. The
  browser test must not use the operational database.
- Run browser accessibility snapshot and viewport checks for desktop and narrow
  layout; verify keyboard navigation and unavailable/error states.
- `git diff --check`

### Exit criteria

Users can inspect opportunity distribution, imported-corpus requirement demand,
and revision-bound candidate evidence gaps with source-posting traceability.
No predictive trend or unsupported market claim appears; all KPI values come
from PR #90 semantic rows.

## PR #92 — Fresh P1-B R7 measurement

### Purpose

Produce current, reproducible runtime-efficiency evidence without attempting
further R5 recovery.

### Task function

Controlled workload capture, replayable evidence packaging, verifier promotion,
and optimization-readiness proof.

### Files and symbols

- Extend `scripts/benchmark_cv_efficiency.py` only where required to consume an
  R7 manifest/replay bundle and emit deterministic evidence.
- Extend `scripts/verify_fitcv_acceptance.py` with explicit R7 validation while
  preserving R5 historical/R6 unavailable behavior.
- Update `config/evidence_registry.yaml` and `config/acceptance_state.yaml` only
  after verifier output is fresh and complete.
- Add sanitized R7 manifest/replay fixture and evidence under
  `docs/superpowers/evidence/`.
- Add focused tests under `tests/test_fitcv_cp/test_acceptance_verifier.py` and
  the benchmark test module.

### Required R7 package

Retain:

```text
manifest
replay bundle or sanitized database
run IDs and repeat count
source commit
provider/model identity
candidate profile revision and fingerprint
fixture hash
declared input fingerprint
analytics contract version
metric registry version
source DB/replay hash
```

The verifier promotes `measurement_status: incomplete` to `measured` only when
it can independently rebuild the package, confirm complete telemetry, and
reconcile material digests. Missing or opaque inputs fail closed.

### Steps

- [ ] Freeze workload, provider/model, candidate profile revision, run count,
  acceptance criteria, and measurement thresholds before execution.
- [ ] Generate a new current cohort and immutable replay package in disposable
  storage; do not overwrite R5/R6 artifacts.
- [ ] Measure provider calls, tokens, latency, regeneration, accepted artifact,
  render proof, and human actions with explicit coverage.
- [ ] Run benchmark and analytics rebuild from the retained R7 package.
- [ ] Validate evidence JSON, Markdown, digest, registry, and acceptance state
  against the same source commit and input identity.
- [ ] Record failure/work categories for later Pareto analysis; do not change
  production routing in this PR.

### Verification

- Run the R7 benchmark with exact peer manifests. Create
  `.tmp/r7/local-first-manifest.json` and
  `.tmp/r7/provider-first-manifest.json` with ten unique run IDs per arm,
  identical fixture/input identity, and opposite `arm` values. Run
  `python scripts/benchmark_cv_efficiency.py --database .tmp/r7/fitcv-r7.sqlite3 --run-manifest .tmp/r7/local-first-manifest.json --output-json docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7.json --output-markdown docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7.md --canonical-evidence-json docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-canonical.json --canonical-evidence-markdown docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-canonical.md --source-commit (git rev-parse HEAD)` and run the same command with `provider-first-manifest.json`, outputting `docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-peer.json` and `docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-peer.md`.
- Run the explicit experiment verifier with all required R7 artifacts:
  `python scripts/verify_fitcv_acceptance.py --state config/acceptance_state.yaml --experiment-json docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7.json --experiment-markdown docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7.md --experiment-peer-json docs/superpowers/evidence/2026-10-06-fitcv-p1b-r7-peer.json --timeout-seconds 300 --output .tmp/pr92-acceptance-report.json`.
- Reject a plain verifier invocation without `--experiment-json`,
  `--experiment-markdown`, and `--experiment-peer-json`; that path can report
  `not_requested` and cannot promote R7.
- Verify peer manifests use opposite `local_first`/`provider_first` arms,
  share declared workload/input identity, and are not duplicate copies of one
  report. Add verifier regressions for missing peer, same-arm peer, and
  mismatched run/fingerprint identity before promotion.
- Rebuild R7 analytics twice and compare material digests.
- Confirm verifier rejects missing run, provider, token, render, or accepted
  artifact coverage.
- Confirm operational database and CV-generation request path remain unchanged.
- `git diff --check`

### Exit criteria

R7 evidence is current, replayable, independently verified, and registry-bound;
P1-B measurement becomes `measured` only with complete proof. Optimization
remains unchanged until a separate decision uses the measured failure/work
Pareto.

## Cross-PR acceptance matrix

| Milestone | Must prove | Must not claim |
|---|---|---|
| PR #89 | authoritative revisions, preserved cohorts, explicit posting denominator, accepted-artifact first pass, separate evidence dimensions | current runtime measurement or dashboard readiness |
| PR #90 | read-only operational export and one semantic metric source | request-path analytics or secret-bearing export |
| PR #91 | P1-C dashboard with coverage, source mix, cohorts, revisions, drill-down | market-wide demand, prediction, or unsupported candidate inability |
| PR #92 | current replayable R7 measurement and verifier promotion | optimization improvement or routing change |

## Final verification

Before declaring this plan complete:

- [ ] PR #89 merged with focused analytics/evidence proof.
- [ ] PR #90 merged with export replay and semantic metric proof.
- [ ] PR #91 merged with backend, frontend, browser, accessibility, and
  contract proof.
- [ ] PR #92 merged only if R7 evidence is complete; otherwise leave P1-B
  measurement explicitly incomplete and record blocker evidence.
- [ ] Full repository tests pass after each PR merge.
- [ ] `git diff --check` passes after each PR merge.
- [ ] `skill-verification-before-completion` returns `verified`.
- [ ] P2, predictive trends, and optimization remain deferred unless separately
  approved.

## Completion criteria

Analytics correctness is complete when revisions/invalidation are authoritative,
historical cohorts remain distinct, denominators derive from explicit posting
inventory, first-pass acceptance requires a durable accepted artifact, candidate
gaps carry profile revision identity, and every KPI is computed by one semantic
metric implementation.

P1-C is complete when FitCV shows opportunity distribution, imported-corpus
requirement demand, and candidate evidence gaps with sample size, source mix,
collection window, extraction coverage, candidate revision, and source-posting
traceability.

P1-B measurement is complete only when a fresh R7 package is independently
rebuildable and verified. R5/R6 unavailable evidence remains historical or
unavailable; no inferred replacement is permitted.
