---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-new-frontend-production
related_features:
  - personal-fitcv
  - fitcv-local
  - greenfield-frontend
---

# FitCV New Frontend Production Specification

## Goal and Problem

### Problem

- current behavior or opportunity: FitCV has canonical backend contracts and frozen UX evidence, but no production frontend implementation. Existing Jinja pages and prototype JavaScript cannot provide the new frontend implementation authority.
- affected users, systems, and maintainers: one trusted Windows user, FitCV Local, the FastAPI control plane, packaged local resources, canonical APIs, and legacy `/admin/*` compatibility surfaces.
- evidence: `docs/fitcv-new-frontend.integration.md`, active focused specifications, `docs/api.md`, `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`, and the frozen prototype.
- consequence of no change: frontend work can duplicate backend truth, reuse legacy implementation accidentally, expose secrets, or leave Personal FitCV journeys without one durable contract.

### Goal

- desired outcome: deliver one canonical contract for rebuilding FitCV frontend from scratch at `/app`, while preserving canonical backend truth and legacy compatibility until explicit retirement approval.
- observable success: a new frontend can consume supported APIs, represent all completion-critical Personal FitCV journeys truthfully, meet security/accessibility/responsive boundaries, and coexist with legacy `/admin/*` without importing or parsing legacy implementation.

## Required Outcomes

### Outcome: Greenfield frontend authority

- affected actor or system: frontend source, browser delivery, and legacy compatibility surfaces.
- required result: new frontend implementation is independent of `src/fitcv_cp/templates/`, legacy Jinja routes, `docs/fitcv-settings-ui-prototype.html` JavaScript, and prototype sample data.
- success condition: `/app` is the only new frontend entry; no frontend import, wrapper, parser, or state path depends on legacy HTML/templates or prototype JavaScript.

### Outcome: Complete Personal FitCV journey

- affected actor or system: FitCV Local user and canonical backend resources.
- required result: completion-critical core journeys include setup/readiness, Candidate Profile, Scans, Runs, Run recovery, fit evaluation, bookmarks/interest, personalization, grounded CV review, and durable decision/history. Supporting surfaces include diagnostics, session-scoped notification convenience, and synonym management.
- success condition: every completion-critical core journey has truthful loading, empty, success, failure, disabled, pending, conflict, cancelled, unavailable, and retry behavior where its canonical contract permits. Supporting surfaces may not block core completion, but must not falsify core truth or suppress actionable recovery.

### Outcome: Truthful cross-boundary ownership

- affected actor or system: browser client, FastAPI APIs, local persistence, and generated artifacts.
- required result: server owns durable business truth; client owns presentation and session state only.
- success condition: client never infers suitability, acceptance, readiness, revision, artifact identity, or retryability from local guesses or stale legacy fields.

### Outcome: Safe local delivery

- affected actor or system: browser, FitCV Local host, Windows package, and user data.
- required result: same-origin `/app` delivery works in development and packaged FitCV Local while existing API, host, CSRF, and local data boundaries remain intact.
- success condition: static resources resolve through supported local launch and deep-link refresh, without requiring terminal-first operation or exposing provider secrets.

## Design Analysis

### Change Summary

