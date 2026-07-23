---
layer: change
artifact_type: plan
status: proposed
template_id: implementation-plan
name: fitcv-preference-optimization-implementation
parent_spec: docs/superpowers/specs/2026-07-23-12-31-fitcv-preference-optimization-frontend-backend-integration-spec.md
targets:
  - config/policy/decision_learning.yaml
  - src/fitcv/decision_feedback.py
  - src/fitcv/preference_policy.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_stage_runner.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/store.py
  - src/fitcv_cp/optimization_service.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/optimization.html
  - docs/fitcv-settings-ui-prototype.html
  - docs/fitcv-settings-ui-prototype.integration.md
  - tests
---

# FitCV Preference Optimization Implementation Plan

## Goal

Deliver packaged-local Preference Optimization as one server-rendered vertical slice: revisioned workspace Ranking Mode and Personalization Strength, synchronous traceable Optimization Runs, domain-wide single-policy lifecycle, safe baseline fallback, historical evidence details, reversible hide metadata, and accessible Pipeline-consistent UI. Preserve internal training identities, CAS/provenance checks, append-only audit history, completed-run snapshots, and local security boundaries.

## Implementation Outcomes

### Workspace Ranking Controls

`preference_optimization.ranking_mode` and `preference_optimization.personalization_strength` persist in existing `pipeline_settings`, share one revision, use policy-owned strength metadata, block strength changes while any policy is active, and drive runtime selection after refresh and restart.

### Public Traceable Optimization Runs

Every accepted synchronous optimization attempt persists one terminal `preference_optimization_runs` projection with deterministic `por_` public identity, immutable settings/evidence snapshot, one-to-one internal `training_run_id` reference, and reversible `hidden_at` visibility metadata without exposing internal identity in normal UI.

### Audited Singular Policy Lifecycle

Activation enforces one active policy per domain, inactivation performs audited fixed-target rollback to `zero_residual`, Personalized Ranking remains selected after inactivation, incompatible active policy displays `Active · Not in use`, and Remove hides only non-active runs.

### Consistent Local UI And Proof

Main and direct-detail pages use existing Pipeline setting, dialog, table, button, status, and Console patterns; backend guards every disabled UI action; focused persistence, runtime, route, template, security, prototype, browser, accessibility, and regression checks pass before temporary integration sidecar removal.

## Execution Approach

- Mode: `inline sequential`
- Required skills: `skill-test-driven-development`, `skill-code-standards`, `skill-full-stack-integration`, `ui-ux-pro-max`, `skill-verification-before-completion`
- Isolation: current workspace; preserve unrelated uncommitted changes and do not create a worktree unless execution begins with a dirty-tree conflict
- Parallel ownership: none; settings, lifecycle persistence, runtime contracts, routes, and templates share contract fields and must land in dependency order
- Sequential fallback: policy/settings contract, persistence migration, lifecycle/store facade, optimization service, runtime resolver, routes/context, templates/prototype, final integration proof

## Task Breakdown

### Task 1: Add Policy Metadata And Workspace Settings

**Purpose:**
- Establish one validated source for strength bounds/default and two revisioned workspace controls.

**Specification Coverage:**
- Workspace Settings; Strength Metadata and Validation; Mode and Strength Mutation.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect: `config/policy/decision_learning.yaml:decision_learning_policy.inverse_optimization`
- Modify: `config/policy/decision_learning.yaml:decision_learning_policy.inverse_optimization`
- Modify: `src/fitcv/decision_feedback.py:_INVERSE_OPTIMIZATION_KEYS`
- Modify: `src/fitcv/decision_feedback.py:_validate_inverse_optimization_policy`
- Modify: `src/fitcv_cp/settings_schema.py:SETTINGS_SCHEMA`
- Modify: `src/fitcv_cp/settings_schema.py:coerce_value`
- Modify: `src/fitcv_cp/settings_schema.py:validate_settings`
- Modify: `src/fitcv_cp/settings_schema.py:merge_and_validate_settings`
- Modify: `src/fitcv_cp/settings_schema.py:apply_settings_to_config`
- Reuse: `src/fitcv_cp/settings_store.py:mutate_settings_atomically`
- Verify: `tests/test_config.py`
- Verify: `tests/test_decision_feedback.py`
- Verify: `tests/test_fitcv_cp/test_settings_schema.py`
- Verify: `tests/test_fitcv_cp/test_settings_store.py`
- Verify: `tests/test_fitcv_cp/test_settings_store_sqlite.py`

