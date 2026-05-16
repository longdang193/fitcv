## 1. Current situation

Settings surface includes runtime knobs, policy toggles, and metadata in same flow. Recent thread analysis identified confusion around CV section toggles (for example Certifications visibility intent versus effective rendering based on eligible evidence). User asked whether Settings IA should be redesigned with clearer grouping and workflow-stage filtering. Existing constraints: preserve current contracts, keep behavior explainable, keep changes incremental, and avoid non-feature scope expansion.

## 2. Core problem

Settings page mixes different decision types without clear applicability context, causing unclear mental model and error-prone interpretation of effects.

Key evidence from thread context:
- Users can read a setting as enabled but still not see expected output due to eligibility/stage conditions.
- Current organization does not make stage/state applicability explicit.
- Metadata-only and runtime-affecting keys are not clearly separated in user-facing flow.

## 3. Root causes

- Single-axis organization: settings grouped mostly by list structure, not by decision intent and application timing.
- Missing applicability signaling: page does not clearly state where and when each setting is consumed.
- Contract opacity: visibility intent, data eligibility, and runtime stage gating are not presented as separate concepts.
- Mixed edit semantics: low-risk toggles and high-risk tuning controls appear similarly editable.

## 4. Options analysis

### Option A: Keep current structure and add helper text only

**Description:** Retain existing sections; improve labels/tooltips/descriptions where confusion appears.

**Benefits:** Lowest disruption and fastest delivery.

**Trade-offs:** Information architecture remains mixed; ambiguity reduced but not removed.

**Risks:** Recurrent confusion likely persists for stage/state-dependent settings.

**Effort / complexity:** Low.

**Best fit when:** Need immediate patch with minimal UI change and short cycle.

### Option B: Two-axis IA redesign (intent layers + workflow-stage filter)

**Description:** Organize by intent layers (General, Workflow Controls, Advanced Tuning, Governance/Metadata) and add secondary stage filtering with explicit setting badges.

**Benefits:** Resolves ambiguity at root by separating what setting means from when it applies. Supports symmetric/invariant/equivalence framing through explicit dependencies and applicability.

**Trade-offs:** Requires moderate UI/UX restructuring and consistency work across descriptions/badges.

**Risks:** If badges/contracts are inconsistent, clarity gains weaken.

**Effort / complexity:** Medium.

**Best fit when:** Need durable clarity improvement without full platform rewrite.

### Option C: Stage-first IA only

**Description:** Reorganize primarily by pipeline stages; each stage page contains all related settings.

**Benefits:** Strong operational alignment for run-time troubleshooting.

**Trade-offs:** Non-stage concerns (governance/metadata/general toggles) become awkward; cross-stage settings harder to reason about globally.

**Risks:** Over-optimizes for operators; weaker for everyday policy decisions.

**Effort / complexity:** Medium.

**Best fit when:** Primary audience is stage-oriented operations users.

### Comparison summary

Option A is simplest but addresses symptoms, not structure. Option C improves stage visibility but weakly handles non-stage decision surfaces. Option B best balances impact, simplicity, and risk: it directly addresses current ambiguity while staying incremental and compatible with existing contracts.

## 5. Recommendation

Adopt Option B: two-axis IA redesign.

Rationale:
- Separates decision intent from execution applicability, which is core confusion source.
- Supports clearer invariance and equivalence communication by making dependencies and gating explicit.
- Enables incremental rollout: badges/filtering first, then navigation split, then pre-save guardrails and effective-state preview.

## 6. Recommended next steps

1. Confirm IA taxonomy: General, Workflow Controls, Advanced Tuning, Governance/Metadata.
2. Define canonical stage mapping for each existing setting key.
3. Define setting-card contract fields: meaning, effect, applies-when, dependencies, default source, observed-in.
4. Add pre-save validation surface for invariants already enforced by backend.
5. Validate redesigned flow against known confusion cases (for example Certifications visibility intent versus eligibility).

## 7. Assumptions and unresolved questions

Assumptions:
- Existing backend validation and config contracts remain source of truth.
- Redesign scope is UI/IA first, not behavioral policy rewrite.
- Incremental delivery is preferred over big-bang replacement.

Unresolved questions:
- Final audience priority split between operators and general users.
- Exact risk labeling policy for each setting category.
- Whether Governance/Metadata remains fully read-only or allows guarded edits for specific keys.
- Acceptance criteria for “clarity improved” (usability signals not yet defined in thread).
