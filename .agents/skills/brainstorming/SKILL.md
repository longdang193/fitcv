---
name: brainstorming
description: "You MUST use this before any creative work - creating features, building components, adding functionality, or modifying behavior. Explores user intent, requirements and design before implementation. Before writing the spec doc, invokes doc-system-lifecycle for the 5-layer doc system and planning-dispatch for the triage block."
---

# Brainstorming Ideas Into Designs

Help turn ideas into validated designs through structured dialogue.

<HARD-GATE>
Do NOT write code or implement anything before:
1. design is presented
2. user explicitly approves
</HARD-GATE>

---

## Core Principle

> Design → validate → then plan.  
> Do not skip classification or doc placement.

This skill produces **design only**.  
It does NOT produce implementation.

---

## Doc-System Alignment

Before writing any spec or doc, align with the 5-layer system:

```text
code/                       → real truth
docs/stages/*.yaml          → stage contracts (when stage-aware docs are in scope)
docs/features/*.yaml        → feature contract (current state)
docs/features/<feature_id>/ → feature-specific explanation + history
docs/*.md                   → cross-cutting explanation
docs/generated/             → discovery (auto)
README.md                   → overview
```

Rules:

- Specs live under `docs/superpowers/specs/`
- Feature YAML must exist before spec when a managed feature is changing; cross-cutting operating-system work may use `feature_yaml: none`
- The spec must link back to the affected `docs/features/<feature_id>.yaml` when one exists
- Use stage classification when the work is pipeline-heavy, architecture-heavy, or boundary-heavy
- Feature-specific explanation/history belongs under `docs/features/<feature_id>/`
- Cross-cutting explanation belongs under `docs/*.md`

---

## Checklist (Execution Order)

```text
1. **Explore context**

- read code + `docs/features/*.yaml`
- check if feature already exists
- recent commits
- other docs

2. **Ask clarifying questions (one at a time)**

3. **Propose 2–3 approaches**

- include tradeoffs
- give recommendation

4. **Present design (incremental)**

- architecture
- components
- data flow
- constraints / invariants
- confirm with user

5. **Feature and Stage Alignment**

- identify `feature_id`
- identify affected stages when relevant
- decide the primary lens: stage | feature | mixed
- classify: add / modify / replace
- name doc targets:
- feature contract → `docs/features/<feature_id>.yaml`
- feature history → `docs/features/<feature_id>/history.md` or `none`
- feature-specific docs → `docs/features/<feature_id>/<doc>.md` or `none`
- cross-cutting docs → `docs/<doc>.md` or `none`
- README → `README.md` or `none`
- generated discovery → `docs/generated/<file>` or `none`
- confirm:
- new feature → create YAML
- existing → update YAML
- cross-cutting operating-system or method change → `feature_yaml: none` is allowed

6. **Invoke planning-dispatch**

- produce triage block
- confirm routing → writing-plans

7. **Write spec**

- save to `docs/superpowers/specs/YYYY-MM-DD-HH-MM-<topic>-spec.md`
- follow frontmatter rules
- link the spec to the affected `docs/features/<feature_id>.yaml`

8. **Spec review loop**

- review → fix → repeat (max 3)

9. **User approval**

10. **Handoff**

- invoke writing-plans
```

---

## Process Flow (Updated)

```text
Explore context
  ↓
Ask questions
  ↓
Propose approaches
  ↓
Present design
  ↓
User approval
  ↓
Feature and stage alignment
  ↓
planning-dispatch (triage)
  ↓
Write spec
  ↓
Review loop
  ↓
User approval
  ↓
writing-plans
```

---

## Design Rules

- prefer small, well-bounded components
- avoid over-engineering (YAGNI)
- follow existing patterns in repo
- improve locally if needed (not global refactor)

Each unit must answer:

- what it does
- how to use it
- what it depends on

---

## Spec Writing Rules

- spec belongs in `docs/superpowers/specs/`
- YAML = current state
- spec = explanation + design
- spec must name the affected `docs/features/<feature_id>.yaml` when one exists
- stage-heavy specs should also name affected stages and the primary lens
- spec should name any feature-specific docs or cross-cutting docs it expects to be updated

### Required frontmatter

```yaml
---
feature_type: add | modify | replace
feature_name: <feature_id>
status: draft | building
summary: "<1-line goal>"
---
```

Optional:

```yaml
invariants:
  - constraint
```

---

## Anti-Patterns

- writing spec before feature classification
- writing spec without classifying affected stages when the work is clearly boundary-heavy
- writing spec without linking the affected feature YAML when one exists
- assuming `FEATURES.md`
- mixing design + implementation
- skipping YAML alignment
- generating global design docs
