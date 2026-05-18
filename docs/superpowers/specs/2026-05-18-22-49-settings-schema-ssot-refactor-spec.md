---
layer: change
artifact_type: spec
status: completed
template_id: detailed-specification
name: settings-schema-ssot-symmetry-invariance-refactor
parent_thread: workstream-operator-control-plane.operator-control-plane-settings-surface-alignment
targets:
  - src/fitcv_cp/settings_schema.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/settings_store.py
  - tests/test_fitcv_cp/test_settings_schema.py
related_features: []
related_stages:
  - cv_analysis
  - cv_generation
  - ranking
---

## Goal

Define bounded refactor specification for `src/fitcv_cp/settings_schema.py` that removes schema drift and hidden duplication, enforces SSOT and symmetry for equivalent settings concepts, and preserves runtime behavior except where contradictions are explicitly resolved.

## Key Deliverables

### Deliverable 1: Canonical metadata and stage mapping model

Produce single-source derivation model for settings stage and IA metadata so equivalent keys follow equivalent classification rules.

### Deliverable 2: Explicit visibility/deprecation contract

Define and enforce non-conflicting contract for `ui_surface`, `ui_deprecation_state`, and editable/metadata-only/hidden sets.

### Deliverable 3: Declarative validation symmetry

Replace repeated relational and sum-check logic patterns with table-driven constraint declarations while preserving current error semantics.

### Deliverable 4: Safe migration strategy

Define rollout, compatibility, deprecation, and rollback controls for schema-default hydration and metadata behavior changes.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- confirm current behavior, callers, and blast radius before refactor

**Steps:**
- [x] run `.\scripts\get_gitnexus_freshness.ps1` (equivalent freshness gate satisfied via repeated `npx gitnexus analyze` during execution loop)
- [x] run `gitnexus_impact` for symbols planned for edit:
  - `_build_settings_ia_metadata`
  - `_default_stage_id`
  - `validate_settings`
  - `_hydrate_schema_defaults_from_config`
- [x] run `gitnexus_query` and `gitnexus_context` for each symbol with medium/high impact
- [x] capture direct consumers in `src/fitcv_cp/app.py`, `src/fitcv_cp/settings_store.py`, and tests

**Verification:**
- [x] each targeted symbol has documented upstream callers and affected flows

**Exit Criteria:**
- no planned change depends on unknown caller behavior

### Wave 2: Decision closure

**Purpose:**
- resolve SSOT/symmetry design choices and bounded migration shape

**Steps:**
- [x] define canonical stage ownership source (per-key model with generated group projections, or group model with generated per-key projections)
- [x] define final contract for visibility/deprecation overlap rules
- [x] define declarative constraint registry for relational validation families
- [x] define schema-default handling mode (immutable declared defaults + runtime overlay)

**Verification:**
- [x] every drift/contradiction from findings maps to one design decision

**Exit Criteria:**
- no unresolved design decision blocks implementation planning

### Wave 3: Validation and approval readiness

**Purpose:**
- specify proof artifacts and safety gates for implementation handoff

**Steps:**
- [x] define invariant tests for coverage, set disjointness, and mapping consistency
- [x] define regression tests for validation behavior and endpoint integration touchpoints
- [x] define GitNexus post-edit scope validation using `gitnexus_detect_changes()`
- [x] define rollback trigger thresholds and containment actions

**Verification:**
- [x] validation plan can prove unchanged behavior for non-targeted paths

**Exit Criteria:**
- spec ready for `skill-writing-plans` handoff

## Design Decisions

### Decision: Stage mapping SSOT

- context: stage semantics represented in both `_KEY_TO_STAGE_ID` and `_GROUP_TO_WORKFLOW_STAGES`, while metadata generation currently uses only per-key single stage output.
- choice: make per-key stage map canonical (`_KEY_TO_STAGE_ID`), generate group-stage map and workflow-stage list from schema/group projections; remove unused parallel map if redundant.
- alternatives considered:
  - keep both maps and add consistency tests only
  - make group-stage map canonical and derive per-key stages
- impact:
  - simplifies metadata generation path
  - reduces drift risk for `settings_keys_for_stage` vs workflow stage outputs
  - may require small test updates where unused map was assumed

### Decision: Visibility/deprecation classification contract

- context: key can currently be both editable and hidden-deprecated; no explicit overlap policy guard.
- choice: enforce default invariant `editable ∩ hidden_deprecated = ∅` with explicit allowlist mechanism for transitional keys.
- alternatives considered:
  - permit unrestricted overlap and let UI resolve conflicts at runtime
  - deprecation-only classification detached from editability semantics
