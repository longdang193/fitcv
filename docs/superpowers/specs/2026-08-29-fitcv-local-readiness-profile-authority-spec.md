---
layer: change
artifact_type: spec
status: active
template_id: detailed-specification
name: fitcv-local-readiness-profile-authority
targets:
  - src/fitcv_cp/local_routes.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/store.py
  - docs/api.md
related_features:
  - local-readiness
  - candidate-profile-lifecycle
  - onboarding
---

# FitCV Local Readiness and Profile Authority

## Goal and Problem

### Problem

- current behavior or opportunity: Local onboarding stores independent `profile_configured` truth while confirmed Candidate Profiles already own selectable profile readiness.
- affected users, systems, or maintainers: Local onboarding/readiness, Candidate Profiles, run eligibility, and recovery flows.
- evidence: readiness reads onboarding state while canonical profile records already expose lifecycle and confirmation state.
- consequence of no change: stale onboarding flags can claim readiness without a usable confirmed profile.

### Goal

- desired outcome: readiness reports profile readiness from canonical confirmed Candidate Profiles and never from stale onboarding flag.
- observable success: onboarding and run eligibility agree on one active confirmed-profile predicate, including failure and recovery states.

## Required Outcomes

### Outcome: Canonical profile readiness

- affected actor or system: Local Overview/onboarding and Candidate Profiles.
- required result: profile readiness is true only when at least one active confirmed Candidate Profile exists.
- success condition: drafts, archived profiles, deleted profiles, malformed records, and stale booleans do not satisfy readiness.

### Outcome: Consistent recovery and run eligibility

- affected actor or system: readiness endpoint, onboarding orchestration, and run guards.
- required result: provider/model blockers and catalog failures are explicit; run guards use same profile predicate.
- success condition: users receive actionable recovery without a second profile authority.

## Design Analysis

### Current State and Evidence

| Question | Evidence | Source | Confidence | Specification implication |
|---|---|---|---|---|
| What currently controls readiness? | `local_readiness_status()` uses `ControlPlaneStore.list_candidate_profiles()` with its canonical active-only predicate; it does not parse onboarding state. | `src/fitcv_cp/local_routes.py` and `src/fitcv_cp/sqlite_store.py` | high | Keep profile readiness owned by the canonical catalog. |
| What owns usable profiles? | Candidate Profile catalog filters `creation_status = 'succeeded'` and `lifecycle = 'active'`. | `src/fitcv_cp/sqlite_store.py` and profile routes | high | Use the same active confirmed predicate for readiness and run eligibility. |
| What does run eligibility require? | Run guards use `creation_status = 'succeeded'` and `lifecycle = 'active'`. | `src/fitcv_cp/sqlite_store.py` and run routes | high | Readiness and run guards share equivalent profile semantics. |
| What happens on local-state failure? | Malformed legacy onboarding JSON is tolerated by onboarding compatibility reads; canonical store, provider, or configuration failures return structured unavailable readiness. | `src/fitcv_cp/local_routes.py` and readiness tests | high | Do not turn stale onboarding syntax into false readiness or an unrelated readiness outage. |

### Prototype and Validation Evidence

