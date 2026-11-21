"""Evaluate a frozen requirement-aware shortlist fixture."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from fitcv.shortlist_evaluation import evaluate_shortlist_pool, evaluation_as_of_now


def _load(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}")
    return payload


def _load_optional(path: Path | None) -> dict[str, Any] | None:
    return _load(path) if path is not None else None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-revision", required=True)
    parser.add_argument("--as-of", default=evaluation_as_of_now())
    parser.add_argument("--split-id", required=True)
    parser.add_argument("--requirement-contract-fingerprint", required=True)
    parser.add_argument("--eligibility-policy-fingerprint", required=True)
    parser.add_argument("--cache-condition", choices=("cold", "warm"), required=True)
    parser.add_argument("--latency-sample-ms", type=float, action="append", default=[])
    parser.add_argument("--legacy-baseline", type=Path)
    parser.add_argument("--retrieval-cost", type=Path)
    args = parser.parse_args()

    artifact = evaluate_shortlist_pool(
        _load(args.fixture),
        profile_revision=args.profile_revision,
        as_of=args.as_of,
        split_id=args.split_id,
        requirement_contract_fingerprint=args.requirement_contract_fingerprint,
        eligibility_policy_fingerprint=args.eligibility_policy_fingerprint,
        cache_condition=args.cache_condition,
        legacy_baseline=_load_optional(args.legacy_baseline),
        latency_samples_ms=args.latency_sample_ms,
        retrieval_cost=_load_optional(args.retrieval_cost),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(artifact, indent=2, sort_keys=True))
    return 0 if artifact["promotion_eligible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
