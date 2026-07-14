---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-implementation
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
parent_spec: docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md
targets:
  - src/fitcv/llm_runtime.py
  - src/fitcv/runtime_routing.py
  - src/fitcv/openai_compat.py
  - src/fitcv/cv_generator.py
  - src/fitcv/agentic_cv_generation.py
  - config/runtime/control_plane.yaml
  - docs/stages/cv_generation.source.yaml
  - docs/stages/cv_generation.yaml
  - docs/features/cv_system/feature.source.yaml
  - docs/features/cv_system/cv_system.yaml
  - docs/features/cv_system/lineage.generated.yaml
  - docs/features/cv_system/history.md
  - docs/features/settings_system/feature.source.yaml
  - docs/features/settings_system/settings_system.yaml
  - docs/features/settings_system/lineage.generated.yaml
  - docs/features/settings_system/history.md
  - docs/features/inspection_debugging/feature.source.yaml
  - docs/features/inspection_debugging/inspection_debugging.yaml
  - docs/features/inspection_debugging/lineage.generated.yaml
  - docs/features/inspection_debugging/history.md
  - docs/configuration.md
  - docs/pipeline.md
  - docs/architecture.md
  - docs/generated/architecture_dag.yaml
  - docs/generated/capability_lineage.yaml
  - docs/generated/planning_lineage.yaml
  - tests/test_llm_runtime.py
  - tests/test_runtime_routing.py
  - tests/test_cv_generator.py
  - tests/test_pipeline_agentic_late_stage.py
  - tests/test_pipeline.py
  - tests/test_pipeline_stage_resume_parity.py
  - tests/test_enrich.py
  - tests/test_ai_score.py
  - tests/test_fitcv_cp/test_provider_routing.py
  - tests/test_fitcv_cp/test_app.py
related_features:
  - cv_system
  - settings_system
  - inspection_debugging
related_stages:
  - enrich
  - ranking
  - cv_generation
---

# Implementation Plan: FitCV LLM runtime spine Phase 3 shared runtime contract

## Goal

Extract one minimal runtime spine from current CV-generation mechanics without
moving stage meaning into shared code:

`LlmTaskRequest -> resolved route -> adapter -> parse -> validate -> LlmRuntimeResult`

CV generation becomes first production consumer. Direct OpenAI-compatible and
LangGraph writers use same request, adapter-response, runtime parser,
structural validator, failure, and provenance contracts. Enrich and ranking production code remains
unchanged until Phase 4.

This plan is sequential. No implementation execution map is needed because each
task modifies same shared runtime boundary and later tasks depend directly on
earlier contracts.

## Key Deliverables

### Deliverable 1: generic routing with compatibility wrappers

`runtime_routing.py` exposes one generic immutable route and readiness resolver
by routing-part name. Existing CV-specific functions delegate to generic owner
and preserve current behavior.

### Deliverable 2: minimal shared runtime and fake adapter seam

`llm_runtime.py` owns request validation, route/credential resolution, adapter
invocation, parser/validator execution, normalized failure envelope, normalized
provenance, and default OpenAI-compatible transport. Plain callables provide
LangGraph and test adapters; no registry, class hierarchy, plugin loader, or new
dependency is added.

### Deliverable 3: CV generation migrated without semantic drift

Direct and LangGraph CV writers use shared runtime. CV prompt meaning,
normalization, rendering, validation, repair, acceptance, review, statuses,
fingerprints, reuse, persistence, replay, and resume remain owned by existing
CV modules. Superseded CV-local HTTP shims and payload/response handling are
deleted.

### Deliverable 4: executable symmetry proof and Phase 4-safe closeout

Runtime, routing, CV parity, pipeline, replay/resume, enrich, ranking, and
control-plane tests prove shared mechanics and unchanged stage semantics.
Canonical docs and generated metadata identify enrich/ranking migration as
pending Phase 4 work.

## Task/Wave Breakdown

### Task 1: Lock runtime contract with failing tests

