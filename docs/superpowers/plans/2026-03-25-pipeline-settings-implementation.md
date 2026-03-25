# Pipeline Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a settings page to the FitCV Admin Control Plane that lets an admin view and edit pipeline tuning defaults stored in BigQuery, with changes applied as immutable snapshots on each pipeline run.

**Architecture:** A new `pipeline_settings` BigQuery table stores editable key-value settings. A `settings_schema.py` registry defines allowed keys, types, defaults, and validation rules. At run trigger time, the control plane merges YAML baseline + BQ settings + per-run overrides from `POST /runs`, validates the result, stores it as `effective_settings_json` on `pipeline_runs`, then enqueues only the `run_id`. The worker reads the snapshot — never re-reads BQ settings. `run_pipeline()` gains a `config: dict | None` kwarg to accept a pre-built config.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, `google-cloud-bigquery` (parameterized queries), existing `fitcv_cp` package patterns.

**Key invariant:** `load_active_settings()` is called only at trigger time on the web side. The worker uses the stored snapshot exclusively.

**Spec:** `docs/superpowers/specs/2026-03-25-pipeline-settings-design.md`

---

## Task 1 — Settings Schema Registry

**Files:**
- Create: `src/fitcv_cp/settings_schema.py`
- Create: `tests/fitcv_cp/test_settings_schema.py`

- [ ] **Step 1.1: Write failing tests**

```python
# tests/fitcv_cp/test_settings_schema.py
import pytest
from fitcv_cp.settings_schema import (
    SETTINGS_SCHEMA,
    apply_settings_to_config,
    validate_settings,
    ValidationError,
)


# ── schema registry ───────────────────────────────────────────────────────────

def test_all_expected_keys_present():
    keys = {s["key"] for s in SETTINGS_SCHEMA}
    assert "pipeline.final_top_n" in keys
    assert "ranking_weights.ai_score" in keys
    assert "fit_label_thresholds.strong" in keys
    assert "gap_thresholds.strong_min_matched_ratio" in keys
    # excluded key — internal fallback only, not admin-editable
    assert "rerank_top_n" not in keys


def test_schema_has_required_fields():
    for entry in SETTINGS_SCHEMA:
        assert "key" in entry
        assert "type" in entry       # "int" or "float"
        assert "default" in entry
        assert "label" in entry
        assert "group" in entry      # "retrieval" | "timing" | "ranking"


# ── type coercion ─────────────────────────────────────────────────────────────

def test_coerce_int_from_string():
    from fitcv_cp.settings_schema import coerce_value
    assert coerce_value("pipeline.final_top_n", "5") == 5
    assert isinstance(coerce_value("pipeline.final_top_n", "5"), int)


def test_coerce_float_from_string():
    from fitcv_cp.settings_schema import coerce_value
    assert coerce_value("ranking_weights.ai_score", "0.5") == 0.5


def test_coerce_rejects_unknown_key():
    from fitcv_cp.settings_schema import coerce_value
    with pytest.raises(KeyError):
        coerce_value("unknown.key", "1")


# ── per-field validation ──────────────────────────────────────────────────────

def test_int_top_n_must_be_positive():
    with pytest.raises(ValidationError, match="pipeline.final_top_n"):
        validate_settings({"pipeline.final_top_n": 0})


def test_float_threshold_must_be_in_range():
    with pytest.raises(ValidationError, match="fit_label_thresholds.strong"):
        validate_settings({"fit_label_thresholds.strong": 1.5})


def test_sleep_secs_may_be_zero():
    validate_settings({"enrichment_sleep_secs": 0.0})  # should not raise


# ── relational validation ─────────────────────────────────────────────────────

def test_top_n_relational_constraint():
    """final_top_n <= ai_score_top_n <= vector_search_top_n"""
    with pytest.raises(ValidationError, match="final_top_n"):
        validate_settings({
            "pipeline.vector_search_top_n": 50,
            "pipeline.ai_score_top_n": 50,
            "pipeline.final_top_n": 60,   # violates: 60 > 50
        })


def test_fit_label_strong_must_exceed_stretch():
    with pytest.raises(ValidationError, match="fit_label_thresholds"):
        validate_settings({
            "fit_label_thresholds.strong": 0.40,
            "fit_label_thresholds.stretch": 0.70,   # violates: stretch > strong
        })


def test_ranking_weights_must_sum_to_one():
    with pytest.raises(ValidationError, match="ranking_weights"):
        validate_settings({
            "ranking_weights.ai_score": 0.90,
            "ranking_weights.must_have_match": 0.20,
            "ranking_weights.vector_similarity": 0.15,
            "ranking_weights.title_relevance": 0.10,
            "ranking_weights.seniority_fit": 0.10,
            "ranking_weights.preference_fit": 0.05,
        })


def test_ranking_weights_partial_update_skips_sum_check():
    """Partial updates are allowed; sum-to-1 only checked when ALL 6 are present."""
    validate_settings({"ranking_weights.ai_score": 0.50})  # should not raise


def test_gap_thresholds_strong_must_exceed_stretch():
    with pytest.raises(ValidationError, match="gap_thresholds"):
        validate_settings({
            "gap_thresholds.strong_min_matched_ratio": 0.30,
            "gap_thresholds.stretch_min_matched_ratio": 0.50,
        })


def test_unknown_key_rejected():
    with pytest.raises(ValidationError, match="unknown"):
        validate_settings({"unknown.key": 1})


# ── config application ────────────────────────────────────────────────────────

def test_apply_settings_to_config_nested():
    config = {"pipeline": {"final_top_n": 10}, "ranking_weights": {"ai_score": 0.40}}
    apply_settings_to_config(config, {"pipeline.final_top_n": 5, "ranking_weights.ai_score": 0.50})
    assert config["pipeline"]["final_top_n"] == 5
    assert config["ranking_weights"]["ai_score"] == 0.50


def test_apply_settings_to_config_flat_key():
    config = {"enrichment_sleep_secs": 1.0}
    apply_settings_to_config(config, {"enrichment_sleep_secs": 0.5})
    assert config["enrichment_sleep_secs"] == 0.5
```

