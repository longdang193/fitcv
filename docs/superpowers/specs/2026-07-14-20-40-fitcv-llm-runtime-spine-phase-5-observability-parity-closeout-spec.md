---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-llm-runtime-spine-phase-5-observability-parity-closeout
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md
targets:
  - src/fitcv/llm_runtime.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/pipeline.py
  - src/fitcv/pipeline_contracts.py
  - src/fitcv/pipeline_observability.py
  - src/fitcv/pipeline_stage_artifacts.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/app_run_support.py
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/worker_run_support.py
  - src/fitcv_cp/run_artifact_mirror.py
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/settings_store.py
  - docs/stages/enrich.source.yaml
  - docs/stages/ranking.source.yaml
  - docs/stages/cv_analysis.source.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/features/bounded_parallel_enrichment/feature.source.yaml
  - docs/features/pipeline_performance/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/settings_system/feature.source.yaml
  - docs/configuration.md
  - docs/api.md
  - docs/observability.md
  - docs/pipeline.md
  - docs/architecture.md
  - tests/test_llm_runtime.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_cv_generator.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_worker_job.py
  - tests/test_fitcv_cp/test_run_artifact_mirror.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_fitcv_cp/test_settings_store.py
  - tests/test_fitcv_cp/test_settings_store_sqlite.py
related_features:
  - bounded_parallel_enrichment
  - pipeline_performance
  - cv_system
  - inspection_debugging
  - settings_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

# Detailed Spec: FitCV LLM runtime spine Phase 5 observability, parity, and closeout

## Goal

Close the LLM-runtime-spine workstream without reopening stage semantics or
transport migration.

Phase 5 makes runtime evidence, failure taxonomy, stage artifacts, traces, and
adapter-parity proof follow one repo-native contract across every admissible LLM
case. It also removes current-write mode framing that still presents one
canonical late-stage flow as `agentic` versus `non_agentic` behavior.

The final architecture remains:

`StageInput -> LlmTaskRequest -> RoutedAdapter -> LlmRuntimeResult -> StageMeaning -> StageOutput -> ArtifactProjection`

Ownership remains split by meaning:

- `llm_runtime.py` owns operational request execution, normalized runtime
  failure, normalized runtime provenance, and one safe evidence projection
- each stage owns prompt meaning, parser meaning, semantic validation, status,
  retry/fallback policy, reuse, and business output
- pipeline and control-plane layers own scheduling, aggregation, persistence,
  presentation, and compatibility reads
- LangGraph remains a private runtime adapter/orchestrator only

Phase 5 is the final child detailed spec required by the master spec. There is
no Phase 6 in this remediation slice. Work outside the decisions and non-goals
below requires a separate future spec rather than an implicit continuation.

## Key Deliverables

### Deliverable 1: one canonical persisted runtime-evidence projection

`LlmRuntimeResult` remains the in-memory SSOT. `llm_runtime.py` exposes one
small, pure projection helper that converts a completed result into the only
persistable per-call runtime evidence block:

```text
llm_runtime_evidence_v1
  contract_version
  status
  provenance
    routing_part
    runtime_path
    adapter
    provider
    model
    wire_api
    attempt_count
    response_id
    trace_id
    latency_ms
  failure | null
    stage
    code
    message
    retryable
    http_status
```

The projection serializes existing canonical dataclasses. It is not a new
runtime framework, registry, envelope hierarchy, or stage service.

Projection rules:

- `status`, `provenance`, and `failure` come only from `LlmRuntimeResult`
- `failure` is null for success and present for failure
- provenance uses `routing_part`, never the CV-generation-local alias
  `route_part`
- empty optional IDs remain null rather than being synthesized
- adapter telemetry outside canonical provenance stays adapter-local unless a
  bounded debug surface explicitly includes it
- prompt text, raw response text, provider payload, base URL, headers, API-key
  values, credentials, and secrets are never persisted in this block
- stage semantic validation and business error payloads are not copied into the
  runtime block
