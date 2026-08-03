from __future__ import annotations

import copy

import pytest

from fitcv.candidate import canonical_candidate_checksum
from fitcv.candidate_ingest import ingest_candidate_source
from fitcv.llm_runtime import (
    LlmAdapterResponse,
    LlmRuntimeFailure,
    LlmRuntimeProvenance,
    LlmRuntimeResult,
    LlmValidationResult,
)
from fitcv_cp.candidate_profile_service import (
    CandidateProfileServiceError,
    apply_review_operations,
    approve_review,
    assemble_confirmation,
    build_baseline_review,
    build_derived_review,
    invalidation_for_stage,
    regenerate_review,
    resolve_regeneration_targets,
    retry_failed_stage,
)


def _success(value: dict) -> LlmRuntimeResult:
    response = LlmAdapterResponse(
        adapter="fake",
        runtime_path="fitcv_llm_fake",
        raw_text="{}",
        provider_payload={"model": "test-model", "secret": "not-projected"},
    )
    return LlmRuntimeResult(
        status="succeeded",
        parsed_value=value,
        validation=LlmValidationResult(valid=True, errors=[], details={}),
        failure=None,
        provenance=LlmRuntimeProvenance(
            routing_part="candidate_profile_base_mapping",
            runtime_path="fitcv_llm_fake",
            adapter="fake",
            provider="openai_compatible",
            model="test-model",
            wire_api="responses",
            attempt_count=1,
            response_id=None,
            trace_id=None,
            latency_ms=1,
        ),
        adapter_response=response,
    )


def _failure(stage: str = "adapter") -> LlmRuntimeResult:
    return LlmRuntimeResult(
        status="failed",
        parsed_value=None,
        validation=None,
        failure=LlmRuntimeFailure(stage=stage, code="adapter_timeout", message="timeout", retryable=True),
        provenance=LlmRuntimeProvenance(
            routing_part="candidate_profile_base_mapping",
            runtime_path="fitcv_llm_fake",
            adapter="fake",
            provider="openai_compatible",
            model="test-model",
            wire_api="responses",
            attempt_count=1,
            response_id=None,
            trace_id=None,
            latency_ms=1,
        ),
        adapter_response=None,
    )


def _runner(result: LlmRuntimeResult, calls: list) -> callable:
    def run(request, *, parser, validator):
        calls.append(request)
        return result

    return run


def _baseline_with_evidence() -> dict:
    source = ingest_candidate_source("candidate.md", "text/markdown", b"# Alex Morgan\n")
    document = build_baseline_review(source, llm_runner=lambda *_args, **_kwargs: pytest.fail("LLM called")).document
    document["experiences"] = [
        {
            "id": "exp_1",
            "role": "Analyst",
            "company": "Northstar",
            "source_refs": [{"document_id": document["source_documents"][0]["id"]}],
            "evidence": [
                {
                    "id": "ev_exp_1",
                    "kind": "work_achievement",
                    "text": "Automated SQL reporting.",
                    "source_refs": [{"document_id": document["source_documents"][0]["id"]}],
                }
            ],
        }
    ]
    return document


def test_deterministic_baseline_skips_llm_when_all_blocks_resolve() -> None:
    source = ingest_candidate_source("candidate.md", "text/markdown", b"# Alex Morgan\n")

    result = build_baseline_review(source, llm_runner=lambda *_args, **_kwargs: pytest.fail("LLM called"))

    assert result.document["name"] == "Alex Morgan"
    assert result.llm_called is False
    assert result.annotations["/name"]["origin"] == "deterministic"
    assert result.annotations["/name"]["regenerable"] is False


def test_ambiguous_baseline_calls_llm_only_with_unresolved_blocks() -> None:
    source = ingest_candidate_source(
        "candidate.md",
        "text/markdown",
        b"# Alex Morgan\n\nData analyst focused on reliable reporting.\n",
    )
    paragraph_id = source.source_blocks[1]["block_id"]
    calls: list = []

    result = build_baseline_review(
        source,
        llm_runner=_runner(
            _success(
                {
                    "proposals": [
                        {
                            "path": "/summary",
                            "value": "Data analyst focused on reliable reporting.",
                            "source_block_ids": [paragraph_id],
                            "confidence": 0.91,
                        }
                    ],
                    "collections": [],
                }
            ),
            calls,
        ),
    )

    assert len(calls) == 1
    assert paragraph_id in calls[0].prompt
    assert source.source_blocks[0]["block_id"] not in calls[0].prompt
    assert result.document["summary"] == "Data analyst focused on reliable reporting."
    assert result.annotations["/summary"]["source_block_ids"] == [paragraph_id]
    assert result.runtime_evidence["status"] == "succeeded"
    assert "secret" not in str(result.runtime_evidence)


def test_baseline_llm_failure_preserves_deterministic_work() -> None:
    source = ingest_candidate_source("candidate.md", "text/markdown", b"# Alex Morgan\n\nAmbiguous text.\n")

    with pytest.raises(CandidateProfileServiceError) as error:
        build_baseline_review(source, llm_runner=_runner(_failure(), []))

    assert error.value.code == "candidate_profile_llm_unavailable"
    assert error.value.last_valid_document["name"] == "Alex Morgan"