**Purpose:**
- freeze request, adapter, result, failure, provenance, and CV parity behavior
  before moving production code

**Files:**
- Create: `tests/test_llm_runtime.py`
- Modify: `tests/test_runtime_routing.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify only to freeze current outputs: `tests/test_enrich.py`
- Modify only to freeze current outputs: `tests/test_ai_score.py`
- Inspect: `src/fitcv/runtime_routing.py`
- Inspect: `src/fitcv/openai_compat.py`
- Inspect: `src/fitcv/cv_generator.py`
- Inspect: `src/fitcv/agentic_cv_generation.py`

**Preconditions:**
- Phase 2 spec and plan are `completed`
- Phase 3 spec is `active`
- baseline repo validator passes
- GitNexus freshness is checked; unavailable/stale results are advisory only for
  exploration, while mandatory per-symbol impact checks run before later edits

**Steps:**
- [x] Add `LlmTaskRequest` validation cases for `text`, `json_object`, and
      `json_schema`, including blank fields, contradictory schema fields, and
      missing schema name/schema.
- [x] Add one plain callable fake adapter supporting deterministic text,
      provider payload, IDs, telemetry, timeout, transport failure, HTTP-like
      failure, and malformed response.
- [x] Add success cases proving execution order: route, adapter, parser,
      validator, normalized result.
- [x] Add result-state matrix cases for parser failure, validator exception,
      invalid validation, routing/adapter failure, and successful validation.
- [x] Add closed failure-matrix cases for routing, credentials, adapter timeout,
      transport, HTTP, adapter contract, parse, and validation failures.
- [x] Add provenance cases proving provider/model/wire API come from route and
      secrets/base URL/raw payload are absent from persisted provenance.
- [x] Add mocked transport cases for both wire APIs, all response modes,
      instructions mapping, SSE/plain JSON decoding, and `/responses` 404
      fallback only, proving schema mode is never downgraded.
- [x] Add generic-route versus CV-wrapper parity fixtures.
- [x] Freeze deterministic direct-versus-LangGraph CV adapter-invariant fields.
- [x] Freeze current enrich and ranking public result shapes without changing
      their production call paths.
- [x] Run new tests before implementation and record failures limited to missing
      Phase 3 contract.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_runtime_routing.py -q`
      fails only because shared contract is not implemented.
- [x] Existing CV, enrich, and ranking baseline tests still pass before source
      changes.

**Exit Criteria:**
- every Phase 3 contract field and failure code has an executable failing proof;
  no test requires SDK-shaped fake clients for new shared-runtime behavior

### Task 2: Generalize routing through existing SSOT

**Purpose:**
- make route resolution reusable by part name without creating second config owner

**Files:**
- Modify: `src/fitcv/runtime_routing.py`
- Verify: `config/runtime/control_plane.yaml`
- Modify: `tests/test_runtime_routing.py`
- Verify: `tests/test_fitcv_cp/test_provider_routing.py`

**Preconditions:**
- Task 1 route tests exist and fail at expected missing symbols
- Run GitNexus impact before editing each existing symbol, including
  `CvGenerationRouting`, `resolve_cv_generation_routing`,
  `resolve_cv_generation_routing_snapshot`, and
  `validate_cv_generation_routing_ready`
- Warn and review before proceeding if any impact result is HIGH or CRITICAL

**Steps:**
- [x] Add generic immutable `LlmRouting` with provider, base URL, wire API,
      model, and timeout fields.
- [x] Add `resolve_llm_routing(part_name, model_fallback="")` using existing
      `resolve_model_routing_part` only.
- [x] Add generic route-readiness validation for supported OpenAI-compatible
      providers and env-only credentials.
- [x] Make CV-specific route type/function/readiness helpers thin compatibility
      wrappers over generic owner; do not keep copied normalization logic.
- [x] Preserve existing LangGraph env override and drift diagnostics as
      compatibility observation paths.
