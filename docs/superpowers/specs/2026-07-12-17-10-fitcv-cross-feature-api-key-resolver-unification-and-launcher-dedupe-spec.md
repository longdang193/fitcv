---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv-cross-feature-api-key-resolver-unification-and-launcher-dedupe
parent_thread: workstream-operator-control-plane.fitcv-cp-app-ssot-symmetry-refactor
targets:
  - src/fitcv/runtime_routing.py
  - src/fitcv/ai_score.py
  - src/fitcv/enrich.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/env_defaults.py
  - start_web.ps1
  - start_worker.ps1
  - tests/test_ai_score.py
  - tests/test_enrich.py
  - tests/test_fitcv_cp/test_app.py
  - tests/test_fitcv_cp/test_env_defaults.py
related_features: []
related_stages: []
---

## Goal

Define one SSOT for OpenAI-compatible API-key resolution across enrich, ranking, CV generation, and control-plane runtime inspection, and remove duplicated launcher-side `.env` parsing where it no longer owns unique behavior.

## Key Deliverables

### Shared API-key resolver contract

One canonical Python resolver surface defines accepted env names, precedence, and failure semantics for OpenAI-compatible runtime paths.

This deliverable must also freeze exact resolver function names, caller ownership, accepted env aliases, precedence order, and missing-key error contract so two implementations cannot diverge while both claiming compliance.

### Cross-feature caller migration

All in-scope runtime paths that currently hand-roll API-key lookup read through shared resolver instead of local `os.environ` chains.

### Launcher dedupe boundary

PowerShell launchers stop owning dotenv parsing logic if Python runtime already owns missing-value bootstrap; launcher scripts retain only launcher-specific concerns.

This deliverable must also define required startup/admissible execution cases that must remain symmetric after dedupe.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- inventory current key lookup variants and launcher duplication before changing contracts

**Steps:**
- [ ] enumerate every in-scope API-key lookup path and current env precedence
- [ ] compare runtime consumers against `src/fitcv/runtime_routing.py`
- [ ] identify which launcher behavior is still unique versus duplicated bootstrap
- [ ] enumerate required startup and execution entry cases that must preserve identical dotenv-default semantics

**Verification:**
- [ ] current-state matrix shows caller, accepted env names, precedence, and failure text
- [ ] startup matrix shows entry path, owner, and expected dotenv behavior

**Exit Criteria:**
- no migration decision depends on unstated env behavior

### Wave 2: Decision closure

**Purpose:**
- define shared resolver shape and launcher ownership boundary

**Steps:**
- [ ] choose canonical resolver API and accepted aliases
- [ ] choose migration scope for in-scope callers
- [ ] choose whether launcher dotenv parsing is deleted or reduced to compatibility wrapper

**Verification:**
- [ ] every in-scope caller has explicit target-state ownership

**Exit Criteria:**
- resolver and launcher ownership are symmetric and bounded

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof that SSOT and symmetry improved without changing allowed behavior unintentionally

**Steps:**
- [ ] define targeted tests for resolver precedence and caller reuse
- [ ] define launcher/runtime verification for clean shells and queue/web paths
- [ ] define drift scan for remaining duplicate key lookup code

**Verification:**
- [ ] validation plan can prove both behavior preservation and duplication removal

**Exit Criteria:**
- spec is ready for implementation planning

## Design Decisions

### Decision: `runtime_routing` owns OpenAI-compatible API-key resolution

- context: `src/fitcv/runtime_routing.py` already owns CV-generation routing readiness and one API-key resolver, but enrich, ranking, and control-plane inspection still duplicate env lookup logic.
- choice: extend `src/fitcv/runtime_routing.py` into canonical resolver owner for OpenAI-compatible API-key resolution used by all in-scope features.
- alternatives considered:
  - keep per-feature lookup chains and only document precedence
  - add new config file field for secret material
- impact:
  - in-scope callers import shared resolver/helper instead of reading `os.environ` directly
  - precedence changes become one-file changes with shared tests
  - secret ownership stays env-based; no secret is moved into config files

