"""
@meta
type: test
scope: unit
domain: persistence
covers:
  - sqlite path helper parity across runtime modules
  - BigQuery client helper parity between shared wrappers
excludes:
  - live BigQuery calls
  - sqlite writes
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

from unittest.mock import patch

from fitcv import enrich
from fitcv import evidence
from fitcv import persistence
from fitcv import shortlist_runtime


def test_sqlite_path_helpers_share_same_runtime_value(monkeypatch) -> None:
    monkeypatch.setenv("FITCV_CP_SQLITE_PATH", "C:/tmp/fitcv.sqlite3")

    assert persistence.get_local_sqlite_path() == "C:/tmp/fitcv.sqlite3"
    assert shortlist_runtime.sqlite_path() == persistence.get_local_sqlite_path()
    assert enrich._sqlite_path() == persistence.get_local_sqlite_path()
    assert evidence._local_sqlite_path() == persistence.get_local_sqlite_path()


def test_bigquery_client_wrappers_share_same_behavior() -> None:
    config = {
        "gcp_project": "fitcv-test",
        "service_account_key": "sa.json",
    }

    with patch("google.oauth2.service_account.Credentials.from_service_account_file", return_value="creds") as creds_patch, patch(
        "google.cloud.bigquery.Client",
        side_effect=["shared-client", "shortlist-client"],
    ) as client_patch:
        shared_client = persistence.build_bigquery_client(config)
        shortlist_client = shortlist_runtime.build_bigquery_client(config)

    assert shared_client == "shared-client"
    assert shortlist_client == "shortlist-client"
    assert creds_patch.call_count == 2
    assert client_patch.call_args_list[0].kwargs == {"project": "fitcv-test", "credentials": "creds"}
    assert client_patch.call_args_list[1].kwargs == {"project": "fitcv-test", "credentials": "creds"}
