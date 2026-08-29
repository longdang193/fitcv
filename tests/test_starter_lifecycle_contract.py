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
    assert "Downstream project-owned handoff: Release/Deploy → Observe" in dispatch
    assert "Lifecycle ownership remains in `docs/operating_system/planning/planning-dispatch.md`." in integration
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
    assert "owner approval or `Not approved: <reason>`" in draft
    assert "remaining blockers or `None identified`" in draft
    assert "approved deferrals with owner, rationale, trigger, and approval reference" in draft
    assert "[ ] important behavior and state transitions are settled" not in draft


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
    assert "## Review Context" in reviewer
    assert "frontend verification complete" in verification
    assert "end-to-end journey complete" in verification
    assert "direct backend" in verification


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
