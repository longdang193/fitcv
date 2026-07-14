---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: fitcv-llm-runtime-spine-phase-4-enrich-ranking-migration
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md
targets:
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/llm_runtime.py
  - src/fitcv/runtime_routing.py
  - config/runtime/control_plane.yaml
  - docs/stages/enrich.source.yaml
  - docs/stages/ranking.source.yaml
  - docs/features/bounded_parallel_enrichment/feature.source.yaml
  - docs/features/pipeline_performance/feature.source.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/configuration.md
  - docs/pipeline.md
  - docs/architecture.md
  - tests/test_llm_runtime.py
  - tests/test_runtime_routing.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_fitcv_cp/test_provider_routing.py
related_features:
  - bounded_parallel_enrichment
  - pipeline_performance
  - cv_system
  - settings_system
related_stages:
  - enrich
  - ranking
---

# Detailed Spec: FitCV LLM runtime spine Phase 4 enrich and ranking migration

## Goal

Migrate the remaining routed LLM stages, `enrich_extraction` and
`ranking_ai_score`, onto the Phase 3 repo-native runtime spine without changing
stage meaning:

`stage prompt -> LlmTaskRequest -> execute_llm_task -> stage parser -> structural validator -> existing stage output/failure policy`

Phase 4 removes local HTTP clients, SDK-shaped `SimpleNamespace` shims, route
resolution, credential lookup, wire payload construction, and response decoding
from `enrich.py` and `ai_score.py`. The existing shared owners remain unchanged:

- `config/runtime/control_plane.yaml` owns route selection
- `runtime_routing.py` owns route and credential resolution
- `llm_runtime.py` owns adapter invocation, wire compatibility, normalized
  operational failure, and runtime provenance
- `enrich.py` owns extraction prompt meaning, permissive parse/repair,
  normalization, merge behavior, 429 retry policy, batching, ordering, reuse,
  fingerprints, and enriched-row shape
- `ai_score.py` owns ranking prompt meaning, permissive score parsing, fit-label
  derivation, per-job failure isolation, batching, ordering, fingerprints, and
  ranking-row shape

Phase 3 runtime contract remains sufficient without a new abstraction, provider
registry, generic stage service, or shared batch executor. Phase 4 permits one
stage-neutral correction proven by current parser behavior: empty adapter text
must reach the stage parser instead of being rejected as an adapter contract
error. This changes no request, result, adapter, routing, provenance, or failure
type; it only removes the shared non-empty-text guard. CV runtime tests must prove
no regression.

Two operational convergences are explicit:

- enrichment inherits the shared adapter's one `/responses` HTTP 404 fallback to
  `/chat/completions`; ranking already has that fallback
- provider model is mandatory in control-plane routing; legacy stage-config model
  fallback is outside the Phase 4 admissible set and no fallback field is added to
  `LlmTaskRequest`

Normalized routing/credential failure message text may replace stage-local client
wording. Stage status, failure code/category, HTTP status, retry behavior, row
shape, and all non-error business fields remain invariant.

## Key Deliverables

### Deliverable 1: one repeated stage integration frame

Each migrated stage uses one private runtime helper with the same structural
shape:

```python
request = LlmTaskRequest(...)
result = execute_llm_task(
    request,
    parser=stage_parser,
    validator=stage_structural_validator,
    adapter=adapter,
)
```

Canonical private helper seams:

```python
_execute_enrich_runtime(
    job,
    config,
    *,
    adapter=None,
) -> LlmRuntimeResult

_execute_ranking_runtime(
    job,
    candidate_summary,
    top_evidence,
    config,
    *,
    adapter=None,
) -> LlmRuntimeResult
```

The parser and structural validator may be nested callables inside each helper.
No public function signature changes are required. `enrich_job`, `enrich_batch`,
`score_job`, and `run_ai_scoring` remain the business entrypoints.

The helper name and exact nesting are implementation details, but these
boundaries are mandatory:

