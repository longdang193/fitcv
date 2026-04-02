"""Semantic retrieval via BigQuery VECTOR_SEARCH.

v1 design (Option A — one candidate summary embedding):
- Build one candidate query text: headline + top skills + preferred domains
- Embed it with Vertex AI text-embedding-005
- Search fitcv.job_embeddings WHERE chunk_type = 'job_summary'
- Restrict to job_url IN (passed_job_urls) — the rule-filtered universe
- Return top-N results ranked by cosine similarity

Option B (multi-evidence aggregation) is deferred to v2.

Public API
----------
build_candidate_query_text : deterministic candidate query string (no embedding call)
build_vector_search_query  : BigQuery VECTOR_SEARCH SQL string
run_vector_search          : embed + query + return shortlist rows (integration)
store_shortlist            : insert into fitcv.vector_shortlist (integration)

Config keys consumed (from pipeline.yaml)
-----------------------------------------
config["vector_top_n"]              : default top_n for VECTOR_SEARCH (default 50)
config["vector_max_candidate_skills"]: max skills in candidate query text (default 15)
config["retrieval_strategy"]        : stored in vector_shortlist (default "job_summary_v1")
"""

from datetime import datetime, timezone
from typing import Any


DEFAULT_RECENT_ROLE_COUNT = 3


def _dedupe_shortlist_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep the best-ranked row per job_url, preserving shortlist order."""
    deduped: list[dict[str, Any]] = []
    seen_job_urls: set[str] = set()
    for row in rows:
        job_url = str(row.get("job_url") or "")
        if not job_url or job_url in seen_job_urls:
            continue
        seen_job_urls.add(job_url)
        deduped.append(row)
    return deduped


# ── candidate query text ──────────────────────────────────────────────────────

def build_candidate_query_text(
    profile: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> str:
    """Build the single candidate query string for v1 Option A retrieval.

    Combines: headline + target role + recent roles + top skills
    (up to vector_max_candidate_skills) + preferred domains.
    Deterministic — same profile always produces the same text.
    No embedding call; used as input to generate_embedding().

    Format:
        Candidate: <headline>
        Skills: <comma-joined skills>
        Target domains: <comma-joined domains>
    """
    max_skills = int((config or {}).get("vector_max_candidate_skills", 15))
    parts: list[str] = []

    headline = (profile.get("headline") or "").strip()
    if headline:
        parts.append(f"Candidate: {headline}")

    prefs = profile.get("preferences", {}) or {}
    target_role = str(prefs.get("target_role") or "").strip()
    if target_role:
        parts.append(f"Target role: {target_role}")

    recent_roles: list[str] = []
    for experience in profile.get("experiences", []) or []:
        role = str(experience.get("role") or "").strip()
        if role and role not in recent_roles:
            recent_roles.append(role)
        if len(recent_roles) >= DEFAULT_RECENT_ROLE_COUNT:
            break
    if recent_roles:
        parts.append(f"Recent roles: {', '.join(recent_roles)}")

    skills = profile.get("skills", []) or []
    skill_names = [str(s.get("name", "")) for s in skills if s.get("name")][:max_skills]
    if skill_names:
        parts.append(f"Skills: {', '.join(skill_names)}")

    domains = prefs.get("domains", []) or []
    if domains:
        parts.append(f"Target domains: {', '.join(str(d) for d in domains)}")

    return "\n".join(parts)


# ── VECTOR_SEARCH SQL builder ─────────────────────────────────────────────────

def build_vector_search_query(
    top_n: int,
    passed_job_urls: list[str],
    project: str = "PROJECT",
    dataset: str = "fitcv",
) -> str:
    """Return a BigQuery VECTOR_SEARCH SQL string.

    Design rules:
    - Only searches job_embeddings WHERE chunk_type = 'job_summary'
    - Only searches within the rule-filtered universe (passed_job_urls)
    - Enforces top_k = top_n
    - Returns job_url, vector_similarity (distance), vector_rank

    The caller is responsible for substituting @candidate_embedding with the
    actual embedding vector before executing.

    Args:
        top_n:            Maximum number of results to return.
        passed_job_urls:  Rule-filtered job URLs to restrict the search universe.
        project:          GCP project id (for table references).
        dataset:          BigQuery dataset name.

    Returns:
        A BigQuery SQL string (not yet executed).
    """
    temp_table_name = "_latest_job_embeddings"

    if passed_job_urls:
        url_list = ", ".join(f"'{u}'" for u in passed_job_urls)
        latest_rows_query = f"""
