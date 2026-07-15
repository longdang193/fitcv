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
    get_ranking_ai_score_model,
    get_ranking_prompt_id,
    get_stage_runtime_concurrency,
    get_stage_runtime_sleep_secs,
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
from fitcv.persistence import get_local_sqlite_path
from fitcv.pipeline_stages.common import job_identity_keys
from fitcv.prompts import render_prompt
from fitcv.ranking_contract import VALID_FIT_LABELS

logger = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────────────────
def _stable_json_fingerprint(payload: dict[str, Any]) -> str:
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload_json.encode("utf-8")).hexdigest()


def build_ai_score_contract_fingerprint(config: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "ai_score_model": get_ranking_ai_score_model(config),
        "prompt_schema_version": RANKING_AI_SCORE_PROMPT_SCHEMA_VERSION,
        "prompt_id": get_ranking_prompt_id(config),
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
) -> dict[str, Any]:
    from fitcv.embeddings import build_job_summary_text

    prompt = build_scoring_prompt(
        jd_summary=build_job_summary_text(job),
        candidate_summary=candidate_summary,
        top_evidence=top_evidence[:2],
        config=config,
    )
    contract_record = build_ai_score_contract_fingerprint(config)
    payload = {
        "job_url": str(job.get("job_url") or ""),
        "prompt": prompt,
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
    ).text


# ── response parsing ──────────────────────────────────────────────────────────


def parse_score_response(response_text: str, config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Parse and validate the model's JSON scoring response.

    Handles:
    - Valid JSON
    - Markdown-fenced JSON (```json ... ```)
    - Legacy fit_label → retained only as migration diagnostics
    - Score outside [0, 1] → clamped
    - Malformed JSON → safe score defaults

    Returns:
        Dict with score fields plus optional legacy label diagnostics.
    """
    _defaults: dict[str, Any] = {
        "ai_score": 0.0,
        "legacy_model_fit_label": None,
        "score_reasoning": "",
        "matched_strengths": [],
        "key_risks": [],
    }

    # Strip markdown fences if present
    text = response_text.strip()
    fence_match = re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        data = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        logger.warning("parse_score_response: malformed JSON — returning defaults")
        failed = _defaults.copy()
        failed["score_reasoning"] = "Scoring response parse failure: malformed_json"
        failed["parser_status"] = "malformed_json"
        return failed

    if not isinstance(data, dict):
        failed = _defaults.copy()
        failed["score_reasoning"] = "Scoring response parse failure: non_object_payload"
        failed["parser_status"] = "non_object_payload"
        return failed

    # Clamp ai_score to [0.0, 1.0]
    try:
        raw_score = float(data.get("ai_score", 0.0))
    except (TypeError, ValueError):
        failed = _defaults.copy()
        failed["score_reasoning"] = "Scoring response parse failure: invalid_ai_score"
        failed["parser_status"] = "invalid_ai_score"
        return failed
    if not math.isfinite(raw_score):
        failed = _defaults.copy()
        failed["score_reasoning"] = "Scoring response parse failure: invalid_ai_score"
        failed["parser_status"] = "invalid_ai_score"
        return failed
    ai_score = max(0.0, min(1.0, raw_score))
    legacy_label = str(data.get("fit_label") or "").lower().strip()

    return {
        "ai_score":          ai_score,
        "legacy_model_fit_label": legacy_label if legacy_label in VALID_FIT_LABELS else None,
        "score_reasoning":   str(data.get("score_reasoning", "")),
        "matched_strengths": list(data.get("matched_strengths", []) or []),
        "key_risks":         list(data.get("key_risks", []) or []),
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
        is_valid = isinstance(value, dict) and {
            "ai_score",
            "legacy_model_fit_label",
            "score_reasoning",
            "matched_strengths",
            "key_risks",
            "parser_status",
        }.issubset(value)
        return LlmValidationResult(
            valid=is_valid,
            errors=[] if is_valid else ["Ranking parser returned invalid contract."],
            details={},
        )

    return execute_llm_task(
        request,
        parser=_parser,
        validator=_validator,
        adapter=adapter,
    )


def _ranking_result_to_row(job: dict[str, Any], result: LlmRuntimeResult) -> dict[str, Any]:
    if result.status != "succeeded" or not isinstance(result.parsed_value, dict):
        failure = result.failure or LlmRuntimeFailure(
            stage="validate",
            code="validation_error",
            message="Ranking runtime returned no parsed value.",
        )
        raise RuntimeError(failure.message)

    value = dict(result.parsed_value)
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


# ── integration: batch score shortlist ───────────────────────────────────────

def run_ai_scoring(
    shortlist: list[dict[str, Any]],
    candidate_summary: str,
    config: dict[str, Any],
    top_n: int | None = None,
    *,
    runtime_observation_callback: Callable[[dict[str, Any]], None] | None = None,
) -> list[dict[str, Any]]:
    """Score at most top_n shortlisted jobs.

    top_n defaults to config["pipeline"]["ai_score_top_n"] (50 if missing).
    sleep between calls prefers config["stage_runtime"]["ranking"]["sleep_secs"].
    Falls back to config["rerank_sleep_secs"] (0.5 if missing).

    shortlist: list of job dicts from VECTOR_SEARCH (must include job_url and
               structured JD fields). Each item may optionally include
               "top_evidence" (list[str]).

    Requires routed OpenAI-compatible provider config and API key.
    """
    import time

    effective_top_n = (
        top_n
        if top_n is not None
        else int((config.get("pipeline") or {}).get("ai_score_top_n") or config.get("rerank_top_n", 50))
    )
    sleep_secs = get_stage_runtime_sleep_secs(
        config,
        stage="ranking",
        default=0.5,
        compatibility_fallback_key="rerank_sleep_secs",
    )
    ranking_concurrency = get_stage_runtime_concurrency(
        config,
        stage="ranking",
        default=1,
    )
    selected_jobs = shortlist[:effective_top_n]

    def _score_single(input_index: int, job: dict[str, Any]) -> dict[str, Any]:
        top_evidence = list(job.get("top_evidence", []) or [])[:2]
        try:
            if runtime_observation_callback is None:
                return score_job(
                    job=job,
                    candidate_summary=candidate_summary,
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
                "ai_score": 0.0, "legacy_model_fit_label": None,
                "score_reasoning": f"Scoring error: {exc}",
                "matched_strengths": [], "key_risks": [],
                "parser_status": "runtime_exception",
            }

    scored_by_index: dict[int, dict[str, Any]] = {}
    if ranking_concurrency <= 1:
        for i, job in enumerate(selected_jobs):
            scored_by_index[i] = _score_single(i, job)
            if i < len(selected_jobs) - 1:
                time.sleep(sleep_secs)
    else:
        with ThreadPoolExecutor(max_workers=ranking_concurrency) as executor:
            futures: dict[Any, int] = {}
            for i, job in enumerate(selected_jobs):
                futures[executor.submit(_score_single, i, job)] = i
                if i < len(selected_jobs) - 1:
                    time.sleep(sleep_secs)
            for future in as_completed(futures):
                scored_by_index[futures[future]] = future.result()

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

