from fitcv.ai_score import parse_score_response
from fitcv.candidate import converge_candidate_profile_for_runtime
import pytest

from fitcv.pipeline_stage_artifacts import (
    build_ranking_score_state_diagnostics,
    build_ranking_stage_block,
)
from fitcv.ranking_contract import RANKING_CV_HANDOFF_VERSION, build_ranking_cv_handoff


def _stage_block(**kwargs):
    return {
        "stage_result": {"evidence": {"decision_summary": {}}},
        **kwargs,
    }


@pytest.mark.parametrize(
    ("row", "expected_status", "expected_failure"),
    [
        ({"ai_score": 0.8}, None, None),
        ({"parser_status": "malformed_json"}, "invalid", "malformed_json"),
        ({"reranker_parser_status": "runtime_exception"}, "unscored", "provider_failure"),
        ({"failure_code": "timeout"}, "unscored", "timeout"),
        ({"ai_score": None}, "unscored", "legacy_ambiguous_score_state"),
    ],
)
def test_ranking_score_state_diagnostics_classifies_only_non_valid_rows(
    row: dict[str, object],
    expected_status: str | None,
    expected_failure: str | None,
) -> None:
    diagnostics = build_ranking_score_state_diagnostics(
        [
            {
                **row,
                "_input_index": 7,
                "canonical_job_identity": "job-key-7",
                "raw_job_fingerprint": "fingerprint-7",
                "job_url": "https://private.example/job",
                "title": "Private title",
                "description": "Private description",
                "prompt": "Private prompt",
                "model_output": "Private model output",
            }
        ]
    )

    if expected_status is None:
        assert diagnostics == []
        return
    assert len(diagnostics) == 1
    diagnostic = diagnostics[0]
    assert diagnostic["score_status"] == expected_status
    assert diagnostic["failure_code"] == expected_failure
    assert diagnostic["job_key"] == "job-key-7"
    assert diagnostic["input_index"] == 7
    assert diagnostic["raw_job_fingerprint"] == "fingerprint-7"
    assert set(diagnostic) == {
        "schema_version",
        "job_key",
        "score_status",
        "failure_code",
        "disposition",
        "retry_eligible",
        "input_index",
        "raw_job_fingerprint",
    }


def test_ranking_score_state_diagnostics_are_bounded_and_deterministic() -> None:
    rows = [
        {"_input_index": 2, "canonical_job_identity": "b", "failure_code": "timeout"},
        {"_input_index": 1, "canonical_job_identity": "a", "failure_code": "provider_failure"},
        {"_input_index": 3, "canonical_job_identity": "c", "failure_code": "missing_ai_score"},
    ]

    diagnostics = build_ranking_score_state_diagnostics(rows, max_items=2)

    assert [item["job_key"] for item in diagnostics] == ["a", "b"]
    assert all("job_url" not in item and "title" not in item for item in diagnostics)


def test_ranking_stage_persists_handoff_without_promoting_shortlist() -> None:
    row = {
        "raw_job_fingerprint": "job-1",
        "job_url": "https://example.test/job-1",
        "baseline_fit": 0.8,
        "baseline_rank": 1,
        "score_status": "valid",
        "job_qualifiers": {"level": "senior"},
        "canonical_evidence_ids": ["ev-2", "ev-1"],
        "confirmed_gaps": [],
        "confirmed_unknowns": [],
        "source_provenance": {"source": "fixture"},
    }
    row.update(parse_score_response('{"ai_score": 0.8, "key_risks": "not-a-list"}'))
    admission_manifest = {"shortlist_status": "shortlist_admitted", "promoted": False}
    block = build_ranking_stage_block(
        ranking_reached=True,
        ai_scores=[row],
        ranking_inputs=[row],
        ranked=[row],
        ranked_urls={row["job_url"]},
        final_top_n=1,
        ranking_fit_distribution={"strong": 1},
        ranking_quality_metrics={},
        ranking_reuse_metrics={},
        ranking_prompt_provenance={
            "prompt_id": "p",
            "prompt_version": "v",
            "template_path": "t",
            "prompt_customized": False,
            "prompt_replacement_sha256": None,
            "prompt_replacement_char_count": 0,
        },
        ranking_policy={"policy_version": "ranking-v2"},
        ranking_contract={
            "ranking_order_version": "order-v1",
            "ranking_score_contract_version": "ranking_score_v1",
            "ranking_contract_fingerprint": "contract",
        },
        legacy_checkpoint_adaptation_count=0,
        zero_weight_features=[],
        contributing_features=["holistic_ai_fit"],
        profile=converge_candidate_profile_for_runtime(
            {
                "name": "Candidate",
                "experiences": [],
                "projects": [],
                "skills": [],
                "revision": "profile-1",
            }
        ),
        config={},
        stage_block_builder=_stage_block,
        stage_block_not_reached_builder=lambda stage: {"stage": stage},
        sample_rows_builder=lambda rows, builder: [built for row in rows if (built := builder(row))],
        ranking_row_sample_builder=lambda current: {"job_url": current["job_url"]},
        extract_job_url=lambda current: current["job_url"],
        ai_score_model_resolver=lambda config: "model",
        effective_preferences_resolver=lambda profile, config: {},
        ranking_admission_manifest=admission_manifest,
    )

    assert block["ranking_cv_handoff"]["schema_version"] == RANKING_CV_HANDOFF_VERSION
    assert block["ranking_cv_handoff"]["status"] == "complete"
    assert block["ranking_cv_handoff"]["items"][0]["evidence_ids"] == ["ev-1", "ev-2"]
    assert block["selected_ranking_identities"] == ["job-1"]
    assert block["admission_manifest"] == admission_manifest
    diagnostics = block["scorer_diagnostics_by_identity"]["job-1"]
    assert [item["code"] for item in diagnostics] == [
        "ranking_metadata_missing",
        "ranking_metadata_missing",
        "ranking_metadata_invalid_type",
    ]
    assert diagnostics[-1]["facts"]["field"] == "key_risks"


