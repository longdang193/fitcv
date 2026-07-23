---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-preference-optimization-frontend-backend-integration
targets:
  - docs/fitcv-settings-ui-prototype.html
  - docs/fitcv-settings-ui-prototype.integration.md
  - config/policy/decision_learning.yaml
  - src/fitcv/preference_policy.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/optimization_service.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/sqlite_store.py
  - src/fitcv_cp/templates/optimization.html
  - tests/test_fitcv_cp
  - tests/test_fitcv_pipeline_prototype.py
related_features:
  - admin_control_plane_core
  - settings_system
  - inspection_debugging
related_stages:
  - ranking
---

# FitCV Preference Optimization Frontend-Backend Integration Specification

## Authority

- This specification owns target Preference Optimization integration behavior for packaged-local FitCV.
- `docs/fitcv-settings-ui-prototype.html` remains visual and wording reference. This specification owns persistence, runtime behavior, identifiers, lifecycle rules, validation, and failure behavior.
- `docs/fitcv-settings-ui-prototype.integration.md` remains temporary acceptance intent and must not duplicate transport schemas.
- This specification narrows the packaged-local integration and prototype-backend compatibility specifications for Preference Optimization only.
- Existing inverse-optimization specifications remain authoritative for solver math, internal content identities, policy provenance, CAS checks, and retained audit history unless explicitly changed here.

## Goal and Problem

### Problem

- current behavior or opportunity: approved UI uses browser-local state for Ranking Mode, Personalization Strength, Optimization Runs, historical evidence, and policy actions.
- affected users, systems, or maintainers: local operator, ranking runtime, decision-feedback compiler, optimizer, lifecycle store, control-plane templates, and tests.
- evidence: production supports synchronous candidate creation, activation, rejection, and generic rollback; `learned_alpha` is config-only and fingerprinted; lifecycle persistence exposes internal training IDs and lacks historical evidence display snapshots.
- consequence of no change: direct wiring would misrepresent backend state, expose internal IDs, bypass safeguards, or create duplicate setting and audit owners.

### Goal

- desired outcome: integrate approved UI using revisioned workspace settings, synchronous server-rendered forms, audited lifecycle operations, public domain-specific run IDs, immutable evidence traceability, and baseline-safe fallback.
- observable success: refresh, restart, direct details, ranking, optimization, activation, inactivation, and removal agree with canonical persisted state without JSON API, typed client, async jobs, hard deletion, or browser-owned domain truth.

## Required Outcomes

### Outcome: Persisted Workspace Ranking Controls

- affected actor or system: local operator, settings store, and ranking runtime.
- required result: Ranking Mode and Personalization Strength persist workspace-wide through existing revisioned settings storage.
- success condition: page and runtime read same values; browser storage owns neither.

### Outcome: Synchronous Traceable Optimization Runs

- affected actor or system: optimization form, service, and persistence.
- required result: each accepted submission resolves synchronously to one persisted terminal Preference Optimization Run with public ID and captured inputs.
- success condition: no durable `Running` state or polling contract; equivalent duplicate submissions resolve to same run.

### Outcome: Safe Policy Lifecycle

- affected actor or system: activation, inactivation, runtime fallback, and audit history.
- required result: activation preserves CAS/provenance checks; inactivation performs audited rollback to `zero_residual`; one domain policy is active at most.
- success condition: Ranking Mode remains Personalized after inactivation and UI shows baseline fallback until another compatible policy becomes active.

### Outcome: Historical Evidence and Details

- affected actor or system: Optimization Runs table and detail page.
- required result: each new run stores evidence fingerprint, watermark, source rating-event IDs, and minimal immutable rows needed for Rating Evidence.
- success condition: details render historical snapshot and retain canonical references.

### Outcome: Consistent Accessible Server-Rendered UI

