---
name: patch-and-pattern-detection-prompt
description: a specific patch is required and you also need a controlled search for
  similar issues.
type: prompt
stage: execution
entry_points:
- next eligible action is a bounded patch and recurrence risk should be checked
- a local fix is required and similar issues may exist across related artifacts
prerequisites:
- in-scope roadmap/workstream/thread/spec/plan context is identified
- concrete failure mode and target patch scope are identified
next_steps:
- implementation-next-action-gate-prompt.md
- thread-closeout-readiness-prompt.md
related_skills:
- systematic-debugging
- executing-plans
- verification-before-completion
required_reads:
- docs/operating_system/prompt_templates/README.md
tags:
- prompt-template
- execution
- change
owner_layer: change
status: active
---

# Patch + Pattern Detection Prompt

## Use When

a specific patch is required and you also need a controlled search for similar issues

## Prerequisites

### Required

- failure mode and root-cause hypothesis are explicit
- bounded patch scope is defined

### Optional

- prior validator outputs
- previous related incidents

## Next Prompts

- `implementation-next-action-gate-prompt.md`
- `thread-closeout-readiness-prompt.md`

## Not For

open-ended refactoring or broad redesign without a concrete failure boundary

```text
Implement this patch and run pattern detection with bounded scope control.

Related skills:
- systematic-debugging (evidence-first root cause and boundary validation)
- executing-plans (bounded implementation and artifact sync)
- verification-before-completion (evidence before closure claims)

Related workflows:
- spec-to-plan-to-execution-workflow.md (primary execution sequence)
- drift-detection-and-reconciliation-workflow.md (fallback when pattern findings indicate broader drift)
- live-run-debugging-workflow.md (when failure source is a live-run lane)

Context:
- roadmap/workstream/thread in scope:
- implementation plan path:
- related detailed spec(s):
- implementation execution map path:
- target issue/failure mode:
- initial patch boundary:

Please:
1. Understand the patch in context:
   - what is broken, why, exact failure mode, and affected components
   - upstream intent linkage (roadmap/spec)
   - downstream impact linkage (implementation/execution/observability)
2. Apply the patch with strict controls:
   - minimal bounded scope
   - no unrelated edits
   - preserve valid behavior
   - keep templates/contracts/metadata alignment
3. Verify completion semantics where applicable:
   - Goal and Key Deliverables remain valid
   - StageResult and other required contracts remain valid
   - observability and traceability are not degraded
4. Detect similar problems (pattern detection):
   - derive failure pattern
   - scan similar files/workflows/specs/plans/stages
   - classify findings as confirmed | likely | risk
5. Decide scope per finding:
   - fix now (safe, low-risk, same pattern)
   - defer as follow-up patch
   - log as known issue
   - do not expand scope uncontrollably
6. Validate:
   - original issue resolved
   - no regressions introduced
   - contract/template consistency preserved
   - downstream dependencies remain valid
7. Return required output:
   - Patch summary (fix, root cause, affected components)
   - Changes applied (files + key modifications)
   - Pattern detection report (finding + classification + recommendation)
   - Scope decision (fixed now vs deferred)
   - Validation results (correctness/consistency/risks)
```

Expected output:
- bounded patch implementation plus structured pattern-detection and scope-decision report

