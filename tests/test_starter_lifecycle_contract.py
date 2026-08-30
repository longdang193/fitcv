"""
@meta
# distribution_tier: starter_kit
name: test_starter_lifecycle_contract
type: test
scope: unit
domain: docs
covers:
  - Conditional delivery lifecycle ownership
  - Specification boundary guidance
  - Separate frontend and backend evidence
tags:
  - fast
  - ci-safe
lifecycle:
  status: active
"""

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def normalized(path: str) -> str:
    return " ".join(read(path).split())


def test_planning_dispatch_owns_conditional_lifecycle() -> None:
    dispatch = normalized("docs/operating_system/planning/planning-dispatch.md")
    integration = read("docs/operating_system/tooling/frontend-backend-integration-tools.md")

    assert "## Delivery Lifecycle" in dispatch
    assert "Discovery or research when uncertainty exists" in dispatch
    assert "Prototype and iterate when UX or behavior needs validation" in dispatch
    assert "End-to-end verification applies only to cross-boundary journeys" in dispatch
    assert "Design review when material design judgment is required" in dispatch
    assert "UX or behavior approval when approval is required" in dispatch
    assert "Design Export when an applicable owner-approved UX freeze" in dispatch
    assert "Design Export method selection is explicit" in dispatch
    assert "all applicable post-approval inputs are complete" in dispatch
    assert "Reconcile those impacts during specification drafting before planning" in dispatch
    assert "Affected-scope/spec reconciliation" not in dispatch
    assert "optional roadmap" not in dispatch
    assert "Do not use an arbitrary overlap threshold" in dispatch
    assert "Downstream project-owned handoff: Release/Deploy → Observe" in dispatch
    assert "Lifecycle ownership remains in `docs/operating_system/planning/planning-dispatch.md`." in integration
    assert "planning-dispatch post-approval gates" in integration
    assert "`skill-writing-plans` only when implementation-ready" in integration
    assert "## Delivery Lifecycle" not in integration
    assert "Design Export" not in integration


def test_design_export_completion_requires_bound_method_evidence() -> None:
    dispatch = normalized("docs/operating_system/planning/planning-dispatch.md")

    assert "selected export method provides a durable output identity" in dispatch
    assert "attributable to the current task and requested deliverable" in dispatch
    assert "independent review is applicable under this lifecycle" in dispatch
    assert "PASS must apply to the same task and output identities" in dispatch
    assert "evidence from another task or run" in dispatch
    assert "Workspace presence" in dispatch
    assert "agent prose" in dispatch
    assert "inferred deliverable classification" in dispatch
    assert "producer self-assessment" in dispatch
    assert "incomplete or blocked" in dispatch
    assert "OpenDesign" not in dispatch
    assert "studio_create" not in dispatch
    assert "studio_status" not in dispatch


def test_design_export_evidence_templates_preserve_bound_identity_contract() -> None:
    draft = normalized("docs/operating_system/templates/draft-specification-template.md")
    detailed = normalized("docs/operating_system/templates/detailed-specification-template.md")

    for content in (draft, detailed):
        assert "design export evidence or `Not required: <reason>`" in content
        assert "selected export method" in content
        assert "export task reference" in content
        assert "requested deliverable" in content
        assert "durable output identity" in content
        assert "independent review" in content
        assert "bound to the same task and output identity" in content

    assert "gate state: `complete | incomplete | blocked`" in draft
    assert "gate state: `complete | incomplete | blocked`" not in detailed


def test_detailed_specification_preserves_promoted_design_export_evidence() -> None:
    detailed = normalized("docs/operating_system/templates/detailed-specification-template.md")

    assert "design export evidence or `Not required: <reason>`" in detailed
    assert "gate state: `incomplete | blocked`" not in detailed
    assert "promoted" in detailed


def test_specification_promotion_mapping_preserves_material_draft_evidence() -> None:
    skill = normalized(".agents/skills/skill-spec-drafting/SKILL.md")
    draft = normalized("docs/operating_system/templates/draft-specification-template.md")

    for source, destination in (
        ("verified facts", "Current State and Evidence"),
        ("accepted behavior", "Required Outcomes"),
        ("rejected behavior", "Constraints and Alternatives"),
        ("resolved questions", "Design Decisions"),
        ("approved deferrals", "Design Analysis"),
        ("prototype findings", "Prototype and Validation Evidence"),
    ):
        assert source in skill
        assert destination in skill

    assert "semantic rewrite" in skill
    assert "block `status: active`" in skill
    assert "durable approval evidence" in skill
    assert "Reconcile affected scope and ownership in this specification" in skill
    assert "affected-scope/spec reconciliation" not in skill
    assert "roadmap or workstream reconciliation" not in skill
    assert "Revise only `proposed` or `active` specifications" in skill
    assert "owner approval or `Not approved: <reason>`" in draft
    assert "remaining blockers or `None identified`" in draft
    assert "approved deferrals with owner, rationale, trigger, and approval reference" in draft
    assert "[ ] important behavior and state transitions are settled" not in draft


