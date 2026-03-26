# Cheap-First Pipeline Narrowing — Implementation Plan

> **Status: COMPLETE** — Committed on `feat/admin-control-plane` as `1df3b74`
> feat: pre-enrichment global filters (cheap-first pipeline narrowing)
> 412 tests pass (+8 new). 2 pre-existing test_enrich failures unrelated.

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Move global job filters to pre-enrichment, fix the run-detail display so pre-enrichment rejects appear, and remove the now-redundant post-enrichment freshness check from `apply_rule_filters`.

**Spec:** `docs/superpowers/specs/2026-03-26-cheap-first-pipeline-narrowing-design.md`

**Status at plan time:**
Filter logic, settings, and admin UI already exist. Two gaps remain:
1. Global filters still run post-enrichment (wasting `enrich_batch` budget on rejected jobs)
2. Post-enrichment `apply_rule_filters` still applies freshness with a 30-day hard default (duplicate, admin-uncontrolled filtering after the pre-enrichment check)

**Resolved decisions:**
- `job_too_stale` and `applications_count_exceeded` are **removed from `apply_rule_filters`** — they now live exclusively in `apply_pre_enrichment_global_filters`; the `global_settings` param in `apply_rule_filters` becomes unused and is retained only for backward compatibility with direct callers
- Pre-enrichment rejects are surfaced in run detail via a separate template section (not via the enriched jobs table, which only includes post-enrichment jobs)
- `max_age_days` migration from candidate-profile ownership is **already complete** at the data/code level (`profile.py` and `candidate_profile.yaml` have no reference); the plan adds a confirming test
- `applications_count_int` (parsed integer from `normalize.py`) is preferred in `check_applicant_count` over the raw `applications_count` string field

---

## File Map

- **Modify:** `src/fitcv/rule_filter.py`
- **Modify:** `src/fitcv/pipeline.py`
- **Modify:** `src/fitcv_cp/app.py`
- **Modify:** `src/fitcv_cp/templates/run_detail.html`
- **Modify:** `tests/test_rule_filter.py`
- **Modify:** `tests/test_pipeline.py` (or add new tests)

---

## Task 1: Update `check_applicant_count` for pre-enrichment field naming

**File:** `src/fitcv/rule_filter.py`

- [x] **Step 1.1: Prefer `applications_count_int` over `applications_count`**

  ```python
  def check_applicant_count(
      job: dict[str, Any], global_settings: dict[str, Any]
  ) -> bool:
      max_count = global_settings.get("global_job_filters.applications_count_max")
      if max_count is None:
          return True
      # Prefer parsed integer from normalize.py; fall back to raw field
      count = job.get("applications_count_int", job.get("applications_count"))
      if count is None:
          return True  # fail open
      try:
          return int(count) <= int(max_count)
      except (ValueError, TypeError):
          return True  # unparseable — fail open
  ```

---

## Task 2: Remove global checks from `apply_rule_filters`

**File:** `src/fitcv/rule_filter.py`

- [x] **Step 2.1: Remove `job_too_stale` from the main checks list**

  Delete this line from the `checks` list:
  ```python
  ("job_too_stale", lambda j, p: check_freshness(j, global_settings)),
  ```

- [x] **Step 2.2: Remove the conditional `applications_count_exceeded` check**

  Delete this block:
  ```python
  if global_settings:
      checks.append(
          ("applications_count_exceeded",
           lambda j, p: check_applicant_count(j, global_settings)),
      )
  ```

- [x] **Step 2.3: Update `apply_rule_filters` docstring**

  Note that `global_settings` is retained for compatibility but global filter checks now belong exclusively in `apply_pre_enrichment_global_filters`. The parameter is no longer exercised by the pipeline.

---

## Task 3: Add `apply_pre_enrichment_global_filters` to `rule_filter.py`

**File:** `src/fitcv/rule_filter.py`

