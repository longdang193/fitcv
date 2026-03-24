"""Structured candidate profile loading, validation, and BigQuery preparation.

Public API
----------
load_profile_yaml          : parse YAML profile file
validate_profile           : check required sections are present
flatten_skills             : extract deduplicated skill list from all evidence
prepare_profile_rows       : map profile to all 5 BQ table schemas
load_candidate_to_bigquery : insert into all candidate BQ tables (integration)
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml


# ── required profile sections ─────────────────────────────────────────────────

_REQUIRED_SECTIONS = ["experiences", "skills", "projects", "achievements", "preferences"]


# ── loading ───────────────────────────────────────────────────────────────────

def load_profile_yaml(path: str | Path) -> dict[str, Any]:
    """Load and return the candidate profile from a YAML file.

    Raises:
        FileNotFoundError: if the file does not exist.
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Candidate profile not found: {file_path}")
    with open(file_path, encoding="utf-8") as f:
        return yaml.safe_load(f)  # type: ignore[return-value]


# ── validation ────────────────────────────────────────────────────────────────

def validate_profile(profile: dict[str, Any]) -> list[str]:
    """Return a list of validation error strings; empty list means valid.

    Checks:
    1. Required sections are present
    2. All exp/proj/ach IDs are globally unique
    3. No dangling evidence_refs (every ref must resolve to a known ID)
    """
    errors: list[str] = []

    # ── 1. required sections ──────────────────────────────────────────────────
    for section in _REQUIRED_SECTIONS:
        if section not in profile:
            errors.append(f"Missing required section: '{section}'")

    if errors:
        return errors  # ID checks require sections; bail early

    # ── 2. ID uniqueness ──────────────────────────────────────────────────────
    all_ids: list[str] = (
        [str(e.get("id", "")) for e in profile.get("experiences", [])]
        + [str(p.get("id", "")) for p in profile.get("projects", [])]
        + [str(a.get("id", "")) for a in profile.get("achievements", [])]
    )
    seen_ids: set[str] = set()
    for id_val in all_ids:
        if not id_val:
            errors.append("Found an experience/project/achievement without an 'id' field")
        elif id_val in seen_ids:
            errors.append(f"Duplicate ID '{id_val}' in candidate profile")
        else:
            seen_ids.add(id_val)

    # ── 3. dangling evidence_refs ─────────────────────────────────────────────
    known_ids: set[str] = set(all_ids)
    for skill in profile.get("skills", []):
        for ref in skill.get("evidence_refs", []):
            if ref not in known_ids:
                errors.append(
                    f"Dangling evidence_ref '{ref}' in skill '{skill.get('name', '?')}'"
                )
    for ach in profile.get("achievements", []):
        for ref in ach.get("evidence_refs", []):
            if ref not in known_ids:
                errors.append(
                    f"Dangling evidence_ref '{ref}' in achievement '{ach.get('id', '?')}'"
                )

    return errors



# ── skill extraction ──────────────────────────────────────────────────────────

def flatten_skills(profile: dict[str, Any]) -> list[str]:
    """Return a deduplicated list of all skills mentioned in the profile.

    Collects from:
    - `skills[].name` (explicit skill inventory)
    - `experiences[].bullets[].skills`
    - `projects[].skills`
    """
    seen: set[str] = set()
    result: list[str] = []

    def _add(skill: str) -> None:
        if skill and skill not in seen:
            seen.add(skill)
            result.append(skill)

    # Explicit skill inventory
    for skill in profile.get("skills", []):
        if isinstance(skill, dict):
            _add(str(skill.get("name", "")))
        else:
            _add(str(skill))

    # Experience bullets
    for exp in profile.get("experiences", []):
        for bullet in exp.get("bullets", []):
            for skill in bullet.get("skills", []):
                _add(str(skill))

    # Projects
    for project in profile.get("projects", []):
        for skill in project.get("skills", []):
            _add(str(skill))

    return result


# ── BQ row preparation ────────────────────────────────────────────────────────

