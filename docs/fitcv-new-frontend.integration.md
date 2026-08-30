# FitCV New Frontend ↔ Backend Reconciliation

**Status:** historical reconciliation evidence; current ownership is the active parent specification and proposed vertical-slice implementation plan
**Date:** 2026-08-29

This August 29, 2026 note preserves closed backend/frontend contract evidence.
It is non-normative for current implementation ownership. Current durable
behavior is owned by `docs/superpowers/specs/2026-08-30-fitcv-new-frontend-production-spec.md`;
current implementation sequencing is owned by
`docs/superpowers/plans/2026-08-29-fitcv-new-frontend-vertical-slice-plan.md`.

## Authority Boundary

The new frontend is built from scratch. Legacy Jinja frontend is excluded from
implementation, visual, and interaction authority.

| Concern | Authority |
| --- | --- |
| Product outcome and scope | `docs/intent/success-outcomes.md`, `docs/intent/constraints-and-non-goals.md`, `docs/intent/project-charter.md` |
| Product ownership and dependencies | `docs/intent/project-charter.md`, `docs/intent/success-outcomes.md`, `docs/intent/constraints-and-non-goals.md` |
| UX structure, interaction, responsive behavior | `docs/fitcv-settings-ui-prototype.html` |
| Visual tokens and reusable component guidance | Agentic Design System SSOT; verified export guidance in `design/fitcv-settings-ux-audit/fitcv-design-system-export.md` |
| Request/response and lifecycle behavior | `docs/api.md`, `/openapi.json`, `src/fitcv_cp/app.py`, `src/fitcv_cp/local_routes.py` |
| Focused behavior | active specifications and route/service/store tests |
| Historical parity evidence only | `docs/fitcv-settings-ui-prototype.integration.md` |

The copied prototype under `design/fitcv-settings-ux-audit/` is export evidence,
not a second UX SSOT. Active prototype remains file under `docs/`.

## Journey Reconciliation

| Product journey | Frozen UX surface | Canonical backend contract | Result | Durable owner |
| --- | --- | --- | --- | --- |
| Local setup and readiness | Overview, API Providers, LLM Configuration, Prompt Management, System/Data Backup | `/healthz`, `/local/readiness`, `/api-providers*`, `/llm-configuration`, `/prompt-configurations*`, `/system-settings`, `/local/data/status`, `/local/lifecycle/status`, `/local/system/diagnostics` | **Aligned.** `/local/readiness` derives profile readiness from active confirmed Candidate Profiles; legacy onboarding profile input remains draft-only and cannot claim readiness. | FitCV Local Experience |
| Candidate Profile creation | Upload, processing, Baseline, Controlled Derivation, Confirmation | Candidate Profile creation-attempt, source, review, confirmation, retry, catalog, archive, restore, delete routes | **Aligned.** Bind staged lifecycle, CAS revisions, fingerprints, capabilities, idempotency, polling, and immutable successor revisions. | Candidate Profile Lifecycle |
| Job collection | Scans list, New Scan, Scan Details, output Table/JSON | `/tracked-companies*`, `/scans*`, scan events/jobs/output, cancel, run-again, archive/unarchive, delete preview/delete | **Aligned.** Use server capabilities and one immutable output for Table and JSON views. | Job Collection and Scans |
| Run trigger and continuity | Runs list, Trigger Run, Run Details, stage/job result views | `POST /runs`, `/runs`, `/runs/{run_id}`, stages, jobs, cancel/archive/unarchive/delete, events, debug bundle | **Aligned.** Use managed trigger, active confirmed profile, server-owned statuses, immutable snapshots, cursor events, and retryable queue-failure semantics. | Run Continuity and Recovery |
| Fit evaluation and interest | Pipeline Results, fit reasons, Application Interest, job selection | `/runs/{run_id}/jobs`, bookmark and interest routes, filtered CSV export | **Aligned.** Fit and interest remain separate; do not infer suitability from preference or rating. | Job Evaluation and Personalization |
| Bookmarks | Bookmarks workspace, search/filter, revisit, remove, export | `/bookmarks`, remove, export preview/export, run-job bookmark mutations | **Aligned.** Preserve bookmark identity, selection preview, filtered export, and dependent-removal truth. | Job Evaluation and Personalization |
| Grounded CV review | View CV, Download CV, Regenerate CV, review state | CV history, `/cv-versions/{version_id}/preview`, `/cv-versions/{version_id}/download`, regeneration action, persisted evaluation/review state | **Aligned.** Preview returns exact safe text bytes for selected immutable version; download remains attachment-only and review/evaluation truth stays separate. | Grounded CV Generation and Review |
| Preference Optimization | Baseline/Personalized Ranking, optimization history/details, policy actions | `/personalization`; legacy `/admin/optimization*` remains supporting administration | **Aligned for completion-critical journey.** JSON read/update exposes only ranking preference and truthful fallback; optimization history/admin remains supporting and is not exposed as legacy HTML API. | Job Evaluation and Personalization; supporting optimization child |
| Synonym management | Synonyms list/details, approve/decline/clear, import/export | `/synonym-policies*`, `/synonym-suggestions*`, `/synonym-processing-runs`, backup routes | **Aligned; supporting only.** It cannot block Personal FitCV unless it breaks a core journey or makes results untruthful. | Job Evaluation and Personalization |
| History, notifications, and diagnostics | Global notification bell, per-run/scan console, prior decisions, recovery actions | Run/Scan immutable events and debug bundle; client-owned transient notification projection | **Aligned.** Notification semantics are session-scoped client state with deduplication, clear-one, clear-all, and zero-badge behavior; durable history remains Run/Scan events. | Decision and History Truth; Reliability and Diagnostics |