- the runtime result constructor and runtime tests own result invariants; the
  projection helper selects safe fields and must not become a second validator

### Deliverable 2: one symmetric stage-observability frame

Every active routed LLM stage uses the same observation frame:

1. build one `LlmTaskRequest`
2. execute one adapter through `execute_llm_task`
3. project the returned `LlmRuntimeResult` through the canonical evidence helper
4. map runtime outcome into stage-owned semantics
5. emit evidence through existing debug, callback, observation, and stage-artifact
   paths

The frame applies to:

- `enrich_extraction`
- `ranking_ai_score`
- `cv_generation_structured_write`

Uniformity means same contract for every runtime invocation, not that every
stage must support every adapter or share one business failure policy.

Per-stage projection rules:

- enrich keeps its current fail/retry behavior and row shape
- ranking keeps its current per-row skip/failure-isolation behavior and row
  shape
- CV generation keeps its canonical result/status/repair/review contract and
  records one evidence block per initial or repair invocation
- reuse, replay, resume, fit-gate skip, and reranker block paths that make no LLM
  call emit zero runtime calls; they must not fabricate success provenance
- stage-transition artifacts expose one bounded runtime summary and bounded
  evidence sample, while existing item/debug observation paths may retain the
  full per-item evidence needed for diagnosis

Stage observations wrap, but do not alter, the canonical runtime block:

```text
llm_runtime_observation_v1
  scope_key
  input_index
  invocation_index
  evidence: llm_runtime_evidence_v1
```

`scope_key` uses the existing stable stage identity: `raw_job_fingerprint`
where available, otherwise the canonical `job_identity_keys` result. Mutable
destination URLs are not primary identity. `invocation_index` counts outer
`execute_llm_task` invocations for one item. Adapter-internal HTTP attempts stay
inside provenance `attempt_count`.

Bounded samples sort observations by stable `scope_key`, `input_index`, then
`invocation_index` before truncation. Concurrent callback completion order must
not change persisted sample contents.

Canonical stage-artifact runtime summary fields:

```text
llm_runtime_summary
  contract_version: llm_stage_runtime_summary_v1
  calls_total
  succeeded_total
  failed_total
  failure_counts_by_stage
  failure_counts_by_code
  adapters
  runtime_paths
  evidence_sample
```

`evidence_sample` contains only `llm_runtime_evidence_v1` blocks and follows the
existing bounded stage-artifact sampling/truncation policy. No second summary
builder may re-derive failure or provenance semantics from stage output text.

### Deliverable 3: honest CV-analysis observability

`cv_analysis` participates in the shared stage artifact and trace structure but
does not currently perform a routed LLM call. Therefore it must not emit fake
LLM provenance such as `fitcv_builtin`, `fitcv_agentic_cv_analysis_builtin`, or
`mode_source`.

CV-analysis observability keeps:

- canonical `CvAnalysisRecord` status
- evidence-selection summary
- gap and readiness summary
- stage execution attempts where useful
- canonical stage/business error summary
- decision-chain and artifact references

It omits `llm_runtime_evidence` unless a future accepted spec introduces a real
routed LLM invocation through `execute_llm_task`. This is the admissible-case
rule that preserves symmetry: real LLM calls use the runtime contract; stages
without an LLM call do not impersonate one.

### Deliverable 4: stage-neutral trace and artifact naming

Newly written late-stage traces stop using mode-owned names and schemas.

Canonical current-write names:

- per-record schema: `stage_execution_trace_record_v1`
- run schema: `stage_execution_trace_run_v1`
- trace family: `stage_execution_trace`
- CV-analysis summary key: `cv_analysis_trace`
- CV-generation summary key: `cv_generation_trace`
- CV-analysis artifact: `cv-analysis-trace.json`
- CV-generation artifact: `cv-generation-trace.json`

Current writes remove:

- `late_stage_mode`
- `agentic_late_stage_enabled`
- `agentic_status`
- `mode_source`
- `agentic_live_trace`
- `agentic-live-trace.json`
- `agentic_step_trace_record_v1`
- `agentic_step_trace_run_v1`
- `trace_family: agentic_step_trace`

