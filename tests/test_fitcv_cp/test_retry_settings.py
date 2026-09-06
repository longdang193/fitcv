import pytest

from fitcv_cp.retry_settings import load_retry_settings


def test_load_retry_settings_reads_packaged_local_system_resource(
    tmp_path,
    monkeypatch,
) -> None:
    from fitcv_cp.settings_store import load_system_settings, patch_system_settings

    monkeypatch.setenv("FITCV_LOCAL_MODE", "1")
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", str(tmp_path / "settings.sqlite3"))
    current = load_system_settings()
    updated = patch_system_settings(
        {
            "maximum_attempts": 4,
            "initial_backoff_seconds": 12,
            "lease_seconds": 120,
            "reconciler_interval_seconds": 15,
            "error_detail_limit": 4096,
        },
        expected_revision=current["revision"],
    )

    settings = load_retry_settings()

    assert settings.maximum_attempts == 4
    assert settings.initial_backoff_seconds == 12
    assert settings.lease_seconds == 120
    assert settings.reconciler_interval_seconds == 15
    assert settings.error_detail_limit == 4096
    assert settings.revision == updated["revision"]


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("maximum_attempts", "bad", 3),
        ("maximum_attempts", 0, 1),
        ("maximum_attempts", 999, 10),
        ("initial_backoff_seconds", -1, 0),
        ("error_detail_limit", 999999, 100000),
    ],
)
def test_load_retry_settings_coerces_and_bounds_values(field, value, expected, monkeypatch) -> None:
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)
    settings = load_retry_settings({"fitcv_cp": {"retry": {field: value}}})
    assert getattr(settings, field) == expected


def test_load_retry_settings_maps_legacy_control_plane_retry() -> None:
    settings = load_retry_settings(
        {
            "fitcv_cp": {
                "retry": {
                    "enabled": True,
                    "max_attempts": 5,
                    "backoff_seconds": [7, 20],
                    "lease_seconds": 900,
                    "reconciler_interval_seconds": 0,
                    "error_details_max_chars": 25000,
                }
            }
        }
    )

    assert settings.maximum_attempts == 5
    assert settings.initial_backoff_seconds == 7
    assert settings.lease_seconds == 900
    assert settings.reconciler_interval_seconds == 30
    assert settings.error_detail_limit == 25000


def test_load_retry_settings_canonical_fields_override_legacy_aliases() -> None:
    settings = load_retry_settings(
        {
            "fitcv_cp": {
                "retry": {
                    "maximum_attempts": 4,
                    "initial_backoff_seconds": 3,
                    "lease_seconds": 900,
                    "reconciler_interval_seconds": 15,
                    "error_detail_limit": 2048,
                    "enabled": False,
                    "max_attempts": 9,
                    "backoff_seconds": [99, 100],
                    "error_details_max_chars": 9999,
                }
            }
        }
    )

    assert settings.maximum_attempts == 4
    assert settings.initial_backoff_seconds == 3
    assert settings.lease_seconds == 900
    assert settings.reconciler_interval_seconds == 15
    assert settings.error_detail_limit == 2048


def test_load_retry_settings_uses_explicit_non_local_defaults(monkeypatch) -> None:
    monkeypatch.delenv("FITCV_LOCAL_MODE", raising=False)

    settings = load_retry_settings({})

    assert settings.maximum_attempts == 3
    assert settings.initial_backoff_seconds == 10
    assert settings.lease_seconds == 300
    assert settings.reconciler_interval_seconds == 30
    assert settings.error_detail_limit == 10000
    assert settings.revision == 0
