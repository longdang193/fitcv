# Run Results JSON Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `Download Results JSON` action on run detail that exports one run-scoped JSON artifact containing ordered jobs, enrichments, scores, statuses, and generated CV content.

**Architecture:** Extend the control-plane read layer to assemble exportable run results from persisted run-scoped data, expose a new admin download endpoint, and surface a single JSON download action on succeeded run detail pages. Reuse existing run-detail inspection data where possible, derive normalized export statuses from persisted facts, and sort rows deterministically with a stable run-scoped tie-breaker.

**Tech Stack:** Python, FastAPI, BigQuery, Jinja2

**Affected feature contract:** `docs/features/trigger_run_management/trigger_run_management.yaml`

**Supporting docs to update during implementation:**

- `docs/features/trigger_run_management/trigger_run_management.yaml`
- `docs/features/trigger_run_management/history.md`

---

## Task 1: Define Export Read Model and Data Contract

**Files:**

- Modify: `src/fitcv_cp/models.py`
- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [x] **Step 1.1: Add explicit export response models**
  - Implemented as a persisted JSON export snapshot shape rather than new typed Python dataclasses
  - Top-level payload now includes run metadata, summary, ordered `results`, normalized `pipeline_status`, `scores`, and `cv`

- [x] **Step 1.2: Define stable export ordering inputs**
  - Export rows use raw input order as a stable run-scoped tie-breaker
  - Deduplicated rows are tracked with explicit `input_index` during normalization
  - Export ordering no longer relies on incidental query order

- [x] **Step 1.3: Write failing store-layer tests**
  - Added/updated tests around persisted export snapshot mapping and storage
  - Added pipeline-level tests covering deterministic ordering and mixed statuses:
    - ranked with CV
    - ranked without CV
    - passed not ranked
    - rejected
    - deduplicated before enrichment

- [x] **Step 1.4: Implement export assembly functions in `bq_store.py`**
  - Completed with an adjusted architecture:
  - export assembly happens in `src/fitcv/pipeline.py`
  - the worker persists an immutable export snapshot via `src/fitcv_cp/worker_job.py`
  - `bq_store.py` stores and retrieves `results_export_json`
  - no recomputation occurs at download time

- [x] **Step 1.5: Confirm tests pass**

---

## Task 2: Normalize Status and Score Derivation

**Files:**

- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [x] **Step 2.1: Codify persisted-facts status derivation**
  - Implemented in the export builder using run-scoped facts:
    - filter outcome / reject reasons
    - shortlist / ranking presence
    - CV presence
    - deduplication exclusions
  - Added explicit `deduplicated_before_enrichment` handling to avoid misleading fallback statuses

- [x] **Step 2.2: Normalize score payload**
  - Export now populates `final_score`, `ai_score`, `vector_score`, and fit label when available
  - Uses `null` when score fields are not available for the row
  - Fixed vector-score normalization to support actual `run_vector_search()` field names (`vector_similarity`, `vector_rank`)

- [x] **Step 2.3: Add tests for incomplete score payloads**
  - Added focused pipeline tests for shortlist/ranking score propagation and deterministic ordering
  - Covered rows with score gaps and non-ranked rows with available vector score

- [x] **Step 2.4: Confirm tests pass**

---

## Task 3: Add Admin Export Endpoint

**Files:**

- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 3.1: Write failing endpoint tests**
  - `200` for succeeded runs with valid export payload
  - `404` for unknown run IDs
  - `409` for runs still in progress
  - Attachment headers:
    - `Content-Type: application/json`
    - `Content-Disposition: attachment; filename="fitcv-run-<run_id>-results.json"`

- [x] **Step 3.2: Implement `GET /admin/runs/{run_id}/export.json`**
  - Reuse the same admin access model as run detail
  - Return the persisted export snapshot without rerunning pipeline logic
  - Pretty-print JSON for human readability on download

- [x] **Step 3.3: Guard first implementation scope**
  - Support succeeded runs only
  - Reject in-progress runs cleanly

- [x] **Step 3.4: Confirm tests pass**

---

## Task 4: Add Run Detail Download Action

**Files:**

- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 4.1: Write failing template/render tests**
  - Download button appears for succeeded runs
  - Download button does not appear for in-progress runs
  - Button points to `/admin/runs/{run_id}/export.json`

- [x] **Step 4.2: Add `Download Results JSON` action to run detail**
  - Place near existing result actions
  - Keep existing per-CV markdown downloads unchanged

- [x] **Step 4.3: Ensure UI wording matches spec**
  - Label: `Download Results JSON`

- [x] **Step 4.4: Confirm tests pass**

---

## Task 5: Verify Persisted-Data-Only Behavior

**Files:**

- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [x] **Step 5.1: Add regression coverage for persisted-data-only assembly**
  - Export is persisted at run completion and downloaded from `results_export_json`
  - Download path does not reread mutable `jobs_path` files
  - Worker persistence is covered in `tests/test_fitcv_cp/test_worker_job.py`

- [x] **Step 5.2: Add regression coverage for deterministic tie-breaking**
  - Pipeline tests cover deterministic ordering with the run-scoped input-order tie-breaker
  - Dedupe exclusions also preserve `input_index` for deterministic export rows

- [x] **Step 5.3: Run the focused control-plane test suites**

---

## Task 6: Update Feature Docs

**Files:**

- Modify: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Modify: `docs/features/trigger_run_management/history.md`

- [x] **Step 6.1: Update feature contract**
  - Add run-results JSON export capability
  - Add spec and plan references

- [x] **Step 6.2: Record implementation history**
  - Document endpoint, UI entry point, and export scope

---

## Verification Checklist

- [x] Store-/pipeline-layer tests cover export assembly, status derivation, score normalization, and ordering
- [x] App-layer tests cover endpoint status codes and attachment headers
- [x] Template tests cover `Download Results JSON` visibility rules
- [x] Export output includes original inspection shape, enriched inspection shape, scores, statuses, and inline CV markdown when present
- [x] Export ordering is deterministic and uses a stable run-scoped tie-breaker beyond score fields
- [x] Export is assembled only from persisted run-scoped data

---

## Post-Implementation Notes

- Export assembly was implemented in the pipeline/worker path and persisted as `pipeline_runs.results_export_json`, rather than being assembled on demand in `bq_store.py`.
- Additional follow-up work landed beyond the original plan:
  - pretty-printed JSON downloads for readability
  - compact `pipeline_complete` event payloads
  - `layer3_shortlist` / `layer3_ai_score` event visibility
  - `layer4_cv_error` event visibility
  - explicit `deduplicated_before_enrichment` export/UI handling
- Remaining follow-up ideas not in this plan:
  - add CV generation metadata such as model and prompt version into the exported `cv` payload
  - consider a future structured CV intermediate representation in addition to `cv.markdown`

---

## Risks and Notes

### Stable Ordering Risk

The plan depends on identifying a trustworthy persisted run-scoped tie-breaker. If the current inspection data does not expose one clearly, implementation should add a normalized input-order field at the read-model layer derived from the canonical run snapshot.

### Shape Consistency Risk

`original_job` and `enriched_job` should mirror the run-detail inspection shapes already used by the control plane. Avoid creating a second incompatible representation just for export.

### Scope Guard

Do not broaden the first implementation to failed or cancelled runs unless the persisted-data story is fully clear. Keep v1 to succeeded runs only.