1. stage builds prompt and response contract
2. shared runtime resolves route and credential
3. shared runtime invokes adapter
4. stage parses and structurally validates returned value
5. stage maps runtime result to existing stage output/failure semantics

### Deliverable 2: enrich request and parser contract

`enrich_extraction` request fields are fixed:

- `routing_part="enrich_extraction"`
- `prompt=build_extraction_prompt(...)`
- `response_mode="json_object"`
- `instructions=None`
- `schema_name=None`
- `schema=None`

Phase 4 preserves `json_object`. It must not switch enrichment to
`json_schema`; stricter provider behavior would be a semantic/provider change,
not a transport-only migration.

The enrich runtime parser preserves the current two-path behavior and returns
the existing extraction-result shape:

```python
{
    "parsed": dict[str, Any],
    "errors": list[str],
    "raw_response": str,
}
```

Parser order:

1. receive `LlmAdapterResponse.raw_text`, including the empty string
2. decode it as one JSON value
3. on JSON decode failure, call `parse_extraction_response` with the same raw text
   and config
4. when decoded JSON is not an object, call `parse_extraction_response` with the
   same raw text and config
5. when it is an object, try `_apply_structured_normalization`
6. on `_ValidationError`, call `parse_extraction_response` with the same raw text
   and config
7. preserve `parse_extraction_response` repair, coercion, warning, canonical
   skill-entity, mapping-suggestion, non-object, and empty-result behavior

The structural validator checks only that:

- runtime parsed value is a mapping
- `parsed` is a mapping
- `errors` is a list of strings
- `raw_response` is a string

Non-empty `errors`, empty `parsed`, coercion warnings, and repair fallback remain
admissible enrich outcomes. They must not become runtime parse or validation
failures.

After runtime success, `enrich_job` keeps current stage mapping:

- log parse/normalization warnings through current logger path
- call `merge_scraped_and_enriched(job, parsed, config)` once
- preserve enriched-row fields, model/version fields, fingerprints, reuse
  behavior, mapping suggestions, canonical skill fields, and timestamps

### Deliverable 3: enrich operational failure and retry preservation

Shared runtime converts provider exceptions into `LlmRuntimeFailure`. Enrich
must preserve its current fail-fast and HTTP 429 retry semantics without
reintroducing `httpx` knowledge outside `llm_runtime.py`.

Add one stage-local exception, or an equivalent stage-local result-aware seam,
carrying the normalized failure:

```python
class EnrichRuntimeError(RuntimeError):
    failure: LlmRuntimeFailure
```

Required mapping:

- runtime success returns current merged enriched row
- runtime failure raises `EnrichRuntimeError` with message equal to
  `failure.message`
- `_enrich_chunk` retries only when:
  - `failure.stage == "adapter"`
  - `failure.code == "adapter_http_error"`
  - `failure.http_status == 429`
  - current attempt count is below `enrichment_max_retries`
- backoff remains `sleep_secs * (2 ** (attempts - 1))`
- `_acquire_enrich_rate_slot` remains before every request attempt
- every other failure emitted after the shared adapter's bounded `/responses`
  HTTP 404 compatibility fallback propagates and preserves batch fail-fast behavior

`enrich_batch` concurrency, chunking, deterministic output order, callbacks,
incremental persistence, and per-job retry isolation remain unchanged.

### Deliverable 4: ranking request and parser contract

`ranking_ai_score` request fields are fixed:

- `routing_part="ranking_ai_score"`
- `prompt=build_scoring_prompt(...)`
- `response_mode="json_object"`
- `instructions=None`
- `schema_name=None`
- `schema=None`

The ranking runtime parser calls `parse_score_response` with raw text and current
config. Current permissive score semantics remain authoritative:

- malformed JSON returns score `0.0`, fit label `skip`, and
  `parser_status="malformed_json"`
