"""@meta
name: ai_score
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.ai_score.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import json
import hashlib
import logging
import math
import os
import re
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from fitcv.config import (
    get_prompt_replacement,
    get_prompt_replacement_metadata,
    get_ranking_ai_score_model,
    get_ranking_prompt_id,
    get_stage_runtime_concurrency,
    resolve_model_routing_part,
)
from fitcv.contracts import RANKING_AI_SCORE_PROMPT_SCHEMA_VERSION
from fitcv.llm_runtime import (
    LlmAdapter,
    LlmAdapterResponse,
    LlmRuntimeFailure,
    LlmRuntimeResult,
    LlmTaskRequest,
    LlmValidationResult,
    execute_llm_task,
    project_llm_runtime_evidence,
)
from fitcv.runtime_routing import resolve_llm_routing
from fitcv.persistence import get_local_sqlite_path
from fitcv.pipeline_stages.common import job_identity_keys
from fitcv.evidence import project_candidate_evidence
from fitcv.candidate import flatten_skills
from fitcv.prompts import render_prompt
from fitcv.ranking_contract import (
    SCORE_STATUS_INVALID,
    SCORE_STATUS_UNSCORED,
    SCORE_STATUS_VALID,
    VALID_FIT_LABELS,
)

logger = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────────────────
def _stable_json_fingerprint(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def build_ai_score_contract_fingerprint(config: dict[str, Any]) -> dict[str, Any]:
    customization = get_prompt_replacement_metadata("ranking_ai_score", config)
    model = get_ranking_ai_score_model(config)
    try:
        provider = str(resolve_model_routing_part("ranking_ai_score", model_fallback=model).get("provider") or "fitcv_builtin")
    except Exception:
        provider = "fitcv_builtin"
    payload = {
        "ai_score_model": get_ranking_ai_score_model(config),
        "provider": provider,
        "prompt_schema_version": RANKING_AI_SCORE_PROMPT_SCHEMA_VERSION,
        "prompt_id": get_ranking_prompt_id(config),
        "prompt_customized": customization["customized"],
        "prompt_replacement_sha256": customization["replacement_sha256"],
        "prompt_replacement_char_count": customization["replacement_char_count"],
    }
    return {
        "payload": payload,
        "fingerprint": _stable_json_fingerprint(payload),
    }


def build_ai_score_input_fingerprint(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[str],
    config: dict[str, Any],
    *,
    ranking_input: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from fitcv.embeddings import build_job_summary_text

    prompt = build_scoring_prompt(
        jd_summary=(ranking_input or {}).get("job_requirements") or build_job_summary_text(job),
        candidate_summary=(ranking_input or {}).get("candidate_summary") or candidate_summary,
        top_evidence=(ranking_input or {}).get("candidate_evidence") or top_evidence[:2],
        config=config,
    )
    contract_record = build_ai_score_contract_fingerprint(config)
    payload = {
        "job_url": str(job.get("job_url") or ""),
        "prompt": prompt,
        "ranking_input": ranking_input or {},
        "contract_fingerprint": contract_record["fingerprint"],
    }
    return {
        "payload": payload,
        "fingerprint": _stable_json_fingerprint(payload),
    }


# ── prompt construction ────────────────────────────────────────────────────────

def build_scoring_prompt(
    jd_summary: str,
    candidate_summary: str,
    top_evidence: list[str],
    *,
    config: dict[str, Any] | None = None,
) -> str:
    """Build the structured reranking prompt for one job.

    Inputs:
        jd_summary        : labelled-section text from build_job_summary_text()
        candidate_summary : brief candidate paragraph (skills, experience level)
        top_evidence      : optional top 0-2 candidate evidence chunk_text strings

    Returns:
        A prompt string with rubric embedded. Model must return JSON only.
    """
    evidence_section = ""
    if top_evidence:
        bullets = "\n".join(f"  - {e}" for e in top_evidence)
        evidence_section = f"\n\nTop matched candidate evidence:\n{bullets}"
    prompt_id = get_ranking_prompt_id(config or {})
    return render_prompt(
        prompt_id,
        {
            "jd_summary": jd_summary,
            "candidate_summary": candidate_summary,
            "evidence_section": evidence_section,
        },
        replacement_text=get_prompt_replacement("ranking_ai_score", config),
    ).text


# ── response parsing ──────────────────────────────────────────────────────────


def build_ranking_job_input(job: dict[str, Any], profile: dict[str, Any]) -> dict[str, Any]:
    """Build bounded ranking-only input; retrieval projection stays separate."""
    def bounded(values: Any, limit: int = 8) -> list[str]:
        return [str(value).strip() for value in list(values or [])[:limit] if str(value).strip()]

    evidence = [{
        "evidence_id": str(item.get("evidence_id") or ""),
        "kind": str(item.get("kind") or ""),
        "title": str(item.get("title") or "")[:160],
        "text": str(item.get("text") or "")[:400],
        "source_section": str(item.get("source_section") or ""),
        "parent_id": str(item.get("parent_id") or ""),
    } for item in project_candidate_evidence(profile)[:2]]
    requirements = {
        "title": str(job.get("title") or "")[:160],
        "required_skills": bounded(job.get("required_skills_canonical") or job.get("required_skills")),
        "preferred_skills": bounded(job.get("preferred_skills_canonical") or job.get("preferred_skills")),
        "seniority": str(job.get("seniority") or ""),
        "job_family": str(job.get("job_family") or ""),
        "domain": str(job.get("domain") or ""),
        "responsibilities": bounded(job.get("responsibilities")),
        "language_requirements": bounded(job.get("language_requirements") or job.get("languages")),
        "location": {"location_type": str(job.get("location_type") or ""), "actual_location": job.get("actual_location") or job.get("location") or None},
    }
    candidate = {
        "skills": bounded(flatten_skills(profile)),
        "years_experience": profile.get("years_experience"),
        "target_role": str((profile.get("preferences") or {}).get("target_role") or ""),
    }
    return {
        "job_requirements": json.dumps(requirements, ensure_ascii=False, sort_keys=True),
        "candidate_summary": json.dumps(candidate, ensure_ascii=False, sort_keys=True),
        "candidate_evidence": evidence,
    }


def parse_score_response(response_text: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse and validate the model's JSON scoring response.

    Handles:
    - Valid JSON
    - Markdown-fenced JSON (```json ... ```)
    - Legacy fit_label → retained only as migration diagnostics
    - Score must be finite and within [0, 1]
    - Malformed JSON → explicit invalid score state

    Returns:
        Dict with score fields plus optional legacy label diagnostics.
    """
    _defaults: dict[str, Any] = {
        "ai_score": None,
        "legacy_model_fit_label": None,
        "score_reasoning": "",
        "matched_strengths": [],
        "key_risks": [],
        "score_status": SCORE_STATUS_INVALID,
        "failure_code": None,
    }

    def _failure(code: str, reasoning: str) -> dict[str, Any]:
        failed = _defaults.copy()
        failed["score_reasoning"] = reasoning
        failed["parser_status"] = code
        failed["failure_code"] = code
        return failed

    # Strip markdown fences if present
    text = response_text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("parse_score_response: malformed JSON — returning defaults")
        return _failure("malformed_json", "Scoring response parse failure: malformed_json")

    if not isinstance(data, dict):
        return _failure("non_object_payload", "Scoring response parse failure: non_object_payload")

    if "ai_score" not in data or data.get("ai_score") is None:
        return _failure("missing_ai_score", "Scoring response parse failure: missing_ai_score")
    try:
        raw_score = float(data["ai_score"])
    except (TypeError, ValueError):
        return _failure("invalid_ai_score", "Scoring response parse failure: invalid_ai_score")
    if not math.isfinite(raw_score) or not 0.0 <= raw_score <= 1.0:
        return _failure("invalid_ai_score", "Scoring response parse failure: invalid_ai_score")
    legacy_label = str(data.get("fit_label") or "").lower().strip()
    missing_fields = [
        field for field in ("score_reasoning", "matched_strengths", "key_risks")
        if field not in data
    ]

    return {
        "ai_score":          raw_score,
        "legacy_model_fit_label": legacy_label if legacy_label in VALID_FIT_LABELS else None,
        "score_reasoning":   str(data.get("score_reasoning", "")),
        "matched_strengths": list(data.get("matched_strengths", []) or []),
        "key_risks":         list(data.get("key_risks", []) or []),
        "score_status":      SCORE_STATUS_VALID,
        "failure_code":      None,
        "missing_fields":    missing_fields,
        "parser_status":     "ok",
    }