- [x] **Step 3.1: Implement the new function**

  ```python
  def apply_pre_enrichment_global_filters(
      jobs: list[dict[str, Any]],
      global_settings: dict[str, Any] | None,
  ) -> dict[str, list]:
      """Apply admin-managed pre-enrichment global filters.

      Uses only fields available after ingest + normalization
      (applications_count_int, published_at). Runs before enrich_batch so
      rejected jobs do not consume LLM/API budget.

      Returns: {"passed": [job_url, ...], "rejected": [{"job_url": ..., "reasons": [...]}, ...]}

      When global_settings is None or empty, all jobs pass (filters disabled).
      """
      if not global_settings:
          return {
              "passed": [str(j.get("job_url", "")) for j in jobs],
              "rejected": [],
          }

      checks: list[tuple[str, Callable[[dict], bool]]] = [
          ("job_too_stale",                lambda j: check_freshness(j, global_settings)),
          ("applications_count_exceeded",  lambda j: check_applicant_count(j, global_settings)),
      ]

      passed: list[str] = []
      rejected: list[dict[str, Any]] = []
      for job in jobs:
          url = str(job.get("job_url", ""))
          failed = [reason for reason, fn in checks if not fn(job)]
          if failed:
              rejected.append({"job_url": url, "reasons": failed})
          else:
              passed.append(url)

      return {"passed": passed, "rejected": rejected}
  ```

---

## Task 4: Reorder `pipeline.py` — filter before enrichment

**File:** `src/fitcv/pipeline.py`

- [x] **Step 4.1: Import `apply_pre_enrichment_global_filters`**

- [x] **Step 4.2: Move filter execution before `enrich_batch`**

  New Layer 1 order:
  ```python
  # ── Layer 1: ingest + normalize ───────────────────────────────────────────
  raw_jobs = parse_jobs_file(jobs_path)
  normalized = normalize_batch(raw_jobs)
  load_to_bigquery(prepare_raw_rows(raw_jobs), config)

  # ── Layer 1b: pre-enrichment global filters ───────────────────────────────
  raw_global = config.get("global_job_filters", {})
  global_settings = (
      {f"global_job_filters.{k}": v for k, v in raw_global.items()}
      if raw_global else None
  )
  pre_filter = apply_pre_enrichment_global_filters(normalized, global_settings)
  pre_filter_passed_urls: set[str] = set(pre_filter["passed"])
  surviving_normalized = [
      j for j in normalized if str(j.get("job_url", "")) in pre_filter_passed_urls
  ]

  # ── Layer 1c: enrich survivors only ──────────────────────────────────────
  enriched = enrich_batch(surviving_normalized, config)
  load_structured_jobs(enriched, config)
  load_run_structured_jobs(enriched, run_id, config)
  ```

- [x] **Step 4.3: Call `apply_rule_filters` without `global_settings`**

  ```python
  filter_result = apply_rule_filters(enriched, profile["preferences"], config)
  ```

- [x] **Step 4.4: Merge pre-enrichment and candidate-filter rejects before `store_filter_results`**

  ```python
  combined_filter_result = {
      "passed": filter_result["passed"],
      "rejected": pre_filter["rejected"] + filter_result["rejected"],
  }
  store_filter_results(combined_filter_result, run_id, config)
  ```

---

## Task 5: Surface pre-enrichment rejects in run-detail UI

Pre-enrichment rejects have no enriched job row. The current template iterates `enriched_jobs` and cannot show them. Fix: derive and pass them explicitly, then render a separate section.

### `src/fitcv_cp/app.py`

- [x] **Step 5.1: Derive `pre_enrichment_rejects` in the run-detail route**

  After fetching `enriched_jobs` and `filter_results`:
  ```python
  enriched_job_urls = {j["job_url"] for j in enriched_jobs}
  pre_enrichment_rejects = [
      row for row in filter_results
      if row["job_url"] not in enriched_job_urls and row.get("reasons")
  ]
  ```

  Pass to template context:
  ```python
  context={
      ...
      "pre_enrichment_rejects": pre_enrichment_rejects,
  }
  ```

### `src/fitcv_cp/templates/run_detail.html`

