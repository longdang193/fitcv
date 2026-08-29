---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-core-personalization-json
targets:
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_store.py
  - src/fitcv_cp/optimization_service.py
  - src/fitcv_cp/store.py
  - docs/api.md
related_features:
  - personal-fitcv
  - preference-optimization
---

# FitCV Core Personalization JSON Contract

## Goal and Problem

### Problem

- current behavior or opportunity: completion-critical personalization is implemented behind `/admin/optimization` HTML routes, which a new frontend cannot consume as a stable JSON contract.
- affected users, systems, or maintainers: users optionally prioritizing future jobs, ranking settings, and existing preference-learning services.
- evidence: canonical settings and optimization service already own ranking mode, strength, active policy, and fallback semantics; legacy routes expose an HTML administration model.
- consequence of no change: new frontend either couples to legacy HTML or cannot truthfully show personalization state.

### Goal

- desired outcome: new frontend can read and update core personalized ranking without inheriting legacy admin HTML.
- observable success: minimal JSON resource reports requested and effective state, validates updates atomically, and never changes fit qualification truth.

## Required Outcomes

### Outcome: Core personalization resource

- affected actor or system: new frontend Personal FitCV journey and canonical settings/optimization services.
- required result: `GET /personalization` exposes requested mode, effective mode, strength, fallback, policy identity, bounds, and revision.
- success condition: displayed state matches canonical settings and active-policy resolution.

### Outcome: Safe optimistic update

- affected actor or system: client update and canonical settings persistence.
- required result: `PATCH /personalization` validates inputs, checks expected revision, persists atomically, and returns refreshed resource with `ETag`.
- success condition: stale updates conflict without overwriting newer state; invalid updates return actionable validation errors.

### Outcome: Supporting administration stays separate

- affected actor or system: legacy optimization administration and completion-critical personalization.
- required result: optimization history and candidate administration remain supporting-only and are not exposed as this JSON resource.
- success condition: core journey works without legacy HTML model or admin row payload.

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| What owns ranking settings? | Canonical settings own ranking mode and strength. | `src/fitcv_cp/settings_store.py` and `src/fitcv_cp/store.py` | high | JSON route delegates to canonical settings ownership. |
| What resolves effective personalization? | Optimization service resolves compatible active policy and fallback/stale semantics. | `src/fitcv_cp/optimization_service.py` | high | Response must distinguish requested from effective mode. |
| Is legacy HTML a usable API? | `/admin/optimization` serves HTML administration surfaces. | existing route inventory | high | Do not expose legacy HTML fields as JSON contract. |

### Prototype and Validation Evidence

- prototype reference: `docs/fitcv-settings-ui-prototype.html` Preference Optimization surfaces.
- UX approval: owner-approved frozen UX.
- frozen prototype revision or reference: `docs/fitcv-settings-ui-prototype.html` at blob `5950dcd2b6a6c4f68b1d522fcea1c0a29d9aff27`.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`.
  - selected export method: verified OpenDesign export.
  - export task reference: OpenDesign run `ea9169ad-d5e0-4e7e-9480-98de93b62a6e`.
  - requested deliverable: FitCV design-system guidance.
  - durable output identity: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md` at blob `8586f2d64bef1ef2ab11db9768877de020e13b89`.
  - independent review: `PASS` recorded for the same OpenDesign run and durable output.
- validated scenarios and states: baseline, personalized with compatible policy, personalized fallback, stale revision, invalid strength, unavailable optimization, and supporting-admin separation.
- findings incorporated into approved behavior: minimal JSON resource, truthful effective state, fit truth independence, and supporting optimization administration.
- rejected alternatives: exposing `/admin/optimization` HTML as JSON, making optimization history completion-critical, and reporting requested mode as effective mode during fallback.

### Scope