- baseline reference: no production `frontend/` package, browser client, frontend test surface, or packaged frontend output exists; legacy Jinja implementation remains compatibility-only.
- added, changed, or removed behavior summary: add a greenfield `/app` frontend contract; preserve existing canonical API behavior; add no backend notification service and no legacy deletion.
- intentionally unchanged behavior: backend lifecycle/status semantics, API resource identities, CAS/revision rules, artifact bytes, profile authority, fit meaning, and legacy `/admin/*` availability remain unchanged.
- affected maintained contracts: `docs/api.md`, active focused specifications, FitCV Local routes, static resource packaging, and frontend/browser verification evidence.

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| What owns product scope? | Personal FitCV journey and one trusted Windows user are current target. | `docs/intent/project-charter.md`, `docs/intent/success-outcomes.md`, `docs/intent/constraints-and-non-goals.md` | high | Do not introduce multi-user SaaS or Internet-facing requirements. |
| What owns UX structure? | Frozen prototype contains approved information architecture, navigation, dialogs, tabs, forms, responsive behavior, and feedback patterns. | `docs/fitcv-settings-ui-prototype.html` | high | Preserve interaction intent, not implementation. |
| What owns visual tokens? | Active Agentic semantic tokens and accepted export guidance own production token values. | `design/fitcv-settings-ux-audit/fitcv-design-system-export.md` | high | Do not create duplicate token SSOT. |
| What owns API truth? | JSON, multipart, event, artifact, lifecycle, settings, and local-control contracts exist. | `docs/api.md`, `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py` | high | Frontend consumes canonical contracts and errors. |
| Which focused contracts are ready? | Managed Scan, candidate evidence, transient notifications, personalization JSON, CV preview transport, and local readiness/profile authority specs are active. | `docs/superpowers/specs/` | high | Parent spec references focused owners without copying their full contracts. |
| Which reconciliation defects are resolved? | G-02, G-03, and G-04 backend corrections have direct focused tests; G-01 remains client-owned. | `docs/fitcv-new-frontend.integration.md`, focused tests | high | Frontend proof extends backend proof; it does not replace it. |
| What is the compatibility boundary? | Local app currently serves Jinja templates and redirects legacy local root behavior. | `src/fitcv_cp/local_app.py`, `src/fitcv_cp/local_routes.py`, `src/fitcv_cp/app.py` | high | New `/app` delivery coexists with legacy `/admin/*` until retirement gates pass. |

### Prototype and Validation Evidence

- prototype reference: `docs/fitcv-settings-ui-prototype.html`.
- UX approval: owner-approved frozen UX reference; implementation is greenfield and prototype source remains immutable.
- frozen prototype revision or reference: `docs/fitcv-settings-ui-prototype.html` at blob `5950dcd2b6a6c4f68b1d522fcea1c0a29d9aff27`.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`.
  - selected export method: verified OpenDesign export.
  - export task reference: OpenDesign run `ea9169ad-d5e0-4e7e-9480-98de93b62a6e`, task `final-design-export-curation`.
  - requested deliverable: FitCV design-system guidance.
  - durable output identity: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md` at blob `8586f2d64bef1ef2ab11db9768877de020e13b89`; matching metadata is in `design/fitcv-settings-ux-audit/fitcv-design-system-export.md.artifact.json`.
  - independent review: `PASS` bound to the same OpenDesign run and durable output identity.
- validated scenarios and states: desktop and mobile prototype rendering, light/dark theme behavior, grouped navigation, dialogs, tabs, forms, status feedback, table overflow, notification panel, and reduced-motion intent.
- findings incorporated into approved behavior: terracotta/cream is an approved FitCV brand override bound through semantic tokens; inspectability IDs are not required for current delivery; native controls, focus behavior, live feedback, responsive navigation, and local table overflow remain required.
- rejected alternatives: reuse of legacy templates or prototype JavaScript, HTML parsing, a second token/component SSOT, persistent notification storage, provider API-key persistence, interest-based suitability inference, and legacy deletion during frontend rollout.

### Scope

- included behavior: `/app` entry and deep links; same-origin static delivery; completion-critical Personal FitCV core journeys and required recovery/history; supporting diagnostics, session-scoped notification convenience, and synonym management; canonical API resource consumption; server capability/error/revision/media handling; client view/URL/unsaved-edit/selection/polling/transient state; responsive and accessible interaction; FitCV Local packaging boundary; legacy coexistence.
- affected boundaries: browser frontend, FastAPI local host, static-resource packaging, canonical API contracts, local persistence authority, and verification surfaces.
- admissible cases: one trusted local user, supported browser and Windows package, supported providers and job sources, valid and invalid API responses, lifecycle transitions, retryable failures, stale revisions, missing/corrupt artifacts, and restart/recovery.
- compatibility expectation: existing API paths, response/error semantics, backend data, legacy `/admin/*` routes, and Jinja compatibility surfaces remain available unless a separate approved retirement change says otherwise.

### Non-Goals

- multi-user accounts, shared-user isolation, Internet-facing hosting, high availability, or public SaaS behavior.
- job application submission, employer communication, or downstream hiring-process management.
- backend notification tables, server push, or cross-session notification history.
- changing fit qualification, ranking semantics, Candidate Profile authority, lifecycle status, artifact identity, or canonical API behavior for frontend convenience.
- deleting, repurposing, wrapping, or incrementally migrating legacy templates during this frontend build.

