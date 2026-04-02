"""Load project configuration from .env.yaml and config/*.yaml policy files.

Load order
----------
1. .env.yaml          — infrastructure secrets (GCP project, SA key, etc.)
2. config/taxonomy.yaml      — seniority ladder, allowed enum values
3. config/skill_synonyms.yaml — skill alias → canonical mapping
4. config/pipeline.yaml      — model names, top_n limits, batch/sleep settings
5. config/ranking.yaml        — ranking weights, fit-label thresholds, missing defaults
6. config/cv.yaml             — CV generation and validation defaults (nested preset-based)

Later files do NOT override .env.yaml keys. They only add new top-level keys.
Missing config/*.yaml files → warning logged, not a crash (safe degradation).

CV config contract (preset-based, v2)
-------------------------------------
config["cv"] is the canonical nested object:
  - cv.preset             : preset name string
  - cv.generation.model    : LLM model name
  - cv.generation.prompt_version : version tag
  - cv.composition.<section>.enabled : bool
  - cv.content_rules.<rule> : bool
  - cv.validation.max_pages : int

Backward-compatibility projection (TEMPORARY — remove after plan 2 lands)
  config["cv_generation_model"]   → cv.generation.model
  config["prompt_version"]        → cv.generation.prompt_version
  config["cv_max_pages"]           → cv.validation.max_pages
  config["required_cv_sections"]   → list derived from composition (enabled:true)
"""

import logging
import os
from fitcv.cv_presets import SUPPORTED_PRESETS
import warnings
from pathlib import Path
from typing import Any

import yaml
from fitcv.prompts import get_prompt_definition

logger = logging.getLogger(__name__)

_REQUIRED_KEYS = [
    "gcp_project",
    "bigquery_dataset",
    "service_account_key",
]

# Optional — only needed when using the Apify API source
_APIFY_KEYS = ["apify_dataset_id", "apify_token"]

# Config YAML files merged into the base config (relative to repo root)
_POLICY_FILES = [
    "taxonomy.yaml",
    "skill_synonyms.yaml",
    "pipeline.yaml",
    "ranking.yaml",
    "cv.yaml",
]

_DEFAULT_ENV_CANDIDATES = (".env.yaml", "config/env.yaml")
_DEFAULT_ENRICH_PROMPT_ID = "enrich.extraction.v1"
_INFRA_ENV_OVERRIDES = {
    "gcp_project": "GCP_PROJECT",
    "bigquery_dataset": "BIGQUERY_DATASET",
    "service_account_key": "GOOGLE_APPLICATION_CREDENTIALS",
}
CV_STRUCTURED_SECTION_KEYS = (
    "header",
    "summary",
    "experience",
    "projects",
    "education",
    "skills",
    "certifications",
    "publications",
    "languages",
)
CV_SECTION_KEY_TO_NAME = {
    "header": "Header",
    "summary": "Summary",
    "education": "Education",
    "experience": "Experience",
    "skills": "Skills",
    "certifications": "Certifications",
    "projects": "Projects",
    "publications": "Publications",
    "languages": "Languages",
}
CV_SECTION_NAME_TO_KEY = {
    display_name.lower(): section_key
    for section_key, display_name in CV_SECTION_KEY_TO_NAME.items()
}