def test_derived_claims_receive_server_ids_and_separate_evidence_refs() -> None:
    baseline = _baseline_with_evidence()
    approved = approve_review("baseline", baseline, expected_fingerprint=None)
    calls: list = []

    result = build_derived_review(
        approved,
        llm_runner=_runner(
            _success(
                {
                    "claims": [
                        {
                            "section": "skills",
                            "name": "SQL",
                            "origin": "llm_inferred",
                            "confidence": 0.96,
                            "evidence_refs": ["ev_exp_1"],
                        },
                        {
                            "section": "responsibility_themes",
                            "name": "Reporting automation",
                            "origin": "llm_inferred",
                            "confidence": 0.87,
                            "evidence_refs": ["ev_exp_1"],
                        },
                    ]
                }
            ),
            calls,
        ),
    )

    assert len(calls) == 1
    assert result.document["skills"][0]["id"].startswith("skill_")
    assert result.document["skills"][0]["evidence_refs"] == ["ev_exp_1"]
    assert result.document["responsibility_themes"][0]["evidence_refs"] == ["ev_exp_1"]
    assert result.baseline_fingerprint == approved["fingerprint"]


def test_derived_claims_reject_missing_evidence_refs() -> None:
    baseline = _baseline_with_evidence()
    approved = approve_review("baseline", baseline, expected_fingerprint=None)

    with pytest.raises(CandidateProfileServiceError) as error:
        build_derived_review(
            approved,
            llm_runner=_runner(
                _success(
                    {
                        "claims": [
                            {
                                "section": "skills",
                                "name": "Python",
                                "origin": "llm_inferred",
                                "confidence": 0.9,
                                "evidence_refs": ["ev_missing"],
                            }
                        ]
                    }
                ),
                [],
            ),
        )

    assert error.value.code == "candidate_profile_llm_output_invalid"


def test_regeneration_uses_one_target_resolver_for_both_stages() -> None:
    annotations = {
        "/summary": {"regenerable": True},
        "/name": {"regenerable": False},
    }
    assert resolve_regeneration_targets(annotations, ["*"]) == ("/summary",)
    assert resolve_regeneration_targets(annotations, ["/summary"]) == ("/summary",)
    with pytest.raises(CandidateProfileServiceError) as error:
        resolve_regeneration_targets(annotations, ["/name"])
    assert error.value.code == "candidate_profile_field_not_regenerable"

    calls: list = []
    regenerated = regenerate_review(
        "baseline",
        {"summary": "Old"},
        annotations,
        ["/summary"],
        llm_runner=_runner(
            _success(
                {
                    "proposals": [
                        {
                            "path": "/summary",
                            "value": "New",
                            "source_block_ids": [],
                            "confidence": 0.9,
                        }
                    ]
                }
            ),
            calls,
        ),
    )
    assert regenerated.document["summary"] == "New"
    assert len(calls) == 1


def test_review_patch_is_atomic_and_baseline_invalidates_all_downstream_state() -> None:
    baseline = _baseline_with_evidence()
    original = copy.deepcopy(baseline)

    updated = apply_review_operations(
        "baseline",
        baseline,
        [{"operation": "replace", "path": "/experiences/exp_1/role", "value": "Senior Analyst"}],
    )

    assert baseline == original
    assert updated["experiences"][0]["role"] == "Senior Analyst"
    assert invalidation_for_stage("baseline") == {
        "approved_baseline": True,
        "derived_draft": True,
        "approved_derived": True,
        "confirmation": True,
    }
    assert invalidation_for_stage("derived") == {"approved_derived": True, "confirmation": True}


def test_approval_and_confirmation_bind_exact_fingerprints() -> None:
    baseline = _baseline_with_evidence()
    baseline_approval = approve_review("baseline", baseline, expected_fingerprint=None)
    derived = {
        "skills": [
            {
                "id": "skill_sql",
                "name": "SQL",
                "origin": "user",
                "confidence": 1.0,
                "support_status": "supported",
                "evidence_refs": ["ev_exp_1"],
            }
        ],
        "role_families": [],
        "domain_tags": [],
        "responsibility_themes": [],
    }
    derived_approval = approve_review(
        "derived",
        derived,
        expected_fingerprint=None,
        baseline_fingerprint=baseline_approval["fingerprint"],
    )

    confirmation = assemble_confirmation("Analytics Profile", baseline_approval, derived_approval)

    canonical = confirmation["profile"]["canonical"]
    assert confirmation["profile_name"] == "Analytics Profile"
    assert confirmation["profile"]["checksum"] == canonical_candidate_checksum(canonical)
    assert canonical["skills"][0]["name"] == "SQL"

    with pytest.raises(CandidateProfileServiceError) as error:
        approve_review("baseline", baseline, expected_fingerprint="stale")
    assert error.value.code == "candidate_profile_fingerprint_conflict"


def test_confirmation_rejects_derived_snapshot_from_other_baseline() -> None:
    baseline = approve_review("baseline", _baseline_with_evidence(), expected_fingerprint=None)
    derived = approve_review(
        "derived",
        {"skills": [], "role_families": [], "domain_tags": [], "responsibility_themes": []},
        expected_fingerprint=None,
        baseline_fingerprint="other",
    )

    with pytest.raises(CandidateProfileServiceError) as error:
        assemble_confirmation("Profile", baseline, derived)

    assert error.value.code == "candidate_profile_fingerprint_conflict"


def test_retry_resumes_only_retryable_failed_stage() -> None:
    assert retry_failed_stage({"stage": "derived_claims", "retryable": True}) == "deriving"
    with pytest.raises(CandidateProfileServiceError) as error:
        retry_failed_stage({"stage": "base_mapping", "retryable": False})
    assert error.value.code == "candidate_profile_transition_invalid"
