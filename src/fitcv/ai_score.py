"""AI reranking for the vector shortlist using Vertex AI (ML.GENERATE_TEXT).

v1 design:
- Shortlist-only: only re-rank top 20-50 jobs from VECTOR_SEARCH
- Primary path: Python Vertex AI call (not BigQuery AI.SCORE)
- Evidence-grounded: each job prompt includes top matched evidence chunks

Scoring rubric (enforced in prompt):
- Score 0.0 (no fit) → 1.0 (perfect fit)
- Heavily weight: required skills coverage
- Penalise: missing core technologies, seniority mismatch, years-of-experience gap
- Reward: strong project evidence matching JD, domain relevance
- Classify: strong (>=0.7), stretch (0.4-0.69), skip (<0.4)
- Return JSON only, no prose

Public API
----------
build_scoring_prompt  : build structured prompt (pure, no marker)
parse_score_response  : parse + validate model JSON response (pure, no marker)
score_job             : call Vertex AI + parse (integration)
run_ai_scoring        : score at most top_n shortlisted jobs (integration)
store_ai_scores       : persist to fitcv.ai_score_results (integration)
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

# ── constants ─────────────────────────────────────────────────────────────────

_VALID_FIT_LABELS = frozenset({"strong", "stretch", "skip"})

_SCORING_RUBRIC = """\
Score the candidate-to-job match using this rubric:
- Score from 0.0 (no fit) to 1.0 (perfect fit)
- Heavily weight: required skills coverage
- Penalise: missing core technologies, seniority mismatch, years-of-experience gap
- Reward: strong project evidence matching JD requirements, domain relevance
- Classify into exactly one fit_label:
    strong  (ai_score >= 0.7)
    stretch (ai_score 0.4 – 0.69)
    skip    (ai_score < 0.4)
Return a JSON object ONLY — no prose, no markdown fences:
{
  "ai_score": <float 0.0–1.0>,
  "fit_label": "<strong|stretch|skip>",
  "score_reasoning": "<one-sentence explanation>",
  "matched_strengths": ["<strength 1>", ...],
  "key_risks": ["<risk 1>", ...]
}"""


# ── prompt construction ────────────────────────────────────────────────────────

def build_scoring_prompt(
    jd_summary: str,
    candidate_summary: str,
    top_evidence: list[str],
) -> str:
    """Build the structured reranking prompt for one job.

    Inputs:
        jd_summary        : labelled-section text from build_job_summary_text()
        candidate_summary : brief candidate paragraph (skills, experience level)
        top_evidence      : top 0-2 candidate evidence chunk_text strings

    Returns:
        A prompt string with rubric embedded. Model must return JSON only.
    """
    evidence_section = ""
    if top_evidence:
        bullets = "\n".join(f"  - {e}" for e in top_evidence)
        evidence_section = f"\n\nTop matched candidate evidence:\n{bullets}"

    return (
        f"## Job Description\n{jd_summary}\n\n"
        f"## Candidate Profile\n{candidate_summary}"
        f"{evidence_section}\n\n"
        f"## Scoring Rubric\n{_SCORING_RUBRIC}"
    )


# ── response parsing ──────────────────────────────────────────────────────────

def _fit_label_from_score(score: float, config: dict[str, Any] | None = None) -> str:
    """Derive fit_label from numeric score using thresholds from config or defaults."""
    thresholds = {}
    if config:
        thresholds = config.get("fit_label_thresholds", {}) or {}
    strong_threshold = float(thresholds.get("strong", 0.70))
    stretch_threshold = float(thresholds.get("stretch", 0.40))
    if score >= strong_threshold:
        return "strong"
    if score >= stretch_threshold:
        return "stretch"
    return "skip"


def parse_score_response(response_text: str) -> dict[str, Any]:
    """Parse and validate the model's JSON scoring response.

    Handles:
    - Valid JSON
    - Markdown-fenced JSON (```json ... ```)
    - Missing fit_label → derived from ai_score
    - Unknown fit_label → mapped to "skip"
    - Score outside [0, 1] → clamped
    - Malformed JSON → safe defaults (ai_score=0.0, fit_label="skip")

    Returns:
        Dict with keys: ai_score, fit_label, score_reasoning,
                        matched_strengths, key_risks
    """
    _defaults: dict[str, Any] = {
        "ai_score": 0.0,
        "fit_label": "skip",
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
        return _defaults.copy()

    if not isinstance(data, dict):
        return _defaults.copy()

    # Clamp ai_score to [0.0, 1.0]
    raw_score = float(data.get("ai_score", 0.0))
    ai_score = max(0.0, min(1.0, raw_score))

    # Validate / derive fit_label
    fit_label = str(data.get("fit_label", "")).lower().strip()
    if fit_label not in _VALID_FIT_LABELS:
        fit_label = _fit_label_from_score(ai_score, config=None)

    return {
        "ai_score":          ai_score,
        "fit_label":         fit_label,
        "score_reasoning":   str(data.get("score_reasoning", "")),
        "matched_strengths": list(data.get("matched_strengths", []) or []),
        "key_risks":         list(data.get("key_risks", []) or []),
    }


# ── integration: score one job ────────────────────────────────────────────────

def score_job(
    job: dict[str, Any],
    candidate_summary: str,
    top_evidence: list[str],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Call Vertex AI ML.GENERATE_TEXT for one job and return a parsed score.

    The model receives:
    - JD summary (built from job fields)
    - Candidate summary paragraph
    - Top 2 matched evidence snippets

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    """
    import vertexai  # type: ignore[import-untyped]
    from vertexai.generative_models import GenerativeModel  # type: ignore[import-untyped]
    from fitcv.embeddings import build_job_summary_text

    vertexai.init(
        project=str(config["gcp_project"]),
        location=str(config.get("location", "us-central1")),
    )

    jd_summary = build_job_summary_text(job)
    prompt = build_scoring_prompt(
        jd_summary=jd_summary,
        candidate_summary=candidate_summary,
        top_evidence=top_evidence[:2],
    )

    model_name = str(config.get("gemini_model", "gemini-2.0-flash"))
    model = GenerativeModel(model_name)
    response = model.generate_content(prompt)
    raw_text = response.text

    result = parse_score_response(raw_text)
    result["job_url"] = str(job.get("job_url", ""))
    return result


