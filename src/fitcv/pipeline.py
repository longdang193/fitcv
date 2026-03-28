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
from fitcv.candidate import load_candidate_to_bigquery, load_profile_json_text, load_profile_yaml
from fitcv.config import load_config
from fitcv.cv_generator import generate_cv
from fitcv.embeddings import embed_and_store_candidate, embed_and_store_jobs
from fitcv.enrich import enrich_batch, load_run_structured_jobs, load_structured_jobs
from fitcv.evidence import retrieve_evidence
from fitcv.gap_analysis import classify_fit, compute_gap
from fitcv.ingest import load_to_bigquery, parse_jobs_file, prepare_raw_rows
from fitcv.normalize import normalize_batch
from fitcv.ranking import compute_final_score, rank_jobs, store_final_ranking
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


class PipelineCancelled(Exception):
    """Raised when a cooperative cancellation checkpoint is triggered."""


# ── helpers ───────────────────────────────────────────────────────────────────

def create_run_id() -> str:
    """Return a new UUID4 string to identify this pipeline run."""
    return str(uuid.uuid4())


def _should_retry_missing_sections(validation: dict[str, Any]) -> bool:
    missing_sections = list(validation.get("missing_sections") or [])
    if not missing_sections:
        return False
    return all(not validation.get(field) for field in _REPAIRABLE_VALIDATION_FIELDS)