- affected actor or system: Jinja page, forms, dialogs, tables, and navigation.
- required result: production follows approved Pipeline setting patterns, native controls, PRG, explicit disabled reasons, responsive layout, and WCAG 2.2 AA behavior.
- success condition: baseline, personalized, fallback, empty, submitting, terminal, active, inactive, hidden, stale, and validation states render without redesign.

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| Where can workspace settings live? | Existing `pipeline_settings` supports atomic mutation and revision conflicts. | `src/fitcv_cp/settings_store.py` | high | Reuse it; no second settings table. |
| How is mode determined now? | Page derives learned, incompatible, or zero-residual mode from lifecycle. | `src/fitcv_cp/app.py` | high | Add independent persisted mode consumed by runtime. |
| Is optimization asynchronous? | Solver and evaluation finish inside candidate POST before persistence returns. | `src/fitcv_cp/optimization_service.py` | high | Keep synchronous; transient submitting state only. |
| Is strength mutable now? | `learned_alpha` is policy-owned, stored, fingerprinted, and used in scoring. | `config/policy/decision_learning.yaml`, `src/fitcv/preference_policy.py` | high | Validate workspace value and capture it per run/policy. |
| What safeguards exist? | Activation uses actor, parent/evidence CAS, and policy provenance; rollback appends event. | `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py` | high | Preserve them behind simpler UI. |
| Can records be deleted? | Training, snapshots, and activation events form retained audit history. | `src/fitcv_cp/sqlite_store.py` | high | Remove changes list visibility only. |
| Can details reproduce evidence? | Current page reconstructs current ratings; historical display rows are not stored. | `src/fitcv_cp/app.py`, `src/fitcv_cp/sqlite_store.py` | high | Persist minimal immutable display snapshot. |
| What security model applies? | Local mode enforces loopback Host, Origin, CSRF, and onboarding. | `src/fitcv_cp/app.py` | high | Feature remains local-only; actor is server-derived. |
| Is typed transport needed? | Production optimization page uses native forms. | `src/fitcv_cp/templates/optimization.html` | high | No JSON API or generated client. |

### Scope

- included behavior: workspace mode/strength, policy bounds, runtime gate, synchronous submission, public run identity, evidence snapshot, main/detail pages, activation, inactivation, hide-from-list, Console Clear, local security, migration, and focused verification.
- affected boundaries: policy config/validation, settings store, optimization service, runtime resolution, SQLite lifecycle, process events, routes/templates, and tests.
- admissible cases: fresh/migrated workspace, no active policy, insufficient evidence, no-op, candidate, rejected promotion, solver/config failure, stale or duplicate submission, hidden run, and pre-integration run.
- compatibility expectation: solver equations, internal `training_run_id`, policy snapshot identity, vectors, provenance, and completed pipeline results remain unchanged.

### Non-Goals

- JSON API, OpenAPI resource schema, generated client, SPA, or separate frontend.
- durable async jobs, polling, cancellation, background workers, or persisted `Running` status.
- multi-user auth, roles, user-specific settings, or remote/server-mode exposure.
- hard deletion, UI writes to policy YAML, solver redesign, or full source snapshots.
- compliance-grade exact original-source preservation; add only under separate approved requirement.

### Requirements and Behavioral Contract

#### Requirement: Workspace Settings

- trigger or actor: local operator opens or submits Preference Optimization settings.
- preconditions: local mode, completed onboarding, valid Host/Origin/CSRF guard.
- required behavior:
  - store `preference_optimization.ranking_mode` as `baseline|personalized` in existing `pipeline_settings`;
  - store `preference_optimization.personalization_strength` as finite decimal in same owner;
  - return one settings revision covering both values and reject stale mutations;
  - default fresh workspace to `baseline` and policy-recommended strength;
  - expose Baseline Ranking and Personalized Ranking only as presentation labels.
- output or state change: one atomic workspace settings revision.
- failure behavior: invalid field returns field notice; stale revision returns `settings_revision_conflict`; no partial write.
- observable acceptance: values survive refresh/restart and runtime reads same revision.

#### Requirement: Strength Metadata and Validation

- trigger or actor: backend projects or validates Personalization Strength.
- preconditions: valid decision-learning policy.
- required behavior:
  - retain `inverse_optimization.learned_alpha` as recommended/default value;
  - add policy-owned minimum `0.01`, maximum `0.10`, and step `0.01` metadata without duplicating recommended value;
  - retain runtime hard safety check `(0, 0.25]`;
  - validate workspace strength against policy and runtime bounds;
  - project minimum, maximum, step, recommended, and current values to Manage dialog.
- output or state change: validated metadata and current value.
- failure behavior: invalid policy metadata fails configuration load rather than widening bounds.
- observable acceptance: input attributes and backend validation use same policy metadata.

#### Requirement: Runtime Gate and Fallback

- trigger or actor: ranking runtime resolves preference policy.
- preconditions: workspace settings and ranking rows.
- required behavior:
  - `baseline` always resolves zero residual;
  - `personalized` uses only active policy compatible with baseline, ranking, embedding, strength, and norm-bound contract;
  - personalized without compatible active policy resolves zero residual with stable fallback diagnostic;
  - an active but currently incompatible policy remains lifecycle-active, displays `Active · Not in use`, permits Inactivate under personalized mode, and never affects ranking;
  - completed pipeline results retain captured policy and never change later.
