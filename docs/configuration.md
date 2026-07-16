---
doc_id: configuration
doc_type: operator-guide
explains:
  features:
    - cv_system
    - settings_system
    - trigger_run_management
  configs:
    - .env
    - config/policy/eligibility.yaml
    - config/runtime/control_plane.yaml
    - config/runtime/pipeline.yaml
---

# Configuration

FitCV uses layered configuration with clear ownership boundaries.

## Primary Runtime Inputs

- FitCV Local packaged defaults plus user-owned local routing overlay
- trigger base config file (`config_path` in `/runs` request; default `.env.yaml`)
- persisted control-plane settings (`/admin/settings` and `/settings` surfaces)
- per-run trigger overrides (`config_overrides` in `/runs`)
- process environment variables for backend/provider credentials and runtime toggles

## FitCV Local Configuration Ownership

FitCV Local keeps application defaults read-only and user configuration narrow:

| Surface | Owner | Secret |
| --- | --- | --- |
| `%APPDATA%\FitCV\bootstrap.json` | selected data-root pointer and minimal version metadata | no |
| `<data-root>\candidate_profile.yaml` | user candidate profile | private user data, not credential |
| `<data-root>\config\local_routing_overlay.yaml` | provider definition and `model_routing.parts` overrides | no |
| Windows Credential Manager service `FitCV.Local` | provider API keys | yes |
| packaged `config/runtime/control_plane.yaml` | immutable provider/model defaults | no |

Local overlay may set provider type, display name, API root, auth mode, wire API,
timeout, default model, and supported task model routes. It cannot replace full
control-plane config or pipeline/policy files.

Onboarding accepts `openai`, `openai_compatible`, and `9router` provider IDs.
API root must be absolute HTTP(S), contain no embedded credential/query/fragment,
and point to API root rather than `/responses`, `/chat/completions`, or `/models`.
Supported wire APIs are `responses` and `chat_completions`.

## Canonical Ownership Matrix (Option B Baseline)

This matrix defines current SSOT ownership for migration execution.

| Config surface | Canonical ownership | Notes |
| --- | --- | --- |
| `config/runtime/control_plane.yaml` | control-plane backend/provider/model routing defaults | Includes `control_plane.data_backend.*`, `control_plane.providers.*`, `control_plane.model_routing.*`, feature flags, observability toggles. |
| `config/runtime/pipeline.yaml` | pipeline execution knobs | Owns enrichment/rerank timing, Top-N controls, `pipeline.shortlist_audit_sample_n`, lifecycle limits, replay health thresholds, and model defaults used by runtime pipeline stages. |
| `config/policy/cv.yaml` | CV generation and validation policy | Owns nested `cv.*` contract (`preset`, composition, validation, generation defaults). |
| `config/policy/eligibility.yaml` | location/language eligibility policy | Sole mutable owner of factor modes and absolute normalization values; ranking/runtime/env config may not shadow `eligibility_policy`. |
| `config/policy/ranking.yaml` | ranking-v2 baseline policy | Sole mutable owner of exact ranking policy, absolute defaults, fixed weights, label thresholds, active baseline mode, and label-migration gate. |
| `config/policy/decision_learning.yaml` | decision-learning policy | Sole owner of ordinal 1–5 application-interest labels, compiler policy, latent-residual optimizer/evaluation policy, and Phase 7 activation threshold/version. Not exposed as a runtime setting. |
| `config/taxonomy/taxonomy.yaml` | shared business taxonomy and enum families | Owns seniority taxonomy, location/contract/experience enums, role taxonomy maps. |
| `.env.yaml` | bootstrap trigger input | Current default `config_path`; now limited to small bootstrap-only values. |
| `config/env.private.yaml` | no active canonical owner in this worktree | File not present in tracked worktree; treat as deprecated/removed unless explicitly reintroduced as local-only untracked override. |

### Legacy-Duplicate Classification (Current Baseline)

- compatibility-only (to be drained from `.env.yaml`): `seniority_ladder`, `application_statuses`, `cv_analysis_min_score`, overlap with runtime knobs that already live in `config/runtime/pipeline.yaml`
- removable private surface: `config/env.private.yaml` (no active tracked consumer in this worktree baseline)
- removable smoke surface: `config/live_smoke.yaml` (duplicates infra/model ownership outside canonical runtime files)
- retired shortlist surfaces: `config/shortlist_lexical.yaml`, top-level `shortlist_lexical`, and top-level `retrieval_strategy`; config loading rejects them rather than silently preserving dormant BM25/BM25F behavior

### Task 1 Ownership And Disposition Decisions

