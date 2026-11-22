from fitcv.candidate import converge_candidate_profile_for_runtime
from fitcv.pipeline_stage_artifacts import build_ranking_stage_block
from fitcv.ranking_contract import RANKING_CV_HANDOFF_VERSION, build_ranking_cv_handoff


def _stage_block(**kwargs):
    return {
        "stage_result": {"evidence": {"decision_summary": {}}},
        **kwargs,
    }


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
    assert block["admission_manifest"] == admission_manifest


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
