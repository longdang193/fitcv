## 1. Current situation

Event timeline for run `01e99594-1e49-485d-abb5-7095121b7d49` shows CV validation failures and repeated `Synonym Proposal Triage Completed` rows. Investigation found CV validation failure was triggered by policy grounding checks (unsupported soft claims), not missing sections. Timeline currently makes expected policy rejection look similar to potential system failure. Timeline also shows repeated triage completion events with identical counts, which adds noise for operators.

## 2. Core problem

Timeline does not clearly separate expected policy outcomes from unexpected failures, and repeated equivalent informational events reduce signal quality.

## 3. Root causes

- Timeline rendering relies heavily on raw event stage/message, without a canonical semantic outcome projection.
- Severity/labeling in timeline does not explicitly classify policy rejection vs system defect conditions.
- Synonym triage refresh is emitted repeatedly across progress snapshots after enrich, and timeline lacks deterministic equivalence-based collapse for repeated identical payloads.
- Equivalent outcomes can appear under stage aliases, but timeline does not normalize them to one canonical event meaning.

## 4. Options analysis

### Option A: Minimal UI Message Patch

**Description:** Keep current event model; only add explicit qualifier text for known validation-failed patterns.

**Benefits:** Fastest path. Low code churn.

**Trade-offs:** Does not solve duplicate-event noise or alias equivalence consistently.

**Risks:** Partial fix can drift and require repeated special-cases.

**Effort / complexity:** Low.

**Best fit when:** Immediate relief needed, short horizon, low tolerance for structural change.

### Option B: Canonical Semantic Outcome Layer + Deterministic Dedup

**Description:** Add event-to-semantic projection, canonical equivalence mapping, symmetric severity policy, and fingerprint-based dedup for repeated informational events.

**Benefits:** Enforces symmetry, invariance, and equivalence in timeline meaning. Reduces noise without losing auditability. Keeps operator interpretation stable across emitter aliases and replay.

**Trade-offs:** Higher upfront design effort than message-only patch.

**Risks:** Requires careful contract definition for semantic projection fields.

**Effort / complexity:** Medium.

**Best fit when:** Timeline is operational decision surface and consistency is required.

### Option C: Suppress Repeated Emission at Source

**Description:** Prevent repeated triage-completed events from being emitted during snapshot cycles.

**Benefits:** Reduces duplication close to source.

**Trade-offs:** Risks coupling emit logic to persistence cadence. Can hide useful audit points if suppression criteria too broad.

**Risks:** Harder to preserve audit semantics while reducing noise.

**Effort / complexity:** Medium.

**Best fit when:** Event stream itself must be compact for downstream consumers beyond timeline UI.

### Comparison summary

Option A is quickest but narrow. Option C can reduce duplication but may compromise event audit clarity. Option B gives strongest long-term consistency: one semantic truth, stable interpretation, deterministic dedup, and equivalent rendering across aliases.

## 5. Recommendation

Recommend Option B.

Rationale: it best satisfies symmetry (consistent treatment of equivalent outcomes), invariance (stable operator meaning under replay/snapshot churn), and equivalence (alias-independent rendering). It also addresses both user concerns directly: expected-vs-bug clarity and repeated triage noise.

## 6. Recommended next steps

1. Define canonical semantic outcome taxonomy for timeline (`expected_rejection`, `unexpected_failure`, `requires_review`, `normal_progress`, `summary`).
2. Define canonical equivalence map from raw stages to semantic event keys.
3. Define deterministic dedup fingerprint contract for repeatable informational events.
4. Add timeline rendering rules to show semantic qualifier and repeat counters.
5. Validate on run `01e99594-1e49-485d-abb5-7095121b7d49` and at least one run with genuine system failure.

## 7. Assumptions and unresolved questions

- Assumption: current timeline remains primary operator surface for diagnosing run outcomes.
- Assumption: preserving raw events for audit is required, even if timeline view is deduplicated.
- Unresolved: exact taxonomy ownership (app layer vs shared event contract module).
- Unresolved: dedup window scope (consecutive-only vs broader time window) for triage events.
- Unresolved: final UX badge vocabulary for policy vs bug states.
