"""@meta
name: pipeline_stage_runner
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.location-language-eligibility
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Execute isolated pipeline stage runner helpers used by orchestrator.
inputs:
  - Pipeline state, config, and stage dependency callbacks
outputs:
  - Mutated pipeline state and stage side effects
lifecycle:
  - status: active
"""

from __future__ import annotations

import hashlib
import json
import time
from copy import deepcopy
from types import SimpleNamespace
from typing import Any, Callable, Mapping

from fitcv.fit_factors import build_candidate_fit_context
from fitcv.config import (
    resolve_retrieval_strategy,
    resolve_shortlist_policy,
    resolve_shortlist_shadow_enabled,
    resolve_shortlist_strategy,
)
from fitcv.ai_score import build_ranking_input_diagnostics, build_ranking_job_input
from fitcv.evidence import build_evidence_projection, retrieve_evidence_bundle, select_ranking_evidence
from fitcv.semantic_snapshot import compile_semantic_policy
from fitcv.pipeline_stages.common import primary_job_identity_key
from fitcv.rule_filter import (
    SHORTLIST_ELIGIBILITY_POLICY_VERSION,
    shortlist_filter_disposition,
)
from fitcv.ranking_contract import AI_ONLY_RANKING_ORDER_VERSION, SCORE_STATUS_VALID, normalize_score_state
from fitcv.contracts import build_stage_6_to_7_handoff
from fitcv.preference_policy import (
    PreferenceRuntimeContract,
    ResolvedPreferencePolicy,
    resolve_run_preference_policy,
    resolved_preference_policy_to_dict,
)
from fitcv.runtime_routing import resolve_llm_routing
from fitcv.vector_search import VECTOR_RETRIEVAL_STRATEGY

def _reuse_stage_enabled(config: dict[str, Any], stage: str) -> bool:
    reuse_block = dict(config.get("reuse") or {})
    stage_block = dict(reuse_block.get(str(stage or "").strip()) or {})
    return bool(stage_block.get("enabled", True))


