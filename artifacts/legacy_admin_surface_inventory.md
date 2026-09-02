# Legacy `/admin/*` Compatibility Surface Inventory

- **Task:** Stage 14 Task 5
- **Date:** 2026-09-02
- **Scope:** Read-only inventory. New `/app` remains authoritative. No source, config, tests, Git state, DB, provider, router, Redis/RQ, or frontend changes made.
- **Evidence sources:** `src/fitcv_cp/app.py`, `src/fitcv_cp/templates/`, `frontend/src/`, route decorators and static/template references as present in working tree.

## Authority and coexistence conclusion

`/app` is registered as the SPA entry and catch-all at `src/fitcv_cp/app.py:15473-15498`; assets mount at `/app/assets`. Root `/` redirects to `/app` at `src/fitcv_cp/app.py:7303-7305`. Legacy `/admin/*` remains registered in the same application and serves server-rendered compatibility pages, redirects, action handlers, and exports. Disposition: **retain read-only inventory; preserve compatibility behavior; do not promote `/admin/*` to authority; route new work through `/app` and its shared non-admin APIs.**

## Registered legacy routes

Source: `src/fitcv_cp/app.py` route decorators.

### HTML pages and compatibility redirects

| Method | Route | Evidence | Template/disposition |
|---|---|---|---|
| GET | `/admin/api-providers` | `app.py:7804` | `api_providers.html`; compatibility page, retain |
| GET | `/admin/api-providers/{provider_id}` | `app.py:7818` | `api_provider_detail.html`; compatibility page, retain |
| GET | `/admin/llm-configuration` | `app.py:7829` | `llm_configuration.html`; compatibility page, retain |
| GET | `/admin/prompt-management` | `app.py:7843-7845` | 308 redirect to `/admin/settings/prompt-management`; retain redirect |
| GET | `/admin/system` | `app.py:7847` | `system.html`; compatibility page, retain |
| GET | `/admin/settings` | `app.py:12136` | `settings.html`; compatibility page, retain |
| GET | `/admin/settings/{section}` | `app.py:12146` | `prompt_management.html` or `settings.html`; retain |
| GET | `/admin/scans` | `app.py:12728` | `scans_list.html`; retain |
| GET | `/admin/scans/{scan_id}` | `app.py:12817` | `scan_detail.html`; retain |
| GET | `/admin/runs` | `app.py:12899` | `runs_list.html`; retain |
| GET | `/admin/runs/{run_id}` | `app.py:13769` | `run_detail.html`; retain |
| GET | `/admin/runs/{run_id}/review-queue` | `app.py:13994` | `review_queue.html`; retain |
| GET | `/admin/candidate-profiles` | `app.py:12967` | `candidate_profiles.html`; retain |
| GET | `/admin/candidate-profiles/create` | `app.py:13034` | `candidate_profile_creation.html`; retain |
| GET | `/admin/candidate-profiles/create/{attempt_id}/baseline` | `app.py:13085` | `candidate_profile_sections.html`; retain |
| GET | `/admin/candidate-profiles/create/{attempt_id}/derived` | `app.py:13092` | `candidate_profile_sections.html`; retain |
| GET | `/admin/candidate-profiles/create/{attempt_id}/confirm` | `app.py:13099` | `candidate_profile_creation.html`; retain |
| GET | `/admin/candidate-profiles/{profile_id}` | `app.py:13130` | `candidate_profile_detail.html`; retain |
| GET | `/admin/synonyms` | `app.py:13161` | `synonyms.html`; retain |
| GET | `/admin/bookmarks` | `app.py:13990` | `bookmarks.html`; retain |

### Mutating compatibility actions