- [ ] **Step 1.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_settings_schema.py -v
# Expected: ImportError — settings_schema not found
```

- [ ] **Step 1.3: Implement `settings_schema.py`**

```python
# src/fitcv_cp/settings_schema.py
"""Registry of admin-editable pipeline settings.

Each entry defines:
  key         Dotted name used in pipeline_settings BQ table and POST /runs overrides
  type        "int" or "float"
  default     YAML baseline default (for display purposes; source of truth is config/*.yaml)
  label       Human-readable display name shown in the admin UI
  group       UI section: "retrieval" | "timing" | "ranking"
  config_path List of keys to traverse when applying to a config dict
              e.g. ["pipeline", "final_top_n"] → config["pipeline"]["final_top_n"]

Validation rules are enforced by validate_settings().
"""
from __future__ import annotations

from typing import Any


class ValidationError(ValueError):
    pass


# ── schema registry ──────────────────────────────────────────────────────────

SETTINGS_SCHEMA: list[dict[str, Any]] = [
    # ── Retrieval ─────────────────────────────────────────────────────────────
    {
        "key": "pipeline.vector_search_top_n",
        "type": "int",
        "default": 50,
        "label": "Vector shortlist size",
        "group": "retrieval",
        "config_path": ["pipeline", "vector_search_top_n"],
    },
    {
        "key": "pipeline.ai_score_top_n",
        "type": "int",
        "default": 50,
        "label": "AI rerank size",
        "group": "retrieval",
        "config_path": ["pipeline", "ai_score_top_n"],
    },
    {
        "key": "pipeline.final_top_n",
        "type": "int",
        "default": 10,
        "label": "Final top-N results",
        "group": "retrieval",
        "config_path": ["pipeline", "final_top_n"],
    },
    {
        "key": "pipeline.evidence_top_k",
        "type": "int",
        "default": 5,
        "label": "Evidence chunks per job",
        "group": "retrieval",
        "config_path": ["pipeline", "evidence_top_k"],
    },
    # ── Timing / Throttling ───────────────────────────────────────────────────
    {
        "key": "enrichment_sleep_secs",
        "type": "float",
        "default": 1.0,
        "label": "Enrichment sleep (secs)",
        "group": "timing",
        "config_path": ["enrichment_sleep_secs"],
    },
    {
        "key": "rerank_sleep_secs",
        "type": "float",
        "default": 0.5,
        "label": "AI rerank sleep (secs)",
        "group": "timing",
        "config_path": ["rerank_sleep_secs"],
    },
    # ── Ranking Policy ────────────────────────────────────────────────────────
    {
        "key": "ranking_weights.ai_score",
        "type": "float",
        "default": 0.40,
        "label": "Weight: AI score",
        "group": "ranking",
        "config_path": ["ranking_weights", "ai_score"],
    },
    {
        "key": "ranking_weights.must_have_match",
        "type": "float",
        "default": 0.20,
        "label": "Weight: must-have match",
        "group": "ranking",
        "config_path": ["ranking_weights", "must_have_match"],
    },
    {
        "key": "ranking_weights.vector_similarity",
        "type": "float",
        "default": 0.15,
        "label": "Weight: vector similarity",
        "group": "ranking",
        "config_path": ["ranking_weights", "vector_similarity"],
    },
    {
        "key": "ranking_weights.title_relevance",
        "type": "float",
        "default": 0.10,
        "label": "Weight: title relevance",
        "group": "ranking",
        "config_path": ["ranking_weights", "title_relevance"],
    },
    {
        "key": "ranking_weights.seniority_fit",
        "type": "float",
        "default": 0.10,
        "label": "Weight: seniority fit",
        "group": "ranking",
        "config_path": ["ranking_weights", "seniority_fit"],
    },
    {
        "key": "ranking_weights.preference_fit",
        "type": "float",
        "default": 0.05,
        "label": "Weight: preference fit",
        "group": "ranking",
        "config_path": ["ranking_weights", "preference_fit"],
    },
    {
        "key": "fit_label_thresholds.strong",
        "type": "float",
        "default": 0.70,
        "label": "Fit threshold: strong (≥)",
        "group": "ranking",
        "config_path": ["fit_label_thresholds", "strong"],
    },
    {
        "key": "fit_label_thresholds.stretch",
        "type": "float",
        "default": 0.40,
        "label": "Fit threshold: stretch (≥)",
        "group": "ranking",
        "config_path": ["fit_label_thresholds", "stretch"],
    },
    {
        "key": "gap_thresholds.strong_min_matched_ratio",
        "type": "float",
        "default": 0.80,
        "label": "Skill gap threshold: strong (ratio ≥)",
        "group": "ranking",
        "config_path": ["gap_thresholds", "strong_min_matched_ratio"],
    },
    {
        "key": "gap_thresholds.stretch_min_matched_ratio",
        "type": "float",
        "default": 0.50,
        "label": "Skill gap threshold: stretch (ratio ≥)",
        "group": "ranking",
        "config_path": ["gap_thresholds", "stretch_min_matched_ratio"],
    },
]