### Decision: canonical precedence stays compatibility-first, not feature-specific

- context: current callers disagree on accepted env names. CV generation uses `OPENAI_API_KEY` then `OPENAI_COMPATIBLE_API_KEY`; enrich and ranking also accept `FITCV_LLM_API_KEY`; control-plane synonym runtime reads `FITCV_LANGGRAPH_OPENAI_API_KEY` and `OPENAI_API_KEY`.
- choice: define explicit resolver variants instead of one hidden mega-rule:
  - base OpenAI-compatible resolver for general HTTP model calls
  - LangGraph-specific resolver when legacy `FITCV_LANGGRAPH_OPENAI_API_KEY` compatibility must remain
- alternatives considered:
  - force one global precedence list for every caller
  - remove legacy aliases immediately
- impact:
  - symmetry improves without silently breaking existing supported env names
  - legacy aliases remain visible and test-covered
  - future alias deletion can be a separate bounded change

### Decision: resolver contract must be explicit and small

- context: current review found spec-level ambiguity; “shared helper(s)” is too loose to preserve SSOT at design level.
- choice: freeze exactly two resolver functions in `src/fitcv/runtime_routing.py` unless source-first analysis proves one can cover both without alias drift:
  - `resolve_openai_compatible_api_key()`
  - `resolve_langgraph_openai_compatible_api_key()`
- alternatives considered:
  - one generic helper with mode flags
  - unbounded set of caller-specific helpers
- impact:
  - API surface stays tiny
  - caller ownership is explicit
  - precedence can be tested directly without guessing helper semantics

### Decision: precedence matrix is canonical contract, not implementation detail

- context: enrich, ranking, CV generation, and control-plane synonym runtime currently differ in accepted env aliases.
- choice: implementation must preserve or intentionally tighten current supported aliases through one explicit matrix:

| Resolver | Owned callers | Accepted env vars in order |
|---|---|---|
| `resolve_openai_compatible_api_key()` | CV generation, enrich extraction, ranking AI score | `FITCV_LLM_API_KEY`, `OPENAI_API_KEY`, `OPENAI_COMPATIBLE_API_KEY` |
| `resolve_langgraph_openai_compatible_api_key()` | control-plane synonym / LangGraph inspection paths | `FITCV_LANGGRAPH_OPENAI_API_KEY`, `OPENAI_API_KEY`, `OPENAI_COMPATIBLE_API_KEY` |

- alternatives considered:
  - make CV generation keep narrower precedence than enrich/ranking
  - add config-driven alias lists
- impact:
  - accepted aliases become authoritative and testable
  - in-scope direct `os.environ` chains can be deleted safely
  - future alias retirement stays separate and deliberate

### Decision: startup symmetry is defined by explicit admissible cases

- context: launcher dedupe can look correct while still breaking direct import or non-launcher worker paths.
- choice: preserve identical dotenv-default semantics for these admissible entry cases:
  - web startup via `fitcv_cp.main.build_app`
  - worker pipeline execution via `fitcv_cp.worker_job.execute_pipeline_run`
  - worker regenerate-once via `fitcv_cp.worker_job.execute_cv_regenerate_once`
  - local launcher start via `start_web.ps1`
  - local launcher start via `start_worker.ps1`
  - clean-env unit-test import/execution paths for the shared runtime owners
- alternatives considered:
  - define launcher-only symmetry
  - treat test/import paths as incidental
- impact:
  - startup semantics stay uniform across real and verification paths
  - dedupe cannot silently reintroduce worker/web asymmetry

### Decision: launcher scripts should not be primary dotenv truth owner

- context: Python runtime now self-loads `.env` defaults for web and worker. `start_web.ps1` and `start_worker.ps1` still duplicate dotenv parsing.
- choice: reduce launcher scripts to launcher concerns and let Python runtime own missing-value dotenv bootstrap.
- alternatives considered:
  - keep full duplicate PowerShell parsers as harmless redundancy
  - move dotenv ownership entirely to PowerShell and remove Python-side bootstrap
