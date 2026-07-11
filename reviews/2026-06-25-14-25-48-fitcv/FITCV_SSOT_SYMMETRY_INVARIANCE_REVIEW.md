# FitCV SSOT, Symmetry, and Invariance Review

## Scope and validation

Reviewed all 40 Python files in the supplied archive (27,651 LOC, 860 functions/classes).

Static validation performed:

- all files compile with `python -m py_compile`;
- 18 exact duplicate function-body groups were detected across modules (38 function instances);
- no test files were included in the archive;
- the archive references `fitcv.prompts` and `fitcv.pipeline_stages.common`, but those modules were not included, so end-to-end imports and runtime tests could not be executed.

## Executive assessment

The codebase has several intended SSOT modules (`ranking_contract.py`, `candidate_name_policy.py`, `placeholder_policy.py`, `persistence.py`, `pipeline_stage_context.py`, `runtime_routing.py`), but the migration is incomplete. Old implementations remain active beside the new owners. The largest risk is not simple duplication; it is **branch-dependent behavior**: the result changes depending on which orchestration path, backend, runtime provider, reuse route, or compatibility surface is used.

The highest-priority invariant should be:

> For the same normalized inputs and effective configuration, every execution path must produce the same decisions, status taxonomy, provenance, and persistence contract, regardless of backend, resume/reuse mode, or provider adapter.

That invariant is currently not guaranteed.

---

# Critical findings

## C1. Two pipeline orchestrators own the same stage behavior

**Evidence**

- `pipeline.py` is a 6,979-line orchestrator and executes normalization, enrichment, filtering, shortlist, ranking, analysis, and generation inline (`pipeline.py:3847`, `3991`, `4063`, `4283`, and later branches).
- `pipeline_stage_runner.py` independently defines `execute_normalize_stage`, `execute_enrich_stage`, `execute_rule_filter_stage`, `execute_shortlist_stage`, `execute_ranking_stage`, and late-stage handlers (`pipeline_stage_runner.py:29-1238`).
- No other file imports or calls the stage-runner functions.
- `pipeline.py` also retains duplicate late-stage helpers that exist in `agentic_cv_analysis.py`, `agentic_cv_generation.py`, `pipeline_observability.py`, and `pipeline_stage_artifacts.py`.

**Violation**

- **SSOT:** stage semantics have two owners.
- **Symmetry:** fixes applied to the extracted runner do not affect the live pipeline.
- **Invariance:** inline and extracted execution can diverge in reuse, telemetry, cancellation, error handling, or persistence behavior.

**Patch**

1. Make `pipeline.py` orchestration-only.
2. Call `pipeline_stage_runner.execute_*` for every stage.
3. Move all nested late-stage handlers into the runner or dedicated services.
4. Delete local duplicates after characterization tests prove parity.
5. Add one contract test per stage comparing fresh, resumed, and reused execution.

Suggested target:

```python
STAGE_EXECUTORS: dict[PipelineStage, StageExecutor] = {
    PipelineStage.NORMALIZE: execute_normalize_stage,
    PipelineStage.ENRICH: execute_enrich_stage,
    PipelineStage.RULE_FILTER: execute_rule_filter_stage,
    PipelineStage.SHORTLIST: execute_shortlist_stage,
    PipelineStage.RANKING: execute_ranking_stage,
    PipelineStage.CV_ANALYSIS: execute_cv_analysis_stage,
    PipelineStage.CV_GENERATION: execute_cv_generation_stage,
}
```

`pipeline.py` should choose stages and manage lifecycle; it should not reimplement stage internals.

---

## C2. Checkpoint completion is inferred from non-empty data instead of explicit stage state

**Evidence**

- `PipelineState.CHECKPOINT_SCHEMA_VERSION` exists (`pipeline_stage_context.py:26`).
- `from_checkpoint_payload` originally ignored `schema_version` (`pipeline_stage_context.py:47-65`).
- `infer_last_completed_stage_from_state` treats a stage as complete only when one of its output collections is non-empty (`pipeline_stage_context.py:112-128`).
- `cv_generation` was omitted entirely from the inference order.
- `_canonical_resume_start_stage` trusts this inference to decide where execution resumes (`pipeline.py:1347-1362`).
- State ownership is manually repeated in dataclass fields, `payload_keys()`, and `as_state_dict()` (`pipeline_stage_context.py:25-109`).

