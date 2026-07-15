---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-llm-runtime-spine-phase-3-shared-runtime-contract
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md
targets:
  - src/fitcv/llm_runtime.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/openai_compat.py
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_generation.py
  - config/runtime/control_plane.yaml
  - docs/configuration.md
  - docs/pipeline.md
  - docs/architecture.md
  - tests/test_llm_runtime.py
  - tests/test_runtime_routing.py
  - tests/test_cv_generator.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
related_features:
  - cv_system
  - settings_system
  - inspection_debugging
related_stages:
  - enrich
  - ranking
  - cv_generation
---

# Detailed Spec: FitCV LLM runtime spine Phase 3 shared runtime contract

## Goal

Extract the smallest repo-native LLM runtime spine proven by current code:

`LlmTaskRequest -> resolved route -> LlmAdapter -> parse -> validate -> LlmRuntimeResult`

Phase 3 shares runtime mechanics only. Stage modules continue to own prompt
meaning, parser and schema definition, semantic validation rules, semantic
repair, review decisions, stage statuses, fingerprints, reuse, persistence, and
output artifacts.

CV generation becomes the first consumer because Phase 2 already exposes one
canonical semantic owner and two contract-equivalent runtime adapters. The
direct OpenAI-compatible writer and LangGraph writer must consume the same
shared runtime request/response seam. `enrich_extraction` and
`ranking_ai_score` remain behaviorally unchanged in Phase 3 and migrate in
Phase 4; no unused cross-stage framework is built ahead of that migration.

Existing owners remain authoritative:

- `config/runtime/control_plane.yaml` owns provider/model route selection
- `runtime_routing.py` owns route resolution and env-only credential lookup
- `openai_compat.py` owns OpenAI-compatible response decoding helpers
- stage modules own prompt/schema/parser definition, semantic validation, repair/review, and output meaning
- LangGraph owns adapter-local orchestration and telemetry only

## Key Deliverables

### Deliverable 1: one minimal shared runtime module

Add `src/fitcv/llm_runtime.py` as the only owner of the common execution
skeleton and OpenAI-compatible adapter call. It must not become a stage service,
plugin registry, dependency-injection container, or workflow framework.

Canonical public call shape:

```python
execute_llm_task(
    request,
    *,
    parser,
    validator,
    adapter=None,
) -> LlmRuntimeResult
```

`adapter=None` selects the repo-native OpenAI-compatible adapter. Tests and
LangGraph paths pass an explicit callable using the same adapter signature.

Uniform execution order:

1. validate programmer-owned request fields
2. resolve route from `request.routing_part`
3. resolve required credential from environment
4. invoke one adapter callable
5. parse adapter response using stage-owned parser
6. structurally validate parsed value using stage-supplied runtime validator
7. normalize runtime result, failure, provenance, and adapter telemetry

Stage semantic validation runs once after this call, before semantic repair,
review, or acceptance. An adapter may perform bounded transport retry or
wire-API compatibility fallback, but it may not alter prompt, parser, structural
validator, semantic validation, or stage decision meaning.

### Deliverable 2: one request and adapter contract

Canonical `LlmTaskRequest` fields:

- `routing_part: str`
- `prompt: str`
- `response_mode: Literal["text", "json_object", "json_schema"]`
- `instructions: str | None`
- `schema_name: str | None`
- `schema: dict[str, Any] | None`

Rules:

- `routing_part` selects one entry under
  `control_plane.model_routing.parts`; request does not carry provider, model,
  base URL, wire API, timeout, or API key
- `prompt` is already rendered by the stage owner
- `json_schema` requires non-empty `schema_name` and `schema`
- `text` and `json_object` reject schema fields to prevent ambiguous contracts
- API keys, authorization headers, stage inputs, config dictionaries, mutable
  mode labels, and output artifacts are not request fields

Canonical adapter callable shape:

```python
adapter(request, route, api_key) -> LlmAdapterResponse
```

Canonical stage callable shapes:

```python
parser(response: LlmAdapterResponse) -> Any
validator(value: Any) -> LlmValidationResult
```

The parser may close over stage-owned inputs needed for normalization and
rendering. The runtime validator checks structural admissibility only and may
close over stage-owned schema/config inputs. Semantic grounding and quality
validation remain stage-owned work after runtime success. Neither callable may
resolve routing, credentials, or adapter choice.

Canonical `LlmAdapterResponse` fields:

