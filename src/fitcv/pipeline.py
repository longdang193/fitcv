"""@meta
name: pipeline
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.location-language-eligibility
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.pipeline.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

"""Full pipeline orchestrator — wires all FitCV pipeline stages end-to-end.

Stage order
-----------
1. Ingest + normalise + enrich
2. Candidate profile load
3a. Rule filter (BEFORE embedding — keeps shortlist clean and reduces cost)
3b. Embed eligible jobs + candidate, then vector shortlist + AI scoring
3c. Build ranking features; final ranking
4. Per-job: evidence retrieval → gap analysis → CV generation → validation → versioning

Failure policy
--------------
- Fail fast on setup issues: missing config, bad credentials, unreadable profile.
- Per-job failures in Layer 4 are caught, logged, and skipped (partial success is OK).

Config keys consumed
--------------------
config["paths"]["candidate_profile"]       path to candidate YAML
config["pipeline"]["vector_search_top_n"]  top-N for vector shortlist (e.g. 50)
config["pipeline"]["ai_score_top_n"]       top-N cap for AI scoring  (e.g. 50)
config["pipeline"]["final_top_n"]          final ranked list size     (e.g. 10)
config["pipeline"]["evidence_top_k"]       evidence items per job     (e.g. 5)

embed_scope note
----------------
v1 embeds only rule-passing jobs (cheaper, faster).
"""

import logging
import hashlib
import json
import os
import time
import uuid
import datetime
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from copy import deepcopy
from typing import Any, Callable, cast

from fitcv.ai_score import build_ai_score_input_fingerprint, run_ai_scoring
from fitcv.agentic_cv_analysis import (
    analyze_ranked_job,
    build_analysis_input_summary,
    resolve_ranked_job_fit,
)
from fitcv.agentic_cv_generation import (
    build_cv_generation_input_fingerprint,
    generate_from_analysis as run_agentic_cv_generation,
    hitl_review_reason_for_case as _hitl_review_reason_for_agentic_case,
    transition_cv_generation_persistence_failed,
)
from fitcv.candidate import (
    flatten_skills,
    infer_effective_preferences,
    load_candidate_profile,
    load_profile_json_text,
    load_profile_yaml,
)
from fitcv.config import (
    CV_SECTION_KEY_TO_NAME,
    get_cv_generation_model,
    get_prompt_addendum_metadata,
    get_cv_generation_prompt_version,
    get_ranking_ai_score_model,
    get_stage_runtime_concurrency,
    get_stage_runtime_sleep_secs,
    load_config,
    resolve_model_routing_part,
)
from fitcv.contracts import (
    STAGE_TRANSITION_ARTIFACTS_PIPELINE_SCHEMA_VERSION,
    normalize_analysis_channel_mapping,
)
from fitcv.pipeline_contracts import (
    JOB_OUTCOME_EVENT_STAGE,
    PIPELINE_STAGE_SEQUENCE,
    PIPELINE_STAGE_SET as _PIPELINE_STAGE_SET,
    build_job_outcome_fact,
    build_stage_dispatch_map as _build_stage_dispatch_map,
    job_outcome_event_reference,
    completed_pipeline_stages_through,
    next_pipeline_stage,
    project_pipeline_status_outcome,
)
from fitcv.pipeline_stages.common import (
    pipeline_int,
    extract_job_title,
    extract_job_url,
    job_identity_keys,
    normalize_shortlist_row,
    json_safe_value,
    shortlist_outcome_for_row,
    unique_job_urls,
    compute_raw_shortlist_anomaly_urls,
    job_sample,
    candidate_profile_summary,
    shortlist_row_sample,
    ranking_row_sample,
    analysis_record_output_sample,
    analysis_record_changed_sample,
    debug_record_output_sample,
    debug_record_changed_sample,
)
from fitcv.embeddings import embed_and_store_candidate, embed_and_store_jobs
from fitcv.enrich import (
    FRESH_ENRICHMENT_STATUS,
    REUSED_CACHED_ENRICHMENT_STATUS,
    build_enrich_contract_fingerprint,
    build_raw_job_fingerprint,
    enrich_batch,
    get_enrich_prompt_provenance,
    load_run_structured_jobs,
    load_structured_jobs,
    lookup_reusable_structured_jobs,
)
from fitcv.fit_factors import build_candidate_fit_context
from fitcv.ingest import load_raw_jobs, parse_jobs_file, prepare_raw_rows
from fitcv.pipeline_stage_runner import merge_passed_filter_records
from fitcv.normalize import normalize_batch, normalize_batch_with_exclusions
from fitcv.ranking import (
    compute_must_have_match,
    compute_declared_preference_fit_details,
    compute_seniority_fit,
    compute_title_relevance,
    rank_jobs,
    store_final_ranking,
)
from fitcv.late_stage_contract import (
    CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
    CV_ANALYSIS_FAILED_STATUS,
    CV_ANALYSIS_READY_FOR_GENERATION_STATUS,
    CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS,
    CV_GENERATION_ATTEMPTED_STATUSES,
    CV_GENERATION_FINAL_STATUSES,
    CV_GENERATION_REVIEW_REQUIRED_STATUS,
    cv_generation_status_for_analysis_status as _cv_generation_status_for_analysis_status,
    deterministic_truth_fields as _deterministic_truth_fields,
    shortlist_status_for_ranked_job as _shortlist_status_for_ranked_job,
    validation_status_for_cv_status as _validation_status_for_cv_status,
)
from fitcv.ranking_contract import (
    build_baseline_result,
    fit_label_from_score,
    project_legacy_ranking_aliases,
)
from fitcv.rule_filter import (
    DEFAULT_SELECTED_RULE_FILTERS,
    apply_pre_enrichment_global_filters,
    apply_rule_filters,
    store_filter_results,
)
from fitcv.runtime_routing import validate_cv_generation_routing_ready
from fitcv.tracker import (
    create_cv_version_record,
    lookup_reusable_cv_versions,
    store_cv_version,
)
from fitcv.validator import AnalysisGroundingPayload
from fitcv.telemetry import (
    bound_langfuse_excerpt,
    bound_langfuse_issue_list,
    bound_langfuse_list,
    bound_langfuse_markdown,
    build_langfuse_item_observation_attributes,
    build_trace_context,
    observe_span,
    render_langfuse_labeled_list_section,
    render_langfuse_labeled_text_section,
    render_langfuse_markdown_sections,
    set_span_attributes,
)
from fitcv.vector_search import run_vector_search
from fitcv.vector_search import store_shortlist
from fitcv.pipeline_observability import build_cv_analysis_item_observation_attributes as _build_cv_analysis_item_observation_attributes_observability
from fitcv.pipeline_observability import build_cv_generation_item_observation_attributes as _build_cv_generation_item_observation_attributes_observability
from fitcv.pipeline_observability import build_bounded_event_payload as _build_bounded_event_payload_observability
from fitcv.pipeline_observability import render_cv_analysis_item_output as _render_cv_analysis_item_output_observability
from fitcv.pipeline_observability import render_cv_generation_item_output as _render_cv_generation_item_output_observability
from fitcv.pipeline_stage_artifacts import build_stage_block as _build_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import build_stage_block_not_reached as _build_stage_block_not_reached_artifacts
from fitcv.pipeline_stage_artifacts import build_normalize_stage_block as _build_normalize_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import build_enrich_stage_block as _build_enrich_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import build_rule_filter_stage_block as _build_rule_filter_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import build_shortlist_stage_block as _build_shortlist_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import build_ranking_stage_block as _build_ranking_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import build_cv_analysis_stage_block as _build_cv_analysis_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import build_cv_generation_stage_block as _build_cv_generation_stage_block_artifacts
from fitcv.pipeline_stage_artifacts import sample_rows as _sample_rows_artifacts
from fitcv.pipeline_stage_artifacts import sample_strings as _sample_strings_artifacts
from fitcv.pipeline_stage_artifacts import truncate_stage_text as _truncate_stage_text_artifacts
from fitcv.pipeline_stage_artifacts import truncate_stage_value as _truncate_stage_value_artifacts
from fitcv.reuse import build_reuse_decision
from fitcv.reuse import resolve_reuse_stage_policy
from fitcv.pipeline_store import PipelineStore
from fitcv.preference_policy import (
    PreferenceRuntimeContract,
    ResolvedPreferencePolicy,
    resolve_run_preference_policy,
    resolved_preference_policy_to_dict,
)
from fitcv.pipeline_stage_context import (
    PipelineState,
    infer_last_completed_stage_from_state,
)

logger = logging.getLogger(__name__)
_EXPORT_ENRICHED_JOB_FIELDS = (
    "location_type",
    "seniority",
    "required_skills",
    "required_skills_canonical",
    "required_skill_entities",
    "preferred_skills",
    "preferred_skills_canonical",
    "preferred_skill_entities",
    "responsibilities",
    "domain",
    "tech_stack",
    "years_experience_min",
    "years_experience_max",
    "keywords",
    "job_family",
    "mapping_suggestions",
    "enrichment_version",
    "enrichment_model",
    "enriched_at",
    "raw_job_fingerprint",
    "enrich_contract_fingerprint",
    "enrich_reuse_status",
)
_DEDUPE_REASON_LABELS = {
    "duplicate_job_url": "duplicate_job_url",
    "near_duplicate_job_posting": "near_duplicate_job_posting",
}
_EMPTY_REPAIR_ATTEMPT = {"performed": False, "missing_sections": []}
_FIT_LABEL_ORDER = {"skip": 0, "stretch": 1, "strong": 2}
_STAGE_ARTIFACT_SAMPLE_LIMIT = 20
_STAGE_ARTIFACT_TEXT_LIMIT = 240
PIPELINE_STATUS_RANKED_BLOCKED_BY_RERANKER = "ranked_blocked_by_reranker_fit"

def _prompt_runtime_metadata(
    config: dict[str, Any],
    *,
    stage_id: str,
    prompt_key: str,
) -> dict[str, Any]:
    stage_block = dict((config.get("prompts_runtime") or {}).get(stage_id) or {})
    prompt_block = dict(stage_block.get(prompt_key) or {})
    task_id = {
        ("enrich", "extraction"): "enrich_extraction",
        ("ranking", "ai_score"): "ranking_ai_score",
        ("cv_generation", "structured_write"): "cv_generation_structured_write",
    }.get((stage_id, prompt_key))
    customization = (
        get_prompt_addendum_metadata(task_id, config) if task_id is not None else {}
    )
    return {
        "prompt_id": str(prompt_block.get("prompt_id") or ""),
        "prompt_version": str(prompt_block.get("version") or ""),
        "template_path": str(prompt_block.get("template_path") or ""),
        "stage_id": str(prompt_block.get("stage_id") or ""),
        "prompt_customized": bool(customization.get("customized", False)),
        "prompt_addendum_sha256": customization.get("addendum_sha256"),
        "prompt_addendum_char_count": int(
            customization.get("addendum_char_count", 0)
        ),
    }

def _materialize_scoring_shortlist(
    raw_shortlist: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Merge production retrieval evidence onto matching passed jobs."""
    passed_by_url: dict[str, dict[str, Any]] = {}
    for job in passed_jobs:
        job_url = extract_job_url(job)
        if not job_url:
            continue
        if job_url in passed_by_url:
            raise ValueError(f"ambiguous passed-job URL mapping: {job_url}")
        passed_by_url[job_url] = job
    scoring_shortlist: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for row in raw_shortlist:
        job_url = extract_job_url(row)
        if not job_url or job_url in seen_urls:
            continue
        passed_job = passed_by_url.get(job_url)
        if passed_job is None:
            continue
        seen_urls.add(job_url)
        scoring_shortlist.append(
            {
                **passed_job,
                "job_url": job_url,
                **normalize_shortlist_row(row),
                "shortlist_origin": "vector_search",
            }
        )

    return scoring_shortlist



def _finalize_fresh_enriched_rows(
    rows: list[dict[str, Any]],
    *,
    raw_job_fingerprints: dict[str, str],
    enrich_contract_fingerprint: str,
) -> list[dict[str, Any]]:
    for row in rows:
        job_url = extract_job_url(row)
        if not job_url:
            continue
        row["raw_job_fingerprint"] = raw_job_fingerprints.get(job_url)
        row["enrich_contract_fingerprint"] = enrich_contract_fingerprint
        row["enrich_reuse_status"] = FRESH_ENRICHMENT_STATUS
        row["reuse_decision"] = build_reuse_decision(
            decision=FRESH_ENRICHMENT_STATUS,
            reason_code="no_reusable_enrichment_row",
            fingerprint=raw_job_fingerprints.get(job_url),
            source_artifact_type="enrich",
        )
    return rows


def _finalize_reused_enriched_row(
    row: dict[str, Any],
    *,
    raw_job_fingerprints: dict[str, str],
    enrich_contract_fingerprint: str,
) -> dict[str, Any]:
    job_url = extract_job_url(row)
    if not job_url:
        return row
    row["raw_job_fingerprint"] = raw_job_fingerprints.get(job_url)
    row["enrich_contract_fingerprint"] = enrich_contract_fingerprint
    row["enrich_reuse_status"] = REUSED_CACHED_ENRICHMENT_STATUS
    row["reuse_decision"] = build_reuse_decision(
        decision=REUSED_CACHED_ENRICHMENT_STATUS,
        reason_code="exact_fingerprint_match",
        fingerprint=raw_job_fingerprints.get(job_url),
        source_artifact_type="enrich",
    )
    return row