**Dependencies:**
- Corrected parent specification is approved input.
- Existing `pipeline_settings` and `settings_revision()` remain canonical mutable workspace owner.

**Steps:**
- [ ] Step 1: Add `inverse_optimization.learned_alpha_bounds` with exact `minimum: 0.01`, `maximum: 0.10`, and `step: 0.01`; keep `learned_alpha: 0.05` as recommended/default and retain hard runtime safety `(0, 0.25]`.
- [ ] Step 2: Validate exact bounds keys, finite decimal values, `0 < minimum <= learned_alpha <= maximum <= 0.25`, and positive step that can represent all allowed values without widening runtime safety.
- [ ] Step 3: Add editable schema entries `preference_optimization.ranking_mode` (`baseline|personalized`, default `baseline`) and `preference_optimization.personalization_strength` (default from `learned_alpha`, bounds from policy metadata).
- [ ] Step 4: Keep both values in existing atomic settings transaction; reject direct strength mutation under baseline with `personalized_ranking_required` and preserve stale-revision rollback. Keep active-policy lookup outside generic settings schema/store.
- [ ] Step 5: Project current/minimum/maximum/step/recommended values without copying policy metadata into browser storage or another config owner.

**Verification:**
- [ ] `python -m pytest tests/test_config.py tests/test_decision_feedback.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py -q`
- Expected: policy metadata rejects malformed bounds; defaults are baseline/0.05; valid settings round-trip; invalid, active-policy, and stale-revision writes change no rows.

**Exit Criteria:**
- Settings and metadata have one SSOT, one revision, backend validation, and no UI-owned domain state.

### Task 2: Add Public Run Projection And Schema Migration

**Purpose:**
- Persist public run identity, immutable historical evidence, and reversible list visibility without weakening internal training immutability.

**Specification Coverage:**
- Public Optimization Run Identity; Preference Optimization Run Projection; Historical Rating Evidence Snapshot; Remove From Normal UI; domain-wide active-policy migration; Migration and Compatibility.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/preference_policy.py:build_training_run_identity`
- Add: `src/fitcv/preference_policy.py:build_preference_optimization_run_id`
- Modify: `src/fitcv_cp/sqlite_store.py:CONTROL_PLANE_SCHEMA_VERSION`
- Modify: `src/fitcv_cp/sqlite_store.py:_ensure_control_plane_schema`
- Modify: `src/fitcv_cp/sqlite_store.py:_ensure_local_preference_policy_tables`
- Modify: `src/fitcv_cp/sqlite_store.py:persist_candidate_attempt`
- Add: `src/fitcv_cp/sqlite_store.py:get_preference_optimization_run`
- Add: `src/fitcv_cp/sqlite_store.py:list_preference_optimization_runs`
- Add: `src/fitcv_cp/sqlite_store.py:hide_preference_optimization_run`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_preference_policy.py`

**Dependencies:**
- Task 1 defines settings revision and strength contract.
- Internal `inverse_training_runs` remains immutable and authoritative for solver result.

