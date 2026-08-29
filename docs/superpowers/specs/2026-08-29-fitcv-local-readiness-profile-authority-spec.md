---
layer: change
artifact_type: spec
status: proposed
template_id: draft-specification
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

## Goal and Scope

- problem or opportunity: Local onboarding stores independent `profile_configured` truth while confirmed Candidate Profiles already own selectable profile readiness.
- affected users or systems: Local onboarding/readiness, Candidate Profiles, run eligibility, and recovery flows.
- desired outcome: readiness reports profile readiness from canonical confirmed Candidate Profiles and never from stale onboarding flag.
- included scope: readiness calculation, onboarding migration/compatibility, and profile save behavior.
- excluded scope: new top-level lifecycle navigation, changing Candidate Profile confirmation semantics, or deleting historical onboarding files without migration evidence.

## User Flow and Business Rules

1. Client requests `GET /local/readiness`.
2. Server checks integration migration, provider/model readiness, and canonical Candidate Profile catalog.
3. Server reports profile readiness only when `len(store.list_candidate_profiles()) > 0`; canonical query selects `creation_status = 'succeeded' AND lifecycle = 'active'`.
4. Onboarding completion uses that same readiness result.

- Draft text or legacy profile file does not satisfy profile readiness.
- Archived, deleted, malformed, or unconfirmed profiles do not satisfy profile readiness.
- `onboarding.json.profile_configured` is ignored for readiness and must not be written for new state; `save_onboarding_state()` drops it from persisted output.
- Existing state may retain legacy field for backward-compatible parsing, but readiness must derive from canonical profile store.
- Legacy `POST /local/onboarding/profile` remains draft-only compatibility: it may save `drafts.profile`, but never sets `profile_configured`; new clients use `POST /candidate-profile-creation-attempts`.
- Run guards and readiness must agree on what “profile ready” means.
- If onboarding state or the canonical catalog cannot be read, `GET /local/readiness` returns `503` with `error.code = "local_readiness_unavailable"`, `retryable = true`, and an actionable recovery message.

## UI Intent and Known States

- target platform: new frontend Local Overview/onboarding.
- intended interaction: one readiness card links to Candidate Profiles when no confirmed profile exists and to provider/model setup for remaining blockers.
- loading, empty, success, error, disabled, and retry states: loading; no confirmed profile; confirmed active profile; only archived/unconfirmed profiles; provider not ready; malformed local state with actionable recovery.
- accessibility or responsive intent: semantic status, explicit reason text, keyboard links, and 44px actions.
- durable design-system owner: Agentic Design System SSOT; verified FitCV Design Export is guidance evidence.

## Assumptions and Open Questions

### Verified Facts

- `local_readiness_status()` currently reads `profile_configured` from onboarding state.
- Candidate Profile catalog already exposes lifecycle and confirmed profile records.
- onboarding provider actions already redirect to canonical provider APIs or are retired.
- `GET /local/readiness` returns `{"ready": bool, "reasons": string[]}`; malformed local state currently raises a server error and needs actionable handling.
- Run eligibility uses the same active-profile predicate as readiness: `creation_status = 'succeeded' AND lifecycle = 'active'`.

### Assumptions

- one canonical active confirmed profile is sufficient for profile readiness.

### Open Questions

- none that change authority ownership.

## Prototype and Validation Findings

- prototype reference: `docs/fitcv-settings-ui-prototype.html` Overview and Candidate Profiles entry flow.
- UX approval: owner-approved frozen UX.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`; gate state: complete.
- scenario required for validation: fresh install, draft only, confirmed active profile, archived-only profile, stale onboarding flag, provider incomplete, and catalog failure.
- observed result: independent profile flag can claim readiness despite no usable confirmed profile.
- accepted behavior: canonical Candidate Profiles determine readiness; onboarding is orchestration, not profile truth.
- rejected behavior: saved draft or boolean flag making profile selectable.
- remaining uncertainty: migration cleanup timing for old `profile_configured` keys.
- boundary implication when material: backend local-readiness and onboarding persistence; no frontend implementation task yet.

## Promotion Readiness

- owner approval or `Not approved: <reason>`: proposed pending independent specification review.
- approval reference: accepted reconciliation finding G-04.
- remaining blockers or `None identified`: independent review.
- approved deferrals with owner, rationale, trigger, and approval reference or `None`: retain tolerant reads for existing files, remove key on next successful save, and verify fresh-install plus upgrade fixtures before deleting tolerant-read logic; product owner owns cleanup approval.
- unresolved behavior-changing questions or `None`: None.