- output or state change: learned or zero-residual policy captured in run snapshot.
- failure behavior: unavailable store, missing embedding, dimension mismatch, or contract mismatch safely falls back with bounded diagnostic.
- observable acceptance: visible mode/fallback and ranking order agree.

#### Requirement: Mode and Strength Mutation

- trigger or actor: local operator changes Ranking Mode or Personalization Strength.
- preconditions: current settings revision.
- required behavior:
  - switching to baseline changes runtime selection only; stored policies remain unchanged;
  - switching to personalized reuses current active policy only when compatible;
  - strength Manage is disabled under baseline and backend rejects direct strength mutation with `personalized_ranking_required`;
  - changing strength while any policy is active is rejected with `active_policy_must_be_inactivated`;
  - Manage dialog explains `Inactivate Policy before changing Personalization Strength.`;
  - after explicit audited inactivation, strength saves through the existing settings transaction;
  - Ranking Mode remains personalized and page continues baseline fallback until another compatible policy is activated.
- output or state change: one settings revision after any required inactivation has completed separately.
- failure behavior: active policy or stale settings revision rejects strength save and preserves current value.
- observable acceptance: settings and lifecycle never require a cross-owner partial transaction.

#### Requirement: Synchronous Optimization Submission

- trigger or actor: local operator selects Optimize Current Ratings.
- preconditions: personalized mode, current settings/evidence/parent tokens, valid CSRF, no pending duplicate form submit.
- required behavior:
  - show transient `Optimizing…` and disable submit only during synchronous request;
  - read strength from persisted settings, never submitted numeric field;
  - compile current canonical rating evidence;
  - persist one terminal attempt for handled submissions, including insufficient evidence and promotion rejection;
  - preserve stale-evidence, changed-parent, changed-policy, and provenance checks;
  - use POST/Redirect/GET and show result in Optimization Runs.
- output or state change: one terminal run and, only for `candidate_created`, one candidate snapshot.
- failure behavior:
  - baseline rejects with `personalized_ranking_required` and creates no run;
  - stale precondition creates no misleading run;
  - canonical solver/config terminal failure persists failed run;
  - uncertain transport retry is idempotent.
- observable acceptance: every accepted completed submission has one terminal row; no durable Running row exists.

#### Requirement: Public Optimization Run Identity

- trigger or actor: backend persists or projects an attempt.
- preconditions: canonical internal terminal training identity exists.
- required behavior:
  - retain internal content-addressed `training_run_id` for persistence and diagnostics;
  - assign immutable unique `preference_optimization_run_id` with `por_` presentation prefix;
  - keep one-to-one mapping and deterministic idempotent identity;
  - never render `training_run_id` or accept it in public detail URLs.
- output or state change: stable public run ID.
- failure behavior: collision or mapping mismatch aborts persistence.
- observable acceptance: table links and details use only public ID.

#### Requirement: Preference Optimization Run Projection

- trigger or actor: backend persists, migrates, hides, or projects an Optimization Run.
- preconditions: internal training run exists or is being persisted in same transaction.
- required behavior:
  - define one `preference_optimization_runs` projection entity keyed by `preference_optimization_run_id`;
  - keep `training_run_id` as unique foreign key to immutable `inverse_training_runs`;
  - own public identity, settings revision, evidence fingerprint, event watermark, ordered source rating-event IDs, minimal Rating Evidence rows, creation time, `hidden_at`, and `hidden_by`;
  - make identity, internal reference, settings revision, evidence metadata, and evidence rows immutable after insert;
  - permit reversible `hidden_at`/`hidden_by` visibility metadata at persistence boundary while exposing only Hide/Remove in current UI;
  - never modify immutable training rows to backfill public identity or visibility.
- output or state change: one public projection row per internal training run.
- failure behavior: missing internal run, duplicate mapping, or immutable payload mutation is rejected; visibility reversal has no current route or UI.
- observable acceptance: public details and list visibility have one persistence owner without weakening internal immutability.

#### Requirement: Terminal Status Projection

- trigger or actor: backend projects main or detail page.
- preconditions: canonical terminal status.
- required behavior:
  - `candidate_created` displays `Succeeded` and permits activation while candidate;
  - `no_op` displays `No Change` and no policy action;
  - `evaluation_rejected|insufficient_evidence` displays `Not Created` with plain-language reason;
  - `invalid_input|infeasible_policy|solver_error` displays `Failed` with bounded action text;
  - unknown status displays Failed and logs safe diagnostic.