- non-object JSON returns current safe defaults
- invalid score values return current safe defaults or clamped score according
  to current parser behavior
- score remains clamped to `[0.0, 1.0]`
- invalid or absent fit labels remain derived through `fit_label_from_score`
- matched strengths, key risks, reasoning, and parser status keep current shape

The structural validator checks only the normalized score-record shape and
types. Parser fallback records remain valid runtime results; they must not be
reclassified as runtime failures.

After runtime success, `score_job` adds `job_url` exactly once and returns the
same ranking record. Runtime provenance remains in-memory and is not added to
ranking rows in Phase 4.

### Deliverable 5: ranking operational failure preservation

`run_ai_scoring` keeps current per-job failure isolation:

- `score_job` maps runtime failure to an exception carrying or rendering
  `failure.message`
- `_score_single` continues catching per-job exceptions
- failure row remains:
  - `ai_score=0.0`
  - `fit_label="skip"`
  - `score_reasoning="Scoring error: <message>"`
  - empty `matched_strengths`
  - empty `key_risks`
  - `parser_status="runtime_exception"`
- one failed job does not fail the ranking batch

`top_n`, input order, output order, `stage_runtime.ranking.concurrency`, submit
pacing, sleep behavior, candidate summary, top-two evidence limit, thresholds,
fingerprints, reuse, and persistence remain unchanged.

### Deliverable 6: delete local transport owners

After parity proof, delete from `enrich.py`:

- `_build_openai_compat_client`
- `_make_genai_client`
- `SimpleNamespace` transport shim
- local `httpx.Client` transport construction
- local provider/model/base URL/wire API resolution
- local credential lookup
- local OpenAI-compatible payload building and response extraction
- direct imports from `openai_compat.py` used only by deleted transport code

After parity proof, delete from `ai_score.py`:

- `_make_genai_client`
- `SimpleNamespace` transport shim
- local `httpx.Client` transport construction
- local provider/model/base URL/wire API resolution
- local credential lookup
- local OpenAI-compatible payload building and response extraction
- direct imports from `openai_compat.py` used only by deleted transport code

No compatibility wrapper remains for private client-builder functions. Current
semantic tests move to plain callable adapters through the private runtime
helpers.

### Deliverable 7: no shared-runtime redesign beyond empty-text pass-through

Phase 4 consumes these Phase 3 contracts as-is:

- `LlmTaskRequest`
- `LlmAdapterResponse`
- `LlmValidationResult`
- `LlmRuntimeFailure`
- `LlmRuntimeResult`
- `LlmAdapter`
- `execute_llm_task`

Expected production changes outside stage modules:

- `llm_runtime.py`: remove only the empty-response rejection in
  `execute_llm_task` and the default OpenAI-compatible adapter so stage parsers
  own empty response meaning
- `runtime_routing.py`, `openai_compat.py`, and
  `config/runtime/control_plane.yaml`: none

No new runtime field, branch, adapter type, hook, option, or abstraction is
allowed. Missing routed model remains `routing_invalid`; do not restore stage
config fallback through the request contract.

### Deliverable 8: exact-output parity and fake-adapter tests

Both stages reuse Phase 3 plain-callable fake adapters. SDK-shaped clients,
mocked `SimpleNamespace.models.generate_content`, and stage-local mocked HTTP
payload tests are removed when they test deleted transport ownership.

Required enrich parity fixtures:

- valid JSON object through structured normalization
- structured-normalization failure falling back to current repair parser
- empty text and malformed JSON producing current empty/default merged fields
- valid non-object JSON producing current empty/default merged fields and error
- enum coercion warnings
- canonical skill entities and mapping suggestions
- merged model/version/fingerprint/reuse fields
- adapter HTTP 429 retry with unchanged attempts and backoff
- non-429 failure propagation
- sequential and concurrent deterministic output order
- retry callback behavior: job_start once per attempt and job_done once after
  success
- callback and incremental persistence behavior

