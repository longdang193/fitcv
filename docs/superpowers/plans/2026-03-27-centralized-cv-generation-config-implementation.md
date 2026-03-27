# Centralized CV Generation Config Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a dedicated `config/cv.yaml` config boundary for CV generation and validation, remove competing CV-specific code defaults, and make CV tests consume one shared config contract.

**Architecture:** Extend the existing config loader to merge a new `cv.yaml` layer into the runtime config without changing the overall loader shape. Move CV-owned defaults into `config/cv.yaml`, validate required CV keys during config loading, and update CV generation, validation, and version-tracking code to read those settings from config rather than silently falling back in business logic.

**Tech Stack:** Python 3.11, YAML, pytest

---

## File Map

- **Add:** `config/cv.yaml`
  - CV generation and validation defaults
- **Modify:** `src/fitcv/config.py`
  - merge `cv.yaml`, validate required CV keys, and keep existing config precedence rules
- **Modify:** `config/env.yaml`
  - remove CV-owned defaults that should now live in `cv.yaml`
- **Modify:** `src/fitcv/cv_generator.py`
  - stop relying on embedded defaults for `cv_template_path` and `cv_generation_model`
- **Modify:** `src/fitcv/validator.py`
  - stop relying on embedded defaults for `required_cv_sections` and `cv_max_pages`
- **Modify:** `src/fitcv/pipeline.py`
  - stop relying on embedded fallback for `prompt_version` when versioning generated CVs
- **Modify:** `tests/test_config.py`
  - loader and validation coverage for `cv.yaml`
- **Modify:** `tests/test_cv_generator.py`
  - shared config fixture / required-key expectations
- **Modify:** `tests/test_validator.py`
  - shared config fixture / required-key expectations if needed
- **Modify:** `tests/conftest.py`
  - optional shared CV-config fixture helper if that reduces repeated inline test config

---

## Task 1: Add `config/cv.yaml` and teach the loader to merge it

**Files:**
- Add: `config/cv.yaml`
- Modify: `src/fitcv/config.py`
- Test: `tests/test_config.py`

- [x] **Step 1: Write failing config-loader tests**

Add tests proving:
- `load_config()` now merges `config/cv.yaml`
- CV keys are present in the final config
- missing required CV keys fail validation
- `.env.yaml` still has precedence over lower config layers when overlap exists

Example:
```python
def test_load_config_includes_cv_defaults() -> None:
    cfg = load_config()
    assert cfg["cv_generation_model"] == "gemini-2.5-flash"
    assert cfg["cv_template_path"]
    assert cfg["prompt_version"]
```

- [x] **Step 2: Run config tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py
```

Expected:
- FAIL because `cv.yaml` is not loaded yet and CV-key validation does not exist

- [x] **Step 3: Create `config/cv.yaml`**

Add a dedicated config file containing the first CV-owned defaults.

Recommended first shape:
```yaml
cv_generation_model: gemini-2.5-flash
cv_template_path: templates/cv_template.md
required_cv_sections:
  - Summary
  - Skills
  - Experience
cv_max_pages: 2
prompt_version: v1
```

Keep the first implementation flat if that matches the current loader more cleanly.

- [x] **Step 4: Extend `src/fitcv/config.py`**

Update the policy-file merge list to include:
```python
"cv.yaml"
```

Add explicit CV-key validation after config merging:
```python
_REQUIRED_CV_KEYS = [
    "cv_generation_model",
    "cv_template_path",
    "required_cv_sections",
    "cv_max_pages",
    "prompt_version",
]
```

Validation rules should ensure:
- required keys exist
- `required_cv_sections` is a non-empty list
- `cv_max_pages` is a positive integer

Missing or invalid CV-owned config should fail during config loading rather than later inside business logic.

- [x] **Step 5: Re-run config tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py
```

Expected:
- PASS

- [x] **Step 6: Commit**

```bash
git add config/cv.yaml src/fitcv/config.py tests/test_config.py
git commit -m "feat(config): add centralized cv config layer"
```

---

## Task 2: Remove CV-owned defaults from runtime code

