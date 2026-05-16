---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: config-ssot-overlap-dead-settings-remediation
parent_workstream: workstream-fitcv-semantic-spine
parent_thread: workstream-fitcv-semantic-spine.semantic-spine-component-boundary-and-interface-contract
targets:
  - config/env.yaml
  - config/env.private.yaml
  - config/live_smoke.yaml
  - config/runtime/control_plane.yaml
  - config/runtime/pipeline.yaml
  - config/policy/cv_analysis.yaml
  - src/fitcv/config.py
  - src/fitcv_cp/settings_schema.py
  - docs/configuration.md
related_features:
  - settings_system
  - cv_system
  - admin_control_plane_core
related_stages:
  - enrich
  - rule_filter
  - shortlist
  - ranking
  - cv_analysis
  - cv_generation
---

## Goal

Define and enforce one canonical source-of-truth shape for runtime config in `config/`, remove overlapping ownership and dead configuration surfaces, and preserve runtime behavior through explicit compatibility boundaries and validation evidence.

## Key Deliverables

### Deliverable 1: Duplicate/overlap ownership eliminated in `config/env.yaml`

`config/env.yaml` no longer carries duplicated or conflicting ownership for keys owned by canonical runtime/policy/taxonomy files, including removal of duplicate key declarations in the same file.

### Deliverable 2: Dead or misleading config surfaces retired or reclassified

Config keys/files without active runtime consumers are either removed or explicitly documented as compatibility-only, with no ambiguous “looks active but unused” surfaces.

### Deliverable 3: Compatibility boundary is explicit and bounded

Any retained legacy compatibility keys have a declared deprecation boundary, read-only fallback policy, and migration path tied to validator-backed evidence.

### Deliverable 4: Validation proves no behavior regression

Targeted config + runtime + live-run checks prove invariance of expected pipeline behavior after SSOT cleanup.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- establish exact overlap/dead-surface boundary before changing config contracts

**Steps:**
- [ ] inventory config ownership by file (`env`, `runtime/*`, `policy/*`, `taxonomy/*`)
- [ ] map each candidate key/file to active runtime consumers in `src/`
- [ ] classify findings as one of: `canonical`, `legacy-compat`, `dead`, `ambiguous`

**Verification:**
- [ ] every flagged overlap/dead claim has file/line evidence in code + config

**Exit Criteria:**
- no proposed cleanup action relies on assumption-only ownership

### Wave 2: Decision closure

**Purpose:**
- lock SSOT ownership model and retirement rules

**Steps:**
- [ ] define canonical owner map for keys currently duplicated across config layers
- [ ] resolve duplicate `cv_acceptance_policy` declaration in `config/env.yaml`
- [ ] decide keep/remove for `config/env.private.yaml` and `config/live_smoke.yaml`
- [ ] decide keep/remove for `control_plane.model_routing.parts.cv_analysis_semantic_alignment`

**Verification:**
- [ ] each decision includes rationale + downstream impact + migration fallback

**Exit Criteria:**
- one deterministic ownership path exists for each in-scope key family

### Wave 3: Validation and approval readiness

**Purpose:**
- prove contract cleanup keeps runtime safe and traceable

**Steps:**
- [ ] define targeted validator set for changed config/doc/code surfaces
- [ ] define runtime verification (live run + settings-used + stage artifact checks)
- [ ] define residual risk handling for compatibility keys retained temporarily

**Verification:**
- [ ] validation plan includes both static and runtime evidence requirements

**Exit Criteria:**
- spec is implementation-plan ready without unresolved ownership ambiguity

## Design Decisions

### Decision: Canonical config ownership remains split by layer, not collapsed into `env.yaml`

- context: current loader already treats `runtime/*`, `policy/*`, and `taxonomy/*` as canonical owners and warns on overlap.
- choice: keep split-layer model and drain overlapping keys from `config/env.yaml` instead of promoting env as owner.
- alternatives considered:
  - consolidate all runtime/policy/taxonomy keys into `config/env.yaml`
  - keep overlap indefinitely and rely on warning-only detection
