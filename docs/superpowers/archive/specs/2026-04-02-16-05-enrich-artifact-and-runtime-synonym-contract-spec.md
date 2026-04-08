---
feature_type: modify
feature_name: none
status: draft
summary: "Make enrich-stage samples fully visible and introduce durable synonym suggestion persistence plus runtime synonym overlays shared across downstream stages."
invariants:
  - Enrich-stage sampled rows must expose the full enrich output contract for each sampled job.
  - Suggested synonym mappings must remain reviewable artifacts and must not auto-mutate the trusted base synonym map.
  - A run must use one effective merged skill-synonym map across all stages that perform synonym-based interpretation.
  - Base config defaults must remain available even when runtime overlays are absent.
---

# Enrich Artifact And Runtime Synonym Contract

## Triage

Feature type: MODIFY  
Summary: Make enrich-stage artifacts fully inspectable and formalize durable synonym suggestions plus runtime synonym overlays shared across downstream stages.  
Reasoning: This changes existing enrich/debugging behavior and the runtime synonym-resolution contract across several stages; it does not introduce a separate user-facing product area.  
Invariants:
- Enrich raw outputs must remain visible and traceable.
- Enrich-stage artifact rows must expose the full enrich contract for sampled jobs.
- Suggested mappings must remain reviewable and separate from the trusted base synonym map.
- All downstream stages in a run must consume one shared effective synonym map.
Dependencies:
- `config/skill_synonyms.yaml`
- enrich canonical field contract
- stage artifact generation
Affected stages:
- `enrich`
- `rule_filter`
- `ranking`
- `cv_generation`
Affected features:
- none
Primary lens: stage
Affected docs:
- feature_yaml: `none`
- feature_history: `none`
- feature_docs:
  - `none`
- cross_cutting_docs:
  - `docs/FitCV-pipeline.md`
  - `docs/stages/enrich.yaml`
  - `docs/stages/rule_filter.yaml`
  - `docs/stages/ranking.yaml`
- readme: `none`
- generated:
  - `none`
Generated refresh required: no
Spec needed: yes
Plan needed: yes

## Problem

The current enrich-stage inspection surface is incomplete for debugging and the current skill-synonym lifecycle is too static.

Today:

- enrich-stage artifact samples may omit enrich outputs that are present on the actual enriched rows
- synonym suggestions discovered during enrichment are not yet treated as durable review artifacts
- the trusted base map in `config/skill_synonyms.yaml` is the only effective synonym source
- downstream stages can only benefit from repo-default synonym updates after the base YAML is manually edited and shipped

This creates two kinds of debugging friction:

- enrich inspection is weaker than the actual runtime contract
- newly discovered or newly approved synonym updates are slow to apply to subsequent stage behavior

## Goals

- Make each enrich-stage sample row include all enrich fields present on the sampled row.
- Persist synonym suggestions so they survive the run and remain reviewable later.
- Support runtime synonym overlays on top of the base synonym YAML.
- Ensure the effective merged synonym map is shared consistently across enrich, rule filter, ranking, and later synonym-using stages in the same run.

## Non-Goals

- Replacing the base `config/skill_synonyms.yaml` file.
- Automatically promoting every discovered suggestion into the trusted synonym map.
- Designing a full admin curation UI in this rollout.
- Solving all ontology or canonical-term governance problems beyond the skill-synonym map.

## Current-State Summary

The system already has:

- a trusted base synonym file at `config/skill_synonyms.yaml`
- enrich canonical outputs such as canonical skill lists and skill entity breakdowns
- stage-transition artifacts for run debugging

The missing parts are:

- full enrich visibility in sampled artifact rows
- durable storage for mapping suggestions
- a formal overlay layer for reviewed or runtime-approved synonym updates
- one explicit effective-map contract reused by all synonym-aware stages

## Proposed Design

## 1. Enrich-Stage Artifact Rows Must Include All Enrich Fields

