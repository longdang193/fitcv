---
layer: change
artifact_type: spec
status: proposed
template_id: detailed-specification
name: fitcv_cp_run_artifact_ssot_symmetry_invariance
parent_thread: workstream-operator-control-plane.fitcv-cp-run-artifact-ssot-symmetry-refactor
targets:
  - src/fitcv_cp/worker_job.py
  - src/fitcv_cp/bq_store.py
related_features: []
related_stages: []
---

# FitCV CP Run Artifact SSOT + Symmetry Refactor (Spec)

## Goal

Make run-artifact payload building + encoding + persistence behavior single-source-of-truth (SSOT), symmetric across artifact types, invariant across backends (BigQuery vs sqlite), while preserving runtime behavior and backward compatibility.

In-scope action set:
- WJ-R1 normalize artifact encoding SSOT
- WJ-R2 remove duplicate hash implementations
- WJ-R3 contract-ize run artifact envelope
- BQ-R1 unify `update_run_*` return contract
- BQ-R2 unify backend-mode selection SSOT
- BQ-R3 fix sqlite connection contract drift
- X-R1 registry for run JSON fields + schema evolution policy SSOT

## Key Deliverables

### Deliverable 1: Canonical artifact envelope + encoding rules

Define one canonical artifact-envelope shape + one canonical encoding path used by all worker-built artifacts (dict-builder → encoder), with explicit schema-version stamping rules.

### Deliverable 2: Canonical persistence result contract

Define one canonical persistence result contract returned by all `bq_store.update_run_*` write paths (BigQuery + sqlite), with stable degradation reasons and missing-column policy.

### Deliverable 3: Canonical registries for field names + schema evolution

Define SSOT registries for pipeline run JSON field names and for “missing column fallback / degrade / skip” policies, eliminating ad-hoc stringly-typed behavior.

## Task/Wave Breakdown

### Wave 1: Source-first analysis

**Purpose:**
- lock current behavior surfaces (payloads, encoding, persistence, degradation) before change

**Steps:**
- [x] inventory all worker-built run artifacts in `src/fitcv_cp/worker_job.py` (payload keys, schema-version keys, encoding function used)
- [x] inventory all persistence entrypoints in `src/fitcv_cp/bq_store.py` used by worker (signature, return/raise behavior, sqlite vs BigQuery divergence)
- [x] confirm callsites for `update_run_*` across repo (blast radius for BQ-R1) and record required compatibility bridges
- [x] record “hash identity” usage sites and expected stability needs (dedupe, reuse, audit diff)

**Verification:**
- [x] current-state table exists in this spec (see Design Decisions: “Current-State Inventory”)

**Exit Criteria:**
- no decision depends on unknown artifact shape or unknown persistence outcome semantics

### Wave 2: Decision closure

**Purpose:**
- choose SSOT shapes and lock invariants + compatibility rules

**Steps:**
- [x] decide canonical artifact envelope fields and required keys
- [x] decide canonical encoding path (single helper)
- [x] decide canonical fingerprint helper and migration policy (if hash bytes change)
- [x] decide canonical persistence-result structure and rollout strategy (bridge period for old callsites)
- [x] decide backend selection SSOT (`bq is None` vs env vs runtime resolver) and delete/retire competing knobs

**Verification:**
- [x] each action WJ-R1..X-R1 has explicit “before/after contract” statements and acceptance criteria

**Exit Criteria:**
- spec contains implementable contracts with bounded scope and testable proof targets

### Wave 3: Validation and approval readiness

**Purpose:**
- define proof and rollback so implementation plan can execute safely

**Steps:**
- [x] define unit tests for payload/encoding/fingerprint invariants
- [x] define unit tests for sqlite degraded paths + BigQuery missing-column fallbacks (mocked)
- [x] define migration controls (feature flags, dual-write/dual-hash if needed)
- [x] define rollback plan (containment switches, revert commit scope)

**Verification:**
- [x] validation plan includes evidence targets and exact commands/tests to run

**Exit Criteria:**
- spec ready for `skill-writing-plans` handoff

## Design Decisions

### Decision: Current-State Inventory (worker artifacts + persistence)

- context: spec must patch drift/contradiction/duplication seen in `worker_job.py` + `bq_store.py`
- choice: record current-state inventory as truth baseline before refactor
- alternatives considered:
  - skip inventory and “fix forward” while coding (rejected: violates evidence-first + increases regression risk)
- impact:
  - inventory becomes acceptance-test input (golden payloads, signature expectations)

**Worker artifacts (initial inventory; must be completed in Wave 1):**
- mapping suggestions payload built via `json.dumps(...)` (not `encode_json_object(...)`) → encoding drift risk
- stage transition artifacts payload built via `_build_*_payload_dict` + `encode_json_object(...)` → preferred pattern
- settings used payload built via `_build_*_payload_dict` + `encode_json_object(...)` → preferred pattern
- fingerprinting uses both `stable_sha256_fingerprint(...)` and local `_stable_sha256_json(...)` → hash SSOT drift risk
- duplicate import `ensure_review_item_id` appears twice → contradiction/obsolete surface