### Requirements and Behavioral Contract

#### Requirement: New frontend entry and delivery

- trigger or actor: user launches FitCV Local or navigates to a supported `/app` route.
- preconditions: local host is running and static frontend resources are available.
- required behavior: serve the new frontend from same origin under `/app`; preserve deep-link refresh and supported browser navigation; keep legacy `/admin/*` routes available.
- output or state change: browser receives frontend assets and uses canonical same-origin API paths; route/hash state identifies current view without making server truth client-owned.
- failure behavior: missing asset or unavailable API shows actionable local error and retry guidance; no redirect silently changes a new-app route into a legacy HTML view.
- observable acceptance: fresh launch, deep link, refresh, Back/Forward, and packaged launch reach the intended new-app route or truthful recovery state.

#### Requirement: Canonical API and state ownership

- trigger or actor: frontend reads or mutates supported resources.
- preconditions: request uses documented route, method, body, headers, capability, identity, and revision semantics.
- required behavior: server response, error envelope, capability, revision, event, snapshot, artifact identity, and retryability remain authoritative.
- output or state change: client stores only presentation state, URL/hash state, unsaved edits, selection, polling control, and session-scoped transient notifications.
- failure behavior: validation, unauthorized/forbidden, CSRF, conflict, unavailable, timeout, cancellation, and malformed responses produce truthful state-specific feedback and preserve unsaved user input where safe.
- observable acceptance: no client path infers readiness, suitability, fit, review acceptance, effective personalization, lifecycle completion, or artifact identity from stale local state.

#### Requirement: Candidate Profile lifecycle

- trigger or actor: user uploads or supplies a supported profile source.
- preconditions: source is accepted by Candidate Profile creation-attempt contract.
- required behavior: show processing, source evidence, baseline/derived information, corrections, save/resume, confirmation, revision conflict, archive/restore, delete, and profile selection states from canonical resources.
- output or state change: only confirmed active profile becomes eligible for normal profile-based Run.
- failure behavior: processing, validation, conflict, unsupported input, or dependency failures remain actionable and never turn suggestions into accepted facts.
- observable acceptance: user can create, review, correct, resume, confirm, revise, archive, restore, and select a profile with source-backed facts distinct from suggestions.

#### Requirement: Scans and Runs

- trigger or actor: user selects supported companies or job input and starts Scan or Run.
- preconditions: canonical capabilities and input readiness permit operation.
- required behavior: display server-owned statuses, stages, jobs, events, immutable outputs, cancellation, retry, archive/unarchive, delete previews, debug bundles, and recovery guidance.
- output or state change: Scan output and Run snapshots retain server identity and can be revisited or reused according to documented contracts.
- failure behavior: queue, timeout, partial, cancelled, or dependency failure states remain truthful; retry uses documented idempotency and does not duplicate mutation.
- observable acceptance: representative Scan and Run journeys show loading, empty, success, failure, polling, terminal, cancellation, retry, event history, and recovery states.

#### Requirement: Evaluation, personalization, and history

- trigger or actor: user reviews Run jobs, bookmarks jobs, records interest, revisits history, or changes ranking preference.
- preconditions: selected resource and documented revision/capability state exist.
- required behavior: keep fit evidence, suitability, Application Interest, bookmarks, ranking preference, and history separate; use `/personalization` JSON resource and ETag/CAS semantics.
- output or state change: user sees server-owned fit and interest truth, bookmark identity, effective ranking/fallback, revision, and historical snapshots.
- failure behavior: stale revision, invalid input, unavailable policy, or missing resource preserves canonical settings and gives retry/conflict guidance.
- observable acceptance: a high-interest weak-fit job remains unsuitable; personalized ranking never claims unsupported evidence; user can return to normal ordering.

#### Requirement: Grounded CV review and safe rendering

- trigger or actor: user selects a suitable job and immutable CV version.
- preconditions: version identity and capability identify a previewable or downloadable artifact.
- required behavior: preview exact persisted `text/markdown` or `text/plain` bytes inline after integrity checks; download remains attachment-only; regeneration and review/evaluation state remain separate.
- output or state change: selected version identity and review state remain unchanged by preview.
- failure behavior: pending/running preview is retryable; failed, corrupt, unsupported, or missing media uses canonical error semantics; renderer treats plain text as text and rejects unsafe HTML/script and URL schemes.
- observable acceptance: preview then download returns selected version bytes, safe headers, unchanged review/evaluation state, and truthful retry or unavailable guidance.