## Frozen UX Contract

- Preserve grouped native navigation, hash/deep-link state, responsive off-canvas navigation, scrim dismissal, and table-local overflow.
- Preserve native inputs, buttons, links, dialogs, disclosures, validation, live regions, visible focus, Escape handling, focus containment, and focus return.
- Use one reusable Button, Field, Dialog, Tabs, Status, Table, and Navigation contract. Active Agentic tokens own production values; export remains guidance evidence.
- Keep desktop density for pointer-only compact actions; touch-capable controls use approved `44px` target.
- Keep domain-separated persistence. Never persist provider API keys in client state, diagnostics, export files, or logs.

## Resolved Contract Findings

### G-01 Global notifications — resolved

Client-owned per-tab/session projection; storage mechanism is implementation
owned and is not part of contract. Deduplicate in priority order by
`action:{action_id}`, `event:{event_id}`,
`state:{source_type}:{source_id}:{revision}:{state}`, then
`request:{operation}:{source_id?}:{error_code}:{attempt_identity}`. Keep client
notification IDs separate from dedupe identities; mark rendered items read;
support clear-one and clear-all; hide badge at zero. No backend notification
service.

### G-02 CV preview — resolved

`GET /cv-versions/{version_id}/preview` returns exact persisted
`text/markdown` or `text/plain` bytes inline after checksum validation. Pending
or running states are retryable; failed, corrupt, unsupported, and missing
states use canonical non-retryable/not-found semantics. The client disables
unsafe HTML/script execution, rejects unsafe URL schemes, renders plain text as
text, and falls back to plain text when safe rich rendering is unavailable.
Version identity, evaluation/review state, and download behavior remain intact.

### G-03 Preference Optimization transport — resolved

`GET /personalization` and `PATCH /personalization` expose only ranking mode,
effective mode, strength, fallback, active policy ID, revision, and bounds.
Revision is the global active-settings snapshot CAS value; no `updated_at` field
is exposed. Legacy optimization administration remains a temporary supporting
HTML-only transition surface and is not a new frontend API.

### G-04 Local onboarding entry flow — resolved

`/local/readiness` uses canonical active confirmed profile predicate
(`creation_status = succeeded` and `lifecycle = active`). Legacy profile form
may retain a draft but never writes `profile_configured`; malformed legacy
onboarding is ignored for readiness. Only canonical catalog/provider/config
dependency failures return actionable `503 local_readiness_unavailable`. New
frontend profile creation uses Candidate Profile creation-attempt APIs.

## Verification

Focused proposed specs were independently reviewed, then backend contracts for
G-02, G-03, and G-04 were implemented and directly verified. G-01 remains
client-owned by design; no persistent notification infrastructure was added.

- `tests/test_fitcv_cp/test_app.py`: CV preview and personalization boundary tests pass.
- `tests/test_fitcv_cp/test_sqlite_store.py`: immutable preview, checksum, pending, and missing-state tests pass.
- `tests/test_fitcv_cp/test_local_routes.py`: canonical profile readiness, legacy-flag rejection, and malformed-state tests pass.
- Focused corrective suite: `635 passed` (`pytest tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_local_routes.py tests/test_fitcv_cp/test_sqlite_store.py`).
- `python -m compileall -q src`: passed; `git diff --check`: passed.

## Stop Point

Reconciliation remains closed as historical evidence. The active parent
specification owns durable frontend behavior and the proposed vertical-slice
plan owns implementation tasks. This note does not grant UX Freeze authority,
activate the production plan, or authorize frontend/backend implementation.
Delete this note only after its mapping and verification evidence are absorbed
by current owners and no active consumer remains.
