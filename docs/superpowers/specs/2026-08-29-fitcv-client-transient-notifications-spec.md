---
layer: change
artifact_type: spec
status: proposed
template_id: draft-specification
name: fitcv-client-transient-notifications
targets:
  - docs/fitcv-settings-ui-prototype.html
  - design/fitcv-settings-ux-audit/fitcv-design-system-export.md
related_features:
  - notifications
  - run-continuity
  - candidate-profile-lifecycle
---

# FitCV Client Transient Notifications

## Goal and Scope

- problem or opportunity: the frozen UX includes a notification bell, but no approved need exists for a persisted notification service.
- affected users or systems: new frontend users receiving action and lifecycle feedback.
- desired outcome: users see timely, actionable feedback without creating a second backend event store.
- included scope: client-owned transient events generated from completed API responses, polling transitions, and recoverable request failures.
- excluded scope: backend notification tables, cross-device history, guaranteed delivery, server push, and replacing run/scan event history.

## User Flow and Business Rules

1. Client starts an action or observes a lifecycle transition.
2. Client creates one notification with stable client ID, severity, title, message, timestamp, and optional route/action target.
3. Bell shows unread count only when count is greater than zero; opening panel marks visible items read.

- Notifications live in `sessionStorage` under one versioned client key; navigation and reload preserve them, closing the browser session clears them.
- Deduplication key is `{source_type}:{source_id}:{terminal_state}`; duplicate observations replace metadata without increasing unread count.
- User can dismiss one item or clear all; dismissal affects client state only. Opening panel marks rendered items read, not unseen items.
- Durable truth remains canonical resource, run/scan event stream, or error response.
- Notification copy must not claim success before canonical response or lifecycle state proves it.

## UI Intent and Known States

- target platform: new frontend desktop and responsive web.
- intended interaction: bell, unread badge, panel, per-item dismiss, clear-all, and link to source detail.
- loading, empty, success, error, disabled, and retry states: hidden badge at zero; empty panel explains no recent activity; success/warning/error items expose source and next action; panel remains usable while source requests load.
- accessibility or responsive intent: native button semantics, accessible name, live announcement for newly created urgent items, and touch targets of at least 44px.
- durable design-system owner: Agentic Design System SSOT; verified FitCV Design Export is guidance evidence.

## Assumptions and Open Questions

### Verified Facts

- frozen prototype includes global notifications and client-side handlers: `docs/fitcv-settings-ui-prototype.html`.
- canonical backend exposes run and scan events, but no global notification API: `docs/api.md` and route inventory.

### Assumptions

- session-only client state is sufficient because durable history is available in source resources.

### Open Questions

- none that change this minimum contract.

## Prototype and Validation Findings

- prototype reference: `docs/fitcv-settings-ui-prototype.html` notification bell and panel.
- UX approval: owner-approved frozen UX.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`; gate state: complete.
- scenario required for validation: action success, action failure, lifecycle success/failure, duplicate polling observation, dismiss one, clear all, zero unread.
- observed result: prototype supports a global panel but backend persistence is not required.
- accepted behavior: transient client feedback links to durable source truth.
- rejected behavior: zero badge displayed as an attention signal; durable backend notification infrastructure.
- remaining uncertainty: none for minimum semantics.
- boundary implication when material: frontend/client state only; no backend contract.

## Promotion Readiness

- owner approval or `Not approved: <reason>`: proposed pending independent specification review.
- approval reference: accepted reconciliation finding G-01.
- remaining blockers or `None identified`: independent review.
- approved deferrals with owner, rationale, trigger, and approval reference or `None`: persistent notifications deferred; product owner, add only if cross-session or guaranteed delivery becomes a success outcome.
- unresolved behavior-changing questions or `None`: None.