| Candidate | Canonical owner | Decision | Consumer evidence |
| --- | --- | --- | --- |
| `cv_acceptance_policy` | `config/policy/cv.yaml` | keep policy with other CV rules; remove bootstrap ownership | `src/fitcv/pipeline.py` + `src/fitcv/config.py:get_cv_acceptance_policy` |
| `max_cv_jobs`, `cv_analysis_min_score`, `required_skill_overlap_min`, `preferred_skill_overlap_min`, `language_match_min`, `summary_quality_min` in `.env.yaml` | `config/runtime/pipeline.yaml` | drain from `env.yaml`; keep compatibility mapping only where active runtime still needs bridge | overlap warnings and compatibility projection in `src/fitcv/config.py` |
| `seniority_ladder` in `.env.yaml` | `config/taxonomy/taxonomy.yaml` | keep temporary compatibility-only bridge; block expansion | consumer in `src/fitcv/rule_filter.py` |
| `application_statuses` in `.env.yaml` | `config/taxonomy/taxonomy.yaml` | keep temporary compatibility-only bridge; block expansion | consumer in `src/fitcv/tracker.py` |
| `control_plane.model_routing.parts.cv_analysis_semantic_alignment` | none (no active runtime consumer) | remove key from `config/runtime/control_plane.yaml` | no source consumer found; only config declaration present |
| `config/live_smoke.yaml` | none (retired in Razor+SSOT lane) | delete file; no runtime dependency allowed | current file duplicates infra/model keys and increases ownership ambiguity |
| `config/env.private.yaml` | none (not tracked) | classify as deprecated local-only override; do not add tracked runtime dependency | file missing in tracked worktree baseline |

### CV Acceptance Strictness Policy (Option B)

Canonical policy owner in this lane: `config/policy/cv.yaml` key `cv_acceptance_policy`.

Policy meaning:

- `required_match.min_ratio_by_fit.<fit>`: minimum `matched_required / matchable_required_count` ratio to remain eligible for auto-accept.
- `required_match.max_missing_by_fit.<fit>`: maximum missing required items allowed for auto-accept.
- `force_review_when_any_required_missing_for_fits`: fit classes that must route to `review_required` when any required item is missing.

`review_required` semantics in this contract:

- non-fatal HITL branch
- generation/validation output can exist
- auto-accept is blocked by policy and requires operator decision (accept/reject/edit)
- hard-failure statuses remain reserved for `validation_failed`, `generation_failed`, `persistence_failed`

### Location And Language Eligibility Policy

Canonical policy owner: `config/policy/eligibility.yaml` key `eligibility_policy`.

- `policy_version` versions the validated policy contract.
- each factor uses the same `disabled | ranking_only | gate_required` mode set.
- normalization values are globally stable absolute values, not run-cohort statistics.
- environment variables, trigger overrides, ranking config, and other policy files may not define a second `eligibility_policy` owner.
- runtime validates the exact shape and fingerprints the validated mapping with deterministic canonical JSON.
- `gate_required` rejects only confirmed factor failures; unknown and not-applicable states remain eligible.
- ranking-v2 consumes emitted `ranking_value` fields without redefining normalization; `gate_required` and `disabled` factors are excluded once from effective structured weights.

### Ranking-V2 Baseline Policy

Canonical policy owner: `config/policy/ranking.yaml` key `ranking_policy`.

- exact policy version: `ranking-v2`
- absolute normalizer version: `absolute-fit-v1`
- sole production mode: `holistic_ai_only`
- baseline inputs: `holistic_ai_fit` and diagnostic `structured_fit`
- structured factors: `must_have_match`, `title_relevance`, `seniority_fit`, `declared_preference_fit`, `location_fit`, `language_fit`
- declared preference components: `domain`, `role_family`, `work_mode`
- globally stable missing-value defaults and fit-label thresholds are policy-owned; runtime code has no numeric fallback owner
- config loading rejects missing, unknown, retired, non-finite, out-of-range, invalid-sum, or unsupported policy values
- top-level `ranking_weights`, `preference_fit_weights`, and `fit_label_thresholds` are retired settings surfaces, not semantic migration inputs
- Phase 3 baseline weights remain fixed and config-only at `holistic_ai_fit: 1.0` and `structured_fit: 0.0`; admin settings expose canonical structured-factor and declared-preference weights only

### Planned Deprecation Boundaries

1. `.env.yaml` remains accepted as trigger default during transition, but ownership must stay bootstrap-only.
2. `config/env.private.yaml` is treated as deprecated in tracked repo state; no new runtime dependency may be introduced.
3. Scripts/tests/control-plane UI should not restore removed bootstrap owners.

### Legacy Removal Gates

Remove legacy compatibility behavior only when all gates pass:

1. reference gate:
   - repo scan shows no required runtime entrypoint depends on removed legacy key/path shape
   - command: `rg -n "\\.env\\.yaml|config/env\\.yaml|seniority_ladder|application_statuses" src scripts tests docs -S`
2. parity gate:
   - bootstrap `.env.yaml` and canonical policy/runtime files produce agreed projections in tests
   - command: `pytest tests/test_config.py -q`
3. contract gate:
   - repo contract checks pass after any deprecation-path removal patch
   - command: `python scripts/hooks/run_validator.py --fast`

## Config Invariants

- secrets are env-only
- no secret values in YAML
- no secret key-name indirection in YAML
- `settings-used.json` is the run-time evidence snapshot

## Effective Settings Resolution

At trigger time, the control plane composes effective run settings in this order:

1. load base config from `config_path` (`TriggerRequest.config_path`)
2. load persisted active settings (`load_active_settings(...)`)
3. apply persisted settings into base config (`apply_settings_to_config`)
4. apply run-scoped trigger overrides (`config_overrides`) after validation/coercion
5. recompute derived compatibility fields
6. persist the run-scoped snapshot as `settings-used.json`/effective settings payload

Interpretation rules:

- `/admin/settings` edits persisted defaults for future runs only.
- trigger-time per-run overrides do not mutate saved defaults.
- completed-run truth belongs to the run-scoped effective settings snapshot.
- process environment variables control backend/provider credentials and runtime wiring; they are not persisted through settings-save routes.

## Settings Surface Ownership

The settings page intentionally mixes editable controls with metadata-only rows.

Schema ownership rules:

- `src/fitcv_cp/settings_schema.py` is the SSOT for settings fields, IA metadata, section/filter membership, and page-contract data returned by `build_settings_page_spec()`.
- `src/fitcv_cp/app.py` adapts that schema-owned contract at render/save boundaries; it must not recreate section lists, decision tabs, or decision-domain filters with app-local literals.
- runtime schema overlays expose both `declared_default` (schema-authored default) and `baseline_default` (loaded runtime baseline); `default` currently mirrors `baseline_default` for compatibility with existing consumers.

- editable: schema-backed controls with persistence keys and save handlers
- metadata-only: fixed/runtime-owned values shown for operator context and provenance
- hidden-deprecated: compatibility keys intentionally removed from operator UI and rejected by settings-save routes (`422`) to prevent false runtime authority signals
- compatibility-readonly: legacy alias keys shown for migration visibility but rendered non-editable; canonical runtime throughput keys remain single editable authority

Examples:

- editable: retrieval funnel sizes, ranking weights, timing, run lifecycle guard, CV composition toggles
- metadata-only: fixed runtime-contract fields such as single-option model metadata
- hidden-deprecated: legacy AI-authority controls (for example `cv_generation_model`) retained only for compatibility projection, not operator control
- compatibility-readonly: runtime throughput legacy aliases mapped to canonical `stage_runtime.*` keys
- canonical-save-path: settings-save routes persist canonical `stage_runtime.*` throughput keys and ignore compatibility alias inputs in timing-section writes
- effective-concurrency-contract: `configured_concurrency` is the stage cap; `*_concurrency_effective` is `min(configured_concurrency, runnable_work_items)` and is `0` when reuse or gating leaves no runnable work
- enrich-pacing-contract: enrich work items are batches, so effective concurrency is capped by `ceil(fresh_jobs / batch_size)`; shared request-start pacing still limits aggregate request rate
- ranking-pacing-contract: ranking work items are fresh AI-score rows; the submit loop still sleeps `stage_runtime.ranking.sleep_secs` between submissions, so provider timestamps can look sequential when sleep is positive
- cv-analysis-pacing-contract: CV analysis runs ranked-job work concurrently up to `stage_runtime.cv_analysis.concurrency` while preserving input order
- cv-generation-pacing-contract: CV generation runs generation-ready rows concurrently up to `stage_runtime.cv_generation.concurrency`, preserves input order, and applies `stage_runtime.cv_generation.sleep_secs` between provider-call submissions

### LLM Runtime Contract

- no persisted mode toggle selects late-stage CV semantics
- `src/fitcv/llm_runtime.py` is the sole generative provider transport and normalized failure owner
- stage code owns prompts, parsers, validators, acceptance, and persistence meaning without alternate runtime paths
- active routes are `enrich_extraction`, `ranking_ai_score`, `cv_generation_structured_write`, and `synonym_triage_recommendation`
- `cv.agentic_late_stage.enabled` is retired from the active settings schema; stale persisted rows are pruned, not projected into current settings

## Backend and Provider Routing