**Steps:**
- [ ] Step 1: Build one atomic version-4-to-version-5 migration while retaining version-3 upgrade behavior; write `PRAGMA user_version = 5` only after projection, lifecycle cleanup, uniqueness, and settings initialization all succeed.
- [ ] Step 2: Create `preference_optimization_runs` keyed by deterministic `por_` ID with unique restricted foreign key to `inverse_training_runs(training_run_id)`, immutable settings/evidence payload, `created_at`, nullable `hidden_at`, and nullable `hidden_by`. Require complete settings/evidence fields for new rows; permit explicit null/unavailable markers only for legacy backfill.
- [ ] Step 3: Store ordered unique effective `set_rating` event IDs and minimal immutable display rows (`source_rating_event_id`, run ID, job identity/label, source URL, saved rank, baseline fit/label, rating, rated time) as validated JSON owned by projection row.
- [ ] Step 4: Add update/delete triggers that protect identity and evidence fields while allowing only reversible `hidden_at`/`hidden_by` changes; retain no-delete triggers on training, snapshot, and audit tables.
- [ ] Step 5: Generate public ID from internal content identity deterministically, abort mapping collision/mismatch, and make duplicate candidate persistence return same projection.
- [ ] Step 6: Backfill projection rows for existing training attempts with public identity and available immutable metadata only; mark unavailable settings/evidence explicitly rather than fabricating current state.
- [ ] Step 7: Inspect all active snapshots per domain; retain current-runtime-compatible winner by latest `activated_at` then `policy_snapshot_id`, retire every other active row with one `domain_single_active_migration` event, and abort the migration on any cleanup failure.
- [ ] Step 8: Drop the per-runtime active index and add the domain-wide partial unique index only after active cleanup completes in the same transaction.
- [ ] Step 9: Initialize both workspace keys together: selected compatible active policy becomes `personalized` with its in-bounds strength; no compatible active becomes `baseline` with recommended strength. Do not overwrite already-present Preference Optimization settings.
- [ ] Step 10: Implement visible-list query, direct-detail query including hidden rows, and idempotent hide that blocks active policy owners and appends one `optimization_run_hidden` process event only on first hide.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_preference_policy.py -q`
- Expected: version-4 fixture upgrades atomically without data loss or multiple active domain policies; failed migration leaves version/data unchanged; public IDs are stable and one-to-one; immutable fields reject mutation/deletion; hide is reversible in storage, idempotent, and never deletes history.

**Exit Criteria:**
- Every persisted attempt has one durable public projection or explicit legacy-unavailable projection, and default listing can exclude hidden rows without losing direct traceability.

### Task 3: Enforce Domain-Wide Lifecycle And Store Contract

**Purpose:**
- Replace per-runtime active uniqueness with one active policy per domain and expose public-run lifecycle operations through existing store facade.

**Specification Coverage:**
- Activation; Inactivation; Runtime Gate and Fallback; Remove From Normal UI; Local Security actor constraint.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/sqlite_store.py:_ensure_local_preference_policy_tables`
- Modify: `src/fitcv_cp/sqlite_store.py:activate_ranking_policy_candidate`
- Modify: `src/fitcv_cp/sqlite_store.py:rollback_ranking_policy`
- Modify: `src/fitcv_cp/sqlite_store.py:resolve_active_ranking_policy`
- Modify: `src/fitcv_cp/sqlite_store.py:inspect_ranking_policy_lifecycle`
- Add: `src/fitcv_cp/sqlite_store.py:activate_preference_optimization_run`
- Add: `src/fitcv_cp/sqlite_store.py:inactivate_preference_optimization_run`
- Modify: `src/fitcv_cp/store.py:RunStore`
- Modify: `src/fitcv_cp/store.py:ControlPlaneStore`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`
- Verify: `tests/test_fitcv_cp/test_store.py`

**Dependencies:**
- Task 2 projection resolves public run to internal training/snapshot identity and has already migrated domain-wide active uniqueness.

**Steps:**
- [ ] Step 1: Keep existing snapshot-ID lifecycle functions as internal compatibility operations. Add public-run activation wrapper that resolves projection and performs hidden/non-candidate/stale/incompatible checks in same transaction before retiring any active domain snapshot, activating target, and appending audit events.
- [ ] Step 2: Add public-run inactivation operation that accepts expected active snapshot, fixes target to `zero_residual`, derives `acted_by=local_workspace`, retires active row, and appends manual-inactivation rollback event without changing Ranking Mode.
- [ ] Step 3: Keep runtime lookup compatibility-aware while lifecycle inspection returns both domain-active and compatible-active projections needed for `Active · Not in use`.
- [ ] Step 4: Extend `RunStore` protocol and `ControlPlaneStore` delegation only with required list/detail/hide/activate/inactivate operations; remove no existing lifecycle safeguards.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py -q`
- Expected: concurrent activation cannot leave two active domain policies; inactivation is audited and fixed-target; hidden active owners are impossible; incompatible active remains visible as lifecycle-active but unusable by runtime.

