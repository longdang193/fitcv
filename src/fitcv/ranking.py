"""@meta
name: ranking
type: module
domain: runtime
ownership: feature
capabilities:
  - cv_system.stage-artifact-diagnostics
responsibility:
  - Module metadata placeholder for src.fitcv.ranking.
inputs:
  - Internal runtime calls and module imports
outputs:
  - Module-level symbols and runtime behavior
lifecycle:
  - status: active
"""

import re
from typing import Any

from fitcv.candidate import canonicalize_role_title, infer_role_family
from fitcv.preference_policy import ResolvedPreferencePolicy, project_personalized_score
from fitcv.ranking_contract import STRUCTURED_FACTOR_IDS
from fitcv.semantic_snapshot import compile_semantic_policy, resolve_semantic_value

SUPPORTED_RANKING_FEATURES = STRUCTURED_FACTOR_IDS


def _normalize_text(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9_]+", " ", value.lower())).strip()

def _canonical_domain(value: str | None, config: dict[str, Any] | None = None) -> str:
    policy = (config or {}).get("semantic_policy")
    if not isinstance(policy, dict):
        policy = compile_semantic_policy(config or {})
    return resolve_semantic_value(value, "domain", policy)

def _canonical_role_family(value: str | None, config: dict[str, Any] | None = None) -> str:
    policy = (config or {}).get("semantic_policy")
    if not isinstance(policy, dict):
        policy = compile_semantic_policy(config or {})
    return resolve_semantic_value(value, "role_family", policy)

def _domain_neighbors(config: dict[str, Any] | None = None) -> dict[str, frozenset[str]]:
    raw_neighbors = (config or {}).get("domain_neighbors")
    if not isinstance(raw_neighbors, dict):
        return {}
    return {
        _normalize_text(str(domain)): frozenset(
            _normalize_text(str(neighbor))
            for neighbor in neighbors
            if _normalize_text(str(neighbor))
        )
        for domain, neighbors in raw_neighbors.items()
        if isinstance(neighbors, (list, tuple))
    }


def _role_family_neighbors(config: dict[str, Any] | None = None) -> dict[str, frozenset[str]]:
    raw_neighbors = ((config or {}).get("role_taxonomy") or {}).get("role_family_neighbors")
    if not isinstance(raw_neighbors, dict):
        return {}
    return {
        _normalize_text(str(family)): frozenset(
            _normalize_text(str(neighbor))
            for neighbor in neighbors
            if _normalize_text(str(neighbor))
        )
        for family, neighbors in raw_neighbors.items()
        if isinstance(neighbors, (list, tuple))
    }





# ── feature computation ───────────────────────────────────────────────────────

def compute_must_have_match(
    job_skills: list[str],
    candidate_skills: list[str],
    config: dict[str, Any] | None = None,
) -> float:
    """Compute ratio of required skills matched by the candidate.

    - Uses the synonym map via config (or default if None) for canonical matching.
    - If job has no required skills, returns 0.5 (neutral, no penalty).
    - If candidate has no skills but job does, returns 0.0.
    """
    if not job_skills:
        return 0.5
    if not candidate_skills:
        return 0.0

    policy = (config or {}).get("semantic_policy")
    if not isinstance(policy, dict):
        policy = compile_semantic_policy(config or {})
    reqs = {resolve_semantic_value(skill, "skill", policy) for skill in job_skills}
    cands = {resolve_semantic_value(skill, "skill", policy) for skill in candidate_skills}

    matched = len(reqs & cands)
    return matched / len(reqs)