- output or state change: deterministic label, tone, helper, and actions.
- failure behavior: technical enum never becomes primary user wording.
- observable acceptance: main and detail projections match.

#### Requirement: Historical Rating Evidence Snapshot

- trigger or actor: backend persists accepted optimization attempt.
- preconditions: effective rating states compiled or insufficient evidence established.
- required behavior:
  - store immutable `evidence_head_fingerprint`, `event_watermark`, and ordered unique `source_rating_event_ids`;
  - define source IDs as effective `set_rating` events contributing to compiled preference comparisons, ordered by canonical `event_sequence`;
  - for insufficient evidence, store effective rated event IDs considered by the compiler even when no comparison is emitted;
  - store immutable rows containing `source_rating_event_id`, `run_id`, `alternative_id`, `job_label`, `source_job_url`, `displayed_rank`, `baseline_fit`, `baseline_fit_label`, `rating`, and `rated_at`;
  - source `job_label` from the canonical immutable run-job display projection at optimization time and fall back to `source_job_url` when no label exists;
  - preserve displayed row ordering;
  - exclude raw job payload, Candidate Profile, CV, credentials, prompts, and free-text logs;
  - allow empty rows for insufficient evidence while retaining available trace references.
- output or state change: immutable evidence snapshot owned by public run.
- failure behavior: malformed input that cannot form a canonical evidence envelope creates no run; canonical terminal `invalid_input` persists a Failed run; malformed snapshot row or unmatched event reference aborts projection persistence.
- observable acceptance: later source changes never alter historical details.

#### Requirement: Main Page

- trigger or actor: local operator opens `GET /admin/optimization`.
- preconditions: local mode and completed onboarding.
- required behavior:
  - Section 1 uses native select for Baseline Ranking and Personalized Ranking;
  - Section 2 uses shared setting row and Manage dialog; Manage is disabled under baseline with user-facing reason;
  - Section 3 renders current canonical Rating Evidence and Optimize Current Ratings;
  - Optimize is disabled only under baseline; insufficient evidence becomes terminal run result rather than readiness gate;
  - Section 4 renders non-hidden runs with shared table styling and public IDs;
  - all run actions are disabled under baseline;
  - personalized without compatible active policy shows `Baseline Ranking is being used until a policy is activated.`
  - an active but runtime-incompatible policy displays `Active · Not in use`, keeps baseline fallback visible, and exposes Inactivate Policy only under Personalized Ranking.
- output or state change: server-rendered page with settings revision and lifecycle precondition tokens.
- failure behavior: page load failure preserves navigation and shows actionable error without stale browser domain data.
- observable acceptance: refresh reproduces persisted workspace and lifecycle state.

#### Requirement: Details Page

- trigger or actor: local operator opens `GET /admin/optimization/runs/{preference_optimization_run_id}`.
- preconditions: public run exists, including hidden run.
- required behavior:
  - use direct server URL, not hash routing;
  - top-right action is Activate Policy or Inactivate Policy when applicable;
  - baseline disables action and explains how to enable it;
  - render Overview, Rating Evidence, and Console Log only;
  - omit Policy Version, Results Summary, Technical Details, Reject Version, and generic rollback controls;
  - use historical snapshot and same Rating Evidence table contract as main page;
  - hidden detail shows `Removed from Optimization Runs` and exposes no lifecycle action.
- output or state change: historical detail plus permitted lifecycle action only for visible runs.
- failure behavior: unknown public ID returns 404; internal IDs are not aliases.
- observable acceptance: direct URL, refresh, Back, and Forward preserve run.

#### Requirement: Activation

- trigger or actor: local operator activates successful candidate policy.
- preconditions: personalized mode, visible run, candidate snapshot, current parent/evidence/settings tokens, and current provenance.
- required behavior:
  - preserve existing CAS and compatibility validation;
  - derive `acted_by=local_workspace` server-side and accept no actor field;
  - retire any prior active domain policy and activate target in one transaction;
  - append canonical activation event;
  - enforce one active policy across domain, not only per runtime fingerprint.
- output or state change: target active, previous active retired, event appended, personalized runtime active.
- failure behavior: hidden, stale, or incompatible target changes nothing and returns stable notice; hidden target returns `optimization_run_hidden`.
- observable acceptance: exactly one domain policy active and runtime resolves it.

#### Requirement: Inactivation

