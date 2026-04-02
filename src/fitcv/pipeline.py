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
v1 embeds only rule-passing jobs (cheaper, faster).  A future
config["pipeline"]["embed_scope"] key (filtered_only | all_enriched_jobs)
can make this configurable without code changes.
"""

import logging
import uuid
from typing import Any, Callable

from fitcv.ai_score import run_ai_scoring
from fitcv.candidate import (
    flatten_skills,
    load_candidate_to_bigquery,
    load_profile_json_text,
    load_profile_yaml,
)
from fitcv.config import load_config
from fitcv.cv_generator import generate_cv
from fitcv.embeddings import embed_and_store_candidate, embed_and_store_jobs
from fitcv.enrich import (
    enrich_batch,
    get_enrich_prompt_provenance,
    load_run_structured_jobs,
    load_structured_jobs,
)
from fitcv.evidence import retrieve_evidence
from fitcv.gap_analysis import classify_fit, compute_gap
from fitcv.ingest import load_to_bigquery, parse_jobs_file, prepare_raw_rows
from fitcv.normalize import normalize_batch, normalize_batch_with_exclusions
from fitcv.ranking import (
    compute_final_score,
    compute_must_have_match,
    compute_preference_fit,
    compute_seniority_fit,
    compute_title_relevance,
    get_active_missing_value_defaults,
    get_active_ranking_weights,
    rank_jobs,
    store_final_ranking,
)
from fitcv.rule_filter import (
    apply_pre_enrichment_global_filters,
    apply_rule_filters,
    store_filter_results,
)
from fitcv.tracker import create_cv_version_record, store_cv_version
from fitcv.validator import run_all_validations
from fitcv.vector_search import run_vector_search

logger = logging.getLogger(__name__)
_REPAIRABLE_VALIDATION_FIELDS = ("grounding_violations", "skill_violations")
_EXPORT_ENRICHED_JOB_FIELDS = (
    "location_type_raw",
    "location_type",
    "seniority_raw",
    "seniority",
    "required_skills",
    "required_skills_canonical",
    "required_skill_entities",
    "preferred_skills",
    "preferred_skills_canonical",
    "preferred_skill_entities",
    "responsibilities",
    "domain_raw",
    "domain",
    "tech_stack",
    "years_experience_min",
    "years_experience_max",
    "keywords",
    "job_family_raw",
    "job_family",
    "mapping_suggestions",
    "description_cleaned",
    "enrichment_version",
    "enrichment_model",
    "enriched_at",
)
_DEDUPE_REASON_LABELS = {
    "duplicate_job_url": "duplicate_job_url",
    "near_duplicate_job_posting": "near_duplicate_job_posting",
}
_EMPTY_REPAIR_ATTEMPT = {"performed": False, "missing_sections": []}
_FIT_LABEL_ORDER = {"skip": 0, "stretch": 1, "strong": 2}
_STAGE_ARTIFACT_SAMPLE_LIMIT = 20
_STAGE_ARTIFACT_TEXT_LIMIT = 240
PIPELINE_STAGE_SEQUENCE = (
    "normalize",
    "enrich",
    "rule_filter",
    "shortlist",
    "ranking",
    "cv_generation",
)
_PIPELINE_STAGE_SET = set(PIPELINE_STAGE_SEQUENCE)


def _extract_job_url(job: dict[str, Any]) -> str:
    return str(job.get("job_url") or job.get("jobUrl") or "")


def _extract_job_title(job: dict[str, Any]) -> str:
    return str(job.get("title") or job.get("job_title") or "")


def _normalize_shortlist_row(shortlist_row: dict[str, Any]) -> dict[str, Any]:
    return {
        "vector_similarity": shortlist_row.get("vector_similarity", shortlist_row.get("similarity_score")),
        "vector_rank": shortlist_row.get("vector_rank", shortlist_row.get("rank")),
        "shortlist_origin": str(shortlist_row.get("shortlist_origin") or "vector_search"),
    }


def _unique_job_urls(rows: list[dict[str, Any]]) -> list[str]:
    urls: list[str] = []
    seen_urls: set[str] = set()
    for row in rows:
        job_url = _extract_job_url(row)
        if not job_url or job_url in seen_urls:
            continue
        seen_urls.add(job_url)
        urls.append(job_url)
    return urls


def _raw_shortlist_anomaly_urls(
    raw_shortlist: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
) -> list[str]:
    passed_job_urls = {_extract_job_url(job) for job in passed_jobs if _extract_job_url(job)}
    return [
        job_url for job_url in _unique_job_urls(raw_shortlist)
        if job_url not in passed_job_urls
    ]


def _materialize_scoring_shortlist(
    raw_shortlist: list[dict[str, Any]],
    passed_jobs: list[dict[str, Any]],
    vector_search_top_n: int,
) -> list[dict[str, Any]]:
    """Build the shortlist used for AI scoring from raw vector-search rows.

    VECTOR_SEARCH returns only `job_url` + similarity/rank, but downstream
    scoring needs the full structured JD fields. We therefore merge raw vector
    rows back onto the corresponding passed jobs.

    We also backfill any passed jobs missing from the raw shortlist while
    capacity remains. This protects against transient read-after-write gaps in
    BigQuery job embeddings visibility without losing the fact that retrieval
    itself missed the job URL.
    """
    passed_by_url = {
        _extract_job_url(job): job
        for job in passed_jobs
        if _extract_job_url(job)
    }
    scoring_shortlist: list[dict[str, Any]] = []
    seen_urls: set[str] = set()

    for row in raw_shortlist:
        job_url = _extract_job_url(row)
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
                **_normalize_shortlist_row(row),
                "vector_rank": len(scoring_shortlist) + 1,
                "shortlist_origin": "vector_search",
            }
        )

    next_rank = len(scoring_shortlist) + 1
    for job in passed_jobs:
        if len(scoring_shortlist) >= vector_search_top_n:
            break
        job_url = _extract_job_url(job)
        if not job_url or job_url in seen_urls:
            continue
        seen_urls.add(job_url)
        scoring_shortlist.append(
            {
                **job,
                "job_url": job_url,
                "vector_similarity": 0.0,
                "vector_rank": next_rank,
                "shortlist_origin": "backfill",
            }
        )
        next_rank += 1

    return scoring_shortlist


def _merge_ranked_job_with_enriched_context(
    ranked_job: dict[str, Any],
    enriched_by_url: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    job_url = _extract_job_url(ranked_job)
    enriched_job = enriched_by_url.get(job_url, {})
    if not enriched_job:
        return dict(ranked_job)
    return {
        **enriched_job,
        **ranked_job,
    }


def _build_export_enriched_job(enriched_job: dict[str, Any] | None) -> dict[str, Any] | None:
    if not enriched_job:
        return None
    return {
        key: enriched_job[key]
        for key in _EXPORT_ENRICHED_JOB_FIELDS
        if key in enriched_job
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
    cv_results: list[dict[str, Any]],
    cv_generation_debug_records: list[dict[str, Any]],
    vector_search_top_n: int,
) -> list[dict[str, Any]]:
    original_by_url = {_extract_job_url(job): job for job in raw_jobs if _extract_job_url(job)}
    enriched_by_url = {_extract_job_url(job): job for job in enriched if _extract_job_url(job)}
    passed_by_url = {_extract_job_url(job): job for job in passed_jobs if _extract_job_url(job)}
    raw_shortlist_by_url = {
        _extract_job_url(job): _normalize_shortlist_row(job)
        for job in raw_shortlist
        if _extract_job_url(job)
    }
    scoring_shortlist_by_url = {
        _extract_job_url(job): _normalize_shortlist_row(job)
        for job in shortlist_for_scoring
        if _extract_job_url(job)
    }
    scoring_by_url = {_extract_job_url(job): job for job in ranking_inputs if _extract_job_url(job)}
    ranked_by_url = {_extract_job_url(job): job for job in ranked if _extract_job_url(job)}
    cv_by_url = {str(item["job_url"]): item for item in cv_results if item.get("job_url")}
    passed_job_urls = set(passed_by_url)
    debug_by_url = {
        str(record.get("job_url") or ""): record
        for record in cv_generation_debug_records
        if str(record.get("job_url") or "")
    }
    skipped_fit_gate_urls = {
        str(record.get("job_url") or "")
        for record in cv_generation_debug_records
        if str(record.get("status") or "") == "skipped_fit_gate" and str(record.get("job_url") or "")
    }
    deduplicated_by_input_index = {
        int(job.get("input_index", -1)): job
        for job in deduplicated_jobs
        if job.get("input_index") is not None
    }

    reject_reasons_by_url: dict[str, list[str]] = {}
    rejected_before_enrichment_urls: set[str] = set()
    rejected_after_enrichment_urls: set[str] = set()
    for rejected in pre_filter_rejected:
        job_url = str(rejected.get("job_url") or "")
        if not job_url:
            continue
        reject_reasons_by_url[job_url] = list(rejected.get("reasons") or [])
        rejected_before_enrichment_urls.add(job_url)
    for rejected in candidate_filter_rejected:
        job_url = str(rejected.get("job_url") or "")
        if not job_url:
            continue
        reject_reasons_by_url[job_url] = list(rejected.get("reasons") or [])
        rejected_after_enrichment_urls.add(job_url)

    def _status_for(job_url: str) -> str:
        if job_url in cv_by_url:
            return "ranked_with_cv"
        if job_url in skipped_fit_gate_urls:
            return "ranked_skipped_fit_gate"
        if job_url in ranked_by_url:
            return "ranked_no_cv"
        if job_url in rejected_before_enrichment_urls:
            return "rejected_before_enrichment"
        if job_url in rejected_after_enrichment_urls:
            return "rejected_after_enrichment"
        if job_url in scoring_by_url:
            return "scored_not_ranked"
        if job_url in scoring_shortlist_by_url:
            return "shortlisted_not_scored"
        if job_url in passed_by_url:
            return "not_shortlisted"
        return "unknown_pipeline_state"

    def _sort_key(row: dict[str, Any]) -> tuple[int, float, float, float, int, int]:
        status = str(row["pipeline_status"])
        category = {
            "ranked_with_cv": 0,
            "ranked_skipped_fit_gate": 1,
            "ranked_no_cv": 2,
            "not_shortlisted": 3,
            "shortlisted_not_scored": 4,
            "scored_not_ranked": 5,
            "rejected_after_enrichment": 6,
            "rejected_before_enrichment": 7,
            "deduplicated_before_enrichment": 8,
            "unknown_pipeline_state": 9,
        }.get(status, 10)
        scores = dict(row.get("scores") or {})
        final_score = float(scores.get("final_score") or 0.0)
        ai_score = float(scores.get("ai_score") or 0.0)
        vector_score = float(scores.get("vector_score") or 0.0)
        rank = int(row.get("rank") or 0) or 999999
        input_index = int(row.get("_input_index") or 0)
        return (category, -final_score, -ai_score, -vector_score, rank, input_index)

    rows: list[dict[str, Any]] = []
    for input_index, raw_job in enumerate(raw_jobs):
        job_url = _extract_job_url(raw_job)
        original_job = raw_job
        enriched_job = enriched_by_url.get(job_url)
        deduplicated_job = deduplicated_by_input_index.get(input_index)
        score_source = {
            **scoring_shortlist_by_url.get(job_url, {}),
            **scoring_by_url.get(job_url, {}),
            **ranked_by_url.get(job_url, {}),
        }
        cv_row = cv_by_url.get(job_url)
        cv_payload = None
        if cv_row is not None:
            cv_payload = {
                "version_id": cv_row.get("cv_version_id"),
                "ranking_fit_label": cv_row.get("ranking_fit_label") or cv_row.get("fit_classification"),
                "fit_classification": cv_row.get("fit_classification"),
                "model_used": cv_row.get("cv_generation_model"),
                "prompt_version": cv_row.get("cv_prompt_version"),
                "schema_version": (
                    cv_row.get("structured_cv", {}) or {}
                ).get("schema_version") if isinstance(cv_row.get("structured_cv"), dict) else None,
                "structured": cv_row.get("structured_cv"),
                "markdown": cv_row.get("cv_markdown"),
                "created_at": cv_row.get("generated_at"),
            }
        pipeline_status = _status_for(job_url)
        reject_reasons = reject_reasons_by_url.get(job_url, [])
        if deduplicated_job is not None:
            pipeline_status = "deduplicated_before_enrichment"
            reject_reasons = [
                _DEDUPE_REASON_LABELS.get(str(deduplicated_job.get("dedupe_reason") or ""), "deduplicated_before_enrichment")
            ]
            score_source = {}

        raw_shortlist_row = raw_shortlist_by_url.get(job_url)
        scoring_shortlist_row = scoring_shortlist_by_url.get(job_url)
        shortlist_debug = None
        if job_url in passed_by_url:
            shortlist_status = _shortlist_status_for_export_row(
                job_url=job_url,
                passed_job_urls=passed_job_urls,
                raw_shortlist_row=raw_shortlist_row,
                scoring_shortlist_row=scoring_shortlist_row,
            )
            shortlist_debug = {
                "passed_rule_filter": True,
                "returned_by_vector_search": raw_shortlist_row is not None,
                "reason": (
                    None
                    if raw_shortlist_row is not None
                    else "job_url_not_returned_in_raw_hits"
                ),
                "vector_search_top_n": vector_search_top_n,
                "vector_rank": raw_shortlist_row.get("vector_rank") if raw_shortlist_row is not None else None,
                "vector_similarity": raw_shortlist_row.get("vector_similarity") if raw_shortlist_row is not None else None,
                "shortlist_origin": shortlist_status,
            }
        else:
            shortlist_status = "not_applicable"

        ranking_fit_label = str(score_source.get("fit_label") or "").strip() or None
        ranking_fit_source = str(score_source.get("fit_label_source") or "").strip() or None
        if ranking_fit_label is not None and ranking_fit_source is None:
            ranking_fit_source = "reranker"
        debug_row = debug_by_url.get(job_url)
        if debug_row is not None:
            cv_status = str(debug_row.get("status") or "not_attempted")
        elif job_url in ranked_by_url:
            cv_status = "not_attempted"
        else:
            cv_status = "not_applicable"
        decision_chain = _build_decision_chain(
            shortlist_status=shortlist_status,
            advanced_to_scoring=job_url in scoring_shortlist_by_url,
            ranking_fit_label=ranking_fit_label,
            ranking_fit_source=ranking_fit_source,
            cv_status=cv_status,
        )

        rows.append(
            {
                "job_url": job_url,
                "job_title": _extract_job_title(enriched_job or original_job or {}),
                "company": (enriched_job or original_job or {}).get("company_name")
                or (enriched_job or original_job or {}).get("companyName"),
                "location_type": (enriched_job or {}).get("location_type"),
                "domain": (enriched_job or {}).get("domain"),
                "original_job": original_job,
                "enriched_job": _build_export_enriched_job(enriched_job),
                "pipeline_status": pipeline_status,
                "reject_reasons": reject_reasons,
                "scores": {
                    "final_score": score_source.get("final_score"),
                    "ai_score": score_source.get("ai_score"),
                    "vector_score": score_source.get("vector_similarity"),
                    "fit_label": score_source.get("fit_label"),
                },
                "decision_chain": decision_chain,
                "shortlist_debug": shortlist_debug,
                "rank": score_source.get("final_rank"),
                "cv": cv_payload,
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


def _json_safe_pipeline_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe_pipeline_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe_pipeline_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_pipeline_value(item) for item in value]
    if isinstance(value, set):
        return [_json_safe_pipeline_value(item) for item in sorted(value)]
    return value


def _empty_pipeline_state(run_id: str) -> dict[str, Any]:
    return {
        "run_id": run_id,
        "raw_jobs": [],
        "normalized": [],
        "deduplicated_jobs": [],
        "pre_filter_rejected_jobs": [],
        "enriched": [],
        "passed_jobs": [],
        "candidate_filter_rejected_jobs": [],
        "raw_shortlist": [],
        "shortlist": [],
        "backfilled_job_urls": [],
        "ai_scores": [],
        "ranking_inputs": [],
        "ranked": [],
        "cv_results": [],
        "cv_generation_debug_records": [],
    }


def _restore_pipeline_state(
    *,
    run_id: str,
    checkpoint_payload: dict[str, Any] | None,
) -> dict[str, Any]:
    state = _empty_pipeline_state(run_id)
    payload = checkpoint_payload or {}
    for key in state:
        if key == "run_id":
            continue
        value = payload.get(key)
        if isinstance(state[key], list):
            state[key] = list(value or [])
        elif value is not None:
            state[key] = value
    return state


def _checkpoint_payload_from_state(state: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "raw_jobs",
        "normalized",
        "deduplicated_jobs",
        "pre_filter_rejected_jobs",
        "enriched",
        "passed_jobs",
        "candidate_filter_rejected_jobs",
        "raw_shortlist",
        "shortlist",
        "backfilled_job_urls",
        "ai_scores",
        "ranking_inputs",
        "ranked",
    )
    return {
        key: _json_safe_pipeline_value(state.get(key) or [])
        for key in keys
    }


def _collect_mapping_suggestions(enriched: list[dict[str, Any]], run_id: str) -> list[dict[str, Any]]:
    suggestions: list[dict[str, Any]] = []
    for job in enriched:
        job_url = _extract_job_url(job)
        job_title = _extract_job_title(job)
        for suggestion in list(job.get("mapping_suggestions") or []):
            if not isinstance(suggestion, dict):
                continue
            record = {
                "run_id": run_id,
                "job_url": job_url,
                "job_title": job_title,
                "must_have_skill": str(suggestion.get("must_have_skill") or ""),
                "matches": bool(suggestion.get("matches")),
                "confidence": float(suggestion.get("confidence") or 0.0),
                "alias": str(suggestion.get("alias") or ""),
                "canonical": str(suggestion.get("canonical") or ""),
            }
            if record["alias"] and record["canonical"]:
                suggestions.append(record)
    return suggestions


def _build_checkpoint_summary(
    *,
    run_id: str,
    paused_after_stage: str,
    state: dict[str, Any],
    profile: dict[str, Any] | None,
    config: dict[str, Any],
    vector_top_n: int | None = None,
    candidate_summary: str | None = None,
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
    backfilled_job_urls = list(state.get("backfilled_job_urls") or [])
    ai_scores = list(state.get("ai_scores") or [])
    ranking_inputs = list(state.get("ranking_inputs") or [])
    ranked = list(state.get("ranked") or [])
    cv_generation_debug_records = list(state.get("cv_generation_debug_records") or [])
    cv_results = list(state.get("cv_results") or [])
    candidate_profile = profile or {"preferences": {}}
    vector_top_n_value = int(
        vector_top_n if vector_top_n is not None else config.get("pipeline", {}).get("vector_search_top_n", 0)
    )
    final_top_n_value = int(
        final_top_n if final_top_n is not None else config.get("pipeline", {}).get("final_top_n", 0)
    )
    candidate_summary_value = str(candidate_summary or "")
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
        backfilled_job_urls=backfilled_job_urls,
        vector_top_n=vector_top_n_value,
        candidate_summary=candidate_summary_value,
        ai_scores=ai_scores,
        ranking_inputs=ranking_inputs,
        ranked=ranked,
        final_top_n=final_top_n_value,
        cv_generation_debug_records=cv_generation_debug_records,
        profile=candidate_profile,
        config=config,
    )
    return {
        "run_id": run_id,
        "paused_after_stage": paused_after_stage,
        "completed_stages": completed_pipeline_stages_through(paused_after_stage),
        "next_stage": next_pipeline_stage(paused_after_stage),
        "total_jobs": len(raw_jobs),
        "passed_filter": len(passed_jobs),
        "ranked": len(ranked),
        "cvs_generated": len(cv_results),
        "checkpoint_payload": _checkpoint_payload_from_state(state),
        "mapping_suggestions": _collect_mapping_suggestions(enriched, run_id),
        "stage_transition_artifacts": stage_transition_artifacts,
    }


# ── helpers ───────────────────────────────────────────────────────────────────

def create_run_id() -> str:
    """Return a new UUID4 string to identify this pipeline run."""
    return str(uuid.uuid4())


def _should_retry_missing_sections(validation: dict[str, Any]) -> bool:
    missing_sections = list(validation.get("missing_sections") or [])
    if not missing_sections:
        return False
    return all(not validation.get(field) for field in _REPAIRABLE_VALIDATION_FIELDS)


def _unwrap_generated_cv(generated_cv: Any) -> tuple[dict[str, Any] | None, str]:
    if isinstance(generated_cv, dict):
        markdown = str(generated_cv.get("markdown") or "")
        structured_cv = generated_cv.get("structured_cv")
        if isinstance(structured_cv, dict):
            return structured_cv, markdown
        return None, markdown
    return None, str(generated_cv)


def _build_debug_evidence_used(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    debug_evidence: list[dict[str, Any]] = []
    for item in evidence:
        debug_evidence.append(
            {
                "evidence_type": str(item.get("evidence_type") or ""),
                "source_ref": str(item.get("source_ref") or ""),
                "name": str(item.get("name") or ""),
            }
        )
    return debug_evidence


def _build_validation_snapshot(validation: dict[str, Any] | None) -> dict[str, Any] | None:
    if validation is None:
        return None
    return {
        "valid": bool(validation.get("valid")),
        "missing_sections": list(validation.get("missing_sections") or []),
        "grounding_violations": list(validation.get("grounding_violations") or []),
        "skill_violations": list(validation.get("skill_violations") or []),
        "warnings": list(validation.get("warnings") or []),
    }


def _build_repair_attempt(missing_sections: list[str] | None = None) -> dict[str, Any]:
    return {
        "performed": bool(missing_sections),
        "missing_sections": list(missing_sections or []),
    }


def _fit_label_from_ai_score(score: float, config: dict[str, Any]) -> str:
    thresholds = dict(config.get("fit_label_thresholds") or {})
    strong_threshold = float(thresholds.get("strong", 0.70))
    stretch_threshold = float(thresholds.get("stretch", 0.40))
    if score >= strong_threshold:
        return "strong"
    if score >= stretch_threshold:
        return "stretch"
    return "skip"


def _resolve_layer4_fit(
    job: dict[str, Any],
    gap_fit: str | None,
    config: dict[str, Any],
) -> str:
    """Return the authoritative post-filter fit label for a ranked job."""
    del gap_fit
    ranked_fit_raw = str(job.get("fit_label") or "").strip().lower()
    ranked_fit = ranked_fit_raw if ranked_fit_raw in _FIT_LABEL_ORDER else None
    if ranked_fit is not None:
        return ranked_fit
    raw_ai_score = job.get("ai_score")
    if raw_ai_score is None:
        return "skip"
    return _fit_label_from_ai_score(float(raw_ai_score), config)


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
    if scoring_shortlist_row is not None and str(scoring_shortlist_row.get("shortlist_origin") or "") == "backfill":
        return "backfilled_for_scoring"
    if scoring_shortlist_row is not None:
        return "advanced_to_scoring"
    return "not_returned_in_raw_hits"


def _shortlist_status_for_ranked_job(job: dict[str, Any]) -> str:
    shortlist_origin = str(job.get("shortlist_origin") or "").strip().lower()
    if shortlist_origin == "backfill":
        return "backfilled_for_scoring"
    return "returned_by_vector_search"


def _validation_status_for_cv_status(status: str) -> str:
    if status == "accepted":
        return "accepted"
    if status == "validation_failed":
        return "failed"
    if status == "persistence_failed":
        return "accepted"
    return "not_run"


def _build_decision_chain(
    *,
    shortlist_status: str,
    advanced_to_scoring: bool,
    ranking_fit_label: str | None,
    ranking_fit_source: str | None,
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
    job: dict[str, Any],
    status: str,
    fit_classification: str | None,
    evidence_used: list[dict[str, Any]],
    gap_summary: dict[str, Any] | None,
    structured_cv_initial: dict[str, Any] | None,
    validation_initial: dict[str, Any] | None,
    repair_attempt: dict[str, Any],
    structured_cv_final: dict[str, Any] | None,
    markdown_final: str | None,
    error: dict[str, str] | None,
) -> dict[str, Any]:
    ranking_fit_label = str(fit_classification or "").strip() or None
    ranking_fit_source = str(job.get("fit_label_source") or "reranker").strip() or None
    decision_chain = _build_decision_chain(
        shortlist_status=_shortlist_status_for_ranked_job(job),
        advanced_to_scoring=True,
        ranking_fit_label=ranking_fit_label,
        ranking_fit_source=ranking_fit_source,
        cv_status=status,
    )
    return {
        "job_url": str(job.get("job_url") or ""),
        "job_title": _extract_job_title(job),
        "status": status,
        "ranking_fit_label": ranking_fit_label,
        "fit_classification": fit_classification,
        "decision_chain": decision_chain,
        "evidence_used": evidence_used,
        "gap_summary": gap_summary,
        "structured_cv_initial": structured_cv_initial,
        "validation_initial": validation_initial,
        "repair_attempt": repair_attempt,
        "structured_cv_final": structured_cv_final,
        "markdown_final": markdown_final,
        "error": error,
    }


def _stage_block_not_reached(stage: str) -> dict[str, Any]:
    return {
        "stage_id": stage,
        "stage": stage,
        "status": "not_reached",
        "input_counts": {},
        "output_counts": {},
        "decision_summary": {},
        "inputs_sample": [],
        "outputs_sample": [],
        "dropped_or_changed_sample": [],
    }


def _truncate_stage_text(value: str, *, limit: int = _STAGE_ARTIFACT_TEXT_LIMIT) -> str:
    if len(value) <= limit:
        return value
    return value[:limit] + "...[truncated]"


def _truncate_stage_value(value: Any) -> Any:
    if isinstance(value, str):
        return _truncate_stage_text(value)
    if isinstance(value, list):
        return [_truncate_stage_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _truncate_stage_value(inner)
            for key, inner in value.items()
        }
    return value


def _sample_rows(
    rows: list[Any],
    row_builder: Callable[[Any], dict[str, Any] | None],
    *,
    limit: int = _STAGE_ARTIFACT_SAMPLE_LIMIT,
) -> list[dict[str, Any]]:
    sampled: list[dict[str, Any]] = []
    for row in rows:
        built = row_builder(row)
        if not built:
            continue
        sampled.append(_truncate_stage_value(built))
        if len(sampled) >= limit:
            break
    return sampled


def _sample_strings(values: list[str], *, limit: int = _STAGE_ARTIFACT_SAMPLE_LIMIT) -> list[str]:
    return [_truncate_stage_text(value) for value in values[:limit] if value]


def _job_sample(job: dict[str, Any]) -> dict[str, Any] | None:
    job_url = _extract_job_url(job)
    if not job_url:
        return None
    sample = {
        "job_url": job_url,
        "job_title": _extract_job_title(job),
        "company": str(job.get("company_name") or job.get("companyName") or ""),
    }
    optional_fields: dict[str, Any] = {}
    for field in _EXPORT_ENRICHED_JOB_FIELDS:
        value = job.get(field)
        optional_fields[field] = value
    for key, value in optional_fields.items():
        if value not in (None, "", []):
            sample[key] = value
    return sample


def _candidate_profile_summary(profile: dict[str, Any]) -> dict[str, Any]:
    preferences = dict(profile.get("preferences") or {})
    flattened_skills = flatten_skills(profile)
    summary = {
        "target_role": str(preferences.get("target_role") or ""),
        "years_experience": profile.get("years_experience"),
        "skills_sample": flattened_skills[:5],
    }
    return {key: value for key, value in summary.items() if value not in (None, "", [])}


def _shortlist_row_sample(row: dict[str, Any]) -> dict[str, Any] | None:
    job_url = _extract_job_url(row)
    if not job_url:
        return None
    sample = {
        "job_url": job_url,
        "job_title": _extract_job_title(row),
        "vector_similarity": row.get("vector_similarity", row.get("similarity_score")),
        "vector_rank": row.get("vector_rank", row.get("rank")),
        "shortlist_origin": str(row.get("shortlist_origin") or "vector_search"),
    }
    return {key: value for key, value in sample.items() if value not in (None, "")}


def _ranking_row_sample(row: dict[str, Any]) -> dict[str, Any] | None:
    job_url = _extract_job_url(row)
    if not job_url:
        return None
    sample = {
        "job_url": job_url,
        "job_title": _extract_job_title(row),
        "ai_score": row.get("ai_score"),
        "must_have_match": row.get("must_have_match"),
        "vector_similarity": row.get("vector_similarity"),
        "title_relevance": row.get("title_relevance"),
        "seniority_fit": row.get("seniority_fit"),
        "preference_fit": row.get("preference_fit"),
        "final_score": row.get("final_score"),
        "ranking_fit_label": row.get("fit_label"),
        "shortlist_origin": row.get("shortlist_origin"),
    }
    return {key: value for key, value in sample.items() if value not in (None, "")}


def _debug_record_output_sample(record: dict[str, Any]) -> dict[str, Any] | None:
    status = str(record.get("status") or "")
    if status not in {"accepted", "persistence_failed"}:
        return None
    job_url = str(record.get("job_url") or "")
    if not job_url:
        return None
    sample = {
        "job_url": job_url,
        "job_title": str(record.get("job_title") or ""),
        "status": status,
        "ranking_fit_label": record.get("ranking_fit_label"),
        "fit_classification": record.get("fit_classification"),
        "validation_initial": record.get("validation_initial"),
        "repair_attempt": record.get("repair_attempt"),
        "markdown_final": record.get("markdown_final"),
    }
    return {key: value for key, value in sample.items() if value not in (None, "", [])}


def _debug_record_changed_sample(record: dict[str, Any]) -> dict[str, Any] | None:
    status = str(record.get("status") or "")
    if status in {"accepted", "persistence_failed"}:
        return None
    job_url = str(record.get("job_url") or "")
    if not job_url:
        return None
    sample = {
        "job_url": job_url,
        "job_title": str(record.get("job_title") or ""),
        "change_type": status,
        "ranking_fit_label": record.get("ranking_fit_label"),
        "validation_initial": record.get("validation_initial"),
        "repair_attempt": record.get("repair_attempt"),
        "error": record.get("error"),
    }
    return {key: value for key, value in sample.items() if value not in (None, "", [])}


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
) -> dict[str, Any]:
    block = {
        "stage_id": stage_id,
        "stage": stage_id,
        "status": status,
        "input_counts": input_counts,
        "output_counts": output_counts,
        "decision_summary": decision_summary,
        "inputs_sample": inputs_sample,
        "outputs_sample": outputs_sample,
        "dropped_or_changed_sample": dropped_or_changed_sample,
    }
    if settings_refs:
        block["settings_refs"] = settings_refs
    return _truncate_stage_value(block)


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
    backfilled_job_urls: list[str],
    vector_top_n: int,
    candidate_summary: str,
    ai_scores: list[dict[str, Any]],
    ranking_inputs: list[dict[str, Any]],
    ranked: list[dict[str, Any]],
    final_top_n: int,
    cv_generation_debug_records: list[dict[str, Any]],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    shortlist_reached = len(passed_jobs) > 0
    ranking_reached = shortlist_reached and (len(shortlist) > 0 or len(ai_scores) > 0 or len(ranking_inputs) > 0)
    cv_generation_reached = len(ranked) > 0 or len(cv_generation_debug_records) > 0
    raw_shortlist_urls = set(_unique_job_urls(raw_shortlist))
    raw_shortlist_anomaly_urls = _raw_shortlist_anomaly_urls(raw_shortlist, passed_jobs)
    ranked_urls = {_extract_job_url(job) for job in ranked if _extract_job_url(job)}
    dedupe_reason_counts: dict[str, int] = {}
    for job in deduplicated_jobs:
        reason = _DEDUPE_REASON_LABELS.get(str(job.get("dedupe_reason") or ""), "deduplicated")
        dedupe_reason_counts[reason] = dedupe_reason_counts.get(reason, 0) + 1
    grouped_reject_reasons: dict[str, int] = {}
    for rejected in candidate_filter_rejected_jobs:
        for reason in list(rejected.get("reasons") or []):
            grouped_reject_reasons[str(reason)] = grouped_reject_reasons.get(str(reason), 0) + 1
    ranking_fit_distribution: dict[str, int] = {}
    for row in ranking_inputs:
        fit_label = str(row.get("fit_label") or "")
        if fit_label:
            ranking_fit_distribution[fit_label] = ranking_fit_distribution.get(fit_label, 0) + 1
    ranking_weights = get_active_ranking_weights(config)
    ranking_defaults = get_active_missing_value_defaults(config)
    zero_weight_features = [
        feature_name
        for feature_name, weight in ranking_weights.items()
        if float(weight) == 0.0
    ]
    contributing_features = [
        feature_name
        for feature_name, weight in ranking_weights.items()
        if float(weight) > 0.0
    ]
    cv_status_counts = {
        "ranked_jobs_total": len(ranked),
        "debug_records_captured": len(cv_generation_debug_records),
        "accepted_count": 0,
        "skipped_fit_gate_count": 0,
        "validation_failed_count": 0,
        "generation_failed_count": 0,
        "persistence_failed_count": 0,
    }
    for record in cv_generation_debug_records:
        status = str(record.get("status") or "")
        if status == "accepted":
            cv_status_counts["accepted_count"] += 1
        elif status == "skipped_fit_gate":
            cv_status_counts["skipped_fit_gate_count"] += 1
        elif status == "validation_failed":
            cv_status_counts["validation_failed_count"] += 1
        elif status == "generation_failed":
            cv_status_counts["generation_failed_count"] += 1
        elif status == "persistence_failed":
            cv_status_counts["persistence_failed_count"] += 1
    enrich_prompt_provenance = get_enrich_prompt_provenance(config)

    return {
        "schema_version": "stage_transition_artifacts_v3",
        "stages": {
            "normalize": _stage_block(
                stage_id="normalize",
                status="completed",
                input_counts={"raw_jobs": len(raw_jobs)},
                output_counts={
                    "normalized_jobs": len(normalized),
                    "deduplicated_jobs": len(deduplicated_jobs),
                },
                decision_summary={"dedupe_reason_counts": dedupe_reason_counts},
                inputs_sample=_sample_rows(raw_jobs, _job_sample),
                outputs_sample=_sample_rows(normalized, _job_sample),
                dropped_or_changed_sample=_sample_rows(
                    deduplicated_jobs,
                    lambda job: {
                        **(_job_sample(job) or {}),
                        "change_type": "deduplicated_before_enrichment",
                        "dedupe_reason": _DEDUPE_REASON_LABELS.get(str(job.get("dedupe_reason") or ""), "deduplicated"),
                    } if _job_sample(job) else None,
                ),
            ),
            "enrich": _stage_block(
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
                    "candidate_profile_summary": _candidate_profile_summary(profile),
                    "enrich_prompt_id": enrich_prompt_provenance["prompt_id"],
                    "enrich_prompt_version": enrich_prompt_provenance["prompt_version"],
                    "enrich_prompt_template_path": enrich_prompt_provenance["template_path"],
                    "enrich_prompt_model": enrich_prompt_provenance["model"],
                },
                inputs_sample=_sample_rows(
                    [job for job in normalized if _extract_job_url(job) not in {_extract_job_url(item) for item in pre_filter_rejected_jobs}],
                    _job_sample,
                ),
                outputs_sample=_sample_rows(enriched, _job_sample),
                dropped_or_changed_sample=_sample_rows(
                    pre_filter_rejected_jobs,
                    lambda job: {
                        **(_job_sample(job) or {}),
                        "change_type": "rejected_before_enrichment",
                        "reasons": list(job.get("reasons") or []),
                    } if _job_sample(job) else None,
                ),
            ),
            "rule_filter": _stage_block(
                stage_id="rule_filter",
                status="completed",
                input_counts={"enriched_jobs": len(enriched)},
                output_counts={
                    "passed_jobs": len(passed_jobs),
                    "rejected_jobs": len(candidate_filter_rejected_jobs),
                },
                decision_summary={
                    "reject_reason_counts": grouped_reject_reasons,
                },
                inputs_sample=_sample_rows(enriched, _job_sample),
                outputs_sample=_sample_rows(passed_jobs, _job_sample),
                dropped_or_changed_sample=_sample_rows(
                    candidate_filter_rejected_jobs,
                    lambda job: {
                        **(_job_sample(job) or {}),
                        "change_type": "rejected_after_enrichment",
                        "reasons": list(job.get("reasons") or []),
                    } if _job_sample(job) else None,
                ),
            ),
            "shortlist": _stage_block(
                stage_id="shortlist",
                status="completed" if shortlist_reached else "not_reached",
                input_counts={"passed_jobs": len(passed_jobs)},
                output_counts={
                    "raw_vector_rows": len(raw_shortlist),
                    "raw_vector_hits": len(raw_shortlist_urls),
                    "scoring_shortlist_jobs": len(shortlist),
                    "backfilled_jobs": len(backfilled_job_urls),
                    "retrieval_anomalies": len(raw_shortlist_anomaly_urls),
                },
                decision_summary={
                    "candidate_query_text": candidate_summary,
                    "vector_search_top_n": vector_top_n,
                    "jobs_not_returned_in_raw_hits": len(
                        [job for job in passed_jobs if _extract_job_url(job) not in raw_shortlist_urls]
                    ),
                },
                inputs_sample=_sample_rows(passed_jobs, _job_sample),
                outputs_sample=_sample_rows(shortlist, _shortlist_row_sample),
                dropped_or_changed_sample=_sample_rows(
                    [
                        *[
                            {
                                **job,
                                "change_type": "missed_by_vector_search",
                            }
                            for job in passed_jobs
                            if _extract_job_url(job) not in raw_shortlist_urls
                        ],
                        *[
                            {
                                "job_url": job_url,
                                "title": next(
                                    (_extract_job_title(job) for job in passed_jobs if _extract_job_url(job) == job_url),
                                    "",
                                ),
                                "change_type": "backfilled_for_scoring",
                            }
                            for job_url in backfilled_job_urls
                        ],
                        *[
                            {
                                "job_url": job_url,
                                "title": "",
                                "change_type": "raw_hit_excluded_from_scoring",
                            }
                            for job_url in raw_shortlist_anomaly_urls
                        ],
                    ],
                    lambda item: {
                        **(_job_sample(item) or {"job_url": str(item.get("job_url") or ""), "job_title": str(item.get("title") or "")}),
                        "change_type": str(item.get("change_type") or ""),
                    }
                    if str(item.get("job_url") or "")
                    else None,
                ),
                settings_refs=["pipeline.vector_search_top_n"],
            ) if shortlist_reached else _stage_block_not_reached("shortlist"),
            "ranking": _stage_block(
                stage_id="ranking",
                status="completed" if ranking_reached else "not_reached",
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
                    "configured_ranking_weights": ranking_weights,
                    "configured_missing_value_defaults": ranking_defaults,
                    "zero_weight_features": zero_weight_features,
                    "contributing_features": contributing_features,
                },
                inputs_sample=_sample_rows(ranking_inputs, _ranking_row_sample),
                outputs_sample=_sample_rows(ranked, _ranking_row_sample),
                dropped_or_changed_sample=_sample_rows(
                    [row for row in ranking_inputs if _extract_job_url(row) not in ranked_urls],
                    lambda row: {
                        **(_ranking_row_sample(row) or {}),
                        "change_type": "scored_not_ranked",
                    } if _ranking_row_sample(row) else None,
                ),
                settings_refs=["ranking_weights", "missing_value_defaults", "pipeline.final_top_n"],
            ) if ranking_reached else _stage_block_not_reached("ranking"),
            "cv_generation": _stage_block(
                stage_id="cv_generation",
                status="completed" if cv_generation_reached else "not_reached",
                input_counts={"ranked_jobs": len(ranked)},
                output_counts={
                    "accepted": cv_status_counts["accepted_count"],
                    "skipped_fit_gate": cv_status_counts["skipped_fit_gate_count"],
                    "validation_failed": cv_status_counts["validation_failed_count"],
                    "generation_failed": cv_status_counts["generation_failed_count"],
                    "persistence_failed": cv_status_counts["persistence_failed_count"],
                },
                decision_summary={
                    "debug_records_captured": cv_status_counts["debug_records_captured"],
                    "ranking_jobs_total": cv_status_counts["ranked_jobs_total"],
                    "cv_generation_model": str(config.get("cv", {}).get("generation", {}).get("model") or ""),
                    "cv_prompt_version": str(config.get("cv", {}).get("generation", {}).get("prompt_version") or ""),
                },
                inputs_sample=_sample_rows(ranked, _ranking_row_sample),
                outputs_sample=_sample_rows(cv_generation_debug_records, _debug_record_output_sample),
                dropped_or_changed_sample=_sample_rows(cv_generation_debug_records, _debug_record_changed_sample),
                settings_refs=["cv.generation.model", "cv.generation.prompt_version"],
            ) if cv_generation_reached else _stage_block_not_reached("cv_generation"),
        },
    }

def build_ranking_features(
    shortlist: list[dict[str, Any]],
    ai_scores: list[dict[str, Any]],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge shortlist + AI-score records into a single six-feature ranking row."""
    shortlist_index: dict[str, dict[str, Any]] = {
        row["job_url"]: row for row in shortlist
    }
    weights = get_active_ranking_weights(config)
    null_defaults = get_active_missing_value_defaults(config)
    candidate_skills = flatten_skills(profile)
    preferences = dict(profile.get("preferences") or {})

    features: list[dict[str, Any]] = []
    for ai_row in ai_scores:
        job_url = str(ai_row.get("job_url") or "")
        sl_row = shortlist_index.get(job_url)
        if sl_row is None:
            continue  # not in shortlist — skip

        vector_rank = sl_row.get("vector_rank", sl_row.get("rank"))
        raw_vector_similarity = sl_row.get("vector_similarity", sl_row.get("similarity_score"))
        vector_similarity = (
            float(raw_vector_similarity)
            if raw_vector_similarity is not None
            else null_defaults["vector_similarity"]
        )
        raw_ai_score = ai_row.get("ai_score")
        ai_score = (
            float(raw_ai_score)
            if raw_ai_score is not None
            else null_defaults["ai_score"]
        )
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
            _extract_job_title(ranking_source),
            str(preferences.get("target_role") or "") or None,
        )
        seniority_fit = compute_seniority_fit(
            str(ranking_source.get("seniority") or "") or None,
            str(preferences.get("seniority_target") or "") or None,
            config,
        )
        preference_fit = compute_preference_fit(ranking_source, preferences)

        feature: dict[str, Any] = {
            **ranking_source,
            "vector_rank": int(vector_rank or 0),
            "vector_similarity": vector_similarity,
            "ai_score": ai_score,
            "must_have_match": must_have_match,
            "title_relevance": title_relevance,
            "seniority_fit": seniority_fit,
            "preference_fit": preference_fit,
            "fit_label_source": "reranker" if ai_row.get("fit_label") is not None else "reranker_score_thresholds",
        }
        feature["final_score"] = compute_final_score(feature, weights, null_defaults)
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
) -> dict[str, Any]:
    """Run the full FitCV candidate pipeline end-to-end.

    Parameters
    ----------
    reporter:
        Optional PipelineReporter instance injected by the control-plane worker.
        When provided, stage events are emitted to pipeline_run_events in BigQuery.
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
    run_id = run_id or create_run_id()
    start_stage = _validate_pipeline_stage_name(start_stage) or PIPELINE_STAGE_SEQUENCE[0]
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
    raw_jobs = list(state["raw_jobs"])
    normalized = list(state["normalized"])
    deduplicated_jobs = list(state["deduplicated_jobs"])
    pre_filter_rejected_jobs = list(state["pre_filter_rejected_jobs"])
    enriched = list(state["enriched"])
    passed_jobs = list(state["passed_jobs"])
    candidate_filter_rejected_jobs = list(state["candidate_filter_rejected_jobs"])
    raw_shortlist = list(state["raw_shortlist"])
    shortlist = list(state["shortlist"])
    backfilled_job_urls = list(state["backfilled_job_urls"])
    ai_scores = list(state["ai_scores"])
    ranking_inputs = list(state["ranking_inputs"])
    ranked = list(state["ranked"])
    results: list[dict[str, Any]] = list(state["cv_results"])
    cv_generation_debug_records: list[dict[str, Any]] = list(state["cv_generation_debug_records"])
    profile: dict[str, Any] | None = None
    candidate_skill_names: list[str] = []
    candidate_summary = ""
    vector_top_n = int(config.get("pipeline", {}).get("vector_search_top_n", 0))
    final_top_n = int(config.get("pipeline", {}).get("final_top_n", 0))

    if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("normalize"):
        raw_jobs = parse_jobs_file(jobs_path)
        normalized = normalize_batch(raw_jobs)
        _normalized_with_exclusions, deduplicated_jobs = normalize_batch_with_exclusions(raw_jobs)
        if reporter is not None and deduplicated_jobs:
            reporter.emit(  # type: ignore[union-attr]
                "layer1_normalize",
                "info",
                f"Normalization dedupe: kept {len(normalized)} of {len(raw_jobs)} jobs, removed {len(deduplicated_jobs)} duplicate(s)",
            )

        raw_rows = prepare_raw_rows(raw_jobs)
        load_to_bigquery(raw_rows, config)
        state["raw_jobs"] = raw_jobs
        state["normalized"] = normalized
        state["deduplicated_jobs"] = deduplicated_jobs
        if stop_after_stage == "normalize":
            return _build_checkpoint_summary(
                run_id=run_id,
                paused_after_stage="normalize",
                state=state,
                profile=None,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                final_top_n=final_top_n,
            )

    normalized = list(state["normalized"])

    if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("enrich"):
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
        enriched = enrich_batch(surviving_normalized, config)
        load_structured_jobs(enriched, config)
        load_run_structured_jobs(enriched, run_id, config)
        if reporter is not None:
            reporter.emit(  # type: ignore[union-attr]
                "layer1_jobs", "info",
                f"Ingested {len(raw_jobs)} jobs, enriched {len(enriched)} (after pre-filter)",
            )
        state["pre_filter_rejected_jobs"] = pre_filter_rejected_jobs
        state["enriched"] = enriched
        if stop_after_stage == "enrich":
            return _build_checkpoint_summary(
                run_id=run_id,
                paused_after_stage="enrich",
                state=state,
                profile=None,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                final_top_n=final_top_n,
            )

    pre_filter_rejected_jobs = list(state["pre_filter_rejected_jobs"])
    enriched = list(state["enriched"])

    if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("rule_filter"):
        runtime_profile_json: str | None = (
            config.get("runtime_inputs", {}).get("candidate_profile_json")
        )
        if runtime_profile_json:
            profile = load_profile_json_text(runtime_profile_json)
        else:
            profile_path: str = str(config["paths"]["candidate_profile"])
            profile = load_profile_yaml(profile_path)
        load_candidate_to_bigquery(profile, config)
        candidate_skill_names = flatten_skills(profile)
        if reporter is not None:
            reporter.emit("layer2_candidate", "info", "Candidate profile loaded")  # type: ignore[union-attr]

        filter_result = apply_rule_filters(enriched, profile["preferences"], config)
        combined_filter_result = {
            "passed": filter_result["passed"],
            "rejected": pre_filter_rejected_jobs + filter_result["rejected"],
        }
        passed_job_urls = [str(url) for url in filter_result["passed"]]
        enriched_by_url = {
            str(job.get("job_url") or ""): job
            for job in enriched
        }
        passed_jobs = [
            enriched_by_url[url]
            for url in passed_job_urls
            if url in enriched_by_url
        ]
        candidate_filter_rejected_jobs = list(filter_result["rejected"])
        store_filter_results(combined_filter_result, run_id, config)
        if reporter is not None:
            reporter.emit("layer3_filter", "info", f"{len(passed_jobs)} passed rule filter")  # type: ignore[union-attr]
        state["passed_jobs"] = passed_jobs
        state["candidate_filter_rejected_jobs"] = candidate_filter_rejected_jobs
        if stop_after_stage == "rule_filter":
            return _build_checkpoint_summary(
                run_id=run_id,
                paused_after_stage="rule_filter",
                state=state,
                profile=profile,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                final_top_n=final_top_n,
            )
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

    if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("shortlist"):
        embed_and_store_jobs(passed_jobs, config)
        embed_and_store_candidate(profile, config)

        raw_shortlist = run_vector_search(
            profile,
            [str(job.get("job_url") or "") for job in passed_jobs],
            config,
            top_n=vector_top_n,
        )
        shortlist = _materialize_scoring_shortlist(raw_shortlist, passed_jobs, vector_top_n)
        raw_shortlist_urls = set(_unique_job_urls(raw_shortlist))
        raw_shortlist_anomaly_urls = _raw_shortlist_anomaly_urls(raw_shortlist, passed_jobs)
        backfilled_job_urls = [
            str(job.get("job_url") or "")
            for job in shortlist
            if str(job.get("job_url") or "") not in raw_shortlist_urls
        ]
        if reporter is not None:
            shortlist_message = f"Vector shortlist: {len(raw_shortlist_urls)} raw hits"
            if backfilled_job_urls:
                shortlist_message += f", {len(shortlist)} scoring jobs ({len(backfilled_job_urls)} backfilled)"
            if raw_shortlist_anomaly_urls:
                shortlist_message += f", {len(raw_shortlist_anomaly_urls)} raw-hit anomalies"
            reporter.emit("layer3_shortlist", "info", shortlist_message)  # type: ignore[union-attr]
        state["raw_shortlist"] = raw_shortlist
        state["shortlist"] = shortlist
        state["backfilled_job_urls"] = backfilled_job_urls
        if stop_after_stage == "shortlist":
            return _build_checkpoint_summary(
                run_id=run_id,
                paused_after_stage="shortlist",
                state=state,
                profile=profile,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                final_top_n=final_top_n,
            )

    raw_shortlist = list(state["raw_shortlist"])
    shortlist = list(state["shortlist"])
    backfilled_job_urls = list(state["backfilled_job_urls"])

    from fitcv.vector_search import build_candidate_query_text
    candidate_summary = build_candidate_query_text(profile, config)

    if PIPELINE_STAGE_SEQUENCE.index(start_stage) <= PIPELINE_STAGE_SEQUENCE.index("ranking"):
        ai_top_n = int(config["pipeline"]["ai_score_top_n"])
        if cancellation_check and cancellation_check():
            raise PipelineCancelled("Cancelled before AI scoring")
        ai_scores = run_ai_scoring(
            shortlist,
            candidate_summary,
            config,
            top_n=ai_top_n,
        )
        if reporter is not None:
            reporter.emit("layer3_ai_score", "info", f"AI scored: {len(ai_scores)} jobs")  # type: ignore[union-attr]

        ranking_inputs = build_ranking_features(shortlist, ai_scores, profile, config)
        ranked = rank_jobs(ranking_inputs, top_n=final_top_n)
        store_final_ranking(ranked, config)
        if reporter is not None:
            reporter.emit("layer3_ranking", "info", f"Final ranking: top {len(ranked)} jobs")  # type: ignore[union-attr]
        state["ai_scores"] = ai_scores
        state["ranking_inputs"] = ranking_inputs
        state["ranked"] = ranked
        if stop_after_stage == "ranking":
            return _build_checkpoint_summary(
                run_id=run_id,
                paused_after_stage="ranking",
                state=state,
                profile=profile,
                config=config,
                vector_top_n=vector_top_n,
                candidate_summary=candidate_summary,
                final_top_n=final_top_n,
            )

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
    if cancellation_check and cancellation_check():
        raise PipelineCancelled("Cancelled before CV generation")
    for job in ranked_jobs_for_cv:
        evidence: list[dict[str, Any]] = []
        gap: dict[str, Any] | None = None
        fit = "skip"
        structured_cv_initial: dict[str, Any] | None = None
        validation_initial: dict[str, Any] | None = None
        repair_attempt = dict(_EMPTY_REPAIR_ATTEMPT)
        structured_cv_final: dict[str, Any] | None = None
        markdown_final: str | None = None
        try:
            evidence_top_k = int(config["pipeline"]["evidence_top_k"])
            evidence = retrieve_evidence(
                profile,
                job.get("required_skills") or [],
                top_k=evidence_top_k,
            )

            gap = compute_gap(
                required_skills=job.get("required_skills") or [],
                candidate_skills=candidate_skill_names,
                years_experience_min=job.get("years_experience_min"),
                years_experience_max=job.get("years_experience_max"),
                years_candidate=profile.get("years_experience"),
                config=config,
            )

            fit = _resolve_layer4_fit(job, gap_fit=None, config=config)
            if fit == "skip":
                logger.info("[run_id=%s] Skipping job %s (fit=skip)", run_id, job.get("job_url"))
                cv_generation_debug_records.append(
                    _build_cv_generation_debug_record(
                        job=job,
                        status="skipped_fit_gate",
                        fit_classification=fit,
                        evidence_used=_build_debug_evidence_used(evidence),
                        gap_summary=gap,
                        structured_cv_initial=None,
                        validation_initial=None,
                        repair_attempt=repair_attempt,
                        structured_cv_final=None,
                        markdown_final=None,
                        error={
                            "stage": "fit_gate",
                            "message": f"Skipped {job.get('job_url')} (fit=skip)",
                        },
                    )
                )
                if reporter is not None:
                    reporter.emit("layer4_cv_skip", "info", f"Skipped {job.get('job_url')} (fit=skip)")  # type: ignore[union-attr]
                continue

            generated_cv = generate_cv(
                job,
                evidence,
                gap,
                profile,
                config,
                fit_classification=fit,
            )
            structured_cv, cv = _unwrap_generated_cv(generated_cv)
            structured_cv_initial = structured_cv
            validation = run_all_validations(
                cv,
                profile,
                config,
                structured_cv=structured_cv,
            )
            validation_initial = _build_validation_snapshot(validation)
            if not validation["valid"] and _should_retry_missing_sections(validation):
                missing_sections = list(validation.get("missing_sections") or [])
                repair_attempt = _build_repair_attempt(missing_sections)
                logger.info(
                    "[run_id=%s] Retrying CV for %s with missing sections: %s",
                    run_id,
                    job.get("job_url"),
                    missing_sections,
                )
                generated_cv = generate_cv(
                    job,
                    evidence,
                    gap,
                    profile,
                    config,
                    fit_classification=fit,
                    repair_missing_sections=missing_sections,
                )
                structured_cv, cv = _unwrap_generated_cv(generated_cv)
                validation = run_all_validations(
                    cv,
                    profile,
                    config,
                    structured_cv=structured_cv,
                )
            if not validation["valid"]:
                failure_details = {
                    "missing_sections": validation.get("missing_sections") or [],
                    "grounding_violations": validation.get("grounding_violations") or [],
                    "skill_violations": validation.get("skill_violations") or [],
                    "warnings": validation.get("warnings") or [],
                }
                logger.warning(
                    "[run_id=%s] CV for %s failed validation: %s",
                    run_id,
                    job.get("job_url"),
                    failure_details,
                )
                # Store rejected version for later review (v2 feature placeholder)
                # store_rejected_cv(job, validation, config)
                cv_generation_debug_records.append(
                    _build_cv_generation_debug_record(
                        job=job,
                        status="validation_failed",
                        fit_classification=fit,
                        evidence_used=_build_debug_evidence_used(evidence),
                        gap_summary=gap,
                        structured_cv_initial=structured_cv_initial,
                        validation_initial=validation_initial,
                        repair_attempt=repair_attempt,
                        structured_cv_final=None,
                        markdown_final=None,
                        error={
                            "stage": "validation",
                            "message": f"CV validation failed for {job.get('job_url')}",
                        },
                    )
                )
                if reporter is not None:
                    reporter.emit("layer4_cv_validation_failed", "warning", f"CV validation failed for {job.get('job_url')}")  # type: ignore[union-attr]
                continue

            structured_cv_final = structured_cv
            markdown_final = cv
            version = create_cv_version_record(
                job_url=str(job.get("job_url") or ""),
                run_id=run_id,
                enrichment_version=str(config.get("enrichment_version") or "v1"),
                vector_rank=int(job.get("vector_rank") or 0),
                ai_score=float(job.get("ai_score") or 0.0),
                final_score=float(job.get("final_score") or 0.0),
                evidence_ids=[str(e.get("evidence_id") or "") for e in evidence],
                prompt_version=str(config["cv"]["generation"]["prompt_version"]),
                cv_markdown=cv,
                gap_summary=gap,
                fit_classification=fit,
                cv_structured=structured_cv,
                cv_generation_model=str(config["cv"]["generation"]["model"]),
                cv_prompt_version=str(config["cv"]["generation"]["prompt_version"]),
            )
            store_cv_version(version, config)
            results.append({
                "job_url": str(job.get("job_url") or ""),
                "fit": fit,
                "ranking_fit_label": fit,
                "cv_version_id": version["version_id"],
                "gap": gap,
                "structured_cv": structured_cv,
                "cv_generation_model": str(config["cv"]["generation"]["model"]),
                "cv_prompt_version": str(config["cv"]["generation"]["prompt_version"]),
                "cv_markdown": cv,
                "generated_at": version.get("generated_at"),
                "fit_classification": fit,
            })
            cv_generation_debug_records.append(
                _build_cv_generation_debug_record(
                    job=job,
                    status="accepted",
                    fit_classification=fit,
                    evidence_used=_build_debug_evidence_used(evidence),
                    gap_summary=gap,
                    structured_cv_initial=structured_cv_initial,
                    validation_initial=validation_initial,
                    repair_attempt=repair_attempt,
                    structured_cv_final=structured_cv_final,
                    markdown_final=markdown_final,
                    error=None,
                )
            )
            logger.info("[run_id=%s] CV generated for %s (fit=%s)", run_id, job.get("job_url"), fit)

        except Exception as exc:  # per-job failure — log and skip, don't crash the run
            logger.error("[run_id=%s] Failed for %s: %s", run_id, job.get("job_url"), exc)
            failure_status = "persistence_failed" if structured_cv_final is not None or markdown_final is not None else "generation_failed"
            failure_stage = "persistence" if failure_status == "persistence_failed" else "generation"
            cv_generation_debug_records.append(
                _build_cv_generation_debug_record(
                    job=job,
                    status=failure_status,
                    fit_classification=fit,
                    evidence_used=_build_debug_evidence_used(evidence),
                    gap_summary=gap,
                    structured_cv_initial=structured_cv_initial,
                    validation_initial=validation_initial,
                    repair_attempt=repair_attempt,
                    structured_cv_final=structured_cv_final if failure_status == "persistence_failed" else None,
                    markdown_final=markdown_final if failure_status == "persistence_failed" else None,
                    error={
                        "stage": failure_stage,
                        "message": str(exc),
                    },
                )
            )
            if reporter is not None:
                reporter.emit(
                    "layer4_cv_error",
                    "error",
                    f"CV generation failed for {job.get('job_url')}: {exc}",
                )  # type: ignore[union-attr]
            continue

    state["cv_results"] = results
    state["cv_generation_debug_records"] = cv_generation_debug_records
    summary: dict[str, Any] = {
        "run_id": run_id,
        "total_jobs": len(raw_jobs),
        "passed_filter": len(passed_jobs),
        "ranked": len(ranked),
        "cvs_generated": len(results),
        "shortlist_debug": {
            "vector_search_top_n": vector_top_n,
            "passed_jobs_total": len(passed_jobs),
            "raw_vector_rows_total": len(raw_shortlist),
            "shortlisted_jobs_total": len(raw_shortlist_urls),
            "scoring_shortlisted_jobs_total": len(shortlist),
            "backfilled_jobs_total": len(backfilled_job_urls),
            "retrieval_anomaly_urls": raw_shortlist_anomaly_urls,
            "candidate_query_text": candidate_summary,
            "not_shortlisted_job_urls": [
                url for url in passed_job_urls
                if url not in raw_shortlist_urls
            ],
            "backfilled_job_urls": backfilled_job_urls,
        },
        "cv_generation_debug_records": cv_generation_debug_records,
        "mapping_suggestions": _collect_mapping_suggestions(enriched, run_id),
        "stage_transition_artifacts": _build_stage_transition_artifacts(
            raw_jobs=raw_jobs,
            normalized=normalized,
            deduplicated_jobs=deduplicated_jobs,
            pre_filter_rejected_jobs=pre_filter_rejected_jobs,
            enriched=enriched,
            passed_jobs=passed_jobs,
            candidate_filter_rejected_jobs=candidate_filter_rejected_jobs,
            raw_shortlist=raw_shortlist,
            shortlist=shortlist,
            backfilled_job_urls=backfilled_job_urls,
            vector_top_n=vector_top_n,
            candidate_summary=candidate_summary,
            ai_scores=ai_scores,
            ranking_inputs=ranking_inputs,
            ranked=ranked,
            final_top_n=final_top_n,
            cv_generation_debug_records=cv_generation_debug_records,
            profile=profile,
            config=config,
        ),
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
            cv_results=results,
            cv_generation_debug_records=cv_generation_debug_records,
            vector_search_top_n=vector_top_n,
        ),
    }
    logger.info("Pipeline run complete [run_id=%s] summary=%s", run_id, summary)
    if reporter is not None:
        event_summary = {
            "run_id": run_id,
            "total_jobs": summary["total_jobs"],
            "passed_filter": summary["passed_filter"],
            "ranked": summary["ranked"],
            "cvs_generated": summary["cvs_generated"],
        }
        reporter.emit("pipeline_complete", "info", str(event_summary))  # type: ignore[union-attr]
    return summary
