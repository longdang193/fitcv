# Centralized CV Generation Config — Design Spec

**Date:** 2026-03-27
**Author:** Admin Control Plane
**Status:** Draft

---

## Problem

CV-generation behavior is currently configured in a partially split and partially implicit way.

Today:

- some related settings live in shared config files
- some important CV defaults still live directly in code
- the boundary between pipeline orchestration config and CV-generation config is not explicit

Examples of current drift:

- `prompt_version` is stored in general config
- `pipeline.evidence_top_k` affects CV creation indirectly but is not CV-specific
- `cv_generator.py` still defaults `cv_template_path` and `cv_generation_model` in code
- `validator.py` still defaults `required_cv_sections` and `cv_max_pages` in code

This makes CV behavior harder to reason about and easier to change inconsistently.

---

## Goal

Create one explicit configuration boundary for CV generation and CV validation by introducing a dedicated:

- `config/cv.yaml`

This file should become the primary source of truth for settings that control how CVs are generated and validated.

---

## Non-Goals

- Moving general pipeline orchestration settings into `cv.yaml`
- Moving ranking policy into `cv.yaml`
- Redesigning CV prompts or template structure
- Replacing the existing top-level config loader architecture

---

## Design

### Config Boundary

Add a dedicated config file:

- `config/cv.yaml`

This file should own settings that are specifically about:

1. CV generation
2. CV output structure
3. CV validation rules

This keeps CV behavior together and avoids mixing it with unrelated runtime or infrastructure settings.

---

### Settings That Belong in `cv.yaml`

The first centralized CV config should include:

- `cv_generation_model`
- `cv_template_path`
- `required_cv_sections`
- `cv_max_pages`
- `prompt_version`

`prompt_version` should move into `cv.yaml` because in this codebase it is used to track CV-generation prompt behavior rather than enrichment or ranking behavior.

Recommended structure:

- `generation.*`
  - `model`
  - `template_path`
  - `prompt_version`
- `validation.*`
  - `required_sections`
  - `max_pages`

The first implementation may keep the file flat if that is simpler for the current loader, but grouping by `generation` and `validation` is the preferred direction as CV-specific settings grow.

---

### Settings That Should Stay Outside `cv.yaml`

These should remain where they are or be owned by non-CV config:

- `pipeline.evidence_top_k`
  - this is pipeline orchestration and retrieval behavior, not purely CV formatting/generation policy
- ranking weights and thresholds
  - these belong to ranking policy
- GCP / BigQuery / credentials / region settings
  - these belong to environment config
- enrichment settings
  - these belong to enrichment/runtime config

---

### Loader Behavior

The existing config loader should treat `cv.yaml` like another dedicated config layer, similar to other focused config files.

Expected behavior:

- load `cv.yaml` as the default source of truth for CV generation and validation behavior
- merge it into the existing config object in a predictable order
- allow higher-precedence overrides such as `.env.yaml` or admin-managed settings where appropriate
- stop relying on competing hardcoded fallback defaults in CV code for the same settings

The exact merge order can follow the project’s current config-loading conventions, but the core rule should be explicit:

- `cv.yaml` provides CV defaults
- higher-precedence config may override them
- business logic should not silently reintroduce fallback defaults for those same keys

Missing required CV settings should fail through config validation rather than surprising runtime fallback behavior.

---

### Code Expectations

After this change:

- `cv_generator.py` should read CV generation settings from config instead of relying on embedded defaults
- `validator.py` should read CV validation settings from config instead of relying on embedded defaults
- CV-related tests should use one coherent shared config fixture aligned with `cv.yaml`

Path semantics should be consistent with the project’s standard config path convention.
`cv_template_path` should be resolved the same way in runtime code and in tests.

The goal is one source of truth, not multiple competing defaults.

---

### Why This Split Is Better

Using a dedicated `cv.yaml` is better than adding more CV settings into `pipeline.yaml` because:

- CV generation is now its own feature area
- generation/validation rules change for different reasons than orchestration limits
- the file boundary makes ownership clearer
- future CV settings can be added without bloating unrelated config files

---

## Acceptance Criteria

- [ ] A dedicated `config/cv.yaml` file exists for CV generation and validation settings
- [ ] `cv_generation_model`, `cv_template_path`, `required_cv_sections`, `cv_max_pages`, and `prompt_version` are defined in `cv.yaml`
- [ ] CV generation and validation code stop relying on hardcoded defaults for those settings
- [ ] Missing required CV settings fail through config validation rather than silent in-code fallback
- [ ] CV-related tests use shared config fixtures aligned with `cv.yaml`
- [ ] Pipeline orchestration settings such as `pipeline.evidence_top_k` remain outside `cv.yaml`
- [ ] The config boundary between CV behavior and pipeline/runtime behavior becomes clearer and more maintainable