- trigger or actor: local operator selects Inactivate Policy.
- preconditions: personalized mode and current expected active snapshot.
- required behavior:
  - use dedicated fixed-target `zero_residual` form action;
  - require explicit confirmation;
  - derive `acted_by=local_workspace` server-side;
  - retire active snapshot and append manual-inactivation rollback event;
  - keep Ranking Mode personalized and show fallback after redirect.
- output or state change: zero-residual runtime and retained retired policy.
- failure behavior: active snapshot conflict aborts without mutation.
- observable acceptance: Inactivate changes to Activate where eligible and fallback appears.

#### Requirement: Remove From Normal UI

- trigger or actor: local operator selects Remove.
- preconditions: run exists and does not own current active policy.
- required behavior:
  - set visibility metadata such as `hidden_at` and server-derived `hidden_by=local_workspace`;
  - exclude hidden run from normal table;
  - retain direct detail, diagnostic references, evidence, policies, and audit events;
  - append one `optimization_run_hidden` process event on first successful Remove;
  - make repeated Remove idempotent;
  - repeated Remove returns existing hidden state without another event;
  - hidden state remains reversible in storage, but current product exposes no Restore action or hidden-runs view;
  - expose no Reject action.
- output or state change: row disappears after PRG; backend record remains.
- failure behavior: active owner returns `active_policy_must_be_inactivated`; unknown run returns not found; no delete occurs.
- observable acceptance: store/process inspection still finds complete history.

#### Requirement: Console Log

- trigger or actor: local operator opens details or selects Clear.
- preconditions: bounded events or empty state.
- required behavior:
  - project bounded events linked through internal diagnostic references;
  - translate technical operations to concise messages while retaining timestamp/level;
  - Clear removes loaded entries from current browser view only;
  - Clear never deletes backend records or events;
  - empty view displays `No console events in current view.`
- output or state change: browser-local cleared view only.
- failure behavior: load failure shows retryable unavailable state and preserves other detail data.
- observable acceptance: reload restores canonical events.

#### Requirement: Server-Rendered Routes and Local Security

- trigger or actor: local browser navigates or submits forms.
- preconditions: feature mounted in local mode.
- required behavior:
  - retain `GET /admin/optimization` and `POST /admin/optimization/candidate`;
  - add direct detail GET and PRG mutations for Ranking Mode, Strength, Inactivate, and Remove;
  - retain candidate activation backend operation and provenance checks; snapshot identity may remain hidden transport data;
  - use native forms, hidden revision/CAS tokens, CSRF middleware, and `303` redirects;
  - return 404 for all feature routes outside local mode;
  - keep Host/Origin/CSRF violations as direct 403 and onboarding unsafe gate as 409.
- output or state change: HTML response or stable-notice redirect.
- failure behavior: no JavaScript client fallback bypasses backend validation.
- observable acceptance: core flow needs no fetch client or generated client.

#### Requirement: Frontend Accessibility and Layout

- trigger or actor: keyboard, pointer, screen reader, narrow container, 200% zoom, reduced motion, light, or dark theme.
- preconditions: any main/detail state.
- required behavior:
  - reuse existing section card, setting row, Manage dialog, table, status, button, and Console patterns;
  - use semantic headings/tables/labels, native controls, focus management, disabled attributes, and visible focus;
  - place disabled reason adjacent to control and expose it to assistive technology;
  - prevent duplicate submission;
  - reflow without fixed text heights or horizontal page overflow;
  - preserve contrast and state distinction in both themes;
  - avoid motion-only status communication.
- output or state change: consistent accessible UI.
- failure behavior: validation summary and field error receive focus; no color-only explanation.
- observable acceptance: WCAG 2.2 AA-focused browser evidence passes.

### Constraints and Alternatives

- expose internal `training_run_id`: rejected; couples UI to solver persistence.
- rename internal ID: rejected; broad migration without user value.
- async job/polling: rejected; current synchronous service satisfies requirement.
- JSON API/client: rejected; server-rendered local application owns current use case.
- hard delete: rejected; visibility metadata satisfies intent without data loss.
- event-only evidence reconstruction: rejected; mutable display metadata prevents stable details.
- full source snapshot: rejected; excess duplication and data exposure without compliance need.

## Design Decisions

### Decision: Workspace Settings Own Mode and Strength

- context: approved UI needs explicit mode and bounded strength.
- selected approach: existing revisioned settings store holds both; YAML owns bounds/default metadata; page and runtime consume same values.
- rationale: one SSOT, no browser truth, no UI YAML writes.
- alternatives considered: lifecycle-derived mode, config-only strength, or arbitrary form alpha.
- accepted trade-offs: personalized mode may show baseline fallback; strength change requires new policy.
- affected owners and boundaries: policy config, settings schema/store, page context, runtime, optimizer, tests.

