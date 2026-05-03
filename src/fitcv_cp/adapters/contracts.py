"""
@meta
name: fitcv_cp_adapters_contracts
type: utility
domain: provider_routing
responsibility:
  - Define provider-agnostic LLM and embedding client contracts.
  - Resolve model routing by task part from control-plane config.
inputs:
  - control-plane routing config
outputs:
  - resolved provider/model selection for task parts
lifecycle:
  status: active
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Any


class LLMClient(Protocol):
    def generate(self, *, prompt: str, **kwargs: Any) -> str: ...


class EmbeddingClient(Protocol):
    def embed(self, *, text: str, **kwargs: Any) -> list[float]: ...


@dataclass(frozen=True)
class RoutingSelection:
    part: str
    provider: str
    model: str


def resolve_part_routing(control_plane_cfg: dict[str, Any], part: str) -> RoutingSelection:
    normalized_part = str(part or "").strip()
    if not normalized_part:
        raise ValueError("routing part is required")

    model_routing = dict(control_plane_cfg.get("model_routing") or {})
    parts = dict(model_routing.get("parts") or {})
    row = dict(parts.get(normalized_part) or {})
    provider = str(row.get("provider") or "").strip()
    model = str(row.get("model") or "").strip()
    if not provider or not model:
        raise ValueError(f"Unsupported model routing part: {normalized_part}")

    providers = dict(control_plane_cfg.get("providers") or {})
    if provider not in providers:
        raise ValueError(
            f"Unsupported provider '{provider}' for routing part '{normalized_part}'"
        )

    return RoutingSelection(
        part=normalized_part,
        provider=provider,
        model=model,
    )
