
# Plan Document Reviewer Prompt Template

Use this template when dispatching a plan document reviewer subagent.

**Purpose:** Verify the plan is complete, aligned with the spec, and executable with clear task decomposition.

**Dispatch after:** The complete plan is written.

```text
Task tool (general-purpose):
 description: "Review plan document"
 prompt: |
 You are a plan document reviewer. Verify this plan is complete and ready for implementation.
 
 
 **Plan to review:** [PLAN_FILE_PATH]
 **Spec for reference:** [SPEC_FILE_PATH]
 **Feature contract:** features/<feature_id>.yaml
 
 ## What to Check
 
 | Category | What to Look For |
 |----------|------------------|
 | **Triage Check** | Triage block (or link to spec triage) is present. If linked, verify spec exists and triage is complete. Missing = hard block. |
 | **Feature YAML Alignment** | Plan references the correct `features/<feature_id>.yaml`. It must state whether the YAML is updated or will be updated before work begins. Missing = advisory. |
 | **Rollout Controls** | For MODIFY and REPLACE: rollback_trigger and rollback_method defined. Missing = hard block. |
 | **Completeness** | No TODOs, placeholders, or missing steps |
 | **Spec Alignment** | Plan covers spec requirements; no major scope drift |
 | **Task Decomposition** | Tasks are small, clear, and actionable |
 | **Buildability** | Engineer can execute without confusion |
 | **Doc-System Compliance** | Plan updates correct layers: code, feature YAML, docs, and regenerates `docs/generated/*` if needed |
 
 ## Calibration
 
 **Hard blocks (must fix):**
 - missing triage
 - missing rollout controls (for MODIFY/REPLACE)
 - plan not tied to a feature YAML
 
 **Advisory (do not block):**
 - feature YAML update not explicitly noted
 - vague steps
 - minor scope creep
 - missing doc or generated updates
 
 Approve only if:
 - triage exists
 - rollout controls exist (when required)
 - plan is executable and aligned
 
 ## Output Format
 
 ## Plan Review
 
 **Status:** Approved | Issues Found
 
 **Triage:** Present | Missing  
 **Feature YAML:** Linked | Not linked  
 **Rollout Controls:** Defined | Missing (if required)
 
 **Issues (if any):**
 - [Task X, Step Y]: [issue] — [why it matters] — [Hard block | Advisory]
 
 **Recommendations:**
 - [improvement suggestions]
```

**Reviewer returns:** Status, Issues, Recommendations