- `adapter: str`
- `runtime_path: str`
- `raw_text: str`
- `provider_payload: dict[str, Any] | None`
- `response_id: str | None`
- `trace_id: str | None`
- `attempt_count: int`
- `telemetry: dict[str, Any]`

`provider_payload` means transport-decoded provider data, not stage-parsed
business output. `adapter` and `runtime_path` are explicit operational
identity supplied by the adapter; runtime never infers identity from callable names.
Adapter telemetry is observation-only and cannot select stage meaning.

Adapters report operational failures by raising `LlmAdapterError` with:

- `code: Literal["adapter_timeout", "adapter_transport_error", "adapter_http_error"]`
- `message: str`
- `retryable: bool`
- `http_status: int | None`
- `adapter: str | None`
- `runtime_path: str | None`

Each adapter translates its native exceptions at its boundary. Unknown adapter
exceptions and invalid adapter return values normalize to
`adapter_contract_error`.

### Deliverable 3: one runtime result and failure envelope

Canonical `LlmRuntimeResult` fields:

- `status: Literal["succeeded", "failed"]`
- `parsed_value: Any | None`
- `validation: LlmValidationResult | None`
- `failure: LlmRuntimeFailure | None`
- `provenance: LlmRuntimeProvenance`
- `adapter_response: LlmAdapterResponse | None`

Canonical `LlmValidationResult` fields:

- `valid: bool`
- `errors: list[str]`
- `details: dict[str, Any]`

Stage validators may retain richer stage-specific fields inside `details`.
Runtime does not interpret those fields.

Canonical `LlmRuntimeFailure` fields:

- `stage: Literal["routing", "adapter", "parse", "validate"]`
- `code: str`
- `message: str`
- `retryable: bool`
- `http_status: int | None`

Closed Phase 3 failure-code set:

- routing:
  - `routing_invalid`
  - `credentials_missing`
- adapter:
  - `adapter_timeout`
  - `adapter_transport_error`
  - `adapter_http_error`
  - `adapter_contract_error`
- parse:
  - `parse_error`
- validate:
  - `validation_error`

Invalid Python call contracts remain programmer errors and raise immediately:
wrong input types, blank `routing_part`, blank prompt, unsupported
`response_mode`, missing JSON schema fields, or contradictory schema fields.
Operational routing, provider, parse, and validation failures return the
normalized failure envelope so stage owners can map them to existing stage
statuses without crashing a batch.

Result-state matrix:

- `succeeded` requires parsed value, `validation.valid is True`, and no failure
- parser failure returns no parsed value or validation and one `parse_error`
- validator exception returns parsed value, no validation, and one
  `validation_error`
- `validation.valid is False` preserves parsed value and validation and returns
  one `validation_error`
- routing or adapter failure returns no parsed value or validation
- `status == "failed"` always requires one failure; `status == "succeeded"`
  always forbids one

### Deliverable 4: one normalized provenance shape

Canonical `LlmRuntimeProvenance` fields:

- `routing_part`
- `runtime_path`
- `adapter`
- `provider`
- `model`
- `wire_api`
- `attempt_count`
- `response_id`
- `trace_id`
- `latency_ms`

Rules:

- `runtime_path` identifies the actual adapter path, such as
  `fitcv_llm_openai_compatible` or `fitcv_llm_langgraph`
- provider/model/wire API come from resolved routing, never stage-local config
  copies or LangGraph env values
- `adapter`, IDs, attempt count, and latency are observational
- base URL, API-key value, headers, raw secrets, and full provider payload are
  excluded from persisted canonical provenance
- route diagnostics may separately expose `api_key_available: bool`; they may
  never expose credential value

### Deliverable 5: one OpenAI-compatible transport implementation

The default adapter reuses `httpx` plus current `openai_compat.py` decoders. No
new dependency is added.

Wire behavior:

- `responses` sends prompt through `input` and optional instructions through
  `instructions`
- `chat_completions` sends optional instructions as one system message followed
  by one user prompt message
- `json_object` maps to the provider's JSON-object response format
- `json_schema` maps the stage-owned schema and schema name without altering it
- `text` omits structured response format
- `/responses` HTTP 404 may fall back once to `/chat/completions`
- fallback preserves requested response mode and schema; it never downgrades
  `json_schema` to `json_object`
- no other HTTP status silently changes route or wire API
- timeout, network, HTTP, empty response, and malformed adapter response are
  normalized through the shared failure envelope

