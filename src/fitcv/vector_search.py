"""@meta
name: vector_search
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.vector_search.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import hashlib
import json
import logging
import math
import sqlite3
from datetime import datetime, timezone
from typing import Any, TypedDict

from fitcv.candidate import flatten_skills, infer_role_family
from fitcv.embeddings import generate_embedding, get_shortlist_embedding_model
from fitcv.shortlist_runtime import (
    build_contract_fingerprint,
    configure_sqlite_connection,
    hash_payload,
    normalize_text_scalar,
    run_sqlite_io_retry,
    sqlite_path,
)

DEFAULT_RECENT_ROLE_COUNT = 3
DEFAULT_ROLE_FAMILY_HINT_COUNT = 3
DEFAULT_DOMAIN_HINT_COUNT = 5
DEFAULT_LOCATION_TYPE_HINT_COUNT = 3
CANDIDATE_QUERY_SCHEMA_VERSION = "shortlist_candidate_query_v1"
REUSED_CACHED_QUERY_EMBEDDING_STATUS = "reused_cached_query_embedding"
FRESH_QUERY_EMBEDDING_STATUS = "fresh_query_embedding"
VECTOR_RETRIEVAL_STRATEGY = "vector_cosine_v1"
VECTOR_DIAGNOSTIC_SAMPLE_LIMIT = 20

logger = logging.getLogger(__name__)


class CandidateQueryEmbeddingRecord(TypedDict):
    text: str
    components: dict[str, Any]
    embedding: list[float]
    candidate_query_signature: str
    candidate_query_contract_fingerprint: str
    candidate_query_reuse_status: str


class CandidateQueryEmbeddingCacheRow(TypedDict):
    candidate_query_signature: str
    candidate_query_contract_fingerprint: str
    candidate_query_text: str
    candidate_query_components_json: str
    embedding: list[float]


def _build_candidate_query_embedding_record(
    *,
    text: str,
    components: dict[str, Any],
    embedding: list[float],
    candidate_query_signature: str,
    candidate_query_contract_fingerprint: str,
    candidate_query_reuse_status: str,
) -> CandidateQueryEmbeddingRecord:
    return {
        "text": text,
        "components": components,
        "embedding": embedding,
        "candidate_query_signature": candidate_query_signature,
        "candidate_query_contract_fingerprint": candidate_query_contract_fingerprint,
        "candidate_query_reuse_status": candidate_query_reuse_status,
    }





def _ensure_sqlite_vector_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_query_embeddings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          candidate_query_signature TEXT NOT NULL,
          candidate_query_contract_fingerprint TEXT NOT NULL,
          candidate_query_text TEXT NOT NULL,
          candidate_query_components_json TEXT NOT NULL,
          embedding_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vector_shortlist (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_url TEXT NOT NULL,
          vector_rank INTEGER NOT NULL,
          vector_similarity REAL NOT NULL,
          retrieval_strategy TEXT NOT NULL,
          retrieved_at TEXT NOT NULL
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_candidate_query_embeddings_sig_created ON candidate_query_embeddings(candidate_query_signature, created_at DESC)"
    )


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(av * bv for av, bv in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(value * value for value in a))
    norm_b = math.sqrt(sum(value * value for value in b))
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def _validated_vector(value: Any, *, expected_dimension: int | None = None) -> list[float] | None:
    if not isinstance(value, list) or not value:
        return None
    vector: list[float] = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            return None
        number = float(item)
        if not math.isfinite(number):
            return None
        vector.append(number)
    if expected_dimension is not None and len(vector) != expected_dimension:
        return None
    if not any(number != 0.0 for number in vector):
        return None
    return vector


def _empty_vector_search_result() -> dict[str, Any]:
    return {
        "production_rows": [],
        "audit_rows": [],
        "diagnostics": {
            "eligible_jobs_total": 0,
            "scored_jobs_total": 0,
            "missing_job_embedding_total": 0,
            "invalid_job_embedding_total": 0,
            "candidate_embedding_available": False,
            "embedding_coverage_rate": 0.0,
            "production_shortlist_total": 0,
            "production_cutoff_rank": None,
            "production_cutoff_similarity": None,
            "audit_candidate_total": 0,
            "audit_sample_total": 0,
            "audit_sample_fingerprint": "",
            "missing_job_embedding_sample": [],
            "invalid_job_embedding_sample": [],
            "duplicate_job_embedding_total": 0,
            "duplicate_job_embedding_sample": [],
            "raw_hit_anomaly_total": 0,
            "raw_hit_anomaly_sample": [],
        },
        "candidate_query": {},
    }


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

def _append_unique_text(values: list[str], candidate: str, seen: set[str]) -> None:
    text = str(candidate or "").strip()
    if not text:
        return
    lowered = text.lower()
    if lowered in seen:
        return
    seen.add(lowered)
    values.append(text)


def _normalize_query_scalar(value: Any) -> str:
    return normalize_text_scalar(value)


def build_candidate_query_components(
    profile: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return bounded deterministic shortlist intent components (SSOT)."""
    max_skills = int((config or {}).get("vector_max_candidate_skills", 15))

    headline = str(profile.get("headline") or "").strip()
    prefs = profile.get("preferences", {}) or {}
    target_role = str(prefs.get("target_role") or "").strip()

    recent_roles: list[str] = []
    seen_recent_roles: set[str] = set()
    for experience in profile.get("experiences", []) or []:
        role = str(experience.get("role") or "").strip()
        if not role:
            continue
        _append_unique_text(recent_roles, role, seen_recent_roles)
        if len(recent_roles) >= DEFAULT_RECENT_ROLE_COUNT:
            break

    skills: list[str] = []
    seen_skills: set[str] = set()
    for skill in flatten_skills(profile):
        _append_unique_text(skills, skill, seen_skills)
        if len(skills) >= max_skills:
            break

    role_families: list[str] = []
    seen_role_families: set[str] = set()
    for role_family in prefs.get("role_families", []) or []:
        _append_unique_text(role_families, str(role_family), seen_role_families)
        if len(role_families) >= DEFAULT_ROLE_FAMILY_HINT_COUNT:
            break
    if len(role_families) < DEFAULT_ROLE_FAMILY_HINT_COUNT:
        inferred_target_family = infer_role_family(target_role, config=config)
        if inferred_target_family:
            _append_unique_text(role_families, inferred_target_family, seen_role_families)
    if len(role_families) < DEFAULT_ROLE_FAMILY_HINT_COUNT:
        for experience in profile.get("experiences", []) or []:
            explicit_family = str(experience.get("role_family") or "").strip()
            inferred_family = infer_role_family(
                str(experience.get("role") or ""),
                explicit_family=explicit_family or None,
                config=config,
            )
            if inferred_family:
                _append_unique_text(role_families, inferred_family, seen_role_families)
            if len(role_families) >= DEFAULT_ROLE_FAMILY_HINT_COUNT:
                break

    domains: list[str] = []
    seen_domains: set[str] = set()
    for domain in prefs.get("domains", []) or []:
        _append_unique_text(domains, str(domain), seen_domains)
        if len(domains) >= DEFAULT_DOMAIN_HINT_COUNT:
            break
    if len(domains) < DEFAULT_DOMAIN_HINT_COUNT:
        for experience in profile.get("experiences", []) or []:
            for domain_tag in experience.get("domain_tags", []) or []:
                _append_unique_text(domains, str(domain_tag), seen_domains)
                if len(domains) >= DEFAULT_DOMAIN_HINT_COUNT:
                    break
            if len(domains) >= DEFAULT_DOMAIN_HINT_COUNT:
                break
    if len(domains) < DEFAULT_DOMAIN_HINT_COUNT:
        for project in profile.get("projects", []) or []:
            for domain_tag in project.get("domain_tags", []) or []:
                _append_unique_text(domains, str(domain_tag), seen_domains)
                if len(domains) >= DEFAULT_DOMAIN_HINT_COUNT:
                    break
            if len(domains) >= DEFAULT_DOMAIN_HINT_COUNT:
                break

    location_types: list[str] = []
    seen_location_types: set[str] = set()
    for location_type in prefs.get("location_types", []) or []:
        _append_unique_text(location_types, str(location_type), seen_location_types)
        if len(location_types) >= DEFAULT_LOCATION_TYPE_HINT_COUNT:
            break

    return {
        "headline": headline,
        "target_role": target_role,
        "recent_roles": recent_roles,
        "skills": skills,
        "role_families": role_families,
        "domains": domains,
        "location_types": location_types,
        "role_family_hints": role_families,
        "flattened_skills": skills,
        "domain_hints": domains,
        "location_type_hints": location_types,
    }