- [x] Keep `config/runtime/control_plane.yaml` unchanged unless source inspection
      finds missing existing route data; do not add new route keys for runtime
      abstraction.

**Verification:**
- [x] `python -m pytest tests/test_runtime_routing.py tests/test_fitcv_cp/test_provider_routing.py -q`
- [x] generic and CV wrapper routes compare equal for configured, fallback, and
      invalid cases.
- [x] `rg -n "def resolve_llm_routing|def resolve_cv_generation_routing" src/fitcv/runtime_routing.py`
      shows generic owner plus thin CV wrapper, with no second config parser.

**Exit Criteria:**
- one generic route owner exists; CV compatibility surface delegates without
  behavior change

### Task 3: Implement minimal shared runtime and default adapter

**Purpose:**
- add shared execution skeleton and OpenAI-compatible transport with no stage meaning

**Files:**
- Create: `src/fitcv/llm_runtime.py`
- Inspect/reuse; modify only if a narrow decoder gap exists: `src/fitcv/openai_compat.py`
- Modify: `tests/test_llm_runtime.py`
- Verify: `src/fitcv/runtime_routing.py`

**Preconditions:**
- Task 2 routing tests pass
- New module carries required Python `@meta` ownership/capability metadata
- Existing `httpx` and stdlib satisfy implementation; no dependency addition

**Steps:**
- [x] Define minimal typed contracts: `LlmTaskRequest`,
      `LlmAdapterResponse`, `LlmValidationResult`, `LlmRuntimeFailure`,
      `LlmRuntimeProvenance`, `LlmRuntimeResult`, and `LlmAdapterError`.
- [x] Use a typed callable alias for adapter injection; do not add adapter base
      class, factory, registry, singleton, or plugin discovery.
- [x] Define parser as `Callable[[LlmAdapterResponse], Any]` and validator as
      `Callable[[Any], LlmValidationResult]`; enforce the spec result-state matrix.
- [x] Validate programmer-owned request fields before operational envelope.
- [x] Resolve route and credential through `runtime_routing.py` only.
- [x] Implement `execute_llm_task` with one order: adapter, parser, validator,
      normalized result.
- [x] Normalize operational exceptions into closed failure codes and preserve
      retryability/HTTP status when known.
- [x] Implement default OpenAI-compatible adapter with `httpx`, existing
      decoders, exact instructions mapping, all response modes, and one
      `/responses` 404 fallback.
- [x] Return provider payload only in in-memory adapter response; never place it
      in provenance or automatic observation output.
- [x] Build provenance from resolved route plus adapter-returned explicit identity,
      IDs, and telemetry; never infer adapter identity from callable names.
- [x] Translate `httpx` timeout, transport, and HTTP failures into
      `LlmAdapterError`; treat unknown exceptions/invalid returns as
      `adapter_contract_error`.
- [x] Keep module imports stage-neutral: no enrich, ranking, CV, pipeline, or
      control-plane app imports.
- [x] Set module `@meta` ownership to
      `cv_system.config-owned-generation-contract` for the Phase 3 consumer set.

**Verification:**
- [x] `python -m pytest tests/test_llm_runtime.py tests/test_runtime_routing.py -q`
- [x] `rg -n "fitcv\.(enrich|ai_score|cv_generator|agentic_cv_generation|pipeline|fitcv_cp)" src/fitcv/llm_runtime.py`
      returns no match.
- [x] `rg -n "enrich_extraction|ranking_ai_score|cv_generation_structured_write" src/fitcv/llm_runtime.py`
      returns no stage-name branches.
- [x] Fake-adapter tests require no environment patching or SDK-shaped client.

**Exit Criteria:**
- shared runtime passes its complete contract/failure matrix and remains stage-neutral

### Task 4: Migrate direct CV writer and delete local HTTP shim

**Purpose:**
- make direct CV generation first production consumer of shared runtime

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Verify: `src/fitcv/openai_compat.py`