**Violation**

- A correctly completed stage with zero outputs is indistinguishable from a stage that never ran.
- A completed CV-generation checkpoint can resume from the wrong stage.
- A future checkpoint schema can be silently interpreted as the current schema.
- Adding a state field requires synchronized edits in three locations.

**Patch**

Persist explicit lifecycle metadata:

```python
@dataclass
class PipelineCheckpoint:
    schema_version: int
    run_id: str
    last_completed_stage: PipelineStage | None
    completed_stages: tuple[PipelineStage, ...]
    state: PipelineState
```

Rules:

- `last_completed_stage` is authoritative.
- data-based inference is legacy-only migration logic;
- reject unsupported schema versions;
- serialize state fields using `dataclasses.fields()` or one explicit field registry, not three manual lists;
- validate prerequisites before resuming a requested stage.

The immediate patch included with this review validates the schema when present and adds `cv_generation` to legacy inference. It does **not** solve the zero-output ambiguity; that needs the explicit metadata migration above.

---

## C3. CV LangGraph routing combines fields from two different model routes

**Evidence**

`runtime_routing.build_langgraph_env_overrides()` reads:

- provider, base URL, and wire API from `enrich_extraction`;
- model from `cv_generation_structured_write`.

See `runtime_routing.py:54-74`.

Additional routing asymmetries:

- enrichment accepts `FITCV_LLM_API_KEY`, ranking and CV generation originally did not (`enrich.py:1608-1627`, `ai_score.py:248-256`, `runtime_routing.py:77-81`);
- ranking and CV generation fall back from `/responses` to `/chat/completions` on HTTP 404, enrichment does not (`ai_score.py:274-310`, `cv_generator.py:121-155`, `enrich.py:1646-1674`);
- `validate_cv_generation_routing_ready` originally allowed unsupported providers to pass preflight, while execution rejected them (`runtime_routing.py:113-127`, `cv_generator.py:88-109`);
- provenance swallowed routing errors and reported a built-in path that execution did not actually use (`runtime_routing.py:84-110`).

**Violation**

One logical route can produce a provider/base URL from one stage and a model from another. Preflight, provenance, and execution can disagree.

**Patch**

Create one route object and one HTTP adapter:

```python
@dataclass(frozen=True)
class LlmRoute:
    part: str
    provider: Provider
    model: str
    base_url: str
    wire_api: WireApi
    timeout_seconds: float

class OpenAICompatibleClient:
    def generate_json(self, route: LlmRoute, prompt: str) -> dict[str, Any]: ...
```

All stages should share:

- API-key precedence;
- URL construction;
- response decoding;
- `/responses` compatibility fallback;
- retry/timeout policy;
- provider validation;
- provenance fields.

The immediate patch fixes the mixed route, aligns API-key precedence, rejects unsupported providers at preflight, and makes unresolved provenance explicit.

---

## C4. Deterministic embedding fallback is cached as though it were a Vertex embedding

**Evidence**

- SQLite uses a deterministic 256-dimensional hash embedding (`embeddings.py:41`, `330-336`).
- Outside SQLite, provider failures default to the same deterministic fallback (`embeddings.py:339-388`).
- The embedding contract fingerprint includes only configured model and summary schema (`embeddings.py:121-131`).
- Stored records are marked `fresh_embedding`, regardless of whether the vector came from Vertex or the local fallback (`embeddings.py:525-536`).
- Reuse checks only input signature and contract fingerprint (`embeddings.py:518-524`).

**Violation**

A fallback vector can be persisted under a `text-embedding-005` contract and later reused as if it were a real provider vector. Mixed dimensions or mixed vector spaces can break similarity calculations or silently corrupt ranking.

**Patch**

Return an explicit result:

```python
@dataclass(frozen=True)
class EmbeddingResult:
    vector: list[float]
    backend: Literal["vertex", "deterministic_local"]
    model: str
    dimension: int
    fallback_used: bool
```

Then:

