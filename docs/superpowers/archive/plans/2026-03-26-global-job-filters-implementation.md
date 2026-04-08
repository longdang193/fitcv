# Global Job Filters — Implementation Plan

> **Status: COMPLETE** — Committed on `feat/admin-control-plane` in two commits:
> - `9f35570` feat: add global job filters (applicant count + freshness migration)
> - `b50a2f9` fix: add global_job_filters to settings.html groups list

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add two admin-managed global job filters (`global_job_filters.applications_count_max`, `global_job_filters.max_age_days`) and migrate freshness checking from the candidate-preference layer to the admin settings layer.

**Spec:** `docs/superpowers/specs/2026-03-26-global-job-filters-design.md`

**Scope:** Two filters only. `min_description_length` is intentionally deferred per spec.

**Resolved decisions:**
- Namespace: `global_job_filters.*` everywhere (settings keys, config paths, group name)
- `max_age_days` migration: clean cut — `check_freshness` no longer reads `prefs.get("max_age_days")`. Reject reason stays `job_too_stale`.
- Fail-open: `NULL` for either field → skip check (no rejection)

---

## File Map

- **Modify:** `src/fitcv/rule_filter.py`
- **Modify:** `src/fitcv_cp/settings_schema.py`
- **Modify:** `src/fitcv/pipeline.py`
- **Modify:** `tests/test_rule_filter.py`
- **Modify:** `tests/test_fitcv_cp/test_settings_schema.py`
- **Modify:** `tests/test_pipeline.py` _(new: settings→config→filter integration path)_

---

## Task 1: Extend `rule_filter.py` with global filter checks

**File:** `src/fitcv/rule_filter.py`

- [x] **Step 1.1: Add `global_settings` parameter to `apply_rule_filters`**

  ```python
  def apply_rule_filters(
      jobs: list[dict[str, Any]],
      prefs: dict[str, Any],
      config: dict[str, Any] | None = None,
      global_settings: dict[str, Any] | None = None,
  ) -> dict[str, list]:
  ```

  `global_settings` carries the flattened admin values under the `global_job_filters.*` namespace. Defaults to `None` → all global checks are skipped (fully backward-compatible).

- [x] **Step 1.2: Implement `check_applicant_count`**

  ```python
  def check_applicant_count(
      job: dict[str, Any], global_settings: dict[str, Any]
  ) -> bool:
      """Return True if applications_count is within the admin threshold.

      NULL applications_count → pass (fail open).
      """
      max_count = global_settings.get("global_job_filters.applications_count_max")
      if max_count is None:
          return True  # filter not configured
      count = job.get("applications_count")
      if count is None:
          return True  # fail open
      return int(count) <= int(max_count)
  ```

  Reject reason: `applications_count_exceeded`

- [x] **Step 1.3: Migrate `check_freshness` — clean cut from prefs**

  Change signature:
  ```python
  def check_freshness(
      job: dict[str, Any],
      global_settings: dict[str, Any] | None = None,
  ) -> bool:
  ```

  Resolution order:
  1. `global_settings.get("global_job_filters.max_age_days")` — admin setting
  2. If `global_settings` is `None` or key is absent → use hard-coded default `30`

  **Remove** `prefs.get("max_age_days")` lookup entirely. Candidate profiles no longer control posting-age filtering.

  NULL/unparseable `published_at` → continue to return `True` (fail open — existing behaviour, unchanged).

- [x] **Step 1.4: Wire global checks into the `checks` list**

  Replace the existing `("job_too_stale", check_freshness)` tuple with:

  ```python
  ("job_too_stale", lambda j, p: check_freshness(j, global_settings)),
  ```

  After the main candidate-driven `checks` list, append global checks when configured:

  ```python
  if global_settings:
      checks.append(
          ("applications_count_exceeded",
           lambda j, p: check_applicant_count(j, global_settings)),
      )
  ```

  Keep the freshness check in the main list (it always runs, now driven by admin settings or the hard default).

- [x] **Step 1.5: Update module docstring** — add `check_applicant_count` and revised `check_freshness` signature to the Public API table.

---

## Task 2: Register settings in `settings_schema.py`

**File:** `src/fitcv_cp/settings_schema.py`

- [x] **Step 2.1: Add `global_job_filters` group**

  Append two entries to `SETTINGS_SCHEMA`:

  ```python
  # ── Global Job Filters ─────────────────────────────────────────────────────
  {
      "key": "global_job_filters.applications_count_max",
      "type": "int",
      "default": 200,
      "label": "Maximum Applicant Count",
      "description": "Reject jobs when the applicant count exceeds this threshold.",
      "group": "global_job_filters",
      "config_path": ["global_job_filters", "applications_count_max"],
  },
  {
      "key": "global_job_filters.max_age_days",
      "type": "int",
      "default": 30,
      "label": "Maximum Posting Age (Days)",
      "description": "Reject jobs when the posting is older than this many days. Missing posted date is treated as passing.",
      "group": "global_job_filters",
      "config_path": ["global_job_filters", "max_age_days"],
  },
  ```

- [x] **Step 2.2: Update `validate_settings` for `global_job_filters.*`**

  Both are positive-integer settings. The existing `int >= 1` rule applies correctly — `applications_count_max` and `max_age_days` should both be `>= 1`. No special-case branch needed.

---

## Task 3: Thread `global_settings` through pipeline

