---
template_id: brainstorming-detailed-report
document_type: report
target_globs:
- docs/superpowers/plans/brainstorming/*/report.md
required_sections:
- Current situation
- Core problem
- Root causes
- Options analysis
- Recommendation
- Recommended next steps
- Assumptions and unresolved questions
distribution_tier: starter_kit
---

# Brainstorming Detailed Report

## 1. Current situation

Current configuration state is split across `config/env.yaml`, `config/env.private.yaml`, and runtime/policy files.  
`config/env.yaml` includes infrastructure keys (`gcp_project`, `bigquery_dataset`, `service_account_key`, `location`) and non-infrastructure keys (retry knobs, thresholds, ladders, statuses).  
Loader behavior treats `config/env.yaml` as legacy-compatible in some paths while control-plane defaults still point to `config/env.yaml`.  
Objective is a central configuration design that enforces single source of truth and satisfies symmetry, invariance, and equivalence.

## 2. Core problem

Configuration ownership is ambiguous and duplicated, so one logical setting can exist in multiple places with unclear precedence and drift risk.

## 3. Root causes

Configuration is not strictly separated by responsibility (infrastructure vs runtime vs policy vs taxonomy).  
Legacy compatibility paths remain active while defaults and documentation are partially migrated.  
No strict duplicate-key ownership gate across config layers.  
No explicit equivalence guard ensuring legacy and canonical inputs resolve to the same effective runtime snapshot.

## 4. Options analysis

### Option A: Keep current dual-file setup with minor cleanup

**Description:** Keep `config/env.yaml` and `config/env.private.yaml`; only update naming/docs and remove obvious duplicates.

**Benefits:** Lowest near-term change cost; minimal disruption.

**Trade-offs:** Leaves legacy behavior and ownership ambiguity in place.

**Risks:** Continued drift and precedence confusion; SSOT remains weak.

**Effort / complexity:** Low.

**Best fit when:** Immediate stability is prioritized over structural correctness.

### Option B: Full central-config refactor with compatibility adapter window

**Description:** Define strict ownership by layer (`runtime/control_plane.yaml`, `runtime/pipeline.yaml`, `policy/*`, `taxonomy/*`, plus dedicated infra file), enforce duplicate-key validation, and keep temporary legacy adapter.

**Benefits:** Strong SSOT; aligns with central-config principle; supports symmetry, invariance, and equivalence checks.

**Trade-offs:** Requires coordinated migration across loader, defaults, scripts, and tests.

**Risks:** Migration breakage if legacy scripts or external callers depend on old paths.

**Effort / complexity:** Medium to high.

**Best fit when:** Long-term correctness and maintainability are primary goals.

### Option C: Big-bang cutover to canonical files with no compatibility

**Description:** Remove legacy paths and private duplicate file immediately; force all callers to canonical files.

**Benefits:** Fast elimination of ambiguity.

**Trade-offs:** High disruption; weak rollback path.

**Risks:** Service/script breakage for any untracked dependency on old paths.

**Effort / complexity:** Medium, with high operational risk.

**Best fit when:** Repository has verified zero legacy consumers and strict change window control.

### Comparison summary

Option A is simplest but does not solve SSOT rigorously.  
Option C is fast but highest risk.  
Option B balances correctness and safety by combining canonical ownership with temporary compatibility, making it strongest against drift while preserving controlled migration.

## 5. Recommendation

Choose Option B.  
It is most aligned with single source of truth and central-config separation by responsibility, while preserving migration safety through a bounded compatibility adapter window.  
This option also best supports:
- symmetry: uniform naming/override rules across config layers
- invariance: same runtime outcomes for same effective values
- equivalence: legacy input maps to same resolved canonical snapshot during transition

## 6. Recommended next steps

1. Approve canonical ownership map: infra, runtime, policy, taxonomy.  
2. Approve canonical precedence contract and legacy-adapter sunset policy.  
3. Validate no required runtime consumer still depends exclusively on `config/env.private.yaml`.  
4. Create implementation spec/plan focused on loader contract, conflict validation, and equivalence tests.

## 7. Assumptions and unresolved questions

Assumptions:
- Existing behavior requiring BigQuery keys remains valid for current backend paths.
- `config/env.private.yaml` is not required by active runtime paths.
- Secret handling should remain environment/secret-manager-first, not plain committed YAML-first.

Unresolved questions:
- Final canonical location and key name for infrastructure-only fields (exact file/key schema not yet approved).
- Whether any external automation outside this repo still passes `config/env.yaml` explicitly.
- Exact deprecation window length for legacy config-path compatibility.
