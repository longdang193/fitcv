# FitCV New Frontend ↔ Backend Reconciliation

**Status:** reconciliation draft; not a specification or implementation plan
**Date:** 2026-08-29

## Authority Boundary

The new frontend is built from scratch. The legacy Jinja frontend is excluded
from implementation, visual, and interaction decisions.

| Concern | Authority |
| --- | --- |
| Product outcome and scope | `docs/intent/success-outcomes.md`, `docs/intent/constraints-and-non-goals.md`, `docs/intent/project-charter.md` |
| Product ownership and dependencies | `docs/intent/master-workstream-roadmap.md` |
| UX structure, interaction, responsive behavior | `docs/fitcv-settings-ui-prototype.html` |
| Visual tokens and reusable component guidance | `design/fitcv-settings-ux-audit/fitcv-design-system-export.md` |
| Request/response and lifecycle behavior | `docs/api.md`, `/openapi.json`, `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py` |
| Focused behavior | active specifications and route/service/store tests |
| Historical parity evidence only | `docs/fitcv-settings-ui-prototype.integration.md` |

The copied prototype under `design/fitcv-settings-ux-audit/` is export evidence,
not a second UX SSOT. The active prototype remains the file under `docs/`.

## Journey Reconciliation

| Product journey | Frozen UX surface | Canonical backend contract | Result | Durable owner |
| --- | --- | --- | --- | --- |
| Local setup and readiness | Overview, API Providers, LLM Configuration, Prompt Management, System/Data Backup | `/healthz`, `/local/readiness`, `/api-providers*`, `/llm-configuration`, `/prompt-configurations*`, `/system-settings`, `/local/data/status`, `/local/lifecycle/status`, `/local/system/diagnostics` | **Aligned with integration work.** Provider, model, prompt, settings, readiness, and diagnostics resources exist. `/local/onboarding/profile` remains form/redirect-shaped and needs a new-frontend entry-flow decision. | FitCV Local Experience |
| Candidate Profile creation | Upload, processing, Baseline, Controlled Derivation, Confirmation | Candidate Profile creation-attempt, source, review, confirmation, retry, catalog, archive, restore, delete routes | **Contract exists.** Bind staged lifecycle, CAS revisions, fingerprints, capabilities, idempotency, polling, and immutable successor revisions. | Candidate Profile Lifecycle |
| Job collection | Scans list, New Scan, Scan Details, output Table/JSON | `/tracked-companies*`, `/scans*`, scan events/jobs/output, cancel, run-again, archive/unarchive, delete preview/delete | **Contract exists.** Use server capabilities and one immutable output for Table and JSON views. | Job Collection and Scans |
| Run trigger and continuity | Runs list, Trigger Run, Run Details, stage/job result views | `POST /runs`, `/runs`, `/runs/{run_id}`, stages, jobs, cancel/archive/unarchive/delete, events, debug bundle | **Contract exists.** Use multipart managed trigger, active confirmed profile, server-owned statuses, immutable snapshots, cursor events, and retryable queue-failure semantics. | Run Continuity and Recovery |
| Fit evaluation and interest | Pipeline Results, fit reasons, Application Interest, job selection | `/runs/{run_id}/jobs`, bookmark and interest routes, filtered CSV export | **Contract exists.** Fit and interest remain separate; do not infer suitability from preference or rating. | Job Evaluation and Personalization |
| Bookmarks | Bookmarks workspace, search/filter, revisit, remove, export | `/bookmarks`, remove, export preview/export, run-job bookmark mutations | **Contract exists.** Preserve bookmark identity, selection preview, filtered export, and dependent-removal truth. | Job Evaluation and Personalization |
| Grounded CV review | View CV, Download CV, Regenerate CV, review state | CV history, `/cv-versions/{version_id}/download`, regeneration action, persisted evaluation/review state | **Partial: preview contract missing.** Frozen UX requires `View CV`; canonical API exposes download but no preview/media contract. | Grounded CV Generation and Review |
| Preference Optimization | Baseline/Personalized Ranking, optimization history/details, policy actions | Current implementation exposes `/admin/optimization*` HTML routes and store/service behavior; no canonical JSON resource is documented | **Gap.** New frontend cannot use HTML as its contract. Need JSON read/action contract or explicit deferral as supporting work. | Job Evaluation and Personalization; supporting optimization child |
| Synonym management | Synonyms list/details, approve/decline/clear, import/export | `/synonym-policies*`, `/synonym-suggestions*`, `/synonym-processing-runs`, backup routes | **Contract exists; supporting only.** It cannot block Personal FitCV unless it breaks a core journey or makes results untruthful. | Job Evaluation and Personalization |
| History, notifications, and diagnostics | Global notification bell, per-run/scan console, prior decisions, recovery actions | Run/Scan immutable events and debug bundle; no global notification collection/clear contract | **Partial: global notification contract missing.** Per-run and per-scan events exist; global count, event creation, clear-one, and clear-all semantics do not. | Decision and History Truth; Reliability and Diagnostics |

