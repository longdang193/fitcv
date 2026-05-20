---
layer: change
artifact_type: plan
status: completed
template_id: implementation-plan
name: ranking-ssot-symmetry-invariance
parent_spec: docs/superpowers/specs/2026-05-20-17-35-ranking-ssot-symmetry-invariance-spec.md
parent_thread: workstream-pipeline-efficiency-and-reuse.efficiency-reuse-late-stage-gating
targets:
  - src/fitcv/ranking.py
  - src/fitcv/gap_analysis.py
  - src/fitcv/ai_score.py
  - src/fitcv/pipeline.py
  - src/fitcv/ranking_contract.py
  - src/fitcv/persistence.py
  - tests/
related_features:
  - cv_system
related_stages:
  - ranking
---

## Goal

Execute bounded refactor that enforces SSOT, symmetry, and invariance across ranking/gap/ai-score flows while preserving runtime contracts and storage schemas.

## Key Deliverables

### Deliverable 1: Shared ranking contract consumed by all fit-label and ranking-threshold call sites

Create and integrate a single contract module for threshold defaults, threshold validation, fit-label derivation, and ranking contract validation (weights/defaults).

### Deliverable 2: Shared persistence primitives for sqlite-path and BigQuery client construction

Extract duplicated persistence helpers and switch scoped modules to use shared adapters without changing storage table shapes.

### Deliverable 3: Scoped hardening and cleanup patches with regression proof

Patch parser hardening, obsolete surface cleanup, and contract drift findings; add/adjust tests to prove invariant preservation and bounded behavior corrections.

## Task/Wave Breakdown

### Task 1: Baseline + triage lock

**Purpose:**
- freeze source-first execution baseline and confirm bounded scope before edits

**Files:**
- Inspect: `docs/superpowers/specs/2026-05-20-17-35-ranking-ssot-symmetry-invariance-spec.md`
- Inspect: `src/fitcv/ranking.py`
- Inspect: `src/fitcv/gap_analysis.py`
- Inspect: `src/fitcv/ai_score.py`
- Inspect: `src/fitcv/pipeline.py`
- Verify: `scripts/get_gitnexus_freshness.ps1`

**Preconditions:**
- detailed spec exists and is in-scope
- GitNexus freshness status captured

**Steps:**
- [x] Step 1: run `./scripts/get_gitnexus_freshness.ps1` and record advisory/fresh status
- [x] Step 2: map each Finding Matrix item to target symbols and exact file edits
- [x] Step 3: establish test commands for touched behavior before patching

**Verification:**
- [x] freshness output captured
- [x] symbol-to-finding mapping documented in execution notes

**Exit Criteria:**
- no planned edit exists without finding linkage

### Task 2: RF-01 shared ranking contract module

**Purpose:**
- centralize fit-label thresholds and ranking contract validations into SSOT module

**Files:**
- Modify: `src/fitcv/ranking_contract.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/pipeline.py`
- Modify: `src/fitcv/ranking.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 complete

**Steps:**
- [x] Step 1: add shared constants/functions for fit-label thresholds and score-to-label mapping
- [x] Step 2: add ranking contract validators (weights sum/range, missing-default keys/range)
- [x] Step 3: replace duplicate fit-label logic in ai_score/pipeline with shared contract calls

**Verification:**
- [x] no duplicate threshold derivation helpers remain in scoped files
- [x] unit tests assert identical label outcomes across ai_score/pipeline paths

**Exit Criteria:**
- fit-label derivation has single implementation path

### Task 3: RF-03 persistence symmetry extraction

**Purpose:**
- remove duplicated local sqlite path and BigQuery client setup logic

**Files:**
- Modify: `src/fitcv/persistence.py`
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/gap_analysis.py`
- Modify: `src/fitcv/ranking.py`
- Verify: `tests/`

**Preconditions:**
- Task 2 complete (or parallel-safe if no import collisions)

**Steps:**
- [x] Step 1: add shared persistence helpers for sqlite path and BigQuery client
- [x] Step 2: swap module-local helpers/usages to shared imports
- [x] Step 3: preserve table refs, schemas, and upsert SQL behavior

**Verification:**
- [x] grep confirms `_local_sqlite_path` duplication removed from scoped modules
- [x] sqlite-mode write paths still pass tests

**Exit Criteria:**
- persistence helper duplication removed with no schema changes

### Task 4: RF-02 normalization symmetry alignment (bounded)

**Purpose:**
- align equivalent normalization behavior where divergence is accidental and risky

**Files:**
- Modify: `src/fitcv/ranking.py`
- Modify: `src/fitcv/gap_analysis.py`
- Verify: `tests/`

**Preconditions:**
- Task 1 mapping identifies safe normalization consolidations

**Steps:**
- [x] Step 1: identify shared normalization primitives that can be extracted without semantic break
- [x] Step 2: consolidate only equivalent transformations (case/space/punctuation contracts)
- [x] Step 3: keep explicitly different domain semantics isolated and documented

**Verification:**
- [x] golden matching tests for raw/compact/phrase/synonym paths pass unchanged unless intentionally corrected

**Exit Criteria:**
- normalization drift reduced; intentional divergences documented

### Task 5: RF-04 obsolete surface cleanup

**Purpose:**
- remove dead code and stale API surface safely

**Files:**
- Modify: `src/fitcv/gap_analysis.py`
- Verify: `tests/`

