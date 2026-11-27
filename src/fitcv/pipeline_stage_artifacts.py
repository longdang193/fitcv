"""@meta
name: pipeline_stage_artifacts
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Build stage-transition artifact blocks and stage-level summaries.
inputs:
  - Pipeline stage data and helper callbacks
outputs:
  - Stage artifact block dictionaries with schema-stable keys
lifecycle:
  - status: active
"""

from typing import Any, Callable, Protocol, cast

from fitcv.candidate import runtime_profile_value
from fitcv.late_stage_contract import CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS
from fitcv.ranking_contract import (
    RANKING_CV_HANDOFF_VERSION,
    RANKING_DECISION_ENVELOPE_VERSION,
    RANKING_ORDER_VERSION,
    RANKING_SCORE_CONTRACT_VERSION,
    SCORE_STATUS_INVALID,
    SCORE_STATUS_UNSCORED,
    SCORE_STATUS_VALID,
    build_ranking_cv_handoff,
    normalize_score_state,
    ranking_cv_handoff_sha256,
    validate_ranking_cv_handoff,
)
from fitcv.pipeline_contracts import dedupe_diagnostics


def truncate_stage_text(value: str, *, limit: int) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "...[truncated]"


def truncate_stage_value(value: Any, *, text_limit: int) -> Any:
    if isinstance(value, str):
        return truncate_stage_text(value, limit=text_limit)
    if isinstance(value, list):
        return [truncate_stage_value(item, text_limit=text_limit) for item in value]
    if isinstance(value, dict):
        return {
            str(key): truncate_stage_value(inner, text_limit=text_limit)
            for key, inner in value.items()
        }
    return value


def sample_rows(
    rows: list[Any],
    row_builder: Callable[[Any], dict[str, Any] | None],
    *,
    limit: int,
    text_limit: int,
) -> list[dict[str, Any]]:
    sampled: list[dict[str, Any]] = []
    for row in rows:
        built = row_builder(row)
        if not built:
            continue
        sampled.append(truncate_stage_value(built, text_limit=text_limit))
        if len(sampled) >= limit:
            break
    return sampled


def sample_strings(values: list[str], *, limit: int, text_limit: int) -> list[str]:
    return [
        truncate_stage_text(value, limit=text_limit)
        for value in values[:limit]
        if value
    ]


def build_ranking_score_state_diagnostics(
    rows: list[dict[str, Any]],
    *,
    max_items: int | None = None,
) -> list[dict[str, Any]]:
    """Build bounded, redacted diagnostics for non-valid ranking score rows."""
    diagnostics: list[dict[str, Any]] = []
    for row in rows:
        score_state = normalize_score_state(row)
        if score_state["score_status"] == SCORE_STATUS_VALID:
            continue
        job_key = next(
            (
                str(row.get(field_name)).strip()
                for field_name in (
                    "canonical_job_identity",
                    "job_identity",
                    "run_job_id",
                    "raw_job_fingerprint",
                )
                if row.get(field_name) not in (None, "")
            ),
            None,
        )
        input_index = row.get("_input_index", row.get("input_index"))
        diagnostic: dict[str, Any] = {
            "schema_version": "ranking_score_state_diagnostic_v1",
            "job_key": job_key,
            "score_status": score_state["score_status"],
            "failure_code": score_state["failure_code"],
            "disposition": score_state["disposition"],
            "retry_eligible": score_state["retry_eligible"],
        }
        if isinstance(input_index, int) and not isinstance(input_index, bool):
            diagnostic["input_index"] = input_index
        raw_fingerprint = row.get("raw_job_fingerprint")
        if raw_fingerprint not in (None, ""):
            diagnostic["raw_job_fingerprint"] = str(raw_fingerprint)
        diagnostics.append(diagnostic)

    diagnostics.sort(
        key=lambda item: (
            int(item.get("input_index"))
            if isinstance(item.get("input_index"), int)
            else 2**31 - 1,
            str(item.get("job_key") or ""),
            str(item.get("raw_job_fingerprint") or ""),
        )
    )
    if max_items is not None:
        return diagnostics[: max(0, int(max_items))]
    return diagnostics