Trace applicability is derived from stage participation and artifact presence:

- stage not reached: `not_applicable`
- stage reached and trace present: `present` or `degraded` from trace status
- stage reached and trace absent: `missing`

No applicability decision may depend on a semantic mode label.

Historical read compatibility is one-way:

- readers may translate persisted `agentic_live_trace` into canonical
  `cv_generation_trace`
- translation changes only the storage key and route exposure; nested historical
  schema/family values remain unchanged and truthful
- readers may ignore persisted `late_stage_mode` blocks
- canonical endpoints may render historical records through that translation
- new pipeline, worker, settings-used, bundle, mirror, and API writes emit only
  canonical names
- no dual-write period is allowed
- no second business branch is retained for historical data

The old download route remains a thin read-only alias to the canonical loader
and response builder. Current UI links, bundle registries, mirrors, and writers
use only the canonical route and filename. The alias creates no dual write and
owns no second payload semantics.

### Deliverable 5: one runtime failure taxonomy at observation boundaries

Runtime evidence preserves the Phase 3 operational taxonomy unchanged:

- stages: `routing`, `adapter`, `parse`, `validate`
- routing codes: `routing_invalid`, `credentials_missing`
- adapter codes: `adapter_timeout`, `adapter_transport_error`,
  `adapter_http_error`, `adapter_contract_error`
- parse code: `parse_error`
- validate code: `validation_error`

Stage owners continue mapping these operational failures into existing stage
policies. Enrich may retry or fail its item, ranking may isolate/skip its item,
and CV generation may produce canonical generation failure/review outcomes.

Artifacts and observations must not invent competing runtime-stage names such
as `provider`, `transport`, `parsing`, or `normalization` when they describe
`LlmRuntimeFailure`. Those broader names may remain in stage-owned business
errors only where the stage contract already defines them.

### Deliverable 6: adapter-parity proof for every admissible adapter set

Parity tests compare adapter-invariant semantics after normalizing only
operational fields.

Required adapter sets:

- shared runtime: default OpenAI-compatible adapter versus fake adapter for
  deterministic success and each normalized failure class
- enrich: default/fake adapter paths using identical raw response fixtures
- ranking: default/fake adapter paths using identical raw response fixtures
- CV generation: direct, LangGraph, and fake adapter paths using identical
  structured response fixtures
- CV analysis: no adapter comparison while it has no routed LLM call; instead,
  assert that no LLM evidence is fabricated

Allowed operational differences:

- `provenance.adapter`
- `provenance.runtime_path`
- `provenance.attempt_count`
- `provenance.response_id`
- `provenance.trace_id`
- `provenance.latency_ms`
- adapter-local telemetry excluded from canonical evidence
- bounded diagnostic `failure.message` text for adapter-origin failures

Required equal fields for the same route and fixture:

- runtime status
- failure stage
- failure code
- retryable flag
- HTTP status
- provider
- model
- wire API
- routing part
- parsed stage value after stage parser
- stage semantic status
- stage output, validation, repair, reuse, and artifact meaning

Routing, parse, and validate failure messages remain exact where the shared
runtime owns them. Adapter-origin message wording may differ, but its taxonomy
and policy inputs may not.

### Deliverable 7: legacy late-stage label closeout

Delete current semantic/runtime-mode framing that no longer controls behavior:

- pipeline `_build_late_stage_mode_payload` and equivalent worker/control-plane
  builders
- control-plane default/load branches that infer trace applicability from
  `agentic` versus `non_agentic`
- settings-used and bundle-manifest `late_stage_mode` blocks
- trigger/runtime payload key `agentic_runtime_expectation` when it represents
  canonical CV-generation runtime expectation
- UI labels claiming an alternate non-agentic generation owner
- canonical settings-schema entry `cv.agentic_late_stage.enabled`, because the
  value is already ignored by the unified runtime and no longer enables a
  distinct stage path

