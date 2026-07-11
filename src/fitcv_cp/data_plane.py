"""@meta
name: data_plane
type: module
domain: runtime
ownership: infrastructure
responsibility:
  - Module metadata placeholder for src.fitcv_cp.data_plane.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

from fitcv.config import load_control_plane_config


@dataclass(frozen=True)
class DataPlaneContract:
    runtime_mode: str
    state_backend: str
    artifact_backend: str
    telemetry_backend: str


def resolve_data_plane_contract(config: dict[str, Any] | None = None) -> DataPlaneContract:
    cfg = dict(config or {})
    block = dict(cfg.get("data_plane") or {})
    try:
        load_control_plane_config()
    except Exception:
        pass
    runtime_mode = str(
        os.environ.get("FITCV_RUNTIME_MODE")
        or block.get("runtime_mode")
        or "full"
    ).strip().lower()
    if runtime_mode not in {"full", "local", "degraded"}:
        runtime_mode = "full"
    state_backend = str(
        os.environ.get("FITCV_STATE_BACKEND")
        or block.get("state_backend")
        or "sqlite"
    ).strip().lower() or "sqlite"
    artifact_backend = str(
        os.environ.get("FITCV_ARTIFACT_BACKEND")
        or block.get("artifact_backend")
        or "sqlite_json"
    ).strip().lower() or "sqlite_json"
    telemetry_backend = str(
        os.environ.get("FITCV_TELEMETRY_BACKEND")
        or block.get("telemetry_backend")
        or "otel_json"
    ).strip().lower() or "otel_json"
    return DataPlaneContract(
        runtime_mode=runtime_mode,
        state_backend=state_backend,
        artifact_backend=artifact_backend,
        telemetry_backend=telemetry_backend,
    )


def data_plane_contract_payload(config: dict[str, Any] | None = None) -> dict[str, Any]:
    return asdict(resolve_data_plane_contract(config))
