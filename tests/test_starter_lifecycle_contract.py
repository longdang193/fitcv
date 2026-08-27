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
    assert "Downstream project-owned handoff: Release/Deploy → Observe" in dispatch
    assert "Lifecycle ownership remains in `docs/operating_system/planning/planning-dispatch.md`." in integration
    assert "## Delivery Lifecycle" not in integration


def test_specification_templates_keep_boundary_guidance_applicable() -> None:
    draft = normalized("docs/operating_system/templates/draft-specification-template.md")
    detailed = normalized("docs/operating_system/templates/detailed-specification-template.md")

    assert "boundary implication when material" in draft
    assert "## Requirements and Behavioral Contract" in detailed
    assert "| Boundary | Owner or canonical contract | Required evidence |" in detailed
    assert "Include only applicable rows" in detailed
    assert "<frontend, backend, or shared contract>" in detailed
    assert "| frontend | <owner or `Not applicable: <reason>`>" not in detailed


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
