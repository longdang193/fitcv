from __future__ import annotations

import os
import re
import tempfile
import hashlib
import io
import json
import zipfile
import datetime
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
_BACKUP_MEMBERS = {
    "skills": "skill_synonyms.yaml",
    "domain": "domain_synonyms.yaml",
    "role_family": "role_family_synonyms.yaml",
}
_BACKUP_MAX_ARCHIVE_BYTES = 8 * 1024 * 1024
_BACKUP_MAX_MEMBER_BYTES = 2 * 1024 * 1024
_BACKUP_MAX_EXTRACTED_BYTES = 6 * 1024 * 1024

_EDITOR_FIELD_ALIASES = {"skills": "skill", "skill": "skill", "domain": "domain", "role_family": "role_family"}


def _field_spec(field: str) -> tuple[str, str, Path]:
    field = _EDITOR_FIELD_ALIASES.get(field, field)
    try:
        return _FIELD_SPECS[field]
    except KeyError as exc:
        raise ValueError(f"unsupported synonym field: {field}") from exc

def _editor_issue(
    code: str,
    message: str,
    *,
    lines: list[int],
    aliases: list[str] | None = None,
    canonicals: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "severity": "error",
        "lines": lines,
        "aliases": aliases or [],
        "canonicals": canonicals or [],
    }

def _normalized_editor_pair(field: str, alias: str, canonical: str) -> tuple[str, str]:
    compiled = compile_global_synonym_map(field, {alias: canonical})
    return next(iter(compiled.items()), ("", ""))