- include backend, model, dimension, and algorithm version in the fingerprint;
- never store a local fallback under a Vertex contract;
- use `raise` as the default outside SQLite, or require an explicit degraded-mode flag;
- verify query/document vector dimensions before similarity search;
- expose fallback usage in stage status and telemetry.

Required invariant:

```text
reusable_embedding.backend == requested_embedding.backend
AND reusable_embedding.dimension == requested_embedding.dimension
AND reusable_embedding.contract_fingerprint == current_contract_fingerprint
```

---

## C5. Role-family neighbor taxonomy has conflicting paths and is ignored by evidence scoring

**Evidence**

- `_normalize_role_taxonomy` stores neighbors under `role_taxonomy.role_family_neighbors` (`config.py:486-538`).
- runtime synonym overlays merge neighbors into top-level `role_family_neighbors` (`config.py:591-658`).
- `load_config` separately normalizes the top-level key (`config.py:1028`).
- ranking originally read only the nested key (`ranking.py:100-112`).
- evidence imported the private ranking resolver and called it **without config**, so it always received an empty map (`evidence.py:50`, `1177-1187`).
- evidence also called `infer_role_family(job_title)` without config, bypassing configured role taxonomy (`evidence.py:1177-1180`).

**Violation**

- overlay behavior differs from base-taxonomy behavior;
- ranking and evidence can score the same role-family relationship differently;
- configured neighbor relationships can be completely ignored in CV evidence selection.

**Patch**

Create a public taxonomy API:

```python
class Taxonomy:
    def canonical_role(self, value: str) -> str | None: ...
    def role_family(self, value: str) -> str | None: ...
    def role_family_neighbors(self, family: str) -> frozenset[str]: ...
```

Canonical storage should be one path, preferably:

```yaml
role_taxonomy:
  canonical_role_by_alias: ...
  role_family_by_role: ...
  role_family_neighbors: ...
```

Runtime overlays should update that nested structure rather than create a top-level second owner.

The immediate patch accepts both paths during migration and passes config into evidence role scoring.

---

## C6. Persistence settings and clients do not have one owner

**Evidence**

- `resolve_data_backend` reads canonical control-plane backend type (`config.py:223-265`).
- SQLite path helpers read only `FITCV_CP_SQLITE_PATH` or a hard-coded default and do not read `control_plane.data_backend.sqlite.path` (`persistence.py:22-23`, `shortlist_runtime.py:30-31`, `enrich.py:2300-2301`, `evidence.py:1864-1865`).
- identical SQLite path bodies exist in four modules.
- BigQuery client construction exists in `persistence.py`, `shortlist_runtime.py`, and inline in `enrich.py`, `evidence.py`, `candidate.py`, and `rule_filter.py`.
- SQLite connection pragmas and retry policy are centralized only for shortlist-related modules; other modules open connections independently.

**Violation**

Backend type may come from control-plane configuration while backend location comes from an unrelated environment/default path. Connection, retry, credential, and schema behavior depend on the calling module.

**Patch**

Introduce one runtime object:

```python
@dataclass(frozen=True)
class StorageRuntime:
    backend: Literal["sqlite", "bigquery"]
    sqlite_path: Path | None
    gcp_project: str | None
    bigquery_dataset: str | None
    credentials_path: Path | None
```

Resolve it once during startup and inject it into repositories. Replace module-level backend branching with repository methods:

```python
class PipelineRepository(Protocol):
    def store_raw_jobs(...): ...
    def store_structured_jobs(...): ...
    def store_ranking(...): ...
    def store_cv_version(...): ...
```

Environment variables may override values, but the resolved runtime object must be the only value read by downstream code.

---

# High-severity findings

## H1. Status and error contracts are scattered

Examples:

- analysis statuses in `agentic_cv_analysis.py:30-43` and again in `pipeline.py:230-235`;
- generation statuses in `agentic_cv_generation.py:62-70`, with additional `review_required` and `persistence_failed` statuses introduced only in `pipeline.py`;
- `ErrorPayload` is defined separately in analysis and generation modules;
- fit-label constants and mapping exist in `ranking_contract.py`, but analysis reimplemented threshold mapping (`agentic_cv_analysis.py:134-152`);
- pipeline quality metrics compare raw string literals (`pipeline.py:2960-3047`).

