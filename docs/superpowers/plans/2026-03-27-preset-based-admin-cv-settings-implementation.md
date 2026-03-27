# Preset-Based Admin CV Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fully admin-editable preset-based `CV Generation` settings area that edits the nested `cv` contract through structured preset-aware controls instead of raw template paths or free-form required-section lists.

**Architecture:** Extend the control-plane settings schema so admin-editable fields map onto the nested `cv` config structure. Render a top-level `CV Generation` section in the settings page with grouped `Preset`, `Composition`, `Content Rules`, and `Validation` sub-cards. Reuse the existing grouped-save endpoint and validate-first semantics so CV settings behave like the rest of the settings system.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, pytest

---

## File Map

- **Modify:** `src/fitcv_cp/settings_schema.py`
  - register preset-based CV settings and grouped registries
- **Modify:** `src/fitcv_cp/app.py`
  - accept grouped CV settings saves and write nested config paths
- **Modify:** `src/fitcv_cp/templates/settings.html`
  - render the preset-based CV settings section
- **Modify:** `tests/test_fitcv_cp/test_settings_schema.py`
  - schema and validation coverage for preset-based CV settings
- **Modify:** `tests/test_fitcv_cp/test_app.py`
  - grouped-save and rendering coverage for preset-based CV settings

---

## Task 1: Add preset-based CV settings to the schema

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`

- [ ] **Step 1: Write failing schema tests**

Add tests proving:
- `cv_preset` exists
- generation fields exist
- preset-aware composition fields exist
- content-rule fields exist
- validation fields exist
- CV group registries exist for `preset`, `composition`, `content-rules`, and `validation`

- [ ] **Step 2: Add schema entries**

Register fields such as:
- `cv_preset`
- `cv_generation_model`
- `cv_prompt_version`
- `cv_summary_style`
- `cv_education_enabled`
- `cv_education_detail`
- `cv_experience_enabled`
- `cv_experience_bullet_style`
- `cv_skills_enabled`
- `cv_skills_max_items`
- `cv_certifications_enabled`
- `cv_projects_enabled`
- `cv_projects_required`
- `cv_emphasize_required_skills`
- `cv_align_jd_terminology`
- `cv_evidence_grounded_only`
- `cv_max_pages`

Use typed schema support:
- `enum`
- `bool`
- `int`
- `str`

- [ ] **Step 3: Add grouped registries**

Example:
```python
CV_GROUPS = {
    "cv-preset": [...],
    "cv-composition": [...],
    "cv-content-rules": [...],
    "cv-validation": [...],
}
```

- [ ] **Step 4: Re-run schema tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "cv"
```

- [ ] **Step 5: Commit**

```bash
git add src/fitcv_cp/settings_schema.py tests/test_fitcv_cp/test_settings_schema.py
git commit -m "feat(cp): add preset-based cv settings schema"
```

---

## Task 2: Add preset-aware validation rules

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Modify: `tests/test_fitcv_cp/test_settings_schema.py`

- [ ] **Step 1: Write failing validation tests**

Add tests proving:
- unsupported `cv_preset` values are rejected
- whitespace-only strings are rejected
- enum fields reject unsupported values
- integer caps reject values `< 1`
- validate-first semantics apply to each CV subgroup

- [ ] **Step 2: Implement validation**

Validation should:
- trim text before validation
- validate enum values against preset-supported options
- preserve stable mapping into nested `cv` config paths
- reject invalid submissions without partial subgroup writes

- [ ] **Step 3: Re-run validation tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "cv"
```

- [ ] **Step 4: Commit**

```bash
git add src/fitcv_cp/settings_schema.py tests/test_fitcv_cp/test_settings_schema.py
git commit -m "feat(cp): validate preset-based cv settings"
```

---

## Task 3: Reuse grouped-save flow for nested CV settings

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 1: Write failing app tests**

Add tests proving:
- grouped-save route accepts CV preset submissions
- grouped-save route accepts composition/content-rule/validation submissions
- invalid subgroup submissions do not partially save
- nested config paths are written correctly

- [ ] **Step 2: Update grouped-save route**

Generalize route handling so it supports:
- ranking groups
- preset-based CV groups

Do not add a second custom CV persistence path.

- [ ] **Step 3: Re-run app tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "cv_preset or cv_composition or cv_validation or settings_group"
```

- [ ] **Step 4: Commit**

```bash
git add src/fitcv_cp/app.py tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): support grouped preset-based cv settings saves"
```

---

## Task 4: Render the preset-based CV settings UI

**Files:**
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 1: Write failing rendering tests**

Add tests proving the settings page renders:
- `CV Generation`
- `Preset`
- `Composition`
- `Content Rules`
- `Validation`
- grouped save actions for each subgroup
- preset-aware typed controls
- no raw template-path field
- no free-form required-sections editor

- [ ] **Step 2: Render `Preset` controls**

Use:
- preset select
- generation model text input
- prompt version text input

- [ ] **Step 3: Render `Composition` controls**

Use preset-aware typed controls:
- select inputs for enum fields
- checkboxes/toggles for booleans
- numeric inputs for caps

If one composition card is too dense, split by section family while keeping preset-aware grouping.

- [ ] **Step 4: Render `Content Rules` and `Validation` controls**

Use:
- toggles for content rules
- numeric input for max pages

- [ ] **Step 5: Preserve subgroup errors and draft values**

Reuse existing grouped-save error handling:
- subgroup-level error messages
- no partial writes
- preserve submitted values on validation failure

- [ ] **Step 6: Re-run rendering tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "settings_page and cv"
```

- [ ] **Step 7: Commit**

```bash
git add src/fitcv_cp/templates/settings.html src/fitcv_cp/app.py \
  tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): render preset-based cv settings ui"
```

---

## Task 5: Full verification

- [ ] **Step 1: Run control-plane tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short tests/test_fitcv_cp
```

- [ ] **Step 2: Manual verification**

Check in browser:
- `CV Generation` renders as a first-class settings section
- preset-aware controls are visible
- grouped saves validate before write
- no raw template path field is exposed
- no free-form required-sections editor is exposed

---

## Important Notes

- **Do not expose raw template paths in the new UI.** Preset is the admin-facing abstraction.
- **Do not revive free-form required sections.** Section expectations come from composition controls.
- **Keep the grouped-save model.** CV settings should reuse the existing settings system.
- **Keep preset and runtime aligned.** The control-plane schema must map cleanly onto the nested `cv` config contract.