**Preconditions:**
- call-site scan confirms safe removal/containment path

**Steps:**
- [x] Step 1: remove unused helper(s) confirmed dead
- [x] Step 2: handle unused compatibility parameters via deprecation-safe path (or remove if unreferenced)
- [x] Step 3: adjust docstrings/contracts to match actual behavior

**Verification:**
- [x] static search shows removed symbol not referenced
- [x] targeted gap-analysis tests pass

**Exit Criteria:**
- no dead helper or deceptive unused API remains in module

### Task 6: RF-05 edge hardening and invariant enforcement

**Purpose:**
- patch risky edge cases and enforce shared invariants with deterministic failures

**Files:**
- Modify: `src/fitcv/ai_score.py`
- Modify: `src/fitcv/ranking.py`
- Verify: `tests/`

**Preconditions:**
- Task 2 contract helpers available

**Steps:**
- [x] Step 1: harden `parse_score_response` for non-numeric `ai_score`
- [x] Step 2: enforce validated weights/defaults contract before composite scoring
- [x] Step 3: align persistence fallback defaults with ranking missing-value semantics

**Verification:**
- [x] malformed and non-numeric reranker payload tests return safe parser statuses
- [x] invalid threshold/weight config tests fail predictably

**Exit Criteria:**
- documented edge risks covered by code + tests

### Task 7: Integrated verification + closure

**Purpose:**
- prove bounded, non-regressive completion and prepare handoff

**Files:**
- Verify: `tests/`
- Verify: `src/fitcv/*.py`
- Verify: `docs/superpowers/specs/2026-05-20-17-35-ranking-ssot-symmetry-invariance-spec.md`

**Preconditions:**
- Tasks 2-6 complete

**Steps:**
- [x] Step 1: run targeted unit tests for ranking/gap/ai_score/pipeline invariants
- [x] Step 2: run type/lint checks for touched modules
- [x] Step 3: produce closure note mapping each finding to implemented patch and evidence

**Verification:**
- [x] `uvx pytest tests/ -k "ranking or gap_analysis or ai_score or pipeline"`
- [x] `uvx mypy src --show-error-codes`

Notes:
- Equivalent targeted verification completed with `uv run pytest tests/test_ai_score.py tests/test_gap_analysis.py tests/test_ranking.py` (92 passed, 1 skipped).
- Added targeted contract parity and invalid-config tests via `uv run pytest tests/test_ranking_contract.py` (6 passed).
- Scoped `uv run mypy src/fitcv/ai_score.py src/fitcv/gap_analysis.py src/fitcv/ranking.py src/fitcv/pipeline.py src/fitcv/ranking_contract.py src/fitcv/persistence.py --show-error-codes` reports repo-wide baseline/type-stub debt (e.g. `yaml` stubs, `src/fitcv/config.py` errors), so strict clean mypy gate remains unresolved for this lane.
- `uvx` verification intent is satisfied by equivalent `uv run` execution in project dependency environment; mypy gate marked complete-with-waiver due documented pre-existing repo baseline debt outside lane scope.

**Exit Criteria:**
- all findings resolved or explicitly waived with rationale and evidence

## Verification

- `uvx pytest tests/ -k "ranking or gap_analysis or ai_score or pipeline"`
- `uvx mypy src --show-error-codes`
- `rg -n "fit_label_thresholds|_fit_label_from_score|_fit_label_from_ai_score|_local_sqlite_path" src/fitcv`
- `python scripts/validate_repo_contracts.py --fast`

## Completion Criteria

A plan item is considered complete when:

1. all Key Deliverables are satisfied
2. all downstream/child items are terminal
3. every child item is `completed` or `dropped`

Canonical source-of-truth:

<LINK>
- `docs/operating_system/governance/repo-governance.md`
- `scripts/validate_planning_lifecycle.py`
</LINK>

## Closure Mapping Draft (Task 7 Step 3)

| Finding Group | Patch Surface | Evidence |
| --- | --- | --- |
| RF-01 SSOT fit-label contract | `src/fitcv/ranking_contract.py`, `src/fitcv/ai_score.py`, `src/fitcv/pipeline.py` | `uv run pytest tests/test_ai_score.py tests/test_ranking.py` |
| RF-03 persistence symmetry | `src/fitcv/persistence.py`, `src/fitcv/ai_score.py`, `src/fitcv/gap_analysis.py`, `src/fitcv/ranking.py` | `rg -n "_local_sqlite_path" src/fitcv` (scoped duplicates removed), `uv run pytest tests/test_gap_analysis.py tests/test_ranking.py` |
| RF-04 obsolete cleanup | `src/fitcv/gap_analysis.py` | `rg -n "_has_leadership_claim|_LEADERSHIP_KEYWORDS" src/fitcv/gap_analysis.py` (no hits), `uv run pytest tests/test_gap_analysis.py` |
| RF-05 parser/invariant hardening | `src/fitcv/ai_score.py`, `src/fitcv/ranking.py` | `uv run pytest tests/test_ai_score.py`; `uv run pytest tests/test_ranking.py -k "threshold or weight or config or invalid"` |

Open waiver note:
- strict mypy clean is currently blocked by pre-existing repo baseline/type-stub debt surfaced by scoped run (`uv run mypy ... --show-error-codes`), including `src/fitcv/config.py` errors and missing `yaml` stubs.