| Method | Route | Evidence | Disposition |
|---|---|---|---|
| POST | `/admin/upload-trigger` | `app.py:9865` | Retain compatibility upload entry; `/app` authority |
| POST | `/admin/settings/{key}` | `app.py:12168` | Retain legacy settings action; shared state/API risk |
| POST | `/admin/settings/group/{group_name}` | `app.py:12218` | Retain legacy settings action; shared state/API risk |
| POST | `/admin/settings/section/{section_name}` | `app.py:12297` | Retain legacy settings action; shared state/API risk |
| POST | `/admin/runs/bulk/cancel` | `app.py:13263` | Retain; destructive action requires compatibility safety |
| POST | `/admin/runs/bulk/archive` | `app.py:13339` | Retain; shared run state |
| POST | `/admin/runs/bulk/unarchive` | `app.py:13383` | Retain; shared run state |
| POST | `/admin/runs/{run_id}/continue` | `app.py:13427` | Retain; orchestration coexistence risk |
| POST | `/admin/runs/{run_id}/retry` | `app.py:13559` | Retain; orchestration coexistence risk |
| POST | `/admin/runs/{run_id}/archive` | `app.py:13698` | Retain; shared run state |
| POST | `/admin/runs/{run_id}/repair-cancellation` | `app.py:13720` | Retain; orchestration/state repair risk |
| POST | `/admin/runs/{run_id}/stop` | `app.py:13164` | Retain; orchestration/state risk |
| POST | `/admin/runs/{run_id}/unarchive` | `app.py:13751` | Retain; shared run state |
| POST | `/admin/reconciler/run-attempts` | `app.py:13977` | Retain compatibility operation; orchestration risk |
| POST | `/admin/runs/{run_id}/cv-review-action` | `app.py:14016` | Retain; review state can diverge if duplicated in UI |
| POST | `/admin/runs/{run_id}/cv-review-batch-action` | `app.py:14286` | Retain; review state can diverge if duplicated in UI |
| POST | `/admin/settings/{key}` | `app.py:12168` | Retain; listed once above |
| POST | `/admin/runs/{run_id}/decision-feedback/{alternative_id}` | `app.py:14678` | Retain; feedback state shared with `/app` |

### Export, diagnostics, and artifact routes

| Method | Route | Evidence | Disposition |
|---|---|---|---|
| GET | `/admin/diagnostics/orchestration-schema` | `app.py:8271` | Retain diagnostic compatibility endpoint |
| GET | `/admin/process-events.json` | `app.py:11720` | Retain export; shared process observability |
| GET | `/admin/synonyms/global.yaml` | `app.py:14648` | Retain export |
| GET | `/admin/synonyms/global-domain.yaml` | `app.py:14658` | Retain export |
| GET | `/admin/synonyms/global-role-family.yaml` | `app.py:14668` | Retain export |
| GET | `/admin/cvs/{version_id}/download` | `app.py:14920` | Retain download compatibility |
| GET | `/admin/runs/{run_id}/export.json` | `app.py:14931` | Retain export |
| GET | `/admin/runs/{run_id}/hitl-review-audit.json` | `app.py:14954` | Retain audit export |
| GET | `/admin/runs/{run_id}/cv-debug.json` | `app.py:14972` | Retain diagnostic export |
| GET | `/admin/runs/{run_id}/cv-generation-review-required.json` | `app.py:14991` | Retain export |
| GET | `/admin/runs/{run_id}/agentic-live-trace.json` | `app.py:15034` | Retain diagnostic export |
| GET | `/admin/runs/{run_id}/approved-synonym-proposals.yaml` | `app.py:14629` | Retain export |
| GET | `/admin/runs/{run_id}/cv-generation-trace.json` | `app.py:15030` | Retain diagnostic export |
| GET | `/admin/runs/{run_id}/cv-analysis-trace.json` | `app.py:15038` | Retain diagnostic export |
| GET | `/admin/runs/{run_id}/stage-artifacts.json` | `app.py:15062` | Retain export |
| GET | `/admin/runs/{run_id}/stage-artifacts/{stage_id}.json` | `app.py:15079` | Retain export |
| GET | `/admin/runs/{run_id}/artifacts.zip` | `app.py:15093` | Retain bundle download |
| GET | `/admin/runs/{run_id}/settings-used.json` | `app.py:15172` | Retain export |
| GET | `/admin/runs/{run_id}/mapping-suggestions.json` | `app.py:15191` | Retain export |
| GET | `/admin/runs/{run_id}/synonym-proposals.json` | `app.py:15213` | Retain export |
| GET | `/admin/runs/{run_id}/synonym-proposals-trace.json` | `app.py:15235` | Retain diagnostic export |
| GET | `/admin/runs/{run_id}/synonym-suppression-diff.json` | `app.py:15256` | Retain diagnostic export |
| GET | `/admin/mapping-suggestions.json` | `app.py:15275` | Retain aggregate export |
| GET | `/admin/synonym-proposals.json` | `app.py:15289` | Retain aggregate export |
| GET | `/admin/runs/{run_id}/tabs/enriched` | `app.py:14756` | Retain tab compatibility |
| GET | `/admin/runs/{run_id}/enriched/export-filtered.zip` | `app.py:14789` | Retain export |
| GET | `/admin/runs/{run_id}/tabs/jobs-input` | `app.py:14892` | Retain tab compatibility |
| GET | `/admin/runs/{run_id}/tabs/profile` | `app.py:14904` | Retain tab compatibility |