Required ranking parity fixtures:

- valid score response
- fenced JSON
- empty, malformed, and non-object JSON safe defaults
- invalid/clamped score behavior
- invalid/derived fit label behavior
- runtime failure mapped to current skip row
- sequential and concurrent deterministic output order
- top-N, top-two evidence, pacing, thresholds, fingerprint, reuse, and
  persistence behavior

Adapter-invariant stage output must compare exactly except normalized operational
failure message text. Allowed differences are failure message wording, adapter
name, runtime path, latency, IDs, attempt count, and adapter telemetry. Failure
status/category, HTTP status, retry decision, parser status, row shape, and all
non-error business fields remain exact.

## Uniform Runtime Flow

Every Phase 4 LLM call follows one skeleton:

```text
stage builds prompt
  -> stage builds LlmTaskRequest(json_object)
  -> shared route and credential resolution
  -> shared adapter call
  -> stage permissive parser
  -> stage structural validator
  -> normalized LlmRuntimeResult
  -> existing stage output/failure policy
  -> existing batch/reuse/persistence flow
```

Allowed stage differences:

- prompt and parser meaning
- normalized business result shape
- enrich repair/coercion behavior
- ranking score/label fallback behavior
- enrich fail-fast plus 429 retry policy
- ranking per-job skip policy
- batch size, concurrency, pacing, callbacks, and persistence

Forbidden stage differences:

- route resolution implementation
- credential lookup implementation
- provider HTTP client construction
- wire payload construction
- response decoding implementation
- `/responses` 404 compatibility fallback implementation
- normalized adapter failure taxonomy
- provider/model/base URL/wire API branches in stage modules

## Acceptance Criteria

- [x] `enrich_job` and `score_job` public signatures remain unchanged
- [x] both stages call `execute_llm_task` through one private runtime seam each
- [x] both requests use their canonical routing part and `json_object`
- [x] `llm_runtime.py` contains no stage-name branch
- [x] `enrich.py` and `ai_score.py` contain no provider HTTP transport owner
- [x] enrichment permissive parse/repair and merge outputs remain exact
- [x] empty, malformed, and non-object provider text reaches stage parsers
- [x] ranking permissive parse/fallback and output records remain exact
- [x] enrich 429 retry, backoff, pacing, and post-adapter fail-fast semantics remain exact
- [x] enrich adopts only the shared bounded `/responses` HTTP 404 compatibility fallback
- [x] ranking per-job runtime failure still produces current skip row
- [x] enrich retry callbacks emit job_start per attempt and job_done once on
      success
- [x] batch ordering, concurrency, callbacks, and persistence remain unchanged
- [x] routed model is mandatory; no stage-config model fallback is added to the
      runtime request
- [x] normalized operational failure text is the only stage-row parity exception
- [x] prompt IDs, prompt text, response mode, thresholds, schema/version fields,
      fingerprints, and reuse decisions remain unchanged
- [x] no runtime provenance field is added to enrich or ranking rows
- [x] CV runtime behavior remains green
- [x] no new dependency is added
- [x] managed docs and generated metadata match final ownership wording

## Non-Goals

- migrating CV analysis or CV generation again
- changing prompt text, prompt IDs, thresholds, model routes, or response schemas
- switching enrich or ranking to strict `json_schema`
- adding LangGraph adapters to enrich or ranking
- adding new providers, SDKs, async APIs, streaming, middleware, hooks, retry
  frameworks, adapter registries, or dependency injection
- moving enrich/ranking parser or business validation into `llm_runtime.py`
- unifying enrich fail-fast and ranking skip behavior
- changing reuse, fingerprints, persistence, stage artifacts, row fields, or
  pipeline/stage-runner ownership
- emitting shared runtime provenance or converged failure artifacts; Phase 5
  owns observability and artifact convergence
- deleting legacy labels outside the two client-shim surfaces; Phase 5 owns
  final legacy-label closeout

