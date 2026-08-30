---
layer: change
artifact_type: spec
status: proposed
template_id: draft-specification
name: fitcv-new-frontend-production
related_features:
  - personal-fitcv
  - fitcv-local
  - greenfield-frontend
---

# FitCV New Frontend Production Draft Specification

## Goal and Scope

- problem or opportunity: FitCV has canonical backend contracts and frozen UX evidence, but no production frontend implementation. A single cross-cutting contract is needed before frontend implementation begins.
- affected users or systems: one trusted Windows user using FitCV Local, the FastAPI control plane, packaged local runtime, canonical API resources, and legacy `/admin/*` compatibility routes.
- desired outcome: provide one approved, greenfield frontend contract for Personal FitCV journeys without reusing the existing Jinja frontend or prototype JavaScript.
- included scope: `/app` browser entry, same-origin delivery, client/server ownership, route and hash behavior, canonical API consumption, lifecycle and error handling, security, accessibility, responsive behavior, reduced motion, legacy coexistence, and verification intent.
- excluded scope: production source code, frontend package scaffolding, exact component decomposition, task order, build commands, backend contract redesign, legacy deletion, hosted multi-user behavior, and application submission.

## User Flow and Business Rules

### User or System Flow

1. User launches FitCV Local and opens the new `/app` entry.
2. Frontend reads `/healthz`, `/local/readiness`, and supported settings resources through same-origin requests.
3. User creates or resumes a Candidate Profile, reviews source-backed evidence and suggestions, and confirms an active profile through canonical creation-attempt and profile APIs.
4. User selects tracked companies or supported job input, creates or reviews a Scan, and uses truthful Scan output as Run input.
5. User starts a Run, observes server-owned stages and cursor events, reviews fit evidence, records separate interest, and bookmarks useful jobs.
6. User revisits bookmarks, optionally changes ranking preference through `/personalization`, and returns to normal ordering when desired.
7. User selects a suitable job, previews an exact immutable CV version as safe text, regenerates or retries when allowed, reviews evaluation state, and downloads the selected artifact.
8. User returns after restart to server-owned history and uses diagnostics or recovery guidance without terminal-first operation.

### Business Rules

- Only an active, confirmed Candidate Profile is eligible for a normal profile-based Run.
- Source-backed facts, derived suggestions, fit qualification, Application Interest, ranking preference, review state, and generated artifacts remain distinct.
- Server owns lifecycle status, capabilities, revisions, snapshots, evidence, suitability, artifact identity, retryability, and historical truth.
- Client owns only view state, URL/hash state, unsaved edits, selection state, polling control, and session-scoped transient notifications.
- Provider API keys never enter client state, browser storage, logs, diagnostics, exports, or downloaded files.
- New frontend never parses legacy HTML, reads prototype sample data as truth, or imports/wraps/copies legacy templates or prototype JavaScript.
- Legacy `/admin/*` routes remain compatibility surfaces until a separate approved retirement decision passes its gates.
- FitCV remains personal and local; no multi-user or Internet-facing service contract is introduced.

## UI Intent and Known States

- target platform: modern browser served by FitCV Local on a user-owned Windows computer; desktop and narrow responsive viewports are supported.
- intended interaction: preserve approved information architecture and interaction patterns from the frozen prototype while rebuilding implementation from scratch with semantic native controls and project-owned design tokens.
- loading, empty, success, error, disabled, and retry states: every asynchronous resource and mutation exposes truthful loading, empty, success, failure, disabled, pending, conflict, cancelled, unavailable, and retry states where its canonical contract permits them. Polling stops or backs off according to server capability and terminal state.
- accessibility or responsive intent: keyboard operation, visible focus, native validation, labelled controls, live-region feedback, Escape handling, focus containment and return for dialogs, 44px touch targets, responsive navigation, local table overflow, and reduced-motion behavior remain required.
- durable design-system owner: active Agentic semantic tokens and the accepted Design Export guidance; the frozen prototype is UX evidence, not a second design-system SSOT.

## Assumptions and Open Questions

### Verified Facts

