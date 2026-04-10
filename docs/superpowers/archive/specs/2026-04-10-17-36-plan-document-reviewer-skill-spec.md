---
feature_type: add
feature_name: none
status: draft
summary: "Add a focused skill for reviewing specs and implementation plans before execution to catch scope drift, weak validation, and document-quality risks early."
invariants:
  - "the skill must review plan/spec quality, not rewrite documents by default"
  - "findings must focus on execution risk, drift risk, validation gaps, and source-of-truth alignment"
  - "the skill should stay lightweight enough to use before major work without becoming mandatory ceremony for tiny tasks"
---

# Plan Document Reviewer Skill Spec

## Triage

Feature type: `ADD`  
Summary: Add a `plan-document-reviewer` skill that reviews specs and plans before execution to catch structural weaknesses and drift risks.  
Reasoning: The repo has strong skills for creating plans, executing plans, and reviewing code, but lacks a dedicated workflow for reviewing plan/spec quality before implementation begins.  
Invariants:
- The skill reviews planning documents; it does not replace `brainstorming`, `writing-plans`, or code review.
- Findings must prioritize real execution risk over style nitpicks.
- The skill must help prevent scope drift, weak verification, missing doc targets, and generic-vs-project leakage in starter/public sync work.
- The skill should be optional for small tasks and strongest for major, cross-cutting, or handoff-heavy work.
Dependencies:
- `.agents/skills/brainstorming/`
- `.agents/skills/planning-dispatch/`
- `.agents/skills/executing-plans/`
- `.agents/skills/requesting-code-review/`
- `docs/operating_system/agent_memory/`
Affected stages:
- `none`
Affected features:
- `none`
Primary lens: `feature`
Affected docs:
  feature_yaml: `none`
  feature_history: `none`
  feature_docs: `none`
  cross_cutting_docs:
    - `.agents/skills/`
    - `docs/operating_system/repo-governance.md`
    - `README.md`
  readme: `README.md`
  generated: `none`
Generated refresh required: `no`
Spec needed: `yes`
Plan needed: `yes`

## Problem

Current workflow has good coverage for:

- designing work (`brainstorming`)
- routing and triage (`planning-dispatch`)
- writing plans
- executing plans
- reviewing code after implementation

But there is no focused step for asking:

- is this spec/plan structurally sound?
- does the file scope match the claimed scope?
- are validation steps strong enough to justify later completion claims?
- are doc targets explicit and source-of-truth aligned?
- is this starter/public sync generic enough?
- is there hidden rollout, merge, or drift risk?

As a result, weak plans can still look “good enough” until execution reveals:

- plan drift
- missing prerequisites
- vague validation
- over-broad or under-scoped file maps
- generated/source confusion
- genericity leaks in cross-repo sync work

## Goal

Create a reusable `plan-document-reviewer` skill that reviews specs and implementation plans in a code-review style and returns findings-first feedback before execution starts.

## Non-Goals

- replacing plan writing
- automatically rewriting the whole plan/spec
- acting as a generic writing-style reviewer
- making review mandatory for every minor task
- reviewing code diffs after implementation

## Proposed Skill Shape

### Name

`plan-document-reviewer`

### Trigger

Use when:

- a spec or implementation plan is about to drive real work
- a plan will be handed to another session or agent
- work is cross-cutting, operational, or starter/public-sync oriented
- the cost of a flawed plan is meaningfully higher than the cost of a short review

### Core principle

Review plans the way code review reviews code:

- prioritize findings
- focus on risk
- be concrete about what can go wrong during execution
- distinguish blocking gaps from optional improvements

## Review Targets

The skill should review both:

- spec documents
- implementation plans

With special attention to:

1. scope clarity
2. execution order
3. missing prerequisites
4. validation quality
5. document/source-of-truth targeting
6. generated vs canonical confusion
7. rollout and merge risk
8. generic-vs-project-specific leakage
9. unnecessary work or hidden coupling

## Review Output Model

The skill should return findings first, ordered by severity, similar to code review.

Recommended structure:

1. Findings
- severity-tagged issues
- exact file references
- explanation of why the issue can hurt execution

2. Open Questions / Assumptions
- only unresolved points that affect safe execution

3. Short Summary
- overall readiness judgment:
  - ready
  - ready with fixes
  - not ready

If there are no findings, the skill should say so explicitly and still mention any residual risk or thin areas.

## Review Checklist

The skill should evaluate at least these questions:

### Spec quality

- does the triage block exist and match the work?
- is the feature classification plausible?
- are affected docs named precisely?
- are invariants strong enough?
- are non-goals clear?
- does the spec accidentally mix design and implementation detail in a confusing way?

### Plan quality

- is the execution order safe and realistic?
- are prerequisites or setup steps missing?
- do validation steps actually prove the desired claims?
- does the scope match the named files?
- are risky follow-up items hidden inside “later” language?
- does the plan assume clean branches, passing tests, or existing config without saying so?

### Cross-cutting / starter sync quality

- does the plan accidentally copy project-specific content into generic layers?
- does it define what must stay generic versus repo-specific?
- does it avoid generated-file churn unless necessary?
- does it protect public/private boundaries?

### Completion-readiness quality

- if executed exactly as written, would verification be strong enough to support final success claims?
- is there an obvious place where memory should probably be updated or dispositioned?

## Integration

The skill should fit alongside existing workflows:

- after `brainstorming` writes a spec and before execution-heavy commitment
- after a plan is written and before `executing-plans`
- before starter syncs, repo-governance changes, or other cross-cutting operating-system work

It should not replace:

- `planning-dispatch` for triage
- plan writing
- code review
- verification-before-completion

## Design Constraints

- Keep the skill concise and operational.
- Prefer checklists and findings patterns over long theory.
- Make it easy to use on one document or a spec+plan pair.
- Teach the reviewer to identify when a plan is too vague to execute safely.
- Encourage memory-aware review when a known failure pattern is relevant.

## Example Use Cases

The skill should work well for:

- reviewing a cross-cutting CI/hook rollout plan
- reviewing a starter sync plan for genericity leaks
- reviewing a large feature plan before handing it to a new session
- reviewing a risky refactor plan before branch creation

## Recommendation

Implement the skill as a focused reviewer workflow under `.agents/skills/plan-document-reviewer/` with findings-first output, a checklist for spec/plan risk, and explicit guidance on starter/public sync genericity.

It should be lightweight enough to use often on meaningful work, but sharp enough to catch the exact class of planning defects currently discovered too late.
