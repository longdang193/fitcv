"""@meta
name: renderer
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.prompts.renderer.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

import hashlib
from string import Template
from typing import Any

from fitcv.prompts.loader import load_prompt_template
from fitcv.prompts.models import RenderedPrompt
from fitcv.prompts.registry import get_prompt_definition


def required_template_variables(template_text: str) -> set[str]:
    required: set[str] = set()
    for match in Template.pattern.finditer(template_text):
        named = match.group("named")
        braced = match.group("braced")
        if named:
            required.add(named)
        elif braced:
            required.add(braced)
    return required


def render_prompt(
    prompt_id: str,
    context: dict[str, Any],
    *,
    replacement_text: str | None = None,
) -> RenderedPrompt:
    definition = get_prompt_definition(prompt_id)
    default_template_text = load_prompt_template(definition.template_path)
    normalized_replacement = (
        replacement_text.replace("\r\n", "\n").replace("\r", "\n")
        if replacement_text is not None
        else None
    )
    if normalized_replacement is not None:
        if not normalized_replacement.strip():
            raise ValueError("replacement_text must not be empty")
        if required_template_variables(normalized_replacement) != required_template_variables(
            default_template_text
        ):
            raise ValueError("replacement_text must use exactly the canonical prompt variables")
    template_text = normalized_replacement or default_template_text
    values = {key: str(value) for key, value in context.items()}
    required_variables = required_template_variables(template_text)
    missing_variables = sorted(
        variable_name
        for variable_name in required_variables
        if variable_name not in values
    )
    if missing_variables:
        raise ValueError(
            "Prompt render missing template variables: "
            + ", ".join(missing_variables)
        )
    rendered_text = Template(template_text).substitute(values)
    return RenderedPrompt(
        prompt_id=definition.prompt_id,
        stage_id=definition.stage_id,
        version=definition.version,
        template_path=definition.template_path,
        text=rendered_text,
        customized=normalized_replacement is not None,
        replacement_sha256=(
            hashlib.sha256(normalized_replacement.encode("utf-8")).hexdigest()
            if normalized_replacement is not None
            else None
        ),
        replacement_char_count=len(normalized_replacement or ""),
    )
