# Stage Lifecycle

## When to Apply

Apply this rule whenever work is naturally framed by architectural or pipeline boundaries, especially when you need to answer:

- which stage owns this behavior?
- which stages are affected by the change?
- how does this work relate to existing features?

Typical cases:

- pipeline cleanup or redesign
- stage-boundary debugging
- transition-artifact or inspection work
- planning that spans multiple features inside one pipeline slice
- cross-cutting operating-system updates for stage-aware documentation

---

## Core Principle

> Stages are navigation and ownership boundaries.  
> Features remain the primary lifecycle and contract units.

Stages help explain where work lives in the system. They do not replace feature contracts, feature status, or feature rollout tracking.

---

## What a Stage Is

A stage is a recognizable architectural boundary with:

- a clear purpose
- clear inputs and outputs
- stable transition points
- a meaningful relationship to one or more features

Examples in the current pipeline vocabulary:

- normalize
- enrich
- rule_filter
- shortlist
- ranking
- cv_generation

Stages should be few, stable, and architectural.

---

## Relationship Between Stages and Features

- a stage can involve many features
- a feature can span multiple stages
- stages describe boundaries and ownership
- features describe capabilities and lifecycle state

Use stages to answer:

- where in the system does this work happen?
- which boundary is responsible?

Use features to answer:

- what capability exists?
- what is its current state?
- what changed?

---

## When Stage Classification Is Required

Stage classification is required when work is primarily:

- pipeline-oriented
- boundary-oriented
- transition-oriented
- cross-feature within one architectural flow

For stage-heavy work, triage/specs/plans should name:

```text
Affected stages:
  - <stage_id>
Affected features:
  - <feature_id> | none
Primary lens: stage | feature | mixed
```

If no real managed feature is changing yet, `Affected features` may be `none` for a cross-cutting operating-system or design-method change.

---

## Stage Contracts

When a project adopts stage-aware source files, stage contracts belong at:

```text
docs/stages/*.yaml
```

Their purpose is to capture:

- stage identity
- purpose
- boundaries
- inputs / outputs
- stage-to-feature relationships

Rules:

- do not use stage contracts as a replacement for feature YAML
- do not duplicate full feature truth into stage contracts
- stage contracts are architectural guidance, not lifecycle tracking

This rule defines the model first. Project-specific rollout of `docs/stages/*.yaml` can happen later.

---

## Triage and Planning Rules

For stage-aware work:

- identify affected stages before writing the spec or plan
- still identify affected features when they exist
- declare whether the work is stage-oriented, feature-oriented, or mixed
- keep lifecycle decisions anchored on features, not stages

Visibility does not imply authority:

- a stage can be named in docs and triage without becoming the primary lifecycle owner
- a stage-aware spec or plan can still be cross-cutting with `Feature: none`

---

## Anti-Patterns

- using stages as a replacement for features
- treating stage IDs as lifecycle units
- creating a new stage for every small subsystem
- forcing stage classification onto trivial non-architectural work
- duplicating stage definitions across multiple rules instead of centralizing them here
