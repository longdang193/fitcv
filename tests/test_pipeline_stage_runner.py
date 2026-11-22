from fitcv import pipeline_stage_runner


def test_requirement_aware_shortlist_does_not_use_vector_shortlist_store(monkeypatch) -> None:
    monkeypatch.setattr(
        pipeline_stage_runner,
        "build_evidence_projection",
        lambda profile: {"items": [], "fingerprint": "projection-1"},
    )

    class Store:
        def store_shortlist(self, rows, config):
            raise AssertionError("requirement-aware rows are not vector shortlist rows")

        def store_shortlist_admission_ledger(self, rows, diagnostics, run_id, config):
            return None

    job = {
        "job_url": "https://example.test/job-1",
        "title": "Data Analyst",
        "description": "Analyze data and report findings.",
        "retrieval_strategy": "vector_cosine_v1",
        "requirement_coverage": [
            {"requirement_id": "required_skill:python", "status": "unknown"}
        ],
    }

    admitted, *_ = pipeline_stage_runner._execute_requirement_aware_shortlist_stage(
        run_id="run-1",
        state={},
        profile={"revision": "profile-1"},
        passed_jobs=[job],
        config={
            "pipeline": {
                "retrieval_strategy": "lexical_v1",
                "shortlist_strategy": "core_pareto_evidence_v1",
                "shortlist_policy": "requirement_aware_v1",
            }
        },
        reporter=None,
        pipeline_store=Store(),
        set_span_attributes=lambda attributes: None,
    )

    assert admitted
