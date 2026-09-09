"""
@meta
type: test
scope: unit
domain: admin_ui
covers:
  - local dev script behavior for the control plane
excludes:
  - shell execution outside test doubles
tags:
  - fast
  - ci-safe
"""

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_windows_local_dev_scripts_exist_and_use_simple_worker() -> None:
    expected_scripts = [
        "start_web.ps1",
        "start_worker.ps1",
        "stop_fitcv.ps1",
    ]

    for script_name in expected_scripts:
        script_path = REPO_ROOT / script_name
        assert script_path.exists(), f"Missing helper script: {script_name}"

    worker_script = (REPO_ROOT / "start_worker.ps1").read_text(encoding="utf-8")
    web_script = (REPO_ROOT / "start_web.ps1").read_text(encoding="utf-8")
    dev_script = (REPO_ROOT / "start_fitcv_dev.ps1").read_text(encoding="utf-8")

    assert ".venv\\Scripts\\python.exe" in web_script
    assert 'FITCV_LOCAL_MODE -eq "1"' in web_script
    assert 'FITCV_CP_INLINE_EXECUTION = "1"' in web_script
    assert '$env:FITCV_LOCAL_MODE = "1"' in dev_script
    assert '$env:FITCV_CP_INLINE_EXECUTION = "1"' in dev_script
    assert "job-project-worker-1" in web_script
    assert "SimpleWorker" in worker_script
    assert "fitcv_cp.queue" in worker_script
    assert ".venv\\Scripts\\python.exe" in worker_script
    assert "job-project-worker-1" in worker_script


def test_frontend_vite_scripts_use_package_entrypoint_without_npm_bin_shim() -> None:
    package = json.loads((REPO_ROOT / "frontend" / "package.json").read_text(encoding="utf-8"))
    vite_entrypoint = "node ./node_modules/vite/bin/vite.js"

    assert package["scripts"]["dev"] == vite_entrypoint
    assert package["scripts"]["build"] == f"{vite_entrypoint} build"
    assert package["scripts"]["preview"] == f"{vite_entrypoint} preview"


"""
@meta
type: test
scope: unit
domain: admin_ui
covers:
  - local dev script behavior for the control plane
excludes:
  - shell execution outside test doubles
tags:
  - fast
  - ci-safe
"""
