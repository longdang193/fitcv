"""
@meta
type: test
scope: unit
domain: inverse_optimization
covers:
  - cv_system.preference-learning
excludes:
  - policy persistence and runtime activation
tags:
  - fast
  - ci-safe
"""

from __future__ import annotations

import dataclasses
import datetime
import json
from pathlib import Path

import pytest
import yaml

import fitcv.inverse_optimization as inverse_optimization
from scripts import run_inverse_optimization as inverse_cli
from fitcv.decision_feedback import (
    DecisionRatingEvent,
    RatingEventType,
    RatingValue,
    build_decision_feedback_source,
    build_episode_records,
)
from fitcv.inverse_optimization import (
    EvaluationAlternativeSlice,
    CompatibleParentReference,
    EvaluationEpisodeContext,
    InverseOptimizationRequest,
    InverseTrainingEpisode,
    RetrievalAuditContext,
    evaluate_preference_residual,
    solve_preference_residual,
)
from fitcv.shortlist_runtime import build_contract_fingerprint


def _policy() -> dict:
    payload = yaml.safe_load(Path("config/policy/decision_learning.yaml").read_text(encoding="utf-8"))
    return payload["decision_learning_policy"]


def _training_episode(
    run_id: str,
    *,
    ratings: tuple[int, int] = (5, 1),
    qualification_marker: str = "first",
    embeddings: tuple[tuple[float, float], tuple[float, float]] = ((1.0, 0.0), (0.0, 1.0)),
) -> InverseTrainingEpisode:
    profile = {
        "headline": "Data Engineer",
        "preferences": {
            "target_role": "Data Engineer",
            "role_families": ["data"],
            "domains": ["analytics"],
            "seniority_target": "mid",
            "preferred_locations": ["Berlin"],
            "work_modes": ["hybrid"],
        },
        "languages": [{"language": "German", "level": "B1"}],
        "qualification_marker": qualification_marker,
    }
    config = {
        "decision_learning_policy": _policy(),
        "ranking_policy": {"policy_version": "ranking-v2"},
        "ranking_contract": {"ranking_contract_fingerprint": "ranking-contract"},
        "embedding_model": "local-test-model",
    }
    rows = [
        {
            "raw_job_fingerprint": "job-a",
            "source_job_url": "https://example.test/a",
            "baseline_fit": 0.4,
            "baseline_fit_label": "stretch",
            "normalized_embedding": list(embeddings[0]),
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
        {
            "raw_job_fingerprint": "job-b",
            "source_job_url": "https://example.test/b",
            "baseline_fit": 0.5,
            "baseline_fit_label": "stretch",
            "normalized_embedding": list(embeddings[1]),
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
    ]
    source = build_decision_feedback_source(
        run_id=run_id,
        candidate_profile=profile,
        config=config,
        scoring_rows=rows,
    )
    episode, alternatives = build_episode_records(source)
    now = datetime.datetime(2026, 7, 16, tzinfo=datetime.timezone.utc)
    events = tuple(
        DecisionRatingEvent(
            event_sequence=index,
            event_id=f"{run_id}-event-{index}",
            episode_id=episode.episode_id,
            alternative_id=alternative_id,
            event_type=RatingEventType.SET_RATING,
            rating=RatingValue(rating),
            rating_scale_version=episode.rating_scale_version,
            acted_by="local_operator",
            created_at=now,
        )
        for index, (alternative_id, rating) in enumerate(
            (("job-a", ratings[0]), ("job-b", ratings[1])), start=1
        )
    )
    context = EvaluationEpisodeContext(
        episode_id=episode.episode_id,
        alternative_slices=(
            EvaluationAlternativeSlice("job-a", "stretch", "berlin", "german_b1"),
            EvaluationAlternativeSlice("job-b", "stretch", "berlin", "german_b1"),
        ),
        retrieval_audit=RetrievalAuditContext(
            audit_fingerprint=f"audit-{run_id}",
            sample_count=2,
            cutoff_vector_similarity=0.3,
            sampled_vector_similarities=(0.3, 0.2),
            relevance_labels_available=False,
        ),
    )
    return InverseTrainingEpisode(
        episode=episode,
        alternatives=alternatives,
        events=events,
        events_loaded_through_sequence=2,
        evaluation_context=context,
    )


def _request(*episodes: InverseTrainingEpisode) -> InverseOptimizationRequest:
    return InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id="ranking_v1",
        event_watermark=2,
        episodes=episodes,
    )


def test_loaded_through_sequence_below_watermark_is_invalid() -> None:
    episode = _training_episode("run-1")
    invalid = InverseTrainingEpisode(
        episode=episode.episode,
        alternatives=episode.alternatives,
        events=episode.events,
        events_loaded_through_sequence=1,
        evaluation_context=episode.evaluation_context,
    )
    result = solve_preference_residual(_request(invalid), _policy())
    assert result.status == "invalid_input"
    assert result.candidate_preference_vector is None


def test_solver_learns_bounded_direction_with_episode_local_qualification() -> None:
    """@proves cv_system.preference-learning"""
    first = _training_episode("run-1", qualification_marker="first")
    second = _training_episode("run-2", qualification_marker="second")
    result = solve_preference_residual(_request(first, second), _policy())
    assert result.status == "optimal"
    assert result.candidate_preference_vector is not None
    assert result.candidate_preference_vector[0] > 0.0
    assert result.candidate_preference_vector[1] < 0.0
    assert result.preference_vector_norm <= 1.0 + 1.0e-7


def test_contradictory_edges_remain_feasible_through_slack() -> None:
    first = _training_episode("run-1", ratings=(5, 1))
    second = _training_episode("run-2", ratings=(1, 5))
    result = solve_preference_residual(_request(first, second), _policy())
    assert result.status == "optimal"
    assert result.max_preference_violation is not None
    assert result.max_preference_violation > 0.0


def test_episode_and_event_permutations_preserve_problem_and_vector() -> None:
    first = _training_episode("run-1")
    second = _training_episode("run-2")
    direct = solve_preference_residual(_request(first, second), _policy())
    reversed_first = InverseTrainingEpisode(
        episode=first.episode,
        alternatives=tuple(reversed(first.alternatives)),
        events=tuple(reversed(first.events)),
        events_loaded_through_sequence=first.events_loaded_through_sequence,
        evaluation_context=first.evaluation_context,
    )
    permuted = solve_preference_residual(_request(second, reversed_first), _policy())
    assert direct.problem_fingerprint == permuted.problem_fingerprint
    assert direct.candidate_preference_vector == pytest.approx(
        permuted.candidate_preference_vector, abs=1.0e-6
    )


def test_evaluation_groups_by_episode_and_keeps_audit_unlabeled() -> None:
    """@proves cv_system.preference-learning"""
    episodes = tuple(_training_episode(f"run-{index}") for index in range(1, 4))
    request = _request(*episodes)
    full_result = solve_preference_residual(request, _policy())
    evaluation = evaluate_preference_residual(request, full_result, _policy())
    assert evaluation.status == "evaluated"
    assert evaluation.evaluation_mode == "leave_one_episode_out"
    assert len(evaluation.fold_results) == 3
    assert all(
        set(fold.train_episode_ids).isdisjoint(fold.validation_episode_ids)
        for fold in evaluation.fold_results
    )
    assert sorted(
        episode_id
        for fold in evaluation.fold_results
        for episode_id in fold.validation_episode_ids
    ) == sorted(episode.episode.episode_id for episode in episodes)
    assert evaluation.retrieval_audit.status == "unlabeled_inspection_only"
    assert evaluation.retrieval_audit.recall is None


@pytest.mark.parametrize(
    "embedding_json, fingerprint",
    [
        ("not-json", "unused"),
        ("[NaN, 0.0]", "unused"),
        ("[1.0, 0.0, 0.0]", "unused"),
        (
            "[0.0, 0.0]",
            build_contract_fingerprint({"normalized_embedding": [0.0, 0.0]}),
        ),
    ],
)
def test_malformed_embeddings_fail_before_solver_import(
    monkeypatch: pytest.MonkeyPatch,
    embedding_json: str,
    fingerprint: str,
) -> None:
    training = _training_episode("run-invalid-embedding")
    invalid_alternative = dataclasses.replace(
        training.alternatives[0],
        normalized_embedding_json=embedding_json,
        embedding_vector_fingerprint=fingerprint,
    )
    invalid = dataclasses.replace(
        training,
        alternatives=(invalid_alternative, training.alternatives[1]),
    )
    monkeypatch.setattr(
        inverse_optimization.importlib,
        "import_module",
        lambda name: pytest.fail(f"solver import attempted: {name}"),
    )
    result = solve_preference_residual(_request(invalid), _policy())
    assert result.status == "invalid_input"
    assert result.candidate_preference_vector is None


def test_nonfinite_baseline_fails_before_solver_import(monkeypatch: pytest.MonkeyPatch) -> None:
    training = _training_episode("run-invalid-baseline")
    invalid = dataclasses.replace(
        training,
        alternatives=(
            dataclasses.replace(training.alternatives[0], baseline_fit=float("nan")),
            training.alternatives[1],
        ),
    )
    monkeypatch.setattr(
        inverse_optimization.importlib,
        "import_module",
        lambda name: pytest.fail(f"solver import attempted: {name}"),
    )
    result = solve_preference_residual(_request(invalid), _policy())
    assert result.status == "invalid_input"
    assert result.candidate_preference_vector is None


def test_mixed_contracts_fail_closed_before_solver_import(monkeypatch: pytest.MonkeyPatch) -> None:
    first = _training_episode("run-compatible")
    second = _training_episode("run-incompatible")
    second = dataclasses.replace(
        second,
        episode=dataclasses.replace(
            second.episode,
            baseline_policy_fingerprint="different-baseline-policy",
        ),
    )
    monkeypatch.setattr(
        inverse_optimization.importlib,
        "import_module",
        lambda name: pytest.fail(f"solver import attempted: {name}"),
    )
    result = solve_preference_residual(_request(first, second), _policy())
    assert result.status == "invalid_input"
    assert result.candidate_preference_vector is None


def test_zero_edges_return_insufficient_without_solver_import(monkeypatch: pytest.MonkeyPatch) -> None:
    training = _training_episode("run-zero-edges", ratings=(3, 3))
    monkeypatch.setattr(
        inverse_optimization.importlib,
        "import_module",
        lambda name: pytest.fail(f"solver import attempted: {name}"),
    )
    result = solve_preference_residual(_request(training), _policy())
    assert result.status == "insufficient_evidence"
    assert result.diagnostics.error_code == "zero_compiled_edges"


def test_missing_cvxpy_returns_typed_solver_error(monkeypatch: pytest.MonkeyPatch) -> None:
    training = _training_episode("run-no-cvxpy")
    original_import = inverse_optimization.importlib.import_module

    def missing_cvxpy(name: str):
        if name == "cvxpy":
            raise ImportError("missing")
        return original_import(name)

    monkeypatch.setattr(inverse_optimization.importlib, "import_module", missing_cvxpy)
    result = solve_preference_residual(_request(training), _policy())
    assert result.status == "solver_error"
    assert result.candidate_preference_vector is None
    assert result.diagnostics.error_code == "install fitcv[inverse-optimization]"


def test_missing_clarabel_returns_typed_solver_error(monkeypatch: pytest.MonkeyPatch) -> None:
    import cvxpy

    training = _training_episode("run-no-clarabel")
    monkeypatch.setattr(cvxpy, "installed_solvers", lambda: [])
    result = solve_preference_residual(_request(training), _policy())
    assert result.status == "solver_error"
    assert result.candidate_preference_vector is None
    assert result.diagnostics.error_code == "CLARABEL is not installed"


@pytest.mark.parametrize("raw_status", ["optimal_inaccurate", "infeasible", "unbounded"])
def test_unsupported_solver_statuses_return_no_candidate(
    monkeypatch: pytest.MonkeyPatch,
    raw_status: str,
) -> None:
    import cvxpy

    training = _training_episode(f"run-{raw_status}")

    def force_status(problem, *args, **kwargs):
        problem._status = raw_status
        return None

    monkeypatch.setattr(cvxpy.Problem, "solve", force_status)
    result = solve_preference_residual(_request(training), _policy())
    assert result.status == "solver_error"
    assert result.raw_solver_status == raw_status
    assert result.candidate_preference_vector is None


def test_failed_objective_postcheck_returns_no_candidate(monkeypatch: pytest.MonkeyPatch) -> None:
    import cvxpy

    training = _training_episode("run-postcheck")
    original_solve = cvxpy.Problem.solve

    def corrupt_objective(problem, *args, **kwargs):
        value = original_solve(problem, *args, **kwargs)
        problem._value = float(problem.value) + 1.0
        return value

    monkeypatch.setattr(cvxpy.Problem, "solve", corrupt_objective)
    result = solve_preference_residual(_request(training), _policy())
    assert result.status == "solver_error"
    assert result.candidate_preference_vector is None
    assert result.diagnostics.error_code == "postsolve_validation_failed"


def test_identical_embeddings_report_zero_direction() -> None:
    training = _training_episode(
        "run-identical",
        embeddings=((1.0, 0.0), (1.0, 0.0)),
    )
    result = solve_preference_residual(_request(training), _policy())
    assert result.status == "optimal"
    assert result.diagnostics.zero_direction_count == 1
    assert result.diagnostics.direction_span_status == "none"
    assert result.candidate_preference_vector == pytest.approx((0.0, 0.0), abs=1.0e-6)


def test_grouped_five_fold_evaluation_holds_each_episode_once() -> None:
    episodes = tuple(_training_episode(f"run-{index}") for index in range(9))
    request = _request(*episodes)
    result = solve_preference_residual(request, _policy())
    evaluation = evaluate_preference_residual(request, result, _policy())
    assert evaluation.status == "evaluated"
    assert evaluation.evaluation_mode == "grouped_k_fold"
    assert len(evaluation.fold_results) == 5
    assert all(
        set(fold.train_episode_ids).isdisjoint(fold.validation_episode_ids)
        for fold in evaluation.fold_results
    )
    held_out = [
        episode_id
        for fold in evaluation.fold_results
        for episode_id in fold.validation_episode_ids
    ]
    assert sorted(held_out) == sorted(episode.episode.episode_id for episode in episodes)


def test_parent_comparison_is_symmetric_and_compatibility_gated() -> None:
    episodes = tuple(_training_episode(f"run-parent-{index}") for index in range(3))
    request = _request(*episodes)
    result = solve_preference_residual(request, _policy())
    parent = CompatibleParentReference(
        parent_kind="zero_residual",
        domain_id=request.domain_id,
        parent_ref="zero",
        preference_vector=(0.0, 0.0),
        baseline_policy_fingerprint=episodes[0].episode.baseline_policy_fingerprint,
        ranking_contract_fingerprint=episodes[0].episode.ranking_contract_fingerprint,
        embedding_contract_fingerprint=episodes[0].episode.embedding_contract_fingerprint,
        embedding_dimension=episodes[0].episode.embedding_dimension,
        learned_alpha=_policy()["inverse_optimization"]["learned_alpha"],
    )
    compatible = evaluate_preference_residual(request, result, _policy(), parent)
    incompatible = evaluate_preference_residual(
        request,
        result,
        _policy(),
        dataclasses.replace(parent, domain_id="other"),
    )
    assert compatible.parent_comparison_status == "compatible"
    assert compatible.aggregate_metrics is not None
    assert compatible.aggregate_metrics.parent is not None
    assert compatible.aggregate_metrics.parent.pair_count == compatible.aggregate_metrics.baseline.pair_count
    assert incompatible.parent_comparison_status == "incompatible"
    assert incompatible.aggregate_metrics is not None
    assert incompatible.aggregate_metrics.parent is None


def test_missing_evaluation_context_stays_unknown_and_audit_unavailable() -> None:
    episodes = tuple(
        dataclasses.replace(_training_episode(f"run-missing-{index}"), evaluation_context=None)
        for index in range(3)
    )
    request = _request(*episodes)
    result = solve_preference_residual(request, _policy())
    evaluation = evaluate_preference_residual(request, result, _policy())
    assert evaluation.status == "evaluated"
    assert evaluation.coverage.locations == (("unknown", 6),)
    assert evaluation.coverage.languages == (("unknown", 6),)
    assert evaluation.retrieval_audit.status == "not_available"
    assert evaluation.retrieval_audit.recall is None


def _bundle_payload(run_id: str = "run-cli") -> dict:
    training = _training_episode(run_id)
    profile = {
        "headline": "Data Engineer",
        "preferences": {
            "target_role": "Data Engineer",
            "role_families": ["data"],
            "domains": ["analytics"],
            "seniority_target": "mid",
            "preferred_locations": ["Berlin"],
            "work_modes": ["hybrid"],
        },
        "languages": [{"language": "German", "level": "B1"}],
        "qualification_marker": "first",
    }
    config = {
        "decision_learning_policy": _policy(),
        "ranking_policy": {"policy_version": "ranking-v2"},
        "ranking_contract": {"ranking_contract_fingerprint": "ranking-contract"},
        "embedding_model": "local-test-model",
    }
    rows = [
        {
            "raw_job_fingerprint": "job-a",
            "source_job_url": "https://example.test/a",
            "baseline_fit": 0.4,
            "baseline_fit_label": "stretch",
            "normalized_embedding": [1.0, 0.0],
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
        {
            "raw_job_fingerprint": "job-b",
            "source_job_url": "https://example.test/b",
            "baseline_fit": 0.5,
            "baseline_fit_label": "stretch",
            "normalized_embedding": [0.0, 1.0],
            "embedding_contract_fingerprint": "embedding-contract",
            "shortlist_origin": "vector_search",
        },
    ]
    source = build_decision_feedback_source(
        run_id=run_id,
        candidate_profile=profile,
        config=config,
        scoring_rows=rows,
    )
    return {
        "schema_version": "inverse_training_bundle_v1",
        "domain_id": "ranking_v1",
        "event_watermark": 2,
        "episodes": [
            {
                "feedback_source": source,
                "events_loaded_through_sequence": 2,
                "rating_events": [
                    {
                        "event_sequence": event.event_sequence,
                        "event_id": event.event_id,
                        "episode_id": event.episode_id,
                        "alternative_id": event.alternative_id,
                        "event_type": event.event_type.value,
                        "rating": int(event.rating) if event.rating is not None else None,
                        "rating_scale_version": event.rating_scale_version,
                        "acted_by": event.acted_by,
                        "created_at": event.created_at.isoformat(),
                    }
                    for event in training.events
                ],
                "evaluation_context": {
                    "episode_id": training.evaluation_context.episode_id,
                    "alternative_slices": [
                        dataclasses.asdict(item)
                        for item in training.evaluation_context.alternative_slices
                    ],
                    "retrieval_audit": dataclasses.asdict(
                        training.evaluation_context.retrieval_audit
                    ),
                },
            }
        ],
    }


def test_cli_train_stdout_is_canonical_and_repeatable(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """@proves cv_system.preference-learning"""
    input_path = tmp_path / "bundle.json"
    input_path.write_text(json.dumps(_bundle_payload()), encoding="utf-8")
    first_exit = inverse_cli.main(
        ["train", "--domain", "ranking_v1", "--input", str(input_path)]
    )
    first = capsys.readouterr().out
    second_exit = inverse_cli.main(
        ["train", "--domain", "ranking_v1", "--input", str(input_path)]
    )
    second = capsys.readouterr().out
    assert first_exit == second_exit == 0
    first_payload = json.loads(first)
    second_payload = json.loads(second)
    assert first == json.dumps(first_payload, sort_keys=True, separators=(",", ":")) + "\n"
    assert second == json.dumps(second_payload, sort_keys=True, separators=(",", ":")) + "\n"
    assert first_payload["status"] == second_payload["status"] == "optimal"
    assert first_payload["problem_fingerprint"] == second_payload["problem_fingerprint"]
    assert first_payload["candidate_preference_vector"] == pytest.approx(
        second_payload["candidate_preference_vector"],
        abs=1.0e-6,
    )


def test_cli_evaluate_without_parent_writes_atomic_json(tmp_path: Path) -> None:
    input_path = tmp_path / "bundle.json"
    output_path = tmp_path / "evaluation.json"
    payload = _bundle_payload()
    payload["episodes"].append(_bundle_payload("run-cli-2")["episodes"][0])
    input_path.write_text(json.dumps(payload), encoding="utf-8")
    assert inverse_cli.main(
        [
            "evaluate",
            "--domain",
            "ranking_v1",
            "--input",
            str(input_path),
            "--output",
            str(output_path),
        ]
    ) == 0
    output = json.loads(output_path.read_text(encoding="utf-8"))
    assert output["status"] == "evaluated"
    assert output["parent_comparison_status"] == "not_provided"
    assert list(tmp_path.glob(f".{output_path.name}.*.tmp")) == []


def test_cli_rejects_malformed_json_unknown_keys_and_naive_timestamps(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    assert inverse_cli.main(
        ["train", "--domain", "ranking_v1", "--input", str(malformed)]
    ) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"

    unknown = _bundle_payload()
    unknown["unexpected"] = True
    unknown_path = tmp_path / "unknown.json"
    unknown_path.write_text(json.dumps(unknown), encoding="utf-8")
    assert inverse_cli.main(
        ["train", "--domain", "ranking_v1", "--input", str(unknown_path)]
    ) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"

    naive = _bundle_payload()
    naive["episodes"][0]["rating_events"][0]["created_at"] = "2026-07-16T12:00:00"
    naive_path = tmp_path / "naive.json"
    naive_path.write_text(json.dumps(naive), encoding="utf-8")
    assert inverse_cli.main(
        ["train", "--domain", "ranking_v1", "--input", str(naive_path)]
    ) == 2
    assert json.loads(capsys.readouterr().out)["status"] == "invalid_input"


def test_cli_exit_code_mapping() -> None:
    assert inverse_cli._exit_code("optimal") == 0
    assert inverse_cli._exit_code("evaluated") == 0
    assert inverse_cli._exit_code("insufficient_evidence") == 0
    assert inverse_cli._exit_code("invalid_input") == 2
    assert inverse_cli._exit_code("solver_error") == 3
    assert inverse_cli._exit_code("evaluation_rejected") == 4
    assert inverse_cli._exit_code("conflict") == 4

def test_cli_rollback_cas_conflict_returns_typed_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def raise_conflict(*args: object, **kwargs: object) -> dict[str, object]:
        raise ValueError("active snapshot changed")

    monkeypatch.setattr(
        inverse_cli.sqlite_store,
        "rollback_ranking_policy",
        raise_conflict,
    )

    exit_code = inverse_cli.main(
        [
            "rollback",
            "--domain",
            "ranking_v1",
            "--expected-active",
            "stale-snapshot",
            "--target",
            "zero_residual",
            "--acted-by",
            "operator",
        ]
    )

    assert exit_code == 4
    assert json.loads(capsys.readouterr().out) == {
        "status": "conflict",
        "error_code": "active_snapshot_changed",
    }


def test_cli_lifecycle_parser_has_phase_7_commands() -> None:
    parser = inverse_cli._parser()
    assert parser.parse_args(["inspect", "--domain", "ranking_v1"]).command == "inspect"
    reject = parser.parse_args(
        ["reject", "--snapshot", "snapshot", "--acted-by", "operator", "--reason", "reason"]
    )
    assert reject.snapshot == "snapshot"
    candidate = parser.parse_args(
        ["candidate", "--domain", "ranking_v1", "--input", "bundle.json"]
    )
    assert not hasattr(candidate, "acted_by")


def test_atomic_output_failure_preserves_existing_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_path = tmp_path / "result.json"
    output_path.write_text("existing", encoding="utf-8")

    def fail_replace(source: str | Path, destination: str | Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(inverse_cli.os, "replace", fail_replace)
    with pytest.raises(OSError, match="replace failed"):
        inverse_cli._emit_payload({"status": "optimal"}, output_path)
    assert output_path.read_text(encoding="utf-8") == "existing"
    assert list(tmp_path.glob(f".{output_path.name}.*.tmp")) == []



def test_cli_golden_result_serialization_is_byte_identical() -> None:
    payload = {"status": "optimal", "candidate_preference_vector": [0.25, -0.25]}
    assert inverse_cli._canonical_json(payload) == inverse_cli._canonical_json(payload)