# ── integration: batch score shortlist ───────────────────────────────────────

def run_ai_scoring(
    shortlist: list[dict[str, Any]],
    candidate_summary: str,
    config: dict[str, Any],
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Score at most top_n shortlisted jobs.

    top_n defaults to config["rerank_top_n"] (50 if missing).
    sleep between calls is config["rerank_sleep_secs"] (0.5 if missing).

    shortlist: list of job dicts from VECTOR_SEARCH (must include job_url and
               structured JD fields). Each item may include "top_evidence" (list[str]).

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    """
    import time

    effective_top_n = top_n if top_n is not None else int(config.get("rerank_top_n", 50))
    sleep_secs = float(config.get("rerank_sleep_secs", 0.5))
    scored: list[dict[str, Any]] = []
    for i, job in enumerate(shortlist[:effective_top_n]):
        top_evidence = list(job.get("top_evidence", []) or [])[:2]
        try:
            result = score_job(
                job=job,
                candidate_summary=candidate_summary,
                top_evidence=top_evidence,
                config=config,
            )
            scored.append(result)
        except Exception as exc:  # noqa: BLE001
            scored.append({
                "job_url": str(job.get("job_url", "")),
                "ai_score": 0.0, "fit_label": "skip",
                "score_reasoning": f"Scoring error: {exc}",
                "matched_strengths": [], "key_risks": [],
            })
        if i < len(shortlist[:effective_top_n]) - 1:
            time.sleep(sleep_secs)

    return scored


# ── integration: persist scores ───────────────────────────────────────────────

def store_ai_scores(
    scores: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert AI scoring results into fitcv.ai_score_results.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    if not scores:
        return

    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.ai_score_results"
    now = datetime.now(tz=timezone.utc).isoformat()

    rows = [
        {
            "job_url":           s["job_url"],
            "ai_score":          s["ai_score"],
            "fit_label":         s["fit_label"],
            "score_reasoning":   s.get("score_reasoning", ""),
            "matched_strengths": s.get("matched_strengths", []),
            "key_risks":         s.get("key_risks", []),
            "scored_at":         now,
        }
        for s in scores
    ]

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors for ai_score_results: {errors}")
