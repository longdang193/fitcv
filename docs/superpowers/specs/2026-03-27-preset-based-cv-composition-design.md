# Preset-Based CV Composition — Design Spec

**Date:** 2026-03-27
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

The earlier CV settings direction exposed low-level controls such as:

- raw template path
- independently editable required sections

That model is too loose for real product use.

It creates two risks:

1. admins can configure validation rules that do not match the active CV template
2. admins can change low-level template-related settings without a clear mental model of the resulting CV structure

This becomes especially problematic when the desired output is not just a generic CV, but a recognizable form such as:

- Europass

In that case, the product should let admins choose a known CV preset and configure structured composition rules inside that preset, rather than editing unrelated fields that can drift apart.

---

## Goal

Move CV generation toward a preset-based composition model where:

1. a fixed CV preset defines the structural template family
2. structured composition settings control which sections appear and how they are rendered
3. content rules constrain how the generator writes inside that structure

The first implementation should focus on one preset:

- `europass`

---

## Non-Goals

- Building a full free-form template editor
- Supporting many CV presets in the first iteration
- Allowing arbitrary custom section names in v1
- Letting admins directly edit Jinja template source in the control plane

---

## Design

### Core Model

CV generation should use three layers of control:

1. `preset`
2. `composition`
3. `content_rules`

These layers should work together, not compete.

Recommended top-level config shape:

```yaml
cv:
  preset: europass
  composition: ...
  content_rules: ...
```

---

### Preset

`preset` selects the CV template family.

For v1:

- supported value: `europass`

This should map to one known structural template implementation.

The preset should define:

- the overall document layout
- the available section types
- the expected section naming/ordering model

The preset is the structural anchor. It is not just a label.

The system should maintain an internal preset registry for allowed presets.
That registry should define, for each preset:

- supported sections
- allowed field values
- default section ordering
- preset-specific validation constraints
- the underlying template implementation bound to that preset

---

### Relationship Between Preset and Template

The system should not treat `cv_template.md` and `cv.preset` as two independent sources of truth.

Instead:

- `preset` selects the structural template
- composition rules parameterize that preset
- content rules constrain what can be written inside it

Recommended mental model:

- preset = layout skeleton
- composition = section-level inclusion and formatting rules
- content rules = writing constraints

For v1, `europass` should map to one concrete Europass-oriented template implementation.
That template mapping is an internal implementation detail of the preset registry, not an admin-facing free-form setting.
Raw template paths should no longer be the main admin abstraction in this model.

---

### Composition Model

`composition` defines which sections are enabled and how each enabled section should be rendered.

For the `europass` preset, the first supported sections should be:

- `summary`
- `education`
- `experience`
- `skills`
- `certifications`
- `projects`
- `publications`
- `languages`

Each section must use explicit typed fields rather than vague booleans or free-form text blobs.

Global section-rule semantics should be explicit:

- `enabled`
  - controls whether a section may appear at all
- `required`
  - where supported, means the generator should include that section when grounded evidence exists
  - it does not permit unsupported content invention

Global `detail` semantics should also be explicit:

- `compact`
  - minimal grounded fields, shorter phrasing, fewer bullets or sub-items
- `standard`
  - normal level of grounded detail
- `detailed`
  - richer grounded field inclusion and fuller bullets where evidence exists

`detail` controls relative verbosity, not permission to generate unsupported content.

---

### Summary Section

Recommended shape:

```yaml
summary:
  enabled: true
  style: concise
```

Supported styles:

- `concise`
- `achievement_focused`
- `skills_focused`

This controls how the summary is written, not whether unsupported content may be invented.

---

### Education Section

Recommended shape:

```yaml
education:
  enabled: true
  detail: compact
  include_institution: true
  include_major: true
  include_grade: false
  thesis:
    mode: off
    relevance_only: true
```

Supported values:

- `detail`
  - `compact`
  - `standard`
  - `detailed`
- `thesis.mode`
  - `off`
  - `title_only`
  - `short_summary`

Rules:

- if `enabled: false`, the section is omitted
- `thesis.relevance_only` only matters when `thesis.mode != off`
- the generator must not invent thesis content when no grounded evidence exists

