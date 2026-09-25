"""Validate paired final-CV evaluation inputs without calling providers."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


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
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
        "cost": usage.get("cost"),
        "available": bool(usage),
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
        raise RuntimeError("live provider adapter is not enabled by this offline harness")
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