def _load_yaml_file(path: Path) -> dict[str, Any]:
    """Load a single YAML file. Returns {} on missing file or empty file."""
    if not path.exists():
        logger.warning("Config file not found (skipping): %s", path)
        return {}
    with open(path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def _find_config_dir(base_path: Path) -> Path:
    """Locate the config/ directory relative to .env.yaml or the repo root."""
    # Walk up from the .env.yaml location to find a config/ dir
    candidate = base_path.parent
    for _ in range(4):  # max 4 levels up
        config_dir = candidate / "config"
        if config_dir.is_dir():
            return config_dir
        candidate = candidate.parent
    return base_path.parent / "config"  # fallback: sibling of .env.yaml


def _resolve_env_path(path: str | Path | None) -> Path:
    """Resolve the active env file, supporting legacy config/env.yaml."""
    if path is not None:
        return Path(path)
    for candidate in _DEFAULT_ENV_CANDIDATES:
        candidate_path = Path(candidate)
        if candidate_path.exists():
            return candidate_path
    return Path(_DEFAULT_ENV_CANDIDATES[0])


def _is_legacy_env_path(path: Path) -> bool:
    return path.name == "env.yaml" and path.parent.name == "config"


def _merge_missing_keys(base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
    for key, value in extra.items():
        if key not in base:
            base[key] = value
    return base


def _normalize_skill_synonyms(raw_synonyms: Any) -> dict[str, str]:
    if not isinstance(raw_synonyms, dict):
        return {}
    return {
        str(alias).strip().lower(): str(canonical).strip().lower()
        for alias, canonical in raw_synonyms.items()
        if str(alias).strip() and str(canonical).strip()
    }


def parse_skill_synonym_overlay_yaml(raw_yaml: str) -> dict[str, str]:
    """Parse and validate a run-scoped synonym overlay YAML payload."""
    try:
        payload = yaml.safe_load(raw_yaml)
    except yaml.YAMLError as exc:
        raise ValueError("Synonym overlay must be valid YAML") from exc
    if payload is None:
        raise ValueError("Synonym overlay must define at least one mapping")
    if not isinstance(payload, dict):
        raise ValueError("Synonym overlay must be a mapping")
    candidate = payload.get("skill_synonyms") if "skill_synonyms" in payload else payload
    if not isinstance(candidate, dict):
        raise ValueError("Synonym overlay entries must be provided as a mapping")

    normalized: dict[str, str] = {}
    for alias, canonical in candidate.items():
        alias_normalized = str(alias).strip().lower()
        canonical_normalized = str(canonical).strip().lower()
        if not alias_normalized or not canonical_normalized:
            raise ValueError("Synonym overlay aliases and canonicals must be non-empty strings")
        normalized[alias_normalized] = canonical_normalized
    if not normalized:
        raise ValueError("Synonym overlay must define at least one mapping")
    return normalized


def apply_runtime_skill_synonym_overlay(
    cfg: dict[str, Any],
    overlay_synonyms: dict[str, str],
    *,
    source: str,
    filename: str,
    uploaded_at: str,
) -> dict[str, Any]:
    """Return cfg with a run-scoped synonym overlay merged in."""
    updated_cfg = dict(cfg)
    runtime = dict(updated_cfg.get("skill_synonyms_runtime") or {})
    base_effective_synonyms = runtime.get("pre_run_overlay_skill_synonyms")
    if not isinstance(base_effective_synonyms, dict):
        base_effective_synonyms = _normalize_skill_synonyms(updated_cfg.get("skill_synonyms"))
    base_effective_synonyms = _normalize_skill_synonyms(base_effective_synonyms)
    merged_synonyms = dict(base_effective_synonyms)
    merged_synonyms.update(_normalize_skill_synonyms(overlay_synonyms))
    runtime["pre_run_overlay_skill_synonyms"] = dict(base_effective_synonyms)
    runtime["has_overlay"] = bool(runtime.get("overlay_paths") or overlay_synonyms)
    runtime["entry_count"] = len(merged_synonyms)
    runtime["has_run_overlay"] = bool(overlay_synonyms)
    runtime["run_overlay_source"] = source
    runtime["run_overlay_filename"] = filename
    runtime["run_overlay_uploaded_at"] = uploaded_at
    runtime["run_overlay_entry_count"] = len(overlay_synonyms)
    updated_cfg["skill_synonyms"] = merged_synonyms
    updated_cfg["skill_synonyms_runtime"] = runtime
    return updated_cfg


def _apply_prompt_defaults(cfg: dict[str, Any]) -> dict[str, Any]:
    prompts = cfg.get("prompts")
    if not isinstance(prompts, dict):
        prompts = {}
    enrich_prompt_cfg = prompts.get("enrich")
    if not isinstance(enrich_prompt_cfg, dict):
        enrich_prompt_cfg = {}
    extraction_cfg = enrich_prompt_cfg.get("extraction")
    if not isinstance(extraction_cfg, dict):
        extraction_cfg = {}
    prompt_id = str(extraction_cfg.get("prompt_id") or _DEFAULT_ENRICH_PROMPT_ID).strip()
    extraction_cfg["prompt_id"] = prompt_id or _DEFAULT_ENRICH_PROMPT_ID
    enrich_prompt_cfg["extraction"] = extraction_cfg
    prompts["enrich"] = enrich_prompt_cfg
    cfg["prompts"] = prompts
    return cfg


def _build_prompts_runtime(cfg: dict[str, Any]) -> dict[str, Any]:
    prompt_id = str(
        (((cfg.get("prompts") or {}).get("enrich") or {}).get("extraction") or {}).get("prompt_id")
        or _DEFAULT_ENRICH_PROMPT_ID
    )
    definition = get_prompt_definition(prompt_id)
    return {
        "enrich": {
            "extraction": {
                "prompt_id": definition.prompt_id,
                "version": definition.version,
                "template_path": str(definition.template_path),
                "stage_id": definition.stage_id,
            }
        }
    }


def _validate_prompt_config(cfg: dict[str, Any]) -> None:
    prompt_id = str(
        (((cfg.get("prompts") or {}).get("enrich") or {}).get("extraction") or {}).get("prompt_id")
        or ""
    ).strip()
    if not prompt_id:
        raise ValueError("prompts.enrich.extraction.prompt_id is required")
    try:
        get_prompt_definition(prompt_id)
    except KeyError as exc:
        raise ValueError(f"Unknown enrich prompt_id: {prompt_id}") from exc


def _resolve_config_relative_path(config_dir: Path, raw_path: str | Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return config_dir / path


def _load_skill_synonym_overlays(
    *,
    config_dir: Path,
    overlay_paths: list[str],
) -> tuple[dict[str, str], list[str]]:
    merged: dict[str, str] = {}
    resolved_paths: list[str] = []
    for overlay_path in overlay_paths:
        resolved_path = _resolve_config_relative_path(config_dir, overlay_path)
        overlay_cfg = _load_yaml_file(resolved_path)
        raw_overlay = overlay_cfg.get("skill_synonyms") if "skill_synonyms" in overlay_cfg else overlay_cfg
        overlay_synonyms = _normalize_skill_synonyms(raw_overlay)
        if not overlay_synonyms:
            continue
        merged.update(overlay_synonyms)
        resolved_paths.append(str(resolved_path))
    return merged, resolved_paths


def _normalize_config_keys(cfg: dict[str, Any]) -> dict[str, Any]:
    """Normalize legacy config keys into the canonical runtime shape."""
    if "gemini_model" not in cfg and "ai_score_model" in cfg:
        cfg["gemini_model"] = cfg["ai_score_model"]
    if "vertex_location" not in cfg:
        location = str(cfg.get("location", "")).strip()
        if location and location.lower() != "us":
            cfg["vertex_location"] = location
    return cfg


def _apply_infra_env_overrides(cfg: dict[str, Any]) -> dict[str, Any]:
    """Prefer standard environment variables for portable runtime configuration."""
    for cfg_key, env_key in _INFRA_ENV_OVERRIDES.items():
        env_value = os.environ.get(env_key, "").strip()
        if env_value:
            cfg[cfg_key] = env_value
    return cfg


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    """Load and validate config from .env.yaml, then merge policy YAML files.

    Args:
        path: Path to the .env.yaml config file.

    Returns:
        Merged config dict. Policy file keys are added alongside .env.yaml keys.
        .env.yaml keys always win on collision.

    Raises:
        FileNotFoundError: If .env.yaml does not exist.
        ValueError: If required infrastructure keys are missing from .env.yaml.
    """
    env_path = _resolve_env_path(path)
    if not env_path.exists():
        raise FileNotFoundError(f"Config file not found: {env_path}")
    if _is_legacy_env_path(env_path):
        warnings.warn(
            f"legacy config path in use: {env_path}",
            UserWarning,
            stacklevel=2,
        )

    with open(env_path) as f:
        cfg: dict[str, Any] = yaml.safe_load(f) or {}

    resolved_env_path = env_path.resolve()
    config_dir = _find_config_dir(resolved_env_path)
    if env_path.name == ".env.yaml":
        legacy_env_path = config_dir / "env.yaml"
        if legacy_env_path.exists():
            cfg = _merge_missing_keys(cfg, _load_yaml_file(legacy_env_path))
    elif _is_legacy_env_path(env_path):
        root_env_path = config_dir.parent / ".env.yaml"
        if root_env_path.exists():
            cfg = _merge_missing_keys(cfg, _load_yaml_file(root_env_path))

    cfg = _normalize_config_keys(cfg)
    cfg = _apply_infra_env_overrides(cfg)

    missing = [k for k in _REQUIRED_KEYS if k not in cfg]
    if missing:
        raise ValueError(f"Missing config keys: {missing}")

    # Merge policy YAML files — later files add keys; .env.yaml keys take priority
    for filename in _POLICY_FILES:
        policy = _load_yaml_file(config_dir / filename)
        for key, value in policy.items():
            if key not in cfg:  # never overwrite .env.yaml values
                cfg[key] = value
    cfg = _apply_prompt_defaults(cfg)

    base_skill_synonyms = _normalize_skill_synonyms(cfg.get("skill_synonyms"))
    overlay_paths_raw = cfg.get("skill_synonyms_overlay_paths") or []
    overlay_paths = [
        str(item).strip()
        for item in overlay_paths_raw
        if str(item).strip()
    ] if isinstance(overlay_paths_raw, list) else []
    overlay_skill_synonyms, resolved_overlay_paths = _load_skill_synonym_overlays(
        config_dir=config_dir,
        overlay_paths=overlay_paths,
    )
    effective_skill_synonyms = dict(base_skill_synonyms)
    effective_skill_synonyms.update(overlay_skill_synonyms)
    cfg["skill_synonyms"] = effective_skill_synonyms
    cfg["skill_synonyms_runtime"] = {
        "base_policy_path": str(config_dir / "skill_synonyms.yaml"),
        "overlay_paths": resolved_overlay_paths,
        "has_overlay": bool(resolved_overlay_paths),
        "entry_count": len(effective_skill_synonyms),
    }
    _validate_prompt_config(cfg)
    cfg["prompts_runtime"] = _build_prompts_runtime(cfg)

    cfg = _normalize_config_keys(cfg)
    _validate_nested_cv_config(cfg)
    cfg = apply_cv_compatibility_projection(cfg)
    return cfg


def _validate_nested_cv_config(cfg: dict[str, Any]) -> None:
    """Validate the nested cv block after policy files are merged.

    Raises ValueError with a descriptive message for any violation.
    """
    if "cv" not in cfg:
        raise ValueError("Missing top-level 'cv' key in config")

    cv_cfg = cfg["cv"]

    if "preset" not in cv_cfg:
        raise ValueError("cv.preset is required")
    preset = str(cv_cfg["preset"])
    if preset not in SUPPORTED_PRESETS:
        raise ValueError(
            f"cv.preset must be one of {sorted(SUPPORTED_PRESETS)}, got: {preset!r}"
        )

    # generation block
    if "generation" not in cv_cfg:
        raise ValueError("cv.generation is required")
    gen = cv_cfg["generation"]
    if "model" not in gen:
        raise ValueError("cv.generation.model is required")
    if "prompt_version" not in gen:
        raise ValueError("cv.generation.prompt_version is required")

    # composition block
    if "composition" not in cv_cfg:
        raise ValueError("cv.composition is required")
    comp = cv_cfg["composition"]
    if not isinstance(comp, dict):
        raise ValueError("cv.composition must be a dict")
    # Validate composition against preset registry
    from fitcv.cv_presets import validate_composition
    comp_result = validate_composition(preset, comp)
    if not comp_result["valid"]:
        raise ValueError(
            f"cv.composition errors for preset '{preset}': {comp_result['errors']}"
        )

    # content_rules block
    if "content_rules" not in cv_cfg:
        raise ValueError("cv.content_rules is required")
    cr = cv_cfg["content_rules"]
    if not isinstance(cr, dict):
        raise ValueError("cv.content_rules must be a dict")

    # validation block
    if "validation" not in cv_cfg:
        raise ValueError("cv.validation is required")
    val = cv_cfg["validation"]
    if "max_pages" not in val:
        raise ValueError("cv.validation.max_pages is required")
    try:
        max_pages = int(val["max_pages"])
    except (TypeError, ValueError):
        raise ValueError(f"cv.validation.max_pages must be an integer, got: {val['max_pages']!r}")
    if max_pages <= 0:
        raise ValueError(f"cv.validation.max_pages must be a positive integer, got: {max_pages}")


# ── Compatibility projection (TEMPORARY — remove after preset-based admin settings plan lands) ─

def apply_cv_compatibility_projection(cfg: dict[str, Any]) -> dict[str, Any]:
    """Project nested cv keys back to flat legacy keys for the migration window.

    This lets control-plane code (settings_schema, etc.) that still reads
    flat keys continue to function until the preset-based admin settings plan
    replaces those reads with nested ones.

    TEMPORARY: Must be removed once plan 2 (preset-based admin settings) is complete.
    """
    cv_cfg = cfg.get("cv")
    if cv_cfg is None:
        return cfg

    cfg["cv_generation_model"] = str(cv_cfg.get("generation", {}).get("model", ""))
    cfg["prompt_version"] = str(cv_cfg.get("generation", {}).get("prompt_version", ""))
    cfg["cv_max_pages"] = int(cv_cfg.get("validation", {}).get("max_pages", 2))

    # required_cv_sections: enabled composition sections only.
    required: list[str] = []
    comp = cv_cfg.get("composition") or {}
    for section_name, section_cfg in comp.items():
        if not isinstance(section_cfg, dict):
            continue
        enabled = section_cfg.get("enabled", False)
        if enabled:
            required.append(section_name.title())
    cfg["required_cv_sections"] = required

    return cfg


def get_required_cv_section_names(config: dict[str, Any]) -> list[str]:
    """Return the configured display names for required CV sections."""
    flat_required = [
        str(section_name)
        for section_name in list(config.get("required_cv_sections") or [])
        if section_name
    ]
    if flat_required:
        return flat_required

    cv_cfg = config.get("cv") or {}
    composition = cv_cfg.get("composition") or {}
    derived_required: list[str] = []
    for section_key, section_cfg in composition.items():
        if not isinstance(section_cfg, dict):
            continue
        if not section_cfg.get("enabled", False):
            continue
        display_name = CV_SECTION_KEY_TO_NAME.get(section_key)
        if display_name:
            derived_required.append(display_name)
    return derived_required


def get_required_structured_section_keys(config: dict[str, Any]) -> list[str]:
    """Return structured section keys mapped from the required section names."""
    keys: list[str] = []
    seen: set[str] = set()
    for section_name in get_required_cv_section_names(config):
        key = CV_SECTION_NAME_TO_KEY.get(section_name.strip().lower())
        if key is None or key in seen:
            continue
        seen.add(key)
        keys.append(key)
    return keys


def get_vertex_location(config: dict[str, Any]) -> str:
    """Return the Vertex AI region, separate from BigQuery location."""
    vertex_location = str(config.get("vertex_location", "")).strip()
    if vertex_location:
        return vertex_location
    return "us-central1"