CREATE TEMP TABLE {temp_table_name} AS
SELECT
  job_url,
  chunk_type,
  chunk_text,
  embedding,
  created_at
FROM (
  SELECT
    job_url,
    chunk_type,
    chunk_text,
    embedding,
    created_at,
    ROW_NUMBER() OVER (
      PARTITION BY job_url
      ORDER BY created_at DESC, chunk_text DESC, job_url DESC
    ) AS rn
  FROM `{project}.{dataset}.job_embeddings`
  WHERE chunk_type = 'job_summary' AND job_url IN ({url_list})
)
WHERE rn = 1;
""".strip()
    else:
        latest_rows_query = f"""
CREATE TEMP TABLE {temp_table_name} AS
SELECT
  job_url,
  chunk_type,
  chunk_text,
  embedding,
  created_at
FROM `{project}.{dataset}.job_embeddings`
WHERE 1 = 0;
""".strip()

    return f"""
{latest_rows_query}

SELECT
  base.job_url                              AS job_url,
  1 - distance                              AS vector_similarity,
  RANK() OVER (ORDER BY distance ASC)       AS vector_rank
FROM
  VECTOR_SEARCH(
    TABLE {temp_table_name},
    'embedding',
    (SELECT @candidate_embedding AS embedding),
    top_k => {top_n},
    distance_type => 'COSINE'
  )
ORDER BY vector_rank
LIMIT {top_n}
""".strip()


# ── integration: run full retrieval pipeline ──────────────────────────────────

def run_vector_search(
    profile: dict[str, Any],
    passed_job_urls: list[str],
    config: dict[str, Any],
    top_n: int | None = None,
) -> list[dict[str, Any]]:
    """Generate candidate query embedding and execute VECTOR_SEARCH.

    top_n defaults to config["vector_top_n"] (50 if missing).

    Steps:
    1. Build candidate query text (deterministic, no embedding call)
    2. Embed it via Vertex AI text-embedding-005
    3. Execute VECTOR_SEARCH over rule-filtered job universe
    4. Return shortlist rows

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.

    Returns:
        List of dicts with: job_url, vector_similarity, vector_rank.
        Returns [] if passed_job_urls is empty.
    """
    if not passed_job_urls:
        return []

    effective_top_n = top_n if top_n is not None else int(config.get("vector_top_n", 50))

    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]
    from fitcv.embeddings import generate_embedding

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)

    query_text = build_candidate_query_text(profile, config)
    embedding_vector = generate_embedding(query_text, config)

    sql = build_vector_search_query(
        top_n=effective_top_n,
        passed_job_urls=passed_job_urls,
        project=project,
        dataset=dataset,
    )

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("candidate_embedding", "FLOAT64", embedding_vector)
        ]
    )

    rows = client.query(sql, job_config=job_config).result()
    shortlist = [
        {"job_url": row.job_url, "vector_similarity": row.vector_similarity, "vector_rank": row.vector_rank}
        for row in rows
    ]
    return _dedupe_shortlist_rows(shortlist)


# ── integration: store shortlist ──────────────────────────────────────────────

def store_shortlist(
    shortlist: list[dict[str, Any]],
    config: dict[str, Any],
    retrieval_strategy: str | None = None,
) -> None:
    """Insert vector shortlist rows into fitcv.vector_shortlist.

    retrieval_strategy defaults to config["retrieval_strategy"] ("job_summary_v1" if missing).

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    if not shortlist:
        return

    effective_strategy = retrieval_strategy or str(config.get("retrieval_strategy", "job_summary_v1"))

    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)
    table_ref = f"{project}.{dataset}.vector_shortlist"
    now = datetime.now(tz=timezone.utc).isoformat()

    rows = [
        {
            "job_url":            item["job_url"],
            "vector_rank":        item["vector_rank"],
            "vector_similarity":  item["vector_similarity"],
            "retrieval_strategy": effective_strategy,
            "retrieved_at":       now,
        }
        for item in shortlist
    ]

    errors = client.insert_rows_json(table_ref, rows)
    if errors:
        raise RuntimeError(f"BigQuery insert errors for vector_shortlist: {errors}")