**Registered route count:** 65 unique route patterns under `/admin/*`, matching 65 decorator declarations found in `src/fitcv_cp/app.py`.

## Legacy templates and navigation

`src/fitcv_cp/templates/base.html:776-799` defines legacy navigation links to `/admin/settings`, `/admin/runs`, `/admin/scans`, `/admin/candidate-profiles`, `/admin/bookmarks`, `/admin/synonyms`, `/admin/api-providers`, `/admin/llm-configuration`, and `/admin/system`. Additional `/admin/*` references occur in `run_detail.html`, `_cv_review_queue.html`, `_jobs_input_sources.html`, `_process_console.html`, and `synonyms.html`.

Template files served by registered legacy pages:

- `api_providers.html`, `api_provider_detail.html`, `llm_configuration.html`, `system.html`
- `settings.html`, `prompt_management.html`, `scans_list.html`, `scan_detail.html`
- `runs_list.html`, `run_detail.html`, `review_queue.html`
- `candidate_profiles.html`, `candidate_profile_creation.html`, `candidate_profile_sections.html`, `candidate_profile_detail.html`
- `synonyms.html`, `bookmarks.html`
- Partials: `_cv_review_queue.html`, `_jobs_input_sources.html`, `_process_console.html`, `_run_detail_snapshot_tab.html`

Disposition: keep templates available for compatibility; do not extend their navigation as new product surface.

## Shared API surfaces used alongside legacy pages

The legacy templates call non-admin APIs, so `/admin/*` and `/app` can mutate/read same state through shared endpoints. Registered shared API groups in `src/fitcv_cp/app.py` include:

- Provider/config: `/api-providers*`, `/llm-configuration`, `/prompt-configurations*`, `/system-settings`
- Runs/scans: `/runs*`, `/scans*`, `/tracked-companies*`
- Candidate profiles: `/candidate-profile-field-schema`, `/candidate-profile-creation-attempts*`, `/candidate-profiles*`
- Synonyms: `/synonym-policies*`, `/synonym-suggestions*`, `/synonym-processing-runs`, `/synonym-backups/*`
- Bookmarks/jobs/CV: `/bookmarks*`, `/runs/{run_id}/jobs*`, `/cv-versions*`
- Settings/operations: `/settings*`, `/settings/pipeline*`, `/personalization/optimization*`, `/healthz`

The `/app` frontend has route and API clients under `frontend/src/app/route-registry.ts`, `frontend/src/lib/api-client.ts`, and feature API modules under `frontend/src/features/*/api.ts`.

## Representative coexistence risks

1. **Dual navigation:** legacy `base.html` still makes `/admin/*` look primary while `/` now redirects to `/app`; users can enter two UI surfaces.
2. **Shared mutable state:** legacy POST handlers and `/app` API actions target same runs, settings, candidate profiles, synonyms, bookmarks, and provider configuration. Concurrent edits can produce stale-page overwrites or confusing status.
3. **Duplicate orchestration controls:** `/admin/runs/{run_id}/continue`, `retry`, `stop`, `repair-cancellation`, bulk cancel/archive, and reconciler actions coexist with `/app` run actions. Repeated clicks or cross-surface operations can race.
4. **Review divergence:** legacy CV review forms in `_cv_review_queue.html` coexist with `/app` CV review flows; stale review decisions or duplicate submissions need idempotency/conflict handling.
5. **Export consistency:** legacy JSON/YAML/ZIP exports and `/app` download paths can expose different timing or snapshots if state changes between page load and export.
6. **Template/API drift:** legacy templates depend on shared API response shapes. API contract changes for `/app` can break compatibility pages even when `/admin/*` route code is untouched.
7. **Diagnostics leakage:** process and orchestration diagnostic endpoints remain directly reachable under `/admin/*`; keep intended local/operator access boundaries unchanged.

## Disposition

- **PASS — inventory complete.** `/app` remains registered authoritative entry; legacy `/admin/*` compatibility routes remain identified and unchanged.
- Keep all listed routes/templates/APIs for compatibility until explicit retirement task.
- Do not add new behavior to legacy templates or make `/admin/*` authoritative.
- Future retirement requires route-level usage evidence, redirect/404 plan, API consumer audit, and fresh browser/backend verification.


