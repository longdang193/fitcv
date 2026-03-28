# Feature Lifecycle

## When to Apply

**Apply this rule whenever classifying, planning, building, or closing a feature.**

Every significant change to the system must have a lifecycle state.

---

## Core Principle

> A feature does not exist until it has a FEATURES.md entry.
> A feature is not complete until it has a post-execution review.

---

## Feature Type Classification

Apply before classifying any feature. The decision tree:

```text
Does this capability exist in the system?
|
├── NO -> Classification: ADD
|
└── YES -> Does the existing capability need a behavior change?
           |
           ├── YES -> Does the new behavior replace the old entirely?
           |         |
           |         ├── YES -> Classification: REPLACE
           |         └── NO  -> Classification: MODIFY
           |
           └── NO -> Do not create a new feature entry.
                      This is a bug fix or configuration change.
                      Apply the fix and document in the existing entry.
```

---

#### ADD

- New capability that has no existing equivalent
- No backward compatibility concern
- Requires: FEATURES.md entry, spec, plan, rollout tracking

---

#### MODIFY

- Changes behavior of an existing feature
- Backward compatibility must be maintained unless explicitly deprecated
- Requires: FEATURES.md entry updating existing feature, migration plan if schema changes, rollback trigger

---

#### REPLACE

- New capability that makes an existing one obsolete
- Old feature must be marked deprecated with `replaced_by` pointing to the new one
- Requires: FEATURES.md REPLACE entry, deprecation notice in old entry, migration path documented

---

## Status Lifecycle

```text
planned -> draft -> building -> rollout -> active -> deprecated
```

| Status     | Meaning                                | Required Action                          |
| ---------- | -------------------------------------- | ---------------------------------------- |
| planned    | Idea exists; FEATURES.md entry created | Entry added with Law, Decree, Impact     |
| draft      | Spec written; design finalized         | Spec linked in FEATURES.md entry         |
| building   | Implementation started                 | Plan linked; tasks underway              |
| rollout    | Staged release in progress             | Rollout plan active; % tracked in entry  |
| active     | Post-execution review complete         | Lessons recorded; no open items          |
| deprecated | Replaced or removed                    | `replaced_by` field filled; reason noted |

---

## Required Fields Per Entry

Every FEATURES.md entry must contain:

```yaml
Feature: <name>
Version: <semver>
Status: <lifecycle status>

Law: <1-sentence business goal>
Type: ADD | MODIFY | REPLACE

Decree:
  must_reuse:
    - <component that must not change>
  must_not_break:
    - <constraint that must hold>

Impact:
  Data:     <schema or data layer changes>
  Pipeline: <pipeline changes>
  API:      <API contract changes>
  UI:       <UI changes>

Dependencies:
  - <prerequisite feature or component>

Replaces:
  - <if REPLACE: what it replaces>

Rollout:
  - <shadow mode / A/B / full rollout>
  - rollback_trigger: <metric or condition>
  - rollback_method: <how to revert>

Post-Execution Review:
  # filled after status -> active
  Classification accurate: yes | no
  Lessons:
    - <what was learned>
  FEATURES.md updated: yes
```

---

## Triage Fields (Pre-Planning Gate)

Before any spec or plan is written, triage must produce these fields.
Field definitions are in this section; planning-dispatch references them:

```
Feature type: ADD | MODIFY | REPLACE
Reasoning: <why this classification>
Law: <1-sentence business goal>

Decree:
  must_reuse:
    - <component that must not change>
  must_not_break:
    - <constraint that must hold>

Impacted layers: Data | Pipeline | API | UI | None
Migration needed: yes | no
Rollback complexity: low | medium | high
Risk level: low | medium | high
Risk reason: <what makes this risky>
Rollback trigger: <metric or condition>
```

---

## Rollout Rules (MODIFY and REPLACE)

### Before Starting Build

- Define the rollback trigger (metric or condition that signals failure)
- Define the rollback method (config revert, migration rollback, feature flag off)
- Define the monitoring window (how long before rollback window closes)

---

### Rollout Stages

1. **Shadow mode** — new behavior runs in parallel; old output is used
2. **A/B test** — percentage rollout with metrics monitored
3. **Full rollout** — new behavior becomes default
4. **Rollback window closes** — feature considered stable

---

### Rollback Criteria

Trigger rollback when:

- Error rate increases beyond threshold
- Output quality degrades (measurable)
- A specific metric violates defined constraint
- A decree constraint is violated

---

## Post-Execution Review

Filled immediately after status transitions to `active`.

### Purpose

- Validate classification correctness
- Capture lessons while context is fresh
- Update decree constraints if needed
- Improve future feature execution

---

### Format

```yaml
Post-Execution Review:
  Classification accurate: yes | no | partially

  Decree constraints valid:
    must_reuse: still valid | wrong — <reason>
    must_not_break: all held | one violated — <which, why>

  Lessons:
    - <actionable lesson>
    - <what to improve next time>

  Rule updates needed: yes | no
    - <which rule, what changed>

  FEATURES.md updated: yes
```

---

## Deprecation Rules

A feature moves to `deprecated` when:

- A REPLACE feature has reached `active`
- The old feature is no longer used in any pipeline
- All consumers have migrated

---

### Required Fields

```yaml
Status: deprecated
Replaced_by: <new feature name>
Deprecation_reason: <why it was replaced>
Migration_path: <how to migrate>
```

---

## Anti-Patterns

- Creating a feature entry after the feature is already built
- Setting status to `active` without a post-execution review
- MODIFY without defining rollback trigger and method upfront
- REPLACE without marking the old feature as deprecated
- Skipping Law/Decree fields (loses reasoning)
- Treating `planned` as final — update if classification changes
