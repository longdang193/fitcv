---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
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

## Goal and Problem

### Problem

- current behavior or opportunity: the frozen UX includes a notification bell, but no approved need exists for a persisted notification service.
- affected users, systems, or maintainers: new frontend users receiving action and lifecycle feedback.
- evidence: the frozen prototype provides a global notification panel; canonical APIs expose source resource and run/scan lifecycle truth, not a global notification store.
- consequence of no change: users lack timely feedback, or a second backend event store is introduced without an approved product need.

### Goal

- desired outcome: users see timely, actionable feedback without creating a second backend event store.
- observable success: client notifications reflect proven source events, deduplicate repeated observations, and never show an unread badge of zero.

## Required Outcomes

### Outcome: Actionable session feedback

- affected actor or system: new frontend user and client notification state.
- required result: completed actions, lifecycle transitions, and recoverable failures produce concise notifications linked to their source.
- success condition: notification copy and target match canonical response or lifecycle state.

### Outcome: Client-only ownership

- affected actor or system: frontend session state and backend resource APIs.
- required result: session-only notification state supports read, dismiss-one, and clear-all without persistent backend notification infrastructure.
- success condition: closing the browser session clears notification state while source records remain authoritative.

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| Is a global notification surface approved? | Frozen prototype includes bell and panel. | `docs/fitcv-settings-ui-prototype.html` | high | Preserve bell, panel, unread, dismiss, and clear-all behavior. |
| Is a notification backend required? | Source APIs already own durable run, scan, and resource truth. | `docs/api.md` and route inventory | high | Keep notification state client-owned and transient. |
| What must notification copy represent? | Source state and completed responses prove outcomes. | API contracts and lifecycle responses | high | Do not claim success before proof. |

### Prototype and Validation Evidence