**Files:**
- Modify: `src/fitcv/cv_generator.py`
- Modify: `src/fitcv/validator.py`
- Modify: `src/fitcv/pipeline.py`
- Test: `tests/test_cv_generator.py`
- Test: `tests/test_validator.py`

- [x] **Step 1: Write failing focused tests for missing in-code CV defaults**

Add or update tests proving:
- `generate_cv()` expects `cv_template_path` and `cv_generation_model` to come from config
- validator expects `required_cv_sections` and `cv_max_pages` to come from config
- pipeline versioning reads `prompt_version` from config without silently injecting `"v1"` in code

Examples:
```python
def test_generate_cv_uses_configured_template_and_model(...):
    ...

def test_run_all_validations_uses_configured_sections_and_page_limit(...):
    ...
```

- [x] **Step 2: Run the targeted tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_cv_generator.py \
  tests/test_validator.py
```

Expected:
- FAIL once tests are tightened to reject embedded code defaults

- [x] **Step 3: Remove CV-owned fallback defaults in `cv_generator.py`**

Replace code like:
```python
config.get("cv_template_path") or "templates/cv_template.md"
config.get("cv_generation_model") or "gemini-2.5-flash"
```

with direct config reads that assume loader validation already happened:
```python
template_path = str(config["cv_template_path"])
model_name = str(config["cv_generation_model"])
```

- [x] **Step 4: Remove CV-owned fallback defaults in `validator.py`**

Replace code like:
```python
config.get("required_cv_sections") or ["Summary", "Skills", "Experience"]
int(config.get("cv_max_pages") or 2)
```

with validated config reads:
```python
required_sections = list(config["required_cv_sections"])
max_pages = int(config["cv_max_pages"])
```

- [x] **Step 5: Remove CV-owned fallback default in `pipeline.py`**

Replace:
```python
prompt_version=str(config.get("prompt_version") or "v1")
```

with:
```python
prompt_version=str(config["prompt_version"])
```

This keeps CV version metadata aligned with the centralized CV config contract.

- [x] **Step 6: Re-run the targeted tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_cv_generator.py \
  tests/test_validator.py
```

Expected:
- PASS

- [x] **Step 7: Commit**

```bash
git add src/fitcv/cv_generator.py src/fitcv/validator.py src/fitcv/pipeline.py \
  tests/test_cv_generator.py tests/test_validator.py
git commit -m "refactor(cv): remove hardcoded cv config defaults"
```

---

## Task 3: Remove duplicated CV-owned values from shared env config

**Files:**
- Modify: `config/env.yaml`
- Modify: `tests/test_config.py`

- [x] **Step 1: Write or update a config test covering precedence after cleanup**

Add a test proving:
- CV defaults are still available after removing CV-owned keys from `config/env.yaml`
- higher-precedence overrides still work when intentionally provided

- [x] **Step 2: Run the focused config test to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py -k "cv"
```

Expected:
- FAIL if the test is added before env cleanup / precedence verification

- [x] **Step 3: Remove CV-owned defaults from `config/env.yaml`**

Delete:
- `prompt_version`

Do not move non-CV settings.

If `config/env.yaml` later contains any of:
- `cv_generation_model`
- `cv_template_path`
- `required_cv_sections`
- `cv_max_pages`

remove those too unless they are intentionally being used as environment-specific overrides.

- [x] **Step 4: Re-run focused config tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_config.py -k "cv"
```

Expected:
- PASS

- [x] **Step 5: Commit**

```bash
git add config/env.yaml tests/test_config.py
git commit -m "chore(config): remove duplicated cv defaults from env config"
```

---

## Task 4: Align shared test fixtures with `cv.yaml`

**Files:**
- Modify: `tests/conftest.py`
- Modify: `tests/test_cv_generator.py`
- Modify: `tests/test_validator.py`

- [x] **Step 1: Write failing tests or fixture assertions**

Add or update tests so they stop depending on repeated inline CV default literals where shared fixture config is more appropriate.

Example fixture shape:
```python
@pytest.fixture
def cv_config(config: dict[str, object]) -> dict[str, object]:
    return {
        **config,
        "cv_template_path": "templates/cv_template.md",
    }
```

Use the shared fixture where it reduces repetition and keeps tests aligned with the real config contract.

- [x] **Step 2: Run focused CV tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_cv_generator.py \
  tests/test_validator.py
