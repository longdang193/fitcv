# Plan Document Reviewer Prompt Template

Use this template when dispatching a plan document reviewer subagent.

**Purpose:** Verify the plan is complete, matches the spec, and has proper task decomposition.

**Dispatch after:** The complete plan is written.

```
Task tool (general-purpose):
  description: "Review plan document"
  prompt: |
    You are a plan document reviewer. Verify this plan is complete and ready for implementation.

    **Plan to review:** [PLAN_FILE_PATH]
    **Spec for reference:** [SPEC_FILE_PATH]

    ## What to Check

    | Category | What to Look For |
    |----------|------------------|
    | **Triage Check** | Triage block (or link to spec's triage block) is present at top of plan. If linked, verify the spec exists and triage is complete there. Missing = hard block. |
    | **FEATURES.md Update** | Plan notes whether FEATURES.md has been updated with the feature entry or will be updated before work begins. If neither is noted = advisory flag. |
    | **Rollout Controls** | For MODIFY and REPLACE plans: rollback_trigger, rollback_method, and monitoring_window are defined. For ADD plans: these are optional. Missing for MODIFY/REPLACE = hard block. |
    | **Completeness** | TODOs, placeholders, incomplete tasks, missing steps |
    | **Spec Alignment** | Plan covers spec requirements, no major scope creep |
    | **Task Decomposition** | Tasks have clear boundaries, steps are actionable |
    | **Buildability** | Could an engineer follow this plan without getting stuck? |

    ## Calibration

    **Two-tier approval:**
    - **Hard blocks (must fix before approval):** Missing triage block; missing rollout controls for MODIFY/REPLACE plans.
    - **Soft blocks (advisory):** FEATURES.md not noted; TODOs; scope creep; vague steps.

    **Overall:** Approve only when triage is present AND rollout controls are defined (for MODIFY/REPLACE) AND design quality passes.

    ## Output Format

    ## Plan Review

    **Status:** Approved | Issues Found

    **Triage:** Present | Missing
    **Rollout Controls:** Defined | Missing (for MODIFY/REPLACE)
    **FEATURES.md Update:** Noted | Not noted

    **Issues (if any):**
    - [Task X, Step Y]: [specific issue] - [why it matters for implementation] — [Hard block | Advisory]

    **Recommendations (advisory, do not block approval):**
    - [suggestions for improvement]
```

**Reviewer returns:** Status, Issues (if any), Recommendations