Persisted historical settings may still contain the removed key. The existing
settings loader treats it as stale after schema removal and deletes that row
without changing runtime behavior. No replacement boolean is introduced.
Provider/model/wire API remain owned by `config/runtime/control_plane.yaml`, and
LangGraph remains an internal adapter choice rather than a second semantic mode.

The cleanup is intentionally exact. Agentic naming for unrelated synonym,
review, or automation features is outside this phase.

### Deliverable 8: final master-spec closeout boundary

Phase 5 completion permits the master spec to move to `completed` only when:

- all five child specs and implementation plans are terminal
- current writes use canonical runtime evidence and stage-neutral trace names
- parity and residue gates pass
- historical read compatibility has no current semantic branch
- generated planning lineage and managed docs are synchronized

No extra “remaining” child spec is created. Any unresolved item outside Phase 5
acceptance criteria is recorded as non-goal or separate follow-up work, not
silently appended to the runtime-spine sequence.

## Task/Wave Breakdown

### Wave 1: freeze current observation and compatibility surfaces

**Purpose:**
- inventory every current runtime-provenance, failure, trace, artifact, settings,
  worker, mirror, and API projection before deletion

**Steps:**
- [x] enumerate all `LlmRuntimeResult` consumers and current provenance builders
- [x] enumerate enrich, ranking, CV-analysis, and CV-generation debug/artifact
      carriers
- [x] classify every `late_stage_mode`, `agentic_late_stage_enabled`,
      `agentic_live_trace`, and `agentic_runtime_expectation` reference as current
      write, historical read, unrelated agentic feature, or dead code
- [x] freeze representative historical payload fixtures before changing readers
- [x] freeze adapter and stage-output parity fixtures before changing projections

**Verification:**
- [x] every deletion target has an identified replacement or explicit historical
      read rule
- [x] unrelated agentic features are excluded from residue gates

**Exit Criteria:**
- no current-write or compatibility surface depends on an unstated assumption

### Wave 2: canonical runtime-evidence projection

**Purpose:**
- make one safe projection of existing runtime truth reusable by every LLM stage

**Steps:**
- [x] add one pure projection helper in `llm_runtime.py`
- [x] add contract tests for success, every failure stage, null fields, and secret
      exclusion
- [x] route enrich, ranking, and CV-generation per-call diagnostics through the
      helper
- [x] preserve stage business row and result contracts
- [x] represent zero-call cases as zero calls rather than synthetic provenance

**Verification:**
- [x] all persisted per-call runtime blocks equal the canonical projection
- [x] no stage-local provenance normalizer redefines canonical field names
- [x] no secret or raw provider payload enters persisted evidence

**Exit Criteria:**
- one runtime evidence owner serves all active routed LLM stages

### Wave 3: artifact and observation convergence

**Purpose:**
- expose useful runtime evidence through existing bounded observability surfaces
  without adding business-row fields

**Steps:**
- [x] add canonical runtime summary and bounded evidence sample to enrich artifact
- [x] add canonical runtime summary and bounded evidence sample to ranking artifact
- [x] project CV-generation initial and repair invocations through same summary
- [x] remove fabricated LLM provenance from CV-analysis traces
- [x] reuse existing pipeline observation and truncation helpers
- [x] preserve replay, resume, reuse, ordering, and stage participation semantics

**Verification:**
- [x] each routed stage artifact reports accurate call/success/failure counts
- [x] CV analysis reports no LLM call when none occurred
- [x] no runtime evidence changes stage output rows or fingerprints

**Exit Criteria:**
- artifacts differ by stage content, not by runtime evidence contract

### Wave 4: trace and legacy-label closeout

**Purpose:**
- remove current mode framing and move late-stage trace surfaces to canonical
  stage names

**Steps:**
- [x] rename current CV-generation trace key, schema, family, artifact, and route
- [x] remove late-stage mode payload builders and current writes
- [x] change trace applicability to stage reach and artifact presence
- [x] add one-way historical readers for old persisted trace keys where required
- [x] remove ignored late-stage enablement setting from canonical settings schema
- [x] remove or rename stale control-plane labels and runtime expectation keys
- [x] update worker, mirror, bundle, and download projections