# ── integration: score one job ────────────────────────────────────────────────

def _execute_ranking_runtime(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[str],
    config: dict[str, Any],
    *,
    adapter: LlmAdapter | None = None,
) -> LlmRuntimeResult:
    from fitcv.embeddings import build_job_summary_text

    prompt = build_scoring_prompt(
        jd_summary=build_job_summary_text(job),
        candidate_summary=candidate_summary,
        top_evidence=top_evidence[:2],
        config=config,
    )
    request = LlmTaskRequest(
        routing_part="ranking_ai_score",
        prompt=prompt,
        response_mode="json_object",
    )

    def _parser(response: LlmAdapterResponse) -> dict[str, Any]:
        return parse_score_response(response.raw_text, config=config)

    def _validator(value: Any) -> LlmValidationResult:
        required_fields = {
            "ai_score",
            "legacy_model_fit_label",
            "score_reasoning",
            "matched_strengths",
            "key_risks",
            "parser_status",
            "score_status",
            "failure_code",
        }
        errors: list[str] = []
        if not isinstance(value, dict) or not required_fields.issubset(value):
            errors.append("Ranking parser returned invalid contract.")
        elif value.get("score_status") != SCORE_STATUS_VALID:
            errors.append(f"Ranking score is {value.get('score_status')!r}.")
        elif not isinstance(value.get("ai_score"), (int, float)) or isinstance(value.get("ai_score"), bool):
            errors.append("Ranking parser returned no finite numeric ai_score.")
        elif not math.isfinite(float(value["ai_score"])) or not 0.0 <= float(value["ai_score"]) <= 1.0:
            errors.append("Ranking parser returned ai_score outside [0.0, 1.0].")
        missing_fields = list(value.get("missing_fields") or []) if isinstance(value, dict) else []
        if missing_fields:
            errors.append(f"Ranking response missing required fields: {missing_fields}.")
        is_valid = not errors
        return LlmValidationResult(
            valid=is_valid,
            errors=errors,
            details={},
        )

    return execute_llm_task(
        request,
        parser=_parser,
        validator=_validator,
        adapter=adapter,
        resolved_route=resolve_llm_routing("ranking_ai_score", runtime_config=config),
    )


