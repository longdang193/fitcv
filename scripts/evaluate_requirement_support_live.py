"""Run bounded paired final-CV evaluation against a configured provider."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv.llm_runtime import LlmTaskRequest, LlmValidationResult, execute_llm_task
from fitcv.runtime_routing import resolve_llm_routing


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected object in {path}")
    return payload


def _fingerprint(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def extract_provider_usage(response: dict[str, Any]) -> dict[str, Any]:
    usage = dict(response.get("usage") or response.get("metadata", {}).get("usage") or {})
    return {
        "prompt_tokens": usage.get("prompt_tokens", usage.get("input_tokens")),
        "completion_tokens": usage.get("completion_tokens", usage.get("output_tokens")),
        "total_tokens": usage.get("total_tokens"),
        "cost": usage.get("cost"),
        "available": bool(usage),
    }


def _review_output(text: str, review: dict[str, Any]) -> dict[str, Any]:
    normalized = str(text or "").casefold()
    requirements = list(review.get("requirements") or [])
    covered = []
    for requirement in requirements:
        requirement_id = str(requirement.get("requirement_id") or "")
        terms = [str(term).casefold() for term in list(requirement.get("terms") or []) if str(term).strip()]
        if requirement_id and terms and any(term in normalized for term in terms):
            covered.append(requirement_id)
    unsupported_markers = [
        str(marker).casefold()
        for marker in list(review.get("unsupported_claim_markers") or [])
        if str(marker).strip()
    ]
    unsupported_hits = sorted({marker for marker in unsupported_markers if marker in normalized})
    positive_count = len(requirements)
    coverage = "not_applicable" if positive_count == 0 else round(len(covered) / positive_count, 6)
    return {
        "covered_requirements": covered,
        "requirement_coverage": coverage,
        "unsupported_claim_hits": unsupported_hits,
        "unsupported_factual_claim_rate": round(len(unsupported_hits) / len(unsupported_markers), 6)
        if unsupported_markers
        else 0.0,
        "accepted": not unsupported_hits and (coverage == "not_applicable" or coverage == 1.0),
    }


def _call_provider(prompt: str, provider: dict[str, Any], environ: dict[str, str]) -> dict[str, Any]:
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
    gate = dict(payload.get("offline_gate") or {})
    if gate.get("passed") is not True:
        errors.append("offline_gate.passed must be true")
    provider = dict(payload.get("provider") or {})
    for field in ("model", "template", "generation_settings", "output_budget"):
        if field not in provider:
            errors.append(f"provider.{field} is required")
    pairs = list(payload.get("pairs") or [])
    if not pairs:
        errors.append("pairs must not be empty")
    for pair in pairs:
        pair_id = str(pair.get("pair_id") or "")
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
    return errors


def evaluate(
    payload: dict[str, Any],
    *,
    dry_run: bool = True,
    environ: dict[str, str] | None = None,
) -> dict[str, Any]:
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
        usage_totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0, "cost": None}
        usage_available = False
        for pair in payload["pairs"]:
            variants = {}
            for variant_name in ("baseline", "fitcv"):
                if calls >= max_calls:
                    raise RuntimeError("live evaluation exceeded max_provider_calls")
                started = time.perf_counter()
                provider_result = _call_provider(str(pair[variant_name]["prompt"]), provider, environment)
                calls += 1
                provider_result["wall_latency_ms"] = round((time.perf_counter() - started) * 1000, 3)
                if provider_result["status"] == "succeeded":
                    review = _review_output(provider_result.pop("text", ""), dict(pair[variant_name]["review"]))
                    provider_result["review"] = review
                    usage = dict(provider_result.get("usage") or {})
                    usage_available = usage_available or bool(usage.get("available"))
                    for key in ("prompt_tokens", "completion_tokens", "total_tokens", "cost"):
                        value = usage.get(key)
                        if isinstance(value, (int, float)):
                            usage_totals[key] = (
                                (usage_totals[key] or 0) + value
                                if key == "cost"
                                else usage_totals[key] + value
                            )
                    if (
                        isinstance(usage_totals["cost"], (int, float))
                        and usage_totals["cost"] > float(payload["cost_ceiling_usd"])
                    ):
                        raise RuntimeError("live evaluation exceeded cost_ceiling_usd")
                variants[variant_name] = provider_result
            pair_results.append({"pair_id": pair["pair_id"], "variants": variants})
        successful_by_variant = {
            variant_name: [
                pair["variants"][variant_name]
                for pair in pair_results
                if pair["variants"][variant_name]["status"] == "succeeded"
            ]
            for variant_name in ("baseline", "fitcv")
        }

        def summarize(variants: list[dict[str, Any]]) -> dict[str, Any]:
            reviews = [variant["review"] for variant in variants]
            coverage_values = [
                review["requirement_coverage"]
                for review in reviews
                if review["requirement_coverage"] != "not_applicable"
            ]
            unsupported_rates = [review["unsupported_factual_claim_rate"] for review in reviews]
            return {
                "final_cv_supported_requirement_coverage": round(sum(coverage_values) / len(coverage_values), 6)
                if coverage_values
                else "not_applicable",
                "unsupported_factual_claim_rate": round(sum(unsupported_rates) / len(unsupported_rates), 6)
                if unsupported_rates
                else "not_applicable",
                "first_pass_acceptance": round(
                    sum(variant["review"]["accepted"] for variant in variants) / len(variants), 6
                )
                if variants
                else 0.0,
                "final_acceptance": round(
                    sum(variant["review"]["accepted"] for variant in variants) / len(variants), 6
                )
                if variants
                else 0.0,
                "repair_attempts": 0,
                "provider_calls": len(variants),
            }

        by_variant = {name: summarize(values) for name, values in successful_by_variant.items()}
        return {
            "evaluation_schema_version": 1,
            "mode": "live",
            "provider_calls": calls,
            "fixture_sha256": payload["offline_gate"]["fixture_sha256"],
            "pair_count": len(payload["pairs"]),
            "pair_fingerprint": _fingerprint(payload["pairs"]),
            "metrics": {
                "by_variant": by_variant,
                "fitcv_minus_baseline": {
                    key: (
                        by_variant["fitcv"][key] - by_variant["baseline"][key]
                        if isinstance(by_variant["fitcv"][key], (int, float))
                        and isinstance(by_variant["baseline"][key], (int, float))
                        else "not_comparable"
                    )
                    for key in (
                        "final_cv_supported_requirement_coverage",
                        "unsupported_factual_claim_rate",
                        "first_pass_acceptance",
                        "final_acceptance",
                    )
                },
                "provider_usage": {**usage_totals, "available": usage_available},
            },
            "reviewer": "deterministic_fixture_rubric_v1",
            "pair_results": pair_results,
        }
    return {
        "evaluation_schema_version": 1,
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
        },
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
