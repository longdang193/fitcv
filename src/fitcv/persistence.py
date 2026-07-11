"""@meta
name: persistence
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Shared sqlite persistence helpers for fitcv runtime modules.
inputs:
  - Runtime config and environment values
outputs:
  - Normalized sqlite path
lifecycle:
  - status: active
"""

import os


def get_local_sqlite_path() -> str:
    return str(os.environ.get("FITCV_CP_SQLITE_PATH") or "data/fitcv_cp.sqlite3").strip() or "data/fitcv_cp.sqlite3"
