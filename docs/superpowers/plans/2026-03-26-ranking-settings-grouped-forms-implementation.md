# Ranking Settings Grouped Forms — Implementation Plan

> **Status: COMPLETE** — Committed on `feat/admin-control-plane` as `3572e5e`
> feat: ranking settings grouped forms (weights, fit-label, gap thresholds)
> 404 tests pass (+14 new). 2 pre-existing test_enrich failures unrelated.

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans.

**Goal:** Replace per-row save for ranking settings with grouped editing forms. Three constraint-aligned groups: Ranking Weights, Fit Label Thresholds, Gap Thresholds.

**Spec:** `docs/superpowers/specs/2026-03-26-ranking-settings-grouped-forms-design.md`

**Resolved decisions:**
- Backend route: `POST /admin/settings/group/{group_name}` (generic grouped endpoint)
- Group slugs: `ranking-weights`, `fit-label-thresholds`, `gap-thresholds`
- Group registry lives in `settings_schema.py` as `RANKING_GROUPS` dict
- **Audit identity:** each group save generates a `uuid4()` encoded in `updated_by` as `"admin:grp:{uuid}"`. All rows from one save share the same UUID and `updated_at` timestamp. No BQ schema change required.
- **Atomicity guarantee (honest):** BQ streaming inserts do not provide true all-or-nothing semantics. The plan guarantees: (1) validation failures never write any rows; (2) BQ insert errors are raised and surfaced as visible error messages, not silently swallowed. Partial writes on BQ-level failures are theoretically possible but not expected in normal operation. This is accepted for an admin tool.
- Non-ranking groups (retrieval, timing, global_job_filters) continue with the existing per-row pattern
- `validate_settings` is already multi-key aware — reuse unchanged

---

## File Map

- **Modify:** `src/fitcv_cp/settings_schema.py`
- **Modify:** `src/fitcv_cp/settings_store.py`
- **Modify:** `src/fitcv_cp/app.py`
- **Modify:** `src/fitcv_cp/templates/settings.html`
- **Modify:** `tests/test_fitcv_cp/test_app.py`
- **Modify:** `tests/test_fitcv_cp/test_settings_schema.py`

---

## Task 1: Add group registry to `settings_schema.py`

**File:** `src/fitcv_cp/settings_schema.py`

- [x] **Step 1.1: Define `RANKING_GROUPS`**

  Add after the `SETTINGS_SCHEMA` list:

  ```python
  # ── Ranking group registry ────────────────────────────────────────────────────
  # Maps URL group slug → ordered list of schema keys.
  # Used by the grouped-edit endpoint and the settings template.

  RANKING_GROUPS: dict[str, list[str]] = {
      "ranking-weights": [
          "ranking_weights.ai_score",
          "ranking_weights.must_have_match",
          "ranking_weights.vector_similarity",
          "ranking_weights.title_relevance",
          "ranking_weights.seniority_fit",
          "ranking_weights.preference_fit",
      ],
      "fit-label-thresholds": [
          "fit_label_thresholds.strong",
          "fit_label_thresholds.stretch",
      ],
      "gap-thresholds": [
          "gap_thresholds.strong_min_matched_ratio",
          "gap_thresholds.stretch_min_matched_ratio",
      ],
  }
  ```

---

## Task 2: Extend `settings_store.py` with `save_settings_group`

**File:** `src/fitcv_cp/settings_store.py`

- [x] **Step 2.1: Implement `save_settings_group`**

  ```python
  def save_settings_group(
      keys_values: dict[str, Any],
      *,
      updated_by: str,
      bq: Any,
      project: str,
      dataset: str,
  ) -> None:
      """Write all keys in the group with a shared timestamp and updated_by identifier.

      Raises RuntimeError if BigQuery rejects the batch, so callers can surface the
      failure to the user rather than silently reporting success.

      WARNING: BigQuery streaming inserts do not guarantee all-or-nothing writes.
      Validation must always be completed before calling this function. BQ-level
      errors during the insert are raised.
      """
      table = f"{project}.{dataset}.pipeline_settings"
      now = datetime.datetime.now(datetime.timezone.utc).isoformat()
      rows = [
          {
              "setting_key": key,
              "setting_value_json": json.dumps(value),
              "updated_by": updated_by,
              "updated_at": now,
          }
          for key, value in keys_values.items()
      ]
      errors = bq.insert_rows_json(table, rows)
      if errors:
          logger.error("BQ save_settings_group errors: %s", errors)
          raise RuntimeError(f"Failed to save settings group: {errors}")
  ```