- prototype reference: `docs/fitcv-settings-ui-prototype.html` Overview and Candidate Profiles entry flow.
- UX approval: owner-approved frozen UX.
- frozen prototype revision or reference: `docs/fitcv-settings-ui-prototype.html` at blob `5950dcd2b6a6c4f68b1d522fcea1c0a29d9aff27`.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`.
  - selected export method: verified OpenDesign export.
  - export task reference: OpenDesign run `ea9169ad-d5e0-4e7e-9480-98de93b62a6e`.
  - requested deliverable: FitCV design-system guidance.
  - durable output identity: `fitcv-design-system-export.md` at blob `8586f2d64bef1ef2ab11db9768877de020e13b89`.
  - independent review: `PASS` recorded for the same OpenDesign run and durable output.
- validated scenarios and states: fresh install, draft only, confirmed active profile, archived-only profile, stale onboarding flag, provider incomplete, and catalog failure.
- findings incorporated into approved behavior: canonical confirmed profiles determine readiness; onboarding orchestrates but does not own profile truth.
- rejected alternatives: saved draft, legacy profile file, or boolean flag making profile selectable; new top-level lifecycle navigation.

### Scope

- included behavior: readiness calculation, profile authority, onboarding compatibility, profile save behavior, structured catalog failure, and consistent run eligibility.
- affected boundaries: local readiness API, onboarding persistence, Candidate Profile catalog, and run guards.
- admissible cases: no profile, draft-only, active confirmed profile, archived/unconfirmed profiles, provider blockers, and local/catalog failure.
- compatibility expectation: existing onboarding files remain readable; malformed legacy onboarding is ignored for readiness; `profile_configured` is tolerated but cannot control readiness.

### Non-Goals

- changing Candidate Profile confirmation semantics.
- deleting historical onboarding files without migration evidence.
- adding a top-level Lifecycle navigation item.
- changing provider/model configuration ownership.

### Requirements and Behavioral Contract

#### Requirement: Derive profile readiness from canonical catalog

- trigger or actor: client requests `GET /local/readiness`.
- preconditions: local readiness dependencies can be read.
- required behavior: profile readiness is true only when at least one Candidate Profile satisfies `creation_status = 'succeeded' AND lifecycle = 'active'`.
- output or state change: readiness response reports profile reason alongside provider/model reasons.
- failure behavior: draft, archived, deleted, malformed, unconfirmed, or stale onboarding state does not satisfy profile readiness; malformed onboarding alone does not produce `503`.
- observable acceptance: toggling `onboarding.json.profile_configured` alone never changes readiness.

#### Requirement: Remove independent onboarding profile truth

- trigger or actor: onboarding state is loaded or saved.
- preconditions: state may contain legacy `profile_configured` field.
- required behavior: readiness ignores the field; new saves do not write it; tolerant reads may retain old files without using the field.
- output or state change: canonical Candidate Profile catalog remains only profile-readiness authority.
- failure behavior: legacy draft endpoint may save `drafts.profile` but never marks profile ready; new clients use canonical profile creation flow.
- observable acceptance: draft creation and legacy field presence leave profile readiness false until confirmed active profile exists.

#### Requirement: Report actionable local-readiness failure

- trigger or actor: canonical catalog, provider registry, or required local configuration cannot be read.
- preconditions: a canonical readiness dependency fails at its boundary.
- required behavior: return `503` with `error.code = "local_readiness_unavailable"`, `retryable = true`, and actionable recovery message.
- output or state change: frontend can show recovery action without claiming readiness.
- failure behavior: no partial readiness result is presented as complete.
- observable acceptance: catalog/readiness failure produces documented retryable error.

| Boundary | Owner or canonical contract | Required evidence |
| --- | --- | --- |
| Profile readiness | Canonical Candidate Profile catalog | Direct predicate tests |
| Onboarding orchestration | Local onboarding state and readiness route | Legacy-field compatibility tests |
| Run eligibility | Existing active confirmed-profile guard | Cross-boundary consistency tests |
| Failure response | `GET /local/readiness` error envelope | 503 response assertions |

### Constraints and Alternatives

- constraint: one profile-readiness authority must serve onboarding and run eligibility.
- alternative: retain `profile_configured` as independent readiness flag
  - benefit: simple onboarding check.
  - trade-off: stale state can contradict actual profile catalog.
  - reason accepted or rejected: rejected because it violates SSOT and makes results untruthful.

## Design Decisions

### Decision: Candidate Profiles own profile readiness

- context: onboarding boolean and canonical profile lifecycle can diverge.
- selected approach: calculate readiness from active confirmed Candidate Profiles; treat onboarding as orchestration only.
- rationale: preserves one authority and aligns readiness with run eligibility.
- alternatives considered: onboarding flag authority, draft-file authority, and dual reconciliation logic.
- accepted trade-offs: older onboarding files retain tolerated legacy field until cleanup evidence supports removal.
- affected owners and boundaries: Candidate Profile catalog owns profile truth; local readiness owns aggregation and recovery presentation.

### Compatibility, Migration, and Risk

- old behavior: onboarding `profile_configured` can influence readiness.
- new behavior: readiness uses active confirmed Candidate Profiles and ignores independent profile boolean.
- compatibility boundary: old files parse; legacy draft endpoint remains draft-only; canonical profile creation path remains authoritative.
- migration or backfill: do not rewrite historical files; tolerate malformed legacy onboarding and ignore `profile_configured`; remove the legacy key only on a future successful save where supported; require fresh-install and upgrade evidence before deleting tolerant reads.
- rollout and rollback: readiness can fall back to retryable unavailable response on dependency failure; no data deletion is required.
- deprecation or consumer impact: clients relying on stale boolean may see not-ready until a confirmed active profile exists; this is intentional truth correction.
- risk:
  - mitigation: shared active-profile predicate, explicit reasons, retryable errors, and compatibility reads.

## Invariants and Edge Cases

### Invariants

- only active confirmed Candidate Profiles satisfy profile readiness.
- onboarding state never independently claims a usable profile.
- readiness and run eligibility use equivalent profile predicates.
- draft or archived profiles remain visible as data but do not satisfy readiness.
- dependency failure never returns ready=true.

### Edge Cases

- empty or minimal input: fresh install with no profile returns not-ready with Candidate Profiles action.
- normal and large input: multiple active confirmed profiles still yield profile-ready; profile list size does not change predicate semantics.
- duplicate, missing, malformed, or unsupported data: malformed records are excluded; missing catalog/readiness dependency returns retryable unavailable error.
- retry, cancellation, timeout, partial failure, or concurrency: retryable failure preserves no false readiness; profile creation completion is re-read from canonical catalog.
- migration or mixed-version state: malformed legacy onboarding is tolerated for compatibility paths; `profile_configured` is tolerated for reads but ignored by readiness; next successful save may remove it.
- generated-source consistency: API documentation, onboarding serialization, and readiness response remain aligned.
- security or accessibility boundary: readiness reason text, semantic status, keyboard recovery links, and 44px actions are required.

## Validation Plan

### Backend Verification Claims

- direct boundary: `GET /local/readiness` derives profile state from canonical catalog and returns documented success/error shape.
- important success and failure behavior: prove fresh install, draft-only, active confirmed, archived-only, stale flag, provider incomplete, and catalog failure.
- final state or side effects: prove readiness reads do not mutate onboarding or profile data; saves do not create new profile authority.
- rollback, retry, duplicate, or idempotency behavior: repeated readiness reads are stable; dependency failure is retryable and does not persist false state.
- canonical contract and conformance proof: response and `local_readiness_unavailable` envelope match `docs/api.md`.
- real dependencies requiring proof: onboarding persistence and canonical Candidate Profile catalog.
- representative-operation trace mechanism: readiness read → profile creation confirmation → readiness read, plus stale-flag and failure traces.
- performance claim and threshold: readiness calculation remains bounded by one canonical profile catalog read plus existing provider/model checks.

### Acceptance Criterion: Profile readiness has one authority

- setup or precondition: onboarding flag is true while no active confirmed profile exists; then create confirmed active profile.
- action: request readiness before and after profile confirmation.
- expected result: first response is not-ready; second is profile-ready; changing flag alone has no effect.
- failure condition: stale flag returns ready or draft/archived profile satisfies readiness.
- proof method: direct API tests with final catalog/state assertions.
- expected evidence: readiness responses and canonical profile records.

### Acceptance Criterion: Local failures are actionable

- setup or precondition: readiness dependency or profile catalog read fails.
- action: request `GET /local/readiness`.
- expected result: `503`, `local_readiness_unavailable`, `retryable: true`, and recovery message.
- failure condition: uncaught server error or ready=true response.
- proof method: boundary failure tests.
- expected evidence: status, error envelope, and unchanged persisted state.

## Completion Criteria

Specification is complete when:

1. canonical profile predicate and onboarding authority boundary are unambiguous
2. readiness response, failure envelope, compatibility, and migration behavior are defined
3. onboarding, Candidate Profiles, and run eligibility ownership is explicit
4. fresh-install, upgrade, stale-flag, malformed, and dependency-failure cases are covered
5. each required outcome maps to acceptance and backend verification intent
6. Design Export and frozen UX evidence are preserved
7. implementation sequencing remains outside this specification