- included behavior: minimal JSON read/update contract for ranking mode, personalization strength, revision, bounds, effective policy state, errors, and ETag.
- affected boundaries: new frontend API consumer, canonical settings, optimization policy resolution, and API documentation.
- admissible cases: baseline mode, personalized mode with valid bounded strength, and fallback when no compatible active policy exists.
- compatibility expectation: existing HTML administration routes and optimization internals remain available as supporting surfaces.

### Non-Goals

- optimization history administration or candidate approve/reject/rollback/remove workflows.
- training internals or policy authoring.
- synonym administration.
- exposing legacy HTML fields as a new API.
- changing fit qualification truth.

### Requirements and Behavioral Contract

#### Requirement: Read current personalization state

- trigger or actor: new frontend requests `GET /personalization`.
- preconditions: canonical settings and optimization policy resolver are available.
- required behavior: return `{ "data": { "ranking_mode", "effective_ranking_mode", "personalization_strength", "baseline_fallback", "active_policy_id", "revision", "bounds" } }` from one immutable active-settings snapshot. `revision` is the canonical global active-settings snapshot revision used for CAS.
- output or state change: no mutation; `ETag` equals quoted global settings snapshot revision.
- failure behavior: standard API error envelope when canonical settings or policy state cannot be read.
- observable acceptance: requested and effective state are explicit and truthful.

#### Requirement: Update personalization atomically

- trigger or actor: client sends `PATCH /personalization` with `ranking_mode`, optional `personalization_strength`, and `expected_revision`.
- preconditions: body contains only supported fields; mode is `baseline` or `personalized`; strength is within canonical bounds; expected revision matches current revision.
- required behavior: persist through canonical settings ownership and return refreshed resource with new `ETag`.
- output or state change: ranking preference changes without changing fit qualification truth.
- failure behavior: unknown or invalid fields return `422 validation_failed`; strength supplied with baseline returns `422 validation_failed`; stale revision returns `409 personalization_revision_conflict`; no partial write occurs.
- observable acceptance: successful update is atomic and response reflects effective policy resolution.

#### Requirement: Report fallback truthfully

- trigger or actor: read or update resolves personalized mode without compatible active policy.
- preconditions: requested mode is personalized and policy resolver reports no compatible active policy.
- required behavior: return `baseline_fallback: true`, `effective_ranking_mode: "baseline"`, and `active_policy_id: null`.
- output or state change: UI explains that personalized mode is requested but baseline is currently effective.
- failure behavior: never claim personalized ranking is active without compatible policy.
- observable acceptance: requested mode and effective mode differ only when fallback is true.

| Boundary | Owner or canonical contract | Required evidence |
| --- | --- | --- |
| Requested settings | Canonical settings store | Direct read/update tests |
| Effective policy state | Optimization service | Fallback and compatible-policy tests |
| HTTP resource and errors | `/personalization` API contract | Response-shape and ETag tests |
| Supporting administration | Existing legacy operator routes | Non-coupling regression proof |

### Constraints and Alternatives

- constraint: core personalization must remain optional and must not alter fit qualification truth.
- alternative: expose legacy optimization HTML model as JSON
  - benefit: fewer backend changes.
  - trade-off: couples new frontend to legacy administrative fields and unstable presentation shape.
  - reason accepted or rejected: rejected; canonical settings and policy state require smaller stable resource.

## Design Decisions

### Decision: Separate core personalization from optimization administration

- context: personalization is completion-critical, while history and candidate administration are supporting capabilities.
- selected approach: minimal `/personalization` resource over canonical settings and optimization resolution; retain admin HTML outside contract.
- rationale: preserves one owner for settings and one owner for effective policy while avoiding legacy model leakage.
- alternatives considered: full optimization JSON administration API and direct HTML reuse.
- accepted trade-offs: supporting administration remains separate and may need future specification if product scope changes.
- affected owners and boundaries: backend API owns resource contract; settings store owns persistence; optimization service owns effective state; frontend owns presentation.

### Compatibility, Migration, and Risk