**Patch**

Move all states into `contracts.py` or focused contract modules:

```python
class AnalysisStatus(str, Enum): ...
class GenerationStatus(str, Enum): ...
class PipelineStage(str, Enum): ...
class ReuseStatus(str, Enum): ...
class ValidationStatus(str, Enum): ...

class ErrorPayload(TypedDict):
    stage: PipelineStage
    code: str
    message: str
```

Use exhaustive transition functions and reject unknown values. The immediate patch routes fallback fit-label computation through `ranking_contract.fit_label_from_score`.

---

## H2. Two reuse engines and several fingerprint laws coexist

**Evidence**

- `reuse.py` owns stage policy and decision envelopes and is used by `pipeline.py`.
- `reuse_law_engine.py` defines a different identity/gate/provenance model and is not imported anywhere.
- fingerprint canonicalization differs:
  - `shortlist_runtime.canonicalize_for_hash` case-folds all strings;
  - `evidence._stable_json_fingerprint` trims strings but preserves case;
  - `ai_score._stable_json_fingerprint` hashes raw values;
  - `reuse_law_engine._sha256_json` uses another raw JSON hash.

**Violation**

“Exact match” means different things by stage. A harmless case change can invalidate one cache and not another; an order/casing change can be silently normalized elsewhere.

**Patch**

Retain one reuse engine with explicitly named canonicalization laws:

```python
FingerprintLaw.EXACT_JSON
FingerprintLaw.NORMALIZED_TEXT
FingerprintLaw.ORDER_INSENSITIVE_SET
```

Each contract fingerprint must declare its law and schema version. Delete or migrate `reuse_law_engine.py`; do not leave both marked active.

---

## H3. Placeholder and section policies remain duplicated

**Evidence**

- generic placeholder SSOT: `placeholder_policy.py:20-39`;
- certification-specific placeholder set: `section_policy.py:27-50`;
- education placeholder constant in `cv_generator.py:77-86` is separate and unused;
- candidate-name policy is duplicated in `pipeline.py:223-226`, `1620-1639` despite `candidate_name_policy.py`;
- `_section_enabled` is duplicated in `section_policy.py:53-58` and `cv_generator.py:1123-1128`;
- validator contains an unused `_normalize_placeholder_name_token` (`validator.py:270-273`).

**Patch**

Use one policy module with contextual sets:

```python
PLACEHOLDERS = {
    PlaceholderContext.GENERIC: frozenset(...),
    PlaceholderContext.CERTIFICATION: frozenset(...),
    PlaceholderContext.CANDIDATE_NAME: frozenset(...),
}
```

Expose public `section_enabled(config, section_key)` and remove wrappers/private copies.

---

## H4. Configuration is called SSOT but defaults to compatibility precedence

**Evidence**

- `load_config` states that `.env.yaml` always wins (`config.py:910-919`).
- canonical ownership overlaps only warn by default (`config.py:970-1021`).
- policy files only backfill missing keys (`config.py:1003-1014`).
- nested CV configuration is projected back into flat legacy keys (`config.py:1126-1154`).
- getters often read flat values first (`config.py:1157-1191`).

**Violation**

Canonical policy files are not authoritative while default mode is `warn`; compatibility values can override them and become the effective behavior.

**Patch**

- make strict ownership the default in production;
- parse legacy config into a separate `LegacyConfigInput`;
- migrate once into `EffectiveConfig`;
- prohibit downstream reads of legacy keys;
- remove `apply_cv_compatibility_projection` after migration;
- expose the resolved effective config and its provenance in diagnostics.

---

## H5. BigQuery and SQLite persistence do not preserve the same record contract

**Evidence**

- SQLite CV version persistence uses the full record (`tracker.py:171-182`).
- BigQuery retries with a “legacy” record that removes structured CV, model, prompt, fingerprint, and reuse fields when columns are missing (`tracker.py:98-129`, `189-194`).

**Violation**

A successful `store_cv_version` call can mean different persisted information depending on backend/schema age. Reuse and provenance invariants no longer hold.

**Patch**

Do not silently downgrade a canonical record. Either:

