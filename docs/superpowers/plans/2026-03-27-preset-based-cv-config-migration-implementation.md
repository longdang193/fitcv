# Preset-Based CV Config Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate runtime CV configuration from the older flat key model to the new nested preset-based `cv` contract, while using a short-lived compatibility shim so the current control plane does not break before the preset-based admin settings plan lands.

**Architecture:** Keep `config/cv.yaml` as the single CV-owned config file, but change its structure from flat keys to a nested `cv:` object organized around `preset`, `generation`, `composition`, `content_rules`, and `validation`. Update the loader, generator, validator, and version-tracking code to consume that contract directly. During the migration, expose a temporary compatibility projection for legacy flat CV keys so existing control-plane code can continue to function until the preset-based admin settings plan replaces it. Treat template-file selection as an internal preset-registry concern rather than an admin-facing raw path setting.

**Tech Stack:** Python 3.11, YAML, pytest

---

## File Map

- **Modify:** `config/cv.yaml`
  - replace the flat CV config shape with the nested preset-based shape
- **Modify:** `src/fitcv/config.py`
  - load and validate the nested `cv` structure, and provide a temporary legacy flat-key compatibility projection
- **Add:** `src/fitcv/cv_presets.py`
  - define the internal preset registry used by config validation, generation, and validation
- **Modify:** `src/fitcv/cv_generator.py`
  - read preset/generation/composition/content-rules config
- **Modify:** `src/fitcv/validator.py`
  - validate generated CVs against composition/content-rules/validation config
- **Modify:** `src/fitcv/pipeline.py`
  - read prompt version from `cv.generation.prompt_version`
- **Modify:** `tests/test_config.py`
  - nested `cv` loader and validation coverage
- **Modify:** `tests/test_cv_generator.py`
  - generator behavior against preset-based config
- **Modify:** `tests/test_validator.py`
  - validator behavior against preset-based config
- **Modify:** `tests/conftest.py`
  - shared nested-CV fixture only if it reduces duplication
- **Modify:** `tests/test_pipeline.py`
  - pipeline helper/config fallout from nested CV config and prompt-version migration

---

## Task 1: Replace the flat CV config with the nested preset-based shape and loader support in one slice

**Files:**
- Modify: `config/cv.yaml`
- Modify: `src/fitcv/config.py`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing config-shape tests**

Add tests proving:
- `load_config()` returns a nested `cv` object
- `cv.preset` is present
- `cv.generation.model` and `cv.generation.prompt_version` are present
- `cv.validation.max_pages` is present
- temporary legacy flat CV keys are still projected for compatibility during the migration window

- [ ] **Step 2: Run focused config tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py -k "cv"
```

Expected:
- FAIL because runtime still expects the flat shape

- [ ] **Step 3: Replace `config/cv.yaml` with the nested shape**

Use the preset-based contract:
```yaml
cv:
  preset: europass
  generation:
    model: gemini-2.5-flash
    prompt_version: v1
  composition:
    summary:
      enabled: true
      style: concise
    education:
      enabled: true
      detail: compact
      include_institution: true
      include_major: true
      include_grade: false
      thesis:
        mode: off
        relevance_only: true
    experience:
      enabled: true
      require_achievements: true
      bullet_style: action_project_result
      detail: standard
    skills:
      enabled: true
      max_items: 12
      display_mode: grouped
    certifications:
      enabled: true
      display_mode: combined_with_skills
      max_items: 5
    projects:
      enabled: true
      required: true
      detail: standard
    publications:
      enabled: false
      detail: compact
    languages:
      enabled: true
      detail: compact
  content_rules:
    emphasize_required_skills: true
    align_jd_terminology: true
    evidence_grounded_only: true
  validation:
    max_pages: 2
```

- [ ] **Step 4: Update `src/fitcv/config.py` in the same slice**

Add nested validation for:
- `cv.preset`
- `cv.generation`
- `cv.composition`
- `cv.content_rules`
- `cv.validation`

Add a temporary compatibility projection that derives legacy flat keys from the nested `cv` object for downstream code that has not migrated yet.

The compatibility projection should be:
- explicit
- read-only in intent
- documented as transitional
- removed once the preset-based admin settings plan is complete

- [ ] **Step 5: Re-run focused config tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py -k "cv"
```

Expected:
- PASS
- [ ] **Step 6: Commit**

```bash
git add config/cv.yaml src/fitcv/config.py tests/test_config.py
git commit -m "feat(config): migrate cv config to preset-based shape"
```

---

## Task 2: Add the internal preset registry

**Files:**
- Add: `src/fitcv/cv_presets.py`
- Modify: `src/fitcv/config.py`
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Modify: related tests as needed

- [ ] **Step 1: Write failing preset-registry tests**

Add tests proving:
- supported preset names are centralized
- supported sections/options are centralized
- config validation, generation, and validation can all use the same registry contract

- [ ] **Step 2: Add `src/fitcv/cv_presets.py`**

Define one internal preset owner for:
- supported preset names
- section ordering
- supported section keys
- allowed enum values
- internal template mapping

Do not duplicate this mapping across `config.py`, `cv_generator.py`, and `validator.py`.

- [ ] **Step 3: Re-run focused tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py tests/test_cv_generator.py tests/test_validator.py -k "cv or preset"
```

Expected:
- PASS

- [ ] **Step 4: Commit**

```bash
git add src/fitcv/cv_presets.py src/fitcv/config.py src/fitcv/cv_generator.py \
  src/fitcv/validator.py tests/test_config.py tests/test_cv_generator.py tests/test_validator.py