- FitCV Local currently serves Jinja templates and redirects local root behavior to legacy routes; source: `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py`, and `src/fitcv_cp/local_app.py`.
- Canonical JSON, multipart, event, artifact, lifecycle, settings, and local-control routes already exist; source: `docs/api.md`, `src/fitcv_cp/app.py`, and `src/fitcv_cp/local_routes.py`.
- G-02 CV preview, G-03 personalization transport, and G-04 local readiness corrections are resolved and directly verified in `docs/fitcv-new-frontend.integration.md` and focused tests.
- Focused specifications for managed scans, candidate evidence, transient notifications, personalization JSON, CV preview transport, and local readiness/profile authority are active.
- The frozen prototype is `docs/fitcv-settings-ui-prototype.html`; it is immutable interaction evidence and must not be reused as production implementation.
- Design Export output is `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`, generated from `fitcv-settings-ui-prototype.html` by task `final-design-export-curation`; metadata status is `complete`.
- Design Export `EX-01` and `EX-12` owner decisions are recorded below; export identity and independent review remain subject to Task 4 confirmation.

### Assumptions

- `/app` can be served from the same FitCV Local origin without changing canonical API paths or weakening host and CSRF protections.
- A production frontend build can be packaged as static resources while legacy templates remain available for compatibility.
- Existing API response shapes and error envelopes remain the source of truth; frontend behavior adapts to those contracts rather than duplicating them.

### Resolved Owner Decisions

- Owner decision: FitCV terracotta/cream is approved as a product brand override, bound through active Agentic semantic tokens without changing information architecture or UX behavior.
- Owner decision: production delivery does not require inspectability IDs such as `data-od-id`; adding them later requires a separate approved runtime need and does not change current UX behavior.

### Open Questions

- Which exact browser support floor and packaged-resource manifest format are required? These may be deferred to implementation planning only if they do not change approved user behavior or security boundaries.

## Prototype and Validation Findings

- prototype reference: `docs/fitcv-settings-ui-prototype.html`.
- UX approval: owner-approved frozen UX reference; implementation remains greenfield.
- design export evidence:
  - selected export method: verified OpenDesign export.
  - export task reference: `final-design-export-curation`.
  - requested deliverable: FitCV design-system guidance.
  - durable output identity: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md` with matching metadata in `design/fitcv-settings-ux-audit/fitcv-design-system-export.md.artifact.json`.
  - independent review: `PASS` recorded for OpenDesign run `ea9169ad-d5e0-4e7e-9480-98de93b62a6e` and durable output `design/fitcv-settings-ux-audit/fitcv-design-system-export.md` at blob `8586f2d64bef1ef2ab11db9768877de020e13b89`.
  - gate state: complete.
- scenario tested: frozen prototype desktop and mobile rendering, light/dark theme behavior, grouped navigation, dialogs, tabs, forms, status feedback, table overflow, and notification panel.
- observed result: prototype provides approved information architecture and interaction evidence; export guidance preserves native controls, responsive navigation, semantic feedback, focus behavior, and token ownership. Owner approved the palette override and resolved inspectability as not required for current delivery.
- accepted behavior: greenfield frontend preserves product journeys, native semantics, server truth, client-only transient notifications, safe CV preview text, and legacy coexistence.
- rejected behavior: importing legacy templates or prototype JavaScript, parsing legacy HTML, persisting provider secrets in client storage, treating interest as suitability, or adding a backend notification service.
- remaining uncertainty: exact packaged static-resource manifest and browser support floor; these do not change approved behavior and remain implementation-plan concerns.
- boundary implication when material: frontend owns presentation and client state; backend and canonical APIs own durable truth; shared contract is limited to documented request/response, capability, identity, revision, error, and media semantics.

## Promotion Readiness

- owner approval: Product owner approved this draft in Codex task on 2026-08-30.
- approval reference: Codex approval message on 2026-08-30.
- remaining blockers: None identified; Task 4 records final identity-bound gate evidence before same-file promotion.
- approved deferrals with owner, rationale, trigger, and approval reference or `None`: `None.`
- unresolved behavior-changing questions: `None.`

This draft intentionally contains no production implementation sequence. After independent review, explicit product-owner approval, and completion of applicable Design Export evidence, replace this content in the same file with the detailed specification template and set `status: active`.