def compute_seniority_fit(
    job_seniority: str | None,
    target_seniority: str | None,
    config: dict[str, Any] | None = None,
) -> float:
    """Map seniority closeness to a score in [0.0, 1.0].

    Rules:
    - exact match: 1.0
    - off by ±1 step: 0.5
    - off by ±2+ steps: 0.0
    - unknown (either side): 0.5 (neutral)
    """
    if not job_seniority or not target_seniority:
        return 0.5

    ladder = (config or {}).get("seniority", {}).get("ladder", [])
    if not ladder:
        # Fallback if config is missing
        ladder = ["intern", "entry", "associate", "mid", "senior", "lead", "manager", "director"]

    try:
        job_idx = ladder.index(job_seniority.lower())
        tgt_idx = ladder.index(target_seniority.lower())
    except ValueError:
        return 0.5

    diff = abs(job_idx - tgt_idx)
    if diff == 0:
        return 1.0
    if diff == 1:
        return 0.5
    return 0.0


def compute_title_relevance(
    job_title: str | None,
    candidate_target_role: str | None,
    *,
    job_family: str | None = None,
    config: dict[str, Any] | None = None,
) -> float:
    """Compute semantic role alignment between target role and job title.

    Prefer deterministic role-family normalization when possible, then fall back
    to lexical token overlap. The exposed score remains bounded in [0.0, 1.0].
    """
    if not job_title or not candidate_target_role:
        return 0.5

    target_family = infer_role_family(candidate_target_role, config=config)
    resolved_job_family = infer_role_family(job_title, explicit_family=job_family, config=config)
    neighbors = _role_family_neighbors(config)
    if target_family and resolved_job_family:
        if target_family == resolved_job_family:
            return 1.0
        if resolved_job_family in neighbors.get(target_family, frozenset()):
            return 0.75
        return 0.0

    canonical_target_role = canonicalize_role_title(candidate_target_role, config)
    canonical_job_role = canonicalize_role_title(job_title, config)
    if canonical_target_role and canonical_job_role:
        return 1.0 if canonical_target_role == canonical_job_role else 0.0

    tgt_tokens = set(candidate_target_role.lower().split())
    job_tokens = set(job_title.lower().split())

    if not tgt_tokens:
        return 0.5

    matched = len(tgt_tokens & job_tokens)
    return matched / len(tgt_tokens)