## Task/Wave Breakdown

### Wave 1: freeze current stage semantics

**Purpose:**
- prove exact behavior before deleting local transport owners

**Steps:**
- [x] freeze enrich request prompt, permissive parser, merge output, retry,
      shared 404 fallback boundary, ordering, callback, reuse, fingerprint, and
      persistence fixtures
- [x] freeze ranking request prompt, permissive parser, skip output, ordering,
      pacing, reuse, fingerprint, and persistence fixtures
- [x] classify existing client-shim tests as transport-owner tests or semantic
      tests
- [x] record exact local transport imports/functions to delete

**Verification:**
- [x] current enrich and ranking suites pass before migration
- [x] fixture comparison excludes only runtime telemetry not present in stage rows

**Exit Criteria:**
- stage semantic baseline is explicit and no migration decision depends on old
  SDK-shaped test scaffolding

### Wave 2: migrate enrich onto shared runtime

**Purpose:**
- remove enrich-local transport while preserving its stronger retry/fail-fast
  boundary

**Steps:**
- [x] add one private enrich runtime helper using `LlmTaskRequest`
- [x] preserve structured normalization followed by repair-parser fallback
- [x] add structural validation for existing extraction-result shape
- [x] map runtime failure through one stage-local failure seam
- [x] update `_enrich_chunk` to retry normalized adapter HTTP 429 only
- [x] delete enrich client builders, shim, route lookup, credential lookup, HTTP
      payload, and response decode code
- [x] replace SDK-shaped transport tests with fake-adapter runtime tests

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_enrich.py -q`
- [x] exact-output enrich parity fixtures pass
- [x] 429 retry/backoff and non-429 fail-fast fixtures pass
- [x] residue gate finds no enrich-local provider transport

**Exit Criteria:**
- enrich uses shared runtime and retains exact stage and batch semantics

### Wave 3: migrate ranking onto shared runtime

**Purpose:**
- remove ranking-local transport while preserving permissive scoring and
  per-job isolation

**Steps:**
- [x] add one private ranking runtime helper using `LlmTaskRequest`
- [x] call `parse_score_response` as the stage parser
- [x] add structural validation for normalized score record
- [x] map runtime failure into current `_score_single` skip path
- [x] delete ranking client shim, route lookup, credential lookup, HTTP payload,
      and response decode code
- [x] replace SDK-shaped transport tests with fake-adapter runtime tests

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_ai_score.py -q`
- [x] exact-output ranking parity fixtures pass
- [x] runtime failure still returns current skip record
- [x] residue gate finds no ranking-local provider transport

**Exit Criteria:**
- ranking uses shared runtime and retains exact parser, label, batch, and failure
  semantics

### Wave 4: cross-stage parity and regression proof

**Purpose:**
- prove migration changed mechanics only

**Steps:**
- [x] compare before/after enrich and ranking fixture outputs exactly
- [x] run pipeline replay/resume and routing regressions
- [x] confirm CV shared-runtime consumer remains unchanged
- [x] confirm control-plane routing and config are unchanged
- [x] inspect Git diff for stage-semantic or output-shape drift

**Verification:**
- [x] all commands in Validation Plan pass
- [x] no production change exists outside bounded stage integration/deletion
      targets unless separately justified by a failing test

**Exit Criteria:**
- all three routed LLM surfaces use one runtime spine with stage meaning intact

### Wave 5: docs and Phase 5 handoff

**Purpose:**
- document completed adoption without pulling observability closeout forward

**Steps:**
- [x] update stage and cross-cutting docs only where runtime ownership wording is
      stale
- [x] regenerate architecture and planning metadata
- [x] record remaining Phase 5 targets: provenance/artifact convergence and
      legacy-label deletion
- [x] mark Phase 4 spec, plan, and master entry completed only after proof passes

