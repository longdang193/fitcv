"""@meta
name: __init__
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.prompts.__init__.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from fitcv.prompts.models import PromptDefinition, RenderedPrompt
from fitcv.prompts.registry import get_prompt_definition
from fitcv.prompts.renderer import render_prompt, required_template_variables

__all__ = [
    "PromptDefinition",
    "RenderedPrompt",
    "get_prompt_definition",
    "required_template_variables",
    "render_prompt",
]