- impact:
  - predictable admin behavior
  - explicit migration path for `cv_generation_model` handling

### Decision: Declarative relational validation

- context: repeated sum-to-one and ordering checks use copy/paste blocks.
- choice: create compact constraint registry (`constraint_id`, key-set, comparator, tolerance, message template) and evaluate in unified engine.
- alternatives considered:
  - keep current imperative checks with helper wrappers only
  - move all validation into schema rows
- impact:
  - consistent symmetry across equivalent constraints
  - lower maintenance cost when adding new weight families

### Decision: Immutable schema defaults

- context: `_hydrate_schema_defaults_from_config()` mutates `SETTINGS_SCHEMA` defaults at import.
- choice: keep declared defaults immutable; compute runtime baseline overlay via explicit function when needed by callers.
- alternatives considered:
  - keep import-time mutation and add warning docs
  - mutate copy of schema at module init and expose only copy
- impact:
  - deterministic schema contract across environments
  - requires coordinated updates in callers that depend on hydrated defaults

## Invariants

- `SETTINGS_SCHEMA` remains canonical source for key/type/default/group/config_path metadata.
- every public key returned by helper selectors exists in `SETTINGS_SCHEMA`.
- no unknown key exists in IA metadata output.
- per-key stage classification remains total for runtime-used keys.
- validation behavior for existing valid payloads remains unchanged unless conflict resolution policy explicitly changes.
- `coerce_value` accepted canonical bool/string/int/float/list forms remain backward compatible.
- existing admin save flows remain operational for section/group/single-key paths.

## Acceptance Criteria

1. stage classification has one canonical source and zero unreferenced parallel stage maps.
2. automated tests enforce classification consistency:
   - metadata-only/editable/hidden sets follow explicit overlap policy
   - stage lookup helpers agree with canonical stage metadata.
3. relational validation checks are table-driven and preserve existing error outcomes for current test corpus.
4. schema defaults no longer mutate at import-time; runtime overlays remain available through explicit API.
5. `gitnexus_detect_changes()` after implementation shows expected symbol/file scope only.

## Non-Goals

- redesign admin UX or endpoint contracts in `src/fitcv_cp/app.py`.
- change setting key names or external payload shape.
- reweight ranking/semantic scoring policy values.
- migrate unrelated settings outside `src/fitcv_cp/settings_schema.py` dependency boundary.

## Risks and Mitigations

- risk: hidden caller dependence on import-time hydrated defaults.
  - mitigation: add compatibility adapter function and targeted integration tests in app/settings_store call paths.
- risk: deprecation/editability policy change impacts admin workflows.
  - mitigation: transitional allowlist + explicit tests for affected keys.
- risk: constraint engine refactor alters error message wording consumed by tests or UI.
  - mitigation: preserve canonical message templates; snapshot assertions for key failures.
- risk: broader-than-expected impact from symbol edits.
  - mitigation: mandatory pre-edit `gitnexus_impact`, post-edit `gitnexus_detect_changes`, and bounded PR scope.

## Validation Plan

- proof target: canonical stage mapping has full key coverage
  - method: unit test + static coverage assertion
  - evidence: passing tests in `tests/test_fitcv_cp/test_settings_schema.py` with explicit coverage checks

- proof target: visibility/deprecation classification follows declared invariant
  - method: unit test on derived key sets + allowlist contract test
  - evidence: test cases asserting disjointness or approved exceptions

- proof target: relational constraints preserve behavior
  - method: regression tests for ordering, sum-to-one, partial payloads, and options validation
  - evidence: existing and new validation tests pass with unchanged expected failures

- proof target: runtime behavior compatibility in save/apply flows
  - method: integration-oriented tests touching `coerce_value`, `validate_settings`, `apply_settings_to_config`, and admin setting endpoints
  - evidence: targeted app/settings tests pass; no new failures in related suites

- proof target: refactor scope remains bounded
  - method: `gitnexus_detect_changes()` + `git diff --stat`
  - evidence: changed symbols and files match implementation plan scope

- proof target: type and contract health
  - method: `uvx mypy src --show-error-codes`, `uvx pytest tests/`
  - evidence: command outputs successful for touched scope

## Completion Criteria

1. all Key Deliverables satisfied with merged design decisions and invariant-aligned implementation plan.
2. all validation proof targets have mapped tests/checks and expected evidence paths.
3. unresolved decisions reduced to explicit, documented approval questions only.
4. artifact ready for downstream planning via `skill-writing-plans` with no additional design discovery required.

