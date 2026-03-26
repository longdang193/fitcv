"""BigQuery persistence helpers for control-plane tables.

All mutating queries use query parameters — never string interpolation.
"""
import datetime
import logging
from typing import Any, Optional

from google.cloud import bigquery as bq_module

from fitcv_cp.models import PipelineRun, RunEvent, RunStatus

logger = logging.getLogger(__name__)


def insert_run(run: PipelineRun, bq: Any, *, project: str, dataset: str) -> None:
    table = f"{project}.{dataset}.pipeline_runs"
    sql = f"""
        INSERT INTO `{table}` (
            run_id, status, triggered_by, trigger_source,
            jobs_path, config_path, created_at, effective_settings_json,
            jobs_input_source, jobs_input_json,
            candidate_profile_source, candidate_profile_json
        )
        VALUES (
            @run_id, @status, @triggered_by, @trigger_source,
            @jobs_path, @config_path, @created_at, @effective_settings_json,
            @jobs_input_source, @jobs_input_json,
            @candidate_profile_source, @candidate_profile_json
        )
    """
    job_config = bq_module.QueryJobConfig(
        query_parameters=[
            bq_module.ScalarQueryParameter("run_id", "STRING", run.run_id),
            bq_module.ScalarQueryParameter("status", "STRING", run.status.value),
            bq_module.ScalarQueryParameter("triggered_by", "STRING", run.triggered_by),
            bq_module.ScalarQueryParameter("trigger_source", "STRING", run.trigger_source),
            bq_module.ScalarQueryParameter("jobs_path", "STRING", run.jobs_path),
            bq_module.ScalarQueryParameter("config_path", "STRING", run.config_path),
            bq_module.ScalarQueryParameter("created_at", "TIMESTAMP", run.created_at),
            bq_module.ScalarQueryParameter("effective_settings_json", "STRING", run.effective_settings_json),
            bq_module.ScalarQueryParameter("jobs_input_source", "STRING", run.jobs_input_source),
            bq_module.ScalarQueryParameter("jobs_input_json", "STRING", run.jobs_input_json),
            bq_module.ScalarQueryParameter("candidate_profile_source", "STRING", run.candidate_profile_source),
            bq_module.ScalarQueryParameter("candidate_profile_json", "STRING", run.candidate_profile_json),
        ]
    )
    bq.query(sql, job_config=job_config).result()


def update_run_status(
    run_id: str,
    status: RunStatus,
    bq: Any,
    *,
    project: str,
    dataset: str,
    started_at: Optional[datetime.datetime] = None,
    finished_at: Optional[datetime.datetime] = None,
    summary: Optional[dict] = None,
    error_message: Optional[str] = None,
    error_stage: Optional[str] = None,
) -> None:
    set_clauses = ["status = @status"]
    params: list[bq_module.ScalarQueryParameter] = [
        bq_module.ScalarQueryParameter("status", "STRING", status.value),
        bq_module.ScalarQueryParameter("run_id", "STRING", run_id),
    ]
    if started_at:
        set_clauses.append("started_at = @started_at")
        params.append(bq_module.ScalarQueryParameter("started_at", "TIMESTAMP", started_at))
    if finished_at:
        set_clauses.append("finished_at = @finished_at")
        params.append(bq_module.ScalarQueryParameter("finished_at", "TIMESTAMP", finished_at))
    if error_message:
        set_clauses.append("error_message = @error_message")
        params.append(bq_module.ScalarQueryParameter("error_message", "STRING", error_message))
    if error_stage:
        set_clauses.append("error_stage = @error_stage")
        params.append(bq_module.ScalarQueryParameter("error_stage", "STRING", error_stage))
    if summary:
        for k in ("total_jobs", "passed_filter", "ranked", "cvs_generated"):
            if k in summary:
                set_clauses.append(f"{k} = @{k}")
                params.append(bq_module.ScalarQueryParameter(k, "INT64", int(summary[k])))

    sql = (
        f"UPDATE `{project}.{dataset}.pipeline_runs` "
        f"SET {', '.join(set_clauses)} WHERE run_id = @run_id"
    )
    job_config = bq_module.QueryJobConfig(query_parameters=params)
    bq.query(sql, job_config=job_config).result()


def append_event(event: RunEvent, bq: Any, *, project: str, dataset: str) -> None:
    table = f"{project}.{dataset}.pipeline_run_events"
    row = {
        "run_id": event.run_id,
        "event_id": event.event_id,
        "stage": event.stage,
        "level": event.level,
        "message": event.message,
        "payload_json": event.payload_json,
        "created_at": event.created_at.isoformat(),
    }
    errors = bq.insert_rows_json(table, [row])
    if errors:
        logger.warning("BQ append_event errors: %s", errors)


def get_run(run_id: str, bq: Any, *, project: str, dataset: str) -> Optional[PipelineRun]:
    sql = f"SELECT * FROM `{project}.{dataset}.pipeline_runs` WHERE run_id = @run_id LIMIT 1"
    job_config = bq_module.QueryJobConfig(
        query_parameters=[bq_module.ScalarQueryParameter("run_id", "STRING", run_id)]
    )
    rows = list(bq.query(sql, job_config=job_config).result())
    return _row_to_run(rows[0]) if rows else None