def build_llm_runtime_summary(
    observations: list[dict[str, Any]],
    *,
    sample_limit: int = 10,
) -> dict[str, Any]:
    ordered = sorted(
        (dict(item) for item in observations),
        key=lambda item: (
            str(item.get("scope_key") or ""),
            int(item.get("input_index") or 0),
            int(item.get("invocation_index") or 0),
        ),
    )
    failures = [
        dict(item.get("evidence", {}).get("failure") or {})
        for item in ordered
        if str(item.get("evidence", {}).get("status") or "") == "failed"
    ]
    failure_counts_by_stage: dict[str, int] = {}
    failure_counts_by_code: dict[str, int] = {}
    input_tokens = 0
    output_tokens = 0
    total_tokens = 0
    cost = 0.0
    for item in ordered:
        telemetry = item.get("evidence", {}).get("telemetry", {})
        usage = telemetry.get("usage", {}) if isinstance(telemetry, dict) else {}
        if not isinstance(usage, dict):
            usage = {}
        item_input = usage.get("input_tokens", usage.get("prompt_tokens", 0))
        item_output = usage.get("output_tokens", usage.get("completion_tokens", 0))
        item_input = (
            item_input
            if isinstance(item_input, (int, float)) and not isinstance(item_input, bool)
            else 0
        )
        item_output = (
            item_output
            if isinstance(item_output, (int, float)) and not isinstance(item_output, bool)
            else 0
        )
        item_total = usage.get("total_tokens")
        item_total = (
            item_total
            if isinstance(item_total, (int, float)) and not isinstance(item_total, bool)
            else item_input + item_output
        )
        input_tokens += int(item_input)
        output_tokens += int(item_output)
        total_tokens += int(item_total)
        cost_details = telemetry.get("cost", {}) if isinstance(telemetry, dict) else {}
        if isinstance(cost_details, dict):
            item_cost = cost_details.get("total_cost", cost_details.get("cost", 0))
            if isinstance(item_cost, (int, float)) and not isinstance(item_cost, bool):
                cost += float(item_cost)
    for failure in failures:
        stage = str(failure.get("stage") or "unknown")
        code = str(failure.get("code") or "unknown")
        failure_counts_by_stage[stage] = failure_counts_by_stage.get(stage, 0) + 1
        failure_counts_by_code[code] = failure_counts_by_code.get(code, 0) + 1
    return {
        "contract_version": "llm_stage_runtime_summary_v1",
        "calls_total": len(ordered),
        "succeeded_total": sum(
            1 for item in ordered if str(item.get("evidence", {}).get("status") or "") == "succeeded"
        ),
        "failed_total": len(failures),
        "failure_counts_by_stage": failure_counts_by_stage,
        "failure_counts_by_code": failure_counts_by_code,
        "adapters": sorted(
            {
                str(item.get("evidence", {}).get("provenance", {}).get("adapter") or "")
                for item in ordered
                if str(item.get("evidence", {}).get("provenance", {}).get("adapter") or "")
            }
        ),
        "runtime_paths": sorted(
            {
                str(item.get("evidence", {}).get("provenance", {}).get("runtime_path") or "")
                for item in ordered
                if str(item.get("evidence", {}).get("provenance", {}).get("runtime_path") or "")
            }
        ),
        "routing_parts": sorted(
            {
                str(item.get("evidence", {}).get("provenance", {}).get("routing_part") or "")
                for item in ordered
                if str(item.get("evidence", {}).get("provenance", {}).get("routing_part") or "")
            }
        ),
        "usage": {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
            "cost": round(cost, 12),
            "input_output_ratio": input_tokens / output_tokens if output_tokens else None,
        },
        "evidence_sample": ordered[:sample_limit],
    }


def build_stage_block_not_reached(
    *,
    stage: str,
    stage_result_builder: Callable[[str], dict[str, Any]],
) -> dict[str, Any]:
    stage_result = stage_result_builder(stage)
    return {
        "stage_id": stage,
        "stage": stage,
        "status": "not_reached",
        "stage_result": stage_result,
        "input_counts": {},
        "output_counts": {},
        "decision_summary": {},
        "outputs_sample": [],
        "dropped_or_changed_sample": [],
        "inputs_sample": [],
    }