def test_ranking_stage_marks_incomplete_handoff_closed() -> None:
    row = {"raw_job_fingerprint": "job-1", "job_url": "u", "baseline_fit": 0.8, "baseline_rank": 1}
    block = build_ranking_stage_block(
        ranking_reached=True,
        ai_scores=[row],
        ranking_inputs=[row],
        ranked=[row],
        ranked_urls={"u"},
        final_top_n=1,
        ranking_fit_distribution={},
        ranking_quality_metrics={},
        ranking_reuse_metrics={},
        ranking_prompt_provenance={
            "prompt_id": "p", "prompt_version": "v", "template_path": "t",
            "prompt_customized": False, "prompt_replacement_sha256": None,
            "prompt_replacement_char_count": 0,
        },
        ranking_policy={"policy_version": "ranking-v2"},
        ranking_contract={"ranking_order_version": "order-v1"},
        legacy_checkpoint_adaptation_count=0,
        zero_weight_features=[],
        contributing_features=[],
        profile={},
        config={},
        stage_block_builder=_stage_block,
        stage_block_not_reached_builder=lambda stage: {"stage": stage},
        sample_rows_builder=lambda rows, builder: [],
        ranking_row_sample_builder=lambda current: {"job_url": current["job_url"]},
        extract_job_url=lambda current: current["job_url"],
        ai_score_model_resolver=lambda config: "model",
        effective_preferences_resolver=lambda profile, config: {},
        ranking_cv_handoffs_by_identity={"job-1": {}},
    )

    assert block["ranking_cv_handoff"]["status"] == "incomplete"
    assert block["ranking_cv_handoff"]["references"]["job-1"] is None


def test_ranking_stage_reuses_analysis_handoff_instead_of_rebuilding_it() -> None:
    row = {
        "raw_job_fingerprint": "job-1",
        "job_url": "https://example.test/job-1",
        "title": "Data Engineer",
        "baseline_fit": 0.8,
        "baseline_rank": 1,
        "score_status": "valid",
        "source_provenance": {"stage": "ranking"},
        "ranking_order_version": "order-v1",
        "ranking_policy_version": "policy-v1",
    }
    handoff = build_ranking_cv_handoff(
        {
            **row,
            "job_qualifiers": {"title": "Data Engineer", "level": "senior"},
        },
        candidate_profile_revision="profile-1",
    )
    block = build_ranking_stage_block(
        ranking_reached=True,
        ai_scores=[row],
        ranking_inputs=[row],
        ranked=[row],
        ranked_urls={row["job_url"]},
        final_top_n=1,
        ranking_fit_distribution={"strong": 1},
        ranking_quality_metrics={},
        ranking_reuse_metrics={},
        ranking_prompt_provenance={
            "prompt_id": "p",
            "prompt_version": "v",
            "template_path": "t",
            "prompt_customized": False,
            "prompt_replacement_sha256": None,
            "prompt_replacement_char_count": 0,
        },
        ranking_policy={"policy_version": "policy-v1"},
        ranking_contract={"ranking_order_version": "order-v1"},
        legacy_checkpoint_adaptation_count=0,
        zero_weight_features=[],
        contributing_features=["holistic_ai_fit"],
        profile={"revision": "profile-1"},
        config={},
        stage_block_builder=_stage_block,
        stage_block_not_reached_builder=lambda stage: {"stage": stage},
        sample_rows_builder=lambda rows, builder: [built for row in rows if (built := builder(row))],
        ranking_row_sample_builder=lambda current: {"job_url": current["job_url"]},
        extract_job_url=lambda current: current["job_url"],
        ai_score_model_resolver=lambda config: "model",
        effective_preferences_resolver=lambda profile, config: {},
        ranking_cv_handoffs_by_identity={"job-1": handoff},
    )

    assert block["ranking_cv_handoff"]["items"][0] == {**handoff, "handoff_status": "complete"}
