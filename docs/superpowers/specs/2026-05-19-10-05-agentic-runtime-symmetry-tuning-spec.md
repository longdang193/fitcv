---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: agentic-runtime-throughput-symmetry-spec
parent_thread: workstream-operator-control-plane.operator-control-plane-agentic-settings-surface
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/templates/settings.html
  - src/fitcv_cp/app.py
  - src/fitcv/pipeline.py
  - src/fitcv/agentic_cv_analysis.py
  - src/fitcv/agentic_cv_generation.py
  - src/fitcv/synonym_management.py
  - tests/test_fitcv_cp/test_settings_schema.py
  - tests/test_pipeline.py
  - tests/test_pipeline_agentic_late_stage.py
related_features: []
related_stages:
  - enrich
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define structural-symmetry specification for Advanced Runtime Tuning so throughput controls stop being enrichment-biased and become stage-symmetric across all agentic AI stages, while preserving compatibility for existing settings keys and operator workflows.

## Key Deliverables

### Deliverable 1: Unified stage-runtime settings contract

Specify one canonical stage-scoped runtime contract for throughput tuning (`sleep_secs`, `concurrency`, optional `batch_size`) that applies consistently to `enrich`, `ranking`, `cv_analysis`, `cv_generation`, and `synonym_triage`.

### Deliverable 2: Compatibility-preserving migration boundary

Specify alias and precedence rules so existing keys (`enrichment_sleep_secs`, `rerank_sleep_secs`, `enrichment_batch_size`, `enrichment_concurrency`) continue to work with no behavioral regression during transition.

### Deliverable 3: IA/metadata symmetry contract

Specify how settings metadata (`stage`, `workflow_stages`, `decision_area`, `control_surface`, `runtime_used`, risk labels) is generated consistently for all throughput controls, including shared-stage effects.

### Deliverable 4: Validation and observability symmetry

Specify proofs, test coverage, and runtime evidence outputs that demonstrate stage-parity behavior and detect drift between schema, runtime usage, and UI representation.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- capture current state, runtime call paths, and blast radius before contract changes

**Steps:**
- [x] verify GitNexus freshness (`.\scripts\get_gitnexus_freshness.ps1` -> fresh)
- [x] collect symbol context and upstream impact:
  - `settings_ia_contract_for_key` (`LOW`, settings UI and admin settings flow)
  - `analyze_ranked_job` (`LOW`, `run_pipeline` + worker indirection)
  - `generate_from_analysis` (`LOW`, `run_pipeline` + worker indirection)
- [x] inspect existing tuning ownership in `settings_schema`, `pipeline`, `enrich`, `ai_score`, agentic generation/analysis code paths
- [x] record existing asymmetry: throughput knobs are stage-classified as `enrich`/`ranking` but no equivalent operator controls for `cv_analysis`/`cv_generation`/`synonym_triage`

**Verification:**
- [x] no design decision depends on unknown caller graph for targeted symbols

**Exit Criteria:**
- current-state asymmetry and dependency boundaries explicitly documented

### Wave 2: Decision closure

**Purpose:**
- choose canonical symmetric contract and bounded migration strategy

**Steps:**
- [ ] decide canonical contract shape under `stage_runtime.<stage_id>.*` for throughput controls
- [ ] define per-stage required/optional knobs:
  - `sleep_secs`: required for all AI stages
  - `concurrency`: required where stage runs parallelizable units
  - `batch_size`: optional; only where stage does chunk/batch boundaries
- [ ] define alias/precedence strategy:
  - new stage-runtime key wins when both present
  - legacy key read as fallback alias
  - persistence writes canonical key only after migration gate
- [ ] define stage-specific rollout sequence to minimize risk

**Verification:**
- [ ] each non-obvious design branch has explicit chosen path and bounded alternative

**Exit Criteria:**
- no unresolved architecture decision blocks implementation planning

### Wave 3: Validation and approval readiness

**Purpose:**
- make proof obligations explicit before plan/coding handoff

**Steps:**
- [ ] define schema validation tests for canonical+alias behavior
- [ ] define pipeline/runtime forwarding tests for each stage
- [ ] define UI metadata/render tests for stage/decision-area symmetry
- [ ] define drift-detection checks between settings schema, runtime usage, and artifact output
- [ ] define post-edit graph-scope check with `gitnexus detect-changes`

**Verification:**
- [ ] validation plan proves compatibility, symmetry, and non-regression

**Exit Criteria:**
- spec is implementation-plan ready

## Design Decisions

### Decision: Canonical throughput contract becomes stage-runtime map

- context: current model mixes stage-local keys and shared semantics; only enrich/ranking have explicit throughput knobs.
- choice: adopt canonical map:
  - `stage_runtime.enrich.sleep_secs|concurrency|batch_size`
  - `stage_runtime.ranking.sleep_secs|concurrency`
  - `stage_runtime.cv_analysis.sleep_secs|concurrency`
  - `stage_runtime.cv_generation.sleep_secs|concurrency`
  - `stage_runtime.synonym_triage.sleep_secs|concurrency`
- alternatives considered:
  - keep adding one-off flat keys per stage
  - keep enrich-only advanced tuning and add docs only