**Exit Criteria:**
- Store API exposes complete public-run lifecycle while database constraint remains final singularity boundary.

### Task 4: Persist Synchronous Terminal Attempts And Evidence

**Purpose:**
- Make optimization submission read authoritative settings, capture historical inputs, and persist exactly one terminal run per accepted request.

**Specification Coverage:**
- Synchronous Optimization Submission; Terminal Status Projection; Historical Rating Evidence Snapshot; Public Optimization Run Identity.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv_cp/optimization_service.py:_request_evidence_head`
- Modify: `src/fitcv_cp/optimization_service.py:create_ranking_policy_candidate`
- Reuse: `src/fitcv_cp/settings_store.py:load_active_settings`
- Reuse: `src/fitcv_cp/settings_store.py:settings_revision`
- Reuse: `src/fitcv_cp/sqlite_store.py:load_inverse_optimization_request`
- Reuse: `src/fitcv_cp/sqlite_store.py:persist_candidate_attempt`
- Verify: `tests/test_fitcv_cp/test_optimization_service.py`
- Verify: `tests/test_fitcv_cp/test_sqlite_store.py`

**Dependencies:**
- Tasks 1-3 provide settings, projection persistence, and lifecycle lookup.

**Steps:**
- [ ] Step 1: Have route layer load Ranking Mode, Strength, and settings revision from persisted workspace settings, then pass those authoritative values into `create_ranking_policy_candidate`; reject baseline before solver/persistence and ignore or reject submitted numeric strength.
- [ ] Step 2: Build runtime/optimizer input with current persisted strength while preserving policy fingerprints, norm bound, parent, evidence, and provenance compare tokens.
- [ ] Step 3: Extract effective source rating events in canonical sequence, capture minimal historical rows and job-label fallback from canonical run-job projection, and include settings revision/evidence metadata in projection payload.
- [ ] Step 4: Preserve no-run behavior for stale preconditions; persist terminal rows for candidate, no-op, evaluation rejection, insufficient evidence, invalid input, infeasible policy, and solver error handled after request acceptance.
- [ ] Step 5: Return public run ID and deterministic status projection; uncertain retry resolves existing identical run instead of creating duplicate training/projection/audit rows.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_optimization_service.py tests/test_fitcv_cp/test_sqlite_store.py -q`
- Expected: baseline creates no run; accepted submission creates one terminal run; duplicate request reuses identity; historical evidence remains unchanged after later ratings; technical status maps deterministically.

**Exit Criteria:**
- Service owns one synchronous accepted-attempt transaction boundary and returns no durable Running contract.

### Task 5: Gate Runtime Ranking With Workspace Mode And Strength

**Purpose:**
- Make ranking behavior agree with persisted UI controls while preserving completed-run snapshots and safe fallback.

**Specification Coverage:**
- Runtime Gate and Fallback; Persisted Workspace Ranking Controls; completed pipeline result permanence.

