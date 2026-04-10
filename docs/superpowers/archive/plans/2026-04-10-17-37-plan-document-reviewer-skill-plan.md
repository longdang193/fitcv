---
feature_type: add
feature_name: none
status: draft
summary: "Add a plan-document-reviewer skill that reviews specs and implementation plans for execution risk before work begins."
invariants:
  - "the skill must review plans/specs with findings-first output instead of silently rewriting them"
  - "the skill must stay focused on execution risk, scope drift, validation strength, and source-of-truth alignment"
  - "the skill should be strong for major or cross-cutting work without becoming required ceremony for tiny tasks"
---

# Plan Document Reviewer Skill Plan

## Spec Anchor

- Spec: [2026-04-10-17-36-plan-document-reviewer-skill-spec.md](C:/Users/HOANG%20PHI%20LONG%20DANG/repos/JOB-PROJECT/docs/superpowers/archive/specs/2026-04-10-17-36-plan-document-reviewer-skill-spec.md)

## Scope

Add a new repo-local skill under `.agents/skills/plan-document-reviewer/` that reviews specs and implementation plans before execution, with findings-first output focused on execution risk, plan drift, validation gaps, and generic-vs-project leakage.

## Affected Docs

- feature_yaml: `none`
- feature_history: `none`
- feature_docs: `none`
- cross_cutting_docs:
  - `.agents/skills/plan-document-reviewer/SKILL.md`
  - `.agents/skills/plan-document-reviewer/`
  - `docs/operating_system/repo-governance.md`
  - `README.md`
- readme: `README.md`
- generated: `none`

## Workstreams

### 1. Create The Skill Skeleton

Target:

- `.agents/skills/plan-document-reviewer/SKILL.md`

Changes:

- Add frontmatter with a discovery-oriented description starting with `Use when...`
- Define the skill’s purpose clearly:
  - review spec/plan quality before execution
  - return findings first
  - focus on risk, not style

Goal:

- make the skill discoverable and narrowly scoped

### 2. Define The Review Workflow

Target:

- `.agents/skills/plan-document-reviewer/SKILL.md`

Changes:

- Add a compact review process for one document or a spec+plan pair:
  - read the target doc(s)
  - identify claimed scope, validation, and doc targets
  - compare for execution risk and drift risk
  - return findings first
- Make the workflow explicitly different from plan writing and code review.

Goal:

- teach a repeatable review behavior instead of a vague “look it over” instruction

### 3. Add The Review Checklist

Target:

- `.agents/skills/plan-document-reviewer/SKILL.md`

Changes:

- Add a checklist covering:
  - scope clarity
  - execution order
  - missing prerequisites
  - validation quality
  - doc/source-of-truth targeting
  - generated vs canonical confusion
  - rollout/merge risk
  - generic-vs-project leakage
  - completion-readiness quality

Goal:

- make the review sharp enough to catch the specific planning problems currently found too late

### 4. Define The Output Format

Target:

- `.agents/skills/plan-document-reviewer/SKILL.md`

Changes:

- Require a findings-first output structure:
  - findings by severity
  - open questions/assumptions
  - short readiness summary
- State that “no findings” is allowed, but residual risk or testing thin spots should still be mentioned.

Goal:

- align plan review with the repo’s code-review mindset

### 5. Position The Skill In The Workflow

Targets:

- `.agents/skills/plan-document-reviewer/SKILL.md`
- optionally `README.md`
- optionally `docs/operating_system/repo-governance.md`

Changes:

- Document where this skill belongs:
  - after spec/plan drafting
  - before execution-heavy work
  - especially for cross-cutting, starter-sync, handoff-heavy, or high-risk work
- Keep this lightweight; avoid making it mandatory for every small task.

Goal:

- improve adoption without adding process noise

### 6. Validate Against Real Repo Documents

Targets:

- the new skill plus a couple of existing archived docs used as pressure tests

Suggested pressure tests:

- one cross-cutting starter sync spec/plan pair
- one implementation-heavy plan from recent FitCV work

Changes:

- run the skill mentally or operationally against representative docs
- confirm it would catch:
  - vague validation
  - scope/file-map mismatch
  - genericity leakage
  - hidden rollout risk
- tighten wording if the skill is too abstract or too stylistic

Goal:

- make sure the skill is practically useful before treating it as canonical

## Execution Order

1. Create `.agents/skills/plan-document-reviewer/`.
2. Draft `SKILL.md` with frontmatter and overview.
3. Add the review workflow.
4. Add the checklist and findings-first output model.
5. Add positioning guidance for when to use the skill and when not to.
6. Review whether `README.md` or `repo-governance.md` needs a small mention.
7. Pressure-test the skill against existing archived spec/plan documents.
8. Refine the skill wording based on those pressure tests.
9. Review the final diff for concision and discoverability.

## Validation

### Skill Content Validation

- Confirm the description helps future discovery and starts with `Use when...`
- Confirm the skill clearly differentiates itself from:
  - `brainstorming`
  - plan writing
  - `executing-plans`
  - code review
- Confirm the output model is findings-first.
- Confirm the checklist covers validation, scope, doc targets, and genericity.

### Practical Validation

- Apply the skill to at least two existing archived docs.
- Confirm it would have produced useful findings on realistic repo work.
- Confirm it does not devolve into style commentary or plan rewriting.

### Scope Validation

- Confirm no generated files need refresh.
- Confirm no new governance burden is introduced for tiny tasks.
- Confirm the skill stays concise enough to load comfortably.

## Risks And Mitigations

### Risk: The skill becomes a second plan writer

- Mitigation: keep it findings-first and explicitly separate from rewriting or re-planning.

### Risk: The skill becomes style-policing

- Mitigation: anchor every checklist item to execution risk, drift risk, or verification strength.

### Risk: The skill adds too much process overhead

- Mitigation: position it as high-value for major, cross-cutting, or handoff-heavy work rather than universal ceremony.

### Risk: The skill is too abstract to help

- Mitigation: pressure-test it against real archived specs/plans and tighten weak sections before rollout.

## Done Criteria

- `.agents/skills/plan-document-reviewer/SKILL.md` exists and is discoverable.
- The skill teaches a findings-first review workflow for specs and plans.
- The checklist covers the key risk areas: scope, validation, doc targeting, drift, rollout risk, and genericity.
- The skill is pressure-tested against real repo planning docs.
- Any README/governance mention added is brief and non-bureaucratic.