- impact:
  - preserves intended source layering in `src/fitcv/config.py`
  - reduces hidden precedence bugs from “last-write/first-write wins” collisions

### Decision: Duplicate key blocks in the same YAML file are disallowed

- context: `config/env.yaml` currently declares `cv_acceptance_policy` twice, creating silent override behavior.
- choice: require single declaration per top-level key in canonical config surfaces.
- alternatives considered:
  - keep duplicates and depend on parser order
- impact:
  - removes silent shadowing risk
  - improves auditability of policy decisions

### Decision: Legacy compatibility keys are transitional and explicitly bounded

- context: compatibility keys (`seniority_ladder`, `application_statuses`, `vector_top_n`, `rerank_top_n`, and other legacy env keys) are still projected in loader logic.
- choice: keep only keys with active consumers; mark each retained key as compatibility-only with removal conditions.
- alternatives considered:
  - immediate full removal of all legacy keys
  - indefinite retention without deprecation boundary
- impact:
  - avoids breaking active runtime while preventing compatibility drift

### Decision: Unused routing/config entries are removed unless a consumer is added

- context: `control_plane.model_routing.parts.cv_analysis_semantic_alignment` has no active consumer path in `src/`.
- choice: remove this routing part unless implementation explicitly adds consumer usage.
- alternatives considered:
  - retain unused key as future placeholder
- impact:
  - removes false configurability and operator confusion

## Invariants

- `load_config(...)` must continue to produce a valid merged runtime config for pipeline and control-plane flows.
- For each config fact in scope, exactly one canonical owning file exists.
- Compatibility projection may not introduce new duplicated owners; it can only bridge legacy keys with explicit deprecation intent.
- No config key may appear twice in the same YAML document.
- Live-run behavior remains non-regressive for stage progression and artifact generation.

## Acceptance Criteria

- `config/env.yaml` contains no duplicate top-level keys and no in-scope keys owned by canonical runtime/policy/taxonomy files unless explicitly marked compatibility-only.
- Every retained compatibility key has:
  - active code consumer evidence, and
  - documented deprecation/removal condition.
- Keys/files classified as dead have either:
  - been removed, or
  - been reclassified in docs as non-runtime with explicit rationale.
- Runtime evidence confirms cleaned config still yields successful stage artifacts with expected policy/semantic behavior.

## Non-Goals

- redesigning ranking/cv policy semantics
- changing business thresholds for acceptance/review policy
- broad refactor of settings UI beyond ownership/dead-surface cleanup
- full repo-wide config migration outside bounded `config/` + direct consumer surfaces

## Risks and Mitigations

- risk: removing a “looks unused” key that is used in hidden path.
  - mitigation: require source grep consumer proof before removal.
- risk: compatibility projection removal breaks older run/config snapshots.
  - mitigation: stage removals with compatibility flags and targeted regression tests.
- risk: stale GitNexus index misses references.
  - mitigation: treat GitNexus as advisory only (source-first evidence gates all decisions).

## Validation Plan

- proof target: duplicate-key and overlap ownership violations are removed
  - method: static inspection + targeted grep on in-scope files
  - evidence: diff + grep outputs showing single owner and no duplicate top-level key blocks

- proof target: retained compatibility keys are justified
  - method: source consumer trace
  - evidence: file/line references to active consumer code paths

- proof target: dead config entries are no longer ambiguous
  - method: config/doc consistency inspection
  - evidence: updated `docs/configuration.md` ownership table + removed/reclassified keys/files

- proof target: runtime behavior preserved after cleanup
  - method: targeted tests + live run
  - evidence:
    - targeted suites around config loading and control-plane run trigger
    - run artifacts (`settings-used.json`, `stage-artifacts/cv_analysis.json`) showing expected stage completion and no runtime failure markers

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
