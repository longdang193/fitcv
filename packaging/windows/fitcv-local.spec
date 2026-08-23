# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules


ROOT = Path(SPECPATH).parents[1]
hiddenimports = collect_submodules("keyring.backends") + [
    "keyring.backends.Windows",
    "tkinter",
    "tkinter.filedialog",
    "tzdata",
]
datas = [
    (str(ROOT / "packaging/windows/.env.yaml"), "."),
    (str(ROOT / "packaging/windows/fitcv.ico"), "."),
    (str(ROOT / "src/fitcv_cp/templates"), "fitcv_cp/templates"),
    (str(ROOT / "src/fitcv/prompts/templates"), "fitcv/prompts/templates"),
    (str(ROOT / "config/policy"), "config/policy"),
    (str(ROOT / "config/runtime/control_plane.yaml"), "config/runtime"),
    (str(ROOT / "config/runtime/pipeline.yaml"), "config/runtime"),
    (str(ROOT / "config/runtime/prompts.yaml"), "config/runtime"),
    (str(ROOT / "config/taxonomy"), "config/taxonomy"),
    (str(ROOT / "data/candidate_profile.template.yaml"), "data"),
    (str(ROOT / "templates"), "templates"),
]

analysis = Analysis(
    [str(ROOT / "src/fitcv_cp/local_app.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[str(ROOT / "packaging/windows/pyi_rth_stdio.py")],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="fitcv-local",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon=str(ROOT / "packaging/windows/fitcv.ico"),
    version=str(ROOT / "packaging/windows/version_info.txt"),
)
bundle = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=True,
    name="fitcv-local",
)