**Verification:**
- [x] new runs contain no mode-owned late-stage labels
- [x] historical fixtures remain inspectable through canonical surfaces
- [x] unrelated agentic automation and synonym features remain unchanged

**Exit Criteria:**
- canonical current behavior has no `agentic` versus `non_agentic` semantic frame

### Wave 5: parity, residue, docs, and master closeout

**Purpose:**
- prove symmetry and close the five-phase sequence

**Steps:**
- [x] lock shared-runtime and stage adapter-parity matrices
- [x] lock zero-call, reuse, replay, resume, failure, and historical-read cases
- [x] add exact residue assertions for deleted current-write labels and builders
- [x] synchronize stage and cross-cutting source docs
- [x] regenerate managed architecture and planning lineage outputs
- [x] mark Phase 5 and master completed only after all proof gates pass

**Verification:**
- [x] adapter-invariant fields match after allowed operational normalization
- [x] full regression, focused type checks, compile, doc lifecycle, and repository
      validators pass
- [x] master has no non-terminal child

**Exit Criteria:**
- LLM-runtime-spine remediation is complete with no hidden sixth phase

## Design Decisions

### Decision: serialize existing runtime result; do not invent another contract layer

- context: Phase 3 already owns normalized result, failure, and provenance
- choice: add one pure safe projection helper over `LlmRuntimeResult`
- alternatives considered:
  - new observability service or registry
  - stage-specific provenance dictionaries
  - generic event bus or middleware
- impact:
  - runtime truth stays single-owner
  - stages reuse one small helper
  - smallest implementation can delete local normalization code

### Decision: keep runtime evidence out of business rows

- context: enrich and ranking exact-output parity intentionally excluded runtime
  fields in Phase 4
- choice: use sidecar debug, callback, observation, trace, and stage-artifact
  projections
- alternatives considered:
  - add provenance fields to every enriched or ranked row
  - wrap every stage business result in a new generic result type
- impact:
  - fingerprints, persistence, downstream schemas, and reuse stay stable
  - observability improves without widening business contracts

### Decision: one evidence block per real runtime invocation

- context: CV generation can perform initial and repair calls, enrich can perform
  outer 429 retries, while reuse and gated cases perform none
- choice: project each actual `execute_llm_task` result before outer retry or
  business-failure mapping; aggregate counts separately
- boundary: `invocation_index` distinguishes outer runtime calls while
  provenance `attempt_count` continues to describe adapter-internal attempts
- alternatives considered:
  - keep only latest provenance
  - synthesize one stage-level provider record for zero-call cases
- impact:
  - attempt history is truthful
  - no-call paths remain distinguishable from successful calls

### Decision: CV analysis shares frame, not fake LLM provenance

- context: CV analysis is stage-adjacent but currently deterministic/repo-native
- choice: keep stage trace symmetry while omitting LLM runtime evidence
- alternatives considered:
  - label built-in Python execution as a fake provider
  - route analysis through LangGraph solely for visual symmetry
- impact:
  - admissible cases stay honest
  - future LLM adoption must enter through same runtime contract

### Decision: canonical writes change once; historical reads translate once

- context: stored runs contain legacy trace and mode fields
- choice: stop dual writes immediately and translate old reads at the boundary
- alternatives considered:
  - indefinite dual write/read
  - migration of every stored payload
  - preserve old semantic names in all new artifacts
- impact:
  - current SSOT is unambiguous
  - historical inspection remains available
  - compatibility code cannot become a second semantic owner

### Decision: delete ignored enablement setting; add no replacement toggle

- context: unified late-stage runtime ignores the old boolean and always emits
  `agentic` mode payloads
- choice: remove the canonical setting and ignore persisted historical values
- alternatives considered:
  - keep a no-op UI toggle
  - rename it to another boolean mode switch
  - let it select a second generation path
- impact:
  - settings describe real behavior
  - adapter/routing authority remains in the control-plane route contract