git commit -m "feat(cv): add preset registry for cv composition"
```

---

## Task 3: Update CV generation to consume preset-based config

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Modify: `tests/test_cv_generator.py`

- [ ] **Step 1: Write failing generator tests**

Add tests proving:
- generator reads `cv.preset`
- generator reads `cv.generation.model`
- generator reads section-level composition rules
- generator reads content rules
- generator no longer depends on `cv_template_path`

- [ ] **Step 2: Update `cv_generator.py`**

Refactor CV generation code to:
- read from `config["cv"]`
- resolve template implementation from preset
- use composition rules to shape section inclusion and rendering instructions
- use content rules to constrain prompting

If the compatibility projection still exists in `config.py`, `cv_generator.py` must ignore it and read the nested `cv` object directly.

Do not keep a parallel flat-key code path unless it is a short-lived, clearly marked migration shim.

- [ ] **Step 3: Re-run focused generator tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_cv_generator.py
```

Expected:
- PASS

- [ ] **Step 4: Commit**

```bash
git add src/fitcv/cv_generator.py tests/test_cv_generator.py
git commit -m "refactor(cv): use preset-based generation config"
```

---

## Task 4: Update validation to consume preset-based config

**Files:**
- Modify: `src/fitcv/validator.py`
- Modify: `tests/test_validator.py`

- [ ] **Step 1: Write failing validator tests**

Add tests proving:
- validator derives section expectations from `cv.composition`
- validator uses `cv.validation.max_pages`
- validator respects `cv.content_rules.evidence_grounded_only`
- validator no longer depends on `required_cv_sections`

- [ ] **Step 2: Update `validator.py`**

Refactor validation code to:
- derive expected sections from `composition`
- treat `required` as composition intent, not permission to invent content
- keep evidence-grounding authoritative
- preserve anti-keyword-stuffing behavior when `align_jd_terminology` is enabled

If the compatibility projection still exists in `config.py`, `validator.py` must ignore it and read the nested `cv` object directly.

- [ ] **Step 3: Re-run focused validator tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_validator.py
```

Expected:
- PASS

- [ ] **Step 4: Commit**

```bash
git add src/fitcv/validator.py tests/test_validator.py
git commit -m "refactor(cv): use preset-based validation config"
```

---

## Task 5: Update version tracking and shared fixtures

**Files:**
- Modify: `src/fitcv/pipeline.py`
- Modify: `tests/conftest.py`
- Modify: `tests/test_pipeline.py`
- Modify: related tests if needed

- [ ] **Step 1: Update prompt-version reads**

Replace legacy reads with:
```python
config["cv"]["generation"]["prompt_version"]
```

- [ ] **Step 2: Align fixtures with nested CV config**

Use one shared fixture or helper only if it reduces duplication.
Avoid a second config-loading path.

- [ ] **Step 3: Update pipeline tests and helpers**

Replace flat CV config assumptions in pipeline tests/helpers with nested `cv` config assumptions.
Do not let `tests/test_pipeline.py` become the last consumer of the flat runtime shape.

- [ ] **Step 4: Re-run focused tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_config.py \
  tests/test_cv_generator.py \
  tests/test_validator.py \
  tests/test_pipeline.py
```

Expected:
- PASS

- [ ] **Step 5: Commit**

```bash
git add src/fitcv/pipeline.py tests/conftest.py \
  tests/test_config.py tests/test_cv_generator.py tests/test_validator.py \
  tests/test_pipeline.py
git commit -m "refactor(cv): align runtime and tests with nested cv config"
```

---

## Task 6: Preserve compatibility for the current control plane until plan 2 lands

**Files:**
- Modify: `src/fitcv/config.py`
- Modify: control-plane tests only if needed to prove compatibility

- [ ] **Step 1: Add one focused compatibility test**

Add a test proving the current control-plane flat CV reads still work through the compatibility projection after the nested `cv` migration.

This is a temporary migration guard, not a long-term contract.

- [ ] **Step 2: Document shim removal boundary**

Add a code comment and plan note that this compatibility projection must be removed once:
- the preset-based admin CV settings plan is complete
- control-plane settings schema no longer reads the old flat CV keys

- [ ] **Step 3: Re-run focused compatibility tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py tests/test_fitcv_cp/test_settings_schema.py -k "cv"
```

Expected:
- PASS

---

## Task 7: Full verification

- [ ] **Step 1: Run focused CV/config tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short \
  tests/test_config.py \
  tests/test_cv_generator.py \
  tests/test_validator.py \
  tests/test_pipeline.py
```

- [ ] **Step 2: Run broader non-integration suite**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
```

- [ ] **Step 3: Manual verification**

Check:
- config loads the nested `cv` contract
- Europass CV generation still works
- validation follows composition/content rules
- generated CV version records still carry the configured prompt version
- current control-plane CV settings paths still function through the temporary compatibility projection

---

## Important Notes

- **Do not keep two equal-status CV config models.** The flat shape should be removed, not preserved indefinitely.
- **Preset chooses structure.** Raw template-file mapping should remain internal.
- **Validation must match generation.** Generator and validator must consume the same preset/composition/content-rules contract.
- **Required does not permit invention.** Composition intent never overrides evidence-grounding.
- **Compatibility is temporary.** The flat-key projection exists only to keep the current control plane stable until the preset-based admin settings plan replaces it.
