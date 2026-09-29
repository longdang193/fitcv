"""@meta
name: embeddings
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.embeddings.
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
import sqlite3
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from fitcv.config import get_embedding_model
from fitcv.shortlist_runtime import (
    build_contract_fingerprint,
    configure_sqlite_connection,
    hash_payload,
    normalize_text_scalar,
    run_sqlite_io_retry,
    sqlite_path,
)
from fitcv.persistence import sqlite_connection

JOB_SUMMARY_CHUNK_TYPE = "job_summary"
SHORTLIST_SUMMARY_SCHEMA_VERSION = "shortlist_job_summary_v2"
EMBEDDING_CONTRACT_VERSION = "embedding_v2"
SHORTLIST_DEFAULT_EMBEDDING_MODEL = "text-embedding-005"
REUSED_CACHED_EMBEDDING_STATUS = "reused_cached_embedding"
FRESH_EMBEDDING_STATUS = "fresh_embedding"
SQLITE_EMBED_DIM = 256
EMBEDDING_FAILURE_POLICY_DEFAULT = "deterministic_fallback"
EMBEDDING_FAILURE_POLICY_RAISE = "raise"
SENTENCE_TRANSFORMERS_BACKEND = "sentence_transformers"
DETERMINISTIC_EMBEDDING_MODEL = "hash-v1"
DEFAULT_SENTENCE_TRANSFORMERS_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_SENTENCE_TRANSFORMERS_REVISION = "e8f8c211226b894fcb81acc59f3b34ba3efd5f42"
DEFAULT_EMBEDDING_PREPROCESSING_VERSION = "normalize_whitespace_v1"
SENTENCE_TRANSFORMERS_DEFAULT_DIM = 384

logger = logging.getLogger(__name__)




def _normalize_summary_scalar(value: Any) -> str:
    """Collapse whitespace while preserving human-readable casing."""
    return normalize_text_scalar(value)


def _stable_sorted_unique_strings(values: list[Any]) -> list[str]:
    normalized_by_key: dict[str, str] = {}
    for value in values:
        normalized = _normalize_summary_scalar(value)
        if not normalized:
            continue
        normalized_by_key.setdefault(normalized.casefold(), normalized)
    return [
        normalized_by_key[key]
        for key in sorted(normalized_by_key)
    ]


def _preferred_skill_values(
    structured_jd: dict[str, Any],
    *,
    canonical_field: str,
    raw_field: str,
) -> list[str]:
    canonical_values = structured_jd.get(canonical_field) or []
    if canonical_values:
        return _stable_sorted_unique_strings(list(canonical_values))
    return _stable_sorted_unique_strings(list(structured_jd.get(raw_field) or []))


def build_job_summary_signature_payload(structured_jd: dict[str, Any]) -> dict[str, Any]:
    """Build the stable shortlist summary payload used for embedding reuse."""
    payload = {
        "title": _normalize_summary_scalar(structured_jd.get("title") or structured_jd.get("job_title") or ""),
        "location_type": _normalize_summary_scalar(structured_jd.get("location_type") or ""),
        "seniority": _normalize_summary_scalar(structured_jd.get("seniority") or ""),
        "job_family": _normalize_summary_scalar(structured_jd.get("job_family") or ""),
        "required_skills": _preferred_skill_values(
            structured_jd,
            canonical_field="required_skills_canonical",
            raw_field="required_skills",
        ),
        "preferred_skills": _preferred_skill_values(
            structured_jd,
            canonical_field="preferred_skills_canonical",
            raw_field="preferred_skills",
        ),
    }
    return {
        key: value
        for key, value in payload.items()
        if value not in ("", [], None)
    }


def build_job_summary_signature_record(structured_jd: dict[str, Any]) -> dict[str, Any]:
    """Return the stable shortlist summary payload plus its hash signature."""
    payload = build_job_summary_signature_payload(structured_jd)
    payload_json, signature = hash_payload(payload)
    return {
        "payload": payload,
        "payload_json": payload_json,
        "signature": signature,
    }


def _semantic_alignment_config(config: dict[str, Any]) -> dict[str, Any]:
    return dict((config.get("cv_analysis") or {}).get("semantic_alignment") or {})


def get_embedding_backend(config: dict[str, Any]) -> str:
    backend = str(
        config.get("embedding_backend")
        or _semantic_alignment_config(config).get("embedding_backend")
        or "sqlite_deterministic_local"
    ).strip().lower()
    return backend if backend in {"sqlite_deterministic_local", SENTENCE_TRANSFORMERS_BACKEND} else "sqlite_deterministic_local"


def get_shortlist_embedding_model(config: dict[str, Any]) -> str:
    """Return the embedding model identifier used for shortlist job summaries."""
    return str(
        config.get("shortlist_embedding_model")
        or config.get("embedding_model")
        or get_embedding_model(config)
        or SHORTLIST_DEFAULT_EMBEDDING_MODEL
    )


def get_embedding_model_revision(config: dict[str, Any], model_name: str | None = None) -> str | None:
    configured_model = str(model_name or get_shortlist_embedding_model(config))
    revision = config.get("embedding_model_revision") or _semantic_alignment_config(config).get("embedding_model_revision")
    if revision:
        return str(revision)
    if configured_model == DEFAULT_SENTENCE_TRANSFORMERS_MODEL:
        return DEFAULT_SENTENCE_TRANSFORMERS_REVISION
    return None


def get_embedding_preprocessing_version(config: dict[str, Any]) -> str:
    return str(
        config.get("embedding_preprocessing_version")
        or _semantic_alignment_config(config).get("embedding_preprocessing_version")
        or DEFAULT_EMBEDDING_PREPROCESSING_VERSION
    )


def get_embedding_dimension(config: dict[str, Any], backend: str | None = None) -> int:
    selected_backend = backend or get_embedding_backend(config)
    if selected_backend == SENTENCE_TRANSFORMERS_BACKEND:
        return int(config.get("embedding_dimension") or _semantic_alignment_config(config).get("embedding_dimension") or SENTENCE_TRANSFORMERS_DEFAULT_DIM)
    return SQLITE_EMBED_DIM


def build_embedding_contract_fingerprint(
    config: dict[str, Any],
    *,
    configured_model: str | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    selected_backend = backend or get_embedding_backend(config)
    model_name = str(configured_model or get_shortlist_embedding_model(config))
    payload = {
        "contract_version": EMBEDDING_CONTRACT_VERSION,
        "embedding_backend": selected_backend,
        "embedding_dimension": get_embedding_dimension(config, selected_backend),
        "embedding_model": model_name,
        "embedding_model_revision": get_embedding_model_revision(config, model_name),
        "embedding_preprocessing_version": get_embedding_preprocessing_version(config),
        "summary_schema_version": SHORTLIST_SUMMARY_SCHEMA_VERSION,
    }
    fingerprint = build_contract_fingerprint(payload)
    return {
        "payload": payload,
        "fingerprint": fingerprint,
    }


def build_embedding_backend_metadata(
    config: dict[str, Any],
    *,
    configured_model: str | None = None,
    backend: str | None = None,
) -> dict[str, Any]:
    contract = build_embedding_contract_fingerprint(
        config,
        configured_model=configured_model,
        backend=backend,
    )
    payload = contract["payload"]
    return {
        "backend_id": str(payload["embedding_backend"]),
        "configured_model": str(payload["embedding_model"]),
        "dimension": int(payload["embedding_dimension"]),
        "model_revision": payload["embedding_model_revision"],
        "preprocessing_version": str(payload["embedding_preprocessing_version"]),
        "contract_fingerprint": str(contract["fingerprint"]),
    }




# ── job summary text ──────────────────────────────────────────────────────────

def build_job_summary_text(structured_jd: dict[str, Any]) -> str:
    """Build a deterministic labelled-section string for embedding.

    Format (structured text gives better embedding quality than free join):

        Title: <title>
        Required skills: <comma-joined required_skills>
        Preferred skills: <comma-joined preferred_skills>
        Location type: <location_type>
        Seniority: <seniority>
        Job family: <job_family>

    All fields are optional; missing/empty fields are omitted from the output.
    """
    payload = build_job_summary_signature_payload(structured_jd)
    parts: list[str] = []

    def _append(label: str, value: str) -> None:
        if value:
            parts.append(f"{label}: {value}")

    _append("Title", str(payload.get("title") or ""))
    _append(
        "Required skills",
        ", ".join(payload.get("required_skills", []) or []),
    )
    _append(
        "Preferred skills",
        ", ".join(payload.get("preferred_skills", []) or []),
    )
    _append("Location type", str(payload.get("location_type") or ""))
    _append("Seniority", str(payload.get("seniority") or ""))
    _append("Job family", str(payload.get("job_family") or ""))

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
        "chunk_type": JOB_SUMMARY_CHUNK_TYPE,
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


# ── integration: local embedding ─────────────────────────────────────────────

def _deterministic_local_embedding(text: str) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values: list[float] = []
    for idx in range(SQLITE_EMBED_DIM):
        b = digest[idx % len(digest)]
        values.append((float(b) / 127.5) - 1.0)
    return values


def get_embedding_failure_policy(config: dict[str, Any]) -> str:
    policy = str(config.get("embedding_failure_policy") or EMBEDDING_FAILURE_POLICY_DEFAULT).strip().lower()
    if policy in {EMBEDDING_FAILURE_POLICY_DEFAULT, EMBEDDING_FAILURE_POLICY_RAISE}:
        return policy
    return EMBEDDING_FAILURE_POLICY_DEFAULT


@lru_cache(maxsize=4)
def _load_sentence_transformer_model(model_name: str, revision: str | None) -> Any:
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(
        model_name,
        revision=revision,
        device="cpu",
        trust_remote_code=False,
    )


def _sentence_transformer_embedding(text: str, model_name: str, revision: str | None) -> list[float]:
    model = _load_sentence_transformer_model(model_name, revision)
    encoded = model.encode(
        [" ".join(text.split()).strip()],
        convert_to_numpy=True,
        normalize_embeddings=False,
        show_progress_bar=False,
    )
    row = encoded[0]
    values = row.tolist() if hasattr(row, "tolist") else row
    return [float(value) for value in values]


def generate_embedding(
    text: str,
    config: dict[str, Any],
    *,
    model_name: str | None = None,
) -> list[float]:
    return list(generate_embedding_with_metadata(text, config, model_name=model_name)["embedding"])


def generate_embedding_with_metadata(
    text: str,
    config: dict[str, Any],
    *,
    model_name: str | None = None,
) -> dict[str, Any]:
    backend = get_embedding_backend(config)
    if backend != SENTENCE_TRANSFORMERS_BACKEND:
        vector = _deterministic_local_embedding(text)
        return {
            "embedding": vector,
            **build_embedding_backend_metadata(config, backend=backend),
        }
    selected_model = str(model_name or get_shortlist_embedding_model(config))
    revision = get_embedding_model_revision(config, selected_model)
    try:
        vector = _sentence_transformer_embedding(text, selected_model, revision)
        expected_dimension = get_embedding_dimension(config, backend)
        if len(vector) != expected_dimension:
            raise ValueError(
                f"embedding dimension mismatch: expected {expected_dimension}, got {len(vector)}"
            )
        return {
            "embedding": vector,
            **build_embedding_backend_metadata(
                config,
                configured_model=selected_model,
                backend=backend,
            ),
        }
    except Exception as exc:
        if get_embedding_failure_policy(config) == EMBEDDING_FAILURE_POLICY_RAISE:
            raise RuntimeError(
                f"sentence-transformers embedding backend unavailable: {selected_model}@{revision or 'default'}"
            ) from exc
        logger.warning("sentence-transformers backend unavailable; using deterministic fallback", exc_info=True)
        vector = _deterministic_local_embedding(text)
        return {
            "embedding": vector,
            **build_embedding_backend_metadata(
                config,
                configured_model=DETERMINISTIC_EMBEDDING_MODEL,
                backend="sqlite_deterministic_local",
            ),
        }




def _ensure_sqlite_embedding_tables(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_embeddings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          job_url TEXT NOT NULL,
          chunk_type TEXT NOT NULL,
          chunk_text TEXT NOT NULL,
          embedding_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          embedding_input_signature TEXT,
          embedding_contract_fingerprint TEXT,
          embedding_input_signature_payload_json TEXT
        )
        """
    )
    columns = {str(row[1]) for row in conn.execute("PRAGMA table_info(job_embeddings)").fetchall()}
    for name, definition in (
        ("embedding_input_signature", "TEXT"),
        ("embedding_contract_fingerprint", "TEXT"),
        ("embedding_input_signature_payload_json", "TEXT"),
    ):
        if name not in columns:
            conn.execute(f"ALTER TABLE job_embeddings ADD COLUMN {name} {definition}")
    conn.execute(
        "DELETE FROM job_embeddings WHERE embedding_input_signature IS NOT NULL AND embedding_contract_fingerprint IS NOT NULL AND id NOT IN (SELECT MAX(id) FROM job_embeddings WHERE embedding_input_signature IS NOT NULL AND embedding_contract_fingerprint IS NOT NULL GROUP BY job_url, chunk_type, embedding_input_signature, embedding_contract_fingerprint)"
    )
    conn.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_job_embeddings_contract ON job_embeddings(job_url, chunk_type, embedding_input_signature, embedding_contract_fingerprint)"
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS candidate_embeddings (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          evidence_id TEXT NOT NULL,
          source_ref_id TEXT NOT NULL,
          evidence_type TEXT NOT NULL,
          chunk_text TEXT NOT NULL,
          embedding_json TEXT NOT NULL,
          created_at TEXT NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_job_embeddings_job_url_created ON job_embeddings(job_url, created_at DESC)")


# ── integration: batch embed + store jobs ─────────────────────────────────────

def embed_and_store_jobs(
    structured_jobs: list[dict[str, Any]],
    config: dict[str, Any],
) -> int:
    """Embed each job summary and store rows in local sqlite table."""
    if not structured_jobs:
        return 0
    if str(config.get("retrieval_strategy") or "").strip() == "lexical_v1":
        for job in structured_jobs:
            job["embedding_reuse_status"] = "not_applicable_lexical"
        return 0
    now = datetime.now(tz=timezone.utc).isoformat()
    embedding_contract = build_embedding_contract_fingerprint(config)
    rows: list[dict[str, Any]] = []
    contract_fingerprint = embedding_contract["fingerprint"]
    with sqlite_connection(sqlite_path(), timeout=30) as conn:
        configure_sqlite_connection(conn)
        _ensure_sqlite_embedding_tables(conn)
        existing = {
            (str(row[0]), str(row[1]), str(row[2]), str(row[3]))
            for row in conn.execute(
                "SELECT job_url, chunk_type, embedding_input_signature, embedding_contract_fingerprint FROM job_embeddings"
            )
        }
    for job in structured_jobs:
        signature_record = build_job_summary_signature_record(job)
        job["embedding_input_signature"] = signature_record["signature"]
        job["embedding_contract_fingerprint"] = contract_fingerprint
        chunk = build_job_summary_chunk(job)[0]
        key = (str(job.get("job_url") or ""), chunk["chunk_type"], signature_record["signature"], contract_fingerprint)
        if key in existing:
            job["embedding_reuse_status"] = REUSED_CACHED_EMBEDDING_STATUS
            continue
        embedding_result = generate_embedding_with_metadata(chunk["chunk_text"], config)
        vector = list(embedding_result["embedding"])
        actual_contract_fingerprint = str(embedding_result["contract_fingerprint"])
        job["embedding_contract_fingerprint"] = actual_contract_fingerprint
        job["embedding_reuse_status"] = FRESH_EMBEDDING_STATUS
        rows.append(
            {
                "job_url": str(job.get("job_url") or ""),
                "chunk_type": chunk["chunk_type"],
                "chunk_text": chunk["chunk_text"],
                "embedding_json": json.dumps(vector),
                "created_at": now,
                "embedding_input_signature": signature_record["signature"],
                "embedding_contract_fingerprint": actual_contract_fingerprint,
                "embedding_input_signature_payload_json": signature_record["payload_json"],
            }
        )

    def _write_job_embeddings() -> None:
        with sqlite_connection(sqlite_path(), timeout=30) as conn:
            configure_sqlite_connection(conn)
            _ensure_sqlite_embedding_tables(conn)
            conn.executemany(
                """
                INSERT INTO job_embeddings(
                  job_url, chunk_type, chunk_text, embedding_json, created_at,
                  embedding_input_signature, embedding_contract_fingerprint, embedding_input_signature_payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(job_url, chunk_type, embedding_input_signature, embedding_contract_fingerprint) DO NOTHING
                """,
                [
                    (
                        row["job_url"],
                        row["chunk_type"],
                        row["chunk_text"],
                        row["embedding_json"],
                        row["created_at"],
                        row["embedding_input_signature"],
                        row["embedding_contract_fingerprint"],
                        row["embedding_input_signature_payload_json"],
                    )
                    for row in rows
                ],
            )
            conn.commit()

    run_sqlite_io_retry(_write_job_embeddings)
    return len(rows)


# ── integration: batch embed + store candidate ────────────────────────────────

def embed_and_store_candidate(
    profile: dict[str, Any],
    config: dict[str, Any],
) -> int:
    """Embed candidate evidence chunks and store rows in local sqlite table."""
    now = datetime.now(tz=timezone.utc).isoformat()
    candidate_chunks = build_candidate_chunks(profile)
    rows = []
    for chunk in candidate_chunks:
        vector = generate_embedding(chunk["chunk_text"], config)
        rows.append(
            (
                chunk["evidence_id"],
                chunk["source_ref_id"],
                chunk["evidence_type"],
                chunk["chunk_text"],
                json.dumps(vector),
                now,
            )
        )

    def _write_candidate_embeddings() -> None:
        with sqlite_connection(sqlite_path(), timeout=30) as conn:
            configure_sqlite_connection(conn)
            _ensure_sqlite_embedding_tables(conn)
            conn.executemany(
                """
                INSERT INTO candidate_embeddings(
                  evidence_id, source_ref_id, evidence_type, chunk_text, embedding_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                rows,
            )
            conn.commit()

    run_sqlite_io_retry(_write_candidate_embeddings)
    return len(rows)