#### Requirement: Security, accessibility, and responsive behavior

- trigger or actor: any user interaction or browser viewport.
- preconditions: frontend renders supported route and state.
- required behavior: preserve same-origin and CSRF protections; never expose secrets; use semantic native controls, visible focus, labels, `aria-*` state, keyboard navigation, Escape behavior, focus containment/return, live regions, responsive navigation, local table overflow, and reduced-motion handling.
- output or state change: user can discover, operate, and recover important journeys across desktop, narrow, light, and dark contexts.
- failure behavior: validation and focus move to actionable errors; unavailable states remain readable and do not rely on color alone.
- observable acceptance: keyboard-only, focus, contrast, touch-target, responsive, reduced-motion, console, and network evidence passes for representative journeys.

#### Requirement: Legacy coexistence and retirement

- trigger or actor: user or maintainer accesses legacy route during frontend rollout.
- preconditions: legacy compatibility route remains supported.
- required behavior: preserve legacy `/admin/*` behavior and templates as compatibility surfaces; new frontend does not import, wrap, parse, or depend on them.
- output or state change: legacy and `/app` routes can coexist with explicit route ownership.
- failure behavior: no new-app failure silently falls back to legacy HTML or changes server truth.
- observable acceptance: retirement occurs only through separate owner-approved gates after new-app browser proof, backend proof, package proof, consumer inventory, and rollback path exist.

### Constraints and Alternatives

- constraint: active Agentic semantic tokens remain visual SSOT; alternative brand palette values must not create a second token system.
  - alternative: copy prototype root tokens into frontend.
  - benefit: fast visual similarity.
  - trade-off: duplicate SSOT and drift.
  - reason accepted or rejected: rejected; bind approved terracotta/cream roles through existing semantic tokens.
- constraint: local product remains one-user and user-controlled.
  - alternative: add account/session service.
  - benefit: broader deployment model.
  - trade-off: outside current product target and adds security surface.
  - reason accepted or rejected: rejected as non-goal.
- constraint: backend truth must remain canonical.
  - alternative: infer lifecycle and suitability from client state.
  - benefit: fewer requests.
  - trade-off: misleading results and lost revision safety.
  - reason accepted or rejected: rejected; consume documented responses, capabilities, events, and revisions.

## Design Decisions

### Decision: Greenfield implementation boundary

- context: existing Jinja templates and frozen prototype JavaScript exist but are not production authority for the rebuilt frontend.
- selected approach: create independent frontend implementation under `/app`; use prototype only as immutable UX evidence and Design Export only as curated guidance.
- rationale: prevents legacy coupling and preserves a single current implementation boundary.
- alternatives considered: incrementally convert Jinja pages; wrap prototype JavaScript; parse legacy HTML.
- accepted trade-offs: duplicate some presentation logic during coexistence; retirement waits for separate proof.
- affected owners and boundaries: frontend source owns presentation; backend routes and legacy templates retain their current owners.

### Decision: Local delivery and compatibility

- context: FitCV Local currently serves Jinja resources and redirects legacy local root behavior.
- selected approach: same-origin `/app` static delivery with deep-link support, while `/admin/*` remains available until retirement approval.
- rationale: preserves local security and compatibility while enabling independent frontend rollout.
- alternatives considered: replace all legacy routes immediately; host frontend on another origin.
- accepted trade-offs: temporary dual route surface and additional package/resource verification.
- affected owners and boundaries: FitCV Local host and Windows packaging own resource delivery; frontend owns route presentation.

### Decision: Visual token and inspectability ownership

- context: Design Export identified palette conflict and absent inspectability metadata.
- selected approach: approve terracotta/cream as FitCV brand override through active Agentic semantic tokens; do not require `data-od-id` for current delivery.
- rationale: preserves approved FitCV visual intent without duplicate token SSOT and avoids unneeded runtime metadata.
- alternatives considered: adopt Agentic navy/blue unchanged; add inspectability IDs proactively.
- accepted trade-offs: future inspectability need requires separate approved runtime change.
- affected owners and boundaries: design-system token owner controls values; frontend consumes tokens; frozen prototype remains unchanged.