def test_spec_and_plan_status_ownership_is_explicit() -> None:
    spec = normalized(".agents/skills/skill-spec-drafting/SKILL.md")
    verification = normalized(".agents/skills/skill-verification-before-completion/SKILL.md")
    governance = normalized("docs/operating_system/governance/repo-governance.md")

    assert "Revise only `proposed` or `active` specifications" in spec
    assert "completed` after implementation is verified against that contract" in spec
    assert "marks that specification `completed` after verification proves the implementation" in verification
    assert "at most one owning specification through `parent_spec`" in governance
    assert "one change affects several specifications" not in governance


def test_spec_guidance_has_single_baseline_stage_and_compact_change_summary() -> None:
    skill = read(".agents/skills/skill-spec-drafting/SKILL.md")
    detailed = read("docs/operating_system/templates/detailed-specification-template.md")

    assert skill.count("### 2. Inspect Current State And Baseline") == 1
    assert "### 3. Inspect Current Baseline" not in skill
    assert skill.count("### 6. Resolve Design Decisions") == 1
    assert skill.count("### 7. Define Invariants And Edge Cases") == 1
    assert "### Change Summary" in detailed
    assert "#### Current Baseline" not in detailed
    assert "#### Affected Maintained Contracts" not in detailed
    assert "not a second owner for evidence" in detailed


def test_starter_adoption_uses_atomic_kit() -> None:
    adoption = read("docs/operating_system/adoption/project-adoption-migration-guide.md")

    assert "generated Starter kit as the atomic adoption unit" in adoption
    assert "manual file-by-file copying" in adoption


def test_skill_selector_uses_documented_triggers_without_forced_brainstorming() -> None:
    selector = read(".agents/skills/skill-using-superpowers/SKILL.md")

    assert "documented trigger matches" in selector
    assert "do not invoke a skill" in selector
    assert "About to EnterPlanMode?" not in selector
    assert "Already brainstormed?" not in selector
    assert "\"Let's build X with unresolved options\"" in selector
    assert "\"Let's build X\" → skill-brainstorming first" not in selector


def test_skill_authoring_contract_matches_validator_and_proportional_testing() -> None:
    writing = read(".agents/skills/skill-writing-skills/SKILL.md")

    assert "scripts/validate_agent_metadata_schema.py" in writing
    assert "Only two fields supported" not in writing
    assert "NO DISCIPLINE SKILL WITHOUT A FAILING TEST FIRST" in writing
    assert "Every skill change still needs applicable verification" in writing
    assert "verify before deploying, using proof proportional to the skill" in writing
    assert "Same Iron Law: No skill without failing test first" not in writing


def test_runtime_docs_use_profile_concept_and_document_cli_selector() -> None:
    paths = [
        "README.md",
        "docs/operating_system/procedures/personal-local-worktree-procedure.md",
        "docs/operating_system/procedures/runtime-adapter-procedure.md",
        "docs/operating_system/tooling/runtime-tool-resolution.md",
        "docs/operating_system/templates/agents/root-AGENTS.template.md",
    ]

    for path in paths:
        content = read(path)
        assert "role source" not in content, path
        assert "role provider" not in content, path

    assert "--role <profile>" in read("docs/operating_system/procedures/runtime-adapter-procedure.md")


def test_terminal_historical_rule_and_status_writer_are_explicit() -> None:
    rule = read("docs/operating_system/rules/doc-contracts-rule.md")
    plan_template = read("docs/operating_system/templates/implementation-plan-template.md")

    assert "Historical terminal artifacts (`completed` or `superseded`)" in rule
    assert "returns `verified`; the lead controller then updates plan status" in plan_template


def test_specification_promotion_owners_share_applicable_gate_contract() -> None:
    paths = [
        "docs/operating_system/planning/planning-dispatch.md",
        ".agents/skills/skill-spec-drafting/SKILL.md",
        "docs/operating_system/templates/draft-specification-template.md",
        "docs/operating_system/templates/detailed-specification-template.md",
        "docs/operating_system/prompt_templates/design-spec-prompt.md",
    ]

    for path in paths:
        content = normalized(path).lower()
        assert "applicable" in content, path
        assert "post-approval" in content, path
        assert "promot" in content, path


def test_specification_templates_keep_boundary_guidance_applicable() -> None:
    draft = normalized("docs/operating_system/templates/draft-specification-template.md")
    detailed = normalized("docs/operating_system/templates/detailed-specification-template.md")

    assert "boundary implication when material" in draft
    assert "## Requirements and Behavioral Contract" in detailed
    assert "| Boundary | Owner or canonical contract | Required evidence |" in detailed
    assert "Include only applicable rows" in detailed
    assert "<frontend, backend, or shared contract>" in detailed
    assert "| frontend | <owner or `Not applicable: <reason>`>" not in detailed


