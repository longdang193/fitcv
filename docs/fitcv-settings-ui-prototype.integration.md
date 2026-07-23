# Preference Optimization Prototype Integration Intent

Status: UI intent revised; prototype remains local-state only until backend contracts are updated and wired.

Operation: select ranking mode, manage Personalization Strength, and create, inspect, activate, inactivate, remove, or clear the current console view for optimization runs from saved application-interest ratings.

Current contract owners:

- decision-learning policy: `config/policy/decision_learning.yaml`
- optimization lifecycle: existing `/admin/optimization` routes and shared optimization service
- rating evidence: canonical stored rating events and compiled preference comparisons

Future contract owner: backend Preference Optimization API exposing ranking mode, bounded Personalization Strength, rating evidence, and optimization lifecycle data. This sidecar does not define transport schemas.

## UI Behavior

- `Preference Optimization` uses the same collapsible section, setting row, `Manage` dialog, and table patterns as other Pipeline settings pages.
- Section 1, `Ranking Mode`, exposes a dropdown with `Baseline Ranking` and `Personalized Ranking`.
- When `Personalized Ranking` has no active successful policy, the UI states that `Baseline Ranking` will be used.
- Section 2, `Personalization Strength`, is disabled for `Baseline Ranking` and edited through `Manage` for `Personalized Ranking`. Helper text explains how higher and lower values affect ranking movement.
- Prototype-only bounds are `0.01–0.10`, step `0.01`, recommended `0.05`. Backend policy must replace these illustrative values before production wiring.
- Section 3, `Rating Evidence`, shows saved ratings across runs and exposes `Optimize Current Ratings` without a readiness gate. The button is disabled for `Baseline Ranking`.
- A new optimization appears immediately in Section 4, `Optimization Runs`, with `Running`, `Succeeded`, or `Failed` status.
- Optimization Runs uses `Activate Policy` or `Inactivate Policy` plus `Remove`; no Usage column or Reject action exists. All action buttons are disabled for `Baseline Ranking`.
- Only one policy can be active. Activating another policy inactivates the previous one and selects `Personalized Ranking`.
- Optimization IDs open restorable details at `#preference-optimization/{optimization_id}`.
- Details place `Activate Policy` or `Inactivate Policy` at the top right. The action is disabled for `Baseline Ranking`, with a message directing the user to select `Personalized Ranking`.
- Details contain Overview, Rating Evidence, and Console Log only. Overview omits Policy Version; both rating tables use the same columns and styles. Console Log provides `Clear`, which clears the current view without deleting authoritative lifecycle evidence.
- Completed pipeline results never change when ranking mode or active policy changes.

## Backend Integration Intent

- Backend returns authoritative ranking mode plus Personalization Strength minimum, maximum, recommended value, step, and current value.
- Backend returns canonical rating evidence rows for both the main page and optimization details.
- Optimization creation accepts one backend-validated strength and returns a durable optimization run immediately.
- Optimization run status is backend-owned and transitions through supported lifecycle states.
- Every successful optimization stores the exact strength and rating evidence snapshot used.
- Backend allows one active successful policy at a time and supports explicit activation, inactivation, and removal rules.
- Backend rejects optimization creation and policy mutations when ranking mode is `Baseline Ranking`; disabled UI controls are not the enforcement boundary.
- Runtime scoring uses the active policy only when ranking mode is `Personalized Ranking`; otherwise it uses baseline ranking.
- Personalized mode without an active compatible policy safely falls back to baseline ranking.
- UI must not write `decision_learning.yaml`; policy YAML owns bounds and defaults while mutable user settings belong to backend storage.
- Console logs expose bounded, authorized lifecycle events without sensitive free-text rating content.

## Required Evidence

- Ranking mode selection survives refresh and matches runtime behavior.
- Personalization Strength cannot be managed while Baseline Ranking is selected.
- Optimize Current Ratings and all Optimization Runs actions are disabled while Baseline Ranking is selected.
- Optimization details disable the policy action under Baseline Ranking and explain how to enable it.
- Backend-provided strength bounds reject malformed values.
- Rating Evidence columns and rows match on the main and details pages.
- Optimization creation appears immediately with status and captures the selected strength.
- Activate Policy, Inactivate Policy, and Remove enforce one-active-policy semantics and preserve unrelated runs.
- Personalized mode without an active policy visibly and operationally falls back to baseline ranking.
- Direct detail URL, refresh, Back, and Forward preserve the selected Optimization ID.
- Clear removes Console Log entries from the current view without deleting authoritative lifecycle evidence.
- Running, success, failure, empty, active, inactive, baseline, and personalized states pass.
- Light, dark, narrow, zoomed, keyboard, focus, and reduced-motion states pass.
- Browser request payload and visible lifecycle state match canonical backend contracts and focused tests.

## Known Backend Gap

- Current contract keeps `inverse_optimization.learned_alpha` config-only and accepts no numeric optimizer parameter from admin UI or CLI.
- Backend schemas, persistence, policy fingerprinting, runtime resolution, lifecycle compatibility, routes, and tests must be updated together before wiring editable Personalization Strength and ranking mode.
