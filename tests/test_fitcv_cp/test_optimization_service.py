"""
@meta
type: test
scope: unit
domain: inverse_optimization
covers:
  - shared candidate orchestration
  - stale evidence and parent compare tokens
excludes:
  - HTTP rendering
  - live solver execution
tags:
  - fast
  - ci-safe
"""

from types import SimpleNamespace
from typing import Any, cast

from fitcv.config import load_config
from fitcv.inverse_optimization import InverseOptimizationRequest
import fitcv_cp.optimization_service as service_module
from fitcv_cp.optimization_service import create_ranking_policy_candidate
from fitcv_cp.store import ControlPlaneStore


def test_candidate_rejects_submitted_stale_evidence_before_solving() -> None:
    request = InverseOptimizationRequest(
        schema_version="inverse_optimization_request_v1",
        domain_id="ranking_v1",
        event_watermark=0,
        episodes=(),
    )
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda domain_id: {
            "schema_version": "decision_evidence_head_v1",
            "domain_id": domain_id,
            "event_watermark": 0,
            "episodes": [],
            "evidence_head_fingerprint": "current-head",
        }
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config={},
        expected_evidence_head_fingerprint="stale-head",
    )

    assert result == {"status": "stale", "error_code": "stale_evidence"}


def test_candidate_rejects_changed_parent_before_solving(monkeypatch: Any) -> None:
    first = SimpleNamespace(
        baseline_policy_fingerprint="baseline",
        ranking_contract_fingerprint="ranking-contract",
        embedding_model="embedding-model",
        embedding_dimension=2,
        embedding_contract_fingerprint="embedding-contract",
    )
    request = cast(
        InverseOptimizationRequest,
        SimpleNamespace(
            domain_id="ranking_v1",
            episodes=(SimpleNamespace(episode=first),),
        ),
    )
    monkeypatch.setattr(
        service_module,
        "_request_evidence_head",
        lambda _request: {"evidence_head_fingerprint": "current-head"},
    )
    monkeypatch.setattr(
        service_module,
        "solve_preference_residual",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("solver called")),
    )
    store = ControlPlaneStore(
        get_decision_evidence_head_fn=lambda domain_id: {
            "domain_id": domain_id,
            "evidence_head_fingerprint": "current-head",
        },
        resolve_active_ranking_policy_fn=lambda domain_id, runtime_fingerprint: {
            "policy_snapshot_id": "active-snapshot",
            "preference_vector_json": [0.0, 0.0],
        },
    )

    result = create_ranking_policy_candidate(
        request,
        store=store,
        config=load_config(),
        expected_evidence_head_fingerprint="current-head",
        expected_parent_ref="zero_residual:baseline",
    )

    assert result == {"status": "stale", "error_code": "candidate_parent_changed"}
