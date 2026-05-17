---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: ai-plane-unification-and-backend-symmetry
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
targets:
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - src/fitcv/config.py
  - src/fitcv/enrich.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv_cp/worker_job.py
  - docs/configuration.md
  - docs/pipeline.md
  - tests/
related_features:
  - cv_system
  - trigger_run_management
  - settings_system
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define migration that deprecates Gemini- and account-key-owned AI execution paths while preserving BigQuery and SQLite as symmetric data-plane backends. Guarantee symmetry, invariance, equivalence, and single source of truth for AI runtime behavior.

## Key Deliverables

### Deliverable 1: Unified AI-plane contract

One canonical AI contract where provider/model routing and auth are backend-agnostic and stage-consistent.

### Deliverable 2: Data-plane symmetry boundary

Explicit boundary where BigQuery and SQLite differences are limited to persistence and query adapters, never AI decision logic.

### Deliverable 3: Legacy compatibility retirement protocol

Bounded deprecation path for legacy fields and paths (`gemini_model`, flat `cv_generation_model` compatibility projection, non-agentic AI runtime branch, account-key AI auth) with measurable removal gates.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- define current asymmetric behavior and legacy ownership overlaps before committing migration decisions

**Steps:**
- [ ] inventory AI-stage runtime path differences across `enrich`, `ranking_ai_score`, `cv_analysis`, `cv_generation`
- [ ] inventory auth source differences (`FITCV_LLM_API_KEY`, `OPENAI_API_KEY`, `OPENAI_COMPATIBLE_API_KEY`, `service_account_key`)
- [ ] inventory backend-coupled AI branches and metadata-only compatibility fields that appear runtime-authoritative
- [ ] classify each difference as allowed data-plane variation vs prohibited AI-plane variation

**Verification:**
- [ ] asymmetry register exists with exact source path for each violation candidate

**Exit Criteria:**
- no migration decision depends on unstated current-state behavior

### Wave 2: Decision closure

**Purpose:**
- select final architecture and deprecation semantics that enforce principles as runtime invariants

**Steps:**
- [ ] lock AI-plane SSOT ownership to control-plane routing and env-key auth contract
- [ ] lock backend role to persistence substrate only
- [ ] define stage-by-stage acceptance parity expectations
- [ ] define compatibility windows and irreversible removal gates

**Verification:**
- [ ] each high-impact decision includes rationale, alternatives, and downstream impact

**Exit Criteria:**
- migration design is internally coherent and testable

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof that migration preserves symmetry, invariance, and equivalence under sqlite and bigquery modes

**Steps:**
- [ ] define parity test matrix and trace-level evidence requirements
- [ ] define negative tests for rejected auth/legacy paths
- [ ] define completion gates for config/docs/test/telemetry alignment

**Verification:**
- [ ] validation plan can reject partial migration that leaves legacy runtime ownership ambiguous

**Exit Criteria:**
- spec ready for implementation planning handoff

## Design Decisions

### Decision: Two-plane architecture with strict ownership boundary

- context: current runtime still mixes backend, auth, and legacy model semantics in some AI paths
- choice: enforce hard split: `data_plane` (`sqlite|bigquery`) for storage only; `ai_plane` for provider/model/auth only
- alternatives considered:
  - keep dual path and relabel UI only
  - remove BigQuery entirely
- impact:
  - backend switch cannot change AI provider/model/decision path
  - BigQuery retained as symmetric storage backend with SQLite

### Decision: Canonical AI auth is API key only

- context: account/service key currently appears in runtime config and can leak as perceived AI credential ownership
- choice: AI calls require API key contract with canonical key `FITCV_LLM_API_KEY`; short transition may accept aliases with warnings
- alternatives considered:
  - stage-specific key contracts
  - allow account_key fallback for AI
- impact:
  - AI auth invariant becomes stage-consistent
  - account/service key remains valid only for BigQuery data-plane auth

### Decision: Remove legacy non-agentic AI runtime branch

- context: `agentic` vs `non_agentic` late-stage mode causes path-dependent behavior and operator confusion
- choice: single AI execution path for generation/analysis/reranking/enrichment decisions; no mode-based AI branching
- alternatives considered:
  - keep non-agentic as hidden fallback
