# Brainstorming Detailed Report

## 1. Current situation

This session reviewed project architecture and implementation patterns across pipeline runtime (`normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`), enrich output handling, and control-plane synonym proposal lifecycle.

Observed context from thread:
- Enrich can emit per-job `mapping_suggestions` plus field suggestions.
- Pipeline aggregates enrich suggestions at run level.
- Control-plane persists mapping snapshots and builds synonym proposals from run summary.
- Synonym-management behavior is settings-driven (propose/triage/apply/promote modes).

Goal of this report: identify bottlenecks and define shared structural principles for stable, scalable behavior.

## 2. Core problem

Core problem is structural scaling pressure and governance complexity: as run size and suggestion volume grow, runtime flow, decision policy flow, and artifact persistence paths risk becoming bottlenecks and drift-prone due to duplicated or fragmented logic.

Key symptoms observed in thread:
- Enrich throughput constrained by global lock plus retry/sleep behavior.
- Mapping/proposal payload volume grows with enrich output.
- Similar logic appears in multiple modules/paths.

## 3. Root causes

- Hot-path work and policy orchestration are mixed across large modules, increasing coupling.
- Snapshot/proposal persistence logic appears in repeated lifecycle paths (checkpoint/partial/final), increasing drift risk.
- Stage/status/reason structures are represented in multiple locations rather than one canonical contract.
- Synonym proposal lifecycle and action-state transitions are split across worker and app surfaces.
- Configuration and policy switches are distributed across multiple config/runtime surfaces.

## 4. Options analysis

### Option A: Contract-first centralization (shared stage/decision/artifact contracts)

**Description:** Introduce canonical shared contracts for stage IDs/order, decision statuses/reason codes, and artifact payload envelopes; route all paths through these contracts.

**Benefits:** Reduces drift, improves symmetry/invariance, and makes debugging and policy reasoning more consistent.

**Trade-offs:** Requires refactor of existing call sites and migration discipline.

**Risks:** Partial adoption can create temporary mixed-contract state.

**Effort / complexity:** Medium.

**Best fit when:** Primary goal is long-term maintainability and deterministic cross-path behavior.

### Option B: Runtime-path optimization first (enrich and payload flow focus)

**Description:** Keep architecture mostly intact but focus on throughput and payload pressure mitigation in enrich and suggestion/proposal flow.

**Benefits:** Faster near-term runtime relief for large runs and suggestion-heavy workloads.

**Trade-offs:** Structural duplication and policy fragmentation remain.

**Risks:** Bottlenecks can shift to governance/debugging paths instead of disappearing.

**Effort / complexity:** Low to medium.

**Best fit when:** Immediate performance pressure is highest and structural refactor must be delayed.

### Option C: Two-lane architecture (online serving lane + offline suggestion governance lane)

**Description:** Keep runtime serving path minimal and deterministic; treat enrich-generated suggestions as async governance input (dedupe/conflict/approval/publish) before becoming active runtime truth.

**Benefits:** Balances latency stability with continuous synonym learning; limits unreviewed expansion in hot path.

**Trade-offs:** Adds governance lane orchestration and publish discipline requirements.

**Risks:** If lane boundaries are unclear, policy outcomes can diverge from runtime expectations.

**Effort / complexity:** Medium to high.

**Best fit when:** Need both scale and policy safety, especially with high suggestion volume and human/auto-review workflows.

### Comparison summary

Option B gives fastest local runtime relief but leaves major structural risks unresolved. Option A improves structural integrity but does not directly impose a serving-versus-governance boundary. Option C best aligns with this project’s observed enrich-generated suggestion dynamics because it combines runtime protection with controlled proposal lifecycle, and can incorporate Option A contracts to enforce consistency.

## 5. Recommendation

Recommend Option C as target architecture, implemented with Option A contract centralization as the governing foundation.

Rationale:
- This directly addresses observed bottleneck shift risk (runtime to governance/data-flow).
- It preserves enrich discovery value while protecting hot-path latency and decision stability.
- It creates a clear boundary for equivalence and invariance checks across stages and policy actions.

## 6. Recommended next steps

1. Define canonical stage/decision/artifact contracts and map current surfaces to them.
2. Define explicit lane boundary: what is runtime truth versus proposal/governance candidate data.
3. Consolidate duplicate synonym proposal builders and transition logic into one canonical module path.
4. Unify snapshot persistence flow into one reusable writer for checkpoint/partial/final paths.
5. Add focused metrics for enrich throughput, suggestion volume, proposal conflicts, and persistence degradation reasons.

## 7. Assumptions and unresolved questions

Assumptions:
- Findings rely on code paths and artifacts reviewed in this thread, including enrich suggestion generation and control-plane proposal flow.
- Current concern is architecture-level scaling and consistency, not only single-function micro-optimization.

Unresolved questions:
- No measured p50/p95 latency baselines were provided in-thread for enrich, proposal generation, or snapshot persistence.
- No explicit target SLO/SLI thresholds were provided for stage latency or proposal throughput.
- No finalized cutover strategy was provided for migrating duplicated logic without temporary behavior divergence.
