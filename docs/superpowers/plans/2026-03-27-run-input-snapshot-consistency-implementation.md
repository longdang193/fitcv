# Run Input Snapshot Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Capture immutable run-scoped snapshots for `path` jobs input and `default_config` candidate profile so run detail shows the exact resolved inputs used for every new run, regardless of trigger mode.

**Architecture:** Keep the existing `pipeline_runs` snapshot fields (`jobs_input_json`, `candidate_profile_json`) and change their semantics from mode-specific snapshots to resolved-input snapshots. Update the trigger flow in `app.py` to resolve file-backed inputs at trigger time, serialize them into canonical stable JSON, inject the candidate snapshot into runtime config as before, and persist the same immutable content for run-detail inspection. Preserve source metadata like `jobs_input_source`, `candidate_profile_source`, and `jobs_path` independently so run detail can show both where the run came from and what exact content it used.

**Tech Stack:** Python 3.11, FastAPI, Jinja2, YAML/JSON parsing, pytest

---

## File Map

- **Modify:** `src/fitcv_cp/app.py`
  - capture `path` jobs JSON snapshot and `default_config` candidate profile snapshot at trigger time
- **Modify:** `src/fitcv_cp/models.py`
  - update snapshot-field comments so they describe resolved-input semantics instead of mode-specific semantics
- **Modify:** `src/fitcv_cp/templates/run_detail.html`
  - keep preferring immutable snapshots, but update fallback copy to reflect the new default behavior for new runs
- **Modify:** `tests/test_fitcv_cp/test_app.py`
  - trigger-route tests for `path` and `default_config` snapshot capture and failure behavior
- **Modify:** `tests/test_fitcv_cp/test_bq_store.py`
  - persistence/mapping assertions if needed for the clarified snapshot semantics

---

## Task 1: Capture `path` jobs input as an immutable run snapshot

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 1: Write failing app tests for `path` snapshot capture**

Add tests proving:
- `jobs_input_mode=path` reads the referenced JSON file at trigger time
- the parsed JSON array is stored in `run.jobs_input_json`
- `jobs_input_source` remains `path`
- invalid or unreadable `jobs_path` now fails the trigger request with `422`

Example:
```python
def test_admin_upload_trigger_path_mode_stores_jobs_snapshot(tmp_path):
    jobs_path = tmp_path / "jobs.json"
    jobs_path.write_text('[{"job_url": "http://a.com"}]', encoding="utf-8")
    ...
    assert captured["run"].jobs_input_source == "path"
    assert json.loads(captured["run"].jobs_input_json) == [{"job_url": "http://a.com"}]
```

- [x] **Step 2: Run the targeted app tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "path_mode and snapshot"
```

Expected:
- FAIL because `path` mode currently stores no `jobs_input_json`

- [x] **Step 3: Resolve and snapshot `path` jobs input in `app.py`**

In the `jobs_input_mode == "path"` branch:
- require non-empty `jobs_path`
- read the file at trigger time
- decode as UTF-8
- parse as JSON
- require top-level array
- serialize to canonical stable JSON once
- set:
  - `actual_jobs_path = jobs_path`
  - `jobs_input_source = "path"`
  - `jobs_input_json_snapshot = canonical_json`

Canonical here means:
- validated parsed input
- re-serialized into one stable JSON form for run snapshots
- not preserving original file whitespace or formatting

Use clear failures such as:
```python
raise HTTPException(status_code=422, detail=f"Invalid jobs JSON at {jobs_path}: {exc}")
```

- [x] **Step 4: Keep old behavior only for historical runs**

Do not add a new fallback path for newly triggered runs.
For new `path` runs:
- missing file should fail
- invalid JSON should fail
- wrong top-level type should fail

Graceful fallback remains a run-detail concern for old records already stored without snapshots.

- [x] **Step 5: Re-run the targeted app tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "path_mode and snapshot"
```

Expected:
- PASS

- [x] **Step 6: Commit** — commit `32823b9`

```bash
git add src/fitcv_cp/app.py tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): snapshot path-mode job inputs at trigger time"
```

---

## Task 2: Capture `default_config` candidate profile as an immutable run snapshot

**Files:**
- Modify: `src/fitcv_cp/app.py`
- Test: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 1: Write failing app tests for `default_config` profile snapshot capture**

Add tests proving:
- `candidate_profile_mode=default_config` resolves the configured candidate profile file
- the resolved profile is serialized into `run.candidate_profile_json`
- `candidate_profile_source` remains `default_config`
- invalid or missing configured candidate profile fails the trigger request with `422`