### Decision: Strength Change Requires Prior Inactivation

- context: alpha participates in optimization and runtime compatibility.
- selected approach: reject strength save while any policy is active and direct operator to Inactivate Policy first.
- rationale: reuses existing safe settings and lifecycle transactions and avoids a new cross-owner composite transaction.
- alternatives considered: one-click combined save/inactivation, silently keep incompatible active policy, or apply new alpha to old vector.
- accepted trade-offs: strength change requires one explicit inactivation action before save, then new optimization and activation.
- affected owners and boundaries: settings validation, lifecycle projection, runtime, dialog.

### Decision: Synchronous Terminal Run

- context: existing solver runs inside POST.
- selected approach: transient submitting state followed by terminal persisted run.
- rationale: no speculative worker/polling infrastructure.
- alternatives considered: durable Running resource.
- accepted trade-offs: long solver requests remain synchronous until measured need proves otherwise.
- affected owners and boundaries: route, service, template, tests.

### Decision: Public Domain Identity, Internal Training Identity

- context: generic training ID should not be public Optimization ID.
- selected approach: `preference_optimization_run_id` with `por_` prefix mapped one-to-one to internal `training_run_id`.
- rationale: presentation decoupling without replacing validated identity.
- alternatives considered: expose or rename internal ID.
- accepted trade-offs: one small public projection table is required because internal training rows remain immutable while visibility is mutable.
- affected owners and boundaries: identity, public run projection, events, routes, templates.

### Decision: Inactivate, Remove, and Evidence Semantics

- context: approved UI removes Reject/generic rollback and requires traceable details.
- selected approach: Inactivate is audited zero-residual rollback; Remove hides non-active row; evidence stores references plus minimal immutable rows.
- rationale: matches UI while preserving lifecycle and data safety.
- alternatives considered: hard delete, rejection alias, current-evidence details, or full snapshots.
- accepted trade-offs: hidden candidates remain retained; old runs may lack historical rows.
- affected owners and boundaries: lifecycle store, visibility projection, evidence persistence, main/detail UI.

### Decision: Server-Rendered and Local Only

- context: packaged application and existing forms cover current use case.
- selected approach: Jinja, native forms, PRG, existing local guard, no non-local mounting.
- rationale: smallest complete integration.
- alternatives considered: JSON client or remote multi-user service.
- accepted trade-offs: separate frontend or durable async work requires future spec.
- affected owners and boundaries: routes, templates, middleware, tests.

### Compatibility, Migration, and Risk

- old behavior: compatible active policy applies automatically; alpha is config-only; production page exposes internal lifecycle tables/IDs and current evidence only.
- new behavior: workspace mode gates runtime; workspace strength is bounded/captured; approved main/detail pages use public IDs and historical evidence; safe mutations replace technical controls.
- compatibility boundary:
  - solver math, internal IDs, vectors, snapshots, provenance, and completed pipeline results remain valid;
  - normal UI stops exposing internal IDs, Reject, and generic rollback;
  - Preference Optimization routes are unavailable outside local mode.
- migration or backfill:
  - fresh workspace defaults to baseline and recommended strength;
  - inspect every active snapshot for the ranking domain before adding domain-wide uniqueness;
  - select the snapshot compatible with current runtime contract; if more than one qualifies, choose latest `activated_at`, then stable `policy_snapshot_id`;
  - retire every other active domain snapshot and append one `retire` event with reason `domain_single_active_migration` for each;
  - add the domain-wide partial unique constraint only after cleanup commits;
  - migrated workspace with selected compatible active policy initializes personalized mode and that policy strength when within current bounds, preserving current ranking behavior;
  - migrated workspace without selected compatible active policy initializes baseline and recommended strength;
  - existing training rows receive deterministic public IDs and visible-by-default metadata;
  - existing rows without display snapshot show fingerprint/watermark and `Historical Rating Evidence is unavailable for runs created before this integration.`;
  - no historical rows are fabricated.
- rollout and rollback:
  - settings validation, persistence, runtime, optimization persistence, routes, templates, and focused tests change together;
  - rollback may ignore new projections but must not delete them or reactivate retired policies.
- deprecation or consumer impact: internal callers may keep training/snapshot IDs; approved UI stops exposing old lifecycle tables/actions.
- risk: page/runtime settings drift.
  - mitigation: one settings owner and captured revision.
- risk: operator tries changing strength while policy remains active.
  - mitigation: reject save with `active_policy_must_be_inactivated`; reuse separate existing lifecycle and settings transactions.