def build_candidate_query_signature_record(components: dict[str, Any]) -> dict[str, Any]:
    """Return the stable shortlist query payload plus its hash signature."""
    payload = {
        "headline": _normalize_query_scalar(components.get("headline") or ""),
        "target_role": _normalize_query_scalar(components.get("target_role") or ""),
        "recent_roles": [
            _normalize_query_scalar(value)
            for value in list(components.get("recent_roles") or [])
            if _normalize_query_scalar(value)
        ],
        "skills": [
            _normalize_query_scalar(value)
            for value in list(components.get("skills") or components.get("flattened_skills") or [])
            if _normalize_query_scalar(value)
        ],
        "role_families": [
            _normalize_query_scalar(value)
            for value in list(components.get("role_families") or components.get("role_family_hints") or [])
            if _normalize_query_scalar(value)
        ],
        "domains": [
            _normalize_query_scalar(value)
            for value in list(components.get("domains") or components.get("domain_hints") or [])
            if _normalize_query_scalar(value)
        ],
        "location_types": [
            _normalize_query_scalar(value)
            for value in list(components.get("location_types") or components.get("location_type_hints") or [])
            if _normalize_query_scalar(value)
        ],
    }
    payload = {
        key: value
        for key, value in payload.items()
        if value not in ("", [], None)
    }
    payload_json, signature = hash_payload(payload)
    return {
        "payload": payload,
        "payload_json": payload_json,
        "signature": signature,
    }


