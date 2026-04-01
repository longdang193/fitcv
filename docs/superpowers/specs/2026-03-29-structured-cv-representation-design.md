---
feature_type: modify
feature_name: cv_system
status: draft
summary: "Introduce a structured intermediate CV representation so CV outputs can be stored, exported, and reused semantically in addition to markdown."
invariants:
  - "Rendered CV markdown must remain available for existing download and display flows."
  - "Structured CV data must be generated from the same run-scoped facts used for markdown generation."
  - "The first rollout must not require downstream consumers to parse markdown to recover CV sections."
  - "Stored structured CV payloads must be explicit, schema-driven, and versioned."
---

# Structured CV Representation — Design Specification

Affected feature contract: [`docs/features/cv_system/cv_system.yaml`](../../features/cv_system/cv_system.yaml)

## Triage

Feature type: MODIFY  
Summary: Add a structured intermediate CV document model alongside rendered markdown output.  
Reasoning: This extends the existing CV system so generated CVs can be stored and consumed as semantic sections, not only as markdown text.  
Invariants:
- Existing markdown CV generation and downloads must continue to work.
- Structured CV data must be persisted with the generated CV version, not reconstructed later by parsing markdown.
- The document model must be versioned so future schema changes are explicit.
- The first implementation should remain compatible with the current run-detail and export flows.
Dependencies:
- `cv_system`
- downstream consumer: `trigger_run_management`
Affected docs:
- feature_yaml: `docs/features/cv_system/cv_system.yaml`
- feature_history: `docs/features/cv_system/history.md`
- feature_docs: none
- cross_cutting_docs: none
- readme: none
- generated: none
Generated refresh required: no
Spec needed: yes
Plan needed: yes
Risk level: medium

## Problem

Today the CV system treats the generated CV primarily as one rendered markdown artifact.

Current behavior:

- [`generate_cv()`](../../../src/fitcv/cv_generator.py) returns a markdown string
- [`create_cv_version_record()`](../../../src/fitcv/tracker.py) persists `cv_markdown`
- run detail and exports can download or embed that markdown

This is good for final delivery, but weak for downstream usage.

Current gaps:

- exports cannot expose semantic CV sections such as `summary`, `experience`, `education`, or `skills`
- downstream consumers would need to parse markdown heuristically
- audits cannot easily answer which section content was produced by the model versus just rendered formatting
- future UI features such as section-level editing, diffing, or validation are harder because the system has no canonical structured CV document

## Goals

- Introduce a structured intermediate CV representation
- Persist that representation with each generated CV version
- Keep markdown as a rendered artifact, not the only canonical artifact
- Make structured CV data available to downstream exports and admin inspection
- Preserve backward compatibility for current markdown download flows

## Non-Goals

- Building a full in-browser CV editor in this change
- Replacing markdown downloads
- Parsing historical markdown CVs into structured documents retroactively
- Supporting arbitrary user-authored template grammars in v1

## Recommendation

Adopt a dual-artifact model:

1. a canonical structured CV document
2. a rendered markdown representation derived from that document

The structured document should be the semantic source of truth for new CV versions. Markdown should remain the delivery-friendly rendering.

This is stronger than trying to recover semantic structure later by parsing markdown.

The structured document should be treated as a generated CV document schema aligned to the current preset/composition/content-rules system. It is not intended to be a raw storage dump of the candidate profile.

## Approaches Considered

### Option 1: Keep markdown-only storage

Pros:

- simplest short-term implementation
- no schema change

Cons:

- exports remain text-heavy and semantically weak
- future section-level features require brittle markdown parsing
- auditability stays limited

### Option 2: Parse markdown after generation into structured sections

Pros:

- avoids changing the generator contract immediately
- can produce a sectioned shape from existing outputs

Cons:

- brittle and template-dependent
- headings can vary by prompt/template/model
- creates low-trust structured data inferred after the fact

### Option 3: Generate a structured CV document first, then render markdown