## Frozen UX Contract

- Preserve grouped native navigation, hash/deep-link state, current-page state,
  responsive off-canvas navigation, scrim dismissal, and table-local overflow.
- Preserve native inputs, buttons, links, dialogs, disclosures, validation, live
  regions, visible focus, Escape handling, focus containment, and focus return.
- Use one reusable Button, Field, Dialog, Tabs, Status, Table, and Navigation
  contract. Use active Agentic tokens as the production token owner; do not copy
  token values into another SSOT file.
- Keep desktop density for pointer-only compact actions; touch-capable controls
  use the approved `44px` target.
- Keep domain-separated persistence. Never persist provider API keys in client
  state, diagnostics, export files, or logs.

## Contract Gaps Requiring Product/Backend Decisions

### G-01 Global notifications

The frozen shell exposes a notification bell and the prototype supports a count,
recent events, and clearing an individual notification. Canonical backend
contracts expose immutable Run/Scan event streams but no global notification
resource. Decide whether notifications are transient client-only projections or
persisted global activity with unread count, clear-one, clear-all, and retention
semantics.

Do not infer this from the legacy Jinja frontend.

### G-02 CV preview

The frozen UX exposes `View CV` separately from `Download CV`, while the stable
API only defines checksum-verified download bytes. Decide whether preview uses a
new safe preview representation or a frontend-supported rendering of the
downloaded artifact. Preview must not imply generation approval or bypass CV
review state.

### G-03 Preference Optimization transport

The frozen UX includes Preference Optimization. Current routes are under
`/admin/optimization*` and render HTML; they are not a new-frontend transport
contract. Decide whether to promote read/actions/history/console to canonical
JSON resources or explicitly defer this surface as supporting work. Personal
preference must never hide qualification problems.

### G-04 Local onboarding entry flow

`/local/readiness` and canonical Application Settings resources exist, but
`/local/onboarding/profile` uses form submission and redirect behavior while
legacy provider onboarding actions return `410`. Decide whether the new frontend
starts at a JSON-driven local shell using canonical resources, or whether a
bounded onboarding resource is needed. Do not reuse legacy HTML as the contract.

## Gap Classification

| Classification | Findings |
| --- | --- |
| No contract gap | Candidate Profile, Scans, Run lifecycle/results, bookmarks, interest, settings, providers, prompts, synonym APIs, diagnostics streams |
| Frontend integration work | Bind server capabilities, CAS/fingerprints, idempotency, polling, cursor events, error envelopes, focus/recovery states, and responsive contracts |
| Backend/contract decision required | G-01 global notifications, G-02 CV preview, G-03 Preference Optimization JSON transport, G-04 onboarding entry flow |
| Legacy-only evidence | Existing Jinja templates and stale direct parity mappings in `docs/fitcv-settings-ui-prototype.integration.md` |

## Stop Point

This ledger does not promote specifications, create implementation tasks, or
choose backend designs for G-01 through G-04. Next approval is product-owner
resolution of those contract decisions, followed by focused spec amendments only
where a decision changes durable behavior. A frontend implementation plan comes
after reconciliation acceptance.
