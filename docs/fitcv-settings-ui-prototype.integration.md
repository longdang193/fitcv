# Preference Optimization Prototype Integration Intent

Status: pending implementation against `docs/superpowers/specs/2026-07-23-12-31-fitcv-preference-optimization-frontend-backend-integration-spec.md`.

Operation: select workspace Ranking Mode, manage bounded workspace Personalization Strength, synchronously optimize current ratings, inspect historical evidence, activate or inactivate one policy, remove a run from the normal list, and clear the current Console Log view.

Contract owner: `docs/superpowers/specs/2026-07-23-12-31-fitcv-preference-optimization-frontend-backend-integration-spec.md`. Canonical source, routes, persistence, runtime contracts, and tests replace this temporary sidecar as implementation lands.

## UI Behavior

- Reuse existing Pipeline setting rows, Manage dialog, collapsible sections, tables, statuses, buttons, and Console patterns.
- Ranking Mode is a persisted workspace select with Baseline Ranking and Personalized Ranking.
- Personalization Strength is workspace-wide, disabled under baseline, bounded by backend policy metadata, and captured per Optimization Run.
- Changing strength while policy is active is blocked with `Inactivate Policy before changing Personalization Strength.` Manual inactivation keeps Personalized Ranking selected and shows baseline fallback.
- Optimize Current Ratings is disabled only under baseline. Submission is synchronous with transient `Optimizing…` and terminal `Succeeded`, `No Change`, `Not Created`, or `Failed` row.
- Optimization Runs uses public `preference_optimization_run_id`; production details use direct server URLs.
- Activate/Inactivate actions are disabled under baseline. Inactivate keeps Personalized Ranking selected and shows fallback.
- Active but runtime-incompatible policy displays `Active · Not in use`; Inactivate remains available under Personalized Ranking.
- Remove permanently hides non-active row from current default view without deleting backend record, evidence, policy, or audit history. Storage keeps reversible `hidden_at`; no Restore UI exists until separately needed.
- Details contain Overview, historical Rating Evidence, and Console Log only. Clear changes current browser view only.
- Personalized Ranking without compatible active policy displays baseline fallback.

## Backend Integration Intent

- Use existing revisioned workspace settings and server-rendered PRG forms.
- Keep optimization synchronous; add no JSON API, typed client, polling, or durable Running state.
- Retain internal `training_run_id`; expose only public `preference_optimization_run_id` in normal UI.
- Store exact strength, settings revision, evidence fingerprint, event watermark, source rating-event IDs, and minimal immutable displayed rows for each new run.
- Preserve CAS, provenance, one-active-domain-policy, local Host/Origin/CSRF/onboarding, and server-derived audit actor.
- Mount feature only in local mode.

## Required Evidence

- Mode and strength survive refresh/restart and match ranking runtime.
- Baseline disables strength, optimization, and policy actions in UI and backend.
- Personalized fallback is visible and operational without compatible active policy.
- Synchronous submissions create one idempotent terminal run with correct status mapping.
- Historical details remain stable after rating changes and trace to source event IDs.
- Activation/inactivation preserve audit and one-active-policy semantics.
- Remove hides only normal row; direct details and backend history remain.
- Direct details, refresh, Back, Forward, Console Clear, validation, stale, and duplicate-submit states pass.
- Light, dark, narrow, 200% zoom, keyboard, focus, reduced-motion, and contrast states pass.
- Existing optimization/runtime contracts and prototype self-checks pass after integration.

## Known Backend Gap

- Current source lacks persisted Ranking Mode, workspace Strength, public Preference Optimization Run identity, historical display snapshots, direct details, dedicated Inactivate action, and hide-from-list metadata.
- Implement affected owners together; never wire prototype-local state directly.