1. require schema migration and fail fast; or
2. persist an explicit degraded envelope with `schema_compatibility_status`, rejected fields, and a non-success stage outcome.

The same logical record schema should be validated before either backend write.

---

## H6. Shared modules expose private implementation details

- `evidence.py` imports `_normalize_text` and `_role_family_neighbors` from `ranking.py`.
- `agentic_cv_generation.py` imports `_normalize_structured_cv` and `_resolve_template_path` from `cv_generator.py`.

Private imports indicate that ownership boundaries are not real and make refactors unsafe.

**Patch**

Move these into public policy/contract modules (`taxonomy.py`, `structured_cv_contract.py`, `template_registry.py`) and import public names only.

---

# Medium findings and cleanup

1. `cv_generator.py` imports the same runtime-routing symbols twice (`cv_generator.py:53` and `60`). The immediate patch removes the duplicate.
2. `config.py` largely acts as a façade around `config_loader.py`, `config_validators.py`, and `config_compat.py`, but also owns substantial parsing and compatibility behavior. Define whether it is the façade or the implementation and keep only one layer of private wrappers.
3. `pipeline.py` contains numerous wrappers that simply delegate to extracted modules. Temporary wrappers should have removal dates/tests, otherwise both names become permanent APIs.
4. There are 37 broad `except Exception` blocks. Several are appropriate for telemetry boundaries, but routing/config/provider paths should not silently convert configuration errors into fallback behavior.
5. Module metadata frequently says “Module metadata placeholder” rather than the actual responsibility, weakening ownership documentation.
6. No tests were included. At minimum, add contract tests for configuration ownership, backend parity, resume of zero-result stages, reuse invalidation, provider routing, and status transition exhaustiveness.

---

# Recommended patch order

## Phase 1 — correctness blockers

1. Fix CV route mixing and shared API-key/provider validation.
2. Fix role-family neighbor config propagation.
3. Route all fit-label decisions through `ranking_contract`.
4. Reject incompatible checkpoint schema; add explicit completion metadata.
5. Prevent deterministic fallback embeddings from sharing provider fingerprints.

## Phase 2 — establish canonical owners

1. `contracts.py`: stages, statuses, errors, transition rules.
2. `taxonomy.py`: role/domain/skill normalization and neighbors.
3. `runtime_routing.py` + `llm_client.py`: route resolution and HTTP execution.
4. `storage_runtime.py` + repositories: backend resolution and persistence.
5. `reuse.py`: identity, fingerprint laws, decision, provenance.
6. `placeholder_policy.py`: all placeholder contexts and section enablement.

## Phase 3 — remove parallel paths

1. Make `pipeline.py` call `pipeline_stage_runner.py` exclusively.
2. Remove duplicate helpers after tests demonstrate parity.
3. Remove legacy config projections and unused compatibility modules.
4. Enforce no private cross-module imports.

---

# Acceptance invariants

Add tests asserting all of the following:

```text
1. Fresh execution == resumed execution == exact-reuse execution
   for decision/status/provenance, excluding timestamps and reuse metadata.

2. SQLite and BigQuery persist the same canonical record fields.

3. A completed zero-result stage resumes after that stage, not before it.

4. Every persisted/reused vector has matching backend, model, dimension,
   algorithm version, and contract fingerprint.

5. The same role-family neighbor map is used by ranking, evidence selection,
   candidate inference, and diagnostics.

6. Preflight routing, runtime routing, and reported provenance are identical.

7. Every status belongs to one enum and every state transition is exhaustive.

8. Effective configuration has exactly one owner per semantic key.
```

## Immediate patch included

`fitcv_ssot_immediate.patch` contains narrow, compile-checked fixes for:

- mixed LangGraph route fields;
- API-key precedence and provider preflight;
- truthful unresolved routing provenance;
- fit-label SSOT delegation;
- top-level/nested role-family neighbor compatibility;
- config propagation into evidence role scoring;
- duplicate import removal;
- checkpoint schema validation and legacy `cv_generation` inference.

This patch is intentionally limited. It does not attempt the larger orchestrator, storage, checkpoint-metadata, or embedding-contract migrations without the missing package modules and tests.
