# 2026-05-02 Updated Synonym Management for Domain + Role Family Spec

## Metadata
- Date: 2026-05-02
- Owner surface: `src/fitcv/`, `src/fitcv_cp/`, ranking + control-plane review workflow
- Type: behavior extension + scoring-stability hardening
- Related systems: mapping suggestions, synonym proposals, ranking preference-fit

## Problem Statement
Current synonym management is strongest for skill aliases. `domain` and `role_family` still rely primarily on exact normalized string equality in ranking preference-fit. This creates ranking-ratio instability for semantically equivalent labels (for example alias drift, lexical variants, or taxonomy-adjacent values) and increases operator review noise.

## Goals
1. Extend the existing synonym-management lifecycle to `domain` and `role_family`.
2. Preserve operational consistency with the skill-synonym workflow (suggestions -> proposals -> review -> apply -> promote).
3. Improve ranking-ratio stability by normalizing `domain` and `role_family` before preference-fit scoring.
4. Keep scoring explainable via deterministic match-type diagnostics.

## Non-Goals
1. Replacing the existing skill-synonym flow.
2. Full taxonomy redesign across unrelated surfaces.
3. Automatic global promotion without operator oversight.

## Scope
- In scope:
  - New alias-map surfaces for `domain` and `role_family`.
  - Mapping suggestion generation for both fields.
  - Proposal generation/review/apply/promotion lifecycle parity with skills.
  - Ranking preference-fit integration with canonicalized values.
  - Optional neighbor-aware scoring rules for taxonomy-adjacent matches.
- Out of scope:
  - New external model providers.
  - Rewriting vector-search candidate-query architecture.

## Canonical Data Model

### A) New maps
- `domain_alias_map: {alias -> canonical_domain}`
- `role_family_alias_map: {alias -> canonical_role_family}`

### B) Optional adjacency maps
- `domain_neighbors: {canonical_domain -> [neighbor_domains...]}`
- `role_family_neighbors: {canonical_role_family -> [neighbor_role_families...]}`

### C) Normalization contract
- All keys/values normalized to lowercase trimmed canonical tokens.
- Empty keys/values rejected.
- Overlay application is additive and run-scoped first; global promotion remains explicit.

## Pipeline Changes

### A) Enrich-stage suggestion generation
During/after enrich, emit field-specific suggestion rows:
- `domain_mapping_suggestions`
- `role_family_mapping_suggestions`

Each suggestion row includes:
- `run_id`
- `job_url`
- `job_title`
- `field` (`domain` or `role_family`)
- `alias`
- `canonical`
- `confidence`
- `evidence_summary` (minimal deterministic context)

### B) Proposal generation
Build grouped proposal payloads per field:
- aggregate by alias
- rank candidate canonicals by support
- mark conflict bundles when alias maps to multiple canonicals
- suppress proposals already present in effective map (run/global)

### C) Review workflow parity
Use same operator action model as skill synonym proposals:
- `approve`, `defer`, `reject`, `promote_global`
- apply approved mappings to run overlay
- optional global promotion path

### D) Ranking integration
Before preference-fit scoring:
- canonicalize `job.domain` and preference domains via `domain_alias_map`
- canonicalize `job_family` and preference role families via `role_family_alias_map`

Preference-fit dimension scoring:
- exact canonical match: `1.0`
- optional neighbor match: configurable default `0.7`
- no match: `0.0`
- empty preference dimension remains neutral policy (`0.5`) as currently defined

## Control Plane / Artifacts

### A) New/extended artifacts
- `domain-mapping-suggestions.json`
- `role-family-mapping-suggestions.json`
- proposal payloads can remain unified if field-tagged, or split per field (implementation choice).

### B) Run detail diagnostics
Expose per-field counters:
- suggested
- suppressed-as-already-global
- generated-for-review
- approved-for-run-overlay
- globally-promoted

### C) Ranking observability
Per ranked row, include:
- raw + canonical `domain`
- raw + canonical `role_family`
- match type per dimension (`exact`, `neighbor`, `none`)
- contribution impact in preference-fit components

## Compatibility and Migration
1. Existing skill synonym flow remains unchanged.
2. New maps default to empty; behavior remains backward-compatible.
3. If adjacency maps are absent, scoring falls back to exact-match-only canonical logic.

## Acceptance Tests
1. Unit: alias canonicalization for `domain` and `role_family`.
2. Unit: already-global mappings are suppressed from proposal review queue.
3. Unit: conflict alias creates conflict-bundle proposal.
4. Unit: preference-fit uses canonical values instead of raw string equality.
5. Unit: neighbor match returns configured partial score.
6. App/UI: run detail shows field-specific proposal counters.
7. Export: new mapping suggestion artifacts return valid schema payloads.
8. Regression: skill synonym workflow remains behaviorally unchanged.

## Rollout Plan
1. Wave 1 (shadow):
   - generate suggestions/proposals for `domain` and `role_family`
   - do not auto-apply; observe proposal quality and suppression rates
2. Wave 2 (apply-to-run):
   - allow operator-approved run overlay application
   - add ranking diagnostics with canonical/match-type visibility
3. Wave 3 (global promotion):
   - enable explicit global promotion controls
   - monitor ranking metric stability deltas and review-load reduction

## Risks
1. Over-aggressive canonicalization could collapse distinct taxonomy values.
2. Neighbor scoring weights may over-smooth distinctions if set too high.
3. Mixed deployment may temporarily show proposal surfaces before full ranking diagnostics are live.

## Done Criteria
1. `domain` and `role_family` follow the same operational lifecycle as skill synonyms.
2. Ranking preference-fit uses canonicalized values for both dimensions.
3. Proposal queues suppress already-global exact mappings.
4. Operator can trace ratio-impact via raw/canonical/match-type diagnostics.
5. Tests for canonicalization, suppression, and scoring behavior pass.