### Decision: parity follows admissible adapter sets

- context: CV generation has direct and LangGraph adapters; enrich and ranking do
  not need artificial LangGraph adapters
- choice: compare each stage across adapters it actually supports, using fake
  adapter everywhere for deterministic contract proof
- alternatives considered:
  - force every stage through LangGraph
  - prove only CV-generation parity
- impact:
  - symmetry is contract-based rather than framework-based
  - no unused adapter code is added

### Decision: preserve stage failure policy

- context: shared runtime taxonomy is operational, while stages differ in retry,
  skip, batch isolation, review, and acceptance behavior
- choice: converge evidence fields, not business policy
- alternatives considered:
  - one generic stage failure policy
  - move stage status mapping into runtime
- impact:
  - Phase 4 semantic parity remains intact
  - runtime stays stage-neutral

## Invariants

- `LlmRuntimeResult` remains the in-memory runtime SSOT
- `llm_runtime.py` never branches on a stage routing-part value
- LangGraph owns only adapter/orchestration mechanics
- provider/model/base URL/wire API remain control-plane routing facts
- credentials remain environment-only and never enter persisted evidence
- runtime evidence derives only from actual `execute_llm_task` results
- zero-call paths emit no synthetic LLM provenance
- CV analysis emits no LLM provenance while it makes no routed LLM call
- enrich and ranking business row shapes remain unchanged
- CV-generation status, validation, repair, reuse, review, and artifact semantics
  remain unchanged
- runtime failure taxonomy stays `routing|adapter|parse|validate`
- stage business-error taxonomies remain stage-owned
- trace applicability depends on stage participation and artifact presence, not a
  mode label
- canonical new writes contain no late-stage `agentic` versus `non_agentic`
  semantic branch framing
- historical read translation is one-way and never dual-writes legacy fields
- persisted historical `cv.agentic_late_stage.enabled` values cannot change
  current runtime behavior
- replay and resume do not duplicate completed runtime calls or evidence
- exact reuse performs no new runtime call and reports zero new calls
- artifact samples remain bounded by existing truncation policy
- no prompt, raw response, raw provider payload, base URL, header, API key, or
  credential value enters canonical evidence
- no new dependency, registry, service class, event bus, middleware, or plugin
  system is introduced
- unrelated synonym, review, and automation uses of `agentic` remain untouched
- generated docs are updated only through repository generators

## Acceptance Criteria

- one tested runtime-evidence projection exists in `llm_runtime.py`
- enrich, ranking, and CV generation emit that projection for every actual call
- CV analysis emits no fabricated LLM provenance
- stage artifacts expose canonical runtime summaries and bounded samples
- direct/LangGraph/fake parity passes for all admissible adapter sets
- adapter-invariant business outputs match after only allowed operational fields
  are normalized
- new late-stage traces use stage-neutral schemas, family, keys, and filenames
- trace applicability no longer reads `late_stage_mode`
- current pipeline, worker, settings-used, mirror, bundle, and API writes omit
  late-stage mode fields
- old persisted CV-generation trace payloads remain readable through canonical
  surfaces
- canonical settings schema and UI no longer expose the ignored late-stage
  enablement toggle
- stage fingerprints, reuse, row contracts, ordering, retry, failure isolation,
  review, acceptance, persistence, replay, and resume behavior remain stable
- exact residue gates find no active current-write legacy owner
- managed docs, planning lineage, and repository validators pass
- Phase 5 and master close only after all child artifacts are terminal

## Non-Goals

- changing enrich extraction meaning, defaults, retry policy, or row fields
- changing ranking score, label, reasoning, ordering, thresholds, or skip policy
- changing CV-analysis evidence, gap, fit, status, or readiness meaning
- changing CV-generation prompt, schema, validation, repair, review, acceptance,
  persistence, fingerprint, or reuse meaning
- moving CV analysis to an LLM
- forcing enrich or ranking through LangGraph
- removing the direct adapter
- renaming `agentic_cv_analysis.py` or `agentic_cv_generation.py` solely for
  aesthetics
