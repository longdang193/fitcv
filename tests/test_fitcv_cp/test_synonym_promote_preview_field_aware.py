from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch


def test_build_promote_global_preview_is_field_aware() -> None:
    from fitcv_cp.app import _build_promote_global_preview

    run = SimpleNamespace(run_id="run-test")
    payload = {
        "proposals": [
            {
                "proposal_id": "p-skill",
                "field": "skill",
                "alias": "gcp",
                "canonical": "google cloud",
                "proposal_status": "approved_for_run_overlay",
            },
            {
                "proposal_id": "p-domain",
                "field": "domain",
                "alias": "fintech",
                "canonical": "financial technology",
                "proposal_status": "approved_for_run_overlay",
            },
            {
                "proposal_id": "p-role",
                "field": "role_family",
                "alias": "data eng",
                "canonical": "data engineering",
                "proposal_status": "approved_for_run_overlay",
            },
            {
                "proposal_id": "p-pending",
                "field": "domain",
                "alias": "banking",
                "canonical": "banking",
                "proposal_status": "proposed_unreviewed",
            },
        ]
    }

    with (
        patch("fitcv_cp.app._load_global_skill_synonyms_map", return_value={"gcp": "google cloud"}),
        patch("fitcv_cp.app._load_global_domain_alias_map", return_value={}),
        patch("fitcv_cp.app._load_global_role_family_alias_map", return_value={"data eng": "engineering"}),
    ):
        preview = _build_promote_global_preview(
            run=run,
            payload=payload,
            selected_proposal_ids=["p-skill", "p-domain", "p-role", "p-pending"],
        )

    assert preview["counts"]["add"] == 1
    assert preview["counts"]["update"] == 1
    assert preview["counts"]["conflict"] == 0
    assert preview["counts"]["skip"] >= 1

    assert [row["proposal_id"] for row in preview["ready_rows_by_field"]["domain"]] == ["p-domain"]
    assert preview["ready_rows_by_field"]["domain"][0]["diff_type"] == "add"

    assert [row["proposal_id"] for row in preview["ready_rows_by_field"]["role_family"]] == ["p-role"]
    assert preview["ready_rows_by_field"]["role_family"][0]["diff_type"] == "update"

    assert [row["proposal_id"] for row in preview["already_global_rows_by_field"]["skill"]] == ["p-skill"]
    assert preview["already_global_rows_by_field"]["skill"][0]["reason"] == "already_present"

