from __future__ import annotations

import json
from unittest.mock import MagicMock, patch


def test_worker_auto_accept_routes_domain_proposals_through_central_queue() -> None:
    from fitcv_cp.worker_job import _sync_central_synonym_suggestions

    payload = {
        "proposals": [
            {
                "field": "domain",
                "alias": "fintech",
                "canonical": "financial technology",
                "evidence_summary": {"occurrence_count": 3},
                "conflict_summary": {"has_conflict": False},
            }
        ]
    }
    run = MagicMock(
        effective_settings_json=json.dumps(
            {"synonym_management": {"auto_accept_suggestions_enabled": True}}
        )
    )

    with (
        patch(
            "fitcv_cp.worker_job.ingest_synonym_suggestions",
            return_value={"actionable_suggestion_ids": ["suggestion-domain"]},
        ) as ingest_mock,
        patch("fitcv_cp.worker_job.apply_synonym_suggestion_action") as approve_mock,
    ):
        _sync_central_synonym_suggestions(
            run_id="run-domain",
            run_record=run,
            payload=payload,
        )

    ingest_mock.assert_called_once_with(
        [
            {
                "synonym_type": "domain",
                "alias": "fintech",
                "canonical": "financial technology",
                "run_id": "run-domain",
                "confidence": None,
                "candidate_canonicals": [],
                "evidence_note": None,
                "evidence": {
                    "evidence_summary": {"occurrence_count": 3},
                    "conflict_summary": {"has_conflict": False},
                },
            }
        ]
    )
    approve_mock.assert_called_once_with(
        ["suggestion-domain"], action="approve", acted_by="automation"
    )