def build_stage_block(
    *,
    stage_id: str,
    status: str,
    input_counts: dict[str, Any],
    output_counts: dict[str, Any],
    decision_summary: dict[str, Any],
    inputs_sample: list[dict[str, Any]],
    outputs_sample: list[dict[str, Any]],
    dropped_or_changed_sample: list[dict[str, Any]],
    truncate_value: Callable[[Any], Any],
    stage_result_builder: Callable[[str, str, dict[str, Any], dict[str, Any], dict[str, Any]], dict[str, Any]],
    settings_refs: list[str] | None = None,
    llm_runtime_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    stage_result = stage_result_builder(
        stage_id,
        status,
        input_counts,
        output_counts,
        decision_summary,
    )
    block: dict[str, Any] = {
        "stage_id": stage_id,
        "stage": stage_id,
        "status": status,
        "stage_result": stage_result,
        "input_counts": input_counts,
        "output_counts": output_counts,
        "decision_summary": decision_summary,
        "outputs_sample": outputs_sample,
        "dropped_or_changed_sample": dropped_or_changed_sample,
        "inputs_sample": inputs_sample,
    }
    if settings_refs:
        block["settings_refs"] = settings_refs
    if llm_runtime_observations is not None:
        block["llm_runtime_summary"] = build_llm_runtime_summary(llm_runtime_observations)
    return cast(dict[str, Any], truncate_value(block))


def build_normalize_stage_block(
    *,
    raw_jobs: list[dict[str, Any]],
    normalized: list[dict[str, Any]],
    deduplicated_jobs: list[dict[str, Any]],
    dedupe_reason_counts: dict[str, Any],
    stage_block_builder: Callable[..., dict[str, Any]],
    sample_rows_builder: Callable[[list[Any], Callable[[Any], dict[str, Any] | None]], list[dict[str, Any]]],
    job_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    dedupe_reason_label_resolver: Callable[[str], str],
) -> dict[str, Any]:
    return stage_block_builder(
        stage_id="normalize",
        status="completed",
        input_counts={"raw_jobs": len(raw_jobs)},
        output_counts={
            "normalized_jobs": len(normalized),
            "deduplicated_jobs": len(deduplicated_jobs),
        },
        decision_summary={"dedupe_reason_counts": dedupe_reason_counts},
        inputs_sample=sample_rows_builder(raw_jobs, job_sample_builder),
        outputs_sample=sample_rows_builder(normalized, job_sample_builder),
        dropped_or_changed_sample=sample_rows_builder(
            deduplicated_jobs,
            lambda job: {
                **(job_sample_builder(job) or {}),
                "change_type": "deduplicated_before_enrichment",
                "dedupe_reason": dedupe_reason_label_resolver(
                    str(job.get("dedupe_reason") or ""),
                ),
            }
            if job_sample_builder(job)
            else None,
        ),
    )


def build_enrich_stage_block(
    *,
    normalized: list[dict[str, Any]],
    pre_filter_rejected_jobs: list[dict[str, Any]],
    enriched: list[dict[str, Any]],
    profile: dict[str, Any],
    config: dict[str, Any],
    enrich_prompt_provenance: dict[str, Any],
    enrich_reuse_counts: dict[str, Any],
    enrich_reuse_metrics: dict[str, Any],
    llm_runtime_observations: list[dict[str, Any]],
    stage_block_builder: Callable[..., dict[str, Any]],
    sample_rows_builder: Callable[[list[Any], Callable[[Any], dict[str, Any] | None]], list[dict[str, Any]]],
    job_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    extract_job_url: Callable[[dict[str, Any]], str],
    candidate_profile_summary_builder: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
) -> dict[str, Any]:
    rejected_urls = {
        extract_job_url(item) for item in pre_filter_rejected_jobs
    }
    surviving_normalized = [
        job for job in normalized if extract_job_url(job) not in rejected_urls
    ]
    return stage_block_builder(
        stage_id="enrich",
        status="completed",
        input_counts={
            "normalized_jobs": len(normalized),
            "jobs_entering_enrichment": len(normalized) - len(pre_filter_rejected_jobs),
        },
        output_counts={
            "enriched_jobs": len(enriched),
            "pre_enrichment_rejected_jobs": len(pre_filter_rejected_jobs),
        },
        decision_summary={
            "candidate_profile_summary": candidate_profile_summary_builder(profile, config),
            "enrich_prompt_id": enrich_prompt_provenance["prompt_id"],
            "enrich_prompt_version": enrich_prompt_provenance["prompt_version"],
            "enrich_prompt_template_path": enrich_prompt_provenance["template_path"],
            "enrich_prompt_model": enrich_prompt_provenance["model"],
            "enrich_prompt_customized": enrich_prompt_provenance[
                "prompt_customized"
            ],
            "enrich_prompt_replacement_sha256": enrich_prompt_provenance[
                "prompt_replacement_sha256"
            ],
            "enrich_prompt_replacement_char_count": enrich_prompt_provenance[
                "prompt_replacement_char_count"
            ],
            **enrich_reuse_counts,
            "reuse_metrics": enrich_reuse_metrics,
        },
        inputs_sample=sample_rows_builder(
            surviving_normalized,
            job_sample_builder,
        ),
        outputs_sample=sample_rows_builder(enriched, job_sample_builder),
        dropped_or_changed_sample=sample_rows_builder(
            pre_filter_rejected_jobs,
            lambda job: {
                **(job_sample_builder(job) or {}),
                "change_type": "rejected_before_enrichment",
                "reasons": list(job.get("reasons") or []),
            }
            if job_sample_builder(job)
            else None,
        ),
        llm_runtime_observations=llm_runtime_observations,
    )


def build_rule_filter_stage_block(
    *,
    enriched: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
    candidate_filter_rejected_jobs: list[dict[str, Any]],
    grouped_reject_reasons: dict[str, Any],
    grouped_mark_codes: dict[str, Any],
    selected_rule_filters: list[str],
    stage_block_builder: Callable[..., dict[str, Any]],
    sample_rows_builder: Callable[[list[Any], Callable[[Any], dict[str, Any] | None]], list[dict[str, Any]]],
    job_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    rule_filter_decision_sample_builder: Callable[..., dict[str, Any] | None],
) -> dict[str, Any]:
    return stage_block_builder(
        stage_id="rule_filter",
        status="completed",
        input_counts={"enriched_jobs": len(enriched)},
        output_counts={
            "passed_jobs": len(passed_jobs),
            "rejected_jobs": len(candidate_filter_rejected_jobs),
        },
        decision_summary={
            "reject_reason_counts": grouped_reject_reasons,
            "mark_code_counts": grouped_mark_codes,
            "selected_filters": selected_rule_filters,
        },
        inputs_sample=sample_rows_builder(enriched, job_sample_builder),
        outputs_sample=sample_rows_builder(
            passed_jobs,
            lambda job: rule_filter_decision_sample_builder(
                job,
                filter_outcome="pass",
            ),
        ),
        dropped_or_changed_sample=sample_rows_builder(
            candidate_filter_rejected_jobs,
            lambda job: (
                {
                    **(
                        rule_filter_decision_sample_builder(
                            job,
                            filter_outcome="reject",
                        )
                        or {}
                    ),
                    "change_type": "rejected_after_enrichment",
                }
                if rule_filter_decision_sample_builder(
                    job,
                    filter_outcome="reject",
                )
                else None
            ),
        ),
    )


def build_shortlist_stage_block(
    *,
    shortlist_reached: bool,
    passed_jobs: list[dict[str, Any]],
    raw_shortlist_urls: set[str],
    raw_shortlist: list[dict[str, Any]],
    shortlist: list[dict[str, Any]],
    audit_rows: list[dict[str, Any]],
    shortlist_diagnostics: dict[str, Any],
    shortlist_embedding_reuse_counts: dict[str, Any],
    shortlist_candidate_query_components: dict[str, Any],
    shortlist_candidate_query_debug: dict[str, Any],
    shortlist_quality_metrics: dict[str, Any],
    candidate_summary: str,
    vector_top_n: int,
    stage_block_builder: Callable[..., dict[str, Any]],
    stage_block_not_reached_builder: Callable[[str], dict[str, Any]],
    sample_rows_builder: Callable[[list[Any], Callable[[Any], dict[str, Any] | None]], list[dict[str, Any]]],
    sample_strings_builder: Callable[[list[str]], list[str]],
    job_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    shortlist_row_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    extract_job_url: Callable[[dict[str, Any]], str],
    extract_job_title: Callable[[dict[str, Any]], str],
    shortlist_admission_manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if not shortlist_reached:
        return stage_block_not_reached_builder("shortlist")
    dropped_rows: list[dict[str, Any]] = [
        *[
            {
                **job,
                "change_type": "not_returned_in_raw_hits",
                "shortlist_outcome": "not_returned_in_raw_hits",
                "raw_hit_present": False,
                "retrieval_anomaly_present": False,
            }
            for job in passed_jobs
            if extract_job_url(job) not in raw_shortlist_urls
        ],
    ]
    retrieval_diagnostics = {
        key: shortlist_diagnostics.get(key)
        for key in (
            "requested_strategy",
            "effective_strategy",
            "backend_id",
            "embedding_backend_id",
            "fallback_reason",
            "eligible_jobs_total",
            "scored_jobs_total",
            "production_shortlist_total",
            "production_cutoff_rank",
        )
        if key in shortlist_diagnostics
    }
    block = stage_block_builder(
        stage_id="shortlist",
        status="completed",
        input_counts={"passed_jobs": len(passed_jobs)},
        output_counts={
            "raw_vector_rows": len(raw_shortlist),
            "raw_vector_unique_jobs": len(raw_shortlist_urls),
            "raw_vector_hits": len(raw_shortlist_urls),
            "scoring_shortlist_jobs": len(shortlist),
            "audit_rows": len(audit_rows),
            "retrieval_anomalies": int(shortlist_diagnostics.get("raw_hit_anomaly_total") or 0),
            **shortlist_embedding_reuse_counts,
        },
        decision_summary={
            "candidate_query_text": candidate_summary,
            "candidate_query_components": shortlist_candidate_query_components,
            **shortlist_candidate_query_debug,
            "quality_metrics": shortlist_quality_metrics,
            "retrieval_diagnostics": retrieval_diagnostics,
            "vector_search_top_n": vector_top_n,
            "jobs_not_returned_in_raw_hits": len([job for job in passed_jobs if extract_job_url(job) not in raw_shortlist_urls]),
            **shortlist_embedding_reuse_counts,
            "raw_shortlist_anomaly_urls": sample_strings_builder(
                list(shortlist_diagnostics.get("raw_hit_anomaly_sample") or [])
            ),
        },
        inputs_sample=sample_rows_builder(passed_jobs, job_sample_builder),
        outputs_sample=sample_rows_builder(shortlist, shortlist_row_sample_builder),
        dropped_or_changed_sample=sample_rows_builder(
            dropped_rows,
            lambda item: {
                **(job_sample_builder(item) or {"job_url": str(item.get("job_url") or ""), "job_title": str(item.get("title") or "")}),
                "change_type": str(item.get("change_type") or ""),
                "shortlist_outcome": str(item.get("shortlist_outcome") or ""),
                "raw_hit_present": bool(item.get("raw_hit_present", False)),
                "retrieval_anomaly_present": bool(item.get("retrieval_anomaly_present", False)),
                **(
                    {
                        "embedding_reuse_status": item.get("embedding_reuse_status"),
                        "embedding_input_signature": item.get("embedding_input_signature"),
                        "embedding_contract_fingerprint": item.get("embedding_contract_fingerprint"),
                    }
                    if item.get("embedding_reuse_status") is not None
                    or item.get("embedding_input_signature") is not None
                    or item.get("embedding_contract_fingerprint") is not None
                    else {}
                ),
                **(
                    {
                        "vector_similarity": item.get("vector_similarity"),
                        "retrieval_score": item.get("retrieval_score"),
                        "retrieval_strategy": item.get("retrieval_strategy"),
                        "vector_rank": item.get("vector_rank"),
                        "shortlist_origin": item.get("shortlist_origin"),
                    }
                    if item.get("vector_rank") is not None or item.get("vector_similarity") is not None
                    else {}
                ),
            }
            if str(item.get("job_url") or "")
            else None,
        ),
        settings_refs=["pipeline.vector_search_top_n"],
    )
    block["production_retrieval_rows"] = [dict(row) for row in raw_shortlist]
    block["production_shortlist"] = [
        sample
        for row in shortlist
        if (sample := shortlist_row_sample_builder(row)) is not None
    ]
    block["audit_sample"] = [dict(row) for row in audit_rows]
    block["candidate_query_debug"] = dict(shortlist_candidate_query_debug)
    block["admission_manifest"] = dict(shortlist_admission_manifest or {})
    return block


def build_ranking_stage_block(
    *,
    ranking_reached: bool,
    ai_scores: list[dict[str, Any]],
    ranking_inputs: list[dict[str, Any]],
    ranking_input_diagnostics_by_identity: dict[str, dict[str, Any]] | None = None,
    ranked: list[dict[str, Any]],
    ranked_urls: set[str],
    final_top_n: int,
    ranking_fit_distribution: dict[str, Any],
    ranking_quality_metrics: dict[str, Any],
    ranking_reuse_metrics: dict[str, Any],
    ranking_prompt_provenance: dict[str, Any],
    ranking_policy: dict[str, Any],
    ranking_contract: dict[str, Any],
    legacy_checkpoint_adaptation_count: int,
    zero_weight_features: list[str],
    contributing_features: list[str],
    profile: dict[str, Any],
    config: dict[str, Any],
    stage_block_builder: Callable[..., dict[str, Any]],
    stage_block_not_reached_builder: Callable[[str], dict[str, Any]],
    sample_rows_builder: Callable[[list[Any], Callable[[Any], dict[str, Any] | None]], list[dict[str, Any]]],
    ranking_row_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    extract_job_url: Callable[[dict[str, Any]], str],
    ai_score_model_resolver: Callable[[dict[str, Any]], str],
    effective_preferences_resolver: Callable[[dict[str, Any], dict[str, Any]], dict[str, Any]],
    llm_runtime_observations: list[dict[str, Any]] | None = None,
    resolved_preference_policy: dict[str, Any] | None = None,
    ranking_admission_manifest: dict[str, Any] | None = None,
    ranking_cv_handoffs_by_identity: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    if not ranking_reached:
        return stage_block_not_reached_builder("ranking")
    scorer_input_diagnostics = {
        str(identity): dict(diagnostics)
        for identity, diagnostics in (ranking_input_diagnostics_by_identity or {}).items()
        if isinstance(diagnostics, dict)
    }
    scorer_diagnostics_by_identity = {
        str(row.get("canonical_job_identity") or row.get("job_identity") or row.get("raw_job_fingerprint") or extract_job_url(row)): dedupe_diagnostics(
            row.get("diagnostics")
        )
        for row in ai_scores
        if isinstance(row, dict)
        and row.get("diagnostics")
        and str(row.get("canonical_job_identity") or row.get("job_identity") or row.get("raw_job_fingerprint") or extract_job_url(row))
    }
    policy = dict(resolved_preference_policy or {})
    runtime_contract = dict(policy.get("runtime_contract") or {})
    residuals = [float(row.get("preference_residual") or 0.0) for row in ranking_inputs]
    personalization = {
        "schema_version": "ranking_personalization_v1",
        "resolution_status": policy.get("resolution_status", "zero_residual_no_active"),
        "diagnostic_code": policy.get("diagnostic_code"),
        "runtime_contract_fingerprint": runtime_contract.get("runtime_contract_fingerprint"),
        "policy_snapshot_id": policy.get("policy_snapshot_id"),
        "payload_fingerprint": policy.get("payload_fingerprint"),
        "preference_vector": list(policy.get("preference_vector") or []),
        "preference_vector_fingerprint": policy.get("preference_vector_fingerprint"),
        "learned_alpha": runtime_contract.get("learned_alpha"),
        "preference_vector_norm_bound": runtime_contract.get("preference_vector_norm_bound"),
        "residual_min": min(residuals, default=0.0),
        "residual_max": max(residuals, default=0.0),
        "residual_mean": sum(residuals) / len(residuals) if residuals else 0.0,
        "clipped_count": sum(bool(row.get("score_was_clipped")) for row in ranking_inputs),
        "rank_change_count": sum(
            row.get("baseline_rank") != row.get("personalized_rank") for row in ranking_inputs
        ),
    }
    personalization["clipped_rate"] = (
        personalization["clipped_count"] / len(ranking_inputs) if ranking_inputs else 0.0
    )
    personalization["rank_change_rate"] = (
        personalization["rank_change_count"] / len(ranking_inputs) if ranking_inputs else 0.0
    )
    score_status_counts = {
        "valid_count": 0,
        "unscored_count": 0,
        "invalid_count": 0,
    }
    for row in ai_scores:
        status = normalize_score_state(row)["score_status"]
        score_status_counts[f"{status}_count"] += 1
    score_state_diagnostics = build_ranking_score_state_diagnostics(ai_scores)
    ranking_status = (
        "failed"
        if ai_scores and score_status_counts["valid_count"] == 0
        else "partial"
        if score_status_counts["unscored_count"] or score_status_counts["invalid_count"]
        else "completed"
    )
    ranking_order_version = str(
        ranking_contract.get("ranking_order_version")
        or next(
            (
                row.get("ranking_order_version")
                for row in ranked
                if row.get("ranking_order_version")
            ),
            "",
        )
    ).strip() or RANKING_ORDER_VERSION
    ranking_policy_version = str(
        ranking_policy.get("policy_version")
        or next(
            (
                row.get("ranking_policy_version")
                for row in ranked
                if row.get("ranking_policy_version")
            ),
            "",
        )
    ).strip() or None
    ranking_contract_version = str(
        ranking_contract.get("ranking_score_contract_version")
        or RANKING_SCORE_CONTRACT_VERSION
    ).strip()
    profile_revision = runtime_profile_value(profile, "revision") if isinstance(profile, dict) else None
    handoff_items: list[dict[str, Any]] = []
    handoff_references: dict[str, str | None] = {}
    for row in ranked:
        identity = str(
            row.get("canonical_job_identity")
            or row.get("job_identity")
            or row.get("raw_job_fingerprint")
            or extract_job_url(row)
            or ""
        ).strip()
        provided_handoff = (ranking_cv_handoffs_by_identity or {}).get(identity)
        if isinstance(provided_handoff, dict):
            try:
                canonical_handoff = validate_ranking_cv_handoff(provided_handoff)
                handoff_fingerprint = str(provided_handoff.get("handoff_fingerprint") or "")
                if handoff_fingerprint != ranking_cv_handoff_sha256(canonical_handoff):
                    raise ValueError("ranking_cv_handoff_fingerprint_mismatch")
                handoff = {
                    **canonical_handoff,
                    "handoff_fingerprint": handoff_fingerprint,
                    "handoff_status": "complete",
                }
            except (TypeError, ValueError) as exc:
                handoff = {
                    "schema_version": RANKING_CV_HANDOFF_VERSION,
                    "handoff_status": "incomplete",
                    "canonical_job_identity": identity or None,
                    "missing_fields": [str(exc)],
                    "handoff_fingerprint": None,
                }
            handoff_references[identity] = handoff.get("handoff_fingerprint")
            handoff_items.append(handoff)
            continue
        provenance = row.get("source_provenance") or row.get("provenance")
        if not isinstance(provenance, dict):
            provenance = {
                "ranking_prompt": dict(ranking_prompt_provenance),
                "ranking_contract_fingerprint": ranking_contract.get(
                    "ranking_contract_fingerprint"
                ),
            }
        try:
            handoff = build_ranking_cv_handoff(
                row,
                candidate_profile_revision=profile_revision,
                ranking_order_version=ranking_order_version,
                ranking_policy_version=ranking_policy_version,
                ranking_contract_version=ranking_contract_version,
                source_provenance=provenance,
            )
            handoff["handoff_status"] = "complete"
            handoff_references[identity] = handoff["handoff_fingerprint"]
        except (TypeError, ValueError) as exc:
            handoff = {
                "schema_version": RANKING_CV_HANDOFF_VERSION,
                "handoff_status": "incomplete",
                "canonical_job_identity": identity or None,
                "missing_fields": [str(exc)],
                "handoff_fingerprint": None,
            }
            handoff_references[identity] = None
        handoff_items.append(handoff)
    handoff_status = (
        "complete"
        if handoff_items and all(item.get("handoff_status") == "complete" for item in handoff_items)
        else "incomplete"
        if handoff_items
        else "not_available"
    )
    block = stage_block_builder(
        stage_id="ranking",
        status=ranking_status,
        input_counts={
            "ai_scores": len(ai_scores),
            "ranking_inputs": len(ranking_inputs),
        },
        output_counts={
            "ranked_jobs": len(ranked),
            "final_top_n": final_top_n,
        },
        decision_summary={
            "ranking_fit_label_counts": ranking_fit_distribution,
            **score_status_counts,
            "reason_code": "ranking_unavailable" if ranking_status == "failed" else None,
            "quality_metrics": ranking_quality_metrics,
            "reuse_metrics": ranking_reuse_metrics,
            "ranking_prompt_id": ranking_prompt_provenance["prompt_id"],
            "ranking_prompt_version": ranking_prompt_provenance["prompt_version"],
            "ranking_prompt_template_path": ranking_prompt_provenance["template_path"],
            "ranking_prompt_customized": ranking_prompt_provenance[
                "prompt_customized"
            ],
            "ranking_prompt_replacement_sha256": ranking_prompt_provenance[
                "prompt_replacement_sha256"
            ],
            "ranking_prompt_replacement_char_count": ranking_prompt_provenance[
                "prompt_replacement_char_count"
            ],
            "ai_score_model": ai_score_model_resolver(config),
            "ranking_policy": ranking_policy,
            "ranking_contract_fingerprint": ranking_contract.get("ranking_contract_fingerprint"),
            "ranking_order_version": ranking_order_version,
            "ranking_policy_version": ranking_policy_version,
            "ranking_score_contract_version": ranking_contract_version,
            "ranking_decision_envelope_version": ranking_contract.get(
                "ranking_decision_envelope_version", RANKING_DECISION_ENVELOPE_VERSION
            ),
            "ranking_cv_handoff_version": RANKING_CV_HANDOFF_VERSION,
            "ranking_cv_handoff_status": handoff_status,
            "score_state_diagnostics_count": len(score_state_diagnostics),
            "score_state_diagnostics_truncated": False,
            "scorer_diagnostics_count": sum(len(items) for items in scorer_diagnostics_by_identity.values()),
            "effective_structured_factor_weights": ranking_contract.get(
                "effective_structured_factor_weights"
            ),
            "normalizer_version": ranking_policy.get("normalizer_version"),
            "legacy_checkpoint_adaptation_count": legacy_checkpoint_adaptation_count,
            "zero_weight_features": zero_weight_features,
            "contributing_features": contributing_features,
            "candidate_preference_resolution": effective_preferences_resolver(profile, config),
            "personalization": personalization,
        },
        inputs_sample=sample_rows_builder(ranking_inputs, ranking_row_sample_builder),
        outputs_sample=sample_rows_builder(ranked, ranking_row_sample_builder),
        dropped_or_changed_sample=sample_rows_builder(
            [row for row in ranking_inputs if extract_job_url(row) not in ranked_urls],
            lambda row: {
                **(ranking_row_sample_builder(row) or {}),
                "change_type": "scored_not_ranked",
            }
            if ranking_row_sample_builder(row)
            else None,
        ),
        settings_refs=[
            "ranking_policy",
            "ranking_contract",
            "pipeline.final_top_n",
            "prompts.ranking.ai_score.prompt_id",
        ],
        llm_runtime_observations=llm_runtime_observations,
    )
    block["scorer_input_diagnostics"] = scorer_input_diagnostics
    block["scorer_diagnostics_by_identity"] = scorer_diagnostics_by_identity
    block["score_state_diagnostics"] = score_state_diagnostics
    block["admission_manifest"] = dict(ranking_admission_manifest or {})
    block["ranking_cv_handoff"] = {
        "schema_version": RANKING_CV_HANDOFF_VERSION,
        "status": handoff_status,
        "items": handoff_items,
        "references": handoff_references,
    }
    evidence_personalization = (
        block.get("stage_result", {})
        .get("evidence", {})
        .get("decision_summary", {})
        .get("personalization")
    )
    if isinstance(evidence_personalization, dict):
        evidence_personalization.pop("preference_vector", None)
    return block


def build_cv_analysis_stage_block(
    *,
    cv_analysis_reached: bool,
    ranked: list[dict[str, Any]],
    cv_analysis_results: list[dict[str, Any]],
    cv_analysis_quality_metrics: dict[str, Any],
    cv_analysis_reuse_metrics: dict[str, Any],
    config: dict[str, Any],
    blocked_by_reranker_status: str,
    ready_for_generation_status: str,
    skipped_fit_gate_status: str,
    failed_status: str,
    stage_block_builder: Callable[..., dict[str, Any]],
    stage_block_not_reached_builder: Callable[[str], dict[str, Any]],
    sample_rows_builder: Callable[[list[Any], Callable[[Any], dict[str, Any] | None]], list[dict[str, Any]]],
    ranking_row_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    analysis_record_output_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    analysis_record_changed_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> dict[str, Any]:
    if not cv_analysis_reached:
        return stage_block_not_reached_builder("cv_analysis")
    handoff_failures = [
        record
        for record in cv_analysis_results
        if str(record.get("status") or "") == CV_ANALYSIS_HANDOFF_CONTRACT_FAILED_STATUS
    ]
    failure_codes = [
        str(
            (record.get("technical_failure") or record.get("error") or {}).get("failure_code")
            or ""
        ).strip()
        for record in handoff_failures
    ]
    failure_codes = [code for code in failure_codes if code]
    return stage_block_builder(
        stage_id="cv_analysis",
        status="failed" if handoff_failures else "completed",
        input_counts={"ranked_jobs": len(ranked)},
        output_counts={
            "blocked_by_reranker_fit": sum(
                1
                for record in cv_analysis_results
                if str(record.get("status") or "") == blocked_by_reranker_status
            ),
            "ready_for_generation": sum(
                1
                for record in cv_analysis_results
                if str(record.get("status") or "") == ready_for_generation_status
            ),
            "skipped_fit_gate": sum(
                1
                for record in cv_analysis_results
                if str(record.get("status") or "") == skipped_fit_gate_status
            ),
            "analysis_failed": sum(
                1
                for record in cv_analysis_results
                if str(record.get("status") or "") == failed_status
            ),
            "handoff_contract_failed": len(handoff_failures),
        },
        decision_summary={
            "analysis_records_captured": len(cv_analysis_results),
            "handoff_contract_failed": len(handoff_failures),
            "failure_code": failure_codes[0] if failure_codes else None,
            "quality_metrics": cv_analysis_quality_metrics,
            "reuse_metrics": cv_analysis_reuse_metrics,
            "evidence_top_k": int(config.get("pipeline", {}).get("evidence_top_k", 0) or 0),
            "effective_channel_pool_size": int(
                config.get("cv_analysis", {}).get("semantic_alignment", {}).get("channel_pool_size", 0) or 0
            ),
            "selected_evidence_total": sum(
                int((record.get("evidence_selection_summary") or {}).get("selected_evidence_count") or 0)
                for record in cv_analysis_results
            ),
            "merged_candidate_pool_total": sum(
                int((record.get("evidence_selection_summary") or {}).get("merged_pool_size") or 0)
                for record in cv_analysis_results
            ),
        },
        inputs_sample=sample_rows_builder(ranked, ranking_row_sample_builder),
        outputs_sample=sample_rows_builder(cv_analysis_results, analysis_record_output_sample_builder),
        dropped_or_changed_sample=sample_rows_builder(
            cv_analysis_results,
            analysis_record_changed_sample_builder,
        ),
        settings_refs=[
            "pipeline.evidence_top_k",
            "cv_analysis.semantic_alignment.enabled",
            "cv_analysis.semantic_alignment.model",
            "cv_analysis.semantic_alignment.required_skill_lexical_weight",
            "cv_analysis.semantic_alignment.required_skill_semantic_weight",
            "cv_analysis.semantic_alignment.role_lexical_weight",
            "cv_analysis.semantic_alignment.role_semantic_weight",
            "cv_analysis.semantic_alignment.responsibility_lexical_weight",
            "cv_analysis.semantic_alignment.responsibility_semantic_weight",
            "cv_analysis.semantic_alignment.domain_lexical_weight",
            "cv_analysis.semantic_alignment.domain_semantic_weight",
            "cv_analysis.semantic_alignment.channel_pool_size",
        ],
        llm_runtime_observations=[],
    )


def build_cv_generation_stage_block(
    *,
    cv_generation_reached: bool,
    cv_analysis_results: list[dict[str, Any]],
    cv_generation_debug_records: list[dict[str, Any]],
    cv_status_counts: dict[str, Any],
    cv_generation_quality_metrics: dict[str, Any],
    cv_generation_reuse_metrics: dict[str, Any],
    cv_generation_prompt_provenance: dict[str, Any],
    config: dict[str, Any],
    stage_block_builder: Callable[..., dict[str, Any]],
    stage_block_not_reached_builder: Callable[[str], dict[str, Any]],
    sample_rows_builder: Callable[[list[Any], Callable[[Any], dict[str, Any] | None]], list[dict[str, Any]]],
    analysis_record_output_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    debug_record_output_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    debug_record_changed_sample_builder: Callable[[dict[str, Any]], dict[str, Any] | None],
    cv_generation_model_summarizer: Callable[[list[dict[str, Any]], str], str],
    cv_generation_provider_summarizer: Callable[[list[dict[str, Any]]], str],
    cv_generation_model_resolver: Callable[[dict[str, Any]], str],
) -> dict[str, Any]:
    if not cv_generation_reached:
        return stage_block_not_reached_builder("cv_generation")
    ready_records = [
        record
        for record in cv_analysis_results
        if str(record.get("status") or "") == "ready_for_generation"
    ]
    runtime_observations = [
        dict(observation)
        for record in cv_generation_debug_records
        for observation in list(record.get("llm_runtime_observations") or [])
        if isinstance(observation, dict)
    ]
    generation_failure_statuses = {
        "validation_failed",
        "generation_failed",
        "pdf_failed",
        "persistence_failed",
    }
    has_generation_failure = any(
        str(record.get("status") or "").strip().lower() in generation_failure_statuses
        for record in cv_generation_debug_records
    )
    return stage_block_builder(
        stage_id="cv_generation",
        status="failed" if has_generation_failure else "completed",
        input_counts={
            "analysis_ready_jobs": len(ready_records),
        },
        output_counts={
            "accepted": cv_status_counts["accepted_count"],
            "review_required": cv_status_counts["review_required_count"],
            "validation_failed": cv_status_counts["validation_failed_count"],
            "generation_failed": cv_status_counts["generation_failed_count"],
            "persistence_failed": cv_status_counts["persistence_failed_count"],
        },
        decision_summary={
            "debug_records_captured": cv_status_counts["debug_records_captured"],
            "analysis_ready_jobs_total": len(ready_records),
            "quality_metrics": cv_generation_quality_metrics,
            "reuse_metrics": cv_generation_reuse_metrics,
            "cv_generation_model": cv_generation_model_summarizer(
                cv_generation_debug_records,
                cv_generation_model_resolver(config),
            ),
            "cv_generation_provider": cv_generation_provider_summarizer(
                cv_generation_debug_records,
            ),
            "cv_prompt_id": cv_generation_prompt_provenance["prompt_id"],
            "cv_prompt_template_path": cv_generation_prompt_provenance["template_path"],
            "cv_prompt_customized": cv_generation_prompt_provenance[
                "prompt_customized"
            ],
            "cv_prompt_replacement_sha256": cv_generation_prompt_provenance[
                "prompt_replacement_sha256"
            ],
            "cv_prompt_replacement_char_count": cv_generation_prompt_provenance[
                "prompt_replacement_char_count"
            ],
        },
        inputs_sample=sample_rows_builder(
            ready_records,
            analysis_record_output_sample_builder,
        ),
        outputs_sample=sample_rows_builder(
            cv_generation_debug_records,
            debug_record_output_sample_builder,
        ),
        dropped_or_changed_sample=sample_rows_builder(
            [
                record
                for record in cv_generation_debug_records
                if str(record.get("status") or "")
                in {"validation_failed", "generation_failed", "pdf_failed", "persistence_failed"}
            ],
            debug_record_changed_sample_builder,
        ),
        settings_refs=[
            "cv.generation.model",
            "prompts.cv_generation.structured_write.prompt_id",
        ],
        llm_runtime_observations=runtime_observations,
    )
