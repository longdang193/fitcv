"""Canonical candidate profile seed overlays for FitCV Local."""

from __future__ import annotations

import copy
import hashlib
import json
from typing import Any

from fitcv.candidate import infer_effective_preferences, load_profile_text


SEED_MANIFEST_REVISION = "candidate-profile-seeds.v1"
CANDIDATE_PROFILE_SEEDS = (
    {
        "candidate_profile_id": "candidate-product-data",
        "name": "Product Data Specialist",
        "target_role": "Product Data Specialist",
        "role_families": ["analytics"],
        "domains": ["product"],
    },
    {
        "candidate_profile_id": "candidate-analytics",
        "name": "Analytics & Operations",
        "target_role": "Analytics & Operations",
        "role_families": ["analytics"],
        "domains": ["operations"],
    },
    {
        "candidate_profile_id": "candidate-platform",
        "name": "Data Platform Engineer",
        "target_role": "Data Platform Engineer",
        "role_families": ["data_engineering"],
        "domains": ["data platform"],
    },
)


def build_candidate_profile_seeds(base_profile: dict[str, Any]) -> list[dict[str, Any]]:
    normalized = load_profile_text(json.dumps(base_profile), format_hint="json")
    effective_preferences = infer_effective_preferences(normalized)["effective_preferences"]
    rows: list[dict[str, Any]] = []
    for index, seed in enumerate(CANDIDATE_PROFILE_SEEDS):
        profile = copy.deepcopy(normalized)
        profile["preferences"] = {
            **effective_preferences,
            "target_role": seed["target_role"],
            "role_families": seed["role_families"],
            "domains": seed["domains"],
        }
        profile_json = json.dumps(profile, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        rows.append(
            {
                "candidate_profile_id": seed["candidate_profile_id"],
                "name": seed["name"],
                "description": "",
                "profile_json": profile_json,
                "revision": 1,
                "checksum": hashlib.sha256(profile_json.encode("utf-8")).hexdigest(),
                "is_active": True,
                "is_default": index == 0,
                "sort_order": (index + 1) * 10,
                "seed_manifest_revision": SEED_MANIFEST_REVISION,
            }
        )
    return rows