- control-plane runtime is SQLite-only for supported startup paths
- local sqlite persistence authority:
  - pipeline run snapshots persist in sqlite (`local_pipeline_runs`)
  - pipeline run events persist in sqlite (`local_pipeline_run_events`)
  - no in-process run shadow cache is authoritative; restart survival comes from sqlite tables
- sqlite path precedence:
  1. `FITCV_CP_SQLITE_PATH`
  2. `control_plane.data_backend.sqlite.path`
  3. `data/fitcv_cp.sqlite3`
- retired split-path env:
  - `FITCV_CP_SETTINGS_SQLITE_PATH` is not supported
- model/provider routing defaults: canonical owner is `config/runtime/control_plane.yaml`
  - `control_plane.providers.*.base_url`
  - `control_plane.providers.*.wire_api`
  - `control_plane.model_routing.parts.*.provider`
  - `control_plane.model_routing.parts.*.model`
- internal runtime resolves each routing part through one provider definition; JOB operator route overrides are not accepted
- routing expectation resolves only from `config/runtime/control_plane.yaml` and fails fast when required fields are missing
- provider credential input:
  - FitCV Local: Windows Credential Manager, keyed by provider ID
  - developer/server mode: `FITCV_LLM_API_KEY`

## AI-Plane Contract (Migration Freeze)

This migration lane defines a strict split between storage backend selection and AI runtime behavior.

- `data_plane` ownership:
  - runtime control-plane SQLite path selection
  - persistence/query adapter behavior only
- `ai_plane` ownership:
  - provider + model routing via `control_plane.model_routing.parts.*`
  - AI credential contract via process env keys
  - shared adapter execution via `src/fitcv/llm_runtime.py`; enrichment, ranking, and CV generation do not own provider clients, endpoint fallback, or credential lookup

Prohibited coupling:

- backend mode must not alter AI provider selection
- backend mode must not alter AI model selection
- backend mode must not alter AI auth key resolution order

Canonical developer/server AI auth contract:

- sole repo-native input: `FITCV_LLM_API_KEY`
- no credential alias projection or second provider-client path is used

Fail-fast runtime contract:

- if routed AI provider/model cannot be resolved, runtime must fail with explicit configuration error
- if AI auth key is missing for routed HTTP provider, runtime must fail with explicit credential error
- no implicit Gemini/default model fallback is allowed as runtime authority in unified mode

FitCV Local keeps same internal LLM runtime and routing semantics. Its only auth
difference is OS credential lookup at packaged boundary; API key never enters
the non-secret routing overlay.

## Related Docs

- [setup.md](setup.md)
- [usage.md](usage.md)
- [architecture.md](architecture.md)



## Decision Feedback Policy

- `decision-learning-v1` owns one ordinal `application-interest-v1` scale.
- Stars capture personal application interest after eligibility; they do not record applications or change ranking.
- Strict SSOT mode requires `config/policy/decision_learning.yaml` and rejects environment or other-policy shadows.
- Phase 4 exposes no optimizer, learned vector, pairwise compiler, or settings control.
- Phase 5 compiler policy owns versioned minimum gaps, gap weights, and episode evidence budget; compiler output remains non-persistent and inactive.
## Offline Preference Learning

- `decision_learning_policy.policy_version` is `decision-learning-v2`; rating scale remains `application-interest-v1` and compiler remains `preference-compiler-v1`.
- `inverse_optimization` owns fixed alpha, margin, regularization, norm bound, CLARABEL iteration limit, numeric tolerances, and episode-grouped evaluation settings. No CLI numeric override or admin setting exists.
- Install local solver support with `uv run --extra inverse-optimization ...`. The shared control-plane Docker image installs the same `.[inverse-optimization]` extra for both web and worker; optimizer parameters remain config-only and are never accepted from HTTP forms.
- Activation config is exact: `activation_version: ranking-policy-lifecycle-v1` and `minimum_fold_vector_stability: 0.0`. Existing `numeric_equivalence_absolute` owns metric tolerance and vector no-op equivalence; no CLI override exists.
- Pure commands remain `train --domain <id> --input <bundle>` and `evaluate ... [--parent <path>]`. Lifecycle commands are `candidate`, `reject`, `activate`, `rollback`, and `inspect`; all emit canonical JSON and use atomic file replacement when `--output` is supplied. `/admin/optimization` adapts stored SQLite evidence into the same shared candidate operation and exposes no numeric optimizer settings.
- Exit codes are `0` for valid terminal/action results, `2` for invalid input or unknown identity, `3` for solver/dependency/storage failure, and `4` for promotion rejection, stale/conflicting lifecycle state, or incompatibility.
