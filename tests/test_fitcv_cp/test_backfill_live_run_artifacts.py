from __future__ import annotations

from types import SimpleNamespace

from fitcv_cp.models import RunStatus
from scripts import backfill_live_run_artifacts as script


def test_backfill_script_dry_run_uses_sqlite_run_store_only(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    listed: list[tuple[int, bool]] = []
    persisted: list[str] = []

    run = SimpleNamespace(
        run_id="run-1",
        status=RunStatus.SUCCEEDED,
        results_export_json='{"results": []}',
        cv_generation_debug_json="",
        stage_transition_artifacts_json="",
        settings_used_json="",
        mapping_suggestions_json="",
        synonym_proposals_json="",
    )

    def _fake_list_runs(*, limit: int, include_archived: bool, archived_only: bool = False):
        listed.append((limit, include_archived))
        assert archived_only is False
        return [run]

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(script, "list_runs", _fake_list_runs)
    monkeypatch.setattr(script, "persist_terminal_run_artifact_mirror", lambda *, run_id: persisted.append(run_id))
    monkeypatch.setattr(script.sys, "argv", ["backfill_live_run_artifacts.py", "--dry-run", "--limit", "7"])

    rc = script.main()

    assert rc == 0
    assert listed == [(7, True)]
    assert persisted == []
    assert "dry_run_create run_id=run-1" in capsys.readouterr().out