**Preconditions:**
- Tasks 1-3 pass runtime and routing tests
- Run GitNexus impact before editing each existing symbol, including
  `_build_openai_compat_client`, `_make_generation_client`,
  `generate_structured_cv`, `generate_cv`, `_execute_generation_attempt`, and
  `generate_from_analysis`
- Warn and review before proceeding if impact is HIGH or CRITICAL

**Steps:**
- [x] Build one CV `LlmTaskRequest` from existing structured prompt,
      instructions, routing part, schema name, and canonical response schema.
- [x] Use `response_mode="json_schema"`, schema name
      `fitcv_structured_cv_document`, canonical schema, and strict transport
      formatting for direct and LangGraph adapters.
- [x] Add thin CV parser callable that consumes `LlmAdapterResponse.raw_text`
      and returns the existing `{structured_cv, markdown}` generated-CV shape.
- [x] Add thin CV structural validator callable that runs
      `validate_structured_cv` and exposes structural admissibility through the
      normalized validation envelope.
- [x] Call `execute_llm_task` for direct initial and repair attempts.
- [x] Make `_execute_generation_attempt` map the runtime result, then run
      `_run_generation_validations` exactly once as stage-owned semantic
      validation before repair or acceptance.
- [x] Map runtime failure envelope to existing CV error stage/message/status;
      preserve current `CvGenerationResult` shape.
- [x] Delete `_build_openai_compat_client`, `_make_generation_client`,
      `SimpleNamespace.models.generate_content` compatibility shim, CV-local
      HTTP payload building, and CV-local response extraction when no callers remain.
- [x] Reuse shared provenance instead of rebuilding direct-provider provenance.
- [x] Preserve prompt text, schema, structured normalization, rendering,
      validation, repair targets, acceptance, review, fingerprints, and reuse.

**Verification:**
- [x] `python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py -q`
- [x] direct CV fixtures retain exact semantic fields after normalizing allowed
      provenance telemetry.
- [x] `rg -n "def _build_openai_compat_client|def _make_generation_client|httpx\.Client|/responses|/chat/completions" src/fitcv/cv_generator.py`
      returns no active transport-owner match.

**Exit Criteria:**
- direct CV writer uses shared runtime and no duplicate OpenAI-compatible client remains

### Task 5: Adapt LangGraph writer to same runtime contract

**Purpose:**
- make LangGraph a shared adapter callable while preserving Phase 2 semantics and trace

**Files:**
- Modify: `src/fitcv/agentic_cv_generation.py`
- Modify: `tests/test_pipeline_agentic_late_stage.py`
- Modify: `tests/test_cv_generator.py`
- Verify: `src/fitcv/llm_runtime.py`
- Verify: `src/fitcv/runtime_routing.py`

**Preconditions:**
- Task 4 direct CV tests pass
- Run GitNexus impact before editing each existing symbol, including
  `_generate_cv_with_live_provider`, `_build_live_provider_generator`,
  `_build_fallback_provider_generator`, `_normalize_runtime_provenance`, and
  `_generate_fresh_from_analysis`
- Warn and review before proceeding if impact is HIGH or CRITICAL

**Steps:**
- [x] Convert LangGraph live writer into adapter callable accepting shared
      request, resolved route, and API key.
- [x] Preserve full decoded provider dictionary in `provider_payload`; extract
      ID/usage/cost metadata, remove only those metadata keys from the business
      payload, and serialize the remainder into `raw_text`.
- [x] Translate native LangGraph provider failures into `LlmAdapterError` at the
      adapter boundary.
- [x] Build LangGraph compatibility env/config by overwriting route-owned values
      and `OPENAI_API_KEY` from resolved route/API key; retain process env only
      for adapter-local retry/debug settings.
- [x] Route LangGraph initial and repair attempts through `execute_llm_task`
      using same CV runtime parser and structural validator as direct path; keep
      `_run_generation_validations` as the single post-runtime semantic check.