- prototype reference: `docs/fitcv-settings-ui-prototype.html` notification bell and panel.
- UX approval: owner-approved frozen UX.
- frozen prototype revision or reference: approved FitCV settings UX prototype.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`.
  - selected export method: verified OpenDesign export.
  - export task reference: recorded Design Export completion evidence.
  - requested deliverable: FitCV design-system guidance.
  - durable output identity: `fitcv-design-system-export.md`.
  - independent review: `PASS` for the verified export.
- validated scenarios and states: action success, action failure, lifecycle success/failure, duplicate polling observation, dismiss-one, clear-all, zero unread, and empty panel.
- findings incorporated into approved behavior: hidden zero badge, session-only state, deterministic deduplication, and source-linked actions.
- rejected alternatives: persistent notification tables, cross-device history, server push, and a zero-valued attention badge.

### Scope

- included behavior: client notification creation, deduplication, session storage, unread state, visible-item read marking, dismiss-one, clear-all, source links, and accessible responsive presentation.
- affected boundaries: new frontend client state and canonical source-resource APIs.
- admissible cases: completed responses, observed lifecycle transitions, and recoverable request failures.
- compatibility expectation: source resource, run, scan, and error contracts remain unchanged.

### Non-Goals

- backend notification tables or API.
- cross-device or cross-session history.
- guaranteed delivery, server push, or replacement of source event history.

### Requirements and Behavioral Contract

#### Requirement: Create source-backed notification

- trigger or actor: client action completion, lifecycle transition, or recoverable request failure.
- preconditions: canonical response or observed lifecycle state identifies source type, source ID, and outcome.
- required behavior: create one notification containing stable client ID, severity, title, message, timestamp, and optional route/action target.
- output or state change: notification enters client session state and unread count increases once.
- failure behavior: if source identity or outcome is unavailable, do not create a success notification; retain request error handling at source boundary.
- observable acceptance: each valid source outcome creates one source-linked notification with truthful copy.

#### Requirement: Deduplicate and retain transient state

- trigger or actor: repeated polling observation or repeated response handling.
- preconditions: notification key is `{source_type}:{source_id}:{terminal_state}`.
- required behavior: replace duplicate metadata without increasing unread count; store state under one versioned `sessionStorage` key.
- output or state change: navigation and reload in same browser session retain state; closing session clears it.
- failure behavior: malformed stored state is discarded and replaced with empty notification state.
- observable acceptance: repeated identical observations do not create duplicate unread items.

#### Requirement: Manage notification visibility

- trigger or actor: user opens panel, dismisses one item, or clears all.
- preconditions: panel is available.
- required behavior: opening marks rendered items read; dismiss-one removes only selected item; clear-all removes every item.
- output or state change: unread count reflects remaining unread items and is hidden when zero.
- failure behavior: notification controls remain keyboard-accessible and do not block source navigation.
- observable acceptance: each control changes only its defined client state.

| Boundary | Owner or canonical contract | Required evidence |
| --- | --- | --- |
| Client notification state | New frontend session state | UI state and browser interaction proof |
| Durable outcome truth | Source resource, run, scan, or error contract | Direct source response or lifecycle evidence |

### Constraints and Alternatives

- constraint: durable outcome truth has one owner; notification state must not become a competing event store.
- alternative: persistent backend notifications
  - benefit: cross-session history.
  - trade-off: new storage, delivery, retention, and synchronization ownership.
  - reason accepted or rejected: rejected until product success outcomes require cross-session or guaranteed delivery.

## Design Decisions

### Decision: Use client-owned session notifications

- context: frozen UX needs immediate feedback, but durable backend notification infrastructure is not approved.
- selected approach: versioned `sessionStorage` state with deterministic deduplication and source links.
- rationale: smallest contract that satisfies current journey while preserving durable source ownership.
- alternatives considered: persistent backend event store, server push, and local-only ephemeral memory.
- accepted trade-offs: feedback ends with browser session; source history remains available through canonical surfaces.
- affected owners and boundaries: new frontend owns transient state; backend source APIs remain unchanged.

### Compatibility, Migration, and Risk

- old behavior: prototype panel has no durable notification contract.
- new behavior: client creates, reads, dismisses, and clears transient source-backed notifications.
- compatibility boundary: no backend schema or endpoint change.
- migration or backfill: none; versioned client key can be discarded on schema change.
- rollout and rollback: client can disable notification creation without changing source resources.
- deprecation or consumer impact: none for existing backend consumers.
- risk:
  - mitigation: deterministic deduplication, truthful copy, malformed-state reset, and source links.

## Invariants and Edge Cases

### Invariants

- durable source state remains canonical.
- success copy requires proven success state.
- duplicate source observations do not increase unread count.
- zero unread count has no visible badge.
- dismiss and clear operations change client state only.

### Edge Cases

- empty or minimal input: no source identity means no success notification; empty panel explains no recent activity.
- normal and large input: keep panel rendering responsive without changing source truth.
- duplicate, missing, malformed, or unsupported data: deduplicate by source key; discard malformed storage; do not invent unsupported outcomes.
- retry, cancellation, timeout, partial failure, or concurrency: classify recoverable request failures as actionable errors; do not report completion for canceled or timed-out work.
- migration or mixed-version state: unknown storage versions reset to empty state.
- generated-source consistency: no generated backend surface is changed.
- security or accessibility boundary: use native button semantics, accessible names, live announcement only for urgent new items, and touch targets of at least 44px.

## Validation Plan

### Backend Verification Claims

- direct boundary: `Not applicable: this specification adds no backend notification boundary.`
- important success and failure behavior: source API and lifecycle responses remain canonical and are consumed without reinterpretation.
- final state or side effects: `Not applicable: notification state is client-owned.`
- rollback, retry, duplicate, or idempotency behavior: duplicate client observations are idempotent by source key.
- canonical contract and conformance proof: `Not applicable: no new backend contract.`
- real dependencies requiring proof: `Not applicable: browser session storage is the only new dependency.`
- representative-operation trace mechanism: browser interaction proof for source success, failure, and lifecycle transitions.
- performance claim and threshold: notification creation and panel updates must not block source navigation or render.

### Acceptance Criterion: Source outcomes produce truthful notifications

- setup or precondition: client receives completed success, failure, or lifecycle terminal state.
- action: observe or complete source event.
- expected result: one notification appears with source link and matching outcome.
- failure condition: success notification appears before proof or claims an outcome not present in source state.
- proof method: browser flow plus source response inspection.
- expected evidence: notification item, source ID, and matching canonical state.

### Acceptance Criterion: Session controls manage state symmetrically

- setup or precondition: session contains unread and read notifications.
- action: open panel, dismiss one, clear all, reload, and end session.
- expected result: visible items become read; one item or all items are removed as selected; same-session reload retains state; session end clears it; zero badge is hidden.
- failure condition: unrelated items change, zero badge remains visible, or durable source data changes.
- proof method: browser interaction and storage inspection.
- expected evidence: final item list and unread count match each action.

## Completion Criteria

Specification is complete when:

1. client-only ownership and durable source ownership are explicit
2. notification identity, state, deduplication, and controls are unambiguous
3. accessibility, responsive, error, retry, and malformed-state behavior are defined
4. persistent notification infrastructure is explicitly deferred with owner and trigger
5. each required outcome maps to acceptance and validation intent
6. Design Export and frozen UX evidence are preserved
7. implementation sequencing remains outside this specification
