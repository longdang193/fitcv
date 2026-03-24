"""Generate and store semantic embeddings for jobs and candidate evidence.

Public API
----------
build_job_summary_text    : deterministic labelled-section text for one job
build_job_summary_chunk   : one-element list with chunk_type="job_summary"
build_candidate_chunks    : evidence chunks (one per project/bullet/achievement)
generate_embedding        : call Vertex AI text-embedding-005 (integration)
embed_and_store_jobs      : batch embed jobs → job_embeddings (integration)
embed_and_store_candidate : batch embed candidate → candidate_embeddings (integration)
"""

from datetime import datetime, timezone
from typing import Any


# ── job summary text ──────────────────────────────────────────────────────────

def build_job_summary_text(structured_jd: dict[str, Any]) -> str:
    """Build a deterministic labelled-section string for embedding.

    Format (structured text gives better embedding quality than free join):

        Title: <title>
        Required skills: <comma-joined required_skills>
        Preferred skills: <comma-joined preferred_skills>
        Responsibilities: <semicolon-joined responsibilities>
        Seniority: <seniority>
        Job family: <job_family>

    All fields are optional; missing/empty fields are omitted from the output.
    """
    parts: list[str] = []

    def _append(label: str, value: str) -> None:
        if value:
            parts.append(f"{label}: {value}")

    _append("Title", str(structured_jd.get("title", "")))
    _append(
        "Required skills",
        ", ".join(structured_jd.get("required_skills", []) or []),
    )
    _append(
        "Preferred skills",
        ", ".join(structured_jd.get("preferred_skills", []) or []),
    )
    _append(
        "Responsibilities",
        "; ".join(structured_jd.get("responsibilities", []) or []),
    )
    _append("Seniority", str(structured_jd.get("seniority", "") or ""))
    _append("Job family", str(structured_jd.get("job_family", "") or ""))

    return "\n".join(parts)


# ── job summary chunk ─────────────────────────────────────────────────────────

def build_job_summary_chunk(structured_jd: dict[str, Any]) -> list[dict[str, Any]]:
    """Return a list containing exactly one job_summary chunk.

    v1 rule: always one chunk per job used for VECTOR_SEARCH shortlist ranking.
    Named build_job_summary_chunk (not chunk_jd_by_section) to clearly
    reflect the single-chunk v1 design. Multi-chunk expansion is reserved for v2.

    Shape: [{"chunk_type": "job_summary", "chunk_text": <labelled text>}]
    """
    return [{
        "chunk_type": "job_summary",
        "chunk_text": build_job_summary_text(structured_jd),
    }]


# ── candidate evidence chunks ─────────────────────────────────────────────────

def _project_chunk_text(proj: dict[str, Any]) -> str:
    skills = ", ".join(proj.get("skills", []) or [])
    return (
        f"Project: {proj.get('name', '')}\n"
        f"Skills: {skills}\n"
        f"Business value: {proj.get('business_value', '')}"
    ).strip()


def _bullet_chunk_text(exp: dict[str, Any], bullet: dict[str, Any]) -> str:
    skills = ", ".join(bullet.get("skills", []) or [])
    impact = bullet.get("measurable_impact", "")
    text = (
        f"Role: {exp.get('role', '')} at {exp.get('company', '')}\n"
        f"Achievement: {bullet.get('text', '')}\n"
        f"Skills: {skills}"
    )
    if impact:
        text += f"\nImpact: {impact}"
    return text.strip()


def _achievement_chunk_text(ach: dict[str, Any]) -> str:
    return (
        f"Achievement: {ach.get('text', '')}\n"
        f"Category: {ach.get('category', '')}"
    ).strip()