# Build lookup maps once
_SCHEMA_BY_KEY: dict[str, dict[str, Any]] = {s["key"]: s for s in SETTINGS_SCHEMA}
_WEIGHT_KEYS: frozenset[str] = frozenset(
    s["key"] for s in SETTINGS_SCHEMA if s["key"].startswith("ranking_weights.")
)


# ── coercion ──────────────────────────────────────────────────────────────────

def coerce_value(key: str, raw: Any) -> int | float:
    """Cast raw value (string or numeric) to the type declared in the schema."""
    entry = _SCHEMA_BY_KEY[key]  # raises KeyError for unknown keys
    if entry["type"] == "int":
        return int(raw)
    return float(raw)


# ── validation ────────────────────────────────────────────────────────────────

def validate_settings(settings: dict[str, Any]) -> None:
    """Validate a (possibly partial) settings dict.

    Raises ValidationError with a descriptive message on any violation.
    settings values must already be coerced to their declared Python types.
    """
    for key, value in settings.items():
        if key not in _SCHEMA_BY_KEY:
            raise ValidationError(f"Unknown setting key: '{key}'")
        entry = _SCHEMA_BY_KEY[key]

        if entry["type"] == "int":
            if not isinstance(value, int) or value < 1:
                raise ValidationError(f"{key} must be an integer >= 1, got {value!r}")
        elif entry["type"] == "float":
            fval = float(value)
            if key.endswith("_secs"):
                if fval < 0.0:
                    raise ValidationError(f"{key} must be >= 0.0, got {fval}")
            else:
                if not (0.0 <= fval <= 1.0):
                    raise ValidationError(
                        f"{key} must be in range [0.0, 1.0], got {fval}"
                    )

    # ── relational constraints ────────────────────────────────────────────────
    vs = settings.get("pipeline.vector_search_top_n")
    ai = settings.get("pipeline.ai_score_top_n")
    fn = settings.get("pipeline.final_top_n")
    if all(v is not None for v in [vs, ai]) and ai > vs:
        raise ValidationError(
            f"pipeline.ai_score_top_n ({ai}) must be <= pipeline.vector_search_top_n ({vs})"
        )
    if all(v is not None for v in [ai, fn]) and fn > ai:
        raise ValidationError(
            f"pipeline.final_top_n ({fn}) must be <= pipeline.ai_score_top_n ({ai})"
        )

    strong = settings.get("fit_label_thresholds.strong")
    stretch = settings.get("fit_label_thresholds.stretch")
    if strong is not None and stretch is not None and strong <= stretch:
        raise ValidationError(
            f"fit_label_thresholds.strong ({strong}) must be > stretch ({stretch})"
        )

    g_strong = settings.get("gap_thresholds.strong_min_matched_ratio")
    g_stretch = settings.get("gap_thresholds.stretch_min_matched_ratio")
    if g_strong is not None and g_stretch is not None and g_strong <= g_stretch:
        raise ValidationError(
            f"gap_thresholds.strong_min_matched_ratio ({g_strong}) must be > stretch ({g_stretch})"
        )

    # Ranking weights sum-to-1 only checked when all 6 are present
    if _WEIGHT_KEYS <= set(settings.keys()):
        total = sum(float(settings[k]) for k in _WEIGHT_KEYS)
        if abs(total - 1.0) > 0.01:
            raise ValidationError(
                f"ranking_weights must sum to 1.0 (± 0.01), got {total:.4f}"
            )


# ── config application ────────────────────────────────────────────────────────

def apply_settings_to_config(config: dict[str, Any], settings: dict[str, Any]) -> None:
    """Write settings values into a config dict in-place.

    Uses config_path from the schema registry to navigate nested dicts.
    settings values must already be coerced to their declared Python types.
    """
    for key, value in settings.items():
        path = _SCHEMA_BY_KEY[key]["config_path"]
        target = config
        for part in path[:-1]:
            target = target.setdefault(part, {})
        target[path[-1]] = value