def test_frontend_export_boundary_stays_provider_agnostic() -> None:
    frontend = normalized("docs/operating_system/rules/frontend-ui-rule.md")

    assert "Curate generated design exports" in frontend
    assert "surface the conflict for reconciliation" in frontend
    assert "evidence classes" in frontend.lower()
    assert "cannot substitute" in frontend.lower()
    assert "runtime-tool-resolution.md" in frontend
    assert "performance or web-quality claims when required" in frontend
    assert "OpenDesign" not in frontend
    assert "combo-ui" not in frontend


def test_review_and_evidence_language_stays_conditional() -> None:
    requesting = normalized(".agents/skills/skill-requesting-code-review/SKILL.md")
    reviewer = read(".agents/skills/skill-requesting-code-review/code-reviewer.md")
    verification = read(".agents/skills/skill-verification-before-completion/SKILL.md")

    assert "general-purpose" not in requesting
    assert "general-purpose" not in reviewer
    assert "discovered-profile reviewer" in requesting
    assert "each applicable frontend, backend, and E2E evidence class" in requesting
    assert "[SPECIFICATION_OR_APPROVED_SCOPE]" in requesting
    assert "[EVIDENCE_CONTEXT]" in requesting
    assert "APPROVED_BASE" in requesting
    assert "BASE_SHA=$(git rev-parse HEAD~1)" not in requesting
    assert "## Review Context" in reviewer
    assert "**Review verdict:** [PASS | FAIL | BLOCKED]" in reviewer
    assert "Ready to merge?" not in reviewer
    assert "frontend verification complete" in verification
    assert "every applicable evidence class" in verification
    assert "frontend-ui-rule.md" in verification
    assert "end-to-end journey complete" in verification
    assert "direct backend" in verification


def test_active_skill_contracts_use_current_authority_and_lifecycle_terms() -> None:
    authority = read(".agents/skills/skill-using-superpowers/SKILL.md")
    subagent = read(".agents/skills/skill-subagent-driven-development/SKILL.md")
    reviewer_prompt = read(
        ".agents/skills/skill-subagent-driven-development/task-reviewer-prompt.md"
    )
    wayfinding = read(".agents/skills/skill-wayfinding/SKILL.md")
    tdd = read(".agents/skills/skill-test-driven-development/SKILL.md")
    writing = read(".agents/skills/skill-writing-skills/SKILL.md")
    parallel = read(".agents/skills/skill-dispatching-parallel-agents/SKILL.md")

    assert "never override system" in authority
    assert "`r`n`r`n" not in authority
    assert "Global Constraints" not in subagent
    assert "[GLOBAL_CONSTRAINTS]" not in reviewer_prompt
    assert "[BINDING_REQUIREMENTS]" in reviewer_prompt
    assert "planning-dispatch.md" in wayfinding
    assert "Behavior-preserving refactoring" in tdd
    assert "superpowers:" not in writing
    assert "TodoWrite" not in writing
    assert "### Read-only fan-out" in parallel
    assert "### Parallel writers" in parallel


def test_skill_rule_bridges_preserve_canonical_applicability() -> None:
    reviewer_prompt = read(
        ".agents/skills/skill-subagent-driven-development/task-reviewer-prompt.md"
    )
    full_stack = read(".agents/skills/skill-full-stack-integration/SKILL.md")
    planning = read(".agents/skills/skill-writing-plans/SKILL.md")
    selector = read(".agents/skills/skill-using-superpowers/SKILL.md")
    central_config = read(".agents/skills/skill-central-config-layer/SKILL.md")

    assert "Apply `backend-verification-rule` independently of task wording" in reviewer_prompt
    assert "may not remove rule-required evidence" in reviewer_prompt
    assert "optional temporary contract-to-UI mappings" in full_stack
    assert "when one exists" in full_stack
    assert "durable multi-task resume" in planning
    assert "delegated\n  checkpoints" in planning
    assert "even a 1% chance" not in selector
    assert "existing canonical owner first" in central_config


def test_active_subagent_templates_use_supported_profiles() -> None:
    implementer = read(".agents/skills/skill-subagent-driven-development/implementer-prompt.md")
    reviewer = read(".agents/skills/skill-subagent-driven-development/task-reviewer-prompt.md")
    planning = read(".agents/skills/skill-writing-plans/SKILL.md")

    assert "controller-selected profile: <discovered-profile>" in implementer
    assert "controller-selected profile: <discovered-profile>" in reviewer
    assert "### 3. Reconcile Approved Scope With Repository Truth" in planning
    assert "map frontend, backend, and shared-contract owners" in planning


def test_obsolete_spec_reviewer_prompt_has_no_consumer() -> None:
    assert not (REPO_ROOT / ".agents/skills/skill-brainstorming/spec-document-reviewer-prompt.md").exists()