**Verification:**
- [x] docs state enrich, ranking, and CV share runtime mechanics
- [x] docs still state each stage owns semantic output and failure policy
- [x] planning lifecycle and repo-contract validators pass

**Exit Criteria:**
- Phase 5 can close observability and labels without reopening stage migration

## Design Decisions

### Decision: reuse Phase 3 runtime unchanged

- context: Phase 3 already provides request, adapter, parse, structural
  validation, failure, provenance, and fake-adapter contracts
- choice: consume those contracts directly from both stage modules
- alternatives considered:
  - add a second enrich/ranking runtime wrapper module
  - add a provider registry or generic stage service
  - retain local client shims behind a compatibility adapter
- impact:
  - smallest diff deletes more code than it adds
  - one runtime owner remains
  - Phase 4 proves the shared contract against all current LLM stages

### Decision: keep `json_object` for both stages

- context: current enrich and ranking providers request JSON objects and rely on
  permissive stage parsers for repair and fallback
- choice: preserve `response_mode="json_object"`
- alternatives considered:
  - switch enrich to Pydantic-derived `json_schema`
  - switch ranking to a strict score schema
- impact:
  - provider behavior stays stable
  - parser fallback remains reachable
  - schema tightening remains a separately reviewed semantic change

### Decision: adopt shared adapter 404 compatibility fallback

- context: ranking already falls back from unsupported `/responses` to
  `/chat/completions`, while enrich currently exposes the 404 as failure
- choice: enrichment adopts the Phase 3 adapter's single 404 compatibility
  fallback before stage failure mapping
- alternatives considered:
  - add a stage flag to disable shared fallback for enrich
  - keep enrich-local HTTP transport
- impact:
  - one transport compatibility behavior becomes symmetric
  - no stage branch or runtime option is added
  - enrich business output and failure policy after adapter exhaustion remain unchanged

### Decision: private runtime helpers, unchanged business APIs

- context: tests need fake adapter injection, but pipeline callers should not
  receive transport parameters
- choice: add one private runtime helper per stage; keep public stage signatures
  unchanged
- alternatives considered:
  - add `adapter` parameters to public functions
  - patch runtime globals in tests
- impact:
  - fake adapters stay plain callables
  - pipeline and stage runner require no changes
  - transport testing does not leak into business API

### Decision: permissive parser outcomes remain successful runtime values

- context: both current parsers intentionally convert empty, malformed, or
  non-object provider output into safe stage-owned defaults
- choice: remove the shared empty-text rejection and let structural validators
  accept normalized fallback records
- alternatives considered:
  - turn malformed JSON into runtime `parse_error`
  - make runtime own repair and defaulting
- impact:
  - enrich and ranking degenerate-response semantics remain exact
  - operational failure stays distinct from low-quality model output
  - runtime taxonomy does not erase stage meaning

### Decision: routed model is mandatory

- context: current stage clients pass legacy config-derived model fallback while
  shared runtime resolves only the control-plane routing part
- choice: treat a missing routed model as `routing_invalid`; do not add fallback
  state to `LlmTaskRequest`
- impact:
  - control-plane remains model SSOT
  - configured model values do not change
  - missing-model legacy fallback is explicitly outside admissible Phase 4 cases

### Decision: normalized failure text may converge

- context: shared routing owns generic failure messages while deleted stage clients
  emitted stage-specific wording
- choice: preserve failure category/status/retry semantics and allow message text
  to normalize
- impact:
  - no stage-specific error translator survives transport deletion
  - exact-output parity excludes only operational failure wording

### Decision: enrich keeps one stage-local failure exception

- context: enrich must inspect normalized HTTP status to preserve 429 retry while
  public `enrich_job` still returns a row or raises
- choice: use one small stage-local exception carrying `LlmRuntimeFailure`
- alternatives considered:
  - rethrow `httpx.HTTPStatusError`
  - add retry hooks or raise-on-failure mode to shared runtime
  - return union result types from public enrich functions
