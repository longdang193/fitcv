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


def test_requirement_aware_shortlist_assesses_full_pool_before_compact_selection(monkeypatch) -> None:
    calls: list[int] = []
    monkeypatch.setattr(
        pipeline_stage_runner,
        "build_evidence_projection",
        lambda profile: {"items": [{"evidence_id": "profile-item"}], "fingerprint": "projection-1"},
    )

    assessment_candidates = [
        {
            "evidence_id": f"ev-{index}",
            "requirement_assessments": {
                "req-1": {
                    "qualified_support": True,
                    "canonical_match": True,
                    "qualifier_status": "verified",
                }
            },
        }
        for index in range(4)
    ]

    def retrieve(*args, **kwargs):
        calls.append(int(args[2]))
        return {
            "selected_evidence": assessment_candidates[:1],
            "assessment_candidates": assessment_candidates,
            "unselected_top_candidates": [],
        }

    monkeypatch.setattr(pipeline_stage_runner, "retrieve_evidence_bundle", retrieve)
    job = {
        "job_url": "https://example.test/full-assessment",
        "requirement_occurrences": [
            {"occurrence_id": "req-1", "category": "required", "source_wording": "Python"}
        ],
    }
    state: dict = {}

    admitted, *_ = pipeline_stage_runner._execute_requirement_aware_shortlist_stage(
        run_id="run-full-assessment",
        state=state,
        profile={"revision": "profile-1"},
        passed_jobs=[job],
        config={"pipeline": {"shortlist_strategy": "core_pareto_evidence_v1"}},
        reporter=None,
        pipeline_store=type("Store", (), {
            "store_shortlist": lambda self, rows, config: None,
            "store_shortlist_admission_ledger": lambda self, rows, diagnostics, run_id, config: None,
        })(),
        set_span_attributes=lambda attributes: None,
    )

    assert calls == [3]
    assert admitted[0]["coverage"]["states"][0]["evidence_ids"] == [
        "ev-0", "ev-1", "ev-2", "ev-3"
    ]
    assert len(admitted[0]["stage5_evidence"]) == 4
    assert state["shortlist_diagnostics"]["assessment_fingerprint"]


def test_requirement_aware_shortlist_display_selection_does_not_change_assessment(monkeypatch) -> None:
    job = {
        "job_url": "https://example.test/display-independent",
        "requirement_occurrences": [
            {"occurrence_id": "req-1", "category": "required", "source_wording": "Python"}
        ],
    }
    candidates = [
        {
            "evidence_id": f"ev-{index}",
            "requirement_assessments": {
                "req-1": {
                    "qualified_support": index == 0,
                    "canonical_match": True,
                    "qualifier_status": "verified" if index == 0 else "unverified",
                }
            },
        }
        for index in range(4)
    ]

    def run(selected_count: int) -> tuple[dict, dict]:
        monkeypatch.setattr(
            pipeline_stage_runner,
            "build_evidence_projection",
            lambda profile: {"items": [], "fingerprint": "projection-1"},
        )
        monkeypatch.setattr(
            pipeline_stage_runner,
            "retrieve_evidence_bundle",
            lambda *args, **kwargs: {
                "selected_evidence": candidates[:selected_count],
                "assessment_candidates": candidates,
                "unselected_top_candidates": [],
            },
        )
        state: dict = {}
        admitted, *_ = pipeline_stage_runner._execute_requirement_aware_shortlist_stage(
            run_id=f"run-{selected_count}",
            state=state,
            profile={"revision": "profile-1"},
            passed_jobs=[job],
            config={"pipeline": {"shortlist_strategy": "core_pareto_evidence_v1"}},
            reporter=None,
            pipeline_store=type("Store", (), {
                "store_shortlist": lambda self, rows, config: None,
                "store_shortlist_admission_ledger": lambda self, rows, diagnostics, run_id, config: None,
            })(),
            set_span_attributes=lambda attributes: None,
        )
        return admitted[0], state["shortlist_diagnostics"]

    one, one_diagnostics = run(1)
    three, three_diagnostics = run(3)

    assert one["coverage"] == three["coverage"]
    assert one_diagnostics["assessment_fingerprint"] == three_diagnostics["assessment_fingerprint"]
    assert one_diagnostics["decision_fingerprint"] == three_diagnostics["decision_fingerprint"]