### Deliverable 6: CV generation as first real consumer

Phase 3 migrates only runtime mechanics used by canonical CV generation:

- direct CV writer builds one `LlmTaskRequest` and calls `execute_llm_task`
- LangGraph writer implements the same adapter callable and returns one
  `LlmAdapterResponse`
- CV requests always use `response_mode="json_schema"`, schema name
  `fitcv_structured_cv_document`, the canonical live structured-CV schema, and
  strict schema transport formatting in both supported wire APIs
- initial and semantic-repair attempts reuse the same request/adapter seam
- CV parser, structured normalization, rendering, validation, repair-target
  selection, acceptance, review-required decision, statuses, fingerprinting,
  reuse, and persistence transitions remain in current CV owners

Delete CV-local duplicated transport mechanics after parity is proven:

- `_build_openai_compat_client` in `cv_generator.py`
- `_make_generation_client` shim when it exists only to expose
  `models.generate_content`
- CV-local OpenAI-compatible payload construction and response extraction
- duplicate runtime-provenance assembly superseded by shared result provenance

LangGraph response boundary mapping is fixed:

- retain the full transport-decoded dictionary as `provider_payload`
- extract `response_id`/`id`, `usage`, and `cost` into response fields/telemetry
- remove only those known transport metadata keys from the business payload
- serialize the remaining business payload into `raw_text`
- run the same CV parser against `raw_text` for direct and LangGraph adapters

LangGraph receives a bounded adapter mapping using the same `FITCV_LLM_*`
vocabulary as the repo-native runtime. Build that mapping only from the resolved
route and runtime-supplied credential; do not copy process route values and do
not translate the credential to `OPENAI_API_KEY`. `FITCV_LANGGRAPH_*` remains
reserved for adapter-specific debug or repository-location mechanics.

Phase 3 must not move `enrich.py` or `ai_score.py` onto the runtime. Their
current local client builders remain explicit Phase 4 deletion targets.

### Deliverable 7: one fake-adapter testing surface

Tests inject a plain callable into `execute_llm_task`; no fake SDK client,
`SimpleNamespace.models.generate_content`, environment patch matrix, HTTP
server, or LangGraph installation is required for semantic tests.

Required fake behaviors:

- return deterministic text
- return deterministic provider payload
- attach response/trace IDs and telemetry
- raise timeout, transport, or HTTP-like failure
- return malformed adapter response

One fake adapter must prove direct CV generation behavior without provider
network access. Phase 4 will reuse the same fake for enrich and ranking.

## Uniform Runtime Flow

Every admissible runtime call follows the same skeleton:

```text
stage builds prompt/schema
  -> request contract validation
  -> route resolution
  -> credential resolution
  -> adapter call
  -> stage parser
  -> stage validator
  -> normalized result/provenance/failure
  -> stage-owned repair/review/output mapping
```

Allowed adapter differences:

- latency
- response ID
- trace ID
- attempt count
- adapter-local telemetry
- transport retry count

Forbidden adapter differences:

- prompt text
- response schema
- parser selection
- validator selection
- parsed business value for deterministic fixture response
- validation result for deterministic fixture response
- stage status mapping
- semantic repair targets
- accepted/review decision
- stage output shape

## Task/Wave Breakdown

### Wave 1: freeze the shared contract before extraction

**Purpose:**
- prove exact repeated mechanics and prevent generic framework growth

**Steps:**
- [x] add request validation fixtures for text, JSON object, and JSON schema
- [x] add route, credential, wire payload, 404 fallback, decode, and provenance fixtures
- [x] add normalized failure fixtures for every closed Phase 3 failure code
- [x] add parser and validator success/exception fixtures
- [x] add one plain-callable fake adapter fixture
- [x] freeze CV direct-versus-LangGraph adapter-invariant output fixture
- [x] freeze current enrich and ranking output fixtures for later Phase 4 migration

**Verification:**
- [x] tests distinguish shared runtime mechanics from stage semantic meaning

**Exit Criteria:**
- no shared type or helper exists only for a hypothetical future surface

### Wave 2: generalize routing without creating a second route owner

**Purpose:**
- make current routing reusable by part name while preserving control-plane SSOT

