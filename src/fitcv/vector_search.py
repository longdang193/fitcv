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
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any, TypedDict

from fitcv.candidate import flatten_rankable_skills, flatten_skills, infer_role_family
from fitcv.config import MIXED_FALLBACK_RETRIEVAL_STRATEGY
from fitcv.ranking import compute_declared_preference_fit_details, compute_must_have_match, compute_title_relevance
from fitcv.embeddings import (
    build_embedding_backend_metadata,
    build_embedding_contract_fingerprint,
    generate_embedding_with_metadata,
    get_shortlist_embedding_model,
)
from fitcv.shortlist_runtime import (
    build_contract_fingerprint,
    configure_sqlite_connection,
    hash_payload,
    normalize_text_scalar,
    run_sqlite_io_retry,
    sqlite_path,
)
from fitcv.persistence import sqlite_connection

DEFAULT_RECENT_ROLE_COUNT = 3
DEFAULT_ROLE_FAMILY_HINT_COUNT = 3
DEFAULT_DOMAIN_HINT_COUNT = 5
DEFAULT_LOCATION_TYPE_HINT_COUNT = 3
CANDIDATE_QUERY_SCHEMA_VERSION = "shortlist_candidate_query_v2"
CANDIDATE_QUERY_TECHNOLOGY_HINT_COUNT = 8
CANDIDATE_QUERY_TECHNOLOGY_HINT_CHARS = 160
CANDIDATE_QUERY_PROJECT_EVIDENCE_HINT_COUNT = 8
CANDIDATE_QUERY_PROJECT_EVIDENCE_HINT_CHARS = 200
REUSED_CACHED_QUERY_EMBEDDING_STATUS = "reused_cached_query_embedding"
FRESH_QUERY_EMBEDDING_STATUS = "fresh_query_embedding"
VECTOR_RETRIEVAL_STRATEGY = "vector_cosine_v1"
LEXICAL_RETRIEVAL_STRATEGY = "lexical_v1"
HYBRID_RETRIEVAL_STRATEGY = "hybrid_rrf_v1"
HYBRID_RRF_K = 60
HYBRID_CHANNEL_WEIGHT = 1.0
VECTOR_DIAGNOSTIC_SAMPLE_LIMIT = 20

logger = logging.getLogger(__name__)