def build_candidate_query_embedding_contract_fingerprint(config: dict[str, Any]) -> dict[str, Any]:
    """Fingerprint shortlist candidate-query embedding behavior to invalidate reuse."""
    payload = {
        "embedding_model": get_shortlist_embedding_model(config),
        "candidate_query_schema_version": CANDIDATE_QUERY_SCHEMA_VERSION,
    }
    fingerprint = build_contract_fingerprint(payload)
    return {
        "payload": payload,
        "fingerprint": fingerprint,
    }

def build_candidate_query_text(
    profile: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> str:
    """Build deterministic canonical shortlist query text from SSOT components."""
    components = build_candidate_query_components(profile, config)

    def _join(values: list[str]) -> str:
        return " | ".join(str(value).strip() for value in values if str(value).strip())

    lines = [
        f"Headline: {str(components.get('headline') or '').strip()}",
        f"Target Role: {str(components.get('target_role') or '').strip()}",
        f"Recent Roles: {_join(list(components.get('recent_roles') or []))}",
        f"Skills: {_join(list(components.get('skills') or []))}",
        f"Role Families: {_join(list(components.get('role_families') or []))}",
        f"Domains: {_join(list(components.get('domains') or []))}",
        f"Location Types: {_join(list(components.get('location_types') or []))}",
    ]
    return "\n".join(lines)




def resolve_candidate_query_embedding(
    profile: dict[str, Any],
    config: dict[str, Any],
) -> CandidateQueryEmbeddingRecord:
    """Return shortlist candidate query plus cached or fresh sqlite embedding."""
    components = build_candidate_query_components(profile, config)
    query_text = build_candidate_query_text(profile, config)
    signature_record = build_candidate_query_signature_record(components)
    contract_record = build_candidate_query_embedding_contract_fingerprint(config)
    with sqlite3.connect(sqlite_path(), timeout=30) as conn:
        configure_sqlite_connection(conn)
        _ensure_sqlite_vector_tables(conn)
        row = conn.execute(
            """
            SELECT embedding_json
            FROM candidate_query_embeddings
            WHERE candidate_query_signature = ?
              AND candidate_query_contract_fingerprint = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (signature_record["signature"], contract_record["fingerprint"]),
        ).fetchone()
        if row and row[0]:
            try:
                cached_embedding = list(json.loads(str(row[0])) or [])
            except Exception:
                cached_embedding = []
            if cached_embedding:
                return _build_candidate_query_embedding_record(
                    text=query_text,
                    components=components,
                    embedding=cached_embedding,
                    candidate_query_signature=signature_record["signature"],
                    candidate_query_contract_fingerprint=contract_record["fingerprint"],
                    candidate_query_reuse_status=REUSED_CACHED_QUERY_EMBEDDING_STATUS,
                )
        embedding_vector = generate_embedding(query_text, config)
        now = datetime.now(tz=timezone.utc).isoformat()
        conn.execute(
            """
            INSERT INTO candidate_query_embeddings(
              candidate_query_signature, candidate_query_contract_fingerprint,
              candidate_query_text, candidate_query_components_json, embedding_json, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                signature_record["signature"],
                contract_record["fingerprint"],
                query_text,
                signature_record["payload_json"],
                json.dumps(embedding_vector),
                now,
            ),
        )
        conn.commit()
    return _build_candidate_query_embedding_record(
        text=query_text,
        components=components,
        embedding=embedding_vector,
        candidate_query_signature=signature_record["signature"],
        candidate_query_contract_fingerprint=contract_record["fingerprint"],
        candidate_query_reuse_status=FRESH_QUERY_EMBEDDING_STATUS,
    )


# ── VECTOR_SEARCH SQL builder ─────────────────────────────────────────────────



# ── integration: run full retrieval pipeline ──────────────────────────────────

def run_vector_search(
    profile: dict[str, Any],
    passed_job_urls: list[str],
    config: dict[str, Any],
    top_n: int | None = None,
) -> dict[str, Any]:
    """Score passed jobs against cached local job embeddings."""
    eligible_job_urls = sorted({str(job_url).strip() for job_url in passed_job_urls if str(job_url).strip()})
    if not eligible_job_urls:
        return _empty_vector_search_result()
    effective_top_n = (
        top_n
        if top_n is not None
        else int((config.get("pipeline") or {}).get("vector_search_top_n") or config.get("vector_top_n", 50))
    )
    audit_sample_n = int((config.get("pipeline") or {}).get("shortlist_audit_sample_n", 0))
    candidate_query_record = resolve_candidate_query_embedding(profile, config)
    candidate_embedding = _validated_vector(candidate_query_record.get("embedding"))
    candidate_query = {
        key: value
        for key, value in candidate_query_record.items()
        if key != "embedding"
    }
    placeholders = ",".join(["?"] * len(eligible_job_urls))
    with sqlite3.connect(sqlite_path(), timeout=30) as conn:
        configure_sqlite_connection(conn)
        query = f"""
        WITH ranked_embeddings AS (
          SELECT
            id,
            job_url,
            embedding_json,
            ROW_NUMBER() OVER (
              PARTITION BY job_url
              ORDER BY created_at DESC, id DESC
            ) AS row_number,
            COUNT(*) OVER (PARTITION BY job_url) AS embedding_row_count
          FROM job_embeddings
          WHERE chunk_type = 'job_summary' AND job_url IN ({placeholders})
        )
        SELECT job_url, embedding_json, embedding_row_count
        FROM ranked_embeddings
        WHERE row_number = 1
        """
        rows = list(conn.execute(query, tuple(eligible_job_urls)).fetchall())

    latest_by_url = {str(job_url): (embedding_json, int(row_count)) for job_url, embedding_json, row_count in rows}
    missing_urls = sorted(set(eligible_job_urls) - set(latest_by_url))
    invalid_urls: list[str] = []
    duplicate_urls = sorted(job_url for job_url, (_, count) in latest_by_url.items() if count > 1)
    scored: list[dict[str, Any]] = []
    for job_url in eligible_job_urls:
        latest = latest_by_url.get(job_url)
        if latest is None:
            continue
        embedding_json, _ = latest
        try:
            raw_job_embedding = json.loads(str(embedding_json))
        except (TypeError, ValueError, json.JSONDecodeError):
            raw_job_embedding = None
        job_embedding = _validated_vector(
            raw_job_embedding,
            expected_dimension=len(candidate_embedding) if candidate_embedding is not None else None,
        )
        if job_embedding is None:
            invalid_urls.append(job_url)
            continue
        if candidate_embedding is None:
            continue
        scored.append(
            {
                "job_url": job_url,
                "vector_similarity": _cosine_similarity(candidate_embedding, job_embedding),
            }
        )
    scored.sort(key=lambda item: (-float(item["vector_similarity"]), str(item["job_url"])))
    ranked_rows = [
        {
            **row,
            "vector_rank": index + 1,
            "shortlist_origin": "vector_search",
            "retrieval_strategy": VECTOR_RETRIEVAL_STRATEGY,
        }
        for index, row in enumerate(scored)
    ]
    production_rows = ranked_rows[:effective_top_n]
    audit_candidates = ranked_rows[effective_top_n:]
    candidate_query_signature = str(candidate_query.get("candidate_query_signature") or "")
    audit_ranked = [
        {
            **row,
            "shortlist_origin": "audit",
            "audit_selection_hash": hashlib.sha256(
                f"{candidate_query_signature}\0{row['job_url']}".encode("utf-8")
            ).hexdigest(),
        }
        for row in audit_candidates
    ]
    audit_rows = sorted(
        sorted(audit_ranked, key=lambda row: (str(row["audit_selection_hash"]), str(row["job_url"])))[:audit_sample_n],
        key=lambda row: int(row["vector_rank"]),
    )
    audit_sample_fingerprint = ""
    if audit_rows:
        _, audit_sample_fingerprint = hash_payload(
            {
                "candidate_query_signature": candidate_query_signature,
                "candidate_query_contract_fingerprint": str(
                    candidate_query.get("candidate_query_contract_fingerprint") or ""
                ),
                "vector_search_top_n": effective_top_n,
                "shortlist_audit_sample_n": audit_sample_n,
                "audit_rows": audit_rows,
            }
        )
    production_cutoff = production_rows[-1] if production_rows else None
    eligible_total = len(eligible_job_urls)
    return {
        "production_rows": production_rows,
        "audit_rows": audit_rows,
        "diagnostics": {
            "eligible_jobs_total": eligible_total,
            "scored_jobs_total": len(ranked_rows),
            "missing_job_embedding_total": len(missing_urls),
            "invalid_job_embedding_total": len(invalid_urls),
            "candidate_embedding_available": candidate_embedding is not None,
            "embedding_coverage_rate": len(ranked_rows) / eligible_total if eligible_total else 0.0,
            "production_shortlist_total": len(production_rows),
            "production_cutoff_rank": production_cutoff.get("vector_rank") if production_cutoff else None,
            "production_cutoff_similarity": production_cutoff.get("vector_similarity") if production_cutoff else None,
            "audit_candidate_total": len(audit_candidates),
            "audit_sample_total": len(audit_rows),
            "audit_sample_fingerprint": audit_sample_fingerprint,
            "missing_job_embedding_sample": missing_urls[:VECTOR_DIAGNOSTIC_SAMPLE_LIMIT],
            "invalid_job_embedding_sample": invalid_urls[:VECTOR_DIAGNOSTIC_SAMPLE_LIMIT],
            "duplicate_job_embedding_total": len(duplicate_urls),
            "duplicate_job_embedding_sample": duplicate_urls[:VECTOR_DIAGNOSTIC_SAMPLE_LIMIT],
            "raw_hit_anomaly_total": 0,
            "raw_hit_anomaly_sample": [],
        },
        "candidate_query": candidate_query,
    }


# ── integration: store shortlist ──────────────────────────────────────────────

def store_shortlist(
    shortlist: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert vector shortlist rows into local sqlite store."""
    if not shortlist:
        return
    now = datetime.now(tz=timezone.utc).isoformat()

    def _write_shortlist() -> None:
        with sqlite3.connect(sqlite_path(), timeout=30) as conn:
            configure_sqlite_connection(conn)
            _ensure_sqlite_vector_tables(conn)
            conn.executemany(
                """
                INSERT INTO vector_shortlist(job_url, vector_rank, vector_similarity, retrieval_strategy, retrieved_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                [
                    (
                        str(item["job_url"]),
                        int(item["vector_rank"]),
                        float(item["vector_similarity"]),
                        VECTOR_RETRIEVAL_STRATEGY,
                        now,
                    )
                    for item in shortlist
                ],
            )
            conn.commit()

    run_sqlite_io_retry(_write_shortlist)