- impact:
  - no transport dependency remains in enrich
  - retry policy stays stage-owned
  - shared runtime API stays unchanged

### Decision: defer provenance output to Phase 5

- context: runtime now provides normalized provenance, but enrich and ranking row
  contracts do not currently emit it
- choice: consume runtime result internally without adding row/artifact fields
- alternatives considered:
  - add runtime provenance to every row during migration
  - add a shared observability projection now
- impact:
  - exact-output parity remains possible
  - Phase 4 stays transport-only
  - Phase 5 owns one deliberate observability convergence

## Invariants

- control-plane routing remains the only provider/model/base URL/wire API owner
- API keys remain environment-only and never enter requests, config, rows,
  artifacts, logs, or fingerprints
- shared runtime contains no branch on `enrich_extraction` or `ranking_ai_score`
- stage modules contain no provider transport after migration
- prompts and parser semantics remain stage-owned
- both stages keep `json_object` response mode
- empty, malformed, and non-object text reaches stage parsers
- enrich parser fallback and empty/default merge behavior remain unchanged
- routed model is mandatory in control-plane config; no stage-config fallback
  exists in the runtime request
- normalized operational failure message text may converge
- enrich inherits the shared adapter's single `/responses` HTTP 404 compatibility fallback
- enrich retries only normalized adapter HTTP 429 with current limit/backoff
- enrich batch stays fail-fast for every failure remaining after adapter fallback
- enrich chunking, pacing, ordering, callbacks, and incremental persistence remain
  unchanged
- ranking malformed output remains a stage-owned skip result, not runtime failure
- ranking runtime failures remain isolated to one skip row
- ranking top-N, evidence limit, thresholds, pacing, concurrency, ordering, reuse,
  fingerprints, and persistence remain unchanged
- no runtime provenance or new failure field is added to existing stage rows
- CV generation remains a regression consumer of the same runtime contract
- no new dependency or abstraction layer is introduced

## Risks and Mitigations

- Risk: enrich 429 retry disappears because runtime catches `httpx` errors.
  - mitigation: stage-local failure seam carries normalized HTTP status and tests
    exact attempt/backoff behavior.
- Risk: shared 404 fallback is mistaken for semantic drift or becomes configurable per stage.
  - mitigation: name it as the one allowed operational convergence and test one
    bounded fallback with no stage flag.
- Risk: empty or malformed model output becomes a runtime failure and changes
  downstream behavior.
  - mitigation: shared runtime passes empty text through; parsers keep current
    permissive defaults; structural validators accept fallback records.
- Risk: route model starts leaking into fingerprints or output fields differently.
  - mitigation: preserve existing fingerprint and merge helpers; defer provenance
    convergence to Phase 5.
- Risk: fake-adapter injection leaks into public business APIs.
  - mitigation: keep adapter injection on private runtime helpers only.
- Risk: deletion removes semantic normalization hidden inside client shims.
  - mitigation: freeze structured and fallback parity fixtures before deletion.
- Risk: batch refactor changes ordering or failure isolation.
  - mitigation: do not refactor batch executors; change only per-job runtime seam
    and normalized failure catch.
- Risk: Phase 4 becomes a shared-runtime redesign.
  - mitigation: shared modules are verify-only unless a failing neutral contract
    test forces a spec amendment.

## Validation Plan

- proof target: Phase 3 is complete before Phase 4 begins
  - method: lifecycle and Git inspection
  - evidence: Phase 3 spec/plan/master entry are `completed`; commit `0ee85f44`
    exists on the active branch

- proof target: one runtime owner serves all three routed LLM surfaces
  - method: source inspection and residue grep
  - evidence: enrich, ranking, and CV call `execute_llm_task`; only
    `llm_runtime.py` owns provider HTTP transport

- proof target: enrich semantic output is unchanged
  - method: exact fixture comparison and current enrich suites
  - evidence: structured, fallback, malformed, coercion, merge, fingerprint,
    reuse, callback, ordering, and persistence outputs match

