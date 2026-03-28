# Doc System Lifecycle

## When to Apply

**Apply this rule whenever designing, updating, or auditing project documentation.**

This includes:

- Creating or revising project docs (README, DESIGN, etc.)
- Designing doc structure for a new project
- Adding or modifying features
- Reviewing docs for clarity, completeness, and consistency

---

## Core Principle

> Docs are the project's memory system.
> They must allow a reader (human or AI) to answer: **what exists, what is current, what changed, and why — without reading code.**

---

## The 4-Layer Doc System

Every project should maintain these four layers:

| Layer         | File             | Purpose                       | Rule                                                          |
| ------------- | ---------------- | ----------------------------- | ------------------------------------------------------------- |
| **Overview**  | README.md        | Why + What + Navigation       | Update when goals or major capabilities change               |
| **System**    | DESIGN.md        | Current architecture snapshot | Current state only (no history)                               |
| **Lifecycle** | FEATURES.md      | Feature lifecycle + evolution | Every significant change is tracked; history accumulates here  |
| **Decisions** | /docs/decisions/ | Why decisions were made       | Capture context, alternatives, and consequences               |

> FEATURES.md is the authoritative source for feature lifecycle (ADD/MODIFY/REPLACE types, status transitions, entry fields, and rollout rules). See `operating-system/feature-lifecycle.md`.

---

### Layer 1 — Overview (README)

Must answer in order:

- **Why** — problem, purpose, value
- **What** — what the system does (plain language)
- **How to navigate** — where to find docs

Must NOT:

- Describe code internals
- Duplicate design details
- Become stale

---

### Layer 2 — System (DESIGN)

- Represents **current system only**
- No history, no rationale (belongs to DECISIONS)
- Visual when possible: pipelines, architecture diagrams, data models

> If the system changes → update DESIGN **before or alongside implementation**

---

### Layer 3 — Lifecycle (FEATURES)

- The single source of truth for feature lifecycle and history
- Every significant change gets an entry before work begins
- History accumulates here — do not delete or overwrite entries
- Status transitions are the only state changes; every entry has a clear trail

---

### Layer 4 — Decisions

Store in `/docs/decisions/`.

Each entry:

```yaml
---
date: YYYY-MM-DD-HH-MM
decision:
context:
alternatives:
consequences:
---
```

> If a decision requires explanation → it must be recorded

---

## Artifact Conventions

### When to Create Additional Artifacts

| Situation                                        | Artifact                            | Rule                                 |
| ------------------------------------------------ | ----------------------------------- | ------------------------------------ |
| System goal, architecture, or navigation changes | Overview doc                        | Update existing README               |
| Architecture or pipeline changes                 | Design doc                          | Replace current-state snapshot       |
| Any significant feature or change                | Feature entry in FEATURES.md        | Add entry before work begins         |
| Design decision with rationale                   | Decision record in /docs/decisions/ | Date-stamped, context + consequences |
| Complex feature design                           | Spec in docs/specs/                 | Only for non-trivial features        |
| Multi-step execution                             | Plan in docs/plans/                 | Only if not obvious from code        |
| Schema change                                    | Migration in docs/migrations/       | Required if persistent data changes  |
| Investigation or failure                         | Log in docs/logs/                   | Only for meaningful learnings        |

---

### Artifact Naming

- Specs: `YYYY-MM-DD-HH-MM-<feature>-design.md`
- Plans: `YYYY-MM-DD-HH-MM-<feature>-plan.md`
- Decisions: `YYYY-MM-DD-HH-MM-<decision>.md`
- Migrations: `YYYY-MM-DD-HH-MM-<change>.sql`

---

### Frontmatter for Specs and Plans

Every spec and plan should include:

```yaml
---
feature_type: modify   # add | modify | replace
feature_name: run-input-snapshot-consistency
law: "<1-sentence business goal>"
status: building       # planned | draft | building | rollout | active | deprecated
---
```

---

### Size Constraints

- Feature entry: ≤ 15 lines
- Decision: ≤ 1 page
- Spec: ≤ 2 pages

---

## Optional Docs (Demand-Driven Only)

Optional docs are created **only when needed**.

| Doc           | When to create                |
| ------------- | ----------------------------- |
| API.md        | External interface exists     |
| DATA.md       | Schema is complex or critical |
| EVAL.md       | ML / experiments exist        |
| DEPLOYMENT.md | Setup is non-trivial          |
| USER_GUIDE.md | Non-engineers use the system  |

> Do NOT create optional docs upfront. Create them when:
>
> - an interface stabilizes
> - confusion repeats
> - another system depends on it

---

## Doc Sync Principle

- FEATURES updated **before work begins**
- DESIGN updated **before or with system change**
- DECISIONS updated when reasoning matters
- Docs must never lag behind system state

---

## Cross-Reference Discipline

- FEATURES ↔ SPEC ↔ PLAN ↔ DECISIONS
- README links to DESIGN + FEATURES
- No orphan documents

---

## Anti-Patterns

- README describing code instead of purpose
- DESIGN containing history or rationale
- Feature implemented without FEATURES entry
- Multiple conflicting sources of truth
- Over-documentation (too many unused docs)
- Docs written only after implementation