def build_ranking_features(
    shortlist: list[dict[str, Any]],
    ai_scores: list[dict[str, Any]],
    profile: dict[str, Any],
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    """Merge vector shortlist + AI-score records into a single feature dict per job.

    Final ranking needs all of:
      ai_score, vector_similarity, must_have_match,
      title_relevance, seniority_fit, preference_fit

    Strategy:
    - Index shortlist by job_url to get vector_similarity + rank.
    - For each AI-score record, look up the vector_similarity from the shortlist index.
    - Jobs in the shortlist but missing from ai_scores are silently dropped
      (they were not scored — e.g. upstream filtering removed them).
    - final_score is computed via ranking.compute_final_score().
    """
    shortlist_index: dict[str, dict[str, Any]] = {
        row["job_url"]: row for row in shortlist
    }
    weights = dict(config.get("ranking_weights") or {})

    features: list[dict[str, Any]] = []
    for ai_row in ai_scores:
        job_url = str(ai_row.get("job_url") or "")
        sl_row = shortlist_index.get(job_url)
        if sl_row is None:
            continue  # not in shortlist — skip

        feature: dict[str, Any] = {
            **ai_row,
            "vector_rank": int(sl_row.get("rank") or 0),
            "vector_similarity": float(sl_row.get("similarity_score") or 0.0),
        }
        # Compute deterministic final_score using the ranking module
        null_defaults: dict[str, float] = dict(config.get("ranking_null_defaults") or {
            "ai_score": 0.0,
            "must_have_match": 0.5,
            "vector_similarity": 0.5,
            "title_relevance": 0.5,
            "seniority_fit": 0.5,
            "preference_fit": 0.5,
        })
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
    logger.info("Pipeline run started [run_id=%s]", run_id)
    if reporter is not None:
        reporter.emit("pipeline_start", "info", f"Run started [run_id={run_id}]")  # type: ignore[union-attr]

    # ── Layer 1: ingest + normalise ───────────────────────────────────────────
    raw_jobs = parse_jobs_file(jobs_path)
    normalized = normalize_batch(raw_jobs)

    raw_rows = prepare_raw_rows(raw_jobs)
    load_to_bigquery(raw_rows, config)

    # ── Layer 1b: pre-enrichment global filters ───────────────────────────────
    # Run cheap admin filters before the expensive enrichment step so rejected
    # jobs never enter the LLM/API path.
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
    if reporter is not None:
        n_pre_rejected = len(normalized) - len(surviving_normalized)
        reporter.emit(  # type: ignore[union-attr]
            "layer1b_pre_filter", "info",
            f"Pre-enrichment filter: {len(surviving_normalized)} pass, {n_pre_rejected} rejected",
        )

    # ── Layer 1c: enrich survivors only ──────────────────────────────────────
    # Checkpoint: before enrichment (expensive LLM calls)
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

    # ── Layer 2: candidate profile ────────────────────────────────────────────
    runtime_profile_json: str | None = (
        config.get("runtime_inputs", {}).get("candidate_profile_json")
    )
    if runtime_profile_json:
        profile = load_profile_json_text(runtime_profile_json)
    else:
        profile_path: str = str(config["paths"]["candidate_profile"])
        profile = load_profile_yaml(profile_path)
    load_candidate_to_bigquery(profile, config)
    if reporter is not None:
        reporter.emit("layer2_candidate", "info", "Candidate profile loaded")  # type: ignore[union-attr]

    # ── Layer 3a: candidate-specific rule filter BEFORE embedding ─────────────
    # Global filters already ran pre-enrichment; pass global_settings=None.
    filter_result = apply_rule_filters(enriched, profile["preferences"], config)
    # Merge pre-enrichment and candidate-filter rejects for run-detail visibility.
    combined_filter_result = {
        "passed": filter_result["passed"],
        "rejected": pre_filter["rejected"] + filter_result["rejected"],
    }
    passed_job_urls = [str(url) for url in filter_result["passed"]]
    enriched_by_url = {
        str(job.get("job_url") or ""): job
        for job in enriched
    }
    passed_jobs: list[dict[str, Any]] = [
        enriched_by_url[url]
        for url in passed_job_urls
        if url in enriched_by_url
    ]
    rejected_jobs: list[dict[str, Any]] = list(combined_filter_result["rejected"])
    store_filter_results(combined_filter_result, run_id, config)
    if reporter is not None:
        reporter.emit("layer3_filter", "info", f"{len(passed_jobs)} passed rule filter")  # type: ignore[union-attr]

    # ── Layer 3b: embed → vector shortlist → AI scoring → final ranking ───────
    embed_and_store_jobs(passed_jobs, config)
    embed_and_store_candidate(profile, config)

    vector_top_n = int(config["pipeline"]["vector_search_top_n"])
    # run_vector_search: (profile, passed_job_urls, config, top_n)
    # searches candidate summary embedding against filtered job-summary embeddings
    shortlist = run_vector_search(
        profile,
        passed_job_urls,
        config,
        top_n=vector_top_n,
    )

    ai_top_n = int(config["pipeline"]["ai_score_top_n"])
    from fitcv.vector_search import build_candidate_query_text
    candidate_summary = build_candidate_query_text(profile, config)
    # Checkpoint: before AI scoring
    if cancellation_check and cancellation_check():
        raise PipelineCancelled("Cancelled before AI scoring")
    ai_scores = run_ai_scoring(
        shortlist,
        candidate_summary,
        config,
        top_n=ai_top_n,
    )

    ranking_inputs = build_ranking_features(shortlist, ai_scores, profile, config)
    final_top_n = int(config["pipeline"]["final_top_n"])
    ranked = rank_jobs(ranking_inputs, top_n=final_top_n)
    store_final_ranking(ranked, config)
    if reporter is not None:
        reporter.emit("layer3_ranking", "info", f"Final ranking: top {len(ranked)} jobs")  # type: ignore[union-attr]

    # ── Layer 4: per-job evidence → gap → CV → validation → versioning ────────
    results: list[dict[str, Any]] = []
    # Checkpoint: before CV generation
    if cancellation_check and cancellation_check():
        raise PipelineCancelled("Cancelled before CV generation")
    for job in ranked:
        try:
            evidence_top_k = int(config["pipeline"]["evidence_top_k"])
            evidence = retrieve_evidence(
                profile,
                job.get("required_skills") or [],
                top_k=evidence_top_k,
            )

            gap = compute_gap(
                required_skills=job.get("required_skills") or [],
                candidate_skills=profile.get("skills") or [],
                years_required=job.get("years_required"),
                years_candidate=profile.get("years_experience"),
                config=config,
            )

            required_count = len(job.get("required_skills") or [])
            fit = classify_fit(gap, required_count=required_count, config=config)
            if fit == "skip":
                logger.info("[run_id=%s] Skipping job %s (fit=skip)", run_id, job.get("job_url"))
                if reporter is not None:
                    reporter.emit("layer4_cv_skip", "info", f"Skipped {job.get('job_url')} (fit=skip)")  # type: ignore[union-attr]
                continue

            cv = generate_cv(job, evidence, gap, profile, config)
            validation = run_all_validations(cv, profile, config)
            if not validation["valid"] and _should_retry_missing_sections(validation):
                missing_sections = list(validation.get("missing_sections") or [])
                logger.info(
                    "[run_id=%s] Retrying CV for %s with missing sections: %s",
                    run_id,
                    job.get("job_url"),
                    missing_sections,
                )
                cv = generate_cv(
                    job,
                    evidence,
                    gap,
                    profile,
                    config,
                    repair_missing_sections=missing_sections,
                )
                validation = run_all_validations(cv, profile, config)
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
                if reporter is not None:
                    reporter.emit("layer4_cv_validation_failed", "warning", f"CV validation failed for {job.get('job_url')}")  # type: ignore[union-attr]
                continue

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
            )
            store_cv_version(version, config)
            results.append({
                "job_url": str(job.get("job_url") or ""),
                "fit": fit,
                "cv_version_id": version["version_id"],
                "gap": gap,
            })
            logger.info("[run_id=%s] CV generated for %s (fit=%s)", run_id, job.get("job_url"), fit)

        except Exception as exc:  # per-job failure — log and skip, don't crash the run
            logger.error("[run_id=%s] Failed for %s: %s", run_id, job.get("job_url"), exc)
            continue

    summary: dict[str, Any] = {
        "run_id": run_id,
        "total_jobs": len(raw_jobs),
        "passed_filter": len(passed_jobs),
        "ranked": len(ranked),
        "cvs_generated": len(results),
    }
    logger.info("Pipeline run complete [run_id=%s] summary=%s", run_id, summary)
    if reporter is not None:
        reporter.emit("pipeline_complete", "info", str(summary))  # type: ignore[union-attr]
    return summary