def _ranking_result_to_row(job: dict[str, Any], result: LlmRuntimeResult) -> dict[str, Any]:
    value = dict(result.parsed_value) if isinstance(result.parsed_value, dict) else {}
    failure = result.failure
    if result.status != "succeeded" or failure is not None:
        if failure is None:
            failure = LlmRuntimeFailure(
                stage="validate",
                code="validation_error",
                message="Ranking runtime returned no parsed value.",
            )
        if failure.stage in {"adapter", "routing"}:
            score_status = SCORE_STATUS_UNSCORED
            failure_code = "timeout" if failure.code == "adapter_timeout" else "provider_failure"
        elif failure.stage == "parse":
            score_status = SCORE_STATUS_INVALID
            failure_code = str(value.get("failure_code") or "parser_failure")
        else:
            score_status = SCORE_STATUS_INVALID
            failure_code = str(value.get("failure_code") or "validation_failure")
        value.update(
            {
                "ai_score": None,
                "score_status": score_status,
                "failure_code": failure_code,
                "score_reasoning": str(value.get("score_reasoning") or failure.message),
                "matched_strengths": list(value.get("matched_strengths") or []),
                "key_risks": list(value.get("key_risks") or []),
                "legacy_model_fit_label": None,
                "parser_status": str(value.get("parser_status") or failure.code),
                "retry_eligible": score_status == SCORE_STATUS_UNSCORED,
            }
        )
    else:
        value["retry_eligible"] = False
    value["job_url"] = str(job.get("job_url", ""))
    return value


