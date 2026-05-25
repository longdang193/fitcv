from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch


def test_commit_synonym_global_promotion_routes_by_field_and_skips_conflict_fields() -> None:
    from fitcv_cp.app import _commit_synonym_global_promotion

    run = SimpleNamespace(run_id="run-test")
    payload = {
        "proposals": [
            {"proposal_id": "p-skill"},
            {"proposal_id": "p-domain"},
            {"proposal_id": "p-role"},
        ]
    }
    preview = {
        "rows": [
            {
                "proposal_id": "p-domain",
                "field": "domain",
                "alias": "fintech",
                "canonical": "financial technology",
                "diff_type": "add",
                "reason": "new_alias",
            },
            {
                "proposal_id": "p-domain-conflict",
                "field": "domain",
                "alias": "banking",
                "canonical": "banking",
                "diff_type": "conflict",
                "reason": "duplicate_alias_with_multiple_canonicals",
            },
            {
                "proposal_id": "p-role",
                "field": "role_family",
                "alias": "data eng",
                "canonical": "data engineering",
                "diff_type": "add",
                "reason": "new_alias",
            },
            {
                "proposal_id": "p-skill",
                "field": "skill",
                "alias": "gcp",
                "canonical": "google cloud",
                "diff_type": "add",
                "reason": "new_alias",
            },
        ]
    }

    persisted: dict[str, dict[str, str]] = {}

    def _persist(field: str):
        def _inner(m: dict[str, str]) -> None:
            persisted[field] = dict(m)
        return _inner

    with (
        patch("fitcv_cp.app._load_global_skill_synonyms_map", return_value={}),
        patch("fitcv_cp.app._load_global_domain_alias_map", return_value={}),
        patch("fitcv_cp.app._load_global_role_family_alias_map", return_value={}),
        patch("fitcv_cp.app._persist_global_skill_synonyms_map", side_effect=_persist("skill")),
        patch("fitcv_cp.app._persist_global_domain_alias_map", side_effect=_persist("domain")),
        patch("fitcv_cp.app._persist_global_role_family_alias_map", side_effect=_persist("role_family")),
        patch("fitcv_cp.app.update_run_synonym_proposals"),
        patch("fitcv_cp.app.append_event"),
    ):
        result = _commit_synonym_global_promotion(
            run=run,
            payload=payload,
            preview=preview,
            selected_ids=["p-skill", "p-domain", "p-role"],
            acted_by="tester",
            note="test",
            bq=None,
            project="proj",
            dataset="ds",
        )

    assert "domain" not in persisted
    assert persisted["role_family"] == {"data eng": "data engineering"}
    assert persisted["skill"] == {"gcp": "google cloud"}
    assert result["applied"] == 2
    assert result["failed"] >= 1
    assert "domain" in result["conflict_fields"]