---

## Task 3: Add grouped endpoint to `app.py`

**File:** `src/fitcv_cp/app.py`

- [x] **Step 3.1: Import `RANKING_GROUPS`, `save_settings_group`, and `uuid4`**

  ```python
  from uuid import uuid4
  from fitcv_cp.settings_schema import RANKING_GROUPS, ...
  from fitcv_cp.settings_store import ..., save_settings_group
  ```

- [x] **Step 3.2: Add `POST /admin/settings/group/{group_name}` route**

  Place immediately **after** `admin_settings_update_key`. No route collision exists: `/admin/settings/group/{group_name}` and `/admin/settings/{key}` differ in path depth, so FastAPI resolves them unambiguously.

  ```python
  @app.post("/admin/settings/group/{group_name}", response_class=HTMLResponse)
  async def admin_settings_update_group(
      request: Request, group_name: str
  ) -> HTMLResponse:
      from fastapi.responses import RedirectResponse

      if group_name not in RANKING_GROUPS:
          raise HTTPException(status_code=404, detail=f"Unknown group: {group_name!r}")

      keys = RANKING_GROUPS[group_name]
      form = await request.form()

      # Coerce all keys in the group
      coerced: dict[str, Any] = {}
      coerce_errors: list[str] = []
      for key in keys:
          raw = form.get(key, "")
          try:
              coerced[key] = coerce_value(key, raw)
          except (KeyError, ValueError) as exc:
              coerce_errors.append(str(exc))

      def _error_response(msg: str) -> HTMLResponse:
          active = load_active_settings(bq=bq, project=project, dataset=dataset)
          return templates.TemplateResponse(
              request=request,
              name="settings.html",
              context={
                  "schema": SETTINGS_SCHEMA,
                  "active": active,
                  "ranking_weight_keys": RANKING_GROUPS["ranking-weights"],
                  "group_error": {group_name: msg},
                  "group_draft": {group_name: dict(form)},  # preserve edited values
              },
              status_code=422,
          )

      if coerce_errors:
          return _error_response("; ".join(coerce_errors))

      # Validate the full group as one coherent payload — no write occurs on failure
      try:
          validate_settings(coerced)
      except ValidationError as exc:
          return _error_response(str(exc))

      # Generate shared audit identity for this grouped save
      update_id = str(uuid4())
      updated_by = f"admin:grp:{update_id}"

      # Write — surface BQ failures to the user
      try:
          save_settings_group(
              coerced, updated_by=updated_by, bq=bq, project=project, dataset=dataset
          )
      except RuntimeError as exc:
          return _error_response(f"Save failed: {exc}")

      return RedirectResponse("/admin/settings", status_code=303)
  ```

- [x] **Step 3.3: Include `ranking_weight_keys` in `admin_settings_view` context**

  ```python
  context={
      "schema": SETTINGS_SCHEMA,
      "active": active,
      "ranking_weight_keys": RANKING_GROUPS["ranking-weights"],
  }
  ```

---

## Task 4: Update `settings.html` template

The `ranking` group is removed from the generic loop and replaced with three bespoke subgroup forms. All other groups remain unchanged.

- [x] **Step 4.1: Remove `"ranking"` from the generic groups loop**

  ```jinja
  {% set groups = ["retrieval", "timing", "global_job_filters"] %}
  ```

- [x] **Step 4.2: After the generic groups loop, add the ranked section with three subgroup forms**

  Each subgroup form follows the same structure:
  - Subgroup heading
  - Constraint hint text
  - Table of inputs pre-filled with `group_draft` → `active` → `default` (priority order)
  - Group-level error area
  - One Save button per subgroup
  - Form `action="/admin/settings/group/{slug}"`

- [x] **Step 4.3: Add live running total for the Ranking Weights group**

  ```html
  <p>Current total: <span id="weights-total">...</span> (must equal 1.0)</p>
  <script>
  function updateWeightsTotal() {
    const keys = {{ ranking_weight_keys | tojson }};
    let total = 0;
    keys.forEach(k => {
      const el = document.querySelector(`[name="${k}"]`);
      if (el) total += parseFloat(el.value) || 0;
    });
    const span = document.getElementById('weights-total');
    span.textContent = total.toFixed(3);
    span.style.color = Math.abs(total - 1.0) < 0.01 ? '#4ade80' : '#f87171';
  }
  document.addEventListener('DOMContentLoaded', updateWeightsTotal);
  </script>
  ```

  `ranking_weight_keys` is injected from the Python context — not hardcoded in HTML.