### Decision: Client/server state split

- context: journeys combine durable API state with route, form, selection, polling, and notification behavior.
- selected approach: server owns durable truth and identity; client owns presentation, URL/hash, unsaved edits, selection, polling control, and session-only notifications.
- rationale: prevents stale or invented business truth and keeps notification scope bounded.
- alternatives considered: persist notification service; duplicate business state in browser storage.
- accepted trade-offs: client re-reads server state after restart and conflict.
- affected owners and boundaries: API/source/tests own durable contracts; frontend state layer owns ephemeral projection.

### Decision: Native accessible interaction

- context: frozen UX uses native controls, dialogs, disclosures, tabs, validation, and responsive navigation.
- selected approach: preserve semantic native controls and shared accessibility behavior without requiring custom widget replacements.
- rationale: keeps keyboard, focus, validation, and reduced-motion behavior inspectable and consistent.
- alternatives considered: custom controls with visual-only state; route-specific focus implementations.
- accepted trade-offs: browser-native styling requires tokenized adaptation and focused browser verification.
- affected owners and boundaries: frontend owns interaction implementation; browser semantics and accessibility evidence are acceptance boundaries.

### Compatibility, Migration, and Risk

- old behavior: local FitCV serves legacy Jinja pages and `/admin/*` routes; backend contracts and persisted data are canonical.
- new behavior: `/app` provides greenfield frontend journeys through same-origin canonical API access.
- compatibility boundary: preserve legacy routes, templates, API paths, response shapes, persisted state, and user data while new frontend is introduced.
- migration or backfill: none; no historical data rewrite, API migration, or legacy template deletion belongs here.
- rollout and rollback: new frontend route can be disabled or redirected only through explicit approved policy; legacy compatibility remains rollback surface until retirement gates pass.
- deprecation or consumer impact: no existing legacy consumer is forced to migrate by this specification; retirement requires separate plan and owner approval.
- risk:
  - mitigation: direct API/backend proof, same-origin/CSRF checks, browser state and accessibility proof, package launch proof, no-legacy-import checks, and explicit retirement gates.

## Invariants and Edge Cases

### Invariants

- only active confirmed Candidate Profiles satisfy normal profile-based Run eligibility.
- server-owned lifecycle, suitability, fit, revision, capability, artifact, review, and history truth never comes from client guesses.
- fit qualification remains separate from Application Interest, bookmarks, and ranking preference.
- preview never mutates CV version identity, download bytes, review state, evaluation state, or generation state.
- provider API keys never enter client state, logs, diagnostics, exports, or browser persistence.
- notifications remain client-owned and transient; source events/resources remain durable truth.
- `/app` never imports, parses, wraps, or copies legacy templates or prototype JavaScript.
- legacy routes remain available until separate retirement evidence and approval pass.

### Edge Cases

- empty or minimal input: fresh install, no profile, no scans, no runs, no bookmarks, or no CV versions show actionable empty states without false readiness or success.
- normal and large input: pagination, local table overflow, server capabilities, and bounded rendering preserve identity and responsive behavior.
- duplicate, missing, malformed, or unsupported data: API validation, missing resources, malformed legacy onboarding, corrupt media, unsafe content, and unknown fields use canonical rejection or fallback semantics.
- retry, cancellation, timeout, partial failure, or concurrency: polling follows server state; retry uses documented idempotency; stale ETag/CAS conflicts do not overwrite newer data; cancellation remains truthful.
- migration or mixed-version state: legacy `/admin/*` can coexist; old onboarding flags do not claim readiness; no backfill or deletion occurs under this contract.
- generated-source consistency: API docs, route response shapes, static-resource packaging, and maintained specs remain aligned with their canonical owners.
- security or accessibility boundary: same-origin and CSRF protections stay active; secrets stay server-side; semantic names, focus, contrast, keyboard, touch targets, reduced motion, and non-color status cues remain required.

## Validation Plan

### Backend Verification Claims