**File:** `src/fitcv/pipeline.py`

- [x] **Step 3.1: Extract `global_job_filters` from config and pass to filter stage**

  `apply_settings_to_config` already writes admin settings into the config dict via `config_path`. At the filter call site:

  ```python
  # Build a flat global_settings dict for rule_filter (mirroring the schema key format)
  raw_global = config.get("global_job_filters", {})
  global_settings = {
      f"global_job_filters.{k}": v for k, v in raw_global.items()
  } if raw_global else None

  filter_result = apply_rule_filters(
      enriched, profile["preferences"], config,
      global_settings=global_settings,
  )
  ```

---

## Task 4: Tests

### Unit tests — `tests/test_rule_filter.py`

- [x] **Step 4.1: `check_applicant_count`**
  - Passes when count ≤ threshold
  - Rejects when count > threshold → reason `applications_count_exceeded`
  - Passes when `applications_count = None` (fail open)
  - Passes when no `global_job_filters.applications_count_max` key (filter disabled)

- [x] **Step 4.2: migrated `check_freshness`**
  - Reads `global_job_filters.max_age_days` from `global_settings`
  - Falls back to hard-coded `30` when `global_settings = None`
  - Does **not** read `prefs.get("max_age_days")` — assert candidate profile with `max_age_days: 999` does not bypass the admin limit
  - Passes when `published_at = None` (fail open)

- [x] **Step 4.3: `apply_rule_filters` with `global_settings`**
  - `global_settings=None` → `applications_count_exceeded` never appears in reject reasons
  - High-count job correctly rejected when setting configured
  - Both global and candidate-specific reasons can appear in the same reject entry

### Unit tests — `tests/test_fitcv_cp/test_settings_schema.py`

- [x] **Step 4.4: schema registration**
  - `global_job_filters.applications_count_max` and `global_job_filters.max_age_days` appear in `SETTINGS_SCHEMA`
  - Group is `"global_job_filters"` for both
  - `apply_settings_to_config` writes to `config["global_job_filters"]["applications_count_max"]` and `config["global_job_filters"]["max_age_days"]`
  - `validate_settings` accepts values `>= 1` and rejects `0` / negative

### Integration path test — `tests/test_pipeline.py` (or `test_rule_filter.py`)

- [x] **Step 4.5: end-to-end settings→config→filter path**

  Simulate the chain `apply_settings_to_config → apply_rule_filters` to prove the admin setting reaches the filter:

  ```python
  def test_admin_setting_applications_count_max_reaches_filter():
      from fitcv_cp.settings_schema import apply_settings_to_config
      from fitcv.rule_filter import apply_rule_filters

      config = {}
      apply_settings_to_config(config, {
          "global_job_filters.applications_count_max": 50,
      })
      raw_global = config.get("global_job_filters", {})
      global_settings = {f"global_job_filters.{k}": v for k, v in raw_global.items()}

      jobs = [
          {"job_url": "http://a", "applications_count": 10},   # pass
          {"job_url": "http://b", "applications_count": 200},  # reject
      ]
      result = apply_rule_filters(jobs, prefs={}, global_settings=global_settings)

      assert "http://a" in result["passed"]
      rejected_urls = {r["job_url"] for r in result["rejected"]}
      assert "http://b" in rejected_urls
      reasons = next(r["reasons"] for r in result["rejected"] if r["job_url"] == "http://b")
      assert "applications_count_exceeded" in reasons
  ```

---

## Task 5: Verify

- [x] **Step 5.1: Run rule filter tests**

  ```bash
  /tmp/fitcv-test-env/bin/pytest tests/test_rule_filter.py -q --tb=short -m "not integration"
  ```

- [x] **Step 5.2: Run settings schema tests**

  ```bash
  /tmp/fitcv-test-env/bin/pytest tests/test_fitcv_cp/test_settings_schema.py -q --tb=short
  ```

- [x] **Step 5.3: Run full regression suite**

  ```bash
  /tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
  ```

- [x] **Step 5.4: Manual verification**

  1. Open admin settings page → confirm `Global Job Filters` group with 2 controls
  2. Set `Maximum Applicant Count = 10`, trigger an upload run with jobs that have `applications_count > 10`
  3. Open run detail → Tab 1 (Enriched Jobs) → verify `applications_count_exceeded` reject reason appears

- [x] **Step 5.5: Commit**

  ```bash
  git add src/fitcv/rule_filter.py src/fitcv_cp/settings_schema.py src/fitcv/pipeline.py \
         tests/test_rule_filter.py tests/test_fitcv_cp/test_settings_schema.py tests/test_pipeline.py
  git commit -m "feat: add global job filters (applicant count + freshness migration)"
  ```

---

## Important Notes

- `min_description_length` is intentionally **out of scope**. Do not implement it.
- The `prefs.max_age_days` lookup in `check_freshness` is **removed entirely**. Existing candidate profiles with `max_age_days` will have no effect on freshness filtering after this change.
- **Template fix required (discovered during implementation):** `settings.html` hardcodes the groups list. Adding a new group to `SETTINGS_SCHEMA` alone is not sufficient — the group name must also be added to the `{% set groups = [...] %}` list in the template. `global_job_filters` was added in commit `b50a2f9`.
- No BigQuery schema changes required — reject reasons extend the existing `reasons` string array.
- 390 tests pass (+16 new). 2 pre-existing `test_enrich` failures are unrelated.
