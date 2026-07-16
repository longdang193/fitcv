param(
    [string]$OutputPath = "artifacts/live_audit_inverse_optimization_20260716_hard_gate/hard-gate-summary.json"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$env:FITCV_HARD_GATE_OUTPUT = $OutputPath

$python = @'
from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from fitcv.config import load_config
from fitcv.fit_factors import build_candidate_fit_context, fingerprint_eligibility_policy
from fitcv.ranking_contract import build_baseline_result, build_ranking_contract_context
from fitcv.rule_filter import apply_rule_filters


config = copy.deepcopy(load_config())
config.setdefault("synonym_management", {})["promote_global_enabled"] = False
config["synonym_management"]["auto_promote_global_enabled"] = False
config["eligibility_policy"]["factors"]["location_fit"]["mode"] = "ranking_only"
config["eligibility_policy"]["factors"]["language_fit"]["mode"] = "gate_required"

candidate_context = build_candidate_fit_context(
    {
        "preferences": {
            "locations": ["Berlin", "Magdeburg"],
            "location_types": ["remote", "hybrid", "onsite"],
        },
        "languages": [{"name": "English", "level": "B2"}],
    },
    valid_work_modes=config["valid_location_types"],
)
preferences = {
    "seniority_target": "mid",
    "location_types": ["remote", "hybrid", "onsite"],
    "contract_types": ["Full-time"],
    "exclude_experience_levels": ["Internship"],
    "must_have_skills": [],
    "preferred_domains": [],
}


def job(
    job_id: str,
    city: str,
    language: str,
    expected_level: str,
    extraction_status: str,
    holistic_ai_fit: float,
) -> dict[str, object]:
    return {
        "job_url": f"https://example.test/{job_id}",
        "raw_job_fingerprint": job_id,
        "seniority": "mid",
        "location_type": "hybrid",
        "contract_type": "Full-time",
        "experience_level": "Mid level",
        "required_skills": ["SQL"],
        "published_at": "2026-07-15",
        "domain": "data_engineering",
        "actual_location": {"city": city, "country": "Germany", "extraction_status": "complete"},
        "language_requirements": [
            {
                "language": language,
                "expected_level": expected_level,
                "requirement_type": "required",
                "extraction_status": extraction_status,
            }
        ],
        "holistic_ai_fit": holistic_ai_fit,
    }


jobs = [
    job("berlin-language-fail", "Berlin", "English", "C1", "complete", 0.85),
    job("magdeburg-language-unknown", "Magdeburg", "German", "B2", "partial", 0.45),
    job("berlin-language-met", "Berlin", "English", "B2", "complete", 0.75),
    job("hamburg-language-met", "Hamburg", "English", "B2", "complete", 0.35),
]
filter_result = apply_rule_filters(
    jobs,
    preferences,
    config,
    candidate_fit_context=candidate_context,
)
records_by_url = {
    record["job_url"]: record
    for record in (*filter_result["passed_records"], *filter_result["rejected"])
}
eligibility_fingerprint = fingerprint_eligibility_policy(config["eligibility_policy"])
ranking_context = build_ranking_contract_context(
    config["ranking_policy"],
    eligibility_policy=config["eligibility_policy"],
    eligibility_policy_fingerprint=eligibility_fingerprint,
)

baseline_rows = []
for item in jobs:
    job_url = str(item["job_url"])
    if job_url not in filter_result["passed"]:
        continue
    record = records_by_url[job_url]
    location_value = record["fit_factor_results"]["location_fit"]["ranking_value"]
    baseline = build_baseline_result(
        holistic_ai_fit=item["holistic_ai_fit"],
        structured_factors={
            "must_have_match": 0.5,
            "title_relevance": 0.5,
            "seniority_fit": 0.5,
            "declared_preference_fit": 0.5,
            "location_fit": location_value,
        },
        context=ranking_context,
    )
    baseline_rows.append(
        {
            "job_url": job_url,
            "holistic_ai_fit": item["holistic_ai_fit"],
            "baseline_fit": baseline["baseline_fit"],
            "baseline_fit_label": baseline["baseline_fit_label"],
            "location_fit": location_value,
            "language_effective_weight": baseline["normalized_factors"]["language_fit"][
                "effective_weight"
            ],
        }
    )

rejected = records_by_url["https://example.test/berlin-language-fail"]
unknown = records_by_url["https://example.test/magdeburg-language-unknown"]
effective_weights = ranking_context["effective_structured_factor_weights"]
location_values = sorted({row["location_fit"] for row in baseline_rows})

assert rejected["eligibility_decision"] == "reject"
assert rejected["fit_factor_results"]["language_fit"]["evaluation"]["status"] == "fail"
assert rejected["job_url"] not in filter_result["passed"]
assert unknown["eligibility_decision"] == "retain"
assert unknown["fit_factor_results"]["language_fit"]["evaluation"]["status"] == "unknown"
assert unknown["eligibility_reason_codes"] == ["language_required_unknown"]
assert "language_fit" not in effective_weights
assert abs(sum(effective_weights.values()) - 1.0) < 1.0e-12
assert abs(effective_weights["location_fit"] - (0.1 / 0.9)) < 1.0e-12
assert location_values == [0.0, 1.0]
assert {row["baseline_fit_label"] for row in baseline_rows} == {"strong", "stretch", "skip"}
assert all(row["baseline_fit"] == row["holistic_ai_fit"] for row in baseline_rows)
assert all(row["language_effective_weight"] == 0.0 for row in baseline_rows)

summary = {
    "status": "passed",
    "scenario": "location-ranking-language-hard-gate-v1",
    "preferred_locations": candidate_context["preferred_locations"],
    "synonym_mutation_disabled": config["synonym_management"],
    "rejected_before_ranking": [record["job_url"] for record in filter_result["rejected"]],
    "ranked_job_urls": list(filter_result["passed"]),
    "unknown_language_diagnostic": {
        "job_url": unknown["job_url"],
        "status": unknown["fit_factor_results"]["language_fit"]["evaluation"]["status"],
        "reason_codes": unknown["eligibility_reason_codes"],
    },
    "effective_structured_factor_weights": effective_weights,
    "effective_weight_sum": sum(effective_weights.values()),
    "location_ranking_values": location_values,
    "baseline_rows": baseline_rows,
    "eligibility_policy_fingerprint": eligibility_fingerprint,
    "ranking_contract_fingerprint": ranking_context["ranking_contract_fingerprint"],
}
output_path = Path(os.environ["FITCV_HARD_GATE_OUTPUT"])
output_path.parent.mkdir(parents=True, exist_ok=True)
output_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
print(json.dumps(summary, sort_keys=True))
'@

$python | uv run python -
if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}
