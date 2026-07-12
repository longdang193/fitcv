from __future__ import annotations

from unittest.mock import patch


def test_worker_auto_promote_global_skips_non_skill_proposals() -> None:
    from fitcv_cp.worker_job import _run_synonym_automation_for_payload
    from fitcv_cp.models import RunStatus

    payload = {
        "proposals": [
            {
                "proposal_id": "p-domain",
                "field": "domain",
                "alias": "fintech",
                "canonical": "financial technology",
                "proposal_status": "approved_for_run_overlay",
            }
        ],
        "synonym_proposals_trace": {"trace_summary": {}},
    }

    mode = {
        "auto_triage_recommendation_enabled": False,
        "auto_apply_recommendation_enabled": False,
        "auto_promote_global_enabled": True,
        "promote_global_enabled": True,
        "triage_recommendation_reuse_enabled": False,
        "auto_accept_ai_action_enabled": False,
        "apply_to_run_enabled": True,
        "propose_enabled": True,
    }

    with (
        patch("fitcv_cp.worker_job.resolve_synonym_management_mode", return_value=mode),
        patch("fitcv_cp.worker_job._persist_global_skill_synonyms_map") as persist_skill,
        patch("fitcv_cp.worker_job.append_event"),
        patch("fitcv_cp.worker_job.update_run_synonym_proposals"),
        patch("fitcv_cp.worker_job.update_run_effective_settings"),
    ):
        _run_synonym_automation_for_payload(
            run_id="run-test",
            run_record=None,
            payload=payload,
            run_status=RunStatus.SUCCEEDED,
            client=None,
            project="proj",
            dataset="ds",
        )

    persist_skill.assert_not_called()