- deleting unrelated agentic synonym, review, or automation features
- adding a generic observability platform
- adding a new user-facing adapter selection setting
- migrating all historical persisted JSON in place
- changing LangFuse vendor configuration or adopting a new telemetry backend
- authoring the Phase 5 implementation plan before this spec is reviewed and
  accepted

## Risks and Mitigations

- Risk: evidence collection changes row shape or fingerprint inputs.
  - mitigation: sidecar-only projection tests and exact business-output fixtures.
- Risk: CV-generation repair overwrites initial-call provenance.
  - mitigation: one evidence block per actual call and ordered attempt fixtures.
- Risk: CV analysis keeps fake built-in provider fields through fallback trace
  builders.
  - mitigation: residue assertions and historical fixture translation tests.
- Risk: trace rename breaks inspection of stored runs.
  - mitigation: canonical readers translate old stored keys; no dual current
    writes.
- Risk: removing the no-op setting breaks settings-store parsing.
  - mitigation: loaders ignore persisted unknown compatibility values and tests
    cover old snapshots.
- Risk: broad `agentic` cleanup damages unrelated automation features.
  - mitigation: exact target-pattern residue gates and explicit excluded-feature
    fixtures.
- Risk: parity normalization hides semantic differences.
  - mitigation: closed allowed-difference field set; all business fields remain
    exact.
- Risk: adapter messages vary and make useful parity impossible.
  - mitigation: compare canonical taxonomy/policy fields; treat bounded
    adapter-origin message as diagnostic only.
- Risk: runtime evidence volume makes artifacts unbounded.
  - mitigation: full item evidence stays in existing diagnostic paths; stage
    artifacts store counts and bounded samples.
- Risk: replay or resume emits duplicate evidence.
  - mitigation: fixture runs compare fresh, paused, resumed, and reused call
    counts and identities.
- Risk: Phase 5 grows into a runtime redesign.
  - mitigation: preserve Phase 3 dataclasses and Phase 4 stage semantics; add one
    serializer and delete local projections first.

## Validation Plan

- proof target: Phase 4 is complete before Phase 5 begins
  - method: inspect Phase 4 spec/plan status and fresh regression evidence
  - evidence: both artifacts are `completed`; shared runtime migration and
    lifecycle validators pass

- proof target: canonical runtime evidence has one owner
  - method: projection unit tests plus source residue inspection
  - evidence: all persisted blocks equal the shared helper output; no stage-local
    provenance normalizer defines competing canonical fields

- proof target: evidence is secret-safe
  - method: sentinel route/adapter payload fixture containing keys, headers, base
    URL, raw body, and credentials
  - evidence: none appears in projected evidence, artifacts, logs, or snapshots

- proof target: every real LLM call uses same frame
  - method: enrich, ranking, and CV-generation success/failure fixtures
  - evidence: each call produces `llm_runtime_evidence_v1`; zero-call cases
    produce none

- proof target: CV analysis is honest
  - method: analysis-ready, blocked, skipped, failed, reused, and historical
    fallback fixtures
  - evidence: stage trace remains useful and contains no fabricated LLM
    provenance

- proof target: failure taxonomy is uniform
  - method: routing-invalid, credentials-missing, timeout, HTTP, transport,
    contract, parse, and validate fixtures
  - evidence: runtime evidence uses closed Phase 3 stages/codes and stage policy
    mapping remains unchanged

- proof target: adapter parity is bounded and exact
  - method: normalized comparison matrix for default, direct, LangGraph, and fake
    adapters where admissible
  - evidence: only allowed operational fields differ; semantic fields match

- proof target: repair and retry evidence is complete
  - method: CV-generation initial failure/repair success, adapter retry, enrich
    retry, and ranking isolated-failure fixtures
  - evidence: ordered calls, attempts, final stage status, and failure counts match
    actual execution

- proof target: artifact symmetry is bounded
  - method: stage-transition artifact snapshots for enrich, ranking, CV analysis,
    and CV generation
  - evidence: routed stages use same runtime-summary shape; CV analysis omits LLM
    evidence; samples obey bounds