- risk: hidden mistaken for deleted.
  - mitigation: direct details and audit tooling identify hidden state; no delete path exists.
- risk: evidence snapshot contains excess data.
  - mitigation: field allowlist and sensitive-content canary tests.
- risk: local routes leak into server mode.
  - mitigation: route inventory tests assert non-local 404.

## Invariants and Edge Cases

### Invariants

- Mode and strength have one workspace persistence owner.
- UI never writes decision-learning YAML.
- Baseline never applies learned residual.
- Personalized without compatible active policy always falls back safely.
- Active but runtime-incompatible policy is presented as `Active · Not in use` and can be manually inactivated under Personalized Ranking.
- One domain policy is active at most.
- Activation and inactivation append retained audit events.
- `training_run_id` remains internal/content-addressed; public ID remains immutable and one-to-one.
- Every new run captures exact strength, settings revision, fingerprint, watermark, event IDs, and immutable display rows.
- Remove never deletes or rewrites canonical records.
- Hidden run never owns active policy and exposes no activation action.
- Console Clear never changes backend data.
- Completed pipeline results never change after settings/policy changes.
- Disabled UI controls never replace backend validation.

### Edge Cases

- empty or minimal input:
  - insufficient comparisons persist terminal Not Created run with evidence metadata and no snapshot;
  - no runs renders distinct empty state;
  - no active personalized policy renders fallback message.
- normal and large input:
  - evidence and history use existing bounded pagination conventions;
  - snapshot ordering is deterministic.
- duplicate, missing, malformed, or unsupported data:
  - equivalent duplicate submit resolves same public run;
  - event IDs are ordered unique;
  - missing title uses persisted safe `job_label` fallback;
  - malformed bounds, strength, evidence, or identity reject atomically.
- retry, cancellation, timeout, partial failure, or concurrency:
  - browser prevents duplicate submit;
  - uncertain retry is idempotent;
  - no cancellation contract exists for synchronous solver;
  - stale evidence, parent, settings, active snapshot, or provenance changes nothing.
- migration or mixed-version state:
  - old runs may show explicit historical-evidence unavailable state;
  - internal old IDs are not public URL aliases;
  - compatible existing active behavior is preserved.
- generated-source consistency: not applicable; no generated client or JSON resource is introduced.
- security or accessibility boundary:
  - local Host/Origin/CSRF/onboarding remain mandatory;
  - audit actor is server-derived `local_workspace`;
  - forms announce labels, errors, disabled states/reasons, dialogs, and status without color-only meaning;
  - tables remain usable at narrow width and 200% zoom.

## Validation Plan

### Acceptance Criterion: Settings and Runtime Agree

- setup or precondition: fresh, migrated-active, and persisted-setting fixtures.
- action: switch modes, change strength, refresh/restart, and run ranking.
- expected result: settings survive; migration preserves compatible behavior; runtime follows persisted state; incompatible personalized mode falls back.
- failure condition: browser-only truth, YAML mutation, page/runtime disagreement, partial write, or learned residual under baseline.
- proof method: settings, runtime, route/template, and browser tests.
- expected evidence: revisioned rows, captured contract, ranking projection, visible fallback.

### Acceptance Criterion: Strength Change Requires Prior Inactivation

- setup or precondition: personalized mode with active policy.
- action: attempt strength save, inactivate policy, then save strength; repeat with stale settings revision.
- expected result: first save is rejected with clear instruction; inactivation keeps personalized mode and shows fallback; second save succeeds through existing settings transaction; stale save changes nothing.
- failure condition: strength changes while policy active, automatic inactivation occurs, mode switches to baseline, or stale write succeeds.
- proof method: settings/lifecycle route tests and browser Manage/Inactivate flow.
- expected evidence: unchanged first revision, audited manual inactivation, updated second revision, fallback, focus/error proof.

### Acceptance Criterion: Synchronous Submission Produces One Terminal Run

- setup or precondition: candidate, no-op, insufficient, rejected, infeasible, solver-error, stale, and duplicate fixtures.
- action: submit Optimize Current Ratings and retry identical request.
- expected result: accepted attempts persist one public terminal run and captured inputs; only candidate creates snapshot; stale creates no misleading run; duplicate returns same run.
- failure condition: durable Running row, duplicate run, missing failure attempt, untrusted alpha, or invalid snapshot creation.
- proof method: service/store/route tests and browser submit flow.
- expected evidence: identity mapping, status/snapshot matrix, PRG target, submitting state.