def _normalized_preferences(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    return [_normalize_text(str(value)) for value in values if _normalize_text(str(value))]


def _preference_dimension_score(job_value: str | None, preferred_values: list[str]) -> float:
    if not preferred_values:
        return 0.5
    normalized_job_value = _normalize_text(job_value)
    if not normalized_job_value:
        return 0.0
    return 1.0 if normalized_job_value in preferred_values else 0.0

def _preference_neighbor_score(config: dict[str, Any] | None = None) -> float:
    raw_score = (config or {}).get("preference_fit_neighbor_score")
    if raw_score is None:
        return 0.7
    try:
        score = float(raw_score)
    except (TypeError, ValueError):
        return 0.7
    return max(0.0, min(1.0, score))

def _preference_dimension_score_with_neighbors(
    *,
    job_value: str,
    preferred_values: list[str],
    neighbors: dict[str, frozenset[str]] | None = None,
    neighbor_score: float = 0.7,
) -> tuple[float, str]:
    if not preferred_values:
        return 0.5, "neutral"
    if not job_value:
        return 0.0, "none"
    if job_value in preferred_values:
        return 1.0, "exact"
    neighbor_map = neighbors or {}
    preferred_set = set(preferred_values)
    for preferred in preferred_set:
        if job_value in neighbor_map.get(preferred, frozenset()):
            return neighbor_score, "neighbor"
        if preferred in neighbor_map.get(job_value, frozenset()):
            return neighbor_score, "neighbor"
    return 0.0, "none"


def compute_declared_preference_fit_details(
    job: dict[str, Any],
    prefs: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ranking_policy = dict((config or {}).get("ranking_policy") or {})
    configured_weights = ranking_policy.get("declared_preference_component_weights")
    if not isinstance(configured_weights, dict):
        raise ValueError("ranking_policy.declared_preference_component_weights is required")
    weights = {
        key: float(configured_weights[key])
        for key in ("domain", "role_family", "work_mode")
    }
    pref_domains = [_canonical_domain(value, config) for value in _normalized_preferences(prefs.get("domains", []))]
    pref_role_families = [_canonical_role_family(value, config) for value in _normalized_preferences(prefs.get("role_families", []))]
    pref_work_modes = _normalized_preferences(prefs.get("location_types", []))
    domain_neighbors = _domain_neighbors(config)
    role_family_neighbors = _role_family_neighbors(config)
    neighbor_score = _preference_neighbor_score(config)

    if not (pref_domains or pref_role_families or pref_work_modes):
        return {
            "score": 0.5,
            "weights": weights,
            "components": {
                "domain": 0.5,
                "role_family": 0.5,
                "work_mode": 0.5,
            },
            "match_details": {
                "domain": "neutral",
                "role_family": "neutral",
                "work_mode": "neutral",
            },
        }

    canonical_domain = _canonical_domain(str(job.get("domain") or ""), config)
    canonical_role_family = _canonical_role_family(str(job.get("job_family") or ""), config)
    domain_score, domain_match_type = _preference_dimension_score_with_neighbors(
        job_value=canonical_domain,
        preferred_values=[value for value in pref_domains if value],
        neighbors=domain_neighbors,
        neighbor_score=neighbor_score,
    )
    role_family_score, role_family_match_type = _preference_dimension_score_with_neighbors(
        job_value=canonical_role_family,
        preferred_values=[value for value in pref_role_families if value],
        neighbors=role_family_neighbors,
        neighbor_score=neighbor_score,
    )
    work_mode_score = _preference_dimension_score(
        str(job.get("location_type") or ""),
        pref_work_modes,
    )
    components = {
        "domain": domain_score,
        "role_family": role_family_score,
        "work_mode": work_mode_score,
    }
    work_mode_match_type = (
        "neutral"
        if not pref_work_modes
        else ("exact" if work_mode_score == 1.0 else "none")
    )
    score = sum(components[key] * weights[key] for key in weights)
    return {
        "score": score,
        "weights": weights,
        "components": components,
        "match_details": {
            "domain": domain_match_type,
            "role_family": role_family_match_type,
            "work_mode": work_mode_match_type,
        },
        "canonical_values": {
            "job": {
                "domain": canonical_domain,
                "role_family": canonical_role_family,
                "work_mode": _normalize_text(str(job.get("location_type") or "")),
            },
            "preferences": {
                "domains": [value for value in pref_domains if value],
                "role_families": [value for value in pref_role_families if value],
                "work_modes": [value for value in pref_work_modes if value],
            },
        },
    }




# ── composite score ───────────────────────────────────────────────────────────



# ── sorting and ranking ───────────────────────────────────────────────────────

def rank_jobs(
    jobs: list[dict[str, Any]],
    top_n: int,
    *,
    resolved_preference_policy: ResolvedPreferencePolicy | None = None,
) -> list[dict[str, Any]]:
    """Assign global baseline rank, then optional personalized order."""
    for job in jobs:
        if not str(job.get("raw_job_fingerprint") or "").strip():
            raise ValueError("ranking row requires raw_job_fingerprint")
        if job.get("baseline_fit") is None:
            raise ValueError("ranking row requires baseline_fit")
    sorted_jobs = sorted(
        jobs,
        key=lambda j: (
            -float(j["baseline_fit"]),
            str(j["raw_job_fingerprint"]),
            str(j.get("job_url") or ""),
        ),
    )

    for index, job in enumerate(sorted_jobs, start=1):
        job["baseline_rank"] = index
        baseline_fit = float(job["baseline_fit"])
        residual = 0.0
        raw_score = baseline_fit
        display_score = baseline_fit
        clipped = False
        if resolved_preference_policy is not None:
            embedding = job.get("normalized_embedding")
            if not isinstance(embedding, list) and any(resolved_preference_policy.preference_vector):
                raise ValueError("ranking row requires normalized_embedding for personalization")
            if isinstance(embedding, list):
                projection = project_personalized_score(
                    runtime_contract=resolved_preference_policy.runtime_contract,
                    baseline_fit=baseline_fit,
                    preference_vector=resolved_preference_policy.preference_vector,
                    normalized_embedding=tuple(float(value) for value in embedding),
                )
                residual = projection.preference_residual
                raw_score = projection.personalized_rank_score
                display_score = projection.personalized_display_score
                clipped = projection.score_was_clipped
        job["preference_residual"] = residual
        job["personalized_rank_score"] = raw_score
        job["personalized_display_score"] = display_score
        job["score_was_clipped"] = clipped
        job["preference_policy_snapshot_id"] = (
            resolved_preference_policy.policy_snapshot_id if resolved_preference_policy else None
        )
        job["preference_vector_fingerprint"] = (
            resolved_preference_policy.preference_vector_fingerprint
            if resolved_preference_policy
            else None
        )
        job["preference_runtime_contract_fingerprint"] = (
            resolved_preference_policy.runtime_contract.runtime_contract_fingerprint
            if resolved_preference_policy
            else None
        )
        job["preference_policy_resolution_status"] = (
            resolved_preference_policy.resolution_status
            if resolved_preference_policy
            else "zero_residual_no_active"
        )

    personalized = sorted(
        sorted_jobs,
        key=lambda job: (
            -float(job["personalized_rank_score"]),
            str(job["raw_job_fingerprint"]),
            str(job.get("job_url") or ""),
        ),
    )
    for index, job in enumerate(personalized, start=1):
        job["personalized_rank"] = index
    return personalized[:top_n]


# ── integration: persist results ─────────────────────────────────────────────

def store_final_ranking(
    ranked_jobs: list[dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Ranking persistence is trimmed from live SQLite product path."""
    if not ranked_jobs:
        return
def compute_ranking_runtime_diagnostics(
    ranking_inputs: list[dict[str, Any]],
    *,
    supported_features: tuple[str, ...] = SUPPORTED_RANKING_FEATURES,
) -> dict[str, Any]:
    total_rows = len(ranking_inputs)
    by_feature: dict[str, dict[str, float]] = {}
    total_applied = 0

    for feature_name in supported_features:
        count = 0
        for row in ranking_inputs:
            factor = dict((row.get("normalized_factors") or {}).get(feature_name) or {})
            if bool(factor.get("missing_default_applied")):
                count += 1
        total_applied += count
        by_feature[feature_name] = {
            "count": count,
            "rate": (float(count) / float(total_rows)) if total_rows > 0 else 0.0,
        }

    domain_unmatched_count = 0
    role_family_unmatched_count = 0
    neighbor_match_count = 0
    active_comparisons = 0
    unmatched_total = 0

    for row in ranking_inputs:
        match_details = row.get("declared_preference_fit_match_details")
        if not isinstance(match_details, dict):
            continue
        for key in ("domain", "role_family"):
            state = str(match_details.get(key) or "").strip().lower()
            if state == "neutral":
                continue
            active_comparisons += 1
            if state == "neighbor":
                neighbor_match_count += 1
            elif state == "none":
                unmatched_total += 1
                if key == "domain":
                    domain_unmatched_count += 1
                elif key == "role_family":
                    role_family_unmatched_count += 1

    return {
        "missing_feature_fallbacks": {
            "total_applied": total_applied,
            "total_rows": total_rows,
            "by_feature": by_feature,
        },
        "taxonomy_drift": {
            "domain_unmatched_count": domain_unmatched_count,
            "role_family_unmatched_count": role_family_unmatched_count,
            "neighbor_match_count": neighbor_match_count,
            "active_comparisons": active_comparisons,
            "unmatched_total": unmatched_total,
            "unmatched_rate": (float(unmatched_total) / float(active_comparisons)) if active_comparisons > 0 else 0.0,
        },
    }