Pros:

- strongest semantic model
- no need to parse markdown
- enables exports, validation, and future editing workflows cleanly

Cons:

- requires generator, storage, and downstream contract changes
- introduces a schema-versioning responsibility

## Decision

Use Option 3.

The system should generate a structured CV document first, then render markdown from that structured document.

## Proposed Architecture

### Current Flow

```text
pipeline inputs
  -> generate_cv(...)
  -> markdown string
  -> cv_versions.cv_markdown
  -> downloads / exports
```

### Proposed Flow

```text
pipeline inputs
  -> generate_structured_cv(...)
  -> structured CV document
  -> render_cv_markdown(structured_doc, template/preset)
  -> persist both structured_doc and markdown
  -> downloads / exports / future section-level UI
```

## Structured CV Document Model

The stored structured representation should be explicit and schema-versioned.

The structured document is the canonical semantic output of the CV generation step after applying the active preset, composition, and content-rule configuration for the run. It is not a universal candidate-profile model.

### Top-Level Shape

```json
{
  "schema_version": "cv_doc_v1",
  "preset": "europass",
  "locale": "en",
  "job_url": "https://example.com/job/123",
  "fit_classification": "strong",
  "target_role": "Data Analyst",
  "sections": {
    "header": {},
    "summary": {},
    "experience": [],
    "projects": [],
    "education": [],
    "skills": {},
    "certifications": [],
    "languages": []
  }
}
```

### Recommended Section Shapes

#### `header`

```json
{
  "name": "Jane Doe",
  "title": "Senior Data Analyst",
  "location": "Berlin, Germany",
  "contact": {
    "email": "jane@example.com",
    "phone": null,
    "linkedin": "https://linkedin.com/in/jane"
  }
}
```

#### `summary`

```json
{
  "text": "Data analyst with 6 years of experience..."
}
```

#### `experience`

```json
[
  {
    "role": "Data Analyst",
    "company": "ACME",
    "start": "2022-01",
    "end": "2025-03",
    "location": null,
    "bullets": [
      "Built KPI reporting pipelines in SQL and Python",
      "Partnered with product and banking stakeholders"
    ]
  }
]
```

#### `projects`

```json
[
  {
    "name": "Fraud Detection Analytics",
    "context": "Internal analytics project",
    "bullets": [
      "Designed fraud detection metrics",
      "Improved analyst review workflow"
    ]
  }
]
```

#### `education`

```json
[
  {
    "degree": "MSc Statistics",
    "institution": "University X",
    "start": null,
    "end": "2020"
  }
]
```

#### `skills`

```json
{
  "groups": [
    {
      "label": "Core",
      "items": ["SQL", "Python", "Power BI"]
    },
    {
      "label": "Tools",
      "items": ["dbt", "Redshift"]
    }
  ]
}
```

This grouped shape is preferred over rigid buckets such as `core/tools/methods`, because it is more compatible with future presets and section compositions.

## Persistence Model

### `cv_versions`

Extend the current `cv_versions` record to store both:

- `cv_markdown`
- `cv_structured_json`

Recommended new fields:

- `cv_structured_json STRING`
- `cv_schema_version STRING`
- `cv_generation_model STRING`
- `cv_prompt_version STRING`

Optional but useful:

- `cv_render_variant STRING`
- `cv_render_locale STRING`

These fields are part of the persisted CV artifact metadata, not just generic run metadata. Each stored artifact should carry enough information to explain:

- which schema it conforms to
- which model generated the content
- which prompt version shaped the output
- which render variant or preset was used

### Why Store Structured JSON Directly

Pros:

- simple BigQuery compatibility
- avoids premature table explosion for nested sections
- keeps the first rollout aligned with the current `cv_versions` storage pattern

This can later evolve into a more normalized model if analytics requirements justify it.

## Generator Contract

### Current Contract

```python
generate_cv(...) -> str
```

### Preferred Contract

