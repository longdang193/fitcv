---
name: plan-document-reviewer
description: Use when a spec or implementation plan is about to guide significant work, especially for cross-cutting, handoff-heavy, or starter/public-sync changes where scope drift, weak validation, or genericity leakage would be costly.
---

# Plan Document Reviewer

Review specs and implementation plans before execution the way code review reviews code: findings first, risk first, no style policing.

When the planning problem resembles a known repo-method failure, consult `docs/operating_system/agent_memory/` before concluding the documents are sound.

## When to Use

Use this skill when:

- a spec or plan is about to drive real implementation work
- another session or agent will execute the plan
- the work is cross-cutting, operational, or starter/public-sync related
- a flawed plan would waste significant time or create hidden risk

Do not use it for:

- tiny one-step tasks
- rewriting the whole plan from scratch
- reviewing code diffs after implementation

## Review Process

1. Read the target document or the spec+plan pair.
2. Identify the claimed scope:
   - goal
   - invariants
   - named files
   - validation steps
3. Review for execution risk:
   - what could fail during execution?
   - what is underspecified?
   - what is likely to drift?
4. Return findings first, ordered by severity.
5. Add only the open questions that affect safe execution.
6. End with a short readiness judgment:
   - ready
   - ready with fixes
   - not ready

Use severity tags that make execution risk obvious:

- `P1` blocking execution risk
- `P2` important weakness that should be fixed before major execution
- `P3` smaller improvement or hardening opportunity

## Review Checklist

Check these areas:

- scope clarity
  - does the claimed scope match the named files and workstreams?
  - are likely collateral file changes missing from the file map?
- execution order
  - is the task order safe and realistic?
- prerequisites
  - are required setup steps, assumptions, or dependencies missing?
  - does the plan assume a clean branch, passing baseline, existing remote, or available credentials without saying so?
- validation quality
  - do the proposed checks actually prove the intended completion claims?
- source-of-truth targeting
  - are feature docs, cross-cutting docs, and generated outputs handled correctly?
- generated vs canonical confusion
  - does the plan treat generated files as outputs instead of source?
- rollout and merge risk
  - does the plan hide risky integration, CI, or baseline assumptions?
- genericity leakage
  - for starter/public sync work, does the plan accidentally copy project-specific behavior into generic layers?
- completion readiness
  - if executed exactly as written, would the final verification be trustworthy?

## Output Format

Use this structure:

### Findings

- list issues first, ordered by severity
- explain the concrete execution risk
- cite exact file references when possible

### Open Questions / Assumptions

- include only unresolved points that affect safe execution

### Summary

- say `ready`, `ready with fixes`, or `not ready`
- if there are no findings, say that explicitly and mention any residual thin spots

## Review Standards

- prioritize execution risk over writing style
- do not rewrite the plan unless asked
- do not invent missing scope; call it out instead
- distinguish blocking gaps from optional improvements
- be especially careful with:
  - weak verification
  - missing doc targets
  - hidden prerequisites
  - starter/public genericity leaks
  - generated-output churn without source changes

## Common Findings

- validation is too weak to support later completion claims
- file map does not match the claimed scope
- important prerequisites are assumed but not stated
- generic starter sync would copy project-specific material
- plan says “later” where a blocking decision is actually needed now
- generated outputs are treated like source-of-truth docs

## Integration

Use this skill:

- after spec/plan drafting
- before `executing-plans`
- before handing a plan to another session or subagent
- before high-risk cross-cutting work

This skill complements:

- `brainstorming` for design
- plan writing for document creation
- `executing-plans` for implementation
- code review for post-implementation feedback