- [x] **Step 5.2: Add a "Rejected before enrichment" section**

  Below the enriched jobs table, add:
  ```html
  {% if pre_enrichment_rejects %}
  <section class="mt-6">
    <h3 class="text-sm font-semibold text-gray-400 mb-2">
      Rejected before enrichment ({{ pre_enrichment_rejects | length }})
    </h3>
    <table class="w-full text-xs text-gray-400">
      <thead>
        <tr>
          <th class="text-left py-1 pr-4">Job URL</th>
          <th class="text-left py-1">Reject Reasons</th>
        </tr>
      </thead>
      <tbody>
        {% for row in pre_enrichment_rejects %}
        <tr class="border-t border-gray-800">
          <td class="py-2 pr-4">
            <a href="{{ row.job_url }}" class="text-indigo-400 hover:underline" target="_blank">
              {{ row.job_url }}
            </a>
          </td>
          <td class="py-2 text-red-400">{{ row.reasons | join(', ') }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </section>
  {% endif %}
  ```

---

## Task 6: Tests

### `tests/test_rule_filter.py`

- [x] **Step 6.1: `apply_pre_enrichment_global_filters` — `global_settings=None` passes all**

- [x] **Step 6.2: `apply_pre_enrichment_global_filters` — rejects stale job using `published_at`**

- [x] **Step 6.3: `apply_pre_enrichment_global_filters` — rejects high-count job using `applications_count_int`**

- [x] **Step 6.4: `apply_pre_enrichment_global_filters` — `applications_count_int=None` → fail open**

- [x] **Step 6.5: `check_applicant_count` — prefers `applications_count_int`, ignores raw `applications_count`**

- [x] **Step 6.6: `apply_rule_filters` — no longer rejects stale jobs when `global_settings=None`**

  A stale job (old `published_at`) with `prefs={}` and `global_settings=None` must **pass** `apply_rule_filters`. This confirms freshness is no longer the pipeline's post-enrichment responsibility.

- [x] **Step 6.7: `apply_rule_filters` — `prefs.max_age_days` has no effect on freshness**

  A stale job with `prefs={"max_age_days": 1}` must still pass `apply_rule_filters` (confirming candidate-profile ownership migration is complete).

### `tests/test_pipeline.py`

- [x] **Step 6.8: `enrich_batch` called only with surviving jobs**

  Mock `apply_pre_enrichment_global_filters` to reject one URL. Assert `enrich_batch` receives only the surviving normalized jobs.

- [x] **Step 6.9: Pre-enrichment rejects appear in `store_filter_results` payload**

---

## Task 7: Verify

- [x] **Step 7.1: Run full test suite**

  ```bash
  /tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
  ```

- [x] **Step 7.2: Update existing tests that assumed `apply_rule_filters` handles global checks**

  Any tests calling `apply_rule_filters` with `global_settings` expecting `applications_count_exceeded` or `job_too_stale` in the result must be moved to target `apply_pre_enrichment_global_filters`.

- [x] **Step 7.3: Commit**

  ```bash
  git add src/fitcv/rule_filter.py src/fitcv/pipeline.py \
         src/fitcv_cp/app.py src/fitcv_cp/templates/run_detail.html \
         tests/test_rule_filter.py tests/test_pipeline.py
  git commit -m "feat: pre-enrichment global filters (cheap-first pipeline narrowing)"
  ```

---

## Important Notes

- **Finding 1 (fixed):** `job_too_stale` and `applications_count_exceeded` are removed from `apply_rule_filters`. Post-enrichment freshness with a 30-day default no longer silently runs. All global filter checks live exclusively in `apply_pre_enrichment_global_filters`.
- **Finding 2 (fixed):** Pre-enrichment rejects get their own template section in `run_detail.html` rather than being conflated with the enriched-jobs table. The `app.py` route derives them by excluding URLs present in `enriched_jobs`.
- **Finding 3 (fixed):** `max_age_days` migration is already complete at the data/code level. Tests 6.6 and 6.7 confirm `apply_rule_filters` no longer respects freshness in any form.
- **Backward compat:** `apply_rule_filters` retains the `global_settings` parameter (default `None`) to avoid breaking direct callers. The pipeline stops passing it; existing tests that pass it directly still pass (they just won't trigger the now-removed checks).
- **Post-enrichment global filters and cheap pre-LLM pruning:** intentionally deferred per spec.