```python
generate_structured_cv(...) -> dict[str, Any]
render_cv_markdown(structured_cv, config) -> str
```

This is the recommended architecture.

### Rollout Compatibility

```python
generate_cv(...) -> {
  "structured_cv": {...},
  "markdown": "# CV ..."
}
```

If a compatibility wrapper is needed during rollout, `generate_cv(...)` may temporarily return both artifacts together. But the target architecture is still:

1. `generate_structured_cv(...)`
2. validate structured output
3. `render_cv_markdown(...)`
4. persist both artifacts

## Rendering Responsibility

Markdown should be treated as a render target, not the canonical semantic source.

That means:

- section ordering belongs to the renderer/template layer
- semantic section content belongs to the structured document
- preset/template selection can still shape formatting and emphasis without redefining the document model
- markdown rendering must consume the validated structured CV document rather than a parallel free-text path

## Export and Admin Implications

### Run Results JSON Export

For future export revisions, the `cv` object should support:

```json
{
  "version_id": "string",
  "model_used": "gemini-2.5-pro",
  "prompt_version": "v1",
  "schema_version": "cv_doc_v1",
  "structured": {},
  "markdown": "# CV ...",
  "created_at": "2026-03-29T16:11:40Z"
}
```

This avoids the need to parse markdown just to expose `experience`, `education`, or `skills`.

### Run Detail UI

The current run detail page can keep the markdown download flow unchanged in v1.

Future UI options enabled by this model:

- inspect structured CV sections
- compare two CV versions by section
- show validation warnings tied to specific sections

## Migration Strategy

### Phase 1

- store structured CV for newly generated CV versions only
- preserve markdown storage
- do not backfill historical rows

### Phase 2

- update exports to include structured CV when available
- include `model_used`, `prompt_version`, and schema metadata in export payloads

### Phase 3

- optionally add section-level admin inspection or editing features

Historical rows without structured CV should remain valid. They should simply expose:

- `cv_structured_json = null`
- `cv_schema_version = null`

## Validation and Invariants

The structured document model should support validation before persistence.

Validation lifecycle:

1. generate structured CV output
2. validate it against the explicit schema
3. render markdown from the validated structured document
4. persist structured JSON, schema metadata, generation metadata, and markdown to `cv_versions`

Recommended invariants:

- required top-level keys always present
- section shapes are stable even when empty
- lists use `[]`, not `null`
- optional scalar values may use `null`
- markdown must be renderable from the structured document without requiring hidden external state
- the structured CV document must reflect the active preset, composition, and content-rule contract for the run

## Open Questions

### Should the model include section-level provenance?

Possibly later, for example:

```json
{
  "summary": {
    "text": "...",
    "sources": ["experience:acme", "project:fraud-detection"]
  }
}
```

This is useful, but likely not required for the first structured rollout.

### Should CV generation ask the LLM for structured JSON directly?

Yes, that is the preferred long-term direction if the schema can be made stable enough.

That would align with the project’s broader move toward structured outputs rather than free-text parsing.

### Should markdown rendering be purely deterministic from structured data?

Ideally yes. The cleaner model is:

- model produces structured content
- renderer produces markdown

That gives the highest trust and repeatability.

## Acceptance Criteria

- New CV versions can persist a structured CV document alongside markdown
- The structured document has an explicit schema version
- Existing markdown download flows remain intact
- Downstream consumers do not need to parse markdown to recover semantic sections
- Historical CV rows without structured data remain supported
- Structured CV output is validated against an explicit schema before persistence
- Markdown rendering consumes the structured CV document rather than a parallel free-text generation path
- Structured CV content reflects the active preset/composition/content-rules contract for the run

## Recommendation Summary

The system should stop treating markdown as the only durable representation of a generated CV.

Instead, it should:

1. generate a structured CV document
2. render markdown from that document
3. persist both artifacts with explicit schema and generation metadata

That gives the project a stronger foundation for exports, auditing, validation, and future editing features without breaking the current markdown-based user experience.