def list_runs(bq: Any, *, project: str, dataset: str, limit: int = 50) -> list[PipelineRun]:
    sql = (
        f"SELECT * FROM `{project}.{dataset}.pipeline_runs` "
        f"ORDER BY created_at DESC LIMIT {int(limit)}"
    )
    return [_row_to_run(r) for r in bq.query(sql).result()]


def get_events(run_id: str, bq: Any, *, project: str, dataset: str) -> list[RunEvent]:
    sql = (
        f"SELECT * FROM `{project}.{dataset}.pipeline_run_events` "
        f"WHERE run_id = @run_id ORDER BY created_at ASC"
    )
    job_config = bq_module.QueryJobConfig(
        query_parameters=[bq_module.ScalarQueryParameter("run_id", "STRING", run_id)]
    )
    return [_row_to_event(r) for r in bq.query(sql, job_config=job_config).result()]


def _row_to_run(row: Any) -> PipelineRun:
    r = dict(row)
    return PipelineRun(
        run_id=r["run_id"],
        status=RunStatus(r["status"]),
        triggered_by=r.get("triggered_by") or "",
        trigger_source=r.get("trigger_source") or "",
        jobs_path=r.get("jobs_path") or "",
        config_path=r.get("config_path") or "",
        created_at=r["created_at"],
        started_at=r.get("started_at"),
        finished_at=r.get("finished_at"),
        total_jobs=r.get("total_jobs"),
        passed_filter=r.get("passed_filter"),
        ranked=r.get("ranked"),
        cvs_generated=r.get("cvs_generated"),
        error_message=r.get("error_message"),
        error_stage=r.get("error_stage"),
        effective_settings_json=r.get("effective_settings_json"),
        jobs_input_source=r.get("jobs_input_source"),
        jobs_input_json=r.get("jobs_input_json"),
        candidate_profile_source=r.get("candidate_profile_source"),
        candidate_profile_json=r.get("candidate_profile_json"),
    )


def _row_to_event(row: Any) -> RunEvent:
    r = dict(row)
    return RunEvent(
        run_id=r["run_id"],
        event_id=r["event_id"],
        stage=r["stage"],
        level=r["level"],
        message=r["message"],
        created_at=r["created_at"],
        payload_json=r.get("payload_json"),
    )


def list_cvs_for_run(run_id: str, bq: Any, *, project: str, dataset: str) -> list[dict[str, Any]]:
    table = f"{project}.{dataset}.cv_versions"
    sql = f"""
        SELECT version_id, job_url, fit_classification, generated_at
        FROM `{table}`
        WHERE run_id = @run_id
        ORDER BY generated_at DESC
    """
    job_config = bq_module.QueryJobConfig(
        query_parameters=[
            bq_module.ScalarQueryParameter("run_id", "STRING", run_id),
        ],
        use_query_cache=False,
    )
    rows = bq.query(sql, job_config=job_config).result()
    return [dict(row.items()) for row in rows]


def get_cv_markdown(version_id: str, bq: Any, *, project: str, dataset: str) -> Optional[str]:
    table = f"{project}.{dataset}.cv_versions"
    sql = f"""
        SELECT cv_markdown
        FROM `{table}`
        WHERE version_id = @version_id
        LIMIT 1
    """
    job_config = bq_module.QueryJobConfig(
        query_parameters=[
            bq_module.ScalarQueryParameter("version_id", "STRING", version_id),
        ],
        use_query_cache=False,
    )
    rows = list(bq.query(sql, job_config=job_config).result())
    if not rows:
        return None
    return rows[0]["cv_markdown"]


def list_run_structured_jobs(
    run_id: str,
    bq: Any,
    *,
    project: str,
    dataset: str,
) -> list[dict[str, Any]]:
    """Return run-scoped enriched job rows for the given run_id.

    Rows are returned as plain dicts and ordered by title, job_url for
    deterministic display. Uses parameterized SQL to avoid injection.
    """
    table = f"{project}.{dataset}.run_structured_jobs"
    sql = f"""
        SELECT *
        FROM `{table}`
        WHERE run_id = @run_id
        ORDER BY title, job_url
    """
    job_config = bq_module.QueryJobConfig(
        query_parameters=[
            bq_module.ScalarQueryParameter("run_id", "STRING", run_id),
        ],
        use_query_cache=False,
    )
    rows = bq.query(sql, job_config=job_config).result()
    return [dict(row.items()) for row in rows]


def list_filter_results_for_run(
    run_id: str,
    bq: Any,
    *,
    project: str,
    dataset: str,
) -> list[dict[str, Any]]:
    """Return run-scoped filter results for a given run_id.

    Rows include job_url, passed (bool), reasons (repeated string), and run_id.
    Ordered by job_url for deterministic display. Uses parameterized SQL.
    """
    table = f"{project}.{dataset}.rule_filter_results"
    sql = f"""
        SELECT job_url, passed, reasons, run_id, filtered_at
        FROM `{table}`
        WHERE run_id = @run_id
        ORDER BY job_url
    """
    job_config = bq_module.QueryJobConfig(
        query_parameters=[
            bq_module.ScalarQueryParameter("run_id", "STRING", run_id),
        ],
        use_query_cache=False,
    )
    rows = bq.query(sql, job_config=job_config).result()
    return [dict(row.items()) for row in rows]