**Persistence inventory (initial; must be completed in Wave 1):**
- `bq_store.update_run_*` functions mostly return `None`, but `update_run_synonym_proposals` returns persistence-result dict → symmetry drift
- missing-column handling differs by field (raise vs degrade-return vs legacy SQL fallback) → invariance drift risk
- sqlite open helper `_sqlite_connection(..., ensure_parent=False)` ignores `ensure_parent` and always mkdir parent → contradiction
- `_sqlite_mode_enabled()` exists but unused; backend selection uses `bq is None` pattern → obsolete/duplication

### Decision: Canonical Run Artifact Envelope (WJ-R3)

- context: multiple artifacts share same envelope-like fields but not enforced
- choice: introduce one canonical envelope schema (dict or dataclass) used by all run artifact payload dicts
- alternatives considered:
  - keep ad-hoc dicts per artifact (rejected: drift repeats)
  - enforce via external schema tool only (rejected: need runtime-level SSOT too)
- impact:
  - worker payload builders become “artifact-specific payload dict” + “envelope merge”

**Canonical envelope keys (required for all worker-built run artifacts persisted to store):**
- `run_id: str`
- `created_at: str` (ISO 8601, timezone-aware)
- `status: str` (when artifact represents terminal run status; optional otherwise but must be consistent per artifact category)
- `schema_version: str` (single canonical key; see next decision)
- `snapshot_complete: bool` (when artifact represents “snapshot-of-run” semantics; required for those artifacts)
- `degradation_reason: str` (required if snapshot incomplete or persistence degraded; default empty string or `"none"`; SSOT)
- `replay_context: dict[str, Any]` (required for artifacts that can be replayed/audited; keep stable shape)

### Decision: Schema Version Key Normalization (WJ-R1/WJ-R3)

- context: schema versions currently stamped with mixed key names (`*_schema_version`, ad-hoc string keys)
- choice: normalize to one canonical key name inside envelope: `schema_version`
- alternatives considered:
  - keep per-artifact schema key names (rejected: prevents generic validators)
  - use both keys forever (rejected: duplication)
- impact:
  - backward compatibility: during migration, allow reading both old and new keys; write new key only after cutover

Compatibility rule:
- for a bounded migration window, payload builders MAY include both:
  - `schema_version`
  - legacy key (ex: `mapping_suggestions_schema_version`)
- after deprecation window, remove legacy key write, keep tolerant reader only if needed for historic artifacts.

### Decision: Canonical JSON Encoding Path (WJ-R1)

- context: encoding drift (raw `json.dumps` vs `encode_json_object`, mixed stable ordering expectations)
- choice: all worker-built payloads must use SSOT encoder `encode_json_object(...)` (or a new wrapper with explicit invariants)
- alternatives considered:
  - keep `json.dumps` and rely on `sort_keys=True` ad hoc (rejected: repeats drift and forgetfulness)
- impact:
  - enforce stable ordering + JSON safety rules from one helper

Encoding invariants (must be documented in helper docstring and tested):
- stable key ordering (deterministic bytes for same payload)
- `ensure_ascii=False`
- reject non-JSON-serializable objects early with clear error (or coerce via SSOT `json_safe` only)

### Decision: Canonical Fingerprint Helper + Migration (WJ-R2)

- context: two hash helpers exist; different canonicalization produces different hashes
- choice: use one SSOT fingerprint function for all run artifact identity hashing (prefer existing `stable_sha256_fingerprint(...)` if already canonical)
- alternatives considered:
  - keep both and “use whichever” (rejected: drift)
  - switch all to local `_stable_sha256_json` (rejected: duplicates SSOT)
- impact:
  - if canonicalization changes hash bytes, define migration:
    - compute both old + new for one release window and store both (if contract supports), OR
    - keep old hash algorithm but route through SSOT helper that reproduces old behavior

### Decision: Canonical Persistence Result Contract (BQ-R1)

- context: `update_run_*` return signatures diverge; caller cannot enforce invariants uniformly
- choice: all `bq_store.update_run_*` and `append_event` return a shared `PersistenceResult` shape:
  - `{ "status": "persisted" | "degraded" | "bundle_only_degraded", "reason": "<reason-code>" }`
- alternatives considered:
  - keep current mix of `None` and dict (rejected: symmetry break)
  - raise exceptions for all non-persist cases (rejected: worker needs graceful degrade for legacy schema)
- impact:
  - callsites updated to record result and emit warning events consistently

Reason-code SSOT (examples; final list must be closed in Wave 2):
- `none`
- `run_not_found`
- `missing_column:<column_name>`
- `sqlite_open_transient_failure`
- `sqlite_malformed_rotated`
- `bq_query_failed`

### Decision: Backend Selection SSOT (BQ-R2)

- context: backend mode inferred via `bq is None` but also has unused `_sqlite_mode_enabled()` and env knobs
- choice: backend mode must be decided in one place and passed explicitly; within `bq_store`, backend selection is:
  - primary: `bq is None` means local sqlite mode
  - secondary: env/runtime resolver decides whether caller passes `bq` or `None` (outside `bq_store`)
