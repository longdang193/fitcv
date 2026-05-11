# Docs Lifecycle Drift Audit — 2026-05-11

Scope:
- `docs/api.md`
- `docs/architecture.md`
- `docs/component_boundaries.md`
- `docs/configuration.md`
- `docs/fitcv-control-plane-setup.md`
- `docs/FitCV-pipeline.md`
- `docs/observability.md`
- `docs/pipeline.md`
- `docs/setup.md`
- `docs/usage.md`

Status key:
- `accurate` = matches code/config/scripts now
- `stale` = conflicts with current implementation
- `ambiguous` = partially verifiable; wording too broad or mixed
- `unsupported` = no implementation evidence found

## 1) docs/setup.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Two runtime surfaces: `src/fitcv_cp/` and `src/fitcv/` | accurate | `src/fitcv_cp/app.py`, `src/fitcv/pipeline.py` | Keep |
| `FITCV_CP_DATA_BACKEND` controls backend mode | accurate | `src/fitcv_cp/backend_runtime.py:40`, `src/fitcv_cp/bq_store.py:43` | Keep |
| Inline execution uses `FITCV_CP_INLINE_EXECUTION=true` | unsupported | no match in `src/fitcv_cp/app.py` grep | Needs correction/removal |
| Quick validation: `/healthz` and run trigger flow | accurate | `src/fitcv_cp/app.py:4514`, `src/fitcv_cp/app.py:5004` | Keep |

## 2) docs/usage.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Entry point `/admin/runs` | accurate | `src/fitcv_cp/app.py:5439` | Keep |
| Run mode choices `Run All` / `Stage by Stage` | accurate | `src/fitcv_cp/app.py` (`RUN_MODE_LABELS`) | Keep |
| Key surfaces include `GET /healthz`, `POST /runs`, `GET /runs/{run_id}` | accurate | `src/fitcv_cp/app.py:4514`, `5004`, route block around runs endpoints | Keep |
| Lifecycle actions include cancel/continue/archive | accurate | route/state logic in `src/fitcv_cp/app.py` + store ops imports | keep but tighten wording to explicit route/actions |

## 3) docs/pipeline.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Stage order normalize→enrich→rule_filter→shortlist→ranking→cv_analysis→cv_generation | accurate | `src/fitcv/pipeline.py:189` (`PIPELINE_STAGE_SEQUENCE`) | Keep |
| Two execution modes full/manual-staged | accurate | `src/fitcv_cp/app.py` (`RUN_MODE_LABELS`) | Keep |
| Wave-1 two-layer observability ownership | ambiguous | Supported partly by observability docs/code, but doc language broader than directly verifiable code anchors in this pass | tighten to implementation-backed wording |

## 4) docs/FitCV-pipeline.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Same stage flow as pipeline summary | accurate | `src/fitcv/pipeline.py:189` | Keep |
| “Explainer, stage truth in docs/stages + docs/features + generated DAG” | accurate | repo doc structure present | Keep |
| Layer descriptions about narrowing/grounding | ambiguous | conceptually consistent; not strict API/contract claims | keep but avoid normative over-claims |

## 5) docs/configuration.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Primary runtime inputs include control_plane/runtime yaml, pipeline yaml, env | ambiguous | docs/config paths partially naming `config/runtime/*`; repo also uses other runtime config patterns | verify exact active paths before patch |
| Secrets env-only and no secret values in YAML | ambiguous | governance intent likely true; not fully proven by single code anchor | keep as policy if sourced, else soften |
| Effective settings layering includes persisted settings + trigger overrides + settings-used snapshot | accurate | settings flow surfaced in `src/fitcv_cp/app.py` and settings store wiring | Keep with clearer code anchors |

## 6) docs/fitcv-control-plane-setup.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Control-plane parts: web, worker, redis | accurate | `docker-compose.yml` services + start scripts | Keep |
| Docker mount uses `FITCV_LANGGRAPH_REPO_PATH` default `../fitcv-langgraph` | accurate | `docker-compose.yml:24,45` | Keep |
| Admin UI at `http://localhost/admin/runs` | accurate | `src/fitcv_cp/app.py:5439` | Keep |
| Trigger example body includes `config_path":".env.yaml"` | stale | needs check against current run submit expectations in app route payload model | likely update required |
| Notes reference `/app/.env.yaml` and `/app/config/env.yaml` | stale | verify actual container config usage before retaining | likely outdated |

## 7) docs/observability.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Core surfaces `/admin/runs`, `/admin/runs/{run_id}`, `GET /runs/{run_id}/events` | accurate | `src/fitcv_cp/app.py` route set, runs/events handlers | Keep |
| Outbox replay health surfaces and checker script | accurate | routes + `scripts/check_outbox_replay_health.py` | Keep |
| OTel env toggles including `FITCV_OTEL_ENABLED`, endpoint, service name | accurate | env-driven paths referenced in app/observability integration | Keep |
| Langfuse Wave 1 detailed semantics | ambiguous | broad narrative; many details likely true but needs selective tightening to concrete implemented fields/events | patch for precision |

## 8) docs/api.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Public API includes `/healthz`, `/runs`, `/runs/{run_id}`, events | accurate | `src/fitcv_cp/app.py:4514,5004,5203` and run routes | Keep |
| Operator HTML routes split from JSON API | accurate | `src/fitcv_cp/app.py` (`/admin/*` + JSON handlers) | Keep |
| Some endpoint payload examples/options | ambiguous | must validate each sample against current pydantic models/handler behavior | targeted patch needed |

## 9) docs/architecture.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Four-layer architecture framing | ambiguous | high-level model consistent but not strictly enforced in single code contract | keep as conceptual framing, reduce hard-contract tone |
| Validation path references generated/validator flow | accurate | repo scripts and governance model exist | Keep |

## 10) docs/component_boundaries.md

| Claim | Status | Evidence | Note |
|---|---|---|---|
| Ownership boundaries between `fitcv` pipeline runtime and `fitcv_cp` control-plane | accurate | module structure and imports in `src/fitcv_cp/app.py` | Keep |
| Phase-2 scaling boundary specifics | ambiguous | mostly design/intent language; ensure not phrased as shipped guarantees where unverified | tighten wording |

---

## High-priority drift fixes for Task 2

1. Remove or correct `FITCV_CP_INLINE_EXECUTION` claim in `docs/setup.md` (unsupported).
2. Re-verify and patch `docs/fitcv-control-plane-setup.md` stale config-path/container-path examples.
3. Validate endpoint payload samples in `docs/api.md` against current request models/handlers.
4. Tighten ambiguous normative language in `architecture.md`, `pipeline.md`, `observability.md`, `component_boundaries.md` to implementation-backed wording.

## Blockers / Follow-up evidence needed

- Need targeted view of current run trigger request model and config-path handling in `src/fitcv_cp/app.py` around `/runs` POST handler.
- Need targeted view of container/runtime config path resolution to finalize setup doc command examples.
