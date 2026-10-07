import json
import sqlite3
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier, Lock

import pytest

import scripts.refresh_fitcv_analytics as refresh_module
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


def test_refresh_includes_canonical_acceptance_and_optimization_state(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)

    result = refresh_analytics(database, output_root, source_commit="head")
    release = output_root / result["release"]
    analytics = json.loads((release / "analytics.json").read_text(encoding="utf-8"))

    assert analytics["gold"]["gold_acceptance_state"]
    assert analytics["gold"]["gold_optimization_state"]
    assert any(
        row["optimization_promotion"] == "rejected"
        for row in analytics["gold"]["gold_optimization_state"]
    )


def test_refresh_failure_preserves_previous_pointer(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    refresh_analytics(database, output_root, source_commit="head")
    before = (output_root / "CURRENT.json").read_text(encoding="utf-8")

    with pytest.raises(ValueError, match="source_hash_mismatch"):
        refresh_analytics(database, output_root, source_commit="head", expected_database_sha256="bad")

    assert (output_root / "CURRENT.json").read_text(encoding="utf-8") == before


def test_refresh_repairs_invalid_existing_release_before_pointer_swap(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    first = refresh_analytics(database, output_root, source_commit="head")
    release = output_root / first["release"]
    (release / "analytics.sqlite3").unlink()

    repaired = refresh_analytics(database, output_root, source_commit="head")

    assert (output_root / repaired["release"] / "analytics.sqlite3").is_file()
    assert json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8"))["release"] == repaired["release"]


def test_refresh_copy_failure_preserves_current_release(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    first = refresh_analytics(database, output_root, source_commit="head")
    before = json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8"))
    with sqlite3.connect(database) as connection:
        connection.execute("UPDATE run_jobs SET title='Changed job' WHERE run_job_id='job-1'")
        connection.commit()

    original_copytree = refresh_module.shutil.copytree

    def interrupted_copytree(source: Path, destination: Path, *args: object, **kwargs: object) -> Path:
        original_copytree(source, destination, *args, **kwargs)
        raise OSError("injected_copy_failure")

    monkeypatch.setattr(refresh_module.shutil, "copytree", interrupted_copytree)
    with pytest.raises(OSError, match="injected_copy_failure"):
        refresh_analytics(database, output_root, source_commit="head")

    assert json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8")) == before
    assert (output_root / first["release"] / "manifest.json").is_file()


def test_refresh_copy_failure_preserves_release_when_current_uses_rebuilt_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    first = refresh_analytics(database, output_root, source_commit="head")
    before = json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8"))
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE unexported (value TEXT)")
        connection.commit()

    original_copytree = refresh_module.shutil.copytree

    def interrupted_copytree(source: Path, destination: Path, *args: object, **kwargs: object) -> Path:
        original_copytree(source, destination, *args, **kwargs)
        raise OSError("injected_copy_failure")

    monkeypatch.setattr(refresh_module.shutil, "copytree", interrupted_copytree)
    with pytest.raises(OSError, match="injected_copy_failure"):
        refresh_analytics(database, output_root, source_commit="head")

    assert json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8")) == before
    assert (output_root / first["release"] / "manifest.json").is_file()


def test_refresh_rejects_corrupt_release_contents(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    first = refresh_analytics(database, output_root, source_commit="head")
    release = output_root / first["release"]
    (release / "source_bundle.json").write_text("{}\n", encoding="utf-8")
    with sqlite3.connect(release / "analytics.sqlite3") as connection:
        connection.execute("DELETE FROM gold_semantic_metric_rows")
        connection.commit()

    refreshed = refresh_analytics(database, output_root, source_commit="head")

    assert refreshed["release"] != first["release"]
    assert (output_root / refreshed["release"] / "source_bundle.json").is_file()
    assert json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8"))["release"] == refreshed["release"]


def test_refresh_rebuilds_release_when_analytics_json_has_wrong_shape(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    first = refresh_analytics(database, output_root, source_commit="head")
    release = output_root / first["release"]
    (release / "analytics.json").write_text("[]\n", encoding="utf-8")

    refreshed = refresh_analytics(database, output_root, source_commit="head")

    assert refreshed["release"] != first["release"]
    assert isinstance(json.loads((output_root / refreshed["release"] / "analytics.json").read_text(encoding="utf-8")), dict)


def test_refresh_rebuilds_release_when_gold_view_columns_are_corrupt(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    first = refresh_analytics(database, output_root, source_commit="head")
    release = output_root / first["release"]
    with sqlite3.connect(release / "analytics.sqlite3") as connection:
        connection.execute("DROP VIEW gold_semantic_metric")
        connection.execute("CREATE VIEW gold_semantic_metric AS SELECT payload_json FROM gold_semantic_metric_rows")
        connection.commit()

    refreshed = refresh_analytics(database, output_root, source_commit="head")

    assert refreshed["release"] != first["release"]
    with sqlite3.connect(output_root / refreshed["release"] / "analytics.sqlite3") as connection:
        columns = [row[1] for row in connection.execute("PRAGMA table_info(gold_semantic_metric)")]
    assert columns[0] == "metric_id"


def test_refresh_rebuilds_release_when_gold_view_values_are_corrupt(tmp_path: Path) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    first = refresh_analytics(database, output_root, source_commit="head")
    release = output_root / first["release"]
    with sqlite3.connect(release / "analytics.sqlite3") as connection:
        connection.execute("DROP VIEW gold_semantic_metric")
        connection.execute(
            """
            CREATE VIEW gold_semantic_metric AS
            SELECT 'corrupt' AS metric_id,
                   json_extract(payload_json, '$.metric_version') AS metric_version,
                   json_extract(payload_json, '$.cohort_id') AS cohort_id,
                   json_extract(payload_json, '$.cohort_type') AS cohort_type,
                   json_extract(payload_json, '$.dimension_key') AS dimension_key,
                   json_extract(payload_json, '$.numerator') AS numerator,
                   json_extract(payload_json, '$.denominator') AS denominator,
                   json_extract(payload_json, '$.value') AS value,
                   json_extract(payload_json, '$.coverage_status') AS coverage_status,
                   json_extract(payload_json, '$.coverage_numerator') AS coverage_numerator,
                   json_extract(payload_json, '$.coverage_denominator') AS coverage_denominator,
                   json_extract(payload_json, '$.unavailable_reason') AS unavailable_reason,
                   json_extract(payload_json, '$.source_commit') AS source_commit,
                   json_extract(payload_json, '$.input_fingerprint') AS input_fingerprint,
                   json_extract(payload_json, '$.material_digest') AS material_digest,
                   payload_json
            FROM gold_semantic_metric_rows
            """
        )
        connection.commit()

    refreshed = refresh_analytics(database, output_root, source_commit="head")

    assert refreshed["release"] != first["release"]
    with sqlite3.connect(output_root / refreshed["release"] / "analytics.sqlite3") as connection:
        assert connection.execute("SELECT COUNT(*) FROM gold_semantic_metric WHERE metric_id = 'corrupt'").fetchone()[0] == 0


def test_concurrent_refreshes_publish_without_shared_pointer_temp_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "fitcv.sqlite3"
    output_root = tmp_path / "analytics"
    _seed_database(database)
    replace_barrier = Barrier(2)
    replace_lock = Lock()
    original_replace = refresh_module.os.replace

    def synchronized_replace(source: str | Path, destination: str | Path) -> None:
        if Path(source).name.startswith(".CURRENT."):
            replace_barrier.wait(timeout=10)
        with replace_lock:
            original_replace(source, destination)

    monkeypatch.setattr(refresh_module.os, "replace", synchronized_replace)
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(
            executor.map(
                lambda _: refresh_analytics(database, output_root, source_commit="head"),
                range(2),
            )
        )

    assert results[0]["status"] == results[1]["status"] == "ok"
    assert results[0]["database_sha256"] == results[1]["database_sha256"]
    assert results[0]["input_fingerprint"] == results[1]["input_fingerprint"]
    assert results[0]["material_metrics_sha256"] == results[1]["material_metrics_sha256"]
    pointer = json.loads((output_root / "CURRENT.json").read_text(encoding="utf-8"))
    assert pointer["release"] in {result["release"] for result in results}
    assert (output_root / pointer["release"] / "manifest.json").is_file()


def test_refresh_script_supports_direct_help_invocation() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/refresh_fitcv_analytics.py", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--database" in result.stdout