def _stage5_evidence_payload(row: Mapping[str, Any], evidence_items: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Carry the admission evidence into Stage 6 without recomputing it."""
    coverage = row.get("coverage") or row.get("coverage_summary") or {}
    source_items = evidence_items or [dict(item) for item in row.get("requirement_coverage") or [] if isinstance(item, Mapping)]
    evidence = [dict(item) for item in source_items if isinstance(item, Mapping)]
    qualifiers = [
        item for item in evidence
        if str(item.get("qualifier_status") or "").strip()
    ]
    gaps = [
        dict(state)
        for state in coverage.get("states") or []
        if isinstance(state, Mapping)
        and (str(state.get("state") or "") in {"E", "U"} or state.get("contradiction") or state.get("qualifier_failure"))
    ]
    return evidence, qualifiers, gaps

def _execute_requirement_aware_shortlist_stage(
    *,
    run_id: str,
    state: dict[str, Any],
    profile: dict[str, Any],
    passed_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    reporter: Any | None,
    pipeline_store: Any,
    set_span_attributes: Callable[[dict[str, Any]], None],
    persist: bool = True,
) -> tuple[list[dict[str, Any]], str, dict[str, Any], dict[str, Any]]:
    from fitcv.shortlist_selection import build_requirement_aware_rows, select_requirement_aware_jobs

    evidence_by_job: dict[str, list[dict[str, Any]]] = {}
    evidence_projection = build_evidence_projection(profile)
    assessment_failures = 0
    for job in passed_jobs:
        identity = str(job.get("canonical_job_identity") or job.get("job_url") or "").strip()
        if isinstance(job.get("requirement_coverage"), list) and job.get("requirement_coverage"):
            evidence_by_job[identity] = []
            continue
        try:
            bundle = retrieve_evidence_bundle(
                profile,
                job,
                max(3, len(evidence_projection.get("items") or [])),
                config=config,
                evidence_projection=evidence_projection,
            )
            assessment_items = [
                *(bundle.get("selected_evidence") or []),
                *(bundle.get("unselected_top_candidates") or []),
            ]
            rows: list[dict[str, Any]] = []
            for item in assessment_items:
                evidence_id = str(item.get("evidence_id") or "").strip()
                for requirement_id, assessment in dict(item.get("requirement_assessments") or {}).items():
                    rows.append(
                        {
                            "requirement_id": requirement_id,
                            "support_status": "supported" if assessment.get("qualified_support") else "partial" if assessment.get("canonical_match") else "unsupported",
                            "qualifier_status": assessment.get("qualifier_status"),
                            "evidence_id": evidence_id,
                            "reviewed": True,
                            "contradiction": assessment.get("qualifier_status") == "contradicted",
                            "provenance_grade": 2,
                        }
                    )
            evidence_by_job[identity] = rows
        except Exception:
            assessment_failures += 1
            evidence_by_job[identity] = []

    rows = build_requirement_aware_rows(
        passed_jobs,
        evidence_by_job,
        assessment_complete=assessment_failures == 0,
    )
    decision = select_requirement_aware_jobs(rows)
    assessment_input = {
        "profile_revision": str(profile.get("revision") or ""),
        "evidence_projection_fingerprint": str(evidence_projection.get("fingerprint") or ""),
        "requirement_contract_version": decision["requirement_contract_version"],
        "retrieval_strategy": resolve_retrieval_strategy(config),
        "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
        "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
        "policy_version": decision["policy_version"],
    }
    assessment_input_fingerprint = hashlib.sha256(
        json.dumps(assessment_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    admitted = []
    for row in decision["admitted"]:
        identity = str(row.get("canonical_job_identity") or row.get("job_url") or "").strip()
        stage5_evidence, qualifiers, gaps = _stage5_evidence_payload(
            row,
            list(evidence_by_job.get(identity) or []),
        )
        admitted.append(
            {
                **row,
                "shortlist_origin": "requirement_aware",
                "shortlist_status": "shortlist_admitted",
                "admission_capacity": decision["admission_capacity"],
                "shortlist_strategy": "core_pareto_evidence_v1",
                "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
                "stage5_admission": {
                    "admitted": True,
                    "status": "admitted",
                    "source": "stage5_shortlist",
                    "strategy": "core_pareto_evidence_v1",
                    "admission_rank": row.get("admission_rank"),
                    "pareto_front": row.get("pareto_front"),
                    "decision_fingerprint": decision.get("decision_fingerprint"),
                },
                "stage5_evidence": stage5_evidence,
                "qualifiers": qualifiers,
                "gaps": gaps,
            }
        )
    if persist:
        pipeline_store.store_shortlist(admitted, config)
    ledger_rows = [
        {
            **row,
            "identity": row.get("canonical_job_identity") or row.get("job_url"),
            "job_url": row.get("job_url"),
            "shortlist_status": "shortlist_admitted" if row.get("admitted") else "not_admitted",
            "raw_hit_present": False,
            "admission_reason": row.get("admission_reason"),
            "exclusion_reason": row.get("exclusion_reason"),
            "shortlist_strategy": "core_pareto_evidence_v1",
            "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
            "policy_version": decision["policy_version"],
            "evaluation_pool_id": decision["evaluation_pool_id"],
            "admission_capacity": decision["admission_capacity"],
        }
        for row in decision["rows"]
    ]
    diagnostics = {
        "shortlist_strategy": "core_pareto_evidence_v1",
        "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
        "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
        "policy_version": decision["policy_version"],
        "requirement_contract_version": decision["requirement_contract_version"],
        "admission_capacity": decision["admission_capacity"],
        "evaluation_pool_size": len(rows),
        "evaluation_pool_id": decision["evaluation_pool_id"],
        "decision_fingerprint": decision["decision_fingerprint"],
        "assessment_fingerprint": decision["assessment_fingerprint"],
        "assessment_input": assessment_input,
        "assessment_input_fingerprint": assessment_input_fingerprint,
        "assessment_failures": assessment_failures,
    }
    persist_ledger = getattr(pipeline_store, "store_shortlist_admission_ledger", None)
    if persist and persist_ledger is not None:
        persist_ledger(ledger_rows, diagnostics, run_id, config)
    state["raw_shortlist"] = admitted
    state["shortlist"] = admitted
    state["shortlist_diagnostics"] = diagnostics
    state["shortlist_admission_manifest"] = {
        "contract_version": "shortlist_admission_manifest_v2",
        "strategy": "core_pareto_evidence_v1",
        "eligibility_policy": diagnostics["eligibility_policy"],
        "evaluation_pool_id": decision["evaluation_pool_id"],
        "assessment_fingerprint": decision["assessment_fingerprint"],
        "assessment_input_fingerprint": assessment_input_fingerprint,
        "counts": {"eligible": len(rows), "admitted": len(admitted), "not_admitted": len(rows) - len(admitted)},
        "rows": ledger_rows,
    }
    if reporter is not None:
        reporter.emit("layer3_shortlist", "info", f"Requirement-aware shortlist: {len(admitted)} admitted")  # type: ignore[union-attr]
    set_span_attributes({"passed_jobs": len(passed_jobs), "shortlist_jobs": len(admitted), "evaluation_pool_jobs": len(rows)})
    return admitted, "", {}, {}

def execute_normalize_stage(
    *,
    run_id: str,
    jobs_path: str,
    state: dict[str, Any],
    pipeline_store: Any,
    config: dict[str, Any],
    reporter: Any | None,
    observe_span: Callable[..., Any],
    set_span_attributes: Callable[[dict[str, Any]], None],
    parse_jobs_file: Callable[[str], list[dict[str, Any]]],
    normalize_batch: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    normalize_batch_with_exclusions: Callable[[list[dict[str, Any]]], tuple[Any, list[dict[str, Any]]]],
    prepare_raw_rows: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> None:
    with observe_span("pipeline.normalize", attributes={"run_id": run_id}):
        raw_jobs = parse_jobs_file(jobs_path)
        normalized = normalize_batch(raw_jobs)
        _normalized_with_exclusions, deduplicated_jobs = normalize_batch_with_exclusions(raw_jobs)
        if reporter is not None:
            reporter.emit(  # type: ignore[union-attr]
                "layer1_normalize",
                "info",
                f"Normalization dedupe: kept {len(normalized)} of {len(raw_jobs)} jobs, removed {len(deduplicated_jobs)} duplicate(s)",
            )

        raw_rows = prepare_raw_rows(raw_jobs)
        pipeline_store.load_raw_jobs(raw_rows, config)
        state["raw_jobs"] = raw_jobs
        state["normalized"] = normalized
        state["deduplicated_jobs"] = deduplicated_jobs
        set_span_attributes(
            {
                "input_jobs": len(raw_jobs),
                "normalized_jobs": len(normalized),
                "deduplicated_jobs": len(deduplicated_jobs),
            }
        )


def execute_enrich_stage(
    *,
    run_id: str,
    state: dict[str, Any],
    config: dict[str, Any],
    reporter: Any | None,
    pipeline_store: Any,
    observe_span: Callable[..., Any],
    set_span_attributes: Callable[[dict[str, Any]], None],
    cancellation_check: Callable[[], bool] | None,
    cancellation_error_cls: type[Exception],
    enrich_jobs_with_reuse: Callable[..., tuple[list[dict[str, Any]], list[dict[str, Any]]]],
    apply_pre_enrichment_global_filters: Callable[[list[dict[str, Any]], dict[str, Any] | None], dict[str, Any]],
    fresh_enrichment_status: str,
    reused_cached_enrichment_status: str,
) -> None:
    normalized = list(state["normalized"])
    raw_jobs = list(state["raw_jobs"])
    with observe_span("pipeline.enrich", attributes={"run_id": run_id}):
        raw_global = config.get("global_job_filters", {})
        global_settings = (
            {f"global_job_filters.{k}": v for k, v in raw_global.items()}
            if raw_global else None
        )
        pre_filter = apply_pre_enrichment_global_filters(normalized, global_settings)
        pre_filter_passed_urls: set[str] = set(pre_filter["passed"])
        surviving_normalized = [
            j for j in normalized
            if str(j.get("job_url", "")) in pre_filter_passed_urls
        ]
        pre_filter_rejected_jobs = list(pre_filter["rejected"])
        if reporter is not None:
            n_pre_rejected = len(normalized) - len(surviving_normalized)
            reporter.emit(  # type: ignore[union-attr]
                "layer1b_pre_filter", "info",
                f"Pre-enrichment filter: {len(surviving_normalized)} pass, {n_pre_rejected} rejected",
            )

        if cancellation_check and cancellation_check():
            raise cancellation_error_cls("Cancelled before enrichment")
        enriched, fresh_enriched_rows = enrich_jobs_with_reuse(
            surviving_normalized,
            config,
            pipeline_store=pipeline_store,
        )
        if fresh_enriched_rows:
            pipeline_store.load_structured_jobs(fresh_enriched_rows, config)
        pipeline_store.load_run_structured_jobs(enriched, run_id, config)
        reused_count = sum(
            1 for row in enriched
            if str(row.get("enrich_reuse_status") or "") == reused_cached_enrichment_status
        )
        fresh_count = sum(
            1 for row in enriched
            if str(row.get("enrich_reuse_status") or "") == fresh_enrichment_status
        )
        if reporter is not None:
            reporter.emit(  # type: ignore[union-attr]
                "layer1_jobs", "info",
                (
                    f"Ingested {len(raw_jobs)} jobs, enriched {len(enriched)} "
                    f"(after pre-filter; fresh={fresh_count}, reused={reused_count})"
                ),
            )
        state["pre_filter_rejected_jobs"] = pre_filter_rejected_jobs
        state["enriched"] = enriched
        set_span_attributes(
            {
                "normalized_jobs": len(normalized),
                "pre_filter_rejected": len(pre_filter_rejected_jobs),
                "enriched_jobs": len(enriched),
                "fresh_enriched": fresh_count,
                "reused_enriched": reused_count,
            }
        )


def merge_passed_filter_records(
    enriched_jobs: list[dict[str, Any]],
    filter_result: dict[str, Any],
) -> list[dict[str, Any]]:
    passed_records_by_url = {
        str(item.get("job_url") or ""): item
        for item in filter_result.get("passed_records", [])
        if str(item.get("job_url") or "")
    }
    enriched_by_url = {
        str(job.get("job_url") or ""): job
        for job in enriched_jobs
        if str(job.get("job_url") or "")
    }
    return [
        {
            **enriched_by_url[job_url],
            "marks": [],
            **passed_records_by_url.get(job_url, {}),
        }
        for raw_job_url in filter_result.get("passed", [])
        if (job_url := str(raw_job_url or "")) in enriched_by_url
    ]


def build_recall_safe_evaluation_pool(
    enriched_jobs: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
    rejected_jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retain passed jobs and only soft-filter exclusions for requirement assessment."""
    passed_by_url = {
        str(job.get("job_url") or "").strip(): dict(job)
        for job in passed_jobs
        if str(job.get("job_url") or "").strip()
    }
    rejected_by_url = {
        str(item.get("job_url") or "").strip(): dict(item)
        for item in rejected_jobs
        if str(item.get("job_url") or "").strip()
    }
    pool: list[dict[str, Any]] = []
    for source_job in enriched_jobs:
        job_url = str(source_job.get("job_url") or "").strip()
        if not job_url:
            continue
        if job_url in passed_by_url:
            pool.append(
                {
                    **passed_by_url[job_url],
                    "legacy_eligibility": "passed",
                    "legacy_exclusion_reasons": [],
                    "evaluation_pool_reason": "legacy_passed",
                    "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
                }
            )
            continue
        rejection = rejected_by_url.get(job_url)
        reasons = [str(reason) for reason in (rejection or {}).get("reasons", []) if str(reason)]
        if not reasons or shortlist_filter_disposition(reasons) != "soft_exclusion":
            continue
        pool.append(
            {
                **dict(source_job),
                "marks": list((rejection or {}).get("marks") or []),
                "legacy_eligibility": "excluded",
                "legacy_exclusion_reasons": reasons,
                "legacy_excluded": True,
                "evaluation_pool_reason": "soft_filter_exclusion",
                "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
            }
        )
    return pool

def execute_rule_filter_stage(
    *,
    run_id: str,
    state: dict[str, Any],
    config: dict[str, Any],
    reporter: Any | None,
    pipeline_store: Any,
    observe_span: Callable[..., Any],
    set_span_attributes: Callable[[dict[str, Any]], None],
    load_profile_json_text: Callable[[str], dict[str, Any]],
    load_profile_yaml: Callable[[str], dict[str, Any]],
    flatten_skills: Callable[[dict[str, Any]], list[str]],
    apply_rule_filters: Callable[..., dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    pre_filter_rejected_jobs = list(state["pre_filter_rejected_jobs"])
    enriched = list(state["enriched"])
    with observe_span("pipeline.rule_filter", attributes={"run_id": run_id}):
        runtime_profile_json: str | None = (
            config.get("runtime_inputs", {}).get("candidate_profile_json")
        )
        if runtime_profile_json:
            profile = load_profile_json_text(runtime_profile_json)
        else:
            profile_path: str = str(config["paths"]["candidate_profile"])
            profile = load_profile_yaml(profile_path)
        pipeline_store.load_candidate_profile(profile, config)
        candidate_skill_names = flatten_skills(profile)
        if reporter is not None:
            reporter.emit("layer2_candidate", "info", "Candidate profile loaded")  # type: ignore[union-attr]

        candidate_fit_context = build_candidate_fit_context(
            profile,
            valid_work_modes=list(config.get("valid_location_types") or []),
        )
        filter_result = apply_rule_filters(
            enriched,
            profile["preferences"],
            config,
            candidate_fit_context=candidate_fit_context,
        )
        combined_filter_result = {
            "passed": filter_result["passed"],
            "passed_records": filter_result.get("passed_records", []),
            "rejected": pre_filter_rejected_jobs + filter_result["rejected"],
        }
        passed_jobs = merge_passed_filter_records(enriched, filter_result)
        candidate_filter_rejected_jobs = list(filter_result["rejected"])
        state["recall_safe_evaluation_pool"] = build_recall_safe_evaluation_pool(
            enriched,
            passed_jobs,
            candidate_filter_rejected_jobs,
        )
        pipeline_store.store_filter_results(combined_filter_result, run_id, config)
        if reporter is not None:
            reporter.emit("layer3_filter", "info", f"{len(passed_jobs)} passed rule filter")  # type: ignore[union-attr]
        state["passed_jobs"] = passed_jobs
        state["candidate_filter_rejected_jobs"] = candidate_filter_rejected_jobs
        state["recall_safe_evaluation_pool"] = build_recall_safe_evaluation_pool(
            enriched,
            passed_jobs,
            candidate_filter_rejected_jobs,
        )
        set_span_attributes(
            {
                "candidate_skills": len(candidate_skill_names),
                "passed_jobs": len(passed_jobs),
                "candidate_filter_rejected": len(candidate_filter_rejected_jobs),
                "recall_safe_evaluation_pool": len(state["recall_safe_evaluation_pool"]),
            }
        )
    return profile, candidate_skill_names


def execute_shortlist_stage(
    *,
    run_id: str,
    state: dict[str, Any],
    profile: dict[str, Any],
    passed_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    vector_top_n: int,
    reporter: Any | None,
    pipeline_store: Any,
    observe_span: Callable[..., Any],
    set_span_attributes: Callable[[dict[str, Any]], None],
    run_vector_search: Callable[..., Any],
    materialize_scoring_shortlist: Callable[[list[dict[str, Any]], list[dict[str, Any]]], list[dict[str, Any]]],
    unique_job_urls: Callable[[list[dict[str, Any]]], list[str]],
    raw_shortlist_anomaly_urls: Callable[[list[dict[str, Any]], list[dict[str, Any]]], list[str]],
) -> tuple[list[dict[str, Any]], str, dict[str, Any], dict[str, Any]]:
    evaluation_pool = list(state.get("recall_safe_evaluation_pool") or passed_jobs)
    if resolve_shortlist_strategy(config) == "core_pareto_evidence_v1":
        with observe_span("pipeline.shortlist", attributes={"run_id": run_id, "strategy": "core_pareto_evidence_v1"}):
            result = _execute_requirement_aware_shortlist_stage(
                run_id=run_id,
                state=state,
                profile=profile,
                passed_jobs=evaluation_pool,
                config=config,
                reporter=reporter,
                pipeline_store=pipeline_store,
                set_span_attributes=set_span_attributes,
            )
            pipeline_store.store_shortlist(result[0], config)
            return result
    with observe_span("pipeline.shortlist", attributes={"run_id": run_id, "vector_top_n": vector_top_n}):
        effective_strategy = resolve_retrieval_strategy(config)
        if effective_strategy != "lexical_v1":
            pipeline_store.embed_and_store_jobs(passed_jobs, config)
        raw_shortlist_result = run_vector_search(
            profile,
            [str(job.get("job_url") or "") for job in passed_jobs],
            config,
            top_n=vector_top_n,
            structured_jobs=passed_jobs,
            requested_strategy=effective_strategy,
        )
        raw_shortlist = list(raw_shortlist_result.get("production_rows") or [])
        audit_rows = list(raw_shortlist_result.get("audit_rows") or [])
        shortlist_diagnostics = dict(raw_shortlist_result.get("diagnostics") or {})
        candidate_query_record = dict(raw_shortlist_result.get("candidate_query") or {})

        if resolve_shortlist_shadow_enabled(config):
            shadow_state: dict[str, Any] = {}
            shadow_pool = list(state.get("recall_safe_evaluation_pool") or passed_jobs)
            if effective_strategy != "lexical_v1":
                pipeline_store.embed_and_store_jobs(shadow_pool, config)
            shadow_legacy_result = run_vector_search(
                profile,
                [str(job.get("job_url") or "") for job in shadow_pool],
                config,
                top_n=vector_top_n,
                structured_jobs=shadow_pool,
                requested_strategy=effective_strategy,
            )
            shadow_legacy_rows = list(shadow_legacy_result.get("production_rows") or [])
            _execute_requirement_aware_shortlist_stage(
                run_id=run_id,
                state=shadow_state,
                profile=profile,
                passed_jobs=shadow_pool,
                config={"pipeline": {**dict(config.get("pipeline") or {}), "shortlist_strategy": "core_pareto_evidence_v1"}},
                reporter=None,
                pipeline_store=SimpleNamespace(store_shortlist=lambda rows, config: None),
                set_span_attributes=lambda attributes: None,
                persist=False,
            )
            shadow_manifest = dict(shadow_state.get("shortlist_admission_manifest") or {})
            legacy_ids = {str(row.get("job_url") or "") for row in shadow_legacy_rows}
            shadow_ids = {str(row.get("job_url") or "") for row in shadow_state.get("shortlist") or []}
            shortlist_diagnostics["shadow"] = {
                "authoritative": False,
                "evaluation_pool_source": "state.recall_safe_evaluation_pool" if state.get("recall_safe_evaluation_pool") else "legacy_passed_jobs",
                "evaluation_pool_id": shadow_manifest.get("evaluation_pool_id"),
                "assessment_fingerprint": (shadow_state.get("shortlist_diagnostics") or {}).get("assessment_fingerprint"),
                "legacy_admitted": len(legacy_ids),
                "requirement_aware_admitted": len(shadow_ids),
                "disagreement_count": len(legacy_ids ^ shadow_ids),
                "legacy_excluded": sum(1 for row in shadow_pool if row.get("legacy_excluded")),
            }

        from fitcv.vector_search import (
            build_candidate_query_components,
            build_candidate_query_embedding_contract_fingerprint,
            build_candidate_query_signature_record,
            build_candidate_query_text,
        )

        candidate_query_components = dict(
            candidate_query_record.get("components") or build_candidate_query_components(profile, config)
        )
        candidate_summary = str(
            candidate_query_record.get("text") or build_candidate_query_text(profile, config)
        )
        signature_record = build_candidate_query_signature_record(candidate_query_components)
        contract_record = build_candidate_query_embedding_contract_fingerprint(config)
        candidate_query_debug = {
            "candidate_query_reuse_status": str(
                candidate_query_record.get("candidate_query_reuse_status") or ""
            ),
            "candidate_query_signature": str(
                candidate_query_record.get("candidate_query_signature") or signature_record["signature"]
            ),
            "candidate_query_contract_fingerprint": str(
                candidate_query_record.get("candidate_query_contract_fingerprint")
                or contract_record["fingerprint"]
            ),
        }
        shortlist_fail_fast = bool((config.get("pipeline", {}) or {}).get("shortlist_fail_fast_empty_raw_hits", False))
        if shortlist_fail_fast and passed_jobs and not raw_shortlist:
            raise RuntimeError(
                "Vector shortlist returned zero raw hits for non-empty passed jobs; fail-fast guard active"
            )
        shortlist = materialize_scoring_shortlist(raw_shortlist, passed_jobs)
        pipeline_store.store_shortlist(shortlist, config)
        raw_shortlist_urls = set(unique_job_urls(raw_shortlist))
        shortlist_urls = set(unique_job_urls(shortlist))
        audit_urls = set(unique_job_urls(audit_rows))
        production_rows_by_url = {
            str(row.get("job_url") or "").strip(): row
            for row in shortlist
            if str(row.get("job_url") or "").strip()
        }
        audit_rows_by_url = {
            str(row.get("job_url") or "").strip(): row
            for row in audit_rows
            if str(row.get("job_url") or "").strip()
        }
        retrieval_rows_by_url = {**audit_rows_by_url, **production_rows_by_url}
        shortlist_admission_rows = []
        fusion_fingerprint = str(shortlist_diagnostics.get("fusion_fingerprint") or "")
        effective_strategy = str(shortlist_diagnostics.get("effective_strategy") or "")
        requested_strategy = str(shortlist_diagnostics.get("requested_strategy") or "")
        for input_index, job in enumerate(passed_jobs):
            job_url = str(job.get("job_url") or "").strip()
            retrieval_row = retrieval_rows_by_url.get(job_url) or {}
            is_admitted = job_url in shortlist_urls
            raw_hit_present = job_url in raw_shortlist_urls or job_url in audit_urls
            shortlist_admission_rows.append(
                {
                    "identity": primary_job_identity_key(job) or job_url,
                    "job_url": job_url,
                    "input_index": input_index,
                    "shortlist_status": "shortlist_admitted" if is_admitted else "not_returned_in_raw_hits",
                    "raw_hit_present": raw_hit_present,
                    "audited": job_url in audit_urls,
                    "admission_order": (
                        next(
                            (index for index, row in enumerate(shortlist) if str(row.get("job_url") or "").strip() == job_url),
                            None,
                        )
                        if is_admitted
                        else None
                    ),
                    "shortlist_origin": str(retrieval_row.get("shortlist_origin") or ""),
                    "retrieval_strategy": str(retrieval_row.get("retrieval_strategy") or shortlist_diagnostics.get("effective_strategy") or ""),
                    "vector_rank": retrieval_row.get("vector_rank"),
                    "vector_similarity": retrieval_row.get("vector_similarity"),
                    "lexical_rank": retrieval_row.get("lexical_rank"),
                    "lexical_score": retrieval_row.get("lexical_score"),
                    "requested_strategy": requested_strategy,
                    "effective_strategy": effective_strategy,
                    "fusion_fingerprint": fusion_fingerprint,
                    "admission_reason": "within_fused_cutoff" if is_admitted else None,
                    "exclusion_reason": (
                        "after_fused_cutoff" if job_url in audit_urls else "not_returned_in_raw_hits"
                    ) if not is_admitted else None,
                }
            )
        audit_sample_n = max(0, int((config.get("pipeline") or {}).get("shortlist_audit_sample_n", 0)))

        def bounded_sample(status: str | None = None) -> list[dict[str, Any]]:
            rows = [
                row for row in shortlist_admission_rows
                if status is None or row.get("shortlist_status") == status
            ]
            return sorted(rows, key=lambda row: (str(row.get("job_url") or ""), int(row.get("input_index") or 0)))[:audit_sample_n]

        admitted_sample = bounded_sample("shortlist_admitted")
        below_cutoff_sample = [
            row for row in sorted(
                shortlist_admission_rows,
                key=lambda item: (str(item.get("job_url") or ""), int(item.get("input_index") or 0)),
            )
            if row.get("exclusion_reason") == "after_fused_cutoff"
        ][:audit_sample_n]
        not_returned_sample = bounded_sample("not_returned_in_raw_hits")
        state["shortlist_admission_manifest"] = {
            "contract_version": "shortlist_admission_manifest_v1",
            "counts": {
                "eligible": len(passed_jobs),
                "raw_retrieved": len(raw_shortlist_urls),
                "audited": len(audit_urls),
                "admitted": len(shortlist_urls),
                "after_fused_cutoff": sum(1 for row in shortlist_admission_rows if row.get("exclusion_reason") == "after_fused_cutoff"),
                "not_returned": sum(1 for row in shortlist_admission_rows if row["shortlist_status"] == "not_returned_in_raw_hits"),
            },
            "retrieval": {
                "requested_strategy": shortlist_diagnostics.get("requested_strategy"),
                "effective_strategy": shortlist_diagnostics.get("effective_strategy"),
                "fallback_reason": shortlist_diagnostics.get("fallback_reason"),
                "fusion_fingerprint": shortlist_diagnostics.get("fusion_fingerprint"),
            },
            "sample_limit": audit_sample_n,
            "rows": admitted_sample,
            "admitted_sample": admitted_sample,
            "audit_sample": below_cutoff_sample,
            "not_returned_sample": not_returned_sample,
        }
        persist_ledger = getattr(pipeline_store, "store_shortlist_admission_ledger", None)
        if persist_ledger is not None:
            persist_ledger(shortlist_admission_rows, shortlist_diagnostics, run_id, config)
        raw_shortlist_anomaly_rows = raw_shortlist_anomaly_urls(raw_shortlist, passed_jobs)
        if reporter is not None:
            shortlist_message = f"Vector shortlist: {len(raw_shortlist_urls)} raw hits"
            if raw_shortlist_anomaly_rows:
                shortlist_message += f", {len(raw_shortlist_anomaly_rows)} raw-hit anomalies"
            reporter.emit("layer3_shortlist", "info", shortlist_message)  # type: ignore[union-attr]
        state["raw_shortlist"] = raw_shortlist
        state["shortlist"] = shortlist
        state["shortlist_diagnostics"] = shortlist_diagnostics
        state["_shortlist_audit_rows"] = audit_rows
        state["candidate_query_debug"] = candidate_query_debug
        set_span_attributes(
            {
                "passed_jobs": len(passed_jobs),
                "raw_shortlist_hits": len(raw_shortlist_urls),
                "shortlist_jobs": len(shortlist),
                "shortlist_audit_rows": len(audit_rows),
            }
        )
    return raw_shortlist, candidate_summary, candidate_query_components, candidate_query_debug


def execute_ranking_stage(
    *,
    run_id: str,
    state: dict[str, Any],
    shortlist: list[dict[str, Any]],
    candidate_summary: str,
    profile: dict[str, Any],
    config: dict[str, Any],
    final_top_n: int,
    reporter: Any | None,
    pipeline_store: Any,
    observe_span: Callable[..., Any],
    set_span_attributes: Callable[[dict[str, Any]], None],
    cancellation_check: Callable[[], bool] | None,
    cancellation_error_cls: type[Exception],
    ranking_ai_score_reuse_index: dict[str, dict[str, Any]],
    build_ai_score_input_fingerprint: Callable[..., dict[str, Any]],
    extract_job_url: Callable[[dict[str, Any]], str],
    run_ai_scoring: Callable[..., list[dict[str, Any]]],
    build_ranking_features: Callable[..., list[dict[str, Any]]],
    rank_jobs: Callable[..., list[dict[str, Any]]],
    preference_policy_resolver: Callable[
        [PreferenceRuntimeContract], ResolvedPreferencePolicy
    ]
    | None = None,
    profile_for_projection: dict[str, Any] | None = None,
    evidence_projection: dict[str, Any] | None = None,
    runtime_observation_callback: Callable[[dict[str, Any]], None] | None = None,
    build_reuse_decision_callback: Callable[..., dict[str, Any]] | None = None,
    resolve_llm_routing_callback: Callable[..., Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with observe_span("pipeline.ai_score", attributes={"run_id": run_id}):
        try:
            resolved_route = (
                resolve_llm_routing_callback or resolve_llm_routing
            )("ranking_ai_score", runtime_config=config)
        except Exception:
            resolved_route = None
        ai_top_n = int(config["pipeline"]["ai_score_top_n"])
        ranking_reuse_enabled = _reuse_stage_enabled(config, "ranking")
        if cancellation_check and cancellation_check():
            raise cancellation_error_cls("Cancelled before AI scoring")
        ai_score_candidates = shortlist[:ai_top_n]
        evidence_projection = evidence_projection or build_evidence_projection(
            profile if profile_for_projection is None else profile_for_projection
        )
        profile_evidence_pool = list(evidence_projection.get("items") or [])
        semantic_policy = config.get("semantic_policy")
        if not isinstance(semantic_policy, dict):
            semantic_policy = compile_semantic_policy(config)
        retrieval_metadata = dict(state.get("shortlist_diagnostics") or {})
        fresh_scoring_jobs: list[dict[str, Any]] = []
        fresh_ai_score_fingerprints: dict[str, str] = {}
        reused_ai_scores_by_identity: dict[str, dict[str, Any]] = {}
        ranking_inputs_by_identity: dict[str, dict[str, Any]] = {}
        ranking_input_diagnostics_by_identity: dict[str, dict[str, Any]] = {}
        ranking_admission_rows: dict[str, dict[str, Any]] = {}
        for shortlisted_job in ai_score_candidates:
            selected_evidence = select_ranking_evidence(
                profile_evidence_pool,
                shortlisted_job,
                limit=2,
                semantic_policy=semantic_policy,
            )
            ranking_profile = {**profile, "_projected_evidence_pool": selected_evidence}
            ranking_input = build_ranking_job_input(shortlisted_job, ranking_profile, config)
            identity_key = primary_job_identity_key(shortlisted_job)
            manifest_identity = identity_key or extract_job_url(shortlisted_job)
            ranking_admission_rows[manifest_identity] = {
                "identity": manifest_identity,
                "job_url": extract_job_url(shortlisted_job),
                "shortlist_status": "shortlist_admitted",
                "ai_score_status": "selected",
                "score_execution": "pending",
                "request_fingerprint": "",
                "ranking_input_diagnostics": {},
            }
            if identity_key:
                ranking_inputs_by_identity[identity_key] = ranking_input
                ranking_input_diagnostics_by_identity[identity_key] = build_ranking_input_diagnostics(
                    ranking_input,
                    retrieval_metadata=retrieval_metadata,
                )
            top_evidence = [str(item.get("text") or "") for item in selected_evidence if item.get("text")]
            try:
                fingerprint_record = build_ai_score_input_fingerprint(
                    shortlisted_job,
                    candidate_summary,
                    top_evidence,
                    config,
                    ranking_input=ranking_input,
                    resolved_route=resolved_route,
                )
            except Exception:
                fingerprint_record = {"fingerprint": ""}
            if identity_key and fingerprint_record.get("request_record"):
                ranking_input_diagnostics_by_identity[identity_key] = build_ranking_input_diagnostics(
                    ranking_input,
                    fingerprint_record["request_record"],
                    retrieval_metadata=retrieval_metadata,
                )
            if manifest_identity in ranking_admission_rows:
                ranking_admission_rows[manifest_identity].update(
                    {
                        "request_fingerprint": str(fingerprint_record.get("fingerprint") or ""),
                        "ranking_input_diagnostics": deepcopy(
                            ranking_input_diagnostics_by_identity.get(manifest_identity) or {}
                        ),
                    }
                )
            job_url = extract_job_url(shortlisted_job)
            reused_ai_row = (
                ranking_ai_score_reuse_index.get(fingerprint_record["fingerprint"])
                if ranking_reuse_enabled
                else None
            )
            if reused_ai_row is not None and normalize_score_state(reused_ai_row)["score_status"] != SCORE_STATUS_VALID:
                reused_ai_row = None
            if reused_ai_row is not None and identity_key:
                reused_ai_scores_by_identity[identity_key] = {
                    **deepcopy(reused_ai_row),
                    "job_url": job_url,
                    **{
                        field_name: shortlisted_job[field_name]
                        for field_name in ("run_job_id", "raw_job_fingerprint", "source_job_url")
                        if shortlisted_job.get(field_name) not in (None, "")
                    },
                    "ai_score_input_fingerprint": fingerprint_record["fingerprint"],
                    "ai_score_reuse_status": "reused_exact_match",
                    "ranking_input_diagnostics": ranking_input_diagnostics_by_identity.get(identity_key) or build_ranking_input_diagnostics(
                        ranking_input,
                        retrieval_metadata=retrieval_metadata,
                    ),
                }
                if manifest_identity in ranking_admission_rows:
                    ranking_admission_rows[manifest_identity]["score_execution"] = "reused"
                if build_reuse_decision_callback is not None:
                    reused_ai_scores_by_identity[identity_key]["reuse_decision"] = (
                        build_reuse_decision_callback(
                            decision="reused_exact_match",
                            reason_code="exact_fingerprint_match",
                            fingerprint=fingerprint_record["fingerprint"],
                            source_artifact_type="ranking_ai_score",
                        )
                    )
                continue
            fresh_scoring_jobs.append(shortlisted_job)
            if identity_key:
                fresh_ai_score_fingerprints[identity_key] = fingerprint_record["fingerprint"]
            if manifest_identity in ranking_admission_rows:
                ranking_admission_rows[manifest_identity]["score_execution"] = "fresh"

        fresh_ai_scores = (
            run_ai_scoring(
                fresh_scoring_jobs,
                candidate_summary,
                config,
                top_n=len(fresh_scoring_jobs),
                **(
                    {"runtime_observation_callback": runtime_observation_callback}
                    if runtime_observation_callback is not None
                    else {}
                ),
                resolved_route=resolved_route,
                **(
                    {"ranking_inputs": ranking_inputs_by_identity}
                    if ranking_inputs_by_identity
                    else {}
                ),
            )
            if fresh_scoring_jobs
            else []
        )
        fresh_ai_scores_by_identity: dict[str, dict[str, Any]] = {}
        for source_job, ai_row in zip(fresh_scoring_jobs, fresh_ai_scores):
            if not any(
                ai_row.get(field_name) not in (None, "")
                for field_name in ("run_job_id", "raw_job_fingerprint")
            ):
                ai_row = {
                    **ai_row,
                    **{
                        field_name: source_job[field_name]
                        for field_name in ("run_job_id", "raw_job_fingerprint", "source_job_url")
                        if source_job.get(field_name) not in (None, "")
                    },
                }
            identity_key = primary_job_identity_key(ai_row)
            fresh_ai_scores_by_identity[identity_key] = {
                **ai_row,
                "ai_score_input_fingerprint": fresh_ai_score_fingerprints.get(identity_key),
                "ai_score_reuse_status": "fresh_compute" if ranking_reuse_enabled else "reuse_disabled",
            }
            if build_reuse_decision_callback is not None:
                fresh_ai_scores_by_identity[identity_key]["reuse_decision"] = (
                    build_reuse_decision_callback(
                        decision=(
                            "fresh_compute"
                            if ranking_reuse_enabled
                            else "reuse_disabled"
                        ),
                        reason_code=(
                            "no_reusable_snapshot_match"
                            if ranking_reuse_enabled
                            else "stage_reuse_disabled"
                        ),
                        fingerprint=fresh_ai_score_fingerprints.get(identity_key),
                        source_artifact_type="ranking_ai_score",
                    )
                )

        ai_scores = []
        for shortlisted_job in ai_score_candidates:
            identity_key = primary_job_identity_key(shortlisted_job)
            score_row: dict[str, Any] | None = reused_ai_scores_by_identity.get(identity_key) or fresh_ai_scores_by_identity.get(identity_key)
            if score_row is not None:
                ai_scores.append(score_row)
                manifest_identity = primary_job_identity_key(shortlisted_job) or extract_job_url(shortlisted_job)
                manifest_row = ranking_admission_rows.get(manifest_identity)
                if manifest_row is not None:
                    score_status = normalize_score_state(score_row)["score_status"]
                    manifest_row.update(
                        {
                            "score_status": score_status,
                            "failure_code": score_row.get("failure_code"),
                            "retry_eligible": bool(score_row.get("retry_eligible", False)),
                            "score_execution": (
                                "invalid" if score_status == "invalid"
                                else "failed" if score_status == "unscored"
                                else manifest_row.get("score_execution") or "fresh"
                            ),
                        }
                    )
                    manifest_row["ranking_input_diagnostics"] = deepcopy(
                        score_row.get("ranking_input_diagnostics")
                        or manifest_row.get("ranking_input_diagnostics")
                        or {}
                    )
        ranking_admission_rows.update(
            {
                primary_job_identity_key(job) or extract_job_url(job): {
                    "identity": primary_job_identity_key(job) or extract_job_url(job),
                    "job_url": extract_job_url(job),
                    "shortlist_status": "shortlist_admitted",
                    "ai_score_status": "not-selected-by-ai-cutoff",
                    "score_execution": "not-attempted",
                }
                for job in shortlist[ai_top_n:]
            }
        )
        state["ranking_admission_manifest"] = {
            "contract_version": "ranking_admission_manifest_v1",
            "counts": {
                "shortlist_admitted": len(shortlist),
                "ai_score_selected": len(ai_score_candidates),
                "not_selected_by_ai_cutoff": max(0, len(shortlist) - len(ai_score_candidates)),
                "fresh": sum(1 for row in ranking_admission_rows.values() if row.get("score_execution") == "fresh"),
                "reused": sum(1 for row in ranking_admission_rows.values() if row.get("score_execution") == "reused"),
                "failed": sum(1 for row in ranking_admission_rows.values() if row.get("score_execution") == "failed"),
                "invalid": sum(1 for row in ranking_admission_rows.values() if row.get("score_execution") == "invalid"),
            },
            "rows": list(ranking_admission_rows.values()),
        }
        reused_ai_count = sum(
            1 for row in ai_scores
            if str(row.get("ai_score_reuse_status") or "") == "reused_exact_match"
        )
        fresh_ai_count = sum(
            1 for row in ai_scores
            if str(row.get("ai_score_reuse_status") or "") == "fresh_compute"
        )
        if reporter is not None:
            reporter.emit("layer3_ai_score", "info", f"AI scored: {len(ai_scores)} jobs")  # type: ignore[union-attr]
        set_span_attributes(
            {
                "ai_score_candidates": len(ai_score_candidates),
                "ai_scores": len(ai_scores),
                "fresh_ai_scores": fresh_ai_count,
                "reused_ai_scores": reused_ai_count,
            }
        )

    with observe_span("pipeline.ranking", attributes={"run_id": run_id, "final_top_n": final_top_n}):
        ranking_inputs = build_ranking_features(shortlist, ai_scores, profile, config)
        # A supplied resolver is the explicit legacy compatibility path. New runs
        # leave historical preference state untouched and rank by ai_score only.
        resolved_preference_policy = None
        if preference_policy_resolver is not None:
            resolved_preference_policy = resolve_run_preference_policy(
                ranking_rows=ranking_inputs,
                config=config,
                existing_payload=dict(state.get("resolved_preference_policy") or {}),
                resolver=preference_policy_resolver,
            )
            state["resolved_preference_policy"] = resolved_preference_policy_to_dict(
                resolved_preference_policy
            )
        ranked = rank_jobs(
            ranking_inputs,
            top_n=final_top_n,
            ranking_order_version=AI_ONLY_RANKING_ORDER_VERSION,
        )
        # Keep a single explicit, additive boundary into Stage 7.
        handoffs = []
        for row in ranked:
            if row.get("final_rank") is None or int(row.get("final_rank") or 0) > final_top_n:
                continue
            handoff = build_stage_6_to_7_handoff(row, profile=profile)
            row["stage6_to_stage7_handoff"] = handoff
            handoffs.append(handoff)
        state["stage6_to_stage7_handoffs"] = handoffs
        pipeline_store.store_final_ranking(ranked, config)
        if reporter is not None:
            reporter.emit("layer3_ranking", "info", f"Final ranking: top {len(ranked)} jobs")  # type: ignore[union-attr]
        state["ai_scores"] = ai_scores
        state["ranking_inputs"] = ranking_inputs
        state["ranking_input_diagnostics_by_identity"] = ranking_input_diagnostics_by_identity
        state["ranked"] = ranked
        set_span_attributes(
            {
                "ranking_inputs": len(ranking_inputs),
                "ranked_jobs": len(ranked),
            }
        )
    return ai_scores, ranking_inputs


def finalize_cv_analysis_stage(
    *,
    run_id: str,
    ranked: list[dict[str, Any]],
    cv_analysis_results: list[dict[str, Any]],
    cv_analysis_started_monotonic: float,
    cv_generation_debug_records: list[dict[str, Any]],
    state: dict[str, Any],
    config: dict[str, Any],
    reporter: Any | None,
    set_span_attributes: Callable[[dict[str, Any]], None],
    bounded_event_payload_builder: Callable[..., dict[str, Any]],
    ready_status: str,
    blocked_status: str,
    skipped_status: str,
    failed_status: str,
) -> None:
    if reporter is not None:
        blocked_by_reranker_diagnostics = [
            {
                "job_url": str(record.get("job_url") or ""),
                "ranking_fit_label": str(record.get("ranking_fit_label") or ""),
                "fit_classification": str(record.get("fit_classification") or ""),
                "ai_score": (record.get("job_snapshot") or {}).get("ai_score"),
                "fit_label_source": str(((record.get("job_snapshot") or {}).get("fit_label_source")) or ""),
            }
            for record in cv_analysis_results
            if str(record.get("status") or "") == blocked_status
        ][:10]
        reporter.emit(
            "layer4_cv_analysis",
            "info",
            (
                "CV analysis complete: "
                f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == 'ready_for_generation')} ready, "
                f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == blocked_status)} blocked by reranker, "
                f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == 'skipped_fit_gate')} skipped, "
                f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == 'analysis_failed')} failed"
            ),
            bounded_event_payload_builder(
                event_name="cv_analysis_decision",
                event_family="decision",
                source_stage="cv_analysis",
                event_status="completed",
                deterministic_outcome=None,
                stage_owned_subreason="stage_summary",
                input_snapshot={
                    "ranked_jobs": len(ranked),
                },
                output_snapshot={
                    "ready_for_generation": sum(
                        1 for record in cv_analysis_results
                        if str(record.get("status") or "") == ready_status
                    ),
                    "blocked_by_reranker_fit": sum(
                        1 for record in cv_analysis_results
                        if str(record.get("status") or "") == blocked_status
                    ),
                    "skipped_fit_gate": sum(
                        1 for record in cv_analysis_results
                        if str(record.get("status") or "") == skipped_status
                    ),
                    "analysis_failed": sum(
                        1 for record in cv_analysis_results
                        if str(record.get("status") or "") == failed_status
                    ),
                },
                artifact_refs={"stage_id": "cv_analysis"},
                latency_ms=int((time.monotonic() - cv_analysis_started_monotonic) * 1000),
            ),
        )  # type: ignore[union-attr]
        if blocked_by_reranker_diagnostics:
            reporter.emit(
                "layer4_cv_analysis_blocked_details",
                "info",
                f"Blocked by reranker diagnostics: {len(blocked_by_reranker_diagnostics)} job(s)",
                bounded_event_payload_builder(
                    event_name="cv_analysis_blocked_diagnostics",
                    event_family="debug",
                    source_stage="cv_analysis",
                    event_status="completed",
                    deterministic_outcome="rejected",
                    stage_owned_subreason=blocked_status,
                    input_snapshot={
                        "fit_label_thresholds": dict(
                            (config.get("ranking_policy") or {}).get("fit_label_thresholds")
                            or {}
                        ),
                    },
                    output_snapshot={
                        "blocked_jobs": blocked_by_reranker_diagnostics,
                    },
                    artifact_refs={"stage_id": "cv_analysis"},
                ),
            )  # type: ignore[union-attr]
    set_span_attributes(
        {
            "cv_analysis_records": len(cv_analysis_results),
            "cv_analysis_ready": sum(
                1 for record in cv_analysis_results
                if str(record.get("status") or "") == ready_status
            ),
            "cv_analysis_failed": sum(
                1 for record in cv_analysis_results
                if str(record.get("status") or "") == failed_status
            ),
        }
    )
    state["cv_analysis_results"] = cv_analysis_results
    state["cv_generation_debug_records"] = cv_generation_debug_records