- impact:
  - startup symmetry no longer depends on which shell launched process
  - launcher scripts become smaller and less likely to drift
  - Python import/reuse paths stay correct outside launcher scripts

### Decision: spec stays bounded to key resolution and launcher dedupe only

- context: env/runtime cleanup can sprawl into provider routing, config schema, and secrets UX.
- choice: keep scope to API-key resolver unification and launcher dotenv dedupe for current local runtime paths.
- alternatives considered:
  - fold all provider/env normalization into same change
  - rewrite startup stack around full settings object injection
- impact:
  - shortest safe diff
  - no speculative config layer added

## Invariants

- `.env` remains default-only, process-env wins when key already set.
- No secret value is written into repo config, control-plane YAML, audit docs, or artifacts.
- OpenAI-compatible runtime paths keep working from clean shell launches when repo `.env` contains required key.
- Queue worker and web startup observe same dotenv bootstrap semantics.
- All admissible startup cases named in this spec observe same dotenv-default semantics.
- Caller-specific error messages may be normalized, but missing-key failure still names accepted env vars truthfully.
- Resolver unification must not change non-OpenAI-compatible provider paths.

## Acceptance Criteria

- Every in-scope OpenAI-compatible caller uses one of two named shared resolvers instead of inline `os.environ` chains.
- One targeted test proves resolver precedence for `resolve_openai_compatible_api_key()`.
- One targeted test proves resolver precedence for `resolve_langgraph_openai_compatible_api_key()` if legacy alias remains supported.
- One targeted worker/web bootstrap test proves `.env` default loading symmetry from clean env.
- One targeted test proves `execute_cv_regenerate_once` observes same dotenv-default bootstrap contract as `execute_pipeline_run`.
- `start_web.ps1` and `start_worker.ps1` no longer duplicate full dotenv parsing logic, or spec records exact minimal retained wrapper and why it still must exist.
- Repo scan shows no remaining direct reads of `FITCV_LLM_API_KEY`, `FITCV_LANGGRAPH_OPENAI_API_KEY`, `OPENAI_API_KEY`, or `OPENAI_COMPATIBLE_API_KEY` in in-scope Python callers outside shared resolver owner(s) and explicitly allowed boundary wrappers.

## Non-Goals

- Do not redesign provider routing contracts.
- Do not change `.env` file format.
- Do not add new dependency for dotenv parsing.
- Do not migrate secrets into YAML config.
- Do not unify unrelated env lookups outside OpenAI-compatible runtime paths.

## Risks and Mitigations

- Risk: unifying precedence breaks caller that depended on special-case alias order.
  - mitigation: lock precedence in explicit tests before broad migration.
- Risk: launcher dedupe removes behavior needed for non-Python child process startup.
  - mitigation: inspect actual launcher-only responsibilities first; keep minimal wrapper only if proven necessary.
- Risk: control-plane runtime inspection and execution paths drift if they use different resolver variants.
  - mitigation: document resolver variants explicitly and bind each caller to one named variant.

## Validation Plan

- proof target: shared resolver preserves intended alias precedence
  - method: unit test
  - evidence: targeted tests under `tests/` showing explicit precedence cases for both named resolvers
- proof target: worker and web both bootstrap missing env from `.env`
  - method: unit test
  - evidence: targeted startup/worker tests from clean env covering web, pipeline worker, and regenerate-once worker entry cases
- proof target: enrich, ranking, CV generation, and control-plane synonym runtime no longer split env lookup logic
  - method: inspection
  - evidence: repo grep or review output showing shared resolver imports at each in-scope caller and zero in-scope direct env-key reads outside shared resolver owner(s)
- proof target: launcher duplication is removed without breaking local validation
  - method: inspection + fast validator
  - evidence: reduced launcher scripts and passing `scripts/hooks/run_validator.py --fast`

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`
4. implementation plan derived from this spec is bounded to resolver migration, launcher dedupe, tests, and verification only

Canonical source-of-truth:

- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\docs\operating_system\governance\repo-governance.md`
- `C:\Users\HOANG PHI LONG DANG\repos\JOB-PROJECT\scripts\validate_planning_lifecycle.py`