```

- [ ] **Step 1.4: Run tests**

```bash
pytest tests/fitcv_cp/test_settings_schema.py -v
# Expected: all pass
```

- [ ] **Step 1.5: Commit**

```bash
git add src/fitcv_cp/settings_schema.py tests/fitcv_cp/test_settings_schema.py
git commit -m "feat(cp/settings): add settings_schema with validation and config mapping"
```

---

## Task 2 — BigQuery Settings Store + DDL

**Files:**
- Create: `src/fitcv_cp/settings_store.py`
- Create: `assets/bigquery/pipeline_settings.sql`
- Create: `tests/fitcv_cp/test_settings_store.py`

- [ ] **Step 2.1: Write failing tests**

```python
# tests/fitcv_cp/test_settings_store.py
import datetime
from unittest.mock import MagicMock

from fitcv_cp.settings_store import (
    load_active_settings,
    save_setting,
)


def _make_bq_row(key: str, value_json: str, updated_at: str) -> dict:
    return {
        "setting_key": key,
        "setting_value_json": value_json,
        "updated_by": "admin",
        "updated_at": updated_at,
    }


def test_save_setting_calls_bq():
    bq = MagicMock()
    save_setting("pipeline.final_top_n", 5, updated_by="admin",
                 bq=bq, project="p", dataset="d")
    bq.insert_rows_json.assert_called_once()
    row = bq.insert_rows_json.call_args[0][1][0]
    assert row["setting_key"] == "pipeline.final_top_n"
    assert row["setting_value_json"] == "5"


def test_load_active_settings_returns_latest_per_key():
    bq = MagicMock()
    # Two rows for the same key — different timestamps. Latest should win.
    rows = [
        _make_bq_row("pipeline.final_top_n", "10", "2026-01-01T00:00:00"),
        _make_bq_row("pipeline.final_top_n", "5", "2026-01-02T00:00:00"),
    ]
    bq.query.return_value.result.return_value = iter(rows)
    result = load_active_settings(bq=bq, project="p", dataset="d")
    # The query uses ORDER BY updated_at DESC so first row per key is the latest
    assert result["pipeline.final_top_n"] == 5
    assert isinstance(result["pipeline.final_top_n"], int)  # coerced


def test_load_active_settings_empty_table():
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    result = load_active_settings(bq=bq, project="p", dataset="d")
    assert result == {}


def test_load_active_settings_uses_parameterized_query_or_safe_query():
    """Just verify query is called (no string injection risk since no user input)."""
    bq = MagicMock()
    bq.query.return_value.result.return_value = iter([])
    load_active_settings(bq=bq, project="p", dataset="d")
    bq.query.assert_called_once()
```

- [ ] **Step 2.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_settings_store.py -v
# Expected: ImportError
```

- [ ] **Step 2.3: Write `assets/bigquery/pipeline_settings.sql`**

```sql
CREATE TABLE IF NOT EXISTS `{project}.{dataset}.pipeline_settings` (
  setting_key        STRING    NOT NULL OPTIONS(description="Namespaced key, e.g. pipeline.final_top_n"),
  setting_value_json STRING    NOT NULL OPTIONS(description="JSON-encoded value, e.g. 10 or 0.40"),
  updated_by         STRING,
  updated_at         TIMESTAMP NOT NULL
);
```

- [ ] **Step 2.4: Implement `settings_store.py`**

```python
# src/fitcv_cp/settings_store.py
"""BigQuery persistence for pipeline_settings table.

All reads use a single query that returns the latest value per key (ORDER BY updated_at DESC).
No in-process caching — reads hit BQ each time. This is acceptable for an internal admin tool.
"""
import datetime
import json
import logging
from typing import Any

from fitcv_cp.settings_schema import coerce_value

logger = logging.getLogger(__name__)


def save_setting(
    key: str,
    value: Any,
    *,
    updated_by: str,
    bq: Any,
    project: str,
    dataset: str,
) -> None:
    """Append a new row for this key. Current value = latest row per key."""
    table = f"{project}.{dataset}.pipeline_settings"
    row = {
        "setting_key": key,
        "setting_value_json": json.dumps(value),
        "updated_by": updated_by,
        "updated_at": datetime.datetime.utcnow().isoformat(),
    }
    errors = bq.insert_rows_json(table, [row])
    if errors:
        logger.error("BQ save_setting errors: %s", errors)


def load_active_settings(*, bq: Any, project: str, dataset: str) -> dict[str, Any]:
    """Return the current active settings dict (latest row per key, coerced to Python types).

    Returns an empty dict if no settings have been saved yet.
    """
    sql = (
        f"SELECT setting_key, setting_value_json "
        f"FROM `{project}.{dataset}.pipeline_settings` "
        f"ORDER BY updated_at DESC"
    )
    rows = list(bq.query(sql).result())

    seen: set[str] = set()
    result: dict[str, Any] = {}
    for row in rows:
        key = str(row["setting_key"])
        if key in seen:
            continue  # older value for same key — skip
        seen.add(key)
        raw = json.loads(str(row["setting_value_json"]))
        try:
            result[key] = coerce_value(key, raw)
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping unknown/invalid setting key=%s: %s", key, exc)

    return result
```

- [ ] **Step 2.5: Run tests**