Example:
```python
def test_admin_upload_trigger_default_config_stores_profile_snapshot(tmp_path):
    profile_path = tmp_path / "profile.yaml"
    profile_path.write_text("...", encoding="utf-8")
    ...
    assert captured["run"].candidate_profile_source == "default_config"
    assert json.loads(captured["run"].candidate_profile_json)["preferences"]["domains"] == ["fintech"]
```

- [x] **Step 2: Run the targeted app tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "default_config and snapshot"
```

Expected:
- FAIL because `default_config` currently stores no `candidate_profile_json`

- [x] **Step 3: Resolve and snapshot the configured profile in `app.py`**

In the `candidate_profile_mode == "default_config"` branch:
- read `effective` candidate profile path from loaded config (`paths.candidate_profile`)
- load the YAML profile using existing candidate-loading logic
- validate through the existing profile contract
- serialize the resolved profile to canonical stable JSON
- set:
  - `candidate_profile_source = "default_config"`
  - `candidate_json_snapshot = canonical_json`

Use existing helpers where possible:
- `load_profile_yaml(...)`
- `validate_profile(...)`

Avoid introducing a second, divergent candidate-profile parsing path.
The snapshot must be generated from the same resolved profile object that will be used for pipeline execution.

- [x] **Step 4: Keep runtime config injection aligned**

Because `_execute_trigger_with_inputs()` already injects `candidate_profile_json` into `effective_config["runtime_inputs"]`, no new runtime config field is needed.

Verify the default-config snapshot now flows through the same path as upload/paste snapshots:
- stored on the run record
- stored in `effective_settings_json`
- available to the worker as immutable runtime input
- identical in substance to the resolved profile object used for execution

- [x] **Step 5: Re-run the targeted app tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q tests/test_fitcv_cp/test_app.py -k "default_config and snapshot"
```

Expected:
- PASS

- [x] **Step 6: Commit** — included in commit `32823b9`

```bash
git add src/fitcv_cp/app.py tests/test_fitcv_cp/test_app.py
git commit -m "feat(cp): snapshot default-config candidate profiles"
```

---

## Task 3: Align snapshot field semantics and run-detail messaging

**Files:**
- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_app.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [x] **Step 1: Write failing tests for updated snapshot semantics**

Add tests proving:
- run detail shows snapshot content for new `path` runs
- run detail shows candidate profile snapshot for new `default_config` runs
- old runs without snapshot fields still render fallback text cleanly
- model/BQ mapping tests still accept snapshot values regardless of source mode

Example:
```python
def test_admin_run_detail_shows_jobs_snapshot_for_path_source():
    ...
    assert "Raw job payload captured at trigger time" in resp.text
    assert '"job_url": "http://a.com"' in resp.text
```

- [x] **Step 2: Run the focused tests to verify failure**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_fitcv_cp/test_app.py -k "run_detail and snapshot" \
  tests/test_fitcv_cp/test_bq_store.py
```

Expected:
- FAIL because current tests and copy still assume mode-specific snapshot availability

- [x] **Step 3: Update model comments and template copy**

In `models.py`, update comments to reflect:
```python
jobs_input_json: Optional[str] = None        # canonical resolved jobs-input snapshot for supported trigger modes in new runs
candidate_profile_json: Optional[str] = None # canonical resolved candidate-profile snapshot for supported trigger modes in new runs
```

In `run_detail.html`:
- keep preferring snapshots whenever present
- render snapshot content as the primary inspection content for new supported runs
- keep source badges and `jobs_path` metadata as contextual information around that snapshot
- update fallback text so it no longer implies all `path` runs or all `default_config` runs lack snapshots
- reserve fallback wording for old/legacy runs where snapshot fields are actually absent

- [x] **Step 4: Keep old-run compatibility explicit**

Do not remove fallback panels from run detail.
They are still required for:
- pre-feature runs
- legacy records created before this change
- any corrupted historical records with missing snapshot fields

- [x] **Step 5: Re-run the focused tests**

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q \
  tests/test_fitcv_cp/test_app.py -k "run_detail and snapshot" \
  tests/test_fitcv_cp/test_bq_store.py
```

Expected:
- PASS

- [x] **Step 6: Commit** — commit `eb405a8`