def _enrich_jobs_with_reuse(
    normalized_jobs: list[dict[str, Any]],
    config: dict[str, Any],
    *,
    pipeline_store: PipelineStore | None = None,
    heartbeat_callback: Callable[[dict[str, Any]], None] | None = None,
    incremental_save_run_id: str | None = None,
    runtime_observations: list[dict[str, Any]] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    import threading

    if not normalized_jobs:
        return [], []
    if pipeline_store is None:
        pipeline_store = PipelineStore(
            load_raw_jobs_fn=load_raw_jobs,
            load_candidate_profile_fn=load_candidate_profile,
            lookup_reusable_structured_jobs_fn=lookup_reusable_structured_jobs,
            load_structured_jobs_fn=load_structured_jobs,
            load_run_structured_jobs_fn=load_run_structured_jobs,
            store_filter_results_fn=store_filter_results,
            embed_and_store_jobs_fn=embed_and_store_jobs,
            store_shortlist_fn=store_shortlist,
            store_final_ranking_fn=store_final_ranking,
            store_cv_version_fn=store_cv_version,
        )

    raw_job_fingerprints: dict[str, str] = {}
    for job in normalized_jobs:
        job_url = extract_job_url(job)
        if not job_url:
            continue
        raw_job_fingerprints[job_url] = build_raw_job_fingerprint(job)["fingerprint"]

    enrich_contract_fingerprint = build_enrich_contract_fingerprint(config)["fingerprint"]
    enrich_reuse_enabled = _reuse_stage_enabled(config, "enrich")
    reused_rows_by_url = (
        pipeline_store.lookup_reusable_structured_jobs(
            normalized_jobs,
            config,
            raw_job_fingerprints=raw_job_fingerprints,
            enrich_contract_fingerprint=enrich_contract_fingerprint,
        )
        if enrich_reuse_enabled
        else {}
    )

    fresh_jobs = [
        job for job in normalized_jobs
        if extract_job_url(job) and extract_job_url(job) not in reused_rows_by_url
    ]
    fresh_rows: list[dict[str, Any]] = []
    incrementally_saved_fresh_urls: set[str] = set()

    def _run_enrich_call_with_polling(
        fn: Callable[[], list[dict[str, Any]]],
        *,
        timeout_secs: int | None = None,
        heartbeat_interval_secs: int | None = None,
        on_progress: Callable[[int, float], None] | None = None,
    ) -> list[dict[str, Any]]:
        result_holder: dict[str, Any] = {"rows": None, "error": None}

        def _target() -> None:
            try:
                result_holder["rows"] = fn()
            except Exception as exc:  # noqa: BLE001
                result_holder["error"] = exc

        worker = threading.Thread(target=_target, daemon=True)
        worker.start()
        started_at = time.monotonic()
        heartbeat_count = 0
        poll_interval = float(heartbeat_interval_secs or 1)

        while worker.is_alive():
            worker.join(timeout=poll_interval)
            elapsed = max(0.0, time.monotonic() - started_at)
            if timeout_secs is not None and elapsed >= float(timeout_secs):
                raise TimeoutError(f"Enrich timeout after {timeout_secs}s")
            if worker.is_alive() and on_progress is not None and heartbeat_interval_secs is not None:
                heartbeat_count += 1
                on_progress(heartbeat_count, elapsed)

        error = result_holder.get("error")
        if error is not None:
            raise error
        return list(result_holder.get("rows") or [])

    if fresh_jobs:
        debug_heartbeat_enabled = str(os.environ.get("FITCV_ENRICH_DEBUG_HEARTBEAT", "") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        emit_job_events_enabled = str(os.environ.get("FITCV_ENRICH_EMIT_JOB_EVENTS", "") or "").strip().lower() in {
            "1",
            "true",
            "yes",
            "on",
        }
        per_job_timeout_raw = str(os.environ.get("FITCV_ENRICH_JOB_TIMEOUT_SECS", "180") or "180").strip()
        try:
            per_job_timeout_secs = max(10, int(float(per_job_timeout_raw)))
        except ValueError:
            per_job_timeout_secs = 180
        heartbeat_interval_raw = str(os.environ.get("FITCV_ENRICH_HEARTBEAT_SECS", "15") or "15").strip()
        try:
            heartbeat_interval_secs = max(5, int(float(heartbeat_interval_raw)))
        except ValueError:
            heartbeat_interval_secs = 15

        def _persist_incremental_fresh_rows(rows: list[dict[str, Any]]) -> None:
            if not incremental_save_run_id or not rows:
                return
            finalized_rows = _finalize_fresh_enriched_rows(
                rows,
                raw_job_fingerprints=raw_job_fingerprints,
                enrich_contract_fingerprint=enrich_contract_fingerprint,
            )
            pipeline_store.load_structured_jobs(finalized_rows, config)
            pipeline_store.load_run_structured_jobs(finalized_rows, incremental_save_run_id, config)
            for row in finalized_rows:
                job_url = extract_job_url(row)
                if job_url:
                    incrementally_saved_fresh_urls.add(job_url)

        if debug_heartbeat_enabled:
            total = len(fresh_jobs)
            for idx, job in enumerate(fresh_jobs, start=1):
                job_url = extract_job_url(job) or f"job_{idx}"
                if heartbeat_callback:
                    heartbeat_callback(
                        {
                            "phase": "job_start",
                            "index": idx,
                            "total": total,
                            "job_url": job_url,
                            "timeout_secs": per_job_timeout_secs,
                        }
                    )
                try:
                    batch_rows = _run_enrich_call_with_polling(
                        lambda: enrich_batch(
                            [job],
                            config,
                            runtime_observation_callback=(
                                runtime_observations.append if runtime_observations is not None else None
                            ),
                        ),
                        timeout_secs=per_job_timeout_secs,
                    )
                except TimeoutError as exc:
                    if heartbeat_callback:
                        heartbeat_callback(
                            {
                                "phase": "job_timeout",
                                "index": idx,
                                "total": total,
                                "job_url": job_url,
                                "timeout_secs": per_job_timeout_secs,
                            }
                        )
                    raise TimeoutError(
                        f"Enrich timeout for {job_url} after {per_job_timeout_secs}s (job {idx}/{total})"
                    ) from exc
                if batch_rows:
                    fresh_rows.extend(batch_rows)
                    _persist_incremental_fresh_rows(batch_rows)
                if heartbeat_callback:
                    heartbeat_callback(
                        {
                            "phase": "job_done",
                            "index": idx,
                            "total": total,
                            "job_url": job_url,
                            "rows": len(batch_rows or []),
                        }
                    )
        else:
            job_index_by_url: dict[str, int] = {}
            job_index_lock = threading.Lock()
            next_job_index = 0

            def _job_event_callback(evt: dict[str, Any]) -> None:
                nonlocal next_job_index
                if not emit_job_events_enabled or heartbeat_callback is None:
                    return
                phase = str(evt.get("phase") or "").strip()
                job_url = str(evt.get("job_url") or "").strip()
                if not phase or not job_url:
                    return
                if phase == "job_start":
                    with job_index_lock:
                        next_job_index += 1
                        job_index_by_url[job_url] = next_job_index
                    heartbeat_callback(
                        {
                            "phase": "job_start",
                            "index": job_index_by_url.get(job_url),
                            "total": len(fresh_jobs),
                            "job_url": job_url,
                            "timeout_secs": per_job_timeout_secs,
                        }
                    )
                    return
                if phase == "job_done":
                    heartbeat_callback(
                        {
                            "phase": "job_done",
                            "index": job_index_by_url.get(job_url),
                            "total": len(fresh_jobs),
                            "job_url": job_url,
                            "elapsed_secs": evt.get("elapsed_secs"),
                        }
                    )
                    return

            if heartbeat_callback:
                heartbeat_callback(
                    {
                        "phase": "batch_start",
                        "fresh_jobs_total": len(fresh_jobs),
                        "reused_jobs_total": len(reused_rows_by_url),
                        "heartbeat_interval_secs": heartbeat_interval_secs,
                    }
                )
            def _on_chunk_complete(chunk_rows: list[dict[str, Any]]) -> None:
                try:
                    _persist_incremental_fresh_rows(chunk_rows)
                except Exception:
                    logger.warning("Incremental save failed for chunk", exc_info=True)

            fresh_rows = _run_enrich_call_with_polling(
                lambda: enrich_batch(
                    fresh_jobs,
                    config,
                    job_event_callback=_job_event_callback if emit_job_events_enabled else None,
                    runtime_observation_callback=(
                        runtime_observations.append if runtime_observations is not None else None
                    ),
                    on_chunk_complete=_on_chunk_complete if incremental_save_run_id else None,
                ),
                heartbeat_interval_secs=heartbeat_interval_secs,
                on_progress=(
                    lambda heartbeat_count, elapsed_secs: heartbeat_callback(
                        {
                            "phase": "batch_progress",
                            "fresh_jobs_total": len(fresh_jobs),
                            "reused_jobs_total": len(reused_rows_by_url),
                            "heartbeat_count": heartbeat_count,
                            "elapsed_secs": int(elapsed_secs),
                            "heartbeat_interval_secs": heartbeat_interval_secs,
                        }
                    ) if heartbeat_callback else None
                ),
            )
            if heartbeat_callback:
                heartbeat_callback(
                    {
                        "phase": "batch_done",
                        "fresh_jobs_total": len(fresh_jobs),
                        "reused_jobs_total": len(reused_rows_by_url),
                        "fresh_rows_total": len(fresh_rows),
                    }
                )
        _finalize_fresh_enriched_rows(
            fresh_rows,
            raw_job_fingerprints=raw_job_fingerprints,
            enrich_contract_fingerprint=enrich_contract_fingerprint,
        )
        pending_fresh_rows = [
            row
            for row in fresh_rows
            if (extract_job_url(row) or "") not in incrementally_saved_fresh_urls
        ]
        if pending_fresh_rows and pipeline_store is not None:
            pipeline_store.load_structured_jobs(pending_fresh_rows, config)
            if incremental_save_run_id:
                pipeline_store.load_run_structured_jobs(
                    pending_fresh_rows,
                    incremental_save_run_id,
                    config,
                )

    fresh_rows_by_url = {
        extract_job_url(row): row
        for row in fresh_rows
        if extract_job_url(row)
    }
    enriched_rows: list[dict[str, Any]] = []
    reused_rows: list[dict[str, Any]] = []
    for job in normalized_jobs:
        job_url = extract_job_url(job)
        if not job_url:
            continue
        reused_row = reused_rows_by_url.get(job_url)
        if reused_row is not None:
            finalized_reused_row = _finalize_reused_enriched_row(
                reused_row,
                raw_job_fingerprints=raw_job_fingerprints,
                enrich_contract_fingerprint=enrich_contract_fingerprint,
            )
            reused_rows.append(finalized_reused_row)
            enriched_rows.append(finalized_reused_row)
            continue
        fresh_row = fresh_rows_by_url.get(job_url)
        if fresh_row is not None:
            enriched_rows.append(fresh_row)
    if incremental_save_run_id and reused_rows and pipeline_store is not None:
        pipeline_store.load_run_structured_jobs(
            reused_rows,
            incremental_save_run_id,
            config,
        )
    return enriched_rows, fresh_rows

def _enrich_runtime_projection(config: dict[str, Any]) -> dict[str, Any]:
    projected = dict(config)
    stage_runtime = dict(projected.get("stage_runtime") or {})
    enrich_runtime = dict(stage_runtime.get("enrich") or {})
    if "sleep_secs" in enrich_runtime:
        projected["enrichment_sleep_secs"] = enrich_runtime["sleep_secs"]
    if "batch_size" in enrich_runtime:
        projected["enrichment_batch_size"] = enrich_runtime["batch_size"]
    if "concurrency" in enrich_runtime:
        projected["enrichment_concurrency"] = enrich_runtime["concurrency"]
    return projected

def _reuse_stage_enabled(config: dict[str, Any], stage: str) -> bool:
    return bool(resolve_reuse_stage_policy(config, stage).enabled)


def _merge_ranked_job_with_enriched_context(
    ranked_job: dict[str, Any],
    enriched_by_url: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    job_url = extract_job_url(ranked_job)
    enriched_job = enriched_by_url.get(job_url, {})
    if not enriched_job:
        return dict(ranked_job)
    return {
        **enriched_job,
        **ranked_job,
    }


def _build_export_results(
    *,
    raw_jobs: list[dict[str, Any]],
    enriched: list[dict[str, Any]],
    deduplicated_jobs: list[dict[str, Any]],
    pre_filter_rejected: list[dict[str, Any]],
    candidate_filter_rejected: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
    raw_shortlist: list[dict[str, Any]],
    shortlist_for_scoring: list[dict[str, Any]],
    ranking_inputs: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    cv_analysis_results: list[dict[str, Any]],
    cv_results: list[dict[str, Any]],
    cv_generation_debug_records: list[dict[str, Any]],
    vector_search_top_n: int,
    run_id: str = "unknown",
    stage_transition_artifacts: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    def _identity_seed(row: dict[str, Any]) -> dict[str, Any]:
        seeded = dict(row)
        seeded["source_job_url"] = str(
            seeded.get("source_job_url")
            or seeded.get("job_url")
            or seeded.get("jobUrl")
            or ""
        ).strip()
        return seeded

    def _index_rows_by_identity(
        items: list[dict[str, Any]],
        *,
        transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None,
    ) -> dict[str, dict[str, Any]]:
        indexed: dict[str, dict[str, Any]] = {}
        for item in items:
            seeded = _identity_seed(item)
            payload = transform(seeded) if transform is not None else seeded
            for identity_key in job_identity_keys(seeded):
                indexed[identity_key] = payload
        return indexed

    def _identity_keys_for(row: dict[str, Any]) -> list[str]:
        return job_identity_keys(_identity_seed(row))

    def _lookup(indexed: dict[str, dict[str, Any]], row: dict[str, Any]) -> dict[str, Any] | None:
        for identity_key in _identity_keys_for(row):
            match = indexed.get(identity_key)
            if match is not None:
                return match
        return None

    def _matches(identity_index: set[str], row: dict[str, Any]) -> bool:
        return any(identity_key in identity_index for identity_key in _identity_keys_for(row))

    enriched_by_identity = _index_rows_by_identity(enriched)
    passed_by_identity = _index_rows_by_identity(passed_jobs)
    raw_shortlist_by_identity = _index_rows_by_identity(raw_shortlist, transform=normalize_shortlist_row)
    scoring_shortlist_by_identity = _index_rows_by_identity(shortlist_for_scoring, transform=normalize_shortlist_row)
    scoring_by_identity = _index_rows_by_identity(ranking_inputs)
    ranked_by_identity = _index_rows_by_identity(ranked)
    analysis_by_identity = _index_rows_by_identity(cv_analysis_results)
    cv_by_identity = _index_rows_by_identity(cv_results)
    passed_job_urls = {extract_job_url(job) for job in passed_jobs if extract_job_url(job)}
    debug_by_identity = _index_rows_by_identity(cv_generation_debug_records)
    skipped_fit_gate_identity_keys = {
        identity_key
        for record in cv_generation_debug_records
        if str(record.get("status") or "") == "skipped_fit_gate"
        for identity_key in _identity_keys_for(record)
    }
    blocked_by_reranker_identity_keys = {
        identity_key
        for record in cv_generation_debug_records
        if str(record.get("status") or "") == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS
        for identity_key in _identity_keys_for(record)
    }
    deduplicated_by_input_index = {
        int(job.get("input_index", -1)): job
        for job in deduplicated_jobs
        if job.get("input_index") is not None
    }

    reject_reasons_by_identity: dict[str, list[str]] = {}
    rule_filter_marks_by_identity: dict[str, list[dict[str, Any]]] = {}
    for job in passed_jobs:
        marks = list(job.get("marks") or [])
        for identity_key in _identity_keys_for(job):
            rule_filter_marks_by_identity[identity_key] = marks
    rejected_before_enrichment_identity_keys: set[str] = set()
    rejected_after_enrichment_identity_keys: set[str] = set()
    for rejected in pre_filter_rejected:
        reject_reasons = list(rejected.get("reasons") or [])
        for identity_key in _identity_keys_for(rejected):
            reject_reasons_by_identity[identity_key] = reject_reasons
            rejected_before_enrichment_identity_keys.add(identity_key)
    for rejected in candidate_filter_rejected:
        reject_reasons = list(rejected.get("reasons") or [])
        marks = list(rejected.get("marks") or [])
        for identity_key in _identity_keys_for(rejected):
            reject_reasons_by_identity[identity_key] = reject_reasons
            rule_filter_marks_by_identity[identity_key] = marks
            rejected_after_enrichment_identity_keys.add(identity_key)

    def _status_for(raw_job: dict[str, Any]) -> str:
        if _lookup(cv_by_identity, raw_job) is not None:
            return "ranked_with_cv"
        if _matches(blocked_by_reranker_identity_keys, raw_job):
            return PIPELINE_STATUS_RANKED_BLOCKED_BY_RERANKER
        if _matches(skipped_fit_gate_identity_keys, raw_job):
            return "ranked_skipped_fit_gate"
        if _lookup(ranked_by_identity, raw_job) is not None:
            return "ranked_no_cv"
        if _matches(rejected_before_enrichment_identity_keys, raw_job):
            return "rejected_before_enrichment"
        if _matches(rejected_after_enrichment_identity_keys, raw_job):
            return "rejected_after_enrichment"
        if _lookup(scoring_by_identity, raw_job) is not None:
            return "scored_not_ranked"
        if _lookup(scoring_shortlist_by_identity, raw_job) is not None:
            return "shortlisted_not_scored"
        if _lookup(passed_by_identity, raw_job) is not None:
            return "not_shortlisted"
        return "unknown_pipeline_state"

    def _sort_key(row: dict[str, Any]) -> tuple[int, float, str, str, int, int]:
        status = str(row["pipeline_status"])
        category = {
            "ranked_with_cv": 0,
            PIPELINE_STATUS_RANKED_BLOCKED_BY_RERANKER: 1,
            "ranked_skipped_fit_gate": 2,
            "ranked_no_cv": 3,
            "not_shortlisted": 4,
            "shortlisted_not_scored": 5,
            "scored_not_ranked": 6,
            "rejected_after_enrichment": 7,
            "rejected_before_enrichment": 8,
            "deduplicated_before_enrichment": 9,
            "unknown_pipeline_state": 10,
        }.get(status, 10)
        scores = dict(row.get("scores") or {})
        baseline_fit = float(scores.get("baseline_fit") or 0.0)
        raw_job_fingerprint = str(row.get("raw_job_fingerprint") or "")
        job_url = str(row.get("job_url") or "")
        rank = int(row.get("rank") or 0) or 999999
        input_index = int(row.get("_input_index") or 0)
        return (category, -baseline_fit, raw_job_fingerprint, job_url, rank, input_index)

    rows: list[dict[str, Any]] = []
    for input_index, raw_job in enumerate(raw_jobs):
        job_url = extract_job_url(raw_job)
        seeded_raw_job = _identity_seed(raw_job)
        enriched_job = _lookup(enriched_by_identity, seeded_raw_job)
        deduplicated_job = deduplicated_by_input_index.get(input_index)
        score_source = {
            **(_lookup(scoring_shortlist_by_identity, seeded_raw_job) or {}),
            **(_lookup(scoring_by_identity, seeded_raw_job) or {}),
            **(_lookup(ranked_by_identity, seeded_raw_job) or {}),
        }
        cv_row = _lookup(cv_by_identity, seeded_raw_job)
        analysis_row = _lookup(analysis_by_identity, seeded_raw_job)
        cv_payload = None
        if cv_row is not None:
            runtime_observations = list(cv_row.get("llm_runtime_observations") or [])
            runtime_provenance = {}
            if runtime_observations and isinstance(runtime_observations[-1], dict):
                evidence = runtime_observations[-1].get("evidence")
                if isinstance(evidence, dict) and isinstance(evidence.get("provenance"), dict):
                    runtime_provenance = dict(evidence["provenance"])
            cv_payload = {
                "version_id": cv_row.get("cv_version_id"),
                "ranking_fit_label": cv_row.get("ranking_fit_label") or cv_row.get("fit_classification"),
                "fit_classification": cv_row.get("fit_classification"),
                "model_used": cv_row.get("cv_generation_model"),
                "runtime_path": runtime_provenance.get("runtime_path"),
                "provider": runtime_provenance.get("provider"),
                "prompt_id": cv_row.get("cv_prompt_id"),
                "prompt_template_path": cv_row.get("cv_prompt_template_path"),
                "schema_version": (
                    cv_row.get("structured_cv", {}) or {}
                ).get("schema_version") if isinstance(cv_row.get("structured_cv"), dict) else None,
                "structured": cv_row.get("structured_cv"),
                "markdown": cv_row.get("cv_markdown"),
                "created_at": cv_row.get("generated_at"),
            }
        pipeline_status = _status_for(seeded_raw_job)
        reject_reasons = next(
            (
                reject_reasons_by_identity[identity_key]
                for identity_key in _identity_keys_for(seeded_raw_job)
                if identity_key in reject_reasons_by_identity
            ),
            [],
        )
        rule_filter_marks = next(
            (
                rule_filter_marks_by_identity[identity_key]
                for identity_key in _identity_keys_for(seeded_raw_job)
                if identity_key in rule_filter_marks_by_identity
            ),
            [],
        )
        if deduplicated_job is not None:
            pipeline_status = "deduplicated_before_enrichment"
            reject_reasons = [
                _DEDUPE_REASON_LABELS.get(str(deduplicated_job.get("dedupe_reason") or ""), "deduplicated_before_enrichment")
            ]
            score_source = {}

        raw_shortlist_row = _lookup(raw_shortlist_by_identity, seeded_raw_job)
        scoring_shortlist_row = _lookup(scoring_shortlist_by_identity, seeded_raw_job)
        matched_passed_job = _lookup(passed_by_identity, seeded_raw_job)
        matched_passed_job_url = extract_job_url(matched_passed_job or {})
        if matched_passed_job is not None and matched_passed_job_url:
            shortlist_status = _shortlist_status_for_export_row(
                job_url=matched_passed_job_url,
                passed_job_urls=passed_job_urls,
                raw_shortlist_row=raw_shortlist_row,
                scoring_shortlist_row=scoring_shortlist_row,
            )
        else:
            shortlist_status = "not_applicable"

        ranking_fit_label = str(score_source.get("baseline_fit_label") or "").strip() or None
        ranking_fit_source = (
            "baseline_fit_label"
            if ranking_fit_label is not None
            else "baseline_fit_thresholds"
            if score_source.get("baseline_fit") is not None
            else None
        )
        debug_row = _lookup(debug_by_identity, seeded_raw_job)
        if debug_row is not None:
            cv_status = str(debug_row.get("status") or "not_attempted")
        elif _lookup(ranked_by_identity, seeded_raw_job) is not None:
            cv_status = "not_attempted"
        else:
            cv_status = "not_applicable"
        if isinstance(debug_row, dict) and isinstance(debug_row.get("decision_chain"), dict):
            decision_chain = dict(debug_row["decision_chain"])
        else:
            decision_chain = _build_decision_chain(
                shortlist_status=shortlist_status,
                advanced_to_scoring=_lookup(scoring_shortlist_by_identity, seeded_raw_job) is not None,
                ranking_fit_label=ranking_fit_label,
                ranking_fit_source=ranking_fit_source,
                cv_status=cv_status,
            )
        truth_fields = (
            _deterministic_truth_fields(debug_row.get("status"))
            if isinstance(debug_row, dict)
            else _deterministic_truth_fields(analysis_row.get("status"))
            if isinstance(analysis_row, dict)
            else _deterministic_truth_fields(None)
        )
        score_projection = project_legacy_ranking_aliases(
            {
                "baseline_fit": score_source.get("baseline_fit"),
                "baseline_fit_label": score_source.get("baseline_fit_label"),
                "baseline_rank": score_source.get("baseline_rank"),
            }
        )
        native_status = pipeline_status
        if pipeline_status == "ranked_no_cv" and cv_status in {
            "review_required",
            "validation_failed",
            "generation_failed",
            "persistence_failed",
            "analysis_failed",
        }:
            native_status = cv_status
        outcome_projection = project_pipeline_status_outcome(native_status)
        reason_code = outcome_projection["reason_code"]
        if native_status == "review_required" and isinstance(debug_row, dict):
            reason_code = str(
                debug_row.get("review_required_reason_code")
                or "review_gate_manual_required"
            )
        elif native_status in {"rejected_after_enrichment", "rejected_before_enrichment"}:
            candidate_reason = str(reject_reasons[0] if reject_reasons else "").strip()
            if candidate_reason and candidate_reason == candidate_reason.lower() and all(
                character.isalnum() or character == "_" for character in candidate_reason
            ):
                reason_code = candidate_reason
        elif native_status == "deduplicated_before_enrichment" and deduplicated_job is not None:
            dedupe_reason = str(deduplicated_job.get("dedupe_reason") or "").strip()
            if dedupe_reason in {"duplicate_job_url", "near_duplicate_job_posting"}:
                reason_code = dedupe_reason
        job_key = f"input:{input_index}"
        evidence_record: dict[str, Any] = {
            "record_key": job_key,
            "job_url": job_url or None,
            "raw_job_fingerprint": str(
                (enriched_job or {}).get("raw_job_fingerprint")
                or raw_job.get("raw_job_fingerprint")
                or score_source.get("raw_job_fingerprint")
                or ""
            ) or None,
            "stage_status": native_status,
            "reason_code": reason_code,
            "reject_reasons": [str(value) for value in reject_reasons[:16]],
            "rule_filter_mark_codes": [
                str(mark.get("code") or "")
                for mark in rule_filter_marks[:16]
                if isinstance(mark, dict) and str(mark.get("code") or "")
            ],
            "cv_status": cv_status,
        }
        evidence_bytes = json.dumps(
            evidence_record,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        evidence_fingerprint = f"sha256:{hashlib.sha256(evidence_bytes).hexdigest()}"
        evidence_record["fingerprint"] = evidence_fingerprint
        if isinstance(stage_transition_artifacts, dict):
            stages = stage_transition_artifacts.setdefault("stages", {})
            if isinstance(stages, dict):
                stage_artifact = stages.setdefault(outcome_projection["stage"], {})
                if isinstance(stage_artifact, dict):
                    records = stage_artifact.setdefault("outcome_evidence_records", [])
                    if isinstance(records, list):
                        records.append(evidence_record)
        evidence_ref = {
            "artifact": f"{outcome_projection['stage']}.json",
            "fingerprint": evidence_fingerprint,
            "record_key": job_key,
        }
        job_outcome = build_job_outcome_fact(
            run_id=run_id,
            input_index=input_index,
            job_url=job_url or None,
            attempt_id=(
                str(debug_row.get("attempt_id") or "").strip() or None
                if isinstance(debug_row, dict)
                else None
            ),
            stage_status=native_status,
            stage=outcome_projection["stage"],
            outcome=outcome_projection["outcome"],
            reason_code=reason_code,
            reason_facts={},
            policy_version=(
                str(debug_row.get("policy_version") or "").strip() or None
                if isinstance(debug_row, dict)
                else None
            ),
            trace_id=(
                str(debug_row.get("trace_id") or "").strip() or None
                if isinstance(debug_row, dict)
                else None
            ),
            evidence_ref=evidence_ref,
            projection_status=outcome_projection["projection_status"],
            occurred_at=datetime.datetime.now(datetime.timezone.utc),
        )

        rows.append(
            {
                "job_url": job_url,
                "source_job_url": str(raw_job.get("source_job_url") or job_url),
                "raw_job_fingerprint": (
                    str(
                        (enriched_job or {}).get("raw_job_fingerprint")
                        or raw_job.get("raw_job_fingerprint")
                        or score_source.get("raw_job_fingerprint")
                        or ""
                    ).strip()
                    or None
                ),
                "shortlist_origin": score_source.get("shortlist_origin"),
                "normalized_embedding": score_source.get("normalized_embedding"),
                "embedding_vector_fingerprint": score_source.get("embedding_vector_fingerprint"),
                "embedding_contract_fingerprint": score_source.get("embedding_contract_fingerprint"),
                "job_title": extract_job_title(enriched_job or raw_job or {}),
                "company": (enriched_job or raw_job or {}).get("company_name")
                or (enriched_job or raw_job or {}).get("companyName"),
                "location_type": (enriched_job or {}).get("location_type"),
                "seniority": (enriched_job or {}).get("seniority"),
                "job_family": (enriched_job or {}).get("job_family"),
                "domain": (enriched_job or {}).get("domain"),
                "pipeline_status": pipeline_status,
                **truth_fields,
                "reject_reasons": reject_reasons,
                "rule_filter_marks": rule_filter_marks,
                "scores": {
                    **score_projection,
                    "personalized_rank": score_source.get("personalized_rank"),
                    "preference_residual": score_source.get("preference_residual"),
                    "personalized_rank_score": score_source.get("personalized_rank_score"),
                    "personalized_display_score": score_source.get("personalized_display_score"),
                    "score_was_clipped": score_source.get("score_was_clipped"),
                    "preference_policy_snapshot_id": score_source.get(
                        "preference_policy_snapshot_id"
                    ),
                    "preference_vector_fingerprint": score_source.get(
                        "preference_vector_fingerprint"
                    ),
                    "preference_runtime_contract_fingerprint": score_source.get(
                        "preference_runtime_contract_fingerprint"
                    ),
                    "preference_policy_resolution_status": score_source.get(
                        "preference_policy_resolution_status"
                    ),
                    "holistic_ai_fit": score_source.get("holistic_ai_fit"),
                    "structured_fit": score_source.get("structured_fit"),
                    "normalized_factors": score_source.get("normalized_factors"),
                    "ranking_contract_fingerprint": score_source.get("ranking_contract_fingerprint"),
                    "vector_score": score_source.get("vector_similarity"),
                    "ai_score_reuse_status": score_source.get("ai_score_reuse_status"),
                    "ai_score_input_fingerprint": score_source.get("ai_score_input_fingerprint"),
                },
                "cv_analysis": (
                    {
                        "status": analysis_row.get("status"),
                        "analysis_reuse_status": analysis_row.get("analysis_reuse_status"),
                        "analysis_input_fingerprint": analysis_row.get("analysis_input_fingerprint"),
                    }
                    if analysis_row is not None
                    else None
                ),
                "decision_chain": decision_chain,
                "rank": score_source.get("personalized_rank") or score_source.get("baseline_rank"),
                "cv": (
                    {
                        key: value
                        for key, value in (cv_payload or {}).items()
                        if key not in {"structured", "markdown"}
                    }
                    if cv_payload is not None
                    else None
                ),
                "job_outcome": job_outcome,
                "_input_index": input_index,
            }
        )

    rows.sort(key=_sort_key)
    for row in rows:
        row.pop("_input_index", None)
    return rows


class PipelineCancelled(Exception):
    """Raised when a cooperative cancellation checkpoint is triggered."""


def _validate_pipeline_stage_name(stage_name: str | None) -> str | None:
    if stage_name is None:
        return None
    normalized = str(stage_name).strip()
    if normalized not in _PIPELINE_STAGE_SET:
        raise ValueError(f"Unknown pipeline stage: {stage_name!r}")
    return normalized


def next_pipeline_stage(stage_name: str | None) -> str | None:
    normalized = _validate_pipeline_stage_name(stage_name)
    if normalized is None:
        return PIPELINE_STAGE_SEQUENCE[0]
    stage_index = PIPELINE_STAGE_SEQUENCE.index(normalized)
    if stage_index + 1 >= len(PIPELINE_STAGE_SEQUENCE):
        return None
    return PIPELINE_STAGE_SEQUENCE[stage_index + 1]


def completed_pipeline_stages_through(stage_name: str | None) -> list[str]:
    normalized = _validate_pipeline_stage_name(stage_name)
    if normalized is None:
        return []
    stage_index = PIPELINE_STAGE_SEQUENCE.index(normalized)
    return list(PIPELINE_STAGE_SEQUENCE[: stage_index + 1])

def _normalize_late_stage_reuse_snapshots(reuse_snapshots: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    payload = dict(reuse_snapshots or {})
    ranking_rows: list[dict[str, Any]] = []
    for item in list(payload.get("ranking_ai_scores") or []):
        if not isinstance(item, dict):
            continue
        ai_score_row = item.get("ai_score_row")
        if isinstance(ai_score_row, dict):
            parser_status = str(
                ai_score_row.get("parser_status")
                or ai_score_row.get("reranker_parser_status")
                or ""
            ).strip().lower()
            score_reasoning = str(
                ai_score_row.get("score_reasoning")
                or ai_score_row.get("reranker_score_reasoning")
                or ""
            ).strip().lower()
            # Do not reuse poisoned reranker cache rows produced by parse failures.
            if (
                parser_status in {"malformed_json", "runtime_exception"}
                or "parse failure" in score_reasoning
                or "default credentials were not found" in score_reasoning
                or "application default credentials" in score_reasoning
            ):
                continue
        ranking_rows.append(dict(item))
    return {
        "ranking_ai_scores": ranking_rows,
        "cv_analysis_records": [
            dict(item)
            for item in list(payload.get("cv_analysis_records") or [])
            if isinstance(item, dict)
        ],
    }


def _index_late_stage_reuse_rows(
    rows: list[dict[str, Any]],
    *,
    fingerprint_key: str,
    payload_key: str,
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        fingerprint = str(row.get(fingerprint_key) or "").strip()
        payload = row.get(payload_key)
        if not fingerprint or not isinstance(payload, dict) or fingerprint in indexed:
            continue
        indexed[fingerprint] = deepcopy(payload)
    return indexed

def _index_cv_analysis_reuse_by_identity(
    rows: list[dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        payload = row.get("analysis_record")
        if not isinstance(payload, dict):
            continue
        identity_source = {
            **dict(payload.get("job_snapshot") or {}),
            **payload,
        }
        if not identity_source.get("job_url"):
            identity_source["job_url"] = str(row.get("job_url") or "")
        for identity_key in job_identity_keys(identity_source):
            indexed.setdefault(identity_key, deepcopy(payload))
    return indexed

def _build_late_stage_reuse_metrics(
    *,
    enriched: list[dict[str, Any]],
    ai_scores: list[dict[str, Any]],
    cv_analysis_results: list[dict[str, Any]],
    cv_generation_debug_records: list[dict[str, Any]],
) -> dict[str, Any]:
    reused_enrich_rows = sum(
        1 for row in enriched
        if str(row.get("enrich_reuse_status") or "") == REUSED_CACHED_ENRICHMENT_STATUS
    )
    fresh_enrich_rows = sum(
        1 for row in enriched
        if str(row.get("enrich_reuse_status") or "") == FRESH_ENRICHMENT_STATUS
    )
    reused_ai_scores = sum(
        1 for row in ai_scores
        if str(row.get("ai_score_reuse_status") or "") == "reused_exact_match"
    )
    fresh_ai_scores = sum(
        1 for row in ai_scores
        if str(row.get("ai_score_reuse_status") or "") == "fresh_compute"
    )
    executed_analysis_rows = [
        row for row in cv_analysis_results
        if str(row.get("status") or "") != CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS
    ]
    reused_analysis_rows = sum(
        1 for row in executed_analysis_rows
        if str(row.get("analysis_reuse_status") or "") == "reused_exact_match"
    )
    fresh_analysis_rows = sum(
        1 for row in executed_analysis_rows
        if str(row.get("analysis_reuse_status") or "") == "fresh_compute"
    )
    blocked_before_analysis_rows = sum(
        1 for row in cv_analysis_results
        if str(row.get("status") or "") == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS
    )
    generation_attempted_rows = [
        row for row in cv_generation_debug_records
        if str(row.get("status") or "") in CV_GENERATION_ATTEMPTED_STATUSES
    ]
    reused_cv_generations = sum(
        1 for row in generation_attempted_rows
        if str(row.get("cv_generation_reuse_status") or "") == "reused_exact_match"
    )
    fresh_cv_generations = sum(
        1 for row in generation_attempted_rows
        if str(row.get("cv_generation_reuse_status") or "") == "fresh_compute"
    )
    return {
        "enrich": {
            "reused_rows": reused_enrich_rows,
            "fresh_rows": fresh_enrich_rows,
            "total_rows": len(enriched),
            "reuse_rate": _safe_rate(reused_enrich_rows, len(enriched)),
        },
        "ranking": {
            "reused_ai_scores": reused_ai_scores,
            "fresh_ai_scores": fresh_ai_scores,
            "total_ai_scores": len(ai_scores),
            "reuse_rate": _safe_rate(reused_ai_scores, len(ai_scores)),
        },
        "cv_analysis": {
            "analysis_rows_executed": len(executed_analysis_rows),
            "reused_analysis_rows": reused_analysis_rows,
            "fresh_analysis_rows": fresh_analysis_rows,
            "blocked_before_analysis_rows": blocked_before_analysis_rows,
            "analysis_reuse_rate": _safe_rate(reused_analysis_rows, len(executed_analysis_rows)),
        },
        "cv_generation": {
            "reused_rows": reused_cv_generations,
            "fresh_rows": fresh_cv_generations,
            "total_rows": len(generation_attempted_rows),
            "reuse_rate": _safe_rate(reused_cv_generations, len(generation_attempted_rows)),
        },
    }

def _reuse_anomaly_payload(
    *,
    reuse_metrics: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any] | None:
    guard_cfg = dict((config.get("reuse") or {}).get("anomaly_guard") or {})
    min_overlap = int(guard_cfg.get("min_overlap", 5) or 5)
    floor = float(guard_cfg.get("reuse_rate_floor", 0.05) or 0.05)
    stages: list[dict[str, Any]] = []
    for stage_id, stage_metrics_raw in dict(reuse_metrics or {}).items():
        stage_metrics = dict(stage_metrics_raw or {})
        total = int(
            stage_metrics.get("total_rows")
            or stage_metrics.get("total_ai_scores")
            or stage_metrics.get("analysis_rows_executed")
            or 0
        )
        reused = int(
            stage_metrics.get("reused_rows")
            or stage_metrics.get("reused_ai_scores")
            or stage_metrics.get("reused_analysis_rows")
            or 0
        )
        fresh = int(
            stage_metrics.get("fresh_rows")
            or stage_metrics.get("fresh_ai_scores")
            or stage_metrics.get("fresh_analysis_rows")
            or 0
        )
        rate = float(stage_metrics.get("reuse_rate") or stage_metrics.get("analysis_reuse_rate") or 0.0)
        if reused <= 0 or total < min_overlap or rate >= floor:
            continue
        stages.append(
            {
                "stage_id": stage_id,
                "total": total,
                "reused": reused,
                "fresh": fresh,
                "reuse_rate": rate,
                "reason_histogram": {
                    "exact_fingerprint_match": reused,
                    "no_reusable_snapshot_match": fresh,
                },
            }
        )
    if not stages:
        return None
    return {
        "status": "breached",
        "min_overlap": min_overlap,
        "reuse_rate_floor": floor,
        "stages": stages,
    }


def _build_late_stage_reuse_snapshots(
    *,
    ai_scores: list[dict[str, Any]],
    cv_analysis_results: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "schema_version": "late_stage_reuse_v1",
        "ranking_ai_scores": [
            {
                "job_url": str(row.get("job_url") or ""),
                "ai_score_input_fingerprint": str(row.get("ai_score_input_fingerprint") or ""),
                "ai_score_row": deepcopy(row),
            }
            for row in ai_scores
            if str(row.get("job_url") or "") and str(row.get("ai_score_input_fingerprint") or "")
        ],
        "cv_analysis_records": [
            {
                "job_url": str(row.get("job_url") or ""),
                "analysis_input_fingerprint": str(row.get("analysis_input_fingerprint") or ""),
                "analysis_record": deepcopy(row),
            }
            for row in cv_analysis_results
            if str(row.get("job_url") or "") and str(row.get("analysis_input_fingerprint") or "")
        ],
    }


def _empty_pipeline_state(run_id: str) -> dict[str, Any]:
    return PipelineState(run_id=run_id).as_state_dict()


def _restore_pipeline_state(
    *,
    run_id: str,
    checkpoint_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    return PipelineState.from_checkpoint_payload(
        run_id=run_id,
        checkpoint_payload=checkpoint_payload,
    ).as_state_dict()


def _checkpoint_payload_from_state(state: dict[str, Any]) -> dict[str, Any]:
    keys = PipelineState.payload_keys()
    payload: dict[str, Any] = {
        "schema_version": int(getattr(PipelineState, "CHECKPOINT_SCHEMA_VERSION", 1)),
    }
    for key in keys:
        if key == "candidate_query_debug":
            payload[key] = json_safe_value(state.get(key) or {})
            continue
        if key == "completed_stage":
            value = str(state.get(key) or state.get("last_completed_stage") or "").strip()
            payload[key] = value or None
            continue
        payload[key] = json_safe_value(state.get(key) or [])
    return payload


def _infer_last_completed_stage_from_state(state: dict[str, Any]) -> str | None:
    return infer_last_completed_stage_from_state(state)


def _canonical_resume_start_stage(
    *,
    requested_start_stage: str | None,
    checkpoint_payload: dict[str, Any] | None,
    run_id: str,
) -> str | None:
    validated_start_stage = _validate_pipeline_stage_name(requested_start_stage)
    if not checkpoint_payload:
        return validated_start_stage

    resume_state = _restore_pipeline_state(run_id=run_id, checkpoint_payload=checkpoint_payload)
    last_completed_stage = _infer_last_completed_stage_from_state(resume_state)
    canonical_next_stage = next_pipeline_stage(last_completed_stage)
    if canonical_next_stage:
        return canonical_next_stage
    return validated_start_stage


def _collect_mapping_suggestions(enriched: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    seen_keys: set[tuple[str, str, str, str]] = set()
    for job in enriched:
        job_url = extract_job_url(job)
        job_title = extract_job_title(job)
        for suggestion in list(job.get("mapping_suggestions") or []):
            if not isinstance(suggestion, dict):
                continue
            record: dict[str, Any] = {
                "run_id": run_id,
                "job_url": job_url,
                "job_title": job_title,
                "must_have_skill": str(suggestion.get("must_have_skill") or ""),
                "matches": bool(suggestion.get("matches")),
                "confidence": float(suggestion.get("confidence") or 0.0),
                "alias": str(suggestion.get("alias") or ""),
                "canonical": str(suggestion.get("canonical") or ""),
                "field": str(suggestion.get("field") or "skill"),
            }
            if record["alias"] and record["canonical"]:
                dedupe_key = (
                    record["field"].strip().lower(),
                    record["alias"].strip().lower(),
                    record["canonical"].strip().lower(),
                    record["must_have_skill"].strip().lower(),
                )
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                suggestions.append(record)
        for field_name, source_key in (
            ("domain", "domain_mapping_suggestions"),
            ("role_family", "role_family_mapping_suggestions"),
        ):
            for suggestion in list(job.get(source_key) or []):
                if not isinstance(suggestion, dict):
                    continue
                alias = str(suggestion.get("alias") or "").strip()
                canonical = str(suggestion.get("canonical") or "").strip()
                if not alias or not canonical:
                    continue
                record = {
                    "run_id": run_id,
                    "job_url": job_url,
                    "job_title": job_title,
                    "must_have_skill": "",
                    "matches": bool(suggestion.get("matches", True)),
                    "confidence": float(suggestion.get("confidence") or 0.0),
                    "alias": alias,
                    "canonical": canonical,
                    "field": field_name,
                }
                dedupe_key = (
                    field_name,
                    alias.lower(),
                    canonical.lower(),
                    "",
                )
                if dedupe_key in seen_keys:
                    continue
                seen_keys.add(dedupe_key)
                suggestions.append(record)
    return suggestions


def _build_stage_progress_summary(
    *,
    run_id: str,
    last_completed_stage: str,
    state: dict[str, Any],
    profile: dict[str, Any] | None,
    config: dict[str, Any],
    vector_top_n: int | None = None,
    candidate_summary: str | None = None,
    candidate_query_components: dict[str, Any] | None = None,
    candidate_query_debug: dict[str, Any] | None = None,
    final_top_n: int | None = None,
) -> dict[str, Any]:
    raw_jobs = list(state.get("raw_jobs") or [])
    normalized = list(state.get("normalized") or [])
    deduplicated_jobs = list(state.get("deduplicated_jobs") or [])
    pre_filter_rejected_jobs = list(state.get("pre_filter_rejected_jobs") or [])
    enriched = list(state.get("enriched") or [])
    passed_jobs = list(state.get("passed_jobs") or [])
    candidate_filter_rejected_jobs = list(state.get("candidate_filter_rejected_jobs") or [])
    raw_shortlist = list(state.get("raw_shortlist") or [])
    shortlist = list(state.get("shortlist") or [])
    shortlist_audit_rows = list(state.get("_shortlist_audit_rows") or [])
    shortlist_diagnostics = dict(state.get("shortlist_diagnostics") or {})
    ai_scores = list(state.get("ai_scores") or [])
    enrich_llm_runtime_observations = list(state.get("enrich_llm_runtime_observations") or [])
    ranking_llm_runtime_observations = list(state.get("ranking_llm_runtime_observations") or [])
    ranking_inputs = list(state.get("ranking_inputs") or [])
    ranked = list(state.get("ranked") or [])
    cv_analysis_results = list(state.get("cv_analysis_results") or [])
    cv_generation_debug_records = list(state.get("cv_generation_debug_records") or [])
    cv_results = list(state.get("cv_results") or [])
    candidate_profile = profile or {"preferences": {}}
    vector_top_n_value = int(
        vector_top_n if vector_top_n is not None else pipeline_int(config, "vector_search_top_n", default=0)
    )
    final_top_n_value = int(
        final_top_n if final_top_n is not None else pipeline_int(config, "final_top_n", default=0)
    )
    candidate_summary_value = str(candidate_summary or "")
    candidate_query_components_value = dict(candidate_query_components or {})
    candidate_query_debug_value = dict(candidate_query_debug or state.get("candidate_query_debug") or {})
    stage_transition_artifacts = _build_stage_transition_artifacts(
        raw_jobs=raw_jobs,
        normalized=normalized,
        deduplicated_jobs=deduplicated_jobs,
        pre_filter_rejected_jobs=pre_filter_rejected_jobs,
        enriched=enriched,
        passed_jobs=passed_jobs,
        candidate_filter_rejected_jobs=candidate_filter_rejected_jobs,
        raw_shortlist=raw_shortlist,
        shortlist=shortlist,
        shortlist_audit_rows=shortlist_audit_rows,
        shortlist_diagnostics=shortlist_diagnostics,
        vector_top_n=vector_top_n_value,
        candidate_summary=candidate_summary_value,
        candidate_query_components=candidate_query_components_value,
        candidate_query_debug=candidate_query_debug_value,
        ai_scores=ai_scores,
        ranking_inputs=ranking_inputs,
        ranked=ranked,
        cv_analysis_results=cv_analysis_results,
        enrich_llm_runtime_observations=enrich_llm_runtime_observations,
        ranking_llm_runtime_observations=ranking_llm_runtime_observations,
        final_top_n=final_top_n_value,
        cv_generation_debug_records=cv_generation_debug_records,
        profile=candidate_profile,
        config=config,
        resolved_preference_policy=dict(state.get("resolved_preference_policy") or {}),
    )
    return {
        "run_id": run_id,
        "last_completed_stage": last_completed_stage,
        "completed_stages": completed_pipeline_stages_through(last_completed_stage),
        "next_stage": next_pipeline_stage(last_completed_stage),
        "total_jobs": len(raw_jobs),
        "passed_filter": len(passed_jobs),
        "ranked": len(ranked),
        "cvs_generated": len(cv_results),
        "mapping_suggestions": _collect_mapping_suggestions(enriched, run_id),
        "stage_transition_artifacts": stage_transition_artifacts,
    }


def _build_checkpoint_summary(
    *,
    run_id: str,
    paused_after_stage: str,
    state: dict[str, Any],
    profile: dict[str, Any] | None,
    config: dict[str, Any],
    vector_top_n: int | None = None,
    candidate_summary: str | None = None,
    candidate_query_components: dict[str, Any] | None = None,
    candidate_query_debug: dict[str, Any] | None = None,
    final_top_n: int | None = None,
) -> dict[str, Any]:
    summary = _build_stage_progress_summary(
        run_id=run_id,
        last_completed_stage=paused_after_stage,
        state=state,
        profile=profile,
        config=config,
        vector_top_n=vector_top_n,
        candidate_summary=candidate_summary,
        candidate_query_components=candidate_query_components,
        candidate_query_debug=candidate_query_debug,
        final_top_n=final_top_n,
    )
    cv_analysis_results = list(state.get("cv_analysis_results") or [])
    cv_generation_debug_records = list(state.get("cv_generation_debug_records") or [])
    ranked = list(state.get("ranked") or [])
    summary["cv_analysis_trace"] = _build_cv_analysis_trace_summary(
        run_id=run_id,
        cv_analysis_results=cv_analysis_results,
    )
    summary["cv_generation_trace"] = _build_cv_generation_trace_summary(
        run_id=run_id,
        cv_generation_debug_records=cv_generation_debug_records,
    )
    summary["paused_after_stage"] = paused_after_stage
    checkpoint_payload = _checkpoint_payload_from_state(state)
    checkpoint_payload["completed_stage"] = paused_after_stage
    summary["checkpoint_payload"] = checkpoint_payload
    return summary


def _handle_stage_boundary(
    *,
    run_id: str,
    last_completed_stage: str,
    stop_after_stage: str | None,
    state: dict[str, Any],
    profile: dict[str, Any] | None,
    config: dict[str, Any],
    vector_top_n: int,
    candidate_summary: str,
    candidate_query_components: dict[str, Any],
    candidate_query_debug: dict[str, Any],
    final_top_n: int,
    stage_progress_callback: Callable[[dict[str, Any]], None] | None,
) -> dict[str, Any] | None:
    if stage_progress_callback is not None:
        stage_progress_callback(
            _build_stage_progress_summary(
                run_id=run_id,
                last_completed_stage=last_completed_stage,
                state=state,
                profile=profile,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                candidate_query_components=candidate_query_components,
                candidate_query_debug=candidate_query_debug,
                final_top_n=final_top_n,
            )
        )
    if stop_after_stage == last_completed_stage:
        return _build_checkpoint_summary(
            run_id=run_id,
            paused_after_stage=last_completed_stage,
            state=state,
            profile=profile,
            config=config,
            vector_top_n=vector_top_n,
            candidate_summary=candidate_summary,
            candidate_query_components=candidate_query_components,
            candidate_query_debug=candidate_query_debug,
            final_top_n=final_top_n,
        )
    return None


# ── helpers ───────────────────────────────────────────────────────────────────

def create_run_id() -> str:
    """Return a new UUID4 string to identify this pipeline run."""
    return str(uuid.uuid4())


def _cv_generation_enabled_sections(config: dict[str, Any]) -> list[str]:
    composition = (config.get("cv") or {}).get("composition") or {}
    enabled_sections: list[str] = []
    for section_key, section_cfg in composition.items():
        if isinstance(section_cfg, dict) and section_cfg.get("enabled", True):
            enabled_sections.append(CV_SECTION_KEY_TO_NAME.get(section_key, section_key.title()))
    return enabled_sections



def _cv_analysis_stage_concurrency(config: dict[str, Any]) -> int:
    return get_stage_runtime_concurrency(config, stage="cv_analysis", default=1)

def _enrich_stage_concurrency(config: dict[str, Any]) -> int:
    return get_stage_runtime_concurrency(
        config,
        stage="enrich",
        default=1,
        compatibility_fallback_key="enrichment_concurrency",
    )

def _ranking_stage_concurrency(config: dict[str, Any]) -> int:
    return get_stage_runtime_concurrency(config, stage="ranking", default=1)


def _effective_stage_concurrency(configured_concurrency: int, work_items: int) -> int:
    return min(max(int(configured_concurrency), 1), max(int(work_items), 0))


def _build_validation_grounding_payload(
    *,
    evidence_payload: list[dict[str, Any]],
    evidence_used: list[dict[str, Any]],
    evidence_selection_summary: dict[str, Any] | None,
    analysis_input_summary: dict[str, Any] | None,
) -> AnalysisGroundingPayload:
    return {
        "evidence_payload": list(evidence_payload),
        "evidence_used": list(evidence_used),
        "evidence_selection_summary": dict(evidence_selection_summary or {}),
        "analysis_input_summary": dict(analysis_input_summary or {}),
    }


def _resolve_layer4_fit(
    job: dict[str, Any],
    gap_fit: str | None,
    config: dict[str, Any],
) -> str:
    """Return the authoritative post-filter fit label for a ranked job."""
    del gap_fit
    return resolve_ranked_job_fit(job, config)


def _shortlist_status_for_export_row(
    *,
    job_url: str,
    passed_job_urls: set[str],
    raw_shortlist_row: dict[str, Any] | None,
    scoring_shortlist_row: dict[str, Any] | None,
) -> str:
    if job_url not in passed_job_urls:
        return "not_applicable"
    if raw_shortlist_row is not None:
        return "returned_by_vector_search"
    if scoring_shortlist_row is not None:
        return "advanced_to_scoring"
    return "not_returned_in_raw_hits"


_bounded_event_payload = _build_bounded_event_payload_observability


def _extract_generation_trace_metrics(cv_generation_trace: dict[str, Any] | None) -> dict[str, Any]:
    trace = dict(cv_generation_trace or {})
    attempts = [
        dict(item)
        for item in list(trace.get("attempts") or [])
        if isinstance(item, dict)
    ]
    latencies = [
        int(item.get("latency_ms") or 0)
        for item in attempts
        if int(item.get("latency_ms") or 0) > 0
    ]
    total_latency_ms = int(sum(latencies)) if latencies else None
    retry_count = max(0, len(attempts) - 1)
    final_attempt = attempts[-1] if attempts else {}

    usage_block = None
    for key in ("usage", "token_usage", "response_usage"):
        value = final_attempt.get(key)
        if isinstance(value, dict):
            usage_block = dict(value)
            break
    cost_block = None
    if isinstance(final_attempt.get("cost"), dict):
        cost_block = dict(final_attempt["cost"])
    elif final_attempt.get("cost_usd") is not None:
        cost_block = {"usd": final_attempt.get("cost_usd")}

    return {
        "latency_ms": total_latency_ms,
        "attempt_count": len(attempts),
        "retry_count": retry_count,
        "usage": usage_block,
        "cost": cost_block,
    }


def _build_analysis_evidence_selection_summary(
    evidence_bundle: dict[str, Any],
    evidence: list[dict[str, Any]],
    *,
    fallback_used: bool,
) -> dict[str, Any]:
    payload = {
        "channel_counts": normalize_analysis_channel_mapping(
            evidence_bundle.get("channel_counts") or {}
        ),
        "fallback_used": fallback_used,
        "effective_channel_pool_size": int(evidence_bundle.get("effective_channel_pool_size") or 0),
        "merged_pool_size": int(evidence_bundle.get("merged_pool_size") or 0),
        "deduped_pool_size": int(evidence_bundle.get("deduped_pool_size") or 0),
        "selected_evidence_count": len(evidence),
        "selected_evidence_ids": list(evidence_bundle.get("selected_evidence_ids") or []),
        "unselected_top_candidates": list(evidence_bundle.get("unselected_top_candidates") or []),
        "hybrid_alignment": normalize_analysis_channel_mapping(
            evidence_bundle.get("hybrid_alignment") or {}
        ),
        "semantic_alignment": dict(evidence_bundle.get("semantic_alignment") or {}),
    }
    return {key: value for key, value in payload.items() if value not in ({}, [], None)}


def _render_cv_analysis_item_input(*, profile: dict[str, Any], job: dict[str, Any]) -> str:
    job_title = extract_job_title(job) or "Unknown job"
    required_skills = bound_langfuse_list(
        [str(item).strip() for item in list(job.get("required_skills") or []) if str(item).strip()],
        max_items=8,
        max_item_chars=300,
    )
    candidate_skills = bound_langfuse_list(
        flatten_skills(profile),
        max_items=20,
        max_item_chars=80,
    )
    experience_highlights = bound_langfuse_list(
        list(profile.get("experience_highlights") or []),
        max_items=8,
        max_item_chars=300,
    )
    sections = [
        (
            "## Job",
            [f"Title: {job_title}"],
        ),
    ]
    sections.append(("### Job Excerpt", [bound_langfuse_excerpt(str(job.get("description") or ""), max_chars=1500) or ""]))
    sections.append(("### Requirements Excerpt", [f"- {item}" for item in required_skills]))
    sections.append(("## Candidate", [f"Headline: {bound_langfuse_excerpt(str(profile.get('headline') or ''), max_chars=240) or 'Unknown candidate'}"]))
    sections.append(("### Skills", [f"- {item}" for item in candidate_skills]))
    sections.append(("### Experience Highlights", [f"- {item}" for item in experience_highlights]))
    sections.append(
        (
            "## Instructions",
            [
                bound_langfuse_excerpt(
                    str(job.get("analysis_instructions") or "Evaluate fit for generation readiness."),
                    max_chars=2000,
                )
                or "Evaluate fit for generation readiness."
            ],
        )
    )
    sections.append(("## Rubric", ["- domain", "- seniority", "- stack", "- scope"]))
    return render_langfuse_markdown_sections(sections)


def _render_cv_analysis_item_output(analysis_record: dict[str, Any]) -> str:
    return _render_cv_analysis_item_output_observability(
        analysis_record,
        bound_langfuse_list=bound_langfuse_list,
        bound_langfuse_excerpt=bound_langfuse_excerpt,
        render_langfuse_markdown_sections=render_langfuse_markdown_sections,
    )


def _build_cv_analysis_item_observation_attributes(
    *,
    run_id: str,
    profile: dict[str, Any],
    job: dict[str, Any],
    analysis_record: dict[str, Any],
) -> dict[str, Any]:
    return _build_cv_analysis_item_observation_attributes_observability(
        run_id=run_id,
        profile=profile,
        job=job,
        analysis_record=analysis_record,
        extract_job_url=extract_job_url,
        extract_job_title=extract_job_title,
        flatten_skills=flatten_skills,
        bound_langfuse_list=bound_langfuse_list,
        bound_langfuse_excerpt=bound_langfuse_excerpt,
        build_langfuse_item_observation_attributes=build_langfuse_item_observation_attributes,
        render_cv_analysis_item_input=_render_cv_analysis_item_input,
        render_cv_analysis_item_output=_render_cv_analysis_item_output,
    )


def _emit_cv_analysis_item_observation(
    *,
    run_id: str,
    profile: dict[str, Any],
    job: dict[str, Any],
    analysis_record: dict[str, Any],
) -> None:
    attributes = _build_cv_analysis_item_observation_attributes(
        run_id=run_id,
        profile=profile,
        job=job,
        analysis_record=analysis_record,
    )
    with observe_span("pipeline.cv_analysis_item", attributes=attributes):
        return


def _render_cv_generation_item_input(
    *,
    job: dict[str, Any],
    evidence_used: list[dict[str, Any]],
    fit_classification: str | None,
) -> str:
    required_skills = bound_langfuse_list(
        [str(item).strip() for item in list(job.get("required_skills") or []) if str(item).strip()],
        max_items=8,
        max_item_chars=300,
    )
    evidence_lines = bound_langfuse_list(
        [
            str(item.get("name") or item.get("source_ref") or item.get("evidence_type") or "evidence").strip()
            for item in evidence_used
            if str(item.get("name") or item.get("source_ref") or item.get("evidence_type") or "").strip()
        ],
        max_items=8,
        max_item_chars=240,
    )
    sections = [
        ("## Job", [f"Title: {extract_job_title(job) or 'Unknown job'}"]),
        ("### Job Excerpt", [bound_langfuse_excerpt(str(job.get("description") or ""), max_chars=1500) or ""]),
        ("### Constraints", [f"- {item}" for item in required_skills]),
        ("## Analysis Inputs", [f"Fit Classification: {fit_classification or 'unknown'}"]),
        ("## Selected Evidence", [f"- {item}" for item in evidence_lines] or ["- No evidence selected"]),
        (
            "## Generation Instructions",
            [
                bound_langfuse_excerpt(
                    str(job.get("generation_instructions") or "Generate grounded CV sections only from selected evidence."),
                    max_chars=2000,
                )
                or "Generate grounded CV sections only from selected evidence."
            ],
        ),
    ]
    return render_langfuse_markdown_sections(sections)


def _render_cv_generation_item_output(debug_record: dict[str, Any]) -> str:
    return _render_cv_generation_item_output_observability(
        debug_record,
        cv_generation_review_required_status=CV_GENERATION_REVIEW_REQUIRED_STATUS,
        bound_langfuse_markdown=bound_langfuse_markdown,
        bound_langfuse_excerpt=bound_langfuse_excerpt,
        bound_langfuse_issue_list=bound_langfuse_issue_list,
        render_langfuse_markdown_sections=render_langfuse_markdown_sections,
    )


def _build_cv_generation_item_observation_attributes(
    *,
    run_id: str,
    analysis_record: dict[str, Any],
    debug_record: dict[str, Any],
) -> dict[str, Any]:
    return _build_cv_generation_item_observation_attributes_observability(
        run_id=run_id,
        analysis_record=analysis_record,
        debug_record=debug_record,
        cv_generation_review_required_status=CV_GENERATION_REVIEW_REQUIRED_STATUS,
        extract_job_url=extract_job_url,
        extract_job_title=extract_job_title,
        bound_langfuse_list=bound_langfuse_list,
        bound_langfuse_excerpt=bound_langfuse_excerpt,
        bound_langfuse_issue_list=bound_langfuse_issue_list,
        bound_langfuse_markdown=bound_langfuse_markdown,
        build_langfuse_item_observation_attributes=build_langfuse_item_observation_attributes,
        render_cv_generation_item_input=_render_cv_generation_item_input,
        render_cv_generation_item_output=_render_cv_generation_item_output,
    )


def _emit_cv_generation_item_observation(
    *,
    run_id: str,
    analysis_record: dict[str, Any],
    debug_record: dict[str, Any],
) -> None:
    attributes = _build_cv_generation_item_observation_attributes(
        run_id=run_id,
        analysis_record=analysis_record,
        debug_record=debug_record,
    )
    with observe_span("pipeline.cv_generation_item", attributes=attributes):
        return


def _authoritative_ranking_fit_label(
    job: dict[str, Any],
    fit_classification: str | None,
) -> str | None:
    ranked_fit_raw = str(job.get("baseline_fit_label") or "").strip().lower()
    if ranked_fit_raw in _FIT_LABEL_ORDER:
        return ranked_fit_raw
    fallback_fit_raw = str(fit_classification or "").strip().lower()
    return fallback_fit_raw or None



def _build_decision_chain(
    *,
    shortlist_status: str,
    advanced_to_scoring: bool,
    ranking_fit_label: str | None,
    ranking_fit_source: str | None,
    cv_analysis_status: str = "not_run",
    cv_status: str,
) -> dict[str, Any]:
    return {
        "shortlist": {
            "status": shortlist_status,
            "advanced_to_scoring": advanced_to_scoring,
        },
        "primary_fit": {
            "source": ranking_fit_source,
            "label": ranking_fit_label,
        },
        "cv_analysis": {
            "status": cv_analysis_status,
            "completed": cv_analysis_status not in {"not_run", "failed", CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS},
        },
        "cv_generation": {
            "status": cv_status,
            "attempted": cv_status not in {"not_applicable", "not_attempted", "skipped_fit_gate"},
        },
        "validation": {
            "status": _validation_status_for_cv_status(cv_status),
        },
    }


def _build_cv_generation_debug_record(
    *,
    generation_result: dict[str, Any],
    enabled_sections: list[str],
    cv_generation_model: str | None,
    cv_prompt_id: str,
    cv_prompt_template_path: str,
    attempt_count: int = 1,
) -> dict[str, Any]:
    payload = deepcopy(generation_result)
    validation = generation_result.get("validation") or generation_result.get("validation_initial")
    reason = generation_result.get("outcome_reason") or generation_result.get("error")
    payload.update(
        {
            "validation_final": generation_result.get("validation"),
            "enabled_sections": list(enabled_sections),
            "cv_generation_model": _resolved_cv_generation_model(
                cv_generation_model,
                cast(list[dict[str, Any]], generation_result.get("llm_runtime_observations") or []),
            ),
            "cv_prompt_id": cv_prompt_id,
            "cv_prompt_template_path": cv_prompt_template_path,
            "attempt_count": attempt_count,
            "failed_rule_ids": _extract_failed_rule_ids(cast(dict[str, Any] | None, validation)),
            "first_failing_section_key": _first_failing_section_key(cast(dict[str, Any] | None, validation)),
            "operator_note": _build_operator_note(
                status=str(generation_result.get("status") or ""),
                error=cast(dict[str, str] | None, reason),
                validation_initial=cast(dict[str, Any] | None, validation),
            ),
        }
    )
    return payload


def _resolved_cv_generation_model(
    default_model: str | None,
    runtime_observations: list[dict[str, Any]] | None,
) -> str | None:
    for observation in reversed(list(runtime_observations or [])):
        evidence = dict(observation.get("evidence") or {})
        provenance = dict(evidence.get("provenance") or {})
        runtime_model = str(provenance.get("model") or "").strip()
        if runtime_model:
            return runtime_model
    return default_model



def _extract_failed_rule_ids(validation: dict[str, Any] | None) -> list[str]:
    if not isinstance(validation, dict):
        return []
    rule_ids: list[str] = []
    keys = (
        "grounding_violations",
        "deterministic_grounding_violations",
        "semantic_grounding_violations",
        "skill_violations",
        "markdown_quality_blocking_issues",
    )
    for key in keys:
        for item in list(validation.get(key) or []):
            if isinstance(item, dict):
                rule_id = str(item.get("rule_id") or item.get("code") or "").strip()
                if rule_id:
                    rule_ids.append(rule_id)
            elif isinstance(item, str) and item.strip():
                rule_ids.append(item.strip())
    return sorted(set(rule_ids))

def _first_failing_section_key(validation: dict[str, Any] | None) -> str | None:
    if not isinstance(validation, dict):
        return None
    missing_sections = [str(item).strip() for item in list(validation.get("missing_sections") or []) if str(item).strip()]
    return missing_sections[0] if missing_sections else None

def _build_operator_note(
    *,
    status: str,
    error: dict[str, str] | None,
    validation_initial: dict[str, Any] | None,
) -> str | None:
    if status in {"validation_failed", CV_GENERATION_REVIEW_REQUIRED_STATUS}:
        failed_rule_ids = _extract_failed_rule_ids(validation_initial)
        if failed_rule_ids:
            return f"Validation failed with {len(failed_rule_ids)} rule(s)."
        failing_section = _first_failing_section_key(validation_initial)
        if failing_section:
            return f"Validation failed in section '{failing_section}'."
    message = str((error or {}).get("message") or "").strip()
    return message or None

def _summarize_cv_generation_model(
    cv_generation_debug_records: list[dict[str, Any]],
    default_model: str | None,
) -> str | None:
    models = [
        str(record.get("cv_generation_model") or "").strip()
        for record in cv_generation_debug_records
        if str(record.get("status") or "") in CV_GENERATION_ATTEMPTED_STATUSES
        and str(record.get("cv_generation_model") or "").strip()
    ]
    unique_models = sorted(set(models))
    if len(unique_models) == 1:
        return unique_models[0]
    if len(unique_models) > 1:
        return "mixed"
    return default_model


def _summarize_cv_generation_provider(
    cv_generation_debug_records: list[dict[str, Any]],
) -> str | None:
    providers = [
        str((observation.get("evidence") or {}).get("provenance", {}).get("provider") or "").strip()
        for record in cv_generation_debug_records
        if str(record.get("status") or "") in CV_GENERATION_ATTEMPTED_STATUSES
        for observation in list(record.get("llm_runtime_observations") or [])
        if isinstance(observation, dict)
        and isinstance(observation.get("evidence"), dict)
        and isinstance((observation.get("evidence") or {}).get("provenance"), dict)
        and str((observation.get("evidence") or {}).get("provenance", {}).get("provider") or "").strip()
    ]
    unique_providers = sorted(set(providers))
    if len(unique_providers) == 1:
        return unique_providers[0]
    if len(unique_providers) > 1:
        return "mixed"
    return None


def _build_cv_generation_trace_summary(
    *,
    run_id: str | None,
    cv_generation_debug_records: list[dict[str, Any]],
) -> dict[str, Any]:
    attempted_records = [
        record for record in cv_generation_debug_records
        if str(record.get("status") or "") in CV_GENERATION_ATTEMPTED_STATUSES
    ]
    trace_records: list[dict[str, Any]] = []
    for record in attempted_records:
        raw_trace = record.get("cv_generation_trace")
        if not isinstance(raw_trace, dict):
            continue
        trace_record = dict(raw_trace)
        job_url = str(record.get("job_url") or "").strip()
        trace_record.setdefault("record_id", job_url or str(record.get("job_title") or "").strip())
        trace_record.setdefault("scope_type", "job")
        trace_record.setdefault("scope_key", job_url)
        trace_record["status"] = str(record.get("status") or "")
        trace_record["decision_chain"] = dict(record.get("decision_chain") or {})
        trace_record["artifact_refs"] = {
            "cv_debug_artifact": "cv-debug.json",
            "stage_artifact": "cv_generation.json",
        }
        trace_records.append(trace_record)
    attempted_total = len(attempted_records)
    present_total = len(trace_records)
    trace_status = "completed"
    degradation: dict[str, Any] = {}
    if attempted_total == 0:
        trace_status = "partial"
        degradation = {"reason": "no_attempted_generation_records"}
    elif present_total < attempted_total:
        trace_status = "partial"
        degradation = {"reason": "missing_job_trace_records"}
    elif any(str(trace.get("trace_status") or "") == "degraded" for trace in trace_records):
        trace_status = "degraded"
        degradation = {"reason": "provider_or_capture_degraded"}
    return {
        "run_id": run_id,
        "trace_schema_version": "stage_execution_trace_run_v1",
        "trace_family": "stage_execution_trace",
        "step_id": "cv_generation",
        "trace_status": trace_status,
        "trace_summary": {
            "records_total": attempted_total,
            "present_records": present_total,
            "attempted_generation_jobs_total": attempted_total,
        },
        "records": trace_records,
        "degradation": degradation,
        "artifact_refs": {
            "cv_debug_artifact": "cv-debug.json",
            "stage_artifact": "cv_generation.json",
        },
    }


def _build_cv_analysis_trace_summary(
    *,
    run_id: str | None,
    cv_analysis_results: list[dict[str, Any]],
) -> dict[str, Any]:
    trace_records: list[dict[str, Any]] = []
    attempted_total = 0
    for record in cv_analysis_results:
        status = str(record.get("status") or "").strip()
        if status != CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS:
            attempted_total += 1
        raw_trace = record.get("cv_analysis_trace")
        if not isinstance(raw_trace, dict):
            continue
        trace_record = dict(raw_trace)
        job_url = str(record.get("job_url") or "").strip()
        trace_record.setdefault("record_id", job_url or str(record.get("job_title") or "").strip())
        trace_record.setdefault("scope_type", "job")
        trace_record.setdefault("scope_key", job_url)
        trace_record["status"] = status
        trace_record["decision_chain"] = dict(record.get("decision_chain") or {})
        trace_record["artifact_refs"] = {
            "cv_debug_artifact": "cv-debug.json",
            "stage_artifact": "cv_analysis.json",
        }
        trace_records.append(trace_record)

    records_total = len(cv_analysis_results)
    present_total = len(trace_records)
    trace_status = "completed"
    degradation: dict[str, Any] = {}
    if records_total == 0:
        trace_status = "partial"
        degradation = {"reason": "no_cv_analysis_records"}
    elif present_total < records_total:
        trace_status = "partial"
        degradation = {"reason": "missing_job_trace_records"}
    elif any(str(trace.get("trace_status") or "").strip() == "degraded" for trace in trace_records):
        trace_status = "degraded"
        degradation = {"reason": "analysis_or_capture_degraded"}

    return {
        "run_id": run_id,
        "trace_schema_version": "stage_execution_trace_run_v1",
        "trace_family": "stage_execution_trace",
        "step_id": "cv_analysis",
        "trace_status": trace_status,
        "trace_summary": {
            "records_total": records_total,
            "present_records": present_total,
            "attempted_analysis_jobs_total": attempted_total,
        },
        "records": trace_records,
        "degradation": degradation,
        "artifact_refs": {
            "cv_debug_artifact": "cv-debug.json",
            "stage_artifact": "cv_analysis.json",
        },
    }


def _stage_block_not_reached(stage: str) -> dict[str, Any]:
    def _stage_result_builder(stage_id: str) -> dict[str, Any]:
        return _build_stage_result(
            stage_id=stage_id,
            status="not_reached",
            input_counts={},
            output_counts={},
            decision_summary={},
        )

    return _build_stage_block_not_reached_artifacts(
        stage=stage,
        stage_result_builder=_stage_result_builder,
    )


def _truncate_stage_text(value: str, *, limit: int = _STAGE_ARTIFACT_TEXT_LIMIT) -> str:
    return _truncate_stage_text_artifacts(value, limit=limit)


def _truncate_stage_value(value: Any) -> Any:
    return _truncate_stage_value_artifacts(value, text_limit=_STAGE_ARTIFACT_TEXT_LIMIT)


def _sample_rows(
    rows: list[Any],
    row_builder: Callable[[Any], dict[str, Any] | None],
    *,
    limit: int = _STAGE_ARTIFACT_SAMPLE_LIMIT,
) -> list[dict[str, Any]]:
    return _sample_rows_artifacts(
        rows,
        row_builder,
        limit=limit,
        text_limit=_STAGE_ARTIFACT_TEXT_LIMIT,
    )


def _sample_strings(values: list[str], *, limit: int = _STAGE_ARTIFACT_SAMPLE_LIMIT) -> list[str]:
    return _sample_strings_artifacts(
        values,
        limit=limit,
        text_limit=_STAGE_ARTIFACT_TEXT_LIMIT,
    )


def _safe_rate(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return float(numerator) / float(denominator)


def _build_shortlist_quality_metrics(
    *,
    diagnostics: dict[str, Any],
) -> dict[str, Any]:
    metric_keys = (
        "eligible_jobs_total",
        "scored_jobs_total",
        "production_shortlist_total",
        "production_cutoff_rank",
        "production_cutoff_similarity",
        "missing_job_embedding_total",
        "invalid_job_embedding_total",
        "embedding_coverage_rate",
        "audit_candidate_total",
        "audit_sample_total",
        "audit_sample_fingerprint",
    )
    return {key: diagnostics.get(key) for key in metric_keys}


def _build_ranking_quality_metrics(ranking_inputs: list[dict[str, Any]], config: dict[str, Any] | None = None) -> dict[str, Any]:
    strong_count = 0
    stretch_count = 0
    skip_count = 0
    for row in ranking_inputs:
        fit_label = str(row.get("baseline_fit_label") or "").strip().lower()
        if fit_label == "strong":
            strong_count += 1
        elif fit_label == "stretch":
            stretch_count += 1
        elif fit_label == "skip":
            skip_count += 1
    total_scored = strong_count + stretch_count + skip_count
    return {
        "label_distribution": {
            "strong_count": strong_count,
            "stretch_count": stretch_count,
            "skip_count": skip_count,
            "strong_rate": _safe_rate(strong_count, total_scored),
            "stretch_rate": _safe_rate(stretch_count, total_scored),
            "skip_rate": _safe_rate(skip_count, total_scored),
            "total_scored": total_scored,
        }
    }


def _build_cv_analysis_quality_metrics(cv_analysis_results: list[dict[str, Any]]) -> dict[str, Any]:
    blocked_by_reranker_fit = 0
    ready_for_generation = 0
    skipped_fit_gate = 0
    analysis_failed = 0
    for record in cv_analysis_results:
        status = str(record.get("status") or "").strip().lower()
        if status == CV_ANALYSIS_READY_FOR_GENERATION_STATUS:
            ready_for_generation += 1
        elif status == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS:
            blocked_by_reranker_fit += 1
        elif status == CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS:
            skipped_fit_gate += 1
        elif status == CV_ANALYSIS_FAILED_STATUS:
            analysis_failed += 1
    total_processed = ready_for_generation + blocked_by_reranker_fit + skipped_fit_gate + analysis_failed
    return {
        "blocked_by_reranker_fit_rate": _safe_rate(blocked_by_reranker_fit, total_processed),
        "skip_rate": _safe_rate(skipped_fit_gate, total_processed),
        "ready_for_generation_rate": _safe_rate(ready_for_generation, total_processed),
        "analysis_failed_rate": _safe_rate(analysis_failed, total_processed),
        "blocked_by_reranker_fit": blocked_by_reranker_fit,
        "skipped_fit_gate": skipped_fit_gate,
        "ready_for_generation": ready_for_generation,
        "analysis_failed": analysis_failed,
        "total_processed": total_processed,
    }


def _build_cv_generation_quality_metrics(
    cv_generation_debug_records: list[dict[str, Any]],
) -> dict[str, Any]:
    accepted = 0
    review_required = 0
    validation_failed = 0
    generation_failed = 0
    persistence_failed = 0
    for record in cv_generation_debug_records:
        status = str(record.get("status") or "").strip().lower()
        if status == "accepted":
            accepted += 1
        elif status == CV_GENERATION_REVIEW_REQUIRED_STATUS:
            review_required += 1
        elif status == "validation_failed":
            validation_failed += 1
        elif status == "generation_failed":
            generation_failed += 1
        elif status == "persistence_failed":
            persistence_failed += 1
    total_attempted = accepted + review_required + validation_failed + generation_failed + persistence_failed
    return {
        "validation_fail_rate": _safe_rate(validation_failed, total_attempted),
        "accepted_rate": _safe_rate(accepted, total_attempted),
        "review_required_rate": _safe_rate(review_required, total_attempted),
        "generation_failed_rate": _safe_rate(generation_failed, total_attempted),
        "persistence_failed_rate": _safe_rate(persistence_failed, total_attempted),
        "accepted": accepted,
        "review_required": review_required,
        "validation_failed": validation_failed,
        "generation_failed": generation_failed,
        "persistence_failed": persistence_failed,
        "total_attempted": total_attempted,
    }


def _collect_stage_quality_metrics(stage_transition_artifacts: dict[str, Any]) -> dict[str, Any]:
    stage_metrics: dict[str, Any] = {}
    for stage_id, block in dict(stage_transition_artifacts.get("stages") or {}).items():
        metrics = dict(block.get("decision_summary") or {}).get("quality_metrics")
        if isinstance(metrics, dict) and metrics:
            stage_metrics[stage_id] = metrics
    return stage_metrics


def _job_sample(job: dict[str, Any]) -> dict[str, Any] | None:
    return job_sample(job, export_fields=_EXPORT_ENRICHED_JOB_FIELDS)

def _candidate_profile_summary(profile: dict[str, Any], config: dict[str, Any] | None = None) -> dict[str, Any]:
    return candidate_profile_summary(profile, config)


def _shortlist_row_sample(row: dict[str, Any]) -> dict[str, Any] | None:
    return shortlist_row_sample(row)


def _rule_filter_decision_sample(
    row: dict[str, Any],
    *,
    filter_outcome: str,
) -> dict[str, Any] | None:
    base = job_sample(row, export_fields=_EXPORT_ENRICHED_JOB_FIELDS)
    if not base:
        return None
    sample = {
        **base,
        "filter_outcome": filter_outcome,
        "reasons": list(row.get("reasons") or []),
        "marks": list(row.get("marks") or []),
    }
    return {
        key: value
        for key, value in sample.items()
        if value not in (None, "", [])
    }


def _ranking_row_sample(row: dict[str, Any]) -> dict[str, Any] | None:
    return ranking_row_sample(row)


def _analysis_record_output_sample(record: dict[str, Any]) -> dict[str, Any] | None:
    return analysis_record_output_sample(
        record,
        deterministic_truth_fields=_deterministic_truth_fields,
    )


def _analysis_record_changed_sample(record: dict[str, Any]) -> dict[str, Any] | None:
    return analysis_record_changed_sample(
        record,
        deterministic_truth_fields=_deterministic_truth_fields,
    )


def _debug_record_output_sample(record: dict[str, Any]) -> dict[str, Any] | None:
    return debug_record_output_sample(
        record,
        deterministic_truth_fields=_deterministic_truth_fields,
    )


def _debug_record_changed_sample(record: dict[str, Any]) -> dict[str, Any] | None:
    return debug_record_changed_sample(
        record,
        deterministic_truth_fields=_deterministic_truth_fields,
    )


def _stage_block(
    *,
    stage_id: str,
    status: str,
    input_counts: dict[str, Any],
    output_counts: dict[str, Any],
    decision_summary: dict[str, Any],
    inputs_sample: list[dict[str, Any]],
    outputs_sample: list[dict[str, Any]],
    dropped_or_changed_sample: list[dict[str, Any]],
    settings_refs: list[str] | None = None,
    llm_runtime_observations: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    def _stage_result_builder(
        local_stage_id: str,
        local_status: str,
        local_input_counts: dict[str, Any],
        local_output_counts: dict[str, Any],
        local_decision_summary: dict[str, Any],
    ) -> dict[str, Any]:
        return _build_stage_result(
            stage_id=local_stage_id,
            status=local_status,
            input_counts=local_input_counts,
            output_counts=local_output_counts,
            decision_summary=local_decision_summary,
        )

    return cast(
        dict[str, Any],
        _build_stage_block_artifacts(
            stage_id=stage_id,
            status=status,
            input_counts=input_counts,
            output_counts=output_counts,
            decision_summary=decision_summary,
            inputs_sample=inputs_sample,
            outputs_sample=outputs_sample,
            dropped_or_changed_sample=dropped_or_changed_sample,
            settings_refs=settings_refs,
            llm_runtime_observations=llm_runtime_observations,
            truncate_value=_truncate_stage_value,
            stage_result_builder=_stage_result_builder,
        ),
    )


def _otel_id(seed: str, *, length: int) -> str:
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:length]


def _resolve_stage_decision(
    *,
    status: str,
    decision_summary: dict[str, Any],
) -> str:
    if status == "not_reached":
        return "not_applicable"
    if status != "completed":
        return "fail"
    review_required = int(decision_summary.get("review_required") or 0)
    if review_required > 0:
        return "manual_review"
    return "pass"


def _build_stage_result(
    *,
    stage_id: str,
    status: str,
    input_counts: dict[str, Any],
    output_counts: dict[str, Any],
    decision_summary: dict[str, Any],
) -> dict[str, Any]:
    summary = dict(decision_summary or {})
    decision = _resolve_stage_decision(status=status, decision_summary=summary)
    trace_seed = f"{stage_id}:{status}:{summary.get('debug_records_captured', '')}"
    # Stage result trace context is used for deterministic artifact linkage.
    # Avoid creating extra OTel spans here to reduce low-signal null span exports.
    trace_context = build_trace_context(trace_seed, emit_otel_span=False)
    return {
        "stage_id": stage_id,
        "status": status,
        "stage_version": "1.0.0",
        "output": dict(output_counts or {}),
        "evidence": {
            "input_counts": dict(input_counts or {}),
            "decision_summary": summary,
        },
        "validation": {
            "checks": [],
            "summary": {
                "status": status,
            },
        },
        "decision": decision,
        "policy_version": f"policy.{stage_id}.v1",
        "trace_context": trace_context,
    }


def _build_stage_transition_artifacts(
    *,
    raw_jobs: list[dict[str, Any]],
    normalized: list[dict[str, Any]],
    deduplicated_jobs: list[dict[str, Any]],
    pre_filter_rejected_jobs: list[dict[str, Any]],
    enriched: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
    candidate_filter_rejected_jobs: list[dict[str, Any]],
    raw_shortlist: list[dict[str, Any]],
    shortlist: list[dict[str, Any]],
    shortlist_audit_rows: list[dict[str, Any]],
    shortlist_diagnostics: dict[str, Any],
    vector_top_n: int,
    candidate_summary: str,
    candidate_query_components: dict[str, Any],
    ai_scores: list[dict[str, Any]],
    ranking_inputs: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    cv_analysis_results: list[dict[str, Any]] | None = None,
    final_top_n: int,
    cv_generation_debug_records: list[dict[str, Any]],
    profile: dict[str, Any],
    config: dict[str, Any],
    candidate_query_debug: dict[str, Any] | None = None,
    enrich_llm_runtime_observations: list[dict[str, Any]] | None = None,
    ranking_llm_runtime_observations: list[dict[str, Any]] | None = None,
    resolved_preference_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """@capability cv_system.stage-artifact-diagnostics"""
    candidate_query_debug = dict(candidate_query_debug or {})
    enrich_llm_runtime_observations = list(enrich_llm_runtime_observations or [])
    ranking_llm_runtime_observations = list(ranking_llm_runtime_observations or [])
    cv_analysis_results = list(cv_analysis_results or [])
    shortlist_reached = len(passed_jobs) > 0
    ranking_reached = shortlist_reached and (len(shortlist) > 0 or len(ai_scores) > 0 or len(ranking_inputs) > 0)
    cv_analysis_reached = len(ranked) > 0 or len(cv_analysis_results) > 0
    generation_execution_records = [
        record for record in cv_generation_debug_records
        if str(record.get("status") or "") in CV_GENERATION_ATTEMPTED_STATUSES
    ]
    cv_generation_reached = len(generation_execution_records) > 0
    raw_shortlist_urls = set(unique_job_urls(raw_shortlist))
    shortlist_candidate_query_components = {
        "headline": str(candidate_query_components.get("headline") or ""),
        "target_role": str(candidate_query_components.get("target_role") or ""),
        "recent_roles": list(candidate_query_components.get("recent_roles") or []),
        "role_family_hints": list(candidate_query_components.get("role_family_hints") or []),
        "flattened_skill_sample": list(candidate_query_components.get("flattened_skills") or []),
        "domain_hints": list(candidate_query_components.get("domain_hints") or []),
    }
    shortlist_candidate_query_components = {
        key: value
        for key, value in shortlist_candidate_query_components.items()
        if value not in (None, "", [])
    }
    shortlist_candidate_query_debug = {
        "candidate_query_reuse_status": str(candidate_query_debug.get("candidate_query_reuse_status") or ""),
        "candidate_query_signature": str(candidate_query_debug.get("candidate_query_signature") or ""),
        "candidate_query_contract_fingerprint": str(
            candidate_query_debug.get("candidate_query_contract_fingerprint") or ""
        ),
        "components_hash": str(candidate_query_debug.get("components_hash") or ""),
        "canonical_text_hash": str(candidate_query_debug.get("canonical_text_hash") or ""),
    }

    shortlist_candidate_query_debug = {
        key: value
        for key, value in shortlist_candidate_query_debug.items()
        if value not in ("", None)
    }
    ranked_urls = {extract_job_url(job) for job in ranked if extract_job_url(job)}
    dedupe_reason_counts: dict[str, int] = {}
    for job in deduplicated_jobs:
        reason = _DEDUPE_REASON_LABELS.get(str(job.get("dedupe_reason") or ""), "deduplicated")
        dedupe_reason_counts[reason] = dedupe_reason_counts.get(reason, 0) + 1
    grouped_reject_reasons: dict[str, int] = {}
    grouped_mark_codes: dict[str, int] = {}
    for rejected in candidate_filter_rejected_jobs:
        for reason in list(rejected.get("reasons") or []):
            grouped_reject_reasons[str(reason)] = grouped_reject_reasons.get(str(reason), 0) + 1
        for mark in list(rejected.get("marks") or []):
            code = str(mark.get("code") or "")
            if code:
                grouped_mark_codes[code] = grouped_mark_codes.get(code, 0) + 1
    for passed in passed_jobs:
        for mark in list(passed.get("marks") or []):
            code = str(mark.get("code") or "")
            if code:
                grouped_mark_codes[code] = grouped_mark_codes.get(code, 0) + 1
    selected_rule_filters = list(
        (
            config.get("rule_filter", {}) if isinstance(config.get("rule_filter"), dict) else {}
        ).get(
            "selected_filters",
            DEFAULT_SELECTED_RULE_FILTERS,
        )
    )
    ranking_fit_distribution: dict[str, int] = {}
    for row in ranking_inputs:
        fit_label = str(row.get("baseline_fit_label") or "")
        if fit_label:
            ranking_fit_distribution[fit_label] = ranking_fit_distribution.get(fit_label, 0) + 1
    ranking_policy = dict(config.get("ranking_policy") or {})
    ranking_contract = dict(config.get("ranking_contract") or {})
    baseline_weights = dict(ranking_policy.get("baseline_weights") or {})
    zero_weight_features = [
        feature_name
        for feature_name, weight in baseline_weights.items()
        if float(weight) == 0.0
    ]
    contributing_features = [
        feature_name
        for feature_name, weight in baseline_weights.items()
        if float(weight) > 0.0
    ]
    cv_status_counts = {
        "ranked_jobs_total": len(ranked),
        "debug_records_captured": len(cv_generation_debug_records),
        "accepted_count": 0,
        "review_required_count": 0,
        "blocked_by_reranker_fit_count": 0,
        "skipped_fit_gate_count": 0,
        "analysis_failed_count": 0,
        "validation_failed_count": 0,
        "generation_failed_count": 0,
        "persistence_failed_count": 0,
    }
    for record in cv_generation_debug_records:
        status = str(record.get("status") or "")
        if status == "accepted":
            cv_status_counts["accepted_count"] += 1
        elif status == CV_GENERATION_REVIEW_REQUIRED_STATUS:
            cv_status_counts["review_required_count"] += 1
        elif status == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS:
            cv_status_counts["blocked_by_reranker_fit_count"] += 1
        elif status == "skipped_fit_gate":
            cv_status_counts["skipped_fit_gate_count"] += 1
        elif status == "analysis_failed":
            cv_status_counts["analysis_failed_count"] += 1
        elif status == "validation_failed":
            cv_status_counts["validation_failed_count"] += 1
        elif status == "generation_failed":
            cv_status_counts["generation_failed_count"] += 1
        elif status == "persistence_failed":
            cv_status_counts["persistence_failed_count"] += 1
    enrich_prompt_provenance = get_enrich_prompt_provenance(config)
    ranking_prompt_provenance = _prompt_runtime_metadata(
        config,
        stage_id="ranking",
        prompt_key="ai_score",
    )
    cv_generation_prompt_provenance = _prompt_runtime_metadata(
        config,
        stage_id="cv_generation",
        prompt_key="structured_write",
    )
    enrich_reuse_counts = {
        "reused_rows": sum(
            1 for job in enriched
            if str(job.get("enrich_reuse_status") or "") == REUSED_CACHED_ENRICHMENT_STATUS
        ),
        "fresh_rows": sum(
            1 for job in enriched
            if str(job.get("enrich_reuse_status") or "") == FRESH_ENRICHMENT_STATUS
        ),
        "total_enriched_rows": len(enriched),
    }
    enrich_reuse_metrics = {
        "reused_rows": int(enrich_reuse_counts["reused_rows"]),
        "fresh_rows": int(enrich_reuse_counts["fresh_rows"]),
        "total_rows": int(enrich_reuse_counts["total_enriched_rows"]),
    }
    enrich_reuse_metrics["reuse_rate"] = _safe_rate(
        int(enrich_reuse_metrics["reused_rows"]),
        int(enrich_reuse_metrics["total_rows"]),
    )
    shortlist_embedding_reuse_counts = {
        "embedding_reused_jobs": sum(
            1 for job in passed_jobs
            if str(job.get("embedding_reuse_status") or "") == "reused_cached_embedding"
        ),
        "embedding_fresh_jobs": sum(
            1 for job in passed_jobs
            if str(job.get("embedding_reuse_status") or "") == "fresh_embedding"
        ),
        "embedding_total_jobs": len(passed_jobs),
    }
    shortlist_quality_metrics = _build_shortlist_quality_metrics(
        diagnostics=shortlist_diagnostics,
    )
    ranking_quality_metrics = _build_ranking_quality_metrics(ranking_inputs, config=config)
    ranking_reuse_metrics = {
        "reused_ai_scores": sum(
            1 for row in ai_scores
            if str(row.get("ai_score_reuse_status") or "") == "reused_exact_match"
        ),
        "fresh_ai_scores": sum(
            1 for row in ai_scores
            if str(row.get("ai_score_reuse_status") or "") == "fresh_compute"
        ),
        "total_ai_scores": len(ai_scores),
    }
    cv_analysis_quality_metrics = _build_cv_analysis_quality_metrics(cv_analysis_results)
    cv_analysis_executed_rows = [
        record for record in cv_analysis_results
        if str(record.get("status") or "") != CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS
    ]
    cv_analysis_reuse_metrics: dict[str, Any] = {
        "analysis_rows_executed": len(cv_analysis_executed_rows),
        "reused_analysis_rows": sum(
            1 for record in cv_analysis_executed_rows
            if str(record.get("analysis_reuse_status") or "") == "reused_exact_match"
        ),
        "fresh_analysis_rows": sum(
            1 for record in cv_analysis_executed_rows
            if str(record.get("analysis_reuse_status") or "") == "fresh_compute"
        ),
        "blocked_before_analysis_rows": sum(
            1 for record in cv_analysis_results
            if str(record.get("status") or "") == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS
        ),
    }
    cv_analysis_reuse_metrics["analysis_reuse_rate"] = _safe_rate(
        int(cv_analysis_reuse_metrics["reused_analysis_rows"]),
        int(cv_analysis_reuse_metrics["analysis_rows_executed"]),
    )
    cv_generation_quality_metrics = _build_cv_generation_quality_metrics(cv_generation_debug_records)
    cv_generation_reuse_metrics = {
        "reused_rows": sum(
            1 for record in cv_generation_debug_records
            if str(record.get("cv_generation_reuse_status") or "") == "reused_exact_match"
        ),
        "fresh_rows": sum(
            1 for record in cv_generation_debug_records
            if str(record.get("cv_generation_reuse_status") or "") == "fresh_compute"
        ),
        "total_rows": sum(
            1 for record in cv_generation_debug_records
            if str(record.get("status") or "") in CV_GENERATION_ATTEMPTED_STATUSES
        ),
    }
    cv_generation_reuse_metrics["reuse_rate"] = _safe_rate(
        int(cv_generation_reuse_metrics["reused_rows"]),
        int(cv_generation_reuse_metrics["total_rows"]),
    )
    return {
        "schema_version": STAGE_TRANSITION_ARTIFACTS_PIPELINE_SCHEMA_VERSION,
        "stages": {
            "normalize": _build_normalize_stage_block_artifacts(
                raw_jobs=raw_jobs,
                normalized=normalized,
                deduplicated_jobs=deduplicated_jobs,
                dedupe_reason_counts=dedupe_reason_counts,
                stage_block_builder=_stage_block,
                sample_rows_builder=_sample_rows,
                job_sample_builder=_job_sample,
                dedupe_reason_label_resolver=lambda reason: _DEDUPE_REASON_LABELS.get(
                    reason,
                    "deduplicated",
                ),
            ),
            "enrich": _build_enrich_stage_block_artifacts(
                normalized=normalized,
                pre_filter_rejected_jobs=pre_filter_rejected_jobs,
                enriched=enriched,
                profile=profile,
                config=config,
                enrich_prompt_provenance=enrich_prompt_provenance,
                enrich_reuse_counts=enrich_reuse_counts,
                enrich_reuse_metrics=enrich_reuse_metrics,
                llm_runtime_observations=enrich_llm_runtime_observations,
                stage_block_builder=_stage_block,
                sample_rows_builder=_sample_rows,
                job_sample_builder=_job_sample,
                extract_job_url=extract_job_url,
                candidate_profile_summary_builder=_candidate_profile_summary,
            ),
            "rule_filter": _build_rule_filter_stage_block_artifacts(
                enriched=enriched,
                passed_jobs=passed_jobs,
                candidate_filter_rejected_jobs=candidate_filter_rejected_jobs,
                grouped_reject_reasons=grouped_reject_reasons,
                grouped_mark_codes=grouped_mark_codes,
                selected_rule_filters=selected_rule_filters,
                stage_block_builder=_stage_block,
                sample_rows_builder=_sample_rows,
                job_sample_builder=_job_sample,
                rule_filter_decision_sample_builder=_rule_filter_decision_sample,
            ),
            "shortlist": _build_shortlist_stage_block_artifacts(
                shortlist_reached=shortlist_reached,
                passed_jobs=passed_jobs,
                raw_shortlist_urls=raw_shortlist_urls,
                raw_shortlist=raw_shortlist,
                shortlist=shortlist,
                audit_rows=shortlist_audit_rows,
                shortlist_diagnostics=shortlist_diagnostics,
                shortlist_embedding_reuse_counts=shortlist_embedding_reuse_counts,
                shortlist_candidate_query_components=shortlist_candidate_query_components,
                shortlist_candidate_query_debug=shortlist_candidate_query_debug,
                shortlist_quality_metrics=shortlist_quality_metrics,
                candidate_summary=candidate_summary,
                vector_top_n=vector_top_n,
                stage_block_builder=_stage_block,
                stage_block_not_reached_builder=_stage_block_not_reached,
                sample_rows_builder=_sample_rows,
                sample_strings_builder=_sample_strings,
                job_sample_builder=_job_sample,
                shortlist_row_sample_builder=_shortlist_row_sample,
                extract_job_url=extract_job_url,
                extract_job_title=extract_job_title,
            ),
            "ranking": _build_ranking_stage_block_artifacts(
                ranking_reached=ranking_reached,
                ai_scores=ai_scores,
                ranking_inputs=ranking_inputs,
                ranked=ranked,
                ranked_urls=ranked_urls,
                final_top_n=final_top_n,
                ranking_fit_distribution=ranking_fit_distribution,
                ranking_quality_metrics=ranking_quality_metrics,
                ranking_reuse_metrics=ranking_reuse_metrics,
                ranking_prompt_provenance=ranking_prompt_provenance,
                ranking_policy=ranking_policy,
                ranking_contract=ranking_contract,
                legacy_checkpoint_adaptation_count=sum(
                    1
                    for row in ranking_inputs
                    if row.get("legacy_checkpoint_default_applied")
                ),
                zero_weight_features=zero_weight_features,
                contributing_features=contributing_features,
                profile=profile,
                config=config,
                stage_block_builder=_stage_block,
                stage_block_not_reached_builder=_stage_block_not_reached,
                sample_rows_builder=_sample_rows,
                ranking_row_sample_builder=_ranking_row_sample,
                extract_job_url=extract_job_url,
                ai_score_model_resolver=get_ranking_ai_score_model,
                effective_preferences_resolver=infer_effective_preferences,
                llm_runtime_observations=ranking_llm_runtime_observations,
                resolved_preference_policy=resolved_preference_policy,
            ),
            "cv_analysis": _build_cv_analysis_stage_block_artifacts(
                cv_analysis_reached=cv_analysis_reached,
                ranked=ranked,
                cv_analysis_results=cv_analysis_results,
                cv_analysis_quality_metrics=cv_analysis_quality_metrics,
                cv_analysis_reuse_metrics=cv_analysis_reuse_metrics,
                config=config,
                blocked_by_reranker_status=CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
                ready_for_generation_status=CV_ANALYSIS_READY_FOR_GENERATION_STATUS,
                skipped_fit_gate_status=CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS,
                failed_status=CV_ANALYSIS_FAILED_STATUS,
                stage_block_builder=_stage_block,
                stage_block_not_reached_builder=_stage_block_not_reached,
                sample_rows_builder=_sample_rows,
                ranking_row_sample_builder=_ranking_row_sample,
                analysis_record_output_sample_builder=_analysis_record_output_sample,
                analysis_record_changed_sample_builder=_analysis_record_changed_sample,
            ),
            "cv_generation": _build_cv_generation_stage_block_artifacts(
                cv_generation_reached=cv_generation_reached,
                cv_analysis_results=cv_analysis_results,
                cv_generation_debug_records=cv_generation_debug_records,
                cv_status_counts=cv_status_counts,
                cv_generation_quality_metrics=cv_generation_quality_metrics,
                cv_generation_reuse_metrics=cv_generation_reuse_metrics,
                cv_generation_prompt_provenance=cv_generation_prompt_provenance,
                config=config,
                stage_block_builder=_stage_block,
                stage_block_not_reached_builder=_stage_block_not_reached,
                sample_rows_builder=_sample_rows,
                analysis_record_output_sample_builder=_analysis_record_output_sample,
                debug_record_output_sample_builder=_debug_record_output_sample,
                debug_record_changed_sample_builder=_debug_record_changed_sample,
                cv_generation_model_summarizer=_summarize_cv_generation_model,
                cv_generation_provider_summarizer=_summarize_cv_generation_provider,
                cv_generation_model_resolver=get_cv_generation_model,
            ),
        },
    }
def build_ranking_features(
    shortlist: list[dict[str, Any]],
    ai_scores: list[dict[str, Any]],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Build canonical ranking-v2 rows from shortlist and AI-score inputs."""
    shortlist_index: dict[str, dict[str, Any]] = {
        row["job_url"]: row for row in shortlist
    }
    ranking_context = dict(config.get("ranking_contract") or {})
    ranking_policy = dict(ranking_context.get("ranking_policy") or {})
    if not ranking_policy:
        raise ValueError("ranking-v2 requires config.ranking_contract")
    candidate_skills = flatten_skills(profile)
    preference_resolution = infer_effective_preferences(profile, config)
    effective_preferences = dict(preference_resolution["effective_preferences"] or {})
    inferred_preferences = dict(preference_resolution["inferred_preferences"] or {})
    preference_sources = dict(preference_resolution["preference_sources"] or {})

    features: list[dict[str, Any]] = []
    for ai_row in ai_scores:
        job_url = str(ai_row.get("job_url") or "")
        sl_row = shortlist_index.get(job_url)
        if sl_row is None:
            continue  # not in shortlist — skip

        vector_rank = sl_row.get("vector_rank", sl_row.get("rank"))
        raw_vector_similarity = sl_row.get("vector_similarity", sl_row.get("similarity_score"))
        vector_similarity = float(raw_vector_similarity) if raw_vector_similarity is not None else None
        raw_ai_score = ai_row.get("ai_score")
        ranking_source: dict[str, Any] = {
            **sl_row,
            **ai_row,
        }
        required_skills = list(
            ranking_source.get("required_skills_canonical")
            or ranking_source.get("required_skills")
            or []
        )
        must_have_match = compute_must_have_match(required_skills, candidate_skills, config)
        title_relevance = compute_title_relevance(
            extract_job_title(ranking_source),
            str(effective_preferences.get("target_role") or "") or None,
            job_family=str(ranking_source.get("job_family") or "") or None,
            config=config,
        )
        seniority_fit = compute_seniority_fit(
            str(ranking_source.get("seniority") or "") or None,
            str(effective_preferences.get("seniority_target") or "") or None,
            config,
        )
        preference_fit_details = compute_declared_preference_fit_details(
            ranking_source,
            effective_preferences,
            config,
        )
        fit_factor_results = dict(ranking_source.get("fit_factor_results") or {})
        structured_factors = {
            "must_have_match": must_have_match,
            "title_relevance": title_relevance,
            "seniority_fit": seniority_fit,
            "declared_preference_fit": float(preference_fit_details["score"]),
            "location_fit": dict(fit_factor_results.get("location_fit") or {}).get("ranking_value"),
            "language_fit": dict(fit_factor_results.get("language_fit") or {}).get("ranking_value"),
        }
        baseline_result = build_baseline_result(
            holistic_ai_fit=raw_ai_score,
            structured_factors=structured_factors,
            context=ranking_context,
        )

        feature: dict[str, Any] = {
            **ranking_source,
            "vector_rank": int(vector_rank or 0),
            "vector_similarity": vector_similarity,
            **baseline_result,
            "declared_preference_fit_components": preference_fit_details["components"],
            "declared_preference_fit_match_details": preference_fit_details["match_details"],
            "declared_preference_fit_weights": preference_fit_details["weights"],
            "effective_preferences": effective_preferences,
            "inferred_preferences": inferred_preferences,
            "preference_sources": preference_sources,
            "eligibility_policy_fingerprint": ranking_source.get("eligibility_policy_fingerprint")
            or config.get("eligibility_policy_fingerprint"),
        }
        for retired_key in ("ai_score", "fit_label", "final_score", "final_rank", "preference_fit"):
            feature.pop(retired_key, None)
        features.append(feature)

    return features


# ── orchestrator ──────────────────────────────────────────────────────────────

def run_pipeline(
    jobs_path: str,
    config_path: str = ".env.yaml",
    reporter: object = None,  # Optional[PipelineReporter] — avoids circular import
    config: dict | None = None,  # If provided, skips load_config(config_path)
    run_id: str | None = None,
    cancellation_check: Callable[[], bool] | None = None,
    start_stage: str | None = None,
    stop_after_stage: str | None = None,
    checkpoint_payload: dict[str, Any] | None = None,
    reuse_snapshots: dict[str, Any] | None = None,
    stage_progress_callback: Callable[[dict[str, Any]], None] | None = None,
    preference_policy_resolver: Callable[
        [PreferenceRuntimeContract], ResolvedPreferencePolicy
    ]
    | None = None,
) -> dict[str, Any]:
    """Run the full FitCV candidate pipeline end-to-end.

    @capability bounded_parallel_enrichment.pre-enrichment-global-filters-run-first
    @capability cv_system.fit-gate-resolution
    @capability cv_system.exact-match-late-stage-reuse

    Parameters
    ----------
    reporter:
        Optional PipelineReporter instance injected by the control-plane worker.
        When provided, stage events are emitted to pipeline_run_events in sqlite-backed run storage.
        When None, no events are emitted (normal CLI / test usage).
    config:
        Optional pre-built config dict. When provided, `config_path` is ignored.
        Used by the worker to inject the effective settings snapshot stored at
        trigger time. When None, config is loaded from `config_path` as usual.
    run_id:
        Optional externally provided run ID. When present, it is treated as the
        canonical identifier for summaries, events, and persisted records.

    Returns
    -------
    dict with keys:
        run_id          : UUID4 of this run
        total_jobs      : number of raw jobs ingested
        passed_filter   : number of jobs that passed rule filtering
        ranked          : number of jobs in the final shortlist
        cvs_generated   : number of successfully generated + validated CVs
    """
    if config is None:
        config = load_config(config_path)
    pipeline_store = PipelineStore(
        load_raw_jobs_fn=load_raw_jobs,
        load_candidate_profile_fn=load_candidate_profile,
        lookup_reusable_structured_jobs_fn=lookup_reusable_structured_jobs,
        load_structured_jobs_fn=load_structured_jobs,
        load_run_structured_jobs_fn=load_run_structured_jobs,
        store_filter_results_fn=store_filter_results,
        embed_and_store_jobs_fn=embed_and_store_jobs,
        store_shortlist_fn=store_shortlist,
        store_final_ranking_fn=store_final_ranking,
        store_cv_version_fn=store_cv_version,
    )
    run_id = run_id or create_run_id()
    with observe_span("fitcv.run_pipeline", attributes={"run_id": run_id}):
        start_stage = _canonical_resume_start_stage(
            requested_start_stage=start_stage,
            checkpoint_payload=checkpoint_payload,
            run_id=run_id,
        ) or PIPELINE_STAGE_SEQUENCE[0]
        stop_after_stage = _validate_pipeline_stage_name(stop_after_stage)
        if stop_after_stage is not None:
            if PIPELINE_STAGE_SEQUENCE.index(stop_after_stage) < PIPELINE_STAGE_SEQUENCE.index(start_stage):
                raise ValueError(
                    f"stop_after_stage {stop_after_stage!r} cannot precede start_stage {start_stage!r}"
                )
        logger.info("Pipeline run started [run_id=%s]", run_id)
        if reporter is not None:
            reporter.emit("pipeline_start", "info", f"Run started [run_id={run_id}]")  # type: ignore[union-attr]
        state = _restore_pipeline_state(run_id=run_id, checkpoint_payload=checkpoint_payload)
        normalized_reuse_snapshots = _normalize_late_stage_reuse_snapshots(reuse_snapshots)
        ranking_ai_score_reuse_index = _index_late_stage_reuse_rows(
            normalized_reuse_snapshots["ranking_ai_scores"],
            fingerprint_key="ai_score_input_fingerprint",
            payload_key="ai_score_row",
        )
        cv_analysis_reuse_by_identity = _index_cv_analysis_reuse_by_identity(
            normalized_reuse_snapshots["cv_analysis_records"],
        )
        raw_jobs = list(state["raw_jobs"])
        normalized = list(state["normalized"])
        deduplicated_jobs = list(state["deduplicated_jobs"])
        pre_filter_rejected_jobs = list(state["pre_filter_rejected_jobs"])
        enriched = list(state["enriched"])
        enrich_llm_runtime_observations = list(state["enrich_llm_runtime_observations"])
        passed_jobs = list(state["passed_jobs"])
        candidate_filter_rejected_jobs = list(state["candidate_filter_rejected_jobs"])
        raw_shortlist = list(state["raw_shortlist"])
        shortlist = list(state["shortlist"])
        shortlist_audit_rows = list(state.get("_shortlist_audit_rows") or [])
        shortlist_diagnostics = dict(state.get("shortlist_diagnostics") or {})
        ai_scores = list(state["ai_scores"])
        ranking_llm_runtime_observations = list(state["ranking_llm_runtime_observations"])
        ranking_inputs = list(state["ranking_inputs"])
        ranked = list(state["ranked"])
        cv_analysis_results = list(state["cv_analysis_results"])
        results: list[dict[str, Any]] = list(state["cv_results"])
        cv_generation_debug_records: list[dict[str, Any]] = list(state["cv_generation_debug_records"])
        profile: dict[str, Any] | None = None
        candidate_skill_names: list[str] = []
        candidate_summary = ""
        candidate_query_components: dict[str, Any] = {}
        candidate_query_debug: dict[str, Any] = {}
        vector_top_n = pipeline_int(config, "vector_search_top_n", default=0)
        final_top_n = pipeline_int(config, "final_top_n", default=0)

        if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("normalize"):
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
            stage_boundary_result = _handle_stage_boundary(
                run_id=run_id,
                last_completed_stage="normalize",
                stop_after_stage=stop_after_stage,
                state=state,
                profile=None,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                candidate_query_components=candidate_query_components,
                candidate_query_debug=candidate_query_debug,
                final_top_n=final_top_n,
                stage_progress_callback=stage_progress_callback,
            )
            if stage_boundary_result is not None:
                return stage_boundary_result

        normalized = list(state["normalized"])

        if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("enrich"):
            with observe_span("pipeline.enrich", attributes={"run_id": run_id}):
                enrich_runtime_config = _enrich_runtime_projection(config)
                enrich_concurrency = _enrich_stage_concurrency(config)
                enrich_batch_size = max(
                    int(enrich_runtime_config.get("enrichment_batch_size", 10)),
                    1,
                )
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
                    raise PipelineCancelled("Cancelled before enrichment")
                enriched, fresh_enriched_rows = _enrich_jobs_with_reuse(
                    surviving_normalized,
                    enrich_runtime_config,
                    pipeline_store=pipeline_store,
                    incremental_save_run_id=run_id,
                    runtime_observations=enrich_llm_runtime_observations,
                    heartbeat_callback=(
                        (lambda payload: reporter.emit(  # type: ignore[union-attr]
                            "enrich_heartbeat",
                            "info",
                            "Enrich in progress",
                            {
                                **dict(payload or {}),
                                "configured_concurrency": int(enrich_concurrency),
                                "enrich_concurrency_effective": _effective_stage_concurrency(
                                    enrich_concurrency,
                                    (
                                        int((payload or {}).get("fresh_jobs_total") or 0)
                                        + enrich_batch_size
                                        - 1
                                    )
                                    // enrich_batch_size,
                                ),
                            },
                        ))
                        if reporter is not None else None
                    ),
                )
                reused_count = sum(
                    1 for row in enriched
                    if str(row.get("enrich_reuse_status") or "") == REUSED_CACHED_ENRICHMENT_STATUS
                )
                fresh_count = sum(
                    1 for row in enriched
                    if str(row.get("enrich_reuse_status") or "") == FRESH_ENRICHMENT_STATUS
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
                state["enrich_llm_runtime_observations"] = enrich_llm_runtime_observations
                set_span_attributes(
                    {
                        "normalized_jobs": len(normalized),
                        "pre_filter_rejected": len(pre_filter_rejected_jobs),
                        "enriched_jobs": len(enriched),
                        "fresh_enriched": fresh_count,
                        "reused_enriched": reused_count,
                    }
                )
            stage_boundary_result = _handle_stage_boundary(
                run_id=run_id,
                last_completed_stage="enrich",
                stop_after_stage=stop_after_stage,
                state=state,
                profile=None,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                candidate_query_components=candidate_query_components,
                candidate_query_debug=candidate_query_debug,
                final_top_n=final_top_n,
                stage_progress_callback=stage_progress_callback,
            )
            if stage_boundary_result is not None:
                return stage_boundary_result

        pre_filter_rejected_jobs = list(state["pre_filter_rejected_jobs"])
        enriched = list(state["enriched"])

        if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("rule_filter"):
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
                pipeline_store.store_filter_results(combined_filter_result, run_id, config)
                if reporter is not None:
                    reporter.emit("layer3_filter", "info", f"{len(passed_jobs)} passed rule filter")  # type: ignore[union-attr]
                state["passed_jobs"] = passed_jobs
                state["candidate_filter_rejected_jobs"] = candidate_filter_rejected_jobs
                set_span_attributes(
                    {
                        "candidate_skills": len(candidate_skill_names),
                        "passed_jobs": len(passed_jobs),
                        "candidate_filter_rejected": len(candidate_filter_rejected_jobs),
                    }
                )
            stage_boundary_result = _handle_stage_boundary(
                run_id=run_id,
                last_completed_stage="rule_filter",
                stop_after_stage=stop_after_stage,
                state=state,
                profile=profile,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                candidate_query_components=candidate_query_components,
                candidate_query_debug=candidate_query_debug,
                final_top_n=final_top_n,
                stage_progress_callback=stage_progress_callback,
            )
            if stage_boundary_result is not None:
                return stage_boundary_result
        else:
            runtime_profile_json = config.get("runtime_inputs", {}).get("candidate_profile_json")
            if runtime_profile_json:
                profile = load_profile_json_text(runtime_profile_json)
            else:
                profile_path = str(config["paths"]["candidate_profile"])
                profile = load_profile_yaml(profile_path)
            candidate_skill_names = flatten_skills(profile)

        passed_jobs = list(state["passed_jobs"])
        candidate_filter_rejected_jobs = list(state["candidate_filter_rejected_jobs"])
        passed_job_urls = [extract_job_url(job) for job in passed_jobs if extract_job_url(job)]

        if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("shortlist"):
            with observe_span("pipeline.shortlist", attributes={"run_id": run_id, "vector_top_n": vector_top_n}):
                # Active shortlist runtime only prepares reusable job embeddings here.
                # The candidate-side vector actually used for retrieval is generated
                # inside run_vector_search() from the deterministic candidate query text.
                pipeline_store.embed_and_store_jobs(passed_jobs, config)
                raw_shortlist_result = run_vector_search(
                    profile,
                    [str(job.get("job_url") or "") for job in passed_jobs],
                    config,
                    top_n=vector_top_n,
                )
                raw_shortlist = list(raw_shortlist_result.get("production_rows") or [])
                shortlist_audit_rows = list(raw_shortlist_result.get("audit_rows") or [])
                shortlist_diagnostics = dict(raw_shortlist_result.get("diagnostics") or {})
                candidate_query_record = dict(raw_shortlist_result.get("candidate_query") or {})
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
                components_hash = hashlib.sha256(
                    json.dumps(candidate_query_components, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                canonical_text_hash = hashlib.sha256(candidate_summary.encode("utf-8")).hexdigest()
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
                    "components_hash": components_hash,
                    "canonical_text_hash": canonical_text_hash,
                }
                shortlist_fail_fast = bool((config.get("pipeline", {}) or {}).get("shortlist_fail_fast_empty_raw_hits", False))
                if shortlist_fail_fast and passed_jobs and not raw_shortlist:
                    raise RuntimeError(
                        "Vector shortlist returned zero raw hits for non-empty passed jobs; fail-fast guard active"
                    )
                shortlist = _materialize_scoring_shortlist(raw_shortlist, passed_jobs)
                pipeline_store.store_shortlist(shortlist, config)
                raw_shortlist_urls = set(unique_job_urls(raw_shortlist))
                if reporter is not None:
                    shortlist_message = f"Vector shortlist: {len(raw_shortlist_urls)} raw hits"
                    reporter.emit("layer3_shortlist", "info", shortlist_message)  # type: ignore[union-attr]
                state["raw_shortlist"] = raw_shortlist
                state["shortlist"] = shortlist
                state["shortlist_diagnostics"] = shortlist_diagnostics
                state["_shortlist_audit_rows"] = shortlist_audit_rows
                state["candidate_query_debug"] = candidate_query_debug
                set_span_attributes(
                    {
                        "passed_jobs": len(passed_jobs),
                        "raw_shortlist_hits": len(raw_shortlist_urls),
                        "shortlist_jobs": len(shortlist),
                        "shortlist_audit_rows": len(shortlist_audit_rows),
                    }
                )
            stage_boundary_result = _handle_stage_boundary(
                run_id=run_id,
                last_completed_stage="shortlist",
                stop_after_stage=stop_after_stage,
                state=state,
                profile=profile,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                candidate_query_components=candidate_query_components,
                candidate_query_debug=candidate_query_debug,
                final_top_n=final_top_n,
                stage_progress_callback=stage_progress_callback,
            )
            if stage_boundary_result is not None:
                return stage_boundary_result

        raw_shortlist = list(state["raw_shortlist"])
        shortlist = list(state["shortlist"])
        shortlist_audit_rows = list(state.get("_shortlist_audit_rows") or [])
        shortlist_diagnostics = dict(state.get("shortlist_diagnostics") or {})
        candidate_query_debug = dict(state.get("candidate_query_debug") or candidate_query_debug)

        if not candidate_query_components or not candidate_summary:
            from fitcv.vector_search import build_candidate_query_components, build_candidate_query_text

            candidate_query_components = build_candidate_query_components(profile, config)
            candidate_summary = build_candidate_query_text(profile, config)

        if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("ranking"):
            with observe_span("pipeline.ai_score", attributes={"run_id": run_id}):
                ai_top_n = pipeline_int(config, "ai_score_top_n", default=0)
                if cancellation_check and cancellation_check():
                    raise PipelineCancelled("Cancelled before AI scoring")
                ai_score_candidates = shortlist[:ai_top_n]
                ranking_reuse_enabled = _reuse_stage_enabled(config, "ranking")
                fresh_scoring_jobs: list[dict[str, Any]] = []
                fresh_ai_score_fingerprints: dict[str, str] = {}
                reused_ai_scores_by_url: dict[str, dict[str, Any]] = {}
                for shortlisted_job in ai_score_candidates:
                    top_evidence = list(shortlisted_job.get("top_evidence") or [])[:2]
                    fingerprint_record = build_ai_score_input_fingerprint(
                        shortlisted_job,
                        candidate_summary,
                        top_evidence,
                        config,
                    )
                    job_url = extract_job_url(shortlisted_job)
                    reused_ai_row = (
                        ranking_ai_score_reuse_index.get(fingerprint_record["fingerprint"])
                        if ranking_reuse_enabled
                        else None
                    )
                    if reused_ai_row is not None and job_url:
                        reused_ai_scores_by_url[job_url] = {
                            **deepcopy(reused_ai_row),
                            "job_url": job_url,
                            "ai_score_input_fingerprint": fingerprint_record["fingerprint"],
                            "ai_score_reuse_status": "reused_exact_match",
                            "reuse_decision": build_reuse_decision(
                                decision="reused_exact_match",
                                reason_code="exact_fingerprint_match",
                                fingerprint=fingerprint_record["fingerprint"],
                                source_artifact_type="ranking_ai_score",
                            ),
                        }
                        continue
                    fresh_scoring_jobs.append(shortlisted_job)
                    if job_url:
                        fresh_ai_score_fingerprints[job_url] = fingerprint_record["fingerprint"]

                ranking_concurrency = _ranking_stage_concurrency(config)
                ranking_effective_concurrency = _effective_stage_concurrency(
                    ranking_concurrency,
                    len(fresh_scoring_jobs),
                )
                fresh_ai_scores = run_ai_scoring(
                    fresh_scoring_jobs,
                    candidate_summary,
                    config,
                    top_n=len(fresh_scoring_jobs),
                    runtime_observation_callback=ranking_llm_runtime_observations.append,
                ) if fresh_scoring_jobs else []
                fresh_ai_scores_by_url: dict[str, dict[str, Any]] = {}
                for ai_row in fresh_ai_scores:
                    job_url = str(ai_row.get("job_url") or "")
                    fresh_ai_scores_by_url[job_url] = {
                        **ai_row,
                        "ai_score_input_fingerprint": fresh_ai_score_fingerprints.get(job_url),
                        "ai_score_reuse_status": "fresh_compute" if ranking_reuse_enabled else "reuse_disabled",
                        "reuse_decision": build_reuse_decision(
                            decision="fresh_compute" if ranking_reuse_enabled else "reuse_disabled",
                            reason_code="no_reusable_snapshot_match" if ranking_reuse_enabled else "stage_reuse_disabled",
                            fingerprint=fresh_ai_score_fingerprints.get(job_url),
                            source_artifact_type="ranking_ai_score",
                        ),
                    }

                ai_scores = []
                for shortlisted_job in ai_score_candidates:
                    job_url = extract_job_url(shortlisted_job)
                    score_row: dict[str, Any] | None = reused_ai_scores_by_url.get(job_url) or fresh_ai_scores_by_url.get(job_url)
                    if score_row is not None:
                        ai_scores.append(score_row)
                reused_ai_count = sum(
                    1 for row in ai_scores
                    if str(row.get("ai_score_reuse_status") or "") == "reused_exact_match"
                )
                fresh_ai_count = sum(
                    1 for row in ai_scores
                    if str(row.get("ai_score_reuse_status") or "") == "fresh_compute"
                )
                if reporter is not None:
                    reporter.emit(  # type: ignore[union-attr]
                        "layer3_ai_score",
                        "info",
                        f"AI scored: {len(ai_scores)} jobs",
                        _bounded_event_payload(
                            event_name="ranking_ai_scored",
                            event_family="summary",
                            source_stage="ranking",
                            event_status="completed",
                            output_snapshot={
                                "ai_scored_jobs": len(ai_scores),
                                "configured_concurrency": ranking_concurrency,
                                "ranking_concurrency_effective": ranking_effective_concurrency,
                            },
                            artifact_refs={"stage_id": "ranking"},
                        ),
                    )
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
                    resolved_preference_policy=resolved_preference_policy,
                )
                pipeline_store.store_final_ranking(ranked, config)
                if reporter is not None:
                    reporter.emit(  # type: ignore[union-attr]
                        "layer3_ranking",
                        "info",
                        f"Final ranking: top {len(ranked)} jobs",
                        _bounded_event_payload(
                            event_name="ranking_completed",
                            event_family="summary",
                            source_stage="ranking",
                            event_status="completed",
                            output_snapshot={
                                "ranked_jobs": len(ranked),
                                "configured_concurrency": ranking_concurrency,
                                "ranking_concurrency_effective": ranking_effective_concurrency,
                                "reused_ai_scores": reused_ai_count,
                                "fresh_ai_scores": fresh_ai_count,
                            },
                            artifact_refs={"stage_id": "ranking"},
                        ),
                    )
                state["ai_scores"] = ai_scores
                state["ranking_llm_runtime_observations"] = ranking_llm_runtime_observations
                state["ranking_inputs"] = ranking_inputs
                state["ranked"] = ranked
                set_span_attributes(
                    {
                        "ranking_inputs": len(ranking_inputs),
                        "ranked_jobs": len(ranked),
                    }
                )
            stage_boundary_result = _handle_stage_boundary(
                run_id=run_id,
                last_completed_stage="ranking",
                stop_after_stage=stop_after_stage,
                state=state,
                profile=profile,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                candidate_query_components=candidate_query_components,
                candidate_query_debug=candidate_query_debug,
                final_top_n=final_top_n,
                stage_progress_callback=stage_progress_callback,
            )
            if stage_boundary_result is not None:
                return stage_boundary_result

        ai_scores = list(state["ai_scores"])
        ranking_inputs = list(state["ranking_inputs"])
        ranked = list(state["ranked"])

        enriched_by_url = {
            str(job.get("job_url") or ""): job
            for job in enriched
            if job.get("job_url")
        }
        ranked_jobs_for_cv = [
            _merge_ranked_job_with_enriched_context(job, enriched_by_url)
            for job in ranked
        ]
        cv_generation_prompt_runtime = _prompt_runtime_metadata(
            config,
            stage_id="cv_generation",
            prompt_key="structured_write",
        )
        cv_generation_model_value = get_cv_generation_model(config)
        cv_prompt_id_value = cv_generation_prompt_runtime["prompt_id"]
        cv_prompt_template_path_value = cv_generation_prompt_runtime["template_path"]
        cv_prompt_version_value = get_cv_generation_prompt_version(config)
        enabled_cv_sections = _cv_generation_enabled_sections(config)
        cv_analysis_concurrency = _cv_analysis_stage_concurrency(config)
        if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("cv_analysis"):
            with observe_span(
                "pipeline.cv_analysis",
                attributes={"run_id": run_id, "ranked_jobs": len(ranked_jobs_for_cv)},
            ):
                cv_analysis_started_monotonic = time.monotonic()
                cv_analysis_effective_concurrency = _effective_stage_concurrency(
                    cv_analysis_concurrency,
                    len(ranked_jobs_for_cv),
                )
                if reporter is not None:
                    reporter.emit(
                        "layer4_cv_analysis_invoked",
                        "info",
                        f"CV analysis invoked for {len(ranked_jobs_for_cv)} ranked job(s)",
                        _bounded_event_payload(
                            event_name="cv_analysis_invoked",
                            event_family="invocation",
                            source_stage="cv_analysis",
                            event_status="started",
                            fallback_used=False,
                            provenance={
                                "configured_concurrency": cv_analysis_concurrency,
                                "cv_analysis_concurrency_effective": cv_analysis_effective_concurrency,
                            },
                            input_snapshot={
                                "ranked_jobs": len(ranked_jobs_for_cv),
                                "cv_analysis_concurrency_configured": cv_analysis_concurrency,
                            },
                            output_snapshot={
                                "ranked_jobs": len(ranked_jobs_for_cv),
                                "configured_concurrency": cv_analysis_concurrency,
                                "cv_analysis_concurrency_effective": cv_analysis_effective_concurrency,
                            },
                            artifact_refs={"stage_id": "cv_analysis"},
                        ),
                    )  # type: ignore[union-attr]
                if cancellation_check and cancellation_check():
                    raise PipelineCancelled("Cancelled before CV analysis")

                cv_analysis_results = []
                cv_analysis_reuse_enabled = _reuse_stage_enabled(config, "cv_analysis")
                fresh_analysis_reuse_reason_counts: dict[str, int] = {}
                fresh_identity_overlap = 0
                fresh_identity_no_overlap = 0
                analysis_inputs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
                for job in ranked_jobs_for_cv:
                    reusable_record = None
                    if cv_analysis_reuse_enabled:
                        for identity_key in job_identity_keys(job):
                            reusable_record = cv_analysis_reuse_by_identity.get(identity_key)
                            if reusable_record is not None:
                                break
                    analysis_inputs.append((job, reusable_record))

                def _analyze_cv_job(
                    analysis_input: tuple[dict[str, Any], dict[str, Any] | None],
                ) -> dict[str, Any]:
                    job, reusable_record = analysis_input
                    return dict(
                        analyze_ranked_job(
                            job,
                            profile,
                            config,
                            reusable_record=reusable_record,
                        )
                    )

                if cv_analysis_effective_concurrency > 1:
                    with ThreadPoolExecutor(max_workers=cv_analysis_effective_concurrency) as executor:
                        analyzed_records = list(executor.map(_analyze_cv_job, analysis_inputs))
                else:
                    analyzed_records = [_analyze_cv_job(item) for item in analysis_inputs]

                for (job, reusable_record), analysis_record in zip(analysis_inputs, analyzed_records):
                    cv_analysis_results.append(analysis_record)
                    _emit_cv_analysis_item_observation(
                        run_id=run_id,
                        profile=profile,
                        job=job,
                        analysis_record=analysis_record,
                    )

                    analysis_status = str(analysis_record.get("status") or "analysis_failed")
                    if analysis_status == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS:
                        logger.info(
                            "[run_id=%s] Blocking job %s before CV analysis (reranker fit=skip)",
                            run_id,
                            job.get("job_url"),
                        )
                    if str(analysis_record.get("analysis_reuse_status") or "") == "fresh_compute":
                        if reusable_record is None:
                            fresh_identity_no_overlap += 1
                        else:
                            fresh_identity_overlap += 1
                        reuse_reason = str(
                            dict(analysis_record.get("reuse_decision") or {}).get("reason_code")
                            or "unknown"
                        )
                        fresh_analysis_reuse_reason_counts[reuse_reason] = int(
                            fresh_analysis_reuse_reason_counts.get(reuse_reason) or 0
                        ) + 1
                    if analysis_status != CV_ANALYSIS_READY_FOR_GENERATION_STATUS:
                        generation_result = dict(
                            run_agentic_cv_generation(
                                analysis_record,
                                profile,
                                config,
                            )
                        )
                        cv_generation_debug_records.append(
                            _build_cv_generation_debug_record(
                                generation_result=generation_result,
                                enabled_sections=enabled_cv_sections,
                                cv_generation_model=cv_generation_model_value,
                                cv_prompt_id=cv_prompt_id_value,
                                cv_prompt_template_path=cv_prompt_template_path_value,
                            )
                        )
                    if reporter is not None and analysis_status == CV_ANALYSIS_FAILED_STATUS:
                        analysis_error = dict(analysis_record.get("error") or {})
                        reporter.emit(
                            "layer4_cv_error",
                            "error",
                            f"CV analysis failed for {job.get('job_url')}: {analysis_error.get('message')}",
                            _bounded_event_payload(
                                event_name="cv_analysis_decision",
                                event_family="decision",
                                source_stage="cv_analysis",
                                event_status="completed",
                                job_url=str(job.get("job_url") or ""),
                                deterministic_outcome="rejected",
                                stage_owned_subreason=CV_ANALYSIS_FAILED_STATUS,
                                input_snapshot={
                                    "ranking_fit_label": analysis_record.get("ranking_fit_label"),
                                },
                                output_snapshot={
                                    "error_stage": str(analysis_error.get("stage") or ""),
                                },
                                artifact_refs={"stage_id": "cv_analysis"},
                            ),
                        )  # type: ignore[union-attr]

                if reporter is not None:
                    blocked_by_reranker_diagnostics = [
                        {
                            "job_url": str(record.get("job_url") or ""),
                            "ranking_fit_label": str(record.get("ranking_fit_label") or ""),
                            "fit_classification": str(record.get("fit_classification") or ""),
                            "ai_score": (record.get("job_snapshot") or {}).get("ai_score"),
                            "fit_label_source": str(
                                ((record.get("job_snapshot") or {}).get("fit_label_source")) or ""
                            ),
                        }
                        for record in cv_analysis_results
                        if str(record.get("status") or "")
                        == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS
                    ][:10]
                    reporter.emit(
                        "layer4_cv_analysis",
                        "info",
                        (
                            "CV analysis complete: "
                            f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == CV_ANALYSIS_READY_FOR_GENERATION_STATUS)} ready, "
                            f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS)} blocked by reranker, "
                            f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS)} skipped, "
                            f"{sum(1 for record in cv_analysis_results if str(record.get('status') or '') == CV_ANALYSIS_FAILED_STATUS)} failed"
                        ),
                        _bounded_event_payload(
                            event_name="cv_analysis_decision",
                            event_family="decision",
                            source_stage="cv_analysis",
                            event_status="completed",
                            deterministic_outcome=None,
                            stage_owned_subreason="stage_summary",
                            input_snapshot={
                                "ranked_jobs": len(ranked),
                                "cv_analysis_concurrency_configured": cv_analysis_concurrency,
                            },
                            output_snapshot={
                                "reused_analysis_rows": sum(
                                    1
                                    for record in cv_analysis_results
                                    if str(record.get("analysis_reuse_status") or "")
                                    == "reused_exact_match"
                                ),
                                "fresh_analysis_rows": sum(
                                    1
                                    for record in cv_analysis_results
                                    if str(record.get("analysis_reuse_status") or "")
                                    == "fresh_compute"
                                ),
                                "ready_for_generation": sum(
                                    1
                                    for record in cv_analysis_results
                                    if str(record.get("status") or "")
                                    == CV_ANALYSIS_READY_FOR_GENERATION_STATUS
                                ),
                                "blocked_by_reranker_fit": sum(
                                    1
                                    for record in cv_analysis_results
                                    if str(record.get("status") or "")
                                    == CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS
                                ),
                                "skipped_fit_gate": sum(
                                    1
                                    for record in cv_analysis_results
                                    if str(record.get("status") or "")
                                    == CV_ANALYSIS_SKIPPED_FIT_GATE_STATUS
                                ),
                                "analysis_failed": sum(
                                    1
                                    for record in cv_analysis_results
                                    if str(record.get("status") or "")
                                    == CV_ANALYSIS_FAILED_STATUS
                                ),
                                "fresh_analysis_reuse_mismatch_reasons": dict(
                                    fresh_analysis_reuse_reason_counts
                                ),
                                "fresh_analysis_overlap_urls": fresh_identity_overlap,
                                "fresh_analysis_no_overlap_urls": fresh_identity_no_overlap,
                                "configured_concurrency": cv_analysis_concurrency,
                                "cv_analysis_concurrency_effective": cv_analysis_effective_concurrency,
                            },
                            artifact_refs={"stage_id": "cv_analysis"},
                            latency_ms=int(
                                (time.monotonic() - cv_analysis_started_monotonic) * 1000
                            ),
                        ),
                    )  # type: ignore[union-attr]
                    if blocked_by_reranker_diagnostics:
                        reporter.emit(
                            "layer4_cv_analysis_blocked_details",
                            "info",
                            f"Blocked by reranker diagnostics: {len(blocked_by_reranker_diagnostics)} job(s)",
                            _bounded_event_payload(
                                event_name="cv_analysis_blocked_diagnostics",
                                event_family="debug",
                                source_stage="cv_analysis",
                                event_status="completed",
                                deterministic_outcome="rejected",
                                stage_owned_subreason=CV_ANALYSIS_BLOCKED_BY_RERANKER_STATUS,
                                input_snapshot={
                                    "fit_label_thresholds": dict(
                                        (config.get("ranking_policy") or {}).get(
                                            "fit_label_thresholds"
                                        )
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
                            1
                            for record in cv_analysis_results
                            if str(record.get("status") or "")
                            == CV_ANALYSIS_READY_FOR_GENERATION_STATUS
                        ),
                        "cv_analysis_failed": sum(
                            1
                            for record in cv_analysis_results
                            if str(record.get("status") or "") == CV_ANALYSIS_FAILED_STATUS
                        ),
                        "cv_analysis_concurrency_effective": cv_analysis_effective_concurrency,
                    }
                )
                state["cv_analysis_results"] = cv_analysis_results
                state["cv_generation_debug_records"] = cv_generation_debug_records
                stage_boundary_result = _handle_stage_boundary(
                    run_id=run_id,
                    last_completed_stage="cv_analysis",
                    stop_after_stage=stop_after_stage,
                    state=state,
                    profile=profile,
                    config=config,
                    vector_top_n=vector_top_n,
                    candidate_summary=candidate_summary,
                    candidate_query_components=candidate_query_components,
                    candidate_query_debug=candidate_query_debug,
                    final_top_n=final_top_n,
                    stage_progress_callback=stage_progress_callback,
                )
                if stage_boundary_result is not None:
                    return stage_boundary_result

        cv_analysis_results = list(state["cv_analysis_results"])
        if cancellation_check and cancellation_check():
            raise PipelineCancelled("Cancelled before CV generation")
        generation_ready_records = [
            record for record in cv_analysis_results
            if str(record.get("status") or "") == "ready_for_generation"
        ]
        indexed_generation_ready_records = list(enumerate(generation_ready_records))
        configured_cv_generation_concurrency = get_stage_runtime_concurrency(
            config,
            stage="cv_generation",
            default=1,
        )
        cv_generation_sleep_secs = get_stage_runtime_sleep_secs(
            config,
            stage="cv_generation",
            default=0.0,
        )
        generation_total = len(indexed_generation_ready_records)
        cv_generation_effective_concurrency = _effective_stage_concurrency(
            configured_cv_generation_concurrency,
            generation_total,
        )
        cv_generation_reuse_enabled = _reuse_stage_enabled(config, "cv_generation")
        cv_generation_fingerprint_by_index: dict[int, str] = {}
        cv_generation_reuse_index: dict[str, dict[str, Any]] = {}
        if cv_generation_reuse_enabled and indexed_generation_ready_records:
            for generation_index, analysis_record in indexed_generation_ready_records:
                fingerprint_record = build_cv_generation_input_fingerprint(analysis_record, config)
                cv_generation_fingerprint_by_index[generation_index] = str(fingerprint_record["fingerprint"])
            cv_generation_reuse_index = lookup_reusable_cv_versions(
                list(cv_generation_fingerprint_by_index.values()),
                config,
                limit=max(500, len(cv_generation_fingerprint_by_index) * 3),
            )

        def _prepare_cv_generation_work_item(
            *,
            generation_index: int,
            analysis_record: dict[str, Any],
        ) -> dict[str, Any]:
            job = dict(analysis_record.get("job_snapshot") or {})
            evidence = list(analysis_record.get("evidence_payload") or [])
            evidence_used = list(analysis_record.get("evidence_used") or [])
            evidence_selection_summary = dict(analysis_record.get("evidence_selection_summary") or {})
            analysis_input_summary = build_analysis_input_summary(job)
            return {
                "job": job,
                "evidence": evidence,
                "evidence_used": evidence_used,
                "evidence_selection_summary": evidence_selection_summary,
                "analysis_input_summary": analysis_input_summary,
                "analysis_grounding": _build_validation_grounding_payload(
                    evidence_payload=evidence,
                    evidence_used=evidence_used,
                    evidence_selection_summary=evidence_selection_summary,
                    analysis_input_summary=analysis_input_summary,
                ),
                "gap": analysis_record.get("gap_summary"),
                "fit": str(analysis_record.get("fit_classification") or "skip"),
                "generation_worker_slot": generation_index % cv_generation_effective_concurrency,
            }

        def _initialize_cv_generation_runtime_state(work_item: dict[str, Any]) -> dict[str, Any]:
            job = dict(work_item["job"])
            job_llm_runtime_observations: list[dict[str, Any]] = []
            return {
                "job": job,
                "evidence": list(work_item["evidence"]),
                "evidence_used": list(work_item["evidence_used"]),
                "evidence_selection_summary": dict(work_item["evidence_selection_summary"]),
                "analysis_input_summary": dict(work_item["analysis_input_summary"]),
                "analysis_grounding": cast(AnalysisGroundingPayload, work_item["analysis_grounding"]),
                "gap": work_item["gap"],
                "fit": str(work_item["fit"] or "skip"),
                "structured_cv_initial": None,
                "validation_initial": None,
                "repair_attempt": dict(_EMPTY_REPAIR_ATTEMPT),
                "structured_cv_final": None,
                "markdown_final": None,
                "job_llm_runtime_observations": job_llm_runtime_observations,
                "job_cv_generation_model_value": _resolved_cv_generation_model(
                    cv_generation_model_value,
                    job_llm_runtime_observations,
                ),
                "job_cv_generation_trace": None,
                "generation_attempt_count": 1,
                "generation_started_at_iso": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "generation_finished_at_iso": None,
                "generation_worker_slot": int(work_item["generation_worker_slot"]),
            }

        def _emit_cv_generation_started_event(
            *,
            generation_index: int,
            generation_total: int,
            state: dict[str, Any],
        ) -> None:
            if reporter is None:
                return
            job = cast(dict[str, Any], state["job"])
            fit = str(state["fit"] or "skip")
            generation_started_at_iso = str(state["generation_started_at_iso"])
            generation_worker_slot = int(state["generation_worker_slot"])
            reporter.emit(
                "layer4_cv_generation_started",
                "info",
                f"CV generation started for {job.get('job_url')} [item {generation_index + 1}/{generation_total}]",
                _bounded_event_payload(
                    event_name="cv_generation_started",
                    event_family="invocation",
                    source_stage="cv_generation",
                    event_status="started",
                    job_url=str(job.get("job_url") or ""),
                    fallback_used=False,
                    input_snapshot={
                        "ranking_fit_label": _authoritative_ranking_fit_label(job, fit),
                        "fit_classification": fit,
                        "generation_index": int(generation_index),
                        "generation_total": int(generation_total),
                    },
                    output_snapshot={
                        "configured_concurrency": int(configured_cv_generation_concurrency),
                        "cv_generation_concurrency_effective": int(cv_generation_effective_concurrency),
                        "worker_slot": int(generation_worker_slot),
                        "started_at": generation_started_at_iso,
                    },
                    artifact_refs={"stage_id": "cv_generation"},
                ),
            )  # type: ignore[union-attr]

        def _emit_cv_generation_result_event(
            *,
            state: dict[str, Any],
            status: str,
            attempt_count: int = 1,
            retry_count: int = 0,
            latency_ms: int | None = None,
            usage: dict[str, Any] | None = None,
            cost: dict[str, Any] | None = None,
            reuse_status: str | None = None,
            reused_cv_version_id: str | None = None,
            cv_generation_input_fingerprint: str | None = None,
            review_required_reason_code: str | None = None,
            validation_evidence_fingerprint: str | None = None,
        ) -> None:
            if reporter is None:
                return
            effective_reuse_status = str(reuse_status or "").strip() or "fresh_compute"
            job = cast(dict[str, Any], state["job"])
            fit = str(state["fit"] or "skip")
            generation_started_at_iso = str(state["generation_started_at_iso"])
            generation_worker_slot = int(state["generation_worker_slot"])
            generation_finished_at_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            reporter.emit(
                "layer4_cv_generation_result",
                "info",
                f"CV generation result for {job.get('job_url')}: {status}",
                _bounded_event_payload(
                    event_name="cv_generation_result",
                    event_family="decision",
                    source_stage="cv_generation",
                    event_status="completed",
                    job_url=str(job.get("job_url") or ""),
                    deterministic_outcome=str(status or ""),
                    fallback_used=False,
                    input_snapshot={
                        "ranking_fit_label": _authoritative_ranking_fit_label(job, fit),
                        "fit_classification": fit,
                    },
                    output_snapshot={
                        "status": str(status or ""),
                        "reuse_status": effective_reuse_status,
                        "reused_cv_version_id": str(reused_cv_version_id or ""),
                        "cv_generation_input_fingerprint": str(cv_generation_input_fingerprint or ""),
                        "review_required_reason_code": str(review_required_reason_code or ""),
                        "validation_evidence_fingerprint": str(validation_evidence_fingerprint or ""),
                        "attempt_count": int(attempt_count),
                        "retry_count": int(retry_count),
                        "configured_concurrency": int(configured_cv_generation_concurrency),
                        "cv_generation_concurrency_effective": int(cv_generation_effective_concurrency),
                        "worker_slot": int(generation_worker_slot),
                        "started_at": generation_started_at_iso,
                        "finished_at": generation_finished_at_iso,
                        "status_flat": str(status or ""),
                        "reuse_status_flat": effective_reuse_status,
                        "reused_cv_version_id_flat": str(reused_cv_version_id or ""),
                        "cv_generation_input_fingerprint_flat": str(cv_generation_input_fingerprint or ""),
                        "review_required_reason_code_flat": str(review_required_reason_code or ""),
                        "validation_evidence_fingerprint_flat": str(validation_evidence_fingerprint or ""),
                    },
                    artifact_refs={"stage_id": "cv_generation"},
                    latency_ms=latency_ms,
                    usage=usage,
                    cost=cost,
                ),
            )  # type: ignore[union-attr]

        def _emit_cv_generation_invoked_event(
            *,
            state: dict[str, Any],
            cv_generation_model_value: str | None,
        ) -> None:
            if reporter is None:
                return
            job = cast(dict[str, Any], state["job"])
            fit = str(state["fit"] or "skip")
            reporter.emit(
                "layer4_cv_generation_invoked",
                "info",
                f"CV generation invoked for {job.get('job_url')}",
                _bounded_event_payload(
                    event_name="cv_generation_invoked",
                    event_family="invocation",
                    source_stage="cv_generation",
                    event_status="started",
                    job_url=str(job.get("job_url") or ""),
                    fallback_used=False,
                    provenance={
                        "cv_generation_model": cv_generation_model_value,
                        "configured_concurrency": configured_cv_generation_concurrency,
                        "cv_generation_concurrency_effective": cv_generation_effective_concurrency,
                    },
                    input_snapshot={
                        "ranking_fit_label": _authoritative_ranking_fit_label(job, fit),
                        "fit_classification": fit,
                    },
                    output_snapshot={
                        "configured_concurrency": configured_cv_generation_concurrency,
                        "cv_generation_concurrency_effective": cv_generation_effective_concurrency,
                    },
                    artifact_refs={"stage_id": "cv_generation"},
                ),
            )  # type: ignore[union-attr]

        def _handle_cv_generation_accepted_debug_and_events(
            *,
            state: dict[str, Any],
            analysis_record: dict[str, Any],
            structured_cv_final: dict[str, Any] | None,
            markdown_final: str | None,
            enabled_cv_sections: list[str],
            cv_prompt_id_value: str,
            cv_prompt_template_path_value: str,
            job_cv_generation_model_value: str | None,
            job_llm_runtime_observations: list[dict[str, Any]],
            job_cv_generation_trace: dict[str, Any] | None,
            generation_attempt_count: int,
            latency_ms: int,
            run_id: str,
            cv_generation_input_fingerprint: str | None,
        ) -> None:
            job = cast(dict[str, Any], state["job"])
            fit = str(state["fit"] or "skip")
            evidence_used = cast(list[dict[str, Any]], state["evidence_used"])
            evidence_selection_summary = cast(dict[str, Any], state["evidence_selection_summary"])
            analysis_input_summary = cast(dict[str, Any], state["analysis_input_summary"])
            gap = state["gap"]
            structured_cv_initial = cast(dict[str, Any] | None, state["structured_cv_initial"])
            validation_initial = cast(dict[str, Any] | None, state["validation_initial"])
            repair_attempt = cast(dict[str, Any], state["repair_attempt"])

            canonical_result = cast(dict[str, Any], state["canonical_result"])
            accepted_debug_record = _build_cv_generation_debug_record(
                generation_result=canonical_result,
                enabled_sections=enabled_cv_sections,
                cv_generation_model=job_cv_generation_model_value,
                cv_prompt_id=cv_prompt_id_value,
                cv_prompt_template_path=cv_prompt_template_path_value,
                attempt_count=generation_attempt_count,
            )
            cv_generation_debug_records.append(accepted_debug_record)
            _emit_cv_generation_item_observation(
                run_id=run_id,
                analysis_record=analysis_record,
                debug_record=accepted_debug_record,
            )
            _emit_cv_generation_result_event(
                state=state,
                status="accepted",
                attempt_count=generation_attempt_count,
                retry_count=max(generation_attempt_count - 1, 0),
                latency_ms=latency_ms,
                cv_generation_input_fingerprint=cv_generation_input_fingerprint,
                review_required_reason_code=str(accepted_debug_record.get("review_required_reason_code") or ""),
                validation_evidence_fingerprint=str(accepted_debug_record.get("validation_evidence_fingerprint") or ""),
            )

        def _handle_cv_generation_failure(
            *,
            state: dict[str, Any],
            analysis_record: dict[str, Any],
            structured_cv_final: dict[str, Any] | None,
            markdown_final: str | None,
            cv_prompt_id_value: str,
            cv_prompt_template_path_value: str,
            enabled_cv_sections: list[str],
            latency_ms: int,
            run_id: str,
            exc: Exception,
            cv_generation_input_fingerprint: str | None,
        ) -> None:
            job = cast(dict[str, Any], state["job"])
            fit = str(state["fit"] or "skip")
            evidence_used = cast(list[dict[str, Any]], state["evidence_used"])
            evidence_selection_summary = cast(dict[str, Any], state["evidence_selection_summary"])
            analysis_input_summary = cast(dict[str, Any], state["analysis_input_summary"])
            gap = state["gap"]
            structured_cv_initial = cast(dict[str, Any] | None, state["structured_cv_initial"])
            validation_initial = cast(dict[str, Any] | None, state["validation_initial"])
            repair_attempt = cast(dict[str, Any], state["repair_attempt"])
            job_cv_generation_model_value = cast(str | None, state["job_cv_generation_model_value"])
            job_llm_runtime_observations = cast(list[dict[str, Any]], state["job_llm_runtime_observations"])
            job_cv_generation_trace = cast(dict[str, Any] | None, state["job_cv_generation_trace"])

            logger.error("[run_id=%s] Failed for %s: %s", run_id, job.get("job_url"), exc)
            canonical_result = cast(dict[str, Any] | None, state.get("canonical_result"))
            persistence_result = (
                transition_cv_generation_persistence_failed(canonical_result, message=str(exc))
                if isinstance(canonical_result, dict)
                and str(canonical_result.get("status") or "") == "accepted"
                and (structured_cv_final is not None or markdown_final is not None)
                else None
            )
            failure_status = str((persistence_result or {}).get("status") or "generation_failed")
            failure_result = persistence_result or canonical_result
            if not isinstance(failure_result, dict):
                return
            failure_debug_record = _build_cv_generation_debug_record(
                generation_result=failure_result,
                enabled_sections=enabled_cv_sections,
                cv_generation_model=job_cv_generation_model_value,
                cv_prompt_id=cv_prompt_id_value,
                cv_prompt_template_path=cv_prompt_template_path_value,
            )
            failure_debug_record["cv_generation_input_fingerprint"] = cv_generation_input_fingerprint
            _emit_cv_generation_result_event(
                state=state,
                status=failure_status,
                attempt_count=1,
                retry_count=0,
                latency_ms=latency_ms,
                cv_generation_input_fingerprint=cv_generation_input_fingerprint,
                review_required_reason_code=str(failure_debug_record.get("review_required_reason_code") or ""),
                validation_evidence_fingerprint=str(failure_debug_record.get("validation_evidence_fingerprint") or ""),
            )
            cv_generation_debug_records.append(failure_debug_record)
            _emit_cv_generation_item_observation(
                run_id=run_id,
                analysis_record=analysis_record,
                debug_record=failure_debug_record,
            )
            if reporter is not None:
                reporter.emit(
                    "layer4_cv_error",
                    "error",
                    f"CV generation failed for {job.get('job_url')}: {exc}",
                    _bounded_event_payload(
                        event_name="cv_generation_decision",
                        event_family="decision",
                        source_stage="cv_generation",
                        event_status="completed",
                        job_url=str(job.get("job_url") or ""),
                        deterministic_outcome="rejected",
                        stage_owned_subreason=failure_status,
                        provenance={
                            "cv_generation_model": job_cv_generation_model_value,
                        },
                        input_snapshot={
                            "ranking_fit_label": _authoritative_ranking_fit_label(job, fit),
                            "fit_classification": fit,
                            "selected_evidence_count": len(evidence_used),
                        },
                        output_snapshot={
                            "error_stage": failure_stage,
                        },
                        artifact_refs={"stage_id": "cv_generation"},
                    ),
                )  # type: ignore[union-attr]

        generation_work_items_by_index: dict[int, tuple[dict[str, Any], dict[str, Any]]] = {}
        if cv_generation_effective_concurrency > 1:
            def _prepare_indexed_work_item(
                generation_index: int,
                analysis_record: dict[str, Any],
            ) -> tuple[int, dict[str, Any], dict[str, Any]]:
                prepared = _prepare_cv_generation_work_item(
                    generation_index=generation_index,
                    analysis_record=analysis_record,
                )
                return generation_index, analysis_record, prepared

            with ThreadPoolExecutor(max_workers=cv_generation_effective_concurrency) as executor:
                future_to_index: dict[Future[tuple[int, dict[str, Any], dict[str, Any]]], int] = {}
                for generation_index, analysis_record in indexed_generation_ready_records:
                    future = executor.submit(_prepare_indexed_work_item, generation_index, analysis_record)
                    future_to_index[future] = generation_index
                for future in future_to_index:
                    completed_index, completed_record, completed_prepared = future.result()
                    generation_work_items_by_index[completed_index] = (completed_record, completed_prepared)
        else:
            for generation_index, analysis_record in indexed_generation_ready_records:
                generation_work_items_by_index[generation_index] = (
                    analysis_record,
                    _prepare_cv_generation_work_item(
                        generation_index=generation_index,
                        analysis_record=analysis_record,
                    ),
                )

        def _begin_cv_generation_item(
            generation_index: int,
            analysis_record: dict[str, Any],
            work_item: dict[str, Any],
        ) -> dict[str, Any]:
            with observe_span(
                "pipeline.cv_generation",
                attributes={
                    "run_id": run_id,
                    "generation_ready_jobs": generation_total,
                    "job_url": str((work_item["job"] or {}).get("job_url") or ""),
                },
            ):
                generation_state = _initialize_cv_generation_runtime_state(work_item)
                _emit_cv_generation_started_event(
                    generation_index=generation_index,
                    generation_total=generation_total,
                    state=generation_state,
                )
            runtime = {
                "analysis_record": analysis_record,
                "generation_state": generation_state,
                "cv_generation_started_monotonic": time.monotonic(),
                "job": cast(dict[str, Any], generation_state["job"]),
                "evidence": cast(list[dict[str, Any]], generation_state["evidence"]),
                "evidence_used": cast(list[dict[str, Any]], generation_state["evidence_used"]),
                "evidence_selection_summary": cast(dict[str, Any], generation_state["evidence_selection_summary"]),
                "analysis_input_summary": cast(dict[str, Any], generation_state["analysis_input_summary"]),
                "analysis_grounding": cast(AnalysisGroundingPayload, generation_state["analysis_grounding"]),
                "gap": generation_state["gap"],
                "fit": str(generation_state["fit"] or "skip"),
                "structured_cv_initial": cast(dict[str, Any] | None, generation_state["structured_cv_initial"]),
                "validation_initial": cast(dict[str, Any] | None, generation_state["validation_initial"]),
                "repair_attempt": cast(dict[str, Any], generation_state["repair_attempt"]),
                "structured_cv_final": cast(dict[str, Any] | None, generation_state["structured_cv_final"]),
                "markdown_final": cast(str | None, generation_state["markdown_final"]),
                "job_llm_runtime_observations": cast(list[dict[str, Any]], generation_state["job_llm_runtime_observations"]),
                "job_cv_generation_model_value": cast(str | None, generation_state["job_cv_generation_model_value"]),
                "job_cv_generation_trace": cast(dict[str, Any] | None, generation_state["job_cv_generation_trace"]),
                "generation_attempt_count": int(generation_state["generation_attempt_count"]),
                "generation_started_at_iso": str(generation_state["generation_started_at_iso"]),
                "generation_finished_at_iso": cast(str | None, generation_state["generation_finished_at_iso"]),
                "generation_worker_slot": int(generation_state["generation_worker_slot"]),
            }
            return runtime

        def _execute_cv_generation_item(
            *,
            generation_state: dict[str, Any],
            analysis_record: dict[str, Any],
            validation: dict[str, Any],
            structured_cv: dict[str, Any] | None,
            cv: str,
            fit: str,
            gap: Any,
            evidence: list[dict[str, Any]],
            job: dict[str, Any],
            analysis_grounding: AnalysisGroundingPayload,
            cv_generation_started_monotonic: float,
            structured_cv_final: dict[str, Any] | None,
            markdown_final: str | None,
            job_cv_generation_model_value: str | None,
            job_llm_runtime_observations: list[dict[str, Any]],
            job_cv_generation_trace: dict[str, Any] | None,
            generation_attempt_count: int,
            validation_initial: dict[str, Any] | None,
            repair_attempt: dict[str, Any],
            evidence_used: list[dict[str, Any]],
            evidence_selection_summary: dict[str, Any],
            analysis_input_summary: dict[str, Any],
            cv_generation_input_fingerprint: str | None,
        ) -> tuple[bool, dict[str, Any] | None, str | None]:
            _emit_cv_generation_invoked_event(
                state=generation_state,
                cv_generation_model_value=job_cv_generation_model_value,
            )
            latency_ms = int((time.monotonic() - cv_generation_started_monotonic) * 1000)
            canonical_result = cast(dict[str, Any], generation_state.get("canonical_result") or {})
            cv_generation_input_fingerprint = str(
                canonical_result.get("cv_generation_input_fingerprint")
                or cv_generation_input_fingerprint
                or ""
            ) or None
            cv_generation_reuse_status = str(
                canonical_result.get("cv_generation_reuse_status") or "fresh_compute"
            )
            reuse_decision = dict(
                canonical_result.get("reuse_decision")
                or build_reuse_decision(
                    decision=cv_generation_reuse_status,
                    reason_code="fresh_compute_required",
                    fingerprint=cv_generation_input_fingerprint,
                    source_artifact_type="cv_generation",
                )
            )
            structured_cv_final = structured_cv
            markdown_final = cv
            version = create_cv_version_record(
                job_url=str(job.get("job_url") or ""),
                run_id=run_id,
                enrichment_version=str(config.get("enrichment_version") or "v1"),
                vector_rank=int(job.get("vector_rank") or 0),
                ai_score=float(job.get("ai_score") or 0.0),
                final_score=float(job.get("baseline_fit") or 0.0),
                evidence_ids=[str(e.get("evidence_id") or "") for e in evidence],
                prompt_version=cv_prompt_version_value,
                cv_markdown=cv,
                gap_summary=gap or {},
                fit_classification=fit,
                cv_structured=structured_cv,
                cv_generation_model=job_cv_generation_model_value,
                cv_prompt_version=cv_prompt_version_value,
                cv_generation_input_fingerprint=cv_generation_input_fingerprint,
                cv_generation_reuse_status=cv_generation_reuse_status,
            )
            pipeline_store.store_cv_version(version, config)
            results.append({
                "job_url": str(job.get("job_url") or ""),
                "fit": fit,
                "ranking_fit_label": _authoritative_ranking_fit_label(job, fit),
                "cv_version_id": version["version_id"],
                "gap": gap,
                "structured_cv": structured_cv,
                "cv_generation_model": job_cv_generation_model_value,
                "llm_runtime_observations": job_llm_runtime_observations,
                "cv_prompt_id": cv_prompt_id_value,
                "cv_prompt_template_path": cv_prompt_template_path_value,
                "cv_markdown": cv,
                "generated_at": version.get("generated_at"),
                "fit_classification": fit,
                "cv_generation_reuse_status": cv_generation_reuse_status,
                "cv_generation_input_fingerprint": cv_generation_input_fingerprint,
                "reuse_decision": reuse_decision,
            })
            _handle_cv_generation_accepted_debug_and_events(
                state=generation_state,
                analysis_record=analysis_record,
                structured_cv_final=structured_cv_final,
                markdown_final=markdown_final,
                enabled_cv_sections=enabled_cv_sections,
                cv_prompt_id_value=cv_prompt_id_value,
                cv_prompt_template_path_value=cv_prompt_template_path_value,
                job_cv_generation_model_value=job_cv_generation_model_value,
                job_llm_runtime_observations=job_llm_runtime_observations,
                job_cv_generation_trace=job_cv_generation_trace,
                generation_attempt_count=generation_attempt_count,
                latency_ms=latency_ms,
                run_id=run_id,
                cv_generation_input_fingerprint=cv_generation_input_fingerprint,
            )
            logger.info("[run_id=%s] CV generated for %s (fit=%s)", run_id, job.get("job_url"), fit)
            return False, structured_cv_final, markdown_final

        def _run_canonical_cv_generation(
            *,
            analysis_record: dict[str, Any],
            job: dict[str, Any],
            generation_worker_slot: int,
            generation_started_at_iso: str,
            reusable_record: dict[str, Any] | None,
        ) -> dict[str, Any]:
            generation_result = run_agentic_cv_generation(
                analysis_record=analysis_record,
                profile=profile,
                config=config,
                reusable_record=reusable_record,
            )
            status = str(generation_result.get("status") or "generation_failed")
            fit = str(generation_result.get("fit_classification") or "skip")
            analysis_input_summary = dict(generation_result.get("analysis_input_summary") or {})
            evidence_used = list(generation_result.get("evidence_used") or [])
            evidence_selection_summary = dict(generation_result.get("evidence_selection_summary") or {})
            gap = generation_result.get("gap_summary")
            structured_cv_initial = cast(dict[str, Any] | None, generation_result.get("structured_cv_initial"))
            validation_initial = cast(dict[str, Any] | None, generation_result.get("validation_initial"))
            validation_final = cast(dict[str, Any] | None, generation_result.get("validation"))
            repair_attempt = dict(generation_result.get("repair_attempt") or _EMPTY_REPAIR_ATTEMPT)
            structured_cv_final = cast(dict[str, Any] | None, generation_result.get("structured_cv_final"))
            markdown_final = cast(str | None, generation_result.get("markdown_final"))
            llm_runtime_observations = cast(list[dict[str, Any]], generation_result.get("llm_runtime_observations") or [])
            cv_generation_trace = cast(dict[str, Any] | None, generation_result.get("cv_generation_trace"))
            generation_metrics = _extract_generation_trace_metrics(cv_generation_trace)
            attempt_count = max(int(generation_metrics["attempt_count"]), 1)
            cv_generation_model = _resolved_cv_generation_model(
                cv_generation_model_value,
                llm_runtime_observations,
            )
            reason_payload = cast(
                dict[str, str] | None,
                generation_result.get("outcome_reason") or generation_result.get("error"),
            )
            reporter_payload = None
            if reporter is not None:
                reporter_payload = {
                    "channel": "layer4_cv_generation_result",
                    "level": "info",
                    "message": f"CV generation result for {job.get('job_url')}: {status}",
                    "payload": _bounded_event_payload(
                        event_name="cv_generation_result",
                        event_family="decision",
                        source_stage="cv_generation",
                        event_status="completed",
                        job_url=str(job.get("job_url") or ""),
                        deterministic_outcome=status,
                        fallback_used=False,
                        input_snapshot={
                            "ranking_fit_label": _authoritative_ranking_fit_label(job, fit),
                            "fit_classification": fit,
                        },
                        output_snapshot={
                            "status": status,
                            "reuse_status": str(generation_result.get("cv_generation_reuse_status") or ""),
                            "reused_cv_version_id": str(generation_result.get("reused_cv_version_id") or ""),
                            "cv_generation_input_fingerprint": str(
                                generation_result.get("cv_generation_input_fingerprint") or ""
                            ),
                            "review_required_reason_code": str(
                                generation_result.get("review_required_reason_code") or ""
                            ),
                            "validation_evidence_fingerprint": str(
                                generation_result.get("validation_evidence_fingerprint") or ""
                            ),
                            "attempt_count": attempt_count,
                            "retry_count": max(attempt_count - 1, 0),
                            "configured_concurrency": int(configured_cv_generation_concurrency),
                            "cv_generation_concurrency_effective": int(
                                cv_generation_effective_concurrency
                            ),
                            "worker_slot": int(generation_worker_slot),
                            "started_at": generation_started_at_iso,
                            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        },
                        artifact_refs={"stage_id": "cv_generation"},
                    ),
                }
            if status != "accepted":
                debug_record = _build_cv_generation_debug_record(
                    generation_result=generation_result,
                    enabled_sections=enabled_cv_sections,
                    cv_generation_model=cv_generation_model,
                    cv_prompt_id=cv_prompt_id_value,
                    cv_prompt_template_path=cv_prompt_template_path_value,
                    attempt_count=attempt_count,
                )
                return {
                    "should_continue": True,
                    "deferred_debug_record": debug_record,
                    "deferred_observation": True,
                    "deferred_reporter_payload": reporter_payload,
                    "canonical_result": generation_result,
                }
            return {
                "should_continue": False,
                "deferred_reporter_payload": reporter_payload,
                "canonical_result": generation_result,
                "fit": fit,
                "analysis_input_summary": analysis_input_summary,
                "evidence_used": evidence_used,
                "evidence_selection_summary": evidence_selection_summary,
                "gap": gap,
                "structured_cv_initial": structured_cv_initial,
                "validation_initial": validation_initial,
                "repair_attempt": repair_attempt,
                "structured_cv_final": structured_cv_final,
                "markdown_final": markdown_final,
                "job_llm_runtime_observations": llm_runtime_observations,
                "job_cv_generation_model_value": cv_generation_model,
                "job_cv_generation_trace": cv_generation_trace,
                "generation_attempt_count": attempt_count,
                "structured_cv": structured_cv_final,
                "cv": str(markdown_final or ""),
                "validation": dict(validation_final or {"valid": True, "missing_sections": []}),
            }

        def _compute_cv_generation_outcome(
            *,
            analysis_record: dict[str, Any],
            job: dict[str, Any],
            generation_worker_slot: int,
            generation_started_at_iso: str,
            reusable_record: dict[str, Any] | None,
        ) -> dict[str, Any]:
            return _run_canonical_cv_generation(
                analysis_record=analysis_record,
                job=job,
                generation_worker_slot=generation_worker_slot,
                generation_started_at_iso=generation_started_at_iso,
                reusable_record=reusable_record,
            )

        generation_runtime_by_index: dict[int, dict[str, Any]] = {}
        for generation_index in sorted(generation_work_items_by_index):
            analysis_record, work_item = generation_work_items_by_index[generation_index]
            generation_runtime_by_index[generation_index] = _begin_cv_generation_item(generation_index, analysis_record, work_item)

        def _compute_for_index(generation_index: int) -> dict[str, Any]:
            runtime = generation_runtime_by_index[generation_index]
            reuse_fingerprint = str(cv_generation_fingerprint_by_index.get(generation_index) or "").strip()
            reusable_record = (
                cv_generation_reuse_index.get(reuse_fingerprint)
                if cv_generation_reuse_enabled and reuse_fingerprint
                else None
            )
            return _compute_cv_generation_outcome(
                analysis_record=cast(dict[str, Any], runtime["analysis_record"]),
                job=cast(dict[str, Any], runtime["job"]),
                generation_worker_slot=int(runtime["generation_worker_slot"]),
                generation_started_at_iso=str(runtime["generation_started_at_iso"]),
                reusable_record=reusable_record,
            )

        compute_outcomes_by_index: dict[int, dict[str, Any]] = {}
        if generation_runtime_by_index:
            with ThreadPoolExecutor(max_workers=cv_generation_effective_concurrency) as executor:
                generation_indexes = sorted(generation_runtime_by_index)
                future_to_generation_index: dict[Future[dict[str, Any]], int] = {}
                for position, generation_index in enumerate(generation_indexes):
                    future_to_generation_index[
                        executor.submit(_compute_for_index, generation_index)
                    ] = generation_index
                    if position < len(generation_indexes) - 1 and cv_generation_sleep_secs > 0:
                        time.sleep(cv_generation_sleep_secs)
                pending_futures = set(future_to_generation_index)
                heartbeat_count = 0
                heartbeat_started_monotonic = time.monotonic()
                while pending_futures:
                    completed_futures, pending_futures = wait(
                        pending_futures,
                        timeout=15.0,
                        return_when=FIRST_COMPLETED,
                    )
                    if not completed_futures:
                        heartbeat_count += 1
                        if reporter is not None:
                            reporter.emit(
                                "cv_generation_heartbeat",
                                "info",
                                "CV generation in progress",
                                {
                                    "phase": "batch_progress",
                                    "generation_total": generation_total,
                                    "completed_items": len(compute_outcomes_by_index),
                                    "pending_items": len(pending_futures),
                                    "heartbeat_count": heartbeat_count,
                                    "elapsed_secs": int(
                                        time.monotonic() - heartbeat_started_monotonic
                                    ),
                                    "heartbeat_interval_secs": 15,
                                    "configured_concurrency": int(
                                        configured_cv_generation_concurrency
                                    ),
                                    "cv_generation_concurrency_effective": int(
                                        cv_generation_effective_concurrency
                                    ),
                                },
                            )
                        continue
                    for future in completed_futures:
                        generation_index = future_to_generation_index[future]
                        try:
                            compute_outcomes_by_index[generation_index] = future.result()
                        except Exception as exc:
                            compute_outcomes_by_index[generation_index] = {"_compute_exception": exc}

        for generation_index in sorted(generation_work_items_by_index):
            runtime = generation_runtime_by_index[generation_index]
            analysis_record = cast(dict[str, Any], runtime["analysis_record"])
            generation_state = cast(dict[str, Any], runtime["generation_state"])
            cv_generation_started_monotonic = cast(float, runtime["cv_generation_started_monotonic"])
            job = cast(dict[str, Any], runtime["job"])
            evidence = cast(list[dict[str, Any]], runtime["evidence"])
            evidence_used = cast(list[dict[str, Any]], runtime["evidence_used"])
            evidence_selection_summary = cast(dict[str, Any], runtime["evidence_selection_summary"])
            analysis_input_summary = cast(dict[str, Any], runtime["analysis_input_summary"])
            analysis_grounding = cast(AnalysisGroundingPayload, runtime["analysis_grounding"])
            gap = runtime["gap"]
            fit = str(runtime["fit"] or "skip")
            structured_cv_initial = cast(dict[str, Any] | None, runtime["structured_cv_initial"])
            validation_initial = cast(dict[str, Any] | None, runtime["validation_initial"])
            repair_attempt = cast(dict[str, Any], runtime["repair_attempt"])
            structured_cv_final = cast(dict[str, Any] | None, runtime["structured_cv_final"])
            markdown_final = cast(str | None, runtime["markdown_final"])
            job_llm_runtime_observations = cast(list[dict[str, Any]], runtime["job_llm_runtime_observations"])
            job_cv_generation_model_value = cast(str | None, runtime["job_cv_generation_model_value"])
            job_cv_generation_trace = cast(dict[str, Any] | None, runtime["job_cv_generation_trace"])
            generation_attempt_count = int(runtime["generation_attempt_count"])
            reuse_fingerprint = str(cv_generation_fingerprint_by_index.get(generation_index) or "").strip()
            try:
                compute_outcome = compute_outcomes_by_index[generation_index]
                compute_exception = cast(Exception | None, compute_outcome.get("_compute_exception"))
                if compute_exception is not None:
                    raise compute_exception

                canonical_outcome = compute_outcome
                if cast(bool, canonical_outcome["should_continue"]):
                    deferred_reporter_payload = cast(
                        dict[str, Any] | None,
                        canonical_outcome.get("deferred_reporter_payload"),
                    )
                    if deferred_reporter_payload is not None and reporter is not None:
                        reporter.emit(
                            str(deferred_reporter_payload.get("channel") or "layer4_cv_generation_result"),
                            str(deferred_reporter_payload.get("level") or "info"),
                            str(deferred_reporter_payload.get("message") or ""),
                            cast(dict[str, Any], deferred_reporter_payload.get("payload") or {}),
                        )  # type: ignore[union-attr]
                    deferred_debug_record = cast(
                        dict[str, Any] | None,
                        canonical_outcome.get("deferred_debug_record"),
                    )
                    if deferred_debug_record is not None:
                        cv_generation_debug_records.append(deferred_debug_record)
                        if cast(bool, canonical_outcome.get("deferred_observation")):
                            _emit_cv_generation_item_observation(
                                run_id=run_id,
                                analysis_record=analysis_record,
                                debug_record=deferred_debug_record,
                            )
                    continue
                fit = str(canonical_outcome["fit"] or fit)
                analysis_input_summary = cast(dict[str, Any], canonical_outcome["analysis_input_summary"])
                evidence_used = cast(list[dict[str, Any]], canonical_outcome["evidence_used"])
                evidence_selection_summary = cast(dict[str, Any], canonical_outcome["evidence_selection_summary"])
                gap = canonical_outcome["gap"]
                structured_cv_initial = cast(dict[str, Any] | None, canonical_outcome["structured_cv_initial"])
                validation_initial = cast(dict[str, Any] | None, canonical_outcome["validation_initial"])
                repair_attempt = cast(dict[str, Any], canonical_outcome["repair_attempt"])
                structured_cv_final = cast(dict[str, Any] | None, canonical_outcome["structured_cv_final"])
                markdown_final = cast(str | None, canonical_outcome["markdown_final"])
                job_llm_runtime_observations = cast(list[dict[str, Any]], canonical_outcome["job_llm_runtime_observations"])
                job_cv_generation_model_value = cast(str | None, canonical_outcome["job_cv_generation_model_value"])
                job_cv_generation_trace = cast(dict[str, Any] | None, canonical_outcome["job_cv_generation_trace"])
                generation_attempt_count = int(canonical_outcome["generation_attempt_count"])
                structured_cv = cast(dict[str, Any] | None, canonical_outcome["structured_cv"])
                cv = str(canonical_outcome["cv"] or "")
                validation = cast(dict[str, Any], canonical_outcome["validation"])
                generation_state["canonical_result"] = canonical_outcome.get("canonical_result")
                generation_state["fit"] = fit
                generation_state["evidence_used"] = evidence_used
                generation_state["evidence_selection_summary"] = evidence_selection_summary
                generation_state["analysis_input_summary"] = analysis_input_summary
                generation_state["gap"] = gap
                generation_state["structured_cv_initial"] = structured_cv_initial
                generation_state["validation_initial"] = validation_initial
                generation_state["repair_attempt"] = repair_attempt
                generation_state["structured_cv_final"] = structured_cv_final
                generation_state["markdown_final"] = markdown_final
                generation_state["job_llm_runtime_observations"] = job_llm_runtime_observations
                generation_state["job_cv_generation_model_value"] = job_cv_generation_model_value
                generation_state["job_cv_generation_trace"] = job_cv_generation_trace
                generation_state["generation_attempt_count"] = generation_attempt_count

                should_continue, structured_cv_final, markdown_final = _execute_cv_generation_item(
                    generation_state=generation_state,
                    analysis_record=analysis_record,
                    validation=validation,
                    structured_cv=structured_cv,
                    cv=cv,
                    fit=fit,
                    gap=gap,
                    evidence=evidence,
                    job=job,
                    analysis_grounding=analysis_grounding,
                    cv_generation_started_monotonic=cv_generation_started_monotonic,
                    structured_cv_final=structured_cv_final,
                    markdown_final=markdown_final,
                    job_cv_generation_model_value=job_cv_generation_model_value,
                    job_llm_runtime_observations=job_llm_runtime_observations,
                    job_cv_generation_trace=job_cv_generation_trace,
                    generation_attempt_count=generation_attempt_count,
                    validation_initial=validation_initial,
                    repair_attempt=repair_attempt,
                    evidence_used=evidence_used,
                    evidence_selection_summary=evidence_selection_summary,
                    analysis_input_summary=analysis_input_summary,
                    cv_generation_input_fingerprint=reuse_fingerprint or None,
                )
                if should_continue:
                    continue

            except Exception as exc:  # per-job failure — log and skip, don't crash the run
                _handle_cv_generation_failure(
                    state=generation_state,
                    analysis_record=analysis_record,
                    structured_cv_final=structured_cv_final,
                    markdown_final=markdown_final,
                    cv_prompt_id_value=cv_prompt_id_value,
                    cv_prompt_template_path_value=cv_prompt_template_path_value,
                    enabled_cv_sections=enabled_cv_sections,
                    latency_ms=int((time.monotonic() - cv_generation_started_monotonic) * 1000),
                    run_id=run_id,
                    exc=exc,
                    cv_generation_input_fingerprint=reuse_fingerprint or None,
                )
                continue

        set_span_attributes(
            {
                "generation_ready_jobs": len(generation_ready_records),
                "generated_cvs": len(results),
                "cv_generation_review_required": sum(
                    1 for record in cv_generation_debug_records
                    if str(record.get("status") or "") == CV_GENERATION_REVIEW_REQUIRED_STATUS
                ),
                "cv_generation_failed": sum(
                    1 for record in cv_generation_debug_records
                    if str(record.get("status") or "") in {"validation_failed", "generation_failed", "persistence_failed"}
                ),
            }
        )
        state["cv_analysis_results"] = cv_analysis_results
        state["cv_results"] = results
        state["cv_generation_debug_records"] = cv_generation_debug_records
        stage_transition_artifacts = _build_stage_transition_artifacts(
            raw_jobs=raw_jobs,
            normalized=normalized,
            deduplicated_jobs=deduplicated_jobs,
            pre_filter_rejected_jobs=pre_filter_rejected_jobs,
            enriched=enriched,
            passed_jobs=passed_jobs,
            candidate_filter_rejected_jobs=candidate_filter_rejected_jobs,
            raw_shortlist=raw_shortlist,
            shortlist=shortlist,
            shortlist_audit_rows=shortlist_audit_rows,
            shortlist_diagnostics=shortlist_diagnostics,
            vector_top_n=vector_top_n,
            candidate_summary=candidate_summary,
            candidate_query_components=candidate_query_components,
            candidate_query_debug=candidate_query_debug,
            ai_scores=ai_scores,
            ranking_inputs=ranking_inputs,
            ranked=ranked,
            cv_analysis_results=cv_analysis_results,
            enrich_llm_runtime_observations=enrich_llm_runtime_observations,
            ranking_llm_runtime_observations=ranking_llm_runtime_observations,
            final_top_n=final_top_n,
            cv_generation_debug_records=cv_generation_debug_records,
            profile=profile,
            config=config,
            resolved_preference_policy=dict(state.get("resolved_preference_policy") or {}),
        )
        late_stage_reuse_snapshots = _build_late_stage_reuse_snapshots(
            ai_scores=ai_scores,
            cv_analysis_results=cv_analysis_results,
        )
        summary: dict[str, Any] = {
            "run_id": run_id,
            "total_jobs": len(raw_jobs),
            "passed_filter": len(passed_jobs),
            "ranked": len(ranked),
            "cvs_generated": len(results),
            "cv_analysis_trace": _build_cv_analysis_trace_summary(
                run_id=run_id,
                cv_analysis_results=cv_analysis_results,
            ),
            "cv_generation_trace": _build_cv_generation_trace_summary(
                run_id=run_id,
                cv_generation_debug_records=cv_generation_debug_records,
            ),
            "late_stage_reuse_snapshots": late_stage_reuse_snapshots,
            "cv_generation_debug_records": cv_generation_debug_records,
            "mapping_suggestions": _collect_mapping_suggestions(enriched, run_id),
            "stage_transition_artifacts": stage_transition_artifacts,
            "export_results": _build_export_results(
                raw_jobs=raw_jobs,
                enriched=enriched,
                deduplicated_jobs=deduplicated_jobs,
                pre_filter_rejected=pre_filter_rejected_jobs,
                candidate_filter_rejected=candidate_filter_rejected_jobs,
                passed_jobs=passed_jobs,
                raw_shortlist=raw_shortlist,
                shortlist_for_scoring=shortlist,
                ranking_inputs=ranking_inputs,
                ranked=ranked,
                cv_analysis_results=cv_analysis_results,
                cv_results=results,
                cv_generation_debug_records=cv_generation_debug_records,
                vector_search_top_n=vector_top_n,
                run_id=run_id,
                stage_transition_artifacts=stage_transition_artifacts,
            ),
        }
        logger.info("Pipeline run complete [run_id=%s] summary=%s", run_id, summary)
        if reporter is not None:
            analysis_quality = _build_cv_analysis_quality_metrics(cv_analysis_results)
            generation_quality = _build_cv_generation_quality_metrics(cv_generation_debug_records)
            late_stage_reuse_metrics = _build_late_stage_reuse_metrics(
                enriched=enriched,
                ai_scores=ai_scores,
                cv_analysis_results=cv_analysis_results,
                cv_generation_debug_records=cv_generation_debug_records,
            )
            reuse_anomaly = _reuse_anomaly_payload(
                reuse_metrics=late_stage_reuse_metrics,
                config=config,
            )
            total_retry_count = sum(
                max(0, int(record.get("attempt_count") or 1) - 1)
                for record in cv_generation_debug_records
                if isinstance(record, dict)
            )
            event_summary = {
                "run_id": run_id,
                "total_jobs": summary["total_jobs"],
                "passed_filter": summary["passed_filter"],
                "ranked": summary["ranked"],
                "cvs_generated": summary["cvs_generated"],
                "quality_summary": {
                    "acceptance_review_failure": {
                        "accepted": generation_quality.get("accepted"),
                        "review_required": generation_quality.get("review_required"),
                        "validation_failed": generation_quality.get("validation_failed"),
                        "generation_failed": generation_quality.get("generation_failed"),
                        "persistence_failed": generation_quality.get("persistence_failed"),
                        "accepted_rate": generation_quality.get("accepted_rate"),
                        "review_required_rate": generation_quality.get("review_required_rate"),
                        "failure_rate": _safe_rate(
                            int(generation_quality.get("validation_failed") or 0)
                            + int(generation_quality.get("generation_failed") or 0)
                            + int(generation_quality.get("persistence_failed") or 0),
                            int(generation_quality.get("total_attempted") or 0),
                        ),
                    },
                    "analysis_to_generation_conversion": {
                        "ready_for_generation": analysis_quality.get("ready_for_generation"),
                        "generation_attempted": generation_quality.get("total_attempted"),
                        "conversion_rate": _safe_rate(
                            int(generation_quality.get("total_attempted") or 0),
                            int(analysis_quality.get("ready_for_generation") or 0),
                        ),
                    },
                    "retry_counts": {
                        "total_retry_count": total_retry_count,
                        "attempted_jobs": generation_quality.get("total_attempted"),
                    },
                },
                "late_stage_reuse_metrics": late_stage_reuse_metrics,
            }
            for export_row in summary["export_results"]:
                fact = export_row.get("job_outcome")
                if not isinstance(fact, dict):
                    continue
                reference = job_outcome_event_reference(fact)
                reporter.emit(
                    JOB_OUTCOME_EVENT_STAGE,
                    "info",
                    (
                        f"{reference['job_key']} {reference['outcome']} "
                        f"at {reference['stage']}: {reference['reason_code']}"
                    ),
                    reference,
                )
            reporter.emit(
                "pipeline_compute_complete",
                "info",
                (
                    "Pipeline compute complete: "
                    f"ranked={summary['ranked']}, "
                    f"attempted={generation_quality.get('total_attempted')}, "
                    f"accepted={generation_quality.get('accepted')}, "
                    f"review_required={generation_quality.get('review_required')}, "
                    f"failed={int(generation_quality.get('validation_failed') or 0) + int(generation_quality.get('generation_failed') or 0) + int(generation_quality.get('persistence_failed') or 0)}, "
                    f"retries={total_retry_count}"
                ),
                _bounded_event_payload(
                    event_name="pipeline_compute_complete",
                    event_family="summary",
                    source_stage="cv_generation",
                    event_status="completed",
                    input_snapshot={
                        "total_jobs": summary["total_jobs"],
                        "passed_filter": summary["passed_filter"],
                        "ranked": summary["ranked"],
                    },
                    output_snapshot={
                        "cvs_generated": summary["cvs_generated"],
                        "quality_summary": event_summary["quality_summary"],
                    },
                ),
            )  # type: ignore[union-attr]
            if reuse_anomaly is not None:
                reporter.emit(
                    "reuse_anomaly",
                    "warning",
                    "Reuse anomaly detected: overlap present but reuse under floor",
                    _bounded_event_payload(
                        event_name="reuse_anomaly",
                        event_family="diagnostic",
                        source_stage="cv_generation",
                        event_status="warning",
                        output_snapshot=reuse_anomaly,
                    ),
                )  # type: ignore[union-attr]
    return summary

