### Acceptance Criterion: Historical Evidence Is Stable and Bounded

- setup or precondition: new run, later rating changes/removals, and old run without snapshot.
- action: open details before/after source changes.
- expected result: new run rows stay unchanged and traceable; old run shows unavailable message; excluded source content is absent.
- failure condition: current evidence replaces history, fabricated old rows, lost references, or leaked content.
- proof method: persistence/detail tests and canary assertions.
- expected evidence: immutable equality, reference integrity, absent canaries.

### Acceptance Criterion: Lifecycle Is Audited and Singular

- setup or precondition: candidates across strength contracts, one active policy, and stale CAS fixtures.
- action: activate, inactivate, retry, and conflict.
- expected result: one active domain policy; prior active retired; inactivation targets zero residual and keeps personalized mode; events retained; conflicts change nothing.
- failure condition: two active policies, client actor, unaudited mutation, deletion, or provenance bypass.
- proof method: SQLite lifecycle and route tests.
- expected evidence: constrained states, event reasons, CAS failures, runtime resolution.

### Acceptance Criterion: Remove Hides Only

- setup or precondition: inactive/candidate, active, hidden, and unknown runs.
- action: remove and inspect table, direct detail, DB, events, and diagnostics.
- expected result: eligible row leaves normal list; direct detail remains read-only; active removal blocked; repeated removal idempotent; records remain.
- failure condition: hard delete, orphan, hidden active policy, broken detail, or duplicate destructive event.
- proof method: store/route/template tests.
- expected evidence: visibility metadata, unchanged canonical payloads, retained references, notices.

### Acceptance Criterion: UI Matches Approved Intent

- setup or precondition: baseline, fallback, active, all terminal statuses, hidden, empty, validation, and console fixtures.
- action: navigate main/detail URLs, submit forms, refresh, Back/Forward, clear console, and use keyboard only.
- expected result: four-section main and three-section detail render; controls follow rules; shared patterns remain consistent; Clear is view-only.
- failure condition: hash production route, old technical sections/actions, missing disabled reason, focus loss, current evidence on details, or backend Clear deletion.
- proof method: Jinja tests, Playwright flows/accessibility/screenshots, and targeted DevTools console/network checks.
- expected evidence: desktop/narrow/200%-zoom/light/dark captures, keyboard sequence, clean console/network, stable URLs.

### Acceptance Criterion: Local Security Holds

- setup or precondition: local/non-local modes and valid/invalid Host, Origin, CSRF, onboarding.
- action: request all page/detail/mutation routes.
- expected result: routes unavailable outside local mode; local unsafe requests require guards; actor is server-derived; form alpha is ignored/rejected.
- failure condition: remote exposure, forged request accepted, actor spoofing, or mutation before onboarding.
- proof method: route inventory and middleware tests.
- expected evidence: 404/403/409 matrix and persisted actor/value assertions.

### Acceptance Criterion: Regression Contracts Stay Intact

- setup or precondition: existing optimization page/service/store/runtime/prototype tests plus new focused cases.
- action: run focused and broader affected suites.
- expected result: solver math, internal IDs, snapshots, completed-run capture, and lifecycle safeguards remain; prototype layout assertion includes Optimization Details.
- failure condition: formula/ID drift, lost CAS, or stale prototype assertion.
- proof method: existing suites and updated prototype contract test.
- expected evidence: passing affected suite without new test framework.

## Completion Criteria

Specification is approved for implementation planning when:

1. mode and strength have one revisioned workspace owner and one runtime contract;
2. policy metadata owns `0.01–0.10`, step `0.01`, and recommended/default alpha;
3. synchronous submission, terminal status mapping, idempotency, and failure persistence are explicit;
4. public `preference_optimization_run_id` replaces internal ID in UI only;
5. evidence fingerprint, watermark, event IDs, and minimal rows have immutable ownership;
6. activation, manual inactivation before strength change, one-active-policy, CAS, provenance, and audit behavior are unambiguous;
7. Remove means hide and cannot hide/delete active policy;
8. main/detail URLs, sections, actions, disabled states, fallback wording, statuses, and Console Clear are explicit;
9. local-only security and server-derived actor remain enforced;
10. migration preserves compatible behavior and never fabricates history;
11. outcomes map to persistence, runtime, route, template, browser, accessibility, and security proof;
12. JSON client, async jobs, multi-user auth, hard deletion, full compliance snapshots, and solver redesign remain non-goals;
13. no behavior-changing decision remains hidden as implementation detail;
14. file/task/command sequencing remains for approved implementation plan.