**Steps:**
- [x] introduce generic immutable route type in `runtime_routing.py`
- [x] add `resolve_llm_routing(part_name, model_fallback="")`
- [x] add generic route-readiness validation for supported providers
- [x] keep `resolve_cv_generation_routing` as a thin compatibility wrapper
- [x] keep API-key lookup env-only
- [x] keep LangGraph override drift detection, but make routed values authoritative

**Verification:**
- [x] CV wrapper and generic resolver return equivalent route values
- [x] no provider/model/base URL/wire API resolver exists in `llm_runtime.py`

**Exit Criteria:**
- all runtime execution can request one resolved route without duplicating config parsing

### Wave 3: add minimal runtime executor and default adapter

**Purpose:**
- extract one reusable execution skeleton from proven CV/runtime mechanics

**Steps:**
- [x] add contract types and `execute_llm_task` in `llm_runtime.py`
- [x] add default OpenAI-compatible adapter using existing response decoders
- [x] normalize provenance and failures once
- [x] keep raw payload in-memory and opt-in; do not emit it automatically
- [x] expose explicit adapter injection for tests and LangGraph
- [x] reject registry, hooks framework, async abstraction, middleware stack, and plugin discovery

**Verification:**
- [x] runtime tests pass using only plain callable fakes and mocked `httpx`
- [x] shared executor contains no stage name branches except routing-part value passthrough

**Exit Criteria:**
- shared runtime is usable without importing enrich, ranking, CV, pipeline, or control-plane modules

### Wave 4: migrate CV runtime mechanics only

**Purpose:**
- prove shared spine against one real semantic owner before broader adoption

**Steps:**
- [x] make direct CV writer build `LlmTaskRequest`
- [x] make LangGraph writer implement shared adapter callable
- [x] route initial and repair attempts through `execute_llm_task`
- [x] map runtime failures to existing `CvGenerationResult` error/status semantics
- [x] preserve CV validation, repair, review, reuse, fingerprint, and persistence behavior
- [x] delete superseded CV-local HTTP client and response-decoding code
- [x] keep enrich/ranking runtime code unchanged

**Verification:**
- [x] existing Phase 2 parity, reuse, review, replay, resume, and persistence tests remain green
- [x] deterministic direct/LangGraph results differ only by allowed telemetry fields
- [x] residue gate finds no CV-local OpenAI-compatible payload builder

**Exit Criteria:**
- CV generation is one real consumer of shared runtime without losing semantic ownership

### Wave 5: docs, handoff, and Phase 4 readiness

**Purpose:**
- close extraction without smuggling enrich/ranking migration into Phase 3

**Steps:**
- [x] document one routing owner, one runtime owner, and stage-owned semantics
- [x] document normalized provenance and failure taxonomy
- [x] record enrich and ranking local client builders as Phase 4 deletion targets
- [x] regenerate managed architecture and planning metadata for touched sources
- [x] prepare Phase 4 spec handoff only after Phase 3 implementation is verified

**Verification:**
- [x] docs do not claim enrich/ranking use shared runtime before Phase 4
- [x] planning lifecycle and repo-contract validators pass

**Exit Criteria:**
- Phase 4 can migrate each remaining stage without reopening runtime contract design

## Design Decisions

### Decision: add one new runtime module, reuse existing owners around it

- context: runtime execution needs a neutral home, while routing and response
  decoding already have SSOT modules
- choice: add only `llm_runtime.py`; reuse `runtime_routing.py`,
  `openai_compat.py`, prompt registry, and stage parsers/validators
- alternatives considered:
  - expand `runtime_routing.py` into routing, transport, parse, and validation
  - create provider classes, factories, registries, and middleware
  - keep three copied HTTP client shims
- impact:
  - one new module has one responsibility
  - existing owners stay narrow
  - Phase 4 has one proven adoption target

### Decision: use callable injection, not an adapter class hierarchy

- context: runtime needs one production adapter, one LangGraph adapter, and test fakes
- choice: use a typed callable signature passed explicitly to
  `execute_llm_task`
- alternatives considered:
  - abstract base class plus factory registry
  - global mutable adapter singleton
  - SDK-shaped fake clients per stage
- impact:
  - fake adapters are one small function
  - no lifecycle or registration framework is required
  - adapter choice remains visible at call site

### Decision: stage supplies parser and validator

- context: enrich extraction, ranking score, and CV structure have different
  business schemas and recovery rules
- choice: runtime executes parser and validator callables but never defines
  their semantic contents
- alternatives considered:
  - generic JSON parser and generic Pydantic model registry inside runtime
  - adapter-owned parsing and validation
