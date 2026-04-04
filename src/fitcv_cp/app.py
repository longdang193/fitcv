"""FastAPI admin control plane app."""
import datetime
import json as _json
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, field_validator

from fitcv.config import (
    apply_cv_compatibility_projection,
    apply_runtime_skill_synonym_overlay,
    load_config,
    parse_skill_synonym_overlay_yaml,
)
from fitcv_cp.bq_store import (
    append_event,
    archive_run,
    get_events, get_run, insert_run, list_filter_results_for_run,
    list_runs, list_cvs_for_run, get_cv_markdown, list_run_structured_jobs,
    request_run_cancel, unarchive_run, update_run_checkpoint,
    update_run_effective_settings,
    update_run_queue_job_id, update_run_status,
)
from fitcv_cp.models import PipelineRun, RunEvent, RunStatus
from fitcv_cp.queue import cancel_queued_run, enqueue_run, enqueue_run_with_job_id
from fitcv_cp.settings_schema import (
    ALL_GROUP_REGISTRIES,
    CV_GROUPS,
    RANKING_GROUPS,
    SETTINGS_SCHEMA,
    SETTINGS_SECTIONS,
    ValidationError,
    apply_settings_to_config,
    coerce_value,
    validate_settings,
)
from fitcv_cp.settings_store import load_active_settings, save_setting, save_settings_group
TEMPLATES_DIR = Path(__file__).parent / "templates"
PIPELINE_OUTCOME_META: dict[str, dict[str, str]] = {
    "ranked_with_cv": {
        "label": "CV created",
        "badge_class": "badge-success",
    },
    "ranked_skipped_fit_gate": {
        "label": "Ranked, skipped by fit gate",
        "badge_class": "badge-warning",
    },
    "ranked_no_cv": {
        "label": "Ranked, CV failed",
        "badge_class": "badge-warning",
    },
    "not_shortlisted": {
        "label": "Passed filter, not shortlisted",
        "badge_class": "badge-info",
    },
    "shortlisted_not_scored": {
        "label": "Shortlisted, not AI scored",
        "badge_class": "badge-info",
    },
    "scored_not_ranked": {
        "label": "Scored, not final top-N",
        "badge_class": "badge-info",
    },
    "rejected_after_enrichment": {
        "label": "Rejected after enrichment",
        "badge_class": "badge-error",
    },
    "rejected_before_enrichment": {
        "label": "Rejected before enrichment",
        "badge_class": "badge-error",
    },
    "deduplicated_before_enrichment": {
        "label": "Deduplicated before enrichment",
        "badge_class": "badge-warning",
    },
}
DECISION_CHAIN_LABELS: dict[str, str] = {
    "returned_by_vector_search": "returned by vector search",
    "backfilled_for_scoring": "backfilled for scoring",
    "advanced_to_scoring": "advanced to scoring",
    "not_returned_by_vector_search": "not returned by vector search",
    "accepted": "accepted",
    "validation_failed": "validation failed",
    "generation_failed": "generation failed",
    "persistence_failed": "persistence failed",
    "skipped_fit_gate": "skipped by fit gate",
    "not_attempted": "not attempted",
    "not_run": "not run",
    "failed": "failed",
}
TIMELINE_STAGE_DOWNLOADS: dict[str, str] = {
    "layer1_normalize": "normalize",
    "layer1_jobs": "enrich",
    "layer3_filter": "rule_filter",
    "layer3_shortlist": "shortlist",
    "layer3_ranking": "ranking",
    "layer4_cv_analysis": "cv_analysis",
    "layer4_cv_analysis_skip": "cv_analysis",
    "pipeline_complete": "cv_generation",
    "layer4_cv_skip": "cv_analysis",
    "layer4_cv_validation_failed": "cv_generation",
}
STAGE_DOWNLOAD_LABELS: dict[str, str] = {
    "normalize": "Download Normalize JSON",
    "enrich": "Download Enrich JSON",
    "rule_filter": "Download Rule Filter JSON",
    "shortlist": "Download Shortlist JSON",
    "ranking": "Download Ranking JSON",
    "cv_analysis": "Download CV Analysis JSON",
    "cv_generation": "Download CV Generation JSON",
}
RUN_MODE_LABELS = {
    "run_all": "Automatic",
    "manual_staged": "Manual staged",
}


def _stage_quality_metric_row(
    *,
    stage_id: str,
    label: str,
    rate: float | int | None,
    numerator: int | None,
    denominator: int | None,
    hint: str,
) -> dict[str, Any] | None:
    if rate is None or numerator is None or denominator is None:
        return None
    return {
        "stage_id": stage_id,
        "label": label,
        "rate": float(rate),
        "rate_percent": int(round(float(rate) * 100)),
        "numerator": int(numerator),
        "denominator": int(denominator),
        "hint": hint,
    }