- direct boundary: canonical routes in `src/fitcv_cp/app.py` and `src/fitcv_cp/local_routes.py` remain callable with documented request, response, error, capability, revision, and media semantics.
- important success and failure behavior: retain direct proof for Candidate Profile authority, Scan atomicity/idempotency/output integrity, Run lifecycle/recovery, bookmark/interest separation, personalization CAS/fallback, CV checksum/media errors, local readiness, CSRF, and host guards.
- final state or side effects: profile confirmation, settings updates, bookmarks, interest, artifacts, and lifecycle transitions remain persisted only through canonical owners; frontend reads do not mutate durable state.
- rollback, retry, duplicate, or idempotency behavior: stale revision rejection, retryable failures, cancellation, repeated polling, repeated mutation submission, and preview/download separation preserve state.
- canonical contract and conformance proof: `docs/api.md`, route decorators, response models, focused specs, and focused backend tests agree.
- real dependencies requiring proof: local SQLite persistence, onboarding state, candidate catalog, settings/optimization service, artifact storage, and FitCV Local host.
- representative-operation trace mechanism: direct API traces for readiness → confirmed profile → Run eligibility; Scan → output → Run; Run → job → bookmark/interest; CV version → preview → download.
- performance claim and threshold: frontend and local API operations stay within existing local request budgets; no new performance target is introduced without measured need.

### Acceptance Criterion: Greenfield journey works

- setup or precondition: fresh FitCV Local launch with supported local data and provider/configuration state.
- action: complete representative Personal FitCV journey through `/app`.
- expected result: user reaches truthful job recommendation and grounded CV review/download without terminal-first operation.
- failure condition: route falls back to legacy HTML, client fabricates server truth, or important failure has no recovery guidance.
- proof method: frontend state tests, browser journey tests, accessibility checks, network/console inspection, and direct backend regression suites.
- expected evidence: route, state, keyboard/focus, responsive, network, console, and backend outputs for representative journeys.

### Acceptance Criterion: Boundary safety holds

- setup or precondition: exercise invalid input, stale revision, CSRF failure, unavailable dependency, unsafe preview content, missing/corrupt artifact, cancellation, and retry.
- action: submit or observe each case through the new frontend.
- expected result: canonical error/fallback state appears, durable state remains correct, secrets remain absent, and safe retry is offered only when permitted.
- failure condition: partial write, duplicate mutation, unsafe rendering, misleading success, secret exposure, or lost user edits.
- proof method: direct backend boundary tests plus frontend/browser/network evidence.
- expected evidence: response/error envelopes, final persisted state, headers, rendered state, and absence of secret/legacy parsing paths.

### Acceptance Criterion: Accessibility and compatibility remain usable

- setup or precondition: desktop and narrow viewports, light/dark themes, keyboard-only operation, reduced-motion preference, and legacy route coexistence.
- action: navigate, open dialogs/tabs/disclosures, submit forms, recover errors, refresh deep links, and return through browser history.
- expected result: visible focus, semantic names/state, focus containment/return, Escape behavior, readable status, touch-size controls, responsive navigation, and stable route behavior.
- failure condition: keyboard trap, invisible focus, color-only state, clipped content, zero-state confusion, or silent legacy fallback.
- proof method: browser accessibility and responsive checks, screenshot/console/network evidence, and route-state tests.
- expected evidence: passing snapshots/checks at representative desktop and mobile widths with no uncaught console errors.

## Completion Criteria

Specification is complete when:

1. greenfield frontend authority and no-legacy-reuse boundary are explicit.
2. Personal FitCV outcomes and all completion-critical journeys are covered.
3. server/client truth ownership, API boundaries, error, revision, idempotency, preview, download, and retry semantics are explicit.
4. local `/app` delivery, deep links, same-origin security, packaging, and legacy coexistence boundaries are explicit.
5. security, accessibility, responsive, keyboard/focus, reduced-motion, and safe-rendering requirements are explicit.
6. Design Export identity, independent PASS, and owner decisions for `EX-01` and `EX-12` are preserved.
7. focused specifications remain single owners of their feature contracts.
8. validation intent covers direct backend proof plus frontend/browser proof without replacing backend evidence.
9. implementation sequencing, exact files, task order, commands, and execution topology remain in the implementation plan.
10. all behavior-changing decisions are resolved in this active specification.
