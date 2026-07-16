"""
@meta
type: test
scope: unit
domain: fitcv_local_storage
covers:
  - atomic bootstrap persistence
  - packaged data-root layout
  - narrow routing overlay validation
excludes:
  - Windows shell folder selection
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from fitcv_cp.local_storage import (
    BootstrapError,
    activate_local_storage,
    load_bootstrap,
    validate_data_root_destination,
    validate_routing_overlay,
    write_bootstrap,
)


_LOCAL_ENV_KEYS = (
    "FITCV_CP_SQLITE_PATH",
    "FITCV_LOCAL_DATA_ROOT",
    "FITCV_LOCAL_ROUTING_OVERLAY_PATH",
    "FITCV_LOCAL_CANDIDATE_PROFILE_PATH",
    "FITCV_LOCAL_ARTIFACTS_PATH",
    "FITCV_LOCAL_EXPORTS_PATH",
    "FITCV_LOCAL_LOGS_PATH",
    "FITCV_LOCAL_BACKUPS_PATH",
    "FITCV_LOCAL_UPLOADS_PATH",
    "FITCV_LOCAL_TEMP_PATH",
)


@pytest.fixture(autouse=True)
def _restore_local_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _LOCAL_ENV_KEYS:
        monkeypatch.setenv(key, os.environ.get(key, ""))


def test_activate_local_storage_creates_expected_layout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    paths = activate_local_storage(app_version="1.2.3")

    assert paths.data_root == tmp_path / "local" / "FitCV" / "data"
    assert paths.sqlite_path == paths.data_root / "fitcv.sqlite3"
    assert paths.routing_overlay_path == paths.data_root / "config" / "local_routing_overlay.yaml"
    assert paths.candidate_profile_path.exists()
    assert paths.routing_overlay_path.read_text(encoding="utf-8") == "version: 1\nproviders: {}\nmodel_routing:\n  parts: {}\n"
    assert json.loads(paths.bootstrap_path.read_text(encoding="utf-8")) == {
        "version": 1,
        "data_root": str(paths.data_root),
        "last_application_version": "1.2.3",
    }
    assert os.environ["FITCV_CP_SQLITE_PATH"] == str(paths.sqlite_path)


def test_write_bootstrap_replace_failure_preserves_previous_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bootstrap_path = tmp_path / "bootstrap.json"
    write_bootstrap(bootstrap_path, tmp_path / "old", "1")
    previous = bootstrap_path.read_bytes()
    monkeypatch.setattr("fitcv_cp.local_storage.os.replace", lambda *_: (_ for _ in ()).throw(OSError("boom")))

    with pytest.raises(OSError, match="boom"):
        write_bootstrap(bootstrap_path, tmp_path / "new", "2")

    assert bootstrap_path.read_bytes() == previous


def test_load_bootstrap_rejects_malformed_json(tmp_path: Path) -> None:
    bootstrap_path = tmp_path / "bootstrap.json"
    bootstrap_path.write_text("{broken", encoding="utf-8")

    with pytest.raises(BootstrapError, match="malformed"):
        load_bootstrap(bootstrap_path)


def test_validate_routing_overlay_rejects_non_routing_keys() -> None:
    with pytest.raises(ValueError, match="unsupported keys"):
        validate_routing_overlay({"version": 1, "data_backend": {}})


def test_validate_data_root_destination_rejects_relative_path() -> None:
    with pytest.raises(ValueError, match="absolute"):
        validate_data_root_destination(Path("relative"))


def test_validate_data_root_destination_rejects_source_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="different"):
        validate_data_root_destination(tmp_path, source_root=tmp_path)


def test_reinstall_reuses_root_without_overwriting_profile(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    first = activate_local_storage(app_version="1")
    first.candidate_profile_path.write_text("user-owned\n", encoding="utf-8")

    second = activate_local_storage(app_version="2")

    assert second.data_root == first.data_root
    assert second.candidate_profile_path.read_text(encoding="utf-8") == "user-owned\n"


def test_explicit_data_root_updates_bootstrap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
    chosen = tmp_path / "chosen"

    paths = activate_local_storage(app_version="1", data_root=chosen)

    assert paths.data_root == chosen
    assert load_bootstrap(paths.bootstrap_path)["data_root"] == str(chosen)


def test_activation_does_not_write_under_bundle_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_root = tmp_path / "bundle"
    (bundle_root / "data").mkdir(parents=True)
    (bundle_root / "data" / "candidate_profile.template.yaml").write_text(
        "name: Candidate\n", encoding="utf-8"
    )
    marker = bundle_root / "read-only-marker.txt"
    marker.write_text("unchanged", encoding="utf-8")
    before = {path.relative_to(bundle_root): path.read_bytes() for path in bundle_root.rglob("*") if path.is_file()}
    monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))

    activate_local_storage(app_version="1", bundle_root=bundle_root)

    after = {path.relative_to(bundle_root): path.read_bytes() for path in bundle_root.rglob("*") if path.is_file()}
    assert after == before
