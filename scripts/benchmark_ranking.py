"""Benchmark deterministic ranking replay without external services."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv.ranking import rank_jobs
from fitcv.embeddings import (
    DEFAULT_SENTENCE_TRANSFORMERS_MODEL,
    DEFAULT_SENTENCE_TRANSFORMERS_REVISION,
    SENTENCE_TRANSFORMERS_BACKEND,
    embed_and_store_jobs,
)
from fitcv.vector_search import LEXICAL_RETRIEVAL_STRATEGY, VECTOR_RETRIEVAL_STRATEGY, run_vector_search

_EVALUATOR_FIELDS = {
    "label",
    "relevance_grade",
    "split",
    "reviewed",
    "baseline_fit",
    "ai_score",
    "ai_score_status",
}
_PRIMARY_RELEVANCE_GRADE = 2
_ALLOWED_SPLITS = {"calibration", "held_out"}
_LABEL_BY_GRADE = {0: "irrelevant", 1: "borderline", 2: "relevant", 3: "relevant"}


def _percentile(values: list[float], percentile: float) -> float:
    return sorted(values)[max(0, math.ceil(percentile * len(values)) - 1)]


def _fixture_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture_role(data: dict[str, Any]) -> str:
    declared = str(data.get("fixture_role") or "").strip().lower()
    if declared in {"smoke", "source_backed"}:
        return declared
    schema_version = str(data.get("schema_version") or "").lower()
    return "source_backed" if "source_backed" in schema_version else "smoke"


def _ranked(rows: list[dict[str, Any]], key: str, top_n: int) -> list[dict[str, Any]]:
    return sorted(
        rows,
        key=lambda row: (
            -(float(row[key]) if row.get(key) is not None else float("-inf")),
            str(row["candidate_id"]),
        ),
    )[:top_n]


def _relevant(rows: list[dict[str, Any]]) -> set[str]:
    return {
        str(row["candidate_id"])
        for row in rows
        if int(row.get("relevance_grade") or 0) >= _PRIMARY_RELEVANCE_GRADE
    }


def _recall(returned_ids: list[str] | set[str], eligible_rows: list[dict[str, Any]]) -> float:
    returned = set(returned_ids)
    relevant = _relevant(eligible_rows)
    return len(returned & relevant) / len(relevant) if relevant else 1.0


def _precision(returned_ids: list[str] | set[str], eligible_rows: list[dict[str, Any]]) -> float:
    returned_ids = set(returned_ids)
    eligible_ids = {str(row["candidate_id"]) for row in eligible_rows}
    returned = returned_ids & eligible_ids
    return len(returned & _relevant(eligible_rows)) / len(returned) if returned else 1.0


def _mrr(returned: list[dict[str, Any]], top_n: int) -> float:
    for index, row in enumerate(returned[:top_n], start=1):
        if int(row.get("relevance_grade") or 0) >= _PRIMARY_RELEVANCE_GRADE:
            return 1 / index
    return 0.0


def _ndcg(returned: list[dict[str, Any]], eligible_rows: list[dict[str, Any]], top_n: int) -> float:
    ranked = returned[:top_n]
    dcg = sum(
        (2 ** int(row.get("relevance_grade") or 0) - 1) / math.log2(index + 2)
        for index, row in enumerate(ranked)
    )
    ideal = sorted(
        (int(row.get("relevance_grade") or 0) for row in eligible_rows),
        reverse=True,
    )[:top_n]
    idcg = sum((2**grade - 1) / math.log2(index + 2) for index, grade in enumerate(ideal))
    return dcg / idcg if idcg else 1.0


def _split_metric_rows(
    retrieved_ids: list[str] | set[str],
    ranked_rows: list[dict[str, Any]],
    source_rows: list[dict[str, Any]],
    retrieval_top_n: int,
    ranking_top_n: int,
    ndcg_top_n: int,
) -> dict[str, dict[str, float | int]]:
    metrics: dict[str, dict[str, float | int]] = {}
    for split in ("calibration", "held_out"):
        eligible = [row for row in source_rows if row.get("split") == split]
        eligible_by_id = {str(row["candidate_id"]): row for row in eligible}
        retrieved = [eligible_by_id[item] for item in retrieved_ids if item in eligible_by_id]
        ranked = [row for row in ranked_rows if row.get("split") == split]
        ranked_ids = {str(row.get("candidate_id")) for row in ranked[:ranking_top_n]}
        metrics[split] = {
            "count": len(eligible),
            "retrieval_recall_at_n": _recall(retrieved_ids, eligible),
            "retrieval_precision_at_n": _precision(retrieved_ids, eligible),
            "retrieval_mrr_at_n": _mrr(retrieved, retrieval_top_n),
            "retrieval_ndcg_at_n": _ndcg(retrieved, eligible, ndcg_top_n),
            "ranking_recall_at_n": _recall(ranked_ids, eligible),
            "ranking_precision_at_n": _precision(ranked_ids, eligible),
            "ranking_mrr_at_n": _mrr(ranked, ranking_top_n),
            "ranking_ndcg_at_n": _ndcg(ranked, eligible, ndcg_top_n),
        }
    return metrics


def _validate_evaluation_input(profiles: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    seen_candidate_ids: set[str] = set()
    source_ids_by_profile: set[tuple[str, str]] = set()
    source_group_profiles: dict[str, set[str]] = {}
    for profile_id, pool in profiles.items():
        rows = list(pool.get("candidates") or [])
        if not rows:
            errors.append(f"{profile_id}:empty_candidate_pool")
            continue
        grades = {int(row.get("relevance_grade") or 0) for row in rows}
        if 0 not in grades or 1 not in grades or not any(grade > 1 for grade in grades):
            errors.append(f"{profile_id}:missing_mixed_relevance_classes")
        splits = {str(row.get("split") or "") for row in rows}
        invalid_splits = sorted(splits - _ALLOWED_SPLITS)
        if invalid_splits:
            errors.append(f"{profile_id}:invalid_split_values:{','.join(invalid_splits)}")
        if not _ALLOWED_SPLITS.issubset(splits):
            errors.append(f"{profile_id}:missing_calibration_or_held_out_split")
        retrieval_top_n = int(pool.get("retrieval_top_n", 50))
        ranking_top_n = int(pool.get("ranking_top_n", 12))
        ndcg_top_n = int(pool.get("ndcg_top_n", 15))
        if retrieval_top_n <= 0:
            errors.append(f"{profile_id}:retrieval_top_n_must_be_positive")
        if retrieval_top_n >= len(rows):
            errors.append(f"{profile_id}:retrieval_top_n_must_be_less_than_pool_size")
        if ranking_top_n <= 0:
            errors.append(f"{profile_id}:ranking_top_n_must_be_positive")
        elif ranking_top_n > retrieval_top_n:
            errors.append(f"{profile_id}:ranking_top_n_must_not_exceed_retrieval_top_n")
        if ndcg_top_n <= 0:
            errors.append(f"{profile_id}:ndcg_top_n_must_be_positive")
        elif ndcg_top_n > ranking_top_n:
            errors.append(f"{profile_id}:ndcg_top_n_must_not_exceed_ranking_top_n")
        if not all(bool(row.get("reviewed")) for row in rows):
            errors.append(f"{profile_id}:unreviewed_candidate")
        for row in rows:
            candidate_id = str(row.get("candidate_id") or "")
            if not candidate_id:
                errors.append(f"{profile_id}:missing_candidate_id")
            elif candidate_id in seen_candidate_ids:
                errors.append(f"{profile_id}:{candidate_id}:duplicate_candidate_id")
            seen_candidate_ids.add(candidate_id)
            source_id = str(row.get("source_id") or "").strip()
            if source_id:
                source_key = (profile_id, source_id)
                if source_key in source_ids_by_profile:
                    errors.append(f"{profile_id}:{source_id}:duplicate_source_id")
                source_ids_by_profile.add(source_key)
            source_group = str(row.get("source_group_id") or "").strip()
            if not source_group:
                errors.append(f"{profile_id}:missing_source_group_id")
            else:
                source_group_profiles.setdefault(source_group, set()).add(profile_id)
            label = row.get("label")
            grade = row.get("relevance_grade")
            if label is not None and grade is not None:
                expected_label = _LABEL_BY_GRADE.get(int(grade))
                if expected_label is None or str(label).strip().lower() != expected_label:
                    errors.append(f"{profile_id}:{candidate_id}:label_grade_mismatch")
        for source_group in sorted({str(row.get("source_group_id") or "").strip() for row in rows if row.get("source_group_id")}):
            group_splits = {str(row.get("split") or "") for row in rows if str(row.get("source_group_id") or "").strip() == source_group}
            if len(group_splits) > 1:
                errors.append(f"{profile_id}:{source_group}:source_group_crosses_split")
    for source_group, group_profiles in source_group_profiles.items():
        if len(group_profiles) > 1:
            errors.append(f"source_group:{source_group}:crosses_profiles")
    return errors


def _source_backed_payload_errors(profiles: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for profile_id, pool in profiles.items():
        if not isinstance(pool.get("profile"), dict) or not pool["profile"]:
            errors.append(f"{profile_id}:missing_source_backed_profile")
        for row in pool.get("candidates", []):
            job = row.get("job")
            if not isinstance(job, dict) or not job.get("job_url") or not job.get("description"):
                errors.append(f"{profile_id}:{row.get('candidate_id')}:missing_source_backed_job_payload")
    return errors


def _source_backed_score_errors(profiles: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for profile_id, pool in profiles.items():
        for row in pool.get("candidates", []):
            candidate_id = str(row.get("candidate_id") or "")
            for field in ("baseline_fit", "ai_score"):
                value = row.get(field)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    errors.append(f"{profile_id}:{candidate_id}:missing_or_invalid_{field}")
    return errors


def _apply_score_artifact(
    profiles: dict[str, dict[str, Any]],
    artifact_path: Path,
    fixture_sha256: str,
) -> str:
    try:
        artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("invalid_score_artifact") from exc
    if artifact.get("schema_version") != "ranking_score_artifact_v1":
        raise RuntimeError("invalid_score_artifact_schema")
    if artifact.get("fixture_sha256") != fixture_sha256:
        raise RuntimeError("score_artifact_fixture_sha256_mismatch")
    scores = artifact.get("scores")
    if not isinstance(scores, dict):
        raise RuntimeError("invalid_score_artifact_scores")
    expected = {
        (profile_id, str(row.get("candidate_id"))): row
        for profile_id, pool in profiles.items()
        for row in pool.get("candidates", [])
    }
    supplied: set[tuple[str, str]] = set()
    for profile_id, rows in scores.items():
        if not isinstance(rows, dict):
            raise RuntimeError("invalid_score_artifact_profile_scores")
        for candidate_id, score in rows.items():
            key = (str(profile_id), str(candidate_id))
            row = expected.get(key)
            if row is None or not isinstance(score, dict):
                raise RuntimeError("score_artifact_candidate_mismatch")
            for field in ("baseline_fit", "ai_score"):
                value = score.get(field)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
                    raise RuntimeError("invalid_score_artifact_value")
                row[field] = float(value)
            supplied.add(key)
    if supplied != set(expected):
        raise RuntimeError("score_artifact_candidate_set_mismatch")
    return _fixture_sha256(artifact_path)


def _valid_relevance_grade(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value in range(4)


def _non_empty_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _source_backed_review_errors(profiles: dict[str, dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for profile_id, pool in profiles.items():
        for row in pool.get("candidates", []):
            candidate_id = str(row.get("candidate_id") or "")
            row_grade = row.get("relevance_grade")
            row_label = str(row.get("label") or "").strip().lower()
            if not _valid_relevance_grade(row_grade):
                errors.append(f"{profile_id}:{candidate_id}:missing_or_invalid_final_grade")
            if not row_label:
                errors.append(f"{profile_id}:{candidate_id}:missing_final_label")
            elif _valid_relevance_grade(row_grade) and row_label != _LABEL_BY_GRADE[row_grade]:
                errors.append(f"{profile_id}:{candidate_id}:final_label_grade_mismatch")

            judgments = row.get("judgments")
            if not isinstance(judgments, list) or len(judgments) != 2:
                errors.append(f"{profile_id}:{candidate_id}:requires_exactly_two_judgments")
                continue

            reviewer_ids: set[str] = set()
            judgment_results: list[tuple[str, int]] = []
            for index, judgment in enumerate(judgments):
                if not isinstance(judgment, dict):
                    errors.append(f"{profile_id}:{candidate_id}:judgment_{index}_incomplete")
                    continue
                reviewer_id = str(judgment.get("reviewer_id") or "").strip()
                if not reviewer_id:
                    errors.append(f"{profile_id}:{candidate_id}:judgment_{index}_missing_reviewer_id")
                elif reviewer_id in reviewer_ids:
                    errors.append(f"{profile_id}:{candidate_id}:duplicate_reviewer_identity")
                else:
                    reviewer_ids.add(reviewer_id)
                grade = judgment.get("relevance_grade")
                if not _valid_relevance_grade(grade):
                    errors.append(f"{profile_id}:{candidate_id}:judgment_{index}_invalid_grade")
                label = str(judgment.get("label") or "").strip().lower()
                if not label:
                    errors.append(f"{profile_id}:{candidate_id}:judgment_{index}_missing_label")
                elif _valid_relevance_grade(grade) and label != _LABEL_BY_GRADE[grade]:
                    errors.append(f"{profile_id}:{candidate_id}:judgment_{index}_label_grade_mismatch")
                if not _non_empty_text(judgment.get("rationale")):
                    errors.append(f"{profile_id}:{candidate_id}:judgment_{index}_missing_rationale")
                if not isinstance(judgment.get("evidence"), list) or not judgment["evidence"]:
                    errors.append(f"{profile_id}:{candidate_id}:judgment_{index}_missing_evidence")
                if _valid_relevance_grade(grade) and label:
                    judgment_results.append((label, grade))

            disagreement = len(judgment_results) == 2 and judgment_results[0] != judgment_results[1]
            adjudication = row.get("adjudication")
            if disagreement:
                if not isinstance(adjudication, dict):
                    errors.append(f"{profile_id}:{candidate_id}:disagreement_requires_adjudication")
                else:
                    if not _non_empty_text(adjudication.get("adjudicator_id")):
                        errors.append(f"{profile_id}:{candidate_id}:missing_adjudicator_id")
                    if not _valid_relevance_grade(adjudication.get("final_grade")):
                        errors.append(f"{profile_id}:{candidate_id}:invalid_adjudication_final_grade")
                    if not _non_empty_text(adjudication.get("decision_rationale")):
                        errors.append(f"{profile_id}:{candidate_id}:missing_adjudication_rationale")
                    if (
                        _valid_relevance_grade(adjudication.get("final_grade"))
                        and _valid_relevance_grade(row_grade)
                        and adjudication["final_grade"] != row_grade
                    ):
                        errors.append(f"{profile_id}:{candidate_id}:adjudication_final_grade_mismatch")
    return errors


def _manifest_errors(fixture_path: Path, data: dict[str, Any], fixture_sha256: str) -> list[str]:
    manifest_path = fixture_path.with_name(f"{fixture_path.stem}_manifest.json")
    if not manifest_path.exists():
        return ["source_backed:missing_manifest"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return ["source_backed:invalid_manifest"]
    errors: list[str] = []
    if str(data.get("fixture_status") or "").strip().lower() == "ready":
        if str(manifest.get("fixture_status") or "").strip().lower() != "ready":
            errors.append("source_backed:manifest_fixture_not_ready")
    try:
        expected_fixture_path = fixture_path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        expected_fixture_path = fixture_path.name
    if str(manifest.get("fixture_path") or "").replace("\\", "/") != expected_fixture_path:
        errors.append("source_backed:manifest_fixture_path_mismatch")
    if manifest.get("fixture_sha256") != fixture_sha256:
        errors.append("source_backed:fixture_sha256_mismatch")
    source_snapshot = data.get("source_snapshot") or {}
    source_snapshot_path = str(manifest.get("source_snapshot_path") or "").replace("\\", "/")
    if source_snapshot_path != str(source_snapshot.get("path") or "").replace("\\", "/"):
        errors.append("source_backed:source_snapshot_path_mismatch")
    if manifest.get("source_snapshot_sha256") != source_snapshot.get("sha256"):
        errors.append("source_backed:source_snapshot_sha256_mismatch")
    source_path = REPO_ROOT / source_snapshot_path
    if not source_path.is_file() or _fixture_sha256(source_path) != manifest.get("source_snapshot_sha256"):
        errors.append("source_backed:source_snapshot_file_mismatch")
    profiles = data.get("profiles", {})
    rows = [row for pool in profiles.values() for row in pool.get("candidates", [])]
    if manifest.get("row_count") != len(rows):
        errors.append("source_backed:manifest_row_count_mismatch")
    if manifest.get("profile_count") != len(profiles):
        errors.append("source_backed:manifest_profile_count_mismatch")
    expected_profile_counts = {profile_id: len(pool.get("candidates", [])) for profile_id, pool in profiles.items()}
    if manifest.get("profile_counts") != expected_profile_counts:
        errors.append("source_backed:manifest_profile_counts_mismatch")
    expected_cutoffs = {
        profile_id: {
            "retrieval_top_n": int(pool.get("retrieval_top_n", 50)),
            "ranking_top_n": int(pool.get("ranking_top_n", 12)),
            "ndcg_top_n": int(pool.get("ndcg_top_n", 15)),
        }
        for profile_id, pool in profiles.items()
    }
    if manifest.get("cutoffs") != expected_cutoffs:
        errors.append("source_backed:manifest_cutoffs_mismatch")
    return errors


def _profile_request(profile_id: str, pool: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    profile = dict(pool.get("profile") or {})
    if not profile:
        profile = {
            "preferences": {
                "target_role": profile_id,
                "role_families": [profile_id],
                "domains": [profile_id],
                "location_types": ["remote"],
            },
            "skills": [profile_id],
        }
    jobs: list[dict[str, Any]] = []
    for source in pool["candidates"]:
        job = {
            key: value
            for key, value in dict(source.get("job") or source.get("retrieval") or {}).items()
            if key not in _EVALUATOR_FIELDS
        }
        if not job:
            candidate_id = str(source["candidate_id"])
            job = {
                "job_url": candidate_id,
                "title": profile_id,
                "job_family": profile_id,
                "required_skills_canonical": [profile_id],
                "domain": profile_id,
                "location_type": "remote",
            }
        job["job_url"] = str(job.get("job_url") or source["candidate_id"])
        jobs.append(job)
    return profile, jobs


def build_retrieval_request(
    profile_id: str,
    pool: dict[str, Any],
    *,
    requested_strategy: str = LEXICAL_RETRIEVAL_STRATEGY,
) -> dict[str, Any]:
    """Build retrieval input without evaluator-only fields."""
    profile, jobs = _profile_request(profile_id, pool)
    return {
        "profile": profile,
        "job_urls": [job["job_url"] for job in jobs],
        "structured_jobs": jobs,
        "config": {
            "pipeline": {"vector_search_top_n": pool.get("retrieval_top_n", 50)},
            "ranking_policy": {
                "declared_preference_component_weights": {
                    "domain": 0.50,
                    "role_family": 0.30,
                    "work_mode": 0.20,
                }
            },
        },
        "top_n": int(pool.get("retrieval_top_n", 50)),
        "requested_strategy": requested_strategy,
    }


def _run_once(
    profiles: dict[str, dict[str, Any]],
    cache: set[str],
    *,
    arm: str = "lexical",
) -> tuple[dict[str, float], dict[str, int], dict[str, Any]]:
    shortlist_recalls: list[float] = []
    shortlist_precisions: list[float] = []
    ranking_recalls: list[float] = []
    ranking_precisions: list[float] = []
    ndcgs: list[float] = []
    llm_calls = 0
    scoring_failures = 0
    cache_hits = 0
    cache_misses = 0
    retrieval_returned_count = 0
    ranking_returned_count = 0
    eligible_count = 0
    shortlist_top_n = 0
    ranking_top_n = 0
    split_counts = {"calibration": 0, "held_out": 0}
    language_split_counts: dict[str, dict[str, int]] = {}
    split_metrics: dict[str, list[dict[str, float | int]]] = {}
    language_split_metrics: dict[str, dict[str, list[dict[str, float | int]]]] = {}
    fallback_count = 0
    effective_strategies: set[str] = set()
    backend_ids: set[str] = set()
    backend_metadata: dict[str, Any] = {}
    requested_strategy = VECTOR_RETRIEVAL_STRATEGY if arm in {"incumbent", "multilingual"} else LEXICAL_RETRIEVAL_STRATEGY
    for profile_id, pool in profiles.items():
        source_rows = list(pool["candidates"])
        eligible_count += len(source_rows)
        for source in source_rows:
            split = str(source.get("split") or "")
            if split in split_counts:
                split_counts[split] += 1
            language = str(source.get("language") or profile_id)
            language_counts = language_split_counts.setdefault(language, {"calibration": 0, "held_out": 0})
            if split in language_counts:
                language_counts[split] += 1
        request = build_retrieval_request(
            profile_id,
            pool,
            requested_strategy=requested_strategy,
        )
        if arm == "multilingual":
            request["config"].update(
                {
                    "embedding_backend": SENTENCE_TRANSFORMERS_BACKEND,
                    "shortlist_embedding_model": DEFAULT_SENTENCE_TRANSFORMERS_MODEL,
                    "embedding_model_revision": DEFAULT_SENTENCE_TRANSFORMERS_REVISION,
                    "embedding_dimension": 384,
                    "embedding_failure_policy": "raise",
                }
            )
            embed_and_store_jobs(request["structured_jobs"], request["config"])
        retrieval = run_vector_search(
            request["profile"],
            request["job_urls"],
            request["config"],
            top_n=request["top_n"],
            structured_jobs=request["structured_jobs"],
            requested_strategy=request["requested_strategy"],
        )
        diagnostics = dict(retrieval.get("diagnostics") or {})
        fallback_count += int(bool(diagnostics.get("fallback_used")))
        effective_strategies.add(str(diagnostics.get("effective_strategy") or ""))
        backend_ids.add(str(diagnostics.get("backend_id") or ""))
        backend_metadata = {
            key: diagnostics.get(key)
            for key in ("backend_id", "configured_model", "dimension", "model_revision", "preprocessing_version", "contract_fingerprint")
            if key in diagnostics
        }
        source_ids_by_url: dict[str, str] = {}
        for source in source_rows:
            candidate_id = str(source["candidate_id"])
            job = dict(source.get("job") or {})
            for value in (
                candidate_id,
                job.get("job_url"),
                job.get("source_job_url"),
                source.get("job_url"),
                source.get("source_job_url"),
            ):
                if value:
                    source_ids_by_url[str(value)] = candidate_id
        retrieved_ids = list(dict.fromkeys(
            source_ids_by_url.get(str(row["job_url"]), str(row["job_url"]))
            for row in retrieval["production_rows"]
        ))
        retrieved_id_set = set(retrieved_ids)
        retrieval_returned_count += len(retrieved_ids)
        shortlist_top_n = request["top_n"]
        shortlist_recalls.append(_recall(retrieved_ids, source_rows))
        shortlist_precisions.append(_precision(retrieved_ids, source_rows))
        source_by_id = {str(row["candidate_id"]): row for row in source_rows}
        rows: list[dict[str, Any]] = []
        for source in source_rows:
            candidate_id = str(source["candidate_id"])
            cache_key = f"lexical_v1:{profile_id}:{candidate_id}"
            if cache_key in cache:
                cache_hits += 1
            else:
                cache.add(cache_key)
                cache_misses += 1
            ai_score = source.get("ai_score")
            if ai_score is None:
                scoring_failures += 1
            rows.append(
                {
                    "candidate_id": candidate_id,
                    "raw_job_fingerprint": candidate_id,
                    "job_url": str(
                        dict(source.get("job") or {}).get("job_url") or candidate_id
                    ),
                    "baseline_fit": source.get("baseline_fit"),
                    "ai_score": ai_score,
                    "relevance_grade": source.get("relevance_grade", 0),
                }
            )
        shortlist = [row for row in rows if row["candidate_id"] in retrieved_id_set]
        ranking_top_n = int(pool.get("ranking_top_n", 12))
        ranked = rank_jobs([dict(row) for row in shortlist], ranking_top_n)
        ranking_returned_count += len(ranked)
        ranked_by_id = {str(row.get("raw_job_fingerprint") or row.get("candidate_id")): row for row in ranked}
        ranked_eval = [
            {**source_by_id[candidate_id], **row, "candidate_id": candidate_id}
            for candidate_id, row in ranked_by_id.items()
            if candidate_id in source_by_id
        ]
        pool_split_metrics = _split_metric_rows(
            retrieved_ids,
            ranked_eval,
            source_rows,
            request["top_n"],
            ranking_top_n,
            int(pool.get("ndcg_top_n", 15)),
        )
        ranked_ids = list(ranked_by_id)
        ranking_recalls.append(_recall(ranked_ids, source_rows))
        ranking_precisions.append(_precision(ranked_ids, source_rows))
        ndcgs.append(_ndcg(ranked_eval, source_rows, int(pool.get("ndcg_top_n", 15))))
        split_metrics.setdefault("calibration", []).append(pool_split_metrics["calibration"])
        split_metrics.setdefault("held_out", []).append(pool_split_metrics["held_out"])
        for language in sorted({str(row.get("language") or profile_id) for row in source_rows}):
            language_rows = [row for row in source_rows if str(row.get("language") or profile_id) == language]
            language_ids = {str(row["candidate_id"]) for row in language_rows}
            language_metrics = _split_metric_rows(
                [candidate_id for candidate_id in retrieved_ids if candidate_id in language_ids],
                [row for row in ranked_eval if str(row.get("language") or profile_id) == language],
                language_rows,
                request["top_n"],
                ranking_top_n,
                int(pool.get("ndcg_top_n", 15)),
            )
            per_language = language_split_metrics.setdefault(language, {"calibration": [], "held_out": []})
            for split in ("calibration", "held_out"):
                per_language[split].append(language_metrics[split])
    aggregated_language_split_metrics = {
        language: {
            split: {
                "count": int(statistics.mean(item["count"] for item in values)),
                "retrieval_recall_at_n": statistics.mean(item["retrieval_recall_at_n"] for item in values),
                "retrieval_precision_at_n": statistics.mean(item["retrieval_precision_at_n"] for item in values),
                "retrieval_mrr_at_n": statistics.mean(item["retrieval_mrr_at_n"] for item in values),
                "retrieval_ndcg_at_n": statistics.mean(item["retrieval_ndcg_at_n"] for item in values),
                "ranking_recall_at_n": statistics.mean(item["ranking_recall_at_n"] for item in values),
                "ranking_precision_at_n": statistics.mean(item["ranking_precision_at_n"] for item in values),
                "ranking_mrr_at_n": statistics.mean(item["ranking_mrr_at_n"] for item in values),
                "ranking_ndcg_at_n": statistics.mean(item["ranking_ndcg_at_n"] for item in values),
            }
            for split, values in splits.items()
        }
        for language, splits in language_split_metrics.items()
    }
    return (
        {
            "shortlist_recall": statistics.mean(shortlist_recalls),
            "shortlist_precision": statistics.mean(shortlist_precisions),
            "ranking_recall": statistics.mean(ranking_recalls),
            "ranking_precision": statistics.mean(ranking_precisions),
            "ndcg": statistics.mean(ndcgs),
            "split_metrics": {
                split: {
                    "count": int(statistics.mean(item["count"] for item in values)),
                    "retrieval_recall_at_n": statistics.mean(item["retrieval_recall_at_n"] for item in values),
                    "retrieval_precision_at_n": statistics.mean(item["retrieval_precision_at_n"] for item in values),
                    "retrieval_mrr_at_n": statistics.mean(item["retrieval_mrr_at_n"] for item in values),
                    "retrieval_ndcg_at_n": statistics.mean(item["retrieval_ndcg_at_n"] for item in values),
                    "ranking_recall_at_n": statistics.mean(item["ranking_recall_at_n"] for item in values),
                    "ranking_precision_at_n": statistics.mean(item["ranking_precision_at_n"] for item in values),
                    "ranking_mrr_at_n": statistics.mean(item["ranking_mrr_at_n"] for item in values),
                    "ranking_ndcg_at_n": statistics.mean(item["ranking_ndcg_at_n"] for item in values),
                }
                for split, values in split_metrics.items()
            },
            "language_split_metrics": aggregated_language_split_metrics,
        },
        {
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "llm_calls": llm_calls,
            "retries": 0,
            "scoring_failure_count": scoring_failures,
        },
        {
            "retrieval_returned_count": retrieval_returned_count,
            "ranking_returned_count": ranking_returned_count,
            "eligible_count": eligible_count,
            "split_counts": split_counts,
                "language_split_counts": language_split_counts,
                "language_split_metrics": aggregated_language_split_metrics,
            "shortlist_top_n": shortlist_top_n,
            "ranking_top_n": ranking_top_n,
            "fallback_count": fallback_count,
            "requested_strategy": requested_strategy,
            "effective_strategies": sorted(effective_strategies),
            "backend_ids": sorted(backend_ids),
            "backend": backend_metadata,
        },
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default="tests/fixtures/ranking_gold.json")
    parser.add_argument("--mode", default="replayed")
    parser.add_argument("--arm", choices=("incumbent", "lexical", "multilingual"), default="incumbent")
    parser.add_argument("--warmup-iterations", type=int, default=1)
    parser.add_argument("--measured-iterations", type=int, default=5)
    parser.add_argument("--output", required=True)
    parser.add_argument("--score-artifact")
    args = parser.parse_args()
    if args.mode != "replayed":
        parser.error(f"unsupported mode: {args.mode}; only replayed is supported")
    if args.warmup_iterations < 0 or args.measured_iterations < 1:
        parser.error("iterations must be warmup >= 0 and measured >= 1")

    fixture_path = Path(args.fixture)
    fixture_sha256 = _fixture_sha256(fixture_path)

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.arm == "multilingual":
        os.environ["FITCV_CP_SQLITE_PATH"] = str(output.with_suffix(".sqlite3"))

    data = json.loads(fixture_path.read_text(encoding="utf-8"))
    profiles = data["profiles"]
    fixture_role = _fixture_role(data)
    fixture_status = str(data.get("fixture_status") or ("ready" if fixture_role == "smoke" else "missing")).strip().lower()
    score_artifact_sha256 = None
    if args.score_artifact:
        try:
            score_artifact_sha256 = _apply_score_artifact(
                profiles,
                Path(args.score_artifact),
                fixture_sha256,
            )
        except RuntimeError as exc:
            result = {
                "schema_version": "ranking_benchmark_v3",
                "arm": args.arm,
                "status": "not_run",
                "reason": str(exc),
                "fixture": str(args.fixture),
                "fixture_sha256": fixture_sha256,
                "fixture_role": fixture_role,
                "score_artifact": str(args.score_artifact),
            }
            output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(result, separators=(",", ":")))
            return
    if fixture_status != "ready":
        result = {
            "schema_version": "ranking_benchmark_v3",
            "arm": args.arm,
            "status": "not_run",
            "reason": "fixture_not_ready",
            "blockers": [f"fixture_status:{fixture_status or 'missing'}"],
            "fixture": str(args.fixture),
            "fixture_sha256": fixture_sha256,
            "fixture_role": fixture_role,
            "score_artifact": str(args.score_artifact) if args.score_artifact else None,
            "score_artifact_sha256": score_artifact_sha256,
        }
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, separators=(",", ":")))
        return
    provenance_errors = []
    if fixture_role == "source_backed":
        provenance_errors.extend(_manifest_errors(fixture_path, data, fixture_sha256))
        provenance_errors.extend(_source_backed_payload_errors(profiles))
    if provenance_errors:
        result = {
            "schema_version": "ranking_benchmark_v3",
            "arm": args.arm,
            "status": "not_run",
            "reason": "invalid_source_backed_provenance",
            "blockers": provenance_errors,
            "fixture": str(args.fixture),
            "fixture_sha256": fixture_sha256,
            "fixture_role": fixture_role,
            "score_artifact": str(args.score_artifact) if args.score_artifact else None,
            "score_artifact_sha256": score_artifact_sha256,
        }
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, separators=(",", ":")))
        return
    review_errors = _source_backed_review_errors(profiles) if fixture_role == "source_backed" else []
    if review_errors:
        result = {
            "schema_version": "ranking_benchmark_v3",
            "arm": args.arm,
            "status": "not_run",
            "reason": "invalid_source_backed_review",
            "blockers": review_errors,
            "fixture": str(args.fixture),
            "fixture_sha256": fixture_sha256,
            "fixture_role": fixture_role,
            "score_artifact": str(args.score_artifact) if args.score_artifact else None,
            "score_artifact_sha256": score_artifact_sha256,
        }
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, separators=(",", ":")))
        return
    score_errors = _source_backed_score_errors(profiles) if fixture_role == "source_backed" else []
    if score_errors:
        result = {
            "schema_version": "ranking_benchmark_v3",
            "arm": args.arm,
            "status": "not_run",
            "reason": "missing_ranking_scores",
            "blockers": score_errors,
            "fixture": str(args.fixture),
            "fixture_sha256": fixture_sha256,
            "fixture_role": fixture_role,
            "score_artifact": str(args.score_artifact) if args.score_artifact else None,
            "score_artifact_sha256": score_artifact_sha256,
        }
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, separators=(",", ":")))
        return
    validation_errors = _validate_evaluation_input(profiles)
    if validation_errors:
        result = {
            "schema_version": "ranking_benchmark_v3",
            "arm": args.arm,
            "status": "not_run",
            "reason": "invalid_evaluation_input",
            "blockers": validation_errors,
            "fixture": str(args.fixture),
            "fixture_sha256": fixture_sha256,
            "fixture_role": fixture_role,
        }
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, separators=(",", ":")))
        return
    cache: set[str] = set()
    try:
        for _ in range(args.warmup_iterations):
            _run_once(profiles, cache, arm=args.arm)
        durations: list[float] = []
        quality: dict[str, float] = {}
        cache_metrics: dict[str, int] = {}
        observation: dict[str, Any] = {}
        for _ in range(args.measured_iterations):
            started = time.perf_counter()
            quality, cache_metrics, observation = _run_once(profiles, cache, arm=args.arm)
            durations.append((time.perf_counter() - started) * 1000)

    except RuntimeError as exc:
        result = {
            "schema_version": "ranking_benchmark_v3",
            "arm": args.arm,
            "status": "not_run",
            "reason": str(exc),
            "fixture": str(args.fixture),
            "fixture_sha256": fixture_sha256,
            "fixture_role": fixture_role,
        }
        output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result, separators=(",", ":")))
        return

    cache_total = cache_metrics["cache_hits"] + cache_metrics["cache_misses"]
    result = {
        "schema_version": "ranking_benchmark_v3",
        "fixture": str(args.fixture),
        "arm": args.arm,
        "status": "measured",
        "fixture_role": fixture_role,
        "score_artifact": str(args.score_artifact) if args.score_artifact else None,
        "score_artifact_sha256": score_artifact_sha256,
        "fixture_sha256": fixture_sha256,
        "mode": args.mode,
        "warmup_iterations": args.warmup_iterations,
        "measured_iterations": args.measured_iterations,
        "latency_ms": {"p50": statistics.median(durations), "p95": _percentile(durations, 0.95)},
        "metrics": {
            "retrieval": {
                "requested_strategy": observation["requested_strategy"],
                "effective_strategies": observation["effective_strategies"],
                "backend_ids": observation["backend_ids"],
                "backend": observation["backend"],
                "fallback_count": observation["fallback_count"],
                "top_n": observation["shortlist_top_n"],
                "returned_count": observation["retrieval_returned_count"],
                "eligible_count": observation["eligible_count"],
                "coverage": observation["retrieval_returned_count"] / observation["eligible_count"] if observation["eligible_count"] else 0.0,
                "recall_at_n": quality["split_metrics"]["held_out"]["retrieval_recall_at_n"],
                "precision_at_n": quality["split_metrics"]["held_out"]["retrieval_precision_at_n"],
                "mrr_at_n": quality["split_metrics"]["held_out"]["retrieval_mrr_at_n"],
                "ndcg_at_n": quality["split_metrics"]["held_out"]["retrieval_ndcg_at_n"],
            },
            "ranking": {
                "evaluation_scope": "held_out",
                "profiles": len(profiles),
                "top_n": observation["ranking_top_n"],
                "returned_count": observation["ranking_returned_count"],
                "eligible_count": observation["eligible_count"],
                "coverage": observation["ranking_returned_count"] / observation["eligible_count"] if observation["eligible_count"] else 0.0,
                "recall_at_n": quality["split_metrics"]["held_out"]["ranking_recall_at_n"],
                "precision_at_n": quality["split_metrics"]["held_out"]["ranking_precision_at_n"],
                "mrr_at_n": quality["split_metrics"]["held_out"]["ranking_mrr_at_n"],
                "ndcg_at_n": quality["split_metrics"]["held_out"]["ranking_ndcg_at_n"],
                "split_metrics": quality["split_metrics"],
                "language_split_metrics": quality["language_split_metrics"],
                "split_counts": observation["split_counts"],
                "language_split_counts": observation["language_split_counts"],
            },
            "calibration": {"count": observation["split_counts"]["calibration"]},
            "held_out": {"count": observation["split_counts"]["held_out"]},
            "cache": {
                "adapter": "replay_fingerprint_set",
                **cache_metrics,
                "hit_rate": cache_metrics["cache_hits"] / cache_total if cache_total else 0.0,
            },
            "llm": {"calls": 0, "retries": 0, "scoring_failure_count": cache_metrics["scoring_failure_count"]},
        },
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, separators=(",", ":")))


if __name__ == "__main__":
    main()
