"""
@meta
# distribution_tier: starter_kit
name: test_runtime_tool_resolution_contract
type: test
scope: unit
domain: docs
covers:
  - Capability and evidence ownership
  - Runtime tool resolution boundaries
  - Starter Kit runtime-policy inputs
tags:
  - fast
  - ci-safe
lifecycle:
  status: active
"""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parent.parent


def read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def normalized(path: str) -> str:
    return " ".join(read(path).split())


def test_runtime_policy_assigns_ownership_and_preserves_evidence() -> None:
    policy = normalized("docs/operating_system/tooling/runtime-tool-resolution.md")

    assert "Project OS owns capability requirements and evidence requirements." in policy
    assert "active executor" in policy
    assert "native or already configured capability" in policy
    assert "Discover a runtime tool only when required capability is unmet" in policy
    assert "one primary provider per capability question" in policy
    assert "does not replace required evidence" in policy
    assert "blocked` or `incomplete`" in policy
    assert "data/trust boundary" in policy
    assert "Do not install, connect, authenticate, or widen data access" in policy
    assert "capability registry" not in policy.lower()


def test_root_and_domain_docs_reference_runtime_policy() -> None:
    root_template_path = "docs/operating_system/templates/agents/root-AGENTS.template.md"
    if not (REPO_ROOT / "repo_config" / "starter-kit-manifest.json").is_file():
        root_template_path = "AGENTS.md"
    root_instructions = read(root_template_path)
    code_tools = read("docs/operating_system/tooling/code-intelligence-tools.md")
    governance = read("docs/operating_system/governance/repo-governance.md")

    assert "## Runtime Capability Resolution" in root_instructions
    assert "runtime-tool-resolution.md" in root_instructions
    assert "runtime-tool-resolution.md" in code_tools
    assert "runtime-tool-resolution.md" in governance
    assert "## Code Intelligence" not in root_instructions


def test_generic_skills_do_not_require_provider_specific_code_guidance() -> None:
    skill_paths = [
        ".agents/skills/skill-brainstorming/SKILL.md",
        ".agents/skills/skill-spec-drafting/SKILL.md",
        ".agents/skills/skill-writing-plans/SKILL.md",
        ".agents/skills/skill-full-stack-integration/SKILL.md",
        ".agents/skills/skill-plan-document-reviewer/SKILL.md",
        ".agents/skills/skill-wayfinding/SKILL.md",
    ]

    for path in skill_paths:
        assert "required_reads:" not in read(path).split("---", 2)[1]


def test_generic_guidance_uses_capabilities_not_optional_provider_names() -> None:
    paths = [
        ".agents/skills/skill-plan-document-reviewer/SKILL.md",
        ".agents/skills/skill-systematic-debugging/SKILL.md",
        ".agents/skills/skill-performance-optimization/SKILL.md",
        ".agents/skills/skill-frontend-component-engineering/SKILL.md",
        ".agents/skills/skill-distinctive-frontend-design/SKILL.md",
        "docs/operating_system/prompt_templates/design-spec-prompt.md",
    ]
    for path in paths:
        content = read(path)
        assert "capability" in content.lower(), path


def test_starter_manifest_omits_private_provider_setup() -> None:
    if not (REPO_ROOT / "repo_config" / "starter-kit-manifest.json").is_file():
        pytest.skip("starter-kit-manifest.json is factory-only")
    manifest = read("repo_config/starter-kit-manifest.json")

    assert "docs/operating_system/procedures/frontend-backend-integration-mcp-setup.md" in manifest
    assert "docs/operating_system/tooling/runtime-tool-resolution.md" in manifest


def test_core_runtime_adapter_maps_are_explicit_not_generic_defaults() -> None:
    policy = normalized("docs/operating_system/tooling/runtime-tool-resolution.md")
    assert "explicit core-runtime bindings" in policy
    assert "not generic provider defaults" in policy
