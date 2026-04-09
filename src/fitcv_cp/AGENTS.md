# GENERATED FILE - do not edit directly.
# Source: `agent-core/adapters/codex/src-fitcv_cp-AGENTS.template.md`
# FitCV Control Plane Instructions

This directory owns the admin control plane and worker-facing orchestration.

## Editing Rules

- Keep operator-facing behavior aligned with the underlying artifact contracts.
- Update templates, route behavior, and worker serialization together when a run-inspection contract changes.
- Preserve clear distinctions between private operating workflow and product-facing operator UX.
- Keep agent/publication governance rules in `docs/operating_system/` and `codex/rules/`, not in control-plane UX docs.

