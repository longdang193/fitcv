"""Run bounded paired final-CV evaluation against a configured provider."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv.llm_runtime import LlmTaskRequest, LlmValidationResult, execute_llm_task  # noqa: E402
from fitcv.runtime_routing import resolve_llm_routing  # noqa: E402
from fitcv.agentic_cv_analysis import analyze_ranked_job  # noqa: E402
from fitcv.cv_generator import build_structured_generation_prompt, project_authorized_profile  # noqa: E402
from fitcv.evidence import project_candidate_evidence  # noqa: E402


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def validate_benchmark_fixture(fixture: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if not str(fixture.get("fixture_id") or ""):
        errors.append("fixture_id is required")
    if not isinstance(fixture.get("evaluation_schema_version"), int):
        errors.append("evaluation_schema_version must be an integer")
    profile = fixture.get("candidate_profile")
    if not isinstance(profile, dict) or not profile:
        errors.append("candidate_profile must be a non-empty object")
    else:
        expected = str(fixture.get("profile_sha256") or "")
        if expected and expected != _fingerprint(profile):
            errors.append("profile_sha256 does not match candidate_profile")
    labels = fixture.get("requirement_labels")
    if not isinstance(labels, dict) or not labels:
        errors.append("requirement_labels must be a non-empty object")
    evidence_ids = {
        str(item.get("id") or "")
        for section in (profile or {}).values()
        if isinstance(section, list)
        for parent in section
        if isinstance(parent, dict)
        for item in list(parent.get("evidence") or [])
        if isinstance(item, dict) and str(item.get("id") or "")
    }
    for requirement_id, label in (labels or {}).items():
        if not isinstance(label, dict):
            errors.append(f"requirement_labels.{requirement_id} must be an object")
            continue
        if not str(label.get("canonical_requirement") or "").strip():
            errors.append(f"requirement_labels.{requirement_id}.canonical_requirement is required")
        if not isinstance(label.get("answerable"), bool):
            errors.append(f"requirement_labels.{requirement_id}.answerable must be boolean")
        for evidence_id in list(label.get("approved_evidence_ids") or []):
            if str(evidence_id) not in evidence_ids:
                errors.append(f"{requirement_id}: unknown approved evidence id {evidence_id}")
    splits = fixture.get("jobs")
    if not isinstance(splits, dict):
        errors.append("jobs must contain development, pilot, and held_out splits")
        return errors
    seen: dict[str, str] = {}
    for split_name in ("development", "pilot", "held_out"):
        jobs = splits.get(split_name)
        if not isinstance(jobs, list) or not jobs:
            errors.append(f"jobs.{split_name} must be non-empty")
            continue
        for job in jobs:
            if not isinstance(job, dict):
                errors.append(f"jobs.{split_name} contains non-object job")
                continue
            job_id = str(job.get("job_id") or "") if isinstance(job, dict) else ""
            if not job_id:
                errors.append(f"jobs.{split_name} contains job without job_id")
            elif job_id in seen:
                errors.append(f"job_id {job_id} appears in {seen[job_id]} and {split_name}")
            else:
                seen[job_id] = split_name
    return errors


def extract_provider_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = dict(response.get("usage") or response.get("metadata", {}).get("usage") or {})
    result = {
        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "total_tokens": usage.get("total_tokens"),
        "cost": usage.get("cost"),
        "available": bool(usage),
    }
    if "estimated_cost" in usage or "estimated_cost_usd" in usage:
        result["estimated_cost"] = usage.get("estimated_cost", usage.get("estimated_cost_usd"))
    if "actual_cost" in usage or "actual_cost_usd" in usage:
        result["actual_cost"] = usage.get("actual_cost", usage.get("actual_cost_usd"))
    return result


def _mean(values: list[float]) -> float | str:
    return round(sum(values) / len(values), 6) if values else "not_available"


def _numeric_values(values: list[Any]) -> list[float]:
    return [float(value) for value in values if isinstance(value, (int, float))]


def _normalize_job_for_retrieval(job: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(job)
    requirements = [
        dict(item)
        for item in list(normalized.get("requirements") or [])
        if isinstance(item, dict) and str(item.get("canonical_requirement") or "").strip()
    ]
    if requirements and not any(
        normalized.get(field)
        for field in ("required_skills", "required_skills_canonical", "required_skill_entities")
    ):
        skills = [str(item["canonical_requirement"]).strip() for item in requirements]
        normalized["required_skills"] = skills
        normalized["required_skills_canonical"] = skills
        normalized["required_skill_entities"] = [
            {"raw_text": skill, "canonical": skill} for skill in skills
        ]
    return normalized


def paired_bootstrap_delta(
    pairs: list[tuple[float, float]],
    *,
    seed: int = 20260925,
    resamples: int = 10_000,
) -> dict[str, Any]:
    deltas = [fitcv - baseline for baseline, fitcv in pairs]
    if not deltas:
        return {
            "point": "not_available",
            "lower": "not_available",
            "upper": "not_available",
            "sample_count": 0,
            "resamples": resamples,
            "seed": seed,
            "zero_variance": False,
        }
    point = sum(deltas) / len(deltas)
    if len(set(deltas)) == 1:
        value = round(point, 6)
        return {
            "point": value,
            "lower": value,
            "upper": value,
            "sample_count": len(deltas),
            "resamples": resamples,
            "seed": seed,
            "zero_variance": True,
        }
    rng = random.Random(seed)
    samples = []
    for _ in range(resamples):
        samples.append(sum(rng.choice(deltas) for _ in deltas) / len(deltas))
    samples.sort()

    def percentile(value: float) -> float:
        position = (len(samples) - 1) * value
        lower = int(position)
        upper = min(lower + 1, len(samples) - 1)
        fraction = position - lower
        return samples[lower] + (samples[upper] - samples[lower]) * fraction

    return {
        "point": round(point, 6),
        "lower": round(percentile(0.025), 6),
        "upper": round(percentile(0.975), 6),
        "sample_count": len(deltas),
        "resamples": resamples,
        "seed": seed,
        "zero_variance": False,
    }


def _annotation_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows = payload.get("human_review_annotations", payload.get("review_annotations", []))
    if isinstance(rows, dict):
        rows = [dict(value, pair_id=key) for key, value in rows.items() if isinstance(value, dict)]
    return [dict(row) for row in rows if isinstance(row, dict)]


def _annotation_score(annotation: dict[str, Any]) -> float | None:
    score = annotation.get("quality_score", annotation.get("score"))
    if isinstance(score, (int, float)):
        return float(score)
    scores = annotation.get("scores")
    if not isinstance(scores, dict):
        return None
    values = _numeric_values(list(scores.values()))
    return sum(values) / len(values) if values and len(values) == len(scores) else None


def _is_unresolved_review(annotation: dict[str, Any]) -> bool:
    state = str(
        annotation.get("adjudication_state", annotation.get("adjudication_status", ""))
    ).casefold()
    return state in {"unresolved", "disagreement"}


def validate_human_review_annotations(
    payload: dict[str, Any],
    pair_ids: set[str],
) -> list[str]:
    errors: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for annotation in _annotation_rows(payload):
        pair_id = str(annotation.get("pair_id") or "")
        variant = str(annotation.get("variant") or "")
        reviewer_hash = str(annotation.get("reviewer_id_hash") or "")
        if pair_id not in pair_ids:
            errors.append(f"unknown human review pair_id: {pair_id}")
        if variant not in {"baseline", "fitcv"}:
            errors.append(f"{pair_id}: human review variant must be baseline or fitcv")
        if not str(annotation.get("rubric_version") or ""):
            errors.append(f"{pair_id}: human review rubric_version is required")
        if not reviewer_hash:
            errors.append(f"{pair_id}: human review reviewer_id_hash is required")
        if _annotation_score(annotation) is None:
            errors.append(f"{pair_id}: human review score is incomplete")
        if not str(annotation.get("adjudication_state") or ""):
            errors.append(f"{pair_id}: human review adjudication_state is required")
        key = (pair_id, variant, reviewer_hash)
        if key in seen:
            errors.append(f"duplicate human review annotation: {pair_id}/{variant}")
        seen.add(key)
    return errors


def _human_review_metrics(payload: dict[str, Any], pair_ids: list[str]) -> dict[str, Any]:
    rows = _annotation_rows(payload)
    by_variant: dict[str, dict[str, Any]] = {}
    for variant in ("baseline", "fitcv"):
        variant_rows = [row for row in rows if str(row.get("variant") or "") == variant]
        scores = [
            score
            for score in (_annotation_score(row) for row in variant_rows if not _is_unresolved_review(row))
            if score is not None
        ]
        unresolved = sum(_is_unresolved_review(row) for row in variant_rows)
        by_variant[variant] = {
            "expected_reviews": len(pair_ids),
            "score_count": len(scores),
            "missing_count": max(0, len(pair_ids) - len(scores)),
            "unresolved_count": unresolved,
            "quality_score": round(sum(scores) / len(scores), 6) if scores else "not_available",
        }
    preference = {key: 0 for key in ("baseline", "fitcv", "tie", "unresolved")}
    for row in rows:
        value = str(row.get("pairwise_preference", row.get("preference", ""))).casefold()
        if value in preference:
            preference[value] += 1
    grouped: dict[tuple[str, str], list[float]] = {}
    for row in rows:
        score = None if _is_unresolved_review(row) else _annotation_score(row)
        if score is not None:
            key = (str(row.get("pair_id") or ""), str(row.get("variant") or ""))
            grouped.setdefault(key, []).append(score)
    agreement_groups = [scores for scores in grouped.values() if len(scores) > 1]
    return {
        "by_variant": by_variant,
        "pairwise_preference": preference,
        "review_count": len(rows),
        "agreement": (
            round(sum(len(set(scores)) == 1 for scores in agreement_groups) / len(agreement_groups), 6)
            if agreement_groups
            else "not_available"
        ),
        "agreement_group_count": len(agreement_groups),
    }


def _review_output(
    text: str,
    review: dict[str, Any],
    *,
    authorized_evidence_ids: list[str] | None = None,
) -> dict[str, Any]:
    normalized = str(text or "").casefold()
    requirements = list(review.get("requirements") or [])
    approved_evidence_ids = {
        str(value).strip()
        for requirement in requirements
        for value in list(requirement.get("approved_evidence_ids") or [])
        if str(value).strip()
    }
    authorized_ids = (
        {str(value).strip() for value in authorized_evidence_ids if str(value).strip()}
        if authorized_evidence_ids is not None
        else set(approved_evidence_ids)
    )
    covered = []
    eligible_requirements = []
    for requirement in requirements:
        requirement_id = str(requirement.get("requirement_id") or "")
        approved_evidence_ids = {
            str(value).strip()
            for value in list(
                requirement.get("approved_evidence_ids")
                or requirement.get("approved_supporting_evidence_ids")
                or []
            )
            if str(value).strip()
        }
        if not requirement.get("answerable", True) or not approved_evidence_ids:
            continue
        eligible_requirements.append(requirement_id)
        terms = [str(term).casefold() for term in list(requirement.get("terms") or []) if str(term).strip()]
        claims = list(requirement.get("supported_claims") or [])
        claim_terms = [
            str(term).casefold()
            for claim in claims
            for term in list(claim.get("terms") or claim.get("patterns") or [])
            if str(term).strip()
        ]
        matched_terms = terms + claim_terms
        if requirement_id and approved_evidence_ids & authorized_ids and matched_terms and any(
            _term_is_supported(normalized, term) for term in matched_terms
        ):
            covered.append(requirement_id)
    claim_queue = []
    reviewed_claims = []
    for claim in list(review.get("claim_reviews") or []):
        claim_id = str(claim.get("claim_id") or "")
        patterns = [
            str(pattern).casefold()
            for pattern in list(claim.get("patterns") or claim.get("terms") or [])
            if str(pattern).strip()
        ]
        if not claim_id or not patterns or not any(
            _term_is_supported(normalized, pattern) for pattern in patterns
        ):
            continue
        evidence_ids = {
            str(value).strip()
            for value in list(claim.get("evidence_ids") or [])
            if str(value).strip()
        }
        authorization_errors = []
        if not evidence_ids:
            authorization_errors.append("evidence_ids_required")
        unauthorized = evidence_ids - authorized_ids
        if unauthorized:
            authorization_errors.append("evidence_not_authorized")
        if approved_evidence_ids and evidence_ids - approved_evidence_ids:
            authorization_errors.append("evidence_not_approved")
        entry = {
            "claim_id": claim_id,
            "matched_patterns": [pattern for pattern in patterns if pattern in normalized],
            "review_status": (
                "needs_review"
                if authorization_errors
                else str(claim.get("review_status") or "needs_review")
            ),
            "supported": None if authorization_errors else claim.get("supported"),
            "evidence_ids": sorted(evidence_ids & authorized_ids),
            "authorization_errors": authorization_errors,
        }
        claim_queue.append(entry)
        if entry["review_status"] == "reviewed" and isinstance(entry["supported"], bool):
            reviewed_claims.append(entry)
    unsupported_claims = [claim for claim in reviewed_claims if not claim["supported"]]
    unsupported_claim_hits = [claim["claim_id"] for claim in unsupported_claims]
    coverage = (
        "not_applicable"
        if not eligible_requirements
        else round(len(set(covered)) / len(set(eligible_requirements)), 6)
    )
    unsupported_rate = (
        round(len(unsupported_claims) / len(reviewed_claims), 6)
        if reviewed_claims
        else "not_applicable"
    )
    unreviewed_claims = [claim for claim in claim_queue if claim not in reviewed_claims]
    return {
        "covered_requirements": covered,
        "requirement_coverage": coverage,
        "eligible_requirements": eligible_requirements,
        "claim_review_queue": claim_queue,
        "reviewed_factual_claims": len(reviewed_claims),
        "unsupported_factual_claims": len(unsupported_claims),
        "unsupported_claim_hits": unsupported_claim_hits,
        "unsupported_factual_claim_rate": unsupported_rate,
        "accepted": (coverage == "not_applicable" or coverage == 1.0)
        and (unsupported_rate == "not_applicable" or unsupported_rate == 0.0)
        and not unreviewed_claims,
    }


def _term_is_supported(normalized: str, term: str) -> bool:
    start = normalized.find(term)
    while start >= 0:
        prefix = normalized[max(0, start - 64) : start]
        if not re.search(
            r"(?:\bno\b|\bnot\b|\bwithout\b|\black of\b|\bdoes not have\b|\bdoesn't have\b)[^.!?,;:]{0,48}$",
            prefix,
        ):
            return True
        start = normalized.find(term, start + 1)
    return False


def _call_provider(
    prompt: str,
    provider: dict[str, Any],
    environ: dict[str, str],
    *,
    output_budget: int | None = None,
) -> dict[str, Any]:
    routing_part = str(provider.get("routing_part") or "cv_generation_structured_write")
    route = resolve_llm_routing(routing_part)
    from dataclasses import replace

    route = replace(
        route,
        model=str(provider["model"]),
        temperature=float(dict(provider["generation_settings"])["temperature"]),
    )
    api_key_name = str(provider.get("credential_env") or "FITCV_LLM_API_KEY")
    previous_key = os.environ.get(api_key_name)
    if environ.get(api_key_name):
        os.environ[api_key_name] = environ[api_key_name]
    try:
        request = LlmTaskRequest(
            routing_part=routing_part,
            prompt=prompt,
            response_mode="text",
            max_output_tokens=output_budget,
        )
        result = execute_llm_task(
            request,
            parser=lambda response: response.raw_text,
            validator=lambda value: LlmValidationResult(
                valid=bool(str(value or "").strip()), errors=[], details={}
            ),
            resolved_route=route,
        )
    finally:
        if previous_key is None:
            os.environ.pop(api_key_name, None)
        else:
            os.environ[api_key_name] = previous_key
    if result.status != "succeeded":
        failure = result.failure
        return {
            "status": "failed",
            "failure": {
                "stage": failure.stage if failure else "adapter",
                "code": failure.code if failure else "provider_failure",
                "http_status": failure.http_status if failure else None,
                "provider_diagnostics": failure.provider_diagnostics if failure else None,
            },
            "latency_ms": result.provenance.latency_ms,
            "attempt_count": result.provenance.attempt_count,
        }
    text = str(result.adapter_response.raw_text if result.adapter_response else "")
    return {
        "status": "succeeded",
        "output_sha256": _fingerprint(text),
        "output_chars": len(text),
        "latency_ms": result.provenance.latency_ms,
        "attempt_count": result.provenance.attempt_count,
        "response_id_present": bool(result.provenance.response_id),
        "usage": extract_provider_usage(dict(result.adapter_response.telemetry or {}) if result.adapter_response else {}),
        "text": text,
    }


def validate_paired_inputs(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    fixture = payload.get("fixture")
    if isinstance(fixture, dict):
        errors.extend(validate_benchmark_fixture(fixture))
    gate = dict(payload.get("offline_gate") or {})
    if gate.get("passed") is not True:
        errors.append("offline_gate.passed must be true")
    provider = dict(payload.get("provider") or {})
    for field in ("model", "template", "generation_settings", "output_budget"):
        if field not in provider:
            errors.append(f"provider.{field} is required")
    if not isinstance(provider.get("output_budget"), int) or provider.get("output_budget", 0) <= 0:
        errors.append("provider.output_budget must be positive")
    pairs = list(payload.get("pairs") or [])
    if not pairs:
        errors.append("pairs must not be empty")
    pair_ids: set[str] = set()
    for pair in pairs:
        if not isinstance(pair, dict):
            errors.append("pairs must contain objects")
            continue
        pair_id = str(pair.get("pair_id") or "")
        if pair_id in pair_ids:
            errors.append(f"duplicate pair_id: {pair_id}")
        pair_ids.add(pair_id)
        baseline = dict(pair.get("baseline") or {})
        fitcv = dict(pair.get("fitcv") or {})
        if not pair_id:
            errors.append("pair_id is required")
        if not baseline or not fitcv:
            errors.append(f"{pair_id or '<unknown>'} needs baseline and fitcv inputs")
            continue
        for field in ("fixture_sha256", "scenario_id", "model", "template", "generation_settings", "output_budget"):
            if baseline.get(field) != fitcv.get(field):
                errors.append(f"{pair_id}: baseline and fitcv {field} mismatch")
        if baseline.get("fixture_sha256") != gate.get("fixture_sha256"):
            errors.append(f"{pair_id}: fixture SHA-256 differs from offline gate")
        for field in ("model", "template", "generation_settings", "output_budget"):
            if baseline.get(field) != provider.get(field):
                errors.append(f"{pair_id}: baseline {field} differs from provider configuration")
    errors.extend(validate_human_review_annotations(payload, pair_ids))
    return errors


def build_paired_inputs(
    fixture: dict[str, Any],
    *,
    config: dict[str, Any],
    provider: dict[str, Any],
    split: str = "pilot",
    top_k: int | None = None,
) -> dict[str, Any]:
    """Build paired prompts from FitCV retrieval, never from hand-written prompts."""
    fixture_errors = validate_benchmark_fixture(fixture)
    if fixture_errors:
        raise ValueError("; ".join(fixture_errors))
    profile = dict(fixture["candidate_profile"])
    jobs = list(dict(fixture["jobs"])[split])
    full_evidence = project_candidate_evidence(profile)
    template = str(config.get("_template_text") or "")
    if not template:
        template = (REPO_ROOT / "templates" / "cv_template.md").read_text(encoding="utf-8")
    pairs: list[dict[str, Any]] = []
    for source_job in jobs:
        job = _normalize_job_for_retrieval(dict(source_job))
        job.setdefault("baseline_fit", 0.8)
        job.setdefault("baseline_fit_label", "strong")
        analysis = dict(analyze_ranked_job(job, profile, config, top_k=top_k))
        rag_evidence = list(analysis.get("evidence_payload") or [])
        gap = dict(analysis.get("gap_summary") or {})
        selection_summary = dict(analysis.get("evidence_selection_summary") or {})
        requirements = []
        for requirement in list(job.get("requirements") or []):
            requirement = dict(requirement)
            canonical_requirement = str(requirement.get("canonical_requirement") or "").strip()
            requirement_id = str(requirement.get("requirement_id") or "").strip()
            if requirement_id and canonical_requirement:
                requirements.append(
                    {
                        "requirement_id": requirement_id,
                        "terms": [canonical_requirement],
                        "answerable": bool(requirement.get("answerable", True)),
                        "approved_evidence_ids": list(requirement.get("approved_evidence_ids") or []),
                    }
                )
        if not requirements:
            for skill in list(job.get("required_skills") or []):
                canonical = str(skill).strip().casefold()
                requirement_id = f"required_skill:{canonical}"
                label = dict(fixture.get("requirement_labels", {}).get(requirement_id) or {})
                requirements.append(
                    {
                        "requirement_id": requirement_id,
                        "terms": [str(skill), str(label.get("canonical_requirement") or skill)],
                        "answerable": bool(label.get("answerable", True)),
                        "approved_evidence_ids": list(label.get("approved_evidence_ids") or []),
                    }
                )
        review = {"requirements": requirements, "claim_reviews": []}
        variants = {}
        for variant_name, evidence, authorized_profile, summary in (
            ("baseline", full_evidence, project_authorized_profile(profile, full_evidence), None),
            ("fitcv", rag_evidence, project_authorized_profile(profile, rag_evidence), selection_summary),
        ):
            prompt = build_structured_generation_prompt(
                jd=job,
                evidence=evidence,
                gap=gap,
                template=template,
                profile=authorized_profile,
                config=config,
                evidence_selection_summary=summary,
            )
            variants[variant_name] = {
                "fixture_sha256": _fingerprint(fixture),
                "scenario_id": str(job.get("job_id") or ""),
                "model": provider.get("model"),
                "template": provider.get("template"),
                "generation_settings": provider.get("generation_settings"),
                "output_budget": provider.get("output_budget"),
                "prompt": prompt,
                "authorized_evidence_ids": [str(item.get("evidence_id") or "") for item in evidence],
                "review": review,
            }
        pairs.append({"pair_id": str(job.get("job_id") or ""), **variants})
    return {
        "offline_gate": {"passed": True, "fixture_sha256": _fingerprint(fixture)},
        "fixture": fixture,
        "provider": provider,
        "pairs": pairs,
    }


def evaluate(
    payload: dict[str, Any],
    *,
    dry_run: bool = True,
    environ: dict[str, str] | None = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if isinstance(payload.get("fixture"), dict) and payload.get("pairs"):
        raise ValueError("fixture-driven evaluation requires programmatic pairing")
    if isinstance(payload.get("fixture"), dict) and not payload.get("pairs"):
        payload = {
            **payload,
            **build_paired_inputs(
                dict(payload["fixture"]),
                config=dict(config or payload.get("generation_config") or {}),
                provider=dict(payload.get("provider") or {}),
                split=str(payload.get("evaluation_split") or "pilot"),
            ),
        }
    errors = validate_paired_inputs(payload)
    if errors:
        raise ValueError("; ".join(errors))
    if not dry_run:
        environment = dict(os.environ if environ is None else environ)
        provider = dict(payload["provider"])
        credential_env = str(provider.get("credential_env") or "")
        if not credential_env or not environment.get(credential_env):
            raise RuntimeError("live evaluation requires configured provider credentials")
        if float(payload.get("cost_ceiling_usd") or 0.0) <= 0:
            raise RuntimeError("live evaluation requires positive cost_ceiling_usd")
        live_errors = []
        for pair in payload["pairs"]:
            pair_id = str(pair.get("pair_id") or "<unknown>")
            for variant_name in ("baseline", "fitcv"):
                variant = dict(pair[variant_name])
                if not str(variant.get("prompt") or "").strip():
                    live_errors.append(f"{pair_id}: {variant_name}.prompt is required for live evaluation")
                if not isinstance(variant.get("review"), dict):
                    live_errors.append(f"{pair_id}: {variant_name}.review is required for live evaluation")
        if live_errors:
            raise ValueError("; ".join(live_errors))
        max_calls = int(payload.get("max_provider_calls") or len(payload["pairs"]) * 2)
        if max_calls <= 0:
            raise RuntimeError("live evaluation requires positive max_provider_calls")
        if max_calls < len(payload["pairs"]) * 2:
            raise RuntimeError("max_provider_calls is lower than paired evaluation calls")
        pair_results = []
        calls = 0
        usage_totals = {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
            "cost": None,
            "estimated_cost": None,
            "actual_cost": None,
        }
        usage_available = False
        for pair in payload["pairs"]:
            variants = {}
            for variant_name in ("baseline", "fitcv"):
                if calls >= max_calls:
                    raise RuntimeError("live evaluation exceeded max_provider_calls")
                started = time.perf_counter()
                provider_result = _call_provider(
                    str(pair[variant_name]["prompt"]),
                    provider,
                    environment,
                    output_budget=int(provider["output_budget"]),
                )
                calls += 1
                provider_result["wall_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
                if provider_result["status"] == "succeeded":
                    review = _review_output(
                        provider_result.pop("text", ""),
                        dict(pair[variant_name]["review"]),
                        authorized_evidence_ids=list(pair[variant_name].get("authorized_evidence_ids") or []),
                    )
                    provider_result["review"] = review
                    usage = dict(provider_result.get("usage") or {})
                    usage_available = usage_available or bool(usage.get("available"))
                    cost = usage.get("cost")
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost", "estimated_cost", "actual_cost"):
                        value = usage.get(key)
                        if isinstance(value, (int, float)):
                            usage_totals[key] = (
                                (usage_totals[key] or 0) + value
                                if key in {"cost", "estimated_cost", "actual_cost"}
                                else usage_totals[key] + value
                            )
                    if (
                        isinstance(usage_totals["cost"], (int, float))
                        and usage_totals["cost"] > float(payload["cost_ceiling_usd"])
                    ):
                        raise RuntimeError("live evaluation exceeded cost_ceiling_usd")
                variants[variant_name] = provider_result
            pair_results.append({"pair_id": pair["pair_id"], "variants": variants})
        def summarize(variant_name: str) -> dict[str, Any]:
            attempts = [pair["variants"][variant_name] for pair in pair_results]
            variants = [variant for variant in attempts if variant.get("status") == "succeeded"]
            reviews = [variant["review"] for variant in variants]
            coverage_values = [
                review["requirement_coverage"]
                for review in reviews
                if review["requirement_coverage"] != "not_applicable"
            ]
            unsupported_rates = [
                review["unsupported_factual_claim_rate"]
                for review in reviews
                if isinstance(review["unsupported_factual_claim_rate"], (int, float))
            ]
            generation_input_tokens = [
                variant.get("usage", {}).get("prompt_tokens")
                for variant in variants
                if isinstance(variant.get("usage", {}).get("prompt_tokens"), (int, float))
            ]
            total_generation_tokens = [
                variant.get("usage", {}).get("total_tokens")
                for variant in variants
                if isinstance(variant.get("usage", {}).get("total_tokens"), (int, float))
            ]
            cost_values = [
                variant.get("usage", {}).get("cost")
                for variant in variants
                if isinstance(variant.get("usage", {}).get("cost"), (int, float))
            ]
            unsupported_rate = _mean([float(value) for value in unsupported_rates])
            precision = (
                round(1 - float(unsupported_rate), 6)
                if isinstance(unsupported_rate, (int, float))
                else "not_applicable"
            )
            latency_values = _numeric_values(
                [variant.get("wall_latency_ms", variant.get("latency_ms")) for variant in attempts]
            )
            return {
                "final_cv_supported_requirement_coverage": round(sum(coverage_values) / len(coverage_values), 6)
                if coverage_values
                else "not_applicable",
                "requirement_coverage": round(sum(coverage_values) / len(coverage_values), 6)
                if coverage_values
                else "not_applicable",
                "unsupported_factual_claim_rate": unsupported_rate,
                "reviewed_factual_precision": precision,
                "human_quality_score": "not_available",
                "first_pass_acceptance": round(
                    sum(variant["review"]["accepted"] and int(variant.get("attempt_count", 1)) == 1 for variant in variants)
                    / len(attempts),
                    6,
                ) if attempts else 0.0,
                "final_acceptance": round(
                    sum(variant["review"]["accepted"] for variant in variants) / len(attempts), 6
                ) if attempts else 0.0,
                "first_pass_accepted": sum(
                    variant["review"]["accepted"] and int(variant.get("attempt_count", 1)) == 1
                    for variant in variants
                ),
                "final_accepted": sum(variant["review"]["accepted"] for variant in variants),
                "unresolved_review_count": sum(
                    bool(variant.get("review", {}).get("claim_review_queue")) for variant in variants
                ),
                "repair_attempts": sum(max(0, int(variant.get("attempt_count", 1)) - 1) for variant in variants),
                "successful_calls": len(variants),
                "succeeded_calls": len(variants),
                "attempted_calls": len(attempts),
                "failed_calls": len(attempts) - len(variants),
                "accepted_cv_rate_over_attempts": round(
                    sum(variant["review"]["accepted"] for variant in variants) / len(attempts), 6
                ) if attempts else 0.0,
                "generation_input_tokens": sum(generation_input_tokens)
                if generation_input_tokens
                else "not_available",
                "total_generation_tokens": sum(total_generation_tokens)
                if total_generation_tokens
                else "not_available",
                "cost": sum(cost_values) if cost_values else "not_available",
                "latency_ms": _mean(latency_values),
            }

        by_variant = {name: summarize(name) for name in ("baseline", "fitcv")}
        paired_metrics = {
            "requirement_coverage": [],
            "reviewed_factual_precision": [],
            "first_pass_acceptance": [],
            "final_acceptance": [],
            "generation_input_tokens": [],
            "total_generation_tokens": [],
            "human_quality_score": [],
        }
        for pair in pair_results:
            baseline = pair["variants"]["baseline"]
            fitcv = pair["variants"]["fitcv"]
            if baseline.get("status") != "succeeded" or fitcv.get("status") != "succeeded":
                continue
            baseline_review = baseline["review"]
            fitcv_review = fitcv["review"]
            values = {
                "requirement_coverage": (baseline_review.get("requirement_coverage"), fitcv_review.get("requirement_coverage")),
                "reviewed_factual_precision": (
                    1 - baseline_review["unsupported_factual_claim_rate"]
                    if isinstance(baseline_review.get("unsupported_factual_claim_rate"), (int, float))
                    else None,
                    1 - fitcv_review["unsupported_factual_claim_rate"]
                    if isinstance(fitcv_review.get("unsupported_factual_claim_rate"), (int, float))
                    else None,
                ),
                "first_pass_acceptance": (
                    float(baseline_review["accepted"] and int(baseline.get("attempt_count", 1)) == 1),
                    float(fitcv_review["accepted"] and int(fitcv.get("attempt_count", 1)) == 1),
                ),
                "final_acceptance": (float(baseline_review["accepted"]), float(fitcv_review["accepted"])),
                "generation_input_tokens": (
                    baseline.get("usage", {}).get("prompt_tokens"),
                    fitcv.get("usage", {}).get("prompt_tokens"),
                ),
                "total_generation_tokens": (
                    baseline.get("usage", {}).get("total_tokens"),
                    fitcv.get("usage", {}).get("total_tokens"),
                ),
            }
            for metric, pair_values in values.items():
                if all(isinstance(value, (int, float)) for value in pair_values):
                    paired_metrics[metric].append((float(pair_values[0]), float(pair_values[1])))
        confidence_intervals = {
            metric: paired_bootstrap_delta(values)
            for metric, values in paired_metrics.items()
        }
        human_review = _human_review_metrics(payload, [str(pair["pair_id"]) for pair in payload["pairs"]])
        human_scores = {
            (str(row.get("pair_id") or ""), str(row.get("variant") or "")): _annotation_score(row)
            for row in _annotation_rows(payload)
            if not _is_unresolved_review(row)
        }
        for pair in pair_results:
            baseline_score = human_scores.get((str(pair["pair_id"]), "baseline"))
            fitcv_score = human_scores.get((str(pair["pair_id"]), "fitcv"))
            if isinstance(baseline_score, (int, float)) and isinstance(fitcv_score, (int, float)):
                paired_metrics["human_quality_score"].append((float(baseline_score), float(fitcv_score)))
        confidence_intervals["human_quality_score"] = paired_bootstrap_delta(paired_metrics["human_quality_score"])
        for variant_name in ("baseline", "fitcv"):
            by_variant[variant_name]["human_quality_score"] = human_review["by_variant"][variant_name]["quality_score"]
        paired_input_tokens = paired_metrics["generation_input_tokens"]
        usage_totals["available"] = usage_available
        usage_totals["cost_available"] = isinstance(usage_totals["cost"], (int, float))
        if usage_totals["actual_cost"] is None and usage_totals["cost_available"]:
            usage_totals["actual_cost"] = usage_totals["cost"]
        usage_totals["cost_status"] = "actual" if usage_totals["cost_available"] else (
            "estimated" if isinstance(usage_totals["estimated_cost"], (int, float)) else "unavailable"
        )
        usage_totals["token_scopes"] = {
            "generation_input_tokens": usage_totals["prompt_tokens"] or "not_available",
            "generation_total_tokens": usage_totals["total_tokens"] or "not_available",
            "workflow_total_tokens": "not_measured_without retrieval, validation, and repair telemetry",
        }
        return {
            "evaluation_schema_version": 2,
            "mode": "live",
            "provider_calls": calls,
            "fixture_sha256": payload["offline_gate"]["fixture_sha256"],
            "pair_count": len(payload["pairs"]),
            "pair_fingerprint": _fingerprint(payload["pairs"]),
            "rubric_fingerprint": _fingerprint([pair["baseline"].get("review") for pair in payload["pairs"]]),
            "config_fingerprint": _fingerprint({key: provider.get(key) for key in ("model", "template", "generation_settings", "output_budget")}),
            "thresholds": dict(dict(payload.get("fixture") or {}).get("thresholds") or payload.get("thresholds") or {}),
            "metrics": {
                "by_variant": by_variant,
                "fitcv_minus_baseline": {
                    key: (
                        by_variant["fitcv"][key] - by_variant["baseline"][key]
                        if isinstance(by_variant["fitcv"].get(key), (int, float))
                        and isinstance(by_variant["baseline"].get(key), (int, float))
                        else "not_comparable"
                    )
                    for key in (
                        "final_cv_supported_requirement_coverage",
                        "reviewed_factual_precision",
                        "unsupported_factual_claim_rate",
                        "first_pass_acceptance",
                        "final_acceptance",
                        "accepted_cv_rate_over_attempts",
                        "generation_input_tokens",
                        "total_generation_tokens",
                        "cost",
                        "latency_ms",
                    )
                },
                "provider_usage": usage_totals,
                "confidence_intervals": confidence_intervals,
                "human_review": human_review,
                "context": {
                    "fitcv_input_tokens_lower_fraction": round(
                        sum(fitcv < baseline for baseline, fitcv in paired_input_tokens) / len(paired_input_tokens), 6
                    ) if paired_input_tokens else "not_available",
                },
            },
            "reviewer": "deterministic_fixture_rubric_v1",
            "pair_results": pair_results,
        }
    return {
        "evaluation_schema_version": 2,
        "mode": "dry-run",
        "provider_calls": False,
        "fixture_sha256": payload["offline_gate"]["fixture_sha256"],
        "pair_count": len(payload["pairs"]),
        "pair_fingerprint": _fingerprint(payload["pairs"]),
        "metrics": {
            "final_cv_supported_requirement_coverage": "not_measured",
            "unsupported_factual_claim_rate": "not_measured",
            "first_pass_acceptance": "not_measured",
            "final_acceptance": "not_measured",
            "repair_attempts": "not_measured",
            "provider_usage": "not_measured",
            "human_review": _human_review_metrics(payload, [str(pair["pair_id"]) for pair in payload["pairs"]]),
        },
        "rubric_fingerprint": _fingerprint([pair["baseline"].get("review") for pair in payload["pairs"]]),
        "config_fingerprint": _fingerprint({
            key: payload["provider"].get(key)
            for key in ("model", "template", "generation_settings", "output_budget")
        }),
        "thresholds": dict(dict(payload.get("fixture") or {}).get("thresholds") or payload.get("thresholds") or {}),
        "limitations": [
            "Dry-run validates pair comparability only; it does not generate or review CVs.",
            "Provider usage and cost require a separately approved live adapter.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args()
    result = evaluate(_load_json(args.input), dry_run=not args.live)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