```bash
pytest tests/fitcv_cp/test_settings_store.py -v
# Expected: all pass
```

- [ ] **Step 2.6: Commit**

```bash
git add src/fitcv_cp/settings_store.py assets/bigquery/pipeline_settings.sql tests/fitcv_cp/test_settings_store.py
git commit -m "feat(cp/settings): add settings_store BQ helpers and pipeline_settings DDL"
```

---

## Task 3 — Modify `pipeline_runs` DDL + `run_pipeline()` config kwarg

**Files:**
- Modify: `assets/bigquery/pipeline_runs.sql` (add `effective_settings_json` column)
- Modify: `src/fitcv/pipeline.py` (add `config: dict | None = None` kwarg)
- Modify: `src/fitcv_cp/bq_store.py` (`insert_run()` and `_row_to_run()` handle new field)
- Modify: `src/fitcv_cp/models.py` (`PipelineRun` gains `effective_settings_json` optional field)

- [ ] **Step 3.1: Add `effective_settings_json` to `pipeline_runs.sql`**

In `assets/bigquery/pipeline_runs.sql`, add before the closing `);`:
```sql
  effective_settings_json STRING    OPTIONS(description="Merged config snapshot at trigger time")
```

- [ ] **Step 3.2: Add field to `PipelineRun` dataclass**

In `src/fitcv_cp/models.py`, add to `PipelineRun`:
```python
effective_settings_json: Optional[str] = None
```

- [ ] **Step 3.3: Write failing pipeline test**

```python
# In tests/test_pipeline.py (add to existing test file):
def test_run_pipeline_accepts_prebuilt_config(tmp_path, monkeypatch):
    """run_pipeline() should use the provided config dict instead of loading from disk."""
    # Arrange: no config file on disk
    config = {
        "gcp_project": "test", "bigquery_dataset": "test",
        "service_account_key": "fake",
        "pipeline": {"vector_search_top_n": 50, "ai_score_top_n": 50,
                     "final_top_n": 10, "evidence_top_k": 5},
    }
    # Monkeypatch all integration functions to no-ops
    # (This is the same pattern as existing pipeline tests)
    ...
    from fitcv.pipeline import run_pipeline
    # Should not raise FileNotFoundError even though no .env.yaml exists
    # (actual full test implementation follows existing test patterns in the file)
```

Check existing test patterns in `tests/test_pipeline.py` before implementing — follow whatever mocking pattern is already in use.

- [ ] **Step 3.4: Add `config` kwarg to `run_pipeline()`**

In `src/fitcv/pipeline.py`, update the signature:
```python
def run_pipeline(
    jobs_path: str,
    config_path: str = ".env.yaml",
    reporter: object = None,
    config: dict | None = None,   # If provided, skips load_config(config_path)
) -> dict[str, Any]:
```

At the top of `run_pipeline()`, replace:
```python
config = load_config(config_path)
```
with:
```python
if config is None:
    config = load_config(config_path)
```

- [ ] **Step 3.5: Update `bq_store.py` for new field**

In `insert_run()`, add to the `row` dict:
```python
"effective_settings_json": run.effective_settings_json,
```

In `_row_to_run()`, add to the `PipelineRun(...)` call:
```python
effective_settings_json=r.get("effective_settings_json"),
```

- [ ] **Step 3.6: Run all existing pipeline tests**

```bash
pytest tests/test_pipeline.py tests/fitcv_cp/test_bq_store.py -v
# Expected: all pass (no regressions)
```

- [ ] **Step 3.7: Commit**

```bash
git add assets/bigquery/pipeline_runs.sql src/fitcv/pipeline.py src/fitcv_cp/models.py src/fitcv_cp/bq_store.py
git commit -m "feat(cp/settings): add effective_settings_json to pipeline_runs and config kwarg to run_pipeline()"
```

---

## Task 4 — Worker: Read Snapshot and Pass Config

**Files:**
- Modify: `src/fitcv_cp/worker_job.py` (read `effective_settings_json` from run record; pass as `config=` to `run_pipeline()`)

- [ ] **Step 4.1: Write failing worker test**

```python
# In tests/fitcv_cp/test_worker_job.py, add:
import json

def test_worker_uses_effective_settings_not_bq_settings():
    """Worker must use the stored effective_settings_json, not re-read BQ settings."""
    bq = MagicMock()
    effective = {"pipeline": {"final_top_n": 5}, "gcp_project": "p",
                 "bigquery_dataset": "d", "service_account_key": "k"}

    # Simulate run record returned by get_run()
    mock_run = MagicMock()
    mock_run.effective_settings_json = json.dumps(effective)

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "total_jobs": 5, "passed_filter": 3, "ranked": 2, "cvs_generated": 1
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    # run_pipeline must have been called with the effective config, not with a config_path load
    call_kwargs = mock_pipeline.call_args[1]
    assert call_kwargs.get("config") is not None
    assert call_kwargs["config"]["pipeline"]["final_top_n"] == 5

def test_worker_falls_back_to_config_path_if_no_snapshot():
    """If effective_settings_json is None, worker falls back to config_path."""
    bq = MagicMock()
    mock_run = MagicMock()
    mock_run.effective_settings_json = None

    with patch("fitcv_cp.worker_job.get_run", return_value=mock_run), \
         patch("fitcv_cp.worker_job.run_pipeline", return_value={
             "total_jobs": 0, "passed_filter": 0, "ranked": 0, "cvs_generated": 0
         }) as mock_pipeline, \
         patch("fitcv_cp.worker_job._get_bq", return_value=bq):
        execute_pipeline_run(run_id="r1", jobs_path="data/sample_jobs.json",
                             config_path=".env.yaml")

    call_kwargs = mock_pipeline.call_args[1]
    # config should be None so run_pipeline loads from config_path
    assert call_kwargs.get("config") is None
```