- [x] Preserve existing trace attempts, retry reason, latency, validation cycle,
      repair summary, and error observation as projections of shared result plus
      adapter telemetry.
- [x] Remove duplicate provenance assembly and failure classification superseded
      by shared runtime.
- [x] Keep LangGraph availability/transport selection observational; mode labels
      remain excluded from fingerprint and semantic decisions.

**Verification:**
- [x] `python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py -q`
- [x] deterministic direct/LangGraph comparison differs only in adapter,
      runtime path, IDs, attempt count, latency, and adapter-local telemetry.
- [x] Phase 2 review, validation failure, generation failure, repair, and trace
      fixtures remain green.

**Exit Criteria:**
- both CV adapters use one shared request/parser/structural-validator/result
  contract, semantic validation runs once in stage owner, and LangGraph owns no
  business meaning

### Task 6: Prove no semantic drift and close lifecycle

**Purpose:**
- verify shared extraction, preserve Phase 4 boundary, synchronize docs, and close Phase 3

**Files:**
- Verify: `tests/test_pipeline.py`
- Verify: `tests/test_pipeline_stage_resume_parity.py`
- Verify: `tests/test_enrich.py`
- Verify: `tests/test_ai_score.py`
- Verify: `tests/test_fitcv_cp/test_provider_routing.py`
- Verify/modify if stale: `tests/test_fitcv_cp/test_app.py`
- Modify if runtime-boundary wording is stale: `docs/stages/cv_generation.source.yaml`
- Generated if stage source changes: `docs/stages/cv_generation.yaml`
- Modify only if capability ownership changes:
  `docs/features/cv_system/feature.source.yaml`
- Modify only if capability ownership changes:
  `docs/features/settings_system/feature.source.yaml`
- Modify only if capability ownership changes:
  `docs/features/inspection_debugging/feature.source.yaml`
- Generated from metadata/source changes: corresponding feature contracts,
  lineage, and generated history blocks
- Modify if stale: `docs/configuration.md`
- Modify if stale: `docs/pipeline.md`
- Modify if stale: `docs/architecture.md`
- Generated if architecture metadata changes:
  `docs/generated/architecture_dag.yaml`
- Generated if architecture metadata changes:
  `docs/generated/capability_lineage.yaml`
- Generated after lifecycle changes: `docs/generated/planning_lineage.yaml`
- Modify at closeout:
  `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- Modify at closeout:
  `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- Modify at closeout:
  `docs/superpowers/plans/2026-07-14-17-58-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-plan.md`

**Preconditions:**
- Tasks 1-5 pass focused tests
- No enrich or ranking production file changed unless separately approved as
  Phase 4 work

**Steps:**
- [x] Run full runtime, routing, CV, pipeline, replay/resume, enrich, ranking,
      provider-routing, and relevant control-plane suites.
- [x] Confirm enrich/ranking results remain unchanged and still use local client
      builders pending Phase 4.
- [x] Run residue gates for CV-local transport code and stage imports/branches in
      shared runtime.
- [x] Inspect stage/feature/cross-cutting docs; edit human-owned sources only
      where owner wording is stale.
- [x] Run architecture metadata generator when metadata/source changes; never
      hand-edit generated YAML.
- [x] Regenerate planning lineage after plan creation and lifecycle transitions.
- [x] Run focused mypy, compile, repo contracts, architecture check, planning
      lifecycle, and diff checks.
- [x] Run `gitnexus_detect_changes(scope="all")` before commit and review
      affected processes; treat stale graph paths as advisory and source/tests as
      authority.
- [x] After all proof passes, mark Phase 3 plan/spec/master entry `completed`.

**Verification:**
- [x] all commands in top-level Verification pass
- [x] no unexpected production changes exist in `src/fitcv/enrich.py` or
      `src/fitcv/ai_score.py`
- [x] docs state enrich/ranking migration remains Phase 4
- [x] generated files match canonical sources and metadata

**Exit Criteria:**
- Phase 3 is implemented, verified, documented, and ready to hand off to Phase 4 spec drafting

