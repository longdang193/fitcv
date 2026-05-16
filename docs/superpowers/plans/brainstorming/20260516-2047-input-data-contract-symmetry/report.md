## 1. Current situation

The trigger UI accepts three input channels: jobs input, candidate profile, and synonym overlay. Each channel supports multiple modes (`path`, `upload`, `paste`, or `default_config`) with different format constraints.

Observed thread facts:
- Jobs input is JSON-oriented across its modes.
- Candidate profile is YAML when sourced from default config path, but JSON-only for upload/paste modes.
- Synonym overlay upload is YAML and normalized through a dedicated parser/merge path.
- Runtime envelope stores normalized snapshots for jobs and candidate as JSON strings.

Objective from thread: choose an optimal design that follows symmetry, invariance, equivalence, and razor principles.

## 2. Core problem

Input contract behavior is mode-dependent rather than semantics-dependent, especially for candidate profile, so representation-equivalent payloads (YAML vs JSON) are not treated equivalently across modes.

Key impact observed in thread:
- User-facing inconsistency and confusion in UI/behavior.
- Increased contract drift risk because parsing rules differ by mode.

## 3. Root causes

1. Parser path fragmentation
- Candidate default mode uses YAML loader, while upload/paste use JSON-only loader.

2. Per-mode validation contract instead of per-artifact validation contract
- Acceptance/rejection depends on selected mode rather than artifact schema.

3. UI labels encode asymmetry
- Candidate actions explicitly say `Upload JSON` / `Paste JSON` while default references YAML path.

4. Uneven channel design
- Synonym overlay has a strong single normalization path, but candidate and jobs are not aligned to same parser strategy pattern.

## 4. Options analysis

### Option A: Keep current contracts (status quo)

**Description:** Preserve existing mode-specific format behavior.

**Benefits:**
- No code churn.
- No migration/test rewrite effort now.

**Trade-offs:**
- Keeps asymmetry and non-equivalence.
- Keeps user confusion for candidate profile mode behavior.

**Risks:**
- Continued drift between UI wording and backend parser behavior.
- Repeated bug reports around format acceptance expectations.

**Effort / complexity:** Low.

**Best fit when:**
- Team prioritizes zero near-term change over contract correctness.

### Option B: Candidate-only symmetry patch

**Description:** Unify candidate profile parser across default/upload/paste so YAML and JSON are both accepted and normalized identically; leave jobs and synonym channel structure mostly unchanged.

**Benefits:**
- Directly addresses reported root issue.
- Lower scope than full cross-channel redesign.

**Trade-offs:**
- Partial symmetry only.
- Channel-level contract patterns remain inconsistent.

**Risks:**
- Future maintenance still split across channels.
- May require later second refactor for full invariance.

**Effort / complexity:** Medium.

**Best fit when:**
- Immediate priority is fixing candidate profile inconsistency with limited scope.

### Option C: Unified per-artifact parser contract across all input channels

**Description:** Define one canonical parse+validate+normalize path per artifact (`jobs`, `candidate`, `synonyms`), then route all modes through those paths.

**Benefits:**
- Strongest symmetry and invariance.
- Representation equivalence enforced by design.
- Clearer user mental model and simpler long-term maintenance.

**Trade-offs:**
- Broadest scope among options.
- Requires coordinated updates in UI wording and tests.

**Risks:**
- Regression risk if not fully verified across all trigger modes.
- Scope creep if implementation plan is not tightly bounded.

**Effort / complexity:** Medium-high.

**Best fit when:**
- Team wants durable contract consistency and to avoid repeat format-contract issues.

### Comparison summary

Option A is simplest now but fails all target principles. Option B fixes current candidate pain with moderate effort but leaves system-wide asymmetry. Option C best matches symmetry, invariance, equivalence, and razor at architecture level by removing duplicated mode-specific parsing logic and converging to per-artifact canonical pipelines.

## 5. Recommendation

Recommend Option C.

Rationale:
- Highest alignment with required principles.
- Reduces duplicated logic and drift vectors.
- Converts format handling from mode-specific behavior to artifact-schema behavior, which is the stable invariant expected by users and downstream runtime.

## 6. Recommended next steps

1. Freeze artifact-level input contracts in a short design note:
- canonical parser/validator/normalizer for `jobs`, `candidate`, `synonyms`.

2. Approve strict boundary for first implementation pass:
- parser unification, trigger path routing updates, UI copy/accept attributes, and tests for all modes.

3. Define verification gates before merge:
- mode-by-mode acceptance matrix, canonical runtime snapshot invariance checks, and regression tests for existing valid inputs.

## 7. Assumptions and unresolved questions

Assumptions:
- Existing downstream pipeline should continue consuming canonical JSON snapshots in runtime envelope for jobs and candidate.
- Synonym overlay remains schema-normalized mapping payload in effective config/runtime metadata.

Unresolved questions:
- Whether jobs channel should accept YAML arrays in addition to JSON, or remain JSON-only by policy.
- Whether synonym channel should add `paste` mode for symmetry with other channels.
- Final error-message contract shape for mixed-format parse failures across all artifacts.
