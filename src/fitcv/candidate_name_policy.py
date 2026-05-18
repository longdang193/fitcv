"""Shared candidate-name placeholder policy for CV generation flows."""

from typing import Any

_CANDIDATE_NAME_PLACEHOLDER_VALUES = {
    "candidate name",
    "your name",
}


def normalize_candidate_name_token(value: str) -> str:
    normalized = str(value or "")
    normalized = normalized.replace("[", " ").replace("]", " ")
    normalized = " ".join(normalized.split()).strip().lower()
    return normalized


def is_candidate_name_placeholder(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return normalize_candidate_name_token(value) in _CANDIDATE_NAME_PLACEHOLDER_VALUES


def resolved_candidate_profile_name(profile: dict[str, Any] | None) -> str:
    if not isinstance(profile, dict):
        return ""
    candidate_name = str(profile.get("name") or "").strip()
    if not candidate_name or is_candidate_name_placeholder(candidate_name):
        return ""
    return candidate_name