The enrich-stage artifact is the primary debugging surface for enrichment. It should therefore expose the full enrich output contract for sampled jobs, not a curated debug subset.

For each sampled enrich output row, the artifact should include every enrich field present on that row, including but not limited to:

- raw extracted list fields
  - `required_skills`
  - `preferred_skills`
  - `responsibilities`
  - `tech_stack`
  - `keywords`
- canonical companion fields
  - `required_skills_canonical`
  - `preferred_skills_canonical`
  - `responsibilities_canonical`
  - `tech_stack_canonical`
  - `keywords_canonical`
- raw/coerced scalar companions
  - `location_type_raw`
  - `seniority_raw`
  - `domain_raw`
  - `job_family_raw`
- normalized scalar fields
  - `location_type`
  - `seniority`
  - `domain`
  - `job_family`
- structured enrich entities
  - `required_skill_entities`
  - `preferred_skill_entities`
- suggestion/debug fields
  - `mapping_suggestions`
- trace fields
  - `enrichment_model`
  - `enrichment_version`
  - `enriched_at`
  - `description_cleaned`

This rule is intentionally simple:

- if an enrich field exists on the sampled row, the enrich-stage artifact sample should include it

The enrich artifact is the one place where broad visibility is more important than aggressive payload slimming.

## 2. Clarify The Meaning Of `required_skill_entities`

`required_skill_entities` should be treated as the structured enrich breakdown of extracted job requirements.

Each entity represents:

- the raw phrase that enrichment extracted
- the canonical skill chosen for that phrase

Illustrative shape:

```json
[
  {
    "raw_text": "Python programming for data science",
    "canonical": "python"
  },
  {
    "raw_text": "Google Cloud Platform (GCP)",
    "canonical": "google cloud"
  }
]
```

This field answers:

- what exact phrase was extracted
- how that phrase was normalized

It exists to make canonicalization debuggable without losing the original wording.

## 3. Clarify The Meaning Of `mapping_suggestions`

`mapping_suggestions` should be treated as a review queue, not as an automatically trusted config update.

Each suggestion represents a candidate alias-to-canonical mapping discovered during enrichment or synonym-aware interpretation.

Illustrative shape:

```json
[
  {
    "must_have_skill": "Python",
    "matches": true,
    "confidence": 0.91,
    "alias": "python programming for data science",
    "canonical": "python"
  }
]
```

This field answers:

- what alias candidate was observed
- what canonical skill it appears to mean
- how confident the system is
- whether the suggestion was associated with a positive match decision

`mapping_suggestions` must remain separate from the trusted base synonym file until explicitly reviewed and promoted.

## 4. Persist Suggestions Beyond One Artifact Download

The system should durably persist all synonym suggestions so they can be reviewed later even if the original run is no longer open in the UI.

Recommended persistence surfaces:

- run-scoped persistence
  - the complete suggestion list discovered in one run
- aggregated persistence
  - grouped alias-to-canonical summaries across many runs

Run-scoped records should keep enough context to support debugging and audit:

- `run_id`
- `job_url`
- `source_field`
- `alias`
- `canonical`
- `confidence`
- `matches`
- optionally `must_have_skill`

Aggregated records should support review and promotion:

- `alias`
- `suggested_canonical`
- `occurrences`
- `avg_confidence`
- `conflicting_canonicals`
- example source rows or run references

The project should support downloading both:

- run-level suggestions
- aggregate suggestion summaries

## 5. Introduce A Synonym Overlay Layer

The system should support a runtime synonym overlay in addition to the base file at `config/skill_synonyms.yaml`.

Recommended layers:

1. base map
- trusted repo-default entries from `config/skill_synonyms.yaml`

2. overlay map
- reviewed or environment-specific updates loaded at runtime

3. optional run-scoped overlay
- explicitly supplied per-run updates for controlled debugging or experiments

Merge order:

```text
effective_skill_synonyms =
  base_map
  + overlay_map
  + run_scoped_overlay
```