```

Expected:
- FAIL until tests are aligned with the shared fixture / updated config contract

- [x] **Step 3: Add or refine shared fixtures**

In `tests/conftest.py`, add a small shared fixture only if it genuinely reduces duplication.

Keep it minimal:
- reuse the existing loaded `config` fixture
- do not create a second ad hoc config-loading path

- [x] **Step 4: Update CV-related tests**

Refactor tests to:
- rely on loader-backed config where appropriate
- override only the specific values each test cares about
- avoid duplicating now-centralized defaults unless the test is explicitly about overriding them

- [x] **Step 5: Re-run focused CV tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_cv_generator.py \
  tests/test_validator.py
```

Expected:
- PASS

- [x] **Step 6: Commit**

```bash
git add tests/conftest.py tests/test_cv_generator.py tests/test_validator.py
git commit -m "test(cv): align fixtures with centralized cv config"
```

---

## Task 5: Full verification

**Files:**
- No new product files

- [x] **Step 1: Run config and CV-focused tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short \
  tests/test_config.py \
  tests/test_cv_generator.py \
  tests/test_validator.py
```

Expected:
- PASS

- [x] **Step 2: Run broader non-integration suite**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
```

Expected:
- PASS

- [x] **Step 3: Manual verification**

Check:
- `load_config()` includes keys from `config/cv.yaml`
- CV generation still works with the configured template path and model
- validation still uses configured required sections and page limits
- generated CV version records still carry the configured `prompt_version`

- [x] **Step 4: Final commit**

```bash
git status --short
git add config/cv.yaml config/env.yaml src/fitcv/config.py \
  src/fitcv/cv_generator.py src/fitcv/validator.py src/fitcv/pipeline.py \
  tests/conftest.py tests/test_config.py tests/test_cv_generator.py tests/test_validator.py
git commit -m "feat(config): centralize cv generation settings"
```

---

## Important Notes

- **Keep config ownership clear.** `pipeline.evidence_top_k` remains outside `cv.yaml`.
- **Validate, don’t silently fall back.** Missing CV-owned config should fail during config loading.
- **Keep path semantics consistent.** `cv_template_path` should follow the project’s normal config-path resolution convention in both runtime code and tests.
- **Do not redesign the whole loader.** This plan extends the existing config layering instead of replacing it.

---

## Completion Log

_Completed: 2026-03-27_

### Commit

| Commit | Description |
|---|---|
| `374c8f4` | `feat(config): centralize cv generation settings` — all 5 tasks, 9 files changed, 157 insertions |

### What was done

#### Task 1: `config/cv.yaml` + loader extension ✅
- Created `config/cv.yaml` with CV-owned defaults
- Added `"cv.yaml"` to `_POLICY_FILES` in `config.py`
- Added `_REQUIRED_CV_KEYS` list and `_validate_cv_config()` — validates required keys, non-empty list, positive int
- Added 5 new TDD tests to `test_config.py`

#### Task 2: Remove fallback defaults from runtime code ✅
- `cv_generator.py`: replaced `config.get("cv_template_path") or "..."` and `config.get("cv_generation_model") or "..."` with direct `config[key]` access
- `validator.py`: replaced `config.get("required_cv_sections") or [...]` and `config.get("cv_max_pages") or 2` with direct access
- `pipeline.py`: replaced `config.get("prompt_version") or "v1"` with `config["prompt_version"]`
- Updated `test_validator.py` to add `_CV_CONFIG` constant and pass it to `run_all_validations` tests that previously used `config={}`

#### Task 3: Clean env.yaml ✅
- Removed `prompt_version: "v1"` from `config/env.yaml` — now owned exclusively by `cv.yaml`

#### Task 4: Align test fixtures ✅
- No new conftest fixture needed — `conftest.py` `config` fixture already loads the full config (now includes cv.yaml keys)
- `test_pipeline.py`: added 5 CV keys to `_minimal_config()` to fix `KeyError: 'prompt_version'` failures

#### Task 5: Full verification ✅
- 69 focused tests pass: `test_config.py` (13), `test_cv_generator.py` (18), `test_validator.py` (21), `test_pipeline.py` (17)