- old behavior: legacy HTML routes expose optimization administration; no minimal JSON resource exists.
- new behavior: new frontend reads and updates core personalization through `/personalization`.
- compatibility boundary: legacy HTML routes and optimization internals remain unchanged and supporting-only.
- migration or backfill: none for existing settings; resource reads current canonical values.
- rollout and rollback: if resource read fails, client shows Personalization unavailable; backend ranking fallback remains authoritative. Existing admin routes may remain temporarily available during legacy frontend retirement.
- deprecation or consumer impact: no existing HTML consumer is required to migrate; future advanced optimization administration needs a separate specification if retained after legacy frontend retirement.
- risk:
  - mitigation: optimistic revision check, atomic persistence, explicit fallback, bounded validation, and fit-truth invariant.

## Invariants and Edge Cases

### Invariants

- canonical settings remain single source for requested ranking mode and strength.
- effective mode never claims personalization without compatible active policy.
- personalization never changes fit qualification truth.
- stale revision never overwrites newer settings.
- supporting administration is not required for core personalization journey.

### Edge Cases

- empty or minimal input: omitted strength preserves current value; baseline mode may omit strength change.
- normal and large input: strength remains bounded by canonical minimum, maximum, and step; no history payload is returned.
- duplicate, missing, malformed, or unsupported data: unknown fields and invalid values fail validation; missing policy resolves fallback.
- retry, cancellation, timeout, partial failure, or concurrency: stale updates conflict; persistence failure produces no partial update; reads may retry through standard API semantics.
- migration or mixed-version state: existing settings are read through canonical compatibility logic; no legacy HTML field migration is required.
- generated-source consistency: API documentation and route response shape must stay aligned.
- security or accessibility boundary: validate at API boundary; expose labels and current effective state with native controls and 44px touch targets.

## Validation Plan

### Backend Verification Claims

- direct boundary: `GET /personalization` and `PATCH /personalization` return documented resource and error shapes.
- important success and failure behavior: prove baseline, compatible personalized, fallback, invalid input, unknown fields, and stale revision.
- final state or side effects: prove atomic settings update and unchanged fit qualification truth.
- rollback, retry, duplicate, or idempotency behavior: prove stale update rejection and repeated same-revision reads/updates do not corrupt settings.
- canonical contract and conformance proof: response, bounds, revision, and ETag match `docs/api.md`.
- real dependencies requiring proof: canonical settings store and optimization service resolution.
- representative-operation trace mechanism: direct API read → update → read trace with policy fallback variant.
- performance claim and threshold: resource read/update must remain within existing local API request budget.

### Acceptance Criterion: Core personalization is independently consumable

- setup or precondition: canonical settings and policy resolver contain baseline or personalized state.
- action: new frontend reads resource and updates valid state.
- expected result: resource contains requested/effective state, bounds, revision, and policy identity without admin rows.
- failure condition: client must parse legacy HTML or response claims unsupported fields.
- proof method: API contract tests and response-shape assertions.
- expected evidence: valid JSON resource and matching ETag.

### Acceptance Criterion: Invalid and stale updates preserve truth

- setup or precondition: current revision and bounded strength are known.
- action: send unknown field, invalid strength, baseline-plus-strength, and stale revision updates.
- expected result: actionable errors return and canonical settings remain unchanged.
- failure condition: partial write, lost update, or personalized claim without compatible policy.
- proof method: direct boundary tests with final-state assertions.
- expected evidence: status/error envelope and unchanged settings snapshot.

## Completion Criteria

Specification is complete when:

1. minimal JSON resource, update body, errors, revision, ETag, and fallback semantics are unambiguous
2. canonical settings and optimization-service ownership are explicit
3. core personalization and supporting administration are separated
4. fit qualification truth is explicitly protected
5. each required outcome maps to acceptance and backend verification intent
6. Design Export and frozen UX evidence are preserved
7. implementation sequencing remains outside this specification