- impact:
  - shared flow stays symmetric
  - stage meaning remains SSOT
  - Phase 4 can migrate without changing output contracts

### Decision: runtime returns operational truth, stage maps business status

- context: `generation_failed`, ranking `skip`, and enrich failure isolation are
  not interchangeable stage meanings
- choice: runtime returns `succeeded|failed` plus normalized failure; stage
  owner maps that result into its existing status/output contract
- alternatives considered:
  - one global stage-status enum
  - propagate raw exceptions to pipeline
- impact:
  - failure taxonomy converges without flattening stage semantics
  - batch behavior stays stage-owned

### Decision: CV generation is first consumer; enrich/ranking wait for Phase 4

- context: Phase 2 already removed CV semantic duplication, while enrich and
  ranking still mix transport and stage behavior
- choice: prove runtime through CV first, freeze other stage contracts, migrate
  remaining stages separately
- alternatives considered:
  - migrate all three surfaces in one phase
  - create runtime with no production consumer
- impact:
  - smaller blast radius
  - no unused abstraction
  - Phase 4 becomes mechanical adoption plus deletion

### Decision: keep transport compatibility inside adapter

- context: current OpenAI-compatible routes may expose `/responses`,
  `/chat/completions`, SSE-wrapped JSON, or `/responses` 404 compatibility gaps
- choice: default adapter owns wire payload mapping, decode helpers, and one 404
  fallback; runtime and stage code see one adapter response
- alternatives considered:
  - duplicate wire handling in each stage
  - let stages retry different endpoints
- impact:
  - provider quirks stop leaking into stage semantics
  - route remains authoritative

## Invariants

- `config/runtime/control_plane.yaml` remains sole provider/model routing source.
- API-key values remain environment-only and never enter request, provenance,
  logs, artifacts, or failure details.
- `llm_runtime.py` never imports stage modules, pipeline, or control-plane app.
- Stage modules build prompt and response schema before runtime invocation.
- Stage modules own parse meaning, validation meaning, semantic repair/review,
  statuses, fingerprints, reuse, persistence, and output shape.
- Runtime owns only request validation, route/credential resolution, adapter
  invocation, parser/validator execution, operational failure normalization,
  and runtime provenance.
- Adapter choice cannot change deterministic semantic output after allowed
  telemetry fields are normalized.
- LangGraph remains an adapter callable, not a stage owner.
- Direct and LangGraph paths use same `LlmTaskRequest`, parser, and validator.
- Transport retry/fallback cannot mutate prompt, schema, parser, or validator.
- Invalid programmer call contracts raise; operational failures return one
  normalized result envelope.
- Raw provider payload is not automatically persisted or emitted.
- Enrich and ranking behavior does not change in Phase 3.
- No new provider SDK or dependency is added.
- No registry, class hierarchy, plugin loader, middleware stack, or async layer
  is introduced without a second proven need not covered by callable injection.
- `llm_runtime.py` is initially owned by the existing
  `cv_system.config-owned-generation-contract` capability; Phase 4 may broaden
  feature lineage only after enrich/ranking become real consumers.

## Acceptance Criteria

- One `execute_llm_task` entrypoint exercises route, adapter, parse, validation,
  failure, and provenance flow.
- One plain callable fake adapter drives deterministic runtime tests.
- Generic routing resolves any configured active routing part without stage-local
  config parsing.
- Current CV route wrapper delegates to generic routing and preserves behavior.
- Default OpenAI-compatible adapter supports text, JSON object, JSON schema,
  both configured wire APIs, current decoding, and one `/responses` 404 fallback.
- Every operational failure maps to one closed Phase 3 failure code.
- CV direct and LangGraph paths consume same request/parser/validator contract.
- CV Phase 2 status, reuse, validation, repair, review, replay, resume,
  persistence, and artifact tests remain green.
- CV-local duplicated HTTP client/payload/response-extraction code is deleted.
- `enrich.py` and `ai_score.py` outputs and tests remain unchanged.
- Docs identify enrich/ranking migration as Phase 4, not completed Phase 3 work.
- Planning, repo-contract, architecture metadata, typing, compile, focused tests,
  residue, and diff checks pass.

## Non-Goals

- migrating `enrich_extraction` or `ranking_ai_score` onto shared runtime
- changing enrichment normalization, ranking scoring, CV writing, validation,
  repair, acceptance, or review semantics
