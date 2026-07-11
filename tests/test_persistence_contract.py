"""
@meta
type: test
scope: unit
domain: persistence
covers:
  - sqlite path helper parity across runtime modules
excludes:
  - sqlite writes
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

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