def build_candidate_chunks(profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Build evidence chunks for candidate embedding.

    v1 granularity (explicit, not vague):
    - One chunk per project        (evidence_type = "project")
    - One chunk per experience bullet (evidence_type = "experience_bullet")
    - One chunk per achievement    (evidence_type = "achievement")

    Each chunk has this shape:
        {
            "evidence_id":   str,  # unique chunk ID (e.g. proj_1, exp_1_bullet_0)
            "source_ref_id": str,  # originating YAML ID (exp_id/proj_id/ach_id)
            "evidence_type": str,  # project | experience_bullet | achievement
            "chunk_text":    str,  # human-readable text for embedding
        }
    """
    chunks: list[dict[str, Any]] = []

    # ── projects: one chunk each ──────────────────────────────────────────────
    for proj in profile.get("projects", []):
        proj_id = str(proj.get("id", ""))
        chunks.append({
            "evidence_id":   proj_id,
            "source_ref_id": proj_id,
            "evidence_type": "project",
            "chunk_text":    _project_chunk_text(proj),
        })

    # ── experience bullets: one chunk per bullet ──────────────────────────────
    for exp in profile.get("experiences", []):
        exp_id = str(exp.get("id", ""))
        for idx, bullet in enumerate(exp.get("bullets", [])):
            chunks.append({
                "evidence_id":   f"{exp_id}_bullet_{idx}",
                "source_ref_id": exp_id,
                "evidence_type": "experience_bullet",
                "chunk_text":    _bullet_chunk_text(exp, bullet),
            })

    # ── achievements: one chunk each ──────────────────────────────────────────
    for ach in profile.get("achievements", []):
        ach_id = str(ach.get("id", ""))
        chunks.append({
            "evidence_id":   ach_id,
            "source_ref_id": ach_id,
            "evidence_type": "achievement",
            "chunk_text":    _achievement_chunk_text(ach),
        })

    return chunks


# ── integration: Vertex AI embedding ─────────────────────────────────────────

def generate_embedding(text: str, config: dict[str, Any]) -> list[float]:
    """Call Vertex AI text-embedding-005 and return the embedding vector.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Marked @pytest.mark.integration in tests.
    """
    import vertexai  # type: ignore[import-untyped]
    from fitcv.config import get_vertex_location
    from vertexai.language_models import TextEmbeddingModel  # type: ignore[import-untyped]

    vertexai.init(
        project=str(config["gcp_project"]),
        location=get_vertex_location(config),
    )
    model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    embeddings = model.get_embeddings([text])
    return embeddings[0].values  # type: ignore[return-value]


# ── integration: batch embed + store jobs ─────────────────────────────────────

def embed_and_store_jobs(
    structured_jobs: list[dict[str, Any]],
    config: dict[str, Any],
) -> int:
    """Embed each job's summary and insert into fitcv.job_embeddings.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Marked @pytest.mark.integration in tests.

    Returns:
        Number of rows inserted.
    """
    import time

    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.job_embeddings"
    now = datetime.now(tz=timezone.utc).isoformat()

    rows: list[dict[str, Any]] = []
    for i, job in enumerate(structured_jobs):
        chunk = build_job_summary_chunk(job)[0]
        vector = generate_embedding(chunk["chunk_text"], config)
        rows.append({
            "job_url":    str(job.get("job_url", "")),
            "chunk_type": chunk["chunk_type"],
            "chunk_text": chunk["chunk_text"],
            "embedding":  vector,
            "created_at": now,
        })
        if i < len(structured_jobs) - 1:
            time.sleep(0.5)  # stay within Vertex AI quota

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors for job_embeddings: {errors}")
    return len(rows)


# ── integration: batch embed + store candidate ────────────────────────────────

def embed_and_store_candidate(
    profile: dict[str, Any],
    config: dict[str, Any],
) -> int:
    """Embed candidate evidence chunks and insert into fitcv.candidate_embeddings.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Marked @pytest.mark.integration in tests.

    Returns:
        Number of rows inserted.
    """
    import time

    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])
    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.candidate_embeddings"
    now = datetime.now(tz=timezone.utc).isoformat()

    candidate_chunks = build_candidate_chunks(profile)
    rows: list[dict[str, Any]] = []

    for i, chunk in enumerate(candidate_chunks):
        vector = generate_embedding(chunk["chunk_text"], config)
        rows.append({
            "evidence_id":   chunk["evidence_id"],
            "source_ref_id": chunk["source_ref_id"],
            "evidence_type": chunk["evidence_type"],
            "chunk_text":    chunk["chunk_text"],
            "embedding":     vector,
            "created_at":    now,
        })
        if i < len(candidate_chunks) - 1:
            time.sleep(0.5)

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors for candidate_embeddings: {errors}")
    return len(rows)