---

### Experience Section

Recommended shape:

```yaml
experience:
  enabled: true
  require_achievements: true
  bullet_style: action_project_result
  detail: standard
```

Supported values:

- `bullet_style`
  - `standard`
  - `action_project_result`
- `detail`
  - `compact`
  - `standard`
  - `detailed`

Rules:

- `require_achievements: true` means the generator should prefer grounded achievement/result statements
- it does not permit invented achievements
- `action_project_result` means experience bullets should follow that writing structure when evidence supports it

---

### Skills and Certifications Sections

Recommended shapes:

```yaml
skills:
  enabled: true
  max_items: 12
  display_mode: grouped

certifications:
  enabled: true
  display_mode: combined_with_skills
  max_items: 5
```

Supported values:

- `skills.display_mode`
  - `grouped`
  - `flat`
- `certifications.display_mode`
  - `combined_with_skills`
  - `separate`

Rules:

- `max_items` is a display cap, not a requirement to fill the count
- `combined_with_skills` means certifications are rendered inside the broader skills/certifications area rather than as a separate standalone section heading

---

### Projects Section

Recommended shape:

```yaml
projects:
  enabled: true
  required: true
  detail: standard
```

Supported values:

- `detail`
  - `compact`
  - `standard`
  - `detailed`

Rules:

- `required: true` means the generator should include projects when grounded project evidence exists
- `required` here expresses composition intent, not permission to invent unsupported content
- it must not invent projects if the profile lacks suitable evidence
- validation may warn when a required section cannot be satisfied from grounded input, but should not encourage hallucination

---

### Publications and Languages Sections

Recommended shapes:

```yaml
publications:
  enabled: false
  detail: compact

languages:
  enabled: true
  detail: compact
```

Supported values:

- `detail`
  - `compact`
  - `standard`
  - `detailed`

These keep the section model consistent even for optional sections.

---

### Content Rules

`content_rules` should govern writing constraints that apply across sections.

Recommended first shape:

```yaml
content_rules:
  emphasize_required_skills: true
  align_jd_terminology: true
  evidence_grounded_only: true
```

Semantics:

- `emphasize_required_skills`
  - prefer inclusion of grounded required skills from the JD
- `align_jd_terminology`
  - prefer truthful wording that mirrors the JD’s terminology where supported by evidence
- `evidence_grounded_only`
  - generated content must stay grounded in candidate/profile evidence and must not invent unsupported claims

`align_jd_terminology` must not lead to blind keyword stuffing or unsupported terminology insertion.
Evidence-grounding rules remain authoritative over terminology alignment.

These rules should shape prompting and validation together.

---

### Generator and Validator Alignment

The generator and validator must consume the same `cv` config.

That means:

- preset determines the expected template family
- composition determines which sections should appear and how they should be structured
- content rules constrain writing and validation

The validator must not enforce section requirements that the chosen preset/config does not support.

Likewise, the generator must not treat config as optional advisory text while the validator treats it as hard law.

---

### Why This Is Better Than Free Template Paths

This model is better than exposing only `CV Template Path` and editable required sections because it gives admins a product-level abstraction:

- choose a known CV form
- configure section composition
- configure content rules

instead of:

- edit a path
- edit unrelated validation fields
- hope they still match

It is safer, easier to explain, and more extensible for future presets.

---

## Acceptance Criteria

- [ ] CV generation config is organized around `preset`, `composition`, and `content_rules`
- [ ] The first supported preset is `europass`
- [ ] The config supports section-level rules for `summary`, `education`, `experience`, `skills`, `certifications`, `projects`, `publications`, and `languages`
- [ ] Composition fields use explicit typed values rather than free-form template instructions
- [ ] `content_rules` includes JD-alignment and evidence-grounding controls
- [ ] Section-level `required` semantics do not permit unsupported content invention
- [ ] The chosen preset defines the allowed section/field schema consumed by both generator and validator
- [ ] JD terminology alignment does not override evidence-grounding rules
- [ ] Generator and validator are designed to consume the same preset/composition/content-rules contract
- [ ] The model avoids free-form section validation drift against the chosen template