- [ ] **Step 4.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_worker_job.py -v
# Expected: new tests fail
```

- [ ] **Step 4.3: Update `worker_job.py`**

In `execute_pipeline_run()`, replace the call to `run_pipeline()` with:

```python
import json as _json
from fitcv_cp.bq_store import get_run as _get_run

# Read the effective config snapshot stored at trigger time
run_record = _get_run(run_id, bq, project=project, dataset=dataset)
effective_config: dict | None = None
if run_record and run_record.effective_settings_json:
    try:
        effective_config = _json.loads(run_record.effective_settings_json)
    except Exception as exc:
        logger.warning("[run_id=%s] Failed to parse effective_settings_json: %s", run_id, exc)

summary = run_pipeline(
    jobs_path=jobs_path,
    config_path=config_path,
    reporter=reporter,
    config=effective_config,   # None → falls back to load_config(config_path)
)
```

- [ ] **Step 4.4: Run worker tests**

```bash
pytest tests/fitcv_cp/test_worker_job.py -v
# Expected: all pass
```

- [ ] **Step 4.5: Commit**

```bash
git add src/fitcv_cp/worker_job.py tests/fitcv_cp/test_worker_job.py
git commit -m "feat(cp/settings): worker reads effective_settings_json snapshot; passes config to run_pipeline()"
```

---

## Task 5 — FastAPI Settings Routes

**Files:**
- Modify: `src/fitcv_cp/app.py` (add settings endpoints; snapshot effective config in `POST /runs`)
- Modify: `src/fitcv_cp/app.py` (update `TriggerRequest` to accept `config_overrides`)
- Create: `src/fitcv_cp/templates/settings.html`
- Modify: `tests/fitcv_cp/test_app.py` (add settings tests)

- [ ] **Step 5.1: Write failing tests**

```python
# Add to tests/fitcv_cp/test_app.py:
import json

def test_get_settings_returns_dict():
    with patch("fitcv_cp.app.load_active_settings", return_value={"pipeline.final_top_n": 5}):
        resp = TestClient(_app()).get("/settings")
    assert resp.status_code == 200
    assert resp.json()["pipeline.final_top_n"] == 5


def test_post_settings_key_saves_and_returns_200():
    with patch("fitcv_cp.app.save_setting") as mock_save:
        resp = TestClient(_app()).post(
            "/settings/pipeline.final_top_n",
            json={"value": 7, "updated_by": "admin"},
        )
    assert resp.status_code == 200
    mock_save.assert_called_once()


def test_post_settings_key_rejects_invalid_value():
    resp = TestClient(_app()).post(
        "/settings/pipeline.final_top_n",
        json={"value": 0, "updated_by": "admin"},  # 0 violates int >= 1
    )
    assert resp.status_code == 422


def test_post_settings_key_rejects_unknown_key():
    resp = TestClient(_app()).post(
        "/settings/unknown.key",
        json={"value": 1, "updated_by": "admin"},
    )
    assert resp.status_code == 422


def test_post_runs_with_config_overrides():
    """POST /runs with per-run overrides snapshot effective settings."""
    with patch("fitcv_cp.app.load_active_settings", return_value={}), \
         patch("fitcv_cp.app.insert_run"), \
         patch("fitcv_cp.app.enqueue_run", return_value="run-123"), \
         patch("fitcv_cp.app.load_config", return_value={
             "gcp_project":"p", "bigquery_dataset":"d", "service_account_key":"k",
             "pipeline": {"final_top_n": 10}
         }):
        resp = TestClient(_app()).post("/runs", json={
            "jobs_path": "data/sample_jobs.json",
            "config_overrides": {"pipeline.final_top_n": 5},
        })
    assert resp.status_code == 201
    # The returned run_id should exist
    assert "run_id" in resp.json()


def test_post_runs_rejects_invalid_config_overrides():
    resp = TestClient(_app()).post("/runs", json={
        "jobs_path": "data/sample_jobs.json",
        "config_overrides": {"pipeline.final_top_n": 0},  # violates >= 1
    })
    assert resp.status_code == 422
