## 1. Current situation

A live run debugging pass was executed using `config/env.yaml` for run `c62dc5a3-6f80-4a43-94f6-ab0025f6633f`. Runtime execution completed successfully across all stages (`normalize`, `enrich`, `rule_filter`, `shortlist`, `ranking`, `cv_analysis`, `cv_generation`) with final run status `succeeded` and `cvs_generated=4`.

Second-pass artifact audit was requested to retrieve all artifacts and assess potential breakdowns. Retrieved artifacts include run/event payloads, cv-debug payload, and all stage artifacts. The audit objective became quality-policy review rather than runtime failure triage.

Constraints in this thread include: keep single source of truth alignment (`config/env.yaml` direction), avoid inventing details outside available evidence, preserve existing artifact contract stability, and keep recommendations bounded and decision-oriented.

## 2. Core problem

Core problem: acceptance policy is too permissive for weak-match `stretch` jobs, causing low-match profiles to be marked `accepted` instead of being routed to review.

Evidence from retrieved artifacts for run `c62dc5a3-6f80-4a43-94f6-ab0025f6633f`:
- 4/4 generation attempts were accepted.
- 3/4 accepted jobs still had missing required items.
- Maximum missing required count among accepted jobs was 7.

This is a quality-governance breakdown, not a runtime execution breakdown.

## 3. Root causes

1. Acceptance decision logic does not sufficiently gate `stretch` outcomes when required-match deficits are high.
2. `cv_analysis` and downstream acceptance do not enforce a deterministic threshold policy based on required-match metrics in a way that prevented these outcomes in this run.
3. Policy expression appears under-specified at central config level for strict acceptance versus review-required boundaries.

Secondary non-fatal degradations observed in artifacts:
- telemetry export and Langfuse outputs were disabled in this run.
- semantic alignment was disabled; lexical matching dominated evidence scoring.

These degradations reduce observability/semantic robustness but do not explain the acceptance-policy boundary by themselves.

## 4. Options analysis

### Option A: Hard ratio gate at `cv_analysis`

**Description:** Apply deterministic required-match thresholds in `cv_analysis`; block or downgrade jobs before `cv_generation` when required-match ratio is below policy.

**Benefits:**
- early deterministic control
- low runtime overhead
- clear stage boundary

**Trade-offs:**
- coarser gate can over-block borderline jobs
- less flexibility for final-stage contextual checks

**Risks:**
- threshold mis-tuning may reduce useful output volume

**Effort / complexity:** Medium.

**Best fit when:** strict early filtering is preferred over nuanced late-stage acceptance.

### Option B: Dual gate (`cv_analysis` + `cv_generation`) with central policy matrix

**Description:** Compute normalized required-match metrics in `cv_analysis`, then apply final acceptance guard in `cv_generation` using central policy thresholds by fit class.

**Benefits:**
- stronger symmetry/invariance across stages
- deterministic policy with explicit reason codes
- preserves late-stage context while preventing permissive acceptance

**Trade-offs:**
- more coordination across two stages
- requires careful contract-compatible additive fields

**Risks:**
- inconsistent implementation if one stage reads stale/different policy projection

**Effort / complexity:** Medium-high.

**Best fit when:** need strong policy strictness plus staged decision transparency without breaking current artifact contracts.

### Option C: Prompt-only tightening

**Description:** Adjust prompt guidance to encourage stricter acceptance behavior without adding deterministic policy gates.

**Benefits:**
- fastest to try
- minimal code/config surface change

**Trade-offs:**
- non-deterministic behavior
- weak enforceability for governance

**Risks:**
- regressions remain likely; inconsistent outcomes run-to-run

**Effort / complexity:** Low.

**Best fit when:** short-term experimentation only, not policy-grade control.

### Comparison summary

Option C is fastest but least reliable and weakest for governance. Option A is deterministic and simple but may be too blunt and can remove useful late-stage context. Option B provides strongest decision integrity and policy transparency while preserving staged architecture; it best aligns with the stated principles (SSOT, symmetry, invariance, equivalence).

## 5. Recommendation

Recommend Option B: dual-gate acceptance with a central config policy matrix as single source of truth.

Rationale:
- directly addresses observed acceptance-permissiveness in this run
- keeps deterministic policy boundaries with auditable reason codes
- aligns with SSOT and architecture consistency goals already established in this lane
- avoids relying on prompt behavior alone

Policy intent from brainstorming output:
- `accepted` only when required-match policy passes for the fit class
- otherwise route to `review_required` with explicit deterministic reason code
- keep artifact compatibility by adding fields rather than replacing existing contract keys

## 6. Recommended next steps

1. Confirm policy boundary decision for `stretch` class (review-required threshold strategy).
2. Draft bounded implementation update against existing lane plan/spec, centered on Option B.
3. Define additive artifact outputs for policy reason codes and required-match metrics.
4. Re-run live run debugging after implementation and compare acceptance/review split against this baseline run.

## 7. Assumptions and unresolved questions

Assumptions:
- Run artifact set retrieved in this thread is complete for `c62dc5a3-6f80-4a43-94f6-ab0025f6633f`.
- Existing runtime success indicates no infrastructure failure requiring audit-triggered failure remediation in this slice.
- Central config path direction remains `config/env.yaml` as active runtime source.

Unresolved questions:
- Exact threshold values for `stretch` acceptance vs `review_required` were not specified in thread evidence.
- Whether semantic alignment should be enabled as part of this same bounded change is not decided.
- Whether telemetry/Langfuse disabled state is intentional baseline or separate follow-up issue is not determined from available context.
