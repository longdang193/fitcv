# Brainstorming Detailed Report

## 1. Current situation

This session reviewed pipeline and control-plane architecture with focus on scale behavior. The run flow is staged (`normalize -> enrich -> rule_filter -> shortlist -> ranking -> cv_analysis -> cv_generation`). Enrich can produce per-job mapping suggestions; pipeline aggregates them into run-level suggestion/proposal artifacts.

Objective for this report: isolate bottlenecks only.

## 2. Core problem

Core problem is bottleneck concentration across runtime, data-flow, policy execution, and persistence paths as run size and suggestion volume increase.

Detailed breakdown:
- Runtime bottleneck:
  Enrich-stage throughput is effectively serialized by global rate-limiting behavior, so wall-clock growth trends toward input size growth.
- Data-flow bottleneck:
  Per-job enrich outputs fan out into run-level suggestion/proposal payloads, so processing and storage pressure increase with both job count and suggestion density.
- Persistence bottleneck:
  Multiple snapshot writes at different lifecycle points increase repeated IO and repeated failure-handling overhead.
- Policy bottleneck:
  Proposal triage/apply/promote branching introduces additional compute and state-transition work as proposal volume grows.
- Maintenance bottleneck:
  Similar logic in multiple paths increases change cost and raises risk of behavior divergence, which then slows optimization and debugging.

## 3. Root causes

- Throughput control model:
  Enrich uses global lock plus retry/sleep pacing to protect external provider limits; this protects stability but constrains parallel throughput.
- Fan-out amplification model:
  Enrich emits per-job suggestion data, then pipeline aggregates at run level, causing higher-order payload growth as runs get larger.
- Lifecycle write duplication:
  Similar snapshot persistence paths appear in checkpoint, partial, and final flows, multiplying persistence and error-handling touchpoints.
- Policy branching expansion:
  Synonym-management modes (propose/triage/apply/promote) add branch combinations that scale operational complexity with proposal volume.
- Structural fragmentation:
  Repeated or split logic across modules (proposal handling, transitions, persistence) increases drift risk and slows safe performance tuning.

## 4. Options analysis

### Option A: Runtime-first throughput optimization

**Description:** Optimize enrich and artifact write path first (rate-limit strategy, payload pressure handling, persistence efficiency).

**Benefits:** Fastest route to immediate runtime relief.

**Trade-offs:** Structural duplication and policy drift risks remain.

**Risks:** Bottleneck may shift to governance/debugging surfaces.

**Effort / complexity:** Low to medium.

**Best fit when:** Immediate latency/throughput pressure is primary concern.

### Option B: Data-flow containment with bounded suggestion lifecycle

**Description:** Introduce stronger bounds on suggestion fan-out and proposal lifecycle before persistence and review surfaces.

**Benefits:** Reduces growth pressure in proposal generation and artifact storage paths.

**Trade-offs:** Requires tighter governance rules and suppression logic discipline.

**Risks:** Over-filtering can reduce useful synonym discovery signal.

**Effort / complexity:** Medium.

**Best fit when:** Suggestion volume growth is main scaling risk.

### Option C: Full two-lane architecture (runtime lane + governance lane)

**Description:** Keep runtime lane minimal and deterministic; process enrich-generated suggestions in separate governance lane before approved publication.

**Benefits:** Prevents governance load from degrading runtime behavior.

**Trade-offs:** Adds orchestration complexity and lane-boundary contracts.

**Risks:** Boundary drift can cause decision mismatch between lanes.

**Effort / complexity:** Medium to high.

**Best fit when:** Need stable runtime performance and controlled synonym evolution at larger scale.

### Comparison summary

Option A is fastest for immediate runtime pressure. Option B better targets data-flow growth. Option C provides broadest bottleneck control by isolating runtime and governance concerns, but requires stronger contract discipline.

## 5. Recommendation

Recommend Option C as target state, with Option A improvements used as immediate stabilization steps.

Rationale: current bottlenecks are cross-domain (runtime, data-flow, policy, persistence). Isolating runtime from governance pressure provides most durable bottleneck control.

## 6. Recommended next steps

1. Establish bottleneck dashboard: enrich latency, proposal volume, persistence degradation counts.
2. Add bounded controls for suggestion/proposal flow before review surfaces.
3. Refactor repeated snapshot persistence into one shared path.
4. Define runtime-versus-governance lane boundaries and enforce in contracts.

## 7. Assumptions and unresolved questions

Assumptions:
- Bottleneck concerns are architecture-level and scale-related.
- Enrich-generated suggestions are material contributors to downstream load.

Unresolved questions:
- No in-thread p50/p95 baselines for enrich, proposal generation, or persistence stages.
- No explicit SLO targets for acceptable stage latency and proposal throughput.
- No quantified current rate of persistence degradation events.