```

- [ ] **Step 5.2: Run to confirm failure**

```bash
pytest tests/fitcv_cp/test_app.py -v
# Expected: new tests fail
```

- [ ] **Step 5.3: Update `app.py`**

Add imports:
```python
import json as _json
from fitcv.config import load_config
from fitcv_cp.settings_schema import (
    SETTINGS_SCHEMA, ValidationError, coerce_value, validate_settings, apply_settings_to_config
)
from fitcv_cp.settings_store import load_active_settings, save_setting
```

Update `TriggerRequest`:
```python
class TriggerRequest(BaseModel):
    jobs_path: str = "data/sample_jobs.json"
    config_path: str = ".env.yaml"
    triggered_by: str = "admin"
    config_overrides: dict[str, Any] = {}

    @field_validator("jobs_path")
    @classmethod
    def jobs_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("jobs_path must not be empty")
        return v
```

Update `trigger_run()` to build effective config snapshot before enqueue:
```python
@app.post("/runs", status_code=201)
def trigger_run(req: TriggerRequest) -> dict:
    # Build effective config: YAML → BQ settings → per-run overrides
    base_config = load_config(req.config_path)
    active_settings = load_active_settings(bq=bq, project=project, dataset=dataset)

    # Coerce and validate per-run overrides using the same schema
    coerced_overrides: dict[str, Any] = {}
    for k, v in req.config_overrides.items():
        try:
            coerced_overrides[k] = coerce_value(k, v)
        except KeyError:
            from fastapi import HTTPException
            raise HTTPException(status_code=422, detail=f"Unknown setting key: {k!r}")
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    try:
        validate_settings(coerced_overrides)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Merge: YAML < BQ < per-run overrides
    effective_config = dict(base_config)
    apply_settings_to_config(effective_config, active_settings)
    apply_settings_to_config(effective_config, coerced_overrides)

    run_id = _generate_run_id()
    run = PipelineRun(
        run_id=run_id,
        status=RunStatus.QUEUED,
        triggered_by=req.triggered_by,
        trigger_source="ui",
        jobs_path=req.jobs_path,
        config_path=req.config_path,
        created_at=datetime.datetime.utcnow(),
        effective_settings_json=_json.dumps(effective_config),
    )
    insert_run(run, bq, project=project, dataset=dataset)
    enqueue_run(
        jobs_path=req.jobs_path,
        config_path=req.config_path,
        triggered_by=req.triggered_by,
        redis_url=redis_url,
        run_id=run_id,
    )
    return {"run_id": run_id}
```

Add settings API routes:
```python
class SettingUpdate(BaseModel):
    value: Any
    updated_by: str = "admin"

@app.get("/settings")
def get_settings() -> dict:
    return load_active_settings(bq=bq, project=project, dataset=dataset)

@app.post("/settings/{key}", status_code=200)
def update_setting(key: str, body: SettingUpdate) -> dict:
    try:
        coerced = coerce_value(key, body.value)
    except KeyError:
        raise HTTPException(status_code=422, detail=f"Unknown setting key: {key!r}")
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    try:
        validate_settings({key: coerced})
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    save_setting(key, coerced, updated_by=body.updated_by, bq=bq, project=project, dataset=dataset)
    return {"key": key, "value": coerced}

@app.get("/admin/settings", response_class=HTMLResponse)
def admin_settings(request: Request) -> HTMLResponse:
    active = load_active_settings(bq=bq, project=project, dataset=dataset)
    return templates.TemplateResponse(
        "settings.html",
        {"request": request, "schema": SETTINGS_SCHEMA, "active": active}
    )

@app.post("/admin/settings", response_class=HTMLResponse)
def admin_settings_update(request: Request) -> HTMLResponse:
    # Form submit — handled via redirect pattern; see template
    ...
```

- [ ] **Step 5.4: Create `src/fitcv_cp/templates/settings.html`**

Extends `base.html`. Three sections (Retrieval, Timing, Ranking Policy) with:
- One `<input>` per key, showing current active value (BQ override if set, YAML default as placeholder)
- Keys with BQ overrides shown with a badge ("Custom")
- Ranking weights section includes a visible sum indicator
- Inline validation error display on submit failure
- "Reset to default" button per field (sets value back to schema default)

```html
{% extends "base.html" %}
{% block content %}
<h2>Pipeline Settings</h2>
<p>Changes take effect on the next triggered run.</p>

{% for group_name, group_label in [("retrieval", "Retrieval"), ("timing", "Timing / Throttling"), ("ranking", "Ranking Policy")] %}
<section>
  <h3>{{ group_label }}</h3>
  <table class="settings-table">
    <thead><tr><th>Setting</th><th>Active Value</th><th>Update</th></tr></thead>
    <tbody>
    {% for s in schema if s.group == group_name %}
    <tr>
      <td>
        <strong>{{ s.label }}</strong><br>
        <code>{{ s.key }}</code>
        {% if s.key in active %}<span class="badge custom">Custom</span>{% endif %}
      </td>
      <td>{{ active.get(s.key, s.default) }}</td>
      <td>
        <form method="post" action="/admin/settings/{{ s.key }}">
          <input type="number" name="value"
                 value="{{ active.get(s.key, s.default) }}"
                 step="{{ '1' if s.type == 'int' else '0.01' }}"
                 min="{{ '1' if s.type == 'int' else '0' }}"
                 max="{{ '100000' if s.type == 'int' else '1' }}">
          <button type="submit">Save</button>
        </form>
      </td>
    </tr>
    {% endfor %}
    </tbody>
  </table>
