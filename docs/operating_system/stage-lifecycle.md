# Stage Lifecycle

This document defines how stages are used as architectural boundaries.

## Core Principle

Stages are navigation and ownership boundaries.

Features remain the primary lifecycle and contract units.

## What A Stage Is

A stage is a stable architectural boundary with:

- a clear purpose
- clear inputs and outputs
- meaningful transition points
- a relationship to one or more features

Current examples include:

- `normalize`
- `enrich`
- `rule_filter`
- `shortlist`
- `ranking`
- `cv_analysis`
- `cv_generation`

## Stage / Feature Relationship

- one stage can involve many features
- one feature can span multiple stages
- stages explain where work happens
- features explain what capability exists and how it evolves

## When To Use Stage Classification

Use stage classification when the work is:

- pipeline-heavy
- boundary-heavy
- transition-heavy
- cross-feature within one architectural flow

Stage-heavy triage should name:

- affected stages
- affected features
- whether the primary lens is stage, feature, or mixed

## Stage Contracts

When stage-aware docs are in scope, stage contracts live in:

```text
docs/stages/*.yaml
```

They describe:

- stage identity
- purpose
- inputs and outputs
- stage-to-feature relationships

They do not replace feature YAML.