**Required Skills:**
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Modify: `src/fitcv/preference_policy.py:PreferenceRuntimeContract.build`
- Modify: `src/fitcv/preference_policy.py:resolve_run_preference_policy`
- Modify: `src/fitcv/pipeline.py:resolve_run_preference_policy` call site
- Modify: `src/fitcv/pipeline_stage_runner.py:resolve_run_preference_policy` call site
- Inspect: `src/fitcv_cp/worker_job.py:resolve_active_ranking_policy` call site
- Verify: `tests/test_preference_policy.py`
- Verify: `tests/test_ranking.py`
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_stage_resume_parity.py`

**Dependencies:**
- Task 1 settings can be applied to effective run config.
- Task 3 compatibility-aware active resolution is available.

**Steps:**
- [ ] Step 1: Extend runtime resolution input with normalized ranking mode and persisted strength; do not mutate policy YAML or active snapshot during resolution.
- [ ] Step 2: Resolve baseline mode directly to zero residual with stable baseline diagnostic even when compatible or incompatible active policies exist.
- [ ] Step 3: In personalized mode, require active policy compatibility across baseline, ranking, embedding, dimension, strength, and norm-bound contract; otherwise return stable zero-residual fallback.
- [ ] Step 4: Preserve existing `existing_payload` fast path so completed and resumed runs use captured policy payload rather than current workspace settings.
- [ ] Step 5: Confirm scoring remains `baseline_fit + personalization_strength × dot(preference_vector, job_embedding)` with unchanged clipping/validation behavior.

**Verification:**
- [ ] `python -m pytest tests/test_preference_policy.py tests/test_ranking.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q`
- Expected: baseline always ranks with zero residual; personalized compatible active uses captured strength; incompatible/missing/store-failure states fall back; completed/resumed output remains stable after later settings changes.

**Exit Criteria:**
- Runtime and page can derive same effective state from canonical settings and lifecycle records.

### Task 6: Add Local Server-Rendered Routes And Page Context

**Purpose:**
- Expose direct main/detail navigation and PRG mutations without JSON API, typed client, polling, actor input, or remote mounting.

**Specification Coverage:**
- Main Page Projection; Optimization Details Projection; Server-Rendered Routes and Local Security; Mode and Strength Mutation; Activation; Inactivation; Remove; Console Log.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-test-driven-development`
- `skill-code-standards`

**Files And Symbols:**
- Inspect impact: GitNexus `api_impact(route="/admin/optimization")` before route edits
- Modify: `src/fitcv_cp/app.py:_optimization_notice_projection`
- Modify: `src/fitcv_cp/app.py:_optimization_error_notice`
- Modify: `src/fitcv_cp/app.py:_optimization_rating_evidence`
- Modify: `src/fitcv_cp/app.py:_optimization_page_context`
- Add: `src/fitcv_cp/app.py:_optimization_detail_context`
- Modify: `src/fitcv_cp/app.py:create_app`
- Modify routes: `src/fitcv_cp/app.py:admin_optimization`
- Modify routes: `src/fitcv_cp/app.py:admin_optimization_candidate`
- Add route: `GET /admin/optimization/runs/{preference_optimization_run_id}`
- Add route: `POST /admin/optimization/ranking-mode`
- Add route: `POST /admin/optimization/personalization-strength`
- Add route: `POST /admin/optimization/runs/{preference_optimization_run_id}/activate`
- Add route: `POST /admin/optimization/runs/{preference_optimization_run_id}/inactivate`
- Add route: `POST /admin/optimization/runs/{preference_optimization_run_id}/remove`
- Verify: `tests/test_fitcv_cp/test_optimization_page.py`
- Verify: `tests/test_fitcv_cp/test_app.py`

**Dependencies:**
- Tasks 1-5 expose canonical settings, run, lifecycle, status, and runtime projections.

