from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Any

import yaml

from fitcv import config_loader
from fitcv.semantic_snapshot import compile_semantic_policy

_FIELD_SPECS = {
    "skill": ("skill_synonyms", "skill_synonyms", Path("config/taxonomy/skill_synonyms.yaml")),
    "domain": ("domain_alias_map", "domain_alias_map", Path("config/taxonomy/domain_synonyms.yaml")),
    "role_family": (
        "role_family_alias_map",
        "role_family_alias_map",
        Path("config/taxonomy/role_family_synonyms.yaml"),
    ),
}
_YAML_TOP_LEVEL_KEY_RE = re.compile(r"^[A-Za-z0-9_]+\s*:")


def _field_spec(field: str) -> tuple[str, str, Path]:
    try:
        return _FIELD_SPECS[field]
    except KeyError as exc:
        raise ValueError(f"unsupported synonym field: {field}") from exc


def replace_yaml_top_level_mapping_block(
    *,
    raw_yaml: str,
    key: str,
    mappings: dict[str, str],
) -> str:
    lines = raw_yaml.splitlines(keepends=True)
    start_idx: int | None = None
    for idx, line in enumerate(lines):
        if line.startswith(f"{key}:"):
            start_idx = idx
            break
    replacement = render_yaml_top_level_mapping(key=key, mappings=mappings)
    if start_idx is None:
        separator = "\n" if raw_yaml and not raw_yaml.endswith("\n") else ""
        return raw_yaml + separator + "".join(replacement)
    end_idx = start_idx + 1
    while end_idx < len(lines):
        candidate = lines[end_idx]
        if candidate.startswith("#") or not candidate.strip() or candidate[:1].isspace():
            end_idx += 1
            continue
        if _YAML_TOP_LEVEL_KEY_RE.match(candidate):
            break
        end_idx += 1
    return "".join([*lines[:start_idx], *replacement, *lines[end_idx:]])


def render_yaml_top_level_mapping(*, key: str, mappings: dict[str, str]) -> list[str]:
    if not mappings:
        return [f"{key}: {{}}\n"]
    return [f"{key}:\n"] + [
        f"  {alias}: {canonical}\n" for alias, canonical in sorted(mappings.items())
    ]


def compile_global_synonym_map(field: str, mappings: dict[str, str]) -> dict[str, str]:
    config_key, _, _ = _field_spec(field)
    policy = compile_semantic_policy({config_key: mappings})
    return dict(policy["maps"][field])


def load_global_synonym_map(
    field: str,
    *,
    path: Path | None = None,
) -> dict[str, str]:
    config_key, yaml_key, default_path = _field_spec(field)
    resolved_path = path or default_path
    if not resolved_path.exists():
        return {}
    payload = config_loader.load_yaml_text(
        resolved_path.read_text(encoding="utf-8"),
        source=str(resolved_path),
        reject_duplicate_keys=True,
    )
    raw_map = payload.get(yaml_key) if isinstance(payload, dict) else None
    return compile_global_synonym_map(field, raw_map if isinstance(raw_map, dict) else {})


def persist_global_synonym_map(
    field: str,
    mappings: dict[str, str],
    *,
    path: Path | None = None,
) -> dict[str, str]:
    _, yaml_key, default_path = _field_spec(field)
    resolved_path = path or default_path
    compiled = compile_global_synonym_map(field, mappings)
    resolved_path.parent.mkdir(parents=True, exist_ok=True)
    raw_yaml = resolved_path.read_text(encoding="utf-8") if resolved_path.exists() else ""
    if field == "skill":
        content = yaml.safe_dump(
            {yaml_key: compiled},
            allow_unicode=True,
            sort_keys=False,
        )
    else:
        content = replace_yaml_top_level_mapping_block(
            raw_yaml=raw_yaml,
            key=yaml_key,
            mappings=compiled,
        )
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=str(resolved_path.parent),
            prefix=f"{resolved_path.name}.",
            suffix=".tmp",
            delete=False,
        ) as tmp_file:
            tmp_file.write(content)
            tmp_file.flush()
            os.fsync(tmp_file.fileno())
            tmp_path = Path(tmp_file.name)
        os.replace(tmp_path, resolved_path)
    finally:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
    return compiled


def synonym_policy_error_reason(exc: Exception) -> str:
    message = str(exc).lower()
    if "cycle" in message:
        return "synonym_cycle"
    if "collision" in message or "conflict" in message or "duplicate" in message:
        return "synonym_alias_conflict"
    return "invalid_synonym_policy"
