---
layer: change
artifact_type: execution_map
status: proposed
parent_workstream: workstream-bounded-agentic-cv-quality
map_type: implementation_execution
threads:
  - workstream-bounded-agentic-cv-quality.agentic-cv-quality-cross-seam-calibration
specs:
  - docs/superpowers/specs/2026-04-29-agentic-cv-quality-drift-and-depth-patch-spec.md
---

# Agentic CV Quality Drift And Depth Patch Implementation Execution Map

## Scope

Execute the patch-first recovery for:

1. project markdown integrity
2. bounded depth guardrails in agentic generation
3. settings-vs-runtime drift visibility in run detail
4. minimal docs/settings copy clarification

## Waves

### Wave 1 (Immediate): Renderer Correctness

- `src/fitcv/cv_generator.py`
- `tests/test_cv_generator.py`

Outcome:

- projects render context plus bullets (not context-only collapse)

### Wave 2: Agentic Depth Guardrails

- `src/fitcv/agentic_cv_generation.py`
- `tests/test_agentic_cv_generation.py`

Outcome:

- bounded shallow-structure detection and one repair attempt budget for depth

### Wave 3: Drift Surface In Run Detail

- `src/fitcv_cp/app.py`
- `src/fitcv_cp/templates/run_detail.html`
- `tests/test_fitcv_cp/test_app.py`

Outcome:

- run detail shows `aligned`, `drifted`, or `not_applicable` for agentic provider/model provenance

### Wave 4: Docs/Validation

- `docs/configuration.md`
- `docs/observability.md`

Outcome:

- clarify operator settings intent vs setup-managed provider runtime controls

## Verification Path

```powershell
python -m pytest tests/test_cv_generator.py -k render_cv_markdown
python -m pytest tests/test_agentic_cv_generation.py -k "repair or shallow or generation"
python -m pytest tests/test_fitcv_cp/test_app.py -k "run_detail or settings"
python scripts/validate_repo_contracts.py --fast
```

## Execution Order

- execute Wave 1 completely first (already lowest-risk, directly user-visible)
- execute Wave 3 next for drift transparency during further tuning
- execute Wave 2 with bounded tests
- finish with docs and repo checks
