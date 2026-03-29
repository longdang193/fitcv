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

- [ ] **Step 1.1: Add explicit export response models**
  - Define top-level run export model and per-result item model
  - Include run metadata, summary, ordered `results`, normalized `pipeline_status`, `scores`, and `cv`

- [ ] **Step 1.2: Define stable export ordering inputs**
  - Identify the persisted run-scoped tie-breaker source
  - Prefer an explicit run-scoped input-order index derived from the persisted snapshot or inspection data
  - Avoid relying on incidental BigQuery query order

- [ ] **Step 1.3: Write failing store-layer tests**
  - Cover happy-path assembly from persisted run-scoped rows
  - Cover deterministic ordering
  - Cover mixed statuses:
    - ranked with CV
    - ranked without CV
    - passed not ranked
    - rejected

- [ ] **Step 1.4: Implement export assembly functions in `bq_store.py`**
  - Fetch run metadata
  - Fetch run-scoped inspection/enrichment rows
  - Fetch CV rows for the run
  - Join by stable identity, preferably `job_url`
  - Normalize export shape without recomputing pipeline stages

- [ ] **Step 1.5: Confirm tests pass**

---

## Task 2: Normalize Status and Score Derivation

**Files:**

- Modify: `src/fitcv_cp/bq_store.py`
- Modify: `tests/test_fitcv_cp/test_bq_store.py`

- [ ] **Step 2.1: Codify persisted-facts status derivation**
  - `pipeline_status` must come from persisted facts, not heuristic guesses
  - Base derivation on available run-scoped facts such as:
    - filter outcome / reject reasons
    - enrichment presence
    - ranking presence
    - CV presence

- [ ] **Step 2.2: Normalize score payload**
  - Populate `final_score`, `ai_score`, `vector_score`, and fit label when available
  - Use `null` when a score field is not persisted

- [ ] **Step 2.3: Add tests for incomplete score payloads**
  - Cover rows with persisted rank but partial score data
  - Ensure these still sort deterministically after fully scored rows

- [ ] **Step 2.4: Confirm tests pass**

---

## Task 3: Add Admin Export Endpoint

**Files:**

- Modify: `src/fitcv_cp/app.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 3.1: Write failing endpoint tests**
  - `200` for succeeded runs with valid export payload
  - `404` for unknown run IDs
  - `409` for runs still in progress
  - Attachment headers:
    - `Content-Type: application/json`
    - `Content-Disposition: attachment; filename="fitcv-run-<run_id>-results.json"`

- [ ] **Step 3.2: Implement `GET /admin/runs/{run_id}/export.json`**
  - Reuse the same admin access model as run detail
  - Call the new export read model
  - Return JSON attachment without rerunning pipeline logic

- [ ] **Step 3.3: Guard first implementation scope**
  - Support succeeded runs only
  - Reject in-progress runs cleanly

- [ ] **Step 3.4: Confirm tests pass**

---

## Task 4: Add Run Detail Download Action

**Files:**

- Modify: `src/fitcv_cp/templates/run_detail.html`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 4.1: Write failing template/render tests**
  - Download button appears for succeeded runs
  - Download button does not appear for in-progress runs
  - Button points to `/admin/runs/{run_id}/export.json`

- [ ] **Step 4.2: Add `Download Results JSON` action to run detail**
  - Place near existing result actions
  - Keep existing per-CV markdown downloads unchanged

- [ ] **Step 4.3: Ensure UI wording matches spec**
  - Label: `Download Results JSON`

- [ ] **Step 4.4: Confirm tests pass**

---

## Task 5: Verify Persisted-Data-Only Behavior

**Files:**

- Modify: `tests/test_fitcv_cp/test_bq_store.py`
- Modify: `tests/test_fitcv_cp/test_app.py`

- [ ] **Step 5.1: Add regression coverage for persisted-data-only assembly**
  - Ensure export does not read mutable source files from `jobs_path`
  - Ensure export still works from run-scoped stored data once the run is complete

- [ ] **Step 5.2: Add regression coverage for deterministic tie-breaking**
  - Multiple rows with equal score fields still sort consistently
  - Final order uses the run-scoped stable tie-breaker

- [ ] **Step 5.3: Run the focused control-plane test suites**

---

## Task 6: Update Feature Docs

**Files:**

- Modify: `docs/features/trigger_run_management/trigger_run_management.yaml`
- Modify: `docs/features/trigger_run_management/history.md`

- [ ] **Step 6.1: Update feature contract**
  - Add run-results JSON export capability
  - Add spec and plan references

- [ ] **Step 6.2: Record implementation history**
  - Document endpoint, UI entry point, and export scope

---

## Verification Checklist

- [ ] Store-layer tests cover export assembly, status derivation, score normalization, and ordering
- [ ] App-layer tests cover endpoint status codes and attachment headers
- [ ] Template tests cover `Download Results JSON` visibility rules
- [ ] Export output includes original inspection shape, enriched inspection shape, scores, statuses, and inline CV markdown when present
- [ ] Export ordering is deterministic and uses a stable run-scoped tie-breaker beyond score fields
- [ ] Export is assembled only from persisted run-scoped data

---

## Risks and Notes

### Stable Ordering Risk

The plan depends on identifying a trustworthy persisted run-scoped tie-breaker. If the current inspection data does not expose one clearly, implementation should add a normalized input-order field at the read-model layer derived from the canonical run snapshot.

### Shape Consistency Risk

`original_job` and `enriched_job` should mirror the run-detail inspection shapes already used by the control plane. Avoid creating a second incompatible representation just for export.

### Scope Guard

Do not broaden the first implementation to failed or cancelled runs unless the persisted-data story is fully clear. Keep v1 to succeeded runs only.