</section>
{% endfor %}
{% endblock %}
```

Also add a `POST /admin/settings/{key}` form handler route in `app.py`:
```python
@app.post("/admin/settings/{key}", response_class=HTMLResponse)
def admin_settings_update_key(request: Request, key: str,
                               value: str = Form(...)) -> HTMLResponse:
    try:
        coerced = coerce_value(key, value)
        validate_settings({key: coerced})
    except (KeyError, ValidationError, ValueError) as exc:
        # Re-render settings page with error
        active = load_active_settings(bq=bq, project=project, dataset=dataset)
        return templates.TemplateResponse(
            "settings.html",
            {"request": request, "schema": SETTINGS_SCHEMA,
             "active": active, "error": str(exc)},
            status_code=422,
        )
    save_setting(key, coerced, updated_by="admin", bq=bq, project=project, dataset=dataset)
    from fastapi.responses import RedirectResponse
    return RedirectResponse("/admin/settings", status_code=303)
```

- [ ] **Step 5.5: Run tests**

```bash
pytest tests/fitcv_cp/test_app.py -v
# Expected: all pass
```

- [ ] **Step 5.6: Commit**

```bash
git add src/fitcv_cp/app.py src/fitcv_cp/templates/settings.html tests/fitcv_cp/test_app.py
git commit -m "feat(cp/settings): add settings API and admin UI with effective config snapshot on POST /runs"
```

---

## Task 6 — Bootstrap + Smoke Test

**Files:**
- Modify: `scripts/bootstrap_bigquery.py` (register `pipeline_settings.sql`)

- [ ] **Step 6.1: Register new DDL in bootstrap script**

Add `pipeline_settings.sql` to the DDL file list in `scripts/bootstrap_bigquery.py`, then run:

```bash
python scripts/bootstrap_bigquery.py
# Expected: pipeline_settings table created (or already exists message)
```

Also run the full BQ migration to add `effective_settings_json` column to `pipeline_runs` if the table already exists. (If `pipeline_runs` was created fresh via bootstrap, the updated DDL already includes the new column.)

- [ ] **Step 6.2: Run full test suite**

```bash
pytest tests/ -v
# Expected: all tests pass, no regressions
```

- [ ] **Step 6.3: Docker smoke test**

```bash
docker compose up --build -d
sleep 15

# 1. Load settings page:
curl -s http://localhost:8000/admin/settings | grep "Pipeline Settings"
# Expected: HTML page rendered

# 2. Check current settings API:
curl http://localhost:8000/settings
# Expected: {} (empty — no overrides saved yet; YAML defaults apply)

# 3. Save a custom setting:
curl -X POST http://localhost:8000/settings/pipeline.final_top_n \
  -H "Content-Type: application/json" \
  -d '{"value": 5, "updated_by": "admin"}'
# Expected: {"key": "pipeline.final_top_n", "value": 5}

# 4. Verify setting is now active:
curl http://localhost:8000/settings
# Expected: {"pipeline.final_top_n": 5}

# 5. Trigger a run:
RUN_ID=$(curl -s -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"jobs_path": "data/sample_jobs.json"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['run_id'])")

# 6. Verify effective_settings_json captured the override:
curl http://localhost:8000/runs/$RUN_ID
# Expected: effective_settings_json contains "final_top_n": 5

# 7. Trigger run with per-run override that overrides the BQ setting:
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"jobs_path": "data/sample_jobs.json", "config_overrides": {"pipeline.final_top_n": 3}}'
# Expected: {"run_id": "<uuid>"} — this run will use final_top_n=3

# 8. Verify invalid override rejected:
curl -X POST http://localhost:8000/runs \
  -H "Content-Type: application/json" \
  -d '{"jobs_path": "data/sample_jobs.json", "config_overrides": {"pipeline.final_top_n": 0}}'
# Expected: 422 Unprocessable Entity

docker compose down
```

- [ ] **Step 6.4: Commit**

```bash
git add scripts/bootstrap_bigquery.py
git commit -m "feat(cp/settings): register pipeline_settings DDL in bootstrap script"
```

---

## Verification Plan

### Automated Tests

```bash
# Existing suite must remain green:
pytest tests/ --ignore=tests/fitcv_cp -v
# Expected: same baseline as before (274 passed, 7 skipped)

# New control-plane settings tests:
pytest tests/fitcv_cp/test_settings_schema.py tests/fitcv_cp/test_settings_store.py -v
# Expected: ~18 tests, all passed

# Full control-plane suite:
pytest tests/fitcv_cp/ -v
# Expected: all pass
```

### Manual Verification

1. Settings page renders all 16 editable keys grouped correctly
2. Saving a setting persists to `pipeline_settings` in BigQuery
3. After saving, `GET /settings` reflects the new value
4. Triggering a run captures the correct `effective_settings_json` on `pipeline_runs`
5. Per-run overrides in `POST /runs` override BQ settings in the snapshot
6. Invalid values (0, out-of-range thresholds, unknown keys) return 422