- proof target: enrich retry/fail-fast policy is unchanged after shared adapter exhaustion
  - method: normalized failure fixtures
  - evidence: one `/responses` HTTP 404 may fall back inside the adapter; only
    remaining adapter HTTP 429 retries with current attempts/backoff; every other
    remaining failure propagates

- proof target: ranking semantic output is unchanged
  - method: exact fixture comparison and current ranking suites
  - evidence: score, label, reasoning, arrays, parser status, ordering,
    fingerprint, reuse, and persistence outputs match

- proof target: ranking failure isolation is unchanged
  - method: batch fixture with one adapter failure
  - evidence: failed row is current runtime-exception skip shape; sibling rows
    still score and output order stays stable

- proof target: shared runtime contract did not regress
  - method: Phase 3 runtime and CV suites
  - evidence: runtime request/adapter/failure tests and CV direct/LangGraph parity
    remain green

- proof target: no transport residue remains in stage modules
  - method: source grep
  - evidence: no client shim, `SimpleNamespace`, local `httpx.Client`, endpoint,
    payload, response decoder, route resolver, or credential resolver remains

- proof target: repository lifecycle stays valid
  - method: focused mypy, compile, architecture, planning, repo-contract, and
    diff checks
  - evidence: required commands pass; unrelated existing debt is recorded
    without scope expansion

Required implementation verification:

```powershell
python -m pytest tests/test_llm_runtime.py tests/test_runtime_routing.py tests/test_enrich.py tests/test_ai_score.py -q
python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_fitcv_cp/test_provider_routing.py -q
python -m mypy src/fitcv/llm_runtime.py src/fitcv/runtime_routing.py --follow-imports=skip --show-error-codes
python -m mypy src/fitcv/enrich.py src/fitcv/ai_score.py --follow-imports=skip --show-error-codes --disable-error-code=no-any-return --disable-error-code=list-item --disable-error-code=dict-item --disable-error-code=type-arg --disable-error-code=misc --disable-error-code=arg-type --disable-error-code=union-attr --disable-error-code=unused-ignore --disable-error-code=import-not-found
python -m compileall -q src/fitcv src/fitcv_cp
python tools/docs/generate_architecture_metadata.py --check
python scripts/generate_planning_lineage.py
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Baseline note: unrestricted focused mypy currently reports 52 existing errors in
`enrich.py` and `ai_score.py` across the disabled codes above. Phase 4 does not
expand into whole-module typing cleanup. Implementation must run unrestricted
mypy before and after edits, remove errors deleted with transport code, and add
no new error code/message in modified runtime seams. Exact mypy remains required
for shared runtime/routing modules.

Residue gates:

```powershell
rg -n "def _build_openai_compat_client|def _make_genai_client|SimpleNamespace|httpx\.Client|/responses|/chat/completions|resolve_model_routing_part|resolve_openai_compatible_api_key" src/fitcv/enrich.py src/fitcv/ai_score.py
rg -n "enrich_extraction|ranking_ai_score" src/fitcv/llm_runtime.py
```

Expected residue result: no active match. Routing-part names belong only in
stage-built requests and control-plane config, not shared-runtime branches.

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

The implementation plan is the next downstream child. Keep this spec `active`
until enrich and ranking use the shared runtime, local transport owners are
deleted, exact-output and batch-policy parity pass, managed docs are synchronized,
and the master Phase 4 entry can move to `completed`.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- `config/runtime/control_plane.yaml`
- `src/fitcv/llm_runtime.py`
- `src/fitcv/runtime_routing.py`
- `src/fitcv/enrich.py`
- `src/fitcv/ai_score.py`
- `docs/stages/enrich.source.yaml`
- `docs/stages/ranking.source.yaml`
- `scripts/validate_planning_lifecycle.py`
</LINK>