def score_job(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Score one job through shared LLM runtime."""
    return _ranking_result_to_row(
        job,
        _execute_ranking_runtime(job, candidate_summary, top_evidence, config),
    )


# ── integration: score shortlist ─────────────────────────────────────────────

def run_ai_scoring(
    shortlist: list[dict[str, Any]],
    candidate_summary: str,
    config: dict[str, Any],
    top_n: int | None = None,
    *,
    runtime_observation_callback: Callable[[dict[str, Any]], None] | None = None,
    ranking_inputs: dict[str, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Score at most top_n shortlisted jobs.

    top_n defaults to config["pipeline"]["ai_score_top_n"] (50 if missing).
    shortlist: list of job dicts from VECTOR_SEARCH (must include job_url and
               structured JD fields). Each item may optionally include
               "top_evidence" (list[str]).

    Requires routed OpenAI-compatible provider config and API key.
    """
    effective_top_n = (
        top_n
        if top_n is not None
        else int((config.get("pipeline") or {}).get("ai_score_top_n") or config.get("rerank_top_n", 50))
    )
    ranking_concurrency = get_stage_runtime_concurrency(
        config,
        stage="ranking",
        default=1,
    )
    selected_jobs = shortlist[:effective_top_n]

    def _score_single(input_index: int, job: dict[str, Any]) -> dict[str, Any]:
        ranking_input = dict((ranking_inputs or {}).get(str(job.get("job_url") or "")) or job.get("ranking_input") or {})
        top_evidence = list(ranking_input.get("candidate_evidence") or job.get("top_evidence", []) or [])[:2]
        scoring_candidate_summary = str(ranking_input.get("candidate_summary") or candidate_summary)
        try:
            if runtime_observation_callback is None:
                return score_job(
                    job=job,
                    candidate_summary=scoring_candidate_summary,
                    top_evidence=top_evidence,
                    config=config,
                )
            result = _execute_ranking_runtime(job, candidate_summary, top_evidence, config)
            identity_keys = job_identity_keys(job)
            runtime_observation_callback(
                {
                    "contract_version": "llm_runtime_observation_v1",
                    "scope_key": str(
                        job.get("raw_job_fingerprint")
                        or (identity_keys[0] if identity_keys else "")
                    ),
                    "input_index": input_index,
                    "invocation_index": 1,
                    "evidence": project_llm_runtime_evidence(result),
                }
            )
            return _ranking_result_to_row(job, result)
        except Exception as exc:  # noqa: BLE001
            return {
                "job_url": str(job.get("job_url", "")),
                "ai_score": None, "legacy_model_fit_label": None,
                "score_status": SCORE_STATUS_UNSCORED,
                "failure_code": "provider_failure",
                "retry_eligible": True,
                "score_reasoning": f"Scoring error: {exc}",
                "matched_strengths": [], "key_risks": [],
                "parser_status": "runtime_exception",
            }

    scored_by_index: dict[int, dict[str, Any]] = {}
    if ranking_concurrency <= 1:
        for index, job in enumerate(selected_jobs):
            scored_by_index[index] = _score_single(index, job)
    else:
        with ThreadPoolExecutor(max_workers=ranking_concurrency) as executor:
            future_to_index = {
                executor.submit(_score_single, index, job): index
                for index, job in enumerate(selected_jobs)
            }
            for future in as_completed(future_to_index):
                scored_by_index[future_to_index[future]] = future.result()

    scored: list[dict[str, Any]] = []
    for i in range(len(selected_jobs)):
        scored.append(scored_by_index[i])

    return scored


# ── integration: persist scores ───────────────────────────────────────────────



def _ensure_local_ai_score_results_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS ai_score_results (
            job_url TEXT PRIMARY KEY,
            ai_score REAL NOT NULL,
            fit_label TEXT NOT NULL,
            score_reasoning TEXT NOT NULL,
            matched_strengths_json TEXT NOT NULL,
            key_risks_json TEXT NOT NULL,
            scored_at TEXT NOT NULL
        )
        """
    )
    conn.commit()



def store_ai_scores(
    scores: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert AI scoring results into local sqlite store."""
    scores = [
        score for score in scores
        if str(score.get("score_status") or SCORE_STATUS_VALID) == SCORE_STATUS_VALID
        and score.get("ai_score") is not None
    ]
    if not scores:
        return

    now = datetime.now(tz=timezone.utc).isoformat()
    db_path = Path(get_local_sqlite_path())
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        _ensure_local_ai_score_results_table(conn)
        conn.executemany(
            """
            INSERT INTO ai_score_results(
                job_url,
                ai_score,
                fit_label,
                score_reasoning,
                matched_strengths_json,
                key_risks_json,
                scored_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_url) DO UPDATE SET
                ai_score = excluded.ai_score,
                fit_label = excluded.fit_label,
                score_reasoning = excluded.score_reasoning,
                matched_strengths_json = excluded.matched_strengths_json,
                key_risks_json = excluded.key_risks_json,
                scored_at = excluded.scored_at
            """,
            [
                (
                    str(score["job_url"]),
                    float(score["ai_score"]),
                    str(score.get("legacy_model_fit_label") or ""),
                    str(score.get("score_reasoning") or ""),
                    json.dumps(list(score.get("matched_strengths") or []), ensure_ascii=False),
                    json.dumps(list(score.get("key_risks") or []), ensure_ascii=False),
                    now,
                )
                for score in scores
            ],
        )
        conn.commit()