class CandidateQueryEmbeddingRecord(TypedDict):
    text: str
    components: dict[str, Any]
    embedding: list[float]
    candidate_query_signature: str
    candidate_query_contract_fingerprint: str
    candidate_query_reuse_status: str
    embedding_backend_id: str


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
    embedding_backend_id: str,
) -> CandidateQueryEmbeddingRecord:
    return {
        "text": text,
        "components": components,
        "embedding": embedding,
        "candidate_query_signature": candidate_query_signature,
        "candidate_query_contract_fingerprint": candidate_query_contract_fingerprint,
        "candidate_query_reuse_status": candidate_query_reuse_status,
        "embedding_backend_id": embedding_backend_id,
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


def _normalized_vector(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    return [value / norm for value in vector]


def _effective_embedding_metadata(config: dict[str, Any], backend_id: str) -> dict[str, Any]:
    configured_model = "hash-v1" if backend_id == "sqlite_deterministic_local" else None
    return build_embedding_backend_metadata(
        config,
        configured_model=configured_model,
        backend=backend_id,
    )

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


def _profile_technology_inventory(profile: dict[str, Any]) -> list[str]:
    values: list[str] = []
    projects = sorted(
        (project for project in profile.get("projects", []) or [] if isinstance(project, dict)),
        key=lambda project: str(project.get("name") or "").casefold(),
    )
    for project in projects:
        technology_values = list(project.get("tech_stack", []) or [])
        for evidence in project.get("evidence", []) or []:
            if not isinstance(evidence, dict):
                continue
            title = str(evidence.get("title") or "").strip().casefold()
            if title != "technology stack" and not any(
                marker in title for marker in ("technology", "tool", "stack", "platform", "api")
            ):
                continue
            text = str(evidence.get("text") or "").strip()
            if text:
                technology_values.append(text)
        technology_values.extend(project.get("skills", []) or [])
        for technology in technology_values:
            if isinstance(technology, dict):
                technology = technology.get("name")
            text = str(technology or "").strip()
            if text:
                values.append(text)
    return values


_GENERIC_TECHNOLOGY_TOKENS = frozenset(
    {"api", "apis", "framework", "frameworks", "platform", "platforms", "tool", "tools", "technology", "technologies"}
)


def _technology_term_tokens(value: Any) -> set[str]:
    return {
        token
        for token in re.findall(r"[\w]+(?:[+#]+)?", str(value or "").casefold())
        if token not in _GENERIC_TECHNOLOGY_TOKENS
    }


def _technology_overlap(job_technology: list[Any], candidate_technology: list[Any]) -> float:
    job_terms = [_technology_term_tokens(value) for value in job_technology]
    candidate_terms = [_technology_term_tokens(value) for value in candidate_technology]
    job_terms = [tokens for tokens in job_terms if tokens]
    if not job_terms:
        return 0.0
    matched = sum(
        1
        for job_tokens in job_terms
        if any(
            job_tokens == candidate_tokens
            or job_tokens.issubset(candidate_tokens)
            or candidate_tokens.issubset(job_tokens)
            for candidate_tokens in candidate_terms
            if candidate_tokens
        )
    )
    return matched / len(job_terms)


def _description_overlap(description: Any, candidate_terms: list[Any]) -> float:
    description_terms = _technology_term_tokens(description)
    if not description_terms:
        return 0.0
    candidate_term_sets = [_technology_term_tokens(value) for value in candidate_terms]
    candidate_term_sets = [terms for terms in candidate_term_sets if terms]
    if not candidate_term_sets:
        return 0.0
    matched = sum(
        1
        for candidate_set in candidate_term_sets
        if candidate_set & description_terms
    )
    return matched / len(candidate_term_sets)


def _bounded_profile_technology_hints(profile: dict[str, Any]) -> list[str]:
    inventory = _profile_technology_inventory(profile)
    counts: dict[str, int] = {}
    first_seen: dict[str, int] = {}
    for index, value in enumerate(inventory):
        key = value.casefold()
        counts[key] = counts.get(key, 0) + 1
        first_seen.setdefault(key, index)
    ranked = sorted(
        {value.casefold(): value for value in inventory}.values(),
        key=lambda value: (-counts[value.casefold()], value.casefold(), first_seen[value.casefold()]),
    )
    return [
        value[:CANDIDATE_QUERY_TECHNOLOGY_HINT_CHARS]
        for value in ranked[:CANDIDATE_QUERY_TECHNOLOGY_HINT_COUNT]
    ]


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
    for skill in flatten_rankable_skills(profile):
        _append_unique_text(skills, skill, seen_skills)
        if len(skills) >= max_skills:
            break

    role_families: list[str] = []
    seen_role_families: set[str] = set()
    max_role_families = int((config or {}).get("vector_max_role_families", 12))
    for role_family in prefs.get("role_families", []) or []:
        _append_unique_text(role_families, str(role_family), seen_role_families)
        if len(role_families) >= max_role_families:
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

    technology_hints = _bounded_profile_technology_hints(profile)
    project_evidence_hints: list[str] = []
    seen_project_evidence: set[str] = set()
    projects = sorted(
        (project for project in profile.get("projects", []) or [] if isinstance(project, dict)),
        key=lambda project: str(project.get("name") or "").casefold(),
    )
    for project in projects:
        for value in [project.get("name"), project.get("business_value"), *(project.get("highlights") or [])]:
            text = str(value or "").strip()
            if not text:
                continue
            _append_unique_text(project_evidence_hints, text[:CANDIDATE_QUERY_PROJECT_EVIDENCE_HINT_CHARS], seen_project_evidence)
            if len(project_evidence_hints) >= CANDIDATE_QUERY_PROJECT_EVIDENCE_HINT_COUNT:
                break
        if len(project_evidence_hints) >= CANDIDATE_QUERY_PROJECT_EVIDENCE_HINT_COUNT:
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
        "technology_hints": technology_hints,
        "project_technology_hints": technology_hints,
        "project_evidence_hints": project_evidence_hints,
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
        "technology_hints": [
            _normalize_query_scalar(value)
            for value in list(components.get("technology_hints") or components.get("project_technology_hints") or [])
            if _normalize_query_scalar(value)
        ],
        "project_evidence_hints": [
            _normalize_query_scalar(value)
            for value in list(components.get("project_evidence_hints") or [])
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


def build_candidate_query_embedding_contract_fingerprint(
    config: dict[str, Any],
    *,
    embedding_backend: str | None = None,
) -> dict[str, Any]:
    """Fingerprint shortlist candidate-query embedding behavior to invalidate reuse."""
    payload = {
        "embedding_contract_fingerprint": build_embedding_contract_fingerprint(
            config,
            configured_model="hash-v1" if embedding_backend == "sqlite_deterministic_local" else None,
            backend=embedding_backend,
        )["fingerprint"],
        "retrieval_strategy": str(
            (config.get("pipeline") or {}).get("retrieval_strategy") or VECTOR_RETRIEVAL_STRATEGY
        ),
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
        f"Project Technology: {_join(list(components.get('technology_hints') or []))}",
        f"Project Evidence: {_join(list(components.get('project_evidence_hints') or []))}",
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
    requested_embedding_metadata = build_embedding_backend_metadata(config)
    configured_backend_id = requested_embedding_metadata["backend_id"]
    contract_record = build_candidate_query_embedding_contract_fingerprint(
        config,
        embedding_backend=configured_backend_id,
    )
    with sqlite_connection(sqlite_path(), timeout=30) as conn:
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
            cached_embedding = _validated_vector(
                cached_embedding,
                expected_dimension=int(requested_embedding_metadata["dimension"]),
            )
            if cached_embedding is not None:
                return _build_candidate_query_embedding_record(
                    text=query_text,
                    components=components,
                    embedding=cached_embedding,
                    candidate_query_signature=signature_record["signature"],
                    candidate_query_contract_fingerprint=contract_record["fingerprint"],
                    candidate_query_reuse_status=REUSED_CACHED_QUERY_EMBEDDING_STATUS,
                    embedding_backend_id=configured_backend_id,
                )
        embedding_result = generate_embedding_with_metadata(query_text, config)
        actual_backend_id = str(embedding_result.get("backend_id") or configured_backend_id)
        embedding_backend_metadata = {
            key: embedding_result.get(key)
            for key in (
                "backend_id",
                "configured_model",
                "dimension",
                "model_revision",
                "preprocessing_version",
                "contract_fingerprint",
            )
        }
        embedding_vector = _validated_vector(
            list(embedding_result["embedding"]),
            expected_dimension=(
                int(embedding_backend_metadata["dimension"])
                if embedding_backend_metadata.get("dimension") is not None
                else None
            ),
        )
        if embedding_vector is None:
            raise ValueError("embedding backend returned an invalid candidate query vector")
        actual_contract_record = build_candidate_query_embedding_contract_fingerprint(
            config,
            embedding_backend=actual_backend_id,
        )
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
                actual_contract_record["fingerprint"],
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
        candidate_query_contract_fingerprint=actual_contract_record["fingerprint"],
        candidate_query_reuse_status=FRESH_QUERY_EMBEDDING_STATUS,
        embedding_backend_id=actual_backend_id,
    )


# ── VECTOR_SEARCH SQL builder ─────────────────────────────────────────────────



# ── integration: run full retrieval pipeline ──────────────────────────────────

def _lexical_search_result(
    profile: dict[str, Any],
    eligible_job_urls: list[str],
    config: dict[str, Any],
    top_n: int,
    structured_jobs: list[dict[str, Any]],
    *,
    requested_strategy: str,
    fallback_reason: str | None = None,
    embedding_backend_id: str | None = None,
    embedding_backend_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    components = build_candidate_query_components(profile, config)
    prefs = dict(profile.get("preferences") or {})
    candidate_skills = flatten_rankable_skills(profile)
    jobs_by_url = {str(job.get("job_url") or ""): job for job in structured_jobs}
    candidate_technology = _profile_technology_inventory(profile)
    scored: list[dict[str, Any]] = []
    for job_url in eligible_job_urls:
        job = jobs_by_url.get(job_url)
        if job is None:
            continue
        required = list(job.get("required_skills_canonical") or job.get("required_skills") or [])
        skill_score = compute_must_have_match(required, candidate_skills, config)
        required_skill_intersection = bool(required) and skill_score > 0.0
        title_score = compute_title_relevance(
            str(job.get("title") or job.get("job_title") or "") or None,
            str(prefs.get("target_role") or "") or None,
            job_family=str(job.get("job_family") or "") or None,
            config=config,
        )
        preference = compute_declared_preference_fit_details(job, prefs, config)
        parts = preference["components"]
        job_technology = list(job.get("tech_stack_canonical") or job.get("tech_stack") or [])
        technology_overlap = _technology_overlap(job_technology, candidate_technology)
        description_overlap = _description_overlap(
            job.get("description_cleaned") or job.get("description"),
            [*candidate_skills, *candidate_technology],
        )
        base_score = (
            skill_score
            + title_score
            + float(parts["domain"])
            + float(parts["role_family"])
            + float(parts["work_mode"])
        ) / 5.0
        retrieval_score = (base_score * 0.65) + (technology_overlap * 0.20) + (description_overlap * 0.15)
        scored.append({
            **job,
            "job_url": job_url,
            "retrieval_score": retrieval_score,
            "retrieval_components": {
                "skill_overlap": skill_score,
                "required_skill_intersection": required_skill_intersection,
                "title_relevance": title_score,
                "domain": parts["domain"],
                "role_family": parts["role_family"],
                "location": parts["work_mode"],
                "technology_overlap": technology_overlap,
                "description_overlap": description_overlap,
            },
        })
    scored.sort(
        key=lambda item: (
            -float(item["retrieval_score"]),
            -float(item.get("retrieval_components", {}).get("technology_overlap") or 0.0),
            str(item["job_url"]),
        )
    )
    ranked_rows = [
        {
            **row,
            "vector_rank": index + 1,
            "lexical_rank": index + 1,
            "shortlist_origin": "lexical_search",
            "retrieval_strategy": LEXICAL_RETRIEVAL_STRATEGY,
        }
        for index, row in enumerate(scored)
    ]
    production_rows = ranked_rows[:top_n]
    audit_sample_n = int((config.get("pipeline") or {}).get("shortlist_audit_sample_n", 0))
    audit_rows = [{**row, "shortlist_origin": "audit"} for row in ranked_rows[top_n:top_n + audit_sample_n]]
    cutoff = production_rows[-1] if production_rows else None
    embedding_metadata = build_embedding_backend_metadata(config)
    effective_embedding_metadata = dict(
        embedding_backend_metadata
        or _effective_embedding_metadata(config, embedding_backend_id or "structured_jobs_lexical")
    )
    return {
        "production_rows": production_rows,
        "audit_rows": audit_rows,
        "diagnostics": {
            "retrieval_strategy": LEXICAL_RETRIEVAL_STRATEGY,
            "requested_strategy": requested_strategy,
            "effective_strategy": LEXICAL_RETRIEVAL_STRATEGY,
            "fallback_used": fallback_reason is not None,
            "fallback_reason": fallback_reason,
            "backend_id": "structured_jobs_lexical",
            "embedding_backend_id": embedding_backend_id or embedding_metadata["backend_id"],
            "requested_embedding_backend_id": embedding_metadata["backend_id"],
            "effective_embedding_backend_metadata": effective_embedding_metadata,
            "configured_model": embedding_metadata["configured_model"],
            "dimension": embedding_metadata["dimension"],
            "contract_fingerprint": embedding_metadata["contract_fingerprint"],
            "eligible_jobs_total": len(eligible_job_urls),
            "scored_jobs_total": len(ranked_rows),
            "production_shortlist_total": len(production_rows),
            "production_cutoff_rank": cutoff.get("vector_rank") if cutoff else None,
            "production_cutoff_retrieval_score": cutoff.get("retrieval_score") if cutoff else None,
            "embedding_generation_skipped": True,
            "personalization_unavailable_reason": "embedding_strategy_incompatible",
            "shortlist_audit_sample_n": audit_sample_n,
            "lexical_rescue_min_score": 0.2,
        },
        "candidate_query": {
            "text": build_candidate_query_text(profile, config),
            "components": components,
            "candidate_query_signature": build_candidate_query_signature_record(components)["signature"],
            "candidate_query_contract_fingerprint": build_contract_fingerprint({"retrieval_strategy": LEXICAL_RETRIEVAL_STRATEGY, "candidate_query_schema_version": CANDIDATE_QUERY_SCHEMA_VERSION}),
            "candidate_query_reuse_status": "not_applicable_lexical",
        },
    }


def _unavailable_search_result(
    eligible_job_urls: list[str],
    *,
    requested_strategy: str,
    reason: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    embedding_metadata = build_embedding_backend_metadata(config)
    return {
        "production_rows": [],
        "audit_rows": [],
        "diagnostics": {
            "retrieval_strategy": requested_strategy,
            "requested_strategy": requested_strategy,
            "effective_strategy": "unavailable",
            "fallback_used": False,
            "fallback_reason": reason,
            "backend_id": "unavailable",
            "embedding_backend_id": embedding_metadata["backend_id"],
            "configured_model": embedding_metadata["configured_model"],
            "dimension": embedding_metadata["dimension"],
            "contract_fingerprint": embedding_metadata["contract_fingerprint"],
            "eligible_jobs_total": len(eligible_job_urls),
            "scored_jobs_total": 0,
            "production_shortlist_total": 0,
            "result_counts": {"eligible": len(eligible_job_urls), "scored": 0, "production": 0},
        },
        "candidate_query": {},
    }


def _hybrid_search_result(
    *,
    vector_result: dict[str, Any],
    lexical_result: dict[str, Any],
    eligible_job_urls: list[str],
    top_n: int,
    channel_depth: int | None = None,
) -> dict[str, Any]:
    """Fuse bounded vector and lexical channels without mixing score scales."""
    vector_rows = list(vector_result.get("production_rows") or [])
    lexical_rows = list(lexical_result.get("production_rows") or [])

    def has_affirmative_lexical_relevance(row: dict[str, Any]) -> bool:
        try:
            score = float(row.get("retrieval_score"))
        except (TypeError, ValueError):
            return False
        if not math.isfinite(score):
            return False
        components = dict(row.get("retrieval_components") or {})
        if components.get("required_skill_intersection") is True:
            return True
        if any(
            isinstance(components.get(key), (int, float))
            and math.isfinite(float(components[key]))
            and float(components[key]) > 0.0
            for key in ("title_relevance", "technology_overlap", "description_overlap")
        ):
            return True
        match_details = dict(components.get("match_details") or {})
        return any(
            str(value).strip().lower() not in {"", "none", "neutral", "unknown"}
            for value in match_details.values()
        )

    by_url: dict[str, dict[str, Any]] = {}
    for rank, row in enumerate(vector_rows, start=1):
        url = str(row.get("job_url") or "").strip()
        if not url:
            continue
        target = by_url.setdefault(url, {**row})
        target["vector_rank"] = min(int(target.get("vector_rank") or rank), rank)
        target["vector_similarity"] = row.get("vector_similarity")
    for rank, row in enumerate(lexical_rows, start=1):
        url = str(row.get("job_url") or "").strip()
        if not url:
            continue
        if url not in by_url and not has_affirmative_lexical_relevance(row):
            continue
        target = by_url.setdefault(url, {**row})
        if "vector_rank" not in target or target.get("shortlist_origin") in {"lexical_search", "audit"}:
            target["vector_rank"] = None
            target["vector_similarity"] = None
        target["lexical_rank"] = min(int(target.get("lexical_rank") or rank), rank)
        target["lexical_score"] = row.get("retrieval_score")

    effective_channel_depth = int(channel_depth or max(len(vector_rows), len(lexical_rows), len(eligible_job_urls)))
    _, fusion_fingerprint = hash_payload(
        {
            "contract": HYBRID_RETRIEVAL_STRATEGY,
            "vector_depth": effective_channel_depth,
            "lexical_depth": effective_channel_depth,
            "rrf_k": HYBRID_RRF_K,
            "channel_weights": {"vector": HYBRID_CHANNEL_WEIGHT, "lexical": HYBRID_CHANNEL_WEIGHT},
            "dedupe": "normalized_job_url",
            "missing_channel": "zero",
            "tie_break": "normalized_job_url",
        }
    )
    fused: list[dict[str, Any]] = []
    for url, row in by_url.items():
        vector_rank = row.get("vector_rank")
        lexical_rank = row.get("lexical_rank")
        fusion_score = 0.0
        if vector_rank:
            fusion_score += HYBRID_CHANNEL_WEIGHT / (HYBRID_RRF_K + int(vector_rank))
        if lexical_rank:
            fusion_score += HYBRID_CHANNEL_WEIGHT / (HYBRID_RRF_K + int(lexical_rank))
        fused.append(
            {
                **row,
                "job_url": url,
                "vector_rank": int(vector_rank) if vector_rank else None,
                "lexical_rank": int(lexical_rank) if lexical_rank else None,
                "hybrid_rrf_score": fusion_score,
                "retrieval_strategy": HYBRID_RETRIEVAL_STRATEGY,
                "fusion_contract_fingerprint": fusion_fingerprint,
                "shortlist_origin": "hybrid_rrf",
            }
        )
    fused.sort(key=lambda row: (-float(row["hybrid_rrf_score"]), str(row["job_url"])))
    production_rows = list(fused[:top_n])
    selected_urls = {str(row.get("job_url") or "") for row in production_rows}
    lexical_only_rows = [
        row
        for row in fused
        if row.get("lexical_rank") and not row.get("vector_rank")
    ]
    rescued_rows: list[dict[str, Any]] = []
    if production_rows:
        rescue_threshold = float((lexical_result.get("diagnostics") or {}).get("lexical_rescue_min_score") or 0.2)
        for lexical_row in lexical_only_rows:
            lexical_score = lexical_row.get("retrieval_score")
            try:
                lexical_score_value = float(lexical_score)
            except (TypeError, ValueError):
                continue
            if not math.isfinite(lexical_score_value) or lexical_score_value < rescue_threshold:
                continue
            if not has_affirmative_lexical_relevance(lexical_row):
                continue
            lexical_url = str(lexical_row.get("job_url") or "")
            if not lexical_url or lexical_url in selected_urls:
                continue
            displaced = production_rows[-1]
            production_rows[-1] = {
                **lexical_row,
                "rescue_reason": "affirmative_lexical_relevance",
                "rescued_displaced_job_url": str(displaced.get("job_url") or ""),
            }
            selected_urls.remove(str(displaced.get("job_url") or ""))
            selected_urls.add(lexical_url)
            rescued_rows.append(production_rows[-1])
            break
    audit_sample_n = int((lexical_result.get("diagnostics") or {}).get("shortlist_audit_sample_n") or 0)
    audit_rows = [
        {**row, "shortlist_origin": "audit"}
        for row in fused
        if str(row.get("job_url") or "") not in selected_urls
    ][:audit_sample_n]
    vector_diagnostics = dict(vector_result.get("diagnostics") or {})
    lexical_diagnostics = dict(lexical_result.get("diagnostics") or {})
    candidate_query = dict(vector_result.get("candidate_query") or lexical_result.get("candidate_query") or {})
    candidate_query["candidate_query_contract_fingerprint"] = build_contract_fingerprint(
        {
            "retrieval_strategy": HYBRID_RETRIEVAL_STRATEGY,
            "candidate_query_schema_version": CANDIDATE_QUERY_SCHEMA_VERSION,
            "fusion_fingerprint": fusion_fingerprint,
        }
    )
    return {
        "production_rows": production_rows,
        "audit_rows": audit_rows,
        "diagnostics": {
            "retrieval_strategy": HYBRID_RETRIEVAL_STRATEGY,
            "requested_strategy": HYBRID_RETRIEVAL_STRATEGY,
            "effective_strategy": HYBRID_RETRIEVAL_STRATEGY,
            "fallback_used": False,
            "fallback_reason": None,
            "fusion_contract": {
                "version": HYBRID_RETRIEVAL_STRATEGY,
                "vector_depth": effective_channel_depth,
                "lexical_depth": effective_channel_depth,
                "rrf_k": HYBRID_RRF_K,
                "channel_weights": {"vector": HYBRID_CHANNEL_WEIGHT, "lexical": HYBRID_CHANNEL_WEIGHT},
                "dedupe": "normalized_job_url",
                "missing_channel": "zero",
                "tie_break": "normalized_job_url",
            },
            "fusion_fingerprint": fusion_fingerprint,
            "eligible_jobs_total": len(eligible_job_urls),
            "vector_candidate_total": len(vector_rows),
            "lexical_candidate_total": len(lexical_rows),
            "fusion_channel_depth": effective_channel_depth,
            "scored_jobs_total": len(fused),
            "production_shortlist_total": len(production_rows),
            "production_cutoff_rank": len(production_rows),
            "lexical_only_rescue_count": len(rescued_rows),
            "lexical_only_rescued_urls": [str(row.get("job_url") or "") for row in rescued_rows],
            "lexical_only_rescue_evidence": [
                {
                    "job_url": str(row.get("job_url") or ""),
                    "lexical_rank": row.get("lexical_rank"),
                    "lexical_score": row.get("lexical_score"),
                    "displaced_job_url": row.get("rescued_displaced_job_url"),
                    "reason": row.get("rescue_reason"),
                }
                for row in rescued_rows
            ],
            "embedding_generation_skipped": bool(vector_diagnostics.get("embedding_generation_skipped")),
            "vector_diagnostics": vector_diagnostics,
            "lexical_diagnostics": lexical_diagnostics,
            "result_counts": {
                "eligible": len(eligible_job_urls),
                "scored": len(fused),
                "production": len(production_rows),
                "audit": len(audit_rows),
            },
        },
        "candidate_query": candidate_query,
    }


def run_vector_search(
    profile: dict[str, Any],
    passed_job_urls: list[str],
    config: dict[str, Any],
    top_n: int | None = None,
    *,
    structured_jobs: list[dict[str, Any]] | None = None,
    requested_strategy: str = VECTOR_RETRIEVAL_STRATEGY,
    _allow_lexical_fallback: bool = True,
) -> dict[str, Any]:
    """Retrieve passed jobs with lexical signals or compatible vectors."""
    eligible_job_urls = sorted({str(job_url).strip() for job_url in passed_job_urls if str(job_url).strip()})
    if not eligible_job_urls:
        return _empty_vector_search_result()
    requested_strategy = str(requested_strategy or VECTOR_RETRIEVAL_STRATEGY).strip()
    effective_top_n = int(
        top_n if top_n is not None else (config.get("pipeline") or {}).get("vector_search_top_n", 50)
    )
    if requested_strategy == HYBRID_RETRIEVAL_STRATEGY:
        if structured_jobs is None:
            return _unavailable_search_result(
                eligible_job_urls,
                requested_strategy=requested_strategy,
                reason="fallback_data_unavailable",
                config=config,
            )
        channel_depth = len(eligible_job_urls)
        vector_result = run_vector_search(
            profile,
            eligible_job_urls,
            config,
            top_n=channel_depth,
            structured_jobs=structured_jobs,
            requested_strategy=VECTOR_RETRIEVAL_STRATEGY,
            _allow_lexical_fallback=False,
        )
        lexical_result = _lexical_search_result(
            profile,
            eligible_job_urls,
            config,
            channel_depth,
            structured_jobs,
            requested_strategy=requested_strategy,
        )
        return _hybrid_search_result(
            vector_result=vector_result,
            lexical_result=lexical_result,
            eligible_job_urls=eligible_job_urls,
            top_n=effective_top_n,
            channel_depth=channel_depth,
        )
    if requested_strategy == LEXICAL_RETRIEVAL_STRATEGY:
        if structured_jobs is None:
            return _unavailable_search_result(
                eligible_job_urls,
                requested_strategy=requested_strategy,
                reason="fallback_data_unavailable",
                config=config,
            )
        return _lexical_search_result(
            profile,
            eligible_job_urls,
            config,
            int(top_n if top_n is not None else (config.get("pipeline") or {}).get("vector_search_top_n", 50)),
            structured_jobs,
            requested_strategy=requested_strategy,
        )
    effective_top_n = top_n if top_n is not None else int(
        (config.get("pipeline") or {}).get("vector_search_top_n") or config.get("vector_top_n", 50)
    )
    audit_sample_n = int((config.get("pipeline") or {}).get("shortlist_audit_sample_n", 0))
    candidate_query_record = resolve_candidate_query_embedding(profile, config)
    embedding_backend_id = str(candidate_query_record.get("embedding_backend_id") or "").strip()
    if embedding_backend_id and embedding_backend_id != "sentence_transformers":
        if structured_jobs is None:
            return _unavailable_search_result(
                eligible_job_urls,
                requested_strategy=requested_strategy,
                reason="fallback_data_unavailable",
                config=config,
            )
        return _lexical_search_result(
            profile,
            eligible_job_urls,
            config,
            len(eligible_job_urls),
            structured_jobs,
            requested_strategy=requested_strategy,
            fallback_reason="non_semantic_embedding_backend",
            embedding_backend_id=embedding_backend_id or "sqlite_deterministic_local",
        )
    candidate_embedding = _validated_vector(candidate_query_record.get("embedding"))
    candidate_query = {
        key: value
        for key, value in candidate_query_record.items()
        if key != "embedding"
    }
    placeholders = ",".join(["?"] * len(eligible_job_urls))
    expected_contract = str(build_embedding_contract_fingerprint(config)["fingerprint"])
    current_signatures = {
        str(job.get("job_url") or ""): str(job.get("embedding_input_signature") or "")
        for job in list(structured_jobs or [])
        if isinstance(job, dict) and str(job.get("job_url") or "")
    }
    with sqlite_connection(sqlite_path(), timeout=30) as conn:
        configure_sqlite_connection(conn)
        embedding_columns = {
            str(row[1]) for row in conn.execute("PRAGMA table_info(job_embeddings)").fetchall()
        }
        embedding_table_available = bool(embedding_columns)
        contract_expression = (
            "embedding_contract_fingerprint"
            if "embedding_contract_fingerprint" in embedding_columns
            else "''"
        )
        contract_select = f"{contract_expression} AS embedding_contract_fingerprint"
        signature_expression = (
            "embedding_input_signature"
            if "embedding_input_signature" in embedding_columns
            else "''"
        )
        signature_select = f"{signature_expression} AS embedding_input_signature"
        query = f"""        WITH ranked_embeddings AS (
          SELECT
            id,
            job_url,
            embedding_json,
                created_at,
            {contract_select},
            {signature_select},
            ROW_NUMBER() OVER (
              PARTITION BY job_url, COALESCE({signature_expression}, ''), COALESCE({contract_expression}, '')
              ORDER BY created_at DESC, id DESC
            ) AS row_number,
            COUNT(*) OVER (PARTITION BY job_url) AS embedding_row_count
          FROM job_embeddings
          WHERE chunk_type = 'job_summary' AND job_url IN ({placeholders})
        )
        SELECT job_url, embedding_json, embedding_contract_fingerprint, embedding_input_signature, embedding_row_count, created_at, id
        FROM ranked_embeddings
        WHERE row_number = 1
        ORDER BY job_url, created_at DESC, id DESC
        """
        try:
            rows = list(conn.execute(query, tuple(eligible_job_urls)).fetchall())
        except sqlite3.OperationalError as exc:
            if "no such table" not in str(exc).lower():
                raise
            rows = []
            embedding_table_available = False

    latest_by_url: dict[str, tuple[str, str, str, int, str, int]] = {}
    incompatible_contract_urls: list[str] = []
    for job_url, embedding_json, contract_fingerprint, input_signature, row_count, created_at, embedding_id in rows:
        normalized_url = str(job_url)
        signature = str(input_signature or "")
        current_signature = current_signatures.get(normalized_url, "")
        if current_signature and signature != current_signature:
            continue
        if embedding_table_available and "embedding_contract_fingerprint" in embedding_columns:
            if str(contract_fingerprint or "") != expected_contract:
                incompatible_contract_urls.append(normalized_url)
                continue
        candidate = (
            str(embedding_json),
            str(contract_fingerprint or ""),
            signature,
            int(row_count),
            str(created_at or ""),
            int(embedding_id),
        )
        previous = latest_by_url.get(normalized_url)
        if previous is None or (candidate[4], candidate[5]) >= (previous[4], previous[5]):
            latest_by_url[normalized_url] = candidate
    missing_urls = sorted(set(eligible_job_urls) - set(latest_by_url))
    invalid_urls: list[str] = []
    duplicate_urls = sorted(job_url for job_url, (_, _, _, count, _, _) in latest_by_url.items() if count > 1)
    scored: list[dict[str, Any]] = []
    for job_url in eligible_job_urls:
        latest = latest_by_url.get(job_url)
        if latest is None:
            continue
        embedding_json, embedding_contract_fingerprint, _, _, _, _ = latest
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
        normalized_embedding = _normalized_vector(job_embedding)
        scored.append(
            {
                "job_url": job_url,
                "vector_similarity": _cosine_similarity(candidate_embedding, job_embedding),
                "normalized_embedding": normalized_embedding,
                "embedding_vector_fingerprint": build_contract_fingerprint(
                    {"normalized_embedding": normalized_embedding}
                ),
                "embedding_contract_fingerprint": embedding_contract_fingerprint,
            }
        )
    fallback_reason = None
    if candidate_embedding is None:
        fallback_reason = "candidate_embedding_unavailable"
    elif incompatible_contract_urls:
        fallback_reason = "incompatible_embedding_contract"
    elif missing_urls:
        fallback_reason = "missing_job_embeddings"
    elif invalid_urls:
        fallback_reason = "invalid_job_embeddings"
    elif eligible_job_urls and not scored:
        fallback_reason = "no_compatible_vectors"
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
    fallback_rows: list[dict[str, Any]] = []
    fallback_diagnostics: dict[str, Any] = {}
    if _allow_lexical_fallback and fallback_reason and structured_jobs is not None:
        lexical_result = _lexical_search_result(
            profile,
            eligible_job_urls,
            config,
            effective_top_n,
            structured_jobs,
            requested_strategy=requested_strategy,
            fallback_reason=fallback_reason,
            embedding_backend_id=embedding_backend_id,
        )
        admitted_urls = {str(row.get("job_url") or "") for row in production_rows}
        fallback_candidates = [
            {
                **row,
                "shortlist_origin": "lexical_fallback",
                "retrieval_strategy": LEXICAL_RETRIEVAL_STRATEGY,
                "fallback_source_rank": row.get("vector_rank"),
            }
            for row in lexical_result.get("production_rows") or []
            if str(row.get("job_url") or "") not in admitted_urls
        ]
        combined_candidates = [*production_rows, *fallback_candidates]
        combined_candidates.sort(
            key=lambda row: (
                -float(
                    row.get("vector_similarity")
                    if row.get("shortlist_origin") == "vector_search"
                    else row.get("retrieval_score") or 0.0
                ),
                str(row.get("job_url") or ""),
            )
        )
        admitted_candidates = combined_candidates[:effective_top_n]
        admitted_urls = {str(row.get("job_url") or "") for row in admitted_candidates}
        displaced_vector_rows = [
            row
            for row in production_rows
            if str(row.get("job_url") or "") not in admitted_urls
        ]
        displaced_vector_urls = [str(row.get("job_url") or "") for row in displaced_vector_rows]
        fallback_rows = []
        for row in admitted_candidates:
            if row.get("shortlist_origin") != "lexical_fallback":
                continue
            if displaced_vector_urls:
                row["rescued_displaced_job_url"] = displaced_vector_urls.pop(0)
                row["rescue_reason"] = "lexical_recovery_competed_with_vector_cutoff"
            fallback_rows.append(row)
        production_rows = admitted_candidates
        fallback_diagnostics = dict(lexical_result.get("diagnostics") or {})
        fallback_urls = {str(row.get("job_url") or "") for row in fallback_rows}
        seen_audit_urls = {
            str(row.get("job_url") or "")
            for row in [*production_rows, *audit_candidates]
            if str(row.get("job_url") or "")
        }
        for row in [
            *displaced_vector_rows,
            *(lexical_result.get("production_rows") or []),
            *(lexical_result.get("audit_rows") or []),
        ]:
            job_url = str(row.get("job_url") or "")
            if not job_url or job_url in seen_audit_urls:
                continue
            audit_candidates.append(row)
            seen_audit_urls.add(job_url)
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
    embedding_metadata = build_embedding_backend_metadata(config)
    effective_embedding_metadata = _effective_embedding_metadata(config, embedding_backend_id)
    return {
        "production_rows": production_rows,
        "audit_rows": audit_rows,
        "diagnostics": {
            "retrieval_strategy": VECTOR_RETRIEVAL_STRATEGY,
            "requested_strategy": requested_strategy,
            "effective_strategy": (
                MIXED_FALLBACK_RETRIEVAL_STRATEGY
                if fallback_reason and production_rows and ranked_rows
                else LEXICAL_RETRIEVAL_STRATEGY
                if fallback_reason
                else VECTOR_RETRIEVAL_STRATEGY
            ),
            "fallback_used": fallback_reason is not None,
            "fallback_reason": fallback_reason,
            "backend_id": embedding_metadata["backend_id"],
            "embedding_backend_id": embedding_backend_id,
            "requested_embedding_backend_id": embedding_metadata["backend_id"],
            "effective_embedding_backend_metadata": effective_embedding_metadata,
            "configured_model": embedding_metadata["configured_model"],
            "dimension": len(candidate_embedding) if candidate_embedding is not None else embedding_metadata["dimension"],
            "model_revision": embedding_metadata["model_revision"],
            "preprocessing_version": embedding_metadata["preprocessing_version"],
            "contract_fingerprint": expected_contract,
            "eligible_jobs_total": eligible_total,
            "scored_jobs_total": len(ranked_rows),
            "fallback_candidate_total": int(
                fallback_diagnostics.get("scored_jobs_total") or len(fallback_rows)
            ),
            "fallback_admitted_total": len(fallback_rows),
            "vector_admitted_total": sum(
                1 for row in production_rows if row.get("shortlist_origin") == "vector_search"
            ),
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
            "incompatible_embedding_contract_total": len(incompatible_contract_urls),
            "incompatible_embedding_contract_sample": incompatible_contract_urls[:VECTOR_DIAGNOSTIC_SAMPLE_LIMIT],
            "duplicate_job_embedding_total": len(duplicate_urls),
            "duplicate_job_embedding_sample": duplicate_urls[:VECTOR_DIAGNOSTIC_SAMPLE_LIMIT],
            "raw_hit_anomaly_total": 0,
            "raw_hit_anomaly_sample": [],
            "result_counts": {
                "eligible": eligible_total,
                "scored": len(ranked_rows),
                "production": len(production_rows),
                "audit": len(audit_rows),
            },
        },
        "candidate_query": candidate_query,
    }


# ── integration: store shortlist ──────────────────────────────────────────────

def store_shortlist(
    shortlist: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Insert vector shortlist rows into local sqlite store."""
    shortlist = [
        item for item in shortlist
        if str(item.get("retrieval_strategy") or VECTOR_RETRIEVAL_STRATEGY) == VECTOR_RETRIEVAL_STRATEGY
    ]
    if not shortlist:
        return
    now = datetime.now(tz=timezone.utc).isoformat()

    def _write_shortlist() -> None:
        with sqlite_connection(sqlite_path(), timeout=30) as conn:
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