## Verification

Run after all tasks:

```powershell
python -m pytest tests/test_llm_runtime.py tests/test_runtime_routing.py tests/test_fitcv_cp/test_provider_routing.py -q
python -m pytest tests/test_cv_generator.py tests/test_pipeline_agentic_late_stage.py -q
python -m pytest tests/test_pipeline.py tests/test_pipeline_stage_resume_parity.py -q
python -m pytest tests/test_enrich.py tests/test_ai_score.py -q
python -m pytest tests/test_fitcv_cp/test_app.py -k "provider or routing or cv_generation or late_stage" -q
python -m mypy src/fitcv/llm_runtime.py src/fitcv/runtime_routing.py src/fitcv/agentic_cv_generation.py --follow-imports=skip --show-error-codes
python -m mypy src/fitcv/cv_generator.py --follow-imports=skip --show-error-codes --disable-error-code=no-any-return
python -m compileall -q src/fitcv src/fitcv_cp
python tools/docs/generate_architecture_metadata.py --check
python scripts/generate_planning_lineage.py
python scripts/validate_planning_lifecycle.py
python scripts/validate_repo_contracts.py --fast
git diff --check
```

Residue gates:

```powershell
rg -n "def _build_openai_compat_client|def _make_generation_client|httpx\.Client|/responses|/chat/completions" src/fitcv/cv_generator.py
rg -n "fitcv\.(enrich|ai_score|cv_generator|agentic_cv_generation|pipeline|fitcv_cp)" src/fitcv/llm_runtime.py
rg -n "enrich_extraction|ranking_ai_score|cv_generation_structured_write" src/fitcv/llm_runtime.py
```

Expected residue result: no active match. Routing-part names belong in stage-built
requests and control-plane config, not shared-runtime branches.

Run GitNexus freshness before implementation and `gitnexus_detect_changes` at
closeout. Before modifying any existing function, class, or method, run upstream
impact analysis for that symbol and stop for user warning on HIGH or CRITICAL
risk.

The unrestricted focused mypy command also reports six existing
`no-any-return` findings in unchanged `cv_generator.py` lines 1015, 1019, 1330,
1376, 1416, and 1506. Phase 3 does not expand scope to fix that existing debt;
the split focused commands above prove all changed modules and all other
`cv_generator.py` error categories clean.

## Completion Evidence

- runtime/routing/provider suites: 30 passed
- CV/direct/LangGraph suites: 71 passed
- pipeline/replay/resume suites: 129 passed
- enrich/ranking suites: 111 passed, 1 skipped
- control-plane routing/CV suites: 18 passed, 493 deselected
- compile, residue, architecture, planning lifecycle, repo-contract, and diff
  gates: passed
- enrich/ranking production files: unchanged; Phase 4 migration boundary preserved
- GitNexus closeout: graph unavailable/stale and reported unrelated pipeline
  symbols absent from Git diff; source, tests, and active docs used as authority
- audit bypass: stale provider-routing test literal was test-only typo drift with
  no behavior impact; assertion now reads model from control-plane SSOT

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

This plan has no child plans. Shared-runtime and regression suites pass, CV
duplicate transport owners are deleted, direct and LangGraph adapter-invariant
fields match, enrich/ranking production code remains unchanged, canonical docs
are synchronized, and Phase 3 lifecycle entries are `completed`.

Canonical source-of-truth:

<LINK>
- `docs/superpowers/specs/2026-07-14-17-39-fitcv-llm-runtime-spine-phase-3-shared-runtime-contract-spec.md`
- `docs/superpowers/specs/2026-07-14-12-13-fitcv-llm-runtime-spine-master-spec.md`
- `config/runtime/control_plane.yaml`
- `src/fitcv/runtime_routing.py`
- `src/fitcv/openai_compat.py`
- `src/fitcv/agentic_cv_generation.py`
- `scripts/validate_planning_lifecycle.py`
</LINK>