- changing stage output schemas or external API payloads
- changing retry counts, rate limits, concurrency, batching, persistence, reuse,
  replay, or resume semantics
- adding provider plugins, SDK wrappers, dependency injection, async execution,
  streaming, tool calling, prompt caching, or token accounting
- moving prompt templates or response schemas into runtime
- making LangGraph mandatory
- deleting compatibility labels reserved for Phase 5
- drafting Phase 3 implementation plan before this spec is reviewed and accepted

## Risks and Mitigations

- Risk: runtime becomes a generic framework before Phase 4 proves reuse.
  - mitigation: one module, callable injection, CV first consumer, no registry or
    hooks framework.
- Risk: shared parser/validator execution steals stage meaning.
  - mitigation: stage passes callables and maps runtime result to stage output.
- Risk: generic failure taxonomy erases useful stage details.
  - mitigation: keep closed operational code plus stage validation details and
    stage-owned output/error mapping.
- Risk: route compatibility wrappers become second owners.
  - mitigation: wrappers delegate to generic resolver and parity tests compare
    exact values.
- Risk: LangGraph env overrides drift from control-plane routing.
  - mitigation: resolved route supplies canonical provenance; env values remain
    compatibility transport inputs with drift assertions.
- Risk: raw provider payload leaks into artifacts.
  - mitigation: keep it in-memory and opt-in; provenance excludes payload and
    secrets.
- Risk: Phase 3 accidentally changes enrich or ranking.
  - mitigation: freeze their outputs, exclude migration edits, and require Phase
    4 spec before adoption.
- Risk: HTTP fallback hides real provider failures.
  - mitigation: fallback only on `/responses` 404; all other failures normalize
    without route mutation.

## Validation Plan

- proof target: Phase 2 is complete before Phase 3 begins
  - method: lifecycle inspection and existing Phase 2 verification evidence
  - evidence: Phase 2 spec and plan are `completed`; committed tests and
    validators pass at Phase 2 closeout

- proof target: one routing SSOT remains
  - method: routing unit tests and source inspection
  - evidence: generic and CV wrapper routes resolve identical provider, model,
    base URL, wire API, and timeout from control-plane config

- proof target: shared runtime has no stage meaning
  - method: import/residue inspection and unit tests
  - evidence: runtime imports no stage module and branches on no stage name;
    parser/validator behavior comes only from passed callables

- proof target: request trust boundary is explicit
  - method: parameterized request validation tests
  - evidence: invalid Python contracts raise; all valid response modes execute

- proof target: OpenAI-compatible transport is symmetric
  - method: mocked `httpx` tests for both wire APIs and response modes
  - evidence: expected payloads, decoder use, response IDs, and 404 fallback are
    deterministic

- proof target: operational failures are normalized
  - method: fake adapter/parser/validator and mocked HTTP failures
  - evidence: every failure row has expected stage, code, retryability, HTTP
    status, and provenance without secret leakage

- proof target: fake adapter is sufficient
  - method: runtime and CV tests using one plain callable
  - evidence: deterministic success, parse failure, validation failure, timeout,
    transport failure, and malformed response need no SDK-shaped fake

- proof target: CV generation is first real consumer without semantic drift
  - method: existing Phase 2 focused and pipeline parity suites
  - evidence: statuses, fingerprints, reuse, validation, repair, review, final
    artifacts, replay, resume, and persistence remain equal

- proof target: CV duplicate transport code is deleted
  - method: residue grep
  - evidence: no CV-local `_build_openai_compat_client`, SDK shim, OpenAI payload
    builder, or response extraction remains outside shared adapter

- proof target: Phase 4 boundary is preserved
  - method: source diff and enrich/ranking regression suites
  - evidence: enrich/ranking production behavior is unchanged and docs state
    migration remains pending

- proof target: repository lifecycle stays valid
  - method: planning lineage, lifecycle, repo contracts, architecture metadata,
    focused mypy, compile, test, and diff checks
  - evidence: all required commands pass; unrelated existing failures are
    recorded separately

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

The downstream implementation plan is `completed`. Shared runtime extraction,
CV adapter migration, duplicate transport deletion, parity proof, and lifecycle
validation satisfy this specification.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `config/runtime/control_plane.yaml`
- `src/fitcv/runtime_routing.py`
- `src/fitcv/openai_compat.py`
- `src/fitcv/agentic_cv_generation.py`
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
