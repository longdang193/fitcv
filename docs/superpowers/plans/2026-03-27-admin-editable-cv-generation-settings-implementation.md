# Admin-Editable CV Generation Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a fully admin-editable `CV Generation` section to the settings page, with grouped `Generation` and `Validation` forms that integrate with the existing settings schema, grouped-save flow, and validation model.

**Architecture:** Extend the existing settings registry in `settings_schema.py` with CV-owned keys and two new grouped-form registries, then render those groups in `settings.html` using the same section-card and sub-card patterns already used for ranking. Reuse the current grouped save endpoint and validate-first persistence model so CV settings behave like first-class settings-system citizens rather than a one-off editor.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, BigQuery-backed settings store, pytest

**Status:** ✅ All tasks complete — committed at `ca1f111`

---

## File Map

- **Modify:** `src/fitcv_cp/settings_schema.py`
  - register CV settings, validation rules, and grouped-form registries
- **Modify:** `src/fitcv_cp/app.py`
  - extend grouped-save route handling so CV groups can use the existing validate-first settings flow
- **Modify:** `src/fitcv_cp/templates/settings.html`
  - render the new `CV Generation` section with `Generation` and `Validation` sub-cards
- **Modify:** `tests/test_fitcv_cp/test_settings_schema.py`
  - schema, validation, and group-registry coverage for CV settings
- **Modify:** `tests/test_fitcv_cp/test_app.py`
  - grouped-save endpoint coverage and settings-page rendering assertions for CV settings

---

## Task 1: Add CV settings to the admin settings schema

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Test: `tests/test_fitcv_cp/test_settings_schema.py`

- [x] **Step 1: Write failing settings-schema tests for CV keys**

Add tests proving:
- CV settings are registered in `SETTINGS_SCHEMA`
- CV settings have the correct group and defaults
- new CV group registries exist for `generation` and `validation`
- `pipeline.evidence_top_k` remains outside the CV section/grouping

Example:
```python
def test_cv_settings_keys_registered():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "cv_generation_model" in keys
    assert "cv_template_path" in keys
    assert "prompt_version" in keys
    assert "required_cv_sections" in keys
    assert "cv_max_pages" in keys
```

- [x] **Step 2: Run the targeted schema tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "cv"
```

Expected:
- FAIL because no CV settings are registered yet

- [x] **Step 3: Add CV-owned schema entries in `settings_schema.py`**

Register:
- `cv_generation_model`
- `cv_template_path`
- `prompt_version`
- `required_cv_sections`
- `cv_max_pages`

Recommended grouping:
- group name: `cv_generation`

Recommended types:
- text/list values should use explicit support in the schema model rather than pretending they are numeric
- `cv_max_pages` remains integer

If the schema currently only supports `int` / `float`, extend it carefully to support:
- `str`
- `list[str]`

Do not overload numeric-only validation paths for CV text/list fields.

- [x] **Step 4: Add grouped registries for CV subgroup saves**

Add a dedicated grouped registry alongside `RANKING_GROUPS`, for example:
```python
CV_GROUPS = {
    "cv-generation": [
        "cv_generation_model",
        "cv_template_path",
        "prompt_version",
    ],
    "cv-validation": [
        "required_cv_sections",
        "cv_max_pages",
    ],
}
```

This keeps CV grouped saves structurally separate from ranking while still using the same grouped-save machinery.

- [x] **Step 5: Re-run the targeted schema tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "cv"
```

Expected:
- PASS

- [x] **Step 6: Commit**

```bash
git add src/fitcv_cp/settings_schema.py tests/test_fitcv_cp/test_settings_schema.py
git commit -m "feat(cp): add cv generation settings schema"
```

---

## Task 2: Add CV-specific validation rules and validate-first grouped semantics

**Files:**
- Modify: `src/fitcv_cp/settings_schema.py`
- Test: `tests/test_fitcv_cp/test_settings_schema.py`

- [x] **Step 1: Write failing validation tests for CV fields**

Add tests proving:
- `cv_generation_model` rejects empty/whitespace-only values
- `cv_template_path` rejects empty/whitespace-only values
- `prompt_version` rejects empty/whitespace-only values
- `required_cv_sections` rejects empty lists
- `required_cv_sections` rejects empty/whitespace-only items
- `required_cv_sections` rejects duplicates while preserving order otherwise
- `cv_max_pages` rejects values `< 1`

Example:
```python
def test_required_cv_sections_reject_duplicates():
    with pytest.raises(ValidationError, match="required_cv_sections"):
        validate_settings({"required_cv_sections": ["Summary", "Summary"]})
```

- [x] **Step 2: Run the targeted validation tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "required_cv_sections or cv_template_path or prompt_version or cv_max_pages"
```

Expected:
- FAIL because CV field validation does not exist yet

- [x] **Step 3: Extend `validate_settings()` for CV field types**

Implement explicit validation rules:
- trim strings before emptiness checks
- reject whitespace-only text
- for `required_cv_sections`:
  - require list type
  - preserve order
  - reject blank entries
  - reject duplicates
- keep `cv_max_pages` on the integer `>= 1` path

Make validation messages field-specific and admin-readable.

- [x] **Step 4: Ensure config application preserves `required_cv_sections` order**

`apply_settings_to_config()` must write the list in its validated order without sorting or deduplicating silently.

- [x] **Step 5: Re-run the targeted validation tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_settings_schema.py -k "required_cv_sections or cv_template_path or prompt_version or cv_max_pages"
```

Expected:
- PASS

- [x] **Step 6: Commit**