def execute_cv_analysis_jobs(
    *,
    ranked_jobs_for_cv: list[dict[str, Any]],
    process_job: Callable[[dict[str, Any]], None],
) -> None:
    for job in ranked_jobs_for_cv:
        process_job(job)


def execute_cv_generation_records(
    *,
    generation_ready_records: list[dict[str, Any]],
    process_record: Callable[[dict[str, Any]], None],
) -> None:
    for analysis_record in generation_ready_records:
        process_record(analysis_record)


def select_cv_generation_ready_records(
    *,
    cv_analysis_results: list[dict[str, Any]],
    ready_status: str = "ready_for_generation",
) -> list[dict[str, Any]]:
    return [
        record for record in cv_analysis_results
        if str(record.get("status") or "") == ready_status
    ]


def emit_cv_generation_result_event(
    *,
    reporter: Any | None,
    bounded_event_payload_builder: Callable[..., dict[str, Any]],
    job: dict[str, Any],
    fit: str,
    authoritative_ranking_fit_label: Callable[[dict[str, Any], str], str],
    status: str,
    attempt_count: int = 1,
    retry_count: int = 0,
    latency_ms: int | None = None,
    usage: dict[str, Any] | None = None,
    cost: dict[str, Any] | None = None,
    reuse_status: str | None = None,
    reused_cv_version_id: str | None = None,
) -> None:
    if reporter is None:
        return
    effective_reuse_status = str(reuse_status or "").strip() or "fresh_compute"
    effective_reused_cv_version_id = str(reused_cv_version_id or "").strip()
    reporter.emit(
        "layer4_cv_generation_result",
        "info",
        f"CV generation result for {job.get('job_url')}: {status}",
        bounded_event_payload_builder(
            event_name="cv_generation_result",
            event_family="decision",
            source_stage="cv_generation",
            event_status="completed",
            job_url=str(job.get("job_url") or ""),
            deterministic_outcome=str(status or ""),
            fallback_used=False,
            input_snapshot={
                "ranking_fit_label": authoritative_ranking_fit_label(job, fit),
                "fit_classification": fit,
            },
            output_snapshot={
                "status": str(status or ""),
                "attempt_count": int(attempt_count),
                "retry_count": int(retry_count),
                "reuse_status": effective_reuse_status,
                "reused_cv_version_id": effective_reused_cv_version_id,
                "reuse_status_flat": effective_reuse_status,
                "reused_cv_version_id_flat": effective_reused_cv_version_id,
            },
            artifact_refs={"stage_id": "cv_generation"},
            latency_ms=latency_ms,
            usage=usage,
            cost=cost,
        ),
    )  # type: ignore[union-attr]
