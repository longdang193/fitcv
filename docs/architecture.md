---
doc_id: architecture
doc_type: architecture-guide
explains:
  features:
    - cv_system
    - inspection_debugging
    - settings_system
    - trigger_run_management
  components:
    - src/fitcv
    - src/fitcv_cp
---

# Architecture

FitCV architecture has four cross-cutting layers:

1. control plane (`src/fitcv_cp`)
2. pipeline runtime (`src/fitcv`)
3. backend/provider adapters and runtime routing
4. managed architecture metadata + generated contract outputs

## Runtime Surfaces

### Control Plane

Owns trigger/lifecycle APIs, admin UI, run-detail inspection, settings surfaces, orchestration binding, and run/event persistence adapters.

Settings-specific boundary:

- `src/fitcv_cp/settings_schema.py` owns settings field metadata, IA metadata, registry membership, and settings-page contract assembly.
- `src/fitcv_cp/app.py` keeps `create_app(...)`, route decorators, and boundary wiring; `src/fitcv_cp/app_run_support.py` now holds extracted review/export helper shaping so page grouping/filter behavior stays schema-driven rather than app-local.

### Pipeline Runtime

Owns stage execution, ranking and CV lanes, validation, artifact emission, and stage-level truth.

CV-analysis ownership boundary:

- `src/fitcv/agentic_cv_analysis.py::analyze_ranked_job` owns per-job CV-analysis meaning and canonical `CvAnalysisRecord` output.
- `src/fitcv/pipeline.py` owns batch ordering, reuse-candidate lookup, persistence, observations, and downstream projection only.
- runtime adapters may change provider or orchestration mechanics, but not status semantics, evidence summary shape, gap meaning, or readiness output.
LLM runtime spine ownership:

- `src/fitcv/llm_runtime.py` owns routed adapter execution, wire compatibility, normalized operational failures, runtime provenance, and the only persistable `llm_runtime_evidence_v1` projection for enrichment, ranking, and CV generation.
- stage modules own prompt meaning, parsing, structural validation, semantic fallback, output/failure policy, and ordered observation scope. Only actual runtime calls emit evidence; reuse, replay, resume, blocked, and skipped paths do not.
- `src/fitcv/runtime_routing.py` plus `config/runtime/control_plane.yaml` remain provider/model/credential routing SSOT; stage modules do not own HTTP clients or route tables.

Location/language eligibility ownership:

- `config/policy/eligibility.yaml` is the sole mutable policy owner for location and language factor modes and absolute normalization values.
- `src/fitcv/ingest.py` preserves provider-native geography as `source_location`; `src/fitcv/normalize.py` carries that evidence without geocoding or confusing it with `location_type` work mode.
- `src/fitcv/enrich.py` owns versioned canonical `actual_location` and `language_requirements` facts. Language requirements remain separate from canonical skills.
- `src/fitcv/fit_factors.py` owns one symmetric factor algebra: candidate adaptation, evaluation truth, absolute normalization, policy projection, and policy fingerprinting.
- `src/fitcv/rule_filter.py` owns eligibility projection. Only confirmed failures under `gate_required` reject; unknown and not-applicable facts remain eligible with diagnostics.
- ranking consumes the same location/language projections without redefining their normalization or hard-gate behavior.

Ranking-v2 ownership:

- `config/policy/ranking.yaml` is the sole mutable owner of ranking policy versions, baseline weights, six structured-factor weights, declared-preference component weights, absolute missing-value defaults, and fit-label thresholds.
- `src/fitcv/ranking_contract.py` owns exact policy validation, effective location/language weight projection, normalized factor records, `structured_fit`, `baseline_fit`, deterministic `baseline_fit_label`, total ordering, compatibility adapters, and `ranking_contract_fingerprint`.
- production mode is `holistic_ai_only`: `holistic_ai_fit` determines `baseline_fit`; structured factors remain versioned diagnostics until a later approved mode changes policy.
- ranking order is `baseline_fit DESC`, `raw_job_fingerprint ASC`, then `job_url ASC`. Vector evidence never enters baseline score, label, fingerprint, or tie-breaks.
- canonical writes use `baseline_fit`, `baseline_fit_label`, and `baseline_rank`. `final_score`, `fit_label`, and `final_rank` exist only at explicit legacy read/export boundaries.
- ranking owns baseline labels. CV analysis consumes persisted `baseline_fit_label`, or derives from persisted `baseline_fit` using the same policy thresholds when the label is absent.

Preference-learning and runtime-policy ownership:

- `config/policy/decision_learning.yaml` owns the exact `decision-learning-v2` optimizer block while preserving the Phase 5 rating-scale and compiler versions.
- `src/fitcv/inverse_optimization.py` replays complete immutable episode evidence through the existing compiler, learns one bounded embedding-space residual with optional CVXPY + CLARABEL, independently validates plain numeric outputs, and evaluates by held-out episode.
- `scripts/run_inverse_optimization.py` is the standard-library JSON boundary for pure `train`/`evaluate` plus store-backed `candidate`, `reject`, `activate`, `rollback`, and `inspect` commands.
- SQLite tables `inverse_training_runs`, `ranking_policy_snapshots`, and `policy_activation_events` form one immutable lifecycle registry. Training and candidate insertion is atomic; lifecycle transitions use short `BEGIN IMMEDIATE` transactions and append audit events in the same commit.
- Candidate solving and held-out evaluation run outside the writer transaction. Content-addressed IDs make exact retries idempotent; evidence, parent, config, and runtime identities are rechecked before persistence or activation.
- Pipeline resolves one compatible active snapshot through an injected resolver, checkpoints the exact payload, and reuses it on resume. Missing, invalid, incompatible, or unavailable storage produces a visible zero-residual status for the entire run.
- Runtime order uses `personalized_rank_score = baseline_fit + learned_alpha * dot(preference_vector, normalized_embedding)`. Display clipping never controls order. Baseline score, global baseline rank, `strong | stretch | skip`, CV eligibility, and generation gates remain baseline-derived.

Shortlist ownership:

- `src/fitcv/vector_search.py` owns one deterministic `vector_cosine_v1` retrieval order over eligible jobs with valid candidate/job embeddings.
- production shortlist rows contain real cosine evidence only; missing or invalid embeddings reduce coverage instead of creating synthetic rows.
- below-cutoff audit rows exist only in the versioned shortlist stage artifact. They never enter checkpoints, shortlist persistence, AI scoring, ranking, exports, or fit labels.
- full-run and continuation paths share the same production row contract; continuation preserves prior completed stage artifacts without persisting audit rows in checkpoint state.

## Portability and Routing

- backend portability: sqlite execution path is selected through control-plane backend runtime resolution
- provider portability: model routing is owned by `config/runtime/control_plane.yaml` and resolved by the internal LLM runtime
- secrets: runtime credentials are supplied via environment variables

## Orchestration and Observability

- queue orchestration is supported by default with persisted run/orchestration bindings
- structured run events and stage artifacts back operator inspection flows
- stage-transition artifacts use pipeline schema `stage_transition_artifacts_v8`; checkpoint schema remains v1 with centralized legacy ranking adaptation
- operator-facing exports are primary inspection evidence surfaces
- CV analysis and generation share the `stage_execution_trace` family; `cv-generation-trace.json` is canonical, while the legacy trace route remains read-only compatibility

## Related Docs

- [setup.md](setup.md)
- [configuration.md](configuration.md)
- [pipeline.md](pipeline.md)
- [component_boundaries.md](component_boundaries.md)


## Patch Notes

- checkpoint resume now prefers explicit completed-stage checkpoint metadata over payload-shape inference when available
- CV-generation env overrides now resolve from one route owner
- role-taxonomy neighbor scoring now uses configured runtime taxonomy consistently across ranking/evidence, including run-scoped overlay parity
- embedding reuse now treats fallback-capable provider mode as non-reusable by default
- sqlite helper consolidation landed for local path wrappers; remaining cleanup focuses on deleting stale compatibility residue rather than preserving alternate backend paths
- large cleanup refactors such as pipeline-stage-runner adoption and reuse-engine deletion remain deferred; current characterization shows these modules are not imported by active `src/` or `tests/` surfaces




## Decision Feedback Spine

Completed runs now emit `results_job_ledger_v4` with one immutable `decision_feedback_source_v1`. Production scoring rows carry normalized embedding evidence through one URL-boundary adapter, then use `raw_job_fingerprint` as alternative identity. The control plane materializes one canonical episode and complete alternative set on first rating, appends immutable rating events in SQLite sequence order, and derives effective `unrated | 1..5` state through one shared reducer. Phase 5 compiles complete event snapshots into deterministic weighted preference edges with provenance and diagnostics; no edge is persisted or consumed by ranking. GET remains read-only; old v3 runs remain explicitly unrated.

`src/fitcv_cp/optimization_service.py` now owns store-backed candidate creation for both CLI and HTTP adapters. `/admin/optimization` reads the typed request and lifecycle rows through `ControlPlaneStore`, derives its read-only Rating Evidence preview with the shared rating-event reducer, renders bounded newest-first evidence and history, and exposes native manual candidate, activation, rejection, and rollback forms. Candidate creation never activates automatically; SQLite lifecycle transactions remain policy truth.