```bash
git add src/fitcv_cp/settings_schema.py tests/test_fitcv_cp/test_settings_schema.py
git commit -m "feat(cp): validate cv settings fields and groups"
```

---

## Task 3: Reuse the grouped-save endpoint for CV groups

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 1: Write failing app tests for CV grouped saves**

Add tests proving:
- the grouped-save endpoint accepts CV generation group submissions
- the grouped-save endpoint accepts CV validation group submissions
- invalid CV grouped submissions return a validation error without partial write
- `required_cv_sections` is submitted and preserved as an ordered structured value

Example:
```python
def test_post_admin_settings_group_cv_generation_saves_all_keys():
    ...
```

- [x] **Step 2: Run the targeted app tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "cv_generation or cv_validation or settings_group"
```

Expected:
- FAIL because the grouped-save route only knows ranking groups today

- [x] **Step 3: Generalize grouped-save route handling in `app.py`**

Refactor the route so it can work with:
- ranking groups
- CV groups

Recommended approach:
- create one combined grouped-registry lookup in `settings_schema.py` or in `app.py`
- keep slug ownership explicit
- do not hardcode another separate CV-only persistence path

Important rule:
- grouped saves must still validate the full subgroup before writing any keys

- [x] **Step 4: Support structured list input for `required_cv_sections`**

Decide one HTML form encoding pattern and use it consistently.

Recommended first pass:
- repeated inputs using the same `name="required_cv_sections"`
- `request.form().getlist("required_cv_sections")` in `app.py`

This keeps the form HTML simple and avoids inventing JSON blobs in the UI.

- [x] **Step 5: Re-run the targeted app tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "cv_generation or cv_validation or settings_group"
```

Expected:
- PASS

- [x] **Step 6: Commit**

```bash
git add src/fitcv_cp/app.py tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): support grouped cv settings saves"
```

---

## Task 4: Render the `CV Generation` section in `settings.html`

**Files:**
- Modify: `src/fitcv_cp/templates/settings.html`
- Modify: `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 1: Write failing rendering tests for the new section**

Add tests proving the settings page renders:
- top-level `CV Generation` section
- `Generation` sub-card
- `Validation` sub-card
- inputs for model, template path, prompt version, required sections, and max pages
- grouped save buttons for each subgroup
- no raw YAML textarea for `Required CV Sections`

Example:
```python
def test_admin_settings_page_renders_cv_generation_section():
    resp = client.get("/admin/settings")
    assert "CV Generation" in resp.text
    assert "Save Generation Settings" in resp.text
    assert "Save Validation Settings" in resp.text
```

- [x] **Step 2: Run the targeted rendering tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "settings_page and cv"
```

Expected:
- FAIL because the section is not rendered yet

- [x] **Step 3: Add the top-level `CV Generation` section**

In `settings.html`:
- render a new outer `section-card`
- use the same outer composition model as other settings sections

Inside it:
- render `Generation` sub-card
- render `Validation` sub-card

Do not merge these into one uninterrupted block.

- [x] **Step 4: Render `Generation` controls**

Use:
- text input for `cv_generation_model`
- text input for `cv_template_path`
- text input for `prompt_version`
- one grouped footer action: `Save Generation Settings`

Label `CV Template Path` as an advanced setting with helper text.
Label `Prompt Version` as a traceability/version setting, not prompt-editing UI.

- [x] **Step 5: Render `Validation` controls**

Use:
- repeated text inputs for `required_cv_sections`
- numeric input for `cv_max_pages`
- one grouped footer action: `Save Validation Settings`

Support add/remove behavior in a lightweight way.
The first pass may use small client-side JS to add/remove repeated inputs.

Do not expose raw YAML editing for section names.

- [x] **Step 6: Surface subgroup errors without losing draft values**

Reuse the existing grouped-save error pattern:
- subgroup-level error message
- preserve submitted values after validation failure
- preserve section list order on failed submit

- [x] **Step 7: Re-run the targeted rendering tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "settings_page and cv"
```

Expected:
- PASS

- [x] **Step 8: Commit**

```bash
git add src/fitcv_cp/templates/settings.html src/fitcv_cp/app.py \
  tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): render admin-editable cv settings section"
```

---

## Task 5: Full verification

**Files:**
- No new product files

- [x] **Step 1: Run control-plane settings tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short \
  tests/test_fitcv_cp/test_settings_schema.py \
  tests/test_fitcv_cp/test_app.py
```

Expected:
- PASS

- [x] **Step 2: Run broader control-plane suite**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short tests/test_fitcv_cp
```

Expected:
- PASS

- [x] **Step 3: Manual verification**

Check in browser:
- settings page shows `CV Generation` as a top-level section
- `Generation` and `Validation` render as sibling grouped sub-cards
- `Required CV Sections` can be added/removed without raw YAML editing
- invalid grouped submissions do not partially save
- `CV Template Path` appears as an advanced field

- [x] **Step 4: Final commit**

```bash
git status --short
git add src/fitcv_cp/settings_schema.py src/fitcv_cp/app.py \
  src/fitcv_cp/templates/settings.html \
  tests/test_fitcv_cp/test_settings_schema.py tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): add admin-editable cv generation settings"
```

---

## Important Notes

- **Do not create a custom CV settings backend.** Reuse the existing settings schema and grouped-save flow.
- **Validate before writing.** CV grouped saves must not partially persist invalid subgroup submissions.
- **Keep ownership boundaries clean.** `pipeline.evidence_top_k` stays outside the `CV Generation` section.
- **Use structured list editing.** `Required CV Sections` should be submitted as repeated structured values, not raw YAML text.
- **Trim before validation.** Whitespace-only text values should be rejected as invalid.
