---
layer: change
artifact_type: spec
status: proposed
template_id: draft-specification
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

## Goal and Scope

- problem or opportunity: completion-critical personalization is implemented behind `/admin/optimization` HTML routes, which a new frontend cannot consume as a stable JSON contract.
- affected users or systems: users optionally prioritizing future jobs, ranking settings, and existing preference-learning services.
- desired outcome: new frontend can read and enable/disable core personalized ranking without inheriting legacy admin HTML.
- included scope: minimal JSON read/update contract for ranking mode and personalization strength, plus truthful active-policy status.
- excluded scope: optimization history administration, candidate approve/reject/rollback/remove workflows, HTML route exposure, training internals, and synonym administration.

## User Flow and Business Rules

1. Client reads `GET /personalization`.
2. Client shows baseline or personalized ranking state and current strength.
3. Client sends `PATCH /personalization` with `ranking_mode`, `personalization_strength`, and `expected_revision`.
4. Server validates, persists atomically through canonical settings ownership, and returns refreshed resource with `ETag`.

- `ranking_mode` is `baseline` or `personalized`; personalized mode remains optional and must not alter fit qualification truth.
- Strength is bounded by existing optimization policy/settings validation; omitted strength preserves current value. Sending strength while target mode is `baseline` returns `422 validation_failed`.
- Stale revision returns `409 personalization_revision_conflict`; invalid values return `422 validation_failed`.
- If personalized mode has no compatible active policy, response reports `baseline_fallback: true`, `effective_ranking_mode: "baseline"`, and `active_policy_id: null`; it must not claim personalized ranking is active.
- Core personalization does not expose optimization candidate rows or legacy HTML fields.
- Supporting administration remains behind existing operator routes until separately approved.

### JSON Contract

`GET /personalization` and successful `PATCH /personalization` return:

```json
{
  "data": {
    "ranking_mode": "baseline|personalized",
    "effective_ranking_mode": "baseline|personalized",
    "personalization_strength": 0.05,
    "baseline_fallback": false,
    "active_policy_id": "opaque-or-null",
    "revision": "sha256",
    "bounds": {"minimum": 0.01, "maximum": 0.1, "step": 0.01},
    "updated_at": "ISO-8601"
  }
}
```

`PATCH` body is `{ "ranking_mode": "baseline|personalized", "personalization_strength": 0.05, "expected_revision": "sha256", "updated_by": "admin" }`. Unknown fields are rejected. `ETag` equals the resource revision in quotes. Errors use the standard API envelope.

## UI Intent and Known States

- target platform: new frontend Preference Optimization area within Personal FitCV.
- intended interaction: optional toggle/mode selector and bounded strength control with current effective state.
- loading, empty, success, error, disabled, and retry states: baseline default; personalized active; personalized requested but fallback; revision conflict reload; invalid input correction; unavailable optimization remains supporting explanation.
- accessibility or responsive intent: native controls, labels, visible current mode, 44px touch targets, no hidden suitability changes.
- durable design-system owner: Agentic Design System SSOT; verified FitCV Design Export is guidance evidence.

## Assumptions and Open Questions

### Verified Facts

- canonical settings already own `preference_optimization.ranking_mode` and `preference_optimization.personalization_strength`.
- optimization service already resolves compatible active policy and reports fallback/stale semantics.
- legacy optimization routes are HTML and therefore not a new-frontend API.

### Assumptions

- one resource is enough for completion-critical personalization; history/admin stays supporting.

### Open Questions

- none that change the minimum JSON contract.

## Prototype and Validation Findings

- prototype reference: `docs/fitcv-settings-ui-prototype.html` Preference Optimization surfaces.
- UX approval: owner-approved frozen UX.
- design export evidence: `design/fitcv-settings-ux-audit/fitcv-design-system-export.md`; gate state: complete.
- scenario required for validation: baseline, personalized with compatible policy, personalized fallback, stale revision, invalid strength.
- observed result: new frontend needs read/update JSON; HTML admin model is not reusable contract.
- accepted behavior: optional personalization only; fit truth remains independent.
- rejected behavior: exposing `/admin/optimization` HTML as JSON, making optimization history completion-critical.
- remaining uncertainty: exact resource field naming can follow existing API conventions without changing behavior.
- boundary implication when material: backend JSON route over canonical settings/service ownership.

## Promotion Readiness

- owner approval or `Not approved: <reason>`: proposed pending independent specification review.
- approval reference: accepted reconciliation finding G-03.
- remaining blockers or `None identified`: independent review.
- approved deferrals with owner, rationale, trigger, and approval reference or `None`: optimization administration remains supporting; product owner, promote only if core journey requires it.
- unresolved behavior-changing questions or `None`: None.
