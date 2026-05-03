---
layer: change
artifact_type: spec
status: completed
parent_thread: workstream-agentic-synonym-management.agentic-synonym-proposal-engine
targets:
  - src/fitcv/config.py
  - src/fitcv_cp/app.py
  - src/fitcv_cp/templates/run_detail.html
  - tests/test_config.py
  - tests/test_fitcv_cp/test_app.py
related_features: []
related_stages: []
---

# 2026-05-02 Run-Scoped Multi-Field Synonym Overlay Parity Spec

## Metadata
- Date: 2026-05-02
- Owner surfaces: `src/fitcv/config.py`, `src/fitcv_cp/app.py`, run-detail/trigger templates, tests
- Type: reliability + operator UX parity patch
- Related: field synonym source-of-truth split, synonym proposal review parity

## Problem Statement
The Trigger/Run overlay flow currently applies uploaded YAML only to `skill_synonyms`.  
`domain_alias_map` and `role_family_alias_map` still use default config only, which creates behavior drift:
1. Operator expects uploaded overlay YAML to affect all reviewed synonym fields.
2. Proposal review for non-skill fields can remain stale after overlay replacement.
3. Debug surfaces imply “synonym overlay” broadly, but runtime apply path is skill-only.

## Goals
1. Support run-scoped overlay for all synonym fields used in ranking/proposal flow:
   - `skill_synonyms`
   - `domain_alias_map`
   - `role_family_alias_map`
2. Preserve backward compatibility with existing skill-only overlay YAML.
3. Make Trigger and Run Detail UI explicit about multi-field overlay contents.
4. Ensure overlay replacement regenerates proposal state against effective multi-field map.

## Non-Goals
1. Changing global promotion policy.
2. Redesigning taxonomy schema.
3. Introducing automatic approval/promote for uploaded overlays.

## Canonical Overlay Contract

### Accepted YAML shapes
1. Legacy (still valid):
```yaml
skill_synonyms:
  gcp: google cloud
```

2. New multi-field:
```yaml
skill_synonyms:
  gcp: google cloud
domain_alias_map:
  fintech: financial services
role_family_alias_map:
  bi analyst: analytics
domain_neighbors:
  financial services: [banking]
role_family_neighbors:
  analytics: [data_science]
```

### Validation rules
1. Top-level must be mapping.
2. At least one supported section must be non-empty.
3. Alias maps normalize to canonical lowercase/tokenized keys/values.
4. Neighbor maps normalize to tuple/list of canonical lowercase tokens.
5. Unknown top-level keys are ignored with diagnostics (not hard-fail), unless strict-mode is later enabled.

## Design Changes

### A) Config parser/runtime apply
- Add parser:
  - `parse_runtime_synonym_overlay_yaml(raw_yaml) -> overlay_payload`
  - payload keys: `skill_synonyms`, `domain_alias_map`, `role_family_alias_map`, `domain_neighbors`, `role_family_neighbors`
- Add runtime apply:
  - `apply_runtime_synonym_overlay(cfg, overlay_payload, ...)`
  - merge strategy:
    - alias maps: overlay overwrites same alias key
    - neighbor maps: overlay key replaces neighbor list for that canonical key
- Keep compatibility wrapper:
  - existing `parse_skill_synonym_overlay_yaml` and `apply_runtime_skill_synonym_overlay` call new generic functions internally.

### B) Trigger upload path
- In `/admin/upload-trigger`:
  - parse uploaded YAML with new parser
  - apply via new runtime overlay function
  - persist raw YAML and normalized section counts in run effective settings metadata

### C) Run detail replacement path
- Overlay replacement endpoint for Stage-by-Stage run must:
  - accept same multi-field YAML
  - reapply effective settings snapshot with multi-field overlay
  - regenerate synonym proposals so queue reflects current effective map

### D) UI copy/inspection parity
- Trigger page “Synonym Overlay” copy:
  - explicitly list supported sections (skills/domain/role family)
- Run detail overlay card:
  - show per-field entry counts
  - show which sections were present in uploaded YAML
  - keep YAML snapshot export

### E) Artifact/diagnostic parity
- Extend runtime overlay metadata in settings-used and run diagnostics:
  - `overlay_section_counts`
  - `has_run_overlay_by_field`
  - `effective_entry_count_by_field`

## Backward Compatibility
1. Existing skill-only overlays remain valid unchanged.
2. If uploaded YAML contains only skills, behavior is identical to today.
3. If multi-field sections omitted, corresponding config remains default.

## Acceptance Tests
1. Config parser accepts legacy skill-only YAML.
2. Config parser accepts multi-field YAML and normalizes all sections.
3. Trigger upload applies `domain_alias_map` and `role_family_alias_map` to run effective settings.
4. Stage-by-Stage overlay replacement updates effective non-skill maps.
5. Proposal regeneration after replacement suppresses now-covered non-skill pairs.
6. Run detail overlay card shows section counts for all fields.
7. Regression: existing skill overlay tests still pass.

## Rollout Plan
1. Wave 1: parser + runtime apply + compatibility wrappers.
2. Wave 2: trigger/replacement endpoints wired to multi-field payload.
3. Wave 3: run-detail/trigger UI copy + overlay diagnostics.
4. Wave 4: proposal-regeneration parity assertions + focused regression tests.

## Risks
1. Over-normalization could collapse distinct domain/family labels.
2. Unknown-key tolerance may hide user typos without clear warning.
3. Multi-field replacement increases surface for stale proposal bugs if regeneration fails.

## Mitigations
1. Emit validation diagnostics listing accepted vs ignored sections.
2. Add explicit event payload for overlay apply summary per field.
3. Keep idempotent regenerate endpoint and verify suppression counters by field.

## Done Criteria
1. Uploaded run overlay can control skills + domain + role family in one YAML.
2. Effective settings and diagnostics report per-field overlay application.
3. Proposal review queue reflects current effective multi-field map after replacement.
4. Legacy skill-only overlay behavior remains intact.