- alternatives considered:
  - make `bq_store` read env to decide mode (rejected: hidden global behavior)
- impact:
  - delete `_sqlite_mode_enabled()` or repurpose into a single exported helper if callsites need it

### Decision: sqlite connection API correctness (BQ-R3)

- context: `ensure_parent` parameter ignored; contradicts signature
- choice: remove `ensure_parent` parameter OR implement it correctly (do not mkdir unless true)
- alternatives considered:
  - keep param and ignore (rejected: misleading contract)
- impact:
  - ensure all callsites still get parent-dir creation as needed, explicitly

### Decision: Registry for pipeline run JSON field names + schema evolution policy (X-R1)

- context: stringly-typed field names + ad-hoc missing-column fallbacks repeated
- choice:
  - create a single registry of allowed JSON field names used in `pipeline_runs`
  - create a single schema evolution policy mapping:
    - field → “on missing column” behavior: `degrade`, `skip`, `legacy_fallback`, `raise`
- alternatives considered:
  - leave as is and rely on review (rejected: repeats errors)
- impact:
  - all update functions route through one helper using registry + policy

## Invariants

- No behavior regress: pipeline must still run in BigQuery mode and sqlite mode.
- Artifact payload meaning must remain same; only normalization/encoding/keys may change with explicit compatibility rules.
- Artifact timestamps: `created_at` remains ISO 8601 and timezone-aware; never naive datetimes.
- Event ordering invariant: persistence-time timestamp used for ordering (already intent in `append_event`); must remain true.
- Missing-column compatibility invariant: live BigQuery schema missing newer columns must not crash run; must degrade with explicit reason and visible warning event.
- Worker must never leak service account key or secrets into sqlite artifacts (already sanitized intent in settings snapshot).

## Acceptance Criteria

- WJ-R1: all run artifact payload builders in `src/fitcv_cp/worker_job.py` use same SSOT encoder; no direct `json.dumps` used for persisted run artifacts (except explicitly documented compatibility dual-write window).
- WJ-R2: only one fingerprint implementation used; local `_stable_sha256_json` removed or replaced by SSOT call; unit tests prove stable output.
- WJ-R3: artifact envelope fields present and consistent; schema-version stamping normalized; any legacy keys handled per compatibility policy.
- BQ-R1: all `update_run_*` return `PersistenceResult`; no mix of `None` return for updates.
- BQ-R2: `_sqlite_mode_enabled()` removed or made SSOT (used); backend decision consistent; no hidden env-based switching inside `bq_store`.
- BQ-R3: `_sqlite_connection` signature matches behavior (no ignored params); tests cover parent-dir behavior.
- X-R1: registry exists; `update_run_*` field names validated against registry; missing-column policy centralized.

## Non-Goals

- No BigQuery schema migration in this change (only code compatibility behavior).
- No new external dependencies (no pydantic adoption, no new storage layer).
- No large re-architecture of pipeline stages; only artifact contract + persistence symmetry.
- No changes to unrelated modules outside `fitcv_cp` unless required for SSOT helper placement.

## Risks and Mitigations

- Risk: payload key rename breaks consumers.
  - Mitigation: migration window dual-key write; tolerant readers; golden tests; staged rollout behind config flag if needed.
- Risk: fingerprint change breaks reuse/dedupe.
  - Mitigation: preserve old algorithm via SSOT helper OR dual-hash recording for one window; document deprecation.
- Risk: return-contract change breaks callers.
  - Mitigation: temporary adapter helpers or overload period; update all callsites in one bounded PR; add mypy/typing checks if available.
- Risk: sqlite recovery behavior changes cause silent data loss.
  - Mitigation: tests for rotate naming; explicit logging assertions; no change to rotate gating unless spec says.

## Validation Plan

- proof target: all worker persisted artifacts use SSOT encoder
  - method: unit tests + static grep assertion in tests
  - evidence: test output shows no direct `json.dumps` in artifact builder paths; payload bytes deterministic
- proof target: fingerprint SSOT and stability
  - method: unit tests for canonical payload dict → expected hash (golden)
  - evidence: test file asserts stable hash across runs/platforms
- proof target: persistence result symmetry
  - method: unit tests with `bq=None` (sqlite) and mocked BigQuery client that raises missing-column errors
  - evidence: `PersistenceResult.status/reason` matches policy table for each update function
- proof target: schema evolution policy SSOT applied
  - method: unit test for policy mapping; update helper consults registry; invalid field names fail fast
  - evidence: tests assert invalid field rejected; missing-column triggers correct degrade path
- proof target: invariants preserved (no secret leaks, timestamps timezone-aware)
  - method: unit tests inspect produced payloads; ensure no `service_account_key` in sqlite mode settings artifacts
  - evidence: tests assert keys absent and datetime strings parse as timezone-aware

## Completion Criteria

- All Key Deliverables done and validated by tests.
- All tasks in implementation plan derived from this spec are `completed` or `dropped`.
- Repo validators pass for touched surfaces:
  - `.\.venv\Scripts\python.exe scripts/validate_repo_contracts.py --fast`
  - plus any test command chosen in implementation plan (pytest or repo standard).

