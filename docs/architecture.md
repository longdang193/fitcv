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
- Phase 1 emits ranking-ready values only. Ranking weights, final score, ordering, and `strong | stretch | skip` labels remain unchanged.

## Portability and Routing

- backend portability: sqlite execution path is selected through control-plane backend runtime resolution
- provider portability: model routing is config/runtime controlled (with optional `FITCV_LANGGRAPH_*` env overrides) and resolved at runtime
- secrets: runtime credentials are supplied via environment variables

## Orchestration and Observability

- queue orchestration is supported by default with persisted run/orchestration bindings
- structured run events and stage artifacts back operator inspection flows
- operator-facing exports are primary inspection evidence surfaces
- CV analysis and generation share the `stage_execution_trace` family; `cv-generation-trace.json` is canonical, while the former agentic-live route remains read-only compatibility

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