def parse_synonym_editor_text(field: str, editor_text: str) -> dict[str, Any]:
    """Parse line-oriented ``alias: canonical`` text with line-aware issues."""
    entries: list[tuple[int, str, str]] = []
    issues: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(editor_text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("-"):
            issues.append(_editor_issue(
                "synonym_list_syntax",
                "Use alias: canonical syntax instead of YAML list syntax.",
                lines=[line_number],
            ))
            continue
        if ":" not in line:
            issues.append(_editor_issue(
                "synonym_missing_canonical",
                "Each alias must use alias: canonical syntax.",
                lines=[line_number],
                aliases=[line],
            ))
            continue
        alias, canonical = (part.strip() for part in line.split(":", 1))
        if not alias:
            issues.append(_editor_issue(
                "synonym_empty_alias",
                "Alias cannot be empty.",
                lines=[line_number],
                canonicals=[canonical] if canonical else [],
            ))
            continue
        if not canonical:
            issues.append(_editor_issue(
                "synonym_missing_canonical",
                "Canonical term cannot be empty.",
                lines=[line_number],
                aliases=[alias],
            ))
            continue
        normalized_alias, normalized_canonical = _normalized_editor_pair(field, alias, canonical)
        entries.append((line_number, normalized_alias, normalized_canonical))

    aliases: dict[str, tuple[str, int]] = {}
    for line_number, alias, canonical in entries:
        previous = aliases.get(alias)
        if previous is not None and previous[0] != canonical:
            issues.append(_editor_issue(
                "synonym_alias_conflict",
                "One alias maps to multiple canonical terms.",
                lines=[previous[1], line_number],
                aliases=[alias],
                canonicals=sorted({previous[0], canonical}),
            ))
            continue
        aliases.setdefault(alias, (canonical, line_number))

    mappings = {alias: value[0] for alias, value in aliases.items()}
    if not issues:
        try:
            mappings = compile_global_synonym_map(field, mappings)
        except ValueError as exc:
            if synonym_policy_error_reason(exc) == "synonym_cycle":
                cycle_aliases = sorted(
                    alias for alias, canonical in mappings.items()
                    if canonical in mappings
                )
                cycle_lines = sorted(aliases[alias][1] for alias in cycle_aliases)
                issues.append(_editor_issue(
                    "synonym_cycle",
                    "Canonical mappings contain a cycle.",
                    lines=cycle_lines,
                    aliases=cycle_aliases,
                    canonicals=sorted({mappings[alias] for alias in cycle_aliases}),
                ))
            else:
                raise
    return {"mappings": mappings if not issues else {}, "issues": issues}


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
    taxonomy = _EDITOR_FIELD_ALIASES.get(field, field)
    config_key, _, _ = _field_spec(taxonomy)
    policy = compile_semantic_policy({config_key: mappings})
    return dict(policy["maps"][taxonomy])


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

def render_synonym_policy_mirrors(
    policies: dict[str, dict[str, str]],
    *,
    paths: dict[str, Path] | None = None,
) -> dict[str, bytes]:
    rendered: dict[str, bytes] = {}
    for synonym_type in ("skills", "domain", "role_family"):
        _, yaml_key, default_path = _field_spec(synonym_type)
        path = (paths or {}).get(synonym_type, default_path)
        raw_yaml = path.read_text(encoding="utf-8") if path.exists() else ""
        content = replace_yaml_top_level_mapping_block(
            raw_yaml=raw_yaml,
            key=yaml_key,
            mappings=compile_global_synonym_map(
                synonym_type, policies.get(synonym_type) or {}
            ),
        )
        rendered[synonym_type] = content.encode("utf-8")
    return rendered

def repair_synonym_policy_mirrors(
    policies: dict[str, dict[str, str]],
    *,
    paths: dict[str, Path] | None = None,
) -> dict[str, str]:
    rendered = render_synonym_policy_mirrors(policies, paths=paths)
    staged: dict[str, tuple[Path, Path]] = {}
    try:
        for synonym_type, content in rendered.items():
            _, _, default_path = _field_spec(synonym_type)
            path = (paths or {}).get(synonym_type, default_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="wb",
                dir=str(path.parent),
                prefix=f"{path.name}.",
                suffix=".tmp",
                delete=False,
            ) as tmp_file:
                tmp_file.write(content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())
                staged[synonym_type] = (Path(tmp_file.name), path)
        for synonym_type in ("skills", "domain", "role_family"):
            tmp_path, path = staged[synonym_type]
            os.replace(tmp_path, path)
        return {
            synonym_type: hashlib.sha256(content).hexdigest()
            for synonym_type, content in rendered.items()
        }
    finally:
        for tmp_path, _path in staged.values():
            tmp_path.unlink(missing_ok=True)

def _backup_yaml(synonym_type: str, mappings: dict[str, str]) -> bytes:
    _, yaml_key, _ = _field_spec(synonym_type)
    payload: dict[str, Any] = {yaml_key: compile_global_synonym_map(synonym_type, mappings)}
    if synonym_type == "domain":
        payload["domain_neighbors"] = {}
    return yaml.safe_dump(payload, allow_unicode=True, sort_keys=False).encode("utf-8")

def export_synonym_backup_zip(
    policies: dict[str, dict[str, str]],
    *,
    bundle_revision_id: str,
    bundle_checksum: str,
    type_revisions: dict[str, dict[str, Any]],
    exported_at: str,
) -> bytes:
    members = {
        filename: _backup_yaml(synonym_type, policies.get(synonym_type) or {})
        for synonym_type, filename in _BACKUP_MEMBERS.items()
    }
    manifest = {
        "schema_version": 1,
        "bundle_revision_id": bundle_revision_id,
        "bundle_checksum": bundle_checksum,
        "type_revisions": type_revisions,
        "exported_at": exported_at,
        "members": {
            filename: hashlib.sha256(content).hexdigest()
            for filename, content in sorted(members.items())
        },
    }
    members["manifest.json"] = json.dumps(
        manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for filename, content in sorted(members.items()):
            info = zipfile.ZipInfo(filename, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o600 << 16
            archive.writestr(info, content)
    return output.getvalue()

def inspect_synonym_backup_zip(content: bytes) -> dict[str, Any]:
    if not content or len(content) > _BACKUP_MAX_ARCHIVE_BYTES:
        raise ValueError("synonym backup archive size is invalid")
    expected = {*_BACKUP_MEMBERS.values(), "manifest.json"}
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)) or set(names) != expected:
            raise ValueError("synonym backup members are invalid")
        total = 0
        raw_members: dict[str, bytes] = {}
        for info in infos:
            path = Path(info.filename)
            if path.is_absolute() or ".." in path.parts or info.is_dir() or (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError("synonym backup member path is invalid")
            if info.file_size > _BACKUP_MAX_MEMBER_BYTES:
                raise ValueError("synonym backup member is too large")
            total += info.file_size
            if total > _BACKUP_MAX_EXTRACTED_BYTES:
                raise ValueError("synonym backup extracted size is too large")
            raw_members[info.filename] = archive.read(info)
    try:
        manifest = json.loads(raw_members["manifest.json"].decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise ValueError("synonym backup manifest is invalid") from exc
    checksums = manifest.get("members") if isinstance(manifest, dict) else None
    type_revisions = manifest.get("type_revisions") if isinstance(manifest, dict) else None
    try:
        exported_at = datetime.datetime.fromisoformat(str(manifest.get("exported_at") or ""))
    except ValueError as exc:
        raise ValueError("synonym backup manifest is invalid") from exc
    if (
        manifest.get("schema_version") != 1
        or not str(manifest.get("bundle_revision_id") or "").strip()
        or not str(manifest.get("bundle_checksum") or "").strip()
        or exported_at.tzinfo is None
        or not isinstance(checksums, dict)
        or not isinstance(type_revisions, dict)
        or set(type_revisions) != set(_BACKUP_MEMBERS)
        or any(
            not isinstance(type_revisions[synonym_type], dict)
            or not str(type_revisions[synonym_type].get("type_revision_id") or "").strip()
            or not isinstance(type_revisions[synonym_type].get("revision"), int)
            or int(type_revisions[synonym_type]["revision"]) < 1
            for synonym_type in _BACKUP_MEMBERS
        )
    ):
        raise ValueError("synonym backup manifest is invalid")
    policies: dict[str, dict[str, str]] = {}
    for synonym_type, filename in _BACKUP_MEMBERS.items():
        raw = raw_members[filename]
        if checksums.get(filename) != hashlib.sha256(raw).hexdigest():
            raise ValueError("synonym backup member checksum mismatch")
        try:
            payload = config_loader.load_yaml_text(
                raw.decode("utf-8"), source=filename, reject_duplicate_keys=True
            )
        except (UnicodeDecodeError, ValueError) as exc:
            raise ValueError("synonym backup YAML is invalid") from exc
        _, yaml_key, _ = _field_spec(synonym_type)
        mapping = payload.get(yaml_key) if isinstance(payload, dict) else None
        if not isinstance(mapping, dict):
            raise ValueError("synonym backup YAML root is invalid")
        policies[synonym_type] = compile_global_synonym_map(synonym_type, mapping)
    return {"manifest": manifest, "policies": policies}

def import_synonym_backup_zip(content: bytes) -> dict[str, Any]:
    return inspect_synonym_backup_zip(content)


def synonym_policy_error_reason(exc: Exception) -> str:
    message = str(exc).lower()
    if "cycle" in message:
        return "synonym_cycle"
    if "collision" in message or "conflict" in message or "duplicate" in message:
        return "synonym_alias_conflict"
    return "invalid_synonym_policy"