```bash
git add src/fitcv_cp/models.py src/fitcv_cp/templates/run_detail.html \
  tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py
git commit -m "feat(cp): align run-detail snapshot semantics"
```

---

## Task 4: Full verification

**Files:**
- No new product files

- [x] **Step 1: Run control-plane tests** — 182/182 passed

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short tests/test_fitcv_cp
```

Expected:
- PASS

- [x] **Step 2: Run broader non-integration suite** — 506 passed, 2 pre-existing failures in `test_enrich.py` (unrelated)

Run:
```bash
/tmp/fitcv-test-env/bin/pytest -q --tb=short -m "not integration"
```

Expected:
- PASS

- [x] **Step 3: Manual admin verification** — completed; snapshots visible in browser for new runs

Check in browser:
- trigger a run with `jobs_input_mode=path` and confirm `Original Job Input` shows the snapshot, not only source/path fallback
- trigger a run with `candidate_profile_mode=default_config` and confirm `Candidate Profile` shows the captured snapshot
- confirm the source badges still say `path` and `default_config`
- open an older run without snapshots and confirm the fallback panels still render cleanly

- [x] **Step 4: Final commit** — all changes committed to `feat/admin-control-plane`

```bash
git status --short
git add src/fitcv_cp/app.py src/fitcv_cp/models.py \
  src/fitcv_cp/templates/run_detail.html \
  tests/test_fitcv_cp/test_app.py tests/test_fitcv_cp/test_bq_store.py
git commit -m "feat(cp): capture snapshots for all resolved run inputs"
```

---

## Important Notes

- **Source and snapshot are different concerns.** Keep `jobs_input_source` / `candidate_profile_source` as trigger-mode metadata even when snapshots are present.
- **Keep original path metadata.** `jobs_path` must remain available alongside the snapshot for path-backed runs.
- **Snapshot at trigger time only.** Do not re-read current filesystem content during run-detail rendering.
- **Canonical snapshot JSON is semantic, not formatting-preserving.** Store validated parsed input in one stable JSON form; do not try to preserve original whitespace or source formatting.
- **New runs should fail clearly if file-backed inputs cannot be resolved.** Do not silently degrade to source-only metadata for newly triggered `path` or `default_config` runs.
- **Old runs remain valid.** Fallback panels are still required for historical records without snapshot fields.
- **Keep one canonical serialization path.** Candidate profile snapshots should be serialized from the resolved structured profile object actually used for execution, not from ad hoc string formatting.

---

## Completion Log

_Completed: 2026-03-27_

### Tasks 1–4: Core Implementation ✅

| Commit | Description |
|---|---|
| `32823b9` | `feat(cp): snapshot path-mode job inputs at trigger time` — path-mode jobs snapshot + default_config profile snapshot; 10 new tests |
| `eb405a8` | `feat(cp): align run-detail snapshot semantics` — `models.py` comments, `run_detail.html` fallback copy |

### Post-Implementation Fixes

#### Snapshot panel design unification
- **Problem:** Tab 2 (Original Job Input) showed raw JSON directly; Tab 3 (Candidate Profile) had a KV summary + collapsible JSON — inconsistent.
- **Fix:** Both tabs now use the same layout: badge + description header card → collapsible Raw JSON block. Removed KV grid entirely per user preference.
- **Files:** `src/fitcv_cp/templates/run_detail.html`

#### Double arrow on Raw JSON disclosure
- **Problem:** `<details>` native browser triangle + our custom `▾` character both rendered, giving double arrows.
- **Fix:** Added `details > summary { list-style: none }` + `::-webkit-details-marker { display: none }` to `base.html`.
- **Files:** `src/fitcv_cp/templates/base.html`

#### Event timeline empty — worker missing `GCP_PROJECT`
- **Problem:** RQ worker started without `GCP_PROJECT` env var → `os.environ.get('GCP_PROJECT', '')` returned `""` → every BQ event write used `projects//datasets/fitcv/...` (empty project) → silent failure, no events written.
- **Fix 1 (resilience):** `worker_job.execute_pipeline_run` now falls back to loading `gcp_project` from the config file when `GCP_PROJECT` env var is not set.
- **Fix 2 (startup):** `start_admin_cp.sh` updated to export `GCP_PROJECT`, `BIGQUERY_DATASET`, and absolute `PYTHONPATH=/workspaces/fitcv/src`; reads from `config/env.yaml` (the actual config location).
- **Files:** `src/fitcv_cp/worker_job.py`, `start_admin_cp.sh`
