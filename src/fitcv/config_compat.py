"""@meta
name: config_compat
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Compatibility projections between canonical and legacy config shapes.
inputs:
  - Canonical config dictionaries and compatibility key lists
outputs:
  - Config dictionaries adjusted for legacy bridge behavior
lifecycle:
  - status: active
"""

from typing import Any


def apply_legacy_env_compatibility_projection(cfg: dict[str, Any]) -> dict[str, Any]:
    if "seniority" not in cfg and isinstance(cfg.get("seniority_ladder"), list):
        cfg["seniority"] = {
            "ladder": [str(item) for item in cfg.get("seniority_ladder", []) if str(item).strip()],
            "aliases": {},
        }
    return cfg


def strip_obsolete_env_keys(
    cfg: dict[str, Any],
    *,
    keys_to_strip: list[str],
) -> dict[str, Any]:
    for key in keys_to_strip:
        cfg.pop(key, None)
    return cfg