- impact:
  - stronger equivalence guarantees
  - cleaner tracing and settings interpretation

### Decision: AI model SSOT is control-plane routing only

- context: fallback and compatibility projection fields (`gemini_model`, flat `cv_generation_model`) create multi-owner ambiguity
- choice: `control_plane.model_routing.parts.*` is sole owner for runtime provider/model selection
- alternatives considered:
  - preserve pipeline-level model fallback defaults indefinitely
- impact:
  - fail-fast when routing unresolved
  - settings and telemetry can report single authoritative source

### Decision: Explicit deprecation lifecycle with hard removal gates

- context: abrupt cutover increases outage risk; indefinite compatibility increases invariance drift risk
- choice: phased migration with warning phase, block phase, removal phase; each phase requires explicit evidence gates
- alternatives considered:
  - one-step hard cutover
  - no sunset timeline
- impact:
  - safer rollout with bounded legacy duration
  - prevents permanent dual-ownership reintroduction

## Invariants

- AI-stage runtime behavior is independent of `FITCV_CP_DATA_BACKEND`.
- Backend selection affects persistence/query adapter only.
- Every AI stage resolves provider/model from `control_plane.model_routing.parts.<stage_part>`.
- AI auth uses API key contract only; account/service key is not consumed by AI clients.
- Effective run snapshot and trace expose resolved `{provider, model, auth_source, routing_source}`.
- Metadata-only or compatibility fields must never override runtime-resolved AI routing.
- Missing required AI routing or API key fails fast with deterministic error.

## Acceptance Criteria

- For fixed fixtures and deterministic test doubles, sqlite and bigquery runs produce identical AI-stage decisions/status payloads; only storage metadata differs.
- No AI stage succeeds when only `service_account_key` is present and API key is absent.
- No runtime path defaults to Gemini model when routing is unset; system raises configuration error.
- UI and `settings-used` artifacts show single runtime-authoritative AI model source.
- `late_stage_mode` no longer introduces non-agentic AI decision branch.

## Non-Goals

- Removing BigQuery as data backend.
- Rewriting unrelated ranking heuristics or acceptance policy math.
- Redesigning business taxonomy or prompt semantics beyond routing/auth ownership.
- Expanding public mirror publication scope for private operating-system artifacts.

## Risks and Mitigations

- Risk: hidden consumers depend on legacy flat keys or non-agentic mode.
  - mitigation: staged warnings, compatibility telemetry counters, explicit removal gate tests.
- Risk: mixed envs rely on `OPENAI_API_KEY` aliases.
  - mitigation: alias transition window with warning and clear sunset release criteria.
- Risk: parity drift between sqlite and bigquery due to adapter-side side effects.
  - mitigation: backend A/B parity suite with strict artifact diff contract and trace assertions.
- Risk: docs/settings drift causes operator misuse.
  - mitigation: same PR updates for config docs, settings labels, and runtime evidence schema tests.

## Validation Plan

- proof target: AI path symmetry across backends
  - method: run parity integration tests for same input across sqlite and bigquery with mocked deterministic provider
  - evidence: test artifacts show equal AI decision payloads and equal `provider/model`, with backend-specific persistence fields as only diff

- proof target: invariance of routing ownership
  - method: static and runtime checks ensuring AI stages read `control_plane.model_routing.parts.*` and fail if unresolved
  - evidence: unit tests and failure-path tests with explicit unresolved routing error messages

- proof target: auth contract enforcement
  - method: negative tests where API key absent and account/service key present
  - evidence: deterministic failures with deprecation/contract error code

- proof target: elimination of non-agentic AI branch
  - method: inspect and test late-stage mode payload/runtime path selection
  - evidence: no decision-critical branch to `non_agentic`; provenance indicates unified runtime path

- proof target: SSOT operator clarity
  - method: snapshot tests for settings response and `settings-used` payload
  - evidence: no runtime-authoritative claim from deprecated compatibility fields; resolved model source visible

## Completion Criteria

A specification item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