def prepare_profile_rows(profile: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Map a candidate profile dict to BQ table row lists.

    Returns a dict with keys: profile, experiences, projects, skills, achievements.
    Each value is a list of row dicts ready for BigQuery insertion.
    """
    now = datetime.now(tz=timezone.utc).isoformat()
    profile_id = str(uuid.uuid4())
    prefs = profile.get("preferences", {})

    # ── candidate_profile (1 row) ─────────────────────────────────────────────
    profile_rows: list[dict[str, Any]] = [{
        "profile_id":                 profile_id,
        "name":                       profile.get("name", ""),
        "headline":                   profile.get("headline", ""),
        "summary":                    profile.get("summary", ""),
        "location_types":             prefs.get("location_types", []),
        "domains":                    prefs.get("domains", []),
        "seniority_target":           prefs.get("seniority_target", ""),
        "exclude_contract_types":     prefs.get("exclude_contract_types", []),
        "exclude_experience_levels":  prefs.get("exclude_experience_levels", []),
        "updated_at":                 now,
    }]

    # ── candidate_experiences (1 row per bullet) ──────────────────────────────
    experience_rows: list[dict[str, Any]] = []
    for exp in profile.get("experiences", []):
        exp_id = str(exp.get("id", ""))
        for idx, bullet in enumerate(exp.get("bullets", [])):
            experience_rows.append({
                "exp_id":           exp_id,
                "role":             exp.get("role", ""),
                "company":          exp.get("company", ""),
                "location":         exp.get("location", ""),
                "start_date":       exp.get("start", ""),
                "end_date":         exp.get("end", ""),
                "bullet_index":     idx,
                "bullet_text":      bullet.get("text", ""),
                "skills":           bullet.get("skills", []),
                "measurable_impact": bullet.get("measurable_impact", ""),
                "updated_at":       now,
            })

    # ── candidate_projects ────────────────────────────────────────────────────
    project_rows: list[dict[str, Any]] = [
        {
            "project_id":     str(proj.get("id", "")),
            "name":           proj.get("name", ""),
            "skills":         proj.get("skills", []),
            "business_value": proj.get("business_value", ""),
            "evidence":       proj.get("evidence", ""),
            "updated_at":     now,
        }
        for proj in profile.get("projects", [])
    ]

    # ── candidate_skills ──────────────────────────────────────────────────────
    skill_rows: list[dict[str, Any]] = [
        {
            "skill_name":    str(skill.get("name", "")),
            "level":         skill.get("level", ""),
            "years":         skill.get("years"),
            "evidence_refs": skill.get("evidence_refs", []),
            "updated_at":    now,
        }
        for skill in profile.get("skills", [])
    ]

    # ── candidate_achievements ────────────────────────────────────────────────
    achievement_rows: list[dict[str, Any]] = [
        {
            "achievement_id": str(ach.get("id", "")),
            "text":           ach.get("text", ""),
            "category":       ach.get("category", ""),
            "evidence_refs":  ach.get("evidence_refs", []),
            "updated_at":     now,
        }
        for ach in profile.get("achievements", [])
    ]

    return {
        "profile":      profile_rows,
        "experiences":  experience_rows,
        "projects":     project_rows,
        "skills":       skill_rows,
        "achievements": achievement_rows,
    }


# ── integration: BigQuery load ────────────────────────────────────────────────

def load_candidate_to_bigquery(
    profile: dict[str, Any],
    config: dict[str, Any],
) -> None:
    """Insert all candidate profile tables into BigQuery.

    Requires GOOGLE_APPLICATION_CREDENTIALS.
    Decorated with @pytest.mark.integration in tests.
    """
    from google.cloud import bigquery  # type: ignore[import-untyped]
    from google.oauth2 import service_account  # type: ignore[import-untyped]

    project = str(config["gcp_project"])
    dataset = str(config["bigquery_dataset"])
    key_path = str(config["service_account_key"])

    credentials = service_account.Credentials.from_service_account_file(key_path)
    client = bigquery.Client(project=project, credentials=credentials)

    rows_by_table = prepare_profile_rows(profile)
    table_map = {
        "profile":      "candidate_profile",
        "experiences":  "candidate_experiences",
        "projects":     "candidate_projects",
        "skills":       "candidate_skills",
        "achievements": "candidate_achievements",
    }

    for key, table_suffix in table_map.items():
        rows = rows_by_table[key]
        if not rows:
            continue
        table_ref = f"{project}.{dataset}.{table_suffix}"
        errors = client.insert_rows_json(table_ref, rows)
        if errors:
            raise RuntimeError(f"BigQuery insert errors for {table_suffix}: {errors}")