- proof target: trace applicability is mode-free
  - method: stage-not-reached, reached-with-trace, reached-without-trace, degraded,
    failed-run, replay, and resume fixtures
  - evidence: applicability follows reach/presence only and never reads a mode
    field

- proof target: historical trace reads survive canonical rename
  - method: stored fixtures using `agentic_live_trace`, old schemas, and old mode
    blocks
  - evidence: canonical CV-generation trace endpoint and bundle expose translated
    content without dual writes

- proof target: ignored setting is removed safely
  - method: settings schema/UI tests plus persisted old-settings snapshot
  - evidence: new UI/schema omit the key; old stored row is pruned on load;
    runtime output is unchanged

- proof target: replay, resume, and reuse remain symmetric
  - method: fresh versus staged/resumed/reused comparison
  - evidence: business outputs match; no duplicate calls; exact reuse reports zero
    new calls

- proof target: current-write legacy labels are deleted
  - method: exact repository residue assertions
  - evidence: no active builder, branch, output key, schema, family, filename, UI
    label, or settings entry remains for the scoped late-stage labels

- proof target: unrelated agentic features remain intact
  - method: focused synonym/review/automation regression tests
  - evidence: their settings, routes, artifacts, and behavior are unchanged

- proof target: documentation lifecycle remains valid
  - method: generate planning lineage and run lifecycle/repository validators
  - evidence: source docs, generated surfaces, master/child lineage, and status
    constraints pass

Suggested implementation validation commands:

```powershell
python -m pytest tests/test_llm_runtime.py tests/test_enrich.py tests/test_ai_score.py tests/test_cv_generator.py tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_pipeline_stage_resume_parity.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py tests/test_fitcv_cp/test_run_artifact_mirror.py tests/test_fitcv_cp/test_settings_schema.py -q
python -m pytest -q
python -m mypy src/fitcv/llm_runtime.py src/fitcv/runtime_routing.py
python -m compileall -q src tests
python scripts/generate_planning_lineage.py
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
python scripts/hooks/run_validator.py --fast
git diff --check
```

Scoped residue gates must use exact late-stage patterns, not a repository-wide
ban on the word `agentic`:

```powershell
rg -n "late_stage_mode|agentic_late_stage_enabled|agentic_runtime_expectation|agentic_live_trace|agentic-live-trace|agentic_step_trace" src/fitcv src/fitcv_cp tests/test_pipeline.py tests/test_pipeline_agentic_late_stage.py tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_worker_job.py
rg -n "cv\.agentic_late_stage\.enabled|Agentic Late Stage Enabled|non-agentic path" src/fitcv src/fitcv_cp docs/configuration.md docs/pipeline.md tests/test_fitcv_cp
rg -n "def _normalize_runtime_provenance|route_part" src/fitcv/cv_generator.py src/fitcv/agentic_cv_generation.py src/fitcv/agentic_cv_analysis.py
```

Expected final result:

- no canonical current-write match for scoped legacy fields
- historical read adapters may retain exact old-key literals in one bounded
  compatibility location with tests
- no stage-local canonical provenance normalizer remains
- unrelated agentic-feature matches are excluded by path/pattern and remain
  valid

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Implementation and verification are complete. Runtime evidence, artifact/trace convergence, adapter parity, legacy-label deletion, historical reads, docs, full regression, type checks, compile checks, lifecycle checks, audit evidence, and GitNexus scope review pass. Phase 5 and the master spec are `completed`.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- `docs/superpowers/specs/2026-07-14-19-22-fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration-spec.md`
- `src/fitcv/llm_runtime.py`
- `src/fitcv/pipeline_observability.py`
- `src/fitcv/pipeline_stage_artifacts.py`
- `src/fitcv/pipeline.py`
- `src/fitcv_cp/app.py`
- `src/fitcv_cp/worker_run_support.py`
- `scripts/validate_planning_lifecycle.py`
</LINK>