**Steps:**
- [ ] Step 1: Confirm route consumers/middleware through GitNexus impact or source fallback; keep existing local Host/Origin/CSRF/onboarding middleware unchanged.
- [ ] Step 2: Register all Preference Optimization routes only in packaged-local mode so non-local requests return 404 by absence, not weaker handler checks.
- [ ] Step 3: Build main context with settings revision, mode, strength metadata, fallback reason, current Rating Evidence, visible run list, domain-active/compatible-active states, disabled reasons, and bounded notices.
- [ ] Step 4: Build detail context by public run ID, including immutable evidence snapshot, status projection, lifecycle action, removed banner, and bounded Console events; return 404 for unknown/internal IDs.
- [ ] Step 5: Implement native form PRG handlers with hidden settings/evidence/parent/provenance tokens, server-derived `local_workspace` actor, explicit confirmation for inactivation, stable notices, `303` redirects, and no fetch/JSON fallback. Reject direct Strength, Optimize, Activate, Inactivate, and Remove mutations under baseline; reject Strength while any policy is active.
- [ ] Step 6: Retain existing snapshot activation/rejection/rollback backend functions only for compatibility; remove old Reject/generic rollback forms from rendered UI and never accept operator actor from new forms.
- [ ] Step 7: Keep Console Clear browser-only by rendering a clear control with no backend mutation route.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_cp/test_app.py -q`
- Expected: main/detail and all PRG success/conflict/error paths use public IDs; local mode works; non-local returns 404; Host/Origin/CSRF remain 403; onboarding unsafe mutations remain 409; actor spoof and numeric strength payloads cannot affect state.

**Exit Criteria:**
- Core flow works with server-rendered forms and direct URLs only, with backend enforcing every disabled UI rule.

### Task 7: Replace Production UI And Align Prototype Intent

**Purpose:**
- Render approved four-section main page and three-section detail page using existing design language and accessible states.

**Specification Coverage:**
- Main Page Projection; Optimization Details Projection; Terminal Status Projection; Frontend Accessibility and Layout; approved UI intent.

**Required Skills:**
- `ui-ux-pro-max`
- `skill-full-stack-integration`

**Files And Symbols:**
- Modify: `src/fitcv_cp/templates/optimization.html`
- Reuse: `src/fitcv_cp/templates/_process_console.html`
- Modify: `docs/fitcv-settings-ui-prototype.html:renderPreferenceOptimizationPage`
- Modify: `docs/fitcv-settings-ui-prototype.html:renderOptimizationDetailsPage`
- Modify: `docs/fitcv-settings-ui-prototype.html:savePersonalizationStrength`
- Modify: `docs/fitcv-settings-ui-prototype.html:optimizationRunsRows`
- Verify: `tests/test_fitcv_cp/test_optimization_page.py`
- Verify: `tests/test_fitcv_pipeline_prototype.py`

**Dependencies:**
- Task 6 page contexts and routes are stable.

**Steps:**
- [ ] Step 1: Replace technical production layout with Section 1 Ranking Mode, Section 2 Personalization Strength with Manage, Section 3 Rating Evidence with Optimize Current Ratings, and Section 4 Optimization Runs.
- [ ] Step 2: Render direct detail in same template contract with top-right Activate/Inactivate, Overview, historical Rating Evidence, and Console Log only; omit Policy Version, Results Summary, Technical Details, Reject, and generic rollback UI.
- [ ] Step 3: Use native select/dialog/form/table/details controls, shared classes/tokens, adjacent disabled reasons, visible focus, screen-reader descriptions, button pending text `Optimizing…`, and one client-side duplicate-submit guard that does not replace backend validation.
- [ ] Step 4: Under baseline, disable Manage, Optimize, Activate, Inactivate, and Remove actions consistently; under personalized fallback, show baseline-use message; show incompatible active as `Active · Not in use` with Inactivate available.
- [ ] Step 5: Render terminal labels `Succeeded`, `No Change`, `Not Created`, and `Failed`; render hidden detail as `Removed from Optimization Runs` with no lifecycle action; expose no Restore UI.
- [ ] Step 6: Keep Rating Evidence columns identical on main/detail and implement Console Clear as current-DOM removal only; reload restores server events.
- [ ] Step 7: Align prototype local-state behavior and self-check wording with final server contract, including blocked Strength save while active, baseline-disabled actions, manual inactivation fallback, and reversible hidden metadata without Restore UI.

**Verification:**
- [ ] `python -m pytest tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_pipeline_prototype.py -q`
- Expected: template assertions cover all sections/actions/statuses/disabled reasons; prototype contract matches approved wording and no removed technical UI remains.

**Exit Criteria:**
- Production and prototype show same approved behavior while production truth remains server-owned.

### Task 8: Run End-To-End Verification And Retire Sidecar

**Purpose:**
- Prove complete vertical slice, record any plan deviation, and remove temporary integration intent only after canonical evidence passes.

**Specification Coverage:**
- All acceptance criteria and completion criteria in parent specification.

**Required Skills:**
- `skill-full-stack-integration`
- `skill-verification-before-completion`

**Files And Symbols:**
- Verify: `docs/superpowers/specs/2026-07-23-12-31-fitcv-preference-optimization-frontend-backend-integration-spec.md`
- Delete after proof: `docs/fitcv-settings-ui-prototype.integration.md`
- Verify: all files and tests changed by Tasks 1-7

**Dependencies:**
- Tasks 1-7 complete with task-local checks passing.

**Steps:**
- [ ] Step 1: Run focused backend and runtime suites, then affected prototype suite and `git diff --check`; fix only regressions caused by this implementation.
- [ ] Step 2: Start isolated local app against fresh data with `py -3 -m uvicorn fitcv_cp.main:app --host 127.0.0.1 --port 8877` and exercise baseline, personalized fallback, optimize, activate, incompatible active, inactivate, strength save, remove, hidden direct detail, refresh, Back, Forward, and Console Clear.
- [ ] Step 3: Use Playwright MCP for repeatable forms, keyboard/focus flow, direct URLs, narrow viewport, 200% zoom, light/dark theme, reduced motion, screenshots, and accessibility snapshot.
- [ ] Step 4: Use Chrome DevTools MCP only for console/network diagnosis and confirmation that forms submit expected tokens with no JSON client/polling; do not duplicate Playwright checks.
- [ ] Step 5: Verify security matrix: non-local 404, invalid Host/Origin/CSRF 403, onboarding unsafe 409, server-derived actor, no public internal IDs, bounded logs, no free-text rating leakage, and no delete path.
- [ ] Step 6: Verify SQLite directly or through store tests: one active domain policy, immutable training/evidence payload, idempotent public identity, one hide event, retained hidden details, and rollback audit.
- [ ] Step 7: Reconcile plan checkboxes/deviations, remove `docs/fitcv-settings-ui-prototype.integration.md` only when every required evidence item passes, and run final documentation validators.

**Verification:**
- [ ] Complete every command and evidence item in final `## Verification` section.
- Expected: affected suites and browser/security evidence pass; changed planning artifacts validate in isolation; unrelated repository-wide findings are recorded separately and do not mask changed-artifact validation.