def _execute_requirement_aware_shortlist_stage(
    *,
    run_id: str,
    state: dict[str, Any],
    profile: dict[str, Any],
    passed_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    reporter: Any | None,
    pipeline_store: Any,
    set_span_attributes: Callable[[dict[str, Any]], None],
    persist: bool = True,
) -> tuple[list[dict[str, Any]], str, dict[str, Any], dict[str, Any]]:
    from fitcv.shortlist_selection import build_requirement_aware_rows, select_requirement_aware_jobs

    evidence_by_job: dict[str, list[dict[str, Any]]] = {}
    evidence_projection = build_evidence_projection(profile)
    assessment_failures = 0
    for job in passed_jobs:
        identity = str(job.get("canonical_job_identity") or job.get("job_url") or "").strip()
        if isinstance(job.get("requirement_coverage"), list) and job.get("requirement_coverage"):
            evidence_by_job[identity] = []
            continue
        try:
            bundle = retrieve_evidence_bundle(
                profile,
                job,
                max(3, len(evidence_projection.get("items") or [])),
                config=config,
                evidence_projection=evidence_projection,
            )
            assessment_items = [
                *(bundle.get("selected_evidence") or []),
                *(bundle.get("unselected_top_candidates") or []),
            ]
            rows: list[dict[str, Any]] = []
            for item in assessment_items:
                evidence_id = str(item.get("evidence_id") or "").strip()
                for requirement_id, assessment in dict(item.get("requirement_assessments") or {}).items():
                    rows.append(
                        {
                            "requirement_id": requirement_id,
                            "support_status": "supported" if assessment.get("qualified_support") else "partial" if assessment.get("canonical_match") else "unsupported",
                            "qualifier_status": assessment.get("qualifier_status"),
                            "evidence_id": evidence_id,
                            "reviewed": True,
                            "contradiction": assessment.get("qualifier_status") == "contradicted",
                            "provenance_grade": 2,
                        }
                    )
            responsibility_support = dict(
                (bundle.get("requirement_support") or {}).get("responsibility") or {}
            )
            for support_scope in ("pool", "selected"):
                for requirement_id, evidence_ids in dict(
                    responsibility_support.get(support_scope) or {}
                ).items():
                    for evidence_id in evidence_ids:
                        rows.append(
                            {
                                "requirement_id": requirement_id,
                                "supported_requirement_ids": [requirement_id],
                                "support_status": "supported",
                                "qualifier_status": "supported",
                                "evidence_id": evidence_id,
                                "reviewed": True,
                                "verified": True,
                                "provenance_grade": 2,
                            }
                        )
            evidence_by_job[identity] = rows
        except Exception:
            assessment_failures += 1
            evidence_by_job[identity] = []

    rows = build_requirement_aware_rows(
        passed_jobs,
        evidence_by_job,
        assessment_complete=assessment_failures == 0,
    )
    decision = select_requirement_aware_jobs(rows)
    assessment_input = {
        "profile_revision": str(profile.get("revision") or ""),
        "evidence_projection_fingerprint": str(evidence_projection.get("fingerprint") or ""),
        "requirement_contract_version": decision["requirement_contract_version"],
        "retrieval_strategy": resolve_retrieval_strategy(config),
        "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
        "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
        "policy_version": decision["policy_version"],
    }
    assessment_input_fingerprint = hashlib.sha256(
        json.dumps(assessment_input, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    admitted = []
    for row in decision["admitted"]:
        admitted.append(
            {
                **row,
                "shortlist_origin": "requirement_aware",
                "shortlist_status": "shortlist_admitted",
                "admission_capacity": decision["admission_capacity"],
                "shortlist_strategy": "core_pareto_evidence_v1",
                "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
            }
        )
    ledger_rows = [
        {
            **row,
            "identity": row.get("canonical_job_identity") or row.get("job_url"),
            "job_url": row.get("job_url"),
            "shortlist_status": "shortlist_admitted" if row.get("admitted") else "not_admitted",
            "raw_hit_present": False,
            "admission_reason": row.get("admission_reason"),
            "exclusion_reason": row.get("exclusion_reason"),
            "shortlist_strategy": "core_pareto_evidence_v1",
            "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
            "policy_version": decision["policy_version"],
            "evaluation_pool_id": decision["evaluation_pool_id"],
            "admission_capacity": decision["admission_capacity"],
        }
        for row in decision["rows"]
    ]
    diagnostics = {
        "shortlist_strategy": "core_pareto_evidence_v1",
        "eligibility_policy": resolve_shortlist_policy(config, strategy="core_pareto_evidence_v1"),
        "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
        "policy_version": decision["policy_version"],
        "requirement_contract_version": decision["requirement_contract_version"],
        "admission_capacity": decision["admission_capacity"],
        "evaluation_pool_size": len(rows),
        "evaluation_pool_id": decision["evaluation_pool_id"],
        "decision_fingerprint": decision["decision_fingerprint"],
        "assessment_fingerprint": decision["assessment_fingerprint"],
        "assessment_input": assessment_input,
        "assessment_input_fingerprint": assessment_input_fingerprint,
        "assessment_failures": assessment_failures,
    }
    persist_ledger = getattr(pipeline_store, "store_shortlist_admission_ledger", None)
    if persist and persist_ledger is not None:
        persist_ledger(ledger_rows, diagnostics, run_id, config)
    state["raw_shortlist"] = admitted
    state["shortlist"] = admitted
    state["shortlist_diagnostics"] = diagnostics
    state["shortlist_admission_manifest"] = {
        "contract_version": "shortlist_admission_manifest_v2",
        "strategy": "core_pareto_evidence_v1",
        "eligibility_policy": diagnostics["eligibility_policy"],
        "evaluation_pool_id": decision["evaluation_pool_id"],
        "assessment_fingerprint": decision["assessment_fingerprint"],
        "assessment_input_fingerprint": assessment_input_fingerprint,
        "counts": {"eligible": len(rows), "admitted": len(admitted), "not_admitted": len(rows) - len(admitted)},
        "rows": ledger_rows,
    }
    if reporter is not None:
        reporter.emit("layer3_shortlist", "info", f"Requirement-aware shortlist: {len(admitted)} admitted")  # type: ignore[union-attr]
    set_span_attributes({"passed_jobs": len(passed_jobs), "shortlist_jobs": len(admitted), "evaluation_pool_jobs": len(rows)})
    return admitted, "", {}, {}

def build_recall_safe_evaluation_pool(
    enriched_jobs: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
    rejected_jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Retain passed jobs and only soft-filter exclusions for requirement assessment."""
    passed_by_url = {
        str(job.get("job_url") or "").strip(): dict(job)
        for job in passed_jobs
        if str(job.get("job_url") or "").strip()
    }
    rejected_by_url = {
        str(item.get("job_url") or "").strip(): dict(item)
        for item in rejected_jobs
        if str(item.get("job_url") or "").strip()
    }
    pool: list[dict[str, Any]] = []
    for source_job in enriched_jobs:
        job_url = str(source_job.get("job_url") or "").strip()
        if not job_url:
            continue
        if job_url in passed_by_url:
            pool.append(
                {
                    **passed_by_url[job_url],
                    "legacy_eligibility": "passed",
                    "legacy_exclusion_reasons": [],
                    "evaluation_pool_reason": "legacy_passed",
                    "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
                }
            )
            continue
        rejection = rejected_by_url.get(job_url)
        reasons = [str(reason) for reason in (rejection or {}).get("reasons", []) if str(reason)]
        if not reasons or shortlist_filter_disposition(reasons) != "soft_exclusion":
            continue
        pool.append(
            {
                **dict(source_job),
                "marks": list((rejection or {}).get("marks") or []),
                "legacy_eligibility": "excluded",
                "legacy_exclusion_reasons": reasons,
                "legacy_excluded": True,
                "evaluation_pool_reason": "soft_filter_exclusion",
                "eligibility_policy_version": SHORTLIST_ELIGIBILITY_POLICY_VERSION,
            }
        )
    return pool