- [x] **Step 4.4: Render group-level error messages**

  ```jinja
  {% if group_error and 'ranking-weights' in group_error %}
  <p class="text-red-400 text-sm mt-2">{{ group_error['ranking-weights'] }}</p>
  {% endif %}
  ```

  Apply the same pattern to `fit-label-thresholds` and `gap-thresholds`.

---

## Task 5: Tests

**Files:** `tests/test_fitcv_cp/test_app.py`, `tests/test_fitcv_cp/test_settings_schema.py`

- [x] **Step 5.1: Schema registry tests** (`test_settings_schema.py`)

  - `RANKING_GROUPS` contains all three expected slugs
  - Every key in `RANKING_GROUPS` exists in `SETTINGS_SCHEMA`

- [x] **Step 5.2: Group endpoint — valid ranking weights → 303**

  POST with 6 weights summing to 1.0 → redirect; `save_settings_group` called with all 6 keys.

- [x] **Step 5.3: Group endpoint — weights don't sum to 1.0 → 422, no write**

  BQ mock must NOT be called. Response is 422 with error message visible in body.

- [x] **Step 5.4: Group endpoint — fit-label-thresholds invalid order → 422, no write**

  `strong=0.4, stretch=0.7` → 422. BQ mock not called.

- [x] **Step 5.5: Group endpoint — form values preserved on error**

  Response body contains the submitted values so the admin can correct without re-entering.

- [x] **Step 5.6: Group endpoint — BQ error raised → 422, not 303**

  Simulate `insert_rows_json` returning errors → `save_settings_group` raises → endpoint returns 422 with error message, not a redirect. This verifies finding 1's fix.

- [x] **Step 5.7: Group endpoint — unknown group name → 404**

  POST to `/admin/settings/group/nonexistent` → 404.

- [x] **Step 5.8: `save_settings_group` — shared `updated_at` and `updated_by`**

  All rows passed to `insert_rows_json` share identical `updated_at` and `updated_by` (containing the group UUID).

- [x] **Step 5.9: `save_settings_group` — raises on BQ error**

  If `insert_rows_json` returns a non-empty errors list → `RuntimeError` is raised (not silently logged).

---

## Task 6: Verify

- [x] **Step 6.1: Run full test suite**

  ```bash
  /tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
  ```

- [x] **Step 6.2: Manual verification**

  1. Settings page shows `ranking` as 3 grouped forms, not per-row rows
  2. Save valid weights → 303 redirect with updated current values
  3. Save weights summing to 0.9 → inline error, form retains edited values
  4. Save fit-label thresholds stretch > strong → inline error
  5. Retrieval, timing, global_job_filters still save per-row as before

- [x] **Step 6.3: Commit**

  ```bash
  git add src/fitcv_cp/settings_schema.py src/fitcv_cp/settings_store.py \
         src/fitcv_cp/app.py src/fitcv_cp/templates/settings.html \
         tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_settings_schema.py
  git commit -m "feat: ranking settings grouped forms (weights, fit-label, gap thresholds)"
  ```

---

## Important Notes

- **BQ error surfacing (finding 1 fix):** `save_settings_group` raises `RuntimeError` on BQ failure. The endpoint catches it and returns a 422 with the error message. No silent success.
- **Atomicity (honest):** BQ streaming inserts are not transactional. The guarantee is: validation failures never write anything; BQ errors are surfaced. Partial writes on BQ-level failures are possible but rare and accepted for an admin tool.
- **Audit identity (finding 4 fix):** Each group save generates `uuid4()` encoded as `"admin:grp:{uuid}"` in `updated_by`. All rows in the group share this UUID and `updated_at`, providing a common logical change identifier without a schema migration.
- **Route ordering (finding 3 fix):** No collision. `/admin/settings/group/{group_name}` (3 path segments) and `/admin/settings/{key}` (2 path segments) are distinct. Place the grouped route after `admin_settings_update_key` — no special ordering constraint needed.
- `validate_settings` is reused unchanged — it already handles all multi-key constraints.
