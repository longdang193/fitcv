import json
import sqlite3
from pathlib import Path

import pytest

from scripts.refresh_fitcv_analytics import refresh_analytics
from tests.test_export_fitcv_analytics_source import _seed_database


def test_refresh_replay_is_idempotent_and_publishes_valid_release(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)

    first = refresh_analytics(database, output_root, source_commit="head")
    second = refresh_analytics(database, output_root, source_commit="head")

    assert first == second
    pointer = json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8"))
    assert pointer["material_metrics_sha256"] == first["material_metrics_sha256"]
    release = output_root / pointer["release"]
    assert json.loads((release / "manifest.json").read_text(encoding="utf-8")) == {
        key: value for key, value in pointer.items() if key != "release"
    }
    with sqlite3.connect(release / "analytics.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM gold_semantic_metric").fetchone()[0] > 0


def test_refresh_failure_preserves_previous_pointer(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    refresh_analytics(database, output_root, source_commit="head")
    before = (output_root / "CURRENT.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="source_hash_mismatch"):
        refresh_analytics(database, output_root, source_commit="head", expected_database_sha256="bad")

    assert (output_root / "CURRENT.json").read_text(encoding="utf-8") == before