def _build_stage_quality_metric_rows(stage_quality_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    shortlist = dict(stage_quality_metrics.get("shortlist") or {})
    shortlist_row = _stage_quality_metric_row(
        stage_id="shortlist",
        label="Shortlist Backfill Rate",
        rate=shortlist.get("backfill_rate"),
        numerator=shortlist.get("backfilled_jobs_total"),
        denominator=shortlist.get("scoring_shortlisted_jobs_total"),
        hint="High values usually mean shortlist recall is relying on backfill.",
    )
    if shortlist_row:
        rows.append(shortlist_row)

    ranking_distribution = dict((stage_quality_metrics.get("ranking") or {}).get("label_distribution") or {})
    ranking_specs = (
        ("Ranking Strong Rate", "strong_rate", "strong_count", "Strong labels among scored ranking inputs."),
        ("Ranking Stretch Rate", "stretch_rate", "stretch_count", "Stretch labels among scored ranking inputs."),
        ("Ranking Skip Rate", "skip_rate", "skip_count", "Skip labels among scored ranking inputs."),
    )
    for label, rate_key, count_key, hint in ranking_specs:
        row = _stage_quality_metric_row(
            stage_id="ranking",
            label=label,
            rate=ranking_distribution.get(rate_key),
            numerator=ranking_distribution.get(count_key),
            denominator=ranking_distribution.get("total_scored"),
            hint=hint,
        )
        if row:
            rows.append(row)

    cv_analysis = dict(stage_quality_metrics.get("cv_analysis") or {})
    cv_analysis_specs = (
        ("CV Analysis Skip Rate", "skip_rate", "skipped_fit_gate", "Jobs blocked by the fit gate after ranking."),
        (
            "CV Analysis Ready Rate",
            "generation_ready_rate",
            "generation_ready",
            "Jobs that are ready to hand off to CV generation.",
        ),
        (
            "CV Analysis Failure Rate",
            "analysis_failed_rate",
            "analysis_failed",
            "Analysis records that failed before generation handoff.",
        ),
    )
    for label, rate_key, count_key, hint in cv_analysis_specs:
        row = _stage_quality_metric_row(
            stage_id="cv_analysis",
            label=label,
            rate=cv_analysis.get(rate_key),
            numerator=cv_analysis.get(count_key),
            denominator=cv_analysis.get("total_processed"),
            hint=hint,
        )
        if row:
            rows.append(row)

    cv_generation = dict(stage_quality_metrics.get("cv_generation") or {})
    cv_generation_specs = (
        (
            "CV Generation Accepted Rate",
            "accepted_rate",
            "accepted",
            "Accepted CV outputs among attempted generation jobs.",
        ),
        (
            "CV Generation Validation-Fail Rate",
            "validation_fail_rate",
            "validation_failed",
            "Generated CVs rejected by validation.",
        ),
        (
            "CV Generation Failure Rate",
            "generation_failed_rate",
            "generation_failed",
            "Runtime failures during CV generation.",
        ),
        (
            "CV Generation Persistence-Fail Rate",
            "persistence_failed_rate",
            "persistence_failed",
            "Generated CVs that failed while saving.",
        ),
    )
    for label, rate_key, count_key, hint in cv_generation_specs:
        row = _stage_quality_metric_row(
            stage_id="cv_generation",
            label=label,
            rate=cv_generation.get(rate_key),
            numerator=cv_generation.get(count_key),
            denominator=cv_generation.get("total_attempted"),
            hint=hint,
        )
        if row:
            rows.append(row)

    return rows


def _build_late_stage_reuse_metric_rows(late_stage_reuse_metrics: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    ranking = dict(late_stage_reuse_metrics.get("ranking") or {})
    ranking_row = _stage_quality_metric_row(
        stage_id="ranking",
        label="Ranking AI-Score Reuse Rate",
        rate=ranking.get("reuse_rate"),
        numerator=ranking.get("reused_ai_scores"),
        denominator=ranking.get("total_ai_scores"),
        hint="Exact-match AI-score rows reused from previous successful runs.",
    )
    if ranking_row:
        ranking_row["fresh_count"] = int(ranking.get("fresh_ai_scores") or 0)
        rows.append(ranking_row)

    cv_analysis = dict(late_stage_reuse_metrics.get("cv_analysis") or {})
    cv_analysis_row = _stage_quality_metric_row(
        stage_id="cv_analysis",
        label="CV Analysis Reuse Rate",
        rate=cv_analysis.get("reuse_rate"),
        numerator=cv_analysis.get("reused_analysis_records"),
        denominator=cv_analysis.get("total_analysis_records"),
        hint="Exact-match analysis records reused from previous successful runs.",
    )
    if cv_analysis_row:
        cv_analysis_row["fresh_count"] = int(cv_analysis.get("fresh_analysis_records") or 0)
        rows.append(cv_analysis_row)

    return rows


def _can_upload_synonym_overlay(run: PipelineRun) -> bool:
    return (
        run.run_mode == "manual_staged"
        and run.status == RunStatus.AWAITING_CONTINUE
        and str(run.next_stage or "").strip() == "rule_filter"
        and str(run.last_completed_stage or "").strip() == "enrich"
    )


def _load_run_effective_config_snapshot(run: PipelineRun) -> dict[str, Any]:
    if run.effective_settings_json:
        try:
            payload = _json.loads(run.effective_settings_json)
            if isinstance(payload, dict):
                return payload
        except (_json.JSONDecodeError, TypeError):
            pass
    return load_config(run.config_path)


def _extract_run_synonym_overlay_info(run: PipelineRun) -> dict[str, Any]:
    if not run.effective_settings_json:
        return {"has_run_overlay": False}
    try:
        payload = _json.loads(run.effective_settings_json)
    except (_json.JSONDecodeError, TypeError):
        return {"has_run_overlay": False}
    if not isinstance(payload, dict):
        return {"has_run_overlay": False}
    runtime = payload.get("skill_synonyms_runtime")
    if not isinstance(runtime, dict):
        return {"has_run_overlay": False}
    return {
        "has_run_overlay": bool(runtime.get("has_run_overlay")),
        "filename": str(runtime.get("run_overlay_filename") or ""),
        "entry_count": int(runtime.get("run_overlay_entry_count") or 0),
        "uploaded_at": str(runtime.get("run_overlay_uploaded_at") or ""),
        "effective_entry_count": int(runtime.get("entry_count") or 0),
    }


def _aggregate_mapping_suggestion_payloads(runs: list[PipelineRun]) -> dict[str, Any]:
    grouped: dict[str, dict[str, Any]] = {}
    for run in runs:
        raw_payload = run.mapping_suggestions_json
        if not raw_payload:
            continue
        try:
            payload = _json.loads(raw_payload)
        except (_json.JSONDecodeError, TypeError):
            continue
        for suggestion in list(payload.get("suggestions") or []):
            if not isinstance(suggestion, dict):
                continue
            alias = str(suggestion.get("alias") or "").strip().lower()
            canonical = str(suggestion.get("canonical") or "").strip().lower()
            if not alias or not canonical:
                continue
            bucket = grouped.setdefault(
                alias,
                {
                    "alias": alias,
                    "canonical": canonical,
                    "occurrences": 0,
                    "confidence_sum": 0.0,
                    "must_have_skills": set(),
                    "run_ids": set(),
                    "conflicting_canonicals": set(),
                },
            )
            bucket["occurrences"] += 1
            bucket["confidence_sum"] += float(suggestion.get("confidence") or 0.0)
            bucket["run_ids"].add(run.run_id)
            must_have_skill = str(suggestion.get("must_have_skill") or "").strip()
            if must_have_skill:
                bucket["must_have_skills"].add(must_have_skill)
            if canonical != bucket["canonical"]:
                bucket["conflicting_canonicals"].add(canonical)
    suggestions: list[dict[str, Any]] = []
    for bucket in grouped.values():
        occurrences = int(bucket["occurrences"])
        suggestions.append(
            {
                "alias": bucket["alias"],
                "canonical": bucket["canonical"],
                "occurrences": occurrences,
                "avg_confidence": (bucket["confidence_sum"] / occurrences) if occurrences else 0.0,
                "must_have_skills": sorted(bucket["must_have_skills"]),
                "run_ids": sorted(bucket["run_ids"]),
                "conflicting_canonicals": sorted(bucket["conflicting_canonicals"]),
            }
        )
    suggestions.sort(key=lambda item: (-int(item["occurrences"]), str(item["alias"])))
    return {
        "mapping_suggestions_schema_version": "mapping_suggestions_aggregate_v1",
        "suggestions": suggestions,
    }


def _decision_chain_label(value: Any) -> str | None:
    normalized = str(value or "").strip()
    if not normalized:
        return None
    return DECISION_CHAIN_LABELS.get(normalized, normalized.replace("_", " "))


def _format_pipeline_outcome_detail(row: dict[str, Any]) -> str | None:
    decision_chain = row.get("decision_chain")
    if not isinstance(decision_chain, dict):
        return None

    detail_parts: list[str] = []
    shortlist = decision_chain.get("shortlist")
    if isinstance(shortlist, dict):
        shortlist_status = _decision_chain_label(shortlist.get("status"))
        if shortlist_status and shortlist_status != "not applicable":
            detail_parts.append(f"Shortlist: {shortlist_status}")

    primary_fit = decision_chain.get("primary_fit")
    if isinstance(primary_fit, dict):
        fit_label = str(primary_fit.get("label") or "").strip()
        if fit_label:
            detail_parts.append(f"Primary fit: {fit_label}")

    cv_generation = decision_chain.get("cv_generation")
    if isinstance(cv_generation, dict):
        cv_status = _decision_chain_label(cv_generation.get("status"))
        if cv_status and cv_status != "not applicable":
            detail_parts.append(f"CV: {cv_status}")

    validation = decision_chain.get("validation")
    if isinstance(validation, dict):
        validation_status = _decision_chain_label(validation.get("status"))
        if validation_status and validation_status != "not run":
            detail_parts.append(f"Validation: {validation_status}")

    if not detail_parts:
        return None
    return " | ".join(detail_parts)


def _timeline_stage_download_for_event(event_stage: str) -> str | None:
    normalized = str(event_stage or "").strip()
    if not normalized:
        return None
    return TIMELINE_STAGE_DOWNLOADS.get(normalized)


def _stage_download_label(stage_id: str | None) -> str | None:
    if not stage_id:
        return None
    return STAGE_DOWNLOAD_LABELS.get(stage_id, f"Download {stage_id.replace('_', ' ').title()} JSON")


class TriggerRequest(BaseModel):
    jobs_path: str = "data/sample_jobs.json"
    config_path: str = ".env.yaml"
    triggered_by: str = "admin"
    config_overrides: dict[str, Any] = {}
    run_mode: str = "run_all"

    @field_validator("jobs_path")
    @classmethod
    def jobs_path_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("jobs_path must not be empty")
        return v

    @field_validator("run_mode")
    @classmethod
    def run_mode_supported(cls, v: str) -> str:
        normalized = str(v or "").strip()
        if normalized not in {"run_all", "manual_staged"}:
            raise ValueError("run_mode must be 'run_all' or 'manual_staged'")
        return normalized


class SettingUpdate(BaseModel):
    value: Any
    updated_by: str = "admin"


def create_app(bq: Any, project: str, dataset: str, redis_url: str) -> FastAPI:
    app = FastAPI(title="FitCV Admin Control Plane")
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    schema_by_key = {entry["key"]: entry for entry in SETTINGS_SCHEMA}
    composition_sections = [
        {
            "id": "summary",
            "title": "Summary",
            "helper": "Professional summary tone and emphasis.",
            "include_key": "cv_summary_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_summary_enabled"]},
                {"title": "Formatting", "keys": ["cv_summary_style"]},
            ],
        },
        {
            "id": "education",
            "title": "Education",
            "helper": "Visibility and detail settings for education.",
            "include_key": "cv_education_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_education_enabled"]},
                {"title": "Formatting", "keys": ["cv_education_detail"]},
            ],
        },
        {
            "id": "experience",
            "title": "Experience",
            "helper": "Whether experience appears and how bullets are written.",
            "include_key": "cv_experience_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_experience_enabled"]},
                {"title": "Formatting", "keys": ["cv_experience_bullet_style"]},
            ],
        },
        {
            "id": "skills",
            "title": "Skills",
            "helper": "Visibility and limits for the skills section.",
            "include_key": "cv_skills_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_skills_enabled"]},
                {"title": "Formatting", "keys": ["cv_skills_max_items"]},
            ],
        },
        {
            "id": "certifications",
            "title": "Certifications",
            "helper": "Whether certifications are shown.",
            "include_key": "cv_certifications_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_certifications_enabled"]},
            ],
        },
        {
            "id": "projects",
            "title": "Projects",
            "helper": "Visibility settings for projects.",
            "include_key": "cv_projects_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_projects_enabled"]},
            ],
        },
        {
            "id": "publications",
            "title": "Publications",
            "helper": "Visibility and detail settings for publications.",
            "include_key": "cv_publications_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_publications_enabled"]},
                {"title": "Formatting", "keys": ["cv_publications_detail"]},
            ],
        },
        {
            "id": "languages",
            "title": "Languages",
            "helper": "Visibility and detail settings for languages.",
            "include_key": "cv_languages_enabled",
            "groups": [
                {"title": "Visibility", "keys": ["cv_languages_enabled"]},
                {"title": "Formatting", "keys": ["cv_languages_detail"]},
            ],
        },
    ]

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    def _build_settings_context(active: dict[str, Any], **extra: Any) -> dict[str, Any]:
        effective = {
            entry["key"]: active.get(entry["key"], entry["default"])
            for entry in SETTINGS_SCHEMA
        }
        context: dict[str, Any] = {
            "schema": SETTINGS_SCHEMA,
            "schema_by_key": schema_by_key,
            "active": active,
            "effective": effective,
            "ranking_weight_keys": RANKING_GROUPS["ranking-weights"],
            "ranking_groups": RANKING_GROUPS,
            "cv_groups": CV_GROUPS,
            "composition_sections": composition_sections,
        }
        context.update(extra)
        return context

    def _settings_form_value(form: Any, key: str) -> Any:
        entry = schema_by_key.get(key, {})
        if entry.get("type") == "list[str]":
            return form.getlist(key)
        return form.get(key, "")

    def _is_stale_cancelling(run: PipelineRun) -> bool:
        if run.status != RunStatus.CANCELLING or run.finished_at is not None:
            return False
        if run.started_at is None:
            return True
        if run.cancel_requested_at is None:
            return False
        now = datetime.datetime.now(datetime.timezone.utc)
        return (now - run.cancel_requested_at) >= datetime.timedelta(minutes=2)

    def _execute_trigger(
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        config_overrides: dict[str, Any],
        *,
        run_mode: str = "run_all",
    ) -> dict:
        # Build effective config: YAML → BQ settings → per-run overrides
        base_config = load_config(config_path)
        active_settings = load_active_settings(bq=bq, project=project, dataset=dataset)

        # Coerce and validate per-run overrides using the same schema
        coerced_overrides: dict[str, Any] = {}
        for k, v in config_overrides.items():
            try:
                coerced_overrides[k] = coerce_value(k, v)
            except KeyError:
                raise HTTPException(status_code=422, detail=f"Unknown setting key: {k!r}")
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=422, detail=str(exc))
        try:
            validate_settings(coerced_overrides)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

        # Merge: YAML < BQ settings < per-run overrides
        effective_config = dict(base_config)
        apply_settings_to_config(effective_config, active_settings)
        apply_settings_to_config(effective_config, coerced_overrides)
        # Recompute derived fields (required_cv_sections, etc.) from effective composition
        effective_config = apply_cv_compatibility_projection(effective_config)

        run_id = str(uuid.uuid4())
        # Insert FIRST — then enqueue. DB is the source of truth.
        run = PipelineRun(
            run_id=run_id,
            status=RunStatus.QUEUED,
            triggered_by=triggered_by,
            trigger_source="ui",
            jobs_path=jobs_path,
            config_path=config_path,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            effective_settings_json=_json.dumps(effective_config),
            run_mode=run_mode,
            checkpoint_status="pending_first_stage" if run_mode == "manual_staged" else None,
            next_stage="normalize" if run_mode == "manual_staged" else None,
            completed_stages=[] if run_mode == "manual_staged" else None,
        )
        insert_run(run, bq, project=project, dataset=dataset)
        _, queue_job_id = enqueue_run_with_job_id(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        update_run_queue_job_id(run_id, queue_job_id, bq, project=project, dataset=dataset)
        return {"run_id": run_id}

    def _execute_trigger_with_inputs(
        jobs_path: str,
        config_path: str,
        triggered_by: str,
        config_overrides: dict[str, Any],
        *,
        jobs_input_source: str | None = None,
        jobs_input_json: str | None = None,
        candidate_profile_source: str | None = None,
        candidate_profile_json: str | None = None,
        run_mode: str = "run_all",
    ) -> dict:
        """Like _execute_trigger but records run-scoped input metadata."""
        # Build effective config: YAML → BQ settings → per-run overrides
        base_config = load_config(config_path)
        active_settings = load_active_settings(bq=bq, project=project, dataset=dataset)
        coerced_overrides: dict[str, Any] = {}
        for k, v in config_overrides.items():
            try:
                coerced_overrides[k] = coerce_value(k, v)
            except KeyError:
                raise HTTPException(status_code=422, detail=f"Unknown setting key: {k!r}")
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=422, detail=str(exc))
        try:
            validate_settings(coerced_overrides)
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        effective_config = dict(base_config)
        apply_settings_to_config(effective_config, active_settings)
        apply_settings_to_config(effective_config, coerced_overrides)
        # Recompute derived fields (required_cv_sections, etc.) from effective composition
        effective_config = apply_cv_compatibility_projection(effective_config)

        # Inject runtime candidate profile override
        if candidate_profile_json:
            effective_config.setdefault("runtime_inputs", {})["candidate_profile_json"] = candidate_profile_json

        run_id = str(uuid.uuid4())
        run = PipelineRun(
            run_id=run_id,
            status=RunStatus.QUEUED,
            triggered_by=triggered_by,
            trigger_source="ui",
            jobs_path=jobs_path,
            config_path=config_path,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            effective_settings_json=_json.dumps(effective_config),
            jobs_input_source=jobs_input_source,
            jobs_input_json=jobs_input_json,
            candidate_profile_source=candidate_profile_source,
            candidate_profile_json=candidate_profile_json,
            run_mode=run_mode,
            checkpoint_status="pending_first_stage" if run_mode == "manual_staged" else None,
            next_stage="normalize" if run_mode == "manual_staged" else None,
            completed_stages=[] if run_mode == "manual_staged" else None,
        )
        insert_run(run, bq, project=project, dataset=dataset)
        _, queue_job_id = enqueue_run_with_job_id(
            jobs_path=jobs_path,
            config_path=config_path,
            triggered_by=triggered_by,
            redis_url=redis_url,
            run_id=run_id,
        )
        update_run_queue_job_id(run_id, queue_job_id, bq, project=project, dataset=dataset)
        return {"run_id": run_id}

    @app.post("/runs", status_code=201)
    def trigger_run(req: TriggerRequest) -> dict:
        return _execute_trigger(
            jobs_path=req.jobs_path,
            config_path=req.config_path,
            triggered_by=req.triggered_by,
            config_overrides=req.config_overrides,
            run_mode=req.run_mode,
        )

    @app.post("/admin/upload-trigger", status_code=201)
    async def upload_trigger(
        jobs_files: list[UploadFile] = File(default_factory=list),
        jobs_file: UploadFile | None = File(None),
        jobs_path: str = Form("data/sample_jobs.json"),
        jobs_input_mode: str = Form("path"),      # "path" | "upload" | "paste"
        jobs_text: str = Form(""),
        config_path: str = Form(".env.yaml"),
        run_mode: str = Form("run_all"),
        candidate_profile_mode: str = Form("default_config"),  # "default_config" | "upload" | "paste"
        candidate_profile_file: UploadFile | None = File(None),
        candidate_profile_text: str = Form(""),
    ) -> dict:
        from fitcv.candidate import load_profile_json_text as _load_json_profile
        from fastapi import HTTPException as _HTTPEx

        _MAX_FILES = 20
        _MAX_TOTAL_BYTES = 50 * 1024 * 1024  # 50 MB

        upload_dir = Path("data/uploads")
        upload_dir.mkdir(parents=True, exist_ok=True)

        from fitcv.candidate import load_profile_yaml as _load_profile_yaml, validate_profile as _validate_profile

        # ── Jobs input resolution ──────────────────────────────────────
        jobs_input_json_snapshot: str | None = None
        if jobs_input_mode == "path":
            if not jobs_path or not jobs_path.strip():
                raise HTTPException(status_code=422, detail="jobs_path required for path mode")
            # Task 1: Resolve and snapshot path-mode jobs input at trigger time
            path_file = Path(jobs_path)
            if not path_file.exists():
                raise HTTPException(status_code=422, detail=f"Jobs file not found: {jobs_path}")
            try:
                raw_text = path_file.read_text(encoding="utf-8")
            except OSError as exc:
                raise HTTPException(status_code=422, detail=f"Cannot read jobs file {jobs_path}: {exc}")
            try:
                parsed_jobs = _json.loads(raw_text)
            except _json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid jobs JSON at {jobs_path}: {exc}")
            if not isinstance(parsed_jobs, list):
                raise HTTPException(
                    status_code=422,
                    detail=f"Invalid jobs JSON at {jobs_path}: top-level value must be a JSON array",
                )
            jobs_input_json_snapshot = _json.dumps(parsed_jobs, ensure_ascii=False, indent=2)
            actual_jobs_path = jobs_path
            jobs_input_source = "path"
        elif jobs_input_mode == "upload":
            # Normalize: accept multi-file (jobs_files) or legacy single-file (jobs_file)
            effective_files: list[UploadFile] = []
            valid_jobs_files = [f for f in (jobs_files or []) if f and f.filename]
            if valid_jobs_files:
                effective_files = valid_jobs_files
            elif jobs_file and jobs_file.filename:
                effective_files = [jobs_file]

            if not effective_files:
                raise HTTPException(status_code=422, detail="jobs_file required for upload mode")

            if len(effective_files) > _MAX_FILES:
                raise HTTPException(
                    status_code=422,
                    detail=f"Too many files: {len(effective_files)} exceeds limit of {_MAX_FILES}",
                )

            # Read and validate each file individually before merging
            validated_arrays: list[list] = []
            total_bytes = 0
            for upload in effective_files:
                raw_bytes = await upload.read()
                total_bytes += len(raw_bytes)
                if total_bytes > _MAX_TOTAL_BYTES:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Total upload size exceeds limit of {_MAX_TOTAL_BYTES // (1024 * 1024)} MB",
                    )
                filename = upload.filename or "<unknown>"
                try:
                    decoded = raw_bytes.decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid jobs JSON in {filename}: {exc}",
                    )
                try:
                    parsed = _json.loads(decoded)
                except _json.JSONDecodeError as exc:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid jobs JSON in {filename}: {exc}",
                    )
                if not isinstance(parsed, list):
                    raise HTTPException(
                        status_code=422,
                        detail=f"Invalid jobs JSON in {filename}: top-level value must be a JSON array",
                    )
                validated_arrays.append(parsed)

            # Merge in submitted file order, preserving row order within each file
            merged_jobs: list = []
            for arr in validated_arrays:
                merged_jobs.extend(arr)

            if not merged_jobs:
                raise HTTPException(
                    status_code=422,
                    detail="Merged upload is empty: all uploaded files contain empty arrays",
                )

            # Serialize once and write the canonical merged file
            canonical_merged = _json.dumps(merged_jobs, ensure_ascii=False, indent=2)
            merged_filename = f"{uuid.uuid4().hex}_merged_jobs.json"
            save_path = upload_dir / merged_filename
            save_path.write_text(canonical_merged, encoding="utf-8")
            actual_jobs_path = str(save_path)
            jobs_input_source = "upload"
            jobs_input_json_snapshot = canonical_merged
        elif jobs_input_mode == "paste":
            if not jobs_text or not jobs_text.strip():
                raise HTTPException(status_code=422, detail="jobs_text required for paste mode")
            try:
                parsed_jobs = _json.loads(jobs_text)
            except _json.JSONDecodeError as exc:
                raise HTTPException(status_code=422, detail=f"Invalid JSON in jobs_text: {exc}")
            if not isinstance(parsed_jobs, list):
                raise HTTPException(status_code=422, detail="jobs_text must be a JSON array of objects")
            canonical = _json.dumps(parsed_jobs, ensure_ascii=False, indent=2)
            paste_file = upload_dir / f"{uuid.uuid4().hex}_pasted_jobs.json"
            paste_file.write_text(canonical, encoding="utf-8")
            actual_jobs_path = str(paste_file)
            jobs_input_source = "paste"
            jobs_input_json_snapshot = canonical
        else:
            raise HTTPException(status_code=422, detail=f"Unknown jobs_input_mode: {jobs_input_mode!r}")

        # ── Candidate profile resolution ─────────────────────────────────
        candidate_json_snapshot: str | None = None
        if candidate_profile_mode == "default_config":
            # Task 2: Resolve and snapshot default_config candidate profile at trigger time
            base_cfg_for_profile = load_config(config_path)
            profile_path_str = base_cfg_for_profile.get("paths", {}).get("candidate_profile", "")
            if not profile_path_str:
                raise HTTPException(status_code=422, detail="No candidate_profile path configured")
            try:
                resolved_profile = _load_profile_yaml(profile_path_str)
            except FileNotFoundError:
                raise HTTPException(
                    status_code=422,
                    detail=f"Candidate profile not found: {profile_path_str}",
                )
            profile_errors = _validate_profile(resolved_profile)
            if profile_errors:
                raise HTTPException(
                    status_code=422,
                    detail=f"Candidate profile validation failed: {'; '.join(profile_errors)}",
                )
            candidate_json_snapshot = _json.dumps(resolved_profile, ensure_ascii=False, indent=2)
            candidate_profile_source = "default_config"
        elif candidate_profile_mode == "upload":
            if not candidate_profile_file or not candidate_profile_file.filename:
                raise HTTPException(status_code=422, detail="candidate_profile_file required for upload mode")
            raw_bytes = await candidate_profile_file.read()
            raw_text = raw_bytes.decode("utf-8")
            try:
                _load_json_profile(raw_text)  # validate
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
            candidate_json_snapshot = _json.dumps(_json.loads(raw_text), ensure_ascii=False, indent=2)
            candidate_profile_source = "upload"
        elif candidate_profile_mode == "paste":
            if not candidate_profile_text or not candidate_profile_text.strip():
                raise HTTPException(status_code=422, detail="candidate_profile_text required for paste mode")
            try:
                _load_json_profile(candidate_profile_text)  # validate
            except ValueError as exc:
                raise HTTPException(status_code=422, detail=str(exc))
            candidate_json_snapshot = _json.dumps(
                _json.loads(candidate_profile_text), ensure_ascii=False, indent=2
            )
            candidate_profile_source = "paste"
        else:
            raise HTTPException(status_code=422, detail=f"Unknown candidate_profile_mode: {candidate_profile_mode!r}")

        return _execute_trigger_with_inputs(
            jobs_path=actual_jobs_path,
            config_path=config_path,
            triggered_by="admin",
            config_overrides={},
            jobs_input_source=jobs_input_source,
            jobs_input_json=jobs_input_json_snapshot,
            candidate_profile_source=candidate_profile_source,
            candidate_profile_json=candidate_json_snapshot,
            run_mode=run_mode,
        )

    @app.get("/runs")
    def get_runs_list() -> list:
        return [_run_to_dict(r) for r in list_runs(bq, project=project, dataset=dataset)]

    @app.get("/runs/{run_id}")
    def get_run_detail(run_id: str) -> dict:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        return _run_to_dict(run)

    @app.get("/runs/{run_id}/events")
    def get_run_events_list(run_id: str) -> list:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        events = get_events(run_id, bq, project=project, dataset=dataset)
        return [
            {
                "event_id": e.event_id,
                "stage": e.stage,
                "level": e.level,
                "message": e.message,
                "created_at": e.created_at.isoformat() if hasattr(e.created_at, "isoformat") else str(e.created_at),
            }
            for e in events
        ]

    @app.get("/settings")
    def get_settings_view() -> dict:
        return load_active_settings(bq=bq, project=project, dataset=dataset)

    @app.post("/settings/{key}", status_code=200)
    def update_setting(key: str, body: SettingUpdate) -> dict:
        try:
            coerced = coerce_value(key, body.value)
        except KeyError:
            raise HTTPException(status_code=422, detail=f"Unknown setting key: {key!r}")
        except (ValueError, TypeError) as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        try:
            validate_settings({key: coerced})
        except ValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        save_setting(key, coerced, updated_by=body.updated_by, bq=bq, project=project, dataset=dataset)
        return {"key": key, "value": coerced}

    @app.get("/admin/settings", response_class=HTMLResponse)
    def admin_settings_view(request: Request) -> HTMLResponse:
        active = load_active_settings(bq=bq, project=project, dataset=dataset)
        return templates.TemplateResponse(
            request=request,
            name="settings.html",
            context=_build_settings_context(active),
        )

    @app.post("/admin/settings/{key}", response_class=HTMLResponse)
    async def admin_settings_update_key(request: Request, key: str) -> HTMLResponse:
        from fastapi import Form
        from fastapi.responses import RedirectResponse
        form = await request.form()
        value = form.get("value", "")
        try:
            coerced = coerce_value(key, value)
            validate_settings({key: coerced})
        except (KeyError, ValidationError, ValueError) as exc:
            active = load_active_settings(bq=bq, project=project, dataset=dataset)
            return templates.TemplateResponse(
                request=request,
                name="settings.html",
                context=_build_settings_context(active, error=str(exc)),
                status_code=422,
            )
        save_setting(key, coerced, updated_by="admin", bq=bq, project=project, dataset=dataset)
        return RedirectResponse("/admin/settings", status_code=303)

    @app.post("/admin/settings/group/{group_name}", response_class=HTMLResponse)
    async def admin_settings_update_group(
        request: Request, group_name: str
    ) -> HTMLResponse:
        from uuid import uuid4
        from fastapi.responses import RedirectResponse

        # Resolve group across both namespaces (ranking + cv)
        target_registry: dict[str, list[str]] | None = None
        for registry in ALL_GROUP_REGISTRIES.values():
            if group_name in registry:
                target_registry = registry
                break
        if target_registry is None:
            raise HTTPException(status_code=404, detail=f"Unknown group: {group_name!r}")

        keys = target_registry[group_name]
        form = await request.form()

        # Coerce all keys in the group
        coerced: dict = {}
        coerce_errors: list[str] = []
        for key in keys:
            raw = _settings_form_value(form, key)
            try:
                coerced[key] = coerce_value(key, raw)
            except (KeyError, ValueError) as exc:
                coerce_errors.append(str(exc))

        def _get_active() -> dict:
            return load_active_settings(bq=bq, project=project, dataset=dataset)

        def _error_response(msg: str) -> HTMLResponse:
            active = _get_active()
            return templates.TemplateResponse(
                request=request,
                name="settings.html",
                context=_build_settings_context(
                    active,
                    group_error={group_name: msg},
                    group_draft={group_name: {key: _settings_form_value(form, key) for key in keys}},
                ),
                status_code=422,
            )

        if coerce_errors:
            return _error_response("; ".join(coerce_errors))

        # Validate full group as one coherent payload — no write occurs on failure
        try:
            validate_settings(coerced)
        except ValidationError as exc:
            return _error_response(str(exc))

        # Generate shared audit identity for this grouped save
        update_id = str(uuid4())
        updated_by = f"admin:grp:{update_id}"

        # Write — surface BQ failures to the user
        try:
            save_settings_group(
                coerced, updated_by=updated_by, bq=bq, project=project, dataset=dataset
            )
        except RuntimeError as exc:
            return _error_response(f"Save failed: {exc}")

        return RedirectResponse("/admin/settings", status_code=303)

    @app.post("/admin/settings/section/{section_name}", response_class=HTMLResponse)
    async def admin_settings_section_save(
        request: Request, section_name: str
    ) -> HTMLResponse:
        """Section-level save for retrieval, timing, and global-job-filters.

        Each key is validated independently (no cross-key constraints within a section).
        A 422 is returned if any value fails validation, with section_errors populated
        so the template can highlight offending fields.
        """
        from uuid import uuid4
        from fastapi.responses import RedirectResponse as _Redirect

        if section_name not in SETTINGS_SECTIONS:
            raise HTTPException(status_code=404, detail=f"Unknown section: {section_name!r}")

        keys = SETTINGS_SECTIONS[section_name]
        form = await request.form()

        coerced: dict = {}
        section_errors: dict[str, str] = {}

        for key in keys:
            raw = _settings_form_value(form, key)
            try:
                coerced[key] = coerce_value(key, raw)
            except (KeyError, ValueError) as exc:
                section_errors[key] = str(exc)

        # Run cross-key validation across all coerced values in this section
        if not section_errors:
            try:
                validate_settings(coerced)
            except ValidationError as exc:
                section_errors[keys[0]] = str(exc)

        def _section_error_response(errors: dict[str, str]) -> HTMLResponse:
            active = load_active_settings(bq=bq, project=project, dataset=dataset)
            return templates.TemplateResponse(
                request=request,
                name="settings.html",
                context=_build_settings_context(
                    active,
                    section_errors=errors,
                    section_draft={key: _settings_form_value(form, key) for key in keys},
                ),
                status_code=422,
            )

        if section_errors:
            return _section_error_response(section_errors)

        update_id = str(uuid4())
        updated_by = f"admin:section:{update_id}"
        try:
            save_settings_group(
                coerced, updated_by=updated_by, bq=bq, project=project, dataset=dataset
            )
        except RuntimeError as exc:
            return _section_error_response({keys[0]: f"Save failed: {exc}"})

        return _Redirect("/admin/settings", status_code=303)

    @app.get("/admin/runs", response_class=HTMLResponse)
    def admin_runs(request: Request) -> HTMLResponse:
        view = request.query_params.get("view", "active")
        if view == "archived":
            runs = list_runs(bq, project=project, dataset=dataset, archived_only=True)
        elif view == "all":
            runs = list_runs(bq, project=project, dataset=dataset, include_archived=True)
        else:  # default: active
            runs = list_runs(bq, project=project, dataset=dataset, include_archived=False)
        return templates.TemplateResponse(
            request=request, name="runs_list.html",
            context={"runs": runs, "view": view, "is_stale_cancelling": _is_stale_cancelling}
        )

    @app.post("/admin/runs/{run_id}/stop")
    def admin_stop_run(run_id: str) -> dict:
        """Stop a queued or running run. Returns JSON for fetch() callers."""
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        eligible = {RunStatus.QUEUED, RunStatus.RUNNING}
        if run.status not in eligible:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot stop run with status '{run.status.value}'",
            )
        now = datetime.datetime.now(datetime.timezone.utc)
        event_id = str(uuid.uuid4())
        if run.status == RunStatus.QUEUED and run.queue_job_id:
            cancelled_in_queue = cancel_queued_run(run.queue_job_id, redis_url=redis_url)
            if cancelled_in_queue:
                # Job still in queue — mark directly cancelled
                request_run_cancel(run_id, "admin", RunStatus.CANCELLED.value, bq, project=project, dataset=dataset)
                append_event(
                    RunEvent(
                        run_id=run_id, event_id=event_id, stage="cancel_requested",
                        level="warning", message="Stop requested — cancelled from queue",
                        created_at=now,
                    ),
                    bq, project=project, dataset=dataset,
                )
                append_event(
                    RunEvent(
                        run_id=run_id, event_id=str(uuid.uuid4()), stage="run_cancelled",
                        level="warning", message="Run cancelled before pipeline execution",
                        created_at=now,
                    ),
                    bq, project=project, dataset=dataset,
                )
                return {"status": "cancelled", "run_id": run_id}
        if run.status == RunStatus.QUEUED and run.started_at is None:
            request_run_cancel(run_id, "admin", RunStatus.CANCELLED.value, bq, project=project, dataset=dataset)
            append_event(
                RunEvent(
                    run_id=run_id, event_id=event_id, stage="cancel_requested",
                    level="warning", message="Stop requested — cancelled before worker claim",
                    created_at=now,
                ),
                bq, project=project, dataset=dataset,
            )
            append_event(
                RunEvent(
                    run_id=run_id, event_id=str(uuid.uuid4()), stage="run_cancelled",
                    level="warning", message="Run cancelled before pipeline execution",
                    created_at=now,
                ),
                bq, project=project, dataset=dataset,
            )
            return {"status": "cancelled", "run_id": run_id}
        # Running (or queued but already claimed) — set cancelling
        request_run_cancel(run_id, "admin", RunStatus.CANCELLING.value, bq, project=project, dataset=dataset)
        append_event(
            RunEvent(
                run_id=run_id, event_id=event_id, stage="cancel_requested",
                level="warning", message="Stop requested — run will be cancelled at next checkpoint",
                created_at=now,
            ),
            bq, project=project, dataset=dataset,
        )
        return {"status": "cancelling", "run_id": run_id}

    @app.post("/admin/runs/{run_id}/synonym-overlay")
    async def admin_upload_run_synonym_overlay(
        run_id: str,
        synonym_overlay_file: UploadFile = File(...),
    ) -> RedirectResponse:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if not _can_upload_synonym_overlay(run):
            raise HTTPException(
                status_code=409,
                detail="Synonym overlay upload is only available for manual runs paused after enrich",
            )
        filename = str(synonym_overlay_file.filename or "").strip()
        if not filename:
            raise HTTPException(status_code=422, detail="A synonym overlay YAML file is required")
        raw_bytes = await synonym_overlay_file.read()
        if not raw_bytes:
            raise HTTPException(status_code=422, detail="Uploaded synonym overlay file is empty")
        try:
            raw_text = raw_bytes.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="Synonym overlay must be UTF-8 encoded text") from exc
        try:
            overlay_synonyms = parse_skill_synonym_overlay_yaml(raw_text)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

        effective_config = _load_run_effective_config_snapshot(run)
        uploaded_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
        updated_config = apply_runtime_skill_synonym_overlay(
            effective_config,
            overlay_synonyms,
            source="upload",
            filename=filename,
            uploaded_at=uploaded_at,
        )
        update_run_effective_settings(
            run_id,
            _json.dumps(updated_config, ensure_ascii=False),
            bq,
            project=project,
            dataset=dataset,
        )
        append_event(
            RunEvent(
                run_id=run_id,
                event_id=str(uuid.uuid4()),
                stage="synonym_overlay_uploaded",
                level="info",
                message=f"Run-scoped synonym overlay uploaded ({len(overlay_synonyms)} entries)",
                created_at=datetime.datetime.now(datetime.timezone.utc),
                payload_json=_json.dumps(
                    {
                        "filename": filename,
                        "entry_count": len(overlay_synonyms),
                    },
                    ensure_ascii=False,
                ),
            ),
            bq,
            project=project,
            dataset=dataset,
        )
        return RedirectResponse(f"/admin/runs/{run_id}", status_code=303)

    @app.post("/admin/runs/{run_id}/continue")
    def admin_continue_run(run_id: str) -> dict:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.run_mode != "manual_staged":
            raise HTTPException(status_code=409, detail="Only manual staged runs can be continued")
        if run.status != RunStatus.AWAITING_CONTINUE:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot continue run with status '{run.status.value}'",
            )
        if not run.next_stage:
            raise HTTPException(status_code=409, detail="Run has no next stage to continue")
        _, queue_job_id = enqueue_run_with_job_id(
            jobs_path=run.jobs_path,
            config_path=run.config_path,
            triggered_by="admin",
            redis_url=redis_url,
            run_id=run.run_id,
        )
        update_run_status(run.run_id, RunStatus.QUEUED, bq, project=project, dataset=dataset)
        update_run_queue_job_id(run.run_id, queue_job_id, bq, project=project, dataset=dataset)
        update_run_checkpoint(
            run.run_id,
            bq,
            project=project,
            dataset=dataset,
            checkpoint_status="queued_for_continue",
            next_stage=run.next_stage,
            last_completed_stage=run.last_completed_stage,
            completed_stages=run.completed_stages,
            checkpoint_payload_json=run.checkpoint_payload_json,
        )
        append_event(
            RunEvent(
                run_id=run.run_id,
                event_id=str(uuid.uuid4()),
                stage="manual_continue_requested",
                level="info",
                message=f"Manual run queued to continue from {run.next_stage}",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ),
            bq,
            project=project,
            dataset=dataset,
        )
        return {"status": "queued", "run_id": run.run_id}

    @app.post("/admin/runs/{run_id}/archive")
    def admin_archive_run(run_id: str) -> dict:
        """Archive a terminal run. Returns JSON for fetch() callers."""
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        eligible = {RunStatus.SUCCEEDED, RunStatus.FAILED, RunStatus.CANCELLED}
        if run.status not in eligible:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot archive run with status '{run.status.value}'",
            )
        if run.archived_at is not None:
            raise HTTPException(status_code=409, detail="Run is already archived")
        archive_run(run_id, "admin", bq, project=project, dataset=dataset)
        append_event(
            RunEvent(
                run_id=run_id, event_id=str(uuid.uuid4()), stage="run_archived",
                level="info", message="Run archived by admin",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ),
            bq, project=project, dataset=dataset,
        )
        return {"status": "archived", "run_id": run_id}

    @app.post("/admin/runs/{run_id}/repair-cancellation")
    def admin_repair_cancellation(run_id: str) -> dict:
        """Repair a stale cancelling run that never actually started."""
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if not _is_stale_cancelling(run):
            raise HTTPException(
                status_code=409,
                detail=f"Cannot repair run with status '{run.status.value}'",
            )
        now = datetime.datetime.now(datetime.timezone.utc)
        update_run_status(
            run_id,
            RunStatus.CANCELLED,
            bq,
            project=project,
            dataset=dataset,
            finished_at=now,
        )
        append_event(
            RunEvent(
                run_id=run_id,
                event_id=str(uuid.uuid4()),
                stage="run_cancelled",
                level="warning",
                message="Run repaired from stale cancelling state",
                created_at=now,
            ),
            bq,
            project=project,
            dataset=dataset,
        )
        return {"status": "cancelled", "run_id": run_id}

    @app.post("/admin/runs/{run_id}/unarchive")
    def admin_unarchive_run(run_id: str) -> dict:
        """Unarchive a run, returning it to the active list. Returns JSON for fetch() callers."""
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.archived_at is None:
            raise HTTPException(status_code=409, detail="Run is not archived")
        unarchive_run(run_id, bq, project=project, dataset=dataset)
        append_event(
            RunEvent(
                run_id=run_id, event_id=str(uuid.uuid4()), stage="run_unarchived",
                level="info", message="Run unarchived by admin",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            ),
            bq, project=project, dataset=dataset,
        )
        return {"status": "unarchived", "run_id": run_id}

    @app.get("/admin/runs/{run_id}", response_class=HTMLResponse)
    def admin_run_detail(request: Request, run_id: str) -> HTMLResponse:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404)
        events = get_events(run_id, bq, project=project, dataset=dataset)
        timeline_events: list[dict[str, Any]] = []
        for ev in events:
            stage_id = _timeline_stage_download_for_event(ev.stage)
            timeline_events.append(
                {
                    "created_at": ev.created_at,
                    "stage": ev.stage,
                    "level": ev.level,
                    "message": ev.message,
                    "stage_id": stage_id,
                    "stage_download_url": (
                        f"/admin/runs/{run_id}/stage-artifacts/{stage_id}.json"
                        if stage_id and run.stage_transition_artifacts_json
                        else None
                    ),
                    "stage_download_label": _stage_download_label(stage_id),
                }
            )
        cv_versions = list_cvs_for_run(run_id, bq, project=project, dataset=dataset)
        enriched_jobs = list_run_structured_jobs(run_id, bq, project=project, dataset=dataset)
        filter_results = list_filter_results_for_run(run_id, bq, project=project, dataset=dataset)

        # Build per-job filter outcome lookup: job_url → {passed, reasons}
        filter_results_by_job_url: dict[str, dict] = {
            row["job_url"]: row for row in filter_results
        }

        # Jobs rejected before enrichment have filter_results rows but no enriched row.
        enriched_job_urls = {j["job_url"] for j in enriched_jobs}
        pre_enrichment_rejects = [
            row for row in filter_results
            if row["job_url"] not in enriched_job_urls and row.get("reasons")
        ]
        deduplicated_before_enrichment: list[dict[str, str | list[str] | None]] = []
        pipeline_outcomes_by_job_url: dict[str, dict[str, str | None]] = {}
        stage_quality_metrics: dict[str, Any] = {}
        stage_quality_metric_rows: list[dict[str, Any]] = []
        late_stage_reuse_metrics: dict[str, Any] = {}
        late_stage_reuse_metric_rows: list[dict[str, Any]] = []
        if run.results_export_json:
            try:
                export_payload = _json.loads(run.results_export_json)
                stage_quality_metrics = dict(export_payload.get("stage_quality_metrics") or {})
                stage_quality_metric_rows = _build_stage_quality_metric_rows(stage_quality_metrics)
                late_stage_reuse_metrics = dict(export_payload.get("late_stage_reuse_metrics") or {})
                late_stage_reuse_metric_rows = _build_late_stage_reuse_metric_rows(late_stage_reuse_metrics)
                pipeline_outcomes_by_job_url = {
                    str(row.get("job_url") or ""): {
                        "status": str(row.get("pipeline_status") or ""),
                        "label": PIPELINE_OUTCOME_META.get(
                            str(row.get("pipeline_status") or ""),
                            {"label": str(row.get("pipeline_status") or "Unknown pipeline outcome")},
                        )["label"],
                        "badge_class": PIPELINE_OUTCOME_META.get(
                            str(row.get("pipeline_status") or ""),
                            {"badge_class": "badge-info"},
                        )["badge_class"],
                        "detail": _format_pipeline_outcome_detail(row),
                    }
                    for row in export_payload.get("results", [])
                    if row.get("job_url")
                }
                deduplicated_before_enrichment = [
                    {
                        "job_url": row.get("job_url"),
                        "job_title": row.get("job_title"),
                        "reasons": row.get("reject_reasons") or [],
                    }
                    for row in export_payload.get("results", [])
                    if row.get("pipeline_status") == "deduplicated_before_enrichment"
                ]
            except (_json.JSONDecodeError, TypeError, AttributeError):
                deduplicated_before_enrichment = []
                pipeline_outcomes_by_job_url = {}
                stage_quality_metrics = {}
                stage_quality_metric_rows = []
                late_stage_reuse_metrics = {}
                late_stage_reuse_metric_rows = []

        # Build job title lookup: job_url → title (used for cv_versions generated output labels)
        job_title_by_url: dict[str, str] = {
            j["job_url"]: j.get("title") or ""
            for j in enriched_jobs
        }

        # Pre-compute pass/reject counts for the enriched jobs summary row.
        # Rows where filter result is missing are NOT counted as rejected — they are "unknown".
        # This preserves the existing three-state distinction (pass / reject / —).
        enriched_passed_count = sum(
            1 for j in enriched_jobs
            if filter_results_by_job_url.get(j["job_url"], {}).get("passed") is True
        )
        enriched_rejected_count = sum(
            1 for j in enriched_jobs
            if filter_results_by_job_url.get(j["job_url"], {}).get("passed") is False
        )

        # Candidate profile display
        candidate_profile_parsed: dict | None = None
        candidate_profile_pretty: str | None = None
        if run.candidate_profile_json:
            try:
                candidate_profile_parsed = _json.loads(run.candidate_profile_json)
                candidate_profile_pretty = _json.dumps(candidate_profile_parsed, indent=2, ensure_ascii=False)
            except (_json.JSONDecodeError, TypeError):
                candidate_profile_pretty = run.candidate_profile_json

        return templates.TemplateResponse(
            request=request, name="run_detail.html", context={
                "run": run,
                "run_mode_label": RUN_MODE_LABELS.get(run.run_mode, run.run_mode),
                "events": timeline_events,
                "cv_versions": cv_versions,
                "enriched_jobs": enriched_jobs,
                "filter_results_by_job_url": filter_results_by_job_url,
                "pipeline_outcomes_by_job_url": pipeline_outcomes_by_job_url,
                "stage_quality_metrics": stage_quality_metrics,
                "stage_quality_metric_rows": stage_quality_metric_rows,
                "late_stage_reuse_metrics": late_stage_reuse_metrics,
                "late_stage_reuse_metric_rows": late_stage_reuse_metric_rows,
                "pre_enrichment_rejects": pre_enrichment_rejects,
                "deduplicated_before_enrichment": deduplicated_before_enrichment,
                "job_title_by_url": job_title_by_url,
                "enriched_passed_count": enriched_passed_count,
                "enriched_rejected_count": enriched_rejected_count,
                "candidate_profile_parsed": candidate_profile_parsed,
                "candidate_profile_pretty": candidate_profile_pretty,
                "is_stale_cancelling": _is_stale_cancelling,
                "can_continue_manual_run": (
                    run.run_mode == "manual_staged"
                    and run.status == RunStatus.AWAITING_CONTINUE
                    and bool(run.next_stage)
                ),
                "can_upload_synonym_overlay": _can_upload_synonym_overlay(run),
                "synonym_overlay_info": _extract_run_synonym_overlay_info(run),
            }
        )

    @app.get("/admin/cvs/{version_id}/download")
    def download_cv(version_id: str):
        content = get_cv_markdown(version_id, bq, project=project, dataset=dataset)
        if content is None:
            raise HTTPException(status_code=404, detail="CV not found")
        return Response(
            content=content,
            media_type="text/markdown",
            headers={"Content-Disposition": f'attachment; filename="cv_{version_id}.md"'}
        )

    @app.get("/admin/runs/{run_id}/export.json")
    def download_run_results_json(run_id: str) -> Response:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status != RunStatus.SUCCEEDED:
            raise HTTPException(status_code=409, detail="Run results export is only available for succeeded runs")
        if not run.results_export_json:
            raise HTTPException(status_code=404, detail="Run results export is not available for this run")
        pretty_json = _json.dumps(_json.loads(run.results_export_json), ensure_ascii=False, indent=2)
        return Response(
            content=pretty_json,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="fitcv-run-{run_id}-results.json"'},
        )

    @app.get("/admin/runs/{run_id}/cv-debug.json")
    def download_run_cv_debug_json(run_id: str) -> Response:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status != RunStatus.SUCCEEDED:
            raise HTTPException(status_code=409, detail="CV debug export is only available for succeeded runs")
        if not run.cv_generation_debug_json:
            raise HTTPException(status_code=404, detail="CV debug export is not available for this run")
        pretty_json = _json.dumps(_json.loads(run.cv_generation_debug_json), ensure_ascii=False, indent=2)
        return Response(
            content=pretty_json,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="fitcv-run-{run_id}-cv-debug.json"'},
        )

    @app.get("/admin/runs/{run_id}/stage-artifacts.json")
    def download_run_stage_transition_artifacts_json(run_id: str) -> Response:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if not run.stage_transition_artifacts_json:
            raise HTTPException(status_code=404, detail="Stage transition artifacts export is not available for this run")
        pretty_json = _json.dumps(_json.loads(run.stage_transition_artifacts_json), ensure_ascii=False, indent=2)
        return Response(
            content=pretty_json,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="fitcv-run-{run_id}-stage-artifacts.json"'},
        )

    @app.get("/admin/runs/{run_id}/stage-artifacts/{stage_id}.json")
    def download_run_stage_transition_artifact_stage_json(run_id: str, stage_id: str) -> Response:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if not run.stage_transition_artifacts_json:
            raise HTTPException(status_code=404, detail="Stage transition artifacts export is not available for this run")
        if stage_id not in {"normalize", "enrich", "rule_filter", "shortlist", "ranking", "cv_analysis", "cv_generation"}:
            raise HTTPException(status_code=404, detail="Unknown stage artifact")
        artifact_payload = _json.loads(run.stage_transition_artifacts_json)
        artifacts = artifact_payload.get("artifacts") or {}
        stages = artifacts.get("stages") or {}
        stage_artifact = stages.get(stage_id)
        if not isinstance(stage_artifact, dict):
            raise HTTPException(status_code=404, detail="Stage artifact is not available for this run")
        payload = {
            "run_id": run_id,
            "stage_id": stage_id,
            "artifact_schema_version": "stage_transition_artifacts_stage_v1",
            "created_at": artifact_payload.get("created_at"),
            "stage_artifact": stage_artifact,
        }
        return Response(
            content=_json.dumps(payload, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="fitcv-run-{run_id}-{stage_id}.json"'},
        )

    @app.get("/admin/runs/{run_id}/settings-used.json")
    def download_run_settings_used_json(run_id: str) -> Response:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if run.status != RunStatus.SUCCEEDED:
            raise HTTPException(status_code=409, detail="Settings-used export is only available for succeeded runs")
        if not run.settings_used_json:
            raise HTTPException(status_code=404, detail="Settings-used export is not available for this run")
        pretty_json = _json.dumps(_json.loads(run.settings_used_json), ensure_ascii=False, indent=2)
        return Response(
            content=pretty_json,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="fitcv-run-{run_id}-settings-used.json"'},
        )

    @app.get("/admin/runs/{run_id}/mapping-suggestions.json")
    def download_run_mapping_suggestions_json(run_id: str) -> Response:
        run = get_run(run_id, bq, project=project, dataset=dataset)
        if run is None:
            raise HTTPException(status_code=404, detail="Run not found")
        if not run.mapping_suggestions_json:
            raise HTTPException(status_code=404, detail="Mapping suggestions export is not available for this run")
        pretty_json = _json.dumps(_json.loads(run.mapping_suggestions_json), ensure_ascii=False, indent=2)
        return Response(
            content=pretty_json,
            media_type="application/json",
            headers={"Content-Disposition": f'attachment; filename="fitcv-run-{run_id}-mapping-suggestions.json"'},
        )

    @app.get("/admin/mapping-suggestions.json")
    def download_aggregate_mapping_suggestions_json() -> Response:
        runs = list_runs(
            bq,
            project=project,
            dataset=dataset,
            limit=500,
            include_archived=True,
        )
        payload = _aggregate_mapping_suggestion_payloads(runs)
        return Response(
            content=_json.dumps(payload, ensure_ascii=False, indent=2),
            media_type="application/json",
            headers={"Content-Disposition": 'attachment; filename="fitcv-mapping-suggestions.json"'},
        )

    return app


def _run_to_dict(run: PipelineRun) -> dict:
    return {
        "run_id": run.run_id,
        "status": run.status.value,
        "run_mode": run.run_mode,
        "checkpoint_status": run.checkpoint_status,
        "next_stage": run.next_stage,
        "last_completed_stage": run.last_completed_stage,
        "completed_stages": list(run.completed_stages or []),
        "triggered_by": run.triggered_by,
        "jobs_path": run.jobs_path,
        "created_at": run.created_at.isoformat() if run.created_at else None,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "total_jobs": run.total_jobs,
        "passed_filter": run.passed_filter,
        "ranked": run.ranked,
        "cvs_generated": run.cvs_generated,
        "error_message": run.error_message,
        "error_stage": run.error_stage,
    }