**Exit Criteria:**
- Fresh evidence satisfies parent specification; no unresolved contract conflict remains; integration sidecar is removed or reduced to exact unresolved blocker only.

## Verification

- `python -m pytest tests/test_config.py tests/test_decision_feedback.py tests/test_preference_policy.py tests/test_ranking.py tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_settings_store.py tests/test_fitcv_cp/test_settings_store_sqlite.py tests/test_fitcv_cp/test_sqlite_store.py tests/test_fitcv_cp/test_store.py tests/test_fitcv_cp/test_optimization_service.py tests/test_fitcv_cp/test_optimization_page.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_pipeline_prototype.py -q`
- Directly call `scripts/validate_planning_lifecycle.py:validate_artifact` for corrected spec and this plan; both return no findings.
- Load `scripts/validate_template_required_sections.py` rules and validate corrected spec and this plan only; both return no findings.
- Run repo-wide planning/template validators as informational diagnostics; record exact pre-existing unrelated findings without treating them as changed-artifact failures.
- `git diff --check`
- Browser evidence from isolated `127.0.0.1:8877` local app covers required main/detail states, keyboard/focus, narrow layout, 200% zoom, light/dark, reduced motion, direct navigation, Console Clear, and clean console/network.
- Security evidence covers local-only mounting, Host/Origin/CSRF/onboarding guards, server-derived actor, internal-ID non-disclosure, bounded logs, immutable records, and hide-not-delete behavior.

## Completion Criteria

The plan is ready for completion verification when:

1. every required implementation outcome is satisfied
2. every required task and task-local verification item is complete
3. plan deviations, substitutions, blockers, and deferrals are recorded
4. changed code, configuration, tests, validators, documentation, and generated outputs are reconciled with current repository truth
5. final verification commands are identified and runnable
6. Ranking Mode and Strength persist workspace-wide and agree with runtime
7. accepted optimization submissions persist one terminal public run with historical evidence
8. activation/inactivation/hide preserve singular lifecycle, audit, immutability, and fallback
9. normal UI exposes no internal training ID, Reject, generic rollback, Restore, hard delete, JSON API, typed client, polling, or remote route
10. temporary integration sidecar is removed only after all acceptance evidence passes

The plan may be marked `completed` only when `skill-verification-before-completion`:

1. runs fresh final verification
2. confirms completion criteria against repository evidence
3. finds no unresolved required task, failed required check, stale status, or unrecorded scope deviation
4. returns `verified` and updates plan status

A checked box records progress; it is not proof by itself.