- impact:
  - unifies mental model
  - removes long-term schema drift pressure
  - enables consistent IA generation rules

### Decision: Legacy keys remain compatibility aliases during migration window

- context: existing operators and tests rely on flat keys today.
- choice: retain read-compat aliases with deterministic precedence:
  1. canonical stage-runtime key
  2. legacy alias key
  3. declared schema default
- alternatives considered:
  - hard cutover with breaking key rename
  - dual-write permanently without deprecation
- impact:
  - no immediate operator break
  - bounded technical debt via explicit deprecation timeline

### Decision: Symmetry with bounded divergence

- context: strict symmetry can force artificial knobs where runtime does not support them.
- choice: enforce structural symmetry at contract level but allow bounded stage-level divergence:
  - `batch_size` required only for genuinely batched stages
  - `concurrency` required only when runtime path can execute concurrent units
  - each divergence must be justified in schema metadata and tests
- alternatives considered:
  - force full identical key set for every stage
  - no symmetry requirement
- impact:
  - keeps invariance principle without fake knobs
  - prevents UX clutter and false control surfaces

### Decision: Throughput controls remain `control_surface=shared` and `decision_area=throughput`

- context: these settings influence scheduling/rate behavior, not quality policy semantics.
- choice: preserve shared throughput classification for all stage-runtime tuning keys.
- alternatives considered:
  - classify by stage-specific bespoke decision areas
  - classify as diagnostics only
- impact:
  - keeps UI semantics stable
  - keeps filters and badge behavior consistent

### Decision: Phased execution ordering

- context: generation stage has highest operator and acceptance-risk sensitivity.
- choice: phase rollout:
  1. schema + alias layer
  2. ranking and cv_generation runtime wiring
  3. cv_analysis and synonym_triage runtime wiring
  4. UI refinement and cleanup
- alternatives considered:
  - big-bang cutover across all stages
- impact:
  - lowers rollback blast radius
  - keeps failure isolation practical

## Invariants

- Existing persisted settings continue to produce equivalent runtime behavior unless a new canonical override is explicitly set.
- No stage receives operator-visible throughput knob that runtime path ignores silently.
- IA metadata remains truthful: if `runtime_used` is `Yes`, path must be exercised by runtime.
- Stage attribution in settings UI must reflect effective stage ownership and shared-stage impact.
- Compatibility aliases are read-only bridge surfaces after migration gate; canonical keys become single write target.
- No hidden stage-specific special case is allowed without explicit schema/documented rationale.

## Validation Plan

- proof target: canonical stage-runtime keys resolve deterministic effective values with legacy fallback
  - method: unit tests in settings schema resolver
  - evidence: new/updated `tests/test_fitcv_cp/test_settings_schema.py` cases for precedence matrix

- proof target: enrichment and ranking behavior unchanged when only legacy keys are set
  - method: regression tests on existing pipeline/enrich/rerank forwarding
  - evidence: passing existing + augmented tests in `tests/test_pipeline.py`, `tests/test_enrich.py`, `tests/test_ai_score.py`

- proof target: cv_generation and cv_analysis consume stage-runtime throughput controls when enabled
  - method: targeted unit/integration tests on agentic generation/analysis invocation paths
  - evidence: new tests in `tests/test_pipeline_agentic_late_stage.py` and related suites

- proof target: settings UI and IA badges show symmetric stage-runtime metadata
  - method: settings view rendering tests and metadata contract assertions
  - evidence: updated `tests/test_fitcv_cp/test_app.py` and `tests/test_fitcv_cp/test_settings_schema.py`

- proof target: graph-level affected scope stays bounded to expected tuning surfaces
  - method: `npx gitnexus detect-changes` before merge
  - evidence: output showing affected symbols align with spec targets

## Acceptance Criteria

- Operator can configure throughput controls for `ranking`, `cv_generation`, and `cv_analysis` through same advanced runtime model used by enrich.
- Legacy tuning keys still function with no behavior regression when canonical stage-runtime keys are absent.
- When both old and new keys exist, documented precedence behavior is enforced and tested.
- Runtime artifacts/metadata expose enough evidence to confirm which stage-runtime values were effective for each run.
- No new throughput control appears in UI as runtime-used unless runtime path consumes it.

## Non-Goals

- No provider-model routing redesign (`openai`/`gemini` decision authority unchanged).
- No redesign of non-throughput decision areas (quality weights, policy thresholds, lifecycle guards).
- No full removal of legacy keys in this change.
- No broad refactor of unrelated settings taxonomy beyond throughput-symmetry scope.

## Risks and Mitigations

- Risk: alias precedence ambiguity causes silent behavior drift.
  - Mitigation: explicit precedence matrix tests + run artifact evidence fields.

- Risk: exposing knobs before runtime wiring creates false operator confidence.
  - Mitigation: gate UI visibility by `runtime_used` truth and staged rollout toggles.

- Risk: stage-specific runtime differences break strict symmetry assumptions.
  - Mitigation: contract-level symmetry with documented bounded divergence and test assertions.

- Risk: migration debt persists indefinitely.
  - Mitigation: include deprecation checkpoints and explicit follow-up criteria in downstream plan.

## Completion Criteria

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>