Later layers override earlier ones on key collision.

This allows newly approved mappings to be used immediately without waiting for the repo-default file to be revised first.

## 6. Overlay Sources Should Be Explicit And Traceable

Overlay loading should be explicit rather than magical.

Recommended supported sources:

- a configured overlay YAML file
- an admin-reviewed exported synonym update file
- an optional run payload override for debugging

Each run should be able to report which synonym layers were used, for example:

- base file path or version/hash
- overlay file path or version/hash
- whether a run-scoped override was present

This traceability matters because filter and ranking decisions depend on the effective map.

## 7. Propagate One Effective Map Across All Synonym-Aware Stages

The system should compute the effective merged synonym map once per run and then propagate that same map to every stage that uses skill canonicalization.

At minimum, this includes:

- `enrich`
- `rule_filter`
- `ranking`
- `gap_analysis`
- `validator`

The important invariant is:

- a single run must not use different effective synonym maps in different downstream stages unless the run explicitly requested that behavior

Without this, the system could:

- canonicalize one way during enrich
- filter a different way in rule filter
- rank a different way again later

That would make debugging and trust much worse.

## 8. Promotion Model

Suggestion persistence and overlay loading should support a later promotion workflow, but promotion itself should remain explicit.

Recommended policy:

- suggestions are automatically persisted
- reviewed entries can be promoted into an overlay source immediately
- trusted long-term entries can later be copied into the base `skill_synonyms.yaml`

This creates three states:

1. discovered
- present only in suggestions

2. approved for runtime use
- present in overlay

3. trusted default
- present in base config

That separation lets the system learn quickly without making the base map noisy.

## Example Workflow

A run enriches this requirement:

```json
{
  "required_skills": [
    "Google Cloud Platform (GCP)",
    "PowerBI",
    "Python programming for data science"
  ]
}
```

Enrich emits:

```json
{
  "required_skill_entities": [
    {"raw_text": "Google Cloud Platform (GCP)", "canonical": "google cloud"},
    {"raw_text": "PowerBI", "canonical": "power bi"},
    {"raw_text": "Python programming for data science", "canonical": "python"}
  ],
  "mapping_suggestions": [
    {"must_have_skill": "Google Cloud", "matches": true, "confidence": 0.99, "alias": "google cloud platform (gcp)", "canonical": "google cloud"},
    {"must_have_skill": "Power BI", "matches": true, "confidence": 0.97, "alias": "powerbi", "canonical": "power bi"},
    {"must_have_skill": "Python", "matches": true, "confidence": 0.91, "alias": "python programming for data science", "canonical": "python"}
  ]
}
```

Later review decides:

- `google cloud platform (gcp) -> google cloud`: promote
- `powerbi -> power bi`: promote
- `python programming for data science -> python`: keep as suggestion only because it is too phrase-specific

The approved entries are written to an overlay source and can immediately affect future runs, while the base YAML stays compact until a later curated update.

## Operational Recommendations

- The enrich-stage artifact should prefer visibility over payload minimalism.
- Suggestion persistence should be treated as operational data, not just UI decoration.
- Overlay files should be easy to inspect and diff.
- The effective map used by a run should be exportable or at least traceable in run metadata.

## Risks

- Full enrich rows increase artifact size.
- Overlay support introduces another configuration layer that must be kept visible and understandable.
- Overly easy promotion could still pollute the synonym system if review standards are weak.

These risks are acceptable because:

- the enrich stage is a debugging-heavy surface by design
- overlays are easier to reason about than silently mutating the base file
- explicit effective-map reporting preserves auditability

## Success Criteria

- A downloaded enrich-stage artifact sample shows all enrich fields present on sampled rows.
- Mapping suggestions remain available after the run for later review.
- A reviewed synonym overlay can be applied to future runs without waiting for a repo-default config edit.
- Rule filter, ranking, and later synonym-aware stages all use the same effective merged synonym map within a run.

