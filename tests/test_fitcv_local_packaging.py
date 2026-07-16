"""
@meta
type: test
scope: contract
domain: fitcv_local_packaging
covers:
  - Windows bundle and installer definitions
  - reproducible build and smoke scripts
excludes:
  - clean-machine installer execution
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_local_entrypoint_targets_packaged_launcher() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert 'fitcv-local = "fitcv_cp.local_app:main"' in pyproject


def test_pyinstaller_spec_is_onedir_and_bundles_required_resources() -> None:
    spec = (ROOT / "packaging/windows/fitcv-local.spec").read_text(encoding="utf-8")

    assert "COLLECT(" in spec
    assert "console=False" in spec
    for required in (
        "packaging/windows/.env.yaml",
        "fitcv_cp/templates",
        "candidate_profile.template.yaml",
        "config",
        "prompts",
        "keyring.backends.Windows",
        "pyi_rth_stdio.py",
        "tkinter",
        "tzdata",
    ):
        assert required in spec


def test_inno_installer_is_per_user_and_preserves_user_data() -> None:
    installer = (ROOT / "packaging/windows/FitCV.iss").read_text(encoding="utf-8")

    assert "PrivilegesRequired=lowest" in installer
    assert "FitCV Local Technical Preview" in installer
    assert "UninstallDelete" not in installer
    assert "fitcv-local.exe" in installer


def test_build_and_smoke_scripts_cover_release_contract() -> None:
    build = (ROOT / "scripts/build_fitcv_local.ps1").read_text(encoding="utf-8")
    smoke = (ROOT / "scripts/smoke_fitcv_local.ps1").read_text(encoding="utf-8")

    assert "PyInstaller" in build
    assert "Get-FileHash" in build
    assert "FITCV_BUILD_ID" in build
    assert "600MB" in build
    for required in (
        "/healthz",
        "/local/onboarding",
        "fitcv_csrf",
        "/local/system/shutdown",
        "second instance",
    ):
        assert required in smoke
